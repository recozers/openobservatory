# MVP: open monitoring of data-centre construction and activity from free satellite data

Working name: DC Watch. Status: pre-MVP, 13 September 2026. Everything here runs on free data with a
Google Earth Engine account and a NASA Earthdata login; no satellite tasking, no paid imagery.

## What the MVP does

For a curated list of sites (`data/sites.csv` + `data/polygons/*.geojson`), produce a monthly report with:

1. **Construction and fit-out timeline** per hall from Sentinel-2 (`tools/s2_roof_timeline.py`).
   Validated: Abilene's twelve hall blocks dated to the month; roofs darken 6-9 months after completion as equipment is fitted.
   This is the strongest layer: new capacity cannot be built without being seen at 10 m every few days.
2. **On-site combustion indicator** from TROPOMI NO2 with a wind-resolved plume test (`tools/no2_plume_test.py`).
   Validated at Abilene (on-site gas plant from 2025): downwind-minus-upwind NO2 rose 1.2 ± 0.45 units after the plant started,
   with the crosswind pair and a rural control flat, and the excess largest at low wind speed. Applies to sites with turbines,
   diesel fleets or captive plants; ~5 km resolution, so only where the site is the dominant local source.
3. **Thermal context** from ECOSTRESS (night) and Landsat (day) (`extract.py`, `model.py`, `tools/night_report.py`).
   Validated as a NEGATIVE: roof temperature does not track IT load, day or night (see `docs/overnight_report_2026-09-13.md`).
   Kept for block-scale night anomalies at dense sites and as the documented limit of the method.

## What it does not do, and says so

- No load estimate for grid-fed sites. Transformer loss heat is real but needs 2-5 m night thermal, which is tasked commercial imagery.
- No utilisation from thermal: roofs are decoupled from load. For sites with on-site combustion, the NO2-flux method (update below) gives calibrated generation with a stated emission-factor range.
- No automatic discovery of unknown campuses yet. The embedding classifier (`results_campus/`) works in-domain (AUC 0.82) but
  fails under domain shift; it needs hard negatives from the regions to be scanned and a structural prior.

## Site inventory

- 12 study sites with hall / cooling / substation polygons and capacity timelines with provenance tiers (A1 measured, A2 stated, U unknown).
- 9 control roofs (warehouses, factories) measured identically, so every claim has a negative class.
- Epoch AI data-centre tables in `data/epoch/` (86 sites, timelines, chip counts, chillers, cooling towers) for expansion.

## Running it

```bash
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt earthengine-api
set -a; . ./.env; set +a            # EE_PROJECT, EARTHDATA_TOKEN
python tools/s2_roof_timeline.py data/polygons/<site>.geojson --start 2022-01-01 --out results_s2/<site>.csv
python tools/no2_plume_test.py --lat <lat> --lon <lon> --change <YYYY-MM-DD> --control <lat,lon> --out results_no2/<site>.csv
python extract.py --backend ecostress --site-ids <site> --start 2022-01-01 --end <today> --no-weather --out data/observations_eco.csv --append
python tools/fill_weather_gee.py data/observations_eco.csv && python tools/night_report.py
```

## Roadmap to a public MVP

1. One command per site that runs all three layers and writes `reports/<site>/<month>.md` + JSON.
2. Add the 东数西算 hubs with hand-verified polygons for the Epoch-listed Chinese campuses (VNET Ulanqab, Huawei Horinger, Alibaba Zhangbei), plus their captive plants for the NO2 layer.
3. Seasonal matching and a source-strength estimate for the NO2 layer; a second validated site with on-site generation (Colossus is unusable: TVA plant next door).
4. Winter snow-cover on/off indicator for cold-climate sites (Sentinel-2 NDSI over yards): designed, untested.
5. A static site (the existing `site/` MapLibre frontend) that renders the monthly reports.
6. Licence (Apache-2.0 or MIT), CONTRIBUTING, and the negative results kept prominent: the credibility of the project rests on them.

## Provenance rule

Every number shown must trace to a free public dataset, a script in this repository and a polygon with a stated confidence.
Official national statistics are inputs to test, never evidence.

## Update, 13 Sep 2026 afternoon: NO2-flux generation estimate (the utilisation result)

`tools/no2_flux.py` estimates a point source's NOx emission rate from TROPOMI NO2 (wind-rotated along-wind line densities from
ERA5 100 m wind, composited over hundreds of days, EMG fit or near-source plateau).  Calibrated blind against five coal plants with
EPA CAMPD hourly NOx at the overpass hours (`results_no2/calibration_2023.csv`): satellite/truth factor 2.66 ± 0.18 (plant-to-plant
scatter ± 0.80, i.e. ±30 %).  `tools/campd_hourly.py` fetches the hourly truth (needs `EPA_API_KEY`).

Colossus 2 (Southaven turbine yard, 59 uncontrolled gas turbines reported from late 2025): near-source NOx flat 2023 to Oct 2025,
+190 kg/h in Nov 2025, +760 in Dec, 530-800 kg/h every month of 2026.  Season-matched 2026 vs 2023-25: +1.00 ± 0.09 mol/s NO2 =
580 ± 180 kg NOx/h (4,600 short tons/yr).  The co-located Southaven combined-cycle plant is flat at 21-25 kg/h in CAMPD, so it is
not the source.  At uncontrolled-turbine emission factors of 0.5-1.0 kg NOx/MWh this is 580-1,160 MW of generation: the fleet is
running at high load (61-123 % of Epoch's 946 MW site figure; >100 % of the 495 MW first reported for 59 turbines, so the fleet or
its emission factor is larger than reported).  A paused or lightly loaded site would show < 200 kg/h.  This is the first
quantitative, free-data activity/utilisation measurement in the project; it applies to sites with on-site combustion.

Abilene: the campus NO2 change (+70 ± 36 kg/h calibrated) exceeds what its permit-limited turbines can emit at full load
(0.14 lb/MWh x 360 MW = 23 kg/h, TCEQ registration 177263), so it is mostly construction and generator diesel; turbine load is not
separable there.  Colossus 1 shows no detectable change (urban background, and turbines partly removed in 2025).

### Correction and calibration detail (13 Sep 2026, evening)

Two calibrations exist: fit-based (EMG emission rate, factor 2.66 ± 0.18, scatter ±30 %) and plateau-based (mean flux 1-9 km
downwind minus far upwind, factor 4.68 ± 0.20, scatter ±16 %, `results_no2/calibration_plateau.json`). Monthly series use the
plateau method (`tools/no2_flux_quarterly.py`), with a season-matched pre-start baseline subtracted for sources that switched on.
The Colossus 2 figure above (580 kg/h) mixed the two; the consistent plateau value is **+1,020 ± 180 kg NOx/h** in 2026
(quarterly: 494 in 2025Q4, then 825, 1,206, 1,281 kg/h), i.e. 4,600-8,000 t/yr.

Caveat on converting to MW: the calibration plants are tall-stack coal units whose exhaust is almost all NO; gas-turbine exhaust
carries a much larger NO2 fraction, so a coal-calibrated factor likely overstates turbine NOx by up to 2x. The emission-factor range
for the Southaven temporary fleet is therefore set to 0.5-1.5 kg/MWh (band 690-3,060 MW, midpoint 1,280 MW against Epoch's
946 MW site). The robust statements are: the source switched on in Nov-Dec 2025, has run every month since at a level consistent
with the whole ~1 GW site at full load, and its month-to-month changes are resolved to about ±20 %. Absolute MW is uncertain by 2-3x.

China: three hub campuses added from 10 m chips (Horinger cloud valley, Zhangbei west halls, Ulanqab park; hall blocks low
confidence, operators not attributed; Epoch power figures as A2 labels). Adjacent fossil plants from the WRI database are measured
with the same NO2-flux tool (CPI Zhongwei cogen 4 km, Jingneng Jining 700 MW adjacent to the Ulanqab park, Shengle cogen 5 km from
Horinger, Liangjiang gas near Chongqing). Their absolute NOx is dominated by winter regional haze and district heating, so it is shown
as an activity index (evidence strip), never as a megawatt band. Sentinel-2 roof dating now uses each polygon's own early baseline;
Ulanqab's long halls were roofed in Nov 2025.

Adjacent-plant indices, honest scoreboard: Ulanqab (Jingneng Jining, 700 MW, adjacent to the park) shows the cogeneration
signature, 2,600-3,200 kg/h in heating quarters and ~0 in summer; Zhongwei (CPI cogen) similar but noisier; Horinger (Shengle cogen)
is unusable because the 6.7 GW Tuoketuo plant and Hohhot sit inside the along-wind window and drive the series negative in some
quarters. The method needs an isolated source within ~15 km; where that fails the strip is shown but should not be read.

## Front page (13 Sep 2026, evening): plain-language status per site

`build_status.py` turns each site's evidence into four lines (built / running / load / confidence) with "how we know" and one key
series; `site/index.html` + `site/cards.js` render them. Rules: "on-site generation detected" needs a calibrated NOx flux above 2 sigma
and 100 kg/h; "combustion activity detected" needs the site-level plume test change >= 2.5 sigma at the documented start; otherwise
"presumably" from documented capacity, "unknown" when only roofs exist, "not yet" otherwise. The map is at `map.html`, the thermal
prototype at `research/`.

## Why the campus classifier did not transfer to China, and what limits NO2 there

The embedding classifier was trained on OSM-tagged data centres against metro warehouses (US, EU, Chinese cities); steppe towns and
county seats are outside that distribution, so a linear model scores cemeteries and temples as data centres. It is a training-data
problem (no negatives from the target regions, no structural features), not a Chinese-specific one. The NO2 method itself is physics
and transfers, but three things weaken it in China: no hourly emissions ground truth (the calibration must be carried over from US
plants), ultra-low-emission coal controls that make plant plumes small, and regional winter haze plus multiple large sources inside
the 30 km along-wind window (Tuoketuo, Hohhot) that swamp a single plant. Rural, isolated hubs (Ulanqab's park with its adjacent
plant) work; Horinger and Chongqing do not.

## Activity proxies used elsewhere, and what they would give here

- Power-plant plumes from Sentinel-2/Landsat/PlanetScope with ML, trained on hourly generation data (Climate TRACE: Carbon Tracker,
  WattTime, TransitionZero): estimates plant utilisation over 30-day windows. The direct analogue is cooling-tower vapour plumes at
  evaporative data centres; worth a pilot at Utah (towers) and any site with visible plumes in cold months.
- Parking-lot car counts, truck counts, port and stockpile imagery (hedge-fund "alternative data"): needs sub-metre imagery; for data
  centres it measures staff and contractors, which track construction and commissioning, not IT load.
- Night-time lights (VIIRS DNB) for GDP-scale activity: too coarse for a campus.
- Mobile-device foot traffic (SafeGraph/Advan Patterns, Placer.ai) and Google Maps "popular times": legitimate paid datasets exist;
  Google's popular-times data is only present for places with many visits and its scraping breaks Google's terms. For a data centre,
  visits measure people on site, and operating campuses run with tens of staff regardless of load, so this is a construction and
  commissioning indicator at best. It could still flag a shutdown (contractors leaving) or a fit-out surge.
- Job postings, contractor announcements and procurement notices: cheap, public, and the best early indicator of fit-out and
  expansion; not of load.

## Pilots, 13 Sep 2026 (night): radar dating, radar candidate scan, night lights, snow

Three new layers were tested against sites with known dates, plus one indicator that failed. Tools: `tools/s1_timeline.py`,
`tools/ntl_timeline.py`, `tools/ntl_scan.py`, `tools/ntl_scan_tiles.py`, `tools/snow_persistence.py`, `tools/pilot_compare.py`,
`tools/scan_check.py`. Results in `results_s1/`, `results_ntl/`, `results_snow/`.

**Sentinel-1 radar structure dating (validated).** Monthly median VV backscatter per hall polygon on one relative orbit. A hall
is "structure on" in the first month whose VV is at least 4 dB above the 20th percentile of all earlier months and stays there
for six months. At Abilene all 12 halls fall within 0–4 months of the Sentinel-2 roof dates (9 within 2 months; radar usually
leads the membrane by a month, since walls and steel reflect before the roof is white). Over Hyperion's farmland, whose VV
swings 3 dB with the seasons, the rule gives no false positive. In China it dates blocks that brightness dating could only call
"existing" because Inner Mongolian bare soil is already bright: Ulanqab long halls 2024-09 (Sentinel-2 said 2025-11, a grey
roof), Horinger block A 2024-06 and block B 2019-06, Zhangbei west halls 2020-01. The site build now uses the radar date when
Sentinel-2 says "existing" or "not yet", or when it lags radar by more than three months; the basis is recorded per hall.

**Radar candidate scan (works, including under cloud).** In a 12 km box, 20 m blobs where the annual-median VV rose at least
4 dB between 2021 and 2026 and now exceeds −8 dB, at least 1 ha, ranked by area, each with a chip cut from the cloud-masked
annual Sentinel-2 median. Ulanqab: the two largest candidates (32 ha and 12 ha, +9 dB) are the campus itself; an 8 ha candidate
5 km away is a photovoltaic compound. Horinger: 99 candidates; the top three (42, 38, 33 ha, +10 to +12 dB, at 40.535/111.815,
40.584/111.847, 40.581/111.862) are new white-hall campuses that are not in the inventory. Zhangbei: four new 9–17 ha
structures 2 km south of the digitised halls (41.18, 114.70–114.75); the digitised halls date from 2020 and correctly do not
appear as new. Gui'an, where every individual Sentinel-2 scene is cloudy: 25 candidates, the two largest 22 and 21 ha, with
usable chips from the annual median. This is the construction-detection chain for China: radar flags and sizes new structures,
the optical median gives a person a chip, Sentinel-2 dates the roof where it can.

**VIIRS night lights (construction and energisation, not load).** Daily Black Marble radiance (500 m), campus minus a 3–10 km
annulus, monthly medians; a site "lights up" in the first month at least max(5 MAD, 5 nW/cm²/sr) above the median of all earlier
months, sustained six months. Every greenfield US campus lights up two to six months after ground-breaking: Rainier 2024-08,
Fairwater 2024-10, Abilene 2024-12 (then climbing to +120 nW/cm²/sr by 2026 as build-out continued), Hyperion 2025-12. Colossus 1
steps up in 2025-01, six months after IT load began: lights follow yard and site expansion, not the operating date. The
nineteen other sites (legacy campuses, supercomputers, the Chinese campuses inside already-lit parks, hub centroids) show no
step since 2019, as expected. As a regional scan (3-month medians, latest
versus three years earlier, brightening ≥ 10 nW/cm²/sr and ratio ≥ 3, blobs ≥ 2 pixels) over 150 km boxes, it recovers six of
seven US campuses within 0.4 km (Hyperion's blob centroid is 2.3 km from the stored coordinate) with 8–22 blobs per box, and the
campus is the first or second blob in five boxes. It misses Colossus 1 (brownfield inside an already-lit industrial area) and the
three Chinese campuses (already-lit parks, build-out before the three-year window): in China the radar stage does the work.

**Winter snow persistence (negative, closed).** Sentinel-2 snow fraction per polygon on days when the built-up ring is at least
40 % snow-covered. Operating halls hold snow like every other roof: Luleå 0.97–1.00 against a ring of 0.97–1.00 over eight
winters (11–23 snow days each), the NSA technical strip 1.0 every winter, Rainier 0.97–1.00 in its operating winters while the
control factory sheds to 0.33–0.84, the Chinese campuses equal to their rings. The only low values are construction winters with
roofs not yet on. Consistent with the thermal result: hall roofs are cold roofs.

Nothing here changes a load band. Radar dates and lit-up months appear in "how we know"; the utilisation question is unchanged.
Next: the tiled lights scan over the western hub provinces (`tools/ntl_scan_tiles.py`), polygons for the campuses the radar
scan found (Astra task A8), and a Sentinel-2 roof timeline run automatically for every radar candidate.

## Operator disclosures, 13 Sep 2026 (night): the first measured loads on the site

Meta publishes annual electricity per campus in its Environmental Data Index (2011–2024). `data/operator_disclosures.csv`
holds the series with URLs; `data/capacity_timeline.csv` carries them as `facility_measured_annual` rows (tier A2), which
now take precedence over any other capacity figure in the site build and give a band of ±10 % around the year's average.
Prineville: 8 MW average in 2011 to 197 MW in 2024 (1,728 GWh). Luleå: 54 MW in 2024 against a 120 MW grid feed, with a dip
to 30 MW in 2022 that no satellite method here could have seen. New Albany: 91 MW in 2023, 60 MW in 2024 against a 250 MW
connection. ORNL Frontier: 12.2 MW average in 2023 against 21–23 MW at HPL. These ratios replace the 0.5–1.0 utilisation
assumption for cloud campuses (now 0.2–0.6) and supercomputers (0.4–0.9); AI-training campuses keep 0.5–1.0 until a
disclosure or filing calibrates them. The site's "running" line says "operator reports an average IT load of N MW in YEAR"
for these sites, confidence high. Chinese listed operators (VNET, GDS, Chindata, Sinnet, the three telcos) publish
company-wide capacity and utilisation only; the per-campus figures that exist are opening press releases and park-committee
statements, which stay outside the evidence (`docs/cn_operator_disclosures_notes.md`).

## National scan, 13 Sep 2026 (late): what lights-then-radar finds across the Chinese hub provinces

`tools/ntl_scan_tiles.py` over 24–43 N, 102–123 E (110 tiles of 2°, July–September 2026 against the same months of 2022)
returns 4,026 newly lit blobs; the brightest are ports, coal-chemical and industrial parks of 15–100 km², and the hub
campuses rank in the hundreds to thousands because their parks were already lit. A campus-like band (2–30 pixels, 15–130
nW/cm²/sr now, dark before) keeps 3,212. `tools/lights_to_radar.py` then ran the radar candidate scan on the 40 brightest
band blobs: 35 contain a new structure of at least 5 ha and 27 one of at least 20 ha, and the chips are factories,
petrochemical sites and logistics parks. Conclusion: night lights are a "new large lit site" alert, not a data-centre
detector; the discriminating step is hall morphology on the radar candidates (long parallel white halls, cooling yards,
generator rows), which the Horinger and Ulanqab boxes show the radar scan can serve up. Inside a hub box the campuses rank
first without any lights stage. Next: a morphology classifier trained on the candidate chips (positives from Abilene,
Rainier, Prometheus, Ulanqab and Horinger; negatives from the 40 national blobs and the photovoltaic and logistics
candidates), and Astra's A8/A9 to turn the found campuses into inventory entries.
