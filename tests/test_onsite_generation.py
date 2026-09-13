import unittest

from build_timeline_data import emission_factor_range


class EmissionFactorTests(unittest.TestCase):
    def test_permit_ceiling_cannot_be_inverted_as_measured_generation(self):
        self.assertIsNone(emission_factor_range({"nox_ef_basis": "permit_upper_limit", "nox_ef_hi": "0.0635029318"}))
        self.assertIsNone(emission_factor_range({"nox_ef_basis": "permit_upper_limit", "nox_ef_lo": "0.04", "nox_ef_hi": "0.064"}))

    def test_existing_qualified_range_and_invalid_ranges(self):
        self.assertEqual(emission_factor_range({"nox_ef_lo": "0.5", "nox_ef_hi": "1.5"}), (0.5, 1.5))
        for lo, hi in [(0, 0.1), ("0", "0.1"), ("nan", "1"), ("1", "inf"), ("1", "0.5")]:
            self.assertIsNone(emission_factor_range({"nox_ef_lo": lo, "nox_ef_hi": hi}))
