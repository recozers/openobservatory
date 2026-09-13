"""Validate regional context and audit disclosed inventory energy; never feed site estimates.

Run: python tools/regional_load.py [--output path.json]
Only Ireland has both a country membership key and a DC-only metered annual
series in this register. The resulting ratio is context, not an accuracy score:
operator facility electricity and CSO grid meters have different boundaries.
"""
import argparse
import calendar
import csv
import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = {
    "contract_capacity": {"MW"},
    "operational_capacity": {"MW", "GW"},
    "capacity_target_increment": {"MW"},
    "forecast_demand_increment": {"GW"},
    "apparent_demand": {"MVA"},
    "forecast_apparent_demand": {"MVA"},
    "annual_electricity_energy": {"GWh", "TWh"},
}


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def validate(rows):
    seen = set()
    for r in rows:
        rid = r["record_id"]
        if not rid or rid in seen:
            raise ValueError(f"duplicate/empty record id: {rid}")
        seen.add(rid)
        for field in ("region_id", "geography_scope", "sector_scope", "publisher",
                      "source_url", "source_locator", "notes", "source_vintage"):
            if not r[field].strip():
                raise ValueError(f"{rid}: missing {field}")
        if not r["source_url"].startswith("https://") or r["use"] != "context_only":
            raise ValueError(f"{rid}: requires source URL and context-only use")
        if r["unit"] not in METRICS.get(r["metric"], set()):
            raise ValueError(f"{rid}: incompatible metric/unit")
        value = float(r["value"])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{rid}: invalid value")
        if r["qualifier"] not in {"reported", "approximate", "greater_than", "at_least", "up_to_approximate"}:
            raise ValueError(f"{rid}: invalid qualifier")
        for field in ("as_of", "period_start", "period_end", "retrieved_on"):
            if r[field]:
                date.fromisoformat(r[field])
        if bool(r["period_start"]) != bool(r["period_end"]):
            raise ValueError(f"{rid}: incomplete period")
        if r["period_start"] > r["period_end"]:
            raise ValueError(f"{rid}: reversed period")
        if r["metric"] == "annual_electricity_energy":
            start, end = r["period_start"], r["period_end"]
            if not start.endswith("-01-01") or end != start[:4] + "-12-31":
                raise ValueError(f"{rid}: annual energy needs an exact calendar year")
    return rows


def audit(rows, sites, disclosures):
    validate(rows)
    ids = [s["site_id"] for s in sites]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate inventory site id")
    # No utility territories inferred from states or lat/lon bounding boxes.
    ireland = {s["site_id"] for s in sites if s["country"] == "IE"}
    energy = {}
    for d in disclosures:
        if d["site_id"] not in ireland or d["metric"] != "electricity_mwh":
            continue
        key = (d["site_id"], int(d["year"]))
        value = float(d["value"])
        if key in energy:
            raise ValueError(f"duplicate facility/year electricity disclosure: {key}")
        if d["unit"] != "MWh" or not d["source_url"].startswith("https://") or not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid electricity disclosure: {key}")
        energy[key] = value

    results = []
    for r in rows:
        item = {"record_id": r["record_id"], "status": "not_comparable",
                "reason": "Different metric, sector, or unverified utility-territory membership."}
        if (r["region_id"], r["sector_scope"], r["metric"]) == ("ireland", "data_centres", "annual_electricity_energy"):
            year = int(r["period_start"][:4])
            included = sorted(s for s in ireland if (s, year) in energy)
            regional_mwh = float(r["value"]) * {"GWh": 1000, "TWh": 1_000_000}[r["unit"]]
            facility_mwh = sum(energy[s, year] for s in included) if included else None
            hours = (366 if calendar.isleap(year) else 365) * 24
            item = dict(record_id=r["record_id"], year=year,
                        status="partial_inventory_context" if included else "no_disclosures",
                        source_url=r["source_url"], regional_grid_mwh=regional_mwh,
                        regional_grid_average_mw=round(regional_mwh / hours, 3),
                        inventory_facility_mwh=facility_mwh,
                        facility_to_regional_grid_ratio=round(facility_mwh / regional_mwh, 6)
                        if facility_mwh is not None and regional_mwh else None,
                        included_sites=included, inventory_sites_without_disclosure=sorted(ireland - set(included)),
                        review_exceeds_regional_grid=facility_mwh > regional_mwh if included else None,
                        reason="Partial campus roster; facility electricity vs national grid meters. Ratio is context, not coverage or accuracy; no rescaling.")
        results.append(item)
    return {"use": "context_only", "records": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(read_csv(ROOT / "data/regional_dc_load.csv"),
                   read_csv(ROOT / "data/sites.csv"), read_csv(ROOT / "data/operator_disclosures.csv"))
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
