"""Exercise create-once publication on the native filesystem."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import BinaryIO

import pytest

from processforge_core.maintenance import project_event_publication as publication

_INTERRUPT_WRITER = """
import os
import sys
from pathlib import Path

from processforge_core.maintenance import project_event_publication as publication

publish_staged = publication._publish_staged

def interrupt(staging, destination):
    if sys.argv[3] == "after":
        publish_staged(staging, destination)
    os._exit(37)

publication._publish_staged = interrupt
publication.publish_immutable_bytes(Path(sys.argv[1]), bytes.fromhex(sys.argv[2]))
"""


def _canonical(document: dict[str, str]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.parametrize("entry", ["selector", "plan"])
@pytest.mark.parametrize("boundary", ["before", "after"])
def test_process_interruption_and_recovery(
    tmp_path: Path, entry: str, boundary: str
) -> None:
    plan = {"store_id": "82e2cf791eab448a8fc766d48ce43eb4"}
    checksum = "sha256:" + hashlib.sha256(_canonical(plan)).hexdigest()
    data = _canonical({**plan, "plan_checksum": checksum}) + b"\n"
    selector = tmp_path / "selector.json"
    journal = tmp_path / checksum.removeprefix("sha256:")
    journal.mkdir()
    plan_path = journal / "plan.json"

    if entry == "plan":
        publication.publish_immutable_bytes(selector, data)
    interrupted_path = selector if entry == "selector" else plan_path

    child = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            _INTERRUPT_WRITER,
            str(interrupted_path),
            data.hex(),
            boundary,
        ],
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=30,
        check=False,
    )
    assert child.returncode == 37, child.stderr.decode(errors="replace")

    if boundary == "before":
        assert not interrupted_path.exists()
    else:
        assert interrupted_path.read_bytes() == data

    # A restart with a selector uses the persisted identity for both names.
    # Before the first selector becomes visible there is no identity to reuse.
    if not selector.exists():
        assert (entry, boundary) == ("selector", "before")
        publication.publish_immutable_bytes(selector, data)
    selector_bytes = selector.read_bytes()
    recovered = json.loads(selector_bytes)
    assert recovered["store_id"] == plan["store_id"]
    assert recovered["plan_checksum"] == checksum
    assert (
        "sha256:"
        + hashlib.sha256(_canonical({"store_id": recovered["store_id"]})).hexdigest()
        == checksum
    )
    publication.publish_immutable_bytes(selector, selector_bytes)
    recovered_journal = tmp_path / recovered["plan_checksum"].removeprefix("sha256:")
    publication.publish_immutable_bytes(recovered_journal / "plan.json", selector_bytes)
    assert selector.read_bytes() == plan_path.read_bytes() == data


@pytest.mark.parametrize("name", ["selector.json", "plan.json"])
@pytest.mark.parametrize("identical", [True, False])
def test_competing_publishers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, identical: bool
) -> None:
    path = tmp_path / name
    staged = Barrier(2)
    publish_staged = publication._publish_staged

    def race(staging: Path, destination: Path) -> None:
        staged.wait(timeout=15)
        publish_staged(staging, destination)

    monkeypatch.setattr(publication, "_publish_staged", race)
    payloads = (b"first\n", b"first\n" if identical else b"second\n")
    winners: list[bytes] = []
    conflicts: list[bytes] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(publication.publish_immutable_bytes, path, data)
            for data in payloads
        ]
        for data, result in zip(payloads, results, strict=True):
            try:
                result.result(timeout=20)
            except publication.PublicationConflict:
                conflicts.append(data)
            else:
                winners.append(data)

    assert winners == [path.read_bytes()] * (2 if identical else 1)
    assert len(conflicts) == (0 if identical else 1)
    assert all(data != winners[0] for data in conflicts)
    assert list(tmp_path.iterdir()) == [path]


def test_reuses_complete_historical_bytes_and_rejects_partial_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "plan.json"
    data = b'{"plan_checksum":"sha256:historical","store_id":"legacy"}\n'
    path.write_bytes(data)
    inode = path.stat().st_ino
    publication.publish_immutable_bytes(path, data)
    assert path.stat().st_ino == inode

    partial = tmp_path / "selector.json"
    partial.write_bytes(data[:17])
    with pytest.raises(publication.PublicationConflict):
        publication.publish_immutable_bytes(partial, data)
    assert partial.read_bytes() == data[:17]


def test_flush_failure_does_not_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "plan.json"

    def fail_flush(_descriptor: int) -> None:
        raise OSError("injected flush failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_flush)
        with pytest.raises(OSError, match="injected flush failure"):
            publication.publish_immutable_bytes(path, b"plan\n")

    assert list(tmp_path.iterdir()) == []
    publication.publish_immutable_bytes(path, b"plan\n")
    assert path.read_bytes() == b"plan\n"


def test_retry_verifies_visible_file_after_sync_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "selector.json"
    data = b"selector\n"

    def fail_sync(destination: Path) -> None:
        assert destination.read_bytes() == data
        raise OSError("injected directory sync failure")

    with monkeypatch.context() as patch:
        patch.setattr(publication, "_sync_parent", fail_sync)
        with pytest.raises(OSError, match="injected directory sync failure"):
            publication.publish_immutable_bytes(path, data)

    inode = path.stat().st_ino
    publication.publish_immutable_bytes(path, data)
    assert path.stat().st_ino == inode
    assert path.read_bytes() == data


def test_staging_replaced_after_flush_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "selector.json"
    data = b"selector\n"
    fsync = os.fsync

    def replace_staging(descriptor: int) -> None:
        fsync(descriptor)
        staging = next(tmp_path.glob(".pf-publication-*/evidence.tmp"))
        staging.rename(staging.with_name("displaced"))
        staging.write_bytes(data)

    monkeypatch.setattr(os, "fsync", replace_staging)
    with pytest.raises(publication.PublicationConflict):
        publication.publish_immutable_bytes(path, data)

    assert not path.exists()
    replacement = next(tmp_path.glob(".pf-publication-*/evidence.tmp"))
    assert replacement.read_bytes() == data
    assert replacement.with_name("displaced").read_bytes() == data


def test_staging_modified_after_flush_is_never_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "selector.json"
    fsync = os.fsync

    def corrupt_staging(descriptor: int) -> None:
        fsync(descriptor)
        staging = next(tmp_path.glob(".pf-publication-*/evidence.tmp"))
        staging.write_bytes(b"bad!")

    monkeypatch.setattr(os, "fsync", corrupt_staging)
    with pytest.raises(publication.PublicationConflict):
        publication.publish_immutable_bytes(path, b"good")

    assert not list(tmp_path.iterdir())


def test_failed_publication_preserves_replacement_and_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "plan.json"

    def fail(staging: Path, destination: Path) -> None:
        assert destination == path
        staging.rename(staging.with_name("displaced"))
        staging.write_bytes(b"replacement")
        raise OSError("injected publication failure")

    monkeypatch.setattr(publication, "_publish_staged", fail)
    with pytest.raises(OSError, match="injected publication failure") as caught:
        publication.publish_immutable_bytes(path, b"plan\n")

    assert any("staging cleanup failed" in note for note in caught.value.__notes__)
    assert not path.exists()
    replacement = next(tmp_path.glob(".pf-publication-*/evidence.tmp"))
    assert replacement.read_bytes() == b"replacement"
    assert replacement.with_name("displaced").read_bytes() == b"plan\n"


@pytest.mark.parametrize("change", ["object", "bytes"])
def test_publication_checks_final_identity_and_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    path = tmp_path / "selector.json"
    raw = b"selector\n"
    publish_staged = publication._publish_staged

    def publish_then_change(staging: Path, destination: Path) -> None:
        publish_staged(staging, destination)
        if change == "object":
            destination.rename(destination.with_name("displaced"))
            destination.write_bytes(raw)
        else:
            destination.write_bytes(b"incorrect")

    monkeypatch.setattr(publication, "_publish_staged", publish_then_change)
    with pytest.raises(publication.PublicationConflict):
        publication.publish_immutable_bytes(path, raw)

    assert path.read_bytes() == (raw if change == "object" else b"incorrect")
    assert not list(tmp_path.glob(".pf-publication-*"))
    if change == "object":
        assert path.with_name("displaced").read_bytes() == raw


def test_checks_final_bytes_after_parent_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "selector.json"

    def corrupt_final(destination: Path) -> None:
        assert destination == path
        destination.write_bytes(b"bad!")

    monkeypatch.setattr(publication, "_sync_parent", corrupt_final)
    with pytest.raises(publication.PublicationConflict):
        publication.publish_immutable_bytes(path, b"good")

    assert list(tmp_path.iterdir()) == [path]
    assert path.read_bytes() == b"bad!"


@pytest.mark.skipif(os.name != "nt", reason="Windows move consumes the staging name")
def test_windows_consumed_staging_name_is_never_unlinked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "plan.json"
    publish_staged = publication._publish_staged
    unlink = Path.unlink

    def publish_then_reuse(staging: Path, destination: Path) -> None:
        publish_staged(staging, destination)
        assert not staging.exists()
        staging.write_bytes(b"replacement")

    def check_unlink(target: Path, missing_ok: bool = False) -> None:
        assert target.name != "evidence.tmp"
        unlink(target, missing_ok=missing_ok)

    monkeypatch.setattr(publication, "_publish_staged", publish_then_reuse)
    monkeypatch.setattr(Path, "unlink", check_unlink)
    publication.publish_immutable_bytes(path, b"plan\n")

    assert path.read_bytes() == b"plan\n"
    assert next(tmp_path.glob(".pf-publication-*/evidence.tmp")).read_bytes() == (
        b"replacement"
    )


def test_existing_evidence_disappears_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "selector.json"
    displaced = tmp_path / "displaced"
    data = b"selector\n"
    path.write_bytes(data)
    original_open = publication._open_evidence

    def remove_before_open(target: Path) -> BinaryIO:
        assert target == path
        path.rename(displaced)
        return original_open(target)

    monkeypatch.setattr(publication, "_open_evidence", remove_before_open)
    with pytest.raises(publication.PublicationConflict) as caught:
        publication.publish_immutable_bytes(path, data)

    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert list(tmp_path.iterdir()) == [displaced]
    assert displaced.read_bytes() == data


def test_existing_evidence_disappears_at_final_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "plan.json"
    displaced = tmp_path / "displaced"
    data = b"plan\n"
    # Use a handle that permits rename while open on Windows so the test
    # can remove the real directory entry before the final identity check.
    with publication._open_staging(path) as existing:
        existing.write(data)
        existing.flush()

        def use_existing_handle(target: Path) -> BinaryIO:
            assert target == path
            return existing

        def displace(destination: Path) -> None:
            assert destination == path
            path.rename(displaced)

        monkeypatch.setattr(publication, "_open_evidence", use_existing_handle)
        monkeypatch.setattr(publication, "_sync_parent", displace)
        with pytest.raises(publication.PublicationConflict) as caught:
            publication.publish_immutable_bytes(path, data)

    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert list(tmp_path.iterdir()) == [displaced]
    assert displaced.read_bytes() == data
