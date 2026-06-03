#!/usr/bin/env python3
"""Fill in per-code Danish descriptions for hierarchical categories whose
sub-codes currently fall back to their parent's description ('X (via N)').

Covers:
  - LAB_disco08: raw/disco.csv (DISCO-08, 6-digit, shipped with repo)
  - LAB_disco:   mapping/DISCO_CODES.txt (6-digit DISCO, shipped with repo)
  - LAB_db07:    raw/dst_downloads/db07_v2_2013.csv (fetched from dst.dk)
  - SOC_ger7:    raw/dst_downloads/ger7.csv (fetched from dst.dk)

Only rows whose current description matches the '(via N)' fallback pattern
are rewritten; rows with genuine per-code descriptions are left alone.

description_en is cleared for rewritten rows so the translation pipeline
(manual dictionary + retranslate) regenerates it from the new Danish source.

Usage:
    python3 scripts/fill_hierarchy_specifics.py [--dry-run]
"""
import argparse
import csv
import os
import re
import sys

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

VIA_RE = re.compile(r"\(via \d+\)\s*$")


def load_disco_raw():
    """raw/disco.csv — DISCO-08 full classification (variable-length codes)."""
    disco = {}
    with open("raw/disco.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = row.get("KODE", "").strip().strip('"')
            title = row.get("TITEL", "").strip()
            if code and title:
                disco[code] = title
    return disco


def load_disco_codes():
    """mapping/DISCO_CODES.txt — 6-digit DISCO (older classification)."""
    d = {}
    with open("mapping/DISCO_CODES.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                d[parts[0].strip()] = parts[1].strip()
    return d


def load_db07():
    """raw/dst_downloads/db07_v2_2013.csv — DB07 v2:2013 from Statistics Denmark."""
    d = {}
    path = "raw/dst_downloads/db07_v2_2013.csv"
    if not os.path.exists(path):
        return d
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = row.get("KODE", "").strip().strip('"')
            title = row.get("TITEL", "").strip()
            if code and title:
                d[code] = title
    return d


def load_ger7():
    """raw/dst_downloads/ger7.csv — GER7 (7-digit offense codes) from Statistics Denmark."""
    d = {}
    path = "raw/dst_downloads/ger7.csv"
    if not os.path.exists(path):
        return d
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) >= 4:
                code = row[2].strip()
                title = row[3].strip()
                if code and title:
                    d[code] = title
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    disco08 = load_disco_raw()
    disco_old = load_disco_codes()
    db07 = load_db07()
    ger7 = load_ger7()

    source_by_cat = {
        "LAB_disco08": disco08,
        "LAB_disco": disco_old,
        "LAB_db07": db07,
        "SOC_ger7": ger7,
    }

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    stats = {cat: 0 for cat in source_by_cat}
    stats["skipped_no_source"] = 0
    stats["not_fallback"] = 0
    samples = []

    for row in rows:
        cat = row["category"]
        if cat not in source_by_cat:
            continue
        src = source_by_cat[cat]
        if not src:
            continue  # source file missing
        da = row["description_da"].strip()
        if not VIA_RE.search(da):
            stats["not_fallback"] += 1
            continue

        # Normalize value: strip float ".0" suffix that some vocab entries carry.
        v = row["value"].replace(".0", "")
        new_desc = None
        if v in src:
            new_desc = src[v]
        else:
            stripped = v.rstrip("0")
            if stripped and stripped in src:
                new_desc = src[stripped]

        if new_desc is None:
            stats["skipped_no_source"] += 1
            continue
        if new_desc == da:
            stats["not_fallback"] += 1
            continue

        if len(samples) < 12:
            samples.append((row["code"], da, new_desc))
        row["description_da"] = new_desc
        row["description"] = new_desc
        # Clear EN so the translation pass picks it up again
        row["description_en"] = ""
        row["description_short"] = ""
        stats[cat] += 1

    print("Fills applied:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if samples:
        print("\nExamples:")
        for code, old, new in samples:
            print(f"  {code}")
            print(f"    OLD: {old}")
            print(f"    NEW: {new}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER_PATH}")
    print("Run scripts/regenerate_mappings.py, then retranslate to populate EN.")


if __name__ == "__main__":
    main()
