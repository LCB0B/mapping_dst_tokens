#!/usr/bin/env python3
"""Fill description_en for LAB_db07, LAB_disco08, and LAB_disco rows using
authoritative international classifications that these Danish codes derive from.

  - DB07 6-digit  ← NACE Rev. 2 4-digit prefix (EU classification)
  - DISCO-08      ← ISCO-08 4-digit prefix (ILO classification)
  - DISCO (old)   ← ISCO-88 4-digit prefix (ILO classification)

Only writes description_en where it is currently empty; never overwrites.

Sources (all saved under raw/dst_downloads/):
    nace_rev2_en.csv  (vincentarelbundock.github.io Rdatasets validate package)
    isco08_en.csv     (iamarsenibragimov GitHub gist)
    isco88_en.csv     (Warwick IER / University of Warwick)

Usage:
    python3 scripts/fill_english_from_intl.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def load_nace():
    d = {}
    with open("raw/dst_downloads/nace_rev2_en.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row["Code"].strip()
            desc = row["Description"].strip()
            if code and desc:
                d[code] = desc
    return d


def load_isco(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d[row["code"].strip()] = row["title_en"].strip()
    return d


def db07_to_nace_candidates(value: str):
    """Yield NACE candidate codes of decreasing specificity: 4-digit class,
    3-digit group, 2-digit division (for shorter DB07 codes that roll up).
    """
    v = value.replace(".0", "")
    if len(v) >= 4:
        yield f"{v[:2]}.{v[2:4]}"
    if len(v) >= 3:
        yield f"{v[:2]}.{v[2]}"
    if len(v) >= 2:
        yield v[:2]


def disco08_to_isco4(value: str) -> str | None:
    """DISCO-08 6-digit '441900' → ISCO 4-digit '4419', stripping trailing zeros
    to also match 1/2/3-digit roll-ups (e.g. '200000' → '2')."""
    v = value.replace(".0", "")
    if not v:
        return None
    # Try progressively shorter prefixes to find best match in source dict
    for n in (4, 3, 2, 1):
        yield v[:n].rstrip("0") or v[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    nace = load_nace()
    isco08 = load_isco("raw/dst_downloads/isco08_en.csv")
    isco88 = load_isco("raw/dst_downloads/isco88_en.csv")

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    stats = {"db07_filled": 0, "db07_missed": 0,
             "disco08_filled": 0, "disco08_missed": 0,
             "disco_filled": 0, "disco_missed": 0}
    samples = []

    def lookup_isco(value: str, table: dict) -> str | None:
        v = value.replace(".0", "")
        for length in (4, 3, 2, 1):
            prefix = v[:length]
            for cand in (prefix.rstrip("0") or prefix, prefix):
                if cand in table:
                    return table[cand]
        return None

    for row in rows:
        cat = row["category"]
        if cat not in ("LAB_db07", "LAB_disco08", "LAB_disco"):
            continue
        if row["description_en"].strip():
            continue

        new_en = None
        stat_key = None
        if cat == "LAB_db07":
            new_en = None
            for cand in db07_to_nace_candidates(row["value"]):
                if cand in nace:
                    new_en = nace[cand]
                    break
            stat_key = "db07"
        elif cat == "LAB_disco08":
            new_en = lookup_isco(row["value"], isco08)
            stat_key = "disco08"
        elif cat == "LAB_disco":
            new_en = lookup_isco(row["value"], isco88)
            stat_key = "disco"

        if new_en:
            row["description_en"] = new_en
            row["description_short"] = re.sub(r"\s*\([^)]*\)", "", new_en).strip()
            stats[f"{stat_key}_filled"] += 1
            if len(samples) < 14:
                samples.append((row["code"], row["description_da"][:50], new_en))
        else:
            stats[f"{stat_key}_missed"] += 1

    print("Fill results:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nSamples:")
    for code, da, en in samples:
        print(f"  {code}")
        print(f"    DA: {da}")
        print(f"    EN: {en}")

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
