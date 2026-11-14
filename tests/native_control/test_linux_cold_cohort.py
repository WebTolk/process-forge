"""Real Linux controlled-cohort checks, not legacy deployment qualification."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pf_linux_cold_controller as cold
import pf_native_control as native
import pytest

_LINUX_ROOT = (
    sys.platform.startswith("linux") and getattr(os, "geteuid", lambda: -1)() == 0
)
_REAL = pytest.mark.skipif(
    not _LINUX_ROOT, reason="Real root-owned Linux cohort required"
)
_WORKER = r"""
import array, ctypes, errno, importlib.util, json, os, socket, subprocess, sys, time
from pathlib import Path
mode, payload = sys.argv[1:]
payload = Path(payload)
if mode == "echo":
    sys.stdout.buffer.write(sys.stdin.buffer.read())
elif mode == "policy":
    status = Path("/proc/self/status").read_text()
    facts = {k:v.strip() for k,v in (line.split(":",1) for line in status.splitlines())
             if k in {"Uid","Gid","Groups","CapInh","CapPrm","CapEff","CapBnd","CapAmb","NoNewPrivs","Seccomp"}}
    a,b=socket.socketpair()
    fd=os.open("/dev/null",os.O_WRONLY)
    try:
        a.sendmsg([b"x"],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array("i",[fd]))])
    except PermissionError:
        facts["export"]="denied"
    else:
        facts["export"]="ALLOWED"
    os.close(fd);a.close();b.close()
    libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
    ctypes.set_errno(0)
    result=libc.syscall(ctypes.c_long(0x40000001),ctypes.c_long(-1),ctypes.c_long(0),ctypes.c_long(0))
    facts["x32_refused"]=result == -1 and ctypes.get_errno()==errno.EPERM
    try:
        Path("/sys/fs/cgroup/cgroup.procs").write_text(str(os.getpid()))
    except PermissionError:
        facts["migration"]="denied"
    else:
        facts["migration"]="ALLOWED"
    print(json.dumps(facts))
elif mode == "writer":
    fd=os.open(payload/"writes",os.O_WRONLY|os.O_APPEND)
    child=os.fork()
    if child==0:
        os.setsid()
        while True:
            os.write(fd,b"descendant\n")
            time.sleep(0.01)
    else:
        os.write(fd,b"parent\n")
elif mode == "hang":
    with (payload/"writes").open("ab") as stream:
        stream.write(b"once\n");stream.flush()
    time.sleep(30)
elif mode == "owned":
    spec=importlib.util.spec_from_file_location("owned_fixture",payload/"owned.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    process=module.spawn([sys.executable,"-B","-c","print('owned child')"],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    job=process.native_job
    try:
        output,error=process.communicate(timeout=5)
        assert process.returncode==0 and output==b"owned child\n" and not error
        assert job.active()==0
        print("owned namespace passed")
    finally:
        if job.active():
            job.stop(deadline=time.monotonic()+5)
        job.close()
"""


def _wait(check: Any) -> None:
    deadline = time.monotonic() + 5
    while not check():
        assert time.monotonic() < deadline, "fixture observation timed out"
        time.sleep(0.01)


class Case:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.control_root = root / "control"
        self.control_root.mkdir(mode=0o700)
        self.payload = root / "payload"
        self.payload.mkdir(mode=0o755)
        (self.payload / "worker.py").write_text(_WORKER, encoding="utf-8")
        (self.payload / "worker.py").chmod(0o644)
        shutil.copyfile(
            Path(__file__).resolve().parents[2] / "tools/pf_linux_native_control.py",
            self.payload / "owned.py",
        )
        (self.payload / "owned.py").chmod(0o644)
        (self.payload / "writes").touch(mode=0o666)
        (self.payload / "writes").chmod(0o666)
        guard, epoch = self.control_root / "guard", self.control_root / "epoch"
        guard.write_bytes(b"0")
        epoch.write_text("cohort-fixture", encoding="ascii")
        guard.chmod(0o600)
        epoch.chmod(0o600)
        self.control = native.NativeControl(guard, epoch, "cohort-fixture")
        self.cohorts: list[cold.ControlledCohort] = []

    def provision(
        self, *, role: str = "legacy", hang_timeout: float = 0.2
    ) -> cold.ControlledCohort:
        directory = self.control_root / ("cohort-" + str(len(self.cohorts)))
        directory.mkdir(mode=0o700)
        routes = {
            name: {
                "argv": [
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "-B",
                    str(self.payload / "worker.py"),
                    name,
                    str(self.payload),
                ],
                "timeout": hang_timeout if name == "hang" else 5,
            }
            for name in ("echo", "policy", "writer", "hang", "owned")
        }
        principal = {"legacy": 62017, "native": 62019, "successor": 62018}[role]
        cohort = cold.ControlledCohort.provision(
            directory,
            self.control,
            uid=principal,
            gid=principal,
            role=role,
            profile_sha256="sha256:" + "a" * 64,
            routes=routes,
        )
        self.cohorts.append(cohort)
        return cohort


@contextmanager
def _case() -> Iterator[Case]:
    # Consumer fixture on local Linux storage; no installed PF tree is touched.
    # CI's ambient TMPDIR can have an unprivileged owner; this profile requires
    # a protected root-owned ancestor chain on the local Linux filesystem.
    root = Path(tempfile.mkdtemp(prefix="pf-cohort-consumer-", dir="/tmp"))
    root.chmod(0o711)
    case = Case(root)
    try:
        yield case
    finally:
        for cohort in reversed(case.cohorts):
            with case.control.exclusive():
                # A separate fixture controller may have committed newer state.
                current = cold.ControlledCohort.reopen(cohort.directory, case.control)
                assert current.state["group_identity"] == cohort.state["group_identity"]
                current.retire(deadline=time.monotonic() + 5)
                assert current.events()["populated"] == 0
            group = cohort.group
            expected = tuple(cohort.state["group_identity"])
            cohort.close()
            current.close()
            assert group.parent == Path("/sys/fs/cgroup")
            assert cold._identity(group) == expected
            group.rmdir()
        assert root.parent == Path("/tmp")
        assert root.name.startswith("pf-cohort-consumer-")
        shutil.rmtree(root)


@_REAL
@pytest.mark.parametrize("role", ["legacy", "native", "successor"])
def test_genesis_fixed_route_and_inherited_policy(role: str) -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision(role=role)
        cohort.start()
        assert cohort.state["phase"] == "active"
        supplied = "Кузня \u2028 \U0001f527".encode()
        reply = cohort.run("echo", supplied)
        assert reply["exit_code"] == 0 and reply["stdout"] == supplied
        assert reply["stderr"] == b""
        facts = json.loads(cohort.run("policy")["stdout"])
        for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
            assert int(facts[name], 16) == 0
        assert facts["NoNewPrivs"] == "1" and facts["Seccomp"] == "2"
        assert facts["export"] == facts["migration"] == "denied"
        assert facts["x32_refused"]
        expected = {"legacy": 62017, "native": 62019, "successor": 62018}[role]
        assert [int(x) for x in facts["Uid"].split()] == [expected] * 4
        assert facts["Groups"] == ""
        owned = cohort.run("owned")
        assert owned["exit_code"] == 0
        assert owned["stdout"] == b"owned namespace passed\n"
        assert not owned["stderr"]
        with pytest.raises(cold.Refused):
            cohort.run("unregistered")
        assert cohort.state["pending"] is None


@_REAL
def test_retirement_closes_detached_writer_with_open_descriptor() -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        cohort.start()
        assert cohort.run("writer")["exit_code"] == 0
        writes = case.payload / "writes"
        _wait(lambda: b"descendant" in writes.read_bytes())
        case.payload.chmod(0o700)
        before = writes.stat().st_size
        _wait(lambda: writes.stat().st_size > before)
        cohort.retire(deadline=time.monotonic() + 5)
        after = writes.stat().st_size
        time.sleep(0.05)
        assert writes.stat().st_size == after
        assert cohort.events() == {"populated": 0, "frozen": 1}
        with pytest.raises(cold.Refused):
            cohort.run("echo")


@_REAL
def test_unknown_mutation_is_not_replayed_or_cleared_by_retirement() -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        cohort.start()
        with pytest.raises(cold.Refused):
            cohort.run("hang")
        pending = dict(cohort.state["pending"])
        assert (case.payload / "writes").read_bytes() == b"once\n"
        with pytest.raises(cold.Refused):
            cohort.run("hang")
        cohort.retire(deadline=time.monotonic() + 5)
        assert cohort.state["pending"] == pending
        assert cohort.state["last_result"] is None
        assert (case.payload / "writes").read_bytes() == b"once\n"


@_REAL
@pytest.mark.parametrize(
    "stage", ["launch_reserved", "carrier_spawned", "ready", "genesis_bound"]
)
def test_interrupted_genesis_cannot_go_again_or_open_target(stage: str) -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        library = ctypes.CDLL(None, use_errno=True)
        descriptor = library.inotify_init1(getattr(os, "O_NONBLOCK"))
        assert descriptor >= 0
        try:
            watch = library.inotify_add_watch(
                descriptor, os.fsencode(case.payload / "worker.py"), 0x20
            )
            assert watch >= 0

            def interrupt(current: str) -> None:
                if current == stage:
                    raise RuntimeError("fixture controller interruption")

            with pytest.raises(RuntimeError):
                cohort.start(checkpoint=interrupt)
            with pytest.raises(BlockingIOError):
                os.read(descriptor, 4096)
            with pytest.raises(cold.Refused):
                cohort.start()
            cohort.retire(deadline=time.monotonic() + 5)
            assert cohort.events()["populated"] == 0
            assert (case.payload / "writes").read_bytes() == b""
        finally:
            os.close(descriptor)


@_REAL
def test_gate_required_and_changed_boot_refused_without_relabel() -> None:
    with _case() as case:
        with case.control.exclusive():
            cohort = case.provision()
        with pytest.raises(cold.Refused):
            cohort.start()
        with case.control.exclusive():
            original = json.loads((cohort.directory / "cohort.json").read_bytes())
            changed = json.loads(json.dumps(original))
            changed["platform"]["boot"] = "fixture-other-boot"
            cold._atomic(cohort.directory / "cohort.json", changed)
            try:
                with pytest.raises(cold.Refused):
                    cold.ControlledCohort.reopen(cohort.directory, case.control)
                assert cold._read(cohort.directory / "cohort.json") == changed
            finally:
                # Restore only this negative fixture's deliberate state mutation.
                cold._atomic(cohort.directory / "cohort.json", original)


_CONTROLLER = r"""
import sys,time
from pathlib import Path
import pf_linux_cold_controller as cold
import pf_native_control as native
directory, control_root, marker, stage=sys.argv[1:]
directory,control_root,marker=Path(directory),Path(control_root),Path(marker)
gate=native.NativeControl(control_root/"guard",control_root/"epoch","cohort-fixture")
with gate.exclusive():
    cohort=cold.ControlledCohort.reopen(directory,gate)
    def checkpoint(current):
        if current==stage:
            marker.write_text(current)
            time.sleep(30)
    cohort.start(checkpoint=checkpoint)
    if stage=="active-native":
        cohort.run("hang")
"""


_SHARED = r"""
import sys,time
from pathlib import Path
import pf_linux_cold_controller as cold
import pf_native_control as native
directory,root,ready,go=sys.argv[1:]
directory,root,ready,go=map(Path,(directory,root,ready,go))
gate=native.NativeControl(root/"guard",root/"epoch","cohort-fixture")
with gate.operation(deadline=time.monotonic()+10):
    assert native._native_life_held(gate)
    ready.write_text("shared")
    deadline=time.monotonic()+5
    while not go.exists():
        assert time.monotonic()<deadline
        time.sleep(0.01)
    try:
        cold.ControlledCohort.reopen(directory,gate)
    except cold.Refused:
        print("shared refused")
    else:
        raise AssertionError("shared controller was accepted")
"""


@_REAL
def test_two_shared_controllers_cannot_mutate_genesis() -> None:
    with _case() as case:
        with case.control.exclusive():
            cohort = case.provision()
        before = (cohort.directory / "cohort.json").read_bytes()
        children: list[tuple[subprocess.Popen[bytes], int]] = []
        go = case.control_root / "shared-go"
        try:
            for index in range(2):
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-B",
                        "-c",
                        _SHARED,
                        str(cohort.directory),
                        str(case.control_root),
                        str(case.control_root / f"ready-{index}"),
                        str(go),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                )
                children.append((process, getattr(os, "pidfd_open")(process.pid)))
            _wait(
                lambda: all(
                    (case.control_root / f"ready-{i}").is_file() for i in range(2)
                )
            )
            go.write_text("proceed", encoding="ascii")
            for process, _descriptor in children:
                stdout, stderr = process.communicate(timeout=5)
                assert process.returncode == 0
                assert stdout == b"shared refused\n" and not stderr
            assert (cohort.directory / "cohort.json").read_bytes() == before
            with case.control.exclusive():
                assert cohort.events()["populated"] == 0
                cohort.start()
                assert (
                    cohort.run("echo", b"only exclusive")["stdout"] == b"only exclusive"
                )
        finally:
            for process, descriptor in children:
                if process.poll() is None:
                    getattr(signal, "pidfd_send_signal")(
                        descriptor, getattr(signal, "SIGKILL")
                    )
                    process.communicate(timeout=5)
                os.close(descriptor)


_OTHER_GATE = r"""
import sys
from pathlib import Path
import pf_linux_cold_controller as cold
import pf_native_control as native
directory,root=map(Path,sys.argv[1:])
other=native.NativeControl(root/"other.guard",root/"other.epoch","cohort-fixture")
with other.exclusive():
    try:
        cold.ControlledCohort.reopen(directory,other)
    except cold.Refused as error:
        assert error.reason=="cohort_gate_changed",error.reason
        print("other gate refused")
    else:
        raise AssertionError("different gate was accepted")
"""


@_REAL
def test_different_gate_refused_while_original_exclusive_owner_is_live() -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        cohort.start()
        before = (cohort.directory / "cohort.json").read_bytes()
        (case.control_root / "other.guard").write_bytes(b"0")
        (case.control_root / "other.epoch").write_bytes(b"cohort-fixture")
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                _OTHER_GATE,
                str(cohort.directory),
                str(case.control_root),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
            check=True,
        )
        assert result.stdout == b"other gate refused\n" and not result.stderr
        assert (cohort.directory / "cohort.json").read_bytes() == before
        assert cohort.events()["populated"] == 1
        assert cohort.run("echo", b"original owner")["stdout"] == b"original owner"


@_REAL
def test_stale_controller_cannot_overwrite_unknown_result() -> None:
    with _case() as case:
        with case.control.exclusive():
            original = case.provision()
            stale = cold.ControlledCohort.reopen(original.directory, case.control)
            original.start()
            with pytest.raises(cold.Refused):
                original.run("hang")
        try:
            before = (original.directory / "cohort.json").read_bytes()
            with case.control.exclusive():
                with pytest.raises(cold.Refused):
                    stale.start()
                with pytest.raises(cold.Refused):
                    stale.retire(deadline=time.monotonic() + 5)
                assert (original.directory / "cohort.json").read_bytes() == before
                assert original.state["pending"] is not None
        finally:
            stale.close()


@_REAL
@pytest.mark.parametrize(
    "stage", ["carrier_spawned", "genesis_bound", "go", "active-native"]
)
def test_real_controller_death_keeps_actors_reconcilable_and_no_replay(
    stage: str,
) -> None:
    with _case() as case:
        with case.control.exclusive():
            cohort = case.provision(role="native", hang_timeout=120)
        marker = case.control_root / "checkpoint"
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                _CONTROLLER,
                str(cohort.directory),
                str(case.control_root),
                str(marker),
                stage,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        descriptor = getattr(os, "pidfd_open")(process.pid)
        try:
            if stage == "active-native":
                _wait(lambda: (case.payload / "writes").read_bytes() == b"once\n")
            else:
                _wait(marker.is_file)
            getattr(signal, "pidfd_send_signal")(descriptor, getattr(signal, "SIGKILL"))
            stdout, stderr = process.communicate(timeout=5)
            assert process.returncode == -getattr(signal, "SIGKILL")
            assert not stdout and not stderr
            with case.control.exclusive():
                recovered = cold.ControlledCohort.reopen(cohort.directory, case.control)
                try:
                    pending = recovered.state["pending"]
                    if stage == "active-native":
                        assert pending is not None
                        assert pending["controller_pid"] == process.pid
                        assert recovered.events()["populated"] == 1
                    with pytest.raises(cold.Refused):
                        recovered.start()
                    with pytest.raises(cold.Refused):
                        recovered.run("hang")
                    recovered.retire(deadline=time.monotonic() + 5)
                    assert recovered.events()["populated"] == 0
                    assert recovered.state["pending"] == pending
                    assert recovered.state["last_result"] is None
                finally:
                    recovered.close()
        finally:
            if process.poll() is None:
                getattr(signal, "pidfd_send_signal")(
                    descriptor, getattr(signal, "SIGKILL")
                )
                process.communicate(timeout=5)
            os.close(descriptor)


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="Non-Linux refusal only")
def test_nonlinux_host_never_enters_cohort_provisioning() -> None:
    with pytest.raises(cold.Refused):
        cold._platform()
