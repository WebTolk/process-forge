"""Existing Work cancellation journal replay with explicit live dependencies."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol


class CancellationWorkWriter(Protocol):
    def _set_run_task_status(self, run: dict, assignment_id: str, status: str) -> None: ...
    def _assignment_path(self, assignment_id: str) -> Path: ...
    def _run_path(self, run_id: str) -> Path: ...
    def _atomic_yaml(self, path: Path, document: dict) -> Any: ...
    def _write_task_index(self, run: dict) -> Any: ...
    def _emit(self, event: str, run: dict, assignment: dict, stage: str,
              *, outcome: str, event_id: str) -> Any: ...
    def state(self, *, run_id: str, assignment_id: str) -> dict: ...
    def _write_projection(self, state: dict) -> Any: ...
    def _atomic_text(self, path: Path, content: str) -> Any: ...


class CancellationBindingReader(Protocol):
    def __call__(self, binding: dict, *, executable: bool, terminal: bool) -> tuple[dict, dict, dict, dict]: ...


class CancellationEventReader(Protocol):
    def __call__(self, path: Path) -> Iterable[tuple[int, object, object]]: ...


@dataclass(frozen=True, kw_only=True)
class CancellationReplayService:
    fingerprint: Callable[[], Callable[[dict], str]] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)
    writer_check: Callable[[], Callable[[dict], None]] = field(repr=False, compare=False)
    binding_reader: Callable[[], CancellationBindingReader] = field(repr=False, compare=False)
    work: Callable[[], CancellationWorkWriter] = field(repr=False, compare=False)
    record_loader: Callable[[], Callable[[Path], dict]] = field(repr=False, compare=False)
    project_root: Callable[[], Path] = field(repr=False, compare=False)
    event_paths: Callable[[], Callable[[Path], tuple[Path, ...]]] = field(repr=False, compare=False)
    event_reader: Callable[[], CancellationEventReader] = field(repr=False, compare=False)
    event_id: Callable[[], Callable[[dict], str | None]] = field(repr=False, compare=False)

    def replay(self, path: Path, intent: dict) -> dict:
        if intent.get("checksum") != self.fingerprint()({k: v for k, v in intent.items() if k != "checksum"}):
            raise self.error()("cancellation_intent_invalid")
        binding = intent["work"]
        self.writer_check()(binding)
        before_run, before_assignment = intent["before_run"], intent["before_assignment"]
        # Recheck the capsule even on a partially applied retry.
        self.binding_reader()(binding, executable=False, terminal=True)
        run, assignment = copy.deepcopy(before_run), copy.deepcopy(before_assignment)
        assignment.update(status="cancelled", updated_at=intent["cancelled_at"])
        assignment["result"] = {"status": "cancelled", "summary": intent["reason"], "artifacts": intent["evidence"]}
        self.work()._set_run_task_status(run, assignment["id"], "cancelled")
        if all(t.get("status") in {"done", "completed", "cancelled", "failed"} for t in run["tasks"]):
            run["status"] = "cancelled"
        run["updated_at"] = intent["cancelled_at"]
        for target, previous, after in ((self.work()._assignment_path(assignment["id"]), before_assignment, assignment),
                                        (self.work()._run_path(run["id"]), before_run, run)):
            current = self.record_loader()(target)
            if current not in (previous, after):
                raise self.error()("cancellation_concurrent_change")
        for target, after in ((self.work()._assignment_path(assignment["id"]), assignment), (self.work()._run_path(run["id"]), run)):
            if self.record_loader()(target) != after:
                self.work()._atomic_yaml(target, after)
        self.work()._write_task_index(run)
        events = ["task.cancelled"] + (["run.cancelled"] if run["status"] == "cancelled" else [])
        for event in events:
            event_id = "evt_" + hashlib.sha256((intent["checksum"] + event).encode()).hexdigest()[:32]
            present = any(not error and isinstance(value, dict) and self.event_id()(value) == event_id
                          for _line, value, error in self.event_reader()(self.event_paths()(self.project_root())[0]))
            if not present:
                self.work()._emit(event, run, assignment, assignment["stage"], outcome="cancelled", event_id=event_id)
        state = self.work().state(run_id=run["id"], assignment_id=assignment["id"])
        self.work()._write_projection(state)
        done = path.with_suffix(".applied.json")
        if not done.exists():
            self.work()._atomic_text(done, json.dumps({"checksum": intent["checksum"], "status": "applied"}) + "\n")
        return {"schema_version": 1, "kind": "pf.work.cancel", "status": "cancelled", "action": "cancelled",
                "work": binding, "run_status": run["status"], "work_state": state}
