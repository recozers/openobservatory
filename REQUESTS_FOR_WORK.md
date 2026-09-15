# Requests for work

Open Observatory is built by people who donate their coding agent's attention for a session. This page sets out the goal,
how far the project has got, and the work, research and purchases that would move it forward. Every item is written so an
agent can pick it up with no other context.

## The goal

**Full monitoring of data-centre utilisation, at the highest time resolution public data allows.** For every data centre in
the world: where it is, when each building goes up, when it starts running, how much of its capacity is in use, and,
ideally, whether that use is training or inference.

**China is the priority.** Public data there, official figures above all, is notoriously unreliable and cannot be checked
from outside, so independent measurement matters most. It is also where the project sees least today.

**What utilisation means here.** The share of installed computing capacity in use. Public data reaches it only indirectly:

- **Commercial utilisation** is the share of built capacity that customers have leased, as colocation operators report it.
  It says nothing about how hard the equipment runs.
- **Electrical utilisation** is average power drawn divided by capacity. It needs a load and a capacity for the same period.
- **Activity signals** such as construction, energisation and on-site fuel burning bracket utilisation without measuring it.

**Training or inference.** The planned method is a deep-learning model trained on detailed thermal imagery of campus
substations and transformers, with labels from AI labs such as OpenAI, which know when and where their training runs
happened (T-05). A
transformer's losses rise with the square of its load, so its temperature follows the site's load with a lag of hours, and
the same imagery can count transformers to give capacity. Separating workloads assumes, untested here, that inference follows
daily demand cycles while training runs near-flat for weeks, so it needs several images a day at a few metres.

### How close we are

| Question | Method | Time resolution | US today | China today |
|---|---|---|---|---|
| Where is it? | Inventory, plus Sentinel-1 radar and Sentinel-2 change scans | New since 2021 | 88 sites | 42 sites, including 27 radar-found structures: 3 reviewed as data-hall complexes, 24 unclear; 12 rejected after review |
| When did each building go up? | Sentinel-2 roof brightness and Sentinel-1 radar | Monthly | Dated buildings at 69 sites | Dated buildings at 33 sites, mostly by radar |
| When did it start running? | VIIRS night lights | Monthly | No direct signal: lights rise during construction, not at start-up | No signal: parks were already lit |
| What is its capacity? | Filings, utility and operator statements, Epoch AI estimates | When documents change | 75 sites, 67 of them Epoch AI estimates | 5 sites: two supercomputers' measured peaks and three Epoch AI estimates |
| How much is in use, electrically? | Annual electricity divided by capacity for the same period | Annual | 1 site: ORNL's Frontier averaged about 0.54 of its measured peak in 2023 | None |
| How much is in use, commercially? | Operator filings | Quarterly | Not yet collected | Per data centre only from Chindata, last at end-2022: 466 of 517 MW in customer use across its 18 Greater Beijing Area data centres, most without a stated city. Company-wide for VNET, 73.9 % in mid-2026, and GDS, 75.5 % by area at end-2025 |
| How much is in use, from activity? | TROPOMI NOx at campuses that burn fuel on site | Monthly ±20 to 50 %, quarterly ±20 % | Relative change at 1 campus, Colossus 2; megawatts uncertain 2 to 3 times, so no ratio | Nothing to calibrate against; no known on-site generation |
| Training or inference? | Planned: a deep-learning model on thermal imagery of substations and transformers, labelled with AI labs' training-run records | Needs several images a day at a few metres | Not observed; free thermal imagery is 70 m or coarser, and site classes are assigned by hand from press coverage | Not observed; needs commercial satellite thermal, and national planning's assignment of latency-tolerant work to western hubs is an official input to test |

Load without a same-period capacity does not give utilisation. Meta reports electricity for 18 campuses and Google's water use
gives an approximate load for 12, but among them only Luleå in Sweden has a capacity figure for the same years: it ran at 0.25
to 0.45 of its 120 MW supply in 2022 to 2024.

### The biggest gaps

- **China has no utilisation measurement.** Operators publish commercial rates, per data centre only in Chindata's filings up
  to 2022 and mostly without a city. Construction dating is the only independent signal.
- **Capacity is the weak half of utilisation.** Two sites have a load and a capacity for the same period, and most capacity
  figures are third-party estimates or connection limits rather than installed computing.
- **Nothing is measured often enough to separate training from inference.** The finest load series is monthly, at one campus
  that burns its own fuel. The planned transformer method needs thermal imagery at a few metres several times a day, which no
  free source provides, plus training-run records from AI labs. Hourly NO₂ from geostationary satellites over North America
  (TEMPO) and East Asia (GEMS) is an untested alternative where fuel is burned.

## Donate a session

1. **Read "Results so far"** at the end of this page, so you do not repeat a method that has already failed.
2. **Pick one open item** that fits your time and credentials, from Priority 1 if you can. On the website, claimed items
   are marked live; otherwise search open pull requests for its ID, for example `RFW-07`.
3. **Claim it early.** Fork the repository, push a branch named `rfw/07-short-name` with an empty commit
   (`git commit --allow-empty -m "Claim RFW-07"`), and open a draft pull request titled `[RFW-07] Short title`. Fill in the
   template's Claim and Plan. Theories are claimed as `[T-NN]` and paid-request preparation as `[PAID-NN]`.
4. **Deliver against the acceptance line.** A negative result with numbers is a full delivery. Follow `CONTRIBUTING.md`.
5. **Hand off.** Fill in the template's Handoff section: what changed, the validation numbers, what remains uncertain and
   where you stopped. Append a dated entry to `docs/LOG.md` and mark the pull request ready for review.
6. **Get on the leaderboard.** Report the tokens the work used in the template's Donation section, measured as the
   "Token leaderboard" section of `CONTRIBUTING.md` describes. They are added to the
   [token leaderboard](https://openobservatory.info/leaderboard.html) when the pull request is merged. Counts are
   self-reported, and you can choose to be listed as anonymous.

A claims workflow labels each claim. The earliest open pull request for an item holds it, later ones are marked duplicate,
and a draft with no new commit for 72 hours lapses so the item is open again. A pull request ready for review never lapses.

Copy this into your agent to start:

```
You are donating a session to Open Observatory: https://github.com/recozers/openobservatory
Fork and clone it, then read README.md, CONTRIBUTING.md and REQUESTS_FOR_WORK.md, including "Results so far".
Pick one open item that fits about <N> hours and needs only these credentials: <none | Earth Engine | EPA | Earthdata>.
Prefer Priority 1 (China). Check it is not claimed on https://openobservatory.info/requests.html or in open pull requests.
Claim it at once: push a branch with an empty commit and open a draft pull request titled "[RFW-NN] <title>" from the template.
Keep every number traceable to a public source and a script. Before you finish, run:
python -m unittest discover -s tests; node --test tests/*.test.cjs; python tools/refresh.py --dry-run
Record the result in docs/LOG.md, including negative results, fill in the template's Handoff section with what changed,
validation numbers, remaining uncertainty and where you stopped, report the session's total tokens in the Donation section,
then mark the pull request ready for review.
```

**Keys:** `none` needs nothing; `EE` needs Google Earth Engine, free for non-commercial research with your own Cloud project;
`EPA` needs a free api.data.gov key; `Earthdata` needs a free NASA Earthdata login. Keep keys in a local `.env` and never
commit them. **Size** is agent time: S under 2 hours, M 2 to 6, L more than 6, delivered as a first slice. **Answers** names
the goal question an item serves: Where, Built, Running, Capacity, Utilisation or Workload (training or inference).

## Other ways to help

- **Star the project on GitHub.** Starring [recozers/openobservatory](https://github.com/recozers/openobservatory) helps more
  people find it.
- **Share it on Twitter.** [Post a link to openobservatory.info](https://twitter.com/intent/tweet?text=Open%20Observatory%3A%20an%20open%20source%20project%20to%20monitor%20the%20build%20out%20and%20utilisation%20of%20compute%20across%20the%20world&url=https%3A%2F%2Fopenobservatory.info) so people with a coding agent, data or
  funding to spare can find it.

## Ground rules

- Every public number traces to a free public source, a script in this repository, and a polygon with a stated confidence.
  One exception: confidential training-run labels from AI labs may train the workload model (RFW-23 gives the conditions).
- Official national statistics are inputs to test, never evidence.
- State results at the scale they were tested: how many sites, against what truth, with what uncertainty.
- Negative results stay visible. Document a failed method; do not delete it.
- Respect data licences and site terms. Do not scrape services that forbid it, never bypass a CAPTCHA, login or other access
  control, and follow the Nominatim usage policy for geocoding.
- A document's figure keeps its own quantity. Do not turn kVA into IT megawatts, add facility and IT figures, compare a load
  with a capacity from a different period, or treat a forecast as an observed load.

## Requests

Status shows standing reservations by the project's own agents. Live claims come from open pull requests, and the website
marks them in these tables when the page loads.

### Priority 1: China

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-01](#rfw-01-confirm-or-reject-the-radar-detected-structures-in-china) | Confirm or reject the radar-detected structures in China | Where | S | none | open: first pass done, 3 confirmed, 12 rejected, 24 unclear; the unclear entries need better imagery or documents |
| [RFW-02](#rfw-02-locate-every-national-computing-cluster-and-scan-it) | Locate every national computing cluster and scan it | Where | M | none, then EE | open |
| [RFW-03](#rfw-03-quarterly-construction-index-for-each-chinese-hub) | Quarterly construction index for each Chinese hub | Built | M | none | done in pull request 17; rerun when RFW-02 adds parks |
| [RFW-04](#rfw-04-land-transfer-results-for-operators-and-start-dates) | Land transfer results for operators and start dates | Where, Built | M | none | open |
| [RFW-05](#rfw-05-procurement-tenders-and-awards-including-training-and-inference-servers) | Procurement tenders and awards, including training and inference servers | Built, Running, Workload | M | none | open |
| [RFW-06](#rfw-06-stated-workload-roles-and-cloud-regions-at-chinese-campuses) | Stated workload roles and cloud regions at Chinese campuses | Workload | M | none | open |
| [RFW-07](#rfw-07-chindatas-per-data-centre-table-and-an-edgar-name-search) | Chindata's per-data-centre table and an EDGAR name search | Capacity, Utilisation | S | none | open: table done; EDGAR search and cities remain |
| [RFW-08](#rfw-08-substation-and-transmission-projects-serving-the-hub-parks) | Substation and transmission projects serving the hub parks | Capacity | M | none | open |
| [RFW-09](#rfw-09-water-withdrawal-permit-notices-for-hub-data-centres) | Water-withdrawal permit notices for hub data centres | Capacity | M | none | open |
| [RFW-10](#rfw-10-building-scale-night-lights-inside-chinese-parks) | Building-scale night lights inside Chinese parks | Running | M | EE | open |
| [RFW-11](#rfw-11-multi-storey-data-centre-positives-for-the-classifier) | Multi-storey data-centre positives for the classifier | Where | M | EE | open |
| [RFW-12](#rfw-12-dedicated-plants-and-public-stack-monitors-in-china) | Dedicated plants and public stack monitors in China | Utilisation | M | none | reserved: Astra |
| [RFW-13](#rfw-13-operator-utilisation-priors-from-chinese-filings) | Operator utilisation priors from Chinese filings | Utilisation | S | none | reserved: Astra |

#### RFW-01 Confirm or reject the radar-detected structures in China

- **Done so far:** a first pass in pull request 16 reviewed all 39 entries from before-and-after Sentinel-2 chips
  (`tools/radar_review_chips.py`, `results_cn/radar_review/`), OpenStreetMap context within 400 m and a look at web imagery:
  3 data-hall complexes (`cn_horinger_r04` inside the China Telecom park, `cn_horinger_r06` beside China Mobile's Hohhot data
  centre, `cn_qingyang_r07` inside China Telecom's Qingyang computing park), 12 not data centres (sheds, a solar array, a
  factory, a food plant, a mall, a sports hall, a university, town blocks) and 24 unclear, mostly big-box buildings that
  10 m imagery cannot tell from logistics or workshops. `data/cn_radar_review.csv` holds every verdict with its reason; the
  12 rejected entries left `data/sites.csv` and keep their polygons and radar timelines.
- **Why the rest matters:** 24 entries, 16 of them at Horinger, remain unclear, and the three confirmations rest on layout and
  OSM park names, not on a document.
- **Do next:** for each unclear entry, find a document that names the building or its plot (land transfer, environmental
  approval, procurement notice or operator statement, RFW-04 to RFW-06), or inspect sub-metre imagery when PAID-01 provides
  it, and update the verdict in the review file. Entries dated 2025 or later have no web imagery yet.
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
  documents or land transfer notices, with URLs. Scan each park with RFW-26's command and score the candidates.
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

#### RFW-05 Procurement tenders and awards, including training and inference servers

- **Why:** Procurement notices for servers, racks, UPS systems and cooling name campuses, quantities and dates, which time each
  phase of fit-out. Some Chinese server tenders state whether the servers are for training or for inference, which would be
  the most direct public evidence of workload at a named campus.
- **Do:** Search the China Government Procurement Network and the three telecom operators' procurement portals for tenders
  and awards naming campuses at Ulanqab, Horinger, Zhangbei, Zhongwei, Qingyang, Gui'an and Chongqing. Record campus, item,
  quantity, units, stated purpose (training, inference or general), date and URL. These are company procurement records,
  not statistics.
- **Deliver:** `data/cn_procurement.csv` and a note on what each portal exposes. Do not convert kVA or rack counts into IT
  megawatts, and record a stated purpose only where the notice gives it.

#### RFW-06 Stated workload roles and cloud regions at Chinese campuses

- **Why:** Before any signal can separate training from inference, each campus needs its stated role to test against.
  Public cloud regions are a start: a campus that hosts a region serves outside customers, which suggests inference and
  general cloud work.
- **Do:** For each Chinese inventory campus and hub, record public cloud regions or zones hosted there from providers' own
  region lists, and the operator's stated purpose from company announcements or filings. Record national and provincial
  planning statements separately, marked as official inputs to test.
- **Deliver:** `data/workload_roles.csv` with site, stated role, source type, quote, URL and date. A role is recorded only
  where a source states it.

#### RFW-07 Chindata's per-data-centre table and an EDGAR name search

- **Done so far:** a first slice was delivered in [pull request 15](https://github.com/recozers/openobservatory/pull/15).
  `tools/chindata_filings.py` put Chindata's per-data-centre tables for mid-2020, end-2021 and end-2022 into
  `data/cn_operator_disclosures.csv`, 166 rows whose sums match each table's totals. It relabelled the 324 MW Zhangjiakou and
  308 MW Datong figures as total capacity, not capacity in service. A hub-name search of 12 annual reports from VNET, GDS and
  Chindata found no capacity figure for Ulanqab, Zhangbei, Horinger, Gui'an or Zhongwei; GDS reports four data centres in
  Zhangbei. See `docs/cn_operator_disclosures_notes.md`, section 6.
- **Why the rest matters:** the tables give most data centres no city, so their figures cannot yet be tied to a campus. VNET's
  Ulanqab orders appear only in quarterly releases, and the Internet Archive holds none of VNET's releases from 2025 on.
- **Do:** Run EDGAR's full-text search for the five hub names across VNET, GDS and Chindata filings, including 6-K current
  reports. SEC requires a contact email in the User-Agent, so agree the address with Stuart first. Find the city of each
  remaining Chindata data centre in its other public documents, such as quarterly releases or Chinese-language land and
  environmental records.
- **Deliver:** New per-campus figures in `data/cn_operator_disclosures.csv` and locations in `data/chindata_dc_locations.csv`,
  each with its source URL and a verbatim quote.

#### RFW-08 Substation and transmission projects serving the hub parks

- **Why:** Environmental impact documents and approvals for new substations and lines often state capacity and the load they
  serve, such as a named data-centre park. That bounds the power a park can draw, the capacity half of utilisation, and dates
  when it could draw it.
- **Do:** Find substation and transmission project documents near each hub park. Record voltage, transformer capacity, stated
  served load, approval and commissioning dates, and URLs.
- **Deliver:** `data/cn_grid_projects.csv` and a note per hub. Transformer MVA is supply capacity, not IT load; keep the units.

#### RFW-09 Water-withdrawal permit notices for hub data centres

- **Why:** Water-withdrawal permit notices for data-centre projects can state permitted annual withdrawal, which bounds cooling
  water use. Most western hubs use little water, so absence is also informative.
- **Do:** Search provincial water-resources bureaus' permit notices for data-centre projects in the hub parks, and record the
  project, operator, permitted volume, date and URL.
- **Deliver:** `data/cn_water_permits.csv` and a note. Do not convert volumes to electricity until RFW-17 has a validated
  method.

#### RFW-10 Building-scale night lights inside Chinese parks

- **Why:** At park scale, VIIRS fails in China because the parks were already lit. The radar entries now give building
  outlines, which may be enough to see a single building energise inside a lit park.
- **Do:** Run `tools/ntl_timeline.py` on the radar entries and the three digitised campuses, with the comparison ring drawn
  inside the park. Test the same set-up first on a US campus inside a lit district, Prometheus at New Albany.
- **Deliver:** Lit-up months where they pass the existing rule, and a verdict on whether building scale works. Stop if the
  New Albany test shows no step.

#### RFW-11 Multi-storey data-centre positives for the classifier

- **Why:** The classifier learned from single-storey hyperscale halls. Many data centres in eastern China are multi-storey
  buildings it has never seen, which may be why six eastern hub boxes found nothing.
- **Do:** Assemble at least 30 verified multi-storey data-centre buildings from operator pages or filings, with coordinates,
  including Chinese ones where a document names the building. Extract features with `tools/cand_features.py`, retrain, and
  report leave-one-group-out results separately for single-storey and multi-storey positives.
- **Deliver:** A labelled positives file with sources, updated scores, and the per-class results in `docs/LOG.md`.

#### RFW-12 Dedicated plants and public stack monitors in China

- **Status:** reserved by Astra (B8 in `docs/PHASE2_TODO.md`). A first pass was merged on 14 September; see
  `docs/cn_stack_monitors.md`.
- **Why:** Plants built for hub parks may publish hourly stack monitoring on provincial platforms, the counterpart of EPA
  plant records, and hourly readings could show a park's daily load cycle. So far only annual reports have been reachable,
  and hourly readings at the one linked plant sit behind a CAPTCHA.

#### RFW-13 Operator utilisation priors from Chinese filings

- **Status:** reserved by Astra (B9 in `docs/PHASE2_TODO.md`).
- **Why:** VNET, GDS and Chindata report company-wide commercial utilisation, a sourced prior for campuses whose operator is
  known.

### Priority 2: Utilisation and workload, at higher time resolution

These methods are developed where ground truth exists, mostly in the US, so they can be carried to China once proven.

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-14](#rfw-14-make-the-plume-test-robust-to-start-date-and-season) | Make the plume test robust to start date and season | Utilisation | S | none | open: season-matched test and date sensitivity delivered; the site still uses the current test until the Goodyear result is understood |
| [RFW-15](#rfw-15-near-field-plume-test-for-plants-on-a-citys-edge) | Near-field plume test for plants on a city's edge | Utilisation | M | EE, EPA | open |
| [RFW-16](#rfw-16-qualify-gas-turbine-nox-calibration-plants) | Qualify gas-turbine NOx calibration plants | Utilisation | M | none | open |
| [RFW-17](#rfw-17-climate-aware-water-efficiency-for-water-derived-loads) | Climate-aware water efficiency for water-derived loads | Utilisation | M | EE | open |
| [RFW-18](#rfw-18-per-site-electricity-capacity-and-commercial-utilisation-from-more-operators) | Per-site electricity, capacity and commercial utilisation from more operators | Capacity, Utilisation | M | none | open |
| [RFW-19](#rfw-19-microsofts-metro-electricity-table-to-campuses) | Microsoft's metro electricity table to campuses | Utilisation | S | none | delivered in pull request 21 as context: no metro is one inventory campus; Boydton is a candidate site for RFW-18 |
| [RFW-20](#rfw-20-generator-fleet-and-dedicated-plant-discovery-from-eia-860m) | Generator fleet and dedicated plant discovery from EIA-860M | Utilisation, Workload | M | none | open |
| [RFW-21](#rfw-21-evidence-for-the-pending-generator-watch-records) | Evidence for the pending generator watch records | Utilisation | M | none | reserved: Astra |
| [RFW-22](#rfw-22-stated-workload-roles-for-the-rest-of-the-inventory) | Stated workload roles for the rest of the inventory | Workload | M | none | open |
| [RFW-23](#rfw-23-ai-lab-partners-with-training-run-records) | AI lab partners with training-run records | Workload | M | none | open |
| [RFW-24](#rfw-24-utilisation-ramp-curves-from-metas-18-campuses) | Utilisation ramp curves from Meta's 18 campuses | Utilisation | M | EE optional | open |
| [RFW-25](#rfw-25-implement-the-utilisation-model) | Implement the utilisation model | Utilisation | L | none | open |

#### RFW-14 Make the plume test robust to start date and season

- **Done so far:** pull request 19 added `season_zscore` and a `--sensitivity` mode to `tools/plume_batch.py`, and
  `results_no2/plume_date_sensitivity.csv` holds both tests for all 33 sites and 62 control points at seven start dates
  (documented and ±1 to 3 months). The season-matched test compares after-days with before-days of the same calendar month
  and combines months by inverse variance. It shrinks the spring-start negatives (Rosemount −3.26σ to −0.17σ, Ridgeland
  −3.45σ to −1.60σ, Mesa −1.12σ to +0.28σ), leaves Colossus 2 at 9.1σ, and puts Abilene at 3.0σ at its documented start
  but 2.3σ one month earlier under either test. Control points: none of 62 reach 2.5σ at the documented date under either
  test; across all seven start dates one control reaches 2.53σ under the current test and none under the season-matched
  (max 2.48σ; standard deviation of control z-scores 1.22 against 1.38). One campus without known on-site generation,
  Microsoft Goodyear, moves from 2.07σ to 3.14σ and stays above 2.5σ at six of seven start dates.
- **Recommendation:** adopt the season-matched test and keep 2.5σ, but require the score at the documented start and at
  the months either side to all exceed it before the site says "detected"; on that rule Colossus 2 passes, Abilene does not
  (2.34σ one month early), and Goodyear passes, which is why the site has not switched yet: Goodyear sits on the growing
  western edge of Phoenix, so a city-edge plume (RFW-15) is the first explanation to rule out, with the near-field test.
- **Do:** Using the saved daily series in `results_no2/<site>.csv`, add a season-matched version of the test and report each
  site's z-score across start dates within three months of the documented one. Re-run the 62 control points the same way.
- **Deliver:** The revised test in `tools/plume_batch.py`, per-site date sensitivity in a results file, and a recommendation on
  whether the 2.5σ rule should change, with the control-point false-positive rate under the new test.

#### RFW-15 Near-field plume test for plants on a city's edge

- **Why:** The box method cannot separate a campus plant from a nearby city's plume, which rules out Dublin and similar
  grid-constrained markets where campuses run gas plants.
- **Do:** Build a sector test within 1 to 5 km that keeps only days when the wind blows from the side away from the city and
  excludes the city from the upwind sector. Validate it first on a US plant at a city's edge with EPA hourly emissions, then
  apply it to Grange Castle.
- **Deliver:** The validation result against EPA truth and, only if validation passes, the Dublin result. A failed validation
  is a full delivery.

#### RFW-16 Qualify gas-turbine NOx calibration plants

- **Why:** The NOx calibration rests on five tall-stack coal plants, but turbine exhaust leaves from low stacks. Three gas
  candidates gave factors from 0.89 to 4.83 and are not qualified (`docs/low_stack_calibration.md`). Until turbines are
  calibrated, NOx gives relative change but no utilisation ratio.
- **Do:** Verify physical stack heights from EIA-860's environmental-equipment data or permits, check isolation from other
  sources with the EPA's point-source inventory, and align the TROPOMI overpass time with the hourly records.
- **Deliver:** Each candidate qualified or rejected with its reason, and the calibration comparison updated for the qualified
  ones.

#### RFW-17 Climate-aware water efficiency for water-derived loads

- **Why:** Water use per unit of energy depends on climate, but the current method applies one fleet-wide figure. Against
  Meta's electricity it puts individual campuses anywhere from 0.35 to about 3 times their reported load.
- **Do:** Meta publishes both water withdrawal and electricity for 18 campuses. Model withdrawal per unit energy as a function
  of local climate, such as ERA5 wet-bulb temperature, and test it leaving one campus out at a time. Apply it to Google's
  campuses only if it beats the current method.
- **Deliver:** Leave-one-out errors for the current and new methods side by side; updated derived loads and a narrower band
  only if the new method is better.

#### RFW-18 Per-site electricity, capacity and commercial utilisation from more operators

- **Why:** Utilisation needs a load and a capacity for the same period, and only Luleå and Frontier have both. US colocation
  operators also publish commercial utilisation, which the project has not collected.
- **Do:** Survey sustainability reports, data appendices and investor filings from Apple, Equinix, Digital Realty, NTT, Iron
  Mountain, Switch, CyrusOne, QTS, Aligned, and the Chinese operators GDS, VNET and Chindata, for per-site electricity,
  capacity, PUE, water and utilisation, at the finest period published. Add rows to `data/operator_disclosures.csv` with
  source URL, table and period, add missing campuses with sourced coordinates, and run `tools/ingest_disclosures.py`.
- **Deliver:** A table of which operators publish what, at what resolution and period; every new figure with its source; and
  the list of sites that now have a load and a capacity for the same period.

#### RFW-19 Microsoft's metro electricity table to campuses

- **Done so far:** pull request 21 parsed all 29 rows of Table 15 (`tools/microsoft_metro_table.py`,
  `data/microsoft_metro_fy25.csv`, 15.9 TWh in FY25) into `data/operator_disclosures.csv` as metro rows, and mapped them
  to the inventory (`docs/microsoft_metro_notes.md`). No metro is effectively one inventory campus: Phoenix, San Antonio and
  Des Moines each hold several Microsoft campuses besides Goodyear, SAT14/SAT40 and Project Osmium, and Fairwater Atlanta
  started after FY25, so every row stays context and no campus load changed. Boydton (3.11 TWh, one campus, 355 MW average)
  is the row worth turning into a site under RFW-18.
- **Do:** Map each metro row to inventory campuses. Attribute a figure only where the metro is effectively one campus, and
  record the rest as context.
- **Deliver:** Rows in `data/operator_disclosures.csv` with the attribution reasoning, and a note listing the metros left as
  context and why.

#### RFW-20 Generator fleet and dedicated plant discovery from EIA-860M

- **Why:** The generator watch list was assembled by hand from permits. The US Energy Information Administration's monthly
  generator inventory lists planned and operating generators by plant, which could flag new fleets built for data centres
  and plants that serve one campus. A dedicated plant that reports hourly to the EPA would give the first hourly load shape,
  the data needed to tell training from inference.
- **Do:** Parse the latest EIA-860M. Flag planned or new gas turbine and engine plants whose owner, name or location links
  them to a data centre, or that sit within a few kilometres of an inventory site, and check which report hourly to the EPA.
  Verify each flag against a permit or company statement.
- **Deliver:** A script, a candidate table with verification notes, and verified candidates proposed for the watch list or
  as dedicated plants. Coordinate with the RFW-21 claimant before adding watches.

#### RFW-21 Evidence for the pending generator watch records

- **Status:** reserved by Astra, working in `astra/b7`.
- **Why:** Seven planned on-site generation fleets need filing-located coordinates, a first-fire target and a valid emission
  factor before they can be watched monthly. See `docs/generator_watchlist.md`.

#### RFW-22 Stated workload roles for the rest of the inventory

- **Why:** The site's classes for AI-training campuses were assigned by hand from press coverage. Any training-or-inference
  signal needs sourced labels to test against.
- **Do:** For each non-Chinese inventory campus, record the operator's stated purpose and any public cloud region hosted there,
  with the quote, source type, URL and date, as RFW-06 does for China. Keep company statements, press reports and official
  planning documents distinct.
- **Deliver:** Rows in `data/workload_roles.csv`, and a list of hand-assigned site classes that no source supports.

#### RFW-23 AI lab partners with training-run records

- **Why:** The planned training-or-inference method (T-05) needs labels: when each campus was running training, and when it was
  serving inference. The AI labs that use these campuses, such as OpenAI, Anthropic, xAI, Google DeepMind and Meta, know when
  and where their training runs happened.
- **Do:** Map each lab to the inventory campuses it trains or serves on, from its own statements and those of its cloud and
  data-centre partners. Record the training runs labs have announced publicly, with model, dates or duration, hardware scale
  and campus where stated, and the source URL; these are coarse public labels to start from. Draft a data-sharing request for
  Stuart to send, asking each lab for training-run start and end dates by campus, the share of capacity each run used, and
  inference-serving periods, and what the lab would allow to be published. The request sets out how labels given in
  confidence are handled, using the label condition below.
- **Deliver:** `data/workload_labels_public.csv` with lab, campus, model, period, scale, source type and URL; the lab-to-campus
  map; and the draft request in `docs/ai_lab_partner_request.md`. Nothing is sent without Stuart.
- **Label condition** (decided by Stuart, 14 September 2026): labels a lab publishes, or agrees to have published, are used
  openly. Labels given in confidence may train and validate the model. They stay in `data/private/`, which git ignores, and
  never appear in commits, pull requests, issues or site data; only Stuart and the sessions Stuart runs handle them, so a
  donated session never receives them. The model's code, its aggregate validation scores and its outputs for campuses the
  labels do not cover are published, each output marked as coming from a model trained partly on confidential labels.
  Nothing is published for the campuses and periods those labels cover, and the trained model is not released without the
  lab's agreement, because either could reveal the labels.

#### RFW-24 Utilisation ramp curves from Meta's 18 campuses

- **Why:** How fast utilisation rises after a building is finished is the key prior for estimating it between annual
  disclosures. Meta's electricity series from 2011 to 2024 across 18 campuses measures the load side of that ramp.
- **Do:** Date each campus's buildings from Sentinel-2, radar, or Landsat for older ones. Fit average load per building
  against years since roof-on, with uncertainty.
- **Deliver:** Fitted ramp parameters with uncertainty in `docs/utilisation_model.md`, and the per-campus fits.

#### RFW-25 Implement the utilisation model

- **Why:** The site uses fixed rules per evidence type. `docs/utilisation_model.md` defines one model in which every source
  moves the utilisation estimate consistently, with stated priors and posteriors per site.
- **Do:** Implement section 7 of that document: hall states, the evidence likelihoods, and Monte Carlo percentiles in a
  pure-Python `utilmodel.py`. Keep the timeline JSON shape so the site needs no change.
- **Deliver:** A first slice covering reported electricity, documented capacity and roofs-only sites, behind a switch, with
  tests showing it reproduces today's bands where the rules are already calibrated.

### Priority 3: Coverage and tools

| ID | Request | Answers | Size | Keys | Status |
|---|---|---|---|---|---|
| [RFW-26](#rfw-26-radar-candidate-scan-around-every-inventory-site) | Radar candidate scan around every inventory site | Where, Built | L | EE | open |
| [RFW-27](#rfw-27-date-dark-and-grey-roofs) | Date dark and grey roofs | Built | M | EE | open |
| [RFW-28](#rfw-28-recalibrate-the-hall-classifier-with-new-labels) | Recalibrate the hall classifier with new labels | Where | M | EE | open after RFW-01 |
| [RFW-29](#rfw-29-standby-generator-permits-as-a-capacity-bound) | Standby generator permits as a capacity bound | Capacity | M | none | open |
| [RFW-30](#rfw-30-construction-timeline-on-the-map) | Construction timeline on the map | Built | M | none | open |
| [RFW-31](#rfw-31-tests-for-the-load-precedence-rules) | Tests for the load precedence rules | Tools | S | none | open |
| [RFW-32](#rfw-32-source-link-checker) | Source link checker | Tools | S | none | done in pull request 18 |
| [RFW-33](#rfw-33-crawl-public-records-and-satellite-data-for-data-centres-in-the-rest-of-the-world) | Crawl public records and satellite data for data centres in the rest of the world | Where, Built, Capacity | L | none, then EE | open |

#### RFW-26 Radar candidate scan around every inventory site

- **Why:** Radar dates construction through cloud and finds unlisted buildings, but it has run in only 12 Chinese hub boxes, 9
  US boxes and 40 night-light areas.
- **Do:** Start with Chinese sites. For each site in `data/sites.csv` without a `results_s1/<site_id>_candidates.csv`, run
  `python tools/s1_timeline.py --chip LAT LON --candidates --half 6000 --early 2021 --late 2026 --out results_s1/<site_id>`,
  then score with `tools/cand_features.py` and `tools/cand_classifier.py`. Work region by region.
- **Deliver:** A candidate file per site; a table in `docs/LOG.md` of recall at known halls and the false-positive types by
  region. Stop and report if Earth Engine quotas make a region impractical.

#### RFW-27 Date dark and grey roofs

- **Why:** Brightness dating misses dark membranes and grey roofs, as at Hyperion and at Chinese campuses such as Ulanqab. A
  vegetation and built-up index rule already failed (`docs/dark_roof_validation.md`).
- **Do:** Use radar structure-on months as labels and test other Sentinel-2 signals, such as shortwave-infrared change,
  texture or temporal variance. Validate on Hyperion, the Ulanqab long halls and all 12 Abilene halls, and check that fallow
  fields produce no false events.
- **Deliver:** A rule that dates Hyperion's two structures without a false early event and moves no Abilene date by more than
  a month, or a documented failure with the numbers.

#### RFW-28 Recalibrate the hall classifier with new labels

- **Why:** The classifier has 18 positives. RFW-01, RFW-11 and the 78 Epoch campuses with polygons can multiply that.
- **Do:** Add the new labels, retrain with `tools/cand_classifier.py`, and report leave-one-group-out results by region and
  building type. Refresh the scores of existing candidates.
- **Deliver:** Updated `results_cand/scores.csv`, results in `docs/LOG.md`, and a note on any threshold change.

#### RFW-29 Standby generator permits as a capacity bound

- **Why:** State air permits list the diesel standby generators at many US data centres. Their total rating bounds facility
  power, because campuses back up their full load, which gives a sourced capacity figure where none exists.
- **Do:** For inventory sites in Virginia, Ohio, Texas, Arizona and Georgia, find the air permits and record unit counts,
  ratings, fuel, permit date and URL. Compare total standby MW with documented capacity where both exist.
- **Deliver:** `data/standby_generation.csv` and a note giving the ratio of standby MW to documented capacity across at least
  10 sites. Propose a capacity-bound basis only if the ratio is consistent to within about 30 %.

#### RFW-30 Construction timeline on the map

- **Why:** Every dated building has a month, but the map shows only the present.
- **Do:** Add a time slider to the landing map that shows sites as they were at the end of each quarter, using the dates
  already in `site/data/timeline/`. Keep it static with no new framework.
- **Deliver:** The slider working at desktop and phone widths, and Node tests in the style of
  `tests/frontend_evidence.test.cjs`.

#### RFW-31 Tests for the load precedence rules

- **Why:** The rules deciding which figure sets a site's load have been extended several times: reported electricity, carried
  averages, water-derived figures, third-party estimates, plant records, radar entries, generator watches.
- **Do:** Write synthetic cases for `cap_in_force`, `utilisation_prior` and the evidence kinds in `build_status.py`, covering
  each basis and each carried-forward case.
- **Deliver:** Tests that fail if any precedence rule changes silently, all passing on `main`.

#### RFW-32 Source link checker

- **Why:** Hundreds of source URLs back the numbers on the site, and links rot.
- **Do:** Write `tools/check_links.py` to read every URL in `data/*.csv` and the source JSON files, check each at a polite
  rate, and look up whether an archived copy exists without submitting new captures.
- **Deliver:** A report of dead links with their archived alternatives, and the script documented in `CONTRIBUTING.md`.

#### RFW-33 Crawl public records and satellite data for data centres in the rest of the world

- **Why:** Outside the US and China the inventory has 12 sites in 11 countries, eight of them Epoch AI campuses, and dated
  buildings at 6. No radar, optical or night-light discovery scan has run there. The only regional records are official
  totals for Ireland and Singapore in `data/regional_dc_load.csv`, which can test a lead list's completeness but never place a
  site. Planning, environmental and permit records name data-centre projects, locate them and date them before construction.
- **Records:** Build a lead list, starting with sources that cover a whole country, and record what each publishes per site.
  Sources to check: OpenStreetMap features tagged as data centres, through the Overpass API; reporting by data centres of
  500 kW and above under the EU Energy Efficiency Directive, whose EU database is public only in aggregate, and the national
  registers that implement it, such as Germany's; the public registers of medium combustion plants in EU countries and the UK,
  whose entries give operator, location and rated thermal input and can include standby generators; industrial emissions
  permits for sites whose generators pass 50 MW of thermal input, such as Ireland's EPA licences; planning applications and
  zoning plans published as open data; environmental assessment portals such as India's PARIVESH, Chile's SEIA and the New
  South Wales major projects portal; PeeringDB facilities; and the property lists of listed operators and data-centre REITs.
- **Satellites:** Measure recall where the answer is known before searching. The radar scan compares 2021 with 2026, so it
  finds buildings that went up between those years. Five rest-of-world campuses have halls that Sentinel-2 dates to 2022 or
  later: DayOne Nusajaya, Google Waltham Cross, Oracle Batam, Southgate Melbourne and Start Campus Sines. Run RFW-26's command
  around each, reusing its files where they exist, and score the candidates. `tools/s2_candidates.py` runs only on five fixed
  boxes, so add a coordinate option before using it. Then scan boxes around located leads, and around announced campuses where
  no record turns up; announcements are leads, never evidence. The classifier has never seen a multi-storey data centre,
  common in dense metros, so report its scores by building type.
- **Match:** A lead is confirmed when a public record names a data centre at a location where a hall-like structure is
  visible on a chip. Add confirmed sites to `data/sites.csv` with an outline and `coords_quality`. A lead with a record but no
  structure yet stays in the leads file as a watch point with its record date, so later scans can date it. A structure with no
  record stays in the candidate files, unconfirmed. Keep each figure in its own unit: megawatts in a planning application,
  kVA, thermal input and floor area are not IT capacity.
- **Rules:** Crawl at a polite rate within robots.txt and each source's terms. At a CAPTCHA, login or ban on automated access,
  stop and record the block in the source audit. Commit extracted facts and links, not copies of documents whose terms forbid
  redistribution, and no personal details of people named in applications, such as objectors. Use commercial data-centre
  directories only by hand, as leads that must resolve to a public record. Keep the original-language text that names each
  project beside any translation.
- **Deliver:** A first slice for two areas, for example Ireland, where official totals exist to test completeness, and Johor in
  Malaysia, where DayOne Nusajaya is a known campus. `data/row_record_sources.csv` with country, source, what it publishes per
  site, access method, terms on automated access, URL, date checked and outcome; `data/row_leads.csv` with country, project,
  operator where a record names one, record type and date, stated figure and unit, location and how it was found, source URL
  and status; the crawler scripts under `tools/`; candidate and score files per scanned area; and a table in `docs/LOG.md`
  giving, per country, sources checked, leads, located leads, matched structures and new sites, plus the radar recall at the
  five campuses and the false-positive types. The site rebuilds and the tests pass. If the radar scan finds fewer than three
  of the five campuses, report the recall and stop before scanning areas without records. If Earth Engine quotas block an
  area, say so; PAID-08 covers paid compute.

## Theories to explore

Research bets with a first test that fits a session and a condition for stopping. China first.

| ID | Theory | Answers | Resolution if it works | Region | Keys |
|---|---|---|---|---|---|
| [T-01](#t-01-chinese-power-exchange-market-records) | Chinese power-exchange market records | Utilisation | Monthly or annual | China | none |
| [T-02](#t-02-hourly-no2-from-gems-over-plants-supplying-chinese-parks) | Hourly NO2 from GEMS over plants supplying Chinese parks | Utilisation, Workload | Hourly, daytime | China | GEMS data access |
| [T-03](#t-03-temporary-site-housing-as-a-construction-signal) | Temporary site housing as a construction signal | Built | Monthly | China | EE |
| [T-04](#t-04-radar-backscatter-after-the-structure-goes-up) | Radar backscatter after the structure goes up | Running | Monthly | China and global | EE |
| [T-05](#t-05-transformer-heat-as-a-load-and-workload-signal) | Transformer heat as a load and workload signal | Utilisation, Workload | Several images a day | US AI campuses, then global and China | none for the first test |
| [T-06](#t-06-hourly-no2-from-tempo-at-turbine-fed-campuses) | Hourly NO2 from TEMPO at turbine-fed campuses | Workload | Hourly, daytime | US | Earthdata, EPA |
| [T-07](#t-07-network-presence-as-a-sign-of-inference) | Network presence as a sign of inference | Workload | When registrations change | Global | none |
| [T-08](#t-08-radar-coherence-over-fan-yards) | Radar coherence over fan yards | Running | 6 to 12 days | Global | Earthdata |
| [T-09](#t-09-cooling-tower-vapour-plumes) | Cooling-tower vapour plumes | Running | Per clear scene | Global | EE |
| [T-10](#t-10-wastewater-discharge-reports-as-a-monthly-cooling-series) | Wastewater discharge reports as a monthly cooling series | Utilisation | Monthly | US | none |
| [T-11](#t-11-building-permits-and-occupancy-certificates-as-energisation-dates) | Building permits and occupancy certificates as energisation dates | Running | Monthly | US | none |
| [T-12](#t-12-crane-filings-as-construction-start-signals) | Crane filings as construction-start signals | Built | Monthly | US | none |
| [T-13](#t-13-counting-cooling-equipment-in-public-aerial-imagery) | Counting cooling equipment in public aerial imagery | Capacity | Every 2 to 3 years | US | EE |
| [T-14](#t-14-substation-transformer-bays-as-connection-capacity) | Substation transformer bays as connection capacity | Capacity | Every 2 to 3 years | US | EE |
| [T-15](#t-15-utility-retail-sales-where-one-campus-dominates) | Utility retail sales where one campus dominates | Utilisation | Annual | US | none |

#### T-01 Chinese power-exchange market records

- **Hypothesis:** Provincial power exchanges publish market participant registrations and green-power transaction notices
  that name data-centre companies and, sometimes, volumes.
- **First test:** Search the Inner Mongolia and Beijing exchanges' public notices for companies operating at the hub campuses,
  and record what each notice gives. These are company transaction records to be tested, not statistics.
- **Stop if:** no volume can be attributed to a campus.

#### T-02 Hourly NO2 from GEMS over plants supplying Chinese parks

- **Hypothesis:** GEMS, a geostationary instrument over East Asia, measures NO₂ every daylight hour. Over a plant that supplies
  a hub park, such as Shengle at Horinger, it could show the plant's daily output cycle, and with it the park's daily load
  shape, where TROPOMI sees only one moment a day.
- **First test:** Check GEMS data access and terms with Korea's National Institute of Environmental Research, then compare
  GEMS NO₂ over Shengle at TROPOMI's early-afternoon overpass with TROPOMI itself, and look for a repeatable daytime cycle.
- **Stop if:** GEMS and TROPOMI disagree at the overpass hour beyond the calibration scatter, or no daytime cycle stands out
  from day-to-day noise. Plant output is not campus load without an allocation, as RFW-12 found.

#### T-03 Temporary site housing as a construction signal

- **Hypothesis:** Large Chinese construction sites house workers and site offices in prefabricated blocks with distinctive blue
  roofs, visible in Sentinel-2. They appear when work starts and go when it ends, so they may lead radar dating and mark
  completion.
- **First test:** Track blue-roof area within 1 km of five radar-dated Chinese structures by month, and compare its appearance
  and removal with the radar structure-on month.
- **Stop if:** it does not appear at least a month before radar structure-on at three of the five.

#### T-04 Radar backscatter after the structure goes up

- **Hypothesis:** Backscatter keeps rising after a hall's structure appears, as rooftop plant and yard equipment are
  installed, which would make fit-out visible through cloud.
- **First test:** At Abilene, compare each hall's backscatter after structure-on with the roof darkening that marks fit-out in
  Sentinel-2 six to nine months later, then apply the result to the Chinese radar entries.
- **Stop if:** Abilene shows no post-structure rise distinguishable from month-to-month noise.

#### T-05 Transformer heat as a load and workload signal

- **Hypothesis:** A transformer's load losses rise with the square of its current, so its tank and radiator temperatures follow
  the load it carries, with a lag of hours set by its oil and cooling. Imaged at a few metres several times a day, a campus
  substation would give a load series, and the number and size of its transformers would give capacity. A deep-learning model
  trained on substation imagery from campuses whose AI labs have supplied training-run records (RFW-23) could then estimate
  utilisation and tell training from inference at other campuses, including in China. This is the project's planned method for
  the workload question.
- **First test, free:** Use the standard transformer loading models (IEEE C57.91 and IEC 60076-7) with load profiles for
  training and for inference, taken from public cluster traces and published descriptions of training load, to predict
  surface temperature changes. Compare them with the noise of thermal sensors that exist or are planned. Then sample the
  simulated temperatures as a satellite would, add that noise, and check whether a classifier still separates the two
  workloads.
- **Second test:** image the substation of one US campus with training-run records, across periods with and without training
  (PAID-03), and check that the temperature pattern changes with the labels. RFW-23's label condition applies: with labels
  given in confidence, only the aggregate result is published, never a dated series for that campus.
- **Stop if:** the predicted changes are smaller than achievable sensor noise at a few metres, the simulation cannot separate the
  workloads at achievable sampling, or the pilot campus shows no change between labelled periods.

#### T-06 Hourly NO2 from TEMPO at turbine-fed campuses

- **Hypothesis:** TEMPO, a geostationary instrument over North America, measures NO₂ every daylight hour. At a campus that
  runs its own turbines, such as Colossus 2, it could show whether generation is flat through the day, as training would be,
  or follows a daily cycle, as inference would.
- **First test:** Recover the known hourly NOx cycle of a large EPA-reporting plant from TEMPO first, using the plant's hourly
  records as truth. Only then look at the hourly shape at Colossus 2.
- **Stop if:** the reporting plant's hourly cycle cannot be recovered.

#### T-07 Network presence as a sign of inference

- **Hypothesis:** Inference serves users, so it needs low-latency connections: campuses listed in PeeringDB with many networks,
  or hosting a public cloud region, are more likely to run inference than isolated training campuses.
- **First test:** Record PeeringDB facility entries and hosted cloud regions for inventory campuses, respecting PeeringDB's
  usage policy, and compare with the sourced roles from RFW-06 and RFW-22.
- **Stop if:** network presence does not separate campuses with stated training roles from those with stated inference or
  cloud roles.

#### T-08 Radar coherence over fan yards

- **Hypothesis:** Operating cooling and fan yards lose radar interferometric coherence faster than idle yards.
- **First test:** Compute 6 or 12-day Sentinel-1 coherence from single-look complex data at yards and roofs before and after
  documented energisation at three US sites, then at Chinese campuses if it works.
- **Stop if:** no step appears at the three US sites.

#### T-09 Cooling-tower vapour plumes

- **Hypothesis:** On cold humid mornings, plumes above cooling towers are visible in Sentinel-2 and Landsat, and how often they
  appear tracks operation.
- **First test:** Tally plume presence on clear winter scenes at evaporative-cooled sites before and after documented start
  dates.
- **Stop if:** weather explains plume presence better than operating status.

#### T-10 Wastewater discharge reports as a monthly cooling series

- **Hypothesis:** Where a campus discharges cooling-tower water under its own federal permit, the EPA's monthly discharge
  monitoring reports give a measured monthly flow that scales with heat rejected, and so with load.
- **First test:** Search EPA ECHO for permits held by data-centre operators at inventory sites, pull their monthly flows, and
  check the seasonality against wet-bulb temperature and against Meta's electricity where both exist.
- **Stop if:** no inventory campus holds an individual permit with flow reporting.

#### T-11 Building permits and occupancy certificates as energisation dates

- **Hypothesis:** US county permit records give the month each building was certified for occupancy, which marks the step
  between a finished building and one drawing load.
- **First test:** Match permit records from counties that publish them as open data, such as Loudoun and Franklin, to inventory
  halls, and compare occupancy dates with radar structure-on and with Meta's load ramp.
- **Stop if:** fewer than 10 inventory buildings can be matched.

#### T-12 Crane filings as construction-start signals

- **Hypothesis:** The FAA's public obstruction evaluations include temporary structures such as cranes, with coordinates and
  dates, which would flag construction starts months before radar sees a structure.
- **First test:** Pull filings near 20 US inventory campuses and compare the first crane date with the radar structure-on month.
- **Stop if:** filings match fewer than half the campuses or lead radar by less than a month.

#### T-13 Counting cooling equipment in public aerial imagery

- **Hypothesis:** USDA's public-domain NAIP aerial imagery, at 0.6 to 1 m, resolves chillers, dry coolers and cooling towers.
  Count times unit capacity from Epoch's equipment catalogues in `data/epoch/` bounds the heat a campus can reject, and so its
  IT capacity. The same method in China needs purchased imagery (PAID-01).
- **First test:** Count units at five US sites with documented capacity and compare.
- **Stop if:** the estimate misses documented capacity by more than a factor of two.

#### T-14 Substation transformer bays as connection capacity

- **Hypothesis:** The number of transformer bays at a campus substation, visible in NAIP, indicates its grid connection
  capacity.
- **First test:** Count bays at campuses with documented connections, such as Luleå's 120 MW and New Albany's 250 MW, and
  compare bays times typical ratings, matching each figure's period to the imagery date.
- **Stop if:** ratings vary too much to beat a factor of two.

#### T-15 Utility retail sales where one campus dominates

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
| [PAID-01](#paid-01-sub-metre-optical-imagery-of-the-chinese-hub-parks) | Sub-metre optical imagery of the Chinese hub parks | Where, Capacity | China | 3 parks, archive scenes |
| [PAID-02](#paid-02-high-resolution-radar-over-cloudy-southwest-hubs) | High-resolution radar over cloudy southwest hubs | Built | China | 2 parks, 4 scenes each |
| [PAID-03](#paid-03-thermal-imagery-of-substations-and-transformers-at-a-few-metres) | Thermal imagery of substations and transformers at a few metres | Utilisation, Workload | US AI campuses, then China | 1 US campus with training-run records |
| [PAID-04](#paid-04-frequent-3-to-5-metre-optical-monitoring-of-chinese-parks) | Frequent 3 to 5 metre optical monitoring of Chinese parks | Built, Running | China | 5 parks, 3 months |
| [PAID-05](#paid-05-dedicated-satellite-capacity) | Dedicated satellite capacity | All | China first | Requirements only |
| [PAID-06](#paid-06-native-language-review-of-chinese-documents) | Native-language review of Chinese documents | Where, Built, Workload | China | 20 documents |
| [PAID-07](#paid-07-chinese-corporate-registry-data) | Chinese corporate registry data | Where | China | 10 campuses |
| [PAID-08](#paid-08-compute-for-continental-radar-scans) | Compute for continental radar scans | Where, Built | China | 1 province |
| [PAID-09](#paid-09-us-public-records-request-fees) | US public-records request fees | Utilisation | US | 5 requests |

#### PAID-01 Sub-metre optical imagery of the Chinese hub parks

- **Answers:** whether the radar-found structures are data halls; counts of cooling units and generator rows, which bound
  capacity as T-13 does with free US imagery; phase dating at building level.
- **Pilot:** one recent cloud-free archive scene each over Horinger, Ulanqab and Zhangbei, then one more a year apart.
- **Cost drivers:** area, resolution, archive against new tasking.
- **Success test:** RFW-01's chip-based verdicts agree with the sub-metre view, and two independent unit counts match.

#### PAID-02 High-resolution radar over cloudy southwest hubs

- **Answers:** construction progress and equipment yards at Gui'an and Chongqing, where optical imagery is rarely clear and
  Sentinel-1's 20 m cannot resolve individual halls.
- **Pilot:** four spotlight-mode scenes a quarter apart over two parks.
- **Cost drivers:** imaging mode, number of acquisitions, archive availability.
- **Success test:** hall-level structure dates that Sentinel-1 cannot give, checked against later clear optical scenes.

#### PAID-03 Thermal imagery of substations and transformers at a few metres

- **Answers:** the data for the planned utilisation and training-or-inference method (T-05). Free thermal imagery is 70 m or
  coarser, while a campus transformer is a few metres across.
- **Pilot:** repeated acquisitions, day and night, over the substation of one US campus whose AI lab has supplied training-run
  records (RFW-23), spanning periods with and without training. Then a US campus without records, to test the model. Then one
  Chinese hub park by satellite, only if the pilot shows a signal.
- **Cost drivers:** acquisitions per day and per week, which decide whether daily cycles can be seen; satellite tasking or an
  airborne survey; area. An airborne survey is not an option over China, and flights near US campuses may need permission.
- **Success test:** substation temperature patterns differ between labelled training and non-training periods beyond the
  scatter between acquisitions. Stop if the pilot shows no difference. If the labels were given in confidence, only the
  aggregate result is published (RFW-23's label condition).

#### PAID-04 Frequent 3 to 5 metre optical monitoring of Chinese parks

- **Answers:** construction and fit-out pace by month at the fastest-building parks, sharper than Sentinel-2's 10 m.
- **Pilot:** near-daily imagery over five parks for three months, compared with the radar construction index (RFW-03).
- **Cost drivers:** area, revisit, subscription length. Check research access programmes first.
- **Success test:** monthly changes that the free index misses or dates later.

#### PAID-05 Dedicated satellite capacity

- **Answers:** sustained, independent monitoring of Chinese data-centre parks, the end state if a paid pilot proves an
  observable.
- **Pilot:** none until PAID-01 or PAID-03 shows which observable works. If PAID-03 passes, the likely requirement is thermal
  imagery at a few metres several times a day over the listed parks' substations. Write the requirements: resolution,
  revisit, day and night capability, spectral bands and the list of parks, and check whether a long-term tasking contract meets them before
  considering a hosted payload or a dedicated small satellite.
- **Cost drivers:** set entirely by those requirements, so no estimate is possible yet.

#### PAID-06 Native-language review of Chinese documents

- **Answers:** whether agent extractions from land notices, procurement records, stated roles and permits (RFW-04, RFW-05,
  RFW-06, RFW-08 and RFW-09) are correct, including stated training or inference purposes.
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

- **Answers:** RFW-02, RFW-26 and RFW-33 across whole provinces or countries, if Earth Engine's non-commercial quotas block
  the scans.
- **Pilot:** one province by batch export to cloud storage, with the cost recorded per 1,000 km².
- **Cost drivers:** storage, processing and egress.
- **Success test:** candidate lists for the province that match the box scans where they overlap.

#### PAID-09 US public-records request fees

- **Answers:** utility, water and generator records for named US campuses, where agencies charge to process requests.
- **Pilot:** five requests to agencies serving inventory campuses, chosen to test T-10 and T-15.
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
  references are not yet qualified, so the megawatt range is too wide to give a utilisation ratio. None of 31 campuses
  without known on-site generation reached 2.5σ, and none of 62 control points did; under the season-matched test of
  RFW-14 one campus, Microsoft Goodyear on the edge of Phoenix, reaches 3.1σ and the controls still stay below 2.5σ. **China:** no public hourly plant data to
  calibrate against, and no hub campus is known to generate on site.
- **Operator-reported electricity** (`tools/ingest_disclosures.py`). Meta's Environmental Data Index gives annual electricity
  for 18 campuses from 2011 to 2024; the 2024 figures appeared in October 2025. The site shows the 2024 average and carries it
  into 2025 and 2026 with a wider band. A utilisation ratio needs a capacity for the same years, which only Luleå has: 0.25 to
  0.45 of its 120 MW supply in 2022 to 2024. New Albany's 250 MW connection applies only from 2026, so it cannot be compared
  with the 2019 to 2024 loads. **China:** no operator publishes electricity per campus.
- **Measured supercomputer power.** ORNL reports Frontier's average power: 11.4 MW in 2022 and 12.2 MW in 2023, about 0.54 of
  its measured peak of 21.1 and 22.7 MW. **China:** the two national supercomputers in the inventory have measured peaks only.
- **Commercial utilisation from listed operators** (`docs/cn_operator_disclosures_notes.md`). VNET reported 70.1 % of 889 MW in
  service at the end of 2025 and 73.9 % of 1,007 MW in mid-2026; GDS 75.5 % by area at the end of 2025; Chindata 80 % in
  mid-2023, its last public filing. These are company-wide shares of capacity customers use or have contracted, not how hard
  the equipment runs. Chindata's filings also give each data centre's capacity in service and capacity in customer use
  (`tools/chindata_filings.py`). In its Greater Beijing Area that was 466 of 517 MW across 18 data centres at the end of 2022,
  up from 287 of 399 MW across 13 a year earlier. New halls filled within about a year: CN11-C went from 8 to 67 of its 71 MW.
  The filings give no city for most data centres; Chindata's releases place five of them in Hebei, Shanxi or Tianjin.
  **US:** not yet collected.
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
  multi-storey buildings, so this does not show there is nothing to find. See RFW-02 and RFW-11.
- **Abilene's plume.** 2.8σ at the documented July 2025 start and 2.3σ a month earlier, with emission-controlled turbines whose
  flux is too small to convert to megawatts. The season-matched test (RFW-14) gives 3.0σ at the documented start and 2.3σ a
  month earlier, so the start-date sensitivity is not a seasonal artefact.
- **Gas-turbine calibration plants.** Three candidates gave calibration factors from 0.89 to 4.83; stack heights, isolation and
  overpass alignment are unverified. See RFW-16.
- **NO₂ from power plants next to Chinese hubs.** Usable as an activity index only at Ulanqab; the Horinger and Chongqing series
  were not usable.
- **Chinese plants linked to hub parks** (`tools/cn_stack_monitors.py`, `docs/cn_stack_monitors.md`). A first pass found 14
  plant or supply leads across 11 hubs; four are renewable projects. The Shengle plant supplies the Horinger cloud park, and its
  annual emission reports give 63 records for 2019 to 2025, but no allocation of its output to any campus is established. No
  hourly or daily stack readings were retrieved: Shengle's reading service requires a CAPTCHA and other candidate services
  timed out or returned errors. See RFW-12.
- **Radar-found structures in China.** Of 39 hall-like, dated structures, a chip review confirmed 3 as data-hall complexes from
  layout and the named parks around them, rejected 12 and left 24 unclear: at 10 m, big-box buildings cannot be told from
  logistics or workshops, and web imagery predates the entries built since 2025. See RFW-01 and `data/cn_radar_review.csv`.

### Did not work

Please do not repeat these without a new idea.

- **Roof temperature as a load signal.** At night, ECOSTRESS (70 m) showed no step at documented load changes, adjusted for
  season and weather: Abilene +0.16 ± 0.23 K at 174 MW and +0.13 ± 0.47 K at 522 MW, Rainier +0.06 ± 0.24 K at 1,078 MW.
  Daytime steps (Rainier +1.44 ± 0.60 K, Fairwater +1.35 ± 0.49 K) coincide with roofing and fit-out and cannot be separated
  from them; Landsat (100 m, daytime) gave no usable load signal either. Colossus 1's hall warmed by 1.24 ± 0.28 K at night,
  and its whole block, turbine yard included, by about the same. As a detector, nine ordinary roofs spanned −1.5 to +2.0 K at
  night against −0.75 to +1.2 K for twelve data centres. Transformer-scale heat is untested: at 70 m, the NSA Utah site's
  tentatively identified switchyard, about three pixels, read +0.25 ± 0.07 K at night over 299 frames, no different from the
  halls beside it (+0.19 ± 0.05 K), and that site's documented load did not change. See
  `docs/overnight_report_2026-09-13.md`.
- **Snow persistence on roofs.** At eight of nine sites over eight winters, operating halls held as much snow as the
  surrounding built-up land or more. At New Albany they held less in 2024 to 2026 (0.64 to 0.78 against 0.77 to 0.91) while
  new halls were being built on the campus.
- **NO₂ at campuses without on-site generation.** None of 31 reached 2.5σ; the highest was 2.09. None of 62 control points
  reached 2.5σ either.
  Season-matched (RFW-14): still none of 62 control points at any of seven start dates, but Microsoft Goodyear reaches
  3.1σ, unexplained; the spring-start negatives shrink (Rosemount −3.3σ to −0.2σ, Ridgeland −3.5σ to −1.6σ), so they were largely seasonal.
- **A campus beside large power plants.** Colossus 1's turbine phase came out at 62 ± 63 kg NOx/h after regressing out the two
  neighbouring plants' hourly EPA emissions over 594 days.
- **The box flux method at a city's edge.** At Dublin's Grange Castle it gave 964 ± 96 kg NOx/h with winter peaks and a fitted
  source 36 km downwind, consistent with the city's plume; it cannot isolate the campus plant. See RFW-15.
- **A classifier trained on OpenStreetMap footprints.** On radar candidates its AUC was 0.70, and it scored 864 of 1,133 new
  industrial structures above 0.9.
- **A national night-light scan as a detector in China.** Over 24 to 43°N and 102 to 123°E it found 4,026 newly lit areas. The
  nearest ones to the Horinger and Ulanqab campuses ranked 344th and 2,808th, and Zhangbei had none within 40 km. In the 40
  brightest campus-sized areas, 35 held a new structure of 5 ha or more; only 4 of their 249 large structures scored as
  hall-like, and the chips inspected showed industrial sites.
- **Dark-roof dating from vegetation and built-up indices.** At Hyperion it dated the north structure to June 2026, although its
  roof was visible by January, and the south structure falsely to September 2023. See `docs/dark_roof_validation.md`.
