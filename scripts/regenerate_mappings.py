#!/usr/bin/env python3
"""Regenerate individual MAPPINGS/ files from MASTER_CATEGORY_MAPPINGS.csv.

This ensures MAPPINGS/ files always reflect the real descriptions in MASTER,
rather than stale placeholders. Run from the repository root:

    python3 scripts/regenerate_mappings.py
"""

import csv
import os
from collections import defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
MAPPINGS_DIR = "hierarchical_vocab/MAPPINGS"
SOURCES_DOC_PATH = os.path.join(MAPPINGS_DIR, "SOURCES_DOCUMENTATION.csv")

# Sources that produce English descriptions
ENGLISH_SOURCES = {
    "generated_pattern",
    "generated:quantile_percentile",
    "manual_update",
    "enhanced_english",
    "manual_demographic_events",
}


def detect_language(source: str) -> str:
    """Heuristic: if source is known-English or description was generated in English."""
    if source in ENGLISH_SOURCES:
        return "english"
    return "danish"


def map_confidence(confidence_level: str) -> str:
    """Map MASTER confidence_level to MAPPINGS confidence."""
    if not confidence_level:
        return "medium"
    return confidence_level


def main():
    # Read MASTER
    categories = defaultdict(list)
    source_counts = defaultdict(lambda: defaultdict(int))

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row.get("category", "")
            if not cat:
                continue

            source = row.get("source", "")
            confidence = map_confidence(row.get("confidence_level", ""))
            language = detect_language(source)

            mapping_row = {
                "code": row["code"],
                "prefix": row["prefix"],
                "database": row.get("variable", ""),
                "value": row.get("value", ""),
                "description": row.get("description", ""),
                "description_da": row.get("description_da", ""),
                "description_da_alt": row.get("description_da_alt", ""),
                "description_da_full": row.get("description_da_full", ""),
                "description_en": row.get("description_en", ""),
                "description_en_official": row.get("description_en_official", ""),
                "description_en_official_source": row.get("description_en_official_source", ""),
                "description_en_source": row.get("description_en_source", ""),
                "source": source,
                "confidence": confidence,
                "language": language,
                "parent_code": row.get("parent_code", ""),
                "hierarchy_level": row.get("hierarchy_level", ""),
                "n_occurrences": row.get("n_occurrences", ""),
                "n_people": row.get("n_people", ""),
                "pct_people": row.get("pct_people", ""),
                "program_group": row.get("program_group", ""),
                "is_primary_code": row.get("is_primary_code", ""),
            }
            categories[cat].append(mapping_row)
            source_counts[source][language] += 1

    os.makedirs(MAPPINGS_DIR, exist_ok=True)

    # Write individual mapping files
    fieldnames = ["code", "prefix", "database", "value", "description", "description_da", "description_da_alt", "description_da_full", "description_en", "description_en_official", "description_en_official_source", "description_en_source", "source", "confidence", "language", "parent_code", "hierarchy_level", "n_occurrences", "n_people", "pct_people", "program_group", "is_primary_code"]
    files_written = 0

    for cat in sorted(categories.keys()):
        rows = categories[cat]
        # Derive filename: category -> category_mappings.csv
        filename = f"{cat}_mappings.csv"
        filepath = os.path.join(MAPPINGS_DIR, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        files_written += 1

    # Write SOURCES_DOCUMENTATION.csv
    source_doc_rows = []
    for source, lang_counts in sorted(source_counts.items()):
        total = sum(lang_counts.values())
        primary_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "unknown"
        # Determine confidence from source name
        if "CSV:" in source or source.startswith("raw_"):
            confidence = "high"
        elif "generated" in source or "manual" in source:
            confidence = "medium"
        else:
            confidence = "medium"

        source_doc_rows.append({
            "source": source,
            "description": source,
            "count": total,
            "confidence": confidence,
            "language": primary_lang,
        })

    with open(SOURCES_DOC_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "description", "count", "confidence", "language"])
        writer.writeheader()
        writer.writerows(source_doc_rows)

    print(f"Regenerated {files_written} mapping files in {MAPPINGS_DIR}/")
    print(f"Wrote {SOURCES_DOC_PATH} with {len(source_doc_rows)} sources")

    # Report total codes
    total = sum(len(rows) for rows in categories.values())
    print(f"Total codes across all files: {total}")


if __name__ == "__main__":
    main()
