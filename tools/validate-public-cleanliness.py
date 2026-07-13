#!/usr/bin/env python3
"""Check public product files for private references and local data."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = ["docs", "schemas", "processes", "packages", "templates", "examples", "tools"]
PUBLIC_ROOT_FILES = ["README.md", "AGENTS.md", "process-forge.yaml", "LICENSE", "CHANGELOG.md"]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}

INTERNAL_FLOW_MARKER = "." + "web" + "tolk"
FORBIDDEN_LITERAL_PATTERNS = [
    INTERNAL_FLOW_MARKER,
    "wt ai " + "control center",
    "wt" + "aicc",
    "sec" + "ret=",
    "pass" + "word=",
    "api" + "_key",
    "scr" + "atch",
]

FORBIDDEN_REGEX_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/home/[A-Za-z0-9_.-]+/"),
    re.compile(r"users\\[A-Za-z0-9_.-]+", re.IGNORECASE),
]


def public_files() -> list[Path]:
    files: list[Path] = []
    for name in PUBLIC_ROOT_FILES:
        path = ROOT / name
        if path.is_file():
            files.append(path)
    for dirname in PUBLIC_DIRS:
        root = ROOT / dirname
        if root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
                and path.suffix not in SKIP_SUFFIXES
            )
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def main() -> int:
    failures: list[str] = []
    for path in public_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for marker in FORBIDDEN_LITERAL_PATTERNS:
            if marker in lower:
                failures.append(f"{rel}: forbidden marker {marker!r}")
        for pattern in FORBIDDEN_REGEX_PATTERNS:
            if pattern.search(text):
                failures.append(f"{rel}: forbidden private/local path pattern {pattern.pattern!r}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: public cleanliness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
