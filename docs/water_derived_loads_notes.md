# Water-derived electricity estimates per campus (task B3)

Companion to `data/water_derived_loads.csv` (234 rows: Google 2022-2025, Meta 2020-2024, Microsoft FY2025).
Compiled 2026-09-13 from the operators' own reports (PDFs fetched and read; page/table cited per row).
Built by `build_water_loads.py` (scratchpad); all inputs are transcribed report values.

## Method

Evaporative cooling consumes water in proportion to the heat rejected, so for a water-cooled campus

    IT energy (kWh)      = water consumed (L) / WUE (L per kWh of IT energy)
    facility energy (GWh) = IT energy x PUE / 1e6

The CSV column `energy_gwh_estimate` is facility energy (IT x PUE). Average load = GWh / 8.76 MW.
Each row states which water quantity (consumed or withdrawn) and which WUE (fleet, fleet-implied, regional)
was used, because the three operators define WUE differently:

| Operator | Water quantity published per site | WUE published | WUE basis | PUE published |
|---|---|---|---|---|
| Google | withdrawal, discharge, consumption (million gallons) per campus, 2022-2025 | **none** | implied here: fleet DC water consumption / (fleet DC electricity / fleet PUE) | per campus |
| Meta | withdrawal (ML) per facility; consumption fleet-only | fleet | **withdrawal** L per IT kWh (Meta's definition) | fleet only |
| Microsoft | withdrawal (ML) per metro, FY25 only; consumption region-only | global + region | "water used for humidification and cooling" per IT kWh | global + region |

Meta and Microsoft also publish per-site electricity, so for those two the water-derived number is a
validation exercise, not new information; the ratio estimate/actual is reported in every note.

## WUE and PUE values used

**Google (no WUE published; fleet-implied).** From the 2026 report's Environmental data tables
(`Electricity consumption` row "Data centers": 2021 17,429,800; 2022 20,616,500; 2023 23,980,800;
2024 30,637,100; 2025 42,415,800 MWh - these are the 2026 report's recalculated values, which differ by
~1% from the 2025 report), fleet PUE 1.10/1.10/1.10/1.09/1.09 (2021-2025), and the "Data centers total"
row of the water tables (consumption 5,219.9 / 6,100.6 / 7,787 / 10,523 million gallons for 2022-2025):

| year | implied fleet WUE, consumption basis (L/kWh IT) | withdrawal basis |
|---|---|---|
| 2022 | 1.054 | 1.337 |
| 2023 | 1.059 | 1.330 |
| 2024 | 1.049 | 1.329 |
| 2025 | 1.024 | 1.319 |

Because the implied WUE is (fleet water)/(fleet IT energy), the estimate for a campus is simply its share
of Google's data-centre water consumption times Google's data-centre electricity, scaled by site PUE /
fleet PUE. Boundary caveat: the "Data centers" electricity row covers all data-centre operations in
Google's reporting boundary, the water table covers Google-owned campuses plus an "Other data center
locations" line (7-8% of consumption); air-cooled campuses contribute electricity but ~no water, so the
implied WUE is a few percent low for water-cooled campuses (estimates slightly high). Site PUE is Google's
campus PUE where published (mean of the two facilities for Council Bluffs and The Dalles, which share one
water row); fleet PUE otherwise (`pue_scope` column).

**Meta (stated fleet WUE, withdrawal basis).** 2025 Environmental Data Index: PUE 1.10, 1.09, 1.08,
1.08, 1.08 and WUE 0.30, 0.26, 0.20, 0.18, 0.19 L/kWh for 2020-2024. Cross-check: Meta's own owned-data-
centre totals (withdrawal minus leased and "other" lines, electricity likewise, divided by PUE) imply
0.43, 0.38, 0.31, 0.24, 0.24 L/kWh - i.e. Meta's stated WUE is 20-30% below the aggregate its tables
imply (probably a different IT-load meter or site weighting). Both are carried in the notes.

**Microsoft (regional, FY25).** datacenters.microsoft.com/sustainability/efficiency: FY25 PUE global
1.17, Americas 1.16, EMEA 1.16, Asia Pacific 1.28; WUE global 0.27, Americas 0.34, EMEA 0.03, Asia
Pacific 0.25 L/kWh (FY24: 0.30 / 0.38 / 0.03 / 0.03). Boundary: Microsoft-owned datacentres operational
for 12 months. Table 15 of the 2026 Data Fact Sheet gives FY25 electricity (MWh) and water withdrawal
(ML) per metro, excluding commissioning and metros under 1% of the total.

## Validation against Meta's actual electricity (ratio = water-derived / reported)

2024, stated WUE 0.19 (implied 0.236 in brackets), site WUE = withdrawal / (electricity/1.08):

| Meta site | actual GWh | ratio | site WUE L/kWh | comment |
|---|---|---|---|---|
| Forest City NC | 536 | 0.17 (0.14) | 0.03 | very little water; mostly free-air |
| Lulea SE | 469 | 0.35 (0.28) | 0.07 | free-air cooling year-round |
| Henrico VA | 949 | 0.55 (0.44) | 0.11 | |
| Sarpy NE | 1,258 | 0.64 (0.52) | 0.12 | |
| Eagle Mountain UT | 1,116 | 0.68 (0.54) | 0.13 | |
| Stanton Springs GA | 1,184 | 0.70 (0.56) | 0.13 | |
| Altoona IA | 1,585 | 0.87 (0.70) | 0.17 | |
| New Albany OH | 521 | 0.94 (0.75) | 0.18 | |
| Prineville OR | 1,728 | 1.08 (0.87) | 0.21 | |
| Los Lunas NM | 1,143 | 1.25 (1.01) | 0.24 | |
| Huntsville AL | 866 | 1.37 (1.10) | 0.26 | |
| Fort Worth TX | 1,109 | 1.59 (1.28) | 0.30 | |
| DeKalb IL | 372 | 1.60 (1.29) | 0.31 | ramping |
| Odense DK | 569 | 2.92 (2.34) | 0.55 | |
| Clonee IE | 1,077 | 3.01 (2.42) | 0.57 | |
| Gallatin TN | 360 | 3.24 (2.60) | 0.62 | first full year |
| Kansas City MO | 23 | 10.2 (8.2) | 1.93 | commissioning |
| Mesa AZ | 25 | 13.1 (10.6) | 2.50 | commissioning |

Medians of the ratio by year (stated WUE): 2020 0.76, 2021 0.99, 2022 0.94, 2023 0.81, 2024 1.17.
Excluding sites in commissioning or first year, the 2024 interquartile range is roughly 0.6-1.6 and
the full range 0.17-3.0. So even within one operator with a uniform cooling design (direct evaporative),
a fleet WUE reproduces a site's electricity only to within about a factor of 2 (1 sigma ~ +/-50%),
and free-air-cooled northern sites are underestimated 3-6x.

## Validation against Microsoft's actual electricity (FY25, regional WUE)

Americas metros (WUE 0.34, PUE 1.16): Ashburn 0.98, San Antonio 0.99, Manassas 0.94, Cheyenne 0.59,
East Wenatchee 0.58, Des Moines 0.42, Boydton 0.40, Chicago 1.88, Quincy 3.19, Phoenix 3.51
(site WUE 0.13-1.2 L/kWh; Phoenix and Quincy are the large evaporative sites, Boydton/Des Moines are
the low-water ones). Median ~0.96, range 0.4-3.5. EMEA metros (WUE 0.03): Dublin 0.53, Gavle 0.77,
Hollands Kroon 1.38 - fine as a group, but the regional WUE is so low (free/adiabatic cooling) that
water carries almost no load information there. Small metros and APAC (Singapore 6.4, Jakarta 19)
are far off. Water withdrawal, not cooling consumption, is what Microsoft publishes per metro, which
inflates the ratio where domestic/other use dominates.

## Google campuses in the inventory: estimates (facility GWh; avg MW in brackets)

| site_id | 2022 | 2023 | 2024 | 2025 | notes |
|---|---|---|---|---|---|
| epoch_google_council_bluffs_east | 3,539 (404) | 3,835 (438) | 3,975 (454) | 5,450 (622) | both Council Bluffs campuses; East campus is a part of this |
| epoch_google_pryor_north | 2,724 (311) | 3,204 (366) | 3,338 (381) | 4,479 (511) | whole Mayes County campus |
| epoch_google_new_albany | 203 (23) | 500 (57) | 1,362 (156) | 3,276 (374) | consumption 352.7 -> 835.7 MG in 2025 |
| epoch_google_columbus (Lockbourne) | - | 92 (10) | 548 (63) | 1,409 (161) | |
| epoch_google_the_dalles | 1,068 (122) | 1,173 (134) | 1,409 (161) | 1,873 (214) | both campuses |
| epoch_google_papillion | 189 (22) | 525 (60) | 1,640 (187) | 2,210 (252) | |
| epoch_google_midlothian | 389 (44) | 548 (63) | 724 (83) | 896 (102) | |
| epoch_google_lancaster | - | 30 (3) | 398 (45) | 522 (60) | |
| epoch_google_bristow | - | - | 332 (38) | 1,079 (123) | |
| epoch_google_omaha | - | - | 126 (14) | 714 (82) | |
| epoch_google_red_oak | - | - | - | 203 (23) | |
| epoch_google_fort_wayne (New Haven IN) | - | - | - | 152 (17) | probable match, verify |
| epoch_google_mesa | - | - | - | invalid | air-cooled (Google 2025 report) |
| epoch_google_storey_county | invalid | invalid | invalid | invalid | air-cooled (report endnote) |

Given the Meta/Microsoft scatter, treat each Google figure as good to roughly a factor of 2, better
for the large, mature, evaporatively cooled campuses (Council Bluffs, Mayes County, The Dalles) whose
cooling design matches the fleet average. Council Bluffs at ~450 MW (2024) and Mayes County at ~380 MW
are consistent with the campuses' known scale.

## Dry-cooled or otherwise invalid campuses

- Google, "Air-cooled facility" endnotes (2023-2026 reports): Dublin, Montreal, Pflugerville TX,
  Phoenix AZ, San Bernardo, Storey County NV, Sydney, Wilmer TX. Mesa AZ and Waltham Cross UK use air
  cooling per the 2025 report's water-stewardship text. Hamina uses seawater (not in the withdrawal
  figure). Frankfurt, Hanau, Middenmeer, Winschoten report < 15 MG and are flagged low-confidence.
  Rows for these carry `method = invalid_air_cooled` or `low_confidence_negligible_water`.
- Meta: Lulea and Forest City are not dry-cooled but use so little water that the method gives 0.2-0.35x.
- Microsoft EMEA (WUE 0.03) and Boydton/Des Moines/Cheyenne: water is a weak proxy.
- Cross-operator transfer is invalid: Google's implied WUE (~1.05 L/kWh, consumption) is ~5x Meta's
  (0.19-0.24, withdrawal) and ~3x Microsoft Americas (0.34) because the cooling technologies differ
  (Google: chilled-water plants with cooling towers; Meta: direct evaporative outside-air cooling;
  Microsoft: mixed adiabatic/air). Never apply one operator's WUE to another.

## Not found / limitations

- Google publishes no WUE and no per-campus electricity; the WUE here is inferred from fleet totals.
- Google water rows merge the two Council Bluffs campuses and the two The Dalles campuses.
- No Google water rows for inventory sites Arcola VA, Kansas City East, Cedar Rapids, Lincoln NE,
  Waltham Cross, Goodnight TX (not operating or below the reporting threshold in 2025).
- Meta publishes per-facility water withdrawal but only fleet water consumption; its 2025 EDI table 3.2
  has the 2021 data-centre and office consumption values swapped (162 vs 2,406 ML). No 2026 Meta
  Environmental Data Index (2025 data) was located as of 2026-09-13. Meta inventory sites not in Meta's
  tables: Kuna, Temple, Cheyenne, Aiken, Rosemount, Jeffersonville, Montgomery, Hyperion, QTS Hillsboro.
- Microsoft gives only FY25, only withdrawal, only per metro, and PUE/WUE only per region; Fairwater
  WI and Fairwater Atlanta were not operating in FY25 and are absent. The Goodyear, SAT14/SAT40 and
  Project Osmium inventory sites sit inside the Phoenix, San Antonio and Des Moines metro rows.
- Google's 2026 report recalculated 2021-2024 electricity (endnote 194); the 2026 values are used.

## Sources

- Google 2026 Environmental Report (2025 data): https://sustainability.google/files/google-2026-environmental-report.pdf - Appendix > Environmental data: "Electricity consumption" table, "Data center energy efficiency (PUE)" (p. 95), "Water use by data center location" 2025 (p. 97)
- Google 2025 Environmental Report (2024 data): https://www.gstatic.com/gumdrop/sustainability/google-2025-environmental-report.pdf - PUE table (p. 108), water by location (pp. 109-110), assured "Alphabet's Schedule of Water Use by Data Center Location" FY2024
- Google 2024 Environmental Report (2023 data): https://www.gstatic.com/gumdrop/sustainability/google-2024-environmental-report.pdf - Appendix environmental data, "Water use by data center location" 2023
- Google 2023 Environmental Report (2022 data): https://www.gstatic.com/gumdrop/sustainability/google-2023-environmental-report.pdf - "Water use by data center location" 2022 (pp. 94-95), PUE table
- Meta 2025 Environmental Data Index (2020-2024): https://sustainability.atmeta.com/wp-content/uploads/2025/10/Meta_2025-Environmental-Data-Index.pdf - 2.1 Electricity Consumption by Facility; 2.4 PUE; 3.1 Water Withdrawal by Facility, WUE; 3.2 Water Consumption; definitions page ("Annual WUE is calculated by dividing our water withdrawal, in liters, by IT electricity load, in kWh")
- Microsoft 2026 Environmental Data Fact Sheet (FY25): https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf - Table 13 (electricity by region), Table 14 (water by region), Table 15 (FY25 datacenter water and electricity by location, p. 25; footnotes p. 26)
- Microsoft datacenter efficiency page (regional PUE/WUE FY24-FY25, WUE definition): https://datacenters.microsoft.com/sustainability/efficiency/
- Microsoft 2026 Environmental Sustainability Report (FY25 global WUE 0.27, 25% below 2022 baseline): https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Environmental-Sustainability-Report-PDF.pdf
