"""Turn hall-like radar candidates into inventory entries (phase 2, C7: China coverage from radar).

    python tools/ingest_radar_candidates.py --scores results_cand/scores.csv --hubs ulanqab horinger ... [--min-score 0.5] [--min-area 5]

For each hub box, every candidate with area >= --min-area ha and classifier score >= --min-score that does not intersect an
existing site's hall polygons becomes a site `cn_<hub>_r<rank>` (coords_quality radar_candidate, site_class radar_candidate,
tier U) with a one-feature polygon file (ptype hall, confidence low) cut from the radar blob outline, and a note carrying
the score, area and VV rise. Also writes results_s1/<hub>_newsites.geojson (all new outlines of the hub, names = site ids)
for one tools/s1_timeline.py run per hub; tools/split_s1_hub.py then writes results_s1/<site>.csv per site so the build
picks up the radar structure-on month. Idempotent: existing site ids are left alone, and ids that data/cn_radar_review.csv
(RFW-01) has rejected as "not a data centre" are never re-added.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
HUB_COUNTRY = "CN"
HUB_NAMES = {"ulanqab": "Ulanqab", "horinger": "Horinger", "zhangbei": "Zhangbei", "guian": "Gui'an", "chongqing_shuitu": "Chongqing Shuitu",
             "qingyang": "Qingyang", "zhongwei": "Zhongwei", "zhangjiakou_huailai": "Zhangjiakou / Huailai", "wuhu": "Wuhu",
             "shaoguan": "Shaoguan", "chengdu_tianfu": "Chengdu Tianfu", "tianjin_wuqing": "Tianjin Wuqing"}


def existing_halls(sites):
    geoms = []
    for sid in sites.site_id:
        p = ROOT / "data" / "polygons" / f"{sid}.geojson"
        if p.exists():
            g = json.load(open(p))
            geoms += [shape(f["geometry"]) for f in g["features"] if f["properties"].get("ptype") == "hall"]
    return unary_union(geoms) if geoms else None


def rejected_ids(path=None):
    """Site ids whose RFW-01 review verdict is "not a data centre"; they stay out of the inventory."""
    path = path or ROOT / "data" / "cn_radar_review.csv"
    if not path.exists():
        return set()
    rev = pd.read_csv(path, dtype=str).fillna("")
    return set(rev.loc[rev.verdict.str.strip() == "not a data centre", "site_id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="results_cand/scores.csv")
    ap.add_argument("--hubs", nargs="+", required=True)
    ap.add_argument("--min-score", type=float, default=0.5)
    ap.add_argument("--min-area", type=float, default=5.0)
    args = ap.parse_args()
    sc = pd.read_csv(ROOT / args.scores)
    sc["key"] = sc.file.str.extract(r"results_s1/(?:china/)?([^/]+)_candidates")[0]
    sites = pd.read_csv(ROOT / "data" / "sites.csv", dtype=str).fillna("")
    have = set(sites.site_id)
    rejected = rejected_ids()
    known = existing_halls(sites)
    new_rows, n_new = [], 0
    for hub in args.hubs:
        gj_path = ROOT / "results_s1" / f"{hub}_candidates.geojson"
        if not gj_path.exists():
            print(f"  {hub}: no candidates file"); continue
        gj = json.load(open(gj_path))
        outlines = {f["properties"]["rank"]: f for f in gj["features"]}
        cands = sc[(sc.key == hub) & (sc.area_ha >= args.min_area) & (sc.score_cand >= args.min_score)]
        hub_feats = []
        for _, c in cands.iterrows():
            rank = int(c["rank"]); sid = f"cn_{hub}_r{rank:02d}"
            f = outlines.get(rank)
            if f is None:
                continue
            geom = shape(f["geometry"])
            if known is not None and geom.intersects(known):
                continue  # already an inventory site's hall
            if sid in have or sid in rejected:
                continue
            rp = geom.representative_point()
            feat = {"type": "Feature", "geometry": f["geometry"],
                    "properties": {"name": "structure", "ptype": "hall", "confidence": "low", "site_id": sid,
                                   "note": f"Radar-detected new structure {c.area_ha:.1f} ha, VV rise {c.rise_db:.1f} dB 2021-2026, hall-like score {c.score_cand:.2f}; unconfirmed, operator unknown.",
                                   "digitised_from": f"Sentinel-1 candidate scan {hub} rank {rank}; outline is the 20 m radar blob"}}
            (ROOT / "data" / "polygons" / f"{sid}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}))
            hub_feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {"name": sid, "ptype": "hall"}})
            r = {col: "" for col in sites.columns}
            r.update(dict(site_id=sid, name=f"{HUB_NAMES.get(hub, hub)} radar structure #{rank} ({c.area_ha:.0f} ha)", operator="unknown", country=HUB_COUNTRY,
                          lat=f"{rp.y:.5f}", lon=f"{rp.x:.5f}", coords_quality="radar_candidate", site_class="radar_candidate", capacity_tier="U",
                          pue_assumed="1.2", in_epoch_db="no",
                          notes=f"radar_candidate score={c.score_cand:.2f} area_ha={c.area_ha:.1f} rise_db={c.rise_db:.1f}. New structure found by the Sentinel-1 candidate scan of the {HUB_NAMES.get(hub, hub)} hub box (2021 to 2026), hall-like by the morphology classifier; not confirmed as a data centre, operator unknown."))
            new_rows.append(r); have.add(sid); n_new += 1
        if hub_feats:
            (ROOT / "results_s1" / f"{hub}_newsites.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": hub_feats}))
        print(f"  {hub}: {len(hub_feats)} new sites")
    if new_rows:
        pd.concat([sites, pd.DataFrame(new_rows)], ignore_index=True).to_csv(ROOT / "data" / "sites.csv", index=False)
    print(f"added {n_new} radar-candidate sites")


if __name__ == "__main__":
    main()
