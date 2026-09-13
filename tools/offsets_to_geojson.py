#!/usr/bin/env python
"""Turn hand-digitised polygons, written as metre offsets (east, north) from a
site centre, into a GeoJSON FeatureCollection in EPSG:4326.

Input is a JSON file:
{
  "site_id": "nsa_utah",
  "centre": [lat, lon],
  "polygons": [
    {"name": "technical_strip", "ptype": "hall", "confidence": "high",
     "offsets_m": [[dx, dy], ...], "valid_from": "2014-06-01"},
    ...
  ]
}

Offsets are converted with a local equirectangular approximation, accurate to
well under a metre at the scales involved (< 2 km).
"""
import argparse
import json
import math
from pathlib import Path


def convert(spec: dict) -> dict:
    lat0, lon0 = spec["centre"]
    m_per_deg_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat0)) + 1.175 * math.cos(4 * math.radians(lat0))
    m_per_deg_lon = 111412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    feats = []
    for p in spec["polygons"]:
        ring = [[round(lon0 + dx / m_per_deg_lon, 7), round(lat0 + dy / m_per_deg_lat, 7)] for dx, dy in p["offsets_m"]]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        props = {k: v for k, v in p.items() if k != "offsets_m"}
        props["site_id"] = spec["site_id"]
        props.setdefault("digitised_from", spec.get("digitised_from", "Sentinel-2 L2A 10 m true colour"))
        feats.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "name": spec["site_id"], "features": feats}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="+", help="offset spec JSON file(s)")
    ap.add_argument("--out-dir", default="data/polygons")
    args = ap.parse_args()
    for s in args.spec:
        spec = json.loads(Path(s).read_text())
        fc = convert(spec)
        out = Path(args.out_dir) / f"{spec['site_id']}.geojson"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(fc, indent=1))
        print("wrote", out, len(fc["features"]), "features")


if __name__ == "__main__":
    main()
