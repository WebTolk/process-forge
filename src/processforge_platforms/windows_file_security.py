"""Exact Windows descriptor restoration and metadata-preserving replacement."""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path

from .file_security import FileReplacementError


OWNER_GROUP_DACL = 0x0007
SE_DACL_AUTO_INHERIT_REQ = 0x0100
SE_DACL_AUTO_INHERITED = 0x0400
MAX_DESCRIPTOR_BYTES = 65536


class WindowsFileSecurity:
    def descriptor(self, path: Path) -> bytes:
        api = ctypes.WinDLL("advapi32", use_last_error=True).GetFileSecurityW
        api.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        api.restype = w.BOOL
        size = w.DWORD()
        api(str(path), OWNER_GROUP_DACL, None, 0, ctypes.byref(size))
        if not 1 <= size.value <= MAX_DESCRIPTOR_BYTES:
            raise OSError("file_security_descriptor_unavailable")
        buf = ctypes.create_string_buffer(size.value)
        if not api(str(path), OWNER_GROUP_DACL, buf, len(buf), ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.raw[:size.value]

    def fingerprint(self, path: Path) -> str:
        return hashlib.sha256(self.descriptor(path)).hexdigest()

    def restore(self, path: Path, descriptor: bytes) -> None:
        if not isinstance(descriptor, bytes) or not 20 <= len(descriptor) <= MAX_DESCRIPTOR_BYTES:
            raise OSError("file_security_descriptor_invalid")
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        buf = ctypes.create_string_buffer(descriptor)
        control, revision = w.WORD(), w.DWORD()
        get_control = adv.GetSecurityDescriptorControl
        get_control.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.WORD), ctypes.POINTER(w.DWORD)]
        get_control.restype = w.BOOL
        if not get_control(buf, ctypes.byref(control), ctypes.byref(revision)):
            raise ctypes.WinError(ctypes.get_last_error())
        if control.value & SE_DACL_AUTO_INHERITED:
            # The legacy setter clears AUTO_INHERITED unless its request bit is
            # also supplied. Change only this API input copy, not the preimage.
            # Requesting it for a descriptor without AUTO_INHERITED changes its
            # semantics, so that case must retain the original control word.
            set_control = adv.SetSecurityDescriptorControl
            set_control.argtypes = [ctypes.c_void_p, w.WORD, w.WORD]
            set_control.restype = w.BOOL
            if not set_control(buf, SE_DACL_AUTO_INHERIT_REQ, SE_DACL_AUTO_INHERIT_REQ):
                raise ctypes.WinError(ctypes.get_last_error())
        # SetNamedSecurityInfo may merge the staging parent's inherited ACEs.
        # Use non-propagating restoration and verify the complete saved bytes.
        setter = adv.SetFileSecurityW
        setter.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p]
        setter.restype = w.BOOL
        if not setter(str(path), OWNER_GROUP_DACL, buf):
            raise ctypes.WinError(ctypes.get_last_error())
        if self.descriptor(path) != descriptor:
            raise OSError("file_security_descriptor_mismatch")

    def replace(self, target: Path, staged: Path, mode: int) -> None:
        if not target.exists():
            os.replace(staged, target)
            return
        api = ctypes.WinDLL("kernel32", use_last_error=True).ReplaceFileW
        api.argtypes = [w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_void_p, ctypes.c_void_p]
        api.restype = w.BOOL
        # Do not ignore ACL/attribute merge errors on an existing target.
        if not api(str(target), str(staged), None, 0, None, None):
            raise FileReplacementError("file_replacement_failed") from ctypes.WinError(ctypes.get_last_error())
