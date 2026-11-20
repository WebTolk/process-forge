"""Existing project resource search and resolution services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, cast

from ..ports import ProjectSnapshotReadPort
from ..project.context_read import ProjectContextCheck
from .index_observation import IndexObservationService
from .local_search import (
    LocalSearchError,
    ResourceSearchIndex,
    authorized_coverage,
    pagination,
)
from .snapshot import add_private_navigation, selected_resource


class ResourceSearchReadPort(Protocol):
    def read_snapshot(
        self, snapshots: ProjectSnapshotReadPort | None
    ) -> dict[str, Any]: ...

    def context_checker(self) -> ProjectContextCheck: ...

    def search_roots_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]: ...


@dataclass(frozen=True)
class ResourceSearchService:
    """Observe index availability and query only current project resources."""

    project_root: Path
    workplace_root: Path
    reads: ResourceSearchReadPort = field(repr=False, compare=False)
    snapshots: ProjectSnapshotReadPort | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )

    def readiness(
        self,
        *,
        snapshot: dict[str, Any] | None = None,
        check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Report availability and selected-resource coverage without maintenance."""
        check = check or self.reads.context_checker()(
            self.project_root, explicit_workplace=str(self.workplace_root)
        )
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            snapshot = (
                snapshot
                if snapshot is not None
                else self.reads.read_snapshot(self.snapshots)
            )
            return {
                **self._readiness(snapshot=snapshot, check=check),
                "scope": "project_context",
                "authorized_coverage": authorized_coverage(
                    self.project_root, snapshot, workplace_root=self.workplace_root
                ),
            }
        snapshot = (
            snapshot
            if snapshot is not None
            else self.reads.read_snapshot(self.snapshots)
        )
        observer = IndexObservationService(self.workplace_root)
        identity = self._checkpoint(observer)
        state = observer.observe()
        coverage = authorized_coverage(
            self.project_root, snapshot, workplace_root=self.workplace_root
        )
        if identity is None or identity != self._checkpoint(observer):
            state = self._changed_state(observer)
        result = self._readiness(
            snapshot=snapshot, check=check, observed=state, coverage=coverage
        )
        result["scope"] = "project_context"
        result["authorized_coverage"] = coverage
        return result

    @staticmethod
    def _checkpoint(
        observer: IndexObservationService,
    ) -> tuple[str | None, str | None] | None:
        try:
            return observer.checkpoint()
        except OSError:
            return None

    @staticmethod
    def _changed_state(observer: IndexObservationService) -> dict[str, Any]:
        state = observer.observe()
        if state.get("status") == "fresh":
            return {
                **state,
                "status": "stale",
                "error": "search_maintenance_state_changed",
            }
        return state

    def _readiness(
        self,
        *,
        snapshot: dict[str, Any] | None = None,
        check: dict[str, Any] | None = None,
        observed: dict[str, Any] | None = None,
        coverage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        check = check or self.reads.context_checker()(
            self.project_root, explicit_workplace=str(self.workplace_root)
        )
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            return {
                "status": "blocked",
                "reason": "snapshot_not_fresh",
                "resource_count": 0,
                "document_count": 0,
            }
        try:
            after = (
                observed
                if observed is not None
                else IndexObservationService(self.workplace_root).observe()
            )
        except LocalSearchError as exc:
            return {
                "status": "blocked",
                "reason": exc.code,
                "resource_count": 0,
                "document_count": 0,
            }
        status = str(after.get("status") or "blocked")
        coverage = (
            coverage
            if coverage is not None
            else authorized_coverage(
                self.project_root,
                snapshot
                if snapshot is not None
                else self.reads.read_snapshot(self.snapshots),
                workplace_root=self.workplace_root,
            )
        )
        resource_count = int(coverage.get("indexed_resource_count") or 0)
        document_count = int(coverage.get("document_count") or 0)
        if status == "fresh" and document_count == 0:
            return {
                "status": "empty",
                "reason": "empty_corpus",
                "resource_count": resource_count,
                "document_count": document_count,
                "remediation": "Select or authorize searchable project resources.",
            }
        if status == "fresh":
            return {
                "status": "ready",
                "reason": "fresh_index",
                "resource_count": resource_count,
                "document_count": document_count,
                "remediation": "none",
            }
        return {
            "status": "stale" if status == "stale" else "blocked",
            "reason": str(after.get("error") or status),
            "resource_count": resource_count,
            "document_count": document_count,
            "remediation": (
                "Request authorized workplace search maintenance; "
                "project context refresh does not maintain the index."
            ),
        }

    def search(
        self,
        *,
        query: Any,
        limit: Any = None,
        limitstart: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
        """Search an observed index through the existing snapshot access filter."""
        check = self.reads.context_checker()(
            self.project_root, explicit_workplace=str(self.workplace_root)
        )
        if str(check.get("status") or "") not in {"fresh", "fresh_with_updates"}:
            raise LocalSearchError("snapshot_not_fresh")
        runtime_snapshot = self.reads.search_roots_resolver()(
            self.reads.read_snapshot(self.snapshots)
        )
        observer = IndexObservationService(self.workplace_root)
        identity = self._checkpoint(observer)
        state = observer.observe()
        coverage = authorized_coverage(
            self.project_root, runtime_snapshot, workplace_root=self.workplace_root
        )
        payload = None
        if state.get("status") == "fresh":
            query_index = ResourceSearchIndex(
                self.project_root, runtime_snapshot, self.workplace_root
            )
            payload = query_index.search(
                query=query, limit=limit, limitstart=limitstart, offset=offset
            )
        if identity is None or identity != self._checkpoint(observer):
            state = self._changed_state(observer)
            payload = None
        if payload is not None and payload.get("search_status") not in (None, "fresh"):
            state = {
                **state,
                "status": payload["search_status"],
                "error": payload.get("degraded_reason") or "index_not_fresh",
            }
        if payload is None:
            if not isinstance(query, str) or not query.strip():
                raise LocalSearchError("invalid_query")
            page_limit, start = pagination(
                limit=limit, limitstart=limitstart, offset=offset
            )
            payload = {
                "schema_version": 1,
                "kind": "pf.search",
                "search_status": state.get("status"),
                "index_generation": state.get("generation"),
                "query": query,
                "total": 0,
                "limit": page_limit,
                "offset": start,
                "items": [],
                "results": [],
                "page": {
                    "limit": page_limit,
                    "limitstart": start,
                    "offset": start,
                    "returned": 0,
                    "total": 0,
                    "next_limitstart": None,
                },
                "degraded_reason": state.get("error") or "index_not_fresh",
            }
        readiness = self._readiness(
            snapshot=runtime_snapshot, check=check, observed=state, coverage=coverage
        )
        readiness["scope"] = "project_context"
        readiness["authorized_coverage"] = coverage
        payload["garage_readiness"] = readiness
        payload["scope"] = "project_context"
        payload["authorized_coverage"] = readiness["authorized_coverage"]
        payload["search"] = readiness
        add_private_navigation(payload, runtime_snapshot)
        return payload


class ResourceResolveReadPort(Protocol):
    def project_id(self) -> str: ...

    def read_snapshot(
        self, snapshots: ProjectSnapshotReadPort | None
    ) -> dict[str, Any]: ...

    def path_ref_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]: ...


@dataclass(frozen=True)
class ResourceResolveService:
    project_root: Path
    workplace_root: Path
    reads: ResourceResolveReadPort | None = field(
        default=None, repr=False, compare=False
    )
    snapshots: ProjectSnapshotReadPort | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.reads is None:
            from .resolve_read import ResourceResolveReadService

            object.__setattr__(
                self,
                "reads",
                ResourceResolveReadService(self.project_root, self.workplace_root),
            )

    def resolve(self, *, resource_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.resolve",
            "scope": "project_context",
            "project": {
                "id": cast(ResourceResolveReadPort, self.reads).project_id(),
                "root": str(self.project_root),
            },
        }
        if not resource_id:
            return payload
        snapshot = cast(ResourceResolveReadPort, self.reads).read_snapshot(
            self.snapshots
        )
        selected = selected_resource(snapshot, resource_id)
        if not selected:
            return {
                **payload,
                "resource": {
                    "id": resource_id,
                    "status": "denied",
                    "reason": "not_in_project_snapshot",
                },
            }
        resource = {
            "id": resource_id,
            "status": "available",
            "scope": "project_context",
            "registry_source": "project-context.snapshot",
            "reference": selected.get("path_ref") or selected.get("path") or "",
            "application": selected.get("application")
            or {"package_id": selected.get("package_id"), "kind": selected.get("kind")},
        }
        if isinstance(selected.get("path_ref"), dict):
            resolution = cast(ResourceResolveReadPort, self.reads).path_ref_resolver()(
                selected["path_ref"]
            )
            if resolution.get("status") == "resolved" and resolution.get("path"):
                resource["local_root"] = str(Path(str(resolution["path"])).resolve())
                resource["navigation"] = "private_runtime_authorized"
            else:
                resource["resolution_status"] = resolution.get("status") or "unresolved"
        return {**payload, "resource": resource}
