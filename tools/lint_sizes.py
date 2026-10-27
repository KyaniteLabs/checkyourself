#!/usr/bin/env python3
"""Enforce file and function size discipline for CheckYourself production code.

Standard-library only, so it runs locally and in CI without installs. Gates:

* every production Python module stays under MAX_MODULE_LINES (1,000) lines;
* the package facade stays under MAX_FACADE_LINES (600) lines — it is
  re-export-only and must never grow engine logic back;
* no function or method exceeds MAX_FUNCTION_LINES (250) lines — split by verb
  instead of adding to a dump.

Exit code 1 with a listed violation on any breach, 0 when the tree is clean.
"""

from __future__ import annotations

import ast
from pathlib import Path

MAX_MODULE_LINES = 1_000
MAX_FACADE_LINES = 600
MAX_FUNCTION_LINES = 250

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "tools" / "checkyourself"
FACADE = PKG / "__init__.py"

# Production Python surface: the package, its launcher, and the public validator.
TARGETS = sorted(PKG.glob("*.py")) + [ROOT / "tools" / "checkyourself.py", ROOT / "tools" / "validate_public.py"]


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def oversized_functions(path: Path) -> list[tuple[str, int, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    breaches: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = node.end_lineno - node.lineno + 1
            if span > MAX_FUNCTION_LINES:
                breaches.append((node.name, node.lineno, span))
    return breaches


def main() -> int:
    errors: list[str] = []

    for path in TARGETS:
        if not path.exists():
            errors.append(f"missing production file: {path.relative_to(ROOT)}")
            continue
        limit = MAX_FACADE_LINES if path == FACADE else MAX_MODULE_LINES
        count = line_count(path)
        if count > limit:
            errors.append(f"{path.relative_to(ROOT)} is {count} lines (limit {limit}); split by verb instead")
        for name, lineno, span in oversized_functions(path):
            errors.append(
                f"{path.relative_to(ROOT)}:{lineno} function {name!r} is {span} lines "
                f"(limit {MAX_FUNCTION_LINES}); extract helpers instead"
            )

    if errors:
        print("Size discipline failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"OK: size discipline passed ({len(TARGETS)} production files; "
        f"facade<= {MAX_FACADE_LINES}, module <= {MAX_MODULE_LINES}, function <= {MAX_FUNCTION_LINES} lines)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
