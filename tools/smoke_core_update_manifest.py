#!/usr/bin/env python3
"""Smoke-test manifest-based ProcessForge core update planning and apply."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import processforge_core.maintenance.update as core_update
from processforge_core.maintenance.update import (
    CORE_MANIFEST_NAME,
    CoreUpdateError,
    apply_update,
    core_status,
    make_core_manifest,
    manifest_bytes,
    repair_status,
)

# The named Core entry captures native before its library import.
# isort: split
import pf_native_control as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def fixture_publication(files: dict[str, str], *, version: str, child_fault: str | None = None) -> native.Build:
    """Freeze fixture source before installation; never repin a damaged target."""
    execution = native.current_entry()
    assert execution is not None and execution.publication is not None
    payload = dict(execution.publication.payload)
    payload.update({name: value.encode("utf-8") for name, value in files.items()})
    payload["VERSION"] = (version + "\n").encode()
    payload[native.INVENTORY] = b""
    if child_fault is not None:
        name = "src/processforge_core/maintenance/update.py"
        source = payload[name].decode("utf-8")
        if child_fault == "workplace-write":
            before = '                atomic_write(target, read_archive_member(archive, str(operation["source"])))'
            after = ('                if target.name == "codex-exec.yaml":\n'
                     '                    raise OSError("locked workplace fixture")\n' + before)
        elif child_fault == "migration-read":
            before = '        return archive.read(relative_path)'
            after = ('        if relative_path == "templates/new.yaml":\n'
                     '            raise KeyError(relative_path)\n' + before)
        else:
            raise AssertionError(child_fault)
        assert source.count(before) == 1, "fixture fault boundary moved"
        payload[name] = source.replace(before, after).encode("utf-8")
    return native.build_publication(payload, version=version, source={"fixture": True}, generated_at="fixture")


def write_native_archive(path: Path, files: dict[str, str], *, version: str = "2.0.0", child_fault: str | None = None) -> None:
    candidate = fixture_publication(files, version=version, child_fault=child_fault)
    with zipfile.ZipFile(path, "w") as archive:
        for name, raw in {**candidate.payload, native.MANIFEST: candidate.manifest}.items():
            archive.writestr(name, raw)


@contextmanager
def managed_target(core: Path, files: dict[str, str], *, workplace_root: Path | None = None) -> Iterator[native.NativeEntry]:
    """Own the original manager and adopt intact bytes before any corruption."""
    if workplace_root is not None:
        manifest = workplace_root / "workplace.yaml"
        manifest.write_text(manifest.read_text(encoding="utf-8") + "\nworkplace:\n  id: fixture-workplace\n", encoding="utf-8")
        identity = workplace_root / "data/accounting/identity.json"
        identity.parent.mkdir(parents=True, exist_ok=True)
        identity.write_text(json.dumps({"origin_id": "fixture-accounting"}), encoding="utf-8")
    candidate = fixture_publication(files, version="1.0.0")
    core.mkdir(parents=True, exist_ok=True)
    for name, raw in {**candidate.payload, native.MANIFEST: candidate.manifest}.items():
        target = core / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    manager_root = core.parent / "original-manager"
    manager_root.mkdir()
    (manager_root / "gate").write_bytes(b"0")
    (manager_root / "protocol").write_bytes(b"original")
    boundary = native.LegacyManagedBoundary(
        core, existing_gate=native.NativeControl(manager_root / "gate", manager_root / "protocol", "original"),
        accepted_archive=candidate.payload,
    )
    try:
        owner = boundary.launch([sys.executable, "-B", "-c", "pass"], ingress="worker")
        assert owner.wait(timeout=5) == 0
        publication = native.accept_publication(core, trusted_leaf=candidate.payload[native.LEAF])
        assert publication is not None
        entry = native.NativeEntry(core.resolve(), publication, native.NativeImage.from_publication(core, publication), None)
        from processforge_core.composition import (
            build_configuration_provider,
            build_storage_migration_host,
        )
        from processforge_core.configuration import (
            ConfigurationProvider,
            DeviceConfigurationSource,
        )

        # A core-only update still needs a real storage owner for adoption.
        # Use the same project setup as the native adopted-manager fixture;
        # leave workplace routing intact for its real post-update storage child.
        project_root = None
        if workplace_root is None:
            project_root = manager_root / "project"
            flow = project_root / ".pf"
            flow.mkdir(parents=True)
            (flow / "process-forge.yaml").write_text(
                "project:\n  id: fixture-project\n", encoding="utf-8"
            )
        device = DeviceConfigurationSource.default_path()
        provider = build_configuration_provider(
            project_root=project_root,
            workplace_root=workplace_root,
            device_config_path=device,
        )
        snapshot = provider.snapshot()
        assert not snapshot.errors
        host = build_storage_migration_host(
            project_root=project_root,
            workplace_root=workplace_root,
            device_config_path=device,
            configuration=ConfigurationProvider.pinned(snapshot.config),
        )
        assert host.context.targets and not host.context.unqualified_targets
        selection = host.service._native_selection
        assert selection is not None
        _, entry = native.ManagedEnrollmentProducer.from_legacy_manager(boundary, entry, selection=selection())
        assert entry.control is not None
        # Target image stays inactive: M executes; T is physically observed data.
        yield entry
    finally:
        for owners in boundary.owners.values():
            for process in owners:
                getattr(process, "native_job").close()
        boundary.anchor.close()


def apply_managed_update(entry: native.NativeEntry, archive: Path, *, force_local_modifications: bool = False, workplace_root: Path | None = None) -> dict[str, Any]:
    with native._replacement_target(entry):
        return apply_update(entry.root, archive, confirm=True, force_local_modifications=force_local_modifications, workplace_root=workplace_root)


def run_managed_smoke(script: Path) -> int:
    """Capture an independent management fixture before the child's Core imports."""
    payload = {}
    for directory in ("src", "tools", "schemas"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".txt", ".md"} and "__pycache__" not in path.parts:
                payload[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    payload["VERSION"] = b"1.0.0\n"
    payload[native.INVENTORY] = b""
    candidate = native.build_publication(payload, version="1.0.0", source={"fixture": True}, generated_at="fixture")
    with tempfile.TemporaryDirectory(prefix="pf-update-management-", dir=os.environ.get("W3_FIXTURE_ROOT")) as raw:
        management = Path(raw)
        for name, content in {**candidate.payload, native.MANIFEST: candidate.manifest}.items():
            target = management / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        device = management / "runtime/device/ProcessForge/configuration.yaml"
        device.parent.mkdir(parents=True)
        device.write_text("schema_version: 1\n", encoding="utf-8")
        code = """import importlib.util,sys,types
from pathlib import Path
root=Path(sys.argv[1]);script=sys.argv[2];sys.argv=[script,*sys.argv[3:]]
leaf=(root/'tools/pf_native_control.py').read_bytes()
p=types.ModuleType('pf_native_control');p.__file__=str(root/'tools/pf_native_control.py');p._captured_source=leaf
sys.modules[p.__name__]=p;exec(compile(leaf,p.__file__,'exec',dont_inherit=True),p.__dict__)
p.bootstrap_entry(root,trusted_leaf=leaf)
sys.path[:0]=[str(root/'tools'),str(root/'src')]
spec=importlib.util.spec_from_file_location('_pf_updater_smoke',root/'tools'/script)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
raise SystemExit(module.main())
"""
        return subprocess.run([sys.executable, "-I", "-B", "-c", code, str(management), script.name, *sys.argv[1:]], env={**os.environ, "LOCALAPPDATA": str(management / "runtime/device"), "PYTHONDONTWRITEBYTECODE": "1"}, check=False).returncode


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


def assert_refused_without_mutation(core: Path, archive: Path, before, entry: native.NativeEntry, *, user_paths: tuple[str, ...], force: bool) -> None:
    authority = {name: (core / name).read_bytes() for name in ("runtime/managed-ingress/baseline.json", "runtime/managed-ingress/adoption.json", "runtime/native-control/epoch")}
    try:
        apply_managed_update(entry, archive, force_local_modifications=force)
    except CoreUpdateError as exc:
        assert exc.code == "plan_blocked", exc
    else:
        raise AssertionError(f"blocked update accepted with force={force}")
    assert {name: (core / name).read_bytes() for name in authority} == authority
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

        cli_status = run_pf("core-update", "status", "--core-root", str(core))
        assert cli_status.returncode == 0, cli_status.stdout + cli_status.stderr
        assert json.loads(cli_status.stdout)["version"] == "1.0.0"

        cli_plan = run_pf("core-update", "plan", "--core-root", str(core), "--archive", str(archive))
        assert cli_plan.returncode == 0, cli_plan.stdout + cli_plan.stderr
        plan_data = json.loads(cli_plan.stdout)
        assert plan_data["counts"]["removed"] == 1
        assert plan_data["counts"]["changed"] == 1
        assert plan_data["counts"]["added"] == 1

        blocked = run_pf("core-update", "apply", "--core-root", str(core), "--archive", str(archive))
        assert blocked.returncode != 0 and "confirm_required" in blocked.stdout

        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            write_native_archive(archive, {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "d.txt": "new-d"})
            applied = apply_managed_update(entry, archive)
            assert applied["status"] == "applied", applied
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
        cli_plan = run_pf("core-update", "plan", "--core-root", str(core), "--archive", str(archive))
        assert cli_plan.returncode == 2, cli_plan.stdout + cli_plan.stderr
        assert json.loads(cli_plan.stdout)["blockers"][0]["code"] == "locally_modified"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-owned-ancestor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            archive = root / "processforge.zip"
            write_native_archive(archive, {"a.txt/child.txt": "new child", "dir/b.txt": "old-b", "dir/c.txt": "same-c"})

            applied = apply_managed_update(entry, archive)
            assert (core / "a.txt" / "child.txt").read_text(encoding="utf-8") == "new child"
            backup = Path(applied["backup_dir"]) / "files" / "a.txt"
            assert backup.read_bytes() == b"old-a"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-owned-ancestor-modified-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            ancestor = core / "a.txt"
            ancestor.write_text("local-a", encoding="utf-8")
            archive = root / "processforge.zip"
            write_native_archive(archive, {"a.txt/child.txt": "new child", "dir/b.txt": "old-b", "dir/c.txt": "same-c"})
            before = ancestor.read_bytes()

            plan = core_update.build_plan(core, archive)
            assert plan["status"] == "blocked", plan
            assert any(item.get("code") == "locally_modified" and item.get("path") == "a.txt" for item in plan["blockers"]), plan
            try:
                apply_managed_update(entry, archive)
            except CoreUpdateError as exc:
                assert exc.code == "plan_blocked", exc
            else:
                raise AssertionError("locally modified owned ancestor was accepted without force")
            assert ancestor.read_bytes() == before

            forced = apply_managed_update(entry, archive, force_local_modifications=True)
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
            with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
                make_collision(core)
                collision_payload = "same-byte" if fixture_name == "same-byte-file" else "NEW CORE PAYLOAD"
                archive = root / "processforge.zip"
                write_native_archive(
                    archive,
                    {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "user-note.txt": collision_payload},
                )
                before = snapshot_core_state(core, ("user-note.txt",))
                plan = core_update.build_plan(core, archive)
                assert plan["status"] == "blocked", plan
                assert any(item.get("code") == "unowned_path_collision" and item.get("path") == "user-note.txt" for item in plan["blockers"]), plan
                for force in (False, True):
                    assert_refused_without_mutation(core, archive, before, entry, user_paths=("user-note.txt",), force=force)

    with tempfile.TemporaryDirectory(prefix="pf-core-update-unowned-ancestor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            (core / "user-area").write_text("USER OWNED DATA", encoding="utf-8")
            archive = root / "processforge.zip"
            write_native_archive(archive, {"user-area/new.txt": "NEW CORE PAYLOAD"})
            plan = core_update.build_plan(core, archive)
            assert plan["status"] == "blocked", plan
            assert any(item.get("conflict_path") == "user-area" for item in plan["blockers"]), plan
            before = snapshot_core_state(core, ("user-area",))
            for force in (False, True):
                assert_refused_without_mutation(core, archive, before, entry, user_paths=("user-area",), force=force)

    with tempfile.TemporaryDirectory(prefix="pf-core-update-unowned-late-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            archive = root / "processforge.zip"
            write_native_archive(archive, {"new.txt": "NEW CORE PAYLOAD"})
            plan = core_update.build_plan(core, archive)
            assert plan["status"] == "planned", plan
            (core / "new.txt").write_text("LATE USER DATA", encoding="utf-8")
            before = snapshot_core_state(core, ("new.txt",))
            for force in (False, True):
                assert_refused_without_mutation(core, archive, before, entry, user_paths=("new.txt",), force=force)

    for symlink_name, broken in (("symlink", False), ("broken-symlink", True)):
        with tempfile.TemporaryDirectory(prefix=f"pf-core-update-unowned-{symlink_name}-") as raw:
            root = Path(raw)
            core = root / "core"
            core.mkdir()
            with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
                outside = root / "outside.txt"
                outside.write_text("OUTSIDE DATA", encoding="utf-8")
                link = core / "user-link.txt"
                archive = root / "processforge.zip"
                write_native_archive(archive, {"user-link.txt": "NEW CORE PAYLOAD"})
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
                    assert_refused_without_mutation(core, archive, before, entry, user_paths=("user-link.txt",), force=force)
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
        cli_plan = run_pf("core-update", "plan", "--core-root", str(root / "core"), "--archive", str(archive))
        assert cli_plan.returncode != 0 and "invalid_manifest_path" in cli_plan.stdout

    with tempfile.TemporaryDirectory(prefix="pf-core-update-locked-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}) as entry:
            archive = root / "processforge.zip"
            write_native_archive(archive, {"dir/b.txt": "new-b", "dir/c.txt": "same-c", "d.txt": "new-d"})
            original_atomic_write = native._update_atomic

            def fail_on_changed_file(path: Path, raw: bytes) -> None:
                if path.name == "b.txt":
                    raise OSError("locked fixture")
                original_atomic_write(path, raw)

            native._update_atomic = fail_on_changed_file
            try:
                try:
                    apply_managed_update(entry, archive)
                except CoreUpdateError as exc:
                    assert exc.code == "file_operation_failed"
                else:
                    raise AssertionError("locked file failure was accepted")
            finally:
                native._update_atomic = original_atomic_write
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
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}, workplace_root=workplace) as entry:
            archive = root / "processforge-1.1.0.zip"
            write_native_archive(
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
            record = apply_managed_update(entry, archive, workplace_root=workplace)
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
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}, workplace_root=workplace) as entry:
            archive = root / "processforge-1.1.0.zip"
            write_native_archive(archive, {"updates/migrations/1.1.0-workplace-runtime-drivers.yaml": migration_yaml, "templates/runtime-drivers/codex-exec.yaml": driver_yaml}, version="1.1.0", child_fault="workplace-write")
            try:
                apply_managed_update(entry, archive, workplace_root=workplace)
            except CoreUpdateError as exc:
                assert exc.code == "file_operation_failed"
            else:
                raise AssertionError("locked Workplace migration was accepted")
            assert core_status(core)["version"] == "1.1.0"
            assert repair_status(core)["status"] == "manual_repair_required"

    with tempfile.TemporaryDirectory(prefix="pf-core-update-workplace-doctor-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        install_old_core(core)
        workplace = root / "workplace"
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        (workplace / "registries" / "runtime-drivers.yaml").write_text(registry_yaml, encoding="utf-8")
        with managed_target(core, {"a.txt": "old-a", "dir/b.txt": "old-b", "dir/c.txt": "same-c"}, workplace_root=workplace) as entry:
            archive = root / "processforge-1.1.0.zip"
            write_native_archive(
                archive,
                {
                    "tools/processforge.py": "def main(arguments):\n    assert arguments[0] == 'doctor-workplace'\n    print('PASS: fixture doctor')\n    return 0\n",
                    "updates/migrations/1.1.0-workplace-runtime-drivers.yaml": migration_yaml,
                    "templates/runtime-drivers/codex-exec.yaml": driver_yaml,
                },
                version="1.1.0",
            )
            payload = apply_managed_update(entry, archive, workplace_root=workplace)
            assert payload["status"] == "applied", payload
            assert payload["post_update_doctor"]["status"] == "pass", payload
            assert "PASS: fixture doctor" in payload["post_update_doctor"]["output"]

            assert payload["post_update_doctor"]["storage_migration"]["exit_code"] == 0, payload
    print("PASS: manifest-based core update smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_managed_smoke(Path(__file__)))
