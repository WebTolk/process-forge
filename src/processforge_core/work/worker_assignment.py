"""Full assignment reads and worker prompt rendering through concrete Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..project.metadata import ProjectMetadataReader
from .context_documents import ContextContractInputs
from .paths import WorkPaths


class WorkerAssignmentService:
    def load(self, project_root: Path, task_id: str) -> dict[str, Any]:
        paths = WorkPaths()
        path = paths.assignment_document(project_root, task_id)
        if not path.is_file():
            raise SystemExit(f"FAIL: task/assignment not found: {safe_id(task_id, 'task')}")
        documents = YamlDocumentReader(_parse_simple_yaml)
        return documents.read(path)

    def render_prompt(self, project_root: Path, task_id: str, *, prepared_input: dict[str, str] | None = None) -> str:
        task_id = safe_id(task_id, "task")
        task = self.load(project_root, task_id)
        run_id = str(task.get("run_id") or "")
        paths = WorkPaths()
        inputs = ContextContractInputs()
        capsule = rel(ProjectMetadataReader(project_root).flow_root() / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml", project_root)
        workspace_access = rel(paths.worker_run(project_root, safe_id(run_id or "run", "run"), task_id)["workspace_access"], project_root)
        requested_workspace_access = inputs.normalize_workspace_access(task.get("workspace_access"))
        allowed_files = inputs.assignment_scope_items(task.get("allowed_files"))
        allowed_read_files = inputs.assignment_scope_items(task.get("allowed_read_files"))
        forbidden_files = inputs.assignment_scope_items(task.get("forbidden_files"))
        required_outputs = inputs.normalize_required_outputs(task.get("required_outputs"))
        expected_report = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
        subagent_policy = inputs.normalize_subagent_policy(task.get("subagent_policy"))
        prepared_instructions = [
            "Read the prepared input identified by PF_PREPARED_INPUT_FILE and verify PF_PREPARED_INPUT_SHA256 before working.",
            "The orchestrator has already resolved the process, scope, inputs and resource permissions for this attempt.",
            "Do not bootstrap ProcessForge, start another Work, reselect the process or rebuild context.",
            "Use inline inputs and only explicitly declared file references. Metadata-only resources do not permit reading their bodies.",
            "No ProcessForge MCP connection is required to execute this prepared assignment.",
        ]
        if not prepared_input:
            prepared_instructions.append("This prompt alone is not launch-ready; the orchestrator must prepare the attempt manifest first.")
        lines = [
            "# Worker Launch Prompt",
            "",
            "You are a worker agent.",
            "You are not the orchestrator.",
            "Use only the assigned task and the provided assignment capsule.",
            "Use the immutable prepared execution input; do not rebuild project context.",
            "Do not edit files outside allowed_files.",
            "Do not read files outside allowed_read_files unless explicitly allowed.",
            "External resource bodies require explicit grants in the prepared input; metadata and pointers do not grant permission.",
            "Do not read an extra mutable workspace_access_file; the prepared input is authoritative.",
            "Do not copy private paths into public project artifacts, assignments, capsules, or reports.",
            "Respect forbidden_files.",
            "Produce required_outputs.",
            "Deliver expected_report according to the supplied output delivery contract.",
            "If the final response is captured as the report, return only its complete content.",
            "For a read-only assignment, do not write the report file yourself.",
            "Stop and report if scope is insufficient.",
            "Invoke subagents only when subagent_policy.allow is true.",
            "When subagent reports are required, write them only under subagent_policy.reports_dir.",
            *prepared_instructions,
            "",
            "## Assignment",
            "",
            f"- task_id: `{task_id}`",
            f"- run_id: `{run_id}`",
            f"- assignment: `{rel(paths.assignment_document(project_root, task_id), project_root)}`",
            f"- capsule: `{capsule}`",
            f"- workspace_access_file: `{workspace_access}`",
            f"- prepared_input_file: `{(prepared_input or {}).get('path', 'pending preparation')}`",
            f"- prepared_input_checksum: `{(prepared_input or {}).get('checksum', 'pending preparation')}`",
            "- worker_may_rebuild_context: `false`",
            "",
            "## workspace_access",
            "",
            f"- knowledge_resources: `{len(requested_workspace_access['knowledge_resources'])}`",
            f"- templates: `{len(requested_workspace_access['templates'])}`",
            f"- tools: `{len(requested_workspace_access['tools'])}`",
            f"- mcp: `{len(requested_workspace_access['mcp'])}`",
            "",
            "## allowed_files",
            "",
            *[f"- `{item}`" for item in allowed_files],
            "",
            "## allowed_read_files",
            "",
            *[f"- `{item}`" for item in allowed_read_files],
            "",
            "## forbidden_files",
            "",
            *[f"- `{item}`" for item in forbidden_files],
            "",
            "## required_outputs",
            "",
        ]
        for output in required_outputs:
            lines.append(f"- `{output.get('id')}` -> `{output.get('path', '')}`")
        lines.extend(["", "## expected_report", "", f"- `{expected_report.get('artifact', '')}`"])
        lines.extend(
            [
                "",
                "## subagent_policy",
                "",
                f"- allow: `{str(subagent_policy.get('allow')).lower()}`",
                f"- max_subagents: `{subagent_policy.get('max_subagents')}`",
                f"- require_reports: `{str(subagent_policy.get('require_reports')).lower()}`",
                f"- reports_dir: `{subagent_policy.get('reports_dir')}`",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"
