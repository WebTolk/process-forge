#!/usr/bin/env python3
"""Check public product files for private references and local data."""

from __future__ import annotations

import re
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = ["docs", "schemas", "processes", "packages", "templates", "examples", "tools"]
PUBLIC_ROOT_FILES = ["README.md", "AGENTS.md", "process-forge.yaml", "LICENSE", "CHANGELOG.md", ".processforge-releaseignore"]
PF_PUBLIC_ROOT_FILES = [".pf/AGENTS.md", ".pf/process-forge.yaml"]
PF_PUBLIC_DIRS = ["processes", "packages", "templates", "assignments", "artifacts", "logs", "handoffs", "reviews", "adr", "schemas", "contexts"]
PF_PRIVATE_PARTS = {"runtime", "private-notes", "cache"}
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


def public_files(root_path: Path) -> list[Path]:
    files: list[Path] = []
    for name in PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append(path)
    for name in PF_PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append(path)
    for dirname in PUBLIC_DIRS:
        root = root_path / dirname
        if root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
                and path.suffix not in SKIP_SUFFIXES
            )
    pf_root = root_path / ".pf"
    if pf_root.is_dir():
        for dirname in PF_PUBLIC_DIRS:
            root = pf_root / dirname
            if root.is_dir():
                files.extend(
                    path
                    for path in root.rglob("*")
                    if path.is_file()
                    and not any(part in SKIP_DIRS or part in PF_PRIVATE_PARTS for part in path.relative_to(pf_root).parts)
                    and path.suffix not in SKIP_SUFFIXES
                    and path.name != "process-forge.local.yaml"
                )
    return sorted(files, key=lambda path: path.relative_to(root_path).as_posix())


def validate_releaseignore(root_path: Path) -> list[str]:
    failures: list[str] = []
    path = root_path / ".processforge-releaseignore"
    if not path.is_file():
        failures.append(".processforge-releaseignore missing")
        return failures
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.strip().startswith("#")]
    required = [
        ".idea/",
        ".serena/",
        "private-notes/",
        "runtime/cache/",
        ".pf/process-forge.local.yaml",
        ".pf/runtime/",
        ".pf/private-notes/",
        ".pf/cache/",
        "tools/__pycache__/",
        "*.pyc",
        "artifacts/*",
        "!artifacts/README.md",
        "assignments/*",
        "!assignments/README.md",
        "logs/*",
        "!logs/README.md",
        "reviews/*",
        "!reviews/README.md",
        "handoffs/*",
        "!handoffs/README.md",
        "contexts/*",
        "!contexts/README.md",
    ]
    for item in required:
        if item not in lines:
            failures.append(f".processforge-releaseignore missing {item}")
    broad_forbidden = {"artifacts/", "assignments/", "logs/", "reviews/", "handoffs/", "contexts/"}
    for item in broad_forbidden:
        if item in lines:
            failures.append(f".processforge-releaseignore excludes whole skeleton directory {item}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root_path = Path(args.root).expanduser().resolve()
    failures: list[str] = []
    for path in public_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for marker in FORBIDDEN_LITERAL_PATTERNS:
            if marker in lower:
                failures.append(f"{rel}: forbidden marker {marker!r}")
        for pattern in FORBIDDEN_REGEX_PATTERNS:
            if pattern.search(text):
                failures.append(f"{rel}: forbidden private/local path pattern {pattern.pattern!r}")
    failures.extend(validate_releaseignore(root_path))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: public cleanliness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
