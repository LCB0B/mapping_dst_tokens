#!/usr/bin/env python3
"""Translate Danish descriptions to English using a 3-tier approach.

Tier 1 (Phase 0): Static lookups — no GPU needed
  - Latin ICD-8 codes: copy as-is (language-neutral)
  - Municipalities: keep Danish names, translate well-known ones
  - Countries: ISO 3166 lookup table
  - Already-English descriptions: detect and copy to description_en

Tier 2 (Phase 1): Machine translation using Helsinki-NLP/opus-mt-da-en
  - Deduplicate descriptions first
  - Batch translate on GPU

Tier 3 (Phase 2): Quality check using Qwen2.5-7B-Instruct 4-bit
  - Heuristic checks (length ratio, number preservation, copy detection)
  - LLM scoring of translation quality
  - Re-translate flagged entries with NLLB fallback

Usage:
    python3 scripts/translate_descriptions.py [--phase 0|1|2|all] [--batch-size 128] [--qc-sample 0]
"""

import argparse
import csv
import os
import re
import sys
import time
from collections import defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
QC_REPORT_PATH = "translation_qc_report.csv"

# ─── ISO 3166 Danish→English country name lookup ───────────────────────────
# Covers all Danish country names that differ from English
COUNTRY_DA_TO_EN = {
    "Danmark": "Denmark",
    "Sverige": "Sweden",
    "Norge": "Norway",
    "Finland": "Finland",
    "Island": "Iceland",
    "Tyskland": "Germany",
    "Frankrig": "France",
    "Spanien": "Spain",
    "Italien": "Italy",
    "Storbritannien": "United Kingdom",
    "Irland": "Ireland",
    "Holland": "Netherlands",
    "Nederlandene": "Netherlands",
    "Belgien": "Belgium",
    "Schweiz": "Switzerland",
    "Østrig": "Austria",
    "Polen": "Poland",
    "Tjekkiet": "Czech Republic",
    "Slovakiet": "Slovakia",
    "Ungarn": "Hungary",
    "Rumænien": "Romania",
    "Bulgarien": "Bulgaria",
    "Kroatien": "Croatia",
    "Serbien": "Serbia",
    "Slovenien": "Slovenia",
    "Bosnien-Hercegovina": "Bosnia and Herzegovina",
    "Bosnien og Hercegovina": "Bosnia and Herzegovina",
    "Nordmakedonien": "North Macedonia",
    "Makedonien": "North Macedonia",
    "Montenegro": "Montenegro",
    "Albanien": "Albania",
    "Grækenland": "Greece",
    "Tyrkiet": "Turkey",
    "Cypern": "Cyprus",
    "Malta": "Malta",
    "Portugal": "Portugal",
    "Estland": "Estonia",
    "Letland": "Latvia",
    "Litauen": "Lithuania",
    "Ukraine": "Ukraine",
    "Hviderusland": "Belarus",
    "Moldova": "Moldova",
    "Rusland": "Russia",
    "Georgien": "Georgia",
    "Armenien": "Armenia",
    "Aserbajdsjan": "Azerbaijan",
    "Kasakhstan": "Kazakhstan",
    "Usbekistan": "Uzbekistan",
    "Turkmenistan": "Turkmenistan",
    "Tadsjikistan": "Tajikistan",
    "Kirgisistan": "Kyrgyzstan",
    "Kina": "China",
    "Japan": "Japan",
    "Sydkorea": "South Korea",
    "Nordkorea": "North Korea",
    "Mongoliet": "Mongolia",
    "Indien": "India",
    "Pakistan": "Pakistan",
    "Bangladesh": "Bangladesh",
    "Sri Lanka": "Sri Lanka",
    "Nepal": "Nepal",
    "Bhutan": "Bhutan",
    "Myanmar": "Myanmar",
    "Thailand": "Thailand",
    "Vietnam": "Vietnam",
    "Cambodja": "Cambodia",
    "Laos": "Laos",
    "Indonesien": "Indonesia",
    "Malaysia": "Malaysia",
    "Filippinerne": "Philippines",
    "Singapore": "Singapore",
    "Brunei": "Brunei",
    "Østtimor": "East Timor",
    "Afghanistan": "Afghanistan",
    "Iran": "Iran",
    "Irak": "Iraq",
    "Syrien": "Syria",
    "Libanon": "Lebanon",
    "Jordan": "Jordan",
    "Israel": "Israel",
    "Palæstina": "Palestine",
    "Saudi-Arabien": "Saudi Arabia",
    "Yemen": "Yemen",
    "Oman": "Oman",
    "De Forenede Arabiske Emirater": "United Arab Emirates",
    "Qatar": "Qatar",
    "Bahrain": "Bahrain",
    "Kuwait": "Kuwait",
    "Ægypten": "Egypt",
    "Libyen": "Libya",
    "Tunesien": "Tunisia",
    "Algeriet": "Algeria",
    "Marokko": "Morocco",
    "Sudan": "Sudan",
    "Sydsudan": "South Sudan",
    "Etiopien": "Ethiopia",
    "Eritrea": "Eritrea",
    "Somalia": "Somalia",
    "Djibouti": "Djibouti",
    "Kenya": "Kenya",
    "Tanzania": "Tanzania",
    "Uganda": "Uganda",
    "Rwanda": "Rwanda",
    "Burundi": "Burundi",
    "Den Demokratiske Republik Congo": "Democratic Republic of the Congo",
    "Congo-Kinshasa": "Democratic Republic of the Congo",
    "Republikken Congo": "Republic of the Congo",
    "Congo-Brazzaville": "Republic of the Congo",
    "Cameroun": "Cameroon",
    "Nigeria": "Nigeria",
    "Ghana": "Ghana",
    "Elfenbenskysten": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "Senegal": "Senegal",
    "Mali": "Mali",
    "Niger": "Niger",
    "Burkina Faso": "Burkina Faso",
    "Guinea": "Guinea",
    "Sierra Leone": "Sierra Leone",
    "Liberia": "Liberia",
    "Togo": "Togo",
    "Benin": "Benin",
    "Mauretanien": "Mauritania",
    "Gambia": "Gambia",
    "Guinea-Bissau": "Guinea-Bissau",
    "Kap Verde": "Cape Verde",
    "Gabon": "Gabon",
    "Ækvatorialguinea": "Equatorial Guinea",
    "Centralafrikanske Republik": "Central African Republic",
    "Tchad": "Chad",
    "Angola": "Angola",
    "Mozambique": "Mozambique",
    "Zambia": "Zambia",
    "Zimbabwe": "Zimbabwe",
    "Malawi": "Malawi",
    "Sydafrika": "South Africa",
    "Namibia": "Namibia",
    "Botswana": "Botswana",
    "Lesotho": "Lesotho",
    "Swaziland": "Eswatini",
    "Eswatini": "Eswatini",
    "Madagaskar": "Madagascar",
    "Mauritius": "Mauritius",
    "Seychellerne": "Seychelles",
    "Komorerne": "Comoros",
    "USA": "United States",
    "Canada": "Canada",
    "Mexico": "Mexico",
    "Guatemala": "Guatemala",
    "Belize": "Belize",
    "Honduras": "Honduras",
    "El Salvador": "El Salvador",
    "Nicaragua": "Nicaragua",
    "Costa Rica": "Costa Rica",
    "Panama": "Panama",
    "Cuba": "Cuba",
    "Jamaica": "Jamaica",
    "Haiti": "Haiti",
    "Den Dominikanske Republik": "Dominican Republic",
    "Trinidad og Tobago": "Trinidad and Tobago",
    "Barbados": "Barbados",
    "Bahamas": "Bahamas",
    "Colombia": "Colombia",
    "Venezuela": "Venezuela",
    "Guyana": "Guyana",
    "Surinam": "Suriname",
    "Ecuador": "Ecuador",
    "Peru": "Peru",
    "Brasilien": "Brazil",
    "Bolivia": "Bolivia",
    "Paraguay": "Paraguay",
    "Chile": "Chile",
    "Argentina": "Argentina",
    "Uruguay": "Uruguay",
    "Australien": "Australia",
    "New Zealand": "New Zealand",
    "Papua Ny Guinea": "Papua New Guinea",
    "Fiji": "Fiji",
    "Samoa": "Samoa",
    "Tonga": "Tonga",
    "Grønland": "Greenland",
    "Færøerne": "Faroe Islands",
    "Statsløs": "Stateless",
    "Ukendt": "Unknown",
    "Uoplyst": "Unknown",
    "Jugoslavien": "Yugoslavia",
    "Tjekkoslovakiet": "Czechoslovakia",
    "Sovjet": "Soviet Union",
    "Sovjetunionen": "Soviet Union",
    "Vesttyskland": "West Germany",
    "Østtyskland": "East Germany",
    "Maldiverne": "Maldives",
    "Taiwan": "Taiwan",
    "Liechtenstein": "Liechtenstein",
    "Luxembourg": "Luxembourg",
    "Monaco": "Monaco",
    "San Marino": "San Marino",
    "Vatikanstaten": "Vatican City",
    "Andorra": "Andorra",
    "Kosovo": "Kosovo",
}

# Municipality translations for well-known Danish cities
MUNICIPALITY_DA_TO_EN = {
    "København": "Copenhagen",
    "Frederiksberg": "Frederiksberg",
    "Helsingør": "Elsinore",
    "Ålborg": "Aalborg",
    "Århus": "Aarhus",
}


def load_master():
    """Load MASTER_CATEGORY_MAPPINGS.csv and return (rows, fieldnames)."""
    rows = []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(dict(row))
    return rows, fieldnames


def save_master(rows, fieldnames):
    """Write rows back to MASTER_CATEGORY_MAPPINGS.csv."""
    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_likely_english(desc):
    """Heuristic check if a description is already English."""
    if not desc:
        return False
    # Danish-specific characters
    if re.search(r"[æøåÆØÅ]", desc):
        return False
    # Danish-specific words (common in admin descriptions)
    danish_words = r"\b(og|med|til|af|ved|eller|der|som|ikke|klasse|uoplyst|forårsaget|uddannelse|forbrydelse|ansatte|selvstændig|lønmodtager|kommune|øvrige|mhp|vedr|ifm|pga|herunder|heraf|andre|andet|uden|efter|almen|kvinder|mænd|børn|samt|dvs|evt|iht|ift|mfl|mv|opr|udl|indl|fys|psyk|kir|sygd|beh|afd|amb|henvist|indlagt|udskrevet|ophold|ydelse|speciale|konsultation|behandling|undersøgelse|henvisning|sengeafd|samlet|herudover|hermed)\b"
    if re.search(danish_words, desc.lower()):
        return False
    return True


def is_latin_icd8(row):
    """Check if this is a Latin ICD-8 description."""
    return (
        row.get("source", "") == "none|icd8_raw"
        or (row.get("category") == "HEA_ICD10"
            and row.get("value", "").isdigit()
            and row.get("source", "").endswith("|icd8_raw"))
    )


# ─── Phase 0: Static lookups ───────────────────────────────────────────────

def phase0(rows):
    """Handle translations that don't need ML: Latin, names, already-English."""
    stats = {"latin": 0, "municipality": 0, "country": 0, "already_english": 0, "skipped": 0}

    for row in rows:
        if row["description_en"].strip():
            continue  # Already has EN
        desc_da = row["description_da"].strip()
        if not desc_da:
            continue

        cat = row["category"]

        # 1. Latin ICD-8 codes — copy as-is
        if is_latin_icd8(row):
            row["description_en"] = desc_da
            stats["latin"] += 1
            continue

        # 2. Municipality names
        if cat == "DEM_kom":
            en_name = MUNICIPALITY_DA_TO_EN.get(desc_da, desc_da)
            row["description_en"] = en_name
            stats["municipality"] += 1
            continue

        # 3. Country names (DEM_opr and DEM_statsb)
        if cat in ("DEM_opr", "DEM_statsb"):
            # Try exact match first
            en_name = COUNTRY_DA_TO_EN.get(desc_da)
            if en_name:
                row["description_en"] = en_name
                stats["country"] += 1
                continue
            # Try matching within compound descriptions like "Land ukendt (1)"
            base = desc_da.split("(")[0].strip()
            en_name = COUNTRY_DA_TO_EN.get(base)
            if en_name:
                suffix = desc_da[len(base):]
                row["description_en"] = en_name + suffix
                stats["country"] += 1
                continue
            # Keep as-is if not in lookup (likely already English or rare)
            row["description_en"] = desc_da
            stats["country"] += 1
            continue

        # 4. Already-English descriptions misclassified as Danish
        if is_likely_english(desc_da):
            row["description_en"] = desc_da
            stats["already_english"] += 1
            continue

        stats["skipped"] += 1

    total_handled = stats["latin"] + stats["municipality"] + stats["country"] + stats["already_english"]
    print(f"\nPhase 0 complete:")
    print(f"  Latin ICD-8 copied:       {stats['latin']}")
    print(f"  Municipalities resolved:  {stats['municipality']}")
    print(f"  Countries resolved:       {stats['country']}")
    print(f"  Already-English copied:   {stats['already_english']}")
    print(f"  Total handled:            {total_handled}")
    print(f"  Still needing translation: {stats['skipped']}")
    return stats


# ─── Phase 1: Machine translation ──────────────────────────────────────────

def phase1(rows, batch_size=128, gpu_id=1):
    """Translate remaining Danish descriptions using MarianMT."""
    try:
        from tqdm import tqdm
    except ImportError:
        print("tqdm not available, using simple progress")
        tqdm = None

    import torch
    from transformers import MarianMTModel, MarianTokenizer

    # Collect rows still needing EN
    needs_translation = []
    for i, row in enumerate(rows):
        if not row["description_en"].strip() and row["description_da"].strip():
            needs_translation.append(i)

    if not needs_translation:
        print("\nPhase 1: No rows need translation!")
        return

    print(f"\nPhase 1: {len(needs_translation)} rows need translation")

    # Deduplicate by description_da
    desc_to_indices = defaultdict(list)
    for idx in needs_translation:
        desc_to_indices[rows[idx]["description_da"]].append(idx)

    unique_descs = list(desc_to_indices.keys())
    print(f"  Unique descriptions: {len(unique_descs)}")

    # Load model
    model_name = "Helsinki-NLP/opus-mt-da-en"
    device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
    print(f"  Loading {model_name} on {device}...")

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name, use_safetensors=True).to(device)
    model.eval()
    print(f"  Model loaded")

    # Batch translate
    translations = {}
    n_batches = (len(unique_descs) + batch_size - 1) // batch_size

    iterator = range(0, len(unique_descs), batch_size)
    if tqdm:
        iterator = tqdm(iterator, total=n_batches, desc="Translating")

    checkpoint_interval = 5000
    translated_count = 0

    with torch.no_grad():
        for batch_start in iterator:
            batch_descs = unique_descs[batch_start : batch_start + batch_size]

            inputs = tokenizer(
                batch_descs,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(device)

            output_ids = model.generate(
                **inputs,
                max_length=512,
                num_beams=4,
            )

            batch_translations = tokenizer.batch_decode(output_ids, skip_special_tokens=True)

            for desc, trans in zip(batch_descs, batch_translations):
                translations[desc] = trans

            translated_count += len(batch_descs)

            # Checkpoint: apply translations periodically
            if translated_count % checkpoint_interval < batch_size:
                _apply_translations(rows, translations, desc_to_indices)
                if tqdm:
                    pass  # tqdm handles progress
                else:
                    print(f"  Checkpoint: {translated_count}/{len(unique_descs)} translated")

    # Final apply
    _apply_translations(rows, translations, desc_to_indices)

    # Clean up GPU memory
    del model
    del tokenizer
    torch.cuda.empty_cache()

    # Count results
    still_empty = sum(1 for row in rows if not row["description_en"].strip())
    print(f"\nPhase 1 complete:")
    print(f"  Translated {len(translations)} unique descriptions")
    print(f"  Applied to {len(needs_translation)} rows")
    print(f"  Remaining empty description_en: {still_empty}")


def _apply_translations(rows, translations, desc_to_indices):
    """Apply translation dict back to all rows sharing the same description_da."""
    for desc_da, indices in desc_to_indices.items():
        if desc_da in translations:
            for idx in indices:
                if not rows[idx]["description_en"].strip():
                    rows[idx]["description_en"] = translations[desc_da]


# ─── Phase 2: Quality check ────────────────────────────────────────────────

def heuristic_qc(rows):
    """Run heuristic quality checks on translations. Returns list of flagged rows."""
    flags = []

    for i, row in enumerate(rows):
        en = row["description_en"].strip()
        da = row["description_da"].strip()
        if not en or not da:
            continue

        issues = []

        # 1. Length ratio check
        if len(da) > 5 and len(en) > 0:
            ratio = len(en) / len(da)
            if ratio < 0.3 or ratio > 3.5:
                issues.append(f"length_ratio={ratio:.2f}")

        # 2. Translation identical to input (copy detection)
        if en.lower() == da.lower() and len(da) > 20:
            # Long identical strings are suspicious (short ones may be proper nouns)
            issues.append("identical_copy")

        # 3. Number preservation
        da_nums = set(re.findall(r"\d+", da))
        en_nums = set(re.findall(r"\d+", en))
        if da_nums and not da_nums.issubset(en_nums):
            missing = da_nums - en_nums
            # Only flag if significant numbers are missing (ignore small formatting diffs)
            if any(len(n) > 1 for n in missing):
                issues.append(f"missing_numbers={missing}")

        # 4. Empty or very short translation for long input
        if len(da) > 30 and len(en) < 5:
            issues.append("suspiciously_short")

        if issues:
            flags.append({
                "row_idx": i,
                "code": row["code"],
                "category": row["category"],
                "description_da": da,
                "description_en": en,
                "issues": "|".join(issues),
                "llm_score": "",
            })

    return flags


def llm_qc(rows, flags_from_heuristic, sample_size=0, gpu_id=0):
    """Score translations using Qwen2.5-7B-Instruct 4-bit."""
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    # Collect all translated rows for LLM scoring
    translated_rows = []
    for i, row in enumerate(rows):
        en = row["description_en"].strip()
        da = row["description_da"].strip()
        if en and da and en != da:
            translated_rows.append(i)

    if sample_size > 0 and sample_size < len(translated_rows):
        import random
        random.seed(42)
        # Stratified sample: ensure flagged rows are included
        flagged_indices = {f["row_idx"] for f in flags_from_heuristic}
        non_flagged = [i for i in translated_rows if i not in flagged_indices]
        remaining_sample = max(0, sample_size - len(flagged_indices))
        sampled = list(flagged_indices) + random.sample(non_flagged, min(remaining_sample, len(non_flagged)))
        translated_rows = sorted(sampled)

    print(f"\nPhase 2 LLM QC: scoring {len(translated_rows)} translations")

    # Load model
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
    print(f"  Loading {model_name} 4-bit on {device}...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map={"": gpu_id} if torch.cuda.is_available() else "auto",
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    model.eval()
    print(f"  Model loaded")

    # Score each translation
    scores = {}
    batch_size = 8  # Process prompts one at a time but batch the scoring

    iterator = range(0, len(translated_rows), batch_size)
    if tqdm:
        iterator = tqdm(
            iterator,
            total=(len(translated_rows) + batch_size - 1) // batch_size,
            desc="LLM QC",
        )

    with torch.no_grad():
        for batch_start in iterator:
            batch_indices = translated_rows[batch_start : batch_start + batch_size]

            for idx in batch_indices:
                row = rows[idx]
                da = row["description_da"]
                en = row["description_en"]
                cat = row["category"]

                prompt = f"""Rate this Danish→English translation on a 1-5 scale.
Context: {cat} (Danish administrative register code)
Danish: {da}
English: {en}

1=wrong/nonsensical, 2=major errors, 3=acceptable but awkward, 4=good, 5=excellent
Reply with ONLY the number (1-5):"""

                messages = [{"role": "user", "content": prompt}]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = tokenizer(text, return_tensors="pt").to(model.device)

                output = model.generate(
                    **inputs,
                    max_new_tokens=5,
                    temperature=0.1,
                    do_sample=False,
                )

                response = tokenizer.decode(
                    output[0][inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True,
                ).strip()

                # Extract score
                score_match = re.search(r"[1-5]", response)
                score = int(score_match.group()) if score_match else 0
                scores[idx] = score

    # Clean up
    del model
    del tokenizer
    torch.cuda.empty_cache()

    return scores


def find_copy_throughs(rows):
    """Find rows where MarianMT just copied the Danish text as-is."""
    copy_indices = []
    for i, row in enumerate(rows):
        da = row["description_da"].strip()
        en = row["description_en"].strip()
        if not da or not en:
            continue
        # Identical and longer than 15 chars (short strings may be proper nouns/Latin)
        if da.lower() == en.lower() and len(da) > 15:
            # Exclude proper noun categories that are expected to be identical
            if row["category"] not in ("DEM_kom", "DEM_opr", "DEM_statsb"):
                # Exclude rows where description was already English (Phase 0 copies)
                if not is_likely_english(da):
                    copy_indices.append(i)
    return copy_indices


def phase2(rows, sample_size=0, gpu_id=0):
    """Run quality checks on all translations."""
    print("\nPhase 2: Quality Check")

    # Step 1: Re-translate copy-throughs with NLLB
    print("  Detecting copy-throughs from Phase 1...")
    copy_indices = find_copy_throughs(rows)
    print(f"  Found {len(copy_indices)} copy-throughs to re-translate")

    if copy_indices:
        retranslate_with_nllb(rows, copy_indices, gpu_id=gpu_id)

    # Step 2: Heuristic checks (after re-translation)
    print("\n  Running heuristic checks...")
    heuristic_flags = heuristic_qc(rows)
    print(f"  Heuristic flags: {len(heuristic_flags)}")

    # Categorize flags
    issue_counts = defaultdict(int)
    for f in heuristic_flags:
        for issue in f["issues"].split("|"):
            issue_name = issue.split("=")[0]
            issue_counts[issue_name] += 1
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"    {issue}: {count}")

    # Step 3: LLM QC
    llm_scores = llm_qc(rows, heuristic_flags, sample_size=sample_size, gpu_id=gpu_id)

    # Merge scores into flags
    flagged_indices = {f["row_idx"]: f for f in heuristic_flags}
    all_qc_rows = []

    for idx, score in llm_scores.items():
        row = rows[idx]
        if idx in flagged_indices:
            entry = flagged_indices[idx]
            entry["llm_score"] = score
        else:
            entry = {
                "row_idx": idx,
                "code": row["code"],
                "category": row["category"],
                "description_da": row["description_da"],
                "description_en": row["description_en"],
                "issues": "",
                "llm_score": score,
            }
        all_qc_rows.append(entry)

    # Add heuristic-only flags not covered by LLM
    for f in heuristic_flags:
        if f["row_idx"] not in llm_scores:
            all_qc_rows.append(f)

    # Step 4: Re-translate any LLM-flagged low quality with NLLB
    low_quality = [idx for idx, score in llm_scores.items() if score <= 2]
    if low_quality:
        # Filter out ones already re-translated in step 1
        already_retranslated = set(copy_indices)
        new_low = [idx for idx in low_quality if idx not in already_retranslated]
        if new_low:
            print(f"\n  Re-translating {len(new_low)} LLM-flagged entries with NLLB...")
            retranslate_with_nllb(rows, new_low, gpu_id=gpu_id)

    # Write QC report
    all_qc_rows.sort(key=lambda x: (x.get("llm_score") or 99, x["code"]))

    with open(QC_REPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["code", "category", "description_da", "description_en", "issues", "llm_score"],
        )
        writer.writeheader()
        for entry in all_qc_rows:
            writer.writerow({
                "code": entry["code"],
                "category": entry["category"],
                "description_da": entry["description_da"],
                "description_en": entry["description_en"],
                "issues": entry["issues"],
                "llm_score": entry.get("llm_score", ""),
            })

    # Summary stats
    scored = [s for s in llm_scores.values() if s > 0]
    if scored:
        avg_score = sum(scored) / len(scored)
        score_dist = defaultdict(int)
        for s in scored:
            score_dist[s] += 1
        print(f"\n  LLM QC Summary ({len(scored)} scored):")
        print(f"    Average score: {avg_score:.2f}")
        for s in range(1, 6):
            pct = score_dist[s] / len(scored) * 100
            print(f"    Score {s}: {score_dist[s]} ({pct:.1f}%)")

    print(f"\n  Low quality (score ≤ 2): {len(low_quality)}")
    print(f"  QC report written to {QC_REPORT_PATH}")
    return all_qc_rows


def retranslate_with_nllb(rows, indices, gpu_id=0):
    """Re-translate flagged entries using facebook/nllb-200-1.3B."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    if not indices:
        return

    model_name = "facebook/nllb-200-1.3B"
    device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
    print(f"  Loading {model_name} on {device}...")

    tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang="dan_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, use_safetensors=True).to(device)
    model.eval()

    # Deduplicate
    desc_to_indices = defaultdict(list)
    for idx in indices:
        desc_to_indices[rows[idx]["description_da"]].append(idx)

    unique_descs = list(desc_to_indices.keys())
    print(f"  Re-translating {len(unique_descs)} unique descriptions...")

    batch_size = 32
    with torch.no_grad():
        for batch_start in range(0, len(unique_descs), batch_size):
            batch = unique_descs[batch_start : batch_start + batch_size]

            inputs = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(device)

            output_ids = model.generate(
                **inputs,
                forced_bos_token_id=tokenizer.convert_tokens_to_ids("eng_Latn"),
                max_length=512,
                num_beams=4,
            )

            translations = tokenizer.batch_decode(output_ids, skip_special_tokens=True)

            for desc, trans in zip(batch, translations):
                for idx in desc_to_indices[desc]:
                    rows[idx]["description_en"] = trans

    del model
    del tokenizer
    torch.cuda.empty_cache()
    print(f"  Re-translated {len(indices)} rows")


# ─── Post-translation ──────────────────────────────────────────────────────

def update_description_short(rows):
    """Update description_short = description_en with parentheses removed."""
    updated = 0
    for row in rows:
        en = row.get("description_en", "").strip()
        if en:
            # Remove parenthetical content for short description
            short = re.sub(r"\s*\([^)]*\)", "", en).strip()
            if short != row.get("description_short", ""):
                row["description_short"] = short
                updated += 1
    print(f"\nUpdated description_short for {updated} rows")


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Translate Danish descriptions to English")
    parser.add_argument(
        "--phase",
        choices=["0", "1", "2", "all"],
        default="all",
        help="Which phase to run (default: all)",
    )
    parser.add_argument("--batch-size", type=int, default=128, help="Translation batch size")
    parser.add_argument(
        "--qc-sample",
        type=int,
        default=0,
        help="QC sample size (0 = score all translations)",
    )
    parser.add_argument("--gpu-translate", type=int, default=1, help="GPU for translation (default: 1)")
    parser.add_argument("--gpu-qc", type=int, default=0, help="GPU for QC model (default: 0)")
    args = parser.parse_args()

    print("=" * 60)
    print("Danish → English Translation Pipeline")
    print("=" * 60)

    rows, fieldnames = load_master()
    total = len(rows)
    empty_en = sum(1 for r in rows if not r["description_en"].strip())
    print(f"\nLoaded {total} rows, {empty_en} missing description_en")

    run_phase = args.phase

    if run_phase in ("0", "all"):
        t0 = time.time()
        phase0(rows)
        save_master(rows, fieldnames)
        print(f"  Phase 0 time: {time.time() - t0:.1f}s")

        # Reload to verify
        rows, fieldnames = load_master()
        empty_en = sum(1 for r in rows if not r["description_en"].strip())
        print(f"  After phase 0: {empty_en} still missing description_en")

    if run_phase in ("1", "all"):
        t0 = time.time()
        phase1(rows, batch_size=args.batch_size, gpu_id=args.gpu_translate)
        save_master(rows, fieldnames)
        print(f"  Phase 1 time: {time.time() - t0:.1f}s")

        rows, fieldnames = load_master()
        empty_en = sum(1 for r in rows if not r["description_en"].strip())
        print(f"  After phase 1: {empty_en} still missing description_en")

    if run_phase in ("2", "all"):
        t0 = time.time()
        phase2(rows, sample_size=args.qc_sample, gpu_id=args.gpu_qc)
        save_master(rows, fieldnames)
        print(f"  Phase 2 time: {time.time() - t0:.1f}s")

    # Post-translation: update description_short
    if run_phase in ("1", "all"):
        rows, fieldnames = load_master()
        update_description_short(rows)
        save_master(rows, fieldnames)

    # Final stats
    rows, fieldnames = load_master()
    empty_en = sum(1 for r in rows if not r["description_en"].strip())
    filled_en = sum(1 for r in rows if r["description_en"].strip())
    print(f"\n{'=' * 60}")
    print(f"FINAL: {filled_en}/{total} rows have description_en ({filled_en/total*100:.1f}%)")
    print(f"  Still empty: {empty_en}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
