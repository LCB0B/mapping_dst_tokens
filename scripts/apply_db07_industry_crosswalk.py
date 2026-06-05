#!/usr/bin/env python3
"""Apply the empirical DB07-5digit -> DB93/nace industry crosswalk (built on the VM).

The 5-digit LAB_db07 weak codes (11100..89900) are leading-zero-stripped low-division
(agriculture/forestry/fishing/mining) industry codes whose encoding is ambiguous online (see
SOURCE_AUDIT.md). They are resolved empirically: for the same firm observed across the DB-version
boundary, each db07 code is mapped to the DB93/nace code it co-occurs with. Input:
  transition/industry_crosswalk_empirical.csv  (per code: best_cross family/code, cooc share, n)

The nace (DB93) label comes from raw/LAB_nace.txt (Danish) / raw/nace.txt (English). This confirmed
the old NACE-Rev2 guesses were wrong (e.g. 13000 = Planteskoler/plant nurseries, NOT textiles;
61000 = crude petroleum, NOT telecom). Apply threshold: share>=0.3 and n>=20; else [Unresolved].
514620 and 999999 are handled separately (direct DB93) and skipped here.

Re-runnable. Usage: python3 scripts/apply_db07_industry_crosswalk.py [--dry-run]
"""
import argparse, csv, json

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
CW = "transition/industry_crosswalk_empirical.csv"


def parse_nace(path):
    d = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = [p for p in line.rstrip("\n").split("\t") if p.strip()]
        for i, p in enumerate(parts):
            if p.strip().isdigit():
                d.setdefault(p.strip(), " ".join(x.strip() for x in parts[i+1:]).strip()); break
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    nace_da = parse_nace("raw/LAB_nace.txt"); nace_en = parse_nace("raw/nace.txt")
    ind = {}
    for r in csv.DictReader(open(CW, encoding="utf-8")):
        if r["family"] == "db07":
            code = r["code"].replace("LAB_db07_", "")
            nc = r["best_cross_code"].strip(); sh = r["cooc_share"].strip()
            n = 0
            try:
                n = json.loads(r["cross_all"] or "{}").get("nace", {}).get("n", 0)
            except Exception:
                pass
            ind[code] = (nc, float(sh) if sh else 0.0, n)

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    ok = unr = 0
    for r in rows:
        if r.get("category") != "LAB_db07":
            continue
        v = (r.get("value") or "").strip()
        if not (r.get("source") or "").startswith("none"):
            continue  # already resolved (sourced), incl. 514620 / 999999
        nc, sh, n = ind.get(v, ("", 0.0, 0))
        da = nace_da.get(nc); en = nace_en.get(nc)
        if nc and da and sh >= 0.3 and n >= 20:
            conf = "high" if (sh >= 0.7 and n >= 100) else ("medium" if (sh >= 0.5 and n >= 50) else "low")
            r["description"] = da; r["description_da"] = da; r["description_en"] = en or da
            r["description_da_alt"] = f"DB07 5-digit {v}; empirical crosswalk -> DB93/nace {nc} ({sh*100:.0f}%, n={n})"
            r["source"] = "empirical_industry_crosswalk"
            r["description_en_source"] = "empirical_industry_crosswalk"
            r["confidence_level"] = conf; ok += 1
        else:
            mark = f"[Unresolved DB07 code: {v}]"
            r["description"] = mark; r["description_da"] = ""; r["description_en"] = mark
            r["source"] = "none|generated"; r["description_en_source"] = ""
            r["confidence_level"] = "low"; unr += 1
    print(f"DB07: applied={ok}, [Unresolved]={unr}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
