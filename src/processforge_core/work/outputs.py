from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

from ..common.checks import Check, check
from ..common.ids import safe_id
from ..common.paths import rel
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

    def checks(self, project_root: Path, task: dict[str, Any], waivers: dict[str, str] | None = None, enforce_missing: bool = True) -> list[Check]:
        waiver_map = waivers or {}
        checks: list[Check] = []
        for output in self.inputs.normalize_required_outputs(task.get("required_outputs")):
            output_id = safe_id(str(output.get("id") or "output"), "output")
            if not bool(output.get("required", True)):
                checks.append(check("PASS", f"required output optional: {output_id}"))
                continue
            out_path = self.task_path(project_root, output)
            if out_path is None:
                if output_id in waiver_map:
                    checks.append(check("WARN", f"required output without path waived: {output_id} ({waiver_map[output_id]})"))
                else:
                    checks.append(check("FAIL", f"required output has no path: {output_id}"))
                continue
            output_rel = self.inputs.normalize_assignment_path(str(output.get("path") or ""))
            if out_path.is_file():
                checks.append(check("PASS", f"required output exists: {output_rel}"))
            elif output_id in waiver_map:
                checks.append(check("WARN", f"required output waived: {output_id} ({waiver_map[output_id]})"))
            elif not enforce_missing:
                checks.append(check("WARN", f"required output pending: {output_rel}"))
            else:
                checks.append(check("FAIL", f"required output missing: {output_rel}"))
        expected = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
        expected_artifact = self.inputs.normalize_assignment_path(str(expected.get("artifact") or ""))
        if expected_artifact:
            try:
                expected_path = self.path(project_root, expected_artifact)
            except (OSError, ValueError):
                checks.append(check("FAIL", "expected report path is outside project output scope"))
                return checks
            if expected_path.is_file():
                checks.append(check("PASS", f"expected report exists: {expected_artifact}"))
            elif "expected-report" in waiver_map or "expected_report" in waiver_map:
                waiver_reason = waiver_map.get("expected-report") or waiver_map["expected_report"]
                checks.append(check("WARN", f"expected report waived: {expected_artifact} ({waiver_reason})"))
            elif not enforce_missing:
                checks.append(check("WARN", f"expected report pending: {expected_artifact}"))
            else:
                checks.append(check("FAIL", f"expected report missing: {expected_artifact}"))
        return checks

    def fingerprint(self, project_root: Path, task: dict[str, Any]) -> str:
        """Fingerprint the task declaration and its declared verification inputs."""
        inputs: list[dict[str, Any]] = []
        for output in self.inputs.normalize_required_outputs(task.get("required_outputs")):
            if not bool(output.get("required", True)):
                continue
            path = self.task_path(project_root, output)
            item = {"id": str(output.get("id") or "output"), "path": rel(path, project_root) if path else "", "status": "missing"}
            if path and path.is_file():
                item.update({"status": "present", "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()})
            inputs.append(item)
        expected = task.get("expected_report") if isinstance(task.get("expected_report"), dict) else {}
        expected_path = str(expected.get("artifact") or "")
        if expected_path:
            path = self.task_path(project_root, {"path": expected_path})
            item = {"id": "expected-report", "path": self.inputs.normalize_assignment_path(expected_path), "status": "missing" if path else "invalid"}
            if path and path.is_file():
                item.update({"status": "present", "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()})
            inputs.append(item)
        payload = {"assignment": task, "inputs": inputs}
        return "sha256:" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
