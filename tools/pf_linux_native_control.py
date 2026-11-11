"""Linux namespace containment with a pre-target ownership publication barrier.

This stdlib-only adapter is loaded by the accepted native image. The helper runs
captured source in an isolated interpreter; it never imports Core or a disk leaf.
"""

from __future__ import annotations

import json
import os
import re
import select
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

ENVIRONMENT = "PF_NATIVE_NAMESPACE"
TOKEN_ENVIRONMENT = "PF_NATIVE_NAMESPACE_TOKEN"
_TREE = re.compile(
    r"linux-pidns-v1:([a-f0-9]{32}):([1-9][0-9]*):([1-9][0-9]*):([1-9][0-9]*):([1-9][0-9]*)\Z"
)
_BIRTH = re.compile(r"linux-start:([a-f0-9-]{36}):([1-9][0-9]*)\Z")
_LIMIT = 65536


class LinuxControlError(OSError):
    """Keep the existing failure code and expose the actual Linux refusal reason."""

    code = "execution_activity_unknown"

    def __init__(self, reason: str = "linux_ownership_unverifiable") -> None:
        self.reason = reason
        super().__init__(reason)


def validate_tree_id(value: Any, token: str) -> bool:
    """Validate the token-bound, versioned identifier without observing processes."""
    match = _TREE.fullmatch(value) if isinstance(value, str) else None
    return (
        match is not None
        and match[1] == token
        and all(len(match[index]) <= 20 for index in range(2, 6))
        and int(match[2]) <= 0x7FFFFFFF
        and all(int(match[index]) <= 0xFFFFFFFFFFFFFFFF for index in range(3, 6))
    )


def _boot() -> str:
    value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9-]{36}", value):
        raise LinuxControlError()
    # An unavailable or differently mounted procfs is not evidence of death.
    if int(Path("/proc/self/stat").read_text().split(" ", 1)[0]) != os.getpid():
        raise LinuxControlError("linux_controller_procfs_mismatch")
    return value


def _ticks(pid: int) -> str:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    fields = raw[raw.rindex(")") + 2 :].split()
    value = fields[19]
    if not value.isdecimal() or int(value) < 1:
        raise LinuxControlError()
    return value


def _ready(descriptor: int | None) -> bool:
    return descriptor is None or bool(select.select([descriptor], [], [], 0)[0])


def _retain(pid: int, ticks: str) -> int | None:
    try:
        descriptor = getattr(os, "pidfd_open")(pid)
    except ProcessLookupError:
        return None
    try:
        if _ticks(pid) != ticks:
            raise LinuxControlError("linux_process_birth_mismatch")
        return descriptor
    except FileNotFoundError:
        exited = _ready(descriptor)
        os.close(descriptor)
        if exited:
            return None
        raise LinuxControlError("linux_process_observation_unavailable") from None
    except BaseException:
        os.close(descriptor)
        raise


class OwnedNamespace:
    """Retain exact carrier/init pidfds; never signal a PID obtained by scanning."""

    def __init__(self, facts: dict[str, Any]) -> None:
        self.carrier: int | None = None
        self.init: int | None = None
        self.facts = facts
        self.name = facts["job_name"]
        self.closed = False
        try:
            birth = _BIRTH.fullmatch(facts["birth_id"])
            tree = _TREE.fullmatch(self.name)
            if (
                birth is None
                or tree is None
                or not validate_tree_id(self.name, tree[1])
                or _boot() != birth[1]
            ):
                raise LinuxControlError()
            self.carrier = _retain(facts["pid"], birth[2])
            self.init = _retain(int(tree[2]), tree[3])
            marker = f"{TOKEN_ENVIRONMENT}={tree[1]}".encode()
            if self.carrier is not None and not _ready(self.carrier):
                carrier = Path(f"/proc/{facts['pid']}")
                with (carrier / "environ").open("rb") as stream:
                    environment = stream.read(1024 * 1024 + 1)
                if (
                    len(environment) > 1024 * 1024
                    or marker not in environment.split(b"\0")
                    or os.readlink(carrier / "ns/user") != f"user:[{tree[5]}]"
                ):
                    raise LinuxControlError()
            if self.init is not None and not _ready(self.init):
                base = Path(f"/proc/{tree[2]}")
                if (
                    os.readlink(base / "ns/pid") != f"pid:[{tree[4]}]"
                    or os.readlink(base / "ns/user") != f"user:[{tree[5]}]"
                ):
                    raise LinuxControlError()
                status = (base / "status").read_text(encoding="ascii")
                if (
                    next(
                        line
                        for line in status.splitlines()
                        if line.startswith("NSpid:")
                    ).split()[-1]
                    != "1"
                ):
                    raise LinuxControlError()
                with (base / "environ").open("rb") as stream:
                    environment = stream.read(1024 * 1024 + 1)
                if len(environment) > 1024 * 1024 or marker not in environment.split(
                    b"\0"
                ):
                    raise LinuxControlError()
                # Recheck after the membership reads; a retained pidfd is the
                # signalling authority, never the pathname used for validation.
                if _ticks(int(tree[2])) != tree[3]:
                    raise LinuxControlError()
        except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration):
            self.close()
            raise LinuxControlError() from None

    def active(self) -> int:
        if self.closed:
            raise LinuxControlError()
        return int(not (_ready(self.carrier) and _ready(self.init)))

    def stop(self, *, deadline: float) -> bool:
        if self.closed:
            raise LinuxControlError()
        if self.init is not None and not _ready(self.init):
            try:
                getattr(signal, "pidfd_send_signal")(
                    self.init, getattr(signal, "SIGKILL")
                )
            except ProcessLookupError:
                pass  # This exact retained kernel object already exited.
        while self.active():
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        return True

    def close(self) -> None:
        for name in ("carrier", "init"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)
        self.closed = True

    def __del__(self) -> None:
        self.close()


def reopen(
    facts: dict[str, Any], *, pid: int, identity: dict[str, Any]
) -> OwnedNamespace:
    """Authenticate persisted native facts before reopening exact kernel objects."""
    if (
        set(facts) != {"schema_version", "pid", "birth_id", "job_name", "identity"}
        or type(facts["schema_version"]) is not int
        or facts["schema_version"] != 1
        or type(pid) is not int
        or pid < 1
        or pid > 0x7FFFFFFF
        or type(facts["pid"]) is not int
        or facts["pid"] != pid
        or facts["identity"] != identity
        or not isinstance(facts["birth_id"], str)
        or not isinstance(facts["job_name"], str)
    ):
        raise LinuxControlError()
    return OwnedNamespace(facts)


def inherited(environment: dict[str, str]) -> dict[str, Any] | None:
    """Validate current membership; environment text alone grants no ownership."""
    value = environment.get(ENVIRONMENT)
    if value is None:
        return None
    try:
        facts = json.loads(value)
        tree = _TREE.fullmatch(facts["job_name"])
        birth = _BIRTH.fullmatch(facts["birth_id"])
        if (
            tree is None
            or birth is None
            or not validate_tree_id(facts["job_name"], tree[1])
            or (
                os.readlink("/proc/self/ns/pid") != f"pid:[{tree[4]}]"
                or os.readlink("/proc/self/ns/user") != f"user:[{tree[5]}]"
                or environment.get(TOKEN_ENVIRONMENT) != tree[1]
                or Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                != birth[1]
                or _ticks(facts["pid"]) != birth[2]
                or _ticks(int(tree[2])) != tree[3]
            )
        ):
            raise LinuxControlError()
        raw = Path(f"/proc/{tree[2]}/stat").read_text()
        if int(raw[raw.rindex(")") + 2 :].split()[1]) != facts["pid"]:
            raise LinuxControlError()
        return facts
    except (OSError, ValueError, KeyError, TypeError):
        raise LinuxControlError() from None


def identity_facts(process: Any) -> dict[str, Any]:
    """Adapt an already authenticated execution identity to the native leaf shape."""
    if not isinstance(process.birth_id, str) or not process.birth_id.startswith(
        "linux-start-ticks:"
    ):
        raise LinuxControlError()
    return {
        "schema_version": 1,
        "pid": process.pid,
        "birth_id": f"linux-start:{process.boot_id}:{process.birth_id.split(':', 1)[1]}",
        "job_name": process.tree_id,
        "identity": {},
    }


# The child source is a constant in the accepted module image. No mutable module
# or utility executable is opened by the child to construct its containment.
_HELPER = r"""
import ctypes, json, os, select, signal, socket, subprocess, sys
from pathlib import Path

control = socket.socket(fileno=int(sys.argv[1]))
control.settimeout(10)
child = None
init_fd = None
gate_write = None
try:
    packet = json.loads(control.recv(65537))
    uid, gid = os.getuid(), os.getgid()
    carrier = os.getpid()
    def ticks(pid):
        raw = Path(f"/proc/{pid}/stat").read_text()
        return raw[raw.rindex(")") + 2:].split()[19]
    birth = "linux-start:" + Path("/proc/sys/kernel/random/boot_id").read_text().strip() + ":" + ticks(carrier)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.unshare(0x10000000 | 0x20000000) != 0:
        raise OSError(ctypes.get_errno(), "linux_user_pid_namespace_unavailable")
    Path("/proc/self/uid_map").write_text(f"0 {uid} 1\n")
    Path("/proc/self/setgroups").write_text("deny\n")
    Path("/proc/self/gid_map").write_text(f"0 {gid} 1\n")
    parent_fd = os.pidfd_open(carrier)
    gate_read, gate_write = os.pipe()
    child = os.fork()
    if child == 0:
        control.close()
        os.close(gate_write)
        # Install lifetime protection before readiness, then close the race in
        # which the carrier died before prctl by querying its inherited pidfd.
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
            os._exit(125)
        if select.select([parent_fd], [], [], 0)[0]:
            os._exit(125)
        os.close(parent_fd)
        with os.fdopen(gate_read, "r") as gate:
            facts = json.loads(gate.readline(65537))
        environment = packet["environment"]
        environment["PF_NATIVE_NAMESPACE_TOKEN"] = packet["token"]
        environment["PF_NATIVE_NAMESPACE"] = json.dumps(facts, separators=(",", ":"))
        target = subprocess.Popen(packet["argv"], env=environment, pass_fds=tuple(packet["pass_fds"]))
        root_code = None
        while True:
            try:
                pid, status = os.waitpid(-1, 0)
            except ChildProcessError:
                break
            if pid == target.pid:
                root_code = os.waitstatus_to_exitcode(status)
                target.returncode = root_code
        os._exit(root_code if root_code is not None and root_code >= 0 else 125)
    os.close(gate_read)
    os.close(parent_fd)
    init_fd = os.pidfd_open(child)
    pidns = os.readlink(f"/proc/{child}/ns/pid").split("[")[1][:-1]
    userns = os.readlink(f"/proc/{child}/ns/user").split("[")[1][:-1]
    facts = {"schema_version": 1, "pid": carrier, "birth_id": birth,
             "job_name": f"linux-pidns-v1:{packet['token']}:{child}:{ticks(child)}:{pidns}:{userns}",
             "identity": packet["identity"]}
    control.send(json.dumps(facts).encode())
    if control.recv(16) != b"GO":
        raise OSError("linux_launch_not_committed")
    with os.fdopen(gate_write, "w") as gate:
        gate_write = None
        gate.write(json.dumps(facts) + "\n")
    control.close()
    _, status = os.waitpid(child, 0)
    child = None
    code = os.waitstatus_to_exitcode(status)
    os.close(init_fd)
    init_fd = None
    sys.exit(code if code >= 0 else 128 - code)
except BaseException as error:
    if isinstance(error, SystemExit):
        raise
    try:
        control.send(json.dumps({"error": str(error)}).encode())
    except OSError:
        pass
    if init_fd is not None:
        try:
            signal.pidfd_send_signal(init_fd, signal.SIGKILL)
            os.waitpid(child, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
    sys.exit(125)
"""


def spawn(
    argv: list[str],
    *,
    token: str | None = None,
    receipt_path: Path | None = None,
    identity: dict[str, Any] | None = None,
    **options: Any,
) -> subprocess.Popen[bytes]:
    """Publish exact ownership before releasing the target from its GO barrier."""
    current = inherited(dict(os.environ))
    if current is not None:
        if token is not None or receipt_path is not None or identity is not None:
            raise LinuxControlError("linux_nested_owned_launch_unsupported")
        supplied = options.pop("env", None)
        environment = dict(os.environ if supplied is None else supplied)
        environment[ENVIRONMENT] = os.environ[ENVIRONMENT]
        environment[TOKEN_ENVIRONMENT] = os.environ[TOKEN_ENVIRONMENT]
        return subprocess.Popen(argv, env=environment, **options)
    if (
        not sys.platform.startswith("linux")
        or not hasattr(os, "pidfd_open")
        or not hasattr(signal, "pidfd_send_signal")
    ):
        raise LinuxControlError("linux_pidfd_unavailable")
    _boot()
    value = token or uuid4().hex
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise LinuxControlError("linux_launch_token_invalid")
    if options.get("shell") or options.get("preexec_fn") is not None:
        raise LinuxControlError("linux_launch_option_unsupported")
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    process: subprocess.Popen[bytes] | None = None
    job: OwnedNamespace | None = None
    try:
        supplied = options.pop("env", None)
        environment = dict(os.environ if supplied is None else supplied)
        environment.pop(ENVIRONMENT, None)
        environment[TOKEN_ENVIRONMENT] = value
        # Target loader settings may execute arbitrary code before Python main.
        # The trusted carrier receives only a fixed interpreter environment;
        # target environment travels over the private socket until after GO.
        carrier_environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            TOKEN_ENVIRONMENT: value,
        }
        forwarded = tuple(options.pop("pass_fds", ()))
        options.setdefault("start_new_session", True)
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", _HELPER, str(child.fileno())],
            env=carrier_environment,
            pass_fds=(*forwarded, child.fileno()),
            **options,
        )
        child.close()
        parent.settimeout(10)
        packet = json.dumps(
            {
                "argv": argv,
                "token": value,
                "identity": identity or {},
                "pass_fds": forwarded,
                "environment": environment,
            }
        ).encode()
        if len(packet) > _LIMIT:
            raise LinuxControlError("linux_launch_packet_too_large")
        parent.send(packet)
        raw = parent.recv(_LIMIT + 1)
        if not raw:
            raise LinuxControlError("linux_helper_unavailable")
        if len(raw) > _LIMIT:
            raise LinuxControlError()
        facts = json.loads(raw)
        if "error" in facts:
            raise LinuxControlError(str(facts["error"]))
        job = reopen(facts, pid=process.pid, identity=identity or {})
        if not validate_tree_id(job.name, value) or job.active() == 0:
            raise LinuxControlError()
        if receipt_path is not None:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = receipt_path.with_name(
                "." + receipt_path.name + "." + uuid4().hex
            )
            try:
                with temporary.open("x", encoding="utf-8") as stream:
                    stream.write(json.dumps(facts, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, receipt_path)
                directory = os.open(receipt_path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                temporary.unlink(missing_ok=True)
        setattr(process, "native_job", job)
        setattr(process, "native_facts", facts)
        parent.send(b"GO")
        return process
    except (OSError, ValueError, KeyError, TypeError):
        parent.close()  # EOF before GO cannot execute target code.
        if job is not None:
            job.stop(deadline=time.monotonic() + 5)
            job.close()
        if process is not None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        raise
    finally:
        parent.close()
        child.close()
