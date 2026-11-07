"""Real raw publication IO boundaries complementing retained W73 regressions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from processforge_core.executions.model import ExecutionError
from processforge_core.prepared import retry_publication as rp


@pytest.mark.parametrize("fault", ["flush", "close"])
def test_flush_close_failure_before_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    target = tmp_path / ".pf/runtime/agent-runs/r/t/attempts/1/raw.json"
    target.parent.mkdir(parents=True)
    real_open = Path.open

    class Writer:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            self.stream.close()
            if fault == "close":
                raise OSError("close boundary")

        def write(self, raw: Any) -> int:
            return self.stream.write(raw)

        def flush(self) -> None:
            if fault == "flush":
                raise OSError("flush boundary")
            self.stream.flush()

        def fileno(self) -> int:
            return self.stream.fileno()

    def opening(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        stream = real_open(path, mode, *args, **kwargs)
        return Writer(stream) if mode == "xb" else stream

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opening)
        with pytest.raises(OSError, match="boundary"):
            rp.publish_raw_once(tmp_path, target, b"\xff" * 945)
    assert not target.exists()
    assert not list(target.parent.glob(".retry-*.tmp"))
    rp.publish_raw_once(tmp_path, target, b"\xff" * 945)
    assert target.read_bytes() == b"\xff" * 945


@pytest.mark.parametrize("primary", [False, True])
def test_cleanup_failure_is_visible_and_final_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, primary: bool
) -> None:
    target = tmp_path / ".pf/runtime/agent-runs/r/t/attempts/1/raw.json"
    target.parent.mkdir(parents=True)
    real_link, real_unlink = os.link, Path.unlink

    def unlink(path: Path, *a: Any, **k: Any) -> None:
        if path.name.startswith(".retry-"):
            raise OSError("cleanup boundary")
        real_unlink(path, *a, **k)

    def link(source: Any, destination: Any) -> None:
        real_link(source, destination)
        if primary:
            raise OSError("primary boundary")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", unlink)
        patch.setattr(os, "link", link)
        with pytest.raises(
            OSError, match="primary boundary" if primary else "cleanup boundary"
        ) as error:
            rp.publish_raw_once(tmp_path, target, b"raw\xff")
        if primary:
            assert "retry_staging_cleanup:OSError" in error.value.__notes__
    orphan = next(target.parent.glob(".retry-*.tmp"))
    orphan_identity = orphan.stat().st_ino
    assert target.read_bytes() == b"raw\xff"
    rp.publish_raw_once(tmp_path, target, b"raw\xff")
    assert orphan.stat().st_ino == orphan_identity  # No orphan adoption by age/name.


def test_cleanup_never_unlinks_replaced_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / ".pf/runtime/agent-runs/r/t/attempts/1/raw.json"
    target.parent.mkdir(parents=True)
    real_link = os.link
    saved: list[Path] = []

    def link(source: Any, destination: Any) -> None:
        real_link(source, destination)
        source = Path(source)
        source.unlink()
        source.write_bytes(b"foreign-object")
        saved.append(source)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(ExecutionError, match="execution_identity_conflict"):
            rp.publish_raw_once(tmp_path, target, b"original")
    assert target.read_bytes() == b"original"
    assert saved[0].read_bytes() == b"foreign-object"


def test_exact_existing_sync_failure_remains_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / ".pf/runtime/agent-runs/r/t/attempts/1/raw.json"
    target.parent.mkdir(parents=True)
    rp.publish_raw_once(tmp_path, target, b"raw")
    real_sync = os.fsync

    def fsync(fd: int) -> None:
        # Staging is one link; the existing destination is the target inode.
        if os.fstat(fd).st_ino == target.stat().st_ino:
            raise OSError("existing final sync")
        real_sync(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fsync)
        with pytest.raises(OSError, match="existing final sync"):
            rp.publish_raw_once(tmp_path, target, b"raw")
    assert target.read_bytes() == b"raw"
