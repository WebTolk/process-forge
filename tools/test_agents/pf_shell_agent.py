#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_heartbeat(path: Path, mode: str, sequence: int, status: str = "running") -> None:
    timestamp = now_utc()
    write_json(
        path,
        {
            "schema_version": "1.0",
            "run_id": os.environ.get("PF_RUN_ID") or os.environ.get("PF_WORKER_RUN_ID", ""),
            "task_id": os.environ.get("PF_TASK_ID") or os.environ.get("PF_WORKER_TASK_ID", ""),
            "status": status,
            "mode": mode,
            "sequence": sequence,
            "timestamp": timestamp,
            "updated_at": timestamp,
            "pid": os.getpid(),
            "agent_run_dir": os.environ.get("PF_AGENT_RUN_DIR", ""),
            "project_root": os.environ.get("PF_PROJECT_ROOT", ""),
            "driver_id": os.environ.get("PF_RUNTIME_DRIVER_ID", ""),
        },
    )


def write_exit(status: str, exit_code: int, skip: bool = False) -> None:
    if skip:
        return
    raw_path = os.environ.get("PF_AGENT_EXIT_PATH")
    if raw_path:
        write_json(Path(raw_path), {"schema_version": 1, "exit_code": exit_code, "finished_at": now_utc(), "status": status})


def write_report(path: Path, mode: str, status: str, capsule: Path, worker_prompt: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    leak_keys = sorted(key for key in os.environ if key.startswith("PF_LEAK_TEST"))
    lines = [
        "# Test Shell Agent Report",
        "",
        f"- status: `{status}`",
        f"- mode: `{mode}`",
        f"- capsule_exists: `{str(capsule.is_file()).lower()}`",
        f"- worker_prompt_exists: `{str(worker_prompt.is_file()).lower()}`",
        f"- leak_keys: `{len(leak_keys)}`",
        f"- run_id: `{os.environ.get('PF_RUN_ID', '')}`",
        f"- task_id: `{os.environ.get('PF_TASK_ID', '')}`",
        f"- agent_run_dir_present: `{str(bool(os.environ.get('PF_AGENT_RUN_DIR'))).lower()}`",
        f"- project_root_present: `{str(bool(os.environ.get('PF_PROJECT_ROOT'))).lower()}`",
        f"- worker_run_id_present: `{str('PF_WORKER_RUN_ID' in os.environ).lower()}`",
        f"- worker_task_id_present: `{str('PF_WORKER_TASK_ID' in os.environ).lower()}`",
        f"- completed_at: `{now_utc()}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Neutral ProcessForge shell-launched test agent.")
    parser.add_argument("--capsule", required=True, help="Assignment capsule path.")
    parser.add_argument("--worker-prompt", required=True, help="Worker launch prompt path.")
    parser.add_argument("--output", required=True, help="Expected report path.")
    parser.add_argument("--heartbeat", required=True, help="Heartbeat JSON path.")
    parser.add_argument("--mode", choices=["success", "env-dump", "fail", "sleep"], default="success")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--heartbeat-interval", type=float, default=0.0)
    parser.add_argument("--skip-exit-marker", action="store_true")
    args = parser.parse_args()

    capsule = Path(args.capsule)
    worker_prompt = Path(args.worker_prompt)
    output = Path(args.output)
    heartbeat = Path(args.heartbeat)
    write_heartbeat(heartbeat, args.mode, 0)

    print(json.dumps({"event": "pf_shell_agent.started", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
    sequence = 0
    if args.mode == "sleep" or (args.mode == "fail" and args.sleep_seconds > 0):
        deadline = time.perf_counter() + max(0.0, float(args.sleep_seconds))
        interval = max(0.05, float(args.heartbeat_interval or 0.25))
        sequence = 1
        while time.perf_counter() < deadline:
            time.sleep(min(interval, max(0.0, deadline - time.perf_counter())))
            write_heartbeat(heartbeat, args.mode, sequence)
            sequence += 1
    if args.mode in {"success", "env-dump", "sleep"}:
        write_heartbeat(heartbeat, args.mode, sequence + 1, "completed")
        write_report(output, args.mode, "completed", capsule, worker_prompt)
        write_exit("completed", 0, args.skip_exit_marker)
        print(json.dumps({"event": "pf_shell_agent.completed", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
        return 0
    write_heartbeat(heartbeat, args.mode, sequence + 1, "failed")
    write_report(output, args.mode, "failed", capsule, worker_prompt)
    write_exit("failed", 7, args.skip_exit_marker)
    print(json.dumps({"event": "pf_shell_agent.failed", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
    return 7


if __name__ == "__main__":
    raise SystemExit(main())
