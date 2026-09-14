"""Replay sourced monthly water records; preserve meters and flow boundaries separately.

python tools/water_monthly.py                 # validate checked-in CSV
python tools/water_monthly.py --rebuild       # reproduce CSV from source table extracts

Source extracts retain the numeric tables and source URL/hash. They do not blend the
municipality's delivery meter with the customer's purchase meter or subtract returns.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AF_TO_ML = Decimal('1.23348183754752')  # international foot: 43560 * 0.3048**3 / 1000
FIELDS = ['series_id','site_id','city','month','metric','volume_ml','reported_value','reported_unit',
          'method','source_url','source_system_id','source_record_id','source_sha256','preferred','notes']


def cells(row):
    return [re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', x))).strip()
            for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.S | re.I)]


def extract_table(document, record_id):
    # Record identity precedes its monthly table in the published Utah layout.
    match = re.search(r'<table\b[^>]*\bid=["\']' + re.escape(record_id) + r'["\']', document, re.I)
    if not match:
        raise ValueError(f'Missing source record {record_id}')
    section = document[match.start():]
    table = re.search(r'<table\b[^>]*class=["\']table4["\'][^>]*>.*?</table>', section, re.I | re.S)
    if not table:
        raise ValueError('Missing monthly table')
    return table.group()


def parse_table(table):
    parsed = [cells(row) for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table, re.S | re.I)]
    if not parsed or parsed[0][:13] != ['Year','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']:
        raise ValueError('Unexpected monthly columns')
    if 'Acre Feet' not in parsed[0][13]:
        raise ValueError('Unexpected water units')
    years = set()
    result = []
    for row in parsed[1:]:
        if len(row) != 15 or not re.fullmatch(r'\d{4}', row[0]) or row[0] in years:
            raise ValueError('Malformed or duplicate water year')
        years.add(row[0])
        values = [None if x in ('','--') else Decimal(x.replace(',','')) for x in row[1:14]]
        if any(v is not None and (not v.is_finite() or v < 0) for v in values):
            raise ValueError('Invalid water volume')
        monthly, annual = values[:12], values[12]
        # Displayed two-decimal months and annual totals can differ by rounding.
        if all(v is not None for v in monthly) and annual is not None and abs(sum(monthly) - annual) > Decimal('.065'):
            raise ValueError('Monthly water volumes do not reconcile with annual total')
        result.extend(dict(month=f'{row[0]}-{m:02}', reported_value='' if v is None else str(v),
                           volume_ml='' if v is None else str((v * AF_TO_ML).quantize(Decimal('.000001'))),
                           method=row[14] or 'not stated') for m,v in enumerate(monthly,1))
    if not result:
        raise ValueError('No monthly water records')
    return result


def rebuild(root=ROOT):
    manifest = json.loads((root / 'data/water_sources/manifest.json').read_text())
    output = []
    for entry in manifest['sources']:
        table = (root / entry['file']).read_bytes()
        if hashlib.sha256(table).hexdigest() != entry['table_sha256']:
            raise ValueError('Water source table hash mismatch')
        for row in parse_table(table.decode()):
            output.append(dict(row, **{k: entry[k] for k in FIELDS if k in entry}, reported_unit='acre_feet'))
    output.sort(key=lambda r: (r['site_id'],r['series_id'],r['month']))
    with (root / 'data/water_monthly.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n'); writer.writeheader(); writer.writerows(output)
    return output


def read(root=ROOT):
    path = root / 'data/water_monthly.csv'
    if not path.exists():
        return []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    seen, preferred = set(), set()
    for r in rows:
        key = (r['site_id'],r['series_id'],r['month'])
        if key in seen or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', r['month']):
            raise ValueError('Duplicate or invalid water month')
        seen.add(key)
        if not r['source_url'].startswith('https://') or not r['source_sha256'] or r['reported_unit'] != 'acre_feet':
            raise ValueError('Missing water provenance or unsupported units')
        value, ml = r['reported_value'], r['volume_ml']
        if bool(value) != bool(ml):
            raise ValueError('Missing water conversion')
        if value:
            v, converted = Decimal(value), Decimal(ml)
            if not v.is_finite() or v < 0 or not converted.is_finite() or abs(v * AF_TO_ML - converted) > Decimal('.000001'):
                raise ValueError('Invalid water volume or conversion')
        if r['preferred'] not in ('yes','no'):
            raise ValueError('Invalid water display selection')
        if r['preferred'] == 'yes':
            pkey = (r['site_id'], r['month'])
            if pkey in preferred or r['metric'] != 'municipal_delivery':
                raise ValueError('Only one municipal delivery series may be preferred')
            preferred.add(pkey)
    return rows


def for_site(site_id, root=ROOT):
    return [dict(month=r['month'],series_id=r['series_id'],metric=r['metric'],
                 volume_ml=float(r['volume_ml']) if r['volume_ml'] else None,method=r['method'],
                 preferred=r['preferred']=='yes',source_url=r['source_url'],notes=r['notes'])
            for r in read(root) if r['site_id']==site_id]


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--rebuild',action='store_true'); args=ap.parse_args()
    if args.rebuild: rebuild()
    rows=read()
    print(f'Validated {len(rows)} monthly water records for {len(set(r["site_id"] for r in rows))} sites')

if __name__ == '__main__': main()
