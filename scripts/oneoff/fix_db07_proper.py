#!/usr/bin/env python3
"""Re-fix LAB_db07 5-digit codes.

Previous attempt (scripts/fix_db07_and_socio_gl.py) assumed codes followed
NACE Rev 2 with stripped leading zero (e.g., 11100 → NACE 01.11 "Growing of
cereals"). That was WRONG for a DB07 context.

The authoritative source for 5-digit DB07 codes in a Danish register is the
DST DB07 127-grupperingen (raw/dst_db07_2014.pdf, from Statistisk Årbog
2014, page 484-485). That publication defines codes like:
  11.00.0 → 11000 Drikkevareindustri (Beverages)
  13.00.0 → 13000 Tekstilindustri (Textile industry)
  14.00.0 → 14000 Beklædningsindustri (Wearing apparel industry)
  15.00.0 → 15000 Læder- og fodtøjsindustri (Leather and footwear)
  17.00.0 → 17000 Papirindustri (Paper industry)
  61.00.0 → 61000 Telekommunikation
  71.00.0 → 71000 Arkitekter og rådgivende Ingeniører
  72.00.0 → 72000 Forskning og udvikling

Codes in MASTER that don't match the 127-grupperingen (like 11100, 12400,
14610, 89100) are from an older Danish classification or a different
aggregation level. They are NOT the NACE Rev 2 01.xx agricultural classes I
previously claimed — 13000 is textiles, not plant propagation.

This script:
  1. Clears my earlier bad mappings (source=nace_rev2)
  2. Applies only verified DB07 127-grupperingen labels
  3. Marks the rest unresolved

Source: DST Statistisk Årbog 2014, "Dansk Branchekode og standardgrupperinger"
https://www.dst.dk/pubfile/17958/branche (saved as raw/dst_db07_2014.pdf)
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Verified DB07 127-grupperingen (from DST Statistisk Årbog 2014)
# Format: {code: (da, en)}
DB07_127 = {
    # Food, drink, tobacco (CA)
    "10001": ("Slagterier", "Slaughterhouses"),
    "10002": ("Fiskeindustri", "Fish processing"),
    "10003": ("Mejerier", "Dairies"),
    "10004": ("Bagerier, brødfabrikker mv.", "Bakeries, bread factories etc."),
    "10005": ("Anden fødevareindustri", "Other food manufacturing"),
    "11000": ("Drikkevareindustri", "Beverage manufacturing"),
    "12000": ("Tobaksindustri", "Tobacco manufacturing"),
    # Textile, clothing, leather (CB)
    "13000": ("Tekstilindustri", "Textile manufacturing"),
    "14000": ("Beklædningsindustri", "Wearing apparel manufacturing"),
    "15000": ("Læder- og fodtøjsindustri", "Leather and footwear manufacturing"),
    # Wood, paper, printing (CC)
    "16000": ("Træindustri", "Wood manufacturing"),
    "17000": ("Papirindustri", "Paper manufacturing"),
    "18000": ("Trykkerier mv.", "Printing etc."),
    # Petroleum (CD)
    "19000": ("Olieraffinaderier mv.", "Oil refineries etc."),
    # Metals (CH)
    "24000": ("Fremstilling af metal", "Manufacture of basic metals"),
    "25000": ("Metalvareindustri", "Manufacture of fabricated metal products"),
    # Electronics (CI)
    "26001": ("Fremstilling af it-udstyr", "Manufacture of IT equipment"),
    "26002": ("Fremstilling af andet elektronisk udstyr",
              "Manufacture of other electronic equipment"),
    # Energy/water (D, E)
    "35001": ("Elforsyning", "Electricity supply"),
    "35002": ("Gasforsyning", "Gas supply"),
    "35003": ("Varmeforsyning", "Heat supply"),
    "36000": ("Vandforsyning", "Water supply"),
    "37000": ("Kloak- og rensningsvirksomhed", "Sewerage"),
    # Information and communication (J)
    "61000": ("Telekommunikation", "Telecommunications"),
    "62000": ("It-konsulenter mv.", "IT consulting etc."),
    # Professional, scientific, technical (M)
    "69001": ("Advokatvirksomhed", "Legal activities"),
    "69002": ("Revision og bogføring", "Accounting and auditing"),
    "70000": ("Virksomhedskonsulenter", "Management consultancy"),
    "71000": ("Arkitekter og rådgivende ingeniører",
              "Architects and consulting engineers"),
    "72000": ("Forskning og udvikling", "Research and development"),
    # Extraterritorial / unknown
    "99000": ("Internationale organisationer og ambassader",
              "International organisations and embassies"),
    "99999": ("Uoplyst aktivitet", "Activity not stated"),
    "999999": ("Uoplyst aktivitet", "Activity not stated"),
}

# Codes in MASTER that appeared in DB93 raw/LAB_nace.txt only (pre-2007 data)
# If MASTER is truly DB07-only, these shouldn't be here — but since they are,
# we mark them with the pre-2007 DB93 label and flag as legacy.
DB93_LEGACY = {
    "514620": ("Engroshandel med læge- og hospitalsartikler (DB93)",
               "Wholesale of medical and hospital supplies (DB93 legacy code)"),
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    stats = {"verified": 0, "db93_legacy": 0, "cleared": 0, "kept_existing": 0}

    for r in rows:
        if r["category"] != "LAB_db07":
            continue
        v = r["value"]

        # Only touch 5-6 digit codes; leave 6-digit DB07 subclasses alone
        if len(v) not in (5, 6):
            continue

        source = r.get("description_en_source", "")

        # Codes I previously filled with nace_rev2 source — these are the bad ones
        if source == "nace_rev2":
            if v in DB07_127:
                da, en = DB07_127[v]
                r["description_da"] = da
                r["description"] = da
                r["description_en"] = en
                r["description_short"] = en
                r["description_en_source"] = "dst_db07_127"
                r["confidence_level"] = "high"
                stats["verified"] += 1
            elif v in DB93_LEGACY:
                da, en = DB93_LEGACY[v]
                r["description_da"] = da
                r["description"] = da
                r["description_en"] = en
                r["description_short"] = en
                r["description_en_source"] = "db93_legacy"
                r["confidence_level"] = "medium"
                stats["db93_legacy"] += 1
            else:
                # Unresolved — no documented DB07 meaning
                r["description_da"] = ""
                r["description"] = ""
                r["description_en"] = f"[Unresolved DB07 code: {v}]"
                r["description_short"] = f"Unresolved DB07 code {v}"
                r["description_en_source"] = "unresolved"
                r["confidence_level"] = "low"
                stats["cleared"] += 1
        else:
            stats["kept_existing"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
