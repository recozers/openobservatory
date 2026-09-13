"""Tiled night-lights change scan over a large region (a province or a country), merging per-tile results.

    EE_PROJECT=<project> python tools/ntl_scan_tiles.py --box 24.0 97.0 45.0 125.0 --tile 2.0 --name china_east \
        --out results_ntl/scan_china_east.csv

Each --tile-degree tile is scanned with tools/ntl_scan.scan_box (3-month VIIRS medians, latest vs 3 years earlier),
with retries on Earth Engine quota errors; results are concatenated and ranked by summed brightening. The output is
a candidate list for the radar stage (tools/s1_timeline.py --candidates) and then an optical chip.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ntl_scan import latest_month, scan_box  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", nargs=4, type=float, required=True, metavar=("LAT_S", "LON_W", "LAT_N", "LON_E"))
    ap.add_argument("--tile", type=float, default=2.0)
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
    s0, w0, n0, e0 = args.box
    late_ym = args.late or latest_month()
    parts = []
    lats = np.arange(s0, n0, args.tile)
    lons = np.arange(w0, e0, args.tile)
    total = len(lats) * len(lons)
    k = 0
    for s in lats:
        for w in lons:
            k += 1
            n, e = min(s + args.tile, n0), min(w + args.tile, e0)
            tname = f"{s:.1f}_{w:.1f}"
            for attempt in range(5):
                try:
                    df, lw, ew = scan_box(float(s), float(w), float(n), float(e), late_ym, args.years_back, args.min_diff, args.min_ratio, args.min_px, args.limit, tname)
                    break
                except Exception as ex:
                    if attempt == 4:
                        print(f"  tile {tname} failed: {str(ex)[:100]}", file=sys.stderr)
                        df = None
                        break
                    print(f"  tile {tname} retry {attempt + 1}: {str(ex)[:80]}", file=sys.stderr)
                    time.sleep(60)
            if df is not None:
                parts.append(df)
                print(f"  [{k}/{total}] tile {tname}: {len(df)} blobs", file=sys.stderr)
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(out):
        out = out.sort_values("sum_diff", ascending=False).reset_index(drop=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"{args.name}: {len(out)} blobs over {total} tiles; late window ends {late_ym}, early {args.years_back} years before")
    print(out.head(40).to_string(index=False))


if __name__ == "__main__":
    main()
