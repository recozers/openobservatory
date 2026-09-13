"""Bounded optical construction-candidate scan, with no prior hall mask.

    python tools/s2_candidates.py stargate_abilene

Each invocation scans one 12 km box. Sentinel-2 is reduced to 50 m before
local vectorisation; requests contain raster tiles, never huge feature lists.
Candidate shape/colour alone does not establish a data centre.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from pyproj import Transformer
import rasterio
from rasterio.features import shapes
from rasterio.merge import merge
import requests
from scipy import ndimage
from shapely.geometry import shape, mapping, box
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dcheat.gee import _ee

SITES = ['stargate_abilene', 'rainier_in', 'prometheus_oh', 'ulanqab_hub', 'zhangbei_hub']
YEARS = [2022, 2023, 2024, 2025, 2026]


def download(image, region, crs, scale, path):
    if path.exists():
        return
    forward = Transformer.from_crs('EPSG:4326', crs, always_xy=True).transform
    inverse = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform
    xmin, ymin, xmax, ymax = transform(forward, shape(region)).bounds
    xmid, ymid = (xmin+xmax)/2, (ymin+ymax)/2
    tiles = []
    for i, (xa,xb,ya,yb) in enumerate([(xmin,xmid,ymin,ymid), (xmid,xmax,ymin,ymid),
                                      (xmin,xmid,ymid,ymax), (xmid,xmax,ymid,ymax)]):
        tile = path.with_name(path.stem + f'_tile{i}.tif')
        tiles.append(tile)
        if tile.exists():
            continue
        tile_region = mapping(transform(inverse, box(xa,ya,xb,yb)))
        print(f'Downloading {path.name}, tile {i+1}/4', file=sys.stderr, flush=True)
        url = image.toFloat().getDownloadURL(dict(region=tile_region, crs=crs, scale=scale, format='GEO_TIFF'))
        response = requests.get(url, timeout=300)
        response.raise_for_status()
        temporary = tile.with_suffix('.partial')
        temporary.write_bytes(response.content)
        with rasterio.open(temporary):
            pass
        temporary.replace(tile)
    sources = [rasterio.open(tile) for tile in tiles]
    try:
        data, affine = merge(sources)
        profile = sources[0].profile.copy()
        profile.update(height=data.shape[1], width=data.shape[2], transform=affine, compress='deflate')
        with rasterio.open(path, 'w', **profile) as target:
            target.write(data)
    finally:
        for source in sources:
            source.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('site', choices=SITES)
    args = ap.parse_args()
    sites = pd.read_csv(ROOT / 'data/sites.csv').set_index('site_id')
    site = sites.loc[args.site]
    crs = f'EPSG:{32600 + int((site.lon + 180) // 6) + 1}'
    forward = Transformer.from_crs('EPSG:4326', crs, always_xy=True).transform
    inverse = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform
    x, y = forward(site.lon, site.lat)
    bounds = box(x-6000, y-6000, x+6000, y+6000)
    region_geo = mapping(transform(inverse, bounds))
    out = ROOT / 'results_discovery'
    out.mkdir(exist_ok=True)
    signature = hashlib.sha256(json.dumps([region_geo, YEARS, 'Jan01-Sep14-exclusive', 'v1']).encode()).hexdigest()[:20]
    cache = ROOT / 'data/cache/optical_discovery' / signature
    cache.mkdir(parents=True, exist_ok=True)
    index_file, rgb_file = cache / 'indices.tif', cache / 'rgb.tif'
    if not index_file.exists() or not rgb_file.exists():
        ee = _ee()
        region = ee.Geometry(region_geo)
        def clean(img):
            scl = img.select('SCL')
            mask = scl.neq(0).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
            return img.select(['B2','B3','B4','B8','B11']).multiply(.0001).updateMask(mask)
        composites, bands = {}, []
        for year in YEARS:
            # Match seasons; 2026 is incomplete. This is not a full-year comparison.
            comp = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region)
                    .filterDate(f'{year}-01-01', f'{year}-09-14').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
                    .map(clean).median().setDefaultProjection(crs, None, 10))
            composites[year] = comp
            indices = comp.select(['B2','B3','B4']).reduce(ee.Reducer.mean()).rename(f'bright_{year}')
            indices = indices.addBands(comp.normalizedDifference(['B8','B4']).rename(f'ndvi_{year}'))
            indices = indices.addBands(comp.normalizedDifference(['B11','B8']).rename(f'ndbi_{year}'))
            bands.append(indices.reduceResolution(ee.Reducer.mean(), maxPixels=256).reproject(crs, None, 50))
        image = ee.Image.cat(bands)
        download(image, region_geo, crs, 50, index_file)
        download(composites[2026].select(['B4','B3','B2']), region_geo, crs, 20, rgb_file)
    with rasterio.open(index_file) as src:
        a = src.read(masked=True).filled(np.nan)
        affine = src.transform
    base = a[:3]
    masks = []
    for k in range(1, len(YEARS)):
        current = a[k*3:k*3+3]
        masks.append(np.isfinite(current).all(axis=0) & np.isfinite(base).all(axis=0)
                     & ((base[1]-current[1]) >= .15) & (current[1] < .25)
                     & (((current[0]-base[0]) >= .08) | ((current[2]-base[2]) >= .10)))
    labels, _ = ndimage.label(masks[-1], structure=np.ones((3,3)))
    candidates = []
    for geom, label in shapes(labels.astype('int32'), mask=labels > 0, transform=affine, connectivity=8):
        poly = shape(geom)
        if not poly.is_valid:
            poly = poly.buffer(0)
        area = poly.area
        rectangularity = area / poly.minimum_rotated_rectangle.area
        if area < 30000 or rectangularity < .6:
            continue
        pixel_mask = labels == int(label)
        first = next(year for year, mask in zip(YEARS[1:], masks) if mask[pixel_mask].mean() >= .5)
        lon, lat = inverse(poly.centroid.x, poly.centroid.y)
        candidates.append(dict(lat=lat, lon=lon, area_ha=area/10000, rectangularity=rectangularity,
                               first_change_year=first, polygon=poly))
    candidates.sort(key=lambda r: -r['area_ha'])
    with rasterio.open(rgb_file) as rgb_src:
        rgb = np.moveaxis(rgb_src.read(), 0, -1)
        rgb = np.uint8(np.clip(np.nan_to_num(rgb / .35), 0, 1)**.8 * 255)
        features, rows = [], []
        for rank, rec in enumerate(candidates, 1):
            poly = rec.pop('polygon')
            chip = f'{args.site}_{rank:03d}.png'
            cx, cy = forward(rec['lon'], rec['lat'])
            px, py = ~rgb_src.transform * (cx, cy)
            # At least 1.2 km square; grow to include the candidate and a margin.
            radius = max(30, int(max(poly.bounds[2]-poly.bounds[0], poly.bounds[3]-poly.bounds[1])/40)+10)
            left, top = max(0,int(px)-radius), max(0,int(py)-radius)
            right, bottom = min(rgb.shape[1],int(px)+radius), min(rgb.shape[0],int(py)+radius)
            img = Image.fromarray(rgb[top:bottom,left:right])
            drawing = ImageDraw.Draw(img)
            for part in ([poly] if poly.geom_type == 'Polygon' else poly.geoms):
                points = [tuple(np.subtract(~rgb_src.transform * coord, (left,top))) for coord in part.exterior.coords]
                drawing.line(points, fill=(255,40,40), width=1)
            img.resize((600,600)).save(out / chip)
            rec.update(rank=rank, site_box=args.site, chip=chip, confidence='low',
                       digitised_from='Sentinel-2 deterministic 50 m change component; not a hall outline',
                       review='unreviewed construction candidate; not a data-centre classification')
            rows.append(rec)
            features.append(dict(type='Feature', geometry=mapping(transform(inverse,poly)), properties=rec.copy()))
    pd.DataFrame(rows, columns=['rank','site_box','lat','lon','area_ha','rectangularity','first_change_year','chip','confidence','digitised_from','review']).to_csv(out / f'{args.site}_candidates.csv',index=False)
    (out / f'{args.site}_candidates.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features))+'\n')
    validation = None
    known_path = ROOT / 'data/polygons' / f'{args.site}.geojson'
    if known_path.exists():
        known = json.loads(known_path.read_text())
        halls = unary_union([shape(f['geometry']) for f in known['features'] if f['properties'].get('ptype') == 'hall'])
        matches = [f['properties']['rank'] for f in features if shape(f['geometry']).intersects(halls)]
        validation = dict(known_campus_recovered=bool(matches), intersecting_ranks=matches,
                          definition='At least one candidate overlaps an independently stored hall polygon; not per-hall recall')
    metadata = dict(site_box=args.site, source='COPERNICUS/S2_SR_HARMONIZED', years=YEARS,
                    season='January 1 through September 13, same season in each year; latest year incomplete',
                    grid_m=50, rgb_grid_m=20, region=region_geo, signature=signature,
                    index_sha256=hashlib.sha256(index_file.read_bytes()).hexdigest(),
                    rule='NDVI drop >= .15, current NDVI < .25, brightness rise >= .08 OR NDBI rise >= .10; 8-connected area >= 3 ha; rectangularity >= .6',
                    first_change_definition='First sampled year with at least half the final candidate pixels meeting the rule against 2022; not a month or commissioning date',
                    count=len(rows), validation=validation, caveat='Bare soil, construction yards, roads and other industries can pass; source identity needs review.')
    (out / f'{args.site}_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2),file=sys.stderr)


if __name__ == '__main__':
    main()
