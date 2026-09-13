"""Second stage of the automatic detection chain: for the brightest new-lit blobs from a night-lights scan, run the
Sentinel-1 candidate scan around each and keep the ones with a new structure of at least --min-area ha.

    EE_PROJECT=<project> python tools/lights_to_radar.py --scan results_ntl/scan_china_hubs.csv --top 40 \
        --max-early 30 --half 4000 --early 2022 --late 2026 --out results_s1/china

Blobs whose early radiance already exceeds --max-early nW/cm^2/sr are skipped (city growth, not a new site). Each blob's
radar run writes results_s1/<out>/blobNN_candidates.csv and chips; the summary CSV lists, per blob, the largest new
structure (ha), the number of structures >= --min-area, and its coordinates, ranked by that largest structure.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", required=True)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--max-early", type=float, default=30.0)
    ap.add_argument("--half", type=int, default=4000)
    ap.add_argument("--early", type=int, default=2022)
    ap.add_argument("--late", type=int, default=2026)
    ap.add_argument("--min-area", type=float, default=5.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    scan = pd.read_csv(args.scan)
    scan = scan[scan.early <= args.max_early].sort_values("sum_diff", ascending=False).head(args.top).reset_index(drop=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, b in scan.iterrows():
        tag = out / f"blob{i + 1:02d}"
        cf = Path(f"{tag}_candidates.csv")
        if not cf.exists():  # reuse a finished blob on relaunch
            cmd = [sys.executable, "tools/s1_timeline.py", "--chip", str(b.lat), str(b.lon), "--candidates", "--half", str(args.half),
                   "--early", str(args.early), "--late", str(args.late), "--chips", "4", "--out", str(tag)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0 or not cf.exists():
                print(f"  blob {i + 1} at {b.lat},{b.lon}: radar stage failed: {r.stderr.strip()[-120:]}", file=sys.stderr)
                rows.append(dict(blob=i + 1, lat=b.lat, lon=b.lon, lit_early=b["early"], lit_late=b["late"], lit_diff=b["diff"], lit_px=b["n_px"], largest_ha=None, n_big=None, cand_lat=None, cand_lon=None))
                continue
        try:
            c = pd.read_csv(cf)
        except pd.errors.EmptyDataError:  # written before the columns fix: no candidates
            c = pd.DataFrame(columns=["rank", "lat", "lon", "area_ha", "early_db", "late_db", "rise_db"])
        big = c[c.area_ha >= args.min_area]
        top = c.iloc[0] if len(c) else None
        rows.append(dict(blob=i + 1, lat=b.lat, lon=b.lon, lit_early=b["early"], lit_late=b["late"], lit_diff=b["diff"], lit_px=b["n_px"],
                         largest_ha=float(top.area_ha) if top is not None else 0.0, n_big=int(len(big)),
                         cand_lat=float(top.lat) if top is not None else None, cand_lon=float(top.lon) if top is not None else None))
        lit = float(b["diff"])
        print(f"  blob {i + 1} at {b.lat},{b.lon}: lights +{lit:.0f}, largest new structure {rows[-1]['largest_ha']:.1f} ha, {len(big)} >= {args.min_area} ha", file=sys.stderr)
    df = pd.DataFrame(rows).sort_values("largest_ha", ascending=False, na_position="last")
    df.to_csv(out / "summary.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
