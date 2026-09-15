"""RFW-19: Microsoft's FY25 metro table, parsed from the fact sheet text, agrees with itself and with the water file, and is
never attributed to an inventory campus."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import microsoft_metro_table as mm  # noqa: E402

SAMPLE = """Table 15 – FY25 Datacenter water and electricity use by location
Asia Pacific Auckland New Zealand 19,465 – –
Singapore Singapore 338,845 423 99 169
Europe Madrid Spain 22,588 15 6 515
Americas Boydton (VA) United States of America 3,113,847 362 145 *
Quincy (WA) United States of America 1,381,569 1,292 74 517 833
Cheyenne (WY) United States of America 1,091,460 188 75 61
"""


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class ParseTests(unittest.TestCase):
    def test_optional_columns_are_placed_by_the_pools_column(self):
        r = mm.parse_row(SAMPLE, "Auckland", "New Zealand")
        self.assertEqual((r["electricity_mwh"], r["water_withdrawal_ml"], r["pools"], r["replenishment_ml"]), (19465, None, None, None))
        r = mm.parse_row(SAMPLE, "Singapore", "Singapore")
        self.assertEqual((r["water_withdrawal_ml"], r["non_potable_pct"], r["pools"], r["replenishment_ml"]), (423, 99, 169, None))
        r = mm.parse_row(SAMPLE, "Madrid", "Spain")
        self.assertEqual((r["non_potable_pct"], r["pools"], r["replenishment_ml"]), (None, 6, 515))
        r = mm.parse_row(SAMPLE, "Boydton (VA)", "United States of America")
        self.assertEqual((r["electricity_mwh"], r["pools"], r["replenishment_ml"]), (3113847, 145, None))
        self.assertTrue(r["replenishment_flag"].startswith("*"))
        r = mm.parse_row(SAMPLE, "Quincy (WA)", "United States of America")
        self.assertEqual((r["non_potable_pct"], r["pools"], r["replenishment_ml"]), (74, 517, 833))
        r = mm.parse_row(SAMPLE, "Cheyenne (WY)", "United States of America")
        self.assertEqual((r["non_potable_pct"], r["pools"], r["replenishment_ml"]), (None, 75, 61))

    def test_missing_row_is_an_error(self):
        with self.assertRaises(ValueError):
            mm.parse_row(SAMPLE, "Dublin", "Ireland")


class CommittedTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = read(ROOT / "data" / "microsoft_metro_fy25.csv")
        cls.water = {r["site_id"]: r for r in read(ROOT / "data" / "water_derived_loads.csv") if r["site_id"].startswith("microsoft_")}
        cls.sites = {r["site_id"] for r in read(ROOT / "data" / "sites.csv")}
        cls.disc = [r for r in read(ROOT / "data" / "operator_disclosures.csv") if r["source_table"] == mm.TABLE]

    def test_29_metros_and_totals(self):
        self.assertEqual(len(self.table), 29)
        self.assertEqual(sum(int(r["electricity_mwh"]) for r in self.table), 15_931_489)
        by_region = {}
        for r in self.table:
            by_region[r["region"]] = by_region.get(r["region"], 0) + int(r["electricity_mwh"])
        self.assertEqual(by_region, {"Asia Pacific": 699_350, "Europe": 3_541_984, "Americas": 11_690_155})

    def test_water_agrees_with_the_independently_extracted_water_file(self):
        self.assertEqual(set(self.water), {r["site_id"] for r in self.table})
        for r in self.table:
            w = float(self.water[r["site_id"]]["water_withdrawn_ML"])
            mine = 0.0 if r["water_withdrawal_ml"] == "" else float(r["water_withdrawal_ml"])
            self.assertEqual(w, mine, r["site_id"])

    def test_pools_are_withdrawal_over_2_5_ml(self):
        for r in self.table:
            if r["pools"]:
                self.assertLessEqual(abs(float(r["water_withdrawal_ml"]) / 2.5 - int(r["pools"])), 1, r["site_id"])

    def test_no_metro_figure_is_attributed_to_an_inventory_campus(self):
        for r in self.table:
            self.assertNotIn(r["site_id"], self.sites, r["site_id"])
            self.assertTrue(r["attribution"].startswith("context:"), r["site_id"])
            for sid in filter(None, r["inventory_campuses"].split(";")):
                self.assertIn(sid, self.sites, sid)

    def test_disclosure_rows_match_the_table(self):
        self.assertEqual(len(self.disc), 29)
        vals = {r["site_id"]: int(r["value"]) for r in self.disc}
        self.assertEqual(vals, {r["site_id"]: int(r["electricity_mwh"]) for r in self.table})
        for r in self.disc:
            self.assertEqual((r["metric"], r["unit"], r["year"], r["operator"]), ("electricity_mwh", "MWh", "2025", "Microsoft"))
            self.assertIn("fiscal year FY25", r["note"])
            self.assertEqual(r["source_url"], mm.URL)


if __name__ == "__main__":
    unittest.main()
