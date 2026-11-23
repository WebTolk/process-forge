"""Admission for a selected project event migration under a managed Runtime."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..runtime.execution_admission import _registry_lock_read_owner, registry_file_lock
from ..runtime_service_state import (
    PROJECT_EVENT_MAINTENANCE_CAPABILITY,
    PROJECT_EVENT_RUNTIME_IDENTITY,
    RuntimeServiceStateStore,
    runtime_process_identity,
)
from .backup import SQLiteBackupService
from .contracts import JsonObject, MaintenanceError
from .storage_migration import (
    StorageMigrationHost,
    StorageMigrationService,
    _connection,
    _safe,
    run_storage_migration,
    storage_owner_root,
    validate_storage_context,
)

if TYPE_CHECKING:
    from ..database import SQLiteDriver
    from .contracts import StoreTarget

PROJECT_EVENT_MAINTENANCE_BUSY = "storage_project_event_maintenance_busy"


class ProjectEventBackupService(SQLiteBackupService):
    """Publish a complete verified bundle at its immutable plan location."""

    def create(self, source: Path, bundle: Path) -> JsonObject:
        # The parent migration retains the project identity gate throughout.
        # A killed copier can leave staging, but never an incomplete final bundle.
        with tempfile.TemporaryDirectory(
            prefix=".backup-stage-", dir=bundle.parent
        ) as name:
            staging = Path(name) / bundle.name
            super().create(source, staging)
            verified = self.verify(staging)
            if bundle.exists():
                raise MaintenanceError("storage_backup_conflict")
            os.rename(staging, bundle)
        return verified


def _intent(root: Path) -> Path:
    return root / "runtime/project-event-maintenance"


@contextmanager
def ordinary_storage_lock(
    path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0
) -> Iterator[None]:
    """Refuse a contested owner gate promptly during its explicit maintenance."""

    def check_intent() -> None:
        intent = _intent(path.parent.parent)
        marker = intent.with_name(f".{intent.name}.lock")
        if marker.is_file():
            raise MaintenanceError(PROJECT_EVENT_MAINTENANCE_BUSY)

    with registry_file_lock(
        path,
        timeout_seconds=timeout_seconds,
        stale_after_seconds=stale_after_seconds,
        on_contention=check_intent if path.name == "storage-identity" else None,
    ):
        yield


def require_compatible_runtime(workplace: Path) -> None:
    """Read bounded control records published by one ready local Runtime."""
    runtime = workplace / "runtime/pf-runtime"
    try:
        state = RuntimeServiceStateStore._control(_safe(runtime / "service.json"))
        lock = RuntimeServiceStateStore._control(_safe(runtime / "runtime.lock"))
    except (OSError, ValueError) as error:
        raise MaintenanceError("storage_project_event_runtime_unknown") from error
    capabilities = state.get("capabilities")
    pid = state.get("pid")
    instance = state.get("instance_id")
    if (
        type(pid) is not int
        or pid <= 0
        or type(lock.get("pid")) is not int
        or lock["pid"] != pid
        or not isinstance(instance, str)
        or not instance
        or lock.get("instance_id") != instance
        or state.get("workplace_root") != str(workplace)
        or state.get("status") != "ready"
    ):
        raise MaintenanceError("storage_project_event_runtime_unknown")
    capability = (
        capabilities.get(PROJECT_EVENT_MAINTENANCE_CAPABILITY)
        if isinstance(capabilities, dict)
        else None
    )
    if type(capability) is not int or capability != 1:
        raise MaintenanceError("storage_project_event_runtime_unsupported")
    observed = runtime_process_identity(pid)
    if observed is None or state.get(PROJECT_EVENT_RUNTIME_IDENTITY) != observed:
        raise MaintenanceError("storage_project_event_runtime_unknown")


def require_imported_history(target: StoreTarget, driver: SQLiteDriver) -> None:
    """Keep the NDJSON import under its existing separate maintenance contract."""
    legacy = _safe(target.target.with_suffix(".ndjson"))
    if not legacy.is_file() or legacy.stat().st_size == 0:
        return
    with _connection(target.target, driver) as connection:
        imported = connection.execute(
            "SELECT value FROM journal_metadata WHERE key='legacy_imported'"
        ).fetchone()
    if imported != ("1",):
        raise MaintenanceError("storage_project_event_import_required")


def run_project_event_migration(
    host: StorageMigrationHost,
    *,
    operation: Literal["inspect", "apply", "resume"],
    offline_confirmed: bool,
) -> JsonObject:
    """Run the existing durable transform with a project-owned operation intent."""
    report = StorageMigrationService._report(f"storage-{operation}")
    report["requested_target"] = {"kind": "events", "scope": "project"}
    try:
        context = host.context
        targets = validate_storage_context(context)
        if (
            context.project_root is None
            or context.workplace_root is None
            or len(targets) != 1
            or targets[0].scope != "project"
            or targets[0].kind != "events"
            or context.unqualified_targets
        ):
            raise MaintenanceError("storage_project_event_target_invalid")
        target = targets[0]
        selected = {
            "kind": target.kind,
            "scope": target.scope,
            "owner_id": target.owner_id,
            "target_relative_path": target.target_relative_path,
        }
        report["selected_target"] = selected
        bound = StorageMigrationHost(context, host.service)
        if operation == "inspect":
            report = run_storage_migration(bound, operation=operation)
        else:
            if not offline_confirmed:
                require_compatible_runtime(context.workplace_root)
            if not target.target.is_file():
                raise MaintenanceError("storage_project_event_journal_missing")
            intent = _intent(storage_owner_root(context, target))
            for suffix in (".lock", ".lock.guard"):
                _safe(intent.with_name(f".{intent.name}{suffix}"))
            with registry_file_lock(
                intent, timeout_seconds=0.05, stale_after_seconds=0
            ):
                if (
                    operation == "resume"
                    and not host.service._selector(
                        storage_owner_root(context, target), target
                    ).is_file()
                ):
                    raise MaintenanceError("storage_project_event_plan_missing")
                require_imported_history(target, host.service.driver)
                report = run_storage_migration(bound, operation=operation)
        report["selected_target"] = selected
        if (report.get("error") or {}).get(
            "code"
        ) == "storage_project_event_runtime_unknown":
            report["retryable"] = True
        return report
    except SystemExit as error:
        if getattr(error, "registry_lock_reason", None) != "contention_timeout":
            raise
        marker = intent.with_name(f".{intent.name}.lock")
        unknown = (
            getattr(error, "registry_lock_phase", None) == "owner"
            and _registry_lock_read_owner(marker) is None
        )
        code = (
            "storage_project_event_intent_unknown"
            if unknown
            else PROJECT_EVENT_MAINTENANCE_BUSY
        )
        report = StorageMigrationService._failure(report, MaintenanceError(code))
        report["retryable"] = not unknown
        return report
    except (MaintenanceError, OSError, sqlite3.Error) as error:
        report = StorageMigrationService._failure(report, error)
        if report["error"]["code"] == "storage_project_event_runtime_unknown":
            report["retryable"] = True
        return report
