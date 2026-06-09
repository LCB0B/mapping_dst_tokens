#!/usr/bin/env python3
"""Upgrade SOC_afgtypko + SOC_bstrfkod: install authoritative Danish + clean English.

Both were already code-sourced (from raw/SOC_afgtypko.txt / raw/SOC_bstrfkod), but their
description_da was filled with poor MACHINE-TRANSLATED ENGLISH (e.g. "Booklet" for Hæfte,
"Out-of-court goods of fines" for "Udenretlig vedt. af bøde og førerretsfrakendelse").
There was no real Danish.

The authoritative Danish value sets are now available from the downloaded KRIN codebook:
  SOC_afgtypko  = AFG_AFGTYPKO / KON_AFGTYPKO / IND_AFGTYPKO  ("Afgørelsens/sanktionens type")
  SOC_bstrfkod  = IND_BSTRFKOD ("Arten af betinget frihedsstraf")
(per input_dataset_description.csv rows 104 & 120). Danish is taken VERBATIM from the
codebook; English is a faithful translation of that Danish (description_en_source=translated).
Codes not present in the value set (e.g. afgtypko 85) are left untouched (stay [Unresolved]).

Source: raw/dst_downloads/KRIN_codebook.md +
  https://www.dst.dk/da/Statistik/dokumentation/Times/kriminalstatistik/ind-afgtypko / ind-bstrfkod

Re-runnable. Usage: python3 scripts/fix_soc_afgtypko_bstrfkod.py [--dry-run]
"""
import argparse, csv, json

MASTER = "MASTER_CATEGORY_MAPPINGS.csv"
CODEBOOK_JSON = "/tmp/claude-270889/-home-louibo-mappings/023a0e03-d690-4ba1-a3d5-ca2184b0b2d3/tasks/wetm5a9gs.output"

# Clean English (faithful translation of the authoritative Danish). Codes omitted here
# fall back to the verbatim Danish (e.g. terse pure-§-reference codes) — never invented.
AFGTYPKO_EN = {
    "0": "Unknown", "1": "Unconditional sentence only", "2": "Fine sentence",
    "3": "Penal Code §68-70 measure / preventive detention", "4": "Suspended sentence only",
    "5": "Suspended sentence and fine", "6": "Partially suspended sentence",
    "7": "Judgment in absentia (default judgment)", "8": "In-court acceptance of fine",
    "9": "Warning in court", "10": "Otherwise concluded in court", "11": "Acquitted",
    "12": "In-court acceptance of fine and driving-licence disqualification",
    "13": "In-court acceptance of fine and driving ban",
    "14": "In-court acceptance of fine and disqualification of a right",
    "15": "Military punishment",
    "16": "In-court acceptance of fine / disqualification of right to ride a small moped",
    "17": "Out-of-court acceptance of fine / disqualification of right to ride a small moped",
    "18": "Out-of-court acceptance of fine and disqualification of a right",
    "19": "Out-of-court acceptance of fine and driving-licence disqualification",
    "20": "Out-of-court acceptance of fine and driving ban", "21": "Fine notice (out-of-court fine)",
    "22": "Charge withdrawn with conditions (Rpl §723(1)(1))",
    "23": "Charge withdrawn with conditions (Rpl §723(1)(2))",
    "24": "Charge withdrawn with conditions (Rpl §723(1)(5))",
    "25": "Charge withdrawn without conditions (Rpl §723(1)(3))",
    "26": "Charge withdrawn without conditions (Rpl §723(1)(4))",
    "27": "Charge withdrawn without conditions (Rpl §723(1)(5))",
    "28": "Charge withdrawn without conditions (Rpl §723(2))",
    "29": "Charge waived (Rpl §723(1))", "30": "Unknown",
    "31": "Charge waived (Faroese; not counted)",
    "33": "Charge withdrawn with conditions (Rpl §723(2))",
    "34": "Charge groundless, Penal Code (Rpl §721(1)(1))",
    "35": "Charge groundless (Faroese; not counted)",
    "36": "Charge waived with warning, Penal Code", "37": "Charge waived without warning, Penal Code",
    "38": "Charge waived with warning, special legislation",
    "39": "Charge waived without warning, special legislation", "40": "Other", "41": "Youth contract",
    "42": "Charge withdrawn with fine (Rpl §723(4) cf. (1)(1))",
    "43": "Charge withdrawn with fine (Rpl §723(4) cf. (1)(2))",
    "44": "Charge withdrawn with fine (Rpl §723(4) cf. (1)(5))",
    "52": "Youth contract (Rpl §722(1)(2); DST-derived, 1999-2006)",
    "53": "Youth contract (Rpl §722(1)(3); DST-derived, 1999-2006)",
    "60": "Travel ban imposed (Penal Code §79e)",
    "62": "Charge withdrawn with conditions (Rpl §722(1)(2))",
    "63": "Charge withdrawn with conditions (Rpl §722(1)(3))",
    "64": "Charge withdrawn with conditions (Rpl §722(1)(7))",
    "65": "Charge withdrawn without conditions (Rpl §722(1)(6))",
    "66": "Charge withdrawn without conditions (Rpl §722(1)(4))",
    "67": "Charge withdrawn without conditions (Rpl §722(1)(7))",
    "68": "Charge withdrawn without conditions (Rpl §722(2) cf. (3))",
    "69": "Prosecution abandoned (Rpl §721(1)(2))", "70": "Judgment without court hearing",
    "71": "Charge withdrawn without conditions (Rpl §722(1)(5))",
    "72": "Prosecution abandoned (Rpl §721(1)(3))",
    "73": "Charge withdrawn with conditions (Rpl §722(2) cf. (3))",
    "74": "Charge groundless, Penal Code (§721(1)(1))",
    "75": "Charge groundless, special legislation (§721(1)(1))",
    "76": "Charge waived with warning, Penal Code (Rpl §722(1)(1))",
    "77": "Charge waived without warning, Penal Code (Rpl §722(1)(1))",
    "78": "Charge waived with warning, special legislation (Rpl §722(1)(1 or 7))",
    "79": "Charge waived, special legislation (Rpl §722(1)(1))",
    "80": "Residence ban imposed (Penal Code §79a)", "81": "Suspended sentence and community service",
    "82": "Suspended sentence, fine and community service (DST-derived, 1983-2006)",
    "83": "Partially suspended sentence and community service (DST-derived, 1983-2006)",
    "84": "Unconditional sentence and community service", "86": "Unconditional sentence and fine",
    "87": "Punishment waived/lapsed", "88": "Served by pre-trial detention",
    "89": "Residence and contact ban imposed (Penal Code §79a)",
    "90": "Contact ban imposed (Penal Code §79a)", "100": "Shelved without restraining order",
    "101": "Shelved without warning (§265)", "104": "Order under the Dog Act",
    "110": "Driving licence disqualified due to illness / administrative withdrawal",
    "118": "Shelved as time-barred (Penal Code §93)", "121": "Transferred abroad",
    "200": "In-court acceptance of fine / disqualification of right to drive heavy vehicles",
    "201": "Out-of-court acceptance of fine / disqualification of right to drive heavy vehicles",
    "202": "In-court acceptance of fine / driving-licence disqualification and right to drive heavy vehicles",
}
BSTRFKOD_EN = {
    "A": "Fine server (bødeafsoner)", "0": "Unknown",
    "1": "Hæfte (lenient short custodial sentence; abolished 1 Jul 2001)",
    "2": "Imprisonment", "3": "Preventive detention (forvaring)", "4": "Sentencing postponed",
    "5": "Pardoned", "6": "Life imprisonment", "7": "Pardoned from a hæfte sentence",
    "8": "Unknown", "9": "Sentencing postponed (old cases)",
}


def load_codebook():
    data = json.load(open(CODEBOOK_JSON, encoding="utf-8"))
    out = {}
    for v in data["result"]["codebook"]:
        if v["variable"] in ("IND_AFGTYPKO", "IND_BSTRFKOD"):
            out[v["variable"]] = {kv["code"]: kv["text"] for kv in (v.get("values") or [])}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cb = load_codebook()
    afg_da, bst_da = cb["IND_AFGTYPKO"], cb["IND_BSTRFKOD"]

    with open(MASTER, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); fns = list(rd.fieldnames); rows = list(rd)

    na = nb = 0
    for r in rows:
        cat = r.get("category"); v = (r.get("value") or "").strip()
        if cat == "SOC_afgtypko" and v in afg_da:
            da = afg_da[v]; en = AFGTYPKO_EN.get(v, da)
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_afgtypko"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; na += 1
        elif cat == "SOC_bstrfkod" and v in bst_da:
            da = bst_da[v]; en = BSTRFKOD_EN.get(v, da)
            r["description"] = da; r["description_da"] = da; r["description_en"] = en
            r["source"] = "dst_ind_bstrfkod"; r["description_en_source"] = "translated"
            r["confidence_level"] = "high"; nb += 1

    print(f"SOC_afgtypko upgraded: {na} (code 85 left unresolved); SOC_bstrfkod upgraded: {nb}")
    if args.dry_run:
        print("[dry-run] no write"); return
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns); w.writeheader(); w.writerows(rows)
    print(f"wrote {MASTER}")


if __name__ == "__main__":
    main()
