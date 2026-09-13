# Optical construction discovery

`tools/s2_candidates.py` scans a 12 km box without using known hall polygons as a mask. The stored halls are used only afterwards to measure campus recovery. Run one site per process for `stargate_abilene`, `rainier_in`, `prometheus_oh`, `ulanqab_hub` and `zhangbei_hub`.

Cloud-masked Sentinel-2 surface-reflectance medians are compared with 2022. Each year uses 1 January–13 September, matching the available part of 2026 rather than comparing different seasons. Three indices are reduced to 50 m before local connected-component extraction: visible brightness, NDVI and NDBI. A pixel must lose at least 0.15 NDVI, end below 0.25 NDVI, and gain at least 0.08 brightness or 0.10 NDBI. Eight-connected components must cover at least 3 ha with area/minimum-rotated-rectangle area at least 0.6. Thresholds were fixed before the five-box run, not fitted to its labels.

The scan downloads bounded raster tiles instead of vector feature collections. A full Zhangbei tile timed out, so downloads now split into four 6 km pieces, validate each GeoTIFF, resume completed pieces, and mosaic them before component extraction. The four earlier boxes retain their equivalent cached 12 km downloads. A 12 km box has approximately 240 × 240 analysis pixels. Cached GeoTIFFs are keyed to the region, years, season and version. Metadata records the index-file SHA256 and exact rule. Candidate CSVs, geographic component outlines, metadata and an annotated RGB chip for every candidate are committed under `results_discovery/`. Red outlines are 50 m change components, not individual hall boundaries; their confidence is low. RGB chips are 20 m composites enlarged for inspection, so enlargement adds no detail.

## US validation

| Box | Candidates | Known campus recovered | Overlapping candidate ranks |
|---|---:|---|---|
| Abilene | 6 | yes | 1, 2 |
| Rainier | 4 | yes | 1, 2 |
| Prometheus | 13 | yes | 8 |

Campus recall is **3/3** under the predefined test: at least one candidate intersects an independently stored hall polygon. This is not per-hall recall and is not a global classifier validation. Components often include yards, access roads and bare ground; their area is not roof area.

Visual review of all 23 US chips finds 11 obvious non-hall components: Abilene ranks 3–6 (bright pads, cleared ground and a small ancillary patch), Rainier rank 4 (a long yard), and Prometheus ranks 3, 6, 9–12 (pads, clearing and yards). That is a **48% non-hall detection rate in this reviewed sample**. Five components overlap the known target campuses. Seven other roof or mixed industrial components remain unattributed; they could include other data centres and are not asserted false solely because they miss the target polygons. Thus these chips demonstrate a candidate generator with substantial review burden, not automatic operator attribution.

The Chinese boxes produced **six Ulanqab candidates and one Zhangbei candidate**, each with an annotated chip. `results_discovery/visual_review.csv` records review of all 30 candidates across the five boxes. No Chinese operator identity is established. The Chinese lists remain attribution review queues. Their hub-centred boxes do not encompass every park in each region. No new capacity, operator identity or public inventory row is derived from a candidate alone. The Ulanqab chips show a mixture of ordinary industrial/urban roofs and construction, without enough evidence to assign an operator. The separate review table records the final inspected candidates and limitations.

## Dates and limits

`first_change_year` is the first sampled year in which at least half of the final component's pixels meet the rule against 2022. It is a coarse substantial-change date, not groundbreaking, membrane completion or commissioning. Bright soil and non-data-centre industrial development pass the rule. Dark roofs can fail it, and solar/seasonal changes can mimic construction. The scan does not resolve the failed dark-roof timing test in A3.

The upper-priority confirmation workflow for radar/night-light candidates is now feasible using these bounded tiles, but has not been validated by this five-box run. A8/A9's broader radar inventory and manual classification remain separate follow-on tasks.
