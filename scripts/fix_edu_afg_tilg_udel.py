#!/usr/bin/env python3
"""Fill EDU_afg, EDU_tilg, EDU_udel descriptions from authoritative DST sources.

All three are from the KOTRE / Elevregistret / Uddannelsesregister variables:

  AFG_ART:  https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-uddannelse-og-kultur/afg-art
  TILG_ART: https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-uddannelse-og-kultur/tilg-art
  UDEL:     https://www.dst.dk/da/Statistik/dokumentation/Times/uddannelseregister/udel

All values in MASTER were verified to exist in the official DST documentation.
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# AFG_ART (afgangsart = exit type)
AFG_ART = {
    "1":  ("Uddannelse afgang",
           "Education exit"),
    "2":  ("Uddannelsespause, fortsætter på samme institution",
           "Education pause, continues at same institution"),
    "3":  ("Uddannelsespause, fortsætter på anden institution",
           "Education pause, continues at different institution"),
    "4":  ("I gang",
           "In progress"),
    "11": ("Uddannelse og klassetrin afgang",
           "Education and grade-level exit"),
    "20": ("Uddannelse/klassetrin pause, fortsætter på samme institution",
           "Education/grade-level pause, continues at same institution"),
    "21": ("Klassetrin afgang, fortsætter på samme institution",
           "Grade-level exit, continues at same institution"),
    "30": ("Uddannelse/klassetrin pause, fortsætter på anden institution",
           "Education/grade-level pause, continues at different institution"),
    "31": ("Klassetrin afgang, fortsætter på anden institution",
           "Grade-level exit, continues at different institution"),
    "44": ("I gang, almene uddannelser",
           "In progress, general education"),
}

# TILG_ART (tilgangsart = entry type)
TILG_ART = {
    "1":  ("Uddannelse tilgang",
           "Education entry"),
    "2":  ("Uddannelse genstart, fortsætter på samme institution",
           "Education restart, continues at same institution"),
    "3":  ("Uddannelse genstart, fortsætter på anden institution",
           "Education restart, continues at different institution"),
    "11": ("Uddannelse og klassetrin tilgang",
           "Education and grade-level entry"),
    "20": ("Uddannelse/klassetrin genstart, fortsætter på samme institution",
           "Education/grade-level restart, continues at same institution"),
    "21": ("Klassetrin tilgang, fortsætter på samme institution",
           "Grade-level entry, continues at same institution"),
    "30": ("Uddannelse/klassetrin genstart, fortsætter på anden institution",
           "Education/grade-level restart, continues at different institution"),
    "31": ("Klassetrin tilgang, fortsætter på anden institution",
           "Grade-level entry, continues at different institution"),
}

# UDEL (uddannelsesdel = education part)
UDEL = {
    "0":  ("Udelt uddannelse", "Undivided education"),
    "20": ("0. klassetrin", "Grade-level 0 (kindergarten class)"),
    "21": ("1. klassetrin", "Grade-level 1"),
    "22": ("2. klassetrin", "Grade-level 2"),
    "23": ("3. klassetrin", "Grade-level 3"),
    "24": ("4. klassetrin", "Grade-level 4"),
    "25": ("5. klassetrin", "Grade-level 5"),
    "26": ("6. klassetrin", "Grade-level 6"),
    "27": ("7. klassetrin", "Grade-level 7"),
    "28": ("8. klassetrin", "Grade-level 8"),
    "29": ("9. klassetrin", "Grade-level 9"),
    "30": ("10. klassetrin", "Grade-level 10"),
    "31": ("11. klassetrin", "Grade-level 11"),
    "40": ("FGU basis/spor ikke valgt", "FGU basis / track not selected"),
    "41": ("FGU spor", "FGU track"),
    "51": ("EUD indgangsforløb", "VET (EUD) entry programme"),
    "52": ("EUD hovedforløb", "VET (EUD) main programme"),
    "53": ("EUD indgangsforløb 1", "VET (EUD) entry programme 1"),
    "54": ("EUD indgangsforløb 2", "VET (EUD) entry programme 2"),
    "55": ("EUD EUX studiekompetenceforløb",
           "VET (EUD) EUX study-competence programme"),
    "56": ("Grundforløb plus", "Basic programme plus"),
    "60": ("Udelt kandidatuddannelse", "Undivided master's programme"),
    "61": ("Bacheloruddannelse", "Bachelor's programme"),
    "62": ("Kandidatoverbygning", "Master's top-up programme"),
    "64": ("Akademisk overbygningsuddannelse",
           "Academic top-up programme"),
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    stats = {"afg": 0, "tilg": 0, "udel": 0}

    for r in rows:
        cat = r["category"]
        raw_v = r["value"].strip()

        if cat == "EDU_afg":
            # value like "art_1" or "art_11" (may have trailing space)
            key = raw_v.replace("art_", "").strip()
            if key in AFG_ART:
                da, en = AFG_ART[key]
                r["description_da"] = da
                r["description"] = da
                r["description_en"] = en
                r["description_short"] = en
                r["description_en_source"] = "dst_times_afg_art"
                r["confidence_level"] = "high"
                stats["afg"] += 1

        elif cat == "EDU_tilg":
            key = raw_v.replace("art_", "").strip()
            if key in TILG_ART:
                da, en = TILG_ART[key]
                r["description_da"] = da
                r["description"] = da
                r["description_en"] = en
                r["description_short"] = en
                r["description_en_source"] = "dst_times_tilg_art"
                r["confidence_level"] = "high"
                stats["tilg"] += 1

        elif cat == "EDU_udel":
            if raw_v in UDEL:
                da, en = UDEL[raw_v]
                r["description_da"] = da
                r["description"] = da
                r["description_en"] = en
                r["description_short"] = en
                r["description_en_source"] = "dst_times_udel"
                r["confidence_level"] = "high"
                stats["udel"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
