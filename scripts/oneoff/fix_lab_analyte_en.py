#!/usr/bin/env python3
"""Translate the HEA_speciale lab-analyte block (KPLL/SSI/regional) English from the
authoritative Danish. Translations were adversarially verified by a medical-Danish workflow
(dst-lab-verify): 31 confirmed as-is, 4 SSI ANA-panel rows where the verifier wanted to
expand the truncated parenthetical "(møn" -> "(pattern)" are instead kept CONSERVATIVE
(source is genuinely truncated, so we render the clear "in panel" and do not invent the
cut-off detail). Institution names + specimen/analyte prefixes (Pt-, P-, B-, F-, ;P, ;B) kept.

description_da (authoritative abbreviated billing text) is left unchanged. Confidence: medium
for fully-clean terms, low for the truncated/ambiguous ones (447001 HR-test, 486310/311/314/315).

Re-runnable. Usage: python3 scripts/fix_lab_analyte_en.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
EN = {
    "443150": "Copenhagen GP Laboratory (KPLL), special haematology",
    "445057": "Copenhagen GP Laboratory (KPLL), pea IgE (plasma)",
    "445073": "Copenhagen GP Laboratory (KPLL), brewer's yeast IgE (plasma)",
    "445513": "Copenhagen GP Laboratory (KPLL), precipitating antibody x 1 (plasma)",
    "445515": "Copenhagen GP Laboratory (KPLL), precipitating antibody x 2 (plasma)",
    "445516": "Copenhagen GP Laboratory (KPLL), precipitating antibody x 3 (plasma)",
    "445563": "Copenhagen GP Laboratory (KPLL), precipitating antibody x 4 (plasma)",
    "447001": "Copenhagen GP Laboratory (KPLL), HR-test, food (blood)",
    "449992": "Copenhagen GP Laboratory (KPLL), sample collection, own home",
    "449994": "Copenhagen GP Laboratory (KPLL), sample collection, nursing home",
    "457001": "Medical Laboratory, sample collection, 1 sample",
    "467154": "Regional laboratories, Pt-capillary bleeding time 10",
    "467167": "Regional laboratories, Pt-capillary resistance 10",
    "467171": "Regional laboratories, F-helminth eggs 16",
    "467177": "Regional laboratories, B-sedimentation reaction (ESR) 10",
    "467516": "Regional laboratories, Pt-EEG (sleep rhythm) 240",
    "467593": "Regional laboratories, Pt-urgent sample 70",
    "467595": "Regional laboratories, Pt-blood sampling 6",
    "467596": "Regional laboratories, Pt-forwarding of sample 4",
    "467635": "Regional laboratories, P-anti-nuclear antibodies",
    "481118": "Statens Serum Institut, ordinary bacteriological examination, wound secretion",
    "481119": "Statens Serum Institut, ordinary bacteriological examination, wound secretion",
    "481349": "Statens Serum Institut, yeast fungi",
    "482118": "Statens Serum Institut, striated muscle",
    "482203": "Statens Serum Institut, amniotic fluid examination",
    "482319": "Statens Serum Institut, estradiol",
    "482442": "Statens Serum Institut, haemochromatosis (HFE)",
    "483163": "Statens Serum Institut, urine sample kit, 10 pcs",
    "484101": "Statens Serum Institut, measles vaccine 1",
    "486168": "Statens Serum Institut, interferon-gamma detection, TB",
    "486305": "Statens Serum Institut, endomysium in coeliac disease",
    "486310": "Statens Serum Institut, ds-DNA in panel",
    "486311": "Statens Serum Institut, histone in panel",
    "486314": "Statens Serum Institut, ENA in panel (møn.8)",
    "486315": "Statens Serum Institut, SSA/SSB in panel",
    "486353": "Statens Serum Institut, coeliac tissue-typing test",
    "486360": "Statens Serum Institut, coeliac tissue-typing test",
}
LOW = {"447001", "486310", "486311", "486314", "486315"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    n = 0
    for r in rows:
        if r.get("category") != "HEA_speciale":
            continue
        v = (r.get("value") or "").strip()
        if v in EN:
            r["description_en"] = EN[v]
            r["description"] = EN[v]
            r["confidence_level"] = "low" if v in LOW else "medium"
            n += 1
    print(f"lab-analyte English updated: {n} rows (expect 37)")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
