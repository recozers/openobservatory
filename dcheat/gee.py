"""Google Earth Engine backend — the data path the project brief specifies.

Landsat 8/9 Collection 2 Level-2 surface temperature (ST_B10, scale 0.00341802,
offset 149.0 → Kelvin, already atmospherically corrected and emissivity
adjusted), QA_PIXEL cloud/shadow masking, ESA WorldCover annulus masking and
ERA5-Land hourly covariates, all computed server-side per acquisition.

STATUS: written against the public EE Python API but NOT executed in the
environment that produced this repository (no EE credentials, EE endpoints
blocked).  Expect small API-drift fixes on first run.  Run with:

    earthengine authenticate            # once
    EE_PROJECT=<your-cloud-project> python extract.py --backend gee \
        --start 2022-01-01 --end 2026-09-01

Output rows use the same schema as the gcs_c1 backend so model.py and
build_site.py need no changes; `sensor` is L8_C2_L2_ST / L9_C2_L2_ST.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import geom as G
from .worldcover import EXCLUDE_ALWAYS

ST_SCALE, ST_OFFSET = 0.00341802, 149.0
# Collection 2 QA_PIXEL bits
QA_FILL, QA_DILATED, QA_CIRRUS, QA_CLOUD, QA_SHADOW = 1 << 0, 1 << 1, 1 << 2, 1 << 3, 1 << 4


def _ee():
    import ee  # noqa: F401
    proj = os.environ.get("EE_PROJECT")
    try:
        ee.Initialize(project=proj) if proj else ee.Initialize()
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=proj) if proj else ee.Initialize()
    # fail a hung request (e.g. after the machine sleeps) instead of blocking forever; the per-site cache makes re-runs cheap
    ee.data.setDeadline(int(os.environ.get("EE_DEADLINE_MS", "900000")))
    return ee


def _polys_to_ee(ee, polys, date_iso=None):
    feats = []
    for p in polys:
        if p.ptype not in G.MEASURED_PTYPES:
            continue
        feats.append(ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {"name": p.name, "ptype": p.ptype,
                                                                       "valid_from": p.valid_from or "", "valid_to": p.valid_to or ""}))
    return ee.FeatureCollection(feats)


def _fetch_chunked(ee, col, per_image, start, end, n_polys, limit=4500, depth=0):
    """getInfo() refuses collections over 5000 elements; split the date range until images x polygons fits."""
    sub = col.filterDate(start, end)
    n_img = int(sub.size().getInfo())
    if n_img == 0:
        return []
    if n_img * max(n_polys, 1) <= limit or depth > 8:
        return ee.FeatureCollection(sub.map(per_image)).flatten().getInfo()["features"]
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end)
    mid = (t0 + (t1 - t0) / 2).strftime("%Y-%m-%d")
    if mid in (start, end):
        return ee.FeatureCollection(sub.map(per_image)).flatten().getInfo()["features"]
    return (_fetch_chunked(ee, col, per_image, start, mid, n_polys, limit, depth + 1)
            + _fetch_chunked(ee, col, per_image, mid, end, n_polys, limit, depth + 1))


def run_gee(sites: pd.DataFrame, polys_by_site: dict, cache_dir, start: str, end: str, cfg: dict):
    ee = _ee()
    cache = Path(cache_dir) / "gee"
    cache.mkdir(parents=True, exist_ok=True)
    rows, rej = [], []
    wc = ee.Image("ESA/WorldCover/v200/2021").select("Map")
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")

    for _, site in sites.iterrows():
        polys = polys_by_site.get(site.site_id)
        if not polys:
            continue
        key = cache / f"{site.site_id}_{start}_{end}.json"
        if key.exists():
            feats = json.loads(key.read_text())
        else:
            crs = G.local_utm_crs(site.lon, site.lat)
            ann_local = G.annulus_geometry(polys, crs, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
            ann = ee.Geometry(G.mapping(G.to_crs(ann_local, crs, "EPSG:4326")))
            measured = _polys_to_ee(ee, polys)
            pt = ee.Geometry.Point([float(site.lon), float(site.lat)])
            # background land-cover eligibility: exclude water/built/snow/wetland, keep the N most common remaining classes
            override = str(site.get("bg_classes_override") or "").strip()
            if override:
                keep = [int(v) for v in override.split("|")]
            else:
                hist = wc.reduceRegion(ee.Reducer.frequencyHistogram(), ann, 10, maxPixels=1e9).get("Map").getInfo()
                order = sorted(((c, int(k)) for k, c in hist.items() if int(k) not in EXCLUDE_ALWAYS), reverse=True)
                keep = [v for _, v in order[: cfg["bg_top_classes"]]]
            bg_mask = wc.remap(keep, [1] * len(keep), 0)

            col = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
                   .filterBounds(pt).filterDate(start, end).filter(ee.Filter.lt("CLOUD_COVER", cfg["max_scene_cloud"])))

            def per_image(img):
                qa = img.select("QA_PIXEL")
                fill = qa.bitwiseAnd(QA_FILL).gt(0)
                cirrus = qa.bitwiseAnd(QA_CIRRUS).gt(0)
                bad_strict = (fill.Or(qa.bitwiseAnd(QA_DILATED).gt(0)).Or(cirrus)
                              .Or(qa.bitwiseAnd(QA_CLOUD).gt(0)).Or(qa.bitwiseAnd(QA_SHADOW).gt(0)))
                st_raw = img.select("ST_B10").multiply(ST_SCALE).add(ST_OFFSET).rename("st")
                st = st_raw.updateMask(bad_strict.Not())
                t = img.date()
                # background: strict QA mask (CFMask is reliable over vegetation / soil)
                bg = st.updateMask(bg_mask).reduceRegion(ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), ann, 30, maxPixels=1e8)
                # totals on the scene's own 30 m grid: an unprojected constant image is sampled on a lat/lon grid and overcounts by 1/cos(lat)
                bg_total = st_raw.mask().updateMask(bg_mask).reduceRegion(ee.Reducer.count(), ann, 30, maxPixels=1e8).get("st")
                # roof: CFMask flags bright white membrane roofs as cloud on clear days (verified at Fairwater: roof 63 % "cloud",
                # ring 88 % clear, scene cloud 0.3 %), and the cloud test uses temperature, so cold unpowered roofs are masked
                # preferentially.  The relaxed roof mask therefore keeps QA cloud/dilated/shadow flags out of the polygon and
                # instead removes fill, cirrus (SWIR test, not fooled by bright roofs) and pixels > cold_k colder than the clear
                # background, which is what real cloud over the roof looks like.  Both variants are stored; the choice is made in
                # Python from the background clear fraction.
                bg_mean = ee.Number(ee.Algorithms.If(bg.get("st_mean"), bg.get("st_mean"), -1e6))
                cold = st_raw.lt(bg_mean.subtract(cfg.get("roof_cold_k", 10.0)))
                st_relaxed = st_raw.updateMask(fill.Or(cirrus).Or(cold).Not())
                # ERA5-Land at the acquisition hour (nearest hourly step)
                e = era5.filterDate(t.advance(-1, "hour"), t.advance(1, "hour")).first()
                met = ee.Algorithms.If(e, ee.Image(e).select(["temperature_2m", "dewpoint_temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m"])
                                       .reduceRegion(ee.Reducer.first(), pt, 11132), ee.Dictionary({}))

                def per_poly(f):
                    red = ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True)
                    r = st.reduceRegion(red, f.geometry(), 30, maxPixels=1e8)
                    rr = st_relaxed.reduceRegion(red, f.geometry(), 30, maxPixels=1e8)
                    tot = st_raw.mask().reduceRegion(ee.Reducer.count(), f.geometry(), 30, maxPixels=1e8).get("st")
                    return f.set({"product_id": img.get("LANDSAT_PRODUCT_ID"), "spacecraft": img.get("SPACECRAFT_ID"),
                                  "time": t.format("YYYY-MM-dd'T'HH:mm:ss'Z'"),
                                  "t_poly_k_strict": r.get("st_mean"), "n_valid_poly_strict": r.get("st_count"),
                                  "t_poly_k_relaxed": rr.get("st_mean"), "n_valid_poly_relaxed": rr.get("st_count"), "n_total_poly": tot,
                                  "t_bg_k": bg.get("st_mean"), "n_valid_bg": bg.get("st_count"), "n_total_bg": bg_total,
                                  "scene_cloud_cover": img.get("CLOUD_COVER"), "sun_elev_deg": img.get("SUN_ELEVATION"), "met": met})
                return measured.map(per_poly)

            n_measured = sum(1 for q in polys if q.ptype in G.MEASURED_PTYPES)
            feats = _fetch_chunked(ee, col, per_image, start, end, n_measured)
            key.write_text(json.dumps(feats))
        # ---- to rows / rejections (same thresholds as gcs_c1)
        bg_keep = str(site.get("bg_classes_override") or "")
        for ft in feats:
            p = ft["properties"]
            ts = pd.Timestamp(p["time"])
            date_iso = ts.strftime("%Y-%m-%d")
            if p.get("valid_from") and date_iso < p["valid_from"]:
                continue
            if p.get("valid_to") and date_iso > p["valid_to"]:
                continue
            n_bg, bg_tot = int(p.get("n_valid_bg") or 0), int(p.get("n_total_bg") or 0)
            n_tot = int(p.get("n_total_poly") or 0)
            relaxed = cfg.get("roof_qa", "relaxed") == "relaxed" and bg_tot > 0 and n_bg / bg_tot >= cfg.get("relaxed_bg_frac", 0.5)
            if relaxed:
                n_ok, t_poly = int(p.get("n_valid_poly_relaxed") or 0), p.get("t_poly_k_relaxed")
            else:
                n_ok, t_poly = int(p.get("n_valid_poly_strict") or 0), p.get("t_poly_k_strict")
            n_ok_strict = int(p.get("n_valid_poly_strict") or 0)
            p = dict(p, t_poly_k=t_poly)
            base = dict(site_id=site.site_id, product_id=p.get("product_id"), datetime_utc=ts.isoformat(), ptype=p["ptype"])
            if bg_tot == 0 or n_bg < cfg["min_valid_bg_px"] or n_bg / max(bg_tot, 1) < cfg["min_valid_bg_frac"]:
                rej.append(dict(base, reason="background_too_cloudy", n_valid_bg=n_bg, n_total_bg=bg_tot))
                continue
            if n_tot == 0 or n_ok < cfg["min_valid_poly_px"] or n_ok / n_tot < cfg["min_valid_poly_frac"]:
                rej.append(dict(base, reason="polygon_too_cloudy", polygon=p["name"], n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_tot))
                continue
            met = p.get("met") or {}
            sensor = "L9_C2_L2_ST" if str(p.get("spacecraft", "")).endswith("9") else "L8_C2_L2_ST"
            rows.append(dict(site_id=site.site_id, ptype=p["ptype"], polygon=p["name"], product_id=p.get("product_id"), sensor=sensor,
                             datetime_utc=ts.isoformat(), local_solar_hour=round((ts.hour + ts.minute / 60 + float(site.lon) / 15) % 24, 3),
                             t_poly_k=round(float(p["t_poly_k"]), 3), t_bg_k=round(float(p["t_bg_k"]), 3), delta_t_k=round(float(p["t_poly_k"]) - float(p["t_bg_k"]), 3),
                             t_poly_sd_k=np.nan, t_bg_sd_k=np.nan, n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_tot,
                             scene_cloud_cover=float(p.get("scene_cloud_cover", np.nan)), sun_elev_deg=float(p.get("sun_elev_deg", np.nan)),
                             qa_flags=f"C2_QA_PIXEL bg:fill|dilated|cirrus|cloud|shadow roof:{'fill|cirrus|cold' if relaxed else 'strict'} bg_classes={bg_keep or 'auto'}",
                             n_valid_poly_strict=n_ok_strict,
                             t2m_k=met.get("temperature_2m"), d2m_k=met.get("dewpoint_temperature_2m"), u10=met.get("u_component_of_wind_10m"), v10=met.get("v_component_of_wind_10m")))
    obs = pd.DataFrame(rows)
    if not obs.empty and "t2m_k" in obs:
        from . import met as MET
        d = MET.derive(obs.t2m_k.astype(float), obs.d2m_k.astype(float), obs.u10.astype(float), obs.v10.astype(float))
        for k, v in d.items():
            obs[k] = np.round(v, 4)
    print(f"[gee] {len(obs)} rows, {len(rej)} rejections", file=sys.stderr)
    return obs, pd.DataFrame(rej)
