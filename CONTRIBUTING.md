# Contributing to Open Observatory

Use Python 3.11 and a virtual environment. Install `requirements.txt`; copy `.env.example` to `.env` only for live data extraction. Never commit credentials, `.env`, `secrets/`, or Earth Engine caches.

## Add a site

1. Add a stable `site_id` to `data/sites.csv`, coordinates with their quality, operator, country, source URL and explanatory notes. Use tier **U** and leave capacity blank when no attributable number exists. A hub centroid is not a campus.
2. Add `data/polygons/<site_id>.geojson`. Each hall needs a unique `name`, `ptype: hall`, `confidence` and `digitised_from`; retain its source URL and state any geometry repairs. Do not infer that every large industrial roof is a data hall. Planned footprints require independent dating and must not be labelled existing roofs after a non-detection.
3. Add dated, sourced rows to `data/capacity_timeline.csv`. State the basis and units. A1 means regulatory filing or measurement; A2 means a sourced company/utility statement (Epoch estimates are explicitly qualified); B is imagery inference; U is unknown. Facility supply, IT capacity, annual consumption and actual operating load are different quantities. Never turn kVA/MVA into IT MW, sum overlapping facility and IT estimates, or treat a forecast as an observed load.
4. With Earth Engine configured, extract roof evidence using `tools/s2_roof_timeline.py`. Run one site per process, cache results under `data/cache/`, and use `caffeinate -i` on macOS for long jobs. Preserve negative results and unresolved dates. The Epoch importer and its validator are described in README.
5. Rebuild and inspect the public page:

```sh
export OBS_FILE=data/observations_all.csv
export REJ_FILE=data/rejections_all.csv
export RESULTS_DIR=results_gee
python build_site.py
python build_timeline_data.py
python build_status.py
python -m unittest discover -s tests -v
python tools/serve_site.py   # http://localhost:8000, caching disabled
```

Open the changed site at desktop and narrow phone widths. Check source links, unknowns, date bounds, and that a roof-only estimate has no midpoint. Run `python tools/validate_epoch.py` for inventory changes. Use `python tools/refresh.py --dry-run` to validate saved evidence without Earth Engine.

## Donated agent sessions

Open work is listed in `REQUESTS_FOR_WORK.md`. Pick an open request, search open pull requests for its ID, then claim it
by pushing `rfw/<NN>-short-name` to your fork and opening a draft pull request titled `[RFW-NN] Short title` with your plan.
A claim with no new commit for 72 hours lapses. Theories are claimed the same way as `[T-NN]`. To add or change a request,
edit `REQUESTS_FOR_WORK.md` and run `python tools/build_requests_page.py`; a test fails if `site/requests.html` is stale.

## Work and review

Start `astra/<task-id>`, `claude/<task-id>` or, for donated sessions, `rfw/<NN>-short-name` from current `main`. Keep changes reviewable and avoid files the other agent is actively changing; record necessary shared-file changes in `docs/LOG.md`. Update the relevant status in `docs/ASTRA_TODO.md` and append a dated log entry with results and limitations.

Open a pull request with what changed, validation counts, uncertain labels or geometry decisions, and the first files a reviewer should read. Stuart merges; do not merge or force-push `main`. For dependent PRs, identify their base and merge order.

Every public number must trace to a free public source, a repository script and an attributable polygon with stated confidence. Negative findings remain visible. Thermal roof temperature is not a validated utilisation measurement; nearby power-plant emissions are not a campus's electricity consumption.
