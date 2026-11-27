"""Live project reads with explicit operation dependencies."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class ProjectContextCheck(Protocol):
    def __call__(
        self, project_root: Path, *, explicit_workplace: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class ExecutionProjectReadService:
    project_root: Path
    workplace_root: Path | None
    context_checker: Callable[[], ProjectContextCheck] = field(repr=False, compare=False)
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]] = field(repr=False, compare=False)
    flow_root: Callable[[], Path] = field(repr=False, compare=False)

    def context_check(self) -> dict[str, Any]:
        explicit = ""
        if self.workplace_root and (self.workplace_root / "workplace.yaml").is_file():
            explicit = str(self.workplace_root)
        return self.context_checker()(self.project_root, explicit_workplace=explicit or None)

    def manifest(self) -> dict[str, Any]:
        return self.document_loader()(self.flow_root() / "process-forge.yaml")


def _parse_snapshot_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _stale_marker_path(flow_root: Path) -> Path:
    return flow_root / "runtime" / "context" / "project-context.stale.json"


def _read_project_context_freshness(
    project_root: Path,
    *,
    explicit_workplace: str | None,
    distribution_root: Callable[[], Path],
    build_current_snapshot: Callable[[], ProjectContextCheck],
    snapshot_path: Callable[[], Path],
    load_snapshot: Callable[[Path], dict[str, Any]],
    stale_marker_path: Callable[[], Path],
    snapshot_digest: Callable[[Path], str],
) -> dict[str, Any]:
    """Compare the selected project's recorded snapshot with current inputs."""
    from .context_policy import ProjectContextPolicy
    from .resolved_comparison import ProjectSnapshotResolvedComparison
    from .source_check import ProjectSnapshotSourceCheckService

    snapshot_yaml = snapshot_path()
    if not snapshot_yaml.is_file():
        return {
            "snapshot_id": None,
            "status": "broken",
            "fresh": False,
            "stale": False,
            "broken": True,
            "updates_available": [],
            "stale_resources": [],
            "broken_refs": [{"reason": "project context snapshot missing"}],
            "recommended_action": "project-context-refresh",
            "policy_action": "block",
        }
    snapshot = load_snapshot(snapshot_yaml)
    reasons: list[str] = []
    stale_resources: list[dict[str, Any]] = []
    updates_available: list[dict[str, Any]] = []
    broken_refs: list[dict[str, Any]] = []
    for key in (
        "schema_version",
        "snapshot",
        "project",
        "flow",
        "sources",
        "capabilities",
        "session",
    ):
        if key not in snapshot:
            broken_refs.append({"reason": f"snapshot schema invalid: missing {key}"})
    meta = snapshot.get("snapshot")
    if not isinstance(meta, dict):
        meta = {}
    snapshot_id = str(meta.get("id") or snapshot.get("id") or "project-context")
    valid_until = _parse_snapshot_timestamp(meta.get("valid_until"))
    if valid_until is None:
        reasons.append("valid_until missing or invalid")
    elif valid_until < datetime.now(timezone.utc):
        reasons.append("valid_until expired")
    marker = stale_marker_path()
    if marker.is_file():
        try:
            marker_data = json.loads(marker.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            marker_data = {"reason": "stale marker invalid"}
        stale_resources.append(
            {
                "id": marker_data.get("subject") or "project-context",
                "reason": marker_data.get("reason") or "snapshot stale marker exists",
            }
        )
    reasons.extend(
        ProjectSnapshotSourceCheckService(
            project_root, distribution_root=distribution_root()
        ).compare(snapshot)
    )

    current = build_current_snapshot()(
        project_root, explicit_workplace=explicit_workplace
    )
    execution_readiness = current.get("execution_readiness")
    if not isinstance(execution_readiness, dict):
        execution_readiness = {}
    resource_readiness = current.get("resource_readiness")
    if not isinstance(resource_readiness, dict):
        resource_readiness = {}
    readiness = current.get("readiness")
    if not isinstance(readiness, dict):
        readiness = {}
    current_meta = current.get("snapshot")
    health = current_meta.get("health") if isinstance(current_meta, dict) else {}
    if not isinstance(health, dict):
        health = {}
    if str(resource_readiness.get("status") or "") == "blocked":
        blockers = resource_readiness.get("blockers")
        for item in blockers if isinstance(blockers, list) else []:
            if isinstance(item, dict):
                broken_refs.append(
                    {
                        "id": (
                            item.get("id") or item.get("target") or "resource_readiness"
                        ),
                        "reason": (
                            item.get("reason")
                            or item.get("type")
                            or "resource readiness blocked"
                        ),
                        "type": item.get("type") or "resource_readiness_blocked",
                    }
                )
    (
        comparison_reasons,
        comparison_stale,
        comparison_updates,
        comparison_broken,
    ) = ProjectSnapshotResolvedComparison().compare(snapshot, current)
    reasons.extend(comparison_reasons)
    stale_resources.extend(comparison_stale)
    updates_available.extend(comparison_updates)
    broken_refs.extend(comparison_broken)
    if broken_refs:
        status = "broken"
    elif stale_resources or reasons:
        status = "stale"
    elif updates_available:
        status = "fresh_with_updates"
    else:
        status = "fresh"
    context_policy = ProjectContextPolicy()
    policy = snapshot.get("context_policy")
    if not isinstance(policy, dict):
        policy = context_policy.build({})
    policy_action = context_policy.action(status, policy)
    return {
        "snapshot_id": snapshot_id,
        "snapshot_sha256": "sha256:" + snapshot_digest(snapshot_yaml),
        "status": status,
        "fresh": status in {"fresh", "fresh_with_updates"},
        "stale": status == "stale",
        "broken": status == "broken",
        "updates_available": updates_available,
        "stale_resources": stale_resources + [{"reason": reason} for reason in reasons],
        "broken_refs": broken_refs,
        "recommended_action": (
            "project-context-refresh" if status in {"stale", "broken"} else "continue"
        ),
        "policy_action": policy_action,
        "policy": {"action": policy_action},
        "health": health,
        "readiness": readiness,
        "resource_readiness": resource_readiness,
        "execution_readiness": execution_readiness,
    }


def _project_temporary_files_summary(
    project_root: Path, *, explicit_workplace: str | None = None
) -> dict[str, Any]:
    from ..configuration import ConfigurationError
    from ..maintenance.temporary_files import last_summary
    from . import configuration_inputs

    try:
        workplace = (
            Path(explicit_workplace).expanduser().resolve() if explicit_workplace else None
        )
        reader = configuration_inputs.project_configuration_reader
        resolved = reader.project_configuration(project_root, workplace)
        if resolved.errors:
            return {
                "status": "unknown",
                "notification": False,
                "reason": "configuration_invalid",
            }
        return last_summary(project_root, resolved.config.runtime.temporary_files)
    except (ConfigurationError, OSError, RuntimeError, ValueError):
        return {
            "status": "unknown",
            "notification": False,
            "reason": "configuration_unavailable",
        }


def _diagnose_project_context_check(
    check: Callable[[], dict[str, Any]],
    temporary_files_summary: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    from .. import diagnostics

    with diagnostics.span("context.check", component="context"):
        result = check()
    result["temporary_files"] = temporary_files_summary()
    diagnostics.annotate(snapshot_id=result.get("snapshot_id"))
    diagnostics.emit(
        "info" if result.get("fresh") else "warning",
        "context.freshness",
        lambda: {
            key: result.get(key)
            for key in (
                "snapshot_id",
                "status",
                "policy_action",
                "recommended_action",
                "reasons",
                "stale_resources",
                "broken_refs",
            )
        },
        component="context",
    )
    return result


def _build_project_context_check(
    *,
    distribution_root: Callable[[], Path],
    build_current_snapshot: Callable[[], ProjectContextCheck],
) -> ProjectContextCheck:
    """Build a checker that reads the project's own recorded snapshot."""

    def check(
        project_root: Path, *, explicit_workplace: str | None = None
    ) -> dict[str, Any]:
        from .metadata import ProjectMetadataReader
        from .snapshot import ProjectSnapshotReadService

        def read_freshness() -> dict[str, Any]:
            recorded = ProjectSnapshotReadService(project_root)
            return _read_project_context_freshness(
                project_root,
                explicit_workplace=explicit_workplace,
                distribution_root=distribution_root,
                build_current_snapshot=build_current_snapshot,
                snapshot_path=recorded.snapshot_path,
                load_snapshot=recorded.load,
                stale_marker_path=lambda: _stale_marker_path(
                    ProjectMetadataReader(project_root).flow_root()
                ),
                # A snapshot removed during the check still raises at the digest read.
                snapshot_digest=recorded.digests.sha256_file,
            )

        return _diagnose_project_context_check(
            read_freshness,
            lambda: _project_temporary_files_summary(
                project_root, explicit_workplace=explicit_workplace
            ),
        )

    return check
