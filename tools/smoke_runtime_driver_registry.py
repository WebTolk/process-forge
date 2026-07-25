#!/usr/bin/env python3
"""Smoke test for ProcessForge runtime driver registry MVP."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=60)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def main() -> int:
    listed = pf("runtime-driver", "list", "--project-root", str(ROOT)).stdout
    for driver_id in ["manual", "generic-shell", "test-echo-worker", "test-shell-agent"]:
        if driver_id not in listed:
            raise AssertionError(f"missing runtime driver in list: {driver_id}")
        if driver_id == "generic-shell":
            not_ready = pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", driver_id, expect=1).stdout
            if "start readiness executable override required" not in not_ready:
                raise AssertionError("generic-shell validate did not report missing executable readiness")
            pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", driver_id, "--executable", sys.executable)
        else:
            pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", driver_id)
        described = pf("runtime-driver", "describe", "--project-root", str(ROOT), "--driver", driver_id).stdout
        if f"id: {driver_id}" not in described:
            raise AssertionError(f"describe output missing id: {driver_id}")
    with tempfile.TemporaryDirectory(prefix="pf-runtime-driver-invalid-") as temp:
        invalid = Path(temp) / "invalid-limits.yaml"
        invalid.write_text(
            """schema_version: 1
id: invalid-limits
title: Invalid Limits
kind: shell
command:
  executable: "{python_executable}"
  args: []
limits:
  timeout_seconds: abc
  max_retries: -1
security:
  allow_shell: false
  require_explicit_executable: false
  allow_network: false
""",
            encoding="utf-8",
        )
        output = pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", str(invalid), expect=1).stdout
        if "limits.timeout_seconds" not in output or "limits.max_retries" not in output:
            raise AssertionError("invalid limits validation did not report both bad fields")
        reserved_env = Path(temp) / "reserved-env.yaml"
        reserved_env.write_text(
            """schema_version: 1
id: reserved-env
title: Reserved Env
kind: shell
command:
  executable: "{python_executable}"
  args: []
environment:
  inherit: false
  variables:
    PF_RUN_ID: wrong
limits:
  timeout_seconds: 5
  max_retries: 0
security:
  allow_shell: false
  require_explicit_executable: false
  allow_network: false
""",
            encoding="utf-8",
        )
        output = pf("runtime-driver", "validate", "--project-root", str(ROOT), "--driver", str(reserved_env), expect=1).stdout
        if "reserved ProcessForge env vars not overridden" not in output or "PF_RUN_ID" not in output:
            raise AssertionError("reserved env validation did not reject PF_RUN_ID override")
    print("PASS: runtime driver registry smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
