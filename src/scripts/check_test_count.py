#!/usr/bin/env python3
"""Gate: TEST_COUNT must equal the live unittest pass count.

Runs the suite (unittest discovery over src/scripts, test_*.py), parses the
"Ran N tests" summary, requires a final "OK", and compares N to TEST_COUNT.
Wired into `make test`, never `make validate`: validate must stay fast and
suite-free. Nothing else compares TEST_COUNT against reality; README parity
passes when both README and TEST_COUNT are stale together.

Exit 0 on match, 1 otherwise. Importable without side effects.
"""

import re
import subprocess
import sys
from pathlib import Path

RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.M)
OK_RE = re.compile(r"^OK(?: \(.*\))?\s*$", re.M)


def parse_summary(output: str) -> dict:
    """Return {'ran': int|None, 'ok': bool} from unittest's stderr text."""
    m = RAN_RE.search(output or "")
    return {"ran": int(m.group(1)) if m else None, "ok": bool(OK_RE.search(output or ""))}


def run_suite(root: Path) -> str:
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "src/scripts", "-p", "test_*.py"]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    return proc.stdout + proc.stderr


def run(root: Path) -> int:
    try:
        expected = int((root / "TEST_COUNT").read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        print(f"FAIL [test-count-io] cannot read TEST_COUNT as an integer: {exc}")
        return 1
    summary = parse_summary(run_suite(root))
    if summary["ran"] is None:
        print("FAIL [test-count-unavailable] no 'Ran N tests' line in unittest output")
        return 1
    if not summary["ok"]:
        print(f"FAIL [test-count-suite] suite did not end with OK (ran {summary['ran']})")
        return 1
    if summary["ran"] != expected:
        print(f"FAIL [test-count-drift] TEST_COUNT is {expected}, live run passed {summary['ran']}")
        return 1
    print(f"PASS TEST_COUNT {expected} matches live run")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[2]
    return run(root)


if __name__ == "__main__":
    raise SystemExit(main())
