#!/usr/bin/env python3
"""Full audit of Danish descriptions, English translations, and official
English. Also adds a new column `description_en_official_source` that
records WHERE the official English came from (which classification file).

Official-English source tags set by this pass (by re-deriving from the
authoritative source files):
    who-icd10        WHO ICD-10 (2019 ClaML)
    who-atc          WHO ATC 2021
    nace2            NACE Rev. 2 (EU)
    isco08           ISCO-08 (ILO) via same-code match
    isco88           ISCO-88 (ILO) via same-code match
    isco08-crosswalk ISCO-08 via Danish-name match (LAB_disco mixed-era rows)
    isco88-crosswalk ISCO-88 via Danish-name match
    (empty)          No authoritative source available for this row

An audit report is written to `archive/translation_audit_report.csv` summarising:
  category, rows, empty_en, translated_en, official_en, and flags
  (mojibake, danish-leftover, repetitive).

Usage:
    python3 scripts/audit_and_tag_official.py [--dry-run]
"""
import argparse
import csv
import re
from collections import Counter, defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
REPORT_PATH = "archive/translation_audit_report.csv"

# ---- Sources ---------------------------------------------------------------

def load_icd10():
    d = {}
    with open("raw/dst_downloads/icd10_who_2019_en.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["code"]] = r["title_en"]
    return d


def load_atc():
    d = {}
    with open("raw/dst_downloads/atc_who_2021_en.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            code = r["atc_code"].strip()
            name = r["atc_name"].strip()
            if code and name and code not in d:
                d[code] = name
    return d


def load_nace():
    d = {}
    with open("raw/dst_downloads/nace_rev2_en.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["Code"]] = r["Description"]
    return d


def load_isco(path):
    d = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[r["code"]] = r["title_en"]
    return d


def load_disco08_da():
    d = {}
    with open("raw/LAB_disco.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            code = r.get("KODE", "").strip().strip('"')
            title = r.get("TITEL", "").strip()
            if code and title:
                d[code] = title
    return d


def load_disco88_da():
    d = {}
    with open("raw/LAB_disco_codes.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                d[parts[0].strip()] = parts[1].strip()
    return d


# ---- Mappers ---------------------------------------------------------------

def danish_icd_to_who(v):
    if not v.startswith("D") or len(v) < 3 or not v[1].isalpha():
        return None
    s = v[1:]
    return s if len(s) <= 3 else s[:3] + "." + s[3:]


def icd_ancestors(code):
    """Yield the code and its ancestors toward the 3-character category.
    E.g. 'E11.6' → 'E11.6', 'E11', 'E1', 'E'.
    """
    yield code
    base = code.split(".")[0] if "." in code else code
    if base != code:
        yield base
    while len(base) > 1:
        base = base[:-1]
        yield base


def atc_label(code, atc):
    full = atc.get(code)
    cls = None
    if len(code) > 5:
        cls = atc.get(code[:5]) or atc.get(code[:4]) or atc.get(code[:3])
    if full and cls and full.lower() != cls.lower():
        return f"{cls}, {full}"
    return full or cls


def db07_candidates(v):
    vv = v.replace(".0", "")
    if len(vv) >= 4: yield f"{vv[:2]}.{vv[2:4]}"
    if len(vv) >= 3: yield f"{vv[:2]}.{vv[2]}"
    if len(vv) >= 2: yield vv[:2]


def isco_lookup(v, table):
    vv = v.replace(".0", "")
    for n in (4, 3, 2, 1):
        prefix = vv[:n]
        for cand in (prefix.rstrip("0") or prefix, prefix):
            if cand in table:
                return table[cand]
    return None


def normalize(s):
    return re.sub(r"\s+", " ", s.lower().strip())


def build_db07_da_en_index(rows, nace):
    """Return {normalized_da: english_title} from LAB_db07 rows whose official
    EN is set via NACE Rev 2. Lets LAB_nace rows (NACE Rev 1.1) reuse a NACE
    Rev 2 English title when the Danish description matches exactly."""
    idx = {}
    for r in rows:
        if r["category"] != "LAB_db07":
            continue
        vv = r["value"].replace(".0", "")
        # Recompute whether this row has a NACE-2-backed label
        en = None
        if len(vv) >= 4 and f"{vv[:2]}.{vv[2:4]}" in nace:
            en = nace[f"{vv[:2]}.{vv[2:4]}"]
        elif len(vv) >= 3 and f"{vv[:2]}.{vv[2]}" in nace:
            en = nace[f"{vv[:2]}.{vv[2]}"]
        elif len(vv) >= 2 and vv[:2] in nace:
            en = nace[vv[:2]]
        if en:
            da = normalize(r["description_da"])
            if da and da not in idx:
                idx[da] = en
    return idx


# ---- Main ------------------------------------------------------------------

DANISH_CHARS = re.compile(r"[æøåÆØÅ]")
MOJIBAKE = re.compile(r"[\u0080-\u009f]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    icd10 = load_icd10()
    atc = load_atc()
    nace = load_nace()
    isco08 = load_isco("raw/dst_downloads/isco08_en.csv")
    isco88 = load_isco("raw/dst_downloads/isco88_en.csv")
    disco08_da = load_disco08_da()
    disco88_da = load_disco88_da()
    # db07_da_en_index is populated after the first pass; see below

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if "description_en_official_source" not in fieldnames:
        fieldnames.append("description_en_official_source")
    for r in rows:
        r.setdefault("description_en_official_source", "")

    # Build per-category audit counters
    audit = defaultdict(lambda: Counter())

    # Rebuild description_en_official and its source fresh (idempotent)
    for r in rows:
        cat = r["category"]
        v = r["value"]
        da = r["description_da"].strip()
        en = r["description_en"].strip()

        audit[cat]["rows"] += 1
        if not en:
            audit[cat]["empty_en"] += 1
        if MOJIBAKE.search(da) or MOJIBAKE.search(en):
            audit[cat]["mojibake"] += 1
        if DANISH_CHARS.search(en):
            audit[cat]["danish_chars_in_en"] += 1

        # Reset official (we'll recompute)
        r["description_en_official"] = ""
        r["description_en_official_source"] = ""

        # --- Compute official English + its source ---
        source_tag = ""
        official = ""

        if cat == "HEA_ICD10":
            who = danish_icd_to_who(v)
            if who:
                for cand in icd_ancestors(who):
                    if cand in icd10:
                        official = icd10[cand]
                        source_tag = "who-icd10"
                        break

        elif cat == "HEA_atc":
            label = atc_label(v, atc)
            if label:
                official = label
                source_tag = "who-atc"

        elif cat == "LAB_db07":
            for cand in db07_candidates(v):
                if cand in nace:
                    official = nace[cand]
                    source_tag = "nace2"
                    break

        elif cat == "LAB_disco08":
            # Same-code Danish agreement check, then ISCO-08 lookup
            lab = isco_lookup(v, isco08)
            if lab:
                # Reliability: DA either empty, or matches DISCO-08 DA
                if not da or (v in disco08_da and normalize(disco08_da[v]) == normalize(da)):
                    official = lab
                    source_tag = "isco08"
                elif v in disco08_da:
                    # DA mismatch at same code → skip (likely mismapped version)
                    pass
                else:
                    # Code not in DISCO-08 raw but ISCO-08 gave a label; accept
                    official = lab
                    source_tag = "isco08"

        elif cat == "LAB_nace":
            # NACE Rev 1.1 codes. No direct NACE Rev 1.1 source, but we can
            # reuse a NACE Rev 2 English title when the Danish description
            # matches a DB07 row exactly (concept-level crosswalk).
            # Populated lazily after the first pass — see below.
            pass

        elif cat == "LAB_disco":
            # Per-row: detect DISCO-08 or DISCO-88 era, then look up matching ISCO
            # 1. DA matches DISCO-08 at same code → ISCO-08
            if v in disco08_da and normalize(disco08_da[v]) == normalize(da):
                lab = isco_lookup(v, isco08)
                if lab:
                    official, source_tag = lab, "isco08-crosswalk"
            # 2. DA matches DISCO-88 at same code → ISCO-88
            if not official and v in disco88_da and normalize(disco88_da[v]) == normalize(da):
                lab = isco_lookup(v, isco88)
                if lab:
                    official, source_tag = lab, "isco88"
            # 3. Code exists in DISCO-88 and DA empty/unknown → trust ISCO-88 by code
            if not official and v in disco88_da and not da:
                lab = isco_lookup(v, isco88)
                if lab:
                    official, source_tag = lab, "isco88"

        if official:
            r["description_en_official"] = official
            r["description_en_official_source"] = source_tag
            audit[cat]["official_en"] += 1
            audit[cat][f"src:{source_tag}"] += 1

        # Source of description_en (refreshed)
        if not en:
            r["description_en_source"] = "empty"
        elif official and en == official:
            r["description_en_source"] = source_tag
        elif da and normalize(en) == normalize(da):
            r["description_en_source"] = "copy-of-da"
        else:
            r["description_en_source"] = "translated"

    # Second pass: ISO-3166 country names for DEM_opr / DEM_statsb
    try:
        import pycountry
        iso_names = set()
        for c in pycountry.countries:
            iso_names.add(c.name.lower())
            if hasattr(c, "official_name"):
                iso_names.add(c.official_name.lower())
            if hasattr(c, "common_name"):
                iso_names.add(c.common_name.lower())
        for c in pycountry.historic_countries:
            iso_names.add(c.name.lower())
        # Hand-add a few variants DST uses
        iso_names.update({"united states", "united kingdom", "south korea",
                          "north korea", "russia", "vietnam", "czech republic",
                          "north macedonia", "myanmar", "swaziland", "east timor",
                          "bosnia and herzegovina", "democratic republic of the congo",
                          "republic of the congo", "ivory coast", "yugoslavia",
                          "czechoslovakia", "soviet union", "west germany",
                          "east germany", "stateless", "unknown", "palestine"})
        for r in rows:
            if r["category"] not in ("DEM_opr", "DEM_statsb"):
                continue
            if r["description_en_official"].strip():
                continue
            en = r["description_en"].strip()
            if not en:
                continue
            if en.lower() in iso_names:
                r["description_en_official"] = en
                r["description_en_official_source"] = "iso3166"
                r["description_en_source"] = "iso3166"
                audit[r["category"]]["official_en"] += 1
                audit[r["category"]]["src:iso3166"] += 1
    except ImportError:
        print("  (pycountry not installed — skipping ISO-3166 country tagging)")

    # Third pass: LAB_nace rows → reuse DB07 Danish-name index for English
    db07_idx = build_db07_da_en_index(rows, nace)
    for r in rows:
        if r["category"] != "LAB_nace":
            continue
        if r["description_en_official"].strip():
            continue
        da = normalize(r["description_da"])
        if not da:
            continue
        if da in db07_idx:
            r["description_en_official"] = db07_idx[da]
            r["description_en_official_source"] = "nace2-crosswalk"
            audit["LAB_nace"]["official_en"] += 1
            audit["LAB_nace"]["src:nace2-crosswalk"] += 1
            # Refresh description_en_source too
            en_val = r["description_en"].strip()
            if en_val == r["description_en_official"]:
                r["description_en_source"] = "nace2-crosswalk"

    # Write master
    if not args.dry_run:
        with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    # ---- Summary ---------------------------------------------------------
    total = len(rows)
    total_empty = sum(a["empty_en"] for a in audit.values())
    total_off = sum(a["official_en"] for a in audit.values())
    total_moji = sum(a["mojibake"] for a in audit.values())
    total_dan = sum(a["danish_chars_in_en"] for a in audit.values())

    print("=" * 72)
    print(f"Audit of {total} rows across {len(audit)} categories")
    print("=" * 72)
    print(f"  Rows with description_en:              {total - total_empty} "
          f"({(total-total_empty)/total*100:.1f}%)")
    print(f"  Rows with description_en_official:     {total_off} "
          f"({total_off/total*100:.1f}%)")
    print(f"  Rows with mojibake artifacts:          {total_moji}")
    print(f"  Rows with Danish chars in EN:          {total_dan}")
    print(f"  Rows with empty EN:                    {total_empty}")

    # Official-source breakdown
    src_totals = Counter()
    for a in audit.values():
        for k, n in a.items():
            if k.startswith("src:"):
                src_totals[k[4:]] += n
    print(f"\nOfficial-English sources:")
    for s, n in src_totals.most_common():
        print(f"  {s}: {n}")

    # Per-category table
    print(f"\n{'Category':<20} {'Rows':>6} {'EmptyEN':>8} {'OfficialEN':>11} "
          f"{'Mojibake':>9} {'DA-leftover':>12}")
    for cat in sorted(audit):
        a = audit[cat]
        print(f"  {cat:<18} {a['rows']:>6} {a['empty_en']:>8} "
              f"{a['official_en']:>11} {a['mojibake']:>9} "
              f"{a['danish_chars_in_en']:>12}")

    # Write detailed per-category CSV report
    if not args.dry_run:
        with open(REPORT_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "category", "rows", "empty_en", "official_en",
                "mojibake", "danish_chars_in_en",
                "src_who_icd10", "src_who_atc", "src_nace2",
                "src_isco08", "src_isco88", "src_isco08_crosswalk",
            ])
            for cat in sorted(audit):
                a = audit[cat]
                w.writerow([
                    cat, a["rows"], a["empty_en"], a["official_en"],
                    a["mojibake"], a["danish_chars_in_en"],
                    a.get("src:who-icd10", 0), a.get("src:who-atc", 0),
                    a.get("src:nace2", 0), a.get("src:isco08", 0),
                    a.get("src:isco88", 0), a.get("src:isco08-crosswalk", 0),
                ])
        print(f"\nPer-category report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
