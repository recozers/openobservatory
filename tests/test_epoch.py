import csv
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

import pandas as pd

import build_status
import build_timeline_data as timeline
from tools.ingest_epoch import normalized_timeline, building_features
from tools.epoch_map_snapshot import decode
from tools.s2_roof_timeline import roof_on_month
from tools.epoch_roof_review import review


class EpochTimelineTests(unittest.TestCase):
    def rows(self):
        return [dict(zip(['Data center', 'Date', 'Power (MW)', 'IT power (MW)', 'Buildings operational', 'Construction status'], r)) for r in [
            ['Example', '2026-01-01', '0', '0', '0', 'Building'],
            ['Example', '2026-06-01', '120', '90', '1', 'Reported commissioning'],
            ['Example', '2027-01-01', '240', '180', '2', 'Forecast'],
        ]]

    def test_units_zero_intervals_and_projections(self):
        rows = normalized_timeline('Example', self.rows(), date(2026, 9, 13))
        self.assertEqual(len(rows), 6)
        data = pd.DataFrame(rows)
        self.assertEqual(timeline.cap_in_force(data, 'epoch_example', '2026-09-13', 1.2), (90.0, 'A2', 'it_reported'))
        self.assertEqual(timeline.cap_in_force(data.iloc[::-1], 'epoch_example', '2026-09-13', 1.2)[0], 90)
        self.assertEqual(timeline.cap_in_force(data, 'epoch_example', '2026-02-01', 1.2)[0], 0)
        self.assertEqual(data.iloc[0].valid_to, '2026-05-31')
        self.assertTrue(all('projection' in r['source'] for r in rows if r['valid_from'] == '2027-01-01'))
        self.assertTrue(all(r['url'].startswith('https://epoch.ai/') for r in rows))

    def test_missing_it_uses_facility_conversion(self):
        rows = self.rows()
        for row in rows:
            row['IT power (MW)'] = ''
        data = pd.DataFrame(normalized_timeline('Example', rows, date(2026, 9, 13)))
        self.assertEqual(timeline.cap_in_force(data, 'epoch_example', '2026-09-13', 1.2)[0], 100)

    def test_invalid_and_duplicate_values_fail(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            normalized_timeline('Example', rows + [rows[0]], date(2026, 9, 13))
        rows[0]['IT power (MW)'] = 'NaN'
        with self.assertRaises(ValueError):
            normalized_timeline('Example', rows, date(2026, 9, 13))

    def test_annotations_preserve_planning_and_provenance(self):
        source = {'shapes': {'features': [{'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[0,0],[.001,0],[.001,.001],[0,.001],[0,0]]]},
                                         'properties': {'type': 'Building', 'complete': 0}}]}}
        props = building_features('Example', source, 'https://epoch.ai/data/ai-data-centers/map')[0]['properties']
        self.assertTrue(props['roof_date_required'])
        self.assertEqual(props['epoch_complete'], 0)
        self.assertNotIn('valid_from', props)
        self.assertIn('Epoch AI', props['digitised_from'])
        self.assertEqual(decode([0, {'x': [1, [[0, 1], [0]]]}]), {'x': [1, None]})


class RoofTests(unittest.TestCase):
    def test_conflicting_construction_date_is_flagged_not_replaced(self):
        context = {'date': '2023-10-01', 'building_number': None, 'url': 'https://epoch.ai/data/ai-data-centers'}
        result = review('2019-04', {}, context)
        self.assertEqual(result['candidate'], '2019-04')
        self.assertIsNone(review('2023-09', {}, context))
        self.assertIsNone(review('existing', {}, context))
        self.assertIsNone(review('2019-04', {'epoch_building_number': 2}, {**context, 'building_number': 1}))
    def series(self, values):
        return pd.Series(values, index=pd.period_range('2020-01', periods=len(values), freq='M').astype(str))

    def test_sustained_rise(self):
        self.assertEqual(roof_on_month(self.series([.1] * 6 + [.35, .36, .3])), '2020-07')

    def test_cloud_gap_is_not_two_consecutive_months(self):
        self.assertEqual(roof_on_month(self.series([.1] * 6 + [.35, None, .36])), 'not_yet')

    def test_existing_and_no_detection(self):
        self.assertEqual(roof_on_month(self.series([.4] * 9)), 'existing')
        self.assertEqual(roof_on_month(self.series([.1] * 6 + [.4, .1, .1])), 'not_yet')
        self.assertEqual(roof_on_month(self.series([None, None, None])), 'not_yet')


class StatusTests(unittest.TestCase):
    def render(self, quarter, roof_on=None, adjacent=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'site'
            (site / 'data/timeline').mkdir(parents=True)
            s = dict(site_id='synthetic', name='Synthetic', lat=1, lon=1, country='US', polygons=[{'confidence': 'medium'}])
            if adjacent:
                s['nox_ef_note'] = 'ADJACENT PLANT'
            (site / 'data/sites.json').write_text(json.dumps({'sites': [s]}))
            (site / 'data/timeline/synthetic.json').write_text(json.dumps({'quarters': [quarter], 'roof_on': roof_on or {'hall': '2024-01'}}))
            with patch.multiple(build_status, ROOT=root, SITE=site), contextlib.redirect_stdout(io.StringIO()):
                build_status.main()
            return json.loads((site / 'data/status.json').read_text())['sites'][0]

    def quarter(self):
        return dict(q='2026Q3', halls_total=1, halls_roofed=1, cap_doc_mw=None, basis='roof potential', est_lo=0, est_mid=None, est_hi=90, fitted_ha=6)

    def test_roof_only_has_no_midpoint(self):
        result = self.render(self.quarter())
        self.assertIsNone(result['est_mid'])
        self.assertIn('unknown', result['running'])
        self.assertFalse(result['combustion'])

    def test_calibrated_flux_above_two_sigma(self):
        q = self.quarter()
        q.update(basis='NO2-flux on-site generation', est_lo=200, est_mid=300, est_hi=400,
                 no2_flux={'nox_kgh': 300, 'nox_se': 40})
        result = self.render(q)
        self.assertEqual(result['est_mid'], 300)
        self.assertTrue(result['combustion'])
        self.assertIn('on-site generation detected', result['running'])

    def test_threshold_and_missing_uncertainty_do_not_detect(self):
        for se in [150, None]:
            q = self.quarter()
            q.update(no2_flux={'nox_kgh': 300, 'nox_se': se})
            self.assertFalse(self.render(q)['combustion'])

    def test_unknown_roof_is_not_a_date(self):
        q = self.quarter()
        q.update(halls_roofed=0, est_hi=0)
        result = self.render(q, {'hall': 'unknown'})
        self.assertIn('unresolved', result['built'])
        self.assertEqual(result['load'], 'unknown')


if __name__ == '__main__':
    unittest.main()
