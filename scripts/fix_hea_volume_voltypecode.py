#!/usr/bin/env python3
"""Fix the HEA drug-VOLUME categories that were mislabelled with hallucinated meanings.

Background
----------
13 HEA categories (DDK, DW, DWG, DWK, GA, GI, GP, L, MG, ML, PK, ST, TU) plus the
bare `HEA_` were previously described as "procedure codes" / invented clinical
meanings ("gestational age weeks", "specialist visits", "inpatient days", "lab
tests", "medication prescriptions" ...), all tagged source=none|generated or
vocab_reconciliation, confidence empty/low. These are HARD-RULES violations.

They are in fact the **VOLTYPECODE** unit types for the **VOLUME** variable in
DST's Lægemiddeldatabasen / Lægemiddelstatistikregisteret (LMDB). VOLUME is the
numeric quantity of one medicine package; it must always be read together with
its unit, given by VOLTYPECODE. The `manual_bin_*`/`over_1000` values are binned
VOLUME ranges *in that unit*. The bare `HEA_` (empty value, token interleaved in
the volume block) is the documented blank VOLTYPECODE (non-specific medicine /
quantity / fee / veterinary).

Source (cited, verbatim VOLTYPETXT):
  esundhed.dk · Lægemiddelstatistikregisteret · documentation rid=14 tid=63 vid=396
  https://www.esundhed.dk/api/sitecore/documentation/documentation?rid=14&tid=63&vid=396
  (VOLUME: vid=399). Cross-checked against
  https://www.dst.dk/extranet/ForskningVariabellister/LMDB - Lægemiddeldatabasen.html

This script ONLY rewrites the description/source/confidence columns of these
168 rows. token_id, code, value, prefix, variable are untouched. Re-runnable.

Usage: python3 scripts/fix_hea_volume_voltypecode.py [--dry-run]
"""
import argparse, csv, sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
SRC_TAG = "esundhed:lmdb_voltypecode"
EN_SRC_TAG = "dst-lmdb-voltypecode"

# code -> (Danish VOLTYPETXT label, English meaning).  Verbatim from esundhed vid=396.
UNITS = {
    "DDK": ("DøgnDosis DK", "Danish defined daily dose (DDD-DK)"),
    "DW":  ("DDD WHO Index", "WHO defined daily dose (DDD, main index)"),
    "DWG": ("DDD WHO Guidelines", "WHO defined daily dose (DDD, guidelines list)"),
    "DWK": ("DDD WHO Kombinationsliste", "WHO defined daily dose (DDD, combination list)"),
    "GA":  ("g (aktivt stof)", "grams of active substance"),
    "GI":  ("g (iod)", "grams of iodine"),
    "GP":  ("g (præparat)", "grams of preparation"),
    "L":   ("L", "litres"),
    "MG":  ("mg (aktivt stof)", "milligrams of active substance"),
    "ML":  ("ml", "millilitres"),
    "PK":  ("pakninger", "packages"),
    "ST":  ("Stk", "units (pieces)"),
    "TU":  ("tusind enheder", "thousand units"),
}

BLANK_DA = "ikke-specifikt lægemiddel og/eller ikke-specifik mængde, gebyr eller veterinært lægemiddel"
BLANK_EN = "non-specific medicine and/or non-specific quantity, fee, or veterinary medicine"


def range_text(value):
    """manual_bin_10 -> '10'; manual_bin_10_15 -> '10-15'; over_1000 -> 'over 1000'."""
    if value == "over_1000":
        return "over 1000"
    if value.startswith("manual_bin_"):
        return value[len("manual_bin_"):].replace("_", "-")
    return None  # stub / header


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    targets = {f"HEA_{c}" for c in UNITS} | {"HEA_"}
    n = 0
    for r in rows:
        cat = r.get("category", "")
        if cat not in targets:
            continue
        value = (r.get("value") or "").strip()

        if cat == "HEA_":
            # bare prefix = blank/non-specific VOLTYPECODE (inferred from token
            # adjacency to the volume block; documented blank value). confidence medium.
            da = f"LMDB VOLTYPECODE (tom) — {BLANK_DA}"
            en = f"LMDB VOLTYPECODE (blank) — {BLANK_EN}"
            short = "VOLTYPECODE (blank / non-specific)"
            conf = "medium"
        else:
            code = cat[len("HEA_"):]
            da_unit, en_unit = UNITS[code]
            rng = range_text(value)
            if rng is None:
                # header/stub row for this VOLTYPECODE
                da = f"LMDB VOLTYPECODE {code} — enhed for lægemiddelmængden VOLUME: {da_unit}"
                en = f"LMDB VOLTYPECODE {code} — unit of the medicine-volume variable VOLUME: {en_unit}"
                short = f"VOLTYPECODE {code} ({en_unit})"
            else:
                da = f"Lægemiddelmængde pr. pakning (VOLUME), enhed {da_unit} (VOLTYPECODE {code}): {rng}"
                en = f"Medicine volume per package (VOLUME), unit {en_unit} (VOLTYPECODE {code}): {rng}"
                short = f"VOLUME {en_unit} ({code}): {rng}"
            conf = "high"

        r["description"] = en
        r["description_da"] = da
        r["description_en"] = en
        if "description_short" in r:
            r["description_short"] = short
        r["source"] = SRC_TAG
        r["description_en_source"] = EN_SRC_TAG
        r["confidence_level"] = conf
        n += 1

    print(f"rewrote {n} HEA volume/VOLTYPECODE rows (expected 168)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
