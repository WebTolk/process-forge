"""Existing two-phase metadata verification and Work material reads."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

if TYPE_CHECKING:
    from .resource_context import WorkResourceErrorFactory
    from .resource_declarations import ResourceDeclarationPolicy
    from .resource_material import MaterialBudget


class WorkMaterialCapture(Protocol):
    def __call__(
        self, row: dict[str, Any], root: Path, reference: dict[str, Any], *,
        include_content: bool, budget: MaterialBudget,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...


@dataclass(frozen=True, kw_only=True)
class WorkMaterialReadService:
    project_root: Callable[[], Path] = field(repr=False, compare=False)
    workplace_root: Callable[[], Path | None] = field(repr=False, compare=False)
    declarations: Callable[[], ResourceDeclarationPolicy] = field(repr=False, compare=False)
    metadata: Callable[[], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = field(repr=False, compare=False)
    fingerprint: Callable[[], Callable[[Any], str]] = field(repr=False, compare=False)
    root_resolver: Callable[[], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]] = field(repr=False, compare=False)
    material_capture: Callable[[], WorkMaterialCapture] = field(repr=False, compare=False)
    budget: Callable[[], Callable[[], MaterialBudget]] = field(repr=False, compare=False)
    error: Callable[[], WorkResourceErrorFactory] = field(repr=False, compare=False)

    def read(self, operation: str, bindings: list[dict[str, Any]], rows: dict[str, dict[str, Any]],
             identity: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        # Authorization and metadata checks for the whole requested set precede any material read.
        for binding in bindings:
            identifier = binding["id"]
            if identifier not in rows or str(rows[identifier].get("status") or "available") in {"disabled", "denied", "missing", "revoked"}:
                raise self.error()("resource_access_revoked", resource_id=identifier)
            if binding.get("status") != "available":
                raise self.error()(str(binding.get("reason") or "resource_material_unavailable"), resource_id=identifier)
            reference = self.declarations().portable_reference(rows[identifier])
            if self.fingerprint()(self.metadata()(rows[identifier], reference)) != binding.get("metadata_fingerprint"):
                raise self.error()("resource_generation_changed", resource_id=identifier)
        documents, provenances, verified = [], [], []
        budget = self.budget()()
        for binding in bindings:
            root, reference = self.root_resolver()(self.project_root(), self.workplace_root(), rows[binding["id"]])
            current, docs = self.material_capture()(rows[binding["id"]], root, reference, include_content=operation == "search", budget=budget)
            if any(current.get(key) != binding.get(key) for key in ("generation", "metadata_fingerprint", "material_fingerprint", "material_kind", "manifest")):
                raise self.error()("resource_material_changed", resource_id=binding["id"])
            provenance = {**identity, "resource_id": binding["id"], **{key: binding[key] for key in ("generation", "metadata_fingerprint", "material_fingerprint", "material_kind")}}
            provenances.append(provenance)
            verified.append({**copy.deepcopy(binding), "local_root": str(root.resolve()),
                             "navigation": "metadata_only" if binding["material_kind"] != "fulltext" else "verified_declared_material",
                             "resource_provenance": provenance})
            documents.extend({**doc, "resource_id": binding["id"], "resource_provenance": provenance} for doc in docs)
        return documents, provenances, verified
