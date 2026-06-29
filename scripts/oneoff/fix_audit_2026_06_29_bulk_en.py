#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 PART 3: bulk description_en corrections from the
workflow audit (find stage), for the self-verifiable categories. The verify
stage was cut short by a spend limit, so these were hand-reviewed by reading
all 630 findings against the Danish before applying.

POLICY (HARD-RULES compliant):
  * Only description_en is changed. description_da (authoritative training text)
    is NEVER modified -- so danish_typo findings are SKIPPED (reported only).
  * Only issue_type in {translation_error, untranslated_english, garbled_or_truncated}.
  * The Danish meaning is GIVEN (description_da is correct); these are translation
    fixes of known Danish, not inferred code meanings.
  * Empty suggested_fix -> skipped. Partial ("...") fixes -> targeted edits below.
A full change log is written to scratchpad for review/revert.
"""
import csv, io, json, re

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
RAW='/tmp/claude-270889/-home-louibo-mappings/2875cd75-8662-4465-877b-ef32d155f377/scratchpad/raw_audit_findings.json'
LOG='/tmp/claude-270889/-home-louibo-mappings/2875cd75-8662-4465-877b-ef32d155f377/scratchpad/applied_en_fixes.tsv'

with open(MASTER, newline='') as f:
    rows=list(csv.reader(f))
header=rows[0]; idx={c:i for i,c in enumerate(header)}; body=rows[1:]
by={r[idx['code']]:r for r in body}
codes=set(by)

raw=json.load(open(RAW))
verified=set(json.load(open('/tmp/claude-270889/-home-louibo-mappings/2875cd75-8662-4465-877b-ef32d155f377/scratchpad/verified_codes.json')))
SELF={'LAB_nace','LAB_branche','LAB_disco','LAB_disco08','LAB_socio','LAB_socio13','LAB_soc','LAB_tilstand',
      'EDU_udd','EDU_audd','EDU_disced','EDU_field','EDU_course','DEM_opr','DEM_statsb','DEM_kom','DEM_civst',
      'SOC_ger7','SOC_frakkod','SOC_pgf','SOC_ansted','SOC_afgtypko'}
FIXTYPES={'translation_error','untranslated_english','garbled_or_truncated'}

def resolve(cat, code):
    if code in codes: return code
    if f'{cat}_{code}' in codes: return f'{cat}_{code}'
    return None

# Build best finding per resolved code (skip danish_typo / empty / partial here)
best={}
unresolved=[]
partial=[]
for f in raw:
    if f.get('code') in verified: continue
    if f.get('issue_type') not in FIXTYPES: continue
    if f.get('_cat') not in SELF: continue
    rc=resolve(f['_cat'], f.get('code',''))
    if not rc:
        unresolved.append(f); continue
    fx=(f.get('suggested_fix') or '').strip()
    if not fx:
        continue
    if fx.startswith('...') or fx.endswith('...'):
        f['_rc']=rc; partial.append(f); continue
    # keep first standalone fix per code
    if rc not in best:
        f['_rc']=rc; best[rc]=f

log=[]
def apply_en(rc, newen, tag):
    r=by[rc]; old=r[idx['description_en']]
    if old!=newen and newen:
        r[idx['description_en']]=newen
        log.append((rc, tag, old, newen))

# 1) bulk standalone
for rc,f in best.items():
    apply_en(rc, f['suggested_fix'].strip(), f['issue_type'])

# 2) targeted partial handling
# 2a) SOC_frakkod 'lille knallert' rendered as firearm/air-rifle -> moped
KNAL=re.compile(r'small (air rifle|air guns|air gun|firearm vehicle|firearms|firearm)', re.I)
for f in partial:
    rc=f['_rc']
    if rc.startswith('SOC_frakkod_') and 'knallert' in (f.get('da','') or '').lower():
        cur=by[rc][idx['description_en']]
        new=KNAL.sub('small moped', cur)
        apply_en(rc, new, 'knallert->moped')
# 2b) promille rendered as %
for code in ('SOC_frakkod_60','SOC_frakkod_86'):
    if code in by:
        cur=by[code][idx['description_en']]
        new=cur.replace('1.2%','1.2 per mille').replace('1,2%','1.2 per mille')
        apply_en(code, new, 'promille')
# 2c) conditional revocation mislabelled as reinstatement/restoration
for code in ('SOC_frakkod_81','SOC_frakkod_85'):
    if code in by:
        cur=by[code][idx['description_en']]
        new=cur.replace('reinstatement','revocation').replace('restoration','revocation')
        apply_en(code, new, 'revocation')
# 2d) EDU degree-level B.A. -> master's (kand.) for the kand.2år partials
for f in partial:
    rc=f['_rc']
    if rc.startswith('EDU_udd_') and 'kand.2' in (f.get('da','') or '').lower():
        cur=by[rc][idx['description_en']]
        new=cur.replace('B.A. 2 years',"kand.2yr (master's)").replace('B.A. 2yr',"kand.2yr (master's)")
        apply_en(rc, new, 'BA->kand')
# 2e) misc targeted partials
misc={
 'EDU_udd_4157': ('Piling Contractor','paver'),
 'EDU_udd_5060': ('Bandaging Assistant','orthopaedic technician'),
}
for code,(a,b) in misc.items():
    if code in by:
        apply_en(code, by[code][idx['description_en']].replace(a,b), 'misc')

# write MASTER
buf=io.StringIO(); w=csv.writer(buf,lineterminator='\n'); w.writerow(header); w.writerows(body)
open(MASTER,'w').write(buf.getvalue())

# write log
with open(LOG,'w',newline='') as g:
    wl=csv.writer(g,delimiter='\t'); wl.writerow(['code','tag','old_en','new_en'])
    for rc,tag,old,new in log: wl.writerow([rc,tag,old,new])

from collections import Counter
print(f"applied description_en fixes: {len(log)}")
print("by category:", Counter(rc.rsplit('_',1)[0] if rc.count('_')>=2 else rc for rc,_,_,_ in log).most_common(12))
print("unresolved finding codes:", len(unresolved), [f.get('code') for f in unresolved][:10])
print("log ->", LOG)