#!/usr/bin/env python3
"""Dump a batch of worklist rows (by id = line order) for in-context translation.
Usage: python3 scripts/dump_batch.py START COUNT
Prints compact lines: id | spec_en | DA | [spec4] | [plo]  so the translator has
all disambiguating context on one line. Also reports how many remain untranslated.
"""
import csv, sys, os

WL = "scripts/worklists/hea_speciale_worklist.csv"
TR = "scripts/worklists/hea_speciale_translations.tsv"

rows = list(csv.DictReader(open(WL, encoding="utf-8")))
done = set()
if os.path.exists(TR):
    for line in open(TR, encoding="utf-8"):
        p = line.split("\t")
        if p and p[0].isdigit():
            done.add(int(p[0]))

start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
count = int(sys.argv[2]) if len(sys.argv) > 2 else 150
print(f"# total={len(rows)} done={len(done)} remaining={len(rows)-len(done)}")
for i in range(start, min(start + count, len(rows))):
    if i in done:
        continue
    r = rows[i]
    extra = ""
    if r["plo_fuller"]:
        extra = f"  ||PLO: {r['plo_fuller']}"
    elif r["spec4_txt"] or r["spec3_txt"]:
        extra = f"  ||LVL: {r['spec4_txt']} / {r['spec3_txt']}"
    print(f"{i}\t[{r['specialty_name_en']}]\t{r['description_da']}{extra}")
