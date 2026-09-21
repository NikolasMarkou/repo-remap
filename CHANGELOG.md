# Changelog

All notable changes to the Repo Remap project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
