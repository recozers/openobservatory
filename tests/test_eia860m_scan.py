"""RFW-20: the EIA-860M scan flags the right generators for the right reasons, and the committed candidate table is consistent."""
import csv
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import eia860m_scan as es  # noqa: E402


def gen(pid, name, entity, tech, mw, lat, lon, sheet="Planned", year=2027, status="(U) Under construction"):
    return {"Plant ID": pid, "Plant Name": name, "Entity Name": entity, "Plant State": "TX", "County": "X", "Sector": "IPP Non-CHP",
            "Generator ID": "1", "Nameplate Capacity (MW)": mw, "Technology": tech, "Status": status, "Latitude": lat, "Longitude": lon,
            "sheet": sheet, "year": year, "month": 3}


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.sites = pd.DataFrame([dict(site_id="campus", name="Campus", operator="Op", lat=32.0, lon=-99.0, site_class="ai_training"),
                                   dict(site_id="far", name="Far", operator="Op", lat=40.0, lon=-80.0, site_class="cloud")])

    def test_near_and_keyword_flags(self):
        g = pd.DataFrame([
            gen(1, "Campus Peaker", "Utility Co", "Natural Gas Fired Combustion Turbine", 100, 32.02, -99.0),        # 2.2 km: near
            gen(2, "Stargate Power", "Crusoe Energy", "Natural Gas Internal Combustion Engine", 50, 35.0, -101.0),   # keyword only
            gen(3, "Nowhere Plant", "Nobody", "Natural Gas Fired Combined Cycle", 900, 45.0, -110.0),               # neither
            gen(4, "Airport", "Aviation Inc", "Natural Gas Fired Combustion Turbine", 10, 32.5, -99.0),               # 55 km: not near
        ])
        out = es.scan(g, self.sites, 5.0, {1}, {2: dict(plant_id="2", verdict="on-site fleet", evidence_url="https://x", note="n")})
        self.assertEqual(list(out.plant_id), [1, 2])
        near = out[out.plant_id == 1].iloc[0]
        self.assertTrue(near.flag_near)
        self.assertEqual(near.nearest_site, "campus")
        self.assertLess(near.distance_km, 2.5)
        self.assertTrue(near.epa_hourly.startswith("in eGRID 2023"))
        kw = out[out.plant_id == 2].iloc[0]
        self.assertFalse(kw.flag_near)
        self.assertEqual(kw.flag_keyword, "stargate; crusoe")
        self.assertEqual((kw.verdict, kw.evidence_url), ("on-site fleet", "https://x"))
        self.assertTrue(kw.epa_hourly.startswith("unknown"))

    def test_keywords_match_whole_words_only(self):
        g = pd.DataFrame([gen(5, "Mainstream Plant", "Switchgrass Energy", "Natural Gas Fired Combustion Turbine", 10, 45.0, -110.0)])
        self.assertTrue(es.scan(g, self.sites, 5.0, set(), {}).empty)   # "ai" inside "Mainstream", "switch" inside "Switchgrass"

    def test_plant_rows_aggregate_generators(self):
        g = pd.DataFrame([gen(6, "Fleet", "X", "Natural Gas Fired Combustion Turbine", 100, 32.01, -99.0, year=2027),
                          gen(6, "Fleet", "X", "Natural Gas Internal Combustion Engine", 20, 32.01, -99.0, sheet="Operating", year=2025, status="(OP) Operating")])
        out = es.scan(g, self.sites, 5.0, set(), {})
        r = out.iloc[0]
        self.assertEqual((r.n_generators, r.nameplate_mw, r.sheet, r.first_operation), (2, 120.0, "Operating; Planned", "2025-03"))
        self.assertIn("Combustion Turbine 100 MW", r.technologies)
        self.assertEqual(r.statuses, "OP; U")

    def test_haversine(self):
        self.assertAlmostEqual(es.haversine_km(0, 0, 0, 1), 111.19, places=1)


class CommittedTableTests(unittest.TestCase):
    def test_candidates_and_summary_agree(self):
        cands = list(csv.DictReader(open(ROOT / "results" / "eia860m_candidates.csv", encoding="utf-8")))
        summary = json.loads((ROOT / "results" / "eia860m_scan_summary.json").read_text())
        self.assertEqual(len(cands), summary["candidates"])
        self.assertEqual(len({c["plant_id"] for c in cands}), len(cands))
        for c in cands:
            self.assertTrue(c["flag_near"] == "True" or c["flag_keyword"], c["plant_id"])
            self.assertTrue(c["verdict"] and c["verdict"] != "unverified", f"{c['plant_id']} {c['plant_name']} lacks a verification note")
        reviewed = {r["plant_id"] for r in csv.DictReader(open(ROOT / "data" / "eia860m_review.csv", encoding="utf-8"))}
        self.assertTrue({c["plant_id"] for c in cands} <= reviewed)


if __name__ == "__main__":
    unittest.main()
