"""Explicit continuation of pinned Work; waiting records never grant access."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ..prepared.input import bounded_read, local_file
from ..process_execution import (ACTIVE_ASSIGNMENT_STATUSES, ACTIVE_RUN_STATUSES,
                                SAFE_ID_RE, ProcessExecutionService, canonical_fingerprint)
from . import permissions as work_permissions
from .context import scope_allows, validate_execution_contract
from .resources import WorkResourceError, WorkResourceService


if TYPE_CHECKING:
    from .continuation_work import ContinuationContractValidator, ContinuationWorkReadService
    from .continuation_status import ContinuationStatusReadService
    from .continuation_read import ContinuationRecordReader


class ContinuationError(ValueError):
    pass


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

    def _record_reader(self) -> ContinuationRecordReader:
        from ..composition import build_continuation_record_reader

        return build_continuation_record_reader(
            path_resolver=lambda: self._path, selector=lambda: self._id,
            bounded_reader=lambda: bounded_read, yaml_loader=lambda: yaml.safe_load,
            error=lambda: ContinuationError,
            workplace=lambda: self.workplace, leases_directory=lambda: self.core.workplace_agent_leases_dir,
            control_loader=lambda: self._load,
        )

    def _record_path(self, continuation_id: str) -> Path:
        return self._record_reader().record_path(continuation_id)

    def _load(self, path: Path) -> dict:
        return self._record_reader().load(path)

    def _validate_record(self, record: dict, continuation_id: str) -> None:
        from .continuation_contract import ContinuationContractPolicy

        ContinuationContractPolicy(error=lambda: ContinuationError).validate_record(record, continuation_id)

    def _work_reader(self) -> ContinuationWorkReadService:
        from ..composition import build_continuation_work_reader

        def contract_validator() -> ContinuationContractValidator:
            validator = validate_execution_contract

            def validate(project_root: Path, path: Path, assignment: dict, capsule: dict,
                         *, check_sources: bool, require_ready: bool) -> dict:
                return validator(project_root, path, assignment, capsule, self.core,
                                 check_sources=check_sources, require_ready=require_ready)

            return validate

        return build_continuation_work_reader(
            selector=lambda: self._id, project_root=lambda: self.project, project_id=lambda: self.core.project_id,
            resources=lambda: WorkResourceService(self.project, self.workplace, self.core), work=lambda: self.work,
            path_resolver=lambda: self._path, bounded_reader=lambda: bounded_read, writer_check=lambda: self._writer_check,
            contract_validator=contract_validator, permission_readiness=lambda: work_permissions.permission_readiness,
            scope_allows=lambda: scope_allows, active_run_statuses=lambda: ACTIVE_RUN_STATUSES,
            active_assignment_statuses=lambda: ACTIVE_ASSIGNMENT_STATUSES, error=lambda: ContinuationError,
        )

    def _work(self, binding: dict, *, executable: bool = True, terminal: bool = False) -> tuple[dict, dict, dict, dict]:
        return self._work_reader().read(binding, executable=executable, terminal=terminal)

    def _status_reader(self) -> ContinuationStatusReadService:
        from ..composition import build_continuation_status_reader

        return build_continuation_status_reader(
            path_resolver=lambda: self._path, selector=lambda: self._id,
            load=lambda: self._load, record_path=lambda: self._record_path,
            selection_path=lambda: self._selection_path, validate_record=lambda: self._validate_record,
            waiting_reader=lambda: self._waiting, work_resolver=lambda: self._work,
            context_checker=lambda: self.work._context_check, work_records=lambda: self.work._work_records,
            error=lambda: ContinuationError,
        )

    def _waiting(self, record: dict) -> dict:
        return self._status_reader().waiting(record)

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
        return self._status_reader().status(continuation_id=continuation_id)

    def _selection_path(self, session_id: str) -> Path:
        return self._record_reader().selection_path(session_id)

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
        return self._status_reader().selected(session_id)

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
        self._record_reader().writer_check(binding)

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
