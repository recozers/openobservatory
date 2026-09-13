"""Preserve publicly embedded Epoch map coordinates and annotations (CC BY).

This is a source snapshot, not an inference of building identity from size.
The existing bundled CSVs remain the capacity and timeline inputs.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

URL = "https://epoch.ai/data/ai-data-centers/map"
ROOT = Path(__file__).resolve().parents[1]


def decode(value):
    """Decode only the plain object/array types used in Astro's public props."""
    if value == [0]:
        return None
    tag, payload = value
    if tag == 0:
        return {k: decode(v) for k, v in payload.items()} if isinstance(payload, dict) else payload
    if tag == 1:
        return [decode(v) for v in payload]
    raise ValueError(f"Unsupported serialized type: {tag}")


class MapParser(HTMLParser):
    sites = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "astro-island" and "SearchFilterMap." in attrs.get("component-url", ""):
            self.sites = decode(json.loads(attrs["props"])["dataCenters"])


def main():
    response = requests.get(URL, headers={"User-Agent": "OpenObservatory/0.1 (https://github.com/recozers/openobservatory)"}, timeout=60)
    response.raise_for_status()
    parser = MapParser()
    parser.feed(response.content.decode("utf-8"))
    if not parser.sites:
        raise ValueError("Epoch map format changed: no sites found")
    out = {"source_url": URL, "retrieved_at": datetime.now(timezone.utc).isoformat(),
           "attribution": "Epoch AI, AI Data Centers, CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
           "sites": {r["id"]: {"lngLat": r.get("lngLat"), "bounds": r.get("bounds"), "shapes": r.get("shapes"),
                                 "city": r["facts"].get("city"), "state": r["facts"].get("state"),
                                 "country": r["facts"].get("country")} for r in parser.sites}}
    path = ROOT / "data/epoch/map_annotations.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(out['sites'])} sites to {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
