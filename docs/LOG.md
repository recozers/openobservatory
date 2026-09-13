# Log

Dated entries by either agent: what was done, what was found, what could not be done.

## 2026-09-13 (Claude)
- Initial public release; docs/ASTRA_TODO.md written for the second agent.

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

### 2026-09-13 — Astra A7 contributor guide and mobile layout

Added CONTRIBUTING.md with source/basis/geometry rules, rebuild checks and branch/PR conventions. Asked Stuart for the site name; with no answer received, applied Open Observatory as the reviewable default matching the repository. All public HTML titles/headings use it. On narrow maps the legend is available while the panel is closed and hidden while it is open; the front-page inline width no longer overrides the full-width bottom sheet. Dependency pins are in PR #1 and 12 evidence/inventory tests in PR #2.
