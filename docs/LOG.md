# Log

Dated entries by either agent: what was done, what was found, what could not be done.

## 2026-09-13 (Claude)
- Initial public release; docs/ASTRA_TODO.md written for the second agent.

## 2026-09-13 (Astra, A6 — monthly refresh)
- Added service-account authentication from `EE_SERVICE_ACCOUNT_JSON` or a local key path; CI never launches interactive authentication. Existing local OAuth remains supported. Five credential tests pass.
- Added monthly/manual refresh and a PR dry-run. Local dry-run rebuilt and strictly parsed 60 JSON files without Earth Engine credentials. Live runs commit only site data and explicitly dispatch Pages (a GITHUB_TOKEN push does not trigger another push workflow).
- Recorded the five published flux profile mappings. The undocumented Colossus 2 seasonal baseline was recovered as before 2025-07-01: reproduces every existing monthly NOx value to the 0.05 kg/h CSV rounding tolerance. Other plant mappings reproduce existing series. Raw research profiles stay research inputs.
- Pinned earthengine-api 1.7.43, tabulate 0.10.0 and openpyxl 3.1.5 to the installed versions; scipy was already pinned.
- Service-account live extraction is not yet validated on GitHub: Stuart must configure the documented secrets. New daily NOx profiles are not downloaded by this workflow. The derived series are recomputed from saved profiles.
- GitHub validation: both the PR dry-run and an actual `workflow_dispatch` dry-run passed; dispatch run https://github.com/recozers/openobservatory/actions/runs/34760217886. A6 acceptance criteria met (PR #1).
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

### 2026-09-13 — Astra refresh integration regression fixed

Current-main integration exposed an empty NO2 pre-change baseline at Prometheus after the new annual electricity rows moved its capacity start earlier. NaN mean/SE/z values made public JSON invalid. Empty or single-sample baselines now use null uncertainty and cannot produce a z-score. The saved-evidence dry run again validates all 60 JSON files. This shared build-file change is also applied in PR #2 with a strict JSON audit.
- Lights-to-radar over the 40 brightest campus-like blobs of the national scan (results_s1/china/summary.csv): 35 of 40
  contain a new structure >= 5 ha and 27 one >= 20 ha (median largest 47 ha, max 218 ha); the chips checked are
  petrochemical, logistics and factory complexes (Ningbo, Yinchuan, east Chongqing). Data centres are a small minority of
  large new lit structures, so the chain needs a hall-morphology step before it is a data-centre detector; inside hub
  boxes the radar scan alone already ranks the campuses first (Ulanqab, Horinger). Chips for the 40 blobs are in
  results_s1/china/ for classification (Astra A8 pattern).
