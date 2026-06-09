# Source audit — `source=none|generated` categories (2026-06-04)

Verification of the categories whose labels were tagged `source=none|generated`
(the same risk pattern that produced the HEA VOLTYPECODE hallucination, see
`QC_REPORT.md` §8). Records the authoritative source for each, the verdict on the
current text, and — where a fix was applied — the commit. Entries marked **✅ FIXED**
have been corrected in MASTER; the rest are verified-correct/untagged or unresolved.

**Authoritative source map:** `input_dataset_description.csv` (repo root) maps every
model variable to its DST `REGISTER:VARIABLE` (e.g. `BEF:OPR_LAND`, `AKM:SOCIO13`,
`LMDB:VOLUME`+`VOLTYPECODE`, `KRAF:AFG_*`, `KRIN:IND_*`, `BUAF:HAENDELSE`, `KOTRE:UDEL`).
It confirmed every fix below and pins the source for the remaining categories.

Verdict legend: **WRONG** = current label is a hallucination · **CORRECT/untagged**
= label matches the source but `source` is still `none|generated` · **FILLABLE** =
empty placeholder that the cited source can fill · **UNVERIFIED** = source/variable
identified but value set not retrieved, do not assert the current label.

---

## SOC_frakkod — DST `AFG_FRAKKOD` (KRAF / Kriminalstatistik)
**Authoritative source (CONFIRMED):** DST TIMES variable **`AFG_FRAKKOD`** in the
**Kriminalstatistik (KRAF)** register — *"Frakendelsens paragraf i lovgivningen"*
("which paragraph in the Road Traffic Act or other special laws a deprivation of
driving licence, entry ban, etc. has been sentenced under").
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakkod>
The variable's table is **`D281700.TXT_FRAKKOD`** — i.e. the repo file
`raw/SOC_frakkod.txt` (same header) *is* the extracted `AFG_FRAKKOD` value set.
So both agree. 177/186 rows are already sourced as `raw_soc_frakkod`; only 5
`none|generated` + 4 `none|generated|generated` are unsourced. DST confirms the codes
(e.g. "ÅA, ÅB, ÅC, ÅD created in 2015 … alcohol lock scheme").

**Verdict: WRONG (hallucinated as prison terms).** `frakkod` is about deprivation
of *rights* — driving-licence disqualification, alcohol-interlock scheme, residence
bans — not imprisonment. The 5 codes exist verbatim in the source file with entirely
different meanings:

| Code | MASTER (hallucinated) | `raw/SOC_frakkod.txt` (authoritative) |
|------|----------------------|----------------------------------------|
| `ÅA` | Open imprisonment | Alkolås jf. færdselslovens § 60a, stk. 3 (obligatorisk ordning) |
| `ÅB` | Open, with limited community | Alkolås jf. færdselslovens § 132a, stk. 1 (frivillig ordning) |
| `ÅC` | Open imprisonment, arrest dept. | Udtrådt af alkolåsordningen |
| `UØ` | Unwanted/expelled | Førerretsfrakendelse jf. færdsl. § 126, stk. 1, nr. 7, jf. § 125, stk. 2 + selvstændig frak. |
| `UÅ` | Unopened prison | Førerretsfrakendelse jf. færdsl. § 126, stk. 1, nr. 7, jf. § 125, stk. 3 |

**✅ FIXED 2026-06-04** (`scripts/oneoff/fix_soc_frakkod.py`): 7 codes (`ÅA ÅB ÅC UØ UÅ UÆ
ØA`) rewritten with verbatim Danish from `raw/SOC_frakkod.txt` + translated English,
`source=raw_soc_frakkod`, `description_en_source=translated`, `confidence=high`. The
2 remaining (`FF`, `36`) are **not in the AFG_FRAKKOD value set** → marked
`[Unresolved …]` / `low` (their old "Withdrawal code" labels were guesses; not
invented). SOC_frakkod is now 184 sourced + 2 honest unresolved.

---

## SOC_ger7 — GER7 gerningskode (offence code)
**Authoritative source (CONFIRMED):** DST TIMES variable **`AFG_GER7`** (KRAF /
Kriminalstatistik – afgørelser); the same GER7 value set is shared by `KON_GER7`,
`SIG_GER7`, `OFR_GER7`, `ANM_GER7`, `IND_GER7`.
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-ger7>
GER7 = a 7-digit conversion of Rigspolitiet's 5-digit gerningskode, **hierarchical at
1 / 2 / 4 / 7 digits** (from counting-year 2020 only the first 4 digits + `000` are
maintained; `AFG_GER9` supersedes it). Repo 4-digit value set:
`lookup_dictionaries/SOC_ger7_dict.csv` (89 codes; first-digit distribution
0:1, 1:68, 2:5, 3:15 — **no 4xxx**). 920/938 rows already sourced (`CSV:SOC_ger7*`).

**Verdict (checked vs AFG_GER7, 2026-06-04): no hallucination, but notes.**
- 1-digit `0` → MASTER placeholder "Criminal offense code 0"; **DST: `0` = Uoplyst**
  (unknown). FILLABLE.
- 2-digit groups verified vs DST. `12`=Voldsforbrydelser and `13`=Ejendomsforbrydelser
  match exactly. Two use older/umbrella wording (semantically correct, can be aligned):
  `11` MASTER "Sædelighedsforbrydelser" vs DST current **"Seksualforbrydelser"**;
  `14` MASTER "Andre straffelovsforbrydelser" vs DST **"Andre forbrydelser"**;
  `38` MASTER "Særlovsovertrædelser" vs DST **"Særlove i øvrigt"** (38 is the residual
  special-law subgroup, not the whole 3x umbrella — slightly imprecise).
- 7-digit detail codes starting with **1** (`1146000`,`1465720`,`1470`,`1480505`):
  their 4-digit prefixes (1146/1465/1470/1480) are **not in the repo dict** (neighbours
  like 1145/1460/1475/1485 exist), so they are valid-looking GER7 codes from another
  vintage but **unverified** here; MASTER carries honest group placeholders, not guesses.
- Codes starting with **4** (`4010`,`4020`,`4010825`,`4010840`,`4020340`,`4020515`,
  `4020630`,`4020910`): **NOT valid GER7** — GER7's first digit is 0–3 and the dict has
  zero 4xxx codes. Anomalous (different coding or data artifact); MASTER labels are
  honest "Criminal offense code X" placeholders. **Flag — do not treat as GER7.**

**Action (later):** fill `0`=Uoplyst; tag the 2-digit groups to `AFG_GER7` and optionally
align `11`/`14`/`38` to DST current wording; obtain the full AFG_GER7 4-digit value set
to resolve the 1xxx detail codes; investigate the 4xxx codes' true origin separately.

---

## DEM_kom — municipality / special territorial codes
**Authoritative source (in repo):** `lookup_dictionaries/DEM_kom_dict.csv`
(343/356 rows sourced `CSV:DEM_kom`) + DST kommune classification for the 9xx
territorial codes.

**Authoritative source checked:** DST TIMES variable **KOM** (bopælskommune) —
<https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-befolkning-og-valg/kom>
— and the repo dict `DEM_kom_dict.csv` (which mirrors it).

**Verdict: no hallucination; mixed (2026-06-04, checked vs DST KOM).**
- `011` → "Told og Skattestyrelsen" **CORRECT/untagged** (matches DST KOM / dict `DEM_kom_11`).
- `010`/`012`/`019` are empty placeholders, **FILLABLE** and confirmed by DST KOM + dict:
  `10`=Sømandsskattekontoret, `12`=ATP, `19`=Administrativ (Sygehusene).
- `955`–`960` = **RESOLVED: the modern Greenland municipalities** (2009 reform + 2018
  split), which is why they are absent from the dict's *old* Greenland list `901`–`953`
  — the vocab spans both eras. Sources: cpr.dk Grønland-2018 (authoritative for 958/959/960)
  <https://www.cpr.dk/cpr-systemet/aendringer/kommunesammenlaegninger-opdeling/groenland-2018>
  + stat.gl / 2009-reform docs (955/956/957). **Two current labels are WRONG:**

  | code | MASTER (wrong/vague) | authoritative |
  |------|----------------------|----------------|
  | 955 | "Grønland" (vague) | Kommune Kujalleq |
  | 956 | "Grønlandsk kommune" (vague) | Kommuneqarfik Sermersooq |
  | 957 | *(empty)* | Qeqqata Kommunia |
  | 958 | *(empty)* | Qaasuitsup Kommunia (2009–2017) |
  | 959 | ❌ "Udlandet (Abroad)" | **Kommune Qeqertalik** (2018–) |
  | 960 | ❌ "Færøerne (Faroe Islands)" | **Avannaata Kommunia** (2018–) |

- `004`/`007`/`009`: still **UNRESOLVED** — in the administrative/tax 0xx family
  (cf. `10`=Sømandsskattekontoret, `11`=Told og Skattestyrelsen, `12`=ATP,
  `19`=Administrativ (Sygehusene); CPR uses 0010–0019 for persons without residence
  assigned a CPR no. for tax reasons), but the specific labels for 004/007/009 were not
  found in any source. Need DST Forskningsservice / original `.pt`. (Note: there is **no**
  Færøerne or Udlandet code among 955–960 — those MASTER labels were hallucinated.)

**Action (later):** (a) fix `955`–`960` to the Greenland municipality names above
(`source=cpr_groenland` / `dst-kom`, conf high); (b) fill `010`/`012`/`019` + tag `011`
from DST KOM/dict; (c) leave `004`/`007`/`009` flagged unresolved pending DST.

---

## DEM_familie — `FAMILIE_TYPE`
**Authoritative source (DST):** TIMES variable **FAMILIE_TYPE** —
<https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-befolkning-og-valg/familie-type>

**Verdict: CORRECT/untagged — all 9 verified.** `type_N` maps to FAMILIE_TYPE code N
exactly:

| code | FAMILIE_TYPE (DST) | MASTER `type_N` |
|------|--------------------|-----------------|
| 1 | Ægtepar | ✓ Married couple |
| 2 | Registreret partnerskab | ✓ |
| 3 | Samlevende par | ✓ Cohabiting (common children) |
| 4 | Samboende par | ✓ Common-law (no common children) |
| 5 | Enlig (herunder også ikke hjemmeboende børn) | ✓ |
| 7 | Ægtepar forskellig køn | ✓ |
| 8 | Ægtepar samme køn | ✓ |
| 9 | Enlig | ✓ |
| 10 | Ikke hjemmeboende børn | ✓ |

**Action (later):** re-tag `source=dst_times_familie_type` (URL above); labels need no
change.

---

## EDU_udel — `UDEL` = Uddannelsesdel (KOTRE / Uddannelsesregister)
**Authoritative source (CONFIRMED):** DST TIMES variable **`UDEL`** ("Uddannelsesdel"),
the KOTRE education-part / klassetrin variable —
<https://www.dst.dk/da/Statistik/dokumentation/Times/uddannelseregister/udel>
(value set retrieved 2026-06-04).

**Verdict: CORRECT/untagged — all 24 verified verbatim.** The DST UDEL value set
matches every MASTER label exactly: `0`=Udelt uddannelse; `20`–`31`=0.–11. klassetrin;
`40`=FGU basis/spor ikke valgt; `41`=FGU spor; `51`=EUD indgangsforløb; `52`=EUD
hovedforløb; `53`=EUD indgangsforløb 1; `54`=EUD indgangsforløb 2; `55`=EUD EUX
studiekompetenceforløb; `56`=Grundforløb plus; `60`=Udelt kandidatuddannelse;
`61`=Bacheloruddannelse; `62`=Kandidatoverbygning; `64`=Akademisk overbygningsuddannelse.
Not a hallucination — labels were just untagged.

**Action (later):** re-tag `source=dst_times_udel` (URL above); labels need no change.

---

## SOC_haendelse — DST `HAENDELSE` (Udsatte børn og unge / BUAF) — NOT criminal

**Authoritative source (CONFIRMED):** DST TIMES variable **`HAENDELSE`**, table
`D280601.TXT_ANB_HAENDELSE` = *"Hændelse i anbringelsessag"* — events in an out-of-home
**placement** (anbringelse) case for vulnerable children/youth. **Not** a criminal-event
code. <https://www.dst.dk/da/Statistik/dokumentation/Times/boern-og-unge/haendelse>
(+ repo `raw/SOC_haendelse.txt`, same table).

**✅ FIXED 2026-06-04** (`scripts/oneoff/fix_soc_haendelse_frakbkod.py`): the decimal sub-codes
(0.2/1.1/5.5/7.5) were already sourced; the integer codes `0/1/2/5/7` had been left as
bogus *"Criminal event type: N"* and are now filled verbatim from the DST value set:
`0`=Iværksættelse af anbringelse, `1`=Iværksættelse af ændret anbringelsessted,
`2`=Ændring af tvangsanbringelse til frivillig anbringelse, `5`=Hjemgivelse/ophør af
anbringelse, `7`=Iværksættelse/genetablering af efterværn. `confidence=high`. (The
category prefix `SOC_` is a misnomer — this is child-welfare, not crime — but codes/IDs
untouched.)

## SOC_frakbkod — DST `AFG_FRAKBKOD` (KRAF)

**Authoritative source (CONFIRMED, fetched twice):** DST TIMES **`AFG_FRAKBKOD`** —
code indicating whether a frakendelse (e.g. driving licence) is *"for bestandig"*
(permanent). <https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakbkod>
Value set: `0`=Uoplyst, `1`=bestandig, `2`=endelig dom, `3`=domsdato, `4`=ikke mere bestandig.

**✅ FIXED 2026-06-04** — all 4 MASTER labels were **hallucinations** (1="Betinget
frakendelse", 2="Ubetinget", 3="Kørselsforbud", 4="Betinget med vilkår" — the variable
is about *permanent*, not betinget/ubetinget). Rewritten to the verbatim value set
(`source=dst_afg_frakbkod`, conf high).

## SOC_fgslkod — DST `IND_FGSLKOD` (KRIN) — ✅ FIXED (was hallucinated)

**Authoritative source (CONFIRMED):** DST TIMES **`IND_FGSLKOD`** — *"Fængslingskode.
Angiver typen af indsættelse (anholdelse, varetægtsfængsling, afsoning mv.)"* — the
**type of incarceration event**, NOT the institution type.
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/ind-fgslkod>
(Whole KRIN codebook downloaded to `raw/dst_downloads/KRIN_codebook.md`.)

The MASTER labels were **hallucinations** — institution types invented from the abbrev:

| code | MASTER (wrong) | IND_FGSLKOD (authoritative) |
|------|----------------|------------------------------|
| 0 | "Prison type code: 0" | Afsoning påbegyndt/fortsat under andet journalnummer |
| 1 | ❌ Åbent fængsel | Anholdt under sag |
| 2 | ❌ Lukket fængsel | Anholdelse opretholdt |
| 3 | ❌ Arresthus | Varetægtsfængslet |
| 4 | ❌ Halvåbent fængsel | Overførsel af afsoner |
| 5 | ❌ Pension | Afsoner |

**✅ FIXED 2026-06-04** (`scripts/oneoff/fix_soc_fgslkod.py`): all 6 rewritten verbatim,
`source=dst_ind_fgslkod`, conf high. (`IND_FGSLSTED` is the separate institution-PLACE
variable, with letter codes `A###`/`F###`/`P###` — not this type code.)

## SOC_afgtypko + SOC_bstrfkod — Danish was bad MT, upgraded from KRIN codebook

Both were already **code-sourced** (`raw/SOC_afgtypko.txt` 85/86; `raw/SOC_bstrfkod` 3/3)
— not hallucinations — **but their `description_da` held machine-translated English**, not
Danish (e.g. `bstrfkod` `1` "Hæfte" → *"Booklet"*; afgtypko `19` → *"Out-of-court goods of
fines and waivers"*). Per `input_dataset_description.csv`: `SOC_afgtypko`=`KRAF:AFG_AFGTYPKO`
/`KON_AFGTYPKO` (rows 104), `SOC_bstrfkod`=`KRIN:IND_BSTRFKOD` (row 120).

**✅ FIXED 2026-06-04** (`scripts/oneoff/fix_soc_afgtypko_bstrfkod.py`): installed the verbatim
authoritative Danish from the downloaded KRIN codebook (`IND_AFGTYPKO` / `IND_BSTRFKOD`)
into `description_da`, plus a faithful clean English translation; `source=dst_afgtypko` /
`dst_ind_bstrfkod`, conf high. **85** afgtypko + **3** bstrfkod rows. afgtypko code `85` is
**absent from the DST value set** (jumps 84→86) → left `[Unresolved]`, not invented.

## Batch (a) — in-repo resolutions (2026-06-04, `scripts/oneoff/fix_inrepo_batch_a.py`)

Resolved from the KRIN codebook + repo files (per `input_dataset_description.csv`):
- **`SOC_loeslkod`** (9) — was bad MT ("Unenlightened"=Uoplyst); upgraded from `IND_LOESLKOD`
  (verbatim Danish + clean English), `source=dst_ind_loeslkod`.
- **`LAB_stoette`** (7) — `AMRUN:STOETTE_BESK_KODE`, filled from `raw/LAB_stoette_besk_kode_nullified.txt`
  (1=løntilskud, 3=fleksjob, 6=voksenlærling…), `source=raw_lab_stoette`.
- **`LAB_fravaer`** (4) — `AMRUN:FRAVAER_BESK_KODE`, from `raw/LAB_fravaer_besk_kode_nullified.txt`.
- **`EDU_afg`** (4) — `KOTRE:AFG_ART`, re-tagged/filled from `EDU_afg_art_dict.csv`.

Not resolvable in-repo (left, not invented): **`DEM_far`/`DEM_mor`** weak codes `1/2/99/unknown`
are absent from the FTDB value set (`FAR/MOR_FOED_ADOP` has 0,11,12,14,…). **`EDU_tilg`**
(`KOTRE:TILG_ART`) → DST-fetch batch (b).

## Batch (b) — DST value-set fetch (2026-06-04, `scripts/oneoff/fix_dst_fetch_batch_b.py`)

A workflow fetched the DST TIMES value set for each remaining variable; results applied:
- **`DEM_ie`** (4) — **HALLUCINATED**: was "Immigration/Emigration event"; `BEF:IE_TYPE` is
  *herkomst* → `type_1`=Personer med dansk oprindelse, `type_2`=Indvandrere,
  `type_3`=Efterkommere, `type_unknown`=Uoplyst. FIXED, `source=dst_bef_ie_type`.
- **`HEA_urgency`** — `LPR_ADM:INDM` (Indlæggelsesmåde) has only `1`=Akut, `2`=Ikke-akut →
  fixed those; the `9`/`ATA*` codes are **not in the INDM value set** (older/triage source
  values) → left unresolved.
- **`HEA_patienttype`** (4) — matches `LPR_ADM:PATTYPE` (0=Heldøgn/1=Deldøgn/2=Ambulant/
  3=Skadestue) → re-tagged `source=dst_lpr_pattype` (+ aligned code 0 Danish).
- **`DEM_relation`** (5) — labels (Barn/Forælder/Helsøskende/Halvsøskende/Søskende ukendt)
  are the model's correct derived categories from `FAMILY_RELATIONS:RELATION` → re-tagged.
- **`EDU_tilg`** (8) — labels match `KOTRE:TILG_ART` value set verbatim → re-tagged.

Confirmed correct already (no change): **`LAB_socio13`** (21) matches `AKM:SOCIO13` verbatim.
**No public value set → left unresolved (not guessed):** `LAB_tilstand` (`AMRUN:TILSTAND_KODE_AMR`
— DST states "ingen værdisæt"; 5-digit codes only via Forskningsservice) and `LAB_socio` `gl_*`
(`AKM:SOCIO_GL` — see deep-dive below).

## LAB_socio `gl_*` = AKM `SOCIO_GL` (1976–1990) — ✅ RESOLVED via crosswalk (2026-06-05)

**Update:** since the raw value set is not public, the labels were recovered **empirically** from
longitudinal sequences (run on the VM → `crosswalks/empirical/socio_gl_crosswalk_empirical.csv`). For people
observed across the ~1987 scheme boundary, each `gl_X` is mapped to its **modal SOCIO13** successor,
labelled with the authoritative `LAB_socio13` text (`scripts/oneoff/apply_socio_gl_crosswalk.py`).
**49/51 recovered** (17 high / 8 medium / 24 low confidence by transition share);
`gl_81`/`gl_82` have no data → `[Unresolved]`. `source=empirical_crosswalk_socio13`; the socio13
code + share + n are recorded in `description_da_alt`. The original deep-dive (below) stands as the
provenance for why the crosswalk was necessary.



`SOCIO_GL` = AKM "Socioøkonomisk klassifikation fra 1976 til 1990" (DST AKM variable list).
It is the **`ARBSTIL`** member of the socio family (per the Aarhus LMDG IDAN var-description
`idan_vde.pdf`): `ARBSTIL` 1980-1993 → `NYARB` 1994-95 → `SOCSTIL_KODE` 1996-2007 →
`SOC_STATUS_KODE` 2008-. Authoritative **group structure** (idan_vde): `11-15`=selvstændige,
`20`=medhjælpende ægtefælle, `31-37`=lønmodtagere, `40`=arbejdsløse, `50/55`=tilbagetrækning,
`60`=pensionister, `90/91/92`=others. The detailed benefit subdivisions were introduced **1994+**.

**The raw 2-digit value set is NOT public.** DST's TIMES `ARBSTIL` page
(`moduldata-for-arbejdsmarked/arbstil`) links a value set `SOCIO_ARB_ARBSTIL_KODE_V1_1980`,
but that nomenclature (downloaded to `raw/dst_downloads/arbstil_kode_1980.csv`) is the
**harmonized 3-digit** scheme (110/131/200/311…/517) — it does **not** contain the raw 2-digit
codes our `gl_*` use. So the raw codes live only in DST Forskningsservice / the original `.pt`
(HARD RULE #5). Searched extensively + IDA arbejdsnotat 27 (scanned image, unreadable).

**Verdict on the 17 labelled `gl_*`:** unsourced. `gl_20` (Medhjælpende ægtefælle) and `gl_40`
(Arbejdsløs) are **confirmed** by idan_vde's group structure. `gl_41/42/43/49/51/52/53`
(orlov/barselsdagpenge/sygedagpenge/revalidering/aktivering/ledighedsydelse/efterløn-detail) are
**anachronistic** for 1976-1990 → almost certainly hallucinated. The rest (`11/12/19/31/32/33/39/50`)
are group-plausible but not confirmable per-code. **Recommendation:** re-mark the anachronistic +
unconfirmable ones `[Unresolved]` (keeping `gl_20`/`gl_40`), OR fill all 51 from the raw `.pt` /
DST Forskningsservice value set if available. Left unchanged pending that decision.

## LAB_db07 5-digit — ✅ 23/42 RESOLVED via firm crosswalk (2026-06-05) + analysis

**Update:** recovered empirically from firm sequences (`crosswalks/empirical/industry_crosswalk_empirical.csv`,
`scripts/apply_db07_industry_crosswalk.py`): each 5-digit db07 code → the DB93/nace code the same
firm co-occurs with → label from `raw/LAB_nace.txt`. **23/42 resolved** (share≥0.3, n≥20),
`source=empirical_industry_crosswalk`. This **confirmed the encoding & that the old guesses were
wrong**: the codes are agriculture/forestry/fishing/mining (`11100`=Kornavl, `13000`=Planteskoler,
`15000`=mixed farming, `61000`=crude petroleum, `89900`=other mining) — NOT textiles/leather/telecom.
`514620`/`999999` resolved directly from DB93. 19 with no/weak co-occurrence stay `[Unresolved]`.
The original analysis (below) explains the ambiguity the crosswalk settled.



The 691 sourced `LAB_db07` codes are 6-digit DB07 (NACE Rev.2); **none start with `0`**, i.e.
the agriculture/mining divisions 01–09 are absent from the sourced set. The 44 weak codes are
the leftovers and are a **mixed encoding**:
- **`514620`** = DB93/NACE-Rev1 `51.46.20` "Engroshandel med læge- og hospitalsartikler"
  (NACE-Rev2 has no `51xxxx`, so unambiguous) and **`999999`** = "Ikke oplyst" → **FIXED**
  (`source=raw_lab_nace`, from `raw/LAB_nace_en.txt`/`LAB_nace.txt`).
- **The 5-digit block (`11100`–`89900`)** is **ambiguous between three encodings** that yield
  *different* industries, so it cannot be resolved by online lookup:
  - (A) NACE-Rev2 **division**-level — what the current guesses assume (`13000`=textiles,
    `61000`=telecom, `71000`=architects);
  - (B) **DB07 6-digit with the leading `0` stripped** (`13000`→`013000`=plant propagation;
    strongly suggested by the absence of any `0xxxxx` in the sourced set);
  - (C) **DB93** (`raw/LAB_nace_en.txt`: `13000`=Planteavl kombineret med husdyravl / mixed farming).
  The ambiguity is in *how the builder encoded the code*, not in what DB07/DB93 mean — DST
  lookups confirm all three are valid but different. The current NACE-Rev2 guesses
  (`13000/15000/17000/24000/61000/71000`) are therefore **unverified** (and contradicted by DB93
  for `13000`/`15000`). This is the "wrong DB07 5-digit mapping" CLAUDE.md HARD RULES warn about.

**Resolution (same as SOCIO_GL):** the original `.pt` (exact codes) or a **transition-crosswalk**
on the firm/person sequences (when an industry token switches between this 5-digit code and a
known 6-digit DB07) — see `SOCIO_GL_README.md`. 36 stay `[Unresolved]`; the 6 NACE-Rev2 guesses
are left pending that decision (mark `[Unresolved]` vs fill from `.pt`).

---

## Summary

| Category | Source | Verdict | In repo? |
|----------|--------|---------|----------|
| SOC_frakkod (5+4) | DST `AFG_FRAKKOD` (KRAF) = `raw/SOC_frakkod.txt` | **✅ FIXED** (7 sourced, 2 unresolved) | ✅ |
| SOC_ger7 (18) | DST `AFG_GER7` (KRAF) + `SOC_ger7_dict.csv` | groups correct (0=Uoplyst fillable; 11/14/38 wording); 1xxx need full DST list; **4xxx not valid GER7** | ✅ (groups) |
| DEM_kom (13) | DST KOM + cpr.dk Grønland + `DEM_kom_dict.csv` | **955–960 RESOLVED = modern Greenland kommuner** (959/960 were WRONG: Abroad/Faroe); 011 correct; 010/012/019 fillable; 004/007/009 still unresolved | mostly |
| DEM_familie (9) | DST TIMES FAMILIE_TYPE | **CORRECT — all 9 verified** | ❌ (DST URL) |
| EDU_udel (25) | DST TIMES `UDEL` (KOTRE) | **CORRECT — all 24 verified verbatim** | ❌ (DST URL) |
| SOC_haendelse (5) | DST `HAENDELSE` (børn og unge/BUAF) + `raw/SOC_haendelse.txt` | **✅ FIXED** — was mis-labelled "Criminal event"; it's out-of-home placement | ✅ |
| SOC_frakbkod (4) | DST `AFG_FRAKBKOD` (KRAF) | **✅ FIXED** — all 4 were hallucinated (betinget/ubetinget); var = permanent-or-not | ❌ (DST URL) |
| SOC_fgslkod (6) | DST `IND_FGSLKOD` (KRIN) | **✅ FIXED** — was hallucinated as prison types; it's the incarceration-event type | ✅ (codebook) |
| SOC_afgtypko (85) | DST `AFG_AFGTYPKO`/`IND_AFGTYPKO` | **✅ UPGRADED** — Danish was bad MT; installed verbatim Danish + clean English (85 absent→unresolved) | ✅ (codebook) |
| SOC_bstrfkod (3) | DST `IND_BSTRFKOD` | **✅ UPGRADED** — "Booklet"→"Hæfte" etc.; verbatim Danish + clean English | ✅ (codebook) |

**Hallucinations corrected so far:** HEA VOLTYPECODE family (168), `SOC_frakkod` (5),
`DEM_kom` 959/960 (Greenland), `SOC_frakbkod` (4), `SOC_haendelse` integer codes (5,
mis-categorised as criminal), `SOC_fgslkod` (6, incarceration type not prison type).
Verified-correct-but-untagged: `EDU_udel`, `DEM_familie`, `SOC_ger7` groups. Still
unresolved (not guessed): `LAB_socio gl_*`, `LAB_db07` 5-digit, `DEM_kom` 004/007/009,
`SOC_ger7` 1xxx/4xxx, most `LAB_tilstand`. Full KRIN codebook: `raw/dst_downloads/KRIN_codebook.md`.
