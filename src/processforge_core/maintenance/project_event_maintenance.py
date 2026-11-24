"""Admission for a selected project event migration under a managed Runtime."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..runtime.execution_admission import (
    ExecutionAdmission,
    PreparedRegistryOwner,
    RegistryLockTimeout,
    prepare_registry_owner,
    registry_file_lock,
    try_registry_file_lock,
    wait_registry_file_lock,
)
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
    _deadline,
    _safe,
    run_storage_migration,
    storage_identity_gate,
    storage_owner_root,
    validate_storage_context,
)

if TYPE_CHECKING:
    from ..database import SQLiteDriver
    from .contracts import StorageMigrationContext, StoreTarget

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


@dataclass(frozen=True)
class _SelectedTargetAdmission:
    gate: Path
    workplace: Path
    owner: PreparedRegistryOwner


_SELECTED_TARGET_ADMISSION: ContextVar[_SelectedTargetAdmission | None] = ContextVar(
    "project_event_target_admission", default=None
)


@contextmanager
def _bind_selected_target(
    gate: Path, workplace: Path
) -> Iterator[PreparedRegistryOwner]:
    # The selected storage gate lives under the project's flow root.
    project_root = gate.parents[2]
    if ExecutionAdmission.held(None, workplace) or ExecutionAdmission.held(
        project_root, None
    ):
        raise MaintenanceError("storage_activity_unknown")
    owner = prepare_registry_owner()
    token = _SELECTED_TARGET_ADMISSION.set(
        _SelectedTargetAdmission(gate, workplace, owner)
    )
    try:
        yield owner
    finally:
        _SELECTED_TARGET_ADMISSION.reset(token)


@contextmanager
def _selected_registry_wait(
    path: Path, *, deadline: float, stale_after_seconds: float, unknown_code: str
) -> Iterator[None]:
    with ExitStack() as access:
        try:
            access.enter_context(
                wait_registry_file_lock(
                    path, deadline=deadline, stale_after_seconds=stale_after_seconds
                )
            )
        except RegistryLockTimeout as error:
            if error.assessment in {"guard_busy", "owner_live"}:
                code = PROJECT_EVENT_MAINTENANCE_BUSY
            elif error.assessment in {"owner_dead", "deadline_expired"}:
                code = "storage_deadline_exceeded"
            else:
                code = unknown_code
            raise MaintenanceError(code) from error
        yield


@contextmanager
def project_event_operation_intent(
    path: Path, owner: PreparedRegistryOwner, *, deadline: float
) -> Iterator[None]:
    """Fence duplicate maintenance requests without shortening free acquisition."""
    _deadline(deadline)
    for suffix in (".lock", ".lock.guard"):
        _safe(path.with_name(f".{path.name}{suffix}"))
    with try_registry_file_lock(path, owner=owner) as result:
        if result == "acquired":
            _deadline(deadline)
            yield
            return
    with ExitStack() as access:
        try:
            access.enter_context(
                _selected_registry_wait(
                    path,
                    deadline=min(deadline, time.monotonic() + 0.05),
                    stale_after_seconds=0,
                    unknown_code="storage_project_event_intent_unknown",
                )
            )
        except MaintenanceError as error:
            if error.code != "storage_deadline_exceeded":
                raise
            # The expired attempt may have reclaimed its stale marker before
            # sync consumed the remaining contention budget. Prove an empty
            # guard with a new try under the original operation deadline.
            _deadline(deadline)
            result = access.enter_context(try_registry_file_lock(path, owner=owner))
            if result != "acquired":
                raise error
        _deadline(deadline)
        yield


@contextmanager
def selected_storage_lock(
    path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0
) -> Iterator[None]:
    """Adapt the frozen target lock callback to operation-local admission."""
    selection = _SELECTED_TARGET_ADMISSION.get()
    if selection is None or path != selection.gate:
        raise MaintenanceError("storage_activity_unknown")
    if ExecutionAdmission.held(None, selection.workplace):
        # The frozen full-wait caller also floors its timeout at 1 ms.
        if timeout_seconds != 0.001:
            raise MaintenanceError("storage_activity_unknown")
        with try_registry_file_lock(path, owner=selection.owner) as result:
            if result == "acquired":
                yield
                return
        # The frozen engine recognizes this signal and unwinds admission.
        error = SystemExit("registry lock contention")
        error.__dict__.update(
            registry_lock_reason="contention_timeout",
            registry_lock_phase="guard" if result == "guard_busy" else "owner",
        )
        raise error

    with _selected_registry_wait(
        path,
        deadline=time.monotonic() + timeout_seconds,
        stale_after_seconds=stale_after_seconds,
        unknown_code="storage_project_event_target_owner_unknown",
    ):
        yield


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


def selected_project_event_target(context: StorageMigrationContext) -> StoreTarget:
    """Return the validated event target selected by the host."""
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
    return targets[0]


def run_project_event_migration(
    host: StorageMigrationHost,
    *,
    operation: Literal["inspect", "apply", "resume"],
    offline_confirmed: bool,
) -> JsonObject:
    """Run the existing durable transform with a project-owned operation intent."""
    report = StorageMigrationService._report(f"storage-{operation}")
    selected: JsonObject | None = None
    try:
        context = host.context
        target = selected_project_event_target(context)
        selected = {
            "kind": target.kind,
            "scope": target.scope,
            "owner_id": target.owner_id,
            "target_relative_path": target.target_relative_path,
        }
        bound = StorageMigrationHost(context, host.service)
        if operation == "inspect":
            report = run_storage_migration(bound, operation=operation)
        else:
            assert context.workplace_root is not None
            if not offline_confirmed:
                require_compatible_runtime(context.workplace_root)
            if not target.target.is_file():
                raise MaintenanceError("storage_project_event_journal_missing")
            root = storage_owner_root(context, target)
            intent = _intent(root)
            with (
                _bind_selected_target(
                    storage_identity_gate(root), context.workplace_root
                ) as owner,
                project_event_operation_intent(
                    intent, owner, deadline=time.monotonic() + 30.0
                ),
            ):
                if (
                    operation == "resume"
                    and not host.service._selector(root, target).is_file()
                ):
                    raise MaintenanceError("storage_project_event_plan_missing")
                require_imported_history(target, host.service.driver)
                report = run_storage_migration(bound, operation=operation)
    except (MaintenanceError, OSError, sqlite3.Error) as error:
        report = StorageMigrationService._failure(report, error)
    report["requested_target"] = {"kind": "events", "scope": "project"}
    if selected is not None:
        report["selected_target"] = selected
    if (report.get("error") or {}).get("code") in {
        "storage_project_event_runtime_unknown",
        PROJECT_EVENT_MAINTENANCE_BUSY,
    }:
        report["retryable"] = True
    return report
