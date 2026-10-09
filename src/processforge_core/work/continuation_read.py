"""Existing bounded Continuation control-document, path and writer checks."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class ContinuationRecordReader:
    path_resolver: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    selector: Callable[[], Callable[[str], str]] = field(repr=False, compare=False)
    bounded_reader: Callable[[], Callable[[Path, int], bytes]] = field(repr=False, compare=False)
    yaml_loader: Callable[[], Callable[[str], Any]] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)
    workplace: Callable[[], Path | None] = field(repr=False, compare=False)
    leases_directory: Callable[[], Callable[[Path | None], Path]] = field(repr=False, compare=False)
    control_loader: Callable[[], Callable[[Path], dict]] = field(repr=False, compare=False)

    def record_path(self, continuation_id: str) -> Path:
        return self.path_resolver()(".pf/continuations/" + self.selector()(continuation_id) + ".yaml")


    def selection_path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not session_id or len(session_id) > 256:
            raise self.error()("invalid_session")
        return self.path_resolver()(".pf/continuations/selections/" + hashlib.sha256(session_id.encode()).hexdigest() + ".yaml")


    def load(self, path: Path) -> dict:
        if not path.exists():
            raise self.error()("continuation_not_found")
        data = self.yaml_loader()(self.bounded_reader()(path, 2 * 1024 * 1024).decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise self.error()("continuation_state_invalid")
        return data

    def writer_check(self, binding: dict) -> None:
        status_path = self.path_resolver()(f".pf/runtime/agent-runs/{binding['run_id']}/{binding['assignment_id']}/status.json")
        if status_path.exists():
            status = self.control_loader()(status_path)
            if status.get("status") not in {"completed", "failed", "timed_out", "cancelled", "collected"}:
                raise self.error()("worker_not_quiescent")
        if self.workplace():
            for path in self.leases_directory()(self.workplace()).glob("*.yaml"):
                lease = self.control_loader()(path)
                scope = lease.get("scope") or {}
                if lease.get("status") == "active" and all(not scope.get(k) or scope[k] == binding[v] for k, v in
                        (("project_id", "project_id"), ("run_id", "run_id"), ("task_id", "assignment_id"))):
                    raise self.error()("active_lease")

