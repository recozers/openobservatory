"""RFW-14: the season-matched plume test ignores a seasonal cycle and still finds a real step."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import plume_batch as pb  # noqa: E402


def synthetic(step=0.0, amplitude=3.0, noise=1.0, start="2023-01-01", end="2026-06-30", change="2026-04-01", seed=0):
    """Daily downwind-minus-upwind with a winter-high seasonal cycle, white noise, and a step of `step` from `change`."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="D")
    season = amplitude * np.cos(2 * np.pi * (idx.dayofyear - 15) / 365.25)
    v = season + rng.normal(0, noise, len(idx)) + np.where(idx >= pd.Timestamp(change), step, 0.0)
    return pd.DataFrame({"site": "synth", "dw_minus_uw": v}, index=idx.strftime("%Y-%m-%d"))


class SeasonMatchedTests(unittest.TestCase):
    def write(self, df):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name) / "synth.csv"
        df.to_csv(p, index_label="d")
        return p

    def test_spring_start_without_a_step_fools_the_current_test_but_not_the_season_matched_one(self):
        p = self.write(synthetic(step=0.0, change="2026-04-01"))
        _, z_cur, *_ = pb.zscore(p, "2026-04-01")
        _, z_sea, na, nb, months = pb.season_zscore(p, "2026-04-01")
        self.assertLess(z_cur, -2.5, "after = spring and summer only, so the current test reads the seasonal dip as a fall")
        self.assertLess(abs(z_sea), 2.0)
        self.assertEqual(months, 3)   # April, May, June on both sides
        self.assertGreater(na, 10)
        self.assertGreater(nb, 10)

    def test_real_step_is_found_by_both(self):
        p = self.write(synthetic(step=2.0, change="2025-07-01"))
        _, z_cur, *_ = pb.zscore(p, "2025-07-01")
        _, z_sea, *_ = pb.season_zscore(p, "2025-07-01")
        self.assertGreater(z_sea, 5)
        self.assertGreater(z_cur, 2.5)

    def test_short_series_returns_nones(self):
        p = self.write(synthetic(start="2026-03-25", end="2026-04-10", change="2026-04-01"))
        self.assertEqual(pb.season_zscore(p, "2026-04-01"), (None, None, None, None, None))

    def test_repository_sensitivity_file_is_consistent(self):
        df = pd.read_csv(ROOT / "results_no2" / "plume_date_sensitivity.csv")
        self.assertEqual(set(df.role), {"site", "control"})
        self.assertEqual(sorted(df.offset_months.unique()), list(range(-3, 4)))
        at_doc = df[(df.offset_months == 0) & (df.role == "site")].set_index("file_site")
        by_series = pd.read_csv(ROOT / "results_no2" / "plume_batch_zscores_by_series.csv")
        ref = by_series[by_series.role == "site"].set_index("file_site").z
        common = ref.index.intersection(at_doc.index)
        self.assertGreater(len(common), 25)
        # the current test at offset 0 reproduces the recorded per-series z-scores
        np.testing.assert_allclose(at_doc.loc[common, "z_current"].astype(float), ref.loc[common].astype(float), atol=0.011)


if __name__ == "__main__":
    unittest.main()
