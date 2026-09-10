#!/usr/bin/env python3
"""Regression smoke for restoring missing manifest-owned core files."""

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


def write_archive(path: Path, files: dict[str, str], *, version: str = "2.0.0") -> None:
    manifest = make_core_manifest(
        version=version,
        source={"fixture": True},
        files=[
            {"relative_path": name, "size": len(value.encode()), "sha256": hashlib.sha256(value.encode()).hexdigest()}
            for name, value in files.items()
        ],
    )
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)
        archive.writestr(CORE_MANIFEST_NAME, manifest_bytes(manifest))


def install_old(core: Path) -> None:
    files = {"same.txt": "same", "changed.txt": "old", "removed.txt": "gone"}
    for name, value in files.items():
        (core / name).write_text(value, encoding="utf-8")
    manifest = make_core_manifest(
        version="1.0.0",
        source={"fixture": True},
        files=[
            {"relative_path": name, "size": len(value.encode()), "sha256": hashlib.sha256(value.encode()).hexdigest()}
            for name, value in files.items()
        ],
    )
    (core / CORE_MANIFEST_NAME).write_bytes(manifest_bytes(manifest))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="Optional temporary fixture parent; defaults to the system temporary directory.")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pf-core-update-missing-", dir=args.root) as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old(core)
        (core / "same.txt").unlink()
        (core / "changed.txt").unlink()
        (core / "removed.txt").unlink()
        (core / "user.txt").write_text("keep", encoding="utf-8")
        archive = root / "release.zip"
        write_archive(archive, {"same.txt": "same", "changed.txt": "new"})

        plan = build_plan(core, archive)
        assert plan["status"] == "planned", plan
        assert plan["missing_owned"] == ["changed.txt", "removed.txt", "same.txt"], plan
        assert plan["unchanged"] == ["same.txt"], plan
        assert plan["restored"] == ["same.txt"], plan
        assert not (core / "same.txt").exists(), "plan must remain read-only"
        assert not (core / "runtime").exists(), "plan must not create update state"
        applied = apply_update(core, archive, confirm=True)
        assert (core / "same.txt").read_text(encoding="utf-8") == "same"
        assert (core / "changed.txt").read_text(encoding="utf-8") == "new"
        assert not (core / "removed.txt").exists()
        assert (core / "user.txt").read_text(encoding="utf-8") == "keep"
        assert applied["backed_up"]["same.txt"] is None
        assert applied["backed_up"]["changed.txt"] is None
        backup_dir = Path(applied["backup_dir"])
        assert json.loads((backup_dir / "control" / "plan.json").read_text())["missing_owned"]

    with tempfile.TemporaryDirectory(prefix="pf-core-update-missing-failure-", dir=args.root) as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old(core)
        (core / "same.txt").unlink()
        archive = root / "release.zip"
        write_archive(archive, {"same.txt": "same", "changed.txt": "old"})
        original = core_update.atomic_write

        def fail_restore(target: Path, content: bytes) -> None:
            if target.name == "same.txt":
                raise OSError("injected restore failure")
            original(target, content)

        core_update.atomic_write = fail_restore
        try:
            try:
                apply_update(core, archive, confirm=True)
            except CoreUpdateError as exc:
                assert exc.code == "file_operation_failed", exc
            else:
                raise AssertionError("injected restore failure was accepted")
        finally:
            core_update.atomic_write = original
        progress = core_status(core)["in_progress"]
        assert progress["status"] == "failed", progress
        assert progress["backed_up"]["same.txt"] is None, progress
        assert any(item["op"] == "write" and item["path"] == "same.txt" for item in progress["pending_operations"])
        assert repair_status(core)["status"] == "safe_to_rollback"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-nonregular-", dir=args.root) as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old(core)
        (core / "same.txt").unlink()
        (core / "same.txt").mkdir()
        archive = root / "release.zip"
        write_archive(archive, {"same.txt": "same"})
        plan = build_plan(core, archive)
        assert plan["status"] == "blocked", plan
        assert any(item["code"] == "nonregular_owned_path" for item in plan["blockers"]), plan

    with tempfile.TemporaryDirectory(prefix="pf-core-update-parent-", dir=args.root) as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        old = make_core_manifest(version="1.0.0", source={"fixture": True}, files=[
            {"relative_path": "dir/same.txt", "size": 4, "sha256": hashlib.sha256(b"same").hexdigest()},
        ])
        (core / CORE_MANIFEST_NAME).write_bytes(manifest_bytes(old))
        (core / "dir").write_text("user obstruction", encoding="utf-8")
        archive = root / "release.zip"
        write_archive(archive, {"dir/same.txt": "same"})
        assert build_plan(core, archive)["status"] == "blocked"
        for force in (False, True):
            try:
                apply_update(core, archive, confirm=True, force_local_modifications=force)
            except CoreUpdateError as exc:
                assert exc.code == "plan_blocked"
            else:
                raise AssertionError("missing owned file bypassed its unowned parent")
        assert (core / "dir").read_text(encoding="utf-8") == "user obstruction"
        assert not (core / "runtime").exists()

    with tempfile.TemporaryDirectory(prefix="pf-core-update-manifest-failure-", dir=args.root) as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old(core)
        (core / "same.txt").unlink()
        archive = root / "release.zip"
        write_archive(archive, {"same.txt": "same", "changed.txt": "old", "removed.txt": "gone"})
        original = core_update.atomic_write

        def fail_manifest(target: Path, content: bytes) -> None:
            if target.name == CORE_MANIFEST_NAME:
                raise OSError("injected manifest failure after restored file write")
            original(target, content)

        core_update.atomic_write = fail_manifest
        try:
            try:
                apply_update(core, archive, confirm=True)
            except CoreUpdateError as exc:
                assert exc.code == "file_operation_failed"
            else:
                raise AssertionError("expected manifest failure")
        finally:
            core_update.atomic_write = original
        progress = core_status(core)["in_progress"]
        assert progress["backed_up"]["same.txt"] is None
        assert any(op["op"] == "write" and op["path"] == "same.txt" for op in progress["completed_operations"])
        assert (core / "same.txt").read_bytes() == b"same"
        assert core_status(core)["version"] == "1.0.0"
        assert repair_status(core)["status"] == "safe_to_rollback"

    print("PASS: missing owned core update smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
