from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

from ..common.ids import safe_id
from ..common.values import as_list
from .context_documents import ContextContractInputs


@dataclass(frozen=True)
class WorkOutputPolicy:
    """Existing output declarations and project-relative path rules."""

    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def waivers(self, value: Any) -> dict[str, str]:
        waivers: dict[str, str] = {}
        for item in as_list(value):
            text = str(item or "").strip()
            if not text:
                continue
            output_id, sep, reason = text.partition(":")
            output_id = safe_id(output_id, "output")
            reason = reason.strip() if sep else ""
            if not reason:
                raise SystemExit(f"FAIL: required output waiver needs '<id>:<reason>': {text}")
            waivers[output_id] = reason
        return waivers

    def path(self, project_root: Path, raw_path: str) -> Path:
        """Resolve a declared project output before any content is read or written."""
        value = str(raw_path).strip().replace("\\", "/")
        if not value or value in {".", "./"} or "\x00" in value or ":" in value or PureWindowsPath(value).drive or value.startswith("/") or ".." in value.split("/"):
            raise ValueError("output path must be project-relative without traversal")
        root = project_root.resolve()
        target = (root / value).resolve()
        if not target.is_relative_to(root) or target == root:
            raise ValueError("output path escapes project root")
        return target

    def task_path(self, project_root: Path, output: dict[str, Any]) -> Path | None:
        raw_path = str(output.get("path") or "").strip()
        if not raw_path:
            return None
        try:
            return self.path(project_root, raw_path)
        except (OSError, ValueError):
            return None

    def expected_report(self, task: dict[str, Any]) -> str:
        expected = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
        value = str(expected.get("artifact") or "")
        if value:
            return self.inputs.normalize_assignment_path(value)
        task_id = safe_id(str(task.get("id") or "task"), "task")
        return self.default_report(task_id)

    def default_report(self, worker_id: str) -> str:
        return f".pf/artifacts/{safe_id(worker_id, 'worker')}-report.md"
