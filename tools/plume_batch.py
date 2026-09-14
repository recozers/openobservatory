"""Batch NO2 plume test over every inventory site with a documented start date (C1 in docs/PHASE2_TODO.md).

    EE_PROJECT=<project> python tools/plume_batch.py [--min-mw 50] [--limit 80]

For each non-control site: change date = start of the first quarter with a positive documented capacity in
site/data/timeline/<site>.json, else the first roof date plus six months; controls = two points 0.35 degrees east and west.
Runs tools/no2_plume_test.py with --start two years before the change date into results_no2/<site>.csv (which build_status.py reads), skipping
sites that already have a file, and writes results_no2/plume_batch_summary.csv with the downwind-minus-upwind change and
its z-score computed as build_status.py does. Sites are processed in descending documented capacity.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def change_date(sid):
    tj = Path(f"site/data/timeline/{sid}.json")
    if not tj.exists():
        return None, None
    t = json.load(open(tj))
    q = next((q for q in t.get("quarters", []) if (q.get("cap_doc_mw") or 0) > 0), None)
    if q:
        return pd.Period(q["q"], freq="Q").start_time.strftime("%Y-%m-%d"), "documented capacity"
    dated = sorted(str(v)[:7] for v in t.get("roof_on", {}).values() if str(v)[:4].isdigit())
    if dated:
        return (pd.Period(dated[0], freq="M") + 6).strftime("%Y-%m-01"), "first roof + 6 months"
    return None, None


def zscore(csv, change, series=None):
    """Downwind-minus-upwind change after `change`, for one series. Output files hold the site and its control points in the
    `site` column; `series` selects one (default: the file's own site, taken from its name). Mixing them dilutes the site."""
    try:
        n2 = pd.read_csv(csv, index_col=0)
        name = series or Path(csv).stem.replace("null_", "")
        if "site" in n2.columns:
            n2 = n2[n2.site == name]
        n2.index = pd.to_datetime(n2.index)
        cut = pd.Timestamp(change)
        a, b = n2[n2.index >= cut].dw_minus_uw.dropna(), n2[n2.index < cut].dw_minus_uw.dropna()
        if len(a) > 10 and len(b) > 10:
            z = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
            return round(float(a.mean() - b.mean()), 3), round(float(z), 2), len(a), len(b)
    except Exception:
        pass
    return None, None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-mw", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    sites = pd.read_csv("data/sites.csv")
    sites = sites[~sites.site_id.str.startswith("ctrl_")].copy()
    sites["cap"] = pd.to_numeric(sites.capacity_mw, errors="coerce").fillna(0)
    sites = sites[sites.cap >= args.min_mw].sort_values("cap", ascending=False).head(args.limit)
    summ = Path("results_no2/plume_batch_summary.csv")
    Path("logs_pilot").mkdir(exist_ok=True)
    jobs, rows = [], []
    for _, s in sites.iterrows():
        sid = s.site_id
        change, basis = change_date(sid)
        if not change or change < "2019-07-01" or change > "2026-06-01":
            rows.append(dict(site_id=sid, cap_mw=s.cap, change=change, basis=basis, status="skipped: start not in mid-2019..mid-2026"))
            continue
        jobs.append((sid, float(s.cap), float(s.lat), float(s.lon), change, basis))

    def run(job):
        sid, cap, lat, lon, change, basis = job
        out = Path(f"results_no2/{sid}.csv")
        if out.exists():
            status = "existing file"
        else:
            start = (pd.Timestamp(change) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
            cmd = [sys.executable, "tools/no2_plume_test.py", "--lat", str(lat), "--lon", str(lon), "--name", sid, "--start", max(start, "2018-07-01"),
                   "--change", change, "--control", f"{lat},{lon + 0.35}", "--control", f"{lat},{lon - 0.35}", "--out", str(out)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            Path(f"logs_pilot/plume_{sid}.log").write_text(r.stdout + r.stderr)
            status = "ok" if r.returncode == 0 and out.exists() else "failed: " + r.stderr.strip()[-120:].replace("\n", " ")
        d, z, na, nb = zscore(out, change) if out.exists() else (None, None, None, None)
        print(f"  {sid:34s} {cap:7.0f} MW  change {change} ({basis})  z={z}  {status[:40]}", file=sys.stderr, flush=True)
        return dict(site_id=sid, cap_mw=cap, change=change, basis=basis, status=status, change_umol=d, z=z, n_after=na, n_before=nb)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run, j) for j in jobs]
        for f in as_completed(futs):
            rows.append(f.result())
            pd.DataFrame(rows).to_csv(summ, index=False)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
