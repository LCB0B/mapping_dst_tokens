#!/usr/bin/env python3
"""Apply the HEA_speciale re-translations to MASTER.

Sources (by worklist id):
  - scripts/worklists/hea_speciale_auto.tsv         glossary+rules output (id, da_full, en, conf, residual)
  - scripts/worklists/hea_speciale_translations.tsv  hand-authored seed batch (id, da_full, en, conf) — OVERRIDES auto

Adds a new `description_da_full` column. For each HEA_speciale row whose
description_en_source is still 'translated', sets:
  description_en        <- clean English
  description_da_full   <- expanded full Danish
  description_en_source <- 'opus-4-8-medical'
  confidence_level      <- 'medium' (clean) | 'low' (residual/uncertain)
The original abbreviated description_da is left intact (authoritative billing text).

Usage: python3 scripts/apply_hea_speciale_translations.py [--dry-run]
"""
import argparse, csv, sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
WL = "scripts/worklists/hea_speciale_worklist.csv"
AUTO = "scripts/worklists/hea_speciale_auto.tsv"
MANUAL = "scripts/worklists/hea_speciale_translations.tsv"
NEWCOL = "description_da_full"


def load_tsv(path):
    d = {}
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and p[0].isdigit():
                conf = p[3] if len(p) >= 4 else "medium"
                d[int(p[0])] = (p[1], p[2], conf)
    except FileNotFoundError:
        pass
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    wl = list(csv.DictReader(open(WL, encoding="utf-8")))
    auto = load_tsv(AUTO)
    manual = load_tsv(MANUAL)

    # build description_da -> (da_full, en, conf); manual overrides auto.
    # A manual override with an empty da_full reuses the auto-expanded da_full
    # (so residual fixes only need to supply the English).
    by_da = {}
    for i, r in enumerate(wl):
        a = auto.get(i)
        m = manual.get(i)
        if m:
            da_full = m[0] if m[0].strip() else (a[0] if a else "")
            rec = (da_full, m[1], m[2])
        else:
            rec = a
        if rec:
            by_da[r["description_da"]] = rec
    print(f"worklist={len(wl)} auto={len(auto)} manual_overrides={len(manual)} mapped_strings={len(by_da)}")

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    if NEWCOL not in fns:
        fns = fns + [NEWCOL]
    for r in rows:
        r.setdefault(NEWCOL, "")

    n = miss = nlow = 0
    for r in rows:
        if r["category"] != "HEA_speciale":
            continue
        # re-runnable: process rows still 'translated' OR already set by a prior run
        if (r.get("description_en_source") or "").strip().lower() not in ("translated", "opus-4-8-medical"):
            continue
        rec = by_da.get((r.get("description_da") or "").strip())
        if not rec:
            miss += 1; continue
        da_full, en, conf = rec
        r["description_en"] = en
        r[NEWCOL] = da_full
        r["description_en_source"] = "opus-4-8-medical"
        r["confidence_level"] = "low" if conf == "low" else "medium"
        n += 1
        if conf != "high":
            nlow += 1

    print(f"updated {n} HEA_speciale rows ({nlow} confidence=low) | unmapped: {miss}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER} (added column {NEWCOL})")


if __name__ == "__main__":
    main()
