#!/usr/bin/env python
"""Stage 1–2: polygons in, tidy thermal-observation CSV out.

    python extract.py --backend gcs_c1 --start 2013-04-01 --end 2021-12-31
    python extract.py --backend gee    --start 2022-01-01 --end 2026-09-01

For every site and every usable acquisition the script writes one row per
measured polygon (hall / cooling / substation):

    ΔT = mean(polygon) − mean(matched background annulus)

with valid-pixel counts, QA flags, ERA5 covariates at the acquisition time
and the capacity that the site's documented timeline assigns to that date.
Frames that fail the pixel-count thresholds go to the rejection log; nothing
is dropped silently.  Everything downloaded is cached, so re-runs are offline
and deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import box

from dcheat import geom as G
from dcheat import landsat_c1 as L8
from dcheat import met as MET
from dcheat.era5 import ERA5Point
from dcheat.worldcover import EXCLUDE_ALWAYS, worldcover_on_grid

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

DEFAULTS = dict(
    min_valid_poly_px=6,        # 30 m pixels (≈ 0.7 native 100 m thermal pixels)
    min_valid_poly_frac=0.6,
    min_valid_bg_px=200,
    min_valid_bg_frac=0.25,
    max_scene_cloud=70.0,
    annulus_r_in_m=500.0,
    annulus_r_out_m=2000.0,
    bg_top_classes=2,           # keep the N most common eligible land-cover classes in the annulus
)


def load_sites(path: Path, site_ids=None) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    for c in ("lat", "lon", "elev_m", "annulus_r_in_m", "annulus_r_out_m"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if site_ids:
        df = df[df.site_id.isin(site_ids)]
    return df.reset_index(drop=True)


def load_timeline(path: Path) -> pd.DataFrame:
    tl = pd.read_csv(path, dtype=str).fillna("")
    tl["capacity_mw"] = pd.to_numeric(tl["capacity_mw"], errors="coerce")
    return tl


def capacity_on(tl: pd.DataFrame, site_id: str, date_iso: str):
    rows = tl[(tl.site_id == site_id) & (tl.valid_from <= date_iso) & ((tl.valid_to == "") | (tl.valid_to >= date_iso))]
    if rows.empty:
        return None
    r = rows.sort_values("valid_from").iloc[-1]
    return r


def local_solar_hours(ts_utc: pd.Timestamp, lon: float) -> float:
    h = ts_utc.hour + ts_utc.minute / 60 + ts_utc.second / 3600
    return (h + lon / 15.0) % 24.0


# --------------------------------------------------------------------------
# Landsat 8 Collection 1 backend (public GCS archive)
# --------------------------------------------------------------------------

def bg_class_selection(site, polys, cache_dir, cfg) -> list[int]:
    """Which WorldCover classes form the background: the N most common
    eligible classes inside the annulus (computed in a local UTM grid at 30 m)."""
    override = str(site.get("bg_classes_override") or "").strip()
    if override:  # e.g. "50" for urban sites where only built-up land is a comparable background (same rule as the GEE backend)
        return [int(v) for v in override.split("|") if v.strip()]
    key = Path(cache_dir) / "worldcover" / f"bgclasses_{site.site_id}.json"
    if key.exists():
        return json.loads(key.read_text())
    crs = G.local_utm_crs(site.lon, site.lat)
    ann = G.annulus_geometry(polys, crs, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
    minx, miny, maxx, maxy = ann.bounds
    res = 30.0
    w, h = int((maxx - minx) / res) + 2, int((maxy - miny) / res) + 2
    from rasterio.transform import from_origin
    tr = from_origin(minx, maxy, res, res)
    wc = worldcover_on_grid(site.lat, site.lon, crs, tr, (h, w), cache_dir)
    m = G.rasterize_mask(ann, tr, (h, w))
    vals, counts = np.unique(wc[m], return_counts=True)
    order = sorted([(c, int(v)) for v, c in zip(vals, counts) if int(v) not in EXCLUDE_ALWAYS], reverse=True)
    classes = [v for _, v in order[: cfg["bg_top_classes"]]]
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(json.dumps(classes))
    return classes


def process_scene_c1(site, polys, scene, cache_dir, cfg, bg_classes):
    """Return (rows, rejections) for one Landsat 8 C1 scene."""
    pid, path, row = scene.PRODUCT_ID, int(scene.WRS_PATH), int(scene.WRS_ROW)
    base = L8.scene_base(pid, path, row)
    ts = pd.Timestamp(scene.SENSING_TIME)
    date_iso = ts.strftime("%Y-%m-%d")
    rows, rej = [], []

    def reject(ptype, reason, **kw):
        rej.append(dict(site_id=site.site_id, product_id=pid, datetime_utc=ts.isoformat(), ptype=ptype, reason=reason, **kw))

    # footprint of everything we need, in WGS84, then read the window
    crs_local = G.local_utm_crs(site.lon, site.lat)
    ann_local = G.annulus_geometry(polys, crs_local, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
    bbox_wgs = G.to_crs(box(*ann_local.bounds), crs_local, "EPSG:4326").bounds
    try:
        mtl = L8.read_mtl(base, cache_dir)
        dn, bqa, tr, crs = L8.read_scene_window(base, bbox_wgs, cache_dir)
    except Exception as e:  # network / missing file
        reject("all", f"read_error:{type(e).__name__}:{str(e)[:80]}")
        return rows, rej
    if not (dn > 0).any():
        reject("all", "outside_footprint")
        return rows, rej
    bt = L8.brightness_temperature(dn, mtl)
    bad = L8.bad_pixel_mask(bqa, dn)
    shape = dn.shape

    # background annulus: ring, minus excluded/dissimilar land cover, minus bad pixels
    ann = G.annulus_geometry(polys, crs, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
    ann_mask = G.rasterize_mask(ann, tr, shape)
    wc = worldcover_on_grid(site.lat, site.lon, crs, tr, shape, cache_dir)
    lc_ok = np.isin(wc, bg_classes)
    bg_total = int((ann_mask & lc_ok).sum())
    bg_ok = ann_mask & lc_ok & ~bad
    n_bg = int(bg_ok.sum())
    if bg_total == 0:
        reject("all", "annulus_has_no_eligible_landcover")
        return rows, rej
    bg_frac = n_bg / bg_total
    if n_bg < cfg["min_valid_bg_px"] or bg_frac < cfg["min_valid_bg_frac"]:
        reject("all", "background_too_cloudy", n_valid_bg=n_bg, n_total_bg=bg_total)
        return rows, rej
    t_bg = float(np.nanmean(bt[bg_ok]))
    t_bg_sd = float(np.nanstd(bt[bg_ok]))

    for p in polys:
        if p.ptype not in G.MEASURED_PTYPES or not p.valid_on(date_iso):
            continue
        g = G.to_crs(p.geom_wgs84, "EPSG:4326", crs)
        m = G.rasterize_mask(g, tr, shape)
        n_tot = int(m.sum())
        ok = m & ~bad
        n_ok = int(ok.sum())
        if n_tot == 0:
            reject(p.ptype, "polygon_smaller_than_pixel", polygon=p.name)
            continue
        if n_ok < cfg["min_valid_poly_px"] or n_ok / n_tot < cfg["min_valid_poly_frac"]:
            reject(p.ptype, "polygon_too_cloudy", polygon=p.name, n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_total)
            continue
        t_poly = float(np.nanmean(bt[ok]))
        rows.append(dict(
            site_id=site.site_id, ptype=p.ptype, polygon=p.name, product_id=pid,
            sensor="L8_C1_L1TP_BT_B10", datetime_utc=ts.isoformat(),
            local_solar_hour=round(local_solar_hours(ts, site.lon), 3),
            t_poly_k=round(t_poly, 3), t_bg_k=round(t_bg, 3), delta_t_k=round(t_poly - t_bg, 3),
            t_poly_sd_k=round(float(np.nanstd(bt[ok])), 3), t_bg_sd_k=round(t_bg_sd, 3),
            n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_total,
            scene_cloud_cover=float(scene.CLOUD_COVER), sun_elev_deg=float(mtl.get("SUN_ELEVATION", "nan")),
            qa_flags=f"cloud_conf>=2|shadow_conf>=2|cirrus_conf>=3|bg_classes={','.join(map(str, bg_classes))}",
        ))
    return rows, rej


def run_c1(sites, polys_by_site, cache_dir, start, end, cfg, workers, fill_gaps=True):
    index = L8.load_index(cache_dir)
    all_rows, all_rej = [], []
    for _, site in sites.iterrows():
        polys = polys_by_site.get(site.site_id)
        if not polys:
            print(f"[{site.site_id}] no polygons — skipped", file=sys.stderr)
            continue
        s0 = site.get("obs_start") or start
        s1 = site.get("obs_end") or end
        s0, s1 = max(s0, start), min(s1, end)
        scenes = L8.scenes_for_point(index, site.lat, site.lon, s0, s1, cfg["max_scene_cloud"])
        # fill years the GCS index omits (2018 at the time of writing) from bucket listings
        if not scenes.empty and fill_gaps:
            path_rows = set(zip(scenes.WRS_PATH.astype(int), scenes.WRS_ROW.astype(int)))
            years_present = set(pd.to_datetime(scenes.DATE_ACQUIRED).dt.year)
            gap_years = [y for y in range(int(s0[:4]), int(s1[:4]) + 1) if y not in years_present]
            if gap_years:
                index = L8.supplement_index(index, cache_dir, path_rows, gap_years)
                scenes = L8.scenes_for_point(index, site.lat, site.lon, s0, s1, cfg["max_scene_cloud"])
                print(f"[{site.site_id}] index gap years {gap_years} filled from bucket listing: now {len(scenes)} scenes", file=sys.stderr)
        bg_classes = bg_class_selection(site, polys, cache_dir, cfg)
        t0 = time.time()
        print(f"[{site.site_id}] {len(scenes)} candidate scenes {s0}..{s1}; background classes {bg_classes}", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(process_scene_c1, site, polys, sc, cache_dir, cfg, bg_classes) for sc in scenes.itertuples(index=False)]
            for i, f in enumerate(as_completed(futs)):
                rows, rej = f.result()
                all_rows += rows
                all_rej += rej
                if (i + 1) % 50 == 0:
                    print(f"[{site.site_id}] {i+1}/{len(scenes)} scenes, {len(all_rows)} rows so far ({time.time()-t0:.0f}s)", file=sys.stderr)
        print(f"[{site.site_id}] done in {time.time()-t0:.0f}s", file=sys.stderr)
    return pd.DataFrame(all_rows), pd.DataFrame(all_rej)


# --------------------------------------------------------------------------
# weather + capacity joins
# --------------------------------------------------------------------------

def _weather_worker(task):
    """One process: its own ERA5 reader; returns records for a batch of keys."""
    cache_dir, batch = task
    era = ERA5Point(cache_dir)
    recs = []
    for sid, ts, lat, lon, elev in batch:
        when = pd.Timestamp(ts).tz_convert("UTC").tz_localize(None)
        try:
            v = era.at(lat, lon, when)
        except Exception as e:
            print(f"[weather] {sid} {ts}: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
            continue
        d = MET.derive(v["t2m"], v["d2m"], v["u10"], v["v10"], elev_m=elev)
        recs.append(dict(site_id=sid, datetime_utc=ts, t2m_k=round(v["t2m"], 3), d2m_k=round(v["d2m"], 3), u10=round(v["u10"], 3), v10=round(v["v10"], 3),
                         ta_c=round(float(d["ta_c"]), 3), td_c=round(float(d["td_c"]), 3), rh_pct=round(float(d["rh_pct"]), 2),
                         wind_ms=round(float(d["wind_ms"]), 3), q_kgkg=round(float(d["q_kgkg"]), 6), tw_c=round(float(d["tw_c"]), 3)))
    era.close()
    return recs


def join_weather(obs: pd.DataFrame, sites: pd.DataFrame, cache_dir, workers: int = 6) -> pd.DataFrame:
    """ERA5 at each (site, acquisition time).  Batched across processes because
    every uncached point read costs one ~2 MB chunk from S3."""
    if obs.empty:
        return obs
    from concurrent.futures import ProcessPoolExecutor
    site_lookup = sites.set_index("site_id")
    keys = obs[["site_id", "datetime_utc"]].drop_duplicates().sort_values(["site_id", "datetime_utc"])
    items = [(sid, ts, float(site_lookup.loc[sid].lat), float(site_lookup.loc[sid].lon), float(site_lookup.loc[sid].get("elev_m") or 0.0))
             for sid, ts in keys.itertuples(index=False)]
    n = max(1, min(workers, len(items)))
    batches = [items[i::n] for i in range(n)]
    print(f"[weather] {len(items)} site-times to join in {n} processes", file=sys.stderr)
    recs = []
    with ProcessPoolExecutor(max_workers=n) as ex:
        for r in ex.map(_weather_worker, [(cache_dir, b) for b in batches]):
            recs += r
    if not recs:
        return obs
    return obs.merge(pd.DataFrame(recs), on=["site_id", "datetime_utc"], how="left")


def join_capacity(obs: pd.DataFrame, tl: pd.DataFrame) -> pd.DataFrame:
    if obs.empty:
        return obs
    cols = {"capacity_mw": [], "capacity_basis": [], "capacity_tier": [], "capacity_source": []}
    for sid, ts in zip(obs.site_id, obs.datetime_utc):
        r = capacity_on(tl, sid, pd.Timestamp(ts).strftime("%Y-%m-%d"))
        cols["capacity_mw"].append(float(r.capacity_mw) if r is not None else np.nan)
        cols["capacity_basis"].append(r.capacity_basis if r is not None else "")
        cols["capacity_tier"].append(r.tier if r is not None else "")
        cols["capacity_source"].append(r.source if r is not None else "")
    for k, v in cols.items():
        obs[k] = v
    return obs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["gcs_c1", "gee", "ecostress"], default="gcs_c1")
    ap.add_argument("--sites", default=str(DATA / "sites.csv"))
    ap.add_argument("--timeline", default=str(DATA / "capacity_timeline.csv"))
    ap.add_argument("--polygons", default=str(DATA / "polygons"))
    ap.add_argument("--site-ids", nargs="*", default=None)
    ap.add_argument("--start", default="2013-04-11")
    ap.add_argument("--end", default="2021-12-31")
    ap.add_argument("--cache", default=str(DATA / "cache"))
    ap.add_argument("--out", default=str(DATA / "observations.csv"))
    ap.add_argument("--rejections", default=str(DATA / "rejections.csv"))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-weather", action="store_true")
    ap.add_argument("--append", action="store_true", help="merge with an existing output file (rows keyed by site, polygon, product)")
    ap.add_argument("--no-fill-index-gaps", action="store_true", help="do not fill years missing from the GCS index by listing the bucket")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}
    if args.backend == "ecostress":
        # pixel-count thresholds were set for 30 m Landsat pixels; ECOSTRESS L2T pixels are 70 m (5.4x the area).
        # Scale any threshold the user left at its default so small supercomputer halls (1-2 pixels) are measurable.
        scale = (30.0 / 70.0) ** 2
        if cfg["min_valid_poly_px"] == DEFAULTS["min_valid_poly_px"]:
            cfg["min_valid_poly_px"] = max(2, round(DEFAULTS["min_valid_poly_px"] * scale))
        if cfg["min_valid_bg_px"] == DEFAULTS["min_valid_bg_px"]:
            cfg["min_valid_bg_px"] = max(20, round(DEFAULTS["min_valid_bg_px"] * scale))
        print(f"[ecostress] pixel thresholds scaled to 70 m: min_valid_poly_px={cfg['min_valid_poly_px']}, min_valid_bg_px={cfg['min_valid_bg_px']}", file=sys.stderr)
    cache_dir = Path(args.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)

    sites = load_sites(Path(args.sites), args.site_ids)
    tl = load_timeline(Path(args.timeline))
    polys_by_site = {}
    for sid in sites.site_id:
        p = Path(args.polygons) / f"{sid}.geojson"
        if p.exists():
            polys_by_site[sid] = G.load_site_polygons(p)
    # per-site annulus overrides
    if args.backend == "gcs_c1":
        obs, rej = run_c1(sites, polys_by_site, cache_dir, args.start, args.end, cfg, args.workers, fill_gaps=not args.no_fill_index_gaps)
    elif args.backend == "gee":
        from dcheat.gee import run_gee
        obs, rej = run_gee(sites, polys_by_site, cache_dir, args.start, args.end, cfg)
    else:
        from dcheat.ecostress import run_ecostress
        obs, rej = run_ecostress(sites, polys_by_site, cache_dir, args.start, args.end, cfg, args.workers, bg_class_selection)

    if not args.no_weather and args.backend in ("gcs_c1", "ecostress"):
        # the gee backend already attaches ERA5-Land at the acquisition hour server-side
        obs = join_weather(obs, sites, cache_dir, workers=args.workers)
    obs = join_capacity(obs, tl)
    if not obs.empty:
        obs = obs.sort_values(["site_id", "datetime_utc", "ptype", "polygon"]).reset_index(drop=True)
    def _read_old(p, **kw):
        try:
            return pd.read_csv(p, **kw)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return pd.DataFrame()

    out = Path(args.out)
    if args.append and out.exists():
        old = _read_old(out, dtype={"product_id": str})
        if obs.empty:
            # a site that produced no rows must not clobber the other sites' rows
            print(f"[append] no new observations for {sorted(sites.site_id)}; {out} left unchanged ({len(old)} rows)", file=sys.stderr)
            obs = old
        elif not old.empty:
            old = old[~old.site_id.isin(obs.site_id.unique())]
            obs = pd.concat([old, obs], ignore_index=True).sort_values(["site_id", "datetime_utc", "ptype", "polygon"]).reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    obs.to_csv(out, index=False)
    rp = Path(args.rejections)
    if args.append and rp.exists():
        old = _read_old(rp, dtype=str)
        if rej.empty:
            rej = old
        elif not old.empty:
            old = old[~old.site_id.isin(rej.site_id.unique())]
            rej = pd.concat([old, rej], ignore_index=True)
    if not rej.empty:
        rej = rej.sort_values(["site_id", "datetime_utc", "ptype"]).reset_index(drop=True)
    rej.to_csv(rp, index=False)
    print(f"wrote {len(obs)} observations to {out} and {len(rej)} rejections to {rp}", file=sys.stderr)
    meta = dict(backend=args.backend, start=args.start, end=args.end, config=cfg, n_obs=int(len(obs)), n_rej=int(len(rej)),
                sites=sorted(sites.site_id.tolist()), generated=pd.Timestamp.utcnow().isoformat())
    (out.parent / "extract_meta.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
