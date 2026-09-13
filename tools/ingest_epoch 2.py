"""Reproducibly import the bundled Epoch CSVs and saved public map annotations.

No network calls. Fetch snapshots separately with epoch_geocode.py and
epoch_map_snapshot.py. Existing validated sites keep their original observations
and capacity labels. An audit row accounts for every Epoch record.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from pyproj import Geod
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://epoch.ai/data/ai-data-centers"
ALIASES = {
    "Colossus 1": "colossus_memphis", "Colossus 2": "colossus2_southaven",
    "Microsoft Fairwater Wisconsin": "fairwater_wi", "Anthropic-Amazon New Carlisle": "rainier_in",
    "Meta Prometheus": "prometheus_oh", "OpenAI Stargate Abilene": "stargate_abilene",
    "Meta Hyperion": "hyperion_la",
}
# These old park polygons were explicitly unattributed, and are not the Epoch campuses.
UNATTRIBUTED = {"cn_horinger_cloud_valley": "Huawei Horinger", "cn_zhangbei_alibaba": "Alibaba Zhangbei",
                "cn_ulanqab_park": "VNET Bayin Ulanqab"}
COUNTRIES = {"United States": "US", "China": "CN", "Norway": "NO", "Portugal": "PT", "United Kingdom": "GB",
             "United Arab Emirates": "AE", "Indonesia": "ID", "Malaysia": "MY", "Australia": "AU"}


def read_csv(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def write_csv(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: '\n'.join(line.rstrip() for line in str(v).split('\n')) for k, v in row.items()} for row in rows)


def site_id(name):
    return ALIASES.get(name, "epoch_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"))


def number(value):
    if value is None or str(value).strip() == "":
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Invalid nonnegative quantity: {value!r}")
    return result


def normalized_timeline(name, rows, as_of):
    """Keep both IT and facility bases; zero is an observed estimate, not missing.

    Future rows remain auditable projections; they must never supply today's load.
    Intervals for each basis end the day before its next nonblank observation.
    """
    out = []
    for column, basis in [("Power (MW)", "facility_design"), ("IT power (MW)", "it_reported")]:
        dated = sorted((r for r in rows if r["Data center"] == name and number(r[column]) is not None), key=lambda r: r["Date"])
        if len({r['Date'] for r in dated}) != len(dated):
            raise ValueError(f"Duplicate dates for {name} / {basis}")
        for i, row in enumerate(dated):
            start = date.fromisoformat(row["Date"])
            end = (date.fromisoformat(dated[i + 1]["Date"]) - timedelta(days=1)).isoformat() if i + 1 < len(dated) else ""
            state = "projection" if start > as_of else "reported estimate"
            out.append(dict(site_id=site_id(name), valid_from=start.isoformat(), valid_to=end,
                            capacity_mw=f"{number(row[column]):g}", capacity_basis=basis, tier="A2",
                            source=f"Epoch AI: {name}; {column}; {state}", url=SOURCE,
                            notes=f"Epoch {state}, not a meter reading. Buildings operational: {row['Buildings operational'] or 'unknown'}. " + row["Construction status"]))
    return out


def building_features(name, source, source_url):
    features = []
    for i, feature in enumerate((source.get("shapes") or {}).get("features", [])):
        props = feature.get("properties", {})
        if props.get("type") != "Building":
            continue
        geom = shape(feature["geometry"])
        repair = ""
        if geom.geom_type == "LineString":
            gap = Geod(ellps="WGS84").inv(*geom.coords[0], *geom.coords[-1])[2]
            if gap > 5:
                raise ValueError(f"Open building outline: {name}, feature {i}, gap {gap:.1f} m")
            geom = Polygon(geom.coords)
            repair = f"Source LineString outline closed (endpoint gap {gap:.2f} m)."
        if not geom.is_valid:
            geom = make_valid(geom)
            if geom.geom_type == "GeometryCollection":
                geom = MultiPolygon([g for g in geom.geoms if g.geom_type == "Polygon"])
            repair += " Source self-intersection repaired with Shapely make_valid; non-area remnants discarded."
        if geom.geom_type not in ("Polygon", "MultiPolygon") or not geom.is_valid or geom.is_empty:
            raise ValueError(f"Invalid Epoch building geometry: {name}, feature {i}")
        # Source annotations identify buildings explicitly. Keep smaller annotated
        # buildings too; the brief's 0.7 ha threshold was for unknown OSM buildings.
        features.append({"type": "Feature", "geometry": mapping(geom), "properties": {
            "site_id": site_id(name), "name": f"epoch_building_{i:03d}", "ptype": "hall", "confidence": "low" if repair else "medium",
            "geometry_repair": repair,
            "digitised_from": f"Epoch AI public map annotation: {name}, feature {i}", "source_url": source_url,
            "epoch_building_number": props.get("buildingNumber"), "epoch_complete": props.get("complete"),
            "roof_date_required": True,
            "note": "Epoch AI Building annotation (CC BY 4.0); identity and boundary not independently field-verified. Includes planned footprints. Completion flag is not a roof date or operating evidence.",
        }})
    return features


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = ap.parse_args()
    data = ROOT / "data"
    epoch, _ = read_csv(data / "epoch/data_centers.csv")
    times, _ = read_csv(data / "epoch/data_center_timelines.csv")
    sites, fields = read_csv(data / "sites.csv")
    timeline, tl_fields = read_csv(data / "capacity_timeline.csv")
    snapshot = json.loads((data / "epoch/map_annotations.json").read_text())
    geocoding = json.loads((data / "epoch/geocoding.json").read_text())
    # Only regenerate rows owned by this importer; preserve curated inputs.
    sites = [r for r in sites if not r['site_id'].startswith('epoch_')]
    timeline = [r for r in timeline if not r['site_id'].startswith('epoch_')]
    normalized, audit = [], []
    for old in sites:
        if old["site_id"] in UNATTRIBUTED:
            name = UNATTRIBUTED[old["site_id"]]
            old.update(capacity_tier="U", capacity_mw="", capacity_basis="", in_epoch_db="no",
                       capacity_source="Unknown: earlier Epoch figure was assigned to unattributed park polygons; withdrawn after comparing Epoch's published location.", capacity_url=SOURCE)
            note = f" Epoch's {name} is mapped separately as {site_id(name)}; do not attribute its MW to this park."
            if note not in old['notes']:
                old['notes'] += note
    timeline = [r for r in timeline if not (r['site_id'] in UNATTRIBUTED and r['source'].startswith('Epoch'))]
    for row in epoch:
        name = row["Name"]
        sid = site_id(name)
        source = snapshot["sites"][name]
        normalized.extend(normalized_timeline(name, times, args.as_of))
        geo = geocoding[name]
        rec = dict(epoch_name=name, site_id=sid, status="existing_curated" if name in ALIASES else "imported",
                   address_status=geo["status"], coords_quality="", geocode_offset_m="", hall_polygons=0,
                   roof_status="pending", notes="")
        if name in ALIASES:
            rec["notes"] = "Existing validated labels and geometry retained; normalized Epoch timeline saved separately for comparison."
            audit.append(rec)
            continue
        lng, lat = source["lngLat"]
        quality = "epoch_published"
        # A street or settlement centroid is never promoted to an address match.
        matches = [r for r in geo["results"] if r.get("place_rank", 0) >= 30]
        if matches:
            nearest = min(matches, key=lambda r: Geod(ellps="WGS84").inv(lng, lat, float(r['lon']), float(r['lat']))[2])
            offset = Geod(ellps="WGS84").inv(lng, lat, float(nearest['lon']), float(nearest['lat']))[2]
            rec['geocode_offset_m'] = round(offset)
            if offset <= 1000:
                quality = "geocoded_address"
                lng, lat = float(nearest['lon']), float(nearest['lat'])
        features = building_features(name, source, snapshot["source_url"])
        rec.update(coords_quality=quality, hall_polygons=len(features))
        if not features:
            rec.update(status="location_only", roof_status="no_polygons", notes="Epoch provides no Building annotation; no boundary invented.")
        current = sorted((r for r in normalized if r['site_id'] == sid and r['valid_from'] <= args.as_of.isoformat()
                          and (not r['valid_to'] or r['valid_to'] >= args.as_of.isoformat())),
                         key=lambda r: (r['capacity_basis'] == 'it_reported', r['valid_from']))
        cap = current[-1] if current else None
        if not features:
            cap = None
        item = {k: "" for k in fields}
        country = COUNTRIES[row['Country']]
        item.update(site_id=sid, name=name, operator=re.sub(r"\s+#(?:confident|likely|speculative)", "", row['Owner']),
                    country=country, region="CN" if country == "CN" else ("EU" if country in ("NO", "GB", "PT") else country),
                    lat=f"{lat:.7f}", lon=f"{lng:.7f}", coords_quality=quality, cooling_arch="unknown", annulus_r_in_m="500", annulus_r_out_m="2000",
                    obs_start="2018-01-01", obs_end=args.as_of.isoformat(), thermal_backend="none", capacity_tier="A2" if cap else "U",
                    capacity_mw=cap['capacity_mw'] if cap else "", capacity_basis=cap['capacity_basis'] if cap else "",
                    capacity_source=cap['source'] if cap else (f"Epoch AI: {name}; no dated capacity on or before {args.as_of}" if features else f"Epoch AI: {name}; capacity unassigned because no building polygon is available"),
                    capacity_url=SOURCE, in_epoch_db="yes",
                    notes=f"Epoch AI (CC BY 4.0). Capacity is a reported/modelled estimate, not measured use; A2 denotes a sourced estimate here. Address: {row['Address'] or 'not supplied'}. "
                          f"Coordinates: {quality}; Epoch map coordinates retained as source in data/epoch/map_annotations.json. "
                          "Building annotations may include planned structures; independent Sentinel-2 dating required. "
                          "Facility-to-IT conversion uses the explicitly assumed default PUE 1.2 only when IT power is absent.")
        sites.append(item)
        if features:
            timeline.extend(r for r in normalized if r['site_id'] == sid)
        if features:
            (data / "polygons" / f"{sid}.geojson").write_text(json.dumps({"type": "FeatureCollection", "name": sid, "features": features}, indent=1) + "\n")
        audit.append(rec)
    write_csv(data / "sites.csv", sites, fields)
    write_csv(data / "capacity_timeline.csv", timeline, tl_fields)
    write_csv(data / "epoch/normalized_capacity_timeline.csv", normalized, tl_fields)
    write_csv(data / "epoch/import_audit.csv", audit, list(audit[0]))
    print(f"Epoch records: {len(audit)}; imported sites: {sum(r['status'] == 'imported' for r in audit)}; location-only: {sum(r['status'] == 'location_only' for r in audit)}; existing: {len(ALIASES)}", file=sys.stderr)


if __name__ == "__main__":
    main()
