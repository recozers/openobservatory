"""Monthly / quarterly ABSOLUTE NOx emission rate of a point source from the daily along-wind profiles
written by tools/no2_flux.py (--out), using the near-source plateau (mean flux at 1-9 km downwind minus
the far-upwind mean) and a plateau-specific calibration factor derived from the calibration plants.

    python tools/no2_flux_quarterly.py calibrate                       # writes results_no2/calibration_plateau.json
    python tools/no2_flux_quarterly.py results_no2/flux_<name>.csv --site <site_id>   # writes results_no2/flux_<site_id>_monthly.csv

The monthly file feeds build_timeline_data.py (columns: nox_kgh_cal, nox_se, n_days).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from no2_flux import NOX_NO2, MW_NO2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W = 12000.0
CAL_PLANTS = {"martin_lake": 6146, "limestone": 298, "oak_grove": 6180, "welsh": 6139, "independence_ar": 6641}


def plateau_series(csv_path):
    piv = pd.read_csv(csv_path, index_col=0)
    xcols = [c for c in piv.columns if c.replace("-", "").replace(".", "").isdigit()]
    up = [c for c in xcols if float(c) <= -4000]
    F = (piv[xcols].sub(piv[up].mean(axis=1), axis=0) * (2 * W)).mul(piv.speed, axis=0)
    near = [c for c in xcols if 1000 <= float(c) <= 9000]
    far = [c for c in xcols if float(c) <= -5000]
    s = F[near].mean(axis=1) - F[far].mean(axis=1)
    s.index = pd.to_datetime(s.index)
    return s  # mol/s NO2, uncalibrated


def calibrate():
    rows = []
    for key, oris in CAL_PLANTS.items():
        s = plateau_series(ROOT / "results_no2" / f"flux_{key}_2023.csv")
        df = pd.read_csv(ROOT / "data" / "campd" / f"{oris}_2023.csv")
        df["noxMass"] = pd.to_numeric(df.noxMass, errors="coerce")
        tot = df.groupby(["date", "hour"]).noxMass.sum().reset_index()
        ov = tot[tot.hour.isin([19, 20])].groupby("date").noxMass.mean()
        ov.index = pd.to_datetime(ov.index)
        j = pd.concat([s.rename("sat"), (ov * 0.4536).rename("truth")], axis=1).dropna()
        sat_kgh = j.sat.mean() * NOX_NO2 * MW_NO2 * 3600
        rows.append(dict(plant=key, stack_class="tall_coal_reference", days=len(j), truth_kgh=j.truth.mean(), sat_kgh=sat_kgh, factor=j.truth.mean() / sat_kgh, sat_se=j.sat.std() / np.sqrt(len(j)) * NOX_NO2 * MW_NO2 * 3600))
    t = pd.DataFrame(rows)
    t.to_csv(ROOT / "results_no2/calibration_reference_plants.csv", index=False)
    t["factor_se"] = t.factor * t.sat_se / t.sat_kgh
    w = 1 / t.factor_se ** 2
    out = dict(factor=float(np.average(t.factor, weights=w)), factor_se=float(np.sqrt(1 / w.sum())), scatter=float(t.factor.std()), n=len(t), method="near-source plateau 1-9 km")
    print(t.round(2).to_string(index=False))
    print(f"plateau calibration factor {out['factor']:.2f} ± {out['factor_se']:.2f}, scatter ± {out['scatter']:.2f}")
    (ROOT / "results_no2" / "calibration_plateau.json").write_text(json.dumps(out, indent=1))
    return out


def monthly(csv_path, site_id, baseline_before=None):
    """baseline_before: for a source that switched on, subtract the pre-start level month-by-month (season-matched)."""
    cal = json.loads((ROOT / "results_no2" / "calibration_plateau.json").read_text())
    s = plateau_series(csv_path)
    if baseline_before:
        base = s[s.index < pd.Timestamp(baseline_before)]
        bm = base.groupby(base.index.month).mean()
        s = s - s.index.month.map(bm).to_numpy()
    m = s.resample("ME").agg(["mean", "count", "std"])
    m = m[m["count"] >= 3]
    kgh = m["mean"] * NOX_NO2 * MW_NO2 * 3600 * cal["factor"]
    se = np.hypot(m["std"] / np.sqrt(m["count"]) * NOX_NO2 * MW_NO2 * 3600 * cal["factor"], kgh.abs() * cal["scatter"] / cal["factor"])
    out = pd.DataFrame({"nox_kgh_cal": kgh, "nox_se": se, "n_days": m["count"]})
    out.index = out.index.strftime("%Y-%m")
    p = ROOT / "results_no2" / f"flux_{site_id}_monthly.csv"
    out.round(1).to_csv(p)
    q = out.groupby(pd.PeriodIndex(out.index, freq="M").asfreq("Q").astype(str)).agg(nox_kgh=("nox_kgh_cal", "mean"), days=("n_days", "sum")).round(0)
    print(q.T.to_string())
    print(f"wrote {p}")


if __name__ == "__main__":
    if sys.argv[1] == "calibrate":
        calibrate()
    else:
        bb = sys.argv[sys.argv.index("--baseline-before") + 1] if "--baseline-before" in sys.argv else None
        monthly(Path(sys.argv[1]), sys.argv[sys.argv.index("--site") + 1], bb)
