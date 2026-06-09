# One-off scripts

These 59 scripts performed **specific, already-applied transformations** on
`MASTER_CATEGORY_MAPPINGS.csv` (and a few on `vocab*.json`). They are kept for
provenance and reproducibility — they are **not** part of the regular
regeneration pipeline (that's the five utilities in `scripts/`).

Run them from the **repo root** (they use paths relative to it, e.g.
`raw/…`, `lookup_dictionaries/…`, `crosswalks/empirical/…`). One pair is
co-dependent: `apply_manual_translations.py` imports `manual_translations_ext.py`
(both live here, so the import resolves).

See `docs/notes.md`, `docs/QC_REPORT.md`, and `docs/SOURCE_AUDIT.md` for the
narrative of what each transformation accomplished and why.

## Index

- `add_official_en_column.py` — Add `description_en_official` and `description_en_source` columns to MASTER.
- `add_prevalence.py` — Add prevalence columns to MASTER from token_occurrences.csv.
- `add_program_groups.py` — Add program_group + is_primary_code for EDU_udd / EDU_audd version-renumbered variants.
- `apply_db07_industry_crosswalk.py` — Apply the empirical DB07-5digit → DB93/nace industry crosswalk.
- `apply_hea_speciale_translations.py` — Apply the HEA_speciale re-translations to MASTER.
- `apply_icd_translations.py` — Apply English translations to HEA_ICD10 Danish/Latin sub-codes.
- `apply_manual_translations.py` — Apply a hand-curated Danish→English dictionary to MASTER.
- `apply_regional_codes.py` — Apply regional §2-agreement codes (Hovedstaden, Sjælland, …).
- `apply_regional_overlaps.py` — Record alternative regional meanings for HEA_speciale codes.
- `apply_socio_gl_crosswalk.py` — Apply the empirical SOCIO_GL → SOCIO13 crosswalk.
- `audit_and_tag_official.py` — Audit Danish/English/official descriptions.
- `audit_description_en.py` — Audit description_en quality across all MASTER rows.
- `build_hea_speciale_worklist.py` — Build the HEA_speciale re-translation worklist.
- `build_token_hierarchy.py` — Build a hierarchical JSON of all vocabulary tokens.
- `clean_hea_speciale.py` — Clean HEA_speciale rows + add authoritative English specialty tags.
- `cleanup_socio_gl.py` — Replace hallucinated SOCIO_gl mappings with only verifiable entries.
- `crosswalk_lab_disco.py` — Name-based ISCO-88/-08 crosswalk for LAB_disco.
- `dump_batch.py` — Dump worklist rows for in-context translation.
- `dump_clinical_residual.py` — Dump residual clinical rows for review.
- `dump_residual.py` — Dump abbreviated DA + expanded da_full from worklists.
- `fill_empty_da_structural.py` — Fill empty description_da for structural/numeric/quantile categories.
- `fill_english_from_intl.py` — Fill description_en for LAB_db07/disco08/disco from intl standards.
- `fill_hierarchy_specifics.py` — Fill per-code Danish for hierarchical categories.
- `fill_icd10_atc_who.py` — Fill description_en for HEA_ICD10 + HEA_atc from WHO sources.
- `fill_undocumented_specs.py` — Fill "(procedure not documented)" HEA_speciale rows.
- `final_cleanup.py` — Final cleanup of mixed Danish/English descriptions.
- `fix_db07_and_socio_gl.py` — Fill missing descriptions for LAB_db07 + LAB_socio.
- `fix_db07_proper.py` — Re-fix LAB_db07 5-digit codes.
- `fix_dem_kom_special.py` — Fix the unsourced DEM_kom special codes.
- `fix_dem_small_cats.py` — Fix small DEM categories from the English audit.
- `fix_dst_fetch_batch_b.py` — Apply DST value sets fetched by the dst-valuesets workflow.
- `fix_edu_afg_tilg_udel.py` — Fill EDU_afg/tilg/udel from authoritative DST sources.
- `fix_edu_small_cats.py` — Fix small EDU translation issues.
- `fix_edu_udd_disced_field.py` — Translate remaining Danish in EDU_udd/disced/field.
- `fix_edu_udd_levels.py` — Fix EDU_udd level mistranslations.
- `fix_en_audit_issues.py` — Fix issues flagged by audit_description_en.py.
- `fix_hea_patienttype.py` — Fix HEA_patienttype (all 4 codes were swapped).
- `fix_hea_volume_voltypecode.py` — Fix the HEA drug-VOLUME categories (hallucinated meanings → LMDB units).
- `fix_icd_false_official.py` — Clear false WHO ICD-10 official claims on HEA_ICD10.
- `fix_income_translations.py` — Fix English of LAB income quantile categories.
- `fix_inrepo_batch_a.py` — Resolve weak-source categories from in-repo sources.
- `fix_lab_analyte_en.py` — Translate the HEA_speciale lab-analyte block English.
- `fix_mojibake.py` — Fix mojibake artifacts in MASTER.
- `fix_mt_hallucinations.py` — Fix MarianMT/Qwen hallucinations in HEA_ICD10 English.
- `fix_residual_danish_en.py` — Clean residual-Danish translations in description_en.
- `fix_soc_afgtypko_bstrfkod.py` — Authoritative Danish + clean English for SOC_afgtypko/bstrfkod.
- `fix_soc_fgslkod.py` — Fix SOC_fgslkod (= DST IND_FGSLKOD).
- `fix_soc_frakkod.py` — Fix unsourced SOC_frakkod rows (= DST AFG_FRAKKOD).
- `fix_soc_haendelse_frakbkod.py` — Fix two mis-labelled SOC categories.
- `fix_unreliable_official_en.py` — Clear unreliable description_en_official.
- `manual_translations_ext.py` — Extended manual Danish→English dictionary (imported by apply_manual_translations.py).
- `mark_edu_current_completed.py` — Mark EDU English as current vs completed.
- `normalize_float_codes.py` — Normalize the 769 `.0` float-style codes in the vocab files.
- `retranslate_v2.py` — Improved Danish→English re-translation (Claude API / local LLM).
- `retranslate_with_llm.py` — Re-translate MarianMT output with Qwen2.5-14B-Instruct.
- `translate_descriptions.py` — 3-tier Danish→English translation.
- `translate_hea_speciale.py` — Expand HEA_speciale Danish billing abbreviations.
- `translate_soc_ger7.py` — Translate SOC_ger7 criminal-offense descriptions.
- `validate_hea_speciale.py` — QC gate for HEA_speciale translations (id-misassignment).
