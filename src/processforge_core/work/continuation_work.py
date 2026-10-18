"""Existing exact Continuation Work binding reads and validation modes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol


class ContinuationWorkRecords(Protocol):
    def _load_run(self, run_id: str) -> dict: ...
    def _load_assignment(self, assignment_id: str) -> dict: ...
    def _effective_process(self, run: dict) -> tuple[dict, str]: ...
    def _assignment_path(self, assignment_id: str) -> Path: ...
    def _run_path(self, run_id: str) -> Path: ...
    def _context_check(self) -> dict: ...
    def state(self, *, run_id: str, assignment_id: str) -> dict: ...


class ContinuationResourceReads(Protocol):
    def _load(self, path: Path) -> dict: ...
    def _context(self, run_id: str, assignment_id: str, context_id: str) -> tuple[dict, list, dict]: ...
    def read(self, *, operation: str, run_id: str, assignment_id: str, context_id: str, resource_id: str) -> dict: ...


class ContinuationContractValidator(Protocol):
    def __call__(self, project_root: Path, path: Path, assignment: dict, capsule: dict,
                 *, check_sources: bool, require_ready: bool) -> dict: ...


@dataclass(frozen=True, kw_only=True)
class ContinuationWorkReadService:
    selector: Callable[[], Callable[[str], str]] = field(repr=False, compare=False)
    project_root: Callable[[], Path] = field(repr=False, compare=False)
    project_id: Callable[[], Callable[[Path], str]] = field(repr=False, compare=False)
    resources: Callable[[], ContinuationResourceReads] = field(repr=False, compare=False)
    work: Callable[[], ContinuationWorkRecords] = field(repr=False, compare=False)
    path_resolver: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    bounded_reader: Callable[[], Callable[[Path], bytes]] = field(repr=False, compare=False)
    writer_check: Callable[[], Callable[[dict], None]] = field(repr=False, compare=False)
    contract_validator: Callable[[], ContinuationContractValidator] = field(repr=False, compare=False)
    permission_readiness: Callable[[], Callable[[dict, dict], dict]] = field(repr=False, compare=False)
    scope_allows: Callable[[], Callable[[dict, str, str], bool]] = field(repr=False, compare=False)
    active_run_statuses: Callable[[], set[str]] = field(repr=False, compare=False)
    active_assignment_statuses: Callable[[], set[str]] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)

    def read(self, binding: dict, *, executable: bool = True, terminal: bool = False) -> tuple[dict, dict, dict, dict]:
        for key in ("run_id", "assignment_id", "context_id"):
            self.selector()(binding.get(key))
        if binding.get("project_id", self.project_id()(self.project_root())) != self.project_id()(self.project_root()):
            raise self.error()("work_project_mismatch")
        resources = self.resources()
        run = self.work()._load_run(binding["run_id"])
        assignment = self.work()._load_assignment(binding["assignment_id"])
        if not run or not assignment or assignment.get('run_id') != binding['run_id']:
            raise self.error()('work_not_found')
        capsule_path = self.path_resolver()('.pf/contexts/assignment-capsules/' + binding['assignment_id'] + '.capsule.yaml')
        capsule = resources._load(capsule_path)
        if executable:
            self.writer_check()({**binding, 'project_id': self.project_id()(self.project_root())})
            identity, bindings, _ = resources._context(binding["run_id"], binding["assignment_id"], binding["context_id"])
        else:
            # Operator cancellation needs intact identity, not executable sources or permissions.
            identity = {'context_id': capsule.get('capsule', {}).get('id'),
                        'context_checksum': 'sha256:' + hashlib.sha256(self.bounded_reader()(capsule_path)).hexdigest()}
            bindings = []
            if identity['context_id'] != binding['context_id'] or self.work()._effective_process(run)[1] != 'pinned':
                raise self.error()('work_context_mismatch')
        if binding.get("capsule_checksum", identity["context_checksum"]) != identity["context_checksum"]:
            raise self.error()("work_context_checksum_mismatch")
        if not terminal and (run.get("status") not in self.active_run_statuses() or assignment.get("status") not in self.active_assignment_statuses()):
            raise self.error()("work_is_terminal")
        validation = self.contract_validator()(self.project_root(), self.work()._assignment_path(assignment["id"]), assignment, capsule,
                                                 check_sources=executable, require_ready=executable)
        if validation.get("status") != "valid":
            raise self.error()(validation.get("reason", "execution_contract_invalid"))
        if executable:
            for pending in self.work()._run_path(run['id']).parent.glob('cancellation-*.yaml'):
                if not pending.with_suffix('.applied.json').is_file():
                    raise self.error()('cancellation_recovery_pending')
            if self.work()._context_check().get("status") not in {"fresh", "fresh_with_updates"}:
                raise self.error()("snapshot_not_fresh")
            contract = capsule["execution_contract"]
            permissions = self.permission_readiness()(contract["scope"], contract["assignment_intent"]["execution_mode"])
            if permissions["status"] != "ready":
                raise self.error()("work_scope_not_executable")
            for source in contract["required_sources"]:
                if source.get("required", True) and source.get("path") and not self.scope_allows()(contract["scope"], source["path"], "read"):
                    raise self.error()("required_source_scope_denied")
            for resource in bindings:
                result = resources.read(operation="resolve", run_id=binding["run_id"], assignment_id=binding["assignment_id"],
                                        context_id=binding["context_id"], resource_id=resource["id"])
                if result.get("status") != "ready":
                    raise self.error()(result.get("reason", "resource_unavailable"))
            state = self.work().state(run_id=run["id"], assignment_id=assignment["id"])
            if state.get("blockers"):
                raise self.error()(state["blockers"][0]["code"])
        else:
            state = self.work().state(run_id=run["id"], assignment_id=assignment["id"])
        bound = {"project_id": self.project_id()(self.project_root()), "run_id": run["id"], "assignment_id": assignment["id"],
                 "context_id": identity["context_id"], "capsule_checksum": identity["context_checksum"]}
        return run, assignment, bound, state

