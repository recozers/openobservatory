# Gas-plant calibration screening — 13 September 2026

Three gas-turbine candidates now have full 2023 CAMPD hourly records and new TROPOMI flux profiles. They are not yet accepted as isolated low-stack references: physical stack heights and non-power-source isolation remain unverified. Production calibration is unchanged.

The screening script found 77 gas-labelled eGRID plants at or above 1,000 short tons NOx/year. Of these, 23 have another ≥1,000-short-ton eGRID power plant within 15 km. Of the other 54, a full-year API query returned hourly rows for 26 and no rows for 28. Gas-labelled plants often include boilers; unit-level annual data prevent treating these as pure turbine references. Denton and Pearsall returned no hourly rows, consistent with their previously empty CSVs. This is not proof that no hourly emissions exist in another reporting system.

Three candidates were extracted: Forney (55480), Fort Myers (612), and Midland Cogeneration Venture (10745). Their nearest other qualifying eGRID power plants are 84.18, 136.60 and 166.67 km away respectively. This power-sector screen does not cover every industrial emitter. Midland has mixed industrial surroundings; a campus-wide plume attribution is especially uncertain. A GAS fuel label is not a stack-height measurement.

## Results

Factors below use the same saved near-source plateau (1–9 km) and NOx/NO2 conversion as the existing calibration. The table shows both the legacy CAMPD local hours 19–20 and the time-zone-adjusted proxy. Satellite daily samples are identical within each pair.

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

The gas factors span roughly 0.9–4.7 after the time-window conversion. This does not justify a common low-stack factor or pooling them with coal: source mixing, controls, stack geometry, retrieval bias and meteorology are still confounded. Reported errors propagate satellite sampling only; they do not include all systematic or hourly reporting uncertainty.

## Time convention correction

EPA reports hourly emissions in **local standard time**, without daylight-saving changes; see [EPA Part 75 technical questions, question 13.4](https://www.epa.gov/system/files/documents/2025-09/part_75_emissions_monitoring_technical_questions_and_answers.pdf), printed page 212. The existing code selects `hour in [19, 20]` directly while the flux code averages winds at UTC 19–21. These are different windows. The comparison converts UTC 19/20 to local standard time: 13/14 for the Central sites and 14/15 for the Eastern sites. This is still a proxy: precise per-pass satellite timestamps are not stored in the existing profiles. A proper recalibration should align actual overpasses before altering public factors.

## Reproduction and validation

1. `python tools/low_stack_screen.py --probe --annual` queries the EPA hourly/annual APIs, caching responses without credentials. It uses the bundled `data/egrid/plants_2023.csv` and explicitly defines a large neighboring power emitter as ≥1,000 short tons/year.
2. Run `python tools/campd_hourly.py FACILITY 2023` for 55480, 612 and 10745. The committed full hourly CSVs are public EPA data.
3. Run `tools/no2_flux.py` for each candidate over 2023 using the coordinates in `results_no2/low_stack_screen_2023.csv`, writing `flux_forney_gas_2023.csv`, `flux_fort_myers_gas_2023.csv` and `flux_midland_gas_2023.csv`.
4. `python tools/compare_stack_calibration.py` reproduces all 16 rows without credentials. It rejects duplicate unit-hours and requires new candidates’ summed hourly NOx (lb ÷ 2,000) to match the independently fetched annual endpoint within 0.1%. All three pass. Full annual endpoint records, screening results, source hashes and flux profiles are retained.

CAMPD covers measured, derived and substitute emissions according to reporting rules, not necessarily raw CEMS observations in every hour. The [EPA data guide](https://www.epa.gov/system/files/documents/2022-07/CAMD%27s%20Power%20Sector%20Emissions%20Data%20Guide%20-%2007182022.pdf) explains that apportioned hourly mass already accounts for partial-hour operation. Do not multiply the CAMPD mass by operating time again.

A5 remains blocked on validating physical stack class, broader emitter isolation and actual overpass alignment. A draft PR preserves the evidence and comparison; it does not meet the claim of three fully qualified low-stack reference plants.
