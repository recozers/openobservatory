"""Rebuild everything the public site reads from the committed data, and keep only real changes.

The Site data workflow (.github/workflows/site-data.yml) runs this on main after every push that can change the site, so a
merged request for work reaches the map views, the list, the research view and the findings page without anyone rebuilding
by hand. It works the same way locally.

    python tools/rebuild_site_data.py           # rebuild; undo changes that are only a new build timestamp
    python tools/rebuild_site_data.py --check   # the same, then exit 1 if anything changed for real

It renders site/requests.html, then runs build_site.py, build_timeline_data.py and build_status.py (which also writes the
findings) with the saved-evidence settings the tests workflow uses. A JSON file has not changed if it differs from the
last commit only in its top-level "generated" timestamp or in the last digits of floating-point numbers, which differ
between a Mac and the Linux runner. If any file has changed for real, every rebuilt file is kept, so the build dates on
the pages agree.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = (["tools/build_requests_page.py"], ["build_site.py"], ["build_timeline_data.py"], ["build_status.py"])
SAVED_EVIDENCE = dict(OBS_FILE="data/observations_all.csv", REJ_FILE="data/rejections_all.csv", RESULTS_DIR="results_gee")
OUTPUTS = ("site/data", "site/requests.html")
TIMESTAMPS = ("generated",)
REL_TOL = 1e-9  # platform rounding shows up in the 16th significant digit; real data changes are far larger


def same_values(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-12)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_values(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_values(x, y) for x, y in zip(a, b))
    return a == b


def same_apart_from_timestamps(path: str, old: str, new: str) -> bool:
    if old == new:
        return True
    if not path.endswith(".json"):
        return False
    try:
        a, b = json.loads(old), json.loads(new)
    except ValueError:
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        for key in TIMESTAMPS:
            a.pop(key, None)
            b.pop(key, None)
    return same_values(a, b)


def changed_files() -> list[str]:
    """Modified and untracked files under the build outputs, relative to the repository root."""
    out = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all", "--", *OUTPUTS], cwd=ROOT,
                         check=True, capture_output=True, text=True).stdout
    return sorted(entry[3:] for entry in out.split("\0") if entry)


def real_changes(files: list[str]) -> list[str]:
    real = []
    for path in files:
        committed = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, text=True)
        current = ROOT / path
        if committed.returncode != 0 or not current.exists():
            real.append(path)  # a new or deleted file
        elif not same_apart_from_timestamps(path, committed.stdout, current.read_text(encoding="utf-8")):
            real.append(path)
    return real


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the rebuild changed anything for real")
    args = ap.parse_args(argv)
    env = {**os.environ, **SAVED_EVIDENCE}
    for step in STEPS:
        print("Running: " + " ".join(step), file=sys.stderr, flush=True)
        subprocess.run([sys.executable, *step], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    files = changed_files()
    real = real_changes(files)
    if files and not real:
        subprocess.run(["git", "checkout", "--", *files], cwd=ROOT, check=True)
    for path in real:
        print(f"changed: {path}")
    print(f"{len(real)} site files changed; kept every rebuilt file" if real else "No change beyond build timestamps")
    return 1 if args.check and real else 0


if __name__ == "__main__":
    sys.exit(main())
