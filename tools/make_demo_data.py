"""
Generate a fully synthetic demo journal (demo/demo.Journal.tsv).

The values are random numbers with plausible ranges - they are NOT derived
from any real measurement. The file has the same column layout as an NIR
journal export, so the app can be tried without real data.

    python tools/make_demo_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

SEED = 20261007
N_RECORDS = 160
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo", "demo.Journal.tsv")

HEADER = ["ROW", "Check", "UID", "Points", "Date", "SNR", "ID", "Use", "Barcode", "Note",
          "Original", "Result", "Reference", "Product", "Moisture", "Protein", "P", "FFA",
          "Mahalanobis", "MahalanobiS_Moisture", "Mahalanobis_FFA", "Begin", "End", "Recipe",
          "Composition", "Images"]
SERIAL = "DEMO-0001"
RECIPE = "demo_oil"


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def num(v, digits):
    return f"{v:.{digits}f}".rstrip("0").rstrip(".") if digits else f"{v:.0f}"


def main():
    rnd = random.Random(SEED)
    rows = []
    t = datetime(2026, 8, 3, 6, 40, 0)
    for i in range(N_RECORDS):
        t += timedelta(hours=rnd.choice([6, 6, 6, 5.5, 6.5, 12]), minutes=rnd.randint(-25, 25))
        # reference (lab) values
        u = rnd.random()
        if u < 0.55:
            p = clip(rnd.gauss(5.4, 0.6), 3.2, 7)
        elif u < 0.9:
            p = rnd.uniform(6, 13)
        else:
            p = rnd.uniform(13, 25)
        p = round(p, 1)
        moist = round(clip(rnd.gauss(4100, 520), 3200, 7000) / 100) * 100
        ffa = round(clip(rnd.gauss(0.54, 0.07), 0.38, 0.8), 2)

        # NIR predictions
        res_p = p + rnd.gauss(0, 1.1)
        if rnd.random() < 0.03:                      # a few suspicious records
            res_p = max(0.5, p + rnd.choice([-1, 1]) * rnd.uniform(5, 9))
        res_m = moist + rnd.gauss(0, 280)
        res_f = ffa + rnd.gauss(0, 0.035)

        newest = i >= N_RECORDS - 6
        has_ref = not newest and rnd.random() > 0.02
        check = (not newest and rnd.random() > 0.05) or (newest and rnd.random() < 0.4)
        use = "CAL" if has_ref and check else ""

        mahal = ""
        if i >= N_RECORDS * 0.7:                     # newer records carry Mahalanobis
            m = [round(clip(rnd.lognormvariate(-0.3, 0.55), 0.1, 3.5), 1) for _ in range(3)]
            mahal = " ; ".join(num(x, 1) for x in m + m)

        result = " ; ".join([num(res_p, 4), num(res_m, 1), num(res_f, 5)])
        original = result if newest else "NaN ; NaN ; NaN"
        if has_ref:
            reference = f"; {moist} ;  ; {num(p, 1)} ; {num(ffa, 2)} ;  ;  ;"
            vals = [str(moist), "", num(p, 1), num(ffa, 2)]
        else:
            reference = ";  ;  ;  ;  ;  ;  ;"
            vals = ["", "", "", ""]
        date = t.strftime("%Y-%m-%d %H:%M:%S")
        begin = (t - timedelta(seconds=15)).strftime("%H:%M:%S")
        end = (t + timedelta(seconds=15)).strftime("%H:%M:%S")
        rows.append([f"{i:04d}", "True" if check else "False", f"#{date} {SERIAL}",
                     str(rnd.randint(8, 13)), date, SERIAL, date, use, "", "",
                     original, result, reference, ""] + vals +
                    [mahal, "", "", begin, end, RECIPE, "", ""])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"Written {os.path.normpath(OUT)} ({len(rows)} records)")


if __name__ == "__main__":
    main()
