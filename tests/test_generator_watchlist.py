import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import build_status
from tools import refresh
from build_timeline_data import emission_factor_range
from tools import generator_watchlist as watch


class GeneratorWatchTests(unittest.TestCase):
    def test_workflow_dry_run_and_live_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'data').mkdir(); (root/'site/data').mkdir(parents=True)
            (root/'data/sites.csv').write_text('site_id\n')
            (root/'data/refresh_flux_sources.csv').write_text('site_id,profile,baseline_before,refresh_mode\n')
            for argv, live in [(['refresh.py','--dry-run'],False),(['refresh.py'],True)]:
                with patch.object(refresh,'ROOT',root), patch.object(refresh,'run') as run, \
                     patch('sys.argv',argv), patch.dict('os.environ',{'EE_SERVICE_ACCOUNT_JSON':'present'},clear=True):
                    refresh.main()
                self.assertIn(unittest.mock.call('tools/generator_watchlist.py', *(['--live'] if live else [])), run.call_args_list)

    def test_seasonal_baseline_uncertainty_and_incomplete_month(self):
        dates = pd.to_datetime(['2024-01-01','2024-01-02','2024-01-03',
                                '2026-01-01','2026-01-02','2026-01-03',
                                '2026-02-01','2026-02-02','2026-02-03'])
        s = pd.Series([0, 10, 20, 30, 30, 30, 99, 99, 99], index=dates)
        f = watch.monthly_frame(s, '2026-01-01', {'factor':1, 'scatter':0}, '2026-02-15')
        self.assertEqual(list(f.index), ['2026-01'])
        unit = watch.NOX_NO2 * watch.MW_NO2 * 3600
        self.assertAlmostEqual(f.iloc[0].nox_kgh_cal, 20 * unit)
        self.assertAlmostEqual(f.iloc[0].nox_se, 10 / np.sqrt(3) * unit)
        self.assertGreater(f.iloc[0].baseline_se, 0)

    def test_absent_season_or_too_few_days_is_not_zero(self):
        s = pd.Series([1]*8, index=pd.to_datetime(['2024-01-01','2024-01-02',
            '2026-01-01','2026-01-02','2026-01-03','2026-02-01','2026-02-02','2026-02-03']))
        self.assertTrue(watch.monthly_frame(s, '2026-01-01', {'factor':1,'scatter':0}, '2026-03-01').empty)

    def test_signed_changes_and_strict_threshold(self):
        f = pd.DataFrame(dict(nox_kgh_cal=[-200,100,200,201,500,500],
                             nox_se=[30,20,100,100,np.nan,-1], n_days=[4]*6))
        self.assertEqual(list(watch.crossings(f).index), [3])
        for ef in ({}, {'nox_ef_lo':'.1','nox_ef_hi':'.2'}):
            self.assertIsNone(emission_factor_range(dict(ef, site_class='generator_planned')))

    def test_refresh_preserves_baseline_replaces_overlap_and_column_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root/'results_no2/generator_watch';folder.mkdir(parents=True)
            p = folder/'sample.csv'
            old = pd.DataFrame({'1000.0':[1,2,3]},index=['2024-01-01','2026-05-01','2026-07-01'])
            old.to_csv(p)
            def fetch(row, days):
                self.assertEqual(str(days[0].date()), '2026-06-01')
                self.assertEqual(str(days[-1].date()), '2026-08-31')
                return pd.DataFrame({1000.0:[9]}, index=['2026-08-01'])
            row = dict(site_id='sample',lat='40',lon='-100',baseline_before='2026-01-01',profile_start='2024-01-01')
            watch.refresh_profile(row, root, fetch, '2026-09-14')
            out = pd.read_csv(p,index_col=0)
            self.assertEqual(list(out.columns), ['1000.0'])
            self.assertEqual(list(out.index), ['2024-01-01','2026-05-01','2026-08-01'])
            self.assertEqual(out.loc['2024-01-01'].iloc[0], 1)

    def fixture(self, root):
        (root/'data').mkdir(); (root/'results_no2/generator_watch').mkdir(parents=True)
        (root/'docs').mkdir(); (root/'docs/LOG.md').write_text('Log\n')
        (root/'results_no2/calibration_plateau.json').write_text('{"factor":1,"scatter":0}')
        (root/'results_no2/generator_watch/sample.csv').write_text('saved input')
        return dict(site_id='sample',status='watching',baseline_before='2026-01-01',first_power_target='2027',
                    target_kind='year',permit_id='P1',nox_limit='unknown',coordinate_url='https://example.org/permit',
                    target_url='https://example.org/target')

    def test_first_crossing_logged_once_and_replay_does_not_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); row=self.fixture(root)
            frame=pd.DataFrame(dict(nox_kgh_cal=[-3,250],nox_se=[40,60],n_days=[5,5]),index=['2026-01','2026-02'])
            with patch.object(watch,'registry',return_value=[row]), patch.object(watch,'plateau_series'), \
                    patch.object(watch,'monthly_frame',return_value=frame), patch.object(watch,'live_fetch') as fetch:
                watch.run(root,today='2026-09-14'); watch.run(root,today='2026-09-14')
                fetch.assert_not_called()
            self.assertEqual((root/'docs/LOG.md').read_text().count('Generator watch threshold'),1)
            self.assertEqual(json.loads((root/'results_no2/generator_watch/audit.json').read_text())[0]['first_threshold_month'],'2026-02')

    def test_builder_watch_colour_without_invented_load_or_first_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row=self.fixture(root);site=root/'site'
            (site/'data/timeline').mkdir(parents=True)
            s=dict(site_id='sample',name='Sample',lat=40,lon=-100,site_class='generator_planned',generator_watch=row)
            (site/'data/sites.json').write_text(json.dumps({'sites':[s]}))
            for rate,kind in [(100,'construction'),(201,'measured')]:
                pd.DataFrame(dict(nox_kgh_cal=[rate],nox_se=[100],n_days=[5]),index=['2026-01']).to_csv(root/'results_no2/flux_sample_monthly.csv')
                with patch.multiple(build_status,ROOT=root,SITE=site), contextlib.redirect_stdout(io.StringIO()):
                    build_status.main()
                out=json.loads((site/'data/status.json').read_text())['sites'][0]
                self.assertEqual(out['evidence_kind'],kind)
                self.assertIsNone(out['est_mid'])
                self.assertIn('unknown',out['load'])
                self.assertFalse(out['combustion'])
                self.assertIn('first fire unverified',out['how'][0])
                if kind=='construction': self.assertEqual(out['running'],'watching: generator fleet under construction')


if __name__ == '__main__':
    unittest.main()
