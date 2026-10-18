"""Live context reads with concrete Core document and contract inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from ..common.request_scope import safe_load
from .context_documents import ContextContractInputs

__all__ = ()


@dataclass(frozen=True)
class WorkContextReadService:
    project_root: Path
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    @property
    def flow_root(self) -> Path:
        return self.inputs.locate_flow_root(self.project_root)

    def validation(self, assignment: dict[str, Any]) -> dict[str, Any]:
        from .context import stage_view, validate_execution_contract
        import yaml

        path = self.flow_root / "contexts" / "assignment-capsules" / f"{assignment['id']}.capsule.yaml"
        if not path.is_file():
            if (assignment.get("process_execution") or {}).get("assignment_capsule"):
                return {"status": "blocked", "reason": "work_context_unavailable"}
            return {"status": "legacy", "reason": "legacy_contract_incomplete"}
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(self.flow_root.resolve()) or path.stat().st_size > 2 * 1024 * 1024:
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
            result = validate_execution_contract(self.project_root, self.inputs.assignment_path(self.project_root, assignment["id"]),
                                                 assignment, capsule, self.inputs, check_sources=False)
            if result.get("status") == "valid":
                result["stage_view"] = stage_view(capsule, assignment)
            return result
        except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError, UnicodeError):
            return {"status": "blocked", "reason": "execution_contract_invalid"}

    def normalized_assignment(self, assignment: dict[str, Any]) -> dict[str, Any]:
        from .context import normalized_assignment_contract

        return normalized_assignment_contract(self.project_root, self.inputs.assignment_path(self.project_root, assignment['id']),
                                              assignment, self.inputs)
