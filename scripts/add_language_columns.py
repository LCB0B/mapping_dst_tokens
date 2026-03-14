#!/usr/bin/env python3
"""Add description_da and description_en columns to MASTER_CATEGORY_MAPPINGS.csv.

For descriptions we know are Danish, set description_da.
For descriptions we know are English, set description_en.
Keep original 'description' column as-is.

Run from repository root:
    python3 scripts/add_language_columns.py
"""

import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Sources that produce English descriptions
ENGLISH_SOURCES = {
    "generated_pattern",
    "generated:quantile_percentile",
    "manual_update",
    "manual_demographic_events",
    "vocab_reconciliation",
}

# Sources that produce Danish descriptions
DANISH_SOURCES = {
    "CSV:HEA_ICD10",
    "CSV:EDU_audd",
    "CSV:EDU_udd",
    "CSV:LAB_db07_hierarchical",
    "CSV:SOC_ger7_hierarchical",
    "CSV:LAB_disco08_comprehensive_hierarchical",
    "CSV:LAB_disco_from_raw_hierarchical",
    "CSV:LAB_branche_from_raw_fixed",
    "CSV:DEM_kom",
    "CSV:DEM_opr_land",
    "CSV:DEM_statsb",
    "CSV:LAB_soc_status",
    "CSV:SOC_ansted_klas",
    "CSV:SOC_ger7",
    "CSV:LAB_socio13",
    "CSV:DEM_mor_foed_adop",
    "CSV:DEM_far_foed_adop",
    "CSV:LAB_disco08_dst_hierarchical",
    "CSV:LAB_disco08_dict.csv",
    "CSV:SOC_samtykke_from_raw",
    "CSV:SOC_haendelse_from_raw",
    "CSV:SOC_bstrfkod_from_raw",
    "CSV:SOC_afgtypko_from_raw",
    "CSV:SOC_pgf_from_raw",
    "CSV:HEA_atc_fallback",
    "CSV:EDU_disced_compound_start",
    "CSV:EDU_disced_compound_end",
    "CSV:LAB_disco_from_raw",
    "dual_source_special2_spec6",
    "special2_only",
    "raw_atc_enhanced_hierarchical",
    "raw_lab_nace",
    "raw_edu_field",
    "raw_soc_frakkod",
    "raw_lab_tilstand_kode",
    "raw_dem_civst",
    "raw_dem_fm_mark",
}


def detect_language(desc, source):
    """Determine if a description is Danish, English, or ambiguous."""
    # Check source first
    base_source = source.split("|")[0]  # Remove |dict_fill, |generated suffixes

    if base_source in ENGLISH_SOURCES:
        return "en"
    if base_source in DANISH_SOURCES:
        return "da"

    # Check for |generated suffix (our generated descriptions are English)
    if "|generated" in source:
        return "en"

    # Heuristic: check for Danish-specific characters and words
    if desc:
        # Danish indicators
        danish_chars = any(c in desc for c in "æøåÆØÅ")
        danish_words = any(w in desc.lower() for w in [
            "uoplyst", "klasse", "kommune", "øvrige", "ikke",
            "forårsaget", "uddannelse", "forbrydelse", "ansatte",
            "selvstændig", "lønmodtager",
        ])
        if danish_chars or danish_words:
            return "da"

        # English indicators
        english_words = any(w in desc.lower() for w in [
            "code:", "quantile", "grade", "bin)", "employment",
            "unknown", "padding", "classification", "separator",
            "category", "over ", "passed", "municipality",
        ])
        if english_words:
            return "en"

    # Names (municipalities, countries) are language-neutral
    if base_source in ("CSV:DEM_kom", "CSV:DEM_opr_land", "CSV:DEM_statsb"):
        return "both"

    # Default: assume Danish for most administrative codes
    return "da"


def main():
    rows = []
    fieldnames = None

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(dict(row))

    # Insert description_da and description_en after description
    desc_idx = fieldnames.index("description")
    if "description_da" not in fieldnames:
        fieldnames.insert(desc_idx + 1, "description_da")
    if "description_en" not in fieldnames:
        fieldnames.insert(desc_idx + 2, "description_en")

    da_count = 0
    en_count = 0
    both_count = 0

    for row in rows:
        desc = row.get("description", "")
        source = row.get("source", "")

        lang = detect_language(desc, source)

        if lang == "da":
            row["description_da"] = desc
            row["description_en"] = ""
            da_count += 1
        elif lang == "en":
            row["description_da"] = ""
            row["description_en"] = desc
            en_count += 1
        elif lang == "both":
            # Names that are the same in both languages
            row["description_da"] = desc
            row["description_en"] = desc
            both_count += 1
        else:
            row["description_da"] = desc
            row["description_en"] = ""
            da_count += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Added description_da and description_en columns")
    print(f"Danish: {da_count}, English: {en_count}, Both: {both_count}")
    print(f"Total: {len(rows)}")


if __name__ == "__main__":
    main()
