#!/usr/bin/env python3
"""Re-translate all MarianMT translations using Qwen2.5-14B-Instruct with domain context.

Uses the A5000 (24GB) GPU with 4-bit quantization.
Provides category-specific context to improve translation quality.

Usage:
    python3 scripts/retranslate_with_llm.py [--batch-size 10] [--gpu 1] [--category HEA_ICD10]
"""

import argparse
import csv
import os
import re
import time
from collections import defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# Domain context for each category prefix/variable
CATEGORY_CONTEXT = {
    # Health
    "HEA_ICD10": "ICD-10 medical diagnosis code (Danish hospital classification). Use standard English medical terminology. 'UNS' means 'NOS' (Not Otherwise Specified). 'IKA' means 'NEC' (Not Elsewhere Classified).",
    "HEA_speciale": "Danish medical specialty and procedure code (hospital department + service). Translate department names and procedure descriptions to English medical terms.",
    "HEA_atc": "ATC pharmaceutical classification (medication/drug category). Use standard English pharmacological terminology.",
    "HEA_DDK": "Danish surgical procedure code. Use standard English surgical terminology.",
    "HEA_DW": "Danish medical procedure code.",
    "HEA_DWG": "Danish medical procedure code.",
    "HEA_DWK": "Danish medical procedure code.",
    "HEA_GA": "Danish medical procedure code.",
    "HEA_GI": "Danish medical procedure code.",
    "HEA_GP": "Danish medical procedure code.",
    "HEA_L": "Danish medical procedure code.",
    "HEA_MG": "Danish medical procedure code.",
    "HEA_ML": "Danish medical procedure code.",
    "HEA_PK": "Danish medical procedure code.",
    "HEA_ST": "Danish medical procedure code.",
    "HEA_TU": "Danish medical procedure code.",
    # Education
    "EDU_audd": "Danish education program code (AUDD classification). Translate program names. Keep degree abbreviations like 'bach.', 'kand.', 'prof.bach.', 'ph.d.' as-is.",
    "EDU_udd": "Danish higher education program code (UDD classification). Translate program names. Keep degree abbreviations as-is.",
    "EDU_disced": "DISCED education classification code. Translate field names. Keep compound codes in parentheses.",
    "EDU_field": "Danish education field classification. Translate field names to English.",
    "EDU_course": "Danish education course type.",
    "EDU_fag": "Danish school subject code.",
    "EDU_grade": "Danish education grade/score.",
    "EDU_afg": "Danish education completion type.",
    # Labor
    "LAB_disco": "DISCO occupational classification (Danish version of ISCO). Translate job titles and occupational descriptions.",
    "LAB_disco08": "DISCO-08 occupational classification. Translate job titles and occupational descriptions.",
    "LAB_db07": "DB07 industry classification (Danish version of NACE Rev. 2). Translate industry/sector names.",
    "LAB_nace": "NACE industry classification (1992-2007 Danish industries). Translate industry/sector names.",
    "LAB_branche": "Danish industry branch code (branche77 format). Translate industry names.",
    "LAB_soc": "Danish socio-economic status classification.",
    "LAB_socio13": "Danish socio-economic status classification (13-category).",
    "LAB_tilstand": "Danish employment status/condition code.",
    # Social/criminal
    "SOC_ger7": "Danish criminal offense code (GER7 classification). Translate offense descriptions. 'Forbr.' = crime/offense.",
    "SOC_frakkod": "Danish driver's license disqualification code. Translate legal descriptions.",
    "SOC_afgtypko": "Danish criminal sentence type code.",
    "SOC_pgf": "Danish legal paragraph reference.",
    "SOC_ansted": "Danish institutional placement type code.",
    "SOC_frakbkod": "Danish conditional disqualification code.",
    "SOC_fgslkod": "Danish prison/detention code.",
    # Demographics
    "DEM_far": "Danish father-child relationship code.",
    "DEM_mor": "Danish mother-child relationship code.",
    "DEM_civst": "Danish civil/marital status code.",
    "DEM_fm": "Danish family structure code.",
}


def load_master():
    rows = []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append(dict(row))
    return rows, fieldnames


def save_master(rows, fieldnames):
    with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def find_rows_to_retranslate(rows, categories=None):
    """Find all rows that were translated by MarianMT and need redoing."""
    phase0_cats = {"DEM_kom", "DEM_opr", "DEM_statsb"}
    targets = []

    for i, row in enumerate(rows):
        da = row["description_da"].strip()
        en = row["description_en"].strip()
        cat = row["category"]
        src = row.get("source", "")

        if not da or not en:
            continue
        if cat in phase0_cats:
            continue  # Place names, handled by Phase 0
        if src.endswith("|icd8_raw") or src == "none|icd8_raw":
            continue  # Latin ICD-8, fine as-is
        if not row["description_da"].strip():
            continue  # No Danish source = was already English

        # Check if this was a Phase 0 "already English" detection
        # Those have da != en and da was set by add_language_columns.py
        # If da is empty, it was English-only
        if da == en:
            # This could be an identical copy or Phase 0 English detection
            # Skip if it looks English already
            if not re.search(r"[æøåÆØÅ]", da) and not re.search(
                r"\b(og|med|til|af|ved|eller|som|ikke)\b", da.lower()
            ):
                continue

        if categories and cat not in categories:
            continue

        targets.append(i)

    return targets


def translate_batch(model, tokenizer, descriptions, category, device):
    """Translate a batch of descriptions using the LLM."""
    context = CATEGORY_CONTEXT.get(category, f"Danish administrative register code ({category}).")

    items = "\n".join(f"{j+1}. {desc}" for j, desc in enumerate(descriptions))
    prompt = f"""Translate each Danish description to English.

Context: {context}

Rules:
- Translate ALL Danish words to English completely. No Danish words should remain in the output.
- Use standard English terminology for the domain.
- 'UNS' in medical codes → 'NOS' (Not Otherwise Specified)
- 'IKA' in medical codes → 'NEC' (Not Elsewhere Classified)
- Keep numbers, parenthetical references like "(via 51)" unchanged.
- Keep degree abbreviations like "bach.", "kand.", "ph.d." as-is.
- Do NOT repeat words or produce garbled output.
- Reply with ONLY the numbered translations, one per line.

{items}"""

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    import torch
    inputs = tokenizer(text, return_tensors="pt").to(device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=1500,
            do_sample=False,
        )

    response = tokenizer.decode(
        output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
    ).strip()

    # Parse numbered responses
    results = {}
    lines = response.strip().split("\n")
    for j, desc in enumerate(descriptions):
        pattern = rf"^{j+1}[\.\)]\s*(.+)"
        for line in lines:
            m = re.match(pattern, line.strip())
            if m:
                trans = m.group(1).strip()
                # Validate: not empty, not garbled
                if trans and not _is_garbled(trans):
                    results[desc] = trans
                break
        else:
            # Fallback for single-item batches
            if len(descriptions) == 1 and lines:
                trans = re.sub(r"^\d+[\.\)]\s*", "", lines[0]).strip()
                if trans and not _is_garbled(trans):
                    results[desc] = trans

    return results


def _is_garbled(text):
    """Check if translation is garbled (excessive repetition)."""
    words = text.split()
    if len(words) > 8:
        from collections import Counter
        counts = Counter(words)
        most_common_count = counts.most_common(1)[0][1]
        if most_common_count > len(words) * 0.4:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--gpu", type=int, default=1, help="GPU ID (default: 1 = A5000)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-14B-Instruct")
    parser.add_argument("--category", nargs="*", help="Only retranslate specific categories")
    parser.add_argument("--checkpoint-interval", type=int, default=500)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from tqdm import tqdm

    rows, fieldnames = load_master()
    print(f"Loaded {len(rows)} rows")

    categories = set(args.category) if args.category else None
    targets = find_rows_to_retranslate(rows, categories)
    print(f"Rows to retranslate: {len(targets)}")

    # Group by category for context-aware translation, then deduplicate
    cat_desc_indices = defaultdict(lambda: defaultdict(list))
    for idx in targets:
        cat = rows[idx]["category"]
        da = rows[idx]["description_da"]
        cat_desc_indices[cat][da].append(idx)

    total_unique = sum(len(descs) for descs in cat_desc_indices.values())
    print(f"Unique descriptions: {total_unique}")
    print(f"Categories: {', '.join(sorted(cat_desc_indices.keys()))}")

    # Load model
    device = f"cuda:{args.gpu}"
    print(f"\nLoading {args.model} 4-bit on {device}...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map={"": args.gpu},
        dtype=torch.float16,
        use_safetensors=True,
        attn_implementation="eager",
    )
    model.eval()
    print("Model loaded\n")

    # Translate category by category
    total_translated = 0
    total_applied = 0
    t0 = time.time()

    for cat in sorted(cat_desc_indices.keys()):
        desc_indices = cat_desc_indices[cat]
        unique_descs = list(desc_indices.keys())
        n_batches = (len(unique_descs) + args.batch_size - 1) // args.batch_size

        cat_translations = {}
        print(f"--- {cat}: {len(unique_descs)} unique descriptions ---")

        iterator = range(0, len(unique_descs), args.batch_size)
        for batch_start in tqdm(iterator, total=n_batches, desc=cat):
            batch = unique_descs[batch_start : batch_start + args.batch_size]
            results = translate_batch(model, tokenizer, batch, cat, device)
            cat_translations.update(results)

            # Periodic checkpoint
            if (total_translated + len(cat_translations)) % args.checkpoint_interval < args.batch_size:
                _apply_and_save(rows, fieldnames, cat_translations, desc_indices)

        # Apply all translations for this category
        applied = _apply_and_save(rows, fieldnames, cat_translations, desc_indices)
        total_translated += len(cat_translations)
        total_applied += applied
        print(f"  Translated: {len(cat_translations)}/{len(unique_descs)}, applied to {applied} rows\n")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed/60:.1f} minutes")
    print(f"  Total translated: {total_translated}")
    print(f"  Total rows updated: {total_applied}")

    # Update description_short
    for row in rows:
        en = row.get("description_en", "").strip()
        if en:
            row["description_short"] = re.sub(r"\s*\([^)]*\)", "", en).strip()
    save_master(rows, fieldnames)
    print("  MASTER saved with updated description_short")

    # Cleanup
    del model, tokenizer
    torch.cuda.empty_cache()


def _apply_and_save(rows, fieldnames, translations, desc_indices):
    """Apply translations and save checkpoint."""
    applied = 0
    for desc, trans in translations.items():
        for idx in desc_indices[desc]:
            rows[idx]["description_en"] = trans
            applied += 1
    save_master(rows, fieldnames)
    return applied


if __name__ == "__main__":
    main()
