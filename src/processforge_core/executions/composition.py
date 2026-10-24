"""Explicit, noncreating selection of project execution storage.

Binding is routing evidence only. SQL owns readiness and execution facts. A
bound but unavailable store must never fall back to a status-file projection.
"""

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from ..configuration import ConfigurationProvider
from ..database import (
    Database,
    DatabaseError,
    DatabaseFactory,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaManager,
)
from ..project.configuration_inputs import ProjectConfigurationReader
from ..project.metadata import ProjectMetadataReader
from .model import ExecutionError
from .schema import EXECUTION_SCHEMA
from .sqlite_repository import SQLiteExecutionRepository


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _contained(root: Path, relative: str) -> Path:
    """Reject traversal, aliases and reparse points before any target open."""
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    if (
        not relative
        or "\x00" in relative
        or "\\" in relative
        or posix.is_absolute()
        or windows.drive
        or any(part in {".", ".."} for part in relative.split("/"))
    ):
        raise ExecutionError("execution_storage_not_ready")
    target = root.joinpath(*posix.parts)
    for path in (target, *target.parents):
        try:
            info = path.lstat()
        except FileNotFoundError:
            pass
        else:
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise ExecutionError("execution_storage_not_ready")
        if path == root:
            break
    else:
        raise ExecutionError("execution_storage_not_ready")
    return target


@dataclass(frozen=True)
class ExecutionStorage:
    """Operation-local route; construction alone performs no I/O."""

    authority: str
    repository: SQLiteExecutionRepository | None = None


def select_execution_storage(
    project_root: Path,
    workplace_root: Path | None = None,
    *,
    configuration: ConfigurationProvider | None = None,
    deadline: float | None = None,
) -> ExecutionStorage:
    """Read exact binding/profile/envelope; create no files, DDL or services.

    No binding and no execution namespace selects compatibility mode. An
    unbound execution namespace, corrupt store or changed profile refuses.
    The returned repository validates SQL readiness on each operation.
    """
    metadata = ProjectMetadataReader(project_root)
    flow = metadata.flow_root()
    provider = configuration or ProjectConfigurationReader().configuration_provider(
        project_root, workplace_root
    )
    config = provider.current()
    database_config = config.database
    profile_id = "project_main"
    relative = "data/pf.sqlite3"
    timeout = 100
    if database_config is not None:
        profile_id = database_config.defaults.get("project_main", profile_id)
        profile = database_config.profiles.get(profile_id)
        if profile is not None:
            if profile.scope != "project":
                raise DatabaseError("database_profile_invalid")
            relative, timeout = profile.path, profile.timeout_ms
        elif database_config.profiles or database_config.defaults:
            raise DatabaseError("database_profile_invalid")
    target = _contained(flow, relative)
    binding_path = _contained(flow, "data/execution-storage.json")
    try:
        with binding_path.open("rb") as stream:
            raw = stream.read(65537)
    except FileNotFoundError:
        binding = None
    else:
        try:
            if len(raw) > 65536:
                raise ValueError("oversize binding")
            binding = json.loads(raw, object_pairs_hook=_pairs)
            if (
                not isinstance(binding, dict)
                or set(binding)
                != {
                    "schema_version",
                    "project_id",
                    "store_id",
                    "profile_id",
                    "target_relative_path",
                }
                or type(binding["schema_version"]) is not int
                or binding["schema_version"] != 1
                or binding["profile_id"] != profile_id
                or binding["target_relative_path"] != relative
            ):
                raise ValueError("invalid binding")
        except (ValueError, TypeError):
            raise ExecutionError("execution_storage_not_ready") from None
    if binding is None and not target.exists():
        return ExecutionStorage("legacy")
    manifest = metadata.manifest()
    project = manifest.get("project")
    project_id = project.get("id") if isinstance(project, dict) else None
    if not isinstance(project_id, str) or not project_id.strip():
        raise ExecutionError("project_identity_required")
    if binding is not None and binding["project_id"] != project_id:
        raise ExecutionError("execution_identity_conflict")
    identity = DatabaseIdentity(
        None if binding is None else binding["store_id"], "project", project_id
    )
    database = Database(
        DatabaseFactory.resolve_driver(database_config),
        DatabaseTarget(target, identity),
        timeout_ms=timeout,
    )
    if binding is None:
        status = SchemaManager().inspect(database, ())
        if status.state != "ready" or any(
            item[0] == "execution" for item in status.versions
        ):
            raise ExecutionError("execution_storage_not_ready")
        return ExecutionStorage("legacy")
    repository = SQLiteExecutionRepository(database, project_id)
    # A deadline-bounded guard calls current directly: it validates namespace,
    # singleton and current rows in one SQL snapshot, without redundant inspect.
    if deadline is None:
        if SchemaManager().inspect(database, (EXECUTION_SCHEMA,)).state != "ready":
            raise ExecutionError("execution_storage_not_ready")
        if not repository.readiness().ready:
            raise ExecutionError("execution_storage_not_ready")
    return ExecutionStorage("sql", repository)
