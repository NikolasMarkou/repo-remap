#!/usr/bin/env python3
"""Map a repo into modules and print them in bottom-up processing order.

Usage:
    python3 module_tree.py <repo-root> [--min-files N] [--ignore DIR ...]

A module is a directory holding source files. A module qualifies for docs when
it has more than N direct files (default 2) or has a qualifying descendant.
The repo root always qualifies. Output is grouped by depth, deepest first,
which is the order the passes should follow.
"""

import argparse
import os
import sys

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "__pycache__", "node_modules", "bower_components", "vendor",
    "venv", ".venv", "env", ".env", "virtualenv", "dist", "build", "out",
    "target", ".next", ".nuxt", ".svelte-kit", "coverage", ".coverage",
    ".terraform", ".gradle", ".tox", ".cache", "site-packages", ".DS_Store",
}

IGNORED_FILES = {"README.md", "CLAUDE.md", ".DS_Store", ".gitkeep"}

IGNORED_SUFFIXES = (
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".dylib", ".log",
    ".lock", ".map", ".min.js", ".min.css", ".snap",
)


def is_ignored_dir(name: str) -> bool:
    return name in IGNORED_DIRS or (name.startswith(".") and name not in {".github"})


def is_counted_file(name: str) -> bool:
    if name in IGNORED_FILES:
        return False
    if name.startswith("."):
        return False
    return not name.endswith(IGNORED_SUFFIXES)


def scan(root: str):
    """Return {dir_path: (direct_file_count, [child_dir_paths])}."""
    tree = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not is_ignored_dir(d))
        count = sum(1 for f in filenames if is_counted_file(f))
        tree[dirpath] = (count, [os.path.join(dirpath, d) for d in dirnames])
    return tree


def qualifying(tree: dict, root: str, min_files: int) -> set:
    """A dir qualifies if it has > min_files direct files, or a qualifying descendant."""
    quals = set()
    for path in sorted(tree, key=lambda p: p.count(os.sep), reverse=True):
        count, children = tree[path]
        if count > min_files or any(c in quals for c in children):
            quals.add(path)
    quals.add(root)
    # Drop dirs that hold nothing anywhere below them.
    return {p for p in quals if any(tree[q][0] > 0 for q in tree if q == p or q.startswith(p + os.sep))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--min-files", type=int, default=2,
                    help="modules with this many direct files or fewer are skipped (default 2)")
    ap.add_argument("--ignore", nargs="*", default=[], help="extra directory names to ignore")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    IGNORED_DIRS.update(args.ignore)

    tree = scan(root)
    quals = qualifying(tree, root, args.min_files)

    def rel(p: str) -> str:
        return os.path.relpath(p, root).replace(os.sep, "/") if p != root else "."

    by_depth = {}
    for p in quals:
        by_depth.setdefault(rel(p).count("/") if p != root else -1, []).append(p)

    print(f"repo root: {root}")
    print(f"qualifying modules: {len(quals)}   skipped dirs: {len(tree) - len(quals)}")
    print()
    print("PROCESSING ORDER (deepest first)")
    for depth in sorted(by_depth, reverse=True):
        label = "root" if depth < 0 else f"depth {depth}"
        print(f"\n-- {label} --")
        for p in sorted(by_depth[depth]):
            count, children = tree[p]
            doc_children = [c for c in children if c in quals]
            kind = "leaf" if not doc_children else f"parent of {len(doc_children)}"
            has = []
            if os.path.exists(os.path.join(p, "README.md")):
                has.append("README")
            if os.path.exists(os.path.join(p, "CLAUDE.md")):
                has.append("CLAUDE")
            existing = f" [{'+'.join(has)}]" if has else ""
            print(f"  {rel(p):<60} files={count:<4} {kind}{existing}")

    skipped = [p for p in tree if p not in quals]
    if skipped:
        print("\nSKIPPED (documented by nearest qualifying ancestor)")
        for p in sorted(skipped):
            print(f"  {rel(p):<60} files={tree[p][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
