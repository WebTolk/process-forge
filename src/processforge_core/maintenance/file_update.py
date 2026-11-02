"""Manifest-owned archive updates for existing file-only installations.

This compatibility route supplies a cooperating updater mutex and recovery
journal. It never supplies native enrollment, migration authority or proof that
unrelated interpreters have retired. Managed installations retain their own
exclusive replacement protocol.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any

from .release_sources import ReleaseSourcePolicy
from .update import CORE_MANIFEST_NAME, CoreUpdateError, _build_plan, manifest_file_map


def _target_root(core_root: Path) -> Path:
    """Read the actual root; an inaccessible path is never absence."""
    root = core_root.absolute()
    try:
        for node in (root, *root.parents):
            info = node.lstat()
            if (
                not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise CoreUpdateError(
                    "plan_blocked", "file update root contains a link"
                )
        root = root.resolve(strict=True)
        try:
            runtime = (root / "runtime").lstat()
        except FileNotFoundError:
            pass
        else:
            if (
                not stat.S_ISDIR(runtime.st_mode)
                or getattr(runtime, "st_file_attributes", 0) & 0x400
            ):
                raise CoreUpdateError(
                    "plan_blocked", "file update runtime is not a directory"
                )
    except OSError as error:
        raise CoreUpdateError(
            "plan_blocked", "file update root cannot be inspected"
        ) from error
    return root


def _managed_marker_present(root: Path) -> bool:
    for name in ("native-control", "managed-ingress"):
        try:
            (root / "runtime" / name).lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise CoreUpdateError(
                "plan_blocked", "native enrollment state cannot be inspected"
            ) from error
        else:
            return True
    return False


def require_unmanaged_target(core_root: Path) -> Path:
    """Validate a real root with no complete or partial native enrollment."""
    root = _target_root(core_root)
    if _managed_marker_present(root):
        raise CoreUpdateError(
            "plan_blocked", "managed installation requires native replacement"
        )
    return root


def file_update_candidate(core_root: Path) -> bool:
    """Select only a sealed, unbound caller and a never-enrolled target."""
    from pf_native_control import current_entry

    entry = current_entry()
    if (
        entry is None
        or entry.control is not None
        or entry.publication is None
        or entry.image is None
    ):
        return False
    # Presence, including a broken link or an empty directory, is a managed
    # refusal. Do not turn an error in managed metadata into a compatibility path.
    root = _target_root(core_root)
    if _managed_marker_present(root):
        return False
    if root == entry.root or root in entry.root.parents or entry.root in root.parents:
        raise CoreUpdateError("plan_blocked", "installer and target roots overlap")
    return (root / CORE_MANIFEST_NAME).is_file()


class _Failure(Exception):
    """Carry errors through generator scopes without frozen exception mutation."""

    def __init__(self, code: str, message: str) -> None:
        self.code, self.message = code, message
        super().__init__(message)


def apply_file_update(
    core_root: Path,
    archive_path: Path,
    *,
    workplace_root: Path | None,
) -> dict[str, Any]:
    """Apply a frozen release archive using the existing ownership contract."""
    from pf_native_control import (
        _PHYSICAL_OPEN,
        MAX_FILE,
        MAX_MANIFEST,
        _freeze_update_archive,
        _read_regular,
        _update_now,
        _update_target,
    )

    from ..runtime.execution_admission import registry_file_lock

    if not file_update_candidate(core_root):
        raise CoreUpdateError(
            "plan_blocked",
            "file update requires an external sealed file-only installer",
        )
    root = require_unmanaged_target(core_root)

    def atomic(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        staging = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pf-update-tmp")
        created = False
        try:
            with _PHYSICAL_OPEN(staging, "xb") as stream:
                created = True
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(staging, path)
        finally:
            if created:
                staging.unlink(missing_ok=True)

    def write_json(path: Path, value: dict[str, Any]) -> None:
        atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())

    def require_offline() -> None:
        if workplace_root is None:
            return
        from pf_runtime.service import inspect_lifecycle

        from ..runtime.observation_inputs import WorkerObservationInputService

        observed = inspect_lifecycle(workplace_root, None)
        pid = observed["state"].get("pid")
        if (
            observed["kind"] not in {"stopped", "not_running", "stale"}
            or observed["pid_running"]
            or (
                isinstance(pid, int)
                and WorkerObservationInputService().process_pid_running(pid)
            )
        ):
            raise CoreUpdateError(
                "plan_blocked", "stop the Workplace App Server before file update"
            )

    # Read the archive once. Subsequent path replacement cannot change the bytes
    # whose manifest, seal, inventory and every member are verified below.
    try:
        with _PHYSICAL_OPEN(archive_path, "rb") as stream:
            archive_raw = stream.read()
        lock = _update_target(root, "runtime/core-update/file-maintenance")
        for name in (f".{lock.name}.lock", f".{lock.name}.lock.guard"):
            path = _update_target(root, f"runtime/core-update/{name}")
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise CoreUpdateError(
                    "plan_blocked", "file maintenance lock is not regular"
                )
    except OSError as error:
        raise CoreUpdateError(
            "plan_blocked", "file update inputs or control paths cannot be inspected"
        ) from error

    def read(relative: str, limit: int = MAX_FILE) -> bytes:
        return _read_regular(root, relative, limit)

    def physical_digest(path: Path) -> str:
        return hashlib.sha256(read(path.relative_to(root).as_posix())).hexdigest()

    def checked_paths(manifest: dict[str, Any]) -> None:
        policy = ReleaseSourcePolicy()
        public_pf = {".pf/agents.md", ".pf/process-forge.yaml", ".pf/hooks.yaml"}
        for relative in manifest_file_map(manifest):
            folded = relative.casefold()
            if (
                folded.startswith("runtime/")
                or (folded.startswith(".pf/") and folded not in public_pf)
                or policy.release_path_is_forbidden(folded)
            ):
                raise CoreUpdateError(
                    "plan_blocked", "manifest claims private or runtime data"
                )
            _update_target(root, relative)

    def run() -> dict[str, Any]:
        require_unmanaged_target(root)
        require_offline()
        old_raw = read(CORE_MANIFEST_NAME, MAX_MANIFEST)
        old = json.loads(old_raw)
        checked_paths(old)
        # Existing planner accepts a pathname. Freeze its input in an owned
        # runtime control file and use exactly those validated bytes thereafter.
        frozen_path = _update_target(
            root, f"runtime/core-update/archive-{uuid.uuid4().hex}.zip"
        )
        created = False
        try:
            with _PHYSICAL_OPEN(frozen_path, "xb") as stream:
                created = True
                stream.write(archive_raw)
                stream.flush()
                os.fsync(stream.fileno())
            plan = _build_plan(
                root,
                frozen_path,
                workplace_root=workplace_root,
                read_installed=lambda: json.loads(old_raw),
                sha256_owned=physical_digest,
            )
        finally:
            if created:
                frozen_path.unlink(missing_ok=True)
        if plan["blockers"]:
            raise CoreUpdateError("plan_blocked", "core update plan has blockers")
        migration = plan.get("workplace_migration") or {}
        if migration.get("operations"):
            raise CoreUpdateError(
                "plan_blocked", "file update cannot apply Workplace migrations"
            )
        checked_paths(plan["new_manifest"])
        frozen = _freeze_update_archive(archive_raw, plan)
        require_unmanaged_target(root)
        if read(CORE_MANIFEST_NAME, MAX_MANIFEST) != old_raw:
            raise CoreUpdateError(
                "plan_blocked", "installed manifest changed during planning"
            )

        update_id = (
            "core-update-"
            + _update_now().replace(":", "").replace("-", "")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        prefix = f"runtime/core-update/backups/{update_id}"
        backup = _update_target(root, prefix)
        backup.mkdir(parents=True, exist_ok=False)
        paths = sorted(
            set(plan["removed"]) | set(plan["changed"]) | set(plan["restored"])
        )
        writes = sorted(
            set(plan["added"]) | set(plan["changed"]) | set(plan["restored"])
        )
        operations = (
            [{"op": "backup", "path": p} for p in paths]
            + [{"op": "delete", "path": p} for p in plan["removed"]]
            + [{"op": "write", "path": p} for p in writes]
            + [{"op": "write_manifest", "path": CORE_MANIFEST_NAME}]
        )
        progress: dict[str, Any] = dict(
            schema_version=1,
            update_id=update_id,
            status="applying",
            started_at=_update_now(),
            core_root=str(root),
            archive=str(archive_path.resolve()),
            backup_dir=str(backup),
            installed_version=plan["installed_version"],
            target_version=plan["available_version"],
            counts=plan["counts"],
            completed_operations=[],
            pending_operations=operations,
            backed_up={},
            maintenance_mode="file_only",
            archive_sha256=hashlib.sha256(archive_raw).hexdigest(),
        )
        journal = _update_target(root, "runtime/core-update/in-progress.json")

        def complete(op: str, relative: str) -> None:
            progress["completed_operations"].append(
                dict(op=op, path=relative, completed_at=_update_now())
            )
            progress["pending_operations"].remove(dict(op=op, path=relative))
            write_json(journal, progress)

        atomic(_update_target(root, prefix + "/control/old-manifest.json"), old_raw)
        atomic(
            _update_target(root, prefix + "/control/new-manifest.json"), frozen.manifest
        )
        write_json(
            _update_target(root, prefix + "/control/plan.json"),
            {k: v for k, v in plan.items() if k != "new_manifest"},
        )
        write_json(journal, progress)
        try:
            for relative in paths:
                require_unmanaged_target(root)
                target = _update_target(root, relative)
                preimage = read(relative) if target.exists() else None
                if preimage is not None:
                    atomic(
                        _update_target(root, prefix + "/files/" + relative), preimage
                    )
                progress["backed_up"][relative] = (
                    "files/" + relative if preimage is not None else None
                )
                complete("backup", relative)
            for relative in plan["removed"]:
                require_unmanaged_target(root)
                target = _update_target(root, relative)
                target.unlink(missing_ok=True)
                parent = target.parent
                while parent != root:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
                complete("delete", relative)
            for relative in writes:
                require_unmanaged_target(root)
                atomic(_update_target(root, relative), frozen.payload[relative])
                complete("write", relative)
            # Verify every new payload before publishing the new manifest.
            for relative, content in frozen.payload.items():
                if read(relative) != content:
                    raise OSError("installed payload verification failed")
            require_unmanaged_target(root)
            atomic(_update_target(root, CORE_MANIFEST_NAME), frozen.manifest)
            if read(CORE_MANIFEST_NAME, MAX_MANIFEST) != frozen.manifest:
                raise OSError("installed manifest verification failed")
            complete("write_manifest", CORE_MANIFEST_NAME)
            record = dict(
                schema_version=1,
                update_id=update_id,
                status="applied",
                applied_at=_update_now(),
                available_version=plan["available_version"],
                backup_dir=str(backup),
                backed_up=progress["backed_up"],
                counts=plan["counts"],
                workplace_migration=None,
                maintenance_mode="file_only",
                archive_sha256=progress["archive_sha256"],
            )
            write_json(
                _update_target(root, "runtime/core-update/last-apply.json"), record
            )
            journal.unlink()
            return record
        except Exception as error:
            progress.update(
                status="failed",
                failed_at=_update_now(),
                error=dict(code="file_operation_failed", message=str(error)),
            )
            try:
                write_json(journal, progress)
            except OSError:
                pass
            raise _Failure("file_operation_failed", str(error)) from error

    try:
        with registry_file_lock(lock, timeout_seconds=30, stale_after_seconds=0):
            try:
                return run()
            except CoreUpdateError as error:
                raise _Failure(error.code, error.message) from error
    except _Failure as error:
        raise CoreUpdateError(error.code, error.message) from error
    except SystemExit as error:
        raise CoreUpdateError(
            "plan_blocked", "file maintenance exclusion is unavailable"
        ) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CoreUpdateError(
            "plan_blocked", "file update could not qualify its target or archive"
        ) from error
