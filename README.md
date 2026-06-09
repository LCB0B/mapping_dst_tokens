# Danish Administrative Vocabulary Mappings

A hierarchical vocabulary-mapping system for the **40,465 codes** that make up
the input vocabulary of a transformer model trained on Danish administrative
and health register data (demographics, education, health, labour market, and
social/criminal justice). Every code maps to a model token ID **and** to
human-readable descriptions in Danish and English, each with a recorded source.

> **New here?** Read the **HARD RULES** at the top of [`CLAUDE.md`](CLAUDE.md)
> before editing any data, and see [`DATA_SOURCES.md`](DATA_SOURCES.md) for where
> every code comes from.

## Source of truth

[`MASTER_CATEGORY_MAPPINGS.csv`](MASTER_CATEGORY_MAPPINGS.csv) is the single
source of truth (40,465 rows). Everything under `hierarchical_vocab/MAPPINGS/`
is **generated** from it — never edit those files by hand. After changing
MASTER, regenerate:

```bash
python3 scripts/regenerate_mappings.py
```

## Repository layout

```
MASTER_CATEGORY_MAPPINGS.csv   ← source of truth (every code, description, source, prevalence)
vocab.json                     ← 40,465 code → token_id pairs (canonical)
vocab_hierarchy.json           ← hierarchical token structure
HIERARCHY_SUMMARY.csv          ← overview of all 127 categories
token_occurrences.csv          ← per-token prevalence (n_occurrences, n_people, pct_people)
input_dataset_description.csv  ← model variable → DST REGISTER:VARIABLE (authoritative)
DATA_SOURCES.md                ← consolidated "where the data comes from" guide
SOURCE_CATALOG.csv             ← per-category provenance table (generated)
CLAUDE.md                      ← HARD RULES + deep domain knowledge

hierarchical_vocab/
  DEM/ EDU/ HEA/ LAB/ SOC/ SPECIAL/   per-category code definitions (code, prefix, database, value, token_id)
  MAPPINGS/                           per-category descriptions  ← GENERATED from MASTER
  MISSING/                            templates for events needing manual descriptions

lookup_dictionaries/   ← official DST dictionaries (*_dict.csv + .pt; *_quantile_dict.csv income bins)  [tier-1 source]
raw/                   ← raw DST classification files, SAS format defs, intl reference files (domain-prefixed)
  dst_downloads/       ← downloaded standards & DST extracts (see raw/dst_downloads/SOURCES.md)
crosswalks/
  empirical/           ← SOCIO_GL→SOCIO13 and DB07→DB93 data-driven recovery crosswalks
  edu/                 ← AUDD/UDD ↔ DISCED crosswalk tables + programme-length mapping
scripts/               ← 5 permanent utilities (regenerate, build_hierarchies, …, build_source_catalog)
  oneoff/              ← historical one-off fixer scripts (kept for reproducibility)
  worklists/           ← intermediate translation/work files
docs/                  ← notes.md, QC_REPORT.md, SOURCE_AUDIT.md, SOCIO_GL_README.md, plots
archive/               ← non-authoritative reference (older vocab_2.json, audit snapshots)
```

## Coverage

| Domain | Categories | Codes | English | Danish | Official EN* |
|--------|-----------:|------:|--------:|-------:|-------------:|
| DEM — Demographics | 25 | 1,239 | 100% | 97% | 30% |
| EDU — Education | 18 | 8,020 | 100% | 96% | 0% |
| HEA — Health | 19 | 23,178 | 100% | 99% | 96% |
| LAB — Labour market | 41 | 6,622 | 100% | 99% | 37% |
| SOC — Social / criminal | 23 | 1,401 | 100% | 98% | 0% |
| SPECIAL — Model tokens | 1 | 5 | 100% | — | — |
| **Total** | **127** | **40,465** | **100%** | **99%** | — |

\* *Official EN* = English traceable to an international standard
(`description_en_official`). It is sparse by design — most domains have no
international equivalent. Use `description_en` for broad coverage and treat the
`*_source` columns as the quality signal.

## Where the data comes from

Provenance is documented in three complementary places:

- [`DATA_SOURCES.md`](DATA_SOURCES.md) — narrative, per-domain: which DST
  register, which source files, which international standards, known gotchas.
- [`SOURCE_CATALOG.csv`](SOURCE_CATALOG.csv) — machine-readable, one row per
  category: DST register, source files, standard, and coverage.
- [`input_dataset_description.csv`](input_dataset_description.csv) — the
  authoritative model variable → DST `REGISTER:VARIABLE` map.

Per-row provenance lives in MASTER's `source`, `description_en_source`, and
`description_en_official_source` columns.

## Key classification systems

- **ICD-10 / ICD-8** — medical diagnoses (`D`-prefixed = ICD-10; numeric-only = legacy ICD-8)
- **ATC** — Anatomical Therapeutic Chemical medication codes
- **DISCO-08 / DISCO-88** — occupations (based on ISCO); `LAB_disco` is mixed-era
- **DB07 / NACE / DB93 / BRANCHE-77** — industries (DB07 = NACE Rev.2; *not* an occupation code)
- **DISCED-15** — education classification (based on ISCED)
- **SOCIO13 / SOCIO_GL** — socio-economic status
- **GER7** — criminal offence codes
- **ISO-3166** — countries / citizenship

See [`CLAUDE.md`](CLAUDE.md) for the domain gotchas (DB07 ≠ DISCO-07, DISCO
version drift, HEA_speciale regional §2-aftaler, the LMDB VOLTYPECODE units,
and the `.0` float bug).

## MASTER columns worth knowing

- `code`, `token_id`, `prefix`, `variable`, `value`, `category`
- `description_da` (authoritative Danish), `description_en` (best English),
  `description_en_official` (+`*_official_source`, only when from a standard)
- `source`, `description_en_source` — per-row provenance
- `n_occurrences`, `n_people`, `pct_people` — prevalence across the dataset
- `program_group`, `is_primary_code` (EDU) — filter `is_primary_code=True` to
  collapse version-renumbered education variants

## Usage

```python
import json, csv

# token IDs
vocab = json.load(open("vocab.json"))                 # code -> token_id

# descriptions + provenance
with open("MASTER_CATEGORY_MAPPINGS.csv", newline="", encoding="utf-8") as f:
    master = {row["code"]: row for row in csv.DictReader(f)}

m = master["DEM_kom_101"]
print(m["description_en"], "|", m["source"])           # København | CSV:DEM_kom
```

> **Note on numeric codes:** upstream values serialized with a trailing `.0`
> must be normalised before lookup: `s = str(v); s = s[:-2] if s.endswith('.0') else s`
> (see the `.0` float bug in [`CLAUDE.md`](CLAUDE.md)).

## Documentation index

| File | What it covers |
|------|----------------|
| [`CLAUDE.md`](CLAUDE.md) | HARD RULES for sourcing + deep domain knowledge + schema |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | Consolidated provenance guide |
| [`SOURCE_CATALOG.csv`](SOURCE_CATALOG.csv) | Per-category source table |
| [`docs/notes.md`](docs/notes.md) | Decision log / domain reasoning |
| [`docs/QC_REPORT.md`](docs/QC_REPORT.md) | Integrity audit & recovery provenance |
| [`docs/SOURCE_AUDIT.md`](docs/SOURCE_AUDIT.md) | Per-category source verification & corrections |
| [`docs/SOCIO_GL_README.md`](docs/SOCIO_GL_README.md) | Empirical crosswalk methodology |
