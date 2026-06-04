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

## SOC_ger7 — GER7 gerningskode (offence code)
**Authoritative source (CONFIRMED):** DST TIMES variable **`AFG_GER7`** (KRAF /
Kriminalstatistik – afgørelser); the same GER7 value set is shared by `KON_GER7`,
`SIG_GER7`, `OFR_GER7`, `ANM_GER7`, `IND_GER7`.
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-ger7>
GER7 = a 7-digit conversion of Rigspolitiet's 5-digit gerningskode, **hierarchical at
1 / 2 / 4 / 7 digits** (from counting-year 2020 only the first 4 digits + `000` are
maintained; `AFG_GER9` supersedes it). Repo 4-digit value set:
`mapping/lookup_dictionaries/SOC_ger7_dict.csv` (89 codes; first-digit distribution
0:1, 1:68, 2:5, 3:15 — **no 4xxx**). 920/938 rows already sourced (`CSV:SOC_ger7*`).

**Verdict (checked vs AFG_GER7, 2026-06-04): no hallucination, but notes.**
- 1-digit `0` → MASTER placeholder "Criminal offense code 0"; **DST: `0` = Uoplyst**
  (unknown). FILLABLE.
- 2-digit groups verified vs DST. `12`=Voldsforbrydelser and `13`=Ejendomsforbrydelser
  match exactly. Two use older/umbrella wording (semantically correct, can be aligned):
  `11` MASTER "Sædelighedsforbrydelser" vs DST current **"Seksualforbrydelser"**;
  `14` MASTER "Andre straffelovsforbrydelser" vs DST **"Andre forbrydelser"**;
  `38` MASTER "Særlovsovertrædelser" vs DST **"Særlove i øvrigt"** (38 is the residual
  special-law subgroup, not the whole 3x umbrella — slightly imprecise).
- 7-digit detail codes starting with **1** (`1146000`,`1465720`,`1470`,`1480505`):
  their 4-digit prefixes (1146/1465/1470/1480) are **not in the repo dict** (neighbours
  like 1145/1460/1475/1485 exist), so they are valid-looking GER7 codes from another
  vintage but **unverified** here; MASTER carries honest group placeholders, not guesses.
- Codes starting with **4** (`4010`,`4020`,`4010825`,`4010840`,`4020340`,`4020515`,
  `4020630`,`4020910`): **NOT valid GER7** — GER7's first digit is 0–3 and the dict has
  zero 4xxx codes. Anomalous (different coding or data artifact); MASTER labels are
  honest "Criminal offense code X" placeholders. **Flag — do not treat as GER7.**

**Action (later):** fill `0`=Uoplyst; tag the 2-digit groups to `AFG_GER7` and optionally
align `11`/`14`/`38` to DST current wording; obtain the full AFG_GER7 4-digit value set
to resolve the 1xxx detail codes; investigate the 4xxx codes' true origin separately.

---

## DEM_kom — municipality / special territorial codes
**Authoritative source (in repo):** `mapping/lookup_dictionaries/DEM_kom_dict.csv`
(343/356 rows sourced `CSV:DEM_kom`) + DST kommune classification for the 9xx
territorial codes.

**Authoritative source checked:** DST TIMES variable **KOM** (bopælskommune) —
<https://www.dst.dk/da/Statistik/dokumentation/Times/moduldata-for-befolkning-og-valg/kom>
— and the repo dict `DEM_kom_dict.csv` (which mirrors it).

**Verdict: no hallucination; mixed (2026-06-04, checked vs DST KOM).**
- `011` → "Told og Skattestyrelsen" **CORRECT/untagged** (matches DST KOM / dict `DEM_kom_11`).
- `010`/`012`/`019` are empty placeholders, **FILLABLE** and confirmed by DST KOM + dict:
  `10`=Sømandsskattekontoret, `12`=ATP, `19`=Administrativ (Sygehusene).
- `955`/`956`/`957`/`958`/`959`/`960` and `004`/`007`/`009`: **NOT in the DST KOM value
  set nor the repo dict** → **UNVERIFIED**. DST KOM codes Greenland as `901`–`953`
  (Christianshåb, Godthåb, Jakobshavn, Thule, Angmagssalik, Scoresbysund, …) and uses
  `961`=Udenfor kommunal inddeling / `999`=Uoplyst kommune for special cases — there is
  **no 955–960 in standard KOM**. So the current `955`=Grønland / `960`=Færøerne /
  `959`=Udlandet labels are plausible but come from a non-standard/older coding; **do
  not assert**. Need DST Forskningsservice or the original `.pt`.

**Action (later):** fill `010`/`012`/`019` from DST KOM/dict + tag `011`; leave the
9xx + `004`/`007`/`009` flagged unverified pending DST.

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
| SOC_ger7 (18) | DST `AFG_GER7` (KRAF) + `SOC_ger7_dict.csv` | groups correct (0=Uoplyst fillable; 11/14/38 wording); 1xxx need full DST list; **4xxx not valid GER7** | ✅ (groups) |
| DEM_kom (13) | DST KOM + `DEM_kom_dict.csv` | 011 correct; 010/012/019 fillable; 9xx + 004/007/009 NOT in KOM → unverified | partial |
| DEM_familie (9) | DST TIMES FAMILIE_TYPE | **CORRECT — all 9 verified** | ❌ (DST URL) |
| EDU_udel (25) | DST TIMES `UDEL` (KOTRE) | **CORRECT — all 24 verified verbatim** | ❌ (DST URL) |

Only **SOC_frakkod (5 rows)** are actually wrong. The rest are correct-but-untagged,
fillable-from-dict, or source-identified-pending-value-set. No fixes applied here
(check-only run).
