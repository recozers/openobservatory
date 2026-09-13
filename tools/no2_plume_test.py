"""Wind-resolved TROPOMI NO2 plume test for a site with (suspected) on-site combustion.

For every day with Sentinel-5P coverage, takes the 10 m wind at the ~13:30 local overpass from
ERA5-Land, and compares the mean tropospheric NO2 column in a DOWNWIND annular sector (2-15 km,
+/-30 deg) with the UPWIND sector.  A real emitter shows downwind > upwind, only after it starts,
only along the wind (crosswind pair ~0), larger at low wind speed, and absent at a control point.

    EE_PROJECT=<project> python tools/no2_plume_test.py --lat 32.5 --lon -99.783 \
        --change 2025-06-01 --control 32.35,-99.35 --out results_no2/abilene.csv

Free data only (Earth Engine account needed).  Resolution ~5 km, so this only works where the site
is the dominant local source; it does not work next to a power plant or a city centre.
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


def sector(ee, lat, lon, phi_deg, r1=2000, r2=15000, half=30):
    k = 111320
    kx = k * math.cos(math.radians(lat))
    pts = []
    for a in np.linspace(phi_deg - half, phi_deg + half, 13):
        pts.append([lon + r2 * math.sin(math.radians(a)) / kx, lat + r2 * math.cos(math.radians(a)) / k])
    for a in np.linspace(phi_deg + half, phi_deg - half, 13):
        pts.append([lon + r1 * math.sin(math.radians(a)) / kx, lat + r1 * math.cos(math.radians(a)) / k])
    return ee.Geometry.Polygon([pts])


def run_site(ee, name, lat, lon, days, min_wind=2.0):
    era = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").select(["u_component_of_wind_10m", "v_component_of_wind_10m"])
    no2 = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2").select(KEY)
    pt = ee.Geometry.Point([lon, lat])
    wind = {}
    for i in range(0, len(days), 400):
        fc = ee.FeatureCollection([ee.Feature(pt, {"d": d.strftime("%Y-%m-%d")}) for d in days[i:i + 400]])

        def w(f):
            d = ee.Date(f.get("d"))
            v = era.filterDate(d.advance(19, "hour"), d.advance(21, "hour")).mean().reduceRegion(ee.Reducer.first(), f.geometry(), 11132)
            return f.set({"u": v.get("u_component_of_wind_10m", -999), "v": v.get("v_component_of_wind_10m", -999)})
        for f in fc.map(w).getInfo()["features"]:
            p = f["properties"]
            wind[p["d"]] = (p.get("u"), p.get("v"))
    wdf = pd.DataFrame([(d, u, v) for d, (u, v) in wind.items()], columns=["d", "u", "v"])
    wdf = wdf[(wdf.u > -900) & (wdf.v > -900)].copy()
    wdf["speed"] = np.hypot(wdf.u, wdf.v)
    wdf["phi"] = (np.degrees(np.arctan2(wdf.u, wdf.v)) + 360) % 360  # direction the wind blows towards
    wdf = wdf[wdf.speed >= min_wind].reset_index(drop=True)
    print(f"[{name}] {len(wdf)} days with wind >= {min_wind} m/s at overpass", file=sys.stderr)
    rows = []
    for i in range(0, len(wdf), 150):
        chunk = wdf.iloc[i:i + 150]
        feats = []
        for _, r in chunk.iterrows():
            for sec, ang in (("down", 0), ("up", 180), ("cross1", 90), ("cross2", 270)):
                feats.append(ee.Feature(sector(ee, lat, lon, (r.phi + ang) % 360), {"d": r.d, "sec": sec}))
        fc = ee.FeatureCollection(feats)

        def m(f):
            d = ee.Date(f.get("d"))
            img = no2.filterDate(d, d.advance(1, "day")).mean()
            return f.set("no2", img.reduceRegion(ee.Reducer.mean(), f.geometry(), 1000).get(KEY, -999))
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
            rows.append(dict(d=p["d"], sec=p["sec"], no2=p.get("no2")))
    df = pd.DataFrame(rows)
    df["no2"] = pd.to_numeric(df.no2, errors="coerce")
    df.loc[df.no2 < -900, "no2"] = np.nan
    df["no2"] *= 1e6
    piv = df.pivot(index="d", columns="sec", values="no2").dropna().join(wdf.set_index("d")[["speed", "phi"]])
    piv["site"] = name
    piv["dw_minus_uw"] = piv.down - piv.up
    piv["cross_diff"] = piv.cross1 - piv.cross2
    return piv


def summarise(piv, change, name):
    pre, post = piv[piv.index < change], piv[piv.index >= change]

    def s(x):
        return f"{x.mean():+.2f} ± {x.std() / np.sqrt(max(len(x), 1)):.2f} (n={len(x)})" if len(x) else "n/a"
    print(f"\n== {name}: downwind minus upwind NO2 (1e-6 mol/m2), sectors 2-15 km, ±30°")
    print(f"   before {change}: {s(pre.dw_minus_uw)}   |  from {change}: {s(post.dw_minus_uw)}")
    print(f"   crosswind pair (null reference): before {s(pre.cross_diff)} | after {s(post.cross_diff)}")
    if len(post):
        sb = post.assign(sb=pd.cut(post.speed, [0, 4, 6, 30], labels=["<4", "4-6", ">6 m/s"])).groupby("sb", observed=True).dw_minus_uw.agg(["mean", "count"]).round(2)
        print("   after, by wind speed (a point source dilutes with wind):", sb.to_dict())
    if len(pre) and len(post):
        d = post.dw_minus_uw.mean() - pre.dw_minus_uw.mean()
        se = np.sqrt(post.dw_minus_uw.var() / len(post) + pre.dw_minus_uw.var() / len(pre))
        print(f"   change in downwind excess: {d:+.2f} ± {se:.2f} ({d / se:.1f} sigma)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--name", default="site")
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--change", required=True, help="date the source is believed to have started, YYYY-MM-DD")
    ap.add_argument("--control", action="append", default=[], help="lat,lon of a control point (repeatable)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    days = pd.date_range(args.start, end, freq="D")
    res = [run_site(ee, args.name, args.lat, args.lon, days)]
    summarise(res[0], args.change, args.name)
    for i, c in enumerate(args.control):
        la, lo = map(float, c.split(","))
        r = run_site(ee, f"control_{i + 1}", la, lo, days)
        summarise(r, args.change, f"control_{i + 1}")
        res.append(r)
    if args.out:
        pd.concat(res).to_csv(args.out)
        print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
