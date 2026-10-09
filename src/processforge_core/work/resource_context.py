"""Existing pinned Work resource context reads and validation order."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Callable, Literal, Protocol, overload


class WorkControlDocumentReader(Protocol):
    @overload
    def __call__(self, path: Path, *, with_digest: Literal[False] = False) -> dict: ...

    @overload
    def __call__(self, path: Path, *, with_digest: Literal[True]) -> tuple[dict, str]: ...


class WorkContractValidator(Protocol):
    def __call__(self, project_root: Path, path: Path, assignment: dict, capsule: dict) -> dict: ...


class WorkResourceErrorFactory(Protocol):
    def __call__(self, code: str, **details: Any) -> Exception: ...


@dataclass(frozen=True, kw_only=True)
class WorkResourceContextReadService:
    project_root: Callable[[], Path] = field(repr=False, compare=False)
    selector_pattern: Callable[[], re.Pattern[str]] = field(repr=False, compare=False)
    flow_root: Callable[[], Callable[[Path], Path]] = field(repr=False, compare=False)
    project_id: Callable[[], Callable[[Path], str]] = field(repr=False, compare=False)
    load: Callable[[], WorkControlDocumentReader] = field(repr=False, compare=False)
    identifiers: Callable[[], Callable[[Any, str], list[str]]] = field(repr=False, compare=False)
    fingerprint: Callable[[], Callable[[dict], str]] = field(repr=False, compare=False)
    contract_validator: Callable[[], WorkContractValidator] = field(repr=False, compare=False)
    error: Callable[[], WorkResourceErrorFactory] = field(repr=False, compare=False)

    def read(self, run_id: Any, assignment_id: Any, context_id: Any) -> tuple[dict, list, dict]:
        if any(not isinstance(item, str) or not self.selector_pattern().fullmatch(item) for item in (run_id, assignment_id, context_id)):
            raise self.error()("work_selector_required")
        flow = self.flow_root()(self.project_root())
        run = self.load()(flow / "runs" / run_id / "run.yaml")
        assignment = self.load()(flow / "assignments" / f"{assignment_id}.yaml")
        if (run.get("id") != run_id or assignment.get("id") != assignment_id or assignment.get("run_id") != run_id
                or not any(isinstance(task, dict) and task.get("id") == assignment_id for task in run.get("tasks", []))):
            raise self.error()("work_identity_mismatch")
        pin = run.get("process_execution") or {}
        assignment_pin = assignment.get("process_execution") or {}
        expected_path = f".pf/contexts/assignment-capsules/{assignment_id}.capsule.yaml"
        if assignment_pin.get("assignment_capsule") != expected_path:
            raise self.error()("legacy_contract_incomplete", remediation="create_successor_work")
        path = flow / "contexts" / "assignment-capsules" / f"{assignment_id}.capsule.yaml"
        capsule, digest = self.load()(path, with_digest=True)
        if assignment_pin.get("assignment_capsule_checksum") != digest:
            raise self.error()("work_context_checksum_mismatch")
        if capsule.get("capsule", {}).get("id") != context_id:
            raise self.error()("work_context_mismatch")
        if (capsule.get("assignment", {}).get("id") != assignment_id
                or capsule.get("assignment", {}).get("run_id") != run_id
                or capsule.get("capsule", {}).get("assignment_id") != assignment_id
                or capsule.get("capsule", {}).get("immutable") is not True):
            raise self.error()("work_identity_mismatch")
        capsule_pin = capsule.get("process_execution") or {}
        definition = capsule_pin.get("definition")
        if not isinstance(definition, dict) or capsule_pin.get("process_fingerprint") != self.fingerprint()(definition):
            raise self.error()("process_pin_invalid")
        for key in ("process_id", "process_version", "process_fingerprint", "snapshot_id", "snapshot_checksum"):
            if not capsule_pin.get(key) or capsule_pin.get(key) != pin.get(key) or capsule_pin.get(key) != assignment_pin.get(key):
                raise self.error()("work_context_mismatch")
        if pin.get("definition") != definition:
            raise self.error()("process_pin_invalid")
        snapshot = capsule.get("context_snapshot") or {}
        if snapshot.get("id") != capsule_pin["snapshot_id"] or snapshot.get("sha256") != capsule_pin["snapshot_checksum"]:
            raise self.error()("work_context_mismatch")
        selected = self.identifiers()(capsule.get("context", {}).get("selected_resource_ids"), "resource_scope_invalid")
        # Older native pins preserve declaration order while their complete
        # contexts sort it. Grants are membership; validate each list before
        # comparing so duplicates and malformed pins still fail closed.
        selected_set = set(selected)
        if any(set(self.identifiers()(item.get("selected_resource_ids"), "resource_scope_invalid")) != selected_set
               for item in (capsule_pin, pin)):
            raise self.error()("resource_scope_invalid")
        bindings = capsule.get("resource_bindings")
        if not isinstance(bindings, dict):
            raise self.error()("legacy_contract_incomplete", remediation="create_successor_work")
        if type(bindings.get("schema_version")) is not int or bindings["schema_version"] != 1:
            raise self.error()("resource_binding_version_unsupported")
        resources = bindings.get("resources")
        if not isinstance(resources, list) or any(not isinstance(item, dict) for item in resources):
            raise self.error()("resource_binding_invalid")
        if set(self.identifiers()([item.get("id") for item in resources], "resource_binding_invalid")) != selected_set:
            raise self.error()("resource_binding_invalid")
        if "execution_contract" in capsule:
            validator = self.contract_validator()
            validation = validator(self.project_root(), flow / "assignments" / f"{assignment_id}.yaml", assignment, capsule)
            if validation["status"] != "valid":
                raise self.error()(validation.get("reason") or "execution_contract_invalid", remediation="create_successor_work")
            scope = capsule["execution_contract"]["scope"]
            if "read" not in scope["allowed_actions"] or "read" in scope["forbidden_actions"]:
                raise self.error()("scope_denied")
        stage = next((item for item in definition.get("stages", []) if isinstance(item, dict) and item.get("id") == assignment.get("stage")), None)
        if stage is None:
            raise self.error()("work_stage_invalid")
        subset = self.identifiers()(stage["resource_subset"], "stage_resource_subset_invalid") if "resource_subset" in stage else selected
        if not set(subset).issubset(selected):
            raise self.error()("stage_resource_subset_invalid")
        identity = {"project_id": self.project_id()(self.project_root()), "run_id": run_id,
                    "assignment_id": assignment_id, "context_id": context_id, "context_checksum": digest,
                    "snapshot_id": snapshot["id"], "snapshot_checksum": snapshot["sha256"], "stage_id": stage["id"]}
        return identity, [item for item in resources if item["id"] in subset], {"pinned": selected, "stage": subset}

