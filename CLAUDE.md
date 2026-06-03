# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## HARD RULES — READ FIRST

**Do NOT infer, guess, or pattern-match Danish code meanings from LLM knowledge.**
This has caused real damage (hallucinated SOCIO_gl labels, wrong DB07
5-digit mappings) that then got committed as if authoritative. Specifically:

1. **Never invent a Danish or English label for a code** just because the
   numeric range or similar-looking codes suggest a plausible meaning. If you
   don't know a code from a documented source, leave it empty or mark it
   `[Unresolved <category> code: <value>]` with `confidence_level=low`.
2. **Always cite the source** in `description_en_source` when filling a
   description: file path (e.g. `raw/LAB_nace.txt`, `mapping/lookup_dictionaries/LAB_db07_dict.pt`)
   or URL (e.g. `dst.dk/.../socstil-kode`).
3. **Sources to try, in priority order:**
   - Files in `mapping/lookup_dictionaries/` (`.pt` and `.csv`) — highest confidence, official DST dicts
   - Files in `raw/` — raw DST classification files (`LAB_nace.txt`, `atc.csv`, SAS format definitions, PDF publications)
   - Files in `mapping/` (e.g. `DISCO_CODES.txt`, `13_to_7_mapping.txt`)
   - DST website lookups via WebFetch/WebSearch:
     - `https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/` — classification nomenclatures
     - `https://www.dst.dk/da/Statistik/dokumentation/Times/` — TIMES variable documentation
     - `https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-arbejdsmarked/` — labour market variables (ARBSTIL, SOCSTIL, NYARB)
     - `https://www.dst.dk/da/Statistik/dokumentation/Times/ida-databasen/` — IDA database variables (PSTILL, STILL, etc.)
     - `https://www.dst.dk/da/Statistik/udgivelser/` — historical publications (Statistisk Årbog, SOCIO 1997, DB07)
     - Publication PDFs via `https://www.dst.dk/pubfile/<id>/<slug>` — save to `raw/` and parse with `pypdf`
   - Eurostat / international: NACE Rev 2 (EU), ICD-10 (WHO), ATC (WHO), ISCO-08 (ILO)
4. **If none of the above has it, say so.** Do not fill the field. A
   placeholder `[Unresolved ... code: X]` plus `confidence_level=low` is the
   correct output, not a plausible Danish sentence you made up.
5. **Older classifications (pre-1996) often aren't web-indexed.** When a DST
   variable has a version history going back to 1980 (ARBSTIL, NYARB,
   SOCIO_KODE older versions), the value sets live in internal DDI/CSV
   metadata accessible only via DST Forskningsservice. If you can't retrieve
   them, mark the codes unresolved and tell the user to contact DST or
   retrieve them from the original `.pt` file the vocab was built from.

## Repository Overview

Hierarchical vocabulary mapping system for **40,465 codes** used in Danish administrative register data (health, education, labor, demographics, social/criminal justice). Each code maps to a token ID in a transformer model vocabulary. (Originally 41,201; 736 `.0` float-duplicate entries were removed — see "The `.0` float bug" below.)

## Architecture

**MASTER_CATEGORY_MAPPINGS.csv** is the single source of truth. All per-category MAPPINGS/ files are regenerated from it via `scripts/regenerate_mappings.py`. Never edit MAPPINGS/ files directly — edit MASTER and regenerate.

## File Inventory

### Root — Core Data
| File | What it is | Why it's here |
|------|-----------|---------------|
| `vocab.json` | Vocabulary: 40,465 code-to-token_id pairs (token IDs preserved from the original; 736 `.0` holes) | Source of truth for token IDs |
| `MASTER_CATEGORY_MAPPINGS.csv` | Every code with descriptions, sources, confidence (40,465 rows) | Central data file, source of truth for descriptions |
| `QC_REPORT.md` | Audit report: integrity, the MASTER↔MAPPINGS reconciliation, gap inventory | Provenance of the 2026-06 recovery |
| `notes.md` | Working decision log (DB07≠DISCO-07, DISCO version-drift, HEA_speciale §2-aftaler, `.0` bug, income rewrites) | Domain reasoning behind the data |
| `HIERARCHY_SUMMARY.csv` | Overview of all 127 categories with counts | Quick reference for category structure |
| `README.md` | Project description and usage | Documentation |
| `.gitignore` | Git ignore rules | Excludes one-off scripts, virtual envs, intermediate files |

### `scripts/` — Permanent Utilities
| File | Purpose |
|------|---------|
| `regenerate_mappings.py` | Regenerate MAPPINGS/ files from MASTER (emits all description_* columns) |
| `build_hierarchies.py` | Fill description gaps from dict files + build parent_code/hierarchy_level |
| `add_language_columns.py` | Split descriptions into description_da/description_en columns |
| `reconcile_master_from_mappings.py` | Recover provenance/official columns into MASTER when it drifts from MAPPINGS (used in the 2026-06 recovery) |

The remaining `scripts/*.py` (e.g. `fix_*`, `apply_*`, `audit_*`, `clean_*`,
`crosswalk_*`, `fill_*`, `retranslate_*`) are **one-off fixers** kept for
provenance/reproducibility of specific transformations — not part of the
regular regeneration pipeline. See `notes.md` for what each accomplished.

### `hierarchical_vocab/` — Per-Category Data

#### Vocabulary Files (`DEM/`, `EDU/`, `HEA/`, `LAB/`, `SOC/`, `SPECIAL/`)
One CSV per category. Columns: `code, prefix, database, value, token_id`. These define which codes belong to each category.

- **DEM/** (25 categories): Demographics — municipalities (kom), countries (statsb, opr), birth data, family structure, immigration/emigration events
- **EDU/** (18 categories): Education — AUDD post-secondary, UDD higher ed, DISCED classification, grades, ECTS, courses
- **HEA/** (19 categories): Health — ICD-10 diagnoses, ICD-8 codes (numeric values without D prefix), ATC medications, medical specialties, procedure codes (DDK, DW, DWG, DWK, GA, GI, GP, L, MG, ML, PK, ST, TU)
- **LAB/** (41 categories): Labor market — DISCO/DISCO-08 occupations, DB07/NACE/branche industries, socio-economic status, income quantiles, employment
- **SOC/** (23 categories): Social/criminal — GER7 offense codes, legal paragraphs (pgf), sentence types, placement types
- **SPECIAL/** (1 category): Model tokens [PAD], [CLS], [SEP], [UNK], [MASK]

#### `MAPPINGS/` (127 files)
Per-category mapping files with descriptions and sources. Columns: `code, prefix, database, value, description, description_da, description_da_alt, description_en, description_en_official, description_en_official_source, description_en_source, source, confidence, language, parent_code, hierarchy_level`. **Generated from MASTER** — do not edit directly.

#### `MISSING/` (6 files)
Templates for categories needing manual descriptions (Birth, Death, Immigration, Emigration, unknown events).

### `mapping/` — Original Source Data
| Path | What it is |
|------|-----------|
| `DISCO_CODES.txt` | Danish occupational classification codes (source for LAB_disco) |
| `13_to_7_mapping.txt` | GER 13-digit to 7-digit offense code mapping (source for SOC_ger7) |
| `lookup_dictionaries/*.csv` | Extracted classification dictionaries (40+ files) — richest reference data per category |
| `lookup_dictionaries/*.pt` | Original PyTorch dictionary files (16 files) — binary source for the CSV extractions |
| `edu_code_related/*.parquet` | AUDD-to-DISCED crosswalk tables (4 files) |
| `edu_len_mapping.parquet` | Education program length mapping |
| `raw/AUDD_PRIA_L1LX_K.txt` | Raw education priority data |

### `raw/` — Classification Reference Files
| File | What it is |
|------|-----------|
| `atc.csv` | ATC medication classification (222KB, comprehensive reference) |
| `nace.txt` | NACE/DB93 industry codes 1992-2007 (partial English translation) |
| `LAB_nace.txt` | NACE/DB93 industry codes (clean Danish version) |
| `branche77.txt` | Danish industry codes (branche format) |
| `disco.csv` | DISCO occupation codes |
| `csv_da.csv` | Danish CSV classification data |
| `Speciale_koder_med_tekst_samt_vejledning.csv` | Medical specialty codes with text and guidance (2.5MB) |
| `Special2.txt` | HEA_speciale specialty mapping reference |
| `groups_of_medicines_text.txt` | ATC medicine group descriptions |
| `speciale_instructions.txt` | HEA_speciale 6-digit structure documentation |
| `bin_instructions.txt` | Manual mapping instructions for bins/quantiles |
| `DEM_*.txt`, `DEN_*.txt` | Demographic category SAS format definitions (civst, far_foed_adop, fm_mark, mor_foed_adop) |
| `EDU_field.txt` | Education field classification |
| `SOC_*.txt` | Social/criminal SAS format definitions (afgtypko, bstrfkod, frakkod, haendelse, loeslkod, pgf, samtykke) |
| `LAB_*.txt` | Labor SAS format definitions (fravaer, stoette, tilstand_kode) |
| `far-foed-adop.txt`, `mor-foed-adop.txt` | Father/mother birth/adoption event codes |

## MASTER_CATEGORY_MAPPINGS.csv Schema

```
code             — Unique code (e.g., HEA_ICD10_DA001)
token_id         — Transformer vocabulary token ID
prefix           — Domain: DEM, EDU, HEA, LAB, SOC, SPECIAL
variable         — Sub-classification (e.g., ICD10, disco, kom). Called "database" in MAPPINGS/ files.
value            — The specific code value
category         — Full category name (prefix_variable)
description      — Legacy combined human-readable description (Danish or English)
description_da   — Danish description, AUTHORITATIVE: follows the training-data semantics
description_da_alt— Alternative regional meanings (only the ~5 HEA_speciale codes with
                   conflicting §2-aftale semantics across regions — see HEA_speciale below)
description_en   — Best-available English: translated from Danish OR from an intl. classification (100% filled)
description_short — Short label variant
description_en_official        — English ONLY when traceable to an intl. standard (WHO/NACE/ISCO/ISO-3166/DST-SSR);
                                 empty when not reliably available (62.4% filled)
description_en_official_source — Authority for the official English: who-icd10, who-atc, nace2,
                                 nace2-crosswalk, isco08, isco08-crosswalk, isco88, iso3166, dst-ssr-specialty
description_en_source          — Provenance tag for description_en: the above + translated, copy-of-da, dst_times_<var>
source           — Where the (legacy) description came from
mapped           — Whether description exists (True/False)
total_codes / mapped_codes / mapping_percentage — per-category summary stats (may be empty)
primary_source   — Primary data source for this category (may be empty)
confidence_level — highest/high/medium/low. NOTE: sparsely populated (~7%); real provenance/quality
                   signal lives in `source`, `description_en_source`, and `description_en_official_source`.
parent_code      — Parent code in hierarchy (empty for flat categories or top-level)
hierarchy_level  — Level name in hierarchy (e.g., chapter, block, category, subcategory)
```

Consumers needing guaranteed accuracy should filter on `description_en_official`.
Consumers needing broad coverage should use `description_en` and treat
`description_en_source` as a quality signal. `MASTER` is the single source of
truth; if it ever diverges from MAPPINGS/, see `scripts/reconcile_master_from_mappings.py`.

## Key Domain Knowledge

### ICD Codes in HEA_ICD10
- Codes with `D` prefix (e.g., DA001, DG4732) are **ICD-10** with Danish chapter prefixes
- Numeric-only codes (e.g., 00009, 01101) are **ICD-8** codes — a legacy classification
- ICD-8 placeholders were filled; HEA_ICD10 official English now comes from WHO ICD-10 2019.

### Remaining `[Unresolved]` codes (70 total)
Only two categories still carry `[Unresolved …]` placeholders — both are the
historically-damaged legacy codes (see HARD RULES). **Do not guess them:**
- **`LAB_db07` 5-digit (36)** — e.g. `11100`…`89900`. DST DB07 is 6-digit (`011100`);
  the leading-zero mapping is ambiguous and `LAB_db07_dict.csv` (3-digit) lacks them.
  Needs DST Forskningsservice or the original `.pt` the vocab was built from.
- **`LAB_socio` `gl_*` (34)** — old SOCIO ("SOCIO_gl"). Only `raw/dst_socio_1997.pdf`
  covers it; extraction is ambiguous (1- vs 2-digit, socioeconomic vs occupation).
  Resolve only via human-verified reading of that PDF.

### Hierarchical Classifications
Eight categories have hierarchical parent-child structure encoded in `parent_code` and `hierarchy_level` columns:
HEA_ICD10, HEA_ATC, LAB_disco, LAB_disco08, LAB_db07, LAB_nace, EDU_disced, SOC_ger7

Total hierarchy relationships built: ~21,500 codes with parent_code set.

### Confidence / provenance
The `confidence_level` column is only sparsely populated (~7% of rows). The
real, per-row provenance signal lives in the **source columns**:
- `source` — origin of the legacy `description` (e.g. `CSV:HEA_ICD10`, `raw_lab_nace`,
  `dual_source_special2_spec6`; `none|generated`/`generated_pattern` = weak/unsourced)
- `description_en_source` — provenance of `description_en` (`who-icd10`, `dst_times_<var>`,
  `dst-ssr-specialty`, `isco08`, `translated`, `copy-of-da`, …)
- `description_en_official_source` — authority for `description_en_official` (filled only
  when traceable to an international/DST standard)

Rough quality tiers, highest→lowest: PyTorch lookup dictionaries
(`mapping/lookup_dictionaries/`, ~36k official mappings) > DISCO/SAS format
definitions > international standards (WHO/NACE/ISCO) > generated patterns >
unverified/placeholder.

### Danish classification gotchas (see `notes.md` for full detail)
- **DB07 ≠ DISCO-07.** The `07` in DB07 = year 2007 (NACE Rev 2 adoption). DB07/NACE/
  branche are **industries**; DISCO-08/DISCO are **occupations**. There is no "DISCO-07".
- **`LAB_disco` is mixed-era.** Its rows are a mix of DISCO-88 and DISCO-08 numbering;
  the same 4-digit code means different occupations across versions. Official English is
  reconciled per-row via name-based crosswalk (`scripts/crosswalk_lab_disco.py`) —
  `description_en_official_source` tags whether ISCO-08 or ISCO-88 was used. Never overwrite
  `description_da` to match an "official" label; the Danish is the training-data ground truth.
- **HEA_speciale regional §2-aftaler.** 6-digit = specialty(2)+procedure(4); procedures ≥4000
  are regional agreements. A few codes mean different things in different regions; the primary
  meaning is in `description_da` (tagged with the region) and alternatives in `description_da_alt`.
- **The `.0` float bug.** vocab originally had 769 `.0`-suffixed keys (736 dup twins removed,
  33 orphans renamed to int). Any upstream numeric code serialized with a trailing `.0` must be
  normalised before tokenizer lookup: `s = str(v); s = s[:-2] if s.endswith('.0') else s`.

## Common Operations

### Regenerate MAPPINGS/ from MASTER
```bash
python3 scripts/regenerate_mappings.py
```

### Find a code's description
```bash
grep "DEM_kom_101" MASTER_CATEGORY_MAPPINGS.csv
# → København
```
