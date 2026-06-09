#!/usr/bin/env python3
"""Add `description_en_official` and `description_en_source` columns to MASTER.

`description_en_official` holds the English title from an authoritative
international classification (WHO, Eurostat, ILO) when one exists for the code.
Unlike `description_en` — which is the best available English (translated
from Danish or official) — `description_en_official` is ONLY populated when
we have a traceable mapping to an international standard.

`description_en_source` tags where `description_en` came from:
    who-icd10  — WHO ICD-10 (2019) via D-prefix → WHO code mapping
    who-atc    — WHO ATC 2021 (composed class + substance)
    nace2      — NACE Rev 2 (4-digit parent of DB07 6-digit)
    isco08     — ISCO-08 (4-digit parent of DISCO-08)
    isco88     — ISCO-88 (4-digit parent of DISCO)
    manual     — hand-curated dictionary in scripts/manual_translations_*
    mt         — any other (prior MarianMT/Qwen/NLLB output)
    empty      — no English yet

This lets downstream consumers filter for authoritative labels when needed.

Usage:
    python3 scripts/add_official_en_column.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def load_dict(path, code_col, desc_col):
    d = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row[code_col].strip()
            desc = row[desc_col].strip()
            if code and desc and code not in d:
                d[code] = desc
    return d


def load_icd10():
    return load_dict("raw/dst_downloads/icd10_who_2019_en.csv", "code", "title_en")


def load_atc():
    return load_dict("raw/dst_downloads/atc_who_2021_en.csv", "atc_code", "atc_name")


def load_nace():
    return load_dict("raw/dst_downloads/nace_rev2_en.csv", "Code", "Description")


def load_isco(path):
    return load_dict(path, "code", "title_en")


def danish_icd_to_who(v: str) -> str | None:
    if not v.startswith("D") or len(v) < 3 or not v[1].isalpha():
        return None
    s = v[1:]
    return s if len(s) <= 3 else s[:3] + "." + s[3:]


def icd_ancestors(code: str):
    yield code
    base = code
    while base:
        base = base.rstrip(".")
        base = base[:-1]
        if base and not base.endswith("."):
            yield base


def atc_label(code: str, atc: dict):
    full = atc.get(code)
    cls = None
    if len(code) > 5:
        cls = atc.get(code[:5]) or atc.get(code[:4]) or atc.get(code[:3])
    if full and cls and full.lower() != cls.lower():
        return f"{cls}, {full}"
    return full or cls


def lookup_isco(value: str, table: dict):
    v = value.replace(".0", "")
    for n in (4, 3, 2, 1):
        prefix = v[:n]
        for cand in (prefix.rstrip("0") or prefix, prefix):
            if cand in table:
                return table[cand]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    icd10 = load_icd10()
    atc = load_atc()
    nace = load_nace()
    isco08 = load_isco("raw/dst_downloads/isco08_en.csv")
    isco88 = load_isco("raw/dst_downloads/isco88_en.csv")

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Add new columns if absent
    for col in ("description_en_official", "description_en_source"):
        if col not in fieldnames:
            fieldnames.append(col)
        for r in rows:
            r.setdefault(col, "")

    stats = {}
    for r in rows:
        cat = r["category"]
        v = r["value"]
        official = ""

        if cat == "HEA_ICD10":
            who = danish_icd_to_who(v)
            if who:
                for cand in icd_ancestors(who):
                    if cand in icd10:
                        official = icd10[cand]
                        break
            if official:
                r["description_en_official"] = official
                stats["who-icd10"] = stats.get("who-icd10", 0) + 1
        elif cat == "HEA_atc":
            lab = atc_label(v, atc)
            if lab:
                r["description_en_official"] = lab
                stats["who-atc"] = stats.get("who-atc", 0) + 1
        elif cat == "LAB_db07":
            vv = v.replace(".0", "")
            candidates = []
            if len(vv) >= 4: candidates.append(f"{vv[:2]}.{vv[2:4]}")
            if len(vv) >= 3: candidates.append(f"{vv[:2]}.{vv[2]}")
            if len(vv) >= 2: candidates.append(vv[:2])
            for cand in candidates:
                if cand in nace:
                    r["description_en_official"] = nace[cand]
                    stats["nace2"] = stats.get("nace2", 0) + 1
                    break
        elif cat == "LAB_disco08":
            lab = lookup_isco(v, isco08)
            if lab:
                r["description_en_official"] = lab
                stats["isco08"] = stats.get("isco08", 0) + 1
        elif cat == "LAB_disco":
            lab = lookup_isco(v, isco88)
            if lab:
                r["description_en_official"] = lab
                stats["isco88"] = stats.get("isco88", 0) + 1

        # Source of current description_en
        en = r["description_en"].strip()
        da = r["description_da"].strip()
        if not en:
            r["description_en_source"] = "empty"
        elif r["description_en_official"].strip() and en == r["description_en_official"]:
            # description_en matches the official one — label it accordingly
            r["description_en_source"] = {
                "HEA_ICD10": "who-icd10",
                "HEA_atc": "who-atc",
                "LAB_db07": "nace2",
                "LAB_disco08": "isco08",
                "LAB_disco": "isco88",
            }.get(cat, "official")
        elif da and en.lower() == da.lower():
            r["description_en_source"] = "copy-of-da"
        else:
            r["description_en_source"] = "translated"

    # Source distribution
    from collections import Counter
    src_cnt = Counter(r["description_en_source"] for r in rows)
    print("description_en_source distribution:")
    for s, n in src_cnt.most_common():
        print(f"  {s}: {n}")
    print("\ndescription_en_official filled by category:")
    for s, n in stats.items():
        print(f"  {s}: {n}")

    total_official = sum(1 for r in rows if r["description_en_official"].strip())
    print(f"\nTotal rows with description_en_official: {total_official}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows with {len(fieldnames)} columns")


if __name__ == "__main__":
    main()
