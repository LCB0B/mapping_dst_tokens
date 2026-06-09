#!/usr/bin/env python3
"""Final cleanup pass for remaining mixed Danish/English descriptions.

Handles three patterns left over after the manual-dictionary passes:

1. "Danish (English, old)" — LAB_socio legacy codes had the Danish kept
   verbatim with an English gloss in parentheses.  Extract just the gloss.
   Example: "Selvstændige (Self-employed, old classification)"
            → "Self-employed (old classification)".

2. "Danish (English) - code NNNN" — LAB_tilstand, SOC_ger7 detail rows.
   Keep just the English + detail suffix.

3. "Course <DanishName>" / "Dansk, læsning N. klasse" / island names —
   small hand-curated map.

Usage:
    python3 scripts/final_cleanup.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# ─── Country / island names (DEM_opr, DEM_statsb) ──────────────────────────
COUNTRY_FIXES = {
    "Cookøerne": "Cook Islands",
    "Marshalløerne": "Marshall Islands",
    "Salomonøerne": "Solomon Islands",
    "Vestindiske Øer": "West Indies",
    "Statsløse": "Stateless",
}

# ─── EDU_course (high-school courses, prefix "Course ") ────────────────────
EDU_COURSE_MAP = {
    "Afsætning": "Marketing",
    "Almen sprogforståelse": "General linguistic understanding",
    "Design og arkitektur": "Design and architecture",
    "EU og internationalt økonomisk samarbejde":
        "EU and international economic cooperation",
    "Erhvervsområdeprojekt": "Business area project",
    "Erhvervsøkonomi": "Business economics",
    "Filosofi og teknologi": "Philosophy and technology",
    "Fransk fortsættersprog": "French continuation language",
    "Fællesprøve i fysik/kemi, biologi og geografi":
        "Joint exam in physics/chemistry, biology and geography",
    "Fællesprøve i samfundsfag og historie":
        "Joint exam in social studies and history",
    "Fællesprøve i samfundsfag, historie":
        "Joint exam in social studies, history",
    "Fødevareteknologi": "Food technology",
    "Græsk begyndersprog": "Greek beginners' language",
    "Grønlandsk": "Greenlandic",
    "Håndarbejde": "Needlework",
    "Håndværk og design": "Crafts and design",
    "Idræt": "Physical education",
    "International teknologi og kultur":
        "International technology and culture",
    "International økonomi": "International economics",
    "Iværksætter": "Entrepreneurship",
    "Kinesisk fortsættersprog": "Chinese continuation language",
    "Kinesisk områdestudium": "Chinese area studies",
    "Kultur- og samfundsfaggruppe": "Culture and social studies group",
    "Kultur- og samfundsfaggruppe - Historie":
        "Culture and social studies group - History",
    "Kultur- og samfundsfaggruppe - Religion":
        "Culture and social studies group - Religion",
    "Kultur- og samfundsfaggruppe - Samfundsfag":
        "Culture and social studies group - Social studies",
    "Kulturforståelse": "Cultural understanding",
    "Metal og motorværksted": "Metal and motor workshop",
    "Musik og lydproduktion": "Music and sound production",
    "Nationaløkonomi": "National economics",
    "Naturvidenskabeligt grundforløb":
        "Natural-science foundation course",
    "Sløjd": "Woodwork / sloyd",
    "Spansk fortsættersprog": "Spanish continuation language",
    "Statik og styrkelære": "Statics and strength of materials",
    "Studieområde": "Study area",
    "Studieområde - det internationale område":
        "Study area - the international area",
    "Studieområde - erhvervscase": "Study area - business case",
    "Studieområde del 1": "Study area part 1",
    "Studieområdeprojekt": "Study area project",
    "Studieområdet del 2": "Study area part 2",
    "Større skriftlig opgave": "Major written assignment",
    "Sundhed og sociale forhold": "Health and social conditions",
    "Teknikfag - byggeri og energi":
        "Technology subject - construction and energy",
    "Teknikfag - design og produktion":
        "Technology subject - design and production",
    "Teknikfag - digitalt design og udvikling":
        "Technology subject - digital design and development",
    "Teknikfag - proces levnedsmiddel og sundhed":
        "Technology subject - process, food and health",
    "Teknikfag - udvikling og produktion":
        "Technology subject - development and production",
    "Teknikfag byggeri og energi, el":
        "Technology subject construction and energy, electricity",
    "Tysk fortsættersprog": "German continuation language",
    "Virksomhedsøkonomi": "Business economics",
    "Økonomisk grundforløb": "Economic foundation course",
}

# ─── EDU_audd / EDU_udd / EDU_field leftovers ──────────────────────────────
EDU_EXTRA = {
    "Forsikring": "Insurance",
    "Forsikring, HD-2.del": "Insurance, HD-2nd part",
    "Kontor, all round": "Office, all-round",
    "Kontor, rejsebranche": "Office, travel industry",
    "Kontor, stat": "Office, state administration",
}

# ─── SOC_ger7 / SOC_frakkod / SOC_frakbkod / SOC_fgslkod ───────────────────
SOC_MAP = {
    "Sædelighedsforbrydelser (Sexual offenses)": "Sexual offenses",
    "Sædelighedsforbrydelser (Sexual offenses) - detail code 1146000":
        "Sexual offenses - detail code 1146000",
    "Særlovsovertrædelser (Special law violations)": "Special law violations",
    "Uåbnet fængsel (Closed prison)": "Unopened prison",
    "Uønsket (Unwanted/expelled)": "Unwanted/expelled",
    "Åbent afsoning (Open imprisonment)": "Open imprisonment",
    "Åbent afsonining, arrestafd. (Open imprisonment, arrest dept.)":
        "Open imprisonment, arrest dept.",
    "Åbent med begrænset fællesskab (Open, limited community)":
        "Open, with limited community",
    "Halvåbent fængsel (Semi-open prison)": "Semi-open prison",
    "Lukket fængsel (Closed prison)": "Closed prison",
    "Åbent fængsel (Open prison)": "Open prison",
    "Betinget med vilkår (Conditional with conditions)":
        "Conditional with conditions",
    "Kørselsforbud (Driving ban)": "Driving ban",
}

# ─── HEA_speciale leftovers (a few partial translations) ───────────────────
HEA_SPEC_MAP = {
    "KFA On-call Schedule 89, Foreign Body øj. Mv":
        "KFA on-call service 89, Foreign body, eye, etc.",
    "Rehabilitation, Østfeldt, Follow-up free session 1 hour":
        "Rehabilitation, Østfeldt, Follow-up free session, 1 hour",
    "Rehabilitation, Østfeldt, Functional assessment handicap.":
        "Rehabilitation, Østfeldt, Functional assessment, disability",
    "State Serum Institute, SSA/SSB in package (mø":
        "Statens Serum Institut, SSA/SSB in panel (menstrual)",
    "Stool vagrant medical assistance 82, Tel. consult Med. Prescription":
        "Itinerant physician service 82, Phone consultation with prescription",
    "General medical assistance 80, Tel. consult med.":
        "General practitioner 80, Phone consultation with prescription",
}


def _course_fix(en: str) -> str | None:
    """Match 'Course <Danish>' → 'Course: <English>' using EDU_COURSE_MAP."""
    m = re.match(r"^Course\s+(.*)$", en.strip())
    if not m:
        return None
    key = m.group(1).strip()
    if key in EDU_COURSE_MAP:
        return f"Course: {EDU_COURSE_MAP[key]}"
    return None


def _dansk_laesning_fix(en: str) -> str | None:
    """Match 'Dansk, læsning N. klasse' or 'Dansk/læsning N. klasse'."""
    m = re.match(r"^Dansk[,\/]\s*læsning\s*(\d+)\.\s*klasse\s*$", en.strip())
    if m:
        return f"Danish, reading, grade {m.group(1)}"
    return None


def _lab_socio_fix(en: str) -> str | None:
    """Match 'DanishText (English, old)' → 'English (old)'."""
    # Match a trailing "(English text ending in 'old')" parenthetical
    m = re.match(r"^.+\((.+?,\s*old(?:\s+classification)?)\)\s*$", en.strip())
    if m:
        inner = m.group(1).strip()
        # inner is like "Self-employed, old" → "Self-employed (old)"
        parts = inner.rsplit(",", 1)
        if len(parts) == 2:
            eng, tag = parts[0].strip(), parts[1].strip()
            return f"{eng} ({tag})"
    return None


def _tilstand_fix(en: str) -> str | None:
    """Match 'Lønmodtager (Employee) - code NNNNN' → 'Employee - code NNNNN'."""
    m = re.match(r"^Lønmodtager\s*\(([^)]+)\)\s*-\s*code\s+(\d+)\s*$", en.strip())
    if m:
        return f"{m.group(1).strip()} - code {m.group(2)}"
    return None


def apply_fix(row):
    en = row["description_en"].strip()
    if not en:
        return None
    # 1. Country/island names
    if en in COUNTRY_FIXES:
        return COUNTRY_FIXES[en]
    # 2. EDU_course
    if row["category"] == "EDU_course":
        fix = _course_fix(en)
        if fix:
            return fix
    # 3. EDU_fag (Dansk, læsning)
    if row["category"] == "EDU_fag":
        fix = _dansk_laesning_fix(en)
        if fix:
            return fix
    # 4. EDU_audd / EDU_udd / EDU_field extras
    if en in EDU_EXTRA:
        return EDU_EXTRA[en]
    # 5. SOC fixes
    if en in SOC_MAP:
        return SOC_MAP[en]
    # 6. HEA_speciale fixes
    if en in HEA_SPEC_MAP:
        return HEA_SPEC_MAP[en]
    # 7. LAB_socio "Danish (English, old)" pattern
    if row["category"] == "LAB_socio":
        fix = _lab_socio_fix(en)
        if fix:
            return fix
    # 8. LAB_tilstand "Lønmodtager (Employee) - code NNNN"
    if row["category"] == "LAB_tilstand":
        fix = _tilstand_fix(en)
        if fix:
            return fix
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    applied = 0
    sample = []
    for row in rows:
        fix = apply_fix(row)
        if fix and fix != row["description_en"].strip():
            if args.dry_run and len(sample) < 8:
                sample.append((row["code"], row["description_en"], fix))
            row["description_en"] = fix
            # Refresh description_short
            row["description_short"] = re.sub(r"\s*\([^)]*\)", "", fix).strip()
            applied += 1

    print(f"Cleanup fixes applied: {applied}")
    if args.dry_run and sample:
        print("\nExamples:")
        for code, old, new in sample:
            print(f"  {code}")
            print(f"    OLD: {old}")
            print(f"    NEW: {new}")
        return

    if args.dry_run:
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {MASTER_PATH}")


if __name__ == "__main__":
    main()
