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
        self.assertGreaterEqual(len(mk), 4)
        self.assertIn("check_agent_wiring.py", mk)

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


class AgentsAndReferences(unittest.TestCase):
    """Drift in the agents/ and references/ copy, validate and sync steps."""

    DIRS = ("agents", "references")
    CITATIONS = (r"scripts/[a-z0-9_]+\.py", r"references/[a-z0-9_-]+\.md",
                 r"agents/rr-[a-z-]+\.md")

    def test_build_copies_both_dirs(self):
        mk, ps = make_target("build"), ps_function("Invoke-Build")
        self.assertIn("cp $(AGENT_FILES) $(BUILD_DIR)/$(SKILL_NAME)/agents/", mk)
        self.assertIn("cp $(REFERENCE_FILES) $(BUILD_DIR)/$(SKILL_NAME)/references/", mk)
        self.assertIn('foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName (Join-Path $target "agents")', ps)
        self.assertIn('foreach ($f in (Get-ReferenceFiles)) { Copy-Item $f.FullName (Join-Path $target "references")', ps)

    def test_combined_inlines_references_then_agents_before_note(self):
        mk, ps = make_target("build-combined"), ps_function("Invoke-BuildCombined")
        self.assertIn("for f in $(REFERENCE_FILES) $(AGENT_FILES); do", mk)
        self.assertLess(ps.index("(Get-ReferenceFiles)"), ps.index("(Get-AgentFiles)"))
        self.assertIn('echo "<!-- file: $${f#src/} -->"', mk)
        self.assertIn("<!-- file: $rel -->", ps)
        self.assertLess(mk.index("<!-- file:"), mk.index("> **Note**"))
        ps_body = ps[ps.index("$body = Get-Content"):]
        self.assertLess(ps_body.index("<!-- file:"), ps_body.index("$note -join"))

    def test_validate_citation_patterns_agree(self):
        mk, ps = make_target("validate"), ps_function("Invoke-Validate")
        for pat in self.CITATIONS:
            self.assertIn(f"grep -oE '{pat}'", mk, pat)
            self.assertIn(f'[regex]::Matches($skill, "{pat}")', ps, pat)

    def test_validate_checks_both_dirs_exist(self):
        mk, ps = make_target("validate"), ps_function("Invoke-Validate")
        for d in self.DIRS:
            self.assertIn(f'test -d src/{d} || {{ echo "ERROR: src/{d}/ directory not found"; exit 1; }}', mk)
            self.assertIn(f'if (-not (Test-Path "src/{d}")) {{ $errors += "src/{d}/ directory not found" }}', ps)

    def test_validate_agent_frontmatter_keys_agree(self):
        mk = re.search(r"for key in ([a-z ]+); do", make_target("validate"))
        ps = re.search(r"foreach \(\$key in @\(([^)]*)\)\)", ps_function("Invoke-Validate"))
        self.assertIsNotNone(mk)
        self.assertIsNotNone(ps)
        self.assertEqual(mk.group(1).split(), ["name", "description", "tools"])
        self.assertEqual(re.findall(r'"([a-z]+)"', ps.group(1)), ["name", "description", "tools"])
        self.assertIn('grep -q "^$$key:" "$$f"', make_target("validate"))
        self.assertIn('-notmatch "(?m)^${key}:"', ps_function("Invoke-Validate"))

    def test_validate_runs_agent_wiring_gate(self):
        self.assertIn("$(PYTHON) src/scripts/check_agent_wiring.py || exit 1", make_target("validate"))
        self.assertIn("& $Python src/scripts/check_agent_wiring.py", ps_function("Invoke-Validate"))
        self.assertNotIn("check_agent_wiring.py", make_target("test"))
        self.assertNotIn("check_agent_wiring.py", ps_function("Invoke-Test"))

    def test_sync_prunes_then_copies_references_and_rr_agents_only(self):
        mk, ps = make_target("sync-skill"), ps_function("Invoke-SyncSkill")
        self.assertIn("AGENT_INSTALL_DIR := $(HOME)/.claude/agents", MAKEFILE)
        self.assertIn('Join-Path $HOME ".claude/agents"', ps)
        for prune, copy in (("rm -f $(SKILL_INSTALL_DIR)/references/*.md",
                             "cp $(REFERENCE_FILES) $(SKILL_INSTALL_DIR)/references/"),
                            ("rm -f $(AGENT_INSTALL_DIR)/rr-*.md",
                             "cp $(AGENT_FILES) $(AGENT_INSTALL_DIR)/")):
            self.assertLess(mk.index(prune), mk.index(copy))
        for prune, copy in (('(Join-Path $install "references") -Filter "*.md"',
                             'foreach ($f in (Get-ReferenceFiles)) { Copy-Item'),
                            ('Get-ChildItem $agentInstall -Filter "rr-*.md"',
                             'foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName $agentInstall')):
            self.assertLess(ps.index(prune), ps.index(copy))
        # ~/.claude/agents is shared: every prune there must be scoped to rr-*.md.
        for line in mk.splitlines():
            if "rm " in line and "AGENT_INSTALL_DIR" in line:
                self.assertIn("$(AGENT_INSTALL_DIR)/rr-*.md", line, line)
        for line in ps.splitlines():
            if "Remove-Item" in line and "$agentInstall" in line:
                self.assertIn('-Filter "rr-*.md"', line, line)

    def test_sync_compares_references_and_agents(self):
        mk, ps = make_target("sync-skill"), ps_function("Invoke-SyncSkill")
        self.assertNotIn("diff -rq src/references", mk)
        self.assertIn('diff -q "$$f" "$(SKILL_INSTALL_DIR)/references/$$(basename "$$f")"', mk)
        self.assertIn('diff -q "$$f" "$(AGENT_INSTALL_DIR)/$$(basename "$$f")"', mk)
        self.assertGreaterEqual(mk.count('ERROR: sync diff mismatch'), 2)
        self.assertIn('ERROR: sync diff mismatch: references/', ps)
        self.assertIn("foreach ($agentFile in (Get-AgentFiles))", ps)
        self.assertIn('ERROR: sync-skill shipped dev-only scripts into the install', mk)
        self.assertIn('ERROR: sync-skill shipped dev-only scripts into the install', ps)


    def test_sync_installs_and_compares_skill_agents_dir(self):
        # SKILL.md reads <skill-path>/agents/rr-*.md, so sync must install there too, not only
        # into the shared ~/.claude/agents.
        mk, ps = make_target("sync-skill"), ps_function("Invoke-SyncSkill")
        self.assertIn("$(SKILL_INSTALL_DIR)/references $(SKILL_INSTALL_DIR)/agents $(AGENT_INSTALL_DIR)", mk)
        prune, copy = "rm -f $(SKILL_INSTALL_DIR)/agents/*.md", "cp $(AGENT_FILES) $(SKILL_INSTALL_DIR)/agents/"
        self.assertLess(mk.index(prune), mk.index(copy))
        self.assertIn('diff -q "$$f" "$(SKILL_INSTALL_DIR)/agents/$$(basename "$$f")" '
                      '|| { echo "ERROR: sync diff mismatch"; exit 1; }', mk)
        self.assertIn('case " $(notdir $(AGENT_FILES)) " in', mk)
        self.assertIn("ERROR: sync diff mismatch: unexpected agents/$$n", mk)
        self.assertIn('$skillAgents = Join-Path $install "agents"', ps)
        self.assertLess(ps.index('Get-ChildItem $skillAgents -Filter "*.md"'),
                        ps.index("foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName $skillAgents"))
        self.assertIn('($srcAgents -join "|") -ne ($dstAgents -join "|")', ps)
        self.assertIn('ERROR: sync diff mismatch: agents/', ps)
        self.assertIn("(Join-Path $skillAgents $agentFile.Name)", ps)
        self.assertIn("(Join-Path $agentInstall $agentFile.Name)", ps)


class RepoDocsExcluded(unittest.TestCase):
    """src/agents/ and src/references/ hold repo docs (README.md, CLAUDE.md) that never ship."""

    MK_REFS = ("REFERENCE_FILES := $(sort $(filter-out src/references/README.md "
               "src/references/CLAUDE.md,$(wildcard src/references/*.md)))")
    MK_AGENTS = "AGENT_FILES := $(sort $(wildcard src/agents/rr-*.md))"
    PS_REFS = ("Get-ChildItem src/references -Filter *.md -File | "
               "Where-Object { $_.Name -notin @('README.md','CLAUDE.md') }")
    PS_AGENTS = "Get-ChildItem src/agents -Filter rr-*.md -File"
    STEPS = (("build", "Invoke-Build"), ("build-combined", "Invoke-BuildCombined"),
             ("sync-skill", "Invoke-SyncSkill"))

    def test_reference_set_excludes_repo_docs_in_both_channels(self):
        self.assertIn(self.MK_REFS, MAKEFILE)
        self.assertIn(self.PS_REFS, ps_function("Get-ReferenceFiles"))

    def test_agent_set_is_rr_only_in_both_channels(self):
        self.assertIn(self.MK_AGENTS, MAKEFILE)
        self.assertIn(self.PS_AGENTS, ps_function("Get-AgentFiles"))
        self.assertIn("for f in src/agents/rr-*.md; do", make_target("validate"))
        self.assertIn("$agents = Get-AgentFiles", ps_function("Invoke-Validate"))

    def test_every_step_uses_the_filtered_sets(self):
        for mk_name, ps_name in self.STEPS:
            mk, ps = make_target(mk_name), ps_function(ps_name)
            self.assertIn("$(REFERENCE_FILES)", mk, mk_name)
            self.assertIn("$(AGENT_FILES)", mk, mk_name)
            self.assertIn("(Get-ReferenceFiles)", ps, ps_name)
            self.assertIn("(Get-AgentFiles)", ps, ps_name)

    def test_no_unfiltered_glob_of_either_dir(self):
        for mk_name, ps_name in self.STEPS + (("validate", "Invoke-Validate"),):
            mk, ps = make_target(mk_name), ps_function(ps_name)
            for bad in ("src/references/*.md", "src/agents/*.md"):
                for line in mk.splitlines():
                    if bad in line:
                        self.assertIn("ERROR: no files match", line, f"{mk_name}: {line}")
            self.assertNotIn('Get-ChildItem "src/references"', ps, ps_name)
            self.assertNotIn('Get-ChildItem "src/agents" -Filter "*.md"', ps, ps_name)
            self.assertNotIn('"src/references/*.md" (Join-Path', ps, ps_name)
            self.assertNotIn('"src/agents/*.md"', ps, ps_name)

    def test_sync_rejects_extra_installed_reference(self):
        mk = make_target("sync-skill")
        self.assertIn('case " $(notdir $(REFERENCE_FILES)) " in', mk)
        self.assertIn("ERROR: sync diff mismatch: unexpected references/$$n", mk)
        self.assertIn('($srcRefs -join "|") -ne ($dstRefs -join "|")', ps_function("Invoke-SyncSkill"))


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
