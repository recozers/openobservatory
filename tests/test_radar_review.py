"""RFW-01: the review of radar-detected structures in China must stay consistent with the inventory.

- Every verdict is one of the three allowed values and has a reason and an evidence path that exists.
- Every radar-candidate entry still in data/sites.csv has a verdict, and that verdict is not "not a data centre".
- Every rejected entry keeps its polygon and radar timeline (negative results stay visible) and is out of the inventory.
- The ingest script refuses to re-add a rejected id.
"""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

VERDICTS = {"data-hall complex", "not a data centre", "unclear"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class RadarReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = read_csv(ROOT / "data" / "cn_radar_review.csv")
        cls.sites = read_csv(ROOT / "data" / "sites.csv")
        cls.by_id = {r["site_id"]: r for r in cls.review}

    def test_columns_and_values(self):
        for col in ("site_id", "hub", "verdict", "reason", "evidence", "classifier_score", "radar_structure_on"):
            self.assertIn(col, self.review[0])
        self.assertEqual(len(self.by_id), len(self.review), "duplicate site_id in review")
        for r in self.review:
            self.assertIn(r["verdict"], VERDICTS, r["site_id"])
            self.assertTrue(r["reason"].strip(), f"{r['site_id']} has no reason")
            for p in r["evidence"].split(";"):
                self.assertTrue((ROOT / p.strip()).exists(), f"{r['site_id']} evidence missing: {p}")

    def test_inventory_radar_entries_are_reviewed_and_not_rejected(self):
        radar = [s for s in self.sites if s["coords_quality"] == "radar_candidate"]
        self.assertTrue(radar, "no radar_candidate entries in the inventory")
        for s in radar:
            self.assertIn(s["site_id"], self.by_id, f"{s['site_id']} is in the inventory but not reviewed")
            self.assertNotEqual(self.by_id[s["site_id"]]["verdict"], "not a data centre", s["site_id"])

    def test_rejected_entries_left_the_inventory_but_kept_their_evidence(self):
        ids = {s["site_id"] for s in self.sites}
        rejected = [r["site_id"] for r in self.review if r["verdict"] == "not a data centre"]
        self.assertTrue(rejected, "the review rejected nothing; check the file")
        for sid in rejected:
            self.assertNotIn(sid, ids, f"{sid} rejected but still in data/sites.csv")
            self.assertTrue((ROOT / "data" / "polygons" / f"{sid}.geojson").exists(), sid)
            self.assertTrue((ROOT / "results_s1" / f"{sid}.csv").exists(), sid)

    def test_ingest_skips_rejected_ids(self):
        import ingest_radar_candidates as ing
        rejected = ing.rejected_ids()
        self.assertEqual(rejected, {r["site_id"] for r in self.review if r["verdict"] == "not a data centre"})
        self.assertEqual(ing.rejected_ids(ROOT / "data" / "no_such_file.csv"), set())


if __name__ == "__main__":
    unittest.main()
