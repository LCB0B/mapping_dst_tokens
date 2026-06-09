#!/usr/bin/env python3
"""Fix the 13 unsourced (none|generated) DEM_kom special codes.

Findings (see SOURCE_AUDIT.md):
- 955-960 = the MODERN Greenland municipalities (2009 reform + 2018 split). The vocab's
  DEM_kom spans both eras (old Greenland kommuner 901-953 are in DEM_kom_dict.csv; the
  new ones 955-960 are not). MASTER had 959="Udlandet (Abroad)" and 960="Færøerne
  (Faroe Islands)" — both HALLUCINATIONS; they are Greenland municipalities.
  Sources: cpr.dk Grønland-2018 (auth. for 958/959/960) + stat.gl / 2009-reform.
- 010/011/012/019 = administrative/tax authority codes — verbatim from DEM_kom_dict.csv
  (the repo's extract of DST KOM).
- 004/007/009 = same administrative 0xx family but specific labels not found in any
  source -> marked [Unresolved]/low (never invented; HARD RULES).

Re-runnable. Usage: python3 scripts/fix_dem_kom_special.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
DICT = "lookup_dictionaries/DEM_kom_dict.csv"

# 955-960: Greenland municipalities (Danish/Greenlandic proper name, English gloss).
GREENLAND = {
    "955": ("Kommune Kujalleq", "Kommune Kujalleq (Greenland municipality)"),
    "956": ("Kommuneqarfik Sermersooq", "Kommuneqarfik Sermersooq (Greenland municipality)"),
    "957": ("Qeqqata Kommunia", "Qeqqata Kommunia (Greenland municipality)"),
    "958": ("Qaasuitsup Kommunia", "Qaasuitsup Kommunia (Greenland municipality, 2009–2017)"),
    "959": ("Kommune Qeqertalik", "Kommune Qeqertalik (Greenland municipality, from 2018)"),
    "960": ("Avannaata Kommunia", "Avannaata Kommunia (Greenland municipality, from 2018)"),
}
# English glosses for the 0xx administrative/tax codes (Danish comes verbatim from dict).
ADMIN_EN = {
    "010": "Sømandsskattekontoret (Seamen's Tax Office)",
    "011": "Told og Skattestyrelsen (Danish Customs and Tax Administration)",
    "012": "ATP (Labour Market Supplementary Pension)",
    "019": "Administrative (hospitals)",
}
UNRESOLVED = {"004", "007", "009"}


def load_dict():
    d = {}
    for r in csv.DictReader(open(DICT, encoding="utf-8")):
        d[r["code"].replace("DEM_kom_", "")] = r["description"]
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dct = load_dict()

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    gl = admin = unres = 0
    for r in rows:
        if r.get("category") != "DEM_kom":
            continue
        if not (r.get("source") or "").strip().lower().startswith("none|generated"):
            continue
        code = (r.get("value") or "").strip()
        if code in GREENLAND:
            da, en = GREENLAND[code]
            r["description"] = en; r["description_da"] = da; r["description_en"] = en
            r["source"] = "cpr_groenland"; r["description_en_source"] = "cpr-groenland"
            r["confidence_level"] = "high"; gl += 1
        elif code in ADMIN_EN:
            da = dct.get(code, "")            # verbatim from dict (e.g. "ATP")
            da_key = code.lstrip("0") or "0"  # dict keys are unpadded (10,11,12,19)
            da = dct.get(code) or dct.get(da_key) or da
            en = ADMIN_EN[code]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "CSV:DEM_kom"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; admin += 1
        elif code in UNRESOLVED:
            mark = f"[Unresolved DEM_kom code: {code}]"
            r["description"] = mark; r["description_da"] = ""; r["description_en"] = mark
            r["source"] = "none|generated"; r["description_en_source"] = ""
            r["confidence_level"] = "low"; unres += 1

    print(f"DEM_kom: Greenland fixed={gl}, admin filled={admin}, unresolved marked={unres}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
