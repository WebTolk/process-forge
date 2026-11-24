"""Exercise registry marker publication with the native file and OS guard."""

from __future__ import annotations

import errno
import json
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from processforge_core.runtime import execution_admission as registry

if TYPE_CHECKING:
    from pathlib import Path


def _replace_marker(marker: Path, change: str) -> bytes:
    original = marker.read_bytes()
    owner = json.loads(original)
    if change == "numeric":
        owner["pid"] = float(owner["pid"])
        replacement = (
            json.dumps(owner, ensure_ascii=False, sort_keys=True) + os.linesep
        ).encode("utf-8")
        assert type(json.loads(replacement)["pid"]) is float
    else:
        assert change == "whitespace"
        replacement = b" " + original
    assert replacement != original
    assert json.loads(replacement) == owner
    temporary = marker.with_suffix(".replacement")
    temporary.write_bytes(replacement)
    temporary.replace(marker)
    return replacement


def _assert_reacquired(gate: Path) -> None:
    with registry.try_registry_file_lock(
        gate, owner=registry.prepare_registry_owner()
    ) as result:
        assert result == "acquired"
    assert list(gate.parent.iterdir()) == [gate.with_name(f".{gate.name}.lock.guard")]


def test_legacy_publication_retains_native_bytes_and_guard(tmp_path: Path) -> None:
    gate = tmp_path / "café"
    marker = tmp_path / ".café.lock"
    owner = registry.prepare_registry_owner()
    with registry.registry_file_lock(gate):
        raw = marker.read_bytes()
        published = json.loads(raw)
        assert published["path"] == str(gate)
        assert {key: published[key] for key in owner.fields} == owner.fields
        expected = json.dumps(published, ensure_ascii=False, sort_keys=True)
        assert raw == (expected + os.linesep).encode("utf-8")
        with registry.try_registry_file_lock(gate, owner=owner) as result:
            assert result == "guard_busy"
    _assert_reacquired(gate)


@pytest.mark.parametrize("change", ["numeric", "whitespace"])
def test_normal_exit_preserves_byte_distinct_marker(
    tmp_path: Path, change: str
) -> None:
    gate = tmp_path / "registry"
    marker = tmp_path / ".registry.lock"
    owner = registry.prepare_registry_owner()
    with registry.try_registry_file_lock(gate, owner=owner) as result:
        assert result == "acquired"
        replacement = _replace_marker(marker, change)
    assert marker.read_bytes() == replacement
    with registry.try_registry_file_lock(gate, owner=owner) as result:
        assert result == "owner_marker"
    marker.unlink()
    _assert_reacquired(gate)


@pytest.mark.parametrize("change", [None, "numeric", "whitespace"])
def test_publication_expiry_unwinds_with_exact_marker_identity(
    tmp_path: Path, change: str | None
) -> None:
    gate = tmp_path / "registry"
    marker = tmp_path / ".registry.lock"
    original_fsync = os.fsync
    synced = False
    replacement = None

    def sync(fd: int) -> None:
        nonlocal synced
        original_fsync(fd)
        synced = True

    def monotonic() -> float:
        nonlocal replacement
        if not synced:
            return 0.0
        if change is not None:
            replacement = _replace_marker(marker, change)
        return 1.0

    with (
        patch.object(registry.time, "monotonic", side_effect=monotonic),
        patch.object(os, "fsync", side_effect=sync),
        pytest.raises(registry.RegistryLockTimeout) as caught,
        registry.wait_registry_file_lock(gate, deadline=1.0),
    ):
        pytest.fail("entered an expired lease")

    assert (caught.value.phase, caught.value.assessment) == (
        "owner",
        "deadline_expired",
    )
    if change is None:
        assert not marker.exists()
    else:
        assert replacement is not None
        assert marker.read_bytes() == replacement
        with registry.try_registry_file_lock(
            gate, owner=registry.prepare_registry_owner()
        ) as result:
            assert result == "owner_marker"
        marker.unlink()
    _assert_reacquired(gate)


def test_failed_publication_removes_incomplete_marker(tmp_path: Path) -> None:
    gate = tmp_path / "registry"
    marker = tmp_path / ".registry.lock"
    original_fsync = os.fsync

    def fail_sync(fd: int) -> None:
        original_fsync(fd)
        raise OSError(errno.EIO, "fixture sync failure")

    with (
        patch.object(os, "fsync", side_effect=fail_sync),
        pytest.raises(OSError) as caught,
        registry.try_registry_file_lock(gate, owner=registry.prepare_registry_owner()),
    ):
        pytest.fail("entered after a failed publication")

    assert caught.value.errno == errno.EIO
    assert not marker.exists()
    _assert_reacquired(gate)
