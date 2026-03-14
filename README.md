# Danish Administrative Vocabulary Mappings

Hierarchical vocabulary mapping system for 41,201 codes used in Danish administrative and health register data. Maps token IDs from a transformer model vocabulary to human-readable descriptions in Danish and English.

## Structure

- **`vocab.json`** — Original vocabulary (41,201 token-to-ID mappings)
- **`MASTER_CATEGORY_MAPPINGS.csv`** — Central data file: every code with description, source, and confidence (41,201 rows)
- **`HIERARCHY_SUMMARY.csv`** — Overview of all 127 categories
- **`hierarchical_vocab/`** — Per-category CSV files organized by domain prefix
  - `DEM/` — Demographics (municipalities, countries, birth data, family)
  - `EDU/` — Education (DISCED, AUDD, UDD classifications)
  - `HEA/` — Health (ICD-10/ICD-8 diagnoses, ATC medications, specialties)
  - `LAB/` — Labor market (DISCO occupations, NACE/DB07 industries, income)
  - `SOC/` — Social/criminal justice (offenses, sentences, placements)
  - `SPECIAL/` — Model tokens ([PAD], [CLS], [SEP], [UNK], [MASK])
  - `MAPPINGS/` — Per-category mapping files with descriptions and sources (regenerated from MASTER)
  - `MISSING/` — Templates for categories still needing manual descriptions
- **`mapping/`** — Original source data (DISCO codes, PyTorch dictionaries, education crosswalks)
- **`raw/`** — Raw classification reference files (ATC, NACE, ICD codes, SAS format definitions)
- **`scripts/`** — Maintenance utilities

## Coverage

| Prefix | Categories | Codes | Description Coverage |
|--------|-----------|-------|---------------------|
| DEM | 25 | ~1,600 | ~82% mapped |
| EDU | 18 | ~8,500 | ~100% mapped |
| HEA | 19 | ~23,800 | ~95% mapped |
| LAB | 41 | ~5,400 | ~100% mapped |
| SOC | 23 | ~1,900 | ~100% mapped |
| SPECIAL | 1 | 5 | 100% mapped |

## Key Classification Systems

- **ICD-10 / ICD-8**: Medical diagnosis codes (with D prefix in Danish system)
- **ATC**: Anatomical Therapeutic Chemical medication codes
- **DISCO-08 / DISCO**: Danish occupational classification (based on ISCO-08)
- **NACE / DB07 / DB93**: Industry classification codes
- **DISCED**: Danish education classification (based on ISCED)
- **Municipality codes (kom)**: Danish administrative areas
- **Socio-economic codes (socio13)**: Status classifications

## Usage

```python
import json, csv

# Load vocabulary
with open('vocab.json') as f:
    vocab = json.load(f)  # code -> token_id

# Look up descriptions
with open('MASTER_CATEGORY_MAPPINGS.csv') as f:
    reader = csv.DictReader(f)
    mappings = {row['code']: row for row in reader}

# Example: get description for a code
code = 'HEA_ICD10_DA001'
print(mappings[code]['description'])  # "Kolera forårsaget af Vibrio cholerae eltor"
```

## Regenerating MAPPINGS

Individual MAPPINGS/ files are derived from MASTER. To regenerate after updating MASTER:

```bash
python3 scripts/regenerate_mappings.py
```
