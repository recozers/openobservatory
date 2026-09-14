# Regional electricity context

The [38-record register](../data/regional_dc_load.csv) covers the six B5 areas. It preserves the source's units, date precision, scope and status. **Every row is context only.** No regional figure changes a campus load, evidence kind, utilisation prior or confidence. This is a set of dated source snapshots, not a claim to have the latest figure for every publisher.

| Area | Selected reported figure | Meaning and limitation |
| --- | --- | --- |
| Dominion | 16,913 MW firm; 47,045 MW including engineering letters, July 2025 | Requested capacity in customer contracts; not power drawn. Three July snapshots, 2023–2025, retain component totals. [2025 IRP, Fig. 2.1.15](https://www.dominionenergy.com/-/media/content/about/our-company/irp/pdfs/2025-integrated-resource-plan-update.pdf#page=27) |
| AEP Ohio | 17,861 MW, 12 February 2026 | Binding DC contracts, including 5,642 MW under the new tariff; projects ramp through 2035. Ohio service territory, not the AEP group or whole state. [Utility update](https://www.aepohio.com/company/news/view?releaseID=10753) |
| ERCOT | Approximately 3,700 MW LFLs on the system, April 2025 report | Flexible loads, including co-located loads; exact observation date and instantaneous/nameplate basis unspecified. Does not identify cloud/AI demand. [Forecast, p7](https://www.ercot.com/files/docs/2025/04/08/ERCOT-2025-Long-Term-Load-Forecast-Report.pdf#page=7) |
| PJM | Up to approximately 30 GW DC growth, 2025–2030 | Forecast increment from the late-2025 evaluation. Not a 2030 total or observed annual average. [PJM year review](https://insidelines.pjm.com/2025-year-in-review-planning-prepares-for-burgeoning-electricity-demand/) |
| EirGrid | 959 MVA historical demand in 2024; 1,402 / 1,870 / 2,183 MVA in 2035 | Low/median/high alternatives for transmission and 110 kV DCs **plus new technology loads**. Smaller DCs are embedded in industry; Northern Ireland excluded. MVA is not MW. [AIRAA 2026–2035, Table 4.2](https://cms.eirgrid.ie/sites/default/files/publications/AIRAA-2026-2035_Ireland.pdf#page=52) |
| Ireland CSO | 6,973 GWh in 2024; 7,663 GWh in 2025 | Identified DC grid meters, with an annual history back to 2015. National statistics used only for testing/context. [2025 release, Table 1](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/keyfindings/) |
| Singapore EMA / IMDA | 58 TWh **all-sector** electricity in 2024; over 1.4 GW DC capacity in the 2024 roadmap | No DC-only annual energy total identified in the EMA chapter. IMDA capacity and its at-least-300-MW additional target are separate metrics. [EMA SES](https://www.ema.gov.sg/resources/singapore-energy-statistics/chapter3), [IMDA roadmap, p4](https://www.imda.gov.sg/-/media/imda/files/how-we-can-help/green-dc-roadmap/green-dc-roadmap.pdf#page=4) |

## Reading the register

`metric` distinguishes contracts, operational capacity, future increments, apparent demand and annual electricity. `qualifier` preserves approximate values and inequalities; 1.4 GW is a lower threshold, not an exact total. `component` distinguishes subtotals, and `scenario` distinguishes alternatives. `period_start/end` denotes the reported year or forecast span; a forecast's year boundaries do not imply a measured daily interval. `as_of` is a stated snapshot or data-freeze date. Blank dates mean the source did not supply an exact day; `source_vintage` still identifies the report. Retrieval date is separate.

Never sum this CSV. Dominion and AEP Ohio overlap PJM; contract components overlap their totals; annual snapshots repeat the same population; Ireland's two publishers cover different populations. Singapore's total electricity is not a data-centre total, and its capacity is not annual energy. Do not multiply a recycled percentage by a newer national denominator. ERCOT's flexible loads are a different category from its general large-load queue: [the February 2025 MORA](https://www.ercot.com/files/docs/2024/12/05/mora_february2025.pdf) identifies LFLs as crypto-mining facilities. No campus allocation follows from that category.

The PJM figure deliberately retains its historical vintage. The [14 January 2026 forecast explanation](https://insidelines.pjm.com/pjms-updated-20-year-forecast-continues-to-see-significant-long-term-load-growth/) describes revised near-term assumptions and includes voltage optimisation, port electrification and peak shaving among its adjustments. Its full-system peak or mixed adjustment total must not be relabelled DC demand.

EirGrid freezes inputs at 30 June 2025 and considers connected/contracted projects. The high-scenario growth column in Table 4.2 is 1,225 MVA while 2,183 minus 959 is 1,224; this apparent rounding discrepancy is not corrected by us. Only the table's reported demand totals are registered. CSO's release landing page and statistician text date publication to **7 July 2026**, although its key-findings/background header says 2025. The register preserves the 2026 vintage and records the conflict. CSO's [methodology](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/backgroundnotes/) uses ESB network meters, identifies DC activity through several searches, and allows revisions; it does not measure behind-meter self-generation. Rounded quarterly figures can differ from the annual total, so the published annual column is used directly.

## Testing the inventory's regional totals

Run the independent audit from the repository root:

```bash
python tools/regional_load.py --output data/regional_inventory_audit.json
python -m unittest discover -s tests -p 'test_regional_load.py' -v
```

The [saved audit](../data/regional_inventory_audit.json) joins the country-coded Irish inventory to **raw annual operator electricity disclosures** and the CSO annual series. It avoids rounded quarterly IT estimates, PUE assumptions, water-derived loads and capacity priors. In 2024 the only included campus is Clonee: 1,076,961 MWh disclosed facility electricity, against 6,973,000 MWh of national DC grid electricity (context ratio about 0.15445). This is an incomplete campus roster and the physical accounting boundaries differ. It is neither national coverage nor an accuracy score. The national 2024 annual average uses the actual leap-year 8,784 hours; the audit does not alter the existing disclosure-ingest convention.

Each year lists included inventory sites and inventory sites missing a disclosure. No 2025 disclosure is available in this checkout; it remains `null`, not zero. A synthetic reported zero stays zero. A facility sum exceeding the regional grid total raises a review flag, not a pass/fail scientific conclusion or automatic correction. Tests reject duplicate facility-years, nonfinite values and invalid units. Other regional rows return `not_comparable`: no verified utility-service membership or compatible observed energy metric exists in this audit. Being below a regional total does not validate the inventory.

Before extending the comparison, establish utility/ISO membership, observation period, IT versus facility versus grid boundary, and an independent campus roster with missingness. Do not select all sites in a state as a utility territory, silently carry disclosures forward, fill missing sites with zeros, sum alternative scenarios, or calibrate estimates to match an official total. No builder imports this register or audit.

## Source checks and refresh

All primary URLs were checked on 13 September 2026. Dominion and EirGrid numeric tables were extracted and visually checked; other values use identified source paragraphs/tables. The [source manifest](../data/regional_dc_load_sources.json) records hashes where actual source bodies were downloaded. ERCOT/PJM/EMA were readable through web retrieval but direct HTTP downloads were blocked or returned a challenge; they do not receive misleading source-body hashes. ERCOT's February 2026 queue graphic was not transcribed because direct retrieval and visual verification failed. The 2025 LFL report is retained with its own vintage.

To refresh, add a new dated row rather than overwrite a historical observation, retain report revisions explicitly, and rerun validation/audit. Review changes to population and metric before any comparison. Raw PDFs are kept in ignored local cache rather than duplicated in the repository; source URLs and PDF page locators allow retrieval.
