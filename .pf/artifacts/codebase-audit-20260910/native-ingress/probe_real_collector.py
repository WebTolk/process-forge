"""Run the real worker collector against a disposable on-disk PF project."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
CLI = REPO / "tools" / "processforge.py"
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import processforge as pf  # noqa: E402


def run_cli(*args: str) -> dict[str, object]:
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-real-collector-") as raw:
        root = Path(raw)
        project = root / "project"
        workplace = root / "workplace"
        project.mkdir()

        setup = [
            run_cli("workplace-init", "--workplace", str(workplace), "--apply"),
            run_cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply"),
            run_cli("run-create", "--project-root", str(project), "--id", "run-fixture", "--title", "Real collector fixture", "--process", "task-batch-execution", "--apply"),
        ]
        setup_status = [{"returncode": item["returncode"], "stderr": item["stderr"], "stdout_tail": str(item["stdout"])[-200:]} for item in setup]

        def create_task(task_id: str, report_rel: str, title: str) -> dict[str, object]:
            return run_cli(
                "task-create",
                "--project-root", str(project),
                "--run", "run-fixture",
                "--id", task_id,
                "--title", title,
                "--process", "task-batch-execution",
                "--required-output", f"id=report,path={report_rel},type=markdown,required=true",
                "--expected-report-artifact", report_rel,
                "--apply",
            )

        traversal_setup = create_task("task-fixture", "../outside.md", "Traversal report fixture")
        path_setup = create_task("task-path", ".pf/artifacts/path-report.md", "Path report fixture")
        outside = root / "outside.md"
        outside_content = "# Outside fixture\nsecret-free external report\n"
        outside.write_text(outside_content, encoding="utf-8")

        path_report = project / ".pf" / "artifacts" / "path-report.md"
        path_report.parent.mkdir(parents=True, exist_ok=True)
        path_report.write_text("# Worker report\n\nSource: C:\\workspace\\src\\module.py\n", encoding="utf-8")

        def prepare_state(task_id: str) -> None:
            paths = pf.worker_run_paths(project, "run-fixture", task_id)
            paths["root"].mkdir(parents=True, exist_ok=True)
            pf.json_write(paths["status"], {
                "schema_version": 1,
                "run_id": "run-fixture",
                "task_id": task_id,
                "status": "completed",
                "attempt": 1,
                "driver_id": "manual",
            })

        prepare_state("task-fixture")
        prepare_state("task-path")

        traversal_collect = run_cli("worker-run", "collect", "--project-root", str(project), "--task", "task-fixture")
        path_collect = run_cli("worker-run", "collect", "--project-root", str(project), "--task", "task-path")
        path_retry = run_cli("worker-run", "collect", "--project-root", str(project), "--task", "task-path")

        raw_worker_rows: list[dict[str, object]] = []
        raw_root = workplace / "runtime" / "agent-events"
        for shard in sorted(raw_root.rglob("*.ndjson")) if raw_root.is_dir() else []:
            for line in shard.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("raw_payload") if isinstance(row, dict) else None
                if isinstance(payload, dict) and payload.get("task_id") == "task-path":
                    raw_worker_rows.append({
                        "raw_event_id": row.get("raw_event_id"),
                        "native_event_type": row.get("native_event_type"),
                        "raw_payload_report_content": payload.get("report_content"),
                        "raw_shard": str(shard),
                    })

        def capture_state(task_id: str) -> dict[str, object]:
            task_path = project / ".pf" / "assignments" / f"{task_id}.yaml"
            task = pf.load_task(project, task_id) if task_path.is_file() else {}
            expected = pf.expected_report_artifact(task) if task else ""
            session = f"pf-worker:run-fixture:{task_id}:attempt:1"
            transcript = pf.chat_transcript_path(project, session)
            messages = pf.load_chat_messages(project, session) if transcript.is_file() else []
            return {
                "task": task,
                "expected_report_helper": expected,
                "collector_report_path": str(project / expected) if expected else "",
                "collector_report_resolves_inside_project": bool(expected) and pf.path_is_relative_to(project / expected, project),
                "transcript_path": str(transcript),
                "transcript_messages": messages,
                "task_after_collect": pf.load_task(project, task_id) if task_path.is_file() else {},
            }

        traversal_state = capture_state("task-fixture")
        path_state = capture_state("task-path")
        result = {
            "setup": setup_status,
            "task_create_traversal": traversal_setup,
            "task_create_path": path_setup,
            "outside_exists": outside.is_file(),
            "outside_path": str(outside),
            "traversal": {"collect": traversal_collect, **traversal_state},
            "path_report": {"collect": path_collect, "retry": path_retry, "raw_worker_rows": raw_worker_rows, **path_state},
        }
        out = Path(__file__).with_name("evidence") / "real-collector-result.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
