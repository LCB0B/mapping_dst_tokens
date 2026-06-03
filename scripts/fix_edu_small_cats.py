#!/usr/bin/env python3
"""Fix small EDU category translation issues found during per-category audit.

Issues:
1. EDU_field "u.n.a." (uden nærmere angivelse = not elsewhere classified) was
   mistranslated as "Various Not Applicable" (4 rows).
2. EDU_fag — 8 rows have the Danish subject name literally copied into EN
   instead of being translated (Matematik, Fysik/kemi, Geografi, etc.).
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# EDU_fag: translate Danish subject names. Pattern: "<Subject> <N>. klasse" →
# "<Subject-EN>, grade N" (same format as the already-translated rows).
SUBJECT_EN = {
    "Matematik":   "Mathematics",
    "Fysik/kemi":  "Physics/Chemistry",
    "Geografi":    "Geography",
    "Engelsk":     "English",
    "Biologi":     "Biology",
    "Kemi":        "Chemistry",
    "Fysik":       "Physics",
    "Historie":    "History",
    "Samfundsfag": "Social studies",
    "Idræt":       "Physical education",
    "Tysk":        "German",
    "Fransk":      "French",
    "Spansk":      "Spanish",
    "Religion":    "Religion",
    "Musik":       "Music",
    "Natur/teknologi": "Science/technology",
    "Natur/teknik": "Science/technology",
    "Teknologi":   "Technology",
    "Dansk":       "Danish",
    "Dansk/læsning": "Danish, reading",
}


def translate_fag(value: str) -> str | None:
    # Expect format "<subject> <N>. klasse"
    for subject, en in sorted(SUBJECT_EN.items(), key=lambda x: -len(x[0])):
        if value.startswith(subject):
            rest = value[len(subject):].strip()
            # rest is like "6. klasse" or "grade 6"
            import re
            m = re.search(r"(\d+)\.?\s*klasse", rest)
            if m:
                return f"{en}, grade {m.group(1)}"
    return None


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    fixed = {"una_fixed": 0, "fag_translated": 0}

    for r in rows:
        cat = r["category"]
        en = r["description_en"]
        da = r["description_da"]

        # Fix #1: u.n.a. mistranslation
        if "Various Not Applicable" in en:
            new_en = en.replace("Various Not Applicable", "n.e.c.")
            r["description_en"] = new_en
            r["description_short"] = new_en
            fixed["una_fixed"] += 1

        # Fix #2: EDU_fag untranslated
        if cat == "EDU_fag" and "klasse" in en and "grade" not in en.lower():
            new_en = translate_fag(en)
            if new_en:
                r["description_da"] = en  # original Danish was in the value/EN
                r["description_en"] = new_en
                r["description_short"] = new_en
                r["description_en_source"] = "translated"
                fixed["fag_translated"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in fixed.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
