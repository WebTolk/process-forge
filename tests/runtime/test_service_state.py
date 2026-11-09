"""Bounded control, lossless status, and accepted-snapshot preservation."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
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
    monkeypatch.setattr(service, "active_service", lambda *_: (False, control(path)))
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
    monkeypatch.setattr(service, "active_service", lambda *_: (True, control(path)))
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
    stop = threading.Event()
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
        except BaseException as error:
            failures.append(error)

    reader = threading.Thread(target=read)
    reader.start()
    try:
        for i in range(1, 20):
            store.write(
                path,
                {**state, "generation": i, "updated_at": f"2026-11-09T12:00:{i:02d}Z"},
            )
    finally:
        stop.set()
        reader.join(timeout=10)
    assert not reader.is_alive()
    assert not failures
    assert reads


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
