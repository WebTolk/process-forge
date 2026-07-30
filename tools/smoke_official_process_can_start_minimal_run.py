#!/usr/bin/env python3
"""Create a minimal run and task from an activated official process."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
PROCESS_ID = "software-feature-development"
RUN_ID = "official-software-smoke"
TASK_ID = "official-software-task"


def run_pf(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-official-minimal-run-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        run_pf(
            "workplace-init",
            "--profile",
            "software-development",
            "--workplace",
            str(workplace),
            "--apply",
        )
        run_pf("project-init", "--project-root", str(project), "--workplace", str(workplace), "--apply")
        run_pf(
            "process-doctor",
            "--project-root",
            str(project),
            "--process",
            PROCESS_ID,
            "--contract-only",
        )
        run_pf(
            "run-create",
            "--project-root",
            str(project),
            "--id",
            RUN_ID,
            "--title",
            "Official software smoke",
            "--process",
            PROCESS_ID,
            "--apply",
        )
        run_pf(
            "task-create",
            "--project-root",
            str(project),
            "--run",
            RUN_ID,
            "--id",
            TASK_ID,
            "--title",
            "Minimal official task",
            "--process",
            PROCESS_ID,
            "--apply",
        )
        assignment_path = project / ".pf" / "assignments" / f"{TASK_ID}.yaml"
        run_pf("task-start", "--project-root", str(project), "--task", TASK_ID)
        run_pf(
            "assignment-capsule",
            "--project-root",
            str(project),
            "--assignment",
            str(assignment_path),
        )

        run_data = yaml.safe_load(
            (project / ".pf" / "runs" / RUN_ID / "run.yaml").read_text(encoding="utf-8")
        )
        task_data = yaml.safe_load(assignment_path.read_text(encoding="utf-8"))
        capsule_path = (
            project
            / ".pf"
            / "contexts"
            / "assignment-capsules"
            / f"{TASK_ID}.capsule.yaml"
        )
        assert run_data["process"] == PROCESS_ID, run_data
        assert task_data["process"] == PROCESS_ID, task_data
        assert task_data["status"] == "in_progress", task_data
        assert any(item.get("id") == TASK_ID for item in run_data.get("tasks", [])), run_data
        assert capsule_path.is_file(), capsule_path

        override_project = root / "override-project"
        override_project.mkdir()
        generic_workplace = root / "generic-workplace"
        run_pf("workplace-init", "--profile", "generic", "--workplace", str(generic_workplace), "--apply")
        run_pf("project-init", "--project-root", str(override_project), "--workplace", str(generic_workplace), "--apply")
        custom_process = override_project / ".pf" / "processes" / "custom" / f"{PROCESS_ID}.yaml"
        custom_process.parent.mkdir(parents=True, exist_ok=True)
        custom_process.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    f"id: {PROCESS_ID}",
                    "name: Project software override",
                    "version: 1.0.0",
                    "status: active",
                    "process_override:",
                    "  reason: project-specific workflow",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        run_pf(
            "run-create",
            "--project-root",
            str(override_project),
            "--id",
            "custom-override-run",
            "--title",
            "Custom override precedence",
            "--process",
            PROCESS_ID,
            "--apply",
        )
    print("PASS: smoke_official_process_can_start_minimal_run")


if __name__ == "__main__":
    main()
