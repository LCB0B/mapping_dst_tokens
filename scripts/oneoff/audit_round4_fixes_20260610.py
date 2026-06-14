#!/usr/bin/env python3
"""Audit round-4 fixes (2026-06-10).

Findings from auditing axes not previously covered (tier-1 dict agreement,
translation digit-preservation, prevalence internals, summary staleness):

1. LAB_socio13_135: register validity dates had leaked into the English and
   the text was duplicated ('Other wage earners 01-01-1600 31-12-9999 Other
   wage earners').
2. HEA_ICD10_Y8609 (ICD-8): the English was truncated to '(born on the sgh)'.
   Re-translated from the Danish ('Levendef. trill.,firl.,etc.en el.fl.dødf.
   (født på sgh)' — levendefødt trilling/firling, en eller flere dødfødte,
   født på sygehus). Also fills the one missing description_short in MASTER.
3. 13 SOC_afgtypko rows tagged 'translated' whose English was the untranslated
   Danish statute shorthand ('Rpl p.723, stk.1, nr.2'). Rendered as English
   citations to Retsplejeloven (the Administration of Justice Act), keyed by
   value with the Danish asserted.

Checked in the same round, no change needed: the remaining 165 da<->en digit
mismatches are benign (ordinals/degree signs written out, documented
annotations like '(discontinued 2014)'); the 79 HEA_ICD10 rows with identical
da/en are Latin terms valid in both languages; pct_people is internally
consistent (implied population 9,028,68x +/- 80 across all large tokens);
token_occurrences.csv token_id column belongs to archive/vocab_2.json
(verified 40,635/40,635) — documented in CLAUDE.md, join by token string only.

Run from the repo root; regenerate MAPPINGS/, HIERARCHY_SUMMARY.csv and
vocab_hierarchy.json afterwards.
"""

import csv
import sys

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"

AFGTYPKO = {  # value: (expected da, en rendering)
    "91": ("Rpl p.723, stk.1, nr.1", "Administration of Justice Act (Rpl) § 723(1) no. 1"),
    "92": ("Rpl p.723, stk.1, nr.2", "Administration of Justice Act (Rpl) § 723(1) no. 2"),
    "93": ("Rpl p.723, stk.1, nr.5", "Administration of Justice Act (Rpl) § 723(1) no. 5"),
    "94": ("Rpl p.723, stk.2", "Administration of Justice Act (Rpl) § 723(2)"),
    "61": ("Rpl p.723, stk.3", "Administration of Justice Act (Rpl) § 723(3)"),
    "45": ("Rpl p.723, stk.4 jf.s.1,n.3", "Administration of Justice Act (Rpl) § 723(4) cf. (1) no. 3"),
    "46": ("Rpl p.723, stk.4 jf.s.1,n.4", "Administration of Justice Act (Rpl) § 723(4) cf. (1) no. 4"),
    "47": ("Rpl p.723, stk.4 jf.s.1,n.5", "Administration of Justice Act (Rpl) § 723(4) cf. (1) no. 5"),
    "97": ("Rpl p.723, stk.4 jf.s.1,n.5", "Administration of Justice Act (Rpl) § 723(4) cf. (1) no. 5"),
    "48": ("Rpl p.723, stk.4 jf.stk.2", "Administration of Justice Act (Rpl) § 723(4) cf. (2)"),
    "50": ("Rpl p.723, stk.4 jf.stk.2", "Administration of Justice Act (Rpl) § 723(4) cf. (2)"),
    "49": ("Rpl p.723, stk.4 jf.stk.1", "Administration of Justice Act (Rpl) § 723(4) cf. (1)"),
    "51": ("Rpl p.723, stk.4 jf.stk.3", "Administration of Justice Act (Rpl) § 723(4) cf. (3)"),
}

Y8609_EN = ("Live-born triplet, quadruplet etc., one or more stillborn "
            "(born in hospital)")

with open(MASTER, newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

counts = {}


def bump(k):
    counts[k] = counts.get(k, 0) + 1


for r in rows:
    if r["code"] == "LAB_socio13_135":
        if r["description_da"].strip() != "Andre lønmodtagere":
            sys.exit(f"FATAL: da drift on socio13_135: {r['description_da']!r}")
        r["description_en"] = "Other wage earners"
        r["description_short"] = "Other wage earners"
        bump("socio13_135 date-leak fixed")
    elif r["code"] == "HEA_ICD10_Y8609":
        r["description_en"] = Y8609_EN
        r["description_short"] = Y8609_EN
        bump("Y8609 truncated en fixed")
    elif r["category"] == "SOC_afgtypko" and r["value"] in AFGTYPKO:
        exp_da, new_en = AFGTYPKO[r["value"]]
        if r["description_da"].strip() != exp_da:
            sys.exit(f"FATAL: da drift on afgtypko {r['value']}: {r['description_da']!r}")
        r["description_en"] = new_en
        r["description_short"] = new_en
        bump("afgtypko citation translated")

with open(MASTER, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for k in sorted(counts):
    print(f"{counts[k]:6d}  {k}")
print("total:", sum(counts.values()))
