# Log

Dated entries by either agent: what was done, what was found, what could not be done.

## 2026-09-13 (Claude)
- Initial public release; docs/ASTRA_TODO.md written for the second agent.

## 2026-09-13 (Astra, A1 — Epoch inventory)
- Worked in a separate clone of recozers/openobservatory, branch `astra/a1-epoch-inventory`. The original workspace points to recozers/Meridian and was left untouched; no Claude research files were changed.
- Accounted for all 86 Epoch records: seven existing curated matches, 78 new sites with 264 hall polygons, and one location-only record (Stargate New Mexico, capacity unassigned/tier U because no polygon is available). There are 103 non-control public status entries.
- The brief missed the public Epoch map's explicit Building annotations and coordinates (85/86 sites). Preserved a CC BY 4.0 source snapshot and used those annotations instead of treating large nearby OSM buildings as halls. Geocoding is cached, serial and rate-limited: 23 new entries have corroborated address-quality coordinates; 56 use Epoch's published coordinates. No hall polygons overlap another inventory site's halls by more than 10% of the smaller polygon.
- Preserved 996 normalized dated capacity rows across both bases. `it_reported` is not measured HPL power; facility and IT figures are not added together. Zero, missing and future projections remain distinct. Existing validated labels are retained for the seven curated matches.
- Completed independent Sentinel-2 extraction from 2018 for all 78 new polygon sites. Accepted event dates occur at 71 sites / 217 halls; 13 halls are left-censored at the first observations; 34 are unresolved. Of those unresolved, 16 brightness candidates conflict with Epoch's reported construction timing and are retained as raw evidence but withheld from public roof dates pending imagery review. The original twelve Abilene dates do not change.
- Geometry judgement calls: 17 source line outlines were closed with endpoint gaps under 5 m; two self-intersections were repaired with Shapely make_valid. All 19 carry low confidence and explicit repair notes; source geometries remain in the snapshot. Planned annotations are not treated as existing roofs.
- Withdrew unsupported Epoch MW from the three provisional Chinese park polygons: published Huawei Horinger, Alibaba Zhangbei and VNET Bayin locations lie approximately 2.0, 1.8 and 15.4 km from those old park centroids. They are separate sourced entries; the old research polygons/adjacent-plant series remain, with capacity tier U.
- Validation: 12 unittest cases pass; all 218 generated JSON files strictly parse; all three site builds pass; deterministic import reproduces inventory/polygon files byte-for-byte. Desktop and 390 px mobile map panels were visually checked locally. The lower request-size limit and bounded retries recovered three Earth Engine concurrent-aggregation failures.
- Review `docs/epoch_inventory_audit.md`, `data/epoch/validation.json`, `data/epoch/import_audit.csv`, and `tools/ingest_epoch.py` first. These are automated brightness-based dates with stated limitations, not independent proof of IT utilisation. A3's dark-roof method remains separate research.
