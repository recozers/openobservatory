# Requests for work

Open Observatory is built by people who donate their coding agent's attention for a session. This page sets out the goal,
how far the project has got, and the work, research and purchases that would move it forward. Every item is written so an
agent can pick it up with no other context.

## The goal

**Full monitoring of data-centre activity, at the highest time resolution public data allows.** For every data centre in
the world: where it is, when each building goes up, when it starts running, and how much power it draws, month by month or
better.

**China is the priority.** Public data there, official figures above all, is notoriously unreliable and cannot be checked
from outside, so independent measurement matters most. It is also where the project sees least today.

### How close we are

| Question | Method | Time resolution | US today | China today |
|---|---|---|---|---|
| Where is it? | Inventory, plus Sentinel-1 radar and Sentinel-2 change scans | New since 2021 | 88 sites | 54 sites, including 39 radar-found structures not yet confirmed as data centres |
| When did each building go up? | Sentinel-2 roof brightness and Sentinel-1 radar | Monthly | Dated buildings at 69 sites | Dated buildings at 45 sites, mostly by radar |
| When did it start running? | VIIRS night lights | Monthly | No direct signal: lights rise during construction, not at start-up | No signal: parks were already lit |
| How much power, reported? | Operator disclosures | Annual | 18 Meta campuses, 15 of them in the US | None published |
| How much power, from water use? | Operator water disclosures | Annual | 12 Google campuses; tested on Meta's campuses, the method gave 0.35 to about 3 times actual | None published |
| How much power, from fuel burned on site? | TROPOMI NOx flux | Monthly ±20 to 50 %, quarterly ±20 % | 1 campus measured, 2 turbine fleets watched | Nothing to calibrate against; no known on-site generation |
| How much power, grid-fed? | No working method | None | Not observable | Not observable |

### The biggest gaps

- **China has no power measurement of any kind.** Construction dating is its only independent signal, and the radar finds
  there are unconfirmed.
- **Grid-fed campuses have no satellite signal.** Every thermal, snow and NO₂ approach tried so far has failed for them.
- **No public source found so far gives power more often than monthly,** and that only where a campus burns its own fuel.
  Elsewhere the best is one figure a year from operators that choose to publish.

## Donate a session

1. **Read "Results so far"** at the end of this page, so you do not repeat a method that has already failed.
2. **Pick one open item** that fits your time and credentials, from Priority 1 if you can. Search open pull requests for its
   ID, for example `RFW-07`, to check it is free.
3. **Claim it early.** Fork the repository, push a branch named `rfw/07-short-name`, and open a draft pull request titled
   `[RFW-07] Short title` with your plan. A claim with no new commit for 72 hours lapses. Theories are claimed as `[T-NN]`
   and paid-request preparation as `[PAID-NN]`.
4. **Deliver against the acceptance line.** A negative result with numbers is a full delivery. Follow `CONTRIBUTING.md`.
5. **Hand off.** End the pull request with what changed, the validation numbers, what remains uncertain and where you
   stopped, and append a dated entry to `docs/LOG.md`.

Copy this into your agent to start:

```
You are donating a session to Open Observatory: https://github.com/recozers/openobservatory
Fork and clone it, then read README.md, CONTRIBUTING.md and REQUESTS_FOR_WORK.md, including "Results so far".
Pick one open item that fits about <N> hours and needs only these credentials: <none | Earth Engine | EPA | Earthdata>.
Prefer Priority 1 (China). Search open pull requests for its ID. If it is free, claim it with a draft pull request titled "[RFW-NN] <title>".
Keep every number traceable to a public source and a script. Before you finish, run:
python -m unittest discover -s tests; node --test tests/frontend_evidence.test.cjs; python tools/refresh.py --dry-run
Record the result in docs/LOG.md, including negative results, and end the pull request with what changed,
validation numbers, remaining uncertainty and where you stopped.
```

**Keys:** `none` needs nothing; `EE` needs Google Earth Engine, free for non-commercial research with your own Cloud project;
`EPA` needs a free api.data.gov key; `Earthdata` needs a free NASA Earthdata login. Keep keys in a local `.env` and never
commit them. **Size** is agent time: S under 2 hours, M 2 to 6, L more than 6, delivered as a first slice.

## Ground rules

- Every public number traces to a free public source, a script in this repository, and a polygon with a stated confidence.
- Official national statistics are inputs to test, never evidence.
- State results at the scale they were tested: how many sites, against what truth, with what uncertainty.
- Negative results stay visible. Document a failed method; do not delete it.
- Respect data licences and site terms. Do not scrape services that forbid it, never bypass a CAPTCHA, login or other access
  control, and follow the Nominatim usage policy for geocoding.
- A document's figure keeps its own quantity. Do not turn kVA into IT megawatts, add facility and IT figures, or treat a
  forecast as an observed load.

## Requests

Status shows only standing reservations by the project's own agents. Live claims are open draft pull requests.

### Priority 1: China

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-01](#rfw-01-confirm-or-reject-the-radar-detected-structures-in-china) | Confirm or reject the radar-detected structures in China | Where | S | none | open |
| [RFW-02](#rfw-02-locate-every-national-computing-cluster-and-scan-it) | Locate every national computing cluster and scan it | Where | M | none, then EE | open |
| [RFW-03](#rfw-03-quarterly-construction-index-for-each-chinese-hub) | Quarterly construction index for each Chinese hub | Built | M | none | open |
| [RFW-04](#rfw-04-land-transfer-results-for-operators-and-start-dates) | Land transfer results for operators and start dates | Where, Built | M | none | open |
| [RFW-05](#rfw-05-procurement-tenders-and-awards-for-named-chinese-campuses) | Procurement tenders and awards for named Chinese campuses | Built, Running | M | none | open |
| [RFW-06](#rfw-06-substation-and-transmission-projects-serving-the-hub-parks) | Substation and transmission projects serving the hub parks | Power bound | M | none | open |
| [RFW-07](#rfw-07-water-withdrawal-permit-notices-for-hub-data-centres) | Water-withdrawal permit notices for hub data centres | Power bound | M | none | open |
| [RFW-08](#rfw-08-chindatas-per-data-centre-table-and-an-edgar-name-search) | Chindata's per-data-centre table and an EDGAR name search | Power bound | S | none | open |
| [RFW-09](#rfw-09-building-scale-night-lights-inside-chinese-parks) | Building-scale night lights inside Chinese parks | Running | M | EE | open |
| [RFW-10](#rfw-10-multi-storey-data-centre-positives-for-the-classifier) | Multi-storey data-centre positives for the classifier | Where | M | EE | open |
| [RFW-11](#rfw-11-dedicated-plants-and-public-stack-monitors-in-china) | Dedicated plants and public stack monitors in China | Power | M | none | reserved: Astra |
| [RFW-12](#rfw-12-operator-utilisation-priors-from-chinese-filings) | Operator utilisation priors from Chinese filings | Power | S | none | reserved: Astra |

#### RFW-01 Confirm or reject the radar-detected structures in China

- **Why:** 39 inventory entries named `cn_<hub>_r<rank>` are new hall-like structures found by radar, dated, and unconfirmed.
  Each needs a verdict before it counts as a data centre.
- **Do:** For each entry, look at its chip (`results_s1/<hub>_candNN.png`, or render one with `tools/chip.py`) and its
  classifier score in `results_cand/scores.csv`. Classify it as data-hall complex, not a data centre, or unclear, with a
  one-line reason naming what you see: long parallel halls, cooling yards, generator rows, a substation. For confirmed halls,
  check the outline in `data/polygons/<site_id>.geojson` against the chip.
- **Deliver:** `data/cn_radar_review.csv` with site_id, verdict, reason and evidence path. Rejected entries leave the public
  inventory but stay in the review file. The site rebuilds and the tests pass.

#### RFW-02 Locate every national computing cluster and scan it

- **Why:** China's national computing network names ten data-centre clusters. Of 12 radar boxes so far, six around digitised
  campuses and hub centroids found the 39 entries, six placed from approximate coordinates found nothing, and some clusters,
  such as the Yangtze River Delta demonstration zone, have never been scanned.
- **Do:** Find each cluster's data-centre parks and their locations or boundaries in park plans, environmental impact
  documents or land transfer notices, with URLs. Scan each park with RFW-23's command and score the candidates.
- **Deliver:** `data/cn_hub_parks.csv` with cluster, park, coordinates or boundary, source URL and page; candidate files per
  park; and a one-line verdict per cluster in `docs/LOG.md`.

#### RFW-03 Quarterly construction index for each Chinese hub

- **Why:** The simplest test of whether building continues or stops is new hall area per hub per quarter, and the radar entries
  already give each structure a month and an area.
- **Do:** Aggregate new hall area by hub and quarter from the radar entries and their outlines, keeping confirmed, unclear and
  rejected structures separate once RFW-01 has run. Report an uncertainty from the dating spread, and extend to new parks as
  RFW-02 adds them.
- **Deliver:** `results_cn/construction_index.csv` and a short note in `docs/MVP.md` stating what the index can and cannot
  show, with the counts behind each quarter.

#### RFW-04 Land transfer results for operators and start dates

- **Why:** Land transfer result notices name the parcel, its area, the buyer and the date. They can attribute radar-found
  structures to operators and date the start of each project.
- **Do:** Search the national land market network and provincial natural-resources bureaus for industrial parcel results in
  the hub parks. Match parcels to radar entries and inventory campuses by location and area.
- **Deliver:** `data/cn_land_transfers.csv` with parcel, area, buyer, date, URL and the matched site, and a note on match
  confidence. An operator is attributed only when a notice names it.

#### RFW-05 Procurement tenders and awards for named Chinese campuses

- **Why:** Procurement notices for racks, UPS systems and cooling name campuses, quantities and dates. They time each phase of
  fit-out, which is the closest public signal to a campus starting to run.
- **Do:** Search the China Government Procurement Network and the three telecom operators' procurement portals for tenders
  and awards naming campuses at Ulanqab, Horinger, Zhangbei, Zhongwei, Qingyang, Gui'an and Chongqing. Record campus, item,
  quantity, units, date and URL. These are company procurement records, not statistics.
- **Deliver:** `data/cn_procurement.csv` and a note on what each portal exposes. Do not convert kVA or rack counts into IT
  megawatts.

#### RFW-06 Substation and transmission projects serving the hub parks

- **Why:** Environmental impact documents and approvals for new substations and lines often state capacity and the load they
  serve, such as a named data-centre park. That bounds the power a park can draw and dates when it could draw it.
- **Do:** Find substation and transmission project documents near each hub park. Record voltage, transformer capacity, stated
  served load, approval and commissioning dates, and URLs.
- **Deliver:** `data/cn_grid_projects.csv` and a note per hub. Transformer MVA is supply capacity, not IT load; keep the units.

#### RFW-07 Water-withdrawal permit notices for hub data centres

- **Why:** Water-withdrawal permit notices for data-centre projects can state permitted annual withdrawal, which bounds cooling
  water use. Most western hubs use little water, so absence is also informative.
- **Do:** Search provincial water-resources bureaus' permit notices for data-centre projects in the hub parks, and record the
  project, operator, permitted volume, date and URL.
- **Deliver:** `data/cn_water_permits.csv` and a note. Do not convert volumes to electricity until RFW-16 has a validated
  method.

#### RFW-08 Chindata's per-data-centre table and an EDGAR name search

- **Why:** Chindata's fiscal-2022 annual report on Form 20-F contains a per-data-centre table with megawatts per campus, and
  VNET's filings mention Ulanqab orders. Neither has been parsed (`docs/cn_operator_disclosures_notes.md`).
- **Do:** Download the filings from EDGAR with a declared User-Agent, parse the table, and run a full-text search for
  Ulanqab, Zhangbei, Horinger, Gui'an and Zhongwei across VNET, GDS and Chindata filings.
- **Deliver:** Every per-campus figure in `data/cn_operator_disclosures.csv` with its filing URL, period and whether it is
  capacity in service, utilised or planned.

#### RFW-09 Building-scale night lights inside Chinese parks

- **Why:** At park scale, VIIRS fails in China because the parks were already lit. The radar entries now give building
  outlines, which may be enough to see a single building energise inside a lit park.
- **Do:** Run `tools/ntl_timeline.py` on the radar entries and the three digitised campuses, with the comparison ring drawn
  inside the park. Test the same set-up first on a US campus inside a lit district, Prometheus at New Albany.
- **Deliver:** Lit-up months where they pass the existing rule, and a verdict on whether building scale works. Stop if the
  New Albany test shows no step.

#### RFW-10 Multi-storey data-centre positives for the classifier

- **Why:** The classifier learned from single-storey hyperscale halls. Many data centres in eastern China are multi-storey
  buildings it has never seen, which may be why six eastern hub boxes found nothing.
- **Do:** Assemble at least 30 verified multi-storey data-centre buildings from operator pages or filings, with coordinates,
  including Chinese ones where a document names the building. Extract features with `tools/cand_features.py`, retrain, and
  report leave-one-group-out results separately for single-storey and multi-storey positives.
- **Deliver:** A labelled positives file with sources, updated scores, and the per-class results in `docs/LOG.md`.

#### RFW-11 Dedicated plants and public stack monitors in China

- **Status:** reserved by Astra (B8 in `docs/PHASE2_TODO.md`). A first pass was merged on 14 September; see
  `docs/cn_stack_monitors.md`.
- **Why:** Plants built for hub parks may publish hourly stack monitoring on provincial platforms, the counterpart of EPA
  plant records. So far only annual reports have been reachable, and hourly readings at the one linked plant sit behind a
  CAPTCHA.

#### RFW-12 Operator utilisation priors from Chinese filings

- **Status:** reserved by Astra (B9 in `docs/PHASE2_TODO.md`).
- **Why:** VNET, GDS and Chindata report company-wide utilisation, a sourced prior for campuses whose operator is known.

### Priority 2: Power, at higher time resolution

These methods are developed where ground truth exists, mostly in the US, so they can be carried to China once proven.

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-13](#rfw-13-make-the-plume-test-robust-to-start-date-and-season) | Make the plume test robust to start date and season | Power | S | none | open |
| [RFW-14](#rfw-14-near-field-plume-test-for-plants-on-a-citys-edge) | Near-field plume test for plants on a city's edge | Power | M | EE, EPA | open |
| [RFW-15](#rfw-15-qualify-gas-turbine-nox-calibration-plants) | Qualify gas-turbine NOx calibration plants | Power | M | none | open |
| [RFW-16](#rfw-16-climate-aware-water-efficiency-for-water-derived-loads) | Climate-aware water efficiency for water-derived loads | Power | M | EE | open |
| [RFW-17](#rfw-17-per-site-electricity-from-more-operators) | Per-site electricity from more operators | Power | M | none | open |
| [RFW-18](#rfw-18-microsofts-metro-electricity-table-to-campuses) | Microsoft's metro electricity table to campuses | Power | S | none | open |
| [RFW-19](#rfw-19-generator-fleet-discovery-from-eia-860m) | Generator fleet discovery from EIA-860M | Power | M | none | open |
| [RFW-20](#rfw-20-evidence-for-the-pending-generator-watch-records) | Evidence for the pending generator watch records | Power | M | none | reserved: Astra |
| [RFW-21](#rfw-21-load-ramp-curves-from-metas-18-campuses) | Load ramp curves from Meta's 18 campuses | Running, Power | M | EE optional | open |
| [RFW-22](#rfw-22-implement-the-utilisation-model) | Implement the utilisation model | Power | L | none | open |

#### RFW-13 Make the plume test robust to start date and season

- **Why:** Abilene reaches 2.8σ with its documented start and 2.3σ with a start one month earlier, and several sites with
  spring starts show strongly negative z-scores. The test compares unmatched seasons and depends on one date.
- **Do:** Using the saved daily series in `results_no2/<site>.csv`, add a season-matched version of the test and report each
  site's z-score across start dates within three months of the documented one. Re-run the 62 control points the same way.
- **Deliver:** The revised test in `tools/plume_batch.py`, per-site date sensitivity in a results file, and a recommendation on
  whether the 2.5σ rule should change, with the control-point false-positive rate under the new test.

#### RFW-14 Near-field plume test for plants on a city's edge

- **Why:** The box method cannot separate a campus plant from a nearby city's plume, which rules out Dublin and similar
  grid-constrained markets where campuses run gas plants.
- **Do:** Build a sector test within 1 to 5 km that keeps only days when the wind blows from the side away from the city and
  excludes the city from the upwind sector. Validate it first on a US plant at a city's edge with EPA hourly emissions, then
  apply it to Grange Castle.
- **Deliver:** The validation result against EPA truth and, only if validation passes, the Dublin result. A failed validation
  is a full delivery.

#### RFW-15 Qualify gas-turbine NOx calibration plants

- **Why:** The NOx calibration rests on five tall-stack coal plants, but turbine exhaust leaves from low stacks. Three gas
  candidates gave factors from 0.89 to 4.83 and are not qualified (`docs/low_stack_calibration.md`).
- **Do:** Verify physical stack heights from EIA-860's environmental-equipment data or permits, check isolation from other
  sources with the EPA's point-source inventory, and align the TROPOMI overpass time with the hourly records.
- **Deliver:** Each candidate qualified or rejected with its reason, and the calibration comparison updated for the qualified
  ones.

#### RFW-16 Climate-aware water efficiency for water-derived loads

- **Why:** Water use per unit of energy depends on climate, but the current method applies one fleet-wide figure. Against
  Meta's electricity it puts individual campuses anywhere from 0.35 to about 3 times their reported load.
- **Do:** Meta publishes both water withdrawal and electricity for 18 campuses. Model withdrawal per unit energy as a function
  of local climate, such as ERA5 wet-bulb temperature, and test it leaving one campus out at a time. Apply it to Google's
  campuses only if it beats the current method.
- **Deliver:** Leave-one-out errors for the current and new methods side by side; updated derived loads and a narrower band
  only if the new method is better.

#### RFW-17 Per-site electricity from more operators

- **Why:** Operator-reported electricity is the strongest load evidence the project has, and it comes from one operator.
- **Do:** Survey sustainability reports and data appendices from Apple, Equinix, Digital Realty, NTT, Iron Mountain, Switch,
  CyrusOne, QTS, Aligned, and the Chinese operators GDS, VNET and Chindata, for per-site electricity, PUE or water, at the
  finest period published. Add rows to `data/operator_disclosures.csv` with source URL and table, add missing campuses with
  sourced coordinates, and run `tools/ingest_disclosures.py`.
- **Deliver:** A table of which operators publish what, at what resolution and period; every new site-year with its source;
  the site rebuilt with the new measured sites.

#### RFW-18 Microsoft's metro electricity table to campuses

- **Why:** Microsoft's 2026 data fact sheet reports fiscal-2025 electricity and water by metro area. Where a metro holds one
  campus, that is a campus figure.
- **Do:** Map each metro row to inventory campuses. Attribute a figure only where the metro is effectively one campus, and
  record the rest as context.
- **Deliver:** Rows in `data/operator_disclosures.csv` with the attribution reasoning, and a note listing the metros left as
  context and why.

#### RFW-19 Generator fleet discovery from EIA-860M

- **Why:** The generator watch list was assembled by hand from permits. The US Energy Information Administration's monthly
  generator inventory lists planned and operating generators by plant, which could flag new fleets built for data centres
  automatically.
- **Do:** Parse the latest EIA-860M. Flag planned or new gas turbine and engine plants whose owner, name or location links
  them to a data centre, or that sit within a few kilometres of an inventory site. Verify each flag against a permit or
  company statement.
- **Deliver:** A script, a candidate table with verification notes, and verified candidates proposed for the watch list.
  Coordinate with the RFW-20 claimant before adding watches.

#### RFW-20 Evidence for the pending generator watch records

- **Status:** reserved by Astra, working in `astra/b7`.
- **Why:** Seven planned on-site generation fleets need filing-located coordinates, a first-fire target and a valid emission
  factor before they can be watched monthly. See `docs/generator_watchlist.md`.

#### RFW-21 Load ramp curves from Meta's 18 campuses

- **Why:** How fast load ramps after a building is finished is the key prior for estimating power between annual disclosures.
  Meta's electricity series from 2011 to 2024 across 18 campuses measures it.
- **Do:** Date each campus's buildings from Sentinel-2, radar, or Landsat for older ones. Fit average load per building
  against years since roof-on, with uncertainty.
- **Deliver:** Fitted ramp parameters with uncertainty in `docs/utilisation_model.md`, and the per-campus fits.

#### RFW-22 Implement the utilisation model

- **Why:** The site uses fixed rules per evidence type. `docs/utilisation_model.md` defines one model in which every source
  moves the estimate consistently, month by month, with stated priors and posteriors per site.
- **Do:** Implement section 7 of that document: hall states, the evidence likelihoods, and Monte Carlo percentiles in a
  pure-Python `utilmodel.py`. Keep the timeline JSON shape so the site needs no change.
- **Deliver:** A first slice covering reported electricity, documented capacity and roofs-only sites, behind a switch, with
  tests showing it reproduces today's bands where the rules are already calibrated.

### Priority 3: Coverage and tools

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-23](#rfw-23-radar-candidate-scan-around-every-inventory-site) | Radar candidate scan around every inventory site | Where, Built | L | EE | open |
| [RFW-24](#rfw-24-date-dark-and-grey-roofs) | Date dark and grey roofs | Built | M | EE | open |
| [RFW-25](#rfw-25-recalibrate-the-hall-classifier-with-new-labels) | Recalibrate the hall classifier with new labels | Where | M | EE | open after RFW-01 |
| [RFW-26](#rfw-26-standby-generator-permits-as-a-capacity-bound) | Standby generator permits as a capacity bound | Power bound | M | none | open |
| [RFW-27](#rfw-27-construction-timeline-on-the-map) | Construction timeline on the map | Built | M | none | open |
| [RFW-28](#rfw-28-tests-for-the-load-precedence-rules) | Tests for the load precedence rules | Tools | S | none | open |
| [RFW-29](#rfw-29-source-link-checker) | Source link checker | Tools | S | none | open |

#### RFW-23 Radar candidate scan around every inventory site

- **Why:** Radar dates construction through cloud and finds unlisted buildings, but it has run in only 12 Chinese hub boxes, 9
  US boxes and 40 night-light areas.
- **Do:** Start with Chinese sites. For each site in `data/sites.csv` without a `results_s1/<site_id>_candidates.csv`, run
  `python tools/s1_timeline.py --chip LAT LON --candidates --half 6000 --early 2021 --late 2026 --out results_s1/<site_id>`,
  then score with `tools/cand_features.py` and `tools/cand_classifier.py`. Work region by region.
- **Deliver:** A candidate file per site; a table in `docs/LOG.md` of recall at known halls and the false-positive types by
  region. Stop and report if Earth Engine quotas make a region impractical.

#### RFW-24 Date dark and grey roofs

- **Why:** Brightness dating misses dark membranes and grey roofs, as at Hyperion and at Chinese campuses such as Ulanqab. A
  vegetation and built-up index rule already failed (`docs/dark_roof_validation.md`).
- **Do:** Use radar structure-on months as labels and test other Sentinel-2 signals, such as shortwave-infrared change,
  texture or temporal variance. Validate on Hyperion, the Ulanqab long halls and all 12 Abilene halls, and check that fallow
  fields produce no false events.
- **Deliver:** A rule that dates Hyperion's two structures without a false early event and moves no Abilene date by more than
  a month, or a documented failure with the numbers.

#### RFW-25 Recalibrate the hall classifier with new labels

- **Why:** The classifier has 18 positives. RFW-01, RFW-10 and the 78 Epoch campuses with polygons can multiply that.
- **Do:** Add the new labels, retrain with `tools/cand_classifier.py`, and report leave-one-group-out results by region and
  building type. Refresh the scores of existing candidates.
- **Deliver:** Updated `results_cand/scores.csv`, results in `docs/LOG.md`, and a note on any threshold change.

#### RFW-26 Standby generator permits as a capacity bound

- **Why:** State air permits list the diesel standby generators at many US data centres. Their total rating bounds facility
  power, because campuses back up their full load.
- **Do:** For inventory sites in Virginia, Ohio, Texas, Arizona and Georgia, find the air permits and record unit counts,
  ratings, fuel, permit date and URL. Compare total standby MW with documented capacity where both exist.
- **Deliver:** `data/standby_generation.csv` and a note giving the ratio of standby MW to documented capacity across at least
  10 sites. Propose a capacity-bound basis only if the ratio is consistent to within about 30 %.

#### RFW-27 Construction timeline on the map

- **Why:** Every dated building has a month, but the map shows only the present.
- **Do:** Add a time slider to the landing map that shows sites as they were at the end of each quarter, using the dates
  already in `site/data/timeline/`. Keep it static with no new framework.
- **Deliver:** The slider working at desktop and phone widths, and Node tests in the style of
  `tests/frontend_evidence.test.cjs`.

#### RFW-28 Tests for the load precedence rules

- **Why:** The rules deciding which figure sets a site's load have been extended several times: reported electricity, carried
  averages, water-derived figures, third-party estimates, plant records, radar entries, generator watches.
- **Do:** Write synthetic cases for `cap_in_force`, `utilisation_prior` and the evidence kinds in `build_status.py`, covering
  each basis and each carried-forward case.
- **Deliver:** Tests that fail if any precedence rule changes silently, all passing on `main`.

#### RFW-29 Source link checker

- **Why:** Hundreds of source URLs back the numbers on the site, and links rot.
- **Do:** Write `tools/check_links.py` to read every URL in `data/*.csv` and the source JSON files, check each at a polite
  rate, and look up whether an archived copy exists without submitting new captures.
- **Deliver:** A report of dead links with their archived alternatives, and the script documented in `CONTRIBUTING.md`.

## Theories to explore

Research bets with a first test that fits a session and a condition for stopping. China first.

| ID | Theory | Answers | Resolution if it works | Region | Keys |
|---|---|---|---|---|---|
| [T-01](#t-01-chinese-power-exchange-market-records) | Chinese power-exchange market records | Power | Monthly or annual | China | none |
| [T-02](#t-02-temporary-site-housing-as-a-construction-signal) | Temporary site housing as a construction signal | Built | Monthly | China | EE |
| [T-03](#t-03-radar-backscatter-after-the-structure-goes-up) | Radar backscatter after the structure goes up | Running | Monthly | China and global | EE |
| [T-04](#t-04-radar-coherence-over-fan-yards) | Radar coherence over fan yards | Running | 6 to 12 days | China and global | Earthdata |
| [T-05](#t-05-cooling-tower-vapour-plumes) | Cooling-tower vapour plumes | Running | Per clear scene | Global | EE |
| [T-06](#t-06-wastewater-discharge-reports-as-a-monthly-cooling-series) | Wastewater discharge reports as a monthly cooling series | Power | Monthly | US | none |
| [T-07](#t-07-building-permits-and-occupancy-certificates-as-energisation-dates) | Building permits and occupancy certificates as energisation dates | Running | Monthly | US | none |
| [T-08](#t-08-crane-filings-as-construction-start-signals) | Crane filings as construction-start signals | Built | Monthly | US | none |
| [T-09](#t-09-counting-cooling-equipment-in-public-aerial-imagery) | Counting cooling equipment in public aerial imagery | Power bound | Every 2 to 3 years | US | EE |
| [T-10](#t-10-substation-transformer-bays-as-connection-capacity) | Substation transformer bays as connection capacity | Power bound | Every 2 to 3 years | US | EE |
| [T-11](#t-11-utility-retail-sales-where-one-campus-dominates) | Utility retail sales where one campus dominates | Power | Annual | US | none |

#### T-01 Chinese power-exchange market records

- **Hypothesis:** Provincial power exchanges publish market participant registrations and green-power transaction notices
  that name data-centre companies and, sometimes, volumes.
- **First test:** Search the Inner Mongolia and Beijing exchanges' public notices for companies operating at the hub campuses,
  and record what each notice gives. These are company transaction records to be tested, not statistics.
- **Stop if:** no volume can be attributed to a campus.

#### T-02 Temporary site housing as a construction signal

- **Hypothesis:** Large Chinese construction sites house workers and site offices in prefabricated blocks with distinctive blue
  roofs, visible in Sentinel-2. They appear when work starts and go when it ends, so they may lead radar dating and mark
  completion.
- **First test:** Track blue-roof area within 1 km of five radar-dated Chinese structures by month, and compare its appearance
  and removal with the radar structure-on month.
- **Stop if:** it does not appear at least a month before radar structure-on at three of the five.

#### T-03 Radar backscatter after the structure goes up

- **Hypothesis:** Backscatter keeps rising after a hall's structure appears, as rooftop plant and yard equipment are
  installed, which would make fit-out visible through cloud.
- **First test:** At Abilene, compare each hall's backscatter after structure-on with the roof darkening that marks fit-out in
  Sentinel-2 six to nine months later, then apply the result to the Chinese radar entries.
- **Stop if:** Abilene shows no post-structure rise distinguishable from month-to-month noise.

#### T-04 Radar coherence over fan yards

- **Hypothesis:** Operating cooling and fan yards lose radar interferometric coherence faster than idle yards.
- **First test:** Compute 6 or 12-day Sentinel-1 coherence from single-look complex data at yards and roofs before and after
  documented energisation at three US sites, then at Chinese campuses if it works.
- **Stop if:** no step appears at the three US sites.

#### T-05 Cooling-tower vapour plumes

- **Hypothesis:** On cold humid mornings, plumes above cooling towers are visible in Sentinel-2 and Landsat, and how often they
  appear tracks operation.
- **First test:** Tally plume presence on clear winter scenes at evaporative-cooled sites before and after documented start
  dates.
- **Stop if:** weather explains plume presence better than operating status.

#### T-06 Wastewater discharge reports as a monthly cooling series

- **Hypothesis:** Where a campus discharges cooling-tower water under its own federal permit, the EPA's monthly discharge
  monitoring reports give a measured monthly flow that scales with heat rejected.
- **First test:** Search EPA ECHO for permits held by data-centre operators at inventory sites, pull their monthly flows, and
  check the seasonality against wet-bulb temperature and against Meta's electricity where both exist.
- **Stop if:** no inventory campus holds an individual permit with flow reporting.

#### T-07 Building permits and occupancy certificates as energisation dates

- **Hypothesis:** US county permit records give the month each building was certified for occupancy, which marks the step
  between a finished building and one drawing load.
- **First test:** Match permit records from counties that publish them as open data, such as Loudoun and Franklin, to inventory
  halls, and compare occupancy dates with radar structure-on and with Meta's load ramp.
- **Stop if:** fewer than 10 inventory buildings can be matched.

#### T-08 Crane filings as construction-start signals

- **Hypothesis:** The FAA's public obstruction evaluations include temporary structures such as cranes, with coordinates and
  dates, which would flag construction starts months before radar sees a structure.
- **First test:** Pull filings near 20 US inventory campuses and compare the first crane date with the radar structure-on month.
- **Stop if:** filings match fewer than half the campuses or lead radar by less than a month.

#### T-09 Counting cooling equipment in public aerial imagery

- **Hypothesis:** USDA's public-domain NAIP aerial imagery, at 0.6 to 1 m, resolves chillers, dry coolers and cooling towers.
  Count times unit capacity from Epoch's equipment catalogues in `data/epoch/` bounds the heat a campus can reject, and so its
  IT capacity. The same method in China needs purchased imagery (PAID-01).
- **First test:** Count units at five US sites with documented capacity and compare.
- **Stop if:** the estimate misses documented capacity by more than a factor of two.

#### T-10 Substation transformer bays as connection capacity

- **Hypothesis:** The number of transformer bays at a campus substation, visible in NAIP, indicates its grid connection
  capacity.
- **First test:** Count bays at campuses with documented connections, such as New Albany's 250 MW and Luleå's 120 MW, and
  compare bays times typical ratings.
- **Stop if:** ratings vary too much to beat a factor of two.

#### T-11 Utility retail sales where one campus dominates

- **Hypothesis:** For small utilities whose load is mostly one campus, the Energy Information Administration's annual retail
  sales by utility approximate that campus's consumption.
- **First test:** Identify serving utilities for inventory campuses, find those where recent sales growth matches the campus,
  and validate on a Meta campus with reported electricity.
- **Stop if:** no validated case lands within 30 % of Meta's figure.

## Requests that cost money

These need funding rather than agent time, and they are where commercial data could close the gap in China. Nothing is bought
until a pilot shows it is worth it.

- **Who does what.** An agent can claim the preparation as `[PAID-NN]`: a pilot specification, analysis code tested on free
  data, and a draft request for quotation. Agents never place orders, sign licences or handle payment; Stuart does.
- **Free access first.** Check research access before paying, such as NASA's commercial smallsat data programme for
  NASA-funded researchers, ESA's third-party missions programme, and providers' research programmes. Eligibility varies.
- **Licence condition.** Every public number must trace to free public data. A purchase helps only if its licence lets the
  project publish the derived numbers, and ideally the data, or if it is used purely to validate a method that then runs on
  free data. Buy nothing whose licence allows neither.
- **Cost.** No prices are listed because none has been quoted. Each request names what drives cost.

| ID | Request | Answers | Region | Pilot |
|---|---|---|---|---|
| [PAID-01](#paid-01-sub-metre-optical-imagery-of-the-chinese-hub-parks) | Sub-metre optical imagery of the Chinese hub parks | Where, Power bound | China | 3 parks, archive scenes |
| [PAID-02](#paid-02-high-resolution-radar-over-cloudy-southwest-hubs) | High-resolution radar over cloudy southwest hubs | Built | China | 2 parks, 4 scenes each |
| [PAID-03](#paid-03-night-thermal-imagery-at-3-to-5-metres) | Night thermal imagery at 3 to 5 metres | Running, Power | US, then China | 1 US campus with a known ramp |
| [PAID-04](#paid-04-frequent-3-to-5-metre-optical-monitoring-of-chinese-parks) | Frequent 3 to 5 metre optical monitoring of Chinese parks | Built, Running | China | 5 parks, 3 months |
| [PAID-05](#paid-05-dedicated-satellite-capacity) | Dedicated satellite capacity | All | China first | Requirements only |
| [PAID-06](#paid-06-native-language-review-of-chinese-documents) | Native-language review of Chinese documents | Where, Built | China | 20 documents |
| [PAID-07](#paid-07-chinese-corporate-registry-data) | Chinese corporate registry data | Where | China | 10 campuses |
| [PAID-08](#paid-08-compute-for-continental-radar-scans) | Compute for continental radar scans | Where, Built | China | 1 province |
| [PAID-09](#paid-09-us-public-records-request-fees) | US public-records request fees | Power | US | 5 requests |

#### PAID-01 Sub-metre optical imagery of the Chinese hub parks

- **Answers:** whether the radar-found structures are data halls; counts of cooling units and generator rows, which bound
  capacity as T-09 does with free US imagery; phase dating at building level.
- **Pilot:** one recent cloud-free archive scene each over Horinger, Ulanqab and Zhangbei, then one more a year apart.
- **Cost drivers:** area, resolution, archive against new tasking.
- **Success test:** RFW-01's chip-based verdicts agree with the sub-metre view, and two independent unit counts match.

#### PAID-02 High-resolution radar over cloudy southwest hubs

- **Answers:** construction progress and equipment yards at Gui'an and Chongqing, where optical imagery is rarely clear and
  Sentinel-1's 20 m cannot resolve individual halls.
- **Pilot:** four spotlight-mode scenes a quarter apart over two parks.
- **Cost drivers:** imaging mode, number of acquisitions, archive availability.
- **Success test:** hall-level structure dates that Sentinel-1 cannot give, checked against later clear optical scenes.

#### PAID-03 Night thermal imagery at 3 to 5 metres

- **Answers:** the one thermal hypothesis still open. Roofs at 70 to 100 m showed nothing, but individual dry coolers, cooling
  towers, transformers and generator yards may be hot enough to see at 3 to 5 m.
- **Pilot:** repeated night acquisitions over one US campus with a documented load ramp, Colossus 2 or Abilene, where ground
  truth exists. One Chinese park only if that shows a signal.
- **Cost drivers:** satellite tasking or an airborne survey, number of nights, area. An airborne survey is not an option over
  China.
- **Success test:** yard or cooling-unit temperature changes with documented load, beyond the scatter between nights. Stop if
  the US pilot shows no signal.

#### PAID-04 Frequent 3 to 5 metre optical monitoring of Chinese parks

- **Answers:** construction and fit-out pace by month at the fastest-building parks, sharper than Sentinel-2's 10 m.
- **Pilot:** near-daily imagery over five parks for three months, compared with the radar construction index (RFW-03).
- **Cost drivers:** area, revisit, subscription length. Check research access programmes first.
- **Success test:** monthly changes that the free index misses or dates later.

#### PAID-05 Dedicated satellite capacity

- **Answers:** sustained, independent monitoring of Chinese data-centre parks, the end state if a paid pilot proves an
  observable.
- **Pilot:** none until PAID-01 or PAID-03 shows which observable works. Then write requirements: resolution, night-time
  capability, spectral bands, revisit and the list of parks, and check whether a long-term tasking contract meets them before
  considering a hosted payload or a dedicated small satellite.
- **Cost drivers:** set entirely by those requirements, so no estimate is possible yet.

#### PAID-06 Native-language review of Chinese documents

- **Answers:** whether agent extractions from environmental impact documents, land notices, procurement records and permits
  (RFW-04 to RFW-07) are correct.
- **Pilot:** a Chinese-reading reviewer checks 20 extracted documents against the originals.
- **Cost drivers:** reviewer hours.
- **Success test:** an error rate per field that shows which extractions can be trusted without review.

#### PAID-07 Chinese corporate registry data

- **Answers:** which companies own the operating entities at hub campuses, and when they were set up.
- **Pilot:** ownership chains for the operating companies at 10 campuses.
- **Cost drivers:** subscription tier. These services usually forbid redistribution, so use them for leads and cite the free
  public document each lead points to.
- **Success test:** at least half the leads resolve to a free public source.

#### PAID-08 Compute for continental radar scans

- **Answers:** RFW-02 and RFW-23 across whole provinces, if Earth Engine's non-commercial quotas block the scans.
- **Pilot:** one province by batch export to cloud storage, with the cost recorded per 1,000 km².
- **Cost drivers:** storage, processing and egress.
- **Success test:** candidate lists for the province that match the box scans where they overlap.

#### PAID-09 US public-records request fees

- **Answers:** utility, water and generator records for named US campuses, where agencies charge to process requests.
- **Pilot:** five requests to agencies serving inventory campuses, chosen to test T-06 and T-11.
- **Cost drivers:** processing and copying fees.
- **Success test:** at least two responses give an attributable monthly or annual series.

## Results so far

Each result is stated at the scale it was tested. Numbers and corrections are in `docs/MVP.md` and `docs/LOG.md`.

### What works, and its limits

- **Roof dating from Sentinel-2 brightness** (`tools/s2_roof_timeline.py`). Dates new bright roofs to the month. The only
  check so far is against radar: all 12 Abilene halls agree with Sentinel-1 dates within 0 to 4 months, 9 within 2. No dated
  construction records have been compared. It misses dark and grey roofs: across the imported Epoch campuses, 217 halls were
  dated, 34 left unresolved and 16 conflicted with reported construction timing; at Horinger, 4 of 27 radar-found structures
  got a brightness date. **China:** works for bright roofs only, and grey roofs are common.
- **Structure dating from Sentinel-1 radar** (`tools/s1_timeline.py`). Dates a hall when backscatter rises at least 4 dB and
  stays up for six months. It gave no false event over Hyperion's farmland and dated Chinese blocks that brightness could not.
  It has not been checked against construction records. **China:** works, including under cloud.
- **Radar change scan for unlisted buildings** (`tools/s1_timeline.py --candidates`). In US boxes the known halls were among the
  candidates at Abilene (ranks 1, 2, 4 and 5), Rainier (1 to 3), Fairwater (1) and Prometheus (8), and were absent at Hyperion,
  whose structures went up in 2025 and 2026. **China:** of 12 hub boxes, the six around digitised campuses and hub centroids
  produced 39 hall-like entries, dated and unconfirmed; the six eastern boxes, placed from approximate coordinates, produced
  none.
- **Hall classifier** (`tools/cand_features.py`, `tools/cand_classifier.py`). Trained on 18 positives from six campuses, three
  of them labelled by inspecting chips, and 1,159 negatives: 1,133 new industrial structures in 40 Chinese areas found by the
  night-light scan, 25 near four US factories and one solar compound. Leave-one-site-out AUC is 0.977; at a 0.5 threshold it
  keeps 14 of 18 halls and 48 of 1,159 negatives. Intel's Ohio fab under construction scores 0.99. It has never seen a
  multi-storey data centre. **China:** it scored 26 of 27 large Horinger candidates above 0.5; none is confirmed.
- **Fuel burned on site, from TROPOMI NO₂** (`tools/no2_plume_test.py`, `tools/no2_flux.py`, `tools/no2_flux_quarterly.py`).
  The plume test reached 9.8σ at Colossus 2 and 2.8σ at Abilene, whose turbines have emission controls; Abilene falls to 2.3σ
  if its start date moves one month earlier. Calibrated flux measures one campus, Colossus 2: 1,207 ± 248 kg NOx/h over July
  and August 2026, which is 637 to 2,919 MW at an assumed 0.5 to 1.5 kg NOx/MWh for its temporary turbine fleet. With 7 to 16
  usable days a month, quarterly figures carry about ±20 % statistical uncertainty and single months ±20 to 50 %. The
  calibration factor, 4.41 ± 0.18, comes from five US tall-stack coal plants with ±19 % plant-to-plant scatter; gas-turbine
  references are not yet qualified. None of 31 campuses without known on-site generation reached 2.5σ, and none of 62 control
  points did. **China:** no public hourly plant data to calibrate against, and no hub campus is known to generate on site.
- **Operator-reported electricity** (`tools/ingest_disclosures.py`). Meta's Environmental Data Index gives annual electricity
  for 18 campuses from 2011 to 2024; the 2024 figures appeared in October 2025. The site shows the 2024 average and carries it
  into 2025 and 2026 with a wider band. **China:** no operator publishes per-campus figures.
- **Load derived from water use** (`tools/ingest_water_loads.py`). Google publishes per-campus water but no water efficiency
  figure; its own totals imply 1.02 to 1.06 litres per kWh. Checked against Meta's electricity in 2024, the method puts the
  middle half of mature campuses at 0.6 to 1.6 times their reported load, individual campuses from 0.35 times (Luleå,
  air-cooled) to about 3 times (Clonee and Odense), and first-year campuses at 10 to 13 times. 12 Google campuses carry a 0.5
  to 2 times band, widened to 0.4 to 2.5 times when a year's figure is carried forward. **China:** none published.
- **Night lights from VIIRS** (`tools/ntl_timeline.py`). Campus radiance rose above its surroundings during construction at all
  four US greenfield campuses tested (Rainier August 2024, Fairwater October 2024, Abilene December 2024, Hyperion December
  2025) and at the converted Colossus 1 factory six months after its documented load began. No step appeared at 19 other
  sites, including the Colossus 2 turbine yard. It tracks construction and site lighting, not operation. As a regional scan,
  the nearest new lit area lay within 0.4 km of four of seven US campuses, 1.2 km and 2.3 km of two more, and Colossus 1 was
  missed. **China:** fails inside parks that were already lit.
- **Optical change scan from Sentinel-2** (`tools/s2_candidates.py`). Recovered 3 of 3 known US campuses; 11 of the 23 US
  components it flagged were not halls. **China:** 7 candidates in the Ulanqab and Zhangbei boxes; on inspection each was an
  unattributed roof or industrial complex, and none showed data-hall evidence.
- **Generator watch list** (`tools/generator_watchlist.py`). Two filing-located turbine fleets, Fermi Matador and Cheyenne's
  Project Jade, have NOx series from January 2024 and eight monthly screens each after a 2024 to 2025 baseline. No month has
  crossed 2σ and 100 kg/h; the largest monthly z-scores are 1.43 and 1.77. Seven more fleets need records. **US only.**
- **Plant and water records** (`tools/campd_monthly.py`, `tools/water_monthly.py`). No EPA plant record yet qualifies as a
  campus's load; the Southaven plant beside Colossus 2 stays evidence only. Of eight cities searched, one published an
  attributable campus water series: Bluffdale's 312 monthly deliveries to the NSA's Utah Data Center. **US only.**
- **Chips without credentials.** `tools/chip.py` renders a Sentinel-2 true-colour chip for any point from AWS open data.

### Inconclusive

- **Six eastern Chinese hub boxes** (Zhongwei, Zhangjiakou and Huailai, Wuhu, Shaoguan, Chengdu Tianfu, Tianjin Wuqing): 76
  candidates of 5 ha or more, none scored as hall-like. The box centres were approximate and the classifier has not seen
  multi-storey buildings, so this does not show there is nothing to find. See RFW-02 and RFW-10.
- **Abilene's plume.** 2.8σ at the documented July 2025 start and 2.3σ a month earlier, with emission-controlled turbines whose
  flux is too small to convert to megawatts. See RFW-13.
- **Gas-turbine calibration plants.** Three candidates gave calibration factors from 0.89 to 4.83; stack heights, isolation and
  overpass alignment are unverified. See RFW-15.
- **NO₂ from power plants next to Chinese hubs.** Usable as an activity index only at Ulanqab; the Horinger and Chongqing series
  were not usable.
- **Chinese plants linked to hub parks** (`tools/cn_stack_monitors.py`, `docs/cn_stack_monitors.md`). A first pass found 14
  plant or supply leads across 11 hubs; four are renewable projects. The Shengle plant supplies the Horinger cloud park, and its
  annual emission reports give 63 records for 2019 to 2025, but no allocation of its output to any campus is established. No
  hourly or daily stack readings were retrieved: Shengle's reading service requires a CAPTCHA and other candidate services
  timed out or returned errors. See RFW-11.
- **Radar-found structures in China.** Hall-like and dated, but unconfirmed. See RFW-01.

### Did not work

Please do not repeat these without a new idea.

- **Roof temperature as a load signal.** At night, ECOSTRESS (70 m) showed no step at documented load changes, adjusted for
  season and weather: Abilene +0.16 ± 0.23 K at 174 MW and +0.13 ± 0.47 K at 522 MW, Rainier +0.06 ± 0.24 K at 1,078 MW.
  Daytime steps (Rainier +1.44 ± 0.60 K, Fairwater +1.35 ± 0.49 K) coincide with roofing and fit-out and cannot be separated
  from them; Landsat (100 m, daytime) gave no usable load signal either. Colossus 1's hall warmed by 1.24 ± 0.28 K at night,
  and its whole block, turbine yard included, by about the same. As a detector, nine ordinary roofs spanned −1.5 to +2.0 K at
  night against −0.75 to +1.2 K for twelve data centres. See `docs/overnight_report_2026-09-13.md`.
- **Snow persistence on roofs.** At eight of nine sites over eight winters, operating halls held as much snow as the
  surrounding built-up land or more. At New Albany they held less in 2024 to 2026 (0.64 to 0.78 against 0.77 to 0.91) while
  new halls were being built on the campus.
- **NO₂ at campuses without on-site generation.** None of 31 reached 2.5σ; the highest was 2.09. None of 62 control points
  reached 2.5σ either.
- **A campus beside large power plants.** Colossus 1's turbine phase came out at 62 ± 63 kg NOx/h after regressing out the two
  neighbouring plants' hourly EPA emissions over 594 days.
- **The box flux method at a city's edge.** At Dublin's Grange Castle it gave 964 ± 96 kg NOx/h with winter peaks and a fitted
  source 36 km downwind, consistent with the city's plume; it cannot isolate the campus plant. See RFW-14.
- **A classifier trained on OpenStreetMap footprints.** On radar candidates its AUC was 0.70, and it scored 864 of 1,133 new
  industrial structures above 0.9.
- **A national night-light scan as a detector in China.** Over 24 to 43°N and 102 to 123°E it found 4,026 newly lit areas. The
  nearest ones to the Horinger and Ulanqab campuses ranked 344th and 2,808th, and Zhangbei had none within 40 km. In the 40
  brightest campus-sized areas, 35 held a new structure of 5 ha or more; only 4 of their 249 large structures scored as
  hall-like, and the chips inspected showed industrial sites.
- **Dark-roof dating from vegetation and built-up indices.** At Hyperion it dated the north structure to June 2026, although its
  roof was visible by January, and the south structure falsely to September 2023. See `docs/dark_roof_validation.md`.
