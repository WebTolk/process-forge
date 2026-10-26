"""Targeted sealed report and untruncated child evidence regressions."""

from __future__ import annotations

import argparse
import ast
import builtins
import importlib.util
import io
import json
import os
import sys
import time
import types
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from processforge_subprocess import (  # noqa: E402
    CommandResult,
    diagnostic_text,
    retain_command_output,
    run_command,
)


@pytest.fixture
def tmp_path() -> Path:
    # Explicit test-owned root avoids restrictive host temp ACL setup.
    root = Path(os.environ["PF_RELEASE_REPORT_TEST_ROOT"]) / uuid.uuid4().hex
    root.mkdir(parents=True)
    return root


def load_native() -> Any:
    spec = importlib.util.spec_from_file_location(
        "report_native", ROOT / "tools/pf_native_control.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sealed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    native = load_native()
    image = native.NativeImage.__new__(native.NativeImage)
    image.root = tmp_path.resolve()
    image.files = {"tools/source.py": b"captured", "schema.json": b"{}"}
    image._active = False
    # Preserve host import machinery; exercise the actual activate/captured_open.
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(builtins, "open", builtins.open)
    monkeypatch.setattr(io, "open", io.open)
    monkeypatch.setattr(
        importlib.util,
        "spec_from_file_location",
        importlib.util.spec_from_file_location,
    )
    image.activate()
    return native, image


@pytest.mark.parametrize("opener", [builtins, io])
@pytest.mark.parametrize(
    "name", ["latest-report.json", "latest-report.md", "latest-trace.ndjson"]
)
def test_exact_outputs(sealed: Any, opener: Any, name: str) -> None:
    _, image = sealed
    path = image.root / ".pf/runtime/release-test" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with opener.open(path, "w", encoding="utf-8") as stream:
        stream.write("?????")
    assert path.read_text(encoding="utf-8") == "?????"


@pytest.mark.parametrize("opener", [builtins, io])
@pytest.mark.parametrize(
    "name",
    [
        "tools/source.py",
        ".pf/other.json",
        ".pf/runtime/release-test/other.json",
        ".pf/runtime/release-test/commands/no/stdout.log",
        ".pf/runtime/release-test/../other.json",
    ],
)
def test_refuses_unrelated(sealed: Any, opener: Any, name: str) -> None:
    native, image = sealed
    with pytest.raises(native.NativeControlError):
        opener.open(image.root / name, "w")
    assert (image.root / "tools/source.py").exists() is False


def release_namespace() -> dict[str, Any]:
    names = {
        "ReleaseCommandResult",
        "format_command",
        "run_release_command",
        "print_release_command_output",
        "write_release_test_report",
        "positive_timeout_scale",
        "command_release_test",
    }
    tree = ast.parse((ROOT / "tools/processforge.py").read_bytes())
    selected = ast.Module(
        body=[n for n in tree.body if getattr(n, "name", None) in names],
        type_ignores=[],
    )
    namespace: dict[str, Any] = dict(
        dataclass=dataclass,
        Path=Path,
        Any=Any,
        argparse=argparse,
        json=json,
        time=time,
        sys=sys,
        math=__import__("math"),
        _core_common_clock=types.SimpleNamespace(
            now_utc=lambda: "2026-10-26T15:00:00Z"
        ),
        run_subprocess_command=run_command,
        diagnostic_text=diagnostic_text,
        retain_command_output=retain_command_output,
        format_subprocess_command=lambda command: " ".join(command),
        ensure_trailing_newline=lambda text: text.rstrip("\n") + "\n",
        diagnostics=types.SimpleNamespace(emit=lambda *a, **k: None),
        rel=lambda path, root: str(path.relative_to(root)),
    )
    exec(
        compile(
            selected,
            str(ROOT / "tools/processforge.py"),
            "exec",
            flags=__import__("__future__").annotations.compiler_flag,
        ),
        namespace,
    )
    return namespace


@pytest.mark.parametrize("code", [0, 3])
def test_schema_only_no_clean_finalizes(sealed: Any, code: int) -> None:
    _, image = sealed
    ns = release_namespace()
    plan = types.SimpleNamespace(
        label="schema validation",
        command=["schema"],
        timeout=10,
        allow_warn=False,
        layer="public",
        public_gate=True,
    )
    ns["_release_command_plan"] = types.SimpleNamespace(
        release_test_commands=lambda root, **kw: [plan] if not kw["clean_first"] else []
    )
    ns["run_subprocess_command"] = lambda *a, **kw: CommandResult(
        ["schema"], str(image.root), code, "schema output", "", False, 10
    )
    args = argparse.Namespace(
        root=str(image.root), no_clean=True, only=["schema validation"]
    )
    assert ns["command_release_test"](args) == (1 if code else 0)
    report = json.loads(
        (image.root / ".pf/runtime/release-test/latest-report.json").read_text()
    )
    assert report["checks"][0]["exit_code"] == code
    assert report["result"] == ("FAIL" if code else "PASS")


def test_report_write_error_propagates(sealed: Any) -> None:
    native, image = sealed
    ns = release_namespace()
    image.files[".pf/runtime/release-test/latest-report.json"] = b"protected"
    with pytest.raises(native.NativeControlError):
        ns["write_release_test_report"](
            image.root,
            [],
            [],
            public=False,
            started_at="a",
            finished_at="b",
            elapsed_seconds=0,
        )


@pytest.mark.parametrize("timeout", [False, True])
def test_full_child_evidence_before_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], timeout: bool
) -> None:
    ns = release_namespace()
    events = []
    ns["diagnostics"] = types.SimpleNamespace(
        emit=lambda *args, **kw: events.append(args)
    )
    script = (
        "import sys,time; print('EARLY-' + 'x'*6000, flush=True); print('ERR-' + 'y'*6000,file=sys.stderr,flush=True); "
        + ("time.sleep(5)" if timeout else "sys.exit(7)")
    )
    result = ns["run_release_command"](
        "child", [sys.executable, "-B", "-c", script], tmp_path, 1
    )
    metadata_path = next(
        (tmp_path / ".pf/runtime/release-test/commands").glob("*/result.json")
    )
    metadata = json.loads(metadata_path.read_text())
    stdout = metadata_path.with_name("stdout.log").read_text()
    stderr = metadata_path.with_name("stderr.log").read_text()
    assert stdout.count("EARLY-") == 1 and len(stdout) > 6000
    assert stderr.count("ERR-") == 1 and len(stderr) > 6000
    assert metadata["timed_out"] == timeout
    assert metadata["args"] == result.command
    assert metadata["timeout_seconds"] == 1
    assert result.code == (124 if timeout else 7)
    assert events[0][2]["result"].endswith("/result.json")
    capsys.readouterr()
    ns["print_release_command_output"](result)
    assert len(capsys.readouterr().out.splitlines()) <= 35
    if timeout:
        assert "EARLY-" not in result.output.split("STDOUT tail:", 1)[1]


def test_linked_report_refused(sealed: Any) -> None:
    native, image = sealed
    original = image.root / "original"
    # The hardlink target is outside the accepted image, created before opening.
    original.touch()
    path = image.root / ".pf/runtime/release-test/latest-report.json"
    path.parent.mkdir(parents=True)
    os.link(original, path)
    with pytest.raises(native.NativeControlError):
        path.write_text("unsafe")
