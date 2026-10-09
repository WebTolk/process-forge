"""Existing project context assembly with explicit, live read dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..common.request_scope import scoped_request
from ..ports import ProjectSnapshotReadPort


class ContextResourceReadiness(Protocol):
    def __call__(self, *, snapshot: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]: ...


class ContextModeRead(Protocol):
    def __call__(self, *, snapshot: dict[str, Any], session_id: str) -> dict[str, Any]: ...


class ContextDerivedReportRead(Protocol):
    def __call__(self, *, snapshot: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class ProjectContextReaders:
    mode: ContextModeRead
    process_summary: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    derived_reports: ContextDerivedReportRead
    boundary: Callable[[dict[str, Any]], dict[str, Any] | None]


@dataclass(frozen=True)
class ProjectContextService:
    project_root: Path
    workplace_root: Path
    snapshots: ProjectSnapshotReadPort = field(kw_only=True, repr=False, compare=False)
    project_id_reader: Callable[[], str] = field(kw_only=True, repr=False, compare=False)
    context_check: Callable[[], dict[str, Any]] = field(kw_only=True, repr=False, compare=False)
    manifest_reader: Callable[[], dict[str, Any]] = field(kw_only=True, repr=False, compare=False)
    runtime_snapshot_resolver: Callable[[], Callable[[dict[str, Any]], dict[str, Any]]] = field(kw_only=True, repr=False, compare=False)
    resource_readiness: ContextResourceReadiness = field(kw_only=True, repr=False, compare=False)
    work_summary: Callable[[], dict[str, Any]] = field(kw_only=True, repr=False, compare=False)
    resource_selection: Callable[[dict[str, Any]], dict[str, Any]] = field(kw_only=True, repr=False, compare=False)
    diagnostics: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], list[dict[str, str]]] = field(kw_only=True, repr=False, compare=False)
    context_readers: Callable[[], ProjectContextReaders] = field(kw_only=True, repr=False, compare=False)

    def project_id(self) -> str:
        return str(self.project_id_reader())

    def snapshot(self) -> dict[str, Any]:
        return self.snapshots.load()

    def check(self) -> dict[str, Any]:
        return self.context_check()

    def runtime_snapshot(self) -> dict[str, Any]:
        return self.runtime_snapshot_resolver()(self.snapshot())

    @scoped_request
    def context(self, *, session_id: str = "") -> dict[str, Any]:
        readers = self.context_readers()

        check = self.check()
        snapshot = self.snapshot() if not check.get("broken") else {}
        manifest = self.manifest_reader()
        search = self.resource_readiness(snapshot=snapshot, check=check)
        mode = readers.mode(snapshot=snapshot, session_id=session_id)
        work = self.work_summary()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "kind": "pf.context",
            "mode": mode["mode"],
            "project": {
                "id": self.project_id(),
                "root": str(self.project_root),
            },
            "context": {
                "snapshot_id": check.get("snapshot_id"),
                "status": check.get("status"),
                "policy_action": check.get("policy_action"),
                "recommended_action": check.get("recommended_action"),
            },
            "process": readers.process_summary(snapshot, manifest),
            "resources": {
                "search_status": search.get("status"),
                "reason": search.get("reason"),
                "resource_count": search.get("resource_count"),
                "document_count": search.get("document_count"),
                "search": search,
                "selection": self.resource_selection(snapshot),
            },
            "work": work,
            "derived_reports": readers.derived_reports(snapshot=snapshot),
            "session": mode["session"],
            "diagnostics": self.diagnostics(check, search, mode),
        }
        continuation = readers.boundary(work)
        if continuation:
            payload["work"]["recommendation"] = "continue_from_handoff"
            payload["continuation"] = continuation
        return payload
