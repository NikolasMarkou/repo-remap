import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import module_tree as mt  # noqa: E402


def make_tree(root: Path, spec: dict):
    """spec: {relative_dir: [file names]}; creates dirs and empty files."""
    for rel, files in spec.items():
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            (d / f).write_text("x")


class IgnoreRules(unittest.TestCase):
    def test_named_dirs_ignored(self):
        for name in ("node_modules", "dist", "build", "__pycache__", "venv"):
            self.assertTrue(mt.is_ignored_dir(name), name)

    def test_dotted_dirs_ignored_except_github(self):
        self.assertTrue(mt.is_ignored_dir(".hidden"))
        self.assertFalse(mt.is_ignored_dir(".github"))

    def test_plain_dir_not_ignored(self):
        self.assertFalse(mt.is_ignored_dir("src"))

    def test_doc_files_not_counted(self):
        self.assertFalse(mt.is_counted_file("README.md"))
        self.assertFalse(mt.is_counted_file("CLAUDE.md"))

    def test_dotfiles_not_counted(self):
        self.assertFalse(mt.is_counted_file(".env"))

    def test_generated_suffixes_not_counted(self):
        for f in ("a.pyc", "b.min.js", "c.lock", "d.snap"):
            self.assertFalse(mt.is_counted_file(f), f)

    def test_source_file_counted(self):
        self.assertTrue(mt.is_counted_file("main.py"))


class Qualifying(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_threshold_is_strictly_greater(self):
        make_tree(self.root, {"two": ["a", "b"], "three": ["a", "b", "c"]})
        tree = mt.scan(str(self.root))
        quals = mt.qualifying(tree, str(self.root), 2)
        self.assertNotIn(str(self.root / "two"), quals)
        self.assertIn(str(self.root / "three"), quals)

    def test_parent_qualifies_through_descendant(self):
        make_tree(self.root, {"pkg": ["one"], "pkg/leaf": ["a", "b", "c"]})
        tree = mt.scan(str(self.root))
        quals = mt.qualifying(tree, str(self.root), 2)
        self.assertIn(str(self.root / "pkg"), quals)

    def test_root_always_qualifies(self):
        make_tree(self.root, {".": ["single"]})
        tree = mt.scan(str(self.root))
        self.assertIn(str(self.root), mt.qualifying(tree, str(self.root), 2))

    def test_empty_scaffolding_dropped(self):
        make_tree(self.root, {"empty/deeper": [], "real": ["a", "b", "c"]})
        tree = mt.scan(str(self.root))
        quals = mt.qualifying(tree, str(self.root), 2)
        self.assertNotIn(str(self.root / "empty"), quals)

    def test_ignored_dirs_not_scanned(self):
        make_tree(self.root, {"node_modules/x": ["a", "b", "c"], "src": ["a", "b", "c"]})
        tree = mt.scan(str(self.root))
        self.assertNotIn(str(self.root / "node_modules"), tree)
        self.assertIn(str(self.root / "src"), tree)

    def test_min_files_raises_bar(self):
        make_tree(self.root, {"three": ["a", "b", "c"]})
        tree = mt.scan(str(self.root))
        self.assertNotIn(str(self.root / "three"), mt.qualifying(tree, str(self.root), 3))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_tree(self.root, {
            ".": ["top.py"],
            "src/core": ["a.py", "b.py", "c.py"],
            "src/core/fixtures": ["f1", "f2"],
            "src/adapters/stripe": ["a", "b", "c", "d"],
            "docs_only": ["README.md"],
        })
        (self.root / "src/core/README.md").write_text("r")
        (self.root / "src/core/CLAUDE.md").write_text("c")
        self._saved = set(mt.IGNORED_DIRS)

    def tearDown(self):
        mt.IGNORED_DIRS.clear()
        mt.IGNORED_DIRS.update(self._saved)
        self.tmp.cleanup()

    def run_main(self, *args):
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["module_tree.py", *args]), redirect_stdout(buf):
            code = mt.main()
        return code, buf.getvalue()

    def test_deepest_first_and_markers(self):
        code, out = self.run_main(str(self.root))
        self.assertEqual(code, 0)
        self.assertLess(out.index("-- depth 2 --"), out.index("-- depth 1 --"))
        self.assertLess(out.index("-- depth 1 --"), out.index("-- root --"))
        self.assertIn("[README+CLAUDE]", out)
        self.assertIn("src/adapters/stripe", out)
        self.assertIn("parent of 1", out)

    def test_skipped_section_lists_small_dirs(self):
        _, out = self.run_main(str(self.root))
        skipped = out.split("SKIPPED")[1]
        self.assertIn("src/core/fixtures", skipped)

    def test_ignore_flag_extends_set(self):
        _, out = self.run_main(str(self.root), "--ignore", "adapters")
        self.assertNotIn("stripe", out)

    def test_min_files_flag(self):
        _, out = self.run_main(str(self.root), "--min-files", "3")
        order = out.split("SKIPPED")[0]
        self.assertNotIn("src/core ", order)
        self.assertIn("src/adapters/stripe", order)

    def test_not_a_directory_exits_1(self):
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["module_tree.py", str(self.root / "nope")]), \
                mock.patch("sys.stderr", new=buf):
            self.assertEqual(mt.main(), 1)
        self.assertIn("not a directory", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
