"""Validate existing worker plans and observe required subagent reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from ..common.ids import safe_id
from ..work.context_documents import WORKSPACE_ACCESS_KEYS, ContextContractInputs
from ..work.scope_conflicts import ScopeConflictService
from .catalog import RuntimeDriverCatalogReader
from .worker_plans import WorkerPlanPolicy


ORCHESTRATOR_PLAN_TOP_LEVEL_KEYS = {
    "schema_version",
    "run",
    "orchestrator",
    "runtime",
    "workers",
    "integration",
    "allow_write_scope_overlap",
    "metadata",
}
ORCHESTRATOR_PLAN_RUNTIME_KEYS = {"default_driver", "supervisor_profile", "start_policy", "max_parallel_workers", "model", "reasoning_effort", "metadata"}
ORCHESTRATOR_PLAN_WORKER_KEYS = {
    "id",
    "title",
    "role",
    "process",
    "objective",
    "execution_mode",
    "writer",
    "owner",
    "runtime_driver",
    "model",
    "reasoning_effort",
    "agent_reasoning_effort",
    "allow_subagents",
    "subagent_policy",
    "allowed_files",
    "allowed_read_files",
    "forbidden_files",
    "required_sources",
    "context_artifacts",
    "workspace_access",
    "required_outputs",
    "expected_report_artifact",
    "expected_report_language",
    "dependencies",
    "depends_on",
    "worker_may_rebuild_context",
    "metadata",
}
ORCHESTRATOR_PLAN_SUBAGENT_KEYS = {"allow", "max_subagents", "allowed_roles", "require_reports", "reports_dir", "metadata"}


class WorkerPlanValidationService:
    """Keep plan checks and live observations with concrete Core owners."""

    def __init__(self, distribution_root: Path) -> None:
        self.inputs = ContextContractInputs()
        self.drivers = RuntimeDriverCatalogReader(distribution_root)
        self.policy = WorkerPlanPolicy(inputs=self.inputs)

    def extension_key(self, key: str) -> bool:
        return key == "metadata" or key.startswith("x_") or key.startswith("x-")

    def unsupported_keys(self, data: dict[str, Any], allowed: set[str]) -> list[str]:
        return sorted(str(key) for key in data if str(key) not in allowed and not self.extension_key(str(key)))

    def subagent_outputs(self, project_root: Path, task: dict[str, Any]) -> list[str]:
        policy = self.inputs.normalize_subagent_policy(task.get("subagent_policy"))
        if not policy.get("allow"):
            return []
        if not policy.get("require_reports"):
            return []
        reports_dir = self.inputs.normalize_assignment_path(str(policy.get("reports_dir") or ""))
        if not reports_dir.startswith(".pf/artifacts/subagents/"):
            return [f"subagent reports_dir outside allowed artifacts dir: {reports_dir or 'missing'}"]
        report_root = project_root / reports_dir
        if not report_root.is_dir():
            return [f"subagent reports dir missing: {reports_dir}"]
        reports = sorted([path for path in report_root.rglob("*") if path.is_file()])
        if not reports:
            return [f"subagent reports missing in: {reports_dir}"]
        max_subagents = int(policy.get("max_subagents") or 0)
        if max_subagents > 0 and len(reports) > max_subagents:
            return [f"subagent reports exceed max_subagents: {len(reports)} > {max_subagents}"]
        return []

    def validate(self, project_root: Path, plan: dict[str, Any]) -> list[Check]:
        checks: list[Check] = []
        run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
        runtime = plan.get("runtime") if isinstance(plan.get("runtime"), dict) else {}
        workers = plan.get("workers") if isinstance(plan.get("workers"), list) else []
        for key in self.unsupported_keys(plan, ORCHESTRATOR_PLAN_TOP_LEVEL_KEYS):
            checks.append(check("FAIL", f"unsupported top-level config field: {key}"))
        if "allow_write_scope_overlap" in plan:
            checks.append(check("PASS" if isinstance(plan.get("allow_write_scope_overlap"), bool) else "FAIL", "allow_write_scope_overlap boolean"))
        if runtime:
            for key in self.unsupported_keys(runtime, ORCHESTRATOR_PLAN_RUNTIME_KEYS):
                checks.append(check("FAIL", f"unsupported runtime config field: {key}"))
            if "max_parallel_workers" in runtime:
                max_parallel = runtime.get("max_parallel_workers")
                checks.append(check("PASS" if type(max_parallel) is int and max_parallel >= 1 else "FAIL", "runtime.max_parallel_workers positive integer"))
            if "model" in runtime:
                checks.append(check("PASS" if self.inputs.normalize_agent_model(runtime.get("model")) else "FAIL", "runtime.model non-empty string when present"))
            if "reasoning_effort" in runtime:
                checks.append(check("PASS" if self.inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort")) else "FAIL", "runtime.reasoning_effort valid when present"))
        checks.append(check("PASS" if run.get("id") else "FAIL", "run.id present"))
        checks.append(check("PASS" if run.get("title") else "FAIL", "run.title present"))
        checks.append(check("PASS" if str(run.get("process") or "multi-agent-task-orchestration") == "multi-agent-task-orchestration" else "FAIL", "run process is multi-agent-task-orchestration"))
        checks.append(check("PASS" if workers else "FAIL", "workers present"))
        default_driver = str(runtime.get("default_driver") or "manual")
        start_policy = str(runtime.get("start_policy") or "manual")
        checks.append(check("PASS" if default_driver in {item[0] for item in self.drivers.ids(project_root=project_root)} else "FAIL", f"runtime.default_driver registered: {default_driver}"))
        checks.append(check("PASS" if start_policy in {"manual", "prepare", "supervisor"} else "FAIL", f"runtime.start_policy valid: {start_policy}"))
        seen: set[str] = set()
        scope_conflicts = ScopeConflictService(project_root)
        write_scopes: list[tuple[str, list[str]]] = []
        workers_by_id = {
            safe_id(str(worker.get("id") or "worker"), "worker"): worker
            for worker in workers
            if isinstance(worker, dict)
        }
        for raw_worker in workers:
            if not isinstance(raw_worker, dict):
                checks.append(check("FAIL", "worker item must be an object"))
                continue
            for key in self.unsupported_keys(raw_worker, ORCHESTRATOR_PLAN_WORKER_KEYS):
                checks.append(check("FAIL", f"unsupported worker config field: {key}"))
            raw_subagent_policy = raw_worker.get("subagent_policy") if isinstance(raw_worker.get("subagent_policy"), dict) else {}
            for key in self.unsupported_keys(raw_subagent_policy, ORCHESTRATOR_PLAN_SUBAGENT_KEYS):
                checks.append(check("FAIL", f"unsupported subagent_policy config field: {key}"))
            worker_id = safe_id(str(raw_worker.get("id") or ""), "worker")
            checks.append(check("PASS" if worker_id and worker_id not in seen else "FAIL", f"worker id unique: {worker_id or 'missing'}"))
            seen.add(worker_id)
            allowed = self.inputs.assignment_scope_items(raw_worker.get("allowed_files"))
            forbidden = self.inputs.assignment_scope_items(raw_worker.get("forbidden_files"))
            read_allowed = self.inputs.assignment_scope_items(raw_worker.get("allowed_read_files"))
            workspace_access = self.inputs.normalize_workspace_access(raw_worker.get("workspace_access"))
            outputs = self.inputs.normalize_required_outputs(raw_worker.get("required_outputs"))
            writer = bool(raw_worker.get("writer", True))
            driver_id = str(raw_worker.get("runtime_driver") or default_driver)
            if "model" in raw_worker:
                checks.append(check("PASS" if self.inputs.normalize_agent_model(raw_worker.get("model")) else "FAIL", f"{worker_id} model non-empty string when present"))
            if "reasoning_effort" in raw_worker or "agent_reasoning_effort" in raw_worker:
                checks.append(check("PASS" if self.inputs.normalize_agent_reasoning_effort(raw_worker.get("reasoning_effort") or raw_worker.get("agent_reasoning_effort")) else "FAIL", f"{worker_id} reasoning_effort valid when present"))
            if writer:
                checks.append(check("PASS" if allowed else "FAIL", f"{worker_id} writer has allowed_files"))
            checks.append(check("PASS" if driver_id in {item[0] for item in self.drivers.ids(project_root=project_root)} else "FAIL", f"{worker_id} runtime_driver registered: {driver_id}"))
            for dep_id in self.policy.dependency_set(raw_worker):
                checks.append(check("PASS" if dep_id in workers_by_id else "FAIL", f"{worker_id} dependency exists: {dep_id}"))
            has_workspace_access = any(workspace_access[key] for key in WORKSPACE_ACCESS_KEYS)
            checks.append(check("PASS" if read_allowed or raw_worker.get("required_sources") or has_workspace_access else "WARN", f"{worker_id} has bounded read/context scope"))
            forbidden_conflicts = scope_conflicts.conflicts(worker_id, allowed, worker_id, forbidden, reason_prefix="forbidden_wins:")
            checks.append(check("PASS" if not forbidden_conflicts else "FAIL", f"{worker_id} forbidden_files do not overlap allowed_files"))
            subagent_policy = self.policy.subagent_policy(raw_worker)
            reports_dir = str(subagent_policy.get("reports_dir") or "")
            if "allow_subagents" in raw_worker:
                checks.append(check("PASS" if isinstance(raw_worker.get("allow_subagents"), bool) else "FAIL", f"{worker_id} allow_subagents boolean"))
            if "allow" in raw_subagent_policy:
                checks.append(check("PASS" if isinstance(raw_subagent_policy.get("allow"), bool) else "FAIL", f"{worker_id} subagent_policy.allow boolean"))
            if "require_reports" in raw_subagent_policy:
                checks.append(check("PASS" if isinstance(raw_subagent_policy.get("require_reports"), bool) else "FAIL", f"{worker_id} subagent_policy.require_reports boolean"))
            if "max_subagents" in raw_subagent_policy:
                max_subagents_raw = raw_subagent_policy.get("max_subagents")
                checks.append(check("PASS" if type(max_subagents_raw) is int and max_subagents_raw >= 0 else "FAIL", f"{worker_id} subagent_policy.max_subagents non-negative integer"))
            checks.append(check("PASS" if isinstance(subagent_policy.get("allow"), bool) else "FAIL", f"{worker_id} subagent allow flag valid"))
            if subagent_policy.get("allow") and subagent_policy.get("require_reports"):
                checks.append(check("PASS" if reports_dir.startswith(".pf/artifacts/subagents/") else "FAIL", f"{worker_id} subagent reports_dir inside .pf/artifacts/subagents"))
                checks.append(check("PASS" if int(subagent_policy.get("max_subagents") or 0) > 0 else "FAIL", f"{worker_id} subagent max_subagents positive"))
            for output in outputs:
                out_path = self.inputs.normalize_assignment_path(output.get("path") if isinstance(output, dict) else "")
                checks.append(check("PASS" if out_path else "FAIL", f"{worker_id} required output has path"))
                if out_path:
                    allowed_output = self.inputs.path_allowed_by_scope(out_path, allowed) or out_path.startswith(".pf/artifacts/")
                    checks.append(check("PASS" if allowed_output else "FAIL", f"{worker_id} required output inside allowed or artifact area: {out_path}"))
            checks.append(check("PASS" if not bool(raw_worker.get("worker_may_rebuild_context", False)) else "FAIL", f"{worker_id} worker_may_rebuild_context false by default"))
            if writer:
                write_scopes.append((worker_id, allowed))
        if not bool(plan.get("allow_write_scope_overlap", False)):
            for index, (left_id, left_scope) in enumerate(write_scopes):
                for right_id, right_scope in write_scopes[index + 1 :]:
                    if self.policy.depends_on(workers_by_id, left_id, right_id) or self.policy.depends_on(workers_by_id, right_id, left_id):
                        continue
                    conflicts = scope_conflicts.conflicts(left_id, left_scope, right_id, right_scope)
                    if conflicts:
                        checks.append(check("FAIL", f"parallel write scopes overlap: {left_id} <-> {right_id}"))
        integration = plan.get("integration") if isinstance(plan.get("integration"), dict) else {}
        if integration.get("required", True):
            checks.append(check("PASS" if integration.get("expected_output") else "FAIL", "integration expected_output present"))
        return checks
