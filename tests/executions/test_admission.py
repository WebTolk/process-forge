"""Gate order, real permanent registry guards and independent-process contention."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, cast

import pytest

from processforge_core.executions.model import ExecutionError
from processforge_core.runtime.execution_admission import ExecutionAdmission

from .test_repository import isolated_path as isolated_path

if TYPE_CHECKING:
    from pf_runtime.service import RuntimeProcess


LockFactory = Callable[..., AbstractContextManager[object]]
_CLI = Path(__file__).resolve().parents[2] / "tools" / "processforge.py"


def real_registry_lock() -> LockFactory:
    """Load the existing implementation only in tests; Core never imports CLI."""
    name = "w3_admission_cli_fixture"
    spec = importlib.util.spec_from_file_location(name, _CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(_CLI.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(_CLI.parent))
    return cast(LockFactory, module.registry_file_lock)


def test_gate_order_and_remaining_budget(isolated_path: Path) -> None:
    events: list[tuple[str, Path, float]] = []

    @contextmanager
    def lock(
        path: Path, *, timeout_seconds: float, stale_after_seconds: float
    ) -> Iterator[None]:
        assert stale_after_seconds == 0
        events.append(("enter", path, timeout_seconds))
        try:
            yield
        finally:
            events.append(("leave", path, timeout_seconds))

    workplace = isolated_path / "workplace"
    project = isolated_path / "project"
    admission = ExecutionAdmission(lock)
    with admission.start(project, workplace, deadline=time.monotonic() + 0.5):
        assert len(events) == 2
    assert [entry[0] for entry in events] == ["enter", "enter", "leave", "leave"]
    assert events[0][1] == workplace / "runtime/pf-runtime/execution-admission"
    assert events[1][1] == project / ".pf/runtime/execution-admission"
    assert 0 < events[1][2] <= events[0][2] <= 0.5
    events.clear()
    with admission.maintenance(project, None):
        assert events[0][1] == project / ".pf/runtime/execution-admission"


def test_deadline_failure_and_exception_release(isolated_path: Path) -> None:
    events: list[str] = []

    @contextmanager
    def lock(path: Path, **options: float) -> Iterator[None]:
        events.append("acquired")
        try:
            yield
        finally:
            events.append("released")

    admission = ExecutionAdmission(lock)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with admission.start(isolated_path, None, deadline=time.monotonic() - 1):
            pytest.fail("expired admission yielded")
    assert events == []
    with pytest.raises(RuntimeError, match="reservation failed"):
        with admission.start(isolated_path, isolated_path / "workplace"):
            raise RuntimeError("reservation failed")
    assert events == ["acquired", "acquired", "released", "released"]


def test_shutdown_requires_exact_selector_and_refuses_lock_timeout(
    isolated_path: Path,
) -> None:
    @contextmanager
    def unavailable(path: Path, **options: float) -> Iterator[None]:
        raise SystemExit("private registry diagnostics must not escape")
        yield

    admission = ExecutionAdmission(unavailable)
    for instance in ("", "instance"):
        with pytest.raises(ExecutionError, match="^execution_activity_unknown$"):
            with admission.shutdown(
                isolated_path,
                expected_instance_id=instance,
                deadline=time.monotonic() + 0.5,
            ):
                pytest.fail("unknown must not pass")


def test_real_guard_persists_after_success_and_crash(isolated_path: Path) -> None:
    admission = ExecutionAdmission(real_registry_lock())
    project = isolated_path / "project"
    gate = project / ".pf/runtime/.execution-admission.lock.guard"
    with admission.start(project, None):
        assert gate.is_file()
    assert gate.is_file()
    assert not gate.with_name(".execution-admission.lock").exists()
    with pytest.raises(RuntimeError):
        with admission.maintenance(project, None):
            raise RuntimeError("controller failure")
    with admission.start(project, None):
        assert gate.is_file()


def test_independent_start_blocks_shutdown_within_budget(isolated_path: Path) -> None:
    """Hold a real start gate in a child process, race the shutdown gate."""
    script = """import importlib.util,sys
from pathlib import Path
from processforge_core.runtime.execution_admission import ExecutionAdmission
sys.path.insert(0,str(Path(sys.argv[1]).parent))
spec=importlib.util.spec_from_file_location("child_cli",sys.argv[1])
module=importlib.util.module_from_spec(spec)
sys.modules["child_cli"]=module
spec.loader.exec_module(module)
with ExecutionAdmission(module.registry_file_lock).start(Path(sys.argv[2]),Path(sys.argv[3])):
    print("reserved-gate",flush=True)
    sys.stdin.readline()
"""
    project, workplace = isolated_path / "project", isolated_path / "workplace"
    admission = ExecutionAdmission(real_registry_lock())
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(_CLI), str(project), str(workplace)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "reserved-gate"
        started = time.monotonic()
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            with admission.shutdown(
                workplace, expected_instance_id="instance", deadline=started + 0.15
            ):
                pytest.fail("shutdown passed an in-flight start")
        assert time.monotonic() - started < 0.5
        _, error = child.communicate("release\n", timeout=10)
        assert child.returncode == 0, error
        with admission.shutdown(
            workplace, expected_instance_id="instance", deadline=time.monotonic() + 0.5
        ):
            pass
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


def test_native_core_guard_is_compatible_with_cli(isolated_path: Path) -> None:
    """The moved primitive must contend with the unchanged CLI guard inode."""
    from processforge_core.runtime.execution_admission import registry_file_lock

    gate = isolated_path / "registry"
    cli_lock = real_registry_lock()
    with registry_file_lock(gate):
        with pytest.raises(SystemExit, match="registry is locked"):
            with cli_lock(gate, timeout_seconds=0.02):
                pytest.fail("two registry owners")
    with cli_lock(gate):
        with pytest.raises(SystemExit, match="registry is locked"):
            with registry_file_lock(gate, timeout_seconds=0.02):
                pytest.fail("two registry owners")


def test_nested_native_admission_tracks_current_thread(isolated_path: Path) -> None:
    admission = ExecutionAdmission()
    workplace = isolated_path / "workplace"
    project = isolated_path / "project"
    assert not admission.held(project, workplace)
    with admission.workplace(workplace):
        assert not admission.held(project, workplace)
        with admission.project(project):
            assert admission.held(project, workplace)
            with admission.maintenance(project, workplace):
                assert admission.held(project, workplace)
    assert not admission.held(project, workplace)


def test_exited_windows_root_with_retained_handle_is_absent() -> None:
    """GetProcessTimes exit time is authoritative even before handle release."""
    if sys.platform != "win32":
        pytest.skip("Windows native handle regression")
    from processforge_core.runtime.process_identity import (
        capture_process,
        probe_process,
        tree_absence,
    )

    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys; print('ready',flush=True); sys.stdin.readline()",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "ready"
        identity = capture_process(child.pid)
        assert identity is not None
        assert probe_process(identity) == "same"
        _, error = child.communicate("exit\n", timeout=10)
        assert child.returncode == 0, error
        # Popen still retains the original Windows process handle here.
        assert probe_process(identity) == "absent"
        assert tree_absence(identity) is None
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


def native_runtime_fixture(root: Path) -> tuple[RuntimeProcess, ModuleType]:
    """Use real Runtime policy and durable records without starting a service."""
    import importlib
    import os
    import threading
    from types import SimpleNamespace

    sys.path.insert(0, str(_CLI.parent))
    try:
        service = importlib.import_module("pf_runtime.service")
    finally:
        sys.path.remove(str(_CLI.parent))
    runtime = object.__new__(service.RuntimeProcess)
    runtime.workplace_root = root
    runtime.core = SimpleNamespace()
    runtime.instance_id = "native-instance"
    runtime.state = {"status": "ready", "instance_id": runtime.instance_id}
    runtime.state_lock = threading.RLock()
    runtime.active_requests = 0
    runtime.scheduler_active = False
    runtime.shutdown_check = False
    service.write_json_atomic(
        service.lock_path(root),
        {"instance_id": runtime.instance_id, "pid": os.getpid()},
    )
    service.write_json_atomic(
        root / "runtime/pf-runtime-host/state.json",
        {"projects": [], "sessions": {}},
    )
    return runtime, service


def test_runtime_stopping_is_durable_before_start_gate_release(
    isolated_path: Path,
) -> None:
    runtime, service = native_runtime_fixture(isolated_path / "workplace")
    assert (
        runtime.request_shutdown(guarded=True, expected_instance_id=runtime.instance_id)
        is None
    )
    assert (
        service.read_json(service.service_path(runtime.workplace_root))["status"]
        == "stopping"
    )
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with ExecutionAdmission().start(
            isolated_path / "project", runtime.workplace_root
        ):
            pytest.fail("new start bypassed stopping")
    assert not runtime.shutdown_check


def test_runtime_shutdown_refuses_unknown_registration_and_owner_change(
    isolated_path: Path,
) -> None:
    runtime, service = native_runtime_fixture(isolated_path / "workplace")
    assert (
        runtime.request_shutdown(guarded=True, expected_instance_id="other-instance")
        == "owner_changed"
    )
    service.write_json_atomic(
        runtime.workplace_root / "runtime/pf-runtime-host/state.json",
        {"projects": ["invalid"], "sessions": {}},
    )
    assert (
        runtime.request_shutdown(guarded=True, expected_instance_id=runtime.instance_id)
        == "runtime_busy_or_activity_unknown"
    )
    assert runtime.state["status"] == "ready"
    assert not service.service_path(runtime.workplace_root).exists()


@pytest.mark.parametrize("route", ["start", "registration"])
def test_actual_shutdown_contends_with_independent_core_start(
    isolated_path: Path,
    route: str,
) -> None:
    runtime, service = native_runtime_fixture(isolated_path / "workplace")
    script = """import sys
from pathlib import Path
from processforge_core.runtime.execution_admission import ExecutionAdmission
if sys.argv[3] == "registration":
    from pf_runtime.host import registration_admission
    gate = registration_admission(Path(sys.argv[2]),[Path(sys.argv[1])])
else:
    gate = ExecutionAdmission().start(Path(sys.argv[1]),Path(sys.argv[2]))
with gate:
    print("start-held",flush=True)
    sys.stdin.readline()
"""
    project = isolated_path / "project"
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            script,
            str(project),
            str(runtime.workplace_root),
            route,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "start-held"
        started = time.monotonic()
        assert (
            runtime.request_shutdown(
                guarded=True, expected_instance_id=runtime.instance_id
            )
            == "runtime_busy_or_activity_unknown"
        )
        assert time.monotonic() - started < 0.8
        assert not service.service_path(runtime.workplace_root).exists()
        _, error = child.communicate("release\n", timeout=10)
        assert child.returncode == 0, error
        assert (
            runtime.request_shutdown(
                guarded=True, expected_instance_id=runtime.instance_id
            )
            is None
        )
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"status":"stopping","status":"ready"}',
        b'{"status":"ready","invalid":NaN}',
        b'{"status":"unknown"}',
        b"[]",
        b" " * 65537,
    ],
    ids=["duplicate", "nonfinite", "unknown", "nonobject", "oversize"],
)
def test_corrupt_stopping_state_cannot_admit_start(
    isolated_path: Path, raw: bytes
) -> None:
    workplace = isolated_path / "workplace"
    path = workplace / "runtime/pf-runtime/service.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with ExecutionAdmission().start(isolated_path / "project", workplace):
            pytest.fail("invalid stopping state admitted start")
