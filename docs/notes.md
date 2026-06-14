# Notes on Danish Classifications in This Repo

## 1. `DB07` is NOT `DISCO-07`

Point of confusion: the `07` in `DB07` refers to the **year 2007**, when Denmark adopted the NACE Rev. 2 industry classification. It has nothing to do with DISCO.

| Name | Classifies | International parent | Year adopted |
|---|---|---|---|
| **DB07** (Dansk Branchekode 2007) | **Industries** (retail, manufacturing, hospitals) | NACE Rev. 2 | 2007 |
| **NACE Rev 1.1** / *branche* | Industries (older) | NACE Rev 1.1 | 1992–2007 |
| **DISCO-08** | **Occupations** (nurse, programmer, electrician) | ISCO-08 | 2011 |
| **DISCO-88** | Occupations (older) | ISCO-88 | 1996–2009 (per DST documentation) |

**There is no DISCO-07.** Denmark went from DISCO-88 → DISCO-08 (jump of 20 in the year), not through a "DISCO-07" intermediate.

In this repo:
- `LAB_db07_*` = **industries** (DB07)
- `LAB_nace_*` = **industries** (NACE Rev 1.1, 1992–2007)
- `LAB_branche_*` = **industries** (branche77, even older)
- `LAB_disco08_*` = **occupations** (DISCO-08)
- `LAB_disco_*` = **occupations** — see version-drift caveat below

---

## 2. What `LAB_disco` actually is (and the version-drift story)

DST officially publishes **two** DISCO versions:

| Version | Validity | Matches | DST page |
|---|---|---|---|
| DISCO-88, v1:1996 | 1996–01–01 → 2009–12–31 | ISCO-88 | [dst.dk/.../disco?id=5d292535…](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco?id=5d292535-2f1f-4225-87e8-0b551d72cd2c) |
| DISCO-08, v1:2010 | 2010–01–01 → present | ISCO-08 | [dst.dk/.../disco](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco) |

Both DISCO-88 and DISCO-08 CSVs are now saved to `raw/dst_downloads/`:
- `disco88_dst.csv` (520 codes, 4-digit max)
- *(DISCO-08 is in the existing `raw/LAB_disco.csv`)*

### Three Danish-description files in the repo — all supposedly "DISCO"

| File | Codes | What we thought it was | What it actually is |
|---|---|---|---|
| `lookup_dictionaries/LAB_disco_dict_from_raw.csv` | 1,165 | The older DISCO (DISCO-88) | **Actually DISCO-08 Danish descriptions under an "older" label** |
| `raw/LAB_disco_codes.txt` | 794 | A DISCO version | Appears to be DISCO-88 (1996 version) |
| `raw/LAB_disco.csv` | 1,172 | DISCO-08 | DISCO-08 (confirmed) |

### Why 149 rows had wrong "official" English

Earlier we populated `description_en_official` for `LAB_disco` rows via **ISCO-88** 4-digit-prefix lookup, assuming the `LAB_disco` category meant "older DISCO = DISCO-88". That gave wrong answers for the subset of rows where MASTER's `description_da` was actually a DISCO-08 description at a DISCO-08 code.

**Concrete example: `LAB_disco_314100`**

| Source | 314100 means |
|---|---|
| MASTER `description_da` (what the training data means) | "Teknikerarbejde inden for biovidenskab" *(Bioscience technician)* — this is **DISCO-08 3141** "Life science technicians (excluding medical)" |
| `LAB_disco_codes.txt` 314100 | "Teknisk arbejde om bord på skibe" *(Technical work on ships)* — this is **DISCO-88 3141** "Ships' engineers" |
| Our first ISCO-88 lookup | "Ships' engineers" — **WRONG** because MASTER is actually DISCO-08 numbered |

The same 4-digit code `3141` means entirely different occupations in DISCO-88 vs DISCO-08. The re-numbering happened in the 2010 reform.

### Fix applied (name-based crosswalk)

`scripts/oneoff/crosswalk_lab_disco.py` detects per-row which version each `LAB_disco` row is actually in:

1. If `description_da` exactly matches DISCO-08's Danish at the same numeric code → use **ISCO-08** for the official English.
2. Else if it matches DISCO-88's Danish at the same code → use **ISCO-88**.
3. Else try fuzzy name-match ≥ 0.90 against both DISCO Danish dictionaries.
4. Else leave `description_en_official` empty.

**Result: all 149 previously-misclassified rows resolved to DISCO-08** — meaning MASTER's `LAB_disco` category actually contains DISCO-08 codes (mixed with some DISCO-88 — the boundary varies by row). The English labels from ISCO-08 are now correct.

| LAB_disco row source (detected) | Count |
|---|---|
| Uses DISCO-08 numbering + descriptions | ~168 previously known + 149 just fixed = **317** |
| Uses DISCO-88 numbering | 642 (were already correctly linked to ISCO-88) |
| Fuzzy-matched (either version) | 0 |

So the `LAB_disco` category name is somewhat misleading — it's really "DISCO occupations, mixed era". Every row now has either a reliable ISCO-08 or ISCO-88 English title, and `description_en_source` tags which.

### Why we don't overwrite `description_da`

MASTER's Danish descriptions are the **ground truth** for what the training data means. Changing them to match some "official" DST description would silently re-label every training record linked to that token. The translation (`description_en`) should follow the Danish; the "official" label (`description_en_official`) must be reconciled via code OR name matching without mutating the Danish.

---

## 3. HEA_speciale and regional §2-aftaler

### Background
`HEA_speciale` covers the Danish Sygesikringsregisteret — provider billing codes from GP / specialist / lab services. The value is structured as **specialty + procedure**:

- 6-digit codes (post-2005): first 2 digits = specialty (e.g., `80` = Almen Lægehjælp / GP), last 4 digits = procedure
- 5-digit codes (pre-2005): first 1 digit = specialty, last 4 digits = procedure

### National vs regional codes
Procedure codes below `4000` and specific named ranges are **nationally defined** in the central Overenskomst (fee schedule) between RLTN (Regionernes Lønnings- og Takstnævn) and PLO (Praktiserende Lægers Organisation). Procedures above `4000` are typically **§2-aftaler** — regional agreements negotiated independently between each of Denmark's 5 regions and its regional PLO branch. Some are also tied to specific counties (pre-2007 amter) or municipalities.

Sources for the regional codes are listed per region in `raw/dst_downloads/regional_p2_codes.csv`. Covered so far:

| Region | Codes captured | Key documents |
|---|---|---|
| Sjælland | ~39 | [§2-aftaler overview](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/sjaelland/almen-praksis/klinikadministration/aftaler/paragraf-to-aftaler/) + [ydelseskoder PDF](https://www.sundhed.dk/content/cms/31/79431_paragraf-2-aftaler-ydelseskoder.pdf) |
| Syddanmark | ~54 | [§2-oversigt](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/syddanmark/almen-praksis/klinikadministration/aftaler/paragraf-2-aftaler/paragraf-2-aftaler-oversigt/) |
| Hovedstaden | ~30 | [laeger.dk PLO-H](https://laeger.dk/foreninger/plo/overenskomsten-og-aftaler/kommunale-og-regionale-aftaler/aftaler-i-region-hovedstaden) |
| Midtjylland | ~24 | [sundhed.dk Midtjylland takster](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/midtjylland/almen-praksis/regionalt/lokalaftaler/takster/) |
| Nordjylland | 0 (not yet consolidated) | [laeger.dk PLO-N](https://laeger.dk/foreninger/plo/overenskomsten-og-aftaler/kommunale-og-regionale-aftaler/aftaler-i-region-nordjylland) |

### Code overlap between regions

Three types:

1. **Same concept, different codes** (common, non-problematic) — e.g., "opfølgende hjemmebesøg" (follow-up home visit) uses `4230-4268` in Sjælland, `4250-4253` in Hovedstaden, `4676/4688-4693` in Syddanmark, `4213-4216` in Midtjylland. Each code maps 1-to-1 to its region.

2. **Same code, same meaning** (national code adopted in multiple §2-aftaler) — e.g., the DD2 (Type 2 Diabetes Research Database) project uses codes `4612`–`4615` nationally; Syddanmark and Midtjylland both reference them with the same semantics.

3. **Same code, DIFFERENT meaning** (genuinely problematic) — same 4-digit procedure means different things in different regions. Known cases:

| Code | Region A | Region B |
|---|---|---|
| `4657` | Syddanmark: "Samtale med pårørende" | Hovedstaden: "Konsultation i stedet for hjemmebesøg (Palliation)" |
| `4612` | Syddanmark: "DD2 model 1, komplet indrullering" | Midtjylland: "DD2 model 1 fuld pakke" (same, slight rewording) |
| `4614` | Syddanmark: "DD2 model 3 henvisning" | Midtjylland: "DD2 model 3 henviser videre" (same concept) |
| `4615` | Syddanmark: "DD2 model 4, delvis indrullering" | Midtjylland: "DD2 blodprøve og forsendelse" **(genuinely different)** |

### How we handle conflicts in MASTER

Each MASTER row has a **single** `description_da` (because each token ID must have one meaning). For codes with real regional conflicts we:

1. Put one region's meaning in `description_da` (tagged with `(regional §2-aftale, Region X)` in the description itself for traceability).
2. Record the alternative(s) in a new `description_da_alt` column. Example for `HEA_speciale_804657`:
   - `description_da`: "Almen Lægehjælp 80, Samtale med pårørende (regional §2-aftale, Region Syddanmark)"
   - `description_da_alt`: "[Syddanmark] Samtale med pårørende (Alvorligt syge og døende); [Hovedstaden] Konsultation i stedet for hjemmebesøg (Palliation)"

This preserves the polysemy without breaking the one-row-per-token contract. Downstream consumers that care about regional disambiguation can inspect `description_da_alt`.

### Fundamental limitation
The training data itself carries **one token ID per 6-digit code** — billing records from all 5 regions for the same code collapse to a single embedding. If region-sensitive analysis matters downstream, the tokenization pipeline would need a region suffix (`HEA_speciale_804657_syd` vs `_hov`). This is an upstream schema change beyond the scope of this repo.

## 4. The `.0` float duplicate bug (fixed) {#section-dot0}

`vocab.json` and `vocab_2.json` originally contained 769 codes ending in `.0`:

| Type | Count | Resolution |
|---|---|---|
| **Twins** (both `X` and `X.0` existed, identical descriptions) | 736 | Deleted the `.0` entries. Token IDs now have 736 holes (1.8%). |
| **Orphans** (only `X.0` existed) | 33 | Renamed `X.0` → `X`. Token IDs preserved. |

The fix was originally applied only to `vocab.json` and MASTER; the per-category
code-definition CSVs (`hierarchical_vocab/{DEM,EDU,HEA,LAB,SOC,SPECIAL}/`) stayed
at the original 41,201-code state until 2026-06-09, when
`scripts/oneoff/fix_codedef_dot0.py` applied the same two resolutions there
(verified afterwards: union of code-def codes == vocab.json, token IDs intact).

**Upstream preprocessing still needed** — any future record that serializes a numeric code with trailing `.0` must be normalised to int-string before tokenizer lookup:

```python
s = str(value)
if s.endswith(".0"):
    s = s[:-2]
```

---

## 4b. HEA drug-volume categories are LMDB VOLUME/VOLTYPECODE (not procedure codes)

The 13 HEA categories `DDK, DW, DWG, DWK, GA, GI, GP, L, MG, ML, PK, ST, TU` (+ the
bare `HEA_`) were originally labelled "procedure codes" and filled with invented
clinical meanings (`HEA_GA`="gestational age", `HEA_MG`="specialist visits",
`HEA_ML`="lab tests", `HEA_ST`="inpatient days", `HEA_L`="medication prescriptions",
`HEA_DW`="DW diagnosis code prefix", …), all `source=none|generated`. **All wrong** —
classic HARD-RULES hallucination (plausible medical phrase guessed from the abbrev).

They are the **`VOLTYPECODE`** unit types for the **`VOLUME`** variable in the
Lægemiddeldatabasen (LMDB). VOLUME = numeric quantity of one medicine package, only
interpretable with its unit; the `manual_bin_*`/`over_1000` values are binned VOLUME
ranges in that unit. The 13 prefixes match the official VOLTYPECODE value set
one-for-one; the bare `HEA_` (token 10278, interleaved in the volume-bin token block)
is the blank VOLTYPECODE (non-specific medicine/quantity/fee/veterinary).

Unit map (verbatim VOLTYPETXT): DDK=DøgnDosis DK, DW=DDD WHO Index,
DWG=DDD WHO Guidelines, DWK=DDD WHO Kombinationsliste, GA=g (aktivt stof),
GI=g (iod), GP=g (præparat), L=L, MG=mg (aktivt stof), ML=ml, PK=pakninger,
ST=Stk, TU=tusind enheder.

Source: esundhed.dk Lægemiddelstatistikregisteret docs `rid=14&tid=63&vid=396`
(VOLTYPECODE) / `vid=399` (VOLUME). Fixed 2026-06-04 by
`scripts/oneoff/fix_hea_volume_voltypecode.py` (168 rows; `source=esundhed:lmdb_voltypecode`,
`description_en_source=dst-lmdb-voltypecode`, confidence high/medium).

---

## 5. MASTER column schema

| Column | Meaning |
|---|---|
| `description_da` | Danish, authoritative — follows the training-data semantics |
| `description_da_alt` | Alternative regional meanings (populated only for the ~4 HEA_speciale codes with conflicting §2-aftale semantics across regions — see §3) |
| `description_en` | Best-available English — translated from Danish **or** taken from an international classification |
| `description_en_official` | English only when traceable to an international standard (WHO / NACE / ISCO / ISO-3166 / DST SSR specialty). Empty when not available or not reliable. |
| `description_en_official_source` | Which authority the official English came from: `who-icd10`, `who-atc`, `nace2`, `nace2-crosswalk`, `isco08`, `isco08-crosswalk`, `isco88`, `iso3166`, `dst-ssr-specialty` |
| `description_en_source` | Provenance tag for `description_en`: same values + `translated`, `copy-of-da`, `empty` |

Consumers needing guaranteed accuracy should filter on `description_en_official`. Consumers needing broad coverage should use `description_en` and treat `description_en_source` as a quality signal.

---

## 6. External files downloaded — all under `raw/dst_downloads/`

| File | Source | Codes | Used for |
|---|---|---|---|
| `db07_v2_2013.csv` | [dst.dk DB07](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/db07) | 1,725 | LAB_db07 Danish descriptions |
| `ger7.csv` | dst.dk AFG_GER7 (HTML-scraped) | 1,263 | SOC_ger7 Danish descriptions |
| `speciale_dst_full.xlsx` | dst.dk SPECIALE ydelser | 15,957 | HEA_speciale verification |
| `audd_ddu_full.csv` | dst.dk DDU-AUDD | 4,704 | AUDD verification |
| `audd_disced15.csv` | dst.dk DISCED-15-AUDD | 5,398 | AUDD verification |
| `disco88_dst.csv` | [dst.dk DISCO-88 v1:1996](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco?id=5d292535-2f1f-4225-87e8-0b551d72cd2c) | 520 | DISCO-88 reference |
| `icd10_who_2019_en.csv` | [icdcdn.who.int ClaML 2019](https://icdcdn.who.int/icd10/index.html) | 11,539 | HEA_ICD10 English (authoritative) |
| `atc_who_2021_en.csv` | [github.com/fabkury/atcd](https://github.com/fabkury/atcd) | 6,440 | HEA_atc English (authoritative) |
| `nace_rev2_en.csv` | [vincentarelbundock Rdatasets](https://vincentarelbundock.github.io/Rdatasets/doc/validate/nace_rev2.html) | 996 | LAB_db07 English |
| `isco08_en.csv` | GitHub gist + manual major groups | 619 | LAB_disco08 English + LAB_disco crosswalk |
| `isco88_en.csv` | Warwick IER xls + manual major groups | 519 | LAB_disco English |

---

## HEA_patienttype — all 4 codes were inverted

Discovered during per-category English audit. The LPR (Landspatientregisteret)
`c_pattype` variable from Sundhedsdatastyrelsen defines patient
administrative type. The original descriptions in MASTER (from
`source=none|generated`, i.e. guessed during initial vocab build) had all four
codes mapped to the wrong labels.

Authoritative source: [esundhed.dk c_pattype documentation](https://www.esundhed.dk/Dokumentation/DocumentationExtended?id=5)
(Sundhedsdatastyrelsen / Danish Health Data Authority).

| Code | Danish (authoritative) | Old (wrong) EN | New (correct) EN |
|---|---|---|---|
| 0 | Heldøgnspatient | Outpatient ❌ | **Inpatient (stationary admission)** |
| 1 | Deldøgnspatient | Inpatient ❌ | **Day/half-day patient (discontinued 2002)** |
| 2 | Ambulant patient | Emergency ❌ | **Outpatient (from 2014 also includes emergency with acute admission)** |
| 3 | Skadestuepatient | Ambulatory ❌ | **Emergency room patient (discontinued 2014)** |

Notes on the DST timeline:
- 1977–1993: only code 0 (inpatient) was registered even though other codes existed
- After 2002: code 1 (day patient) discontinued — institutions now code as
  either inpatient or outpatient
- 2014: code 3 (emergency room) was folded into code 2 (outpatient) with the
  admission-mode flag `c_indm=1` (acute) used to distinguish ER visits.

`description_en_source` is now `dst_lpr_c_pattype` and `confidence_level=high`.

## LAB income quantile translations — 14 categories rewritten

Found during the 2026-04-19 audit pass. The LAB income quantile categories
(Q1–Q100) had been translated by MT without consulting DST TIMES variable
documentation. Several had catastrophic mistranslations.

Authoritative source for each: `https://www.dst.dk/da/Statistik/dokumentation/Times/personindkomst/<varname>`

| Category (variable) | Old (wrong) EN | New (DST authoritative) |
|---|---|---|
| LAB_skatmvialt (`skatmvialt_13`) | "Tax-deductible maintenance payments" ❌ | **Total taxes, labor market contribution and special pension (excl. church tax)** |
| LAB_ovrig (`ovrig_dagpenge_akas_13`) | "Other labor income" ❌ | **Other unemployment benefits from A-kasses (excl. efterløn, regular unemployment benefit, training allowance)** |
| LAB_korstoett (`korstoett`) | "Housing insurance and housing benefit" ❌ | **Housing benefit (tenants) and housing allowance (pensioners)** — insurance→benefit mistranslation of *Boligsikring* |
| LAB_lejev (`lejev_egen_bolig`) | "Rental income" ❌ | **Imputed rental value of own dwelling** — it's an imputed value for homeowners, not actual rental income |
| LAB_syg (`syg_barsel_13`) | "Sick pay benefits" | **Sick leave and maternity benefits (paid by municipalities)** — was missing the maternity half |
| LAB_folkefortid (`folkefortid_13`) | "Early retirement pension" | **State pension (folkepension) and disability pension (førtidspension), etc.** — førtidspension ≠ early retirement, it's disability; folkepension was missing |
| LAB_bredt (`bredt_loen_beloeb`) | "Broad income measure" | **Broad wage amount (incl. ATP and employee benefits)** — it's wages, not income |
| LAB_dagpenge (`dagpenge_kontant_13`) | "Unemployment benefits" | **Unemployment and cash benefits etc. combined (dagpenge, kontanthjælp, sygedagpenge, barsel)** |
| LAB_korydial (`korydial`) | "after registration for the entire calendar year" | **annualized to full calendar year** — *opregning* = annualization, not registration |
| LAB_perindkialt (`perindkialt_13`) | "Personal income total" | **Total personal income (excl. imputed rental value of own dwelling)** |
| LAB_privat (`privat_pension_13`) | "Private income/pensions" | **Paid-out private pensions** — the "income" part was extraneous |
| LAB_netovskud (`netovskud_13`) | "Net surplus/profit" | **Net profit from self-employment** |
| LAB_offpens (`offpens_efterlon_13`) | "Public pensions" | **State pension, disability pension, heating allowance, efterløn and flex benefit** |
| LAB_resuink (`resuink_13`) | "Residual income" | **Residual income (including child support)** |

All 28 income categories now have `description_en_source=dst_times_<variable>`
so each can be verified against its DST TIMES page. `description_da` was also
populated with the authoritative DST Danish name (previously empty).

Loanwords intentionally retained in the English: `efterløn`, `dagpenge`,
`kontanthjælp`, `førtidspension`, `folkepension`, `A-kasser`, `fleksydelse` —
these Danish welfare terms don't have clean English equivalents and are kept
as loanwords (like how "kindergarten" is retained in English).

## 7. Summary of corrections to MASTER

- **1,420** mojibake rows in HEA_speciale repaired (MacRoman-as-Latin1 bytes restored to proper Danish)
- **2,485** HEA_ICD10 rows gained WHO English via `D`-prefix code mapping
- **668** HEA_atc rows gained WHO English (composed `<class>, <substance>`)
- **1,347** LAB_db07 English filled from NACE Rev 2 (4-digit prefix)
- **707** LAB_disco08 English filled from ISCO-08 (4-digit prefix)
- **610** LAB_disco English filled from ISCO-88 (4-digit prefix)
- **149** LAB_disco rows re-resolved via name-based crosswalk to **ISCO-08** after discovering they were DISCO-08 codes mislabelled as "older DISCO"
- **667** SOC_ger7 rows translated with rule-based Danish→English (a few dozen partials remain)
- **736** `.0` duplicate vocab entries removed, **33** orphan floats renamed to int

Final state: 40,465 rows, 99.94% have English descriptions, 43% have authoritative `description_en_official`, 0 mojibake, 0 `.0` keys in vocab.

## 8. EDU_disced '(compound:)' fix + vocab_hierarchy regeneration (2026-06-09)

### All 790 EDU_disced descriptions were wrong-granularity
Every `EDU_disced` row carried a description of the form
`<label> (compound: <8-digit code>)` (source `CSV:EDU_disced_compound_start/_end`),
where `<label>` was the title of the **4-digit programme group**, not the
8-digit programme itself. 776/790 contradicted the official 8-digit titles
(e.g. `30551510` is *Industriteknikeruddannelsen*, not "Teknologiområdet,
maskinteknik og produktion"; `50583010` is *Maskinmester, MVU*, not "Teknisk,
MVU"). The official Danish titles for all 790 codes were taken from the DST
AUDD/UDD↔DISCED crosswalks (`crosswalks/edu/df_{AUDD,UDD}_DISCED.parquet`,
`code4`/`title4`; the two tables agree on every overlapping code).
`scripts/oneoff/fix_disced_compound.py` set `description_da` to the official
title (`source=crosswalk_edu_disced`) and `description_en`/`description_short`
to an English rendering (`description_en_source=fable-5-edu`: 94 reused from
existing audd/udd translations of the same Danish title, 696 translated by
Fable 5 from a reviewed base-name dictionary embedded in the script; full
audit trail in `scripts/worklists/disced_title_translations.tsv`). The legacy
`description` column keeps the old compound text.

### vocab_hierarchy.json regenerated
The original file (built by `scripts/oneoff/build_token_hierarchy.py`) was
frozen pre-corrections: it still contained the hallucinated HEA volume-code
labels, the 736 deleted `.0` entries, and `"Group X"` placeholder labels on
synthetic nodes. `scripts/build_vocab_hierarchy.py` (permanent) now rebuilds
it from MASTER: token nodes carry `description_en` **and** `description_da`,
and synthetic orphan-group nodes are labelled from the official reference
files via `scripts/describe_vocab.py` (with `label_source` recording the
provenance). Validated: every one of the 40,465 token_ids appears exactly once.

### New / repaired reference sources (see raw/dst_downloads/SOURCES.md)
- `raw/dst_downloads/nace_rev1_en.csv` — was a failed PDF extraction; now the
  real NACE Rev. 1 (1990) structure, 833 codes with English titles, from the
  Eurostat RAMON-LD mirror. Wired into `describe_vocab.py` as the English
  source for `LAB_nace` (DB93) aggregation levels.
- `raw/dst_downloads/sks_dia_dk.csv` — complete SKS `dia` catalog (25,048
  D-codes, Danish, validity dates) from Sundhedsdatastyrelsen; superset of
  `HEA_ICD10_dict.csv` (+69 codes). Layered into `describe_vocab.py`.
- Aggregation prefixes like `DVRA`/`DVRK`/`DUM0`/`DUP0`/`DU99` are **not**
  classification levels in SKS (only `DUP` = fosterpræsentation exists) —
  vocabs truncated at 3 ICD characters will honestly miss those families.

## 9. Official English preferred over custom translations (2026-06-09)

`scripts/oneoff/prefer_official_english.py` — 8,353 changes. Where
`description_en` was a custom/LLM translation but `description_en_official`
provably describes the **same classification level**, the official text now
also fills `description_en` (with `description_en_source` set to the official
authority). Level checks per group:

| Group | Replaced | Same-level check |
|---|---|---|
| HEA_ICD10 | 6,994 | value (D stripped) is an exact WHO ICD-10 2019 code. Danish-only sub-codes (DQ808A …) keep their more precise translations (5,738 skipped). |
| HEA_atc | 924 | exact WHO ATC 2021 code |
| LAB_nace | 195 | official was per-row NAME-matched (`nace2-crosswalk`) — also fixed real mistranslations (155200 'Fremstilling af konsumis' was "Production of consumer goods" → "Manufacture of ice cream") |
| LAB_disco / disco08 | 141 / 32 | value ends `00` (4-digit ISCO group + DST padding); 6-digit Danish subdivisions keep translations |
| LAB_db07 6-digit | 5 | ends `00` AND `description_da` matches the DST DB07 title at the padded level |
| HEA_speciale | 0 | officials are specialty-level (2-digit) — far coarser than the 6-digit billing codes; never replaced |

### 12 more leading-zero-misread LAB_db07 rows fixed
The 5-digit `LAB_db07` rows tagged `CSV:LAB_db07_hierarchical` (14100, 91000,
16200, 16100, 81100, 14200, 81200, 14300, 99000, 32200, 32100, 62000 — 14100
alone has 51,995 people) still carried the **literal** NACE Rev 2 reading
("Fremstilling af beklædningsartikler", "Computerprogrammering", …). A 5-digit
value cannot be a literal DB07 code (DB07 is 6-digit): each is a 6-digit code
with the leading zero stripped. The zero-restored reading was verified per row
against the DST DB07 title **and** the empirical DB93 co-occurrence partner
(e.g. 14100 = 01.41.00 'Avl af malkekvæg', DB93 partner 'Malkekvæghold',
share 0.99). Re-labelled with `source=dst_db07_leading_zero`, basis in
`description_da_alt`, confidence high/medium/low by co-occurrence support
(62000 has no co-occurrence data — structural argument + DST title only, low).

Also: 40 contradicting `description_en_official` values cleared on the
empirically-recovered/unresolved 5-digit rows plus 999999/514620 (they held
the literal misreading, e.g. 11100 → "Manufacture of beverages"), and 10
garbled empirical translations fixed ('Hortithnries' → 'Market gardens',
'Agerbrug, by the way' → 'Other arable farming', 'Grain Breeding' → 'Grain
growing', …).

## 10. Audit round 2 (2026-06-09): hierarchy, markers, partial translations

`scripts/oneoff/audit_fixes_20260609.py` + `scripts/oneoff/fix_ger7_partial_translations.py`:

- **54 LAB_db07 5-digit `parent_code` re-pointed.** They pointed at the
  literal 4-digit truncation (14100 → `LAB_db07_1410`), wrong under the
  leading-zero-stripped reading. Now `LAB_db07_0<class>` (14100 →
  `LAB_db07_0141`), written WITH the leading zero so it is unambiguous.
- **9 LAB_db07 rows upgraded from group- to class-level labels.** The
  47911x block + 222290 carried the 47.9 group label ("Detailhandel
  undtagen fra forretninger, stalde og markeder (via 479)") although the
  4-digit class is known and finer (47.91 internet/mail-order retail).
  da/en now carry the DST/NACE class titles with a `(via 47.91)` marker
  (`source=dst_db07_class_label`; old label in `description_da_alt`).
  452590/702010/702020 left as-is (no clean DST class).
- **75 SOC_ger7 `(via NNNN)` markers stripped** where the value is the
  4-digit group + `000` padding — the group label IS the same-level label
  there (matched against `SOC_ger7_dict.csv` before stripping). The two
  genuinely-deeper rows (1312715, 1430510) keep their markers.
- **33 SOC_ger7 half-translated English rows fixed** ("Seat belt, ikke brug
  af", "Ulovlig adgang to erdutyshemmeligheder", "foreignersloven" …) —
  re-translated in full from the official ger7.csv Danish, keyed by value
  with the expected Danish asserted.
- **129 `description_en_source` tags upgraded** where `description_en` was
  byte-identical to `description_en_official` but still tagged `translated`
  (the translation coincided with the official text) — now tagged with the
  official authority (115 who-icd10, 14 nace2).
- **7 EDU translation-cruft fixes** (" (via jura)"/" (via 51)" stripped from
  EDU_audd English; EDU_field 256020 aligned with the Danish "i øvrigt").
- Checked and found OK: HIERARCHY_SUMMARY.csv (in sync with MASTER),
  prevalence join, ICD-8 rows, the `generated_pattern`/`none|generated`
  sources (all are quantile/day-count bin categories with appropriate
  pattern labels), and the 806 English texts containing æ/ø/å (place names,
  degree titles, documented loanwords — intentional).

## 11. Row-by-row audit (2026-06-09, round 3)

Every MASTER row was passed through per-row validators (naming/token-id
integrity, parent sanity, text hygiene, provenance-tag consistency,
official-text verification against the WHO/NACE/ISCO reference files,
prevalence sanity). Fixes in `scripts/oneoff/audit_row_fixes_20260609.py`:

- **1,264 `value` columns resynced from `code`.** HEA_speciale values had
  lost their leading zero (code `HEA_speciale_090120` / value `90120` — the
  same serialization-bug class as the `.0` issue); DEM_manual_bin_* values
  contained a chunk of the category name. `code` (the join key) was correct
  everywhere; the per-category code-definition CSVs were already correct.
- **6,448 `description_en_official_source` tags got a `-parent` suffix**
  (5,766 who-icd10, 275 isco88, 210 isco08, 197 nace2) where the official
  text is the verbatim label of an ANCESTOR code rather than the code
  itself (e.g. DQ808A 'Sjögren-Larssons syndrom' carrying WHO's Q80.8
  title). Same-level officials (exact code, or pure zero-padding as in
  disco 441900 = ISCO 4419 — but never for ICD-10, where a trailing 0 is a
  real subcode) keep their plain tag. Verified in the same pass: **every
  filled official matches its claimed reference verbatim at the exact code
  or an ancestor — no fabricated officials exist.**
- **10 truncated SOC_ger7 English texts** re-translated ('Forsøg på
  manddrab' had become ' on homicide').
- **5 EDU English leftovers** fixed ('Biofysiske programmes', three
  'Grafisk technician' rows, empty 'Grade code: ' for EDU_grade NA).
- **611 whitespace normalisations** (double spaces / unstripped ends in
  description_da/en/official/short — fee-schedule column-alignment
  artifacts), and SOC_frakkod_UJ mojibake aligned with the raw source.

Known/accepted (checked, not changed): HEA_atc officials use the documented
composed '<class>, <substance>' form rather than verbatim WHO text (notes
§7); 22 HEA_atc officials are for ATC codes newer than the 2021 WHO file
(e.g. N02BF01 gabapentin, added by WHO later) — plausible and kept; 362
empty description_da (EDU_grade/EDU_course/special tokens etc. — categories
without Danish register text, plus the 19 unresolved db07 + 2 socio);
'47,XXX' karyotype and 'e-todo-lac' are validator false positives.

## 12. Audit round 4 (2026-06-10): dict agreement, prevalence internals, translation integrity

New audit axes, fixes in `scripts/oneoff/audit_round4_fixes_20260610.py`:

### Verified clean (no change)
- **Tier-1 dict agreement:** all 14,650 HEA_ICD10 codes present in both
  `lookup_dictionaries/HEA_ICD10_dict.csv` and MASTER have byte-identical
  Danish; same for SOC_ger7. Zero drift between MASTER and its highest-tier
  sources.
- **EDU program_group invariants:** all 5,240 groups have exactly one
  `is_primary_code=True`, and it is always the max-`pct_people` member.
- **Prevalence internals:** `pct_people` = `n_people` / N with N = 9,028,68x
  (±80) across all 1,732 large tokens — internally consistent. The 86 MASTER
  codes absent from `token_occurrences.csv` are the documented rare codes.
- **Translation digit-preservation:** of 166 da↔en digit mismatches, 165 are
  benign (ordinals/degree signs written out: '2°' → 'second degree';
  documented annotations like '(discontinued 2014)'). The 79 ICD rows with
  identical da/en are Latin terms valid in both languages.
- No parent cycles, no embedded newlines, all text NFC-normalised.

### Found and fixed (15 rows)
- `LAB_socio13_135`: register validity dates had leaked into the English
  ('Other wage earners 01-01-1600 31-12-9999 Other wage earners').
- `HEA_ICD10_Y8609` (ICD-8): English truncated to '(born on the sgh)' —
  re-translated in full; was also the single row missing description_short.
- 13 `SOC_afgtypko` rows whose 'translated' English was untranslated Danish
  statute shorthand ('Rpl p.723, stk.1, nr.2') — now rendered as English
  citations to the Administration of Justice Act.

### Infrastructure
- **`token_occurrences.csv` token_id column belongs to `archive/vocab_2.json`**
  (verified 40,635/40,635 match vocab_2, 40,376 mismatch vocab.json). The
  prevalence join was done by code, so MASTER is unaffected — but the gotcha
  is now documented in CLAUDE.md: always join that file by the `token` string.
  It also contains ~256 model-side tokens outside this vocab (`TIM_AGE_*`,
  `DEM_DEATH_OWN`, …).
- `HIERARCHY_SUMMARY.csv` had no generator and its `with_da` column was stale
  on 54 categories — new permanent `scripts/build_hierarchy_summary.py`,
  file regenerated.
- CLAUDE.md official-fill figure corrected (62.4% → 62.3% after round 1
  cleared 40 contradicting officials).

## 13. Audit round 5 (2026-06-15): multi-agent resolve-and-verify of the residual surface

A dynamic multi-agent workflow (`scripts/oneoff/` has no copy — it ran via the
Workflow harness; results archived to the task output) attacked every residual
unresolved/untranslated MASTER row. One **resolver** agent per category hunted
the repo's official sources for each unresolved code; one **adversarial
verifier** per category then re-opened each cited source and tried to refute the
proposal (verbatim-match + code-system check, default-reject when uncertain).
**184 confirmed, 201 confirmed genuinely unresolvable, 1 adversarially rejected.**
Every confirmed item was re-checked by hand, then applied via
`scripts/oneoff/audit_round5_fixes_20260615.py`.

### Resolved (184)
- **LAB_db07 18 of 19 remaining `[Unresolved]`** — from `db07_v1_2008.csv` (the
  v1 edition carries all 5 levels; earlier passes only loaded v2/v3). Each is a
  leading-zero-stripped 6-digit code landing on a valid sequential
  agriculture/forestry/fishing/mining title (`11200`=01.12.00 'Dyrkning af ris',
  `89100`=08.91.00 chemical/fertilizer minerals). All 18 are internally
  systematic and every one with firm-level co-occurrence agrees
  (16300→14190 1.0, 17000→15000 1.0, 89100→143000 1.0, 31200→50100 0.75).
  Treated like the round-1 `dst_db07_leading_zero` rows: da=DST v1 title,
  en/official=NACE Rev 2 class, parent re-pointed to the zero-restored class,
  basis in `description_da_alt`, confidence high (co-occ) else medium. Only
  `12110` (no clean zero-restore) stays unresolved.
- **DEM_opr 5157/5393/5223** = Palæstina/Vestbredden/Gaza from
  `DEM_statsb_dict.csv` (DEM_opr & DEM_statsb share DST landekode — 223 shared
  codes, 0 semantic conflicts). **Bug fix:** 5157's English was "Kosovo"
  (Kosovo is code 5761, not 5157).
- **EDU_course 112** empty-da filled in the category's house style
  ('Course <subject>' / 'Course: <english>'; the value IS the Danish subject).
- **EDU_field 34** translation-only ('Teknologi u.n.a.' → 'Technology, not
  further specified'; Danish unchanged).
- **LAB_disco08 5** armed-forces codes (raw/LAB_disco.csv + ISCO-08);
  **SOC_overfkod -/X** (KRIN_codebook.md); **LAB_tilstand 17100**='SU';
  **SOC_ger7 0**='Uoplyst'; **DEM_manual_bin_antefam 8** range bins (documented
  bin convention, English already present).

### Left unresolved (correctly)
201 rows confirmed unresolvable by the adversarial verifiers, each with a cited
reason: DEM_far/mor `foed_adop_1/2/99` (not in the documented SAS value set —
NOT mapped to 11/12/etc.), EDU_grade/EDU_course-abbreviations with no register
text, SOC_charge/start/victim/end and LAB_akm `type_akm_*` (model-created
indicators, not DST classifications), HEA_urgency/HEA_speciale gaps, and the
12 documented `[Unresolved]` placeholders. 1 proposal (LAB_udd
`besk_kode_nullified_1`) was adversarially **rejected** — proposed Danish
appeared in no source. LAB_akm's resolver crashed on an API false-positive;
those 3 left unresolved (model-derived, no DST source).

Net: `[Unresolved]`/`[UNMAPPED]` placeholder rows fell from 32 to 12.
