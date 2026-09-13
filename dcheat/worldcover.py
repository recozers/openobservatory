"""ESA WorldCover 10 m (2021, v200) for masking the background annulus.

Public bucket, anonymous HTTPS, Cloud-Optimised GeoTIFFs in 3°×3° tiles.
Classes: 10 tree, 20 shrub, 30 grass, 40 crop, 50 built-up, 60 bare, 70 snow,
80 water, 90 wetland, 95 mangrove, 100 moss/lichen.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"
CLASS_NAMES = {10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built", 60: "bare", 70: "snow", 80: "water", 90: "wetland", 95: "mangrove", 100: "moss"}
EXCLUDE_ALWAYS = {0, 50, 70, 80, 90, 95}  # nodata, built-up, snow, water, wetland, mangrove

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


def tile_name(lat: float, lon: float) -> str:
    lat0 = int(math.floor(lat / 3.0) * 3)
    lon0 = int(math.floor(lon / 3.0) * 3)
    ns = "N" if lat0 >= 0 else "S"
    ew = "E" if lon0 >= 0 else "W"
    return f"ESA_WorldCover_10m_2021_v200_{ns}{abs(lat0):02d}{ew}{abs(lon0):03d}_Map.tif"


def worldcover_on_grid(lat: float, lon: float, dst_crs, dst_transform, dst_shape, cache_dir: Path) -> np.ndarray:
    """Return WorldCover classes resampled (mode) onto a target grid.  The raw
    4326 window is cached on disk per site so re-runs are offline."""
    cache_dir = Path(cache_dir) / "worldcover"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_dir / f"wc_{lat:.4f}_{lon:.4f}.tif"
    if not key.exists():
        # window: ±0.06° (~6 km) around the site, enough for a 2 km annulus
        url = f"/vsicurl/{BASE}/{tile_name(lat, lon)}"
        with rasterio.open(url) as src:
            win = rasterio.windows.from_bounds(lon - 0.06, lat - 0.06, lon + 0.06, lat + 0.06, src.transform)
            win = win.round_offsets().round_lengths()
            arr = src.read(1, window=win)
            tr = src.window_transform(win)
            prof = src.profile.copy()
            prof.update(width=arr.shape[1], height=arr.shape[0], transform=tr, driver="GTiff", compress="deflate")
            prof.pop("blockxsize", None); prof.pop("blockysize", None); prof["tiled"] = False
            with rasterio.open(key, "w", **prof) as dst:
                dst.write(arr, 1)
    with rasterio.open(key) as src:
        out = np.zeros(dst_shape, dtype="uint8")
        reproject(
            source=src.read(1), destination=out,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=dst_transform, dst_crs=dst_crs,
            resampling=Resampling.mode, dst_nodata=0,
        )
    return out
