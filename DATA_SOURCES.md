# Data Sources & Provenance

**Where every code in this repository comes from.** This is the consolidated
provenance guide. For the per-category machine-readable table see
[`SOURCE_CATALOG.csv`](SOURCE_CATALOG.csv); for the deep domain rules and the
non-negotiable sourcing policy see [`CLAUDE.md`](CLAUDE.md).

> **Sourcing policy (summary of the [CLAUDE.md](CLAUDE.md) HARD RULES):** code
> meanings are *never* inferred from the look of a number. They come from a
> documented source — a DST lookup dictionary, a raw classification file, an
> international standard, or official DST documentation — and that source is
> recorded per row. Where no source exists, the code is left
> `[Unresolved …]` with `confidence_level=low` rather than guessed.

---

## 1. The provenance chain

The codes are the input vocabulary of a transformer trained on Danish
administrative register data. Each value travels through four layers:

```
DST register variable            input_dataset_description.csv   "which register"
        │                        (model variable → REGISTER:VARIABLE)
        ▼
token id                         vocab.json                      "the integer"
        │
        ▼
code meaning (da / en)           lookup_dictionaries/ , raw/ ,   "what it means"
        │                        international standards, DST docs
        ▼
per-row provenance               MASTER_CATEGORY_MAPPINGS.csv    "how we know"
                                 (source / *_source columns)
```

1. **Which register** — `input_dataset_description.csv` maps every model
   variable to its DST `REGISTER:VARIABLE` (e.g. `BEF:OPR_LAND`,
   `AKM:SOCIO13`, `LMDB:VOLUME`+`VOLTYPECODE`, `LPR_ADM:AKTIONSDIAGNOSE`,
   `KRAF:AFG_GER7`). This is the authoritative model→register document.
2. **The integer** — `vocab.json` holds the 40,465 code→token_id pairs used by
   the model. (`archive/vocab_2.json` is a *different, older* vocabulary kept
   only for reference — see [§6](#6-archived--non-authoritative).)
3. **What it means** — descriptions were resolved from the source tiers below,
   in priority order.
4. **How we know** — every row in `MASTER_CATEGORY_MAPPINGS.csv` records its
   provenance in three columns: `source`, `description_en_source`,
   `description_en_official_source`.

### Source tiers (highest confidence first)

| Tier | Location | What it is |
|------|----------|-----------|
| 1 | `lookup_dictionaries/*.pt` (+ `.csv` extractions) | Official DST PyTorch dictionaries the vocab was built from (~36k mappings) |
| 2 | `raw/` | Raw DST classification exports + SAS format definitions + international reference CSVs |
| 3 | international standards | WHO ICD-10 / WHO ATC / NACE Rev.2 / ISCO-08 / ISCO-88 / ISO-3166 |
| 4 | DST web documentation | TIMES variable docs, esundhed (LMDB), historical publication PDFs |
| 5 | `crosswalks/empirical/` | Data-driven recovery for historically undocumented codes |

The `description_en_official` / `description_en_official_source` columns are
filled **only** for tier-3 international standards — consumers who need
guaranteed accuracy should filter on those.

---

## 2. Source directories at a glance

| Directory | Role | Tier |
|-----------|------|------|
| `lookup_dictionaries/` | Extracted DST dictionaries (`*_dict.csv` + `.pt` binaries; `*_quantile_dict.csv` for binned income/wealth) | 1 |
| `raw/` | Raw DST classification files, SAS format defs, and international reference files (all domain-prefixed) | 2–3 |
| `raw/dst_downloads/` | Downloaded standards & DST extracts (ICD-10 WHO, ATC WHO, ISCO, NACE, SSR fee schedules, …); see `raw/dst_downloads/SOURCES.md` | 3–4 |
| `crosswalks/empirical/` | `SOCIO_GL→SOCIO13` and `DB07→DB93` recovery crosswalks built from longitudinal sequences | 5 |
| `crosswalks/edu/` | AUDD/UDD ↔ DISCED education crosswalk tables + programme-length mapping | 2 |

---

## 3. Per-domain provenance

### DEM — Demographics
- **Registers:** mostly `BEF:*` (population: `OPR_LAND`, `STATSB`, `CIVST`,
  `FAMILIE_TYPE`, `FM_MARK`, `IE_TYPE`, `ANT*F` household counts), `BEFADR:KOM`
  (municipality), `FERTILITETSDATABASEN:*` (birth weight/length, parental
  adoption codes), `LIFELINES:*` (birth date, sex, migration events),
  `FAMILY_RELATIONS:RELATION` (births/deaths/siblings).
- **Sources:** `lookup_dictionaries/DEM_{kom,opr_land,statsb,mor_foed_adop}_dict.*`;
  raw SAS format defs `raw/DEM_{civst,far_foed_adop,fm_mark,mor_foed_adop}.txt`
  (+ English variants `*_en.txt`). Countries/citizenship carry official
  **ISO-3166** English.
- **Notes:** municipality codes include modern Greenlandic communes
  (955–960); a few `DEM_kom`/`DEM_opr` codes remain `[Unresolved]`. Created
  event/indicator categories (`DEM_Birth/Death/Indvandret/Udvandret`,
  `DEM_manual`, `DEM_n`, `DEM_unknown`) are derived, not register value sets.

### EDU — Education
- **Registers:** `KOTRE:{UDD,AUDD,UDEL,TILG_ART,AFG_ART}` and
  `UDG/UDKV:AUDD` (enrolments, qualifications, diplomas);
  `UDFK/UDGK:*` and `UDD_KARAKTER_UNIVID_FAG:*` (grades, courses, ECTS);
  **DISCED-15** subject/major areas; `UDD_TRIVSEL_*` (wellbeing);
  `UDD_NATTEST_*` (national tests); `UDD_FOLKESKOLE_FRAVAER_STIL:*` (absences).
- **Sources:** `lookup_dictionaries/EDU_{audd,udd,disced,afg_art}_dict.*`;
  `raw/EDU_field.txt`, `raw/EDU_audd_pria_l1lx_k.txt`; AUDD/UDD↔DISCED
  crosswalks in `crosswalks/edu/`.
- **Notes:** EDU codes are reissued across classification versions; MASTER's
  `program_group` + `is_primary_code` columns collapse version-renumbered
  variants. Absence/ECTS/grade bins are generated bin labels.

### HEA — Health
- **Registers:** `LPR_ADM:AKTIONSDIAGNOSE` (5-digit Danish ICD-10),
  `LMDB:ATC` (medications), `LMDB:VOLUME`+`VOLTYPECODE` (drug quantity unit
  bins), `SYSI/SSSY:SPECIALE` (doctor-visit specialty/procedure billing),
  `LPR_ADM:{INDM,PATTYPE}` (urgency, patient type).
- **Sources:** `lookup_dictionaries/HEA_ICD10_dict.*`,
  `HEA_atc_dict_{comprehensive,downloaded,from_raw,manual}.csv`,
  `HEA_spec2_dict.*`; `raw/HEA_atc.csv`, `raw/HEA_icd8.txt` (legacy ICD-8),
  `raw/HEA_special2.txt`, `raw/HEA_speciale_koder_med_tekst_samt_vejledning.csv`,
  `raw/HEA_groups_of_medicines_text.txt`. Official English from **WHO ICD-10
  (2019)** and **WHO ATC**.
- **Notes:** the `HEA_{DDK,DW,DWG,DWK,GA,GI,GP,L,MG,ML,PK,ST,TU}` and bare
  `HEA_` categories are **LMDB VOLTYPECODE units**, *not* procedure codes
  (source `esundhed:lmdb_voltypecode`). `HEA_speciale` 6-digit codes are
  specialty+procedure billing codes with regional §2-aftale variants; English
  was clinically re-translated (`opus-4-8-medical`). Numeric-only `HEA_ICD10`
  values are ICD-8.

### LAB — Labour market
- **Registers:** occupations `AKM:DISCO08_*`/`AKM:DISCO_*` + `AMRUN:DISCO_KODE`;
  industries `AKM:NACE_DB07_13` (DB07), `AKM:NACE_13` (DB93),
  `AKM:BRANCHE_77` + `AMRUN:ARB_HOVED_BRA_DB07`; socio-economic
  `AKM:SOCIO13` / `AKM:SOCIO_GL` + `AMRUN:SOC_STATUS_KODE`; employment status
  `AMRUN:{TILSTAND_KODE_AMR,FRAVAER_BESK_KODE,STOETTE_BESK_KODE}`; and the
  large block of `IND:*` income/tax/wealth variables (binned within years).
- **Sources:** `lookup_dictionaries/LAB_{db07,disco08,nace,branche,socio13,soc_status}_dict*.csv`,
  per-variable `LAB_*_quantile_dict.csv` for income bins;
  `raw/LAB_nace.txt` (Danish DB93) + `raw/LAB_nace_en.txt` (English),
  `raw/LAB_branche77.txt`, `raw/LAB_disco.csv`, `raw/LAB_disco_codes.txt`,
  `raw/LAB_tilstand_kode.txt`. Official English from **NACE Rev.2**,
  **ISCO-08** and **ISCO-88**.
- **Notes:** `DB07 ≠ DISCO-07` — DB07 is industry (NACE Rev.2, year 2007),
  DISCO is occupation; there is no "DISCO-07". `LAB_disco` is mixed DISCO-88/-08
  numbering (official English reconciled per row). `LAB_socio` `gl_*`
  (1976–1990) and several 5-digit `LAB_db07` codes were recovered empirically —
  see `crosswalks/empirical/` and `docs/SOCIO_GL_README.md`.

### SOC — Social / criminal justice
- **Registers:** offence codes `*_GER7` shared across
  `KRAF/KRKO/KRMS/KRSI/KROF/KRIN`; sanction & sentence
  `KRAF:AFG_{AFGTYPKO,UBSTRFLG,BSTRFLG,BETBKOD,BOEDEBLB,DAGBO*,FRAKKOD,FRAKBKOD,FRAK*}`;
  incarceration `KRIN:IND_{FGSLKOD,OVERFKOD,BSTRFKOD,LOESLKOD}`; child welfare
  `BUAF:{SAMTYKKE,ANSTED_KLAS,HAENDELSE}` and `BUFO:PFG`.
- **Sources:** `lookup_dictionaries/SOC_{ger7,ansted_klas,pgf}_dict.*`;
  raw SAS format defs `raw/SOC_{afgtypko,bstrfkod,frakkod,haendelse,loeslkod,pgf,samtykke}.txt`,
  `raw/SOC_ger7_13_to_7_mapping.txt`. Many SOC categories were verified/corrected
  against DST TIMES documentation — see `docs/SOURCE_AUDIT.md`.
- **Notes:** several SOC categories previously held machine-translation or
  hallucinated meanings (frakkod, frakbkod, fgslkod, haendelse, afgtypko) and
  were corrected to verbatim DST text; the audit trail is in `docs/SOURCE_AUDIT.md`.
  Created indicators (`SOC_start/end/charge/victim`) have no register value set.

### SPECIAL
- The five model tokens `[PAD] [CLS] [SEP] [UNK] [MASK]` — not register-derived.

---

## 4. Reading the per-row provenance columns

| Column | Meaning | Example values |
|--------|---------|----------------|
| `source` | origin of the legacy `description` | `CSV:HEA_ICD10`, `raw_lab_nace`, `dual_source_special2_spec6`, `empirical_crosswalk_socio13`, `none\|generated` (weak) |
| `description_en_source` | how `description_en` was produced | `who-icd10`, `dst_times_<var>`, `dst-ssr-specialty`, `isco08`, `translated`, `copy-of-da`, `opus-4-8-medical` |
| `description_en_official_source` | authority for `description_en_official` | `who-icd10`, `who-atc`, `nace2`, `nace2-crosswalk`, `isco08`, `isco88`, `iso3166`, `dst-ssr-specialty` (blank when no standard applies) |

`confidence_level` is only sparsely populated — the **source columns are the
real per-row quality signal**.

---

## 5. Empirical crosswalks (`crosswalks/empirical/`)

Two historically-damaged blocks had no public value set and were recovered
data-driven from longitudinal sequences (see `docs/SOCIO_GL_README.md` and
`docs/SOURCE_AUDIT.md`):

- **`socio_gl_crosswalk_empirical.csv`** — `LAB_socio` `gl_*` (1976–1990)
  mapped to modern SOCIO13 via per-person scheme-transition tallies
  (`source=empirical_crosswalk_socio13`). 49/51 recovered.
- **`industry_crosswalk_empirical.csv`** — 5-digit `LAB_db07` low-division
  codes mapped to DB93/NACE via firm co-occurrence
  (`source=empirical_industry_crosswalk`). 23/42 recovered.

The remaining ~32 `[Unresolved]` codes are listed in `CLAUDE.md` — do not guess them.

---

## 6. Archived / non-authoritative

`archive/` holds reference material that must **not** be treated as current:

- `vocab_2.json` — an older/alternate vocabulary (40,697 keys; token IDs differ
  from the canonical `vocab.json`). Kept for reference only.
- `translation_en_audit.csv`, `translation_audit_report.csv` — outputs of
  one-off English-translation audits.
- `translation_qc_report.csv.<date>` — historical QC snapshot.

---

## 7. See also

- [`SOURCE_CATALOG.csv`](SOURCE_CATALOG.csv) — per-category table (register, source files, standard, coverage). Regenerate with `python3 scripts/build_source_catalog.py`.
- [`input_dataset_description.csv`](input_dataset_description.csv) — model variable → DST `REGISTER:VARIABLE`.
- [`CLAUDE.md`](CLAUDE.md) — sourcing HARD RULES + deep domain knowledge.
- [`docs/SOURCE_AUDIT.md`](docs/SOURCE_AUDIT.md) — per-category source verification & hallucination corrections.
- [`docs/notes.md`](docs/notes.md) — decision log (DB07≠DISCO, DISCO version drift, §2-aftaler, the `.0` bug).
- [`docs/QC_REPORT.md`](docs/QC_REPORT.md) — integrity audit & recovery provenance.
- [`docs/SOCIO_GL_README.md`](docs/SOCIO_GL_README.md) — empirical crosswalk methodology.
