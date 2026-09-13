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
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import geom as G  # noqa: E402



def roof_on_month(series, thr=0.30, jump=0.08, roof_like=0.22):
    v = series.dropna().sort_index()
    if len(v) < 3:
        return "not_yet"
    base = float(v.iloc[:6].median())
    if base >= roof_like:
        return "existing"
    level = max(min(thr, base + 2 * jump), base + jump)
    for k in range(len(v) - 1):
        consecutive = pd.Period(v.index[k], freq="M") + 1 == pd.Period(v.index[k + 1], freq="M")
        if consecutive and v.iloc[k] >= level and v.iloc[k + 1] >= level:
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
    ap.add_argument("--cache-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data/cache/s2_roofs")
    args = ap.parse_args()
    from dcheat.gee import _ee
    ee = _ee()
    polys = [p for p in G.load_site_polygons(Path(args.polygons)) if p.ptype == args.ptype]
    if not polys:
        sys.exit(f"no polygons of ptype {args.ptype}")
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {"name": p.name}) for p in polys])
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")

    def clean(img):
        scl = img.select("SCL")
        ok = scl.neq(0).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
        return img.select(["B2", "B3", "B4"]).multiply(1e-4).reduce(ee.Reducer.mean()).rename("bright").updateMask(ok).set("d", img.date().format("YYYY-MM-dd")).copyProperties(img, ["system:time_start"])
    rows = []
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    for y in range(int(args.start[:4]), int(end[:4]) + 1):
        start_y, end_y = max(args.start, f"{y}-01-01"), min(end, f"{y + 1}-01-01")
        if start_y >= end_y:
            continue
        key = hashlib.sha256(Path(args.polygons).read_bytes() + json.dumps([start_y, end_y, args.ptype, args.max_cloud, "bright-v2"]).encode()).hexdigest()
        cache = args.cache_dir / f"{key}.json"
        if cache.exists():
            part = json.loads(cache.read_text())
            rows.extend(part)
            print(f"  {y}: {len(part)} cached polygon-images", file=sys.stderr)
            continue
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(fc.geometry())
              .filterDate(start_y, end_y).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", args.max_cloud)).map(clean))
        from dcheat.gee import _fetch_chunked
        for attempt in range(4):
            try:
                feats = _fetch_chunked(ee, s2, lambda img: img.reduceRegions(fc, ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), 10)
                                      .map(lambda f: ee.Feature(None, f.toDictionary()).set("d", img.get("d"))),
                                      start_y, end_y, len(polys), limit=1000)
                break
            except ee.EEException as exc:
                if attempt == 3 or not any(msg in str(exc).lower() for msg in ("concurrent aggregations", "too many requests", "timed out", "internal error")):
                    raise
                print(f"  {y}: transient EE error; retry {attempt + 1}/3", file=sys.stderr)
                time.sleep(2 ** (attempt + 1))
        part = [dict(name=f["properties"]["name"], d=f["properties"]["d"], bright=f["properties"].get("mean"), n=f["properties"].get("count", 0)) for f in feats]
        cache.write_text(json.dumps(part))
        rows.extend(part)
        print(f"  {y}: {len(feats)} polygon-images", file=sys.stderr)
    df = pd.DataFrame(rows, columns=["name", "d", "bright", "n"]).dropna(subset=["bright"])
    df = df[df.n >= args.min_px]
    df["ym"] = df.d.astype(str).str[:7]
    piv = df.groupby(["ym", "name"]).bright.median().unstack().sort_index()
    print(piv.round(2).to_string())
    print("\nroof-on month (brightness rises >= 0.08 above the polygon's own early baseline, sustained; 'existing' if already roof-like):")
    for c in piv.columns:
        print(f"  {c:26s} {roof_on_month(piv[c], args.threshold)}")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        piv.to_csv(args.out)
        summary = {"start": args.start, "end_exclusive": end, "rule": "visible_brightness",
                   "source": "COPERNICUS/S2_SR_HARMONIZED", "threshold": args.threshold,
                   "polygons_sha256": hashlib.sha256(Path(args.polygons).read_bytes()).hexdigest(),
                   "halls": {p.name: {"roof_on": roof_on_month(piv[p.name], args.threshold) if p.name in piv else "unknown",
                                      "first_observation": str(piv[p.name].dropna().index[0]) if p.name in piv and piv[p.name].notna().any() else None,
                                      "valid_months": int(piv[p.name].notna().sum()) if p.name in piv else 0} for p in polys}}
        Path(args.out).with_suffix(".roof_dates.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
