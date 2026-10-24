"""Operation-local SQLite storage for immutable revisions and current contributions."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from processforge_core.maintenance.contracts import StoreTarget
    from processforge_core.maintenance.storage_migration import StorageMigrationHost


from processforge_core.accounting.model import (
    ActivityInterval,
    Attribution,
    FactKey,
    Provenance,
    QueryFilter,
    SourceCapability,
    SourceCursor,
    TokenCounts,
    UsageRecord,
)
from processforge_core.database import DatabaseFactory, SQLiteDriver
from processforge_core.sqlite_storage import adapter_identity_access, transaction

Fact = UsageRecord | ActivityInterval
Kind = Literal["usage", "activity"]
APPLICATION_ID = 0x50464143
SCHEMA_VERSION = 1
_KEY = "kind, origin_id, source_id, record_id"
_SCHEMA = (
    "CREATE TABLE revisions (kind TEXT NOT NULL, origin_id TEXT NOT NULL, "
    "source_id TEXT NOT NULL, record_id TEXT NOT NULL, revision INTEGER NOT NULL, "
    "payload TEXT NOT NULL, PRIMARY KEY(kind, origin_id, source_id, record_id, revision))",
    "CREATE TABLE current_facts (kind TEXT NOT NULL, origin_id TEXT NOT NULL, "
    "source_id TEXT NOT NULL, record_id TEXT NOT NULL, revision INTEGER NOT NULL, "
    "project_id TEXT, assignment_id TEXT, run_id TEXT, attempt INTEGER, model TEXT, "
    "agent_instance_id TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, "
    "valid INTEGER NOT NULL, PRIMARY KEY(kind, origin_id, source_id, record_id), "
    "FOREIGN KEY(kind, origin_id, source_id, record_id, revision) "
    "REFERENCES revisions(kind, origin_id, source_id, record_id, revision))",
    "CREATE INDEX facts_project_time ON current_facts(project_id, kind, started_at)",
    "CREATE INDEX facts_agent_time ON current_facts(project_id, origin_id, agent_instance_id, started_at)",
    "CREATE TABLE source_cursors (origin_id TEXT NOT NULL, source_id TEXT NOT NULL, "
    "revision INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(origin_id, source_id))",
    "CREATE TABLE source_capabilities (origin_id TEXT NOT NULL, source_id TEXT NOT NULL, "
    "project_id TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL, "
    "PRIMARY KEY(origin_id, source_id, project_id))",
)
_COLUMNS = {
    "revisions": {"kind", "origin_id", "source_id", "record_id", "revision", "payload"},
    "current_facts": {
        "kind",
        "origin_id",
        "source_id",
        "record_id",
        "revision",
        "project_id",
        "assignment_id",
        "run_id",
        "attempt",
        "model",
        "agent_instance_id",
        "started_at",
        "ended_at",
        "valid",
    },
    "source_cursors": {"origin_id", "source_id", "revision", "payload"},
    "source_capabilities": {
        "origin_id",
        "source_id",
        "project_id",
        "observed_at",
        "payload",
    },
}


class AccountingStorageError(RuntimeError):
    """Accounting storage is unavailable; lifecycle operations remain independent."""


class SchemaVersionError(AccountingStorageError):
    """An explicit migration is needed; unknown databases are never rewritten."""


class RevisionConflict(ValueError):
    """One immutable identity/revision was delivered with different contents."""


def timestamp(value: datetime) -> str:
    """Use a fixed-width UTC representation for chronological SQL comparison."""
    return value.isoformat(timespec="microseconds")


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return timestamp(value)
    raise TypeError("unsupported accounting value")


def _encode(value: Fact | SourceCursor | SourceCapability) -> str:
    return json.dumps(
        asdict(value),
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def decode_fact(kind: Kind, payload: str) -> Fact:
    """Revalidate a persisted domain value on retrieval."""
    data = json.loads(payload)
    key = FactKey(**data.pop("key"))
    attribution = Attribution(**data.pop("attribution"))
    provenance = Provenance(**data.pop("provenance"))
    if kind == "usage":
        return UsageRecord(
            key=key,
            attribution=attribution,
            provenance=provenance,
            **{
                **data,
                "tokens": TokenCounts(**data["tokens"]),
                "occurred_at": datetime.fromisoformat(data["occurred_at"]),
            },
        )
    return ActivityInterval(
        key=key,
        attribution=attribution,
        provenance=provenance,
        **{
            **data,
            "start": datetime.fromisoformat(data["start"]),
            "end": datetime.fromisoformat(data["end"]) if data["end"] else None,
        },
    )


class SQLiteAccountingRepository:
    """Own a caller-selected database; each operation closes its own connection."""

    def __init__(
        self,
        path: Path,
        *,
        busy_timeout_ms: int = 1000,
        driver: SQLiteDriver | None = None,
        storage_host: StorageMigrationHost | None = None,
    ) -> None:
        """Initialize only an empty database; reject foreign or unsupported schemas."""
        self.driver = driver if driver is not None else DatabaseFactory.resolve_driver()
        self.storage_host = storage_host
        self.path = Path(path)
        if not self.path.is_absolute():
            raise ValueError("accounting database path must be absolute")
        if type(busy_timeout_ms) is not int or not 0 <= busy_timeout_ms <= 30_000:
            raise ValueError("busy_timeout_ms must be between 0 and 30000")
        self.busy_timeout_ms = busy_timeout_ms
        with self._database(writable=True, initializing=True):
            pass

    def _initialize(
        self, connection: sqlite3.Connection, identity: tuple[StoreTarget, str] | None
    ) -> None:
        with transaction(connection):
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if application_id == 0 and version == 0 and not tables:
                for statement in _SCHEMA:
                    connection.execute(statement)
                connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            if (
                identity is not None
                and not connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='pf_store_meta'"
                ).fetchone()
            ):
                from processforge_core.maintenance.storage_migration import (
                    add_store_identity,
                )

                add_store_identity(connection, *identity)
            self._verify(connection)
        connection.execute("PRAGMA journal_mode = WAL")

    @staticmethod
    def _verify(connection: sqlite3.Connection) -> None:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
            raise SchemaVersionError("accounting_schema_unsupported")
        for table, expected in _COLUMNS.items():
            columns = {
                row[1] for row in connection.execute(f"PRAGMA table_info({table})")
            }
            if columns != expected:
                raise SchemaVersionError("accounting_schema_incomplete")

    @contextmanager
    def _database_unfenced(
        self,
        *,
        writable: bool = False,
        initializing: bool = False,
        identity: tuple[StoreTarget, str] | None = None,
    ) -> Iterator[sqlite3.Connection]:
        if self.path.is_symlink():
            raise AccountingStorageError("accounting_unsafe_path")
        connection: sqlite3.Connection | None = None
        try:
            if writable:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                connection = self.driver._connect(
                    self.path,
                    timeout=self.busy_timeout_ms / 1000,
                    isolation_level=None,
                )
            else:
                connection = self.driver._connect(
                    self.path.as_uri() + "?mode=ro",
                    uri=True,
                    timeout=self.busy_timeout_ms / 1000,
                    isolation_level=None,
                )
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            connection.execute("PRAGMA foreign_keys = ON")
            if writable:
                connection.execute("PRAGMA synchronous = FULL")
            if initializing:
                self._initialize(connection, identity)
            if (
                identity is None
                and connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='pf_store_meta'"
                ).fetchone()
            ):
                raise AccountingStorageError("storage_host_required")
            yield connection
        except sqlite3.Error as exc:
            # SQLite error text may include private paths or submitted payloads.
            code = getattr(exc, "sqlite_errorname", "SQLITE_ERROR")
            raise AccountingStorageError(f"accounting_database_error: {code}") from exc
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def _database(
        self, *, writable: bool = False, initializing: bool = False
    ) -> Iterator[sqlite3.Connection]:
        with adapter_identity_access(
            self.path, self.storage_host, writable=writable
        ) as identity:
            with self._database_unfenced(
                writable=writable, initializing=initializing, identity=identity
            ) as connection:
                yield connection

    @contextmanager
    def snapshot(self) -> Iterator[sqlite3.Connection]:
        """Pin all parts of a query to one SQLite read snapshot."""
        with self._database() as connection:
            connection.execute("BEGIN")
            try:
                self._verify(connection)
                yield connection
            finally:
                connection.execute("ROLLBACK")

    def ingest(
        self,
        usage: Sequence[UsageRecord] = (),
        activity: Sequence[ActivityInterval] = (),
        *,
        cursor: SourceCursor | None = None,
        capabilities: Sequence[SourceCapability] = (),
    ) -> int:
        """Atomically accept revisions and a bounded replay checkpoint.

        Returns:
            Number of new immutable fact revisions, including late history.

        Raises:
            RevisionConflict: A fact/checkpoint has conflicting content.
            ValueError: Batch types, size or cursor source are invalid.
            AccountingStorageError: The transaction cannot be committed.
        """
        if len(usage) + len(activity) > 10_000 or len(capabilities) > 500:
            raise ValueError("batch exceeds bound")
        if any(not isinstance(fact, UsageRecord) for fact in usage):
            raise ValueError("usage batch requires UsageRecord")
        if any(not isinstance(fact, ActivityInterval) for fact in activity):
            raise ValueError("activity batch requires ActivityInterval")
        if any(not isinstance(cap, SourceCapability) for cap in capabilities):
            raise ValueError("capabilities require SourceCapability")
        batches: tuple[tuple[Kind, Sequence[Fact]], ...] = (
            ("usage", usage),
            ("activity", activity),
        )
        if cursor is not None:
            if not isinstance(cursor, SourceCursor):
                raise ValueError("cursor requires SourceCursor")
            if any(
                (fact.key.origin_id, fact.key.source_id)
                != (cursor.origin_id, cursor.source_id)
                for _, facts in batches
                for fact in facts
            ) or any(
                (cap.origin_id, cap.source_id) != (cursor.origin_id, cursor.source_id)
                for cap in capabilities
            ):
                raise ValueError("cursor batch has mixed sources")
        inserted = 0
        with self._database(writable=True) as connection:
            with transaction(connection):
                self._verify(connection)
                for kind, facts in batches:
                    for fact in facts:
                        inserted += self._insert_fact(connection, kind, fact)
                if cursor is not None:
                    self._cursor(connection, cursor)
                for capability in capabilities:
                    self._capability(connection, capability)
        return inserted

    @staticmethod
    def _insert_fact(connection: sqlite3.Connection, kind: Kind, fact: Fact) -> int:
        key = (kind, fact.key.origin_id, fact.key.source_id, fact.key.record_id)
        payload = _encode(fact)
        existing = connection.execute(
            "SELECT payload FROM revisions WHERE kind=? AND origin_id=? "
            "AND source_id=? AND record_id=? AND revision=?",
            (*key, fact.revision),
        ).fetchone()
        if existing is not None:
            if existing[0] != payload:
                raise RevisionConflict("accounting_revision_conflict")
            return 0
        connection.execute(
            f"INSERT INTO revisions({_KEY}, revision, payload) VALUES (?,?,?,?,?,?)",
            (*key, fact.revision, payload),
        )
        attribution = fact.attribution
        start = fact.occurred_at if isinstance(fact, UsageRecord) else fact.start
        end = fact.end if isinstance(fact, ActivityInterval) else None
        # Both observed endpoints bound selection after a backwards UTC jump.
        # These index bounds never become an invented occupied-time span.
        if end is not None:
            start, end = min(start, end), max(start, end)
        connection.execute(
            f"INSERT INTO current_facts({_KEY}, revision, project_id, assignment_id, "
            "run_id, attempt, model, agent_instance_id, started_at, ended_at, valid) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            f"ON CONFLICT({_KEY}) DO UPDATE SET "
            "revision=excluded.revision, project_id=excluded.project_id, "
            "assignment_id=excluded.assignment_id, run_id=excluded.run_id, "
            "attempt=excluded.attempt, model=excluded.model, "
            "agent_instance_id=excluded.agent_instance_id, started_at=excluded.started_at, "
            "ended_at=excluded.ended_at, valid=excluded.valid "
            "WHERE excluded.revision > current_facts.revision",
            (
                *key,
                fact.revision,
                attribution.project_id,
                attribution.assignment_id,
                attribution.run_id,
                attribution.attempt,
                attribution.model,
                attribution.agent_instance_id,
                timestamp(start),
                timestamp(end) if end else None,
                int(fact.valid),
            ),
        )
        return 1

    @staticmethod
    def _cursor(connection: sqlite3.Connection, cursor: SourceCursor) -> None:
        key = (cursor.origin_id, cursor.source_id)
        payload = _encode(cursor)
        existing = connection.execute(
            "SELECT revision, payload FROM source_cursors WHERE origin_id=? AND source_id=?",
            key,
        ).fetchone()
        if existing is not None:
            if existing[0] == cursor.revision and existing[1] != payload:
                raise RevisionConflict("accounting_cursor_conflict")
            if existing[0] >= cursor.revision:
                return
        connection.execute(
            "INSERT INTO source_cursors(origin_id,source_id,revision,payload) VALUES (?,?,?,?) "
            "ON CONFLICT(origin_id,source_id) DO UPDATE SET revision=excluded.revision, "
            "payload=excluded.payload",
            (*key, cursor.revision, payload),
        )

    @staticmethod
    def _capability(
        connection: sqlite3.Connection, capability: SourceCapability
    ) -> None:
        key = (capability.origin_id, capability.source_id, capability.project_id)
        observed_at = timestamp(capability.observed_at)
        payload = _encode(capability)
        existing = connection.execute(
            "SELECT observed_at,payload FROM source_capabilities "
            "WHERE origin_id=? AND source_id=? AND project_id=?",
            key,
        ).fetchone()
        if existing is not None:
            if existing[0] == observed_at and existing[1] != payload:
                raise RevisionConflict("accounting_capability_conflict")
            if existing[0] >= observed_at:
                return
        connection.execute(
            "INSERT INTO source_capabilities(origin_id,source_id,project_id,observed_at,payload) "
            "VALUES (?,?,?,?,?) ON CONFLICT(origin_id,source_id,project_id) DO UPDATE SET "
            "observed_at=excluded.observed_at,payload=excluded.payload",
            (*key, observed_at, payload),
        )

    def get_cursor(self, origin_id: str, source_id: str) -> SourceCursor | None:
        """Read the latest private replay checkpoint without opening source logs."""
        with self.snapshot() as connection:
            row = connection.execute(
                "SELECT payload FROM source_cursors WHERE origin_id=? AND source_id=?",
                (origin_id, source_id),
            ).fetchone()
            if row is None:
                return None
            data = json.loads(row[0])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            return SourceCursor(**data)

    def backup(self, destination: Path) -> None:
        """Create a consistent SQLite backup, refusing to overwrite any existing file."""
        destination = Path(destination)
        if not destination.is_absolute():
            raise ValueError("backup destination must be absolute")
        with destination.open("xb"):
            pass
        try:
            with self.snapshot() as source:
                target = self.driver._connect(destination)
                try:
                    source.backup(target)
                finally:
                    target.close()
        except BaseException:
            destination.unlink(missing_ok=True)
            raise

    @staticmethod
    def where(
        projects: Sequence[str], filters: QueryFilter, kind: Kind
    ) -> tuple[str, list[object]]:
        """Build parameterized predicates; quarantine is never part of project queries."""
        if not projects:
            return "0", []
        conditions = [
            f"c.project_id IN ({','.join('?' for _ in projects)})",
            "c.kind=?",
            "c.valid=1",
        ]
        values: list[object] = [*projects, kind]
        for name in (
            "project_id",
            "assignment_id",
            "run_id",
            "attempt",
            "source_id",
            "model",
        ):
            value = getattr(filters, name)
            if value is not None:
                conditions.append(f"c.{name}=?")
                values.append(value)
        if filters.end is not None:
            conditions.append("c.started_at < ?")
            values.append(timestamp(filters.end))
        if filters.start is not None:
            if kind == "usage":
                conditions.append("c.started_at >= ?")
            else:
                # Unknown open tails are included as partial when they might overlap.
                conditions.append(
                    "(c.ended_at > ? OR c.ended_at IS NULL OR "
                    "(c.ended_at=c.started_at AND c.started_at >= ?))"
                )
                values.append(timestamp(filters.start))
            values.append(timestamp(filters.start))
        return " AND ".join(conditions), values

    @staticmethod
    def facts(
        connection: sqlite3.Connection,
        projects: Sequence[str],
        filters: QueryFilter,
        kind: Kind,
        *,
        order: Literal["identity", "time", "agent"] = "identity",
        page: bool = False,
    ) -> Iterator[Fact]:
        """Stream selected current facts; only detail pages use LIMIT/OFFSET."""
        predicate, values = SQLiteAccountingRepository.where(projects, filters, kind)
        orders = {
            "identity": "c.origin_id,c.source_id,c.record_id",
            "time": "c.started_at,c.origin_id,c.source_id,c.record_id",
            "agent": "c.origin_id,c.agent_instance_id,c.started_at,c.project_id,c.source_id,c.record_id",
        }
        sql = (
            "SELECT r.payload FROM current_facts c JOIN revisions r "
            "USING(kind,origin_id,source_id,record_id,revision) "
            f"WHERE {predicate} ORDER BY {orders[order]}"
        )
        if page:
            sql += " LIMIT ? OFFSET ?"
            values.extend((filters.limit, filters.offset))
        for row in connection.execute(sql, values):
            yield decode_fact(kind, row[0])
