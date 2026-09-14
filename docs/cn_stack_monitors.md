# China plant links and public stack monitors (B8)

Audit date: **14 September 2026**. Branch: `astra/b8`, based on integrated main `5000633`.

The first pass covers all **eleven requested hubs**, with fourteen link/lead records and nine regional access outcomes.
It establishes park energy connections for **Shengle (Horinger)** and an operator-described **Liangjiang cooling link
(Chongqing Shuitu)**, but no exclusive electrical allocation. Four other records concern renewable supply. Nearby thermal
plants, grid substations and virtual power plants must not be mistaken for dedicated campus combustion sources.

**Hourly/daily acceptance remains unmet.** Shengle's public reading request requires a CAPTCHA; other candidate provincial
endpoints timed out or returned errors. Seven annual Shengle reports were downloadable: **63 annual emission-mass records**
are retained with eight primary PDFs, including its monitoring plan. Annual totals do not replace the requested hourly series.
No builder, site inventory, capacity, load or evidence-kind output consumes this audit.

Start with `data/cn_plant_links.csv`, `data/cn_stack_monitor_platforms.csv`, and `data/cn_stack_monitors/README.md`.
`data/cn_stack_monitor_sources.json` records the actual HTTP outcomes, hashes and retained files. An HTTP 200 app shell or
error message is not evidence of public readings. Search-index evidence is explicitly distinguished from fetched documents.

## Hub findings

| Hub | Candidate or supply arrangement | What the source establishes; what remains unknown |
|---|---|---|
| Ulanqab | Zhongjin wind/solar/storage; nearby Jingning and Huaning thermal plants | [Energy Bureau approval](https://nyj.nmg.gov.cn/tzgg/202404/t20240409_2491156.html), 8 April 2024 I(a), names 200 MW wind and 100 MW solar for Zhongjin's load. No combustion stack. Public provincial enterprise search verifies Jingning/Huaning identities but supplies no DC allocation. |
| Horinger | Inner Mongolia Jingneng Shengle, 2 × 350 MW coal CHP | [2025 company monitoring report](https://sthjt.nmg.gov.cn/qyzxjc/PollutionMonitor/publishDownFile.action?fileId=402861b59babb33a019bb04463b53c26), pp2-4: cloud-park support and surrounding heat/electricity/cooling supply. [2016 transaction filing](https://static.cninfo.com.cn/finalpage/2016-06-27/1202409707.PDF), p119: earlier customer revenue is heat sales; electricity planned to be sold to Mengxi grid. Not a dedicated electricity meter. |
| Zhangbei | Renewable direct-supply proposals; no dedicated combustion plant verified | [Provincial cluster plan](https://he.spb.gov.cn/hbsyzglj/c100756/c100761/202301/a4d2168913aa4dbabe461202d0ededd4.shtml), II(a)/III(a), names Zhangbei parks and renewable supply measures. This is a plan, not a physical thermal allocation. |
| Zhongwei | China Mobile PV/storage/distribution grid; nearby Guoneng Zhongwei thermal plant | [Energy regulator notice](https://xbj.nea.gov.cn/dtyw/hyxx/202606/t20260626_303639.html), 26 June 2026, describes PV priority supply. [Thermal operator tender](https://www.chnenergybidding.com.cn/bidweb/001/001002/001002002/20260709/0d5acb92-2566-4125-9547-c08f1a1ce9c2.html), 9 July 2026 §2.1.1, describes grid dispatch and market participation. No DC electrical dedication established. |
| Qingyang | Green-power aggregation project | [City notice](https://zgqingyang.gov.cn/zw/bmdt/content_343777) is indexed as first units connected 30 January 2026; direct download returned 403. [Owner's SASAC account](https://wap.sasac.gov.cn/n2588025/n2588129/c35451088/content.html) also indexed but failed TLS locally. Provisional renewable lead; full project filing and any dedicated thermal plant remain unverified. |
| Gui'an | Regional grid/substations | [Guizhou Energy Bureau](https://nyj.guizhou.gov.cn/ztzl/zsyz/201908/t20190805_28839775.html), 5 August 2019, describes substation planning for Huawei/Tencent/Apple. A [Huawei A4 substation EIA](https://sthj.guizhou.gov.cn/zwgk/zdlyxx/fsjg/fslxmspqgs/202405/P020240515682131370766.pdf) was indexed but direct download timed out. No combustion plant dedication verified. |
| Chongqing Shuitu | Huaneng Liangjiang gas CHP → Huaqing cooling station → China Telecom | [China Telecom's account](https://www.chinatelecom.com.cn/ct/news/yunjisuanjisuanli/154820.html), 21 June 2022, describes waste steam/industrial cooling water and indirect campus heat exchange. Search index supplied the text; direct request returned 412 and the EIA was unavailable. Cooling linkage does not establish electricity share. |
| Tianfu | No dedicated combustion plant verified | [Sichuan action plan](https://new.tzxm.gov.cn/zckd/fzgh/202411/t20241122_1394663.shtml), II(1), II(15-17), supports renewable aggregation and the Tianfu cluster, without naming an attributable thermal source. |
| Wuhu | Virtual power plant/flexible demand | [City SASAC operator report](https://gzw.wuhu.gov.cn/xwzx/gzyw/8927779.html), 9 May 2026, describes demand response and proposed expansion of DC participation. A virtual power plant is not a combustion generator. |
| Shaoguan | GDS grid-connection project at 220 kV Tanjie substation | [EIA acceptance](https://www.sg.gov.cn/zw/zdlyxxgk/dzjg/sgssthjj/hjbhxxgk/jsxmhjyxpjxx/content/post_2855829.html), 12 June 2026, names Guangdong Power Grid's works inside the substation. No power generator specified in the acceptance table. |
| Zhangjiakou/Huailai | Hoyinn aggregate wind/solar supply | [Operator-submitted NDA case](https://www.nda.gov.cn/sjj/zhuanti/ztdsjblh/ztxwfb/0924/20240924133430913242032_pc.html), 23 September 2024, describes nine wind/solar farms about 150 km away across three counties. Those are not campus combustion stacks. |

These are bounded search findings, not proof that no further plants exist. Search terms combined each hub with 数据中心,
电厂, 自备电厂, 热电联产, 环评, 源网荷储, 绿电直供 and provincial 自行监测/自动监测. Searches covered public regulatory,
park, utility and operator sources. The CSV preserves unverified leads rather than assigning them to low-confidence hall polygons.
The four renewable rows are Ulanqab Zhongjin, Zhongwei Mobile, Qingyang aggregation and Huailai Hoyinn. No source determines
physical attribution to each of the radar-discovered unconfirmed halls.

## Shengle: working public documents, protected time series

The [public enterprise page](https://sthjt.nmg.gov.cn/qyzxjc/PollutionMonitor/publishEnterpriseInfo.action?back=list&ID=B91752F8E785428E8900B78EA180D9AC)
identifies enterprise `B91752F8E785428E8900B78EA180D9AC`, social credit `91150100053932362B`. Its 2026 plan, p3,
reports 111°51′51.01″ E, 40°33′40.00″ N. These are company-reported coordinates; datum is unstated, and they are not new
campus polygons. The same name lookup distinguishes Jingning `80B48D912F8A47A3BFAE4D0E48F28B77` and Huaning `247112141339328`.

The 2025 report p4 describes hourly SO2, NOx and particulate monitoring at **#1/#2 desulfurisation total outlets**
(`#1、#2脱硫总排口`). The 2026 plan uses labels `废气监测点1` and `废气监测点2`, and contains a separate manual-monitor schedule.
Those labels are retained without inventing `DA001`/`DA002` or database outlet IDs. The report's broad compliance limits
and its tighter ultra-low-emissions claims are distinct; neither is an operating emission factor.

The automatic-data UI offers years 2019 through the current year; its legacy tab offers 2015-2018. These are **selector
ranges, not verified record coverage**. A single August 2026 request returned HTTP 200 with `result:false` and
`验证码不能为空！` (verification code cannot be empty). Collection stopped at the CAPTCHA. No automatic samples or
flue-gas flow readings were acquired. The annual report's assertion of 100% disclosure does not demonstrate unattended access.

Public document lists contain seventeen plan revisions and eight annual listings for 2018-2025. The 2018 download returns
an HTML “file does not exist (not yet synchronised)” message. The seven other annual PDFs and the latest listed stamped
2026 plan downloaded successfully. The plan was uploaded in July 2026 but its cover is dated 9 January 2026.

The saved annual files preserve SO2/NOx/particulate emissions for each of the two units and the reported plant total, in
**metric tonnes**. They are not interval means, do not include MWh, and are not assigned to a data centre. The 2023 PDF is
scanned; section V on physical p15 was visually transcribed. The 2024 source itself has an arithmetic discrepancy:
282.47 + 319.13 = 601.60 t NOx, while it prints 606.6 t. All three values remain with `source_total_mismatch`.
Twenty of twenty-one plant-year-pollutant totals reconcile; the one mismatch is flagged and visually confirmed on p19.
The 2019 listing has an anomalous “测试” in its title; retain that warning despite the normal company/year title inside.

## Provincial access audit

| Region | Observed outcome on 14 September 2026 |
|---|---|
| Inner Mongolia | Public enterprise metadata and documents work. Automatic-reading endpoint requires CAPTCHA. |
| Hebei | `http://111.62.218.180:9920/` timed out. Current retention and outlet IDs unverified. |
| Ningxia | Current department homepage links `https://222.75.41.50:30000/xxgk/`; that endpoint timed out. |
| Gansu | Directory's public map route returned HTTP 404; department homepage returned HTTP 412. |
| Chongqing | Directory's port-20003 public enterprise route and department homepage timed out. |
| Anhui | Operator-disclosed port-8081 automatic platform timed out; national public route returned a JavaScript app shell. |
| Sichuan | Historical operator-disclosed port-6666 endpoint timed out. National province view not inspected. |
| Guizhou | Current operator disclosure links national province route `520000`; province view not inspected. No verified hourly access. |
| Guangdong | Current [department page](https://gdee.gd.gov.cn/wryml/content/post_3841259.html) links national province route `440000`. Browser rendered public search and an initially empty company list. No province-wide absence inferred. |

The national `/hb/home` route redirected in the browser to login; `/gkpt/mainZxjc/<province>` is the public app and must
not be confused with it. A dated [independent platform audit](https://www.epmap.org/selfmonitorplatform) and the
[2024 endpoint directory](https://cloud.heimalanshi.com/Uploads/pecc/File/202502/10/173915716423/%E5%8D%81%E5%B9%B4%E5%9C%A8%E7%BA%BF%E7%9B%91%E6%B5%8B%E4%BF%A1%E6%81%AF%E5%85%AC%E5%BC%80%EF%BC%8C%E5%85%B1%E7%BB%98%E7%A2%A7%E6%B0%B4%E8%93%9D%E5%A4%A9.pdf)
(pp60-61) were used for discovery. Their historical closure/retention claims are not current tests. Timeouts here can be
network-specific; they do not prove that residents cannot access the services. No login, paywall or CAPTCHA was bypassed.

## Reproduce and continue

Run `python tools/cn_stack_monitors.py` for the saved-data audit. The CSV source URLs point directly to the original annual
PDFs; retained source hashes enable offline review. The source manifest also records failed requests, but failed HTML,
third-party directories and session-bearing public shells remain in the ignored research cache.

For a permitted manual portal session, use the public page's normal workflow:

1. Search company names on `publish.action`. The page calls `publishEnterpriseList.action` with page/rows/SHI/XIAN/QYMC.
2. Use the returned enterprise ID in `publishEnterpriseInfo.action?back=list&ID=...`; tabs 20/30/40/60/900 are monitoring
   plan, automatic readings, manual readings, annual reports and legacy readings respectively.
3. Public document lists call `publishJCFAlist.action` or `publishNDBGlist.action` with that ID; their returned `fileId`
   or `FILE_ID` selects `publishDownFile.action`. Use the page's current session and CSRF token; never publish the token.
4. The automatic tab calls `publishZXJGlist.action` with enterprise ID and page size 30, plus `lX=FQ`, year, month and
   optional outlet/pollutant filters. It demands its normal CAPTCHA. This audit does not implement CAPTCHA handling.

Remaining work: obtain normal public hourly/daily exports for Shengle and accessible Liangjiang outlets; verify actual
retention, database outlet IDs, flow units and wet/dry/standard/oxygen correction; find additional dedicated-plant filings.
Preserve quality flags and missing records. Manual spot samples must not be called daily averages. Corrected concentration
cannot simply be multiplied by unmatched actual-volume flow. Plant emissions require both a valid generation conversion
and an independently documented supply allocation before any campus electricity inference.
