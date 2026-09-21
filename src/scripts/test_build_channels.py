"""Lockstep tests: Makefile and build.ps1 must fail on the same conditions.

The PowerShell channel cannot run in the usual development environment, so
these tests are the only mechanical check that it names the same gates, the
same lint list, the same test command and the same targets as the Makefile.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
PS1 = (ROOT / "build.ps1").read_text(encoding="utf-8")

TARGETS = ["build", "build-combined", "package", "package-combined", "package-tar",
           "validate", "lint", "test", "clean", "list", "sync-skill", "help"]
GATE_RE = re.compile(r"check_[a-z_]+\.py")


def make_target(name):
    m = re.search(rf"^{re.escape(name)}:.*?\n((?:\t.*\n|\n)*)", MAKEFILE, re.M)
    return m.group(1) if m else ""


def ps_function(name):
    m = re.search(rf"^function {re.escape(name)} \{{\n(.*?)^\}}", PS1, re.M | re.S)
    return m.group(1) if m else ""


class Targets(unittest.TestCase):
    def test_makefile_declares_every_target(self):
        for t in TARGETS:
            self.assertIsNotNone(re.search(rf"^{re.escape(t)}:", MAKEFILE, re.M), t)

    def test_ps1_dispatches_every_target(self):
        for t in TARGETS:
            self.assertIn(f'"{t}"', PS1, t)

    def test_ps1_requires_powershell_7(self):
        self.assertTrue(PS1.startswith("#Requires -Version 7"))

    def test_ps1_names_utf8_on_every_read_and_write(self):
        for line in PS1.splitlines():
            if re.search(r"\b(Get-Content|Set-Content)\b", line):
                self.assertIn("-Encoding utf8", line, line)

    def test_unknown_command_exits_1(self):
        self.assertRegex(PS1, r"default\s*\{[^}]*exit 1")


class Gates(unittest.TestCase):
    def test_validate_runs_same_gates(self):
        mk = set(GATE_RE.findall(make_target("validate")))
        ps = set(GATE_RE.findall(ps_function("Invoke-Validate")))
        self.assertEqual(mk, ps)
        self.assertGreaterEqual(len(mk), 3)

    def test_test_target_runs_test_count_gate_and_validate_does_not(self):
        self.assertIn("check_test_count.py", make_target("test"))
        self.assertIn("check_test_count.py", ps_function("Invoke-Test"))
        self.assertNotIn("check_test_count.py", make_target("validate"))
        self.assertNotIn("check_test_count.py", ps_function("Invoke-Validate"))

    def test_no_gate_is_skip_wrapped_in_ps1(self):
        for line in ps_function("Invoke-Validate").splitlines():
            if GATE_RE.search(line):
                self.assertNotIn("Test-Path", line, line)

    def test_lint_lists_agree(self):
        mk = set(re.findall(r"src/scripts/[a-z_]+\.py", make_target("lint")))
        block = re.search(r"\$LintFiles = @\((.*?)\)", PS1, re.S).group(1)
        ps = set(re.findall(r"src/scripts/[a-z_]+\.py", block))
        self.assertIn("$LintFiles", ps_function("Invoke-Lint"))
        self.assertEqual(mk, ps)
        live = {f"src/scripts/{p.name}" for p in (ROOT / "src/scripts").glob("*.py")}
        self.assertEqual(mk, live)

    def test_unittest_discovery_matches(self):
        pat = r'unittest discover -s src/scripts -p "test_\*\.py"'
        self.assertRegex(make_target("test"), pat)
        self.assertRegex(ps_function("Invoke-Test"), pat)

    def test_makefile_loops_use_brace_groups(self):
        for line in MAKEFILE.splitlines():
            if line.lstrip().startswith(("#", "@#")):
                continue
            self.assertNotIn("|| (", line, "use || { ...; exit 1; } inside loops")

    def test_shipped_scripts_exclude_tests_and_gates(self):
        m = re.search(r"^SCRIPT_FILES := (.*)$", MAKEFILE, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).split(), ["src/scripts/module_tree.py"])
        self.assertIn('"src/scripts/module_tree.py"', PS1)
        self.assertNotIn("test_", ps_function("Invoke-Build"))


class CombinedNote(unittest.TestCase):
    def test_note_text_identical(self):
        mk = re.findall(r'@echo "(> [^"]*)" >> \$\(BUILD_DIR\)/\$\(SKILL_NAME\)-combined\.md',
                        make_target("build-combined"))
        ps = re.findall(r'^\s*"(> .*?)",?$', ps_function("Invoke-BuildCombined"), re.M)
        mk = [s.replace("\\`", "`").replace('\\"', '"') for s in mk]
        ps = [s.replace("``", "`").replace('""', '"').replace("`$", "$") for s in ps]
        self.assertTrue(mk)
        self.assertEqual(mk, ps)


if __name__ == "__main__":
    unittest.main()
