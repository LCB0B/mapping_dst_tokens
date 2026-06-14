#!/usr/bin/env python3
"""Fix 33 half-translated SOC_ger7 English descriptions.

The rule-based Danish->English translation (notes.md §7) left Danish fragments
in 33 rows ('Seat belt, ikke brug af', 'Ulovlig adgang to erdutyshemmeligheder',
'foreignersloven', ...). Re-translated in full from the official Danish
(description_da = ger7.csv register text). Keyed by value with the expected
Danish asserted, so the fix cannot land on drifted rows.
"""

import csv
import sys

FIX = {
    # value: (expected description_da, corrected description_en)
    "2610078": ("Sikkerhedssele, ikke brug af",
                "Seat belt, failure to use"),
    "3830713": ("Hundeloven, overtrædelse af, samt overtrædelse af pålæg",
                "Dog Act, violation of, and violation of orders"),
    "1180545": ("Børnepornografi, besiddelse af/bekendt med",
                "Child pornography, possession of/acquaintance with"),
    "1180546": ("Børnepornografi, besiddelse af/bekendt med",
                "Child pornography, possession of/acquaintance with"),
    "1210510": ("Trusler om vold mv. mod offentlig myndighed",
                "Threats of violence etc. against public authority"),
    "2610044": ("Mobiltelefon mv., brug af",
                "Mobile phone etc., use of"),
    "2610080": ("Styrthjelm, ikke brug af",
                "Crash helmet, failure to use"),
    "1351505": ("Ulovlig omgang med hittegods",
                "Unlawful handling of found property"),
    "2610047": ("Spirituskørsel, manglende hindring af",
                "Drunk driving, failure to prevent"),
    "2610051": ("Spirituskørsel, manglende hindring af",
                "Drunk driving, failure to prevent"),
    "1410712": ("Fanger mv., ulovlig forbindelse med",
                "Prisoners etc., unlawful contact with"),
    "1210509": ("Trussel om vold mod nogen i offentlig tjeneste",
                "Threat of violence against a person in public service"),
    "3810915": ("Tilhold, overtrædelse af",
                "Restraining order, violation of"),
    "2610076": ("Ulovlig kørsel med udenlandsk køretøj",
                "Unlawful driving of a foreign vehicle"),
    "1410717": ("Ulovlig forbindelse med fanger mv.",
                "Unlawful contact with prisoners etc."),
    "1120511": ("Voldtægt ved ulovlig tvang",
                "Rape by unlawful coercion"),
    "1120520": ("Anden kønslig omgang ved vold",
                "Other sexual intercourse by violence"),
    "3810241": ("Manglende overholdelse af pålagt meldepligt jf. udlændingeloven",
                "Non-compliance with imposed duty to report under the Aliens Act"),
    "3810212": ("Udlændingeloven, bistand ved ulovlig indrejse/ophold",
                "Aliens Act, assisting unlawful entry/stay"),
    "1120525": ("Anden kønslig omgang ved ulovlig tvang",
                "Other sexual intercourse by unlawful coercion"),
    "1336570": ("Tyveri i forbindelse med vold",
                "Theft in connection with violence"),
    "1120526": ("Andet seksuelt forhold ved ulovlig tvang",
                "Other sexual relation by unlawful coercion"),
    "1210503": ("Trusler om vold mv. mod overordnet polititjenestemand",
                "Threats of violence etc. against a senior police officer"),
    "1000100": ("Opholdsforbud ved dom, registrering af",
                "Residence ban by judgment, registration of"),
    "1120521": ("Andet seksuelt forhold ved vold eller trussel om vold",
                "Other sexual relation by violence or threat of violence"),
    "1120510": ("Samleje med ulovlig tvang",
                "Sexual intercourse by unlawful coercion"),
    "1485410": ("Ulovlig adgang til erhvervshemmeligheder",
                "Unlawful access to trade secrets"),
    "3810918": ("Tilhold og opholdsforbud, overtrædelse af",
                "Restraining and exclusion orders, violation of"),
    "3810242": ("Manglende overholdelse af pålagt opholdspligt jf. udlændingeloven",
                "Non-compliance with imposed duty of residence under the Aliens Act"),
    "3810916": ("Opholdsforbud, overtrædelse af",
                "Exclusion order, violation of"),
    "1485415": ("Kode til informationssystem, ulovlig anvendelse af",
                "Code for an information system, unlawful use of"),
    "2610079": ("ATK Sikkerhedssele, ikke brug af",
                "ATK seat belt, failure to use"),
    "3810243": ("Manglende overholdelse af pålagt underretningspligt jf. udlændingeloven",
                "Non-compliance with imposed duty of notification under the Aliens Act"),
}

with open("MASTER_CATEGORY_MAPPINGS.csv", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

n = 0
seen = set()
for r in rows:
    if r["category"] == "SOC_ger7" and r["value"] in FIX:
        exp_da, new_en = FIX[r["value"]]
        if r["description_da"].strip() != exp_da:
            sys.exit(f"FATAL: da drift on {r['value']}: {r['description_da']!r}")
        r["description_en"] = new_en
        seen.add(r["value"])
        n += 1

missing = set(FIX) - seen
if missing:
    sys.exit(f"FATAL: values not found: {sorted(missing)}")

with open("MASTER_CATEGORY_MAPPINGS.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print(f"fixed {n} SOC_ger7 partial translations")
