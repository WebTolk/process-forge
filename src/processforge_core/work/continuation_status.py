"""Existing live Continuation waiting, status and selected binding reads."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol


class WorkCandidateReader(Protocol):
    def __call__(self, *, include_historical: bool) -> list[dict]: ...


@dataclass(frozen=True, kw_only=True)
class ContinuationStatusReadService:
    path_resolver: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    selector: Callable[[], Callable[[str], str]] = field(repr=False, compare=False)
    load: Callable[[], Callable[[Path], dict]] = field(repr=False, compare=False)
    record_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    selection_path: Callable[[], Callable[[str], Path]] = field(repr=False, compare=False)
    validate_record: Callable[[], Callable[[dict, str], None]] = field(repr=False, compare=False)
    waiting_reader: Callable[[], Callable[[dict], dict]] = field(repr=False, compare=False)
    work_resolver: Callable[[], Callable[[dict], tuple[dict, dict, dict, dict]]] = field(repr=False, compare=False)
    context_checker: Callable[[], Callable[[], dict]] = field(repr=False, compare=False)
    work_records: Callable[[], WorkCandidateReader] = field(repr=False, compare=False)
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)

    def waiting(self, record: dict) -> dict:
        waiting = record.get("waiting_for") or {}
        paths = waiting.get("expected_artifacts") or []
        if not isinstance(paths, list) or len(paths) > 128:
            raise self.error()("waiting_conditions_invalid")
        missing = []
        for path in paths:
            target = self.path_resolver()(path)
            if not target.is_file():
                missing.append(path)
        handoff_id = waiting.get("handoff_id")
        handoff_ready = True
        if handoff_id:
            handoff = self.path_resolver()(".pf/handoffs/" + self.selector()(handoff_id) + "/handoff.yaml")
            handoff_ready = handoff.is_file() and self.load()(handoff).get("status") in {"returned", "finalized"}
        return {"status": "ready" if not missing and handoff_ready else "waiting", "missing_expected_artifacts": missing,
                "handoff_ready": handoff_ready}


    def status(self, *, continuation_id: str = "") -> dict:
        if not continuation_id:
            if self.context_checker()().get("status") not in {"fresh", "fresh_with_updates"}:
                raise self.error()("snapshot_not_fresh")
            records = self.work_records()(include_historical=False)
            candidates = [{k: row[k] for k in ("run_id", "assignment_id", "stage", "status")} for row in records[:20]]
            for row in candidates:
                capsule = self.load()(self.path_resolver()('.pf/contexts/assignment-capsules/' + self.selector()(row['assignment_id']) + '.capsule.yaml'))
                row["context_id"] = capsule.get('capsule', {}).get('id')
            return {"schema_version": 2, "kind": "pf.continuation.status", "status": "discovery",
                    "action": "choice_required" if len(records) > 1 else "candidate_available" if records else "not_found",
                    "candidates": candidates, "total": len(records), "selection_required": True}
        record = self.load()(self.record_path()(continuation_id))
        self.validate_record()(record, continuation_id)
        waiting = self.waiting_reader()(record)
        if record.get("schema_version") == 1:
            return {"schema_version": 1, "kind": "pf.continuation.status", "status": waiting["status"], "waiting": waiting,
                    "continuation_id": continuation_id, "work_resumed": False, "work_readiness": "legacy_binding_required"}
        if record.get("schema_version") != 2:
            raise self.error()("continuation_version_unsupported")
        _, _, binding, state = self.work_resolver()(record["work"])
        return {"schema_version": 2, "kind": "pf.continuation.status", "status": waiting["status"], "waiting": waiting,
                "continuation_id": continuation_id, "work": binding, "work_readiness": "ready", "work_state": state}


    def selected(self, session_id: str) -> dict | None:
        if not session_id:
            return None
        path = self.selection_path()(session_id)
        if not path.exists():
            return None
        receipt = self.load()(path)
        if receipt.get("session_id") != session_id or receipt.get("schema_version") != 1:
            raise self.error()("selection_invalid")
        record = self.load()(self.record_path()(receipt["continuation_id"]))
        self.validate_record()(record, receipt['continuation_id'])
        if record.get("work") != receipt.get("work") or record.get("status") == "cancelled":
            raise self.error()("selection_invalid")
        if self.waiting_reader()(record)['status'] != 'ready':
            raise self.error()('continuation_waiting')
        self.work_resolver()(receipt["work"])
        return receipt["work"]
