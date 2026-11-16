"""Require ready SQL execution storage before ordinary Work and worker writes."""

from __future__ import annotations

from pathlib import Path

from ..configuration import ConfigurationProvider
from ..database import DatabaseError
from ..executions.composition import select_execution_storage
from ..executions.model import ExecutionError
from ..project.configuration_inputs import (
    ProjectConfigurationReader,
    _first_write_storage_host,
    operation_device_path,
)
from .contracts import MaintenanceError
from .storage_migration import StorageMigrationHost


def ensure_execution_storage_ready(
    project_root: Path, workplace_root: Path | None
) -> tuple[StorageMigrationHost | None, ConfigurationProvider]:
    """Map storage-boundary I/O failure without exposing private paths."""
    try:
        return _ensure_execution_storage_ready(project_root, workplace_root)
    except OSError as error:
        raise MaintenanceError("storage_activity_unknown") from error


def _ensure_execution_storage_ready(
    project_root: Path, workplace_root: Path | None
) -> tuple[StorageMigrationHost | None, ConfigurationProvider]:
    """Migrate through actual host proof, then reselect SQL before taking locks.

    Read-only selection and explicit recovery may still inspect legacy storage.
    A deferred migration never authorizes an ordinary write or a new attempt.
    """
    provider = ProjectConfigurationReader().configuration_provider(
        project_root, workplace_root
    )
    snapshot = provider.snapshot()
    if snapshot.errors:
        raise MaintenanceError("storage_configuration_invalid")
    pinned = ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)
    from .fresh_project import initialize_project_storage

    initialize_project_storage(project_root, workplace_root, configuration=pinned)
    try:
        route = select_execution_storage(
            project_root, workplace_root, configuration=pinned
        )
    except (DatabaseError, ExecutionError):
        # The coordinator alone may repair an exact pending initializer/plan.
        # It must revalidate bound, foreign and corrupt routes before any write.
        route = None
    if route is not None and route.repository is not None:
        return None, pinned
    host = _first_write_storage_host(
        project_root,
        workplace_root,
        operation_device_path(project_root, workplace_root, provider.device_path),
        pinned,
    )
    result = host.service.ensure_ready(host.context, trigger="first_write")
    if result.get("blocked") or result.get("status") != "ready":
        raise MaintenanceError(
            str((result.get("error") or {}).get("code") or "storage_activity_unknown")
        )
    if (
        select_execution_storage(
            project_root, workplace_root, configuration=pinned
        ).repository
        is None
    ):
        raise MaintenanceError("execution_storage_not_ready")
    return host, pinned
