# Open Observatory

Tracking data-centre construction and activity from free satellite data, with a source for every claim.

**Live site:** the `site/` folder is a static page (map, list, quarterly detail) deployed by GitHub Pages.

## What it can and cannot see

- **Construction, reliably.** Sentinel-2 (10 m, every few days) dates each hall's roof to the month and shows fit-out afterwards.
- **Fuel burning on site, where it happens.** Sentinel-5P TROPOMI NO₂ plumes, wind-rotated and composited over hundreds of days,
  give a monthly emission rate calibrated against five EPA-monitored power plants. At a site running its own turbines that is a
  monthly on/off/ramp readout of generation; absolute megawatts are uncertain by 2–3×, month-to-month changes are good to ~20 %.
- **Not electricity use.** Roof temperature does not track IT load, day or night: tested with ECOSTRESS and Landsat at twelve
  sites against nine control roofs (`docs/overnight_report_2026-09-13.md`). Load figures on the site are documented capacity
  with a stated utilisation assumption unless marked as measured.

## Layout

```
site/                static frontend: index.html (map), list.html (cards), map.html (quarterly detail), research/ (thermal prototype)
build_status.py      plain-language status per site  -> site/data/status.json
build_timeline_data.py  quarterly bands + evidence    -> site/data/timeline/*.json
build_site.py        inventory + provenance           -> site/data/sites.json
tools/               s2_roof_timeline.py, no2_plume_test.py, no2_flux.py, no2_flux_quarterly.py, campd_hourly.py,
                     fill_weather_gee.py, night_report.py, ring_analysis.py, chip.py
extract.py, model.py thermal pipeline (Landsat C1/C2 via Earth Engine, ECOSTRESS)
dcheat/              library: geometry, Landsat, Earth Engine, ECOSTRESS, WorldCover, ERA5
data/                sites.csv, capacity_timeline.csv, polygons/, observations, Epoch tables, eGRID, CAMPD pulls
results_*/           model reports, calibration tables, NO₂ results
docs/                MVP definition, overnight thermal report, the original prototype README
```

## Running it

```bash
python3.11 -m venv venv && . venv/bin/activate && pip install -r requirements.txt earthengine-api tabulate openpyxl
cp .env.example .env   # EE_PROJECT (Google Earth Engine), EARTHDATA_TOKEN (NASA), EPA_API_KEY (api.data.gov)
set -a; . ./.env; set +a
python tools/s2_roof_timeline.py data/polygons/<site>.geojson --start 2022-01-01 --out results_s2/<site>.csv
python tools/no2_plume_test.py --lat <lat> --lon <lon> --change <YYYY-MM-DD> --control <lat,lon> --out results_no2/<site>.csv
python tools/no2_flux.py --name <name> --lat <lat> --lon <lon> --start 2023-01-01 --end 2026-08-31 --out results_no2/flux_<name>.csv
python build_timeline_data.py && python build_status.py
cd site && python -m http.server 8000
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

## Provenance rule

Every number shown must trace to a free public dataset, a script in this repository and a polygon with a stated confidence.
Official national statistics are inputs to test, never evidence. Negative results stay visible.

## Status

Pre-MVP. See `docs/MVP.md` for what is validated, what is not, and the roadmap. Issues and pull requests welcome.

## Licence

MIT. Data sources carry their own licences: Copernicus Sentinel data (free and open), NASA ECOSTRESS and Landsat (public domain),
ERA5 (Copernicus C3S), OpenStreetMap (ODbL), Epoch AI data-centre tables (CC BY), EPA and eGRID (public domain).
