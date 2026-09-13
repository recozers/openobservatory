# Overnight report, 13 September 2026: the night-time test

Everything below is from `data/observations_eco.csv` (ECOSTRESS L2T LSTE v002, 70 m, 16,780 polygon rows, 21 sites, 2018/2022 to Aug 2026, ERA5-Land weather attached), `data/observations_gee.csv` (Landsat 8/9 Collection 2 surface temperature, 30 m, daytime), and the scripts `tools/night_report.py` and `tools/ring_analysis.py`. Full machine output: `results_eco/night_report.md`, `results_eco/summary.json`.

Night = solar elevation below −6°. Day = above 20°. ΔT = polygon mean minus matched background ring (500–2000 m), same land-cover rule as before. "Step" effects are season- and weather-adjusted OLS period effects.

## Bottom line

1. **Roof thermal does not see IT load, day or night.** At night, operating data-centre halls sit within ±1 K of their surroundings, and documented load steps of 170 MW to 1 GW nameplate produced +0.06 to +0.16 K (all consistent with zero). The one apparent daytime success, Colossus, was a mislabelled load period plus a 2025 daytime rise with no load counterpart.
2. **Thermal cannot identify a data centre.** Nine ordinary warehouses and factories span a wider range of night anomaly (−1.5 to +2.0 K) than twelve data centres (−0.75 to +1.2 K). Frame-level AUC for operating halls versus controls is 0.49. Daytime anomaly and diurnal amplitude rank controls *above* data centres (AUC 0.36–0.37) because they are roof-colour signals.
3. **The constraint is physical, not statistical.** Per-frame night noise is 0.65–1.0 K at the best sites; a year of passes resolves ~0.5 K; the coupling between load and roof temperature is below 0.0005 K per nameplate MW. A better model cannot recover a signal that is not on the surface. Only a different sensor (sub-10 m night thermal) or a different observable (optical, night lights, power infrastructure) changes the picture.

## The four questions

### Pursuable angles, ranked

1. **Write the negative result properly.** Twelve sites, nine controls, ~2,700 night frames, two sensors, measured labels for six supercomputing/agency sites, and quantified upper limits. This is a well-powered null that the community keeps re-proposing; it is publishable and all the data are in hand. Include the two traps we hit: daytime within-site "steps" are construction/surface artefacts (Hyperion, an unpowered construction site, is the hottest object in the study by day at +7.6 K), and Landsat's cloud mask deletes cold white roofs preferentially.
2. **If the goal is monitoring data centres from space, change the observable.** Optical (Sentinel-2, 10 m) resolves construction phase, roof completion, cooling-unit counts and substation build-out, which is where the information is. VIIRS night-time lights and Sentinel-1 SAR give activity proxies. Thermal earns a place only as a construction-phase indicator.
3. **The one thermal experiment left: a tasked night acquisition at 3–4 m** (commercial mid-wave/long-wave thermal) over Colossus or Abilene, to see whether individual dry coolers and cooling towers are resolvable when the 70 m pixel is removed. This is cost-limited, not data-limited, and the physics (latent and advected heat) says expect small numbers even then.
4. **A small open science question:** the entire Colossus block, roof, ring and yard alike, warmed by ~1.2 K at night after conversion and stayed flat when the GPU count doubled. Roughly 150 MW released over ~30 ha is ~500 W/m², enough to warm the near-surface air locally. That would be block-scale anthropogenic heating, not roof conduction. It is not a monitoring tool, and none of the greenfield campuses shows it yet.

### Can we train a model to identify new data centres on thermal signal?

No. Night anomaly of operating halls versus controls:

| operating data-centre halls (night ΔT, K) | | ordinary large roofs (night ΔT, K) | |
|---|---|---|---|
| Colossus, operating period | +0.03 | Memphis industrial roof, 1.3 km from Colossus | **+2.04** |
| Fairwater | +0.44 | Amazon MKE1 fulfilment centre | +0.64 |
| Utah (NSA) | +0.19 | Abilene warehouse | +0.09 |
| Prometheus / New Albany | +0.45 | DSV warehouse, New Albany | +0.04 |
| Rainier | +0.32 | Racine industrial roof | −0.07 |
| Abilene | −0.09 | Memphis Navy test facility | −0.06 |
| ORNL | −0.21 | Abercrombie distribution centre | −0.14 |
| Kobe | −0.53 | New Carlisle factory | −0.27 |
| Wuxi / Guangzhou | +0.50 / +0.53 | Les Schwab warehouse, Prineville | −1.48 |

Site-level AUC on night ΔT 0.60 (12 vs 9 sites, indistinguishable from chance at this n); frame-level 0.54; operating frames only 0.49. Daytime ΔT AUC 0.36, diurnal amplitude 0.37, Landsat daytime 0.37: dark-roofed controls (Abercrombie +7.9 K by day, Racine B +5.9 K) out-heat every data centre. There is no thermal feature to learn. What identifies a data centre is structural and optical: cooling yards, generator rows, substations, security perimeter.

### Can we estimate utilisation within sites?

No, not from roofs at 70 m, and not from the immediate surroundings either.

Within-site night steps, season and weather adjusted:

| site | documented change | night step (roof) | night step (35–150 m ring) | day step (roof) |
|---|---|---|---|---|
| Colossus | 0 → ~125 IT-MW (Jul 2024) | **+1.21 ± 0.29 K** | +1.20 ± 0.25 K | +2.0 ± 0.4 K |
| Abilene | 0 → 174 → 522 IT-MW | +0.16 ± 0.22, +0.13 ± 0.45 | +0.40 ± 0.17, +0.21 ± 0.35 | ~0 |
| Rainier | 0 → 1,078 IT-MW nameplate | +0.06 ± 0.24 | +0.02 ± 0.17 | +1.44 ± 0.60 |
| Fairwater | 0 → 348 IT-MW (4 night frames since) | +0.08 ± 0.43 | +0.63 ± 0.54 | +1.35 ± 0.49 |
| ORNL | Summit 10.1 → Frontier+Summit 31–33 → Frontier 24.6 MW | +0.2 to +0.4, slope +0.006 ± 0.008 K/MW | | ~0 |
| Kobe | K 12.7 → Fugaku 29.9 MW (6 pre frames) | −0.14 ± 0.82 | | +0.65 ± 0.61 |

Colossus is the only site with a night step, and it is the same magnitude on the roof, the ring and the turbine yard, and it did not grow when the load reportedly doubled during 2025 (trend −0.5 ± 0.7 K/yr). Same-acquisition ring-minus-roof differences in the operating periods are all within ±0.25 K, so heat-rejection equipment is not visible next to the halls at night either.

Detectability, taking the residual night noise per site and one year of passes on each side of a step (80% power): the best sites (Fairwater, Rainier, Prometheus, Utah, Abilene) resolve 0.5–0.7 K; Colossus 1.3 K; the small Asian halls 1.4–3 K. At Colossus's own 0.01 K per MW that is 60–100 MW. But the greenfield sites put the coupling below 0.0005 K per nameplate MW (Rainier: +0.06 ± 0.24 K for 1,078 MW), which makes the detectable step larger than a gigawatt. Utilisation is out of reach by orders of magnitude.

### Data-constrained or model-constrained?

Signal-constrained first, label-constrained second, not model-constrained.

- **Signal.** Per-frame night noise 0.65–1.0 K (best sites), 1.3–2.4 K (Colossus, Prineville, Kobe). Annual means are good to ~0.2 K. Against that, labelled steps of hundreds of MW give ≤0.16 K. The physics: heat leaves as latent heat from towers and as warm air from dry coolers and exhausts, roofs are insulated and white, and a 70 m pixel dilutes a chiller row. More frames tighten the bounds; they do not create a signal.
- **Labels.** Greenfield labels are nameplate or prorated design figures, not metered load, and energisation coincides with finishing works. Better labels would sharpen the denominator, not the numerator.
- **Model.** The cross-site night fit removes the albedo term exactly as hoped (between-site variance share 0.09 at night vs 0.34 by day; site random-effect SD 0.56 K vs 1.51 K) and capacity still explains 0.5% of variance. There is nothing left for a more flexible model to find.
- **Sensor.** The one lever that is genuinely "data" is spatial resolution at night. That is a different instrument, not more of this one.

## What changed overnight

- ECOSTRESS backend written and run: catalogue search, signed-URL range reads, 70 m-scaled thresholds, per-granule cache, relaxed roof mask option, solar geometry; weather via Earth Engine ERA5-Land (`tools/fill_weather_gee.py`).
- Six measured-label sites extended back to July 2018 (Kobe and ORNL swaps now inside the window); nine control roofs added on both sensors; hall-surround rings added at six sites.
- Bugs fixed: a zero-row site overwrote the whole observations file in append mode (now impossible); stale per-site observation windows; mixed timestamp formats; Landsat-era pixel thresholds applied to 70 m pixels; built-up background override ignored by the Landsat-C1/ECOSTRESS path.
- Colossus's July 2024–Jan 2025 label corrected from 8 MW (grid share) to ~150 MW facility (turbine-fed), which removes the daytime "0.02 K/MW step" claim; ORNL corrected for Frontier.
- ECOSTRESS's own cloud mask also deletes some bright roofs by day (Prineville control 61% roof-only rejections by day, 29% at night); night rates at data-centre sites are 3–17%, and any bias shrinks steps rather than inflating them.

## Caveats

- Fairwater has only 4 night frames since energisation; Kobe only 6 before Fugaku. Both nulls are weak individually; the pattern across sites is not.
- Ring polygons are crude (paving and laydown included). The Abilene ring's +0.40 ± 0.17 K at 174 MW is the only hint of near-hall heat and did not grow at 522 MW.
- Luleå has no ECOSTRESS coverage (ISS orbit). Wuxi and Guangzhou yield few frames (small halls, cloud).
- Nothing is committed to git yet.

## Files

`data/observations_eco.csv`, `data/rejections_eco.csv`, `results_eco/`, `results_gee/`, `dcheat/ecostress.py`, `tools/fill_weather_gee.py`, `tools/night_report.py`, `tools/ring_analysis.py`, `data/polygons/ctrl_*.geojson`, phase scripts in `data/cache/run_*.sh`.
