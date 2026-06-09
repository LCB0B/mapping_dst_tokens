#!/usr/bin/env python3
"""QC gate for HEA_speciale translations: detect id-misassignment.

Every opus-4-8-medical English string must begin with the SAME specialty as
its row (the specialty is fixed by the code prefix). A first-word mismatch
means a translation was applied to the wrong row (an agent returned a wrong id).
Exits non-zero if any mismatch is found.

Usage: python3 scripts/validate_hea_speciale.py
"""
import csv, re, sys

def fw(s):
    m = re.search(r"[a-zæøå]+", s.lower())
    return m.group(0) if m else ""

def main():
    rows = [r for r in csv.DictReader(open("MASTER_CATEGORY_MAPPINGS.csv"))
            if r["category"] == "HEA_speciale"]
    bad = []
    for r in rows:
        if (r.get("description_en_source") or "").strip() != "opus-4-8-medical":
            continue
        da = (r.get("description") or r.get("description_da") or "")
        # the authoritative specialty English lives in description_en_official
        spec = (r.get("description_en_official") or "").strip()
        en = (r.get("description_en") or "").strip()
        if not spec or not en:
            continue
        if fw(en) != fw(spec):
            bad.append((r["code"], spec, en[:60]))
    print(f"checked {len(rows)} HEA_speciale rows | specialty mismatches: {len(bad)}")
    for c, spec, en in bad[:20]:
        print(f"  {c}: official=[{spec}] but en=[{en}]")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
