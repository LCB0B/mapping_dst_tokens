#!/usr/bin/env python3
"""Describe any vocab.json — including vocabs compiled at higher hierarchy levels.

Given a vocab JSON ({code: token_id}), emit a per-code table with Danish and
English descriptions. Codes are resolved in three tiers:

1. ``exact``      — the code is a row in MASTER_CATEGORY_MAPPINGS.csv. This
                    covers any standard vocab, and also many intermediate
                    hierarchy levels that happen to be tokens themselves.
2. ``reference``  — the code belongs to a hierarchical category but was
                    aggregated to a level that is not a token (e.g.
                    HEA_ICD10_DA00, HEA_atc_N02B, LAB_db07_11). The value is
                    looked up in the official classification files shipped in
                    raw/ and raw/dst_downloads/ (WHO ICD-10 2019, WHO ATC 2021,
                    DST DB07, DST DISCO/DISCO-88, ISCO-08/88, DB93/NACE,
                    DISCED, GER7). The matched reference key is recorded in
                    the ``match_key`` column so every non-exact resolution is
                    auditable.
3. ``not_found``  — no documented source covers the code. Descriptions are
                    left EMPTY (never guessed), per the repo HARD RULES.

Trailing zeros are treated as padding when matching digit-coded values
(DST 6-digit codes pad coarser levels with zeros: disco 131000 = ISCO 1310),
and one leading zero is restored for the leading-zero-stripped categories
(LAB_db07/LAB_nace: 11100 = 01.11.00). The exact key that matched is always
reported.

Usage:
    python3 scripts/describe_vocab.py VOCAB.json [-o OUT.csv]
        [--json OUT.json] [--lang da|en|both]

Run from the repo root (paths are repo-relative).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Reference-file loaders (official sources only — see CLAUDE.md HARD RULES)
# ---------------------------------------------------------------------------

def _read_csv(path, delimiter=",", encoding="utf-8-sig"):
    with open(ROOT / path, newline="", encoding=encoding) as f:
        yield from csv.DictReader(f, delimiter=delimiter)


def _strip_trailing_zero_variants(key):
    """Yield key, then progressively trailing-zero-stripped variants.

    DST 6-digit codes pad coarser levels with zeros (disco 131000 = ISCO 1310),
    so stripping trailing zeros walks up the hierarchy, most specific first.
    """
    yield key
    while len(key) > 1 and key.endswith("0"):
        key = key[:-1]
        yield key


def _digit_candidates(value):
    """Candidate reference keys for a digit-coded value, most literal first.

    Also retries with one leading zero restored, for the categories whose
    vocab values are leading-zero-stripped (LAB_db07, LAB_nace). Digit
    lengths 1 and 5 cannot be canonical NACE/DB07 codes (2/3/4/6 are), so
    there the zero-restored reading is tried first: '11100' means 01.11.00
    (grain growing), not division 11 (beverages).
    """
    bases = (value, "0" + value)
    if value.isdigit() and len(value) in (1, 5):
        bases = ("0" + value, value)
    seen = []
    for base in bases:
        for k in _strip_trailing_zero_variants(base):
            if k not in seen:
                seen.append(k)
    return seen


def _icd10_candidates(value):
    """WHO keys for a Danish SKS ICD-10 value: strip the D prefix, keep dots out.

    DA001 -> A001 ; range DA00-DA09 -> A00-A09 ; DI (chapter-ish) -> I.
    """
    v = value[1:] if value[:1] == "D" else value
    if "-" in v:
        a, b = v.split("-", 1)
        if b[:1] == "D":
            b = b[1:]
        v = f"{a}-{b}"
    return [v]


def _load_tier1_dict(fname, category, keyfunc=lambda v: v):
    """Load a lookup_dictionaries/*_dict.csv (tier-1 DST source), keyed by value."""
    out = {}
    prefix = category + "_"
    for r in _read_csv("lookup_dictionaries/" + fname):
        code = r["code"]
        if code.startswith(prefix):
            out[keyfunc(code[len(prefix):])] = r["description"]
    return out


def load_icd10():
    # Danish: the official DST dict (24,979 entries, all levels incl. 3-char),
    # then the full SKS 'dia' catalog (adds 69 codes + historical variants;
    # extracted from filer.sundhedsdata.dk SKScomplete).
    da = _load_tier1_dict("HEA_ICD10_dict.csv", "HEA_ICD10",
                          keyfunc=lambda v: _icd10_candidates(v)[0])
    sks = {}
    for r in _read_csv("raw/dst_downloads/sks_dia_dk.csv"):
        sks[_icd10_candidates(r["code"])[0]] = r["text_da"]
    en = {}
    for r in _read_csv("raw/dst_downloads/icd10_who_2019_en.csv"):
        en[r["code"].replace(".", "")] = r["title_en"]
    return {"da": [(da, "lookup_dictionaries/HEA_ICD10_dict.csv"),
                   (sks, "sks-dia")],
            "en": [(en, "who-icd10-2019")],
            "cand": _icd10_candidates}


def load_atc():
    da = {}
    for r in _read_csv("raw/HEA_atc.csv", delimiter=";"):
        k = r["Kode"]
        if k[:1] == "M" and len(k) > 1:  # SKS prefixes ATC with 'M'
            da[k[1:]] = r["Tekst"]
    en = {}
    for r in _read_csv("raw/dst_downloads/atc_who_2021_en.csv"):
        en.setdefault(r["atc_code"], r["atc_name"])
    return {"da": [(da, "raw/HEA_atc.csv (SKS)")],
            "en": [(en, "who-atc-2021")],
            "cand": lambda v: [v]}


def load_db07():
    tier1 = _load_tier1_dict("LAB_db07_dict.csv", "LAB_db07")  # 3-digit groups
    # v2 (2013) carries all 5 levels; v3 (2014) overlays newer 6-digit titles.
    da = {}
    for fname in ("raw/dst_downloads/db07_v2_2013.csv",
                  "raw/dst_downloads/db07_v3_2014.csv"):
        for r in _read_csv(fname, delimiter=";"):
            da[r["KODE"].replace(".", "")] = r["TITEL"]
    en = {}
    for r in _read_csv("raw/dst_downloads/nace_rev2_en.csv"):
        en[r["Code"].replace(".", "")] = r["Description"]
    return {"da": [(tier1, "lookup_dictionaries/LAB_db07_dict.csv"),
                   (da, "dst-db07-v2/v3")],
            "en": [(en, "nace2")],
            "cand": _digit_candidates}


def load_nace():
    da = {}
    for r in _read_csv("raw/LAB_nace.txt", delimiter="\t"):
        k = (r.get("Kode ") or r.get("Kode") or "").strip()
        if k:
            da[k] = (r.get("Tekst ") or r.get("Tekst") or "").strip()
    # English: NACE Rev 1 (1990, the basis of DB93) from the Eurostat RAMON-LD
    # mirror — see raw/dst_downloads/SOURCES.md
    en = {}
    for r in _read_csv("raw/dst_downloads/nace_rev1_en.csv"):
        en[r["code"].replace(".", "")] = r["title_en"]
    return {"da": [(da, "raw/LAB_nace.txt (DB93)")],
            "en": [(en, "nace1")],
            "cand": _digit_candidates}


def load_disco08():
    da = {}
    for r in _read_csv("raw/LAB_disco.csv", delimiter=";"):
        da[r["KODE"]] = r["TITEL"]
    en = {}
    for r in _read_csv("raw/dst_downloads/isco08_en.csv"):
        en[r["code"]] = r["title_en"]
    return {"da": [(da, "raw/LAB_disco.csv (DISCO-08)")],
            "en": [(en, "isco08")],
            "cand": _digit_candidates}


def load_disco():
    # LAB_disco is mixed DISCO-88/DISCO-08 (see docs/notes.md); aggregated
    # levels are resolved against DISCO-88/ISCO-88 and tagged as such.
    da = {}
    for r in _read_csv("raw/dst_downloads/disco88_dst.csv", delimiter=";"):
        da[r["KODE"]] = r["TITEL"]
    en = {}
    for r in _read_csv("raw/dst_downloads/isco88_en.csv"):
        en[r["code"]] = r["title_en"]
    return {"da": [(da, "dst-disco88 (NB: LAB_disco is mixed-era)")],
            "en": [(en, "isco88 (NB: LAB_disco is mixed-era)")],
            "cand": _digit_candidates}


def load_disced():
    tier1 = _load_tier1_dict("EDU_disced_dict.csv", "EDU_disced")  # 4-digit
    # full DISCED hierarchy (2/4/6/8-digit) from the official AUDD/UDD
    # crosswalk tables
    xwalk = {}
    import pandas as pd
    for fname in ("crosswalks/edu/df_AUDD_DISCED.parquet",
                  "crosswalks/edu/df_UDD_DISCED.parquet"):
        df = pd.read_parquet(ROOT / fname)
        for lvl in ("1", "2", "3", "4"):  # code5 is the AUDD code, not DISCED
            for k, t in zip(df["code" + lvl].astype(str), df["title" + lvl]):
                if k and t:
                    xwalk.setdefault(k, t)
    da = {}
    for r in _read_csv("raw/dst_downloads/audd_disced15.csv"):  # 4-digit
        da[r["code"]] = r["title"]
    for r in _read_csv("raw/EDU_field.txt", delimiter="\t"):  # 6-digit
        k = (r.get("Kode ") or r.get("Kode") or "").strip()
        if k:
            da[k] = (r.get("Tekst ") or r.get("Tekst") or "").strip()
    return {"da": [(tier1, "lookup_dictionaries/EDU_disced_dict.csv"),
                   (xwalk, "crosswalks/edu (AUDD/UDD-DISCED)"),
                   (da, "EDU_field.txt + audd_disced15.csv")],
            "en": [],
            "cand": lambda v: [v]}


def load_ger7():
    tier1 = _load_tier1_dict("SOC_ger7_dict.csv", "SOC_ger7")  # 4-digit groups
    da = {}
    for r in _read_csv("raw/dst_downloads/ger7.csv"):
        da[r["Kode"]] = r["Tekst"]
    return {"da": [(tier1, "lookup_dictionaries/SOC_ger7_dict.csv"),
                   (da, "dst-ger7")],
            "en": [],
            "cand": lambda v: [v]}


REF_LOADERS = {
    "HEA_ICD10": load_icd10,
    "HEA_atc": load_atc,
    "LAB_db07": load_db07,
    "LAB_nace": load_nace,
    "LAB_disco08": load_disco08,
    "LAB_disco": load_disco,
    "EDU_disced": load_disced,
    "SOC_ger7": load_ger7,
}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def load_master():
    master = {}
    categories = set()
    with open(ROOT / "MASTER_CATEGORY_MAPPINGS.csv", newline="") as f:
        for r in csv.DictReader(f):
            master[r["code"]] = r
            categories.add(r["category"])
    # longest first so e.g. LAB_disco08 wins over LAB_disco
    return master, sorted(categories, key=len, reverse=True)


def detect_category(code, categories):
    for cat in categories:
        if code.startswith(cat + "_") or code == cat:
            return cat, code[len(cat) + 1:]
    return "", ""


def resolve(code, master, categories, ref_cache):
    """Return dict(category, value, da, en, da_source, en_source, match, match_key)."""
    norm = code[:-2] if code.endswith(".0") else code
    row = master.get(norm)
    if row:
        return {
            "category": row["category"],
            "value": row["value"],
            "description_da": row["description_da"],
            "description_en": row["description_en"],
            "da_source": "master",
            "en_source": "master:" + (row["description_en_source"] or "?"),
            "match": "exact" if norm == code else "exact (.0-normalised)",
            "match_key": norm,
        }
    cat, value = detect_category(norm, categories)
    out = {
        "category": cat, "value": value,
        "description_da": "", "description_en": "",
        "da_source": "", "en_source": "",
        "match": "not_found" if cat else "unknown_category",
        "match_key": "",
    }
    if cat not in REF_LOADERS:
        return out
    if cat not in ref_cache:
        ref_cache[cat] = REF_LOADERS[cat]()
    refs = ref_cache[cat]
    keys = []
    # each language takes its first hit across its ordered source list
    # (tier-1 dict before raw reference); da and en may match the same level
    # under different keys (db07 '1' vs NACE '01')
    for lang in ("da", "en"):
        hit = next(((table[key], src, key)
                    for key in refs["cand"](value)
                    for table, src in refs[lang]
                    if key in table), None)
        if hit:
            out["description_" + lang], src, key = hit
            out[lang + "_source"] = f"{src} @{key}"
            keys.append(key)
    if keys:
        out["match"] = "reference"
        out["match_key"] = keys[0] if len(set(keys)) == 1 else "|".join(keys)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vocab", help="path to a vocab JSON ({code: token_id})")
    ap.add_argument("-o", "--out", help="output CSV (default: <vocab>_descriptions.csv)")
    ap.add_argument("--json", dest="json_out", help="also write a {code: description} JSON")
    ap.add_argument("--lang", choices=["da", "en", "both"], default="both",
                    help="language for the --json output (CSV always has both)")
    args = ap.parse_args()

    vocab = json.load(open(args.vocab))
    master, categories = load_master()
    ref_cache = {}

    results = []
    for code, token_id in vocab.items():
        r = resolve(str(code), master, categories, ref_cache)
        r = {"code": code, "token_id": token_id, **r}
        results.append(r)

    out_path = args.out or str(Path(args.vocab).with_suffix("")) + "_descriptions.csv"
    cols = ["code", "token_id", "category", "value", "description_da",
            "description_en", "da_source", "en_source", "match", "match_key"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(results)

    if args.json_out:
        if args.lang == "both":
            payload = {r["code"]: {"da": r["description_da"], "en": r["description_en"]}
                       for r in results}
        else:
            key = "description_" + args.lang
            payload = {r["code"]: r[key] for r in results}
        with open(args.json_out, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)

    # summary
    from collections import Counter
    by_match = Counter(r["match"] for r in results)
    print(f"{len(results)} codes -> {out_path}")
    for m, n in by_match.most_common():
        print(f"  {m}: {n}")
    misses = Counter(r["category"] or "(unknown)" for r in results
                     if r["match"] in ("not_found", "unknown_category"))
    if misses:
        print("unresolved by category:",
              ", ".join(f"{c}={n}" for c, n in misses.most_common(10)))


if __name__ == "__main__":
    main()
