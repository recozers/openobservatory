"""Known-source subtraction for a campus next to power plants that report to EPA CAMPD (phase 2, C2: Colossus 1).

    python tools/known_source_subtract.py --flux results_no2/flux_colossus.csv --plants 3393 55269 \
        --on 2024-07-01 --off 2025-07-01 --out results_no2/colossus1_subtraction.json

The daily near-source plateau (tools/no2_flux_quarterly.plateau_series, mol/s uncalibrated) is regressed on each plant's
NOx mass at the overpass hours (CAMPD hours are local standard time; TROPOMI passes ~13:30 local clock time, so hours
12-14 are averaged), a seasonal pair (sin/cos of day of year), a linear trend, and a step for the campus's own combustion
period [--on, --off). The step coefficient, times the plateau calibration factor, is the campus's NOx emission rate with
the plants' day-to-day variability removed. A monthly variant replaces the step by month dummies to show the profile.
Standard errors are HAC (Newey-West, 10-day lag).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.no2_flux_quarterly import MW_NO2, NOX_NO2, plateau_series  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OVERPASS_HOURS = (12, 13, 14)


def plant_overpass_nox(oris, years):
    parts = []
    for y in years:
        f = ROOT / "data" / "campd" / f"{oris}_{y}.csv"
        if f.exists() and f.stat().st_size > 0:
            d = pd.read_csv(f, usecols=["date", "hour", "noxMass"])
            d["noxMass"] = pd.to_numeric(d.noxMass, errors="coerce")
            parts.append(d)
    if not parts:
        return pd.Series(dtype=float)
    d = pd.concat(parts)
    tot = d.groupby(["date", "hour"]).noxMass.sum().reset_index()
    ov = tot[tot.hour.isin(OVERPASS_HOURS)].groupby("date").noxMass.mean() * 0.4536  # lb/h -> kg/h
    ov.index = pd.to_datetime(ov.index)
    return ov.rename(f"plant_{oris}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flux", required=True)
    ap.add_argument("--plants", nargs="+", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--off", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cal = json.loads((ROOT / "results_no2" / "calibration_plateau.json").read_text())
    s = plateau_series(args.flux).rename("plateau")
    years = sorted(set(s.index.year))
    X = pd.concat([s] + [plant_overpass_nox(p, years) for p in args.plants], axis=1).dropna()
    X["on"] = ((X.index >= pd.Timestamp(args.on)) & (X.index < pd.Timestamp(args.off))).astype(float)
    doy = X.index.dayofyear / 365.25 * 2 * np.pi
    X["sin"], X["cos"] = np.sin(doy), np.cos(doy)
    X["trend"] = (X.index - X.index[0]).days / 365.25
    plant_cols = [c for c in X.columns if c.startswith("plant_")]
    kgh = NOX_NO2 * MW_NO2 * 3600 * cal["factor"]  # mol/s NO2 plateau -> kg NOx/h calibrated
    exog = sm.add_constant(X[plant_cols + ["on", "sin", "cos", "trend"]])
    fit = sm.OLS(X.plateau, exog).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
    out = dict(n_days=int(len(X)), on=args.on, off=args.off, calibration_factor=cal["factor"],
               campus_step_kgh=float(fit.params["on"] * kgh), campus_step_se_kgh=float(fit.bse["on"] * kgh),
               plant_coefficients={c: dict(coef=float(fit.params[c]), se=float(fit.bse[c])) for c in plant_cols},
               plant_mean_kgh_on={c: float(X.loc[X.on == 1, c].mean()) for c in plant_cols},
               plant_mean_kgh_off={c: float(X.loc[X.on == 0, c].mean()) for c in plant_cols},
               r2=float(fit.rsquared))
    # monthly profile during the on period (month dummies replace the step)
    months = X.index.to_period("M")
    dummies = pd.get_dummies(months.astype(str)).astype(float)
    dummies.index = X.index
    on_months = sorted(set(months[X.on == 1].astype(str)))
    exog2 = sm.add_constant(pd.concat([X[plant_cols + ["sin", "cos", "trend"]], dummies[on_months]], axis=1))
    fit2 = sm.OLS(X.plateau, exog2).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
    out["monthly_kgh"] = {m: dict(kgh=float(fit2.params[m] * kgh), se=float(fit2.bse[m] * kgh), n=int((months.astype(str) == m).sum())) for m in on_months}
    # naive estimate without subtraction, for comparison
    naive = (X.loc[X.on == 1, "plateau"].mean() - X.loc[X.on == 0, "plateau"].mean()) * kgh
    out["naive_step_kgh_no_subtraction"] = float(naive)
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(f"days {out['n_days']}; campus step {out['campus_step_kgh']:.0f} ± {out['campus_step_se_kgh']:.0f} kg NOx/h (naive {naive:.0f}); r2 {out['r2']:.2f}")
    for c in plant_cols:
        print(f"  {c}: coef {fit.params[c]:.4f} ± {fit.bse[c]:.4f} (mean {out['plant_mean_kgh_on'][c]:.0f} kg/h on, {out['plant_mean_kgh_off'][c]:.0f} off)")
    print("  monthly during the on period:")
    for m, v in out["monthly_kgh"].items():
        print(f"    {m}: {v['kgh']:6.0f} ± {v['se']:4.0f} kg/h (n={v['n']})")


if __name__ == "__main__":
    main()
