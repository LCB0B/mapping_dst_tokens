#!/usr/bin/env python3
"""Build a hierarchical JSON of all 41,201 vocabulary tokens.

Organizes tokens into a tree structure:
  Domain (DEM/HEA/LAB/EDU/SOC/SPECIAL)
    → Category (kom/ICD10/disco08/...)
      → Sub-groups (chapters/blocks/groups/...)
        → Leaf tokens (token_ids)

For hierarchical categories (HEA_ICD10, HEA_atc, LAB_disco, etc.),
builds the tree from parent_code relationships + synthetic chapter nodes.

For flat categories, groups tokens directly under the category.

Output: vocab_hierarchy.json

Usage:
    python3 scripts/build_token_hierarchy.py
"""

import csv
import json
import re
from collections import defaultdict

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

# ICD-10 chapter names (Danish chapter prefix → English name)
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


def load_master():
    rows = []
    with open(MASTER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def build_hierarchy():
    rows = load_master()

    # Group rows by domain and category
    domain_cats = defaultdict(lambda: defaultdict(list))
    for row in rows:
        prefix = row["prefix"]
        cat = row["category"]
        domain_cats[prefix][cat].append(row)

    hierarchy = {}

    for domain in sorted(domain_cats.keys()):
        domain_node = {
            "_meta": {
                "name": DOMAIN_NAMES.get(domain, domain),
                "count": sum(len(v) for v in domain_cats[domain].values()),
            },
        }

        for cat in sorted(domain_cats[domain].keys()):
            cat_rows = domain_cats[domain][cat]
            variable = cat_rows[0]["variable"] if cat_rows else cat

            # Check if this is a hierarchical category
            has_hierarchy = any(r.get("parent_code", "").strip() for r in cat_rows)

            if has_hierarchy:
                cat_node = build_hierarchical_category(cat, cat_rows)
            else:
                cat_node = build_flat_category(cat, cat_rows)

            domain_node[variable] = cat_node

        hierarchy[domain] = domain_node

    return hierarchy


def build_flat_category(cat, rows):
    """Build a flat category node with all tokens listed."""
    tokens = []
    for r in rows:
        tokens.append({
            "token_id": int(r["token_id"]),
            "code": r["code"],
            "value": r["value"],
            "description_en": r["description_en"],
        })

    # Sort by value for consistency
    tokens.sort(key=lambda t: t["value"])

    return {
        "_meta": {
            "name": cat,
            "count": len(tokens),
            "hierarchical": False,
        },
        "token_ids": [t["token_id"] for t in tokens],
        "tokens": tokens,
    }


def build_hierarchical_category(cat, rows):
    """Build a tree from parent_code relationships."""
    # Index all rows by code
    code_to_row = {}
    code_to_children = defaultdict(list)
    all_codes = set()

    for r in rows:
        code = r["code"]
        code_to_row[code] = r
        all_codes.add(code)
        parent = r.get("parent_code", "").strip()
        if parent:
            code_to_children[parent].append(code)

    # Find roots: codes with no parent, or parent not in our set
    roots = []
    orphans = []  # codes whose parent doesn't exist
    for r in rows:
        parent = r.get("parent_code", "").strip()
        if not parent:
            roots.append(r["code"])
        elif parent not in all_codes:
            orphans.append(r["code"])

    # For ICD-10: create synthetic chapter nodes from orphaned parents
    if cat == "HEA_ICD10":
        return build_icd10_hierarchy(rows, code_to_row, code_to_children, roots, orphans)

    # For other hierarchical categories: group orphans by their missing parent
    # This creates synthetic intermediate nodes
    orphan_groups = defaultdict(list)
    for code in orphans:
        parent = code_to_row[code].get("parent_code", "").strip()
        orphan_groups[parent].append(code)

    # Build tree recursively
    def build_subtree(code):
        row = code_to_row[code]
        children_codes = code_to_children.get(code, [])

        node = {
            "token_id": int(row["token_id"]),
            "code": code,
            "value": row["value"],
            "description_en": row["description_en"],
            "level": row.get("hierarchy_level", ""),
        }

        if children_codes:
            children = {}
            child_token_ids = []
            for child_code in sorted(children_codes):
                child_node = build_subtree(child_code)
                children[code_to_row[child_code]["value"]] = child_node
                # Collect all token_ids in subtree
                if "all_token_ids" in child_node:
                    child_token_ids.extend(child_node["all_token_ids"])
                else:
                    child_token_ids.append(child_node["token_id"])

            node["children"] = children
            node["all_token_ids"] = [int(row["token_id"])] + child_token_ids
        else:
            node["all_token_ids"] = [int(row["token_id"])]

        return node

    # Build from real roots
    tree = {}
    all_token_ids = []

    for code in sorted(roots):
        node = build_subtree(code)
        tree[code_to_row[code]["value"]] = node
        all_token_ids.extend(node["all_token_ids"])

    # Add orphan groups as synthetic nodes
    for missing_parent, child_codes in sorted(orphan_groups.items()):
        # Create synthetic group
        group_children = {}
        group_token_ids = []
        for code in sorted(child_codes):
            node = build_subtree(code)
            group_children[code_to_row[code]["value"]] = node
            group_token_ids.extend(node["all_token_ids"])

        # Derive group name from missing parent code
        group_key = missing_parent.replace(f"{cat}_", "")
        tree[group_key] = {
            "synthetic": True,
            "description_en": f"Group {group_key}",
            "children": group_children,
            "all_token_ids": group_token_ids,
        }
        all_token_ids.extend(group_token_ids)

    return {
        "_meta": {
            "name": cat,
            "count": len(rows),
            "hierarchical": True,
            "roots": len(roots),
            "orphan_groups": len(orphan_groups),
        },
        "all_token_ids": all_token_ids,
        "children": tree,
    }


def build_icd10_hierarchy(rows, code_to_row, code_to_children, roots, orphans):
    """Special handler for ICD-10 with synthetic chapter nodes."""

    # Separate ICD-8 (numeric) from ICD-10 (D-prefixed)
    icd8_codes = []
    icd10_by_chapter = defaultdict(list)
    other_roots = []

    for r in rows:
        val = r["value"]
        code = r["code"]
        parent = r.get("parent_code", "").strip()

        if val.isdigit():
            icd8_codes.append(r)
        elif not parent:
            # Root without parent — group by first 2 chars
            chapter = val[:2] if len(val) >= 2 else "other"
            other_roots.append(r)
        else:
            pass  # has parent, will be picked up via tree traversal

    # Group all codes by chapter prefix (DA, DB, DC, ...)
    chapter_blocks = defaultdict(list)
    for r in rows:
        val = r["value"]
        if not val.isdigit() and len(val) >= 2:
            chapter = val[:2]
            if chapter.startswith("D") and chapter[1:2].isalpha():
                chapter_blocks[chapter].append(r)

    # Build per-chapter trees
    def build_subtree(code):
        row = code_to_row[code]
        children_codes = code_to_children.get(code, [])
        node = {
            "token_id": int(row["token_id"]),
            "code": code,
            "value": row["value"],
            "description_en": row["description_en"],
            "level": row.get("hierarchy_level", ""),
        }
        if children_codes:
            children = {}
            child_ids = []
            for cc in sorted(children_codes):
                cn = build_subtree(cc)
                children[code_to_row[cc]["value"]] = cn
                child_ids.extend(cn.get("all_token_ids", [cn["token_id"]]))
            node["children"] = children
            node["all_token_ids"] = [int(row["token_id"])] + child_ids
        else:
            node["all_token_ids"] = [int(row["token_id"])]
        return node

    chapters = {}
    all_icd10_ids = []
    placed_codes = set()

    for ch in sorted(ICD10_CHAPTERS.keys()):
        if ch not in chapter_blocks:
            continue

        # Find block-level codes for this chapter (roots of the chapter tree)
        ch_rows = chapter_blocks[ch]
        # Block-level = codes whose parent is the synthetic chapter node
        block_codes = []
        for r in ch_rows:
            parent = r.get("parent_code", "").strip()
            parent_val = parent.replace(f"HEA_ICD10_", "") if parent else ""
            if parent_val == ch or not parent or parent not in code_to_row:
                # This is a block or orphan at chapter level
                if r.get("hierarchy_level") == "block" or not parent:
                    block_codes.append(r["code"])

        # Build chapter tree
        ch_children = {}
        ch_ids = []

        for code in sorted(block_codes):
            node = build_subtree(code)
            ch_children[code_to_row[code]["value"]] = node
            ch_ids.extend(node["all_token_ids"])
            placed_codes.add(code)
            # Mark all descendants as placed
            def mark_placed(c):
                placed_codes.add(c)
                for cc in code_to_children.get(c, []):
                    mark_placed(cc)
            mark_placed(code)

        # Also add any remaining codes in this chapter not yet placed
        for r in ch_rows:
            if r["code"] not in placed_codes:
                node = build_subtree(r["code"])
                ch_children[r["value"]] = node
                ch_ids.extend(node["all_token_ids"])
                placed_codes.add(r["code"])
                def mark_placed2(c):
                    placed_codes.add(c)
                    for cc in code_to_children.get(c, []):
                        mark_placed2(cc)
                mark_placed2(r["code"])

        chapters[ch] = {
            "description_en": ICD10_CHAPTERS.get(ch, f"Chapter {ch}"),
            "children": ch_children,
            "all_token_ids": ch_ids,
        }
        all_icd10_ids.extend(ch_ids)

    # Handle non-chapter codes (Y-codes, BL, EU, TU, ZZ, etc.)
    other_groups = defaultdict(list)
    for r in rows:
        if r["code"] not in placed_codes:
            val = r["value"]
            if val.isdigit():
                other_groups["ICD8"].append(r)
            else:
                prefix = val[:2] if len(val) >= 2 else "other"
                other_groups[prefix].append(r)

    for grp in sorted(other_groups.keys()):
        grp_rows = other_groups[grp]
        grp_children = {}
        grp_ids = []
        for r in grp_rows:
            if r["code"] not in placed_codes:
                node = build_subtree(r["code"]) if r["code"] in code_to_row else {
                    "token_id": int(r["token_id"]),
                    "code": r["code"],
                    "value": r["value"],
                    "description_en": r["description_en"],
                    "all_token_ids": [int(r["token_id"])],
                }
                grp_children[r["value"]] = node
                grp_ids.extend(node.get("all_token_ids", [node["token_id"]]))
                placed_codes.add(r["code"])

        if grp == "ICD8":
            desc = "ICD-8 legacy codes"
        else:
            desc = f"Supplementary codes ({grp})"

        chapters[grp] = {
            "description_en": desc,
            "children": grp_children,
            "all_token_ids": grp_ids,
        }
        all_icd10_ids.extend(grp_ids)

    return {
        "_meta": {
            "name": "HEA_ICD10",
            "count": len(rows),
            "hierarchical": True,
            "chapters": len(chapters),
        },
        "all_token_ids": all_icd10_ids,
        "children": chapters,
    }


def validate(hierarchy, rows):
    """Verify all token_ids appear exactly once."""
    all_ids = set()
    expected_ids = {int(r["token_id"]) for r in rows}

    def collect_ids(node, path=""):
        if isinstance(node, dict):
            if "token_id" in node and "children" not in node:
                all_ids.add(node["token_id"])
            if "tokens" in node:
                for t in node["tokens"]:
                    all_ids.add(t["token_id"])
            if "children" in node:
                for key, child in node["children"].items():
                    collect_ids(child, f"{path}/{key}")
            # Recurse into domain/category nodes
            for key, val in node.items():
                if key.startswith("_") or key in ("token_id", "tokens", "children",
                    "all_token_ids", "code", "value", "description_en", "level",
                    "synthetic", "count", "hierarchical", "roots", "orphan_groups",
                    "name", "chapters"):
                    continue
                if isinstance(val, dict):
                    collect_ids(val, f"{path}/{key}")

    collect_ids(hierarchy)

    missing = expected_ids - all_ids
    extra = all_ids - expected_ids
    print(f"Validation: {len(all_ids)} token_ids in hierarchy, {len(expected_ids)} expected")
    if missing:
        print(f"  MISSING: {len(missing)} token_ids not in hierarchy")
    if extra:
        print(f"  EXTRA: {len(extra)} token_ids not expected")
    if not missing and not extra:
        print(f"  OK: All {len(all_ids)} token_ids accounted for")
    return len(missing) == 0 and len(extra) == 0


def main():
    rows = load_master()
    print(f"Building hierarchy from {len(rows)} codes...")

    hierarchy = build_hierarchy()

    # Print summary
    for domain, node in hierarchy.items():
        n_cats = len([k for k in node if not k.startswith("_")])
        print(f"  {domain}: {node['_meta']['count']} tokens in {n_cats} categories")

    # Validate
    print()
    validate(hierarchy, rows)

    # Write JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, ensure_ascii=False, indent=2)

    import os
    size_mb = os.path.getsize(OUTPUT_PATH) / 1e6
    print(f"\nWrote {OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
