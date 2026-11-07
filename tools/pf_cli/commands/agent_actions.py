"""Adapt discovery requests to the catalogue and optional exact native Work read."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from processforge_core.operations.catalogue import ActionCatalog, CatalogRequestError

if TYPE_CHECKING:
    from processforge_core.process_execution import ProcessExecutionService


class ActionsCommand:
    def __init__(
        self,
        *,
        parser_factory: Callable[[], argparse.ArgumentParser],
        execution_factory: Callable[[Path, str | None], ProcessExecutionService],
        require_flow_root: Callable[[Path], Path],
        dump_yaml: Callable[[dict[str, Any]], str],
        version: str,
    ) -> None:
        self._parser_factory = parser_factory
        self._execution_factory = execution_factory
        self._require_flow_root = require_flow_root
        self._dump_yaml = dump_yaml
        self._version = version

    def _print(self, args: argparse.Namespace, payload: dict[str, Any]) -> int:
        print(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            if args.json
            else self._dump_yaml(payload)
        )
        return 0 if payload.get("status") == "ready" else 1

    def execute(self, args: argparse.Namespace) -> int:
        from pf_runtime.action_catalog import catalog_payload

        request = {
            "operation": args.actions_operation,
            **{
                key: getattr(args, key)
                for key in ("action_id", "query", "surface", "limit", "offset")
                if hasattr(args, key)
            },
        }

        def blocked(reason: str) -> int:
            return self._print(
                args,
                {
                    "schema_version": 1,
                    "kind": "pf.actions." + args.actions_operation,
                    "status": "blocked",
                    "reason": reason,
                },
            )

        try:
            ActionCatalog.validate_request(**request)
        except CatalogRequestError as exc:
            return blocked(exc.reason)
        selectors = tuple(
            getattr(args, "actions_" + key, None)
            for key in ("run", "assignment", "context_id")
        )
        present = tuple(value is not None for value in selectors)
        state = None
        if any(present):
            run_id, assignment_id, context_id = selectors
            if (
                not isinstance(run_id, str)
                or not run_id.strip()
                or not isinstance(assignment_id, str)
                or not assignment_id.strip()
                or not isinstance(context_id, str)
                or not context_id.strip()
            ):
                return blocked("work_selectors_required")
            project_root = args.actions_project_root
            if not isinstance(project_root, str) or not project_root.strip():
                return blocked("project_root_required")
            project = Path(project_root).expanduser().resolve()
            self._require_flow_root(project)
            state = self._execution_factory(project, None).state(
                run_id=run_id,
                assignment_id=assignment_id,
                context_id=context_id,
                session_id="",
            )
            if not isinstance(state, Mapping):
                return blocked("work_state_unavailable")
            identity = tuple(
                state.get(key, {}).get("id")
                if isinstance(state.get(key), Mapping)
                else None
                for key in ("run", "assignment", "context")
            )
            if identity != selectors:
                return blocked("work_context_mismatch")
            context = state.get("context", {})
            if (
                not isinstance(context.get("validation"), Mapping)
                or context["validation"].get("status") != "valid"
            ):
                return blocked("work_context_invalid")
        payload = catalog_payload(
            self._parser_factory, version=self._version, work_state=state, **request
        )
        return self._print(args, payload)
