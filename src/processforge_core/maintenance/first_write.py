"""Require ready SQL execution storage before ordinary Work and worker writes."""

from __future__ import annotations

from pathlib import Path

from ..configuration import ConfigurationProvider
from ..database import DatabaseError
from ..executions.composition import select_execution_storage
from ..executions.model import ExecutionError
from ..project.configuration_inputs import ProjectConfigurationReader
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
    """Require SQL readiness; legacy migration is an explicit maintenance action.

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
    except (DatabaseError, ExecutionError) as error:
        raise MaintenanceError(error.code) from error
    if route.repository is None:
        from ..project.metadata import ProjectMetadataReader

        owner = ProjectMetadataReader(project_root).manifest().get("project")
        owner_id = owner.get("id") if isinstance(owner, dict) else None
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise MaintenanceError("project_identity_required")
        raise MaintenanceError("storage_migration_required")
    return None, pinned
