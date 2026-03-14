# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Repository Overview

Hierarchical vocabulary mapping system for 41,201 codes used in Danish administrative register data (health, education, labor, demographics, social/criminal justice). Each code maps to a token ID in a transformer model vocabulary.

## Architecture

**MASTER_CATEGORY_MAPPINGS.csv** is the single source of truth. All per-category MAPPINGS/ files are regenerated from it via `scripts/regenerate_mappings.py`. Never edit MAPPINGS/ files directly — edit MASTER and regenerate.

## File Inventory

### Root — Core Data
| File | What it is | Why it's here |
|------|-----------|---------------|
| `vocab.json` | Original vocabulary: 41,201 code-to-token_id pairs | Source of truth for token IDs |
| `MASTER_CATEGORY_MAPPINGS.csv` | Every code with description, source, confidence (41,201 rows) | Central data file, source of truth for descriptions |
| `HIERARCHY_SUMMARY.csv` | Overview of all 127 categories with counts | Quick reference for category structure |
| `README.md` | Project description and usage | Documentation |
| `.gitignore` | Git ignore rules | Excludes one-off scripts, virtual envs, intermediate files |

### `scripts/` — Permanent Utilities
| File | Purpose |
|------|---------|
| `regenerate_mappings.py` | Regenerate MAPPINGS/ files from MASTER |
| `build_hierarchies.py` | Fill description gaps from dict files + build parent_code/hierarchy_level |
| `add_language_columns.py` | Split descriptions into description_da/description_en columns |

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
Per-category mapping files with descriptions and sources. Columns: `code, prefix, database, value, description, source, confidence, language`. **Generated from MASTER** — do not edit directly.

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
code            — Unique code (e.g., HEA_ICD10_DA001)
token_id        — Transformer vocabulary token ID
prefix          — Domain: DEM, EDU, HEA, LAB, SOC, SPECIAL
variable        — Sub-classification (e.g., ICD10, disco, kom). Called "database" in MAPPINGS/ files.
value           — The specific code value
category        — Full category name (prefix_variable)
description     — Human-readable description (Danish or English)
description_da  — Danish description (empty if English-only)
description_en  — English description (empty if Danish-only)
source          — Where the description came from
mapped          — Whether description exists (True/False)
total_codes     — Total codes in this category (summary stat, may be empty)
mapped_codes    — Mapped codes in this category (summary stat, may be empty)
mapping_percentage — Coverage percentage (summary stat, may be empty)
primary_source  — Primary data source for this category (may be empty)
confidence_level — highest/high/medium/low
parent_code     — Parent code in hierarchy (empty for flat categories or top-level)
hierarchy_level — Level name in hierarchy (e.g., chapter, block, category, subcategory)
```

## Key Domain Knowledge

### ICD Codes in HEA_ICD10
- Codes with `D` prefix (e.g., DA001, DG4732) are **ICD-10** with Danish chapter prefixes
- Numeric-only codes (e.g., 00009, 01101) are **ICD-8** codes — a legacy classification
- 556 ICD-8 codes currently have placeholder descriptions

### Hierarchical Classifications
Eight categories have hierarchical parent-child structure encoded in `parent_code` and `hierarchy_level` columns:
HEA_ICD10, HEA_ATC, LAB_disco, LAB_disco08, LAB_db07, LAB_nace, EDU_disced, SOC_ger7

Total hierarchy relationships built: ~21,500 codes with parent_code set.

### Confidence Levels
- **highest**: PyTorch dictionaries (36,092 mappings from official Danish admin classifications)
- **high**: DISCO codes, SAS format definitions
- **medium**: External APIs, research-enhanced, generated patterns
- **low**: Unverified or placeholder descriptions

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
