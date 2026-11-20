"""Behavioral contracts for disconnected canonical Work DDL.

Fixtures explicitly initialize disposable project stores through the real database
foundation. These tests do not implement or qualify a Work mutation protocol.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.database import (
    Database,
    DatabaseError,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaDefinition,
    SchemaManager,
    SQLiteDriver,
    SqlSession,
    SqlStatement,
    SqlValue,
)
from processforge_core.work.schema import work_migration_schema, work_schema
from processforge_core.work.selection_schema import selection_schema

_P = "project-uuid"
_H = "sha256:" + hashlib.sha256(b"fixture").hexdigest()
_SCHEMAS = (work_schema(), work_migration_schema(), selection_schema())


def _definition(namespace: str, statements: tuple[str, ...]) -> SchemaDefinition:
    raw = json.dumps(
        {"namespace": namespace, "version": 1, "statements": statements},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return SchemaDefinition(
        namespace, 1, statements, "sha256:" + hashlib.sha256(raw).hexdigest()
    )


@pytest.fixture
def store_path(request: pytest.FixtureRequest) -> Path:
    # Match the database foundation fixtures: inherited workspace permissions,
    # not pytest's restrictive mode-0700 directory creation on managed Windows.
    base = request.config.getoption("basetemp")
    if base is None:
        factory = request.getfixturevalue("tmp_path_factory")
        root = factory.getbasetemp()
    else:
        root = Path(base)
    path = root / uuid4().hex
    path.mkdir(parents=True)
    return path / "project.sqlite3"


def _database(path: Path, *, owner: str = _P, store: str = "a" * 32) -> Database:
    return Database(
        SQLiteDriver(), DatabaseTarget(path, DatabaseIdentity(store, "project", owner))
    )


def _sample(table: str, **changes: SqlValue) -> dict[str, SqlValue]:
    samples: dict[str, dict[str, SqlValue]] = {
        "work_state": dict(
            singleton=1,
            authority="legacy",
            readiness="importing",
            generation=0,
            catalog_revision=0,
            next_change_seq=1,
            active_coverage="unknown",
            protocol_version=1,
            required_features="[]",
            migration_id=None,
            plan_hash=None,
        ),
        "work_entities": dict(
            kind="run",
            entity_id="r",
            revision=1,
            generation=0,
            payload_version=1,
            payload="{}",
            payload_hash=_H,
            changed_seq=1,
            source_order="001",
            integrity="valid",
            source_ref=None,
            status_raw="open",
            objective_raw="",
            objective_normalized="",
            created_lex="",
            updated_lex="",
            process_ref="",
            context_ref="",
            session_id="",
            deleted=0,
        ),
        "work_members": dict(
            run_id="r",
            ordinal=0,
            assignment_ref="a",
            member_status="open",
            member_payload="{}",
        ),
        "work_operations": dict(
            operation_id="op",
            operation_kind="start",
            client_key="key",
            request_version=1,
            request_hash=_H,
            request_body="{}",
            accepted_version=1,
            accepted_hash=_H,
            accepted_body="{}",
            receipt_version=1,
            receipt="{}",
            receipt_hash=_H,
            accepted_seq=1,
            origin="client",
        ),
        "work_history": dict(
            seq=1,
            operation_id="op",
            entity_kind="run",
            entity_id="r",
            entity_revision=1,
            record_version=1,
            history_kind="import_snapshot",
            body="{}",
            body_hash=_H,
            occurred_at="old lexical timestamp",
        ),
        "work_operation_state": dict(
            operation_id="op",
            revision=1,
            state="pending",
            next_due_at="",
            last_error_code="",
            pending_steps=1,
        ),
        "work_events": dict(
            event_id="e",
            operation_id="op",
            ordinal=0,
            event_type="created",
            event_version=1,
            canonical_envelope="{}",
            envelope_hash=_H,
            change_seq=1,
        ),
        "work_outbox": dict(
            step_id="s",
            operation_id="op",
            ordinal=0,
            target_kind="immutable_link",
            target_key="capsule",
            target_revision=1,
            payload_version=1,
            payload="{}",
            payload_hash=_H,
            status="pending",
            next_due_at="",
            claim_epoch=0,
            attempt_count=0,
            last_error_code="",
        ),
        "work_file_refs": dict(
            object_id="f",
            hash=_H,
            size=0,
            media_type="application/octet-stream",
            ref_version=1,
            relative_path=".pf/objects/fixture",
            role="source",
            immutable=1,
        ),
        "work_entity_files": dict(
            entity_kind="run",
            entity_id="r",
            entity_revision=1,
            object_id="f",
            role="source",
            ordinal=0,
        ),
        "work_bindings": dict(
            binding_id="b",
            run_id="r",
            assignment_id="a",
            context_id="c",
            session_id="session",
            revision=1,
            generation=0,
            payload="{}",
            hash=_H,
            changed_seq=1,
        ),
        "work_health": dict(
            issue_id="i",
            entity_kind="malformed legacy kind",
            entity_id="missing",
            code="import_invalid",
            severity="blocking",
            source_hash=_H,
            state="open",
            changed_seq=1,
        ),
        "work_scope_reservations": dict(
            reservation_id="reservation",
            entity_id="a",
            revision=1,
            generation=0,
            scope_version=1,
            scope="{}",
            active=1,
            changed_seq=1,
        ),
        "work_migrations": dict(
            migration_id="m",
            descriptor_version=1,
            descriptor_hash=_H,
            source_manifest_hash=_H,
            source_generation=0,
            target_namespace_version=1,
            phase="planned",
            cursor="",
            imported_units=0,
            high_water="",
            verification_hash=None,
            revision=1,
            last_error_code="",
        ),
    }
    return dict(project_id=_P, **samples[table]) | changes


def _insert(session: SqlSession, table: str, **changes: SqlValue) -> None:
    row = _sample(table, **changes)
    session.execute(
        SqlStatement(
            f"INSERT INTO {table}({','.join(row)}) VALUES({','.join('?' for _ in row)})",
            tuple(row.values()),
        )
    )


def _all(
    database: Database, text: str, params: tuple[SqlValue, ...] = ()
) -> list[tuple[SqlValue, ...]]:
    with database.read() as session:
        with session.stream(SqlStatement(text, params)) as rows:
            return [row.values for row in rows]


@pytest.fixture
def database(store_path: Path) -> Database:
    database = _database(store_path)
    SchemaManager().initialize(database, _SCHEMAS)
    with database.transaction() as session:
        _insert(session, "work_state")
        _insert(session, "work_entities")
        _insert(session, "work_entities", kind="assignment", entity_id="a")
        for table in (
            "work_members",
            "work_operations",
            "work_history",
            "work_operation_state",
            "work_events",
            "work_outbox",
            "work_file_refs",
            "work_entity_files",
            "work_bindings",
            "work_health",
            "work_scope_reservations",
            "work_migrations",
        ):
            _insert(session, table)
    return database


@pytest.mark.parametrize(
    "factory,namespace",
    [(work_schema, "work"), (work_migration_schema, "work_migration")],
)
def test_descriptor_is_canonical_immutable_and_cold(
    factory, namespace: str, monkeypatch: pytest.MonkeyPatch, store_path: Path
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("descriptor opened a connection")

    monkeypatch.setattr(SQLiteDriver, "_connect", forbidden)
    first = factory()
    assert first == factory() == _definition(namespace, first.statements)
    assert first.version == 1
    with pytest.raises(FrozenInstanceError):
        setattr(first, "version", 2)
    assert not store_path.exists()


def test_inspection_never_creates_store(store_path: Path) -> None:
    database = _database(store_path)
    assert SchemaManager().inspect(database, _SCHEMAS).state == "missing"
    for context in (database.read, database.transaction):
        with pytest.raises(DatabaseError, match="database_missing"):
            with context():
                pass
    assert not store_path.exists()
    assert list(store_path.parent.iterdir()) == []


def test_explicit_registration_coexists_and_reapply_is_idempotent(
    store_path: Path,
) -> None:
    database = _database(store_path)
    manager = SchemaManager()
    initial_selection = selection_schema()
    assert manager.initialize(database, (initial_selection,)).state == "ready"
    assert manager.inspect(database, _SCHEMAS).state == "migration_required"
    before = _all(
        database,
        "SELECT name,sql FROM sqlite_schema WHERE name LIKE 'work_%' ORDER BY name",
    )
    assert manager.apply(database, _SCHEMAS).state == "ready"
    assert manager.apply(database, tuple(reversed(_SCHEMAS))).state == "ready"
    assert selection_schema() == initial_selection
    after = _all(
        database,
        "SELECT name,sql FROM sqlite_schema WHERE name LIKE 'work_%' ORDER BY name",
    )
    assert all(row in after for row in before)
    assert len(manager.inspect(database, _SCHEMAS).versions) == 3
    expected = {
        "work_state",
        "work_entities",
        "work_members",
        "work_history",
        "work_operations",
        "work_operation_state",
        "work_events",
        "work_outbox",
        "work_file_refs",
        "work_entity_files",
        "work_bindings",
        "work_health",
        "work_scope_reservations",
        "work_migrations",
        "work_selection_state",
        "work_run_selection",
        "work_selection_edges",
        "work_valid_pending_edges",
        "work_standalone_selection",
    }
    assert {
        row[0]
        for row in _all(
            database,
            "SELECT name FROM sqlite_schema WHERE type='table' AND name LIKE 'work_%'",
        )
    } == expected
    assert _all(database, "SELECT name FROM sqlite_schema WHERE type='trigger'") == []
    with pytest.raises(DatabaseError, match="database_foreign"):
        manager.initialize(database, _SCHEMAS)
    changed = _definition(
        "work", work_schema().statements + ("CREATE TABLE unexpected(x INTEGER)",)
    )
    assert manager.inspect(database, (changed,)).state == "unsupported"
    with pytest.raises(DatabaseError, match="database_schema_unsupported"):
        manager.apply(database, (changed,))


@pytest.mark.parametrize(
    "bad_statement",
    [
        "CREATE TABLE bad_constraint(x INTEGER CHECK(no_such_column>0))",
        "INSERT INTO work_members(project_id,run_id,ordinal,assignment_ref,member_status,member_payload) VALUES('p','absent',0,'a','','{}')",
    ],
)
def test_namespace_ddl_rollback_on_invalid_constraint_or_foreign_link(
    store_path: Path, bad_statement: str
) -> None:
    database = _database(store_path)
    manager = SchemaManager()
    manager.initialize(database, (selection_schema(),))
    broken = _definition("work", work_schema().statements + (bad_statement,))
    before = _all(database, "SELECT name,sql FROM sqlite_schema ORDER BY name")
    with pytest.raises(DatabaseError):
        manager.apply(database, (broken, work_migration_schema()))
    assert _all(database, "SELECT name,sql FROM sqlite_schema ORDER BY name") == before
    assert [
        row[0] for row in _all(database, "SELECT namespace FROM pf_schema_versions")
    ] == ["work_selection"]


def test_project_and_store_identity_gate(database: Database) -> None:
    for foreign in (
        _database(database.target.path, owner="other"),
        _database(database.target.path, store="b" * 32),
    ):
        with pytest.raises(DatabaseError, match="database_foreign"):
            with foreign.read():
                pass
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(session, "work_state", singleton=2, project_id="other")
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(session, "work_entities", project_id="other", entity_id="other")


@pytest.mark.parametrize(
    "table",
    [
        "work_members",
        "work_history",
        "work_operation_state",
        "work_events",
        "work_outbox",
        "work_entity_files",
        "work_bindings",
        "work_scope_reservations",
        "work_migrations",
    ],
)
def test_composite_project_links_and_atomic_dml_rollback(
    database: Database, table: str
) -> None:
    # Keep real valid IDs but replace their project. A second owner must not
    # link them; a preceding operation in the same transaction rolls back too.
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(
                session, "work_operations", operation_id="rolled-back", client_key=None
            )
            session.execute(
                SqlStatement(f"UPDATE {table} SET project_id=?", ("other",))
            )
    assert (
        _all(
            database,
            "SELECT operation_id FROM work_operations WHERE operation_id='rolled-back'",
        )
        == []
    )


def test_typed_foreign_keys_reject_same_id_wrong_entity_kind(
    database: Database,
) -> None:
    invalid_links: list[tuple[str, dict[str, SqlValue]]] = [
        ("work_members", dict(run_id="a", ordinal=1)),
        ("work_bindings", dict(binding_id="b2", run_id="a")),
        ("work_bindings", dict(binding_id="b2", assignment_id="r")),
        ("work_scope_reservations", dict(reservation_id="s2", entity_id="r")),
    ]
    for table, changes in invalid_links:
        with pytest.raises(DatabaseError, match="database_constraint_failed"):
            with database.transaction() as session:
                _insert(session, table, **changes)


def test_members_preserve_duplicates_order_and_missing_bodies(
    database: Database,
) -> None:
    with database.transaction() as session:
        _insert(session, "work_members", ordinal=1)
        _insert(session, "work_members", ordinal=2, assignment_ref="missing")
        _insert(
            session,
            "work_members",
            ordinal=3,
            assignment_ref="",
            member_payload='{"raw_ref":null}',
        )
    assert _all(
        database,
        "SELECT ordinal,assignment_ref FROM work_members WHERE project_id=? AND run_id='r' ORDER BY ordinal",
        (_P,),
    ) == [(0, "a"), (1, "a"), (2, "missing"), (3, "")]
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(session, "work_members", assignment_ref="different")


def test_empty_placeholder_orphan_and_import_evidence(database: Database) -> None:
    with database.transaction() as session:
        _insert(session, "work_entities", entity_id="empty-run")
        _insert(
            session,
            "work_entities",
            kind="assignment",
            entity_id="first-assignment",
            integrity="placeholder",
            payload="{}",
        )
        _insert(
            session,
            "work_entities",
            kind="assignment",
            entity_id="orphan",
            integrity="orphan",
            payload='{"body_ref":"f"}',
            source_ref="legacy/orphan.yaml",
        )
        _insert(
            session,
            "work_entities",
            kind="continuation",
            entity_id="bad-import",
            integrity="invalid",
            payload='{"raw_ref":"f"}',
            source_ref="legacy/broken.yaml",
        )
    assert _all(
        database, "SELECT COUNT(*) FROM work_members WHERE run_id='empty-run'"
    ) == [(0,)]
    assert _all(
        database,
        "SELECT integrity,payload FROM work_entities WHERE entity_id='first-assignment'",
    ) == [("placeholder", "{}")]
    assert _all(
        database,
        "SELECT integrity,source_ref FROM work_entities WHERE entity_id='orphan'",
    ) == [("orphan", "legacy/orphan.yaml")]
    assert _all(database, "SELECT entity_kind,entity_id,code FROM work_health") == [
        ("malformed legacy kind", "missing", "import_invalid")
    ]


def test_client_keys_use_kind_project_and_null_semantics(database: Database) -> None:
    with database.transaction() as session:
        for operation in ("no-key-1", "no-key-2"):
            _insert(
                session,
                "work_operations",
                operation_id=operation,
                client_key=None,
                origin="internal",
            )
        _insert(
            session,
            "work_operations",
            operation_id="different-kind",
            operation_kind="transition",
        )
        _insert(session, "work_operations", operation_id="empty-key", client_key="")
    for changes in (
        dict(operation_id="same-key"),
        dict(operation_id="empty-key-2", client_key=""),
        dict(client_key="different"),
    ):
        with pytest.raises(DatabaseError, match="database_constraint_failed"):
            with database.transaction() as session:
                _insert(session, "work_operations", **changes)
    assert _all(
        database, "SELECT COUNT(*) FROM work_operations WHERE client_key IS NULL"
    ) == [(2,)]


@pytest.mark.parametrize(
    "table,changes",
    [
        ("work_history", dict(seq=2)),
        ("work_events", dict(event_id="e2")),
        ("work_outbox", dict(step_id="s2")),
        ("work_file_refs", dict(object_id="f2")),
    ],
)
def test_logical_uniqueness(
    database: Database, table: str, changes: dict[str, SqlValue]
) -> None:
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(session, table, **changes)


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("work_state", "generation", -1),
        ("work_state", "catalog_revision", -1),
        ("work_state", "next_change_seq", 0),
        ("work_state", "next_change_seq", 1.5),
        ("work_state", "protocol_version", 2),
        ("work_state", "authority", "other"),
        ("work_state", "readiness", "active"),
        ("work_state", "active_coverage", "maybe"),
        ("work_entities", "revision", 0),
        ("work_entities", "generation", -1),
        ("work_entities", "payload_version", 0),
        ("work_entities", "changed_seq", 0),
        ("work_entities", "integrity", "missing"),
        ("work_entities", "deleted", 2),
        ("work_members", "ordinal", -1),
        ("work_members", "run_kind", "assignment"),
        ("work_operations", "request_version", 0),
        ("work_operations", "accepted_version", 0),
        ("work_operations", "receipt_version", 0),
        ("work_operations", "accepted_seq", 0),
        ("work_operations", "origin", "retry"),
        ("work_history", "seq", 0),
        ("work_history", "seq", None),
        ("work_history", "entity_revision", 0),
        ("work_history", "record_version", 0),
        ("work_operation_state", "revision", 0),
        ("work_operation_state", "state", "lost"),
        ("work_operation_state", "pending_steps", -1),
        ("work_events", "ordinal", -1),
        ("work_events", "event_version", 0),
        ("work_events", "change_seq", 0),
        ("work_outbox", "ordinal", -1),
        ("work_outbox", "target_revision", -1),
        ("work_outbox", "target_kind", "unknown"),
        ("work_outbox", "payload_version", 0),
        ("work_outbox", "status", "lost"),
        ("work_outbox", "claim_epoch", -1),
        ("work_outbox", "attempt_count", -1),
        ("work_file_refs", "size", -1),
        ("work_file_refs", "ref_version", 2),
        ("work_file_refs", "immutable", 0),
        ("work_entity_files", "entity_revision", 0),
        ("work_entity_files", "ordinal", -1),
        ("work_bindings", "revision", 0),
        ("work_bindings", "generation", -1),
        ("work_bindings", "changed_seq", 0),
        ("work_health", "severity", "warning"),
        ("work_health", "state", "hidden"),
        ("work_health", "changed_seq", 0),
        ("work_scope_reservations", "revision", 0),
        ("work_scope_reservations", "generation", -1),
        ("work_scope_reservations", "scope_version", 0),
        ("work_scope_reservations", "active", 2),
        ("work_scope_reservations", "changed_seq", 0),
        ("work_migrations", "descriptor_version", 0),
        ("work_migrations", "source_generation", -1),
        ("work_migrations", "target_namespace_version", 0),
        ("work_migrations", "imported_units", -1),
        ("work_migrations", "phase", "active"),
        ("work_migrations", "revision", 0),
    ],
)
def test_versions_statuses_ordinals_and_counters(
    database: Database, table: str, field: str, value: SqlValue
) -> None:
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            session.execute(SqlStatement(f"UPDATE {table} SET {field}=?", (value,)))


@pytest.mark.parametrize(
    "bad_hash",
    [
        "sha256:" + "A" * 64,
        "sha256:" + "g" * 64,
        "sha256:" + "0" * 63,
        "sha512:" + "0" * 64,
        "sha256:" + "0" * 63 + "\x00",
        "sha256:" + "0" * 64 + "\x00",
    ],
)
@pytest.mark.parametrize(
    "table,field",
    [
        ("work_entities", "payload_hash"),
        ("work_operations", "receipt_hash"),
        ("work_events", "envelope_hash"),
        ("work_file_refs", "hash"),
        ("work_migrations", "verification_hash"),
    ],
)
def test_digest_shape(
    database: Database, table: str, field: str, bad_hash: str
) -> None:
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            session.execute(SqlStatement(f"UPDATE {table} SET {field}=?", (bad_hash,)))


def test_receipt_is_separate_from_mutable_delivery_state(database: Database) -> None:
    receipt = _all(
        database, "SELECT receipt_version,receipt,receipt_hash FROM work_operations"
    )
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            session.execute(
                SqlStatement("UPDATE work_operation_state SET state='applied'")
            )
    with database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE work_outbox SET status='applied',claim_epoch=1,attempt_count=1"
            )
        )
        session.execute(
            SqlStatement(
                "UPDATE work_operation_state SET state='applied',pending_steps=0,revision=revision+1"
            )
        )
    assert (
        _all(
            database, "SELECT receipt_version,receipt,receipt_hash FROM work_operations"
        )
        == receipt
    )
    assert _all(
        database, "SELECT state,pending_steps,revision FROM work_operation_state"
    ) == [("applied", 0, 2)]


def test_historical_references_survive_current_revision_change(
    database: Database,
) -> None:
    with database.transaction() as session:
        session.execute(
            SqlStatement(
                "UPDATE work_entities SET revision=2,payload=?,changed_seq=2 WHERE kind='run' AND entity_id='r'",
                ('{"body_ref":"f2"}',),
            )
        )
        _insert(session, "work_history", seq=2, entity_revision=2, history_kind="delta")
        _insert(
            session,
            "work_file_refs",
            object_id="f2",
            relative_path=".pf/objects/second",
        )
        _insert(session, "work_entity_files", entity_revision=2, object_id="f2")
    assert _all(
        database,
        "SELECT entity_revision,object_id FROM work_entity_files ORDER BY entity_revision",
    ) == [(1, "f"), (2, "f2")]
    for statement in (
        "DELETE FROM work_file_refs WHERE object_id='f'",
        "DELETE FROM work_history WHERE seq=1",
        "DELETE FROM work_operations WHERE operation_id='op'",
    ):
        with pytest.raises(DatabaseError, match="database_constraint_failed"):
            with database.transaction() as session:
                session.execute(SqlStatement(statement))
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            _insert(session, "work_entity_files", entity_revision=3)
    with database.transaction() as session:
        # Same bytes can have a separate semantic object ID at another locator.
        _insert(
            session,
            "work_file_refs",
            object_id="same-bytes",
            relative_path=".pf/objects/other-role",
        )


def test_high_water_history_keyset_and_future_record_versions(
    database: Database,
) -> None:
    with database.transaction() as session:
        for revision in range(2, 6):
            _insert(
                session,
                "work_history",
                seq=revision,
                entity_revision=revision,
                record_version=2,
            )
    assert _all(
        database,
        "SELECT seq,record_version FROM work_history WHERE project_id=? AND seq>? AND seq<=? ORDER BY seq LIMIT ?",
        (_P, 1, 4, 2),
    ) == [(2, 2), (3, 2)]
    assert _all(
        database,
        "SELECT seq FROM work_history WHERE project_id=? AND seq>? AND seq<=? ORDER BY seq LIMIT ?",
        (_P, 3, 4, 2),
    ) == [(4,)]
    # Positive future versions can be preserved. Supporting/decoding one is a
    # future codec decision; DDL must not silently coerce it to v1.


@pytest.mark.parametrize(
    "index,sql,params",
    [
        (
            "work_entity_status",
            "SELECT entity_id FROM work_entities WHERE project_id=? AND kind='run' AND status_raw='open' AND deleted=0",
            (_P,),
        ),
        (
            "work_member_lookup",
            "SELECT run_id,ordinal FROM work_members WHERE project_id=? AND assignment_ref='a'",
            (_P,),
        ),
        (
            "work_member_pair",
            "SELECT ordinal FROM work_members WHERE project_id=? AND run_id='r' AND assignment_ref='a' ORDER BY ordinal",
            (_P,),
        ),
        (
            "work_history_entity",
            "SELECT seq FROM work_history WHERE project_id=? AND entity_kind='run' AND entity_id='r' AND seq>0 ORDER BY seq",
            (_P,),
        ),
        (
            "work_history_tail",
            "SELECT seq FROM work_history WHERE project_id=? AND seq>0 ORDER BY seq LIMIT 2",
            (_P,),
        ),
        (
            "work_client_key",
            "SELECT operation_id FROM work_operations WHERE project_id=? AND operation_kind='start' AND client_key='key'",
            (_P,),
        ),
        (
            "work_event_tail",
            "SELECT event_id FROM work_events WHERE project_id=? AND change_seq>0 ORDER BY change_seq,event_id",
            (_P,),
        ),
        (
            "work_pending_operations",
            "SELECT operation_id FROM work_operation_state WHERE project_id=? AND state IN ('pending','blocked') AND next_due_at<=? ORDER BY next_due_at,operation_id LIMIT 2",
            (_P, "z"),
        ),
        (
            "work_pending_delivery",
            "SELECT step_id FROM work_outbox WHERE project_id=? AND status IN ('pending','claimed','blocked') AND next_due_at<=? ORDER BY next_due_at,step_id LIMIT 2",
            (_P, "z"),
        ),
        (
            "work_target_delivery",
            "SELECT step_id FROM work_outbox WHERE project_id=? AND target_kind='immutable_link' AND target_key='capsule' ORDER BY target_revision,step_id",
            (_P,),
        ),
        (
            "work_health_status",
            "SELECT issue_id FROM work_health WHERE project_id=? AND severity='blocking' AND state='open'",
            (_P,),
        ),
        (
            "work_health_blocking",
            "SELECT issue_id FROM work_health WHERE project_id=? AND code='import_invalid' AND state='open' AND severity='blocking'",
            (_P,),
        ),
        (
            "work_reservation_active",
            "SELECT reservation_id FROM work_scope_reservations WHERE project_id=? AND active=1",
            (_P,),
        ),
    ],
)
def test_relevant_queries_have_real_index_seeks(
    database: Database,
    index: str,
    sql: str,
    params: tuple[SqlValue, ...],
    record_property: Callable[[str, object], None],
) -> None:
    assert _all(
        database,
        "SELECT name FROM sqlite_schema WHERE type='index' AND name=?",
        (index,),
    ) == [(index,)]
    plan = " ".join(
        str(row[3]) for row in _all(database, "EXPLAIN QUERY PLAN " + sql, params)
    )
    record_property("expected_index", index)
    record_property("sql", sql)
    record_property("query_plan", plan)
    assert index in plan
    assert "SEARCH" in plan and "TEMP B-TREE" not in plan
    assert _all(database, sql, params)


def test_namespace_has_no_lifecycle_side_effects(store_path: Path) -> None:
    database = _database(store_path)
    SchemaManager().initialize(database, _SCHEMAS)
    for table in (
        "work_state",
        "work_entities",
        "work_operations",
        "work_migrations",
        "work_selection_state",
    ):
        assert _all(database, f"SELECT COUNT(*) FROM {table}") == [(0,)]
    # Descriptors can be registered without activating work or manufacturing
    # a generation, authority row, selection coverage or migration checkpoint.
    wrong_store = replace(
        database.target, identity=DatabaseIdentity("c" * 32, "project", _P)
    )
    with pytest.raises(DatabaseError, match="database_foreign"):
        SchemaManager().inspect(Database(SQLiteDriver(), wrong_store), _SCHEMAS)
