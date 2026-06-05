#!/usr/bin/env python3
"""Apply the empirical SOCIO_GL -> SOCIO13 crosswalk (built on the VM from person sequences).

SOCIO_GL (LAB_socio gl_*) = AKM "Socioøkonomisk klassifikation 1976-1990" (the ARBSTIL-era
variable); its raw 2-digit value set is not public (see SOCIO_GL_README.md). Instead the labels
are recovered empirically: for people observed across the ~1987 scheme boundary, each old gl_X
code is mapped to the modern SOCIO13 code they co-occur with. Input:
  transition/socio_gl_crosswalk_empirical.csv  (per gl_X: modal/recommended socio13, share, n, confidence)

We label gl_X by its MODAL socio13 successor (most-common; equals the lift recommendation for all
high/medium codes, and is the faithful choice where they disagree at low share). The SOCIO13 label
is the authoritative LAB_socio13 text. Confidence is carried from the crosswalk file. Codes with no
transition data (gl_81, gl_82) stay [Unresolved]. The empirical basis (socio13 code, share, n) is
recorded in description_da_alt for transparency.

Re-runnable. Usage: python3 scripts/apply_socio_gl_crosswalk.py [--dry-run]
"""
import argparse, csv

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
CW = "transition/socio_gl_crosswalk_empirical.csv"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    s13 = {}
    for r in csv.DictReader(open(MASTER, encoding="utf-8")):
        if r["category"] == "LAB_socio13":
            s13[(r.get("value") or "").strip()] = ((r.get("description_da") or "").strip(),
                                                    (r.get("description_en") or "").strip())
    cw = {}
    for r in csv.DictReader(open(CW, encoding="utf-8")):
        cw["gl_" + r["gl_code"]] = (r["modal_socio13"].strip(), r["modal_share"].strip(),
                                    r["n_support_people"].strip(), r["confidence"].strip())

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)
    ok = unr = 0
    for r in rows:
        if r.get("category") != "LAB_socio":
            continue
        v = (r.get("value") or "").strip()
        c = cw.get(v)
        modal = c[0] if c else ""
        if c and modal and modal in s13 and not c[3].startswith("low (no data)"):
            da, en = s13[modal]
            conf = c[3] if c[3] in ("high", "medium", "low") else "low"
            share = float(c[1]) if c[1] else 0.0
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["description_da_alt"] = (f"SOCIO_GL (1976-1990) {v}; empirical crosswalk -> "
                                       f"SOCIO13 {modal} ({share*100:.0f}% of transitions, n={c[2]})")
            r["source"] = "empirical_crosswalk_socio13"
            r["description_en_source"] = "empirical_crosswalk_socio13"
            r["confidence_level"] = conf; ok += 1
        else:
            gl = v.replace("gl_", "")
            mark = f"[Unresolved SOCIO_GL (1976-1990) code: {gl}]"
            r["description"] = mark; r["description_da"] = ""; r["description_en"] = mark
            r["description_da_alt"] = ""; r["source"] = "none|generated"
            r["description_en_source"] = ""; r["confidence_level"] = "low"; unr += 1
    print(f"SOCIO_GL: applied={ok}, [Unresolved] (no data)={unr}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
