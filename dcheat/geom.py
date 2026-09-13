"""Site polygons, background annulus and rasterisation helpers.

Polygon files live in ``data/polygons/<site_id>.geojson`` (EPSG:4326).  Each
feature carries ``ptype`` in {hall, cooling, substation, campus} plus optional
``valid_from`` / ``valid_to`` dates (ISO) for buildings that appear or vanish
inside the observation window.  ``campus`` polygons are never measured; they
only widen the exclusion zone used when building the background annulus.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
from rasterio import features
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform, unary_union

MEASURED_PTYPES = ("hall", "cooling", "substation")


@dataclass
class SitePolygon:
    name: str
    ptype: str
    geom_wgs84: object  # shapely geometry in EPSG:4326
    valid_from: str | None = None
    valid_to: str | None = None
    props: dict = field(default_factory=dict)

    def valid_on(self, date_iso: str) -> bool:
        if self.valid_from and date_iso < self.valid_from:
            return False
        if self.valid_to and date_iso > self.valid_to:
            return False
        return True


def load_site_polygons(path: Path) -> list[SitePolygon]:
    with open(path) as f:
        fc = json.load(f)
    out = []
    for feat in fc["features"]:
        p = feat.get("properties", {})
        out.append(
            SitePolygon(
                name=p.get("name", p.get("ptype", "poly")),
                ptype=p["ptype"],
                geom_wgs84=shape(feat["geometry"]),
                valid_from=p.get("valid_from"),
                valid_to=p.get("valid_to"),
                props=p,
            )
        )
    return out


def to_crs(geom, crs_from, crs_to):
    tr = Transformer.from_crs(CRS.from_user_input(crs_from), CRS.from_user_input(crs_to), always_xy=True)
    return shp_transform(tr.transform, geom)


def local_utm_crs(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) // 6) + 1
    return CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)


def polygon_areas_m2(polys: list[SitePolygon], lon: float, lat: float) -> dict[str, float]:
    """Total area per ptype in a local UTM projection (metres)."""
    crs = local_utm_crs(lon, lat)
    out: dict[str, float] = {}
    for p in polys:
        g = to_crs(p.geom_wgs84, "EPSG:4326", crs)
        out[p.ptype] = out.get(p.ptype, 0.0) + g.area
    return out


def annulus_geometry(polys: list[SitePolygon], crs, r_in_m: float, r_out_m: float):
    """Ring between r_in and r_out metres around the union of all site
    polygons (including ``campus``), in the target projected CRS."""
    union = unary_union([to_crs(p.geom_wgs84, "EPSG:4326", crs) for p in polys])
    return union.buffer(r_out_m).difference(union.buffer(r_in_m))


def rasterize_mask(geom, transform, shape_hw) -> np.ndarray:
    """Boolean mask of pixels whose centre lies inside ``geom``."""
    if geom.is_empty:
        return np.zeros(shape_hw, dtype=bool)
    m = features.rasterize([(mapping(geom), 1)], out_shape=shape_hw, transform=transform, fill=0, all_touched=False, dtype="uint8")
    return m.astype(bool)


def geojson_feature(geom_wgs84, props: dict) -> dict:
    return {"type": "Feature", "properties": props, "geometry": mapping(geom_wgs84)}
