#!/usr/bin/env python3
"""Clean up HEA_speciale rows and add authoritative English specialty tags.

Three actions:

1. **Drop "[Service code XXXX not found]" placeholders** on 44 rows whose value
   is 1-2 digits (pure specialty metadata rows). Keep just the specialty name.

2. **Relabel** the remaining ~1,636 placeholders to "(procedure not
   documented)" — more informative than the build-script placeholder.

3. **Populate `description_en_official`** with the English specialty name
   for every HEA_speciale row. Source is DST SSR Kodeark + SSR Ydelsesoversigt
   sheet headers (74 specialty codes), plus standard English medical-specialty
   terminology. This makes the SPECIALTY portion traceable to authority;
   the procedure portion remains translated in `description_en`.

   Tag:  description_en_official_source = "dst-ssr-specialty"

Usage:
    python3 scripts/clean_hea_speciale.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# DST specialty code → authoritative English name.  Built from:
#   raw/dst_downloads/ssr_speciale_2digit.csv (Kodeark, 74 codes)
#   raw/dst_downloads/ssr_ydelser_full.csv sheet-header names
#   + English medical-specialty terminology
SPECIALTY_EN = {
    # 1-digit codes (5-digit codes pre-2005 use these)
    "0": "Unspecified",
    "1": "Anaesthesiology",
    "2": "Fictive cut-off",
    "3": "Diagnostic radiology, Copenhagen",
    "4": "Dermato-venereology",
    "5": "Diagnostic radiology",
    "6": "Rheumatology",
    "7": "Gynaecology/obstetrics",
    "8": "Internal medicine",
    "9": "Surgery",
    # 2-digit codes (6-digit codes post-2005 use these)
    "00": "Unspecified",
    "01": "Anaesthesiology",
    "02": "Fictive cut-off",
    "03": "Diagnostic radiology, Copenhagen",
    "04": "Dermato-venereology",
    "05": "Diagnostic radiology",
    "06": "Rheumatology",
    "07": "Gynaecology/obstetrics",
    "08": "Internal medicine",
    "09": "Surgery",
    "11": "Clinical chemistry",
    "15": "ENT on-call, Copenhagen",
    "16": "ENT on-call, KAK",
    "17": "Neurosurgery",
    "18": "Neurology",
    "19": "Ophthalmology service",
    "20": "Orthopaedic surgery",
    "21": "ENT service",
    "22": "Pathology",
    "23": "Plastic surgery",
    "24": "Psychiatry",
    "25": "Paediatrics",
    "26": "Child psychiatry",
    "28": "Tropical medicine",
    "35": "Community psychiatry",
    "39": "Ophthalmology service (KFA)",
    "41": "ENT service (KFA)",
    "42": "Reference laboratory",
    "43": "Diagnostic laboratory",
    "44": "Copenhagen GP Laboratory (KPLL)",
    "45": "Medical Laboratory",
    "46": "Regional laboratories",
    "47": "Aarhus University",
    "48": "Statens Serum Institut",
    "49": "Dental hygienist service",  # post-2007; pre-2007 was Histopathology
    "50": "Dental service",
    "51": "Physiotherapy",
    "52": "Eyeglasses",
    "53": "Chiropractic",
    "54": "Podiatry",
    "55": "Orthonyxia",
    "56": "Clinic treatment",
    "57": "Horseback-riding physiotherapy",
    "58": "Rehabilitation",
    "59": "Foot treatment, scar-tissue patients",
    "60": "Foot treatment",
    "61": "Physiotherapy 61",
    "62": "Free-of-charge physiotherapy",
    "63": "Psychology service",
    "64": "Chiropractic, chronic patients",
    "65": "Free-of-charge horseback-riding physiotherapy",
    "68": "Hearing care",
    "70": "GP, consultation (historic)",
    "71": "Hospitals",
    "72": "GP, telephone consultation",
    "73": "GP, telephone consultation (variant)",
    "74": "GP, visit, daytime",
    "75": "Municipalities",
    "76": "Counties",
    "77": "GP, other services",
    "78": "GP, contacts",
    "79": "Fictive / basic fee",
    "80": "General practitioner",
    "81": "KFA on-call service 81",
    "82": "KAK on-call GP 82",
    "83": "On-call GP service 83",
    "84": "KAK on-call GP 84",
    "85": "Pre-hospital",
    "86": "Island doctors",
    "87": "STI clinic",
    "88": "Physician without contract",
    "89": "KFA on-call service 89",
    "90": "Public health insurance",
    "91": "Dispensations",
    "92": "Prescribed medicines, GPs",
    "93": "Specialist prescriptions",
    "94": "Nutritional-supplement subsidy",
    "95": "Funeral benefit",
    "96": "Interpreter service",
    "97": "Funds",
    "98": "Transport of GPs",
    "99": "Miscellaneous services",
}

# Regex for the old placeholder suffix
PLACEHOLDER_RE = re.compile(r",?\s*\[Service code [0-9]+ not found\]\s*$")


def specialty_prefix(value: str):
    """Return the specialty-code portion of a HEA_speciale value.
    6-digit → first 2 digits. 5-digit → first 1 digit. 1-2 digit → itself."""
    v = value.strip()
    if len(v) == 6:
        return v[:2]
    if len(v) == 5:
        return v[:1]
    if len(v) in (1, 2):
        return v
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    stats = {
        "drop_metadata_placeholder": 0,
        "relabel_placeholder": 0,
        "official_specialty_filled": 0,
        "specialty_not_in_map": 0,
    }

    for r in rows:
        if r["category"] != "HEA_speciale":
            continue
        da = r["description_da"]
        v = r["value"]
        spec = specialty_prefix(v)

        # Action 1+2 — fix placeholders
        if "[Service code" in da and "not found]" in da:
            if len(v) in (1, 2):
                # Metadata row — drop the placeholder tail, keep specialty
                new_da = PLACEHOLDER_RE.sub("", da).rstrip(", ").strip()
                if new_da != da:
                    r["description_da"] = new_da
                    r["description"] = new_da
                    r["description_short"] = new_da
                    stats["drop_metadata_placeholder"] += 1
            else:
                # Procedure-level placeholder — relabel to something informative
                new_da = PLACEHOLDER_RE.sub(", (procedure not documented)", da)
                if new_da != da:
                    r["description_da"] = new_da
                    r["description"] = new_da
                    r["description_short"] = re.sub(
                        r"\s*\([^)]*\)", "", new_da
                    ).strip()
                    stats["relabel_placeholder"] += 1
                    # Also update description_en to match
                    en = r["description_en"]
                    if "Service code" in en or "not found" in en:
                        r["description_en"] = re.sub(
                            r",?\s*\[Service code [0-9]+ not found\]\s*$",
                            ", (procedure not documented)",
                            en,
                        )

        # Action 3 — fill description_en_official with specialty-level English
        if spec in SPECIALTY_EN:
            r["description_en_official"] = SPECIALTY_EN[spec]
            r["description_en_official_source"] = "dst-ssr-specialty"
            stats["official_specialty_filled"] += 1
        elif spec:
            stats["specialty_not_in_map"] += 1

    print("Actions applied:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows")


if __name__ == "__main__":
    main()
