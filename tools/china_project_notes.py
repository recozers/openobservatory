"""Reapply the dated Chinese project-document search notes without changing capacity.

    python tools/china_project_notes.py

Only this script's bracketed suffix is replaced. Figures for separate substations
stay in the document registry until a campus and its hall polygons are matched.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ' [Astra project search '


def main():
    registry = json.loads((ROOT / 'data/china_project_documents.json').read_text())
    notes = registry['site_notes']
    path = ROOT / 'data/sites.csv'
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    assert set(notes) <= {r['site_id'] for r in rows}
    for row in rows:
        if row['site_id'] in notes:
            row['notes'] = row['notes'].split(MARKER)[0] + MARKER + registry['searched_on'] + '] ' + notes[row['site_id']]
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'Updated {len(notes)} sourced search notes; no capacity or polygon changes.')


if __name__ == '__main__':
    main()
