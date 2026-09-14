"""Exercise status output with independent synthetic evidence per category."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_status


class EvidenceKindTests(unittest.TestCase):
    def render(self, quarter=None, lights=None, radar=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'site'
            (site / 'data/timeline').mkdir(parents=True)
            s = dict(site_id='synthetic', name='Synthetic', lat=1, lon=1, country='US', polygons=[])
            if radar:
                s.update(coords_quality='radar_candidate', notes='score=0.8 area_ha=6')
            (site / 'data/sites.json').write_text(json.dumps({'sites': [s]}))
            if quarter:
                t = dict(quarters=[quarter], roof_on={'hall': '2024-01'}, ntl_lit=lights)
                (site / 'data/timeline/synthetic.json').write_text(json.dumps(t))
            with patch.multiple(build_status, ROOT=root, SITE=site), contextlib.redirect_stdout(io.StringIO()):
                build_status.main()
            return json.loads((site / 'data/status.json').read_text())['sites'][0]

    def quarter(self, **overrides):
        return dict(dict(q='2024Q4', halls_total=1, halls_roofed=1, cap_doc_mw=100,
                         cap_basis='it_reported', basis='documented capacity', est_lo=20,
                         est_mid=40, est_hi=60, fitted_ha=6), **overrides)

    def test_measured_annual_and_zero_are_measured(self):
        for value in (0, 100):
            r = self.render(self.quarter(cap_basis='facility_measured_annual', cap_doc_mw=value,
                                        est_lo=value, est_mid=value, est_hi=value))
            self.assertEqual(r['evidence_kind'], 'measured')
            self.assertIn('operator reports', r['running'])

    def test_calibrated_generation_is_measured(self):
        q = self.quarter(basis='NO2-flux on-site generation', no2_flux={'nox_kgh': 300, 'nox_se': 40})
        self.assertEqual(self.render(q)['evidence_kind'], 'measured')

    def test_water_derived_in_disclosed_year_and_carried(self):
        for basis in ('water_derived_it_annual', 'water_derived_carried_measured_annual'):
            r = self.render(self.quarter(cap_basis=basis))
            self.assertEqual(r['evidence_kind'], 'derived')
            self.assertIn('water', r['running'])

    def test_energisation_detected_without_measured_load(self):
        r = self.render(self.quarter(), lights='2024-05')
        self.assertEqual(r['evidence_kind'], 'detected')
        self.assertIn('not directly measured', r['load'])

    def test_capacity_prior_is_presumed(self):
        self.assertEqual(self.render(self.quarter())['evidence_kind'], 'presumed')

    def test_roofs_missing_timeline_and_unconfirmed_radar_are_construction(self):
        self.assertEqual(self.render(self.quarter(cap_doc_mw=None, est_mid=None))['evidence_kind'], 'construction')
        self.assertEqual(self.render()['evidence_kind'], 'construction')
        self.assertEqual(self.render(self.quarter(), radar=True)['evidence_kind'], 'construction')


if __name__ == '__main__':
    unittest.main()
