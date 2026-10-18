"""Existing worker plan normalization and dependency rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.values import as_list
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..work.context_documents import ContextContractInputs
from ..work.paths import WorkPaths


class WorkerPlanPolicy:
    def __init__(
        self,
        *,
        inputs: ContextContractInputs | None = None,
        paths: WorkPaths | None = None,
        documents: YamlDocumentReader | None = None,
    ) -> None:
        self._documents = documents if documents is not None else YamlDocumentReader(_parse_simple_yaml)
        self._inputs = inputs if inputs is not None else ContextContractInputs(self._documents)
        self._work_paths = paths if paths is not None else WorkPaths()

    def subagent_policy(self, worker: dict[str, Any]) -> dict[str, Any]:
        raw = worker.get("subagent_policy") if isinstance(worker.get("subagent_policy"), dict) else {}
        policy = self._inputs.normalize_subagent_policy(raw)
        if "allow_subagents" in worker:
            policy["allow"] = bool(worker.get("allow_subagents"))
        return policy

    def default_task_plan(self, run_id: str, title: str) -> dict[str, Any]:
        run_id = safe_id(run_id, "run")
        return {
            "schema_version": 1,
            "run": {"id": run_id, "title": title, "process": "multi-agent-task-orchestration"},
            "orchestrator": {
                "role": "orchestrator",
                "responsibilities": ["decompose work", "assign workers", "review outputs", "integrate final result"],
            },
            "runtime": {
                "default_driver": "manual",
                "supervisor_profile": "default",
                "start_policy": "manual",
            },
            "workers": [
                {
                    "id": "fixture-worker-a",
                    "title": "Fixture work item A",
                    "role": "worker",
                    "process": "task-batch-execution",
                    "execution_mode": "implementation",
                    "writer": True,
                    "allowed_files": [".pf/artifacts/fixture-a/**"],
                    "allowed_read_files": [".pf/contexts/project-context.snapshot.yaml"],
                    "forbidden_files": ["tools/**", "schemas/**"],
                    "required_sources": [".pf/contexts/project-context.snapshot.yaml"],
                    "required_outputs": [{"id": "fixture-a-report", "path": ".pf/artifacts/fixture-a-report.md", "type": "markdown", "required": True}],
                    "expected_report_artifact": ".pf/artifacts/fixture-a-report.md",
                    "runtime_driver": "manual",
                    "worker_may_rebuild_context": False,
                },
                {
                    "id": "fixture-worker-b",
                    "title": "Fixture work item B",
                    "role": "reviewer",
                    "process": "task-batch-execution",
                    "execution_mode": "assurance",
                    "writer": True,
                    "allowed_files": [".pf/artifacts/fixture-b/**"],
                    "allowed_read_files": [".pf/artifacts/fixture-a/**", ".pf/contexts/project-context.snapshot.yaml"],
                    "forbidden_files": ["tools/processforge.py"],
                    "required_sources": [".pf/contexts/project-context.snapshot.yaml"],
                    "required_outputs": [{"id": "fixture-b-report", "path": ".pf/artifacts/fixture-b-report.md", "type": "markdown", "required": True}],
                    "expected_report_artifact": ".pf/artifacts/fixture-b-report.md",
                    "runtime_driver": "manual",
                    "depends_on": ["fixture-worker-a"],
                    "worker_may_rebuild_context": False,
                },
            ],
            "integration": {"required": True, "role": "orchestrator", "expected_output": ".pf/artifacts/orchestrator-integration-report.md"},
        }

    def worker_map(self, plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
        workers = plan.get("workers") if isinstance(plan.get("workers"), list) else []
        result: dict[str, dict[str, Any]] = {}
        for worker in workers:
            if isinstance(worker, dict):
                worker_id = safe_id(str(worker.get("id") or "worker"), "worker")
                result[worker_id] = worker
        return result

    def task_dependency_ids(self, task: dict[str, Any], worker: dict[str, Any] | None = None) -> list[str]:
        values: list[str] = []
        dependencies = task.get("dependencies") if isinstance(task.get("dependencies"), dict) else {}
        values.extend(str(item) for item in as_list(dependencies.get("blocked_by")))
        if worker:
            values.extend(str(item) for item in as_list(worker.get("dependencies")))
            values.extend(str(item) for item in as_list(worker.get("depends_on")))
        return sorted({safe_id(item, "task") for item in values if item})

    def task_dependencies_done(self, project_root: Path, task: dict[str, Any], worker: dict[str, Any] | None = None) -> bool:
        for dep_id in self.task_dependency_ids(task, worker):
            dep_path = self._work_paths.assignment_document(project_root, dep_id)
            if not dep_path.is_file():
                return False
            dep = self._documents.read(dep_path)
            if str(dep.get("status")) not in {"done", "completed"}:
                return False
        return True

    def dependency_set(self, worker: dict[str, Any]) -> set[str]:
        result: set[str] = set()
        for key in ["dependencies", "depends_on"]:
            for item in as_list(worker.get(key)):
                if item:
                    result.add(safe_id(str(item), "worker"))
        return result

    def depends_on(self, workers_by_id: dict[str, dict[str, Any]], worker_id: str, dependency_id: str, seen: set[str] | None = None) -> bool:
        seen = seen or set()
        if worker_id in seen:
            return False
        seen.add(worker_id)
        worker = workers_by_id.get(worker_id, {})
        dependencies = self.dependency_set(worker)
        if dependency_id in dependencies:
            return True
        return any(self.depends_on(workers_by_id, dep_id, dependency_id, seen) for dep_id in dependencies)

    def allows_write_scope_overlap(self, plan: dict[str, Any]) -> bool:
        return plan.get("allow_write_scope_overlap") is True
