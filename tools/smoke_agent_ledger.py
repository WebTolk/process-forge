#!/usr/bin/env python3
"""Smoke test for agent registry, ledger, presence, availability, and leases."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 90) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-agent-ledger-") as temp:
        workplace = Path(temp) / "workplace"
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("agent-register", "--workplace", str(workplace), "--agent", "director-local", "--role", "director", "--role", "orchestrator", "--capability", "process.routing")
        pf("agent-register", "--workplace", str(workplace), "--agent", "decomposer-local", "--role", "decomposer", "--capability", "task.decomposition")
        pf("agent-checkin", "--workplace", str(workplace), "--agent", "director-local", "--session", "sess-director-001", "--process", "feature-development", "--run", "feature-run", "--role", "director", "--role", "orchestrator")
        unavailable = json.loads(pf("agent-availability", "--workplace", str(workplace), "--role", "decomposer", "--json").stdout)
        if unavailable["available"]:
            raise AssertionError("decomposer unexpectedly available before checkin")
        pf("agent-checkin", "--workplace", str(workplace), "--agent", "decomposer-local", "--session", "sess-decomposer-001", "--process", "task-decomposition", "--run", "decomp-run", "--role", "decomposer")
        available = json.loads(pf("agent-availability", "--workplace", str(workplace), "--role", "decomposer", "--json").stdout)
        if not available["available"]:
            raise AssertionError("decomposer not available after checkin")
        pf("agent-lease-grant", "--workplace", str(workplace), "--id", "lease-decomposer", "--agent", "decomposer-local", "--session", "sess-decomposer-001", "--process", "task-decomposition", "--run", "decomp-run", "--task", "decompose-task", "--allowed-file", ".pf/artifacts/**")
        pf("agent-lease-release", "--workplace", str(workplace), "--lease", "lease-decomposer")
        pf("agent-checkout", "--workplace", str(workplace), "--agent", "decomposer-local", "--session", "sess-decomposer-001")
        pf("agent-ledger-doctor", "--workplace", str(workplace))
        ledger = workplace / "runtime" / "agent-ledger" / "sessions.ndjson"
        if "agent.checked_in" not in ledger.read_text(encoding="utf-8"):
            raise AssertionError("ledger did not store check-in event")
    print("PASS: agent ledger smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
