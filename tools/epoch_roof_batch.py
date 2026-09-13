"""Run one resumable Earth Engine roof extraction process per imported site.

On macOS: caffeinate -i python tools/epoch_roof_batch.py --workers 3
Credentials are read from the environment or the existing EE login. Per-site
logs and extraction caches stay under gitignored data/cache/.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, choices=range(1, 5), default=1)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=(date.today() + timedelta(days=1)).isoformat(), help="Exclusive end")
    args = ap.parse_args()
    logs = ROOT / "data/cache/epoch_roof_logs"
    logs.mkdir(parents=True, exist_ok=True)

    def run(path):
        out = ROOT / "results_s2" / f"{path.stem}.csv"
        summary = out.with_suffix(".roof_dates.json")
        if summary.exists() and out.exists():
            saved = json.loads(summary.read_text())
            if (saved.get("start") == args.start and saved.get("end_exclusive") == args.end
                    and saved.get("polygons_sha256") == hashlib.sha256(path.read_bytes()).hexdigest()
                    and any(h["valid_months"] for h in saved["halls"].values())):
                return path.stem, 0, "cached"
        with (logs / f"{path.stem}.log").open("w") as log:
            result = subprocess.run([sys.executable, str(ROOT / "tools/s2_roof_timeline.py"), str(path),
                                     "--start", args.start, "--end", args.end, "--out", str(out)],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        return path.stem, result.returncode, "extracted"

    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for sid, code, state in pool.map(run, sorted((ROOT / "data/polygons").glob("epoch_*.geojson"))):
            print(f"{sid}: {state}, exit {code}", file=sys.stderr, flush=True)
            if code:
                failed.append(sid)
    if failed:
        sys.exit(f"Failed sites (rerun to resume): {', '.join(failed)}")


if __name__ == "__main__":
    main()
