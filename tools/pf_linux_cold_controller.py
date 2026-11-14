"""Private Linux controlled-cohort primitives; never deployment authority.

Only the independent trusted issuer may provision a cohort BEFORE its first
writer. Unknown historical installations cannot be adopted through this API.
The caller retains its external native gate and domain recovery obligations.
No import, empty cgroup, receipt, UID or caller flag qualifies a deployment.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import select
import socket
import stat
import struct
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

import pf_native_control as native

_FORMAT = "linux-controlled-cohort-v1"
_PACKET_LIMIT = 64 * 1024 * 1024
_OUTPUT_LIMIT = 1024 * 1024


class Refused(native.NativeControlError):
    """Keep native refusal; detailed reasons are private controller diagnostics."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__()


def _require(value: bool, reason: str) -> None:
    if not value:
        raise Refused(reason)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def _sha(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _controller() -> dict[str, str | int]:
    raw = Path("/proc/self/stat").read_text(encoding="ascii")
    return {
        "pid": os.getpid(),
        "ticks": raw[raw.rindex(")") + 2 :].split()[19],
    }


def _identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    _require(
        stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0,
        "cohort_directory",
    )
    return info.st_dev, info.st_ino


def _protected(path: Path) -> None:
    _require(
        path.is_absolute() and path.anchor == "/" and ".." not in path.parts,
        "cohort_directory",
    )
    for item in (path, *path.parents):
        _identity(item)
        mode = item.lstat().st_mode
        # A root-owned child cannot be renamed by a nonroot user in /tmp.
        _require(
            not mode & 0o022 or (item != path and bool(mode & stat.S_ISVTX)),
            "cohort_ancestor_writable",
        )
        _require(
            not {"system.posix_acl_access", "system.posix_acl_default"}
            & set(getattr(os, "listxattr")(item, follow_symlinks=False)),
            "cohort_acl",
        )
    _require(stat.S_IMODE(path.lstat().st_mode) == 0o700, "cohort_directory_mode")


def _platform() -> dict[str, str]:
    _require(
        sys.platform.startswith("linux")
        and getattr(os, "uname")().machine == "x86_64"
        and sys.maxsize == 2**63 - 1
        and os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 0,
        "cohort_platform",
    )
    return {
        "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "mount": os.readlink("/proc/self/ns/mnt"),
        "cgroup_namespace": os.readlink("/proc/self/ns/cgroup"),
        "user_namespace": os.readlink("/proc/self/ns/user"),
    }


def _atomic(path: Path, value: dict[str, Any]) -> None:
    _protected(path.parent)
    temporary = path.with_name("." + path.name + "." + uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _private_file(path: Path) -> None:
    info = path.lstat()
    _require(
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == info.st_gid == 0
        and stat.S_IMODE(info.st_mode) == 0o600,
        "cohort_private_file",
    )
    _require(
        not {"system.posix_acl_access", "system.posix_acl_default"}
        & set(getattr(os, "listxattr")(path, follow_symlinks=False)),
        "cohort_private_file_acl",
    )


def _read(path: Path) -> dict[str, Any]:
    _protected(path.parent)
    _private_file(path)
    value = native._read(path, _PACKET_LIMIT)
    _require(isinstance(value, dict), "cohort_state")
    return value


def _held(control: native.NativeControl) -> dict[str, Any]:
    _platform()
    _protected(control.guard.parent)
    _protected(control.epoch_path.parent)
    _private_file(control.guard)
    _private_file(control.epoch_path)
    try:
        return native._exclusive_lease_identity(control)
    except (native.NativeControlError, OSError, UnicodeError):
        raise Refused("cohort_exclusive_gate_required") from None


def _receive(connection: socket.socket) -> dict[str, Any]:
    def exact(size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            part = connection.recv(size - len(result))
            if not part:
                raise Refused("cohort_channel_closed")
            result.extend(part)
        return bytes(result)

    size = struct.unpack("!I", exact(4))[0]
    _require(0 < size <= _PACKET_LIMIT, "cohort_packet")
    value = json.loads(exact(size))
    _require(isinstance(value, dict), "cohort_packet")
    return value


def _send(connection: socket.socket, value: dict[str, Any]) -> None:
    raw = _canonical(value)
    _require(0 < len(raw) <= _PACKET_LIMIT, "cohort_packet")
    connection.sendall(struct.pack("!I", len(raw)) + raw)


# Captured constant source only. The carrier imports stdlib, not Core or any
# mutable helper module. No target read/spawn is possible before exact token GO.
_BROKER = r"""
import base64, ctypes, errno, json, os, select, socket, struct, subprocess, sys, tempfile
from pathlib import Path
channel = socket.socket(fileno=int(sys.argv[1]))
group_fd, parent_fd = int(sys.argv[2]), int(sys.argv[3])
channel.settimeout(10)
def exact(size):
    value = bytearray()
    while len(value) < size:
        part = channel.recv(size-len(value))
        if not part:
            raise EOFError
        value.extend(part)
    return bytes(value)
def receive():
    size = struct.unpack("!I", exact(4))[0]
    if not 0 < size <= 67108864:
        raise ValueError("packet")
    return json.loads(exact(size))
def send(value):
    raw = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True).encode("ascii")
    if len(raw) > 67108864:
        raise ValueError("packet")
    channel.sendall(struct.pack("!I",len(raw))+raw)
try:
    packet = receive()
    if select.select([parent_fd],[],[],0)[0]:
        raise EOFError
    fd = os.open("cgroup.procs",os.O_WRONLY|os.O_NOFOLLOW,dir_fd=group_fd)
    with os.fdopen(fd,"w") as stream:
        stream.write(str(os.getpid()))
    os.close(group_fd)
    libc = ctypes.CDLL(None,use_errno=True)
    libc.prctl.argtypes = (ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong)
    def prctl(option,value):
        if libc.prctl(option,value,None,0,0)!=0:
            raise OSError(ctypes.get_errno(),"credential policy")
    # Drop the bounding set before SETPCAP and the other capabilities are lost.
    for capability in range(64):
        if libc.prctl(24,capability,None,0,0)!=0:
            if ctypes.get_errno()==errno.EINVAL:
                break
            raise OSError(ctypes.get_errno(),"capability bound")
    prctl(28,3)  # NOROOT and NOROOT_LOCKED; no UID0 business/actor cohort.
    prctl(47,4)  # Clear ambient capabilities.
    os.setgroups([])
    os.setresgid(packet["gid"],packet["gid"],packet["gid"])
    os.setresuid(packet["uid"],packet["uid"],packet["uid"])
    class Header(ctypes.Structure):
        _fields_=[("version",ctypes.c_uint32),("pid",ctypes.c_int)]
    class Caps(ctypes.Structure):
        _fields_=[("effective",ctypes.c_uint32),("permitted",ctypes.c_uint32),("inheritable",ctypes.c_uint32)]
    header=Header(0x20080522,0)
    capabilities=(Caps*2)()
    if libc.capset(ctypes.byref(header),ctypes.byref(capabilities))!=0:
        raise OSError(ctypes.get_errno(),"capability clear")
    prctl(38,1)  # no_new_privs is inherited and cannot be unset.
    prctl(4,0)   # Do not expose the broker's private control descriptors.
    class Insn(ctypes.Structure):
        _fields_=[("code",ctypes.c_ushort),("jt",ctypes.c_ubyte),("jf",ctypes.c_ubyte),("k",ctypes.c_uint32)]
    class Prog(ctypes.Structure):
        _fields_=[("len",ctypes.c_ushort),("filter",ctypes.POINTER(Insn))]
    rules=[(0x20,0,0,4),(0x15,1,0,0xc000003e),(0x06,0,0,0x80000000),
           (0x20,0,0,0),(0x45,0,1,0x40000000),(0x06,0,0,0x00050001)]
    for number in (46,307,438,101,311,425):
        rules += [(0x15,0,1,number),(0x06,0,0,0x00050001)]
    rules += [(0x06,0,0,0x7fff0000)]
    instructions=(Insn*len(rules))(*(Insn(*row) for row in rules))
    program=Prog(len(rules),instructions)
    if libc.prctl(22,2,ctypes.byref(program),0,0)!=0:
        raise OSError(ctypes.get_errno(),"syscall policy")
    send({"kind":"ready","token":packet["token"],"pid":os.getpid()})
    go=receive()
    if go != {"kind":"go","token":packet["token"]} or select.select([parent_fd],[],[],0)[0]:
        raise EOFError
    os.close(parent_fd)
    channel.settimeout(None)
    while True:
        request=receive()
        if set(request)!={"id","route","input"} or request["route"] not in packet["routes"]:
            raise ValueError("fixed route")
        route=packet["routes"][request["route"]]
        supplied=base64.b64decode(request["input"],validate=True)
        # Spool bounded protocol output without unbounded parent memory. A timeout
        # leaves unknown outcome; the controller must retire the whole cohort.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process=subprocess.Popen(route["argv"],stdin=subprocess.PIPE,
                stdout=stdout,stderr=stderr,env=packet["environment"],close_fds=True)
            try:
                process.communicate(supplied,timeout=route["timeout"])
            except subprocess.TimeoutExpired:
                send({"id":request["id"],"error":"outcome_unknown"})
                break
            stdout.seek(0);stderr.seek(0)
            output,error=stdout.read(1048577),stderr.read(1048577)
            if len(output)>1048576 or len(error)>1048576:
                send({"id":request["id"],"error":"outcome_unknown"})
                break
            send({"id":request["id"],"exit_code":process.returncode,
                  "stdout":base64.b64encode(output).decode("ascii"),
                  "stderr":base64.b64encode(error).decode("ascii")})
except (EOFError, OSError, ValueError, KeyError, TypeError):
    pass  # No GO/unknown reply never permits a target replay.
finally:
    channel.close()
"""


class ControlledCohort:
    """Exact cohort lifetime under an existing independent native gate.

    This primitive supplies no issuer attestation, filesystem fence, operational
    readiness, native adoption or guarded release. A fixed route's exit is not
    proof that its descendants stopped. Only explicit whole-cohort retirement
    can establish that kernel fact, and never completeness of unknown history.
    """

    def __init__(
        self, directory: Path, control: native.NativeControl, state: dict[str, Any]
    ) -> None:
        self.connection: socket.socket | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.group_fd = -1
        gate = _held(control)
        _protected(directory)
        self.directory, self.control, self.state = directory, control, state
        _require(state["format"] == _FORMAT, "cohort_state")
        _require(state["platform"] == _platform(), "cohort_platform_changed")
        _require(state["gate"] == gate, "cohort_gate_changed")
        self.group = Path(state["group"])
        _require(
            self.group.parent == Path("/sys/fs/cgroup")
            and self.group.name == "pf-controlled-" + state["token"],
            "cohort_path",
        )
        self.group_fd = os.open(
            self.group,
            os.O_RDONLY | getattr(os, "O_DIRECTORY") | getattr(os, "O_NOFOLLOW"),
        )
        info = os.fstat(self.group_fd)
        _require(
            [info.st_dev, info.st_ino] == state["group_identity"]
            and info.st_uid == info.st_gid == 0
            and not stat.S_IMODE(info.st_mode) & 0o022,
            "cohort_identity",
        )
        filesystem = ctypes.create_string_buffer(512)
        library = ctypes.CDLL(None, use_errno=True)
        _require(
            library.fstatfs(self.group_fd, ctypes.byref(filesystem)) == 0
            and ctypes.c_long.from_buffer(filesystem).value == 0x63677270,
            "cohort_filesystem",
        )

    @classmethod
    def provision(
        cls,
        directory: Path,
        control: native.NativeControl,
        *,
        uid: int,
        gid: int,
        role: str,
        profile_sha256: str,
        routes: Mapping[str, Mapping[str, Any]],
    ) -> ControlledCohort:
        """Trusted genesis only, before any writer of this declared history."""
        gate = _held(control)
        _protected(directory)
        _require(role in {"legacy", "native", "successor"}, "cohort_role")
        _require(
            type(uid) is int
            and type(gid) is int
            and 0 < uid < 2**32 - 1
            and 0 < gid < 2**32 - 1,
            "cohort_credentials",
        )
        _require(
            len(profile_sha256) == 71
            and profile_sha256.startswith("sha256:")
            and all(c in "0123456789abcdef" for c in profile_sha256[7:]),
            "cohort_profile",
        )
        selected = json.loads(_canonical(dict(routes)))
        _require(bool(selected), "cohort_routes")
        for name, route in selected.items():
            _require(
                isinstance(name, str)
                and bool(name)
                and isinstance(route, dict)
                and set(route) == {"argv", "timeout"}
                and isinstance(route["argv"], list)
                and bool(route["argv"])
                and all(
                    isinstance(arg, str) and "\0" not in arg for arg in route["argv"]
                )
                and Path(route["argv"][0]).is_absolute()
                and type(route["timeout"]) in {int, float}
                and 0 < route["timeout"] <= 120,
                "cohort_routes",
            )
        path = directory / "cohort.json"
        _require(not path.exists(), "cohort_already_provisioned")
        token = uuid4().hex
        group = Path("/sys/fs/cgroup") / ("pf-controlled-" + token)
        state = {
            "format": _FORMAT,
            "platform": _platform(),
            "gate": gate,
            "token": token,
            "role": role,
            "uid": uid,
            "gid": gid,
            "profile": profile_sha256,
            "group": str(group),
            "group_identity": None,
            "routes": selected,
            "phase": "reserved",
            "pending": None,
            "last_result": None,
            "launch_reserved": False,
            "broker": None,
            "environment_sha256": None,
            "creator": None,
        }
        _atomic(path, state)
        group.mkdir()  # Exclusive; never adopt an existing cgroup by its name.
        state["group_identity"] = list(_identity(group))
        _atomic(path, state)
        return cls(directory, control, state)

    @classmethod
    def reopen(cls, directory: Path, control: native.NativeControl) -> ControlledCohort:
        """Reopen exact kernel identity for observation/retirement, never GO."""
        return cls(directory, control, _read(directory / "cohort.json"))

    def _current(self) -> None:
        gate = _held(self.control)
        _require(
            _read(self.directory / "cohort.json") == self.state
            and self.state["platform"] == _platform()
            and self.state["gate"] == gate,
            "cohort_state_changed",
        )
        info = os.fstat(self.group_fd)
        _require(
            list(_identity(self.group)) == self.state["group_identity"]
            and [info.st_dev, info.st_ino] == self.state["group_identity"],
            "cohort_identity",
        )

    def _save(self) -> None:
        _atomic(self.directory / "cohort.json", self.state)

    def _file(self, name: str, *, write: str | None = None) -> str:
        self._current()
        _require(
            name in {"cgroup.events", "cgroup.freeze", "cgroup.kill"},
            "cohort_control_file",
        )
        descriptor = os.open(
            name,
            (os.O_RDONLY if write is None else os.O_WRONLY) | getattr(os, "O_NOFOLLOW"),
            dir_fd=self.group_fd,
        )
        with os.fdopen(descriptor, "r" if write is None else "w") as stream:
            info = os.fstat(stream.fileno())
            _require(
                stat.S_ISREG(info.st_mode)
                and info.st_uid == info.st_gid == 0
                and not stat.S_IMODE(info.st_mode) & 0o022,
                "cohort_control_file",
            )
            if write is not None:
                stream.write(write)
                return ""
            return stream.read(65537)

    def events(self) -> dict[str, int]:
        raw = self._file("cgroup.events")
        _require(len(raw) <= 65536, "cohort_events")
        result: dict[str, int] = {}
        for line in raw.splitlines():
            fields = line.split()
            _require(
                len(fields) == 2 and fields[0] not in result and fields[1].isdecimal(),
                "cohort_events",
            )
            result[fields[0]] = int(fields[1])
        _require(
            result.get("populated") in {0, 1} and result.get("frozen") in {0, 1},
            "cohort_events",
        )
        return result

    def _broker_facts(self, pid: int) -> dict[str, Any]:
        base = Path("/proc") / str(pid)
        status = dict(
            line.split(":", 1)
            for line in (base / "status").read_text(encoding="ascii").splitlines()
        )
        for key in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
            _require(int(status[key], 16) == 0, "cohort_credentials")
        _require(
            [int(x) for x in status["Uid"].split()] == [self.state["uid"]] * 4
            and [int(x) for x in status["Gid"].split()] == [self.state["gid"]] * 4
            and not status["Groups"].strip()
            and status["NoNewPrivs"].strip() == "1"
            and status["Seccomp"].strip() == "2"
            and int(status["Seccomp_filters"]) > 0
            and os.readlink(base / "ns/cgroup")
            == self.state["platform"]["cgroup_namespace"]
            and (base / "cgroup").read_text().strip() == "0::/" + self.group.name,
            "cohort_broker_membership",
        )
        raw = (base / "stat").read_text(encoding="ascii")
        return {
            "pid": pid,
            "ticks": raw[raw.rindex(")") + 2 :].split()[19],
            "carrier_sha256": _sha(_BROKER.encode("utf-8")),
        }

    def start(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        checkpoint: Callable[[str], None] = lambda _: None,
    ) -> None:
        """One genesis attempt; failed/unknown attempts are never replayed."""
        self._current()
        _require(
            self.state["phase"] == "reserved" and not self.state["launch_reserved"],
            "cohort_genesis_already_attempted",
        )
        selected = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            **dict(environment or {}),
        }
        _require(
            all(
                isinstance(k, str)
                and isinstance(v, str)
                and "\0" not in k + v
                and "=" not in k
                for k, v in selected.items()
            ),
            "cohort_environment",
        )
        self.state["launch_reserved"] = True
        self.state["environment_sha256"] = _sha(_canonical(selected))
        self.state["creator"] = {**_controller(), "incarnation": uuid4().hex}
        self._save()
        checkpoint("launch_reserved")
        parent, child = socket.socketpair()
        parent.settimeout(15)
        parent_fd = getattr(os, "pidfd_open")(os.getpid())
        process_fd = None
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    _BROKER,
                    str(child.fileno()),
                    str(self.group_fd),
                    str(parent_fd),
                ],
                env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                pass_fds=(child.fileno(), self.group_fd, parent_fd),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            child.close()
            process_fd = getattr(os, "pidfd_open")(self.process.pid)
            checkpoint("carrier_spawned")
            _send(
                parent,
                {
                    "token": self.state["token"],
                    "uid": self.state["uid"],
                    "gid": self.state["gid"],
                    "routes": self.state["routes"],
                    "environment": selected,
                },
            )
            ready = _receive(parent)
            _require(
                ready
                == {
                    "kind": "ready",
                    "token": self.state["token"],
                    "pid": self.process.pid,
                }
                and not select.select([process_fd], [], [], 0)[0],
                "cohort_genesis_unverified",
            )
            facts = self._broker_facts(self.process.pid)
            checkpoint("ready")
            self.state.update(phase="active", broker=facts)
            self._save()
            checkpoint("genesis_bound")
            _send(parent, {"kind": "go", "token": self.state["token"]})
            self.connection = parent
            checkpoint("go")
        except BaseException:
            parent.close()  # EOF before GO can never execute a target.
            self.connection = None
            raise
        finally:
            child.close()
            os.close(parent_fd)
            if process_fd is not None:
                os.close(process_fd)

    def run(self, route: str, supplied: bytes = b"") -> dict[str, Any]:
        """Run a fixed trusted route once; unknown reply keeps its reservation."""
        self._current()
        _require(
            self.state["phase"] == "active"
            and self.connection is not None
            and self.state["pending"] is None
            and self.state["creator"]["pid"] == os.getpid()
            and self.state["creator"]["ticks"] == _controller()["ticks"]
            and route in self.state["routes"]
            and isinstance(supplied, bytes)
            and len(supplied) <= _PACKET_LIMIT // 2,
            "cohort_route_unavailable",
        )
        connection = self.connection
        if connection is None:
            raise Refused("cohort_route_unavailable")
        request = uuid4().hex
        pending = {
            "id": request,
            "route": route,
            "input_sha256": _sha(supplied),
            "controller_pid": os.getpid(),
            "controller_incarnation": self.state["creator"]["incarnation"],
            "cohort_token": self.state["token"],
            "profile": self.state["profile"],
        }
        self.state["pending"] = pending
        self._save()
        connection.settimeout(self.state["routes"][route]["timeout"] + 10)
        _send(
            connection,
            {
                "id": request,
                "route": route,
                "input": base64.b64encode(supplied).decode("ascii"),
            },
        )
        reply = _receive(connection)
        _require(
            set(reply) == {"id", "exit_code", "stdout", "stderr"}
            and reply["id"] == request
            and type(reply["exit_code"]) is int,
            "cohort_outcome_unknown",
        )
        output = base64.b64decode(reply["stdout"], validate=True)
        error = base64.b64decode(reply["stderr"], validate=True)
        _require(
            len(output) <= _OUTPUT_LIMIT and len(error) <= _OUTPUT_LIMIT,
            "cohort_outcome_unknown",
        )
        self.state["last_result"] = {
            **pending,
            "exit_code": reply["exit_code"],
            "stdout_sha256": _sha(output),
            "stderr_sha256": _sha(error),
        }
        self.state["pending"] = None
        self._save()
        return {
            "id": request,
            "exit_code": reply["exit_code"],
            "stdout": output,
            "stderr": error,
        }

    def close_and_freeze(self, *, deadline: float) -> None:
        """Close genesis and suspend its exact tree before a filesystem fence.

        Suspension does not establish journal drain, process absence or fence
        completeness. Recovery retains the same closed generation and gate.
        """
        self._current()
        _require(
            type(deadline) in {int, float} and 0 < deadline - time.monotonic() < 3600,
            "cohort_deadline",
        )
        if self.state["phase"] != "retired":
            self.state["phase"] = "closed"
            self._save()
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self._file("cgroup.freeze", write="1")
        while not self.events()["frozen"]:
            _require(time.monotonic() < deadline, "cohort_freeze_unknown")
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        if self.state["phase"] != "retired":
            self.state["phase"] = "frozen"
            self._save()

    def retire(self, *, deadline: float) -> None:
        """Freeze/kill the exact whole tree; retain unknown mutation facts."""
        self.close_and_freeze(deadline=deadline)
        self._file("cgroup.kill", write="1")
        while self.events()["populated"]:
            _require(time.monotonic() < deadline, "cohort_retirement_unknown")
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        self.state["phase"] = "retired"
        self._save()
        if self.process is not None:
            self.process.wait(timeout=max(0.001, deadline - time.monotonic()))

    def close(self) -> None:
        """Release only borrowed kernel handles; never unfence or infer absence."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.group_fd >= 0:
            os.close(self.group_fd)
            self.group_fd = -1

    def __del__(self) -> None:
        self.close()


# This is a baseline restriction primitive, not a cold-provider/adoption proof.
# Later copy and release owners must publish their own exact evolving plans.
_FENCE_FORMAT = "linux-frozen-tree-fence-v1"
_BYTE_LOCK_PATHS = frozenset(
    {
        "runtime/managed-ingress/ingress.guard",
        "runtime/native-control/installation.guard",
    }
)


def _mount_id(descriptor: int) -> int:
    raw = Path(f"/proc/self/fdinfo/{descriptor}").read_text(encoding="ascii")
    rows = [line.split()[1] for line in raw.splitlines() if line.startswith("mnt_id:")]
    _require(len(rows) == 1 and rows[0].isdecimal(), "fence_mount")
    return int(rows[0])


def _open_object(name: str, *, parent: int) -> int:
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    _require(
        stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode),
        "fence_object_type",
    )
    descriptor = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW") | getattr(os, "O_NONBLOCK"),
        dir_fd=parent,
    )
    after = os.fstat(descriptor)
    if (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode)) != (
        after.st_dev,
        after.st_ino,
        stat.S_IFMT(after.st_mode),
    ):
        os.close(descriptor)
        raise Refused("fence_object_changed")
    return descriptor


def _root_fd(path: Path) -> int:
    _require(
        path.is_absolute()
        and path.anchor == "/"
        and path != Path("/")
        and ".." not in path.parts,
        "fence_root",
    )
    descriptor = os.open("/", os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        for name in path.parts[1:]:
            info = os.fstat(descriptor)
            _require(
                stat.S_ISDIR(info.st_mode)
                and info.st_uid == info.st_gid == 0
                and (not info.st_mode & 0o022 or bool(info.st_mode & stat.S_ISVTX))
                and not {"system.posix_acl_access", "system.posix_acl_default"}
                & set(getattr(os, "listxattr")(descriptor)),
                "fence_ancestor",
            )
            child = _open_object(name, parent=descriptor)
            os.close(descriptor)
            descriptor = child
        _require(stat.S_ISDIR(os.fstat(descriptor).st_mode), "fence_root")
        result, descriptor = descriptor, -1
        return result
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _object_fact(descriptor: int) -> dict[str, Any]:
    info = os.fstat(descriptor)
    kind = "directory" if stat.S_ISDIR(info.st_mode) else "file"
    _require(
        (kind == "directory" or stat.S_ISREG(info.st_mode))
        and (kind != "file" or info.st_nlink == 1),
        "fence_object_type",
    )
    _require(
        not {
            "system.posix_acl_access",
            "system.posix_acl_default",
            "security.capability",
        }
        & set(getattr(os, "listxattr")(descriptor)),
        "fence_object_acl",
    )
    return {
        "identity": [info.st_dev, info.st_ino, _mount_id(descriptor), info.st_nlink],
        "kind": kind,
        "rights": [info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)],
    }


class FrozenTreeFence:
    """Forward-only baseline DAC restriction of an exact suspended generation.

    This supplies no issuer attestation, N-actor completeness, domain readiness,
    adoption, publication or release authority. The independent owner must first
    reconcile every prior maintenance actor and keep all creators closed. There
    is deliberately no old-rights restore method or automatic boot recovery.
    """

    def __init__(
        self, directory: Path, cohort: ControlledCohort, state: dict[str, Any]
    ) -> None:
        self.directory, self.cohort, self.state = directory, cohort, state
        self._current()

    @staticmethod
    def _binding(cohort: ControlledCohort) -> dict[str, Any]:
        return {
            key: cohort.state[key]
            for key in (
                "platform",
                "gate",
                "token",
                "role",
                "uid",
                "gid",
                "profile",
                "group",
                "group_identity",
                "broker",
                "creator",
            )
        }

    @staticmethod
    def _scan(
        roots: list[dict[str, Any]],
        *,
        forbidden: set[tuple[int, int]] | None = None,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        identities: set[tuple[int, int]] = set()

        def walk(descriptor: int, index: int, relative: str, mount: int) -> None:
            info = os.fstat(descriptor)
            identity = (info.st_dev, info.st_ino)
            _require(
                forbidden is None or identity not in forbidden,
                "fence_private_alias",
            )
            fact = _object_fact(descriptor)
            _require(
                fact["identity"][2] == mount and identity not in identities,
                "fence_mount_or_alias",
            )
            identities.add(identity)
            result.append({"root": index, "relative": relative, **fact})
            if fact["kind"] == "directory":
                for name in sorted(os.listdir(descriptor)):
                    child = _open_object(name, parent=descriptor)
                    try:
                        walk(
                            child,
                            index,
                            name if relative == "." else relative + "/" + name,
                            mount,
                        )
                    finally:
                        os.close(child)

        for index, root in enumerate(roots):
            descriptor = _root_fd(Path(root["path"]))
            try:
                walk(descriptor, index, ".", _mount_id(descriptor))
            finally:
                os.close(descriptor)
        return result

    @classmethod
    def _management_identities(
        cls, directory: Path, cohort: ControlledCohort
    ) -> set[tuple[int, int]]:
        """Exclude management objects physically, including sole bind aliases.

        Checking the target root before descending also rejects an alias of a
        private ancestor without enumerating its unrelated contents. Targets
        and control roots remain distinct even when their mount IDs differ.
        """
        paths = {
            directory,
            cohort.directory,
            cohort.control.guard.parent,
            cohort.control.epoch_path.parent,
        }
        selected = [
            path
            for path in paths
            if not any(parent in paths for parent in path.parents)
        ]
        identities: set[tuple[int, int]] = set()
        for path in selected:
            _protected(path)
            for ancestor in (path, *path.parents):
                info = ancestor.lstat()
                identities.add((info.st_dev, info.st_ino))
        for row in cls._scan([{"path": str(path)} for path in selected]):
            identities.add(tuple(row["identity"][:2]))
        # The kernel control namespace is also outside replacement roots. Its
        # write-only files need stat, not read-open, for physical exclusion.
        for ancestor in (cohort.group, *cohort.group.parents):
            info = ancestor.lstat()
            identities.add((info.st_dev, info.st_ino))

        def kernel_objects(descriptor: int) -> None:
            info = os.fstat(descriptor)
            identities.add((info.st_dev, info.st_ino))
            for name in os.listdir(descriptor):
                item = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                _require(
                    stat.S_ISDIR(item.st_mode) or stat.S_ISREG(item.st_mode),
                    "fence_private_kernel_object",
                )
                identities.add((item.st_dev, item.st_ino))
                if stat.S_ISDIR(item.st_mode):
                    child = os.open(
                        name,
                        os.O_RDONLY
                        | getattr(os, "O_DIRECTORY")
                        | getattr(os, "O_NOFOLLOW"),
                        dir_fd=descriptor,
                    )
                    try:
                        actual = os.fstat(child)
                        _require(
                            (actual.st_dev, actual.st_ino)
                            == (item.st_dev, item.st_ino),
                            "fence_private_kernel_object",
                        )
                        kernel_objects(child)
                    finally:
                        os.close(child)

        kernel_objects(cohort.group_fd)
        return identities

    @classmethod
    def plan(
        cls,
        directory: Path,
        cohort: ControlledCohort,
        *,
        roots: Mapping[Path, str],
        maintenance_uid: int,
        maintenance_gid: int,
        byte_locks: tuple[Path, ...] = (),
        executables: tuple[Path, ...] = (),
    ) -> FrozenTreeFence:
        """Freeze exact before/intermediate/after images before any DAC write."""
        cohort._current()
        _protected(directory)
        _require(
            cohort.state["role"] in {"legacy", "successor"}
            and cohort.state["broker"] is not None
            and cohort.state["phase"] in {"frozen", "retired"}
            and cohort.events()["frozen"] == 1,
            "fence_generation_not_frozen",
        )
        _require(
            type(maintenance_uid) is int
            and type(maintenance_gid) is int
            and 0 < maintenance_uid < 2**32 - 1
            and 0 < maintenance_gid < 2**32 - 1
            and maintenance_uid != cohort.state["uid"]
            and maintenance_gid != cohort.state["gid"],
            "fence_credentials",
        )
        selected = [{"path": str(path), "kind": kind} for path, kind in roots.items()]
        _require(bool(selected), "fence_roots")
        paths = [Path(row["path"]) for row in selected]
        protected = (
            directory,
            cohort.directory,
            cohort.control.guard.parent,
            cohort.control.epoch_path.parent,
        )
        _require(
            all(
                path.is_absolute()
                and path.anchor == "/"
                and path != Path("/")
                and ".." not in path.parts
                and selected[index]["kind"] in {"core", "data"}
                and all(
                    path != private
                    and path not in private.parents
                    and private not in path.parents
                    for private in protected
                )
                and all(
                    path != other
                    and path not in other.parents
                    and other not in path.parents
                    for other in paths[index + 1 :]
                )
                for index, path in enumerate(paths)
            ),
            "fence_roots",
        )
        _require(
            len(byte_locks) == len(set(byte_locks))
            and len(executables) == len(set(executables))
            and not set(byte_locks) & set(executables),
            "fence_role_map",
        )
        rows = cls._scan(
            selected, forbidden=cls._management_identities(directory, cohort)
        )
        seen_locks: set[Path] = set()
        seen_executables: set[Path] = set()
        for row in rows:
            root = selected[row["root"]]
            path = Path(root["path"]) / row["relative"]
            before = row.pop("rights")
            _require(
                before[0] in {0, cohort.state["uid"]}
                and before[1] in {0, cohort.state["gid"]}
                and not before[2] & 0o7002
                and (not before[2] & 0o020 or before[1] == cohort.state["gid"]),
                "fence_before_rights",
            )
            if root["kind"] == "core":
                owner, group = 0, maintenance_gid
                mode = 0o750 if row["kind"] == "directory" else 0o640
                if path in byte_locks:
                    _require(
                        row["kind"] == "file" and row["relative"] in _BYTE_LOCK_PATHS,
                        "fence_role_map",
                    )
                    mode = 0o660
                    seen_locks.add(path)
                if path in executables:
                    _require(row["kind"] == "file", "fence_role_map")
                    mode = 0o750
                    seen_executables.add(path)
            else:
                owner, group = maintenance_uid, maintenance_gid
                mode = 0o700 if row["kind"] == "directory" else 0o600
            after = [owner, group, mode]
            row.update(
                before=before,
                after=after,
                allowed=[before, [before[0], before[1], 0], [owner, group, 0], after],
            )
        _require(
            seen_locks == set(byte_locks) and seen_executables == set(executables),
            "fence_role_map",
        )
        plan = {
            "format": _FENCE_FORMAT,
            "transaction": uuid4().hex,
            "binding": cls._binding(cohort),
            "roots": selected,
            "rows": rows,
            "maintenance": [maintenance_uid, maintenance_gid],
        }
        state = {"plan": plan, "sha256": _sha(_canonical(plan)), "complete": False}
        path = directory / "fence.json"
        _require(not path.exists(), "fence_already_planned")
        _atomic(path, state)
        return cls(directory, cohort, state)

    @classmethod
    def reopen(cls, directory: Path, cohort: ControlledCohort) -> FrozenTreeFence:
        return cls(directory, cohort, _read(directory / "fence.json"))

    def _current(self) -> None:
        self.cohort._current()
        _protected(self.directory)
        plan = self.state["plan"]
        _require(
            _read(self.directory / "fence.json") == self.state
            and plan["format"] == _FENCE_FORMAT
            and _sha(_canonical(plan)) == self.state["sha256"]
            and plan["binding"] == self._binding(self.cohort)
            and self.cohort.state["phase"] in {"frozen", "retired"}
            and self.cohort.events()["frozen"] == 1
            and (
                self.cohort.state["phase"] != "retired"
                or self.cohort.events()["populated"] == 0
            ),
            "fence_state_changed",
        )

    def _validate(self, *, complete: bool) -> None:
        self._current()
        rows = self.state["plan"]["rows"]
        observed = self._scan(
            self.state["plan"]["roots"],
            forbidden=self._management_identities(self.directory, self.cohort),
        )
        _require(len(rows) == len(observed), "fence_membership_changed")
        for expected, actual in zip(rows, observed, strict=True):
            _require(
                all(
                    expected[key] == actual[key]
                    for key in ("root", "relative", "identity", "kind")
                )
                and (
                    actual["rights"] == expected["after"]
                    if complete
                    else actual["rights"] in expected["allowed"]
                ),
                "fence_object_changed",
            )

    def _descriptor(self, row: dict[str, Any]) -> int:
        root = self.state["plan"]["roots"][row["root"]]
        descriptor = _root_fd(Path(root["path"]))
        try:
            if row["relative"] != ".":
                for name in Path(row["relative"]).parts:
                    child = _open_object(name, parent=descriptor)
                    os.close(descriptor)
                    descriptor = child
            fact = _object_fact(descriptor)
            _require(
                fact["identity"] == row["identity"]
                and fact["kind"] == row["kind"]
                and fact["rights"] in row["allowed"],
                "fence_object_changed",
            )
            result, descriptor = descriptor, -1
            return result
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def apply(
        self, *, checkpoint: Callable[[int, str], None] = lambda _row, _stage: None
    ) -> None:
        """Resume only this frozen plan's exact images; never undo inhibition."""
        self._validate(complete=self.state["complete"])
        if self.state["complete"]:
            return
        for index, row in enumerate(self.state["plan"]["rows"]):
            descriptor = self._descriptor(row)
            try:
                if _object_fact(descriptor)["rights"] == row["after"]:
                    continue
                getattr(os, "fchmod")(descriptor, 0)
                os.fsync(descriptor)
                checkpoint(index, "zero")
                getattr(os, "fchown")(descriptor, row["after"][0], row["after"][1])
                os.fsync(descriptor)
                checkpoint(index, "owner")
                getattr(os, "fchmod")(descriptor, row["after"][2])
                os.fsync(descriptor)
                checkpoint(index, "final")
                _require(
                    _object_fact(descriptor)["rights"] == row["after"],
                    "fence_object_changed",
                )
            finally:
                os.close(descriptor)
        self._validate(complete=True)
        self.state["complete"] = True
        _atomic(self.directory / "fence.json", self.state)

    def verify(self) -> None:
        """Verify an already complete baseline; no content/adoption claim."""
        _require(self.state["complete"] is True, "fence_incomplete")
        self._validate(complete=True)
