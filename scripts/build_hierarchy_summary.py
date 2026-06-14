#!/usr/bin/env python3
"""Regenerate HIERARCHY_SUMMARY.csv from MASTER_CATEGORY_MAPPINGS.csv.

Per-category counts and description coverage. Previously the file had no
generator and its with_da column had gone stale as descriptions were filled.

Usage (from the repo root):
    python3 scripts/build_hierarchy_summary.py
"""

import csv
from collections import defaultdict

rows = list(csv.DictReader(open("MASTER_CATEGORY_MAPPINGS.csv", newline="")))

agg = defaultdict(lambda: {"prefix": "", "variable": "", "count": 0,
                           "mapped": 0, "with_da": 0, "with_en": 0})
order = []
for r in rows:
    cat = r["category"]
    if cat not in agg:
        order.append(cat)
    a = agg[cat]
    a["prefix"], a["variable"] = r["prefix"], r["variable"]
    a["count"] += 1
    if r["description_en"].strip() or r["description_da"].strip():
        a["mapped"] += 1
    if r["description_da"].strip():
        a["with_da"] += 1
    if r["description_en"].strip():
        a["with_en"] += 1

with open("HIERARCHY_SUMMARY.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["prefix", "variable", "category", "count", "mapped",
                "with_da", "with_en", "coverage_pct"])
    for cat in order:
        a = agg[cat]
        w.writerow([a["prefix"], a["variable"], cat, a["count"], a["mapped"],
                    a["with_da"], a["with_en"],
                    round(100.0 * a["mapped"] / a["count"], 1)])

print(f"wrote HIERARCHY_SUMMARY.csv ({len(order)} categories, {len(rows)} codes)")
