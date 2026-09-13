"""Winter snow persistence on hall roofs against control roofs and the built-up surroundings (Sentinel-2).

    EE_PROJECT=<project> python tools/snow_persistence.py fairwater_wi --controls ctrl_racine_mke1 ctrl_racine_b \
        --start 2018-11-01 --out results_snow/fairwater_wi.csv

Question: does an operating data hall shed snow faster than an ordinary large roof nearby (warm exhaust, rooftop
plant), so that snow cover after a snowfall is an on/off indicator? For every Sentinel-2 scene in Nov-Mar the
script computes, per polygon, the fraction of valid pixels classed as snow (SCL 11, or NDSI > 0.4 with green
reflectance > 0.12), and the same fraction over built-up pixels (ESA WorldCover 2021 class 50) in a 0.5-3 km ring
around the site with the halls cut out. Scenes where the built-up ring is at least 40 % snow-covered are
"snow days"; the per-winter table compares mean snow fraction on those days for halls, control roofs and the ring.
Raw per-scene rows go to <out>.raw.csv before any summary is computed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import geom as G  # noqa: E402

BAD_SCL = [0, 1, 3, 8, 9, 10]


def load(site_id, prefix):
    import ee
    pf = Path("data/polygons") / f"{site_id}.geojson"
    polys = [p for p in G.load_site_polygons(pf) if p.ptype == "hall"]
    return [ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {"name": f"{prefix}{p.name}"}) for p in polys]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--controls", nargs="*", default=[])
    ap.add_argument("--start", default="2018-11-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--max-cloud", type=float, default=70.0)
    ap.add_argument("--min-px", type=int, default=10)
    ap.add_argument("--snow-day", type=float, default=0.4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    sites = pd.read_csv("data/sites.csv").set_index("site_id")
    row = sites.loc[args.site]
    halls = load(args.site, "hall:")
    ctrls = [f for c in args.controls for f in load(c, f"ctrl:{c}:")]
    fc = ee.FeatureCollection(halls + ctrls)
    hall_geom = ee.FeatureCollection(halls).geometry()
    centre = ee.Geometry.Point([float(row.lon), float(row.lat)])
    ring = centre.buffer(3000).difference(centre.buffer(500)).difference(hall_geom.buffer(100))
    builtup = ee.Image("ESA/WorldCover/v200/2021").select("Map").eq(50)
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")

    def classify(img):
        scl = img.select("SCL")
        valid = scl.neq(BAD_SCL[0])
        for c in BAD_SCL[1:]:
            valid = valid.And(scl.neq(c))
        ndsi = img.normalizedDifference(["B3", "B11"])
        snow = scl.eq(11).Or(ndsi.gt(0.4).And(img.select("B3").multiply(1e-4).gt(0.12))).And(valid)
        return snow.rename("snow").updateMask(valid).set("d", img.date().format("YYYY-MM-dd"))

    winter = ee.Filter.Or(ee.Filter.calendarRange(11, 12, "month"), ee.Filter.calendarRange(1, 3, "month"))
    rows = []
    for y in range(int(args.start[:4]), int(end[:4]) + 1):
        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ring.bounds())
               .filterDate(max(args.start, f"{y}-01-01"), min(end, f"{y}-12-31")).filter(winter)
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", args.max_cloud)).map(classify))
        red = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)
        polys = col.map(lambda img: img.reduceRegions(fc, red, 10).map(lambda f: f.set("d", img.get("d")))).flatten()
        rings = col.map(lambda img: ee.Feature(ring, img.updateMask(builtup).reduceRegion(red, ring, 10)).set("d", img.get("d"), "name", "ring:builtup"))
        feats = polys.merge(rings).getInfo()["features"]
        rows += [dict(name=f["properties"]["name"], d=f["properties"]["d"], snow=f["properties"].get("mean", f["properties"].get("snow_mean")),
                      n=f["properties"].get("count", f["properties"].get("snow_count", 0))) for f in feats]
        print(f"  {args.site} {y}: {len(feats)} rows", file=sys.stderr)
    raw = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(Path(args.out).with_suffix(".raw.csv"), index=False)
    df = raw.dropna(subset=["snow"])
    df = df[df.n >= args.min_px]
    piv = df.pivot_table(index="d", columns="name", values="snow")
    piv.to_csv(args.out)
    if "ring:builtup" not in piv:
        sys.exit("no ring data")
    snowdays = piv[piv["ring:builtup"] >= args.snow_day].copy()
    snowdays["winter"] = [f"{int(d[:4]) + (1 if int(d[5:7]) >= 11 else 0)}" for d in snowdays.index]
    hall_cols = [c for c in piv.columns if c.startswith("hall:")]
    ctrl_cols = [c for c in piv.columns if c.startswith("ctrl:")]
    print(f"\n{args.site}: snow days = scenes with built-up ring >= {args.snow_day:.0%} snow; mean snow fraction on those days")
    tab = snowdays.groupby("winter").agg(n_days=("ring:builtup", "size"), ring=("ring:builtup", "mean"))
    if hall_cols:
        tab["halls"] = snowdays.groupby("winter")[hall_cols].mean().mean(axis=1)
    if ctrl_cols:
        tab["ctrl_roofs"] = snowdays.groupby("winter")[ctrl_cols].mean().mean(axis=1)
    print(tab.round(2).to_string())
    per = snowdays.groupby("winter")[hall_cols + ctrl_cols].mean().T
    print("\nper polygon (winter columns are the January year):")
    print(per.round(2).to_string())


if __name__ == "__main__":
    main()
