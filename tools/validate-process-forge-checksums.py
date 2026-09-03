#!/usr/bin/env python3
"""Create or verify a deterministic public-file checksum inventory."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = ["docs", "schemas", "processes", "packages", "packs", "templates", "prompts", "examples", "policies", "seeds", "bin", "src", "tools", "updates", "checksums"]
PUBLIC_ROOT_FILES = [
    "README.md",
    "README.ru.md",
    "QUICKSTART.md",
    "QUICKSTART.ru.md",
    "LICENSE",
    "NOTICE",
    "CHANGELOG.md",
    "VERSION",
    "requirements.txt",
    ".gitignore",
    ".processforge-releaseignore",
]
PF_PUBLIC_ROOT_FILES = [".pf/AGENTS.md", ".pf/process-forge.yaml", ".pf/hooks.yaml"]
PUBLIC_INVENTORY = Path("checksums/processforge.sha256")
LEGACY_INVENTORY = Path(".pf/artifacts/checksum-inventory.sha256")
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def released_content(path: Path) -> bytes:
    """Return the deterministic text representation used by release-pack."""
    content = path.read_bytes()
    return content if b"\0" in content else content.replace(b"\r\n", b"\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(released_content(path)).hexdigest()


def public_file_entries(root_path: Path) -> list[tuple[str, Path]]:
    """Return the shipped archive path and source path for checksum coverage."""
    files: list[tuple[str, Path]] = []
    for name in PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append((name, path))

    # release-pack exposes AGENTS.md at the archive root. Source checkouts may
    # use .pf/AGENTS.md as its canonical source, while extracted archives have
    # both paths. Preserve the archive-visible name in either layout.
    root_agents = root_path / "AGENTS.md"
    pf_agents = root_path / ".pf" / "AGENTS.md"
    if root_agents.is_file():
        files.append(("AGENTS.md", root_agents))
    elif pf_agents.is_file():
        files.append(("AGENTS.md", pf_agents))

    for name in PF_PUBLIC_ROOT_FILES:
        path = root_path / name
        if path.is_file():
            files.append((name, path))
    for dirname in PUBLIC_DIRS:
        root = root_path / dirname
        if root.is_dir():
            files.extend(
                (path.relative_to(root_path).as_posix(), path)
                for path in root.rglob("*")
                if path.is_file()
                and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
                and path.suffix not in SKIP_SUFFIXES
                and path.relative_to(root_path).as_posix() != PUBLIC_INVENTORY.as_posix()
            )
    return sorted(files, key=lambda item: item[0])


def public_files(root_path: Path) -> list[Path]:
    """Compatibility view of source files included in the public inventory."""
    files: list[Path] = []
    seen: set[Path] = set()
    for _archive_path, path in public_file_entries(root_path):
        if path not in seen:
            files.append(path)
            seen.add(path)
    return files


def build_inventory(root_path: Path) -> str:
    lines = []
    for archive_path, source_path in public_file_entries(root_path):
        lines.append(f"{sha256(source_path)}  {archive_path}")
    return "\n".join(lines) + "\n"


def resolve_inventory_path(root_path: Path, requested: str | None = None) -> Path:
    if requested:
        path = Path(requested).expanduser()
        return path if path.is_absolute() else root_path / path
    public_path = root_path / PUBLIC_INVENTORY
    if public_path.is_file():
        return public_path
    return root_path / LEGACY_INVENTORY


def check_inventory(root_path: Path, output: Path) -> int:
    if not output.is_file():
        print(f"FAIL: checksum inventory missing: {output.relative_to(root_path)}; run with --write")
        return 1
    expected = output.read_text(encoding="utf-8")
    actual = build_inventory(root_path)
    if expected == actual:
        print("PASS: checksum inventory matches.")
        return 0
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    expected_set = set(expected_lines)
    actual_set = set(actual_lines)
    missing = sorted(expected_set - actual_set)
    added = sorted(actual_set - expected_set)
    print("FAIL: checksum inventory is stale.")
    for line in missing[:20]:
        print(f"- expected only: {line}")
    for line in added[:20]:
        print(f"- actual only: {line}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ProcessForge root path.")
    parser.add_argument("--output", help="checksum inventory path relative to --root; defaults to checksums/processforge.sha256")
    parser.add_argument("--write", action="store_true", help="write checksums/processforge.sha256")
    parser.add_argument("--check", action="store_true", help="compare current public files with existing checksum inventory")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    output = resolve_inventory_path(root, args.output)
    if args.write and not args.output:
        output = root / PUBLIC_INVENTORY
    if args.write and args.check:
        parser.error("choose either --write or --check")
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_inventory(root), encoding="utf-8")
        print(f"PASS: wrote {output.relative_to(root)}")
        return 0
    return check_inventory(root, output)


if __name__ == "__main__":
    sys.exit(main())
