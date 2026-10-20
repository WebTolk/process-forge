"""Prepare project-local native hooks using the existing PF agent installer.

Workplace configuration owns the setup decision. Native ingress still owns
event admission, session binding and all subsequent effects.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agent_entry.contract import EntryError
from ..agent_entry.migration import safe_path
from .coordination import ProjectCoordinationReader

_TARGET = ".codex/hooks.json"
_ADAPTER = "tools/pf_runtime/codex_hooks.py"


@dataclass(frozen=True)
class AgentHookSetupError(Exception):
    """A bounded setup error safe to return through initialization adapters."""

    code: str


@dataclass(frozen=True)
class AgentHookPlan:
    """Request-local native settings and their public-safe setup projection."""

    project_root: Path
    report: dict[str, Any]
    revision: str | None = None
    payload: dict[str, Any] | None = None
    changed_events: tuple[str, ...] = ()


class ProjectAgentHookConfigurator:
    """Coordinate Forge setup without loading Main or starting infrastructure."""

    def __init__(
        self,
        distribution_root: Path | None = None,
        *,
        coordination: ProjectCoordinationReader | None = None,
    ) -> None:
        self.distribution_root = (
            Path(distribution_root)
            if distribution_root is not None
            else Path(__file__).parents[3]
        )
        self.coordination = (
            coordination if coordination is not None else ProjectCoordinationReader()
        )

    @staticmethod
    def _revision(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

    @staticmethod
    def failure(code: str, *, unavailable: bool = False) -> dict[str, Any]:
        """Return a bounded failure without native exception or host paths."""
        return {
            "status": "unavailable" if unavailable else "invalid",
            "target": _TARGET,
            "adapter": _ADAPTER,
            "scope": "project-local",
            "required": True,
            "severity": "error",
            "purpose": "project_initialization_hooks",
            "error": code,
            "restart_required": False,
        }

    def plan(
        self, project_root: Path, workplace_manifest: Path | None
    ) -> AgentHookPlan | None:
        """Inspect native settings without writing them.

        Args:
            project_root: Existing initialization destination.
            workplace_manifest: Actual linked workplace manifest, if available.

        Returns:
            A request-local Codex plan for Forge, or None for other workplaces.
            Configuration failures appear in the plan's bounded report.

        Raises:
            AgentHookSetupError: Workplace configuration cannot be determined.
        """
        try:
            if workplace_manifest and workplace_manifest.is_file():
                self.coordination.documents.read(workplace_manifest)
            workplace = self.coordination.workplace(workplace_manifest)
        except (OSError, SystemExit) as exc:
            raise AgentHookSetupError("codex_hooks_workplace_invalid") from exc
        if workplace["default_project_mode"] != "organized":
            return None

        root = Path(project_root).expanduser().absolute()
        try:
            # This standalone infrastructure module has no Main/Host imports.
            from pf_runtime import codex_integration
        except ImportError:
            return AgentHookPlan(
                root, self.failure("codex_hooks_adapter_unavailable", unavailable=True)
            )
        adapter = (self.distribution_root / _ADAPTER).resolve()
        if not adapter.is_file():
            return AgentHookPlan(
                root, self.failure("codex_hooks_adapter_unavailable", unavailable=True)
            )
        try:
            target = safe_path(root, _TARGET)
            if target.exists() and not target.is_file():
                raise EntryError("unsupported_path")
            revision = self._revision(target)
            current = codex_integration.load_config(target)
            # Keep unknown settings and native handler fields. Refuse malformed
            # known-event groups rather than quietly appending a second group.
            for event in codex_integration.EVENTS:
                groups = current["hooks"].get(event, [])
                if not isinstance(groups, list):
                    raise AgentHookSetupError("codex_hooks_configuration_invalid")
                for group in groups:
                    if not isinstance(group, dict) or not isinstance(
                        group.get("hooks"), list
                    ):
                        raise AgentHookSetupError("codex_hooks_configuration_invalid")
                    if not all(isinstance(handler, dict) for handler in group["hooks"]):
                        raise AgentHookSetupError("codex_hooks_configuration_invalid")
                    if group.get("matcher") and any(
                        codex_integration.is_managed(handler, adapter)
                        for handler in group["hooks"]
                    ):
                        raise AgentHookSetupError("codex_hooks_handler_conflict")
            payload, changed = codex_integration.install_payload(current, adapter)
            if self._revision(target) != revision:
                raise AgentHookSetupError("codex_hooks_configuration_changed")
        except EntryError:
            return AgentHookPlan(root, self.failure("codex_hooks_unsafe_path"))
        except AgentHookSetupError as exc:
            return AgentHookPlan(root, self.failure(exc.code))
        except (OSError, UnicodeError, ValueError, SystemExit):
            return AgentHookPlan(
                root, self.failure("codex_hooks_configuration_invalid")
            )

        events = sorted(codex_integration.EVENTS)
        return AgentHookPlan(
            root,
            {
                "status": "installed"
                if not changed
                else "missing"
                if revision is None
                else "stale",
                "target": _TARGET,
                "adapter": _ADAPTER,
                "scope": "project-local",
                "required": True,
                "severity": "info",
                "purpose": "project_initialization_hooks",
                "event_types": events,
                "registered_events": [
                    event for event in events if event not in changed
                ],
                "missing_events": sorted(changed),
                "restart_required": bool(changed),
            },
            revision,
            payload,
            tuple(sorted(changed)),
        )

    def apply(self, plan: AgentHookPlan) -> dict[str, Any]:
        """Apply a preflighted plan after successful base initialization.

        Args:
            plan: The request-local plan from the same initialization operation.

        Returns:
            Public-safe integration status and a relative recovery backup, if any.

        Raises:
            AgentHookSetupError: Preflight failed, current bytes changed, or the
                existing atomic installer could not complete. Existing settings
                and any recovery backup are retained on a failed replacement.
        """
        if plan.payload is None:
            raise AgentHookSetupError(plan.report["error"])
        from pf_runtime import codex_integration

        try:
            target = safe_path(
                plan.project_root, _TARGET, writable=bool(plan.changed_events)
            )
            if self._revision(target) != plan.revision:
                raise AgentHookSetupError("codex_hooks_configuration_changed")
            result = {
                **plan.report,
                "status": "installed",
                "registered_events": list(plan.report["event_types"]),
                "missing_events": [],
                "changed_events": list(plan.changed_events),
            }
            if plan.changed_events:
                backup = codex_integration.write_atomic(target, plan.payload)
                result["backup"] = (
                    backup.relative_to(plan.project_root).as_posix()
                    if backup != Path()
                    else None
                )
            return result
        except EntryError as exc:
            raise AgentHookSetupError("codex_hooks_unsafe_path") from exc
        except OSError as exc:
            raise AgentHookSetupError("codex_hooks_write_failed") from exc
