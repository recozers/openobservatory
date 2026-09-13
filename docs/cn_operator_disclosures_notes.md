# Chinese data-centre operator disclosures for the 东数西算 hubs — what exists, what does not

Companion to `data/cn_operator_disclosures.csv` (81 rows, 2026-09-13). Every row carries a URL that was fetched and read
during this pass; where a figure appeared only in a search snippet it is flagged "unverified" in the note column and is
not given its own row. Time-boxed to ~30 minutes, so this is a first sweep, not an exhaustive filing review.

## 1. Headline finding

**No listed operator discloses capacity or utilisation at the level of an individual 东数西算 campus.**
The three US-listed colocation operators (VNET, GDS, Chindata) report company-wide MW / sqm and utilisation each quarter;
the three telcos report company-wide rack counts once a year; the hyperscalers (Alibaba, Tencent, Huawei) report PUE and
clean-energy shares but no capacity. Campus-level numbers exist only in (a) operator press releases at ground-breaking or
opening (design capacity, servers "planned"), and (b) park administrative-committee statements republished by press
(built racks, in-service racks, 上架率) — i.e. exactly the government-origin statistics this project treats as untested.

## 2. What each operator discloses

| Operator | Granularity | Frequency / since | Metrics | Hub campuses named |
|---|---|---|---|---|
| **VNET** (NASDAQ: VNET) | Company-wide, split wholesale vs retail | Quarterly (6-K press release) since wholesale segment introduced ~2021; 20-F annually | Wholesale: capacity in service / committed / utilized / under construction / pre-committed (MW), utilization %, mature vs ramp-up utilization. Retail: cabinets in service, utilized, MRR/cabinet | Ulanqab appears only in narrative (order wins, near-zero-carbon demo project). The FY2025 20-F contains zero occurrences of "Ulanqab"; owned-building floor area (1,049,009 sqm) lists Inner Mongolia and Hebei among nine provinces but is not split |
| **GDS** (NASDAQ: GDS) | Company-wide China | Quarterly since IPO (2016) | Area in service / committed / utilized / under construction (sqm), utilization %, commitment and pre-commitment rates. No MW | 20-F FY2025 names "new growth markets" Inner Mongolia, Ningxia, Shaoguan and three Zhangjiakou DCs; "Ulanqab" not in 20-F. Chinese-site press release (2023-07) gives Ulanqab phase 1 land (125 mu) and gross building area (~110,000 sqm), no MW |
| **Chindata** (NASDAQ: CD, private since 2023) | Company-wide + region (Greater Beijing / Malaysia-India / YRD / GBA) | Quarterly 2020–Q2 2023; 20-F FY2020–FY2022 | Capacity in service / under construction / utilized (MW), utilization %, contracted+IoI ratio | Best campus granularity of any filer: 20-F FY2022 gives Zhangjiakou total capacity 324 MW, Datong 308 MW, Qingyang 150 MW planned; Q2 2023 release gives Huailai ">300 MW operational". Nothing after Aug 2023 |
| **Sinnet** 光环新网 (SZ: 300383) | Per site, by design cabinets (4.4 kW equiv.) | Semi-annual + annual (Chinese) | Cabinets in operation (92,000 at 2026-06-30), planned cabinets per site; utilisation only qualitatively | **None in a hub cluster.** Sites are Beijing, Yanjiao (Hebei, Langfang), Tianjin, Shanghai, Hangzhou, Changsha. Only "expansion plans" in Inner Mongolia / Hainan / Malaysia. Sinnet runs AWS China (Beijing); the Zhongwei AWS region is run by NWCD 西云数据 (private, no filings; site returned 403) |
| **Alibaba** | None for capacity | ESG report annual (FY2025 PUE 1.190 fleet-wide per search snippet, not fetched) | PUE, clean-electricity share, heat recovery | Zhangbei: design PUE 1.25 (2016 company blog); 380,000+ servers, 7 projects, 1,647 mu (Xinhua press 2021) |
| **Tencent** | None for capacity | ESG annual; press | Fleet PUE <=1.25; servers "planned" per campus | Gui'an Qixing 300,000 servers planned; Chongqing 100k+200k; Huailai 2×>300k (press quoting Tencent) |
| **Huawei Cloud** | None | Press at opening | Servers planned, PUE | Gui'an: >1 m servers planned, PUE 1.12 (2021); phase 1 ~480,000 sqm (IDC圈 compilation) |
| **China Mobile** (600941) | Company-wide | Annual report | 对外服务IDC标准机架 150.4万 (2.5 kW equiv.), AI EFLOPS | Says it is "accelerating resource planning in Inner Mongolia, Ningxia, Gansu, Guizhou hub nodes" — no per-hub racks |
| **China Unicom** (600050) | Company-wide | Annual report | >1.1 m racks, 7 hundred-MW AIDC parks, cabinet utilisation >72% | "Large parks cover the eight national hubs" — no split |
| **China Telecom** (601728) | Company-wide | Annual report | Rack power >3.2 GW, AIDC revenue; also quotes MIIT's 938,000-rack figure for the three telcos | No split; the full H-share PDF download failed (only the A-share summary was read) |

## 3. Hub-by-hub: what was found

**Inner Mongolia — Ulanqab (VNET, GDS, Alibaba, Huawei, Apple, Kuaishou).** Company filings: none campus-specific.
VNET group wholesale: 889 MW in service / 70.1% utilised (2025-12-31, 20-F); 1,007 MW / 73.9% (2026-06-30, 6-K);
573 MW / 437 MW utilised (2025-03-31). GDS Ulanqab phase 1: 125 mu, ~110,000 sqm gross, delivery by 2025 (company PR).
Municipal statistics via IDC圈: 260,000 racks built, 190,000 in operation, 73% 上架率 (2024); 173,000 built / 62% (2023);
signed racks >1.05 m (May 2024) and >5 m, 172,000 P in operation (Aug 2026, 科技日报).

**Inner Mongolia — Horinger cloud valley.** Park targets (2025): 600,000 racks, 3 m servers, 84,000 P; end-2024 44,500 P
(park committee via press). China Telecom Inner Mongolia Information Park: ~50,000 racks built, >RMB 4 bn invested,
1.14 EFLOPS (China News Service, May 2025). China Mobile Hohhot AI centre: 6.7 EFLOPS, RMB 4.66 bn, PUE 1.24 (press,
Apr 2024). Huawei Cloud Horinger: "3 m+ servers capacity" (park statement) — no operator figure.

**Beijing-Tianjin-Hebei — Zhangjiakou (Alibaba Zhangbei; Chindata & Tencent Huailai).** Chindata FY2022 20-F: 324 MW
total capacity in Zhangjiakou; Q2 2023: >300 MW operational in Huailai, Greater Beijing 489 MW utilised of 722 MW.
Alibaba Zhangbei: 380,000+ servers, 5 projects live + 2 building, >50% wind/solar (Xinhua press 2021); no Alibaba filing
gives racks/MW. Tencent Huailai: 2 sites × >300,000 servers planned.

**Guizhou — Gui'an.** Park committee (China Daily, Aug 2023): 21 DCs, 450,000 racks planned, 4.29 m servers planned,
645,000 servers operational (~15% of plan); 23 DCs and 53 EFLOPS by end-2024. Per-operator planned scale (IDC圈
compilation, Jun 2023): China Telecom 50,000 racks / 340,000 sqm; China Unicom 72,000 racks / 320,000 sqm; China Mobile
20,000+ racks; Huawei 1 m servers / 480,000 sqm; Tencent Qixing 300,000 servers planned; Apple/GCBD USD 1 bn, 2,500 mu
(park site, 2019). No utilisation for any Gui'an campus from any source.

**Ningxia — Zhongwei.** Securities Times (Mar 2025): China Mobile phase 1 55,000 racks planned, ~20,000 in production,
>99.8% 上架率; phase 2 150,000+ racks planned; China Unicom 120,000 cabinets / 310 MW IT planned; 13 DC enterprises,
8 parks operating. Meiligo (000815) 2025 annual report (via press): buildings E1/E3/C1 delivered, B1/B3/C3 civil works
done, IDC revenue RMB 324 m; rack count / >70% 上架率 seen only in snippets (unverified). AWS/NWCD: nothing fetched.

**Chengdu-Chongqing — Shuitu.** Chongqing government portal (May 2024): Shuitu data port 32,000 racks / 480,000 servers;
China Mobile Chongqing ~13,000 racks / 130,000 servers. Liangjiang Cloud Computing DC phase 2: 2,112 racks commissioned
Oct 2024. Tencent Chongqing: 100,000 servers (phase 1) + 200,000 (phase 2). GDS has Chongqing DCs but its 20-F gives
no site figures.

**Gansu — Qingyang.** People's Daily (Jan 2025, quoting park committee director and China Mobile / China Telecom Qingyang
deputy GMs): 31,000 racks in operation, >51,000 PFLOPS, 6 AI centres operating + 10 under construction; China Telecom
>30,000 PFLOPS on its platform. Chindata planned 150 MW campus (20-F FY2022). Gansu Daily China Mobile figures are
ambiguous in extraction (low confidence).

## 4. What could not be found (in this pass)

- Any operator-reported MW, racks or utilisation for: VNET Ulanqab; GDS Ulanqab (beyond land/gross area) or GDS Chongqing;
  Alibaba Zhangbei; Tencent Gui'an/Chongqing/Huailai (servers "planned" only); Huawei Gui'an/Horinger/Ulanqab in-service;
  Apple/GCBD Gui'an; AWS/NWCD Zhongwei; any telco per-hub rack count.
- VNET Q4 2024 6-K (486 MW / 353 MW utilised / 73%, Ulanqab 235 MW orders and 100 MW framework with 28 MW in 4Q25):
  ir.vnet.com timed out twice and the PRNewswire URL 404'd — figures above come from search snippets only (unverified).
- Meiligo 2025 annual report PDF itself (cninfo) — not fetched; NWCD "about" page — 403; DTDATA Zhongwei stats — 522;
  Horinger "5 centres lit" (Zhihu) — 403; Gui'an ce.cn 2025 piece (25 DCs / 1.4 m racks planned) — 504;
  guizhou.gov.cn Huawei page — failed; China Telecom full H-share annual report — download failed.
- Chindata 20-F FY2022 per-data-centre table (CN01…CN23) — the text is in the downloaded file
  (scratchpad `cd20f.txt`) but was not parsed in the time available; worth a follow-up since it is the only filing with
  per-campus MW in a hub cluster.
- EDGAR full-text search for "Ulanqab" across all 20-F/6-K (would catch VNET 6-K order announcements) — not run.

## 5. Caveats on interpretation

- "Racks" are not comparable across sources: Sinnet uses 4.4 kW equivalents, China Mobile 2.5 kW equivalents, park
  statistics rarely say. Convert to MW only with the stated per-rack power.
- "Servers planned" (Tencent/Huawei/Alibaba press) is design ambition, not installed base; the only in-service server
  counts are park self-reports (Gui'an 645,000 in 2023; Alibaba Zhangbei 380,000+ via Xinhua 2021).
- Park-committee 上架率 (Ulanqab 73%, China Mobile Zhongwei 99.8%) are self-reports with no stated denominator
  definition; treat as untested inputs alongside official statistics, not as validation.
- SEC filings require a declared User-Agent for bulk download; WebFetch truncates them — download and grep locally.
