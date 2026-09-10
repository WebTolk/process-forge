#!/usr/bin/env python3
"""Smoke-test manifest-based ProcessForge core update planning and apply."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from processforge_core import core_update
from processforge_core.core_update import CORE_MANIFEST_NAME, CoreUpdateError, apply_update, core_status, make_core_manifest, manifest_bytes, repair_status


def run_pf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ROOT / "tools" / "processforge.py"), *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)


def sha_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_archive(path: Path, files: dict[str, str], *, version: str = "2.0.0") -> None:
    manifest = make_core_manifest(
        version=version,
        source={"fixture": True},
        files=[{"relative_path": item_path, "size": len(content.encode("utf-8")), "sha256": sha_text(content)} for item_path, content in files.items()],
    )
    with zipfile.ZipFile(path, "w") as archive:
        for item_path, content in files.items():
            archive.writestr(item_path, content)
        archive.writestr(CORE_MANIFEST_NAME, manifest_bytes(manifest))


def install_old_core(core: Path) -> None:
    old_files = {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}
    for item_path, content in old_files.items():
        target = core / item_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest = make_core_manifest(
        version="1.0.0",
        source={"fixture": True},
        files=[{"relative_path": item_path, "size": len(content.encode("utf-8")), "sha256": sha_text(content)} for item_path, content in old_files.items()],
    )
    (core / CORE_MANIFEST_NAME).write_bytes(manifest_bytes(manifest))


def snapshot_object(path: Path):
    """Capture an object lexically, including directories and symlinks."""
    if path.is_symlink():
        if path.is_dir():
            kind = "symlink-directory"
        else:
            kind = "symlink"
        return (kind, os.readlink(path))
    if path.is_dir():
        return ("directory", tuple(sorted((child.name, snapshot_object(child)) for child in path.iterdir())))
    if path.is_file():
        return ("file", path.read_bytes())
    return ("absent",)


def snapshot_core_state(core: Path, user_paths: tuple[str, ...] = ()):
    owned_paths = ("a.txt", "dir/b.txt", "dir/c.txt")
    return {
        "owned": {relative_path: (core / relative_path).read_bytes() for relative_path in owned_paths},
        "manifest": (core / CORE_MANIFEST_NAME).read_bytes(),
        "user_objects": {relative_path: snapshot_object(core / relative_path) for relative_path in user_paths},
    }


def assert_refused_without_mutation(core: Path, archive: Path, before, *, user_paths: tuple[str, ...], force: bool) -> None:
    try:
        apply_update(core, archive, confirm=True, force_local_modifications=force)
    except CoreUpdateError as exc:
        assert exc.code == "plan_blocked", exc
    else:
        raise AssertionError(f"blocked update accepted with force={force}")
    assert snapshot_core_state(core, user_paths) == before
    assert not (core / "runtime" / "core-update").exists()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-core-update-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        (core / "user-note.txt").write_text("must stay", encoding="utf-8")
        archive = root / "processforge.zip"
        write_archive(archive, {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "d.txt": "new-d"})

        status = run_pf("core-update", "status", "--core-root", str(core))
        assert status.returncode == 0, status.stdout + status.stderr
        assert json.loads(status.stdout)["version"] == "1.0.0"

        plan = run_pf("core-update", "plan", "--core-root", str(core), "--archive", str(archive))
        assert plan.returncode == 0, plan.stdout + plan.stderr
        plan_data = json.loads(plan.stdout)
        assert plan_data["counts"]["removed"] == 1
        assert plan_data["counts"]["changed"] == 1
        assert plan_data["counts"]["added"] == 1

        blocked = run_pf("core-update", "apply", "--core-root", str(core), "--archive", str(archive))
        assert blocked.returncode != 0 and "confirm_required" in blocked.stdout

        applied = run_pf("core-update", "apply", "--core-root", str(core), "--archive", str(archive), "--confirm")
        assert applied.returncode == 0, applied.stdout + applied.stderr
        assert not (core / "a.txt").exists()
        assert (core / "dir" / "b.txt").read_text(encoding="utf-8") == "new-b"
        assert (core / "dir" / "c.txt").read_text(encoding="utf-8") == "same-c"
        assert (core / "d.txt").read_text(encoding="utf-8") == "new-d"
        assert (core / "user-note.txt").read_text(encoding="utf-8") == "must stay"
        assert json.loads((core / CORE_MANIFEST_NAME).read_text(encoding="utf-8"))["version"] == "2.0.0"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-local-mod-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        (core / "dir" / "b.txt").write_text("local-change", encoding="utf-8")
        archive = root / "processforge.zip"
        write_archive(archive, {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "d.txt": "new-d"})
        plan = run_pf("core-update", "plan", "--core-root", str(core), "--archive", str(archive))
        assert plan.returncode == 2, plan.stdout + plan.stderr
        assert json.loads(plan.stdout)["blockers"][0]["code"] == "locally_modified"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-owned-ancestor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        archive = root / "processforge.zip"
        write_archive(archive, {"a.txt/child.txt": "new child", "dir/b.txt": "old-b", "dir/c.txt": "same-c"})

        applied = apply_update(core, archive, confirm=True)
        assert (core / "a.txt" / "child.txt").read_text(encoding="utf-8") == "new child"
        backup = Path(applied["backup_dir"]) / "files" / "a.txt"
        assert backup.read_bytes() == b"old-a"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-owned-ancestor-modified-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        ancestor = core / "a.txt"
        ancestor.write_text("local-a", encoding="utf-8")
        archive = root / "processforge.zip"
        write_archive(archive, {"a.txt/child.txt": "new child", "dir/b.txt": "old-b", "dir/c.txt": "same-c"})
        before = ancestor.read_bytes()

        plan = core_update.build_plan(core, archive)
        assert plan["status"] == "blocked", plan
        assert any(item.get("code") == "locally_modified" and item.get("path") == "a.txt" for item in plan["blockers"]), plan
        try:
            apply_update(core, archive, confirm=True)
        except CoreUpdateError as exc:
            assert exc.code == "plan_blocked", exc
        else:
            raise AssertionError("locally modified owned ancestor was accepted without force")
        assert ancestor.read_bytes() == before

        forced = apply_update(core, archive, confirm=True, force_local_modifications=True)
        assert (core / "a.txt" / "child.txt").read_text(encoding="utf-8") == "new child"
        forced_backup = Path(forced["backup_dir"]) / "files" / "a.txt"
        assert forced_backup.read_bytes() == before

    def make_directory_collision(core: Path) -> None:
        collision = core / "user-note.txt"
        collision.mkdir()
        (collision / "keep.txt").write_text("DIRECTORY USER DATA", encoding="utf-8")

    for fixture_name, make_collision in (
        ("file", lambda core: (core / "user-note.txt").write_text("USER OWNED DATA", encoding="utf-8")),
        ("same-byte-file", lambda core: (core / "user-note.txt").write_text("same-byte", encoding="utf-8")),
        ("directory", make_directory_collision),
    ):
        with tempfile.TemporaryDirectory(prefix=f"pf-core-update-unowned-{fixture_name}-") as raw:
            root = Path(raw)
            core = root / "core"
            core.mkdir()
            install_old_core(core)
            make_collision(core)
            payload = "same-byte" if fixture_name == "same-byte-file" else "NEW CORE PAYLOAD"
            archive = root / "processforge.zip"
            write_archive(
                archive,
                {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "user-note.txt": payload},
            )
            before = snapshot_core_state(core, ("user-note.txt",))
            plan = core_update.build_plan(core, archive)
            assert plan["status"] == "blocked", plan
            assert any(item.get("code") == "unowned_path_collision" and item.get("path") == "user-note.txt" for item in plan["blockers"]), plan
            for force in (False, True):
                assert_refused_without_mutation(core, archive, before, user_paths=("user-note.txt",), force=force)

    with tempfile.TemporaryDirectory(prefix="pf-core-update-unowned-ancestor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        (core / "user-area").write_text("USER OWNED DATA", encoding="utf-8")
        archive = root / "processforge.zip"
        write_archive(archive, {"user-area/new.txt": "NEW CORE PAYLOAD"})
        plan = core_update.build_plan(core, archive)
        assert plan["status"] == "blocked", plan
        assert any(item.get("conflict_path") == "user-area" for item in plan["blockers"]), plan
        before = snapshot_core_state(core, ("user-area",))
        for force in (False, True):
            assert_refused_without_mutation(core, archive, before, user_paths=("user-area",), force=force)

    with tempfile.TemporaryDirectory(prefix="pf-core-update-unowned-late-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        archive = root / "processforge.zip"
        write_archive(archive, {"new.txt": "NEW CORE PAYLOAD"})
        plan = core_update.build_plan(core, archive)
        assert plan["status"] == "planned", plan
        (core / "new.txt").write_text("LATE USER DATA", encoding="utf-8")
        before = snapshot_core_state(core, ("new.txt",))
        for force in (False, True):
            assert_refused_without_mutation(core, archive, before, user_paths=("new.txt",), force=force)

    for symlink_name, broken in (("symlink", False), ("broken-symlink", True)):
        with tempfile.TemporaryDirectory(prefix=f"pf-core-update-unowned-{symlink_name}-") as raw:
            root = Path(raw)
            core = root / "core"
            core.mkdir()
            install_old_core(core)
            outside = root / "outside.txt"
            outside.write_text("OUTSIDE DATA", encoding="utf-8")
            link = core / "user-link.txt"
            archive = root / "processforge.zip"
            write_archive(archive, {"user-link.txt": "NEW CORE PAYLOAD"})
            try:
                link.symlink_to(root / "missing-target" if broken else outside)
            except (OSError, NotImplementedError) as exc:
                print(f"SKIP: {symlink_name} fixture unavailable: {exc}")
                continue
            plan = core_update.build_plan(core, archive)
            assert plan["status"] == "blocked", plan
            assert any(item.get("code") == "unowned_path_collision" for item in plan["blockers"]), plan
            before = snapshot_core_state(core, ("user-link.txt",))
            for force in (False, True):
                assert_refused_without_mutation(core, archive, before, user_paths=("user-link.txt",), force=force)
            assert link.is_symlink()
            assert outside.read_text(encoding="utf-8") == "OUTSIDE DATA"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-malicious-") as raw:
        root = Path(raw)
        archive = root / "bad.zip"
        manifest = {
            "schema_version": 1,
            "kind": "processforge.core_manifest",
            "version": "9.9.9",
            "files": [{"relative_path": "../escape.txt", "size": 1, "sha256": "0" * 64}],
        }
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("../escape.txt", "x")
            package.writestr(CORE_MANIFEST_NAME, json.dumps(manifest))
        plan = run_pf("core-update", "plan", "--core-root", str(root / "core"), "--archive", str(archive))
        assert plan.returncode != 0 and "invalid_manifest_path" in plan.stdout

    with tempfile.TemporaryDirectory(prefix="pf-core-update-locked-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        archive = root / "processforge.zip"
        write_archive(archive, {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "d.txt": "new-d"})
        original_atomic_write = core_update.atomic_write

        def fail_on_changed_file(target: Path, content: bytes) -> None:
            if target.name == "b.txt":
                raise OSError("locked fixture")
            original_atomic_write(target, content)

        core_update.atomic_write = fail_on_changed_file
        try:
            try:
                apply_update(core, archive, confirm=True)
            except CoreUpdateError as exc:
                assert exc.code == "file_operation_failed"
            else:
                raise AssertionError("locked file failure was accepted")
        finally:
            core_update.atomic_write = original_atomic_write
        status = core_status(core)
        assert status["incomplete_update"] is True
        assert status["in_progress"]["status"] == "failed"
        assert status["in_progress"]["pending_operations"]
        assert status["in_progress"]["completed_operations"]
        assert status["in_progress"]["error"]["code"] == "file_operation_failed"
        assert repair_status(core)["status"] == "safe_to_rollback"

    migration_yaml = """schema_version: 1
kind: processforge.workplace_migration
id: fixture-workplace-1.0.2-to-1.1.0
from_versions:
  - 1.0.0
  - 1.0.1
  - 1.0.2
allow_unmanaged_installed_core: true
to_version: 1.1.0
operations:
  - id: install-codex-exec-driver
    type: copy_if_missing
    source: templates/runtime-drivers/codex-exec.yaml
    target: runtime-drivers/codex-exec.yaml
  - id: register-codex-exec-driver
    type: append_registry_entry_if_missing
    target: registries/runtime-drivers.yaml
    list_key: runtime_drivers
    match_key: id
    entry:
      id: codex-exec
      path: ../runtime-drivers/codex-exec.yaml
      status: available
      builtin: true
"""
    driver_yaml = "schema_version: 1\nid: codex-exec\nkind: shell\n"
    registry_yaml = "schema_version: 1\nruntime_drivers:\n  - id: manual\n    path: ../runtime-drivers/manual.yaml\ncustom_registry_setting: preserve\n"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-workplace-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        workplace = root / "workplace"
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text("schema_version: 1\ncustom_setting: preserve\n", encoding="utf-8")
        (workplace / "registries" / "runtime-drivers.yaml").write_text(registry_yaml, encoding="utf-8")
        archive = root / "processforge-1.1.0.zip"
        write_archive(
            archive,
            {
                "dir/b.txt": "new-b",
                "dir/c.txt": "same-c",
                "d.txt": "new-d",
                "updates/migrations/1.1.0-workplace-runtime-drivers.yaml": migration_yaml,
                "templates/runtime-drivers/codex-exec.yaml": driver_yaml,
            },
            version="1.1.0",
        )
        plan = core_update.build_plan(core, archive, workplace_root=workplace)
        assert plan["status"] == "planned", plan
        assert plan["workplace_migration"]["status"] == "planned", plan
        assert len(plan["workplace_migration"]["operations"]) == 2, plan
        record = apply_update(core, archive, confirm=True, workplace_root=workplace)
        assert record["workplace_migration"]["migration"]["id"] == "fixture-workplace-1.0.2-to-1.1.0", record
        assert (workplace / "runtime-drivers" / "codex-exec.yaml").read_text(encoding="utf-8") == driver_yaml
        migrated_registry = (workplace / "registries" / "runtime-drivers.yaml").read_text(encoding="utf-8")
        assert "custom_registry_setting: preserve" in migrated_registry
        assert "id: codex-exec" in migrated_registry
        assert "custom_setting: preserve" in (workplace / "workplace.yaml").read_text(encoding="utf-8")
        assert (Path(record["backup_dir"]) / "workplace-migration.json").is_file()

    with tempfile.TemporaryDirectory(prefix="pf-core-update-workplace-failure-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        workplace = root / "workplace"
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        (workplace / "registries" / "runtime-drivers.yaml").write_text(registry_yaml, encoding="utf-8")
        archive = root / "processforge-1.1.0.zip"
        write_archive(archive, {"updates/migrations/1.1.0-workplace-runtime-drivers.yaml": migration_yaml, "templates/runtime-drivers/codex-exec.yaml": driver_yaml}, version="1.1.0")
        original_atomic_write = core_update.atomic_write

        def fail_on_workplace_driver(target: Path, content: bytes) -> None:
            if target.name == "codex-exec.yaml":
                raise OSError("locked workplace fixture")
            original_atomic_write(target, content)

        core_update.atomic_write = fail_on_workplace_driver
        try:
            try:
                apply_update(core, archive, confirm=True, workplace_root=workplace)
            except CoreUpdateError as exc:
                assert exc.code == "file_operation_failed"
            else:
                raise AssertionError("locked Workplace migration was accepted")
        finally:
            core_update.atomic_write = original_atomic_write
        assert repair_status(core)["status"] == "safe_to_rollback"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-workplace-doctor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        workplace = root / "workplace"
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        (workplace / "registries" / "runtime-drivers.yaml").write_text(registry_yaml, encoding="utf-8")
        archive = root / "processforge-1.1.0.zip"
        write_archive(
            archive,
            {
                "bin/pf.py": "import sys\nprint('PASS: fixture doctor')\nraise SystemExit(0)\n",
                "updates/migrations/1.1.0-workplace-runtime-drivers.yaml": migration_yaml,
                "templates/runtime-drivers/codex-exec.yaml": driver_yaml,
            },
            version="1.1.0",
        )
        applied = run_pf("core-update", "apply", "--core-root", str(core), "--archive", str(archive), "--workplace-root", str(workplace), "--confirm")
        assert applied.returncode == 0, applied.stdout + applied.stderr
        payload = json.loads(applied.stdout)
        assert payload["post_update_doctor"]["status"] == "pass", payload
        assert "PASS: fixture doctor" in payload["post_update_doctor"]["output"]

    print("PASS: manifest-based core update smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
