"""Refresh permit-located generator watches; screen changes, never infer campus MW.

--live fetches the latest three complete months using noninteractive EE credentials.
Without it, replay the saved profiles. Pre-cut baseline observations stay frozen.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from no2_flux_quarterly import plateau_series, NOX_NO2, MW_NO2


def registry(root=ROOT):
    with (root / "data/generator_watchlist.csv").open() as f:
        rows = list(csv.DictReader(f))
    ids = [r["watch_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate generator watch")
    for r in rows:
        if r["status"] != "watching":
            continue
        if not r["site_id"] or not r["coordinate_url"].startswith("https://") or not r["target_url"].startswith("https://"):
            raise ValueError("Active watch needs site, coordinate and target sources")
        if not (-90 <= float(r["lat"]) <= 90 and -180 <= float(r["lon"]) <= 180):
            raise ValueError("Invalid watch coordinates")
        pd.Timestamp(r["baseline_before"])
    active = {r["site_id"]: r for r in rows if r["status"] == "watching"}
    with (root / "data/sites.csv").open() as f:
        sites = {s["site_id"]: s for s in csv.DictReader(f)}
    with (root / "data/refresh_flux_sources.csv").open() as f:
        sources = {s["site_id"]: s for s in csv.DictReader(f) if s.get("refresh_mode") == "generator_watch"}
    if set(active) != set(sources):
        raise ValueError("Active watches and refresh registrations disagree")
    for sid, row in active.items():
        site, source = sites[sid], sources[sid]
        if (site["site_class"] != "generator_planned" or site["lat"] != row["lat"] or site["lon"] != row["lon"]
                or source["baseline_before"] != row["baseline_before"]
                or source["profile"] != f"results_no2/generator_watch/{sid}.csv"):
            raise ValueError(f"Inconsistent generator watch registration: {sid}")
    return rows


def monthly_frame(s, cut, cal, today=None):
    """Seasonal change with sampling, baseline and shared calibration uncertainty.

    Baseline months themselves are not tests. Require >=3 daily samples on each
    side and omit the incomplete calendar month. Negative estimates stay signed.
    """
    cut = pd.Timestamp(cut)
    end = pd.Timestamp(today or pd.Timestamp.now().date()).to_period("M").start_time
    base = s[s.index < cut].groupby(s[s.index < cut].index.month).agg(["mean", "std", "count"])
    post = s[(s.index >= cut) & (s.index < end)].resample("ME").agg(["mean", "std", "count"])
    b = base.reindex(post.index.month).set_axis(post.index)
    valid = (post["count"] >= 3) & (b["count"] >= 3)
    post, b = post[valid], b[valid]
    factor = NOX_NO2 * MW_NO2 * 3600 * cal["factor"]
    rate = (post["mean"] - b["mean"]) * factor
    sampling = post["std"] / np.sqrt(post["count"]) * factor
    baseline = b["std"] / np.sqrt(b["count"]) * factor
    se = np.sqrt(sampling ** 2 + baseline ** 2 + (rate.abs() * cal["scatter"] / cal["factor"]) ** 2)
    frame = pd.DataFrame(dict(nox_kgh_cal=rate, nox_se=se, n_days=post["count"],
                             baseline_days=b["count"], baseline_se=baseline))
    frame.index = frame.index.strftime("%Y-%m")
    frame.index.name = "month"
    return frame


def crossings(frame):
    rate = pd.to_numeric(frame.nox_kgh_cal, errors="coerce")
    error = pd.to_numeric(frame.nox_se, errors="coerce")
    days = pd.to_numeric(frame.n_days, errors="coerce")
    valid = np.isfinite(rate) & np.isfinite(error) & (error >= 0) & (days >= 3)
    return frame[valid & (rate > 100) & (rate > 2 * error)]


def refresh_profile(row, root, fetch, today=None):
    """Requery a three-month overlap, preserving earlier and baseline profiles."""
    folder = root / "results_no2/generator_watch"
    path = folder / f"{row['site_id']}.csv"
    metadata = folder / f"{row['site_id']}_extraction.json"
    if metadata.exists():
        previous = json.loads(metadata.read_text())
        if any(float(previous[k]) != float(row[k]) for k in ("lat", "lon")) or previous["start"] != row["profile_start"]:
            raise ValueError("Watch geometry or extraction start changed; rebuild the baseline explicitly")
    end = pd.Timestamp(today or pd.Timestamp.now().date()).to_period("M").start_time - pd.Timedelta(days=1)
    start = max(pd.Timestamp(row["baseline_before"]), end.to_period("M").start_time - pd.DateOffset(months=2)) if path.exists() else pd.Timestamp(row["profile_start"])
    old = pd.read_csv(path, index_col=0) if path.exists() else pd.DataFrame()
    fresh = fetch(row, pd.date_range(start, end))
    fresh.index = pd.to_datetime(fresh.index).strftime("%Y-%m-%d")
    fresh.columns = fresh.columns.map(str)
    retained = old[old.index < start.strftime("%Y-%m-%d")] if not old.empty else old
    combined = pd.concat([retained, fresh])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    folder.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    combined.to_csv(temporary)
    temporary.replace(path)
    metadata.write_text(json.dumps(dict(
        start=row["profile_start"], through=end.strftime("%Y-%m-%d"),
        lat=float(row["lat"]), lon=float(row["lon"]), half_width_km=12, max_cloud=0.3,
        wind_utc="19:00–21:00", source="COPERNICUS/S5P/OFFL/L3_NO2; ECMWF/ERA5/HOURLY"), indent=2) + "\n")


def live_fetch(row, days):
    from dcheat.gee import _ee
    from no2_flux import daily_profiles
    # Never initiate interactive authentication in a scheduled or CLI watch job.
    os.environ["CI"] = "true"
    ee = _ee()
    ee.data.setDeadline(int(os.getenv("EE_DEADLINE_MS", "180000")))
    return daily_profiles(ee, row["site_id"], float(row["lat"]), float(row["lon"]),
                          days, list(range(-12000, 30001, 2000)), 12000, 0.3)


def run(root=ROOT, live=False, today=None):
    rows = registry(root)
    folder = root / "results_no2/generator_watch"
    folder.mkdir(parents=True, exist_ok=True)
    calpath = root / "results_no2/calibration_plateau.json"
    cal = json.loads(calpath.read_text())
    audit = []
    events_path = folder / "detections.csv"
    events = list(csv.DictReader(events_path.open())) if events_path.exists() else []
    for row in rows:
        if row["status"] != "watching":
            continue
        sid = row["site_id"]
        path = folder / f"{sid}.csv"
        if live:
            refresh_profile(row, root, live_fetch, today)
        frame = monthly_frame(plateau_series(path), row["baseline_before"], cal, today)
        # Retain full precision so the displayed colour and audit use one threshold.
        frame.to_csv(root / f"results_no2/flux_{sid}_monthly.csv", float_format="%.17g")
        frame = pd.read_csv(root / f"results_no2/flux_{sid}_monthly.csv", index_col=0)
        hits = crossings(frame)
        first = str(hits.index[0]) if len(hits) else None
        audit.append(dict(site_id=sid, months=len(frame), threshold_months=list(hits.index),
                          first_threshold_month=first, baseline_before=row["baseline_before"],
                          baseline_is="analysis cutoff, not a first-fire date", scope="regional NOx change; fleet attribution unconfirmed",
                          calibration_sha256=hashlib.sha256(calpath.read_bytes()).hexdigest(),
                          profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if first and not any(e["site_id"] == sid for e in events):
            events.append(dict(site_id=sid, month=first, recorded_on=str(today or pd.Timestamp.now().date()),
                               nox_kgh_cal=str(frame.loc[first, "nox_kgh_cal"]), nox_se=str(frame.loc[first, "nox_se"])))
            with (root / "docs/LOG.md").open("a") as log:
                log.write(f"\n\n### Generator watch threshold: {sid}, {first}\n\n"
                          f"First monthly seasonal-change screen above 2σ and 100 kg NOx/h: "
                          f"{frame.loc[first, 'nox_kgh_cal']:.1f} ± {frame.loc[first, 'nox_se']:.1f} kg/h. "
                          "Automatic regional NOx screen; source attribution and first fire remain unverified. "
                          "No generation or campus MW inferred. See results_no2/generator_watch/audit.json.\n")
        print(f"{sid}: {len(frame)} months, {len(hits)} threshold crossings", file=sys.stderr)
    with events_path.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=["site_id", "month", "recorded_on", "nox_kgh_cal", "nox_se"])
        writer.writeheader()
        writer.writerows(events)
    (folder / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")


def public_status(root, site):
    watch = site["generator_watch"]
    path = root / f"results_no2/flux_{site['site_id']}_monthly.csv"
    frame = pd.read_csv(path, index_col=0)
    hits = crossings(frame)
    first = str(hits.index[0]) if len(hits) else None
    return dict(
        built="filing-located generator monitoring point; hall geometry not mapped", built_conf="medium",
        running=(f"NOx change measured: watch threshold crossed in {first}; fleet attribution unconfirmed" if first
                 else "watching: generator fleet under construction"),
        load="unknown: no two-sided operating emission factor or measured campus load",
        confidence="low", key="generator_watch", combustion=False, est_mid=None, est_hi=0,
        evidence_kind="measured" if first else "construction", first_threshold_month=first,
        series=[dict(x=str(i), y=float(r.nox_kgh_cal), se=float(r.nox_se)) for i, r in frame.iterrows()],
        series_label="Monthly NOx change from seasonal baseline, kg/h (±1σ)",
        sources=[dict(label="Permit / siting location", url=watch["coordinate_url"]),
                 dict(label="First-power target", url=watch["target_url"])],
        recent=f"latest complete observation: {frame.index[-1]}" if len(frame) else "no qualifying monthly observations",
        how=[f"Target: {watch['first_power_target']} ({watch['target_kind']}); first fire unverified",
             f"Permit: {watch['permit_id']}; {watch['nox_limit']}",
             "TROPOMI calibrated seasonal change including baseline uncertainty; 2σ and >100 kg/h screening threshold",
             "Regional plume and repeated-testing uncertainty; source attribution requires follow-up"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true")
    run(live=ap.parse_args().live)
