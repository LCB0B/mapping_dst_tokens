#!/usr/bin/env python3
"""
Audit fixes 2026-06-29 PART 4: unambiguous orthographic typo corrections in the
Danish label columns. These are non-word corruptions (e.g. 'vcld'->'vold',
'unbdtagen'->'undtagen', 'fkerflaet'->'flerfladet'); the token is keyed by
code/value (not the label string), so correcting the spelling preserves
semantics. Each replacement is presence-guarded and only touches the label
columns where the misspelling actually appears.
SKIPPED: HEA_ICD10_DI502 ('inkompenseret' vs 'dekompenseret' is an in-/de- meaning
distinction, not a typo) -- reported for manual review.
"""
import csv, io

MASTER='MASTER_CATEGORY_MAPPINGS.csv'
LABEL_COLS=['description_da','description','description_da_full','description_short','description_en']

pairs=[
 ('HEA_ICD10_DD249F','Harmartom','Hamartom'),
 ('HEA_ICD10_DZ113B','syflis','syfilis'),
 ('EDU_audd_1509','grundsskolekursus','grundskolekursus'),
 ('EDU_audd_3866','infomationsteknologi','informationsteknologi'),
 ('EDU_audd_5918','rystmisk','rytmisk'),
 ('EDU_audd_6011','Samfundsvindenskab','Samfundsvidenskab'),
 ('EDU_audd_6991','Samfundsvindenskab','Samfundsvidenskab'),
 ('EDU_audd_8447','pædadgoguddannelsen','pædagoguddannelsen'),
 ('EDU_disced_20304010','Bacalaurétte','Baccalauréat'),
 ('EDU_disced_60255720','brasilliansk','brasiliansk'),
 ('EDU_disced_60352015','Biomedicn','Biomedicin'),
 ('EDU_disced_70255720','brasilliansk','brasiliansk'),
 ('EDU_disced_70352015','Biomedicn','Biomedicin'),
 ('EDU_udd_3113','Innivation','Innovation'),
 ('EDU_udd_4028','Akademiøkonon','Akademiøkonom'),
 ('EDU_udd_4030','Labratorie','Laboratorie'),
 ('EDU_udd_5218','inveractive','interactive'),
 ('EDU_udd_5260','Civilingenør','Civilingeniør'),
 ('EDU_udd_6744','Communikation','Communication'),
 ('EDU_udd_7846','Klasisk','Klassisk'),
 ('HEA_ICD10_DT754A','elektisk','elektrisk'),
 ('HEA_speciale_013025','Anæstæsi','Anæstesi'),
 ('HEA_speciale_445301','Hvepsegid','Hvepsegift'),
 ('HEA_speciale_501558','fkerflaet','flerfladet'),
 ('LAB_branche_77_81021','Reakkreditinstitutter','Realkreditinstitutter'),
 ('LAB_nace_295620','unbdtagen','undtagen'),
 ('LAB_nace_364000','sportsrekvistitter','sportsrekvisitter'),
 ('SOC_frakkod_BE','Hastidhedsoverskridelse','Hastighedsoverskridelse'),
 ('SOC_frakkod_BF','Hastidhedsoverskridelse','Hastighedsoverskridelse'),
 ('SOC_ger7_1250000','vcld','vold'),
]

with open(MASTER, newline='') as f:
    rows=list(csv.reader(f))
header=rows[0]; idx={c:i for i,c in enumerate(header)}; body=rows[1:]
by={r[idx['code']]:r for r in body}

log=[]
for code,wrong,right in pairs:
    r=by.get(code)
    if r is None:
        log.append((code,'MISSING','','')); continue
    hit=False
    for col in LABEL_COLS:
        v=r[idx[col]]
        if wrong in v:
            r[idx[col]]=v.replace(wrong,right); hit=True
            log.append((code,col,v,r[idx[col]]))
    if not hit:
        log.append((code,'NOT-FOUND',wrong,''))

buf=io.StringIO(); w=csv.writer(buf,lineterminator='\n'); w.writerow(header); w.writerows(body)
open(MASTER,'w').write(buf.getvalue())
print(f"typo edits: {sum(1 for _,c,_,_ in log if c in LABEL_COLS)}")
for code,col,old,new in log:
    if col in LABEL_COLS:
        print(f"  {code} [{col}]: {old[:50]!r} -> {new[:50]!r}")
    else:
        print(f"  {code}: {col} ({old})")
