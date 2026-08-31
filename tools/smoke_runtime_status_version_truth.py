#!/usr/bin/env python3
"""Smoke test for explicit installed PF versus runtime instance status fields."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-runtime-truth-") as raw:
        workplace = Path(raw) / "workplace"
        subprocess.run([sys.executable, str(PF), "workplace-init", "--workplace", str(workplace), "--apply"], cwd=ROOT, check=True, text=True, encoding="utf-8", capture_output=True, timeout=120)
        result = subprocess.run([sys.executable, str(PF), "runtime", "status", "--workplace", str(workplace), "--json"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=120)
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        if not payload.get("installed_pf", {}).get("version"):
            raise AssertionError(payload)
        if payload.get("runtime", {}).get("running") is not False:
            raise AssertionError(payload)
        if payload.get("last_runtime_instance", {}).get("status") not in {"not_available", "historical"}:
            raise AssertionError(payload)
    print("PASS: runtime status separates installed PF from runtime instance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
