"""Existing project resource search and resolution services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ports import ProjectSnapshotReadPort
from ..project.snapshot import load_snapshot
from .local_search import LocalSearchError, ResourceSearchIndex, authorized_coverage
from .snapshot import add_private_navigation, snapshot_with_resolved_search_roots


@dataclass(frozen=True)
class ResourceSearchService:
    project_root: Path
    workplace_root: Path
    core: Any
    snapshots: ProjectSnapshotReadPort | None = field(default=None, kw_only=True, repr=False, compare=False)

    def readiness(self, *, snapshot: dict[str, Any] | None = None, check: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self._readiness(snapshot=snapshot, check=check)
        result["scope"] = "project_context"
        result["authorized_coverage"] = authorized_coverage(self.project_root, snapshot if snapshot is not None else load_snapshot(self.project_root, self.core, snapshots=self.snapshots), workplace_root=self.workplace_root)
        return result

    def _readiness(self, *, snapshot: dict[str, Any] | None = None, check: dict[str, Any] | None = None) -> dict[str, Any]:
        check = check or self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            return {"status": "blocked", "reason": "snapshot_not_fresh", "resource_count": 0, "document_count": 0}
        index_snapshot = self.core.workplace_search_runtime_snapshot(self.workplace_root)
        index = ResourceSearchIndex(self.workplace_root, index_snapshot, self.workplace_root)
        try:
            before = index.status(verify_files=True)
            if before.get("status") in {"missing", "stale"}:
                after = index.maintenance_tick().get("after", {})
            else:
                after = before
        except LocalSearchError as exc:
            return {"status": "blocked", "reason": exc.code, "resource_count": 0, "document_count": 0}
        status = str(after.get("status") or "blocked")
        resource_count = int(after.get("resource_count") or 0)
        document_count = int(after.get("document_count") or 0)
        if status == "fresh" and document_count == 0:
            return {"status": "empty", "reason": "empty_corpus", "resource_count": resource_count, "document_count": document_count, "remediation": "Select or authorize searchable project resources."}
        if status == "fresh":
            return {"status": "ready", "reason": "fresh_index", "resource_count": resource_count, "document_count": document_count, "remediation": "none"}
        return {"status": "stale" if status == "stale" else "blocked", "reason": str(after.get("error") or status), "resource_count": resource_count, "document_count": document_count, "remediation": "Run safe technical search maintenance or refresh project context when required."}

    def search(self, *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
        check = self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise LocalSearchError("snapshot_not_fresh")
        runtime_snapshot = snapshot_with_resolved_search_roots(self.project_root, load_snapshot(self.project_root, self.core, snapshots=self.snapshots), self.workplace_root, self.core)
        index_snapshot = self.core.workplace_search_runtime_snapshot(self.workplace_root)
        index = ResourceSearchIndex(self.workplace_root, index_snapshot, self.workplace_root)
        state = index.status(verify_files=True)
        if state.get("status") in {"missing", "stale"}:
            state = index.maintenance_tick().get("after", {})
        readiness = self.readiness(snapshot=runtime_snapshot, check=check)
        query_index = ResourceSearchIndex(self.project_root, runtime_snapshot, self.workplace_root)
        payload = query_index.search(query=query, limit=limit, limitstart=limitstart, offset=offset)
        payload["garage_readiness"] = readiness
        payload["scope"] = "project_context"
        payload["authorized_coverage"] = readiness["authorized_coverage"]
        payload["search"] = readiness
        add_private_navigation(payload, runtime_snapshot)
        return payload
