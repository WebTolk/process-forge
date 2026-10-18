"""Internal evidence collection rules; callers retain lifecycle and I/O ownership."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any


class EvidenceCollectionPolicy:
    def current(self, assignment: dict[str, Any]) -> list[dict[str, Any]]:
        execution = assignment.get("stage_execution") if isinstance(assignment.get("stage_execution"), dict) else {}
        return [copy.deepcopy(item) for item in execution.get("evidence", []) if isinstance(item, dict)] if isinstance(execution.get("evidence"), list) else []

    def accumulated(
        self, assignment: dict[str, Any], *, current: Callable[[dict[str, Any]], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        history = assignment.get("stage_history") if isinstance(assignment.get("stage_history"), list) else []
        for record in history:
            if isinstance(record, dict) and isinstance(record.get("evidence"), list):
                evidence.extend(copy.deepcopy(item) for item in record["evidence"] if isinstance(item, dict))
        evidence.extend(current(assignment))
        return evidence

    def merge(
        self, existing: Any, incoming: list[dict[str, Any]], *, identity: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> list[dict[str, Any]]:
        values = [copy.deepcopy(item) for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
        for item in incoming:
            marker = identity(item)
            values = [current for current in values if identity(current) != marker]
            values.append(item)
        return values

    def identity(self, item: dict[str, Any]) -> tuple[str, str]:
        kind = str(item.get("kind") or "")
        if kind == "gate":
            return ("gate", str(item.get("gate_id") or item.get("id") or ""))
        if kind in {"input", "artifact"}:
            # Inputs deliberately accept artifact-shaped evidence. Treat both
            # forms as one identity so a later alias cannot resurrect an older
            # positive record.
            return ("input_or_artifact", str(item.get("input_id") or item.get("artifact_id") or item.get("id") or ""))
        if kind in {"evidence", "attestation"}:
            return ("evidence", str(item.get("evidence_id") or item.get("id") or ""))
        return (kind, str(item.get("id") or ""))
