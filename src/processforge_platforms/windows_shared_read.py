"""Read a published Windows file while an atomic rename holds delete access."""

from __future__ import annotations

import os
from pathlib import Path


def _open_shared(path: str, flags: int) -> int:
    import _winapi
    import msvcrt

    # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE.
    handle = _winapi.CreateFile(
        path, _winapi.GENERIC_READ, 7, 0, _winapi.OPEN_EXISTING, 0, 0
    )
    try:
        return msvcrt.open_osfhandle(handle, flags | os.O_BINARY | os.O_NOINHERIT)
    except BaseException:
        _winapi.CloseHandle(handle)
        raise


def read_published_file(path: Path) -> bytes:
    with open(path, "rb", opener=_open_shared) as stream:
        return stream.read()
