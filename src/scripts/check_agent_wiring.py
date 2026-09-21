#!/usr/bin/env python3
"""Gate: src/agents/rr-*.md, src/SKILL.md and src/references/ are wired together.

Checks agent frontmatter, that workers cannot spawn, that the orchestrator's
Agent(...) list matches the agent files, that every cited agent and reference
exists, and that rr-verifier runs on sonnet. A missing SKILL.md or agents
directory is a FAIL, not a skip. Exit 0 when clean, 1 otherwise. Importable
without side effects.
"""

import re
import sys
from pathlib import Path

ORCHESTRATOR = "rr-orchestrator"
VERIFIER = "rr-verifier"
VERIFIER_MODEL = "sonnet"
REQUIRED_KEYS = ("name", "description", "tools", "model")

FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)$")
SPAWN_RE = re.compile(r"\bAgent\(([^)]*)\)")
AGENT_CITE_RE = re.compile(r"agents/(rr-[a-z-]+)\.md")
SUBAGENT_RE = re.compile(r"subagent_type[:=]\s*\"?(rr-[a-z-]+)")
REF_CITE_RE = re.compile(r"references/([a-z0-9_-]+)\.md")


def parse_frontmatter(text: str):
    """Return {key: raw value} from a leading --- block, or None if absent.

    Indented or "- " continuation lines are appended to the previous key, so
    YAML block lists and folded values keep their content.
    """
    m = FRONTMATTER_RE.match(text or "")
    if not m:
        return None
    fields = {}
    key = None
    for line in m.group(1).splitlines():
        km = KEY_RE.match(line)
        if km:
            key = km.group(1)
            fields[key] = km.group(2).strip()
        elif key is not None and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def spawn_list(tools_value: str):
    """Names inside Agent(...) on a tools value, or None when there is no Agent(."""
    m = SPAWN_RE.search(tools_value or "")
    if not m:
        return None
    return [n.strip().strip("\"'") for n in m.group(1).split(",") if n.strip()]


def has_agent_tool(value: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])Agent(?![A-Za-z0-9_])", value or "") is not None


def check(agents: dict, cited_texts: dict, references: set) -> list:
    """Return a list of (tag, message) defects.

    agents: {stem: file text} for src/agents/rr-*.md.
    cited_texts: {label: text} for SKILL.md and every src/agents/*.md.
    references: set of stems present under src/references/.
    """
    defects = []
    if not agents:
        return [("agents-missing", "src/agents/ has no rr-*.md files")]

    meta = {}
    for stem in sorted(agents):
        fm = parse_frontmatter(agents[stem])
        if fm is None:
            defects.append(("agent-frontmatter", f"agents/{stem}.md has no --- frontmatter block"))
            meta[stem] = {}
            continue
        meta[stem] = fm
        missing = [k for k in REQUIRED_KEYS if not fm.get(k)]
        if missing:
            defects.append(("agent-frontmatter", f"agents/{stem}.md missing keys: {', '.join(missing)}"))
        if fm.get("name") and fm["name"] != stem:
            defects.append(("agent-frontmatter", f"agents/{stem}.md name is '{fm['name']}', expected '{stem}'"))

    for stem in sorted(agents):
        if stem == ORCHESTRATOR:
            continue
        if not has_agent_tool(meta[stem].get("disallowedTools", "")):
            defects.append(("worker-can-spawn", f"agents/{stem}.md disallowedTools does not contain Agent"))

    if ORCHESTRATOR not in agents:
        defects.append(("orchestrator-wiring", f"agents/{ORCHESTRATOR}.md not found"))
    else:
        spawns = spawn_list(meta[ORCHESTRATOR].get("tools", ""))
        if spawns is None:
            defects.append(("orchestrator-wiring", f"{ORCHESTRATOR} tools has no Agent(...)"))
        else:
            for name in spawns:
                if name not in agents:
                    defects.append(("orchestrator-wiring", f"{ORCHESTRATOR} spawns '{name}' but agents/{name}.md not found"))
            for stem in sorted(agents):
                if stem != ORCHESTRATOR and stem not in spawns:
                    defects.append(("orchestrator-wiring", f"agents/{stem}.md is not listed in {ORCHESTRATOR} Agent(...)"))

    for label in sorted(cited_texts):
        text = cited_texts[label]
        agent_names = set(AGENT_CITE_RE.findall(text)) | set(SUBAGENT_RE.findall(text))
        for name in sorted(agent_names):
            if name not in agents:
                defects.append(("dangling-agent", f"{label} cites {name} but agents/{name}.md not found"))
        for ref in sorted(set(REF_CITE_RE.findall(text))):
            if ref not in references:
                defects.append(("dangling-reference", f"{label} cites references/{ref}.md but it is not found"))

    if VERIFIER in agents:
        model = meta[VERIFIER].get("model", "").strip("\"'")
        if model != VERIFIER_MODEL:
            defects.append(("verifier-model", f"{VERIFIER} model is '{model}', expected '{VERIFIER_MODEL}'"))

    return defects


def run(root: Path) -> int:
    src = root / "src"
    agents_dir = src / "agents"
    try:
        skill = (src / "SKILL.md").read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL [agent-wiring-io] {exc}")
        return 1
    if not agents_dir.is_dir():
        print("FAIL [agents-missing] src/agents/ does not exist")
        return 1
    try:
        agents = {p.stem: p.read_text(encoding="utf-8") for p in sorted(agents_dir.glob("rr-*.md"))}
        cited = {"SKILL.md": skill}
        for p in sorted(agents_dir.glob("*.md")):
            cited[f"agents/{p.name}"] = p.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL [agent-wiring-io] {exc}")
        return 1
    ref_dir = src / "references"
    references = {p.stem for p in ref_dir.glob("*.md")} if ref_dir.is_dir() else set()

    defects = check(agents, cited, references)
    if defects:
        for tag, msg in defects:
            print(f"FAIL [{tag}] {msg}")
        return 1
    workers = len(agents) - 1
    print(f"PASS agent wiring: {len(agents)} agents ({workers} workers), {len(references)} references, {len(cited)} files scanned")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[2]
    return run(root)


if __name__ == "__main__":
    raise SystemExit(main())
