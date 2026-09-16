"""RFW-16: the qualification rules for NOx calibration plants, and the committed qualification and comparison files."""
import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import turbine_calibration_qualify as tq  # noqa: E402


def row(**o):
    base = dict(stack_max_m=45.0, nei_other_share_10km=0.02, nei_largest_other_10km="", nei_largest_other_10km_tons=10.0, nei_own_nox_tons=1000.0)
    base.update(o)
    return base


class RuleTests(unittest.TestCase):
    def test_overpass_window_from_longitude(self):
        w = tq.overpass_window(-96.5, -6)          # east Texas: 13:30 solar = 19:56 UTC
        self.assertEqual((w["overpass_utc"], w["overpass_utc_hours"], w["overpass_local_standard_hours"]), (19.93, "19|20", "13|14"))
        w = tq.overpass_window(-81.78, -5)         # Florida: 18:57 UTC, so the 18 and 19 UTC hours, 13 and 14 EST
        self.assertEqual((w["overpass_utc_hours"], w["overpass_local_standard_hours"]), ("18|19", "13|14"))
        w = tq.overpass_window(0.0, 0)
        self.assertEqual(w["overpass_utc_hours"], "13|14")

    def test_candidate_qualifies_only_with_a_low_reported_stack_and_isolation(self):
        self.assertEqual(tq.qualify(row(), True)[0], "qualified low-stack reference")
        self.assertEqual(tq.qualify(row(stack_max_m=None), True)[0], "rejected")
        self.assertEqual(tq.qualify(row(stack_max_m=90.0), True)[0], "rejected")
        self.assertEqual(tq.qualify(row(nei_other_share_10km=0.12), True)[0], "rejected")
        self.assertEqual(tq.qualify(row(nei_largest_other_10km_tons=60.0), True)[0], "rejected")   # 6 % of 1,000 t singly
        self.assertEqual(tq.qualify(row(nei_other_share_10km=None), True)[0], "rejected")

    def test_reference_keeps_its_class_but_carries_a_caveat(self):
        self.assertEqual(tq.qualify(row(stack_max_m=137.0), False)[0], "tall-stack reference")
        verdict, reason = tq.qualify(row(stack_max_m=137.0, nei_other_share_10km=0.3), False)
        self.assertEqual(verdict, "reference with caveat")
        self.assertIn("30%", reason)


class CommittedFilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = {r["plant"]: r for r in csv.DictReader(open(ROOT / "results_no2" / "calibration_plant_qualification.csv"))}
        cls.cmp = list(csv.DictReader(open(ROOT / "results_no2" / "calibration_stack_comparison.csv")))
        cls.meta = json.loads((ROOT / "results_no2" / "calibration_plant_qualification.json").read_text())

    def test_eight_plants_with_verdicts(self):
        self.assertEqual(len(self.q), 8)
        for k in tq.CAL_PLANTS:
            self.assertEqual(self.q[k]["verdict"], "tall-stack reference", k)
            self.assertGreaterEqual(float(self.q[k]["stack_max_m"]), 90.0, k)
        self.assertEqual(self.q["forney_gas"]["verdict"], "rejected")
        self.assertEqual(self.q["fort_myers_gas"]["verdict"], "rejected")
        self.assertEqual(self.q["fort_myers_gas"]["stack_max_m"], "")
        self.assertEqual(self.q["midland_gas"]["verdict"], "qualified low-stack reference")
        self.assertLess(float(self.q["midland_gas"]["stack_max_m"]), 60.0)

    def test_comparison_carries_the_classes_and_the_solar_window(self):
        classes = {r["plant"]: r["stack_class"] for r in self.cmp}
        self.assertEqual(classes["midland_gas"], "gas_low_stack_qualified")
        self.assertEqual(classes["forney_gas"], "gas_candidate_rejected")
        self.assertEqual(classes["fort_myers_gas"], "gas_candidate_stack_unreported")
        windows = {r["time_window"] for r in self.cmp}
        self.assertIn("solar_overpass_utc_hours_in_local_standard_time", windows)
        self.assertEqual(len(self.cmp), 24)   # 8 plants × 3 windows
        prod = [r for r in self.cmp if r["used_by_existing_production"] == "True"]
        self.assertEqual({r["plant"] for r in prod}, set(tq.CAL_PLANTS))

    def test_neighbour_file_and_metadata(self):
        n = list(csv.DictReader(open(ROOT / "data" / "nei_2020_nox_near_calibration_plants.csv")))
        self.assertEqual({r["plant"] for r in n}, set(self.q))
        own = [r for r in n if r["role"] == "own"]
        self.assertEqual({r["plant"] for r in own}, set(self.q))
        self.assertEqual(self.meta["eia860_sha256"], tq.EIA860_SHA256)
        self.assertEqual(self.meta["rules"]["isolation_km"], 10.0)


if __name__ == "__main__":
    unittest.main()
