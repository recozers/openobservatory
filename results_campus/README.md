# Campus detector prototype (2-hour sprint, 13 Sep 2026)

Goal: find data-centre campuses in satellite data (inventory layer), tested on the 东数西算 hubs.
Features: Google satellite embeddings (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL, 2024), mean over 50 m / 250 m / 700 m buffers per building.

Data assembled
- osm_datacenters_geom.json: 2,115 OSM-tagged data-centre buildings worldwide with footprints (1,611 >= 0.7 ha)
- osm_large_roofs_neg.json: 1,171 warehouse/factory roofs >= 1 ha from ten metros (US, EU, CN)
- hub_buildings.json: 603 mapped buildings >= 0.5 ha in the Ulanqab, Zhangbei, Helingeer and Gui'an hub boxes
- data/epoch/*.csv: Epoch AI data-centre tables (86 sites, timelines, chip counts, chillers, cooling towers)
- train_features.csv, large_dc_features.csv: extracted features

Results
- In-domain: large tagged data centres vs metro large roofs, region-grouped CV AUC 0.82 (China-only 0.85); the study campuses rank at 0.9.
- Roof-scale features carry the signal; 700 m campus-context similarity does NOT separate data centres from industrial parks.
- Region scan: FAILS. Raster scan hits Earth Engine's interactive memory cap (needs batch export). Object scan suffers domain shift:
  in steppe/small-town settings the top picks are town centres, a cemetery, a temple (see chips/ulanqab_top.png, chips/zhangbei_top.png).
  Adding hub buildings as presumed negatives (v3) did not fix it (AUC 0.56).
- What would: hard negatives from rural/small-town China at scale, a size prior (>= 2 ha halls, rows of identical halls),
  batch-exported score rasters, and verification against the three Epoch-listed Chinese campuses (VNET Ulanqab, Huawei Horinger, Alibaba Zhangbei).

Also working from this sprint: Sentinel-2 roof-dating per hall (see docs/overnight_report_2026-09-13.md discussion; Abilene roof dates corrected by 5-10 months).
