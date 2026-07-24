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
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_heartbeat(path: Path, mode: str, sequence: int) -> None:
    write_json(
        path,
        {
            "schema_version": 1,
            "status": "alive",
            "mode": mode,
            "sequence": sequence,
            "updated_at": now_utc(),
            "pid": os.getpid(),
        },
    )


def write_report(path: Path, mode: str, capsule: Path, worker_prompt: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    leak_keys = sorted(key for key in os.environ if key.startswith("PF_LEAK_TEST"))
    lines = [
        "# Test Shell Agent Report",
        "",
        f"- status: `completed`",
        f"- mode: `{mode}`",
        f"- capsule_exists: `{str(capsule.is_file()).lower()}`",
        f"- worker_prompt_exists: `{str(worker_prompt.is_file()).lower()}`",
        f"- leak_keys: `{len(leak_keys)}`",
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
    args = parser.parse_args()

    capsule = Path(args.capsule)
    worker_prompt = Path(args.worker_prompt)
    output = Path(args.output)
    heartbeat = Path(args.heartbeat)
    write_heartbeat(heartbeat, args.mode, 0)

    print(json.dumps({"event": "pf_shell_agent.started", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
    if args.mode == "sleep":
        deadline = time.perf_counter() + max(0.0, float(args.sleep_seconds))
        interval = max(0.05, float(args.heartbeat_interval or 0.25))
        sequence = 1
        while time.perf_counter() < deadline:
            time.sleep(min(interval, max(0.0, deadline - time.perf_counter())))
            write_heartbeat(heartbeat, args.mode, sequence)
            sequence += 1
    if args.mode in {"success", "env-dump", "sleep"}:
        write_report(output, args.mode, capsule, worker_prompt)
        print(json.dumps({"event": "pf_shell_agent.completed", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
        return 0
    write_report(output, args.mode, capsule, worker_prompt)
    print(json.dumps({"event": "pf_shell_agent.failed", "mode": args.mode, "pid": os.getpid()}, sort_keys=True), flush=True)
    return 7


if __name__ == "__main__":
    raise SystemExit(main())
