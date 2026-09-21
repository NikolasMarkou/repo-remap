# scripts

The Python scripts behind the Repo Remap skill, in `src/scripts/` of the repo-remap repository. One script ships to users; the rest are development gates and their tests.

## What it is for

Repo Remap is a Claude Code skill that rewrites a repository's docs as a tree of `README.md` and `CLAUDE.md` files, working from the deepest directories up to the root. Before any doc is written, something has to decide which directories get docs and in what order. `module_tree.py` does that, and it is the only script users receive.

The other scripts protect the repo that builds the skill. A "gate" is a small script that compares a few files and fails loudly when they disagree. The gates here check that the README badges, the changelog, the version file, the test count and the ignore lists all agree, and that the skill's agent files (`src/agents/rr-*.md`), reference files (`src/references/*.md`) and `src/SKILL.md` point at each other correctly. The tests also check that the two build scripts (`Makefile` for Unix, `build.ps1` for Windows) do the same things.

## How it works

`module_tree.py` walks a directory tree, counts the source files directly inside each directory, and marks a directory as worth documenting when it has more than 2 such files or contains a directory that is. The repo root always counts. It prints those directories deepest first, which is the order the skill writes docs in.

```mermaid
flowchart LR
    A[os.walk the repo] --> B[drop ignored dirs, count direct files]
    B --> C[mark qualifying dirs, deepest first]
    C --> D[drop dirs with no files anywhere below]
    D --> E[print by depth, then skipped dirs]
```

Each `check_*.py` gate reads a few files at the repo root, compares them, prints `PASS ...` or `FAIL [tag] ...`, and exits 0 (pass) or 1 (fail). Each `test_*.py` file is a standard `unittest` suite.

## Files

- `module_tree.py` - maps a repo into modules and prints the processing order. Shipped.
- `check_readme_parity.py` - README version badge must equal `VERSION`, tests badge must equal `TEST_COUNT`.
- `check_changelog_parity.py` - first `## [X.Y.Z] - YYYY-MM-DD` heading in `CHANGELOG.md` must equal `VERSION`.
- `check_ignore_parity.py` - README "Ignored by default" paragraph must agree with the ignore lists in `module_tree.py`.
- `check_agent_wiring.py` - agent files have valid frontmatter, worker agents cannot spawn other agents, the orchestrator lists exactly the worker agents, every cited agent and reference file exists, and `rr-verifier` runs on the `sonnet` model.
- `check_test_count.py` - runs the whole test suite and requires the pass count to equal `TEST_COUNT`.
- `test_module_tree.py` - tests for the mapper's ignore rules, qualifying logic and command line output (18 tests).
- `test_check_readme_parity.py` (12), `test_check_changelog_parity.py` (10), `test_check_ignore_parity.py` (11), `test_check_agent_wiring.py` (13), `test_check_test_count.py` (11) - one suite per gate.
- `test_build_channels.py` - checks that `Makefile` and `build.ps1` name the same targets, gates, lint list, test command, agent and reference handling, and combined-file note, and that both pick only `src/agents/rr-*.md` as agents and leave `README.md` and `CLAUDE.md` out of `src/references/`, and that `sync-skill` installs the `rr-*.md` agents both into the skill's own `agents/` folder and into `~/.claude/agents/` (27 tests).

102 tests in total.

## How to use it

Map a repository (run from anywhere, pass the repo root):

```bash
python3 src/scripts/module_tree.py .
python3 src/scripts/module_tree.py . --min-files 3
python3 src/scripts/module_tree.py . --ignore fixtures generated
```

Sample output for this repo:

```
repo root: /path/to/repo-remap
qualifying modules: 5   skipped dirs: 0

PROCESSING ORDER (deepest first)

-- depth 1 --
  src/agents                                                   files=4    leaf [README+CLAUDE]
  src/references                                               files=3    leaf [README+CLAUDE]
  src/scripts                                                  files=13   leaf [README+CLAUDE]

-- depth 0 --
  src                                                          files=1    parent of 3 [README+CLAUDE]

-- root --
  .                                                            files=6    parent of 1 [README+CLAUDE]
```

Run a gate or the tests from the repo root:

```bash
python3 src/scripts/check_readme_parity.py
python3 src/scripts/check_agent_wiring.py
python3 -m unittest discover -s src/scripts -p "test_*.py" -v
```

## Things to know

- Python 3.8 or newer, standard library only. Nothing to install.
- `module_tree.py` only reads. It never writes files.
- `README.md`, `CLAUDE.md`, dotfiles and generated files (such as `.pyc`, `.lock`, `.min.js`) do not count as source files. Dotted directories are skipped, except `.github`.
- Every gate defaults to the repo root two levels above the script, or takes a root path as its first argument.
- Several tests run the gates against the real repo, so the suite fails if the repo's README, `VERSION`, `CHANGELOG.md`, `TEST_COUNT` or agent files are out of step.
- `src/agents/` and `src/references/` hold their own `README.md` and `CLAUDE.md`. These are repo docs, not skill content. The build scripts treat only `src/agents/rr-*.md` as agents and skip `README.md` and `CLAUDE.md` in `src/references/` when they build, package, validate or sync. `test_build_channels.py` fails if either build script stops filtering.
- `check_test_count.py` runs the full suite itself, so it is slow compared to the other gates. It runs under `make test`, not `make validate`.
- While the suite runs you will see some `FAIL [...]` lines printed. They come from tests that make a gate fail on purpose; the run still ends with `OK`.
