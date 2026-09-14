# Campus links to EPA plant records — B2, 13 September 2026

The register separates a plant's measured gross generation from a campus's physical allocation. None of the current real links qualifies as a campus load proxy. This is a conditional implementation, not a new measured campus.

## Sourced links

- **Southaven CC, ORIS 55269**: TVA's utility plant is separate from the Colossus 2 turbine yard. [TVA's plant description](https://www.tva.com/energy/our-power-system/natural-gas/southaven-combined-cycle-plant) describes its three generating blocks and TVA ownership. The [EPA allocation table](https://www.epa.gov/sites/default/files/2016-09/documents/allocationtable.pdf) and EPA hourly responses identify 55269; 6641 is Independence in Arkansas. No physical supply share to the campus is verified. Southaven is the real negative control, shown only in the CAMPD evidence strip. Existing campus NOx estimates are unchanged.
- **Hyperion's original three proposed CCCT plants**: [Entergy's 20 August 2025 approval announcement](https://www.entergy.com/news/entergy-louisiana-receives-lpsc-approval-for-major-infrastructure-investments-to-support-metas-data-center-and-improve-reliability) schedules two Richland Parish plants for late 2028 and a new Waterford plant for late 2029. The Richland pair is named Franklin Farms 1/2 in Entergy's [2025 performance report](https://www.entergy.com/wp-content/uploads/2026/03/2025-Performance-Report.pdf). Reporting plant IDs, unit rosters and numeric physical output shares remain unknown. Cost recovery for Meta is not a physical output allocation. Do not attach historical Waterford units to the new plant. Later Richland expansion permits in the B1 register are separate projects.
- **Other B1 leads**: no additional verified CAMPD reporting plant was established in the initial permit audit. Abilene's non-export on-site generation registration is not itself a CAMPD plant ID. Pending fleets stay in `data/onsite_generation.csv` until their reporting identity is verified; do not invent IDs or shares.

## Units and independent reconciliation

The apportioned hourly API's `grossLoad` is an operating-hour MW rate: sum `grossLoad * opTime` for gross MWh. `noxMass` is already hourly mass in pounds: sum directly and multiply by 0.45359237 for kg. Explicit off-hours with blank readings are zero; missing unit-hours or missing active-hour gross readings are unknown. Calendar hours, operating unit-hours and reported unit-hours are separate output columns. Average MW divides energy by calendar hours, not the sum of unit operating hours. EPA hours use local standard time; no daylight-saving adjustment. Leap years are handled by calendar month.

Independent EPA apportioned **annual** and **monthly** responses were retrieved 2026-09-13 and saved verbatim in `tests/fixtures/annual_55269_2023.json` and `monthly_55269_2023.json`. Requests use `https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/{annual,monthly}`, facilityId=55269, year=2023, page=1, perPage=500; monthly adds month=1. Credentials are excluded. [EPA CAM API portal](https://www.epa.gov/power-sector/cam-api-portal) documents access.

- 2023 hourly total: **4,609,315.53 MWh**, matching the independently aggregated annual endpoint; 19,463.49 operating unit-hours. Unweighted hourly load would incorrectly give 4,620,360 MWh.
- January 2023: **290,017.02 MWh**, 1,246.58 operating unit-hours, matching the monthly endpoint.
- Hourly 2023 NOx sums to **186.190582 short tons**; the aggregate endpoint reports 186.191 after unit-level rounding. January: 12.856 short tons at aggregate precision. Tests allow 0.002 short tons for three rounded unit totals.
- Replayed 2023–June 2026: **42 complete months**, three verified units AA-001/AA-002/AA-003. July onward is absent, not zero. `results_no2/campd_sources.json` hashes each input hourly CSV. EPA reporting lag means a current calendar quarter can lack reported data.

## Promotion rule and limits

`dedicated_plant_measured` requires relationship=dedicated_supply, allocation_verified=yes, a source URL and a finite contracted physical share >=0.8, valid for every day of a complete three-month quarter. All registered dedicated plants must have complete reporting and valid allocation. Changing the current unit roster invalidates stale aggregates. Missing months, unknown shares, lesser shares, utility ownership and PPAs without established physical delivery remain evidence only. No annual carry-forward is applied.

Eligible output is plant gross generation times physical share. IT equivalent further divides by the site's assumed PUE. Station/network losses and campus imports from elsewhere are unmeasured: this is a supply proxy, not a campus meter or proof of full campus energy. `load_basis=dedicated_plant_measured` and `load_tier=A1` describe the regulator measurement; `cap_basis` and documented capacity remain separate. The scalar proxy uses coincident plot endpoints; these are **not** a zero-width statistical confidence interval. The UI explicitly states that uncertainty has not been established. Zero reported generation does not produce a 'yes' operating statement.

Synthetic tests exercise the qualifying builder/status path; no synthetic site is published. A public 'yes: dedicated plant generated N MW average' remains conditional on a real eligible link. Current Southaven data must never cause that statement for Colossus 2.

## Refresh and validation

`python tools/campd_monthly.py` replays checked-in records. `python tools/campd_monthly.py --fetch` fetches the current and previous years with EPA_API_KEY in the environment; `--years 2023 2024` selects explicit years. An API error raises rather than silently publishing a partial year. The monthly refresh uses fetch when live refresh and EPA credentials are available, otherwise replays saved records. `python tools/refresh.py --dry-run` never contacts EPA.

The test suite checks partial operating hours, direct NOx mass sums, leap months, missing units/hours/measurements, true off-hours, duplicate/wrong plant records, changing rosters, contract dates, missing dedicated plants, synthetic positive/zero/negative status, failed API fetch and independent real EPA aggregates.
