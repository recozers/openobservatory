#!/usr/bin/env python
"""Render before/after Sentinel-2 chips for the radar-detected structures under review (RFW-01).

For every inventory entry with coords_quality radar_candidate (or the ids given), reads the least cloudy Sentinel-2 L2A
true-colour scene in two summers from the public AWS `sentinel-cogs` bucket (no credentials), draws the entry's radar
outline from data/polygons/<site_id>.geojson in red and every other polygon in the view in yellow (other radar entries)
or cyan (digitised campuses), and writes one side-by-side PNG per entry, early year on the left and late year on the right.

    python tools/radar_review_chips.py --out results_cn/radar_review [--ids cn_horinger_r15 ...] [--half 700] [--scale 4]

The chips are the evidence paths recorded in data/cn_radar_review.csv. Scene ids are printed and written to
<out>/scenes.csv so a reviewer can fetch the same pixels.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chip  # noqa: E402  (tools/chip.py: list_scenes, read_window, BUCKET, CLOUDY)
import mgrs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUMMER = ["06", "07", "08", "09"]
ALL_MONTHS = [f"{m:02d}" for m in range(1, 13)]


def best_scene(lat, lon, half, year, months, max_scenes, cloud_ok=0.05):
    m = mgrs.MGRS()
    tile = m.toMGRS(lat, lon, MGRSPrecision=0)
    zone, band, sq = tile[:2], tile[2], tile[3:5]
    scenes = chip.list_scenes(zone, band, sq, [f"{year}-{mm}" for mm in months])
    if not scenes:
        return None
    scenes = scenes[-max_scenes:]
    best = None
    for sc in scenes:
        scl, _, _ = chip.read_window(f"{chip.BUCKET}/{sc}/SCL.tif", lon, lat, half)
        cf = float(np.isin(scl[0], list(chip.CLOUDY)).mean())
        if best is None or cf < best[1]:
            best = (sc, cf)
        if cf < cloud_ok:
            break
    return best


def render(lat, lon, half, scene, scale, outlines):
    tci, win_tr, crs = chip.read_window(f"{chip.BUCKET}/{scene}/TCI.tif", lon, lat, half)
    rgb = np.moveaxis(tci, 0, -1).astype(np.uint8)
    mask = rgb.sum(axis=2) > 0
    lo, hi = np.percentile(rgb[mask], [1, 99]) if mask.any() else (0, 255)
    rgb = np.clip((rgb.astype(float) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb).resize((rgb.shape[1] * scale, rgb.shape[0] * scale), Image.NEAREST)
    draw = ImageDraw.Draw(img)
    tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    inv = ~win_tr
    for geom, colour, width in outlines:
        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for p in polys:
            pts = []
            for x, y in p.exterior.coords:
                px, py = tr.transform(x, y)
                c, r = inv * (px, py)
                pts.append((c * scale, r * scale))
            draw.line(pts, fill=colour, width=width)
    # 250 m scale bar
    px_per_m = scale / 10.0
    x0, y0 = 8, img.size[1] - 14
    draw.line([(x0, y0), (x0 + 250 * px_per_m, y0)], fill=(255, 255, 255), width=3)
    draw.text((x0, y0 - 12), "250 m", fill=(255, 255, 255))
    draw.text((x0, 4), scene.split("/")[-1], fill=(255, 255, 0))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results_cn/radar_review")
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--half", type=float, default=700, help="half-size of each panel in metres")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--early", type=int, default=2021)
    ap.add_argument("--late", type=int, default=2026)
    ap.add_argument("--max-scenes", type=int, default=5)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    sites = list(csv.DictReader(open(ROOT / "data" / "sites.csv")))
    todo = [s for s in sites if s["coords_quality"] == "radar_candidate" and (not args.ids or s["site_id"] in args.ids)]
    if args.ids:
        have = {s["site_id"] for s in todo}
        for sid in args.ids:
            if sid not in have:
                todo.append(next(s for s in sites if s["site_id"] == sid))
    # every polygon we can draw, for context
    polys = {}
    for s in sites:
        p = ROOT / "data" / "polygons" / f"{s['site_id']}.geojson"
        if s["country"] == "CN" and p.exists():
            gj = json.load(open(p))
            polys[s["site_id"]] = (s["coords_quality"], [shape(f["geometry"]) for f in gj["features"]])

    scenes_path = out / "scenes.csv"
    rows = {r["site_id"]: r for r in csv.DictReader(open(scenes_path))} if scenes_path.exists() else {}
    for s in todo:
        sid = s["site_id"]
        png = out / f"{sid}.png"
        if png.exists() and not args.overwrite:
            print(sid, "exists"); continue
        lat, lon = float(s["lat"]), float(s["lon"])
        outlines = []
        for oid, (q, geoms) in polys.items():
            colour = (255, 40, 40) if oid == sid else ((255, 230, 0) if q == "radar_candidate" else (0, 230, 255))
            for g in geoms:
                outlines.append((g, colour, 3 if oid == sid else 1))
        panels, rec = [], {"site_id": sid}
        for label, year in (("early", args.early), ("late", args.late)):
            best = best_scene(lat, lon, args.half, year, SUMMER, args.max_scenes)
            if best is None or best[1] > 0.3:
                alt = best_scene(lat, lon, args.half, year, ALL_MONTHS, args.max_scenes * 3)
                if alt is not None and (best is None or alt[1] < best[1]):
                    best = alt
            if best is None:
                print(sid, label, "no scene"); rec[f"{label}_scene"], rec[f"{label}_cloud"] = "", ""; continue
            sc, cf = best
            print(f"{sid} {label}: {sc.split('/')[-1]} cloudy {cf:.2f}")
            rec[f"{label}_scene"], rec[f"{label}_cloud"] = sc.split("/")[-1], f"{cf:.2f}"
            panels.append(render(lat, lon, args.half, sc, args.scale, outlines))
        if not panels:
            continue
        w = sum(p.size[0] for p in panels) + 8 * (len(panels) - 1)
        h = max(p.size[1] for p in panels) + 16
        canvas = Image.new("RGB", (w, h), (30, 30, 30))
        x = 0
        for p in panels:
            canvas.paste(p, (x, 16)); x += p.size[0] + 8
        d = ImageDraw.Draw(canvas)
        d.text((4, 2), f"{sid}  {s['name']}  centre {lat:.5f},{lon:.5f}  red = this entry's radar outline, yellow = other radar entries, cyan = digitised campus", fill=(255, 255, 255))
        canvas.save(png)
        rows[sid] = rec
        with open(scenes_path, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["site_id", "early_scene", "early_cloud", "late_scene", "late_cloud"])
            wr.writeheader()
            for r in rows.values():
                wr.writerow({k: r.get(k, "") for k in wr.fieldnames})
        print("wrote", png)


if __name__ == "__main__":
    main()
