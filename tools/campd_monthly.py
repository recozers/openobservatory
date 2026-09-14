"""CAMPD hourly rates -> calendar-month plant generation; allocation is separately sourced.

python tools/campd_monthly.py                 # replay checked-in hourly files
python tools/campd_monthly.py --fetch         # refresh current and previous years

grossLoad is an operating-hour MW rate: multiply by opTime. noxMass is already
the hourly mass in pounds: do NOT multiply by opTime a second time. Both are
checked against EPA's independently aggregated 2023 Southaven endpoint.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/hourly"
COLUMNS = ["link_id", "oris_id", "month", "gross_mwh", "observed_gross_mwh", "calendar_hours",
           "operating_unit_hours", "reported_unit_hours", "expected_unit_hours", "coverage",
           "gross_avg_mw", "nox_kg", "complete"]


def links(root=ROOT):
    with (root / "data/campus_plant_links.csv").open() as f:
        rows = list(csv.DictReader(f))
    if len({r["link_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate campus/plant link IDs")
    for r in rows:
        if r["contracted_share"] and not 0 <= float(r["contracted_share"]) <= 1:
            raise ValueError("contracted_share must be in [0, 1]")
        if r["allocation_verified"] == "yes" and (not r["source_url"] or not r["from_date"] or not r["contracted_share"]):
            raise ValueError("Verified allocation needs source, share and effective date")
    return rows


def can_allocate(link, month):
    """A large plant or an economic PPA alone does not establish physical delivery."""
    p = pd.Period(month, freq="M")
    try:
        share = float(link["contracted_share"])
    except (TypeError, ValueError):
        return False
    return (link["relationship"] == "dedicated_supply" and link["allocation_verified"] == "yes"
            and math.isfinite(share) and 0.8 <= share <= 1 and bool(link["source_url"])
            and bool(link["from_date"]) and link["from_date"] <= str(p.start_time.date())
            and (not link["to_date"] or link["to_date"] >= str(p.end_time.date())))


def aggregate(frame, link):
    required = {"facilityId", "unitId", "date", "hour", "opTime", "grossLoad", "noxMass"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing hourly fields: {required - set(frame.columns)}")
    d = frame.copy()
    if not (pd.to_numeric(d.facilityId) == int(link["oris_id"])).all():
        raise ValueError("Hourly file contains the wrong plant ID")
    expected = set(link["unit_ids"].split(";")) - {""}
    if not expected or not set(d.unitId).issubset(expected):
        raise ValueError("Verify the plant's expected generating-unit roster before aggregating")
    if d.duplicated(["facilityId", "unitId", "date", "hour"]).any():
        raise ValueError("Duplicate unit-hours; refusing to double count generation")
    d["date"] = pd.to_datetime(d.date, errors="raise")
    d["hour"] = pd.to_numeric(d.hour, errors="raise")
    if not (d.hour.between(0, 23) & (d.hour % 1 == 0)).all():
        raise ValueError("CAMPD hours must be integer local-standard-time hours 0-23")
    for col in ["opTime", "grossLoad", "noxMass"]:
        d[col] = pd.to_numeric(d[col], errors="raise")
    if not d.opTime.between(0, 1).all():
        raise ValueError("Missing or invalid operating time")
    off = d.opTime == 0
    # Explicit off-hours may have empty readings; absence of an entire row is not an off-hour.
    if ((off & ((d.grossLoad.fillna(0) != 0) | (d.noxMass.fillna(0) != 0)))).any():
        raise ValueError("Nonzero measurements in a declared off-hour")
    d.loc[off, ["grossLoad", "noxMass"]] = 0
    for col in ["grossLoad", "noxMass"]:
        if (d[col].dropna() < 0).any() or not d[col].dropna().map(math.isfinite).all():
            raise ValueError(f"Invalid {col}")
    d["month"] = d.date.dt.to_period("M").astype(str)
    rows = []
    for month, g in d.groupby("month"):
        hours = pd.Period(month, freq="M").days_in_month * 24
        expected_hours = hours * len(expected)
        full = len(g) == expected_hours and not g.grossLoad.isna().any()
        observed = float((g.grossLoad * g.opTime).sum(min_count=1))
        rows.append(dict(link_id=link["link_id"], oris_id=link["oris_id"], month=month,
                         gross_mwh=observed if full else None, observed_gross_mwh=observed if math.isfinite(observed) else None,
                         calendar_hours=hours, operating_unit_hours=float(g.opTime.sum()),
                         reported_unit_hours=len(g), expected_unit_hours=expected_hours,
                         coverage=len(g) / expected_hours, gross_avg_mw=observed / hours if full else None,
                         nox_kg=float(g.noxMass.sum()) * 0.45359237 if not g.noxMass.isna().any() and len(g) == expected_hours else None,
                         complete=full))
    return rows


def quarterly_for_site(site_id, pue, root=ROOT):
    path = root / "results_no2" / f"campd_{site_id}_monthly.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if df.empty:
        return {}
    current = {r["link_id"]: r for r in links(root) if r["site_id"] == site_id}
    df["q"] = pd.PeriodIndex(df.month, freq="M").asfreq("Q").astype(str)
    result = {}
    for q, group in df.groupby("q"):
        plants, allocated = [], []
        period = pd.Period(q, freq="Q")
        months = set(pd.period_range(period.start_time, period.end_time, freq="M").astype(str))
        for link_id, g in group.groupby("link_id"):
            link = current.get(link_id)
            if not link or not (g.oris_id.astype(str) == link["oris_id"]).all():
                continue
            if g.month.duplicated().any():
                raise ValueError("Duplicate plant-months")
            roster_size = len(set(link["unit_ids"].split(";")) - {""})
            complete = bool(set(g.month) == months and g.complete.eq(True).all() and g.gross_mwh.notna().all()
                            and roster_size > 0 and (g.expected_unit_hours == g.calendar_hours * roster_size).all())
            hours = int(g.calendar_hours.sum())
            mwh = float(g.gross_mwh.sum()) if complete else None
            eligible = complete and all(can_allocate(link, m) for m in months)
            plants.append(dict(link_id=link_id, oris_id=int(link["oris_id"]), name=link["plant_name"],
                               gross_mwh=mwh, gross_avg_mw=mwh / hours if complete else None,
                               calendar_hours=hours, complete=complete,
                               nox_kg=float(g.nox_kg.sum()) if complete and g.nox_kg.notna().all() else None,
                               relationship=link["relationship"], eligible=eligible, source_url=link["source_url"],
                               reason="Verified physical allocation" if eligible else "Not a verified >=80% physical allocation with a complete quarter"))
            if eligible:
                allocated.append((link_id, mwh * float(link["contracted_share"]) / hours))
        # Every declared dedicated supply link must have data; one of several plants is not a whole-campus total.
        dedicated = {k for k, r in current.items() if r["relationship"] == "dedicated_supply"}
        valid = bool(dedicated) and {k for k, _ in allocated} == dedicated and math.isfinite(pue) and pue > 0
        avg = sum(v for _, v in allocated) if valid else None
        if plants:
            result[q] = dict(plants=plants, allocated_gross_avg_mw=avg,
                             it_equivalent_avg_mw=avg / pue if valid else None,
                             basis="dedicated_plant_measured" if valid else "plant_evidence_only",
                             caveat="Plant gross generation times a documented physical share; not a campus meter. IT equivalent uses assumed PUE; station and network losses are not measured.")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--years", nargs="+", type=int)
    args = ap.parse_args()
    registry = links()
    if args.fetch:
        from campd_hourly import fetch
        years = args.years or [date.today().year - 1, date.today().year]
        for oris in sorted({r["oris_id"] for r in registry if r["oris_id"] and r["unit_ids"]}):
            for year in years:
                df = fetch(int(oris), year, os.environ["EPA_API_KEY"])
                if df.empty:
                    raise ValueError(f"No hourly data for {oris}/{year}; retaining prior cache")
                for link in [r for r in registry if r["oris_id"] == oris]:
                    aggregate(df, link)
                path = ROOT / "data/campd" / f"{oris}_{year}.csv"
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                df.to_csv(tmp, index=False)
                tmp.replace(path)
    by_site, sources, pending = {}, [], []
    for link in registry:
        by_site.setdefault(link["site_id"], [])
        paths = sorted((ROOT / "data/campd").glob(f"{link['oris_id']}_*.csv")) if link["oris_id"] else []
        if args.years:
            paths = [p for p in paths if int(p.stem.split("_")[-1]) in args.years]
        if not paths or not link["unit_ids"]:
            pending.append(dict(link_id=link["link_id"], reason="Verified plant ID/unit roster and hourly records not yet available"))
            continue
        frames = []
        for p in paths:
            frames.append(pd.read_csv(p))
            sources.append(dict(link_id=link["link_id"], file=str(p.relative_to(ROOT)),
                                sha256=hashlib.sha256(p.read_bytes()).hexdigest(), api=API))
        by_site[link["site_id"]].extend(aggregate(pd.concat(frames, ignore_index=True), link))
    for sid, rows in by_site.items():
        output = ROOT / "results_no2" / f"campd_{sid}_monthly.csv"
        pd.DataFrame(rows, columns=COLUMNS).to_csv(output, index=False, float_format="%.8f")
        print(f"{sid}: {len(rows)} plant-months", file=sys.stderr)
    (ROOT / "results_no2/campd_sources.json").write_text(json.dumps(dict(sources=sources, pending=pending), indent=2) + "\n")


if __name__ == "__main__":
    main()
