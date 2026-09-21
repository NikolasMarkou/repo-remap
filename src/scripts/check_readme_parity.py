#!/usr/bin/env python3
"""Gate: README badges must match VERSION and TEST_COUNT.

Both checks match the WHOLE shields.io badge image, never a bare substring.
A substring match passes as long as any line carries the string (a quoted
sample, a changelog excerpt), which proves a string exists, not that a badge
does. Do not loosen either regex back to a substring match.

Exit 0 when both badges match, 1 on any failure. Importable without side effects.
"""

import re
import sys
from pathlib import Path

VERSION_BADGE_RE = re.compile(
    r"!\[[^\]]*\]\(https://img\.shields\.io/badge/Skill-v(\d+\.\d+\.\d+)-[^)]*\)"
)
TEST_BADGE_RE = re.compile(
    r"!\[[^\]]*\]\(https://img\.shields\.io/badge/tests-(\d+)%20passing-[^)]*\)"
)


def check_version_badge(readme_text: str, version: str) -> dict:
    m = VERSION_BADGE_RE.search(readme_text or "")
    found = m is not None
    got = m.group(1) if found else ""
    return {"ok": found and got == version, "found": found, "readme": got, "expected": version}


def check_test_badge(readme_text: str, test_count: str) -> dict:
    m = TEST_BADGE_RE.search(readme_text or "")
    found = m is not None
    got = m.group(1) if found else ""
    return {"ok": found and got == test_count, "found": found, "readme": got, "expected": test_count}


def run(root: Path) -> int:
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        test_count = (root / "TEST_COUNT").read_text(encoding="utf-8").strip()
        readme = (root / "README.md").read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL [readme-parity-io] {exc}")
        return 1

    failures = 0
    v = check_version_badge(readme, version)
    if v["ok"]:
        print(f"PASS version badge v{version}")
    else:
        failures += 1
        if not v["found"]:
            print(f"FAIL [readme-version-badge] no Skill version badge found (expected v{version})")
        else:
            print(f"FAIL [readme-version-badge] README has v{v['readme']}, VERSION is {version}")

    t = check_test_badge(readme, test_count)
    if t["ok"]:
        print(f"PASS test badge {test_count} passing")
    else:
        failures += 1
        if not t["found"]:
            print(f"FAIL [readme-test-badge] no tests badge found (expected {test_count})")
        else:
            print(f"FAIL [readme-test-badge] README says {t['readme']}, TEST_COUNT is {test_count}")

    return 1 if failures else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[2]
    return run(root)


if __name__ == "__main__":
    raise SystemExit(main())
