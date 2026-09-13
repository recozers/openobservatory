"""Landsat 8 Collection 1 Level-1 thermal band from the public Google Cloud
archive (gs://gcp-public-data-landsat, anonymous HTTPS, 2013 – Jan 2022).

Why this backend exists
-----------------------
The project brief asks for Collection 2 Level-2 surface temperature via Google
Earth Engine.  GEE needs an authenticated client, and the build environment
that produced this repository had no credentials and no route to USGS,
Planetary Computer or AppEEARS.  The one thermal archive that was reachable is
Google's public Collection 1 Level-1 mirror, which stops at the end of 2021.

What is measured here is therefore *top-of-atmosphere brightness temperature*
(band 10, 10.6–11.2 µm), not emissivity- and atmosphere-corrected surface
temperature.  Because every observation is a difference against a background
annulus 0.5–2 km away under the same atmosphere, most of the atmospheric term
cancels; the emissivity term does not (a low-emissivity metal roof reads
cooler in brightness temperature than its true kinetic temperature).  This is
a known, site-constant bias absorbed by the per-site random effect in the
model, but it is one more reason to re-run with the GEE backend when possible.

Files per scene: <PRODUCT_ID>_B10.TIF (uint16 DN, 30 m grid resampled from
100 m), <PRODUCT_ID>_BQA.TIF (quality bitmask), <PRODUCT_ID>_MTL.txt.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.windows import Window, from_bounds

GCS_HTTP = "https://storage.googleapis.com/gcp-public-data-landsat"
INDEX_URL = f"{GCS_HTTP}/index.csv.gz"

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")

# Collection 1 Landsat 8 BQA bit layout
BQA_FILL = 1 << 0
BQA_TERRAIN = 1 << 1
BQA_CLOUD = 1 << 4


def _conf(bqa: np.ndarray, shift: int) -> np.ndarray:
    return (bqa >> shift) & 0b11  # 0 none, 1 low, 2 medium, 3 high


def bad_pixel_mask(bqa: np.ndarray, dn: np.ndarray, cloud_conf_min: int = 2, shadow_conf_min: int = 2, cirrus_conf_min: int = 3) -> np.ndarray:
    """True where a pixel must not be used.  Defaults: cloud bit set, cloud
    confidence ≥ medium, shadow confidence ≥ medium, cirrus confidence high,
    fill, terrain occlusion, or DN == 0."""
    bad = (bqa & BQA_FILL) > 0
    bad |= (bqa & BQA_TERRAIN) > 0
    bad |= (bqa & BQA_CLOUD) > 0
    bad |= _conf(bqa, 5) >= cloud_conf_min
    bad |= _conf(bqa, 7) >= shadow_conf_min
    bad |= _conf(bqa, 11) >= cirrus_conf_min
    bad |= dn == 0
    return bad


def ensure_index(cache_dir: Path) -> Path:
    """Landsat 8 / Tier 1 / L1TP subset of the GCS index.  Building it streams
    the full 770 MB index once; the subset (~65 MB gz) is cached."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / "landsat8_t1_index.csv.gz"
    if out.exists():
        return out
    cols = ["PRODUCT_ID", "DATE_ACQUIRED", "SENSING_TIME", "WRS_PATH", "WRS_ROW", "CLOUD_COVER", "NORTH_LAT", "SOUTH_LAT", "WEST_LON", "EAST_LON"]
    with requests.get(INDEX_URL, stream=True, timeout=600) as r, gzip.open(out, "wt") as fo:
        r.raise_for_status()
        w = csv.writer(fo)
        w.writerow(cols)
        reader = csv.DictReader((line.decode() for line in gzip.GzipFile(fileobj=r.raw)))
        for row in reader:
            if row["SPACECRAFT_ID"] == "LANDSAT_8" and row["COLLECTION_CATEGORY"] == "T1" and row["DATA_TYPE"] == "L1TP":
                w.writerow([row[c] for c in cols])
    return out


def load_index(cache_dir: Path) -> pd.DataFrame:
    p = ensure_index(cache_dir)
    df = pd.read_csv(p)
    df["SENSING_TIME"] = pd.to_datetime(df["SENSING_TIME"], utc=True, format="ISO8601")
    return df


def scenes_for_point(index: pd.DataFrame, lat: float, lon: float, start: str, end: str, max_cloud: float = 70.0) -> pd.DataFrame:
    m = (index.NORTH_LAT >= lat) & (index.SOUTH_LAT <= lat) & (index.WEST_LON <= lon) & (index.EAST_LON >= lon)
    m &= (index.DATE_ACQUIRED >= start) & (index.DATE_ACQUIRED <= end) & (index.CLOUD_COVER <= max_cloud)
    # drop antimeridian-spanning bboxes
    m &= (index.EAST_LON - index.WEST_LON) < 20
    return index[m].sort_values(["SENSING_TIME", "PRODUCT_ID"]).reset_index(drop=True)


def _list_prefixes(prefix: str) -> list[str]:
    """List 'directories' under a prefix in the public bucket via the JSON API."""
    out, token = [], None
    while True:
        params = {"prefix": prefix, "delimiter": "/", "maxResults": "500"}
        if token:
            params["pageToken"] = token
        r = requests.get("https://www.googleapis.com/storage/v1/b/gcp-public-data-landsat/o", params=params, timeout=120)
        r.raise_for_status()
        d = r.json()
        out += d.get("prefixes", [])
        token = d.get("nextPageToken")
        if not token:
            break
    return out


def supplement_index(index: pd.DataFrame, cache_dir: Path, path_rows, years) -> pd.DataFrame:
    """The GCS index.csv.gz omits some periods (all of 2018 at the time of
    writing) although the scenes exist in the bucket.  Fill such gaps by
    listing the bucket per path/row/year and reading each scene's MTL for the
    fields the index would have carried.  Results are cached."""
    cache_dir = Path(cache_dir)
    sup_path = cache_dir / "landsat8_t1_index_supplement.csv"
    sup = pd.read_csv(sup_path) if sup_path.exists() else pd.DataFrame(columns=index.columns.tolist() + ["_key"])
    if "_key" not in sup:
        sup["_key"] = ""
    new_rows = []
    for (p, r) in sorted(set(path_rows)):
        for y in years:
            key = f"{int(p):03d}{int(r):03d}_{y}"
            if (sup["_key"] == key).any():
                continue
            prefixes = _list_prefixes(f"LC08/01/{int(p):03d}/{int(r):03d}/LC08_L1TP_{int(p):03d}{int(r):03d}_{y}")
            found = 0
            for pre in prefixes:
                pid = pre.rstrip("/").rsplit("/", 1)[-1]
                if not pid.endswith("_T1"):
                    continue
                try:
                    mtl = read_mtl(scene_base(pid, p, r), cache_dir)
                except Exception:
                    continue
                try:
                    new_rows.append(dict(
                        PRODUCT_ID=pid, DATE_ACQUIRED=mtl["DATE_ACQUIRED"], SENSING_TIME=f"{mtl['DATE_ACQUIRED']}T{mtl['SCENE_CENTER_TIME']}",
                        WRS_PATH=int(p), WRS_ROW=int(r), CLOUD_COVER=float(mtl["CLOUD_COVER"]),
                        NORTH_LAT=max(float(mtl["CORNER_UL_LAT_PRODUCT"]), float(mtl["CORNER_UR_LAT_PRODUCT"])),
                        SOUTH_LAT=min(float(mtl["CORNER_LL_LAT_PRODUCT"]), float(mtl["CORNER_LR_LAT_PRODUCT"])),
                        WEST_LON=min(float(mtl["CORNER_UL_LON_PRODUCT"]), float(mtl["CORNER_LL_LON_PRODUCT"])),
                        EAST_LON=max(float(mtl["CORNER_UR_LON_PRODUCT"]), float(mtl["CORNER_LR_LON_PRODUCT"])), _key=key))
                    found += 1
                except KeyError:
                    continue
            if found == 0:  # remember that we looked, with a sentinel row
                new_rows.append(dict(PRODUCT_ID="", _key=key))
    if new_rows:
        sup = pd.concat([sup, pd.DataFrame(new_rows)], ignore_index=True)
        sup.to_csv(sup_path, index=False)
    add = sup[(sup.PRODUCT_ID.fillna("") != "") & (~sup.PRODUCT_ID.isin(index.PRODUCT_ID))].drop(columns=["_key"])
    if add.empty:
        return index
    add = add.copy()
    add["SENSING_TIME"] = pd.to_datetime(add["SENSING_TIME"], utc=True, format="ISO8601")
    for c in ("WRS_PATH", "WRS_ROW"):
        add[c] = add[c].astype(int)
    return pd.concat([index, add[index.columns]], ignore_index=True)


def scene_base(product_id: str, path: int, row: int) -> str:
    return f"{GCS_HTTP}/LC08/01/{int(path):03d}/{int(row):03d}/{product_id}/{product_id}"


def read_mtl(base: str, cache_dir: Path) -> dict:
    cache = Path(cache_dir) / "mtl"
    cache.mkdir(parents=True, exist_ok=True)
    pid = base.rsplit("/", 1)[-1]
    key = cache / f"{pid}.json"
    if key.exists():
        return json.loads(key.read_text())
    r = requests.get(base + "_MTL.txt", timeout=120)
    r.raise_for_status()
    d = {}
    for line in r.text.splitlines():
        m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*\"?([^\"]*)\"?\s*$", line)
        if m:
            d[m.group(1)] = m.group(2)
    key.write_text(json.dumps(d))
    return d


def brightness_temperature(dn: np.ndarray, mtl: dict) -> np.ndarray:
    ml = float(mtl.get("RADIANCE_MULT_BAND_10", 3.3420e-4))
    al = float(mtl.get("RADIANCE_ADD_BAND_10", 0.1))
    k1 = float(mtl.get("K1_CONSTANT_BAND_10", 774.8853))
    k2 = float(mtl.get("K2_CONSTANT_BAND_10", 1321.0789))
    L = ml * dn.astype(np.float64) + al
    with np.errstate(divide="ignore", invalid="ignore"):
        bt = k2 / np.log(k1 / L + 1.0)
    bt[dn == 0] = np.nan
    return bt


def read_scene_window(base: str, bounds_wgs84: tuple, cache_dir: Path, pad_px: int = 2):
    """Read B10 and BQA over ``bounds_wgs84`` (minx, miny, maxx, maxy in
    EPSG:4326).  Returns (dn, bqa, transform, crs).  Raw windows are cached as
    .npz so that re-running with different polygons or thresholds is offline."""
    from pyproj import Transformer
    from rasterio.warp import transform_bounds

    cache = Path(cache_dir) / "windows"
    cache.mkdir(parents=True, exist_ok=True)
    pid = base.rsplit("/", 1)[-1]
    tag = "_".join(f"{v:.4f}" for v in bounds_wgs84)
    key = cache / f"{pid}_{tag}.npz"
    if key.exists():
        z = np.load(key, allow_pickle=True)
        tr = rasterio.Affine(*[float(v) for v in z["transform"][:6]])
        return z["dn"], z["bqa"], tr, str(z["crs"])
    with rasterio.open("/vsicurl/" + base + "_B10.TIF") as ds:
        bx = transform_bounds("EPSG:4326", ds.crs, *bounds_wgs84, densify_pts=5)
        win = from_bounds(*bx, transform=ds.transform)
        win = Window(int(np.floor(win.col_off)) - pad_px, int(np.floor(win.row_off)) - pad_px,
                     int(np.ceil(win.width)) + 2 * pad_px, int(np.ceil(win.height)) + 2 * pad_px)
        dn = ds.read(1, window=win, boundless=True, fill_value=0)
        tr = ds.window_transform(win)
        crs = ds.crs.to_string()
    with rasterio.open("/vsicurl/" + base + "_BQA.TIF") as ds:
        bqa = ds.read(1, window=win, boundless=True, fill_value=1)
    np.savez_compressed(key, dn=dn, bqa=bqa, transform=np.array([tr.a, tr.b, tr.c, tr.d, tr.e, tr.f]), crs=np.array(crs))
    return dn, bqa, tr, crs


def scene_crs(base: str) -> str:
    with rasterio.open("/vsicurl/" + base + "_B10.TIF") as ds:
        return ds.crs.to_string()
