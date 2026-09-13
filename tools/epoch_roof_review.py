"""Flag brightness dates that conflict with Epoch's reported construction start.

The conflict is not resolved by choosing either source. Keep the raw satellite
date as evidence and publish an unknown roof date until imagery is reviewed.
"""
import csv
from pathlib import Path
import re

import pandas as pd

from tools.ingest_epoch import ALIASES, site_id, SOURCE


def construction_context(root):
    path = Path(root) / 'data/epoch/data_center_timelines.csv'
    if not path.exists():
        return {}
    with path.open() as f:
        rows = sorted(csv.DictReader(f), key=lambda r: r['Date'])
    first = {}
    for row in rows:
        first.setdefault(row['Data center'], row)
    out = {}
    for name, row in first.items():
        note = row['Construction status']
        if name in ALIASES or 'expansion' in note.lower():
            continue
        if re.search(r'land clearing (?:begins|and site prep begins)|first signs of site preparation|construction start', note, re.I):
            buildings = re.search(r'for Building (\d+)\b', note, re.I)
            out[site_id(name)] = dict(date=row['Date'], note=note, building_number=int(buildings.group(1)) if buildings else None, url=SOURCE)
    return out


def review(candidate, props, context):
    if not context or not re.fullmatch(r'\d{4}-\d{2}', candidate):
        return None
    if context['building_number'] is not None and props.get('epoch_building_number') != context['building_number']:
        return None
    if pd.Period(candidate, freq='M') + 1 < pd.Period(context['date'], freq='M'):
        return dict(candidate=candidate, reported_start=context['date'], source_url=context['url'],
                    reason='Brightness rise precedes reported construction/site preparation; possible soil or pre-existing roof. Manual imagery review required.')
    return None
