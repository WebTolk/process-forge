#!/usr/bin/env python3
"""Smoke-test the packaged bootstrap seam for direct-script runtime adapters."""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, path: Path) -> Any:
    module = sys.modules.get(module_name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_python(*args: str, input_text: str | None = None, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(REPO_ROOT),
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def main() -> int:
    bootstrap = load_module("processforge_core.bootstrap", REPO_ROOT / "src" / "processforge_core" / "bootstrap.py")
    runtime = bootstrap.bootstrap_runtime(__file__)
    assert runtime.repo_root == REPO_ROOT
    assert runtime.core.ROOT == REPO_ROOT
    assert sys.modules["processforge_core._legacy_processforge"] is runtime.core
    assert importlib.import_module("processforge") is runtime.core
    assert runtime.host.__name__ == "pf_runtime.host"
    assert runtime.service.__name__ == "pf_runtime.service"
    assert runtime.service.host is runtime.host

    adapter_runtime = bootstrap.bootstrap_runtime(REPO_ROOT / "tools" / "pf_runtime" / "mcp_server.py")
    assert adapter_runtime.core is runtime.core

    mcp_server = load_module("processforge_core_smoke_mcp_server", REPO_ROOT / "tools" / "pf_runtime" / "mcp_server.py")
    codex_hooks = load_module("processforge_core_smoke_codex_hooks", REPO_ROOT / "tools" / "pf_runtime" / "codex_hooks.py")
    assert mcp_server.runtime_bootstrap().core is runtime.core
    assert mcp_server.runtime_bootstrap().host is runtime.host
    assert codex_hooks.runtime_bootstrap().core is runtime.core
    assert codex_hooks.runtime_bootstrap().service is runtime.service

    mcp_help = run_python("tools/pf_runtime/mcp_server.py", "--workplace", str(REPO_ROOT), "--help")
    assert mcp_help.returncode == 0, mcp_help.stderr

    hook_payload = json.dumps(
        {
            "hook_event_name": "SessionStart",
            "source": "startup",
            "cwd": "C:/Windows",
            "session_id": "smoke-session",
            "turn_id": "t1",
            "tool_name": "Bash",
            "tool_use_id": "u1",
        }
    )
    hook_debug = run_python(
        "tools/pf_runtime/codex_hooks.py",
        input_text=hook_payload,
        extra_env={"PF_CODEX_HOOK_DEBUG": "1"},
    )
    assert hook_debug.returncode == 0, hook_debug.stderr
    assert '"status": "ignored"' in hook_debug.stdout
    assert '"reason": "not_processforge_project"' in hook_debug.stdout

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
