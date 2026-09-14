"""Audit saved B8 plant emissions and report provenance; never infer campus load.

Run: python tools/cn_stack_monitors.py
Only annual report totals currently exist. This is not a live hourly scraper.
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(root=ROOT):
    directory = root / "data/cn_stack_monitors"
    sources = json.loads((root / "data/cn_stack_monitor_sources.json").read_text())
    reports = {}
    for source in sources["requests"]:
        if "retained_file" not in source:
            continue
        payload = (root / source["retained_file"]).read_bytes()
        if not payload.startswith(b"%PDF"):
            raise ValueError(f"Not a PDF: {source['key']}")
        if hashlib.sha256(payload).hexdigest() != source["sha256"]:
            raise ValueError(f"Source hash mismatch: {source['key']}")
        reports[source["url"]] = source
    groups = defaultdict(dict)
    used_reports = set()
    count = 0
    for path in sorted(directory.glob("shengle_*.csv")):
        for row in csv.DictReader(path.open()):
            start, end = date.fromisoformat(row["period_start"]), date.fromisoformat(row["period_end"])
            if (start.month, start.day, end.month, end.day) != (1, 1, 12, 31) or start.year != end.year:
                raise ValueError(f"Not a complete annual reporting period: {path}")
            if row["resolution"] != "annual" or row["unit"] != "metric_tonne":
                raise ValueError(f"Unexpected period or unit: {path}")
            if row["metric"] != "reported_emission_mass" or row["basis"] != "operator_annual_monitoring_report":
                raise ValueError(f"Unexpected evidence basis: {path}")
            if row["pollutant"] not in {"SO2", "NOx", "particulate_matter"}:
                raise ValueError(f"Unknown pollutant: {path}")
            source = reports[row["source_url"]]
            if row["plant_id"] != "shengle" or source["key"] != f"shengle_annual_{start.year}":
                raise ValueError(f"Plant/report year mismatch: {path}")
            if path.name != f"shengle_{start.year}.csv":
                raise ValueError(f"Reporting period/file mismatch: {path}")
            used_reports.add(row["source_url"])
            if row["source_sha256"] != source["sha256"] or int(row["source_pdf_page"]) < 1:
                raise ValueError(f"Invalid provenance: {path}")
            value = Decimal(row["value"])
            if not value.is_finite() or value < 0:
                raise ValueError(f"Invalid reported mass: {path}")
            group = groups[(row["plant_id"], start.year, row["pollutant"])]
            if row["unit_label"] in group:
                raise ValueError(f"Duplicate unit record: {path}")
            group[row["unit_label"]] = (value, row["reconciliation_status"])
            count += 1
    mismatches = []
    for key, group in groups.items():
        if set(group) != {"unit_1", "unit_2", "whole_plant"}:
            raise ValueError(f"Missing reporting scope: {key}")
        difference = group["whole_plant"][0] - group["unit_1"][0] - group["unit_2"][0]
        expected = "source_total_mismatch" if difference else "matches"
        if any(flag != expected for _, flag in group.values()):
            raise ValueError(f"Unflagged or incorrectly flagged reconciliation: {key}")
        if difference:
            mismatches.append({"plant": key[0], "year": key[1], "pollutant": key[2],
                               "reported_total_minus_units_tonnes": str(difference)})
    if not groups:
        raise ValueError("No report records")
    expected_reports = {url for url, source in reports.items() if source["key"].startswith("shengle_annual_")}
    if used_reports != expected_reports:
        raise ValueError("A retained annual report has no observations")
    links = list(csv.DictReader((root / "data/cn_plant_links.csv").open()))
    if any(r["campus_load_eligible"] != "false" for r in links):
        raise ValueError("B8 audit has no validated campus load allocation")
    return {"records": count, "plant_year_pollutants": len(groups), "retained_pdfs": len(reports),
            "hubs": len({r["hub_id"] for r in links}), "source_total_mismatches": mismatches,
            "hourly_or_daily_records": 0, "campus_load_promotions": 0}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2), file=sys.stderr)
