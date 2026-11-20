"""Event-owner reads preserve unbound compatibility and never initialize storage."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.maintenance.contracts import MaintenanceError, StoreTarget
from processforge_core.maintenance.storage_migration import add_store_identity
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.sqlite_storage import JournalError, set_metadata, transaction


def project_fixture(root: Path) -> tuple[ProcessEventRecorder, Path]:
    write_yaml_file(root / ".pf/process-forge.yaml", {"project": {"id": "read-owner"}})
    recorder = ProcessEventRecorder(
        configuration=ConfigurationProvider.pinned(PFConfig())
    )
    return recorder, root / ".pf/runtime/events/events.sqlite3"


def files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


def settle(path: Path) -> None:
    """Use rollback mode to distinguish read effects from ordinary WAL sidecars."""
    with closing(sqlite3.connect(path)) as connection:
        assert (
            connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
        )


def test_absent_journal_does_not_resolve_configuration_or_create_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableConfiguration:
        def project_configuration(self, *_args: object) -> None:
            pytest.fail("absent journal attempted configuration resolution")

    recorder, path = project_fixture(tmp_path)
    before = files(tmp_path)
    monkeypatch.setattr(recorder, "configuration", UnavailableConfiguration())
    assert recorder.latest_process_event(tmp_path) is None
    assert not path.parent.exists()
    assert files(tmp_path) == before


def test_unbound_journal_read_keeps_bytes_schema_and_no_uuid(tmp_path: Path) -> None:
    recorder, path = project_fixture(tmp_path)
    event = {
        "event_id": "last",
        "event_type": "fixture.observed",
        "payload": {"opaque": 42},
    }
    ProcessEventJournal().append(path, event)
    settle(path)
    before = files(tmp_path)
    assert recorder.latest_process_event(tmp_path) == event
    assert list(recorder.event_journal_for_project(tmp_path).records(path)) == [
        (1, event, None)
    ]
    assert files(tmp_path) == before
    assert not (tmp_path / ".pf/runtime/.storage-identity.lock.guard").exists()


@pytest.mark.parametrize("damage", ["corrupt", "pending", "unhosted-envelope"])
def test_refused_read_preserves_storage_and_cause(tmp_path: Path, damage: str) -> None:
    recorder, path = project_fixture(tmp_path)
    journal = ProcessEventJournal()
    journal.append(path, {"event_id": "preserved"})
    if damage == "corrupt":
        path.write_bytes(b"corrupt event store")
        code = "journal_database_error"
    else:
        with journal.connection(path, writable=True) as connection:
            with transaction(connection):
                if damage == "pending":
                    set_metadata(connection, "migration_state", "importing")
                else:
                    connection.execute("CREATE TABLE pf_store_meta(foreign_owner TEXT)")
        code = (
            "journal_migration_incomplete"
            if damage == "pending"
            else "storage_host_required"
        )
        settle(path)
    before = files(tmp_path)
    with pytest.raises(JournalError, match=code) as caught:
        recorder.latest_process_event(tmp_path)
    if damage == "corrupt":
        assert caught.value.__cause__ is not None
    with pytest.raises(JournalError, match=code):
        list(recorder.event_journal_for_project(tmp_path).records(path))
    assert files(tmp_path) == before


def bound_fixture(root: Path) -> tuple[ProcessEventRecorder, Path, Path]:
    """Construct read-only adapter unit inputs; this is no native migration proof."""
    recorder, path = project_fixture(root)
    journal = ProcessEventJournal()
    journal.append(path, {"event_id": "bound-event", "event_type": "fixture.observed"})
    target = StoreTarget(
        "events", path, "runtime/events/events.sqlite3", "project", "read-owner"
    )
    with journal.connection(path, writable=True) as connection:
        with transaction(connection):
            add_store_identity(connection, target, "a" * 32)
    settle(path)
    pin = root / ".pf/data/storage-identities.json"
    pin.parent.mkdir()
    pin.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "slots": [
                    {
                        "kind": "events",
                        "target_relative_path": target.target_relative_path,
                        "store_id": "a" * 32,
                        "scope": "project",
                        "owner_id": "read-owner",
                        "state": "ready",
                        "plan_checksum": "sha256:" + "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return recorder, path, pin


def test_configured_owner_reads_bound_journal_without_adoption(tmp_path: Path) -> None:
    recorder, path, _pin = bound_fixture(tmp_path)
    with pytest.raises(JournalError, match="storage_host_required"):
        ProcessEventJournal().latest(path)
    before = files(tmp_path)
    assert recorder.latest_process_event(tmp_path) == {
        "event_id": "bound-event",
        "event_type": "fixture.observed",
    }
    assert list(recorder.event_journal_for_project(tmp_path).records(path)) == [
        (1, {"event_id": "bound-event", "event_type": "fixture.observed"}, None)
    ]
    assert files(tmp_path) == before


@pytest.mark.parametrize("damage", ["owner", "uuid", "path", "pending", "corrupt"])
def test_bound_owner_refusals_preserve_bytes_and_identity(
    tmp_path: Path, damage: str
) -> None:
    recorder, path, pin = bound_fixture(tmp_path)
    if damage == "corrupt":
        path.write_bytes(b"corrupt bound store")
    else:
        pins = json.loads(pin.read_text(encoding="utf-8"))
        field, value = {
            "owner": ("owner_id", "foreign-owner"),
            "uuid": ("store_id", "c" * 32),
            "path": ("target_relative_path", "runtime/events/foreign.sqlite3"),
            "pending": ("state", "pending"),
        }[damage]
        pins["slots"][0][field] = value
        pin.write_text(json.dumps(pins), encoding="utf-8")
    before = files(tmp_path)
    expected, code = {
        "owner": (MaintenanceError, "storage_identity_conflict"),
        "uuid": (MaintenanceError, "storage_identity_conflict"),
        "path": (JournalError, "storage_host_required"),
        "pending": (MaintenanceError, "storage_resume_required"),
        "corrupt": (sqlite3.DatabaseError, "file is not a database"),
    }[damage]
    with pytest.raises(expected, match=code):
        recorder.latest_process_event(tmp_path)
    with pytest.raises(expected, match=code):
        list(recorder.event_journal_for_project(tmp_path).records(path))
    assert files(tmp_path) == before
