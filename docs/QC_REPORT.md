# QC / Audit Report — recovered enriched mappings

**Date:** 2026-06-03 · **Branch:** `restore-enriched-mappings` · **Rows:** 40,465

This report documents the Phase-2 audit of the recovered (previously uncommitted)
enriched vocabulary mappings. Context: the originating Claude Code conversation's
transcript was lost to local retention; the work survived in the working tree and
`notes.md` and was snapshotted in commit `1ffc0b9`.

## 1. Integrity — PASS
- **Token IDs preserved:** of 40,432 keys shared with the prior `HEAD`, **0** changed token_id. The 769 removed keys are all `.0` float-duplicates; 33 orphan floats renamed to int. (Documented `.0` bug fix, `notes.md` §4.)
- **Cross-file consistency:** `vocab.json` keys = MASTER rows = Σ MAPPINGS rows = **40,465** (equal).
- **Regeneration idempotent:** after the fix in §2, `scripts/regenerate_mappings.py` reproduces MAPPINGS/ exactly from MASTER (pure function of MASTER).

## 2. Data regression found & FIXED (commit `4385216`)
Regenerating MAPPINGS/ from MASTER drifted **45 files** — MASTER had been clobbered by a late rewrite *after* the MAPPINGS were last generated, while the MAPPINGS retained the correct, sourced data. Drift was isolated to provenance/official columns (no content columns affected):

| Column | Rows MASTER had lost/degraded | Resolution |
|---|---|---|
| `description_en_official` | **6,128** (all HEA_speciale, `dst-ssr-specialty`) emptied in MASTER | restored from MAPPINGS; verified vs `raw/dst_downloads/ssr_speciale_2digit.csv` (80=Almen Lægehjælp=GP, 19=Øjenlægehjælp) |
| `description_en_official_source` | same 6,128 tags | restored |
| `description_en_source` | 6,746 flattened to generic `translated` | 3,184 upgraded to specific tags; `copy-of-da` vs `translated` recomputed objectively from `en==da` |

Net effect: `description_en_official` coverage **47.3% → 62.4%** (19,130 → 25,258). The single MASTER-ahead value (`LAB_nace_642000` "Telecommunications") was preserved. 2 DB07 rows had a both-specific source conflict (`dst_db07_127` vs `nace2`) — kept MASTER's `nace2` (correct English provenance), flagged here for review.

## 3. HARD-RULES compliance — CLEAN
- **No un-sourced hallucinations detected.** 522 rows have a filled `description_da` with a coarse `source` (`generated_pattern`); these are LAB income/quantile categories whose authoritative provenance lives in `description_en_source=dst_times_*` (per `notes.md`). The `source` column is merely coarse, not a violation.
- **Historically-damaged categories are correctly marked `[Unresolved]`, not guessed:**
  - `LAB_db07` 5-digit codes (the "wrong DB07 5-digit mappings" of repo lore): the 36 unresolved ones are marked `[Unresolved]`, not hallucinated.
  - `SOCIO_gl` (`socio_gl`): the 34 unresolved ones are marked `[Unresolved]`, not the previously-hallucinated labels. The 51 `none|generated` socio rows are accounted for (34 unresolved + 17 socio13-derived).

## 4. Gap inventory & resolvability
| Gap | Count | Resolvable from repo/DST sources? |
|---|---|---|
| `[Unresolved]` — `LAB_db07` 5-digit | 36 | **No (not without guessing).** Codes `11100`…`89900` are 5-digit; DST DB07 is 6-digit (`011100`). The leading-zero map is ambiguous (`012100`/`089900` absent). `LAB_db07_dict.csv` (3-digit) lacks them. → **needs DST / original `.pt`** (HARD RULE #5). |
| `[Unresolved]` — `LAB_socio` (`gl_*`) | 34 | **Confirmed NOT resolvable from repo sources.** Verified by reading `raw/dst_socio_1997.pdf` (Bilag 1, p.14): SOCIO-1997 codes are `1/11/111–114/12/13/131–135/2/3/31/32/321–323/33/4`. The `gl_*` values (`1–10, 21–30, 59–89`) **do not match** — `socio_gl` is the *pre-1997* "arbejdsstilling"/socioøkonomisk system the 1997 PDF replaced, and its value set is not in this PDF or any `.pt`/`.csv` dict. → **needs DST Forskningsservice or the original `.pt`** (HARD RULE #5). Do not map to SOCIO-1997. |
| empty `description_da` | 1,420 | Mostly numeric/quantile categories (EDU_course 163, DEM_birthyear 158, EDU_grade 143, DEM_vaegt 100, EDU_ects 100, EDU_wellbeing 60, DEM_laengde 52, EDU_dage* ~115, LAB_tilstand 22). English present (100%). Danish fillable from the same source as the English for quantile cats; some self-evident (birthyear). Low risk, optional polish. |
| `SOC_ger7` partials | **0** | Already complete — `description_en` 100% filled (938/938). |
| Region Nordjylland §2 | 0 captured | Needs laeger.dk PLO-N source (not yet downloaded). |

## 5. Recommendation for Phase 3
- **Leave the 36 DB07 5-digit `[Unresolved]`** — correct per HARD RULES; flag for DST retrieval.
- **SOCIO_gl (34):** investigated `raw/dst_socio_1997.pdf` — it documents the *1997* system, not the pre-1997 `gl_*` codes. **Left `[Unresolved]`; retrieve the old value set from DST Forskningsservice / original `.pt`.**
- **empty `description_da`:** DONE — 967 filled (90 by copying Danish already in `description`, 877 structural/numeric/quantile); coverage 96.5% → 98.9%. The remaining ~453 empties are `[UNMAPPED]`/placeholder/ambiguous rows, intentionally left blank.

## 6. Code & translation verification (independent cross-check vs source files)

**Source coverage — NOT 100%.** ~992 rows (2.5%) have a description but no external source: almost all are *structural* categories (exam grades, percentile/visit-count bins, quantiles) that have no external authority by nature. Plus **17 `LAB_branche` rows tagged `dse77_inferred` ("fully inferred")** — NOT in `raw/LAB_branche77.txt`, unverified guesses → now tagged **`confidence_level=low`** so they're honestly flagged.

**Cross-validation of `description_en_official` against the cited authorities:**
| Category | Result |
|---|---|
| HEA_ICD10 (who-icd10) | 8,810 exact match to WHO + 5,766 match a WHO ancestor (category/block level — coarser but valid). **0 wrong among verifiable.** 25 rows falsely claimed WHO (codes not in WHO 2019: 18× `DI84*` haemorrhoids→now K64, 7× `DVR*` Danish supplementary) — **CLEARED** (`scripts/oneoff/fix_icd_false_official.py`). |
| HEA_atc | 1,634/1,656 name-consistent with WHO ATC 2021, 0 mismatch, 22 codes absent from 2021 file (older/withdrawn). |
| HEA_speciale (official, dst-ssr) | Consistent (1 label per 2-digit specialty), matches SSR Danish (Neurokirurgi→Neurosurgery, Øjenlæge→Ophthalmology, …). A couple specialties differ from the 1990–2003 SSR file (code reuse across eras). |
| LAB_disco08 (isco08) | Correct; apparent "mismatches" are our-label-more-specific-than-major-group artifacts. |

**Translation quality (`description_en`):** 75.9% of all English is machine-translated (`description_en_source=translated`) — this is the broad-coverage field; `description_en_official` (62.4%) is the authority-verified one. MT is reliable for clean Danish (income quantiles, socio, audd all verified correct) but **unreliable for heavily-abbreviated text** — notably **`HEA_speciale` (6,051 MT rows)**, e.g. `802144` "Vejl. af svang." (counselling of pregnant women) → "Evacuation of constipation". `DEM_civst` `description_da` (7 rows) was English (its source file `raw/DEM_civst.txt` is itself English) → now **filled with the official DST Danish** (Skilt, Gift (+ separeret), Enke/Enkemand, Registreret/Ophævet partnerskab, Længstlevende af 2 partnere, Død), sourced to DST TIMES CIVST.

## 7. HEA_speciale re-translation (2026-06)

The 6,051 `HEA_speciale` machine-translated rows were re-translated in-context
(Opus 4.8) via an authored Danish medical-billing abbreviation glossary +
structural rules (`scripts/oneoff/translate_hea_speciale.py`), expanding ~3,539 unique
abbreviated procedure strings and applying back to all rows
(`scripts/oneoff/apply_hea_speciale_translations.py`).

- **New column `description_da_full`** (6,045 filled): the unabbreviated Danish.
  The abbreviated `description_da` is preserved as the authoritative register text.
- `description_en` rewritten; `description_en_source='opus-4-8-medical'`.
- The canonical failure is fixed: `802144` "Vejl. af svang." → **"Guidance in use
  of contraceptive methods by insertion of coil (IUD)"** (the PLO full text revealed
  `svang.`=*svangerskabsforebyggende*/contraceptive, not *svangre*/pregnant women —
  so the old "Evacuation of constipation" was doubly wrong). GP rows use the fuller
  `plo_gp_ydelser_merged.csv` text for `description_da_full` where available.
- **Two-stage completion.** First an authored glossary cleared the systematic ~59%.
  Then the remaining clinical tail (849 strings) was translated by a **multi-agent
  workflow** (15+ translator agents, each adversarially verified, +1 focused pass for
  109 stragglers) — see `scripts/worklists/clinical_residual.tsv`/`scripts/worklists/clinical_missing.tsv` and the
  override `scripts/worklists/hea_speciale_translations.tsv`.
- **Final grading:** `confidence_level=medium` **4,561 (75%)** = æøå-clean fluent English
  (0 medium rows contain residual Danish); `low` **1,490** = **1,289 `(procedure not
  documented)` placeholders** (no source text exists), **325 lab analyte/allergen codes**
  (KPLL/SSI — left as semi-international notation by decision), and a small remainder with
  `*marker*`/uncertainty. Of the ~4,762 rows that have a translatable procedure, **~96%
  are clean**.
- **Never invented:** opaque/placeholder codes stay `low` with best-effort partial English;
  the abbreviated `description_da` and full `description_da_full` are preserved.
- **Id-misassignment caught & fixed.** A post-merge audit found 88 rows (radiology +
  dermatology) where a workflow agent had returned translations under the wrong ids,
  corrupting those rows (e.g. a Dermato consultation showing "Surgery, haemorrhoid
  ligation"). Detected by `scripts/oneoff/validate_hea_speciale.py` (every row's `description_en`
  must start with its `description_en_official` specialty); the 88 were stripped and
  re-translated under strict id-fidelity. Final gate: **0 specialty mismatches** across
  all 6,134 rows. Run `python3 scripts/oneoff/validate_hea_speciale.py` as a regression check.
- **Medium-row verification sweep.** A detector (word shared between `description_da_full`
  and `description_en`, excluding cognates/proper nouns) flagged glossary-translated `medium`
  rows that still held a stray untranslated Danish word (e.g. `Albue`→now "elbow",
  `Plastfyld`→"plastic (composite) filling"); ~1,770 were re-translated by a review workflow.
  A second id-fidelity slip (45 Paediatrics rows) was caught by the gate and re-fixed.
- **Final tally:** medium 4,412 / low 1,639; **0 specialty mismatches** (gate clean);
  integrity `vocab=master=mappings=40,465`. Of the ~4,762 rows with a translatable procedure,
  ~93% are clean `medium`; the rest are placeholders, lab analyte notation, or honest `low`.

## 8. HEA LMDB drug-volume categories — hallucinated labels corrected (2026-06-04)

A user flag (these "HEA procedure-code prefixes" are actually drug dosage / LMDB
VOLUME + VOLTYPECODE) exposed a HARD-RULES violation that had been committed:
**168 rows** across 13 HEA categories (`DDK, DW, DWG, DWK, GA, GI, GP, L, MG, ML,
PK, ST, TU`) plus the bare `HEA_` carried invented clinical meanings — e.g.
`HEA_GA`="gestational age weeks", `HEA_MG`="specialist visits", `HEA_ML`="lab tests",
`HEA_ST`="inpatient days", `HEA_L`="medication prescriptions", `HEA_DW`="DW diagnosis
code prefix" — all tagged `source=none|generated` / `vocab_reconciliation`.

**What they really are:** the `VOLTYPECODE` unit types for the `VOLUME` variable in
DST's Lægemiddeldatabasen (LMDB / Lægemiddelstatistikregisteret). `VOLUME` = numeric
quantity of one medicine package, only meaningful together with its unit
(`VOLTYPECODE`). The `manual_bin_*`/`over_1000` values are binned VOLUME ranges in
that unit. The bare `HEA_` (token 10278, interleaved inside the volume-bin token
block) is the documented blank VOLTYPECODE (non-specific medicine/quantity/fee/
veterinary). Confirmed two ways: the 13 prefixes match the VOLTYPECODE value set
**one-for-one**, and the values are all binned quantities.

**Source (cited):** esundhed.dk · Lægemiddelstatistikregisteret · documentation
`rid=14&tid=63&vid=396` (VOLTYPECODE) / `vid=399` (VOLUME); cross-checked vs
`dst.dk/extranet/ForskningVariabellister/LMDB - Lægemiddeldatabasen.html`.

**Fix:** `scripts/oneoff/fix_hea_volume_voltypecode.py` rewrote all 168 rows
(`description`, `description_da`, `description_en`, `description_short`) to sourced
unit labels; set `source=esundhed:lmdb_voltypecode`,
`description_en_source=dst-lmdb-voltypecode`, `confidence_level=high` (13 named
categories, direct code→doc match) / `medium` (bare `HEA_`, blank-voltypecode
inference). token_id/code/value untouched; integrity `vocab=master=mappings=40,465`,
regeneration idempotent. **Not invented:** every label is the documented VOLTYPETXT.
