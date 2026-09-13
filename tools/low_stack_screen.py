"""Screen eGRID gas plants for A5 without treating eGRID estimates as hourly measurements.

    python tools/low_stack_screen.py [--probe]

--probe requests one CAMPD hourly row for the full calendar year and saves a
credential-free cache. The distance screen covers eGRID power plants only;
industrial-source isolation and actual stack heights still require review.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--annual', action='store_true', help='Fetch unit-level annual totals for facilities with hourly rows')
    args = ap.parse_args()
    plants = pd.read_csv(ROOT / 'data/egrid/plants_2023.csv')
    large = plants[plants.nox_tpy >= 1000]
    gas = large[large.PLFUELCT == 'GAS'].copy()
    out, annual = [], []
    for _, row in gas.sort_values('nox_tpy', ascending=False).iterrows():
        others = large[large.ORISPL != row.ORISPL]
        a, b = np.radians(others.LAT), np.radians(others.LON)
        lat, lon = np.radians(row.LAT), np.radians(row.LON)
        d = 6371 * 2 * np.arcsin(np.sqrt(np.clip(np.sin((a-lat)/2)**2 + np.cos(a)*np.cos(lat)*np.sin((b-lon)/2)**2, 0, 1)))
        neighbor = others.loc[d.idxmin()]
        rec = dict(facility_id=int(row.ORISPL), name=row.PNAME, lat=row.LAT, lon=row.LON,
                   egrid_nox_short_tons=float(row.nox_tpy), nearest_large_power_plant=neighbor.PNAME,
                   distance_km=round(d.min(), 2), power_isolated=bool(d.min() >= 15),
                   campd_status='not_probed', sample_unit_type='', stack_class='unverified',
                   industrial_isolation='not_verified')
        if rec['power_isolated']:
            cache = ROOT / 'data/cache/campd_screen' / f'{int(row.ORISPL)}_2023.json'
            if args.probe and not cache.exists():
                response = requests.get('https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/hourly',
                    params=dict(beginDate='2023-01-01', endDate='2023-12-31', facilityId=int(row.ORISPL), page=1, perPage=1),
                    headers={'x-api-key': os.environ['EPA_API_KEY']}, timeout=120)
                if response.status_code == 200:
                    items = response.json()
                    items = items.get('items', items) if isinstance(items, dict) else items
                    result = dict(status='rows_present' if items else 'no_rows', sample=items[:1])
                else:
                    result = dict(status=f'http_{response.status_code}', sample=[])
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(result))
                time.sleep(.2)
            if cache.exists():
                result = json.loads(cache.read_text())
                rec['campd_status'] = result['status']
                if result['sample']:
                    rec['sample_unit_type'] = result['sample'][0].get('unitType', '')
        out.append(rec)
        if rec['campd_status'] == 'rows_present':
            annual_path = ROOT / 'data/cache/campd_screen' / f'{int(row.ORISPL)}_annual_2023.json'
            if args.annual and not annual_path.exists():
                response = requests.get('https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/annual',
                    params=dict(year='2023', facilityId=int(row.ORISPL), page=1, perPage=500),
                    headers={'x-api-key': os.environ['EPA_API_KEY']}, timeout=120)
                response.raise_for_status()
                annual_path.write_text(json.dumps(response.json()))
            if annual_path.exists():
                items = json.loads(annual_path.read_text())
                items = items.get('items', items) if isinstance(items, dict) else items
                if len(items) >= 500:
                    raise ValueError('Annual response needs pagination; refusing a partial total')
                annual.extend(dict(item, queried_facility_id=int(row.ORISPL)) for item in items)
        print(f"{rec['facility_id']} {rec['name']}: {rec['campd_status']}, nearest large power source {rec['distance_km']} km", file=sys.stderr)
    pd.DataFrame(out).to_csv(ROOT / 'results_no2/low_stack_screen_2023.csv', index=False)
    if annual:
        (ROOT / 'results_no2/campd_annual_screen_2023.json').write_text(json.dumps(annual, indent=2) + '\n')


if __name__ == '__main__':
    main()
