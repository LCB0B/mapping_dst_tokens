#!/usr/bin/env python3
"""Audit description_en quality across all 40,465 MASTER rows.

Per-row flags:
  F1  empty
  F2  mojibake / control characters (U+0080–U+009F, \\x00–\\x1F)
  F3  Danish characters (æøåÆØÅ) leaking through in non-proper-noun context
  F4  identical to description_da when we have a real Danish description
      (should differ, unless DA is Latin/English/proper noun)
  F5  suspiciously short vs long DA (ratio < 0.3 with DA > 10 chars)
  F6  suspiciously long vs short DA (ratio > 3.5 with DA > 10 chars)
  F7  numbers in DA missing from EN (large-number preservation)
  F8  repetitive garbled output (same word ≥ 40% of words when > 8 words)
  F9  contains a placeholder phrase ("not documented", "not found",
      "no text available")
  F10 disagreement with description_en_official (when official is set and
      en differs significantly)

Writes a per-row report to translation_en_audit.csv and a per-category
summary.

Usage:
    python3 scripts/audit_description_en.py [--report N]  # show top N samples per flag
"""
import argparse
import csv
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
REPORT_PATH = "translation_en_audit.csv"

DANISH_CHARS = re.compile(r"[æøåÆØÅ]")
MOJIBAKE = re.compile(r"[\x00-\x1f\x80-\x9f]|Ã\x98|¾|¿")
PLACEHOLDER = re.compile(
    r"not documented|not found|no text available|ingen tekst|service code",
    re.I,
)

# Category-specific allow-lists for Danish chars in EN (legitimate proper nouns)
ALLOW_DANISH_CHARS_IN_EN = {
    "DEM_kom",        # Danish municipality names (Copenhagen = København, etc.)
    "DEM_opr",        # country-of-origin legacy entries
    "DEM_statsb",     # citizenship — some retained as Danish names
    "EDU_course",     # some Danish school-subject names
    "EDU_fag",        # school subjects with Danish chars
    "HEA_speciale",   # contains Danish place names (Sejrø, Ørelæge service), already translated
    "HEA_ICD10",      # legitimate cases like "Leptospirosis (Sejrø, Saxkøbing)"
    "EDU_audd", "EDU_udd",  # Danish degree abbreviations like "cand.mag."
    "SOC_ger7",       # partial-translated Danish offense codes
}


def normalize(s):
    s = re.sub(r"\s+", " ", s.lower().strip())
    s = re.sub(r"[.,;:!?]+", "", s)
    return s


def is_repetitive(text):
    words = text.split()
    if len(words) < 9:
        return False
    c = Counter(words)
    most = c.most_common(1)[0][1]
    return most >= len(words) * 0.4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=int, default=5, help="show N samples per flag")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    flags = defaultdict(list)     # flag → list of (code, category, da, en, detail)
    cat_flag_counts = defaultdict(lambda: Counter())
    total_by_cat = Counter()

    for r in rows:
        cat = r["category"]
        code = r["code"]
        da = r["description_da"].strip()
        en = r["description_en"].strip()
        en_official = r.get("description_en_official", "").strip()
        total_by_cat[cat] += 1

        # F1 — empty
        if not en:
            flags["F1_empty"].append((code, cat, da, en, ""))
            cat_flag_counts[cat]["F1_empty"] += 1
            continue  # other flags moot if empty

        # F2 — mojibake
        if MOJIBAKE.search(en):
            flags["F2_mojibake"].append((code, cat, da, en, ""))
            cat_flag_counts[cat]["F2_mojibake"] += 1

        # F3 — Danish chars leaking
        if DANISH_CHARS.search(en) and cat not in ALLOW_DANISH_CHARS_IN_EN:
            leaked_words = [w for w in en.split() if DANISH_CHARS.search(w)]
            flags["F3_danish_leak"].append((code, cat, da, en, str(leaked_words[:3])))
            cat_flag_counts[cat]["F3_danish_leak"] += 1

        # F4 — en identical to da when da is Danish
        if da and normalize(en) == normalize(da) and DANISH_CHARS.search(da):
            flags["F4_da_copy"].append((code, cat, da, en, ""))
            cat_flag_counts[cat]["F4_da_copy"] += 1

        # F5/F6 — length ratio
        if da and len(da) > 10:
            ratio = len(en) / len(da)
            if ratio < 0.3:
                flags["F5_too_short"].append((code, cat, da, en, f"ratio={ratio:.2f}"))
                cat_flag_counts[cat]["F5_too_short"] += 1
            elif ratio > 3.5:
                flags["F6_too_long"].append((code, cat, da, en, f"ratio={ratio:.2f}"))
                cat_flag_counts[cat]["F6_too_long"] += 1

        # F7 — number preservation (only flag missing 2+ digit numbers)
        da_nums = set(re.findall(r"\d{2,}", da))
        en_nums = set(re.findall(r"\d{2,}", en))
        missing = da_nums - en_nums
        if missing:
            flags["F7_missing_nums"].append(
                (code, cat, da, en, f"missing={sorted(missing)}")
            )
            cat_flag_counts[cat]["F7_missing_nums"] += 1

        # F8 — repetitive
        if is_repetitive(en):
            flags["F8_repetitive"].append((code, cat, da, en, ""))
            cat_flag_counts[cat]["F8_repetitive"] += 1

        # F9 — placeholder text in EN
        if PLACEHOLDER.search(en) and not PLACEHOLDER.search(da):
            flags["F9_placeholder"].append((code, cat, da, en, ""))
            cat_flag_counts[cat]["F9_placeholder"] += 1

        # F10 — major divergence from official EN when both set
        if en_official and en != en_official:
            ratio = SequenceMatcher(None, normalize(en), normalize(en_official)).ratio()
            if ratio < 0.5:
                flags["F10_diverge_official"].append(
                    (code, cat, da, en, f"official={en_official[:50]!r}  r={ratio:.2f}")
                )
                cat_flag_counts[cat]["F10_diverge_official"] += 1

    # Report
    total = len(rows)
    print("=" * 78)
    print(f"description_en audit — {total} rows")
    print("=" * 78)
    print()
    total_flagged = 0
    for flag_name in sorted(flags):
        n = len(flags[flag_name])
        total_flagged += n
        print(f"  {flag_name:<25s} {n}  ({n/total*100:.2f}%)")
    print(f"  {'ANY flag raised':<25s} {len(set(f[0] for lst in flags.values() for f in lst))}")
    print()

    # Per-category breakdown for common flags
    print("Top flagged categories:")
    cat_total = Counter()
    for cat, fcount in cat_flag_counts.items():
        cat_total[cat] = sum(fcount.values())
    for cat, n in cat_total.most_common(15):
        breakdown = ", ".join(
            f"{f[3:]}:{v}" for f, v in cat_flag_counts[cat].most_common(5)
        )
        print(f"  {cat:<18s} total={n:<5} rows={total_by_cat[cat]:<6} | {breakdown}")

    # Sample per flag
    print()
    for flag_name in sorted(flags):
        samples = flags[flag_name][: args.report]
        if not samples:
            continue
        print(f"\n--- {flag_name} samples (showing {len(samples)} of {len(flags[flag_name])}) ---")
        for code, cat, da, en, detail in samples:
            print(f"  {code:<35s} [{cat}]")
            print(f"    DA: {da[:70]!r}")
            print(f"    EN: {en[:70]!r}")
            if detail:
                print(f"    detail: {detail}")

    # Write CSV report
    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["flag", "code", "category", "description_da", "description_en", "detail"])
        for flag_name, items in sorted(flags.items()):
            for code, cat, da, en, detail in items:
                w.writerow([flag_name, code, cat, da, en, detail])
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
