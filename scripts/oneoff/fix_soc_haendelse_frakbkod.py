#!/usr/bin/env python3
"""Fix two mis-labelled SOC categories that are not actually criminal-event codes.

SOC_haendelse = BUAF / "Udsatte børn og unge" HAENDELSE — events in an out-of-home
PLACEMENT case (anbringelse), NOT criminal events. Table D280601.TXT_ANB_HAENDELSE.
The decimal sub-codes (0.2/1.1/5.5/7.5) were already sourced from raw/SOC_haendelse.txt;
the integer codes 0/1/2/5/7 were left as bogus "Criminal event type: N". Filled here
from the DST value set (verbatim Danish).
Source: https://www.dst.dk/da/Statistik/dokumentation/Times/boern-og-unge/haendelse
        (+ raw/SOC_haendelse.txt)

SOC_frakbkod = DST AFG_FRAKBKOD (KRAF) — code indicating whether a frakendelse (e.g.
driving-licence) is "for bestandig" (permanent). The MASTER labels
(Betinget/Ubetinget/Kørselsforbud/Betinget med vilkår) were hallucinated. Correct
value set (verbatim, confirmed twice):
Source: https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakbkod

Re-runnable. Usage: python3 scripts/fix_soc_haendelse_frakbkod.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# SOC_haendelse integer codes -> (Danish verbatim from DST, clean English)
HAENDELSE = {
    "0": ("Iværksættelse af anbringelse", "Implementation of placement"),
    "1": ("Iværksættelse af ændret anbringelsessted", "Implementation of a changed placement location"),
    "2": ("Ændring af tvangsanbringelse til frivillig anbringelse", "Change from involuntary to voluntary placement"),
    "5": ("Hjemgivelse/ophør af anbringelse", "Return home / discontinuation of placement"),
    "7": ("Iværksættelse/genetablering af efterværn med døgnophold i anbringelsessted",
          "Initiation/re-establishment of aftercare with 24-hour stay at the placement"),
}
# SOC_frakbkod codes -> (Danish verbatim from AFG_FRAKBKOD, English gloss)
FRAKBKOD = {
    "1": ("bestandig", "Permanent (for bestandig)"),
    "2": ("endelig dom", "Final judgment"),
    "3": ("domsdato", "Judgment date"),
    "4": ("ikke mere bestandig", "No longer permanent"),
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    nh = nf = 0
    for r in rows:
        cat = r.get("category"); v = (r.get("value") or "").strip()
        if cat == "SOC_haendelse" and v in HAENDELSE and (r.get("source") or "").startswith("none|generated"):
            da, en = HAENDELSE[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "CSV:SOC_haendelse_from_raw"; r["description_en_source"] = "dst_times_haendelse"
            r["confidence_level"] = "high"; nh += 1
        elif cat == "SOC_frakbkod" and v in FRAKBKOD and (r.get("source") or "").startswith("none|generated"):
            da, en = FRAKBKOD[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_afg_frakbkod"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; nf += 1

    print(f"SOC_haendelse integer codes fixed: {nh} (expect 5); SOC_frakbkod fixed: {nf} (expect 4)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
