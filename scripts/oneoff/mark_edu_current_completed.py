#!/usr/bin/env python3
"""Mark EDU education English as current vs completed.

EDU_udd  = KOTRE:UDD  = the education being studied  -> "[current education]"
EDU_audd = KOTRE:AUDD = the qualification completed  -> "[completed qualification]"
These are the same 4-digit programme codes in two event contexts, so "Law, bach." appeared
identically in both. Appending a status marker to description_en disambiguates the cross-category
duplicates and makes each English self-describing. description_da / description (Danish) untouched.
Non-programme status sentinels (Discontinued, No education, Unknown, In progress, ...) are skipped.

Re-runnable (idempotent). Usage: python3 scripts/mark_edu_current_completed.py [--dry-run]
"""
import argparse, csv, re

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
MARK = {"EDU_udd": " [current education]", "EDU_audd": " [completed qualification]"}
SKIP = re.compile(r"(no education|discontinued|unknown|not stated|in progress|uoplyst|interrupted|ingen uddannelse|abandoned)", re.I)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    n = {"EDU_udd": 0, "EDU_audd": 0}; skipped = 0
    for r in rows:
        cat = r.get("category")
        if cat not in MARK:
            continue
        en = (r.get("description_en") or "").strip()
        if not en:
            continue
        if "[current education]" in en or "[completed qualification]" in en:
            continue  # idempotent
        if SKIP.search(en):
            skipped += 1; continue
        r["description_en"] = en + MARK[cat]
        n[cat] += 1
    print(f"marked: EDU_udd={n['EDU_udd']} (current), EDU_audd={n['EDU_audd']} (completed); sentinels skipped={skipped}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
