"""Bounded control, lossless status, and accepted-snapshot preservation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.client import HTTPMessage
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pf_runtime import monitor, service

from processforge_core.executions.model import ExecutionError
from processforge_core.runtime.execution_admission import ExecutionAdmission
from processforge_core.runtime_service_state import (
    SERVICE_STATE_MAX_BYTES,
    RuntimeServiceStateStore,
    RuntimeServiceStateWriter,
)


def snapshot(root: Path, count: int = 1000) -> dict[str, Any]:
    identifiers = [f"run-{i:04d}-" + "длинный-id-" * 8 for i in range(count)]
    return {
        "schema_version": 2,
        "status": "ready",
        "health": "ready",
        "instance_id": "fixture-instance",
        "pid": os.getpid(),
        "endpoint": "http://127.0.0.1:1",
        "workplace_root": str(root),
        "updated_at": "2026-11-09T12:00:00Z",
        "capabilities": {"guarded_shutdown": 1},
        "metrics": {
            "schema_version": 1,
            "instance_id": "fixture-instance",
            "groups": {},
        },
        "configuration": {
            "status": "valid",
            "metrics_interval_seconds": 5,
            "logging": {"description": "diagnostic configuration " * 5000},
        },
        "scheduler": {
            "jobs": {
                "inspector": {"period_seconds": 30, "last_result": "ok"},
                "temporary_files": {
                    "period_seconds": 300,
                    "projects": {str(i): {"error": "detail " * 20} for i in range(128)},
                },
            }
        },
        "last_scheduler_result": {
            "status": "ok",
            "projects": [
                {"inspector_result": {"runs": identifiers, "observed": identifiers}}
            ],
        },
        "project_errors": {"fixture": "long diagnostic " * 5000},
        "extension": {"nested": {"_runtime_state_details": "ordinary nested data"}},
    }


def control(path: Path) -> dict[str, Any]:
    return json.loads(path.read_bytes())


def active_slot(path: Path) -> Path:
    return path.with_name(
        f"service-details.{control(path)['_runtime_state_details']['slot']}.json"
    )


@pytest.mark.parametrize("count", [250, 1000])
def test_large_actual_service_save_keeps_admission_and_full_status(
    tmp_path: Path, count: int
) -> None:
    state = snapshot(tmp_path, count)
    service.save_service_state(tmp_path, SimpleNamespace(), state)
    path = service.service_path(tmp_path)
    assert path.stat().st_size <= SERVICE_STATE_MAX_BYTES
    assert active_slot(path).stat().st_size > SERVICE_STATE_MAX_BYTES
    assert RuntimeServiceStateStore().read(path) == state
    assert service.restore_service_state(tmp_path, control(path)) == state
    ExecutionAdmission.check_stopping(tmp_path)
    assert control(path)["configuration"] == {
        "status": "valid",
        "metrics_interval_seconds": 5,
    }
    assert "projects" not in control(path)["scheduler"]["jobs"]["temporary_files"]
    assert control(path)["metrics"] == state["metrics"]
    assert "_runtime_state_details" not in state


@pytest.mark.parametrize(
    "status", ["starting", "ready", "running", "stopped", "stale", "stopping", "failed"]
)
def test_lifecycle_fence_does_not_depend_on_diagnostic_volume(
    tmp_path: Path, status: str
) -> None:
    state = snapshot(tmp_path)
    state["status"] = status
    RuntimeServiceStateStore().write(service.service_path(tmp_path), state)
    if status in {"stopping", "failed"}:
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            ExecutionAdmission.check_stopping(tmp_path)
    else:
        ExecutionAdmission.check_stopping(tmp_path)


def test_repeated_publication_reuses_only_two_slots(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    state = snapshot(tmp_path, 250)
    original = copy.deepcopy(state)
    for i in range(12):
        state["sequence"] = i
        store.write(path, state)
        assert store.read(path) == state
    assert {p.name for p in path.parent.iterdir()} == {
        "service.json",
        "service-details.0.json",
        "service-details.1.json",
    }
    state.pop("sequence")
    assert state == original


@pytest.mark.parametrize("failure_point", ["details", "control"])
def test_failed_publication_preserves_accepted_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_point: str
) -> None:
    path = service.service_path(tmp_path)
    writer = RuntimeServiceStateWriter()
    store = RuntimeServiceStateStore(writer)
    before = snapshot(tmp_path, 250)
    store.write(path, before)
    accepted = active_slot(path)
    old_control, old_details = path.read_bytes(), accepted.read_bytes()
    replace = writer._replace

    def fail(staging: Path, destination: Path) -> None:
        if (destination == path) == (failure_point == "control"):
            raise PermissionError("injected publication refusal")
        replace(staging, destination)

    monkeypatch.setattr(writer, "_replace", fail)
    after = {**before, "status": "stopping", "new_result": [1, 2, 3]}
    with pytest.raises(PermissionError, match="injected publication refusal"):
        store.write(path, after)
    assert path.read_bytes() == old_control
    assert accepted.read_bytes() == old_details
    assert store.read(path) == before
    assert not list(path.parent.glob("*.tmp"))


def test_child_exit_before_control_commit_keeps_old_data(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    before = snapshot(tmp_path, 250)
    store.write(path, before)
    old = path.read_bytes()
    code = """
import os,sys
from pathlib import Path
from processforge_core.runtime_service_state import RuntimeServiceStateStore,RuntimeServiceStateWriter
path=Path(sys.argv[1])
writer=RuntimeServiceStateWriter()
replace=writer._replace
def fail(staging,destination):
    if destination==path: os._exit(19)
    replace(staging,destination)
writer._replace=fail
store=RuntimeServiceStateStore(writer)
state=store.read(path)
state['status']='stopping'
store.write(path,state)
"""
    child = subprocess.run(
        [sys.executable, "-B", "-c", code, str(path)], capture_output=True, timeout=30
    )
    assert child.returncode == 19, child.stderr
    assert path.read_bytes() == old
    assert store.read(path) == before
    # An abrupt exit may retain its own staging; there is no global recovery or deletion.
    assert len(list(path.parent.glob(".service.json.*.tmp"))) == 1


def test_oversized_control_refuses_before_any_write(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    before = snapshot(tmp_path, 250)
    store.write(path, before)
    files = {p.name: p.read_bytes() for p in path.parent.iterdir()}
    after = {**before, "endpoint": "x" * SERVICE_STATE_MAX_BYTES}
    with pytest.raises(ValueError, match="runtime_state_control_too_large"):
        store.write(path, after)
    assert {p.name: p.read_bytes() for p in path.parent.iterdir()} == files


def test_legacy_large_snapshot_roundtrip_and_owner_conversion(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    state = snapshot(tmp_path)
    RuntimeServiceStateWriter().write(path, state)
    assert path.stat().st_size > SERVICE_STATE_MAX_BYTES
    store = RuntimeServiceStateStore()
    assert store.read(path) == state
    store.write(path, state)
    assert path.stat().st_size <= SERVICE_STATE_MAX_BYTES
    assert store.read(path) == state


@pytest.mark.parametrize("kind", ["unknown_file", "directory"])
def test_unknown_slot_is_preserved(tmp_path: Path, kind: str) -> None:
    path = service.service_path(tmp_path)
    path.parent.mkdir(parents=True)
    other = path.with_name("service-details.0.json")
    if kind == "directory":
        other.mkdir()
        (other / "foreign").write_bytes(b"not owned")
    else:
        other.write_bytes(b'{"foreign":true}')
    with pytest.raises(ValueError):
        RuntimeServiceStateStore().write(path, snapshot(tmp_path))
    assert not path.exists()
    assert (
        (other / "foreign").read_bytes() == b"not owned"
        if kind == "directory"
        else other.read_bytes() == b'{"foreign":true}'
    )


@pytest.mark.parametrize(
    "corruption", ["hash", "size", "missing", "owner", "duplicate"]
)
def test_bad_diagnostics_never_splice_into_control(
    tmp_path: Path, corruption: str
) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    store.write(path, snapshot(tmp_path, 250))
    selected = active_slot(path)
    header = control(path)
    raw = selected.read_bytes()
    if corruption == "hash":
        selected.write_bytes(raw[:-1] + b" ")
    elif corruption == "size":
        selected.write_bytes(raw + b" ")
    elif corruption == "missing":
        selected.unlink()
    else:
        envelope = json.loads(raw)
        if corruption == "owner":
            envelope["instance_id"] = "another-owner"
            raw = json.dumps(envelope).encode()
        else:
            raw = raw.replace(b'"kind":', b'"kind":"duplicate","kind":', 1)
        selected.write_bytes(raw)
        header["_runtime_state_details"].update(
            size=len(raw), sha256=hashlib.sha256(raw).hexdigest()
        )
        RuntimeServiceStateWriter().write(path, header)
    with pytest.raises((OSError, ValueError)):
        store.read(path)
    reported = service.restore_service_state(tmp_path, control(path))
    assert reported["status"] == "ready"
    assert reported["state_details_error"] == "runtime_state_details_unavailable"
    assert "last_scheduler_result" not in reported
    assert "_runtime_state_details" not in reported
    ExecutionAdmission.check_stopping(tmp_path)


@pytest.mark.parametrize(
    "reference",
    [
        None,
        {},
        {"slot": "../foreign"},
        {"schema_version": True, "slot": 0, "size": 1, "sha256": "0" * 64},
    ],
)
def test_invalid_reference_is_not_a_path_or_legacy_downgrade(
    tmp_path: Path, reference: Any
) -> None:
    path = service.service_path(tmp_path)
    RuntimeServiceStateWriter().write(
        path, {"status": "ready", "_runtime_state_details": reference}
    )
    with pytest.raises(ValueError, match="reference_invalid"):
        RuntimeServiceStateStore().read(path)


def test_public_offline_status_keeps_all_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = snapshot(tmp_path)
    state["status"] = "stopped"
    state["health"] = "stopped"
    path = service.service_path(tmp_path)
    RuntimeServiceStateStore().write(path, state)
    monkeypatch.setattr(
        service,
        "inspect_lifecycle",
        lambda *_: {
            "kind": "stopped",
            "state": control(path),
            "matching": False,
            "pid_running": False,
        },
    )
    monkeypatch.setattr(
        service, "add_runtime_truth", lambda payload, _core, **_: payload
    )
    assert service.status_payload(tmp_path, SimpleNamespace()) == state


def test_public_status_ipc_failure_preserves_saved_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = snapshot(tmp_path)
    path = service.service_path(tmp_path)
    RuntimeServiceStateStore().write(path, state)
    monkeypatch.setattr(
        service,
        "inspect_lifecycle",
        lambda *_: {
            "kind": "ready",
            "state": control(path),
            "matching": True,
            "pid_running": True,
        },
    )
    monkeypatch.setattr(service, "load_token", lambda *_: "fixture-token")
    monkeypatch.setattr(
        service,
        "http_json",
        lambda *_args, **_kwargs: (503, {"error": "fixture-unavailable"}),
    )
    monkeypatch.setattr(
        service, "add_runtime_truth", lambda payload, _core, **_: payload
    )
    expected = {
        **state,
        "health": "degraded",
        "last_status_error": {"error": "fixture-unavailable"},
    }
    assert service.status_payload(tmp_path, SimpleNamespace()) == expected


def _status_files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("mode", ["constructors", "loaders"])
def test_cold_runtime_token_callers_preserve_one_credential(
    tmp_path: Path, mode: str
) -> None:
    code = """
import json,os,sys
from pathlib import Path
from http.client import HTTPMessage
from types import SimpleNamespace
from pf_runtime import service
root,role,mode=Path(sys.argv[1]),sys.argv[2],sys.argv[3]
service.secrets.token_urlsafe=lambda _: "fixture-"+role
original=service.read_json
paused=False
if role != "owner":
    def read(path):
        global paused
        payload=original(path)
        if path == service.token_path(root) and not paused:
            assert not payload
            paused=True
            (root/(role+".waiting")).write_text("ready",encoding="utf-8")
            assert sys.stdin.readline().strip() == "go"
        return payload
    service.read_json=read
if mode == "loaders":
    print(json.dumps({"token":service.load_token(root)}),flush=True)
else:
    runtime=service.RuntimeProcess(root,SimpleNamespace(),interval=1)
    assert runtime.httpd is None and runtime.scheduler_thread is None
    if role == "owner":
        service.acquire_singleton(root,runtime.core,runtime.instance_id)
        try:
            runtime.state["token_hash"]=service.token_hash(runtime.token)
            runtime.save()
            (root/"owner.waiting").write_text(json.dumps({"instance_id":runtime.instance_id,"pid":os.getpid()}),encoding="utf-8")
            assert sys.stdin.readline().strip() == "go"
            disk=original(service.token_path(root))["token"]
            handler=object.__new__(runtime.make_handler())
            handler.path="/status"
            handler.headers=HTTPMessage()
            handler.headers["Authorization"]="Bearer "+disk
            handler.send_json=lambda *_: None
            print(json.dumps({"token":runtime.token,"disk":disk,"authorized":handler.authorize()}),flush=True)
        finally:
            service.release_singleton(root,runtime.instance_id,runtime.core)
    else:
        try:
            service.acquire_singleton(root,runtime.core,runtime.instance_id)
        except SystemExit as exc:
            assert "already owns workplace" in str(exc)
            print(json.dumps({"token":runtime.token,"refused":True}),flush=True)
        else:
            service.release_singleton(root,runtime.instance_id,runtime.core)
            raise AssertionError("contender acquired live workplace")
"""
    children: list[subprocess.Popen[str]] = []

    def start(role: str) -> subprocess.Popen[str]:
        child = subprocess.Popen(
            [sys.executable, "-B", "-c", code, str(tmp_path), role, mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        children.append(child)
        deadline = time.monotonic() + 30
        marker = tmp_path / (role + ".waiting")
        while not marker.exists():
            assert child.poll() is None, child.communicate(timeout=5)
            assert time.monotonic() < deadline, "child did not reach cold-read barrier"
            time.sleep(0.01)
        return child

    def release(child: subprocess.Popen[str]) -> None:
        assert child.stdin is not None
        child.stdin.write("go\n")
        child.stdin.flush()

    def finish(child: subprocess.Popen[str]) -> dict[str, Any]:
        stdout, stderr = child.communicate(timeout=30)
        assert child.returncode == 0, (stdout, stderr)
        assert not stderr, stderr
        return json.loads(stdout)

    try:
        delayed = start("delayed")
        other = start("owner" if mode == "constructors" else "other")
        if mode == "constructors":
            before = _status_files(service.runtime_root(tmp_path))
            release(delayed)
            result = finish(delayed)
            assert result["refused"]
            assert other.poll() is None
            after = _status_files(service.runtime_root(tmp_path))
            assert {k: v for k, v in after.items() if k != "token.json"} == {
                k: v for k, v in before.items() if k != "token.json"
            }
            identity = control(tmp_path / "owner.waiting")
            status = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).resolve().parents[2] / "tools/processforge.py"),
                    "runtime",
                    "status",
                    "--workplace",
                    str(tmp_path),
                    "--json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            assert status.returncode == 0, status.stderr
            payload = json.loads(status.stdout)
            assert payload["status"] == "starting"
            assert payload["instance_id"] == identity["instance_id"]
            assert payload["pid"] == identity["pid"]
            assert _status_files(service.runtime_root(tmp_path)) == after
            release(other)
            owner = finish(other)
            assert owner["token"] == result["token"] == owner["disk"]
            assert owner["authorized"] is True
        else:
            release(delayed)
            release(other)
            left, right = finish(delayed), finish(other)
            assert (
                left["token"]
                == right["token"]
                == control(service.token_path(tmp_path))["token"]
            )
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.communicate(timeout=10)


def test_existing_runtime_token_avoids_guard_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = service.token_path(tmp_path)
    service.write_json_atomic(path, {"schema_version": 1, "token": "fixture-existing"})
    before = _status_files(tmp_path)

    def unexpected(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("existing credential must use read-only fast path")

    monkeypatch.setattr(service, "singleton_critical_section", unexpected)
    monkeypatch.setattr(service, "write_json_atomic", unexpected)
    monkeypatch.setattr(service.secrets, "token_urlsafe", unexpected)
    assert service.load_token(tmp_path) == "fixture-existing"
    assert _status_files(tmp_path) == before


def test_runtime_token_publication_failure_releases_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError("fixture token publication refusal")

    with monkeypatch.context() as patch:
        patch.setattr(service, "write_json_atomic", refuse)
        with pytest.raises(PermissionError, match="fixture token publication refusal"):
            service.load_token(tmp_path)
    assert not service.token_path(tmp_path).exists()
    # A separate interpreter must acquire the actual OS mutex after the failure.
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "from pathlib import Path; from pf_runtime import service; "
            "from types import SimpleNamespace; import sys; "
            "runtime=service.RuntimeProcess(Path(sys.argv[1]),SimpleNamespace(),interval=1); "
            "assert runtime.token and runtime.httpd is None",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (
        service.load_token(tmp_path) == control(service.token_path(tmp_path))["token"]
    )


def test_runtime_token_guard_refusal_does_not_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    @contextmanager
    def refuse(*_args: Any):
        raise PermissionError("fixture token guard refusal")
        yield

    def unexpected(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("guard refusal must precede credential generation")

    monkeypatch.setattr(service, "singleton_critical_section", refuse)
    monkeypatch.setattr(service.secrets, "token_urlsafe", unexpected)
    with pytest.raises(PermissionError, match="fixture token guard refusal"):
        service.load_token(tmp_path)
    assert not list(tmp_path.iterdir())


def _status_command_result(
    root: Path, entry: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, Any]]:
    if entry == "api":
        core = SimpleNamespace(resolve_workplace_root=lambda _: root)
        code = service.command_status(
            argparse.Namespace(workplace="fixture", json=True), core
        )
        return code, json.loads(capsys.readouterr().out)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve().parents[2] / "tools/processforge.py"),
            "runtime",
            "status",
            "--workplace",
            str(root),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert not result.stderr, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize("entry", ["api", "cli"])
@pytest.mark.parametrize("bad_details", [False, True])
@pytest.mark.parametrize(
    "stored_status", ["starting", "stopping", "failed", "ready", "running"]
)
def test_public_status_preserves_matching_live_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stored_status: str,
    bad_details: bool,
    entry: str,
) -> None:
    state = snapshot(tmp_path, 250)
    state.update(status=stored_status, health=stored_status, endpoint="")
    path = service.service_path(tmp_path)
    RuntimeServiceStateStore().write(path, state)
    service.write_json_atomic(
        service.lock_path(tmp_path),
        {"pid": os.getpid(), "instance_id": state["instance_id"]},
    )
    if bad_details:
        active_slot(path).write_bytes(b"unavailable diagnostic body")
    expected = "failed" if stored_status in {"ready", "running"} else stored_status
    observed = service.inspect_lifecycle(tmp_path, SimpleNamespace())
    assert observed["kind"] == expected
    assert observed["matching"] and observed["pid_running"]
    inspection = service.inspect_lifecycle
    calls = 0

    def counted(root: Path, core: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return inspection(root, core)

    monkeypatch.setattr(service, "inspect_lifecycle", counted)
    before = _status_files(tmp_path)
    code, payload = _status_command_result(tmp_path, entry, capsys)
    assert calls == (1 if entry == "api" else 0)
    assert payload["status"] == expected
    health = "degraded" if bad_details else expected
    assert payload["health"] == health
    assert payload["runtime"] == {"status": expected, "health": health, "running": True}
    assert code == (1 if expected == "failed" else 0)
    assert payload["pid"] == os.getpid()
    assert payload["instance_id"] == state["instance_id"]
    assert payload["last_runtime_instance"]["status"] == "current"
    if bad_details:
        assert payload["state_details_error"] == "runtime_state_details_unavailable"
        assert "project_errors" not in payload
        assert "last_scheduler_result" not in payload
    else:
        assert payload["project_errors"] == state["project_errors"]
        assert payload["last_scheduler_result"] == state["last_scheduler_result"]
    assert _status_files(tmp_path) == before
    assert not service.token_path(tmp_path).exists()


@pytest.mark.parametrize("entry", ["api", "cli"])
@pytest.mark.parametrize(
    "fixture",
    ["stopped", "stale", "empty", "missing-lock", "mismatched-lock", "unknown-lock"],
)
def test_public_status_keeps_offline_and_unqualified_owner_conservative(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fixture: str,
    entry: str,
) -> None:
    state: dict[str, Any] = {}
    if fixture not in {"empty", "unknown-lock"}:
        state = snapshot(tmp_path, 250)
        state["endpoint"] = ""
        if fixture != "missing-lock":
            state["pid"] = int(
                subprocess.check_output(
                    [sys.executable, "-B", "-c", "import os;print(os.getpid())"],
                    timeout=10,
                )
            )
        state["status"] = "stopped" if fixture == "stopped" else "failed"
        state["health"] = state["status"]
        RuntimeServiceStateStore().write(service.service_path(tmp_path), state)
    if fixture in {"stale", "mismatched-lock"}:
        lock = {
            "pid": os.getpid() if fixture == "mismatched-lock" else state["pid"],
            "instance_id": "other-instance"
            if fixture == "mismatched-lock"
            else state["instance_id"],
        }
        service.write_json_atomic(service.lock_path(tmp_path), lock)
    elif fixture == "unknown-lock":
        service.write_json_atomic(service.lock_path(tmp_path), {"unknown_owner": True})
    expected = {
        "stopped": "stopped",
        "stale": "stale",
        "empty": "not_running",
        "missing-lock": "orphaned",
        "mismatched-lock": "orphaned",
        "unknown-lock": "orphaned",
    }[fixture]
    assert service.inspect_lifecycle(tmp_path, SimpleNamespace())["kind"] == expected
    before = _status_files(tmp_path)
    code, payload = _status_command_result(tmp_path, entry, capsys)
    assert payload["status"] == expected
    health = "stopped" if expected == "not_running" else expected
    assert payload["runtime"] == {
        "status": expected,
        "health": health,
        "running": False,
    }
    assert code == 0  # Existing failed-only exit policy; orphaned grants no authority.
    if state:
        assert payload["pid"] == state["pid"]
        assert payload["instance_id"] == state["instance_id"]
        assert payload["project_errors"] == state["project_errors"]
        assert payload["last_runtime_instance"]["status"] == "historical"
    assert _status_files(tmp_path) == before
    assert not service.token_path(tmp_path).exists()


def test_stale_cleanup_uses_same_store_and_preserves_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import nullcontext

    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    state = snapshot(tmp_path)
    store.write(path, state)
    monkeypatch.setattr(service, "singleton_critical_section", lambda *_: nullcontext())
    monkeypatch.setattr(
        service,
        "inspect_lifecycle",
        lambda *_: {"kind": "stale", "state": control(path)},
    )
    service.cleanup_stale_runtime(tmp_path, SimpleNamespace())
    restored = store.read(path)
    assert restored["status"] == "stale"
    assert restored["health"] == "stale"
    assert restored["last_scheduler_result"] == state["last_scheduler_result"]
    assert restored["project_errors"] == state["project_errors"]
    assert path.stat().st_size <= SERVICE_STATE_MAX_BYTES


def _runtime_post(
    runtime: service.RuntimeProcess, path: str, payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    handler: Any = object.__new__(runtime.make_handler())
    body = json.dumps(payload).encode("utf-8")
    handler.path = path
    handler.headers = HTTPMessage()
    handler.headers["Authorization"] = "Bearer " + runtime.token
    handler.headers["Content-Length"] = str(len(body))
    handler.rfile = io.BytesIO(body)
    replies: list[tuple[int, dict[str, Any]]] = []
    handler.send_json = lambda status, response: replies.append((status, response))
    handler.do_POST()
    assert len(replies) == 1
    return replies[0]


def _runtime_after_shutdown_publication_failure(
    root: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> service.RuntimeProcess:
    runtime = object.__new__(service.RuntimeProcess)
    runtime.workplace_root = root
    runtime.core = SimpleNamespace()
    runtime.state = snapshot(root, 250)
    runtime.instance_id = runtime.state["instance_id"]
    runtime.token = "fixture-token"
    runtime.state_lock = threading.RLock()
    runtime.active_requests = 0
    runtime.scheduler_active = False
    runtime.shutdown_check = False
    runtime.stop_event = threading.Event()
    runtime.httpd = None
    service.write_json_atomic(
        service.lock_path(root),
        {"pid": os.getpid(), "instance_id": runtime.instance_id},
    )
    service.write_json_atomic(
        root / "runtime/pf-runtime-host/state.json", {"projects": [], "sessions": {}}
    )
    runtime.save()
    path = service.service_path(root)
    before = copy.deepcopy(runtime.state)
    accepted_control = path.read_bytes()
    accepted_slot = active_slot(path)
    accepted_details = accepted_slot.read_bytes()
    replace = RuntimeServiceStateWriter._replace
    faults: list[str] = []
    failure = OSError("injected shutdown publication failure")

    def fail(staging: Path, destination: Path) -> None:
        if (phase == "details" and destination.name.startswith("service-details.")) or (
            phase == "control-before" and destination == path
        ):
            faults.append(destination.name)
            raise failure
        replace(staging, destination)
        if phase == "control-after" and destination == path:
            faults.append(destination.name)
            raise failure

    with monkeypatch.context() as fault:
        fault.setattr(RuntimeServiceStateWriter, "_replace", staticmethod(fail))
        assert _runtime_post(
            runtime,
            "/shutdown",
            {"require_idle": True, "expected_instance_id": runtime.instance_id},
        ) == (409, {"error": "runtime_busy_or_activity_unknown"})
    assert len(faults) == 1
    assert runtime.state["status"] == "stopping"
    assert not runtime.stop_event.is_set()
    assert not runtime.shutdown_check
    assert runtime.active_requests == 0
    assert accepted_slot.read_bytes() == accepted_details
    observed = RuntimeServiceStateStore().read(path)
    if phase == "control-after":
        assert observed == runtime.state
        assert observed["status"] == "stopping"
    else:
        assert path.read_bytes() == accepted_control
        assert observed == before
    return runtime


@pytest.mark.parametrize("phase", ["details", "control-before", "control-after"])
def test_failed_shutdown_publication_can_retry_through_http_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    runtime = _runtime_after_shutdown_publication_failure(tmp_path, monkeypatch, phase)
    accepted = _status_files(tmp_path)
    assert _runtime_post(runtime, "/event", {}) == (503, {"error": "runtime_stopping"})
    assert _status_files(tmp_path) == accepted
    assert runtime.active_requests == 0
    assert not runtime.stop_event.is_set()
    assert _runtime_post(
        runtime,
        "/shutdown",
        {"require_idle": True, "expected_instance_id": runtime.instance_id},
    ) == (200, {"status": "stopping"})
    assert runtime.stop_event.is_set()
    assert not runtime.shutdown_check
    assert runtime.active_requests == 0
    assert (
        RuntimeServiceStateStore().read(service.service_path(tmp_path)) == runtime.state
    )


@pytest.mark.parametrize("phase", ["details", "control-before", "control-after"])
@pytest.mark.parametrize(
    "refusal",
    [
        "active_requests",
        "scheduler_active",
        "shutdown_check",
        "wrong-instance",
        "changed-lock",
    ],
)
def test_shutdown_retry_revalidates_owner_and_busy_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, refusal: str
) -> None:
    runtime = _runtime_after_shutdown_publication_failure(tmp_path, monkeypatch, phase)
    payload = {"require_idle": True, "expected_instance_id": runtime.instance_id}
    if refusal == "wrong-instance":
        payload["expected_instance_id"] = "another-instance"
    elif refusal == "changed-lock":
        service.write_json_atomic(
            service.lock_path(tmp_path),
            {"pid": os.getpid(), "instance_id": "another-instance"},
        )
    else:
        setattr(runtime, refusal, 1 if refusal == "active_requests" else True)
    before = _status_files(tmp_path)
    flags = (runtime.active_requests, runtime.scheduler_active, runtime.shutdown_check)
    error = (
        "owner_changed"
        if refusal in {"wrong-instance", "changed-lock"}
        else "runtime_busy_or_activity_unknown"
    )
    assert _runtime_post(runtime, "/shutdown", payload) == (409, {"error": error})
    assert not runtime.stop_event.is_set()
    assert _status_files(tmp_path) == before
    assert (
        runtime.active_requests,
        runtime.scheduler_active,
        runtime.shutdown_check,
    ) == flags


@pytest.mark.parametrize("phase", ["details", "control-before", "control-after"])
@pytest.mark.parametrize("malformed", ["json", "length", "short", "permission"])
@pytest.mark.parametrize("denied", [False, True])
def test_malformed_shutdown_retry_fences_error_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    malformed: str,
    denied: bool,
) -> None:
    import pf_native_control as native

    runtime = _runtime_after_shutdown_publication_failure(tmp_path, monkeypatch, phase)
    assert service.operation_lease is native.operation_lease
    attempts: list[float | None] = []

    class Admission:
        def __enter__(self) -> None:
            if denied:
                raise native.NativeControlError()

        def __exit__(self, *_exception: Any) -> None:
            pass

    class Control:
        def operation(self, *, deadline: float | None = None) -> Admission:
            attempts.append(deadline)
            return Admission()

    class UnavailableBody(io.BytesIO):
        def read(self, *_args: Any, **_kwargs: Any) -> bytes:
            raise PermissionError("fixture body read denied")

    handler: Any = object.__new__(runtime.make_handler())
    handler.path = "/shutdown"
    body = b"{" if malformed == "json" else b"{}"
    handler.rfile = (
        UnavailableBody(body) if malformed == "permission" else io.BytesIO(body)
    )
    handler.headers = HTTPMessage()
    handler.headers["Authorization"] = "Bearer " + runtime.token
    handler.headers["Content-Length"] = (
        "invalid" if malformed == "length" else str(len(body) + (malformed == "short"))
    )
    replies: list[tuple[int, dict[str, Any]]] = []
    handler.send_json = lambda status, payload: replies.append((status, payload))
    before = _status_files(tmp_path)
    paths = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    control_port: Any = Control()
    with monkeypatch.context() as admission:
        admission.setattr(
            native, "_ENTRY", native.NativeEntry(tmp_path, None, None, control_port)
        )
        handler.do_POST()
    assert len(replies) == 1
    assert runtime.active_requests == 0
    assert not runtime.shutdown_check
    assert (
        runtime.stop_event.is_set() is denied
    )  # Existing in-memory retired-entry stop.
    if denied:
        assert replies == [(409, {"error": "runtime_busy_or_activity_unknown"})]
        assert attempts == [None]
        assert _status_files(tmp_path) == before
        assert (
            sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
            == paths
        )
    else:
        assert replies[0][0] == (403 if malformed == "permission" else 400)
        log = service.operator_log_path(tmp_path)
        entries = [
            json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
        ]
        assert len(entries) == 1
        assert entries[0]["event"] == (
            "request.forbidden" if malformed == "permission" else "request.error"
        )
        after = _status_files(tmp_path)
        del after[log.relative_to(tmp_path).as_posix()]
        assert after == before


def test_actual_guarded_shutdown_publishes_compact_stopping(tmp_path: Path) -> None:
    runtime = object.__new__(service.RuntimeProcess)
    runtime.workplace_root = tmp_path
    runtime.core = SimpleNamespace()
    runtime.instance_id = "fixture-instance"
    runtime.state = snapshot(tmp_path)
    runtime.state_lock = threading.RLock()
    runtime.active_requests = 0
    runtime.scheduler_active = False
    runtime.shutdown_check = False
    service.write_json_atomic(
        service.lock_path(tmp_path),
        {"pid": os.getpid(), "instance_id": runtime.instance_id},
    )
    service.write_json_atomic(
        tmp_path / "runtime/pf-runtime-host/state.json",
        {"projects": [], "sessions": {}},
    )
    assert (
        runtime.request_shutdown(guarded=True, expected_instance_id=runtime.instance_id)
        is None
    )
    path = service.service_path(tmp_path)
    assert path.stat().st_size <= SERVICE_STATE_MAX_BYTES
    assert RuntimeServiceStateStore().read(path) == runtime.state
    assert control(path)["status"] == "stopping"
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        ExecutionAdmission.check_stopping(tmp_path)


def test_rotated_slot_retries_same_owner_but_never_changes_owner(
    tmp_path: Path,
) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    first = snapshot(tmp_path, 250)
    store.write(path, first)
    saved = control(path)
    for i in range(2):
        current = {**first, "generation": i}
        store.write(path, current)
    assert store.read(path, saved) == current
    other = {**first, "instance_id": "next-owner", "generation": "foreign"}
    store.write(path, other)
    store.write(path, other)
    with pytest.raises(ValueError):
        store.read(path, saved)


def test_concurrent_status_reads_do_not_mix_generations(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    state = snapshot(tmp_path, 250)
    state["generation"] = 0
    store.write(path, state)
    accepted = state
    published = {0}
    stop = threading.Event()
    observed_new = threading.Event()
    failures: list[BaseException] = []
    reads: list[int] = []

    def read() -> None:
        try:
            while not stop.is_set():
                try:
                    observed = store.read(path)
                except (OSError, ValueError):
                    continue  # Exhausted retries report unavailable, never mixed data.
                number = observed["generation"]
                assert observed["updated_at"] == f"2026-11-09T12:00:{number:02d}Z"
                reads.append(number)
                if number:
                    observed_new.set()
        except BaseException as error:
            failures.append(error)

    reader = threading.Thread(target=read)
    reader.start()
    try:
        for i in range(1, 20):
            candidate = {
                **state,
                "generation": i,
                "updated_at": f"2026-11-09T12:00:{i:02d}Z",
            }
            before_control = path.read_bytes()
            try:
                store.write(path, candidate)
            except OSError as error:
                if sys.platform != "win32" or getattr(error, "winerror", None) not in {
                    5,
                    32,
                    33,
                }:
                    raise
                # Bounded sharing refusal must preserve the accepted generation.
                assert path.read_bytes() == before_control
                assert store.read(path) == accepted
            else:
                accepted = candidate
                published.add(i)
        observed_new.wait(timeout=5)
    finally:
        stop.set()
        reader.join(timeout=10)
    assert not reader.is_alive()
    assert not failures
    assert len(published) > 1
    assert observed_new.is_set()
    assert reads and set(reads).issubset(published)
    assert store.read(path) == accepted


def test_native_open_control_handle_preserves_snapshot_and_releases(
    tmp_path: Path,
) -> None:
    path = service.service_path(tmp_path)
    store = RuntimeServiceStateStore()
    initial = {**snapshot(tmp_path, 10), "generation": 0}
    updated = {
        **initial,
        "generation": 1,
        "updated_at": "2026-11-09T12:00:01Z",
    }
    store.write(path, initial)
    before = path.read_bytes()
    with path.open("rb") as reader:
        if sys.platform == "win32":
            with pytest.raises(OSError) as caught:
                store.write(path, updated)
            assert getattr(caught.value, "winerror", None) in {5, 32, 33}
            assert path.read_bytes() == before
            assert store.read(path) == initial
        else:
            store.write(path, updated)
            assert store.read(path) == updated
        # A real open descriptor keeps its original complete snapshot.
        assert reader.read() == before
    store.write(path, updated)
    assert store.read(path) == updated


def test_monitor_uses_compact_control_without_diagnostics(tmp_path: Path) -> None:
    import processforge as core

    now = datetime.now(timezone.utc)
    state = snapshot(tmp_path)
    metrics = service.metrics_core()
    state.update(
        schema_version=1,
        updated_at=now.isoformat(),
        started_at=(now - timedelta(seconds=100)).isoformat(),
        metrics=metrics.collect(
            tmp_path,
            [],
            core,
            state["instance_id"],
            metrics.registrations({}),
            now=now.timestamp(),
            interval_seconds=5,
        ),
    )
    path = service.service_path(tmp_path)
    service.write_json_atomic(
        service.lock_path(tmp_path),
        {"pid": state["pid"], "instance_id": state["instance_id"]},
    )
    service.write_json_atomic(
        tmp_path / "runtime/pf-runtime-host/state.json",
        {"projects": [], "sessions": {}, "updated_at": now.isoformat()},
    )
    # The same public monitor projection must survive a large diagnostic body.
    RuntimeServiceStateWriter().write(path, state)
    legacy = monitor.collect_snapshot(
        tmp_path,
        "1.3.0",
        now=now,
        alive=lambda _: True,
        probe=lambda _: (True, "ready"),
    )
    assert legacy["runtime"]["lifecycle"] == "ready"
    RuntimeServiceStateStore().write(path, state)
    collected = monitor.collect_snapshot(
        tmp_path,
        "1.3.0",
        now=now,
        alive=lambda _: True,
        probe=lambda _: (True, "ready"),
    )
    assert collected["runtime"]["lifecycle"] == "ready"
    assert collected["runtime"]["uptime_seconds"] == 100
    assert collected["metrics"]["age_seconds"] == 0
    assert collected["configuration"]["interval_seconds"] == 5
    assert collected == legacy
    active_slot(path).write_bytes(b"unavailable diagnostic body")
    assert collected == monitor.collect_snapshot(
        tmp_path,
        "1.3.0",
        now=now,
        alive=lambda _: True,
        probe=lambda _: (True, "ready"),
    )


def test_actual_redirected_slot_is_preserved(tmp_path: Path) -> None:
    path = service.service_path(tmp_path)
    path.parent.mkdir(parents=True)
    destination = path.with_name("service-details.0.json")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "owned-by-another").write_bytes(b"preserve")
    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(destination), str(foreign)],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert destination.lstat().st_file_attributes & 0x400
    else:
        destination.symlink_to(foreign, target_is_directory=True)
        assert destination.is_symlink()
    with pytest.raises(ValueError, match="runtime_state_unsafe_file"):
        RuntimeServiceStateStore().write(path, snapshot(tmp_path))
    assert not path.exists()
    assert (foreign / "owned-by-another").read_bytes() == b"preserve"
