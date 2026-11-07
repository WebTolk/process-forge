"""Real IO reconstruction of Q65 F66-01, not the lost original test bytes.

Provenance: Q65 raw traceback b13569ca3b0fcd220a4b183c13c453056ca3f5cdaed7ec9207ceaca94f85b679.
Faults wrap the actual staging file and leave storage assertions independent of
the injected call counts. No production module is replaced with a stub.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from processforge_core.executions.model import ExecutionError
from processforge_core.prepared.retry_publication import publish_raw_once


@pytest.fixture
def destination(tmp_path: Path) -> Path:
    target = tmp_path / ".pf/runtime/agent-runs/run/task/attempts/1/archive.json"
    target.parent.mkdir(parents=True)
    return target


def project(destination: Path) -> Path:
    return destination.parents[7]


@pytest.mark.parametrize("raw", [b"", b"x" * 945, b"\xff\x00\xfe\r\n" * 189])
def test_exact_replay_and_conflict(destination: Path, raw: bytes) -> None:
    publish_raw_once(project(destination), destination, raw)
    identity = destination.stat().st_ino
    publish_raw_once(project(destination), destination, raw)
    assert destination.read_bytes() == raw
    assert destination.stat().st_ino == identity
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        publish_raw_once(project(destination), destination, raw + b"different")
    assert destination.read_bytes() == raw
    assert not list(destination.parent.glob(".retry-*.tmp"))


@pytest.mark.parametrize("fault", ["raise", "short", "zero", "none"])
def test_real_short_write(
    destination: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original_open = Path.open
    raw = b"\xff\x00\xfe\r\n" * 189
    assert len(raw) == 945
    original = destination.with_name("original.bin")
    original.write_bytes(raw)

    class Writer:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> Any:
            self.stream.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.stream.__exit__(*args)

        def write(self, value: Any) -> Any:
            if fault == "zero":
                return 0
            if fault == "none":
                return None
            count = self.stream.write(value[:17])
            if fault == "raise":
                raise OSError("injected after real 17 bytes")
            return count

        def flush(self) -> None:
            self.stream.flush()

        def fileno(self) -> int:
            return self.stream.fileno()

    def faulty_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        stream = original_open(path, mode, *args, **kwargs)
        if mode == "xb" and path.name.startswith(".retry-"):
            return Writer(stream)
        return stream

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", faulty_open)
        if fault == "short":
            publish_raw_once(project(destination), destination, raw)
        else:
            with pytest.raises(OSError):
                publish_raw_once(project(destination), destination, raw)
            assert not destination.exists()
    assert original.read_bytes() == raw
    assert not list(destination.parent.glob(".retry-*.tmp"))
    publish_raw_once(project(destination), destination, raw)
    assert destination.read_bytes() == raw


@pytest.mark.parametrize("committed", [False, True])
def test_link_failure(
    destination: Path, monkeypatch: pytest.MonkeyPatch, committed: bool
) -> None:
    real_link = os.link

    def link(source: Any, target: Any) -> None:
        if committed:
            real_link(source, target)
        raise OSError("injected link boundary")

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(OSError, match="injected link boundary"):
            publish_raw_once(project(destination), destination, b"raw\xff")
    assert destination.exists() == committed
    publish_raw_once(project(destination), destination, b"raw\xff")
    assert destination.read_bytes() == b"raw\xff"


def test_fsync_failure(destination: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(descriptor: int) -> None:
        raise OSError("injected fsync")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail)
        with pytest.raises(OSError, match="injected fsync"):
            publish_raw_once(project(destination), destination, b"raw")
    assert not destination.exists()
    assert not list(destination.parent.glob(".retry-*.tmp"))
    publish_raw_once(project(destination), destination, b"raw")
    assert destination.read_bytes() == b"raw"


def test_old_poison_is_preserved(destination: Path) -> None:
    destination.write_bytes(b"x" * 17)
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        publish_raw_once(project(destination), destination, b"x" * 945)
    assert destination.read_bytes() == b"x" * 17
