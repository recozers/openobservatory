"""NOx emission rate of a point source from TROPOMI NO2: wind-rotated along-wind line densities,
composited over many days, fitted with an exponentially modified Gaussian (the standard power-plant
method, e.g. Beirle et al. 2019).

    EE_PROJECT=<project> python tools/no2_flux.py --name martin_lake --lat 32.2597 --lon -94.5705 --start 2023-01-01 --end 2023-12-31

Per day: wind at the ~13:30 local overpass from ERA5 100 m (u, v at 19-21 UTC), then the mean tropospheric
NO2 column in along-wind bins (2 km steps from -12 to +30 km, crosswind half-width W) built as rotated
rectangles.  Line density L(x) = (bin mean - upwind background) x 2W  [mol/m].  Flux F(x) = L(x) x u  [mol/s].
Composite F(x) over days with cloud fraction below --max-cloud and 2-12 m/s wind; fit
F(x) = E * exp(-x/x0) (x) Gaussian(sigma) with a fitted offset.  E is the NO2 emission rate; NOx = 1.32 E.
Reports E in mol/s, kg NOx/h and t NOx/yr, with a bootstrap error over days.

Caveats: 5 km native pixels, so only sources dominating a ~30 km box; lifetime and NOx/NO2 ratio are
assumed (x0 absorbs the lifetime); calibrate against plants with public emissions (eGRID annual, CAMPD hourly).
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np
import pandas as pd

KEY = "tropospheric_NO2_column_number_density"
MW_NO2 = 46.0055e-3  # kg/mol
NOX_NO2 = 1.32


def rect(ee, lat, lon, phi_deg, x0, x1, half_w):
    """Rotated rectangle: along-wind from x0 to x1 (m, positive downwind), crosswind +/- half_w (m)."""
    k = 111320
    kx = k * math.cos(math.radians(lat))
    a = math.radians(phi_deg)
    ux, uy = math.sin(a), math.cos(a)          # unit vector along the wind (east, north)
    vx, vy = -uy, ux                           # crosswind unit vector
    pts = []
    for X, Y in ((x0, -half_w), (x1, -half_w), (x1, half_w), (x0, half_w)):
        ex, ny = X * ux + Y * vx, X * uy + Y * vy
        pts.append([lon + ex / kx, lat + ny / k])
    return ee.Geometry.Polygon([pts])


def daily_profiles(ee, name, lat, lon, days, xs, half_w, max_cloud, min_wind=2.0, max_wind=12.0):
    era = ee.ImageCollection("ECMWF/ERA5/HOURLY").select(["u_component_of_wind_100m", "v_component_of_wind_100m"])
    no2c = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2").select([KEY, "cloud_fraction"])
    pt = ee.Geometry.Point([lon, lat])
    wind = {}
    for i in range(0, len(days), 400):
        fc = ee.FeatureCollection([ee.Feature(pt, {"d": d.strftime("%Y-%m-%d")}) for d in days[i:i + 400]])

        def w(f):
            d = ee.Date(f.get("d"))
            v = era.filterDate(d.advance(19, "hour"), d.advance(21, "hour")).mean().reduceRegion(ee.Reducer.first(), f.geometry(), 27830)
            return f.set({"u": v.get("u_component_of_wind_100m", -999), "v": v.get("v_component_of_wind_100m", -999)})
        for f in fc.map(w).getInfo()["features"]:
            p = f["properties"]
            wind[p["d"]] = (p.get("u"), p.get("v"))
    wdf = pd.DataFrame([(d, u, v) for d, (u, v) in wind.items()], columns=["d", "u", "v"])
    wdf = wdf[(wdf.u > -900) & (wdf.v > -900)].copy()
    wdf["speed"] = np.hypot(wdf.u, wdf.v)
    wdf["phi"] = (np.degrees(np.arctan2(wdf.u, wdf.v)) + 360) % 360
    wdf = wdf[(wdf.speed >= min_wind) & (wdf.speed <= max_wind)].reset_index(drop=True)
    print(f"[{name}] {len(wdf)} days with {min_wind}-{max_wind} m/s wind at 100 m", file=sys.stderr)
    rows = []
    bins = list(zip(xs[:-1], xs[1:]))
    per_call = max(1, 1800 // (len(bins) + 1))
    t0 = time.time()
    for i in range(0, len(wdf), per_call):
        chunk = wdf.iloc[i:i + per_call]
        feats = []
        for _, r in chunk.iterrows():
            for (a, b) in bins:
                feats.append(ee.Feature(rect(ee, lat, lon, r.phi, a, b, half_w), {"d": r.d, "x": (a + b) / 2}))
            feats.append(ee.Feature(pt.buffer(15000), {"d": r.d, "x": "cloud"}))
        fc = ee.FeatureCollection(feats)

        def m(f):
            d = ee.Date(f.get("d"))
            img = no2c.filterDate(d, d.advance(1, "day")).mean()
            v = img.reduceRegion(ee.Reducer.mean(), f.geometry(), 1000)
            return f.set({"no2": v.get(KEY, -999), "cf": v.get("cloud_fraction", -999)})
        for attempt in range(3):
            try:
                out = fc.map(m).getInfo()["features"]
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5)
        for f in out:
            p = f["properties"]
            rows.append(dict(d=p["d"], x=p["x"], no2=p.get("no2"), cf=p.get("cf")))
        print(f"  {min(i + per_call, len(wdf))}/{len(wdf)} days ({time.time() - t0:.0f}s)", file=sys.stderr)
    df = pd.DataFrame(rows)
    for c in ("no2", "cf"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] < -900, c] = np.nan
    cloud = df[df.x == "cloud"].set_index("d").cf
    prof = df[df.x != "cloud"].copy()
    prof["x"] = prof.x.astype(float)
    piv = prof.pivot(index="d", columns="x", values="no2")
    piv = piv.join(wdf.set_index("d")[["speed", "phi"]]).join(cloud.rename("cloud"))
    piv = piv[(piv.cloud <= max_cloud)].dropna(subset=[c for c in piv.columns if isinstance(c, float)])
    print(f"[{name}] {len(piv)} usable days after cloud filter (cloud fraction <= {max_cloud})", file=sys.stderr)
    return piv


def fit_emg(xkm, F):
    """F(x) = off + E * [exp(-x/x0) convolved with Gaussian(sigma)], via the closed-form EMG."""
    from scipy.optimize import curve_fit
    from scipy.special import erfc

    def emg(x, E, x0, sig, off):
        lam = 1.0 / x0
        return off + E * 0.5 * np.exp(0.5 * lam * lam * sig * sig - lam * x) * erfc((lam * sig * sig - x) / (math.sqrt(2) * sig))
    p0 = [max(F.max(), 1e-3), 15.0, 4.0, np.median(F[xkm < -4]) if (xkm < -4).any() else 0.0]
    lo = [0, 3.0, 1.0, -abs(F).max() - 1e-9]
    hi = [abs(F).max() * 10 + 1, 120.0, 15.0, abs(F).max() + 1e-9]
    popt, pcov = curve_fit(emg, xkm, F, p0=p0, bounds=(lo, hi), maxfev=20000)
    return popt, emg


def estimate(piv, xs, half_w, label, n_boot=200):
    xcols = sorted(c for c in piv.columns if isinstance(c, float))
    xkm = np.array(xcols) / 1000.0
    up = [c for c in xcols if c <= -4000]
    L = piv[xcols].sub(piv[up].mean(axis=1), axis=0) * (2 * half_w)      # mol/m
    F = L.mul(piv.speed, axis=0)                                          # mol/s
    comp = F.mean(axis=0).to_numpy()
    popt, emg = fit_emg(xkm, comp)
    E = popt[0]
    boots = []
    rng = np.random.default_rng(0)
    for _ in range(n_boot):
        idx = rng.integers(0, len(F), len(F))
        try:
            boots.append(fit_emg(xkm, F.iloc[idx].mean(axis=0).to_numpy())[0][0])
        except Exception:
            pass
    se = float(np.std(boots)) if boots else float("nan")
    kgh = E * NOX_NO2 * MW_NO2 * 3600
    tpy = kgh * 24 * 365.25 / 1000 / 1.10231  # short tons
    print(f"\n== {label}: {len(F)} days composited")
    print(f"   NO2 emission rate E = {E:.2f} ± {se:.2f} mol/s   (x0 = {popt[1]:.1f} km, sigma = {popt[2]:.1f} km, offset {popt[3]:+.2f})")
    print(f"   NOx (x1.32): {kgh:.0f} ± {se * NOX_NO2 * MW_NO2 * 3600:.0f} kg/h  =  {tpy:.0f} ± {se / E * tpy if E else float('nan'):.0f} short tons/yr")
    print("   composite F(x) [mol/s] by x km: " + ", ".join(f"{x:+.0f}:{v:.1f}" for x, v in zip(xkm, comp)))
    return dict(label=label, n_days=int(len(F)), E_mol_s=float(E), E_se=se, nox_kg_h=float(kgh), nox_tpy=float(tpy), x0_km=float(popt[1]), sigma_km=float(popt[2]), offset=float(popt[3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--half-width-km", type=float, default=12.0)
    ap.add_argument("--max-cloud", type=float, default=0.3)
    ap.add_argument("--split", default=None, help="optional YYYY-MM-DD: also report before/after this date")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    days = pd.date_range(args.start, args.end, freq="D")
    xs = list(range(-12000, 30001, 2000))
    piv = daily_profiles(ee, args.name, args.lat, args.lon, days, xs, args.half_width_km * 1000, args.max_cloud)
    if args.out:
        piv.to_csv(args.out)
    res = [estimate(piv, xs, args.half_width_km * 1000, f"{args.name} {args.start}..{args.end}")]
    if args.split:
        res.append(estimate(piv[piv.index < args.split], xs, args.half_width_km * 1000, f"{args.name} before {args.split}"))
        res.append(estimate(piv[piv.index >= args.split], xs, args.half_width_km * 1000, f"{args.name} from {args.split}"))
    if args.out:
        pd.DataFrame(res).to_csv(args.out.replace(".csv", "_estimates.csv"), index=False)


if __name__ == "__main__":
    main()
