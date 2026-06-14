#!/usr/bin/env python3
"""Sync the per-category code-definition CSVs with the post-`.0`-fix vocab.

The 2026 `.0` float-bug fix (docs/notes.md §4) was applied to vocab.json and
MASTER_CATEGORY_MAPPINGS.csv but never to the per-category code-definition
files under hierarchical_vocab/{DEM,EDU,HEA,LAB,SOC,SPECIAL}/, which stayed at
the original 41,201-code state. This script applies the same two resolutions:

  - Twins  (both `X` and `X.0` rows in the file): delete the `.0` row.
  - Orphans (only `X.0` in the file):             rename code/value to `X`,
                                                  keep the token_id.

Run from the repo root. Verifies afterwards that the union of codes across all
code-definition files equals vocab.json exactly, with matching token IDs.
"""

import csv
import glob
import json
import sys

vocab = json.load(open("vocab.json"))

files = sorted(
    p
    for p in glob.glob("hierarchical_vocab/*/*.csv")
    if "/MAPPINGS/" not in p and "/MISSING/" not in p
)

n_twins_deleted = 0
n_orphans_renamed = 0
all_codes = {}

for path in files:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    codes_in_file = {r["code"] for r in rows}
    out = []
    changed = False
    for r in rows:
        code = r["code"]
        if code.endswith(".0"):
            int_code = code[:-2]
            if int_code in codes_in_file:
                # Twin: the int row already exists; the .0 entry was deleted
                # from vocab, so drop it here too.
                assert int_code in vocab, f"{path}: twin target {int_code} not in vocab"
                assert code not in vocab, f"{path}: twin {code} still in vocab?"
                n_twins_deleted += 1
                changed = True
                continue
            # Orphan: renamed X.0 -> X in vocab with token_id preserved.
            assert int_code in vocab, f"{path}: orphan target {int_code} not in vocab"
            assert str(vocab[int_code]) == r["token_id"], (
                f"{path}: token_id mismatch for {code}: "
                f"file={r['token_id']} vocab={vocab[int_code]}"
            )
            r["code"] = int_code
            if r["value"].endswith(".0"):
                r["value"] = r["value"][:-2]
            n_orphans_renamed += 1
            changed = True
        out.append(r)

    if changed:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(out)

    for r in out:
        all_codes[r["code"]] = r["token_id"]

print(f"files scanned:    {len(files)}")
print(f"twins deleted:    {n_twins_deleted}")
print(f"orphans renamed:  {n_orphans_renamed}")

# Full verification against vocab.json
vk = set(vocab)
ck = set(all_codes)
errors = []
if ck != vk:
    errors.append(f"code sets differ: extra={sorted(ck - vk)[:5]} missing={sorted(vk - ck)[:5]}")
bad_ids = [c for c in ck if str(vocab[c]) != all_codes[c]]
if bad_ids:
    errors.append(f"token_id mismatches: {bad_ids[:5]}")
if errors:
    sys.exit("VERIFICATION FAILED: " + "; ".join(errors))
print(f"verified: {len(ck)} codes across code-def files == vocab.json, all token IDs match")
