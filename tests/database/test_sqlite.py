"""Transactions, snapshots, bounds, deadlines and connection ownership."""

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from processforge_core.database import DatabaseError, SchemaManager, SqlStatement

from . import isolated_path
from .test_schema import database_at, definition

tmp_path = isolated_path


@pytest.fixture
def database(tmp_path):
    result = database_at(tmp_path)
    SchemaManager().initialize(result, (definition(),))
    return result


def count(database):
    with database.read() as session:
        return session.fetch_one(SqlStatement("SELECT count(*) AS n FROM sample"))["n"]


def test_missing_ro_rw_noncreation(tmp_path):
    database = database_at(tmp_path / "absent")
    for operation in (database.read, database.transaction):
        with pytest.raises(DatabaseError, match="database_missing"):
            with operation():
                pass
    assert not database.target.path.parent.exists()


def test_binding_commit_rollback_and_redaction(database):
    value = "private ' quote ; DROP TABLE sample;"
    with database.transaction() as session:
        result = session.execute(
            SqlStatement("INSERT INTO sample(value) VALUES(?)", (value,))
        )
        assert result.affected_rows == 1 and result.last_insert_id == 1

    class Abort(BaseException):
        pass

    with pytest.raises(Abort):
        with database.transaction() as session:
            session.execute(
                SqlStatement("INSERT INTO sample(value) VALUES(?)", ("rolled back",))
            )
            raise Abort()
    assert count(database) == 1
    with database.read() as session:
        assert (
            session.fetch_one(SqlStatement("SELECT value FROM sample"))["value"]
            == value
        )
        with pytest.raises(DatabaseError) as caught:
            session.execute(
                SqlStatement("INSERT INTO private_secret_table VALUES(?)", (value,))
            )
        assert value not in str(caught.value)
        assert "private_secret_table" not in str(caught.value)
        assert str(database.target.path) not in str(caught.value)
    assert caught.value.__suppress_context__


def test_snapshot_with_concurrent_writer(database):
    with database.read() as reader:
        assert reader.fetch_one(SqlStatement("SELECT count(*) FROM sample"))[0] == 0
        with database.transaction() as writer:
            writer.execute(
                SqlStatement("INSERT INTO sample(value) VALUES(?)", ("new",))
            )
        assert reader.fetch_one(SqlStatement("SELECT count(*) FROM sample"))[0] == 0
    assert count(database) == 1


def test_readonly_and_admin_denial(database):
    with database.read() as session:
        with pytest.raises(DatabaseError):
            session.execute(SqlStatement("INSERT INTO sample(value) VALUES('x')"))
    with database.transaction() as session:
        for text in (
            "PRAGMA synchronous=OFF",
            "CREATE TABLE forbidden(x)",
            "COMMIT",
            "UPDATE pf_store_meta SET owner_id='other'",
        ):
            with pytest.raises(DatabaseError):
                session.execute(SqlStatement(text))


def test_commit_failure_rolls_back_and_enforces_fk_full(database):
    SchemaManager().apply(
        database,
        (
            definition(
                "fk",
                statements=(
                    "CREATE TABLE parent(id INTEGER PRIMARY KEY)",
                    "CREATE TABLE child(parent_id INTEGER REFERENCES parent(id) DEFERRABLE INITIALLY DEFERRED)",
                ),
            ),
        ),
    )
    with pytest.raises(DatabaseError, match="database_constraint_failed"):
        with database.transaction() as session:
            session.execute(
                SqlStatement("INSERT INTO sample(value) VALUES('rollback on commit')")
            )
            session.execute(SqlStatement("INSERT INTO child VALUES(404)"))
    assert count(database) == 0
    with database.driver._admin(
        database.target, mode="rw", timeout_ms=100
    ) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert connection.execute("PRAGMA synchronous").fetchone() == (2,)
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)


def test_stream_bounds_and_early_close(database):
    with database.transaction() as session:
        assert (
            session.execute_many(
                SqlStatement("INSERT INTO sample(value) VALUES(?)"),
                [(str(n),) for n in range(600)],
            ).affected_rows
            == 600
        )
    with database.read() as session:
        with session.stream(
            SqlStatement("SELECT id FROM sample"), batch_size=2
        ) as rows:
            assert next(rows)[0] == 1
            assert len(session._cursors) == 1
        assert len(session._cursors) == 0
        assert list(rows) == []
        for size in (0, 1001, True):
            with pytest.raises(DatabaseError):
                with session.stream(SqlStatement("SELECT 1"), batch_size=size):
                    pass
    with pytest.raises(DatabaseError):
        session.fetch_one(SqlStatement("SELECT 1"))


def test_many_limits(database):
    with database.transaction() as session:
        for statement, rows in [
            (SqlStatement("SELECT ?", (1,)), [(1,)]),
            (SqlStatement("SELECT ?"), [(1,)] * 10001),
            (SqlStatement("SELECT ?"), [(True,)]),
        ]:
            with pytest.raises(DatabaseError):
                session.execute_many(statement, rows)


def test_thread_bound_session(database):
    with database.read() as session:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(DatabaseError):
                pool.submit(session.fetch_one, SqlStatement("SELECT 1")).result()


def test_busy_and_deadline_bounded(database):
    with database.transaction():
        start = time.monotonic()
        with pytest.raises(DatabaseError) as caught:
            with database.transaction():
                pass
        assert caught.value.code == "database_busy" and caught.value.retryable
        assert time.monotonic() - start < 0.8
        start = time.monotonic()
        with pytest.raises(DatabaseError) as caught:
            with database.transaction(deadline=start + 0.025):
                pass
        assert caught.value.code in ("database_busy", "database_deadline_exceeded")
        assert time.monotonic() - start < 0.5
    with pytest.raises(DatabaseError, match="database_deadline_exceeded"):
        with database.read(deadline=time.monotonic() - 1):
            pass
    with pytest.raises(DatabaseError, match="database_deadline_exceeded"):
        with database.read(deadline=time.monotonic() + 0.025) as session:
            session.fetch_one(
                SqlStatement(
                    "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n"
                )
            )


def test_concurrent_writers(database):
    barrier = threading.Barrier(2)

    def write(value):
        barrier.wait(timeout=2)
        with database.transaction() as session:
            session.execute(
                SqlStatement("INSERT INTO sample(value) VALUES(?)", (value,))
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, value) for value in ("a", "b")]
        for future in futures:
            future.result(timeout=3)
    assert count(database) == 2


def test_cursor_connection_cleanup_after_failure(database, monkeypatch):
    real = sqlite3.connect
    connections = []

    def tracked(*args, **kwargs):
        connection = real(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked)
    with pytest.raises(DatabaseError):
        with database.transaction() as session:
            session.execute(SqlStatement("broken SQL"))
    assert not session._cursors
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


def test_all_supported_values_and_row_names(database):
    values = (None, -(2**63), 2**63 - 1, 1.25, "quoted ' text", b"\x00\xff")
    with database.read() as session:
        row = session.fetch_one(
            SqlStatement("SELECT ? AS a,? AS b,? AS c,? AS d,? AS e,? AS f", values)
        )
        assert row is not None
        assert row.values == values


def test_duplicate_names_and_create_mode_denied(database):
    with database.read() as session:
        with pytest.raises(DatabaseError, match="database_constraint_failed"):
            session.fetch_one(SqlStatement("SELECT 1 AS x, 2 AS x"))
    with pytest.raises(DatabaseError, match="database_capability_unsupported"):
        with database.driver.open(database.target, mode="create", timeout_ms=100):
            pass


def test_stream_outliving_session_is_invalid_and_cleans_up(database):
    with database.read() as session:
        context = session.stream(SqlStatement("SELECT 1 UNION ALL SELECT 2"))
        rows = context.__enter__()
        assert next(rows)[0] == 1
    with pytest.raises(DatabaseError):
        next(rows)
    context.__exit__(None, None, None)
    assert not session._cursors
