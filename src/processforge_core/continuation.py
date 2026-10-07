"""Explicit continuation of pinned Work; waiting records never grant access."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import yaml

from .prepared.input import bounded_read, local_file
from .process_execution import (ACTIVE_ASSIGNMENT_STATUSES, ACTIVE_RUN_STATUSES,
                                SAFE_ID_RE, ProcessExecutionService, canonical_fingerprint)
from .work.context import scope_allows, validate_execution_contract
from .work.resources import WorkResourceError, WorkResourceService


class ContinuationError(ValueError):
    pass


def permission_readiness(scope: dict, mode: dict) -> dict:
    actions = set(scope.get("allowed_actions") or []) - set(scope.get("forbidden_actions") or [])
    reads = scope.get("allowed_read_files") or scope.get("allowed_files") or []
    writes = scope.get("allowed_files") or []
    reasons = []
    if "read" not in actions or not reads:
        reasons.append("read_scope_missing")
    if mode.get("code_changes_allowed") and ("write_product" not in actions or not writes):
        reasons.append("product_write_scope_missing")
    if mode.get("kind") != "read_only" and mode.get("artifact_changes_allowed") and (not writes or not actions & {"write_product", "write_artifact"}):
        reasons.append("artifact_write_scope_missing")
    return {"status": "blocked" if reasons else "ready", "blockers": reasons,
            "allowed_actions": sorted(actions), "allowed_files": writes,
            "allowed_read_files": scope.get("allowed_read_files") or [],
            "remediation": "create_explicitly_scoped_successor" if reasons else "none"}


class ContinuationService:
    def __init__(self, project_root: Path, workplace_root: Path | None, core: Any):
        self.project = project_root.resolve()
        self.workplace, self.core = workplace_root, core
        self.work = ProcessExecutionService(self.project, workplace_root, core)
        self.flow = core.locate_flow_root(self.project)

    def request(self, operation: str, **args: Any) -> dict:
        try:
            if operation not in {"create", "status", "resume", "cancel_work"}:
                raise ContinuationError("invalid_operation")
            return getattr(self, operation)(**args)
        except (ContinuationError, WorkResourceError) as exc:
            return {"schema_version": 1, "kind": "pf.work.cancel" if operation == "cancel_work" else "pf.continuation." + operation,
                    "status": "blocked", "action": "blocked", "reason": getattr(exc, "code", str(exc))}
        except (OSError, ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError):
            return {"schema_version": 1, "kind": "pf.work.cancel" if operation == "cancel_work" else "pf.continuation." + operation,
                    "status": "blocked", "action": "blocked", "reason": "continuation_state_invalid"}

    def _id(self, value: str) -> str:
        if not isinstance(value, str) or not SAFE_ID_RE.fullmatch(value):
            raise ContinuationError("exact_selector_required")
        return value

    def _path(self, relative: str) -> Path:
        return local_file(self.project, relative)

    def _record_path(self, continuation_id: str) -> Path:
        return self._path(".pf/continuations/" + self._id(continuation_id) + ".yaml")

    def _load(self, path: Path) -> dict:
        if not path.exists():
            raise ContinuationError("continuation_not_found")
        data = yaml.safe_load(bounded_read(path, 2 * 1024 * 1024).decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise ContinuationError("continuation_state_invalid")
        return data

    def _validate_record(self, record: dict, continuation_id: str) -> None:
        if record.get('id') != continuation_id or record.get('status') not in {'waiting', 'ready', 'resumed'}:
            raise ContinuationError('continuation_not_resumable')
        if type(record.get('schema_version')) is not int or record['schema_version'] not in (1, 2):
            raise ContinuationError('continuation_version_unsupported')
        if record['schema_version'] == 2:
            binding = record.get('work')
            if not isinstance(binding, dict) or set(binding) != {'project_id', 'run_id', 'assignment_id', 'context_id', 'capsule_checksum'}:
                raise ContinuationError('continuation_binding_invalid')
            if not isinstance(binding['project_id'], str) or not binding['project_id'] or not re.fullmatch(r'sha256:[a-f0-9]{64}', str(binding['capsule_checksum'])):
                raise ContinuationError('continuation_binding_invalid')

    def _work(self, binding: dict, *, executable: bool = True, terminal: bool = False) -> tuple[dict, dict, dict, dict]:
        for key in ("run_id", "assignment_id", "context_id"):
            self._id(binding.get(key))
        if binding.get("project_id", self.core.project_id(self.project)) != self.core.project_id(self.project):
            raise ContinuationError("work_project_mismatch")
        resources = WorkResourceService(self.project, self.workplace, self.core)
        run = self.work._load_run(binding["run_id"])
        assignment = self.work._load_assignment(binding["assignment_id"])
        if not run or not assignment or assignment.get('run_id') != binding['run_id']:
            raise ContinuationError('work_not_found')
        capsule_path = self._path('.pf/contexts/assignment-capsules/' + binding['assignment_id'] + '.capsule.yaml')
        capsule = resources._load(capsule_path)
        if executable:
            self._writer_check({**binding, 'project_id': self.core.project_id(self.project)})
            identity, bindings, _ = resources._context(binding["run_id"], binding["assignment_id"], binding["context_id"])
        else:
            # Operator cancellation needs intact identity, not executable sources or permissions.
            identity = {'context_id': capsule.get('capsule', {}).get('id'),
                        'context_checksum': 'sha256:' + hashlib.sha256(bounded_read(capsule_path)).hexdigest()}
            bindings = []
            if identity['context_id'] != binding['context_id'] or self.work._effective_process(run)[1] != 'pinned':
                raise ContinuationError('work_context_mismatch')
        if binding.get("capsule_checksum", identity["context_checksum"]) != identity["context_checksum"]:
            raise ContinuationError("work_context_checksum_mismatch")
        if not terminal and (run.get("status") not in ACTIVE_RUN_STATUSES or assignment.get("status") not in ACTIVE_ASSIGNMENT_STATUSES):
            raise ContinuationError("work_is_terminal")
        validation = validate_execution_contract(self.project, self.work._assignment_path(assignment["id"]), assignment, capsule,
                                                 self.core, check_sources=executable, require_ready=executable)
        if validation.get("status") != "valid":
            raise ContinuationError(validation.get("reason", "execution_contract_invalid"))
        if executable:
            for pending in self.work._run_path(run['id']).parent.glob('cancellation-*.yaml'):
                if not pending.with_suffix('.applied.json').is_file():
                    raise ContinuationError('cancellation_recovery_pending')
            if self.work._context_check().get("status") not in {"fresh", "fresh_with_updates"}:
                raise ContinuationError("snapshot_not_fresh")
            contract = capsule["execution_contract"]
            permissions = permission_readiness(contract["scope"], contract["assignment_intent"]["execution_mode"])
            if permissions["status"] != "ready":
                raise ContinuationError("work_scope_not_executable")
            for source in contract["required_sources"]:
                if source.get("required", True) and source.get("path") and not scope_allows(contract["scope"], source["path"], "read"):
                    raise ContinuationError("required_source_scope_denied")
            for resource in bindings:
                result = resources.read(operation="resolve", run_id=binding["run_id"], assignment_id=binding["assignment_id"],
                                        context_id=binding["context_id"], resource_id=resource["id"])
                if result.get("status") != "ready":
                    raise ContinuationError(result.get("reason", "resource_unavailable"))
            state = self.work.state(run_id=run["id"], assignment_id=assignment["id"])
            if state.get("blockers"):
                raise ContinuationError(state["blockers"][0]["code"])
        else:
            state = self.work.state(run_id=run["id"], assignment_id=assignment["id"])
        bound = {"project_id": self.core.project_id(self.project), "run_id": run["id"], "assignment_id": assignment["id"],
                 "context_id": identity["context_id"], "capsule_checksum": identity["context_checksum"]}
        return run, assignment, bound, state

    def _waiting(self, record: dict) -> dict:
        waiting = record.get("waiting_for") or {}
        paths = waiting.get("expected_artifacts") or []
        if not isinstance(paths, list) or len(paths) > 128:
            raise ContinuationError("waiting_conditions_invalid")
        missing = []
        for path in paths:
            target = self._path(path)
            if not target.is_file():
                missing.append(path)
        handoff_id = waiting.get("handoff_id")
        handoff_ready = True
        if handoff_id:
            handoff = self._path(".pf/handoffs/" + self._id(handoff_id) + "/handoff.yaml")
            handoff_ready = handoff.is_file() and self._load(handoff).get("status") in {"returned", "finalized"}
        return {"status": "ready" if not missing and handoff_ready else "waiting", "missing_expected_artifacts": missing,
                "handoff_ready": handoff_ready}

    def create(self, *, continuation_id: str, run_id: str, assignment_id: str, context_id: str,
               expected_artifacts: list[str] | None = None, handoff_id: str = "", instruction: str = "",
               apply: bool = False, **unused: Any) -> dict:
        if unused:
            raise ContinuationError("invalid_arguments")
        path = self._record_path(continuation_id)
        self._id(run_id)
        with self.work._run_lock(run_id):
            run, assignment, binding, state = self._work(dict(run_id=run_id, assignment_id=assignment_id, context_id=context_id))
            record = {"schema_version": 2, "id": continuation_id, "work": binding,
                      "waiting_for": {"handoff_id": handoff_id, "expected_artifacts": expected_artifacts or []},
                      "resume": {"instruction": instruction}, "status": "waiting"}
            self._waiting(record)
            with self.core.registry_file_lock(path):
                if path.exists():
                    existing = self._load(path)
                    if any(existing.get(key) != record[key] for key in ("schema_version", "id", "work", "waiting_for", "resume")):
                        raise ContinuationError("continuation_exists_with_different_intent")
                    action = "existing"
                elif apply is True:
                    record["created_at"] = self.core.now_utc()
                    self.work._atomic_yaml(path, record)
                    action = "created"
                else:
                    action = "preview"
        return {"schema_version": 2, "kind": "pf.continuation.create", "status": "ready", "action": action,
                "continuation_id": continuation_id, "work": binding, "waiting": self._waiting(record), "stage": state["stage"]}

    def status(self, *, continuation_id: str = "") -> dict:
        if not continuation_id:
            if self.work._context_check().get("status") not in {"fresh", "fresh_with_updates"}:
                raise ContinuationError("snapshot_not_fresh")
            records = self.work._work_records(include_historical=False)
            candidates = [{k: row[k] for k in ("run_id", "assignment_id", "stage", "status")} for row in records[:20]]
            for row in candidates:
                capsule = self._load(self._path('.pf/contexts/assignment-capsules/' + self._id(row['assignment_id']) + '.capsule.yaml'))
                row["context_id"] = capsule.get('capsule', {}).get('id')
            return {"schema_version": 2, "kind": "pf.continuation.status", "status": "discovery",
                    "action": "choice_required" if len(records) > 1 else "candidate_available" if records else "not_found",
                    "candidates": candidates, "total": len(records), "selection_required": True}
        record = self._load(self._record_path(continuation_id))
        self._validate_record(record, continuation_id)
        waiting = self._waiting(record)
        if record.get("schema_version") == 1:
            return {"schema_version": 1, "kind": "pf.continuation.status", "status": waiting["status"], "waiting": waiting,
                    "continuation_id": continuation_id, "work_resumed": False, "work_readiness": "legacy_binding_required"}
        if record.get("schema_version") != 2:
            raise ContinuationError("continuation_version_unsupported")
        _, _, binding, state = self._work(record["work"])
        return {"schema_version": 2, "kind": "pf.continuation.status", "status": waiting["status"], "waiting": waiting,
                "continuation_id": continuation_id, "work": binding, "work_readiness": "ready", "work_state": state}

    def _selection_path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not session_id or len(session_id) > 256:
            raise ContinuationError("invalid_session")
        return self._path(".pf/continuations/selections/" + hashlib.sha256(session_id.encode()).hexdigest() + ".yaml")

    def selected(self, session_id: str) -> dict | None:
        try:
            return self._selected(session_id)
        except ContinuationError:
            raise
        except WorkResourceError as exc:
            raise ContinuationError(exc.code) from exc
        except (OSError, ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError) as exc:
            raise ContinuationError('selection_invalid') from exc

    def _selected(self, session_id: str) -> dict | None:
        if not session_id:
            return None
        path = self._selection_path(session_id)
        if not path.exists():
            return None
        receipt = self._load(path)
        if receipt.get("session_id") != session_id or receipt.get("schema_version") != 1:
            raise ContinuationError("selection_invalid")
        record = self._load(self._record_path(receipt["continuation_id"]))
        self._validate_record(record, receipt['continuation_id'])
        if record.get("work") != receipt.get("work") or record.get("status") == "cancelled":
            raise ContinuationError("selection_invalid")
        if self._waiting(record)['status'] != 'ready':
            raise ContinuationError('continuation_waiting')
        self._work(receipt["work"])
        return receipt["work"]

    def resume(self, *, continuation_id: str, session_id: str = "") -> dict:
        path = self._record_path(continuation_id)
        record = self._load(path)
        if record.get("schema_version") == 1:
            # Preserve old wait-only operation, but never imply a Work was selected.
            with self.core.registry_file_lock(path):
                record = self._load(path)
                result = self.status(continuation_id=continuation_id)
                if result["status"] != "ready":
                    raise ContinuationError("continuation_waiting")
                if record.get("status") != "resumed":
                    record.update(status="resumed", resumed_at=self.core.now_utc())
                    self.work._atomic_yaml(path, record)
                return {**result, "action": "legacy_wait_resumed", "work_resumed": False, "remediation": "create_explicit_v2_binding"}
        binding = record.get("work") or {}
        self._id(binding.get("run_id"))
        with self.work._run_lock(binding["run_id"]), self.core.registry_file_lock(path):
            result = self.status(continuation_id=continuation_id)
            if result["status"] != "ready":
                raise ContinuationError("continuation_waiting")
            record = self._load(path)
            if session_id:
                selection = self._selection_path(session_id)
                with self.core.registry_file_lock(selection):
                    receipt = {"schema_version": 1, "session_id": session_id, "continuation_id": continuation_id, "work": result["work"]}
                    existing = self._load(selection) if selection.exists() else {}
                    if any(existing.get(key) != value for key, value in receipt.items()):
                        receipt["selected_at"] = self.core.now_utc()
                        self.work._atomic_yaml(selection, receipt)
            if record.get("status") != "resumed":
                record.update(status="resumed", resumed_at=self.core.now_utc())
                try:
                    self.work._atomic_yaml(path, record)
                except OSError:
                    if not session_id:
                        raise
                    return {**result, "kind": "pf.continuation.resume", "action": "selection_committed",
                            "work_resumed": True, "selection": "session_bound", "marker_recovery_required": True,
                            "remediation": "retry_same_resume",
                            "selectors": {key: result["work"][key] for key in ("run_id", "assignment_id", "context_id")}}
            return {**result, "kind": "pf.continuation.resume", "action": "continued", "work_resumed": True,
                    "selection": "session_bound" if session_id else "explicit_selectors_required",
                    "selectors": {key: result["work"][key] for key in ("run_id", "assignment_id", "context_id")}}

    def _writer_check(self, binding: dict) -> None:
        status_path = self._path(f".pf/runtime/agent-runs/{binding['run_id']}/{binding['assignment_id']}/status.json")
        if status_path.exists():
            status = self._load(status_path)
            if status.get("status") not in {"completed", "failed", "timed_out", "cancelled", "collected"}:
                raise ContinuationError("worker_not_quiescent")
        if self.workplace:
            for path in self.core.workplace_agent_leases_dir(self.workplace).glob("*.yaml"):
                lease = self._load(path)
                scope = lease.get("scope") or {}
                if lease.get("status") == "active" and all(not scope.get(k) or scope[k] == binding[v] for k, v in
                        (("project_id", "project_id"), ("run_id", "run_id"), ("task_id", "assignment_id"))):
                    raise ContinuationError("active_lease")

    def cancel_work(self, *, run_id: str, assignment_id: str, context_id: str, capsule_checksum: str,
                    reason: str, evidence: list[str] | None = None, apply: bool = False) -> dict:
        self._id(run_id); self._id(assignment_id); self._id(context_id)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise ContinuationError("cancellation_reason_required")
        if not isinstance(capsule_checksum, str) or not re.fullmatch(r'sha256:[a-f0-9]{64}', capsule_checksum):
            raise ContinuationError("capsule_checksum_required")
        evidence = evidence or []
        if not isinstance(evidence, list) or len(evidence) > 128:
            raise ContinuationError("cancellation_evidence_invalid")
        for item in evidence:
            bounded_read(self._path(item))
        binding = dict(project_id=self.core.project_id(self.project), run_id=run_id, assignment_id=assignment_id,
                       context_id=context_id, capsule_checksum=capsule_checksum)
        path = self._path(f".pf/runs/{run_id}/cancellation-{assignment_id}.yaml")
        leases_lock = self.core.registry_file_lock(self.workplace / "runtime/agent-leases/registry") if self.workplace else nullcontext()
        worker_lock = self.core.worker_run_lifecycle_lock(self.project, run_id, assignment_id)
        with self.work._start_lock(), worker_lock, self.work._run_lock(run_id), leases_lock:
            if path.exists():
                intent = self._load(path)
                if intent.get("work") != binding or intent.get("reason") != reason or intent.get("evidence") != evidence:
                    raise ContinuationError("cancellation_intent_mismatch")
                if path.with_suffix(".applied.json").exists():
                    receipt = self._load(path.with_suffix(".applied.json"))
                    if receipt.get("checksum") != intent.get("checksum") or intent.get("checksum") != canonical_fingerprint({k: v for k, v in intent.items() if k != "checksum"}):
                        raise ContinuationError("cancellation_intent_invalid")
                    run, assignment, _, state = self._work(binding, executable=False, terminal=True)
                    if assignment.get("status") != "cancelled":
                        raise ContinuationError("cancellation_concurrent_change")
                    return {"schema_version": 1, "kind": "pf.work.cancel", "status": "cancelled", "action": "cancelled",
                            "work": binding, "run_status": run["status"], "work_state": state, "already_applied": True}
            else:
                for pending in path.parent.glob('cancellation-*.yaml'):
                    if not pending.with_suffix('.applied.json').is_file():
                        raise ContinuationError('cancellation_recovery_pending')
                run, assignment, binding, _ = self._work(binding, executable=False)
                if self.work._load_completion_intent(run, assignment) != (None, None):
                    raise ContinuationError("completion_recovery_pending")
                self._writer_check(binding)
                intent = {"schema_version": 1, "kind": "pf.work.cancellation", "work": binding,
                          "reason": reason, "evidence": evidence, "cancelled_at": self.core.now_utc(),
                          "before_run": run, "before_assignment": assignment}
                intent["checksum"] = canonical_fingerprint(intent)
                if apply is True:
                    self.work._atomic_yaml(path, intent)
            if apply is not True:
                return {"schema_version": 1, "kind": "pf.work.cancel", "status": "ready", "action": "preview", "work": binding}
            return self._replay_cancel(path, intent)

    def _replay_cancel(self, path: Path, intent: dict) -> dict:
        if intent.get("checksum") != canonical_fingerprint({k: v for k, v in intent.items() if k != "checksum"}):
            raise ContinuationError("cancellation_intent_invalid")
        binding = intent["work"]
        self._writer_check(binding)
        before_run, before_assignment = intent["before_run"], intent["before_assignment"]
        # Recheck the capsule even on a partially applied retry.
        self._work(binding, executable=False, terminal=True)
        run, assignment = copy.deepcopy(before_run), copy.deepcopy(before_assignment)
        assignment.update(status="cancelled", updated_at=intent["cancelled_at"])
        assignment["result"] = {"status": "cancelled", "summary": intent["reason"], "artifacts": intent["evidence"]}
        self.work._set_run_task_status(run, assignment["id"], "cancelled")
        if all(t.get("status") in {"done", "completed", "cancelled", "failed"} for t in run["tasks"]):
            run["status"] = "cancelled"
        run["updated_at"] = intent["cancelled_at"]
        for target, previous, after in ((self.work._assignment_path(assignment["id"]), before_assignment, assignment),
                                        (self.work._run_path(run["id"]), before_run, run)):
            current = self._load(target)
            if current not in (previous, after):
                raise ContinuationError("cancellation_concurrent_change")
        for target, after in ((self.work._assignment_path(assignment["id"]), assignment), (self.work._run_path(run["id"]), run)):
            if self._load(target) != after:
                self.work._atomic_yaml(target, after)
        self.work._write_task_index(run)
        events = ["task.cancelled"] + (["run.cancelled"] if run["status"] == "cancelled" else [])
        for event in events:
            event_id = "evt_" + hashlib.sha256((intent["checksum"] + event).encode()).hexdigest()[:32]
            present = any(not error and isinstance(value, dict) and self.core.event_id_value(value) == event_id
                          for _line, value, error in self.core.iter_ndjson(self.core.event_runtime_paths(self.project)[0]))
            if not present:
                self.work._emit(event, run, assignment, assignment["stage"], outcome="cancelled", event_id=event_id)
        state = self.work.state(run_id=run["id"], assignment_id=assignment["id"])
        self.work._write_projection(state)
        done = path.with_suffix(".applied.json")
        if not done.exists():
            self.work._atomic_text(done, json.dumps({"checksum": intent["checksum"], "status": "applied"}) + "\n")
        return {"schema_version": 1, "kind": "pf.work.cancel", "status": "cancelled", "action": "cancelled",
                "work": binding, "run_status": run["status"], "work_state": state}
