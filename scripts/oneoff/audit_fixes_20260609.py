#!/usr/bin/env python3
"""Audit fixes 2026-06-09 (follow-up to prefer_official_english.py).

1. LAB_db07 5-digit rows (54): parent_code was the literal 4-digit truncation
   (14100 -> LAB_db07_1410), which is wrong under the established
   leading-zero-stripped reading (14100 = 014100, class 01.41). parent_code
   is re-pointed at the zero-restored class, written WITH the leading zero
   (LAB_db07_0141) so it is unambiguous and resolvable against the DST DB07
   files.
2. LAB_db07 en <- official for rows whose description_da exactly matches a
   DST DB07 title *including the v1 (2008) edition* (the earlier guard only
   loaded v2/v3 and missed v1-worded rows like 711100 'Arkitektvirksomhed').
   Same constraints as before: 6-digit, ends '00', official differs.
3. LAB_db07 47911x block (8 rows) + 222290: description_da/_en carried the
   GROUP label ('Detailhandel undtagen fra forretninger, stalde og markeder
   (via 479)') although the official 4-digit class is known and finer
   (47.91 internet/mail-order retail). Upgraded to the DST class title (da)
   and NACE Rev 2 class title (en), keeping a '(via XX.XX)' marker because
   the 6-digit code itself is not separately listed by DST. Old label kept
   in description_da_alt.
4. SOC_ger7 '(via NNNN)' markers stripped on the 75 rows where the value is
   the 4-digit group + '000' padding — there the group label IS the
   same-level label and the marker wrongly suggests a borrowed coarser label.
   (2 genuinely-deeper rows, 1312715/1430510, keep their markers.)
5. EDU translation cruft: ' (via jura)' / ' (via 51)' stripped from 6
   EDU_audd English texts; EDU_field 256020 English aligned with the Danish
   ('i øvrigt' was dropped and a '(via ...)' marker left in).

Run from the repo root; regenerate MAPPINGS/, SOURCE_CATALOG.csv and
vocab_hierarchy.json afterwards.
"""

import csv
import re
import sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

db07_titles = {}  # digits-key -> set of titles across v1+v2+v3
for fn in ("raw/dst_downloads/db07_v1_2008.csv",
           "raw/dst_downloads/db07_v2_2013.csv",
           "raw/dst_downloads/db07_v3_2014.csv"):
    with open(fn, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            db07_titles.setdefault(r["KODE"].replace(".", ""), set()).add(r["TITEL"].strip())

# current (v3, falling back v2) single title per key for class upgrades
db07_current = {}
for fn in ("raw/dst_downloads/db07_v2_2013.csv", "raw/dst_downloads/db07_v3_2014.csv"):
    with open(fn, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            db07_current[r["KODE"].replace(".", "")] = r["TITEL"].strip()

CLASS_UPGRADE = {"479111", "479112", "479113", "479114", "479115",
                 "479116", "479117", "479119", "222290"}

GER7_DICT = {}
for r in csv.DictReader(open("lookup_dictionaries/SOC_ger7_dict.csv")):
    GER7_DICT[r["code"].replace("SOC_ger7_", "")] = r["description"].strip()

VIA = re.compile(r"\s*\(via \d+\)")

with open(MASTER, newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

counts = {}


def bump(k):
    counts[k] = counts.get(k, 0) + 1


for r in rows:
    cat, val = r["category"], r["value"]

    if cat == "LAB_db07" and len(val) == 5:
        new_parent = "LAB_db07_0" + val[:3]
        if r["parent_code"] != new_parent:
            r["parent_code"] = new_parent
            bump("db07 5-digit parent re-pointed (zero-restored class)")

    elif cat == "LAB_db07" and len(val) == 6:
        off = r["description_en_official"].strip()
        if val in CLASS_UPGRADE:
            cls = val[:4]
            da_cls = db07_current.get(cls)
            if not (da_cls and off):
                sys.exit(f"FATAL: missing class title/official for {val}")
            marker = f" (via {cls[:2]}.{cls[2:]})"
            r["description_da_alt"] = ("Tidligere gruppe-niveau-etiket: "
                                       + r["description_da"])
            r["description_da"] = da_cls + marker
            r["description_en"] = off + marker
            r["description_en_source"] = "nace2"
            r["source"] = "dst_db07_class_label"
            bump("db07 group label upgraded to class level")
        elif off and off != r["description_en"].strip() \
                and r["description_en_source"] == "translated" \
                and val.endswith("00") \
                and r["description_da"].strip() in db07_titles.get(val, ()):
            r["description_en"] = off
            r["description_en_source"] = r["description_en_official_source"]
            bump("db07 en<-official (v1 title match)")

    elif cat == "SOC_ger7" and "(via" in r["description_en"]:
        if len(val) == 7 and val.endswith("000") \
                and GER7_DICT.get(val[:4], "") and GER7_DICT[val[:4]] in r["description_da"]:
            r["description_da"] = VIA.sub("", r["description_da"]).strip()
            r["description_en"] = VIA.sub("", r["description_en"]).strip()
            bump("ger7 same-level '(via)' marker stripped")

    elif cat == "EDU_audd" and "(via jura)" in r["description_en"]:
        r["description_en"] = r["description_en"].replace(" (via jura)", "")
        bump("audd '(via jura)' cruft stripped")
    elif cat == "EDU_audd" and "(via 51)" in r["description_en"]:
        r["description_en"] = r["description_en"].replace(" (via 51)", "")
        bump("audd '(via 51)' cruft stripped")
    elif cat == "EDU_field" and val == "256020":
        r["description_en"] = "Other Middle Eastern languages and societies"
        bump("EDU_field 256020 en aligned with da")

with open(MASTER, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for k in sorted(counts):
    print(f"{counts[k]:6d}  {k}")
print("total:", sum(counts.values()))
