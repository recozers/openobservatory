import unittest
from tools.validate_epoch import supported_timeline_row


class DisclosureAuditTests(unittest.TestCase):
    def row(self, **changes):
        return dict(dict(capacity_basis='water_derived_it_annual', url='https://example.invalid/report',
                         source='Published annual water / WUE', tier='A2', capacity_mw='32.5',
                         valid_from='2024-01-01', valid_to='2024-12-31'), **changes)

    def test_sourced_annual_disclosures_can_augment_epoch(self):
        for basis in ['water_derived_it_annual', 'facility_measured_annual', 'it_measured_annual']:
            self.assertTrue(supported_timeline_row(self.row(capacity_basis=basis)))

    def test_unknown_unsourced_and_invalid_units_still_fail(self):
        for change in [dict(capacity_basis='invented'), dict(url=''), dict(source=''), dict(tier='U'),
                       dict(capacity_mw='nan'), dict(capacity_mw='-1'), dict(valid_to=''),
                       dict(valid_from='2024-02-01'), dict(valid_to='2025-12-31')]:
            with self.subTest(change=change):
                self.assertFalse(supported_timeline_row(self.row(**change)))
