"""Features for radar candidates (or any polygon set) in the same definition as results_campus/train_features.csv:
Google satellite-embedding means (64 bands) in 50 m and 250 m discs around a point inside each polygon, plus a few
Sentinel-2 spectral statistics over the polygon itself.

    EE_PROJECT=<project> python tools/cand_features.py "results_s1/*_candidates.geojson" "results_s1/china/*_candidates.geojson" \
        --year 2025 --out results_cand/candidate_features.csv

Rows carry file, name, rank, area_ha, rise_db, lat, lon (the representative point), A00_r..A63_r, A00_m..A63_m,
bright, ndvi, bright_frac. Files are processed one at a time (<= 300 polygons each) so no query exceeds Earth Engine's
feature cap; quota errors are retried.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from shapely.geometry import shape


def getinfo_retry(obj, tries=6, wait=60):
    for i in range(tries):
        try:
            return obj.getInfo()
        except Exception as e:
            if i == tries - 1 or ("concurrent" not in str(e) and "quota" not in str(e).lower() and "timed out" not in str(e).lower()):
                raise
            print(f"  retry {i + 1}/{tries}: {str(e)[:80]}", file=sys.stderr)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns", nargs="+")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    emb = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate(f"{args.year}-01-01", f"{args.year}-12-31").mosaic()
    bands = [f"A{i:02d}" for i in range(64)]

    def s2mask(img):
        scl = img.select("SCL")
        return img.updateMask(scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(0)))
    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(f"{args.year}-01-01", f"{args.year}-12-31")
          .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80)).map(s2mask).median())
    bright = s2.select(["B2", "B3", "B4"]).multiply(1e-4).reduce(ee.Reducer.mean()).rename("bright")
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("ndvi")
    spec = ee.Image.cat([bright, ndvi, bright.gt(0.3).rename("bright_frac")])

    files = sorted(set(f for p in args.patterns for f in glob.glob(p)))
    rows = []
    for f in files:
        gj = json.load(open(f))
        feats = gj["features"]
        if not feats:
            continue
        pts, polys = [], []
        for k, ft in enumerate(feats):
            geom = shape(ft["geometry"])
            rp = geom.representative_point()
            pr = ft.get("properties", {})
            meta = dict(file=f, name=pr.get("name", f"f{k}"), rank=pr.get("rank"), area_ha=pr.get("area_ha"), rise_db=pr.get("rise_db"), lat=round(rp.y, 5), lon=round(rp.x, 5))
            pts.append(ee.Feature(ee.Geometry.Point([rp.x, rp.y]), {"k": k}))
            polys.append(ee.Feature(ee.Geometry(ft["geometry"]), {"k": k}))
            rows.append(meta)
        base = len(rows) - len(feats)
        fc_pts = ee.FeatureCollection(pts)
        for suffix, radius in (("_r", 50), ("_m", 250)):
            fc = fc_pts.map(lambda ft: ft.buffer(radius))
            res = getinfo_retry(emb.reduceRegions(fc, ee.Reducer.mean(), 10))["features"]
            for r in res:
                k = r["properties"]["k"]
                for b in bands:
                    rows[base + k][b + suffix] = r["properties"].get(b)
        res = getinfo_retry(spec.reduceRegions(ee.FeatureCollection(polys), ee.Reducer.mean(), 10))["features"]
        for r in res:
            k = r["properties"]["k"]
            for b in ("bright", "ndvi", "bright_frac"):
                rows[base + k][b] = r["properties"].get(b)
        print(f"  {f}: {len(feats)} polygons", file=sys.stderr)
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(df)} rows from {len(files)} files")


if __name__ == "__main__":
    main()
