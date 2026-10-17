"""Indexed project events, optional history, and required verification state."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
import hashlib
import json
from pathlib import Path
from typing import Any

from .sqlite_storage import JournalError, database, metadata, set_metadata, transaction


APPLICATION_ID = 0x50464556
SCHEMA = (
    "CREATE TABLE admissions(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL)",
    "CREATE TABLE events(seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, event_type TEXT NOT NULL, "
    "assignment_id TEXT NOT NULL, subject TEXT NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL, "
    "time TEXT NOT NULL, record TEXT NOT NULL)",
    "CREATE INDEX events_assignment_type ON events(assignment_id, event_type, seq)",
    "CREATE INDEX events_subject_type ON events(subject, event_type, seq)",
    "CREATE INDEX events_session ON events(session_id, seq)",
    "CREATE INDEX events_run ON events(run_id, seq)",
    "CREATE INDEX events_type ON events(event_type, seq)",
    "CREATE TABLE verification_state(assignment_id TEXT NOT NULL, event_type TEXT NOT NULL, "
    "subject TEXT NOT NULL, seq INTEGER NOT NULL, record TEXT NOT NULL, PRIMARY KEY(assignment_id, event_type))",
    "CREATE INDEX verification_subject_type ON verification_state(subject, event_type, seq)",
    "CREATE TABLE pending_dispatch(event_id TEXT PRIMARY KEY, seq INTEGER NOT NULL, record TEXT NOT NULL)",
    "CREATE INDEX pending_dispatch_sequence ON pending_dispatch(seq)",
)


def _identifier(event: dict[str, Any]) -> str:
    return str(event.get("event_id") or event.get("id") or "")


class ProcessEventJournal:
    """Commit each admission before the caller dispatches project effects.

    With history disabled only minimal IDs and latest verification facts are
    retained, so retries and Work readiness remain independent of logging.
    """

    @staticmethod
    def connection(path: Path, *, writable: bool = False, migrating: bool = False):
        return database(path, application_id=APPLICATION_ID, schema=SCHEMA,
                        writable=writable, migrating=migrating, legacy_path=path.with_suffix(".ndjson"))

    def append(
        self, path: Path, event: dict[str, Any], *,
        event_id_value: Callable[[dict[str, Any]], str] = _identifier,
        record: bool = True, queue_dispatch: bool = False,
    ) -> bool:
        return bool(self.append_many(path, (event,), event_id_value=event_id_value,
                                     record=record, queue_dispatch=queue_dispatch))

    def append_many(
        self, path: Path, events: Iterable[dict[str, Any]], *,
        event_id_value: Callable[[dict[str, Any]], str] = _identifier,
        record: bool = True, migrating: bool = False, queue_dispatch: bool = False,
    ) -> int:
        with self.connection(path, writable=True, migrating=migrating) as connection:
            with transaction(connection):
                return sum(self._append(connection, event, event_id_value, record, migrating, queue_dispatch) for event in events)

    @staticmethod
    def _append(connection, event, event_id_value, record, migrating=False, queue_dispatch=False) -> bool:
        event_id = event_id_value(event)
        if not isinstance(event_id, str) or not event_id:
            raise JournalError("journal_event_id_required")
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        cursor = connection.execute(
            "INSERT INTO admissions(event_id, payload_hash) VALUES (?, ?) ON CONFLICT(event_id) DO NOTHING",
            (event_id, digest),
        )
        if not cursor.rowcount:
            if migrating:
                old = connection.execute("SELECT payload_hash FROM admissions WHERE event_id = ?", (event_id,)).fetchone()
                if old[0] != digest:
                    raise JournalError("journal_migration_event_id_conflict")
            return False
        sequence = cursor.lastrowid
        assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
        session = event.get("session") if isinstance(event.get("session"), dict) else {}
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        event_type = str(event.get("event_type") or "")
        assignment_id = str(assignment.get("id") or data.get("task_id") or data.get("assignment_id") or "")
        subject = str(event.get("subject") or "")
        if record:
            connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sequence, event_id, event_type, assignment_id, subject, str(session.get("id") or ""),
                 str(data.get("run_id") or ""), str(event.get("time") or ""), encoded),
            )
            connection.execute("UPDATE journal_metadata SET value = CAST(value AS INTEGER) + 1 WHERE key = 'history_count'")
        if "verification_fingerprint" in data:
            connection.execute(
                "INSERT INTO verification_state VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(assignment_id, event_type) DO UPDATE SET subject = excluded.subject, "
                "seq = excluded.seq, record = excluded.record",
                (assignment_id or subject, event_type, subject, sequence, encoded),
            )
            set_metadata(connection, "verification_revision", str(sequence))
        if queue_dispatch:
            connection.execute("INSERT INTO pending_dispatch VALUES (?, ?, ?)", (event_id, sequence, encoded))
        return True

    def pending_dispatch(self, path: Path, *, event_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("journal_limit_invalid")
        try:
            with self.connection(path) as connection:
                if event_id is None:
                    rows = connection.execute("SELECT record FROM pending_dispatch ORDER BY seq LIMIT ?", (limit,)).fetchall()
                else:
                    rows = connection.execute("SELECT record FROM pending_dispatch WHERE event_id = ?", (event_id,)).fetchall()
                return [json.loads(row[0]) for row in rows]
        except FileNotFoundError:
            return []

    def complete_dispatch(self, path: Path, event_id: str) -> None:
        with self.connection(path, writable=True) as connection:
            with transaction(connection):
                connection.execute("DELETE FROM pending_dispatch WHERE event_id = ?", (event_id,))

    def contains(self, path: Path, event_id: str, *, event_id_value=None) -> bool:
        try:
            with self.connection(path) as connection:
                return connection.execute("SELECT 1 FROM admissions WHERE event_id = ?", (event_id,)).fetchone() is not None
        except FileNotFoundError:
            return False

    def get(self, path: Path, event_id: str) -> dict[str, Any] | None:
        try:
            with self.connection(path) as connection:
                row = connection.execute("SELECT record FROM events WHERE event_id = ?", (event_id,)).fetchone()
                return json.loads(row[0]) if row else None
        except FileNotFoundError:
            return None

    def latest(self, path: Path) -> dict[str, Any] | None:
        try:
            with self.connection(path) as connection:
                row = connection.execute("SELECT record FROM events ORDER BY seq DESC LIMIT 1").fetchone()
                return json.loads(row[0]) if row else None
        except FileNotFoundError:
            return None

    def count(self, path: Path) -> int:
        try:
            with self.connection(path) as connection:
                return int(metadata(connection, "history_count") or 0)
        except FileNotFoundError:
            return 0

    def verification_revision(self, path: Path) -> int:
        try:
            with self.connection(path) as connection:
                return int(metadata(connection, "verification_revision") or 0)
        except FileNotFoundError:
            return 0

    def latest_assignment_event(self, path: Path, assignment_id: str, event_types: set[str]) -> dict[str, Any] | None:
        if not event_types:
            return None
        placeholders = ",".join("?" for _ in event_types)
        values = (assignment_id, *sorted(event_types))
        try:
            with self.connection(path) as connection:
                candidates = []
                for table in ("events", "verification_state"):
                    for column in ("assignment_id", "subject"):
                        row = connection.execute(
                            f"SELECT seq, record FROM {table} WHERE {column} = ? "
                            f"AND event_type IN ({placeholders}) ORDER BY seq DESC LIMIT 1", values,
                        ).fetchone()
                        if row is not None:
                            candidates.append(row)
                return json.loads(max(candidates, key=lambda row: row[0])[1]) if candidates else None
        except FileNotFoundError:
            return None

    def page(
        self, path: Path, *, after: int = 0, limit: int = 100,
        session_id: str | None = None, run_id: str | None = None,
        event_type: str | None = None,
    ) -> list[tuple[int, dict[str, Any]]]:
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("journal_cursor_or_limit_invalid")
        clauses, values = ["seq > ?"], [after]
        for column, value in (("session_id", session_id), ("run_id", run_id), ("event_type", event_type)):
            if value is not None:
                clauses.append(column + " = ?")
                values.append(value)
        try:
            with self.connection(path) as connection:
                rows = connection.execute(
                    "SELECT seq, record FROM events WHERE " + " AND ".join(clauses) + " ORDER BY seq LIMIT ?",
                    (*values, limit),
                ).fetchall()
                return [(row[0], json.loads(row[1])) for row in rows]
        except FileNotFoundError:
            return []

    def records(self, path: Path) -> Iterator[tuple[int, Any, str | None]]:
        """Explicit export/doctor iterator, with connections closed per page."""
        after = 0
        while True:
            try:
                with self.connection(path) as connection:
                    rows = connection.execute("SELECT seq, record FROM events WHERE seq > ? ORDER BY seq LIMIT 1000", (after,)).fetchall()
            except FileNotFoundError:
                return
            if not rows:
                return
            for sequence, encoded in rows:
                try:
                    event = json.loads(encoded)
                except (TypeError, ValueError) as exc:
                    yield sequence, None, str(exc)
                else:
                    yield sequence, event, None
            after = rows[-1][0]

    def finish_migration(self, path: Path) -> None:
        with self.connection(path, writable=True, migrating=True) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise JournalError("journal_integrity_check_failed")
            with transaction(connection):
                set_metadata(connection, "legacy_imported", "1")
                set_metadata(connection, "migration_state", "ready")
