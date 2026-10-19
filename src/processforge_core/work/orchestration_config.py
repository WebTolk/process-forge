"""Existing orchestration configuration and its resolution artifacts."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.paths import rel
from ..common.yaml_io import write_yaml_file
from ..runtime.worker_plans import WorkerPlanPolicy
from .context_documents import ContextContractInputs
from .outputs import WorkOutputPolicy
from .paths import WorkPaths


class OrchestrationConfigService:
    def __init__(self) -> None:
        self._context_contract_inputs = ContextContractInputs()
        self._yaml_documents = self._context_contract_inputs.documents
        self._work_paths = WorkPaths()
        self._work_output_policy = WorkOutputPolicy()
        self._worker_plan_policy = WorkerPlanPolicy()

    def orchestrator_plan_path(self, project_root: Path, run_id: str) -> Path:
        return self._work_paths.run_root(project_root, run_id) / "orchestrator-plan.yaml"

    def load_orchestrator_plan(self, project_root: Path, plan_arg: str | None = None, run_arg: str | None = None) -> dict[str, Any]:
        if plan_arg:
            path = Path(plan_arg).expanduser()
            if not path.is_absolute():
                path = (project_root / path).resolve()
        elif run_arg:
            path = self.orchestrator_plan_path(project_root, run_arg)
        else:
            raise SystemExit("FAIL: --plan or --run is required")
        if not path.is_file():
            raise SystemExit(f"FAIL: orchestrator plan not found: {path}")
        data = self._yaml_documents.read(path)
        if not isinstance(data, dict):
            raise SystemExit(f"FAIL: orchestrator plan must be a YAML object: {path}")
        return data

    def apply_orchestrator_model_override(self, plan: dict[str, Any], model: str | None) -> dict[str, Any]:
        agent_model = self._context_contract_inputs.normalize_agent_model(model)
        if not agent_model:
            return plan
        result = copy.deepcopy(plan)
        runtime = result.get("runtime")
        if not isinstance(runtime, dict):
            runtime = {}
            result["runtime"] = runtime
        runtime["model"] = agent_model
        workers = result.get("workers") if isinstance(result.get("workers"), list) else []
        for worker in workers:
            if isinstance(worker, dict):
                worker["model"] = agent_model
        return result

    def normalized_orchestrator_plan(self, project_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
        run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
        runtime = plan.get("runtime") if isinstance(plan.get("runtime"), dict) else {}
        default_driver = str(runtime.get("default_driver") or "manual")
        default_model = self._context_contract_inputs.normalize_agent_model(runtime.get("model") or "")
        default_reasoning_effort = self._context_contract_inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort") or "")
        default_reasoning_effort = self._context_contract_inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort") or "")
        default_reasoning_effort = self._context_contract_inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort") or "")
        normalized_workers: list[dict[str, Any]] = []
        for order, worker in enumerate(plan.get("workers", []) if isinstance(plan.get("workers"), list) else [], start=1):
            if not isinstance(worker, dict):
                continue
            worker_id = safe_id(str(worker.get("id") or f"worker-{order}"), "worker")
            normalized_workers.append(
                {
                    "id": worker_id,
                    "order": order,
                    "runtime_driver": str(worker.get("runtime_driver") or default_driver),
                    "model": self._context_contract_inputs.normalize_agent_model(worker.get("model") or default_model),
                    "reasoning_effort": self._context_contract_inputs.normalize_agent_reasoning_effort(worker.get("reasoning_effort") or worker.get("agent_reasoning_effort") or default_reasoning_effort),
                    "allow_subagents": bool(worker.get("allow_subagents", False)),
                    "subagent_policy": self._worker_plan_policy.subagent_policy(worker),
                    "allowed_files": self._context_contract_inputs.assignment_scope_items(worker.get("allowed_files")),
                    "allowed_read_files": self._context_contract_inputs.assignment_scope_items(worker.get("allowed_read_files")),
                    "forbidden_files": self._context_contract_inputs.assignment_scope_items(worker.get("forbidden_files")),
                    "required_outputs": self._context_contract_inputs.normalize_required_outputs(worker.get("required_outputs")),
                    "workspace_access": self._context_contract_inputs.normalize_workspace_access(worker.get("workspace_access")),
                    "expected_report_artifact": str(worker.get("expected_report_artifact") or self._work_output_policy.default_report(worker_id)),
                    "depends_on": sorted(self._worker_plan_policy.dependency_set(worker)),
                }
            )
        return {
            "schema_version": 1,
            "run": {
                "id": safe_id(str(run.get("id") or "run"), "run"),
                "title": str(run.get("title") or run.get("id") or "run"),
                "process": str(run.get("process") or "multi-agent-task-orchestration"),
            },
            "runtime": {
                "default_driver": default_driver,
                "supervisor_profile": str(runtime.get("supervisor_profile") or "default"),
                "start_policy": str(runtime.get("start_policy") or "manual"),
                "max_parallel_workers": int(runtime.get("max_parallel_workers") or 1),
                "model": default_model,
                "reasoning_effort": default_reasoning_effort,
            },
            "allow_write_scope_overlap": self._worker_plan_policy.allows_write_scope_overlap(plan),
            "workers": normalized_workers,
        }

    def build_config_resolution_report(self, project_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalized_orchestrator_plan(project_root, plan)
        run_id = str(normalized["run"]["id"])
        runtime = plan.get("runtime") if isinstance(plan.get("runtime"), dict) else {}
        default_model = self._context_contract_inputs.normalize_agent_model(runtime.get("model") or "")
        default_reasoning_effort = self._context_contract_inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort") or "")
        raw_workers: dict[str, dict[str, Any]] = {}
        for raw_worker in plan.get("workers", []) if isinstance(plan.get("workers"), list) else []:
            if isinstance(raw_worker, dict):
                raw_workers[safe_id(str(raw_worker.get("id") or "worker"), "worker")] = raw_worker
        workers: list[dict[str, Any]] = []
        for worker in normalized["workers"]:
            policy = worker["subagent_policy"] if isinstance(worker.get("subagent_policy"), dict) else {}
            raw_worker = raw_workers.get(str(worker["id"]), {})
            if self._context_contract_inputs.normalize_agent_model(raw_worker.get("model") if isinstance(raw_worker, dict) else ""):
                model_source = f"workers[{worker['id']}].model"
            elif default_model:
                model_source = "runtime.model"
            else:
                model_source = "default.empty"
            workers.append(
                {
                    "id": worker["id"],
                    "runtime_driver": {
                        "value": worker["runtime_driver"],
                        "source": f"workers[{worker['id']}].runtime_driver",
                        "behavior": ["worker-run.runtime_driver"],
                    },
                    "agent_model": {
                        "value": self._context_contract_inputs.normalize_agent_model(worker.get("model")),
                        "source": model_source,
                        "behavior": ["assignment.agent_model", "capsule.agent_model", "worker-run.PF_AGENT_MODEL", "runtime-driver.command.model_args"],
                    },
                    "agent_reasoning_effort": {
                        "value": self._context_contract_inputs.normalize_agent_reasoning_effort(worker.get("reasoning_effort") or default_reasoning_effort),
                        "source": f"workers[{worker['id']}].reasoning_effort" if self._context_contract_inputs.normalize_agent_reasoning_effort(raw_worker.get("reasoning_effort") if isinstance(raw_worker, dict) else "") else ("runtime.reasoning_effort" if default_reasoning_effort else "default.empty"),
                        "behavior": ["assignment.agent_reasoning_effort", "capsule.agent_reasoning_effort", "worker-run.PF_AGENT_REASONING_EFFORT", "codex-exec.PF_CODEX_REASONING_EFFORT"],
                    },
                    "subagent_policy": {
                        "allow": bool(policy.get("allow")),
                        "max_subagents": int(policy.get("max_subagents") or 0),
                        "allowed_roles": policy.get("allowed_roles") if isinstance(policy.get("allowed_roles"), list) else [],
                        "require_reports": bool(policy.get("require_reports")),
                        "reports_dir": str(policy.get("reports_dir") or ""),
                        "behavior": ["assignment.subagent_policy", "capsule.subagent_policy", "worker-run.collect.subagent_reports"],
                    },
                    "required_outputs": worker["required_outputs"],
                    "expected_report_artifact": worker["expected_report_artifact"],
                }
            )
        return {
            "schema_version": 1,
            "plan": rel(self.orchestrator_plan_path(project_root, run_id), project_root),
            "resolved": {
                "allow_write_scope_overlap": {
                    "value": bool(normalized["allow_write_scope_overlap"]),
                    "source": "plan.allow_write_scope_overlap" if "allow_write_scope_overlap" in plan else "default.deny",
                    "behavior": [
                        "assignment.overlap_policy=allow" if normalized["allow_write_scope_overlap"] else "assignment.overlap_policy=deny",
                        "supervisor.write_scope_overlap=allow_for_plan" if normalized["allow_write_scope_overlap"] else "supervisor.write_scope_overlap=block_conflicts",
                    ],
                },
                "runtime": normalized["runtime"],
                "workers": workers,
            },
            "warnings": [],
            "unsupported_fields": [],
        }

    def write_orchestrator_config_resolution_artifacts(self, project_root: Path, plan: dict[str, Any]) -> None:
        normalized = self.normalized_orchestrator_plan(project_root, plan)
        run_id = str(normalized["run"]["id"])
        root = self._work_paths.run_root(project_root, run_id)
        root.mkdir(parents=True, exist_ok=True)
        write_yaml_file(root / "orchestrator-shell-plan.normalized.yaml", normalized)
        write_yaml_file(root / "config-resolution-report.yaml", self.build_config_resolution_report(project_root, plan))
