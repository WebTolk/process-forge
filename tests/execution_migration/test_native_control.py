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
    runtime.save = write
    server = SimpleNamespace(server_address=("127.0.0.1", 0), serve_forever=idle)
    with (
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
    runtime.stop_event = SimpleNamespace(is_set=lambda: False, wait=wait)
    runtime.reload_configuration = lambda: None
    runtime.save = save
    with (
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

    from pf_runtime import service

    runtime = object.__new__(service.RuntimeProcess)
    runtime.stop_event = threading.Event()
    closed = threading.Event()
    runtime.httpd = SimpleNamespace(shutdown=closed.set)
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
    kernel._operation = lambda: (SimpleNamespace(records=records), True)
    with patch.object(
        p, "current_entry", return_value=SimpleNamespace(operation=operation)
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


def test_actual_trusted_entry_captures_leaf_core_aliases_and_resources(
    native_root: Path,
) -> None:
    import processforge as cli

    assert p.__file__ is not None
    candidate = build(
        {
            p.LEAF: Path(p.__file__).read_bytes(),
            p.INVENTORY: b"source inventory\n",
            "src/fixture_core.py": b"VALUE = 'accepted'\n",
            "docs/data.txt": b"accepted resource\n",
            "VERSION": b"1.3.0-alpha6\n",
        }
    )
    for name, raw in candidate.payload.items():
        path = native_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (native_root / p.MANIFEST).write_bytes(candidate.manifest)
    for name in (p.LEAF, "src/fixture_core.py"):
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
    preamble = (
        Path(cli.__file__).read_text(encoding="utf-8").split("if TYPE_CHECKING:", 1)[0]
    )
    entry = native_root / "tools/fixture-entry.py"
    entry.write_text(
        preamble
        + """
sys.path.insert(0, str(_native_root / "src"))
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
        timeout=15,
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
