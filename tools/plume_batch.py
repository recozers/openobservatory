"""Batch NO2 plume test over every inventory site with a documented start date (C1 in docs/PHASE2_TODO.md).

    EE_PROJECT=<project> python tools/plume_batch.py [--min-mw 50] [--limit 80]

For each non-control site: change date = start of the first quarter with a positive documented capacity in
site/data/timeline/<site>.json, else the first roof date plus six months; controls = two points 0.35 degrees east and west.
Runs tools/no2_plume_test.py with --start two years before the change date into results_no2/<site>.csv (which build_status.py reads), skipping
sites that already have a file, and writes results_no2/plume_batch_summary.csv with the downwind-minus-upwind change and
its z-score computed as build_status.py does. Sites are processed in descending documented capacity.

    python tools/plume_batch.py --sensitivity [--offsets 3] [--out results_no2/plume_date_sensitivity.csv]

RFW-14: re-reads the saved daily series (no Earth Engine) for every site and control point in
results_no2/plume_batch_zscores_by_series.csv and reports two tests at every start date within --offsets months of the
documented one: the current test (`zscore`, all after-days against all before-days) and a season-matched test
(`season_zscore`, after-days against before-days from the same calendar month, combined across months by inverse variance),
so a seasonal NO2 cycle cannot masquerade as a step. Writes one row per series and start date, then prints the
control-point false-positive rate under each test.
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


def _series(csv, series=None):
    n2 = pd.read_csv(csv, index_col=0)
    name = series or Path(csv).stem.replace("null_", "")
    if "site" in n2.columns:
        n2 = n2[n2.site == name]
    n2.index = pd.to_datetime(n2.index)
    return pd.to_numeric(n2.dw_minus_uw, errors="coerce").dropna()


def season_zscore(csv, change, series=None, min_days=5):
    """Season-matched downwind-minus-upwind change after `change`: within each calendar month, after-days minus before-days
    of that same month, combined across months by inverse variance (a stratified two-sample z). Months with fewer than
    `min_days` on either side are left out. Returns (change, z, n_after, n_before, n_months) or Nones."""
    try:
        v = _series(csv, series)
        cut = pd.Timestamp(change)
        a_all, b_all = v[v.index >= cut], v[v.index < cut]
        num = den = 0.0
        na = nb = months = 0
        for m in range(1, 13):
            a, b = a_all[a_all.index.month == m], b_all[b_all.index.month == m]
            if len(a) < min_days or len(b) < min_days:
                continue
            var = a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)
            if not np.isfinite(var) or var <= 0:
                continue
            w = 1.0 / var
            num += w * (a.mean() - b.mean())
            den += w
            na += len(a); nb += len(b); months += 1
        if months and na > 10 and nb > 10:
            d = num / den
            return round(float(d), 3), round(float(d * np.sqrt(den)), 2), na, nb, months
    except Exception:
        pass
    return None, None, None, None, None


def sensitivity(by_series="results_no2/plume_batch_zscores_by_series.csv", offsets=3, out="results_no2/plume_date_sensitivity.csv", threshold=2.5):
    """Both tests for every series at start dates within `offsets` months of the documented one."""
    bs = pd.read_csv(by_series)
    rows = []
    for _, r in bs.iterrows():
        csv = Path(f"results_no2/{r.file_site}.csv")
        if not csv.exists():
            continue
        doc = pd.Timestamp(r.change)
        for k in range(-offsets, offsets + 1):
            change = (doc + pd.DateOffset(months=k)).strftime("%Y-%m-%d")
            d0, z0, na0, nb0 = zscore(csv, change, r.series)
            d1, z1, na1, nb1, nm = season_zscore(csv, change, r.series)
            rows.append(dict(file_site=r.file_site, series=r.series, role=r.role, documented=r.change, offset_months=k, change=change,
                             z_current=z0, change_current=d0, n_after=na0, n_before=nb0,
                             z_season=z1, change_season=d1, n_after_season=na1, n_before_season=nb1, n_months=nm))
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    ctrl = df[df.role == "control"]
    at_doc = ctrl[ctrl.offset_months == 0]
    def rate(frame, col):
        v = frame[col].dropna()
        return f"{int((v >= threshold).sum())} of {len(v)} ({(v >= threshold).mean():.1%}), sd {v.std():.2f}, max {v.max():.2f}, min {v.min():.2f}"
    summary = {
        "controls at documented date, current test": rate(at_doc, "z_current"),
        "controls at documented date, season-matched": rate(at_doc, "z_season"),
        "controls, any start date within offsets, current test": rate(ctrl.groupby(["file_site", "series"]).z_current.max().to_frame(), "z_current"),
        "controls, any start date within offsets, season-matched": rate(ctrl.groupby(["file_site", "series"]).z_season.max().to_frame(), "z_season"),
    }
    return df, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensitivity", action="store_true", help="RFW-14: date and season sensitivity from saved series, no Earth Engine")
    ap.add_argument("--offsets", type=int, default=3)
    ap.add_argument("--out", default="results_no2/plume_date_sensitivity.csv")
    ap.add_argument("--min-mw", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if args.sensitivity:
        df, summary = sensitivity(offsets=args.offsets, out=args.out)
        site_rows = df[(df.role == "site")]
        piv = site_rows.pivot_table(index="file_site", columns="offset_months", values=["z_current", "z_season"])
        print(piv.round(2).to_string())
        for k, v in summary.items():
            print(f"{k}: {v}")
        print(f"wrote {args.out} ({len(df)} rows)")
        return
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
