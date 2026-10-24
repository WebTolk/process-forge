"""Real legacy SQLite formats, UUID/parity/backup and crash recovery."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from unittest.mock import patch
from uuid import uuid4

import pytest

from processforge_core.accounting.storage import _SCHEMA
from processforge_core.database import SQLiteDriver
from processforge_core.executions.model import ExecutionError
from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import (
    JsonObject,
    MaintenanceError,
    MigrationSafety,
    StorageMigrationContext,
    StoreTarget,
)
from processforge_core.process_event_journal import SCHEMA as EVENTS
from processforge_core.raw_hook_journal import SCHEMA as RAW
from processforge_core.resources.local_search import _ensure_schema
from processforge_core.runtime.execution_admission import ExecutionAdmission


def create_legacy(path: Path, kind: str) -> None:
    """Create the actual qualified domain DDL and opaque data, including FTS."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = SQLiteDriver()._connect(path, isolation_level=None)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("BEGIN IMMEDIATE")
        if kind in {"events", "raw"}:
            connection.execute(
                "CREATE TABLE journal_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            for statement in EVENTS if kind == "events" else RAW:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO journal_metadata VALUES('migration_state','ready')"
            )
            connection.execute("INSERT INTO journal_metadata VALUES('opaque','é/ё')")
            connection.execute(
                "PRAGMA application_id="
                + str(0x50464556 if kind == "events" else 0x50465257)
            )
            connection.execute("PRAGMA user_version=1")
            if kind == "events":
                connection.execute(
                    "INSERT INTO admissions(event_id,payload_hash) VALUES('exact-event','opaque-hash')"
                )
            else:
                connection.execute(
                    "INSERT INTO raw_events VALUES('exact-raw','{\"opaque\":true}')"
                )
        elif kind == "accounting":
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.execute("PRAGMA application_id=" + str(0x50464143))
            connection.execute("PRAGMA user_version=1")
            connection.execute(
                "INSERT INTO revisions VALUES('usage','old-origin','source','record',1,'{\"extension\":true}')"
            )
        else:
            _ensure_schema(connection)
            connection.execute(
                "INSERT INTO documents_fts(title,content,document_id,resource_id) VALUES('title','Unicode evidence','doc','resource')"
            )
        connection.commit()
    finally:
        connection.close()


@dataclass
class StorageHarness:
    """Fixture-only host proof and locks; no claim of actual writer exclusion."""

    root: Path
    kind: Literal["events", "raw", "accounting", "search"] = "events"
    state: Literal["proven", "active", "unknown"] = "proven"
    generation: str = "fixture-exclusion-1"
    gates: list[str] = field(default_factory=list)
    proof_calls: int = 0

    def __post_init__(self) -> None:
        self.project = self.root / "project"
        self.flow = self.project / ".pf"
        self.workplace = self.root / "workplace"
        self.flow.mkdir(parents=True)
        self.workplace.mkdir()
        (self.flow / "process-forge.yaml").write_text(
            "project:\n  id: stable-project\n", encoding="utf-8"
        )
        scope: Literal["project", "workplace"] = (
            "workplace" if self.kind == "accounting" else "project"
        )
        owner = "old-origin" if scope == "workplace" else "stable-project"
        owner_root = self.workplace if scope == "workplace" else self.flow
        relative = "runtime/stores/é-ё-" + self.kind + ".sqlite3"
        self.target = StoreTarget(
            self.kind, owner_root / relative, relative, scope, owner
        )
        if self.kind == "accounting":
            identity = self.workplace / "data/accounting/identity.json"
            identity.parent.mkdir(parents=True)
            identity.write_text('{"origin_id":"old-origin"}', encoding="utf-8")
        self.context = StorageMigrationContext(
            self.project,
            self.workplace if scope == "workplace" else None,
            self.root / "device.yaml",
            (self.target,),
        )
        self.backup = SQLiteBackupService(driver=SQLiteDriver())
        self.service = migration.StorageMigrationService(
            backup=self.backup,
            admission=ExecutionAdmission(self.lock),
            registry_lock=self.lock,
            safety=self.proof,
        )

    @contextmanager
    def lock(
        self, path: Path, *, timeout_seconds: float, stale_after_seconds: int
    ) -> Iterator[object]:
        assert timeout_seconds > 0 and stale_after_seconds == 0
        self.gates.append(path.name)
        try:
            yield object()
        finally:
            assert self.gates.pop() == path.name

    def proof(self, context: StorageMigrationContext) -> MigrationSafety:
        assert context == self.context
        assert "execution-admission" in self.gates
        self.proof_calls += 1
        return MigrationSafety(
            self.state,
            self.generation,
            ("fixture:exclusive-managed-writers-trees-routing",),
        )

    @property
    def owner(self) -> Path:
        return migration.storage_owner_root(self.context, self.target)

    @property
    def slot(self) -> JsonObject:
        return migration._slot(self.owner, self.target) or {}

    def create(self) -> None:
        create_legacy(self.target.target, self.kind)

    def ensure(self) -> JsonObject:
        return self.service.ensure_ready(self.context, trigger="first_write")

    def parity(self) -> JsonObject:
        return migration._inspect_target(
            self.target, migration._descriptor(), SQLiteDriver(), parity=True
        )


@pytest.fixture
def storage() -> StorageHarness:
    return StorageHarness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)


@pytest.mark.parametrize("kind", ["events", "raw", "accounting", "search"])
def test_known_formats_in_place_uuid_parity_and_replay(
    kind: Literal["events", "raw", "accounting", "search"],
) -> None:
    harness = StorageHarness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex, kind)
    harness.create()
    before, original = harness.parity(), harness.target.target.read_bytes()
    report = harness.ensure()
    assert report["status"] == "ready", report
    after = harness.parity()
    assert after["store_id"] == harness.slot["store_id"]
    assert {**before, "store_id": after["store_id"]} == after
    assert harness.target.target.read_bytes() != original
    assert harness.slot["state"] == "ready"
    assert harness.ensure()["status"] == "ready"
    assert harness.service.resume(harness.context)["status"] == "ready"
    assert harness.parity() == after
    directory = harness.service._journal(
        harness.owner, str(harness.slot["plan_checksum"])
    )
    assert harness.backup.verify(directory / "backup")["verified"] is True
    with sqlite3.connect(directory / "backup/database.sqlite3") as old:
        assert (
            old.execute(
                "SELECT name FROM sqlite_schema WHERE name='pf_store_meta'"
            ).fetchone()
            is None
        )
    if kind == "search":
        with sqlite3.connect(harness.target.target) as search:
            assert search.execute(
                "SELECT title FROM documents_fts WHERE documents_fts MATCH 'Unicode'"
            ).fetchall() == [("title",)]


def test_inspect_and_absent_ensure_do_not_create_unused_stores(
    storage: StorageHarness,
) -> None:
    before = sorted(p.relative_to(storage.root) for p in storage.root.rglob("*"))
    assert storage.service.inspect(storage.context)["per_target_counts"]["absent"] == 1
    assert storage.ensure()["per_target_counts"]["absent"] == 1
    assert (
        sorted(p.relative_to(storage.root) for p in storage.root.rglob("*")) == before
    )
    assert not storage.slot and storage.proof_calls == 0


@pytest.mark.parametrize("state", ["active", "unknown"])
def test_unknown_or_active_defers_without_uuid_or_maintenance(
    storage: StorageHarness, state: Literal["active", "unknown"]
) -> None:
    storage.create()
    storage.state = state
    original = storage.target.target.read_bytes()
    report = storage.ensure()
    assert report["blocked"] is True and report["targets"][0]["legacy_allowed"] is True
    assert not storage.slot and not (storage.owner / "data/storage-migrations").exists()
    assert storage.target.target.read_bytes() == original
    storage.state = "proven"
    assert storage.ensure()["status"] == "ready"


@pytest.mark.parametrize(
    "ddl",
    [
        "CREATE TABLE unexpected(id)",
        "CREATE TRIGGER unexpected AFTER INSERT ON admissions BEGIN SELECT 1; END",
        "CREATE INDEX unexpected ON admissions(payload_hash)",
    ],
)
def test_unknown_extra_objects_refuse_without_relabel(
    storage: StorageHarness, ddl: str
) -> None:
    storage.create()
    with sqlite3.connect(storage.target.target) as connection:
        connection.execute(ddl)
    report = storage.ensure()
    assert report["error"]["code"] == "storage_schema_unrecognized"
    assert not storage.slot


@pytest.mark.parametrize(
    "mutation",
    [
        "PRAGMA application_id=9",
        "PRAGMA user_version=99",
        "UPDATE journal_metadata SET value='importing' WHERE key='migration_state'",
    ],
)
def test_foreign_future_incomplete_old_import_refuses(
    storage: StorageHarness, mutation: str
) -> None:
    storage.create()
    with sqlite3.connect(storage.target.target) as connection:
        connection.execute(mutation)
    assert storage.ensure()["blocked"] is True
    assert not storage.slot


def test_backup_failure_then_resume_retains_uuid(storage: StorageHarness) -> None:
    storage.create()
    with patch.object(
        storage.backup,
        "create",
        side_effect=MaintenanceError("fixture_backup_interrupt"),
    ):
        assert storage.ensure()["blocked"] is True
    slot = storage.slot
    assert slot["state"] == "pending"
    assert storage.service.resume(storage.context)["status"] == "ready"
    assert storage.slot["store_id"] == slot["store_id"]


def test_selector_before_pin_crash_never_remints(storage: StorageHarness) -> None:
    storage.create()
    original = migration._publish_pin
    with patch.object(
        migration, "_publish_pin", side_effect=OSError("private path omitted")
    ):
        assert storage.ensure()["blocked"] is True
    selector = storage.service._selector(storage.owner, storage.target)
    planned = json.loads(selector.read_text(encoding="utf-8"))
    assert not storage.slot
    with patch.object(migration, "_publish_pin", wraps=original):
        assert storage.ensure()["status"] == "ready"
    assert storage.slot["store_id"] == planned["store_id"]


@pytest.mark.parametrize("point", ["metadata", "verified", "ready-pin", "report"])
def test_crash_after_commit_or_publication_recovers_exact_uuid(
    storage: StorageHarness, point: str
) -> None:
    storage.create()
    atomic, pin, inspect = (
        migration._atomic,
        migration._publish_pin,
        migration._inspect_target,
    )
    injected = False

    def fail_atomic(path: Path, value: object) -> None:
        nonlocal injected
        if not injected and (
            (
                point == "verified"
                and isinstance(value, dict)
                and value.get("state") == "verified"
            )
            or (point == "report" and path.name == "report.json")
        ):
            injected = True
            raise OSError("interrupted private output")
        atomic(path, value)

    def fail_pin(
        root: Path, target: StoreTarget, store_id: str, checksum: str, state: str
    ) -> None:
        nonlocal injected
        if point == "ready-pin" and state == "ready" and not injected:
            injected = True
            raise OSError("interrupted ready publication")
        pin(root, target, store_id, checksum, state)

    def fail_inspect(
        target: StoreTarget,
        descriptor: JsonObject,
        driver: SQLiteDriver,
        *,
        parity: bool = False,
        deadline: float | None = None,
    ) -> JsonObject:
        nonlocal injected
        result = inspect(target, descriptor, driver, parity=parity, deadline=deadline)
        if point == "metadata" and result.get("store_id") is not None and not injected:
            injected = True
            raise OSError("interrupted after commit")
        return result

    with (
        patch.object(migration, "_atomic", side_effect=fail_atomic),
        patch.object(migration, "_publish_pin", side_effect=fail_pin),
        patch.object(migration, "_inspect_target", side_effect=fail_inspect),
    ):
        assert storage.ensure()["blocked"] is True
    assert injected
    uuid = storage.slot["store_id"]
    assert storage.service.resume(storage.context)["status"] == "ready"
    assert storage.slot["store_id"] == uuid and storage.parity()["store_id"] == uuid
    directory = storage.service._journal(
        storage.owner, str(storage.slot["plan_checksum"])
    )
    assert (directory / "report.json").is_file()


def test_source_drift_and_corrupt_backup_do_not_get_second_backup(
    storage: StorageHarness,
) -> None:
    storage.create()
    with patch.object(
        migration, "add_store_identity", side_effect=OSError("interrupt")
    ):
        assert storage.ensure()["blocked"]
    directory = storage.service._journal(
        storage.owner, str(storage.slot["plan_checksum"])
    )
    (directory / "backup/database.sqlite3").write_bytes(b"corrupt")
    with patch.object(
        storage.backup, "create", side_effect=AssertionError("second backup")
    ):
        assert storage.service.resume(storage.context)["blocked"] is True
    assert storage.slot["state"] == "pending"


def test_changed_source_after_pending_conflicts(storage: StorageHarness) -> None:
    storage.create()
    with patch.object(storage.backup, "create", side_effect=OSError("interrupt")):
        storage.ensure()
    with sqlite3.connect(storage.target.target) as connection:
        connection.execute(
            "INSERT INTO admissions(event_id,payload_hash) VALUES('late','late')"
        )
    assert (
        storage.service.resume(storage.context)["error"]["code"]
        == "storage_source_changed"
    )


def test_pending_access_blocked_and_ready_access_holds_gate(
    storage: StorageHarness,
) -> None:
    storage.create()
    with patch.object(storage.backup, "create", side_effect=OSError("interrupt")):
        storage.ensure()
    with pytest.raises(MaintenanceError, match="storage_resume_required"):
        with migration.storage_identity_access(
            storage.context, storage.target, registry_lock=storage.lock
        ):
            pytest.fail("pending opened")
    assert storage.service.resume(storage.context)["status"] == "ready"
    with migration.storage_identity_access(
        storage.context, storage.target, registry_lock=storage.lock
    ) as identity:
        assert identity == storage.slot["store_id"] and storage.gates == [
            "storage-identity"
        ]


def test_explicit_new_initializer_pins_before_creation_and_commits_metadata(
    storage: StorageHarness,
) -> None:
    with storage.service.new_store_identity(
        storage.context, storage.target
    ) as identity:
        assert storage.slot["state"] == "pending" and not storage.target.target.exists()
        storage.create()
        with sqlite3.connect(storage.target.target) as connection:
            connection.execute("BEGIN IMMEDIATE")
            migration.add_store_identity(connection, storage.target, identity)
    assert storage.slot["state"] == "ready"
    assert storage.ensure()["status"] == "ready"


def test_deadline_before_work_preserves_nonmutation(storage: StorageHarness) -> None:
    storage.create()
    result = storage.service.ensure_ready(
        storage.context, trigger="first_write", deadline=time.monotonic() - 1
    )
    assert result["error"]["code"] == "storage_deadline_exceeded"
    assert not storage.slot


def test_safety_generation_changed_after_pending_refuses(
    storage: StorageHarness,
) -> None:
    storage.create()
    with patch.object(storage.backup, "create", side_effect=OSError("interrupt")):
        storage.ensure()
    storage.generation = "fixture-exclusion-2"
    assert (
        storage.service.resume(storage.context)["error"]["code"]
        == "storage_safety_changed"
    )
    assert storage.slot["state"] == "pending"


def test_malformed_and_duplicate_pins_fail_closed(storage: StorageHarness) -> None:
    storage.create()
    storage.ensure()
    pins = storage.owner / "data/storage-identities.json"
    document = json.loads(pins.read_text(encoding="utf-8"))
    document["slots"].append(document["slots"][0])
    pins.write_text(json.dumps(document), encoding="utf-8")
    assert storage.ensure()["error"]["code"] == "storage_identity_conflict"


def test_unsafe_target_outside_owner(storage: StorageHarness) -> None:
    target = StoreTarget(
        "events",
        storage.root / "outside.sqlite3",
        "../outside.sqlite3",
        "project",
        "stable-project",
    )
    context = StorageMigrationContext(
        storage.project, None, storage.context.device_config_path, (target,)
    )
    assert storage.service.inspect(context)["blocked"] is True


def test_backup_restore_of_adopted_store_preserves_uuid(
    storage: StorageHarness,
) -> None:
    storage.create()
    storage.ensure()
    bundle, target = storage.root / "adopted-backup", storage.root / "restored.sqlite3"
    storage.backup.create(storage.target.target, bundle)
    storage.backup.restore(bundle, target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT store_id FROM pf_store_meta").fetchone() == (
            storage.slot["store_id"],
        )


def test_existing_inspect_is_readonly_and_does_not_take_proof(
    storage: StorageHarness,
) -> None:
    storage.create()
    original = storage.target.target.read_bytes()
    with (
        patch.object(
            storage.service, "safety", side_effect=AssertionError("inspect proof")
        ),
        patch.object(migration, "uuid4", side_effect=AssertionError("inspect mint")),
    ):
        result = storage.service.inspect(storage.context)
    assert result["status"] == "planned" and result["targets"][0]["state"] == "legacy"
    assert storage.target.target.read_bytes() == original and not storage.slot
    assert not storage.gates


def test_corrupt_file_is_not_rebuilt(storage: StorageHarness) -> None:
    storage.target.target.parent.mkdir(parents=True)
    storage.target.target.write_bytes(b"corrupt SQLite bytes")
    result = storage.ensure()
    assert (
        result["blocked"]
        and storage.target.target.read_bytes() == b"corrupt SQLite bytes"
    )
    assert not storage.slot


def test_explicit_initializer_crash_after_metadata_is_resumable(
    storage: StorageHarness,
) -> None:
    with pytest.raises((OSError, ExecutionError)):
        with storage.service.new_store_identity(
            storage.context, storage.target
        ) as identity:
            storage.create()
            with sqlite3.connect(storage.target.target) as connection:
                connection.execute("BEGIN IMMEDIATE")
                migration.add_store_identity(connection, storage.target, identity)
            raise OSError("interrupted after metadata")
    pending = storage.slot
    assert pending["state"] == "pending"
    assert storage.service.resume(storage.context)["status"] == "ready"
    assert storage.slot["store_id"] == pending["store_id"]


def test_explicit_initializer_before_creation_retries_same_uuid(
    storage: StorageHarness,
) -> None:
    with pytest.raises((OSError, ExecutionError)):
        with storage.service.new_store_identity(storage.context, storage.target):
            raise OSError("interrupted before creation")
    identity = storage.slot["store_id"]
    with storage.service.new_store_identity(storage.context, storage.target) as retried:
        assert retried == identity
        storage.create()
        with sqlite3.connect(storage.target.target) as connection:
            connection.execute("BEGIN IMMEDIATE")
            migration.add_store_identity(connection, storage.target, retried)
    assert storage.slot["state"] == "ready"


def test_symlink_target_is_refused(storage: StorageHarness) -> None:
    source = storage.root / "outside.sqlite3"
    create_legacy(source, "events")
    storage.target.target.parent.mkdir(parents=True)
    try:
        storage.target.target.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable for this test account")
    assert storage.ensure()["error"]["code"] == "storage_path_unsafe"


def test_two_targets_progress_independently(storage: StorageHarness) -> None:
    storage.create()
    raw = StoreTarget(
        "raw",
        storage.flow / "runtime/z-raw.sqlite3",
        "runtime/z-raw.sqlite3",
        "project",
        "stable-project",
    )
    create_legacy(raw.target, "raw")
    storage.context = StorageMigrationContext(
        storage.project, None, storage.context.device_config_path, (storage.target, raw)
    )
    original = storage.backup.create

    def interrupt(source: Path, bundle: Path) -> JsonObject:
        if source == raw.target:
            raise MaintenanceError("fixture_second_target_interrupt")
        return original(source, bundle)

    with patch.object(storage.backup, "create", side_effect=interrupt):
        result = storage.ensure()
    assert result["blocked"] and storage.slot["state"] == "ready"
    first_uuid = storage.slot["store_id"]
    pending_slot = migration._slot(storage.flow, raw)
    assert pending_slot is not None and pending_slot["state"] == "pending"
    assert storage.service.resume(storage.context)["status"] == "ready"
    assert storage.slot["store_id"] == first_uuid


def test_wal_snapshot_contains_committed_rows(storage: StorageHarness) -> None:
    storage.create()
    connection = SQLiteDriver()._connect(storage.target.target, isolation_level=None)
    try:
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute(
            "INSERT INTO admissions(event_id,payload_hash) VALUES('wal-only','opaque')"
        )
        result = storage.ensure()
        assert result["status"] == "ready", result
        directory = storage.service._journal(
            storage.owner, str(storage.slot["plan_checksum"])
        )
        with sqlite3.connect(directory / "backup/database.sqlite3") as backup:
            assert backup.execute(
                "SELECT event_id FROM admissions ORDER BY seq"
            ).fetchall() == [("exact-event",), ("wal-only",)]
    finally:
        connection.close()


def test_adapter_ready_replacement_different_uuid_refuses(
    storage: StorageHarness,
) -> None:
    storage.create()
    assert storage.ensure()["status"] == "ready"
    with sqlite3.connect(storage.target.target) as connection:
        connection.execute("UPDATE pf_store_meta SET store_id=?", ("f" * 32,))
    with pytest.raises(MaintenanceError, match="storage_identity_conflict"):
        with migration.storage_identity_access(
            storage.context, storage.target, registry_lock=storage.lock
        ):
            pytest.fail("foreign UUID opened")
