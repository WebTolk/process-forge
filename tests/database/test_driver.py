"""Native connection transport preserves SQLite options and native failures."""

import sqlite3

import pytest

from processforge_core.configuration import DatabaseConfig
from processforge_core.database import STORE_ENVELOPE_DDL, DatabaseFactory, SQLiteDriver

from . import isolated_path

tmp_path = isolated_path


@pytest.mark.parametrize(
    "config", [None, DatabaseConfig(), DatabaseConfig(driver="sqlite")]
)
def test_cold_resolve_driver(config, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("cold connect")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    assert isinstance(DatabaseFactory.resolve_driver(config), SQLiteDriver)


@pytest.mark.parametrize("target", [":memory:", ""])
def test_memory_and_temp_native_transactions(target):
    connection = SQLiteDriver()._connect(target)
    try:
        connection.execute("CREATE TABLE t(x)")
        connection.execute("INSERT INTO t VALUES(1)")
        assert connection.in_transaction
        connection.rollback()
        assert connection.execute("SELECT count(*) FROM t").fetchone() == (0,)
    finally:
        connection.close()


def test_transport_exact_forwarding_and_native_error(monkeypatch):
    seen = []
    marker = sqlite3.OperationalError("native")

    def connect(*args, **kwargs):
        seen.append((args, kwargs))
        raise marker

    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError) as caught:
        SQLiteDriver()._connect(
            "file:target?mode=ro", timeout=0.05, isolation_level=None, uri=True
        )
    assert caught.value is marker
    assert seen == [
        (
            ("file:target?mode=ro",),
            {"timeout": 0.05, "isolation_level": None, "uri": True},
        )
    ]


def test_uri_noncreation_backup_and_envelope_export(tmp_path):
    driver = SQLiteDriver()
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        driver._connect(missing.as_uri() + "?mode=ro", uri=True)
    assert not missing.exists()
    source = driver._connect(":memory:", timeout=10, isolation_level=None)
    destination = driver._connect(tmp_path / "backup.sqlite3", timeout=0)
    try:
        source.execute("CREATE TABLE t(x)")
        source.execute("INSERT INTO t VALUES(7)")
        source.backup(destination)
        assert destination.execute("SELECT x FROM t").fetchone() == (7,)
    finally:
        source.close()
        destination.close()
    assert len(STORE_ENVELOPE_DDL) == 2
