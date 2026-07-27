#!/usr/bin/env python3
"""Smoke test for the built-in process catalog contract doctor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def main() -> int:
    pf("builtin-process-catalog-doctor", "--root", str(ROOT), "--public")
    report = json.loads(pf("builtin-process-catalog-doctor", "--root", str(ROOT), "--public", "--json").stdout)
    summary = report["summary"]
    if summary["public_stable"] < 1:
        raise AssertionError("no public stable processes were counted")
    if summary["fail"] != 0:
        raise AssertionError(f"catalog doctor reported failures: {summary}")
    classifications = {item["classification"] for item in report["processes"]}
    if "PUBLIC_STABLE" not in classifications:
        raise AssertionError("PUBLIC_STABLE classification missing")
    if "PUBLIC_EXPERIMENTAL" not in classifications:
        raise AssertionError("PUBLIC_EXPERIMENTAL classification missing")
    if "INTERNAL_MAINTENANCE" not in classifications:
        raise AssertionError("INTERNAL_MAINTENANCE classification missing")
    print("PASS: built-in process catalog smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
