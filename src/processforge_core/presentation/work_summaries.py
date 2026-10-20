"""Markdown task indexes and run summaries from current Work documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.work.paths import WorkPaths


class WorkSummaryRenderer:
    def __init__(self) -> None:
        self._work_paths = WorkPaths()
        self._yaml_documents = YamlDocumentReader(fallback=_parse_simple_yaml)

    def render_task_index(self, project_root: Path, run: dict[str, Any]) -> str:
        tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
        lines = [
            f"# Task Index: {run.get('id', 'run')}",
            "",
            f"Run status: `{run.get('status', 'unknown')}`",
            "",
            "| Order | Task | Status | Assignment |",
            "| --- | --- | --- | --- |",
        ]
        for item in sorted([task for task in tasks if isinstance(task, dict)], key=lambda value: int(value.get("order", 0) or 0)):
            lines.append(f"| {item.get('order', '')} | `{item.get('id', '')}` | `{item.get('status', '')}` | `{item.get('assignment', '')}` |")
        if not tasks:
            lines.append("| | No tasks yet | | |")
        return "\n".join(lines) + "\n"

    def render_run_summary(self, project_root: Path, run: dict[str, Any]) -> str:
        run_id = str(run.get("id", "run"))
        lines = [f"# Run Summary: {run.get('title', run_id)}", "", f"- run_id: `{run_id}`", f"- status: `{run.get('status')}`", "", "## Tasks", ""]
        for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
            if isinstance(item, dict):
                task = self._yaml_documents.load(self._work_paths.assignment_document(project_root, str(item.get("id", ""))))
                result = task.get("result") if isinstance(task.get("result"), dict) else {}
                lines.append(f"- `{item.get('id')}`: `{item.get('status')}` - {result.get('summary', task.get('title', ''))}")
        if len(lines) == 7:
            lines.append("- No tasks recorded.")
        return "\n".join(lines) + "\n"
