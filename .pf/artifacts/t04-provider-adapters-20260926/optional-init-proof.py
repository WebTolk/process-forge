#!/usr/bin/env python3
"""Exercise real project initialization/status with optional Codex failures."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"
PF = TOOLS / "processforge.py"


def load_core():
    tools_text = str(TOOLS)
    if tools_text not in sys.path:
        sys.path.insert(0, tools_text)
    spec = importlib.util.spec_from_file_location("pf_optional_init_proof_core", PF)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source CLI module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_workplace(path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(PF), "workplace-init", "--workplace", str(path), "--apply"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("isolated workplace initialization failed")


def scenario(core, workplace: Path, project: Path, name: str, behavior):
    project.mkdir(parents=True, exist_ok=True)
    original = core.project_codex_integration_status
    if behavior == "missing_callable":
        replacement = None
    elif behavior == "malformed_response":
        replacement = lambda _root: {"status": "not-a-supported-status", "private_path": "SHOULD_NOT_ESCAPE"}
    elif behavior in {"import_error", "runtime_error"}:
        exception_type = ImportError if behavior == "import_error" else RuntimeError
        replacement = lambda _root: (_ for _ in ()).throw(exception_type("private failure detail"))
    else:
        raise AssertionError("unknown scenario")

    # Invoke the actual source command/service with only the optional callback replaced.
    out = io.StringIO()
    status_out = io.StringIO()
    with patch.object(core, "project_codex_integration_status", replacement):
        with contextlib.redirect_stdout(out):
            onboard_rc = core.command_init_project(argparse.Namespace(
                project_root=str(project), workplace=str(workplace), answers=None,
                project_type="generic", coordination_mode=None, platform=[],
                specialization=[], process=None, force=False,
                allow_missing_workplace=False, apply=True, command="project-onboard",
            ))
        with contextlib.redirect_stdout(status_out):
            status_rc = core.command_project_init_status(argparse.Namespace(
                project_root=str(project), workplace=str(workplace), json=True,
            ))
    status_payload = json.loads(status_out.getvalue())
    codex = status_payload.get("codex_integration") or {}
    expected_error = "optional_integration_result_invalid" if behavior == "malformed_response" else "optional_integration_unavailable"
    hooks_created = (project / ".codex" / "hooks.json").exists()
    passed = (
        onboard_rc == 0 and status_rc == 0
        and status_payload.get("state") == "complete"
        and codex.get("status") == "unavailable"
        and codex.get("required") is False
        and codex.get("severity") == "info"
        and codex.get("error") == expected_error
        and "install_codex_hooks" not in status_payload.get("repair_plan", [])
        and not hooks_created
        and "SHOULD_NOT_ESCAPE" not in out.getvalue()
        and "private failure detail" not in out.getvalue()
    )
    return {
        "scenario": name,
        "onboard_exit_code": onboard_rc,
        "status_exit_code": status_rc,
        "project_state": status_payload.get("state"),
        "codex_status": codex.get("status"),
        "codex_error": codex.get("error"),
        "hooks_created": hooks_created,
        "passed": passed,
    }


def main() -> int:
    core = load_core()
    results = []
    with tempfile.TemporaryDirectory(prefix="pf-t04-optional-init-") as raw:
        temp = Path(raw)
        workplace = temp / "workplace"
        create_workplace(workplace)
        for name in ("import_error", "runtime_error", "missing_callable", "malformed_response"):
            results.append(scenario(core, workplace, temp / name, name, name))
    result = {
        "schema_version": 1,
        "kind": "pf.t04.optional_initialization_proof",
        "source_checkout": True,
        "scenarios": results,
        "passed": all(item["passed"] for item in results),
        "boundary": "temporary workplace/projects; no shared registry or installed host touched",
    }
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
