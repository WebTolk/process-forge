"""Execute existing governed Work commands through explicit Core factories."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from processforge_core.process_execution import ProcessExecutionService
    from processforge_core.work.resources import WorkResourceService


def _print_result(
    payload: dict[str, Any],
    *,
    dump_yaml: Callable[[dict[str, Any]], str],
    as_json: bool = False,
) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if as_json else dump_yaml(payload))


class WorkStartCommand:
    """Adapt the existing work start operation."""

    def __init__(
        self,
        *,
        execution_factory: Callable[[Path, str | None], ProcessExecutionService],
        require_flow_root: Callable[[Path], Path],
        dump_yaml: Callable[[dict[str, Any]], str],
    ) -> None:
        self._execution_factory = execution_factory
        self._require_flow_root = require_flow_root
        self._dump_yaml = dump_yaml

    def execute(self, args: argparse.Namespace) -> int:
        project_root = Path(args.project_root).expanduser().resolve()
        self._require_flow_root(project_root)
        security = None
        if getattr(args, "egress_intent", None):
            from processforge_core.egress.contracts import EgressError, bounded_json, security_intent
            try:
                with Path(args.egress_intent).open("rb") as stream:
                    security = security_intent(bounded_json(stream.read(1048577), 1048576))
            except (EgressError, OSError, ValueError):
                _print_result({"action": "blocked", "reason": "egress_contract_invalid"}, as_json=bool(args.json), dump_yaml=self._dump_yaml)
                return 1
        scope_intent = None
        if getattr(args, "scope_file", None):
            from processforge_core.process_execution import creation_scope_intent
            from processforge_core.work.context import ContextContractError
            try:
                with Path(args.scope_file).open("rb") as stream:
                    raw = stream.read(65537)
                if len(raw) > 65536:
                    raise ValueError("scope input too large")
                scope_intent = creation_scope_intent(json.loads(raw.decode("utf-8")))
            except (ContextContractError, OSError, ValueError):
                _print_result({"action": "blocked", "reason": "work_scope_invalid"}, as_json=bool(args.json), dump_yaml=self._dump_yaml)
                return 1
        payload = self._execution_factory(project_root, getattr(args, "workplace", None)).start(objective=args.objective, process_id=str(getattr(args, "process_id", None) or ""), security=security, scope_intent=scope_intent)
        _print_result(payload, as_json=bool(getattr(args, "json", False)), dump_yaml=self._dump_yaml)
        return 0 if payload.get("action") in {"created_new", "continue_existing"} else 1


class WorkStateCommand:
    """Adapt the existing work state operation."""

    def __init__(
        self,
        *,
        execution_factory: Callable[[Path, str | None], ProcessExecutionService],
        require_flow_root: Callable[[Path], Path],
        dump_yaml: Callable[[dict[str, Any]], str],
    ) -> None:
        self._execution_factory = execution_factory
        self._require_flow_root = require_flow_root
        self._dump_yaml = dump_yaml

    def execute(self, args: argparse.Namespace) -> int:
        project_root = Path(args.project_root).expanduser().resolve()
        self._require_flow_root(project_root)
        payload = self._execution_factory(project_root, getattr(args, "workplace", None)).state(
            run_id=str(getattr(args, "run", None) or ""),
            assignment_id=str(getattr(args, "assignment", None) or ""),
            context_id=str(getattr(args, "context_id", None) or ""),
            session_id=str(getattr(args, "session", None) or ""),
        )
        _print_result(payload, as_json=bool(getattr(args, "json", False)), dump_yaml=self._dump_yaml)
        return 0


class WorkResourceReadCommand:
    """Adapt the existing work resource read operation."""

    def __init__(
        self,
        *,
        resource_factory: Callable[[Path, str | None], WorkResourceService],
        require_flow_root: Callable[[Path], Path],
        dump_yaml: Callable[[dict[str, Any]], str],
    ) -> None:
        self._resource_factory = resource_factory
        self._require_flow_root = require_flow_root
        self._dump_yaml = dump_yaml

    def execute(self, args: argparse.Namespace) -> int:
        project_root = Path(args.project_root).expanduser().resolve()
        self._require_flow_root(project_root)
        payload = self._resource_factory(project_root, getattr(args, "workplace", None)).read(
            operation=args.command.removeprefix("work-"), run_id=args.run, assignment_id=args.assignment,
            context_id=args.context_id, resource_id=getattr(args, "resource_id", None), query=getattr(args, "query", None),
            limit=getattr(args, "limit", None), limitstart=getattr(args, "limitstart", None), offset=getattr(args, "offset", None))
        _print_result(payload, as_json=bool(getattr(args, "json", False)), dump_yaml=self._dump_yaml)
        return 0 if payload.get("status") == "ready" else 1


class WorkTransitionCommand:
    """Adapt the existing work transition operation."""

    def __init__(
        self,
        *,
        execution_factory: Callable[[Path, str | None], ProcessExecutionService],
        require_flow_root: Callable[[Path], Path],
        dump_yaml: Callable[[dict[str, Any]], str],
    ) -> None:
        self._execution_factory = execution_factory
        self._require_flow_root = require_flow_root
        self._dump_yaml = dump_yaml

    def execute(self, args: argparse.Namespace) -> int:
        project_root = Path(args.project_root).expanduser().resolve()
        self._require_flow_root(project_root)
        evidence: list[Any] = []
        evidence_file = str(getattr(args, "evidence_file", None) or "").strip()
        if evidence_file:
            loaded = json.loads(Path(evidence_file).expanduser().read_text(encoding="utf-8"))
            evidence.extend(loaded if isinstance(loaded, list) else [loaded])
        for raw in getattr(args, "evidence", None) or []:
            try:
                evidence.append(json.loads(raw))
            except json.JSONDecodeError:
                evidence.append(raw)
        payload = self._execution_factory(project_root, getattr(args, "workplace", None)).transition(
            outcome=args.outcome,
            evidence=evidence,
            notes=str(getattr(args, "notes", None) or ""),
            run_id=str(getattr(args, "run", None) or ""),
            assignment_id=str(getattr(args, "assignment", None) or ""),
            context_id=str(getattr(args, "context_id", None) or ""),
            session_id=str(getattr(args, "session", None) or ""),
        )
        _print_result(payload, as_json=bool(getattr(args, "json", False)), dump_yaml=self._dump_yaml)
        return 0 if payload.get("action") in {"stage_transitioned", "run_completed"} else 1
