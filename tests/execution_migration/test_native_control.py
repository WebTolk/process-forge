"""Real no-model Windows process-tree qualification at the native boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

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
