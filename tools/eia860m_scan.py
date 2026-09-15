#!/usr/bin/env python
"""Generator fleets and dedicated plants near data centres, from EIA-860M (RFW-20).

    python tools/eia860m_scan.py [--xlsx path/to/<month>_generator<year>.xlsx] [--radius-km 10] [--since 2023]

EIA-860M is the US Energy Information Administration's monthly inventory of generators, one row per generator with the
plant's coordinates, owner, technology, capacity, status and (planned) operating date:
https://www.eia.gov/electricity/data/eia860m/  (xls/<month>_generator<year>.xlsx). Without --xlsx the newest workbook that
downloads is used, walking back from the current month; its SHA-256 is written to the summary.

Two flags, per plant:
  near      the plant is within --radius-km of an inventory site (data/sites.csv, US, not a control point); the nearest
            site and the distance are recorded
  keyword   the plant or owner name carries a data-centre operator or term (KEYWORDS below)
Kept generators: fossil and fuel-cell prime movers (gas turbines, combined cycle, engines, steam, fuel cells) that are planned,
or operating since --since. Solar, wind, hydro and batteries are dropped: they emit no NOx and cannot be watched by TROPOMI.
Whether a plant is in data/egrid/plants_2023.csv, the eGRID 2023 fossil plants with emissions estimates, is looked up by ORIS
code (EIA plant id = ORIS): "in eGRID 2023; hourly EPA reporting not checked" for plants in that file, because eGRID lists
plants whether or not they report hourly to EPA's CAMPD, else "unknown: not in eGRID 2023 (new plant or non-reporting); needs the CAMPD
facility list, EPA key". Hand verification lives in data/eia860m_review.csv (plant_id, verdict, evidence_url, note) and is
merged in; every other row is "unverified".

Writes results/eia860m_candidates.csv (one row per flagged plant) and results/eia860m_scan_summary.json. Nothing here is a
load or a capacity of a campus: a generator's nameplate is generation capacity, and a plant next to a campus may serve the
grid. Watches are added by hand, in coordination with RFW-21.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.eia.gov/electricity/data/eia860m/xls/"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
FOSSIL_TECH = re.compile(r"natural gas|petroleum|combustion turbine|combined cycle|internal combustion|fuel cell|other gas|steam coal|coal", re.I)
KEYWORDS = [
    "data center", "datacenter", "data centre", "hyperscale", "compute", "ai campus", "stargate", "colossus", "fairwater", "hyperion",
    "microsoft", "meta platforms", "facebook", "google", "amazon", "aws", "oracle", "openai", "xai", "x.ai", "crusoe", "coreweave",
    "vantage data", "qts", "digital realty", "equinix", "stack infrastructure", "aligned", "compass datacenters", "switch", "fermi",
    "poolside", "nebius", "lancium", "applied digital", "terawulf", "core scientific", "cipher mining", "galaxy digital", "hut 8",
    "iren", "soluna", "sail", "cyrusone", "novva", "edgecore", "prime data", "voltagrid", "williams field services", "apollo",
]


def haversine_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_workbook(cache: Path) -> tuple[Path, str]:
    """Newest EIA-860M workbook that downloads (the page links months that are not yet published)."""
    import requests
    ua = {"User-Agent": "openobservatory.info research (https://github.com/recozers/openobservatory)"}
    today = dt.date.today()
    y, m = today.year, today.month
    for _ in range(14):
        name = f"{MONTHS[m - 1]}_generator{y}.xlsx"
        out = cache / name
        if out.exists() and out.stat().st_size > 1_000_000:
            return out, BASE + name
        r = requests.get(BASE + name, headers=ua, timeout=120)
        if r.status_code == 200 and len(r.content) > 1_000_000:
            cache.mkdir(parents=True, exist_ok=True)
            out.write_bytes(r.content)
            return out, BASE + name
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    sys.exit("no EIA-860M workbook could be downloaded")


def load_generators(xlsx: Path, since: int) -> pd.DataFrame:
    frames = []
    for sheet in ("Operating", "Planned"):
        df = pd.read_excel(xlsx, sheet, header=2)
        df["sheet"] = sheet
        frames.append(df)
    g = pd.concat(frames, ignore_index=True)
    g = g[g.Technology.fillna("").str.contains(FOSSIL_TECH)]
    g["year"] = pd.to_numeric(g.get("Operating Year"), errors="coerce").fillna(pd.to_numeric(g.get("Planned Operation Year"), errors="coerce"))
    g["month"] = pd.to_numeric(g.get("Operating Month"), errors="coerce").fillna(pd.to_numeric(g.get("Planned Operation Month"), errors="coerce"))
    g = g[(g.sheet == "Planned") | (g.year >= since)]
    g = g.dropna(subset=["Latitude", "Longitude"])
    return g


def inventory() -> pd.DataFrame:
    s = pd.read_csv(ROOT / "data" / "sites.csv", dtype=str).fillna("")
    s = s[(s.country == "US") & ~s.site_id.str.startswith("ctrl_")].copy()
    s["lat"] = s.lat.astype(float)
    s["lon"] = s.lon.astype(float)
    return s[["site_id", "name", "operator", "lat", "lon", "site_class"]]


def epa_known() -> set[int]:
    p = ROOT / "data" / "egrid" / "plants_2023.csv"
    if not p.exists():
        return set()
    return set(pd.to_numeric(pd.read_csv(p).ORISPL, errors="coerce").dropna().astype(int))


def review() -> dict[int, dict]:
    p = ROOT / "data" / "eia860m_review.csv"
    if not p.exists():
        return {}
    return {int(r["plant_id"]): r for r in csv.DictReader(open(p, encoding="utf-8"))}


def scan(g: pd.DataFrame, sites: pd.DataFrame, radius_km: float, epa: set[int], reviews: dict[int, dict]) -> pd.DataFrame:
    rows = []
    for pid, pg in g.groupby("Plant ID"):
        lat, lon = float(pg.Latitude.iloc[0]), float(pg.Longitude.iloc[0])
        d = sites.assign(km=[haversine_km(lat, lon, a, b) for a, b in zip(sites.lat, sites.lon)]).sort_values("km").iloc[0]
        text = f"{pg['Plant Name'].iloc[0]} | {pg['Entity Name'].iloc[0]}".lower()
        kws = [k for k in KEYWORDS if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", text)]
        near = d.km <= radius_km
        if not near and not kws:
            continue
        cap = pd.to_numeric(pg["Nameplate Capacity (MW)"], errors="coerce").fillna(0)
        tech = "; ".join(f"{t} {c:.0f} MW" for t, c in cap.groupby(pg.Technology).sum().items())
        statuses = "; ".join(sorted({str(x).split(")")[0].strip("(") for x in pg.Status.dropna()}))
        first = pg.assign(ym=pg.year.fillna(9999) * 100 + pg.month.fillna(1)).ym.min()
        first_txt = f"{int(first // 100)}-{int(first % 100):02d}" if first < 999900 else ""
        rv = reviews.get(int(pid), {})
        rows.append(dict(
            plant_id=int(pid), plant_name=pg["Plant Name"].iloc[0], entity=pg["Entity Name"].iloc[0], state=pg["Plant State"].iloc[0],
            county=pg.County.iloc[0], lat=round(lat, 5), lon=round(lon, 5), sector=pg.Sector.iloc[0], sheet="; ".join(sorted(set(pg.sheet))),
            n_generators=len(pg), nameplate_mw=round(float(cap.sum()), 1), technologies=tech, statuses=statuses, first_operation=first_txt,
            flag_near=bool(near), nearest_site=d.site_id, nearest_site_name=d["name"], nearest_site_class=d.site_class, distance_km=round(float(d.km), 2),
            flag_keyword="; ".join(kws),
            epa_hourly="in eGRID 2023; hourly EPA reporting not checked" if int(pid) in epa else "unknown: not in eGRID 2023 (new plant or non-reporting); needs the CAMPD facility list, EPA key",
            verdict=rv.get("verdict", "unverified"), evidence_url=rv.get("evidence_url", ""), review_note=rv.get("note", ""),
        ))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["score"] = out.flag_near.astype(int) * 2 + (out.flag_keyword != "").astype(int)
    return out.sort_values(["score", "distance_km"], ascending=[False, True]).drop(columns="score")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=None)
    ap.add_argument("--radius-km", type=float, default=10.0)
    ap.add_argument("--since", type=int, default=2023, help="keep operating generators with an operating year from this year")
    ap.add_argument("--out", default="results/eia860m_candidates.csv")
    args = ap.parse_args()
    if args.xlsx:
        xlsx, url = args.xlsx, ""
    else:
        xlsx, url = latest_workbook(ROOT / "data" / "cache" / "eia860m")
    g = load_generators(xlsx, args.since)
    sites = inventory()
    cands = scan(g, sites, args.radius_km, epa_known(), review())
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cands.to_csv(out, index=False)
    title = pd.read_excel(xlsx, "Operating", header=None, nrows=1).iloc[0, 0]
    summary = dict(workbook=xlsx.name, workbook_title=str(title), url=url or BASE + xlsx.name, sha256=sha256(xlsx), scanned_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                   generators_kept=int(len(g)), plants_kept=int(g["Plant ID"].nunique()), inventory_sites=int(len(sites)), radius_km=args.radius_km, since=args.since,
                   candidates=int(len(cands)), near=int(cands.flag_near.sum()) if len(cands) else 0, keyword=int((cands.flag_keyword != "").sum()) if len(cands) else 0,
                   both=int((cands.flag_near & (cands.flag_keyword != "")).sum()) if len(cands) else 0,
                   epa_known=int(cands.epa_hourly.str.startswith("yes").sum()) if len(cands) else 0)
    (out.with_name("eia860m_scan_summary.json")).write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    cols = ["plant_id", "plant_name", "entity", "state", "nameplate_mw", "sheet", "first_operation", "distance_km", "nearest_site", "flag_keyword", "verdict"]
    with pd.option_context("display.width", 250, "display.max_colwidth", 40):
        print(cands[cols].to_string(index=False))


if __name__ == "__main__":
    main()
