"""Manifest-owned archive updates under operator or updater responsibility.

A cooperating updater mutex and a durable recovery journal protect the selected
files. The caller stops PF and its writers before applying or resuming an update.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Any, NoReturn

from .release_sources import ReleaseSourcePolicy
from .update import (
    CORE_MANIFEST_NAME,
    CoreUpdateError,
    _build_plan,
    apply_workplace_migration,
    manifest_file_map,
)


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


def require_update_target(core_root: Path) -> Path:
    """Validate the physical target; old enrollment markers grant no authority."""
    return _target_root(core_root)


def file_update_candidate(core_root: Path) -> bool:
    """Select a separate verified installer for the manifest-owned target."""
    from pf_native_control import current_entry

    entry = current_entry()
    if (
        entry is None
        or entry.control is not None
        or entry.publication is None
        or entry.image is None
    ):
        return False
    root = _target_root(core_root)
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
    resume: bool = False,
    force_local_modifications: bool = False,
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
    root = require_update_target(core_root)
    offline_records: tuple[dict[str, Any], dict[str, Any], bool] | None = None

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
        nonlocal offline_records
        if workplace_root is None:
            return
        from pf_runtime.service import (
            classify_lifecycle,
            lock_path,
            read_json,
            service_path,
        )

        from ..runtime.observation_inputs import WorkerObservationInputService

        # Offline admission uses the shared classifier without endpoint readiness.
        # A stopped service record is not proof that its process is absent.
        state = read_json(service_path(workplace_root))
        lock = read_json(lock_path(workplace_root))
        records = (state, lock, lock_path(workplace_root).exists())
        # The existing Runtime singleton mutex is held throughout this update.
        # An unchanged record whose process was observed absent stays historical:
        # probing its PID again can mistake PID reuse for a restarted Runtime.
        if records == offline_records:
            return
        for pid in (state.get("pid"), lock.get("pid")):
            if isinstance(
                pid, int
            ) and WorkerObservationInputService().process_pid_running(pid):
                raise CoreUpdateError(
                    "plan_blocked", "stop the Workplace App Server before file update"
                )
        kind = classify_lifecycle(
            state,
            lock,
            lock_exists=records[2],
            pid_running=False,
            state_pid_running=False,
            ready=False,
        )
        if kind not in {"stopped", "not_running", "stale"}:
            raise CoreUpdateError(
                "plan_blocked", "stop the Workplace App Server before file update"
            )
        offline_records = records

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

    def checked_paths(
        manifest: dict[str, Any], *, installed_legacy: bool = False
    ) -> None:
        policy = ReleaseSourcePolicy()
        public_pf = {".pf/agents.md", ".pf/process-forge.yaml", ".pf/hooks.yaml"}
        for relative in manifest_file_map(manifest):
            folded = relative.casefold()
            # Older manifests owned these entry templates. Permit their
            # existing backup/removal, never new private target payload.
            legacy_entry = installed_legacy and folded in public_pf
            if (
                folded.startswith("runtime/")
                or (folded.startswith(".pf/") and not legacy_entry)
                or (not legacy_entry and policy.release_path_is_forbidden(folded))
            ):
                raise CoreUpdateError(
                    "plan_blocked", "manifest claims private or runtime data"
                )
            _update_target(root, relative)

    def pin(raw: bytes) -> dict[str, Any]:
        return {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}

    def current(relative: str) -> bytes | None:
        target = _update_target(root, relative)
        try:
            target.lstat()
        except FileNotFoundError:
            return None
        return read(relative)

    def binding() -> dict[str, Any]:
        info = require_update_target(root).stat()
        result: dict[str, Any] = {
            "core_root": str(root),
            "identity": [info.st_dev, info.st_ino],
            "workplace": None,
        }
        if workplace_root is not None:
            workplace = _target_root(workplace_root)
            info = workplace.stat()
            result["workplace"] = {
                "root": str(workplace),
                "identity": [info.st_dev, info.st_ino],
                "manifest": pin(
                    _read_regular(workplace, "workplace.yaml", MAX_MANIFEST)
                ),
            }
        return result

    def refuse() -> NoReturn:
        raise CoreUpdateError(
            "plan_blocked", "file recovery proof or target state differs"
        )

    def resume_inputs() -> tuple[dict[str, Any], dict[str, Any], Any, dict[str, Any]]:
        progress = json.loads(
            read("runtime/core-update/in-progress.json", MAX_MANIFEST)
        )
        if not isinstance(progress, dict):
            refuse()
        if not isinstance(progress.get("completed_operations"), list) or not all(
            isinstance(op, dict) for op in progress["completed_operations"]
        ):
            refuse()
        if (
            not isinstance(progress.get("pending_operations"), list)
            or not isinstance(progress.get("backed_up"), dict)
            or not isinstance(progress.get("failure_history", []), list)
            or not all(
                isinstance(item, dict) for item in progress.get("failure_history", [])
            )
        ):
            refuse()
        update_id = progress["update_id"]
        if (
            not isinstance(update_id, str)
            or not update_id.startswith("core-update-")
            or any(
                c
                not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-."
                for c in update_id
            )
            or progress.get("status") not in {"failed", "applying"}
            or progress.get("maintenance_mode") != "file_only"
            or progress.get("core_root") != str(root)
            or any(
                op.get("op") == "write_manifest"
                for op in progress["completed_operations"]
            )
        ):
            refuse()
        prefix = f"runtime/core-update/backups/{update_id}"
        if progress["backup_dir"] != str(_update_target(root, prefix)):
            refuse()
        proof_raw = read(prefix + "/control/recovery-proof.json", MAX_MANIFEST)
        if progress.get("recovery_evidence") != {"version": 1, **pin(proof_raw)}:
            refuse()
        proof = json.loads(proof_raw)
        if not isinstance(proof, dict):
            refuse()
        if (
            proof["version"] != 1
            or proof["binding"] != binding()
            or proof["update_id"] != update_id
            or proof["archive"] != pin(archive_raw)
            or progress["archive_sha256"] != pin(archive_raw)["sha256"]
        ):
            refuse()
        controls = {}
        for name in ("old-manifest", "new-manifest", "plan"):
            raw = read(prefix + f"/control/{name}.json", MAX_MANIFEST)
            if pin(raw) != proof["controls"][name]:
                refuse()
            controls[name] = raw
        if read(CORE_MANIFEST_NAME, MAX_MANIFEST) != controls["old-manifest"]:
            refuse()
        old, new = (
            json.loads(controls[name]) for name in ("old-manifest", "new-manifest")
        )
        checked_paths(old, installed_legacy=True)
        checked_paths(new)
        plan = json.loads(controls["plan"])
        if not isinstance(plan, dict) or not isinstance(proof["initial"], dict):
            refuse()
        frozen = _freeze_update_archive(archive_raw, {"new_manifest": new})
        if frozen.manifest != controls["new-manifest"]:
            refuse()
        old_files, new_files = manifest_file_map(old), manifest_file_map(new)
        common = old_files.keys() & new_files.keys()
        changed, restored = set(plan["changed"]), set(plan["restored"])
        if (
            plan["blockers"]
            or plan["core_root"] != str(root)
            or plan["added"] != sorted(new_files.keys() - old_files.keys())
            or plan["removed"] != sorted(old_files.keys() - new_files.keys())
            or not changed <= common
            or not restored <= common - changed
            or plan["unchanged"] != sorted(common - changed)
            or any(
                old_files[p]["sha256"] != new_files[p]["sha256"]
                for p in common - changed
            )
        ):
            refuse()
        paths = sorted(set(plan["removed"]) | changed | restored)
        writes = sorted(set(plan["added"]) | changed | restored)
        operations = (
            [{"op": "backup", "path": p} for p in paths]
            + [{"op": "delete", "path": p} for p in plan["removed"]]
            + [{"op": "write", "path": p} for p in writes]
            + [{"op": "write_manifest", "path": CORE_MANIFEST_NAME}]
        )
        completed = [
            {"op": op["op"], "path": op["path"]}
            for op in progress["completed_operations"]
        ]
        if (
            completed + progress["pending_operations"] != operations
            or len(completed) < len(paths)
            or set(progress["backed_up"]) != set(paths)
            or set(proof["initial"]) != set(paths) | set(writes)
        ):
            refuse()
        for relative, initial in proof["initial"].items():
            if relative in plan["added"] and initial is not None:
                refuse()
            if relative in paths:
                saved = progress["backed_up"][relative]
                if initial is None:
                    if saved is not None:
                        refuse()
                elif (
                    saved != "files/" + relative
                    or pin(read(prefix + "/" + saved)) != initial
                ):
                    refuse()
        validate_current(proof, plan, frozen)
        return progress, plan, frozen, proof

    def replaced_by_directory(relative: str, frozen: Any) -> bool:
        if not any(name.startswith(relative + "/") for name in frozen.payload):
            return False
        try:
            info = _update_target(root, relative).lstat()
        except FileNotFoundError:
            return False
        return stat.S_ISDIR(info.st_mode) and not (
            getattr(info, "st_file_attributes", 0) & 0x400
        )

    def validate_current(
        proof: dict[str, Any], plan: dict[str, Any], frozen: Any
    ) -> None:
        require_update_target(root)
        require_offline()
        if proof["binding"] != binding():
            refuse()
        for relative, initial in proof["initial"].items():
            raw = (
                None
                if relative in plan["removed"]
                and replaced_by_directory(relative, frozen)
                else current(relative)
            )
            actual = pin(raw) if raw is not None else None
            intended = (
                pin(frozen.payload[relative]) if relative in frozen.payload else None
            )
            if actual != initial and actual != intended:
                refuse()
        for relative, content in frozen.payload.items():
            if relative not in proof["initial"] and current(relative) != content:
                refuse()

    def run() -> dict[str, Any]:
        require_update_target(root)
        require_offline()
        if resume:
            progress, plan, frozen, proof = resume_inputs()
            return execute(progress, plan, frozen, proof, resuming=True)
        old_raw = read(CORE_MANIFEST_NAME, MAX_MANIFEST)
        old = json.loads(old_raw)
        checked_paths(old, installed_legacy=True)
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
        checked_paths(plan["new_manifest"])
        frozen = _freeze_update_archive(archive_raw, plan)
        require_update_target(root)
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
        progress = dict(
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

        atomic(_update_target(root, prefix + "/control/old-manifest.json"), old_raw)
        atomic(
            _update_target(root, prefix + "/control/new-manifest.json"), frozen.manifest
        )
        write_json(
            _update_target(root, prefix + "/control/plan.json"),
            {k: v for k, v in plan.items() if k != "new_manifest"},
        )
        write_json(journal, progress)
        return execute(progress, plan, frozen, None, resuming=False)

    def execute(
        progress: dict[str, Any],
        plan: dict[str, Any],
        frozen: Any,
        proof: dict[str, Any] | None,
        *,
        resuming: bool,
    ) -> dict[str, Any]:
        prefix = "runtime/core-update/backups/" + progress["update_id"]
        backup = _update_target(root, prefix)
        journal = _update_target(root, "runtime/core-update/in-progress.json")
        paths = sorted(
            set(plan["removed"]) | set(plan["changed"]) | set(plan["restored"])
        )
        writes = sorted(
            set(plan["added"]) | set(plan["changed"]) | set(plan["restored"])
        )

        def complete(op: str, relative: str) -> None:
            item = dict(op=op, path=relative)
            if item in progress["pending_operations"]:
                progress["completed_operations"].append(
                    {**item, "completed_at": _update_now()}
                )
                progress["pending_operations"].remove(item)
                write_json(journal, progress)

        try:
            if resuming:
                # Retain the exact prior journal, including the original failure.
                receipt = _update_target(
                    root, prefix + f"/control/resume-{uuid.uuid4().hex}.json"
                )
                with _PHYSICAL_OPEN(receipt, "xb") as stream:
                    stream.write(
                        read("runtime/core-update/in-progress.json", MAX_MANIFEST)
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
            initial: dict[str, Any] = {}
            for relative in [] if resuming else paths:
                require_update_target(root)
                preimage = current(relative)
                if preimage is not None:
                    atomic(
                        _update_target(root, prefix + "/files/" + relative), preimage
                    )
                    if read(prefix + "/files/" + relative) != preimage:
                        raise OSError("backup verification failed")
                progress["backed_up"][relative] = (
                    "files/" + relative if preimage is not None else None
                )
                initial[relative] = pin(preimage) if preimage is not None else None
                complete("backup", relative)
            if not resuming:
                for relative in plan["added"]:
                    if current(relative) is not None:
                        refuse()
                    initial[relative] = None
                proof = {
                    "version": 1,
                    "update_id": progress["update_id"],
                    "binding": binding(),
                    "archive": pin(archive_raw),
                    "initial": initial,
                    "controls": {
                        name: pin(read(prefix + f"/control/{name}.json", MAX_MANIFEST))
                        for name in ("old-manifest", "new-manifest", "plan")
                    },
                }
                proof_path = _update_target(
                    root, prefix + "/control/recovery-proof.json"
                )
                write_json(proof_path, proof)
                progress["recovery_evidence"] = {
                    "version": 1,
                    **pin(read(prefix + "/control/recovery-proof.json", MAX_MANIFEST)),
                }
                write_json(journal, progress)
            assert proof is not None
            validate_current(proof, plan, frozen)
            for relative in plan["removed"]:
                require_update_target(root)
                require_offline()
                if proof["binding"] != binding():
                    refuse()
                if replaced_by_directory(relative, frozen):
                    complete("delete", relative)
                    continue
                raw = current(relative)
                if raw is not None and pin(raw) != proof["initial"][relative]:
                    refuse()
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
                require_update_target(root)
                require_offline()
                if proof["binding"] != binding():
                    refuse()
                raw = current(relative)
                if raw != frozen.payload[relative]:
                    if (pin(raw) if raw is not None else None) != proof["initial"][
                        relative
                    ]:
                        refuse()
                    atomic(_update_target(root, relative), frozen.payload[relative])
                complete("write", relative)
            # Verify every new payload before publishing the new manifest.
            for relative, content in frozen.payload.items():
                if read(relative) != content:
                    raise OSError("installed payload verification failed")
            require_update_target(root)
            require_offline()
            if (
                read(CORE_MANIFEST_NAME, MAX_MANIFEST)
                != read(prefix + "/control/old-manifest.json", MAX_MANIFEST)
                or proof["binding"] != binding()
            ):
                refuse()
            for relative in plan["removed"]:
                if (
                    not replaced_by_directory(relative, frozen)
                    and current(relative) is not None
                ):
                    refuse()
            atomic(_update_target(root, CORE_MANIFEST_NAME), frozen.manifest)
            if read(CORE_MANIFEST_NAME, MAX_MANIFEST) != frozen.manifest:
                raise OSError("installed manifest verification failed")
            complete("write_manifest", CORE_MANIFEST_NAME)
            migration = plan.get("workplace_migration") or {}
            migration_record = None
            if migration.get("operations"):
                require_offline()
                if workplace_root is None or proof["binding"] != binding():
                    refuse()
                # Supplemental Workplace files use the same frozen archive.
                # Journal/SQL migration remains an explicit, separate operation.
                migration_record = apply_workplace_migration(
                    io.BytesIO(archive_raw), workplace_root, migration, backup
                )
            record = dict(
                schema_version=1,
                update_id=progress["update_id"],
                status="applied",
                applied_at=_update_now(),
                available_version=plan["available_version"],
                backup_dir=str(backup),
                backed_up=progress["backed_up"],
                counts=plan["counts"],
                workplace_migration=migration_record,
                maintenance_mode="file_only",
                archive_sha256=progress["archive_sha256"],
                recovery_evidence=progress["recovery_evidence"],
                failure_history=progress.get("failure_history", []),
                resumed=resuming,
            )
            write_json(
                _update_target(root, "runtime/core-update/last-apply.json"), record
            )
            journal.unlink()
            return record
        except Exception as error:
            message = (
                error.message
                if isinstance(error, CoreUpdateError)
                else "file update operation failed"
            )
            failure = dict(
                code=getattr(error, "code", "file_operation_failed"),
                message=message,
                errno=getattr(error, "errno", None),
                winerror=getattr(error, "winerror", None),
            )
            progress.setdefault("failure_history", []).append(
                {"failed_at": _update_now(), **failure}
            )
            progress.update(
                status="failed",
                failed_at=_update_now(),
                error=failure,
            )
            try:
                write_json(journal, progress)
            except OSError as cleanup:
                error.add_note(f"journal publication failed: {type(cleanup).__name__}")
            raise _Failure(str(failure["code"]), message) from error

    try:
        with registry_file_lock(lock, timeout_seconds=30, stale_after_seconds=0):
            with ExitStack() as lifecycle:
                try:
                    if workplace_root is not None:
                        from pf_runtime.service import lock_path

                        workplace_root = _target_root(workplace_root)
                        runtime_lock = lock_path(workplace_root)
                        for path in (
                            runtime_lock,
                            runtime_lock.with_name(f".{runtime_lock.name}.lock"),
                            runtime_lock.with_name(f".{runtime_lock.name}.lock.guard"),
                        ):
                            _update_target(
                                workplace_root,
                                path.relative_to(workplace_root).as_posix(),
                            )
                            try:
                                info = path.lstat()
                            except FileNotFoundError:
                                continue
                            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                                raise CoreUpdateError(
                                    "plan_blocked",
                                    "Runtime singleton lock is not regular",
                                )
                        lifecycle.enter_context(
                            registry_file_lock(
                                runtime_lock,
                                timeout_seconds=30,
                                stale_after_seconds=0,
                            )
                        )
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
