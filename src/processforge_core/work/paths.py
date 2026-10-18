from __future__ import annotations

import re
from pathlib import Path

from processforge_core.common.ids import safe_id
from processforge_core.project.metadata import ProjectMetadataReader


class WorkPaths:
    def run_root(self, project_root: Path, run_id: str) -> Path:
        candidate = str(run_id or "").strip()
        # ProcessExecutionService may append a collision suffix to a truncated id,
        # leaving a valid repeated hyphen such as `review--2`. Preserve that ID.
        normalized = candidate if re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", candidate) else safe_id(candidate, "run")
        return ProjectMetadataReader(project_root).flow_root() / "runs" / normalized

    def run_document(self, project_root: Path, run_id: str) -> Path:
        return self.run_root(project_root, run_id) / "run.yaml"

    def assignment_document(self, project_root: Path, task_id: str) -> Path:
        return ProjectMetadataReader(project_root).flow_root() / "assignments" / f"{safe_id(task_id, 'task')}.yaml"

    def task_artifacts(self, project_root: Path, run_id: str, task_id: str) -> Path:
        return ProjectMetadataReader(project_root).flow_root() / "artifacts" / "runs" / safe_id(run_id, "run") / safe_id(task_id, "task")

    def summary(self, project_root: Path, run_id: str) -> Path:
        return self.run_root(project_root, run_id) / "summary.md"

    def handoff(self, project_root: Path, run_id: str) -> Path:
        candidate = str(run_id or "").strip()
        normalized = candidate if re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", candidate) else safe_id(candidate, "run")
        return ProjectMetadataReader(project_root).flow_root() / "handoffs" / "runs" / f"{normalized}-handoff.md"

    def worker_prompt(self, project_root: Path, run_id: str, task_id: str) -> Path:
        return self.run_root(project_root, run_id) / "worker-prompts" / f"{safe_id(task_id, 'task')}.md"

    def agent_run(self, project_root: Path, run_id: str, task_id: str) -> Path:
        return ProjectMetadataReader(project_root).flow_root() / "runtime" / "agent-runs" / safe_id(run_id, "run") / safe_id(task_id, "task")

    def worker_run(self, project_root: Path, run_id: str, task_id: str) -> dict[str, Path]:
        root = self.agent_run(project_root, run_id, task_id)
        return {
            "root": root,
            "status": root / "status.json",
            "command": root / "command.json",
            "process": root / "process.json",
            "exit": root / "exit.json",
            "stdout": root / "stdout.log",
            "stderr": root / "stderr.log",
            "heartbeat": root / "heartbeat.json",
            "collection": root / "collection-report.md",
            "workspace_access": root / "workspace-access.json",
        }
