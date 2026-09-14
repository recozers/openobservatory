# Phase 2: more sites with measured activity

Phase 1 is in `docs/ASTRA_TODO.md` (A1–A11, all merged or closed) and `docs/LOG.md`. Same conventions: Astra branches
`astra/b<N>`, Claude `claude/*`, Stuart merges or delegates, both agents log to `docs/LOG.md`, never commit `.env` or
`secrets/`, official national statistics are inputs to test and never evidence.

**Priority from Stuart, 14 Sep: focus more on China; US observability is already much better. The goal is utilisation, not
power draw, and ideally telling training from inference, at the highest time resolution possible. Planned workload method:
deep learning on high-resolution thermal imagery of substations and transformers, labelled with AI labs' training-run records. Labels given in confidence are allowed under the conditions in README's
provenance rule; they stay in the git-ignored `data/private/`.** Prefer China tasks when
choosing what to do next. Outside contributors donate agent sessions against `REQUESTS_FOR_WORK.md`. RFW-21, RFW-12 and RFW-13 there are this
brief's B7, B8 and B9, marked reserved for Astra (renumbered 14 Sep). Before starting any other task, search open pull requests for an
`[RFW-NN]` claim on the same work; if you finish or drop B7, B8 or B9, update its Status in that file.

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
Status: initial pass merged (PR #8); unresolved candidate permits/first fire/geometry remain in the register notes.
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
Status: implemented on astra/b2; 42 Southaven plant-months verified, evidence-only negative control passes. Real dedicated-supply promotion awaits verified reporting IDs and physical allocation; see `docs/campd_plant_links.md`.
Where a campus is supplied by a named plant that reports hourly to CAMPD, the plant's generation is the campus load to
within the contracted share. Build `data/campus_plant_links.csv` (site_id, ORIS id, plant name, contracted share, source
URL, from date) starting with Meta Hyperion (Entergy Louisiana's three combined-cycle units, when they report) and any
plant in B1 that is grid-connected and reports; write `tools/campd_monthly.py` (reuse `tools/campd_hourly.py`) producing
`results_no2/campd_<site>_monthly.csv` (MWh, hours, NOx); add a `dedicated_plant_measured` basis (tier A1) used by
`build_timeline_data.py` when the share is ≥ 0.8, otherwise an evidence strip only. Accept: links table with URLs; the
build shows "yes: dedicated plant generated N MW average" for at least one site once data exists, and the code path is
tested on Southaven CC (verified ORIS 55269; 6641 is Independence AR) as a non-dedicated example that must NOT become a campus load.

### B3. Annual loads from published water use  [no-EE]  — done by Claude 13 Sep (see LOG); remaining: Microsoft metro attribution
Google publishes per-site water withdrawal and consumption (2023 report onward) and fleet WUE; Meta publishes per-site
water; Microsoft publishes FY25 electricity and water by metro. Water ÷ WUE gives an annual energy for water-cooled
campuses. Extend `data/operator_disclosures.csv` and `tools/ingest_disclosures.py` (A11) with `water_derived_annual`
rows (tier A2, band ±30 %), attributing Microsoft metros to campuses only where a metro is one campus. Accept: ≥ 10 sites
with an annual load figure and source URLs; the derivation and WUE assumptions in `docs/operator_disclosures_notes.md`.

### B4. Municipal water records  [no-EE]
Status: public-source audit implemented on astra/b4 (stacked on PR #9): all eight cities checked; Bluffdale municipal/customer/return records retained as four separate series, 312 monthly observations. Other cities have no attributable monthly series established; access limitations and non-campus aggregates documented in `docs/water_monthly_notes.md`.
Cities that supply water-cooled campuses sometimes publish or release monthly volumes (The Dalles, Mesa, Council
Bluffs, Bluffdale, Prineville, Lenoir, Clarksville, Papillion). Collect what is public with URLs into
`data/water_monthly.csv`; monthly series become an evidence strip ("water use, monthly"). Accept: whatever exists, with a
note per city on what was searched and what was not public.

### B5. Regional data-centre load context  [no-EE]
Status: ready for review (astra/b5, based on astra/b2). 38 sourced records across all six areas; contracts,
forecasts, MVA and actual annual energy kept separate. Independent Irish disclosure/context audit and six tests;
no site evidence or load changes. See `docs/regional_dc_load_notes.md`. Singapore EMA has only an all-sector
energy total in the inspected chapter; IMDA capacity context is separately labelled. Other utility comparisons
remain unavailable without verified service-territory membership and compatible observed demand.
Utility and ISO reports of aggregate data-centre load (Dominion, AEP Ohio, ERCOT large flexible load, PJM, EirGrid,
Singapore EMA) into `data/regional_dc_load.csv` with URLs, for the docs and for testing the inventory's regional totals.
Not per site.

### B6. Map: show the evidence kind  [no-EE]  — done (merged 14 Sep)
Claude supplied the five evidence categories and colours and the quarterly detail page. Astra added the list filter,
labelled swatches, result counts, measured-first sorting, default map fit with mobile legend layout, and backend plus
frontend tests. Explicit map deep links and unconfirmed radar status are preserved. See LOG 14 September.
`build_status.py` gains an `evidence_kind` field (measured / detected / presumed / construction) with the rules above;
`site/mapmin.js` and `site/cards.js` draw measured in orange, detected in a second colour, presumed in blue, construction
white, with the legend updated; `list.html` gets a filter by kind; the default map view fits all markers. Accept: Abilene
and the operator-reported sites no longer look presumed; a synthetic test per kind in `tests/`.


### B7. Watch list for generator fleets under construction  [EE for the monthly runs]
Status: in progress (astra/b7; two filing-located watches; seven plant records still pending)

14 September: Fermi and Cheyenne power-site points have monthly watch pipelines. Cheyenne's filed traffic study expects power operation by 2030, separately from the data centre's 2027 target. No first-fire date or two-sided operating emission factor has been verified for these watches; no campus MW is inferred. See `docs/generator_watchlist.md` for the nine-record audit and remaining gaps.

B1's register shows that, apart from Colossus 2, Abilene (SCR) and the historical Colossus 1, every on-site generation
fleet in scope is planned or under construction for 2026–2028 (Fermi Matador, Vantage Frontier, Poolside Horizon, Cheyenne
Project Jade, Ohio Apollo, Wonder Valley, Entergy's Hyperion plants). Add each as a site with `site_class=generator_planned`,
coordinates from the permit or siting filing, the permit emission factor, and the expected first-fire date; give them a
flux profile and a monthly series in `data/refresh_flux_sources.csv` so the refresh runs them every month; the map shows
them as "watching: generator fleet under construction" until the calibrated NOx exceeds 2σ and 100 kg/h, when they turn
orange automatically. Accept: the watch list on the map with a documented first-fire target per site; a monthly NOx
series per site from the refresh; the first detection recorded in `docs/LOG.md`.

### B8. China: dedicated plants and public stack monitors  [no-EE]
Status: in progress (astra/b8; eleven-hub source/access audit and 63 annual Shengle emission records; hourly/daily collection blocked by CAPTCHA or inaccessible endpoints).

14 September: `docs/cn_stack_monitors.md` records fourteen plant/supply leads across all eleven hubs and nine provincial
access outcomes. Shengle's seven annual reports and current monitoring plan are retained; its automatic readings require
a CAPTCHA. Liangjiang has an operator-described waste-heat cooling link, without verified electrical allocation. Renewable
source-grid-load-storage projects have no combustion stacks. No campus load is promoted; the hourly/daily acceptance
criterion remains unmet. The 2024 annual NOx report's five-tonne total discrepancy is preserved and flagged.

Chinese hub campuses have no operator disclosure and no self-generation, but several sit beside plants built for them
(源网荷储一体化 projects, park cogeneration) and large plants publish hourly stack monitoring (重点排污单位自动监测数据: SO₂,
NOx, flue-gas flow per outlet) on provincial platforms. That is the plant's own monitor, not a statistic, and the analogue
of EPA CAMPD. For each hub (Ulanqab, Horinger, Zhangbei, Zhongwei, Qingyang, Gui'an, Chongqing Shuitu, Tianfu, Wuhu,
Shaoguan, Zhangjiakou/Huailai): identify plants dedicated to or physically inside the data-centre park (EIA documents,
grid-connection notices, park plans), find whether their hourly monitor data is public (platform URL, outlet ids, how far
back), and pull what exists into `data/cn_stack_monitors/<plant>_<year>.csv`. Accept: a table of hub → plant → dedication
evidence → monitor URL; hourly or daily series for every plant with public data; a note on which platforms block access.

### B9. China: operator utilisation priors from filings  [no-EE]
VNET, GDS and Chindata report company-wide utilisation of in-service capacity (70–80 %) in SEC filings; where a campus's
operator is known (VNET Ulanqab, GDS Ulanqab, Chindata Zhangjiakou/Datong), that figure is the utilisation prior with
provenance. Add `operator_utilisation` rows to `data/cn_operator_disclosures.csv` per filing period and let
`build_timeline_data.py` use the operator's latest reported utilisation (±10 points) instead of the generic cloud prior for
those sites. Accept: priors applied to every Chinese site with a known listed operator; the basis text names the filing.

## Claude tasks

- **C1 (done, corrected 14 Sep)**: plume test over 33 sites. Per series, none of 31 campuses without known on-site generation
  reached 2.5σ (highest 2.09); Abilene (SCR turbines) 2.80σ; Colossus 2 9.84σ (`results_no2/plume_batch_zscores_by_series.csv`).
- **C2 (done, negative)**: Colossus 1 with Allen and Southaven subtracted: turbine-period step 62 ± 63 kg NOx/h, no month
  above 2.5σ; the turbine phase stays undetected (see `docs/LOG.md`, `results_no2/colossus1_subtraction.json`).
- **C3 (done, negative)**: night thermal at the documented gigawatt-class loads: Rainier +0.06 ± 0.24 K at 1,078 MW, Abilene
  +0.13 ± 0.47 K at 522 MW; only Colossus 1's turbine-yard block shows a night step (`docs/LOG.md`, `results_eco/`).
- **C4 (done, corrected 14 Sep)**: null distribution from 62 control points 0.35° east and west of the sites: z mean −0.29,
  sd 1.38, 95th percentile 1.53, max 2.06, none at 2.5σ. The 2.5σ bar stays; nothing below it is claimed.
- **C5**: classifier recalibration with the labels from phase-1 A8 and the optical review, then scores in the site JSON.
- **C7 (running)**: China coverage from radar: every hall-like radar candidate ≥ 5 ha in the twelve hub boxes becomes an
  inventory entry with its outline, radar structure-on month and classifier score, labelled unconfirmed; eastern hubs
  (Zhangjiakou/Huailai, Wuhu, Shaoguan, Tianfu, Wuqing) scanned as well.
- **C6 (done, inconclusive)**: Dublin's Grange Castle: the box method reads the city's plume (964 ± 96 kg/h, winter peaks),
  not the campus plant; a near-field westerly-wind sector test would be needed (`docs/LOG.md`).
