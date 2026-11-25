"""Acquire the project journal before entering a routed Runtime event phase."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager, nullcontext
from contextvars import ContextVar
from pathlib import Path

from ..database import DatabaseError
from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import ExecutionAdmission, _GateLease
from .contracts import MaintenanceError
from .fresh_project import event_main_snapshot
from .project_event_maintenance import ordinary_storage_lock
from .storage_migration import StorageMigrationHost, storage_identity_gate

_JOURNAL_GATE: ContextVar[_GateLease | None] = ContextVar(
    "event_ingress_gate", default=None
)


def ordinary_journal_lock(
    path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0
) -> AbstractContextManager[None]:
    lease = _JOURNAL_GATE.get()
    if lease is not None and lease.is_current() and lease.key[2] == path:
        return nullcontext()
    return ordinary_storage_lock(
        path, timeout_seconds=timeout_seconds, stale_after_seconds=stale_after_seconds
    )


@contextmanager
def _event_snapshot_scope(storage: StorageMigrationHost) -> Iterator[None]:
    """Keep the SQLite read separate from errors raised by the Runtime adapter."""
    with ExitStack() as snapshot:
        snapshot.enter_context(event_main_snapshot(storage))
        try:
            yield
        except BaseException as request_error:
            try:
                snapshot.close()
            except Exception as close_error:
                code = (
                    close_error.code
                    if isinstance(close_error, DatabaseError)
                    else type(close_error).__name__
                )
                request_error.add_note(f"event_main_snapshot_close_failed: {code}")
            raise


@contextmanager
def event_ingress_admission(
    project: Path,
    workplace: Path,
    storage: StorageMigrationHost | None,
    *,
    writing: bool = False,
) -> Iterator[None]:
    if storage is None:
        with ExecutionAdmission().start(project, workplace):
            yield
        return

    context = storage.context
    if (context.project_root, context.workplace_root) != (project, workplace):
        raise MaintenanceError("storage_enrollment_conflict")
    root = ProjectMetadataReader(project).flow_root()
    gate = storage_identity_gate(root)
    # The service releases workplace admission before waiting for a reader.
    # Retain this exact gate across the phase so each journal open can verify
    # its own target and UUID without racing to reacquire the same lock.
    deadline = time.monotonic() + 30.0
    inherited = ExecutionAdmission.held(project, None) or ExecutionAdmission.held(
        None, workplace
    )
    with ExitStack() as acquired:
        while True:
            acquired.enter_context(
                storage.service._admitted_gate(context, root, deadline)
            )
            try:
                if writing:
                    # This read witnesses WAL availability before event writes.
                    acquired.enter_context(_event_snapshot_scope(storage))
            except DatabaseError as error:
                if inherited or error.code != "database_busy" or not error.retryable:
                    raise
                # No part of the event phase has run. Wait outside every gate.
                acquired.close()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(0.01, remaining))
                if time.monotonic() >= deadline:
                    raise
            else:
                break
        lease = _GateLease((os.getpid(), threading.get_ident(), gate))
        token = _JOURNAL_GATE.set(lease)
        try:
            yield
        finally:
            lease.active = False
            _JOURNAL_GATE.reset(token)
