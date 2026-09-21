# Repo Remap

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Skill](https://img.shields.io/badge/Skill-v1.1.0-green.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-102%20passing-brightgreen.svg)](src/scripts/test_module_tree.py)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](src/scripts/module_tree.py)
[![Sponsored by Electi](https://img.shields.io/badge/Sponsored%20by-Electi-red.svg)](https://www.electiconsulting.com)

**A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill that rebuilds a repository's documentation as a bottom-up tree of self-contained `README.md` and `CLAUDE.md` files.**

Documentation rots quietly. The root README was true two refactors ago. Half the subdirectories have no docs at all, and the ones that do describe a module that has since been split, renamed, or gutted. Nobody notices until someone acts on it: a new hire wires up an interface that no longer exists, or an agent reads a confident, stale paragraph and builds on top of a lie.

The usual fix makes it worse. Someone asks a model to "document the repo", it reads the top-level files, and writes downward. Every child description is a guess extrapolated from a directory name. The docs get longer, the error rate stays the same, and now the wrong information is spread across more files.

Repo Remap inverts the direction. It maps the repo into modules, orders them deepest first, and writes the leaves before anything above them. A parent is written from its children's finished docs plus its own source files, so information is summarized upward from things that were actually read, never guessed downward from things that were not.

> Write the leaves first. Every layer above summarizes text that already exists, not a directory name it hopes to understand.

Each documented directory gets exactly two files, because the two readers want opposite things. `README.md` is for a person who has never seen the code: plain words, short sentences, the shape of the problem. `CLAUDE.md` is for an agent working inside that directory right now: paths, signatures, data shapes, invariants, failure modes, and the rules for changing the code.

Both are self-contained. No file points at another file in the tree. Open any single one of them and you can act.

---

## At a Glance

Say "remap this repo" and here is what actually happens:

- The repo is scanned into a module tree, with trivial and ignored directories filtered out.
- You get the module list back before anything is written if the repo is large, so you can exclude areas.
- Leaf modules are documented first, from their source files, not from their old docs.
- Each level up is written from its children's finished docs, ending at the repo root.
- Existing `README.md` and `CLAUDE.md` files are treated as claims to verify, then overwritten.
- Every module is checked by a separate read-only verifier before anything above it is written.

The main conversation acts as an orchestrator. It never reads source or doc bodies itself: it hands each module to a subagent (a separate Claude worker with its own context) and keeps only the module list and short replies. The skill is one protocol file, four agent definitions, three format rule files and one Python script with no dependencies. See [Get Started](#get-started-in-60-seconds) to install it, and [A Worked Example](#a-worked-example) to watch a full run.

## Table of Contents

**Start here**

- [When to Use This](#when-to-use-this)
- [Get Started in 60 Seconds](#get-started-in-60-seconds)
- [A Worked Example](#a-worked-example)
- [Why This Works](#why-this-works)

**Reference**
[How It Works](#how-it-works) ·
[The Module Tree Script](#the-module-tree-script) ·
[Self-Containment](#self-containment) ·
[Document Contracts](#document-contracts) ·
[Style Constraints](#style-constraints) ·
[FAQ](#faq)

**Project**
[Project Structure](#project-structure) ·
[Contributing](#contributing) ·
[Sponsored by](#sponsored-by) ·
[License](#license)

---

## When to Use This

Reach for it when the map of the codebase is missing or wrong. Skip it when you need one file explained, not the territory.

| Use it | Skip it |
| --- | --- |
| Docs are stale after a large refactor or migration | A single function or file needs a comment |
| A repo has no per-module documentation at all | The repo is one flat directory of three files |
| You are starting work in an unfamiliar codebase | You already know the code and need a quick fix |
| Agents keep acting on outdated README claims | You want API reference generated from docstrings |
| Onboarding a new person or a new agent to the system | You want a changelog, ADR, or design proposal |
| You want `CLAUDE.md` files across the whole tree | You want prose marketing copy about the project |

**Trigger phrases**: *"remap this repo"*, *"the docs are out of date"*, *"document every module"*, *"generate CLAUDE.md files across the codebase"*, *"re-onboard me to this project"*.

---

## Get Started in 60 Seconds

**Requires**: Python 3.8+ for the mapping script. Standard library only, no `pip install`.

### Option 1: Zip package (recommended)

Download `repo-remap-v*.zip` from the [GitHub Releases](https://github.com/NikolasMarkou/repo-remap/releases) page and unpack it into your skills directory:

```bash
unzip repo-remap-v*.zip -d ~/.claude/skills/
```

You get `~/.claude/skills/repo-remap/` with `SKILL.md`, `scripts/module_tree.py`, `agents/rr-*.md`, `references/*.md`, and the docs. For a project-local install, unpack into `.claude/skills/` inside that project instead.

The agents inside the skill folder are enough for the skill to run: `SKILL.md` reads the orchestrator from `<skill-path>/agents/rr-orchestrator.md`, and workers can be started as general-purpose subagents told to follow their `rr-*.md` file. To have Claude Code offer `rr-leaf-writer`, `rr-parent-writer` and `rr-verifier` as named subagent types (so the verifier runs on its own `sonnet` model), also copy the agent files to your user agents directory:

```bash
mkdir -p ~/.claude/agents
cp ~/.claude/skills/repo-remap/agents/rr-*.md ~/.claude/agents/
```

### Option 2: Single-file skill

Download `repo-remap-combined.md` from the same release and paste it into your custom instructions. It holds `SKILL.md` followed by the three reference files and the four agent definitions, inlined. The mapping script is not included, so Claude builds the module list by hand as described in Step 0, and the passes run in the main conversation or in general-purpose subagents told to follow the inlined `rr-*` section for their role.

### Option 3: Clone and install

```bash
git clone https://github.com/NikolasMarkou/repo-remap.git
cd repo-remap
make sync-skill
```

`make sync-skill` installs `SKILL.md`, `scripts/module_tree.py`, `references/` and `agents/rr-*.md` into `~/.claude/skills/repo-remap/`, and also copies `rr-*.md` into `~/.claude/agents/`, which registers the subagent types. It prunes old files before copying, so files deleted from the repo do not linger, and compares every installed copy with its source. In `~/.claude/agents/` it only touches `rr-*.md`, so your other agents are left alone. On Windows use `.\build.ps1 sync-skill`.

To stage a package without installing, `make build` writes `build/repo-remap/` with the version, date and commit stamped into `SKILL.md`.

### Fallbacks

The skill degrades cleanly:

- No mapping script: the orchestrator builds the same module list by hand. It lists directories, count direct files, discard ignored paths, sort by depth descending.
- No `rr-*` subagent types: each worker is spawned as a general-purpose subagent with `Read <skill-path>/agents/rr-<name>.md and follow it.` in front of its prompt.
- No subagents at all: the passes run in the main conversation, reading the three `references/*.md` rule files directly.

### First run

In any project directory, say **"remap this repo"**. Claude takes the orchestrator role, runs the mapping script, confirms the module list with you if the repo is large, then dispatches writers and the verifier from the deepest leaves to the root.

---

## A Worked Example

One full run, condensed. This is the shape every remap takes.

> **You**: "The docs in this service are ancient. Remap this repo."

**Claude (Step 0: map)** runs the helper:

```bash
python3 ~/.claude/skills/repo-remap/scripts/module_tree.py .
```

Output, deepest first:

```
repo root: /home/dev/payments-api
qualifying modules: 8   skipped dirs: 1

PROCESSING ORDER (deepest first)

-- depth 2 --
  src/adapters/ledger          files=4    leaf
  src/adapters/stripe          files=6    leaf [README]

-- depth 1 --
  src/adapters                 files=1    parent of 2
  src/core                     files=7    leaf [README+CLAUDE]
  tests/integration            files=5    leaf

-- depth 0 --
  src                          files=0    parent of 2
  tests                        files=0    parent of 1

-- root --
  .                            files=3    parent of 2 [README]

SKIPPED (documented by nearest qualifying ancestor)
  src/adapters/stripe/fixtures files=2
```

Eight modules is under the confirmation threshold, so the orchestrator proceeds. From here on it only sends short prompts (skill path, repo root, module path, child doc paths, skipped dirs, threshold) and reads short replies.

**Pass 1 (leaves)** dispatches one `rr-leaf-writer` per leaf. The two depth-2 leaves go out together in one message, then the depth-1 leaves. The writer for `src/adapters/stripe` reads every direct source file in full: public API, entry points, side effects, error paths. It reads the existing README too, and treats it as a set of claims. Two of them still hold, one describes a retry policy that was removed last year, so it goes. It writes a new `README.md` and a new `CLAUDE.md`, overwriting the old file completely, and replies in at most five lines.

After each writer, an `rr-verifier` checks that module's two docs against its source and the format rules and replies `PASS` or `FAIL` with one line per defect. On `FAIL` the same writer runs again with those lines as a `FIX:` block, at most twice. A module still failing after that is marked open and reported.

**Pass 2 (one level up)** reaches `src/adapters` once both its children have passed. An `rr-parent-writer` reads the module's own single file, then the finished `README.md` and `CLAUDE.md` of both children, then the skipped `fixtures/` directory, since nothing else will cover it. It does not read the children's source. The parent docs state what each adapter is for and how the pieces connect. They do not restate the Stripe client's retry semantics: that already lives one level down, in full.

The same pass then writes `src`, from `src/adapters` and `src/core`, and `tests`, from `tests/integration`. Neither holds source files of its own; they qualify only through their children.

**Pass 3 (root)** writes the repo root last, from the finished docs of `src` and `tests` plus the three files at the top level. It describes what the system is, how to run it, how the top-level pieces fit, and where the important behavior lives.

**Reporting back** is the paths written grouped by pass, the verifier result per module (`PASS` or `PASS after <n> retries`), and any open items. No narrative, no summary of what was learned, no commentary about the documentation itself.

---

## Why This Works

Four ideas separate this from "ask Claude to write some READMEs."

### 1. Direction of travel

Top-down documentation is extrapolation. The model reads the root, sees `src/adapters/`, and writes a sentence about adapters that sounds right. Bottom-up documentation is summarization. By the time the parent is written, its children's docs exist as text, produced from files that were actually opened. Summarizing existing text is a task models are reliable at. Guessing the contents of an unopened directory is not.

The ordering rule that enforces this is blunt: never document a parent before its children, and if a child is rewritten later, rewrite every ancestor above it.

### 2. Two readers, two documents

A README that satisfies a new engineer is bad context for an agent, and a file dense enough to be good agent context is unreadable for a person. Most projects compromise and produce one document that serves neither.

Repo Remap refuses the compromise. `README.md` explains the problem the module solves in plain language and shows how to run it. `CLAUDE.md` carries the path from repo root, the public interface with signatures, data shapes, invariants and ordering constraints, dependencies, failure modes, and the concrete rules for changing the code. Target around 200 lines, hard ceiling 300. When it will not fit, narrative gets cut and contracts stay.

### 3. Self-containment over cross-references

A documentation tree held together by links reads well in a browser and fails everywhere else. Agents load one file. People open one file. Grep returns one file.

So no file in the tree references another file in the tree. No "see the parent README", no "as described in `../core/CLAUDE.md`". Context a reader needs is repeated, and duplication across files is expected and correct here. Referring to source files by path is encouraged. Referring to other docs is not. Each file states what the module is and where it sits in the repo in its first lines, so it survives being read in isolation.

### 4. Not everything deserves a file

Documenting every directory produces noise that buries the real content. The qualifying rule keeps the tree honest:

| Term | Definition |
| --- | --- |
| **Module** | A directory containing source files, excluding ignored paths |
| **Direct files** | Source files directly inside the directory, not counting `README.md` and `CLAUDE.md` |
| **Leaf module** | A module with no child modules |
| **Qualifying module** | More than 2 direct files, or at least one qualifying descendant |
| **Skipped module** | 2 or fewer direct files and no qualifying descendant |

Skipped directories get no docs. Their contents are covered by the nearest qualifying ancestor, which reads them directly during its own pass. The repo root always qualifies, regardless of file count.

---

## How It Works

Three passes over a tree that was ordered once, at the start, run by an orchestrator and three kinds of worker.

```mermaid
flowchart TD
    U[User: remap this repo] --> S[SKILL.md]
    S --> O[Main conversation assumes the rr-orchestrator role]
    O -->|Step 0| M[scripts/module_tree.py: modules, deepest first]
    M --> L[Pass 1: rr-leaf-writer per leaf, same depth in parallel]
    L --> V1[rr-verifier per module]
    V1 -- FAIL, max 2 retries with FIX --> L
    V1 -- PASS --> P[Pass 2: rr-parent-writer once all children are done]
    P --> V2[rr-verifier per module]
    V2 -- FAIL, max 2 retries with FIX --> P
    V2 -- PASS --> E{At repo root?}
    E -- no --> P
    E -- yes --> F[Pass 3 done: root README.md + CLAUDE.md, report]
```

**No mermaid renderer? The same passes as a table**

| Step | Who | What happens | Inputs read |
| --- | --- | --- | --- |
| **Step 0** | `rr-orchestrator` | Run the mapper, mark qualifying modules, order deepest first. Confirm the list with the user above roughly 25 modules. | Mapper output, or a hand-built list if the script is missing |
| **Pass 1** | `rr-leaf-writer` | Write both files for every qualifying leaf, deepest first. Overwrite old docs completely. | Every direct source file in the module, non-qualifying subdirectories under it, existing docs treated as unverified claims, the three rule files |
| **Check** | `rr-verifier` | After every writer: `PASS`, or `FAIL` with up to 15 defect lines. Read-only. | The module's two new docs, its direct files, the three rule files |
| **Pass 2** | `rr-parent-writer` | Write both files for every module whose children are all verified or open. Summarize children, do not copy them. | Own direct files, children's finished docs, skipped child directories, the three rule files |
| **Pass 3** | `rr-parent-writer` | Repeat Pass 2 one level at a time until the root is written. | Same as Pass 2, ending at the whole system |

The agents live in `src/agents/`:

| Agent | Role | Model | Limits |
| --- | --- | --- | --- |
| `rr-orchestrator` | Step 0, scheduling, dispatch, retries, final report | inherit | Never reads source or doc bodies. May spawn only the three workers |
| `rr-leaf-writer` | Both docs for one leaf, from its source | inherit | Cannot spawn agents. Writes only that module's two docs |
| `rr-parent-writer` | Both docs for one parent or the root, from its children's docs | inherit | Cannot spawn agents. Never edits child docs |
| `rr-verifier` | Checks one module's two docs | sonnet | Cannot spawn agents, write or edit. Runs no builds or tests |

Every worker reads the same three rule files in `src/references/` before it writes or checks anything: `readme-format.md`, `claude-format.md` and `style.md`. A child rewritten after its parent was written sends every ancestor back to be rewritten.

**Ignored by default**: `.git`, `.hg`, `.svn`, `.idea`, `.vscode`, `__pycache__`, `node_modules`, `bower_components`, `vendor`, `venv`, `.venv`, `env`, `virtualenv`, `dist`, `build`, `out`, `target`, `.next`, `.nuxt`, `.svelte-kit`, `coverage`, `.terraform`, `.gradle`, `.tox`, `.cache`, `site-packages`, and caches such as `.pytest_cache`, `.mypy_cache`, `.ruff_cache`. Dotted directories are skipped except `.github`. Compiled and generated files (`.pyc`, `.pyo`, `.class`, `.o`, `.so`, `.dll`, `.dylib`, `.log`, `.lock`, `.map`, `.min.js`, `.min.css`, `.snap`) do not count toward the file total.

---

## The Module Tree Script

`src/scripts/module_tree.py` is a read-only mapper. It never writes documentation, it decides where documentation belongs.

```bash
python3 module_tree.py <repo-root> [--min-files N] [--ignore DIR ...]
```

| Flag | Effect |
| --- | --- |
| `--min-files N` | Modules with this many direct files or fewer are skipped. Default 2. Raise it on a sprawling repo to get a coarser tree. |
| `--ignore DIR ...` | Extra directory names added to the ignore set, matched by name at any depth. |

Output has three parts: a header with the qualifying and skipped counts, the processing order grouped by depth with the deepest first, and the list of skipped directories with their file counts. Each qualifying line shows the relative path, the direct file count, whether it is a leaf or a parent of N documented children, and a `[README]`, `[CLAUDE]`, or `[README+CLAUDE]` marker when docs already exist there.

A directory that qualifies only through a descendant but holds nothing anywhere below it is dropped, so empty scaffolding never enters the list. Exit code is 1 if the root argument is not a directory, 0 otherwise.

---

## Self-Containment

The rule is one sentence: a reader must be able to act on one file alone, without opening another file in the tree.

What follows from it:

- No cross-document links or pointers of any kind, in either direction.
- Repeat the context a reader needs, even when it appears in a sibling or a parent.
- Refer to source files by path freely. Never refer to other docs.
- Define local terms, acronyms, and domain words in the file that uses them.
- Open with what the module is and where it sits in the repo.

Duplication is the price, and it is the right price. The alternative is a tree where every file is a pointer to another pointer.

---

## Document Contracts

Both templates adapt to the module. Sections that would be empty are dropped, and a small module gets a short file.

### README.md

For a person who has never seen this code. Simple words, short sentences, concrete examples. Assume competence, not context.

| Section | Contents |
| --- | --- |
| Title and summary | What this is and what it does, in one or two sentences |
| What it is for | The problem it solves, in plain language, 3 to 6 sentences |
| How it works | A walkthrough of the main flow, with a mermaid diagram if that is clearer |
| Files | One line per file, saying what it does |
| How to use it | A minimal runnable example or the command to run, with real values |
| Things to know | Gotchas, limits, assumptions, required environment |

### CLAUDE.md

For an agent working in this module. Operational and specific, with no motivation and no sales copy.

| Section | Contents |
| --- | --- |
| Header | Module name, `Path:` from repo root, one-line purpose |
| Scope | What lives here, and what explicitly does not |
| Architecture | Structure, data flow, control flow, mermaid for state machines and pipelines |
| Key files | Table of file, role, notes |
| Public interface | Exported functions, classes, endpoints, CLI commands, events, with signatures, inputs, outputs, errors |
| Data shapes | Structs, schemas, payloads, DB tables, config keys |
| Invariants and constraints | Ordering requirements, thread and async rules, idempotency, resource lifecycles |
| Dependencies | Internal modules relied on and what is used from them, external packages and why |
| Failure modes | Known errors, how they surface, how they are handled |
| Working here | Conventions, where to add new cases, what to update in tandem, how to test |

---

## Style Constraints

These apply to every generated file, and are overridden only when you explicitly ask:

- Plain, direct language.
- No emojis.
- No em dashes.
- No preamble, no closing summary, no meta-commentary about the documentation itself.
- Mermaid is encouraged for diagrams, flows, state machines, and protocols.
- Never invent behavior. If something is unclear from the code, say so or leave it out.

**The completion checklist**

- [ ] Every qualifying module has both files, and no skipped module has them
- [ ] Every module has a `PASS` from `rr-verifier`, or is listed as open
- [ ] No parent was written before its children, and no ancestor of a rewritten module was left stale
- [ ] No file references another doc file
- [ ] Every `CLAUDE.md` is under 300 lines
- [ ] Parents summarize children rather than duplicating their internals
- [ ] Skipped directories are covered by their nearest documented ancestor
- [ ] No emojis, no em dashes, no preambles anywhere

---

## FAQ

**Does it overwrite my existing docs?** Yes, completely, in every qualifying module. Old files are read first and treated as claims to check against the code, so accurate content survives on its merits, but their structure is not preserved. Commit before running.

**What if I only want part of the repo done?** Run the script yourself, decide which modules you want, and say so. For a repo above roughly 25 qualifying modules the skill confirms the module list with you before writing anyway.

**Why two files instead of one?** Because the audiences want opposite things. A person needs the problem explained. An agent needs signatures, invariants, and the rules for changing the code. One file serving both serves neither well.

**Why no links between docs?** Because a file that points elsewhere is useless to whoever loaded only that file. Self-containment costs duplication and buys the ability to act on any single file.

**Will my `CLAUDE.md` files get huge?** No. Target is around 200 lines with a hard ceiling of 300. Over the ceiling, narrative is cut and contracts, invariants, and paths are kept.

**What counts as a module?** Any directory with source files, after ignored paths are removed, that has more than 2 direct files or has a qualifying descendant. The root always counts.

**Can I change the threshold?** Yes, with `--min-files N`. A higher number gives a coarser tree with fewer, broader documents.

**Do I need the Python script?** No, but it helps. Without it the protocol builds the same ordering by hand.

**Do I need subagents?** No. Without the `rr-*` subagent types, workers run as general-purpose subagents following their agent file. Without subagents at all, the passes run in the main conversation. Subagents keep the main context small: it holds only the module list and five-line replies, never source or doc bodies.

**What if the code contradicts itself or is unclear?** The skill says so in the document, or leaves it out. Guessed intent presented as fact is the failure mode this whole approach exists to avoid.

---

## Project Structure

```
repo-remap/
├── LICENSE                             # Apache License 2.0
├── VERSION                             # single source of truth for the version
├── TEST_COUNT                          # live test count, checked by make test
├── CHANGELOG.md                        # version history, top entry must match VERSION
├── Makefile                            # Unix/Linux/macOS build (reads VERSION)
├── build.ps1                           # Windows PowerShell 7+ build (reads VERSION)
└── src/
    ├── SKILL.md                        # the protocol: role assumption, definitions, passes, dispatch rules, checklist
    ├── agents/
    │   ├── rr-orchestrator.md          # Step 0, scheduling, dispatch, retries, final report
    │   ├── rr-leaf-writer.md           # Pass 1: docs for one leaf from its source
    │   ├── rr-parent-writer.md         # Pass 2 and 3: docs for one parent from its children's docs
    │   └── rr-verifier.md              # read-only check of one module (sonnet)
    ├── references/
    │   ├── readme-format.md            # README.md template
    │   ├── claude-format.md            # CLAUDE.md template, 200-line target, 300 ceiling
    │   └── style.md                    # self-containment and style rules
    └── scripts/
        ├── module_tree.py              # module mapper, prints processing order deepest first
        ├── check_readme_parity.py      # gate: badges vs VERSION and TEST_COUNT (make validate)
        ├── check_changelog_parity.py   # gate: top CHANGELOG entry vs VERSION (make validate)
        ├── check_ignore_parity.py      # gate: ignore paragraph vs module_tree.py (make validate)
        ├── check_agent_wiring.py       # gate: agent frontmatter, spawn rules, citations (make validate)
        ├── check_test_count.py         # gate: TEST_COUNT vs live suite (make test only)
        ├── test_module_tree.py         # unittest suite for the mapper
        ├── test_check_*.py             # one suite per gate
        └── test_build_channels.py      # keeps Makefile and build.ps1 in lockstep
```

The package built by `make build` contains only `SKILL.md`, `scripts/module_tree.py`, `agents/rr-*.md`, the three `references/*.md` rule files, `README.md`, `LICENSE`, `CHANGELOG.md` and `VERSION`. Gate and test scripts stay in the repo, and so do the `README.md` and `CLAUDE.md` files inside `src/` and its folders: they document this repo and never ship. The complete protocol is `src/SKILL.md`.

---

## Contributing

The skill is a protocol file, four agent definitions, three rule files and one script with no dependencies. The repo around them keeps these in agreement mechanically with five gates and seven test suites.

**Requires**: Python 3.8+ and GNU make, or PowerShell 7+ on Windows. No pip install.

<details>
<summary><strong>Run the tests</strong></summary>

```bash
make test
```

This compiles every script, runs unittest discovery over `src/scripts/test_*.py`, then checks that `TEST_COUNT` equals the live pass count. The same suite by hand:

```bash
python3 -m unittest discover -s src/scripts -p "test_*.py" -v
```

102 tests across 7 suites: build_channels 27, check_agent_wiring 13, check_changelog_parity 10, check_ignore_parity 11, check_readme_parity 12, check_test_count 11, module_tree 18. The per-suite numbers are hand-maintained prose. If they drift, `TEST_COUNT` and the badge remain the machine-checked source of truth.

</details>

<details>
<summary><strong>Build and package</strong></summary>

| Unix/Linux/macOS | Windows (PowerShell 7+) | What it does |
| --- | --- | --- |
| `make build` | `.\build.ps1 build` | Stage `build/repo-remap/` (with `scripts/`, `agents/`, `references/`) and stamp version, date and commit into `SKILL.md` |
| `make build-combined` | `.\build.ps1 build-combined` | Single file: `SKILL.md` plus the inlined references and agents, for pasting into context |
| `make package` | `.\build.ps1 package` | Validate, build, zip into `dist/` (default target) |
| `make package-combined` | `.\build.ps1 package-combined` | Validate, then copy the single file into `dist/` |
| `make package-tar` | `.\build.ps1 package-tar` | Validate, build, tarball into `dist/` |
| `make validate` | `.\build.ps1 validate` | Frontmatter, cited scripts, references and agents, agent frontmatter, README, CHANGELOG, ignore-list and agent-wiring gates |
| `make lint` | `.\build.ps1 lint` | `py_compile` every script |
| `make test` | `.\build.ps1 test` | Lint, tests, `TEST_COUNT` gate |
| `make clean` | `.\build.ps1 clean` | Remove `build/` and `dist/` |
| `make list` | `.\build.ps1 list` | Show package contents |
| `make sync-skill` | `.\build.ps1 sync-skill` | Deploy to `~/.claude/skills/repo-remap` and `rr-*.md` to `~/.claude/agents`, pruning first |

The Windows channel requires PowerShell 7 or later and is kept in lockstep with the Makefile by `src/scripts/test_build_channels.py`.

Things to know about the build:

- `build`, `build-combined`, `package*` and `list` call `git rev-parse --short HEAD`, so they need a git checkout.
- The Makefile edits files with `sed -i "..."`, the GNU form. BSD `sed` on stock macOS expects a suffix argument after `-i`.
- `make test` runs the suite twice: once directly, then again inside `check_test_count.py`.
- `sync-skill` compares `SKILL.md`, `module_tree.py`, `VERSION`, every shipped reference file and every agent file (in both install locations) with the source after copying, and fails on any unexpected file in the installed `references/` or `agents/`. `README.md`, `LICENSE` and `CHANGELOG.md` are copied but not compared.
- Only `src/agents/rr-*.md` counts as an agent, and `src/references/README.md` and `CLAUDE.md` are excluded from the references. Every build step applies both filters.

</details>

<details>
<summary><strong>Validation checklist before submitting changes</strong></summary>

- [ ] `make validate` and `make test` pass
- [ ] Definitions in `src/SKILL.md` match the qualifying logic in `module_tree.py`
- [ ] The "Ignored by default" paragraph in this README matches `IGNORED_DIRS` and `IGNORED_SUFFIXES` (gated by `check_ignore_parity.py`)
- [ ] `src/SKILL.md` keeps `name:`, `description:` and the `__SKILL_VERSION__`, `__SKILL_DATE__`, `__SKILL_COMMIT__` placeholders in its frontmatter
- [ ] The version badge above matches `VERSION` and the tests badge matches `TEST_COUNT` (gated by `check_readme_parity.py`)
- [ ] The top `CHANGELOG.md` entry matches `VERSION` (gated by `check_changelog_parity.py`)
- [ ] Every agent file has its frontmatter, workers cannot spawn agents, the orchestrator lists every worker, the verifier uses `sonnet`, and every cited agent or reference exists (gated by `check_agent_wiring.py`)
- [ ] `Makefile` and `build.ps1` were changed together if either was touched
- [ ] The workflow diagram matches the pass descriptions
- [ ] Generated output still obeys the style constraints

</details>

---

## Sponsored by

This project is sponsored by **[Electi Consulting](https://www.electiconsulting.com)**, a technology consultancy specializing in AI, blockchain, cryptography, and data science. Founded in 2017, headquartered in Limassol, Cyprus, with a London presence. Clients include the European Central Bank, US Navy, and Cyprus Securities and Exchange Commission.

---

## License

[Apache License 2.0](LICENSE)