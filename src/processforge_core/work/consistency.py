"""Current run and task consistency rules with concrete Core dependencies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from ..common.ids import safe_id
from ..common.paths import rel
from ..common.privacy import public_yaml_has_private_path
from ..common.yaml_io import yaml_error
from ..process_catalog.models import ProcessCatalogContext
from ..process_catalog.service import process_definition_exists as catalog_process_definition_exists
from ..process_catalog.validation import ITERATION_KINDS
from ..process_event_journal import ProcessEventJournal
from ..project.metadata import PROJECT_FLOW_ROOT
from .context_documents import ContextContractInputs
from .outputs import WorkOutputPolicy
from .paths import WorkPaths


RUN_STATUSES = {"draft", "open", "in_progress", "blocked", "review", "completed", "cancelled", "failed"}
TASK_STATUSES = {"open", "in_progress", "blocked", "debugging", "review", "done", "cancelled", "failed"}
ITERATION_STATUSES = {"planned", "in_progress", "completed", "passed", "failed", "cancelled"}


class RunTaskInputReader:
    def __init__(self) -> None:
        self._context_contract_inputs = ContextContractInputs()
        self._yaml_documents = self._context_contract_inputs.documents
        self._work_paths = WorkPaths()

    def require_flow_root(self, project_root: Path) -> Path:
        flow_root = self._context_contract_inputs.locate_flow_root(project_root)
        manifest = flow_root / "process-forge.yaml"
        if not manifest.is_file():
            raise SystemExit(
                f"FAIL: .pf/process-forge.yaml not found under {project_root}. "
                "Run `python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --apply` first."
            )
        return flow_root

    def event_runtime_paths(self, project_root: Path) -> tuple[Path, Path]:
        runtime = self._context_contract_inputs.locate_flow_root(project_root) / "runtime" / "events"
        return runtime / "events.sqlite3", self._context_contract_inputs.locate_flow_root(project_root) / "runtime" / "hooks" / "outbox"

    def active_run_ids(self, project_root: Path) -> list[str]:
        root = self._context_contract_inputs.locate_flow_root(project_root) / "runs"
        ids: list[str] = []
        if not root.is_dir():
            return ids
        for path in sorted(root.glob("*/run.yaml")):
            data = self._yaml_documents.load_fields(path, ("id", "status", "__yaml_error__"))
            if yaml_error(data):
                continue
            status = str(data.get("status", ""))
            if status in {"draft", "open", "in_progress", "blocked", "review"}:
                ids.append(str(data.get("id") or path.parent.name))
        return ids

    def task_process_id(self, task: dict[str, Any]) -> str:
        value = task.get("process")
        if isinstance(value, dict):
            return str(value.get("id", ""))
        return str(value or "")

    def next_iteration_id(self, task: dict[str, Any]) -> str:
        iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
        used = {str(item.get("id")) for item in iterations if isinstance(item, dict)}
        index = 1
        while True:
            candidate = f"iter-{index:03d}"
            if candidate not in used:
                return candidate
            index += 1


class RunTaskConsistencyService(RunTaskInputReader):
    def __init__(self, distribution_root: Path) -> None:
        super().__init__()
        self.distribution_root = distribution_root
        self._work_output_policy = WorkOutputPolicy()
        self._process_event_journal = ProcessEventJournal()

    def _process_catalog_context(
        self,
        project_root: Path,
        *,
        workplace_manifest: Path | None = None,
    ) -> ProcessCatalogContext:
        from processforge_core.process_catalog.catalog_read import ProcessCatalogReadService

        return ProcessCatalogReadService(
            project_root, distribution_root=self.distribution_root, workplace_manifest=workplace_manifest,
        ).context()

    def process_definition_exists(self, project_root: Path, process_id: str) -> bool:
        return catalog_process_definition_exists(self._process_catalog_context(project_root), process_id)

    def validate_run_consistency(self, project_root: Path, run_id: str, include_runtime_events: bool = False) -> list[Check]:
        flow_root = self.require_flow_root(project_root)
        checks: list[Check] = []
        path = self._work_paths.run_document(project_root, run_id)
        if not path.is_file():
            return [check("FAIL", f"{rel(path, project_root)} missing")]
        run = self._yaml_documents.read(path)
        error = yaml_error(run)
        if error:
            return [check("FAIL", f"{rel(path, project_root)} invalid YAML: {error}")]
        for key in ["schema_version", "id", "title", "process", "status", "created_at", "updated_at", "tasks"]:
            checks.append(check("PASS" if key in run else "FAIL", f"run.{key} present"))
        status = str(run.get("status", ""))
        checks.append(check("PASS" if status in RUN_STATUSES else "FAIL", f"run status valid: {status or 'missing'}"))
        artifact_paths = {
            "summary": self._work_paths.summary(project_root, str(run.get("id", run_id))),
            "task index": self._work_paths.run_root(project_root, str(run.get("id", run_id))) / "task-index.md",
            "handoff": self._work_paths.handoff(project_root, str(run.get("id", run_id))),
        }
        status_patterns = {
            "summary": r"^- status: `([^`]+)`$",
            "task index": r"^Run status: `([^`]+)`$",
            "handoff": r"^Status: `([^`]+)`$",
        }
        for label, artifact_path in artifact_paths.items():
            required = label == "task index" or status == "completed"
            if not artifact_path.is_file():
                checks.append(check("FAIL" if required else "PASS", f"{label} artifact {'exists' if required else 'not yet required'}: {rel(artifact_path, project_root)}"))
                continue
            text = artifact_path.read_text(encoding="utf-8", errors="replace")
            match = re.search(status_patterns[label], text, flags=re.MULTILINE)
            artifact_status = match.group(1) if match else ""
            checks.append(check("PASS" if artifact_status == status else "FAIL", f"{label} status matches run: {artifact_status or 'missing'}"))
        process_id = str(run.get("process", ""))
        checks.append(check("PASS" if self.process_definition_exists(project_root, process_id) else "FAIL", f"process exists: {process_id or 'missing'}"))
        checks.append(check("PASS" if not public_yaml_has_private_path(run) else "FAIL", f"{rel(path, project_root)} has no private absolute paths"))
        tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
        seen: set[str] = set()
        if not isinstance(tasks, list):
            checks.append(check("FAIL", "run.tasks must be a list"))
            tasks = []
        for item in tasks:
            if not isinstance(item, dict):
                checks.append(check("FAIL", "run.tasks item must be an object"))
                continue
            task_id = str(item.get("id", ""))
            assignment_rel = str(item.get("assignment", ""))
            task_status = str(item.get("status", ""))
            checks.append(check("PASS" if task_id and task_id not in seen else "FAIL", f"task id unique: {task_id or 'missing'}"))
            seen.add(task_id)
            checks.append(check("PASS" if task_status in TASK_STATUSES else "FAIL", f"task status valid for {task_id}: {task_status or 'missing'}"))
            assignment_path = project_root / assignment_rel if assignment_rel.startswith(PROJECT_FLOW_ROOT + "/") else flow_root / "assignments" / f"{safe_id(task_id, 'task')}.yaml"
            checks.append(check("PASS" if assignment_path.is_file() else "FAIL", f"assignment exists for {task_id}: {assignment_rel or rel(assignment_path, project_root)}"))
            if assignment_path.is_file():
                task = self._yaml_documents.read(assignment_path)
                checks.append(check("PASS" if str(task.get("run_id", "")) == str(run.get("id", "")) else "FAIL", f"{task_id} run_id matches run"))
        if status == "completed":
            incomplete = [str(item.get("id")) for item in tasks if isinstance(item, dict) and item.get("blocking", True) is not False and str(item.get("status")) != "done"]
            checks.append(check("PASS" if not incomplete else "FAIL", "completed run has all blocking tasks done" + (f": {', '.join(incomplete)}" if incomplete else "")))
            summary = artifact_paths["summary"]
            handoff = artifact_paths["handoff"]
            checks.append(check("PASS" if summary.is_file() else "FAIL", f"{rel(summary, project_root)} exists"))
            checks.append(check("PASS" if handoff.is_file() else "FAIL", f"{rel(handoff, project_root)} exists"))
        if include_runtime_events:
            events_path, _outbox = self.event_runtime_paths(project_root)
            events = self._process_event_journal.page(events_path, run_id=str(run.get("id", run_id)), limit=1)
            checks.append(check("PASS" if events else "WARN", "runtime run events exist"))
        return checks

    def validate_task_consistency(self, project_root: Path, task_id: str) -> list[Check]:
        self.require_flow_root(project_root)
        checks: list[Check] = []
        path = self._work_paths.assignment_document(project_root, task_id)
        if not path.is_file():
            return [check("FAIL", f"{rel(path, project_root)} missing")]
        task = self._yaml_documents.read(path)
        for key in ["schema_version", "id", "title", "run_id", "process", "status", "iterations", "result"]:
            checks.append(check("PASS" if key in task else "FAIL", f"task.{key} present"))
        status = str(task.get("status", ""))
        checks.append(check("PASS" if status in TASK_STATUSES else "FAIL", f"task status valid: {status or 'missing'}"))
        run_id = str(task.get("run_id", ""))
        checks.append(check("PASS" if run_id and self._work_paths.run_document(project_root, run_id).is_file() else "FAIL", f"referenced run exists: {run_id or 'missing'}"))
        process_id = self.task_process_id(task)
        checks.append(check("PASS" if self.process_definition_exists(project_root, process_id) else "FAIL", f"process exists: {process_id or 'missing'}"))
        checks.append(check("PASS" if not public_yaml_has_private_path(task) else "FAIL", f"{rel(path, project_root)} has no private absolute paths"))
        iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
        seen: set[str] = set()
        if not isinstance(iterations, list):
            checks.append(check("FAIL", "task.iterations must be a list"))
            iterations = []
        for item in iterations:
            if not isinstance(item, dict):
                checks.append(check("FAIL", "iteration item must be an object"))
                continue
            iter_id = str(item.get("id", ""))
            kind = str(item.get("kind", ""))
            iter_status = str(item.get("status", ""))
            checks.append(check("PASS" if iter_id and iter_id not in seen else "FAIL", f"iteration id unique: {iter_id or 'missing'}"))
            seen.add(iter_id)
            checks.append(check("PASS" if kind in ITERATION_KINDS else "FAIL", f"iteration kind valid for {iter_id}: {kind or 'missing'}"))
            checks.append(check("PASS" if iter_status in ITERATION_STATUSES else "FAIL", f"iteration status valid for {iter_id}: {iter_status or 'missing'}"))
        result = task.get("result") if isinstance(task.get("result"), dict) else {}
        if status == "done":
            result_summary = str(result.get("summary", "")).strip()
            result_artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), list) else []
            checks.append(check("PASS" if result_summary or result_artifacts else "FAIL", "completed task has result summary or artifact"))
        result_waivers = result.get("waivers") if isinstance(result.get("waivers"), dict) else {}
        checks.extend(self._work_output_policy.checks(project_root, task, {str(key): str(value) for key, value in result_waivers.items()}, enforce_missing=status == "done"))
        return checks
