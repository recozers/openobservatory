"""Fill ERA5-Land weather covariates into an observations CSV using Earth Engine.

    EE_PROJECT=<project> python tools/fill_weather_gee.py data/observations_eco.csv

For every (site, acquisition time) that lacks `t2m_k`, samples ECMWF/ERA5_LAND/HOURLY
at the nearest hour (the same convention as the GEE Landsat backend) at the site
point, then derives air temperature, dew point, RH, wind speed, specific humidity
and wet-bulb temperature with dcheat.met.derive.  One server-side request per
chunk of times, so thousands of observations take minutes, and it does not depend
on the AWS ERA5 mirror.  The CSV is rewritten in place after a `.bak` copy.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import met as MET  # noqa: E402

VARS = ["temperature_2m", "dewpoint_temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m"]
COLS = ["t2m_k", "d2m_k", "u10", "v10"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("obs")
    ap.add_argument("--sites", default="data/sites.csv")
    ap.add_argument("--chunk", type=int, default=400)
    ap.add_argument("--force", action="store_true", help="refill even where t2m_k is present")
    args = ap.parse_args()

    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")

    obs = pd.read_csv(args.obs, dtype={"product_id": str})
    sites = pd.read_csv(args.sites).set_index("site_id")
    for c in COLS:
        if c not in obs:
            obs[c] = np.nan
    need = obs if args.force else obs[obs.t2m_k.isna()]
    keys = need[["site_id", "datetime_utc"]].drop_duplicates()
    print(f"{len(keys)} site-times to fill over {keys.site_id.nunique()} sites", file=sys.stderr)

    def sample(feat):
        t = ee.Date(feat.get("t"))
        img = era5.filterDate(t.advance(-30, "minute"), t.advance(30, "minute")).first()
        vals = ee.Algorithms.If(img, ee.Image(img).select(VARS).reduceRegion(ee.Reducer.first(), feat.geometry(), 11132), ee.Dictionary({}))
        return feat.set(ee.Dictionary(vals))

    recs = []
    for sid, ks in keys.groupby("site_id"):
        lat, lon = float(sites.loc[sid].lat), float(sites.loc[sid].lon)
        times = ks.datetime_utc.tolist()
        for i in range(0, len(times), args.chunk):
            chunk = times[i:i + args.chunk]
            fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lon, lat]), {"t": pd.Timestamp(t).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%S"), "k": t}) for t in chunk])
            out = fc.map(sample).getInfo()["features"]
            for f in out:
                p = f["properties"]
                recs.append(dict(site_id=sid, datetime_utc=p["k"], **{c: p.get(v) for c, v in zip(COLS, VARS)}))
            print(f"[{sid}] {min(i + args.chunk, len(times))}/{len(times)}", file=sys.stderr)
    w = pd.DataFrame(recs)
    if w.empty:
        print("nothing to fill", file=sys.stderr)
        return
    # several polygon rows share one acquisition, so map by key rather than assigning by index
    w = w.drop_duplicates(["site_id", "datetime_utc"]).set_index(["site_id", "datetime_utc"])
    key_index = pd.MultiIndex.from_frame(obs[["site_id", "datetime_utc"]])
    for c in COLS:
        filled = pd.to_numeric(w[c], errors="coerce").reindex(key_index).to_numpy()
        obs[c] = np.where(np.isfinite(filled), filled, obs[c].to_numpy(dtype=float))
    elev = obs.site_id.map(sites.elev_m).fillna(0.0).astype(float)
    ok = obs[COLS].notna().all(axis=1)
    d = MET.derive(obs.loc[ok, "t2m_k"].astype(float), obs.loc[ok, "d2m_k"].astype(float), obs.loc[ok, "u10"].astype(float), obs.loc[ok, "v10"].astype(float), elev_m=elev[ok])
    for k, v in d.items():
        obs.loc[ok, k] = np.round(np.asarray(v, dtype=float), 4)
    src = Path(args.obs)
    src.with_suffix(src.suffix + ".bak").write_bytes(src.read_bytes())
    obs.to_csv(src, index=False)
    print(f"filled {int(ok.sum())} of {len(obs)} rows; wrote {src}", file=sys.stderr)


if __name__ == "__main__":
    main()
