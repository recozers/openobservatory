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

## 2026-09-14 (Claude): China coverage from radar (C7)
- Every hall-like radar candidate (area >= 5 ha, classifier score >= 0.5, not overlapping a known site) in the hub boxes becomes
  an inventory entry `cn_<hub>_r<rank>` with its 20 m radar outline as a low-confidence polygon, coords_quality
  radar_candidate, tier U, and a note carrying score, area and VV rise (tools/ingest_radar_candidates.py). One radar
  timeline per hub (results_s1/<hub>_newsites.csv, split per site by tools/split_s1_hub.py) gives each a structure-on month.
  The site says "radar-detected new structure, N ha, structure on <month> (radar); hall-like score S; unconfirmed, operator
  unknown", running "unknown: new structure found by radar, not confirmed as a data centre", load "not estimated".
- First six hubs: 39 entries (Horinger 23, Zhangbei 6, Ulanqab 5, Qingyang 4, Gui'an 1, Chongqing 0), all dated; structure-on
  months cluster in 2023-2025 (Jul 2024 x5, Aug 2025 x4, Jun 2023/2024 x3 each). Six more hub boxes scanned (Zhongwei 60
  candidates, Zhangjiakou/Huailai 25, Wuhu 63, Shaoguan 24, Chengdu Tianfu 109, Tianjin Wuqing 78) and being scored.
- What this is and is not: automatic, dated detection of new large hall-like structures in the hubs, with provenance;
  not confirmation of a data centre, not an operator, not a load. Confirmation is human (chips in results_s1/) or
  documents (Astra A8/A2/B8).
- Six more hub boxes (Zhongwei, Zhangjiakou/Huailai, Wuhu, Shaoguan, Chengdu Tianfu, Tianjin Wuqing): 359 candidates,
  76 of them >= 5 ha, none scoring >= 0.5. Chips checked: Zhongwei's largest is a power plant (cooling towers), Tianfu's
  is apartment blocks, so the rejections are right. Two open questions: the box centres for the eastern hubs are approximate
  and may miss the parks, and eastern Chinese data centres are often multi-storey buildings that the classifier, trained on
  single-storey hyperscale halls, has never seen. Needs: verified park coordinates (Astra A2/B8) and eastern positives
  before the classifier is trusted there. No entries added from these boxes.

## 2026-09-14 (Claude): all three pages show the new evidence
- The quarterly detail page (map.html) still used the old three-colour scheme, so Meta's measured campuses appeared as
  "documented capacity in force". It now reads evidence_kind from status.json: same five colours, legend and kind badge as
  the landing map, plus the built/running/load lines; the chart's dashed line is labelled by basis; methods text updated.
- The list page gained a kind badge per card, an evidence filter with counts, and a strongest-evidence-first sort; the
  intro says where load figures come from (operator electricity, water-derived, presumed).
- Bug fixed: a water-derived figure carried into later quarters was renamed carried_it_measured_annual and got the 0.7-1.3
  band for reported electricity. It keeps its own basis now (carried_water_derived_it_annual, band 0.4-2.5). Basis text
  says "operator-reported annual electricity" or "water-derived annual IT load" instead of "documented capacity in force".
  Tests for both added (22 pass).
- Unconfirmed radar structures no longer carry a roofed-area potential band (it showed 0-393 MW for a structure not known
  to be a data centre); their load reads "not estimated".
- Local serving: tools/serve_site.py serves site/ with Cache-Control no-store, so a rebuild shows on reload; README and
  CONTRIBUTING point to it.

## 2026-09-13 — Astra B2 CAMPD integration

Working in isolated astra/b2; incorporated Claude's committed B3/B6 work through e91e31b before editing shared builders. Add monthly CAMPD evidence and a separate A1 load_basis, preserving documented capacity and existing NOx estimates. Physical allocation must be sourced and >=80% for a complete quarter; otherwise evidence only. Southaven is ORIS 55269 (6641 is Independence AR). Hyperion's original three plants remain pending IDs, reporting units and physical allocation.

B2 validation: 42 complete Southaven plant-months (2023-01 to 2026-06), 14 complete quarters, latest 625 MW gross plant average; no physical campus allocation and no campus-load substitution. Independent EPA 2023 annual/monthly API fixtures reconcile gross MWh and operating unit-hours exactly and NOx within aggregate rounding. Hyperion remains header-only/pending, not zero output. 31 tests pass, including a full synthetic qualifying builder path with separate A1 load basis, zero-output status and the real non-dedicated control. Dry refresh validates 240 public JSON files; browser inspection confirms separate grey CAMPD strip and explicit evidence-only wording. No real qualifying dedicated-supply record exists yet; that conditional acceptance remains pending.

PR #9 CI exposed an existing integration gap after B3: validate_epoch rejected all non-Epoch annual disclosure bases. Updated the audit to admit the three known annual bases only with URL/source, A1/A2 tier, finite nonnegative MW and matching calendar-year dates. Two regression tests retain unknown/unsourced/invalid-row rejection. Full suite now 33 tests; Epoch audit has zero failures.


## 2026-09-13 — Astra B4 municipal monthly water

Working in isolated astra/b4, stacked on PR #9 (astra/b2) to share its builder integration and annual-disclosure audit fix. B2 remains awaiting review; no merge to main. Found monthly municipal deliveries to Utah Data Center plus independently reported customer purchases and return flows in Utah DWR. Preserve four distinct series; city and customer amounts differ. Add a separate monthly water strip without changing load estimates or evidence classification. Other seven cities get a dated public-source search audit, with system-wide or annual data excluded from campus monthly records.

B4 result: 312 monthly observations in four separate series for one campus; the main municipal strip covers 120 months, 2016–2025. Municipal and customer annual/monthly mismatches are retained (including October 2023 and the flagged 2020 meter/cleaning year). No annual/system-wide data were allocated into campus months. All eight city searches have URLs and explicit outcomes; Prineville/Clarksville access limits documented. 38 tests pass, dry refresh validates 240 public JSON files, Epoch audit has zero failures. Browser check verifies 120-month water strip, separate intake/return table, source links and reporting cutoff. All existing load, running, confidence and evidence-kind values unchanged; NSA quarterly estimates are byte-for-value identical.

## 2026-09-13 — Astra B5 regional context

Added 38 dated regional records for Dominion, AEP Ohio, ERCOT LFLs, PJM, EirGrid/Ireland CSO and Singapore EMA/IMDA, with source URLs, units, inequalities, scopes and source locators. Contracts, future increments, apparent MVA demand, capacity targets and annual metered energy remain distinct. Historical snapshots are not advertised as latest figures. Singapore EMA's inspected chapter does not provide DC-only annual electricity; all-sector energy is explicit context, supplemented by IMDA capacity. Dominion/EirGrid tables visually checked; direct source hashes retained where available, retrieval blocks disclosed.

Independent `tools/regional_load.py` audit reads raw annual electricity, not quarterly IT priors. Current Irish subset is Clonee only: 1,076,961 MWh disclosed facility electricity in 2024 against CSO 6,973,000 MWh national DC grid energy. Partial-roster and accounting-boundary caveats prevent interpreting this as coverage/accuracy. Missing years are null, utility-region membership is not guessed, MVA and contract/forecast rows are not compared as energy, and no site builder consumes these data. Six tests cover source reconciliation, incompatible metrics, leap-year averaging, missing/zero, duplicates, and an outlier review flag without rescaling. Branch astra/b5 is based on astra/b2 / PR #9 to retain its existing annual-disclosure audit fix. No main merge or deployment.

B5 validation: 39 tests pass; dry refresh validates 240 public JSON files; Epoch audit has zero failures. Public site data are unchanged apart from discarded generated timestamps. Regional audit is reproducible offline. All six regional areas have context; only the Irish annual series supports even a partial inventory comparison at present.


## 2026-09-14 — Astra B6 evidence filter and default map fit

Built on current main 003aabf, retaining Claude's 39 Chinese radar candidates and B8/B9 brief additions. List now filters all five evidence kinds, composes with the hub toggle and sort, shows text plus matching colour swatches, announces result counts, and has an empty state. Default ordering actually groups measured first, then derived/detected/presumed/construction and load. The map fits all displayed valid coordinates once on initial load; a valid site hash keeps its selected-site view. Phone layouts put the legend below a bounded-height map because MapLibre's Mercator height constraint otherwise prevents fitting the full longitude span. No private transform overrides. Desktop and 390px mobile visuals checked; detected filter includes Abilene and its unchanged measurement caveats.

Six synthetic status tests cover all five categories, annual zero, calibrated generation, night lights, missing timeline and unconfirmed radar. They exposed and fixed the uncarried water-derived annual basis being missed, annual zero falling through to unknown, and a missing-timeline null dereference. Current published inventory values remain unchanged; only regenerated timestamps were discarded. Four Node tests exercise list filtering/sorting/hub composition/escaping, map coordinate inclusion, legend padding, five marker colours, one-time fit and deep links. Node tests run in validation CI.

28 Python tests and 4 Node tests pass; dry refresh validates 318 JSON files; Epoch audit has zero failures. The existing annual-disclosure audit fix from PR #9 was cherry-picked independently (bf92f0d) so this branch targets main and preserves the newer China work; it does not depend on the B2/B4/B5 stack. No main merge or deployment. B7–B9 remain unfinished; conditional B1/B2/B3 source-attribution limits still apply.


### 14 September 2026 — Astra B7 generator watch first pass (astra/b7; incomplete)

Added two filing-located generator watch points and a nine-row register spanning the seven requested projects (Hyperion supply split into three plants). Fermi permit p13 gives 35.2843/-101.5776 and developer targets 2026 first power. Cheyenne county packet p45 gives power-site centre 41.022293/-104.819811; traffic study p330 expects power operation by 2030, separately from the data centre's 2027 target. Seven plant records still need locational/permit evidence. Apollo final permit obtained from EIP mirror is effective June 2 2026, despite June 15 filename; numeric coordinate not verified. See docs/generator_watchlist.md, data/generator_watchlist.csv and hashed source manifest.

Initial live OAuth extraction: Fermi 632 usable days, Cheyenne 401, January 2024–August 2026. With frozen 2024–2025 seasonal baselines, each has eight complete 2026 monthly changes; neither exceeds both 2σ and 100 kg/h. No first detection or actual first-fire date is claimed. Baseline uncertainty included; signed negatives retained. Tall-coal calibration transfer, source isolation, daily independence and multiple testing remain scientific limits. Both public statuses are watching, load unknown. No emission-factor prior or campus MW is inferred from a permit ceiling or missing EF. Cheyenne fuel-cell output is outside NOx observability.

Monthly refresh now fetches a three-month complete-calendar overlap for registered watches, keeps baseline profiles, replays dry runs, retains raw/monthly evidence, and idempotently logs the first future crossing. Orange means measured regional NOx change requiring source follow-up, not verified fleet commissioning. Existing non-watch load/status records are unchanged. Signed chart/error bars and direct source links checked in the browser. Local validation: 35 Python tests, 5 Node frontend tests, dry refresh strictly parses 322 JSON files, Epoch audit has zero failures.

B7 remains in progress: seven pending plant records and Cheyenne air limit need source evidence. No real first-threshold event yet; the automatic log/colour path is covered synthetically. Draft PR targets astra/b6 / PR #12 to preserve its evidence filter and map work. Stuart handles merges; no deployment or main merge performed.

## 2026-09-14 (Claude): Codex's phase-2 branches integrated
- Merged astra/b2 (via b4), b4, b5, b6 (via b7) and b7 into main: EPA CAMPD plant evidence with a verified-allocation
  guard (Southaven CC at Colossus 2 stays evidence only), municipal monthly water (NSA Utah, 312 records, eight-city
  audit), regional data-centre load context with an inventory energy audit, the tested list filter and default map fit,
  and the generator watch list (Fermi Matador and Cheyenne Jade, both below threshold).
- Conflicts resolved: where B6 and Claude's same-day evidence-kind UI overlapped, Codex's tested list script and toolbar
  and its map framing were kept; Claude's quarterly-detail page, intro banner, carried water-derived band and "not
  estimated" wording for unconfirmed radar structures were kept; the refresh runs CAMPD, water and watch-list steps.
- Checks: 59 Python and 5 Node tests pass; dry refresh validates 322 JSON files; landing map, list and detail pages
  load without errors and show both sets of changes. Generator watches read "not estimated" rather than "0 MW".

## 2026-09-14 (Claude): Requests for work
- `REQUESTS_FOR_WORK.md` at the repository root lists work for people who donate a coding agent's session: how to claim
  (fork, `rfw/NN-name` branch, draft pull request titled `[RFW-NN]`, 72-hour lapse) and hand off, what already works, the
  methods already tried and failed, 23 requests with size, credentials and an acceptance line, and 9 theories with a first
  test and a stopping rule. RFW-09, 16 and 17 are Astra's B7, B8 and B9, marked reserved.
- `tools/build_requests_page.py` renders it to `site/requests.html` (anchors match GitHub's), `tools/refresh.py` rebuilds
  it, and `tests/test_requests_page.py` fails if the page is stale or a link is broken. The page is linked from the map, list
  and detail pages; README and CONTRIBUTING describe how to donate a session.

## 2026-09-14 (Claude): corrections from an audit of the requests page
- The plume batch's z-scores (13 Sep, C1/C4) mixed each site's series with its two control points. Recomputed per series:
  none of 31 campuses without known on-site generation reached 2.5σ (highest 2.09); Abilene 2.80σ; Colossus 2 9.84σ; 62
  control points mean −0.29, sd 1.38, highest 2.06, none at 2.5σ. The entry above quoting "0/32, sd 1.42, max 2.00" is
  superseded. tools/plume_batch.py now filters to one series; results_no2/plume_batch_summary.csv is recomputed and
  results_no2/plume_batch_zscores_by_series.csv holds every series.
- Also corrected (details in docs/MVP.md, "Corrections, 14 Sep 2026"): NOx monthly precision (quarters ±20 %, months
  ±20–50 %), night-light recall (four of seven within 0.4 km, not six), the unsupported "two to six months after
  ground-breaking" timing, roof dating "±1 month" (only checked against radar), and the Horinger candidates' wording.
- Requests page rewritten for precision and China priority (Stuart, 14 Sep: "focus a little more on China, US observability
  is much better"): each working method now states its test scale, truth and uncertainty and whether it carries to China; a
  new Inconclusive section; the failed list uses corrected numbers; China requests come first, with five new ones (RFW-24
  construction index, RFW-25 land transfers, RFW-26 grid projects, RFW-27 water permits, RFW-28 building-scale lights) and
  RFW-29 plume-test robustness; China theories T-10 (temporary site housing) and T-11 (post-structure radar); and a separate
  "Requests that cost money" section (PAID-01 to PAID-09) with licence conditions and pilots, no prices.

## 14 September 2026 — Astra B8: eleven-hub plant/monitor audit; hourly access unresolved

Branch `astra/b8` from integrated main `5000633`. Reconciled Claude's integration of B2/B4/B5/B6 and the two initial B7
watches before starting; no duplicate implementation. First-pass B8 register has fourteen plant/supply records across all
eleven requested Chinese hubs, nine regional access outcomes, and explicit source URLs/locators/access states. Shengle
is a cloud-park CHP support plant, with documented heat sales and planned grid electricity sales; Liangjiang has an
operator-described waste-heat cooling connection to China Telecom. Neither establishes a dedicated electrical share.
Four source-grid-load-storage leads are renewable projects; Jingning, Huaning and Zhongwei nearby thermal plants remain
unattributed. No campus generation, capacity, load or evidence-kind promotion.

Inner Mongolia's public enterprise/document endpoints work. Shengle enterprise ID is B91752F8E785428E8900B78EA180D9AC;
2025 report describes hourly SO2/NOx/PM at #1/#2 desulfurisation outlets. Database outlet IDs and flow remain unknown.
An August 2026 automatic reading query returned a CAPTCHA requirement; no bypass attempted. Other provincial endpoints
returned connection timeouts, 404 or 412; national public app is distinct from the login route. Dated third-party platform
closure claims are discovery context, not current proof. Hourly/daily acceptance remains unmet; B8 stays in progress.

Downloaded seven annual Shengle reports (2019-2025) and the latest listed stamped 2026 monitoring plan, retaining eight
PDFs (~6.3MB) and hashes. The listed 2018 report returned an unsynchronised/missing-file HTML message. Saved 63 **annual**
SO2/NOx/PM emission-mass records: unit 1/unit 2/whole-plant for seven years, metric tonnes, overlapping scopes explicitly
labelled. 2023 is scanned, visually read at physical p15. The 2024 NOx source total is 606.6 t but units 282.47 + 319.13 = 601.60 t;
all originals preserved and discrepancy flagged, visually confirmed on p19. Twenty of 21 pollutant-year totals reconcile.
2019 listing contains 测试; retained as a source metadata caveat. No missing readings replaced by zeros.

`tools/cn_stack_monitors.py` verifies PDF hashes, annual periods/units, record uniqueness, report-year identity and source
arithmetic flags; added to validation CI. Local checks: audit 63 records/8 PDFs/11 hubs, 59 Python tests, 5 Node tests, dry refresh 322
strict JSON files, Epoch audit zero failures. Rebuilt page visually checked at localhost:8011. Public outputs differ only
in two generated timestamps, discarded after inspecting the diff. No main merge or deployment. Start review with
`docs/cn_stack_monitors.md`, `data/cn_plant_links.csv`, and `data/cn_stack_monitors/README.md`. Monitor remains active;
B9 is the next independent task, while B8 needs normal public reading access and further physical-allocation filings.

## 2026-09-14 (Claude): B8 merged; subtitle
- Merged astra/b8 (PR #14, draft first pass): 14 Chinese plant or supply leads across 11 hubs, Shengle's annual emission
  reports 2019-2025 (63 records, 8 PDFs with hashes) and `tools/cn_stack_monitors.py` in CI. No hourly or daily readings
  (CAPTCHA at Shengle; other services timed out); no campus allocation; no site figures change. REQUESTS_FOR_WORK.md now
  lists it under Inconclusive and adds a ground rule against bypassing CAPTCHAs or access controls.
- Site and README subtitle set to "Open source project to monitor the build out and utilisation of compute across the world."
- Requests page reorganised (Stuart: "organise the rfw cleaner"; goal is full monitoring of data-centre activity at the
  highest possible time resolution; China the priority because its public data is notoriously unreliable). New order: the
  goal, a "How close we are" table by question and time resolution for the US and China, the biggest gaps, how to donate,
  ground rules, requests in three priority tiers (1 China, 2 power at higher time resolution, 3 coverage and tools), theories,
  paid requests, and the detailed results at the end. Requests renumbered RFW-01 to RFW-29 in priority order (no claims
  existed); theories T-01 to T-11 with China first; Astra's B7, B8 and B9 are now RFW-20, RFW-11 and RFW-12. Earlier log
  entries use the old numbers.
- Goal reframed (Stuart, 14 Sep: "it's not about power draw it's about utilisation; ideally distinguish training and
  inference"). REQUESTS_FOR_WORK.md now defines utilisation (commercial, electrical, activity signals), adds capacity,
  utilisation and training-or-inference rows to "How close we are", and adds RFW-06 and RFW-22 (sourced workload roles, cloud
  regions), widens RFW-05 (training and inference server tenders) and RFW-18 (capacity and commercial utilisation), and adds
  theories T-02 (hourly GEMS NO2 over plants supplying Chinese parks), T-05 (hourly TEMPO NO2 at turbine-fed campuses) and
  T-06 (network presence as a sign of inference). Requests now RFW-01 to RFW-31, theories T-01 to T-14; Astra's B7, B8, B9
  are RFW-21, RFW-12, RFW-13.
- Correction: New Albany's 250 MW connection applies only from 2026, so its 2023-24 loads cannot give a utilisation ratio.
  The cloud prior (0.2-0.6) now cites its one same-period calibration point, Luleå at 0.25-0.45 of 120 MW in 2022-24; fixed
  in the builder's basis text, the site's methods text, docs/utilisation_model.md and docs/MVP.md.
- Training-or-inference method set (Stuart, 14 Sep): a deep-learning model on detailed thermal imagery of campus substations
  and transformers, labelled with metered load and workload records from US national laboratories. Added as theory T-05 (free
  first test: IEEE C57.91 / IEC 60076-7 transformer thermal models with training and inference load profiles, sampled and
  noised as a satellite would), request RFW-23 (laboratory partners and a draft data-sharing request), and PAID-03 refocused
  on substation thermal imagery. Evidence so far, computed from data/observations_eco.csv: at 70 m the NSA site's tentatively
  identified switchyard (about 3 pixels) read +0.25 ± 0.07 K at night over 299 frames, no different from its halls
  (+0.19 ± 0.05 K), with no load change to test against, so transformer-scale heat is untested rather than failed.
  Requests are now RFW-01 to RFW-32 and theories T-01 to T-15.
- Correction to the workload method (Stuart, 14 Sep): the labels come from AI labs such as OpenAI, which know when and where
  their training runs happened, not from US national laboratories. RFW-23 is now "AI lab partners with training-run records"
  (map labs to campuses, collect publicly announced training runs as coarse labels, draft a data-sharing request for
  Stuart); T-05 and PAID-03 now pilot on a US campus with training-run records. Flagged: labels given in confidence would
  conflict with the free-public-data provenance rule; publishing or agreeing to publish them avoids that, otherwise it is
  Stuart's decision.
- Provenance rule amended (Stuart, 14 Sep: "i'll allow that", in reply to whether labels given in confidence may train the
  workload model). Training-run records that AI labs supply in confidence may now train and validate the training-or-inference
  model. Conditions written into README's provenance rule, docs/MVP.md, CONTRIBUTING.md, docs/ASTRA_TODO.md,
  docs/PHASE2_TODO.md, docs/utilisation_model.md and RFW-23: records stay in `data/private/` (now git-ignored) and out of
  commits, pull requests, issues and site data; only Stuart and sessions Stuart runs handle them, never donated sessions; code,
  aggregate validation scores and outputs for campuses the records do not cover are published, marked as from a model trained
  partly on confidential labels; nothing is published for the campuses and periods the records cover (T-05's second test and
  PAID-03's pilot publish only aggregate results); the trained model is not released without the lab's agreement. The last
  three safeguards are Claude's reading of the decision and Stuart can change them. Every other public number still traces to
  free public data.
- Added RFW-33, "Crawl public records and satellite data for data centres in the rest of the world" (Stuart, 14 Sep), as the
  last Priority 3 item, so no request was renumbered. Its figures come from data/sites.csv and site/data/status.json: 12
  sites in 11 countries outside the US and China, eight of them Epoch AI campuses, dated buildings at 6, and five campuses
  with halls Sentinel-2 dates to 2022 or later (DayOne Nusajaya, Google Waltham Cross, Oracle Batam, Southgate Melbourne,
  Start Campus Sines), which serve as its recall check. No radar, optical or night-light discovery scan has run outside the
  US and China (results_s1, results_discovery, results_ntl). The record sources it names are candidates to check, not yet
  verified. PAID-08 now also answers RFW-33. Requests are now RFW-01 to RFW-33.
- Custom domain (Stuart, 14 Sep): the site now serves at https://openobservatory.info/. Stuart registered the domain at
  GoDaddy and set its DNS: four A records for the apex to GitHub Pages (185.199.108.153 to 185.199.111.153) and www as a
  CNAME to recozers.github.io. The domain was then set in the repository's Pages settings through the API, because the
  Actions deploy ignores CNAME files. Each Pages setting change needed a workflow re-run before it took effect: after the
  domain was added the old address redirected to a "Site not found" page for about 90 seconds until the redeploy, and forced
  HTTPS only redirected after a second redeploy. GitHub's Let's Encrypt certificate covers the apex and www. http, www and
  the old recozers.github.io address all redirect to the HTTPS apex. README links updated.

## 2026-09-14 (Claude): contributor workflow for donated sessions

Stuart asked for the repository to be ready for outside contributors and for a practice claim. Added:

- `.github/workflows/claims.yml` and `.github/scripts/claims.cjs`: a claim bot on `pull_request_target` and a daily
  schedule. The earliest open pull request for an item gets `claim`; later ones get `duplicate claim` and take over when
  the holder closes or lapses; a draft with no commit for 72 hours gets `lapsed claim`; `reserved: <agent>` items are only
  claimable from that agent's branches. One comment per pull request, updated in place. It checks out main, reads titles,
  labels and commit dates through the API, and never runs pull request code. Commit dates are set by the committer, so the
  lapse rule can be gamed by a dishonest contributor; it is a courtesy mechanism, not enforcement.
- `site/claims.js`: shared by the bot and the requests page, which now marks claimed items live from the GitHub API (one
  unauthenticated request per page load, 60 an hour per visitor) and says so when GitHub cannot be reached.
- `.github/pull_request_template.md` (Claim, Plan, Handoff, checklist), issue forms for proposals and data corrections,
  `.github/CODEOWNERS` requesting Stuart's review, and labels.
- `tests/claims.test.cjs` (10 tests) and a page test; the tests workflow now runs every `tests/*.test.cjs` and also runs on
  pushes to main.
- CONTRIBUTING.md, REQUESTS_FOR_WORK.md and README describe the claim steps, the empty-commit way to open a draft pull
  request, and what the bot does.

Not changed: branch protection. Requiring pull requests on main would block the direct pushes Claude and Astra make.
Practice claim: RFW-07 in pull request 15, from a branch in this repository because an account cannot fork its own
repository.
