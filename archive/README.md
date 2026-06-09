# archive/

Reference material that is **not authoritative** — kept for history, not for use.

| File | What it is | Why not authoritative |
|------|-----------|-----------------------|
| `vocab_2.json` | An older/alternate vocabulary (40,697 keys) | Token IDs **differ** from the canonical `vocab.json` (40,465 keys); 40,413 shared keys map to different IDs. The model uses `vocab.json`. |
| `translation_en_audit.csv` | Per-row output of the English-translation audit | One-off audit snapshot (produced by `scripts/oneoff/audit_description_en.py`) |
| `translation_audit_report.csv` | Per-category translation/official audit summary | One-off audit snapshot (produced by `scripts/oneoff/audit_and_tag_official.py`) |
| `translation_qc_report.csv.<date>` | Dated QC snapshot | Historical backup |

The current data is always `MASTER_CATEGORY_MAPPINGS.csv` + `vocab.json` at the
repo root.
