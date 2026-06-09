#!/usr/bin/env python3
"""Fill empty `description_da` for STRUCTURAL / numeric / quantile categories only.

This does NOT invent code meanings (HARD RULES). It either:
  (A) copies Danish text already present in the `description` field
      (rows of the form "Dansk tekst (English gloss)"), or
  (B) renders a deterministic Danish label for a self-evident structural
      pattern (a year, a grade, a percentile/quantile, a visit-count bin, …),
      where the meaning is fully given by `description_en`.

It SKIPS:
  - rows whose value is empty, or whose description is an `[UNMAPPED]` /
    `[Unresolved]` placeholder (these are genuine gaps — leave them),
  - LAB_db07 and LAB_socio (the unresolved legacy codes),
  - anything not matched by an explicit rule (reported, left empty).

Each filled row gets description_en_source untouched and a note via the
`source` column is NOT changed; provenance for these structural Danish labels
is "structural" (recorded in description_en_source only if it was empty).

Usage: python3 scripts/fill_empty_da_structural.py [--dry-run]
"""
import argparse, csv, re
from collections import Counter

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
SKIP_CATS = {"LAB_db07", "LAB_socio"}

# (B) Domain phrase -> Danish, for "<phrase>: N (bin)" / "<phrase>: a-b (bin)" and
# "<phrase> - Nth percentile" style structural descriptions.
PHRASE_DA = {
    "outpatient visits (DW)": "ambulante besøg (DW)",
    "dental visits (DDK)": "tandlægebesøg (DDK)",
    "outpatient surgical visits (DWK)": "ambulante kirurgiske besøg (DWK)",
    "outpatient group visits (DWG)": "ambulante gruppebesøg (DWG)",
    "GP visits": "besøg hos alment praktiserende læge",
    "lab tests (ML)": "laboratorieprøver (ML)",
    "gestational age weeks": "gestationsalder i uger",
    "medication prescriptions (L)": "medicinordinationer (L)",
    "inpatient days (ST)": "indlæggelsesdage (ST)",
    "specialist visits (MG)": "speciallægebesøg (MG)",
    "emergency visits (TU)": "skadestuebesøg (TU)",
    "inpatient admissions (GI)": "indlæggelser (GI)",
    "psychiatric contacts (PK)": "psykiatriske kontakter (PK)",
    "active days": "aktive dage",
    "total absence days": "samlede fraværsdage",
    "legal absence days": "lovligt fravær (dage)",
    "sick days": "sygedage",
    "unauthorized absence days": "ulovligt fravær (dage)",
    "education days": "uddannelsesdage",
    "ECTS credits": "ECTS-point",
    "sentence length": "domslængde",
    "unconditional sentence length": "ubetinget domslængde",
    "fine amount": "bødebeløb",
    "daily fine amount": "dagbødebeløb",
    "daily fine count": "antal dagbøder",
    "Birth weight": "Fødselsvægt",
    "Birth length/height": "Fødselslængde/-højde",
    "Educational wellbeing score": "Trivselsscore (uddannelse)",
    "Sentence revocation": "Inddragelse af kørekort/dom",
}


def da_from_structural(en):
    """Return a Danish rendering for a recognized structural English description, else None."""
    s = en.strip()
    # Year / month / counts
    m = re.fullmatch(r"Birthyear (\d{4})", s);            # Birthyear 1926
    if m: return f"Fødselsår {m.group(1)}"
    m = re.fullmatch(r"Birth month (\d{1,2})", s)
    if m: return f"Fødselsmåned {m.group(1)}"
    m = re.fullmatch(r"Grade (\d+) \(exam grade\)", s)
    if m: return f"Karakter {m.group(1)} (eksamenskarakter)"
    m = re.fullmatch(r"Urgency level (\d+)", s)
    if m: return f"Hastegrad {m.group(1)}"
    m = re.fullmatch(r"Number of siblings at birth (\d+)", s)
    if m: return f"Antal søskende ved fødsel {m.group(1)}"
    if s == "Sex: Female": return "Køn: Kvinde"
    if s == "Sex: Male": return "Køn: Mand"
    # Manual bin family/persons/children
    m = re.fullmatch(r"Manual bin: (\d+) families in the household", s)
    if m: return f"Manuelt interval: {m.group(1)} familier i husstanden"
    m = re.fullmatch(r"Manual bin: (\d+) persons in the family", s)
    if m: return f"Manuelt interval: {m.group(1)} personer i familien"
    m = re.fullmatch(r"Manual bin: (\d+) children in the family", s)
    if m: return f"Manuelt interval: {m.group(1)} børn i familien"
    m = re.fullmatch(r"Number of (children|persons) in family: over (\d+) \(bin\)", s)
    if m:
        w = "børn" if m.group(1) == "children" else "personer"
        return f"Antal {w} i familien: over {m.group(2)} (interval)"
    m = re.fullmatch(r"Number of families in household: over (\d+) \(bin\)", s)
    if m: return f"Antal familier i husstanden: over {m.group(1)} (interval)"
    # "<phrase>: N (bin)" or "<phrase>: a-b (bin)"
    m = re.fullmatch(r"(.+?): (\d+(?:-\d+)?) \(bin\)", s)
    if m and m.group(1) in PHRASE_DA:
        return f"{PHRASE_DA[m.group(1)]}: {m.group(2)} (interval)"
    # "<phrase>: quantile N"
    m = re.fullmatch(r"(.+?): quantile (\d+)", s)
    if m and m.group(1) in PHRASE_DA:
        return f"{PHRASE_DA[m.group(1)]}: kvantil {m.group(2)}"
    # "<phrase> - Nth percentile [(newborns)]"
    m = re.fullmatch(r"(.+?) - (\d+)(?:st|nd|rd|th) percentile( \(newborns\))?", s)
    if m and m.group(1) in PHRASE_DA:
        suffix = " (nyfødte)" if m.group(3) else ""
        return f"{PHRASE_DA[m.group(1)]} – {m.group(2)}. percentil{suffix}"
    return None


PAREN_EN = re.compile(r"\s*\([^)]*\)")
DANISH_CHARS = re.compile(r"[æøåÆØÅ]")


def da_from_description(desc, en):
    """If `description` carries a Danish form 'Dansk (English)' that `en` dropped,
    return the Danish (English parenthetical removed, 'code'->'kode'). Else None."""
    if "[UNMAPPED]" in desc or "[Unresolved]" in desc:
        return None
    stripped = PAREN_EN.sub("", desc).strip()
    if not stripped:
        return None
    # Only trust it as Danish if it differs from the English OR contains Danish letters
    looks_danish = DANISH_CHARS.search(stripped) or (desc != en)
    if not looks_danish:
        return None
    # If after removing the paren we're left with the same pure-English text, skip
    if stripped == PAREN_EN.sub("", en).strip() and not DANISH_CHARS.search(stripped):
        return None
    return stripped.replace(" - code ", " - kode ")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    filled_A = Counter(); filled_B = Counter(); skipped = Counter()
    samples = []
    for r in rows:
        if (r.get("description_da") or "").strip():
            continue
        cat = r["category"]
        val = (r.get("value") or "").strip()
        desc = (r.get("description") or "").strip()
        en = (r.get("description_en") or "").strip()
        if cat in SKIP_CATS or not val or "[UNMAPPED]" in desc or "[Unresolved]" in desc:
            skipped[cat] += 1; continue
        da = da_from_description(desc, en)
        rule = "A"
        if not da:
            da = da_from_structural(en); rule = "B"
        if not da:
            skipped[cat] += 1; continue
        r["description_da"] = da
        (filled_A if rule == "A" else filled_B)[cat] += 1
        if len(samples) < 30:
            samples.append((rule, cat, en[:42], da[:46]))

    print(f"Filled via (A) copy-Danish-from-description: {sum(filled_A.values())}")
    for k, n in filled_A.most_common(): print(f"   {n:5d}  {k}")
    print(f"\nFilled via (B) structural template: {sum(filled_B.values())}")
    for k, n in filled_B.most_common(): print(f"   {n:5d}  {k}")
    print(f"\nSkipped (placeholder/unmapped/unmatched): {sum(skipped.values())}")
    for k, n in skipped.most_common(): print(f"   {n:5d}  {k}")
    print("\nSamples (rule, category, EN, -> DA):")
    for s in samples: print("  ", s)

    if args.dry_run:
        print("\n[dry-run] no changes written"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER}")


if __name__ == "__main__":
    main()
