#!/usr/bin/env python3
"""Fill description_en for HEA_ICD10 and HEA_atc rows using authoritative
WHO English sources.

HEA_ICD10 codes use a Danish 'D' prefix plus the WHO ICD-10 code (with an
optional Danish-specific 4th–5th character subdivision). Example:
  DA001   → WHO A00.1  (exact match, WHO title definitive)
  DG4732  → WHO G47.3 exists, DG4732 is Danish subdivision of G47.3
            (keep current EN if it is specific; else fall back to WHO parent)

HEA_atc codes are international ATC codes. Their EN label should be
composed as "<class name>, <substance name>" using the WHO ATC hierarchy
(5-char prefix = class, full code = substance). Example:
  A10BB01 → "sulfonylureas, glibenclamide"

This script only overwrites description_en when the current value is:
  * empty
  * identical (case-insensitive) to description_da
  * a 'X (via NNN)' hierarchy-fallback placeholder
  * duplicated across 5+ codes in the same category (too generic)

Sources saved in raw/dst_downloads/:
  icd10_who_2019_en.csv   from icdcdn.who.int ClaML 2019
  atc_who_2021_en.csv     from github.com/fabkury/atcd (WHO scrape)

Usage:
    python3 scripts/fill_icd10_atc_who.py [--dry-run]
"""
import argparse
import csv
import re
from collections import defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
VIA_RE = re.compile(r"\(via \d+\)")


def load_who_icd10():
    d = {}
    with open("raw/dst_downloads/icd10_who_2019_en.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d[row["code"].strip()] = row["title_en"].strip()
    return d


def load_who_atc():
    d = {}
    with open("raw/dst_downloads/atc_who_2021_en.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["atc_code"].strip()
            name = row["atc_name"].strip()
            if code and name and code not in d:
                d[code] = name
    return d


def danish_icd_to_who(v: str) -> str | None:
    """Convert DA001 → A00.1, DG4732 → G47.32, etc."""
    if not v.startswith("D") or len(v) < 3 or not v[1].isalpha():
        return None
    s = v[1:]  # drop 'D'
    if len(s) <= 3:
        return s
    return s[:3] + "." + s[3:]


def icd_candidates(who_code: str):
    """Yield the WHO code and its ancestors (shorter codes)."""
    yield who_code
    base = who_code
    # Strip one trailing character at a time. If code is "G47.32", try "G47.3", "G47", "G4" etc.
    while base:
        if base.endswith("."):
            base = base[:-1]
            continue
        base = base[:-1]
        if base:
            yield base


def atc_label(code: str, atc: dict) -> str | None:
    """Compose '<class>, <substance>' from WHO ATC dict using the code and its
    5-char prefix. If only one is available, return that."""
    full = atc.get(code)
    cls = None
    if len(code) > 5:
        cls = atc.get(code[:5]) or atc.get(code[:4]) or atc.get(code[:3])
    if full and cls and full.lower() != cls.lower():
        return f"{cls}, {full}".lower() if cls.isupper() or full.isupper() else f"{cls}, {full}"
    return full or cls


def count_duplicates(rows):
    """Return dict mapping category → desc → count."""
    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["description_en"].strip():
            counts[r["category"]][r["description_en"].strip()] += 1
    return counts


def should_overwrite(row, dup_counts):
    en = row["description_en"].strip()
    da = row["description_da"].strip()
    if not en:
        return True
    if VIA_RE.search(en):
        return True
    if da and en.lower() == da.lower():
        return True
    # Highly-duplicated generic EN (5+ codes share it) — probably parent-rollup
    if dup_counts[row["category"]].get(en, 0) >= 5:
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--category", choices=["icd10", "atc", "both"], default="both")
    args = ap.parse_args()

    who_icd = load_who_icd10()
    who_atc = load_who_atc()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    dup_counts = count_duplicates(rows)

    stats = {"icd10_exact": 0, "icd10_parent": 0, "icd10_skipped": 0,
             "atc_exact": 0, "atc_parent": 0, "atc_skipped": 0}
    samples = []

    for row in rows:
        cat = row["category"]

        if cat == "HEA_ICD10" and args.category in ("icd10", "both"):
            who_code = danish_icd_to_who(row["value"])
            if not who_code:
                continue
            if not should_overwrite(row, dup_counts):
                stats["icd10_skipped"] += 1
                continue
            new_en = None
            exact = False
            for cand in icd_candidates(who_code):
                if cand in who_icd:
                    new_en = who_icd[cand]
                    exact = cand == who_code
                    break
            if new_en:
                if len(samples) < 8:
                    samples.append((row["code"], row["description_da"][:50],
                                    row["description_en"][:50], new_en, "exact" if exact else "parent"))
                row["description_en"] = new_en
                row["description_short"] = re.sub(r"\s*\([^)]*\)", "", new_en).strip()
                stats["icd10_exact" if exact else "icd10_parent"] += 1

        elif cat == "HEA_atc" and args.category in ("atc", "both"):
            if not should_overwrite(row, dup_counts):
                stats["atc_skipped"] += 1
                continue
            label = atc_label(row["value"], who_atc)
            if label:
                is_exact = row["value"] in who_atc
                if len(samples) < 14:
                    samples.append((row["code"], row["description_da"][:50],
                                    row["description_en"][:50], label,
                                    "exact" if is_exact else "parent"))
                row["description_en"] = label
                row["description_short"] = re.sub(r"\s*\([^)]*\)", "", label).strip()
                stats["atc_exact" if is_exact else "atc_parent"] += 1

    print("Results:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nSamples:")
    for code, da, en_old, en_new, kind in samples:
        print(f"  {code}  ({kind})")
        print(f"    DA: {da}")
        print(f"    OLD EN: {en_old}")
        print(f"    NEW EN: {en_new}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER_PATH}")


if __name__ == "__main__":
    main()
