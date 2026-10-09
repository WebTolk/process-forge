"""Existing project resource search and resolution services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from ..ports import ProjectSnapshotReadPort
from ..project.context_read import ProjectContextCheck
from ..project.snapshot import load_snapshot
from .local_search import LocalSearchError, ResourceSearchIndex, authorized_coverage
from .snapshot import add_private_navigation, resolve_garage_path_ref, selected_resource, snapshot_with_resolved_search_roots


class ResourceSearchReadPort(Protocol):
    def read_snapshot(self, snapshots: ProjectSnapshotReadPort | None) -> dict[str, Any]: ...

    def context_checker(self) -> ProjectContextCheck: ...

    def runtime_snapshot_reader(self) -> Callable[[Path], dict[str, Any]]: ...

    def search_roots_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]: ...


@dataclass(frozen=True)
class ResourceSearchService:
    project_root: Path
    workplace_root: Path
    reads: ResourceSearchReadPort = field(repr=False, compare=False)
    snapshots: ProjectSnapshotReadPort | None = field(default=None, kw_only=True, repr=False, compare=False)

    def readiness(self, *, snapshot: dict[str, Any] | None = None, check: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self._readiness(snapshot=snapshot, check=check)
        result["scope"] = "project_context"
        result["authorized_coverage"] = authorized_coverage(self.project_root, snapshot if snapshot is not None else self.reads.read_snapshot(self.snapshots), workplace_root=self.workplace_root)
        return result

    def _readiness(self, *, snapshot: dict[str, Any] | None = None, check: dict[str, Any] | None = None) -> dict[str, Any]:
        check = check or self.reads.context_checker()(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            return {"status": "blocked", "reason": "snapshot_not_fresh", "resource_count": 0, "document_count": 0}
        index_snapshot = self.reads.runtime_snapshot_reader()(self.workplace_root)
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
        check = self.reads.context_checker()(self.project_root, explicit_workplace=str(self.workplace_root))
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise LocalSearchError("snapshot_not_fresh")
        runtime_snapshot = self.reads.search_roots_resolver()(self.reads.read_snapshot(self.snapshots))
        index_snapshot = self.reads.runtime_snapshot_reader()(self.workplace_root)
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


@dataclass(frozen=True)
class ResourceResolveService:
    project_root: Path
    workplace_root: Path
    core: Any
    snapshots: ProjectSnapshotReadPort | None = field(default=None, kw_only=True, repr=False, compare=False)

    def resolve(self, *, resource_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.resolve",
            "scope": "project_context",
            "project": {"id": self.core.project_id(self.project_root), "root": str(self.project_root)},
        }
        if not resource_id:
            return payload
        snapshot = load_snapshot(self.project_root, self.core, snapshots=self.snapshots)
        selected = selected_resource(snapshot, resource_id)
        if not selected:
            return {**payload, "resource": {"id": resource_id, "status": "denied", "reason": "not_in_project_snapshot"}}
        resource = {
            "id": resource_id,
            "status": "available",
            "scope": "project_context",
            "registry_source": "project-context.snapshot",
            "reference": selected.get("path_ref") or selected.get("path") or "",
            "application": selected.get("application") or {"package_id": selected.get("package_id"), "kind": selected.get("kind")},
        }
        if isinstance(selected.get("path_ref"), dict):
            resolution = resolve_garage_path_ref(self.project_root, selected["path_ref"], self.workplace_root, self.core)
            if resolution.get("status") == "resolved" and resolution.get("path"):
                resource["local_root"] = str(Path(str(resolution["path"])).resolve())
                resource["navigation"] = "private_runtime_authorized"
            else:
                resource["resolution_status"] = resolution.get("status") or "unresolved"
        return {**payload, "resource": resource}
