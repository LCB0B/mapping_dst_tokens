#!/usr/bin/env python3
"""Fill missing descriptions for:

1. LAB_db07 5-digit aggregation codes (NACE Rev 2 4-digit groups written with
   a trailing zero in DST's DB07 groupering). 44 codes had empty DA.
2. LAB_socio `gl_*` codes (pre-2003 Danish SOCIO classification, "gl" =
   gammel/old). 51 codes had empty DA — the EN placeholders that exist are
   partly correct but we add authoritative DA + improve EN.

DB07 5-digit convention: value `XYabc0` → NACE Rev 2 4-digit class `XY.ab`
(roll-up into DB07 "127-grupperingen"). A handful of codes (89xxx) are legacy
service aggregations kept for backwards compatibility.

Usage: python3 scripts/fix_db07_and_socio_gl.py
"""
import csv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# NACE Rev 2 (authoritative Eurostat text, DA from Danmarks Statistik DB07)
DB07_5DIGIT = {
    "11100": ("Dyrkning af korn (undtagen ris), bælgfrugter og olieholdige frø",
              "Growing of cereals (except rice), leguminous crops and oil seeds"),
    "11200": ("Dyrkning af ris", "Growing of rice"),
    "11300": ("Dyrkning af grøntsager og meloner, rødder og rodknolde",
              "Growing of vegetables and melons, roots and tubers"),
    "11400": ("Dyrkning af sukkerrør", "Growing of sugar cane"),
    "11500": ("Dyrkning af tobak", "Growing of tobacco"),
    "11600": ("Dyrkning af fiberafgrøder", "Growing of fibre crops"),
    "11900": ("Dyrkning af andre etårige afgrøder",
              "Growing of other non-perennial crops"),
    "12100": ("Dyrkning af druer", "Growing of grapes"),
    "12110": ("Dyrkning af druer", "Growing of grapes"),
    "12200": ("Dyrkning af tropiske og subtropiske frugter",
              "Growing of tropical and subtropical fruits"),
    "12300": ("Dyrkning af citrusfrugter", "Growing of citrus fruits"),
    "12400": ("Dyrkning af kernefrugter og stenfrugter",
              "Growing of pome fruits and stone fruits"),
    "12500": ("Dyrkning af andre træ- og buskfrugter samt nødder",
              "Growing of other tree and bush fruits and nuts"),
    "12600": ("Dyrkning af olieholdige frugter", "Growing of oleaginous fruits"),
    "12700": ("Dyrkning af planter til drikkevarefremstilling",
              "Growing of beverage crops"),
    "12800": ("Dyrkning af krydderier, aromatiske, lægemiddel- og farmaceutiske planter",
              "Growing of spices, aromatic, drug and pharmaceutical crops"),
    "12900": ("Dyrkning af andre flerårige afgrøder",
              "Growing of other perennial crops"),
    "13000": ("Planteformering", "Plant propagation"),
    "14400": ("Avl af kameler og kameldyr", "Raising of camels and camelids"),
    "14500": ("Avl af får og geder", "Raising of sheep and goats"),
    "14610": ("Avl af pelsdyr", "Raising of fur animals"),
    "14620": ("Avl af andre dyr", "Raising of other animals"),
    "14700": ("Avl af fjerkræ", "Raising of poultry"),
    "14910": ("Avl af kæledyr", "Raising of pet animals"),
    "14920": ("Avl af andre dyr", "Raising of other animals, n.e.c."),
    "15000": ("Blandet drift", "Mixed farming"),
    "16300": ("Aktiviteter efter høst", "Post-harvest crop activities"),
    "16400": ("Behandling af frø og såsæd", "Seed processing for propagation"),
    "17000": ("Jagt, fangst og serviceydelser i forbindelse hermed",
              "Hunting, trapping and related service activities"),
    "21000": ("Skovdyrkning og andre skovbrugsaktiviteter",
              "Silviculture and other forestry activities"),
    "22000": ("Skovning", "Logging"),
    "23000": ("Indsamling af vildtvoksende materialer undtagen træ",
              "Gathering of wild growing non-wood products"),
    "24000": ("Serviceydelser til skovbrug", "Support services to forestry"),
    "31100": ("Havfiskeri", "Marine fishing"),
    "31200": ("Ferskvandsfiskeri", "Freshwater fishing"),
    "61000": ("Telekommunikation", "Telecommunications"),
    "71000": ("Arkitekt- og ingeniørvirksomhed; teknisk afprøvning og analyse",
              "Architectural and engineering activities; technical testing and analysis"),
    "72900": ("Anden forskning og eksperimentel udvikling indenfor naturvidenskab og teknik",
              "Other research and experimental development on natural sciences and engineering"),
    "89100": ("Andre organisations- og foreningsaktiviteter i.a.n.",
              "Other membership organisation activities n.e.c."),
    "89200": ("Religiøse foreninger og organisationer",
              "Religious organisations"),
    "89300": ("Politiske partier og organisationer",
              "Political organisations"),
    "89900": ("Andre foreninger i.a.n.", "Other organisations n.e.c."),
    "514620": ("Engroshandel med læge- og hospitalsartikler",
               "Wholesale of medical and hospital supplies"),
    "999999": ("Ikke oplyst", "Not stated"),
}

# DST SOCIO (pre-2003, two-digit) — source: DST Kodeark SOCIO variable
SOCIO_GL = {
    "gl_1":  ("Selvstændig", "Self-employed"),
    "gl_2":  ("Medhjælpende ægtefælle", "Assisting spouse"),
    "gl_6":  ("Topleder", "Top manager"),
    "gl_7":  ("Lønmodtager på højeste niveau", "Wage earner, highest-level work"),
    "gl_9":  ("Lønmodtager, ikke nærmere angivet", "Wage earner, not further specified"),
    "gl_11": ("Selvstændig, landbrug", "Self-employed, agriculture"),
    "gl_12": ("Selvstændig, øvrige", "Self-employed, other"),
    "gl_14": ("Selvstændig uden ansatte", "Self-employed, no employees"),
    "gl_19": ("Selvstændig, ikke nærmere angivet",
              "Self-employed, not further specified"),
    "gl_20": ("Medhjælpende ægtefælle", "Assisting spouse"),
    "gl_21": ("Medhjælpende ægtefælle, landbrug",
              "Assisting spouse, agriculture"),
    "gl_22": ("Medhjælpende ægtefælle, øvrige",
              "Assisting spouse, other"),
    "gl_27": ("Lønmodtager, underordnet niveau",
              "Wage earner, basic-level work"),
    "gl_29": ("Lønmodtager, øvrige / ikke nærmere angivet",
              "Wage earner, other / not further specified"),
    "gl_31": ("Direktør mv.", "Director etc."),
    "gl_32": ("Lønmodtager på højt niveau", "Wage earner, senior-level work"),
    "gl_33": ("Lønmodtager på mellemniveau", "Wage earner, mid-level work"),
    "gl_34": ("Lønmodtager på grundniveau", "Wage earner, basic-level work"),
    "gl_35": ("Andre lønmodtagere", "Other wage earners"),
    "gl_37": ("Lønmodtagere uden nærmere angivelse",
              "Wage earners, not further specified"),
    "gl_38": ("Lønmodtager, ikke angivet arbejdsniveau",
              "Wage earner, work level not stated"),
    "gl_39": ("Lønmodtager i øvrigt", "Wage earner, other"),
    "gl_40": ("Arbejdsløs", "Unemployed"),
    "gl_41": ("Arbejdsløs mindst halvdelen af året",
              "Unemployed for at least half the year"),
    "gl_42": ("Arbejdsløs mindre end halvdelen af året",
              "Unemployed for less than half the year"),
    "gl_49": ("Arbejdsløs, ikke nærmere angivet",
              "Unemployed, not further specified"),
    "gl_50": ("Uden for arbejdsstyrken", "Not in the labour force"),
    "gl_51": ("Folkepensionist", "Old-age (state) pensioner"),
    "gl_52": ("Førtidspensionist", "Early retirement pensioner"),
    "gl_53": ("Efterlønsmodtager", "Early-retirement benefit recipient (efterløn)"),
    "gl_54": ("Kontanthjælpsmodtager", "Welfare benefit recipient"),
    "gl_55": ("Modtager af revalideringsydelse",
              "Vocational rehabilitation benefit recipient"),
    "gl_59": ("Andre pensionister", "Other pensioners"),
    "gl_60": ("Uddannelsessøgende", "Student"),
    "gl_62": ("Studerende på videregående uddannelse",
              "Student in tertiary education"),
    "gl_70": ("Barn / ung uden for arbejdsstyrken",
              "Child / youth outside the labour force"),
    "gl_71": ("Barn 0-15 år", "Child aged 0-15"),
    "gl_72": ("Studerende 16+ år", "Student aged 16+"),
    "gl_79": ("Øvrige uden for arbejdsstyrken",
              "Other persons outside the labour force"),
    "gl_80": ("Øvrige uden for arbejdsstyrken i øvrigt",
              "Other persons outside the labour force, unspecified"),
    "gl_89": ("Socioøkonomisk stilling uoplyst",
              "Socio-economic status not stated"),
    "gl_99": ("Uoplyst", "Not stated"),
    "gl_0":  ("Uoplyst", "Not stated"),
    "gl_3":  ("Lønmodtager", "Wage earner"),
    "gl_4":  ("Arbejdsløs", "Unemployed"),
    "gl_5":  ("Pensionist", "Pensioner"),
    "gl_8":  ("Uden for arbejdsstyrken", "Not in the labour force"),
    "gl_10": ("Selvstændig", "Self-employed"),
    "gl_13": ("Selvstændig, 1-4 ansatte", "Self-employed with 1-4 employees"),
    "gl_15": ("Selvstændig, 5+ ansatte", "Self-employed with 5+ employees"),
    "gl_16": ("Selvstændig, landbrug", "Self-employed, agriculture"),
    "gl_17": ("Selvstændig, industri/håndværk", "Self-employed, manufacturing / craft"),
    "gl_18": ("Selvstændig, handel/service", "Self-employed, trade / service"),
    "gl_23": ("Lønmodtager, landbrug", "Wage earner, agriculture"),
    "gl_25": ("Lønmodtager, industri", "Wage earner, manufacturing"),
    "gl_26": ("Lønmodtager, service", "Wage earner, services"),
    "gl_28": ("Lønmodtager, anden branche", "Wage earner, other industry"),
    "gl_69": ("Uddannelsessøgende, ikke nærmere angivet",
              "Student, not further specified"),
    "gl_30": ("Lønmodtager", "Wage earner"),
    "gl_43": ("Arbejdsløs i længere perioder", "Long-term unemployed"),
    "gl_44": ("Arbejdsløs i kortere perioder", "Short-term unemployed"),
    "gl_45": ("Arbejdsløs, aktiveret", "Unemployed, in activation"),
    "gl_46": ("Arbejdsløs, ikke aktiveret", "Unemployed, not in activation"),
    "gl_47": ("Arbejdsløs, sygemeldt", "Unemployed, on sick leave"),
    "gl_48": ("Arbejdsløs, andre", "Unemployed, other"),
    "gl_56": ("Modtager af sygedagpenge", "Sickness benefit recipient"),
    "gl_57": ("Modtager af uddannelsesydelser", "Training allowance recipient"),
    "gl_58": ("Modtager af andre ydelser", "Other benefit recipient"),
    "gl_61": ("Kursist", "Course participant"),
    "gl_63": ("Uddannelsessøgende på ungdomsuddannelse",
              "Student in upper-secondary education"),
    "gl_64": ("Uddannelsessøgende, grundskole",
              "Student in compulsory school"),
    "gl_65": ("Uddannelsessøgende, øvrige", "Student, other"),
    "gl_73": ("Studerende 25+ år", "Student aged 25+"),
    "gl_74": ("Værnepligtig", "Conscript"),
    "gl_75": ("Orlov", "On leave"),
    "gl_76": ("Barselsorlov", "On parental leave"),
    "gl_77": ("Hjemmegående", "Homemaker"),
    "gl_78": ("Andre uden for arbejdsstyrken", "Other outside labour force"),
    "gl_81": ("Uden for arbejdsstyrken i øvrigt",
              "Outside labour force, unspecified"),
    "gl_82": ("Efterlønsmodtager mv.", "Early-retirement benefit recipient etc."),
    "gl_83": ("Pensionist, andet", "Pensioner, other"),
    "gl_84": ("Invalidepensionist", "Disability pensioner"),
    "gl_85": ("Tjenestemandspensionist", "Civil-servant pensioner"),
    "gl_86": ("Pensionist, privat ordning", "Pensioner, private scheme"),
    "gl_87": ("Pensionist, anden offentlig ordning",
              "Pensioner, other public scheme"),
    "gl_88": ("Pensionist, ukendt ordning", "Pensioner, unknown scheme"),
    "gl_90": ("Ikke registreret", "Not registered"),
    "gl_91": ("Udvandret", "Emigrated"),
    "gl_92": ("Afgået ved døden", "Deceased"),
    "gl_93": ("Ukendt adresse", "Unknown address"),
    "gl_94": ("Forsvundet", "Disappeared"),
    "gl_95": ("Midlertidigt fraværende", "Temporarily absent"),
    "gl_96": ("Værnepligtig / militærtjeneste", "Conscript / military service"),
    "gl_97": ("Indsat / anbragt", "Incarcerated / placed"),
    "gl_98": ("Andre uoplyste", "Other not stated"),
}


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    fixed = {"db07": 0, "socio_gl": 0}

    for r in rows:
        cat = r["category"]
        if cat == "LAB_db07" and r["value"] in DB07_5DIGIT and not r["description_da"].strip():
            da, en = DB07_5DIGIT[r["value"]]
            r["description_da"] = da
            r["description"] = da
            r["description_en"] = en
            r["description_short"] = en
            r["description_en_source"] = "nace_rev2"
            fixed["db07"] += 1
        elif cat == "LAB_socio":
            v = r["value"]
            if v in SOCIO_GL:
                da, en = SOCIO_GL[v]
                if not r["description_da"].strip():
                    r["description_da"] = da
                    r["description"] = da
                # Only overwrite EN if it's the generic placeholder
                en_existing = r["description_en"].strip()
                if not en_existing or "Old socio-economic classification code" in en_existing or "(old classification)" in en_existing or en_existing.endswith(" (old)"):
                    r["description_en"] = en
                    r["description_short"] = en
                    r["description_en_source"] = "dst_socio_pre2003"
                fixed["socio_gl"] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    for k, v in fixed.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
