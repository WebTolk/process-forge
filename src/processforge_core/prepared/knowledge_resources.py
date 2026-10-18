"""Existing prepared knowledge material verification and grant provenance."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

if TYPE_CHECKING:
    from .resource_selection import PreparedResourceSelectionPolicy
    from ..work.resource_declarations import ResourceDeclarationPolicy
    from ..work.resource_material import MaterialBudget, MaterialError
    from ..work.resources import WorkResourceError


class PreparedKnowledgeRootResolver(Protocol):
    def __call__(self, project: Path, workplace: Path | None, row: dict[str, Any]) -> tuple[Path, dict[str, Any]]: ...


class PreparedKnowledgeMaterialCapture(Protocol):
    def __call__(
        self, row: dict[str, Any], root: Path, reference: dict[str, Any], *,
        include_content: bool = False, budget: MaterialBudget | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...


@dataclass(frozen=True, kw_only=True)
class PreparedKnowledgeResourceReader:
    selection: Callable[[], PreparedResourceSelectionPolicy] = field(repr=False, compare=False)
    declarations: Callable[[], ResourceDeclarationPolicy] = field(repr=False, compare=False)
    metadata: Callable[[], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = field(repr=False, compare=False)
    root_resolver: Callable[[], PreparedKnowledgeRootResolver] = field(repr=False, compare=False)
    material_capture: Callable[[], PreparedKnowledgeMaterialCapture] = field(repr=False, compare=False)
    budget: Callable[[], Callable[[], MaterialBudget]] = field(repr=False, compare=False)
    work_error: Callable[[], type[WorkResourceError]] = field(repr=False, compare=False)
    material_error: Callable[[], type[MaterialError]] = field(repr=False, compare=False)
    fail: Callable[[], Callable[[str], None]] = field(repr=False, compare=False)

    def read(self, project: Path, workplace: Path, requested: list[Any], capsule: dict[str, Any],
             pinned_snapshot: dict[str, Any], current_snapshot: dict[str, Any],
             snapshot_id: str, snapshot_checksum: str, selected_ids: list[str],
             stage_subset: list[str]) -> list[dict[str, Any]]:
        capsule_rows = capsule.get("resolved_resources")
        selection = self.selection()
        pinned_rows = selection.resolved_rows(pinned_snapshot, "knowledge_resources")
        if not isinstance(capsule_rows, list) or any(not isinstance(item, dict) for item in capsule_rows):
            self.fail()("resource_binding_invalid")
        if capsule_rows != pinned_rows:
            self.fail()("snapshot_generation_changed")
        bindings = selection.resource_bindings(capsule)
        try:
            current_rows = self.declarations().grant_rows(current_snapshot)
        except self.work_error() as exc:
            self.fail()(exc.code)
        ids = set(selected_ids)
        subset = set(stage_subset)
        unique_by_request: set[str] = set()
        grants: list[dict[str, Any]] = []
        budget = self.budget()()

        for request in requested:
            pinned = selection.unique_match(capsule_rows, request, "resource_not_in_snapshot")
            identifier = str(pinned.get("id") or pinned.get("resource_id") or "")
            if not identifier or identifier in unique_by_request:
                self.fail()("resource_scope_invalid")
            unique_by_request.add(identifier)
            if identifier not in ids:
                self.fail()("resource_not_selected")
            if identifier not in subset:
                self.fail()("resource_not_in_stage")
            binding = bindings.get(identifier)
            if binding is None or binding.get("status") != "available":
                self.fail()(str((binding or {}).get("reason") or "resource_material_unavailable"))

            row = selection.current_resource(current_rows, identifier)
            try:
                reference = self.declarations().portable_reference(row)
                descriptor = self.metadata()(row, reference)
                from ..work.resource_material import canonical_fingerprint

                metadata_fp = canonical_fingerprint(descriptor)
                if metadata_fp != binding.get("metadata_fingerprint"):
                    self.fail()("resource_generation_changed")
                root, resolved_reference = self.root_resolver()(project, workplace, row)
                actual, _ = self.material_capture()(row, root, resolved_reference, include_content=False, budget=budget)
            except self.work_error() as exc:
                self.fail()(exc.code)
            except self.material_error() as exc:
                self.fail()(exc.code)
            except (OSError, RuntimeError, SystemExit):
                self.fail()("resource_material_unavailable")

            if actual.get("metadata_fingerprint") != binding.get("metadata_fingerprint") or actual.get("generation") != binding.get("generation"):
                self.fail()("resource_generation_changed")
            if any(actual.get(key) != binding.get(key) for key in ("material_fingerprint", "material_kind", "manifest")):
                self.fail()("resource_material_changed")

            provenance = {
                "snapshot_id": snapshot_id,
                "snapshot_checksum": snapshot_checksum,
                "resource_id": identifier,
                "generation": actual["generation"],
                "metadata_fingerprint": actual["metadata_fingerprint"],
                "material_fingerprint": actual["material_fingerprint"],
            }
            material_kind = str(actual.get("material_kind") or "none")
            grant: dict[str, Any] = {
                "id": identifier,
                "path_ref": copy.deepcopy(resolved_reference),
                "metadata": descriptor,
                "material_kind": material_kind,
                "navigation": "verified_declared_material" if material_kind == "fulltext" else "metadata_only",
                "provenance": provenance,
                "manifest": copy.deepcopy(actual.get("manifest") or []),
                "resolution": ({"status": "resolved", "path": str(root.resolve())}
                               if material_kind == "fulltext" else {"status": "metadata_only"}),
            }
            grants.append(grant)
        return grants
