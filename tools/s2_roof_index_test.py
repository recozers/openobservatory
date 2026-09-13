"""Test the proposed dark-roof rule without promoting it into production dates.

    python tools/s2_roof_index_test.py --extract hyperion_la
    python tools/s2_roof_index_test.py --extract stargate_abilene
    python tools/s2_roof_index_test.py

One site per extraction process. The index rule is NDVI < 0.15 and NDBI
(or BSI) at least 0.08 above the first six valid months, for two consecutive
calendar months. A1's public brightness timeline is not changed by this test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dcheat import geom as G
from dcheat.gee import _ee, _fetch_chunked
from tools.s2_roof_timeline import roof_on_month

SITES = ['hyperion_la', 'stargate_abilene', 'cn_horinger_cloud_valley', 'cn_zhangbei_alibaba', 'cn_ulanqab_park']
BANDS = ['bright', 'ndvi', 'ndbi', 'bsi']


def index_event(series, index='ndbi_mean', jump=.08):
    data = series[['ndvi_mean', index]].dropna().sort_index()
    if len(data) < 8:
        return 'not_yet'
    baseline = data[index].iloc[:6].median()
    test = (data.ndvi_mean < .15) & (data[index] >= baseline + jump)
    for a, b in zip(data.index, data.index[1:]):
        if pd.Period(a, freq='M') + 1 == pd.Period(b, freq='M') and test.loc[a] and test.loc[b]:
            return str(a)
    return 'not_yet'


def extract(sid, end):
    ee = _ee()
    path = ROOT / 'data/polygons' / f'{sid}.geojson'
    polygons = [p for p in G.load_site_polygons(path) if p.ptype == 'hall']
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry(G.mapping(p.geom_wgs84)), {'name': p.name}) for p in polygons])
    def clean(image):
        scl = image.select('SCL')
        ok = scl.neq(0).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
        img = image.multiply(.0001).updateMask(ok)
        bright = img.select(['B2', 'B3', 'B4']).reduce(ee.Reducer.mean()).rename('bright')
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi = img.normalizedDifference(['B11', 'B8']).rename('ndbi')
        bsi = img.expression('((s+r)-(n+b))/((s+r)+(n+b))', {'s': img.select('B11'), 'r': img.select('B4'), 'n': img.select('B8'), 'b': img.select('B2')}).rename('bsi')
        return bright.addBands([ndvi, ndbi, bsi])
    rows = []
    for year in range(2018, int(end[:4]) + 1):
        start_y, end_y = f'{year}-01-01', min(f'{year+1}-01-01', end)
        if start_y >= end_y:
            continue
        digest = hashlib.sha256(path.read_bytes() + f'{start_y}:{end_y}:indices-v1'.encode()).hexdigest()
        cache = ROOT / 'data/cache/roof_indices' / f'{digest}.json'
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists():
            part = json.loads(cache.read_text())
        else:
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(fc.geometry())
                          .filterDate(start_y, end_y).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60)))
            for attempt in range(4):
                try:
                    part = _fetch_chunked(ee, collection, lambda img: clean(img).reduceRegions(fc, ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True), 10)
                                          .map(lambda f: ee.Feature(None, f.toDictionary()).set('d', img.date().format('YYYY-MM-dd'))),
                                          start_y, end_y, len(polygons), limit=1000)
                    break
                except ee.EEException as exc:
                    if attempt == 3 or 'concurrent aggregations' not in str(exc).lower():
                        raise
                    time.sleep(2 ** (attempt + 1))
            cache.write_text(json.dumps(part))
        rows.extend(f['properties'] for f in part)
        print(f'{sid} {year}: {len(part)} polygon-images', file=sys.stderr)
    data = pd.DataFrame(rows)
    data = data[data.bright_count >= 10].copy()
    data['ym'] = data.d.str[:7]
    out = data.groupby(['ym', 'name'])[[b + '_mean' for b in BANDS]].median()
    out.to_csv(ROOT / 'results_s2' / f'{sid}_indices.csv')


def report():
    rows = []
    missing = []
    for sid in SITES:
        path = ROOT / 'results_s2' / f'{sid}_indices.csv'
        if not path.exists():
            missing.append(sid)
            continue
        data = pd.read_csv(path, index_col=0)
        for name, series in data.groupby('name'):
            bright = roof_on_month(series.bright_mean)
            nd, bs = index_event(series), index_event(series, 'bsi_mean')
            dates = [x for x in (bright, nd, bs) if x not in ('not_yet', 'existing')]
            combined = 'existing' if bright == 'existing' else min(dates, default='not_yet')
            rows.append(dict(site_id=sid, hall=name, brightness=bright, ndvi_ndbi=nd, ndvi_bsi=bs, combined=combined))
    result = dict(rule='NDVI < 0.15; NDBI or BSI >= first-six-month median + 0.08; two consecutive months',
                  source='COPERNICUS/S2_SR_HARMONIZED', extraction_start='2018-01-01',
                  status='experimental; not used for public roof dating', missing_sites=missing, halls=rows)
    out = ROOT / 'results_s2/roof_index_validation.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), file=sys.stderr)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--extract', choices=SITES)
    ap.add_argument('--end', default=(pd.Timestamp.utcnow() + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    args = ap.parse_args()
    if args.extract:
        extract(args.extract, args.end)
    else:
        report()


if __name__ == '__main__':
    main()
