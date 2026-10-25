"""Native, fenced UUID adoption; execution authority stays with its own engine.

No discovery, connection, configuration read or UUID mint happens on import or
construction. Hosts supply exact targets and actual ownership exclusion proof.
Legacy application IDs and domain objects are never rewritten by this module.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import stat
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, closing, contextmanager
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import uuid4

from ..database import (
    STORE_ENVELOPE_DDL,
    DatabaseFactory,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaDefinition,
    SchemaManager,
    SQLiteDriver,
)
from ..database.contracts import Database
from ..database.errors import DatabaseError
from ..executions.model import ExecutionError
from ..executions.projection import canonical_json
from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import ExecutionAdmission
from .contracts import (
    BackupPort,
    ExecutionMigrationContext,
    JsonObject,
    MaintenanceError,
    MigrationSafety,
    StorageMigrationContext,
    StoreTarget,
)
from .execution_migration import ExecutionMigrationService, _atomic, _hash, _read
from .journal_scan import _check_links, _exclusive_bytes

MIGRATION_ID = "r02-storage-v1"
STORE_IDENTITY_SCHEMA = SchemaDefinition(
    "store_identity",
    1,
    STORE_ENVELOPE_DDL,
    _hash(
        {"namespace": "store_identity", "version": 1, "statements": STORE_ENVELOPE_DDL}
    ),
)
_META = frozenset({"pf_store_meta", "pf_schema_versions"})
_KINDS = frozenset({"events", "raw", "accounting", "search", "main"})
_STATES = frozenset({"planned", "backed_up", "importing", "verified", "ready"})


def _deadline(deadline: float | None) -> None:
    if deadline is not None and (
        not math.isfinite(deadline) or time.monotonic() >= deadline
    ):
        raise MaintenanceError("storage_deadline_exceeded")


def _uuid(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise MaintenanceError("storage_identity_conflict")
    return value


def _safe(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise MaintenanceError("storage_path_unsafe")
    _check_links(path, "storage_path_unsafe")
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise MaintenanceError("storage_path_unsafe")
    return path


def storage_owner_root(context: StorageMigrationContext, target: StoreTarget) -> Path:
    """Resolve only the host-selected owner, with no enrollment fallback."""
    if target.scope == "project" and context.project_root is not None:
        return _safe(ProjectMetadataReader(_safe(context.project_root)).flow_root())
    if target.scope == "workplace" and context.workplace_root is not None:
        return _safe(context.workplace_root)
    raise MaintenanceError("storage_owner_scope_required")


def validate_storage_context(
    context: StorageMigrationContext,
) -> tuple[StoreTarget, ...]:
    """Validate containment, explicit project identity, aliases and target order."""
    _safe(context.device_config_path)
    if context.project_root is None and context.workplace_root is None:
        raise MaintenanceError("storage_root_required")
    project_id = None
    if context.project_root is not None:
        project = _safe(context.project_root)
        metadata = ProjectMetadataReader(project)
        _safe(metadata.flow_root() / "process-forge.yaml")
        owner = metadata.manifest().get("project")
        project_id = owner.get("id") if isinstance(owner, dict) else None
        if (
            not isinstance(project_id, str)
            or not project_id.strip()
            or "\x00" in project_id
        ):
            raise MaintenanceError("project_identity_required")
    if context.workplace_root is not None:
        _safe(context.workplace_root)
    expected_unqualified = {
        "raw": "runtime/agent-events/hooks.sqlite3",
        "search": "runtime/search/local-resource-search.sqlite",
        "accounting": "data/accounting/accounting.sqlite3",
    }
    for kind, path in context.unqualified_targets:
        if (
            context.workplace_root is None
            or kind not in expected_unqualified
            or _safe(path) != context.workplace_root / expected_unqualified[kind]
        ):
            raise MaintenanceError("storage_targets_invalid")
    if type(context.targets) is not tuple or len(context.targets) > 128:
        raise MaintenanceError("storage_targets_invalid")
    paths: set[Path] = set()
    physical: set[tuple[int, int]] = set()
    for target in context.targets:
        if target.kind not in _KINDS or target.scope not in {"project", "workplace"}:
            raise MaintenanceError("storage_target_invalid")
        root = storage_owner_root(context, target)
        relative = PurePosixPath(target.target_relative_path)
        if (
            not target.target_relative_path
            or relative.is_absolute()
            or relative.as_posix() != target.target_relative_path
            or any(p in {".", ".."} for p in relative.parts)
            or "\\" in target.target_relative_path
            or ":" in target.target_relative_path
        ):
            raise MaintenanceError("storage_path_unsafe")
        path = _safe(target.target)
        if root / relative != path or path == root or path in paths:
            raise MaintenanceError("storage_target_alias")
        paths.add(path)
        if path.exists():
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise MaintenanceError("storage_path_unsafe")
            identity = (info.st_dev, info.st_ino)
            if identity in physical:
                raise MaintenanceError("storage_target_alias")
            physical.add(identity)
        if not target.owner_id.strip() or "\x00" in target.owner_id:
            raise MaintenanceError("owner_identity_required")
        if target.scope == "project" and target.owner_id != project_id:
            raise MaintenanceError("storage_owner_conflict")
        if target.kind == "main" and target.scope != "project":
            raise MaintenanceError("storage_main_scope_invalid")
        if target.kind == "accounting":
            source = _safe(root / "data/accounting/identity.json")
            if not source.exists() or _read(source).get("origin_id") != target.owner_id:
                raise MaintenanceError("owner_identity_required")
    return tuple(
        sorted(
            context.targets,
            key=lambda t: (
                t.scope.encode(),
                t.owner_id.encode(),
                t.target_relative_path.encode("utf-8"),
            ),
        )
    )


def storage_identity_gate(root: Path) -> Path:
    """One owner gate serializes slot publication as well as adapter lifetimes."""
    return _safe(root) / "runtime/storage-identity"


def _pins(root: Path) -> JsonObject:
    path = _safe(root / "data/storage-identities.json")
    result = _read(path) if path.exists() else {"schema_version": 1, "slots": []}
    if (
        set(result) != {"schema_version", "slots"}
        or type(result["schema_version"]) is not int
        or result["schema_version"] != 1
    ):
        raise MaintenanceError("storage_pin_invalid")
    slots = result["slots"]
    if not isinstance(slots, list) or len(slots) > 128:
        raise MaintenanceError("storage_pin_invalid")
    paths, ids = set(), set()
    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {
            "kind",
            "target_relative_path",
            "store_id",
            "scope",
            "owner_id",
            "state",
            "plan_checksum",
        }:
            raise MaintenanceError("storage_pin_invalid")
        _uuid(slot["store_id"])
        if (
            slot["kind"] not in _KINDS - {"main"}
            or slot["scope"] not in {"project", "workplace"}
            or slot["state"] not in {"pending", "ready"}
            or not isinstance(slot["owner_id"], str)
            or not slot["owner_id"].strip()
            or not _checksum(slot["plan_checksum"])
        ):
            raise MaintenanceError("storage_pin_invalid")
        relative = slot["target_relative_path"]
        if (
            not isinstance(relative, str)
            or relative in paths
            or slot["store_id"] in ids
        ):
            raise MaintenanceError("storage_identity_conflict")
        p = PurePosixPath(relative)
        if (
            p.is_absolute()
            or p.as_posix() != relative
            or not p.parts
            or any(v in {".", ".."} for v in p.parts)
            or "\\" in relative
            or ":" in relative
        ):
            raise MaintenanceError("storage_pin_invalid")
        paths.add(relative)
        ids.add(slot["store_id"])
    return result


def _checksum(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(c in "0123456789abcdef" for c in value[7:])
    )


def _slot(root: Path, target: StoreTarget) -> JsonObject | None:
    for slot in _pins(root)["slots"]:
        if slot["target_relative_path"] == target.target_relative_path:
            if any(
                slot[k] != getattr(target, k) for k in ("kind", "scope", "owner_id")
            ):
                raise MaintenanceError("storage_identity_conflict")
            return dict(slot)
    return None


def _publish_pin(
    root: Path, target: StoreTarget, store_id: str, checksum: str, state: str
) -> None:
    pins = _pins(root)
    old = _slot(root, target)
    slot = {
        "kind": target.kind,
        "target_relative_path": target.target_relative_path,
        "store_id": _uuid(store_id),
        "scope": target.scope,
        "owner_id": target.owner_id,
        "state": state,
        "plan_checksum": checksum,
    }
    if old is not None and any(old[k] != slot[k] for k in slot if k != "state"):
        raise MaintenanceError("storage_pin_conflict")
    if old is not None and old["state"] == "ready" and state != "ready":
        raise MaintenanceError("storage_pin_conflict")
    pins["slots"] = [
        s
        for s in pins["slots"]
        if s["target_relative_path"] != target.target_relative_path
    ] + [slot]
    pins["slots"].sort(key=lambda s: s["target_relative_path"].encode("utf-8"))
    if len({s["store_id"] for s in pins["slots"]}) != len(pins["slots"]):
        raise MaintenanceError("storage_identity_conflict")
    path = root / "data/storage-identities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic(path, pins)


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def storage_schema_facts(
    connection: sqlite3.Connection, *, metadata: bool = False
) -> list[JsonObject]:
    """Bounded exact objects, SQL/constraints/index/FTS shadow qualification."""
    rows = connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name"
    ).fetchmany(257)
    if len(rows) > 256:
        raise MaintenanceError("storage_schema_unrecognized")
    facts = []
    for kind, name, table, sql in rows:
        if (table in _META) != metadata:
            continue
        fact: JsonObject = {"type": kind, "name": name, "table": table, "sql": sql}
        if kind == "table":
            fact["columns"] = [
                list(row)
                for row in connection.execute(
                    "PRAGMA table_xinfo(" + _quote(name) + ")"
                )
            ]
            fact["foreign_keys"] = [
                list(row)
                for row in connection.execute(
                    "PRAGMA foreign_key_list(" + _quote(name) + ")"
                )
            ]
        if kind == "index":
            fact["index"] = [
                list(row)
                for row in connection.execute(
                    "PRAGMA index_xinfo(" + _quote(name) + ")"
                )
            ]
        facts.append(fact)
    return facts


def _value(value: object) -> object:
    if isinstance(value, bytes):
        return ["blob", value.hex()]
    if isinstance(value, float):
        return ["real", value.hex()]
    return [type(value).__name__, value]


def _parity(connection: sqlite3.Connection, deadline: float | None) -> JsonObject:
    result: JsonObject = {}
    for fact in storage_schema_facts(connection):
        if fact["type"] != "table":
            continue
        name = fact["name"]
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_xinfo(" + _quote(name) + ")")
            if row[6] != 1
        ]
        selection = ",".join(_quote(c) for c in columns)
        digest, count = hashlib.sha256(), 0
        with closing(
            connection.execute(
                "SELECT "
                + selection
                + " FROM "
                + _quote(name)
                + " ORDER BY "
                + selection
            )
        ) as cursor:
            while rows := cursor.fetchmany(128):
                _deadline(deadline)
                for row in rows:
                    raw = canonical_json([_value(v) for v in row]).encode("utf-8")
                    digest.update(len(raw).to_bytes(8, "big"))
                    digest.update(raw)
                    count += 1
        result[name] = {"count": count, "sha256": "sha256:" + digest.hexdigest()}
    return result


@contextmanager
def _connection(
    path: Path,
    driver: SQLiteDriver,
    *,
    writable: bool = False,
    deadline: float | None = None,
) -> Iterator[sqlite3.Connection]:
    _deadline(deadline)
    path = _safe(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise MaintenanceError("storage_path_unsafe")
    for suffix in ("-wal", "-shm", "-journal"):
        member = _safe(path.with_name(path.name + suffix))
        if member.exists() and not member.is_file():
            raise MaintenanceError("storage_path_unsafe")
    timeout = (
        0.1 if deadline is None else min(0.1, max(0.0, deadline - time.monotonic()))
    )
    with closing(
        driver._connect(
            path.as_uri() + ("?mode=rw" if writable else "?mode=ro"),
            uri=True,
            timeout=timeout,
            isolation_level=None,
        )
    ) as connection:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA foreign_keys=ON")
        if not writable:
            connection.execute("PRAGMA query_only=ON")
        connection.set_progress_handler(
            lambda: int(deadline is not None and time.monotonic() >= deadline), 1000
        )
        try:
            yield connection
            after = _safe(path).stat()
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise MaintenanceError("storage_target_changed")
            _deadline(deadline)
        finally:
            if connection.in_transaction:
                connection.rollback()


def _descriptor(*, verify_transforms: bool = True) -> JsonObject:
    root = Path(__file__).absolute().parents[3]
    descriptor = _read(root / "schemas/storage-migration-v1.json")
    paths = (
        "src/processforge_core/maintenance/contracts.py",
        "src/processforge_core/maintenance/storage_migration.py",
        "src/processforge_core/maintenance/backup.py",
        "src/processforge_core/maintenance/execution_migration.py",
        "src/processforge_core/maintenance/journal_scan.py",
        "src/processforge_core/executions/schema.py",
        "src/processforge_core/executions/sqlite_repository.py",
        "schemas/execution-migration-v1.json",
    )
    files = (
        [
            {
                "relative_path": p,
                "sha256": "sha256:"
                + hashlib.sha256((root / p).read_bytes()).hexdigest(),
            }
            for p in paths
        ]
        if verify_transforms
        else descriptor.get("transform_files")
    )
    if (
        descriptor.get("migration_id") != MIGRATION_ID
        or descriptor.get("descriptor_version") != 1
        or descriptor.get("transform_files") != files
        or descriptor.get("transform_checksum") != _hash(files)
        or descriptor.get("identity_schema_checksum") != STORE_IDENTITY_SCHEMA.checksum
    ):
        raise MaintenanceError("storage_transform_changed")
    return descriptor


def _legacy_facts(
    connection: sqlite3.Connection,
    target: StoreTarget,
    descriptor: JsonObject,
    *,
    parity: bool,
    deadline: float | None,
) -> JsonObject:
    expected = descriptor["legacy_formats"].get(target.kind)
    if not isinstance(expected, dict):
        raise MaintenanceError("storage_schema_unrecognized")
    actual = {
        "application_id": connection.execute("PRAGMA application_id").fetchone()[0],
        "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
        "schema_checksum": _hash(storage_schema_facts(connection)),
    }
    if actual != expected:
        raise MaintenanceError("storage_schema_unrecognized")
    if target.kind in {"events", "raw"} and connection.execute(
        "SELECT value FROM journal_metadata WHERE key='migration_state'"
    ).fetchone() != ("ready",):
        raise MaintenanceError("journal_migration_incomplete")
    if target.kind == "search" and connection.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone() != ("6",):
        raise MaintenanceError("storage_schema_unrecognized")
    meta = storage_schema_facts(connection, metadata=True)
    identity = None
    if meta:
        if _hash(meta) != descriptor["metadata_schema_checksum"]:
            raise MaintenanceError("storage_identity_conflict")
        rows = connection.execute(
            "SELECT singleton,store_id,scope,owner_id,format_version FROM pf_store_meta"
        ).fetchmany(2)
        versions = connection.execute(
            "SELECT namespace,version,checksum FROM pf_schema_versions"
        ).fetchmany(2)
        if (
            len(rows) != 1
            or rows[0][0] != 1
            or rows[0][2:] != (target.scope, target.owner_id, 1)
            or versions != [("store_identity", 1, STORE_IDENTITY_SCHEMA.checksum)]
        ):
            raise MaintenanceError("storage_identity_conflict")
        identity = _uuid(rows[0][1])
    facts: JsonObject = {**actual, "store_id": identity}
    if parity:
        if (
            connection.execute("PRAGMA integrity_check").fetchmany(2) != [("ok",)]
            or connection.execute("PRAGMA foreign_key_check").fetchone() is not None
        ):
            raise MaintenanceError("storage_integrity_failed")
        facts["parity"] = _parity(connection, deadline)
    return facts


def _inspect_target(
    target: StoreTarget,
    descriptor: JsonObject,
    driver: SQLiteDriver,
    *,
    parity: bool = False,
    deadline: float | None = None,
) -> JsonObject:
    _safe(target.target)
    if not target.target.exists():
        return {"state": "absent"}
    if target.kind == "main":
        database = Database(
            driver,
            DatabaseTarget(
                target.target, DatabaseIdentity(None, target.scope, target.owner_id)
            ),
        )
        status = SchemaManager().inspect(database, ())
        if status.identity is None or status.state not in {
            "ready",
            "migration_required",
        }:
            raise MaintenanceError("storage_main_unsupported")
        return {
            "state": "main",
            "store_id": status.identity.store_id,
            "versions": [list(v) for v in status.versions],
        }
    with _connection(target.target, driver, deadline=deadline) as connection:
        connection.execute("BEGIN")
        return {
            "state": "legacy",
            **_legacy_facts(
                connection, target, descriptor, parity=parity, deadline=deadline
            ),
        }


@contextmanager
def storage_identity_access(
    context: StorageMigrationContext,
    target: StoreTarget,
    *,
    registry_lock: Callable[..., AbstractContextManager[object]],
    driver: SQLiteDriver | None = None,
    deadline: float | None = None,
) -> Iterator[str | None]:
    """Hold an adapter's owner gate from before open until after connection close.

    Unadopted legacy returns None and performs no migration. Pending always
    refuses. Hosts call ensure_ready BEFORE taking this gate or task/SQL locks.
    Main is routed exclusively by execution composition and is not accepted here.
    """
    if target not in validate_storage_context(context) or target.kind == "main":
        raise MaintenanceError("storage_target_invalid")
    root = storage_owner_root(context, target)
    _deadline(deadline)
    timeout = 30.0 if deadline is None else max(0.001, deadline - time.monotonic())
    with registry_lock(
        storage_identity_gate(root), timeout_seconds=timeout, stale_after_seconds=0
    ):
        _deadline(deadline)
        slot = _slot(root, target)
        if slot is not None and slot["state"] != "ready":
            raise MaintenanceError("storage_resume_required")
        if slot is None:
            # Bounded envelope detection only; legacy adapters retain all their
            # original schema/refusal checks. Unpinned metadata is never adopted.
            if target.target.exists():
                with _connection(
                    target.target,
                    driver or DatabaseFactory.resolve_driver(),
                    deadline=deadline,
                ) as connection:
                    if connection.execute(
                        "SELECT 1 FROM sqlite_schema WHERE name IN ('pf_store_meta','pf_schema_versions') LIMIT 1"
                    ).fetchone():
                        raise MaintenanceError("storage_pin_missing")
            yield None
        else:
            descriptor = _descriptor(verify_transforms=False)
            facts = _inspect_target(
                target,
                descriptor,
                driver or DatabaseFactory.resolve_driver(),
                deadline=deadline,
            )
            if facts.get("store_id") != slot["store_id"]:
                raise MaintenanceError("storage_identity_conflict")
            yield str(slot["store_id"])


class StorageMigrationService:
    """One native coordinator for update/first-write/resume, using BackupPort.

    Safety is a private trusted host callback for exact context. It must recheck
    capability/installed bytes, exclusion, routing/instance, gaps and whole trees;
    a flag, version, empty registry or PID probe cannot stand in for that proof.
    """

    def __init__(
        self,
        *,
        backup: BackupPort,
        admission: ExecutionAdmission,
        registry_lock: Callable[..., AbstractContextManager[object]],
        safety: Callable[[StorageMigrationContext], MigrationSafety],
        execution: ExecutionMigrationService | None = None,
        driver: SQLiteDriver | None = None,
        execution_factory: Callable[
            [StorageMigrationContext, StoreTarget], ExecutionMigrationService
        ]
        | None = None,
    ) -> None:
        self.backup, self.admission, self.registry_lock = (
            backup,
            admission,
            registry_lock,
        )
        self.safety, self.execution = safety, execution
        self.driver = driver if driver is not None else DatabaseFactory.resolve_driver()
        self.execution_factory = execution_factory

    @contextmanager
    def _admit(
        self, context: StorageMigrationContext, deadline: float | None
    ) -> Iterator[None]:
        _deadline(deadline)
        if context.project_root is not None:
            with self.admission.start(
                context.project_root, context.workplace_root, deadline=deadline
            ):
                yield
        elif context.workplace_root is not None:
            timeout = (
                30.0 if deadline is None else max(0.001, deadline - time.monotonic())
            )
            with self.registry_lock(
                context.workplace_root / "runtime/pf-runtime/execution-admission",
                timeout_seconds=timeout,
                stale_after_seconds=0,
            ):
                _deadline(deadline)
                yield
        else:
            raise MaintenanceError("storage_root_required")

    @contextmanager
    def _gate(self, root: Path, deadline: float | None) -> Iterator[None]:
        _deadline(deadline)
        timeout = 30.0 if deadline is None else max(0.001, deadline - time.monotonic())
        with self.registry_lock(
            storage_identity_gate(root), timeout_seconds=timeout, stale_after_seconds=0
        ):
            _deadline(deadline)
            yield

    def _proof(
        self, context: StorageMigrationContext, expected: str | None = None
    ) -> MigrationSafety:
        try:
            proof = self.safety(context)
        except Exception:
            raise MaintenanceError("storage_safety_unavailable") from None
        if not isinstance(proof, MigrationSafety) or proof.state not in {
            "proven",
            "active",
            "unknown",
        }:
            raise MaintenanceError("storage_safety_unavailable")
        if proof.state == "proven" and (
            not isinstance(proof.generation, str)
            or not proof.generation.strip()
            or type(proof.evidence) is not tuple
            or not proof.evidence
            or any(not isinstance(e, str) or not e.strip() for e in proof.evidence)
        ):
            raise MaintenanceError("storage_safety_unavailable")
        if expected is not None and (
            proof.state != "proven" or proof.generation != expected
        ):
            raise MaintenanceError("storage_safety_changed")
        return proof

    @staticmethod
    def _report(operation: str) -> JsonObject:
        return {
            "schema_version": 1,
            "operation": operation,
            "status": "planned",
            "blocked": False,
            "phase": "planned",
            "retryable": False,
            "per_target_counts": {
                "ready": 0,
                "absent": 0,
                "pending": 0,
                "legacy": 0,
                "deferred": 0,
            },
            "targets": [],
            "error": None,
            "evidence": [],
        }

    def _unqualified(
        self, context: StorageMigrationContext, descriptor: JsonObject
    ) -> list[JsonObject]:
        """Recognize old layouts without inventing a durable workplace owner."""
        results: list[JsonObject] = []
        if context.workplace_root is None:
            return results
        pins = _pins(context.workplace_root)
        for kind, path in context.unqualified_targets:
            relative = path.relative_to(context.workplace_root).as_posix()
            if any(
                slot.get("target_relative_path") == relative for slot in pins["slots"]
            ):
                raise MaintenanceError("owner_identity_required")
            target = StoreTarget(kind, path, relative, "workplace", "unqualified")
            facts = _inspect_target(target, descriptor, self.driver)
            if facts.get("store_id") is not None:
                raise MaintenanceError("owner_identity_required")
            results.append(
                {
                    "kind": kind,
                    "scope": "workplace",
                    "target_relative_path": relative,
                    "state": "deferred",
                    "legacy_allowed": True,
                    "reason": "owner_identity_required",
                }
            )
        return results

    @staticmethod
    def _failure(report: JsonObject, error: BaseException) -> JsonObject:
        code = (
            error.code
            if isinstance(error, (MaintenanceError, DatabaseError, ExecutionError))
            else "storage_operation_failed"
        )
        report.update(
            status="failed",
            blocked=True,
            error={"code": code},
            retryable=code
            in {
                "storage_deadline_exceeded",
                "storage_safety_changed",
                "storage_safety_unavailable",
                "storage_activity_unknown",
                "database_busy",
                "execution_activity_unknown",
            },
        )
        return report

    def inspect(self, context: StorageMigrationContext) -> JsonObject:
        """Read only; never mint, publish, lock, scan history or create evidence."""
        report = self._report("storage-inspect")
        try:
            targets, descriptor = validate_storage_context(context), _descriptor()
            for result in self._unqualified(context, descriptor):
                report["targets"].append(result)
                report["per_target_counts"]["deferred"] += 1
            for target in targets:
                root = storage_owner_root(context, target)
                if target.kind == "main":
                    facts = _inspect_target(target, descriptor, self.driver)
                    state = "main" if facts["state"] == "main" else "absent"
                else:
                    slot = _slot(root, target)
                    if slot is not None and slot["state"] == "pending":
                        state = "pending"
                    else:
                        facts = _inspect_target(target, descriptor, self.driver)
                        state = "absent" if facts["state"] == "absent" else "legacy"
                        if slot is not None:
                            if facts.get("store_id") != slot["store_id"]:
                                raise MaintenanceError("storage_identity_conflict")
                            state = "ready"
                        elif facts.get("store_id") is not None:
                            raise MaintenanceError("storage_pin_missing")
                report["targets"].append(
                    {
                        "kind": target.kind,
                        "scope": target.scope,
                        "target_relative_path": target.target_relative_path,
                        "state": state,
                    }
                )
                if state in report["per_target_counts"]:
                    report["per_target_counts"][state] += 1
            if any(t["state"] == "pending" for t in report["targets"]):
                report.update(
                    blocked=True,
                    error={"code": "storage_resume_required"},
                    retryable=True,
                )
            return report
        except (
            MaintenanceError,
            DatabaseError,
            ExecutionError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            sqlite3.Error,
            SystemExit,
        ) as error:
            return self._failure(report, error)

    def ensure_ready(
        self,
        context: StorageMigrationContext,
        *,
        trigger: Literal["update", "first_write"],
        deadline: float | None = None,
    ) -> JsonObject:
        """Synchronously migrate proven idle targets; automatically resume pins."""
        if trigger not in {"update", "first_write"}:
            return self._failure(
                self._report("storage-ensure"),
                MaintenanceError("storage_trigger_invalid"),
            )
        return self._run(context, "storage-" + trigger, deadline)

    def resume(
        self, context: StorageMigrationContext, *, deadline: float | None = None
    ) -> JsonObject:
        """Resume only exact plans selected by pending pins, never newest journal."""
        return self._run(context, "storage-resume", deadline)

    def _run(
        self, context: StorageMigrationContext, operation: str, deadline: float | None
    ) -> JsonObject:
        report = self._report(operation)
        try:
            targets, descriptor = validate_storage_context(context), _descriptor()
            for result in self._unqualified(context, descriptor):
                report["targets"].append(result)
                report["per_target_counts"]["deferred"] += 1
                report.update(
                    status="failed",
                    blocked=True,
                    retryable=True,
                    error={"code": "owner_identity_required"},
                )
            for target in targets:
                _deadline(deadline)
                report["phase"] = target.kind
                if target.kind == "main":
                    result = self._execution(context, target, deadline)
                else:
                    result = self._target(context, target, descriptor, deadline)
                report["targets"].append(
                    {
                        "kind": target.kind,
                        "scope": target.scope,
                        "target_relative_path": target.target_relative_path,
                        **result,
                    }
                )
                report["per_target_counts"][result["state"]] += 1
                if result["state"] == "deferred":
                    report.update(
                        status="failed",
                        blocked=True,
                        retryable=True,
                        error={"code": "storage_activity_unknown"},
                    )
            if not report["blocked"]:
                report.update(status="ready", phase="ready")
            return report
        except (
            MaintenanceError,
            DatabaseError,
            ExecutionError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            sqlite3.Error,
            SystemExit,
        ) as error:
            return self._failure(report, error)

    @staticmethod
    def _journal(root: Path, checksum: str) -> Path:
        if not _checksum(checksum):
            raise MaintenanceError("storage_plan_invalid")
        return _safe(root / "data/storage-migrations" / MIGRATION_ID / checksum[7:])

    def _plan(
        self,
        context: StorageMigrationContext,
        target: StoreTarget,
        descriptor: JsonObject,
        root: Path,
        proof: MigrationSafety,
        facts: JsonObject,
    ) -> JsonObject:
        selector = self._selector(root, target)
        if selector.exists():
            plan = _read(selector)
            self._check_plan(plan, target, descriptor)
            if plan["source"] != facts or plan["safety_generation"] != proof.generation:
                raise MaintenanceError("storage_source_changed")
        else:
            plan = {
                "schema_version": 1,
                "migration_id": MIGRATION_ID,
                "mode": "existing",
                "descriptor_checksum": _hash(descriptor),
                "kind": target.kind,
                "scope": target.scope,
                "owner_id": target.owner_id,
                "target_relative_path": target.target_relative_path,
                "store_id": uuid4().hex,
                "source_generation": 0,
                "target_generation": 1,
                "safety_generation": proof.generation,
                "source": facts,
            }
            plan["plan_checksum"] = _hash(plan)
            selector.parent.mkdir(parents=True, exist_ok=True)
            _exclusive_bytes(selector, (canonical_json(plan) + "\n").encode())
        directory = self._journal(root, plan["plan_checksum"])
        directory.mkdir(parents=True, exist_ok=True)
        _exclusive_bytes(
            directory / "plan.json", (canonical_json(plan) + "\n").encode()
        )
        if not (directory / "journal.json").exists():
            _atomic(
                directory / "journal.json",
                {
                    "plan_checksum": plan["plan_checksum"],
                    "store_id": plan["store_id"],
                    "state": "planned",
                    "backup_manifest_checksum": None,
                },
            )
        return plan

    @staticmethod
    def _selector(root: Path, target: StoreTarget) -> Path:
        key = _hash(
            {
                "kind": target.kind,
                "scope": target.scope,
                "owner_id": target.owner_id,
                "target_relative_path": target.target_relative_path,
            }
        )
        return _safe(
            root
            / "data/storage-migrations"
            / MIGRATION_ID
            / "targets"
            / (key[7:] + ".json")
        )

    @staticmethod
    def _check_plan(
        plan: JsonObject, target: StoreTarget, descriptor: JsonObject
    ) -> None:
        checksum = plan.get("plan_checksum")
        if checksum != _hash({k: v for k, v in plan.items() if k != "plan_checksum"}):
            raise MaintenanceError("storage_plan_changed")
        _uuid(plan.get("store_id"))
        if (
            plan.get("migration_id") != MIGRATION_ID
            or plan.get("descriptor_checksum") != _hash(descriptor)
            or plan.get("source_generation") != 0
            or plan.get("target_generation") != 1
            or any(
                plan.get(k) != getattr(target, k)
                for k in ("kind", "scope", "owner_id", "target_relative_path")
            )
        ):
            raise MaintenanceError("storage_plan_changed")

    def _load(
        self, root: Path, slot: JsonObject, target: StoreTarget, descriptor: JsonObject
    ) -> JsonObject:
        directory = self._journal(root, slot["plan_checksum"])
        plan = _read(directory / "plan.json")
        checksum = plan.pop("plan_checksum", None)
        if checksum != _hash(plan) or checksum != slot["plan_checksum"]:
            raise MaintenanceError("storage_plan_changed")
        plan["plan_checksum"] = checksum
        self._check_plan(plan, target, descriptor)
        if (
            plan.get("migration_id") != MIGRATION_ID
            or plan.get("descriptor_checksum") != _hash(descriptor)
            or plan.get("store_id") != slot["store_id"]
            or plan.get("source_generation") != 0
            or plan.get("target_generation") != 1
            or any(
                plan.get(k) != getattr(target, k)
                for k in ("kind", "scope", "owner_id", "target_relative_path")
            )
        ):
            raise MaintenanceError("storage_plan_changed")
        return plan

    @contextmanager
    def new_store_identity(
        self,
        context: StorageMigrationContext,
        target: StoreTarget,
        *,
        _allow_legacy: bool = False,
    ) -> Iterator[str | None]:
        """Fence an explicit domain initializer, not an unused-store inventory.

        Publish a durable planned UUID/pending pin before the adapter creates its
        file. The adapter adds metadata in its domain initialization transaction
        with add_store_identity and closes before leaving this context. Failure
        retains the exact plan; a subsequent explicit initializer can retry if
        still absent, or verify an already committed exact UUID. No backup of an
        absent source is fabricated. Ordinary ensure_ready never creates stores.
        """
        if target not in validate_storage_context(context) or target.kind == "main":
            raise MaintenanceError("storage_target_invalid")
        root, descriptor = storage_owner_root(context, target), _descriptor()
        with self._admit(context, None), self._gate(root, None):
            slot = _slot(root, target)
            if slot is None:
                if target.target.exists():
                    raise MaintenanceError("storage_existing_target")
                proof = self._proof(context)
                if proof.state != "proven":
                    if _allow_legacy:
                        # Exact absent target, no pending pin or UUID. The original
                        # initializer remains usable on an unsupported host.
                        yield None
                        return
                    raise MaintenanceError("storage_activity_unknown")
                plan = self._plan(
                    context, target, descriptor, root, proof, {"state": "absent"}
                )
                _publish_pin(
                    root, target, plan["store_id"], plan["plan_checksum"], "pending"
                )
            else:
                plan = self._load(root, slot, target, descriptor)
                if plan.get("source") != {"state": "absent"}:
                    raise MaintenanceError("storage_resume_required")
                self._proof(context, plan["safety_generation"])
            yield str(plan["store_id"])
            self._proof(context, plan["safety_generation"])
            facts = _inspect_target(target, descriptor, self.driver, parity=True)
            if facts.get("store_id") != plan["store_id"]:
                raise MaintenanceError("storage_identity_conflict")
            _publish_pin(root, target, plan["store_id"], plan["plan_checksum"], "ready")
            _atomic(
                self._journal(root, plan["plan_checksum"]) / "journal.json",
                {
                    "plan_checksum": plan["plan_checksum"],
                    "store_id": plan["store_id"],
                    "state": "ready",
                    "backup_manifest_checksum": None,
                    "source_absent": True,
                },
            )

    def _target(
        self,
        context: StorageMigrationContext,
        target: StoreTarget,
        descriptor: JsonObject,
        deadline: float | None,
    ) -> JsonObject:
        root = storage_owner_root(context, target)
        with self._admit(context, deadline), self._gate(root, deadline):
            # No UUID or journal until safety has been proved under admission.
            slot = _slot(root, target)
            if slot is not None and slot["state"] == "ready":
                facts = _inspect_target(
                    target, descriptor, self.driver, deadline=deadline
                )
                if facts.get("store_id") != slot["store_id"]:
                    raise MaintenanceError("storage_identity_conflict")
                self._repair_ready(root, target, slot)
                return {"state": "ready"}
            if slot is None:
                facts = _inspect_target(
                    target, descriptor, self.driver, parity=True, deadline=deadline
                )
                if facts["state"] == "absent":
                    return {"state": "absent"}
                if facts["store_id"] is not None:
                    raise MaintenanceError("storage_pin_missing")
                proof = self._proof(context)
                if proof.state != "proven":
                    return {"state": "deferred", "legacy_allowed": True}
                plan = self._plan(context, target, descriptor, root, proof, facts)
                _publish_pin(
                    root, target, plan["store_id"], plan["plan_checksum"], "pending"
                )
            else:
                plan = self._load(root, slot, target, descriptor)
                self._proof(context, plan["safety_generation"])
        # Long backup/digests/DDL run outside admission and SQL transactions.
        # Pending pin fences capable opens. Target gate prevents concurrent resume.
        with self._gate(root, deadline):
            slot = _slot(root, target)
            if slot is None or slot["plan_checksum"] != plan["plan_checksum"]:
                raise MaintenanceError("storage_pin_conflict")
            self._apply_target(context, target, descriptor, root, plan, deadline)
        with self._admit(context, deadline), self._gate(root, deadline):
            self._proof(context, plan["safety_generation"])
            facts = _inspect_target(
                target, descriptor, self.driver, parity=True, deadline=deadline
            )
            if plan["source"] != {"state": "absent"}:
                self._parity(plan, facts)
            elif facts.get("store_id") != plan["store_id"]:
                raise MaintenanceError("storage_identity_conflict")
            _publish_pin(root, target, plan["store_id"], plan["plan_checksum"], "ready")
            directory = self._journal(root, plan["plan_checksum"])
            journal = _read(directory / "journal.json")
            journal["state"] = "ready"
            _atomic(directory / "journal.json", journal)
            _atomic(
                directory / "report.json",
                {
                    "schema_version": 1,
                    "status": "ready",
                    "plan_checksum": plan["plan_checksum"],
                    "store_id": plan["store_id"],
                    "target_relative_path": target.target_relative_path,
                },
            )
        return {"state": "ready", "plan_checksum": plan["plan_checksum"]}

    def _repair_ready(self, root: Path, target: StoreTarget, slot: JsonObject) -> None:
        """Repair only derived owned output, without reading old domain rows."""
        directory = self._journal(root, slot["plan_checksum"])
        journal_path = directory / "journal.json"
        if journal_path.exists():
            journal = _read(journal_path)
            if (
                journal.get("plan_checksum") != slot["plan_checksum"]
                or journal.get("store_id") != slot["store_id"]
            ):
                raise MaintenanceError("storage_journal_conflict")
            if journal.get("state") != "ready":
                journal["state"] = "ready"
                _atomic(journal_path, journal)
            expected = {
                "schema_version": 1,
                "status": "ready",
                "plan_checksum": slot["plan_checksum"],
                "store_id": slot["store_id"],
                "target_relative_path": target.target_relative_path,
            }
            report = directory / "report.json"
            if not report.exists():
                _atomic(report, expected)

    @staticmethod
    def _parity(plan: JsonObject, facts: JsonObject) -> None:
        expected = dict(plan["source"])
        expected["store_id"] = facts.get("store_id")
        if facts != expected or facts.get("store_id") not in {None, plan["store_id"]}:
            raise MaintenanceError("storage_source_changed")

    def _apply_target(
        self,
        context: StorageMigrationContext,
        target: StoreTarget,
        descriptor: JsonObject,
        root: Path,
        plan: JsonObject,
        deadline: float | None,
    ) -> None:
        directory = self._journal(root, plan["plan_checksum"])
        journal_path = directory / "journal.json"
        journal = _read(journal_path)
        if (
            journal.get("plan_checksum") != plan["plan_checksum"]
            or journal.get("store_id") != plan["store_id"]
            or journal.get("state") not in _STATES
        ):
            raise MaintenanceError("storage_journal_conflict")
        if plan.get("mode") != "existing":
            raise MaintenanceError("storage_plan_invalid")
        facts = _inspect_target(
            target, descriptor, self.driver, parity=True, deadline=deadline
        )
        if plan.get("source") == {"state": "absent"}:
            if facts.get("store_id") != plan["store_id"]:
                raise MaintenanceError("storage_new_initialization_required")
            journal.update(state="verified", source_absent=True)
            _atomic(journal_path, journal)
            return
        self._parity(plan, facts)
        bundle = directory / "backup"
        if not bundle.exists():
            if journal["state"] != "planned" or facts["store_id"] is not None:
                raise MaintenanceError("storage_backup_missing")
            self.backup.create(target.target, bundle)
        verified = self.backup.verify(bundle)
        if verified.get("verified") is not True or not isinstance(
            verified.get("manifest_sha256"), str
        ):
            raise MaintenanceError("storage_backup_unverified")
        checksum = "sha256:" + str(verified["manifest_sha256"])
        if journal.get("backup_manifest_checksum") not in {None, checksum}:
            raise MaintenanceError("storage_backup_changed")
        backup_target = StoreTarget(
            target.kind,
            bundle / "database.sqlite3",
            target.target_relative_path,
            target.scope,
            target.owner_id,
        )
        before = _inspect_target(
            backup_target, descriptor, self.driver, parity=True, deadline=deadline
        )
        if before != plan["source"] or before.get("store_id") is not None:
            raise MaintenanceError("storage_backup_conflict")
        if journal["backup_manifest_checksum"] is None:
            if facts["store_id"] is not None:
                raise MaintenanceError("storage_backup_unverified")
            journal.update(state="backed_up", backup_manifest_checksum=checksum)
            _atomic(journal_path, journal)
        _deadline(deadline)
        if facts["store_id"] is None:
            journal["state"] = "importing"
            _atomic(journal_path, journal)
            with _connection(
                target.target, self.driver, writable=True, deadline=deadline
            ) as connection:
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                current = {
                    "state": "legacy",
                    **_legacy_facts(
                        connection, target, descriptor, parity=True, deadline=deadline
                    ),
                }
                if current != plan["source"]:
                    raise MaintenanceError("storage_source_changed")
                add_store_identity(connection, target, plan["store_id"])
                connection.commit()
        after = _inspect_target(
            target, descriptor, self.driver, parity=True, deadline=deadline
        )
        self._parity(plan, after)
        if after["store_id"] != plan["store_id"]:
            raise MaintenanceError("storage_identity_conflict")
        journal["state"] = "verified"
        _atomic(journal_path, journal)

    def _execution(
        self,
        context: StorageMigrationContext,
        target: StoreTarget,
        deadline: float | None,
    ) -> JsonObject:
        if context.project_root is None:
            raise MaintenanceError("storage_execution_host_required")
        root = storage_owner_root(context, target)
        binding = _safe(root / "data/execution-storage.json")
        # A cold host needs no UUID/engine to defer an unqualified legacy target.
        # Pending/bound routes never get this escape hatch.
        if not binding.exists():
            with self._admit(context, deadline):
                if self._proof(context).state != "proven":
                    return {"state": "deferred", "legacy_allowed": True}
        engine = self.execution
        if engine is None and self.execution_factory is not None:
            engine = self.execution_factory(context, target)
        if engine is None:
            raise MaintenanceError("storage_execution_host_required")
        if (
            engine.database.target.path != target.target
            or engine.database.target.identity.owner_id != target.owner_id
            or engine.workplace_root != context.workplace_root
        ):
            raise MaintenanceError("storage_execution_target_conflict")
        if deadline is not None:
            # An operation-local engine retains the frozen API and checkpoint
            # protocol. Its proof boundaries enforce cancellation before CAS;
            # the shared injected service is never mutated between requests.
            verifier = engine.safety

            def bounded_proof(context: ExecutionMigrationContext) -> MigrationSafety:
                _deadline(deadline)
                if verifier is None:
                    raise MaintenanceError("execution_safety_unavailable")
                return verifier(context)

            engine = ExecutionMigrationService(
                database=engine.database,
                repository=engine.repository,
                admission=engine.admission,
                backup=engine.backup,
                safety=bounded_proof,
                workplace_root=engine.workplace_root,
                profile_id=engine.profile_id,
            )
        root = storage_owner_root(context, target)
        binding = _safe(root / "data/execution-storage.json")
        # The engine owns its binding, frozen source manifest, backup and SQL CAS.
        # Never hold an outer admission/identity gate when calling its protocol.
        if binding.exists():
            ready = engine.repository.readiness(deadline=deadline)
            if (
                ready.ready
                and ready.authority == "sql"
                and ready.store_id == engine.database.target.identity.store_id
            ):
                if _read(binding) != engine._binding(
                    {
                        "project_id": target.owner_id,
                        "store_id": ready.store_id,
                        "target_relative_path": target.target_relative_path,
                    }
                ):
                    raise MaintenanceError("execution_binding_conflict")
                return {"state": "ready"}
        with self._admit(context, deadline):
            proof = self._proof(context)
            if proof.state != "proven":
                if binding.exists():
                    raise MaintenanceError("storage_safety_changed")
                return {"state": "deferred", "legacy_allowed": True}
        _deadline(deadline)
        evidence_root = root / "maintenance/storage-migrations" / MIGRATION_ID
        selector = evidence_root / "execution.json"
        _safe(selector)
        if binding.exists():
            ready = engine.repository.readiness(deadline=deadline)
            if (
                ready.ready
                and ready.authority == "sql"
                and ready.store_id == engine.database.target.identity.store_id
            ):
                if _read(binding) != engine._binding(
                    {
                        "project_id": target.owner_id,
                        "store_id": ready.store_id,
                        "target_relative_path": target.target_relative_path,
                    }
                ):
                    raise MaintenanceError("execution_binding_conflict")
                return {"state": "ready"}
            if not selector.exists():
                raise MaintenanceError("storage_execution_resume_required")
            selected = _read(selector)
            evidence = evidence_root / str(selected["plan_checksum"])[7:]
            if selected.get(
                "migration_id"
            ) != "r02-worker-executions-v1" or not _checksum(
                selected.get("plan_checksum")
            ):
                raise MaintenanceError("storage_plan_invalid")
            result = engine.resume(
                context.project_root,
                migration_id=selected["migration_id"],
                plan_checksum=selected["plan_checksum"],
                evidence_dir=evidence,
                offline_confirmed=True,
            )
        else:
            if selector.exists():
                selected = _read(selector)
                if not _checksum(selected.get("plan_checksum")):
                    raise MaintenanceError("storage_plan_invalid")
                evidence = evidence_root / selected["plan_checksum"][7:]
                plan = _read(evidence / "plan.json")
            else:
                plan = engine.plan(context.project_root)
                if plan.get("blocked"):
                    raise MaintenanceError(
                        str(
                            plan.get("error", {}).get(
                                "code", "execution_storage_not_ready"
                            )
                        )
                    )
                evidence = evidence_root / plan["plan_checksum"][7:]
                with self._admit(context, deadline):
                    self._proof(context, proof.generation)
                    evidence_root.mkdir(parents=True, exist_ok=True)
                    # Exact selector is durable before invoking an independently
                    # checkpointed engine. Conflicting concurrent plans refuse.
                    selected = {
                        "migration_id": plan["migration_id"],
                        "plan_checksum": plan["plan_checksum"],
                    }
                    if selector.exists() and _read(selector) != selected:
                        raise MaintenanceError("storage_plan_conflict")
                    evidence.mkdir(parents=True, exist_ok=True)
                    if not (evidence / "plan.json").exists():
                        _exclusive_bytes(
                            evidence / "plan.json",
                            (canonical_json(plan) + "\n").encode(),
                        )
                    _atomic(selector, selected)
            result = engine.apply(
                context.project_root,
                plan,
                evidence_dir=evidence,
                offline_confirmed=True,
            )
        if result.get("status") != "ready" or result.get("blocked"):
            raise MaintenanceError(
                str(
                    (result.get("error") or {}).get(
                        "code", "execution_storage_not_ready"
                    )
                )
            )
        return {"state": "ready", "plan_checksum": result["plan_checksum"]}


def add_store_identity(
    connection: sqlite3.Connection, target: StoreTarget, store_id: str
) -> None:
    """Add exact metadata inside the caller-owned domain initialization transaction.

    Caller must publish its pending pin BEFORE creating/opening a new managed
    store, and hold admission then identity gate. No commit, pin publication,
    connection, default owner or remint occurs here. Main is never accepted.
    """
    if target.kind == "main" or not connection.in_transaction:
        raise MaintenanceError("storage_identity_transaction_required")
    _uuid(store_id)
    for statement in STORE_ENVELOPE_DDL:
        connection.execute(statement)
    connection.execute(
        "INSERT INTO pf_store_meta VALUES(1,?,?,?,1)",
        (store_id, target.scope, target.owner_id),
    )
    connection.execute(
        "INSERT INTO pf_schema_versions VALUES('store_identity',1,?)",
        (STORE_IDENTITY_SCHEMA.checksum,),
    )


@dataclass(frozen=True, init=False)
class StorageMigrationHost:
    """Exact host composition result consumed by script and automatic hooks."""

    service: StorageMigrationService
    _context: StorageMigrationContext | None
    _context_factory: Callable[[], StorageMigrationContext] | None
    automatic: bool

    def __init__(
        self,
        context: StorageMigrationContext | None,
        service: StorageMigrationService,
        *,
        _context_factory: Callable[[], StorageMigrationContext] | None = None,
        _automatic: bool = False,
    ) -> None:
        if (context is None) == (_context_factory is None):
            raise MaintenanceError("storage_host_factory_invalid")
        object.__setattr__(self, "service", service)
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_context_factory", _context_factory)
        object.__setattr__(self, "automatic", _automatic)

    @cached_property
    def context(self) -> StorageMigrationContext:
        """Resolve selected metadata only at an explicit operation boundary."""
        if self._context is not None:
            return self._context
        if self._context_factory is None:
            raise MaintenanceError("storage_host_factory_invalid")
        return self._context_factory()


def run_storage_migration(
    host: StorageMigrationHost,
    *,
    operation: Literal["inspect", "apply", "resume"],
    deadline: float | None = None,
) -> JsonObject:
    """Use the identical service from installed script and automatic host calls."""
    if operation == "inspect":
        return host.service.inspect(host.context)
    if operation == "apply":
        return host.service.ensure_ready(
            host.context, trigger="update", deadline=deadline
        )
    if operation == "resume":
        return host.service.resume(host.context, deadline=deadline)
    return StorageMigrationService._failure(
        StorageMigrationService._report("storage"),
        MaintenanceError("storage_operation_invalid"),
    )
