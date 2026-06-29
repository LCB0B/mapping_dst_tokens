#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 (see conversation: MASTER mistake audit).
All fixes are sourced (no invented code meanings). Edits MASTER only;
run scripts/regenerate_mappings.py afterwards.

Fixes applied:
  1. HEA_ICD10_03819  - English was editorial boilerplate leaked from an ICD
     revision doc; replaced with a faithful English of the Latin description_da
     "Septicaemia staphylococcica".
  2. HEA_ICD10 glued cross-reference codes (WHO parse artifact): insert a space
     where a lowercase word runs straight into a chapter cross-ref [A-Z][0-9]{2}
     (e.g. "diseaseG30.-" -> "disease G30.-"). description_en + description_en_official.
  3. LAB_branche_77_61154 - "knallerter" (mopeds) mistranslated as "fireworks".
  4. LAB_branche_77_62299 - "i.a.n." (= ikke andetsteds naevnt = n.e.c.)
     mistranslated as "including but not limited to".
  5. DEM_kom 6 dual-name codes - Python-list-literal leak from DEM_kom_dict.csv;
     normalised to current name (description_da) + historical (description_da_alt).
     849 also had translation-corrupted "Jammern Bugt" -> dict's "Jammerbugt".
  6. LAB_db07 18 codes - stale legacy `description`/`description_short` still
     "[Unresolved ...]" though resolved 2026-06-15; synced to description_da.
"""
import csv, re, sys

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
with open(MASTER, newline='') as f:
    reader=csv.reader(f)
    rows=list(reader)
header=rows[0]
idx={c:i for i,c in enumerate(header)}
body=rows[1:]
by_code={r[idx['code']]: r for r in body}

log=[]
def setcell(code, col, val):
    r=by_code[code]
    old=r[idx[col]]
    if old!=val:
        r[idx[col]]=val
        log.append((code, col, old, val))

# --- Fix 1: ICD10_03819 editorial-text leak ---
setcell('HEA_ICD10_03819', 'description_en', 'Staphylococcal septicaemia')

# --- Fix 2: ICD10 glued cross-reference codes ---
GLUE=re.compile(r'(?<=[a-z])(?=[A-Z][0-9]{2})')
nglue=0
for r in body:
    if r[idx['category']]!='HEA_ICD10':
        continue
    for col in ('description_en','description_en_official'):
        v=r[idx[col]]
        if v:
            nv=GLUE.sub(' ', v)
            if nv!=v:
                old=v; r[idx[col]]=nv
                log.append((r[idx['code']], col, old, nv)); nglue+=1

# --- Fix 3 & 4: LAB_branche translation errors ---
setcell('LAB_branche_77_61154', 'description_en',
        'Wholesale of bicycles, mopeds, baby carriages and')
setcell('LAB_branche_77_62299', 'description_en', 'Other retail trade n.e.c.')

# --- Fix 5: DEM_kom dual-name normalisation (source: lookup_dictionaries/DEM_kom_dict.csv) ---
# primary (current) name, historical/alt name, and whether en/short still hold the literal
kom = {
 '751': ('Aarhus', 'Århus', False),
 '851': ('Aalborg', 'Ålborg', False),
 '169': ('Høje-Taastrup', 'Høje Tåstrup', False),
 '400': ('Bornholms Regionskommune', 'Bornholm', False),  # en/short already informative, leave
 '707': ('Norddjurs', 'Grenaa', True),                     # en/short still literal -> fix
 '849': ('Jammerbugt', 'Åbybro', True),                    # en/short literal+corrupted -> fix
}
for k,(primary, alt, fix_en) in kom.items():
    code=f'DEM_kom_{k}'
    setcell(code, 'description_da', primary)
    setcell(code, 'description_da_alt', alt)
    setcell(code, 'description', primary)
    if fix_en:
        setcell(code, 'description_en', primary)
        setcell(code, 'description_short', primary)

# --- Fix 6: db07 stale legacy description ---
db07=['14920','17000','16300','31200','12300','12100','12600','12200','23000',
      '11600','14400','11200','72900','89100','12700','11400','71000','11500']
for v in db07:
    code=f'LAB_db07_{v}'
    da=by_code[code][idx['description_da']]
    setcell(code, 'description', da)
    setcell(code, 'description_short', da)

# --- write back ---
import io
buf=io.StringIO()
w=csv.writer(buf, lineterminator='\n')
w.writerow(header)
w.writerows(body)
open(MASTER,'w').write(buf.getvalue())

# --- report ---
print(f"Total cell edits: {len(log)}  (ICD10 glue edits: {nglue})")
from collections import Counter
print("By column:", dict(Counter(c for _,c,_,_ in log)))
print("\n--- non-ICD10-glue edits (full detail) ---")
for code,col,old,new in log:
    if col in ('description_en','description_en_official') and code.startswith('HEA_ICD10') and code!='HEA_ICD10_03819':
        continue
    print(f"  {code} [{col}]\n     - {old!r}\n     + {new!r}")
