#!/usr/bin/env python3
"""Batch (a): resolve weak-source categories from in-repo sources (KRIN codebook + raw files).

Per input_dataset_description.csv:
  SOC_loeslkod  = KRIN:IND_LOESLKOD   -> upgrade bad-MT Danish from the downloaded codebook
  LAB_stoette   = AMRUN:STOETTE_BESK_KODE -> raw/LAB_stoette_besk_kode_nullified.txt
  LAB_fravaer   = AMRUN:FRAVAER_BESK_KODE -> raw/LAB_fravaer_besk_kode_nullified.txt
  EDU_afg       = KOTRE:AFG_ART       -> mapping/lookup_dictionaries/EDU_afg_art_dict.csv

(DEM_far/DEM_mor weak codes 1/2/99/unknown are NOT in the FTDB value set -> left as-is, not
invented. EDU_tilg/KOTRE:TILG_ART deferred to the DST-fetch batch.)

Re-runnable. Usage: python3 scripts/fix_inrepo_batch_a.py [--dry-run]
"""
import argparse, csv, json

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
CODEBOOK = "/tmp/claude-270889/-home-louibo-mappings/023a0e03-d690-4ba1-a3d5-ca2184b0b2d3/tasks/wetm5a9gs.output"

LOESL_EN = {
    "0": "Unknown",
    "1": "Released by the judge at the constitutional hearing (grundlovsforhør)",
    "2": "Released by police within 24 hours without a constitutional hearing",
    "3": "Released by police after upheld arrest, without re-presentation at a constitutional hearing",
    "4": "Released after pre-trial detention",
    "5": "Directly to serving sentence after constitutional hearing (imprisoned / time-limit extended)",
    "6": "Measure revoked",
    "7": "Detention upheld",
    "8": "Released after administrative detention",
    "9": "Released after being held back (tilbageholdelse)",
    "10": "Released on parole on stricter terms",
}
# LAB_stoette: value besk_kode_nullified_N -> code N in raw/LAB_stoette_besk_kode_nullified.txt
STOETTE = {
    "1": ("Ansættelse med løntilskud", "Employment with wage subsidy"),
    "2": ("Jobrotation", "Job rotation"),
    "3": ("Fleksjob", "Flex job"),
    "4": ("Skånejob", "Skånejob (sheltered job)"),
    "5": ("Servicejob", "Service job"),
    "6": ("Voksenlærling", "Adult apprentice"),
    "7": ("Revalidering", "Rehabilitation (revalidering)"),
}
FRAVAER = {
    "1": ("Orlov til børnepasning", "Childcare leave"),
    "2": ("Fravær pga. sygdom", "Absence due to illness"),
    "3": ("Fravær pga. barsel", "Absence due to maternity/parental leave"),
    "4": ("Imputeret job ved kortvarigt fravær", "Imputed job (short-term absence)"),
}
EDU_AFG_EN = {
    "art_1": "Education exit",
    "art_2": "Education pause, continues at the same institution",
    "art_3": "Education pause, continues at a different institution",
    "art_4": "In progress",
}


def load_loeslkod_da():
    data = json.load(open(CODEBOOK, encoding="utf-8"))
    for v in data["result"]["codebook"]:
        if v["variable"] == "IND_LOESLKOD":
            return {kv["code"]: kv["text"] for kv in (v.get("values") or [])}
    return {}


def load_afg_dict():
    d = {}
    for r in csv.DictReader(open("mapping/lookup_dictionaries/EDU_afg_art_dict.csv", encoding="utf-8")):
        d[r["code"].replace("EDU_", "")] = r["description"]  # key e.g. afg_art_1
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    loesl_da = load_loeslkod_da()
    afg_dict = load_afg_dict()

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    c = {"SOC_loeslkod": 0, "LAB_stoette": 0, "LAB_fravaer": 0, "EDU_afg": 0}
    for r in rows:
        cat = r.get("category"); v = (r.get("value") or "").strip()
        if cat == "SOC_loeslkod" and v in loesl_da:
            da = loesl_da[v]; en = LOESL_EN.get(v, da)
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_ind_loeslkod"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["SOC_loeslkod"] += 1
        elif cat == "LAB_stoette" and v.startswith("besk_kode_nullified_") and v.split("_")[-1] in STOETTE:
            da, en = STOETTE[v.split("_")[-1]]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "raw_lab_stoette"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["LAB_stoette"] += 1
        elif cat == "LAB_fravaer" and v.startswith("besk_kode_nullified_") and v.split("_")[-1] in FRAVAER:
            da, en = FRAVAER[v.split("_")[-1]]
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "raw_lab_fravaer"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; c["LAB_fravaer"] += 1
        elif cat == "EDU_afg" and (r.get("source") or "").startswith("none|generated"):
            key = f"afg_{v}"  # value art_1 -> dict key afg_art_1
            if key in afg_dict:
                da = afg_dict[key]; en = EDU_AFG_EN.get(v, da)
                r["description"] = da; r["description_da"] = da; r["description_en"] = en
                r["source"] = "CSV:EDU_afg_art"; r["description_en_source"] = "translated"
                r["confidence_level"] = "high"; c["EDU_afg"] += 1

    print("updated:", c, "total", sum(c.values()))
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
