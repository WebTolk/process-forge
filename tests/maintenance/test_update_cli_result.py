"""CLI result contracts, including a real offline sealed file update."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
QA = Path(
    os.environ.get(
        "PF_UPDATE_CLI_TEST_ROOT",
        str(ROOT.parents[0] / "exit-qa" / "execution_regression"),
    )
).absolute()


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import the complete source CLI, keeping its real handler and imports."""
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    module = importlib.import_module("processforge")
    module_file = module.__file__
    assert isinstance(module_file, str)
    assert Path(module_file).resolve() == ROOT / "tools/processforge.py"
    return module


def arguments(*, workplace: bool = True) -> argparse.Namespace:
    return argparse.Namespace(
        core_root=str(QA / "handler-target"),
        archive=str(QA / "handler-incoming.zip"),
        workplace_root=str(QA / "handler-workplace") if workplace else None,
        confirm=True,
        force_local_modifications=False,
    )


def assert_service_call(service: Mock, args: argparse.Namespace) -> None:
    service.assert_called_once_with(
        Path(args.core_root).resolve(),
        Path(args.archive).resolve(),
        confirm=True,
        force_local_modifications=False,
        workplace_root=Path(args.workplace_root).resolve()
        if args.workplace_root
        else None,
    )


def test_file_only_with_workplace_succeeds_without_doctor(
    cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "status": "applied",
        "maintenance_mode": "file_only",
        "counts": {"added": 1, "changed": 2},
        "private_preserved": True,
    }
    service = Mock(return_value=payload)
    monkeypatch.setattr("processforge_core.maintenance.update.apply_update", service)
    args = arguments()
    assert cli.command_core_update_apply(args) == 0
    assert_service_call(service, args)
    captured = capsys.readouterr()
    assert captured.out == json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("mode", "doctor_status", "expected"),
    [
        (None, "pass", 0),
        (None, "fail", 2),
        ("managed", "fail", 2),
        ("file_only_pending", "fail", 2),
    ],
)
def test_managed_doctor_result_and_exact_mode_selection(
    cli: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str | None,
    doctor_status: str,
    expected: int,
) -> None:
    payload: dict[str, Any] = {
        "status": "applied",
        "post_update_doctor": {"status": doctor_status},
    }
    if mode is not None:
        payload["maintenance_mode"] = mode
    service = Mock(return_value=payload)
    monkeypatch.setattr("processforge_core.maintenance.update.apply_update", service)
    args = arguments()
    assert cli.command_core_update_apply(args) == expected
    assert_service_call(service, args)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == payload
    assert captured.err == ""


def test_without_workplace_preserves_success_without_doctor(
    cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"status": "applied"}
    service = Mock(return_value=payload)
    monkeypatch.setattr("processforge_core.maintenance.update.apply_update", service)
    args = arguments(workplace=False)
    assert cli.command_core_update_apply(args) == 0
    assert_service_call(service, args)
    assert json.loads(capsys.readouterr().out) == payload


@pytest.mark.parametrize("code", ["plan_blocked", "file_operation_failed"])
def test_update_refusal_remains_nonzero_without_retry(
    cli: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    code: str,
) -> None:
    from processforge_core.maintenance.update import CoreUpdateError

    service = Mock(side_effect=CoreUpdateError(code, "controlled service refusal"))
    monkeypatch.setattr("processforge_core.maintenance.update.apply_update", service)
    args = arguments()
    assert cli.command_core_update_apply(args) == 1
    assert_service_call(service, args)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "error": {"code": code, "message": "controlled service refusal"}
    }
    assert captured.err == ""


def test_external_sealed_cli_with_offline_workplace_exits_successfully() -> None:
    """Exercise the launcher, service, file replacement and CLI exit together."""
    spec = importlib.util.spec_from_file_location(
        "update_cli_fixture_support", ROOT / "tests/maintenance/test_file_update.py"
    )
    assert spec is not None and spec.loader is not None
    support = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = support
    spec.loader.exec_module(support)
    native_spec = importlib.util.spec_from_file_location(
        "update_cli_fixture_native", ROOT / "tools/pf_native_control.py"
    )
    assert native_spec is not None and native_spec.loader is not None
    native = importlib.util.module_from_spec(native_spec)
    sys.modules[native_spec.name] = native
    native_spec.loader.exec_module(native)
    case = QA / uuid.uuid4().hex
    manager, target, workplace = (
        case / name for name in ("manager", "target", "workplace")
    )
    for directory in (manager, target, workplace):
        directory.mkdir(parents=True)
    workplace_manifest = b"schema_version: 1\nid: offline-cli-fixture\n"
    (workplace / "workplace.yaml").write_bytes(workplace_manifest)
    payload = {
        path.relative_to(ROOT).as_posix(): native.canonical_release_bytes(
            path.read_bytes()
        )
        for directory in ("src", "tools")
        for path in (ROOT / directory).rglob("*.py")
    }
    payload.update(
        {
            "bin/pf.py": (ROOT / "bin/pf.py").read_bytes(),
            "VERSION": b"1.0.0\n",
            native.INVENTORY: b"",
            **support.OLD,
        }
    )
    build = native.build_publication(
        payload, version="1.0.0", source={"fixture": True}, generated_at="fixture"
    )
    for relative, raw in {**build.payload, native.MANIFEST: build.manifest}.items():
        support.put(manager, relative, raw)
    incoming = native.build_publication(
        {
            native.LEAF: (ROOT / native.LEAF).read_bytes(),
            native.INVENTORY: b"",
            "VERSION": b"2.0.0\n",
            **support.NEW,
        },
        version="2.0.0",
        source={"fixture": True},
        generated_at="fixture",
    )
    archive = case / "incoming.zip"
    archive.write_bytes(support.archive_bytes(incoming))
    for relative, raw in {
        **support.OLD,
        **support.PRIVATE,
        native.MANIFEST: support.old_manifest(support.OLD),
    }.items():
        support.put(target, relative, raw)
    command = [
        sys.executable,
        "-I",
        "-B",
        str(manager / "bin/pf.py"),
        "core-update",
        "apply",
        "--core-root",
        str(target),
        "--archive",
        str(archive),
        "--workplace-root",
        str(workplace),
        "--confirm",
    ]
    result = subprocess.run(
        command,
        cwd=case,
        env={
            key: value for key, value in os.environ.items() if not key.startswith("PF_")
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    (case / "actual-cli.stdout.log").write_text(result.stdout, encoding="utf-8")
    (case / "actual-cli.stderr.log").write_text(result.stderr, encoding="utf-8")
    (case / "actual-cli.command.json").write_text(
        json.dumps({"command": command, "exit_code": result.returncode}, indent=2),
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    outcome = json.loads(result.stdout)
    assert outcome["status"] == "applied" and outcome["maintenance_mode"] == "file_only"
    assert "post_update_doctor" not in outcome
    for relative, raw in {**incoming.payload, **support.PRIVATE}.items():
        assert (target / relative).read_bytes() == raw
    assert (target / native.MANIFEST).read_bytes() == incoming.manifest
    assert not (target / "removed.txt").exists()
    assert not (target / "runtime/core-update/in-progress.json").exists()
    assert not (target / "runtime/native-control").exists()
    assert not (target / "runtime/managed-ingress").exists()
    assert (workplace / "workplace.yaml").read_bytes() == workplace_manifest
    assert not (workplace / "runtime").exists()
