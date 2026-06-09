#!/usr/bin/env python3
"""Add prevalence columns to MASTER from token_occurrences.csv.

token_occurrences.csv columns: token, token_id, n_occurrences, n_people, pct_people.
Joined onto MASTER by `code` == `token` (NOT token_id — token_occurrences uses a different
token_id numbering that disagrees with MASTER in ~all rows). Adds three columns:
  n_occurrences  — total occurrences of the token across the dataset
  n_people       — number of distinct people who have the token
  pct_people     — fraction of people (0-1) who have the token (prevalence)
~40,379/40,465 MASTER rows match; the rest (rare codes absent from the occurrence export,
e.g. very old DEM_birthyear) get empty prevalence (not asserted as 0).

Re-runnable. Usage: python3 scripts/add_prevalence.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
OCC = "token_occurrences.csv"
NEWCOLS = ["n_occurrences", "n_people", "pct_people"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    occ = {}
    for r in csv.DictReader(open(OCC, encoding="utf-8")):
        occ[(r.get("token") or "").strip()] = r
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    for c in NEWCOLS:
        if c not in fns:
            fns.append(c)
    matched = 0
    for r in rows:
        o = occ.get((r.get("code") or "").strip())
        if o:
            r["n_occurrences"] = (o.get("n_occurrences") or "").strip()
            r["n_people"] = (o.get("n_people") or "").strip()
            r["pct_people"] = (o.get("pct_people") or "").strip()
            matched += 1
        else:
            for c in NEWCOLS:
                r.setdefault(c, "")
                if c not in r:
                    r[c] = ""
    print(f"prevalence added to {matched}/{len(rows)} rows ({len(rows)-matched} without occurrence data)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER} (+columns {NEWCOLS})")


if __name__ == "__main__":
    main()
