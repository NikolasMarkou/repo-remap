#!/usr/bin/env python3
"""Gate: README's "Ignored by default" paragraph must agree with module_tree.py.

Rules:
- Every non-dotted name in IGNORED_DIRS must appear backticked in the paragraph.
- Every suffix in IGNORED_SUFFIXES must appear backticked in the paragraph.
- Every backticked name in the paragraph must be in IGNORED_DIRS or IGNORED_SUFFIXES.
- Dotted directories are covered by the paragraph's "dotted directories are
  skipped" sentence, which must be present; dotted names may still be listed.

Anti-vacuity: a paragraph with fewer than MIN_NAMES backticked names fails,
so a renamed or deleted paragraph cannot pass as "nothing to compare".

Exit 0 on parity, 1 otherwise. Importable without side effects.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_tree import IGNORED_DIRS, IGNORED_SUFFIXES  # noqa: E402

PARAGRAPH_MARKER = "**Ignored by default**"
DOTTED_SENTENCE = "Dotted directories are skipped except `.github`"
MIN_NAMES = 10
BACKTICK_RE = re.compile(r"`([^`]+)`")


def extract_paragraph(readme_text: str) -> str:
    for para in (readme_text or "").split("\n\n"):
        if para.lstrip().startswith(PARAGRAPH_MARKER):
            return para
    return ""


def compare(readme_text: str, dirs=IGNORED_DIRS, suffixes=IGNORED_SUFFIXES) -> dict:
    para = extract_paragraph(readme_text)
    names = set(BACKTICK_RE.findall(para))
    known = set(dirs) | set(suffixes) | {".github"}  # named by DOTTED_SENTENCE itself
    return {
        "paragraph_found": bool(para),
        "dotted_sentence": DOTTED_SENTENCE in para,
        "too_few": len(names) < MIN_NAMES,
        "missing_dirs": sorted(d for d in dirs if not d.startswith(".") and d not in names),
        "missing_suffixes": sorted(s for s in suffixes if s not in names),
        "unknown": sorted(n for n in names if n not in known),
    }


def run(root: Path) -> int:
    try:
        readme = (root / "README.md").read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL [ignore-parity-io] {exc}")
        return 1
    r = compare(readme)
    failures = 0
    if not r["paragraph_found"]:
        print(f"FAIL [ignore-parity-floor] README has no paragraph starting with {PARAGRAPH_MARKER}")
        return 1
    if r["too_few"]:
        print(f"FAIL [ignore-parity-floor] fewer than {MIN_NAMES} backticked names in the paragraph")
        failures += 1
    if not r["dotted_sentence"]:
        print(f"FAIL [ignore-parity-dotted] sentence missing: {DOTTED_SENTENCE}")
        failures += 1
    for d in r["missing_dirs"]:
        print(f"FAIL [ignore-parity-missing] IGNORED_DIRS entry not in README: {d}")
        failures += 1
    for s in r["missing_suffixes"]:
        print(f"FAIL [ignore-parity-missing] IGNORED_SUFFIXES entry not in README: {s}")
        failures += 1
    for n in r["unknown"]:
        print(f"FAIL [ignore-parity-unknown] README names {n}, not in module_tree.py")
        failures += 1
    if not failures:
        print(f"PASS ignore lists agree ({len(IGNORED_DIRS)} dirs, {len(IGNORED_SUFFIXES)} suffixes)")
    return 1 if failures else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[2]
    return run(root)


if __name__ == "__main__":
    raise SystemExit(main())
