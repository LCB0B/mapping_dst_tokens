#!/usr/bin/env python3
"""Fix real issues flagged by `audit_description_en.py`:

1. F1_empty — translate remaining 23 SOC_ger7 Danish laws + 4 HEA_speciale
   rows from Danish to English.
2. F2_mojibake — strip tab/control chars from description_en
   (already fixed in DA, but EN had the same artifact).
3. F9_placeholder — remove "[Service code XXXX not found]" tail from EN
   and clean the description.
4. F4_da_copy on HEA_speciale "Ingen tekst tilgængelig" rows — rewrite
   EN to the English phrase instead of copying the Danish.
5. F3_danish_leak — simplify EDU_grade "Bestået (passed)" to "Passed".

Benign audit flags (F5-F7, F10) are expected behavior (official EN is
generic ISCO/NACE parent vs the specific Danish translation). Not fixed.

Usage:
    python3 scripts/fix_en_audit_issues.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# ── SOC_ger7 Danish-law English translations ────────────────────────────────
SOC_GER7_TRANSLATIONS = {
    "Radiospredningsloven": "Broadcasting Act",
    "Bogføringsloven": "Bookkeeping Act",
    "Vejlov, rådighed over gadeareal": "Road Act, use of street area",
    "Returkommission": "Kickback",
    "Fragåelsesunderslæb": "Refusal-type embezzlement",
    "Kødloven": "Meat Act",
    "Kvalificeret frihedsberøvelse": "Aggravated deprivation of liberty",
    "Uoplyst straffelov": "Unspecified Criminal Code",
    "Modulvogntog, færdselsområde": "Modular trucks, traffic area",
    "Svig, der ikke er bedrageri": "Fraud not constituting deception",
    "Menneskehandel": "Human trafficking",
    "EF's markedsforordninger": "EC market regulations",
    "Ulovlig aflytning": "Unlawful wiretapping",
    "Lejeloven": "Rent Act",
    "Konkurrenceloven": "Competition Act",
    "Ulovlig selvtægt": "Unlawful self-help",
    "Uberettiget deltagelse i folketingsvalg":
        "Unlawful participation in parliamentary election",
    "Vanrøgt": "Neglect",
    "Civilforsvarsloven": "Civil Defence Act",
    "Pasloven": "Passport Act",
    "Legemsbeskadigelse": "Bodily harm",
    "Dokumentsvig": "Document fraud",
    "Hvidvask": "Money laundering",
}

# HEA_speciale — lab-test codes with empty EN
HEA_SPECIALE_TRANSLATIONS = {
    "Medicinsk Laboratorium, F-FEDT I FÆCES":
        "Medical Laboratory, faecal fat",
    "Medicinsk Laboratorium, S-VÆKSTHORMON":
        "Medical Laboratory, serum growth hormone",
    "Medicinsk Laboratorium, B-KVIKSØLV 21":
        "Medical Laboratory, blood mercury 21",
    "Medicinsk Laboratorium, B-KVIKSØLV 12":
        "Medical Laboratory, blood mercury 12",
}

# EDU_grade Danish-with-English-in-parens → just English
EDU_GRADE_FIX = {
    "Bestået (passed)": "Passed",
    "Ikke bestået (not passed)": "Not passed",
}

PLACEHOLDER_RE = re.compile(r",?\s*\[Service code [0-9]+ not found\]\s*", re.I)
TEXT_NOT_FOUND_RE = re.compile(r",?\s*Text( |,)?not found\s*$", re.I)
CONTROL_RE = re.compile(r"[\x00-\x1f]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    stats = {
        "soc_ger7_translated": 0,
        "hea_speciale_translated": 0,
        "edu_grade_cleaned": 0,
        "mojibake_fixed": 0,
        "placeholder_cleaned": 0,
        "ingen_tekst_english": 0,
    }

    for r in rows:
        cat = r["category"]
        da = r["description_da"].strip()
        en = r["description_en"].strip()

        # F1 — SOC_ger7 empty English
        if cat == "SOC_ger7" and not en and da in SOC_GER7_TRANSLATIONS:
            r["description_en"] = SOC_GER7_TRANSLATIONS[da]
            r["description_short"] = SOC_GER7_TRANSLATIONS[da]
            r["description_en_source"] = "translated"
            stats["soc_ger7_translated"] += 1
            continue

        # F1 — HEA_speciale empty English
        if cat == "HEA_speciale" and not en and da in HEA_SPECIALE_TRANSLATIONS:
            r["description_en"] = HEA_SPECIALE_TRANSLATIONS[da]
            r["description_short"] = HEA_SPECIALE_TRANSLATIONS[da]
            r["description_en_source"] = "translated"
            stats["hea_speciale_translated"] += 1
            continue

        # F3 — EDU_grade simplification
        if cat == "EDU_grade" and en in EDU_GRADE_FIX:
            r["description_en"] = EDU_GRADE_FIX[en]
            r["description_short"] = EDU_GRADE_FIX[en]
            stats["edu_grade_cleaned"] += 1

        # F2 — strip control chars
        if CONTROL_RE.search(en):
            new_en = CONTROL_RE.sub(" ", en).strip()
            new_en = re.sub(r"\s+", " ", new_en)
            if new_en != en:
                r["description_en"] = new_en
                stats["mojibake_fixed"] += 1
                en = new_en

        # F9 — placeholder "[Service code XXXX not found]" in EN
        if PLACEHOLDER_RE.search(en):
            new_en = PLACEHOLDER_RE.sub("", en).rstrip(", ").strip()
            if new_en != en:
                r["description_en"] = new_en
                r["description_short"] = new_en
                stats["placeholder_cleaned"] += 1
                en = new_en

        # F9 — "Text not found" (translation of "Teksten findes ikke") — normalise
        if TEXT_NOT_FOUND_RE.search(en):
            new_en = TEXT_NOT_FOUND_RE.sub(", (no text available)", en)
            if new_en != en:
                r["description_en"] = new_en
                r["description_short"] = re.sub(r"\s*\([^)]*\)", "", new_en).strip()
                stats["placeholder_cleaned"] += 1
                en = new_en
        if cat == "HEA_speciale" and "Teksten findes ikke" in r["description_da"]:
            # Also normalise the Danish so DA stays consistent
            new_da = r["description_da"].replace(
                "Teksten findes ikke", "(ingen tekst tilgængelig)"
            )
            if new_da != r["description_da"]:
                r["description_da"] = new_da
                r["description"] = new_da

        # F4 — "Ingen tekst tilgængelig" copy-of-DA → English phrase
        if cat == "HEA_speciale" and "Ingen tekst tilgængelig" in en:
            new_en = en.replace(
                "Ingen tekst tilgængelig", "(no text available)"
            )
            # Also clean specialty prefix ("Almen Lægehjælp" etc. stays Danish — that's OK)
            # but specialty already has English in `description_en_official`
            r["description_en"] = new_en
            stats["ingen_tekst_english"] += 1

    print("Fixes applied:")
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
