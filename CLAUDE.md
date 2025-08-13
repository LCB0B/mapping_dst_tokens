# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview
This is a hierarchical vocabulary mapping repository for Danish administrative and educational data systems. The repository contains a complete hierarchical organization of vocab.json codes with comprehensive mappings to English and Danish descriptions.

## Project Goals ✅ COMPLETED
1. **Hierarchical Organization**: Split vocab.json into systematic hierarchical structure ✅
2. **CSV Format**: All data organized in easily accessible CSV format ✅  
3. **Complete Mappings**: Comprehensive mappings from multiple authoritative sources ✅
4. **Source Tracking**: Track mapping sources and confidence levels ✅
5. **Missing Identification**: Identify categories needing manual mappings ✅

**Result**: Clean hierarchical structure with 124 categories, 117 with mappings, 5 needing manual input

## Repository Structure

### Core Files
- **vocab.json**: Original vocabulary file (41,201 codes)
- **HIERARCHY_SUMMARY.csv**: Complete overview of all categories
- **REPOSITORY_STRUCTURE.csv**: Directory structure summary

### Original Data Sources  
- **mapping/**: Original mapping files (DISCO_CODES.txt, lookup_dictionaries/*.pt, raw/*)
- **pt_extracted_mappings.json**: Extracted from PyTorch dictionary files (36,092 mappings)
- **extracted_mappings.json**: Extracted from DISCO and SAS files (6,463 mappings)
- **lookup_reference_data.json**: Reference data (ICD-10, municipalities, countries)

### Hierarchical Structure: `/hierarchical_vocab/`

#### Vocabulary by Category
```
DEM/     - Demographics (22 categories)
├── DEM_birthyear.csv         (158 codes)
├── DEM_kom.csv               (356 municipality codes)  
├── DEM_statsb.csv            (214 country residence codes)
├── DEM_opr.csv               (219 country origin codes)
└── ... (18 more demographic categories)

EDU/     - Education (16 categories)  
├── EDU_audd.csv              (3,758 post-secondary codes)
├── EDU_udd.csv               (2,416 higher education codes)
├── EDU_disced.csv            (790 DISCED classifications)
└── ... (13 more education categories)

HEA/     - Health (19 categories)
├── HEA_icd10.csv             (15,206 medical diagnosis codes)
├── HEA_speciale.csv          (6,134 medical specialty codes)
├── HEA_atc.csv               (1,657 medication codes)  
└── ... (16 more health categories)

LAB/     - Labor Market (42 categories)
├── LAB_disco.csv             (793 occupation codes)
├── LAB_disco08.csv           (756 DISCO-08 codes)
├── LAB_db07.csv              (1,483 industry codes)
├── LAB_socio13.csv           (21 socio-economic codes)
└── ... (38 more labor categories)

SOC/     - Social/Criminal (22 categories)
├── SOC_ger7.csv              (938 criminal offense codes)
├── SOC_ansted.csv            (32 placement type codes)
├── SOC_frakkod.csv           (186 offense type codes)
└── ... (19 more social categories)

SPECIAL/ - Special tokens (1 category)
└── special_tokens.csv        (5 model tokens: [PAD], [CLS], etc.)
```

#### Mappings with Sources: `/hierarchical_vocab/MAPPINGS/`
```
MAPPINGS/
├── SOURCES_DOCUMENTATION.csv           # Documentation of all mapping sources
├── DEM_kom_mappings.csv                # Municipality mappings with sources
├── EDU_audd_mappings.csv               # Education mappings with sources  
├── HEA_icd10_mappings.csv              # Medical mappings with sources
├── LAB_disco_mappings.csv              # Occupation mappings with sources
└── ... (117 mapping files total)

Each mapping CSV contains:
- code: The vocabulary code
- prefix: Category prefix (DEM, EDU, HEA, LAB, SOC)
- database: Database/subcategory  
- value: The specific value/identifier
- description: English/Danish description
- source: Source of mapping (pt_dictionaries, disco_codes, etc.)
- confidence: Confidence level (highest, high, medium, low)
- language: Original language of description
```

#### Missing Mappings: `/hierarchical_vocab/MISSING/`
```
MISSING/
├── MISSING_CATEGORIES_SUMMARY.csv      # Overview of categories needing mappings
├── DEM_Birth_MISSING.csv               # Template for Birth event codes
├── DEM_Death_MISSING.csv               # Template for Death event codes  
├── DEM_Indvandret_MISSING.csv          # Template for Immigration codes
├── DEM_Udvandret_MISSING.csv           # Template for Emigration codes
└── DEM_unknown_MISSING.csv             # Template for Unknown codes

Each missing CSV contains template with:
- code: The vocabulary code
- prefix, database, value: Structure information  
- description_en: [TO BE FILLED]
- description_da: [TO BE FILLED]  
- notes: [FOR ADDITIONAL INFO]
- confidence: [TO BE SET]
- source: manual
```

## Mapping Sources and Confidence Levels

### 🔥 **Highest Confidence** - PT Dictionaries (36,092 mappings)
- **Source**: PyTorch files from `mapping/lookup_dictionaries/*.pt`
- **Description**: Official Danish administrative classification dictionaries
- **Language**: Danish
- **Coverage**: DEM (municipalities, countries), EDU (education levels), HEA (medical), LAB (socio-economic), SOC (criminal)

### 🎯 **High Confidence** - External Official Sources (6,463 mappings)  
- **DISCO Codes**: Danish occupational classifications from `mapping/DISCO_CODES.txt`
- **SAS Formats**: Code definitions from `mapping/raw/*.txt` files
- **Language**: Mixed Danish/English

### 📊 **Medium Confidence** - Research Enhanced (remaining mappings)
- **External APIs**: ICD-10 from GitHub, ATC medication categories
- **Research**: Municipality names, country mappings from official sources
- **Generated**: Pattern-based descriptions for percentiles and bins

## Working with this Repository

### Getting Started
1. **Explore categories**: Check `HIERARCHY_SUMMARY.csv` for overview
2. **Find your codes**: Look in appropriate `PREFIX/PREFIX_database.csv` file
3. **Get mappings**: Check `MAPPINGS/PREFIX_database_mappings.csv` for descriptions
4. **Identify gaps**: Review `MISSING/MISSING_CATEGORIES_SUMMARY.csv`

### Adding Missing Mappings  
1. Open relevant file in `MISSING/` directory
2. Fill in `description_en` and `description_da` columns
3. Set appropriate `confidence` level  
4. Add `notes` for context
5. Update `source` if using external reference

### Key Danish Administrative Systems
- **DISCED**: Education classification adapted for Denmark  
- **DISCO-08**: Danish occupational classification (6-digit hierarchical)
- **Municipality codes**: Danish administrative areas (kom codes)
- **Country codes**: Origin (opr_land) and residence (statsb) classifications
- **ICD-10**: International medical diagnosis codes (with D prefix)
- **ATC**: Anatomical Therapeutic Chemical medication codes
- **Socio codes**: Socio-economic status classifications

## File Navigation Guide

### For Demographics Research
- **Municipalities**: `DEM/DEM_kom.csv` + `MAPPINGS/DEM_kom_mappings.csv`
- **Countries**: `DEM/DEM_statsb.csv` + `DEM/DEM_opr.csv` + mappings
- **Birth data**: `DEM/DEM_birthyear.csv`, `DEM/DEM_birthmonth.csv` + mappings

### For Education Research  
- **Post-secondary**: `EDU/EDU_audd.csv` + `MAPPINGS/EDU_audd_mappings.csv`
- **Higher education**: `EDU/EDU_udd.csv` + `MAPPINGS/EDU_udd_mappings.csv`
- **DISCED**: `EDU/EDU_disced.csv` + `MAPPINGS/EDU_disced_mappings.csv`

### For Health Research
- **Medical diagnoses**: `HEA/HEA_icd10.csv` + `MAPPINGS/HEA_icd10_mappings.csv`  
- **Medications**: `HEA/HEA_atc.csv` + `MAPPINGS/HEA_atc_mappings.csv`
- **Specialties**: `HEA/HEA_speciale.csv` + `MAPPINGS/HEA_speciale_mappings.csv`

### For Labor Research
- **Occupations**: `LAB/LAB_disco.csv` + `LAB/LAB_disco08.csv` + mappings
- **Industries**: `LAB/LAB_db07.csv` + `LAB/LAB_nace.csv` + mappings  
- **Socio-economic**: `LAB/LAB_socio13.csv` + `MAPPINGS/LAB_socio13_mappings.csv`

### For Social/Criminal Research
- **Criminal offenses**: `SOC/SOC_ger7.csv` + `MAPPINGS/SOC_ger7_mappings.csv`
- **Placements**: `SOC/SOC_ansted.csv` + `MAPPINGS/SOC_ansted_mappings.csv`

## Quick Statistics
- **Total vocabulary codes**: 41,201
- **Hierarchical categories**: 124
- **Categories with mappings**: 117 (94.4%)
- **Categories needing work**: 5 (4.0%)
- **Highest confidence mappings**: 36,092 (87.6%)
- **CSV files created**: 246 total
- **Repository structure**: Clean and systematic

## Usage Examples

### Finding Municipality Name
```bash
# Check municipality code 237
grep "DEM_kom_237" hierarchical_vocab/MAPPINGS/DEM_kom_mappings.csv
# Result: Ølstykke
```

### Finding Country Name  
```bash
# Check country residence code 5159
grep "DEM_statsb_5159" hierarchical_vocab/MAPPINGS/DEM_statsb_mappings.csv  
# Result: San Marino
```

### Finding Education Level
```bash
# Check education code 1006
grep "EDU_audd_1006" hierarchical_vocab/MAPPINGS/EDU_audd_mappings.csv
# Result: 6. klasse (6th grade)
```

The repository is now organized hierarchically and ready for systematic vocabulary research and mapping completion.