#!/usr/bin/env python3
"""Fix HEA_patienttype — all 4 codes were swapped/wrong.

Source: DST LPR c_pattype documentation
(esundhed.dk, DST high-quality variable docs for Sygehusbenyttelse).

Correct mappings (LPR patient type):
  0 = Indlagt (Inpatient)
  1 = Deldøgnspatient (Day/half-day patient; discontinued 2002)
  2 = Ambulant patient (Outpatient; from 2014 also includes emergency with
      acute admission method)
  3 = Skadestuepatient (Emergency room; discontinued 2014)
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

FIX = {
    "0": ("Indlagt", "Inpatient (stationary admission)"),
    "1": ("Deldøgnspatient", "Day/half-day patient (discontinued 2002)"),
    "2": ("Ambulant patient",
          "Outpatient (from 2014 also includes emergency with acute admission)"),
    "3": ("Skadestuepatient", "Emergency room patient (discontinued 2014)"),
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    fixed = 0
    for r in rows:
        if r["category"] == "HEA_patienttype" and r["value"] in FIX:
            da, en = FIX[r["value"]]
            r["description_da"] = da
            r["description"] = da
            r["description_en"] = en
            r["description_short"] = en
            r["description_en_source"] = "dst_lpr_c_pattype"
            r["confidence_level"] = "high"
            fixed += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    print(f"Fixed: {fixed}")


if __name__ == "__main__":
    main()
