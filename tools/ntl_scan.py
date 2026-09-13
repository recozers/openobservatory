"""Night-lights change scan: places inside a box that lit up between two 3-month windows (VIIRS VNP46A2 daily
gap-filled radiance, 500 m; medians over the window). A cheap first pass for new large sites anywhere; candidates are then checked in Sentinel-2/1.

    EE_PROJECT=<project> python tools/ntl_scan.py --box LAT_S LON_W LAT_N LON_E --name inner_mongolia \
        [--late 2026-06] [--years-back 3] [--min-diff 10] [--min-ratio 3] --out results_ntl/scan_inner_mongolia.csv

late = median of the daily radiance over the 3 months ending at --late (default: latest available month), quality
flag 0 and no snow; early = the same 3 calendar months --years-back earlier. A pixel is flagged when late-early >= --min-diff
(nW/cm^2/sr) and (late+1)/(early+1) >= --min-ratio; flagged pixels are grouped into 8-connected blobs of at least
--min-px pixels and ranked by summed brightening. Output columns: lat, lon (blob centroid), n_px, area_km2,
early, late, diff (means over the blob), sum_diff.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

BAND = "Gap_Filled_DNB_BRDF_Corrected_NTL"


def latest_month():
    import ee
    now = pd.Timestamp.utcnow()
    col = ee.ImageCollection("NASA/VIIRS/002/VNP46A2").filterDate((now - pd.Timedelta(days=120)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))
    t = col.aggregate_max("system:time_start").getInfo()
    last = pd.Timestamp(t, unit="ms")
    return (last if last.day >= 25 else last - pd.offsets.MonthBegin(1)).strftime("%Y-%m")


def window_median(box, end_ym, months=3):
    import ee
    end = pd.Period(end_ym, freq="M")
    start = end - (months - 1)

    def clean(img):
        ok = img.select("Mandatory_Quality_Flag").eq(0).And(img.select("Snow_Flag").eq(0))
        return img.select(BAND).updateMask(ok)
    col = (ee.ImageCollection("NASA/VIIRS/002/VNP46A2").filterBounds(box)
           .filterDate(start.strftime("%Y-%m-01"), (end + 1).strftime("%Y-%m-01")).map(clean))
    return col.median(), f"{start}..{end}"


def scan_box(s, w, n, e, late_ym, years_back=3, min_diff=10.0, min_ratio=3.0, min_px=2, limit=400, name=""):
    import ee
    box = ee.Geometry.Rectangle([w, s, e, n])
    early_ym = str(pd.Period(late_ym, freq="M") - 12 * years_back)
    late, lw = window_median(box, late_ym)
    early, ew = window_median(box, early_ym)
    diff = late.subtract(early).rename("diff")
    ratio = late.add(1).divide(early.add(1))
    mask = diff.gte(min_diff).And(ratio.gte(min_ratio)).selfMask()
    blobs = mask.reduceToVectors(reducer=ee.Reducer.countEvery(), geometry=box, scale=500, geometryType="polygon",
                                 eightConnected=True, labelProperty="lab", bestEffort=True, maxPixels=1e9)
    blobs = blobs.filter(ee.Filter.gte("count", min_px))
    stats = ee.Image.cat([early.rename("early"), late.rename("late"), diff]).reduceRegions(blobs, ee.Reducer.mean(), 500)
    stats = stats.map(lambda f: f.set("sum_diff", ee.Number(f.get("diff")).multiply(f.get("count")),
                                      "lat", f.geometry().centroid(1).coordinates().get(1),
                                      "lon", f.geometry().centroid(1).coordinates().get(0)))
    feats = stats.sort("sum_diff", False).limit(limit).getInfo()["features"]
    rows = [dict(lat=round(f["properties"]["lat"], 4), lon=round(f["properties"]["lon"], 4), n_px=int(f["properties"]["count"]),
                 area_km2=round(0.25 * f["properties"]["count"], 2), early=round(f["properties"].get("early", 0), 1),
                 late=round(f["properties"].get("late", 0), 1), diff=round(f["properties"]["diff"], 1),
                 sum_diff=round(f["properties"]["sum_diff"], 0), tile=name) for f in feats]
    return pd.DataFrame(rows, columns=["lat", "lon", "n_px", "area_km2", "early", "late", "diff", "sum_diff", "tile"]), lw, ew


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", nargs=4, type=float, required=True, metavar=("LAT_S", "LON_W", "LAT_N", "LON_E"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--late", default=None)
    ap.add_argument("--years-back", type=int, default=3)
    ap.add_argument("--min-diff", type=float, default=10.0)
    ap.add_argument("--min-ratio", type=float, default=3.0)
    ap.add_argument("--min-px", type=int, default=2)
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    s, w, n, e = args.box
    late_ym = args.late or latest_month()
    df, lw, ew = scan_box(s, w, n, e, late_ym, args.years_back, args.min_diff, args.min_ratio, args.min_px, args.limit, args.name)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{args.name}: {len(df)} blobs (>= {args.min_px} px, diff >= {args.min_diff}, ratio >= {args.min_ratio}); windows late {lw} early {ew}")
    print(df.head(40).to_string(index=False))


if __name__ == "__main__":
    main()
