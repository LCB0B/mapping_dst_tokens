#!/usr/bin/env python3
"""Clear `description_en_official` on HEA_ICD10 rows that claim WHO ICD-10 as
their source but whose code matches NO WHO ICD-10 2019 entry at any level.

Audit (2026-06) found 25 such rows carrying a WRONG chapter-level label:
  - 18x `DI84*` (I84 = haemorrhoids; removed from WHO ICD-10, now K64) were
    labelled "Certain infectious and parasitic diseases".
  - 7x `DVR*` (Danish supplementary codes, not standard ICD chapters) were
    labelled "Mental and behavioural disorders".
A wrong "official" label falsely asserts WHO authority (HARD RULES), so we
clear description_en_official + description_en_official_source for these. The
machine-translated `description_en` (broad field) and `description_da` are
left untouched.

Usage: python3 scripts/fix_icd_false_official.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
WHO = "raw/dst_downloads/icd10_who_2019_en.csv"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    who = {r["code"].replace(".", "").upper(): r["title_en"].strip()
           for r in csv.DictReader(open(WHO))}

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    cleared = []
    for r in rows:
        if r["category"] != "HEA_ICD10":
            continue
        if (r.get("description_en_official_source") or "").strip().lower() != "who-icd10":
            continue
        off = (r.get("description_en_official") or "").strip()
        if not off:
            continue
        v = (r.get("value") or "").strip().upper()
        key = v[1:] if v.startswith("D") else v
        # matches any WHO ancestor?
        if any(key[:L] in who and who[key[:L]].lower() == off.lower()
               for L in range(len(key), 2, -1)):
            continue
        cleared.append((r["code"], off))
        r["description_en_official"] = ""
        r["description_en_official_source"] = ""

    print(f"Cleared false WHO official label on {len(cleared)} HEA_ICD10 rows:")
    for code, off in cleared:
        print(f"   {code:14s} was: {off!r}")

    if args.dry_run:
        print("\n[dry-run] no changes written"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER}")


if __name__ == "__main__":
    main()
