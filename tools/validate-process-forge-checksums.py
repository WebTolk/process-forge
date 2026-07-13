#!/usr/bin/env python3
"""Create or print a deterministic public-file checksum inventory."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = ["docs", "schemas", "processes", "packages", "templates", "examples", "tools"]
PUBLIC_ROOT_FILES = ["README.md", "AGENTS.md", "process-forge.yaml", "LICENSE", "CHANGELOG.md"]
OUTPUT = ROOT / "artifacts" / "checksum-inventory.sha256"
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def build_inventory() -> str:
    lines = []
    for path in public_files():
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"{sha256(path)}  {rel}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write artifacts/checksum-inventory.sha256")
    args = parser.parse_args()
    inventory = build_inventory()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(inventory, encoding="utf-8")
        print(f"PASS: wrote {OUTPUT.relative_to(ROOT)}")
    else:
        print(inventory, end="")
        print("PASS: checksum inventory generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
