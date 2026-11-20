"""W52 semantic faults at the Windows owner-close cleanup boundary."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from processforge_core.prepared import input as prepared
from processforge_core.work import capsule_publication as capsule
from processforge_core.work.compact_model import CompactError, ObjectRef
from processforge_core.work.compact_objects import (
    ProjectObjectStore,
    object_relative_path,
)

STAGED: dict[Path, Any] = {}


def staged_bytes(path: Path) -> bytes:
    stream = STAGED.get(path)
    if stream is not None and not stream.closed:
        position = stream.tell()
        stream.seek(0)
        raw = stream.read()
        stream.seek(position)
        return raw
    return path.read_bytes()


RAW = b"x" * 4096
KINDS = ("capsule", "prepared", "object")
FAULTS = (
    "short",
    "zero",
    "none",
    "negative",
    "oversize",
    "float",
    "bool",
    "write",
    "flush",
    "fsync",
    "link",
    "cancel",
)


class Cancel(BaseException):
    """Cancellation deliberately outside Exception."""


@dataclass
class Writer:
    destination: Path
    raw: bytes
    run: Callable[[], object]


def writer(kind: str, root: Path) -> Writer:
    root.mkdir(parents=True, exist_ok=True)
    if kind == "capsule":
        dest = root / "accepted"
        return Writer(dest, RAW, lambda: capsule.publish_capsule_bytes(dest, RAW))
    if kind == "prepared":
        dest = root / "accepted"
        document = {"x": "x" * 4096}
        return Writer(
            dest,
            prepared.encoded(document),
            lambda: prepared.write_once(dest, document),
        )
    ref = ObjectRef(
        "sha256",
        hashlib.sha256(RAW).hexdigest(),
        len(RAW),
        "application/octet-stream",
        "raw.v1",
    )
    store = ProjectObjectStore(
        root, authorize=lambda *args: None, sync_directory=lambda path: None
    )
    return Writer(
        root / object_relative_path(ref), RAW, lambda: store.publish(ref, [RAW])
    )


def snapshot(root: Path) -> list[dict[str, Any]]:
    return [
        dict(
            path=p.relative_to(root).as_posix(),
            size=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        )
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def record(name: str, data: object) -> None:
    directory = Path(os.environ["W52_TMP"]) / "observations" / os.environ["W52_LABEL"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (name + ".json")).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def inject(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    primary: BaseException,
    *,
    cleanup: BaseException | None = None,
    close_error: BaseException | None = None,
) -> tuple[list[Path], list[str]]:
    original = capsule.tempfile.NamedTemporaryFile
    unlink = Path.unlink
    lstat = Path.lstat
    exists = Path.exists
    closed = False
    paths: list[Path] = []
    events: list[str] = []

    class Proxy:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.stream = original(*args, **kwargs)
            paths.append(Path(self.stream.name))
            STAGED[paths[-1]] = self.stream

        def __enter__(self) -> Proxy:
            self.stream.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            nonlocal closed
            self.stream.__exit__(*args)
            closed = True
            if close_error is not None:
                raise close_error
            return None

        def __getattr__(self, name: str) -> Any:
            return getattr(self.stream, name)

        def write(self, raw: bytes) -> Any:
            events.append("write")
            if fault in ("write", "cancel"):
                self.stream.write(raw[:17])
                raise primary
            if fault == "short":
                return self.stream.write(raw[:17])
            if fault == "zero":
                return 0
            if fault == "none":
                return None
            if fault == "negative":
                return -1
            if fault == "oversize":
                return len(raw) + 1
            if fault == "float":
                self.stream.write(raw)
                return float(len(raw))
            if fault == "bool":
                return True
            return self.stream.write(raw)

        def flush(self) -> None:
            events.append("flush")
            if fault == "flush":
                raise primary
            self.stream.flush()

    def sync(descriptor: int) -> None:
        events.append("fsync")
        if fault == "fsync":
            raise primary
        original_sync(descriptor)

    def link(source: Any, dest: Any, *args: Any, **kwargs: Any) -> None:
        events.append("link")
        if fault == "link":
            raise primary
        original_link(source, dest, *args, **kwargs)

    def dispose(path: Path, *args: Any, **kwargs: Any) -> None:
        if path in paths and cleanup is not None:
            raise cleanup
        unlink(path, *args, **kwargs)

    def inspect(path: Path, *args: Any, **kwargs: Any) -> Any:
        if os.name == "nt" and closed and path in paths and cleanup is not None:
            raise cleanup
        return lstat(path, *args, **kwargs)

    def present(path: Path) -> bool:
        if os.name == "nt" and closed and path in paths and cleanup is not None:
            raise cleanup
        return exists(path)

    monkeypatch.setattr(Path, "exists", present)
    monkeypatch.setattr(Path, "lstat", inspect)
    original_sync, original_link = os.fsync, os.link
    monkeypatch.setattr(capsule.tempfile, "NamedTemporaryFile", Proxy)
    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(Path, "unlink", dispose)
    return paths, events


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("fault", FAULTS)
def test_fault_never_publishes(
    kind: str, fault: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = Cancel("cancel") if fault == "cancel" else OSError("primary-" + fault)
    with monkeypatch.context() as patch:
        paths, events = inject(patch, fault, primary)
        with pytest.raises(BaseException) as caught:
            case.run()
    record(
        kind + "-" + fault,
        dict(
            error=type(caught.value).__name__,
            primary_identity=caught.value is primary,
            files=snapshot(tmp_path),
            events=events,
        ),
    )
    assert not case.destination.exists()
    assert not any(path.exists() for path in paths)
    if fault in ("write", "flush", "fsync", "link", "cancel"):
        assert caught.value is primary
    else:
        assert events == ["write"], (
            "invalid write count must stop before flush/fsync/link"
        )
        assert isinstance(caught.value, (OSError, CompactError))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("cancel", [False, True])
def test_primary_and_cleanup_failure(
    kind: str, cancel: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = Cancel("primary-cancel") if cancel else OSError("primary-write")
    cleanup = PermissionError("cleanup-denied")
    with monkeypatch.context() as patch:
        paths, _ = inject(patch, "write", primary, cleanup=cleanup)
        with pytest.raises(BaseException) as caught:
            case.run()
    notes = getattr(caught.value, "__notes__", [])
    record(
        kind + "-double-" + str(cancel),
        dict(
            error=type(caught.value).__name__,
            primary_identity=caught.value is primary,
            cleanup_notes=[note.replace(str(tmp_path), "<FIXTURE>") for note in notes],
            files=snapshot(tmp_path),
        ),
    )
    assert caught.value is primary
    assert not case.destination.exists()
    assert len(paths) == 1
    if os.name == "nt":
        assert not paths[0].exists(), "kernel close already removed owned staging"
    else:
        assert paths[0].read_bytes() == case.raw[:17]
    assert any(
        str(paths[0]) in note
        and "PermissionError: cleanup-denied" in note
        and "publication=not_linked" in note
        for note in notes
    )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("cancel", [False, True])
def test_cleanup_failure_after_link(
    kind: str, cancel: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    cleanup = Cancel("cleanup-cancel") if cancel else PermissionError("cleanup-denied")
    with monkeypatch.context() as patch:
        paths, _ = inject(patch, "success", OSError("unused"), cleanup=cleanup)
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is cleanup
    assert case.destination.read_bytes() == case.raw
    assert len(paths) == 1
    if os.name == "nt":
        assert not paths[0].exists()
    else:
        assert paths[0].stat().st_ino == case.destination.stat().st_ino
    notes = getattr(cleanup, "__notes__", [])
    assert any(str(paths[0]) in note and "publication=linked" in note for note in notes)
    before = case.destination.stat().st_ino
    if kind == "object":
        case.run()
    else:
        with pytest.raises(FileExistsError):
            case.run()
    assert (
        case.destination.stat().st_ino == before
        and case.destination.read_bytes() == case.raw
    )
    assert paths[0].exists() is (os.name != "nt")
    # POSIX denied unlink retains the old name; Windows owner close removes it.
    # Foreign/live ownership assertions remain in the repeat and nested tests.
    record(
        kind + "-post-link-" + str(cancel),
        dict(
            files=snapshot(tmp_path),
            publication="linked",
            cleanup_identity=caught.value is cleanup,
        ),
    )


@pytest.mark.parametrize("kind", KINDS)
def test_100_fixed_size_attempts(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    case.run()
    accepted = case.destination.stat().st_ino
    foreign = case.destination.parent / ("." + kind + "-foreign.tmp")
    foreign.write_bytes(b"foreign-live-staging")
    foreign_inode = foreign.stat().st_ino
    rows = []
    cycle = (
        "success",
        "write",
        "short",
        "zero",
        "flush",
        "fsync",
        "link",
        "cancel",
        "success",
        "success",
    )
    for index in range(100):
        fault = cycle[index % len(cycle)]
        primary = Cancel("cancel") if fault == "cancel" else OSError("primary-" + fault)
        error: BaseException | None = None
        with monkeypatch.context() as patch:
            paths, _ = inject(patch, fault, primary)
            try:
                case.run()
            except BaseException as exc:
                error = exc
        owned = [path for path in paths if path.exists()]
        assert not owned
        assert (
            case.destination.read_bytes() == case.raw
            and case.destination.stat().st_ino == accepted
        )
        assert (
            foreign.read_bytes() == b"foreign-live-staging"
            and foreign.stat().st_ino == foreign_inode
        )
        all_staging = [
            row for row in snapshot(tmp_path) if row["path"].endswith(".tmp")
        ]
        rows.append(
            dict(
                attempt=index,
                fault=fault,
                error=type(error).__name__ if error else None,
                owned_staging_count=len(owned),
                owned_staging_bytes=sum(path.stat().st_size for path in owned),
                all_staging_count=len(all_staging),
                all_staging_bytes=sum(row["size"] for row in all_staging),
                destination_size=case.destination.stat().st_size,
                destination_sha256=hashlib.sha256(
                    case.destination.read_bytes()
                ).hexdigest(),
                destination_inode_unchanged=True,
            )
        )
    record("repeat-" + kind, rows)
    assert all(
        row["all_staging_count"] == 1
        and row["all_staging_bytes"] == len(b"foreign-live-staging")
        for row in rows
    )


@pytest.mark.parametrize("kind", KINDS)
def test_nested_concurrent_writer_keeps_live_staging(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    original = os.link
    factory = capsule.tempfile.NamedTemporaryFile
    active = False

    def create(*args: Any, **kwargs: Any) -> Any:
        stream = factory(*args, **kwargs)
        STAGED[Path(stream.name)] = stream
        return stream

    def link(source: Path, destination: Path) -> None:
        nonlocal active
        if not active:
            active = True
            assert staged_bytes(source) == case.raw
            case.run()
            assert source.exists(), "inner publisher removed outer staging"
        original(source, destination)

    with monkeypatch.context() as patch:
        patch.setattr(capsule.tempfile, "NamedTemporaryFile", create)
        patch.setattr(os, "link", link)
        if kind == "object":
            case.run()
        else:
            with pytest.raises(FileExistsError):
                case.run()
    assert case.destination.read_bytes() == case.raw
    assert not any(row["path"].endswith(".tmp") for row in snapshot(tmp_path))


@pytest.mark.parametrize("kind", KINDS)
def test_cleanup_identity_mismatch_retains_replacement(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = OSError("link-failed")
    renamed: list[Path] = []

    original_factory = capsule.tempfile.NamedTemporaryFile

    class ReplacedAfterClose:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.stream = original_factory(*args, **kwargs)

        def __enter__(self) -> Any:
            return self.stream.__enter__()

        def __exit__(self, *args: Any) -> None:
            self.stream.__exit__(*args)
            Path(self.stream.name).write_bytes(b"foreign-replacement")

    def replace_and_fail(source: Path, destination: Path) -> None:
        saved = source.with_suffix(".owned")
        if os.name == "nt":
            saved.write_bytes(case.raw)
            renamed.append(saved)
            raise primary
        source.rename(saved)
        renamed.append(saved)
        source.write_bytes(b"foreign-replacement")
        raise primary

    with monkeypatch.context() as patch:
        if os.name == "nt":
            patch.setattr(capsule.tempfile, "NamedTemporaryFile", ReplacedAfterClose)
        patch.setattr(os, "link", replace_and_fail)
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is primary
    assert renamed[0].read_bytes() == case.raw
    assert renamed[0].with_suffix(".tmp").read_bytes() == b"foreign-replacement"
    assert any(
        ("staging_cleanup_pending" if os.name == "nt" else "temporary_changed") in note
        for note in getattr(primary, "__notes__", [])
    )


def test_prepared_legacy_bytes_and_digest(tmp_path: Path) -> None:
    document = {"z": "русский\u0000", "a": [1, False, None]}
    expected = (
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    ).encode()
    assert (
        prepared.write_once(tmp_path / "accepted", document)
        == "sha256:" + hashlib.sha256(expected).hexdigest()
    )
    assert (tmp_path / "accepted").read_bytes() == expected


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("cancel", [False, True])
def test_stream_close_keeps_body_primary(
    kind: str, cancel: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = Cancel("body-cancel") if cancel else OSError("body-write")
    close_error = PermissionError("close-denied")
    with monkeypatch.context() as patch:
        paths, _ = inject(patch, "write", primary, close_error=close_error)
        with pytest.raises(BaseException) as caught:
            case.run()
    record(
        kind + "-close-" + str(cancel),
        dict(primary_identity=caught.value is primary, files=snapshot(tmp_path)),
    )
    assert caught.value is primary
    assert not case.destination.exists() and not any(path.exists() for path in paths)
    assert any(
        str(paths[0]) in note and "PermissionError: close-denied" in note
        for note in getattr(primary, "__notes__", [])
    )


@pytest.mark.parametrize("kind", KINDS)
def test_stream_close_then_unlink_keeps_first_primary(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    primary = Cancel("body-cancel")
    close_error = PermissionError("close-denied")
    cleanup = OSError("unlink-denied")
    with monkeypatch.context() as patch:
        paths, _ = inject(
            patch, "write", primary, close_error=close_error, cleanup=cleanup
        )
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is primary
    notes = getattr(primary, "__notes__", [])
    assert any("close-denied" in note for note in notes)
    assert any("unlink-denied" in note for note in notes)
    assert not case.destination.exists()
    if os.name == "nt":
        assert not paths[0].exists()
    else:
        assert paths[0].read_bytes() == case.raw[:17]


@pytest.mark.parametrize("kind", KINDS)
def test_stream_close_failure_before_link(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer(kind, tmp_path)
    close_error = Cancel("close-cancel")
    with monkeypatch.context() as patch:
        paths, _ = inject(patch, "success", OSError("unused"), close_error=close_error)
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is close_error
    if os.name == "nt":
        assert case.destination.read_bytes() == case.raw
        assert not any(path.exists() for path in paths)
    else:
        assert not case.destination.exists() and not any(
            path.exists() for path in paths
        )


@pytest.mark.parametrize("double", [False, True])
def test_object_directory_sync_cleanup_failure(tmp_path: Path, double: bool) -> None:
    ref = ObjectRef(
        "sha256",
        hashlib.sha256(RAW).hexdigest(),
        len(RAW),
        "application/octet-stream",
        "raw.v1",
    )
    destination = tmp_path / object_relative_path(ref)
    primary, cleanup = OSError("publication-sync"), PermissionError("cleanup-sync")

    def sync(path: Path) -> None:
        if destination.exists():
            if list(destination.parent.glob(".compact-*.tmp")):
                if double:
                    raise primary
            else:
                raise cleanup

    store = ProjectObjectStore(
        tmp_path, authorize=lambda *args: None, sync_directory=sync
    )
    with pytest.raises(BaseException) as caught:
        store.publish(ref, [RAW])
    assert caught.value is (primary if double else cleanup)
    assert destination.read_bytes() == RAW and not list(
        destination.parent.glob(".compact-*.tmp")
    )
    assert any(
        "step=sync_directory" in note
        and "publication=linked" in note
        and "cleanup-sync" in note
        for note in getattr(caught.value, "__notes__", [])
    )


def test_existing_object_cleanup_reports_verified_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = writer("object", tmp_path)
    case.run()
    inode = case.destination.stat().st_ino
    cleanup = PermissionError("cleanup-reuse")
    with monkeypatch.context() as patch:
        inject(patch, "success", OSError("unused"), cleanup=cleanup)
        with pytest.raises(BaseException) as caught:
            case.run()
    assert caught.value is cleanup
    assert (
        case.destination.read_bytes() == case.raw
        and case.destination.stat().st_ino == inode
    )
    assert any(
        "publication=existing_verified" in note
        for note in getattr(cleanup, "__notes__", [])
    )
