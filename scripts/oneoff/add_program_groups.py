#!/usr/bin/env python3
"""Add program_group + is_primary_code for EDU_udd / EDU_audd version-renumbered variants.

DST renumbers education codes across classification versions, so one programme has many distinct
codes (e.g. 10 EDU_udd codes all = "HA almen erhvervsøkonomi, bach."). This groups codes by their
authoritative Danish programme name (description_da) WITHIN a category and flags the canonical
(highest-prevalence) code per group, so consumers can collapse the historical variants.

Columns added (populated for EDU_udd / EDU_audd only; empty elsewhere):
  program_group   — the DST programme name (description_da); shared by all version-variants
  is_primary_code — "True" for the highest pct_people code in (category, program_group), else "False"

Re-runnable. Usage: python3 scripts/add_program_groups.py [--dry-run]
"""
import argparse, csv
from collections import defaultdict

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
NEWCOLS = ["program_group", "is_primary_code"]
EDU = {"EDU_udd", "EDU_audd"}


def pct(r):
    try:
        return float((r.get("pct_people") or "").strip())
    except Exception:
        return 0.0


def tid(r):
    try:
        return int((r.get("token_id") or "0").strip())
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    for c in NEWCOLS:
        if c not in fns:
            fns.append(c)
    for r in rows:
        for c in NEWCOLS:
            r.setdefault(c, "")

    groups = defaultdict(list)
    for r in rows:
        if r.get("category") in EDU:
            da = (r.get("description_da") or "").strip()
            if da:
                groups[(r["category"], da)].append(r)

    n_codes = n_groups = n_collapsible = 0
    for (cat, da), rs in groups.items():
        # primary = highest pct_people, tie-break lowest token_id
        primary = sorted(rs, key=lambda r: (-pct(r), tid(r)))[0]
        for r in rs:
            r["program_group"] = da
            r["is_primary_code"] = "True" if r is primary else "False"
            n_codes += 1
        n_groups += 1
        if len(rs) > 1:
            n_collapsible += 1

    print(f"EDU program groups: {n_groups} groups over {n_codes} codes; "
          f"{n_collapsible} groups have >1 code (collapsible version-variants)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER} (+columns {NEWCOLS})")


if __name__ == "__main__":
    main()
