# CLAUDE.md

Guidance for working with the Repo Remap codebase.

## Project Purpose

Claude Code skill that rebuilds a repository's documentation as a bottom-up tree of self-contained `README.md` (for people) and `CLAUDE.md` (for Claude) files. Leaves are documented first from their source; each parent is written from its children's finished docs. The skill is one protocol file plus one Python script.

Use cases: stale docs after a refactor, repos with no per-module docs, onboarding a person or an agent to an unfamiliar codebase.

## Repository Structure

```
repo-remap/
├── README.md                          # User documentation (badges gated against VERSION and TEST_COUNT)
├── LICENSE                            # Apache License 2.0
├── VERSION                            # Single source of truth for the version number
├── TEST_COUNT                         # Live unittest pass count, gated by check_test_count.py
├── CHANGELOG.md                       # Keep a Changelog; top entry must equal VERSION
├── CLAUDE.md                          # This file
├── Makefile                           # Unix/Linux/macOS build script (reads VERSION)
├── build.ps1                          # Windows PowerShell 7+ build script (reads VERSION)
└── src/
    ├── SKILL.md                       # The protocol: definitions, passes, formats, checklist
    └── scripts/
        ├── module_tree.py             # Module mapper, prints processing order deepest first (shipped)
        ├── test_module_tree.py        # unittest suite
        ├── check_readme_parity.py     # Gate: README badges == VERSION and TEST_COUNT (validate)
        ├── check_changelog_parity.py  # Gate: first "## [X.Y.Z]" == VERSION (validate)
        ├── check_ignore_parity.py     # Gate: README ignore paragraph == IGNORED_DIRS/IGNORED_SUFFIXES (validate)
        ├── check_test_count.py        # Gate: TEST_COUNT == live suite (test only, never validate)
        ├── test_check_*.py            # One suite per gate
        └── test_build_channels.py     # Lockstep: Makefile and build.ps1 agree
```

Only `SKILL.md`, `scripts/module_tree.py`, `README.md`, `LICENSE`, `CHANGELOG.md` and `VERSION` ship in the package. `check_*.py` and `test_*.py` are dev-only.

## Key Commands

### Module mapper

Run from any project root, where `<skill-path>` is the installed skill directory:

```bash
python3 <skill-path>/scripts/module_tree.py <repo-root>                 # processing order, deepest first
python3 <skill-path>/scripts/module_tree.py <repo-root> --min-files 3   # coarser tree
python3 <skill-path>/scripts/module_tree.py <repo-root> --ignore fixtures generated
```

Exit 1 if the root is not a directory, 0 otherwise. It never writes files.

### Activation triggers

"remap this repo", "the docs are out of date", "document every module", "generate CLAUDE.md files across the codebase", "re-onboard me to this project".

## Protocol Reference

Complete spec in `src/SKILL.md`. Key sections: Definitions, Workflow (Step 0, Pass 1 to 3), Self-containment, README.md format, CLAUDE.md format, Style constraints, Checklist.

Do not duplicate protocol content here. Read `src/SKILL.md` directly.

## Working with This Codebase

### File modification guidelines

- `src/SKILL.md` is the protocol. Its frontmatter must keep `name:`, `description:` and the three placeholders `__SKILL_VERSION__`, `__SKILL_DATE__`, `__SKILL_COMMIT__`; the build substitutes them. Never write a literal version there.
- `src/scripts/module_tree.py` is standard library only, Python 3.8+. Its `IGNORED_DIRS`, `IGNORED_FILES` and `IGNORED_SUFFIXES` are mirrored in README's "Ignored by default" paragraph and in the Definitions section of `src/SKILL.md`. Change all three together; the README half is gated.
- `VERSION` is the single source of truth. `Makefile` and `build.ps1` read it. A release bumps `VERSION`, adds a `CHANGELOG.md` entry at the top, and updates the README version badge.
- `TEST_COUNT` holds the live pass count. After adding or removing tests, run the suite, write the number, and update the README tests badge.
- `Makefile` and `build.ps1` are one fact in two places. Any change to a target, a gate invocation, the lint list, the test command or the combined-file Note is made in both, and `test_build_channels.py` fails when they drift.
- Commit subjects use a bracketed area tag: `[skill] ...`, `[script] ...`, `[build] ...`, `[docs] ...`.

### Tech stack

- Python 3.8+ standard library only. No pip dependencies, no linters that need installing.
- Markdown documentation.
- Make and PowerShell 7+ for the build channels.

### Build commands

```bash
# Unix/Linux/macOS
make build                   # Stage build/repo-remap/ with placeholders substituted
make build-combined          # Single-file SKILL.md with a trailing note (no script)
make package                 # Zip package (default), runs validate first
make package-combined        # Single-file skill into dist/
make package-tar             # Tarball package
make validate                # Structure and parity gates, fast and suite-free
make lint                    # py_compile every script
make test                    # lint, unittest discovery, TEST_COUNT gate
make clean                   # Remove build/ and dist/
make list                    # Show package contents
make sync-skill              # Opt-in: deploy to ~/.claude/skills/repo-remap

# Windows (PowerShell 7+)
.\build.ps1 <same target names>
```

Python is `python3` by default; override with `PYTHON=... make test` or `$env:PYTHON`.

### Validation checklist

- [ ] `make validate` passes (or `.\build.ps1 validate`)
- [ ] `make test` passes, and `TEST_COUNT` equals the live `Ran N tests` count (enforced by `check_test_count.py`, run by `make test` only; `validate` must stay fast)
- [ ] README version badge and tests badge match `VERSION` and `TEST_COUNT` (enforced by `check_readme_parity.py`). Both are matched as whole shields.io badges, never as a bare substring; do not loosen either regex
- [ ] `CHANGELOG.md` first `## [X.Y.Z] - YYYY-MM-DD` entry equals `VERSION` (enforced by `check_changelog_parity.py`; a missing or unparseable file is a FAIL, not a skip). There is no `[Unreleased]` section
- [ ] README "Ignored by default" paragraph agrees with `IGNORED_DIRS` and `IGNORED_SUFFIXES` (enforced by `check_ignore_parity.py`): every non-dotted dir and every suffix is listed, nothing unknown is listed, and the sentence "Dotted directories are skipped except `.github`" is present. A paragraph with fewer than 10 names fails the floor rather than passing vacuously
- [ ] `src/SKILL.md` has `name:`, `description:` and the three `__SKILL_*__` placeholders; every `scripts/<x>.py` it cites exists under `src/scripts/`
- [ ] Definitions in `src/SKILL.md` match the qualifying logic in `module_tree.py` (more than N direct files, or a qualifying descendant; root always qualifies)
- [ ] The Makefile never uses `|| ( ... exit 1 )` inside a `for` loop. `exit 1` in a subshell ends only that subshell and a loop's status is its last iteration's, so an earlier failure would print ERROR and still pass. Use `|| { echo ...; exit 1; }`. Probe any repair with a non-last entry
- [ ] `build.ps1` starts with `#Requires -Version 7`, names `-Encoding utf8` on every `Get-Content` and `Set-Content`, never wraps a gate in a `Test-Path` skip, and exits 1 on an unknown command. No PowerShell runs in the usual development environment here, so every claim about that channel is verified by reading it and by `test_build_channels.py`, not by running it. Say so when you report on it
- [ ] `make list` shows no `check_*.py` or `test_*.py`; `SCRIPT_FILES` in the Makefile and `$ScriptFiles` in `build.ps1` name only `module_tree.py`
- [ ] `grep -c __SKILL_ build/repo-remap/SKILL.md` is 0 after `make build`
- [ ] Generated output still obeys the style constraints in `src/SKILL.md` (no emojis, no em dashes, no preambles)

## Updating Local Skill

When asked to "update local skill", run the sync target. This is the procedure, not one option among several:

```bash
make sync-skill          # Unix/Linux/macOS
.\build.ps1 sync-skill   # Windows
```

It prunes `~/.claude/skills/repo-remap/scripts/*.py` before copying, copies `SKILL.md`, `module_tree.py`, `README.md`, `LICENSE`, `CHANGELOG.md` and `VERSION`, refuses if any dev-only script leaked into the install, and verifies the synced files with `diff -q`, failing loudly on any mismatch. Prune-before-copy is the point: `cp` alone cannot remove a file that was deleted from the repo, so a copy-only sync leaves orphans in the install forever.

### Fallback (no prune) if make and PowerShell are unavailable

```bash
mkdir -p ~/.claude/skills/repo-remap/scripts
cp src/SKILL.md ~/.claude/skills/repo-remap/SKILL.md
cp src/scripts/module_tree.py ~/.claude/skills/repo-remap/scripts/    # never the check_*.py or test_*.py files
cp README.md LICENSE CHANGELOG.md VERSION ~/.claude/skills/repo-remap/
diff -q src/SKILL.md ~/.claude/skills/repo-remap/SKILL.md
diff -q src/scripts/module_tree.py ~/.claude/skills/repo-remap/scripts/module_tree.py
ls ~/.claude/skills/repo-remap/scripts/                                 # must list module_tree.py only
```

Any file present only in the install is an orphan the fallback cannot remove; delete it by hand.
