import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_agent_wiring as g  # noqa: E402

WORKERS = ("rr-leaf-writer", "rr-parent-writer", "rr-verifier")


def agent_text(name, tools="Read, Write", model="opus", disallowed="Agent", body=""):
    lines = ["---", f"name: {name}", f"description: {name} role", f"tools: {tools}", f"model: {model}"]
    if disallowed is not None:
        lines.append(f"disallowedTools: {disallowed}")
    return "\n".join(lines) + "\n---\n\n" + body + "\n"


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.src = self.d / "src"
        (self.src / "agents").mkdir(parents=True)
        (self.src / "references").mkdir()
        (self.src / "references" / "style.md").write_text("# Style\n")
        (self.src / "SKILL.md").write_text(
            "---\nname: repo-remap\n---\n\nRead agents/rr-orchestrator.md and references/style.md.\n"
        )
        spawn = "Agent(" + ", ".join(WORKERS) + "), Read, Bash"
        self.write_agent("rr-orchestrator", agent_text(
            "rr-orchestrator", tools=spawn, disallowed=None,
            body='Spawn with subagent_type: "rr-leaf-writer".'))
        for w in WORKERS:
            model = "sonnet" if w == "rr-verifier" else "opus"
            self.write_agent(w, agent_text(w, model=model))

    def tearDown(self):
        self.tmp.cleanup()

    def write_agent(self, name, text):
        (self.src / "agents" / f"{name}.md").write_text(text)

    def run_gate(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = g.main([str(self.d)])
        return code, buf.getvalue()

    def assert_fails_with(self, tag):
        code, out = self.run_gate()
        self.assertEqual(code, 1, out)
        self.assertIn(f"FAIL [{tag}]", out)

    def test_pass(self):
        code, out = self.run_gate()
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("PASS "))

    def test_missing_skill_is_fail_not_skip(self):
        (self.src / "SKILL.md").unlink()
        self.assert_fails_with("agent-wiring-io")

    def test_agents_missing(self):
        for p in (self.src / "agents").glob("*.md"):
            p.unlink()
        self.assert_fails_with("agents-missing")

    def test_agents_dir_absent(self):
        for p in (self.src / "agents").glob("*.md"):
            p.unlink()
        (self.src / "agents").rmdir()
        self.assert_fails_with("agents-missing")

    def test_frontmatter_name_mismatch(self):
        self.write_agent("rr-leaf-writer", agent_text("rr-leaf"))
        self.assert_fails_with("agent-frontmatter")

    def test_frontmatter_missing_key(self):
        self.write_agent("rr-parent-writer", "---\nname: rr-parent-writer\ndescription: x\ntools: Read\n"
                         "disallowedTools: Agent\n---\n")
        self.assert_fails_with("agent-frontmatter")

    def test_worker_can_spawn(self):
        self.write_agent("rr-parent-writer", agent_text("rr-parent-writer", disallowed="Write"))
        self.assert_fails_with("worker-can-spawn")

    def test_orchestrator_lists_missing_agent(self):
        self.write_agent("rr-orchestrator", agent_text(
            "rr-orchestrator", tools="Agent(rr-leaf-writer, rr-parent-writer, rr-verifier, rr-ghost), Read",
            disallowed=None))
        self.assert_fails_with("orchestrator-wiring")

    def test_orchestrator_omits_worker(self):
        self.write_agent("rr-orchestrator", agent_text(
            "rr-orchestrator", tools="Agent(rr-leaf-writer, rr-verifier), Read", disallowed=None))
        self.assert_fails_with("orchestrator-wiring")

    def test_dangling_agent(self):
        (self.src / "SKILL.md").write_text("Use subagent_type=\"rr-nobody\" and agents/rr-ghost.md.\n")
        code, out = self.run_gate()
        self.assertEqual(code, 1)
        self.assertEqual(out.count("FAIL [dangling-agent]"), 2)

    def test_dangling_reference(self):
        self.write_agent("rr-verifier", agent_text("rr-verifier", model="sonnet", body="See references/missing.md."))
        self.assert_fails_with("dangling-reference")

    def test_verifier_model(self):
        self.write_agent("rr-verifier", agent_text("rr-verifier", model="opus"))
        self.assert_fails_with("verifier-model")

    def test_live_repo_passes(self):
        self.assertEqual(g.main([str(Path(__file__).resolve().parents[2])]), 0)


if __name__ == "__main__":
    unittest.main()
