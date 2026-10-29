"""Real no-model Windows process-tree qualification at the native boundary."""

from __future__ import annotations

import importlib.util
import json
import marshal
import os
import struct
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import pf_native_control as p
import pytest
from pf_native_control import NativeControlError, reopen_job, spawn_owned

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job qualification")


@pytest.fixture
def native_root() -> Path:
    root = Path(os.environ["W3_FIXTURE_ROOT"]) / uuid4().hex
    root.mkdir(parents=True)
    return root


def _wait_file(path: Path) -> None:
    deadline = time.monotonic() + 5
    while not path.is_file():
        if time.monotonic() >= deadline:
            raise AssertionError("fixture child did not publish")
        time.sleep(0.01)


def test_runtime_idle_releases_lease_and_stale_finalizer_writes_nothing() -> None:
    import threading
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from pf_runtime import service

    held = 0
    stale = False
    writes: list[str] = []

    @contextmanager
    def operation(**kwargs):
        nonlocal held
        if stale:
            raise NativeControlError()
        held += 1
        try:
            yield
        finally:
            held -= 1

    def write(*args, **kwargs):
        assert held == 1
        writes.append("write")

    def idle(**kwargs):
        nonlocal stale
        assert held == 0
        stale = True

    runtime = object.__new__(service.RuntimeProcess)
    runtime.workplace_root = Path("unused-runtime-fixture")
    runtime.core = SimpleNamespace()
    runtime.instance_id = "fixture-instance"
    runtime.token = "fixture-token"
    runtime.stop_event = threading.Event()
    runtime.state_lock = threading.RLock()
    server = SimpleNamespace(server_address=("127.0.0.1", 0), serve_forever=idle)
    with (
        patch.object(runtime, "save", write),
        patch.object(
            p, "current_entry", return_value=SimpleNamespace(operation=operation)
        ),
        patch.object(service, "acquire_singleton", side_effect=write),
        patch.object(
            service, "release_singleton", side_effect=AssertionError("stale cleanup")
        ),
        patch.object(service, "base_state", return_value={}),
        patch.object(service, "append_operator_log", side_effect=write),
        patch.object(service, "ThreadingHTTPServer", return_value=server),
        patch.object(threading.Thread, "start"),
    ):
        with pytest.raises(NativeControlError):
            runtime.serve(0)
    assert held == 0
    assert len(writes) == 4  # singleton, two saves, startup log; no terminal writes.
    assert runtime.stop_event.is_set()


def test_runtime_metrics_error_persistence_stays_within_live_cycle() -> None:
    import threading
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from pf_runtime import service

    held = 0
    persisted: list[int] = []

    @contextmanager
    def operation(**kwargs):
        nonlocal held
        held += 1
        try:
            yield
        finally:
            held -= 1

    def fail(*args, **kwargs):
        assert held == 1
        raise OSError("unrelated_metrics_storage_fault")

    def save():
        assert held == 1
        persisted.append(held)

    def wait(delay):
        assert held == 0
        return True

    runtime = object.__new__(service.RuntimeProcess)
    runtime.workplace_root = Path("unused-runtime-fixture")
    runtime.state_lock = threading.RLock()
    runtime.state = {"scheduler": {"jobs": {}}}
    runtime.configuration = SimpleNamespace(
        config=SimpleNamespace(
            runtime=SimpleNamespace(metrics=SimpleNamespace(interval_seconds=1.0))
        )
    )
    with (
        patch.object(
            runtime,
            "stop_event",
            SimpleNamespace(is_set=lambda: False, wait=wait),
            create=True,
        ),
        patch.object(runtime, "reload_configuration", lambda: None),
        patch.object(runtime, "save", save),
        patch.object(
            p, "current_entry", return_value=SimpleNamespace(operation=operation)
        ),
        patch.object(
            service,
            "metrics_core",
            return_value=SimpleNamespace(registered_projects=fail),
        ),
    ):
        runtime.metrics_loop()
    assert persisted == [1]
    assert runtime.state["scheduler"]["jobs"]["metrics"]["last_result"] == "failed"


def test_native_acquire_refusal_does_not_relabel_body_oserror(
    native_root: Path,
) -> None:
    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    control = p.NativeControl(guard, epoch, "accepted")
    failure = OSError("unrelated_domain_fault")
    with pytest.raises(OSError) as caught:
        with control.operation():
            raise failure
    assert caught.value is failure
    epoch.write_bytes(b"\xff")
    with pytest.raises(NativeControlError):
        with control.operation():
            pytest.fail("invalid epoch admitted")
    epoch.unlink()
    with pytest.raises(NativeControlError):
        with control.operation():
            pytest.fail("missing epoch admitted")


def test_stale_runtime_closes_idle_transport_without_core_writes() -> None:
    import threading
    from types import SimpleNamespace
    from unittest.mock import patch

    from pf_runtime import service

    runtime = object.__new__(service.RuntimeProcess)
    runtime.stop_event = threading.Event()
    closed = threading.Event()
    with patch.object(
        runtime, "httpd", SimpleNamespace(shutdown=closed.set), create=True
    ):
        runtime._stop_stale()
        assert runtime.stop_event.is_set()
        assert closed.wait(1)


def test_copied_context_cannot_reuse_released_or_foreign_thread_lease(
    native_root: Path,
) -> None:
    import threading
    from contextvars import copy_context

    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    entry = p.NativeEntry(
        native_root, None, None, p.NativeControl(guard, epoch, "accepted")
    )
    refused: list[bool] = []

    def use():
        with pytest.raises(NativeControlError):
            with entry.operation():
                pytest.fail("copied lifetime admitted")
        refused.append(True)

    with entry.operation():
        copied = copy_context()
        other = copied.copy()
        thread = threading.Thread(target=lambda: other.run(use))
        thread.start()
        thread.join(1)
        assert not thread.is_alive() and refused == [True]
    copied.run(use)
    assert refused == [True, True]


def test_raw_iterator_retains_lease_until_close() -> None:
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from pf_runtime.raw_ingress_kernel import RawIngressKernel

    held = 0

    @contextmanager
    def operation(**kwargs):
        nonlocal held
        held += 1
        try:
            yield
        finally:
            held -= 1

    def records(*args, **kwargs):
        assert held == 1
        yield {"event_id": "one"}
        assert held == 1

    kernel = object.__new__(RawIngressKernel)
    kernel.database = Path("unused-fixture.sqlite")
    with (
        patch.object(
            kernel, "_operation", lambda: (SimpleNamespace(records=records), True)
        ),
        patch.object(
            p, "current_entry", return_value=SimpleNamespace(operation=operation)
        ),
    ):
        iterator = kernel.records()
        assert held == 0
        assert next(iterator) == {"event_id": "one"}
        assert held == 1
        iterator.close()
        assert held == 0


@pytest.mark.parametrize("adapter", ["codex_hooks", "kimi_hooks"])
def test_stale_hook_returns_neutral_without_diagnostics(adapter, capsys) -> None:
    import importlib
    import io
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from processforge_core import diagnostics

    module = importlib.import_module("pf_runtime." + adapter)

    @contextmanager
    def refuse(**kwargs):
        raise NativeControlError()
        yield

    with (
        patch.object(
            p, "current_entry", return_value=SimpleNamespace(operation=refuse)
        ),
        patch.object(sys, "stdin", io.StringIO('{"hook_event_name":"Stop"}')),
        patch.object(
            diagnostics, "for_project", side_effect=AssertionError("stale diagnostics")
        ),
    ):
        assert module.main() == 0
    assert capsys.readouterr().out == "{}\n"


def test_stale_executor_and_storage_script_keep_existing_failure_shapes(capsys) -> None:
    import argparse
    import runpy
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import patch

    from prepared_executor import run_target

    @contextmanager
    def refuse(**kwargs):
        raise NativeControlError()
        yield

    with patch.object(
        p, "current_entry", return_value=SimpleNamespace(operation=refuse)
    ):
        assert run_target(argparse.Namespace(), []) == 125
        main = runpy.run_path(
            str(Path(__file__).absolute().parents[2] / "tools/migrate-storage.py")
        )["main"]
        assert main(["--inspect", "--project-root", str(Path.cwd())]) == 1
    captured = capsys.readouterr()
    assert captured.err == "FAIL: execution_activity_unknown\n"
    assert len(captured.out.splitlines()) == 1
    assert json.loads(captured.out)["blocked"] is True


def _chain(root: Path, *, root_exits: bool = False) -> list[str]:
    child = root / "child.py"
    child.write_text(
        "import os,pathlib,time; p=pathlib.Path(__file__).with_suffix('.pid'); "
        "p.write_text(str(os.getpid())); time.sleep(60)",
        encoding="utf-8",
    )
    controller = root / "controller.py"
    controller.write_text(
        "import os,subprocess,sys,time; "
        "env=dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'; "
        "subprocess.Popen(['cmd.exe','/d','/c',sys.executable,'-B',"
        + repr(str(child))
        + "],env=env); "
        + ("time.sleep(0.3)" if root_exits else "time.sleep(60)"),
        encoding="utf-8",
    )
    return [sys.executable, "-B", str(controller)]


def test_timeout_waits_for_cmd_native_grandchild(native_root: Path) -> None:
    process = spawn_owned(
        _chain(native_root), env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    )
    job = getattr(process, "native_job")
    try:
        _wait_file(native_root / "child.pid")
        assert job.active() >= 3
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0.01)
        assert job.stop(deadline=time.monotonic() + 5)
        assert process.wait(timeout=5) == 130
        assert job.active() == 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


def test_terminal_root_does_not_hide_live_tree(native_root: Path) -> None:
    identity = {"run_id": "run", "task_id": "task", "attempt": 7}
    receipt = native_root / "native-tree.json"
    process = spawn_owned(
        _chain(native_root, root_exits=True), receipt_path=receipt, identity=identity
    )
    job = getattr(process, "native_job")
    try:
        _wait_file(native_root / "child.pid")
        assert process.wait(timeout=5) == 0
        assert job.active() >= 1
        reopened = reopen_job(
            json.loads(receipt.read_bytes()), pid=process.pid, identity=identity
        )
        assert reopened is not None
        try:
            assert reopened.active() >= 1
            assert reopened.stop(deadline=time.monotonic() + 5)
        finally:
            reopened.close()
        assert job.active() == 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


def test_root_death_last_job_close_cannot_leak_child(native_root: Path) -> None:
    process = spawn_owned(_chain(native_root))
    job = getattr(process, "native_job")
    try:
        _wait_file(native_root / "child.pid")
        # Reproduce wrapper-only kill, while retaining kernel ownership for proof.
        process.kill()
        process.wait(timeout=5)
        assert job.active() > 0
        assert job.stop(deadline=time.monotonic() + 5)
        assert job.active() == 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        job.close()


def test_reused_pid_or_wrong_attempt_never_signals(native_root: Path) -> None:
    identity = {"run_id": "run", "task_id": "task", "attempt": 1}
    process = spawn_owned(
        [sys.executable, "-B", "-c", "import time;time.sleep(60)"], identity=identity
    )
    job = getattr(process, "native_job")
    facts = getattr(process, "native_facts")
    try:
        with pytest.raises(NativeControlError):
            reopen_job(facts, pid=process.pid, identity={**identity, "attempt": 2})
        with pytest.raises(NativeControlError):
            reopen_job({**facts, "birth_id": "1"}, pid=process.pid, identity=identity)
        assert process.poll() is None
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


def test_controller_death_fence_is_inherited_before_execution(
    native_root: Path,
) -> None:
    tools = Path(__file__).resolve().parents[2] / "tools"
    controller = native_root / "outer.py"
    controller.write_text(
        "import os,sys,time;sys.path.insert(0," + repr(str(tools)) + ");"
        "from pf_native_control import spawn_owned;"
        "p=spawn_owned([sys.executable,'-B','-c',"
        + repr(
            "import pathlib,time;pathlib.Path("
            + repr(str(native_root / "started"))
            + ").write_text('yes');time.sleep(60)"
        )
        + "],receipt_path=__import__('pathlib').Path("
        + repr(str(native_root / "owner.json"))
        + "),identity={'attempt':1});"
        "time.sleep(60)",
        encoding="utf-8",
    )
    outer = spawn_owned([sys.executable, "-B", str(controller)])
    outer_job = getattr(outer, "native_job")
    try:
        _wait_file(native_root / "started")
        facts = json.loads((native_root / "owner.json").read_bytes())
        child_job = reopen_job(facts, pid=facts["pid"], identity={"attempt": 1})
        assert child_job is not None
        try:
            # Outer controller death closes its handle; inner inherited handle
            # still fences the exact child until the enclosing Job removes it.
            assert outer_job.stop(deadline=time.monotonic() + 5)
            outer.wait(timeout=5)
            assert child_job.active() == 0
        finally:
            child_job.stop(deadline=time.monotonic() + 5)
            child_job.close()
    finally:
        outer_job.stop(deadline=time.monotonic() + 5)
        outer.wait(timeout=5)
        outer_job.close()


def test_image_rejects_drift_and_requires_external_expected_pins(
    native_root: Path,
) -> None:
    import hashlib

    from pf_native_control import NativeImage

    source = native_root / "entry.py"
    source.write_bytes(b"value = 7\n")
    expected = {"entry.py": hashlib.sha256(b"value = 7\n").hexdigest()}
    image = NativeImage(native_root, expected)
    source.write_bytes(b"value = 99\n")
    assert image.read("entry.py") == b"value = 7\n"
    with pytest.raises(NativeControlError):
        NativeImage(native_root, expected)
    with pytest.raises(NativeControlError):
        NativeImage(native_root, {"../escape.py": expected["entry.py"]})


def test_image_direct_alias_lazy_import_resource_and_pyc(native_root: Path) -> None:
    import hashlib

    payload = {
        "src/captured_pkg/__init__.py": b"from .lazy import value\n",
        "src/captured_pkg/lazy.py": b"value = 7\n",
        "tools/entry.py": b"value = 8\n",
        "resource.txt": b"accepted resource\n",
    }
    for name, raw in payload.items():
        target = native_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    pins = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    script = r"""
import importlib.util,json,pathlib,sys
from pf_native_control import NativeImage,NativeControlError
root=pathlib.Path(sys.argv[1]); pins=json.loads(sys.argv[2]); image=NativeImage(root,pins)
(root/'src/captured_pkg/lazy.py').write_text('value=99')
(root/'tools/entry.py').write_text('value=99')
(root/'resource.txt').write_text('changed')
(root/'tools/injected.py').write_text('raise AssertionError(\"uncaptured code ran\")')
(root/'tools/__pycache__').mkdir()
(root/'tools/__pycache__/entry.cpython-314.pyc').write_bytes(b'untrusted')
sys.path.insert(0,str(root/'src'));sys.path.insert(0,str(root/'tools'))
image.activate()
import captured_pkg
assert captured_pkg.value==7
spec=importlib.util.spec_from_file_location('direct_alias',root/'tools/entry.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.value==8
assert (root/'resource.txt').read_text()=='accepted resource\n'
try: import injected
except NativeControlError: pass
else: raise AssertionError('uncaptured module admitted')
try: (root/'resource.txt').write_text('old Core write')
except NativeControlError: pass
else: raise AssertionError('payload mutation admitted')
print('image verified')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(native_root), json.dumps(pins)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "image verified"


def test_operation_lease_releases_at_idle_and_refuses_epoch_drift(
    native_root: Path,
) -> None:
    from pf_native_control import NativeControl

    guard, epoch = native_root / "guard", native_root / "epoch"
    control = NativeControl(guard, epoch, "accepted-epoch")
    assert not guard.exists() and not epoch.exists()
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted-epoch")
    with control.operation():
        with pytest.raises(NativeControlError):
            with control.exclusive(deadline=time.monotonic() + 0.1):
                raise AssertionError("lock upgrade")
    # Idle releases all request leases; update can acquire immediately.
    with control.exclusive(deadline=time.monotonic() + 0.1):
        epoch.write_bytes(b"next-epoch")
    with pytest.raises(NativeControlError):
        with control.operation(deadline=time.monotonic() + 0.1):
            raise AssertionError("stale operation admitted")


@pytest.mark.parametrize("mode", ["unadopted", "acquired", "nested"])
@pytest.mark.parametrize("boundary", ["entry", "service"])
def test_native_entry_preserves_frozen_error_and_releases_lease(
    native_root: Path,
    mode: str,
    boundary: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class FrozenError(Exception):
        code: str

    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    control = p.NativeControl(guard, epoch, "accepted")
    entry = p.NativeEntry(
        native_root, None, None, None if mode == "unadopted" else control
    )
    monkeypatch.setattr(p, "_ENTRY", entry)
    operation = entry.operation if boundary == "entry" else p.operation_lease
    error = FrozenError("snapshot_not_fresh")
    life = None
    try:
        with operation() as held:
            assert held is (entry if boundary == "entry" else None)
            life = p._OPERATION_LIFETIME.get()
            if mode == "unadopted":
                assert p._CONTROL_LEASE.get() is None
                assert life is None
            else:
                assert p._CONTROL_LEASE.get() is control
                assert life is not None and life.active
            if mode == "nested":
                try:
                    with operation():
                        raise error
                except FrozenError as caught:
                    assert caught is error
                    assert p._CONTROL_LEASE.get() is control
                    assert life is not None and life.active
                    raise
            raise error
    except FrozenError as caught:
        assert caught is error
        assert caught.code == "snapshot_not_fresh"
    else:
        raise AssertionError("domain error suppressed")
    assert p._CONTROL_LEASE.get() is None
    assert p._OPERATION_LIFETIME.get() is None
    if life is not None:
        assert not life.active
    with control.exclusive(deadline=time.monotonic() + 0.1):
        pass


def test_shared_requests_exclude_update_within_deadline(native_root: Path) -> None:
    import threading

    from pf_native_control import NativeControl

    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    control = NativeControl(guard, epoch, "accepted")
    outcomes: list[str | float] = []

    def contend() -> None:
        with control.operation(deadline=time.monotonic() + 0.1):
            outcomes.append("shared")
        before = time.monotonic()
        with pytest.raises(NativeControlError):
            with control.exclusive(deadline=before + 0.05):
                outcomes.append("bad exclusive")
        outcomes.append(time.monotonic() - before)

    with control.operation():
        thread = threading.Thread(target=contend)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
    assert outcomes[0] == "shared"
    elapsed = outcomes[1]
    assert isinstance(elapsed, float) and 0.04 <= elapsed < 0.2


def test_operation_lease_excludes_independent_update_process(native_root: Path) -> None:
    from pf_native_control import NativeControl

    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    control = NativeControl(guard, epoch, "accepted")
    script = """
import pathlib,sys,time
from pf_native_control import NativeControl,NativeControlError
c=NativeControl(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),'accepted')
try:
    with c.exclusive(deadline=time.monotonic()+0.1): pass
except NativeControlError: sys.exit(42)
"""
    command = [sys.executable, "-B", "-c", script, str(guard), str(epoch)]
    with control.operation():
        child = subprocess.run(
            command,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            timeout=5,
        )
        assert child.returncode == 42, child.stderr
    child = subprocess.run(
        command,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        timeout=5,
    )
    assert child.returncode == 0, child.stderr


def test_automatic_storage_reselects_between_adapters_but_refuses_stale_proof(
    native_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from processforge_core.accounting.composition import WorkplaceAccounting
    from processforge_core.composition import (
        build_configuration_provider,
        build_storage_migration_host,
    )
    from processforge_core.maintenance.contracts import MaintenanceError
    from processforge_core.process_event_journal import ProcessEventJournal

    project = native_root / "project"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    (flow / "process-forge.yaml").write_text("project:\n  id: stable-project\n")
    workplace = native_root / "workplace"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text("id: stable-workplace\n")
    device = native_root / "device.yaml"
    device.write_text("schema_version: 1\n")
    provider = build_configuration_provider(
        project_root=project, workplace_root=workplace, device_config_path=device
    )
    host = build_storage_migration_host(
        project_root=project,
        workplace_root=workplace,
        device_config_path=device,
        configuration=provider,
    )
    # Source mode has no managed migration authority, even after reselection.
    monkeypatch.setattr(p, "current_entry", lambda: None)
    before = host.context
    journal = ProcessEventJournal(storage_host=host)
    events = flow / "runtime/events/events.sqlite3"
    journal.append(events, {"event_id": "before"}, record=True)
    accounting = WorkplaceAccounting(
        workplace=workplace,
        project_root=project,
        project_id="stable-project",
        configuration=provider,
        storage_host=host,
    )
    assert accounting.service(create=True) is not None
    after = host.context
    assert before != after
    assert any(kind == "accounting" for kind, _path in before.unqualified_targets)
    assert not after.unqualified_targets
    assert host.service._proof(after).state == "unknown"
    with pytest.raises(MaintenanceError, match="storage_safety_unavailable"):
        host.service._proof(before)
    journal.append(events, {"event_id": "after"}, record=True)
    assert not (flow / "data/storage-identities.json").exists()
    assert not (workplace / "data/storage-identities.json").exists()
    # Re-enrollment still invalidates the captured context during one operation.
    (workplace / "workplace.yaml").write_text("id: other-workplace\n")
    with pytest.raises(MaintenanceError, match="storage_safety_unavailable"):
        host.service._proof(after)


def test_selected_cmd_round_trips_literal_argv_without_injection(
    native_root: Path,
) -> None:
    fake = native_root / "fake executable.py"
    received = native_root / "received.json"
    fake.write_text(
        "import json,pathlib,sys;"
        "pathlib.Path(__file__).with_name('received.json').write_text("
        "json.dumps(sys.argv[1:]),encoding='utf-8')",
        encoding="utf-8",
    )
    selected = native_root / "selected shim.cmd"
    selected.write_text(
        f'@echo off\n"{sys.executable}" -B "{fake}" %*\n', encoding="utf-8"
    )
    arguments = [
        "with spaces",
        'embedded"quote',
        "",
        "trailing\\",
        "space and trailing\\\\",
        'slashes\\\\"quote\\',
        "%!^&|<>()",
        "%W272_LITERAL%",
        "!W272_LITERAL!",
        'space %W272_LITERAL% !W272_LITERAL! ^&|<>() "quote" \\',
        "& echo injected>side-effect.txt &",
        '"& echo injected>side-effect.txt & rem "',
        '%W272_LITERAL%" & echo injected>side-effect.txt & "!W272_LITERAL!',
        "tab\tand (parentheses)",
    ]
    environment = {
        **os.environ,
        "PF_CODEX_EXECUTABLE": str(selected),
        "W272_LITERAL": "expanded & echo injected>side-effect.txt &",
    }
    process = spawn_owned(
        [environment["PF_CODEX_EXECUTABLE"], *arguments],
        cwd=native_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    job = getattr(process, "native_job")
    try:
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, (stdout, stderr)
        assert received.is_file(), (stdout, stderr)
        assert json.loads(received.read_text(encoding="utf-8")) == arguments
        assert not (native_root / "side-effect.txt").exists()
        assert job.active() == 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


def test_actual_codex_cmd_wrapper_contains_live_native_grandchild(
    native_root: Path,
) -> None:
    child = native_root / "sleeper.py"
    child.write_text(
        "import os,pathlib,time;pathlib.Path(__file__).with_suffix('.pid').write_text(str(os.getpid()));time.sleep(60)",
        encoding="utf-8",
    )
    fake = native_root / "fake_codex.py"
    fake.write_text(
        "import subprocess,sys;sys.stdin.buffer.read();subprocess.Popen([sys.executable,'-B',"
        + repr(str(child))
        + "])",
        encoding="utf-8",
    )
    command = native_root / "codex.cmd"
    command.write_text(
        '@echo off\n"' + sys.executable + '" -B "' + str(fake) + '" %*\n',
        encoding="utf-8",
    )
    for name, body in (
        ("prompt.md", "fixture only"),
        ("capsule.yaml", "{}"),
        ("access.json", "{}"),
    ):
        (native_root / name).write_text(body, encoding="utf-8")
    environment = {k: v for k, v in os.environ.items() if not k.startswith("PF_")}
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        PF_CODEX_EXECUTABLE=str(command),
        PF_AGENT_MODEL="fixture-no-model",
        PF_PROJECT_ROOT=str(native_root),
        PF_AGENT_EXIT_PATH=str(native_root / "exit.json"),
    )
    wrapper = Path(__file__).resolve().parents[2] / "tools/codex_exec_worker.py"
    with (
        (native_root / "stdout.log").open("wb") as stdout,
        (native_root / "stderr.log").open("wb") as stderr,
    ):
        process = spawn_owned(
            [
                sys.executable,
                "-B",
                str(wrapper),
                "--worker-prompt",
                str(native_root / "prompt.md"),
                "--capsule",
                str(native_root / "capsule.yaml"),
                "--workspace-access",
                str(native_root / "access.json"),
                "--output",
                str(native_root / "report.md"),
            ],
            env=environment,
            stdout=stdout,
            stderr=stderr,
        )
    job = getattr(process, "native_job")
    try:
        _wait_file(native_root / "sleeper.pid")
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0.1)
        assert not (native_root / "exit.json").exists()
        assert job.active() >= 2
        assert job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        assert job.active() == 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


LEAF_SOURCE = (
    b'"""Trusted fixture leaf; not the production control leaf."""\n'
    + p.BEGIN
    + b"_PUBLICATION_SEAL = None\n"
    + p.END
    + b"VALUE = 'source'\n"
)


def test_mcp_request_holds_real_lease_and_idle_releases(
    native_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pf_runtime import mcp_server

    guard, epoch = native_root / "guard", native_root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"accepted")
    control = p.NativeControl(guard, epoch, "accepted")
    entry = p.NativeEntry(native_root, None, None, control)
    monkeypatch.setattr(p, "_ENTRY", entry)
    calls = []

    def handler(*args: Any) -> dict[str, Any]:
        assert p._CONTROL_LEASE.get() is control
        calls.append("request")
        return {"accepted": True}

    monkeypatch.setattr(mcp_server, "_respond_in_operation", handler)
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call"}
    assert mcp_server.respond(request, native_root, "", None) == {"accepted": True}
    # A process-lifetime MCP object owns no lease between requests.
    with control.exclusive(deadline=time.monotonic() + 0.1):
        epoch.write_bytes(b"replaced")
    refused = mcp_server.respond(request, native_root, "", None)
    assert refused is not None and refused["result"]["isError"] is True
    assert "execution_activity_unknown" in refused["result"]["content"][0]["text"]
    assert calls == ["request"]


def build(payload: dict[str, bytes] | None = None) -> Any:
    """Create a deterministic in-memory publication."""
    return p.build_publication(
        payload
        or {
            p.LEAF: LEAF_SOURCE,
            p.INVENTORY: b"source inventory placeholder\n",
            "src/fixture_core.py": b"VALUE = 'accepted source'\n",
            "VERSION": b"1.3.0-alpha6\n",
            "resources/data.txt": b"resource\n",
        },
        version="1.3.0-alpha6",
        source={"vcs": "git", "commit": "a" * 40, "dirty": False},
        generated_at="2026-10-24T00:00:00Z",
    )


def test_qualified_publication_probes_actual_owned_backend_without_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = build(
        {
            p.LEAF: Path(p.__file__).read_bytes(),
            p.INVENTORY: b"source\n",
            "VERSION": b"1.3.0-alpha6\n",
        }
    )
    root = fixture_root(candidate)
    publication = p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])
    assert publication is not None
    monkeypatch.setattr(p, "_ENTRY", p.NativeEntry(root, publication, None, None))
    before = set(root.rglob("*"))
    assert p.supports_owned_execution() is True
    assert set(root.rglob("*")) == before


def fixture_root(candidate: Any) -> Path:
    """Write only an explicitly owned fixture, without OS tempfile/ACL setup."""
    root = Path(os.environ["W3_FIXTURE_ROOT"]) / "publication" / uuid4().hex
    root.mkdir(parents=True)
    for path, raw in candidate.payload.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (root / p.MANIFEST).write_bytes(candidate.manifest)
    return root


def encode(data: dict[str, Any]) -> bytes:
    """Change JSON formatting without changing semantic projection."""
    return json.dumps(data, separators=(",", ":")).encode()


def test_sealing_is_acyclic_and_second_build_idempotent() -> None:
    candidate = build()
    repeated = build(dict(candidate.payload))
    assert dict(repeated.payload) == dict(candidate.payload)
    assert repeated.manifest == candidate.manifest
    changed = dict(candidate.payload)
    changed[p.LEAF] = p._sealed_leaf(changed[p.LEAF], "b" * 64)
    changed[p.INVENTORY] = p.inventory_bytes(changed)
    final = p._manifest(
        changed,
        version="1.3.0-alpha6",
        source={"vcs": "git", "commit": "a" * 40, "dirty": False},
        generated_at="2026-10-24T00:00:00Z",
    )
    assert p.digest(final) != p.digest(candidate.manifest)
    assert p.projection(final) == p.projection(candidate.manifest)
    assert changed[p.INVENTORY] != candidate.payload[p.INVENTORY]
    with pytest.raises(TypeError):
        candidate.payload["new"] = b"bad"


def test_original_single_exclusion_has_transitive_inventory_cycle() -> None:
    candidate = build()
    data = p.parse_manifest(candidate.manifest)
    data["files"] = [r for r in data["files"] if r["relative_path"] != p.LEAF]
    naive_pin = p.digest(p.canonical_json(data))
    payload = dict(candidate.payload)
    payload[p.LEAF] = p._sealed_leaf(payload[p.LEAF], naive_pin)
    payload[p.INVENTORY] = p.inventory_bytes(payload)
    row = next(r for r in data["files"] if r["relative_path"] == p.INVENTORY)
    row.update(size=len(payload[p.INVENTORY]), sha256=p.digest(payload[p.INVENTORY]))
    assert p.digest(p.canonical_json(data)) != naive_pin


def test_old_copy_and_manifest_reserialization_accepts_without_new_script() -> None:
    candidate = build()
    root = fixture_root(candidate)
    data = p.parse_manifest(candidate.manifest)
    data["files"].reverse()
    (root / p.MANIFEST).write_bytes(encode(data))
    accepted = p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])
    assert accepted is not None
    assert dict(accepted.payload) == dict(candidate.payload)
    assert accepted.projection_sha256 == candidate.projection_sha256
    assert not (root / "runtime").exists()
    assert not (root / "guard").exists()


def test_payload_tamper_refuses_and_captured_bytes_survive_drift() -> None:
    candidate = build()
    root = fixture_root(candidate)
    accepted = p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])
    assert accepted is not None
    (root / "src/fixture_core.py").write_bytes(b"tampered\n")
    assert (
        accepted.payload["src/fixture_core.py"]
        == candidate.payload["src/fixture_core.py"]
    )
    with pytest.raises(p.Refusal, match="payload_drift|read_limit"):
        p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])


@pytest.mark.parametrize("field", ["version", "source", "generated_at", "files"])
def test_manifest_repin_from_current_files_cannot_create_authority(field: str) -> None:
    candidate = build()
    root = fixture_root(candidate)
    data = p.parse_manifest(candidate.manifest)
    if field == "files":
        data[field] = [r for r in data[field] if r["relative_path"] != "VERSION"]
    elif field == "source":
        data[field] = {"commit": "b" * 40}
    else:
        data[field] = "changed"
    (root / p.MANIFEST).write_bytes(encode(data))
    with pytest.raises(p.Refusal, match="publication_drift"):
        p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])


def test_derived_inventory_is_not_an_unchecked_exemption() -> None:
    candidate = build()
    root = fixture_root(candidate)
    malicious = b"forged inventory\n"
    data = p.parse_manifest(candidate.manifest)
    row = next(r for r in data["files"] if r["relative_path"] == p.INVENTORY)
    row.update(size=len(malicious), sha256=p.digest(malicious))
    raw = encode(data)
    assert p.projection(raw) == p.projection(candidate.manifest)
    (root / p.MANIFEST).write_bytes(raw)
    (root / p.INVENTORY).write_bytes(malicious)
    with pytest.raises(p.Refusal, match="derived_inventory_drift"):
        p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])


def test_trusted_leaf_entry_still_compares_exact_captured_source() -> None:
    candidate = build()
    root = fixture_root(candidate)
    data = p.parse_manifest(candidate.manifest)
    row = next(r for r in data["files"] if r["relative_path"] == p.LEAF)
    row["sha256"] = "a" * 64
    (root / p.MANIFEST).write_bytes(encode(data))
    with pytest.raises(p.Refusal, match="payload_drift"):
        p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])


def test_duplicate_keys_rows_and_aliases_refuse_before_overwrite() -> None:
    candidate = build()
    with pytest.raises(p.Refusal):
        p.parse_manifest(
            candidate.manifest.replace(
                b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'
            )
        )
    for alias in ("VERSION", "version"):
        data = p.parse_manifest(candidate.manifest)
        data["files"].append({"relative_path": alias, "size": 0, "sha256": "a" * 64})
        with pytest.raises(p.Refusal, match="duplicate_path"):
            p.projection(encode(data))


@pytest.mark.parametrize(
    "path",
    [
        "../x",
        "/x",
        "C:/x",
        "x\\y",
        "x//y",
        "x/./y",
        "x:ads",
        "nul.txt",
        "x. ",
        "x\0y",
        "e\u0301.txt",
    ],
)
def test_unsafe_paths_refuse(path: str) -> None:
    with pytest.raises(p.Refusal):
        p.safe_path(path)


def test_file_directory_collision_and_bytecode_rows_refuse() -> None:
    candidate = build()
    data = p.parse_manifest(candidate.manifest)
    data["files"].append({"relative_path": "src", "size": 0, "sha256": "a" * 64})
    with pytest.raises(p.Refusal, match="file_directory_collision"):
        p.projection(encode(data))
    for path in (p.MANIFEST, "src/module.pyc", "src/module.pyo"):
        data = p.parse_manifest(candidate.manifest)
        data["files"].append({"relative_path": path, "size": 0, "sha256": "a" * 64})
        with pytest.raises(p.Refusal, match="excluded_or_bytecode_entry"):
            p.projection(encode(data))


def test_unsealed_unsupported_reads_do_not_touch_or_create_root() -> None:
    root = Path(os.environ["W3_FIXTURE_ROOT"]) / "publication" / uuid4().hex
    unknown = LEAF_SOURCE.replace(b"None", b"('pf.publication.v999', 'unsupported')")
    for leaf in (b"VALUE = 'legacy'\n", LEAF_SOURCE, unknown):
        assert p.accept_publication(root, trusted_leaf=leaf) is None
        assert not root.exists()
    with pytest.raises(p.Refusal):
        p.accept_publication(
            root,
            trusted_leaf=LEAF_SOURCE.replace(b"None", b"('pf.publication.v1', 'bad')"),
        )
    with pytest.raises(p.Refusal):
        p.accept_publication(root, trusted_leaf=build().payload[p.LEAF])
    assert not root.exists()


@pytest.mark.parametrize("relative", ["src/fixture_core.py", p.LEAF])
def test_source_compile_ignores_actual_unchecked_pyc(relative: str) -> None:
    candidate = build()
    root = fixture_root(candidate)
    source = root / relative
    cache = Path(importlib.util.cache_from_source(str(source)))
    cache.parent.mkdir(parents=True)
    poison = compile("VALUE = 'unchecked pyc'", str(source), "exec")
    cache.write_bytes(
        importlib.util.MAGIC_NUMBER
        + struct.pack("<I", 1)
        + b"\0" * 8
        + marshal.dumps(poison)
    )
    spec = importlib.util.spec_from_file_location("fixture_untrusted_loader", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.VALUE == "unchecked pyc"  # -B does not disable pyc reads.
    accepted = p.accept_publication(root, trusted_leaf=candidate.payload[p.LEAF])
    assert accepted is not None
    namespace: dict[str, Any] = {}
    exec(
        compile(
            accepted.payload[relative],
            str(source),
            "exec",
            dont_inherit=True,
        ),
        namespace,
    )
    assert namespace["VALUE"] == ("source" if relative == p.LEAF else "accepted source")
    leaf_namespace: dict[str, Any] = {}
    exec(
        compile(candidate.payload[p.LEAF], p.LEAF, "exec", dont_inherit=True),
        leaf_namespace,
    )
    assert leaf_namespace["_PUBLICATION_SEAL"] == (
        p.SEAL_KIND,
        candidate.projection_sha256,
    )


def test_canonicalization_precedes_freeze_and_source_is_unchanged() -> None:
    candidate = build()
    source = dict(candidate.payload)
    source[p.LEAF] = LEAF_SOURCE.replace(b"\n", b"\r\n")
    source["resources/data.txt"] = b"a\r\nb\r\n"
    original = dict(source)
    staged = {path: p.canonical_release_bytes(raw) for path, raw in source.items()}
    sealed = build(staged)
    assert source == original
    assert b"\r\n" not in sealed.payload[p.LEAF]
    assert sealed.payload["resources/data.txt"] == b"a\nb\n"
    assert p.canonical_release_bytes(b"binary\0\r\n") == b"binary\0\r\n"


def test_real_packager_freezes_before_zip_and_freshness_replays(
    native_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import zipfile

    import processforge as cli

    payload = {
        p.LEAF: LEAF_SOURCE,
        p.INVENTORY: b"unsealed inventory\n",
        "VERSION": b"1.3.0-alpha6\r\n",
        "docs/example.txt": b"before\r\n",
    }
    selected = []
    for name, content in payload.items():
        target = native_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        selected.append((name, target))
    source = {"commit": "a" * 40, "dirty": False}
    generated_at = "2026-10-24T00:00:00Z"
    frozen, core_manifest = cli._sealed_release_payload(
        selected, version="1.3.0-alpha6", source=source, generated_at=generated_at
    )
    assert (native_root / p.LEAF).read_bytes() == LEAF_SOURCE
    assert frozen["docs/example.txt"] == b"before\n"
    (native_root / "docs/example.txt").write_bytes(b"after freeze")
    archive = native_root / "fixture.zip"
    rows = cli.write_release_zip(
        archive,
        [],
        1761264000,
        extra_entries=[
            *frozen.items(),
            (
                p.MANIFEST,
                (json.dumps(core_manifest, indent=2, sort_keys=True) + "\n").encode(),
            ),
        ],
    )
    with zipfile.ZipFile(archive) as opened:
        assert opened.read("docs/example.txt") == b"before\n"
        for row in rows:
            assert row["sha256"] == hashlib.sha256(opened.read(row["path"])).hexdigest()
    # Freshness is a deterministic rebuild, including both generated entries.
    (native_root / "docs/example.txt").write_bytes(frozen["docs/example.txt"])
    monkeypatch.setattr(cli, "expected_release_files_from_root", lambda root: selected)
    sidecar = {
        "version": "1.3.0-alpha6",
        "source": source,
        "build": {"generated_at": generated_at},
    }
    expected = cli.expected_release_manifest_from_root(native_root, sidecar)
    assert expected == {row["path"]: row["sha256"] for row in rows}
    for name, raw in frozen.items():
        (native_root / name).write_bytes(raw)
    assert cli.expected_release_manifest_from_root(native_root, sidecar) == expected
    (native_root / "docs/example.txt").write_bytes(b"drift")
    assert cli.expected_release_manifest_from_root(native_root, sidecar) != expected


def test_real_packager_rejects_duplicates_before_mapping(native_root: Path) -> None:
    import processforge as cli

    target = native_root / "x"
    target.write_bytes(b"x")
    with pytest.raises(p.Refusal, match="duplicate_path"):
        cli._sealed_release_payload(
            [("VERSION", target), ("version", target)],
            version="fixture",
            source={},
            generated_at="fixture",
        )


@pytest.mark.parametrize("entry_name", ["cli", "service", "core"])
def test_actual_trusted_entry_captures_leaf_core_aliases_and_resources(
    native_root: Path,
    entry_name: str,
) -> None:
    import processforge as cli

    assert p.__file__ is not None
    payload = {
        p.LEAF: Path(p.__file__).read_bytes(),
        p.INVENTORY: b"source inventory\n",
        "src/fixture_core.py": b"VALUE = 'accepted'\n",
        "src/processforge_core/__init__.py": b"VALUE = 'accepted Core'\n",
        "docs/data.txt": b"accepted resource\n",
        "VERSION": b"1.3.0-alpha6\n",
    }
    if entry_name in {"service", "core"}:
        # Exercise the complete existing service/Legacy bridge, not an extracted
        # preamble with synthetic Core. The helper is shared with adopted tests.
        payload.update(_adopted_publication().payload)
    candidate = build(payload)
    for name, raw in candidate.payload.items():
        path = native_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (native_root / p.MANIFEST).write_bytes(candidate.manifest)
    cached = [p.LEAF, "src/fixture_core.py"]
    if entry_name == "cli":
        cached.append("src/processforge_core/__init__.py")
    else:
        cached.append("src/processforge_core/bootstrap.py")
    for name in cached:
        source = native_root / name
        cache = Path(importlib.util.cache_from_source(str(source)))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(
            importlib.util.MAGIC_NUMBER
            + struct.pack("<I", 1)
            + b"\0" * 8
            + marshal.dumps(
                compile(
                    "raise RuntimeError('unchecked cache executed')",
                    str(source),
                    "exec",
                )
            )
        )
    assert cli.__file__ is not None
    if entry_name == "cli":
        preamble = (
            Path(cli.__file__)
            .read_text(encoding="utf-8")
            .split("if TYPE_CHECKING:", 1)[0]
        )
        entry = native_root / "tools/fixture-entry.py"
    else:
        preamble = """
import importlib.util,json,sys
from pathlib import Path
_native_root = Path(__file__).absolute().parents[1]
sys.path[:0] = [str(_native_root / 'src'), str(_native_root / 'tools')]
"""
        if entry_name == "core":
            preamble += """
from processforge_core import bootstrap_runtime
assert 'processforge' not in sys.modules
assert not any(n.startswith(('pf_cli', 'pf_runtime')) for n in sys.modules)
runtime = bootstrap_runtime(__file__)
"""
        else:
            preamble += """
from pf_runtime import service
from processforge_core import bootstrap_runtime
runtime = bootstrap_runtime(__file__)
assert runtime.service is service
assert hasattr(service, 'RuntimeProcess')
"""
        preamble += """
assert runtime.core is sys.modules['processforge']
assert runtime.core is sys.modules['processforge_core._legacy_processforge']
assert runtime.service.host is runtime.host
assert bootstrap_runtime(__file__).core is runtime.core
_native_module = sys.modules['pf_native_control']
_native_entry = _native_module.current_entry()
"""
        entry = native_root / "tools/fixture-entry.py"
    entry.write_text(
        preamble
        + """
sys.path.insert(0, str(_native_root / "src"))
import processforge_core
if hasattr(processforge_core, 'VALUE'):
    assert processforge_core.VALUE == 'accepted Core'
import fixture_core
with _native_module._PHYSICAL_OPEN(_native_root / "src/fixture_core.py", "wb") as target:
    target.write(b"raise RuntimeError('drift executed')")
spec = importlib.util.spec_from_file_location("captured_direct_alias", _native_root / "src/fixture_core.py")
alias = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alias)
print(json.dumps({"normal": fixture_core.VALUE, "alias": alias.VALUE,
    "resource": (_native_root / "docs/data.txt").read_text(),
    "publication": _native_entry.publication.projection_sha256}))
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-B", str(entry)],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "normal": "accepted",
        "alias": "accepted",
        "resource": "accepted resource\n",
        "publication": candidate.projection_sha256,
    }
    assert not (native_root / "runtime").exists()
    if entry_name == "core":
        (native_root / "src/fixture_core.py").write_bytes(
            candidate.payload["src/fixture_core.py"]
        )
        # A completed/unqualified Core cannot be retrospectively promoted.
        refused = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import sys,types; from pathlib import Path; "
                "root=Path(sys.argv[1]); "
                "sys.path[:0]=[str(root/'tools'),str(root/'src')]; "
                "m=types.ModuleType('processforge_core'); "
                "exec('VALUE = 1',m.__dict__); "
                "sys.modules[m.__name__]=m; from pf_runtime import service",
                str(native_root),
            ],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert refused.returncode != 0
        assert "execution_activity_unknown" in refused.stderr
        initializer = native_root / "src/processforge_core/__init__.py"
        unqualified = (
            initializer.read_bytes()
            + b"\nraise AssertionError('unqualified business ran')\n"
        )
        cache = Path(importlib.util.cache_from_source(str(initializer)))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(
            importlib.util.MAGIC_NUMBER
            + struct.pack("<I", 1)
            + b"\0" * 8
            + marshal.dumps(compile(unqualified, str(initializer), "exec"))
        )
        refused = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import sys; sys.path[:0]=sys.argv[1:]; import processforge_core",
                str(native_root / "src"),
                str(native_root / "tools"),
            ],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert refused.returncode != 0
        assert "execution_activity_unknown" in refused.stderr
        assert "unqualified business ran" not in refused.stderr


def test_publication_read_exclusion_blocks_an_old_uncooperative_writer(
    native_root: Path,
) -> None:
    candidate = build()
    for name, raw in candidate.payload.items():
        path = native_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (native_root / p.MANIFEST).write_bytes(candidate.manifest)
    with p._publication_read_exclusion(native_root):
        with pytest.raises(PermissionError):
            (native_root / "src/fixture_core.py").write_bytes(b"overwrite")
    (native_root / "src/fixture_core.py").write_bytes(b"after capture")


def test_fixture_archive_passes_unchanged_validator_and_real_root_freshness(
    native_root: Path,
) -> None:
    import zipfile

    import processforge as cli

    assert cli.__file__ is not None
    product = Path(cli.__file__).parent
    source = native_root / "source"
    source.mkdir()
    payload = {
        p.LEAF: LEAF_SOURCE,
        p.INVENTORY: b"old inventory\n",
        "VERSION": b"1.3.0-alpha6\n",
        "docs/example.txt": b"fixture\n",
        "tools/validate-process-forge-checksums.py": (
            product / "validate-process-forge-checksums.py"
        ).read_bytes(),
    }
    files = []
    for name, raw in payload.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files.append((name, path))
    provenance = {"commit": "b" * 40, "dirty": False}
    generated = "2026-10-24T00:00:00Z"
    frozen, manifest = cli._sealed_release_payload(
        files,
        version="1.3.0-alpha6",
        source=provenance,
        generated_at=generated,
    )
    archive = native_root / "fixture.zip"
    rows = cli.write_release_zip(
        archive,
        [],
        1761264000,
        extra_entries=[
            *frozen.items(),
            (
                p.MANIFEST,
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
            ),
        ],
    )
    extracted = native_root / "extracted"
    with zipfile.ZipFile(archive) as opened:
        opened.extractall(extracted)
    checked = subprocess.run(
        [
            sys.executable,
            "-B",
            str(extracted / "tools/validate-process-forge-checksums.py"),
            "--root",
            str(extracted),
            "--check",
        ],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    accepted = p.accept_publication(extracted, trusted_leaf=frozen[p.LEAF])
    assert accepted is not None and dict(accepted.payload) == frozen
    sidecar = {
        "version": "1.3.0-alpha6",
        "source": provenance,
        "build": {"generated_at": generated},
    }
    assert cli.expected_release_manifest_from_root(extracted, sidecar) == {
        row["path"]: row["sha256"] for row in rows
    }


# Joint fixtures qualify adopted state only; they do not reconstruct FIRST history.
assert p.__file__ is not None
_ADOPTED_SOURCE = Path(p.__file__).absolute().parents[1]

_ADOPTED_PREAMBLE = r"""
import json,sys,types
from pathlib import Path
root=Path(sys.argv[1]);leaf=(root/'tools/pf_native_control.py').read_bytes()
p=types.ModuleType('pf_native_control');p.__file__=str(root/'tools/pf_native_control.py');p._captured_source=leaf
sys.modules[p.__name__]=p;exec(compile(leaf,p.__file__,'exec',dont_inherit=True),p.__dict__)
sys.path[:0]=[str(root/'tools'),str(root/'src')]
"""
_ADOPTED_MANAGER = (
    _ADOPTED_PREAMBLE
    + r"""
work=root/'runtime/fixture';work.mkdir(parents=True)
(work/'gate').write_bytes(b'0');(work/'protocol').write_bytes(b'original')
publication=p.accept_publication(root,trusted_leaf=leaf)
boundary=p.LegacyManagedBoundary(root,existing_gate=p.NativeControl(work/'gate',work/'protocol','original'),accepted_archive=publication.payload)
owner=boundary.launch([sys.executable,'-B','-c','pass'],ingress='worker');assert owner.wait(timeout=5)==0
entry=p.NativeEntry(root,publication,p.NativeImage.from_publication(root,publication),None)
entry.image.activate()
from processforge_core.composition import build_configuration_provider,build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider
project=work/'project';flow=project/'.pf';flow.mkdir(parents=True)
(flow/'process-forge.yaml').write_text('project:\n  id: stable-project\n')
device=work/'device.yaml';device.write_text('schema_version: 1\nruntime:\n  metrics:\n    interval_seconds: 17\n')
provider=build_configuration_provider(project_root=project,device_config_path=device)
config=ConfigurationProvider.pinned(provider.snapshot().config)
host=build_storage_migration_host(project_root=project,workplace_root=None,device_config_path=device,configuration=config)
producer,entry=p.ManagedEnrollmentProducer.from_legacy_manager(boundary,entry,selection=host.service._native_selection())
print(json.dumps({'generation':producer._state()['adoption']}))
"""
)
_ADOPTED_CHILD = (
    _ADOPTED_PREAMBLE
    + r"""
entry=p.bootstrap_entry(root,trusted_leaf=leaf)
from processforge_core.composition import build_configuration_provider,build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider
from processforge_core.project.configuration_inputs import configuration_operation
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.executions.composition import select_execution_storage
import processforge as cli
project=root/'runtime/fixture/project';device=root/'runtime/fixture/device.yaml'
provider=build_configuration_provider(project_root=project,device_config_path=device)
config=ConfigurationProvider.pinned(provider.snapshot().config)
host=build_storage_migration_host(project_root=project,workplace_root=None,device_config_path=device,configuration=config)
with entry.operation():
    journal=ProcessEventJournal(storage_host=host)
    journal.append(project/'.pf/runtime/events/events.sqlite3',{'event_id':sys.argv[2]},record=True)
    with configuration_operation(project,None,device_config_path=device,configuration=config):
        cli._storage_first_write(project)
    result=host.service.resume(host.context)
    assert not result['blocked'],result
    selected=select_execution_storage(project,None,configuration=config)
    pins=json.loads((project/'.pf/data/storage-identities.json').read_text())
    assert entry.storage_safety(host.context)[0]=='unknown'
    print(json.dumps({'generation':p.ManagedEnrollmentProducer(root,leaf)._state()['adoption'],'interval':config.get('runtime.metrics.interval_seconds'),'pins':pins,'result':result,'authority':selected.repository.readiness().authority}))
"""
)


def _adopted_run(
    code: str, root: Path, *args: object, timeout: int = 60
) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(root), *map(str, args)],
        env={
            **os.environ,
            "LOCALAPPDATA": str(root / "runtime/device"),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    return json.loads(result.stdout)


def _adopted_publication(version: str = "1.3.0-alpha6") -> p.Build:
    payload = {}
    for directory in ("src", "tools", "schemas", "bin"):
        for path in (_ADOPTED_SOURCE / directory).rglob("*"):
            if (
                path.is_file()
                and path.suffix in {".py", ".json", ".yaml", ".txt", ".md"}
                and "__pycache__" not in path.parts
            ):
                payload[path.relative_to(_ADOPTED_SOURCE).as_posix()] = (
                    path.read_bytes()
                )
    payload["VERSION"] = (version + "\n").encode()
    payload[p.INVENTORY] = b""
    return p.build_publication(
        payload,
        version=version,
        source={"commit": "f" * 40, "dirty": False},
        generated_at="fixture",
    )


def _adopted_fixture_install(root: Path) -> tuple[Path, p.Build]:
    root.mkdir(parents=True, exist_ok=True)
    build = _adopted_publication()
    for name, raw in {**build.payload, p.MANIFEST: build.manifest}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    device = root / "runtime/device/ProcessForge/configuration.yaml"
    device.parent.mkdir(parents=True)
    device.write_text("schema_version: 1\n", encoding="utf-8")
    return root, build


def test_real_adopted_factory_after_manager_exit(native_root: Path) -> None:
    root, _ = _adopted_fixture_install(native_root)
    bound = _adopted_run(_ADOPTED_MANAGER, root)
    first = _adopted_run(_ADOPTED_CHILD, root, "one")
    second = _adopted_run(_ADOPTED_CHILD, root, "two")
    assert bound["generation"] == first["generation"] == second["generation"]
    assert first["interval"] == second["interval"] == 17
    assert first["authority"] == second["authority"] == "sql"
    assert first["pins"] == second["pins"]


_ADOPTED_UPDATE = (
    _ADOPTED_PREAMBLE
    + r"""
entry=p.bootstrap_entry(root,trusted_leaf=leaf)
from processforge_core.maintenance.update import apply_update
record=apply_update(root,Path(sys.argv[2]),confirm=True)
assert record['status']=='applied',record
print(json.dumps(record))
"""
)


def test_joint_real_updater_and_independent_successor_child(native_root: Path) -> None:
    root, old = _adopted_fixture_install(native_root / "target")
    _adopted_run(_ADOPTED_MANAGER, root)
    new = _adopted_publication("1.3.0-alpha7")
    archive = root / "runtime/fixture-release.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, raw in {**new.payload, p.MANIFEST: new.manifest}.items():
            bundle.writestr(name, raw)
    before = json.loads((root / "runtime/managed-ingress/baseline.json").read_text())
    management, _ = _adopted_fixture_install(native_root / "independent-management")
    command = [
        sys.executable,
        "-B",
        str(management / "bin/pf.py"),
        "core-update",
        "apply",
        "--core-root",
        str(root),
        "--archive",
        str(archive),
        "--confirm",
    ]
    applied = subprocess.run(command, capture_output=True, text=True, timeout=240)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    record = json.loads(applied.stdout)
    after = json.loads((root / "runtime/managed-ingress/baseline.json").read_text())
    assert before["adoption"] != after["adoption"]
    assert after["phase"] == "bound" and len(after["successors"]) == 1
    assert (root / "VERSION").read_text().strip() == "1.3.0-alpha7"
    assert (
        json.loads((root / "runtime/core-update/last-apply.json").read_text()) == record
    )
    assert not (root / "runtime/core-update/in-progress.json").exists()
    # Stale generation loses its epoch even if the payload is replaced again with identical bytes.
    result = _adopted_run(_ADOPTED_CHILD, root, "after-update")
    assert result["generation"] == after["adoption"]
    (root / "VERSION").write_bytes(b"local second preimage")
    second = subprocess.run(command, capture_output=True, text=True, timeout=240)
    assert second.returncode == 0, second.stdout + second.stderr
    second_record = json.loads(second.stdout)
    assert (
        Path(second_record["backup_dir"]) / "files/VERSION"
    ).read_bytes() == b"local second preimage"
    latest = json.loads((root / "runtime/managed-ingress/baseline.json").read_text())
    assert len(latest["successors"]) == 2 and latest["adoption"] != after["adoption"]
    assert latest["successors"][-1]["maintenance"]["manifest_sha256"] == p.digest(
        new.manifest
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "local",
        "unchanged-local",
        "manifest",
        "epoch",
        "selection",
        "unbound-cli",
        "public-cli",
        "configuration",
        "owner",
        "excluded-leaf",
        "excluded-inventory",
        "malformed",
        "unknown",
    ],
)
def test_real_updater_retained_target_repair_force_and_authority(
    native_root: Path, case: str
) -> None:
    management, _ = _adopted_fixture_install(native_root / "management")
    result = _adopted_run(
        _ADOPTED_PREAMBLE
        + r"""
entry=p.bootstrap_entry(root,trusted_leaf=leaf)
import zipfile
from smoke_core_update_manifest import managed_target,write_native_archive,apply_managed_update
from processforge_core.maintenance.update import CoreUpdateError,apply_update,build_plan
case=sys.argv[2];target=root.parent/'target';archive=root.parent/'new.zip'
files={'same.txt':'same','changed.txt':'old','removed.txt':'gone'}
with managed_target(target,files) as retained:
    write_native_archive(archive,{'same.txt':'same','changed.txt':'new'},version='1.3.0-alpha7')
    with zipfile.ZipFile(archive) as bundle: expected_leaf=bundle.read(p.LEAF)
    (target/'unknown.txt').write_bytes(b'preserve')
    authority=('runtime/managed-ingress/baseline.json','runtime/managed-ingress/adoption.json','runtime/native-control/epoch')
    def snapshot():
        return {name:(target/name).read_bytes() for name in (*authority,p.MANIFEST,'changed.txt','unknown.txt') if (target/name).is_file()}
    before_generation=json.loads((target/authority[0]).read_text())['adoption']
    if case=='missing':
        for name in files: (target/name).unlink()
        plan=build_plan(target,archive)
        assert plan['missing_owned']==['changed.txt','removed.txt','same.txt'],plan
        assert plan['restored']==['same.txt'],plan
    elif case in {'local','unchanged-local','public-cli'}:
        (target/('same.txt' if case=='unchanged-local' else 'changed.txt')).write_bytes(b'local-preimage')
        assert not (target/'runtime/core-update').exists()
    elif case=='manifest':
        raw=json.loads((target/p.MANIFEST).read_text())
        (target/p.MANIFEST).write_text(json.dumps(raw))
    elif case=='epoch':
        (target/authority[2]).write_bytes(b'stale-target-epoch')
    elif case=='selection':
        raw=json.loads((target/authority[0]).read_text());raw['selection']['owner']='another-owner'
        (target/authority[0]).write_text(json.dumps(raw))
    if case=='unbound-cli':
        # A truly never-adopted sibling retains the negative CLI control.
        target=root.parent/'never-adopted';target.mkdir()
        for name,raw in {**retained.publication.payload,p.MANIFEST:retained.publication.manifest}.items():
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        (target/'changed.txt').write_bytes(b'local-preimage')
    if case=='configuration':
        device=Path(json.loads((target/authority[0]).read_text())['retirement']['baseline']['maintenance']['device_config_path'])
        device.write_text('schema_version: 1\nruntime:\n  metrics:\n    interval_seconds: 18\n')
    if case=='owner':
        project=Path(json.loads((target/authority[0]).read_text())['selection']['project'])
        (project/'.pf/process-forge.yaml').write_text('project:\n  id: external-owner\n')
    if case in {'excluded-leaf','excluded-inventory'}:
        raw=json.loads((target/p.MANIFEST).read_text());name=p.LEAF if case=='excluded-leaf' else p.INVENTORY
        next(row for row in raw['files'] if row['relative_path']==name)['sha256']='0'*64
        assert p.digest(p.projection(json.dumps(raw).encode()))==retained.publication.projection_sha256
        (target/p.MANIFEST).write_text(json.dumps(raw))
    if case in {'malformed','unknown'}:
        raw=json.loads((target/authority[0]).read_text())
        raw['retirement']['baseline']['maintenance']={'manifest_sha256':p.digest((target/p.MANIFEST).read_bytes()),'device_config_path':'relative'} if case=='malformed' else {'unknown':'authority'}
        (target/authority[0]).write_text(json.dumps(raw))
    if case in {'manifest','epoch','selection','unbound-cli','configuration','owner','excluded-leaf','excluded-inventory','malformed','unknown'}:
        before=snapshot()
        if case=='unbound-cli':
            import subprocess
            refused=subprocess.run([sys.executable,'-B',str(root/'bin/pf.py'),'core-update','apply','--core-root',str(target),'--archive',str(archive),'--confirm','--force-local-modifications'],capture_output=True,text=True,timeout=30)
            assert refused.returncode!=0,refused.stdout
            assert json.loads(refused.stdout)['error']['code']=='plan_blocked',refused.stdout+refused.stderr
        else:
            for force in (False,True):
                try: apply_managed_update(retained,archive,force_local_modifications=force)
                except CoreUpdateError as error: assert error.code=='plan_blocked',error
                else: raise AssertionError('force bypassed target authority')
                import subprocess
                command=[sys.executable,'-B',str(root/'bin/pf.py'),'core-update','apply','--core-root',str(target),'--archive',str(archive),'--confirm']
                if force: command.append('--force-local-modifications')
                refused=subprocess.run(command,capture_output=True,text=True,timeout=30)
                assert refused.returncode!=0,refused.stdout
                assert json.loads(refused.stdout)['error']['code']=='plan_blocked',refused.stdout+refused.stderr
        assert snapshot()==before
        assert not (target/'runtime/core-update').exists()
        print(json.dumps({'case':case,'refused':True}))
    else:
        if case=='public-cli':
            import subprocess
            applied=subprocess.run([sys.executable,'-B',str(root/'bin/pf.py'),'core-update','apply','--core-root',str(target),'--archive',str(archive),'--confirm','--force-local-modifications'],capture_output=True,text=True,timeout=240)
            assert applied.returncode==0,applied.stdout+applied.stderr
            record=json.loads(applied.stdout)
        else:
            record=apply_managed_update(retained,archive,force_local_modifications=False)
        assert record['status']=='applied',record
        assert (target/'same.txt').read_bytes()==b'same'
        assert (target/'changed.txt').read_bytes()==b'new'
        assert not (target/'removed.txt').exists()
        assert (target/'unknown.txt').read_bytes()==b'preserve'
        if case=='missing':
            assert record['backed_up']['same.txt'] is None
            assert record['backed_up']['changed.txt'] is None
            assert record['backed_up']['removed.txt'] is None
        else:
            assert (Path(record['backup_dir'])/'files'/('same.txt' if case=='unchanged-local' else 'changed.txt')).read_bytes()==b'local-preimage'
        state=json.loads((target/authority[0]).read_text())
        assert state['phase']=='bound' and len(state['successors'])==1,state
        assert state['adoption']!=before_generation
        assert not (target/'runtime/core-update/in-progress.json').exists()
        assert (target/p.LEAF).read_bytes()==expected_leaf
        accepted=p.accept_publication(target,trusted_leaf=expected_leaf)
        assert accepted is not None
        print(json.dumps({'case':case,'refused':False,'status':record['status']}))
""",
        management,
        case,
        timeout=300,
    )
    assert result["case"] == case
    assert result["refused"] is (
        case not in {"missing", "local", "unchanged-local", "public-cli"}
    )


@pytest.mark.parametrize("drift", ["configuration", "owner"])
def test_real_adopted_factory_refuses_changed_selection(
    native_root: Path, drift: str
) -> None:
    root, _ = _adopted_fixture_install(native_root)
    _adopted_run(_ADOPTED_MANAGER, root)
    project = root / "runtime/fixture/project"
    if drift == "configuration":
        (root / "runtime/fixture/device.yaml").write_text(
            "schema_version: 1\nruntime:\n  metrics:\n    interval_seconds: 18\n"
        )
    else:
        (project / ".pf/process-forge.yaml").write_text(
            "project:\n  id: another-owner\n"
        )
    result = subprocess.run(
        [sys.executable, "-B", "-c", _ADOPTED_CHILD, str(root), "refused"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "execution_activity_unknown" in result.stderr
    assert not (project / ".pf/data/storage-identities.json").exists()
    assert not (project / ".pf/runtime/events/events.sqlite3").exists()


def test_real_updater_rejected_plan_does_not_publish_pending(native_root: Path) -> None:
    root, _ = _adopted_fixture_install(native_root)
    _adopted_run(_ADOPTED_MANAGER, root)
    build = _adopted_publication("1.3.0-alpha7")
    payload = dict(build.payload)
    payload["docs/new-owned.txt"] = b"accepted new bytes"
    build = p.build_publication(
        payload, version="1.3.0-alpha7", source={}, generated_at="fixture"
    )
    target = root / "docs/new-owned.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"unowned collision")
    archive = root / "runtime/fixture-release.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, raw in {**build.payload, p.MANIFEST: build.manifest}.items():
            bundle.writestr(name, raw)
    baseline = (root / "runtime/managed-ingress/baseline.json").read_bytes()
    head = (root / "runtime/managed-ingress/adoption.json").read_bytes()
    epoch = (root / "runtime/native-control/epoch").read_bytes()
    result = subprocess.run(
        [sys.executable, "-B", "-c", _ADOPTED_UPDATE, str(root), str(archive)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0 and "plan_blocked" in result.stderr
    assert (root / "runtime/managed-ingress/baseline.json").read_bytes() == baseline
    assert (root / "runtime/managed-ingress/adoption.json").read_bytes() == head
    assert (root / "runtime/native-control/epoch").read_bytes() == epoch
    assert not (root / "runtime/core-update").exists()


_ADOPTED_FRESH_CRASH = (
    _ADOPTED_PREAMBLE
    + r"""
entry=p.bootstrap_entry(root,trusted_leaf=leaf)
from processforge_core.composition import build_configuration_provider,build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider
from processforge_core.executions.composition import _initialize_fresh_execution_storage
from processforge_core.maintenance import journal_scan
import os
project=root/'runtime/fixture/project';device=root/'runtime/fixture/device.yaml'
provider=build_configuration_provider(project_root=project,device_config_path=device)
config=ConfigurationProvider.pinned(provider.snapshot().config)
host=build_storage_migration_host(project_root=project,workplace_root=None,device_config_path=device,configuration=config)
write=journal_scan._exclusive_bytes
def crash_before_binding(path,raw):
    if path.name=='execution-storage.json': os._exit(0)
    return write(path,raw)
journal_scan._exclusive_bytes=crash_before_binding
with host.service._native_operation(host.context,None):
    with host.service.admission.maintenance(project,None):
        assert host.service.safety(host.context).state=='proven'
        _initialize_fresh_execution_storage(project,None,configuration=config)
raise AssertionError('crash hook not reached')
"""
)


def test_real_adopted_first_write_repairs_marker_before_binding(
    native_root: Path,
) -> None:
    root, _ = _adopted_fixture_install(native_root)
    _adopted_run(_ADOPTED_MANAGER, root)
    crash = subprocess.run(
        [sys.executable, "-B", "-c", _ADOPTED_FRESH_CRASH, str(root)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert crash.returncode == 0, crash.stderr
    flow = root / "runtime/fixture/project/.pf"
    marker = json.loads(
        (flow / "maintenance/execution-initialization.json").read_text()
    )
    assert marker["state"] == "pending"
    assert not (flow / "data/execution-storage.json").exists()
    repaired = _adopted_run(_ADOPTED_CHILD, root, "repair")
    assert repaired["authority"] == "sql"
    assert (
        json.loads((flow / "data/execution-storage.json").read_text())
        == marker["binding"]
    )
    assert (
        json.loads((flow / "maintenance/execution-initialization.json").read_text())[
            "state"
        ]
        == "ready"
    )


_ADOPTED_COLLECT = (
    _ADOPTED_PREAMBLE
    + r"""
entry=p.bootstrap_entry(root,trusted_leaf=leaf)
from processforge_core.composition import build_configuration_provider
from processforge_core.configuration import ConfigurationProvider
from processforge_core.project.configuration_inputs import configuration_operation
from unittest.mock import patch
from argparse import Namespace
import contextlib,io
import processforge as cli
project=root/'runtime/fixture/project';device=root/'runtime/fixture/device.yaml'
provider=build_configuration_provider(project_root=project,device_config_path=device)
config=ConfigurationProvider.pinned(provider.snapshot().config)
# Named collection-policy seam only. Proof, factory, admission and migration are real.
with patch.object(type(cli._worker_assignment_service),'load',return_value={'id':'fixture-task','run_id':'fixture-run'}), patch.object(cli,'_collect_worker_run_locked',return_value=0):
    with configuration_operation(project,None,device_config_path=device,configuration=config):
        with contextlib.redirect_stdout(io.StringIO()):
            code=cli.command_worker_run_collect(Namespace(project_root=str(project),task='fixture-task'))
assert code==0
binding=json.loads((project/'.pf/data/execution-storage.json').read_text())
print(json.dumps({'binding':binding,'generation':p.ManagedEnrollmentProducer(root,leaf)._state()['adoption']}))
"""
)


def test_real_adopted_collect_callback_migrates_after_lifecycle_unlock(
    native_root: Path,
) -> None:
    root, _ = _adopted_fixture_install(native_root)
    adopted = _adopted_run(_ADOPTED_MANAGER, root)
    first = _adopted_run(_ADOPTED_COLLECT, root)
    repeated = _adopted_run(_ADOPTED_COLLECT, root)
    assert first == repeated
    assert first["generation"] == adopted["generation"]


@pytest.mark.parametrize("minor", [11, 12, 13])
@pytest.mark.parametrize(
    "relative",
    [
        "tools/pf_native_control.py",
        "tools/pf_native_maintenance.py",
        "tools/prepared_executor.py",
    ],
)
def test_bootstrap_python_grammar_floor(relative: str, minor: int) -> None:
    import ast

    root = Path(__file__).resolve().parents[2]
    assert Path(p.__file__).resolve() == root / "tools/pf_native_control.py"
    # Static grammar evidence only; this does not qualify an older interpreter.
    ast.parse((root / relative).read_bytes(), feature_version=(3, minor))


@pytest.mark.parametrize("value", [None, object()])
def test_image_relative_refuses_nonpaths(value: Any) -> None:
    image = p.NativeImage.__new__(p.NativeImage)
    assert image.relative(value) is None


@pytest.mark.parametrize("raw", [b"{", b"\xff", b"[" * 1100])
def test_maintenance_document_preserves_invalid_json_refusal(raw: bytes) -> None:
    import pf_native_maintenance as maintenance

    root = Path(__file__).resolve().parents[2]
    assert (
        Path(maintenance.__file__).resolve() == root / "tools/pf_native_maintenance.py"
    )
    with pytest.raises(maintenance.Rejected, match="^invalid_json$"):
        maintenance.document(raw, 4096)


@pytest.mark.parametrize("failure", [OSError, RuntimeError, ValueError])
def test_executor_same_path_preserves_resolution_failure(
    monkeypatch: pytest.MonkeyPatch, failure: type[Exception]
) -> None:
    import prepared_executor as executor

    root = Path(__file__).resolve().parents[2]
    assert Path(executor.__file__).resolve() == root / "tools/prepared_executor.py"

    def fail(path: Path) -> Path:
        raise failure("resolution failed")

    monkeypatch.setattr(Path, "expanduser", fail)
    assert executor._same_path("left", "right") is False


@pytest.mark.parametrize("failure", [OSError, ValueError])
def test_executor_failure_receipts_remain_best_effort(
    monkeypatch: pytest.MonkeyPatch, failure: type[Exception]
) -> None:
    import prepared_executor as executor

    calls: list[str] = []

    def heartbeat(*args: Any, **kwargs: Any) -> None:
        calls.append("heartbeat")
        raise failure("heartbeat failed")

    def exited(*args: Any, **kwargs: Any) -> None:
        calls.append("exit")
        raise failure("exit failed")

    monkeypatch.setattr(executor, "write_heartbeat", heartbeat)
    monkeypatch.setattr(executor, "write_exit_contract", exited)
    executor._write_failure(
        (Path("unused-heartbeat"), Path("unused-exit")), 125, "invalid"
    )
    assert calls == ["heartbeat", "exit"]


_PORTABLE_CAPTURE = r"""
import builtins, importlib.util, io, json, os, pathlib, sys, types
root = pathlib.Path(sys.argv[1])
entry_name, fault = sys.argv[2:4]
entry_path = root / entry_name
original_io = io.open
original_open = builtins.open
original_spec = importlib.util.spec_from_file_location
original_meta = list(sys.meta_path)

class Captured(Exception):
    def __init__(self, entry):
        self.entry = entry

def trace(frame, event, arg):
    if frame.f_code.co_name != 'bootstrap_entry':
        return trace
    if event == 'call':
        module = sys.modules['pf_native_control']
        # Windows unit evidence for the POSIX *selection* and snapshot algorithm.
        # The actual POSIX no-follow syscalls are a separate host gate.
        proxy = types.SimpleNamespace(**vars(os))
        proxy.name = 'posix'
        module.os = proxy
        read = module._read_regular
        if fault == 'root_alias':
            original_image = module.NativeImage.from_publication
            def redirected_image(directory, publication):
                image = original_image(directory, publication)
                image.root = directory / 'redirected-root'
                return image
            module.NativeImage.from_publication = redirected_image
        changed = False
        def snapshot(directory, relative, limit):
            nonlocal changed
            raw = read(directory, relative, limit)
            if not changed and relative == module.MANIFEST:
                changed = True
                if fault == 'mixed':
                    target = root / 'src/fixture_core.py'
                    temporary = target.with_suffix('.replacement')
                    temporary.write_bytes(b"VALUE = 'rejected'\n")
                    os.replace(temporary, target)
                elif fault == 'pending':
                    target = root / 'runtime/managed-ingress/baseline.json'
                    target.parent.mkdir(parents=True)
                    target.write_text(json.dumps(state('pending')))
            if fault == 'replaced' and relative == 'src/fixture_core.py':
                target = root / relative
                temporary = target.with_suffix('.replacement')
                temporary.write_bytes(b"VALUE = 'rejected'\n")
                os.replace(temporary, target)
            return raw
        module._snapshot_read_regular = snapshot
    elif event == 'return' and arg is not None:
        raise Captured(arg)
    return trace

def state(phase):
    return dict(schema=1, installation='a'*32, archive='b'*64, selection={},
                sentinel={}, launches=[], phase=phase, adoption=None, replacement=None)

if fault in {'legacy', 'bound', 'updating'}:
    target = root / 'runtime/managed-ingress/baseline.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(state(fault)))

runtime_before = {
    str(path.relative_to(root)): path.read_bytes()
    for path in (root/'runtime').rglob('*') if path.is_file()
}

if fault == 'helper':
    leaf_path = root / 'tools/pf_native_control.py'
    raw = leaf_path.read_bytes()
    module = types.ModuleType('pf_native_control')
    module.__file__ = str(leaf_path)
    module._captured_source = raw
    sys.modules[module.__name__] = module
    exec(compile(raw + b'\nSHADOW = True\n', str(leaf_path), 'exec', dont_inherit=True), module.__dict__)

raw_entry = entry_path.read_bytes()
if fault == 'caller':
    raw_entry += b'\nSHADOW = True\n'
namespace = {'__file__': str(entry_path), '__name__': 'portable_fixture_entry'}
if entry_name == 'src/processforge_core/__init__.py':
    spec = original_spec('processforge_core', entry_path, submodule_search_locations=[str(entry_path.parent)])
    core = importlib.util.module_from_spec(spec)
    spec._initializing = True
    sys.modules['processforge_core'] = core
    namespace = core.__dict__
sys.settrace(trace)
try:
    exec(compile(raw_entry, str(entry_path), 'exec', dont_inherit=True), namespace)
    raise AssertionError('capture did not run')
except Captured as result:
    sys.settrace(None)
    entry = result.entry
    module = sys.modules['pf_native_control']
    assert entry is module.current_entry()
    assert entry.control is None and entry.publication is not None
    assert entry.image is not None and entry.image._active
    assert dict(entry.publication.payload) == {
        row['relative_path']: entry.image.read(row['relative_path'])
        for row in module.parse_manifest(entry.publication.manifest)['files']
    }
    assert entry.storage_safety(object()) == ('unknown', '', ('managed_exclusion_not_held',))
    assert module.supports_owned_execution() is False
    with entry.operation():
        assert module._CONTROL_LEASE.get() is None
    try:
        module.replace_core(entry, root/'absent.zip', lambda: (_ for _ in ()).throw(AssertionError('planner called')), workplace_root=None)
    except module.NativeControlError:
        pass
    else:
        raise AssertionError('snapshot granted update authority')
    # No disk fallback after capture, including direct alias and resources.
    with module._PHYSICAL_OPEN(root/'src/fixture_core.py', 'wb') as stream:
        stream.write(b"raise AssertionError('disk fallback')\n")
    with module._PHYSICAL_OPEN(root/'resources/data.txt', 'wb') as stream:
        stream.write(b'drift')
    spec = importlib.util.spec_from_file_location('portable_alias', root/'src/fixture_core.py')
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    assert loaded.VALUE == 'accepted'
    assert (root/'resources/data.txt').read_bytes() == b'resource\n'
    assert {
        str(path.relative_to(root)): path.read_bytes()
        for path in (root/'runtime').rglob('*') if path.is_file()
    } == runtime_before
    print(json.dumps({'accepted': True, 'control': False, 'native': False}))
finally:
    sys.settrace(None)
    builtins.open, io.open = original_open, original_io
    importlib.util.spec_from_file_location = original_spec
    sys.meta_path[:] = original_meta
"""


def _portable_candidate() -> Any:
    root = Path(__file__).resolve().parents[2]
    source = Path(os.environ["W332_SOURCE"])
    assert Path(p.__file__).resolve() == root / p.LEAF
    return build(
        {
            p.LEAF: (root / p.LEAF).read_bytes(),
            p.INVENTORY: b"source inventory\n",
            "tools/processforge.py": (source / "tools/processforge.py").read_bytes(),
            "tools/prepared_executor.py": (
                root / "tools/prepared_executor.py"
            ).read_bytes(),
            "src/processforge_core/__init__.py": (
                source / "src/processforge_core/__init__.py"
            ).read_bytes(),
            "src/fixture_core.py": b"VALUE = 'accepted'\n",
            "resources/data.txt": b"resource\n",
            "VERSION": b"1.3.0-beta1\n",
        }
    )


@pytest.mark.parametrize(
    "entry_name",
    [
        "tools/processforge.py",
        "tools/prepared_executor.py",
        "src/processforge_core/__init__.py",
    ],
)
@pytest.mark.parametrize(
    "fault", ["none", "legacy", "caller", "helper", "mixed", "replaced", "root_alias"]
)
def test_portable_snapshot_binds_actual_whole_entries(
    entry_name: str, fault: str
) -> None:
    candidate = _portable_candidate()
    root = fixture_root(candidate)
    completed = subprocess.run(
        [sys.executable, "-B", "-c", _PORTABLE_CAPTURE, str(root), entry_name, fault],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    if fault in {"none", "legacy", "replaced"}:
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout) == {
            "accepted": True,
            "control": False,
            "native": False,
        }
    else:
        assert completed.returncode != 0
        assert "execution_activity_unknown" in completed.stderr or (
            fault == "mixed" and "payload_drift" in completed.stderr
        )
        assert completed.stdout == ""
    if fault != "legacy":
        assert not (root / "runtime").exists()


@pytest.mark.parametrize("fault", ["pending", "bound", "updating", "guard", "epoch"])
def test_portable_snapshot_cannot_bypass_control_state(fault: str) -> None:
    candidate = _portable_candidate()
    root = fixture_root(candidate)
    if fault in {"guard", "epoch"}:
        name = "installation.guard" if fault == "guard" else "epoch"
        target = root / "runtime/native-control" / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b"unqualified")
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            _PORTABLE_CAPTURE,
            str(root),
            "tools/prepared_executor.py",
            fault,
        ],
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "execution_activity_unknown" in completed.stderr


@pytest.mark.parametrize(
    "fault", ["none", "atime", "alias", "hardlink", "changing", "limit"]
)
def test_portable_snapshot_reader_retains_nofollow_descriptors(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import io
    import stat
    from types import SimpleNamespace

    # Deterministic syscall model, not POSIX host acceptance on Windows.
    opened: list[tuple[str, int, int | None]] = []
    closed: list[int] = []

    def open_descriptor(name: str, flags: int, *, dir_fd: int | None = None) -> int:
        assert flags & 0x100
        if fault == "alias" and name == "src":
            raise OSError("nofollow alias refused")
        opened.append((name, flags, dir_fd))
        return len(opened)

    class Stream(io.BytesIO):
        def fileno(self) -> int:
            return len(opened)

        def close(self) -> None:
            closed.append(self.fileno())
            super().close()

    stats = 0

    def fstat(descriptor: int) -> os.stat_result:
        nonlocal stats
        stats += 1
        return os.stat_result(
            (
                stat.S_IFREG | 0o600,
                100,
                1,
                2 if fault == "hardlink" else 1,
                0,
                0,
                stats if fault == "changing" else 5,
                stats if fault == "atime" else 0,
                0,
                0,
            )
        )

    monkeypatch.setattr(
        p,
        "os",
        SimpleNamespace(
            O_RDONLY=0,
            O_DIRECTORY=0x200,
            O_NOFOLLOW=0x100,
            O_NONBLOCK=0x400,
            open=open_descriptor,
            close=closed.append,
            fdopen=lambda descriptor, mode: Stream(b"bytes"),
            fstat=fstat,
        ),
    )
    root = Path(os.environ["W3_FIXTURE_ROOT"]).absolute()
    if fault in {"none", "atime"}:
        assert p._snapshot_read_regular(root, "src/file.py", 5) == b"bytes"
    else:
        with pytest.raises((p.Refusal, OSError)):
            p._snapshot_read_regular(root, "src/file.py", 4 if fault == "limit" else 5)
    assert sorted(closed) == list(range(1, len(opened) + 1))
    assert all(flags & 0x200 for _, flags, _ in opened[:-1])
    if fault != "alias":
        assert opened[-1][1] & 0x400
