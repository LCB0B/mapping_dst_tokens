#!/usr/bin/env python3
"""Build the HEA_speciale re-translation worklist: the unique abbreviated
`description_da` strings among the machine-translated rows, each annotated with
context that helps an LLM expand+translate correctly (specialty name, coarser
SSR levels, and fuller GP text where available).

Output: scripts/worklists/hea_speciale_worklist.csv with columns:
  description_da, n_rows, sample_value, specialty_code, specialty_name_en,
  spec4_txt, spec3_txt, plo_fuller, current_bad_en
"""
import csv, os
from collections import defaultdict

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
SPEC = "raw/dst_downloads/speciale_dst_codes.csv"          # code, spec6_txt, spec4_txt, spec3_txt
PLO = "raw/dst_downloads/plo_gp_ydelser_merged.csv"        # ydelsesnr, description_da
OUT = "scripts/worklists/hea_speciale_worklist.csv"


def load_spec():
    d = {}
    if not os.path.exists(SPEC):
        return d
    for r in csv.DictReader(open(SPEC, encoding="utf-8", errors="replace")):
        code = (r.get("code") or "").strip()
        d[code] = (r.get("spec4_txt", "").strip(), r.get("spec3_txt", "").strip())
    return d


def load_plo():
    d = {}
    if not os.path.exists(PLO):
        return d
    for r in csv.DictReader(open(PLO, encoding="utf-8", errors="replace")):
        d[(r.get("ydelsesnr") or "").strip()] = (r.get("description_da") or "").strip()
    return d


def main():
    spec = load_spec()
    plo = load_plo()
    rows = [r for r in csv.DictReader(open(MASTER, encoding="utf-8"))
            if r["category"] == "HEA_speciale"
            and (r.get("description_en_source") or "").strip().lower() == "translated"]

    # group by the unique abbreviated Danish text
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("description_da") or "").strip()].append(r)

    out = []
    for da, grp in groups.items():
        r0 = grp[0]
        v = (r0.get("value") or "").strip()
        spec_code = v[:2] if len(v) == 6 else (v[:1] if len(v) == 5 else "")
        proc4 = v[2:] if len(v) == 6 else (v[1:] if len(v) == 5 else "")
        spec4, spec3 = "", ""
        for r in grp:                       # any row's code may resolve in the SPEC table
            vv = (r.get("value") or "").strip()
            if vv in spec:
                spec4, spec3 = spec[vv]; break
        # fuller GP text (specialty 80) by 4-digit procedure
        plo_full = ""
        if spec_code == "80":
            plo_full = plo.get(proc4) or plo.get(proc4.lstrip("0")) or ""
        out.append({
            "description_da": da,
            "n_rows": len(grp),
            "sample_value": v,
            "specialty_code": spec_code,
            "specialty_name_en": (r0.get("description_en_official") or "").strip(),
            "spec4_txt": spec4,
            "spec3_txt": spec3,
            "plo_fuller": plo_full,
            "current_bad_en": (r0.get("description_en") or "").strip(),
        })

    out.sort(key=lambda d: (d["specialty_code"], d["description_da"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    n_rows = sum(d["n_rows"] for d in out)
    print(f"Wrote {OUT}: {len(out)} unique strings covering {n_rows} rows")
    print(f"  with spec4/spec3 context: {sum(1 for d in out if d['spec4_txt'] or d['spec3_txt'])}")
    print(f"  with plo fuller GP text : {sum(1 for d in out if d['plo_fuller'])}")
    print(f"  distinct specialties    : {len(set(d['specialty_code'] for d in out))}")


if __name__ == "__main__":
    main()
