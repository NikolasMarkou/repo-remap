#!/usr/bin/env python3
"""Gate: CHANGELOG.md's first "## [X.Y.Z]" entry must equal VERSION.

A missing or unparseable CHANGELOG is a FAIL, not a skip. Exit 0 on match,
1 otherwise. Importable without side effects.
"""

import re
import sys
from pathlib import Path

ENTRY_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$", re.M)


def top_entry(changelog_text: str):
    """Return (version, date) of the first release heading, or None."""
    m = ENTRY_RE.search(changelog_text or "")
    return (m.group(1), m.group(2)) if m else None


def check(changelog_text: str, version: str) -> dict:
    entry = top_entry(changelog_text)
    return {"ok": entry is not None and entry[0] == version, "entry": entry, "expected": version}


def run(root: Path) -> int:
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL [changelog-parity-io] {exc}")
        return 1
    r = check(text, version)
    if r["ok"]:
        print(f"PASS changelog top entry [{version}] - {r['entry'][1]}")
        return 0
    if r["entry"] is None:
        print("FAIL [changelog-parity] no '## [X.Y.Z] - YYYY-MM-DD' heading found")
    else:
        print(f"FAIL [changelog-parity] top entry is [{r['entry'][0]}], VERSION is {version}")
    return 1


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[2]
    return run(root)


if __name__ == "__main__":
    raise SystemExit(main())
