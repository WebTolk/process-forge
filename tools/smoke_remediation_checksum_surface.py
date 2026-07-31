#!/usr/bin/env python3
"""Regression coverage for the shipped checksum surface."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import sys
import tempfile
from pathlib import Path
from types import ModuleType


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT_PATHS = {
    ".gitignore",
    ".processforge-releaseignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE",
    "QUICKSTART.md",
    "QUICKSTART.ru.md",
    "README.md",
    "README.ru.md",
    "VERSION",
    "requirements.txt",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def load_validator(root: Path) -> ModuleType:
    path = root / "tools" / "validate-process-forge-checksums.py"
    spec = importlib.util.spec_from_file_location("processforge_checksum_validator", path)
    if spec is None or spec.loader is None:
        fail(f"cannot load checksum validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_release_module(root: Path) -> ModuleType:
    tools_path = str(root / "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    path = root / "tools" / "processforge.py"
    spec = importlib.util.spec_from_file_location("processforge_checksum_release_contract", path)
    if spec is None or spec.loader is None:
        fail(f"cannot load release contract module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def inventory_paths(inventory: str) -> list[str]:
    return [line.split("  ", 1)[1] for line in inventory.splitlines()]


def build_fixture(root: Path, *, root_agents: bool) -> None:
    for relative_path in sorted(EXPECTED_ROOT_PATHS - {"AGENTS.md"}):
        write(root / relative_path, f"fixture for {relative_path}\n")
    write(root / ".pf" / "AGENTS.md", "canonical agent contract\n")
    if root_agents:
        write(root / "AGENTS.md", "archive root agent contract\n")
    write(root / ".pf" / "process-forge.yaml", "schema_version: 1\n")
    write(root / ".pf" / "hooks.yaml", "schema_version: 1\n")
    write(root / "docs" / "guide.md", "guide\n")
    write(root / "packs" / "official" / "fixture.yaml", "id: fixture\n")
    write(root / "checksums" / "processforge.sha256", "self-referential\n")
    write(root / "tools" / "__pycache__" / "ignored.pyc", "ignored\n")


def validate_layout(validator: ModuleType, fixture: Path, *, root_agents: bool) -> None:
    build_fixture(fixture, root_agents=root_agents)
    inventory = validator.build_inventory(fixture)
    paths = inventory_paths(inventory)

    missing = sorted(EXPECTED_ROOT_PATHS - set(paths))
    if missing:
        fail(f"shipped root files missing from checksum inventory: {missing}")
    if "checksums/processforge.sha256" in paths:
        fail("checksum inventory must exclude itself")
    if "tools/__pycache__/ignored.pyc" in paths:
        fail("generated cache file unexpectedly entered checksum inventory")
    if "packs/official/fixture.yaml" not in paths:
        fail("official pack file missing from checksum inventory")
    if paths != sorted(paths):
        fail("checksum inventory paths are not deterministic")
    if len(paths) != len(set(paths)):
        fail("checksum inventory contains duplicate archive paths")

    agents_line = next(line for line in inventory.splitlines() if line.endswith("  AGENTS.md"))
    expected_agents = fixture / ("AGENTS.md" if root_agents else ".pf/AGENTS.md")
    if not agents_line.startswith(validator.sha256(expected_agents)):
        fail("AGENTS.md checksum does not follow release-pack source precedence")


def validate_stale_detection(validator: ModuleType, fixture: Path) -> None:
    build_fixture(fixture, root_agents=False)
    inventory_path = fixture / "checksums" / "processforge.sha256"
    inventory_path.write_text(validator.build_inventory(fixture), encoding="utf-8")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        fresh_status = validator.check_inventory(fixture, inventory_path)
    if fresh_status != 0:
        fail("fresh checksum inventory was rejected")
    write(fixture / "README.ru.md", "tampered\n")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        stale_status = validator.check_inventory(fixture, inventory_path)
    if stale_status == 0:
        fail("changed shipped root file did not invalidate checksum inventory")


def validate_current_release_parity(root: Path, validator: ModuleType) -> None:
    release = load_release_module(root)
    patterns = release.release_ignore_patterns(root)
    shipped_paths = {
        archive_path
        for archive_path, _source_path in release.release_source_files(root)
        if not release.release_ignore_match(archive_path, patterns)
        and not release.release_path_is_forbidden(archive_path)
    }
    shipped_paths.discard(validator.PUBLIC_INVENTORY.as_posix())
    checksum_paths = {
        archive_path for archive_path, _source_path in validator.public_file_entries(root)
    }
    missing = sorted(shipped_paths - checksum_paths)
    extra = sorted(checksum_paths - shipped_paths)
    if missing or extra:
        fail(f"checksum/release surface drift: missing={missing}, extra={extra}")
    print(
        f"PASS: checksum selection matches {len(shipped_paths)} release-pack entries "
        "excluding the inventory itself"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    validator = load_validator(root)
    validate_current_release_parity(root, validator)

    with tempfile.TemporaryDirectory(prefix="processforge-checksum-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        validate_layout(validator, temp_root / "source-layout", root_agents=False)
        validate_layout(validator, temp_root / "archive-layout", root_agents=True)
        validate_stale_detection(validator, temp_root / "stale-detection")

    print("PASS: shipped checksum surface covers root aliases, public directories, and stale-file detection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
