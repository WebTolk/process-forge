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
from ..configuration.database import DatabaseConfig
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


def _execution_profile(config: DatabaseConfig | None) -> tuple[str, str, int]:
    """Select the exact immutable alias shared by reads, migration and init."""
    profile_id, relative, timeout = "project_main", "data/pf.sqlite3", 100
    if config is not None:
        profile_id = config.defaults.get("project_main", profile_id)
        profile = config.profiles.get(profile_id)
        if profile is not None:
            if profile.scope != "project":
                raise DatabaseError("database_profile_invalid")
            relative, timeout = profile.path, profile.timeout_ms
        elif config.profiles or config.defaults:
            raise DatabaseError("database_profile_invalid")
    return profile_id, relative, timeout


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
    profile_id, relative, timeout = _execution_profile(database_config)
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


def _initialize_fresh_execution_storage(
    project_root: Path,
    workplace_root: Path | None,
    *,
    configuration: ConfigurationProvider,
) -> None:
    """Initialize only inside the acknowledged new-flow admission boundary.

    The host establishes physical fresh-root creation and a qualified native
    tree backend before calling. This function is never a read-path fallback.
    Binding precedes DDL, so interruption leaves an exact blocked route.
    """
    from uuid import uuid4

    from ..database import SqlStatement
    from ..maintenance.execution_migration import EXECUTION_MIGRATION_SCHEMA, _atomic
    from ..maintenance.journal_scan import _exclusive_bytes
    from ..runtime.execution_admission import ExecutionAdmission

    if not ExecutionAdmission.held(project_root, workplace_root):
        raise ExecutionError("execution_storage_not_ready")
    metadata = ProjectMetadataReader(project_root)
    flow = metadata.flow_root()
    owner = metadata.manifest().get("project")
    project_id = owner.get("id") if isinstance(owner, dict) else None
    if not isinstance(project_id, str) or not project_id.strip():
        raise ExecutionError("project_identity_required")
    profile_id, relative, _timeout = _execution_profile(configuration.current().database)
    target = _contained(flow, relative)
    binding_path = _contained(flow, "data/execution-storage.json")
    if binding_path.exists() or target.exists():
        raise ExecutionError("execution_storage_not_ready")
    attempts = _contained(flow, "runtime/agent-runs")
    if attempts.exists() and next(attempts.iterdir(), None) is not None:
        raise ExecutionError("execution_activity_unknown")
    identity = DatabaseIdentity(uuid4().hex, "project", project_id)
    database = DatabaseFactory.from_profile(configuration.current().database, profile_id,
        DatabaseTarget(target, identity))
    binding = {"schema_version": 1, "project_id": project_id,
        "store_id": identity.store_id, "profile_id": profile_id,
        "target_relative_path": relative}
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    marker = _contained(flow, "maintenance/execution-initialization.json")
    marker.parent.mkdir(parents=True, exist_ok=True)
    _exclusive_bytes(marker, (json.dumps({"schema_version": 1, "state": "pending",
        "binding": binding}, sort_keys=True) + "\n").encode())
    _exclusive_bytes(binding_path, (json.dumps(binding, sort_keys=True) + "\n").encode())
    SchemaManager().initialize(database, (EXECUTION_SCHEMA, EXECUTION_MIGRATION_SCHEMA))
    with database.transaction() as session:
        session.execute(SqlStatement(
            "INSERT INTO execution_state(singleton,project_id,generation,authority,readiness,"
            "active_coverage,revision,next_history_seq,migration_id,plan_checksum) "
            "VALUES(1,?,1,'sql','ready','complete',0,1,NULL,NULL)", (project_id,)))
    _atomic(marker, {"schema_version": 1, "state": "ready", "binding": binding})
