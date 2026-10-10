"""Existing initial material binding assembly for capsule creation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

if TYPE_CHECKING:
    from .resource_declarations import ResourceDeclarationPolicy
    from .resource_material import MaterialBudget, MaterialError
    from .resources import WorkResourceError


class BindingMaterialCapture(Protocol):
    def __call__(
        self, row: dict[str, Any], root: Path, reference: dict[str, Any], *, budget: MaterialBudget,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]: ...


@dataclass(frozen=True, kw_only=True)
class ResourceBindingBuilder:
    limits: Callable[[], dict[str, int]] = field(repr=False, compare=False)
    budget: Callable[[], Callable[[], MaterialBudget]] = field(repr=False, compare=False)
    declarations: Callable[[], ResourceDeclarationPolicy] = field(repr=False, compare=False)
    snapshot: Callable[[], Callable[[Path], dict[str, Any]]] = field(repr=False, compare=False)
    root_resolver: Callable[[], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]] = field(repr=False, compare=False)
    material_capture: Callable[[], BindingMaterialCapture] = field(repr=False, compare=False)
    work_error: Callable[[], type[WorkResourceError]] = field(repr=False, compare=False)
    material_error: Callable[[], type[MaterialError]] = field(repr=False, compare=False)

    def build(self, project: Path, workplace: Path | None, selected_ids: list[str]) -> dict[str, Any]:
        """Pin new material only at capsule creation; never migrate a read request."""

        result: dict[str, Any] = {"schema_version": 1, "resources": [], "limits": dict(self.limits())}
        budget = self.budget()()
        try:
            identifiers = self.declarations().identifiers(selected_ids, "resource_scope_invalid")
            rows = self.declarations().grant_rows(self.snapshot()(project))
        except self.work_error() as exc:
            return {**result, "status": "unavailable", "reason": exc.code}
        for identifier in identifiers:
            try:
                if identifier not in rows:
                    raise self.work_error()("resource_access_revoked")
                row = rows[identifier]
                if str(row.get("status") or "available") in {"disabled", "denied", "missing", "revoked"}:
                    raise self.work_error()("resource_access_revoked")
                root, reference = self.root_resolver()(project, workplace, row)
                binding, _ = self.material_capture()(row, root, reference, budget=budget)
            except (self.material_error(), self.work_error()) as exc:
                binding = {"id": identifier, "status": "unavailable", "reason": exc.code}
            except (OSError, ValueError, RuntimeError, SystemExit):
                binding = {"id": identifier, "status": "unavailable", "reason": "resource_material_unavailable"}
            result["resources"].append(binding)
        result["status"] = "available" if all(item["status"] == "available" for item in result["resources"]) else "unavailable"
        return result
