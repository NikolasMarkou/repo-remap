import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_test_count as g  # noqa: E402

OK_OUT = "....\n----------------------------------------------------------------------\nRan 4 tests in 0.010s\n\nOK\n"
SKIP_OUT = "Ran 4 tests in 0.010s\n\nOK (skipped=1)\n"
FAIL_OUT = "Ran 4 tests in 0.010s\n\nFAILED (failures=1)\n"


class Parse(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(g.parse_summary(OK_OUT), {"ran": 4, "ok": True})

    def test_ok_with_skips(self):
        self.assertEqual(g.parse_summary(SKIP_OUT), {"ran": 4, "ok": True})

    def test_failed(self):
        self.assertEqual(g.parse_summary(FAIL_OUT), {"ran": 4, "ok": False})

    def test_no_summary(self):
        self.assertEqual(g.parse_summary("garbage"), {"ran": None, "ok": False})

    def test_single_test_wording(self):
        self.assertEqual(g.parse_summary("Ran 1 test in 0.0s\n\nOK\n")["ran"], 1)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, count_text, output):
        (self.d / "TEST_COUNT").write_text(count_text)
        with mock.patch.object(g, "run_suite", return_value=output):
            return g.main([str(self.d)])

    def test_match(self):
        self.assertEqual(self.run_with("4\n", OK_OUT), 0)

    def test_drift(self):
        self.assertEqual(self.run_with("5\n", OK_OUT), 1)

    def test_suite_failure(self):
        self.assertEqual(self.run_with("4\n", FAIL_OUT), 1)

    def test_unavailable(self):
        self.assertEqual(self.run_with("4\n", "no output"), 1)

    def test_bad_count_file(self):
        self.assertEqual(self.run_with("many\n", OK_OUT), 1)

    def test_missing_count_file(self):
        with mock.patch.object(g, "run_suite", return_value=OK_OUT):
            self.assertEqual(g.main([str(self.d)]), 1)


if __name__ == "__main__":
    unittest.main()
