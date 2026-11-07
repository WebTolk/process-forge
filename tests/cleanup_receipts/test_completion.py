"""Receipt completion at owned Windows failure boundaries; no PF services."""

from __future__ import annotations

import ctypes
import json
import os
from contextlib import contextmanager
from ctypes import wintypes
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest

from processforge_core.configuration.models import TemporaryFilesConfig
from processforge_core.maintenance import temporary_disposal as disposal


@pytest.fixture
def root() -> Path:
    path = Path(os.environ["PF_TEST_SCRATCH_ROOT"]) / uuid4().hex
    path.mkdir(parents=True)
    return path


def record(root: Path, name: str, receipt: disposal.CleanupReceipt) -> None:
    text = json.dumps(asdict(receipt), indent=2).replace(
        str(root).replace("\\", "\\\\"), "<fixture>"
    )
    (root / (name + ".json")).write_text(text, encoding="utf-8")


@contextmanager
def held_directory(path: Path, access: int, sharing: int) -> Iterator[None]:
    kernel: Any = ctypes.WinDLL("kernel32", use_last_error=True)
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
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(path), access, sharing, None, 3, 0x02200000, None)
    assert handle != wintypes.HANDLE(-1).value, ctypes.get_last_error()
    try:
        yield
    finally:
        assert kernel.CloseHandle(handle)


@pytest.mark.skipif(os.name != "nt", reason="real Windows sharing boundary")
@pytest.mark.parametrize("kind", ["file", "directory"])
def test_real_ancestry_failure_before_walk(
    root: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    boundary = root / "boundary"
    boundary.mkdir()
    resource = (
        disposal.create_owned_directory(boundary)
        if kind == "directory"
        else disposal.create_owned_file(boundary / "output")
    )
    resource = disposal.release_owned(resource)
    marker = resource.path / "payload" if kind == "directory" else resource.path
    marker.write_bytes(b"evidence")

    def unexpected(*args: Any, **kwargs: Any) -> disposal.CleanupReceipt:
        pytest.fail("directory walker entered despite blocked ancestry")

    with monkeypatch.context() as patch:
        patch.setattr(disposal, "_dispose_directory", unexpected)
        # Existing DELETE access conflicts with ancestry guard's no-delete sharing.
        with held_directory(boundary, 0x10080, 7):
            receipt = disposal.dispose_owned(resource)
            record(root, "ancestry", receipt)
            assert receipt.result == "cleanup_pending"
            assert receipt.error_code == 32
            assert not receipt.complete
            assert receipt.deleted_files == receipt.deleted_directories == 0
            assert receipt.deleted_bytes == 0
            assert marker.read_bytes() == b"evidence"
    repeated = disposal.dispose_owned(resource)
    record(root, "released", repeated)
    assert repeated.result == "deleted" and repeated.complete
    assert not resource.path.exists()
    assert disposal.dispose_owned(resource).result == "already_absent"


@pytest.mark.skipif(os.name != "nt", reason="real Windows sharing boundary")
@pytest.mark.parametrize("progress", [False, True])
def test_real_walker_counts_current_pass(root: Path, progress: bool) -> None:
    resource = disposal.release_owned(disposal.create_owned_directory(root))
    if progress:
        (resource.path / "payload").write_bytes(b"data")
    # Permit traversal, deny DELETE on the owned root after child deletion.
    with held_directory(resource.path, 0x81, 3):
        receipt = disposal.dispose_owned(resource)
        record(root, "blocked", receipt)
        assert receipt.result == ("partial" if progress else "cleanup_pending")
        assert not receipt.complete
        assert receipt.error_code == 32
        assert receipt.deleted_files == int(progress)
        assert receipt.deleted_bytes == (4 if progress else 0)
        assert receipt.deleted_directories == 0
        assert receipt.residuals == (str(resource.path),)
        assert resource.path.is_dir() and list(resource.path.iterdir()) == []
        again = disposal.dispose_owned(resource)
        record(root, "second_pass", again)
        assert again.result == "cleanup_pending" and not again.complete
        assert again.deleted_files == again.deleted_bytes == 0
    repeated = disposal.dispose_owned(resource)
    record(root, "released", repeated)
    assert repeated.result == "deleted" and repeated.complete
    assert repeated.deleted_files == 0 and repeated.deleted_directories == 1


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_injected_ancestry_oserror_preserves_fields(
    root: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    resource = disposal.release_owned(
        disposal.create_owned_directory(root)
        if kind == "directory"
        else disposal.create_owned_file(root / "output")
    )

    @contextmanager
    def denied(path: Path) -> Iterator[None]:
        assert path == resource.path
        raise OSError(13, "controlled ancestry denial")
        yield None

    with monkeypatch.context() as patch:
        patch.setattr(disposal, "_parent", denied)
        receipt = disposal.dispose_owned(resource, configuration_errors=("invalid",))
    assert receipt == disposal.CleanupReceipt(
        resource.resource_id,
        "cleanup_pending",
        error_code=13,
        configuration_errors=("invalid",),
        complete=False,
    )
    assert resource.path.exists()
    assert disposal.dispose_owned(resource).result == "deleted"


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_other_receipts_and_refusals_unchanged(root: Path, kind: str) -> None:
    resource = (
        disposal.create_owned_directory(root)
        if kind == "directory"
        else disposal.create_owned_file(root / "output")
    )
    marker = resource.path / "keep" if kind == "directory" else resource.path
    marker.write_bytes(b"keep")
    assert disposal.dispose_owned(resource) == disposal.CleanupReceipt(
        resource.resource_id, "needed"
    )
    resource = disposal.release_owned(resource)
    for altered, result in (
        (replace(resource, _creation=object()), "ownership_unknown"),
        (replace(resource, boundary=root / "foreign"), "unsafe_path"),
    ):
        assert disposal.dispose_owned(altered) == disposal.CleanupReceipt(
            resource.resource_id, result
        )
        assert marker.read_bytes() == b"keep"
    wrong = replace(resource, identity=(resource.identity[0] ^ 1, resource.identity[1]))
    refused = disposal.dispose_owned(wrong)
    assert refused.result == (
        "cleanup_pending" if kind == "directory" else "identity_changed"
    )
    assert refused.complete is (kind == "file")
    assert refused.deleted_files == refused.deleted_directories == 0
    assert marker.read_bytes() == b"keep"
    retained = disposal.dispose_owned(
        resource, config=TemporaryFilesConfig(retain_unused=True)
    )
    assert retained == disposal.CleanupReceipt(
        resource.resource_id, "retained_by_configuration"
    )
    assert marker.read_bytes() == b"keep"
    deleted = disposal.dispose_owned(resource)
    assert deleted.result == "deleted" and deleted.complete
    assert deleted.deleted_files == 1 and deleted.deleted_bytes == 4
    assert deleted.deleted_directories == int(kind == "directory")
    assert disposal.dispose_owned(resource) == disposal.CleanupReceipt(
        resource.resource_id, "already_absent"
    )
