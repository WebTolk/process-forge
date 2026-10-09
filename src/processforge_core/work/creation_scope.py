"""Existing operator scope validation and assignment overlay."""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_SAFE_ID_RE = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")


@dataclass(frozen=True)
class CreationScopeService:
    project_root: Path
    normalizer: Callable[[], Callable[[Any], dict[str, Any]]] = field(kw_only=True, repr=False, compare=False)
    handoff_reader: Callable[[], Callable[[Path], bytes]] = field(kw_only=True, repr=False, compare=False)

    @staticmethod
    def validate(value: Any) -> dict[str, Any]:
        """Validate explicit local-operator input; never infer grants from an objective."""
        from .context import ContextContractError

        fields = {"allowed_files", "allowed_read_files", "forbidden_files", "allowed_actions",
                  "forbidden_actions", "required_sources", "required_outputs", "expected_report",
                  "execution_mode", "ownership"}
        if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
                or value["schema_version"] != 1 or set(value) - {"schema_version", "assignment", "predecessor", "predecessor_handoff"}
                or not isinstance(value.get("assignment"), dict) or set(value["assignment"]) - fields):
            raise ContextContractError("work_scope_invalid")
        result = copy.deepcopy(value)
        assignment = result["assignment"]
        for key in fields - {"required_outputs", "expected_report", "execution_mode", "ownership"}:
            if key in assignment and (not isinstance(assignment[key], list) or len(assignment[key]) > 256
                    or any(not isinstance(item, str) or not item.strip() for item in assignment[key])):
                raise ContextContractError("work_scope_invalid")
        actions = {"read", "write_artifact", "write_product"}
        for key in ("allowed_actions", "forbidden_actions"):
            if set(assignment.get(key, [])) - actions:
                raise ContextContractError("work_scope_invalid")
        if set(assignment.get("allowed_actions", [])) & set(assignment.get("forbidden_actions", [])):
            raise ContextContractError("work_scope_conflict")
        if "execution_mode" in assignment and not isinstance(assignment["execution_mode"], (str, dict)):
            raise ContextContractError("work_scope_invalid")
        for key, allowed in (("ownership", {"owner_id", "role", "writer"}),
                             ("expected_report", {"artifact", "language", "format"})):
            if key in assignment and (not isinstance(assignment[key], dict) or set(assignment[key]) - allowed):
                raise ContextContractError("work_scope_invalid")
            if key in assignment and any(not isinstance(item, str) for name, item in assignment[key].items() if name != "writer"):
                raise ContextContractError("work_scope_invalid")
        outputs = assignment.get("required_outputs", [])
        if (not isinstance(outputs, list) or len(outputs) > 256
                or any(not isinstance(item, dict) or set(item) - {"id", "path", "type", "required"}
                       or not isinstance(item.get("id"), str) or not _SAFE_ID_RE.fullmatch(item["id"])
                       or not isinstance(item.get("path"), str) or not item["path"]
                       or ("required" in item and type(item["required"]) is not bool) for item in outputs)):
            raise ContextContractError("work_scope_invalid")
        if "predecessor" in result:
            prior = result["predecessor"]
            if (not isinstance(prior, dict) or set(prior) != {"run_id", "assignment_id", "capsule_checksum"}
                    or any(not isinstance(prior.get(key), str) or not _SAFE_ID_RE.fullmatch(prior[key])
                           for key in ("run_id", "assignment_id"))
                    or not isinstance(prior.get("capsule_checksum"), str)
                    or not re.fullmatch(r"sha256:[a-f0-9]{64}", prior["capsule_checksum"])):
                raise ContextContractError("work_scope_invalid")
        if "predecessor_handoff" in result:
            from .context import portable_path
            if not result.get("predecessor"):
                raise ContextContractError("work_scope_invalid")
            result["predecessor_handoff"] = portable_path(result["predecessor_handoff"])
            if not result["predecessor_handoff"].startswith(".pf/handoffs/"):
                raise ContextContractError("work_scope_invalid")
        return result


    def apply(self, assignment: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(assignment)
        result.update(copy.deepcopy(intent["assignment"]))
        if "execution_mode" in intent["assignment"]:
            result["execution_mode"] = self.normalizer()(result["execution_mode"])
        if intent.get("predecessor"):
            result.setdefault("coordination_requirements", {})["scope_predecessor"] = copy.deepcopy(intent["predecessor"])
        if intent.get("predecessor_handoff"):
            raw = self.handoff_reader()(self.project_root / intent["predecessor_handoff"])
            result.setdefault("coordination_requirements", {})["scope_handoff"] = {
                "path": intent["predecessor_handoff"], "checksum": "sha256:" + hashlib.sha256(raw).hexdigest()}
        return result

