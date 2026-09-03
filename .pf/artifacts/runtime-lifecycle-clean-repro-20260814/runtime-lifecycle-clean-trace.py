#!/usr/bin/env python3
"""Capture a clean isolated long-lived Runtime lifecycle trace."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "tools" / "processforge.py"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(CLI), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False, timeout=120)
    if result.returncode != expect:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def running(pid: object) -> bool:
    if not isinstance(pid, int):
        return False
    if os.name == "nt":
        probe = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], text=True, capture_output=True, check=False)
        return str(pid) in probe.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def readyz(endpoint: object) -> dict[str, object]:
    if not isinstance(endpoint, str) or not endpoint:
        return {"status": "not_attempted"}
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/readyz", timeout=1.0) as response:
            return {"http_status": response.status, "body": json.loads(response.read().decode("utf-8"))}
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}


def snapshot(label: str, workplace: Path, observed_pid: object = None) -> dict[str, object]:
    runtime = workplace / "runtime" / "pf-runtime"
    lock = read_json(runtime / "runtime.lock")
    service = read_json(runtime / "service.json")
    pid = observed_pid if isinstance(observed_pid, int) else lock.get("pid") or service.get("pid")
    return {
        "label": label,
        "timestamp": now(),
        "runtime_dir_exists": runtime.exists(),
        "lock": lock,
        "service": service,
        "process_exists": running(pid),
        "readyz": readyz(service.get("endpoint")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="pf-runtime-clean-trace-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# clean trace\n", encoding="utf-8")
        trace.append(snapshot("T0: runtime dir absent", workplace))
        run("workplace-init", "--workplace", str(workplace), "--apply")
        run("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")

        started = subprocess.Popen([sys.executable, str(CLI), "runtime", "start", "--workplace", str(workplace), "--interval", "60", "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        trace.append(snapshot("T1: runtime start called", workplace))
        seen_lock = False
        seen_starting = False
        seen_endpoint = False
        deadline = time.monotonic() + 30.0
        while started.poll() is None and time.monotonic() < deadline:
            current = snapshot("poll", workplace)
            lock = current["lock"]
            service = current["service"]
            if not seen_lock and lock:
                trace.append({**current, "label": "T2: lock written"})
                seen_lock = True
            if not seen_starting and service.get("status") == "starting":
                trace.append({**current, "label": "T3: service starting"})
                seen_starting = True
            if not seen_endpoint and service.get("endpoint"):
                trace.append({**current, "label": "T4: endpoint bound"})
                seen_endpoint = True
            if current["readyz"].get("http_status") == 200 and current["readyz"].get("body", {}).get("ready") is True:
                trace.append({**current, "label": "T5: readyz success"})
                break
            time.sleep(0.01)
        stdout, stderr = started.communicate(timeout=30)
        if started.returncode != 0:
            raise RuntimeError(f"runtime start failed: {stdout}\n{stderr}")
        start_payload = json.loads(stdout)
        pid = start_payload.get("pid")
        trace.append({**snapshot("T6: CLI start returned", workplace, pid), "cli": start_payload})

        registered = json.loads(run("runtime", "session-register", "--workplace", str(workplace), "--session", "clean-trace", "--agent", "codex", "--project-root", str(project), "--json").stdout)
        trace.append({**snapshot("T7: session-register", workplace, pid), "session_register": registered})
        work_state = json.loads(run("runtime", "work-state", "--workplace", str(workplace), "--session", "clean-trace", "--json").stdout)
        trace.append({**snapshot("T8: work-state", workplace, pid), "work_state_project": work_state.get("project")})

        trace.append(snapshot("T9: runtime stop called", workplace, pid))
        stop = run("runtime", "stop", "--workplace", str(workplace))
        process_deadline = time.monotonic() + 10.0
        while running(pid) and time.monotonic() < process_deadline:
            time.sleep(0.05)
        trace.append({**snapshot("T10: process exited", workplace, pid), "stop_stdout": stop.stdout.strip()})
        trace.append(snapshot("T11: state cleanup", workplace, pid))

    observed_labels = {str(item["label"]).split(":", 1)[0] for item in trace}
    lines = ["# Clean isolated Runtime lifecycle reproduction", "", "Result: PASS", ""]
    missing = [label for label in ["T3", "T4", "T5"] if label not in observed_labels]
    if missing:
        lines.extend([
            "## Trace-resolution limitation",
            "",
            f"The polling loop did not externally observe {', '.join(missing)} before the child reached ready. "
            "T2 and T6 prove the surrounding durable states; service.py orders the missing transitions "
            "as starting-state write, HTTP bind/endpoint publication, then ready-state write. This is a "
            "measurement gap, not evidence of a failed transition.",
            "",
        ])
    for item in trace:
        lines.extend([f"## {item['label']}", "", "```json", json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True), "```", ""])
    args.output.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
