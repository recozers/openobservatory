"""Turn operator electricity disclosures into capacity-timeline rows, idempotently (phase-1 task A11).

    python tools/ingest_disclosures.py            # reads data/operator_disclosures.csv, updates data/capacity_timeline.csv

Each electricity_mwh row (site_id, year, value, source_url, source_table) becomes one row with basis
facility_measured_annual, tier A2, capacity_mw = MWh / 8760 (the year's average facility load), valid for that calendar
year. Rows already present for the same site, year and basis are replaced, so the script can run after every new
disclosure without duplicating anything. Sites not in data/sites.csv are skipped and listed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASIS = "facility_measured_annual"


def main():
    disc = pd.read_csv(ROOT / "data" / "operator_disclosures.csv")
    tl = pd.read_csv(ROOT / "data" / "capacity_timeline.csv", dtype=str).fillna("")
    sites = set(pd.read_csv(ROOT / "data" / "sites.csv").site_id)
    e = disc[(disc.metric == "electricity_mwh") & disc.value.notna()].copy()
    e["year"] = pd.to_numeric(e.year, errors="coerce")
    e = e.dropna(subset=["year"])
    skipped = sorted(set(e[~e.site_id.isin(sites)].site_id))
    e = e[e.site_id.isin(sites)]
    rows = []
    for _, r in e.iterrows():
        y = int(r.year)
        it_only = "ORNL" in str(r.operator) or "Frontier" in str(r.note)  # a system's own metered energy is IT, not facility
        if it_only and ((tl.site_id == r.site_id) & (tl.valid_from == f"{y}-01-01") & (tl.capacity_basis == "it_measured_annual")).any():
            continue
        rows.append(dict(site_id=r.site_id, valid_from=f"{y}-01-01", valid_to=f"{y}-12-31", capacity_mw=f"{float(r.value) / 8760:.1f}",
                         capacity_basis="it_measured_annual" if it_only else BASIS, tier="A1" if it_only else "A2",
                         source=f"{r.operator} per-site annual electricity disclosure: {int(float(r.value)):,} MWh in {y} ({r.source_table})",
                         url=str(r.source_url), notes="Whole-campus metered electricity divided by 8760 h: the average facility load for the year, not a peak or a capacity. IT load = this / PUE."))
    new = pd.DataFrame(rows, columns=tl.columns.tolist()) if rows else pd.DataFrame(columns=tl.columns)
    keep = ~((tl.capacity_basis == BASIS) & tl.set_index(["site_id", "valid_from"]).index.isin(new.set_index(["site_id", "valid_from"]).index))
    out = pd.concat([tl[keep], new], ignore_index=True)
    out.to_csv(ROOT / "data" / "capacity_timeline.csv", index=False)
    print(f"timeline rows {len(tl)} -> {len(out)}; measured-annual rows now {int((out.capacity_basis == BASIS).sum())} for {out[out.capacity_basis == BASIS].site_id.nunique()} sites")
    if skipped:
        print("disclosed but not in the inventory (add sites to use them):", ", ".join(skipped), file=sys.stderr)


if __name__ == "__main__":
    main()
