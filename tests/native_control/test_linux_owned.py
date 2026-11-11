"""Real Linux namespace lifetime, exact ownership and pre-target launch barriers."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pf_linux_native_control as linux
import pf_native_control as native
import pytest

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux PID namespace backend"
)


def wait_file(path: Path) -> None:
    deadline = time.monotonic() + 10
    while not path.exists():
        assert time.monotonic() < deadline, "target did not publish"
        time.sleep(0.01)


def absent(pid: int) -> bool:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        return raw[raw.rindex(")") + 2 :].split()[0] in {"Z", "X"}
    except FileNotFoundError:
        return True


def test_success_reopens_exact_persisted_tree(tmp_path: Path) -> None:
    receipt = tmp_path / "native.json"
    identity = {"run_id": "run", "task_id": "task", "attempt": 1}
    process = native.spawn_owned(
        [sys.executable, "-c", "pass"], receipt_path=receipt, identity=identity
    )
    job = getattr(process, "native_job")
    try:
        assert process.wait(timeout=10) == 0
        assert job.active() == 0
        facts = json.loads(receipt.read_text())
        assert facts == getattr(process, "native_facts")
        reopened = native.reopen_job(facts, pid=process.pid, identity=identity)
        assert reopened is not None
        try:
            assert reopened.active() == 0
        finally:
            reopened.close()
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


@pytest.mark.parametrize("carrier_death", [False, True])
def test_root_exit_keeps_escaped_descendant_owned(
    tmp_path: Path, carrier_death: bool
) -> None:
    marker = tmp_path / "descendant.json"
    script = """
import json, os, pathlib, sys, time
child = os.fork()
if child == 0:
    os.setsid()
    host_pid = int(pathlib.Path("/proc/self/status").read_text().split("NSpid:")[1].split()[0])
    pathlib.Path(sys.argv[1]).write_text(json.dumps({"pid": host_pid, "pgid": os.getpgrp()}))
    time.sleep(60)
os._exit(0)
"""
    process = native.spawn_owned([sys.executable, "-c", script, str(marker)])
    job = getattr(process, "native_job")
    try:
        wait_file(marker)
        child = json.loads(marker.read_text())
        assert child["pgid"] > 1
        assert process.poll() is None and job.active() > 0
        facts = getattr(process, "native_facts")
        job.close()  # Carrier retains lifetime without a controller handle.
        reopened = native.reopen_job(facts, pid=process.pid, identity={})
        assert reopened is not None
        try:
            assert reopened.active() > 0
            if carrier_death:
                process.kill()  # Retained Popen object, never a scanned PID.
            else:
                assert reopened.stop(deadline=time.monotonic() + 5)
            process.wait(timeout=5)
            deadline = time.monotonic() + 5
            while reopened.active() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert reopened.active() == 0 and absent(child["pid"])
        finally:
            reopened.stop(deadline=time.monotonic() + 5)
            reopened.close()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        job.close()


def test_controller_exit_allows_exact_restart(tmp_path: Path) -> None:
    receipt = tmp_path / "native.json"
    script = """
import os, pathlib, sys
from pf_native_control import spawn_owned
spawn_owned([sys.executable, "-c", "import time; time.sleep(60)"],
            receipt_path=pathlib.Path(sys.argv[1]), identity={"attempt": 4})
os._exit(73)
"""
    controller = subprocess.Popen([sys.executable, "-c", script, str(receipt)])
    assert controller.wait(timeout=15) == 73
    facts = json.loads(receipt.read_text())
    job = native.reopen_job(facts, pid=facts["pid"], identity={"attempt": 4})
    assert job is not None
    try:
        assert job.active() > 0
        assert job.stop(deadline=time.monotonic() + 5)
    finally:
        job.close()


def test_publication_refusal_never_executes_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "must-not-exist"
    launched: list[subprocess.Popen[bytes]] = []
    popen = subprocess.Popen

    def capture(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = popen(*args, **kwargs)
        launched.append(process)
        return process

    def refuse(*args: Any) -> None:
        raise PermissionError("fixture publication denied")

    monkeypatch.setattr(linux.subprocess, "Popen", capture)
    monkeypatch.setattr(linux.os, "replace", refuse)
    with pytest.raises(PermissionError):
        native.spawn_owned(
            [
                sys.executable,
                "-c",
                "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()",
                str(marker),
            ],
            receipt_path=tmp_path / "native.json",
        )
    assert not marker.exists()
    assert len(launched) == 1 and launched[0].poll() is not None


def test_foreign_pid_birth_token_and_owner_refuse_without_signal(
    tmp_path: Path,
) -> None:
    process = native.spawn_owned([sys.executable, "-c", "import time; time.sleep(60)"])
    victim = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    job = getattr(process, "native_job")
    facts = getattr(process, "native_facts")
    try:
        with pytest.raises(OSError):
            native.reopen_job(facts, pid=process.pid, identity={"foreign": True})
        with pytest.raises(OSError):
            native.reopen_job({**facts, "pid": victim.pid}, pid=victim.pid, identity={})
        other_token = "a" * 32 if "a" * 32 not in facts["job_name"] else "b" * 32
        other = ":".join(
            [
                facts["job_name"].split(":")[0],
                other_token,
                *facts["job_name"].split(":")[2:],
            ]
        )
        with pytest.raises(OSError):
            native.reopen_job(
                {**facts, "job_name": other}, pid=process.pid, identity={}
            )
        assert victim.poll() is None and job.active() > 0
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()
        victim.kill()
        victim.wait(timeout=5)


def test_denied_observation_stays_unknown_and_does_not_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prepared_executor import owned_tree_absent, signal_owned_tree

    from processforge_core.runtime.process_identity import capture_process

    process = native.spawn_owned([sys.executable, "-c", "import time; time.sleep(60)"])
    job = getattr(process, "native_job")
    try:
        identity = capture_process(process.pid, tree_id=job.name)
        assert identity is not None
        with monkeypatch.context() as patch:
            patch.setattr(
                linux, "_boot", lambda: (_ for _ in ()).throw(PermissionError())
            )
            assert owned_tree_absent(identity) is None
            with pytest.raises(OSError):
                signal_owned_tree(identity)
        assert job.active() > 0 and process.poll() is None
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()


def test_controller_death_before_go_does_not_execute_target(tmp_path: Path) -> None:
    proof, receipt, marker = (
        tmp_path / name for name in ("proof.json", "native.json", "target")
    )
    script = """
import json, os, pathlib, sys
import pf_linux_native_control as linux
from pf_native_control import spawn_owned
original = linux.reopen
def capture(facts, **kwargs):
    job = original(facts, **kwargs)
    pathlib.Path(sys.argv[1]).write_text(json.dumps(facts))
    return job
linux.reopen = capture
linux.os.replace = lambda *args: os._exit(73)
spawn_owned([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", sys.argv[3]],
            receipt_path=pathlib.Path(sys.argv[2]))
"""
    controller = subprocess.Popen(
        [sys.executable, "-c", script, str(proof), str(receipt), str(marker)]
    )
    assert controller.wait(timeout=15) == 73
    facts = json.loads(proof.read_text())
    deadline = time.monotonic() + 8
    while True:
        try:
            job = native.reopen_job(facts, pid=facts["pid"], identity={})
            assert job is not None
            try:
                done = job.active() == 0
            finally:
                job.close()
        except OSError:
            done = False  # Transient unreadability is not proof of absence.
        if done:
            break
        assert time.monotonic() < deadline
        time.sleep(0.02)
    assert not marker.exists() and not receipt.exists()


@pytest.mark.skipif(
    platform.machine() != "x86_64",
    reason="Seccomp syscall fixture uses x86_64 unshare number",
)
def test_kernel_denied_namespace_refuses_before_target(tmp_path: Path) -> None:
    marker = tmp_path / "target"
    script = """
import ctypes, pathlib, sys
import pf_linux_native_control as linux
class Filter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]
class Program(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filters", ctypes.POINTER(Filter))]
filters = (Filter * 4)(Filter(0x20, 0, 0, 0), Filter(0x15, 0, 1, 272), Filter(0x06, 0, 0, 0x50001), Filter(0x06, 0, 0, 0x7fff0000))
program = Program(4, filters)
libc = ctypes.CDLL(None)
assert libc.prctl(38, 1, 0, 0, 0) == 0
assert libc.prctl(22, 2, ctypes.byref(program), 0, 0) == 0
try:
    linux.spawn([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", sys.argv[1]])
except linux.LinuxControlError as error:
    assert "linux_user_pid_namespace_unavailable" in error.reason, error
    print(error.code, error.reason)
else:
    raise AssertionError("kernel denial launched target")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(marker)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "execution_activity_unknown" in result.stdout and not marker.exists()


def test_wrapper_rejects_token_mismatch_before_receipts_or_target(
    tmp_path: Path,
) -> None:
    script = """
import os, pathlib, sys
from prepared_executor import ExecutionReceipts
root = pathlib.Path(sys.argv[1])
document = {"identity": {"project_id": "p", "run_id": "r", "assignment_id": "t", "attempt": 1}}
ExecutionReceipts(dict(os.environ), document, root / "heartbeat.json", root / "exit.json")
(root / "target").touch()
"""
    environment = dict(os.environ)
    environment.update(
        PF_EXECUTION_PROJECT_ID="p",
        PF_EXECUTION_RUN_ID="r",
        PF_EXECUTION_TASK_ID="t",
        PF_EXECUTION_ATTEMPT="1",
        PF_EXECUTION_LAUNCH_TOKEN="b" * 32,
    )
    with (tmp_path / "stderr").open("wb") as stderr:
        process = native.spawn_owned(
            [sys.executable, "-c", script, str(tmp_path)],
            token="a" * 32,
            env=environment,
            stderr=stderr,
        )
        job = getattr(process, "native_job")
        try:
            assert process.wait(timeout=10) == 1
            assert job.active() == 0
        finally:
            job.stop(deadline=time.monotonic() + 5)
            process.wait(timeout=5)
            job.close()
    assert "execution_identity_conflict" in (tmp_path / "stderr").read_text()
    assert (
        not (tmp_path / "process.json").exists() and not (tmp_path / "target").exists()
    )


@pytest.mark.parametrize("refused", [False, True])
def test_target_preload_runs_only_inside_committed_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, refused: bool
) -> None:
    marker = tmp_path / "preload.log"
    source, library = tmp_path / "preload.c", tmp_path / "preload.so"
    source.write_text(
        r"""
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
__attribute__((constructor)) static void observe(void) {
    char ns[256];
    ssize_t size = readlink("/proc/self/ns/pid", ns, sizeof(ns) - 1);
    if (size < 0) return;
    ns[size] = 0;
    int fd = open(MARKER, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd >= 0) { dprintf(fd, "%s\n", ns); close(fd); }
}
""".replace("MARKER", json.dumps(str(marker)))
    )
    subprocess.run(
        ["cc", "-shared", "-fPIC", str(source), "-o", str(library)],
        check=True,
        capture_output=True,
    )
    environment = {**os.environ, "LD_PRELOAD": str(library)}
    if refused:

        def refuse(*args: Any) -> None:
            raise PermissionError("fixture publication denied")

        monkeypatch.setattr(linux.os, "replace", refuse)
        with pytest.raises(PermissionError):
            native.spawn_owned(
                [sys.executable, "-c", "pass"],
                env=environment,
                receipt_path=tmp_path / "native.json",
            )
        assert not marker.exists()
    else:
        process = native.spawn_owned([sys.executable, "-c", "pass"], env=environment)
        job = getattr(process, "native_job")
        try:
            assert process.wait(timeout=10) == 0 and job.active() == 0
            assert marker.read_text().splitlines() == [
                f"pid:[{job.name.split(':')[4]}]"
            ]
        finally:
            job.stop(deadline=time.monotonic() + 5)
            process.wait(timeout=5)
            job.close()
