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
    _require(path.is_absolute(), "cohort_directory")
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


def _read(path: Path) -> dict[str, Any]:
    _protected(path.parent)
    info = path.lstat()
    _require(
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == info.st_gid == 0
        and stat.S_IMODE(info.st_mode) == 0o600,
        "cohort_state",
    )
    value = native._read(path, _PACKET_LIMIT)
    _require(isinstance(value, dict), "cohort_state")
    return value


def _held(control: native.NativeControl) -> dict[str, Any]:
    _platform()
    _protected(control.guard.parent)
    _protected(control.epoch_path.parent)
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

    def retire(self, *, deadline: float) -> None:
        """Close creators, freeze/kill the exact whole tree; retain unknown facts."""
        self._current()
        _require(
            type(deadline) in {int, float} and 0 < deadline - time.monotonic() < 3600,
            "cohort_deadline",
        )
        self.state["phase"] = "closed"
        self._save()
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self._file("cgroup.freeze", write="1")
        while not self.events()["frozen"]:
            _require(time.monotonic() < deadline, "cohort_freeze_unknown")
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
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
