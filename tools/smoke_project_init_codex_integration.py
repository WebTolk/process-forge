#!/usr/bin/env python3
"""Focused smoke for project-init Codex hook status and repair."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "tools" / "processforge.py"


def cli(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=120,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-init-codex-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic",
            "--apply",
        )
        hooks = project / ".codex" / "hooks.json"
        if hooks.exists():
            raise AssertionError("generic project-onboard unexpectedly installed Codex hooks")
        status = json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)
        codex = status.get("codex_integration") if isinstance(status.get("codex_integration"), dict) else {}
        if (
            status.get("state") != "complete"
            or codex.get("status") != "missing"
            or codex.get("required") is not False
            or codex.get("severity") != "info"
            or "install_codex_hooks" in status.get("repair_plan", [])
        ):
            raise AssertionError(f"missing optional hooks affected generic readiness: {status}")

        repair = cli(
            "project-init-repair",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--repair-action",
            "install_codex_hooks",
            "--apply",
        ).stdout
        if "install_codex_hooks" not in repair or not hooks.is_file():
            raise AssertionError("hook repair did not reinstall hooks")
        repaired = json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)
        if repaired.get("state") != "complete" or repaired.get("codex_integration", {}).get("status") != "installed":
            raise AssertionError(f"repaired hooks are not installed: {repaired}")

        hooks.unlink()
        missing_again = json.loads(cli("project-init-status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)
        if missing_again.get("state") != "complete" or "install_codex_hooks" in missing_again.get("repair_plan", []):
            raise AssertionError(f"removing optional hooks changed generic readiness: {missing_again}")
    print("PASS: project-init keeps Codex hooks optional and supports explicit operator installation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
