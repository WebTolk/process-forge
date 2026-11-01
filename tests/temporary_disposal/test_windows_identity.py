"""Real Windows handles share the identity format recorded by Python producers."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
from ctypes import wintypes
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from processforge_core.maintenance import temporary_disposal as disposal
from processforge_core.maintenance import temporary_files

pytestmark = pytest.mark.skipif(os.name != "nt", reason="real Windows handle identity")


@pytest.fixture
def owned_root() -> Path:
    base = Path(os.environ["PF_TEST_SCRATCH_ROOT"])
    assert base.is_absolute()
    root = base / uuid4().hex
    root.mkdir(parents=True)
    # Keep these small, test-owned fixtures and exact refusal receipts as evidence.
    return root


def record(root: Path, name: str, value: Any) -> None:
    (root / (name + ".json")).write_text(
        json.dumps(value, indent=2, default=str), encoding="utf-8"
    )


def identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    return info.st_dev, info.st_ino


def kernel_api() -> Any:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetHandleInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.GetHandleInformation.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def test_recorded_file_identity_disposes_first_time(owned_root: Path) -> None:
    resource = disposal.create_owned_file(owned_root / "result")
    resource.path.write_bytes(b"recorded file payload")
    assert resource.identity == identity(resource.path)
    receipt = disposal.dispose_owned(disposal.release_owned(resource))
    record(
        owned_root, "file", {"identity": resource.identity, "receipt": asdict(receipt)}
    )
    assert receipt.result == "deleted"
    assert (receipt.deleted_files, receipt.deleted_bytes) == (1, 21)
    assert not resource.path.exists()


@pytest.mark.parametrize("private", [False, True])
def test_recorded_nested_directory_disposes_first_time(
    owned_root: Path, private: bool
) -> None:
    resource = disposal.create_owned_directory(owned_root, private=private)
    assert resource.identity == identity(resource.path)
    nested = resource.path / "a/b"
    nested.mkdir(parents=True)
    (resource.path / "one").write_bytes(b"one")
    (nested / "two").write_bytes(b"two")
    receipt = disposal.dispose_owned(disposal.release_owned(resource))
    record(
        owned_root,
        "directory",
        {"identity": resource.identity, "private": private, "receipt": asdict(receipt)},
    )
    assert receipt.result == "deleted"
    assert receipt.complete and receipt.residuals == ()
    assert (
        receipt.deleted_files,
        receipt.deleted_bytes,
        receipt.deleted_directories,
    ) == (
        2,
        6,
        3,
    )
    assert not resource.path.exists()


@pytest.mark.parametrize("kind", ["file", "directory"])
@pytest.mark.parametrize("field", [0, 1])
def test_mismatched_recorded_identity_preserves_resource(
    owned_root: Path, kind: str, field: int
) -> None:
    if kind == "file":
        resource = disposal.create_owned_file(owned_root / "result")
        marker = resource.path
    else:
        resource = disposal.create_owned_directory(owned_root)
        marker = resource.path / "keep"
    marker.write_bytes(b"preserve")
    wrong = list(resource.identity)
    wrong[field] ^= 1
    forged = replace(disposal.release_owned(resource), identity=tuple(wrong))
    receipt = disposal.dispose_owned(forged)
    record(owned_root, "mismatch", asdict(receipt))
    assert receipt.result in {"identity_changed", "cleanup_pending"}
    if kind == "directory":
        assert receipt.reason_code == "identity_changed"
    assert receipt.deleted_files == receipt.deleted_directories == 0
    assert marker.read_bytes() == b"preserve"


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_handle_identity_closes_only_noninheritable_duplicate(
    owned_root: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    import msvcrt

    path = owned_root / "object"
    path.mkdir() if kind == "directory" else path.write_bytes(b"payload")
    expected = identity(path)
    kernel = kernel_api()
    # READ_ATTRIBUTES, all sharing, BACKUP_SEMANTICS | OPEN_REPARSE_POINT.
    handle = kernel.CreateFileW(str(path), 0x80, 7, None, 3, 0x02200000, None)
    assert handle != wintypes.HANDLE(-1).value
    fstat = os.fstat
    observed = []

    def inspect_duplicate(descriptor: int) -> os.stat_result:
        duplicate = msvcrt.get_osfhandle(descriptor)
        assert duplicate != handle
        flags = wintypes.DWORD()
        assert kernel.GetHandleInformation(duplicate, ctypes.byref(flags))
        assert flags.value & 1 == 0
        observed.append((descriptor, duplicate))
        return fstat(descriptor)

    monkeypatch.setattr(temporary_files.os, "fstat", inspect_duplicate)
    try:
        actual = temporary_files._windows_handle_identity(handle)
        assert actual == expected
        assert len(observed) == 1
        flags = wintypes.DWORD()
        assert kernel.GetHandleInformation(handle, ctypes.byref(flags))
        descriptor, duplicate = observed[0]
        assert not kernel.GetHandleInformation(duplicate, ctypes.byref(flags))
        assert ctypes.get_last_error() == 6  # ERROR_INVALID_HANDLE.
        with pytest.raises(OSError):
            fstat(descriptor)
        record(
            owned_root,
            "handle",
            {
                "kind": kind,
                "expected": expected,
                "actual": actual,
                "original_valid": True,
                "duplicate_closed": True,
                "duplicate_noninheritable": True,
            },
        )
    finally:
        assert kernel.CloseHandle(handle)


def test_directory_guard_uses_exact_identity_and_keeps_rename_excluded(
    owned_root: Path,
) -> None:
    directory = owned_root / "directory"
    directory.mkdir()
    expected = identity(directory)
    entered = False
    with temporary_files._directory(directory, expected_identity=expected):
        entered = True
        with pytest.raises(PermissionError):
            directory.rename(owned_root / "renamed")
    assert entered and directory.is_dir()
    with pytest.raises(ValueError, match="^identity_changed$"):
        with temporary_files._directory(
            directory, expected_identity=(expected[0] ^ 1, expected[1])
        ):
            pytest.fail("mismatched directory guard yielded")
    with temporary_files._directory(directory, expected_identity=expected):
        pass


def test_exact_handle_identity_does_not_allow_hardlink_deletion(
    owned_root: Path,
) -> None:
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    resource.path.write_bytes(b"linked payload")
    alias = owned_root / "alias"
    os.link(resource.path, alias)
    assert identity(alias) == resource.identity
    with pytest.raises(ValueError, match="^unsafe_path$"):
        disposal._windows_delete(resource)
    assert resource.path.read_bytes() == alias.read_bytes() == b"linked payload"


def test_exact_handle_identity_does_not_allow_wrong_kind_deletion(
    owned_root: Path,
) -> None:
    resource = disposal.release_owned(disposal.create_owned_directory(owned_root))
    with pytest.raises(ValueError, match="^unsafe_path$"):
        disposal._windows_delete(replace(resource, kind="file"))
    assert resource.path.is_dir()


def test_junction_is_refused_even_with_its_exact_identity(owned_root: Path) -> None:
    resource = disposal.release_owned(disposal.create_owned_directory(owned_root))
    resource.path.rmdir()
    target = owned_root / "foreign"
    target.mkdir()
    marker = target / "keep"
    marker.write_bytes(b"foreign evidence")
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(resource.path), str(target)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert resource.path.lstat().st_file_attributes & 0x400
    with pytest.raises(OSError, match="unsafe_directory"):
        with temporary_files._directory(
            resource.path, expected_identity=identity(resource.path)
        ):
            pytest.fail("junction guard yielded")
    receipt = disposal.dispose_owned(resource)
    record(owned_root, "junction", asdict(receipt))
    assert receipt.result == "cleanup_pending"
    assert receipt.reason_code == "unsafe_path"
    assert receipt.deleted_files == receipt.deleted_directories == 0
    assert marker.read_bytes() == b"foreign evidence"
    assert resource.path.exists()
