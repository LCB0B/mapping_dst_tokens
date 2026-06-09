#!/usr/bin/env python3
"""Improved Danish→English re-translation using Claude API or a local LLM.

Improvements over retranslate_with_llm.py:
  1. Supports Anthropic Claude API as the primary backend (best quality).
     Falls back to local Qwen2.5-14B if ANTHROPIC_API_KEY is unset.
  2. Much stricter prompt with in-context examples for each category.
  3. JSON-structured output (one item at a time) for reliable parsing —
     avoids MarianMT-style hallucinations ("Møbelsnedker" →
     "Sub-contracted operations...") and Qwen's repetition glitches.
  4. Per-item validation: rejects translations that still contain Danish
     characters (æ/ø/å), repeat themselves, or equal the input.
  5. Targets only truly-Danish rows (DA has Danish chars or known stems).
     Rows where DA/EN match but are actually English pass through.
  6. Latin ICD-8 medical terms and proper nouns are preserved.

Usage:
    # Claude API (requires ANTHROPIC_API_KEY)
    python3 scripts/retranslate_v2.py --backend claude

    # Local Qwen fallback (requires GPU + transformers)
    python3 scripts/retranslate_v2.py --backend local --gpu 1

    # Limit scope
    python3 scripts/retranslate_v2.py --backend claude --category HEA_ICD10 EDU_audd
    python3 scripts/retranslate_v2.py --backend claude --limit 50   # dry test
"""
import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"

# ─── Category context with concrete in-context examples ──────────────────
# Each value is a tuple (domain_description, list_of_example_pairs).
CATEGORY_CONTEXT = {
    "HEA_ICD10": (
        "ICD-10 medical diagnosis code (Danish hospital classification). "
        "Use standard English medical terminology. 'UNS' = 'NOS' (Not Otherwise Specified). "
        "'IKA' = 'NEC' (Not Elsewhere Classified). Keep Latin species/anatomical names.",
        [
            ("Type 2-diabetes UNS", "Type 2 diabetes, NOS"),
            ("Kronisk posttraumatisk hovedpine", "Chronic post-traumatic headache"),
            ("Galdestenskolik UNS", "Gallstone colic, NOS"),
            ("Astma UNS", "Asthma, NOS"),
            ("Rask ledsager", "Healthy companion"),
        ],
    ),
    "HEA_speciale": (
        "Danish medical-specialty-plus-procedure code (hospital department + service). "
        "Format is usually 'Specialty, procedure'. Keep abbreviations (v., flg., kons.) expanded.",
        [
            ("Øjenlægehjælp, 1.Konsultation", "Ophthalmology service, 1st consultation"),
            ("Ørelægehjælp, Toneaudiometri", "ENT service, Pure-tone audiometry"),
            ("Almen lægehjælp 80, Blodprøvetagning", "General practitioner 80, Blood sampling"),
            ("Psykiatri, Pårørende konsultati", "Psychiatry, Family member consultation"),
            ("Kirurgi, Operat. Åreknuder 1.", "Surgery, Varicose vein operation, 1st"),
        ],
    ),
    "HEA_atc": (
        "ATC pharmaceutical classification. Format is usually 'drug_class, specific_substance'. "
        "Use English INN drug names. Examples of class translations below.",
        [
            ("sulfonylcarbamid, glibenclamid", "sulfonylureas, glibenclamide"),
            ("beta-lactamase resistente penicilliner, dicloxacillin",
             "beta-lactamase resistant penicillins, dicloxacillin"),
            ("thyroideahormoner, liothyroninnatrium", "thyroid hormones, liothyronine sodium"),
            ("antiallergiske midler, excl. kortikosteroider, azelastin",
             "antiallergic agents, excl. corticosteroids, azelastine"),
            ("meningokok vacciner, meningococcus A,C,Y,W-135, tetravalent renset polysaccharid",
             "meningococcal vaccines, meningococcus A,C,Y,W-135, tetravalent purified polysaccharide"),
        ],
    ),
    "EDU_audd": (
        "Danish education program code (AUDD classification). Translate program names. "
        "Keep degree abbreviations (bach., kand., prof.bach., ph.d.) as-is.",
        [
            ("Møbelsnedker", "Furniture maker / Cabinetmaker"),
            ("Gourmetslagteraspirant", "Gourmet butcher apprentice"),
            ("Vvs-uddannelse una", "Plumbing education, unspecified"),
            ("Landbrugets driftlederkursus", "Agricultural farm manager course"),
            ("Akademiuddannelse i Byggeteknologi", "Academy programme in Building Technology"),
            ("Engelsk-russisk erhvervssprog, bach.", "English-Russian business language, bach."),
            ("Teknologisk diplomuddannelse i parkvirksomhed", "Technological diploma programme in park management"),
        ],
    ),
    "EDU_udd": (
        "Danish higher education program code (UDD classification). Translate program names. "
        "Keep degree abbreviations as-is.",
        [
            ("Industriteknikeruddannelsen", "Industrial technician programme"),
            ("Karrosseriteknikeruddannelsen", "Auto-body technician programme"),
            ("Tekstile erhvervsuddannelse", "Textile vocational education"),
            ("Engelsk-spansk erhvervssprog, bach.", "English-Spanish business language, bach."),
            ("Dansk-Fransk Baccalauréat", "Danish-French Baccalauréat"),
        ],
    ),
    "EDU_disced": (
        "DISCED education classification. Translate field names; keep compound codes in parentheses.",
        [
            ("Byggeteknik", "Building technology"),
            ("Socialt arbejde", "Social work"),
        ],
    ),
    "EDU_field": (
        "Danish education field classification.",
        [("Teknik og it", "Engineering and IT"), ("Humanistisk og kunstnerisk", "Humanities and arts")],
    ),
    "LAB_disco": (
        "DISCO occupational classification. 'Arbejde' often means 'work/occupations'. "
        "'(via NNN)' references a parent code — keep the parenthetical unchanged.",
        [
            ("Almindeligt kontorarbejde", "General office work"),
            ("Elektrikerarbejde", "Electrician work"),
            ("Bartenderarbejde (via 5132)", "Bartending work (via 5132)"),
            ("Jordemoderarbejde", "Midwifery work"),
            ("Sygeplejerskearbejde (via 2221)", "Nursing work (via 2221)"),
            ("Stenhuggerarbejde", "Stonemasonry work"),
        ],
    ),
    "LAB_disco08": (
        "DISCO-08 occupational classification. Keep '(via NNNN)' parentheticals unchanged.",
        [
            ("Akademikere (via 2)", "Academics / Professionals (via 2)"),
            ("Ledere (via 1)", "Managers (via 1)"),
            ("Kemikere (via 2113)", "Chemists (via 2113)"),
            ("Tjenere (via 5131)", "Waiters (via 5131)"),
            ("VVS-arbejdere (via 7126)", "Plumbers (via 7126)"),
        ],
    ),
    "LAB_db07": (
        "DB07 industry classification (Danish NACE Rev. 2). Keep '(via NNN)' unchanged.",
        [
            ("Elforsyning (via 351)", "Electricity supply (via 351)"),
            ("Hospitaler (via 861)", "Hospitals (via 861)"),
            ("Genbrug (via 383)", "Recycling (via 383)"),
            ("Vandforsyning (via 360)", "Water supply (via 360)"),
        ],
    ),
    "LAB_nace": (
        "NACE industry classification (1992-2007 Danish industries).",
        [("Fremstilling af møbler", "Manufacture of furniture")],
    ),
    "LAB_branche": (
        "Danish industry branch (branche77). Translate industry names fully.",
        [("Bygge- og anlægsvirksomhed", "Construction and civil-engineering activities")],
    ),
    "SOC_ger7": (
        "Danish criminal offense code (GER7). 'Forbr.' = 'offences'. Keep '(via NNNN)' unchanged.",
        [
            ("Alvorligere vold (via 1255)", "Aggravated violence (via 1255)"),
            ("Brandstiftelse (via 1312)", "Arson (via 1312)"),
            ("Manddrab (via 1230)", "Homicide (via 1230)"),
            ("Trusler (via 1292)", "Threats (via 1292)"),
            ("Uagtsomt manddrab/legemsbesk. (via 1283)",
             "Negligent homicide/bodily harm (via 1283)"),
        ],
    ),
    "SOC_pgf": (
        "Danish legal paragraph reference. Translate Danish law names to English but keep paragraph numbers.",
        [("Straffeloven § 245", "Criminal Code § 245")],
    ),
    "SOC_ansted": (
        "Danish institutional placement type. Translate care/institution types.",
        [
            ("Almindelig plejefamilie, generelt godkendt",
             "Ordinary foster family, generally approved"),
            ("Skibsprojekt", "Ship project"),
        ],
    ),
    "LAB_soc": (
        "Danish socio-economic status categories.",
        [
            ("Folkepension", "State pension"),
            ("Feriedagpenge", "Holiday unemployment benefit"),
            ("Ledighedsydelse", "Unemployment benefit"),
            ("Revalidering", "Vocational rehabilitation"),
            ("Seniorpension", "Senior pension"),
        ],
    ),
    "LAB_tilstand": (
        "Danish employment status/condition code.",
        [
            ("Arbejdsmarkedsydelse", "Labor-market benefit"),
            ("Fleksydelse", "Flex-job benefit"),
            ("G-dage", "Unemployment compensation days (G-dage)"),
            ("Tjenestemandspension", "Civil servant pension"),
            ("Virksomhedspraktik", "Company internship"),
        ],
    ),
}


# ─── Danish detection ──────────────────────────────────────────────────────
DANISH_CHARS = re.compile(r"[æøåÆØÅ]")
DANISH_MARKERS = re.compile(
    r"\b(og|med|til|af|ved|eller|der|som|ikke|ikka|øvrige|"
    r"uddannelse|uddannelsen|uddannelser|arbejde|arbejder|arbejdet|"
    r"hjælp|behandling|undersøgelse|tekniker|teknikere|virksomhed|"
    r"lægehjælp|tjeneste|ydelse|forsikring|pension|foranstaltning|"
    r"kirurgi|psykiatri|medicin|aspirant|erhvervs|videre|"
    r"kommune|kontor|salg|service|operation|fremstilling|"
    r"bach|kand|prof|ph\.d|una|igv|uns|ika)\b",
    re.IGNORECASE,
)
LATIN_MEDICAL = re.compile(
    r"\b\w*(us|um|ae|is|osis|itis|oma|rum|ium|asis|osus|ans|atus|"
    r"ica|ici|orum|atis|eris)\b",
    re.IGNORECASE,
)


def is_danish(text: str) -> bool:
    if not text:
        return False
    if DANISH_CHARS.search(text):
        return True
    if DANISH_MARKERS.search(text):
        return True
    # Danish compound suffixes without word boundaries
    if re.search(r"(uddannelse|arbejde|hjælp|tjeneste|ydelse|kirurgi)", text, re.I):
        return True
    return False


def looks_latin_medical(text: str) -> bool:
    if DANISH_CHARS.search(text):
        return False
    words = text.split()
    if len(words) < 2:
        return False
    hits = len(LATIN_MEDICAL.findall(text))
    return hits / max(len(words), 1) > 0.3


def is_repetitive(text: str) -> bool:
    words = text.split()
    if len(words) < 8:
        return False
    c = Counter(words)
    return c.most_common(1)[0][1] >= len(words) * 0.4


def validate_translation(da: str, en: str) -> tuple[bool, str]:
    """Return (ok, reason_if_not)."""
    en = en.strip()
    if not en:
        return False, "empty"
    if DANISH_CHARS.search(en):
        return False, "contains Danish chars"
    if is_repetitive(en):
        return False, "repetitive"
    if en.lower() == da.lower() and is_danish(da):
        return False, "identical to Danish source"
    if len(en) > max(60, len(da) * 4) and len(da) < 30:
        return False, "suspicious length blow-up"
    return True, ""


# ─── Row selection ─────────────────────────────────────────────────────────

def find_rows_to_retranslate(rows, categories=None, only_identical=False):
    """Find rows whose description_en still looks Danish or is empty."""
    skip_cats = {"DEM_kom", "DEM_opr", "DEM_statsb"}
    targets = []
    for i, r in enumerate(rows):
        da = r["description_da"].strip()
        en = r["description_en"].strip()
        cat = r["category"]
        src = r.get("source", "")
        if cat in skip_cats:
            continue
        if src.endswith("|icd8_raw") or src == "none|icd8_raw":
            continue
        if not da:
            continue
        if categories and cat not in categories:
            continue
        # Keep Latin medical unchanged
        if looks_latin_medical(en) and not DANISH_CHARS.search(en):
            continue
        # Empty EN
        if not en:
            targets.append(i)
            continue
        # EN still looks Danish
        if is_danish(en):
            if only_identical and da != en:
                # Skip if EN differs from DA but is still Danish — likely a bad MT
                targets.append(i)
            else:
                targets.append(i)
    return targets


# ─── Claude backend ────────────────────────────────────────────────────────

def translate_with_claude(items, category, client, model):
    """Translate a list of Danish strings via Claude API, one call per batch."""
    domain, examples = CATEGORY_CONTEXT.get(
        category, (f"Danish administrative register code ({category}).", [])
    )
    example_text = ""
    if examples:
        example_text = "\n\nExamples:\n" + "\n".join(
            f"  {i+1}. Danish: {da}  →  English: {en}" for i, (da, en) in enumerate(examples)
        )

    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(items))
    prompt = f"""You are translating short Danish administrative/medical codes into English.

Domain context: {domain}{example_text}

Rules:
- Translate ALL Danish words. No Danish should remain in your output.
- Keep numbers, codes, and parenthetical references like "(via 51)" exactly.
- Keep Latin species/drug names (e.g. glibenclamide, liothyronine) as-is.
- "UNS" → "NOS", "IKA" → "NEC", "una" → "unspecified".
- Prefer concise standard English terminology for the domain.
- If the input is already English, repeat it unchanged.
- Respond with ONLY a JSON array of English strings, same length and order as input.

Danish inputs:
{numbered}

Respond with a JSON array only, no prose."""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip potential code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        arr = json.loads(text)
    except json.JSONDecodeError:
        # Attempt to extract JSON array
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            return {}
        arr = json.loads(m.group(0))
    if not isinstance(arr, list) or len(arr) != len(items):
        return {}
    return dict(zip(items, [str(x) for x in arr]))


def run_claude(rows, targets, batch_size, model, checkpoint_path, fieldnames):
    try:
        import anthropic  # type: ignore
    except ImportError:
        print("ERROR: anthropic SDK not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(2)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(2)

    client = anthropic.Anthropic()

    # Group by category for per-category context
    cat_desc_idx = defaultdict(lambda: defaultdict(list))
    for i in targets:
        cat_desc_idx[rows[i]["category"]][rows[i]["description_da"]].append(i)

    translated = 0
    applied = 0
    failed = 0

    for cat, desc_map in sorted(cat_desc_idx.items()):
        uniq = list(desc_map.keys())
        print(f"\n--- {cat}: {len(uniq)} unique descriptions ---")

        for start in range(0, len(uniq), batch_size):
            batch = uniq[start : start + batch_size]
            try:
                results = translate_with_claude(batch, cat, client, model)
            except Exception as e:
                print(f"  [batch {start}] API error: {e}")
                failed += len(batch)
                continue

            for da in batch:
                if da not in results:
                    failed += 1
                    continue
                en = results[da].strip()
                ok, reason = validate_translation(da, en)
                if not ok:
                    print(f"  rejected ({reason}): {da!r} → {en!r}")
                    failed += 1
                    continue
                for idx in desc_map[da]:
                    rows[idx]["description_en"] = en
                    applied += 1
                translated += 1

            print(f"  batch {start//batch_size + 1}: "
                  f"ok={translated}, applied={applied}, failed={failed}")
            # Checkpoint
            _save(rows, fieldnames, checkpoint_path)

    print(f"\nTotal translated: {translated}, applied: {applied}, failed: {failed}")


# ─── Local (Qwen) backend ──────────────────────────────────────────────────

def run_local(rows, targets, batch_size, gpu, model_name, checkpoint_path, fieldnames):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    device = f"cuda:{gpu}"
    print(f"Loading {model_name} 4-bit on {device}...")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name, quantization_config=bnb, device_map={"": gpu},
        dtype=torch.float16, use_safetensors=True, attn_implementation="eager",
    )
    model.eval()

    cat_desc_idx = defaultdict(lambda: defaultdict(list))
    for i in targets:
        cat_desc_idx[rows[i]["category"]][rows[i]["description_da"]].append(i)

    translated = 0; applied = 0; failed = 0
    for cat, desc_map in sorted(cat_desc_idx.items()):
        uniq = list(desc_map.keys())
        print(f"\n--- {cat}: {len(uniq)} unique ---")
        for start in range(0, len(uniq), batch_size):
            batch = uniq[start : start + batch_size]
            results = _local_batch(model, tokenizer, device, batch, cat)
            for da in batch:
                en = results.get(da, "").strip()
                ok, reason = validate_translation(da, en) if en else (False, "no-output")
                if not ok:
                    failed += 1
                    continue
                for idx in desc_map[da]:
                    rows[idx]["description_en"] = en
                    applied += 1
                translated += 1
            _save(rows, fieldnames, checkpoint_path)
    del model, tokenizer
    torch.cuda.empty_cache()
    print(f"\nTotal translated: {translated}, applied: {applied}, failed: {failed}")


def _local_batch(model, tokenizer, device, items, category):
    import torch
    domain, examples = CATEGORY_CONTEXT.get(
        category, (f"Danish admin code ({category}).", []),
    )
    ex_text = "\n".join(f'  "{da}" → "{en}"' for da, en in examples)
    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(items))
    prompt = (
        f"Translate each Danish line to English.\n"
        f"Domain: {domain}\n"
        f"Examples:\n{ex_text}\n\n"
        f"Rules: no Danish left; keep parentheticals like (via 51); "
        f"'UNS'→'NOS', 'IKA'→'NEC'; respond as a JSON array of strings only.\n\n"
        f"Input:\n{numbered}\n\n"
        f"JSON array:"
    )
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=800, do_sample=False)
    resp = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    if resp.startswith("```"):
        resp = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp, flags=re.MULTILINE).strip()
    try:
        arr = json.loads(resp)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", resp, re.DOTALL)
        if not m:
            return {}
        try:
            arr = json.loads(m.group(0))
        except Exception:
            return {}
    if not isinstance(arr, list) or len(arr) != len(items):
        return {}
    return dict(zip(items, [str(x) for x in arr]))


# ─── IO ────────────────────────────────────────────────────────────────────

def _load(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        return list(reader), fieldnames


def _save(rows, fieldnames, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["claude", "local"], default="claude")
    ap.add_argument("--claude-model", default="claude-sonnet-4-6")
    ap.add_argument("--local-model", default="Qwen/Qwen2.5-14B-Instruct")
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--gpu", type=int, default=1)
    ap.add_argument("--category", nargs="*", help="Restrict to specific categories")
    ap.add_argument("--limit", type=int, default=0, help="Limit unique inputs (for testing)")
    args = ap.parse_args()

    rows, fieldnames = _load(MASTER_PATH)
    cats = set(args.category) if args.category else None
    targets = find_rows_to_retranslate(rows, cats)
    print(f"Candidate rows: {len(targets)}")
    uniq = {rows[i]["description_da"] for i in targets}
    print(f"Unique Danish strings: {len(uniq)}")

    if args.limit:
        # Keep only rows matching first N unique descs
        limited = set()
        kept = []
        for i in targets:
            d = rows[i]["description_da"]
            if d in limited or len(limited) < args.limit:
                limited.add(d)
                kept.append(i)
        targets = kept
        print(f"Limited to {len(targets)} rows, {len(limited)} unique")

    t0 = time.time()
    if args.backend == "claude":
        run_claude(rows, targets, args.batch_size, args.claude_model, MASTER_PATH, fieldnames)
    else:
        run_local(rows, targets, args.batch_size, args.gpu, args.local_model, MASTER_PATH, fieldnames)

    # Update description and description_short
    for r in rows:
        en = r.get("description_en", "").strip()
        if en:
            r["description_short"] = re.sub(r"\s*\([^)]*\)", "", en).strip()
    _save(rows, fieldnames, MASTER_PATH)
    print(f"\nDone in {(time.time()-t0)/60:.1f} min. MASTER saved.")


if __name__ == "__main__":
    main()
