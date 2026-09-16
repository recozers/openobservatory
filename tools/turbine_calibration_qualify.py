#!/usr/bin/env python
"""Qualify or reject the gas-turbine NOx calibration candidates (RFW-16).

    python tools/turbine_calibration_qualify.py [--eia860 path/to/eia8602024.zip] [--offline]

Three checks per plant, for the five tall-stack coal references and the three gas candidates in
tools/compare_stack_calibration.py:

1. Physical stack height, from EIA-860 2024 schedule 6 (environmental equipment), sheet "Stack Flue", column
   "Stack Height (Feet)", joined to boilers through the "Boiler Stack Flue" association. Source:
   https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602024.zip (SHA-256 recorded). A plant with no stack record
   cannot be classed.
2. Isolation from other NOx sources, from the EPA's 2020 National Emissions Inventory facility summaries through the
   Envirofacts API (https://data.epa.gov/efservice/nei.vw_facility_summaries_2020/pollutant_code/equals/NOX/state_abbr/equals/<ST>/JSON,
   short tons per year, facility coordinates). The plant's own record is the facility within 1.5 km; every other facility
   within 30 km is kept in data/nei_2020_nox_near_calibration_plants.csv. The test: other facilities within 10 km (the
   plume plateau is read 1 to 9 km downwind) must sum to less than 10 % of the plant's own NOx, and no single one may
   exceed 5 % of it; a neighbour of that size biases the factor by less than the 19 % plant-to-plant scatter of the coal
   calibration. Power plants and industry alike count; eGRID covered only power plants.
3. Overpass alignment. Sentinel-5P crosses the equator at about 13:30 mean local solar time, so the overpass at a plant is
   near 13:30 + longitude / 15 hours UTC; the two whole UTC hours around it are mapped to the CAMPD hours, which are local
   standard time. This is a third time window for tools/compare_stack_calibration.py. It is still not the per-day overpass
   time, which the saved profiles do not hold; across the 2,600 km swath the pixel's local time varies by about an hour.

Writes results_no2/calibration_plant_qualification.csv (one row per plant with heights, isolation numbers, windows and the
verdict) and the NEI neighbour file. A candidate is qualified as a low-stack reference when its stack height is reported and
under 60 m and it passes the isolation test; it is never pooled with the coal references, whose stacks are 91 to 305 m.
--offline reuses the cached downloads under data/cache/ and fails if they are missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from no2_flux_quarterly import CAL_PLANTS  # noqa: E402
from compare_stack_calibration import CANDIDATES  # noqa: E402

EIA860_URL = "https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602024.zip"
EIA860_SHA256 = "0aaae04812cd4ab87a3e346bdf93848a3cc15053fd4dc2a4cf82d2aeac95f12b"
NEI_URL = "https://data.epa.gov/efservice/nei.vw_facility_summaries_2020/pollutant_code/equals/NOX/state_abbr/equals/{st}/JSON"
UA = {"User-Agent": "openobservatory.info research (https://github.com/recozers/openobservatory)"}
CACHE = ROOT / "data" / "cache"
LOW_STACK_M = 60.0
ISOLATION_KM = 10.0
ISOLATION_SHARE = 0.10
ISOLATION_SINGLE_SHARE = 0.05
NEIGHBOUR_KM = 30.0
OVERPASS_SOLAR_HOUR = 13.5   # Sentinel-5P ascending node, mean local solar time

# plant key -> (facility id, UTC offset of local standard time)
PLANTS = {k: (v, -6) for k, v in CAL_PLANTS.items()} | {k: v for k, v in CANDIDATES.items()}


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


def fetch(url: str, out: Path, offline: bool) -> Path:
    if out.exists():
        return out
    if offline:
        sys.exit(f"offline and {out} is missing")
    import requests
    r = requests.get(url, headers=UA, timeout=600)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    return out


def plant_coords() -> dict[str, tuple[float, float, str]]:
    eg = pd.read_csv(ROOT / "data" / "egrid" / "plants_2023.csv")
    eg = eg.set_index("ORISPL")
    return {k: (float(eg.loc[fid, "LAT"]), float(eg.loc[fid, "LON"]), str(eg.loc[fid, "PSTATABB"])) for k, (fid, _) in PLANTS.items()}


def stack_heights(zip_path: Path) -> dict[int, dict]:
    with zipfile.ZipFile(zip_path) as z:
        equip = next(n for n in z.namelist() if "EnviroEquip" in n)
        with z.open(equip) as f:
            sf = pd.read_excel(f, "Stack Flue", header=1)
    out = {}
    for fid in {v[0] for v in PLANTS.values()}:
        rows = sf[(sf["Plant Code"] == fid) & (sf["Stack Flue Status"].astype(str) == "OP")]
        h = pd.to_numeric(rows["Stack Height (Feet)"], errors="coerce").dropna() * 0.3048
        out[fid] = dict(n_stacks=int(len(rows)), stack_min_m=round(float(h.min()), 1) if len(h) else None,
                        stack_max_m=round(float(h.max()), 1) if len(h) else None,
                        stack_ids=";".join(map(str, rows["Stack or Flue ID"].tolist())))
    return out


def nei_neighbours(coords: dict, offline: bool) -> tuple[pd.DataFrame, dict[str, dict]]:
    by_state = {}
    for st in sorted({c[2] for c in coords.values()}):
        p = fetch(NEI_URL.format(st=st), CACHE / "nei2020" / f"nox_{st}.json", offline)
        by_state[st] = json.loads(p.read_text())
    rows, stats = [], {}
    for key, (lat, lon, st) in coords.items():
        own, others = [], []
        for f in by_state[st]:
            if f.get("latitude") is None or f.get("longitude") is None:
                continue
            km = haversine_km(lat, lon, f["latitude"], f["longitude"])
            if km > NEIGHBOUR_KM:
                continue
            rec = dict(plant=key, eis_facility_id=f["eis_facility_id"], site_name=f["site_name"], facility_type=f.get("facility_type") or "",
                       naics_code=f.get("naics_code"), county=f.get("county_name"), state=st, latitude=f["latitude"], longitude=f["longitude"],
                       nox_short_tons=round(float(f.get("emissions") or 0), 2), distance_km=round(km, 2))
            (own if km < 1.5 and "Electricity Generation" in rec["facility_type"] else others).append(rec)
            rows.append(dict(rec, role="own" if rec in own else "neighbour"))
        own_tons = sum(r["nox_short_tons"] for r in own)
        near = [r for r in others if r["distance_km"] <= ISOLATION_KM]
        near_tons = sum(r["nox_short_tons"] for r in near)
        biggest = max(near, key=lambda r: r["nox_short_tons"]) if near else None
        stats[key] = dict(nei_own_nox_tons=round(own_tons, 1), nei_own_records=len(own),
                          nei_other_nox_10km_tons=round(near_tons, 1), nei_other_share_10km=round(near_tons / own_tons, 3) if own_tons else None,
                          nei_largest_other_10km=f"{biggest['site_name']} ({biggest['nox_short_tons']:.0f} t, {biggest['distance_km']:.1f} km)" if biggest else "",
                          nei_largest_other_10km_tons=round(biggest["nox_short_tons"], 1) if biggest else 0.0,
                          nei_other_nox_30km_tons=round(sum(r["nox_short_tons"] for r in others), 1),
                          nei_largest_other_30km=(lambda b: f"{b['site_name']} ({b['nox_short_tons']:.0f} t, {b['distance_km']:.1f} km)")(max(others, key=lambda r: r["nox_short_tons"])) if others else "")
    return pd.DataFrame(rows), stats


def overpass_window(lon: float, offset: int) -> dict:
    utc = OVERPASS_SOLAR_HOUR - lon / 15.0
    h = int(math.floor(utc))
    local = [h + offset, h + 1 + offset]
    return dict(overpass_utc=round(utc, 2), overpass_utc_hours=f"{h}|{h + 1}", overpass_local_standard_hours="|".join(map(str, local)))


def qualify(row: dict, is_candidate: bool) -> tuple[str, str]:
    reasons = []
    if row["stack_max_m"] is None:
        reasons.append("no operating stack record in EIA-860 2024, so the stack height is unreported")
    elif is_candidate and row["stack_max_m"] >= LOW_STACK_M:
        reasons.append(f"tallest stack {row['stack_max_m']} m is not a low stack")
    share = row["nei_other_share_10km"]
    if share is None:
        reasons.append("no NEI record for the plant itself")
    elif share >= ISOLATION_SHARE:
        reasons.append(f"other NOx sources within {ISOLATION_KM:.0f} km emit {share:.0%} of the plant's own NOx (limit {ISOLATION_SHARE:.0%})")
    own = row["nei_own_nox_tons"] or 0
    if own and row["nei_largest_other_10km_tons"] / own >= ISOLATION_SINGLE_SHARE:
        reasons.append(f"a single neighbour within {ISOLATION_KM:.0f} km emits {row['nei_largest_other_10km_tons'] / own:.0%} of the plant's own NOx (limit {ISOLATION_SINGLE_SHARE:.0%})")
    if reasons:
        return ("rejected" if is_candidate else "reference with caveat"), "; ".join(reasons)
    return ("qualified low-stack reference" if is_candidate else "tall-stack reference"), "stack height reported; other sources within 10 km under 10 % in total and under 5 % singly"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eia860", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", default="results_no2/calibration_plant_qualification.csv")
    args = ap.parse_args()
    zip_path = args.eia860 or fetch(EIA860_URL, CACHE / "eia860" / "eia8602024.zip", args.offline)
    digest = sha256(zip_path)
    if digest != EIA860_SHA256:
        sys.exit(f"EIA-860 archive SHA-256 {digest} differs from the recorded {EIA860_SHA256}")
    coords = plant_coords()
    heights = stack_heights(zip_path)
    neighbours, stats = nei_neighbours(coords, args.offline)
    neighbours.sort_values(["plant", "distance_km"]).to_csv(ROOT / "data" / "nei_2020_nox_near_calibration_plants.csv", index=False)
    rows = []
    for key, (fid, offset) in PLANTS.items():
        lat, lon, st = coords[key]
        is_candidate = key in CANDIDATES
        row = dict(plant=key, facility_id=fid, state=st, lat=lat, lon=lon, candidate=is_candidate, **heights[fid], **stats[key], **overpass_window(lon, offset))
        row["verdict"], row["reason"] = qualify(row, is_candidate)
        row["stack_class"] = ("tall_coal_reference" if not is_candidate else
                              "gas_low_stack_qualified" if row["verdict"].startswith("qualified") else
                              "gas_candidate_rejected" if row["stack_max_m"] is not None else "gas_candidate_stack_unreported")
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / args.out, index=False)
    meta = dict(eia860_url=EIA860_URL, eia860_sha256=digest, nei_endpoint=NEI_URL, nei_states=sorted({c[2] for c in coords.values()}),
                rules=dict(low_stack_m=LOW_STACK_M, isolation_km=ISOLATION_KM, isolation_share=ISOLATION_SHARE, isolation_single_share=ISOLATION_SINGLE_SHARE,
                           overpass_solar_hour=OVERPASS_SOLAR_HOUR))
    (ROOT / args.out).with_suffix(".json").write_text(json.dumps(meta, indent=1))
    cols = ["plant", "facility_id", "stack_min_m", "stack_max_m", "nei_own_nox_tons", "nei_other_share_10km", "nei_largest_other_10km", "overpass_utc", "overpass_local_standard_hours", "verdict"]
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(out[cols].to_string(index=False))
    for r in rows:
        print(f"  {r['plant']}: {r['verdict']}: {r['reason']}")


if __name__ == "__main__":
    main()
