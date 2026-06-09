#!/usr/bin/env python3
"""Fix mojibake artifacts in MASTER_CATEGORY_MAPPINGS.csv.

The Danish-character encoding artifacts originate from reading a MacRoman-
encoded CSV (raw/HEA_speciale_koder_med_tekst_samt_vejledning.csv) as Latin-1,
plus a double-UTF-8 encoding pass in a few cases. All defects are
deterministic character swaps — restore them before any re-translation.

After fixing description_da, any description_en that is an identical copy
of the old (corrupt) description_da is cleared so the translation pipeline
will regenerate it from the restored Danish text.

Usage:
    python3 scripts/fix_mojibake.py [--dry-run]
"""
import argparse
import csv
from collections import Counter

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Mojibake → correct character.  Patterns chosen by inspection of contexts:
#   'Ã\x98'  → 'Ø'   e.g. "Ã\x98jenlægehjælp" → "Øjenlægehjælp"
#   '¾'      → 'æ'   e.g. "Till¾g"            → "Tillæg"
#   '¿'      → 'ø'   e.g. "Blodpr¿vetagning"  → "Blodprøvetagning"
#   '\x8c'   → 'å'   e.g. "P\x8cr¿rende"      → "Pårørende"
#   '\x81'   → 'å'   e.g. "\x81rskontrol"     → "årskontrol" (lowercase)
#   '\x8e'   → 'é'   e.g. "diarr\x8e"         → "diarré"
#   '\x8f'   → 'é'   e.g. "diarr\x8f"         → "diarré"
MOJIBAKE_MAP = [
    ("Ã\x98", "Ø"),
    ("¾", "æ"),
    ("¿", "ø"),
    ("\x8c", "å"),
    ("\x81", "å"),
    ("\x8e", "é"),
    ("\x8f", "é"),
    # KPLL / Medicinsk Laboratorium rows — pre-2005 SAS encoding leftovers.
    ("\x15", "Ø"),   # e.g. "KVIKS\x15LV" → "KVIKSØLV"
    ("\x16", "Æ"),   # e.g. "\x16ggehvide" → "Æggehvide"
    ("\x17", "å"),   # e.g. "m\x17ling" → "måling"
    ("À", "ø"),      # e.g. "PrÀve" → "Prøve", "LÀg" → "Løg"
    ("`", "æ"),      # e.g. "H`moglobin" → "Hæmoglobin"
]


def fix_text(s: str) -> str:
    if not s:
        return s
    for bad, good in MOJIBAKE_MAP:
        if bad in s:
            s = s.replace(bad, good)
    return s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    fix_counts = Counter()
    cleared_en = 0

    for row in rows:
        old_da = row.get("description_da", "")
        old_en = row.get("description_en", "")
        old_desc = row.get("description", "")
        old_short = row.get("description_short", "")

        new_da = fix_text(old_da)
        new_en = fix_text(old_en)
        new_desc = fix_text(old_desc)
        new_short = fix_text(old_short)

        if new_da != old_da:
            fix_counts["description_da"] += 1
            row["description_da"] = new_da
            # If EN was a copy of the corrupt DA, clear it so retranslation runs
            if old_en.strip() and old_en.strip() == old_da.strip():
                row["description_en"] = ""
                cleared_en += 1
        if new_en != old_en and row["description_en"]:
            # Only apply EN fix if we didn't just clear it
            fix_counts["description_en"] += 1
            row["description_en"] = new_en
        if new_desc != old_desc:
            fix_counts["description"] += 1
            row["description"] = new_desc
        if new_short != old_short:
            fix_counts["description_short"] += 1
            row["description_short"] = new_short

    print("Mojibake fixes per field:")
    for k, n in fix_counts.items():
        print(f"  {k}: {n}")
    print(f"Cleared description_en for retranslation: {cleared_en}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER_PATH}")


if __name__ == "__main__":
    main()
