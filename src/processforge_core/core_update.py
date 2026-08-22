"""Manifest-based ProcessForge core update primitives.

The service is intentionally file-system scoped.  It does not discover update
servers or workplace registries; callers provide an explicit core root and,
for update operations, an explicit release archive.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CORE_MANIFEST_NAME = "processforge-core.manifest.json"
CORE_MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CoreUpdateError(Exception):
    code: str
    message: str


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise CoreUpdateError("invalid_manifest_path", "manifest path is empty")
    value = raw.replace("\\", "/")
    if value != raw:
        raise CoreUpdateError("invalid_manifest_path", f"manifest path contains backslash: {raw}")
    if value.startswith("/") or value.startswith("//") or (len(value) > 1 and value[1] == ":"):
        raise CoreUpdateError("invalid_manifest_path", f"manifest path is absolute: {raw}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CoreUpdateError("invalid_manifest_path", f"manifest path escapes or is not normalized: {raw}")
    if value == CORE_MANIFEST_NAME:
        raise CoreUpdateError("invalid_manifest_path", f"{CORE_MANIFEST_NAME} is a control file, not an owned payload file")
    return value


def ensure_inside(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    target = (root / relative_path).resolve()
    if root_resolved != target and root_resolved not in target.parents:
        raise CoreUpdateError("path_outside_core_root", f"path escapes core root: {relative_path}")
    return target


def manifest_path(core_root: Path) -> Path:
    return core_root / CORE_MANIFEST_NAME


def runtime_root(core_root: Path) -> Path:
    return core_root / "runtime" / "core-update"


def manifest_file_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if manifest.get("schema_version") != CORE_MANIFEST_SCHEMA_VERSION:
        raise CoreUpdateError("invalid_core_manifest", "core manifest schema_version must be 1")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise CoreUpdateError("invalid_core_manifest", "core manifest files must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict):
            raise CoreUpdateError("invalid_core_manifest", "core manifest file entry must be an object")
        relative_path = safe_relative_path(item.get("relative_path") or item.get("path"))
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise CoreUpdateError("invalid_core_manifest", f"invalid sha256 for {relative_path}")
        result[relative_path] = {**item, "relative_path": relative_path, "sha256": digest.lower()}
    return result


def make_core_manifest(*, version: str, source: dict[str, Any] | None, files: Iterable[dict[str, Any]], generated_at: str | None = None) -> dict[str, Any]:
    normalized_files = []
    for item in files:
        relative_path = safe_relative_path(item.get("relative_path") or item.get("path"))
        normalized_files.append(
            {
                "relative_path": relative_path,
                "size": int(item.get("size") or 0),
                "sha256": str(item.get("sha256") or "").lower(),
            }
        )
    normalized_files.sort(key=lambda row: row["relative_path"])
    manifest = {
        "schema_version": CORE_MANIFEST_SCHEMA_VERSION,
        "kind": "processforge.core_manifest",
        "version": version,
        "generated_at": generated_at or now_utc(),
        "source": source or {},
        "files": normalized_files,
    }
    manifest_file_map(manifest)
    return manifest


def make_core_manifest_from_release_files(files: list[tuple[str, Path]], *, version: str, source: dict[str, Any] | None, generated_at: str | None = None) -> dict[str, Any]:
    entries = []
    for archive_path, source_path in files:
        if archive_path == CORE_MANIFEST_NAME:
            continue
        entries.append({"relative_path": archive_path, "size": source_path.stat().st_size, "sha256": sha256_file(source_path)})
    return make_core_manifest(version=version, source=source, files=entries, generated_at=generated_at)


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CoreUpdateError("manifest_missing", f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CoreUpdateError("manifest_invalid_json", f"invalid manifest JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CoreUpdateError("invalid_core_manifest", "core manifest must be an object")
    manifest_file_map(data)
    return data


def read_archive_manifest(archive_path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            try:
                raw = archive.read(CORE_MANIFEST_NAME)
            except KeyError as exc:
                raise CoreUpdateError("archive_manifest_missing", f"archive does not contain {CORE_MANIFEST_NAME}") from exc
    except zipfile.BadZipFile as exc:
        raise CoreUpdateError("archive_invalid", f"invalid ZIP archive: {archive_path}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoreUpdateError("archive_manifest_invalid", f"archive manifest is invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CoreUpdateError("invalid_core_manifest", "archive core manifest must be an object")
    manifest_file_map(data)
    return data


def validate_archive_payload(archive_path: Path, manifest: dict[str, Any]) -> None:
    new_files = manifest_file_map(manifest)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            for relative_path, entry in new_files.items():
                if relative_path not in names:
                    raise CoreUpdateError("archive_file_missing", f"archive file missing: {relative_path}")
                actual = sha256_bytes(archive.read(relative_path))
                if actual != entry["sha256"]:
                    raise CoreUpdateError("archive_checksum_mismatch", f"archive file sha256 mismatch: {relative_path}")
            for name in names:
                if name.endswith("/"):
                    continue
                if name == CORE_MANIFEST_NAME:
                    continue
                safe_relative_path(name)
    except zipfile.BadZipFile as exc:
        raise CoreUpdateError("archive_invalid", f"invalid ZIP archive: {archive_path}") from exc


def installed_manifest(core_root: Path) -> dict[str, Any] | None:
    path = manifest_path(core_root)
    return read_manifest(path) if path.is_file() else None


def build_plan(core_root: Path, archive_path: Path) -> dict[str, Any]:
    core_root = core_root.resolve()
    archive_path = archive_path.resolve()
    new_manifest = read_archive_manifest(archive_path)
    validate_archive_payload(archive_path, new_manifest)
    old_manifest = installed_manifest(core_root)
    old_files = manifest_file_map(old_manifest) if old_manifest else {}
    new_files = manifest_file_map(new_manifest)
    old_paths = set(old_files)
    new_paths = set(new_files)
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    common = old_paths & new_paths
    changed = sorted(path for path in common if old_files[path]["sha256"] != new_files[path]["sha256"])
    unchanged = sorted(path for path in common if old_files[path]["sha256"] == new_files[path]["sha256"])
    locally_modified = []
    missing_owned = []
    for relative_path in sorted(old_paths):
        target = ensure_inside(core_root, relative_path)
        if not target.exists():
            missing_owned.append(relative_path)
            continue
        if target.is_file() and sha256_file(target) != old_files[relative_path]["sha256"]:
            locally_modified.append(relative_path)
    blockers = []
    for relative_path in sorted(set(locally_modified).intersection(set(removed).union(changed))):
        blockers.append({"code": "locally_modified", "path": relative_path})
    incomplete = (runtime_root(core_root) / "in-progress.json").is_file()
    if incomplete:
        blockers.append({"code": "incomplete_update", "path": str(runtime_root(core_root) / "in-progress.json")})
    return {
        "schema_version": 1,
        "kind": "processforge.core_update.plan",
        "status": "blocked" if blockers else "planned",
        "core_root": str(core_root),
        "archive": str(archive_path),
        "installed_manifest": str(manifest_path(core_root)) if old_manifest else None,
        "installed_version": old_manifest.get("version") if old_manifest else None,
        "available_version": new_manifest.get("version"),
        "counts": {"added": len(added), "removed": len(removed), "changed": len(changed), "unchanged": len(unchanged), "locally_modified": len(locally_modified), "missing_owned": len(missing_owned)},
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "locally_modified": locally_modified,
        "missing_owned": missing_owned,
        "blockers": blockers,
        "new_manifest": new_manifest,
    }


def core_status(core_root: Path) -> dict[str, Any]:
    core_root = core_root.resolve()
    manifest = installed_manifest(core_root)
    incomplete_path = runtime_root(core_root) / "in-progress.json"
    payload = {
        "schema_version": 1,
        "kind": "processforge.core_update.status",
        "core_root": str(core_root),
        "status": "installed" if manifest else "not_installed",
        "manifest": str(manifest_path(core_root)),
        "version": manifest.get("version") if manifest else None,
        "file_count": len(manifest_file_map(manifest)) if manifest else 0,
        "incomplete_update": incomplete_path.is_file(),
    }
    if incomplete_path.is_file():
        try:
            payload["in_progress"] = json.loads(incomplete_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload["in_progress"] = {"status": "unreadable"}
    return payload


def backup_file(core_root: Path, backup_dir: Path, relative_path: str) -> str | None:
    source = ensure_inside(core_root, relative_path)
    if not source.is_file():
        return None
    target = backup_dir / "files" / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target.relative_to(backup_dir).as_posix())


def prune_empty_parents(core_root: Path, relative_path: str) -> None:
    root = core_root.resolve()
    parent = ensure_inside(root, relative_path).parent
    while parent != root and root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def atomic_write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".pf-update-tmp")
    with temporary.open("wb") as handle:
        handle.write(content)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass
    os.replace(temporary, target)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_update(core_root: Path, archive_path: Path, *, confirm: bool = False, force_local_modifications: bool = False) -> dict[str, Any]:
    if not confirm:
        raise CoreUpdateError("confirm_required", "core update apply requires explicit confirmation")
    plan = build_plan(core_root, archive_path)
    blockers = [item for item in plan["blockers"] if item.get("code") != "locally_modified" or not force_local_modifications]
    if blockers:
        raise CoreUpdateError("plan_blocked", "core update plan has blockers")
    update_id = "core-update-" + now_utc().replace(":", "").replace("-", "")
    work_root = runtime_root(core_root)
    backup_dir = work_root / "backups" / update_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    in_progress_path = work_root / "in-progress.json"
    in_progress_path.parent.mkdir(parents=True, exist_ok=True)
    backed_up: dict[str, str | None] = {}
    pending_operations: list[dict[str, str]] = []
    for relative_path in sorted(set(plan["removed"]).union(plan["changed"])):
        pending_operations.append({"op": "backup", "path": relative_path})
    for relative_path in plan["removed"]:
        pending_operations.append({"op": "delete", "path": relative_path})
    for relative_path in sorted(set(plan["added"]).union(plan["changed"])):
        pending_operations.append({"op": "write", "path": relative_path})
    pending_operations.append({"op": "write_manifest", "path": CORE_MANIFEST_NAME})
    progress = {
        "schema_version": 1,
        "update_id": update_id,
        "status": "applying",
        "started_at": now_utc(),
        "core_root": str(core_root.resolve()),
        "archive": str(archive_path.resolve()),
        "backup_dir": str(backup_dir),
        "installed_version": plan.get("installed_version"),
        "target_version": plan.get("available_version"),
        "counts": plan.get("counts"),
        "completed_operations": [],
        "pending_operations": pending_operations,
        "backed_up": backed_up,
    }

    def complete_operation(op: str, relative_path: str) -> None:
        completed = progress["completed_operations"]
        pending = progress["pending_operations"]
        assert isinstance(completed, list)
        assert isinstance(pending, list)
        completed.append({"op": op, "path": relative_path, "completed_at": now_utc()})
        for index, item in enumerate(list(pending)):
            if isinstance(item, dict) and item.get("op") == op and item.get("path") == relative_path:
                del pending[index]
                break
        write_json(in_progress_path, progress)

    old_manifest = installed_manifest(core_root)
    if old_manifest:
        write_json(backup_dir / "control" / "old-manifest.json", old_manifest)
    write_json(backup_dir / "control" / "new-manifest.json", plan["new_manifest"])
    write_json(in_progress_path, progress)
    try:
        for relative_path in sorted(set(plan["removed"]).union(plan["changed"])):
            backed_up[relative_path] = backup_file(core_root, backup_dir, relative_path)
            complete_operation("backup", relative_path)
        for relative_path in plan["removed"]:
            target = ensure_inside(core_root, relative_path)
            if target.exists():
                target.unlink()
                prune_empty_parents(core_root, relative_path)
            complete_operation("delete", relative_path)
        with zipfile.ZipFile(archive_path) as archive:
            for relative_path in sorted(set(plan["added"]).union(plan["changed"])):
                content = archive.read(relative_path)
                atomic_write(ensure_inside(core_root, relative_path), content)
                complete_operation("write", relative_path)
        atomic_write(manifest_path(core_root), manifest_bytes(plan["new_manifest"]))
        complete_operation("write_manifest", CORE_MANIFEST_NAME)
        record = {"schema_version": 1, "update_id": update_id, "status": "applied", "applied_at": now_utc(), "available_version": plan["available_version"], "backup_dir": str(backup_dir), "backed_up": backed_up, "counts": plan["counts"]}
        last_apply = work_root / "last-apply.json"
        write_json(last_apply, record)
        in_progress_path.unlink(missing_ok=True)
        return record
    except CoreUpdateError:
        raise
    except OSError as exc:
        try:
            failure = {
                **progress,
                "schema_version": 1,
                "update_id": update_id,
                "status": "failed",
                "failed_at": now_utc(),
                "backup_dir": str(backup_dir),
                "error": {"code": "file_operation_failed", "message": str(exc)},
            }
            write_json(in_progress_path, failure)
        except OSError:
            pass
        raise CoreUpdateError("file_operation_failed", str(exc)) from exc


def recovery_assessment(in_progress: dict[str, Any]) -> str:
    status = str(in_progress.get("status") or "")
    if status not in {"failed", "applying"}:
        return "manual_repair_required"
    completed = in_progress.get("completed_operations")
    if not isinstance(completed, list):
        return "manual_repair_required"
    manifest_written = any(isinstance(item, dict) and item.get("op") == "write_manifest" for item in completed)
    if manifest_written:
        return "manual_repair_required"
    raw_backup_dir = str(in_progress.get("backup_dir") or "")
    backup_dir = Path(raw_backup_dir) if raw_backup_dir else None
    if status == "failed" and backup_dir is not None and backup_dir.is_dir() and (backup_dir / "control" / "old-manifest.json").is_file():
        return "safe_to_rollback"
    return "manual_repair_required"


def repair_status(core_root: Path) -> dict[str, Any]:
    status = core_status(core_root)
    if not status.get("incomplete_update"):
        return {"schema_version": 1, "kind": "processforge.core_update.repair", "status": "nothing_to_repair", "core_root": str(core_root.resolve())}
    in_progress = status.get("in_progress") if isinstance(status.get("in_progress"), dict) else {}
    assessment = recovery_assessment(in_progress)
    return {
        "schema_version": 1,
        "kind": "processforge.core_update.repair",
        "status": assessment,
        "core_root": str(core_root.resolve()),
        "in_progress": in_progress,
    }
