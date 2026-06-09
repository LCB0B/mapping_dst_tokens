#!/usr/bin/env python3
"""Fix small DEM categories flagged during per-category English audit.

Issues found:
1. DEM_manual bin_antefam_over_1000: EN said "over 10 (bin)" — should be "over 1000"
2. DEM_familie: all 9 rows have empty DA and placeholder EN "Family type N.0" —
   fill from authoritative DST FAMILIE_TYPE source
   (https://www.dst.dk/da/Statistik/dokumentation/Times/cpr-oplysninger/familier-og-husstande/familie-type)
3. DEM_relation: fill DA (Danish translation of relation names)

Source files consulted:
- raw/bin_instructions.txt (repo — authoritative for DEM_manual_bin_*)
- DST TIMES FAMILIE_TYPE variable docs (web)
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# DST FAMILIE_TYPE (CPR variable) — authoritative code list
FAMILIE_TYPE = {
    "type_1":  ("Ægtepar", "Married couple"),
    "type_2":  ("Registreret partnerskab", "Registered partnership"),
    "type_3":  ("Samlevende par", "Cohabiting couple (with common children)"),
    "type_4":  ("Samboende par", "Common-law couple (without common children)"),
    "type_5":  ("Enlig (herunder også ikke hjemmeboende børn)",
                "Single person (including non-resident children)"),
    "type_7":  ("Ægtepar, forskelligt køn", "Married couple, different sex"),
    "type_8":  ("Ægtepar, samme køn", "Married couple, same sex"),
    "type_9":  ("Enlig", "Single"),
    "type_10": ("Ikke hjemmeboende børn", "Non-resident children"),
}

# Relation types — Danish fill based on repo convention
RELATION = {
    "Parent":           ("Forælder", "Parent relationship"),
    "Child":            ("Barn", "Child relationship"),
    "Full sibling":     ("Helsøskende", "Full sibling"),
    "Half-sibling":     ("Halvsøskende", "Half-sibling"),
    "Sibling (unknown)": ("Søskende (ukendt type)", "Sibling (unknown type)"),
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    stats = {"antefam_fixed": 0, "familie_filled": 0, "relation_filled": 0}

    for r in rows:
        cat = r["category"]
        v = r["value"]

        # Fix #1
        if cat == "DEM_manual" and v == "bin_antefam_over_1000":
            new_en = "Number of families in household: over 1000 (bin)"
            r["description_en"] = new_en
            r["description"] = new_en
            r["description_short"] = new_en
            r["description_en_source"] = "raw/bin_instructions.txt"
            stats["antefam_fixed"] += 1

        # Fix #2
        if cat == "DEM_familie" and v in FAMILIE_TYPE:
            da, en = FAMILIE_TYPE[v]
            r["description_da"] = da
            r["description"] = da
            r["description_en"] = en
            r["description_short"] = en
            r["description_en_source"] = "dst_times_familie_type"
            r["confidence_level"] = "high"
            stats["familie_filled"] += 1

        # Fix #3
        if cat == "DEM_relation" and v in RELATION:
            da, en = RELATION[v]
            r["description_da"] = da
            r["description"] = da
            r["description_en"] = en
            r["description_short"] = en
            stats["relation_filled"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
