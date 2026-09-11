#!/usr/bin/env python3
"""Regression smoke for archive-declared Workplace migration sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from processforge_core import core_update
from processforge_core.core_update import (
    CORE_MANIFEST_NAME,
    CoreUpdateError,
    apply_update,
    build_plan,
    core_status,
    make_core_manifest,
    manifest_bytes,
    repair_status,
)


MIGRATION_PATH = "updates/migrations/fixture.yaml"


def migration_yaml(operations: list[dict[str, str]]) -> str:
    lines = [
        "schema_version: 1",
        "kind: processforge.workplace_migration",
        "id: fixture-migration",
        "from_versions:",
        "  - 1.0.0",
        "to_version: 1.1.0",
        "operations:",
    ]
    for operation in operations:
        lines.extend(
            [
                f"  - id: {operation['id']}",
                "    type: copy_if_missing",
                f"    source: {operation['source']}",
                f"    target: {operation['target']}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_archive(path: Path, migration: str, extra_entries: dict[str, str] | None = None, *, directory_entries: tuple[str, ...] = ()) -> None:
    core_content = "same"
    manifest = make_core_manifest(
        version="1.1.0",
        source={"fixture": True},
        files=[
            {
                "relative_path": "a.txt",
                "size": len(core_content.encode()),
                "sha256": hashlib.sha256(core_content.encode()).hexdigest(),
            }
        ],
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a.txt", core_content)
        archive.writestr(MIGRATION_PATH, migration)
        for name in directory_entries:
            archive.writestr(name, "")
        for name, content in (extra_entries or {}).items():
            archive.writestr(name, content)
        archive.writestr(CORE_MANIFEST_NAME, manifest_bytes(manifest))


def make_fixture(root: Path) -> tuple[Path, Path]:
    core = root / "core"
    core.mkdir()
    (core / "a.txt").write_text("same", encoding="utf-8")
    old_manifest = make_core_manifest(
        version="1.0.0",
        source={"fixture": True},
        files=[{"relative_path": "a.txt", "size": 4, "sha256": hashlib.sha256(b"same").hexdigest()}],
    )
    (core / CORE_MANIFEST_NAME).write_bytes(manifest_bytes(old_manifest))
    workplace = root / "workplace"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return core, workplace


def assert_blocked_source(source: str, expected_code: str, *, directory: bool = False, temp_root: Path | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="pf-migration-source-", dir=temp_root) as raw:
        root = Path(raw)
        core, workplace = make_fixture(root)
        archive = root / "release.zip"
        write_archive(
            archive,
            migration_yaml([{"id": "copy-source", "source": source, "target": "runtime-drivers/new.yaml"}]),
            directory_entries=(source,) if directory else (),
        )
        plan = build_plan(core, archive, workplace_root=workplace)
        assert plan["status"] == "blocked", plan
        assert any(item.get("code") == expected_code for item in plan["blockers"]), plan
        assert not (workplace / "runtime-drivers" / "new.yaml").exists()
        assert not (core / "runtime").exists()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="Optional disposable fixture parent.")
    args = parser.parse_args()
    temp_root = Path(args.root).resolve() if args.root else None
    assert_blocked_source("templates/missing.yaml", "workplace_migration_source_missing", temp_root=temp_root)
    assert_blocked_source("../escape.yaml", "workplace_migration_source_invalid", temp_root=temp_root)
    assert_blocked_source("templates/", "workplace_migration_source_directory", directory=True, temp_root=temp_root)

    with tempfile.TemporaryDirectory(prefix="pf-migration-positive-", dir=temp_root) as raw:
        root = Path(raw)
        core, workplace = make_fixture(root)
        existing = workplace / "runtime-drivers" / "existing.yaml"
        existing.parent.mkdir(parents=True)
        existing.write_text("keep-existing\n", encoding="utf-8")
        archive = root / "release.zip"
        write_archive(
            archive,
            migration_yaml(
                [
                    {"id": "preserve", "source": "templates/preserve.yaml", "target": "runtime-drivers/existing.yaml"},
                    {"id": "install", "source": "templates/new.yaml", "target": "runtime-drivers/new.yaml"},
                ]
            ),
            extra_entries={"templates/preserve.yaml": "archive-preserve\n", "templates/new.yaml": "new-driver\n"},
        )
        plan = build_plan(core, archive, workplace_root=workplace)
        assert plan["status"] == "planned", plan
        assert len(plan["workplace_migration"]["operations"]) == 1, plan
        assert len(plan["workplace_migration"]["preserved"]) == 1, plan
        applied = apply_update(core, archive, confirm=True, workplace_root=workplace)
        assert applied["workplace_migration"]["migration"]["id"] == "fixture-migration", applied
        assert existing.read_text(encoding="utf-8") == "keep-existing\n"
        assert (workplace / "runtime-drivers" / "new.yaml").read_text(encoding="utf-8") == "new-driver\n"

    with tempfile.TemporaryDirectory(prefix="pf-migration-read-fault-", dir=temp_root) as raw:
        root = Path(raw)
        core, workplace = make_fixture(root)
        archive = root / "release.zip"
        write_archive(
            archive,
            migration_yaml([
                {"id": "first-read", "source": "templates/first.yaml", "target": "runtime-drivers/first.yaml"},
                {"id": "faulted-read", "source": "templates/new.yaml", "target": "runtime-drivers/new.yaml"},
            ]),
            extra_entries={"templates/first.yaml": "first-driver\n", "templates/new.yaml": "new-driver\n"},
        )
        plan = build_plan(core, archive, workplace_root=workplace)
        assert plan["status"] == "planned", plan
        original = zipfile.ZipFile.read

        def fail_read(archive: zipfile.ZipFile, relative_path: str, *args, **kwargs) -> bytes:
            if relative_path == "templates/new.yaml":
                raise KeyError(relative_path)
            return original(archive, relative_path, *args, **kwargs)

        zipfile.ZipFile.read = fail_read
        try:
            try:
                apply_update(core, archive, confirm=True, workplace_root=workplace)
            except CoreUpdateError as exc:
                assert exc.code == "archive_file_missing", exc
            else:
                raise AssertionError("post-plan archive read fault was accepted")
        finally:
            zipfile.ZipFile.read = original
        status = core_status(core)
        assert status["in_progress"]["status"] == "failed", status
        assert status["in_progress"]["error"]["code"] == "archive_file_missing", status
        assert repair_status(core)["status"] == "safe_to_rollback", status
        assert not (workplace / "runtime-drivers" / "new.yaml").exists()
        assert (workplace / "runtime-drivers" / "first.yaml").read_text(encoding="utf-8") == "first-driver\n"
        backup = Path(status["in_progress"]["backup_dir"])
        record = json.loads((backup / "workplace-migration.json").read_text(encoding="utf-8"))
        assert record["status"] == "applying" and len(record["backed_up"]) == 2, record
        assert all(item["existed"] is False for item in record["backed_up"]), record

    print("PASS: core update migration source validation and recovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
