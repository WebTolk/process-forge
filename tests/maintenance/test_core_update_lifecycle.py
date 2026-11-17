"""Check orchestration boundaries between existing stop, update and startup."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def lifecycle(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(ROOT / "src"))
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    module = importlib.import_module("pf_cli.core_update_lifecycle")
    files = importlib.import_module("processforge_core.maintenance.file_update")
    service = importlib.import_module("pf_runtime.service")
    events = []
    args = argparse.Namespace(
        core_root=str(tmp_path / "target"),
        archive=str(tmp_path / "release.zip"),
        workplace_root=str(tmp_path / "workplace"),
        confirm=True,
        force_local_modifications=False,
        runtime_timeout=10.0,
    )
    monkeypatch.setattr(files, "file_update_candidate", lambda _: True)
    monkeypatch.setattr(files, "require_update_target", lambda path: path)

    def plan(*_):
        events.append("plan")
        return {"status": "planned"}

    def stop(options, _):
        assert options.command == "server" and options.force is False
        events.append("stop")
        return 0

    def apply(*_, **kwargs):
        assert kwargs["confirm"] is True
        events.append("apply")
        return {"status": "applied"}

    def start(command, **kwargs):
        events.append("start")
        assert command[2] == str(Path(args.core_root) / "bin/pf.py")
        assert kwargs["cwd"] == Path(args.core_root)
        return SimpleNamespace(
            returncode=0, stdout='{"status":"started","pid":321}', stderr=""
        )

    monkeypatch.setattr(module, "build_plan", plan)
    monkeypatch.setattr(service, "command_stop", stop)
    monkeypatch.setattr(module, "apply_update", apply)
    monkeypatch.setattr(module.subprocess, "run", start)
    monkeypatch.setattr(
        module,
        "DistributionMetadataReader",
        lambda _: SimpleNamespace(
            read=lambda: SimpleNamespace(build_id="manifest:fixture")
        ),
    )
    monkeypatch.setattr(
        service,
        "inspect_lifecycle",
        lambda *_: {
            "kind": "ready",
            "state": {
                "pid": 321,
                "instance_id": "new-runtime",
                "core_identity": {"loaded": {"build_id": "manifest:fixture"}},
            },
        },
    )
    return module, service, args, events


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("confirm", False, "confirm_required"),
        ("workplace_root", None, "workplace_required"),
        ("archive", None, "archive_required"),
        ("runtime_timeout", float("nan"), "invalid_timeout"),
    ],
)
def test_missing_preconditions_never_stop_runtime(lifecycle, field, value, code):
    module, _, args, events = lifecycle
    setattr(args, field, value)
    with pytest.raises(module.CoreUpdateError) as caught:
        module.managed_core_update(args, object())
    assert caught.value.code == code
    assert events == []


def test_blocked_plan_never_stops_runtime(lifecycle, monkeypatch):
    module, _, args, events = lifecycle
    monkeypatch.setattr(module, "build_plan", lambda *_: {"status": "blocked"})
    with pytest.raises(module.CoreUpdateError) as caught:
        module.managed_core_update(args, object())
    assert caught.value.code == "plan_blocked"
    assert events == []


def test_busy_stop_never_updates_files(lifecycle, monkeypatch):
    module, service, args, events = lifecycle

    def busy(*_):
        events.append("stop")
        raise SystemExit("FAIL: runtime_busy_or_activity_unknown")

    monkeypatch.setattr(service, "command_stop", busy)
    with pytest.raises(module.CoreUpdateError) as caught:
        module.managed_core_update(args, object())
    assert caught.value.code == "runtime_stop_failed"
    assert events == ["plan", "stop"]


def test_failed_apply_never_starts_partial_core(lifecycle, monkeypatch):
    module, _, args, events = lifecycle

    def fail(*_, **__):
        events.append("apply")
        raise module.CoreUpdateError("file_operation_failed", "fixture write refusal")

    monkeypatch.setattr(module, "apply_update", fail)
    with pytest.raises(module.CoreUpdateError) as caught:
        module.managed_core_update(args, object())
    assert caught.value.code == "file_operation_failed"
    assert "restart was not attempted" in caught.value.message
    assert events == ["plan", "stop", "apply"]


def test_success_starts_verified_target_after_apply(lifecycle):
    module, _, args, events = lifecycle
    result, code = module.managed_core_update(args, object())
    assert code == 0
    assert result["status"] == "applied"
    assert result["runtime_lifecycle"]["instance_id"] == "new-runtime"
    assert events == ["plan", "stop", "apply", "start"]


def test_wrong_running_core_is_not_accepted(lifecycle, monkeypatch):
    module, service, args, events = lifecycle
    monkeypatch.setattr(
        service,
        "inspect_lifecycle",
        lambda *_: {
            "kind": "ready",
            "state": {
                "pid": 321,
                "core_identity": {"loaded": {"build_id": "manifest:wrong"}},
            },
        },
    )
    result, code = module.managed_core_update(args, object())
    assert code == 2 and result["status"] == "applied"
    assert result["runtime_lifecycle"]["start"] == "identity_unverified"
    assert events == ["plan", "stop", "apply", "start"]


def test_start_failure_preserves_successful_update_result(lifecycle, monkeypatch):
    module, _, args, events = lifecycle
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(
            returncode=1, stdout="", stderr="fixture startup failure"
        ),
    )
    result, code = module.managed_core_update(args, object())
    assert code == 2 and result["status"] == "applied"
    assert result["runtime_lifecycle"]["exit_code"] == 1
    assert events == ["plan", "stop", "apply"]


def test_resume_uses_original_archive_and_recovery_path(lifecycle, monkeypatch):
    module, _, args, events = lifecycle
    manifest = {"fixture": "original"}
    monkeypatch.setattr(module, "read_archive_manifest", lambda _: manifest)

    def validate(archive, selected):
        assert archive == Path(args.archive) and selected is manifest
        events.append("validate_archive")

    def resume(target, archive, **kwargs):
        assert target == Path(args.core_root) and archive == Path(args.archive)
        assert kwargs["confirm"] is True
        events.append("resume")
        return {"status": "applied"}

    monkeypatch.setattr(module, "validate_archive_payload", validate)
    monkeypatch.setattr(module, "resume_file_update", resume)
    result, code = module.managed_core_update(args, object(), resume=True)
    assert code == 0 and result["runtime_lifecycle"]["instance_id"] == "new-runtime"
    assert events == ["validate_archive", "stop", "resume", "start"]
