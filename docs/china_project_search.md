# Chinese project documents — search audit, 13 September 2026

The three provisional campus polygons still lack a matched regulatory IT-load figure. Provincial environmental and development/reform searches did find two useful power-infrastructure EIAs. Their locations do not justify assigning their figures to the existing parks. A1 separately removes the parks' misassigned Epoch capacities and imports Epoch's published locations.

`data/china_project_documents.json` records the documents, figures, original units, pages, coordinates, attribution decisions and all ten inventory notes. `python tools/china_project_notes.py` applies the notes idempotently. No load was added to `capacity_timeline.csv`: it requires MW, whereas the matched text gives kV and MVA for infrastructure, or planned annual consumption for a project without a matched parcel. Converting these into a campus operating load would manufacture evidence.

## Documents inspected

1. **Huawei Horinger Cloud Valley south area, phase 1, 220 kV substation.** Inner Mongolia environmental approval notice, 10 February 2025; the linked full EIA was downloaded, text-extracted, and PDF pages 14–15 visually checked. Page 14 places the substation at 111°51′12.252″ E, 40°32′32.862″ N. Page 15, table 2-2, specifies three 100 MVA transformers for this phase. This is apparent power and does not state IT load. The main text's eventual eight-transformer plan conflicts with a three-transformer statement in an appendix; retain the unambiguous current-phase count only. The substation is roughly 2 km east of Epoch's Huawei campus point and farther from the provisional `cn_horinger_cloud_valley` park. Treat it as a separate south-area project until its campus parcel is matched. Page 14 says the main data-centre project was exempted from environmental impact assessment under 呼环函〔2024〕375; the electrical substation still requires the radiation-category assessment. This can explain why searching for a campus EIA alone misses it.
2. **VNET Ulanqab cloud-computing base 110 kV supply lines.** Inner Mongolia EIA notice, 10 January 2025; full EIA downloaded and PDF page 29 (printed page 25) visually checked. It gives a terminal outside VNET's site at 113°18′47.341″ E, 40°58′56.255″ N. That is about 0.2 km from Epoch's VNET point, versus about 15 km from the provisional `cn_ulanqab_park`. Two 110 kV circuits connect upstream substations. Their transformer capacities are shared grid assets, not VNET's IT load. The line terminal is a useful location check, not a campus boundary.

The PDFs were inspected with `pdftotext -layout` and page rendering. File hashes in the registry identify the exact downloaded copies. Re-download URLs are retained instead of committing 45 MB of source PDFs. No rack count, generator count or operating IT MW was found in the inspected portions relevant to these projects; this is not a claim that no such filing exists.

## Search coverage and negative results

Searches used Chinese project/operator names plus 环境影响报告, 环评, 节能审查, 备案 and 土地, with `site:` restrictions to provincial environmental and development/reform domains. These are indexed-web searches, not a complete crawl of every provincial archive; unindexed attachments and municipal registers remain a limitation.

| Inventory sites | Provincial domains searched | Outcome |
|---|---|---|
| `cn_horinger_cloud_valley`, `helingeer_hub` | `sthjt.nmg.gov.cn`, `fgw.nmg.gov.cn` | Huawei south-area substation filing found; no IT MW matched to existing halls. A separate green-energy 110 kV step-up station also surfaced; generation infrastructure is not campus consumption. |
| `cn_ulanqab_park`, `ulanqab_hub` | `sthjt.nmg.gov.cn`, `fgw.nmg.gov.cn` | VNET supply-line filing found; terminal supports A1's separate Epoch location, not the provisional park. |
| `cn_zhangbei_alibaba`, `zhangbei_hub` | `hbepb.hebei.gov.cn`, `hbdrc.hebei.gov.cn` | No attributable filed IT MW found. Queried 阿里巴巴, 张北云联数据服务, 庙滩 and 小二台. A provincial industry article mentions a phase-two energy approval; the underlying approval was not retrieved. The MIIT green-data-centre case study is not an energy-review filing and is not promoted to A1. |
| `zhongwei_hub` | `sthjt.nx.gov.cn`, `fzggw.nx.gov.cn` | Named Zhongjin Xuanhe 330 kV supply-project EIA lead and grid-connection approval found; neither identifies a boundary/load for the generic hub centroid. |
| `guian_hub` | `sthj.guizhou.gov.cn`, `fgw.guizhou.gov.cn` | Huawei AZ3 Machang and A4 substation EIA leads found. Full PDFs not inspected in this audit; no figures imported. |
| `qingyang_hub` | `sthj.gansu.gov.cn`, `fzgg.gansu.gov.cn` | No attributable campus energy-review/EIA figure found in returned indexed results. |
| `chongqing_hub` | `sthjj.cq.gov.cn`, `fzggw.cq.gov.cn` | Energy reviews for Shenzhen Benmao's Chongqing computing centre and GDS Chongqing found, but parcels not matched to this centroid. Planned annual consumption does not establish measured current use. |

Primary leads, including the Chongqing energy reviews, are in the registry with their inspection status. No numerical figure from an uninspected PDF is used. Hub centroids remain hub centroids; a province-wide plan, company-wide number, grid transformer or nearby power plant cannot establish a campus load.

## Validation

All ten target IDs receive a dated, sourced note. The notes script makes no capacity or geometry changes and repeated application produces identical bytes. All three site build scripts run using the saved observations. A2 meets its explicit negative-search alternative for the three provisional campuses; it does not establish their filed IT loads. The next useful step is municipal parcel/permit matching at the newly located Epoch campuses, with the substation and line coordinates as leads.
