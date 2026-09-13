"""Cache a one-time, serial Nominatim lookup of the bundled Epoch addresses.

Usage: python tools/epoch_geocode.py
Policy: https://operations.osmfoundation.org/policies/nominatim/
One machine, one process, at most one request/second; never schedule this job.
Successful and empty responses are cached. HTTP errors stop the run.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "OpenObservatory/0.1 (https://github.com/recozers/openobservatory; one-time Epoch inventory research)"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", default=os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"))
    ap.add_argument("--out", type=Path, default=ROOT / "data/epoch/geocoding.json")
    args = ap.parse_args()
    records = json.loads(args.out.read_text()) if args.out.exists() else {}
    rows = list(csv.DictReader((ROOT / "data/epoch/data_centers.csv").open()))
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    last_request = 0.0
    for row in rows:
        name, address = row["Name"], row["Address"].strip()
        if name in records:
            continue
        if not address:
            records[name] = {"address": "", "status": "missing_address", "results": []}
        else:
            # Reuse identical addresses within this run too (two Epoch entries can share a campus).
            prior = next((v for v in records.values() if v["address"] == address), None)
            if prior:
                records[name] = dict(prior)
            else:
                time.sleep(max(0, 1.1 - (time.monotonic() - last_request)))
                last_request = time.monotonic()
                response = session.get(args.endpoint, params={"q": address, "format": "jsonv2", "limit": 3, "addressdetails": 1}, timeout=45)
                response.raise_for_status()
                results = response.json()
                records[name] = {"address": address, "status": "found" if results else "not_found",
                                 "requested_url": response.url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                 "results": results}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
        temporary.replace(args.out)
        result = records[name]
        print(f"{name}: {result['status']} " + (result["results"][0]["display_name"] if result["results"] else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
