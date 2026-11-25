"""Acquire the project journal before entering a routed Runtime event phase."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar
from pathlib import Path

from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import ExecutionAdmission, _GateLease
from .contracts import MaintenanceError
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
def event_ingress_admission(
    project: Path, workplace: Path, storage: StorageMigrationHost | None
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
    with storage.service._admitted_gate(context, root, None):
        lease = _GateLease((os.getpid(), threading.get_ident(), gate))
        token = _JOURNAL_GATE.set(lease)
        try:
            yield
        finally:
            lease.active = False
            _JOURNAL_GATE.reset(token)
