"""Sentinel-1 radar for construction tracking where optical imagery is cloudy.

Per-polygon timeline (monthly median VV and VH backscatter in dB, one relative orbit for constant geometry):
    EE_PROJECT=<project> python tools/s1_timeline.py data/polygons/cn_ulanqab_park.geojson --start 2018-01-01 \
        --out results_s1/cn_ulanqab_park.csv
Change chips for a box around a point (median VV late minus early, plus early/late VV and a cloud-masked
Sentinel-2 reference composite):
    python tools/s1_timeline.py --chip 26.40 106.42 --half 6000 --early 2021 --late 2026 --out results_s1/guian

New buildings raise VV backscatter by several dB (double bounce off walls) and appear in every pass regardless
of cloud. Values depend on look geometry, so one relative orbit is used for the time series (the one with the
most scenes over the area). Raw per-scene rows go to <out>.raw.csv before the monthly summary.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcheat import geom as G  # noqa: E402


def s1(aoi, start, end):
    import ee
    return (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(aoi).filterDate(start, end)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")))


def dominant_orbit(col):
    h = col.aggregate_histogram("relativeOrbitNumber_start").getInfo()
    if not h:
        sys.exit("no Sentinel-1 scenes")
    orb = int(float(max(h, key=h.get)))
    print(f"  relative orbits seen {h}; using {orb}", file=sys.stderr)
    return int(orb)


def s1_on(series, jump=4.0, sustain=6, min_hist=6):
    """First month whose VV is >= jump dB above the 20th percentile of all earlier months, for `sustain`
    consecutive months. Seasonal swings over fields (2-3 dB, one or two quarters) do not pass; new halls
    at Abilene rise 8-12 dB and stay there."""
    v = series.dropna()
    for k in range(min_hist, len(v) - sustain + 1):
        base = float(v.iloc[:k].quantile(0.2))
        if bool((v.iloc[k:k + sustain] >= base + jump).all()):
            return f"{v.index[k]} (base {base:.1f} dB, +{float(v.iloc[k:k + sustain].median()) - base:.1f})"
    return "not_yet" if len(v) >= min_hist + sustain else "insufficient"


def timeline(args):
    import ee
    polys = [p for p in G.load_site_polygons(Path(args.polygons)) if p.ptype == "hall"]
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {"name": p.name}) for p in polys])
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    orb = dominant_orbit(s1(fc.geometry(), args.start, end))
    rows = []
    for y in range(int(args.start[:4]), int(end[:4]) + 1):
        col = s1(fc.geometry(), max(args.start, f"{y}-01-01"), min(end, f"{y}-12-31")).filter(ee.Filter.eq("relativeOrbitNumber_start", orb))
        col = col.map(lambda img: img.select(["VV", "VH"]).set("d", img.date().format("YYYY-MM-dd")))
        feats = col.map(lambda img: img.reduceRegions(fc, ee.Reducer.mean(), 10).map(lambda f: f.set("d", img.get("d")))).flatten().getInfo()["features"]
        rows += [dict(name=f["properties"]["name"], d=f["properties"]["d"], VV=f["properties"].get("VV"), VH=f["properties"].get("VH")) for f in feats]
        print(f"  {y}: {len(feats)} rows", file=sys.stderr)
    raw = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(Path(args.out).with_suffix(".raw.csv"), index=False)
    raw = raw.dropna(subset=["VV"])
    raw["ym"] = raw.d.str[:7]
    piv = raw.groupby(["ym", "name"])[["VV", "VH"]].median().unstack()
    piv.columns = [f"{b}:{n}" for b, n in piv.columns]
    piv = piv.sort_index()
    piv.to_csv(args.out)
    print(piv.round(1).to_string())
    print("\nradar structure-on month (VV >= 4 dB above the 20th percentile of all earlier months, sustained 6 months):")
    for c in [c for c in piv.columns if c.startswith("VV:")]:
        print(f"  {c[3:]:26s} {s1_on(piv[c])}")


def chips(args):
    import ee
    lat, lon = args.chip
    box = ee.Geometry.Point([lon, lat]).buffer(args.half).bounds()
    orb = dominant_orbit(s1(box, f"{args.early}-01-01", f"{args.late}-12-31"))
    def med(y):
        return s1(box, f"{y}-01-01", f"{y}-12-31").filter(ee.Filter.eq("relativeOrbitNumber_start", orb)).select("VV").median()
    early, late = med(args.early), med(args.late)
    diff = late.subtract(early)
    def s2ref(y):
        def mask(img):
            scl = img.select("SCL")
            ok = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(0))
            return img.updateMask(ok)
        return (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(box).filterDate(f"{y}-01-01", f"{y}-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80)).map(mask).median().select(["B4", "B3", "B2"]).multiply(1e-4))
    outs = {
        f"vv_{args.early}": early.visualize(min=-22, max=2),
        f"vv_{args.late}": late.visualize(min=-22, max=2),
        f"vv_diff_{args.early}_{args.late}": diff.visualize(min=-6, max=6, palette=["0000ff", "ffffff", "ff0000"]),
        f"s2_{args.late}": s2ref(args.late).visualize(min=0, max=0.3),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    for k, img in outs.items():
        url = img.getThumbURL({"region": box, "dimensions": 900, "format": "png"})
        p = f"{args.out}_{k}.png"
        open(p, "wb").write(requests.get(url, timeout=300).content)
        print(f"wrote {p}", file=sys.stderr)
    print(f"box centre {lat},{lon} half-size {args.half} m; red = VV up (new structure), blue = VV down; orbit {orb}")


def candidates(args):
    """New-structure candidates inside the box: 20 m blobs where median VV rose >= --min-db between the early and late
    year and the late VV is at least --min-vv dB (built-up brightness), area >= --min-px pixels. Writes a CSV ranked
    by area and a Sentinel-2 chip for the largest --chips candidates."""
    import ee
    lat, lon = args.chip
    box = ee.Geometry.Point([lon, lat]).buffer(args.half).bounds()
    orb = dominant_orbit(s1(box, f"{args.early}-01-01", f"{args.late}-12-31"))
    def med(y):
        return s1(box, f"{y}-01-01", f"{y}-12-31").filter(ee.Filter.eq("relativeOrbitNumber_start", orb)).select("VV").median()
    early, late = med(args.early), med(args.late)
    diff = late.subtract(early).focal_median(1, "square", "pixels")
    mask = diff.gte(args.min_db).And(late.gte(args.min_vv)).selfMask()
    blobs = mask.reduceToVectors(reducer=ee.Reducer.countEvery(), geometry=box, scale=20, geometryType="polygon",
                                 eightConnected=True, labelProperty="lab", bestEffort=True, maxPixels=1e9)
    blobs = blobs.filter(ee.Filter.gte("count", args.min_px))
    stats = ee.Image.cat([early.rename("early"), late.rename("late"), diff.rename("diff")]).reduceRegions(blobs, ee.Reducer.mean(), 20)
    stats = stats.map(lambda f: f.set("lat", f.geometry().centroid(1).coordinates().get(1), "lon", f.geometry().centroid(1).coordinates().get(0)))
    feats = stats.sort("count", False).limit(args.limit).getInfo()["features"]
    rows = [dict(rank=i + 1, lat=round(f["properties"]["lat"], 5), lon=round(f["properties"]["lon"], 5), area_ha=round(0.04 * f["properties"]["count"], 1),
                 early_db=round(f["properties"]["early"], 1), late_db=round(f["properties"]["late"], 1), rise_db=round(f["properties"]["diff"], 1))
            for i, f in enumerate(feats)]
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{args.out}_candidates.csv", index=False)
    print(f"{len(df)} candidates (VV rise >= {args.min_db} dB, late VV >= {args.min_vv} dB, >= {0.04 * args.min_px:.1f} ha) in a {2 * args.half / 1000:.0f} km box at {lat},{lon}; orbit {orb}")
    print(df.head(30).to_string(index=False))
    def s2med(y, region):
        def mask_(img):
            scl = img.select("SCL")
            return img.updateMask(scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(0)))
        return (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate(f"{y}-01-01", f"{y}-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80)).map(mask_).median().select(["B4", "B3", "B2"]).multiply(1e-4))
    for r in rows[:args.chips]:
        reg = ee.Geometry.Point([r["lon"], r["lat"]]).buffer(600).bounds()
        url = s2med(args.late, reg).visualize(min=0, max=0.3).getThumbURL({"region": reg, "dimensions": 400, "format": "png"})
        p = f"{args.out}_cand{r['rank']:02d}.png"
        open(p, "wb").write(requests.get(url, timeout=300).content)
    print(f"wrote {min(len(rows), args.chips)} candidate chips to {args.out}_candNN.png", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("polygons", nargs="?")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--chip", nargs=2, type=float, metavar=("LAT", "LON"))
    ap.add_argument("--half", type=int, default=5000)
    ap.add_argument("--early", type=int, default=2021)
    ap.add_argument("--late", type=int, default=2026)
    ap.add_argument("--candidates", action="store_true", help="with --chip: list new-structure candidates in the box")
    ap.add_argument("--min-db", type=float, default=4.0)
    ap.add_argument("--min-vv", type=float, default=-8.0)
    ap.add_argument("--min-px", type=int, default=25)
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--chips", type=int, default=12)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT") or None)
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    if args.chip and args.candidates:
        candidates(args)
    elif args.chip:
        chips(args)
    elif args.polygons:
        timeline(args)
    else:
        sys.exit("give a polygons file or --chip LAT LON")


if __name__ == "__main__":
    main()
