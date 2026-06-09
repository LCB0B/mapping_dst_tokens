#!/usr/bin/env python3
"""Batch (b): apply the DST value sets fetched by the dst-valuesets workflow.

Per input_dataset_description.csv + fetched DST TIMES value sets:
  DEM_ie         = BEF:IE_TYPE        -> HALLUCINATED as migration events; it is herkomst
                                         (origin: dansk/indvandrer/efterkommer/uoplyst). FIX.
  HEA_urgency    = LPR_ADM:INDM       -> 1=Akut, 2=Ikke-akut (only these two are in the value
                                         set; 9/ATA* are not -> left untouched).
  DEM_relation   = FAMILY_RELATIONS:RELATION -> labels already correct (derived categories) -> re-tag.
  EDU_tilg       = KOTRE:TILG_ART     -> labels match the value set verbatim -> re-tag.
  HEA_patienttype= LPR_ADM:PATTYPE    -> labels correct -> re-tag (+ align code 0 Danish).

Not resolvable from public DST (left unresolved, NOT guessed):
  LAB_tilstand  (AMRUN:TILSTAND_KODE_AMR — no published værdisæt)
  LAB_socio gl_* (AKM:SOCIO_GL — no published værdisæt)
LAB_socio13 (AKM:SOCIO13) is already fully sourced/correct — untouched.

Re-runnable. Usage: python3 scripts/fix_dst_fetch_batch_b.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

# DEM_ie: BEF:IE_TYPE (herkomst). vocab token_N -> IE_TYPE code.
IE = {
    "type_1": ("Personer med dansk oprindelse", "Persons of Danish origin"),
    "type_2": ("Indvandrere", "Immigrants"),
    "type_3": ("Efterkommere", "Descendants (of immigrants)"),
    "type_unknown": ("Uoplyst", "Unknown"),
}
# HEA_urgency: LPR_ADM:INDM (Indlæggelsesmåde). Only 1 and 2 are in the value set.
INDM = {
    "1": ("Akut", "Acute admission (akut)"),
    "2": ("Ikke-akut", "Non-acute admission (ikke-akut)"),
}
# HEA_patienttype: LPR_ADM:PATTYPE — align Danish to official, keep meanings.
PATTYPE = {
    "0": ("Heldøgnspatient", "Inpatient (full-day / overnight)"),
    "1": ("Deldøgnspatient", "Part-day patient (discontinued 2002)"),
    "2": ("Ambulant patient", "Outpatient (ambulatory; from 2014 also acute/ER)"),
    "3": ("Skadestuepatient", "Emergency-room patient (discontinued 2014)"),
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    c = {"DEM_ie": 0, "HEA_urgency": 0, "HEA_patienttype": 0, "DEM_relation": 0, "EDU_tilg": 0}
    for r in rows:
        cat = r.get("category"); v = (r.get("value") or "").strip()
        if cat == "DEM_ie" and v in IE:
            da, en = IE[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_bef_ie_type"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["DEM_ie"] += 1
        elif cat == "HEA_urgency" and v in INDM:
            da, en = INDM[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_lpr_indm"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["HEA_urgency"] += 1
        elif cat == "HEA_patienttype" and v in PATTYPE:
            da, en = PATTYPE[v]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_lpr_pattype"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["HEA_patienttype"] += 1
        elif cat == "DEM_relation" and (r.get("source") or "").startswith("none|generated"):
            # labels (Barn/Forælder/Helsøskende/Halvsøskende/Søskende ukendt) already correct
            r["source"] = "dst_family_relations_relation"; r["confidence_level"] = "high"
            c["DEM_relation"] += 1
        elif cat == "EDU_tilg" and (r.get("source") or "").startswith("none|generated"):
            # labels match KOTRE:TILG_ART value set verbatim
            r["source"] = "dst_kotre_tilg_art"; r["confidence_level"] = "high"
            c["EDU_tilg"] += 1

    print("updated:", c, "total", sum(c.values()))
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
