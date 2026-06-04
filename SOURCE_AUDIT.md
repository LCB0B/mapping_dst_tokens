# Source audit — `source=none|generated` categories (check-only, 2026-06-04)

Verification of the categories whose labels were tagged `source=none|generated`
(the same risk pattern that produced the HEA VOLTYPECODE hallucination, see
`QC_REPORT.md` §8). **No data was changed** — this records the authoritative
source for each so a later fill can cite it, plus the verdict on the current text.

Verdict legend: **WRONG** = current label is a hallucination · **CORRECT/untagged**
= label matches the source but `source` is still `none|generated` · **FILLABLE** =
empty placeholder that the cited source can fill · **UNVERIFIED** = source/variable
identified but value set not retrieved, do not assert the current label.

---

## SOC_frakkod — DST `AFG_FRAKKOD` (KRAF / Kriminalstatistik)
**Authoritative source (CONFIRMED):** DST TIMES variable **`AFG_FRAKKOD`** in the
**Kriminalstatistik (KRAF)** register — *"Frakendelsens paragraf i lovgivningen"*
("which paragraph in the Road Traffic Act or other special laws a deprivation of
driving licence, entry ban, etc. has been sentenced under").
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakkod>
The variable's table is **`D281700.TXT_FRAKKOD`** — i.e. the repo file
`raw/SOC_frakkod.txt` (same header) *is* the extracted `AFG_FRAKKOD` value set.
So both agree. 177/186 rows are already sourced as `raw_soc_frakkod`; only 5
`none|generated` + 4 `none|generated|generated` are unsourced. DST confirms the codes
(e.g. "ÅA, ÅB, ÅC, ÅD created in 2015 … alcohol lock scheme").

**Verdict: WRONG (hallucinated as prison terms).** `frakkod` is about deprivation
of *rights* — driving-licence disqualification, alcohol-interlock scheme, residence
bans — not imprisonment. The 5 codes exist verbatim in the source file with entirely
different meanings:

| Code | MASTER (hallucinated) | `raw/SOC_frakkod.txt` (authoritative) |
|------|----------------------|----------------------------------------|
| `ÅA` | Open imprisonment | Alkolås jf. færdselslovens § 60a, stk. 3 (obligatorisk ordning) |
| `ÅB` | Open, with limited community | Alkolås jf. færdselslovens § 132a, stk. 1 (frivillig ordning) |
| `ÅC` | Open imprisonment, arrest dept. | Udtrådt af alkolåsordningen |
| `UØ` | Unwanted/expelled | Førerretsfrakendelse jf. færdsl. § 126, stk. 1, nr. 7, jf. § 125, stk. 2 + selvstændig frak. |
| `UÅ` | Unopened prison | Førerretsfrakendelse jf. færdsl. § 126, stk. 1, nr. 7, jf. § 125, stk. 3 |

**✅ FIXED 2026-06-04** (`scripts/fix_soc_frakkod.py`): 7 codes (`ÅA ÅB ÅC UØ UÅ UÆ
ØA`) rewritten with verbatim Danish from `raw/SOC_frakkod.txt` + translated English,
`source=raw_soc_frakkod`, `description_en_source=translated`, `confidence=high`. The
2 remaining (`FF`, `36`) are **not in the AFG_FRAKKOD value set** → marked
`[Unresolved …]` / `low` (their old "Withdrawal code" labels were guesses; not
invented). SOC_frakkod is now 184 sourced + 2 honest unresolved.

---

## SOC_ger7 — offence codes
**Authoritative source (in repo):** `mapping/lookup_dictionaries/SOC_ger7_dict.csv`
(4-digit offence codes, hierarchical) + DST Kriminalstatistik "overtrædelsens art"
hovedgrupper. 920/938 rows already sourced (`CSV:SOC_ger7*`).

**Verdict: no hallucination.**
- 2-digit group codes `11`/`12`/`13`/`14`/`38` (Sædeligheds-/Volds-/Ejendoms-/Andre
  straffelovs-/Særlovs-forbrydelser) are **CORRECT/untagged** — consistent with the
  dict's 11xx/12xx… blocks and the standard DST main groups.
- The long 7-digit detail codes (`1146000`, `4010825`, `4020515`, …) carry honest
  placeholders ("Criminal offense code X"), not guesses; they are not in the 4-digit
  dict → **unresolved but not wrong**.

**Action (later):** tag the 5 group codes to `CSV:SOC_ger7_dict`; detail codes need a
fuller GER source (DST) — leave as honest placeholders until then.

---

## DEM_kom — municipality / special territorial codes
**Authoritative source (in repo):** `mapping/lookup_dictionaries/DEM_kom_dict.csv`
(343/356 rows sourced `CSV:DEM_kom`) + DST kommune classification for the 9xx
territorial codes.

**Verdict: no hallucination; mixed.**
- `011` → "Told og Skattestyrelsen" is **CORRECT/untagged** (matches dict `DEM_kom_11`).
- `010`/`012`/`019` are empty placeholders that are **FILLABLE from the dict**:
  `DEM_kom_10`=Sømandsskattekontoret, `DEM_kom_12`=ATP, `DEM_kom_19`=Administrativ (Sygehusene).
- `955`/`956`/`959`/`960` (Grønland / Grønlandsk kommune / Udlandet / Færøerne) are
  plausible standard special codes but **not in the repo dict** → **UNVERIFIED**, need
  DST. `957`/`958`/`004`/`007`/`009` are placeholders, not in dict.

**Action (later):** fill `010`/`012`/`019` from dict + tag `011`; verify the 9xx /
0xx special codes against the official DST kommune list before asserting.

---

## DEM_familie — `FAMILIE_TYPE`
**Authoritative source (DST):** TIMES variable **FAMILIE_TYPE** —
<https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-befolkning-og-valg/familie-type>

**Verdict: CORRECT/untagged — all 9 verified.** `type_N` maps to FAMILIE_TYPE code N
exactly:

| code | FAMILIE_TYPE (DST) | MASTER `type_N` |
|------|--------------------|-----------------|
| 1 | Ægtepar | ✓ Married couple |
| 2 | Registreret partnerskab | ✓ |
| 3 | Samlevende par | ✓ Cohabiting (common children) |
| 4 | Samboende par | ✓ Common-law (no common children) |
| 5 | Enlig (herunder også ikke hjemmeboende børn) | ✓ |
| 7 | Ægtepar forskellig køn | ✓ |
| 8 | Ægtepar samme køn | ✓ |
| 9 | Enlig | ✓ |
| 10 | Ikke hjemmeboende børn | ✓ |

**Action (later):** re-tag `source=dst_times_familie_type` (URL above); labels need no
change.

---

## EDU_udel — `UDEL` = Uddannelsesdel (KOTRE / Uddannelsesregister)
**Authoritative source (CONFIRMED):** DST TIMES variable **`UDEL`** ("Uddannelsesdel"),
the KOTRE education-part / klassetrin variable —
<https://www.dst.dk/da/Statistik/dokumentation/Times/uddannelseregister/udel>
(value set retrieved 2026-06-04).

**Verdict: CORRECT/untagged — all 24 verified verbatim.** The DST UDEL value set
matches every MASTER label exactly: `0`=Udelt uddannelse; `20`–`31`=0.–11. klassetrin;
`40`=FGU basis/spor ikke valgt; `41`=FGU spor; `51`=EUD indgangsforløb; `52`=EUD
hovedforløb; `53`=EUD indgangsforløb 1; `54`=EUD indgangsforløb 2; `55`=EUD EUX
studiekompetenceforløb; `56`=Grundforløb plus; `60`=Udelt kandidatuddannelse;
`61`=Bacheloruddannelse; `62`=Kandidatoverbygning; `64`=Akademisk overbygningsuddannelse.
Not a hallucination — labels were just untagged.

**Action (later):** re-tag `source=dst_times_udel` (URL above); labels need no change.

---

## Summary

| Category | Source | Verdict | In repo? |
|----------|--------|---------|----------|
| SOC_frakkod (5+4) | DST `AFG_FRAKKOD` (KRAF) = `raw/SOC_frakkod.txt` | **✅ FIXED** (7 sourced, 2 unresolved) | ✅ |
| SOC_ger7 (18) | `SOC_ger7_dict.csv` + DST kriminalstatistik | correct groups / honest placeholders | ✅ (groups) |
| DEM_kom (13) | `DEM_kom_dict.csv` + DST kommune list | correct/fillable; 9xx need DST | ✅ (most) |
| DEM_familie (9) | DST TIMES FAMILIE_TYPE | **CORRECT — all 9 verified** | ❌ (DST URL) |
| EDU_udel (25) | DST TIMES `UDEL` (KOTRE) | **CORRECT — all 24 verified verbatim** | ❌ (DST URL) |

Only **SOC_frakkod (5 rows)** are actually wrong. The rest are correct-but-untagged,
fillable-from-dict, or source-identified-pending-value-set. No fixes applied here
(check-only run).
