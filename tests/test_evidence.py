"""Findings from requests for work (tools/evidence.py): the committed findings validate, each adapter reports what its
request merged, contributed rows with problems are refused with a reason, and an imagery verdict reaches a radar-found
entry's status lines."""
import csv
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import build_status
from tools import evidence as E

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    with (ROOT / rel).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class CommittedFindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.errors, cls.sites, cls.requests = E.collect(ROOT)
        cls.findings = [r for _, _, r in cls.rows]

    def test_every_committed_finding_validates(self):
        self.assertEqual(self.errors, [])

    def test_every_adapter_reads_committed_files_and_reports_its_request(self):
        counts = Counter(f["request"] for f in self.findings)
        for a in E.ADAPTERS:
            for rel in a["reads"]:
                self.assertTrue((ROOT / rel).exists(), f"{a['name']} reads {rel}")
            self.assertGreater(counts[a["request"]], 0, a["name"])

    def test_radar_review_keeps_every_verdict_visible(self):
        review = read("data/cn_radar_review.csv")
        mine = [f for f in self.findings if f["request"] == "RFW-01"]
        self.assertEqual(len(mine), len(review))
        on_entries = {f["subject"]: f["verdict"] for f in mine if f["verdict"]}
        self.assertEqual(on_entries, {r["site_id"]: r["verdict"] for r in review if r["site_id"] in self.sites})
        # structures that left the inventory are reported on their hub, without a verdict that would change the hub's lines
        rejected = [f for f in mine if not f["verdict"]]
        self.assertEqual(len(rejected), sum(r["site_id"] not in self.sites for r in review))
        self.assertTrue(all(f["subject"].endswith("_hub") or f["subject"] == "country:CN" for f in rejected))

    def test_chindata_totals_match_the_filings_notes(self):
        text = " ".join(f["finding"] for f in self.findings if f["request"] == "RFW-07")
        for figure in ("171 MW, 77.5 %", "399 MW, 287 MW", "517 MW, 466 MW"):
            self.assertIn(figure, text)

    def test_every_site_level_plume_series_is_reported(self):
        sensitivity = read("results_no2/plume_date_sensitivity.csv")
        series = {r["series"] for r in sensitivity if r["role"] == "site" and r["series"] in self.sites}
        self.assertEqual({f["subject"] for f in self.findings if f["request"] == "RFW-14" and f["subject"] != "global"}, series)

    def test_published_findings_link_to_their_request_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "evidence.json"
            per_site = E.build(ROOT, out=out)
            data = json.loads(out.read_text())
        page = (ROOT / "site" / "requests.html").read_text()
        self.assertEqual(len(data["findings"]), len(self.findings))
        for f in data["findings"]:
            self.assertIn(f'id="{f["request_anchor"]}"', page, f["request"])
            self.assertTrue(f["source_url"].startswith(("https://", "http://")))
        self.assertEqual(sum(len(v) for v in per_site.values()), sum(f["subject_type"] == "site" for f in data["findings"]))
        keys = [(E.request_key(f["request"]),) for f in data["findings"]]
        self.assertEqual(keys, sorted(keys))


class ContributedFindingsTests(unittest.TestCase):
    GOOD = dict(subject="site_a", request="RFW-04", answers="built", finding="Land for the campus was sold in March 2024.",
                confidence="medium", source="results/land.csv", period="2024-03", pull_request="31", recorded="2026-09-20")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for folder in ("data/evidence", "data/private", "results"):
            (self.root / folder).mkdir(parents=True)
        (self.root / "data/sites.csv").write_text("site_id,name,country\nsite_a,Site A,US\n")
        (self.root / "REQUESTS_FOR_WORK.md").write_text("#### RFW-04 Land transfer results for operators and start dates\n")
        (self.root / "results/land.csv").write_text("parcel\n1\n")
        (self.root / "data/private/records.csv").write_text("x\n1\n")

    def write(self, rows, header=None):
        with (self.root / "data/evidence/RFW-04.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header or E.COLUMNS)
            w.writeheader()
            w.writerows(rows)

    def errors(self):
        return E.collect(self.root, adapters=[])[1]

    def test_a_valid_row_is_published_with_links(self):
        self.write([self.GOOD])
        self.assertEqual(self.errors(), [])
        per_site = E.build(self.root, out=self.root / "evidence.json", adapters=[])
        f = per_site["site_a"][0]
        self.assertEqual(f["request_anchor"], "rfw-04-land-transfer-results-for-operators-and-start-dates")
        self.assertEqual(f["source_url"], f"{E.REPO}/blob/main/results/land.csv")
        self.assertEqual((f["pull_request"], f["subject_name"], f["origin"]), (31, "Site A", "data/evidence/RFW-04.csv"))

    def test_rows_with_problems_are_refused_with_a_reason(self):
        cases = [
            (dict(subject="nowhere"), "is not an inventory site_id"),
            (dict(subject="country:China"), "is not an inventory site_id"),
            (dict(request="RFW-99"), "is not a heading"),
            (dict(answers="power"), "answers must be one of"),
            (dict(confidence="certain"), "confidence must be one of"),
            (dict(finding=""), "finding is empty"),
            (dict(verdict="unclear"), "a verdict needs answers = where"),
            (dict(subject="country:US", answers="where", verdict="unclear"), "a verdict needs answers = where"),
            (dict(answers="where", verdict="probably"), "verdict must be one of"),
            (dict(source="results/missing.csv"), "neither a URL nor a file"),
            (dict(source="../outside.csv"), "neither a URL nor a file"),
            (dict(source="data/private/records.csv"), "must not point at private files"),
            (dict(period="spring 2024"), "period must look like"),
            (dict(recorded="20 Sep 2026"), "recorded must be a date"),
            (dict(pull_request="#31"), "pull_request must be a number"),
            (dict(finding="x" * (E.MAX_FINDING + 1)), "finding must be one line"),
        ]
        for change, reason in cases:
            with self.subTest(reason=reason, change=change):
                self.write([{**self.GOOD, **change}])
                self.assertTrue(any(reason in e for e in self.errors()), self.errors())

    def test_country_global_and_verdict_rows_are_accepted(self):
        self.write([{**self.GOOD, "subject": "country:CN"}, {**self.GOOD, "subject": "global", "period": "2024Q1..FY2025"},
                    {**self.GOOD, "answers": "where", "verdict": "data-hall complex"}])
        self.assertEqual(self.errors(), [])

    def test_a_misspelt_column_is_refused(self):
        header = [c if c != "confidence" else "confidance" for c in E.COLUMNS]
        self.write([{("confidance" if k == "confidence" else k): v for k, v in self.GOOD.items()}], header=header)
        self.assertTrue(any("unknown: confidance" in e for e in self.errors()), self.errors())

    def test_a_problem_stops_the_build(self):
        self.write([{**self.GOOD, "subject": "nowhere"}])
        with self.assertRaises(E.EvidenceError):
            E.build(self.root, write=False, adapters=[])


class VerdictTests(unittest.TestCase):
    def test_the_most_recently_recorded_verdict_applies(self):
        findings = [dict(verdict="unclear", recorded="2026-09-15", request="RFW-01"), dict(verdict="", recorded="2026-12-01"),
                    dict(verdict="data-hall complex", recorded="2026-10-02", request="RFW-04")]
        self.assertEqual(E.latest_verdict(findings)["request"], "RFW-04")
        same_day = [dict(verdict="unclear", recorded="2026-09-15"), dict(verdict="not a data centre", recorded="2026-09-15")]
        self.assertEqual(E.latest_verdict(same_day)["verdict"], "not a data centre")
        self.assertIsNone(E.latest_verdict([dict(verdict="")]))

    def test_radar_entry_lines_follow_the_verdict(self):
        self.assertEqual(build_status.review_note(None), "unconfirmed")
        self.assertEqual(build_status.review_note(dict(request="RFW-01", verdict="unclear")), "imagery review (RFW-01): unclear")
        running, load = build_status.radar_lines(None)
        self.assertIn("not confirmed as a data centre", running)
        running, load = build_status.radar_lines(dict(verdict="data-hall complex"))
        self.assertTrue(running.startswith("unknown:") and load.startswith("not estimated"))
        running, load = build_status.radar_lines(dict(verdict="not a data centre"))
        self.assertTrue(running.startswith("no:") and load.startswith("none"))


if __name__ == "__main__":
    unittest.main()
