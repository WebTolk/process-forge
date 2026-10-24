"""SQLite adapter with bounded operations and a private schema admin channel."""

from __future__ import annotations

import math
import sqlite3
import threading
import time
from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, cast

from .contracts import (
    DatabaseCapabilities,
    DatabaseIdentity,
    DatabaseTarget,
    SqlRow,
    SqlSession,
    SqlStatement,
    SqlValue,
    WriteResult,
    _values,
)
from .errors import DatabaseError

_APPLICATION_ID = 0x50464D31
_FORMAT_VERSION = 1


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None:
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise DatabaseError("database_profile_invalid")
        if time.monotonic() >= deadline:
            raise DatabaseError("database_deadline_exceeded")


def _failure(error: sqlite3.Error, deadline: float | None) -> DatabaseError:
    code = getattr(error, "sqlite_errorcode", 0) & 0xFF
    if deadline is not None and time.monotonic() >= deadline:
        return DatabaseError("database_deadline_exceeded")
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return DatabaseError("database_busy", retryable=True)
    if code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
        return DatabaseError("database_corrupt")
    if code == sqlite3.SQLITE_CONSTRAINT or isinstance(
        error, (sqlite3.IntegrityError, sqlite3.ProgrammingError)
    ):
        return DatabaseError("database_constraint_failed")
    return DatabaseError("database_io_failed")


def _one(connection: sqlite3.Connection, text: str) -> tuple:
    cursor = connection.execute(text)
    try:
        return tuple(cursor.fetchone() or ())
    finally:
        cursor.close()


def _identity(
    connection: sqlite3.Connection, expected: DatabaseIdentity
) -> DatabaseIdentity:
    if _one(connection, "PRAGMA application_id") != (_APPLICATION_ID,):
        raise DatabaseError("database_foreign")
    if _one(connection, "PRAGMA user_version") != (_FORMAT_VERSION,):
        raise DatabaseError("database_schema_unsupported")
    try:
        cursor = connection.execute(
            "SELECT singleton,store_id,scope,owner_id,format_version FROM pf_store_meta"
        )
        try:
            rows = cursor.fetchmany(2)
        finally:
            cursor.close()
        if len(rows) != 1 or rows[0][0] != 1 or rows[0][4] != _FORMAT_VERSION:
            raise DatabaseError("database_corrupt")
        actual = DatabaseIdentity(rows[0][1], rows[0][2], rows[0][3])
        if actual.store_id is None:
            raise DatabaseError("database_corrupt")
        if (actual.scope, actual.owner_id) != (
            expected.scope,
            expected.owner_id,
        ) or expected.store_id not in (None, actual.store_id):
            raise DatabaseError("database_foreign")
        return actual
    except sqlite3.OperationalError:
        raise DatabaseError("database_corrupt") from None


_DENIED = {
    sqlite3.SQLITE_PRAGMA,
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_TRANSACTION,
    sqlite3.SQLITE_SAVEPOINT,
    sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX,
    sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
    sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_CREATE_VTABLE,
    sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX,
    sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER,
    sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_DROP_VTABLE,
    sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_REINDEX,
    sqlite3.SQLITE_ANALYZE,
}


def _authorize(
    action: int,
    first: str | None,
    second: str | None,
    db: str | None,
    source: str | None,
) -> int:
    if action in _DENIED:
        return sqlite3.SQLITE_DENY
    if action in (
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
    ) and first in ("pf_store_meta", "pf_schema_versions"):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


class _SQLiteSession:
    def __init__(
        self, connection: sqlite3.Connection, deadline: float | None, timeout_ms: int
    ) -> None:
        self._connection = connection
        self._deadline = deadline
        self._thread = threading.get_ident()
        self._active = True
        self._timeout_ms = timeout_ms
        self._budget: int | None = None
        self._cursors: set[sqlite3.Cursor] = set()

    def _check(self) -> None:
        if not self._active or self._thread != threading.get_ident():
            raise DatabaseError("database_io_failed")
        _check_deadline(self._deadline)
        if self._deadline is not None:
            budget = min(
                self._timeout_ms,
                max(0, int((self._deadline - time.monotonic()) * 1000)),
            )
            if budget != self._budget:
                self._connection.set_authorizer(None)
                try:
                    self._connection.execute(f"PRAGMA busy_timeout={budget}").close()
                    self._budget = budget
                finally:
                    self._connection.set_authorizer(_authorize)

    def _row(self, cursor: sqlite3.Cursor, row: tuple) -> SqlRow:
        return SqlRow(tuple(item[0] for item in cursor.description or ()), tuple(row))

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        self._check()
        cursor = self._connection.cursor()
        self._cursors.add(cursor)
        try:
            yield cursor
        except sqlite3.Error as error:
            raise _failure(error, self._deadline) from None
        finally:
            if cursor in self._cursors:
                self._cursors.discard(cursor)
                cursor.close()

    def fetch_one(self, statement: SqlStatement) -> SqlRow | None:
        with self._cursor() as cursor:
            cursor.execute(statement.text, statement.params)
            row = cursor.fetchone()
            self._check()
            return None if row is None else self._row(cursor, row)

    @contextmanager
    def stream(
        self, statement: SqlStatement, *, batch_size: int = 256
    ) -> Iterator[Iterator[SqlRow]]:
        if type(batch_size) is not int or not 1 <= batch_size <= 1000:
            raise DatabaseError("database_constraint_failed")
        with self._cursor() as cursor:
            cursor.execute(statement.text, statement.params)

            def rows() -> Generator[SqlRow, None, None]:
                while True:
                    self._check()
                    try:
                        batch = cursor.fetchmany(batch_size)
                    except sqlite3.Error as error:
                        raise _failure(error, self._deadline) from None
                    if not batch:
                        return
                    for row in batch:
                        self._check()
                        yield self._row(cursor, row)

            iterator = rows()
            try:
                yield iterator
            finally:
                iterator.close()

    def execute(self, statement: SqlStatement) -> WriteResult:
        with self._cursor() as cursor:
            cursor.execute(statement.text, statement.params)
            self._check()
            return WriteResult(
                None if cursor.rowcount < 0 else cursor.rowcount, cursor.lastrowid
            )

    def execute_many(
        self, statement: SqlStatement, rows: Sequence[tuple[SqlValue, ...]]
    ) -> WriteResult:
        if statement.params or len(rows) > 10000:
            raise DatabaseError("database_constraint_failed")
        for row in rows:
            _values(row)
        with self._cursor() as cursor:
            cursor.executemany(statement.text, rows)
            self._check()
            return WriteResult(None if cursor.rowcount < 0 else cursor.rowcount, None)

    def _close(self) -> None:
        self._active = False
        for cursor in tuple(self._cursors):
            cursor.close()
        self._cursors.clear()


class SQLiteDriver:
    """Cold SQLite driver; schema creation is available only through SchemaManager."""

    capabilities = DatabaseCapabilities(True, True, True, True, True)

    def _connect(
        self,
        database: str | Path,
        *,
        timeout: float = 5.0,
        isolation_level: str | None = "",
        uri: bool = False,
    ) -> sqlite3.Connection:
        """Native transport only; the caller owns policy, errors and lifetime."""
        # Typeshed narrows this argument, omitting native's valid empty string.
        # Keep native validation and exact caller bytes (including case).
        level = cast(
            Literal["DEFERRED", "EXCLUSIVE", "IMMEDIATE"] | None, isolation_level
        )
        return sqlite3.connect(
            database, timeout=timeout, isolation_level=level, uri=uri
        )

    @contextmanager
    def _admin(
        self,
        target: DatabaseTarget,
        *,
        mode: Literal["ro", "rw"],
        timeout_ms: int,
        deadline: float | None = None,
    ) -> Iterator[sqlite3.Connection]:
        _check_deadline(deadline)
        if type(timeout_ms) is not int or not 0 <= timeout_ms <= 30000:
            raise DatabaseError("database_profile_invalid")
        if not target.path.is_file():
            raise DatabaseError("database_missing")
        budget = (
            timeout_ms
            if deadline is None
            else min(timeout_ms, max(0, int((deadline - time.monotonic()) * 1000)))
        )
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect(
                target.path.as_uri() + "?mode=" + mode,
                uri=True,
                timeout=budget / 1000,
                isolation_level=None,
            )
            connection.set_progress_handler(
                lambda: int(deadline is not None and time.monotonic() >= deadline), 100
            )
            connection.execute("PRAGMA foreign_keys=ON").close()
            if mode == "rw":
                connection.execute("PRAGMA synchronous=FULL").close()
            if _one(connection, "PRAGMA foreign_keys") != (1,):
                raise DatabaseError("database_capability_unsupported")
            if mode == "rw" and _one(connection, "PRAGMA synchronous") != (2,):
                raise DatabaseError("database_capability_unsupported")
            _check_deadline(deadline)
            yield connection
        except sqlite3.Error as error:
            raise _failure(error, deadline) from None
        except OSError:
            raise DatabaseError("database_io_failed") from None
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def open(
        self,
        target: DatabaseTarget,
        *,
        mode: Literal["ro", "rw", "create"],
        timeout_ms: int,
        deadline: float | None = None,
    ) -> Iterator[SqlSession]:
        if mode not in ("ro", "rw"):
            raise DatabaseError("database_capability_unsupported")
        if target.identity.store_id is None:
            raise DatabaseError("database_foreign")
        with self._admin(
            target, mode=mode, timeout_ms=timeout_ms, deadline=deadline
        ) as connection:
            session: _SQLiteSession | None = None
            try:
                connection.execute(
                    "BEGIN" if mode == "ro" else "BEGIN IMMEDIATE"
                ).close()
                _identity(connection, target.identity)
                if _one(connection, "PRAGMA journal_mode") != ("wal",):
                    raise DatabaseError("database_capability_unsupported")
                session = _SQLiteSession(connection, deadline, timeout_ms)
                connection.set_authorizer(_authorize)
                yield session
                session._check()
                session._close()
                connection.set_authorizer(None)
                if mode == "rw":
                    connection.commit()
            finally:
                if session is not None:
                    session._close()
                connection.set_authorizer(None)
                if connection.in_transaction:
                    connection.rollback()
