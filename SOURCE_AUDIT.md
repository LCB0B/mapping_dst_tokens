# Source audit — `source=none|generated` categories (2026-06-04)

Verification of the categories whose labels were tagged `source=none|generated`
(the same risk pattern that produced the HEA VOLTYPECODE hallucination, see
`QC_REPORT.md` §8). Records the authoritative source for each, the verdict on the
current text, and — where a fix was applied — the commit. Entries marked **✅ FIXED**
have been corrected in MASTER; the rest are verified-correct/untagged or unresolved.

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
- `955`–`960` = **RESOLVED: the modern Greenland municipalities** (2009 reform + 2018
  split), which is why they are absent from the dict's *old* Greenland list `901`–`953`
  — the vocab spans both eras. Sources: cpr.dk Grønland-2018 (authoritative for 958/959/960)
  <https://www.cpr.dk/cpr-systemet/aendringer/kommunesammenlaegninger-opdeling/groenland-2018>
  + stat.gl / 2009-reform docs (955/956/957). **Two current labels are WRONG:**

  | code | MASTER (wrong/vague) | authoritative |
  |------|----------------------|----------------|
  | 955 | "Grønland" (vague) | Kommune Kujalleq |
  | 956 | "Grønlandsk kommune" (vague) | Kommuneqarfik Sermersooq |
  | 957 | *(empty)* | Qeqqata Kommunia |
  | 958 | *(empty)* | Qaasuitsup Kommunia (2009–2017) |
  | 959 | ❌ "Udlandet (Abroad)" | **Kommune Qeqertalik** (2018–) |
  | 960 | ❌ "Færøerne (Faroe Islands)" | **Avannaata Kommunia** (2018–) |

- `004`/`007`/`009`: still **UNRESOLVED** — in the administrative/tax 0xx family
  (cf. `10`=Sømandsskattekontoret, `11`=Told og Skattestyrelsen, `12`=ATP,
  `19`=Administrativ (Sygehusene); CPR uses 0010–0019 for persons without residence
  assigned a CPR no. for tax reasons), but the specific labels for 004/007/009 were not
  found in any source. Need DST Forskningsservice / original `.pt`. (Note: there is **no**
  Færøerne or Udlandet code among 955–960 — those MASTER labels were hallucinated.)

**Action (later):** (a) fix `955`–`960` to the Greenland municipality names above
(`source=cpr_groenland` / `dst-kom`, conf high); (b) fill `010`/`012`/`019` + tag `011`
from DST KOM/dict; (c) leave `004`/`007`/`009` flagged unresolved pending DST.

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

## SOC_haendelse — DST `HAENDELSE` (Udsatte børn og unge / BUAF) — NOT criminal

**Authoritative source (CONFIRMED):** DST TIMES variable **`HAENDELSE`**, table
`D280601.TXT_ANB_HAENDELSE` = *"Hændelse i anbringelsessag"* — events in an out-of-home
**placement** (anbringelse) case for vulnerable children/youth. **Not** a criminal-event
code. <https://www.dst.dk/da/Statistik/dokumentation/Times/boern-og-unge/haendelse>
(+ repo `raw/SOC_haendelse.txt`, same table).

**✅ FIXED 2026-06-04** (`scripts/fix_soc_haendelse_frakbkod.py`): the decimal sub-codes
(0.2/1.1/5.5/7.5) were already sourced; the integer codes `0/1/2/5/7` had been left as
bogus *"Criminal event type: N"* and are now filled verbatim from the DST value set:
`0`=Iværksættelse af anbringelse, `1`=Iværksættelse af ændret anbringelsessted,
`2`=Ændring af tvangsanbringelse til frivillig anbringelse, `5`=Hjemgivelse/ophør af
anbringelse, `7`=Iværksættelse/genetablering af efterværn. `confidence=high`. (The
category prefix `SOC_` is a misnomer — this is child-welfare, not crime — but codes/IDs
untouched.)

## SOC_frakbkod — DST `AFG_FRAKBKOD` (KRAF)

**Authoritative source (CONFIRMED, fetched twice):** DST TIMES **`AFG_FRAKBKOD`** —
code indicating whether a frakendelse (e.g. driving licence) is *"for bestandig"*
(permanent). <https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/afg-frakbkod>
Value set: `0`=Uoplyst, `1`=bestandig, `2`=endelig dom, `3`=domsdato, `4`=ikke mere bestandig.

**✅ FIXED 2026-06-04** — all 4 MASTER labels were **hallucinations** (1="Betinget
frakendelse", 2="Ubetinget", 3="Kørselsforbud", 4="Betinget med vilkår" — the variable
is about *permanent*, not betinget/ubetinget). Rewritten to the verbatim value set
(`source=dst_afg_frakbkod`, conf high).

## SOC_fgslkod — prison-institution type (KRIN) — UNVERIFIED

MASTER: `1`=Åbent fængsel, `2`=Lukket fængsel, `3`=Arresthus, `4`=Halvåbent fængsel,
`5`=Pension, `0`=placeholder. These are the standard Kriminalforsorgen institution
types and look plausible, **but the specific integer→type mapping could not be verified**
from a public source: the KRIN (Kriminalstatistik indsættelser) value sets are not
published (extranet shows only dataset metadata), and the related TIMES variable
`IND_FGSLSTED` uses **letter place-codes** (`A###` arresthuse, `F###` fængsler,
`P###` pensioner) — not these 1–5 type codes.
<https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/ind-fgslsted>
**Verdict: UNVERIFIED — left untouched.** Needs the KRIN codebook from DST
Forskningsservice / the original `.pt` to confirm before asserting.

---

## Summary

| Category | Source | Verdict | In repo? |
|----------|--------|---------|----------|
| SOC_frakkod (5+4) | DST `AFG_FRAKKOD` (KRAF) = `raw/SOC_frakkod.txt` | **✅ FIXED** (7 sourced, 2 unresolved) | ✅ |
| SOC_ger7 (18) | DST `AFG_GER7` (KRAF) + `SOC_ger7_dict.csv` | groups correct (0=Uoplyst fillable; 11/14/38 wording); 1xxx need full DST list; **4xxx not valid GER7** | ✅ (groups) |
| DEM_kom (13) | DST KOM + cpr.dk Grønland + `DEM_kom_dict.csv` | **955–960 RESOLVED = modern Greenland kommuner** (959/960 were WRONG: Abroad/Faroe); 011 correct; 010/012/019 fillable; 004/007/009 still unresolved | mostly |
| DEM_familie (9) | DST TIMES FAMILIE_TYPE | **CORRECT — all 9 verified** | ❌ (DST URL) |
| EDU_udel (25) | DST TIMES `UDEL` (KOTRE) | **CORRECT — all 24 verified verbatim** | ❌ (DST URL) |
| SOC_haendelse (5) | DST `HAENDELSE` (børn og unge/BUAF) + `raw/SOC_haendelse.txt` | **✅ FIXED** — was mis-labelled "Criminal event"; it's out-of-home placement | ✅ |
| SOC_frakbkod (4) | DST `AFG_FRAKBKOD` (KRAF) | **✅ FIXED** — all 4 were hallucinated (betinget/ubetinget); var = permanent-or-not | ❌ (DST URL) |
| SOC_fgslkod (6) | KRIN (not public) | **UNVERIFIED** — plausible prison types, integer→type mapping unconfirmed | ❌ |

**Hallucinations corrected so far:** HEA VOLTYPECODE family (168), `SOC_frakkod` (5),
`DEM_kom` 959/960 (Greenland), `SOC_frakbkod` (4), `SOC_haendelse` integer codes (5,
mis-categorised as criminal). Verified-correct-but-untagged: `EDU_udel`, `DEM_familie`,
`SOC_ger7` groups. Still unresolved (not guessed): `LAB_socio gl_*`, `LAB_db07` 5-digit,
`DEM_kom` 004/007/009, `SOC_ger7` 1xxx/4xxx, `SOC_fgslkod`, most `LAB_tilstand`.
