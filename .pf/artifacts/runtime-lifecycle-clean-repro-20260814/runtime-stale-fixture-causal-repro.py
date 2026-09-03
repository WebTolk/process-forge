#!/usr/bin/env python3
"""Safely reproduce the checkout's stale Runtime metadata pattern."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "tools" / "processforge.py"


def pf(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(CLI), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stdout}\n{result.stderr}")
    return result


def service_path(workplace: Path) -> Path:
    return workplace / "runtime" / "pf-runtime" / "service.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pf-runtime-stale-fixture-", ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# stale fixture\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("runtime", "start", "--workplace", str(workplace), "--json")
        pf("runtime", "stop", "--workplace", str(workplace))

        path = service_path(workplace)
        fixture = json.loads(path.read_text(encoding="utf-8"))
        fixture.update({"status": "ready", "health": "ready", "pid": 999999, "endpoint": "http://127.0.0.1:9"})
        path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        lock = path.with_name("runtime.lock")
        lock.unlink(missing_ok=True)

        stale = json.loads(pf("runtime", "status", "--workplace", str(workplace), "--json").stdout)
        if stale.get("status") != "stale":
            raise AssertionError(f"fixture was not classified stale: {stale}")
        restarted = json.loads(pf("runtime", "start", "--workplace", str(workplace), "--json").stdout)
        if restarted.get("status") != "started":
            raise AssertionError(f"stale fixture did not recover: {restarted}")
        registered = json.loads(pf("runtime", "session-register", "--workplace", str(workplace), "--session", "stale-fixture", "--agent", "codex", "--project-root", str(project), "--json").stdout)
        work_state = json.loads(pf("runtime", "work-state", "--workplace", str(workplace), "--session", "stale-fixture", "--json").stdout)
        stopped = pf("runtime", "stop", "--workplace", str(workplace)).stdout.strip()
        final = json.loads(pf("runtime", "status", "--workplace", str(workplace), "--json").stdout)

    lines = [
        "# Stale Runtime metadata causal fixture",
        "",
        "Result: PASS",
        "",
        "The isolated fixture used the same material pattern as the current checkout: a `ready` service record, no `runtime.lock`, a dead PID, and an unreachable endpoint.",
        "",
        f"- Fixture classification: `{stale.get('status')}` / `{stale.get('health')}`",
        f"- Automatic restart result: `{restarted.get('status')}`",
        f"- Session registration returned a project handle: `{bool(registered.get('project'))}`",
        f"- Work-state returned a project: `{bool(work_state.get('project'))}`",
        f"- Stop result: `{stopped}`",
        f"- Final classification: `{final.get('status')}` / `{final.get('health')}`",
        "",
        "Conclusion: this metadata pattern deterministically explains a `stale` status, but it does not reproduce `started -> stale while PID alive`; the current implementation recovers it on the next start.",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
