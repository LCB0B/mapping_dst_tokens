#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 PART 6: leftover findings the auditor left without a
confident suggested_fix. Each English below is a faithful translation of the
GIVEN Danish (description_da, unchanged) or a clear de-garbling.
SKIPPED (not guessed, per HARD RULES, reported instead):
  - DEM_statsb_5115 'Kongelig' (citizenship meaning undocumented)
  - EDU_audd_4851 'Nitter og stemmer' (opaque trade name; cannot translate confidently)
"""
import csv, io

EN = {
 'LAB_branche_77_36912': 'Manufacture of moler (diatomite/kieselguhr) products',
 'LAB_branche_77_61157': 'Wholesale of leather goods, fancy goods (haberdashery) and souvenirs',
 'LAB_branche_77_50195': 'Furnace/kiln setting',
 'EDU_audd_200': '1-6 years, ivu [completed qualification]',
 'EDU_audd_210': '9-10 years, ivu [completed qualification]',
 'EDU_audd_5924': 'Choir, ear-training and notation, music pedagogue diploma examination [completed qualification]',
 'EDU_audd_6631': 'Eastern (bloc) state studies, cand.phil. [completed qualification]',
 'EDU_audd_8603': 'Social service provision (socialformidling), diploma programme [completed qualification]',
 'EDU_audd_8604': 'Academy programme to statonom (public administration) [completed qualification]',
 'EDU_udd_5156': 'Catering/household manager (økonoma) [current education]',
 'EDU_udd_4369': 'Building assembly technician [current education]',
 'EDU_udd_7523': 'HA(jur.) Business Economics and Law, bach. [current education]',
}
# Danish typo: DI502 'infufficiens' -> 'insufficiens' (en is already correct)
DA_TYPO = [('HEA_ICD10_DI502', 'infufficiens', 'insufficiens')]

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
with open(MASTER, newline='') as f:
    rows=list(csv.reader(f))
h=rows[0]; idx={c:i for i,c in enumerate(h)}; by={r[idx['code']]:r for r in rows[1:]}
log=[]
for code,en in EN.items():
    r=by.get(code)
    if r is None: log.append((code,'MISSING')); continue
    if r[idx['description_en']]!=en:
        log.append((code,'en',r[idx['description_en']],en)); r[idx['description_en']]=en
for code,a,b in DA_TYPO:
    r=by.get(code)
    if r is None: continue
    for col in ('description_da','description'):
        if a in r[idx[col]]:
            log.append((code,col,r[idx[col]],r[idx[col]].replace(a,b))); r[idx[col]]=r[idx[col]].replace(a,b)

buf=io.StringIO(); w=csv.writer(buf,lineterminator='\n'); w.writerows(rows)
open(MASTER,'w').write(buf.getvalue())
print(f"leftover edits: {sum(1 for x in log if len(x)==4)}")
for x in log:
    if len(x)==4: print(f"  {x[0]} [{x[1]}]: {x[2][:45]!r} -> {x[3][:45]!r}")
    else: print(f"  {x[0]}: {x[1]}")
