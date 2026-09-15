"""RFW-03: the quarterly construction index is a deterministic aggregation of the radar review and radar series."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import cn_construction_index as ci  # noqa: E402


def step_series(step_month, months=("2018-01", "2026-09"), low=-15.0, high=-3.0):
    idx = pd.period_range(months[0], months[1], freq="M").strftime("%Y-%m")
    return pd.Series([high if m >= step_month else low for m in idx], index=idx, name="VV:structure")


class ConstructionIndexTests(unittest.TestCase):
    def test_quarter_and_window_of_a_clean_step(self):
        d = ci.date_entry(step_series("2024-05"))
        self.assertEqual(d["structure_on"], "2024-05")
        self.assertEqual(d["quarter"], "2024Q2")
        self.assertEqual((d["window_from"], d["window_to"], d["spread_months"]), ("2024-05", "2024-05", 0))

    def test_onset_of_a_ramp_opens_the_window(self):
        s = step_series("2024-05")
        s["2024-03"], s["2024-04"] = -12.5, -11.5   # above base + 2 dB but below the 4 dB rule
        d = ci.date_entry(s)
        self.assertEqual(d["structure_on"], "2024-05")
        self.assertEqual((d["window_from"], d["spread_months"]), ("2024-03", 2))
        s["2024-02"] = -13.5  # below base + 2 dB: the run stops
        self.assertEqual(ci.date_entry(s)["window_from"], "2024-03")

    def test_undated_series_is_kept_without_a_quarter(self):
        d = ci.date_entry(step_series("2030-01"))
        self.assertEqual(d["structure_on"], "")
        self.assertEqual(d["quarter"], "")

    def test_quarters_between(self):
        self.assertEqual(ci.quarters_between("2023Q4", "2024Q2"), ["2023Q4", "2024Q1", "2024Q2"])
        self.assertEqual(ci.quarters_between("2024Q1", "2024Q1"), ["2024Q1"])

    def test_aggregation_keeps_verdicts_separate_and_sums_areas(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            rows = [dict(site_id="cn_x_r01", hub="x", verdict="data-hall complex", area_ha="10"),
                    dict(site_id="cn_x_r02", hub="x", verdict="unclear", area_ha="6"),
                    dict(site_id="cn_x_r03", hub="x", verdict="not a data centre", area_ha="5"),
                    dict(site_id="cn_x_r04", hub="x", verdict="unclear", area_ha="7")]
            with open(tmp / "review.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            for sid, m in (("cn_x_r01", "2024-05"), ("cn_x_r02", "2024-06"), ("cn_x_r03", "2024-05")):
                pd.DataFrame({"VV:structure": step_series(m)}).rename_axis("ym").to_csv(tmp / f"{sid}.csv")
            # r04 has no radar series
            entries, agg = ci.build(tmp / "review.csv", tmp)
            self.assertEqual(len(entries), 4)
            self.assertEqual(next(e for e in entries if e["site_id"] == "cn_x_r04")["note"], "no radar series")
            by = {(r["hub"], r["quarter"], r["verdict"]): r for r in agg}
            self.assertEqual(by[("x", "2024Q2", "data-hall complex")]["area_ha"], 10.0)
            self.assertEqual(by[("x", "2024Q2", "unclear")]["area_ha"], 6.0)
            self.assertEqual(by[("x", "2024Q2", "not a data centre")]["area_ha"], 5.0)
            self.assertEqual(by[("x", "2024Q2", "unclear")]["area_firm_ha"], 6.0)
            self.assertEqual(by[("x", "2024Q2", "unclear")]["area_possible_ha"], 6.0)
            self.assertEqual(sum(r["area_ha"] for r in agg), 21.0)

    def test_repository_index_matches_the_review_file(self):
        review = list(csv.DictReader(open(ROOT / "data" / "cn_radar_review.csv", encoding="utf-8")))
        entries = list(csv.DictReader(open(ROOT / "results_cn" / "construction_index_entries.csv")))
        self.assertEqual({r["site_id"] for r in review}, {e["site_id"] for e in entries})
        for e in entries:
            self.assertIn(e["verdict"], {"data-hall complex", "not a data centre", "unclear"})
        agg = list(csv.DictReader(open(ROOT / "results_cn" / "construction_index.csv")))
        dated = [e for e in entries if e["structure_on"]]
        self.assertAlmostEqual(sum(float(r["area_ha"]) for r in agg), sum(float(e["area_ha"]) for e in dated), places=1)
        self.assertEqual(sum(int(r["n"]) for r in agg), len(dated))


if __name__ == "__main__":
    unittest.main()
