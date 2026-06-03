#!/usr/bin/env python3
"""Fix EDU_udd level-mistranslations.

Two classes of errors found (2026-04-19 audit):

1. Danish master-level abbreviations (kand./cand./civilingeniør) translated
   as English bachelor-level (BSc/BA/BEng/bachelor) — 392 rows.
2. Danish bachelor-level abbreviation (diplomingeniør) translated as English
   master-level (Master of Engineering, MSc in Engineering) — 2 rows.

Convention: Danish-preserving (matches the existing 282+24 = 306 rows that
already correctly render kand.2år/cand.2år as kand.2yr/cand.2yr). Keeps the
repo's loanword pattern.

Reference levels (Danish higher education / DST):
  - bach.              = Bachelor (3 yr)
  - prof.bach.         = Professional bachelor (3.5-4 yr)
  - ing.bach. / ing.prof.bach. = Engineering bachelor
  - diplomingeniør     = Diploma engineer (bachelor level, 3.5 yr)
  - kand. / cand.      = Kandidat (master's level, typically +2 yr)
  - kand.2år           = 2-year master's top-up
  - civilingeniør      = Civil engineer (5-yr MSc in Engineering, NOT bachelor)
  - cand.scient., cand.mag., cand.merc., cand.jur. etc. = master's-level Latin titles

DST source: https://www.dst.dk/da/Statistik/emner/uddannelse-og-forskning/
videregaaende-uddannelser
"""
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Suffixes: Danish → correct English (Danish-preserving convention)
SUFFIX_FIX = {
    # kand. variants
    "kand.2år":        "kand.2yr",
    "kand. 2 år":      "kand.2yr",
    "kand.2.år":       "kand.2yr",
    "kand.3år":        "kand.3yr",
    "kand.2år (DPU)":  "kand.2yr (DPU)",
    "kand.2år (RUC)":  "kand.2yr (RUC)",
    # cand.xxx (Latin form) — preserve
    "cand.merc.2år":       "cand.merc.2yr",
    "cand.ling.merc.2år":  "cand.ling.merc.2yr",
    "cand.merc.(jur.)2år": "cand.merc.(jur.)2yr",
    "cand.negot.2år":      "cand.negot.2yr",
    "cand.soc.2år":        "cand.soc.2yr",
    "cand.it.2år":         "cand.it.2yr",
    "cand.mag.2år":        "cand.mag.2yr",
    "cand.scient.tech.2år": "cand.scient.tech.2yr",
    # civilingeniør
    "civilingeniør 2år":       "civilingeniør 2yr",
    "civilingeniør 2år (AAU)": "civilingeniør 2yr (AAU)",
    "civilingiør 2år":         "civilingeniør 2yr",  # fix typo too
}

# Full-string DA → correct EN (not suffix-based)
FULL_FIX = {
    "Diplomingeniør prof.bach.":        "Diplomingeniør prof.bach.",
    "Diplomingeniør, prof.bach. una":   "Diplomingeniør, prof.bach. una",
    "grunduddannelse (kand.)":          "foundation programme (kand.)",
}

MASTER_DA = re.compile(r'\b(kand\.|cand\.|civilingeniør)', re.I)
BACHELOR_EN = re.compile(r'\b(BSc|BA|B\.A\.|B\.Sc|BEng|B\.Eng|bachelor)\b', re.I)
BACHELOR_DA = re.compile(r'\bdiplomingeniør\b', re.I)
MASTER_EN = re.compile(r'\b(MSc|M\.Sc|MEng|M\.Eng|master\s+of)\b', re.I)


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    stats = {"suffix_fixed": 0, "diplomingeniør_fixed": 0,
             "grunduddannelse": 0}

    for r in rows:
        if r["category"] != "EDU_udd":
            continue
        da = r["description_da"]
        en = r["description_en"]

        # Strategy A: suffix-based — use Danish suffix to derive correct English
        # Only apply when EN has bachelor-level forms but DA has master-level
        if MASTER_DA.search(da) and "bach." not in da and BACHELOR_EN.search(en):
            # Find the Danish suffix (last ", "-separated segment or full string)
            if ", " in da:
                da_prefix, da_suffix = da.rsplit(", ", 1)
            else:
                da_prefix, da_suffix = "", da

            if da_suffix in SUFFIX_FIX:
                new_suffix = SUFFIX_FIX[da_suffix]
                # Rebuild EN preserving the English prefix (the translated name)
                if ", " in en:
                    en_prefix, _ = en.rsplit(", ", 1)
                    new_en = f"{en_prefix}, {new_suffix}"
                else:
                    new_en = new_suffix
                r["description_en"] = new_en
                r["description_short"] = new_en
                r["description_en_source"] = "manual_level_fix"
                stats["suffix_fixed"] += 1
                continue

        # Strategy B: Diplomingeniør (bachelor) mistranslated as master
        if BACHELOR_DA.search(da) and MASTER_EN.search(en):
            if da in FULL_FIX:
                new_en = FULL_FIX[da]
                r["description_en"] = new_en
                r["description_short"] = new_en
                r["description_en_source"] = "manual_level_fix"
                stats["diplomingeniør_fixed"] += 1

        # Strategy C: "grunduddannelse (kand.)" — the single remaining mapping
        if da == "grunduddannelse (kand.)":
            r["description_en"] = "foundation programme (kand.)"
            r["description_short"] = "foundation programme (kand.)"
            r["description_en_source"] = "manual_level_fix"
            stats["grunduddannelse"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
