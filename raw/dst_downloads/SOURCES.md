# `raw/dst_downloads/` — source manifest

The CSV/TXT extractions in this directory are tracked in git. The **large
third-party binary reference files** (PDF/XLS/XLSX, ~38 MB) are **NOT committed**
— they are redistributable only under their publishers' terms, so they are
`.gitignore`d and listed here for re-download. See `notes.md` §3 and §6 for how
each was used.

## Not-committed binaries (re-download from publisher)

| File | What it is | Source / where to get it |
|---|---|---|
| `nace_rev1_en.pdf` | NACE Rev. 1.1 industry classification (EU), English | Eurostat RAMON / NACE Rev. 1.1 |
| `nace_rev2_en.pdf` | NACE Rev. 2 industry classification (EU), English | Eurostat RAMON / NACE Rev. 2 (CSV form: vincentarelbundock Rdatasets, see `notes.md` §6) |
| `speciale_dst_full.xlsx` | DST SPECIALE ydelser (full) | dst.dk SPECIALE (`notes.md` §6) |
| `ssr_ydelsesoversigt_historisk.xls` | Sygesikringsregisteret — historical ydelsesoversigt | Sundhedsdatastyrelsen / Sygesikringsregisteret |
| `okportal_almen_laegegerning.pdf` | Overenskomst — almen lægegerning | laeger.dk / sundhed.dk (PLO–RLTN), `notes.md` §3 |
| `plo_overenskomst_2024.pdf` | PLO overenskomst 2024 | laeger.dk |
| `plo_honorartabel_2022.pdf` | PLO honorartabel 2022 | laeger.dk |
| `plo_vejledning_2022.pdf` | PLO vejledning 2022 | laeger.dk |
| `plo_regionale_aftaler_koder.pdf` | PLO regional/§2-aftale codes | laeger.dk (regional PLO branches), `notes.md` §3 |
| `takst2024.pdf`, `takstmappe.pdf` | Fee schedules (takstmapper) | RLTN/PLO |
| `sjaelland_paragraf2_koder.pdf` | Region Sjælland §2-aftale ydelseskoder | sundhed.dk — see the §2-aftaler URL in `notes.md` §3 |
| `dst_socio_1997.pdf` | "SOCIO – Danmarks Statistiks Socioøkonomiske Klassifikation, 1. udgave 1997" | Danmarks Statistik (documents the 1997 system; does NOT cover the pre-1997 `LAB_socio` `gl_*` codes — see `QC_REPORT.md`) |
| `dst_db07_2014.pdf` | DB07 (Dansk Branchekode 2007) publication | dst.dk DB07 (CSV form: `db07_v*.csv` here) |
| `dst_uddreg_guide.pdf` | DST education-register guide | dst.dk |
| `aarhus_idap_vde.pdf` | Regional/local reference document | provenance uncertain — confirm before relying on it |

## Committed extractions (CSV/TXT) — kept in git
The `*.csv` / `*.txt` files in this directory (ATC/ICD-10/ISCO/NACE/DB07/GER7/
DISCO-88/speciale/SSR code lists, etc.) are the machine-readable extractions
actually consumed by the scripts. They remain tracked.

**Replaced file (2026-06-09):** `nace_rev1_en.csv` was originally a failed PDF
extraction (16 lines of cover-page noise). It now holds the proper NACE Rev. 1
(1990) structure — 833 codes (sections/divisions/groups/classes) with English
titles — extracted from the Eurostat RAMON linked-data mirror:
`https://raw.githubusercontent.com/ipsoeu/ramon-ld/master/nace/1990.rdf`
(SKOS notation + English prefLabel). NACE Rev. 1 is the basis of DST's DB93
(`LAB_nace`).

**`sks_dia_dk.csv` (added 2026-06-09):** the complete SKS `dia` (diagnosis)
catalog — 25,048 D-codes with Danish text and validity dates, one row per code
(currently-valid text preferred, else the latest historical text). Extracted
from Sundhedsdatastyrelsen's full SKS dump:
`https://filer.sundhedsdata.dk/sks/data/skscomplete/SKScomplete.txt`
(fixed-width, ISO-8859; the 23 MB raw dump itself is not committed).
It is a strict superset of `lookup_dictionaries/HEA_ICD10_dict.csv` (+69 codes).
