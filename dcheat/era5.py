"""ERA5 hourly single-level fields from the NCAR/NSF mirror on AWS Open Data.

Bucket: s3://nsf-ncar-era5 (anonymous HTTPS).  Files are monthly netCDF-4 per
variable, global 0.25°, chunked (27 h × 139 lat × 279 lon), so a point read
costs one ~2 MB chunk per variable.  Extracted point slices are cached.

This is ERA5 (~31 km), not ERA5-Land (~9 km) as the project brief specifies;
ERA5-Land is only reachable through GEE / CDS, both blocked in the build
environment.  Both are far coarser than a facility, and the caveat in the brief
about reanalysis wind at the cooler inlet applies with extra force.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import fsspec
import h5py
import numpy as np
import pandas as pd

BASE = "https://nsf-ncar-era5.s3.amazonaws.com/e5.oper.an.sfc"
VARS = {
    "t2m": ("128_167_2t", "VAR_2T"),
    "d2m": ("128_168_2d", "VAR_2D"),
    "u10": ("128_165_10u", "VAR_10U"),
    "v10": ("128_166_10v", "VAR_10V"),
    "sp": ("128_134_sp", "SP"),
    "skt": ("128_235_skt", "SKT"),
}
TCHUNK = 27  # time chunk length in these files


def _file_url(var_key: str, ym: pd.Timestamp) -> str:
    code, _ = VARS[var_key]
    start = ym.replace(day=1)
    end = (start + pd.offsets.MonthEnd(0))
    return f"{BASE}/{start:%Y%m}/e5.oper.an.sfc.{code}.ll025sc.{start:%Y%m%d}00_{end:%Y%m%d}23.nc"


def grid_index(lat: float, lon: float) -> tuple[int, int]:
    li = int(round((90.0 - lat) / 0.25))
    lo = int(round((lon % 360.0) / 0.25)) % 1440
    return li, lo


class ERA5Point:
    """Cached point extraction.  Cache layout: <cache>/era5/<var>/<yyyymm>_<li>_<lo>_<chunk>.json"""

    def __init__(self, cache_dir: Path, variables=("t2m", "d2m", "u10", "v10")):
        self.cache = Path(cache_dir) / "era5"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.variables = list(variables)
        self.fs = fsspec.filesystem("https", client_kwargs={"trust_env": True}, block_size=2 ** 21)
        self._open: dict[str, h5py.File] = {}

    def _dataset(self, var_key, ym):
        url = _file_url(var_key, ym)
        if url not in self._open:
            f = self.fs.open(url, "rb")
            self._open[url] = h5py.File(f, "r")
        h = self._open[url]
        return h[VARS[var_key][1]], h["time"]

    def _slice(self, var_key: str, ym: pd.Timestamp, li: int, lo: int, chunk: int) -> np.ndarray:
        key = self.cache / var_key / f"{ym:%Y%m}_{li}_{lo}_{chunk}.json"
        if key.exists():
            return np.array(json.loads(key.read_text()), dtype=float)
        ds, _ = self._dataset(var_key, ym)
        t0, t1 = chunk * TCHUNK, min((chunk + 1) * TCHUNK, ds.shape[0])
        vals = np.asarray(ds[t0:t1, li, lo], dtype=float)
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps([float(v) for v in vals]))
        return vals

    def at(self, lat: float, lon: float, when_utc: pd.Timestamp, interpolate: bool = True) -> dict[str, float]:
        """Values at the nearest grid point, linearly interpolated in time
        between the two bracketing hours (or nearest hour if interpolate=False)."""
        when = pd.Timestamp(when_utc).tz_convert("UTC").tz_localize(None) if pd.Timestamp(when_utc).tzinfo else pd.Timestamp(when_utc)
        li, lo = grid_index(lat, lon)
        h0 = when.floor("h")
        frac = (when - h0).total_seconds() / 3600.0
        out = {}
        for var in self.variables:
            v0 = self._hour_value(var, h0, li, lo)
            if interpolate and frac > 1e-6:
                v1 = self._hour_value(var, h0 + pd.Timedelta(hours=1), li, lo)
                out[var] = (1 - frac) * v0 + frac * v1
            else:
                out[var] = v0
        return out

    def _hour_value(self, var, hour: pd.Timestamp, li, lo) -> float:
        ym = hour.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        idx = int((hour - ym).total_seconds() // 3600)
        chunk = idx // TCHUNK
        vals = self._slice(var, ym, li, lo, chunk)
        return float(vals[idx - chunk * TCHUNK])

    def close(self):
        for h in self._open.values():
            try:
                h.close()
            except Exception:
                pass
        self._open = {}
