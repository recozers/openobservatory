"""Independent EPA reconciliation plus allocation/completeness regressions."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests
import build_status
import build_timeline_data
from tools.campd_monthly import aggregate, can_allocate, links, quarterly_for_site, ROOT
from tools.campd_hourly import fetch


class CampdTests(unittest.TestCase):
    def link(self, **changes):
        row = dict(link_id='test', site_id='synthetic', oris_id='1', plant_name='Synthetic plant',
                   contracted_share='0.8', allocation_verified='yes', relationship='dedicated_supply',
                   from_date='2023-01-01', to_date='', unit_ids='A', source_url='https://example.invalid/synthetic')
        return dict(row, **changes)

    def hourly(self, month='2023-01'):
        p = pd.Period(month, freq='M')
        times = pd.date_range(p.start_time, p.end_time, freq='h')
        return pd.DataFrame(dict(facilityId=1, unitId='A', date=times.strftime('%Y-%m-%d'),
                                 hour=times.hour, opTime=0.5, grossLoad=100., noxMass=2.))

    def quarter(self, link=None, frames=None, extra=None):
        link = link or self.link()
        frames = frames if frames is not None else [self.hourly(m) for m in ['2023-01', '2023-02', '2023-03']]
        rows = aggregate(pd.concat(frames), self.link())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir(); (root / 'results_no2').mkdir()
            with (root / 'data/campus_plant_links.csv').open('w') as f:
                writer = csv.DictWriter(f, fieldnames=link.keys()); writer.writeheader()
                writer.writerows([link] + ([extra] if extra else []))
            pd.DataFrame(rows).to_csv(root / 'results_no2/campd_synthetic_monthly.csv', index=False)
            return quarterly_for_site('synthetic', 1.25, root)['2023Q1']

    def test_partial_hours_and_mass_units(self):
        r = aggregate(self.hourly(), self.link())[0]
        self.assertTrue(r['complete'])
        self.assertEqual(r['gross_mwh'], 744 * 50)
        self.assertEqual(r['gross_avg_mw'], 50)
        self.assertAlmostEqual(r['nox_kg'], 744 * 2 * .45359237)
        self.assertEqual(r['operating_unit_hours'], 372)

    def test_zero_is_known_off_time_not_missing(self):
        d = self.hourly(); d.opTime = 0; d[['grossLoad','noxMass']] = float('nan')
        r = aggregate(d, self.link())[0]
        self.assertTrue(r['complete']); self.assertEqual(r['gross_mwh'], 0)
        self.assertEqual(r['nox_kg'], 0)
        self.assertFalse(aggregate(d.iloc[:-1], self.link())[0]['complete'])

    def test_incomplete_unit_and_measurement(self):
        for d, link in [(self.hourly().iloc[:-1], self.link()), (self.hourly(), self.link(unit_ids='A;B'))]:
            r = aggregate(d, link)[0]
            self.assertFalse(r['complete']); self.assertIsNone(r['gross_avg_mw'])
        d = self.hourly(); d.loc[0, 'grossLoad'] = float('nan')
        self.assertIsNone(aggregate(d, self.link())[0]['gross_mwh'])

    def test_leap_february(self):
        r = aggregate(self.hourly('2024-02'), self.link())[0]
        self.assertEqual(r['calendar_hours'], 696); self.assertTrue(r['complete'])

    def test_duplicate_wrong_plant_or_bad_time_rejected(self):
        d = self.hourly()
        with self.assertRaises(ValueError): aggregate(pd.concat([d,d.iloc[:1]]), self.link())
        with self.assertRaises(ValueError): aggregate(d, self.link(oris_id='6641'))
        for column, value in [('opTime', 1.5), ('hour', 24), ('grossLoad', -1)]:
            bad = d.copy(); bad.loc[0,column] = value
            with self.assertRaises(ValueError): aggregate(bad, self.link())

    def test_verified_positive_quarter(self):
        q = self.quarter()
        self.assertEqual(q['basis'], 'dedicated_plant_measured')
        self.assertEqual(q['allocated_gross_avg_mw'], 40)
        self.assertEqual(q['it_equivalent_avg_mw'], 32)

    def test_allocations_and_partial_quarters_fail_closed(self):
        for change in [dict(contracted_share='', allocation_verified='no'), dict(contracted_share='0.79'), dict(allocation_verified='no'),
                       dict(relationship='non_dedicated_control'), dict(from_date='2023-01-02'),
                       dict(to_date='2023-03-30'), dict(unit_ids='A;B')]:
            with self.subTest(change=change):
                q = self.quarter(self.link(**change))
                self.assertEqual(q['basis'], 'plant_evidence_only')
                self.assertIsNone(q['it_equivalent_avg_mw'])
        self.assertIsNone(self.quarter(frames=[self.hourly()])['allocated_gross_avg_mw'])
        self.assertIsNone(self.quarter(extra=self.link(link_id='missing'))['allocated_gross_avg_mw'])

    def test_real_southaven_matches_independent_epa_aggregates(self):
        link = next(r for r in links() if r['oris_id'] == '55269')
        hourly = pd.read_csv(ROOT / 'data/campd/55269_2023.csv')
        rows = aggregate(hourly, link)
        for period, subset in [('annual', rows), ('monthly', rows[:1])]:
            api = json.loads((ROOT / f'tests/fixtures/{period}_55269_2023.json').read_text())['items']
            self.assertAlmostEqual(sum(r['gross_mwh'] for r in subset), sum(r['grossLoad'] for r in api), places=5)
            self.assertAlmostEqual(sum(r['operating_unit_hours'] for r in subset), sum(r['sumOpTime'] for r in api), places=5)
            self.assertLess(abs(sum(r['nox_kg'] for r in subset) / 907.18474 - sum(r['noxMass'] for r in api)), .002)
        self.assertTrue(all(r['complete'] for r in rows))
        self.assertFalse(can_allocate(link, '2023-01'))
        real = quarterly_for_site('colossus2_southaven', 1.2)
        self.assertTrue(real)
        self.assertTrue(all(q['basis'] == 'plant_evidence_only' and q['it_equivalent_avg_mw'] is None for q in real.values()))

    def test_failed_fetch_never_returns_partial_year(self):
        ok = Mock(status_code=200); ok.json.return_value = [dict(date='2023-01-01')]
        error = Mock(status_code=500); error.raise_for_status.side_effect = requests.HTTPError('upstream failed')
        with patch('tools.campd_hourly.requests.get', side_effect=[ok, error]):
            with self.assertRaises(requests.HTTPError): fetch(1, 2023, 'synthetic')

    def render(self, plant):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); site = root / 'site'; (site / 'data/timeline').mkdir(parents=True)
            (site / 'data/sites.json').write_text(json.dumps(dict(sites=[dict(site_id='synthetic',name='Synthetic',lat=1,lon=1)])))
            q = dict(q='2023Q1', halls_total=0, halls_roofed=0, fitted_ha=0, cap_doc_mw=None,
                     basis='dedicated_plant_measured', est_mid=32,est_lo=32,est_hi=32,campd=plant)
            (site / 'data/timeline/synthetic.json').write_text(json.dumps(dict(quarters=[q])))
            with patch.multiple(build_status, ROOT=root, SITE=site), contextlib.redirect_stdout(io.StringIO()):
                build_status.main()
            return json.loads((site / 'data/status.json').read_text())['sites'][0]

    def test_status_positive_zero_and_negative(self):
        result = self.render(self.quarter())
        self.assertIn('yes: dedicated plant generated 50 MW average', result['running'])
        self.assertEqual(result['evidence_kind'], 'measured')
        self.assertIn('Not a campus meter', result['load'])
        frames = [self.hourly(m) for m in ['2023-01','2023-02','2023-03']]
        for f in frames: f.opTime=0; f.grossLoad=0; f.noxMass=0
        self.assertFalse(self.render(self.quarter(frames=frames))['running'].startswith('yes:'))
        negative = self.render(self.quarter(self.link(relationship='non_dedicated_control')))
        self.assertNotEqual(negative['key'], 'plant')
        self.assertNotEqual(negative['evidence_kind'], 'measured')

    def test_builder_assigns_separate_load_basis_without_changing_capacity(self):
        plant = self.quarter()
        sid = 'colossus2_southaven'
        original = json.loads((ROOT / f'site/data/timeline/{sid}.json').read_text())
        expected = next(q for q in original['quarters'] if q['q'] == '2023Q1')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch.object(build_timeline_data, 'OUT', out), patch.object(
                    build_timeline_data, 'quarterly_for_site',
                    side_effect=lambda site, pue, root: {'2023Q1': plant} if site == sid else {}), contextlib.redirect_stdout(io.StringIO()):
                build_timeline_data.main()
            result = json.loads((out / f'{sid}.json').read_text())
            q = next(q for q in result['quarters'] if q['q'] == '2023Q1')
            self.assertEqual(q['load_basis'], 'dedicated_plant_measured')
            self.assertEqual(q['load_tier'], 'A1')
            self.assertEqual(q['est_mid'], 32)
            self.assertEqual(q['cap_doc_mw'], expected['cap_doc_mw'])
            self.assertEqual(q['cap_basis'], expected['cap_basis'])
            self.assertIn('not a campus meter', result['caveat'])

if __name__ == '__main__':
    unittest.main()
