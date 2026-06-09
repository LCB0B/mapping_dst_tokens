#!/usr/bin/env python3
"""Generate SOURCE_CATALOG.csv — a machine-readable provenance catalog.

For every category (prefix_variable) this aggregates, deterministically from
MASTER_CATEGORY_MAPPINGS.csv and the on-disk source files:
  - code count and description coverage (en / da / official)
  - the dominant provenance tags actually present in the data
    (`source`, `description_en_source`, `description_en_official_source`)
  - the matching source file(s) in raw/ and lookup_dictionaries/
  - the international standard used for official English (when any)

It then joins a curated category -> DST `REGISTER:VARIABLE` map that is sourced
*verbatim* from input_dataset_description.csv (the authoritative provenance
document). Per the repo HARD RULES, the register field is left blank for the
handful of categories whose individual register variable is not documented
there (created indicators, ambiguous manual bins) rather than guessed.

Run from the repo root:  python3 scripts/build_source_catalog.py
"""
import csv
import glob
import os
from collections import Counter, defaultdict

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
OUT = "SOURCE_CATALOG.csv"

# --- Curated category -> DST register:variable, sourced from
# --- input_dataset_description.csv. Blank where not individually documented.
DST_REGISTER = {
    # DEM ---------------------------------------------------------------
    "DEM_birthyear": "LIFELINES:FOED_DAG",
    "DEM_birthmonth": "LIFELINES:FOED_DAG",
    "DEM_female": "LIFELINES:KOEN",
    "DEM_opr": "BEF:OPR_LAND",
    "DEM_ie": "BEF:IE_TYPE",
    "DEM_statsb": "BEF:STATSB",
    "DEM_vaegt": "FERTILITETSDATABASEN:VAEGT_BARN",
    "DEM_laengde": "FERTILITETSDATABASEN:LAENGDE_BARN",
    "DEM_far": "FERTILITETSDATABASEN:FAR_FOED_ADOP",
    "DEM_mor": "FERTILITETSDATABASEN:MOR_FOED_ADOP",
    "DEM_civst": "BEF:CIVST",
    "DEM_familie": "BEF:FAMILIE_TYPE",
    "DEM_fm": "BEF:FM_MARK",
    "DEM_kom": "BEFADR:KOM",
    "DEM_relation": "FAMILY_RELATIONS:RELATION",
    "DEM_manual_bin_antboernf": "BEF:ANTBOERNF",
    "DEM_manual_bin_antpersf": "BEF:ANTPERSF",
    "DEM_manual_bin_antefam": "BEF:ANTEFAM",
    "DEM_Indvandret": "LIFELINES:EVENT_CAUSE_START",
    "DEM_Udvandret": "LIFELINES:EVENT_CAUSE_FINAL",
    "DEM_Birth": "FAMILY_RELATIONS:RELATION",
    "DEM_Death": "FAMILY_RELATIONS:RELATION",
    # EDU ---------------------------------------------------------------
    "EDU_grade": "UDFK:GRUNDSKOLEKARAKTER / UDGK:KARAKTER",
    "EDU_course": "UDFK:GRUNDSKOLEFAG / UDGK:FAG_TXT",
    "EDU_ects": "UDD_KARAKTER_UNIVID_FAG:ECTS",
    "EDU_field": "DISCED-15 (KOTRE:UDD / KOTRE:AUDD)",
    "EDU_disced": "DISCED-15 (KOTRE:UDD / KOTRE:AUDD)",
    "EDU_udd": "KOTRE:UDD",
    "EDU_udel": "KOTRE:UDEL",
    "EDU_tilg": "KOTRE:TILG_ART",
    "EDU_afg": "KOTRE:AFG_ART",
    "EDU_audd": "KOTRE:AUDD / UDG:AUDD / UDKV:AUDD",
    "EDU_wellbeing": "UDD_TRIVSEL_SMAA_KLASSER / UDD_TRIVSEL_STORE_KLASSER",
    "EDU_dnt": "UDD_NATTEST_OPRINDELIGE:FAG / UDD_NATTEST_GENBEREGNEDE:FAG",
    "EDU_dageaktiv": "UDD_FOLKESKOLE_FRAVAER_STIL:DAGEAKTIV",
    "EDU_dageialtfra": "UDD_FOLKESKOLE_FRAVAER_STIL:DAGEIALTFRA",
    "EDU_dagelovfra": "UDD_FOLKESKOLE_FRAVAER_STIL:DAGELOVFRA",
    "EDU_dagesyg": "UDD_FOLKESKOLE_FRAVAER_STIL:DAGESYG",
    "EDU_dageulovfra": "UDD_FOLKESKOLE_FRAVAER_STIL:DAGEULOVFRA",
    # HEA ---------------------------------------------------------------
    "HEA_ICD10": "LPR_ADM:AKTIONSDIAGNOSE",
    "HEA_atc": "LMDB:ATC",
    "HEA_speciale": "SYSI:SPECIALE / SSSY:SPECIALE",
    "HEA_urgency": "LPR_ADM:INDM",
    "HEA_patienttype": "LPR_ADM:PATTYPE",
    # LMDB VOLUME/VOLTYPECODE unit categories
    **{f"HEA_{u}": "LMDB:VOLUME + LMDB:VOLTYPECODE" for u in
       ["", "DDK", "DW", "DWG", "DWK", "GA", "GI", "GP", "L", "MG", "ML", "PK", "ST", "TU"]},
    # LAB ---------------------------------------------------------------
    "LAB_disco": "AKM:DISCO_ALLE_INDK_13 (DISCO 2-digit)",
    "LAB_disco08": "AKM:DISCO08_* / AMRUN:DISCO_KODE",
    "LAB_db07": "AKM:NACE_DB07_13 / AMRUN:ARB_HOVED_BRA_DB07",
    "LAB_nace": "AKM:NACE_13 (DB93)",
    "LAB_branche": "AKM:BRANCHE_77",
    "LAB_socio13": "AKM:SOCIO13",
    "LAB_socio": "AKM:SOCIO_GL",
    "LAB_soc": "AMRUN:SOC_STATUS_KODE",
    "LAB_tilstand": "AMRUN:TILSTAND_KODE_AMR",
    "LAB_fravaer": "AMRUN:FRAVAER_BESK_KODE",
    "LAB_stoette": "AMRUN:STOETTE_BESK_KODE",
    "LAB_bredt": "AMRUN:BREDT_LOEN_BELOEB",
    "LAB_udd": "AMRUN:UDD_BESK_KODE",
    # IND income/tax/wealth bins
    "LAB_dispon": "IND:DISPON_13",
    "LAB_perindkialt": "IND:PERINDKIALT_13",
    "LAB_erhvervsindk": "IND:ERHVERVSINDK_13",
    "LAB_loenmv": "IND:LOENMV_13",
    "LAB_honny": "IND:HONNY",
    "LAB_netovskud": "IND:NETOVSKUD_13",
    "LAB_off": "IND:OFF_OVERFORSEL_13",
    "LAB_dagpenge": "IND:DAGPENGE_KONTANT_13",
    "LAB_arblhumv": "IND:ARBLHUMV",
    "LAB_ovrig": "IND:OVRIG_DAGPENGE_AKAS_13 / OVRIG_KONTANTHJALP_13 / OVRIG_OVERFORSEL_13",
    "LAB_kontanthj": "IND:KONTANTHJ_13",
    "LAB_syg": "IND:SYG_BARSEL_13",
    "LAB_stip": "IND:STIP",
    "LAB_korstoett": "IND:KORSTOETT",
    "LAB_korydial": "IND:KORYDIAL",
    "LAB_gron": "IND:GRON_CHECK",
    "LAB_offpens": "IND:OFFPENS_EFTERLON_13",
    "LAB_folkefortid": "IND:FOLKEFORTID_13",
    "LAB_qeftlon": "IND:QEFTLON",
    "LAB_privat": "IND:PRIVAT_PENSION_13",
    "LAB_formueindk": "IND:FORMUEINDK_BRUTTO",
    "LAB_resuink": "IND:RESUINK_13",
    "LAB_lejev": "IND:LEJEV_EGEN_BOLIG",
    "LAB_rentudgpr": "IND:RENTUDGPR",
    "LAB_skatmvialt": "IND:SKATMVIALT_13",
    "LAB_underhol": "IND:UNDERHOL",
    "LAB_assets": "IND:FORMREST + IND:FORMREST_NY05",
    "LAB_akm": "AKM (employment-type indicator)",
    # SOC ---------------------------------------------------------------
    "SOC_ger7": "KRAF/KRKO/KRMS/KRSI/KROF/KRIN :*_GER7",
    "SOC_afgtypko": "KRAF:AFG_AFGTYPKO / KRKO:KON_AFGTYPKO",
    "SOC_ubstrflg": "KRAF:AFG_UBSTRFLG",
    "SOC_boedeblb": "KRAF:AFG_BOEDEBLB",
    "SOC_dagboant": "KRAF:AFG_DAGBOANT",
    "SOC_dagbobel": "KRAF:AFG_DAGBOBEL",
    "SOC_bstrflgd": "KRAF:AFG_BSTRFLG",
    "SOC_betbkod": "KRAF:AFG_BETBKOD",
    "SOC_frakkod": "KRAF:AFG_FRAKKOD",
    "SOC_revoke": "KRAF:AFG_FRAKAAR + AFG_FRAKMND",
    "SOC_frakbkod": "KRAF:AFG_FRAKBKOD",
    "SOC_fgslkod": "KRIN:IND_FGSLKOD",
    "SOC_overfkod": "KRIN:IND_OVERFKOD",
    "SOC_bstrfkod": "KRIN:IND_BSTRFKOD",
    "SOC_loeslkod": "KRIN:IND_LOESLKOD",
    "SOC_samtykke": "BUAF:SAMTYKKE",
    "SOC_ansted": "BUAF:ANSTED_KLAS",
    "SOC_haendelse": "BUAF:HAENDELSE",
    "SOC_pgf": "BUFO:PFG",
    # SPECIAL -----------------------------------------------------------
    "special_tokens": "(model tokens — not register-derived)",
}

# Extra notes for special provenance situations (HARD-RULES context).
NOTES = {
    "LAB_socio": "1976-1990 SOCIO_GL recovered via empirical SOCIO13 crosswalk (crosswalks/empirical/); 2 codes unresolved",
    "LAB_db07": "5-digit low-division codes partly recovered via empirical DB93 firm crosswalk; 19 unresolved",
    "LAB_nace": "Danish DB93 (raw/LAB_nace.txt); official English only where a NACE Rev.2 crosswalk exists",
    "HEA_speciale": "6-digit specialty+procedure billing codes; regional 2-aftaler; English re-translated (opus-4-8-medical)",
    "special_tokens": "[PAD] [CLS] [SEP] [UNK] [MASK]",
}
for u in ["", "DDK", "DW", "DWG", "DWK", "GA", "GI", "GP", "L", "MG", "ML", "PK", "ST", "TU"]:
    NOTES[f"HEA_{u}"] = "LMDB VOLTYPECODE unit + binned VOLUME ranges (NOT procedure codes)"


def dom(rows, col):
    c = Counter((r.get(col) or "").strip() for r in rows)
    c.pop("", None)
    return c.most_common(1)[0][0] if c else ""


def find_source_files(category):
    """Return (lookup_dict_files, raw_files) actually present on disk."""
    ld = set()
    for pat in (f"lookup_dictionaries/{category}_dict*",
                f"lookup_dictionaries/{category}_quantile_dict*"):
        ld.update(os.path.basename(p) for p in glob.glob(pat))
    rawf = set()
    for p in glob.glob(f"raw/{category}*"):
        if not p.lower().endswith(".pdf"):
            rawf.update([os.path.basename(p)])
    return sorted(ld), sorted(rawf)


def main():
    rows = list(csv.DictReader(open(MASTER, newline="", encoding="utf-8")))
    cats = defaultdict(list)
    for r in rows:
        cats[(r["prefix"], r["variable"], r["category"])].append(r)

    out_rows = []
    for (prefix, variable, category), rs in sorted(cats.items()):
        n = len(rs)
        en = sum(1 for r in rs if (r.get("description_en") or "").strip())
        da = sum(1 for r in rs if (r.get("description_da") or "").strip())
        off = sum(1 for r in rs if (r.get("description_en_official") or "").strip())
        ld, rawf = find_source_files(category)
        out_rows.append({
            "prefix": prefix,
            "variable": variable,
            "category": category,
            "n_codes": n,
            "dst_register": DST_REGISTER.get(category, ""),
            "source_tag": dom(rs, "source"),
            "lookup_dict": "; ".join(ld),
            "raw_source": "; ".join(rawf),
            "intl_standard": dom(rs, "description_en_official_source"),
            "en_coverage_pct": round(100 * en / n),
            "da_coverage_pct": round(100 * da / n),
            "official_coverage_pct": round(100 * off / n),
            "dominant_confidence": dom(rs, "confidence_level"),
            "notes": NOTES.get(category, ""),
        })

    fields = ["prefix", "variable", "category", "n_codes", "dst_register",
              "source_tag", "lookup_dict", "raw_source", "intl_standard",
              "en_coverage_pct", "da_coverage_pct", "official_coverage_pct",
              "dominant_confidence", "notes"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    mapped = sum(1 for r in out_rows if r["dst_register"])
    print(f"Wrote {OUT} with {len(out_rows)} categories")
    print(f"  dst_register filled: {mapped}/{len(out_rows)}")
    print(f"  with a lookup dict:  {sum(1 for r in out_rows if r['lookup_dict'])}")
    print(f"  with a raw source:   {sum(1 for r in out_rows if r['raw_source'])}")


if __name__ == "__main__":
    main()
