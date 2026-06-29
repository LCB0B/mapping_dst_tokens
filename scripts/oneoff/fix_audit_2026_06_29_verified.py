#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 PART 2: workflow-verified translation errors.
These 23 were adversarially verified (find -> verify) and re-checked by hand
against the Danish. All are description_en mistranslations / untranslated copies
(description_da is correct). Country names grounded in ISO-3166.

NOT applied (left for manual review, per HARD RULES / verifier note):
  - DEM_statsb_5115 'Kongelig': meaning undocumented in a citizenship context;
    'Royal' is a literal guess, not a sourced meaning.
  - LAB_soc_status_kode_321 / LAB_tilstand_kode_15020: Danish-source typos;
    verifier advised not to overwrite verbatim source text.
"""
import csv, io

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
with open(MASTER, newline='') as f:
    rows=list(csv.reader(f))
header=rows[0]; idx={c:i for i,c in enumerate(header)}; body=rows[1:]
by={r[idx['code']]:r for r in body}
log=[]
def setc(code,col,val):
    r=by.get(code)
    if r is None:
        print("MISSING", code); return
    if r[idx[col]]!=val:
        log.append((code,col,r[idx[col]],val)); r[idx[col]]=val

# ISO-3166 country-name fixes (en + official, sourced iso3166)
iso = {
 'DEM_opr_land_5403':'United Arab Emirates',
 'DEM_opr_land_5326':'Dominican Republic',
 'DEM_opr_land_5279':'Congo, Republic of',
 'DEM_opr_land_5272':'Egypt',
 'DEM_opr_land_5215':'Comoros',
 'DEM_statsb_5272':'Egypt',
 'DEM_statsb_5326':'Dominican Republic',
 'DEM_statsb_5278':'Congo, Democratic Republic of',
 'DEM_statsb_5279':'Congo, Republic of',
 'DEM_statsb_5215':'Comoros',
 'DEM_statsb_5403':'United Arab Emirates',
}
for code,name in iso.items():
    setc(code,'description_en',name)
    setc(code,'description_en_source','iso3166')
    setc(code,'description_en_official',name)
    setc(code,'description_en_official_source','iso3166')

# "Island, ligeret dansk" = Iceland, equal rights as Danish (citizens) -- translation
for code in ('DEM_opr_land_5105','DEM_statsb_5105'):
    setc(code,'description_en','Iceland, equal rights as Danish (citizens)')

# LAB false-friend / abbreviation mistranslations (en only; da is correct)
lab = {
 'LAB_socio13_220':'Recipient of sick pay, educational allowance, leave benefits etc.',
 'LAB_socio13_120':'Assisting spouse',
 'LAB_disco_931220':'Helper for paving (cobblestone-laying) work',
 'LAB_disco_931240':'Assembly of overhead (aerial) power lines',
 'LAB_disco_832240':'Van driver work with refuse-collection tasks',
 'LAB_disco_832220':'Van driver work',
 'LAB_soc_status_kode_120':'Assisting spouses',
 'LAB_soc_status_kode_110':'Self-employed (primary status end of November)',
}
for code,en in lab.items():
    setc(code,'description_en',en)

# write
buf=io.StringIO(); w=csv.writer(buf,lineterminator='\n'); w.writerow(header); w.writerows(body)
open(MASTER,'w').write(buf.getvalue())
print(f"edits: {len(log)}")
for code,col,old,new in log:
    print(f"  {code} [{col}]: {old!r} -> {new!r}")
