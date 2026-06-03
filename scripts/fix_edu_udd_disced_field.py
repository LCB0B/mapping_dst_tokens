#!/usr/bin/env python3
"""Translate remaining Danish strings in EDU_udd, EDU_disced, EDU_field where
description_da == description_en."""
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

EDU_UDD = {
    "Diplomklasse-orgel (musik)": "Diploma class organ (music)",
    "Dyrevidenskab, bach.": "Animal science, bach.",
    "Erhvervsgrunduddannelse EGU": "Basic vocational training (EGU)",
    "Erhvervssproglig afgangseksamen EA": "Business language final examination (EA)",
    "Forberedende grunduddannelse (FGU)": "Preparatory basic education (FGU)",
    "Forfatteruddannelsen (privat udd.)": "Author training (private education)",
    "Grundskole 7.-9. kl.": "Primary school grades 7-9",
    "Jordbrug (overbygning), prof.bach.": "Agriculture (top-up), prof.bach.",
    "Jordbrugvirksomhed(overbygning).prof.bach.": "Agricultural business (top-up), prof.bach.",
    "Konservatorieuddannelse 2 (musik)": "Conservatory education 2 (music)",
    "Konservatorieuddannelse 3 (musik)": "Conservatory education 3 (music)",
    "Naturvidenskab kombineret, kand. (AAU)": "Natural science combined, cand. (AAU)",
    "Naturvidenskab, bach.": "Natural science, bach.",
    "Naturvidenskab, bach. (RUC)": "Natural science, bach. (RUC)",
    "Nordisk folkemindevidenskab, kand.": "Nordic folklore studies, cand.",
    "Sproglig studenterkursus": "Language-oriented student course",
    "Tresproglig korrespondent": "Trilingual correspondent",
    "Tysk-russisk erhvervssprog, bach.": "German-Russian business language, bach.",
    "Chemical and Biotechnical Technology and Food Technology (overbygning), prof.bach.":
        "Chemical and Biotechnical Technology and Food Technology (top-up), prof.bach.",
    "Design and Business (overbygning), prof.bach.":
        "Design and Business (top-up), prof.bach.",
    "Digital Concept Development (overbygning), prof.bach.":
        "Digital Concept Development (top-up), prof.bach.",
    "Innovation and entrepreneurship (overbygning), prof.bach.":
        "Innovation and entrepreneurship (top-up), prof.bach.",
    "International Sales and Marketing (overbygning), prof.bach.":
        "International Sales and Marketing (top-up), prof.bach.",
    "Nature and Agricultural Management (overbygning), prof.bach.":
        "Nature and Agricultural Management (top-up), prof.bach.",
    "Product Development and Integrative Technology (overbygning), prof.bach.":
        "Product Development and Integrative Technology (top-up), prof.bach.",
    "Software Development (overbygning), prof.bach.":
        "Software Development (top-up), prof.bach.",
    "Web Development (overbygning), prof.bach.":
        "Web Development (top-up), prof.bach.",
}

EDU_DISCED_STEM = {
    "Alment gymnasiale uddannelser": "General upper-secondary education",
    "Erhvervsrettede gymnasiale uddannelser": "Vocational upper-secondary education",
    "Internationale gymnasiale uddannelser": "International upper-secondary education",
    "Naturvidenskab, BACH": "Natural science, bachelor",
    "Naturvidenskab, LVU": "Natural science, long-cycle higher education",
    "Naturvidenskab, Ph.d.": "Natural science, PhD",
    "Samfundsvidenskab, BACH": "Social science, bachelor",
    "Samfundsvidenskab, LVU": "Social science, long-cycle higher education",
    "Samfundsvidenskab, MVU": "Social science, medium-cycle higher education",
    "Samfundsvidenskab, Ph.d.": "Social science, PhD",
    "Sundhedsvidenskab, BACH": "Health science, bachelor",
    "Sundhedsvidenskab, LVU": "Health science, long-cycle higher education",
    "Sundhedsvidenskab, Ph.d.": "Health science, PhD",
}

EDU_FIELD = {
    "Bibliotekskundskab": "Library science",
    "Biologisk laboratorieteknik": "Biological laboratory technology",
    "Bygningsservice": "Building services",
    "Filologi klassisk": "Classical philology",
}

COMPOUND_RE = re.compile(r"\s*\(compound:\s*[^)]+\)\s*$")


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    fixed = {"EDU_udd": 0, "EDU_disced": 0, "EDU_field": 0}
    for r in rows:
        cat = r["category"]
        da = r["description_da"].strip()
        en = r["description_en"].strip()
        if not da or da != en:
            continue
        if cat == "EDU_udd" and da in EDU_UDD:
            new_en = EDU_UDD[da]
            r["description_en"] = new_en
            r["description_short"] = new_en
            fixed["EDU_udd"] += 1
        elif cat == "EDU_disced":
            m = COMPOUND_RE.search(da)
            stem = COMPOUND_RE.sub("", da).strip()
            if stem in EDU_DISCED_STEM:
                new_en = EDU_DISCED_STEM[stem] + (m.group(0) if m else "")
                r["description_en"] = new_en
                r["description_short"] = EDU_DISCED_STEM[stem]
                fixed["EDU_disced"] += 1
        elif cat == "EDU_field" and da in EDU_FIELD:
            new_en = EDU_FIELD[da]
            r["description_en"] = new_en
            r["description_short"] = new_en
            fixed["EDU_field"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    for k, v in fixed.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
