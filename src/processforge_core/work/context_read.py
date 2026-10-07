"""Internal live context read scenario with explicit compatibility callbacks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Callable

from ..request_scope import safe_load

__all__ = ()


@dataclass(frozen=True)
class WorkContextReadService:
    flow_root: Callable[[], Path]
    assignment_path: Callable[[str], Path]
    validate_contract: Callable[[Path, dict[str, Any], dict[str, Any]], dict[str, Any]]
    normalize_assignment: Callable[[Path, dict[str, Any]], dict[str, Any]]

    def validation(self, assignment: dict[str, Any]) -> dict[str, Any]:
        from .context import stage_view
        import yaml

        path = self.flow_root() / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        if not path.is_file():
            if (assignment.get("process_execution") or {}).get("assignment_capsule"):
                return {"status": "blocked", "reason": "work_context_unavailable"}
            return {"status": "legacy", "reason": "legacy_contract_incomplete"}
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(self.flow_root().resolve()) or path.stat().st_size > 2 * 1024 * 1024:
                return {"status": "blocked", "reason": "execution_contract_invalid"}
            raw = path.read_bytes()
            if len(raw) > 2 * 1024 * 1024:
                return {"status": "blocked", "reason": "execution_contract_invalid"}
            capsule = safe_load(raw.decode("utf-8-sig"))
            expected = (assignment.get("process_execution") or {}).get("assignment_capsule_checksum")
            if expected and expected != "sha256:" + hashlib.sha256(raw).hexdigest():
                return {"status": "blocked", "reason": "immutable_context_changed"}
            if "execution_contract" not in capsule:
                return {"status": "legacy", "reason": "legacy_contract_incomplete"}
            result = self.validate_contract(self.assignment_path(assignment["id"]), assignment, capsule)
            if result.get("status") == "valid":
                result["stage_view"] = stage_view(capsule, assignment)
            return result
        except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError, UnicodeError):
            return {"status": "blocked", "reason": "execution_contract_invalid"}

    def normalized_assignment(self, assignment: dict[str, Any]) -> dict[str, Any]:
        return self.normalize_assignment(self.assignment_path(assignment['id']), assignment)
