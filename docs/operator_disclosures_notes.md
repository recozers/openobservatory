# Operator-published electricity, PUE and water disclosures (per site)

Companion to `data/operator_disclosures.csv` (138 rows). Compiled 2026-09-13 from the operators' own
reports where they exist; secondary sources are flagged in the CSV `note` column. Implied average load
= annual MWh / 8760 (facility load, PUE included). "Not found" means searched and not located, not
that the figure does not exist.

## Summary table (latest year available)

| site_id | Operator disclosure | Latest MWh/yr | Implied avg MW | Stated capacity | Site PUE | Water |
|---|---|---|---|---|---|---|
| prineville | Meta, per site, 2011-2024 | 1,728,291 (2024) | 197 MW (183 MW IT at fleet PUE 1.08) | none published by Meta | fleet 1.08 | 328,000 m3 withdrawn (2024) |
| lulea | Meta, per site, 2012-2024 | 468,809 (2024) | 54 MW (50 MW IT) | 120 MW grid feed (utility/press, in sites.csv) | fleet 1.08 | 29,000 m3 (2024) |
| prometheus_oh (New Albany) | Meta, per site, 2019-2024 | 521,217 (2024); 793,063 (2023) | 60 MW (2024), 91 MW (2023) | none published | fleet 1.08 | 86,000 m3 (2024) |
| hyperion_la | Meta capacity only | not yet reported | n/a | 2 GW "by 2030", 5 GW full build (Meta) | n/a | none |
| google_council_bluffs | Google: PUE + water only | electricity NOT published | n/a | none | 1.11 / 1.07 (two campuses, 2024) | 5.34 Mm3 withdrawn, 3.82 Mm3 consumed (2024) |
| google_the_dalles | Google: PUE + water only | electricity NOT published | n/a | none | 1.10 / 1.06 (2024) | 1.75 Mm3 withdrawn, 1.37 Mm3 consumed (2024) |
| fairwater_wi | Microsoft: nothing site-specific yet | not found | n/a | ~3.3 GW by late 2027 (Epoch AI estimate, secondary) | Americas region 1.16 (FY25) | planned peak 2.8 M gal/yr Phase 1, 8.4 M gal/yr full (Racine records) |
| nsa_utah | none by operator | not found | ~59 MW implied from "$18M/yr at 2.7-4.3 c/kWh" (derived) | 65 MW facility (Army Corps, 2013) | none | peak months 23,000-25,000 m3 (Bluffdale billing, 2013-14) |
| ornl_olcf | ORNL technical reports (Frontier only) | 100,000 (Frontier, 2022) | 12.2 MW avg Frontier (2023) | Frontier 8-28 MW; 40 MW power/cooling provision | 1.05 (Frontier, 2023) | not found |
| rainier_in | none by AWS | not found (NDA) | n/a | 2,250 MW grid at 90% load factor (I&M IURC filings); Phase 1 ~590 MW IT (secondary) | none | none by operator |

## What each operator publishes

### Meta (Prineville, Lulea, New Albany, Hyperion)
- Resolution: annual, per owned data-center campus, whole-campus totals (all buildings). Metrics per site:
  electricity (MWh), water withdrawal (m3/ML), market- and location-based Scope 2. PUE and WUE are
  fleet-wide only (1.08 and 0.19 L/kWh in 2024).
- History: the series starts in 2011 (Prineville) / 2012 (Lulea) / 2019 (New Albany). Documents used:
  - 2016 Facebook Sustainability Data Disclosure (2011-2016 electricity; 2014-2016 water in gallons; PUE 2011-2016)
    https://sustainability.atmeta.com/wp-content/uploads/2023/04/2016-Facebook-Sustainability-Data-Disclosure.pdf
  - 2020 Facebook Sustainability Data (2016-2020)  https://sustainability.atmeta.com/wp-content/uploads/2021/06/2020_FB_Sustainability-Data.pdf
  - 2021 Meta ESG Data Index (2017-2021)  https://sustainability.fb.com/wp-content/uploads/2022/06/2021-Meta-Sustainability-ESG-Data-Index.pdf
  - 2023 Environmental Data Index (2017-2022, water in m3)  https://sustainability.atmeta.com/wp-content/uploads/2023/07/Meta-2023-Environmental-Data-Index.pdf
  - 2025 Environmental Data Index (2020-2024, water in ML)  https://sustainability.atmeta.com/wp-content/uploads/2025/10/Meta_2025-Environmental-Data-Index.pdf
  These are PDFs (Meta's "spreadsheet" disclosures are published as PDF tables); values before 2021 are
  rounded to 1,000 MWh, later years are exact. Sites below 100,000 MWh are still reported by name.
- Implied average load (MW = MWh/8760), facility basis:
  - Prineville: 8.1 (2011), 17.5, 25.6, 29.9, 32.4, 37.3 (2016), 48.6, 55.7, 65.4, 78.3 (2020), 102.6, 112.1, 157.0 (2023), 197.3 (2024).
    Growth is roughly linear with the 2-to-11 building expansion; the 2023-24 jump (+353 GWh in one year) is the largest step in the series.
    No Meta-published capacity exists to compare against; the CSV `sites.csv` carries it as unknown.
  - Lulea: 0.6 (2012), 6.1, 12.0, 21.3, 33.7 (2016), 34.4, 38.5, 42.6, 42.1 (2020), 34.9, 30.5 (2022), 40.2, 53.5 (2024).
    Against the 120 MW dual grid feed quoted in sites.csv the site has averaged 30-54 MW, i.e. 25-45% of the
    feed. The 2021-22 dip (-100 GWh) and 2023-24 recovery are real reported values, not restatements.
  - New Albany: 4.3 (2019), 30.8, 58.4, 80.2, 90.5 (2023), 59.5 (2024). The 2024 drop of 272 GWh is in Meta's
    index and is mirrored in location-based Scope 2; Meta gives no explanation (possible scope change).
- Hyperion (Richland Parish): only announced capacity ("over two gigawatts", "5 gigawatts of compute
  capacity", https://datacenters.atmeta.com/richland-parish-data-center/). Not in the 2025 index; the first
  reported electricity should appear in the 2026 or 2027 index once buildings are online.

### Google (Council Bluffs, The Dalles) - as a check on per-site availability
- Publishes per campus: annual PUE (since the 2023 report, back-filled to 2018 for most campuses; two
  campuses each at Council Bluffs and The Dalles) and, since the 2023 report (2022 data), water withdrawal,
  discharge and consumption in million gallons. The 2024 water table is third-party assured
  ("Alphabet's Schedule of Water Use by Data Center Location").
- Does NOT publish per-site electricity. Electricity is company-wide only (fleet PUE 1.09 in 2024).
- Reports: https://www.gstatic.com/gumdrop/sustainability/google-2023-environmental-report.pdf (2022 water,
  2018-2022 PUE), .../google-2024-environmental-report.pdf (2023), .../google-2025-environmental-report.pdf (2024).
- Council Bluffs water withdrawal 1,236 -> 1,335 -> 1,410 million gal (2022-24); The Dalles 352 -> 384 -> 461.
  Withdrawal-to-consumption ratio ~0.72-0.78 at both sites (evaporative cooling).

### Microsoft (Mount Pleasant / Fairwater)
- Regional PUE/WUE (Americas, EMEA, APAC, global) for FY24 and FY25 at
  https://datacenters.microsoft.com/sustainability/efficiency/ (Americas FY25: PUE 1.16, WUE 0.34 L/kWh).
- New in the 2026 Environmental Data Fact Sheet (Table 15): FY25 electricity (MWh) and water withdrawal (ML)
  by metro for owned datacenters, e.g. Des Moines 2,152,335 MWh / 264 ML; Boydton 3,113,847 MWh; Quincy
  1,381,569 MWh / 1,292 ML. Wisconsin is absent because Fairwater only became fully operational in June 2026
  (FY26). Expect a Mount Pleasant row in the 2027 fact sheet (FY26 data), possibly excluded as commissioning.
  https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf
- Site-specific: water only, and only from City of Racine public records (WPR, 17 Sep 2025): Phase 1 peak
  234,000 gal/day = 2.8 M gal/yr (10,600 m3); full campus 702,000 gal/day = 8.4 M gal/yr (31,800 m3);
  Microsoft says >90% of the campus is closed-loop. No MW figure from Microsoft; Epoch AI estimates ~3.3 GW
  by late 2027 (secondary). A "Phase 1 maximum 400 MW" figure appears in press summaries but I could not
  verify its primary source, so it is not in the CSV. We Energies/PSC Wisconsin docket 6630-TE-113 (rate
  approved 24 Apr 2026) and the July 2026 15-year contract were not retrieved in full.

### NSA Utah Data Center
- No operator disclosure. Best primary-adjacent figures: 65 MW facility load, ~$18 M/yr power bill at
  2.7-4.3 c/kWh (Salt Lake Tribune, 30 Jun 2013, citing Rocky Mountain Power and the Army Corps); Wired's
  $40 M/yr estimate (via Data Center Knowledge, 20 May 2013). $18 M / 3.5 c/kWh ~ 514 GWh/yr ~ 59 MW average,
  i.e. the 65 MW figure was treated as near-continuous load in 2013 planning; this is a derivation, not data.
- Water: Bluffdale billing records released after a GRAMA fight (Salt Lake Tribune 26 Apr 2014 and 2 Feb 2015):
  monthly usage 0.76-6.2 M gal in 2013 (peak July), up to 6.6 M gal in Aug 2014; design 1.7 M gal/day
  later cut to 1.2 M gal/day. Summer peaks of ~6.5 M gal/month are ~15-18% of the design rate, consistent
  with the facility running well below 65 MW in 2013-14.
- Not found: any metered MWh. Utah PSC docket 26-035-05 (>100 MW large-load contract, 2026) is redacted
  and is not identifiable as NSA. The MIDA energy-tax stream (0.5-6% on RMP sales to the site) is a
  possible back-door via the State Auditor's MIDA dashboard but was not pursued.

### ORNL OLCF (Building 5600)
- ORNL publishes campus-wide utility totals in its annual Site Sustainability Plan (FY2024: 564,744 MWh,
  $35.8 M; four HEMSFs incl. the HPC facility take ~66% of campus electricity, but the OLCF share is only
  shown as a bar chart). https://info.ornl.gov/sites/publications/Files/Pub225618.pdf
- Frontier-specific measured energy: ORNL/TM-2023/3218 (1 Jan-31 Dec 2022: 1e8 kWh, monthly 6.5-16.5 MW,
  PUE 1.04-1.10) https://info.ornl.gov/sites/publications/Files/Pub207081.pdf and Scientific Data 2024
  (1 Jan-31 Dec 2023: average 12.2 MW, idle 8.5, peak 28.5, cooling 0.6 MW, PUE 1.05)
  https://www.nature.com/articles/s41597-024-03913-w. Implied 2023 Frontier energy ~107 GWh.
- Comparison with sites.csv capacity (10.1 MW = Summit HPL): Frontier alone averaged 11.4 MW (2022) and
  12.2 MW (2023), with Summit (retired Nov 2024) still in the same building, so building 5600's total load
  in 2022-23 was plausibly 18-25 MW, roughly double the Summit-only capacity in sites.csv.
- Not found: whole-building 5600 metered annual electricity or water. The Better Buildings showcase page
  (betterbuildingssolutioncenter.energy.gov) refused connections during this session.

### Amazon (New Carlisle / Project Rainier)
- AWS publishes no per-site electricity or water (global WUE only). Capacity: 2,250 MW grid connection at a
  90% load factor per Indiana Michigan Power's IURC filings (GovTech, 23 Apr 2025); Phase 1 ~590 MW IT in nine
  ~65 MW buildings, Phase 1 cooling water permitted 1.58 M gal/day, ~0.8 M gal/day average (MeasuredAI,
  secondary). Actual draw is under NDA. I&M's large-load tariff (IURC order Feb 2025) does not publish
  customer-level usage.

### EU Energy Efficiency Directive data-centre database (Lulea)
- Operators with >=500 kW IT load (Meta Lulea qualifies) report annually to the EU database (first report
  for CY2023 by 15 Sep 2024; CY2025 by 15 May 2026). Per Annex IV of Delegated Regulation 2024/1364 and the
  Swedish Energy Agency, the data are published only in aggregated form at member-state and EU level; no
  per-facility figures are public. https://www.energimyndigheten.se/en/climate/climate/data-centre-energy-performance-reporting/
  and https://energy.ec.europa.eu/topics/energy-efficiency/energy-efficiency-targets-directive-and-rules/energy-efficiency-directive/energy-performance-data-centres_en
  Meta's own index remains the only per-site source for Lulea.

## Not found (searched)
- Meta: per-site PUE/WUE, per-site IT capacity, any Hyperion energy/water. Meta site info sheets (Lulea,
  Prineville) carry community and renewable-PPA figures only.
- Google: per-site electricity for any campus.
- Microsoft: any Wisconsin-specific PUE, WUE, or MWh; Microsoft-stated MW for Fairwater.
- NSA: metered electricity; identity of any RMP special contract for the site.
- ORNL: building-level annual electricity/water for 5600; OLCF share of campus electricity as a number.
- AWS: any per-site metric.
- EU database: any per-facility record.

## Unit conventions in the CSV
- electricity_mwh = facility-level metered electricity for the calendar year (ORNL uses federal FY for
  the campus row; Microsoft uses FY Jul-Jun).
- water_m3 = withdrawal; water_consumption_m3 = withdrawal minus discharge (Google only);
  water_m3_peak_month = single peak month (NSA only, do not annualise).
- it_capacity_mw = stated capacity; check the note for whether it is IT, facility, or grid capacity.
- 1 US gal = 3.78541 L; 1 ML = 1,000 m3.
