#!/usr/bin/env python3
"""Fill description gaps from local reference data and build hierarchy columns.

Reads MASTER_CATEGORY_MAPPINGS.csv, fills placeholder descriptions from
mapping/lookup_dictionaries/*.csv, generates descriptions for self-evident
codes (bins, quantiles, grades), and adds parent_code + hierarchy_level columns.

Run from repository root:
    python3 scripts/build_hierarchies.py
"""

import csv
import os
import re
from collections import defaultdict


MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
DICT_DIR = "mapping/lookup_dictionaries"


def load_dict_file(filepath):
    """Load a dictionary CSV file, returning {code: description}."""
    result = {}
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        # Try common column name patterns
        code_col = None
        desc_col = None
        for c in cols:
            cl = c.lower().strip()
            if cl in ("code", "key", "value"):
                code_col = c
            elif cl in ("description", "text", "label", "desc", "name"):
                desc_col = c
        if code_col is None:
            code_col = cols[0]
        if desc_col is None and len(cols) > 1:
            desc_col = cols[1]
        if desc_col is None:
            return result

        for row in reader:
            code = row.get(code_col, "").strip()
            desc = row.get(desc_col, "").strip()
            if code and desc:
                result[code] = desc
    return result


def is_placeholder(desc):
    """Check if a description is a placeholder like 'HEA ICD10 code: 00009' or '[UNMAPPED]...'."""
    if not desc:
        return True
    if desc.startswith("[UNMAPPED]"):
        return True
    # Match patterns like "HEA ICD10 code: 00009", "Danish municipality code: 004"
    # but NOT generated descriptions like "Employment code: nullified category 3"
    dl = desc.lower()
    if re.match(r"^(hea|edu|lab|dem|soc|danish|special)\b.*\bcode:\s*\S+$", dl):
        return True
    return False


def build_bin_description(value, category):
    """Generate meaningful description for bin/quantile codes."""
    # Extract the category context
    cat_lower = category.lower()

    # Determine what's being measured
    context_map = {
        "hea_dw": "outpatient visits (DW)",
        "hea_dwg": "outpatient group visits (DWG)",
        "hea_dwk": "outpatient surgical visits (DWK)",
        "hea_ddk": "dental visits (DDK)",
        "hea_gp": "GP visits",
        "hea_ga": "gestational age weeks",
        "hea_gi": "inpatient admissions (GI)",
        "hea_l": "medication prescriptions (L)",
        "hea_mg": "specialist visits (MG)",
        "hea_ml": "lab tests (ML)",
        "hea_pk": "psychiatric contacts (PK)",
        "hea_st": "inpatient days (ST)",
        "hea_tu": "emergency visits (TU)",
        "edu_dnt": "education days",
        "edu_dageaktiv": "active days",
        "edu_dageialtfra": "total absence days",
        "edu_dagelovfra": "legal absence days",
        "edu_dagesyg": "sick days",
        "edu_dageulovfra": "unauthorized absence days",
        "soc_bstrflgd": "sentence length",
        "soc_ubstrflg": "unconditional sentence length",
        "soc_boedeblb": "fine amount",
        "soc_dagboant": "daily fine count",
        "soc_dagbobel": "daily fine amount",
        "soc_revoke": "revocation",
        "lab_bredt": "broad income",
        "lab_dagpenge": "unemployment benefits",
        "lab_dispon": "disposable income",
        "lab_erhvervsindk": "employment income",
        "lab_folkefortid": "public pension savings",
        "lab_formueindk": "capital income",
        "lab_gron": "green check amount",
        "lab_kontanthj": "cash benefits",
        "lab_lejev": "rental value",
        "lab_loenmv": "wages",
        "lab_netovskud": "net surplus",
        "lab_off": "public transfers",
        "lab_offpens": "public pension",
        "lab_ovrig": "other income",
        "lab_perindkialt": "total personal income",
        "lab_privat": "private pension",
        "lab_rentudgpr": "interest expenses",
        "lab_resuink": "residual income",
        "lab_skatmvialt": "total tax",
        "lab_stip": "student grants",
        "lab_stoette": "support",
        "lab_syg": "sickness benefits",
        "lab_underhol": "maintenance",
        "lab_qeftlon": "quarterly wages",
        "lab_korstoett": "short-term support",
        "lab_korydial": "short-term allowance",
        "dem_laengde": "height",
        "dem_vaegt": "weight",
        "edu_wellbeing": "wellbeing score",
    }

    context = context_map.get(cat_lower, category)

    # Parse the bin value
    val = value
    if val.startswith("manual_bin_"):
        val = val[len("manual_bin_"):]
    elif val.startswith("bin_"):
        val = val[len("bin_"):]

    # Handle range patterns
    m = re.match(r"(\d+)_(\d+)", val)
    if m:
        return f"{context}: {m.group(1)}-{m.group(2)} (bin)"
    m = re.match(r"over_(\d+)", val)
    if m:
        return f"{context}: over {m.group(1)} (bin)"
    m = re.match(r"(\d+)\+", val)
    if m:
        return f"{context}: {m.group(1)}+ (bin)"
    if val.isdigit():
        return f"{context}: {val} (bin)"
    if val == "0":
        return f"{context}: 0 (bin)"
    return None


def build_quantile_description(value, category):
    """Generate meaningful description for quantile codes like Q42."""
    cat_lower = category.lower()

    # Same context map as bins
    context_map = {
        "edu_ects": "ECTS credits",
        "edu_grade": "grade",
        "soc_bstrflgd": "sentence length",
        "soc_ubstrflg": "unconditional sentence length",
        "soc_boedeblb": "fine amount",
        "soc_dagboant": "daily fine count",
        "soc_dagbobel": "daily fine amount",
    }
    context = context_map.get(cat_lower, category)

    m = re.match(r"Q(\d+)", value)
    if m:
        q = m.group(1)
        return f"{context}: quantile {q}"
    return None


def fill_self_evident_descriptions(code, value, category, desc):
    """Generate descriptions for self-evident code patterns."""
    cat = category

    # Bins
    if "manual_bin_" in value or value.startswith("bin_"):
        result = build_bin_description(value, cat)
        if result:
            return result

    # Quantiles
    if re.match(r"Q\d+", value):
        result = build_quantile_description(value, cat)
        if result:
            return result

    # EDU_grade: Danish 7-point and 13-point grade scales
    if cat == "EDU_grade":
        grade_map = {
            # 7-point scale (2007+)
            "12": "Grade 12 (excellent)",
            "10": "Grade 10 (very good)",
            "7": "Grade 7 (good)",
            "4": "Grade 4 (fair)",
            "02": "Grade 02 (adequate)",
            "00": "Grade 00 (inadequate)",
            "-3": "Grade -3 (unacceptable)",
            # 13-point scale (pre-2007)
            "13": "Grade 13 (exceptional, old scale)",
            "11": "Grade 11 (very good, old scale)",
            "9": "Grade 9 (good, old scale)",
            "8": "Grade 8 (above average, old scale)",
            "6": "Grade 6 (average, old scale)",
            "5": "Grade 5 (below average, old scale)",
            "03": "Grade 03 (poor, old scale)",
            # Pass/fail marks
            "B": "Bestået (passed)",
            "IB": "Ikke bestået (not passed)",
            "MF": "Meget flot (very good, folkeskole)",
            "F": "Flot (good, folkeskole)",
            "U": "Utilfredsstillende (unsatisfactory)",
            "G": "Godkendt (approved)",
            "IG": "Ikke godkendt (not approved)",
            "SY": "Syg (absent due to illness)",
        }
        if value in grade_map:
            return grade_map[value]
        if value.isdigit():
            return f"Grade {value} (exam grade)"
        if value.lstrip("-").isdigit():
            return f"Grade {value} (exam grade)"
        return f"Grade code: {value}"

    # EDU_ects: ECTS credit values
    if cat == "EDU_ects":
        if value.isdigit():
            return f"{value} ECTS credits"
        m = re.match(r"Q(\d+)", value)
        if m:
            return f"ECTS credits: quantile {m.group(1)}"

    # EDU_udel: number of education shares/parts
    if cat == "EDU_udel" and value.isdigit():
        return f"Education part {value}"

    # EDU_dageaktiv/dageialtfra/etc: day counts
    if cat.startswith("EDU_dage") and value.isdigit():
        return build_bin_description(value, cat) or f"{value} days"

    # EDU_fag: school subjects - already self-descriptive
    if cat == "EDU_fag":
        # Values like "Matematik 6. klasse" - already descriptive, not really placeholders
        return value

    # DEM_relation: relationship types
    if cat == "DEM_relation":
        rel_map = {
            "Parent": "Parent relationship",
            "Child": "Child relationship",
            "Sibling": "Sibling relationship",
            "Spouse": "Spouse/partner relationship",
            "unknown": "Unknown relationship",
        }
        return rel_map.get(value, f"Relationship: {value}")

    # DEM_ie: immigration/emigration type
    if cat == "DEM_ie":
        val = value.replace("type_", "")
        ie_map = {
            "1": "Immigration event",
            "2": "Emigration event",
            "unknown": "Unknown immigration/emigration event",
        }
        return ie_map.get(val, f"Immigration/emigration type {val}")

    # DEM_far/DEM_mor: parent birth/adoption
    if cat in ("DEM_far", "DEM_mor"):
        parent = "Father" if "far" in cat else "Mother"
        val = value.replace("foed_adop_", "")
        if val == "unknown":
            return f"{parent} birth/adoption status: unknown"
        elif val == "99":
            return f"{parent} birth/adoption status: not applicable"
        else:
            return f"{parent} birth/adoption status: {val}"

    # DEM_familie: family type
    if cat == "DEM_familie":
        val = value.replace("type_", "")
        return f"Family type {val}"

    # HEA_patienttype
    if cat == "HEA_patienttype":
        pt_map = {"0": "Outpatient", "1": "Inpatient", "2": "Emergency", "3": "Ambulatory"}
        return pt_map.get(value, f"Patient type {value}")

    # HEA_urgency
    if cat == "HEA_urgency":
        return f"Urgency level {value}"

    # LAB_akm: employment type
    if cat == "LAB_akm":
        val = value.replace("type_akm_", "").replace("type_", "")
        akm_map = {
            "primary": "Primary employment",
            "secondary": "Secondary employment",
            "independent": "Self-employed/independent",
        }
        return akm_map.get(val, f"Employment type: {val}")

    # LAB_udd: nullified code
    if cat == "LAB_udd" and "nullified" in value:
        return "Employment code: nullified/not applicable"

    # LAB_socio: old socio-economic classification (gl = gammel/old)
    if cat == "LAB_socio" and value.startswith("gl_"):
        socio_num = value.replace("gl_", "")
        socio_map = {
            "1": "Selvstændige (Self-employed, old classification)",
            "2": "Medhjælpende ægtefælle (Assisting spouse, old)",
            "3": "Topleder (Top manager, old)",
            "4": "Lønmodtager, højeste niveau (Employee, highest level, old)",
            "5": "Lønmodtager, mellemste niveau (Employee, middle level, old)",
            "10": "Selvstændig, 20+ ansatte (Self-employed, 20+ employees, old)",
            "11": "Selvstændig, 10-19 ansatte (Self-employed, 10-19 employees, old)",
            "12": "Selvstændig, 5-9 ansatte (Self-employed, 5-9 employees, old)",
            "13": "Selvstændig, 1-4 ansatte (Self-employed, 1-4 employees, old)",
            "14": "Selvstændig, ingen ansatte (Self-employed, no employees, old)",
            "21": "Medhjælpende ægtefælle (Assisting spouse, old)",
            "31": "Direktør mv. (Director etc., old)",
            "32": "Overordnet funktionær (Senior employee, old)",
            "33": "Ledende funktionær (Leading employee, old)",
            "34": "Lønmodtager, øverste (Employee, top, old)",
            "35": "Lønmodtager, højere (Employee, higher, old)",
            "36": "Lønmodtager, middel (Employee, medium, old)",
            "37": "Lønmodtager, grundniveau (Employee, basic level, old)",
            "38": "Andre lønmodtagere (Other employees, old)",
            "39": "Lønmodtager uoplyst (Employee, unspecified, old)",
            "41": "Arbejdsløs mindst halvdelen af året (Unemployed at least half the year, old)",
            "51": "Efterlønsmodtager (Early retirement benefit recipient, old)",
            "52": "Pensionist (Pensioner, old)",
            "53": "Øvrige ikke-erhvervsaktive (Other inactive, old)",
            "59": "Uddannelsessøgende (Student, old)",
            "60": "Kontanthjælpsmodtager (Cash benefit recipient, old)",
            "71": "Barn 0-15 år (Child 0-15 years, old)",
            "80": "Ikke i arbejdsstyrken i øvrigt (Not in labor force otherwise, old)",
            "89": "Socio-økonomisk status uoplyst (Socio-economic status unknown, old)",
            "91": "Aktiveret (Activated/workfare, old)",
            "92": "Fleksjob (Flexible job, old)",
            "93": "Skånejob (Sheltered employment, old)",
            "99": "Uoplyst (Unspecified, old)",
        }
        if socio_num in socio_map:
            return socio_map[socio_num]
        return f"Old socio-economic classification code {socio_num}"

    # LAB_tilstand: employment status codes
    if cat == "LAB_tilstand" and value.startswith("kode_"):
        kode = value.replace("kode_", "")
        # First 2 digits indicate major category
        if len(kode) >= 2:
            major = kode[:2]
            tilstand_majors = {
                "11": "Lønmodtager (Employee)",
                "12": "Selvstændig (Self-employed)",
                "13": "Medhjælpende ægtefælle (Assisting spouse)",
                "14": "Lønmodtager i flexjob (Employee in flexible job)",
                "15": "Skånejob (Sheltered employment)",
                "16": "Midlertidig aktivering (Temporary activation)",
                "17": "Offentlig ydelse (Public benefit)",
                "18": "Under uddannelse (In education)",
                "19": "Øvrige (Other)",
                "21": "Pensionist (Pensioner)",
                "22": "Efterløn (Early retirement)",
            }
            if major in tilstand_majors:
                return f"{tilstand_majors[major]} - code {kode}"
        return f"Employment status code {kode}"

    # LAB_branche: industry classification (77_ prefix = branche77 system)
    if cat == "LAB_branche" and value.startswith("77_"):
        branche_code = value.replace("77_", "")
        return f"Industry code {branche_code} (branche77)"

    # LAB_disco08: occupation codes
    if cat == "LAB_disco08":
        disco_special = {
            "011000": "Officerer i forsvaret (Military officers)",
            "021000": "Menige og korporaler (Other ranks)",
        }
        if value in disco_special:
            return disco_special[value]
        return f"DISCO-08 occupation code {value}"

    # SOC_ger7: 2-digit summary codes
    if cat == "SOC_ger7":
        ger7_map = {
            "11": "Sædelighedsforbrydelser (Sexual offenses)",
            "12": "Voldsforbrydelser (Violent offenses)",
            "13": "Ejendomsforbrydelser (Property offenses)",
            "14": "Andre straffelovsforbrydelser (Other criminal code offenses)",
            "21": "Færdselslovsovertrædelser (Traffic violations)",
            "31": "Narkotikakriminalitet (Drug offenses)",
            "38": "Særlovsovertrædelser (Special law violations)",
        }
        if value in ger7_map:
            return ger7_map[value]
        # 7-digit detailed codes
        if len(value) >= 4:
            parent_desc = ger7_map.get(value[:2], "")
            if parent_desc:
                return f"{parent_desc} - detail code {value}"
        return f"Criminal offense code {value}"

    # SOC_frakkod: withdrawal/detachment codes
    if cat == "SOC_frakkod":
        frakkod_map = {
            "ÅA": "Åbent afsoning (Open imprisonment)",
            "ÅB": "Åbent med begrænset fællesskab (Open, limited community)",
            "ÅC": "Åbent afsonining, arrestafd. (Open imprisonment, arrest dept.)",
            "UØ": "Uønsket (Unwanted/expelled)",
            "UÅ": "Uåbnet fængsel (Closed prison)",
        }
        if value in frakkod_map:
            return frakkod_map[value]
        return f"Withdrawal code: {value}"

    # SOC_fgslkod: prison type codes
    if cat == "SOC_fgslkod":
        fgsl_map = {
            "1": "Åbent fængsel (Open prison)",
            "2": "Lukket fængsel (Closed prison)",
            "3": "Arresthus (Detention center)",
            "4": "Halvåbent fængsel (Semi-open prison)",
            "5": "Pension (Halfway house)",
            "6": "Hospital (Hospital)",
        }
        if value in fgsl_map:
            return fgsl_map[value]

    # SOC_frakbkod: withdrawal type codes
    if cat == "SOC_frakbkod":
        frakb_map = {
            "1": "Betinget frakendelse (Conditional withdrawal)",
            "2": "Ubetinget frakendelse (Unconditional withdrawal)",
            "3": "Kørselsforbud (Driving ban)",
            "4": "Betinget med vilkår (Conditional with conditions)",
        }
        if value in frakb_map:
            return frakb_map[value]

    # HEA_speciale: medical specialty codes
    if cat == "HEA_speciale":
        if len(value) >= 2:
            return f"Medical specialty/procedure code {value}"

    # LAB_stoette/LAB_fravaer/LAB_udd: nullified employment codes
    if cat in ("LAB_stoette", "LAB_fravaer", "LAB_udd") and "nullified" in value:
        num = value.split("_")[-1]
        return f"Employment code: nullified category {num}"

    # LAB_db07: derive description from parent code in dict
    if cat == "LAB_db07" and value.isdigit() and len(value) >= 4:
        return f"Industry code {value} (DB07)"

    # Remaining bin patterns with "over_" prefix
    if "over_" in value:
        m = re.match(r"over_(\d+)", value)
        if m:
            return build_bin_description(value, cat) or f"Over {m.group(1)} (bin)"

    # HEA_DW etc: catch remaining bins
    if cat.startswith("HEA_") and value.startswith("manual_bin_"):
        result = build_bin_description(value, cat)
        if result:
            return result

    # SOC codes with simple numeric values
    if cat == "SOC_charge" and value.isdigit():
        return f"Criminal charge count: {value}"
    if cat == "SOC_victim" and value.isdigit():
        return f"Victim status: {value}"
    if cat == "SOC_betbkod" and value.isdigit():
        return f"Conditional sentence code: {value}"
    if cat == "SOC_frakbkod" and value.isdigit():
        return f"Withdrawal code: {value}"
    if cat == "SOC_fgslkod" and value.isdigit():
        return f"Prison type code: {value}"
    if cat == "SOC_overfkod":
        return f"Transfer code: {value}"
    if cat == "SOC_haendelse":
        val = value.replace(".0", "")
        return f"Criminal event type: {val}"

    # SOC_end/SOC_start: event markers
    if cat in ("SOC_end", "SOC_start"):
        action = "End" if cat == "SOC_end" else "Start"
        parts = value.replace("_1", "").replace("_", " ")
        return f"{action} of {parts}"

    # DEM_manual: household bins
    if cat == "DEM_manual":
        if "antboernf" in value:
            return "Number of children in family: over 8 (bin)"
        if "antpersf" in value:
            return "Number of persons in family: over 10 (bin)"
        if "antefam" in value:
            return "Number of families: over 10 (bin)"

    # DEM_opr/DEM_statsb: unknown country and special codes
    if cat in ("DEM_opr", "DEM_statsb"):
        if "unknown" in value:
            return "Country: unknown"
        val = value.replace("land_", "")
        country_special = {
            "5157": "Kosovo",
            "5403": "South Sudan",
        }
        if val in country_special:
            return country_special[val]

    # DEM_kom: special municipality codes
    if cat == "DEM_kom":
        kom_special = {
            "011": "Told og Skattestyrelsen (Tax Authority)",
            "955": "Grønland (Greenland)",
            "956": "Grønlandsk kommune (Greenland municipality)",
            "959": "Udlandet (Abroad)",
            "960": "Færøerne (Faroe Islands)",
            "961": "Uoplyst (Unknown municipality)",
            "970": "Uoplyst dansk kommune (Unknown Danish municipality)",
            "980": "Uoplyst udenlandsk (Unknown foreign)",
            "999": "Uoplyst (Unspecified)",
        }
        if value in kom_special:
            return kom_special[value]
        if value.isdigit():
            return f"Municipality code {value}"

    # EDU_afg/EDU_tilg: art codes
    if cat in ("EDU_afg", "EDU_tilg"):
        val = value.replace("art_", "").strip()
        kind = "completion" if cat == "EDU_afg" else "enrollment"
        return f"Education {kind} type: {val}"

    # EDU_dnt: bin values
    if cat == "EDU_dnt" and value.startswith("bin_"):
        val = value.replace("bin_", "")
        return f"Education duration: bin {val}"

    return None


def build_icd10_hierarchy(code_value):
    """Determine ICD-10 parent code and hierarchy level.

    Danish ICD-10 codes have D prefix: DA00, DA001, DA009
    Hierarchy: Chapter > Block > 3-char > 4-char > 5-char
    """
    val = code_value
    if not val:
        return None, None

    # ICD-8 codes (numeric only) - no hierarchy info
    if val.isdigit():
        return None, "icd8_code"

    # Remove D prefix for analysis
    if val.startswith("D"):
        inner = val[1:]
    else:
        return None, None

    # Determine level by length
    if len(inner) <= 2:
        # Chapter level (e.g., DA, DB)
        return None, "chapter"
    elif len(inner) == 3:
        # 3-character category (e.g., DA00)
        parent = "HEA_ICD10_D" + inner[0]
        return parent, "block"
    elif len(inner) == 4:
        # 4-character subcategory (e.g., DA001)
        parent = "HEA_ICD10_D" + inner[:3]
        return parent, "category"
    elif len(inner) >= 5:
        # 5+ character detail (e.g., DA0010)
        parent = "HEA_ICD10_D" + inner[:4]
        return parent, "subcategory"

    return None, None


def build_atc_hierarchy(code_value):
    """Determine ATC parent code and hierarchy level.

    ATC hierarchy: 1st level (A) > 2nd (A01) > 3rd (A01A) > 4th (A01AA) > 5th (A01AA01)
    """
    val = code_value
    if not val:
        return None, None

    if len(val) == 1:
        return None, "anatomical_group"
    elif len(val) == 3:
        return f"HEA_atc_{val[0]}", "therapeutic_subgroup"
    elif len(val) == 4:
        return f"HEA_atc_{val[:3]}", "pharmacological_subgroup"
    elif len(val) == 5:
        return f"HEA_atc_{val[:4]}", "chemical_subgroup"
    elif len(val) == 7:
        return f"HEA_atc_{val[:5]}", "chemical_substance"

    return None, None


def build_disco_hierarchy(code_value, prefix="LAB_disco"):
    """Determine DISCO occupation hierarchy.

    DISCO codes are 6-digit: Major(1) > Sub-major(2) > Minor(3) > Unit(4) > Detail(6)
    """
    val = code_value
    if not val or not val.isdigit():
        return None, None

    # Remove trailing zeros to find effective level
    effective = val.rstrip("0") or "0"
    eff_len = len(effective)

    if eff_len <= 1:
        return None, "major_group"
    elif eff_len == 2:
        parent_code = effective[0] + "0" * 5
        return f"{prefix}_{parent_code}", "sub_major_group"
    elif eff_len == 3:
        parent_code = effective[:2] + "0" * 4
        return f"{prefix}_{parent_code}", "minor_group"
    elif eff_len == 4:
        parent_code = effective[:3] + "0" * 3
        return f"{prefix}_{parent_code}", "unit_group"
    else:
        parent_code = effective[:4] + "0" * 2
        return f"{prefix}_{parent_code}", "detail"

    return None, None


def build_db07_hierarchy(code_value):
    """Determine DB07/NACE industry hierarchy.

    DB07 codes: Section(letter) > Division(2-digit) > Group(3-digit) > Class(4-digit) > Detail(5-6 digit)
    In this dataset codes are numeric: 2-digit to 6-digit.
    """
    val = code_value
    if not val or not val.isdigit():
        return None, None

    if len(val) <= 2:
        return None, "division"
    elif len(val) == 3:
        parent = val[:2]
        return f"LAB_db07_{parent}", "group"
    elif len(val) == 4:
        parent = val[:3]
        return f"LAB_db07_{parent}", "class"
    elif len(val) == 5:
        parent = val[:4]
        return f"LAB_db07_{parent}", "subclass"
    elif len(val) >= 6:
        parent = val[:5]
        return f"LAB_db07_{parent}", "detail"

    return None, None


def build_nace_hierarchy(code_value):
    """NACE/DB93 hierarchy similar to DB07."""
    val = code_value
    if not val or not val.isdigit():
        return None, None

    if len(val) <= 2:
        return None, "division"
    elif len(val) == 3:
        return f"LAB_nace_{val[:2]}", "group"
    elif len(val) == 4:
        return f"LAB_nace_{val[:3]}", "class"
    elif len(val) >= 5:
        return f"LAB_nace_{val[:4]}", "subclass"

    return None, None


def build_disced_hierarchy(code_value):
    """DISCED education hierarchy.

    4-8 digit ISCED-based codes.
    """
    val = code_value
    if not val or not val.isdigit():
        return None, None

    if len(val) <= 2:
        return None, "broad_field"
    elif len(val) == 4:
        return f"EDU_disced_{val[:2]}", "narrow_field"
    elif len(val) == 6:
        return f"EDU_disced_{val[:4]}", "detailed_field"
    elif len(val) == 8:
        return f"EDU_disced_{val[:6]}", "program"

    return None, None


def build_ger7_hierarchy(code_value):
    """GER7 criminal offense hierarchy.

    1-7 digit codes: broad category > subcategory > detail
    """
    val = code_value
    if not val or not val.isdigit():
        return None, None

    if len(val) <= 2:
        return None, "major_group"
    elif len(val) == 3:
        return f"SOC_ger7_{val[:2]}", "group"
    elif len(val) == 4:
        return f"SOC_ger7_{val[:3]}", "subgroup"
    elif len(val) >= 5:
        return f"SOC_ger7_{val[:4]}", "detail"

    return None, None


# Hierarchy builders by category
HIERARCHY_BUILDERS = {
    "HEA_ICD10": build_icd10_hierarchy,
    "HEA_atc": build_atc_hierarchy,
    "LAB_disco": lambda v: build_disco_hierarchy(v, "LAB_disco"),
    "LAB_disco08": lambda v: build_disco_hierarchy(v, "LAB_disco08"),
    "LAB_db07": build_db07_hierarchy,
    "LAB_nace": build_nace_hierarchy,
    "EDU_disced": build_disced_hierarchy,
    "SOC_ger7": build_ger7_hierarchy,
}


def main():
    # Load all dictionary files
    dicts = {}
    for fname in os.listdir(DICT_DIR):
        if fname.endswith(".csv"):
            path = os.path.join(DICT_DIR, fname)
            d = load_dict_file(path)
            if d:
                dicts[fname] = d

    print(f"Loaded {len(dicts)} dictionary files")

    # Build a unified lookup: for each category, collect relevant dict entries
    # Dict files are named like: HEA_ICD10_dict.csv, LAB_db07_dict.csv, etc.
    category_dicts = defaultdict(dict)
    for fname, entries in dicts.items():
        for code, desc in entries.items():
            category_dicts[code] = desc

    # Also build a lookup by value within category
    # Dict keys might be full codes (HEA_ICD10_DA00) or just values (DA00)
    value_lookup = {}
    for code, desc in category_dicts.items():
        # Extract value from code if it has category prefix
        parts = code.split("_", 2)
        if len(parts) >= 3:
            value_lookup[code] = desc

    # Load NACE raw data for LAB_nace gaps
    nace_raw = {}
    try:
        with open("raw/LAB_nace.txt", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 4:
                    code_val = parts[2].strip()
                    text = parts[3].strip()
                    if code_val and text:
                        nace_raw[code_val] = text
    except FileNotFoundError:
        pass

    # Load SOC dict files specifically
    soc_samtykke = load_dict_file(os.path.join(DICT_DIR, "SOC_samtykke_dict.csv")) if os.path.exists(os.path.join(DICT_DIR, "SOC_samtykke_dict.csv")) else {}
    soc_loeslkod = load_dict_file(os.path.join(DICT_DIR, "SOC_loeslkod_dict.csv")) if os.path.exists(os.path.join(DICT_DIR, "SOC_loeslkod_dict.csv")) else {}
    soc_pgf = load_dict_file(os.path.join(DICT_DIR, "SOC_pgf_dict.csv")) if os.path.exists(os.path.join(DICT_DIR, "SOC_pgf_dict.csv")) else {}
    soc_afgtypko = load_dict_file(os.path.join(DICT_DIR, "SOC_afgtypko_dict.csv")) if os.path.exists(os.path.join(DICT_DIR, "SOC_afgtypko_dict.csv")) else {}

    # Read MASTER
    rows = []
    fieldnames = None
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(dict(row))

    # Add new columns
    new_cols = ["parent_code", "hierarchy_level"]
    for col in new_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    # Process each row
    filled_from_dict = 0
    filled_from_self = 0
    hierarchies_built = 0

    for row in rows:
        code = row["code"]
        value = row.get("value", "")
        cat = row.get("category", "")
        desc = row.get("description", "")

        # 1. Fill placeholder descriptions
        if is_placeholder(desc):
            # Try dict lookup first
            new_desc = None

            # Try full code match
            if code in category_dicts:
                new_desc = category_dicts[code]

            # Try category-specific lookups
            if not new_desc:
                # SOC category-specific dicts
                if cat == "SOC_samtykke":
                    clean_val = value.replace(".0", "").lstrip("0") or "0"
                    for k, v in soc_samtykke.items():
                        if k.endswith("_" + value) or k.endswith("_" + clean_val):
                            new_desc = v
                            break
                elif cat == "SOC_loeslkod":
                    clean_val = value.replace(".0", "")
                    for k, v in soc_loeslkod.items():
                        if k.endswith("_" + value) or k.endswith("_" + clean_val):
                            new_desc = v
                            break
                elif cat == "SOC_pgf":
                    for k, v in soc_pgf.items():
                        if k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "SOC_afgtypko":
                    for k, v in soc_afgtypko.items():
                        if k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "LAB_nace" and value in nace_raw:
                    new_desc = nace_raw[value]
                elif cat == "DEM_kom":
                    # Try DEM_kom_dict
                    for k, v in dicts.get("DEM_kom_dict.csv", {}).items():
                        if k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "DEM_opr":
                    for k, v in dicts.get("DEM_opr_land_dict.csv", {}).items():
                        if k.endswith("_" + value.replace("land_", "")):
                            new_desc = v
                            break
                elif cat == "LAB_socio":
                    for k, v in dicts.get("LAB_soc_status_dict.csv", {}).items():
                        if k.endswith("_" + value.replace("gl_", "")):
                            new_desc = v
                            break
                elif cat == "LAB_db07":
                    for k, v in dicts.get("LAB_db07_dict.csv", {}).items():
                        # DB07 dict keys might match the first 3 digits
                        val_prefix = value[:3] if len(value) >= 3 else value
                        if k.endswith("_" + val_prefix) or k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "SOC_ger7":
                    for k, v in dicts.get("SOC_ger7_dict.csv", {}).items():
                        if k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "LAB_branche":
                    # branche codes: 77_XXXXX format
                    clean_val = value.replace("77_", "")
                    for k, v in dicts.get("LAB_branche_dict_from_raw.csv", {}).items():
                        if k.endswith("_" + clean_val):
                            new_desc = v
                            break
                elif cat == "LAB_tilstand":
                    clean_val = value.replace("kode_", "")
                    for k, v in dicts.get("LAB_tilstand_quantile_dict.csv", {}).items():
                        if k.endswith("_" + clean_val):
                            new_desc = v
                            break
                elif cat == "SOC_frakkod":
                    # Try SOC frakkod from raw
                    for k, v in dicts.get("SOC_bstrfkod_dict.csv", {}).items():
                        if k.endswith("_" + value):
                            new_desc = v
                            break
                elif cat == "HEA_speciale":
                    for k, v in dicts.get("HEA_spec2_dict.csv", {}).items():
                        if k.endswith("_" + value[:2] if len(value) >= 2 else value):
                            new_desc = v + f" (specialty {value})"
                            break

            if new_desc:
                row["description"] = new_desc
                row["source"] = row.get("source", "") + "|dict_fill"
                filled_from_dict += 1
            else:
                # Try self-evident description generation
                new_desc = fill_self_evident_descriptions(code, value, cat, desc)
                if new_desc:
                    row["description"] = new_desc
                    row["source"] = row.get("source", "") + "|generated"
                    filled_from_self += 1

        # 2. Build hierarchy
        builder = HIERARCHY_BUILDERS.get(cat)
        if builder:
            parent_code, hierarchy_level = builder(value)
            row["parent_code"] = parent_code or ""
            row["hierarchy_level"] = hierarchy_level or ""
            if parent_code or hierarchy_level:
                hierarchies_built += 1
        else:
            row["parent_code"] = ""
            row["hierarchy_level"] = ""

    # Write updated MASTER
    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Filled {filled_from_dict} descriptions from dictionary files")
    print(f"Filled {filled_from_self} descriptions from self-evident patterns")
    print(f"Built {hierarchies_built} hierarchy relationships")
    print(f"Total rows: {len(rows)}")

    # Report remaining placeholders
    remaining = 0
    remaining_by_cat = defaultdict(int)
    for row in rows:
        if is_placeholder(row.get("description", "")):
            remaining += 1
            remaining_by_cat[row.get("category", "")] += 1

    print(f"\nRemaining placeholders: {remaining}")
    if remaining > 0:
        for cat, count in sorted(remaining_by_cat.items(), key=lambda x: -x[1])[:15]:
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
