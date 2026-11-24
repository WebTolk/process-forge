"""Binding facts and writer serialization for the selected project event journal."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

from ..project.metadata import ProjectMetadataReader
from ..runtime.execution_admission import registry_file_lock
from .contracts import MaintenanceError
from .storage_migration import _safe

_EVENT_TARGET = "runtime/events/events.sqlite3"
INERT_LEGACY_PROJECT_TEMPLATE = b"schema_version: 1\n"


@dataclass(frozen=True)
class ProjectEventBinding:
    """The project, explicit owner and physical routes selected by the caller."""

    project_root: Path
    project_id: str
    workplace_manifest: Path
    event_target: Path


def project_event_binding_path(project_root: Path) -> Path:
    """Return the registry lock key shared by all writers for this physical root."""
    root = project_root.resolve(strict=True)
    flow = _safe(ProjectMetadataReader(root).flow_root())
    if not flow.is_dir():
        raise MaintenanceError("storage_enrollment_conflict")
    return _safe(flow / "runtime/project-event-owner")


def read_project_event_binding(project_root: Path) -> ProjectEventBinding:
    """Read live binding facts without taking admission or opening SQLite."""
    try:
        root = project_root.resolve(strict=True)
        metadata = ProjectMetadataReader(root)
        flow = metadata.flow_root()
        _safe(flow / "process-forge.yaml")
        _safe(flow / "process-forge.local.yaml")
        project = metadata.manifest().get("project")
        project_id = project.get("id") if isinstance(project, dict) else None
        if (
            not isinstance(project_id, str)
            or not project_id.strip()
            or "\x00" in project_id
        ):
            raise MaintenanceError("storage_enrollment_conflict")

        local = metadata.documents.load(flow / "process-forge.local.yaml")
        workplace = local.get("workplace")
        reference = workplace.get("manifest") if isinstance(workplace, dict) else None
        if not isinstance(reference, str) or not reference.strip():
            raise MaintenanceError("storage_enrollment_conflict")
        manifest = (root / Path(reference).expanduser()).resolve(strict=True)
        if manifest.name != "workplace.yaml" or not _safe(manifest).is_file():
            raise MaintenanceError("storage_enrollment_conflict")

        event_target = _safe(flow / _EVENT_TARGET)
        if not event_target.is_file():
            raise MaintenanceError("storage_enrollment_conflict")
    except (OSError, RuntimeError, ValueError) as error:
        if (
            isinstance(error, MaintenanceError)
            and error.code == "storage_enrollment_conflict"
        ):
            raise
        raise MaintenanceError("storage_enrollment_conflict") from error
    return ProjectEventBinding(root, project_id, manifest, event_target)


def require_project_event_binding(expected: ProjectEventBinding) -> None:
    """Refuse a changed selection while the caller retains the binding guard."""
    if read_project_event_binding(expected.project_root) != expected:
        raise MaintenanceError("storage_enrollment_conflict")


@contextmanager
def project_event_binding_writer_guard(project_root: Path) -> Iterator[None]:
    """Wait for the binding guard after the writer has established its flow root."""
    with ExitStack() as stack:
        try:
            path = project_event_binding_path(project_root)
            stack.enter_context(registry_file_lock(path))
        except SystemExit as error:
            if getattr(error, "registry_lock_reason", None) != "contention_timeout":
                raise
            raise MaintenanceError("storage_project_event_maintenance_busy") from error
        except OSError as error:
            raise MaintenanceError("storage_activity_unknown") from error
        yield
