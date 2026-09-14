import copy
import unittest

from tools.regional_load import ROOT, audit, read_csv, validate


class RegionalLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv(ROOT / "data/regional_dc_load.csv")
        cls.sites = read_csv(ROOT / "data/sites.csv")
        cls.disclosures = read_csv(ROOT / "data/operator_disclosures.csv")

    def test_register_sources_and_reconciliation(self):
        validate(self.rows)
        self.assertEqual({r['region_id'] for r in self.rows},
                         {'dominion_virginia_power', 'aep_ohio', 'ercot', 'pjm', 'ireland', 'singapore'})
        lookup = {r['record_id']: float(r['value']) for r in self.rows}
        for year in (2023, 2024, 2025):
            prefix = f'dom_{year}07_'
            self.assertEqual(lookup[prefix+'firm'], lookup[prefix+'esa'] + lookup[prefix+'cloa'])
            self.assertEqual(lookup[prefix+'total'], lookup[prefix+'firm'] + lookup[prefix+'eloa'])
        self.assertEqual(lookup['aep_20260212_total'], lookup['aep_20260212_new_tariff'] + lookup['aep_20260212_pre_tariff'])

    def test_capacity_forecasts_mva_and_all_sector_never_enter_energy_comparison(self):
        result = audit(self.rows, self.sites, self.disclosures)['records']
        for row in result:
            if not row['record_id'].startswith('cso_ie_dc_'):
                self.assertEqual(row['status'], 'not_comparable')
                self.assertNotIn('facility_to_regional_grid_ratio', row)

    def test_actual_inventory_context_uses_raw_energy_not_quarter_estimates(self):
        result = {r['record_id']: r for r in audit(self.rows, self.sites, self.disclosures)['records']}
        r = result['cso_ie_dc_2024']
        self.assertEqual(r['included_sites'], ['meta_clonee'])
        self.assertEqual(r['inventory_facility_mwh'], 1076961)
        self.assertEqual(r['regional_grid_mwh'], 6973000)
        self.assertEqual(r['regional_grid_average_mw'], round(6973000 / 8784, 3))
        self.assertEqual(r['status'], 'partial_inventory_context')

    def test_missing_is_not_zero_and_zero_is_a_disclosure(self):
        r = next(r for r in self.rows if r['record_id'] == 'cso_ie_dc_2025')
        site = [{'site_id': 'example', 'country': 'IE'}]
        empty = audit([r], site, [])['records'][0]
        self.assertEqual(empty['status'], 'no_disclosures')
        self.assertIsNone(empty['inventory_facility_mwh'])
        self.assertIsNone(empty['review_exceeds_regional_grid'])
        d = dict(site_id='example', metric='electricity_mwh', year='2025', value='0', unit='MWh', source_url='https://example.com/report')
        zero = audit([r], site, [d])['records'][0]
        self.assertEqual(zero['inventory_facility_mwh'], 0)
        self.assertEqual(zero['facility_to_regional_grid_ratio'], 0)

    def test_duplicates_and_invalid_metrics_fail(self):
        with self.assertRaises(ValueError):
            validate(self.rows + [self.rows[0]])
        for field, value in [('unit', 'MWh'), ('value', 'nan'), ('use', 'site_evidence')]:
            bad = copy.deepcopy(self.rows[:1]); bad[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(bad)
        d = next(d for d in self.disclosures if d['site_id'] == 'meta_clonee' and d['metric'] == 'electricity_mwh')
        with self.assertRaises(ValueError):
            audit(self.rows, self.sites, self.disclosures + [d])

    def test_outlier_is_review_flag_and_inputs_are_unchanged(self):
        r = next(r for r in self.rows if r['record_id'] == 'cso_ie_dc_2024')
        d = dict(site_id='example', metric='electricity_mwh', year='2024', value='9000000', unit='MWh', source_url='https://example.com/report')
        before = copy.deepcopy((r, d))
        result = audit([r], [{'site_id':'example', 'country':'IE'}], [d])['records'][0]
        self.assertTrue(result['review_exceeds_regional_grid'])
        self.assertEqual(result['inventory_facility_mwh'], 9000000)
        self.assertEqual((r, d), before)


if __name__ == '__main__':
    unittest.main()
