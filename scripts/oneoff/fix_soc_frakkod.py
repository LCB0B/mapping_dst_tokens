#!/usr/bin/env python3
"""Fix the unsourced SOC_frakkod rows (= DST AFG_FRAKKOD, KRAF register).

SOC_frakkod is the DST TIMES variable AFG_FRAKKOD (Kriminalstatistik) —
"Frakendelsens paragraf i lovgivningen": which Road-Traffic-Act / special-law
paragraph a deprivation (driving-licence disqualification, alcohol-interlock
scheme, residence ban, …) was sentenced under. Its value-set table is
D281700.TXT_FRAKKOD == raw/SOC_frakkod.txt.
Docs: https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakkod

9 rows were unsourced (source startswith none|generated) and 5 of them held
HALLUCINATED "prison" labels (ÅA="Open imprisonment" etc.). The Danish here is
pulled VERBATIM from raw/SOC_frakkod.txt (so it is sourced, not hand-typed);
English is a translation. Codes absent from the source file are left
[Unresolved] / low — never invented (HARD RULES).

Re-runnable. Usage: python3 scripts/fix_soc_frakkod.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
SRC_FILE = "raw/SOC_frakkod.txt"

# English translations for the codes we are fixing (translated from the
# verbatim Danish in SRC_FILE; § n = paragraf, stk = subsection, nr = number).
EN = {
    "ÅA": "Alcohol interlock (Road Traffic Act § 60a(3)) — entered mandatory scheme",
    "ÅB": "Alcohol interlock (Road Traffic Act § 132a(1)) — entered voluntary scheme",
    "ÅC": "Exited the alcohol interlock scheme",
    "UØ": "Driving-licence disqualification (Road Traffic Act § 126(1)(7), cf. § 125(2)) + separate disqualification",
    "UÅ": "Driving-licence disqualification (Road Traffic Act § 126(1)(7), cf. § 125(3))",
    "UÆ": "Driving-licence disqualification (Road Traffic Act § 126(1)(7), cf. § 125(2) and (3))",
    "ØA": "Disqualified from operating as a driving instructor (Road Traffic Act § 66a(1))",
}


def parse_source():
    d = {}
    for line in open(SRC_FILE, encoding="utf-8"):
        parts = [p for p in line.rstrip("\n").split("\t") if p.strip()]
        if len(parts) >= 2:
            code = parts[0].strip()
            text = " ".join(p.strip() for p in parts[1:]).strip()
            if code.lower().startswith("d281700") or "frakendelsens paragraf" in text.lower():
                continue
            d.setdefault(code, text)   # keep first (current) definition
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = parse_source()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    fixed = unresolved = 0
    for r in rows:
        if r.get("category") != "SOC_frakkod":
            continue
        if not (r.get("source") or "").strip().lower().startswith("none|generated"):
            continue
        code = (r.get("value") or "").strip()
        da = src.get(code)
        if da:
            en = EN.get(code) or da
            r["description"] = da
            r["description_da"] = da
            r["description_en"] = en
            r["source"] = "raw_soc_frakkod"
            r["description_en_source"] = "translated"
            r["confidence_level"] = "high"
            fixed += 1
        else:
            # code not in the authoritative value set — do NOT invent
            mark = f"[Unresolved SOC_frakkod (AFG_FRAKKOD) code: {code}]"
            r["description"] = mark
            r["description_da"] = ""
            r["description_en"] = mark
            r["source"] = "none|generated"
            r["description_en_source"] = ""
            r["confidence_level"] = "low"
            unresolved += 1

    print(f"SOC_frakkod: fixed {fixed} from source, marked {unresolved} unresolved")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
