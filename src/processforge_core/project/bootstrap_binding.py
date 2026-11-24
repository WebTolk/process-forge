"""Read and validate the project and Workplace binding for bootstrap."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..maintenance.contracts import MaintenanceError
from ..maintenance.fresh_project import _receipt
from ..maintenance.project_event_owner import INERT_LEGACY_PROJECT_TEMPLATE
from ..maintenance.storage_migration import _safe
from .metadata import PROJECT_FLOW_ROOT

_DOCUMENTS = YamlDocumentReader(fallback=_parse_simple_yaml)


@dataclass(frozen=True)
class ProjectBootstrapBinding:
    """Receipt, owner and Workplace route selected for project bootstrap."""

    receipt: dict[str, Any] | None
    project_id: str
    workplace_root: Path | None


class ProjectBootstrapBindingReader:
    """Read the binding used by bootstrap preflight and the guarded reread."""

    def read(
        self,
        project_root: Path,
        proposed_files: Mapping[Path, str],
        *,
        workplace_manifest: Path | str | None,
        force: bool,
        repair: bool,
    ) -> ProjectBootstrapBinding:
        """Check live and proposed binding files without opening or writing stores."""
        flow = project_root / PROJECT_FLOW_ROOT
        try:
            receipt = _receipt(project_root)
        except (TypeError, ValueError) as error:
            raise MaintenanceError("storage_fresh_receipt_invalid") from error

        def read_manifest(path: Path, *, planned: bool = False) -> dict[str, Any]:
            if planned and path in proposed_files:
                value = _load_proposed_manifest(proposed_files[path])
            else:
                value = _DOCUMENTS.load(path)
            if not isinstance(value, dict) or "__yaml_error__" in value:
                raise MaintenanceError("storage_configuration_invalid")
            return value

        manifest_path = _safe(flow / "process-forge.yaml")
        local_path = _safe(flow / "process-forge.local.yaml")
        has_manifest, has_local = manifest_path.exists(), local_path.exists()
        inert_template = (
            has_manifest
            and not has_local
            and force
            and not repair
            and receipt is None
            and manifest_path.stat().st_size == len(INERT_LEGACY_PROJECT_TEMPLATE)
            and manifest_path.read_bytes() == INERT_LEGACY_PROJECT_TEMPLATE
        )
        current_owner = (
            _project_id(read_manifest(manifest_path))
            if has_manifest and not inert_template
            else None
        )
        proposed_owner = (
            _project_id(read_manifest(manifest_path, planned=True))
            if force or current_owner is None
            else current_owner
        )

        current_reference = _workplace_reference(
            project_root, read_manifest(local_path)
        )
        proposed_reference = (
            _workplace_reference(project_root, read_manifest(local_path, planned=True))
            if force or not has_local
            else current_reference
        )
        if repair:
            # A repair proposal must agree with the surviving half of the binding.
            if (
                has_manifest
                and not has_local
                and current_owner
                != _project_id(read_manifest(manifest_path, planned=True))
            ):
                raise MaintenanceError("storage_enrollment_conflict")
            if (
                has_local
                and not has_manifest
                and current_reference
                != _workplace_reference(
                    project_root, read_manifest(local_path, planned=True)
                )
            ):
                raise MaintenanceError("storage_enrollment_conflict")

        workplace = (
            Path(workplace_manifest).parent if workplace_manifest is not None else None
        )
        if proposed_reference is not None and (
            repair or (receipt is None and has_local and not force)
        ):
            workplace = proposed_reference.parent
        expected = workplace / "workplace.yaml" if workplace is not None else None

        if receipt is not None:
            if current_owner is not None and proposed_owner != current_owner:
                raise MaintenanceError("storage_fresh_target_conflict")
            if receipt["domains"] is not None and (
                current_owner is None
                or proposed_owner != receipt["project_id"]
                or receipt["workplace"] != str(workplace or "")
            ):
                raise MaintenanceError("storage_fresh_target_conflict")
            if (
                current_reference is not None
                and current_reference != proposed_reference
            ):
                raise MaintenanceError("storage_enrollment_conflict")
        if proposed_reference is not None and proposed_reference != expected:
            raise MaintenanceError("storage_enrollment_conflict")

        return ProjectBootstrapBinding(receipt, proposed_owner, workplace)


def _load_proposed_manifest(text: str) -> Any:
    try:
        import yaml
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise MaintenanceError("storage_configuration_invalid") from error


def _project_id(manifest: dict[str, Any]) -> str:
    section = manifest.get("project")
    value = section.get("id") if isinstance(section, dict) else None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise MaintenanceError("project_identity_required")
    return value


def _workplace_reference(project_root: Path, local: dict[str, Any]) -> Path | None:
    section = local.get("workplace", {})
    if not isinstance(section, dict):
        raise MaintenanceError("storage_configuration_invalid")
    value = section.get("manifest")
    if not value:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise MaintenanceError("storage_configuration_invalid")
    declared = Path(value).expanduser()
    return declared if declared.is_absolute() else (project_root / declared).resolve()
