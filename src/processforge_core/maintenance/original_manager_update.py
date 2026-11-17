"""Bounded planning for a genuine 1.2.0 installation's original manager.

This service does not issue manager authority. Its caller is the original
trusted launcher, with an issuer-bound profile installed before its first
writer. A serialized plan or a new launcher cannot restore that authority.
"""

from __future__ import annotations

import io
import json
import zipfile
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping

from .contracts import MaintenanceError
from .file_update import checked_owned_paths
from .update import CORE_MANIFEST_NAME, CoreUpdateError, _build_plan, manifest_file_map

if TYPE_CHECKING:
    from pf_native_control import (
        LegacyManagedBoundary,
        LegacyUpdatePlan,
        ManagedSelection,
    )

PUBLIC_ZIP_SHA256 = "0cd5c1f48ca0e94ddf5b0298b774a3498baf20e5a64b84dd9c05bbc0f36a2880"
PUBLIC_SIDECAR_SHA256 = (
    "2881c62ff279c9d418d7bb88ad01a321817c1c7454ec03e10227d3f6791d40bd"
)


@dataclass(frozen=True)
class OriginalRelease:
    """Unchanged published bytes; this is provenance, never writer exclusion."""

    archive: bytes
    sidecar: bytes
    manifest: bytes
    members: Mapping[str, bytes]

    @classmethod
    def public_1_2(cls, archive: bytes, sidecar: bytes) -> OriginalRelease:
        from pf_native_control import digest, safe_path

        if (
            digest(archive) != PUBLIC_ZIP_SHA256
            or digest(sidecar) != PUBLIC_SIDECAR_SHA256
        ):
            raise CoreUpdateError("plan_blocked", "original public release pin differs")
        metadata = json.loads(sidecar)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            names = bundle.namelist()
            rows = {row["path"]: row for row in metadata["files"]}
            if len(names) != len(set(names)) or set(names) != set(rows):
                raise CoreUpdateError(
                    "plan_blocked", "original release membership differs"
                )
            members = {safe_path(name): bundle.read(name) for name in names}
        for name, raw in members.items():
            if rows[name]["sha256"] != digest(raw) or rows[name]["size"] != len(raw):
                raise CoreUpdateError("plan_blocked", "original release member differs")
        manifest = members[CORE_MANIFEST_NAME]
        old = json.loads(manifest)
        if old["version"] != "1.2.0" or set(manifest_file_map(old)) != (
            set(members) - {CORE_MANIFEST_NAME}
        ):
            raise CoreUpdateError("plan_blocked", "original Core manifest differs")
        for name, row in manifest_file_map(old).items():
            if row["sha256"] != digest(members[name]) or row["size"] != len(
                members[name]
            ):
                raise CoreUpdateError("plan_blocked", "original Core member differs")
        return cls(archive, sidecar, manifest, MappingProxyType(members))


_ROUTE: ContextVar[OriginalManagerUpdateService | None] = ContextVar(
    "original_manager_update_route", default=None
)


def current_original_manager(core_root: Path) -> OriginalManagerUpdateService | None:
    service = _ROUTE.get()
    if service is not None and service.boundary.root != core_root.resolve(strict=True):
        raise CoreUpdateError("plan_blocked", "original manager target differs")
    return service


class OriginalManagerUpdateService:
    """Use the existing delta planner; surrender mutation to the native leaf."""

    def __init__(
        self,
        boundary: LegacyManagedBoundary,
        release: OriginalRelease,
        *,
        selection: ManagedSelection,
    ) -> None:
        from pf_native_control import digest

        # Re-validate supplied values: construction of a Python value is not an issuer.
        accepted = OriginalRelease.public_1_2(release.archive, release.sidecar)
        if dict(boundary.archive) != dict(accepted.members):
            raise CoreUpdateError("plan_blocked", "manager original member map differs")
        with boundary.held():
            binding = boundary.original_profile()
        if binding["release_sha256"] != digest(accepted.archive) or binding[
            "sidecar_sha256"
        ] != digest(accepted.sidecar):
            raise CoreUpdateError("plan_blocked", "manager release binding differs")
        self.boundary = boundary
        self.release = accepted
        self.selection = selection

    def core_update(
        self,
        command: str,
        archive_path: Path,
        *,
        confirm: bool = False,
        workplace_root: Path | None = None,
    ) -> dict[str, Any]:
        """Fixed manager route to existing operations; no arbitrary callback."""
        from .update import apply_update, build_plan, resume_file_update

        token = _ROUTE.set(self)
        try:
            if command == "plan":
                return build_plan(
                    self.boundary.root, archive_path, workplace_root=workplace_root
                )
            if command == "apply":
                return apply_update(
                    self.boundary.root,
                    archive_path,
                    confirm=confirm,
                    workplace_root=workplace_root,
                )
            if command == "repair":
                return resume_file_update(
                    self.boundary.root,
                    archive_path,
                    confirm=confirm,
                    workplace_root=workplace_root,
                )
            raise CoreUpdateError(
                "plan_blocked", "unknown original manager update operation"
            )
        finally:
            _ROUTE.reset(token)

    def public_cli(
        self,
        command: str,
        archive_path: Path,
        *,
        confirm: bool = False,
        workplace_root: Path | None = None,
    ) -> int:
        """Fixed CLI dispatch inside the retained manager, including exit contract."""
        import argparse

        import processforge

        handlers = {
            "plan": processforge.command_core_update_plan,
            "apply": processforge.command_core_update_apply,
            "repair": processforge.command_core_update_repair,
        }
        if command not in handlers:
            raise CoreUpdateError(
                "plan_blocked", "unknown original manager CLI operation"
            )
        args = argparse.Namespace(
            core_root=str(self.boundary.root),
            archive=str(archive_path),
            confirm=confirm,
            force_local_modifications=False,
            workplace_root=str(workplace_root) if workplace_root else None,
            resume=True,
        )
        token = _ROUTE.set(self)
        try:
            return handlers[command](args)
        finally:
            _ROUTE.reset(token)

    def plan(
        self, archive_path: Path, *, workplace_root: Path | None = None
    ) -> LegacyUpdatePlan:
        from pf_native_control import (
            MAX_FILE,
            MAX_MANIFEST,
            MAX_TOTAL,
            LegacyUpdatePlan,
            NativeControlError,
            NativeUpdateError,
            _freeze_update_archive,
            _read_regular,
            _update_target,
            canonical_json,
            current_entry,
            digest,
            parse_manifest,
        )

        entry = current_entry()
        if entry is None or entry.publication is None or entry.image is None:
            raise CoreUpdateError("plan_blocked", "sealed external updater required")
        root = self.boundary.root
        if (
            root == entry.root
            or root in entry.root.parents
            or entry.root in root.parents
        ):
            raise CoreUpdateError(
                "plan_blocked", "installer and original roots overlap"
            )
        for variable, value in copy_context().items():
            if (
                variable.name
                in {
                    "pf_diagnostic",
                    "pf_configuration_operation",
                    "pf_storage_operation",
                }
                and value is not None
            ):
                raise CoreUpdateError(
                    "plan_blocked", "unwind operation scopes before update"
                )
        try:
            with self.boundary.held():
                try:
                    self.boundary.original_profile()
                    if self.boundary.facts()[0] != "proven":
                        raise NativeControlError()
                    if (
                        self.boundary.producer is not None
                        or self.boundary.update_plan is not None
                    ):
                        raise NativeControlError()
                    old_raw = _read_regular(root, CORE_MANIFEST_NAME, MAX_MANIFEST)
                    if old_raw != self.release.manifest:
                        raise NativeControlError()
                    old = json.loads(old_raw)
                    checked_owned_paths(root, old, installed_legacy=True)
                    with archive_path.open("rb") as stream:
                        archive_raw = stream.read(MAX_TOTAL + MAX_MANIFEST + 1)
                    if len(archive_raw) > MAX_TOTAL + MAX_MANIFEST:
                        raise NativeControlError()
                    with zipfile.ZipFile(io.BytesIO(archive_raw)) as bundle:
                        new = parse_manifest(bundle.read(CORE_MANIFEST_NAME))
                    checked_owned_paths(root, new)
                    frozen = _freeze_update_archive(archive_raw, {"new_manifest": new})

                    def read(relative: str) -> bytes | None:
                        target = _update_target(root, relative)
                        try:
                            target.lstat()
                        except FileNotFoundError:
                            return None
                        return _read_regular(root, relative, MAX_FILE)

                    # Resolve the effective root BEFORE the delta/package plan.
                    selection, configuration, workplace_root = (
                        resolve_original_selection(self.selection, workplace_root)
                    )

                    plan = _build_plan(
                        root,
                        archive_path,
                        workplace_root=workplace_root,
                        read_installed=lambda: old,
                        sha256_owned=lambda path: digest(
                            _read_regular(
                                root, path.relative_to(root).as_posix(), MAX_FILE
                            )
                        ),
                    )
                    if plan["blockers"] or plan["new_manifest"] != new:
                        raise NativeControlError()
                    if (plan.get("workplace_migration") or {}).get("operations"):
                        raise CoreUpdateError(
                            "plan_blocked",
                            "original bridge requires no package migration",
                        )
                    plan["_native_device_config_path"] = selection._device_config_path
                    plan["_native_configuration"] = configuration
                    profile = self.boundary.original_profile()
                    roots = [
                        selection.project,
                        selection.workplace,
                        selection._device_config_path,
                    ]
                    roots.extend(row[1] for row in selection.targets)
                    for value in roots:
                        if not value:
                            continue
                        physical = Path(value).resolve()
                        if (
                            physical == root
                            or root in physical.parents
                            or physical in root.parents
                        ):
                            raise CoreUpdateError(
                                "plan_blocked",
                                "active configuration or data overlaps Core",
                            )
                        if not any(
                            physical == Path(issued) or Path(issued) in physical.parents
                            for issued in profile["roots"]
                        ):
                            raise NativeControlError()
                    from ..work.context_documents import ContextContractInputs

                    inputs = [Path(selection._device_config_path)]
                    if selection.project:
                        flow = ContextContractInputs().locate_flow_root(
                            Path(selection.project)
                        )
                        inputs.extend(
                            [flow / "process-forge.yaml", flow / "configuration.yaml"]
                        )
                    if selection.workplace:
                        place = Path(selection.workplace)
                        inputs.extend(
                            [
                                place / "workplace.yaml",
                                place / "configuration.yaml",
                                place / "runtime/pf-runtime/service.json",
                                place / "data/accounting/identity.json",
                            ]
                        )
                    selection_files: dict[str, bytes | None] = {}
                    for path in inputs:
                        try:
                            path.lstat()
                        except FileNotFoundError:
                            selection_files[str(path)] = None
                        else:
                            selection_files[str(path)] = _read_regular(
                                path.parent, path.name, MAX_MANIFEST
                            )
                    paths = set(manifest_file_map(old)) | set(frozen.payload)
                    initial = {name: read(name) for name in sorted(paths)}
                    if _read_regular(root, CORE_MANIFEST_NAME, MAX_MANIFEST) != old_raw:
                        raise NativeControlError()
                    # Planner and frozen payload must describe the same original preimages.
                    changed = set(plan["changed"]) | set(plan["restored"])
                    for name, raw in frozen.payload.items():
                        if name in plan["added"]:
                            if initial[name] is not None:
                                raise NativeControlError()
                        elif name not in changed and initial[name] != raw:
                            raise NativeControlError()
                    prepared = LegacyUpdatePlan(
                        root=root,
                        archive=archive_raw,
                        frozen=frozen,
                        old_manifest=old_raw,
                        plan=canonical_json(plan),
                        initial=MappingProxyType(initial),
                        selection=selection,
                        profile=canonical_json(profile),
                        workplace=workplace_root,
                        selection_files=MappingProxyType(selection_files),
                    )
                    # Pin the same resolved inputs used by the delta planner,
                    # including changes between resolution and snapshot capture.
                    checked, checked_configuration, checked_workplace = (
                        resolve_original_selection(selection, workplace_root)
                    )
                    if (
                        checked != selection
                        or checked_configuration != configuration
                        or checked_workplace != workplace_root
                    ):
                        raise NativeControlError()
                    for selection_name, selected_raw in selection_files.items():
                        path = Path(selection_name)
                        if path.exists():
                            if (
                                _read_regular(path.parent, path.name, MAX_MANIFEST)
                                != selected_raw
                            ):
                                raise NativeControlError()
                        elif selected_raw is not None:
                            raise NativeControlError()
                    self.boundary.prepared_update = prepared
                    return prepared
                except (CoreUpdateError, MaintenanceError) as error:
                    raise NativeUpdateError(
                        error.code, getattr(error, "message", error.code)
                    ) from error
        except (
            NativeControlError,
            NativeUpdateError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            raise CoreUpdateError(
                "plan_blocked", "original manager plan is not qualified"
            ) from error

    def apply(
        self, archive_path: Path, *, confirm: bool, workplace_root: Path | None
    ) -> dict[str, Any]:
        from pf_native_control import (
            NativeControlError,
            NativeUpdateError,
            replace_legacy_core,
        )

        if not confirm:
            raise CoreUpdateError(
                "confirm_required", "core update apply requires explicit confirmation"
            )
        prepared = self.plan(archive_path, workplace_root=workplace_root)
        try:
            return replace_legacy_core(self.boundary, prepared)
        except NativeUpdateError as error:
            raise CoreUpdateError(error.code, error.message) from error
        except (NativeControlError, OSError, ValueError, KeyError, TypeError) as error:
            raise CoreUpdateError(
                "plan_blocked", "original manager apply refused"
            ) from error

    def resume(
        self, archive_path: Path, *, update_id: str, confirm: bool
    ) -> dict[str, Any]:
        from pf_native_control import (
            NativeControlError,
            NativeUpdateError,
            resume_legacy_core,
        )

        if not confirm:
            raise CoreUpdateError(
                "confirm_required", "core update repair requires explicit confirmation"
            )
        try:
            return resume_legacy_core(self.boundary, archive_path, update_id=update_id)
        except NativeUpdateError as error:
            raise CoreUpdateError(error.code, error.message) from error
        except (NativeControlError, OSError, ValueError, KeyError, TypeError) as error:
            raise CoreUpdateError(
                "plan_blocked", "original manager recovery refused"
            ) from error


def resolve_original_selection(
    expected: ManagedSelection, workplace_root: Path | None
) -> tuple[ManagedSelection, dict[str, Any], Path | None]:
    """Resolve project identity and the one effective Workplace without mutation."""
    from ..composition import _update_selection

    if not expected.project or not expected.owner:
        raise CoreUpdateError(
            "project_identity_required", "original upgrade requires an existing project"
        )
    with _update_selection(
        expected.document(),
        Path(expected._device_config_path),
        workplace_root=workplace_root,
    ) as (selected, configuration):
        return (
            selected,
            configuration,
            Path(selected.workplace) if selected.workplace else None,
        )


def finish_original_update(data: dict[str, Any]) -> dict[str, Any]:
    """Execute only in the fresh captured child, under its actual native lease."""
    from pf_native_control import NativeUpdateError, _update_json, _update_now

    from ..composition import build_configuration_provider, build_storage_migration_host
    from ..executions.composition import select_execution_storage

    project = (
        Path(data["selection"]["project"]) if data["selection"]["project"] else None
    )
    if project is None or not data["selection"].get("owner"):
        raise NativeUpdateError(
            "project_identity_required", "original upgrade requires an existing project"
        )
    workplace = Path(data["workplace_root"]) if data["workplace_root"] else None
    device = Path(data["device_config_path"])
    configuration = build_configuration_provider(
        project_root=project,
        workplace_root=workplace,
        device_config_path=device,
    )
    host = build_storage_migration_host(
        project_root=project,
        workplace_root=workplace,
        device_config_path=device,
        configuration=configuration,
    )
    migrated = host.service.ensure_ready(host.context, trigger="update")
    if migrated["blocked"]:
        raise NativeUpdateError(
            "storage_resume_required", "original upgrade storage migration is blocked"
        )
    selected = select_execution_storage(project, workplace, configuration=configuration)
    if (
        selected.repository is None
        or selected.repository.readiness().authority != "sql"
    ):
        raise NativeUpdateError(
            "execution_storage_not_ready", "SQL execution repository is unavailable"
        )
    progress = data["progress"]
    record = {
        "schema_version": 1,
        "update_id": progress["update_id"],
        "status": "applied",
        "applied_at": _update_now(),
        "maintenance_mode": "original_manager",
        "backup_dir": progress["backup_dir"],
        "backed_up": progress["backed_up"],
        "counts": progress["counts"],
        "archive_sha256": data["archive_sha256"],
        "storage_migration": migrated,
        "execution_authority": "sql",
        "failure_history": progress["failure_history"],
    }
    root = Path(data["root"])
    _update_json(root / "runtime/core-update/last-apply.json", record)
    (root / "runtime/core-update/in-progress.json").unlink()
    return record


def original_update_succeeded(result: dict[str, Any]) -> bool:
    """CLI success requires the validated fresh-child SQL/migration result."""
    migration = result.get("storage_migration")
    return (
        result.get("status") == "applied"
        and result.get("execution_authority") == "sql"
        and isinstance(migration, dict)
        and migration.get("blocked") is False
        and migration.get("status") == "ready"
    )
