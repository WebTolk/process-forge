#!/usr/bin/env python3
"""Focused smoke for doctor-project effective .gitignore protection."""

from __future__ import annotations

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
    with tempfile.TemporaryDirectory(prefix="pf-doctor-gitignore-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        cli("workplace-init", "--workplace", str(workplace), "--apply")
        cli("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic", "--apply")
        subprocess.run(["git", "init", "-q"], cwd=project, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (project / ".gitignore").write_text(".codex/hooks.json\n.pf/\n", encoding="utf-8")
        result = cli("doctor-project", "--project-root", str(project), check=False)
        output = result.stdout + result.stderr
        for entry in [".codex/hooks.json", ".pf/process-forge.local.yaml", ".pf/runtime/", ".pf/cache/"]:
            if f"PASS: .gitignore protects {entry}" not in output:
                raise AssertionError(f"effective protection was not accepted for {entry}:\n{output}")
            if f"FAIL: .gitignore missing {entry}" in output:
                raise AssertionError(f"effective protection was reported as a hard failure for {entry}:\n{output}")
        if "WARN: .gitignore missing recommended explicit entry .pf/runtime/" not in output:
            raise AssertionError(f"recommended explicit policy warning missing:\n{output}")
    print("PASS: doctor-project accepts effective gitignore protection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
