# Recovering the `LAB_socio` `gl_*` (SOCIO_GL) labels from your sequence data

## The issue in one paragraph

`LAB_socio` `gl_*` (51 codes) come from **`AKM:SOCIO_GL`** = Statistics Denmark's
*"Socioøkonomisk klassifikation 1976–1990"*. This is the **`ARBSTIL`** member of the
socio-status family. DST only publishes the **harmonized 3-digit** version of it
(`raw/dst_downloads/arbstil_kode_1980.csv` → codes like `110/131/200/311`); the **raw
2-digit codes** our `gl_*` actually use (`11`, `31`, `40`, …) are **not published** — they
live only in DST Forskningsservice or the original `.pt` the vocab was built from
(CLAUDE.md HARD RULE #5). So we cannot label them from a public source. The labels currently
in `MASTER_CATEGORY_MAPPINGS.csv` for the 17 non-`[Unresolved]` `gl_*` are **unsourced guesses**
and several are anachronistic — do **not** trust them.

## The socio variable changes coding scheme over time

The "socio-economic status" of a person is recorded under **different variables / code
schemes depending on the year** (from `raw/aarhus_idap_vde.pdf`, Aarhus LMDG, + DST):

| Period | DST variable | Scheme in the vocab |
|--------|--------------|---------------------|
| 1976/80–1986 | `ARBSTIL` (raw 2-digit) | **`gl_*`** (`LAB_socio`, SOCIO_GL) |
| 1987– | `SOCIO13` (back-extended to 1987) | **`socio13`** (`LAB_socio13`, codes `110`–`420`) |
| (1994–95 `NYARB`, 1996–2007 `SOCSTIL_KODE`, 2008– `SOC_STATUS_KODE` are the intermediate DST names; in the vocab the modern values are `LAB_socio13`) | | |

So in a person's life sequence, the socio token **switches from `gl_*` to `socio13`**
around **1987** (the SOCIO13 back-extension boundary). The person's *real* status usually
does **not** jump at that administrative boundary — which is what makes the crosswalk possible.

> Note `LAB_socio13` (the 21 modern codes) is **fully and authoritatively labelled** already
> (verified against `AKM:SOCIO13`). It is the *target* you map the old `gl_*` onto.

## How to build the `gl_* → socio13` mapping from your data

For each person, walk their sequence and find the **scheme-transition point** (last `gl_*`
token before the switch, first `socio13` token after). For individuals whose status is stable
across the boundary, the old code and the new code denote the same thing. Aggregated over many
people, the dominant new-code for each old-code gives the crosswalk.

1. **Extract socio events per person, ordered by time.** Keep `(person_id, year, socio_token)`
   where `socio_token` is either a `gl_*` or a `socio13` code.
2. **Find adjacent cross-scheme pairs.** For each person, take consecutive socio observations
   `(year_t: gl_X) → (year_{t+1}: socio13_Y)` that straddle the 1987 boundary (ideally
   consecutive years, no gap).
3. **Tally** `count[gl_X][socio13_Y]`.
4. **Assign** each `gl_X` the `socio13_Y` with the highest count (its modal successor), and
   record the support/share so you can see how clean each mapping is.
5. **Label** `gl_X` using `socio13_Y`'s authoritative label (from `LAB_socio13`), tagging the
   source as e.g. `empirical_crosswalk_socio13` and confidence by the share.
6. (Optional, more robust) also use the **backward** pair `(gl after) ← (socio13 before)` for
   the few people who appear earlier in modern data, and intersect the two directions.

Tips: restrict to people **not changing employment** around the boundary (e.g. same
DISCO/industry token, no job-start/stop event) to reduce noise; require a minimum support
(say ≥50 people and ≥70 % share) before trusting a mapping.

## Validation: expected group-level mapping

`gl_*` is a 2-digit hierarchical code (1st digit = main group). Use the authoritative group
structure (`raw/aarhus_idap_vde.pdf`) to **sanity-check** the empirical result — the modal `socio13`
should fall in the matching block:

| `gl_*` group | meaning (idan_vde) | expected `socio13` block |
|---|---|---|
| `1x` (11,12,19) | Selvstændige | `110`–`114` |
| `20` | **Medhjælpende ægtefælle** ✅ confirmed | `120` |
| `3x` (31,32,33,39) | Lønmodtagere | `131`–`139` |
| `40` | **Arbejdsløse** ✅ confirmed | `210` |
| `5x`/`6x` | Tilbagetrækning / pensionister | `321`–`323` |
| `9x`/uddannelse/børn | Uden for arbejdsstyrken | `310`, `330`, `410`, `420` |

(`2x` 21–30, `5x`–`8x` 59–89, and `0x` 1–10 are the still-`[Unresolved]` blocks — the empirical
crosswalk is the most promising way to recover them.)

**Confirmed anchors:** `gl_20` = Medhjælpende ægtefælle, `gl_40` = Arbejdsløs.
**Known-bad (anachronistic for 1976–1990, ignore the current labels):**
`gl_41/42/43/49/51/52/53` (orlov, barsels-/sygedagpenge, revalidering, aktivering,
ledighedsydelse, efterløn-detail) — those benefit subdivisions were only introduced 1994+.

## Caveats / data breaks

- DST notes socio **data breaks in 1994, 1996, 2002, 2008** — and `SOCIO13` itself was
  back-extended to 1987, so the pre-1987 ↔ post-1987 join is the cleanest crosswalk point.
- A few `gl_*` may have **no clean modern counterpart** (categories that disappeared) — leave
  those `[Unresolved]`.
- The empirical crosswalk gives the *meaning*, not DST's exact historical wording; tag it as
  derived, not as an official DST label.

## Other variables with the same scheme-transition problem

The same crosswalk method applies to these (a token's coding scheme changed over time, so
adjacent observations of the same person/firm across the boundary recover the old→new map):

| Category | Old (ambiguous) code | Map onto (newer, labelled) | Note |
|---|---|---|---|
| `LAB_db07` 5-digit (`11100`–`89900`) | mixed: NACE-Rev2 division / leading-zero-stripped DB07 / DB93 | the 6-digit `LAB_db07` token the same **firm** has after the switch | encoding genuinely ambiguous online; see `SOURCE_AUDIT.md`. `514620`+`999999` already resolved (DB93). |
| `LAB_tilstand` (`AMRUN:TILSTAND_KODE_AMR`) | 5-digit AMR tilstand (no public værdisæt) | co-occurring `LAB_socio13` (DST notes a `TILSTAND_KODE_AMR↔SOC_STATUS_KODE` crosslist) | |
| `HEA_urgency` `9`/`ATA*` | old/triage admission codes | modern `INDM` `1`=Akut/`2`=Ikke-akut (LPR3, 2014+) | |

For `LAB_db07`, restrict to the same **firm id** across the DB-version boundary (no industry
change) and map the 5-digit code to the modal 6-digit DB07 successor.

## Sources
- `input_dataset_description.csv` (repo) — `AKM:SOCIO_GL` / `AKM:SOCIO13` provenance.
- `raw/dst_downloads/arbstil_kode_1980.csv` — DST harmonized ARBSTIL_KODE v1:1980 nomenclature.
- `raw/aarhus_idap_vde.pdf` (Aarhus LMDG, ECONAU/IDAN var-description) — the `ARBSTIL→NYARB→SOCSTIL→
  SOC_STATUS` timeline + group structure.
- DST: `dst.dk/.../Times/moduldata-for-arbejdsmarked/arbstil` ;
  `.../nomenklaturer/socio-arb` (value set `SOCIO_ARB_ARBSTIL_KODE_V1_1980`, CSV/DDI download).
- `SOURCE_AUDIT.md` → "LAB_socio `gl_*`" deep-dive.
