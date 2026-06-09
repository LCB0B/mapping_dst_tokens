#!/usr/bin/env python3
"""Name-based crosswalk for LAB_disco rows whose ISCO-88 4-digit prefix
lookup gave a wrong English title because the Danish description in
MASTER belongs to a DIFFERENT DISCO version than the numeric code
implies.

Finding (see notes.md): the `LAB_disco` category in MASTER mixes rows
from BOTH Danish DISCO eras:
  - Some rows follow DISCO-88 numbering (codes align with ISCO-88)
  - Some rows follow DISCO-08 numbering (codes align with ISCO-08)
  - A few rows follow an even-older internal numbering with no clean alignment

For each row needing official English, this script:
  1. Checks if the row's Danish description matches the DISCO-08 title
     at the same numeric code (via raw/LAB_disco.csv) — if yes, use ISCO-08.
  2. Otherwise checks if it matches DISCO-88 title at the same code
     (via LAB_disco_codes.txt) — if yes, use ISCO-88.
  3. Otherwise tries name-based fuzzy match (≥ 0.90) against both DISCO
     Danish dictionaries and uses the matched code's ISCO prefix.
  4. If still nothing reliable, leaves `description_en_official` empty.

Never mutates `description_da`, `description_en`, token_id, or code.

Usage:
    python3 scripts/crosswalk_lab_disco.py [--dry-run] [--threshold 0.90]
"""
import argparse
import csv
import re
from difflib import SequenceMatcher

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def load_disco88_txt():
    d = {}
    with open("raw/LAB_disco_codes.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                d[parts[0].strip()] = parts[1].strip()
    return d


def load_disco08_raw():
    d = {}
    with open("raw/LAB_disco.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            code = r.get("KODE", "").strip().strip('"')
            title = r.get("TITEL", "").strip()
            if code and title:
                d[code] = title
    return d


def load_isco(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["code"].strip()] = r["title_en"].strip()
    return d


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def lookup_isco(disco_code: str, isco: dict):
    for n in (4, 3, 2, 1):
        prefix = disco_code[:n]
        for cand in (prefix.rstrip("0") or prefix, prefix):
            if cand in isco:
                return isco[cand]
    return None


def find_fuzzy(da: str, disco_da_dict: dict, threshold: float):
    key = normalize(da)
    # Exact first
    for code, desc in disco_da_dict.items():
        if normalize(desc) == key:
            return code, 1.0
    # Fuzzy
    best_code, best_ratio = None, 0.0
    for code, desc in disco_da_dict.items():
        ratio = SequenceMatcher(None, key, normalize(desc)).ratio()
        if ratio > best_ratio:
            best_code, best_ratio = code, ratio
    if best_ratio >= threshold:
        return best_code, best_ratio
    return None, best_ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.90)
    args = ap.parse_args()

    disco88 = load_disco88_txt()
    disco08 = load_disco08_raw()
    isco88 = load_isco("raw/dst_downloads/isco88_en.csv")
    isco08 = load_isco("raw/dst_downloads/isco08_en.csv")

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    candidates = [
        r for r in rows
        if r["category"] == "LAB_disco"
        and not r["description_en_official"].strip()
        and r["description_da"].strip()
    ]

    stats = {
        "same-code-disco08": 0,   # DA matches DISCO-08 at same code → ISCO-08 lookup
        "same-code-disco88": 0,   # DA matches DISCO-88 at same code → ISCO-88 lookup
        "fuzzy-disco08": 0,
        "fuzzy-disco88": 0,
        "no-match": 0,
    }
    samples = []

    for r in candidates:
        v = r["value"]
        da = r["description_da"].strip()
        en = None
        kind = None

        # 1. Same-code match against DISCO-08 Danish
        if v in disco08 and normalize(disco08[v]) == normalize(da):
            en = lookup_isco(v, isco08)
            if en:
                kind = "same-code-disco08"
                r["description_en_source"] = "isco08-crosswalk"
        # 2. Same-code match against DISCO-88 Danish
        if en is None and v in disco88 and normalize(disco88[v]) == normalize(da):
            en = lookup_isco(v, isco88)
            if en:
                kind = "same-code-disco88"
                r["description_en_source"] = "isco88-crosswalk"
        # 3. Fuzzy match DISCO-08
        if en is None:
            code, ratio = find_fuzzy(da, disco08, args.threshold)
            if code:
                en = lookup_isco(code, isco08)
                if en:
                    kind = "fuzzy-disco08"
                    r["description_en_source"] = "isco08-crosswalk"
        # 4. Fuzzy match DISCO-88
        if en is None:
            code, ratio = find_fuzzy(da, disco88, args.threshold)
            if code:
                en = lookup_isco(code, isco88)
                if en:
                    kind = "fuzzy-disco88"
                    r["description_en_source"] = "isco88-crosswalk"

        if en:
            r["description_en_official"] = en
            stats[kind] += 1
            if len(samples) < 10:
                samples.append((r["code"], da, en, kind))
        else:
            stats["no-match"] += 1

    print(f"Candidates: {len(candidates)}")
    print("Resolution:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nSamples:")
    for code, da, en, kind in samples:
        print(f"  [{kind}] {code}")
        print(f"    DA: {da[:60]!r}")
        print(f"    EN: {en[:60]!r}")

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
