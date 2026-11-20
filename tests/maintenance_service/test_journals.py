"""Behavior, replay and recovery checks for the owning maintenance service."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pytest

from processforge_core.maintenance import journals
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import (
    JournalRow,
    JournalSource,
    JsonObject,
    MaintenanceError,
)
from processforge_core.maintenance.journal_scan import JournalScanService
from processforge_core.maintenance.journals import JournalMaintenanceService
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import (
    JournalError,
    JournalMigrationRequired,
    transaction,
)


@dataclass(frozen=True)
class _Files:
    project: Path
    workplace: Path
    events: Path
    raw: Path

    @property
    def event_db(self) -> Path:
        return self.events.with_suffix(".sqlite3")

    @property
    def raw_db(self) -> Path:
        return self.project / ".pf/runtime/agent-events/hooks.sqlite3"


def _line(record: JsonObject) -> bytes:
    return (
        json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    )


def _raw(project: Path, *, answer: str = "kept") -> JsonObject:
    from pf_runtime.raw_ingress_kernel import (
        NativeAgentEvent,
        raw_event_id,
        raw_payload_hash,
        stable_native_identity_key,
    )

    event = NativeAgentEvent(
        provider="codex",
        adapter="native",
        native_event_type="message",
        native_event_id="native-1",
        raw_payload={"answer": answer},
        source_session_id="session-1",
        source_project_ref=str(project.resolve()),
    )
    return {
        "schema_version": 1,
        "raw_event_id": raw_event_id(event),
        "raw_payload_hash": raw_payload_hash(event.raw_payload),
        "native_identity_key": stable_native_identity_key(event),
        "provider": event.provider,
        "adapter": event.adapter,
        "native_event_type": event.native_event_type,
        "native_event_id": event.native_event_id,
        "native_id_scope": event.native_id_scope,
        "native_event_id_stable": event.native_event_id_stable,
        "raw_payload": event.raw_payload,
        "payload_version": event.payload_version,
        "source_project_ref": event.source_project_ref,
        "source_session_id": event.source_session_id,
        "received_at": "2026-10-22T00:00:00Z",
        "unknown": {"preserved": True},
    }


def _layout(tmp_path: Path, *, damage: bytes = b"", duplicates: bool = False) -> _Files:
    project, workplace = tmp_path / "project", tmp_path / "workplace"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    workplace.mkdir()
    (flow / "process-forge.yaml").write_text(
        "schema_version: 1\nproject: {id: service-tests}\n", encoding="utf-8"
    )
    events = flow / "runtime/events/events.ndjson"
    raw = workplace / "runtime/agent-events/raw/v1/2026/10/22/00.ndjson"
    events.parent.mkdir(parents=True)
    raw.parent.mkdir(parents=True)
    record = {
        "event_id": "event-1",
        "event_type": "decision",
        "unknown": {"text": "Решение"},
    }
    events.write_bytes(_line(record) + damage + (_line(record) if duplicates else b""))
    raw_record = _raw(project)
    raw.write_bytes(_line(raw_record) + (_line(raw_record) if duplicates else b""))
    return _Files(project, workplace, events, raw)


@pytest.mark.parametrize("first", ["caf\u00e9", "cafe\u0301"])
def test_nfc_equivalent_raw_payloads_import_once_and_replay(
    tmp_path: Path, first: str
) -> None:
    from pf_runtime.raw_ingress_kernel import raw_payload_hash

    files = _layout(tmp_path)
    second = "cafe\u0301" if first == "caf\u00e9" else "caf\u00e9"
    one = _raw(files.project, answer=first)
    two = _raw(files.project, answer=second)
    # Stable native IDs use payload hash for conflict checks; both observations
    # are the same native identity under the existing NFC hash policy.
    for field in ("raw_event_id", "native_identity_key", "raw_payload_hash"):
        assert one[field] == two[field]
    files.raw.write_bytes(_line(one) + _line(two))
    originals = files.events.read_bytes(), files.raw.read_bytes()
    service = JournalMaintenanceService()
    first_result = service.migrate(files.project, files.workplace, apply=True)
    assert first_result["status"] == "ready"
    assert first_result["stored_counts"] == {"events": 1, "raw": 1}
    replay = service.migrate(files.project, files.workplace, apply=True)
    assert replay["status"] == "ready" and replay["imported_counts"] == {
        "events": 0,
        "raw": 0,
    }
    stored = list(RawHookJournal().records(files.raw_db))[0]["record"]
    assert raw_payload_hash(stored["raw_payload"]) == one["raw_payload_hash"]
    assert originals == (files.events.read_bytes(), files.raw.read_bytes())


def test_preflight_conflict_keeps_incomplete_quarantine_and_truthful_failure(
    tmp_path: Path,
) -> None:
    damage = b"{broken\x00\r\n"
    files = _layout(tmp_path)
    files.events.write_bytes(
        damage
        + _line({"event_id": "same", "value": 1})
        + _line({"event_id": "same", "value": 2})
    )
    before = files.events.read_bytes(), files.raw.read_bytes()
    with pytest.raises(MaintenanceError, match="migration_event_id_conflict"):
        JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    failed = _failure(files)
    assert failed["quarantine"]["status"] == "incomplete"
    assert failed["scan_complete"] is False
    directory = Path(failed["quarantine"]["directory"])
    manifests = list(directory.glob("manifest.incomplete-*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["scan_complete"] is False
    record = manifest["records"][0]
    assert record["line"] == 1 and record["offset"] == 0
    assert record["sha256"] == hashlib.sha256(damage).hexdigest()
    assert (directory / record["file"]).read_bytes() == damage
    assert not files.event_db.exists() and not files.raw_db.exists()
    assert before == (files.events.read_bytes(), files.raw.read_bytes())


def _failure(files: _Files) -> JsonObject:
    evidence = list(
        (files.project / ".pf/runtime/journal-maintenance").glob("*/failure.json")
    )
    assert len(evidence) == 1
    return json.loads(evidence[0].read_text(encoding="utf-8"))


def _guarded(files: _Files) -> None:
    for owner, path in (
        (ProcessEventJournal(), files.event_db),
        (RawHookJournal(), files.raw_db),
    ):
        with pytest.raises(JournalMigrationRequired, match="incomplete"):
            owner.count(path)


def _database_counts(files: _Files) -> tuple[int, int]:
    result = []
    for path, query in (
        (files.event_db, "SELECT COUNT(*) FROM events"),
        (files.raw_db, "SELECT COUNT(*) FROM raw_events"),
    ):
        with closing(
            sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        ) as connection:
            result.append(connection.execute(query).fetchone()[0])
    return result[0], result[1]


def test_plan_has_no_database_backup_or_default_evidence_effect(tmp_path: Path) -> None:
    files = _layout(tmp_path)
    before = {path: path.read_bytes() for path in (files.events, files.raw)}
    plan = JournalMaintenanceService().migrate(files.project, files.workplace)
    assert plan["status"] == "planned" and not plan["applied"]
    assert plan["unique_events"] == 1 and plan["unique_raw"] == 1
    assert plan["backups"] == [] and plan["evidence"] == []
    assert plan["counts"] == {
        "read": 2,
        "valid": 2,
        "imported": 0,
        "already_present": 0,
        "skipped": 0,
        "corrupted": 0,
    }
    assert not files.event_db.exists() and not files.raw_db.exists()
    assert not (files.project / ".pf/runtime/journal-maintenance").exists()
    assert all(path.read_bytes() == content for path, content in before.items())


def test_apply_refuses_and_quarantines_nul_before_any_database_mutation(
    tmp_path: Path,
) -> None:
    damaged = b"\x00\x00broken\x00\r\n"
    files = _layout(tmp_path, damage=damaged)
    original = files.events.read_bytes()
    result = JournalMaintenanceService().migrate(
        files.project, files.workplace, apply=True
    )
    assert result["blocked"] and result["status"] == "blocked" and not result["applied"]
    assert result["backups"] == [] and result["counts"]["corrupted"] == 1
    assert result["counts"]["skipped"] == 0 and result["counts"]["read"] == 3
    assert not files.event_db.exists() and not files.raw_db.exists()
    manifest_path = Path(result["quarantine"]["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["records"][0]
    assert (manifest_path.parent / entry["file"]).read_bytes() == damaged
    assert entry["offset"] == original.index(damaged)
    assert entry["length"] == len(damaged)
    assert entry["sha256"] == hashlib.sha256(damaged).hexdigest()
    assert files.events.read_bytes() == original
    assert (Path(result["evidence_dir"]) / "result.json").is_file()


def test_explicit_plan_evidence_preserves_corruption_without_creating_databases(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path, damage=b"\x00bad\n")
    evidence = tmp_path / "requested-evidence"
    plan = JournalMaintenanceService().migrate(
        files.project, files.workplace, evidence_dir=evidence
    )
    assert plan["blocked"]
    assert Path(plan["quarantine"]["manifest"]).is_relative_to(evidence)
    assert not files.event_db.exists() and not files.raw_db.exists()


def test_explicit_skip_imports_unknown_fields_and_replay_counts_without_duplicates(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path, damage=b"\x00bad\n", duplicates=True)
    originals = files.events.read_bytes(), files.raw.read_bytes()
    service = JournalMaintenanceService()
    first = service.migrate(
        files.project, files.workplace, apply=True, skip_invalid=True
    )
    assert first["status"] == "ready" and first["migration_state"] == "ready"
    assert first["stored_counts"] == {"events": 1, "raw": 1}
    assert first["counts"] == {
        "read": 5,
        "valid": 4,
        "imported": 2,
        "already_present": 2,
        "skipped": 1,
        "corrupted": 1,
    }
    assert first["duplicate_rows"] == 2
    assert all(item["status"] == "missing" for item in first["backups"])
    event = ProcessEventJournal().get(files.event_db, "event-1")
    assert event is not None and event["unknown"] == {"text": "Решение"}
    assert list(RawHookJournal().records(files.raw_db))[0]["record"] == _raw(
        files.project
    )
    second = service.migrate(
        files.project, files.workplace, apply=True, skip_invalid=True
    )
    assert second["stored_counts"] == first["stored_counts"]
    assert second["counts"]["imported"] == 0
    assert second["counts"]["already_present"] == 4
    assert second["verification"]["semantic_replay"] == {
        "status": "verified",
        "checked_rows": 4,
        "inserted": 0,
    }
    assert second["evidence_dir"] != first["evidence_dir"]
    assert originals == (files.events.read_bytes(), files.raw.read_bytes())
    for item in second["evidence"]:
        assert (
            hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()
            == item["sha256"]
        )


def test_repeat_backups_are_verified_restorable_preimport_snapshots(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    service = JournalMaintenanceService()
    service.migrate(files.project, files.workplace, apply=True)
    with files.events.open("ab") as stream:
        stream.write(_line({"event_id": "event-2", "extra": [1, 2]}))
    result = service.migrate(files.project, files.workplace, apply=True)
    assert result["stored_counts"] == {"events": 2, "raw": 1}
    assert result["backup_consistency"] == "per_database"
    backup = SQLiteBackupService()
    for item in result["backups"]:
        assert item["status"] == "verified"
        assert backup.verify(Path(item["bundle"]))["integrity_check"] == "ok"
        restored = tmp_path / (item["kind"] + "-restored.sqlite3")
        backup.restore(Path(item["bundle"]), restored)
        owner = ProcessEventJournal() if item["kind"] == "events" else RawHookJournal()
        assert owner.count(restored) == 1
    assert ProcessEventJournal().get(files.event_db, "event-2") == {
        "event_id": "event-2",
        "extra": [1, 2],
    }


def test_both_backups_finish_before_either_migration_barrier(tmp_path: Path) -> None:
    files = _layout(tmp_path)
    JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    observed = []

    class Observe(SQLiteBackupService):
        def create(self, source: Path, bundle: Path) -> JsonObject:
            assert ProcessEventJournal().count(files.event_db) == 1
            assert RawHookJournal().count(files.raw_db) == 1
            observed.append(("create", source.name))
            return super().create(source, bundle)

        def verify(self, bundle: Path) -> JsonObject:
            assert ProcessEventJournal().count(files.event_db) == 1
            assert RawHookJournal().count(files.raw_db) == 1
            observed.append(("verify", bundle.name))
            return super().verify(bundle)

    JournalMaintenanceService(backup=Observe()).migrate(
        files.project, files.workplace, apply=True
    )
    assert observed == [
        ("create", "events.sqlite3"),
        ("verify", "events"),
        ("create", "hooks.sqlite3"),
        ("verify", "raw"),
    ]


@pytest.mark.parametrize("returned_failure", [False, True])
def test_backup_refusal_prevents_database_mutation(
    tmp_path: Path, returned_failure: bool
) -> None:
    files = _layout(tmp_path)
    JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    before = files.event_db.read_bytes(), files.raw_db.read_bytes()

    class Refuse(SQLiteBackupService):
        def verify(self, bundle: Path) -> JsonObject:
            if returned_failure:
                return {"status": "invalid", "integrity_check": "failed"}
            raise MaintenanceError("backup_tampered")

    with pytest.raises(MaintenanceError, match="backup"):
        JournalMaintenanceService(backup=Refuse()).migrate(
            files.project, files.workplace, apply=True
        )
    assert before == (files.event_db.read_bytes(), files.raw_db.read_bytes())
    assert ProcessEventJournal().count(files.event_db) == 1
    assert RawHookJournal().count(files.raw_db) == 1
    assert _failure(files)["migration_state"] == "not_started"


def test_source_changed_during_backup_is_refused_before_barriers(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)

    class Drift(SQLiteBackupService):
        def verify(self, bundle: Path) -> JsonObject:
            result = super().verify(bundle)
            if bundle.name == "raw":
                with files.events.open("ab") as stream:
                    stream.write(_line({"event_id": "late"}))
            return result

    with pytest.raises(MaintenanceError, match="source_changed"):
        JournalMaintenanceService(backup=Drift()).migrate(
            files.project, files.workplace, apply=True
        )
    assert ProcessEventJournal().count(files.event_db) == 1
    assert RawHookJournal().count(files.raw_db) == 1
    assert _failure(files)["migration_state"] == "not_started"


def test_interrupted_import_keeps_both_barriers_and_retry_does_not_duplicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _layout(tmp_path)
    service = JournalMaintenanceService()
    original = files.events.read_bytes(), files.raw.read_bytes()

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("injected interruption")

    with monkeypatch.context() as changes:
        changes.setattr(RawHookJournal, "_accept", fail)
        with pytest.raises(OSError, match="interruption"):
            service.migrate(files.project, files.workplace, apply=True)
    _guarded(files)
    assert _database_counts(files) == (1, 0)
    failed = _failure(files)
    assert failed["imported_counts"] == {"events": 1, "raw": 0}
    assert failed["recovery"]["destination_states"] == {
        "events.sqlite3": "importing",
        "hooks.sqlite3": "importing",
    }
    retried = service.migrate(files.project, files.workplace, apply=True)
    assert retried["imported_counts"] == {"events": 0, "raw": 1}
    assert retried["already_present_counts"] == {"events": 1, "raw": 0}
    assert original == (files.events.read_bytes(), files.raw.read_bytes())
    assert all(item["status"] == "verified" for item in retried["backups"])


def test_batch_failure_rolls_back_only_current_batch_and_retry_preserves_prior_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _layout(tmp_path)
    files.events.write_bytes(
        b"".join(_line({"event_id": f"event-{number}"}) for number in range(501))
    )
    original_append = ProcessEventJournal._append

    def fail_late(
        connection: sqlite3.Connection,
        event: JsonObject,
        *args: object,
        **kwargs: object,
    ) -> bool:
        if event["event_id"] == "event-500":
            raise OSError("late batch interrupted")
        return original_append(connection, event, *args, **kwargs)

    with monkeypatch.context() as changes:
        changes.setattr(ProcessEventJournal, "_append", staticmethod(fail_late))
        with pytest.raises(OSError, match="batch"):
            JournalMaintenanceService().migrate(
                files.project, files.workplace, apply=True
            )
    _guarded(files)
    assert _database_counts(files) == (500, 0)
    assert _failure(files)["imported_counts"]["events"] == 500
    result = JournalMaintenanceService().migrate(
        files.project, files.workplace, apply=True
    )
    assert result["stored_counts"] == {"events": 501, "raw": 1}
    assert result["imported_counts"] == {"events": 1, "raw": 1}
    assert result["already_present_counts"]["events"] == 500


@pytest.mark.parametrize("change", ["same_stat_bytes", "discovery", "deleted"])
def test_source_drift_after_import_scan_never_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    files = _layout(tmp_path)
    signature = journals._signature(files.events)
    original_signature = journals._signature
    if change == "same_stat_bytes":

        def frozen_signature(path: Path) -> tuple[int, int, int, int, int]:
            return signature if path == files.events else original_signature(path)

        monkeypatch.setattr(
            journals,
            "_signature",
            frozen_signature,
        )

    class Drift(JournalScanService):
        passes = 0

        def rows(
            self,
            sources: list[JournalSource],
            project: Path,
            report: JsonObject,
            *,
            skip_invalid: bool = False,
            quarantine_dir: Path | None = None,
        ) -> Iterator[JournalRow]:
            self.passes += 1
            yield from super().rows(
                sources,
                project,
                report,
                skip_invalid=skip_invalid,
                quarantine_dir=quarantine_dir,
            )
            if self.passes == 2:
                if change == "same_stat_bytes":
                    stamp = files.events.stat()
                    files.events.write_bytes(
                        files.events.read_bytes().replace(b"event-1", b"event-2")
                    )
                    os.utime(files.events, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                elif change == "discovery":
                    files.raw.with_name("new.ndjson").write_bytes(b"\n")
                else:
                    files.events.unlink()

    with pytest.raises(MaintenanceError, match="source_changed"):
        JournalMaintenanceService(scan=Drift()).migrate(
            files.project, files.workplace, apply=True
        )
    _guarded(files)
    assert _failure(files)["migration_state"] == "incomplete"


@pytest.mark.parametrize("phase", ["finish", "result_evidence"])
def test_completion_failure_reasserts_both_barriers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    files = _layout(tmp_path)
    original_evidence = journals._evidence

    def fail_finish(*args: object) -> None:
        raise OSError("finish unavailable")

    def fail_result(directory: Path | None, name: str, report: JsonObject) -> None:
        if name == "result":
            raise OSError("result unavailable")
        original_evidence(directory, name, report)

    with monkeypatch.context() as changes:
        if phase == "finish":
            changes.setattr(RawHookJournal, "finish_migration", fail_finish)
        else:
            changes.setattr(journals, "_evidence", fail_result)
        with pytest.raises(OSError, match="unavailable"):
            JournalMaintenanceService().migrate(
                files.project, files.workplace, apply=True
            )
    _guarded(files)
    assert _failure(files)["migration_state"] == "incomplete"
    result = JournalMaintenanceService().migrate(
        files.project, files.workplace, apply=True
    )
    assert result["stored_counts"] == {"events": 1, "raw": 1}
    assert result["counts"]["imported"] == 0


def test_conflicting_source_ids_refuse_before_mutation_even_with_skip(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    with files.events.open("ab") as stream:
        stream.write(_line({"event_id": "event-1", "different": True}))
    with pytest.raises(MaintenanceError, match="conflict"):
        JournalMaintenanceService().migrate(
            files.project, files.workplace, apply=True, skip_invalid=True
        )
    assert not files.event_db.exists() and not files.raw_db.exists()
    assert _failure(files)["migration_state"] == "not_started"


def test_existing_destination_id_conflict_keeps_backup_and_barriers(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    service = JournalMaintenanceService()
    service.migrate(files.project, files.workplace, apply=True)
    files.events.write_bytes(_line({"event_id": "event-1", "different": True}))
    with pytest.raises(JournalError, match="event_id_conflict"):
        service.migrate(files.project, files.workplace, apply=True)
    _guarded(files)
    failed = _failure(files)
    assert all(item["status"] == "verified" for item in failed["backups"])
    assert _database_counts(files) == (1, 1)


@pytest.mark.parametrize("kind", ["events", "raw"])
def test_semantic_replay_detects_corrupted_record_even_when_counts_are_correct(
    tmp_path: Path, kind: str
) -> None:
    files = _layout(tmp_path)

    class Tamper(JournalScanService):
        passes = 0

        def rows(
            self,
            sources: list[JournalSource],
            project: Path,
            report: JsonObject,
            *,
            skip_invalid: bool = False,
            quarantine_dir: Path | None = None,
        ) -> Iterator[JournalRow]:
            self.passes += 1
            if self.passes == 3:
                if kind == "events":
                    with ProcessEventJournal().connection(
                        files.event_db, writable=True, migrating=True
                    ) as connection:
                        with transaction(connection):
                            connection.execute(
                                "UPDATE events SET record = ?",
                                ('{"event_id":"event-1","tampered":true}',),
                            )
                else:
                    with RawHookJournal().connection(
                        files.raw_db, writable=True, migrating=True
                    ) as connection:
                        with transaction(connection):
                            changed = dict(
                                _raw(files.project), raw_payload={"answer": "tampered"}
                            )
                            connection.execute(
                                "UPDATE raw_events SET record = ?",
                                (json.dumps(changed),),
                            )
            yield from super().rows(
                sources,
                project,
                report,
                skip_invalid=skip_invalid,
                quarantine_dir=quarantine_dir,
            )

    with pytest.raises(MaintenanceError, match="record_mismatch"):
        JournalMaintenanceService(scan=Tamper()).migrate(
            files.project, files.workplace, apply=True
        )
    assert _database_counts(files) == (1, 1)
    _guarded(files)


def test_missing_valid_id_is_not_hidden_by_unrelated_stored_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _layout(tmp_path)
    service = JournalMaintenanceService()
    service.migrate(files.project, files.workplace, apply=True)
    files.events.write_bytes(_line({"event_id": "event-missing"}))
    monkeypatch.setattr(ProcessEventJournal, "_append", lambda *args, **kwargs: False)
    with pytest.raises(MaintenanceError, match="record_mismatch"):
        service.migrate(files.project, files.workplace, apply=True)
    assert _database_counts(files) == (1, 1)
    _guarded(files)


def test_raw_duplicate_observation_metadata_keeps_existing_dedup_semantics(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    with files.raw.open("ab") as stream:
        stream.write(
            _line(dict(_raw(files.project), received_at="2026-10-22T01:00:00Z"))
        )
    result = JournalMaintenanceService().migrate(
        files.project, files.workplace, apply=True
    )
    assert result["unique_raw"] == 1 and result["raw_rows"] == 2
    assert result["stored_counts"] == {"events": 1, "raw": 1}
    assert result["imported_counts"]["raw"] == 1
    assert result["already_present_counts"]["raw"] == 1


def test_keyboard_interruption_is_reraised_with_recovery_barriers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _layout(tmp_path)

    def interrupt(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(RawHookJournal, "_accept", interrupt)
    with pytest.raises(KeyboardInterrupt):
        JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    _guarded(files)
    assert _failure(files)["error"] == "migration_interrupted"


def test_failure_recovery_never_recreates_a_disappeared_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _layout(tmp_path)

    def disappear(*args: object, **kwargs: object) -> None:
        files.event_db.unlink()
        raise OSError("destination disappeared")

    monkeypatch.setattr(RawHookJournal, "_accept", disappear)
    with pytest.raises(OSError, match="disappeared"):
        JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    assert not files.event_db.exists()
    states = _failure(files)["recovery"]["destination_states"]
    assert states["events.sqlite3"] == "missing"
    with pytest.raises(JournalMigrationRequired, match="incomplete"):
        RawHookJournal().count(files.raw_db)


def test_database_replaced_after_backup_is_not_mutated_by_service(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    JournalMaintenanceService().migrate(files.project, files.workplace, apply=True)
    displaced = files.event_db.with_name("original.sqlite3")

    class Replace(SQLiteBackupService):
        def verify(self, bundle: Path) -> JsonObject:
            result = super().verify(bundle)
            if bundle.name == "events":
                files.event_db.rename(displaced)
                with ProcessEventJournal().connection(
                    files.event_db, writable=True, migrating=True
                ):
                    pass
                ProcessEventJournal().finish_migration(files.event_db)
            return result

    with pytest.raises(MaintenanceError, match="destination_changed"):
        JournalMaintenanceService(backup=Replace()).migrate(
            files.project, files.workplace, apply=True
        )
    assert ProcessEventJournal().count(files.event_db) == 0
    assert ProcessEventJournal().count(displaced) == 1
    assert RawHookJournal().count(files.raw_db) == 1
    assert _failure(files)["migration_state"] == "not_started"


def test_history_metadata_count_mismatch_is_refused(tmp_path: Path) -> None:
    files = _layout(tmp_path)
    service = JournalMaintenanceService()
    service.migrate(files.project, files.workplace, apply=True)
    with ProcessEventJournal().connection(files.event_db, writable=True) as connection:
        connection.execute(
            "UPDATE journal_metadata SET value = '99' WHERE key = 'history_count'"
        )
    with pytest.raises(MaintenanceError, match="count_mismatch"):
        service.migrate(files.project, files.workplace, apply=True)
    _guarded(files)


def test_cold_default_composition_and_real_library_import_never_load_main_or_host(
    tmp_path: Path,
) -> None:
    files = _layout(tmp_path)
    root = Path(__file__).resolve().parents[2]
    code = """
import importlib.abc
from pathlib import Path
import sys
from unittest.mock import patch
sys.path[:0] = sys.argv[1:3]
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in (
            'processforge', 'pf_runtime.host',
            'pf_runtime.service', 'pf_runtime.mcp_server'
        ):
            raise AssertionError('forbidden import: ' + fullname)
sys.meta_path.insert(0, Block())
from processforge_core.maintenance.journals import JournalMaintenanceService
with patch('pathlib.Path.open', side_effect=AssertionError('constructor file I/O')):
    with patch('sqlite3.connect', side_effect=AssertionError('constructor DB I/O')):
        service = JournalMaintenanceService()
report = service.migrate(Path(sys.argv[3]), Path(sys.argv[4]), apply=True)
assert report['status'] == 'ready'
assert 'processforge' not in sys.modules and 'pf_runtime.host' not in sys.modules
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            code,
            str(root / "src"),
            str(root / "tools"),
            str(files.project),
            str(files.workplace),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_legacy_script_keeps_flags_json_and_exit_behavior(tmp_path: Path) -> None:
    files = _layout(tmp_path, damage=b"\x00bad\n")
    script = Path(__file__).resolve().parents[2] / "tools/migrate-hook-journals.py"
    args = [
        sys.executable,
        "-B",
        str(script),
        "--project-root",
        str(files.project),
        "--workplace",
        str(files.workplace),
    ]
    refused = subprocess.run(args, capture_output=True, text=True, check=False)
    assert refused.returncode == 1 and json.loads(refused.stdout)["blocked"]
    planned = subprocess.run(
        [*args, "--skip-invalid"], capture_output=True, text=True, check=False
    )
    assert planned.returncode == 0 and json.loads(planned.stdout)["status"] == "planned"
    assert not files.event_db.exists()
    applied = subprocess.run(
        [
            *args,
            "--skip-invalid",
            "--apply",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(applied.stdout)
    assert applied.returncode == 0 and report["status"] == "ready"
    assert Path(report["evidence_dir"]).is_relative_to(tmp_path / "evidence")
    assert not applied.stderr
