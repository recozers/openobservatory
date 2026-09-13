# Estimating data-centre heat rejection from public thermal satellite imagery

A research prototype and, deliberately, a falsification exercise. The question
it was built to answer is:

> Does the thermal channel add anything over counting cooling equipment in
> optical imagery?

**Short answer from this build: no, not with daytime Landsat.** On the Tier A
sites available, the fitted relation between thermal anomaly and documented
capacity is indistinguishable from zero, weather covariates explain an order of
magnitude more variance than capacity, and leave-one-site-out inversion cannot
produce a bounded capacity estimate for most held-out sites. Both kill
conditions in the brief are met. Details, numbers and the reasons are in
[Results](#results). The pipeline, the site list with provenance, the polygons
and the static site are all here so the test can be re-run with the data source
the brief actually specifies (Earth Engine Collection 2 surface temperature,
ECOSTRESS for time-of-day diversity) when credentials are available.

Everything below is honest about what was and was not done.

![map](docs/map.png)

*The static site (`site/`), rendered offline: every measured site is in the
"ΔT measured, Q̂ not identified" state; hollow markers have no thermal
observations yet. Per-site panel and the model-results panel are in
`docs/panel_ornl_olcf.png` and `docs/results.png`.*

---

## 1. The estimand

Heat rejection scales roughly as `capacity × utilisation`. A thermal
observation is a noisy proxy for the **product**. Capacity and utilisation are
**not separately identified** from thermal data alone.

| Quantity | Symbol | Identified from thermal alone? |
|---|---|---|
| Thermal anomaly | `ΔT` (K) | Yes — this is the measurement |
| Implied heat rejection | `Q̂` (MW) | Yes, with wide intervals, *if* a ΔT–capacity relation exists |
| Utilisation | `U = Q̂ / (C_known × PUE)` | **Only where capacity is known independently** |

The website never labels an unidentified quantity as utilisation. It shows
five marker states: utilisation identified (Tier A capacity), `Q̂` only,
unvalidated transfer (China, not in the fit), *ΔT measured but Q̂ not
identified* (the state every site is in after this build's negative result),
and no thermal observations.

## 2. What was built

```
extract.py        polygons + site list in → tidy observation CSV + rejection log out
model.py          observations in → mixed model, LOSO report, kill conditions, Q̂ per site
build_site.py     model output → static JSON for site/
site/             MapLibre GL JS static frontend (no backend, no build step)
dcheat/           library: geometry, Landsat C1 reader, GEE backend, WorldCover, ERA5, met
tools/chip.py     Sentinel-2 true-colour chip with metre grid, for locating sites / digitising
tools/offsets_to_geojson.py   hand-digitised metre offsets → GeoJSON polygons
tools/screenshot.py           headless render check of the site
data/sites.csv, data/capacity_timeline.csv, data/polygon_specs/, data/polygons/
data/observations.csv, data/rejections.csv, data/extract_meta.json
results/model_report.json, results/loso.csv, results/site_estimates.csv, results/frames_used.csv
```

### 2.1 Data sources: specified vs. what was reachable

The build environment had no Google Earth Engine credentials and an egress
policy that blocked `epoch.ai`, `earthengine.googleapis.com` (API usable but
needs OAuth), USGS (`landsatlook`, M2M, EarthExplorer), NASA (CMR, AppEEARS,
LP DAAC), Planetary Computer, Copernicus (CDS, CDSE), OpenStreetMap/Overpass,
`sec.gov`, and most CDNs. What *was* reachable, and what the run used:

| Brief | Used in this build | Consequence |
|---|---|---|
| Landsat 8/9 **Collection 2 Level-2** surface temperature (`ST_B10`) via GEE | Landsat 8 **Collection 1 Level-1** band-10 **brightness temperature** from Google Cloud's public bucket (`gs://gcp-public-data-landsat`, ends Jan 2022) | No emissivity correction (a per-site bias, absorbed by the site random effect); no atmospheric correction (largely cancels in the annulus difference); **no data after 2021**, so every post-2021 AI site has no observations |
| ECOSTRESS L2 LSTE for time-of-day diversity | Not reachable | Every observation is at the ~10:30 local Landsat overpass. There is no night-time frame anywhere in the dataset; low solar elevation is used as the closest proxy in the conditioned fit |
| ERA5-Land hourly via GEE | ERA5 (0.25°, ~31 km) hourly from the NCAR/NSF mirror on AWS (`s3://nsf-ncar-era5`), interpolated in time | Coarser still than the 9 km the brief warns about |
| ESA WorldCover for annulus masking | ESA WorldCover 2021 v200 from its public S3 bucket | As specified |
| Epoch AI data-centre database for the site list | Unreachable; site list compiled by hand with per-site provenance | The loader for Epoch's CSV is not written because its schema could not be inspected; `in_epoch_db` is recorded per site as best knowledge |
| OpenStreetMap polygons | Unreachable; polygons hand-digitised on Sentinel-2 10 m chips (`tools/chip.py`, AWS `sentinel-cogs`) | Halls vs. chiller yards are usually not separable at 10 m; substations rarely identifiable. Polygons carry a `confidence` field and are shown in the UI |
| Cooling-equipment-count baseline | Unit counts need sub-metre imagery; a geometry-only baseline (log capacity ~ log roof area) is implemented, and `model.py` switches to counts automatically if a `cooling_units` column is supplied in `sites.csv` | The baseline used is weaker than Epoch's |
| TabPFN as secondary learner | `pip install` works but the model weights live on Hugging Face, which was blocked; a Gaussian-process stand-in with the same LOSO harness runs instead | Reported as such in the results |

The GEE backend (`dcheat/gee.py`, `extract.py --backend gee`) is written against
the public Earth Engine Python API with the exact bands, scale factors and
QA bits from the brief, produces the same CSV schema, and has **not been
executed**. Expect small API-drift fixes on first run.

One more archive quirk found on the way: Google's `index.csv.gz` for the
Landsat bucket omits **all of 2018** although the scenes are in the bucket.
`extract.py` fills such gaps by listing the bucket per path/row/year and
reading each scene's MTL (`landsat_c1.supplement_index`).

### 2.2 Stage 0 — sites, capacity provenance, polygons

Capacity provenance tiers (recorded per site and per timeline entry):

* **A1** — regulatory filing, utility document, or an independent measurement
  (TOP500 measured HPL power is treated as A1: it is an instrumented reading of
  the IT load, not an inference from imagery).
* **A2** — company or utility public statement of a design / grid-connection
  figure.
* **B** — inferred from imagery (Epoch-style). None used for fitting.
* **U** — unknown.

Fitting uses A1 + A2 only. The circularity trap in the brief (fitting a thermal
model to capacity numbers that were themselves derived from counting cooling
units) is avoided by construction: no imagery-derived capacity is in the fit.

Sites with thermal observations (Landsat 8 C1, 2013–2021):

| site | capacity (basis) | tier | why it is here |
|---|---|---|---|
| NSA Utah Data Center, Bluffdale | 65 MW facility (US Army Corps of Engineers estimate) | A1 | isolated desert site, dedicated substation, cooling towers |
| Meta Luleå | 120 MW grid connection (utility/company statements) | A2 | free-air cooled, cold climate, grew 2013–2021 |
| ORNL OLCF (Bldg 5600 complex) | 8.2 → 17.0 → 10.1 MW (TOP500: Titan, Titan+Summit, Summit) | A1 | documented **within-site capacity steps** |
| RIKEN R-CCS Kobe | 12.66 → 29.9 MW (TOP500: K computer, Fugaku) | A1 | within-site step, dense urban setting |
| NSCC Wuxi | ~0 → 15.4 MW (TOP500: Sunway TaihuLight from June 2016) | A1 | Chinese site with an independent label; within-site step |
| NSCC Guangzhou | 17.8 → 18.5 MW (TOP500: Tianhe-2 / 2A) | A1 | Chinese site with an independent label |
| Meta Prineville | unknown | U | large, isolated, campus grew from 2 to 11 buildings; the "Q̂ only" case |

Supercomputing centres are in the set because they are the only class of
facility with *instrumented* power figures in the public domain. Their caveat:
the measured number covers the named system only, and the buildings also hold
other systems; this biases documented capacity low by an unknown amount.

Facility-basis capacities (NSA, Luleå) are converted to IT-equivalent MW with
the per-site `pue_assumed` in `sites.csv`, and the model's capacity variable is
**IT-equivalent MW per hectare of measured roof** ("capacity density"): a
roof's temperature excess scales with heat flux per unit area, not with total
MW. A total-MW variant is fitted for comparison.

Also listed, **without thermal observations in this build**: xAI Colossus 1
(Tier A1 via MLGW/TVA supply approvals; polygons digitised; needs the GEE
backend), four other post-2021 US AI sites with approximate coordinates, and
seven 东数西算 hub centroids in China (see §4).

Polygons were digitised by eye on Sentinel-2 chips at 10 m. Each polygon has a
`ptype` in {hall, cooling, substation, campus}, a `confidence`, an optional
`valid_from` date for buildings that appear during the window, and the chip it
was drawn from. `campus` polygons are never measured; they only widen the
exclusion zone for the background annulus. The substation was identifiable at
one site only (NSA Utah, low confidence); the brief's first-class substation
test therefore has n = 1 and is reported descriptively.

### 2.3 Stage 1 — thermal extraction

For every Landsat 8 Tier-1 L1TP scene whose footprint contains the site
(cloud cover ≤ 70 %), `extract.py` reads only the window around the site
(tiled GeoTIFF range requests), converts band 10 DN to brightness temperature
with the scene's MTL constants, masks with the Collection 1 BQA bits (fill,
terrain occlusion, cloud, cloud confidence ≥ medium, shadow confidence ≥
medium, cirrus confidence high), and computes

```
ΔT = mean(polygon) − mean(matched background annulus)
```

The annulus is the ring 500–2000 m (site-specific overrides for compact urban
sites) around the union of all site polygons, restricted to the two most
common WorldCover classes in it after excluding water, built-up, wetland and
snow (an urban site may override this to allow built-up). Frames with fewer
than 6 valid polygon pixels (or < 60 % valid) or fewer than 200 valid annulus
pixels (or < 25 %) are written to `data/rejections.csv` with the reason.
Everything downloaded is cached under `data/cache/` so re-runs are offline
and deterministic.

### 2.4 Stage 2 — weather

ERA5 2 m temperature, 2 m dew point and 10 m u/v at the acquisition time
(linear in time between the bracketing hours), plus derived wind speed,
relative humidity, specific humidity (ISA pressure from site elevation) and
wet-bulb temperature (Stull 2011). Cooling architecture per site is carried as
a categorical (`evaporative`, `free_air_evap_assist`, `dry`, `unknown`) but is
only entered in the model when every level has at least two sites, which is
not the case here.

### 2.5 Stage 3 — model

* Primary: `ΔT ~ capacity_density + ta_c + wind_ms + tw_c + sun_elev_deg + (1 | site)`,
  statsmodels `MixedLM`, Tier A frames only. Solar elevation is included
  because every frame is a daytime frame and roof solar loading is the largest
  term in the anomaly.
* Conditioned variant: no covariates, frames restricted to wind < 3 m/s,
  5–25 °C, scene cloud < 20 %, fully valid polygon, solar elevation < 40°.
* Validation: leave-one-site-out only. For the held-out site the fitted
  relation is inverted (mean residual ΔT / slope) to an implied capacity
  density; the inversion is reported as **not identified** whenever the
  training fold's slope is within 2 SE of zero.
* Baselines: constant (geometric mean capacity of the other sites) and
  geometry (log capacity ~ log roof area).
* Within-site tests: for sites whose documented capacity changes inside the
  window, `ΔT ~ it_mw + met` on that site's frames only. This removes roof
  albedo, emissivity and background type entirely and is the cleanest test of
  the heat term the data allow.
* Kill conditions from the brief, evaluated automatically and written into
  `results/model_report.json`.

---

## 3. Results

All numbers below are from `results/model_report.json` (hall polygons,
capacity density, Landsat 8 C1 2013–2021). Re-run `python model.py` to
regenerate them.

### 3.1 Extraction

715 accepted acquisitions (1 474 polygon rows) over 7 sites, 576 rejected
frames with reasons (`polygon_too_cloudy`, `background_too_cloudy`,
`outside_footprint` — the last one is scenes whose bounding box but not
footprint contains the site). Per-site frame counts and mean hall ΔT:

| site | frames | mean ΔT (K) | sd (K) | background classes |
|---|---|---|---|---|
| Meta Luleå | 125 | +2.0 | 2.6 | tree / grass |
| NSA Utah | 98 | −1.8 | 1.1 | grass / shrub |
| ORNL OLCF | 83 | +2.9 | 1.5 | tree / grass |
| RIKEN Kobe | 73 | +0.9 | 0.8 | built-up (override) |
| NSCC Wuxi | 58 | +0.6 | 1.2 | built-up (override) |
| NSCC Guangzhou | 49 | +0.3 | 0.5 | built-up (override) |
| Meta Prineville (capacity unknown) | 224 | −1.1 | 1.9 | shrub / grass |

The sign and size of the site means are set by what the roof is compared
with: white roofs on desert shrub are 1–2 K *colder* than their surroundings
at 10:30; any building against Tennessee forest is ~3 K warmer; buildings
against other built-up land are within 1 K. The 65 MW facility reads −1.8 K,
the 8–17 MW facility reads +2.9 K.

### 3.2 Cross-site fit (Tier A, 6 sites, 486 frames)

| quantity | value |
|---|---|
| slope of ΔT on capacity density | **0.0035 ± 0.016 K per (MW/ha)** — not distinguishable from zero |
| between-site random-effect SD | 1.72 K |
| residual SD | 1.08 K |
| partial R², capacity term | 0.016 |
| partial R², met block (air temp, wind, wet-bulb, solar elevation) | 0.256 |
| share of ΔT variance that is between-site | 0.64 |
| total-MW variant (`--capacity log_it_mw`) | slope 0.06 ± 0.08 K per log MW — same conclusion |

Physically, 0.0035 K per MW/ha means that the whole plausible range of
capacity density in the set (1–30 MW/ha) moves the predicted anomaly by about
0.1 K, against a between-site scatter of 1.7 K that is explained by albedo
and background type instead.

### 3.3 Leave-one-site-out

| model | thermal (median factor error) | geometry baseline | constant baseline |
|---|---|---|---|
| all frames, covariate-adjusted | **not identified in 6 of 6 folds** (every training fold's slope is within 2 SE of zero; the raw inversions range from −11 000 to +9 000 MW) | 5.4× | 3.0× |
| conditioned (21 frames, 4 sites: clear, calm, 5–25 °C, sun < 40°) | not identified in 4 of 4 folds | 6.8× | 2.8× |
| GP stand-in for TabPFN (same LOSO harness, grid-search inversion) | median \|log error\| 3.6 (≈ 37×) | — | — |

The constant baseline (guess the geometric mean of the other sites) beats
everything, which is what a set of six facilities spanning 0.5–110 MW does to
any estimator; the geometry baseline is worse than constant because roof area
and capacity are only loosely related across supercomputer buildings and
hyperscale halls. The point is not the baselines' quality but that the
thermal inversion produces no bounded number at all.

### 3.4 Within-site capacity steps (the cleanest test)

| site | documented change | mean ΔT before → after | coefficient (K per MW, met-adjusted) | p |
|---|---|---|---|---|
| NSCC Wuxi | ~0 → 15.4 MW (TaihuLight switch-on, Jun 2016) | +0.38 → +0.73 K | +0.025 ± 0.013 | 0.056 |
| ORNL OLCF | 8.2 → 17.0 → 10.1 MW (Titan, Titan+Summit, Summit) | +3.09 → +2.64 → +2.60 K | −0.039 ± 0.038 | 0.31 |
| RIKEN Kobe | 12.7 → 29.9 MW (K → Fugaku) | +0.90 → +0.85 K | +0.002 ± 0.012 | 0.85 |
| NSCC Guangzhou | 17.8 → 18.5 MW | +0.28 → +0.24 K | −0.04 ± 0.11 | 0.73 (change too small to test) |

One site shows a step of the expected sign at the edge of significance;
doubling the load at ORNL and Kobe produced nothing. If the Wuxi result is
real it implies ~0.025 K/MW, i.e. a 100 MW facility would show ~2.5 K on a
building-sized polygon — detectable in principle, but only within one site
with the albedo term held fixed, and only for a facility whose sensible-heat
path (Wuxi uses a water-cooled system with towers, so even that is
surprising) reaches the roof pixel.

### 3.5 Substation as a first-class observable

Only one site has a substation polygon (NSA Utah, low confidence). Its mean
ΔT is −0.1 K against −1.8 K for the technical strip at the same site: the
switchyard is 1.7 K warmer than the white roofs, which is the sign expected
for transformer losses on gravel, but it is also what bare gravel does in
the sun. With n = 1 nothing more can be said; `python model.py --ptype
substation` exits with "fewer than 3 Tier A sites".

### 3.6 Kill conditions

1. LOSO error does not beat the cooling-equipment / geometry baseline — **met**
   (thermal is not even bounded).
2. Meteorological covariates explain more variance than capacity — **met**
   (0.256 vs 0.016 partial R²; the model is a weather-and-albedo detector).

Verdict written by `model.py`: `negative_result`. The website shows every
measured site as "ΔT measured, Q̂ not identified" rather than a heat figure,
and no utilisation is displayed anywhere.

### 3.7 Interpretation

With daytime Landsat brightness temperature, hand-digitised roof polygons and
six Tier A sites, the thermal channel adds nothing over geometry. The reasons
are physical, not statistical: most of a data centre's heat leaves as latent
heat from evaporative towers or as warm exhaust air that has left the pixel by
the time the roof surface equilibrates; the roof surface itself is set by
insolation and albedo; and a 100 m thermal pixel dilutes the few
sensible-heat features (substation, dry coolers) into the roof. The
between-site variance that a cross-site model must explain is 1.7 K of
albedo/background, against a heat signal that even the most favourable
within-site test puts at a few tenths of a kelvin. The brief's expectation
that "diurnal structure is where the useful signal lives" is consistent with
everything seen here: the test that remains to be run is a night-time one.

---

## 4. China (Stage 4)

The 东数西算 hubs are on the map as approximate centroids (Zhongwei, Ulanqab,
Hohhot/Helingeer, Zhangbei, Gui'an, Qingyang, Chongqing/Shuitu). Attempts to
locate the actual campuses in 16 km Sentinel-2 chips failed: candidate clusters
in Ulanqab, Helingeer and Chongqing turned out to be housing, a livestock farm
and generic warehousing, and every Gui'an scene inspected was cloud-covered
(which is itself relevant: Guizhou will give few usable thermal frames).
No 环评/能评 documents could be retrieved. Two Chinese sites with independent
(TOP500) labels — Wuxi and Guangzhou — are in the Tier A fit, which is the
seed of a Chinese label set. Every other Chinese estimate would be an
unvalidated extrapolation, and the UI says so; in this build there are none,
because the model did not identify a usable relation at all.

The bias warning in the brief stands and is displayed: a model trained on
demand-constrained US/EU/JP sites learns `P(ΔT | capacity, utilisation ≈ high)`
and will read under-utilised western Chinese hubs as smaller than they are.

## 5. What failed, and what to do next

* **Daytime brightness temperature does not see the heat.** At 10:30 the
  anomaly of a data-centre roof against its surroundings is dominated by
  albedo and background type (white roofs on desert shrub read −2 K; any
  building on Tennessee forest reads +3 K), not by the megawatts inside.
  Evaporative cooling rejects most heat as latent heat, which does not warm
  the surface at all. Only sensible-heat paths (dry coolers, exhaust air,
  transformer losses) can show up, and at 100 m thermal resolution they are
  diluted into the roof pixel.
* **Night-time and diurnal data are the missing ingredient**, exactly as the
  brief anticipated. ECOSTRESS (or Landsat night acquisitions where they
  exist) is the first thing to add. `extract.py --backend gee` is the
  intended route for Collection 2 surface temperature; an AppEEARS backend
  for ECOSTRESS is not written.
* **Polygons at 10 m are too coarse for the substation test.** Sub-metre
  imagery (or OSM `power=substation` polygons, unreachable here) is needed to
  test transformer losses as a first-class observable; the one substation
  polygon in this build is tentative.
* **Tier A sites are scarce.** Six were fitted; the brief expected 10–15.
  Candidates researched but not used for lack of an independent number:
  Facebook Prineville (no per-site figure), Facebook Los Lunas / Eagle
  Mountain / Papillion (PPA and substation figures, not load), Microsoft
  Cheyenne (tariff only), QTS / CyrusOne / Switch (10-K figures are utility
  feed or design ceilings, and `sec.gov` was blocked), Yahoo Lockport (NYPA
  16–23 MW allocation is a good Tier A label but the coop buildings are too
  small to locate at 10 m).
* **The Epoch CSV join** is the obvious next step for the AI-site list and
  Tier B out-of-sample checks; the file could not be downloaded here.

## 6. How to run

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt

# Stage 1–2 with the credential-free backend (Landsat 8 C1, 2013–2021):
python extract.py --backend gcs_c1 --start 2013-04-11 --end 2021-12-31
# Stage 1–2 as specified in the brief, once you have Earth Engine access:
earthengine authenticate
EE_PROJECT=<gcp-project> python extract.py --backend gee --start 2022-01-01 --end 2026-09-01 --append

# Stage 3
python model.py                      # hall polygons, capacity density
python model.py --ptype substation   # substation as the observable (n=1 here)
python model.py --capacity log_it_mw # total-MW variant

# Stage 5
python build_site.py
cd site && python -m http.server 8000   # any static host works; no build step

# Helpers
python tools/chip.py --lat 40.428 --lon -111.934 --half 1500 --out chips/nsa.png
python tools/offsets_to_geojson.py data/polygon_specs/*.json
python tools/screenshot.py --out shots/
```

`data/cache/` (Landsat windows, MTL files, ERA5 point slices, WorldCover
windows, the 65 MB Landsat-8 index subset) is gitignored and rebuilt on demand.

## 7. Credits and licences

* Landsat 8 Collection 1 Level-1: USGS, via Google Cloud Public Datasets.
* ERA5: Copernicus Climate Change Service / ECMWF, via the NCAR/NSF Research
  Data Archive mirror on AWS Open Data.
* ESA WorldCover 2021 v200 (CC BY 4.0), via AWS Open Data.
* Sentinel-2 L2A COGs (Copernicus / Element 84 `sentinel-cogs`), used only for
  locating sites and digitising polygons.
* TOP500 measured power figures (top500.org) for supercomputing-centre labels.
* Epoch AI, *AI Data Centers* database (CC BY), the intended source for the
  AI-site list; not reachable from the build environment, credited as the
  reference the site list should be reconciled against.
* Natural Earth (public domain) country outlines; MapLibre GL JS (BSD-3);
  OpenStreetMap tiles (© OpenStreetMap contributors) when online.
