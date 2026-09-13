# Astra task list — Open Observatory

You are one of two AI agents working on this repository. The other is Claude (Anthropic), who wrote the current codebase and
is pursuing method research (listed at the end so you don't duplicate it). The human owner is Stuart (GitHub: recozers).
Everything you need is in this repo; do not assume access to any prior conversation.

## The goal

Map data centres worldwide, detect new construction automatically, and estimate utilisation from public data and modelling.
Every number shown on the site must trace to a free public dataset, a script in this repo and a polygon with a stated confidence.
Official national statistics are inputs to test, never evidence. Negative results stay visible.

## What exists and what is validated (read before starting)

- `README.md` — layout, run commands. `docs/MVP.md` — what works, what does not, the roadmap and every correction so far.
- `docs/overnight_report_2026-09-13.md` — the thermal result: roof temperature does NOT track IT load, day or night. Do not
  build anything that assumes it does.
- Validated and in use:
  - Sentinel-2 roof dating per hall polygon (`tools/s2_roof_timeline.py`); roofs are dated to the month.
  - TROPOMI NO₂ plume test (`tools/no2_plume_test.py`) and calibrated NOx flux (`tools/no2_flux.py`,
    `tools/no2_flux_quarterly.py`, calibration in `results_no2/calibration_plateau.json`, ground truth via
    `tools/campd_hourly.py`). Works only where a site burns its own fuel and dominates a ~30 km box.
  - Site inventory `data/sites.csv` + `data/polygons/<site>.geojson` + `data/capacity_timeline.csv` with provenance tiers
    (A1 filing/measurement, A2 company or utility statement, B imagery-inferred, U unknown). Placeholder rows (0.5 MW,
    basis `placeholder`) mark pre-operation periods for within-site tests.
  - Site build: `build_site.py` (inventory → `site/data/sites.json`), `build_timeline_data.py` (quarterly bands + evidence →
    `site/data/timeline/*.json`), `build_status.py` (plain-language lines → `site/data/status.json`). The static site in
    `site/` reads only those JSON files. GitHub Pages deploys `site/` on push to `main`.
- Not validated / do not rely on: the campus classifier in `results_campus/` (in-domain only), adjacent-plant NOx indices
  in China except Ulanqab (see `docs/MVP.md`), the Chinese hall polygons (low confidence, operators not attributed).

## Setup

```bash
python3.11 -m venv venv && . venv/bin/activate
pip install -r requirements.txt earthengine-api tabulate openpyxl
cp .env.example .env    # EE_PROJECT (Google Earth Engine project id), EARTHDATA_TOKEN (NASA Earthdata), EPA_API_KEY (api.data.gov)
set -a; . ./.env; set +a
```
Credentials come from Stuart; never commit `.env` or anything under `secrets/`. Earth Engine calls need `EE_PROJECT`; if you
have no Earth Engine access, do the tasks marked [no-EE] first. Long Earth Engine jobs: run one site per process, under
`caffeinate -i` on macOS, and cache results under `data/cache/` (gitignored). The pattern is a shell loop over site ids with one
`python extract.py ...` call per iteration, each writing to its own log.

## Working conventions (both agents)

- Branch `astra/<task-id>` from `main`; open a pull request when a task's acceptance criteria are met. Claude uses `claude/*`.
  Stuart merges. Never force-push `main`.
- Keep this file current: set each task's Status line to `todo | in progress (branch) | done (PR #) | blocked (why)`, and
  append a dated entry to `docs/LOG.md` when you finish or get stuck (what you did, what you found, what you could not do).
- Do not edit files Claude is actively changing (listed under "Claude's research" below) without leaving a note in `docs/LOG.md`.
- Every new site needs: a row in `data/sites.csv` with a capacity source URL, polygons with `confidence` and `digitised_from`,
  and a `capacity_timeline.csv` row with a source. If you cannot source a number, use tier U and say so in `notes`.
- After changing data: `python build_site.py && python build_timeline_data.py && python build_status.py`, then check
  `site/index.html` locally (`cd site && python -m http.server 8000`) before the PR. `build_site.py` needs
  `OBS_FILE=data/observations_all.csv REJ_FILE=data/rejections_all.csv RESULTS_DIR=results_gee` in the environment.
- Style: plain Python, no new frameworks; scripts print what they did to stderr; results in CSV/JSON, never pickled objects
  except the existing classifier.

## Tasks, in priority order

### A1. Ingest the Epoch AI site list as the inventory backbone  [no-EE for steps 1–3]
Status: done (PR #2; 78 new polygon/S2 sites, 71 with accepted event dates)

Goal: the 86 sites in `data/epoch/data_centers.csv` (and their `data_center_timelines.csv` rows, which carry dated IT MW and
buildings-operational counts) become proper inventory entries.
Update (Astra, 2026-09-13): Epoch's public map now exposes coordinates and explicit Building annotations for 85/86 entries.
Use the saved, attributed `data/epoch/map_annotations.json` as the polygon source instead of assuming nearby OSM buildings are halls.
Retain cached address geocoding for comparison; use `epoch_published` when there is no reliable address match.
Annotations can include planned buildings: missing brightness detections remain unknown, not existing roofs.
The three provisional Chinese parks are distinct from the published Epoch coordinates; their unsupported Epoch MW labels are withdrawn.

Original fallback steps: (1) geocode each address (Nominatim, 1 request/s, `User-Agent` set) and record `coords_quality=geocoded_address`;
(2) for each site, fetch OpenStreetMap building footprints within 1 km (Overpass, `out geom`) and keep buildings ≥ 0.7 ha as
hall polygons (`confidence=medium`, `digitised_from=OSM way <id>`); where OSM has nothing, render a Sentinel-2 chip with
`tools/chip.py` and digitise by hand (`confidence=low`); (3) convert Epoch timeline rows into `capacity_timeline.csv` rows
(basis `it_measured_hpl` is wrong for these; use `facility_design` for "Power (MW)" and a new basis `it_reported` for
"IT power (MW)", tier A2, source URL to Epoch); (4) run `tools/s2_roof_timeline.py` for each new site from 2018;
(5) rebuild and open a PR. Accept: ≥ 40 new sites with polygons, timelines and roof dates; the status page shows them;
no site without a source.

### A2. Chinese project documents  [no-EE]
Status: done (PR #3; provincial search audit and negative-search alternative)
Goal: replace the low-confidence Chinese labels with filed figures. For `cn_horinger_cloud_valley`, `cn_zhangbei_alibaba`,
`cn_ulanqab_park` and the seven hub centroids, search for 环境影响报告表/报告书 公示 (EIA notices), 节能审查 (energy review),
土地出让公告 (land transfer) and 备案 (project filing) documents naming the campuses. Record IT load (MW), rack counts, generator
counts, coordinates and dates with the document URL in `capacity_timeline.csv` (tier A1 for regulatory filings) and
`sites.csv.notes`. Where a document gives a parcel boundary or address, correct the polygons. Accept: each of the three campuses
has at least one filed figure with URL, or a note that none was found after searching the provincial EPB and NDRC sites.

### A3. Dark-roof and grey-roof detection in the Sentinel-2 timeline
Status: blocked (proposed index rule fails Hyperion validation; draft PR #4)
`tools/s2_roof_timeline.py` dates roofs by visible brightness rising above the polygon's early baseline; dark membranes
(Hyperion) and grey Chinese roofs are missed. Add a second criterion using change against bare soil: NDVI falling below 0.15 and
a built-up index (NDBI or BSI) rising, sustained two months; report whichever fires first and label the rule. Validate on
Abilene (12 known dates), Hyperion (roofs on by Jan 2026) and the three Chinese campuses. Accept: Hyperion's two structures get
dates; Abilene's dates move by ≤ 1 month.

### A4. Candidate-site discovery from Sentinel-2 change (the automatic-detection layer)
Status: done (PR #7; 3/3 US recall, 7 Chinese candidates, all 30 chips reviewed)
Note: a radar version now exists (`tools/s1_timeline.py --candidates`, see A8/A9) and a night-lights regional scan
(`tools/ntl_scan.py`). The optical detector is still wanted as the confirmation stage: for each radar or lights candidate,
confirm a flat-roofed complex and date its roofs; the region-wide optical scan is the lower priority.
Goal: find large new flat-roofed complexes in a region without a prior list. Method (deterministic, no ML): for a region
box, build annual median Sentinel-2 composites (2022 and latest year), compute a built-up change mask (NDBI or brightness
rise plus NDVI drop), connected components ≥ 3 ha with rectangularity ≥ 0.6, and rank by area. Output a candidate CSV with
centroid, area, first-change year and a Sentinel-2 chip per candidate for review. Validate on a box around Abilene, Rainier
and Prometheus: the known campuses must be recovered. Then run on the Ulanqab and Zhangbei hub boxes. Keep Earth Engine
requests small (tile the region, use `reduceResolution` to 50 m before vectorising; `getInfo` payloads under 5,000 features).
Accept: recall = 3/3 on the US validation boxes; a ranked candidate list with chips for two Chinese boxes; a note on the
false-positive rate you observed.

### A5. Low-stack NOx calibration plants
Status: blocked (3 gas factors available; stack class, broader isolation and overpass alignment unverified; draft PR #6)
The NOx calibration uses tall-stack coal plants. Find gas-turbine or engine plants that (a) report hourly to EPA CAMPD
(`tools/campd_hourly.py <facilityId> 2023` returns rows), (b) emit ≥ 1,000 short tons NOx/yr (eGRID `data/egrid/plants_2023.csv`),
and (c) have no other large emitter within 15 km. Run `tools/no2_flux.py` on each for 2023 and add them to
`tools/no2_flux_quarterly.py` calibration with a `stack_class` column. Accept: ≥ 3 such plants with factors; a table comparing
low-stack vs tall-stack factors in `docs/LOG.md`.

### A6. Monthly refresh workflow
Status: done (PR #1; expanded 218-file workflow_dispatch dry run green)

Write `.github/workflows/refresh.yml` (manual trigger plus monthly cron) that installs the environment, runs
`tools/s2_roof_timeline.py` for every site with polygons, `tools/no2_flux_quarterly.py` for sites with flux files, then the three
build scripts, and commits `site/data/*` to `main`. Secrets `EE_SERVICE_ACCOUNT_JSON`, `EARTHDATA_TOKEN`, `EPA_API_KEY` are to be
set by Stuart in the repo settings; document that in the workflow header and in `README.md`. Earth Engine needs a service
account for non-interactive use: add a code path in `dcheat/gee.py`'s `_ee()` that uses `ee.ServiceAccountCredentials` when the
JSON is present. Accept: the workflow runs green on `workflow_dispatch` in a dry-run mode that skips Earth Engine when secrets
are absent.

### A7. Housekeeping  [no-EE]
Status: done (PR #5; name, mobile layout and contributor guide; pins/tests in PRs #1/#2)
- Pin `requirements.txt` (add earthengine-api, tabulate, openpyxl, scipy versions in use).
- `CONTRIBUTING.md`: how to add a site, the provenance rule, the branch convention above.
- Make the site name consistent (repo is openobservatory; pages say DC Watch): ask Stuart which, then apply.
- Add minimal tests under `tests/`: `build_status.py` rules on a synthetic timeline (a roofed-only site must not get a
  midpoint; a calibrated flux above 2σ must), and `tools/s2_roof_timeline.roof_on_month` on synthetic series.
- Mobile layout for `site/index.html` panel (currently overlaps the legend below 500 px).

### A8. Digitise the campuses the radar scan found  [no-EE]
Status: todo
`results_s1/<hub>_candidates.csv` (hub = ulanqab, horinger, zhangbei, guian, chongqing_shuitu, qingyang) lists new structures
2021→2026 ranked by area with a chip per candidate (`results_s1/<hub>_candNN.png`, 1.2 km, annual Sentinel-2 median). For every
candidate ≥ 5 ha, decide from the chip whether it is a data-hall complex (long white halls, cooling yards, generator rows,
substation) or something else (PV compound, logistics, factory), and for the data-hall ones add polygons
(`data/polygons/<site>.geojson`, `confidence=low`, `digitised_from=Sentinel-1 candidate <hub> rank N + S2 median chip`) and a
`sites.csv` row with tier U capacity and the coordinates. Horinger ranks 1–3 (42, 38, 33 ha) and Zhangbei ranks 1–4 are the
first to do. Then run `tools/s2_roof_timeline.py` and `tools/s1_timeline.py` on each new file. Accept: every ≥ 5 ha candidate
in the six boxes classified with a one-line reason in `docs/LOG.md`; polygons for the data-hall ones; site rebuilt.

### A9. Radar candidate boxes for every inventory site and hub
Status: todo
Run `python tools/s1_timeline.py --chip LAT LON --candidates --half 6000 --early 2021 --late 2026 --out results_s1/<site>`
for every site in `data/sites.csv` that does not yet have a `results_s1/<site>_candidates.csv` (the US AI sites are the
validation: their known halls must appear in the top ranks), and for the Chinese hub centroids not yet covered (zhongwei_hub,
qingyang_hub if missing). Note the recall at the known sites and the false-positive types in `docs/LOG.md`. Accept: a
candidates CSV per site; a table of recall.

### A10. Chinese operator filings, campus level  [no-EE]
Status: todo
`docs/cn_operator_disclosures_notes.md` found that no listed operator gives per-campus figures in its headline tables, but
Chindata's FY2022 20-F has a per-data-centre table (CN01–CN23, MW per site inside the Zhangjiakou/Datong clusters) that was
not parsed, and VNET's 6-Ks mention Ulanqab orders (235 MW, a 100 MW framework) that could not be fetched. Download the
filings from EDGAR with a declared User-Agent, parse those tables into `data/cn_operator_disclosures.csv` (campus, MW in
service, utilised, period, URL), and run an EDGAR full-text search for "Ulanqab", "Zhangbei", "Horinger", "Gui'an",
"Zhongwei" across VNET, GDS and Chindata filings. Accept: every per-campus MW figure in those filings recorded with its URL.

### A11. Operator disclosure ingest  [no-EE]
Status: todo
Write `tools/ingest_disclosures.py` that turns `data/operator_disclosures.csv` electricity rows into
`data/capacity_timeline.csv` rows (basis `facility_measured_annual`, tier A2) idempotently, so the next Meta index (each
July) is a one-line update. Then extend the CSV: Meta's other campuses that are in the Epoch list (Forest City, Altoona,
Fort Worth, Los Lunas, Papillion, Henrico, Newton, Eagle Mountain, Huntsville, DeKalb, Gallatin, Kuna, Mesa, Temple, Odense,
Clonee), Microsoft's FY25 metro table, and Google per-site water/PUE as context rows. Accept: the ingest is idempotent
(running twice adds nothing); at least ten more sites have measured annual loads once A1 adds them to the inventory.

## Claude's research (do not duplicate; results land in `docs/` and `results_*/`)

- Done 13 Sep: Sentinel-1 structure dating and candidate scan (validated at Abilene; new campuses found at Horinger and
  Zhangbei), VIIRS lit-up dates and regional scan (6/7 US greenfield campuses recovered), snow persistence (negative, closed),
  national lights scan over the hub provinces (4,026 newly lit blobs: industry dominates, lights alone are not a data-centre
  detector, so A9's radar boxes are the discriminating step). See `docs/MVP.md` and `docs/LOG.md`.
- Hall-morphology classifier on radar-candidate chips (positives: Abilene, Rainier, Prometheus, Ulanqab, Horinger candidates;
  negatives: the 40 national blobs in `results_s1/china/`, PV and logistics candidates) so the lights-then-radar chain
  can rank data centres above factories.
- Cooling-tower vapour-plume detection in Sentinel-2/Landsat as an activity indicator at evaporative sites (Climate TRACE analogue).
- Sentinel-1 amplitude variance over yards as an activity indicator (coherence needs SLC data, not in Earth Engine).
- A utilisation model from public data: documented capacity, construction stage, fit-out, combustion, operator disclosures,
  with stated priors and posteriors per site (`docs/utilisation_model.md` when it exists).
- Emission-factor work for turbine fleets (NO₂ fraction correction) and the Colossus 2 permit follow-up.

## Handoff format

When a task is done, the PR description states: what changed, how it was validated (numbers), what remains uncertain, and
which files a reviewer should open first. If you had to make a judgement call on a label or polygon, say so in `notes` and in
`docs/LOG.md`. If something in this brief is wrong or out of date, fix the brief in the same PR.
