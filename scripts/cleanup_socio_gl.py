#!/usr/bin/env python3
"""Replace my LLM-hallucinated SOCIO_gl mappings with only the entries I can
verify from Danmarks Statistik's PSTILL / ARBSTIL nomenclature documentation.

Sources consulted:
  - DST Times: https://www.dst.dk/da/Statistik/dokumentation/Times/ida-databasen/ida-personer/pstill
  - DST Times: https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-arbejdsmarked/arbstil
  - DST nomenclature: Socioøkonomisk status (SOCSTIL_KODE), v1:1996
  - DST SOCIO 1997 publication (raw/dst_socio_1997.pdf)
  - Aarhus Univ. IDAP doc: https://lmdg.econ.au.dk/web_datasets/idap_vde.pdf

Certain mappings (PSTILL / ARBSTIL two-digit codes that appear literally in
DST documentation).

Uncertain `gl_*` values (no documented counterpart in DST PSTILL/ARBSTIL) get
a generic placeholder and confidence_level=low, so downstream consumers know
not to trust them.
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# ── Verified PSTILL / ARBSTIL two-digit codes from DST ──────────────────────
# (code_value_without_prefix → (description_da, description_en))
VERIFIED = {
    # Self-employed (PSTILL 11-19)
    "gl_11": ("Arbejdsgiver", "Employer"),
    "gl_12": ("Momsbetaler", "VAT-registered self-employed"),
    "gl_19": ("Anden selvstændig uden ansatte",
              "Other self-employed without employees"),
    "gl_20": ("Medhjælpende ægtefælle", "Assisting spouse"),
    # Wage earners — ARBSTIL (1980-1995) used 30-39; labels below are the
    # pre-1996 versions (Direktør, Overordnet funktionær, etc.) per PSTILL doc.
    "gl_31": ("Direktør (1980-1995) / Topleder (1996+)",
              "Director (1980-1995) / Top manager (1996+)"),
    "gl_32": ("Overordnet funktionær (1980-1995) / Lønmodtager på højeste niveau (1996+)",
              "Senior white-collar employee (1980-1995) / Highest-level employee (1996+)"),
    "gl_33": ("Ledende funktionær (1980-1995) / Funktionær i øvrigt",
              "Managerial white-collar employee (1980-1995) / Other white-collar"),
    "gl_39": ("Lønmodtager uden nærmere angivelse",
              "Wage earner, not further specified"),
    # Unemployment
    "gl_40": ("Arbejdsløs (fuldt ledige i uge 48)",
              "Unemployed (fully unemployed in week 48)"),
    "gl_41": ("Orlov fra ledighed", "On leave from unemployment"),
    "gl_42": ("Barselsdagpenge", "Maternity benefit"),
    "gl_43": ("Sygedagpenge", "Sickness benefit"),
    "gl_49": ("Revalidering", "Vocational rehabilitation"),
    # Out of labour force
    "gl_50": ("Efterlønsmodtager", "Early-retirement benefit (efterløn) recipient"),
    "gl_51": ("Aktivering (ifølge kontanthjælpsregisteret)",
              "Activation (per social-assistance register)"),
    "gl_52": ("Ledighedsydelse", "Unemployment allowance"),
    "gl_53": ("Efterlønsmodtagere mv. (SOCIO kode 323)",
              "Early-retirement benefit recipients etc. (SOCIO code 323)"),
}

# Codes that appear in MASTER but have no documented DST counterpart. We leave
# descriptions empty and mark confidence=low so they're visible as unresolved.
UNRESOLVED = {
    "gl_1", "gl_2", "gl_3", "gl_4", "gl_5", "gl_6", "gl_7", "gl_8", "gl_9",
    "gl_10",
    "gl_21", "gl_22", "gl_23", "gl_25", "gl_26", "gl_27", "gl_28", "gl_29",
    "gl_30",
    "gl_59",
    "gl_60", "gl_61", "gl_62", "gl_63", "gl_69",
    "gl_70", "gl_71", "gl_72", "gl_73", "gl_79",
    "gl_80", "gl_81", "gl_82", "gl_89",
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    stats = {"verified": 0, "cleared": 0}

    for r in rows:
        if r["category"] != "LAB_socio":
            continue
        v = r["value"]
        if v in VERIFIED:
            da, en = VERIFIED[v]
            r["description_da"] = da
            r["description"] = da
            r["description_en"] = en
            r["description_short"] = en
            r["description_en_source"] = "dst_pstill"
            r["confidence_level"] = "high"
            stats["verified"] += 1
        elif v in UNRESOLVED:
            r["description_da"] = ""
            r["description"] = ""
            r["description_en"] = f"[Unresolved legacy SOCIO code: {v}]"
            r["description_short"] = f"Unresolved SOCIO code {v}"
            r["description_en_source"] = "unresolved"
            r["confidence_level"] = "low"
            stats["cleared"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in stats.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
