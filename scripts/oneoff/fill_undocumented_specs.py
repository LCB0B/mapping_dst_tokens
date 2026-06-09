#!/usr/bin/env python3
"""Fill some of the 1,636 "(procedure not documented)" HEA_speciale rows
from additional authoritative sources:

  - Re-parsed SDS Ydelsesoversigt (including rows where DST documented the
    code but with "Ingen tekst tilgængelig" / "no text available") — 148 rows
  - PLO Honorartabel + Takstmappe (current GP fee schedule) — 24 rows

Rows that remain undocumented after this pass are genuinely not published
in any DST/PLO source we could locate. The specialty prefix in those rows
is correct; the procedure-level detail predates DST's 1990-2008 window,
was region-specific without national publication, or was removed from
the fee schedule.

Usage:
    python3 scripts/fill_undocumented_specs.py [--dry-run]
"""
import argparse
import csv
import re

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def load_sds_ydelser():
    d = {}
    with open("raw/dst_downloads/ssr_ydelser_full.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["code6"]] = (r["specialty_name_da"], r["ydelse_text_da"])
    return d


def load_plo_gp():
    d = {}
    with open("raw/dst_downloads/plo_gp_ydelser_merged.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["ydelsesnr"]] = r["description_da"]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sds = load_sds_ydelser()
    plo = load_plo_gp()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    stats = {"from_sds": 0, "from_plo": 0, "still_undocumented": 0,
             "marked_dst_no_text": 0}

    for r in rows:
        if r["category"] != "HEA_speciale":
            continue
        if "not documented" not in r["description_da"]:
            continue

        v = r["value"]
        # 1. Try SDS Ydelsesoversigt (re-parsed, includes "Ingen tekst")
        if v in sds:
            spec_name, ytext = sds[v]
            if ytext.lower().startswith("(ingen tekst"):
                # DST lists the code but has no description
                new_da = f"{spec_name}, (ingen tekst tilgængelig)"
                stats["marked_dst_no_text"] += 1
            else:
                new_da = f"{spec_name}, {ytext}"
                stats["from_sds"] += 1
            r["description_da"] = new_da
            r["description"] = new_da
            # Also refresh description_en — leave a marker; translation pass would fill properly
            if "(procedure not documented)" in r["description_en"]:
                # Compose simple EN placeholder matching the new DA
                if "(ingen tekst" in new_da:
                    # Use existing specialty EN
                    en_official = r.get("description_en_official", "")
                    if en_official:
                        r["description_en"] = f"{en_official} (DST code exists, no description)"
                else:
                    # Real DST Danish — keep DA for now (translation script would pick it up)
                    r["description_en"] = new_da
            continue

        # 2. Try PLO GP fee schedule (for 80xxxx codes)
        if len(v) == 6 and v.startswith("80"):
            proc = v[2:]
            if proc in plo:
                new_da = f"Almen Lægehjælp 80, {plo[proc]}"
                r["description_da"] = new_da
                r["description"] = new_da
                if "(procedure not documented)" in r["description_en"]:
                    r["description_en"] = f"General practitioner, {plo[proc]}"
                stats["from_plo"] += 1
                continue

        stats["still_undocumented"] += 1

    print("Fill results:")
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
