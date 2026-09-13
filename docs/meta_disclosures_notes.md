# Meta per-campus electricity and water disclosures

Extraction notes for the Meta rows in `data/operator_disclosures.csv` (metric `electricity_mwh`, unit MWh; metric `water_m3`, unit m3). Parsed from `pdftotext -layout` output of the primary PDFs below (script: scratchpad `meta/extract.py`, table rows matched by facility label; the parser reproduced all 61 pre-existing Prineville/Lulea/New Albany rows exactly before the 179 new rows were appended).

## Sources (all on sustainability.atmeta.com)

| Years used | Document | Table (page) |
|---|---|---|
| 2011-2015 electricity; 2014-2015 water | https://sustainability.atmeta.com/wp-content/uploads/2023/04/2016-Facebook-Sustainability-Data-Disclosure.pdf | "Electricity Use (MWh)" (p1); "Water Use** (gallons)" (p2) |
| 2016 electricity and water | https://sustainability.atmeta.com/wp-content/uploads/2021/06/2020_FB_Sustainability-Data.pdf | "Electricity Use (MWh)" (p2); "Water Withdrawal (cubic meters)" (p5) |
| 2017-2019 electricity; 2017-2022 water | https://sustainability.atmeta.com/wp-content/uploads/2023/07/Meta-2023-Environmental-Data-Index.pdf | 2.1 "Electricity consumption by facility (In MWh)" (p9); 3.1 "Water withdrawal by facility (in cubic meters)" (p11) |
| 2020-2024 electricity; 2023-2024 water | https://sustainability.atmeta.com/wp-content/uploads/2025/10/Meta_2025-Environmental-Data-Index.pdf | 2.1 "Electricity Consumption by Facility (in MWh)" (p6); 3.1 "Water Withdrawal by Facility (in megaliters)" (p9) |
| (cross-check only) | https://sustainability.atmeta.com/wp-content/uploads/2024/08/Meta-2024-Sustainability-Report.pdf | embedded data index, electricity by facility 2019-2023 (p82), water by facility in ML 2019-2023 (p85) |

Precedence: for each year the most recent disclosure covering it is used (matches the convention of the pre-existing Prineville/Lulea/New Albany rows). Exception: water for 2017-2022 is taken from the 2023 EDI because it reports exact cubic metres, whereas the 2025 EDI rounds to whole megaliters. The 2023 EDI, the 2024 report's index and the 2025 EDI agree exactly on every overlapping site-year (no restatements found). There is no separately published 2022 or 2024 "Environmental Data Index" PDF; the `/asset/2024-esg-data-index/` link redirects to the Responsible Business Practices index, which has no facility data.

## Sites and years found

Electricity (MWh) and water withdrawal (m3) per campus:

| site_id | Label(s) in the PDFs | Electricity years | Water years |
|---|---|---|---|
| prineville | Prineville, OR | 2011-2024 (pre-existing) | 2014-2024 (pre-existing) |
| lulea | Lulea, Sweden | 2012-2024 (pre-existing) | 2014-2024 (pre-existing) |
| prometheus_oh | New Albany, OH | 2019-2024 (pre-existing) | 2019-2023 (pre-existing; 2024 = 86,000 m3 added) |
| meta_forest_city | Forest City, NC | 2011-2024 | 2014-2024 |
| meta_altoona | Altoona, IA | 2013-2024 | 2014-2024 |
| meta_fort_worth | Fort Worth, TX | 2015-2024 | 2016-2024 |
| meta_clonee | Clonee, Ireland ("Clonee, Irleand" in the 2016 PDF) | 2016-2024 | 2017-2024 |
| meta_odense | Odense, Denmark | 2018-2024 | 2019-2024 |
| epoch_meta_sarpy | Papillion, NE (2020 PDF, 2023 EDI) = Sarpy (NE) (2025 EDI) | 2018-2024 | 2019-2024 |
| epoch_meta_los_lunas | Los Lunas, NM | 2018-2024 | 2018-2024 |
| meta_henrico | Henrico, VA (2020 PDF, 2025 EDI) = Richmond, VA (2023 EDI) | 2019-2024 | 2020-2024 |
| meta_dekalb | DeKalb, IL | 2021-2024 | 2021-2024 (2021 = 0) |
| epoch_meta_eagle_mountain | Eagle Mountain, UT | 2021-2024 | 2021-2024 |
| epoch_meta_gallatin | Gallatin, TN | 2021-2024 (2021 = 0) | 2021-2024 (2021, 2022 = 0) |
| epoch_meta_huntsville | Huntsville, AL | 2021-2024 | 2021-2024 |
| meta_newton | Newton County, GA (2023 EDI) = Stanton Springs (GA) (2025 EDI) | 2021-2024 | 2021-2024 |
| meta_kansas_city | Kansas City (MO) | 2024 only (22,963 MWh, first partial year) | 2024 |
| meta_mesa | Mesa (AZ) | 2024 only (24,657 MWh, first partial year) | 2024 |

2024 electricity (MWh), 2025 EDI: Prineville 1,728,291; Altoona 1,585,392; Sarpy 1,258,239; Newton/Stanton Springs 1,184,380; Los Lunas 1,143,067; Eagle Mountain 1,115,619; Fort Worth 1,109,004; Clonee 1,076,961; Henrico 948,859; Huntsville 865,803; Odense 569,374; Forest City 535,555; New Albany 521,217; Lulea 468,809; DeKalb 372,339; Gallatin 359,730; Mesa 24,657; Kansas City 22,963. Owned data centers total 18,061,781 MWh.

## Not found in any disclosure (through reporting year 2024)

epoch_meta_rosemount, epoch_meta_jeffersonville, epoch_meta_montgomery, epoch_meta_kuna, epoch_meta_temple, epoch_meta_cheyenne, epoch_meta_aiken, hyperion_la (Richland Parish). None of these campuses appears in any facility table; per Meta's footnote, owned online data centers are always listed by site even below the 100,000 MWh threshold, so absence means no metered consumption was reported for them by end-2024 (Temple TX, which had buildings under construction in 2024, is not listed either). epoch_meta_qts_hillsboro_2 is a leased/colocation site and would fall inside the aggregate lines below.

## Aggregates deliberately not loaded as sites

- "Leased data center facilities" (2025 EDI: 795,000 / 964,650 / 1,105,834 / 2,187,020 / 3,069,504 MWh for 2020-2024) and its predecessors "East Coast Leased Data Center Facility" / "East Coast Colocation Facility" / "West Coast Colocation Facility" (2011-2019). These are colocation leases (the East Coast facility is the Ashburn-area lease), not campuses; the leased line roughly tripled 2022-2024.
- "Other data center-related facilities": facilities under 100,000 MWh/yr (warehouses, network, small colos).
- Offices.

## Ambiguities and caveats

- Rounding: 2011-2016 values are rounded (the 2016 PDF rounds <1,000 to the nearest 100, otherwise to the nearest 1,000; totals computed before rounding); 2017-2020 values are rounded to the nearest 1,000 MWh / 1,000 m3; 2021+ values are exact. Water for 2023-2024 comes only in whole megaliters (stored as ML x 1,000 m3, so precision is +/-500 m3).
- Water metric: all `water_m3` rows are withdrawal, not consumption. Meta publishes water consumption only as fleet totals (data centers total / offices total), never per site, so no `water_consumption_m3` rows could be added. Fleet WUE (L/kWh) is already stored under `meta_fleet`.
- Construction water is excluded from the site tables: Meta notes an additional 1,780,000 m3 (2022) and 1,019 ML (2024) withdrawn for data center construction, not attributed to sites.
- 2014-2015 water was reported in US gallons and converted at 3.78541 L/gal (stated in each row's note). The 2016 water figures in gallons (2016 PDF) were superseded by the 2020 PDF's cubic-metre figures, which are lower for several sites (Fort Worth 17,791 vs 14,000; Lulea 36,718 vs 32,000; Forest City 132,868 vs 123,000; Altoona 90,850 vs 87,000 m3). The later restated values were used, matching the pre-existing Prineville/Lulea 2016 rows.
- Zero rows: Gallatin 2021 electricity = 0 and DeKalb 2021 / Gallatin 2021-2022 water = 0 are stored as reported (site listed but not yet drawing); first partial years (e.g. Altoona 2013 = 400 MWh, Fort Worth 2015 = 100 MWh, Clonee 2016-2017 = 1,000 MWh) are flagged in the note column. Treat these as non-operational when fitting load models.
- Campus renames: Henrico is labelled "Richmond, VA" in the 2023 EDI; Sarpy is "Papillion, NE" before the 2025 EDI; the Newton County, GA campus is "Stanton Springs (GA)" in the 2025 EDI. Each is one campus and is stored under one site_id with the alias in the note.
- New Albany 2024 (521,217 MWh) is 34% below 2023 with no explanation in the index (pre-existing row already notes this); every other campus grew or held flat in 2024.
- Not touched: the CSV already contained duplicate (site_id, year, metric) keys for google_council_bluffs / google_the_dalles `pue` rows (2018-2024) before this pass.
