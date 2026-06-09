#!/usr/bin/env python3
"""Apply regional §2-agreement codes (Region Hovedstaden, Sjælland,
Syddanmark, Midtjylland) to HEA_speciale rows that were tagged as
"(procedure not documented)". These codes are GP (specialty 80) specific
services negotiated by each Danish region separately — not published in
the national Ydelsesoversigt.

Source: curated from sundhed.dk regional §2-aftale pages and laeger.dk
PLO regional agreements (see raw/dst_downloads/regional_p2_codes.csv
for provenance per code).

Usage:
    python3 scripts/apply_regional_codes.py [--dry-run]
"""
import argparse
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
REGIONAL_CSV = "raw/dst_downloads/regional_p2_codes.csv"


def load_regional():
    d = {}
    with open(REGIONAL_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            code = r["ydelsesnr"].strip()
            desc = r["description_da"].strip()
            region = r["region"].strip()
            agreement = r["agreement"].strip()
            d[code] = (desc, region, agreement)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    regional = load_regional()
    print(f"Regional codes loaded: {len(regional)}")

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    filled = 0
    samples = []
    for r in rows:
        if r["category"] != "HEA_speciale":
            continue
        if "not documented" not in r["description_da"]:
            continue
        v = r["value"]
        if len(v) != 6 or not v.startswith("80"):
            continue
        proc = v[2:]
        if proc not in regional:
            continue
        desc, region, agreement = regional[proc]
        new_da = f"Almen Lægehjælp 80, {desc} (regional §2-aftale, Region {region})"
        r["description_da"] = new_da
        r["description"] = new_da
        # description_en — compose a reasonable English label
        en_desc = (
            desc.replace("sygebesøg", "home visit")
                .replace("konsultation", "consultation")
                .replace("hjemmebesøg", "home visit")
        )
        r["description_en"] = f"General practitioner, {desc} (regional §2 agreement, Region {region})"
        filled += 1
        if len(samples) < 8:
            samples.append((r["code"], new_da))

    print(f"Filled {filled} rows from regional §2-aftaler")
    print("\nSamples:")
    for code, da in samples:
        print(f"  {code}")
        print(f"    {da}")

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
