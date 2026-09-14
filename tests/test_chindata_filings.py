"""Chindata's per-data-centre tables parse, add up to their reported totals, and reach the disclosures file correctly."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import chindata_filings as cf

ROOT = Path(__file__).resolve().parents[1]

# Verbatim table text from Chindata's FY2022 Form 20-F (after HTML is reduced to text).
FY2022 = (
    "The following table sets forth details concerning our data centers in service as of December 31, 2022: Data Center Type "
    "Leased/ Owned IT Capacity in Service (MW) Contracted IT Capacity (MW) IoI IT Capacity (MW) Utilized IT Capacity(MW) "
    "Greater Beijing Area, mainland China CN01 Hyperscale Owned 36 36 — 36 CN02 Wholesale Leased 11 5 — 5 CN03 Hyperscale "
    "Owned 17 17 — 17 CN04 Hyperscale Owned 28 27 — 27 CN05 Hyperscale Owned 23 23 — 23 CN06 Hyperscale Owned 30 30 — 26 "
    "CN07 Hyperscale Owned 29 27 — 27 CN08 Hyperscale Owned 51 51 — 50 CN09 Hyperscale Owned 52 51 — 48 CN10 Hyperscale "
    "Owned 3 3 — 3 CN11-A Hyperscale Owned 24 23 — 23 CN11-B Hyperscale Owned 24 23 — 23 CN11-C Hyperscale Owned 71 71 — 67 "
    "CN12 Hyperscale Owned 6 5 — 5 CN13 Hyperscale Leased 13 13 — 4 CN14 Hyperscale Owned 18 18 — 18 CN15 Hyperscale Owned "
    "51 52 — 36 CN18 Hyperscale Owned 30 30 — 28 Yangtze River Delta Area, mainland China CE01 Hyperscale Owned 17 10 — 10 "
    "Greater Bay Area, mainland China CS01 Wholesale Leased 5 4 — 4 Malaysia MY0102 Hyperscale Owned 20 17 — 13 MY03 "
    "Hyperscale Owned 16 8 8 4 MY06-1 Hyperscale Owned 19 — 19 19 India BBY01 Hyperscale Owned 20 20 — 12 Total 613 563 27 "
    "525 The following table sets forth details concerning our data centers under construction as of December 31, 2022: "
    "Data Center Type Leased/ Owned Designed IT Capacity (MW) Contracted IT Capacity IoI IT Capacity (MW) Greater Beijing "
    "Area, mainland China CN16 Hyperscale Leased 14 — 14 CN17 Hyperscale Leased 14 — 14 CN19 Hyperscale Owned 26 11 — CN20 "
    "Hyperscale Owned 49 38 11 CN21 Hyperscale Owned 50 — 38 Yangtze River Delta Area, mainland China CE02 Hyperscale Owned "
    "20 — — Malaysia MY06-2 Hyperscale Owned 42 — 42 MY06-3 Hyperscale Owned 43 — 43 Total 257 49 162 68 Table of Contents "
    "Land Resources Held for Future Development"
)

# Verbatim table text from Chindata's September 2020 prospectus, which reports ratios instead of megawatts.
IPO = (
    "The following table sets forth details concerning our data centers in service as of June 30, 2020: Data Center Type "
    "Leased/ Owned Capacity in Service (MW) Contracted Ratio (1) IoI Ratio (2) Utilization Ratio (3) Greater Beijing Area, "
    "China CN01 Hyperscale Owned 36 100% — 96% CN02 Wholesale Leased 11 98% — 98% CN03 Hyperscale Owned 17 99% — 98% CN04 "
    "Hyperscale Owned 28 96% — 94% CN05 Hyperscale Owned 21 100% — 97% CN06 Hyperscale Owned 29 88% 9% 46% CN07 Hyperscale "
    "Owned 29 96% — 36% Greater Bay Area, China CS01 Wholesale Leased 5 70% — 28% Malaysia MY0102 Hyperscale Owned 20 38% "
    "40% 38% Total 196 90% 5% 72% Notes: (1) The ratio of contractually committed capacity to capacity in service. The "
    "following table sets forth details concerning our data centers under construction as of June 30, 2020: Data Center "
    "Type Leased/ Owned Planned Capacity (MW) Contracted Ratio (1) IoI Ratio (2) Greater Beijing Area, China CN08 Hyperscale "
    "Owned 47 82% 18% CN09 Hyperscale Owned 45 86% — CN10 (3) Hyperscale Owned 3 95% — CN11 Hyperscale Owned 103 — 100% "
    "Yangtze River Delta Area, China CE01 Hyperscale Owned 16 26% — India BBY01 Hyperscale Owned 20 50% — Total 234 40% 47% "
    "Notes: (1) The ratio of contractually committed capacity to planned capacity."
)

LOCATIONS = {"CN20": {"data_center": "CN20", "stated_location": "the Company's Datong campus in Shanxi Province",
                      "hub": "Shanxi (Datong; outside the 8 hubs)", "source_key": "cd_pr_2023q2"}}


class ParseTables(unittest.TestCase):
    def test_megawatt_tables(self):
        in_service, building = cf.parse_tables(FY2022)
        self.assertEqual((in_service.status, in_service.as_of), ("in_service", "2022-12-31"))
        self.assertEqual([m for m, _ in in_service.columns], ["it_capacity_in_service_mw", "contracted_it_capacity_mw",
                                                               "ioi_it_capacity_mw", "utilized_it_capacity_mw"])
        self.assertEqual(len(in_service.rows), 24)
        cn15 = next(r for r in in_service.rows if r["data_center"] == "CN15")
        self.assertEqual(cn15["values"], {"it_capacity_in_service_mw": 51, "contracted_it_capacity_mw": 52,
                                          "ioi_it_capacity_mw": None, "utilized_it_capacity_mw": 36})
        self.assertEqual(cn15["region"], "Greater Beijing Area, mainland China")
        self.assertEqual(next(r for r in in_service.rows if r["data_center"] == "BBY01")["region"], "India")
        self.assertEqual(in_service.total["utilized_it_capacity_mw"], 525)
        self.assertEqual(building.status, "under_construction")
        self.assertEqual([r["data_center"] for r in building.rows], ["CN16", "CN17", "CN19", "CN20", "CN21", "CE02", "MY06-2", "MY06-3"])
        self.assertEqual(building.total, {"designed_it_capacity_mw": 257, "contracted_it_capacity_mw": 49, "ioi_it_capacity_mw": 162})

    def test_ratio_tables_and_footnote_markers(self):
        in_service, building = cf.parse_tables(IPO)
        self.assertEqual(in_service.as_of, "2020-06-30")
        cn06 = next(r for r in in_service.rows if r["data_center"] == "CN06")
        self.assertEqual(cn06["values"], {"it_capacity_in_service_mw": 29, "contracted_ratio_pct": 88, "ioi_ratio_pct": 9,
                                          "utilization_ratio_pct": 46})
        self.assertEqual([r["data_center"] for r in building.rows], ["CN08", "CN09", "CN10", "CN11", "CE01", "BBY01"])
        self.assertEqual(building.columns[0], ("planned_capacity_mw", "MW"))

    def test_rows_reproduce_reported_totals(self):
        for text in (FY2022, IPO):
            for table in cf.parse_tables(text):
                failed = [c for c in cf.check_totals(table) if not c["ok"]]
                self.assertEqual(failed, [], (table.as_of, table.status))

    def test_a_wrong_row_fails_the_totals_check(self):
        in_service, _ = cf.parse_tables(FY2022.replace("CN08 Hyperscale Owned 51 51 — 50", "CN08 Hyperscale Owned 51 51 — 80"))
        failed = {c["metric"] for c in cf.check_totals(in_service) if not c["ok"]}
        self.assertEqual(failed, {"utilized_it_capacity_mw"})


class DisclosureRows(unittest.TestCase):
    def rows(self):
        tables = {"cd_20f_2022": cf.parse_tables(FY2022)}
        return cf.disclosure_rows(tables, LOCATIONS, {"cd_20f_2022": {"archive_url": "https://web.archive.org/web/20230506044058id_/x"}})

    def test_only_chinese_data_centres_and_no_invented_zeros(self):
        rows = self.rows()
        self.assertFalse([r for r in rows if r["campus"].startswith(("Chindata MY", "Chindata BBY"))])
        cn16 = [r for r in rows if r["campus"] == "Chindata CN16"]
        self.assertEqual({r["metric"] for r in cn16}, {"designed_it_capacity_mw", "ioi_it_capacity_mw"})
        self.assertTrue(all(r["note"].startswith(cf.TAG) and r["unit"] in ("MW", "%") for r in rows))

    def test_stated_locations_set_the_hub_and_others_say_the_city_is_unknown(self):
        rows = self.rows()
        cn20 = next(r for r in rows if r["campus"].startswith("Chindata CN20") and r["metric"] == "designed_it_capacity_mw")
        self.assertEqual((cn20["hub"], cn20["value"], cn20["period"]), ("Shanxi (Datong; outside the 8 hubs)", "49", "2022-12-31"))
        cn08 = next(r for r in rows if r["campus"] == "Chindata CN08" and r["metric"] == "utilized_it_capacity_mw")
        self.assertIn("do not give this data centre's city", cn08["hub"])
        self.assertIn("not a power measurement", cn08["note"])

    def test_updating_the_disclosures_file_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_operator_disclosures.csv"
            shutil.copy(ROOT / "data" / "cn_operator_disclosures.csv", path)
            with mock.patch.object(cf, "DISCLOSURES", path):
                cf.update_disclosures(self.rows())
                first = path.read_text(encoding="utf-8")
                cf.update_disclosures(self.rows())
                self.assertEqual(path.read_text(encoding="utf-8"), first)


class LocationsAndSearch(unittest.TestCase):
    def test_every_location_names_a_listed_source_and_quotes_it(self):
        locations = cf.read_locations()
        self.assertIn("CN20", locations)
        for code, row in locations.items():
            self.assertIn(row["source_key"], cf.DOCS, code)
            self.assertTrue(row["quote"] and row["hub"] and row["hub_basis"], code)
            if code != "CN10":  # CN10's quote is the prospectus footnote attached to its row, which does not repeat the code
                self.assertIn(code, row["quote"])

    def test_quotes_match_cached_documents_when_present(self):
        texts = {k: t for k in cf.DOCS if (t := cf.cached_text(k)) is not None}
        if not all(row["source_key"] in texts for row in cf.read_locations().values()):
            self.skipTest("source documents are not cached; run tools/chindata_filings.py fetch")
        self.assertEqual(cf.verify_locations(cf.read_locations(), texts), [])

    def test_hub_mentions_find_spelling_variants_and_nearby_figures(self):
        found = cf.hub_mentions("x", "Our Ulanqab campus has 100 MW in service. We also operate in Gui’an and Hohhot.")
        self.assertEqual([m["hub"] for m in found], ["Ulanqab", "Horinger", "Gui'an"])
        self.assertIn("100 MW", found[0]["figures_nearby"])


class DisclosuresFile(unittest.TestCase):
    def test_table_rows_in_the_file_are_consistent(self):
        with (ROOT / "data" / "cn_operator_disclosures.csv").open(newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["note"].startswith(cf.TAG)]
        if not rows:
            self.skipTest("no per-data-centre rows yet")
        self.assertEqual({r["period"] for r in rows}, {"2020-06-30", "2021-12-31", "2022-12-31"})
        self.assertTrue(all(r["source_url"] in {d.sec_url for d in cf.DOCUMENTS if d.role == "tables"} for r in rows))
        self.assertTrue(all((r["unit"] == "%") == r["metric"].endswith("_pct") for r in rows))


if __name__ == "__main__":
    unittest.main()
