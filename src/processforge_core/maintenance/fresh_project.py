"""Qualified fresh project initialization, separate from old-writer migration.

Only the host that exclusively created the flow root may publish the receipt.
Recovery requires that durable receipt and the same physical root and routing.
No workplace target derives authority from this project receipt.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..configuration import ConfigurationProvider
from ..database import DatabaseError, SchemaManager
from ..database.sqlite import _failure
from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import ExecutionAdmission
from .contracts import MaintenanceError, StoreTarget
from .execution_migration import _atomic, _hash, _read
from .journal_scan import _exclusive_bytes
from .storage_migration import (
    StorageMigrationHost,
    _descriptor,
    _inspect_target,
    _publish_pin,
    _safe,
    _slot,
    _uuid,
)

RECEIPT = "maintenance/project-initialization.json"


def _capable() -> None:
    # Use the already captured native entry, never reload a leaf from disk.
    import sys

    native = sys.modules.get("pf_native_control")
    probe = getattr(native, "supports_owned_execution", None)
    if not callable(probe) or not probe():
        raise MaintenanceError("storage_fresh_capability_required")


def _physical(flow: Path) -> list[int]:
    info = _safe(flow).stat()
    return [info.st_dev, info.st_ino]


def create_project_storage_root(project: Path) -> bool:
    """Qualify the backend and exclusively create the root before issuing authority."""
    _capable()
    flow = _safe(project / ".pf")
    try:
        flow.mkdir()
    except FileExistsError:
        return False
    path = _safe(flow / RECEIPT)
    path.parent.mkdir(parents=True, exist_ok=True)
    _exclusive_bytes(
        path,
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "creation_id": uuid4().hex,
                    "root_identity": _physical(flow),
                    "state": "pending",
                    "project_id": None,
                    "workplace": None,
                    "domains": None,
                },
                sort_keys=True,
            )
            + "\n"
        ).encode(),
    )
    return True


def _receipt(project: Path) -> dict[str, Any] | None:
    flow = _safe(ProjectMetadataReader(project).flow_root())
    path = _safe(flow / RECEIPT)
    if not path.exists():
        return None
    value = _read(path)
    if (
        set(value)
        != {
            "schema_version",
            "creation_id",
            "root_identity",
            "state",
            "project_id",
            "workplace",
            "domains",
        }
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["state"] not in {"pending", "ready"}
        or value["root_identity"] != _physical(flow)
    ):
        raise MaintenanceError("storage_fresh_receipt_invalid")
    _uuid(value["creation_id"])
    return value


def _domain(document: dict[str, Any], target: StoreTarget) -> dict[str, Any]:
    domains = document["domains"]
    if not isinstance(domains, list):
        raise MaintenanceError("storage_fresh_receipt_invalid")
    matches = [
        item
        for item in domains
        if isinstance(item, dict)
        and item.get("target_relative_path") == target.target_relative_path
    ]
    if len(matches) != 1:
        raise MaintenanceError("storage_fresh_target_conflict")
    item = matches[0]
    if set(item) != {"kind", "scope", "owner_id", "target_relative_path", "store_id"}:
        raise MaintenanceError("storage_fresh_receipt_invalid")
    if any(item[k] != getattr(target, k) for k in item if k != "store_id"):
        raise MaintenanceError("storage_fresh_target_conflict")
    _uuid(item["store_id"])
    return item


def _selected(host: StorageMigrationHost, target: StoreTarget) -> dict[str, Any] | None:
    context = host.context
    if target.scope != "project" or context.project_root is None:
        return None
    document = _receipt(context.project_root)
    if document is None:
        return None
    if (
        target not in context.targets
        or target.kind not in {"events", "raw", "search"}
        or document["project_id"] != target.owner_id
        or document["workplace"] != str(context.workplace_root or "")
    ):
        raise MaintenanceError("storage_fresh_target_conflict")
    _domain(document, target)
    return document


def owns_target(host: StorageMigrationHost, target: StoreTarget) -> bool:
    return _selected(host, target) is not None


@contextmanager
def _storage_errors() -> Iterator[None]:
    """Translate only expected storage failures, retaining diagnostic causes."""
    from ..sqlite_storage import JournalError

    try:
        yield
    except sqlite3.Error as error:
        raise _failure(error, None) from error
    except OSError as error:
        raise DatabaseError("database_io_failed") from error
    except JournalError as error:
        if isinstance(error.__cause__, sqlite3.Error):
            raise _failure(error.__cause__, None) from error
        raise


@contextmanager
def _connection(
    host: StorageMigrationHost, path: Path, *, readonly: bool = False
) -> Iterator[sqlite3.Connection]:
    """Own direct initializer connections and preserve failures during close."""
    with _storage_errors():
        db = host.service.driver._connect(
            path.as_uri() + "?mode=ro" if readonly else path,
            uri=readonly,
            isolation_level=None,
        )
    primary: BaseException | None = None
    try:
        with _storage_errors():
            yield db
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            with _storage_errors():
                db.close()
        except Exception as cleanup:
            if primary is None:
                raise
            primary.add_note(f"storage_close_failed: {type(cleanup).__name__}")
            primary.add_note(
                f"storage_close_reason: {getattr(cleanup, 'code', 'unknown')}"
            )


def _initialize_domain(
    host: StorageMigrationHost, target: StoreTarget, store_id: str
) -> None:
    """Initialize schema/envelope atomically before admitting ordinary domain work."""
    from ..sqlite_storage import _database, transaction
    from .storage_migration import add_store_identity

    path = _safe(target.target)
    if path.exists():
        # Only a zero-object SQLite file left by this pending initializer may
        # retry DDL. A pre-existing domain without its planned UUID is refused.
        with _connection(host, path, readonly=True) as db:
            objects = db.execute("SELECT 1 FROM sqlite_schema LIMIT 1").fetchone()
            empty = (
                objects is None
                and db.execute("PRAGMA application_id").fetchone()[0] == 0
                and db.execute("PRAGMA user_version").fetchone()[0] == 0
            )
        if not empty:
            facts = _inspect_target(
                target, _descriptor(verify_transforms=False), host.service.driver
            )
            if facts.get("store_id") != store_id:
                raise MaintenanceError("storage_identity_conflict")
            return
    if target.kind in {"events", "raw"}:
        from .. import process_event_journal, raw_hook_journal

        domain = process_event_journal if target.kind == "events" else raw_hook_journal
        with _storage_errors():
            with _database(
                path,
                application_id=domain.APPLICATION_ID,
                schema=domain.SCHEMA,
                writable=True,
                driver=host.service.driver,
                identity=(target, store_id),
            ):
                pass
    else:
        from ..resources.local_search import _ensure_schema

        with _storage_errors():
            path.parent.mkdir(parents=True, exist_ok=True)
        with _connection(host, path) as db:
            db.execute("PRAGMA synchronous=FULL")
            with transaction(db):
                _ensure_schema(db)
                add_store_identity(db, target, store_id)


def _require_ready(host: StorageMigrationHost, document: dict[str, Any]) -> None:
    """Read main SQL using the exact host-selected configuration and alias."""
    from ..executions.composition import _fresh_initialization
    from ..executions.schema import EXECUTION_SCHEMA

    context = host.context
    if document["state"] != "ready" or context.project_root is None:
        raise MaintenanceError("execution_storage_not_ready")
    flow = ProjectMetadataReader(context.project_root).flow_root()
    marker = _fresh_initialization(flow)
    if marker is None or marker["state"] != "ready":
        raise MaintenanceError("execution_storage_not_ready")
    binding = _read(_safe(flow / "data/execution-storage.json"))
    if (
        binding != marker["binding"]
        or binding.get("project_id") != document["project_id"]
    ):
        raise MaintenanceError("execution_storage_not_ready")
    # A host may select only a lazy domain. The durable main binding supplies
    # its target; the host factory still checks the exact configured profile.
    relative = binding["target_relative_path"]
    main = StoreTarget(
        "main", _safe(flow / relative), relative, "project", document["project_id"]
    )
    factory = host.service.execution_factory
    if factory is None:
        raise MaintenanceError("execution_storage_not_ready")
    engine = factory(context, main)
    if (
        SchemaManager().inspect(engine.database, (EXECUTION_SCHEMA,)).state != "ready"
        or not engine.repository.readiness().ready
    ):
        raise MaintenanceError("execution_storage_not_ready")


def _domain_identity(
    host: StorageMigrationHost, target: StoreTarget, document: dict[str, Any]
) -> tuple[StoreTarget, str]:
    """Initializer implementation; caller holds admission and identity gate."""
    context = host.context
    assert context.project_root is not None
    root = ProjectMetadataReader(context.project_root).flow_root()
    if _selected(host, target) != document:
        raise MaintenanceError("storage_fresh_target_conflict")
    item = _domain(document, target)
    store_id = item["store_id"]
    checksum = _hash({"creation_id": document["creation_id"], "domain": item})
    slot = _slot(root, target)
    if slot is not None and (
        slot["store_id"] != store_id or slot["plan_checksum"] != checksum
    ):
        raise MaintenanceError("storage_identity_conflict")
    if slot is None or slot["state"] == "pending":
        _capable()
        if slot is None:
            if target.target.exists():
                raise MaintenanceError("storage_existing_target")
            _publish_pin(root, target, store_id, checksum, "pending")
        _initialize_domain(host, target, store_id)
        facts = _inspect_target(
            target, _descriptor(verify_transforms=False), host.service.driver
        )
        if facts.get("store_id") != store_id:
            raise MaintenanceError("storage_identity_conflict")
        _publish_pin(root, target, store_id, checksum, "ready")
    else:
        facts = _inspect_target(
            target, _descriptor(verify_transforms=False), host.service.driver
        )
        if facts.get("store_id") != store_id:
            raise MaintenanceError("storage_identity_conflict")
    return target, store_id


@contextmanager
def identity_access(
    host: StorageMigrationHost, target: StoreTarget
) -> Iterator[tuple[StoreTarget, str]]:
    """Explicit initializer/recovery authority for an exact receipt-owned domain."""
    context = host.context
    document = _selected(host, target)
    if document is None or context.project_root is None:
        raise MaintenanceError("storage_fresh_target_conflict")
    root = ProjectMetadataReader(context.project_root).flow_root()
    with host.service._admitted_gate(context, root, None):
        yield _domain_identity(host, target, document)


@contextmanager
def ordinary_identity_access(
    host: StorageMigrationHost, target: StoreTarget
) -> Iterator[tuple[StoreTarget, str]]:
    """Admit lazy writes only after project and actual main SQL readiness."""
    context = host.context
    document = _selected(host, target)
    if document is None or context.project_root is None:
        raise MaintenanceError("storage_fresh_target_conflict")
    root = ProjectMetadataReader(context.project_root).flow_root()
    if document["state"] != "ready":
        raise MaintenanceError("execution_storage_not_ready")
    with host.service._admitted_gate(context, root, None):
        _require_ready(host, document)
        yield _domain_identity(host, target, document)


def initialize_project_storage(
    project: Path, workplace: Path | None, *, configuration: ConfigurationProvider
) -> bool:
    """Complete only an explicitly created project; raw/search remain lazy."""
    from ..composition import build_storage_migration_host
    from ..executions.composition import (
        _fresh_initialization,
        _initialize_fresh_execution_storage,
        _repair_fresh_execution_storage,
        select_execution_storage,
    )

    if _receipt(project) is None:
        return False
    with ExecutionAdmission().maintenance(project, workplace):
        document = _receipt(project)
        assert document is not None
        if document["state"] == "pending":
            _capable()
        host = build_storage_migration_host(
            project_root=project,
            workplace_root=workplace,
            device_config_path=None,
            configuration=configuration,
        )
        context = host.context
        targets = tuple(
            t for t in context.targets if t.scope == "project" and t.kind != "main"
        )
        flow = ProjectMetadataReader(project).flow_root()
        owner = ProjectMetadataReader(project).manifest().get("project", {}).get("id")
        if document["domains"] is None:
            if document["state"] != "pending" or document["project_id"] is not None:
                raise MaintenanceError("storage_fresh_receipt_invalid")
            if any(t.target.exists() or _slot(flow, t) is not None for t in targets):
                raise MaintenanceError("storage_existing_target")
            document.update(
                project_id=owner,
                workplace=str(workplace or ""),
                domains=[
                    {
                        "kind": t.kind,
                        "scope": t.scope,
                        "owner_id": t.owner_id,
                        "target_relative_path": t.target_relative_path,
                        "store_id": uuid4().hex,
                    }
                    for t in targets
                ],
            )
            _atomic(flow / RECEIPT, document)
        if (
            document["project_id"] != owner
            or document["workplace"] != str(workplace or "")
            or len(document["domains"]) != len(targets)
        ):
            raise MaintenanceError("storage_fresh_target_conflict")
        for target in targets:
            _domain(document, target)
        marker = _fresh_initialization(flow)
        if marker is None:
            if document["state"] == "ready":
                raise MaintenanceError("execution_storage_not_ready")
            _initialize_fresh_execution_storage(
                project, workplace, configuration=configuration
            )
        elif marker["state"] == "pending":
            _repair_fresh_execution_storage(
                project, workplace, configuration=configuration, _verify=_capable
            )
        if (
            select_execution_storage(
                project, workplace, configuration=configuration
            ).repository
            is None
        ):
            raise MaintenanceError("execution_storage_not_ready")
        for target in targets:
            if target.kind == "events":
                with identity_access(host, target):
                    pass
        if document["state"] != "ready":
            document["state"] = "ready"
            _atomic(flow / RECEIPT, document)
    return True
