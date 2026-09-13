# Log

Dated entries by either agent: what was done, what was found, what could not be done.

## 2026-09-13 (Claude)
- Initial public release; docs/ASTRA_TODO.md written for the second agent.

## 2026-09-13 (Astra, A1 — Epoch inventory)
- Worked in a separate clone of recozers/openobservatory, branch `astra/a1-epoch-inventory`. The original workspace points to recozers/Meridian and was left untouched; no Claude research files were changed.
- Accounted for all 86 Epoch records: seven existing curated matches, 78 new sites with 264 hall polygons, and one location-only record (Stargate New Mexico, capacity unassigned/tier U because no polygon is available). There are 103 non-control public status entries.
- The brief missed the public Epoch map's explicit Building annotations and coordinates (85/86 sites). Preserved a CC BY 4.0 source snapshot and used those annotations instead of treating large nearby OSM buildings as halls. Geocoding is cached, serial and rate-limited: 23 new entries have corroborated address-quality coordinates; 56 use Epoch's published coordinates. No hall polygons overlap another inventory site's halls by more than 10% of the smaller polygon.
- Preserved 996 normalized dated capacity rows across both bases. `it_reported` is not measured HPL power; facility and IT figures are not added together. Zero, missing and future projections remain distinct. Existing validated labels are retained for the seven curated matches.
- Completed independent Sentinel-2 extraction from 2018 for all 78 new polygon sites. Accepted event dates occur at 71 sites / 217 halls; 13 halls are left-censored at the first observations; 34 are unresolved. Of those unresolved, 16 brightness candidates conflict with Epoch's reported construction timing and are retained as raw evidence but withheld from public roof dates pending imagery review. The original twelve Abilene dates do not change.
- Geometry judgement calls: 17 source line outlines were closed with endpoint gaps under 5 m; two self-intersections were repaired with Shapely make_valid. All 19 carry low confidence and explicit repair notes; source geometries remain in the snapshot. Planned annotations are not treated as existing roofs.
- Withdrew unsupported Epoch MW from the three provisional Chinese park polygons: published Huawei Horinger, Alibaba Zhangbei and VNET Bayin locations lie approximately 2.0, 1.8 and 15.4 km from those old park centroids. They are separate sourced entries; the old research polygons/adjacent-plant series remain, with capacity tier U.
- Validation: 12 unittest cases pass; all 218 generated JSON files strictly parse; all three site builds pass; deterministic import reproduces inventory/polygon files byte-for-byte. Desktop and 390 px mobile map panels were visually checked locally. The lower request-size limit and bounded retries recovered three Earth Engine concurrent-aggregation failures.
- Review `docs/epoch_inventory_audit.md`, `data/epoch/validation.json`, `data/epoch/import_audit.csv`, and `tools/ingest_epoch.py` first. These are automated brightness-based dates with stated limitations, not independent proof of IT utilisation. A3's dark-roof method remains separate research.
## 2026-09-13 (Astra, A6 — monthly refresh)
- Added service-account authentication from `EE_SERVICE_ACCOUNT_JSON` or a local key path; CI never launches interactive authentication. Existing local OAuth remains supported. Five credential tests pass.
- Added monthly/manual refresh and a PR dry-run. Local dry-run rebuilt and strictly parsed 60 JSON files without Earth Engine credentials. Live runs commit only site data and explicitly dispatch Pages (a GITHUB_TOKEN push does not trigger another push workflow).
- Recorded the five published flux profile mappings. The undocumented Colossus 2 seasonal baseline was recovered as before 2025-07-01: reproduces every existing monthly NOx value to the 0.05 kg/h CSV rounding tolerance. Other plant mappings reproduce existing series. Raw research profiles stay research inputs.
- Pinned earthengine-api 1.7.43, tabulate 0.10.0 and openpyxl 3.1.5 to the installed versions; scipy was already pinned.
- Service-account live extraction is not yet validated on GitHub: Stuart must configure the documented secrets. New daily NOx profiles are not downloaded by this workflow. The derived series are recomputed from saved profiles.
- GitHub validation: both the PR dry-run and an actual `workflow_dispatch` dry-run passed; dispatch run https://github.com/recozers/openobservatory/actions/runs/34760217886. A6 acceptance criteria met (PR #1).
### 2026-09-13 — Astra A3 dark-roof test failed validation

Extracted 2018–13 September 2026 Sentinel-2 brightness, NDVI, NDBI and BSI for Hyperion, Abilene and the three provisional Chinese parks (21 halls). Tested NDVI < 0.15 plus a sustained 0.08 index rise: all 12 Abilene dates unchanged, Hyperion north June 2026 (late) and south September 2023 (false early event), zero additional Chinese index detections. Negative result, monthly series and exact rule in docs/dark_roof_validation.md and results_s2/roof_index_validation.json. No production rule changed. A3 remains blocked on method validation.
## 2026-09-13 evening (Claude): pilot results
- Winter snow persistence (tools/snow_persistence.py, Sentinel-2 SCL/NDSI, nine sites, winters 2019-2026): NEGATIVE.
  On days when the built-up ring is >= 40 % snow-covered, operating halls hold snow like any other roof:
  Lulea halls 0.97-1.00 vs ring 0.97-1.00 (15-23 snow days per winter); NSA Utah 1.0 every winter; Rainier operating
  winters 2025-26 0.97-1.00 while the control factory roof sheds to 0.33-0.84; Chinese campuses equal to the ring.
  The only low values are construction winters (Rainier 2024: 0.00-0.32 with roofs not yet on; Prometheus LCO 2024).
  Consistent with the thermal null: hall roofs are cold roofs. Closed; results in results_snow/.
- Sentinel-1 VV structure-on dates (tools/s1_timeline.py): at Abilene all 12 halls within 0-4 months of the Sentinel-2
  roof dates (9 within 2); Hyperion farmland gives no false positive with the rule "VV >= 4 dB above the 20th
  percentile of earlier months, sustained 6 months". Chinese blocks that Sentinel-2 could only label "existing"
  (bright soil baseline) get dates: Ulanqab long_halls 2024-09 (S2 said 2025-11: grey roof missed), Horinger block_a
  2024-06, block_b 2019-06, Zhangbei west_halls 2020-01.
- VIIRS night lights (tools/ntl_timeline.py): Abilene campus-minus-annulus flat at -9 nW/cm2/sr 2019-2024, lit from
  2024-12 (six months after ground-breaking), rising to +120 by 2026 as build-out continued; Colossus 1 step 2025-01.
  Lights track construction and site expansion, not the operating date (Colossus IT load began 2024-07).
- Operator disclosures (two research agents, 13 Sep evening): Meta per-site annual electricity 2011-2024 for Prineville,
  Lulea, New Albany (data/operator_disclosures.csv, 138 rows with URLs); ORNL Frontier measured energy; Google per-site PUE
  and water only; Microsoft by metro from FY25; Amazon nothing. Chinese listed operators: company-wide MW and utilisation only
  (VNET 70-74 %, GDS 75 %, Chindata 80 % in 2023); no per-campus figures except Chindata's FY2022 20-F table (unparsed, task A10).
  Site build now: measured annual rows take precedence (band ±10 %), cloud utilisation prior 0.2-0.6, HPC 0.4-0.9.
- Radar-to-optical chain at Horinger (13 Sep, late): the 27 radar candidates >= 5 ha were run through the Sentinel-2
  brightness timeline (results_s2/horinger_candidates.csv). Only 4 of 27 get an optical roof date (cand03 2024-05, cand16
  2026-05, cand19 2022-05, cand24 2025-04); the rest stay at 0.17-0.25 brightness, i.e. grey roofs over bright soil, the
  known failure of the brightness rule (Astra task A3). In Inner Mongolia the radar date stands alone; the chip is the
  human check. tools/s2_roof_timeline.py now chunks queries by quarter/month for large polygon sets (5000-feature cap).

### 2026-09-13 — Astra A4 optical candidate discovery

Fixed-rule 2022-to-2026 Sentinel-2 change scan on five 12 km boxes, reduced to 50 m before local vectorisation. Annual comparisons match January–13 September in every year; latest year is incomplete. Area >=3 ha, rectangularity >=0.6, NDVI drop plus brightness/NDBI rise. Recall 3/3: Abilene ranks 1/2, Rainier ranks 1/2, Prometheus rank 8. Candidate counts: 6, 4, 13, Ulanqab 6, Zhangbei 1. All 30 have source metadata, geographic outlines and visually reviewed 20 m RGB chips. Eleven of the 23 US components are obvious non-hall ground/yards (48% in this sample); seven other roof/industrial components are unattributed, so no claim of automatic data-centre identity. Zhangbei full-tile timeout recovered with four resumable 6 km requests. Results and limits in docs/optical_discovery.md and results_discovery/visual_review.csv. No capacity or public campus polygon was inferred from candidate shape alone.
### 2026-09-13 — Astra A2 provincial filing audit

Searched provincial EPB/NDRC sources for three provisional campuses and seven hub centroids. Two downloaded EIAs were text-extracted and relevant pages visually checked: Huawei south-area substation (3 x 100 MVA, separate parcel) and VNET supply lines (110 kV; terminal near A1 Epoch coordinates, about 15 km from the old park). No IT-load MW can be assigned to the existing halls. Kept infrastructure units, coordinates, URLs, PDF hashes and search leads in data/china_project_documents.json; all ten inventory rows receive a dated note. No unsupported number or invented campus boundary was promoted. docs/china_project_search.md records scope and limitations; A2 satisfies the explicit negative-search alternative.
### 2026-09-13 — Astra A1 integration with current main

Integrated Claude commits through 14e24f0: retained operator annual-load priority, utilisation priors, radar dates and night-light evidence. Regenerated the Epoch inventory on the updated CSV schemas and rebuilt all public JSON. The S2 extraction conflict keeps Astra’s cached adaptive date splitting (1,000-feature target), which covers Claude’s large-polygon batching fix as well. Brightness review flags and unknown dates remain explicit.

### 2026-09-13 — Astra JSON regression found by A6

The new annual-disclosure history can put the first capacity date before the saved NO2 observations. Prometheus then has zero pre-change samples: the former mean/SE calculation emitted NaN and invalid public JSON. Empty or single-sample baselines now retain null uncertainty and yield no z-score; no baseline is invented. A1 audit now strictly parses every public JSON, so this regression is checked in CI as well as the refresh workflow. A fresh checkout also lacks results_ntl/prometheus_oh.csv although older rendered JSON contained its night-light values; reproducible rebuilds cannot retain that unsupported series. Claude should commit the source CSV if that layer is to be restored.
### 2026-09-13 — Astra refresh integration regression fixed

Current-main integration exposed an empty NO2 pre-change baseline at Prometheus after the new annual electricity rows moved its capacity start earlier. NaN mean/SE/z values made public JSON invalid. Empty or single-sample baselines now use null uncertainty and cannot produce a z-score. The saved-evidence dry run again validates all 60 JSON files. This shared build-file change is also applied in PR #2 with a strict JSON audit.
### 2026-09-13 — Astra A7 contributor guide and mobile layout

Added CONTRIBUTING.md with source/basis/geometry rules, rebuild checks and branch/PR conventions. Asked Stuart for the site name; with no answer received, applied Open Observatory as the reviewable default matching the repository. All public HTML titles/headings use it. On narrow maps the legend is available while the panel is closed and hidden while it is open; the front-page inline width no longer overrides the full-width bottom sheet. Dependency pins are in PR #1 and 12 evidence/inventory tests in PR #2.

Mobile QA: at 390 x 844 the Abilene sheet spans the viewport, all text wraps, and the map legend is hidden only while the sheet is open. Browser check of the closed map confirms the legend and tile checkbox remain available. PR #5; name choice can be revised during review.
### 2026-09-13 — Astra A5 gas calibration screen and time-window audit

Screened all 77 gas-labelled eGRID plants ≥1,000 short tons/year. 23 fail the 15 km power-emitter screen, 28 of the remainder have no CAMPD rows, and 26 return rows (many boiler/mixed facilities). Retrieved full hourly records and independent annual unit totals for Forney, Fort Myers and Midland, plus new 2023 TROPOMI flux profiles. Hourly/annual totals reconcile; no duplicate unit-hours. Physical heights and industrial-source isolation remain unverified, so no new production factor is accepted. EPA reports local standard time; the existing calibration selects hours 19/20 directly. The comparison includes converted UTC-window proxies, while actual overpass alignment remains outstanding. Changes to tools/no2_flux_quarterly.py only expose the existing references’ stack_class table; the production factor is unchanged.

| Plant | Class | Days | Legacy factor ± SE | UTC-window proxy factor ± SE |
|---|---|---:|---:|---:|
| martin_lake | coal reference | 169 | 5.12 ± 0.33 | 4.65 ± 0.30 |
| limestone | coal reference | 188 | 4.16 ± 0.36 | 3.88 ± 0.34 |
| oak_grove | coal reference | 193 | 4.33 ± 0.46 | 4.27 ± 0.45 |
| welsh | coal reference | 165 | 5.97 ± 0.92 | 6.06 ± 0.93 |
| independence_ar | coal reference | 183 | 4.68 ± 0.57 | 5.13 ± 0.63 |
| forney_gas | gas candidate; height unverified | 202 | 0.91 ± 0.08 | 0.89 ± 0.08 |
| fort_myers_gas | gas candidate; height unverified | 167 | 1.68 ± 0.23 | 1.73 ± 0.23 |
| midland_gas | gas candidate; height unverified | 122 | 4.83 ± 0.78 | 4.70 ± 0.76 |

Full source/limitations: docs/low_stack_calibration.md and results_no2/low_stack_sources.json. A5 is preserved as a draft pending qualification rather than labelling gas as low-stack by assumption.
- Lights-to-radar over the 40 brightest campus-like blobs of the national scan (results_s1/china/summary.csv): 35 of 40
  contain a new structure >= 5 ha and 27 one >= 20 ha (median largest 47 ha, max 218 ha); the chips checked are
  petrochemical, logistics and factory complexes (Ningbo, Yinchuan, east Chongqing). Data centres are a small minority of
  large new lit structures, so the chain needs a hall-morphology step before it is a data-centre detector; inside hub
  boxes the radar scan alone already ranks the campuses first (Ulanqab, Horinger). Chips for the 40 blobs are in
  results_s1/china/ for classification (Astra A8 pattern).

### 2026-09-13 — Astra combined review and handoff

Resolved the ready implementation branches as a review stack: #2 inventory, #1 refresh, #3 Chinese project notes, #5 housekeeping. No main merge or deployment performed. Combined credential-free refresh validates all 218 public JSON files. Manual GitHub run 34763113476 passed on the expanded inventory. Current main through 17d3380 includes the previously missing Prometheus night-light source, and the rebuilt branch preserves it.

Final phone-width review caught a wording ambiguity when a site has both an old roof and a dated new roof. Status now states how many were present at the first observations and how many were newly roofed, with a regression test (18 tests in the combined branch). The enlarged inventory, Epoch attribution, Open Observatory name and full-width mobile panel were inspected together. A4 is ready as PR #7; A3 and A5 remain scientific drafts #4/#6. Follow-on A8–A11, added while this run was underway, remain todo.

## 2026-09-13 late (Claude): Astra's stack merged; hall-morphology classifier
- Merged PRs #2, #1, #3, #5, #7 (stack) and the two drafts #4 and #6 after resolving docs conflicts (LOG union, brief from
  main). Tests: 18 pass on main; dry-run build validates 218 JSON files; live site serves 103 sites.
- Working copy is now the openobservatory clone; the Meridian branch is an archive.
- Classifier on radar candidates (tools/cand_features.py, tools/cand_classifier.py): leave-one-group-out AUC 0.977 with
  18 hall positives vs 1,159 industrial negatives; 0.5 keeps 14/18 halls and rejects 96 % of industry; only 4 of 249 large
  national industrial structures pass 0.5 (all 0.54-0.78, industrial in their chips); Intel Ohio's fab is the hard false
  positive (0.99). Details in docs/MVP.md, scores in results_cand/scores.csv.

## 2026-09-13 (Claude, phase 2 start)
- docs/PHASE2_TODO.md written: B1-B6 for Astra (on-site generation permits, dedicated plants via CAMPD, water-derived
  annual loads, municipal water, regional context, map evidence kinds), C1-C5 for Claude.
- C1 running: batch plume test over 71 sites with a documented or roof-derived start (tools/plume_batch.py).
- Calibration corrected to overpass hours 12-14 local standard (factor 4.41 ± 0.18, was 4.68); all NOx series regenerated.
- C2 in progress: tools/known_source_subtract.py (regress the Colossus 1 plateau on Allen and Southaven CAMPD NOx at the
  overpass hours plus a turbine-period step); CAMPD hourly for Allen 2023-2026 being fetched.
- C2 result (Colossus 1, TVA Allen and Southaven subtracted, tools/known_source_subtract.py, results_no2/colossus1_subtraction.json):
  turbine-period step Jul 2024-Jun 2025 = 62 ± 63 kg NOx/h after regressing the daily plateau on both plants' overpass-hour
  CAMPD NOx (594 days, r2 0.14); naive step 44. No month exceeds 2.5 sigma (Jan-Feb 2025 at 336 ± 140 and 391 ± 180 are the
  largest). 2-sigma upper bound ~190 kg NOx/h: consistent with SCR-fitted turbines, low output, or noise; Colossus 1's
  turbine phase cannot be shown as measured. Allen itself averaged 48 kg/h at overpass during that period vs 25 outside it.
- C3 result (night thermal revisited with ECOSTRESS frames to Sep 2026, tools/night_report.py, results_eco/): season- and
  weather-adjusted night roof steps at the documented load levels: Abilene +0.16 ± 0.23 K at 174 MW (25 frames) and
  +0.13 ± 0.47 K at 522 MW (5 frames); Rainier +0.06 ± 0.24 K at a documented 1,078 MW IT (24 frames); Fairwater +0.08 ± 0.43
  (4 frames). Colossus 1 remains the only night step (+1.24 ± 0.28 K at 125 MW, block-wide, turbine yard). Daytime steps at
  Rainier (+1.44 ± 0.60) and Fairwater (+1.35 ± 0.49) are the fit-out/roof effect seen before. The thermal null holds at the
  largest documented loads in the inventory; the refresh workflow re-runs this cheaply as 2026 frames accumulate.
- C1/C4 result: the plume test over the inventory was stopped at 33 sites once it was clear that grid-fed campuses carry no
  NO2 signature (Stuart's point, and the data agree). The 32 grid-fed sites serve as the null distribution: z mean -0.32,
  sd 1.42, 95th percentile 1.89, max 2.00, none at 2.5 sigma. So the 2.5-sigma bar has a measured false-positive rate of
  0/32 and stays. Only generator-driven sites can reach "measured": the route is Astra's B1 register plus a flux run per
  operating fleet. results_no2/plume_batch_summary.csv keeps the per-site z-scores.

## 2026-09-13 — Astra B1 permit audit started

Working in isolated astra/b1 from 6b24514. Claude C1/C2 outputs remain owned by Claude. Build change: distinguish an emission-factor ceiling from a two-sided operating range before adding Abilene monthly NOx; a permit limit must not create an invented MW interval. Research includes the named candidates and additional Ohio leads.

### Astra B1 initial results

14-record register covers named leads and additional Ohio projects, with source URLs, exact permit identifiers where verified, explicit generation scope and unknown first-fire dates. Visually checked Abilene technical review and SCR application, Fermi final permit and MZX final permit. Abilene registration: 360.5 MW, NOx ceiling 0.14 lb/MWh; no defensible lower operating emission factor, so the build preserves NOx but does not infer MW. Planned/portfolio figures are not operating campuses or a summable total. New candidate sites await attributable hall geometry.

Replayed existing no2_flux composite and monthly methods on saved daily profiles through August 2026: Abilene 880 days, 0/20 post-baseline months >=2.5 sigma (max 2.381), monthly flux below detection; Colossus 2 607 days, 7/14 months (max 4.386), existing detection retained. Colossus 1 remains Claude C2's negative result, not rerun. Unknown first fire is distinct from the chosen analysis baseline. Conditional baseline SE, source attribution, SCR fleet transition and coal calibration remain limitations. No new measured campus claimed.

Validation: 20 tests pass; dry-run rebuild strictly validates 220 JSON files; inventory audit passes. Checked the local Abilene front page and quarterly NOx strip in the browser: capacity remains explicitly assumed, new NOx values retain negative months, and no NOx-derived MW is shown. Remaining B1 work: identify permits and commissioning for unresolved leads and source hall geometry before adding new inventory sites. This is a reviewable initial implementation, not an exhaustive completed census.

Draft PR #8: https://github.com/recozers/openobservatory/pull/8 . Resume this branch for B1 follow-up; do not duplicate the register or rerun Claude C2. B2-B6 remain available when further B1 progress requires new source evidence.
- C6 result (Dublin Grange Castle, results_no2/flux_grange_castle_dublin.csv, 373 clear days 2023-2026): the calibrated
  plateau averages 964 ± 96 kg NOx/h with winter peaks near 1,900 and the EMG fit places the source 36 km downwind: this is
  Dublin's urban plume, not the campus's gas plant. The box method cannot separate a plant on a city's edge. A near-field
  sector test (1-5 km) restricted to westerly winds, with the city excluded from the upwind sector, would be needed;
  parked. Dublin and other grid-constrained cities stay on the list only if that sector variant is built.
- B3 done (Claude, via research agent, docs/water_derived_loads_notes.md, data/water_derived_loads.csv, 234 rows):
  Google publishes no WUE; an implied fleet WUE of 1.02-1.06 L/kWh comes from its own totals (about 5x Meta's 0.19, 3x
  Microsoft Americas' 0.34, so WUE never transfers across operators). Validation against Meta's metered electricity:
  water-derived / actual = 1.08 Prineville, 0.94 New Albany, 0.35 Lulea (free-air), 0.87 Altoona, 1.25 Los Lunas, 1.59
  Fort Worth, about 3 at Clonee/Odense; Microsoft metros 0.4-3.5. So the method is good to about a factor of two; 12
  Google campuses now carry a "derived" annual IT load with a 0.5x-2x band (tools/ingest_water_loads.py), drawn in
  light orange; reported electricity always beats a water derivation. Air-cooled campuses (Mesa, Storey County) excluded.
- Meta per-site electricity extended to all 18 disclosed campuses (docs/meta_disclosures_notes.md); ten campuses added
  to the inventory with OSM footprint coordinates. Map evidence kinds: measured 19, derived 12, detected 4, presumed 52,
  construction 26 (113 public sites).


## 2026-09-13 — Astra B2 CAMPD integration

Working in isolated astra/b2; incorporated Claude's committed B3/B6 work through e91e31b before editing shared builders. Add monthly CAMPD evidence and a separate A1 load_basis, preserving documented capacity and existing NOx estimates. Physical allocation must be sourced and >=80% for a complete quarter; otherwise evidence only. Southaven is ORIS 55269 (6641 is Independence AR). Hyperion's original three plants remain pending IDs, reporting units and physical allocation.

B2 validation: 42 complete Southaven plant-months (2023-01 to 2026-06), 14 complete quarters, latest 625 MW gross plant average; no physical campus allocation and no campus-load substitution. Independent EPA 2023 annual/monthly API fixtures reconcile gross MWh and operating unit-hours exactly and NOx within aggregate rounding. Hyperion remains header-only/pending, not zero output. 31 tests pass, including a full synthetic qualifying builder path with separate A1 load basis, zero-output status and the real non-dedicated control. Dry refresh validates 240 public JSON files; browser inspection confirms separate grey CAMPD strip and explicit evidence-only wording. No real qualifying dedicated-supply record exists yet; that conditional acceptance remains pending.

PR #9 CI exposed an existing integration gap after B3: validate_epoch rejected all non-Epoch annual disclosure bases. Updated the audit to admit the three known annual bases only with URL/source, A1/A2 tier, finite nonnegative MW and matching calendar-year dates. Two regression tests retain unknown/unsourced/invalid-row rejection. Full suite now 33 tests; Epoch audit has zero failures.
