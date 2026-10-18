"""Existing continuation creation and resume publication with live dependencies."""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


class ContinuationBindingReader(Protocol):
    def __call__(self, binding: dict) -> tuple[dict, dict, dict, dict]: ...


class ContinuationStatusReader(Protocol):
    def __call__(self, *, continuation_id: str) -> dict: ...


class ContinuationDocumentWriter(Protocol):
    def __call__(self, path: Path, document: dict) -> Any: ...


@dataclass(frozen=True, kw_only=True)
class ContinuationPublicationService:
    record_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    selection_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    validate_id: Callable[[], Callable[[object], str]] = field(repr=False, compare=False)
    record_loader: Callable[[], Callable[[Path], dict]] = field(repr=False, compare=False)
    binding_reader: Callable[[], ContinuationBindingReader] = field(repr=False, compare=False)
    waiting_reader: Callable[[], Callable[[dict], dict]] = field(repr=False, compare=False)
    status_reader: Callable[[], ContinuationStatusReader] = field(repr=False, compare=False)
    run_lock: Callable[[], Callable[[str], AbstractContextManager[Any]]] = field(repr=False, compare=False)
    record_lock: Callable[[], Callable[[Path], AbstractContextManager[Any]]] = field(repr=False, compare=False)
    publish_document: Callable[[], ContinuationDocumentWriter] = field(repr=False, compare=False)
    clock: Callable[[], Callable[[], str]] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)

    def create(self, *, continuation_id: str, run_id: str, assignment_id: str, context_id: str,
               expected_artifacts: list[str] | None = None, handoff_id: str = "", instruction: str = "",
               apply: bool = False, **unused: Any) -> dict:
        if unused:
            raise self.error()("invalid_arguments")
        path = self.record_path()(continuation_id)
        self.validate_id()(run_id)
        with self.run_lock()(run_id):
            run, assignment, binding, state = self.binding_reader()(dict(run_id=run_id, assignment_id=assignment_id, context_id=context_id))
            record = {"schema_version": 2, "id": continuation_id, "work": binding,
                      "waiting_for": {"handoff_id": handoff_id, "expected_artifacts": expected_artifacts or []},
                      "resume": {"instruction": instruction}, "status": "waiting"}
            self.waiting_reader()(record)
            with self.record_lock()(path):
                if path.exists():
                    existing = self.record_loader()(path)
                    if any(existing.get(key) != record[key] for key in ("schema_version", "id", "work", "waiting_for", "resume")):
                        raise self.error()("continuation_exists_with_different_intent")
                    action = "existing"
                elif apply is True:
                    record["created_at"] = self.clock()()
                    self.publish_document()(path, record)
                    action = "created"
                else:
                    action = "preview"
        return {"schema_version": 2, "kind": "pf.continuation.create", "status": "ready", "action": action,
                "continuation_id": continuation_id, "work": binding, "waiting": self.waiting_reader()(record), "stage": state["stage"]}

    def resume(self, *, continuation_id: str, session_id: str = "") -> dict:
        path = self.record_path()(continuation_id)
        record = self.record_loader()(path)
        if record.get("schema_version") == 1:
            # Preserve old wait-only operation, but never imply a Work was selected.
            with self.record_lock()(path):
                record = self.record_loader()(path)
                result = self.status_reader()(continuation_id=continuation_id)
                if result["status"] != "ready":
                    raise self.error()("continuation_waiting")
                if record.get("status") != "resumed":
                    record.update(status="resumed", resumed_at=self.clock()())
                    self.publish_document()(path, record)
                return {**result, "action": "legacy_wait_resumed", "work_resumed": False, "remediation": "create_explicit_v2_binding"}
        binding = record.get("work") or {}
        self.validate_id()(binding.get("run_id"))
        with self.run_lock()(binding["run_id"]), self.record_lock()(path):
            result = self.status_reader()(continuation_id=continuation_id)
            if result["status"] != "ready":
                raise self.error()("continuation_waiting")
            record = self.record_loader()(path)
            if session_id:
                selection = self.selection_path()(session_id)
                with self.record_lock()(selection):
                    receipt = {"schema_version": 1, "session_id": session_id, "continuation_id": continuation_id, "work": result["work"]}
                    existing = self.record_loader()(selection) if selection.exists() else {}
                    if any(existing.get(key) != value for key, value in receipt.items()):
                        receipt["selected_at"] = self.clock()()
                        self.publish_document()(selection, receipt)
            if record.get("status") != "resumed":
                record.update(status="resumed", resumed_at=self.clock()())
                try:
                    self.publish_document()(path, record)
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
