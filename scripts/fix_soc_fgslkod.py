#!/usr/bin/env python3
"""Fix SOC_fgslkod = DST IND_FGSLKOD (KRIN / Kriminalstatistik indsættelser).

IND_FGSLKOD = "Fængslingskode" — the TYPE OF INCARCERATION/admission event
(arrest / remand / serving / transfer), NOT the institution type. The MASTER labels
(1=Åbent fængsel, 2=Lukket fængsel, 3=Arresthus, 4=Halvåbent fængsel, 5=Pension) were
HALLUCINATIONS — institution types invented from the abbreviation. Corrected here from
the KRIN codebook value set (verbatim Danish):
Source: https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/ind-fgslkod
        (also raw/dst_downloads/KRIN_codebook.md)

Re-runnable. Usage: python3 scripts/fix_soc_fgslkod.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# IND_FGSLKOD value set (verbatim Danish) -> clean English
FGSLKOD = {
    "0": ("Afsoning påbegyndt/fortsat under andet journalnummer",
          "Serving begun/continued under another case number"),
    "1": ("Anholdt under sag", "Arrested during the case"),
    "2": ("Anholdelse opretholdt", "Arrest upheld"),
    "3": ("Varetægtsfængslet", "Remanded in custody (pre-trial detention)"),
    "4": ("Overførsel af afsoner", "Transfer of an inmate"),
    "5": ("Afsoner", "Serving a sentence (inmate)"),
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    n = 0
    for r in rows:
        if r.get("category") != "SOC_fgslkod":
            continue
        v = (r.get("value") or "").strip()
        if v in FGSLKOD and (r.get("source") or "").startswith("none|generated"):
            da, en = FGSLKOD[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_ind_fgslkod"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; n += 1

    print(f"SOC_fgslkod fixed: {n} (expect 6)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
