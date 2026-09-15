"""The public requests page stays in sync with REQUESTS_FOR_WORK.md, and its internal links resolve."""
import re
import unittest
from pathlib import Path

from tools import build_requests_page as page

ROOT = Path(__file__).resolve().parents[1]


class RequestsPageTests(unittest.TestCase):
    def test_committed_page_is_current(self):
        self.assertEqual((ROOT / "site" / "requests.html").read_text(encoding="utf-8"), page.build(),
                         "site/requests.html is out of date: run python tools/build_requests_page.py")

    def test_internal_links_resolve(self):
        html = page.build()
        ids = set(re.findall(r'id="([^"]+)"', html))
        targets = set(re.findall(r'href="#([^"]+)"', html))
        self.assertTrue(targets)
        self.assertEqual(sorted(targets - ids), [])

    def test_every_request_in_the_table_has_a_section_and_back(self):
        md = (ROOT / "REQUESTS_FOR_WORK.md").read_text(encoding="utf-8")
        for prefix in ("RFW", "PAID", "T"):
            in_table = set(re.findall(rf"^\| \[({prefix}-\d+)\]", md, flags=re.M))
            sections = set(re.findall(rf"^#### ({prefix}-\d+) ", md, flags=re.M))
            self.assertTrue(in_table, prefix)
            self.assertEqual(in_table, sections, prefix)

    def test_slug_matches_github_anchor_rules(self):
        self.assertEqual(page.slug("RFW-11 Near-field plume test for plants on a city's edge"),
                         "rfw-11-near-field-plume-test-for-plants-on-a-citys-edge")

    def test_page_loads_live_claims(self):
        html = page.build()
        self.assertIn('<p id="live-claims" class="claims-note" hidden></p>', html)
        self.assertIn('<script src="claims.js"></script>', html)
        self.assertTrue((ROOT / "site" / "claims.js").exists())

    def test_link_urls_are_escaped_once(self):
        out = page.render_markdown("[share](https://twitter.com/intent/tweet?text=a%20b&url=https%3A%2F%2Fx.test)")
        self.assertIn('href="https://twitter.com/intent/tweet?text=a%20b&amp;url=https%3A%2F%2Fx.test"', out)
        self.assertNotIn("&amp;amp;", out)

    def test_text_is_escaped(self):
        out = page.render_markdown("- **x** <script>alert(1)</script> `<b>`")
        self.assertNotIn("<script>", out)
        self.assertIn("<code>&lt;b&gt;</code>", out)


if __name__ == "__main__":
    unittest.main()
