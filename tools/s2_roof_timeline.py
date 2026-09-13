"""Sentinel-2 roof timeline per hall polygon: monthly median visible brightness and the month each
roof appeared (construction phase tracking).

    EE_PROJECT=<project> python tools/s2_roof_timeline.py data/polygons/stargate_abilene.geojson \
        --start 2023-01-01 --out results_s2/abilene_roofs.csv

Bare soil reflects ~0.08-0.20 in the visible, a white membrane roof 0.35-0.55; roofs then darken
over 6-9 months as rooftop equipment is fitted.  "Roof on" = first month at or above --threshold
sustained into the next month.  Cloud and shadow pixels are removed with the Scene Classification
Layer; images with fewer than --min-px valid pixels in a polygon are ignored for that polygon.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import geom as G  # noqa: E402



def roof_on_month(series, thr=0.30, jump=0.08, roof_like=0.22):
    v = series.dropna()
    if len(v) < 3:
        return "not_yet"
    base = float(v.iloc[:6].median())
    if base >= roof_like:
        return "existing"
    level = max(min(thr, base + 2 * jump), base + jump)
    for k in range(len(v) - 1):
        if v.iloc[k] >= level and v.iloc[k + 1] >= level:
            return str(v.index[k])
    return "not_yet"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("polygons")
    ap.add_argument("--ptype", default="hall")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--min-px", type=int, default=10)
    ap.add_argument("--max-cloud", type=float, default=60.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    polys = [p for p in G.load_site_polygons(Path(args.polygons)) if p.ptype == args.ptype]
    if not polys:
        sys.exit(f"no polygons of ptype {args.ptype}")
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {"name": p.name}) for p in polys])
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")

    def clean(img):
        scl = img.select("SCL")
        ok = scl.neq(0).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
        return img.select(["B2", "B3", "B4"]).multiply(1e-4).reduce(ee.Reducer.mean()).rename("bright").updateMask(ok).set("d", img.date().format("YYYY-MM-dd"))
    rows = []
    # Earth Engine returns at most 5000 features per query: chunk the date range so polygons x images stays under it
    step = 12 if len(polys) <= 12 else (3 if len(polys) <= 40 else 1)
    periods = pd.period_range(args.start[:7], end[:7], freq="M")
    for k in range(0, len(periods), step):
        p0, p1 = periods[k], periods[min(k + step - 1, len(periods) - 1)]
        d0, d1 = max(args.start, p0.strftime("%Y-%m-01")), min(end, (p1 + 1).strftime("%Y-%m-01"))
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(fc.geometry())
              .filterDate(d0, d1).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", args.max_cloud)).map(clean))
        feats = s2.map(lambda img: img.reduceRegions(fc, ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), 10)
                       .map(lambda f: f.set("d", img.get("d")))).flatten().getInfo()["features"]
        rows += [dict(name=f["properties"]["name"], d=f["properties"]["d"], bright=f["properties"].get("mean"), n=f["properties"].get("count", 0)) for f in feats]
        print(f"  {p0}..{p1}: {len(feats)} polygon-images", file=sys.stderr)
    df = pd.DataFrame(rows).dropna(subset=["bright"])
    df = df[df.n >= args.min_px]
    df["ym"] = df.d.str[:7]
    piv = df.groupby(["ym", "name"]).bright.median().unstack().sort_index()
    print(piv.round(2).to_string())
    print("\nroof-on month (brightness rises >= 0.08 above the polygon's own early baseline, sustained; 'existing' if already roof-like):")
    for c in piv.columns:
        print(f"  {c:26s} {roof_on_month(piv[c], args.threshold)}")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        piv.to_csv(args.out)
        print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
