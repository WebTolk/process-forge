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
WORKPLACE_MIGRATION_KIND = "processforge.workplace_migration"


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


def load_yaml_bytes(content: bytes, *, source: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise CoreUpdateError("yaml_support_missing", "PyYAML is required for Workplace migration") from exc
    try:
        data = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:  # type: ignore[attr-defined]
        raise CoreUpdateError("workplace_migration_invalid", f"invalid YAML in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise CoreUpdateError("workplace_migration_invalid", f"migration document must be a mapping: {source}")
    return data


def dump_yaml_bytes(data: dict[str, Any]) -> bytes:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise CoreUpdateError("yaml_support_missing", "PyYAML is required for Workplace migration") from exc
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")


def load_archive_workplace_migration(archive_path: Path, *, installed_version: str | None, target_version: str) -> tuple[str | None, dict[str, Any] | None]:
    """Select the one declared Workplace migration applicable to this Core plan."""
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for name in sorted(archive.namelist()):
                if not name.startswith("updates/migrations/") or not name.endswith((".yaml", ".yml")):
                    continue
                migration = load_yaml_bytes(archive.read(name), source=name)
                if migration.get("kind") != WORKPLACE_MIGRATION_KIND:
                    continue
                if str(migration.get("to_version") or "") != target_version:
                    continue
                versions = migration.get("from_versions")
                allowed = {str(value) for value in versions} if isinstance(versions, list) else set()
                if installed_version not in allowed and not (installed_version is None and migration.get("allow_unmanaged_installed_core") is True):
                    continue
                return name, migration
    except zipfile.BadZipFile as exc:
        raise CoreUpdateError("archive_invalid", f"invalid ZIP archive: {archive_path}") from exc
    return None, None


def workplace_target(workplace_root: Path, relative_path: str) -> Path:
    return ensure_inside(workplace_root, safe_relative_path(relative_path))


def read_archive_member(archive: zipfile.ZipFile, relative_path: str) -> bytes:
    """Read an apply-time archive member as a structured update error."""
    try:
        return archive.read(relative_path)
    except KeyError as exc:
        raise CoreUpdateError("archive_file_missing", f"archive file missing: {relative_path}") from exc
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise CoreUpdateError("archive_read_failed", f"archive member read failed: {relative_path}: {exc}") from exc


def workplace_migration_plan(core_root: Path, archive_path: Path, *, installed_version: str | None, target_version: str, workplace_root: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "not_requested",
        "workplace_root": str(workplace_root.resolve()) if workplace_root else None,
        "migration": None,
        "operations": [],
        "preserved": [],
        "blockers": [],
    }
    if workplace_root is None:
        return result
    workplace_root = workplace_root.resolve()
    if not (workplace_root / "workplace.yaml").is_file():
        result.update({"status": "blocked", "blockers": [{"code": "workplace_manifest_missing", "path": str(workplace_root / "workplace.yaml")} ]})
        return result
    source_path, migration = load_archive_workplace_migration(
        archive_path, installed_version=installed_version, target_version=target_version
    )
    if migration is None:
        result["status"] = "not_applicable"
        return result
    migration_id = str(migration.get("id") or "")
    operations = migration.get("operations")
    if not migration_id or not isinstance(operations, list):
        raise CoreUpdateError("workplace_migration_invalid", f"migration {source_path} requires id and operations")
    result.update({"status": "planned", "migration": {"id": migration_id, "source": source_path}})
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive_members = {info.filename: info for info in archive.infolist()}
    except zipfile.BadZipFile as exc:
        raise CoreUpdateError("archive_invalid", f"invalid ZIP archive: {archive_path}") from exc
    for item in operations:
        if not isinstance(item, dict):
            raise CoreUpdateError("workplace_migration_invalid", f"migration {migration_id} contains a non-object operation")
        operation_id = str(item.get("id") or "")
        operation_type = str(item.get("type") or "")
        target_path = str(item.get("target") or "")
        if not operation_id or not target_path:
            raise CoreUpdateError("workplace_migration_invalid", f"migration {migration_id} operation requires id and target")
        target = workplace_target(workplace_root, target_path)
        if operation_type == "copy_if_missing":
            raw_source = item.get("source")
            if isinstance(raw_source, str) and raw_source.endswith("/"):
                source_info = archive_members.get(raw_source)
                if source_info is not None and source_info.is_dir():
                    result["blockers"].append(
                        {
                            "code": "workplace_migration_source_directory",
                            "migration": migration_id,
                            "operation": operation_id,
                            "source": raw_source,
                        }
                    )
                    continue
            try:
                source = safe_relative_path(raw_source)
            except CoreUpdateError as exc:
                result["blockers"].append(
                    {
                        "code": "workplace_migration_source_invalid",
                        "migration": migration_id,
                        "operation": operation_id,
                        "source": raw_source if isinstance(raw_source, str) else None,
                        "reason": exc.code,
                    }
                )
                continue
            source_info = archive_members.get(source)
            if source_info is None:
                result["blockers"].append(
                    {
                        "code": "workplace_migration_source_missing",
                        "migration": migration_id,
                        "operation": operation_id,
                        "source": source,
                    }
                )
                continue
            if source_info.is_dir():
                result["blockers"].append(
                    {
                        "code": "workplace_migration_source_directory",
                        "migration": migration_id,
                        "operation": operation_id,
                        "source": source,
                    }
                )
                continue
            if target.exists():
                result["preserved"].append({"id": operation_id, "path": target_path, "reason": "existing_file"})
            else:
                result["operations"].append({"id": operation_id, "type": operation_type, "source": source, "target": target_path})
            continue
        if operation_type == "append_registry_entry_if_missing":
            list_key = str(item.get("list_key") or "")
            match_key = str(item.get("match_key") or "id")
            entry = item.get("entry")
            if not list_key or not isinstance(entry, dict) or not entry.get(match_key):
                raise CoreUpdateError("workplace_migration_invalid", f"migration {migration_id} registry operation {operation_id} is invalid")
            data = load_yaml_bytes(target.read_bytes(), source=target_path) if target.is_file() else {"schema_version": 1}
            current = data.get(list_key)
            if current is None:
                current = []
            if not isinstance(current, list):
                raise CoreUpdateError("workplace_migration_invalid", f"registry list is invalid: {target_path}:{list_key}")
            if any(isinstance(row, dict) and row.get(match_key) == entry[match_key] for row in current):
                result["preserved"].append({"id": operation_id, "path": target_path, "reason": "existing_registry_entry", "value": entry[match_key]})
            else:
                result["operations"].append({"id": operation_id, "type": operation_type, "target": target_path, "list_key": list_key, "entry": entry})
            continue
        raise CoreUpdateError("workplace_migration_invalid", f"unsupported migration operation: {operation_type}")
    if result["blockers"]:
        result["status"] = "blocked"
    return result


def backup_workplace_target(workplace_root: Path, backup_dir: Path, relative_path: str) -> dict[str, Any]:
    source = workplace_target(workplace_root, relative_path)
    record: dict[str, Any] = {"path": relative_path, "existed": source.is_file()}
    if source.is_file():
        target = backup_dir / "workplace" / "files" / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        record["backup"] = str(target.relative_to(backup_dir).as_posix())
    return record


def apply_workplace_migration(archive_path: Path, workplace_root: Path, migration_plan: dict[str, Any], backup_dir: Path) -> dict[str, Any]:
    operations = migration_plan.get("operations") if isinstance(migration_plan.get("operations"), list) else []
    backed_up: list[dict[str, Any]] = []
    record = {
        "schema_version": 1, "status": "applying",
        "migration": migration_plan.get("migration"),
        "operations": operations, "preserved": migration_plan.get("preserved", []),
        "backed_up": backed_up,
    }
    with zipfile.ZipFile(archive_path) as archive:
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            target_path = str(operation["target"])
            backed_up.append(backup_workplace_target(workplace_root, backup_dir, target_path))
            # Preserve recovery evidence before each mutation, including when
            # a subsequent archive member disappears or cannot be decoded.
            atomic_write(backup_dir / "workplace-migration.json", (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            target = workplace_target(workplace_root, target_path)
            if operation["type"] == "copy_if_missing":
                atomic_write(target, read_archive_member(archive, str(operation["source"])))
            elif operation["type"] == "append_registry_entry_if_missing":
                data = load_yaml_bytes(target.read_bytes(), source=target_path) if target.is_file() else {"schema_version": 1}
                values = data.get(str(operation["list_key"]))
                if not isinstance(values, list):
                    values = []
                    data[str(operation["list_key"])] = values
                values.append(operation["entry"])
                atomic_write(target, dump_yaml_bytes(data))
    record = {
        "schema_version": 1,
        "status": "applied",
        "migration": migration_plan.get("migration"),
        "applied_at": now_utc(),
        "operations": operations,
        "preserved": migration_plan.get("preserved", []),
        "backed_up": backed_up,
    }
    write_json(backup_dir / "workplace-migration.json", record)
    return record


def installed_manifest(core_root: Path) -> dict[str, Any] | None:
    path = manifest_path(core_root)
    return read_manifest(path) if path.is_file() else None


def unowned_path_blocker(
    core_root: Path,
    relative_path: str,
    *,
    removable_owned_paths: set[str] | frozenset[str] = frozenset(),
) -> dict[str, str] | None:
    """Return a blocker when an added payload would replace an unowned path.

    ``Path.exists()`` does not report broken symlinks, and resolving a path
    through a non-directory ancestor can defer the failure until apply has
    already created update state.  Inspect the lexical path first so all
    existing objects, including symlinks, are protected before any mutation.
    """
    target = core_root / relative_path
    if os.path.lexists(target):
        return {"code": "unowned_path_collision", "path": relative_path, "conflict_path": relative_path}

    ancestor = target.parent
    while ancestor != core_root:
        if os.path.lexists(ancestor) and (ancestor.is_symlink() or not ancestor.is_dir()):
            conflict_path = ancestor.relative_to(core_root).as_posix()
            if (
                conflict_path in removable_owned_paths
                and ancestor.is_file()
                and not ancestor.is_symlink()
            ):
                ancestor = ancestor.parent
                continue
            return {"code": "unowned_path_collision", "path": relative_path, "conflict_path": conflict_path}
        ancestor = ancestor.parent
    return None


def build_plan(core_root: Path, archive_path: Path, *, workplace_root: Path | None = None) -> dict[str, Any]:
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
    blockers = []
    for relative_path in sorted(old_paths):
        target = core_root / relative_path
        if target.is_symlink() or (os.path.lexists(target) and not target.is_file()):
            blockers.append({"code": "nonregular_owned_path", "path": relative_path})
            continue
        if not target.exists():
            missing_owned.append(relative_path)
            collision = unowned_path_blocker(core_root, relative_path)
            if collision:
                blockers.append(collision)
            continue
        target = ensure_inside(core_root, relative_path)
        if sha256_file(target) != old_files[relative_path]["sha256"]:
            locally_modified.append(relative_path)
    restored = sorted(set(missing_owned).intersection(unchanged))
    for relative_path in sorted(set(locally_modified).intersection(set(removed).union(changed))):
        blockers.append({"code": "locally_modified", "path": relative_path})
    for relative_path in added:
        collision = unowned_path_blocker(core_root, relative_path, removable_owned_paths=set(removed))
        if collision is not None:
            blockers.append(collision)
    incomplete = (runtime_root(core_root) / "in-progress.json").is_file()
    if incomplete:
        blockers.append({"code": "incomplete_update", "path": str(runtime_root(core_root) / "in-progress.json")})
    migration = workplace_migration_plan(
        core_root,
        archive_path,
        installed_version=old_manifest.get("version") if old_manifest else None,
        target_version=str(new_manifest.get("version") or ""),
        workplace_root=workplace_root,
    )
    blockers.extend(migration.get("blockers", []))
    return {
        "schema_version": 1,
        "kind": "processforge.core_update.plan",
        "status": "blocked" if blockers else "planned",
        "core_root": str(core_root),
        "archive": str(archive_path),
        "installed_manifest": str(manifest_path(core_root)) if old_manifest else None,
        "installed_version": old_manifest.get("version") if old_manifest else None,
        "available_version": new_manifest.get("version"),
        "counts": {"added": len(added), "removed": len(removed), "changed": len(changed), "unchanged": len(unchanged), "locally_modified": len(locally_modified), "missing_owned": len(missing_owned), "restored": len(restored)},
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "locally_modified": locally_modified,
        "missing_owned": missing_owned,
        "restored": restored,
        "blockers": blockers,
        "workplace_migration": migration,
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


def apply_update(
    core_root: Path,
    archive_path: Path,
    *,
    confirm: bool = False,
    force_local_modifications: bool = False,
    workplace_root: Path | None = None,
) -> dict[str, Any]:
    if not confirm:
        raise CoreUpdateError("confirm_required", "core update apply requires explicit confirmation")
    plan = build_plan(core_root, archive_path, workplace_root=workplace_root)
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
    missing_unchanged = set(plan["restored"])
    backup_paths = set(plan["removed"]).union(plan["changed"]).union(missing_unchanged)
    for relative_path in sorted(backup_paths):
        pending_operations.append({"op": "backup", "path": relative_path})
    for relative_path in plan["removed"]:
        pending_operations.append({"op": "delete", "path": relative_path})
    write_paths = set(plan["added"]).union(plan["changed"]).union(missing_unchanged)
    for relative_path in sorted(write_paths):
        pending_operations.append({"op": "write", "path": relative_path})
    migration = plan.get("workplace_migration") if isinstance(plan.get("workplace_migration"), dict) else {}
    if migration.get("status") == "planned" and migration.get("operations"):
        pending_operations.append({"op": "workplace_migration", "path": str(migration.get("migration", {}).get("id") or "workplace")})
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

    def record_failure(code: str, message: str) -> None:
        failure = {
            **progress,
            "schema_version": 1,
            "update_id": update_id,
            "status": "failed",
            "failed_at": now_utc(),
            "backup_dir": str(backup_dir),
            "error": {"code": code, "message": message},
        }
        try:
            write_json(in_progress_path, failure)
        except OSError:
            pass

    old_manifest = installed_manifest(core_root)
    if old_manifest:
        write_json(backup_dir / "control" / "old-manifest.json", old_manifest)
    write_json(backup_dir / "control" / "new-manifest.json", plan["new_manifest"])
    write_json(backup_dir / "control" / "plan.json", {key: value for key, value in plan.items() if key != "new_manifest"})
    write_json(in_progress_path, progress)
    try:
        migration_record = None
        if migration.get("status") == "planned" and migration.get("operations"):
            if workplace_root is None:
                raise CoreUpdateError("workplace_root_missing", "Workplace migration was planned without a Workplace root")
            migration_record = apply_workplace_migration(archive_path, workplace_root.resolve(), migration, backup_dir)
            complete_operation("workplace_migration", str(migration.get("migration", {}).get("id") or "workplace"))
        for relative_path in sorted(backup_paths):
            backed_up[relative_path] = backup_file(core_root, backup_dir, relative_path)
            complete_operation("backup", relative_path)
        for relative_path in plan["removed"]:
            target = ensure_inside(core_root, relative_path)
            if target.exists():
                target.unlink()
                prune_empty_parents(core_root, relative_path)
            complete_operation("delete", relative_path)
        with zipfile.ZipFile(archive_path) as archive:
            for relative_path in sorted(write_paths):
                content = read_archive_member(archive, relative_path)
                atomic_write(ensure_inside(core_root, relative_path), content)
                complete_operation("write", relative_path)
        atomic_write(manifest_path(core_root), manifest_bytes(plan["new_manifest"]))
        complete_operation("write_manifest", CORE_MANIFEST_NAME)
        record = {"schema_version": 1, "update_id": update_id, "status": "applied", "applied_at": now_utc(), "available_version": plan["available_version"], "backup_dir": str(backup_dir), "backed_up": backed_up, "counts": plan["counts"], "workplace_migration": migration_record}
        last_apply = work_root / "last-apply.json"
        write_json(last_apply, record)
        in_progress_path.unlink(missing_ok=True)
        return record
    except CoreUpdateError as exc:
        record_failure(exc.code, exc.message)
        raise
    except zipfile.BadZipFile as exc:
        record_failure("archive_invalid", f"invalid ZIP archive: {archive_path}")
        raise CoreUpdateError("archive_invalid", f"invalid ZIP archive: {archive_path}") from exc
    except OSError as exc:
        record_failure("file_operation_failed", str(exc))
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
