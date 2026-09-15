"""RFW-32: URL extraction, skip rules and the report shape of tools/check_links.py, without any network."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import check_links as cl  # noqa: E402


class ExtractionTests(unittest.TestCase):
    def test_trailing_punctuation_and_brackets_are_stripped(self):
        self.assertEqual(cl.urls_in_text("see https://example.org/a/b."), ["https://example.org/a/b"])
        self.assertEqual(cl.urls_in_text("(https://example.org/x)"), ["https://example.org/x"])
        self.assertEqual(cl.urls_in_text("https://en.wikipedia.org/wiki/Foo_(bar)"), ["https://en.wikipedia.org/wiki/Foo_(bar)"])
        self.assertEqual(cl.urls_in_text("a https://a.org/1; b http://b.org/2, c"), ["https://a.org/1", "http://b.org/2"])

    def test_collect_reads_csv_cells_and_nested_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "data"
            (d / "sub").mkdir(parents=True)
            (d / "a.csv").write_text('id,url,notes\n1,https://one.org/p,"two links https://two.org/q and https://one.org/p"\n')
            (d / "sub" / "s.json").write_text(json.dumps({"x": [{"url": "https://three.org/r"}, "text https://one.org/p."]}))
            (d / "sub" / "bad.json").write_text("{not json")
            with patch.object(cl, "ROOT", Path(tmp)):
                found = cl.collect(d)
            self.assertEqual(set(found), {"https://one.org/p", "https://two.org/q", "https://three.org/r"})
            self.assertEqual(found["https://one.org/p"], {"data/a.csv", "data/sub/s.json"})

    def test_private_and_cache_folders_are_never_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "data"
            for sub in ("private", "cache/gee", "public"):
                (d / sub).mkdir(parents=True)
            (d / "private" / "labels.json").write_text(json.dumps({"run": "https://lab.example/secret-run"}))
            (d / "private" / "labels.csv").write_text("url\nhttps://lab.example/secret.csv\n")
            (d / "cache" / "gee" / "tile.json").write_text(json.dumps({"u": "https://cache.example/tile"}))
            (d / "public" / "ok.json").write_text(json.dumps({"u": "https://public.example/source"}))
            with patch.object(cl, "ROOT", Path(tmp)):
                found = cl.collect(d)
            self.assertEqual(set(found), {"https://public.example/source"})


class SkipAndReportTests(unittest.TestCase):
    def test_skip_hosts_are_not_fetched(self):
        class Gate:
            def allowed(self, url):
                raise AssertionError("must not touch the network")

            def request(self, *a):
                raise AssertionError("must not touch the network")

        rec = cl.check_one(Gate(), "https://www.sec.gov/Archives/x")
        self.assertTrue(rec["note"].startswith("skipped"))
        self.assertEqual(rec["status"], "")
        rec = cl.check_one(Gate(), "https://nominatim.openstreetmap.org/search?q=x")
        self.assertIn("Nominatim", rec["note"])

    def test_dead_definition(self):
        self.assertTrue(cl.is_dead(dict(status="404")))
        self.assertTrue(cl.is_dead(dict(status="error")))
        self.assertFalse(cl.is_dead(dict(status="200")))
        self.assertFalse(cl.is_dead(dict(status="")))
        self.assertFalse(cl.is_dead(dict(status="429")))
        self.assertTrue(cl.is_blocked(dict(status="403")))

    def test_run_writes_report_and_dead_file_with_archive_lookup(self):
        found = {"https://ok.org/a": {"data/x.csv"}, "https://gone.org/b": {"data/x.csv", "data/y.json"},
                 "https://www.sec.gov/z": {"data/x.csv"}}
        fake = {"https://ok.org/a": dict(status="200", final_url="https://ok.org/a/", note=""),
                "https://gone.org/b": dict(status="404", final_url="", note=""),
                "https://www.sec.gov/z": dict(status="", final_url="", note="skipped: SEC")}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(cl, "check_one", lambda gate, u: dict(url=u, **fake[u])), \
                patch.object(cl, "wayback", lambda s, u: ("https://web.archive.org/web/2024/" + u, "20240101000000")), \
                patch.object(cl.time, "sleep", lambda s: None):
            out = Path(tmp) / "link_check.csv"
            rows, summary = cl.run(found, out, progress=lambda m: None)
            report = list(csv.DictReader(open(out)))
            dead = list(csv.DictReader(open(out.with_name("link_check_dead.csv"))))
        self.assertEqual(summary, dict(urls=3, ok=1, dead=1, dead_with_archive=1, blocked=0, tls_untrusted=0, skipped=1, redirected=1))
        self.assertEqual(len(report), 3)
        self.assertEqual([d["url"] for d in dead], ["https://gone.org/b"])
        self.assertEqual(dead[0]["archive_url"], "https://web.archive.org/web/2024/https://gone.org/b")
        self.assertEqual(dead[0]["used_in"], "data/x.csv;data/y.json")
        self.assertEqual(dead[0]["n_files"], "2")


if __name__ == "__main__":
    unittest.main()
