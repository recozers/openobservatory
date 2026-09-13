"""ECOSTRESS backend: night-time and diurnal thermal at 70 m.

Product: ECO_L2T_LSTE v002 (tiled land surface temperature and emissivity, 70 m,
UTM tiles), on the LP DAAC Earthdata cloud.  Granules are found through NASA's
CMR by point and time (no login needed); the tile files are cloud-optimised
GeoTIFFs read with HTTP range requests and an Earthdata Login bearer token
(`EARTHDATA_TOKEN`).  Only the window around each site is read, and every
window is cached under data/cache/ecostress/<site>/, so re-runs are offline.

Why this backend exists: every Landsat frame is a ~10:30 daytime frame, and the
daytime anomaly of a data-centre roof is dominated by albedo and insolation.
ECOSTRESS flies on the ISS, so its overpass time drifts through the whole day
and night; roughly a third of granules over the US sites are night passes.
The ISS orbit limits coverage to about 52 N-52 S (Lulea has no data).

Output rows use the same schema as the other backends (sensor
`ECOSTRESS_L2T_LSTE_v002`), plus `view_zenith_deg` and `day_night`, so model.py
and build_site.py need no changes.  `scene_cloud_cover` is the cloud fraction
of the read window in percent, since the granule metadata carries none.

Masking: LST pixels are bad when the QC mandatory-QA bits (bits 0-1) are 2
(cloud) or 3 (missing), the cloud mask is set, or LST is non-finite / outside
200-350 K.  Unlike Landsat's CFMask, the ECOSTRESS cloud test is a thermal
and spatial test on the 70 m grid and is not fooled by bright roofs in the
same way, but the relaxed-roof option from the GEE backend is kept: when the
background ring is at least `relaxed_bg_frac` clear, roof pixels are kept unless
they are non-finite or more than `roof_cold_k` colder than the clear background.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds, Window
from shapely.geometry import box

from . import geom as G
from .worldcover import worldcover_on_grid

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
COLLECTION = "C2076090826-LPCLOUD"  # ECO_L2T_LSTE v002
SENSOR = "ECOSTRESS_L2T_LSTE_v002"
BANDS = ("LST", "QC", "cloud", "view_zenith")


# --------------------------------------------------------------------------
# access
# --------------------------------------------------------------------------

def token() -> str:
    t = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not t:
        raise RuntimeError("EARTHDATA_TOKEN is not set: create an Earthdata Login token and put it in .env")
    return t


def gdal_env(cache_dir: Path) -> rasterio.Env:
    # no Authorization header here: files are opened through the signed CloudFront URL that resolve_url() obtains
    return rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                        GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", GDAL_HTTP_TIMEOUT="120")


def resolve_url(url: str) -> str:
    """LP DAAC answers an authenticated GET with a 303 to a signed CloudFront URL.  GDAL's own
    handling of that redirect fails (it probes with HEAD and forwards the header), so the
    redirect is resolved here and GDAL reads the signed URL, which needs no header."""
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {token()}", "Range": "bytes=0-0"}, allow_redirects=False, timeout=90)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                return r.headers["Location"]
            if r.status_code in (200, 206):
                return url
            if r.status_code in (401, 403):
                raise PermissionError(f"Earthdata rejected the token ({r.status_code}) for {url[-60:]}")
        except requests.RequestException as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise IOError(f"could not resolve {url[-60:]}")


# --------------------------------------------------------------------------
# catalogue
# --------------------------------------------------------------------------

def search_granules(site_id: str, lat: float, lon: float, start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    """All L2T LSTE granules whose tile contains the point, with per-band URLs.
    Cached per site and date range (CMR is public; no token needed)."""
    key = Path(cache_dir) / "ecostress" / f"cmr_{site_id}_{start}_{end}.json"
    if key.exists():
        return pd.DataFrame(json.loads(key.read_text()))
    rows, page = [], 1
    while True:
        r = requests.get(CMR, params={"collection_concept_id": COLLECTION, "point": f"{lon},{lat}",
                                      "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z", "page_size": 2000, "page_num": page,
                                      "sort_key": "start_date"}, timeout=180)
        r.raise_for_status()
        entries = r.json()["feed"]["entry"]
        if not entries:
            break
        for e in entries:
            urls = {}
            for l in e.get("links", []):
                h = l.get("href", "")
                if h.startswith("https://") and h.endswith(".tif"):
                    for b in BANDS:
                        if h.endswith(f"_{b}.tif"):
                            urls[b] = h
            if not all(b in urls for b in BANDS):
                continue
            parts = e["title"].split("_")
            rows.append(dict(granule=e["title"], time_start=e["time_start"], day_night=e.get("day_night_flag", ""),
                             tile=parts[5] if len(parts) > 5 else "", orbit=parts[3] if len(parts) > 3 else "", **{f"url_{b}": urls[b] for b in BANDS}))
        if len(entries) < 2000:
            break
        page += 1
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(json.dumps(rows))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def _read_window(url: str, bounds_wgs84, pad_px: int = 2):
    with rasterio.open(f"/vsicurl/{resolve_url(url)}") as ds:
        b = transform_bounds("EPSG:4326", ds.crs, *bounds_wgs84, densify_pts=5)
        w = from_bounds(*b, ds.transform).round_offsets().round_lengths()
        col0 = max(int(w.col_off) - pad_px, 0)
        row0 = max(int(w.row_off) - pad_px, 0)
        col1 = min(int(w.col_off + w.width) + pad_px, ds.width)
        row1 = min(int(w.row_off + w.height) + pad_px, ds.height)
        if col1 <= col0 or row1 <= row0:
            return None, None, ds.crs, ds.nodata, ds.scales[0] if ds.scales else 1.0
        win = Window(col0, row0, col1 - col0, row1 - row0)
        arr = ds.read(1, window=win)
        return arr, ds.window_transform(win), ds.crs, ds.nodata, (ds.scales[0] if ds.scales else 1.0)


def _to_kelvin(raw: np.ndarray, nodata, scale) -> np.ndarray:
    if raw.dtype.kind == "f":
        lst = raw.astype(np.float32)
        if nodata is not None and np.isfinite(nodata):
            lst[raw == nodata] = np.nan
    else:  # integer product (v001 style): 0 = fill, scale to Kelvin
        lst = raw.astype(np.float32) * (scale if scale not in (None, 0, 1.0) else 0.02)
        lst[raw == (nodata if nodata is not None else 0)] = np.nan
    lst[(lst < 200) | (lst > 350)] = np.nan
    return lst


def load_frame(site_id: str, gran, bounds_wgs84, cache_dir: Path):
    """LST (K, NaN where invalid), QC, cloud, mean view zenith, transform, crs for one granule window.
    LST is read first; if the window holds no valid pixel (outside the swath, or fully cloudy)
    the other bands are not fetched."""
    from rasterio.transform import Affine
    key = Path(cache_dir) / "ecostress" / site_id / f"{gran.granule}.npz"
    if key.exists():
        z = np.load(key, allow_pickle=False)
        return z["lst"], z["qc"], z["cloud"], float(z["vz"]), Affine(*z["tr"]), str(z["crs"])
    with gdal_env(cache_dir):
        lst_raw, tr, crs, nodata, scale = _read_window(gran.url_LST, bounds_wgs84)
        if lst_raw is None:
            raise ValueError("window outside tile")
        lst = _to_kelvin(lst_raw, nodata, scale)
        if np.isfinite(lst).any():
            qc, _, _, _, _ = _read_window(gran.url_QC, bounds_wgs84)
            cloud, _, _, _, _ = _read_window(gran.url_cloud, bounds_wgs84)
            vz, _, _, vz_nodata, vz_scale = _read_window(gran.url_view_zenith, bounds_wgs84)
            qc = qc.astype(np.uint16)
            cloud = (cloud > 0).astype(np.uint8)
            vzf = vz.astype(np.float32)
            if vz_nodata is not None:
                vzf[vz == vz_nodata] = np.nan
            if vz_scale not in (None, 0, 1.0):
                vzf = vzf * vz_scale
            vz_mean = float(np.nanmean(vzf)) if np.isfinite(vzf).any() else float("nan")
        else:
            qc = np.full(lst.shape, 3, np.uint16)
            cloud = np.zeros(lst.shape, np.uint8)
            vz_mean = float("nan")
    key.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(key, lst=lst, qc=qc, cloud=cloud, vz=vz_mean, tr=np.array((tr.a, tr.b, tr.c, tr.d, tr.e, tr.f)), crs=np.array(crs.to_string()))
    return lst, qc, cloud, vz_mean, tr, crs.to_string()


def bad_pixel_mask(lst: np.ndarray, qc: np.ndarray, cloud: np.ndarray) -> np.ndarray:
    mandatory = qc & 0b11  # 0 best, 1 nominal, 2 cloud, 3 missing
    return (mandatory >= 2) | (cloud > 0) | ~np.isfinite(lst)


# --------------------------------------------------------------------------
# solar geometry (NOAA approximation; negative elevation at night)
# --------------------------------------------------------------------------

def solar_elevation_deg(ts_utc: pd.Timestamp, lat: float, lon: float) -> float:
    doy = ts_utc.dayofyear
    hour = ts_utc.hour + ts_utc.minute / 60 + ts_utc.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hour * 60 + eqtime + 4 * lon
    ha = math.radians(tst / 4 - 180)
    lat_r = math.radians(lat)
    cos_zen = math.sin(lat_r) * math.sin(decl) + math.cos(lat_r) * math.cos(decl) * math.cos(ha)
    return 90.0 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zen))))


# --------------------------------------------------------------------------
# per-granule measurement (same logic and thresholds as the Landsat backends)
# --------------------------------------------------------------------------

def process_granule(site, polys, gran, cache_dir, cfg, bg_classes):
    ts = pd.Timestamp(gran.time_start)
    ts = (ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")).floor("s")  # whole seconds, like the other backends
    date_iso = ts.strftime("%Y-%m-%d")
    rows, rej = [], []

    def reject(ptype, reason, **kw):
        rej.append(dict(site_id=site.site_id, product_id=gran.granule, datetime_utc=ts.isoformat(), ptype=ptype, reason=reason, **kw))

    crs_local = G.local_utm_crs(site.lon, site.lat)
    ann_local = G.annulus_geometry(polys, crs_local, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
    bbox_wgs = G.to_crs(box(*ann_local.bounds), crs_local, "EPSG:4326").bounds
    try:
        lst, qc, cloud, vz, tr, crs = load_frame(site.site_id, gran, bbox_wgs, cache_dir)
    except Exception as e:
        reject("all", f"read_error:{type(e).__name__}:{str(e)[:80]}")
        return rows, rej
    shape = lst.shape
    if not np.isfinite(lst).any():
        reject("all", "no_valid_lst_in_window")
        return rows, rej
    bad = bad_pixel_mask(lst, qc, cloud)
    window_cloud_pct = float(100.0 * (cloud > 0).mean())

    ann = G.annulus_geometry(polys, crs, cfg["annulus_r_in_m"], cfg["annulus_r_out_m"])
    ann_mask = G.rasterize_mask(ann, tr, shape)
    wc = worldcover_on_grid(site.lat, site.lon, crs, tr, shape, cache_dir)
    lc_ok = np.isin(wc, bg_classes)
    bg_total = int((ann_mask & lc_ok).sum())
    if bg_total == 0:
        reject("all", "annulus_has_no_eligible_landcover")
        return rows, rej
    bg_ok = ann_mask & lc_ok & ~bad
    n_bg = int(bg_ok.sum())
    bg_frac = n_bg / bg_total
    if n_bg < cfg["min_valid_bg_px"] or bg_frac < cfg["min_valid_bg_frac"]:
        reject("all", "background_too_cloudy", n_valid_bg=n_bg, n_total_bg=bg_total)
        return rows, rej
    t_bg = float(np.nanmean(lst[bg_ok]))
    t_bg_sd = float(np.nanstd(lst[bg_ok]))

    relaxed = cfg.get("roof_qa", "relaxed") == "relaxed" and bg_frac >= cfg.get("relaxed_bg_frac", 0.5)
    roof_bad = (~np.isfinite(lst)) | (lst < t_bg - cfg.get("roof_cold_k", 10.0)) if relaxed else bad
    sun = solar_elevation_deg(ts, float(site.lat), float(site.lon))
    day_night = str(getattr(gran, "day_night", "") or ("DAY" if sun > 0 else "NIGHT"))

    for p in polys:
        if p.ptype not in G.MEASURED_PTYPES or not p.valid_on(date_iso):
            continue
        g = G.to_crs(p.geom_wgs84, "EPSG:4326", crs)
        m = G.rasterize_mask(g, tr, shape)
        n_tot = int(m.sum())
        if n_tot == 0:
            reject(p.ptype, "polygon_smaller_than_pixel", polygon=p.name)
            continue
        ok = m & ~roof_bad
        n_ok = int(ok.sum())
        n_ok_strict = int((m & ~bad).sum())
        if n_ok < cfg["min_valid_poly_px"] or n_ok / n_tot < cfg["min_valid_poly_frac"]:
            reject(p.ptype, "polygon_too_cloudy", polygon=p.name, n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_total)
            continue
        t_poly = float(np.nanmean(lst[ok]))
        rows.append(dict(
            site_id=site.site_id, ptype=p.ptype, polygon=p.name, product_id=gran.granule, sensor=SENSOR,
            datetime_utc=ts.isoformat(), local_solar_hour=round((ts.hour + ts.minute / 60 + ts.second / 3600 + float(site.lon) / 15.0) % 24.0, 3),
            t_poly_k=round(t_poly, 3), t_bg_k=round(t_bg, 3), delta_t_k=round(t_poly - t_bg, 3),
            t_poly_sd_k=round(float(np.nanstd(lst[ok])), 3), t_bg_sd_k=round(t_bg_sd, 3),
            n_valid_poly=n_ok, n_total_poly=n_tot, n_valid_bg=n_bg, n_total_bg=bg_total, n_valid_poly_strict=n_ok_strict,
            scene_cloud_cover=round(window_cloud_pct, 2), sun_elev_deg=round(sun, 3),
            view_zenith_deg=round(vz, 2) if vz == vz else np.nan, day_night=day_night,
            qa_flags=f"ECO_QC_mandatory>=2|cloud_mask roof:{'finite|cold' if relaxed else 'strict'} bg_classes={','.join(map(str, bg_classes))}",
        ))
    return rows, rej


def run_ecostress(sites: pd.DataFrame, polys_by_site: dict, cache_dir, start: str, end: str, cfg: dict, workers: int, bg_class_fn):
    """bg_class_fn(site, polys, cache_dir, cfg) -> list of WorldCover classes (shared with the other backends)."""
    cache_dir = Path(cache_dir)
    token()  # fail early if missing
    all_rows, all_rej = [], []
    for _, site in sites.iterrows():
        polys = polys_by_site.get(site.site_id)
        if not polys:
            print(f"[{site.site_id}] no polygons — skipped", file=sys.stderr)
            continue
        # sites.csv obs_start/obs_end describe the Landsat C1 build's window and are stale for this backend:
        # the command-line range is authoritative (same convention as the GEE backend)
        s0, s1 = start, end
        grans = search_granules(site.site_id, float(site.lat), float(site.lon), s0, s1, cache_dir)
        if grans.empty:
            print(f"[{site.site_id}] no ECOSTRESS granules {s0}..{s1} (outside ISS coverage or no data)", file=sys.stderr)
            continue
        bg_classes = bg_class_fn(site, polys, cache_dir, cfg)
        t0 = time.time()
        print(f"[{site.site_id}] {len(grans)} granules {s0}..{s1} ({(grans.day_night == 'NIGHT').sum()} night); background classes {bg_classes}", file=sys.stderr)
        rows_site, rej_site = [], []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(process_granule, site, polys, gr, cache_dir, cfg, bg_classes) for gr in grans.itertuples(index=False)]
            for i, f in enumerate(as_completed(futs)):
                r, j = f.result()
                rows_site += r
                rej_site += j
                if (i + 1) % 100 == 0:
                    print(f"[{site.site_id}] {i+1}/{len(grans)} granules, {len(rows_site)} rows so far ({time.time()-t0:.0f}s)", file=sys.stderr)
        # the same overpass can appear in two adjacent tiles: keep, per polygon and acquisition, the tile with most valid pixels
        if rows_site:
            df = pd.DataFrame(rows_site)
            df["_t"] = pd.to_datetime(df.datetime_utc, utc=True, format="ISO8601").dt.floor("min")
            df = df.sort_values("n_valid_poly", ascending=False).drop_duplicates(["site_id", "polygon", "_t"]).drop(columns="_t")
            rows_site = df.to_dict("records")
        all_rows += rows_site
        all_rej += rej_site
        print(f"[{site.site_id}] done: {len(rows_site)} rows, {len(rej_site)} rejections in {time.time()-t0:.0f}s", file=sys.stderr)
    return pd.DataFrame(all_rows), pd.DataFrame(all_rej)
