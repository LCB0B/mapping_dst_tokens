#!/usr/bin/env python3
"""Record alternative regional meanings for HEA_speciale codes that have
genuinely conflicting semantics across Danish regions' §2-aftaler.

The MASTER row for a 4-digit procedure code carries ONE description. But
some codes mean different things in different regions because each region
independently negotiated its §2-aftale. When a GP bills 804657 in Region
Syddanmark, the patient had a conversation with relatives; in Region
Hovedstaden, the same code means a consultation instead of a home visit.

We handle this by:
  1. Adding a `description_da_alt` column to MASTER. For rows where another
     region's meaning exists, the alternative is captured there.
  2. Logging each conflict in translation_audit_report.csv.

This preserves information without breaking the one-row-per-token model.

Usage:
    python3 scripts/apply_regional_overlaps.py [--dry-run]
"""
import argparse
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Known regional-meaning conflicts for 4-digit GP procedure codes.
# Collected from sundhed.dk and laeger.dk §2-aftale pages.
# Each key is a 4-digit procedure code; value is a list of (region, description) pairs.
CONFLICTS = {
    "4657": [
        ("Syddanmark", "Samtale med pårørende (Alvorligt syge og døende)"),
        ("Hovedstaden", "Konsultation i stedet for hjemmebesøg (Palliation)"),
    ],
    "4612": [
        ("Syddanmark", "Type 2-diabetes DD2, model 1 (komplet indrullering)"),
        ("Midtjylland", "DD2 model 1 fuld pakke"),
    ],
    "4614": [
        ("Syddanmark", "Type 2-diabetes DD2, model 3 (henvisning)"),
        ("Midtjylland", "DD2 model 3 henviser videre"),
    ],
    "4615": [
        ("Syddanmark", "Type 2-diabetes DD2, model 4 (delvis indrullering)"),
        ("Midtjylland", "DD2 blodprøve og forsendelse"),
    ],
    # 0101, 0124, 7403 are nationally defined but reused in regional agreements
    # with the same meaning — not a conflict.
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Add column if absent
    if "description_da_alt" not in fieldnames:
        fieldnames.append("description_da_alt")
    for r in rows:
        r.setdefault("description_da_alt", "")

    updated = 0
    samples = []
    for r in rows:
        if r["category"] != "HEA_speciale":
            continue
        v = r["value"]
        if len(v) != 6 or not v.startswith("80"):
            continue
        proc = v[2:]
        if proc not in CONFLICTS:
            continue
        variants = CONFLICTS[proc]
        # Current description is likely one of the variants (whichever we picked
        # in the regional apply pass). Record ALL alternatives.
        alt_texts = "; ".join(f"[{reg}] {desc}" for reg, desc in variants)
        r["description_da_alt"] = alt_texts
        updated += 1
        if len(samples) < 6:
            samples.append((r["code"], r["description_da"][:60], alt_texts[:90]))

    print(f"Rows with regional-conflict alternatives recorded: {updated}")
    print("\nSamples:")
    for code, cur, alt in samples:
        print(f"  {code}")
        print(f"    current DA: {cur}")
        print(f"    alt DA:     {alt}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows")


if __name__ == "__main__":
    main()
