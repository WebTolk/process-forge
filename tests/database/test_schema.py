"""Envelope identity, schema drift and atomic registration checks."""

import hashlib
import json
import sqlite3
from dataclasses import replace

import pytest

from processforge_core.database import (
    Database,
    DatabaseError,
    DatabaseIdentity,
    DatabaseTarget,
    SchemaDefinition,
    SchemaManager,
    SQLiteDriver,
)

from . import isolated_path

tmp_path = isolated_path


def definition(
    namespace="sample",
    version=1,
    statements=("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)",),
):
    data = {"namespace": namespace, "version": version, "statements": statements}
    checksum = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                data,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        ).hexdigest()
    )
    return SchemaDefinition(namespace, version, statements, checksum)


def database_at(tmp_path):
    return Database(
        SQLiteDriver(),
        DatabaseTarget(
            tmp_path / "pf.sqlite3", DatabaseIdentity("a" * 32, "project", "p")
        ),
    )


def test_missing_inspect_and_explicit_initialize(tmp_path):
    database = database_at(tmp_path)
    manager = SchemaManager()
    assert manager.inspect(database, (definition(),)).state == "missing"
    assert not database.target.path.exists()
    status = manager.initialize(database, (definition(),))
    assert status.state == "ready"
    assert status.identity == database.target.identity
    with pytest.raises(DatabaseError, match="database_foreign"):
        manager.initialize(database, ())
    discovery = Database(
        SQLiteDriver(),
        replace(database.target, identity=DatabaseIdentity(None, "project", "p")),
    )
    assert manager.inspect(discovery, (definition(),)).identity == status.identity
    with sqlite3.connect(database.target.path) as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0x50464D31
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_atomic_ddl_and_namespace_registration(tmp_path):
    database = database_at(tmp_path)
    manager = SchemaManager()
    manager.initialize(database, ())
    bad = definition(
        "broken", statements=("CREATE TABLE temporary_one(id INTEGER)", "invalid SQL")
    )
    with pytest.raises(DatabaseError):
        manager.apply(database, (bad,))
    with sqlite3.connect(database.target.path) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='temporary_one'"
            ).fetchone()
            is None
        )
        assert connection.execute("SELECT * FROM pf_schema_versions").fetchall() == []
    assert manager.apply(database, (definition(),)).state == "ready"
    assert manager.apply(database, (definition(),)).state == "ready"


def test_initialize_rollback_on_bad_schema(tmp_path):
    database = database_at(tmp_path)
    with pytest.raises(DatabaseError):
        SchemaManager().initialize(database, (definition(statements=("invalid SQL",)),))
    with sqlite3.connect(database.target.path) as connection:
        assert connection.execute("SELECT name FROM sqlite_master").fetchall() == []
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0


def test_drift_future_and_upgrade_refused(tmp_path):
    database = database_at(tmp_path)
    manager = SchemaManager()
    manager.initialize(database, (definition(),))
    changed = definition(statements=("CREATE TABLE other(id INTEGER)",))
    assert manager.inspect(database, (changed,)).state == "unsupported"
    assert (
        manager.inspect(database, (definition(version=2),)).state
        == "migration_required"
    )
    for schema in (changed, definition(version=2)):
        with pytest.raises(DatabaseError, match="database_schema_unsupported"):
            manager.apply(database, (schema,))
    with sqlite3.connect(database.target.path) as connection:
        connection.execute("UPDATE pf_schema_versions SET version=2")
    assert manager.inspect(database, (definition(),)).state == "unsupported"


@pytest.mark.parametrize(
    "change,code",
    [
        ("PRAGMA application_id=99", "database_foreign"),
        ("PRAGMA user_version=2", "database_schema_unsupported"),
        ("UPDATE pf_store_meta SET owner_id='other'", "database_foreign"),
        (
            "UPDATE pf_store_meta SET store_id='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'",
            "database_foreign",
        ),
        ("DELETE FROM pf_store_meta", "database_corrupt"),
    ],
)
def test_foreign_future_and_owner_mismatch(tmp_path, change, code):
    database = database_at(tmp_path)
    SchemaManager().initialize(database, ())
    with sqlite3.connect(database.target.path) as connection:
        connection.execute(change)
    if code == "database_schema_unsupported":
        assert SchemaManager().inspect(database, ()).state == "unsupported"
    else:
        with pytest.raises(DatabaseError, match=code):
            SchemaManager().inspect(database, ())
    with pytest.raises(DatabaseError, match=code):
        with database.read():
            pass


def test_corrupt_and_checksum(tmp_path):
    database = database_at(tmp_path)
    database.target.path.write_bytes(b"not a database")
    with pytest.raises(DatabaseError, match="database_corrupt"):
        SchemaManager().inspect(database, ())
    with pytest.raises(DatabaseError, match="database_schema_unsupported"):
        SchemaDefinition("x", 1, (), "sha256:" + "0" * 64)
