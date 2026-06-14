#!/usr/bin/env python3
"""Regenerate vocab_hierarchy.json from MASTER_CATEGORY_MAPPINGS.csv.

Successor to scripts/oneoff/build_token_hierarchy.py (which generated the
original file before the `.0` fix and several description corrections, and
filled synthetic group nodes with generated text). This version:

  - reads everything from MASTER (single source of truth) — token nodes carry
    both description_en and description_da;
  - labels synthetic orphan-group nodes (hierarchy parents that are not
    tokens, e.g. NACE groups, DISCED programme groups) from the official
    reference files via scripts/describe_vocab.py instead of "Group X";
  - keeps the original output schema: domain -> category -> _meta /
    token_ids+tokens (flat) or all_token_ids+children (hierarchical, with
    per-chapter trees for HEA_ICD10).

Usage (from the repo root):
    python3 scripts/build_vocab_hierarchy.py
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import describe_vocab as dv

MASTER_PATH = "MASTER_CATEGORY_MAPPINGS.csv"
OUTPUT_PATH = "vocab_hierarchy.json"

DOMAIN_NAMES = {
    "DEM": "Demographics",
    "EDU": "Education",
    "HEA": "Health",
    "LAB": "Labor market",
    "SOC": "Social and criminal justice",
    "SPECIAL": "Special tokens",
}

# ICD-10 chapter names (Danish SKS chapter prefix -> WHO chapter title).
ICD10_CHAPTERS = {
    "DA": "Certain infectious and parasitic diseases",
    "DB": "Neoplasms",
    "DC": "Malignant neoplasms",
    "DD": "Neoplasms (benign, in situ, uncertain)",
    "DE": "Endocrine, nutritional and metabolic diseases",
    "DF": "Mental and behavioural disorders",
    "DG": "Diseases of the nervous system",
    "DH": "Diseases of the eye, ear and mastoid process",
    "DI": "Diseases of the circulatory system",
    "DJ": "Diseases of the respiratory system",
    "DK": "Diseases of the digestive system",
    "DL": "Diseases of the skin and subcutaneous tissue",
    "DM": "Diseases of the musculoskeletal system",
    "DN": "Diseases of the genitourinary system",
    "DO": "Pregnancy, childbirth and the puerperium",
    "DP": "Certain conditions originating in the perinatal period",
    "DQ": "Congenital malformations and chromosomal abnormalities",
    "DR": "Symptoms, signs and abnormal findings",
    "DS": "Injury, poisoning and other consequences of external causes",
    "DT": "Injury, poisoning (continued) and external causes",
    "DX": "Intentional self-harm",
    "DY": "Assault and events of undetermined intent",
    "DZ": "Factors influencing health status and contact with health services",
}

# describe_vocab state, used to label synthetic (non-token) group nodes
_MASTER, _CATEGORIES = dv.load_master()
_REF_CACHE = {}


def token_node_fields(row):
    return {
        "token_id": int(row["token_id"]),
        "code": row["code"],
        "value": row["value"],
        "description_en": row["description_en"],
        "description_da": row["description_da"],
    }


def synthetic_group_label(parent_code, fallback_key):
    """Label a hierarchy parent that is not itself a token, from official refs."""
    res = dv.resolve(parent_code, _MASTER, _CATEGORIES, _REF_CACHE)
    if res["match"] in ("exact", "reference"):
        return {
            "description_en": res["description_en"] or f"Group {fallback_key}",
            "description_da": res["description_da"],
            "label_source": (res["en_source"] or res["da_source"]),
        }
    return {"description_en": f"Group {fallback_key}", "description_da": "",
            "label_source": ""}


def build_flat_category(cat, rows):
    tokens = sorted((token_node_fields(r) for r in rows), key=lambda t: t["value"])
    return {
        "_meta": {"name": cat, "count": len(tokens), "hierarchical": False},
        "token_ids": [t["token_id"] for t in tokens],
        "tokens": tokens,
    }


def make_subtree_builder(code_to_row, code_to_children):
    def build_subtree(code):
        row = code_to_row[code]
        node = token_node_fields(row)
        node["level"] = row.get("hierarchy_level", "")
        children_codes = code_to_children.get(code, [])
        if children_codes:
            children = {}
            child_ids = []
            for cc in sorted(children_codes):
                cn = build_subtree(cc)
                children[code_to_row[cc]["value"]] = cn
                child_ids.extend(cn["all_token_ids"])
            node["children"] = children
            node["all_token_ids"] = [node["token_id"]] + child_ids
        else:
            node["all_token_ids"] = [node["token_id"]]
        return node
    return build_subtree


def build_hierarchical_category(cat, rows):
    code_to_row = {r["code"]: r for r in rows}
    code_to_children = defaultdict(list)
    for r in rows:
        parent = r.get("parent_code", "").strip()
        if parent:
            code_to_children[parent].append(r["code"])

    roots, orphans = [], []
    for r in rows:
        parent = r.get("parent_code", "").strip()
        if not parent:
            roots.append(r["code"])
        elif parent not in code_to_row:
            orphans.append(r["code"])

    if cat == "HEA_ICD10":
        return build_icd10_hierarchy(rows, code_to_row, code_to_children)

    orphan_groups = defaultdict(list)
    for code in orphans:
        orphan_groups[code_to_row[code]["parent_code"].strip()].append(code)

    build_subtree = make_subtree_builder(code_to_row, code_to_children)
    tree = {}
    all_token_ids = []
    for code in sorted(roots):
        node = build_subtree(code)
        tree[code_to_row[code]["value"]] = node
        all_token_ids.extend(node["all_token_ids"])

    for missing_parent, child_codes in sorted(orphan_groups.items()):
        group_children = {}
        group_token_ids = []
        for code in sorted(child_codes):
            node = build_subtree(code)
            group_children[code_to_row[code]["value"]] = node
            group_token_ids.extend(node["all_token_ids"])
        group_key = missing_parent.replace(f"{cat}_", "")
        tree[group_key] = {
            "synthetic": True,
            **synthetic_group_label(missing_parent, group_key),
            "children": group_children,
            "all_token_ids": group_token_ids,
        }
        all_token_ids.extend(group_token_ids)

    return {
        "_meta": {"name": cat, "count": len(rows), "hierarchical": True,
                  "roots": len(roots), "orphan_groups": len(orphan_groups)},
        "all_token_ids": all_token_ids,
        "children": tree,
    }


def build_icd10_hierarchy(rows, code_to_row, code_to_children):
    """Per-chapter trees (DA..DZ), plus ICD-8 and supplementary-prefix groups."""
    build_subtree = make_subtree_builder(code_to_row, code_to_children)

    chapter_blocks = defaultdict(list)
    for r in rows:
        val = r["value"]
        if not val.isdigit() and len(val) >= 2 and val[:1] == "D" and val[1:2].isalpha():
            chapter_blocks[val[:2]].append(r)

    chapters = {}
    all_ids = []
    placed = set()

    def place(code):
        placed.add(code)
        for cc in code_to_children.get(code, []):
            place(cc)

    for ch in sorted(ICD10_CHAPTERS):
        if ch not in chapter_blocks:
            continue
        ch_children = {}
        ch_ids = []
        # roots of the chapter tree: blocks / codes whose parent is missing
        for r in chapter_blocks[ch]:
            parent = r.get("parent_code", "").strip()
            if (not parent or parent not in code_to_row) and r["code"] not in placed:
                node = build_subtree(r["code"])
                ch_children[r["value"]] = node
                ch_ids.extend(node["all_token_ids"])
                place(r["code"])
        # anything in the chapter still unplaced (nested under placed parents
        # is already covered; this catches odd cases)
        for r in chapter_blocks[ch]:
            if r["code"] not in placed:
                node = build_subtree(r["code"])
                ch_children[r["value"]] = node
                ch_ids.extend(node["all_token_ids"])
                place(r["code"])
        chapters[ch] = {
            "description_en": ICD10_CHAPTERS[ch],
            "children": ch_children,
            "all_token_ids": ch_ids,
        }
        all_ids.extend(ch_ids)

    other_groups = defaultdict(list)
    for r in rows:
        if r["code"] not in placed:
            val = r["value"]
            key = "ICD8" if val.isdigit() else (val[:2] if len(val) >= 2 else "other")
            other_groups[key].append(r)

    for grp in sorted(other_groups):
        grp_children = {}
        grp_ids = []
        for r in other_groups[grp]:
            if r["code"] in placed:
                continue
            node = build_subtree(r["code"])
            grp_children[r["value"]] = node
            grp_ids.extend(node["all_token_ids"])
            place(r["code"])
        desc = "ICD-8 legacy codes" if grp == "ICD8" else f"Supplementary codes ({grp})"
        chapters[grp] = {
            "description_en": desc,
            "children": grp_children,
            "all_token_ids": grp_ids,
        }
        all_ids.extend(grp_ids)

    return {
        "_meta": {"name": "HEA_ICD10", "count": len(rows), "hierarchical": True,
                  "chapters": len(chapters)},
        "all_token_ids": all_ids,
        "children": chapters,
    }


def validate(hierarchy, rows):
    expected = {int(r["token_id"]) for r in rows}
    seen = []

    def collect(node):
        if not isinstance(node, dict):
            return
        if "token_id" in node:
            seen.append(node["token_id"])
        for t in node.get("tokens", []):
            seen.append(t["token_id"])
        for child in node.get("children", {}).values():
            collect(child)

    for domain in hierarchy.values():
        for key, val in domain.items():
            if key != "_meta":
                collect(val)

    seen_set = set(seen)
    dupes = len(seen) - len(seen_set)
    missing, extra = expected - seen_set, seen_set - expected
    print(f"validate: {len(seen)} placements, {len(seen_set)} unique, "
          f"{dupes} duplicates, missing={len(missing)}, extra={len(extra)}")
    return not missing and not extra and not dupes


def main():
    with open(MASTER_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    domain_cats = defaultdict(lambda: defaultdict(list))
    for r in rows:
        domain_cats[r["prefix"]][r["category"]].append(r)

    hierarchy = {}
    for domain in sorted(domain_cats):
        node = {"_meta": {
            "name": DOMAIN_NAMES.get(domain, domain),
            "count": sum(len(v) for v in domain_cats[domain].values()),
        }}
        for cat in sorted(domain_cats[domain]):
            cat_rows = domain_cats[domain][cat]
            variable = cat_rows[0]["variable"]
            if any(r.get("parent_code", "").strip() for r in cat_rows):
                node[variable] = build_hierarchical_category(cat, cat_rows)
            else:
                node[variable] = build_flat_category(cat, cat_rows)
        hierarchy[domain] = node

    ok = validate(hierarchy, rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, ensure_ascii=False, indent=2)
    import os
    print(f"wrote {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH) / 1e6:.1f} MB)")
    if not ok:
        sys.exit("VALIDATION FAILED")


if __name__ == "__main__":
    main()
