"""Windows product lifetime, disk readback, sharing and ownership regressions."""

from __future__ import annotations

import errno
import os
from pathlib import Path
from typing import Any

import pytest

from processforge_core.work import capsule_publication as capsule
from processforge_core.work.compact_model import CompactError
from tests.work.test_immutable_publication import KINDS, Cancel, inject, record, writer

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows lifetime only")


@pytest.mark.parametrize("kind", KINDS)
def test_sole_exclusive_binary_noninheritable_descriptor(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open, original_link = os.open, os.link
    opened: list[tuple[int, int]] = []
    ordinary_reader: list[int | None] = []
    case = writer(kind, tmp_path)

    def create(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if str(path).endswith(".tmp"):
            opened.append((descriptor, flags))
            assert not os.get_inheritable(descriptor)
        return descriptor

    def link(source: Path, destination: Path) -> None:
        assert len(opened) == 1
        assert os.fstat(opened[0][0]).st_size == len(case.raw)
        original_link(source, destination)
        try:
            assert destination.read_bytes() == case.raw
        except PermissionError as exc:
            ordinary_reader.append(exc.winerror)
        else:
            ordinary_reader.append(None)

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", create)
        patch.setattr(os, "link", link)
        case.run()
    flags = opened[0][1]
    for expected in (os.O_RDWR, os.O_CREAT, os.O_EXCL, os.O_BINARY, os.O_TEMPORARY):
        assert flags & expected
    with pytest.raises(OSError) as caught:
        os.fstat(opened[0][0])
    assert caught.value.errno == errno.EBADF
    assert ordinary_reader[0] in (None, 5, 32), ordinary_reader
    assert case.destination.read_bytes() == case.raw
    assert not list(case.destination.parent.glob("*.tmp"))
    record(
        "sharing-" + kind,
        dict(
            flags=flags,
            staged_opens=len(opened),
            reader_winerror=ordinary_reader,
            after_return_read=True,
        ),
    )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("fault", ("corrupt", "truncate", "extend", "identity"))
@pytest.mark.parametrize("existing", (False, True))
def test_verify_actual_staged_disk_bytes_and_identity(
    kind: str,
    fault: str,
    existing: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = writer(kind, tmp_path)
    accepted = None
    if existing:
        case.run()
        accepted = case.destination.stat().st_ino
    original_sync, original_stat = os.fsync, os.fstat
    changed = False

    def sync(descriptor: int) -> None:
        nonlocal changed
        original_sync(descriptor)
        if fault == "corrupt":
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.write(descriptor, b"!")
        elif fault == "truncate":
            os.ftruncate(descriptor, 17)
        elif fault == "extend":
            os.ftruncate(descriptor, len(case.raw) + 1)
        changed = True

    def inspect(descriptor: int) -> os.stat_result:
        info = original_stat(descriptor)
        if changed and fault == "identity":
            fields = list(info)
            fields[1] += 1
            return os.stat_result(fields)
        return info

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", sync)
        patch.setattr(os, "fstat", inspect)
        with pytest.raises((OSError, CompactError)):
            case.run()
    if existing:
        assert case.destination.stat().st_ino == accepted
        assert case.destination.read_bytes() == case.raw
    else:
        assert not case.destination.exists()
    assert not list(case.destination.parent.glob("*.tmp"))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("fault", ("write", "flush", "fsync", "link", "cancel"))
def test_primary_identity_across_close_and_cleanup_double_faults(
    kind: str, fault: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = Cancel("primary-" + fault)
    with monkeypatch.context() as patch:
        paths, _ = inject(
            patch,
            fault,
            primary,
            close_error=PermissionError("secondary-close"),
            cleanup=OSError("secondary-cleanup"),
        )
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is primary
    notes = getattr(primary, "__notes__", [])
    assert any("secondary-close" in note for note in notes)
    assert any("secondary-cleanup" in note for note in notes)
    assert not case.destination.exists()
    assert not any(path.exists() for path in paths)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("primary_fault", (False, True))
def test_external_duplicate_delays_kernel_cleanup_without_retry(
    kind: str, primary_fault: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    original = os.fsync
    duplicates: list[int] = []
    primary = Cancel("actual-extended-lifetime")
    try:

        def sync(descriptor: int) -> None:
            duplicates.append(os.dup(descriptor))
            original(descriptor)
            if primary_fault:
                raise primary

        with monkeypatch.context() as patch:
            patch.setattr(os, "fsync", sync)
            with pytest.raises(BaseException) as caught:
                case.run()
        assert len(duplicates) == 1
        if primary_fault:
            assert caught.value is primary
            assert not case.destination.exists()
        assert getattr(caught.value, "__notes__", [])
        assert len(list(case.destination.parent.glob("*.tmp"))) == 1
    finally:
        for descriptor in duplicates:
            os.close(descriptor)
    assert not list(case.destination.parent.glob("*.tmp"))
    if not primary_fault:
        assert case.destination.read_bytes() == case.raw


@pytest.mark.parametrize("kind", KINDS)
def test_close_error_cannot_double_close_reused_descriptor(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    factory = capsule.tempfile.NamedTemporaryFile
    replacement: list[int] = []
    close_error = Cancel("close-after-ownership-lost")
    unrelated = tmp_path / "unrelated"

    class Stream:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.stream = factory(*args, **kwargs)

        def __enter__(self) -> Any:
            return self.stream.__enter__()

        def __exit__(self, *args: Any) -> None:
            number = self.stream.fileno()
            self.stream.__exit__(*args)
            descriptor = os.open(
                unrelated, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_BINARY, 0o600
            )
            replacement.append(descriptor)
            assert descriptor == number, "fixture must actually reuse the fd"
            raise close_error

    try:
        with monkeypatch.context() as patch:
            patch.setattr(capsule.tempfile, "NamedTemporaryFile", Stream)
            with pytest.raises(Cancel) as caught:
                case.run()
        assert caught.value is close_error
        assert os.write(replacement[0], b"unrelated-preserved") == 19
    finally:
        for descriptor in replacement:
            os.close(descriptor)
    assert unrelated.read_bytes() == b"unrelated-preserved"
    assert case.destination.read_bytes() == case.raw
