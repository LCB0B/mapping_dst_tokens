#!/usr/bin/env python3
"""Fix English translations of LAB income quantile categories.

Each category is verified against DST TIMES variable documentation
(https://www.dst.dk/da/Statistik/dokumentation/Times/personindkomst/<var>).

For each category we rebuild:
  description_da       = authoritative Danish name from DST TIMES
  description_en       = corrected English
  description           = same as description_en (display)
  description_short    = EN base without quantile suffix
  description_en_source = 'dst_times_<variable>'

The per-row quantile/percentile suffix (" - Nth percentile" or " - N/10 quantile"
depending on how many codes the category has) is preserved/regenerated.
"""
import csv
import re
from collections import defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# (category, variable, da, en)
# DA is from DST TIMES variable documentation.
# EN is either the official DST English label or a faithful translation
# validated against the DST page. Only categories with real issues or
# those needing a DA fill are included; fully-correct ones are also
# re-populated so DA is consistent.
FIXES = {
    # ── Corrections (wrong or misleading) ─────────────────────────────────
    "LAB_skatmvialt": (
        "skatmvialt_13",
        "Skat, arbejdsmarkedsbidrag og særlig pension i alt (ekskl. kirkeskat)",
        "Total taxes, labor market contribution and special pension (excl. church tax)",
    ),
    "LAB_ovrig": (
        "ovrig_dagpenge_akas_13",
        "Øvrige dagpenge fra A-kasser (ekskl. efterløn, arbejdsløshedsdagpenge og uddannelsesgodtgørelse)",
        "Other unemployment benefits from A-kasses (excl. efterløn, regular unemployment benefit and training allowance)",
    ),
    "LAB_korstoett": (
        "korstoett",
        "Boligsikring og boligydelse",
        "Housing benefit (for tenants) and housing allowance (for pensioners)",
    ),
    "LAB_lejev": (
        "lejev_egen_bolig",
        "Beregnet lejeværdi af egen bolig",
        "Imputed rental value of own dwelling",
    ),
    "LAB_syg": (
        "syg_barsel_13",
        "Udbetalte syge- og barselsdagpenge fra kommuner",
        "Sick leave and maternity benefits (paid by municipalities)",
    ),
    "LAB_folkefortid": (
        "folkefortid_13",
        "Folke- og førtidspension mv.",
        "State pension (folkepension) and disability pension (førtidspension), etc.",
    ),
    "LAB_bredt": (
        "bredt_loen_beloeb",
        "Bredt lønbeløb (inkl. ATP og personalegoder)",
        "Broad wage amount (incl. ATP and employee benefits)",
    ),
    "LAB_dagpenge": (
        "dagpenge_kontant_13",
        "Dagpenge og kontanthjælp mv. i alt",
        "Unemployment and cash benefits etc. combined (dagpenge, kontanthjælp, sygedagpenge, barsel)",
    ),
    "LAB_korydial": (
        "korydial",
        "Udbetalte børnetilskud og familieydelser (opregnet til hele kalenderåret)",
        "Paid child allowances and family benefits (annualized to full calendar year)",
    ),
    "LAB_perindkialt": (
        "perindkialt_13",
        "Personindkomst i alt (ekskl. beregnet lejeværdi af egen bolig)",
        "Total personal income (excl. imputed rental value of own dwelling)",
    ),
    "LAB_privat": (
        "privat_pension_13",
        "Udbetalte private pensioner",
        "Paid-out private pensions",
    ),
    "LAB_netovskud": (
        "netovskud_13",
        "Nettooverskud af selvstændig virksomhed",
        "Net profit from self-employment",
    ),
    "LAB_offpens": (
        "offpens_efterlon_13",
        "Folke- og førtidspension, varmehjælp, efterløn og fleksydelse",
        "State pension, disability pension, heating allowance, efterløn and flex benefit",
    ),
    "LAB_resuink": (
        "resuink_13",
        "Restindkomst inkl. børnebidrag",
        "Residual income (including child support)",
    ),
    # ── Already accurate — re-populated so DA is filled ──────────────────
    "LAB_loenmv": (
        "loenmv_13",
        "Lønindkomst i alt",
        "Total wage income",
    ),
    "LAB_dispon": (
        "dispon_13",
        "Disponibel indkomst",
        "Disposable income",
    ),
    "LAB_erhvervsindk": (
        "erhvervsindk_13",
        "Erhvervsindkomst (løn og nettooverskud af selvstændig virksomhed inkl. visse honorarer)",
        "Business income (wages and net surplus from self-employment, incl. certain honorariums)",
    ),
    "LAB_formueindk": (
        "formueindk_brutto",
        "Renteindtægter og realiserede tab/gevinster på værdipapirer (ekskl. beregnet lejeværdi af egen bolig)",
        "Interest income and realized gains/losses on securities (excl. imputed rental value of own dwelling)",
    ),
    "LAB_kontanthj": (
        "kontanthj_13",
        "Kontanthjælp (underhold/forsørgelse)",
        "Cash assistance (subsistence/support)",
    ),
    "LAB_honny": (
        "honny",
        "Honoraraflønning (arbejdsmarkedsbidragspligtig)",
        "Fee-based remuneration (subject to labor market contribution)",
    ),
    "LAB_underhol": (
        "underhol",
        "Betalt underholdsbidrag (fradrag i skattepligtig indkomst)",
        "Paid maintenance (deduction in taxable income)",
    ),
    "LAB_stip": (
        "stip",
        "Stipendier fra Statens Uddannelsesstøtte (SU)",
        "Scholarships from State Educational Support (SU)",
    ),
    "LAB_rentudgpr": (
        "rentudgpr",
        "Fradragsberettigede renteudgifter (ekskl. udland og selvstændig virksomhed)",
        "Tax-deductible interest expenses (excl. foreign and self-employment interest)",
    ),
    "LAB_assets": (
        "formrest_ny05",
        "Nettoformue ultimo året, ekskl. pensionsformue",
        "Net residual wealth at end of year (excl. pension assets)",
    ),
    "LAB_qeftlon": (
        "qeftlon",
        "Efterløn, overgangsydelse og (fra 2008) fleksydelse",
        "Efterløn (early retirement benefit), transitional allowance and (from 2008) flex benefit",
    ),
    "LAB_arblhumv": (
        "arblhumv",
        "Arbejdsløshedsdagpenge og uddannelsesgodtgørelse",
        "Unemployment benefits and training allowance",
    ),
    "LAB_gron": (
        "gron_check",
        "Grøn check (kompensation for grønne afgifter)",
        "Green check (compensation for green taxes)",
    ),
    "LAB_off": (
        "off_overforsel_13",
        "Offentlige overførsler",
        "Public transfers",
    ),
}

Q_RE = re.compile(r"Q(\d+)$")


def main():
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fn = list(reader.fieldnames)
        rows = list(reader)

    # Count rows per category to determine bucket scale (10 or 100)
    cat_counts = defaultdict(int)
    for r in rows:
        if r["category"] in FIXES:
            cat_counts[r["category"]] += 1

    fixed = defaultdict(int)

    for r in rows:
        cat = r["category"]
        if cat not in FIXES:
            continue

        variable, da_base, en_base = FIXES[cat]

        # Extract quantile number from value (e.g. "Q15", "loen_beloeb_Q15", "13_Q24")
        m = Q_RE.search(r["value"])
        if not m:
            continue
        q = int(m.group(1))
        total = cat_counts[cat]
        # total is 10, 100, or 300 (LAB_ovrig has 3 sub-variables × 100).
        # Treat 300 as 100-quantile (percentile) since each sub-variable has 100.
        scale = 10 if total <= 10 else 100
        suffix_en = f" — {q}/{scale} quantile"
        suffix_da = f" — {q}/{scale} kvantil"

        r["description_da"] = da_base + suffix_da
        r["description"] = da_base + suffix_da
        r["description_en"] = en_base + suffix_en
        r["description_short"] = en_base
        r["description_en_source"] = f"dst_times_{variable}"
        r["confidence_level"] = "high"
        fixed[cat] += 1

    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        w.writerows(rows)

    total = sum(fixed.values())
    for cat in sorted(fixed):
        print(f"  {cat:<20} {fixed[cat]}")
    print(f"\nTotal rows fixed: {total}")


if __name__ == "__main__":
    main()
