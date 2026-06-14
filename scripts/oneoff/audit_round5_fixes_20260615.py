#!/usr/bin/env python3
"""Audit round 5 (2026-06-15): apply workflow-confirmed, adversarially-verified resolutions.

A multi-agent workflow (resolver + adversarial verifier per category) searched
the repo's official sources for every residual unresolved/untranslated MASTER
row. 184 resolutions were confirmed (verbatim source match + code-system check);
201 rows were confirmed genuinely unresolvable (left untouched); 1 proposal was
adversarially REJECTED (proposed Danish appeared in no source). Every confirmed
item was then re-verified by hand against its cited source before this script.

Applied (per category, each with its real cited source):

- DEM_opr 5157/5393/5223 -> Palæstina/Vestbredden/Gaza (lookup_dictionaries/
  DEM_statsb_dict.csv; DEM_opr & DEM_statsb share DST landekode — 223 shared
  codes, 0 semantic conflicts). ALSO fixes a real bug: 5157's English was
  "Kosovo" (Kosovo is code 5761, not 5157).
- LAB_db07 18 of the 19 [Unresolved] 5-digit codes -> resolved from
  db07_v1_2008.csv (the v1 edition, which carries all 5 levels and was not
  loaded in the earlier db07 passes). Each is a leading-zero-stripped 6-digit
  code (11200 = 01.12.00 'Dyrkning af ris'); all 18 land on valid sequential
  agriculture/forestry/fishing/mining titles, and every one with firm-level
  co-occurrence data agrees (16300->14190 share 1.0, 17000->15000 share 1.0,
  89100->143000 share 1.0, 31200->50100 share 0.75). Treated exactly like the
  round-1/round-2 dst_db07_leading_zero rows: da=DST title, en/official=NACE
  Rev 2 class, parent re-pointed to the zero-restored class, basis in
  description_da_alt, confidence high (co-occ-confirmed) else medium. The 19th
  (12110) does NOT zero-restore to a real DB07 code and stays unresolved.
- EDU_course 112 empty-da -> filled in the category's established house style
  ('Course <subject>' / 'Course: <english>'); the value IS the Danish subject
  name (Engelsk, Matematik, ...). Matches the 51 already-filled rows.
- EDU_field 34 -> translation-only: Danish unchanged (correct register text),
  English translated ('Teknologi u.n.a.' -> 'Technology, not further specified').
- LAB_disco08 5 armed-forces codes -> raw/LAB_disco.csv (DISCO-08) + ISCO-08.
- SOC_overfkod -/X -> raw/dst_downloads/KRIN_codebook.md (IND_OVERFKOD).
- LAB_tilstand 17100 -> 'SU' (raw/LAB_tilstand_kode.txt).
- SOC_ger7 0 -> 'Uoplyst' (raw/dst_downloads/ger7.csv).
- DEM_manual_bin_antefam 8 range bins -> Danish filled to the documented bin
  convention (raw/bin_instructions.txt) matching the verbatim single-number
  siblings; English already present.

NOT applied: LAB_udd_besk_kode_nullified_1 (adversarially rejected); LAB_akm 3
(resolver crashed on an API false-positive; they are model-derived type_akm_*
tags with no DST source — left unresolved like the SOC model-indicators).

Run from the repo root; regenerate MAPPINGS/, HIERARCHY_SUMMARY.csv,
SOURCE_CATALOG.csv and vocab_hierarchy.json afterwards.
"""

import csv
import json
import sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
RESULT = "/tmp/wf_result.json"

# ---- references for LAB_db07 ----
db07_v1 = {}
with open("raw/dst_downloads/db07_v1_2008.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        db07_v1[r["KODE"].replace(".", "")] = r["TITEL"].strip()
nace2 = {}
for r in csv.DictReader(open("raw/dst_downloads/nace_rev2_en.csv")):
    nace2[r["Code"].replace(".", "")] = r["Description"].strip()
xw = {x["code"]: x for x in csv.DictReader(open(
    "crosswalks/empirical/industry_crosswalk_empirical.csv")) if x["family"] == "db07"}

# db07 codes with co-occurrence agreement -> high confidence, else medium
DB07_HIGH = {"16300", "17000", "89100", "31200", "14920"}

result = json.load(open(RESULT))
confirmed = {c["code"]: c for c in result["confirmed"]}

# simple (source, en_source) per category for the straightforward pockets
PROV = {
    "DEM_opr":                ("dst_landekode_statsb", "translated"),
    "EDU_course":             ("CSV:EDU_course", "translated"),
    "EDU_field":              (None, "translated"),         # keep source; retag en
    "LAB_disco08":            ("raw/LAB_disco.csv (DISCO-08)", "isco08"),
    "SOC_overfkod":           ("dst_krin_codebook", "translated"),
    "LAB_tilstand":           ("raw/LAB_tilstand_kode.txt", "translated"),
    "SOC_ger7":               ("dst_ger7", "translated"),
    "DEM_manual_bin_antefam": ("raw/bin_instructions.txt", "translated"),
}

with open(MASTER, newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

counts = {}


def bump(k, n=1):
    counts[k] = counts.get(k, 0) + n


applied = set()
for r in rows:
    c = confirmed.get(r["code"])
    if not c:
        continue
    cat, val = r["category"], r["value"]

    if cat == "LAB_db07":
        zkey = "0" + val
        title = db07_v1.get(zkey)
        if title != c["final_da"]:
            sys.exit(f"FATAL: db07 {val} v1 title {title!r} != confirmed {c['final_da']!r}")
        cls4 = zkey[:4]
        en = nace2.get(cls4, c["final_en"])
        r["description_da"] = title
        r["description_en"] = en
        r["description_en_official"] = en if cls4 in nace2 else ""
        r["description_en_official_source"] = ("nace2-parent" if cls4 in nace2 else "")
        r["description_en_source"] = "nace2" if cls4 in nace2 else "translated"
        r["description_da_alt"] = (
            f"5-cifret kode = 6-cifret DB07 med foranstillet nul fjernet "
            f"(0{val} = {zkey[:2]}.{zkey[2:4]}.{zkey[4:]}); DST DB07 v1:2008-titel")
        r["source"] = "dst_db07_leading_zero"
        r["parent_code"] = "LAB_db07_0" + val[:3]
        r["confidence_level"] = "high" if val in DB07_HIGH else "medium"
        bump("LAB_db07 [Unresolved] -> v1:2008 leading-zero title")

    else:
        # generic: write confirmed da/en
        if c["final_da"].strip():
            r["description_da"] = c["final_da"]
        if c["final_en"].strip():
            r["description_en"] = c["final_en"]
        src, en_src = PROV.get(cat, (None, "translated"))
        if src is not None:
            r["source"] = src
        r["description_en_source"] = en_src
        if cat == "EDU_field":
            r["description_short"] = c["final_en"]
        bump(f"{cat} resolved")

    applied.add(r["code"])

missing = set(confirmed) - applied
if missing:
    sys.exit(f"FATAL: confirmed codes not found in MASTER: {sorted(missing)[:5]}")

with open(MASTER, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for k in sorted(counts):
    print(f"{counts[k]:6d}  {k}")
print("total applied:", sum(counts.values()), "/ confirmed", len(confirmed))
