"""Explicit envelope initialization and atomic, code-owned schema registration."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Literal

from .contracts import Database, DatabaseIdentity
from .errors import DatabaseError
from .sqlite import _APPLICATION_ID, _FORMAT_VERSION, SQLiteDriver, _identity, _one

_ENVELOPE = (
    "CREATE TABLE pf_store_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),store_id TEXT NOT NULL UNIQUE,scope TEXT NOT NULL CHECK(scope IN ('project','workplace')),owner_id TEXT NOT NULL,format_version INTEGER NOT NULL CHECK(format_version=1))",
    "CREATE TABLE pf_schema_versions(namespace TEXT PRIMARY KEY,version INTEGER NOT NULL CHECK(version>=1),checksum TEXT NOT NULL)",
)


@dataclass(frozen=True)
class SchemaDefinition:
    """Immutable namespace DDL and SHA256 of its canonical JSON definition."""

    namespace: str
    version: int
    statements: tuple[str, ...]
    checksum: str

    def __post_init__(self) -> None:
        if (
            type(self.namespace) is not str
            or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.namespace) is None
            or type(self.version) is not int
            or self.version < 1
            or type(self.statements) is not tuple
            or any(
                type(text) is not str or not text.strip() for text in self.statements
            )
        ):
            raise DatabaseError("database_schema_unsupported")
        body = json.dumps(
            {
                "namespace": self.namespace,
                "version": self.version,
                "statements": self.statements,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if self.checksum != "sha256:" + hashlib.sha256(body).hexdigest():
            raise DatabaseError("database_schema_unsupported")


@dataclass(frozen=True)
class SchemaStatus:
    """Noncreating discovery result with concrete identity for existing stores."""

    identity: DatabaseIdentity | None
    state: Literal["missing", "ready", "migration_required", "unsupported"]
    versions: tuple[tuple[str, int, str], ...]


def _requirements(schemas: tuple[SchemaDefinition, ...]) -> None:
    if (
        type(schemas) is not tuple
        or any(not isinstance(schema, SchemaDefinition) for schema in schemas)
        or len({schema.namespace for schema in schemas}) != len(schemas)
    ):
        raise DatabaseError("database_schema_unsupported")


def _status(
    connection: sqlite3.Connection,
    expected: DatabaseIdentity,
    requirements: tuple[SchemaDefinition, ...],
) -> SchemaStatus:
    identity = _identity(connection, expected)
    try:
        cursor = connection.execute(
            "SELECT namespace,version,checksum FROM pf_schema_versions ORDER BY namespace"
        )
        try:
            versions = tuple(tuple(row) for row in cursor)
        finally:
            cursor.close()
    except sqlite3.OperationalError:
        raise DatabaseError("database_corrupt") from None
    for namespace, version, checksum in versions:
        if (
            type(namespace) is not str
            or not namespace
            or type(version) is not int
            or version < 1
            or type(checksum) is not str
            or re.fullmatch(r"sha256:[0-9a-f]{64}", checksum) is None
        ):
            raise DatabaseError("database_corrupt")
    known = {
        namespace: (version, checksum) for namespace, version, checksum in versions
    }
    state: Literal["ready", "migration_required", "unsupported"] = "ready"
    for schema in requirements:
        actual = known.get(schema.namespace)
        if actual is None or actual[0] < schema.version:
            if state != "unsupported":
                state = "migration_required"
        elif actual != (schema.version, schema.checksum):
            state = "unsupported"
    return SchemaStatus(identity, state, versions)


class SchemaManager:
    """Only administrative entry point; existing namespace upgrades are refused."""

    @staticmethod
    def _driver(database: Database) -> SQLiteDriver:
        if not isinstance(database.driver, SQLiteDriver):
            raise DatabaseError("database_capability_unsupported")
        return database.driver

    def inspect(
        self, database: Database, requirements: tuple[SchemaDefinition, ...]
    ) -> SchemaStatus:
        _requirements(requirements)
        driver = self._driver(database)
        if not database.target.path.exists():
            return SchemaStatus(None, "missing", ())
        with driver._admin(
            database.target, mode="ro", timeout_ms=database.timeout_ms
        ) as connection:
            connection.execute("BEGIN").close()
            try:
                return _status(connection, database.target.identity, requirements)
            except DatabaseError as error:
                if error.code == "database_schema_unsupported":
                    return SchemaStatus(None, "unsupported", ())
                raise

    def initialize(
        self, database: Database, schemas: tuple[SchemaDefinition, ...]
    ) -> SchemaStatus:
        _requirements(schemas)
        database._concrete()
        driver = self._driver(database)
        path = database.target.path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb"):
                pass
        except FileExistsError:
            raise DatabaseError("database_foreign") from None
        except OSError:
            raise DatabaseError("database_io_failed") from None
        # A failed initialization leaves an uninitialized, blocked target for explicit repair.
        with driver._admin(
            database.target, mode="rw", timeout_ms=database.timeout_ms
        ) as connection:
            self._wal(connection)
            connection.execute("BEGIN IMMEDIATE").close()
            try:
                connection.execute(f"PRAGMA application_id={_APPLICATION_ID}").close()
                connection.execute(f"PRAGMA user_version={_FORMAT_VERSION}").close()
                for text in _ENVELOPE:
                    connection.execute(text).close()
                identity = database.target.identity
                connection.execute(
                    "INSERT INTO pf_store_meta VALUES(1,?,?,?,1)",
                    (identity.store_id, identity.scope, identity.owner_id),
                ).close()
                self._register(connection, schemas)
                result = _status(connection, identity, schemas)
                connection.commit()
                return result
            finally:
                if connection.in_transaction:
                    connection.rollback()

    def apply(
        self, database: Database, schemas: tuple[SchemaDefinition, ...]
    ) -> SchemaStatus:
        _requirements(schemas)
        database._concrete()
        driver = self._driver(database)
        with driver._admin(
            database.target, mode="rw", timeout_ms=database.timeout_ms
        ) as connection:
            # Reject foreign identities before mutating any persistent pragma.
            _identity(connection, database.target.identity)
            self._wal(connection)
            connection.execute("BEGIN IMMEDIATE").close()
            try:
                before = _status(connection, database.target.identity, schemas)
                known = {
                    namespace: (version, checksum)
                    for namespace, version, checksum in before.versions
                }
                for schema in schemas:
                    if schema.namespace in known and known[schema.namespace] != (
                        schema.version,
                        schema.checksum,
                    ):
                        raise DatabaseError("database_schema_unsupported")
                self._register(
                    connection,
                    tuple(
                        schema for schema in schemas if schema.namespace not in known
                    ),
                )
                result = _status(connection, database.target.identity, schemas)
                connection.commit()
                return result
            finally:
                if connection.in_transaction:
                    connection.rollback()

    @staticmethod
    def _wal(connection: sqlite3.Connection) -> None:
        if _one(connection, "PRAGMA journal_mode=WAL") != ("wal",):
            raise DatabaseError("database_capability_unsupported")

    @staticmethod
    def _register(
        connection: sqlite3.Connection, schemas: tuple[SchemaDefinition, ...]
    ) -> None:
        for schema in schemas:
            for text in schema.statements:
                connection.execute(text).close()
            connection.execute(
                "INSERT INTO pf_schema_versions VALUES(?,?,?)",
                (schema.namespace, schema.version, schema.checksum),
            ).close()
