import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_readme_parity as g  # noqa: E402

BADGES = (
    "[![Skill](https://img.shields.io/badge/Skill-v1.2.3-green.svg)](CHANGELOG.md)\n"
    "[![Tests](https://img.shields.io/badge/tests-42%20passing-brightgreen.svg)](x)\n"
)


class VersionBadge(unittest.TestCase):
    def test_match(self):
        self.assertTrue(g.check_version_badge(BADGES, "1.2.3")["ok"])

    def test_wrong_version(self):
        r = g.check_version_badge(BADGES, "1.2.4")
        self.assertFalse(r["ok"])
        self.assertTrue(r["found"])
        self.assertEqual(r["readme"], "1.2.3")

    def test_bare_substring_is_not_a_badge(self):
        r = g.check_version_badge("Skill-v1.2.3-green.svg mentioned in prose", "1.2.3")
        self.assertFalse(r["ok"])
        self.assertFalse(r["found"])

    def test_empty(self):
        self.assertFalse(g.check_version_badge("", "1.0.0")["ok"])


class TestBadge(unittest.TestCase):
    def test_match(self):
        self.assertTrue(g.check_test_badge(BADGES, "42")["ok"])

    def test_wrong_count(self):
        r = g.check_test_badge(BADGES, "41")
        self.assertFalse(r["ok"])
        self.assertEqual(r["readme"], "42")

    def test_bare_substring_is_not_a_badge(self):
        self.assertFalse(g.check_test_badge("tests-42%20passing", "42")["found"])


class Cli(unittest.TestCase):
    def write(self, version, count, readme):
        d = Path(self.tmp.name)
        (d / "VERSION").write_text(version + "\n")
        (d / "TEST_COUNT").write_text(count + "\n")
        (d / "README.md").write_text(readme)
        return d

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass(self):
        self.assertEqual(g.main([str(self.write("1.2.3", "42", BADGES))]), 0)

    def test_fail_on_version(self):
        self.assertEqual(g.main([str(self.write("9.9.9", "42", BADGES))]), 1)

    def test_fail_on_count(self):
        self.assertEqual(g.main([str(self.write("1.2.3", "7", BADGES))]), 1)

    def test_missing_file_fails(self):
        self.assertEqual(g.main([self.tmp.name]), 1)

    def test_live_repo_passes(self):
        self.assertEqual(g.main([str(Path(__file__).resolve().parents[2])]), 0)


if __name__ == "__main__":
    unittest.main()
