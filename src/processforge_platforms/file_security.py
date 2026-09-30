"""Opaque file-security operations selected at the native platform boundary."""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Protocol


class FileReplacementError(OSError):
    """The native replacement could not preserve required file metadata."""


class FileSecurity(Protocol):
    def descriptor(self, path: Path) -> bytes | None: ...
    def fingerprint(self, path: Path) -> str: ...
    def restore(self, path: Path, descriptor: bytes) -> None: ...
    def replace(self, target: Path, staged: Path, mode: int) -> None: ...


@lru_cache(maxsize=2)
def file_security_for(platform: str) -> FileSecurity:
    """Load only the selected adapter; unknown platforms have no fallback."""
    if platform == "nt":
        from .windows_file_security import WindowsFileSecurity
        return WindowsFileSecurity()
    if platform == "posix":
        from .posix_file_security import PosixFileSecurity
        return PosixFileSecurity()
    raise OSError("file_security_platform_unsupported")


def native_file_security() -> FileSecurity:
    return file_security_for(os.name)
