"""tools/rebuild_site_data.py: a rebuild that only moves the build timestamp is not a change."""
import json
import unittest

from tools.rebuild_site_data import same_apart_from_timestamps as same


class TimestampOnlyTests(unittest.TestCase):
    def test_a_new_build_timestamp_alone_is_not_a_change(self):
        old = json.dumps(dict(generated="2026-09-15T12:00:00+00:00", sites=[1, 2]), indent=0)
        new = json.dumps(dict(generated="2026-09-16T08:00:00+00:00", sites=[1, 2]), indent=0)
        self.assertTrue(same("site/data/status.json", old, new))

    def test_content_changes_count(self):
        old = json.dumps(dict(generated="a", sites=[1, 2]))
        self.assertFalse(same("site/data/status.json", old, json.dumps(dict(generated="b", sites=[1, 3]))))
        self.assertFalse(same("site/data/status.json", old, json.dumps(dict(generated="a", sites=[1, 2], findings=[]))))

    def test_other_files_and_broken_json_compare_as_text(self):
        self.assertTrue(same("site/requests.html", "<p>x</p>", "<p>x</p>"))
        self.assertFalse(same("site/requests.html", '{"generated": 1}', '{"generated": 2}'))
        self.assertFalse(same("site/data/x.json", '{"generated": 1', '{"generated": 2'))


if __name__ == "__main__":
    unittest.main()
