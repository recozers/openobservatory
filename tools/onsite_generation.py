"""Audit the B1 register and replay existing daily NO2 profiles without an EE download.

python tools/onsite_generation.py --replay
Fresh profiles use tools/no2_flux.py with the source coordinates and date range;
this replay uses that module's same composite fit and quarterly module's monthly method.
The register includes unresolved leads: it is not a count of operating campuses.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from no2_flux import estimate
from no2_flux_quarterly import monthly


def audit(rows, site_ids):
    ids = [r["record_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate generation record")
    for r in rows:
        if not r["source_url"].startswith("https://"):
            raise ValueError(f"Missing source: {r['record_id']}")
        if r["site_id"] and r["site_id"] not in site_ids:
            raise ValueError(f"Unknown inventory site: {r['site_id']}")
        if r["generation_mw"] and (not r["generation_basis"] or float(r["generation_mw"]) <= 0):
            raise ValueError(f"Generation needs a positive value and explicit basis: {r['record_id']}")
        if r["nox_ef_basis"] == "permit_upper_limit" and r["nox_ef_lo"]:
            raise ValueError("A permit ceiling does not establish a lower emission factor")
        if r["profile"] and not r["site_id"]:
            raise ValueError("A flux profile must link to an existing study site")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()
    with (ROOT / "data/onsite_generation.csv").open() as f:
        rows = list(csv.DictReader(f))
    sites = pd.read_csv(ROOT / "data/sites.csv")
    audit(rows, set(sites.site_id))
    print(f"Validated {len(rows)} generation records, including planned and unresolved leads", file=sys.stderr)
    if not args.replay:
        return
    records = []
    for r in rows:
        if not r["profile"]:
            continue
        path = ROOT / r["profile"]
        piv = pd.read_csv(path, index_col=0)
        piv.columns = [float(c) if c.replace("-", "").replace(".", "").isdigit() else c for c in piv.columns]
        if piv.index.duplicated().any():
            raise ValueError(f"Duplicate observation dates: {path}")
        result = estimate(piv, list(range(-12000, 30001, 2000)), 12000,
                          r["record_id"] + " cached daily profiles")
        # This is the repository's established monthly method and calibration.
        monthly(path, r["site_id"], r["baseline_before"] or None)
        output = ROOT / "results_no2" / f"flux_{r['site_id']}_monthly.csv"
        m = pd.read_csv(output, index_col=0)
        post = m[m.index >= r["baseline_before"][:7]]
        z = (post.nox_kgh_cal / post.nox_se.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
        n = int((z >= 2.5).sum())
        records.append(dict(record_id=r["record_id"], site_id=r["site_id"], profile=r["profile"],
                            profile_sha256=digest(path), observation_start=str(piv.index.min()),
                            observation_end=str(piv.index.max()), observation_days=len(piv),
                            baseline_before=r["baseline_before"], monthly_output=str(output.relative_to(ROOT)),
                            monthly_sha256=digest(output), post_baseline_months=len(post),
                            months_ge_2_5_sigma=n, maximum_monthly_z=round(float(z.max()), 3),
                            monthly_screen="detected" if n else "below_detection",
                            composite_fit=result,
                            caveat="Monthly screen uses the existing conditional baseline SE and coal calibration; it is not an independent source-attribution test or a measured IT-load verdict. First-fire dates remain unverified."))
    result = dict(calibration_sha256=digest(ROOT / "results_no2/calibration_plateau.json"),
                  method="tools/no2_flux.py estimate; tools/no2_flux_quarterly.py monthly", records=records)
    (ROOT / "results_no2/onsite_generation_audit.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Wrote results_no2/onsite_generation_audit.json", file=sys.stderr)


if __name__ == "__main__":
    main()
