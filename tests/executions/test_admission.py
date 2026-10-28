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
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import mock_open

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


@pytest.mark.parametrize("enrolled", [False, True])
@pytest.mark.parametrize(
    "error",
    [
        OSError("after admission, before dispatch"),
        PermissionError("session is not authorized for requested project_root"),
        TimeoutError("operation timed out"),
        SystemExit(23),
    ],
    ids=["oserror", "permission", "timeout", "exit"],
)
def test_operation_exception_identity_and_reentrant_release(
    isolated_path: Path, enrolled: bool, error: BaseException
) -> None:
    events: list[tuple[str, Path]] = []
    observed: list[BaseException] = []

    @contextmanager
    def lock(path: Path, **options: float) -> Iterator[None]:
        events.append(("enter", path))
        try:
            yield
        except BaseException as exc:
            observed.append(exc)
            raise
        finally:
            events.append(("leave", path))

    project = isolated_path / "project"
    workplace = isolated_path / "workplace" if enrolled else None
    admission = ExecutionAdmission(lock)
    paths = [project / ".pf/runtime/execution-admission"]
    if workplace is not None:
        paths.insert(0, workplace / "runtime/pf-runtime/execution-admission")
    with pytest.raises(type(error)) as caught:
        with admission.start(project, workplace):
            assert admission.held(project, workplace)
            with admission.maintenance(project, workplace):
                assert admission.held(project, workplace)
                raise error
    assert caught.value is error
    assert len(observed) == len(paths)
    assert all(exc is error for exc in observed)
    assert events == [("enter", path) for path in paths] + [
        ("leave", path) for path in reversed(paths)
    ]
    assert not admission.held(project, workplace)
    events.clear()
    with admission.start(project, workplace):
        assert admission.held(project, workplace)
    assert len(events) == 2 * len(paths)
    assert not admission.held(project, workplace)


@pytest.mark.parametrize("phase", ["factory", "enter", "leave", "stopping"])
@pytest.mark.parametrize(
    "error",
    [
        OSError("registry unavailable"),
        PermissionError("denied"),
        TimeoutError("registry timeout"),
        SystemExit("registry locked"),
    ],
    ids=["oserror", "permission", "timeout", "exit"],
)
def test_admission_owned_failures_remain_normalized(
    isolated_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    error: BaseException,
) -> None:
    events: list[tuple[str, Path]] = []
    project = isolated_path / "project"
    workplace = isolated_path / "workplace"
    project_gate = project / ".pf/runtime/execution-admission"
    workplace_gate = workplace / "runtime/pf-runtime/execution-admission"

    @contextmanager
    def lock(path: Path, **options: float) -> Iterator[None]:
        if phase == "enter" and path == project_gate:
            raise error
        events.append(("enter", path))
        try:
            yield
        finally:
            events.append(("leave", path))
            if phase == "leave" and path == project_gate:
                raise error

    def factory(path: Path, **options: float) -> AbstractContextManager[object]:
        if phase == "factory" and path == project_gate:
            raise error
        return lock(path, **options)

    def stopping(root: Path) -> None:
        raise error

    admission = ExecutionAdmission(factory)
    if phase == "stopping":
        monkeypatch.setattr(admission, "check_stopping", stopping)
    with pytest.raises(ExecutionError, match="^execution_activity_unknown$") as caught:
        with admission.start(project, workplace):
            assert phase == "leave", "refused admission yielded"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert not admission.held(project, workplace)
    expected = [("enter", workplace_gate)]
    if phase in {"leave", "stopping"}:
        expected += [("enter", project_gate), ("leave", project_gate)]
    expected.append(("leave", workplace_gate))
    assert events == expected


@pytest.mark.parametrize("route", ["direct", "start", "registration"])
@pytest.mark.parametrize("phase", ["open", "read"])
@pytest.mark.parametrize("error_type", [OSError, PermissionError])
def test_stopping_state_io_failure_is_normalized_for_every_caller(
    isolated_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    phase: str,
    error_type: type[OSError],
) -> None:
    import traceback

    sys.path.insert(0, str(_CLI.parent))
    try:
        from pf_runtime.host import registration_admission
    finally:
        sys.path.remove(str(_CLI.parent))

    project = isolated_path / "project"
    workplace = isolated_path / "workplace"
    state_path = workplace / "runtime/pf-runtime/service.json"
    error = error_type(13, "private stopping-fence diagnostic", str(state_path))
    state_open = mock_open(read_data=b'{"status":"ready"}')
    if phase == "open":
        state_open.side_effect = error
    else:
        state_open.return_value.read.side_effect = error
    original_open = Path.open

    def open_state(path: Path, *args: Any, **options: Any) -> Any:
        if path == state_path:
            return state_open(*args, **options)
        return original_open(path, *args, **options)

    monkeypatch.setattr(Path, "open", open_state)
    admission = ExecutionAdmission()
    with pytest.raises(ExecutionError, match="^execution_activity_unknown$") as caught:
        if route == "direct":
            admission.check_stopping(workplace)
        else:
            gate = (
                admission.start(project, workplace)
                if route == "start"
                else registration_admission(workplace, [project])
            )
            with gate:
                pytest.fail("unreadable stopping fence admitted an operation")
    state_open.assert_called_once_with("rb")
    if phase == "read":
        state_open.return_value.read.assert_called_once_with(65537)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    rendered = "".join(traceback.format_exception(caught.value))
    assert str(state_path) not in rendered
    assert "private stopping-fence diagnostic" not in rendered
    assert not admission.held(project, workplace)
    monkeypatch.undo()
    with admission.start(project, workplace):
        assert admission.held(project, workplace)
    assert not admission.held(project, workplace)


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


@pytest.fixture
def first_start_project(
    isolated_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModuleType, Path, Path]:
    """Real enrolled metadata without runtime-host initialization or a service."""
    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.configuration import DeviceConfigurationSource

    real_registry_lock()
    core = sys.modules["w3_admission_cli_fixture"]
    project, workplace = isolated_path / "project", isolated_path / "workplace"
    write_yaml_file(project / ".pf/process-forge.yaml", {"project": {"id": "project"}})
    write_yaml_file(workplace / "workplace.yaml", {"schema_version": 1})
    write_yaml_file(
        project / ".pf/process-forge.local.yaml",
        {"workplace": {"manifest": str(workplace / "workplace.yaml")}},
    )
    monkeypatch.setattr(
        DeviceConfigurationSource,
        "default_path",
        staticmethod(lambda: isolated_path / "device.yaml"),
    )
    return core, project, workplace


@pytest.mark.parametrize("storage", ["legacy", "sql"])
@pytest.mark.parametrize("existing", [False, True])
def test_first_start_publishes_route_for_shutdown_and_global_count(
    first_start_project: tuple[ModuleType, Path, Path], storage: str, existing: bool
) -> None:
    import json

    from pf_runtime import host

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.runtime import metrics

    from .test_configuration_access import _sql_project

    core, project, workplace = first_start_project
    runtime, _service = native_runtime_fixture(workplace)
    runtime.core = core
    cache = host.state_path(workplace)
    cache.unlink()  # The runtime policy fixture alone seeds an empty cache.
    other = project.parent / "other"
    if existing:
        write_yaml_file(other / ".pf/process-forge.yaml", {"project": {"id": "other"}})
        host.write_json(
            cache,
            {
                "projects": [host.route_project(str(other), workplace, core)],
                "sessions": {"kept": {"cache_only": True}},
            },
        )
    else:
        assert not cache.exists()
    with core._worker_start_admission(project):
        assert ExecutionAdmission.held(project, workplace)
        roots, _registration, complete = metrics.registered_projects(workplace)
        assert complete and project in roots
        assert (other in roots) is existing
        if storage == "sql":
            _sql_project(project, current_count=1)
        else:
            core._core_common_json_io.json_write(
                project / ".pf/runtime/agent-runs/run/task/status.json",
                {"status": "running"},
            )
    published = cache.read_bytes()
    # Re-entry must keep both routing and unrelated session metadata intact.
    with core._worker_start_admission(project):
        assert cache.read_bytes() == published
    if existing:
        assert json.loads(published)["sessions"] == {"kept": {"cache_only": True}}
    assert metrics.shutdown_workers(workplace, core)["counts"]["running"] == 1
    assert runtime.active_worker_count(runtime.known_project_roots()) == 1
    assert (
        runtime.request_shutdown(guarded=True, expected_instance_id=runtime.instance_id)
        == "runtime_busy_or_activity_unknown"
    )
    # The same published route must keep unknown activity from becoming idle.
    if storage == "sql":
        (project / ".pf/data/pf.sqlite3").unlink()
    else:
        core._core_common_json_io.json_write(
            project / ".pf/runtime/agent-runs/run/task/status.json",
            {"status": "unknown_exit"},
        )
    assert metrics.shutdown_workers(workplace, core)["counts"]["running"] is None
    assert runtime.active_worker_count(runtime.known_project_roots()) is None


@pytest.mark.parametrize(
    "failure",
    ["corrupt", "coverage", "sessions", "collision", "budget", "stopping", "workplace"],
)
def test_first_start_registration_refuses_without_replacing_coverage(
    first_start_project: tuple[ModuleType, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    import json

    from pf_runtime import host

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.runtime import metrics

    core, project, workplace = first_start_project
    cache = host.state_path(workplace)
    state: dict[str, Any] = {"projects": [], "sessions": {}}
    if failure in {"coverage", "collision"}:
        other = project.parent / "other"
        if failure == "collision":
            write_yaml_file(
                other / ".pf/process-forge.yaml", {"project": {"id": "project"}}
            )
        state["projects"] = [{"project_id": "project", "project_root": str(other)}]
    if failure == "sessions":
        state["sessions"] = None
    cache.parent.mkdir(parents=True)
    cache.write_text(
        "{" if failure == "corrupt" else json.dumps(state), encoding="utf-8"
    )
    before = cache.read_bytes()
    if failure == "budget":

        def exhausted(self: metrics.Budget) -> None:
            raise TimeoutError

        monkeypatch.setattr(metrics.Budget, "check", exhausted)
    elif failure == "stopping":
        core._core_common_json_io.json_write(
            workplace / "runtime/pf-runtime/service.json", {"status": "stopping"}
        )
    elif failure == "workplace":
        (workplace / "workplace.yaml").unlink()
    with pytest.raises(ExecutionError, match="^execution_activity_unknown$"):
        with core._worker_start_admission(project):
            pytest.fail("unproven observation coverage admitted start")
    assert cache.read_bytes() == before
    assert not ExecutionAdmission.held(project, workplace)
