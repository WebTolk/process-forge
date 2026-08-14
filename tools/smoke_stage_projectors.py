#!/usr/bin/env python3
"""Focused proof for declaration-driven stage obligation projections."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import diagnostic_text, run_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, cwd: Path = ROOT, expect: int = 0) -> str:
    result = run_command([sys.executable, str(CLI), *args], cwd=cwd, timeout=60)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result.stdout + result.stderr


def create_project(base: Path, name: str, workplace: Path) -> tuple[Path, str, str]:
    project = base / name
    project.mkdir()
    (project / "README.md").write_text("# projector smoke\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    run_id = f"run-{name}"
    task_id = f"task-{name}"
    pf("run-create", "--project-root", str(project), "--id", run_id, "--title", name, "--process", "process-supervisor", "--status", "in_progress", "--apply")
    report = f".pf/artifacts/{name}/result.md"
    pf(
        "task-create",
        "--project-root", str(project),
        "--run", run_id,
        "--id", task_id,
        "--title", name,
        "--process", "process-supervisor",
        "--objective", "projection smoke",
        "--execution-mode", "assurance",
        "--allowed-file", report,
        "--required-output", f"id=result,path={report},type=markdown",
        "--expected-report-artifact", report,
        "--apply",
    )
    pf("worker-run", "prepare", "--project-root", str(project), "--task", task_id, "--driver", "manual")
    return project, task_id, report


def rebuild(project: Path) -> dict[str, object]:
    raw = pf("runtime-host", "rebuild-projections", "--project-root", str(project), "--json")
    return json.loads(raw)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-stage-projectors-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        pf("init-workplace", "--root", str(workplace), "--apply")
        project_a, task_a, report_a = create_project(root, "project-a", workplace)
        project_b, _task_b, _report_b = create_project(root, "project-b", workplace)
        semantic = project_a / ".pf" / "artifacts" / "semantic.md"
        semantic.write_text("human-owned semantic body\n", encoding="utf-8")

        rebuild(project_a)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a), expect=1)
        projection = project_a / ".pf" / "artifacts" / "projections" / "stage-obligations.json"
        missing = json.loads(projection.read_text(encoding="utf-8"))
        if missing["obligations"][0]["readiness"] != "missing":
            raise AssertionError("missing required output was not projected")

        report_path = project_a / report_a
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("automatic test output\n", encoding="utf-8")
        pf("task-doctor", "--project-root", str(project_a), "--task", task_a)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a), expect=1)
        rebuild(project_a)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a))
        if semantic.read_text(encoding="utf-8") != "human-owned semantic body\n":
            raise AssertionError("projector overwrote a semantic artifact")

        report_path.write_text("changed after projection\n", encoding="utf-8")
        stale = pf("runtime-host", "projection-doctor", "--project-root", str(project_a), expect=1)
        if "stale" not in stale:
            raise AssertionError("changed output did not make projection stale")
        pf("task-doctor", "--project-root", str(project_a), "--task", task_a)
        rebuild(project_a)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a))

        projection.unlink()
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a), expect=1)
        rebuild(project_a)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a))

        rebuild(project_b)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_b), expect=1)
        pf("runtime-host", "projection-doctor", "--project-root", str(project_a))

        event = {
            "event_type": "agent.session.started",
            "event_id": "projection-smoke-session",
            "project_root": str(project_a),
            "session_id": "projection-smoke-session",
            "agent_id": "codex",
            "source": {"adapter": "smoke", "agent": "codex", "session_id": "projection-smoke-session"},
        }
        input_path = root / "event.json"
        input_path.write_text(json.dumps(event), encoding="utf-8")
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(input_path))
        sys.path.insert(0, str(ROOT / "tools"))
        from pf_runtime import host  # Imported only after the CLI proof above.
        import processforge as core

        work_state = host.work_state_payload(workplace, core, session="projection-smoke-session")
        if work_state.get("projections", {}).get("stage_obligations", {}).get("status") != "current":
            raise AssertionError("work state did not expose the current projection")
        if task_a not in {str(row.get("task_id")) for row in work_state["projections"]["stage_obligations"]["obligations"]}:
            raise AssertionError("work state omitted the active collect obligation")
    print("PASS: declaration-driven stage projector smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
