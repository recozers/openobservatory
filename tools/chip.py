#!/usr/bin/env python
"""Render a Sentinel-2 true-colour chip around a point, for verifying site
coordinates and hand-digitising polygons.

Reads windowed data from the public `sentinel-cogs` bucket (AWS Open Data,
no credentials needed).  Picks the least cloudy scene in the requested months
using the SCL band, then writes a PNG with a metre grid centred on the point.

Usage:
    python tools/chip.py --lat 40.428 --lon -111.934 --half 1500 \
        --months 2021-06 2021-07 2021-08 --out chips/nsa_utah.png
"""
import argparse
import os
import re
import sys

import numpy as np
import rasterio
import requests
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from rasterio.windows import Window

import mgrs

BUCKET = "https://sentinel-cogs.s3.us-west-2.amazonaws.com"
# SCL classes: 0 nodata, 1 saturated, 2 dark, 3 cloud shadow, 4 veg, 5 bare,
# 6 water, 7 unclassified, 8 cloud medium, 9 cloud high, 10 cirrus, 11 snow
CLOUDY = {0, 1, 3, 8, 9, 10}

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")


def list_scenes(zone, band, sq, months):
    scenes = []
    for ym in months:
        y, m = ym.split("-")
        prefix = f"sentinel-s2-l2a-cogs/{int(zone)}/{band}/{sq}/{int(y)}/{int(m)}/"
        token = None
        while True:
            params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
            if token:
                params["continuation-token"] = token
            r = requests.get(BUCKET + "/", params=params, timeout=60)
            r.raise_for_status()
            keys = re.findall(r"<Key>(.*?)</Key>", r.text)
            scenes += [k for k in keys if k.endswith("/TCI.tif")]
            m2 = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r.text)
            if not m2:
                break
            token = m2.group(1)
    return sorted(set(s.rsplit("/", 1)[0] for s in scenes))


def read_window(url, lon, lat, half_m):
    with rasterio.open("/vsicurl/" + url) as ds:
        tr = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
        x, y = tr.transform(lon, lat)
        r, c = ds.index(x, y)
        n = int(round(half_m / ds.res[0]))
        w = Window(c - n, r - n, 2 * n, 2 * n)
        arr = ds.read(window=w, boundless=True, fill_value=0)
        win_tr = ds.window_transform(w)
        return arr, win_tr, ds.crs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--half", type=float, default=1500, help="half-size of chip in metres")
    ap.add_argument("--months", nargs="+", default=["2021-06", "2021-07", "2021-08"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=3, help="upsampling factor for viewing")
    ap.add_argument("--grid", type=float, default=250, help="grid spacing in metres")
    ap.add_argument("--max-scenes", type=int, default=6)
    ap.add_argument("--scene", default=None, help="use this scene prefix instead of searching")
    args = ap.parse_args()

    m = mgrs.MGRS()
    tile = m.toMGRS(args.lat, args.lon, MGRSPrecision=0)
    zone, band, sq = tile[:2], tile[2], tile[3:5]

    if args.scene:
        candidates = [args.scene]
    else:
        candidates = list_scenes(zone, band, sq, args.months)
        if not candidates:
            sys.exit(f"no scenes for tile {tile} in {args.months}")
        candidates = candidates[-args.max_scenes:]  # newest few

    best = None
    for sc in candidates:
        scl, _, _ = read_window(f"{BUCKET}/{sc}/SCL.tif", args.lon, args.lat, args.half)
        cf = float(np.isin(scl[0], list(CLOUDY)).mean())
        print(f"{sc.split('/')[-1]}: cloudy fraction {cf:.2f}")
        if best is None or cf < best[1]:
            best = (sc, cf)
        if cf < 0.02:
            break
    sc, cf = best
    print("using", sc, "cloudy", round(cf, 3))
    tci, win_tr, crs = read_window(f"{BUCKET}/{sc}/TCI.tif", args.lon, args.lat, args.half)
    rgb = np.moveaxis(tci, 0, -1).astype(np.uint8)
    # simple stretch for viewing
    lo, hi = np.percentile(rgb[rgb.sum(axis=2) > 0], [1, 99]) if (rgb.sum(axis=2) > 0).any() else (0, 255)
    rgb = np.clip((rgb.astype(float) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)

    img = Image.fromarray(rgb).resize((rgb.shape[1] * args.scale, rgb.shape[0] * args.scale), Image.NEAREST)
    draw = ImageDraw.Draw(img)
    px_per_m = args.scale / 10.0
    cx, cy = img.size[0] / 2, img.size[1] / 2
    # grid lines every args.grid metres, labelled as metre offsets from centre
    k = int(args.half // args.grid)
    for i in range(-k, k + 1):
        off = i * args.grid * px_per_m
        col = (255, 255, 0) if i == 0 else (255, 255, 255)
        draw.line([(cx + off, 0), (cx + off, img.size[1])], fill=col, width=1)
        draw.line([(0, cy - off), (img.size[0], cy - off)], fill=col, width=1)
        draw.text((cx + off + 2, 2), f"{int(i*args.grid):+d}", fill=(255, 255, 0))
        draw.text((2, cy - off + 2), f"{int(i*args.grid):+d}", fill=(255, 255, 0))
    draw.text((4, img.size[1] - 14), f"{sc.split('/')[-1]} centre {args.lat:.5f},{args.lon:.5f} E=+x N=+y (m)", fill=(255, 255, 0))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img.save(args.out)
    print("wrote", args.out, "crs", crs, "transform", win_tr)


if __name__ == "__main__":
    main()
