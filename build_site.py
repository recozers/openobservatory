#!/usr/bin/env python
"""Stage 5: model output → static JSON for site/.

    python build_site.py

Reads data/sites.csv, data/capacity_timeline.csv, data/polygons/*.geojson,
data/observations.csv, data/rejections.csv and results/model_report.json and
writes site/data/sites.json plus site/data/obs/<site_id>.json.  No backend:
the frontend only fetches these files.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA, RESULTS, SITE = ROOT / "data", ROOT / "results", ROOT / "site"

Q_BINS = [(0, 5, "< 5 MW"), (5, 15, "5–15 MW"), (15, 50, "15–50 MW"), (50, 150, "50–150 MW"), (150, 500, "150–500 MW"), (500, 1e9, "> 500 MW")]


def q_bin(q):
    if q is None or not np.isfinite(q) or q <= 0:
        return "no estimate"
    for lo, hi, lab in Q_BINS:
        if lo <= q < hi:
            return lab
    return "no estimate"


def interval_class(lo, hi):
    """Coarse width class from the 5–95 % interval, as a ratio."""
    if lo is None or hi is None or not np.isfinite(lo) or not np.isfinite(hi) or lo <= 0:
        return "unbounded"
    r = hi / lo
    return "narrow (< 2×)" if r < 2 else "moderate (2–4×)" if r < 4 else "wide (4–10×)" if r < 10 else "very wide (> 10×)"


def none_if_nan(v):
    try:
        return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v
    except Exception:
        return None


def sanitize(obj):
    """Recursively turn NaN/inf and numpy scalars into JSON-safe values.
    `NaN` is not valid JSON and a single one breaks the whole frontend."""
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not math.isfinite(float(obj)) else float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def main():
    sites = pd.read_csv(DATA / "sites.csv", dtype=str).fillna("")
    tl = pd.read_csv(DATA / "capacity_timeline.csv", dtype=str).fillna("")
    import os
    obs_path = Path(os.environ.get("OBS_FILE", DATA / "observations.csv"))
    rej_path = Path(os.environ.get("REJ_FILE", DATA / "rejections.csv"))
    results_dir = Path(os.environ.get("RESULTS_DIR", RESULTS))
    obs = pd.read_csv(obs_path, dtype={"product_id": str}) if obs_path.exists() else pd.DataFrame()
    rej = pd.read_csv(rej_path, dtype=str) if rej_path.exists() and rej_path.stat().st_size > 0 else pd.DataFrame()
    report = json.loads((results_dir / "model_report.json").read_text()) if (results_dir / "model_report.json").exists() else {}
    est = pd.DataFrame(report.get("site_estimates", []))
    est = est.set_index("site_id") if not est.empty else est
    meta = json.loads((DATA / "extract_meta.json").read_text()) if (DATA / "extract_meta.json").exists() else {}

    from dcheat import geom as G
    (SITE / "data" / "obs").mkdir(parents=True, exist_ok=True)
    out_sites = []
    for _, s in sites.iterrows():
        sid = s.site_id
        lat, lon = float(s.lat), float(s.lon)
        polys = []
        pfile = DATA / "polygons" / f"{sid}.geojson"
        if pfile.exists():
            pl = G.load_site_polygons(pfile)
            areas = G.polygon_areas_m2(pl, lon, lat)
            for p in pl:
                polys.append(dict(name=p.name, ptype=p.ptype, confidence=p.props.get("confidence", ""), note=p.props.get("note", ""),
                                  digitised_from=p.props.get("digitised_from", ""), source_url=p.props.get("source_url", ""),
                                  geometry_repair=p.props.get("geometry_repair", ""), roof_date_required=p.props.get("roof_date_required", False),
                                  valid_from=p.valid_from, area_ha=round(G.polygon_areas_m2([p], lon, lat)[p.ptype] / 1e4, 2)))
        so = obs[obs.site_id == sid] if not obs.empty else pd.DataFrame()
        sr = rej[rej.site_id == sid] if not rej.empty else pd.DataFrame()
        e = est.loc[sid] if (not est.empty and sid in est.index) else None
        tier = s.capacity_tier or "U"
        region_cn = (s.region == "CN")
        if e is None or int(e.n_frames) == 0:
            case = "no_data"
        elif not bool(e.get("q_identified", False)) or not np.isfinite(float(e.q_hat_mw)):
            case = "measured_not_identified"
        elif region_cn and not bool(e.get("in_training_set", False)):
            case = "unvalidated_transfer"
        elif bool(e.get("utilisation_identified", False)):
            case = "utilisation_identified"
        else:
            case = "q_only"
        # when the model's own kill conditions are met, no thermal inversion is shown as an estimate anywhere
        if (report.get("kill_conditions") or {}).get("verdict") == "negative_result" and case in ("utilisation_identified", "q_only", "unvalidated_transfer"):
            case = "measured_not_identified"
        # Chinese Tier A sites that were fitted are still flagged: the transfer is measured, not assumed
        transfer_note = ""
        if region_cn:
            transfer_note = ("Chinese site. No thermal inversion is shown for any site (the cross-site relation is not identified). "
                             "The load band below comes from documented or Epoch capacity, Sentinel-2 roof timelines and, where an adjacent plant exists, an NO2 activity index. See each polygon's source and confidence.")
        n_frames = int(so.datetime_utc.nunique()) if not so.empty else 0
        rej_counts = sr.groupby("reason").size().to_dict() if not sr.empty else {}
        n_rej_frames = int(sr.groupby(["product_id"]).ngroups) if not sr.empty else 0
        tl_s = tl[tl.site_id == sid]
        timeline = [dict(valid_from=r.valid_from, valid_to=r.valid_to or None, capacity_mw=float(r.capacity_mw), basis=r.capacity_basis, tier=r.tier, source=r.source, url=r.url, notes=r.notes) for r in tl_s.itertuples()]
        rec = dict(
            site_id=sid, name=s["name"], operator=s.operator, country=s.country, region=s.region, lat=lat, lon=lon,
            coords_quality=s.get("coords_quality", ""), cooling_arch=s.cooling_arch, capacity_tier=tier, capacity_mw=none_if_nan(float(s.capacity_mw)) if s.capacity_mw else None,
            capacity_basis=s.capacity_basis, pue_assumed=float(s.pue_assumed) if s.pue_assumed else 1.2,
            capacity_source=s.capacity_source, capacity_url=s.capacity_url, in_epoch_db=s.in_epoch_db, notes=s.notes,
            thermal_backend=s.thermal_backend, obs_start=s.obs_start, obs_end=s.obs_end, case=case, transfer_note=transfer_note,
            n_frames=n_frames, n_rejected_frames=n_rej_frames, rejection_reasons=rej_counts, polygons=polys, capacity_timeline=timeline,
        )
        if e is not None:
            rec.update(dict(
                q_hat_mw=none_if_nan(float(e.q_hat_mw)), q_lo_mw=none_if_nan(float(e.q_lo_mw)), q_hi_mw=none_if_nan(float(e.q_hi_mw)),
                it_hat_mw=none_if_nan(float(e.it_hat_mw)), it_lo_mw=none_if_nan(float(e.it_lo_mw)), it_hi_mw=none_if_nan(float(e.it_hi_mw)),
                capacity_it_mw=none_if_nan(float(e.capacity_it_mw)), utilisation=none_if_nan(float(e.utilisation)) if case == "utilisation_identified" else None,
                mean_delta_t_k=none_if_nan(float(e.mean_delta_t_k)), sd_delta_t_k=none_if_nan(float(e.sd_delta_t_k)), area_ha=none_if_nan(float(e.area_ha)),
                in_training_set=bool(e.get("in_training_set", False)), q_bin=q_bin(float(e.q_hat_mw)), interval_class=interval_class(float(e.q_lo_mw), float(e.q_hi_mw)),
            ))
        else:
            rec.update(dict(q_hat_mw=None, q_lo_mw=None, q_hi_mw=None, it_hat_mw=None, utilisation=None, q_bin="no estimate", interval_class="unbounded", in_training_set=False))
        rec["frames_bin"] = "none" if n_frames == 0 else "< 30 frames" if n_frames < 30 else "30–100 frames" if n_frames < 100 else "> 100 frames"
        out_sites.append(rec)

        # per-site observation file
        frames = []
        if not so.empty:
            for r in so.sort_values(["datetime_utc", "ptype", "polygon"]).itertuples():
                frames.append(dict(t=r.datetime_utc, sensor=r.sensor, ptype=r.ptype, polygon=r.polygon, dt=round(float(r.delta_t_k), 2),
                                   t_poly=round(float(r.t_poly_k), 1), t_bg=round(float(r.t_bg_k), 1), n_valid_poly=int(r.n_valid_poly), n_total_poly=int(r.n_total_poly),
                                   n_valid_bg=int(r.n_valid_bg), sun=none_if_nan(round(float(r.sun_elev_deg), 1)) if pd.notna(r.sun_elev_deg) else None,
                                   cloud=none_if_nan(round(float(r.scene_cloud_cover), 1)),
                                   ta=none_if_nan(round(float(r.ta_c), 1)) if "ta_c" in so and pd.notna(r.ta_c) else None,
                                   wind=none_if_nan(round(float(r.wind_ms), 1)) if "wind_ms" in so and pd.notna(r.wind_ms) else None,
                                   tw=none_if_nan(round(float(r.tw_c), 1)) if "tw_c" in so and pd.notna(r.tw_c) else None,
                                   rh=none_if_nan(round(float(r.rh_pct), 0)) if "rh_pct" in so and pd.notna(r.rh_pct) else None,
                                   capacity_mw=none_if_nan(float(r.capacity_mw)) if "capacity_mw" in so and pd.notna(r.capacity_mw) else None,
                                   product_id=r.product_id))
        rejections = []
        if not sr.empty:
            for r in sr.sort_values(["datetime_utc"]).itertuples():
                rejections.append(dict(t=r.datetime_utc, ptype=r.ptype, reason=r.reason, product_id=r.product_id))
        (SITE / "data" / "obs" / f"{sid}.json").write_text(json.dumps(sanitize(dict(site_id=sid, frames=frames, rejections=rejections)), separators=(",", ":"), allow_nan=False))

    model_summary = {}
    if report:
        model_summary = dict(
            status=report.get("status"), ptype=report.get("ptype"), capacity_col=report.get("capacity_col"), met=report.get("met"),
            n_sites_tier_a=report.get("n_sites_tier_a"), n_frames_tier_a=report.get("n_frames_tier_a"), n_sites_all=report.get("n_sites_all"), n_frames_all=report.get("n_frames_all"),
            slope=report.get("slope"), variance=report.get("variance_all_frames"), loso=report.get("loso_all_frames"), loso_conditioned=report.get("loso_conditioned"),
            n_frames_conditioned=report.get("n_frames_conditioned"), n_sites_conditioned=report.get("n_sites_conditioned"),
            kill_conditions=report.get("kill_conditions"), model=report.get("model_all_frames"), model_conditioned=report.get("model_conditioned"),
            secondary=report.get("secondary"), loso_rows=report.get("loso_rows"), within_site=report.get("within_site"),
        )
    out = dict(generated=pd.Timestamp.now("UTC").isoformat(), extract_meta=meta, model=model_summary, sites=out_sites,
               q_bins=[b[2] for b in Q_BINS] + ["no estimate"],
               credits="Site list and capacity provenance compiled in this repository; Epoch AI's AI Data Centers database (CC-BY) is the intended source for the AI-site list and was not reachable from the build environment. Landsat 8 Collection 1 (USGS, via Google Cloud Public Datasets). ERA5 (ECMWF/Copernicus, via NCAR/NSF mirror on AWS). ESA WorldCover 2021 (CC-BY). Natural Earth basemap.")
    (SITE / "data" / "sites.json").write_text(json.dumps(sanitize(out), indent=1, allow_nan=False, default=str))
    print(f"wrote site/data/sites.json ({len(out_sites)} sites) and {len(out_sites)} observation files")


if __name__ == "__main__":
    main()
