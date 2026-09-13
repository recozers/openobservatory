"""Null distribution for the NO2 plume test (phase 2, C4): run the test at places with no data-centre start, using an
arbitrary change date, and report the spread of z-scores. Places: the nine control roofs in data/sites.csv and a sample
of the national industrial blobs (results_ntl/scan_china_hubs_band.csv, which lit up for unrelated reasons).

    EE_PROJECT=<project> python tools/plume_null.py --change 2024-07-01 --blobs 12 --workers 3 --out results_no2/plume_null.csv
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.plume_batch import zscore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--change", default="2024-07-01")
    ap.add_argument("--blobs", type=int, default=12)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default="results_no2/plume_null.csv")
    args = ap.parse_args()
    sites = pd.read_csv("data/sites.csv")
    places = [(r.site_id, float(r.lat), float(r.lon)) for _, r in sites[sites.site_id.str.startswith("ctrl_")].iterrows()]
    blobs = pd.read_csv("results_ntl/scan_china_hubs_band.csv").sort_values("sum_diff", ascending=False)
    blobs = blobs.iloc[::max(1, len(blobs) // args.blobs)].head(args.blobs)
    places += [(f"null_blob_{i + 1:02d}", float(b.lat), float(b.lon)) for i, (_, b) in enumerate(blobs.iterrows())]
    start = (pd.Timestamp(args.change) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    Path("logs_pilot").mkdir(exist_ok=True)

    def run(p):
        name, lat, lon = p
        out = Path(f"results_no2/null_{name}.csv")
        if not out.exists():
            cmd = [sys.executable, "tools/no2_plume_test.py", "--lat", str(lat), "--lon", str(lon), "--name", name, "--start", start,
                   "--change", args.change, "--control", f"{lat},{lon + 0.35}", "--control", f"{lat},{lon - 0.35}", "--out", str(out)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            Path(f"logs_pilot/plume_{name}.log").write_text(r.stdout + r.stderr)
        d, z, na, nb = zscore(out, args.change) if out.exists() else (None, None, None, None)
        print(f"  {name:22s} z={z}", file=sys.stderr, flush=True)
        return dict(name=name, lat=lat, lon=lon, change=args.change, change_umol=d, z=z, n_after=na, n_before=nb)

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for f in as_completed([ex.submit(run, p) for p in places]):
            rows.append(f.result())
            pd.DataFrame(rows).to_csv(args.out, index=False)
    df = pd.DataFrame(rows).dropna(subset=["z"])
    print(df.sort_values("z", ascending=False).to_string(index=False))
    z = df.z.to_numpy()
    print(f"\nnull z: n={len(z)}, mean {z.mean():.2f}, sd {z.std(ddof=1):.2f}, 95th pct {np.quantile(z, .95):.2f}, max {z.max():.2f}; share >= 2.5: {(z >= 2.5).mean():.2f}")


if __name__ == "__main__":
    main()
