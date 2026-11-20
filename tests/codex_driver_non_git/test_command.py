"""Codex repository trust must not replace PF prepared-input authorization."""

from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import codex_exec_worker as worker
import pf_native_control as native
import prepared_executor
import pytest

from processforge_core import diagnostics
from processforge_core.prepared import command as prepared_command
from processforge_core.runtime import command as runtime_command


@pytest.fixture
def launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    project = tmp_path / "project"
    project.mkdir()
    capsule = project / ".pf/contexts/capsule.yaml"
    output = project / ".pf/artifacts/report.md"
    prepared = {
        "input": {
            "capsule": {"path": ".pf/contexts/capsule.yaml"},
            "outputs": {"expected_report": {"artifact": ".pf/artifacts/report.md"}},
        }
    }
    argv = [
        "codex_exec_worker.py",
        "--worker-prompt",
        str(project / "prompt.md"),
        "--capsule",
        str(capsule),
        "--workspace-access",
        str(project / "access.yaml"),
        "--output",
        str(output),
    ]
    environment = {
        "PF_PROJECT_ROOT": str(project),
        "PF_AGENT_MODEL": "fixture-model",
        "PF_CODEX_SANDBOX": "read-only",
        "PF_CODEX_REASONING_EFFORT": "low",
        "PF_AGENT_RUN_DIR": str(project / ".pf/runtime/agent-runs/run/task"),
        "PF_PREPARED_INPUT_FILE": str(
            project / ".pf/runtime/agent-runs/run/task/attempts/1/prepared-input.json"
        ),
        "PF_PREPARED_INPUT_SHA256": "sha256:" + "a" * 64,
        "PF_CODEX_EXTRA_READ_DIR": str(tmp_path),
    }
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(os, "environ", environment)
    monkeypatch.setattr(native, "operation_lease", contextlib.nullcontext)
    monkeypatch.setattr(worker, "codex_executable", lambda: "fixture-codex")
    monkeypatch.setattr(
        worker, "managed_hook_trust_args", lambda _: ["-c", "fixture_hook_trust=true"]
    )
    monkeypatch.setattr(
        prepared_executor, "load_and_validate_manifest", lambda *_: prepared
    )
    monkeypatch.setattr(runtime_command, "load_configuration_snapshot", lambda *_: None)
    monkeypatch.setattr(prepared_command, "scratch_environment", lambda _doc, env: env)
    monkeypatch.setattr(
        worker, "prompt_payload", lambda *_: "prepared payload: Проверка"
    )
    monkeypatch.setattr(worker, "capture_worker_input", lambda *_: None)
    monkeypatch.setattr(diagnostics, "for_project", lambda *a, **k: None)
    monkeypatch.setattr(
        diagnostics, "operation", lambda *a, **k: contextlib.nullcontext()
    )
    monkeypatch.setattr(diagnostics, "identity_for", lambda *_: "fixture")
    monkeypatch.setattr(diagnostics, "emit", lambda *a, **k: None)
    calls = []
    payloads = []

    class Capture:
        def __init__(self, *args, **kwargs):
            pass

        def begin(self):
            return io.BytesIO()

        def start_execution(self):
            pass

        def finish(self):
            pass

    class Child:
        returncode = 0

        def communicate(self, payload):
            payloads.append(payload)

    def spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return Child()

    monkeypatch.setattr(worker, "ManagedUsageCapture", Capture)
    monkeypatch.setattr(native, "spawn_owned", spawn)
    return SimpleNamespace(
        project=project,
        argv=argv,
        environment=environment,
        calls=calls,
        payloads=payloads,
    )


@pytest.mark.parametrize("git_marker", [False, True])
def test_prepared_argv_preserves_guards_and_permissions(launch, git_marker):
    if git_marker:
        (launch.project / ".git").mkdir()
    assert worker.main() == 0
    assert len(launch.calls) == 1
    argv, kwargs = launch.calls[0]
    assert argv[:5] == [
        "fixture-codex",
        "-c",
        "fixture_hook_trust=true",
        "exec",
        "--skip-git-repo-check",
    ]
    assert argv.count("--skip-git-repo-check") == 1
    assert argv[argv.index("-m") + 1] == "fixture-model"
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert argv[argv.index("--cd") + 1] == str(launch.project)
    assert "--add-dir" not in argv
    assert argv[-4:] == [
        "--json",
        "-o",
        str(launch.project / ".pf/artifacts/report.md"),
        "-",
    ]
    assert kwargs["env"]["PF_PREPARED_INPUT_SHA256"] == "sha256:" + "a" * 64
    assert launch.payloads == ["prepared payload: Проверка".encode("utf8")]


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("capsule", "prepared_capsule_pointer_mismatch"),
        ("report", "prepared_report_pointer_mismatch"),
        ("prepared", "prepared_input_required"),
        ("model", "Codex model is not configured"),
    ],
)
def test_invalid_prepared_launch_refuses_before_spawn(launch, fault, expected):
    if fault in {"capsule", "report"}:
        option = "--capsule" if fault == "capsule" else "--output"
        launch.argv[launch.argv.index(option) + 1] = str(launch.project / "foreign")
    elif fault == "prepared":
        del launch.environment["PF_PREPARED_INPUT_FILE"]
    else:
        del launch.environment["PF_AGENT_MODEL"]
    with pytest.raises(SystemExit, match=expected):
        worker.main()
    assert launch.calls == launch.payloads == []
