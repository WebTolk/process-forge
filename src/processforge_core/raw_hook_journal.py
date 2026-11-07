"""Project-local raw receipts, optional payload history and pending recovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from .database import SQLiteDriver

if TYPE_CHECKING:
    from .maintenance.storage_migration import StorageMigrationHost
from .sqlite_storage import (
    JournalError,
    JournalMigrationRequired,
    database,
    metadata,
    set_metadata,
    transaction,
)

APPLICATION_ID = 0x50465257
SCHEMA = (
    "CREATE TABLE receipts(seq INTEGER PRIMARY KEY AUTOINCREMENT, raw_event_id TEXT NOT NULL UNIQUE, "
    "native_identity_key TEXT UNIQUE, raw_payload_hash TEXT NOT NULL, provider TEXT NOT NULL, adapter TEXT NOT NULL, "
    "session_id TEXT NOT NULL, project_ref TEXT NOT NULL, received_at TEXT NOT NULL, pending_record TEXT, response TEXT)",
    "CREATE INDEX receipts_session ON receipts(session_id, provider, adapter, seq)",
    "CREATE TABLE raw_events(raw_event_id TEXT PRIMARY KEY, record TEXT NOT NULL)",
    "CREATE TABLE quarantine(seq INTEGER PRIMARY KEY, code TEXT NOT NULL, raw_event_id TEXT NOT NULL, "
    "raw_payload_hash TEXT NOT NULL, existing_raw_event_id TEXT NOT NULL, record TEXT)",
    "CREATE TABLE legacy_locations(location TEXT PRIMARY KEY, raw_event_id TEXT NOT NULL)",
)


def _encode(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _legacy_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    record: dict[str, object] = {}
    for key, value in pairs:
        if key in record:
            raise ValueError("duplicate legacy key")
        record[key] = value
    return record


def _legacy_constant(value: str) -> None:
    raise ValueError("nonfinite legacy value")


class RawHookJournal:
    def __init__(
        self,
        *,
        driver: SQLiteDriver | None = None,
        storage_host: StorageMigrationHost | None = None,
    ) -> None:
        self.driver = driver
        self.storage_host = storage_host

    @staticmethod
    def require_legacy_migration(
        path: Path, *, project_root: Path | None, workplace_root: Path
    ) -> None:
        """Refuse creation when legacy history may belong to this journal.

        Shared history of a positively identified foreign project does not
        belong to a new project-local database. Unknown ownership remains a
        migration requirement; this method never modifies legacy records.
        """
        if path.is_file():
            return
        local = path.parent / "raw/v1"
        shared = workplace_root / "runtime/agent-events/raw/v1"
        required = False
        try:
            required = any(local.rglob("*.ndjson"))
            if not required and shared != local:
                project = project_root.resolve() if project_root is not None else None
                for source in shared.rglob("*.ndjson"):
                    if project is None or source.is_symlink():
                        required = True
                        break
                    with source.open(encoding="utf-8") as stream:
                        for line in stream:
                            if not line.strip():
                                continue
                            record = json.loads(
                                line,
                                object_pairs_hook=_legacy_object,
                                parse_constant=_legacy_constant,
                            )
                            reference = (
                                record.get("source_project_ref")
                                if isinstance(record, dict)
                                else None
                            )
                            if (
                                not isinstance(reference, str)
                                or not Path(reference).is_absolute()
                                or Path(reference).resolve() == project
                            ):
                                required = True
                                break
                    if required:
                        break
        except (OSError, UnicodeError, ValueError, RuntimeError):
            required = True
        if required:
            raise JournalMigrationRequired(
                "raw_journal_migration_required: run tools/migrate-hook-journals.py"
            )

    @staticmethod
    def connection(
        path: Path,
        *,
        writable: bool = False,
        migrating: bool = False,
        driver: SQLiteDriver | None = None,
        storage_host: StorageMigrationHost | None = None,
    ):
        return database(
            path,
            application_id=APPLICATION_ID,
            schema=SCHEMA,
            writable=writable,
            migrating=migrating,
            driver=driver,
            storage_host=storage_host,
        )

    def accept(
        self,
        path: Path,
        record: dict[str, Any],
        *,
        retain_raw: bool = True,
        migrating: bool = False,
        legacy_location: str | None = None,
    ) -> dict[str, Any]:
        with self.connection(
            path,
            writable=True,
            migrating=migrating,
            driver=self.driver,
            storage_host=self.storage_host,
        ) as connection:
            with transaction(connection):
                return self._accept(
                    connection,
                    path,
                    record,
                    retain_raw=retain_raw,
                    legacy_location=legacy_location,
                )

    @staticmethod
    def _accept(connection, path, record, *, retain_raw, legacy_location=None):
        raw_id, digest = record["raw_event_id"], record["raw_payload_hash"]
        native_key = record.get("native_identity_key")
        existing = connection.execute(
            "SELECT seq, raw_event_id, raw_payload_hash FROM receipts WHERE raw_event_id = ?",
            (raw_id,),
        ).fetchone()
        native = (
            connection.execute(
                "SELECT seq, raw_event_id, raw_payload_hash FROM receipts WHERE native_identity_key = ?",
                (native_key,),
            ).fetchone()
            if native_key
            else None
        )
        code = None
        if native is not None and native["raw_payload_hash"] != digest:
            code, prior = "native_id_payload_conflict", native
        elif existing is not None and existing["raw_payload_hash"] != digest:
            code, prior = "raw_event_id_hash_collision", existing
        if code:
            connection.execute(
                "INSERT INTO quarantine(code, raw_event_id, raw_payload_hash, existing_raw_event_id, record) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    code,
                    raw_id,
                    digest,
                    prior["raw_event_id"],
                    _encode(record) if retain_raw else None,
                ),
            )
            return {
                "accepted": False,
                "deduplicated": False,
                "raw_location": None,
                "routing_status": "quarantined",
                "diagnostics": {"code": code},
            }
        if existing is None:
            cursor = connection.execute(
                "INSERT INTO receipts(raw_event_id, native_identity_key, raw_payload_hash, provider, adapter, "
                "session_id, project_ref, received_at, pending_record) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    raw_id,
                    native_key,
                    digest,
                    record["provider"],
                    record["adapter"],
                    str(record.get("source_session_id") or ""),
                    str(record.get("source_project_ref") or ""),
                    record["received_at"],
                    None if retain_raw else _encode(record),
                ),
            )
            sequence = cursor.lastrowid
        else:
            sequence = existing["seq"]
        if retain_raw:
            cursor = connection.execute(
                "INSERT INTO raw_events VALUES (?, ?) ON CONFLICT(raw_event_id) DO NOTHING",
                (raw_id, _encode(record)),
            )
            if cursor.rowcount:
                connection.execute(
                    "UPDATE journal_metadata SET value = CAST(value AS INTEGER) + 1 WHERE key = 'history_count'"
                )
        if legacy_location is not None:
            connection.execute(
                "INSERT INTO legacy_locations VALUES (?, ?) ON CONFLICT(location) DO NOTHING",
                (legacy_location, raw_id),
            )
        return {
            "accepted": True,
            "deduplicated": existing is not None,
            "raw_location": f"{path.name}:{sequence}",
            "routing_status": "duplicate_raw"
            if existing is not None
            else "raw_accepted",
            "diagnostics": {},
        }

    def finish(self, path: Path, raw_event_id: str, response: dict[str, Any]) -> None:
        with self.connection(
            path, writable=True, driver=self.driver, storage_host=self.storage_host
        ) as connection:
            with transaction(connection):
                connection.execute(
                    "UPDATE receipts SET pending_record = NULL, response = ? WHERE raw_event_id = ?",
                    (_encode(response), raw_event_id),
                )

    def result(self, path: Path, raw_event_id: str) -> dict[str, Any] | None:
        try:
            with self.connection(
                path, driver=self.driver, storage_host=self.storage_host
            ) as connection:
                row = connection.execute(
                    "SELECT response FROM receipts WHERE raw_event_id = ?",
                    (raw_event_id,),
                ).fetchone()
                return (
                    json.loads(row[0])
                    if row is not None and row[0] is not None
                    else None
                )
        except FileNotFoundError:
            return None

    def records(
        self,
        path: Path,
        *,
        session_id: str | None = None,
        provider: str | None = None,
        adapter: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        after = 0
        clauses, values = [], []
        for column, value in (
            ("session_id", session_id),
            ("provider", provider),
            ("adapter", adapter),
        ):
            if value is not None:
                clauses.append("r." + column + " = ?")
                values.append(value)
        where = " AND ".join(clauses)
        if where:
            where += " AND "
        while True:
            try:
                with self.connection(
                    path, driver=self.driver, storage_host=self.storage_host
                ) as connection:
                    rows = connection.execute(
                        "SELECT r.seq, COALESCE(h.record, r.pending_record) AS record FROM receipts r "
                        "LEFT JOIN raw_events h ON h.raw_event_id = r.raw_event_id WHERE "
                        + where
                        + "r.seq > ? ORDER BY r.seq LIMIT 1000",
                        (*values, after),
                    ).fetchall()
            except FileNotFoundError:
                return
            if not rows:
                return
            for row in rows:
                if row["record"] is not None:
                    location = f"{path.name}:{row['seq']}"
                    try:
                        record = json.loads(row["record"])
                    except (TypeError, ValueError):
                        yield {"malformed": True, "raw_location": location}
                        return
                    yield {"record": record, "raw_location": location}
            after = rows[-1]["seq"]

    def count(self, path: Path) -> int:
        try:
            with self.connection(
                path, driver=self.driver, storage_host=self.storage_host
            ) as connection:
                return int(metadata(connection, "history_count") or 0)
        except FileNotFoundError:
            return 0

    def finish_migration(self, path: Path) -> None:
        with self.connection(
            path,
            writable=True,
            migrating=True,
            driver=self.driver,
            storage_host=self.storage_host,
        ) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise JournalError("journal_integrity_check_failed")
            with transaction(connection):
                set_metadata(connection, "legacy_imported", "1")
                set_metadata(connection, "migration_state", "ready")
