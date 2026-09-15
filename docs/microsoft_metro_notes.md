# Microsoft's FY25 metro table and the inventory (RFW-19)

Companion to `data/microsoft_metro_fy25.csv` and the 29 `microsoft_<metro>` rows in `data/operator_disclosures.csv`, written by
`tools/microsoft_metro_table.py` from Table 15 of Microsoft's 2026 Environmental Data Fact Sheet (p. 25, footnotes p. 26;
SHA-256 `0fd18083…a197f6`). Source:
https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/msc/documents/presentations/CSR/2026-Microsoft-Environmental-Data-Fact-Sheet-PDF.pdf

## What the table is

- Period: Microsoft fiscal year FY25, 1 July 2024 to 30 June 2025. Not a calendar year, so it cannot be compared with Meta's or
  Google's calendar-year figures without noting the six-month offset.
- Boundary: Microsoft-owned datacenters under Microsoft operational control. Leased capacity, commissioning activity and
  metros under 1 % of the owned total are excluded. Electricity is primary data where available, otherwise estimated from
  capacity (footnote 8).
- Unit of place: a metropolitan area, "city or regional cluster", not a campus. 29 metros; 15,931,489 MWh in total, an
  average of 1,819 MW. Water withdrawal per metro is also given, with the non-potable share where any, and replenishment.
- Table 13 gives company-wide electricity of 37,026,353 MWh in FY25, so the 29 owned-datacenter metros are 43 % of it;
  the rest is leased datacenters, metros under the 1 % cut and offices.

## Metro rows against the inventory

| Metro | FY25 MWh | Average MW | Water ML | Inventory campuses in the metro | Decision |
|---|---|---|---|---|---|
| Phoenix (AZ) | 954,206 | 109 | 981 | epoch_microsoft_goodyear | context: several Microsoft campuses (Goodyear, El Mirage and others); an upper bound for Goodyear |
| San Antonio (TX) | 1,440,710 | 164 | 420 | epoch_microsoft_sat14, epoch_microsoft_sat40 | context: SAT14, SAT40 and the older Westover Hills campus; an upper bound for either |
| Des Moines (IA) | 2,152,335 | 246 | 264 | epoch_microsoft_project_osmium | context: several West Des Moines campuses; an upper bound for Osmium |
| Atlanta (GA) | 11,718 | 1.3 | 19 | epoch_microsoft_fairwater_atlanta | context: Fairwater Atlanta started in October 2025, after FY25; this is other Atlanta capacity |
| Chicago (IL) | 369,328 | 42 | 204 | none (Fairwater WI is 100 km north, not operating in FY25) | context |
| Boydton (VA) | 3,113,847 | 355 | 362 | none | context: effectively one campus, the largest row; a candidate site for RFW-18 |
| Cheyenne (WY) | 1,091,460 | 125 | 188 | none Microsoft (Meta Cheyenne and the Project Jade watch are separate) | context |
| Quincy (WA) | 1,381,569 | 158 | 1,292 | none | context: Microsoft's Quincy cluster of several campuses |
| Dublin (Ireland) | 1,308,581 | 149 | 18 | none Microsoft in the inventory | context; a test point for Ireland's official total in `data/regional_dc_load.csv` |
| Ashburn (VA) | 828,925 | 95 | 239 | none | context: several sites in Loudoun County |
| Hollands Kroon (NL) | 1,291,170 | 147 | 46 | none | context |
| Gävle–Sandviken (SE) | 704,549 | 80 | 14 | none | context |
| 17 others | 1,283,091 together | 146 | | none | context |

No metro figure is attributed to an inventory campus. Every metro that holds one (Phoenix, San Antonio, Des Moines, Atlanta)
holds several Microsoft campuses, or the campus was not operating in FY25, so the metro total is at best an upper bound and
never the campus's load. The rows therefore stay outside `data/sites.csv`; `tools/ingest_disclosures.py` lists them as
"disclosed but not in the inventory" and nothing on the public site changes.

## What would turn context into a campus figure

- **Boydton (VA)** is one campus and 355 MW average over FY25, larger than any measured campus on the site. Adding it under
  RFW-18 needs sourced coordinates and hall polygons; then the row becomes the campus's FY25 load with a fiscal-year note.
- **East Wenatchee (WA)** and **Cheyenne (WY)** may each be one Microsoft campus; that has not been checked here.
- **Goodyear, SAT14/SAT40, Osmium**: only a per-campus disclosure (none exists) or a metro with one campus would do. Dividing a
  metro total between campuses by capacity would be a model, not a measurement, and is not done.

## Consistency checks

The water withdrawal per metro parsed here equals, for all 29 metros, the figure in `data/water_derived_loads.csv`, which was
extracted separately on 13 September; the "Olympic pools" column equals withdrawal / 2.5 ML within one pool for every row,
which is how the parser tells the optional non-potable and replenishment columns apart. `tests/test_microsoft_metros.py`
holds these checks and the 29-row totals.
