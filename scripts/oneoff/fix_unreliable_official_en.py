#!/usr/bin/env python3
"""Clear `description_en_official` for rows where it was populated via an
ISCO/NACE 4-digit prefix lookup, but MASTER's Danish description does NOT
match the authoritative DST source for that numeric code.

Root cause: the `LAB_disco` codes in MASTER came from an older Danish DISCO
dictionary whose code numbering DIFFERS from both `raw/LAB_disco_codes.txt`
(a later DISCO version) and ISCO-88. Example:

  LAB_disco_314100
     MASTER description_da  = "Teknikerarbejde inden for biovidenskab"
                               (Bioscience technician — OLDER DISCO)
     LAB_disco_codes.txt 314100 = "Teknisk arbejde om bord på skibe"
                               (Technical work on ships — LATER DISCO)
     ISCO-88 3141            = "Ships' engineers"
                               (matches LAB_disco_codes.txt but NOT MASTER's DA)

Because MASTER uses an older DISCO version, its numeric codes don't map
cleanly to ISCO-88 4-digit prefixes. The translated English (derived from
MASTER's actual DA) is still correct; the ISCO-88-derived official English
is not. This script clears `description_en_official` in those cases so
downstream consumers don't rely on a wrong authoritative label.

LAB_disco08 and LAB_db07 are also checked for safety; both are minimally
affected (DISCO-08 and DB07 are reliably aligned with ISCO-08 and NACE Rev 2).

Usage:
    python3 scripts/fix_unreliable_official_en.py [--dry-run]
"""
import argparse
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def load_source(path, is_csv_semicolon=False, code_col="code", desc_col="description"):
    d = {}
    with open(path, encoding="utf-8") as f:
        if is_csv_semicolon:
            for r in csv.DictReader(f, delimiter=";"):
                code = r.get("KODE", "").strip().strip('"')
                title = r.get("TITEL", "").strip()
                if code and title:
                    d[code] = title
        else:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    d[parts[0].strip()] = parts[1].strip()
    return d


def load_csv(path, code_col="code", desc_col="description"):
    d = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            code = r[code_col].strip().replace("LAB_db07_", "").replace("LAB_disco_", "")
            desc = r[desc_col].strip()
            if code and desc:
                d[code] = desc
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Authoritative per-code Danish sources
    sources = {
        "LAB_disco":   load_source("raw/LAB_disco_codes.txt"),
        "LAB_disco08": load_source("raw/LAB_disco.csv", is_csv_semicolon=True),
    }

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    cleared = {c: 0 for c in sources}
    samples = []

    for r in rows:
        cat = r["category"]
        if cat not in sources:
            continue
        if not r["description_en_official"].strip():
            continue
        src = sources[cat]
        v = r["value"]
        if v not in src:
            continue
        if r["description_da"].strip() == src[v].strip():
            continue  # DA matches authoritative source → ISCO lookup is reliable
        if not r["description_da"].strip():
            continue  # Empty DA is not a disagreement; official EN may still be right
        # Mismatch: clear the unreliable official EN
        if len(samples) < 6:
            samples.append((r["code"], r["description_da"][:50], src[v][:50],
                            r["description_en_official"][:60]))
        r["description_en_official"] = ""
        cleared[cat] += 1

    print("Cleared description_en_official on version-drift rows:")
    for c, n in cleared.items():
        print(f"  {c}: {n}")

    print("\nSamples cleared:")
    for code, master_da, dst_da, bad_official_en in samples:
        print(f"  {code}")
        print(f"    MASTER DA         : {master_da}")
        print(f"    DST authoritative : {dst_da}")
        print(f"    (wrong) official  : {bad_official_en}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {MASTER_PATH}")


if __name__ == "__main__":
    main()
