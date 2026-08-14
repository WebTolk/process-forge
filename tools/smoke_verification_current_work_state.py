#!/usr/bin/env python3
"""Focused proof for declaration-driven verification state and work state."""

from __future__ import annotations

import json
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


def project(base: Path, workplace: Path) -> tuple[Path, str, str]:
    root = base / "project-a"
    root.mkdir()
    (root / "README.md").write_text("# verification smoke\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(root), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    pf("run-create", "--project-root", str(root), "--id", "run-a", "--title", "A", "--process", "process-supervisor", "--status", "in_progress", "--apply")
    report = ".pf/artifacts/verification/result.md"
    pf("task-create", "--project-root", str(root), "--run", "run-a", "--id", "task-a", "--title", "A", "--process", "process-supervisor", "--objective", "verification", "--execution-mode", "assurance", "--allowed-file", report, "--required-output", f"id=result,path={report},type=markdown", "--expected-report-artifact", report, "--apply")
    pf("worker-run", "prepare", "--project-root", str(root), "--task", "task-a", "--driver", "manual")
    return root, "task-a", report


def rebuild(root: Path) -> None:
    pf("runtime-host", "rebuild-projections", "--project-root", str(root), "--json")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-verification-state-") as tmp:
        base = Path(tmp)
        workplace = base / "workplace"
        pf("init-workplace", "--root", str(workplace), "--apply")
        root, task, report = project(base, workplace)
        semantic = root / ".pf" / "artifacts" / "semantic.md"
        semantic.write_text("human-owned\n", encoding="utf-8")

        rebuild(root)
        payload = json.loads((root / ".pf" / "artifacts" / "projections" / "stage-obligations.json").read_text(encoding="utf-8"))
        verification = next(row for row in payload["obligations"] if row["projector"] == "verification-state")
        if verification["verification"]["result"] != "not_run":
            raise AssertionError("missing verification did not remain not_run")
        pf("runtime-host", "projection-doctor", "--project-root", str(root), expect=1)

        result = root / report
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text("first\n", encoding="utf-8")
        pf("task-doctor", "--project-root", str(root), "--task", task)
        rebuild(root)
        pf("runtime-host", "projection-doctor", "--project-root", str(root))

        event = {"event_type": "agent.session.started", "event_id": "verification-session", "project_root": str(root), "session_id": "verification-session", "agent_id": "codex", "source": {"adapter": "smoke", "agent": "codex", "session_id": "verification-session"}}
        event_path = base / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(event_path))
        sys.path.insert(0, str(ROOT / "tools"))
        from pf_runtime import host
        import processforge as core
        state = host.work_state_payload(workplace, core, session="verification-session")["current_work_state"]
        if state["blockers"] or not any(row.get("verification", {}).get("result") == "passed" for row in state["automation_bindings"]):
            raise AssertionError("current work state did not expose current passed verification")

        result.write_text("changed\n", encoding="utf-8")
        (root / ".pf" / "artifacts" / "projections" / "stage-obligations.json").unlink()
        rebuild(root)
        state = host.work_state_payload(workplace, core, session="verification-session")["current_work_state"]
        if not any(row.get("freshness") == "stale" for row in state["automation_bindings"]):
            raise AssertionError("stale verification did not survive deletion/rebuild")
        pf("runtime-host", "projection-doctor", "--project-root", str(root), expect=1)
        pf("task-doctor", "--project-root", str(root), "--task", task)
        rebuild(root)
        pf("runtime-host", "projection-doctor", "--project-root", str(root))

        result.unlink()
        failed_event = core.processforge_event(root, "task.doctor.failed", assignment_id_value=task, subject=task, payload={"task_id": task, "result": "fail"})
        core.append_process_event(root, failed_event)
        rebuild(root)
        failed = json.loads((root / ".pf" / "artifacts" / "projections" / "stage-obligations.json").read_text(encoding="utf-8"))
        row = next(item for item in failed["obligations"] if item["projector"] == "verification-state")
        if row["verification"]["result"] != "failed":
            raise AssertionError("failed doctor did not create failed verification")
        if semantic.read_text(encoding="utf-8") != "human-owned\n":
            raise AssertionError("projector overwrote semantic artifact")
    print("PASS: verification-state and current-work-state smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
