# Phase 2: more sites with measured activity

Phase 1 is in `docs/ASTRA_TODO.md` (A1–A11, all merged or closed) and `docs/LOG.md`. Same conventions: Astra branches
`astra/b<N>`, Claude `claude/*`, Stuart merges or delegates, both agents log to `docs/LOG.md`, never commit `.env` or
`secrets/`, official national statistics are inputs to test and never evidence.

## The problem

Of 103 public sites, one shows "fuel burning measured on site" (Colossus 2, calibrated NOx flux), one shows combustion
detected by the plume test (Abilene), and four carry operator-reported annual loads (Meta Prineville, Luleå, New Albany;
ORNL Frontier). Every other "running" line is a documented capacity times a prior. The map draws all of these except
Colossus 2 in the same blue. Goal for this phase: at least fifteen sites whose activity rests on a measurement or an
operator/regulator figure, every AI campus with on-site generation covered, and a map that shows which kind of evidence
each site has.

## Evidence kinds (what the map will distinguish after B6)

- **measured**: calibrated NOx flux at a self-generating site; a dedicated plant's CAMPD hourly generation; an operator's
  annual electricity; an annual load derived from published water use.
- **detected**: plume test change ≥ 2.5σ at the documented start; night-lights energisation; radar or optical construction.
- **presumed**: documented capacity × prior only.
- **construction**: roofs on, nothing else.

## Astra tasks

### B1. On-site generation inventory from permits  [no-EE for the research, EE for the flux runs]
Status: in progress (astra/b1; permit audit and cached-profile monthly replay)
Data centres that burn their own fuel are directly measurable from TROPOMI (Colossus 2: 1,020 ± 180 kg NOx/h). Find every
campus with on-site turbines or engines ≥ 50 MW, from air-permit registries (TCEQ, MDEQ, LDEQ, Ohio EPA, Wyoming DEQ,
Arizona DEQ, Alberta) and company statements, and record: site, fuel, MW, control technology (SCR or not), permit id and
URL, first-fire date, NOx limit. Candidates reported in press and to be verified, not assumed: xAI Colossus 1 turbine phase
(Memphis, 2024–25), Crusoe/Oracle Abilene (turbines with SCR; below detection so far), Fermi America (Amarillo), Vantage
Frontier (Shackelford County TX), Poolside/CoreWeave West Texas, Crusoe Cheyenne, Wonder Valley (Alberta), any VoltaGrid
or ProEnergy fleet serving a campus. Write `data/onsite_generation.csv`, add `sites.csv` rows with `nox_ef_lo/hi` from the
permit (uncontrolled simple-cycle 0.5–1.5 kg/MWh; SCR ≤ 0.1), then for each operating one run
`tools/no2_flux.py` and `tools/no2_flux_quarterly.py monthly` exactly as for Colossus 2 and record the verdict (detected /
below detection) in the notes. Accept: the table with URLs; a monthly NOx series per operating site; each verdict in
`docs/LOG.md`. Colossus 1 is Claude's (C2) because of the TVA plant next door.

### B2. Dedicated power plants → EPA CAMPD  [no-EE]
Where a campus is supplied by a named plant that reports hourly to CAMPD, the plant's generation is the campus load to
within the contracted share. Build `data/campus_plant_links.csv` (site_id, ORIS id, plant name, contracted share, source
URL, from date) starting with Meta Hyperion (Entergy Louisiana's three combined-cycle units, when they report) and any
plant in B1 that is grid-connected and reports; write `tools/campd_monthly.py` (reuse `tools/campd_hourly.py`) producing
`results_no2/campd_<site>_monthly.csv` (MWh, hours, NOx); add a `dedicated_plant_measured` basis (tier A1) used by
`build_timeline_data.py` when the share is ≥ 0.8, otherwise an evidence strip only. Accept: links table with URLs; the
build shows "yes: dedicated plant generated N MW average" for at least one site once data exists, and the code path is
tested on Southaven CC (ORIS 6641... verify) as a non-dedicated example that must NOT become a campus load.

### B3. Annual loads from published water use  [no-EE]
Google publishes per-site water withdrawal and consumption (2023 report onward) and fleet WUE; Meta publishes per-site
water; Microsoft publishes FY25 electricity and water by metro. Water ÷ WUE gives an annual energy for water-cooled
campuses. Extend `data/operator_disclosures.csv` and `tools/ingest_disclosures.py` (A11) with `water_derived_annual`
rows (tier A2, band ±30 %), attributing Microsoft metros to campuses only where a metro is one campus. Accept: ≥ 10 sites
with an annual load figure and source URLs; the derivation and WUE assumptions in `docs/operator_disclosures_notes.md`.

### B4. Municipal water records  [no-EE]
Cities that supply water-cooled campuses sometimes publish or release monthly volumes (The Dalles, Mesa, Council
Bluffs, Bluffdale, Prineville, Lenoir, Clarksville, Papillion). Collect what is public with URLs into
`data/water_monthly.csv`; monthly series become an evidence strip ("water use, monthly"). Accept: whatever exists, with a
note per city on what was searched and what was not public.

### B5. Regional data-centre load context  [no-EE]
Utility and ISO reports of aggregate data-centre load (Dominion, AEP Ohio, ERCOT large flexible load, PJM, EirGrid,
Singapore EMA) into `data/regional_dc_load.csv` with URLs, for the docs and for testing the inventory's regional totals.
Not per site.

### B6. Map: show the evidence kind  [no-EE]
`build_status.py` gains an `evidence_kind` field (measured / detected / presumed / construction) with the rules above;
`site/mapmin.js` and `site/cards.js` draw measured in orange, detected in a second colour, presumed in blue, construction
white, with the legend updated; `list.html` gets a filter by kind; the default map view fits all markers. Accept: Abilene
and the operator-reported sites no longer look presumed; a synthetic test per kind in `tests/`.

## Claude tasks

- **C1 (running)**: batch plume test over every inventory site with a documented or roof-derived start date
  (`tools/plume_batch.py` → `results_no2/<site>.csv`, summary in `results_no2/plume_batch_summary.csv`); sites at ≥ 2.5σ
  go to a flux run.
- **C2 (done, negative)**: Colossus 1 with Allen and Southaven subtracted: turbine-period step 62 ± 63 kg NOx/h, no month
  above 2.5σ; the turbine phase stays undetected (see `docs/LOG.md`, `results_no2/colossus1_subtraction.json`).
- **C3 (done, negative)**: night thermal at the documented gigawatt-class loads: Rainier +0.06 ± 0.24 K at 1,078 MW, Abilene
  +0.13 ± 0.47 K at 522 MW; only Colossus 1's turbine-yard block shows a night step (`docs/LOG.md`, `results_eco/`).
- **C4**: plume-test detection threshold: seasonal matching and longer baselines, false-positive rate measured on the
  nine control roofs and forty industrial blobs, so "detected" can be claimed below 2.5σ where justified.
- **C5**: classifier recalibration with the labels from phase-1 A8 and the optical review, then scores in the site JSON.
