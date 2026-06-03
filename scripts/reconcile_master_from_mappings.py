#!/usr/bin/env python3
"""Reconcile MASTER_CATEGORY_MAPPINGS.csv against the per-category MAPPINGS/
files for the three provenance/official columns where MASTER was accidentally
clobbered by a late rewrite while the MAPPINGS files retained the good data.

Audit finding (2026-06-03 recovery):
  Regenerating MAPPINGS/ from MASTER produced drift in 45 files, isolated to:
    - description_en_official          : 6,128 rows MASTER had EMPTY but MAPPINGS
                                         had a sourced value (all HEA_speciale,
                                         src=dst-ssr-specialty; only 1 row MASTER ahead)
    - description_en_official_source   : same 6,128 rows
    - description_en_source            : 6,746 rows flattened to generic 'translated'
                                         in MASTER vs specific tags in MAPPINGS
  The loss was accidental (fix_unreliable_official_en.py only ever touches
  LAB_disco*/LAB_db07, never HEA_speciale). The MAPPINGS values are sourced
  (verified e.g. ssr_speciale_2digit.csv: 80=Almen Lægehjælp=GP, 19=Øjenlægehjælp).

Reconciliation rules (no invention — only recovers values already present in
the committed MAPPINGS, or recomputes objectively from existing columns):
  * description_en_official / _official_source: prefer the non-empty value.
    (No true conflicts exist; the single MASTER-ahead row is preserved.)
  * description_en_source: prefer a SPECIFIC source tag over a generic one
    (translated/copy-of-da/empty/generated_pattern). When both sides are
    generic but differ (copy-of-da vs translated), recompute objectively:
    'copy-of-da' iff description_en == description_da, else 'translated'.

Writes MASTER in place. Run scripts/regenerate_mappings.py afterwards; the
MAPPINGS diff should then be empty (MASTER becomes the true superset).

Usage: python3 scripts/reconcile_master_from_mappings.py [--dry-run]
"""
import argparse, csv, glob
from collections import Counter

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
GENERIC = {"", "translated", "copy-of-da", "empty", "generated_pattern"}


def load_mappings():
    mp = {}
    for f in glob.glob("hierarchical_vocab/MAPPINGS/*_mappings.csv"):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                mp[r["code"]] = r
    return mp


def pick_en_source(map_v, mas_v, en, da):
    map_v, mas_v = (map_v or "").strip(), (mas_v or "").strip()
    if map_v == mas_v:
        return mas_v, False
    map_spec, mas_spec = map_v not in GENERIC, mas_v not in GENERIC
    if map_spec and not mas_spec:
        return map_v, True
    if mas_spec and not map_spec:
        return mas_v, False
    if map_spec and mas_spec:
        return mas_v, "conflict"  # both specific & differ — keep master, flag
    # both generic & differ -> recompute objectively from en/da
    en, da = (en or "").strip(), (da or "").strip()
    new = "copy-of-da" if (en and en == da) else ("translated" if en else "")
    return new, (new != mas_v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mp = load_mappings()
    with open(MASTER, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fns = list(reader.fieldnames)
        rows = list(reader)

    chg = Counter()
    conflicts = []
    for r in rows:
        m = mp.get(r["code"])
        if not m:
            continue
        # official + official_source: prefer non-empty
        if not (r.get("description_en_official") or "").strip() and (m.get("description_en_official") or "").strip():
            r["description_en_official"] = m["description_en_official"]
            r["description_en_official_source"] = m.get("description_en_official_source", "")
            chg["description_en_official restored"] += 1
        # description_en_source: specific-wins / objective recompute
        new_src, changed = pick_en_source(
            m.get("description_en_source"), r.get("description_en_source"),
            r.get("description_en"), r.get("description_da"))
        if changed == "conflict":
            conflicts.append((r["code"], m.get("description_en_source"), r.get("description_en_source")))
        elif changed:
            r["description_en_source"] = new_src
            chg["description_en_source updated"] += 1

    print("Changes:")
    for k, n in chg.most_common():
        print(f"  {n:6d}  {k}")
    if conflicts:
        print(f"\n  {len(conflicts)} both-specific conflicts (kept MASTER, review):")
        for c in conflicts[:10]:
            print("    ", c)

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER}")


if __name__ == "__main__":
    main()
