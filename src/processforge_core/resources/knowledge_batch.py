"""Add knowledge records through native transactions and one selected index pass.

KnowledgeBatchService owns batch validation and ordering. Its injected callbacks
retain native authoring, audit/recovery, and canonical index-writer ownership.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeAlias, cast

from processforge_core.authoring.plans import AuthoringPlan
from processforge_core.common.ids import safe_id
from processforge_core.resources.project_packages import PackageRootResolution

KnowledgeAddPlan: TypeAlias = tuple[
    AuthoringPlan, dict[str, Any], str, Path, Path, PackageRootResolution
]


class _BatchInputError(ValueError):
    """Carry a bounded envelope diagnostic without source bytes or paths."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _explicit_id(record: dict[str, Any]) -> str | None:
    value = record.get("id")
    return safe_id(str(value), "resource") if value else None


def _records(envelope: object) -> list[dict[str, Any]]:
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"schema_version", "resources"}
        or type(envelope.get("schema_version")) is not int
        or envelope["schema_version"] != 1
    ):
        raise _BatchInputError("knowledge_batch_envelope_invalid")
    resources = envelope["resources"]
    if not isinstance(resources, list) or not resources:
        raise _BatchInputError("knowledge_batch_resources_invalid")
    seen: set[str] = set()
    for record in resources:
        if not isinstance(record, dict):
            raise _BatchInputError("knowledge_batch_resource_invalid")
        resource_id = _explicit_id(record)
        if resource_id is not None:
            if resource_id in seen:
                raise _BatchInputError("knowledge_batch_duplicate_id")
            seen.add(resource_id)
    return cast(list[dict[str, Any]], resources)


class KnowledgeBatchService:
    """Sequence native per-item commits before one final selected-resource call."""

    def __init__(
        self,
        *,
        build_plan: Callable[[dict[str, Any]], KnowledgeAddPlan],
        preflight_plan: Callable[[AuthoringPlan], None],
        execute_plan: Callable[[AuthoringPlan], dict[str, Any]],
        index_resources: Callable[[list[str]], dict[str, Any]],
    ) -> None:
        """Save callbacks bound to one operation's explicit workplace/package.

        The builder must bind build_knowledge_resource_add_plan. Preflight and
        execution must bind the native preflight_authoring_plan and
        execute_authoring_plan. The index callback binds the canonical owner's
        run_resources method. Construction performs no I/O or callback calls.

        Args:
            build_plan: Prepare one record using the latest package manifest.
            preflight_plan: Validate a prepared plan without durable effects.
            execute_plan: Commit a plan and finish its native audit transaction.
            index_resources: Refresh only the given registered catalogue IDs.
        """
        self._build_plan = build_plan
        self._preflight_plan = preflight_plan
        self._execute_plan = execute_plan
        self._index_resources = index_resources

    def run(
        self,
        envelope: object,
        *,
        package_id: str,
        apply: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Validate the whole envelope, process rows, and return a safe report.

        Default and explicit dry-run only build/preflight plans. Applied plans
        are prepared immediately before their individual native executions;
        neither plans nor job state survive this invocation. Ordinary item
        errors remain failed rows in input order. Only completed native audit
        transactions qualify for the final deduplicated indexing selection.

        KeyboardInterrupt and SystemExit propagate, except legacy FAIL:
        validation exits from the builder and explicit preflight boundary.
        An execution error has unconfirmed commit state; native recovery owns
        its durable journal and this service never attempts rollback or retry.

        Args:
            envelope: Schema 1 batch with inline native resource records.
            package_id: Existing package identity bound to the authoring builder.
            apply: Enable native commits and the final selected indexing call.
            dry_run: Explicitly request read-only planning; conflicts with apply.

        Returns:
            Ordered row outcomes and separate selected indexing status. Reports
            contain portable codes and never include raw native diagnostics.
        """
        if apply and dry_run:
            return self.failure("knowledge_batch_mode_conflict", apply=apply)
        try:
            records = _records(envelope)
        except _BatchInputError as error:
            return self.failure(error.code, apply=apply)

        rows: list[dict[str, Any]] = []
        for index, record in enumerate(records, start=1):
            rows.append(
                self._run_item(index, record, package_id=package_id, apply=apply)
            )
        successful_ids: list[str] = list(
            dict.fromkeys(
                row["index_resource_id"] for row in rows if row["status"] == "ok"
            )
        )
        indexing = self._index(successful_ids, apply=apply)
        failed = any(row["status"] == "error" for row in rows)
        failed = failed or indexing["status"] == "error"
        return {
            "schema_version": 1,
            "kind": "pf.knowledge.add_batch",
            "mode": "apply" if apply else "dry_run",
            "status": "failed" if failed else ("ok" if apply else "planned"),
            "results": rows,
            "successful_resource_ids": successful_ids,
            "indexing": indexing,
        }

    @staticmethod
    def failure(code: str, *, apply: bool = False) -> dict[str, Any]:
        """Build a refusal report before any native authoring is attempted."""
        return {
            "schema_version": 1,
            "kind": "pf.knowledge.add_batch",
            "mode": "apply" if apply else "dry_run",
            "status": "failed",
            "error": code,
            "results": [],
            "successful_resource_ids": [],
            "indexing": {
                "status": "skipped",
                "reason": "batch_refused",
                "resource_ids": [],
                "workplace_reconciled": False,
            },
        }

    def _run_item(
        self,
        index: int,
        record: dict[str, Any],
        *,
        package_id: str,
        apply: bool,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "index": index,
            "resource_id": _explicit_id(record),
            "status": "error",
            "authoring_state": "not_started",
        }
        phase = "prepare"
        try:
            plan, resource, result, manifest_path, _index_path, _root = (
                self._build_plan(deepcopy(record))
            )
            resource_id = resource["id"]
            if (
                not isinstance(resource_id, str)
                or safe_id(resource_id, "resource") != resource_id
            ):
                raise ValueError("native_resource_id_invalid")
            row["resource_id"] = resource_id
            row["index_resource_id"] = f"{package_id}:{resource_id}"
            # The native builder can propose package creation. This operation
            # only adds records to an already existing package.
            if not manifest_path.is_file():
                row["error"] = "knowledge_batch_package_missing"
                row["phase"] = phase
                return row
            phase = "preflight"
            self._preflight_plan(plan)
        except SystemExit as error:
            # These two native validation callbacks historically signal input
            # refusals with FAIL:. Numeric/other exits remain cancellation.
            if not isinstance(error.code, str) or not error.code.startswith("FAIL:"):
                raise
            row.update(error=f"knowledge_batch_{phase}_failed", phase=phase)
            return row
        except Exception:
            row.update(error=f"knowledge_batch_{phase}_failed", phase=phase)
            return row

        if result in ("added", "updated"):
            row["result"] = result
        if not apply:
            row["status"] = "planned"
            return row
        row["authoring_state"] = "unconfirmed"
        try:
            journal = self._execute_plan(plan)
        except Exception:
            # Execution includes durable commit AND post-commit audit. A raised
            # error may follow commit; retain native evidence and fail the row.
            row.update(error="knowledge_batch_authoring_failed", phase="execute")
            return row
        if (
            not isinstance(journal, dict)
            or journal.get("state") != "committed_audit_complete"
        ):
            row.update(error="knowledge_batch_authoring_incomplete", phase="execute")
            return row
        row.update(status="ok", authoring_state="complete")
        return row

    def _index(self, resource_ids: list[str], *, apply: bool) -> dict[str, Any]:
        row: dict[str, Any] = {
            "status": "skipped",
            "reason": "no_successful_resources" if apply else "dry_run",
            "resource_ids": list(resource_ids),
            "workplace_reconciled": False,
        }
        if not apply or not resource_ids:
            return row
        row.pop("reason")
        row["status"] = "error"
        try:
            result = self._index_resources(list(resource_ids))
        except Exception:
            row["error"] = "knowledge_batch_indexing_failed"
            return row
        # Project only bounded fields. A selected pass says nothing about the
        # observation's global readiness, earlier failure or invalidation.
        if not isinstance(result, dict):
            row["error"] = "knowledge_batch_indexing_failed"
            return row
        status = result.get("status")
        row["search_status"] = (
            status
            if status in ("fresh", "missing", "stale", "degraded", "unavailable")
            else "unavailable"
        )
        if (
            status == "fresh"
            and not result.get("error")
            and not result.get("failed_file_count")
        ):
            row["status"] = "ok"
        else:
            row["error"] = "knowledge_batch_indexing_failed"
        return row
