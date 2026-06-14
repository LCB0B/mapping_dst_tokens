#!/usr/bin/env python3
"""Row-by-row audit fixes (2026-06-09, round 3).

Findings from running every MASTER row through per-row validators:

1. `value` column desynced from `code` on 1,263 rows: HEA_speciale values
   lost their leading zero (code HEA_speciale_090120 / value '90120' — same
   serialization-bug class as the `.0` issue), and the DEM_manual_bin_*
   values contain a chunk of the category name. value is re-derived from
   code (code = '<category>_<value>' is the repo convention).
2. 10 truncated SOC_ger7 English texts (rule-based translator dropped the
   leading noun: 'Forsøg på manddrab' -> ' on homicide') re-translated in
   full from the register Danish, keyed by value with the Danish asserted.
3. EDU leftovers: 'Biofysiske programmes', three 'Grafisk technician' rows,
   and the empty 'Grade code: ' for EDU_grade NA.
4. SOC_frakkod_UJ mojibake ('Âø') aligned with the raw source text
   (raw/SOC_frakkod.txt has '¿' at that position).
5. Whitespace hygiene: runs of spaces collapsed and ends stripped in
   description_da / description_en / description_en_official /
   description_short (register column-alignment artifacts; semantics
   unchanged). The legacy `description` column is left untouched.
6. PROVENANCE HONESTY: description_en_official_source gets a '-parent'
   suffix where the official text is verbatim the label of an ANCESTOR code
   (e.g. Danish sub-code DQ808A carrying WHO's Q80.8 title), so consumers
   filtering on officials can tell same-level officials from inherited ones.
   Officials whose code is the reference code + zero padding (disco 441900 =
   ISCO 4419) count as same-level and keep their tag. Verified: every
   official text matches its reference exactly at some ancestor — there are
   no fabricated officials.

Run from the repo root; regenerate MAPPINGS/, SOURCE_CATALOG.csv and
vocab_hierarchy.json afterwards.
"""

import csv
import re
import sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# ----------------------------------------------------------------- references
who_icd = {}
for r in csv.DictReader(open("raw/dst_downloads/icd10_who_2019_en.csv")):
    who_icd[r["code"].replace(".", "")] = r["title_en"].strip()
nace2 = {}
for r in csv.DictReader(open("raw/dst_downloads/nace_rev2_en.csv")):
    nace2[r["Code"].replace(".", "")] = r["Description"].strip()
isco08, isco88 = {}, {}
for r in csv.DictReader(open("raw/dst_downloads/isco08_en.csv")):
    isco08[r["code"]] = r["title_en"].strip()
for r in csv.DictReader(open("raw/dst_downloads/isco88_en.csv")):
    isco88[r["code"]] = r["title_en"].strip()

GER7_FIX = {
    "1286525": ("Forvoldt fare for liv eller førlighed",
                "Causing danger to life or limb"),
    "2610016": ("Forpligtelser ved færdselsuheld § 9, stk. 2, nr. 2-6",
                "Obligations at traffic accidents, § 9(2) nos. 2-6"),
    "2610012": ("Forpligtelser ved færdselsuheld, undlader at standse",
                "Obligations at traffic accidents, failure to stop"),
    "1240505": ("Forsøg på manddrab",
                "Attempted homicide"),
    "1410760": ("Forstyrrelse af folketingets møder o.l.",
                "Disruption of parliamentary (Folketing) sessions etc."),
    "2610089": ("Forurening af vej mv.",
                "Pollution of roads etc."),
    "1410739": ("Foregivelse af offentlig myndighed",
                "Impersonation of public authority"),
    "1445765": ("Forstyrrelse af samfærdselsmidlerne",
                "Disruption of means of public transport"),
    "2610014": ("Forpligtelser ved færdselsuheld § 9, stk. 2, nr. 1 (undlader at yde hjælp)",
                "Obligations at traffic accidents, § 9(2) no. 1 (failure to render assistance)"),
    "1445725": ("Forstyrrelse af transportmidler",
                "Disruption of means of transport"),
}

EDU_EN_FIX = {
    "EDU_field_453025": "Biophysical programmes",
    "EDU_disced_30453010": "Graphic technician",
    "EDU_udd_4150": "Graphic technician [current education]",
    "EDU_audd_4467": "Graphic technician [completed qualification]",
    "EDU_grade_NA": "Grade code: NA",
}

SPACES = re.compile(r" {2,}")

with open(MASTER, newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

counts = {}


def bump(k, n=1):
    counts[k] = counts.get(k, 0) + n


def official_level(src, ref, val_eff, off):
    """exact | padded (same level) | parent | None (no verbatim match)."""
    if ref.get(val_eff) == off:
        return "exact"
    k = val_eff
    while len(k) > 1:
        k = k[:-1]
        if ref.get(k) == off:
            pad = val_eff[len(k):]
            return "padded" if pad and set(pad) == {"0"} else "parent"
    return None


for r in rows:
    cat, val, code = r["category"], r["value"], r["code"]

    # 1. value re-derived from code
    if cat != "special_tokens" and code.startswith(cat + "_") \
            and code != f"{cat}_{val}":
        r["value"] = code[len(cat) + 1:]
        bump(f"value resynced from code ({cat.split('_')[0]})")

    # 2. truncated ger7 translations
    if cat == "SOC_ger7" and r["value"] in GER7_FIX:
        exp_da, new_en = GER7_FIX[r["value"]]
        if r["description_da"].strip() != exp_da:
            sys.exit(f"FATAL: da drift on ger7 {r['value']}: {r['description_da']!r}")
        r["description_en"] = new_en
        bump("ger7 truncated en fixed")

    # 3. EDU leftovers
    if code in EDU_EN_FIX:
        r["description_en"] = EDU_EN_FIX[code]
        bump("EDU en leftover fixed")

    # 4. frakkod mojibake -> raw source text
    if code == "SOC_frakkod_UJ" and "Âø" in r["description_da"]:
        r["description_da"] = r["description_da"].replace("Âø", "¿")
        bump("frakkod mojibake aligned with raw")

    # 5. whitespace hygiene
    for col in ("description_da", "description_en", "description_en_official",
                "description_short"):
        x = r[col]
        y = SPACES.sub(" ", x).strip()
        if y != x:
            r[col] = y
            bump(f"whitespace normalised ({col})")

    # 6. '-parent' retag for ancestor-level officials
    off, src = r["description_en_official"].strip(), r["description_en_official_source"].strip()
    if off and src in ("who-icd10", "isco08", "isco88", "nace2"):
        if src == "who-icd10":
            ref, val_eff = who_icd, (r["value"][1:] if r["value"].startswith("D") else r["value"])
        elif src == "nace2":
            ref, val_eff = nace2, ("0" + r["value"] if len(r["value"]) == 5 else r["value"])
        elif src == "isco08":
            ref, val_eff = isco08, r["value"]
        else:
            ref, val_eff = isco88, r["value"]
        level = official_level(src, ref, val_eff, off)
        if level is None:
            sys.exit(f"FATAL: official on {code} matches reference nowhere: {off!r}")
        # ICD-10 has no zero padding — a trailing 0 is a real subcode (A00.0),
        # so an ancestor match is always parent-level there
        if level == "padded" and src == "who-icd10":
            level = "parent"
        if level == "parent":
            r["description_en_official_source"] = src + "-parent"
            bump(f"official retagged {src}-parent")

with open(MASTER, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for k in sorted(counts):
    print(f"{counts[k]:6d}  {k}")
print("total:", sum(counts.values()))
