#!/usr/bin/env python3
"""Focused proof for opt-in, reversible project-local Codex hook registration."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "tools" / "pf_runtime" / "codex_integration.py"


def invoke(*args: str) -> dict[str, object]:
    result = subprocess.run([sys.executable, str(INSTALLER), *args], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=30)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="pf-codex-integration-"))
    try:
        codex = root / ".codex"
        codex.mkdir()
        target = codex / "hooks.json"
        target.write_text(json.dumps({"description": "operator hooks", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "operator-hook"}]}]}}), encoding="utf-8")
        dry_run = invoke("install", "--project-root", str(root))
        if dry_run.get("applied") or json.loads(target.read_text(encoding="utf-8"))["hooks"]["Stop"][0]["hooks"][0]["command"] != "operator-hook":
            raise AssertionError("dry-run modified an existing hook configuration")
        installed = invoke("install", "--project-root", str(root), "--apply")
        if not installed.get("backup") or not Path(str(installed["backup"])).is_file():
            raise AssertionError("apply did not create a rollback backup")
        status = invoke("status", "--project-root", str(root))
        if not status.get("complete"):
            raise AssertionError("all PF observation hooks were not registered")
        installed_config = json.loads(target.read_text(encoding="utf-8"))
        for event, groups in installed_config["hooks"].items():
            for group in groups:
                for handler in group.get("hooks", []):
                    if handler.get("commandWindows", "").endswith("codex_hooks.py\""):
                        if not handler.get("command") or handler.get("timeout") != 3 or (event != "SessionEnd" and handler.get("async") is not True):
                            raise AssertionError("observation hooks were not configured as bounded background work")
        repeated = invoke("install", "--project-root", str(root), "--apply")
        if repeated.get("changed_events"):
            raise AssertionError("hook installation was not idempotent")
        removed = invoke("remove", "--project-root", str(root), "--apply")
        if not removed.get("changed_events"):
            raise AssertionError("managed hook removal did not remove any handlers")
        restored = json.loads(target.read_text(encoding="utf-8"))
        if restored["hooks"]["Stop"][0]["hooks"][0]["command"] != "operator-hook":
            raise AssertionError("managed hook removal damaged an operator hook")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS: Codex integration installer smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
