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
elif mode in {"writer","fence-writer"}:
    target=payload/"writes" if mode=="writer" else Path(sys.stdin.buffer.read().decode())
    fd=os.open(target,os.O_WRONLY|os.O_APPEND)
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
elif mode == "rights":
    result={"uid":os.geteuid(),"gid":os.getegid(),"paths":{}}
    for name in json.load(sys.stdin):
        rights={}
        for kind,flags in (("read",os.O_RDONLY),("write",os.O_WRONLY|os.O_APPEND)):
            try:
                fd=os.open(name,flags|os.O_NOFOLLOW)
            except PermissionError:
                rights[kind]=False
            else:
                os.close(fd);rights[kind]=True
        result["paths"][name]=rights
    print(json.dumps(result))
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
            for name in (
                "echo",
                "policy",
                "writer",
                "fence-writer",
                "hang",
                "owned",
                "rights",
            )
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
def test_frozen_tree_is_suspended_and_reopened_before_retirement() -> None:
    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        cohort.start()
        assert cohort.run("writer")["exit_code"] == 0
        writes = case.payload / "writes"
        _wait(lambda: b"descendant" in writes.read_bytes())
        cohort.close_and_freeze(deadline=time.monotonic() + 5)
        assert cohort.state["phase"] == "frozen"
        assert cohort.events() == {"populated": 1, "frozen": 1}
        before = writes.read_bytes()
        cohort.close()
        reopened = cold.ControlledCohort.reopen(cohort.directory, case.control)
        try:
            time.sleep(0.05)
            assert writes.read_bytes() == before
            with pytest.raises(cold.Refused):
                reopened.run("echo")
            reopened.retire(deadline=time.monotonic() + 5)
            assert reopened.events()["populated"] == 0
        finally:
            reopened.close()


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
    if stage=="frozen":
        cohort.close_and_freeze(deadline=time.monotonic()+5)
        checkpoint("frozen")
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
        (case.control_root / "other.guard").chmod(0o600)
        (case.control_root / "other.epoch").chmod(0o600)
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
@pytest.mark.parametrize("name", ["guard", "epoch"])
@pytest.mark.parametrize("attack", ["mode", "owner", "acl"])
def test_independent_control_files_must_remain_root_only(
    name: str, attack: str
) -> None:
    import struct

    with _case() as case, case.control.exclusive():
        cohort = case.provision()
        before = (cohort.directory / "cohort.json").read_bytes()
        path = case.control_root / name
        try:
            if attack == "mode":
                path.chmod(0o666)
            elif attack == "owner":
                getattr(os, "chown")(path, 62017, 62017)
            else:
                acl = struct.pack("<I", 2) + b"".join(
                    struct.pack("<HHI", tag, permission, uid)
                    for tag, permission, uid in (
                        (1, 6, 0xFFFFFFFF),
                        (2, 4, 62019),
                        (4, 0, 0xFFFFFFFF),
                        (16, 0, 0xFFFFFFFF),
                        (32, 0, 0xFFFFFFFF),
                    )
                )
                getattr(os, "setxattr")(path, "system.posix_acl_access", acl)
                assert path.lstat().st_mode & 0o777 == 0o600
            with pytest.raises(cold.Refused):
                cohort.start()
            assert (cohort.directory / "cohort.json").read_bytes() == before
        finally:
            if attack == "acl":
                getattr(os, "removexattr")(path, "system.posix_acl_access")
            getattr(os, "chown")(path, 0, 0)
            path.chmod(0o600)


@_REAL
@pytest.mark.parametrize(
    "stage", ["carrier_spawned", "genesis_bound", "go", "active-native", "frozen"]
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
                    if stage == "frozen":
                        assert recovered.state["phase"] == "frozen"
                        assert recovered.events() == {"populated": 1, "frozen": 1}
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


def _fence_fixture(case: Case) -> tuple[Path, Path, Path, Path]:
    core, data = case.root / "legacy-core", case.root / "legacy-data"
    (core / "tools").mkdir(parents=True)
    (core / "runtime/native-control").mkdir(parents=True)
    data.mkdir()
    code = core / "tools/agent.py"
    code.write_text("print('fixture')\n", encoding="ascii")
    guard = core / "runtime/native-control/installation.guard"
    guard.write_bytes(b"0")
    (guard.parent / "epoch").write_bytes(b"fixture-epoch")
    (data / "store").write_bytes(b"legacy\n")
    for root in (core, data):
        for path in (root, *root.rglob("*")):
            path.chmod(0o700 if path.is_dir() else 0o600)
            getattr(os, "chown")(path, 62017, 62017)
    code.chmod(0o700)
    directory = case.control_root / "fence"
    directory.mkdir(mode=0o700)
    return core, data, guard, directory


def _fence_plan(case: Case, cohort: cold.ControlledCohort) -> cold.FrozenTreeFence:
    core, data = case.root / "legacy-core", case.root / "legacy-data"
    return cold.FrozenTreeFence.plan(
        case.control_root / "fence",
        cohort,
        roots={core: "core", data: "data"},
        maintenance_uid=62019,
        maintenance_gid=62019,
        byte_locks=(core / "runtime/native-control/installation.guard",),
        executables=(core / "tools/agent.py",),
    )


@_REAL
def test_persistent_fence_restricts_live_descriptors_and_exact_nonroot_roles() -> None:
    with _case() as case, case.control.exclusive():
        core, data, guard, directory = _fence_fixture(case)
        legacy = case.provision()
        legacy.start()
        assert legacy.run("fence-writer", os.fsencode(data / "store"))["exit_code"] == 0
        _wait(lambda: b"descendant" in (data / "store").read_bytes())
        with pytest.raises(cold.Refused):
            _fence_plan(case, legacy)
        assert not (directory / "fence.json").exists()
        legacy.close_and_freeze(deadline=time.monotonic() + 5)
        fence = _fence_plan(case, legacy)
        stale = cold.FrozenTreeFence.reopen(directory, legacy)
        fence.apply()
        fence.verify()
        assert legacy.events() == {"populated": 1, "frozen": 1}
        size = (data / "store").stat().st_size
        time.sleep(0.03)
        assert (data / "store").stat().st_size == size
        legacy.retire(deadline=time.monotonic() + 5)
        assert legacy.events()["populated"] == 0
        fence.verify()
        saved = (directory / "fence.json").read_bytes()
        with pytest.raises(cold.Refused):
            stale.apply()
        assert (directory / "fence.json").read_bytes() == saved
        selected = [
            str(core / "tools/agent.py"),
            str(guard),
            str(guard.parent / "epoch"),
            str(data / "store"),
        ]
        # Test-only credential access probes, not business B release or an
        # issuer attestation for an existing deployment.
        for role in ("legacy", "successor", "native"):
            probe = case.provision(role=role)
            probe.start()
            reply = probe.run("rights", json.dumps(selected).encode())
            assert reply["exit_code"] == 0 and not reply["stderr"]
            actual = json.loads(reply["stdout"])
            assert (
                actual["uid"]
                == {"legacy": 62017, "successor": 62018, "native": 62019}[role]
            )
            expected = (
                [(True, False), (True, True), (True, False), (True, True)]
                if role == "native"
                else [(False, False)] * 4
            )
            for path, (read, write) in zip(selected, expected, strict=True):
                assert actual["paths"][path] == {"read": read, "write": write}
            probe.retire(deadline=time.monotonic() + 5)
        assert (data / "store").stat().st_size == size
        cold.FrozenTreeFence.reopen(directory, legacy).verify()


@_REAL
@pytest.mark.parametrize("stage", ["zero", "owner", "final"])
@pytest.mark.parametrize("target", ["directory", "file"])
def test_fence_exact_partial_images_resume_without_restoring_old_rights(
    stage: str, target: str
) -> None:
    with _case() as case, case.control.exclusive():
        core, _data, _guard, directory = _fence_fixture(case)
        cohort = case.provision()
        cohort.start()
        cohort.close_and_freeze(deadline=time.monotonic() + 5)
        fence = _fence_plan(case, cohort)
        relative = "." if target == "directory" else "tools/agent.py"
        index = next(
            i
            for i, row in enumerate(fence.state["plan"]["rows"])
            if row["root"] == 0 and row["relative"] == relative
        )

        def interrupt(row: int, step: str) -> None:
            if row == index and step == stage:
                raise RuntimeError("fixture fence interruption")

        with pytest.raises(RuntimeError, match="fence interruption"):
            fence.apply(checkpoint=interrupt)
        assert not cold._read(directory / "fence.json")["complete"]
        row = fence.state["plan"]["rows"][index]
        path = core / relative
        info = path.lstat()
        expected = {
            "zero": [row["before"][0], row["before"][1], 0],
            "owner": [row["after"][0], row["after"][1], 0],
            "final": row["after"],
        }[stage]
        assert [info.st_uid, info.st_gid, info.st_mode & 0o7777] == expected
        resumed = cold.FrozenTreeFence.reopen(directory, cohort)
        with pytest.raises(cold.Refused):
            resumed.verify()
        resumed.apply()
        resumed.verify()
        cohort.retire(deadline=time.monotonic() + 5)
        resumed.verify()


_FENCE_CONTROLLER = r"""
import sys,time
from pathlib import Path
import pf_linux_cold_controller as cold
import pf_native_control as native
directory,cohort_dir,control_root,marker,index,stage=sys.argv[1:]
directory,cohort_dir,control_root,marker=map(Path,(directory,cohort_dir,control_root,marker))
gate=native.NativeControl(control_root/"guard",control_root/"epoch","cohort-fixture")
with gate.exclusive():
    cohort=cold.ControlledCohort.reopen(cohort_dir,gate)
    fence=cold.FrozenTreeFence.reopen(directory,cohort)
    def checkpoint(row,step):
        if row==int(index) and step==stage:
            marker.write_text(step)
            time.sleep(30)
    fence.apply(checkpoint=checkpoint)
    if stage=="complete":
        marker.write_text(stage)
        time.sleep(30)
"""


@_REAL
@pytest.mark.parametrize(
    ("target", "stage"),
    [
        (target, stage)
        for target in ("directory", "file")
        for stage in ("zero", "owner", "final")
    ]
    + [("directory", "complete")],
)
def test_real_controller_death_preserves_exact_fence_recovery(
    target: str, stage: str
) -> None:
    with _case() as case:
        with case.control.exclusive():
            _core, _data, _guard, directory = _fence_fixture(case)
            cohort = case.provision()
            cohort.start()
            cohort.close_and_freeze(deadline=time.monotonic() + 5)
            fence = _fence_plan(case, cohort)
            relative = "." if target == "directory" else "tools/agent.py"
            index = next(
                i
                for i, row in enumerate(fence.state["plan"]["rows"])
                if row["root"] == 0 and row["relative"] == relative
            )
        marker = case.control_root / "fence-checkpoint"
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                _FENCE_CONTROLLER,
                str(directory),
                str(cohort.directory),
                str(case.control_root),
                str(marker),
                str(index),
                stage,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        descriptor = getattr(os, "pidfd_open")(process.pid)
        try:
            _wait(marker.is_file)
            getattr(signal, "pidfd_send_signal")(descriptor, getattr(signal, "SIGKILL"))
            stdout, stderr = process.communicate(timeout=5)
            assert process.returncode == -getattr(signal, "SIGKILL")
            assert not stdout and not stderr
            with case.control.exclusive():
                recovered = cold.ControlledCohort.reopen(cohort.directory, case.control)
                try:
                    assert recovered.events() == {"populated": 1, "frozen": 1}
                    resumed = cold.FrozenTreeFence.reopen(directory, recovered)
                    assert resumed.state["complete"] is (stage == "complete")
                    resumed.apply()
                    resumed.verify()
                    recovered.retire(deadline=time.monotonic() + 5)
                    resumed.verify()
                finally:
                    recovered.close()
        finally:
            if process.poll() is None:
                getattr(signal, "pidfd_send_signal")(
                    descriptor, getattr(signal, "SIGKILL")
                )
                process.communicate(timeout=5)
            os.close(descriptor)


@_REAL
@pytest.mark.parametrize("attack", ["extra", "missing", "replaced", "rights", "link"])
def test_fence_drift_refuses_before_any_other_permission_mutation(attack: str) -> None:
    with _case() as case, case.control.exclusive():
        core, data, _guard, directory = _fence_fixture(case)
        cohort = case.provision()
        cohort.start()
        cohort.close_and_freeze(deadline=time.monotonic() + 5)
        fence = _fence_plan(case, cohort)
        target = core / "tools/agent.py"
        if attack == "extra":
            (core / "foreign").write_bytes(b"foreign")
        elif attack == "missing":
            target.unlink()
        elif attack == "replaced":
            temporary = core / "replacement"
            temporary.write_bytes(target.read_bytes())
            temporary.replace(target)
        elif attack == "rights":
            target.chmod(0o004)
        else:
            target.unlink()
            target.symlink_to(data / "store")
        before = [
            (path.lstat().st_uid, path.lstat().st_gid, path.lstat().st_mode)
            for path in (core, data)
        ]
        plan = (directory / "fence.json").read_bytes()
        with pytest.raises(cold.Refused):
            fence.apply()
        assert (directory / "fence.json").read_bytes() == plan
        assert [
            (path.lstat().st_uid, path.lstat().st_gid, path.lstat().st_mode)
            for path in (core, data)
        ] == before


@_REAL
@pytest.mark.parametrize(
    "attack", ["symlink", "hardlink", "fifo", "acl", "role-map", "control-root"]
)
def test_fence_rejects_unsafe_initial_objects_and_control_delegation(
    attack: str,
) -> None:
    with _case() as case, case.control.exclusive():
        core, _data, _guard, directory = _fence_fixture(case)
        target = core / "tools/agent.py"
        cohort = case.provision()
        cohort.start()
        cohort.close_and_freeze(deadline=time.monotonic() + 5)
        if attack == "symlink":
            (core / "alias").symlink_to(target)
        elif attack == "hardlink":
            os.link(target, core / "alias")
        elif attack == "fifo":
            getattr(os, "mkfifo")(core / "fifo", 0o600)
        elif attack == "acl":
            import struct

            acl = struct.pack("<I", 2) + b"".join(
                struct.pack("<HHI", tag, permission, uid)
                for tag, permission, uid in (
                    (1, 6, 0xFFFFFFFF),
                    (2, 6, 62020),
                    (4, 0, 0xFFFFFFFF),
                    (16, 6, 0xFFFFFFFF),
                    (32, 0, 0xFFFFFFFF),
                )
            )
            getattr(os, "setxattr")(target, "system.posix_acl_access", acl)
        with pytest.raises(cold.Refused):
            if attack in {"role-map", "control-root"}:
                cold.FrozenTreeFence.plan(
                    directory,
                    cohort,
                    roots={core if attack == "role-map" else case.control_root: "core"},
                    maintenance_uid=62019,
                    maintenance_gid=62019,
                    byte_locks=(target,) if attack == "role-map" else (),
                )
            else:
                _fence_plan(case, cohort)
        assert not (directory / "fence.json").exists()
        assert core.lstat().st_uid == 62017


@_REAL
@pytest.mark.parametrize("kind", ["nested", "alias"])
def test_actual_bind_mount_is_rejected_before_fencing(kind: str) -> None:
    with _case() as case, case.control.exclusive():
        core, data, _guard, directory = _fence_fixture(case)
        cohort = case.provision()
        cohort.start()
        cohort.close_and_freeze(deadline=time.monotonic() + 5)
        source = case.root / "mount-source" if kind == "nested" else core
        if kind == "nested":
            source.mkdir()
            (source / "file").write_bytes(b"mount fixture")
        destination = core / "nested" if kind == "nested" else case.root / "alias-core"
        destination.mkdir()
        assert destination.is_relative_to(case.root)
        library = ctypes.CDLL(None, use_errno=True)
        library.mount.argtypes = (
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
        )
        library.mount.restype = ctypes.c_int
        library.umount2.argtypes = (ctypes.c_char_p, ctypes.c_int)
        library.umount2.restype = ctypes.c_int
        result = library.mount(
            os.fsencode(source), os.fsencode(destination), None, 4096, None
        )
        assert result == 0, f"real bind mount unavailable errno={ctypes.get_errno()}"
        try:
            roots = {core: "core", data: "data"}
            if kind == "alias":
                roots[destination] = "core"
            with pytest.raises(cold.Refused):
                cold.FrozenTreeFence.plan(
                    directory,
                    cohort,
                    roots=roots,
                    maintenance_uid=62019,
                    maintenance_gid=62019,
                )
            assert not (directory / "fence.json").exists()
            assert core.lstat().st_uid == 62017
        finally:
            assert library.umount2(os.fsencode(destination), 0) == 0


@_REAL
@pytest.mark.parametrize(
    "attack", ["double-slash", "guard-alias", "guard-descendant-alias", "cohort-alias"]
)
def test_sole_private_alias_refuses_before_plan_or_permission_writes(
    attack: str,
) -> None:
    with _case() as case:
        independent = case.root / "independent-gate"
        independent.mkdir(mode=0o700)
        for name in ("guard", "epoch"):
            (case.control_root / name).replace(independent / name)
        case.control = native.NativeControl(
            independent / "guard", independent / "epoch", "cohort-fixture"
        )
        with case.control.exclusive():
            cohort = case.provision()
            cohort.start()
            cohort.close_and_freeze(deadline=time.monotonic() + 5)
            directory = case.control_root / "fence"
            directory.mkdir(mode=0o700)
            nested = independent / "private"
            nested.mkdir(mode=0o700)
            (nested / "receipt").write_bytes(b"private")
            (nested / "receipt").chmod(0o600)
            source = (
                nested
                if attack == "guard-descendant-alias"
                else cohort.group
                if attack == "cohort-alias"
                else independent
            )
            before = {
                str(path): (
                    path.lstat().st_uid,
                    path.lstat().st_gid,
                    path.lstat().st_mode,
                )
                for path in (
                    independent,
                    independent / "guard",
                    independent / "epoch",
                    cohort.group,
                    nested,
                    nested / "receipt",
                )
            }
            guard_bytes = (independent / "guard").read_bytes()
            epoch_bytes = (independent / "epoch").read_bytes()
            mounted = attack != "double-slash"
            if mounted:
                target = case.root / "protected-alias"
                target.mkdir(mode=0o700)
                library = ctypes.CDLL(None, use_errno=True)
                library.mount.argtypes = (
                    ctypes.c_char_p,
                    ctypes.c_char_p,
                    ctypes.c_char_p,
                    ctypes.c_ulong,
                    ctypes.c_void_p,
                )
                library.mount.restype = ctypes.c_int
                library.umount2.argtypes = (ctypes.c_char_p, ctypes.c_int)
                library.umount2.restype = ctypes.c_int
                assert (
                    library.mount(
                        os.fsencode(source), os.fsencode(target), None, 4096, None
                    )
                    == 0
                ), f"bind mount unavailable errno={ctypes.get_errno()}"
            else:
                target = Path("//" + str(independent).lstrip("/"))
                assert target.anchor == "//"
            try:
                with pytest.raises(cold.Refused):
                    cold.FrozenTreeFence.plan(
                        directory,
                        cohort,
                        roots={target: "data"},
                        maintenance_uid=62019,
                        maintenance_gid=62019,
                    )
                assert not (directory / "fence.json").exists()
                assert (independent / "guard").read_bytes() == guard_bytes
                assert (independent / "epoch").read_bytes() == epoch_bytes
                assert {
                    name: (
                        Path(name).lstat().st_uid,
                        Path(name).lstat().st_gid,
                        Path(name).lstat().st_mode,
                    )
                    for name in before
                } == before
                assert cohort.events() == {"populated": 1, "frozen": 1}
                assert native._exclusive_lease_identity(case.control)
            finally:
                if mounted:
                    assert target.is_relative_to(case.root)
                    assert library.umount2(os.fsencode(target), 0) == 0
