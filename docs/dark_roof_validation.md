# Dark-roof index test: negative result

The proposed second roof rule is not validated. It preserves all 12 Abilene dates, but gives Hyperion north June 2026 (after the January 2026 acceptance date) and south September 2023 (before construction). No Chinese hall gets a new index date. Production roof dating is unchanged.

Run `python tools/s2_roof_index_test.py --extract SITE --end 2026-09-14` once for each of the five supported sites, then run the script without arguments. Annual Earth Engine responses are cached by polygon hash and date range. The committed monthly CSVs reproduce the report without credentials.

The test uses cloud-masked Sentinel-2 surface reflectance, at least ten valid pixels per hall/image, monthly median polygon means, NDVI < 0.15 and NDBI or BSI at least 0.08 above the first six valid months for two consecutive calendar months. The brief did not prescribe a numerical index rise; 0.08 is an explicit experimental choice, not a calibrated threshold.

| Site / hall | Brightness | NDVI + NDBI | NDVI + BSI | First rule |
|---|---|---|---|---|
| hyperion_la / structure_north | not_yet | 2026-06 | not_yet | 2026-06 |
| hyperion_la / structure_south | not_yet | 2023-09 | 2023-09 | 2023-09 |
| stargate_abilene / phase1_block1 | 2025-01 | not_yet | not_yet | 2025-01 |
| stargate_abilene / phase1_block2 | 2024-07 | not_yet | not_yet | 2024-07 |
| stargate_abilene / phase2_mid_block1 | 2025-05 | not_yet | not_yet | 2025-05 |
| stargate_abilene / phase2_mid_block2 | 2025-03 | not_yet | not_yet | 2025-03 |
| stargate_abilene / phase2_mid_block3 | 2025-04 | not_yet | not_yet | 2025-04 |
| stargate_abilene / phase2_mid_block4 | 2025-06 | not_yet | not_yet | 2025-06 |
| stargate_abilene / phase2_south_block1 | 2025-05 | not_yet | not_yet | 2025-05 |
| stargate_abilene / phase2_south_block2 | 2025-04 | not_yet | not_yet | 2025-04 |
| stargate_abilene / phase2_south_block3 | 2025-05 | not_yet | not_yet | 2025-05 |
| stargate_abilene / phase2_south_block4 | 2025-10 | not_yet | not_yet | 2025-10 |
| stargate_abilene / phase2_south_block5 | 2025-06 | not_yet | not_yet | 2025-06 |
| stargate_abilene / phase2_south_block6 | 2025-07 | not_yet | not_yet | 2025-07 |
| cn_horinger_cloud_valley / block_a | not_yet | not_yet | not_yet | not_yet |
| cn_horinger_cloud_valley / block_b | not_yet | not_yet | not_yet | not_yet |
| cn_horinger_cloud_valley / block_c | existing | not_yet | not_yet | existing |
| cn_horinger_cloud_valley / block_d | not_yet | not_yet | not_yet | not_yet |
| cn_zhangbei_alibaba / west_halls | existing | not_yet | not_yet | existing |
| cn_ulanqab_park / long_halls | 2025-11 | not_yet | not_yet | 2025-11 |
| cn_ulanqab_park / white_block | not_yet | not_yet | not_yet | not_yet |

The Hyperion south false event coincides with a low-vegetation interval in the monthly series; seasonal bare/fallow ground is a plausible explanation, not independent roof evidence. North remains too vegetated at the whole-polygon scale around January 2026 to satisfy the fixed NDVI criterion. Smaller verified roof footprints or a different event model need validation; choosing a threshold or date merely to match the expected month would hide this failure.

The three Chinese polygons are provisional and low-confidence. Existing/unknown brightness labels are reported as the algorithm returns them, not newly validated hall identities. Claude has independently added radar structure dates on main; these are different evidence and are not used to claim this optical test succeeded.

A3 is blocked on scientific validation. A draft PR preserves the extraction, results and failure; no public build uses the experimental rule.
