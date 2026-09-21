import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_changelog_parity as g  # noqa: E402

LOG = "# Changelog\n\nintro\n\n## [1.2.3] - 2026-09-21\n\n### Added\n\n- x\n\n## [1.2.2] - 2026-09-01\n"


class TopEntry(unittest.TestCase):
    def test_parses_first_entry(self):
        self.assertEqual(g.top_entry(LOG), ("1.2.3", "2026-09-21"))

    def test_none_when_absent(self):
        self.assertIsNone(g.top_entry("# Changelog\n\nnothing here\n"))

    def test_unreleased_heading_is_not_an_entry(self):
        self.assertIsNone(g.top_entry("## [Unreleased]\n"))

    def test_check_ok(self):
        self.assertTrue(g.check(LOG, "1.2.3")["ok"])

    def test_check_mismatch(self):
        self.assertFalse(g.check(LOG, "1.2.2")["ok"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, version, log):
        (self.d / "VERSION").write_text(version + "\n")
        if log is not None:
            (self.d / "CHANGELOG.md").write_text(log)

    def test_pass(self):
        self.write("1.2.3", LOG)
        self.assertEqual(g.main([str(self.d)]), 0)

    def test_mismatch_fails(self):
        self.write("2.0.0", LOG)
        self.assertEqual(g.main([str(self.d)]), 1)

    def test_missing_changelog_is_fail_not_skip(self):
        self.write("1.2.3", None)
        self.assertEqual(g.main([str(self.d)]), 1)

    def test_unparseable_changelog_fails(self):
        self.write("1.2.3", "# Changelog\n\nno entries\n")
        self.assertEqual(g.main([str(self.d)]), 1)

    def test_live_repo_passes(self):
        self.assertEqual(g.main([str(Path(__file__).resolve().parents[2])]), 0)


if __name__ == "__main__":
    unittest.main()
