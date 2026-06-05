#!/usr/bin/env python3
"""Clean the genuine residual-Danish translations in description_en (spot-check follow-up).

After reading all flagged rows, the vast majority of "residual Danish" / copy-through are FALSE
POSITIVES (Danish place names, country names identical in EN/DA, glossed welfare-scheme terms).
This fixes only the genuinely-untranslated ones:
  - HEA_speciale Øfeldt rehab (medium-conf): untranslated abbreviations v.fri (vederlagsfri=
    free-of-charge), funk (funktions=functional), muskellid (muskellidelse=muscle disorder),
    ?t/Nt (½/N hours) -> full clean English.
  - HEA_speciale GP §2: "ind to" (indtil=up to).
  - DEM_opr / DEM_statsb origin codes whose description_en was still Danish ("... uoplyst",
    "Land ukendt").
  - EDU_udd Diplomingeniør rows.
description_da (authoritative) is left unchanged; only description_en/description.
The KPLL/SSI/regional lab-analyte block (conf=low) is intentionally NOT touched (semi-
international notation, by prior decision) — fix it in a dedicated lab pass if desired.

Re-runnable. Usage: python3 scripts/fix_residual_danish_en.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# HEA_speciale: code -> full corrected description_en
SPECIALE = {
    "581200": "Rehabilitation, Øfeldt, free-of-charge rehabilitation training per ½ hour",
    "581201": "Rehabilitation, Øfeldt, free-of-charge rehabilitation training per 1 hour",
    "581202": "Rehabilitation, Øfeldt, free-of-charge rehabilitation training per 1½ hours",
    "581203": "Rehabilitation, Øfeldt, free-of-charge rehabilitation training per 2 hours",
    "581204": "Rehabilitation, Øfeldt, free-of-charge rehabilitation training per 2½ hours",
    "582110": "Rehabilitation, Øfeldt, functional examination, muscle disorder",
    "582201": "Rehabilitation, Øfeldt, treatment of muscle disorder per ½ hour",
}
# HEA_speciale GP §2: targeted fragment fix (keeps the rest, incl. proper noun "Sjælland")
SPECIALE_FRAG = {"804261", "804263"}  # "ind to" -> "up to"

# DEM origin/citizenship: Danish text -> English (description_da stays Danish)
DEM_EN = {
    "Udlandet uoplyst": "Abroad, unspecified",
    "Afrika uoplyst": "Africa, unspecified",
    "Nordamerika uoplyst": "North America, unspecified",
    "Europa uoplyst": "Europe, unspecified",
    "Asien uoplyst": "Asia, unspecified",
    "Helt uoplyst": "Completely unspecified",
    "Land ukendt (1)": "Country unknown (1)",
    "Jugoslavien, Forbundsrepublikken": "Yugoslavia, Federal Republic of",
}
EDU_EN = {
    "Diplomingeniør prof.bach.": "Diploma engineer (professional bachelor)",
    "Diplomingeniør, prof.bach. una": "Diploma engineer, professional bachelor (unspecified)",
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    n = 0
    for r in rows:
        cat = r.get("category"); v = (r.get("value") or "").strip(); en = (r.get("description_en") or "")
        new = None
        if cat == "HEA_speciale" and v in SPECIALE:
            new = SPECIALE[v]
        elif cat == "HEA_speciale" and v in SPECIALE_FRAG and "ind to" in en:
            new = en.replace("ind to", "up to")
        elif cat in ("DEM_opr", "DEM_statsb") and en.strip() in DEM_EN and en == (r.get("description_da") or ""):
            new = DEM_EN[en.strip()]
        elif cat == "EDU_udd" and en.strip() in EDU_EN and en == (r.get("description_da") or ""):
            new = EDU_EN[en.strip()]
        if new and new != en:
            r["description_en"] = new
            r["description"] = new
            if (r.get("description_en_source") or "").strip() in ("", "copy-of-da"):
                r["description_en_source"] = "translated"
            n += 1
    print(f"fixed residual-Danish description_en in {n} rows")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
