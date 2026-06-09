#!/usr/bin/env python3
"""Normalize the 769 '.0' float-style codes in vocab.json, archive/vocab_2.json, and
MASTER_CATEGORY_MAPPINGS.csv into plain integer codes.

Rule:
  - Twin pair (both `X` and `X.0` exist, same description):
      delete the `X.0` entry. Its token_id becomes unused (a hole — safe for
      transformer models; embedding row is simply never looked up).
  - Orphan (only `X.0` exists, no integer twin):
      rename the key `X.0` → `X`. Token_id is preserved.

After this operation:
  - vocab has zero keys ending in `.0`
  - Upstream tokenization code should cast numeric codes to int before
    string-formatting (so record "101110.0" → "101110" on lookup); a
    2-line preprocessing hook makes both past and future data map to
    the same integer-keyed token_id.

The script edits all three files in-place (unless --dry-run).

Usage:
    python3 scripts/normalize_float_codes.py [--dry-run]
"""
import argparse
import csv
import json
import os
from collections import Counter

VOCAB_FILES = ["vocab.json", "archive/vocab_2.json"]
MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"


def plan_for_vocab(vocab):
    """Return (renames, deletions) lists for one vocab dict."""
    renames = []   # (old_key, new_key)
    deletions = []  # keys to remove
    for k in list(vocab.keys()):
        if not k.endswith(".0"):
            continue
        int_k = k[:-2]
        if int_k in vocab:
            # Twin: delete the .0 key; the int version already owns a token_id
            deletions.append(k)
        else:
            # Orphan: rename in place
            renames.append((k, int_k))
    return renames, deletions


def apply_vocab(vocab, renames, deletions):
    out = dict(vocab)
    for old, new in renames:
        out[new] = out.pop(old)
    for k in deletions:
        del out[k]
    return out


def process_vocab_file(path, dry_run):
    if not os.path.exists(path):
        print(f"  [skip] {path} not found")
        return None
    with open(path) as f:
        vocab = json.load(f)
    before = len(vocab)
    renames, deletions = plan_for_vocab(vocab)
    new_vocab = apply_vocab(vocab, renames, deletions)
    print(f"  {path}: {before} → {len(new_vocab)} entries "
          f"({len(renames)} renamed, {len(deletions)} deleted)")
    if not dry_run:
        with open(path, "w") as f:
            json.dump(new_vocab, f, indent=2, ensure_ascii=False)
    return renames, deletions


def process_master(renames_union, deletions_union, dry_run):
    """Apply the same renames/deletions to MASTER. Keys in vocab map to codes
    in MASTER by the form f'{prefix}_{variable}_{value}' where value is the
    part that carries the optional '.0'. We match on MASTER 'code' column
    against the vocab key directly (they are identical)."""
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    rename_map = dict(renames_union)  # old_code → new_code
    delete_set = set(deletions_union)

    kept = []
    renamed = 0
    deleted = 0
    for r in rows:
        code = r["code"]
        if code in delete_set:
            deleted += 1
            continue
        if code in rename_map:
            new_code = rename_map[code]
            r["code"] = new_code
            # Also normalize the value column (strip trailing .0)
            if r.get("value", "").endswith(".0"):
                r["value"] = r["value"][:-2]
            renamed += 1
        kept.append(r)

    print(f"  MASTER: renamed {renamed}, deleted {deleted}, "
          f"{len(rows)} → {len(kept)} rows")

    if not dry_run:
        with open(MASTER_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("Processing vocab files:")
    all_renames = []
    all_deletions = []
    for path in VOCAB_FILES:
        res = process_vocab_file(path, args.dry_run)
        if res is not None:
            r, d = res
            all_renames.extend(r)
            all_deletions.extend(d)

    # Union (same codes show up in both vocab files with the same status,
    # but dedupe just in case)
    renames_union = list({(old, new) for old, new in all_renames})
    deletions_union = list({k for k in all_deletions})

    print(f"\nUnion across vocab files: {len(renames_union)} renames, "
          f"{len(deletions_union)} deletions")

    # Apply to MASTER
    print("\nProcessing MASTER:")
    process_master(renames_union, deletions_union, args.dry_run)

    print("\nSamples:")
    for old, new in list({(o, n) for o, n in all_renames})[:6]:
        print(f"  rename  {old}  →  {new}")
    for k in list({d for d in all_deletions})[:6]:
        print(f"  delete  {k}")

    if args.dry_run:
        print("\n[dry-run] no changes written")
        return

    # Regenerate MAPPINGS/ after MASTER changes
    print("\nRegenerating MAPPINGS/...")
    os.system("python3 scripts/regenerate_mappings.py 2>&1 | tail -3")


if __name__ == "__main__":
    main()
