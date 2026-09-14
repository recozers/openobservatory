# Requests for work

Open Observatory maps data centres worldwide, detects new construction automatically, and estimates how hard they run from
public data. It is built by people who donate their coding agent's attention for a session. This page lists the work that
needs doing and the ideas worth testing. Each request is scoped so an agent can pick it up with no other context.

## Donate a session

1. **Pick one open request** that fits the time you have and the credentials you have. The Size and Keys columns tell you both.
2. **Check nobody has it.** Search the open pull requests for its ID, for example `RFW-07`.
3. **Claim it early.** Fork the repository, push a branch named `rfw/07-short-name`, and open a draft pull request titled
   `[RFW-07] Short title` with your plan in the description. A claim with no new commit for 72 hours lapses.
4. **Deliver against the acceptance line.** A negative result with numbers is a full delivery. Follow `CONTRIBUTING.md`.
5. **Hand off.** Finish the pull request with what changed, the validation numbers, what remains uncertain, and where you
   stopped. Append a dated entry to `docs/LOG.md`. Unfinished work is welcome if the handoff says exactly what is left.

Copy this into your agent to start:

```
You are donating a session to Open Observatory: https://github.com/recozers/openobservatory
Fork and clone it, then read README.md, CONTRIBUTING.md and REQUESTS_FOR_WORK.md.
Pick one open request that fits about <N> hours and needs only these credentials: <none | Earth Engine | EPA | Earthdata>.
Search open pull requests for its ID. If it is free, claim it with a draft pull request titled "[RFW-NN] <title>".
Keep every number traceable to a public source and a script. Before you finish, run:
python -m unittest discover -s tests; node --test tests/frontend_evidence.test.cjs; python tools/refresh.py --dry-run
Record the result in docs/LOG.md, including negative results, and end the pull request with what changed,
validation numbers, remaining uncertainty and where you stopped.
```

**Keys** says what a request needs. `none` needs nothing. `EE` needs Google Earth Engine, free for non-commercial research
with your own Cloud project. `EPA` needs a free api.data.gov key. `Earthdata` needs a free NASA Earthdata login. Put keys in a
local `.env` and never commit them. **Size** is agent time: S is under 2 hours, M is 2 to 6, L is more than 6 and should be
delivered as a first slice.

## Ground rules

- Every public number traces to a free public source, a script in this repository, and a polygon with a stated confidence.
- Official national statistics are inputs to test, never evidence.
- Negative results stay visible. Do not delete a failed method; document it.
- Respect data licences and site terms. Do not scrape services that forbid it, such as map products or commercial
  data-centre directories. Follow the Nominatim usage policy for geocoding.
- A document's figure keeps its own quantity. Do not turn kVA into IT megawatts, add facility and IT figures, or treat a
  forecast as an observed load.

## What already works

Build on these rather than rebuilding them. Details and numbers are in `docs/MVP.md` and `docs/LOG.md`.

- **Roof dating.** Sentinel-2 brightness dates each hall's roof to the month (`tools/s2_roof_timeline.py`).
- **Radar dating and discovery.** Sentinel-1 dates structures through cloud, within 0 to 4 months of the optical date at
  Abilene, and a change scan lists new structures in a 12 km box (`tools/s1_timeline.py`).
- **Hall classifier.** Satellite-embedding features separate data halls from new industrial buildings with a
  leave-one-site-out AUC of 0.977 on 18 positives (`tools/cand_features.py`, `tools/cand_classifier.py`).
- **Fuel burned on site.** Calibrated TROPOMI NOx flux measures generation where a campus runs its own turbines, as at
  Colossus 2 (`tools/no2_flux.py`, `tools/no2_flux_quarterly.py`).
- **Operator disclosures.** Meta reports annual electricity for 18 campuses; Google's published water use gives a load good
  to about a factor of two for 12 more (`tools/ingest_disclosures.py`, `tools/ingest_water_loads.py`).
- **Watches and records.** A generator watch list screens planned turbine fleets monthly (`tools/generator_watchlist.py`);
  EPA plant records and municipal water records attach where they can be attributed (`tools/campd_monthly.py`,
  `tools/water_monthly.py`).
- **Night lights.** VIIRS gives the month a greenfield campus lit up, two to six months after ground-breaking
  (`tools/ntl_timeline.py`).
- **Chips without credentials.** `tools/chip.py` renders a Sentinel-2 true-colour chip for any point from AWS open data.

## Already tried: please do not repeat without a new idea

- **Roof or ground temperature as a load signal.** No response day or night at 12 sites against 9 control roofs, including
  documented gigawatt loads: Rainier +0.06 ± 0.24 K at 1,078 MW. See `docs/overnight_report_2026-09-13.md`.
- **Snow persistence on roofs.** Operating halls hold snow like every other roof at 9 sites over 8 winters.
- **NO₂ at grid-fed campuses.** None of 32 reached 2.5σ. Only campuses that burn fuel on site have a plume.
- **A campus beside a large power plant.** Colossus 1's turbine phase came out at 62 ± 63 kg NOx/h after subtracting the
  neighbouring plants' hourly EPA emissions.
- **A plant on a city's edge.** At Dublin's Grange Castle the box method measured the city's plume, not the campus plant.
- **A classifier trained on OpenStreetMap footprints.** It scored most new industrial buildings as data centres (AUC 0.70).
- **National night-light scans as a detector.** Across the Chinese hub provinces, the 40 brightest newly lit campus-sized
  blobs were factories, ports and chemical plants.
- **Dark-roof dating from vegetation and built-up indices.** The rule failed at Hyperion. See `docs/dark_roof_validation.md`.
- **Radar boxes at six eastern Chinese hubs.** 76 large candidates, none hall-like. The box centres were approximate.
- **One fleet-wide water efficiency figure.** Water-derived load is within a factor of two of Meta's metered electricity,
  no better (Luleå 0.35×, Clonee about 3×). See `docs/water_derived_loads_notes.md`.

## Requests

The Status column shows only standing reservations by the project's own agents. Live claims are open draft pull requests.

| ID | Request | Size | Keys | Status |
|---|---|---|---|---|
| [RFW-01](#rfw-01-confirm-or-reject-the-radar-detected-structures-in-china) | Confirm or reject the radar-detected structures in China | S | none | open |
| [RFW-02](#rfw-02-radar-candidate-scan-around-every-inventory-site) | Radar candidate scan around every inventory site | L | EE | open |
| [RFW-03](#rfw-03-park-boundaries-for-the-eastern-chinese-hubs-then-rescan) | Park boundaries for the eastern Chinese hubs, then rescan | M | none, then EE | open |
| [RFW-04](#rfw-04-multi-storey-data-centre-positives-for-the-classifier) | Multi-storey data-centre positives for the classifier | M | EE | open |
| [RFW-05](#rfw-05-date-dark-and-grey-roofs) | Date dark and grey roofs | M | EE | open |
| [RFW-06](#rfw-06-standby-generator-permits-as-a-capacity-bound) | Standby generator permits as a capacity bound | M | none | open |
| [RFW-07](#rfw-07-per-site-electricity-from-more-operators) | Per-site electricity from more operators | M | none | open |
| [RFW-08](#rfw-08-microsofts-metro-electricity-table-to-campuses) | Microsoft's metro electricity table to campuses | S | none | open |
| [RFW-09](#rfw-09-evidence-for-the-pending-generator-watch-records) | Evidence for the pending generator watch records | M | none | reserved: Astra |
| [RFW-10](#rfw-10-generator-fleet-discovery-from-eia-860m) | Generator fleet discovery from EIA-860M | M | none | open |
| [RFW-11](#rfw-11-near-field-plume-test-for-plants-on-a-citys-edge) | Near-field plume test for plants on a city's edge | M | EE, EPA | open |
| [RFW-12](#rfw-12-qualify-low-stack-nox-calibration-plants) | Qualify low-stack NOx calibration plants | M | none | open |
| [RFW-13](#rfw-13-climate-aware-water-efficiency-for-water-derived-loads) | Climate-aware water efficiency for water-derived loads | M | EE | open |
| [RFW-14](#rfw-14-procurement-tenders-and-awards-for-named-chinese-campuses) | Procurement tenders and awards for named Chinese campuses | M | none | open |
| [RFW-15](#rfw-15-chindatas-per-data-centre-table-and-an-edgar-name-search) | Chindata's per-data-centre table and an EDGAR name search | S | none | open |
| [RFW-16](#rfw-16-dedicated-plants-and-public-stack-monitors-in-china) | Dedicated plants and public stack monitors in China | M | none | reserved: Astra |
| [RFW-17](#rfw-17-operator-utilisation-priors-from-chinese-filings) | Operator utilisation priors from Chinese filings | S | none | reserved: Astra |
| [RFW-18](#rfw-18-implement-the-utilisation-model) | Implement the utilisation model | L | none | open |
| [RFW-19](#rfw-19-load-ramp-curves-from-metas-18-campuses) | Load ramp curves from Meta's 18 campuses | M | EE optional | open |
| [RFW-20](#rfw-20-recalibrate-the-hall-classifier-with-new-labels) | Recalibrate the hall classifier with new labels | M | EE | open after RFW-01 |
| [RFW-21](#rfw-21-construction-timeline-on-the-map) | Construction timeline on the map | M | none | open |
| [RFW-22](#rfw-22-tests-for-the-load-precedence-rules) | Tests for the load precedence rules | S | none | open |
| [RFW-23](#rfw-23-source-link-checker) | Source link checker | S | none | open |

### Inventory and construction

#### RFW-01 Confirm or reject the radar-detected structures in China

- **Why:** 39 inventory entries named `cn_<hub>_r<rank>` are new hall-like structures found by radar, dated, and unconfirmed.
  The map shows them as construction with no load. Each needs a verdict before it counts as a data centre.
- **Do:** For each entry, look at its chip (`results_s1/<hub>_candNN.png`, or render one with `tools/chip.py`) and the
  classifier score in `results_cand/scores.csv`. Classify it as data-hall complex, not a data centre, or unclear, with a
  one-line reason naming what you see: long parallel halls, cooling yards, generator rows, substation. For confirmed halls,
  check the outline in `data/polygons/<site_id>.geojson` against the chip.
- **Deliver:** `data/cn_radar_review.csv` with site_id, verdict, reason and evidence path. Rejected entries leave the public
  inventory but stay in the review file. The site rebuilds and the tests pass.

#### RFW-02 Radar candidate scan around every inventory site

- **Why:** Radar dates construction through cloud and finds unlisted buildings, but it has only run in 18 boxes.
- **Do:** For each site in `data/sites.csv` without a `results_s1/<site_id>_candidates.csv`, run
  `python tools/s1_timeline.py --chip LAT LON --candidates --half 6000 --early 2021 --late 2026 --out results_s1/<site_id>`,
  then score with `tools/cand_features.py` and `tools/cand_classifier.py`. Work region by region.
- **Deliver:** A candidate file per site; a table in `docs/LOG.md` of recall at known halls and the false-positive types by
  region. Stop and report if Earth Engine quotas make a region impractical.

#### RFW-03 Park boundaries for the eastern Chinese hubs, then rescan

- **Why:** Radar boxes at Zhongwei, Zhangjiakou and Huailai, Wuhu, Shaoguan, Chengdu Tianfu and Tianjin Wuqing found nothing
  hall-like, but their centres were approximate.
- **Do:** Find each data-centre park's location or boundary in park plans, environmental impact documents or land transfer
  notices, with URLs. Rescan each located park with the RFW-02 command.
- **Deliver:** `data/cn_hub_parks.csv` with hub, park, coordinates or boundary, source URL and page; rescan results and a
  one-line verdict per hub in `docs/LOG.md`.

#### RFW-04 Multi-storey data-centre positives for the classifier

- **Why:** The classifier learned from single-storey hyperscale halls. Many data centres in eastern China, Singapore,
  Frankfurt and northern Virginia are multi-storey buildings it has never seen.
- **Do:** Assemble at least 30 verified multi-storey data-centre buildings from operator pages or filings, with
  coordinates. Extract features with `tools/cand_features.py`, retrain, and report leave-one-group-out results separately
  for single-storey and multi-storey positives.
- **Deliver:** A labelled positives file with sources, updated scores, and the per-class results in `docs/LOG.md`.

#### RFW-05 Date dark and grey roofs

- **Why:** Brightness dating misses dark membranes and grey roofs, as at Hyperion and Ulanqab. A vegetation and built-up
  index rule already failed (`docs/dark_roof_validation.md`).
- **Do:** Use radar structure-on months as labels and test other Sentinel-2 signals, such as shortwave-infrared change,
  texture or temporal variance. Validate on Hyperion, the Ulanqab long halls and all 12 Abilene halls, and check that
  fallow fields produce no false events.
- **Deliver:** A rule that dates Hyperion's two structures without a false early event and moves no Abilene date by more
  than a month, or a documented failure with the numbers.

#### RFW-06 Standby generator permits as a capacity bound

- **Why:** State air permits list the diesel standby generators at many data centres. Their total rating bounds the facility's
  power, because campuses back up their full load.
- **Do:** For inventory sites in Virginia, Ohio, Texas, Arizona and Georgia, find the air permits and record unit counts,
  ratings, fuel, permit date and URL. Compare total standby MW with documented capacity where both exist.
- **Deliver:** `data/standby_generation.csv` and a note giving the ratio of standby MW to documented capacity across at least
  10 sites. Propose a capacity-bound basis only if the ratio is consistent to within about 30 %.

### Activity and load evidence

#### RFW-07 Per-site electricity from more operators

- **Why:** Operator-reported electricity is the strongest load evidence the site has, and it comes from one operator so far.
- **Do:** Survey sustainability reports and data appendices from Apple, Equinix, Digital Realty, NTT, Iron Mountain, Switch,
  CyrusOne, QTS, Aligned and others for per-site annual electricity or water. Add rows to `data/operator_disclosures.csv`
  with source URL and table, add any missing campuses to the inventory with sourced coordinates, and run
  `tools/ingest_disclosures.py`.
- **Deliver:** A table of which operators publish what, and at what resolution; every new site-year with its source; the site
  rebuilt with the new measured sites.

#### RFW-08 Microsoft's metro electricity table to campuses

- **Why:** Microsoft's 2026 data fact sheet reports fiscal-2025 electricity and water by metro area. Where a metro holds one
  campus, that is a campus figure.
- **Do:** Map each metro row to inventory campuses. Attribute a figure only where the metro is effectively one campus, and
  record the rest as context.
- **Deliver:** Rows in `data/operator_disclosures.csv` with the attribution reasoning, and a note listing the metros left as
  context and why.

#### RFW-09 Evidence for the pending generator watch records

- **Status:** reserved by Astra, who is working on it in `astra/b7`. Listed so nobody duplicates it.
- **Why:** Seven planned on-site generation fleets need filing-located coordinates, a first-fire target and a valid emission
  factor before they can be watched. See `docs/generator_watchlist.md`.

#### RFW-10 Generator fleet discovery from EIA-860M

- **Why:** The watch list was assembled by hand from permits. The US Energy Information Administration's monthly generator
  inventory lists planned and operating generators by plant, which could flag new fleets built for data centres
  automatically.
- **Do:** Parse the latest EIA-860M. Flag planned or new gas turbine and engine plants whose owner, name or location links
  them to a data centre, or that sit within a few kilometres of an inventory site. Verify each flag against a permit or
  company statement.
- **Deliver:** A script, a candidate table with verification notes, and verified candidates proposed for the watch list.
  Coordinate with the RFW-09 claimant before adding watches.

#### RFW-11 Near-field plume test for plants on a city's edge

- **Why:** The box method cannot separate a campus plant from a nearby city's plume, which rules out Dublin and similar
  grid-constrained markets where campuses run gas plants.
- **Do:** Build a sector test within 1 to 5 km that keeps only days when the wind blows from the side away from the city and
  excludes the city from the upwind sector. Validate it first on a US plant at a city's edge with EPA hourly emissions, then
  apply it to Grange Castle.
- **Deliver:** The validation result against EPA truth and, only if validation passes, the Dublin result. A failed validation
  is a full delivery.

#### RFW-12 Qualify low-stack NOx calibration plants

- **Why:** The NOx calibration rests on five tall-stack coal plants. Turbine exhaust leaves from low stacks, so turbine-fed
  campuses need gas references. Three candidates gave factors from 0.9 to 4.8 but are not qualified
  (`docs/low_stack_calibration.md`).
- **Do:** Verify physical stack heights from EIA-860's environmental-equipment data or permits, check isolation from other
  sources with the EPA's point-source inventory, and align the TROPOMI overpass time with the hourly records.
- **Deliver:** Each candidate qualified or rejected with its reason, and the calibration comparison updated for the qualified
  ones.

#### RFW-13 Climate-aware water efficiency for water-derived loads

- **Why:** Water use per unit of energy depends on climate, but the current method applies one fleet-wide figure, which is
  why it is only good to about a factor of two.
- **Do:** Meta publishes both water withdrawal and electricity for 18 campuses. Model withdrawal per unit energy as a function
  of local climate, such as ERA5 wet-bulb temperature, and test it leaving one campus out at a time. Apply it to Google's
  campuses only if it beats the current method.
- **Deliver:** Leave-one-out errors for the current and new methods side by side; updated derived loads and a narrower band
  only if the new method is better.

### China

#### RFW-14 Procurement tenders and awards for named Chinese campuses

- **Why:** Chinese hub campuses publish no electricity figures, but public procurement notices for racks, UPS systems and
  cooling name campuses, quantities and dates.
- **Do:** Search the China Government Procurement Network and the three telecom operators' procurement portals for tenders
  and awards naming campuses at Ulanqab, Horinger, Zhangbei, Zhongwei, Qingyang, Gui'an and Chongqing. Record the campus,
  item, quantity, units, date and URL. These are company procurement records, not statistics.
- **Deliver:** `data/cn_procurement.csv` and a note on what each portal exposes. Use the records as timing and scale
  evidence; do not convert kVA or rack counts into IT megawatts.

#### RFW-15 Chindata's per-data-centre table and an EDGAR name search

- **Why:** Chindata's fiscal-2022 annual report on Form 20-F contains a per-data-centre table with megawatts per campus,
  and VNET's filings mention Ulanqab orders. Neither has been parsed (`docs/cn_operator_disclosures_notes.md`).
- **Do:** Download the filings from EDGAR with a declared User-Agent, parse the table, and run a full-text search for
  Ulanqab, Zhangbei, Horinger, Gui'an and Zhongwei across VNET, GDS and Chindata filings.
- **Deliver:** Every per-campus figure in `data/cn_operator_disclosures.csv` with its filing URL, period and whether it is
  capacity in service, utilised or planned.

#### RFW-16 Dedicated plants and public stack monitors in China

- **Status:** reserved by Astra as the next phase-2 task (B8 in `docs/PHASE2_TODO.md`). Listed so nobody duplicates it.
- **Why:** Plants built for hub parks may publish hourly stack monitoring on provincial platforms, the counterpart of EPA
  plant records.

#### RFW-17 Operator utilisation priors from Chinese filings

- **Status:** reserved by Astra (B9 in `docs/PHASE2_TODO.md`). Listed so nobody duplicates it.
- **Why:** VNET, GDS and Chindata report company-wide utilisation, a sourced prior for campuses whose operator is known.

### Modelling

#### RFW-18 Implement the utilisation model

- **Why:** The site uses fixed rules per evidence type. `docs/utilisation_model.md` defines one model in which every source
  moves the estimate consistently, with stated priors and posteriors per site.
- **Do:** Implement section 7 of that document: hall states, the evidence likelihoods, and Monte Carlo percentiles in a
  pure-Python `utilmodel.py`. Keep the timeline JSON shape so the site needs no change.
- **Deliver:** A first slice covering reported electricity, documented capacity and roofs-only sites, behind a switch, with
  tests showing it reproduces today's bands where the rules are already calibrated.

#### RFW-19 Load ramp curves from Meta's 18 campuses

- **Why:** How fast a campus's load ramps after its halls are built is the biggest unknown prior in the model. Meta's
  electricity series from 2011 to 2024 across 18 campuses measures it.
- **Do:** Date each campus's buildings from Sentinel-2, radar or Landsat for older ones. Fit average load per building-year
  against years since roof-on, with uncertainty.
- **Deliver:** Fitted ramp parameters with uncertainty in `docs/utilisation_model.md`, and the per-campus fits.

#### RFW-20 Recalibrate the hall classifier with new labels

- **Why:** The classifier has 18 positives. RFW-01, RFW-04 and the 78 Epoch campuses with polygons can multiply that.
- **Do:** Add the new labels, retrain with `tools/cand_classifier.py`, and report leave-one-group-out results by region and
  building type. Refresh the scores of existing candidates.
- **Deliver:** Updated `results_cand/scores.csv`, results in `docs/LOG.md`, and a note on any threshold change.

### Site and engineering

#### RFW-21 Construction timeline on the map

- **Why:** Every hall has a structure-on or roof-on month, but the map shows only the present.
- **Do:** Add a year slider to the landing map that shows sites as they were at the end of each year, using the dates
  already in `site/data/timeline/`. Keep it static with no new framework.
- **Deliver:** The slider working at desktop and phone widths, and Node tests in the style of
  `tests/frontend_evidence.test.cjs`.

#### RFW-22 Tests for the load precedence rules

- **Why:** The rules deciding which figure sets a site's load have been extended several times: reported electricity,
  carried averages, water-derived figures, third-party estimates, plant records, radar entries, generator watches.
- **Do:** Write synthetic cases for `cap_in_force`, `utilisation_prior` and the evidence kinds in `build_status.py`,
  covering each basis and each carried-forward case.
- **Deliver:** Tests that fail if any precedence rule changes silently, all passing on `main`.

#### RFW-23 Source link checker

- **Why:** Hundreds of source URLs back the numbers on the site, and links rot.
- **Do:** Write `tools/check_links.py` to read every URL in `data/*.csv` and the source JSON files, check each at a polite
  rate, and look up whether an archived copy exists without submitting new captures.
- **Deliver:** A report of dead links with their archived alternatives, and the script documented in `CONTRIBUTING.md`.

## Theories to explore

Research bets. Each has a first test that fits a session and a condition for stopping. Claim them the same way, as `[T-NN]`.

### T-01 Building permits and occupancy certificates as energisation dates

- **Hypothesis:** US county permit records give the month each building was certified for occupancy, which marks the step
  between a finished building and one drawing load.
- **First test:** Match permit records from counties that publish them as open data, such as Loudoun and Franklin, to
  inventory halls, and compare occupancy dates with radar structure-on and with Meta's load ramp.
- **Keys:** none. **Stop if** fewer than 10 inventory buildings can be matched.

### T-02 Wastewater discharge reports as a monthly cooling series

- **Hypothesis:** Where a campus discharges cooling-tower water under its own federal permit, the EPA's monthly discharge
  monitoring reports give a measured monthly flow that scales with heat rejected.
- **First test:** Search EPA ECHO for permits held by data-centre operators at inventory sites, pull their monthly flows, and
  check the seasonality against wet-bulb temperature and against Meta's electricity where both exist.
- **Keys:** none. **Stop if** no inventory campus holds an individual permit with flow reporting.

### T-03 Counting cooling equipment in public aerial imagery

- **Hypothesis:** USDA's public-domain NAIP aerial imagery, at 0.6 to 1 m, resolves chillers, dry coolers and cooling towers.
  Count times unit capacity from Epoch's equipment catalogues in `data/epoch/` bounds the heat a campus can reject, which
  bounds its IT capacity.
- **First test:** Count units at five US sites with documented capacity and compare.
- **Keys:** EE for NAIP. **Stop if** the estimate misses documented capacity by more than a factor of two.

### T-04 Substation transformer bays as connection capacity

- **Hypothesis:** The number of transformer bays at a campus substation, visible in NAIP, indicates its grid connection
  capacity.
- **First test:** Count bays at campuses with documented connections, such as New Albany's 250 MW and Luleå's 120 MW, and
  compare bays times typical ratings.
- **Keys:** EE for NAIP. **Stop if** ratings vary too much to beat a factor of two.

### T-05 Crane filings as construction-start signals

- **Hypothesis:** The FAA's public obstruction evaluations include temporary structures such as cranes, with coordinates and
  dates, which would flag construction starts months before radar sees a structure.
- **First test:** Pull filings near 20 US inventory campuses and compare the first crane date with the radar structure-on
  month.
- **Keys:** none. **Stop if** filings match fewer than half the campuses or lead radar by less than a month.

### T-06 Utility retail sales where one campus dominates

- **Hypothesis:** For small utilities whose load is mostly one campus, the Energy Information Administration's annual retail
  sales by utility approximate that campus's consumption.
- **First test:** Identify serving utilities for inventory campuses, find those where recent sales growth matches the campus,
  and validate on a Meta campus with reported electricity.
- **Keys:** none. **Stop if** no validated case lands within 30 % of Meta's figure.

### T-07 Radar coherence over fan yards

- **Hypothesis:** Operating cooling and fan yards lose radar interferometric coherence faster than idle yards.
- **First test:** Compute 6 or 12-day Sentinel-1 coherence from single-look complex data at yards and roofs before and after
  documented energisation at three sites.
- **Keys:** Earthdata. **Stop if** no step appears at the three sites.

### T-08 Cooling-tower vapour plumes

- **Hypothesis:** On cold humid mornings, plumes above cooling towers are visible in Sentinel-2 and Landsat, and how often they
  appear tracks operation.
- **First test:** Tally plume presence on clear winter scenes at evaporative-cooled sites before and after documented start
  dates.
- **Keys:** EE. **Stop if** weather explains plume presence better than operating status.

### T-09 Chinese power-exchange market records

- **Hypothesis:** Provincial power exchanges publish market participant registrations and green-power transaction notices
  that name data-centre companies and, sometimes, volumes.
- **First test:** Search the Inner Mongolia and Beijing exchanges' public notices for companies operating at the hub campuses,
  and record what each notice gives.
- **Keys:** none. These are company transaction records to be tested, not statistics. **Stop if** no volume can be
  attributed to a campus.
