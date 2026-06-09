#!/usr/bin/env python3
"""Apply specific English translations to HEA_ICD10 Danish/Latin sub-codes.

Many Danish ICD-10 sub-codes (5th char A-L etc., a Danish supplementary subdivision not in WHO)
had their description_en collapsed to the coarse WHO PARENT label, so distinct Danish terms shared
one English string. The workflow `icd-da-translate` (translate -> adversarial verify, anchored by
the WHO parent in description_en_official) produced a specific English per code; result map in
/tmp/icd_en.json (or pass --map).

This sets description_en to the specific translation (source=translated). It does NOT touch:
  - description       (the Danish/Latin source text)
  - description_en_official / _source  (the authoritative WHO standard label — preserved)
Re-runnable. Usage: python3 scripts/apply_icd_translations.py [--map PATH] [--dry-run]
"""
import argparse, csv, json

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="scripts/worklists/icd_da_translations.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    en_map = json.load(open(args.map, encoding="utf-8"))

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    changed = same = 0
    for r in rows:
        if r.get("category") != "HEA_ICD10":
            continue
        code = (r.get("code") or "").strip()
        new = en_map.get(code)
        if not new:
            continue
        if new.strip() != (r.get("description_en") or "").strip():
            r["description_en"] = new.strip()
            r["description_en_source"] = "translated"
            changed += 1
        else:
            same += 1
    print(f"HEA_ICD10 description_en updated: {changed} changed, {same} unchanged (already specific)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
