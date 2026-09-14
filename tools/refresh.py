"""Refresh roof evidence, approved published NOx series, and the static JSON.

Dry-run skips Earth Engine, rebuilds from checked-in evidence, validates JSON,
and never commits. The workflow owns committing and deployment.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    print("Running: " + " ".join(args), file=sys.stderr, flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    no_credentials = not (os.getenv("EE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    dry = args.dry_run or no_credentials
    if dry:
        print("Dry-run: Earth Engine skipped; rebuilding from saved evidence; no publication.", file=sys.stderr)
    else:
        with (ROOT / "data/sites.csv").open() as f:
            sites = list(csv.DictReader(f))
        for site in sites:
            sid = site["site_id"]
            polygons = ROOT / "data/polygons" / f"{sid}.geojson"
            if not polygons.exists():
                continue
            data = json.loads(polygons.read_text())
            if not any(p.get("properties", {}).get("ptype") == "hall" for p in data["features"]):
                continue
            run("tools/s2_roof_timeline.py", str(polygons), "--start", "2018-01-01",
                "--end", (date.today() + timedelta(days=1)).isoformat(), "--out", f"results_s2/{sid}.csv")
    with (ROOT / "data/refresh_flux_sources.csv").open() as f:
        flux_sources = list(csv.DictReader(f))
    for source in flux_sources:
        if source.get("refresh_mode") == "generator_watch":
            continue  # Fresh extraction and baseline uncertainty handled below.
        if not (ROOT / source["profile"]).exists():
            raise FileNotFoundError(f"Missing approved flux profile: {source['profile']}")
        cmd = ["tools/no2_flux_quarterly.py", source["profile"], "--site", source["site_id"]]
        if source["baseline_before"]:
            cmd += ["--baseline-before", source["baseline_before"]]
        run(*cmd)
    run("tools/campd_monthly.py", *(["--fetch"] if not dry and os.getenv("EPA_API_KEY") else []))
    run("tools/water_monthly.py")
    run("tools/generator_watchlist.py", *([] if dry else ["--live"]))
    os.environ.update(OBS_FILE="data/observations_all.csv", REJ_FILE="data/rejections_all.csv", RESULTS_DIR="results_gee")
    for script in ("build_site.py", "build_timeline_data.py", "build_status.py"):
        run(script)
    def invalid(value):
        raise ValueError(f"Non-JSON numeric token: {value}")
    files = list((ROOT / "site/data").rglob("*.json"))
    for path in files:
        json.loads(path.read_text(), parse_constant=invalid)
    print(f"Validated {len(files)} JSON files", file=sys.stderr)
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"publish={'false' if dry else 'true'}\n")


if __name__ == "__main__":
    main()
