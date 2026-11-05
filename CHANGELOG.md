# Changelog

All notable changes to the Repo Remap project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.3.1] - 2026-11-05

**Line budgets.** Fenced diagrams no longer count toward the `AGENTS.md` length budget.

### Changed

- `references/agents-format.md` says the 200-line target and 300-line ceiling exclude fenced diagram blocks and gives an `awk` command that counts the rest.
- `rr-verifier` has a new length check that flags only more than 300 counted lines, never diagram lines.
- `SKILL.md` checklist and the repo docs restate the budget with the diagram exemption.

## [1.3.0] - 2026-11-05

**Diagram convention.** Generated `README.md` files now draw diagrams as ASCII box diagrams; generated `AGENTS.md` files keep mermaid.

### Changed

- `references/readme-format.md` defines the ASCII box diagram style (text fence, box-drawing characters, arrows on every edge, T-junction fan-out, side channels, at most 78 characters wide) with an example; `references/agents-format.md` and `references/style.md` state the split by file type.
- `rr-verifier` has a new check: a mermaid fence in a `README.md`, a non-mermaid diagram in an `AGENTS.md`, or an over-wide ASCII diagram line is a defect.
- This repo's own `README.md` files (root, `src/`, `src/agents/`, `src/references/`, `src/scripts/`) now use ASCII box diagrams.

## [1.2.0] - 2026-10-05

**AGENTS.md rename.** The generated agent doc is now `AGENTS.md` instead of `CLAUDE.md`, matching the multi-tool agent-instruction standard.

### Added

- Legacy migration shim: `module_tree.py` keeps ignoring `CLAUDE.md` so mid-migration repos don't count it as source; writers read a legacy `CLAUDE.md` as claims when no `AGENTS.md` exists, then delete it; `rr-verifier` fails a module where legacy `CLAUDE.md` remains beside `AGENTS.md`.

### Changed

- Renamed this repo's own docs (`AGENTS.md` in root, `src/`, `src/agents/`, `src/references/`, `src/scripts/`) and the template (`src/references/agents-format.md`); all prompts, gates, tests, build channels and docs now emit `AGENTS.md`, with the audience reworded from Claude-only to agents.
- Historical entries below keep their original `CLAUDE.md` wording; this entry records the rename.

## [1.1.0] - 2026-09-21

**Subagent architecture.** The skill now runs as an orchestrator that hands every read and every doc write to a subagent, so the main context holds only the module list and short replies.

### Added

- `src/agents/`: `rr-orchestrator` (Step 0, scheduling, dispatch, retries), `rr-leaf-writer` (Pass 1), `rr-parent-writer` (Pass 2 and 3), `rr-verifier` (read-only check, `sonnet`). Workers cannot spawn agents.
- `src/references/`: `readme-format.md`, `claude-format.md`, `style.md`, moved out of `SKILL.md` so each worker reads only the rules it needs.
- `SKILL.md` sections: Orchestrator role assumption, Sub-agent architecture, Dispatch rules (spawn prompt contract, 5-line replies, parallel dispatch by depth, verifier retries, `general-purpose` and in-thread fallbacks), References.
- Gate `check_agent_wiring.py` with 13 tests: agent frontmatter, worker spawn ban, orchestrator wiring, dangling agent and reference citations, verifier model.
- Build channels ship `agents/` and `references/`, inline both in the combined file, validate cited references and agent frontmatter, and `sync-skill` installs `rr-*.md` into `~/.claude/agents/` with prune and diff. Only `rr-*.md` agents and the three reference files ship; module docs in those folders do not. `sync-skill` also installs the agents under the skill dir, where `SKILL.md` reads them. 14 new build-channel tests.

### Changed

- `SKILL.md` Workflow names the agent for each pass. The README.md and CLAUDE.md formats, style and self-containment rules now live in `references/`.
- Test count 75 to 102.

## [1.0.1] - 2026-09-21

**Documentation remap.** The repository's own docs were regenerated with the skill, bottom-up.

### Added

- `src/scripts/README.md` and `src/scripts/CLAUDE.md`: the mapper, the four gates and the six suites, with interfaces, data shapes, FAIL tags and the rules for adding scripts, gates and tests.
- `src/README.md` and `src/CLAUDE.md`: the protocol and the scripts directory as one unit, including the frontmatter placeholder contract.

### Changed

- `CLAUDE.md` rewritten in the module format (scope, architecture, interface, invariants, failure modes, working rules), keeping the release, validation and local-skill sync procedures.
- `README.md` project structure lists every gate and when it runs, and the Contributing section notes that builds need a git checkout, that the Makefile uses GNU `sed -i`, that `make test` runs the suite twice, and which files `sync-skill` compares.

### Fixed

- The README worked example now matches real `module_tree.py` output: 8 qualifying modules and 1 skipped, the `-- depth 0 --` group for `src` and `tests`, and `parent of 2` at the root. The pass narrative was updated to match.

### Notes

- `src/SKILL.md` Definitions lists a subset of `IGNORED_DIRS` and names "lockfile-only dirs", which `module_tree.py` does not implement. Documented, not changed.
- Test count: 75 (live run).

## [1.0.0] - 2026-09-21

**First packaged release.** The skill itself (the bottom-up remap protocol and the module mapper) already existed as two files; this release wraps them in the same build, versioning and gate skeleton used by the other skill repositories, so a release is a reproducible artifact rather than a directory copy.

### Added

- **Skill protocol** (`src/SKILL.md`): definitions, the three passes from leaf modules to the repo root, the self-containment rule, the README.md and CLAUDE.md contracts, style constraints and the completion checklist. The frontmatter now carries `version`, `released` and `commit` placeholders that the build substitutes; the source file is version-free by design.
- **Module mapper** (`src/scripts/module_tree.py`): read-only, standard library only. Prints qualifying modules deepest first with file counts and existing-doc markers, then the skipped directories. `--min-files` and `--ignore` flags.
- **Build channels**: `Makefile` (Unix/Linux/macOS) and `build.ps1` (Windows, PowerShell 7+), both reading `VERSION` as the single source of truth. Targets: `build`, `build-combined`, `package`, `package-combined`, `package-tar`, `validate`, `lint`, `test`, `clean`, `list`, `sync-skill`, `help`. The package ships `SKILL.md`, `scripts/module_tree.py`, `README.md`, `LICENSE`, `CHANGELOG.md` and `VERSION`; gate and test scripts never ship.
- **Mechanical gates** (`src/scripts/check_*.py`, run by `validate`): README version and test-count badges against `VERSION` and `TEST_COUNT` (matched as whole badges, never bare substrings), the first `CHANGELOG.md` entry against `VERSION` (missing file is a failure, not a skip), and the README "Ignored by default" paragraph against the mapper's `IGNORED_DIRS` and `IGNORED_SUFFIXES`. `check_test_count.py` compares `TEST_COUNT` with the live suite and runs under `test` only, so `validate` stays fast.
- **Tests** (`src/scripts/test_*.py`, stdlib `unittest`): the mapper's ignore rules, qualifying logic and CLI output; every gate's positive and negative paths; and lockstep tests pinning `Makefile` and `build.ps1` to the same targets, gate set, lint list, test command and combined-file note.
- **CLAUDE.md**: repository structure, commands, file modification guidelines, validation checklist and the local-skill sync procedure.

### Notes

- Test count: 75 (live run).
- The PowerShell channel is verified by reading and by the lockstep tests, not by execution; no PowerShell runs in the usual development environment.
