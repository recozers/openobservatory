"""VIIRS night-lights timeline per site: monthly median radiance over the campus against a 3-10 km annulus.

    EE_PROJECT=<project> python tools/ntl_timeline.py stargate_abilene rainier_in --start 2019-01-01 --out-dir results_ntl

Uses NASA Black Marble VNP46A2 daily gap-filled, BRDF-corrected night-time radiance (500 m). The campus is the
union of hall polygons buffered 250 m (or a 600 m disc at the site coordinate when there are no polygons); the
control is the 3-10 km annulus around the site coordinate with the campus cut out. Only days with the mandatory
quality flag 0 and no snow flag are used. Radiance is the raw band value (catalog units nW/cm^2/sr, scale 0.1
per the product spec; treat values as relative). Output: <out-dir>/<site>.csv with monthly medians and a printed
"lit-up" month: first month where campus-minus-annulus exceeds its first-12-month baseline by max(3 MAD, 1.0),
sustained into the next month. Night lights indicate construction activity and campus energisation, not IT load.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import geom as G  # noqa: E402

BAND = "Gap_Filled_DNB_BRDF_Corrected_NTL"


def getinfo_retry(obj, tries=6, wait=60):
    import time
    for i in range(tries):
        try:
            return obj.getInfo()
        except Exception as e:  # Earth Engine quota errors ("Too many concurrent aggregations") clear after a minute
            if i == tries - 1 or "concurrent" not in str(e) and "quota" not in str(e).lower():
                raise
            print(f"  retry {i + 1}/{tries} after: {str(e)[:80]}", file=sys.stderr)
            time.sleep(wait)


def geoms(site_id, row):
    import ee
    pf = Path("data/polygons") / f"{site_id}.geojson"
    centre = ee.Geometry.Point([float(row.lon), float(row.lat)])
    polys = [p for p in G.load_site_polygons(pf) if p.ptype == "hall"] if pf.exists() else []
    if polys:
        campus = ee.FeatureCollection([ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84))) for p in polys]).geometry().buffer(250)
    else:
        campus = centre.buffer(600)
    ring = centre.buffer(10000).difference(centre.buffer(3000)).difference(campus.buffer(500))
    return ee.FeatureCollection([ee.Feature(campus, {"z": "campus"}), ee.Feature(ring, {"z": "ring"})]), bool(polys)


def fetch(site_id, row, start, end):
    import ee
    fc, has_polys = geoms(site_id, row)

    def clean(img):
        ok = img.select("Mandatory_Quality_Flag").eq(0).And(img.select("Snow_Flag").eq(0))
        return img.select(BAND).rename("rad").updateMask(ok).set("d", img.date().format("YYYY-MM-dd"))

    rows = []
    for y in range(int(start[:4]), int(end[:4]) + 1):
        col = (ee.ImageCollection("NASA/VIIRS/002/VNP46A2").filterBounds(fc.geometry())
               .filterDate(max(start, f"{y}-01-01"), min(end, f"{y}-12-31")).map(clean))
        req = col.map(lambda img: img.reduceRegions(fc, ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), 500)
                      .map(lambda f: f.set("d", img.get("d")))).flatten()
        feats = getinfo_retry(req)["features"]
        rows += [dict(z=f["properties"]["z"], d=f["properties"]["d"], rad=f["properties"].get("mean"), n=f["properties"].get("count", 0)) for f in feats]
        print(f"  {site_id} {y}: {len(feats)} rows", file=sys.stderr)
    return pd.DataFrame(rows), has_polys


def summarise(df, min_days=5):
    df = df.dropna(subset=["rad"])
    df = df[df.n > 0]
    df["ym"] = df.d.str[:7]
    m = df.groupby(["ym", "z"]).rad.agg(["median", "count"]).unstack()
    out = pd.DataFrame({"campus": m[("median", "campus")], "ring": m[("median", "ring")],
                        "n_days": m[("count", "campus")]}).sort_index()
    out = out[out.n_days >= min_days]
    out["diff"] = out.campus - out.ring
    return out


def lit_month(diff, sustain=6, min_hist=12):
    """First month whose campus-minus-annulus radiance is >= max(5 MAD, 5.0) above the median of all earlier
    months, for `sustain` consecutive months. Short blips (a few months of temporary lighting) do not pass."""
    v = diff.dropna()
    for k in range(min_hist, len(v) - sustain + 1):
        hist = v.iloc[:k]
        mad = float((hist - hist.median()).abs().median())
        level = float(hist.median()) + max(5 * 1.4826 * mad, 5.0)
        if bool((v.iloc[k:k + sustain] >= level).all()):
            return f"{v.index[k]} (baseline {hist.median():.1f}, level {level:.1f}, reached {float(v.iloc[k:k + sustain].median()):.1f})"
    return "not_yet" if len(v) >= min_hist + sustain else "insufficient"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", nargs="+")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out-dir", default="results_ntl")
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    sites = pd.read_csv("data/sites.csv").set_index("site_id")
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    for sid in args.sites:
        raw, has_polys = fetch(sid, sites.loc[sid], args.start, end)
        raw.to_csv(Path(args.out_dir) / f"{sid}.raw.csv", index=False)
        out = summarise(raw)
        out.to_csv(Path(args.out_dir) / f"{sid}.csv")
        print(f"\n{sid} ({'polygons' if has_polys else 'point disc'}): campus, ring, campus-ring by month")
        print(out.round(1).to_string())
        print(f"lit-up month: {lit_month(out['diff'])}")


if __name__ == "__main__":
    main()
