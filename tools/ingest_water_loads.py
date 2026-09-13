"""Turn water-derived annual loads (data/water_derived_loads.csv, phase-2 task B3) into capacity-timeline rows,
idempotently. Only rows whose method is a valid consumption/WUE derivation are used; air-cooled and negligible-water
rows are skipped. The figure is the operator's published water consumption divided by its (implied) fleet WUE, giving
IT energy, times PUE for facility energy; here the IT average is stored (basis water_derived_it_annual, tier A2).
Validation against Meta's actual electricity reproduces a site's load only to about a factor of two, so the builder
gives these rows a 0.5x-2x band. Where one water row covers two campuses the note says so (upper bound for the site).

    python tools/ingest_water_loads.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASIS = "water_derived_it_annual"


def main():
    w = pd.read_csv(ROOT / "data" / "water_derived_loads.csv")
    tl = pd.read_csv(ROOT / "data" / "capacity_timeline.csv", dtype=str).fillna("")
    sites = pd.read_csv(ROOT / "data" / "sites.csv")
    have_elec = set(tl[tl.capacity_basis == "facility_measured_annual"].site_id)
    ok = w[w.method.str.startswith(("consumption/", "withdrawal/")) & w.energy_gwh_estimate.notna() & w.site_id.isin(sites.site_id)]
    ok = ok[~ok.site_id.isin(have_elec)]  # reported electricity beats a water derivation
    rows = []
    for _, r in ok.iterrows():
        y = int(r.year)
        it_mw = float(r.energy_gwh_estimate) * 1000 / 8760 / float(r.pue)
        merged = any(k in str(r.note) for k in ("both", "two campuses", "Whole Mayes County", "One water row"))
        rows.append(dict(site_id=r.site_id, valid_from=f"{y}-01-01", valid_to=f"{y}-12-31", capacity_mw=f"{it_mw:.1f}", capacity_basis=BASIS, tier="A2",
                         source=f"{r.operator} environmental report: {float(r.water_consumed_ML):,.0f} ML water consumed in {y} ÷ WUE {float(r.wue_l_per_kwh):.2f} L/kWh ({r.wue_scope}) = {float(r.energy_gwh_estimate):,.0f} GWh facility, PUE {float(r.pue):.2f}",
                         url=str(r.source_url),
                         notes=("Annual average IT load derived from published water use; validated to about x2 against Meta's electricity. " + ("Upper bound: one water row covers two campuses. " if merged else "") + str(r.note)[:160])))
    new = pd.DataFrame(rows, columns=tl.columns.tolist())
    keep = ~((tl.capacity_basis == BASIS) & tl.set_index(["site_id", "valid_from"]).index.isin(new.set_index(["site_id", "valid_from"]).index))
    out = pd.concat([tl[keep], new], ignore_index=True)
    out.to_csv(ROOT / "data" / "capacity_timeline.csv", index=False)
    print(f"timeline rows {len(tl)} -> {len(out)}; water-derived rows {int((out.capacity_basis == BASIS).sum())} for {out[out.capacity_basis == BASIS].site_id.nunique()} sites")


if __name__ == "__main__":
    main()
