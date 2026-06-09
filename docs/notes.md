# Notes on Danish Classifications in This Repo

## 1. `DB07` is NOT `DISCO-07`

Point of confusion: the `07` in `DB07` refers to the **year 2007**, when Denmark adopted the NACE Rev. 2 industry classification. It has nothing to do with DISCO.

| Name | Classifies | International parent | Year adopted |
|---|---|---|---|
| **DB07** (Dansk Branchekode 2007) | **Industries** (retail, manufacturing, hospitals) | NACE Rev. 2 | 2007 |
| **NACE Rev 1.1** / *branche* | Industries (older) | NACE Rev 1.1 | 1992–2007 |
| **DISCO-08** | **Occupations** (nurse, programmer, electrician) | ISCO-08 | 2011 |
| **DISCO-88** | Occupations (older) | ISCO-88 | 1996–2009 (per DST documentation) |

**There is no DISCO-07.** Denmark went from DISCO-88 → DISCO-08 (jump of 20 in the year), not through a "DISCO-07" intermediate.

In this repo:
- `LAB_db07_*` = **industries** (DB07)
- `LAB_nace_*` = **industries** (NACE Rev 1.1, 1992–2007)
- `LAB_branche_*` = **industries** (branche77, even older)
- `LAB_disco08_*` = **occupations** (DISCO-08)
- `LAB_disco_*` = **occupations** — see version-drift caveat below

---

## 2. What `LAB_disco` actually is (and the version-drift story)

DST officially publishes **two** DISCO versions:

| Version | Validity | Matches | DST page |
|---|---|---|---|
| DISCO-88, v1:1996 | 1996–01–01 → 2009–12–31 | ISCO-88 | [dst.dk/.../disco?id=5d292535…](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco?id=5d292535-2f1f-4225-87e8-0b551d72cd2c) |
| DISCO-08, v1:2010 | 2010–01–01 → present | ISCO-08 | [dst.dk/.../disco](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco) |

Both DISCO-88 and DISCO-08 CSVs are now saved to `raw/dst_downloads/`:
- `disco88_dst.csv` (520 codes, 4-digit max)
- *(DISCO-08 is in the existing `raw/LAB_disco.csv`)*

### Three Danish-description files in the repo — all supposedly "DISCO"

| File | Codes | What we thought it was | What it actually is |
|---|---|---|---|
| `lookup_dictionaries/LAB_disco_dict_from_raw.csv` | 1,165 | The older DISCO (DISCO-88) | **Actually DISCO-08 Danish descriptions under an "older" label** |
| `raw/LAB_disco_codes.txt` | 794 | A DISCO version | Appears to be DISCO-88 (1996 version) |
| `raw/LAB_disco.csv` | 1,172 | DISCO-08 | DISCO-08 (confirmed) |

### Why 149 rows had wrong "official" English

Earlier we populated `description_en_official` for `LAB_disco` rows via **ISCO-88** 4-digit-prefix lookup, assuming the `LAB_disco` category meant "older DISCO = DISCO-88". That gave wrong answers for the subset of rows where MASTER's `description_da` was actually a DISCO-08 description at a DISCO-08 code.

**Concrete example: `LAB_disco_314100`**

| Source | 314100 means |
|---|---|
| MASTER `description_da` (what the training data means) | "Teknikerarbejde inden for biovidenskab" *(Bioscience technician)* — this is **DISCO-08 3141** "Life science technicians (excluding medical)" |
| `LAB_disco_codes.txt` 314100 | "Teknisk arbejde om bord på skibe" *(Technical work on ships)* — this is **DISCO-88 3141** "Ships' engineers" |
| Our first ISCO-88 lookup | "Ships' engineers" — **WRONG** because MASTER is actually DISCO-08 numbered |

The same 4-digit code `3141` means entirely different occupations in DISCO-88 vs DISCO-08. The re-numbering happened in the 2010 reform.

### Fix applied (name-based crosswalk)

`scripts/oneoff/crosswalk_lab_disco.py` detects per-row which version each `LAB_disco` row is actually in:

1. If `description_da` exactly matches DISCO-08's Danish at the same numeric code → use **ISCO-08** for the official English.
2. Else if it matches DISCO-88's Danish at the same code → use **ISCO-88**.
3. Else try fuzzy name-match ≥ 0.90 against both DISCO Danish dictionaries.
4. Else leave `description_en_official` empty.

**Result: all 149 previously-misclassified rows resolved to DISCO-08** — meaning MASTER's `LAB_disco` category actually contains DISCO-08 codes (mixed with some DISCO-88 — the boundary varies by row). The English labels from ISCO-08 are now correct.

| LAB_disco row source (detected) | Count |
|---|---|
| Uses DISCO-08 numbering + descriptions | ~168 previously known + 149 just fixed = **317** |
| Uses DISCO-88 numbering | 642 (were already correctly linked to ISCO-88) |
| Fuzzy-matched (either version) | 0 |

So the `LAB_disco` category name is somewhat misleading — it's really "DISCO occupations, mixed era". Every row now has either a reliable ISCO-08 or ISCO-88 English title, and `description_en_source` tags which.

### Why we don't overwrite `description_da`

MASTER's Danish descriptions are the **ground truth** for what the training data means. Changing them to match some "official" DST description would silently re-label every training record linked to that token. The translation (`description_en`) should follow the Danish; the "official" label (`description_en_official`) must be reconciled via code OR name matching without mutating the Danish.

---

## 3. HEA_speciale and regional §2-aftaler

### Background
`HEA_speciale` covers the Danish Sygesikringsregisteret — provider billing codes from GP / specialist / lab services. The value is structured as **specialty + procedure**:

- 6-digit codes (post-2005): first 2 digits = specialty (e.g., `80` = Almen Lægehjælp / GP), last 4 digits = procedure
- 5-digit codes (pre-2005): first 1 digit = specialty, last 4 digits = procedure

### National vs regional codes
Procedure codes below `4000` and specific named ranges are **nationally defined** in the central Overenskomst (fee schedule) between RLTN (Regionernes Lønnings- og Takstnævn) and PLO (Praktiserende Lægers Organisation). Procedures above `4000` are typically **§2-aftaler** — regional agreements negotiated independently between each of Denmark's 5 regions and its regional PLO branch. Some are also tied to specific counties (pre-2007 amter) or municipalities.

Sources for the regional codes are listed per region in `raw/dst_downloads/regional_p2_codes.csv`. Covered so far:

| Region | Codes captured | Key documents |
|---|---|---|
| Sjælland | ~39 | [§2-aftaler overview](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/sjaelland/almen-praksis/klinikadministration/aftaler/paragraf-to-aftaler/) + [ydelseskoder PDF](https://www.sundhed.dk/content/cms/31/79431_paragraf-2-aftaler-ydelseskoder.pdf) |
| Syddanmark | ~54 | [§2-oversigt](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/syddanmark/almen-praksis/klinikadministration/aftaler/paragraf-2-aftaler/paragraf-2-aftaler-oversigt/) |
| Hovedstaden | ~30 | [laeger.dk PLO-H](https://laeger.dk/foreninger/plo/overenskomsten-og-aftaler/kommunale-og-regionale-aftaler/aftaler-i-region-hovedstaden) |
| Midtjylland | ~24 | [sundhed.dk Midtjylland takster](https://www.sundhed.dk/sundhedsfaglig/information-til-praksis/midtjylland/almen-praksis/regionalt/lokalaftaler/takster/) |
| Nordjylland | 0 (not yet consolidated) | [laeger.dk PLO-N](https://laeger.dk/foreninger/plo/overenskomsten-og-aftaler/kommunale-og-regionale-aftaler/aftaler-i-region-nordjylland) |

### Code overlap between regions

Three types:

1. **Same concept, different codes** (common, non-problematic) — e.g., "opfølgende hjemmebesøg" (follow-up home visit) uses `4230-4268` in Sjælland, `4250-4253` in Hovedstaden, `4676/4688-4693` in Syddanmark, `4213-4216` in Midtjylland. Each code maps 1-to-1 to its region.

2. **Same code, same meaning** (national code adopted in multiple §2-aftaler) — e.g., the DD2 (Type 2 Diabetes Research Database) project uses codes `4612`–`4615` nationally; Syddanmark and Midtjylland both reference them with the same semantics.

3. **Same code, DIFFERENT meaning** (genuinely problematic) — same 4-digit procedure means different things in different regions. Known cases:

| Code | Region A | Region B |
|---|---|---|
| `4657` | Syddanmark: "Samtale med pårørende" | Hovedstaden: "Konsultation i stedet for hjemmebesøg (Palliation)" |
| `4612` | Syddanmark: "DD2 model 1, komplet indrullering" | Midtjylland: "DD2 model 1 fuld pakke" (same, slight rewording) |
| `4614` | Syddanmark: "DD2 model 3 henvisning" | Midtjylland: "DD2 model 3 henviser videre" (same concept) |
| `4615` | Syddanmark: "DD2 model 4, delvis indrullering" | Midtjylland: "DD2 blodprøve og forsendelse" **(genuinely different)** |

### How we handle conflicts in MASTER

Each MASTER row has a **single** `description_da` (because each token ID must have one meaning). For codes with real regional conflicts we:

1. Put one region's meaning in `description_da` (tagged with `(regional §2-aftale, Region X)` in the description itself for traceability).
2. Record the alternative(s) in a new `description_da_alt` column. Example for `HEA_speciale_804657`:
   - `description_da`: "Almen Lægehjælp 80, Samtale med pårørende (regional §2-aftale, Region Syddanmark)"
   - `description_da_alt`: "[Syddanmark] Samtale med pårørende (Alvorligt syge og døende); [Hovedstaden] Konsultation i stedet for hjemmebesøg (Palliation)"

This preserves the polysemy without breaking the one-row-per-token contract. Downstream consumers that care about regional disambiguation can inspect `description_da_alt`.

### Fundamental limitation
The training data itself carries **one token ID per 6-digit code** — billing records from all 5 regions for the same code collapse to a single embedding. If region-sensitive analysis matters downstream, the tokenization pipeline would need a region suffix (`HEA_speciale_804657_syd` vs `_hov`). This is an upstream schema change beyond the scope of this repo.

## 4. The `.0` float duplicate bug (fixed) {#section-dot0}

`vocab.json` and `vocab_2.json` originally contained 769 codes ending in `.0`:

| Type | Count | Resolution |
|---|---|---|
| **Twins** (both `X` and `X.0` existed, identical descriptions) | 736 | Deleted the `.0` entries. Token IDs now have 736 holes (1.8%). |
| **Orphans** (only `X.0` existed) | 33 | Renamed `X.0` → `X`. Token IDs preserved. |

**Upstream preprocessing still needed** — any future record that serializes a numeric code with trailing `.0` must be normalised to int-string before tokenizer lookup:

```python
s = str(value)
if s.endswith(".0"):
    s = s[:-2]
```

---

## 4b. HEA drug-volume categories are LMDB VOLUME/VOLTYPECODE (not procedure codes)

The 13 HEA categories `DDK, DW, DWG, DWK, GA, GI, GP, L, MG, ML, PK, ST, TU` (+ the
bare `HEA_`) were originally labelled "procedure codes" and filled with invented
clinical meanings (`HEA_GA`="gestational age", `HEA_MG`="specialist visits",
`HEA_ML`="lab tests", `HEA_ST`="inpatient days", `HEA_L`="medication prescriptions",
`HEA_DW`="DW diagnosis code prefix", …), all `source=none|generated`. **All wrong** —
classic HARD-RULES hallucination (plausible medical phrase guessed from the abbrev).

They are the **`VOLTYPECODE`** unit types for the **`VOLUME`** variable in the
Lægemiddeldatabasen (LMDB). VOLUME = numeric quantity of one medicine package, only
interpretable with its unit; the `manual_bin_*`/`over_1000` values are binned VOLUME
ranges in that unit. The 13 prefixes match the official VOLTYPECODE value set
one-for-one; the bare `HEA_` (token 10278, interleaved in the volume-bin token block)
is the blank VOLTYPECODE (non-specific medicine/quantity/fee/veterinary).

Unit map (verbatim VOLTYPETXT): DDK=DøgnDosis DK, DW=DDD WHO Index,
DWG=DDD WHO Guidelines, DWK=DDD WHO Kombinationsliste, GA=g (aktivt stof),
GI=g (iod), GP=g (præparat), L=L, MG=mg (aktivt stof), ML=ml, PK=pakninger,
ST=Stk, TU=tusind enheder.

Source: esundhed.dk Lægemiddelstatistikregisteret docs `rid=14&tid=63&vid=396`
(VOLTYPECODE) / `vid=399` (VOLUME). Fixed 2026-06-04 by
`scripts/oneoff/fix_hea_volume_voltypecode.py` (168 rows; `source=esundhed:lmdb_voltypecode`,
`description_en_source=dst-lmdb-voltypecode`, confidence high/medium).

---

## 5. MASTER column schema

| Column | Meaning |
|---|---|
| `description_da` | Danish, authoritative — follows the training-data semantics |
| `description_da_alt` | Alternative regional meanings (populated only for the ~4 HEA_speciale codes with conflicting §2-aftale semantics across regions — see §3) |
| `description_en` | Best-available English — translated from Danish **or** taken from an international classification |
| `description_en_official` | English only when traceable to an international standard (WHO / NACE / ISCO / ISO-3166 / DST SSR specialty). Empty when not available or not reliable. |
| `description_en_official_source` | Which authority the official English came from: `who-icd10`, `who-atc`, `nace2`, `nace2-crosswalk`, `isco08`, `isco08-crosswalk`, `isco88`, `iso3166`, `dst-ssr-specialty` |
| `description_en_source` | Provenance tag for `description_en`: same values + `translated`, `copy-of-da`, `empty` |

Consumers needing guaranteed accuracy should filter on `description_en_official`. Consumers needing broad coverage should use `description_en` and treat `description_en_source` as a quality signal.

---

## 6. External files downloaded — all under `raw/dst_downloads/`

| File | Source | Codes | Used for |
|---|---|---|---|
| `db07_v2_2013.csv` | [dst.dk DB07](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/db07) | 1,725 | LAB_db07 Danish descriptions |
| `ger7.csv` | dst.dk AFG_GER7 (HTML-scraped) | 1,263 | SOC_ger7 Danish descriptions |
| `speciale_dst_full.xlsx` | dst.dk SPECIALE ydelser | 15,957 | HEA_speciale verification |
| `audd_ddu_full.csv` | dst.dk DDU-AUDD | 4,704 | AUDD verification |
| `audd_disced15.csv` | dst.dk DISCED-15-AUDD | 5,398 | AUDD verification |
| `disco88_dst.csv` | [dst.dk DISCO-88 v1:1996](https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/disco?id=5d292535-2f1f-4225-87e8-0b551d72cd2c) | 520 | DISCO-88 reference |
| `icd10_who_2019_en.csv` | [icdcdn.who.int ClaML 2019](https://icdcdn.who.int/icd10/index.html) | 11,539 | HEA_ICD10 English (authoritative) |
| `atc_who_2021_en.csv` | [github.com/fabkury/atcd](https://github.com/fabkury/atcd) | 6,440 | HEA_atc English (authoritative) |
| `nace_rev2_en.csv` | [vincentarelbundock Rdatasets](https://vincentarelbundock.github.io/Rdatasets/doc/validate/nace_rev2.html) | 996 | LAB_db07 English |
| `isco08_en.csv` | GitHub gist + manual major groups | 619 | LAB_disco08 English + LAB_disco crosswalk |
| `isco88_en.csv` | Warwick IER xls + manual major groups | 519 | LAB_disco English |

---

## HEA_patienttype — all 4 codes were inverted

Discovered during per-category English audit. The LPR (Landspatientregisteret)
`c_pattype` variable from Sundhedsdatastyrelsen defines patient
administrative type. The original descriptions in MASTER (from
`source=none|generated`, i.e. guessed during initial vocab build) had all four
codes mapped to the wrong labels.

Authoritative source: [esundhed.dk c_pattype documentation](https://www.esundhed.dk/Dokumentation/DocumentationExtended?id=5)
(Sundhedsdatastyrelsen / Danish Health Data Authority).

| Code | Danish (authoritative) | Old (wrong) EN | New (correct) EN |
|---|---|---|---|
| 0 | Heldøgnspatient | Outpatient ❌ | **Inpatient (stationary admission)** |
| 1 | Deldøgnspatient | Inpatient ❌ | **Day/half-day patient (discontinued 2002)** |
| 2 | Ambulant patient | Emergency ❌ | **Outpatient (from 2014 also includes emergency with acute admission)** |
| 3 | Skadestuepatient | Ambulatory ❌ | **Emergency room patient (discontinued 2014)** |

Notes on the DST timeline:
- 1977–1993: only code 0 (inpatient) was registered even though other codes existed
- After 2002: code 1 (day patient) discontinued — institutions now code as
  either inpatient or outpatient
- 2014: code 3 (emergency room) was folded into code 2 (outpatient) with the
  admission-mode flag `c_indm=1` (acute) used to distinguish ER visits.

`description_en_source` is now `dst_lpr_c_pattype` and `confidence_level=high`.

## LAB income quantile translations — 14 categories rewritten

Found during the 2026-04-19 audit pass. The LAB income quantile categories
(Q1–Q100) had been translated by MT without consulting DST TIMES variable
documentation. Several had catastrophic mistranslations.

Authoritative source for each: `https://www.dst.dk/da/Statistik/dokumentation/Times/personindkomst/<varname>`

| Category (variable) | Old (wrong) EN | New (DST authoritative) |
|---|---|---|
| LAB_skatmvialt (`skatmvialt_13`) | "Tax-deductible maintenance payments" ❌ | **Total taxes, labor market contribution and special pension (excl. church tax)** |
| LAB_ovrig (`ovrig_dagpenge_akas_13`) | "Other labor income" ❌ | **Other unemployment benefits from A-kasses (excl. efterløn, regular unemployment benefit, training allowance)** |
| LAB_korstoett (`korstoett`) | "Housing insurance and housing benefit" ❌ | **Housing benefit (tenants) and housing allowance (pensioners)** — insurance→benefit mistranslation of *Boligsikring* |
| LAB_lejev (`lejev_egen_bolig`) | "Rental income" ❌ | **Imputed rental value of own dwelling** — it's an imputed value for homeowners, not actual rental income |
| LAB_syg (`syg_barsel_13`) | "Sick pay benefits" | **Sick leave and maternity benefits (paid by municipalities)** — was missing the maternity half |
| LAB_folkefortid (`folkefortid_13`) | "Early retirement pension" | **State pension (folkepension) and disability pension (førtidspension), etc.** — førtidspension ≠ early retirement, it's disability; folkepension was missing |
| LAB_bredt (`bredt_loen_beloeb`) | "Broad income measure" | **Broad wage amount (incl. ATP and employee benefits)** — it's wages, not income |
| LAB_dagpenge (`dagpenge_kontant_13`) | "Unemployment benefits" | **Unemployment and cash benefits etc. combined (dagpenge, kontanthjælp, sygedagpenge, barsel)** |
| LAB_korydial (`korydial`) | "after registration for the entire calendar year" | **annualized to full calendar year** — *opregning* = annualization, not registration |
| LAB_perindkialt (`perindkialt_13`) | "Personal income total" | **Total personal income (excl. imputed rental value of own dwelling)** |
| LAB_privat (`privat_pension_13`) | "Private income/pensions" | **Paid-out private pensions** — the "income" part was extraneous |
| LAB_netovskud (`netovskud_13`) | "Net surplus/profit" | **Net profit from self-employment** |
| LAB_offpens (`offpens_efterlon_13`) | "Public pensions" | **State pension, disability pension, heating allowance, efterløn and flex benefit** |
| LAB_resuink (`resuink_13`) | "Residual income" | **Residual income (including child support)** |

All 28 income categories now have `description_en_source=dst_times_<variable>`
so each can be verified against its DST TIMES page. `description_da` was also
populated with the authoritative DST Danish name (previously empty).

Loanwords intentionally retained in the English: `efterløn`, `dagpenge`,
`kontanthjælp`, `førtidspension`, `folkepension`, `A-kasser`, `fleksydelse` —
these Danish welfare terms don't have clean English equivalents and are kept
as loanwords (like how "kindergarten" is retained in English).

## 7. Summary of corrections to MASTER

- **1,420** mojibake rows in HEA_speciale repaired (MacRoman-as-Latin1 bytes restored to proper Danish)
- **2,485** HEA_ICD10 rows gained WHO English via `D`-prefix code mapping
- **668** HEA_atc rows gained WHO English (composed `<class>, <substance>`)
- **1,347** LAB_db07 English filled from NACE Rev 2 (4-digit prefix)
- **707** LAB_disco08 English filled from ISCO-08 (4-digit prefix)
- **610** LAB_disco English filled from ISCO-88 (4-digit prefix)
- **149** LAB_disco rows re-resolved via name-based crosswalk to **ISCO-08** after discovering they were DISCO-08 codes mislabelled as "older DISCO"
- **667** SOC_ger7 rows translated with rule-based Danish→English (a few dozen partials remain)
- **736** `.0` duplicate vocab entries removed, **33** orphan floats renamed to int

Final state: 40,465 rows, 99.94% have English descriptions, 43% have authoritative `description_en_official`, 0 mojibake, 0 `.0` keys in vocab.
