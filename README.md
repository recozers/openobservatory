# Open Observatory

Open source project to monitor the build out and utilisation of compute across the world.

**Live site:** https://recozers.github.io/openobservatory/ is the static `site/` folder (map, list, quarterly detail),
deployed by GitHub Pages.

## Donate your coding agent's time

This project is built in sessions donated by people who point their coding agents at it for a while. The work that needs
doing and the theories worth testing are listed in [REQUESTS_FOR_WORK.md](REQUESTS_FOR_WORK.md), also published at
https://recozers.github.io/openobservatory/requests.html. Each request says how big it is, which free credentials it needs,
and what counts as done. A negative result with numbers counts as done.

To donate a session, give your agent this:

```
Fork and clone https://github.com/recozers/openobservatory, read README.md, CONTRIBUTING.md and REQUESTS_FOR_WORK.md,
pick one open request that fits my time and credentials, claim it with a draft pull request titled "[RFW-NN] <title>",
deliver it against its acceptance line, and hand off in the pull request and docs/LOG.md.
```

The full claiming and handoff steps, and the list of methods already tried and failed, are at the top of the requests file.

## What it can and cannot see

The goal is full monitoring of data-centre utilisation at the highest time resolution public data allows: where each data
centre is, when each building goes up, when it starts running, how much of its capacity is in use, and ideally whether that
use is training or inference. The planned method for that last question is a deep-learning model on detailed thermal
imagery of substations and transformers, labelled with training-run records from AI labs such as OpenAI, which know when
their runs happened. China is the priority, because public
data there, official figures above all, is notoriously unreliable. It is also where the project sees least: hourly plant
emissions, air permits, county records, public-domain aerial imagery and operator disclosures are mostly American. Each claim below is stated at the scale it was tested; `docs/MVP.md` has the details and
its corrections section.

- **Construction.** Sentinel-2 brightness dates new bright roofs to the month. At all 12 Abilene halls the dates agree with
  independent Sentinel-1 radar dates within 0 to 4 months; neither has been checked against dated construction records.
  Brightness misses dark and grey roofs, which are common in China. Radar dates those, through cloud.
- **New buildings without a prior list.** A Sentinel-1 change scan in 12 km boxes, scored by a hall classifier, put 39
  hall-like structures from six Chinese hubs on the map. They are dated by radar and not confirmed as data centres. Six
  eastern hub boxes, placed from approximate coordinates, produced none.
- **Fuel burned on site, validated in the US only.** TROPOMI NOx flux, calibrated against five EPA-monitored coal plants,
  measures generation at one campus so far, Colossus 2. Quarterly figures carry about ±20 % and megawatts are uncertain by
  2 to 3 times. None of 31 campuses without known on-site generation showed a plume. China has no public hourly plant data to
  calibrate against.
- **Electricity use comes only from operators.** Meta reports annual electricity for 18 campuses. Google's published water
  use gives an approximate load for 12 more: checked against Meta's electricity, the middle half of mature campuses fall
  within 0.6 to 1.6 times and individual campuses range from 0.35 to about 3 times. No Chinese operator publishes
  per-campus figures.
- **Not from satellites.** Night roof temperature showed no step at documented load changes (Rainier +0.06 ± 0.24 K at a
  documented 1,078 MW), and snow did not clear faster from operating halls than from other roofs.

## Layout

```
REQUESTS_FOR_WORK.md open work and theories for donated agent sessions (rendered to site/requests.html)
site/                static frontend: index.html (map), list.html (cards), map.html (quarterly detail), requests.html, research/ (thermal prototype)
build_status.py      plain-language status per site  -> site/data/status.json
build_timeline_data.py  quarterly bands + evidence    -> site/data/timeline/*.json
build_site.py        inventory + provenance           -> site/data/sites.json
tools/               s2_roof_timeline.py, s1_timeline.py (radar dating, candidate scan), cand_features.py, cand_classifier.py,
                     ntl_timeline.py, ntl_scan.py,
                     ntl_scan_tiles.py, lights_to_radar.py, snow_persistence.py, no2_plume_test.py, no2_flux.py,
                     no2_flux_quarterly.py, campd_hourly.py, fill_weather_gee.py, night_report.py, ring_analysis.py, chip.py,
                     build_requests_page.py (REQUESTS_FOR_WORK.md -> site/requests.html), serve_site.py
extract.py, model.py thermal pipeline (Landsat C1/C2 via Earth Engine, ECOSTRESS)
dcheat/              library: geometry, Landsat, Earth Engine, ECOSTRESS, WorldCover, ERA5
data/                sites.csv, capacity_timeline.csv, polygons/, observations, Epoch tables, eGRID, CAMPD pulls
results_*/           model reports, calibration tables, NO₂ results
docs/                MVP definition and results log, utilisation model, Astra task brief, thermal report, disclosure notes
```

## Running it

Regional utility/ISO figures are separate context, with metric, scope and vintage retained. See
[regional load notes](docs/regional_dc_load_notes.md) and `data/regional_dc_load.csv`.
`python tools/regional_load.py` audits compatible annual disclosures against regional context without changing site estimates.

```bash
python3.11 -m venv venv && . venv/bin/activate && pip install -r requirements.txt earthengine-api tabulate openpyxl
cp .env.example .env   # EE_PROJECT (Google Earth Engine), EARTHDATA_TOKEN (NASA), EPA_API_KEY (api.data.gov)
set -a; . ./.env; set +a
python tools/s2_roof_timeline.py data/polygons/<site>.geojson --start 2022-01-01 --out results_s2/<site>.csv
python tools/no2_plume_test.py --lat <lat> --lon <lon> --change <YYYY-MM-DD> --control <lat,lon> --out results_no2/<site>.csv
python tools/no2_flux.py --name <name> --lat <lat> --lon <lon> --start 2023-01-01 --end 2026-08-31 --out results_no2/flux_<name>.csv
python tools/s1_timeline.py data/polygons/<site>.geojson --start 2018-01-01 --out results_s1/<site>.csv      # radar dates per hall
python tools/s1_timeline.py --chip <lat> <lon> --candidates --half 6000 --early 2021 --late 2026 --out results_s1/<name>  # new structures
python tools/ntl_scan.py --box <lat_s> <lon_w> <lat_n> <lon_e> --name <name> --out results_ntl/scan_<name>.csv        # newly lit sites
python build_timeline_data.py && python build_status.py
python tools/serve_site.py   # http://localhost:8000, caching disabled so a rebuild shows on reload
```

Earth Engine is free for non-commercial use; the Earthdata login and the EPA key are free.

## Epoch inventory

`data/epoch/` contains the 86-row source inventory, dated power estimates and
saved public map annotations. Epoch AI data and annotations are used under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with attribution on the
site. Annotation geometry is kept separately from independent Sentinel-2 roof
observations; planned footprints do not prove construction or operation.

```bash
# One-time, serial address lookup; caches both matches and misses.
python tools/epoch_geocode.py
# Snapshot Epoch's published coordinates and annotated buildings.
python tools/epoch_map_snapshot.py
# Deterministic import from saved sources (no network).
python tools/ingest_epoch.py --as-of 2026-09-13
# Long EE work: one site per process, per-site logs and annual caches.
caffeinate -i python tools/epoch_roof_batch.py --workers 3
OBS_FILE=data/observations_all.csv REJ_FILE=data/rejections_all.csv RESULTS_DIR=results_gee python build_site.py
python build_timeline_data.py && python build_status.py
python tools/validate_epoch.py
python -m unittest discover -s tests -v
```

Address geocoding follows the [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/):
one process on one machine, identified User-Agent, at most one request/second,
and cached responses. Never schedule the one-time geocoder. The endpoint can be
changed with `NOMINATIM_URL` or `--endpoint`. Street/settlement centroids and distant
matches are not promoted to address-quality coordinates; Epoch's published point
is retained instead. The public map is the building-identity source, avoiding the
assumption that any large OSM roof nearby is a data centre.

`it_reported` is Epoch's IT-power estimate, distinct from measured HPL power.
`facility_design` retains facility power; the build prefers IT power when both are
available and never adds them. Tier A2 here includes sourced Epoch model estimates,
not just company statements. Future timeline rows are explicitly projections and
cannot supply today's status. Brightness dates that conflict with reported construction starts remain unresolved, with both sources retained for review. Every original row, including curated-site matches,
is preserved in `normalized_capacity_timeline.csv`; existing validated site labels
are retained. See `docs/epoch_inventory_audit.md` for per-site results and limits.
## Monthly refresh

`.github/workflows/refresh.yml` runs at 04:00 UTC on the third day of each month,
and can be started from Actions → Monthly evidence refresh → Run workflow.
The manual trigger defaults to **dry-run**: it skips Earth Engine, rebuilds from
saved evidence, validates every generated JSON file, and uploads a review artifact.
Missing service-account credentials also select dry-run, without committing.
Pull requests run the same dry-run check without access to service-account secrets.

Stuart must add `EE_SERVICE_ACCOUNT_JSON` (the full JSON key), `EARTHDATA_TOKEN`,
and `EPA_API_KEY` under Settings → Secrets and variables → Actions. Register the
service account's Cloud project with Earth Engine and enable its API. The optional
repository variable `EE_PROJECT` overrides the project in the key. Keys are read
in memory and never included in artifacts or commits. Local OAuth still works;
`GOOGLE_APPLICATION_CREDENTIALS` can alternatively point to a local key file.
See [Earth Engine service-account setup](https://developers.google.com/earth-engine/guides/service_account).

Live refresh runs one roof-extraction process per hall-bearing site from 2018,
recomputes the published NOx series listed in `data/refresh_flux_sources.csv`, and
runs the three build scripts. That manifest preserves the original seasonal
baseline and maps adjacent-plant profiles to their existing activity strips.
Research and calibration profiles are not automatically promoted into campus
generation estimates. NOx daily profiles are saved inputs: this workflow does
not fetch new daily NOx observations. Earthdata and EPA keys are reserved for
future extraction steps; the present refresh does not require them.

Live runs on `main` commit only `site/data/`, retain extracted evidence as a
30-day Actions artifact, and explicitly dispatch Pages after a successful push.
If main changes during extraction, the push fails normally; rerun on the new
inventory. Branch protection may require Stuart to permit the automation's
data commits. No force pushes are used.

Local check: `python tools/refresh.py --dry-run`. Dependencies, including
Earth Engine, tabulate, openpyxl and scipy, are pinned in `requirements.txt`.

## Provenance rule

Every number shown must trace to a free public dataset, a script in this repository and a polygon with a stated confidence.
Official national statistics are inputs to test, never evidence. Negative results stay visible.

**Exception for confidential training-run labels** (decided by Stuart, 14 September 2026). Training-run records that AI labs
supply in confidence may train and validate the training-or-inference model, on these conditions:

- The records stay in `data/private/`, which git ignores. They never appear in commits, pull requests, issues or site data,
  and only Stuart and the sessions Stuart runs handle them, never donated sessions.
- The model's code, its aggregate validation scores and its outputs for campuses the labels do not cover are published. Each
  output is marked as coming from a model trained partly on confidential labels.
- Nothing is published for the campuses and periods the confidential labels cover, not even a dated series from a pilot, since
  that would reveal the labels. The trained model is not released without the lab's agreement, because it could encode them.

Labels a lab publishes, or agrees to have published, are ordinary public data and need no exception.

## Status

Pre-MVP. See `docs/MVP.md` for what is validated, what is not, and the roadmap. To help, pick a request from
[REQUESTS_FOR_WORK.md](REQUESTS_FOR_WORK.md); issues and pull requests are welcome.

## Licence

MIT. Data sources carry their own licences: Copernicus Sentinel data (free and open), NASA ECOSTRESS and Landsat (public domain),
ERA5 (Copernicus C3S), OpenStreetMap (ODbL), Epoch AI data-centre tables (CC BY), EPA and eGRID (public domain).


Generator watch points: `python tools/generator_watchlist.py` replays saved seasonal NOx changes; `--live` refreshes three complete months with noninteractive EE credentials. The monthly workflow runs registered watches and retains their raw profiles, monthly series and first-crossing ledger. Targets, source locations, uncertainty and pending projects are documented in [the generator watch audit](docs/generator_watchlist.md). An orange watch is a calibrated regional NOx screen, not a confirmed first fire or campus electricity measurement.

Chinese plant monitors: `python tools/cn_stack_monitors.py` audits the saved annual plant emissions and report hashes.
The [eleven-hub source/access audit](docs/cn_stack_monitors.md) distinguishes thermal park services, renewable supply and
unverified nearby plants. Hourly collection remains access-limited; annual plant emissions are not campus electricity.
