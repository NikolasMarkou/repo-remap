import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ignore_parity as g  # noqa: E402

DIRS = {"node_modules", "dist", ".git", ".idea"}
SUFFIXES = (".pyc", ".lock")
NAMES = ["node_modules", "dist", ".git", ".idea", ".pyc", ".lock", "a", "b", "c", "d"]


def paragraph(names, dotted=True):
    body = ", ".join(f"`{n}`" for n in names)
    tail = " " + g.DOTTED_SENTENCE + "." if dotted else ""
    return f"intro\n\n**Ignored by default**: {body}.{tail}\n\nnext\n"


class Compare(unittest.TestCase):
    def test_exact_parity(self):
        r = g.compare(paragraph(NAMES), DIRS | set("abcd"), SUFFIXES)
        self.assertEqual(r["missing_dirs"], [])
        self.assertEqual(r["missing_suffixes"], [])
        self.assertEqual(r["unknown"], [])
        self.assertTrue(r["dotted_sentence"])
        self.assertFalse(r["too_few"])

    def test_missing_dir_reported(self):
        r = g.compare(paragraph([n for n in NAMES if n != "dist"]), DIRS | set("abcd"), SUFFIXES)
        self.assertEqual(r["missing_dirs"], ["dist"])

    def test_dotted_dir_may_be_omitted(self):
        r = g.compare(paragraph([n for n in NAMES if n != ".idea"]), DIRS | set("abcd"), SUFFIXES)
        self.assertEqual(r["missing_dirs"], [])

    def test_missing_suffix_reported(self):
        r = g.compare(paragraph([n for n in NAMES if n != ".lock"]), DIRS | set("abcd"), SUFFIXES)
        self.assertEqual(r["missing_suffixes"], [".lock"])

    def test_unknown_name_reported(self):
        r = g.compare(paragraph(NAMES + ["ghost"]), DIRS | set("abcd"), SUFFIXES)
        self.assertEqual(r["unknown"], ["ghost"])

    def test_missing_dotted_sentence(self):
        r = g.compare(paragraph(NAMES, dotted=False), DIRS | set("abcd"), SUFFIXES)
        self.assertFalse(r["dotted_sentence"])

    def test_floor(self):
        r = g.compare(paragraph(NAMES[:3]), DIRS, SUFFIXES)
        self.assertTrue(r["too_few"])

    def test_no_paragraph(self):
        r = g.compare("nothing relevant\n", DIRS, SUFFIXES)
        self.assertFalse(r["paragraph_found"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_readme_fails(self):
        self.assertEqual(g.main([self.tmp.name]), 1)

    def test_paragraph_absent_fails(self):
        Path(self.tmp.name, "README.md").write_text("# x\n\nno list\n")
        self.assertEqual(g.main([self.tmp.name]), 1)

    def test_live_repo_passes(self):
        self.assertEqual(g.main([str(Path(__file__).resolve().parents[2])]), 0)


if __name__ == "__main__":
    unittest.main()
