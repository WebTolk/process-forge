"""Explicit continuation of pinned Work; waiting records never grant access."""
from __future__ import annotations

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
    from .continuation_publication import ContinuationPublicationService
    from .cancellation_replay import CancellationReplayService
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

    def _continuation_publisher(self) -> ContinuationPublicationService:
        from ..composition import build_continuation_publication_service

        return build_continuation_publication_service(
            record_path=lambda: self._record_path, selection_path=lambda: self._selection_path,
            validate_id=lambda: self._id, record_loader=lambda: self._load,
            binding_reader=lambda: self._work, waiting_reader=lambda: self._waiting,
            status_reader=lambda: self.status, run_lock=lambda: self.work._run_lock,
            record_lock=lambda: self.core.registry_file_lock,
            publish_document=lambda: self.work._atomic_yaml, clock=lambda: self.core.now_utc,
            error=lambda: ContinuationError,
        )

    def create(self, *, continuation_id: str, run_id: str, assignment_id: str, context_id: str,
               expected_artifacts: list[str] | None = None, handoff_id: str = "", instruction: str = "",
               apply: bool = False, **unused: Any) -> dict:
        return self._continuation_publisher().create(
            continuation_id=continuation_id, run_id=run_id, assignment_id=assignment_id,
            context_id=context_id, expected_artifacts=expected_artifacts, handoff_id=handoff_id,
            instruction=instruction, apply=apply, **unused,
        )

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
        return self._continuation_publisher().resume(continuation_id=continuation_id, session_id=session_id)

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

    def _cancellation_replayer(self) -> CancellationReplayService:
        from ..composition import build_cancellation_replay_service

        return build_cancellation_replay_service(
            fingerprint=lambda: canonical_fingerprint, error=lambda: ContinuationError,
            writer_check=lambda: self._writer_check, binding_reader=lambda: self._work,
            work=lambda: self.work, record_loader=lambda: self._load,
            project_root=lambda: self.project, event_paths=lambda: self.core.event_runtime_paths,
            event_reader=lambda: self.core.iter_ndjson, event_id=lambda: self.core.event_id_value,
        )

    def _replay_cancel(self, path: Path, intent: dict) -> dict:
        return self._cancellation_replayer().replay(path, intent)
