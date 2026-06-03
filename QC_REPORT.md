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
| `[Unresolved]` — `LAB_socio` (`gl_*`) | 34 | **Source exists but ambiguous.** Only `raw/dst_socio_1997.pdf` covers old SOCIO; no `.pt`/`.csv` dict. PDF text extraction is noisy and 1- vs 2-digit / socioeconomic-vs-occupation code semantics are unclear. → **needs careful human-verified PDF reading** before any fill (high hallucination risk). |
| empty `description_da` | 1,420 | Mostly numeric/quantile categories (EDU_course 163, DEM_birthyear 158, EDU_grade 143, DEM_vaegt 100, EDU_ects 100, EDU_wellbeing 60, DEM_laengde 52, EDU_dage* ~115, LAB_tilstand 22). English present (100%). Danish fillable from the same source as the English for quantile cats; some self-evident (birthyear). Low risk, optional polish. |
| `SOC_ger7` partials | **0** | Already complete — `description_en` 100% filled (938/938). |
| Region Nordjylland §2 | 0 captured | Needs laeger.dk PLO-N source (not yet downloaded). |

## 5. Recommendation for Phase 3
- **Leave the 36 DB07 5-digit `[Unresolved]`** — correct per HARD RULES; flag for DST retrieval.
- **SOCIO_gl (34):** only attempt with human-verified reading of `raw/dst_socio_1997.pdf`; otherwise leave `[Unresolved]`.
- **empty `description_da` (1,420):** safe to fill the quantile/numeric categories from their existing (sourced) English + DST TIMES, citing source; defer anything not source-backed.
