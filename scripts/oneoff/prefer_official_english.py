#!/usr/bin/env python3
"""Prefer official English over custom translations — where same-level & verified.

Replaces `description_en` with `description_en_official` ONLY where the official
label provably describes the same classification level as the code (checked per
group, see below), and fixes a block of LAB_db07 rows whose labels were still
the literal misreading of leading-zero-stripped codes.

Rules applied (each verified by sampling before running — see notes.md §9):

1. HEA_ICD10 (en_source translated/copy-of-da): en <- official only when the
   full Danish value (D stripped) is an exact WHO ICD-10 2019 code. Danish
   sub-codes deeper than WHO (e.g. DQ808A 'Sjögren-Larssons syndrom') keep the
   more precise translation.
2. HEA_atc (translated): en <- official only when the value is an exact WHO
   ATC 2021 code.
3. LAB_nace (official from nace2-crosswalk = per-row NAME-matched): en <-
   official. This also fixes real mistranslations ('Fremstilling af konsumis'
   was translated 'Production of consumer goods'; official: 'Manufacture of
   ice cream').
4. LAB_disco / LAB_disco08 (translated): en <- official only when the value
   ends '00' (4-digit ISCO group + DST padding = same level). 6-digit Danish
   subdivisions (931210 'Asfaltarbejde') keep the more precise translation.
5. LAB_db07 (translated, 6-digit, ends '00'): en <- official only when
   description_da matches the official DST DB07 title at the value or at its
   padded class/group level (guards against rows whose da disagrees with the
   literal code reading, e.g. 477100).
6. LAB_db07 5-digit literal-misread block (source CSV:LAB_db07_hierarchical,
   12 rows): a 5-digit value cannot be a literal DB07 code (DB07 is 6-digit) —
   it is a 6-digit code with the leading zero stripped. The zero-restored
   reading was verified per-row against (a) the official DST DB07 title and
   (b) the empirical DB93 co-occurrence partner in
   crosswalks/empirical/industry_crosswalk_empirical.csv (e.g. 14100:
   DST 01.41.00 'Avl af malkekvæg' + DB93 partner 'Malkekvæghold', share 0.99
   — NOT 'Fremstilling af beklædningsartikler'). description_da/_en/official
   are re-set from the DST DB07 title and the NACE Rev 2 class.
7. LAB_db07 wrong officials cleared: the 23 empirically-recovered and 19
   unresolved 5-digit rows (plus 999999/514620) still carried
   description_en_official from the literal misreading ('11100' ->
   'Manufacture of beverages'); contradicting officials are cleared.
8. A few garbled empirical-row translations fixed from the Danish
   ('Hortithnries' -> 'Market gardens', 'Agerbrug, by the way' -> 'Other
   arable farming', ...).

Run from the repo root; regenerate MAPPINGS/, SOURCE_CATALOG.csv and
vocab_hierarchy.json afterwards.
"""

import csv
import json
import re
import sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# ---------------------------------------------------------------- references
who_icd = set()
for r in csv.DictReader(open("raw/dst_downloads/icd10_who_2019_en.csv")):
    who_icd.add(r["code"].replace(".", ""))

who_atc = set()
for r in csv.DictReader(open("raw/dst_downloads/atc_who_2021_en.csv")):
    who_atc.add(r["atc_code"])

nace2_en = {}
for r in csv.DictReader(open("raw/dst_downloads/nace_rev2_en.csv")):
    nace2_en[r["Code"].replace(".", "")] = r["Description"].strip()

db07_titles = {}  # digits-key -> set of titles across v2+v3
for fn in ("raw/dst_downloads/db07_v2_2013.csv", "raw/dst_downloads/db07_v3_2014.csv"):
    with open(fn, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            db07_titles.setdefault(r["KODE"].replace(".", ""), set()).add(r["TITEL"].strip())

# value -> (zfill DST title, DB93 partner text, cooc share, confidence)
# verified row by row against the empirical crosswalk + DST DB07 (see docstring)
DB07_ZFILL = {
    "14100": ("12110 Malkekvæghold", 0.985, "high"),
    "91000": ("112000 Teknisk servicevirksomhed ifm. olie-/gasudvinding", 1.0, "high"),
    "16200": ("14200 Servicevirksomhed ifm. husdyravl", 0.796, "medium"),
    "16100": ("14110 Landbrugsmaskinstationer", 0.974, "high"),
    "81100": ("141120 Stenfiskeri", 0.034, "low"),
    "14200": ("12190 Anden kvægavl", 0.922, "high"),
    "81200": ("142100 Grus- og sandgrave, sandsugning", 0.980, "high"),
    "14300": ("12210 Stutterier", 0.902, "high"),
    "99000": ("142100 Grus- og sandgrave, sandsugning (n=4)", 1.0, "low"),
    "32200": ("50200 Dambrug og fiskeavl", 0.998, "high"),
    "32100": ("50200 Dambrug og fiskeavl", 0.988, "high"),
    "62000": (None, None, "low"),  # no co-occurrence; structural + DST title only
}

# garbled / wrong empirical-row translations, fixed from the Danish
FIX_EMPIRICAL_EN = {
    "11100": "Grain growing",
    "11300": "Market gardens",
    "12800": "Market gardens",
    "11900": "Other arable farming",
    "13000": "Plant nurseries",
    "15000": "Crop growing combined with animal husbandry (mixed farming)",
    "14700": "Poultry farming",
    "14500": "Sheep and goat farming",
    "16400": "Industrial production and breeding of seeds",
    "89900": "Other raw materials extraction n.e.c.",
}

CLEAR_OFFICIAL_EXTRA = {"999999", "514620"}  # off contradicts the resolved da

VIA = re.compile(r"\s*\(via \d+\)\s*$")


def db07_da_matches(value, da):
    base = VIA.sub("", da).strip()
    for key in (value, value[:4], value[:3], value[:2]):
        if base in db07_titles.get(key, ()):
            return True
    return False


with open(MASTER, newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

counts = {}


def bump(k):
    counts[k] = counts.get(k, 0) + 1


for r in rows:
    cat, val = r["category"], r["value"]
    en, off = r["description_en"].strip(), r["description_en_official"].strip()
    en_src, off_src = r["description_en_source"], r["description_en_official_source"]

    if cat == "HEA_ICD10" and off and off != en and en_src in ("translated", "copy-of-da"):
        stripped = val[1:] if val.startswith("D") else val
        if stripped in who_icd:
            r["description_en"], r["description_en_source"] = off, "who-icd10"
            bump("icd10 en<-official (exact WHO code)")

    elif cat == "HEA_atc" and off and off != en and en_src == "translated":
        if val in who_atc:
            r["description_en"], r["description_en_source"] = off, "who-atc"
            bump("atc en<-official (exact WHO code)")

    elif cat == "LAB_nace" and off and off != en and en_src == "translated" \
            and off_src == "nace2-crosswalk":
        r["description_en"], r["description_en_source"] = off, "nace2-crosswalk"
        bump("nace en<-official (name-crosswalked)")

    elif cat in ("LAB_disco", "LAB_disco08") and off and off != en \
            and en_src == "translated" and val.endswith("00"):
        r["description_en"], r["description_en_source"] = off, off_src
        bump(f"{cat} en<-official (4-digit+padding)")

    elif cat == "LAB_db07" and len(val) == 6 and off and off != en \
            and en_src == "translated" and val.endswith("00") \
            and db07_da_matches(val, r["description_da"]):
        r["description_en"], r["description_en_source"] = off, off_src
        bump("db07 en<-official (da matches DST title)")

    elif cat == "LAB_db07" and len(val) == 5:
        if r["source"] == "CSV:LAB_db07_hierarchical":
            if val not in DB07_ZFILL:
                sys.exit(f"FATAL: unexpected literal 5-digit db07 row {val}")
            zkey = "0" + val
            titles = db07_titles.get(zkey)
            if not titles:
                sys.exit(f"FATAL: no DST DB07 title for {zkey}")
            nace = nace2_en.get(zkey[:4])
            if not nace:
                sys.exit(f"FATAL: no NACE2 class for {zkey[:4]}")
            partner, share, conf = DB07_ZFILL[val]
            r["description_da"] = sorted(titles)[-1]
            basis = (f"5-cifret kode = 6-cifret DB07 med foranstillet nul "
                     f"fjernet (0{val} = {zkey[:2]}.{zkey[2:4]}.{zkey[4:]})")
            if partner:
                basis += f"; DB93-samtidighedspartner: {partner} (share {share})"
            else:
                basis += "; ingen samtidighedsdata - strukturelt + DST DB07-titel"
            r["description_da_alt"] = basis
            r["description_en"] = nace
            r["description_en_source"] = "nace2"
            r["description_en_official"] = nace
            r["description_en_official_source"] = "nace2"
            r["source"] = "dst_db07_leading_zero"
            r["confidence_level"] = conf
            bump("db07 5-digit literal misread RELABELLED")
        else:
            # empirically-recovered or unresolved rows: clear contradicting
            # officials (the literal NACE reading), fix garbled translations
            if off:
                r["description_en_official"] = ""
                r["description_en_official_source"] = ""
                bump("db07 wrong official CLEARED")
            if val in FIX_EMPIRICAL_EN and r["description_en"] != FIX_EMPIRICAL_EN[val]:
                r["description_en"] = FIX_EMPIRICAL_EN[val]
                bump("db07 empirical en fixed")

    if cat == "LAB_db07" and val in CLEAR_OFFICIAL_EXTRA and r["description_en_official"]:
        r["description_en_official"] = ""
        r["description_en_official_source"] = ""
        bump("db07 wrong official CLEARED")

with open(MASTER, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for k in sorted(counts):
    print(f"{counts[k]:6d}  {k}")
print("total changes:", sum(counts.values()))
