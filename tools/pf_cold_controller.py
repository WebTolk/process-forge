"""Finite Windows cold controller; no target Core imports.

Only trusted maintenance code may construct a deployment. No profile is qualified
by this source. Real positive retirement requires a separately qualified exact
Windows build and protected deployment namespace. Fixture observations are not
platform qualification. Do not invoke against a live installation in this Work.
"""

from __future__ import annotations

import ctypes
import io
import os
import re
import stat
import sys
import threading
import zipfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from ctypes import wintypes as w
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pf_native_control as p


class Refused(p.NativeControlError):
    """Private refusal; integration retains existing public error surfaces."""


def require(condition: bool) -> None:
    if not condition:
        raise Refused()


def identity(path: Path) -> list[int]:
    """Check every ancestor without resolving away reparse points first."""
    require(path.is_absolute())
    for item in (path, *path.parents):
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode))
        require(not getattr(info, "st_file_attributes", 0) & 0x400)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
    require(stat.S_ISDIR(info.st_mode) or info.st_nlink == 1)
    return [info.st_dev, info.st_ino]


def tree(root: Path) -> tuple[Path, ...]:
    """Metadata only; refuse reparse/hardlinked payload instead of following it."""
    identity(root)
    items = [root]
    for directory, names, files in os.walk(root, followlinks=False):
        for name in sorted([*names, *files]):
            child = Path(directory) / name
            identity(child)
            items.append(child)
    return tuple(sorted(items, key=lambda item: str(item).casefold()))


def read(path: Path) -> dict[str, Any]:
    value = p.json.loads(
        p._read_regular(path.parent, path.name, 64 * 1024 * 1024),
        object_pairs_hook=p._pairs,
        parse_constant=p._no_number,
    )
    require(isinstance(value, dict))
    return value


def atomic(path: Path, value: dict[str, Any]) -> None:
    raw = p.canonical_json(value)
    require(len(raw) <= 64 * 1024 * 1024)
    temporary = path.with_name("." + path.name + "." + p.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sid_string(value: str) -> str:
    require(bool(re.fullmatch(r"S-1-(?:[0-9]+-)*[0-9]+", value)))
    return value


class Windows:
    """Checked native APIs. Mutators are used only on fixtures by this Work."""

    def __init__(self) -> None:
        require(os.name == "nt")
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.a = ctypes.WinDLL("advapi32", use_last_error=True)
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        declarations = (
            (self.k, "GetTickCount64", (), ctypes.c_uint64),
            (self.k, "GetCurrentProcess", (), w.HANDLE),
            (self.k, "GetCurrentThread", (), w.HANDLE),
            (self.k, "CloseHandle", (w.HANDLE,), w.BOOL),
            (self.k, "LocalFree", (ctypes.c_void_p,), ctypes.c_void_p),
            (self.u, "GetSystemMetrics", (ctypes.c_int,), ctypes.c_int),
            (
                self.a,
                "OpenProcessToken",
                (w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)),
                w.BOOL,
            ),
            (
                self.a,
                "OpenThreadToken",
                (w.HANDLE, w.DWORD, w.BOOL, ctypes.POINTER(w.HANDLE)),
                w.BOOL,
            ),
            (
                self.a,
                "GetTokenInformation",
                (
                    w.HANDLE,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    w.DWORD,
                    ctypes.POINTER(w.DWORD),
                ),
                w.BOOL,
            ),
            (
                self.a,
                "DuplicateToken",
                (w.HANDLE, ctypes.c_int, ctypes.POINTER(w.HANDLE)),
                w.BOOL,
            ),
            (
                self.a,
                "ConvertSidToStringSidW",
                (ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)),
                w.BOOL,
            ),
            (
                self.a,
                "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                (
                    w.LPCWSTR,
                    w.DWORD,
                    ctypes.POINTER(ctypes.c_void_p),
                    ctypes.POINTER(w.DWORD),
                ),
                w.BOOL,
            ),
            (
                self.a,
                "ConvertSecurityDescriptorToStringSecurityDescriptorW",
                (
                    ctypes.c_void_p,
                    w.DWORD,
                    w.DWORD,
                    ctypes.POINTER(w.LPWSTR),
                    ctypes.POINTER(w.DWORD),
                ),
                w.BOOL,
            ),
            (
                self.a,
                "GetFileSecurityW",
                (w.LPCWSTR, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)),
                w.BOOL,
            ),
            (
                self.a,
                "SetFileSecurityW",
                (w.LPCWSTR, w.DWORD, ctypes.c_void_p),
                w.BOOL,
            ),
            (
                self.a,
                "AccessCheck",
                (
                    ctypes.c_void_p,
                    w.HANDLE,
                    w.DWORD,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    ctypes.POINTER(w.DWORD),
                    ctypes.POINTER(w.DWORD),
                    ctypes.POINTER(w.BOOL),
                ),
                w.BOOL,
            ),
            (
                self.a,
                "LookupPrivilegeNameW",
                (w.LPCWSTR, ctypes.c_void_p, w.LPWSTR, ctypes.POINTER(w.DWORD)),
                w.BOOL,
            ),
        )
        for library, name, arguments, result in declarations:
            function = getattr(library, name)
            function.argtypes, function.restype = arguments, result

    def checked(self, result: Any) -> None:
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())

    @contextmanager
    def process_token(self) -> Iterator[int]:
        handle = w.HANDLE()
        if not self.a.OpenThreadToken(
            self.k.GetCurrentThread(), 0xA, True, ctypes.byref(handle)
        ):
            require(ctypes.get_last_error() == 1008)  # ERROR_NO_TOKEN only.
            self.checked(
                self.a.OpenProcessToken(
                    self.k.GetCurrentProcess(), 0xA, ctypes.byref(handle)
                )
            )
        try:
            if handle.value is None:
                raise Refused()
            yield int(handle.value)
        finally:
            self.k.CloseHandle(handle)

    def token_info(self, token: int, kind: int) -> Any:
        needed = w.DWORD()
        self.a.GetTokenInformation(token, kind, None, 0, ctypes.byref(needed))
        require(0 < needed.value <= 65536)
        buffer = ctypes.create_string_buffer(needed.value)
        self.checked(
            self.a.GetTokenInformation(
                token, kind, buffer, needed, ctypes.byref(needed)
            )
        )
        return buffer

    def token_sid(self, token: int) -> str:
        buffer = self.token_info(token, 1)
        pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = w.LPWSTR()
        self.checked(self.a.ConvertSidToStringSidW(pointer, ctypes.byref(text)))
        try:
            return str(text.value)
        finally:
            self.k.LocalFree(text)

    def privileges(self, token: int) -> set[str]:
        class Privilege(ctypes.Structure):
            _fields_ = [("luid", ctypes.c_int64), ("flags", w.DWORD)]

        class Privileges(ctypes.Structure):
            _fields_ = [("count", w.DWORD), ("items", Privilege * 1)]

        buffer = self.token_info(token, 3)
        header = ctypes.cast(buffer, ctypes.POINTER(Privileges)).contents
        require(header.count < 1024)
        # LUID_AND_ATTRIBUTES has DWORD alignment, not the host's int64 alignment.
        base = ctypes.addressof(buffer) + 4
        result = set()
        for index in range(header.count):
            address = base + index * 12
            length = w.DWORD(256)
            name = ctypes.create_unicode_buffer(length.value)
            self.checked(
                self.a.LookupPrivilegeNameW(None, address, name, ctypes.byref(length))
            )
            result.add(name.value)
        return result

    def descriptor(self, path: Path) -> Any:
        identity(path)
        needed = w.DWORD()
        self.a.GetFileSecurityW(str(path), 7, None, 0, ctypes.byref(needed))
        require(0 < needed.value <= 65536)
        buffer = ctypes.create_string_buffer(needed.value)
        self.checked(
            self.a.GetFileSecurityW(str(path), 7, buffer, needed, ctypes.byref(needed))
        )
        return buffer

    def sddl(self, path: Path) -> str:
        descriptor = self.descriptor(path)
        text, length = w.LPWSTR(), w.DWORD()
        self.checked(
            self.a.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                descriptor, 1, 5, ctypes.byref(text), ctypes.byref(length)
            )
        )
        try:
            return str(text.value)
        finally:
            self.k.LocalFree(text)

    def set_sddl(self, path: Path, value: str, *, owner: bool = True) -> None:
        identity(path)
        descriptor = ctypes.c_void_p()
        self.checked(
            self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                value, 1, ctypes.byref(descriptor), None
            )
        )
        try:
            # Protected DACL; no propagation claim for pre-existing descendants.
            self.checked(
                self.a.SetFileSecurityW(
                    str(path), 0x80000004 | (1 if owner else 0), descriptor
                )
            )
        finally:
            self.k.LocalFree(descriptor)

    def access(self, path: Path, token: int) -> int:
        return self.access_descriptor(self.descriptor(path), token)

    def access_sddl(self, value: str, token: int) -> int:
        descriptor = ctypes.c_void_p()
        self.checked(
            self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                value, 1, ctypes.byref(descriptor), None
            )
        )
        try:
            return self.access_descriptor(descriptor, token)
        finally:
            self.k.LocalFree(descriptor)

    def access_descriptor(self, descriptor: Any, token: int) -> int:
        class Mapping(ctypes.Structure):
            _fields_ = [(name, w.DWORD) for name in ("read", "write", "execute", "all")]

        mapping = Mapping(0x120089, 0x120116, 0x1200A0, 0x1F01FF)
        duplicated = w.HANDLE()
        self.checked(self.a.DuplicateToken(token, 2, ctypes.byref(duplicated)))
        try:
            privileges = ctypes.create_string_buffer(65536)
            size, granted, allowed = w.DWORD(65536), w.DWORD(), w.BOOL()
            self.checked(
                self.a.AccessCheck(
                    descriptor,
                    duplicated,
                    0x02000000,
                    ctypes.byref(mapping),
                    privileges,
                    ctypes.byref(size),
                    ctypes.byref(granted),
                    ctypes.byref(allowed),
                )
            )
            return granted.value if allowed else 0
        finally:
            self.k.CloseHandle(duplicated)

    def sample(self) -> dict[str, Any]:
        version = sys.getwindowsversion()
        before = int(self.k.GetTickCount64())
        checked = bool(self.u.GetSystemMetrics(22))
        after = int(self.k.GetTickCount64())
        require(before <= after < 2**63)
        return {
            "low": before,
            "high": after,
            "checked": checked,
            "version": [version.major, version.minor, version.build],
        }


@dataclass(frozen=True)
class Policy:
    """Trusted bundle policy, never request data. Empty qualified set is closed."""

    maintenance_sid: str
    normal_sids: tuple[str, ...]
    qualified_versions: tuple[tuple[int, int, int], ...] = ()
    qualification_sha256: str = ""

    def document(self) -> dict[str, Any]:
        require(bool(self.normal_sids))
        sid_string(self.maintenance_sid)
        require(self.maintenance_sid != "S-1-5-18")
        for sid in self.normal_sids:
            sid_string(sid)
            require(sid not in {self.maintenance_sid, "S-1-5-18"})
        require(len(set(self.normal_sids)) == len(self.normal_sids))
        return {
            "maintenance": self.maintenance_sid,
            "normal": list(self.normal_sids),
            "versions": [list(row) for row in self.qualified_versions],
            "qualification": self.qualification_sha256,
        }

    def sddl(self) -> str:
        self.document()
        return f"O:{self.maintenance_sid}D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;{self.maintenance_sid})"

    def eligible(self, sample: dict[str, Any]) -> None:
        require(bool(re.fullmatch(r"sha256:[a-f0-9]{64}", self.qualification_sha256)))
        require(set(sample) == {"low", "high", "checked", "version"})
        require(type(sample["checked"]) is bool and not sample["checked"])
        require(type(sample["low"]) is int and type(sample["high"]) is int)
        require(0 <= sample["low"] <= sample["high"] < 2**63)
        require(tuple(sample["version"]) in self.qualified_versions)


def retirement(
    before: dict[str, Any], after: dict[str, Any], policy: Policy
) -> dict[str, Any]:
    """Sufficient counter-reset candidate, not a general changed-boot detector.

    Native elapsed tick includes sleep/hibernation per supplied Microsoft notes.
    An actual post-reset value must be strictly below the protected pre-fence
    lower observation by 60 seconds. Delayed restart may therefore refuse. No
    positive production observation is enabled without qualified exact builds.
    """
    for sample in (before, after):
        policy.eligible(sample)
    require(before["version"] == after["version"])
    require(after["high"] + 60000 < before["low"])
    return {
        "kind": "qualified-native-tick-reset-v1",
        "before": before,
        "after": after,
        "qualification": policy.qualification_sha256,
    }


class Fence:
    """Persistent all-object deny-by-allowlist, with real normal-token checks.

    Deployment owns exact roots, ancestors and tokens. Normal tokens may not
    carry maintenance/SYSTEM membership or privilege bypass. All unrelated
    administrators, copied payloads and snapshot rollback are outside trust.
    No inventory/profile discovery or host configuration edits are performed.
    """

    def __init__(
        self,
        windows: Windows,
        policy: Policy,
        roots: tuple[Path, ...],
        normal_tokens: Mapping[str, int],
    ) -> None:
        self.windows, self.policy, self.roots = windows, policy, roots
        self.tokens = dict(normal_tokens)
        require(bool(roots) and len(set(roots)) == len(roots))
        require(set(self.tokens) == set(policy.normal_sids))

    def token_checks(self) -> None:
        self.policy.document()
        forbidden = {
            "SeBackupPrivilege",
            "SeRestorePrivilege",
            "SeTakeOwnershipPrivilege",
            "SeDebugPrivilege",
            "SeTcbPrivilege",
            "SeCreateTokenPrivilege",
            "SeImpersonatePrivilege",
            "SeLoadDriverPrivilege",
        }
        with self.windows.process_token() as maintenance:
            require(self.windows.token_sid(maintenance) == self.policy.maintenance_sid)
        for sid, token in self.tokens.items():
            require(self.windows.token_sid(token) == sid)
            require(not self.windows.privileges(token) & forbidden)

    def objects(self) -> tuple[Path, ...]:
        items = tuple(path for root in self.roots for path in tree(root))
        require(len(items) == len(set(items)))
        return items

    def install(self) -> list[dict[str, Any]]:
        """Future delivery only. Failure retains partial inhibition; no release."""
        self.token_checks()
        for item in self.objects():
            self.windows.set_sddl(item, self.policy.sddl())
        return self.verify()

    def verify(self) -> list[dict[str, Any]]:
        self.token_checks()
        result = []
        for item in self.objects():
            # Parent DELETE_CHILD can bypass a child's DELETE denial. Check all
            # external ancestors, including roots of owned volumes/namespaces.
            for ancestor in item.parents:
                if any(
                    ancestor == root or root in ancestor.parents for root in self.roots
                ):
                    continue
                for token in self.tokens.values():
                    require(not self.windows.access(ancestor, token) & 0xD0156)
            for token in self.tokens.values():
                require(self.windows.access(item, token) == 0)
            descriptor = self.windows.sddl(item)
            require("D:P" in descriptor)
            require(descriptor.startswith("O:" + self.policy.maintenance_sid + "D:"))
            result.append(
                {"path": str(item), "identity": identity(item), "sddl": descriptor}
            )
        return result


@dataclass
class Authority:
    controller: Controller
    evidence: dict[str, Any]
    pid: int
    thread: int
    active: bool = True

    def verify(self) -> None:
        require(
            self.active
            and self.pid == os.getpid()
            and self.thread == threading.get_ident()
        )
        require(self.controller._authority is self)
        state = self.controller.state()
        require(
            state["phase"]
            in {"retired", "copying", "installed", "bound", "releasing", "released"}
        )
        require(state["retirement"] == self.evidence)
        require(state["policy"] == self.controller.fence.policy.document())
        require(state["namespace"] == self.controller.namespace())
        require(state["fence"] == self.controller.verify_fence())
        retirement(
            state["before"], self.evidence["after"], self.controller.fence.policy
        )


class Controller:
    """Finite staged/resumed transaction, independent of target Core/domain.

    The control directory and this trusted controller/interpreter live outside
    replacement roots and are protected by the same maintenance policy. The
    caller obtains an existing OS gate before every state operation. No reboot
    API exists here, and neither state files nor a supplied bool confer proof.
    """

    def __init__(self, directory: Path, fence: Fence, control: p.NativeControl) -> None:
        self.directory, self.fence, self.control = directory, fence, control
        self._authority: Authority | None = None
        self._locked = False
        self._life: Any = None
        identity(directory)
        require(
            all(
                root != directory and root not in directory.parents
                for root in fence.roots
            )
        )

    def protected_control(self) -> None:
        """Control namespace must be inaccessible to every declared normal token."""
        self.fence.token_checks()
        for item in tree(self.directory):
            require(
                self.fence.windows.sddl(item).startswith(
                    "O:" + self.fence.policy.maintenance_sid + "D:P"
                )
            )
            for token in self.fence.tokens.values():
                require(self.fence.windows.access(item, token) == 0)
        for ancestor in self.directory.parents:
            for token in self.fence.tokens.values():
                require(not self.fence.windows.access(ancestor, token) & 0xD0156)

    def live(self) -> None:
        require(self._locked and self._life is not None)
        require(
            self._life[0] is self.control
            and self._life[1].active
            and self._life[1].pid == os.getpid()
            and self._life[1].thread_id == threading.get_ident()
        )
        self.protected_control()

    def namespace(self) -> list[Any]:
        return [
            [str(path), identity(path)]
            for path in (
                self.directory,
                self.control.guard,
                self.control.epoch_path,
                *self.fence.roots,
            )
        ]

    def reconcile_copy_inventory(self) -> None:
        state = self.state()
        if state["phase"] not in {"copying", "installed"}:
            return
        current = self.fence.verify()
        if current == state["fence"]:
            return
        journal = read(self.directory / "copy.json")
        require(
            journal["update_id"] == state["transaction"]
            and journal["archive"] == state["archive"]
        )
        root = Path(journal["root"])
        original = {row["path"]: row for row in state["fence"]}
        observed = {row["path"]: row for row in current}
        allowed: set[str] = set()
        for name, after in journal["after"].items():
            path = root / p.safe_path(name)
            allowed.add(str(path))
            allowed.update(
                str(parent) for parent in path.parents if root in parent.parents
            )
            if path.exists():
                raw = p._read_regular(root, name, p.MAX_FILE)
                fact = {"sha256": p.digest(raw), "size": len(raw)}
                require(fact in (after, journal["before"][name]))
            else:
                require(after is None or journal["before"][name] is None)
        native_names = {
            "runtime/managed-ingress",
            "runtime/managed-ingress/ingress.guard",
            "runtime/managed-ingress/protocol",
            "runtime/managed-ingress/baseline.json",
            "runtime/managed-ingress/adoption.json",
            "runtime/native-control",
            "runtime/native-control/installation.guard",
            "runtime/native-control/epoch",
        }
        if state["phase"] == "installed":
            allowed.update(str(root / name) for name in native_names)
            baseline = root / "runtime/managed-ingress/baseline.json"
            if baseline.exists():
                pending = p._read(baseline)
                require(
                    pending.get("origin") == "cold-v1"
                    and pending["installation"] == state["transaction"]
                )
                require(
                    pending["selection"] == state["selection"]
                    and pending["phase"] in {"pending", "bound"}
                )
        for name in set(original) | set(observed):
            if original.get(name) != observed.get(name):
                require(name in allowed)
        state["fence"] = current
        atomic(self.directory / "cold.json", state)

    def verify_fence(self) -> list[dict[str, Any]]:
        state = self.state()
        if state["phase"] not in {"releasing", "released"}:
            return self.fence.verify()
        self.fence.token_checks()
        progress = read(self.directory / "release.json")
        plan = progress["plan"]
        require(plan["archive"] == state["archive"])
        require(plan["qualification"] == self.fence.policy.qualification_sha256)
        child = read(self.directory / "child.json")
        require(
            child["phase"] == "completed"
            and child["result"]["transaction"] == state["transaction"]
        )
        require(child["result"]["epoch"] == state["epoch"])
        root = Path(state["installed"]["root"])
        released = {str(root / p.safe_path(row["path"])): row for row in plan["rows"]}
        originals = {row["path"]: row for row in state["fence"]}
        require({str(path) for path in self.fence.objects()} == set(originals))
        for path_text, original in originals.items():
            path = Path(path_text)
            require(identity(path) == original["identity"])
            row = released.get(path_text)
            actual = self.fence.windows.sddl(path)
            if row is None or actual == original["sddl"]:
                require(actual == original["sddl"])
                require(
                    all(
                        self.fence.windows.access(path, token) == 0
                        for token in self.fence.tokens.values()
                    )
                )
            else:
                require(actual == row["sddl"])
                require(
                    p.digest(p._read_regular(root, row["path"], p.MAX_FILE))
                    == row["sha256"]
                )
                require(
                    actual.startswith("O:" + self.fence.policy.maintenance_sid + "D:P")
                )
                for sid, token in self.fence.tokens.items():
                    mask = self.fence.windows.access(path, token)
                    require(mask == row["normal_access"][sid] and mask & 0xD0156 == 0)
        # External parent mutation checks remain effective after release.
        for root_path in self.fence.roots:
            for ancestor in root_path.parents:
                if ancestor in self.fence.roots:
                    continue
                for token in self.fence.tokens.values():
                    require(not self.fence.windows.access(ancestor, token) & 0xD0156)
        return state["fence"]

    def state(self) -> dict[str, Any]:
        self.live()
        return read(self.directory / "cold.json")

    @contextmanager
    def held(self) -> Iterator[Controller]:
        require(not self._locked)
        with self.control.exclusive():
            self._locked = True
            self._life = (self.control, p._OPERATION_LIFETIME.get())
            try:
                self.live()
                yield self
            finally:
                self._locked = False
                self._life = None

    def stage(self, *, archive_sha256: str, selection: dict[str, Any]) -> None:
        self.live()
        if (self.directory / "cold.json").exists():
            interrupted = self.state()
            require(interrupted["phase"] == "fencing")
            require(
                interrupted["archive"] == archive_sha256
                and interrupted["selection"] == selection
            )
            require(
                interrupted["namespace"] == self.namespace()
                and interrupted["policy"] == self.fence.policy.document()
            )
            interrupted["fence"] = self.fence.install()
            interrupted["before"] = self.fence.windows.sample()
            self.fence.policy.eligible(interrupted["before"])
            interrupted["retirement"], interrupted["phase"] = (
                None,
                "awaiting_retirement",
            )
            atomic(self.directory / "cold.json", interrupted)
            return
        require(bool(re.fullmatch(r"sha256:[a-f0-9]{64}", archive_sha256)))
        initial = self.fence.windows.sample()
        self.fence.policy.eligible(initial)
        require(initial["low"] > 60000)
        # Persist refusal intent BEFORE changing any target ACL; crash means
        # exact recovery/restart, never inferred successful installation.
        state: dict[str, Any] = {
            "phase": "fencing",
            "transaction": p.uuid4().hex,
            "archive": archive_sha256,
            "selection": selection,
            "policy": self.fence.policy.document(),
            "namespace": self.namespace(),
        }
        atomic(self.directory / "cold.json", state)
        state["fence"] = self.fence.install()
        state["before"] = self.fence.windows.sample()
        state["retirement"], state["phase"] = None, "awaiting_retirement"
        atomic(self.directory / "cold.json", state)

    @contextmanager
    def resume(self) -> Iterator[Authority]:
        require(self._locked and self._authority is None)
        self.reconcile_copy_inventory()
        state = self.state()
        require(
            state["phase"]
            in {
                "awaiting_retirement",
                "retired",
                "copying",
                "installed",
                "bound",
                "releasing",
                "released",
            }
        )
        require(state["namespace"] == self.namespace())
        require(state["policy"] == self.fence.policy.document())
        require(state["fence"] == self.verify_fence())
        observed = retirement(
            state["before"], self.fence.windows.sample(), self.fence.policy
        )
        # A crash before bound does not preserve the live lease. Re-observe
        # counter-reset sufficiency and all persistent fences on every resume.
        if state["retirement"] is None:
            state["retirement"], state["phase"] = observed, "retired"
            state["retirement_fence"] = p.digest(p.canonical_json(state["fence"]))
            atomic(self.directory / "cold.json", state)
        authority = Authority(
            self, state["retirement"], os.getpid(), threading.get_ident()
        )
        self._authority = authority
        try:
            authority.verify()
            yield authority
        finally:
            authority.active = False
            self._authority = None

    def before_copy(self, authority: Authority, archive: bytes) -> None:
        authority.verify()
        state = self.state()
        require(state["archive"] == "sha256:" + p.digest(archive))
        require(state["phase"] in {"retired", "copying"})
        state["phase"] = "copying"
        atomic(self.directory / "cold.json", state)

    def installed(
        self, authority: Authority, *, root: Path, frozen: FrozenArchive
    ) -> None:
        """Call after native exact copy/manifest checks, before cold adoption.

        New objects require the maintenance-only descriptor. This refresh only
        changes the object inventory after an authorized native copy; it never
        accepts a namespace, policy, archive or old-object identity change.
        """
        require(self._locked and authority is self._authority and authority.active)
        state = self.state()
        require(
            state["phase"] in {"copying", "installed"}
            and state["namespace"] == self.namespace()
        )
        require(root in self.fence.roots and frozen.archive_sha256 == state["archive"])
        publication = p.accept_publication(root, trusted_leaf=frozen.trusted_leaf)
        if publication is None:
            raise Refused()
        require(publication.payload == frozen.payload)
        require(publication.manifest_sha256 == p.digest(frozen.manifest))
        require(p._read_regular(root, p.LEAF, p.MAX_FILE) == frozen.trusted_leaf)
        installed = {
            "root": str(root),
            "archive": frozen.archive_sha256,
            "manifest": publication.manifest_sha256,
            "publication": publication.projection_sha256,
            "leaf": p.digest(frozen.trusted_leaf),
        }
        require(state.get("installed", installed) == installed)
        state["installed"] = installed
        state["fence"] = self.fence.verify()
        state["phase"] = "installed"
        atomic(self.directory / "cold.json", state)
        authority.verify()

    def bound(self, authority: Authority, epoch: str) -> None:
        authority.verify()
        state = self.state()
        require(state["phase"] in {"installed", "bound"} and bool(epoch))
        require(state.get("epoch", epoch) == epoch)
        state["epoch"], state["phase"] = epoch, "bound"
        atomic(self.directory / "cold.json", state)

    # Release deliberately has no generic ACL-restore method. Delivery must
    # verify guarded-only routes, exact committed durable state and independent
    # fresh child outcome before selectively restoring approved permissions.
    # Old entry ACL backups are recovery data, never permission to reopen them.


@dataclass(frozen=True)
class FrozenArchive:
    """Exact prequalified archive+sidecar; accepted leaf never comes from target."""

    archive_sha256: str
    payload: Mapping[str, bytes]
    manifest: bytes
    trusted_leaf: bytes
    raw: bytes

    @classmethod
    def capture(
        cls, raw: bytes, manifest: bytes, *, expected_sha256: str
    ) -> FrozenArchive:
        require("sha256:" + p.digest(raw) == expected_sha256)
        metadata = p.parse_manifest(manifest)
        payload: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(len(archive.infolist()) <= 20000)
            total = 0
            for member in archive.infolist():
                name = p.safe_path(member.filename)
                require(name == member.filename and not member.is_dir())
                require(not member.flag_bits & 1)
                require(stat.S_IFMT(member.external_attr >> 16) in {0, stat.S_IFREG})
                require(member.file_size <= p.MAX_FILE)
                total += member.file_size
                require(total <= p.MAX_TOTAL + p.MAX_MANIFEST)
                require(name.casefold() not in {key.casefold() for key in payload})
                payload[name] = archive.read(member)
        require(payload.pop(p.MANIFEST, None) == manifest)
        require(sum(map(len, payload.values())) <= p.MAX_TOTAL)
        require(set(payload) == {row["relative_path"] for row in metadata["files"]})
        for row in metadata["files"]:
            require(len(payload[row["relative_path"]]) == row["size"])
            require(p.digest(payload[row["relative_path"]]) == row["sha256"])
        leaf = payload[p.LEAF]
        seal = p.leaf_seal(leaf)
        require(seal is not None and seal[1] == p.digest(p.projection(manifest)))
        require(payload[p.INVENTORY] == p.inventory_bytes(payload))
        return cls(expected_sha256, MappingProxyType(payload), manifest, leaf, raw)

    def copy(self, authority: Authority, root: Path, backup: Path) -> p.NativeEntry:
        """Compatibility call into the single cold G2 plan/progress engine."""
        require(backup == authority.controller.directory / "backup")
        return copy_resumable(authority, self, root)


def _refresh(controller: Controller) -> None:
    """Only a native mutation under the live external lease changes inventory."""
    require(controller._locked and controller._life is not None)
    state = controller.state()
    require(state["namespace"] == controller.namespace())
    state["fence"] = controller.fence.verify()
    atomic(controller.directory / "cold.json", state)


def copy_resumable(
    authority: Authority, frozen: FrozenArchive, root: Path
) -> p.NativeEntry:
    """G2 native backup/plan/progress conventions, with exact cold resume.

    Plan and original bytes live in the independent protected management domain.
    Every backup is verified before mutation. A crash never re-plans over a
    partially replaced target and never invokes old Core after overwrite.
    """
    authority.verify()
    controller = authority.controller
    require(root in controller.fence.roots)
    require(controller.state()["archive"] == frozen.archive_sha256)
    journal_path = controller.directory / "copy.json"
    backup = controller.directory / "backup"
    payload = {**dict(frozen.payload), p.MANIFEST: frozen.manifest}
    if not journal_path.exists():
        require(controller.state()["phase"] == "retired")
        old_raw = p._read_regular(root, p.MANIFEST, p.MAX_MANIFEST)
        old = p.parse_manifest(old_raw)
        old_names = {row["relative_path"] for row in old["files"]} | {p.MANIFEST}
        names = sorted(old_names | set(payload))
        before: dict[str, Any] = {}
        for name in names:
            target = root / p.safe_path(name)
            if target.exists():
                identity(target)
                # Unknown target collisions are retained for recovery, not
                # silently overwritten as newly managed package members.
                require(name in old_names)
                raw = p._read_regular(root, name, p.MAX_FILE)
                before[name] = {"sha256": p.digest(raw), "size": len(raw)}
            else:
                before[name] = None
        journal = {
            "schema_version": 1,
            "update_id": controller.state()["transaction"],
            "archive": frozen.archive_sha256,
            "root": str(root),
            "before": before,
            "after": {
                name: {"sha256": p.digest(payload[name]), "size": len(payload[name])}
                if name in payload
                else None
                for name in names
            },
            "backed_up": [],
            "completed_operations": [],
            "pending_operations": names,
            "phase": "backup",
        }
        atomic(journal_path, journal)
    journal = read(journal_path)
    require(
        journal["archive"] == frozen.archive_sha256 and journal["root"] == str(root)
    )
    require(journal["update_id"] == controller.state()["transaction"])
    backup.mkdir(exist_ok=True)
    controller.fence.windows.set_sddl(backup, controller.fence.policy.sddl())
    if journal["phase"] == "backup":
        for name, original in journal["before"].items():
            if original is None:
                continue
            target, saved = root / name, backup / name
            if name not in journal["backed_up"]:
                raw = p._read_regular(root, name, p.MAX_FILE)
                require(
                    p.digest(raw) == original["sha256"] and len(raw) == original["size"]
                )
                if saved.exists():
                    require(p._read_regular(backup, name, p.MAX_FILE) == raw)
                else:
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    p._update_atomic(saved, raw)
                journal["backed_up"].append(name)
                atomic(journal_path, journal)
        journal["phase"] = "copying"
        atomic(journal_path, journal)
        state = controller.state()
        state["phase"] = "copying"
        atomic(controller.directory / "cold.json", state)
    # Recovery always checks the same original backups, even after partial copy.
    for name, original in journal["before"].items():
        if original is not None:
            saved = p._read_regular(backup, name, p.MAX_FILE)
            require(
                p.digest(saved) == original["sha256"] and len(saved) == original["size"]
            )
    for name in tuple(journal["pending_operations"]):
        authority.verify()
        target = p._update_target(root, name)
        if name in payload:
            # Atomic writes inherit the maintenance-only parent descriptor.
            p._update_atomic(target, payload[name])
            controller.fence.windows.set_sddl(target, controller.fence.policy.sddl())
        else:
            target.unlink(missing_ok=True)
        _refresh(controller)
        journal["completed_operations"].append(name)
        journal["pending_operations"].remove(name)
        atomic(journal_path, journal)
    publication = p.accept_publication(root, trusted_leaf=frozen.trusted_leaf)
    if publication is None or publication.payload != frozen.payload:
        raise Refused()
    journal["phase"] = "installed"
    atomic(journal_path, journal)
    controller.installed(authority, root=root, frozen=frozen)
    return p.NativeEntry(
        root, publication, p.NativeImage.from_publication(root, publication), None
    )


_COLD_CHILD = """import base64,json,sys,types
x=json.load(sys.stdin)
s=base64.b64decode(x["leaf"],validate=True)
m=types.ModuleType("pf_native_control");m.__file__=x["root"]+"/tools/pf_native_control.py"
m._captured_source=s;sys.modules[m.__name__]=m
exec(compile(s,m.__file__,"exec",dont_inherit=True),m.__dict__)
m._run_cold_child(x)
"""


def fresh_child(
    authority: Authority,
    entry: p.NativeEntry,
    frozen: FrozenArchive,
    *,
    interpreter: str,
) -> dict[str, Any]:
    """Reserve before native suspended spawn; child acquires its OWN lease."""
    import base64
    import subprocess
    import time

    authority.verify()
    controller = authority.controller
    state = p.ManagedEnrollmentProducer(entry.root, frozen.trusted_leaf)._state()
    if state["phase"] != "bound" or entry.control is None:
        raise Refused()
    reservation_path = controller.directory / "child.json"
    reservation = {
        "transaction": controller.state()["transaction"],
        "generation": state["adoption"],
        "epoch": entry.control.accepted_epoch,
        "selection": state["selection"],
        "archive": frozen.archive_sha256,
        "manifest": p.digest(frozen.manifest),
        "leaf": p.digest(frozen.trusted_leaf),
        "token": p.uuid4().hex,
        "phase": "reserved",
        "boot": controller.fence.windows.sample(),
    }
    # Exact incomplete reservation is not absence-of-activity evidence. The outer
    # native owner must terminal-reconcile it before preparing another child.
    if reservation_path.exists():
        existing = read(reservation_path)
        require(
            {
                key: existing[key]
                for key in (
                    "transaction",
                    "generation",
                    "epoch",
                    "selection",
                    "archive",
                    "manifest",
                    "leaf",
                )
            }
            == {
                key: reservation[key]
                for key in (
                    "transaction",
                    "generation",
                    "epoch",
                    "selection",
                    "archive",
                    "manifest",
                    "leaf",
                )
            }
        )
        if existing["phase"] == "completed":
            return existing["result"]
        tree_path = controller.directory / "child-tree.json"
        if tree_path.exists():
            facts = read(tree_path)
            owned = p.reopen_job(
                facts,
                pid=facts["pid"],
                identity={
                    "transaction": existing["transaction"],
                    "token": existing["token"],
                },
            )
            if owned is not None:
                try:
                    require(owned.active() == 0)
                finally:
                    owned.close()
        else:
            retirement(
                existing["boot"],
                controller.fence.windows.sample(),
                controller.fence.policy,
            )
        # No running prior child remains. Keep its exact failed/reserved evidence.
        atomic(
            controller.directory / ("child-" + existing["token"] + ".json"), existing
        )
        tree_path.unlink(missing_ok=True)
    atomic(reservation_path, reservation)
    handoff = {
        **reservation,
        "root": str(entry.root),
        "leaf": base64.b64encode(frozen.trusted_leaf).decode("ascii"),
        "leaf_sha256": p.digest(frozen.trusted_leaf),
        "manifest_sha256": p.digest(frozen.manifest),
        "archive_raw": base64.b64encode(frozen.raw).decode("ascii"),
    }
    process = p.spawn_owned(
        [interpreter, "-I", "-B", "-c", _COLD_CHILD],
        token=reservation["token"],
        receipt_path=controller.directory / "child-tree.json",
        identity={
            "transaction": reservation["transaction"],
            "token": reservation["token"],
        },
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    job = getattr(process, "native_job", None)
    try:
        stdout, stderr = process.communicate(p.canonical_json(handoff), timeout=120)
        require(process.returncode == 0 and not stderr and len(stdout) <= 65536)
        require(job is not None and job.active() == 0)
        result = p.json.loads(stdout)
        expected = {
            key: reservation[key]
            for key in (
                "transaction",
                "generation",
                "epoch",
                "selection",
                "archive",
                "manifest",
                "leaf",
                "token",
            )
        }
        require(result == {**expected, "result": "verified"})
        reservation.update(phase="completed", result=result)
        atomic(reservation_path, reservation)
        return result
    finally:
        if job is not None:
            if process.poll() is None or job.active():
                job.stop(deadline=time.monotonic() + 5)
                process.wait(timeout=5)
            job.close()


def release_guarded(
    authority: Authority,
    entry: p.NativeEntry,
    plan: dict[str, Any],
    child: dict[str, Any],
) -> None:
    """Selective committed ACL plan only; interruption never restores old ACLs.

    Real guarded-route qualification is a required trusted deployment input.
    A report/receipt by itself never establishes retirement or release authority.
    """
    authority.verify()
    controller = authority.controller
    state = controller.state()
    require(state["phase"] in {"bound", "releasing", "released"})
    if entry.publication is None or entry.control is None:
        raise Refused()
    producer = p.ManagedEnrollmentProducer(
        entry.root, entry.publication.payload[p.LEAF]
    )
    durable = producer._state()
    require(
        entry.control is not None
        and producer._epoch(durable) == entry.control.accepted_epoch
    )
    require(child == read(controller.directory / "child.json")["result"])
    require(
        child["transaction"] == state["transaction"]
        and child["epoch"] == state["epoch"]
    )
    require(
        child["generation"] == durable["adoption"]
        and child["selection"] == durable["selection"]
    )
    require(set(plan) == {"qualification", "archive", "rows"})
    require(plan["qualification"] == controller.fence.policy.qualification_sha256)
    require(plan["archive"] == state["archive"])
    rows = plan["rows"]
    require(bool(rows) and len({row["path"] for row in rows}) == len(rows))
    for row in rows:
        require(set(row) == {"path", "sha256", "sddl", "normal_access"})
        name = p.safe_path(row["path"])
        require(
            name in entry.publication.payload
            and row["sha256"] == p.digest(entry.publication.payload[name])
        )
        require(set(row["normal_access"]) == set(controller.fence.tokens))
        require(
            row["sddl"].startswith(
                "O:" + controller.fence.policy.maintenance_sid + "D:P"
            )
        )
        for sid, token in controller.fence.tokens.items():
            mask = controller.fence.windows.access_sddl(row["sddl"], token)
            require(
                type(row["normal_access"][sid]) is int
                and mask == row["normal_access"][sid]
                and mask & 0xD0156 == 0
            )
    release_path = controller.directory / "release.json"
    if release_path.exists():
        progress = read(release_path)
        require(progress["plan"] == plan)
    else:
        authority.verify()
        progress = {"plan": plan, "completed": []}
        atomic(release_path, progress)
    state["phase"] = "releasing"
    atomic(controller.directory / "cold.json", state)
    rows = plan["rows"]
    require(bool(rows) and len({row["path"] for row in rows}) == len(rows))
    for row in rows:
        require(set(row) == {"path", "sha256", "sddl", "normal_access"})
        name = p.safe_path(row["path"])
        require(name in entry.publication.payload)
        require(row["sha256"] == p.digest(entry.publication.payload[name]))
        require(set(row["normal_access"]) == set(controller.fence.tokens))
        # Code release is read/execute only. Permanent guard/data/control and old
        # unselected entry objects are never restored from ACL backups.
        require(
            all(
                type(mask) is int and mask & 0xD0156 == 0
                for mask in row["normal_access"].values()
            )
        )
        path = entry.root / name
        require(
            p._read_regular(entry.root, name, p.MAX_FILE)
            == entry.publication.payload[name]
        )
        controller.fence.windows.set_sddl(path, row["sddl"])
        require(
            controller.fence.windows.sddl(path).startswith(
                "O:" + controller.fence.policy.maintenance_sid + "D:P"
            )
        )
        for sid, token in controller.fence.tokens.items():
            require(
                controller.fence.windows.access(path, token)
                == row["normal_access"][sid]
            )
        if name not in progress["completed"]:
            progress["completed"].append(name)
            atomic(release_path, progress)
    state["phase"] = "released"
    atomic(controller.directory / "cold.json", state)


@contextmanager
def normal_tokens(
    windows: Windows, rows: list[dict[str, Any]]
) -> Iterator[dict[str, int]]:
    """Bind exact actual effective tokens to qualified normal-principal inputs."""
    handles: list[int] = []
    result: dict[str, int] = {}
    windows.k.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    windows.k.OpenProcess.restype = w.HANDLE
    try:
        for row in rows:
            require(set(row) == {"sid", "pid", "birth_id"})
            process = windows.k.OpenProcess(0x1000, False, row["pid"])
            windows.checked(process)
            try:
                require(p._birth(p._kernel(), process) == row["birth_id"])
                token = w.HANDLE()
                windows.checked(
                    windows.a.OpenProcessToken(process, 0xA, ctypes.byref(token))
                )
                if token.value is None or row["sid"] in result:
                    raise Refused()
                handles.append(int(token.value))
                require(windows.token_sid(int(token.value)) == row["sid"])
                result[row["sid"]] = int(token.value)
            finally:
                windows.k.CloseHandle(process)
        yield result
    finally:
        for handle in handles:
            windows.k.CloseHandle(handle)


def execute_job(
    operation: str, spec: dict[str, Any], captured: dict[str, bytes], native: Any
) -> dict[str, Any]:
    """Finite fixed dispatch; real platform facts come from accepted input."""
    require(native is p)
    deployment = spec["deployment"]
    qualified = spec["qualified"]
    require(
        qualified["deployment_sha256"]
        == "sha256:" + p.digest(p.canonical_json(deployment))
    )
    policy = Policy(
        deployment["maintenance_sid"],
        tuple(deployment["normal_sids"]),
        tuple(tuple(row) for row in qualified["windows_versions"]),
        qualified["platform_qualification_sha256"],
    )
    windows = Windows()
    with normal_tokens(windows, deployment["token_processes"]) as tokens:
        directory = Path(spec["namespace"]["control"])
        roots = tuple(Path(row) for row in spec["target_roots"])
        fence = Fence(windows, policy, roots, tokens)
        control = p.NativeControl(
            directory / "controller.guard",
            directory / "controller.epoch",
            deployment["controller_epoch"],
        )
        if operation == "cold-stage" and not directory.exists():
            # Parent mutation exclusion is checked before creating control state.
            fence.token_checks()
            for ancestor in directory.parents:
                if ancestor.exists():
                    for token in tokens.values():
                        require(not windows.access(ancestor, token) & 0xD0156)
            directory.mkdir()
            windows.set_sddl(directory, policy.sddl())
            for name, raw in {
                "controller.guard": b"0",
                "controller.epoch": deployment["controller_epoch"].encode("ascii"),
            }.items():
                path = directory / name
                with path.open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                windows.set_sddl(path, policy.sddl())
        controller = Controller(directory, fence, control)
        with controller.held():
            selection = p.ManagedSelection(**deployment["selection"])
            if operation == "cold-stage":
                controller.stage(
                    archive_sha256=deployment["archive_sha256"],
                    selection=selection.document(),
                )
                return {"phase": "awaiting_retirement"}
            with controller.resume() as authority:
                archive = FrozenArchive.capture(
                    captured["archive"],
                    captured["manifest"],
                    expected_sha256=deployment["archive_sha256"],
                )
                root = Path(deployment["core_root"])
                if operation == "cold-resume" and controller.state()["phase"] in {
                    "retired",
                    "copying",
                    "installed",
                }:
                    entry = copy_resumable(authority, archive, root)
                    _, entry = p.ManagedEnrollmentProducer.from_cold_provider(
                        authority, entry, selection=selection
                    )
                    if entry.control is None:
                        raise Refused()
                    return {"phase": "bound", "epoch": entry.control.accepted_epoch}
                producer = p.ManagedEnrollmentProducer(root, archive.trusted_leaf)
                publication = p.accept_publication(
                    root, trusted_leaf=archive.trusted_leaf
                )
                require(publication is not None)
                entry = producer.attach(
                    p.NativeEntry(root, publication, None, None), selection=selection
                )
                child = fresh_child(
                    authority, entry, archive, interpreter=deployment["interpreter"]
                )
                if operation == "cold-release":
                    release_guarded(authority, entry, deployment["release"], child)
                    return {"phase": "released"}
                require(operation in {"cold-finalize", "cold-resume"})
                return {"phase": "child_verified"}
