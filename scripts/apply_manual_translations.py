#!/usr/bin/env python3
"""Apply a hand-curated Danish→English dictionary to MASTER_CATEGORY_MAPPINGS.

Covers the most frequent Danish administrative terms that the MT pipeline
failed to translate. Only rewrites description_en when the current value is
an identical copy of description_da (i.e. the pipeline didn't translate it).
Entries are deterministic and reviewed by hand.

Usage:
    python3 scripts/apply_manual_translations.py [--dry-run]
"""
import argparse
import csv
import os
import re
import sys

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from manual_translations_ext import EXTENDED  # type: ignore
except ImportError:
    EXTENDED = {}

# Hand-curated translations — ONE PER LINE.  Keys are exact strings as they
# appear in description_da.  Values are the English replacement.
MANUAL = {
    # ─── LAB_disco (occupations) ────────────────────────────────────────
    "Almindeligt kontorarbejde": "General office work",
    "Almindeligt kontorarbejde (via 411)": "General office work (via 411)",
    "Arbejde inden for PR": "Work in public relations",
    "Arbejde inden for kemi": "Work in chemistry",
    "Asfaltarbejde": "Asphalt work",
    "Assistentarbejde i laboratorier": "Laboratory assistant work",
    "Bartenderarbejde": "Bartending work",
    "Bartenderarbejde (via 5132)": "Bartending work (via 5132)",
    "Bedemandsarbejde": "Funeral director work",
    "Dataregistreringsarbejde": "Data-entry work",
    "Elektrikerarbejde": "Electrician work",
    "Elektrikerarbejde (via 7411)": "Electrician work (via 7411)",
    "Finmekanikerarbejde": "Precision mechanic work",
    "Flymekanikerarbejde": "Aircraft mechanic work",
    "Fotografarbejde": "Photographer work",
    "Fotografarbejde (via 3431)": "Photographer work (via 3431)",
    "Grafisk arbejde (via 732)": "Graphic work (via 732)",
    "Indtastningsarbejde (via 413)": "Data-entry work (via 413)",
    "Jordemoderarbejde": "Midwifery work",
    "Kabelarbejde": "Cable work",
    "Kammertjenerarbejde": "Valet work",
    "Kokkearbejde (via 512)": "Cooking / chef work (via 512)",
    "Kundeinformationsarbejde (via 422)": "Customer-information work (via 422)",
    "Kundeservice (via 42)": "Customer service (via 42)",
    "Laborantarbejde": "Laboratory technician work",
    "Malerarbejde (via 7131)": "Painting work (via 7131)",
    "Manuelt produktionsarbejde (via 932)": "Manual production work (via 932)",
    "Mekanikerarbejde (via 723)": "Mechanic work (via 723)",
    "Monteringsarbejde (via 82)": "Assembly work (via 82)",
    "Monteringsarbejde (via 821)": "Assembly work (via 821)",
    "Pladesmedarbejde": "Sheet-metal work",
    "Rejsebureauarbejde": "Travel agency work",
    "Riggerarbejde": "Rigger work",
    "Salgsarbejde (ekskl. agentarbejde) (via 52)": "Sales work (excl. agent work) (via 52)",
    "Salgsarbejde i butik (via 522)": "Retail sales work (via 522)",
    "Servicearbejde (via 51)": "Service work (via 51)",
    "Smedearbejde": "Smithing / blacksmith work",
    "Specialundervisning (via 2352)": "Special-needs education (via 2352)",
    "Stenhuggerarbejde": "Stonemason work",
    "Sygeplejerskearbejde (via 2221)": "Nursing work (via 2221)",
    "Teknisk tegnearbejde": "Technical drawing / drafting work",
    "Telefonomstillingsarbejde": "Telephone switchboard work",
    "Telefonomstillingsarbejde (via 4223)": "Telephone switchboard work (via 4223)",
    "Tjenerarbejde": "Waiting work",
    "Tjenerarbejde (via 5131)": "Waiting work (via 5131)",
    "Tograngering": "Train shunting",
    "Trykkerarbejde": "Printing work",

    # ─── LAB_disco08 ────────────────────────────────────────────────────
    "Administrativ ledelse i den offentlige sektor": "Administrative management in the public sector",
    "Akademikere (via 2)": "Professionals (via 2)",
    "Bygningsarkitekter (via 2161)": "Building architects (via 2161)",
    "Elektroteknikere (via 3113)": "Electrical technicians (via 3113)",
    "Fiskere (via 6114)": "Fishermen (via 6114)",
    "Generelt kontorpersonale (via 41)": "General office clerks (via 41)",
    "Gipsere (via 7123)": "Plasterers (via 7123)",
    "Glasmagere (via 7125)": "Glassmakers (via 7125)",
    "Hjemmepersonale (via 9111)": "Domestic staff (via 9111)",
    "Hurtigmadslavere (via 9411)": "Fast-food preparers (via 9411)",
    "Kemikere (via 2113)": "Chemists (via 2113)",
    "Kemiteknikere (via 3116)": "Chemical technicians (via 3116)",
    "Landbrugsarbejdere (via 6111)": "Farm workers (via 6111)",
    "Landskabsarkitekter (via 2162)": "Landscape architects (via 2162)",
    "Ledelse inden for HR-funktioner": "Management in HR functions",
    "Ledere (via 1)": "Managers (via 1)",
    "Maskinteknikere (via 3115)": "Mechanical technicians (via 3115)",
    "Meteorologer (via 2112)": "Meteorologists (via 2112)",
    "Murere (via 7112)": "Bricklayers (via 7112)",
    "Rejseledere (via 5113)": "Travel guides (via 5113)",
    "Tjenere (via 5131)": "Waiters (via 5131)",
    "VVS-arbejdere (via 7126)": "Plumbers (via 7126)",

    # ─── LAB_db07 (industries) ──────────────────────────────────────────
    "Arbejdsformidlingskontorer (via 781)": "Employment agencies (via 781)",
    "Campingpladser (via 553)": "Campsites (via 553)",
    "Elforsyning (via 351)": "Electricity supply (via 351)",
    "Fastnetbaseret telekommunikation (via 611)": "Fixed-line telecommunications (via 611)",
    "Formueforvaltning (via 663)": "Asset management (via 663)",
    "Forsikring (via 651)": "Insurance (via 651)",
    "Gasforsyning (via 352)": "Gas supply (via 352)",
    "Genbrug (via 383)": "Recycling (via 383)",
    "Hospitaler (via 861)": "Hospitals (via 861)",
    "Investeringsforeninger, investeringsselskaber o.l. (via 643)":
        "Investment funds, investment companies etc. (via 643)",
    "Kombinerede serviceydelser (via 811)": "Combined support services (via 811)",
    "Landskabspleje (via 813)": "Landscape care (via 813)",
    "Pengeinstitutvirksomhed (via 641)": "Banking (via 641)",
    "Pensionsforsikring (via 653)": "Pension insurance (via 653)",
    "Radiovirksomhed (via 601)": "Radio broadcasting (via 601)",
    "Reklame (via 731)": "Advertising (via 731)",
    "Renhold (via 812)": "Cleaning services (via 812)",
    "Satellitbaseret telekommunikation (via 613)": "Satellite telecommunications (via 613)",
    "Servicestationer (via 473)": "Service stations (via 473)",
    "Specialiseret designarbejde (via 741)": "Specialised design work (via 741)",
    "Sport (via 931)": "Sports (via 931)",
    "Vandforsyning (via 360)": "Water supply (via 360)",
    "Varmeforsyning (via 353)": "Heat supply (via 353)",
    "Vikarbureauer (via 782)": "Temporary-work agencies (via 782)",

    # ─── SOC_ger7 (criminal offences) ───────────────────────────────────
    "Alvorligere vold (via 1255)": "Aggravated violence (via 1255)",
    "Bedrageri (via 1357)": "Fraud (via 1357)",
    "Brandstiftelse (via 1312)": "Arson (via 1312)",
    "Forbrydelser i familieforhold": "Offences against family relations",
    "Indbr. i ubeboede bebyggelser (via 1324)":
        "Burglary in uninhabited buildings (via 1324)",
    "Mandatsvig (via 1363)": "Breach of trust (via 1363)",
    "Manddrab (via 1230)": "Homicide (via 1230)",
    "Skyldnersvig (via 1372)": "Debtor fraud (via 1372)",
    "Tilhold (via 1475)": "Restraining order (via 1475)",
    "Trusler (via 1292)": "Threats (via 1292)",
    "Uagtsomt manddrab/legemsbesk. (via 1283)":
        "Negligent homicide / bodily harm (via 1283)",

    # ─── LAB_soc (socio-economic status) ────────────────────────────────
    "Feriedagpenge": "Holiday unemployment benefit",
    "Fleksydelse": "Flex-job benefit",
    "Folkepension": "State pension",
    "Folkepensionister": "State pensioners",
    "Integrationsydelse": "Integration benefit",
    "Kursister": "Course participants",
    "Ledighedsydelse": "Unemployment benefit for flex-job recipients",
    "Produktionsskoleelever": "Production-school students",
    "Revalidering": "Vocational rehabilitation",
    "Seniorpension": "Senior pension",
    "Tidlig pension": "Early retirement pension",
    "Udenlandske studerende (ud fra opholdsgrundlag)":
        "Foreign students (based on residence status)",

    # ─── LAB_tilstand ───────────────────────────────────────────────────
    "Arbejdsmarkedsydelse": "Labor-market benefit",
    "G-dage": "Employer-paid unemployment days (G-dage)",
    "Introduktionsydelse": "Introduction benefit",
    "Ledighedsydelse under ferie": "Unemployment benefit during vacation",
    "Nytteindsats": "Community work placement",
    "Revalidering, detaljer oplyst": "Vocational rehabilitation, details provided",
    "Tjenestemandspension": "Civil-servant pension",
    "Udenlandske studerende": "Foreign students",
    "Virksomhedspraktik": "Company internship",

    # ─── SOC_ansted (placement types) ───────────────────────────────────
    "17 akutinstitution (2006-2009)": "17 acute institution (2006-2009)",
    "25 Specialiseret plejefamilie": "25 Specialised foster family",
    "Almindelig plejefamilie, generelt godkendt":
        "Ordinary foster family, generally approved",
    "Almindelig plejefamilie, konkret godkendt":
        "Ordinary foster family, specifically approved",
    "Kommunal plejefamilie, generelt godkendt":
        "Municipal foster family, generally approved",
    "Skibsprojekt": "Ship project",

    # ─── SOC_frakkod ────────────────────────────────────────────────────
    "Indrejseforbud, Retsplejeloven 723, 23-28":
        "Entry ban, Administration of Justice Act § 723, 23-28",
    "Meddelt strakstilhold": "Immediate restraining order issued",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Combined dictionary: base + extension. Extension values win on conflict.
    combined = dict(MANUAL)
    combined.update(EXTENDED)

    applied = 0
    not_found = 0
    seen = set()

    for row in rows:
        da = row["description_da"].strip()
        en = row["description_en"].strip()
        if da not in combined:
            continue
        seen.add(da)
        # Replace if EN is empty OR EN is an identical untranslated copy of DA.
        if en and en != da:
            continue
        row["description_en"] = combined[da]
        applied += 1

    for da in combined:
        if da not in seen:
            not_found += 1

    print(f"Applied translations to {applied} rows "
          f"(base dict: {len(MANUAL)}, extended: {len(EXTENDED)})")
    print(f"Dictionary entries not found in MASTER: {not_found}")

    if args.dry_run:
        print("[dry-run] no changes written")
        return

    # Also refresh description_short for changed rows
    for row in rows:
        en = row["description_en"].strip()
        if en:
            row["description_short"] = re.sub(r"\s*\([^)]*\)", "", en).strip()

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {MASTER_PATH}")


if __name__ == "__main__":
    main()
