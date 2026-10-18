"""Small typed Windows boundary for private ACLs and non-redirected reads."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import stat

from .contracts import EgressError


def apis():
    if os.name != "nt":
        raise EgressError("enforcement_unavailable")
    kernel = C.WinDLL("kernel32", use_last_error=True)
    adv = C.WinDLL("advapi32", use_last_error=True)
    specs = [
        (kernel, "GetCurrentProcess", [], W.HANDLE),
        (kernel, "CloseHandle", [W.HANDLE], W.BOOL),
        (kernel, "LocalFree", [C.c_void_p], C.c_void_p),
        (kernel, "CreateDirectoryW", [W.LPCWSTR, C.c_void_p], W.BOOL),
        (kernel, "CreateFileW", [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE], W.HANDLE),
        (kernel, "GetFinalPathNameByHandleW", [W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD], W.DWORD),
        (adv, "OpenProcessToken", [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)], W.BOOL),
        (adv, "GetTokenInformation", [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)], W.BOOL),
        (adv, "ConvertSidToStringSidW", [C.c_void_p, C.POINTER(W.LPWSTR)], W.BOOL),
        (adv, "ConvertStringSecurityDescriptorToSecurityDescriptorW", [W.LPCWSTR, W.DWORD, C.POINTER(C.c_void_p), C.c_void_p], W.BOOL),
        (adv, "GetNamedSecurityInfoW", [W.LPCWSTR, C.c_int, W.DWORD, C.POINTER(C.c_void_p), C.c_void_p, C.POINTER(C.c_void_p), C.c_void_p, C.POINTER(C.c_void_p)], W.DWORD),
        (adv, "GetSecurityDescriptorControl", [C.c_void_p, C.POINTER(W.WORD), C.POINTER(W.DWORD)], W.BOOL),
        (adv, "GetAce", [C.c_void_p, W.DWORD, C.POINTER(C.c_void_p)], W.BOOL),
    ]
    for dll, name, args, result in specs:
        function = getattr(dll, name)
        function.argtypes, function.restype = args, result
    return kernel, adv


def sid_text(pointer, kernel, adv):
    value = W.LPWSTR()
    if not pointer or not adv.ConvertSidToStringSidW(pointer, C.byref(value)):
        raise EgressError("private_acl_unavailable")
    try:
        return value.value
    finally:
        kernel.LocalFree(C.cast(value, C.c_void_p))


def current_sid():
    kernel, adv = apis()
    token, size = W.HANDLE(), W.DWORD()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, C.byref(token)):
        raise EgressError("private_acl_unavailable")
    try:
        adv.GetTokenInformation(token, 1, None, 0, C.byref(size))
        if not 1 <= size.value <= 65536:
            raise EgressError("private_acl_unavailable")
        buffer = C.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, C.byref(size)):
            raise EgressError("private_acl_unavailable")
        return sid_text(C.cast(buffer, C.POINTER(C.c_void_p))[0], kernel, adv)
    finally:
        kernel.CloseHandle(token)


def no_reparse(path: Path):
    path = path.absolute()
    for current in (*reversed(path.parents), path):
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise EgressError("source_changed")
    return path


def private_directory(path: Path):
    kernel, adv = apis()
    no_reparse(path.parent)
    if not path.exists():
        class Attributes(C.Structure):
            _fields_ = [("length", W.DWORD), ("descriptor", C.c_void_p), ("inherit", W.BOOL)]
        descriptor = C.c_void_p()
        sid = current_sid()
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                f"O:{sid}D:P(A;OICI;FA;;;{sid})", 1, C.byref(descriptor), None):
            raise EgressError("private_acl_unavailable")
        try:
            attributes = Attributes(C.sizeof(Attributes), descriptor, False)
            if not kernel.CreateDirectoryW(str(path), C.byref(attributes)) and C.get_last_error() != 183:
                raise EgressError("private_acl_unavailable")
        finally:
            kernel.LocalFree(descriptor)
    verify_private(path, directory=True)


def verify_private(path: Path, *, directory=False):
    no_reparse(path)
    kernel, adv = apis()
    owner, acl, descriptor = C.c_void_p(), C.c_void_p(), C.c_void_p()
    if adv.GetNamedSecurityInfoW(str(path), 1, 5, C.byref(owner), None, C.byref(acl), None, C.byref(descriptor)):
        raise EgressError("private_acl_unavailable")
    try:
        sid = current_sid()
        if not acl or sid_text(owner, kernel, adv) != sid:
            raise EgressError("private_acl_unavailable")
        # ACL header: BYTE revision, BYTE reserved, WORD size, WORD count, WORD reserved.
        count = C.c_ushort.from_address(acl.value + 4).value
        if count != 1:
            raise EgressError("private_acl_unavailable")
        ace = C.c_void_p()
        if not adv.GetAce(acl, 0, C.byref(ace)):
            raise EgressError("private_acl_unavailable")
        kind, flags = C.c_ubyte.from_address(ace.value).value, C.c_ubyte.from_address(ace.value + 1).value
        mask = C.c_uint32.from_address(ace.value + 4).value
        if kind != 0 or flags & 8 or mask != 0x1F01FF or sid_text(ace.value + 8, kernel, adv) != sid:
            raise EgressError("private_acl_unavailable")
        if directory:
            control, revision = W.WORD(), W.DWORD()
            if (not adv.GetSecurityDescriptorControl(descriptor, C.byref(control), C.byref(revision))
                    or not control.value & 0x1000 or flags & 3 != 3):
                raise EgressError("private_acl_unavailable")
    finally:
        kernel.LocalFree(descriptor)


def read_source(path: Path, maximum: int) -> bytes:
    """Open without sharing writes/deletes; verify actual handle target before read."""
    import msvcrt
    kernel, _ = apis()
    expected = no_reparse(path)
    handle = kernel.CreateFileW(str(expected), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == C.c_void_p(-1).value:
        raise EgressError("source_changed")
    descriptor = None
    try:
        def check_target():
            name = C.create_unicode_buffer(32768)
            count = kernel.GetFinalPathNameByHandleW(handle, name, len(name), 0)
            if not count or count >= len(name):
                raise EgressError("source_changed")
            resolved = name.value.removeprefix("\\\\?\\")
            if os.path.normcase(resolved) != os.path.normcase(str(expected)):
                raise EgressError("source_changed")
            no_reparse(expected)
        check_target()
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise EgressError("content_budget_exceeded")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        check_target()
        after = os.fstat(descriptor)
        if len(raw) > maximum or (after.st_ino, after.st_size, after.st_mtime_ns) != (info.st_ino, info.st_size, info.st_mtime_ns):
            raise EgressError("source_changed")
        return raw
    except EgressError:
        raise
    except (OSError, ValueError):
        raise EgressError("source_changed") from None
    finally:
        if descriptor is None:
            kernel.CloseHandle(handle)
        else:
            os.close(descriptor)
