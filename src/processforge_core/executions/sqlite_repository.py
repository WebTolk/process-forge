"""Project-scoped execution adapter using only the public synchronous SQL API."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, replace
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, cast

from ..database import (
    Database,
    DatabaseError,
    SqlRow,
    SqlSession,
    SqlStatement,
    SqlValue,
)
from .model import (
    CurrentSnapshot,
    ExecutionError,
    ExecutionKey,
    ExecutionObservation,
    ExecutionRecord,
    HistoryPage,
    ProcessIdentity,
    StorageReadiness,
)
from .projection import canonical_json, compatibility_payload, with_projection
from .schema import EXECUTION_SCHEMA
from .service import apply_evidence

_COLUMNS = (
    "project_id,run_id,task_id,attempt,launch_token,revision,generation,phase,"
    "outcome,collection,process_json,history_seq,payload_json,projected_revision"
)
_KEY = "project_id=? AND run_id=? AND task_id=? AND attempt=?"
_CURRENT_PHASES = frozenset({"starting", "running", "stopping", "unresolved"})
CURRENT_SQL = (
    "SELECT "
    + ",".join("a." + column for column in _COLUMNS.split(","))
    + " FROM execution_current c CROSS JOIN execution_attempts a "
    "ON a.project_id=c.project_id AND a.run_id=c.run_id AND a.task_id=c.task_id "
    "AND a.attempt=c.attempt WHERE c.project_id=? "
    "ORDER BY c.run_id,c.task_id,c.attempt LIMIT ?"
)


def _integer(value: SqlValue) -> int:
    if type(value) is not int:
        raise DatabaseError("database_corrupt")
    return value


def _text(value: SqlValue) -> str:
    if not isinstance(value, str):
        raise DatabaseError("database_corrupt")
    return value


def _optional_text(value: SqlValue) -> str | None:
    return None if value is None else _text(value)


def _record(row: SqlRow) -> ExecutionRecord:
    try:
        process_json = _optional_text(row["process_json"])
        process = (
            None
            if process_json is None
            else ProcessIdentity(**json.loads(process_json))
        )
        record = ExecutionRecord(
            ExecutionKey(
                _text(row["project_id"]),
                _text(row["run_id"]),
                _text(row["task_id"]),
                _integer(row["attempt"]),
            ),
            _optional_text(row["launch_token"]),
            _integer(row["revision"]),
            _integer(row["generation"]),
            cast(
                Literal[
                    "prepared",
                    "starting",
                    "running",
                    "stopping",
                    "unresolved",
                    "absent",
                ],
                _text(row["phase"]),
            ),
            _optional_text(row["outcome"]),
            cast(
                Literal["pending", "collected", "failed", "refused"],
                _text(row["collection"]),
            ),
            process,
            None if row["history_seq"] is None else _integer(row["history_seq"]),
            _text(row["payload_json"]),
            _integer(row["projected_revision"]),
        )
        payload = compatibility_payload(record.payload_json, record.key)
        if record.payload_json != canonical_json(payload) or (
            process is not None and process_json != canonical_json(asdict(process))
        ):
            raise ValueError("noncanonical execution record")
        return record
    except (ValueError, TypeError, KeyError):
        raise DatabaseError("database_corrupt") from None


def _values(record: ExecutionRecord) -> tuple[SqlValue, ...]:
    return (
        *_key_values(record.key),
        record.launch_token,
        record.revision,
        record.generation,
        record.phase,
        record.outcome,
        record.collection,
        None if record.process is None else canonical_json(asdict(record.process)),
        record.history_seq,
        record.payload_json,
        record.projected_revision,
    )


def _key_values(key: ExecutionKey) -> tuple[SqlValue, ...]:
    return key.project_id, key.run_id, key.task_id, key.attempt


def _limit(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 1000:
        raise ValueError("invalid limit")


class SQLiteExecutionRepository:
    """Maintain heads/current/history atomically; construction performs no I/O."""

    def __init__(self, database: Database, project_id: str) -> None:
        ExecutionKey(project_id, "validation", "validation", 1)
        if (
            database.target.identity.scope != "project"
            or database.target.identity.owner_id != project_id
        ):
            raise ExecutionError("execution_identity_conflict")
        capabilities = database.driver.capabilities
        if not all(
            (
                capabilities.transactions,
                capabilities.read_snapshots,
                capabilities.foreign_keys,
                capabilities.transactional_ddl,
            )
        ):
            raise DatabaseError("database_capability_unsupported")
        self.database = database
        self.project_id = project_id

    def _key(self, key: ExecutionKey) -> None:
        if key.project_id != self.project_id:
            raise ExecutionError("execution_identity_conflict")

    def _state(self, session: SqlSession) -> SqlRow:
        schema = session.fetch_one(
            SqlStatement(
                "SELECT version,checksum FROM pf_schema_versions WHERE namespace=?",
                ("execution",),
            )
        )
        if schema is None:
            raise DatabaseError("database_migration_required")
        if (
            schema["version"] != EXECUTION_SCHEMA.version
            or schema["checksum"] != EXECUTION_SCHEMA.checksum
        ):
            raise DatabaseError("database_schema_unsupported")
        state = session.fetch_one(
            SqlStatement("SELECT * FROM execution_state WHERE singleton=1")
        )
        if state is None:
            raise ExecutionError("execution_storage_not_ready")
        if state["project_id"] != self.project_id:
            raise ExecutionError("execution_identity_conflict")
        return state

    def _readiness(self, state: SqlRow) -> StorageReadiness:
        authority = _text(state["authority"])
        coverage = _text(state["active_coverage"])
        if authority not in {"sql", "legacy"} or coverage not in {
            "complete",
            "unknown",
        }:
            raise DatabaseError("database_corrupt")
        ready = authority == "sql" and state["readiness"] == "ready"
        return StorageReadiness(
            cast(Literal["sql", "legacy"], authority),
            ready,
            cast(Literal["complete", "unknown"], coverage),
            _integer(state["generation"]),
            self.database.target.identity.store_id,
            None if ready else "execution_storage_not_ready",
        )

    def _writable(self, session: SqlSession, generation: int) -> SqlRow:
        state = self._state(session)
        if not self._readiness(state).ready:
            raise ExecutionError("execution_storage_not_ready")
        if type(generation) is not int or state["generation"] != generation:
            raise ExecutionError("stale_generation")
        return state

    def _load(self, session: SqlSession, key: ExecutionKey) -> ExecutionRecord | None:
        self._key(key)
        row = session.fetch_one(
            SqlStatement(
                "SELECT " + _COLUMNS + " FROM execution_attempts WHERE " + _KEY,
                _key_values(key),
            )
        )
        return None if row is None else _record(row)

    def _cas(
        self,
        session: SqlSession,
        key: ExecutionKey,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        record = self._load(session, key)
        if record is None:
            raise ExecutionError("execution_identity_conflict")
        if type(expected_revision) is not int or record.revision != expected_revision:
            raise ExecutionError("stale_revision")
        if record.generation != generation:
            raise ExecutionError("stale_generation")
        return record

    def _save(self, session: SqlSession, record: ExecutionRecord) -> ExecutionRecord:
        record = with_projection(record)
        values = _values(record)
        session.execute(
            SqlStatement(
                "UPDATE execution_attempts SET "
                + ",".join(name + "=?" for name in _COLUMNS.split(",")[4:])
                + " WHERE "
                + _KEY,
                values[4:] + values[:4],
            )
        )
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET revision=revision+1 WHERE singleton=1 AND project_id=?",
                (self.project_id,),
            )
        )
        session.execute(
            SqlStatement(
                "UPDATE execution_heads SET projection_dirty=1 WHERE project_id=? AND run_id=? AND task_id=? AND latest_attempt=?",
                _key_values(record.key),
            )
        )
        if record.phase in _CURRENT_PHASES:
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_current(project_id,run_id,task_id,attempt) VALUES(?,?,?,?) ON CONFLICT(project_id,run_id,task_id,attempt) DO NOTHING",
                    _key_values(record.key),
                )
            )
        else:
            session.execute(
                SqlStatement(
                    "DELETE FROM execution_current WHERE " + _KEY,
                    _key_values(record.key),
                )
            )
        return record

    def readiness(self, *, deadline: float | None = None) -> StorageReadiness:
        """Read readiness without creation; storage failures remain explicit unknown."""
        try:
            with self.database.read(deadline=deadline) as session:
                return self._readiness(self._state(session))
        except (DatabaseError, ExecutionError) as error:
            return StorageReadiness(
                "sql",
                False,
                "unknown",
                0,
                self.database.target.identity.store_id,
                error.code,
            )

    def load(self, key: ExecutionKey) -> ExecutionRecord | None:
        """Load an exact attempt; never redirect old evidence to the head."""
        with self.database.read() as session:
            self._require_ready(session)
            return self._load(session, key)

    def _require_ready(self, session: SqlSession) -> SqlRow:
        state = self._state(session)
        if not self._readiness(state).ready:
            raise ExecutionError("execution_storage_not_ready")
        return state

    def load_latest(self, run_id: str, task_id: str) -> ExecutionRecord | None:
        """Resolve only the indexed head and its primary-key attempt."""
        ExecutionKey(self.project_id, run_id, task_id, 1)
        with self.database.read() as session:
            self._require_ready(session)
            head = session.fetch_one(
                SqlStatement(
                    "SELECT latest_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    (self.project_id, run_id, task_id),
                )
            )
            return (
                None
                if head is None
                else self._load(
                    session,
                    ExecutionKey(self.project_id, run_id, task_id, _integer(head[0])),
                )
            )

    def allocate_attempt(
        self, run_id: str, task_id: str, payload_json: str, *, generation: int
    ) -> ExecutionRecord:
        """Allocate under BEGIN IMMEDIATE without enumerating attempt directories.

        Validate the caller's complete DTO, then replace its attempt with the
        allocated head value. Callers need not guess migration directory floors.
        """
        ExecutionKey(self.project_id, run_id, task_id, 1)
        raw_payload = json.loads(payload_json)
        if not isinstance(raw_payload, dict):
            raise ValueError("invalid compatibility payload")
        requested_attempt = raw_payload.get("attempt")
        if type(requested_attempt) is not int:
            raise ValueError("invalid compatibility payload")
        payload = compatibility_payload(
            payload_json,
            ExecutionKey(self.project_id, run_id, task_id, requested_attempt),
        )
        with self.database.transaction() as session:
            state = self._writable(session, generation)
            if state["active_coverage"] != "complete":
                raise ExecutionError("execution_activity_unknown")
            task = (self.project_id, run_id, task_id)
            current = session.fetch_one(
                SqlStatement(
                    "SELECT attempt FROM execution_current WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            if current is not None:
                raise ExecutionError("execution_activity_unknown")
            head = session.fetch_one(
                SqlStatement(
                    "SELECT next_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            floor = session.fetch_one(
                SqlStatement(
                    "SELECT next_attempt FROM execution_allocation_floors WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            attempt = max(
                1 if head is None else _integer(head[0]),
                1 if floor is None else _integer(floor[0]),
            )
            key = ExecutionKey(self.project_id, run_id, task_id, attempt)
            payload["attempt"] = attempt
            record = with_projection(
                ExecutionRecord(
                    key,
                    None,
                    1,
                    generation,
                    "prepared",
                    None,
                    "pending",
                    None,
                    None,
                    canonical_json(payload),
                    0,
                )
            )
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_attempts("
                    + _COLUMNS
                    + ") VALUES("
                    + ",".join("?" for _ in range(14))
                    + ")",
                    _values(record),
                )
            )
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_heads(project_id,run_id,task_id,latest_attempt,next_attempt,projection_dirty) VALUES(?,?,?,?,?,1) ON CONFLICT(project_id,run_id,task_id) DO UPDATE SET latest_attempt=excluded.latest_attempt,next_attempt=excluded.next_attempt,projection_dirty=1",
                    (*task, attempt, attempt + 1),
                )
            )
            session.execute(
                SqlStatement(
                    "DELETE FROM execution_allocation_floors WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            session.execute(
                SqlStatement(
                    "UPDATE execution_state SET revision=revision+1 WHERE singleton=1 AND project_id=?",
                    (self.project_id,),
                )
            )
            return record

    def _finalize_prepared(
        self, allocated: ExecutionRecord, payload_json: str
    ) -> ExecutionRecord:
        """Finalize attempt-local references after immutable preparation I/O.

        This owner-private transition never manufactures physical execution.
        A failed preparation remains planned and consumes its allocated number.
        """
        payload = compatibility_payload(payload_json, allocated.key)
        if payload["status"] not in {"ready", "manual_required", "blocked"} or any(
            payload[field] is not None
            for field in (
                "pid",
                "started_at",
                "finished_at",
                "exit_code",
                "last_heartbeat_at",
            )
        ):
            raise ValueError("invalid prepared payload")
        with self.database.transaction() as session:
            state = self._writable(session, allocated.generation)
            record = self._cas(
                session, allocated.key, allocated.revision, allocated.generation
            )
            head = session.fetch_one(
                SqlStatement(
                    "SELECT latest_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    (record.key.project_id, record.key.run_id, record.key.task_id),
                )
            )
            if (
                state["active_coverage"] != "complete"
                or record.phase != "prepared"
                or record.launch_token is not None
                or record.collection != "pending"
                or compatibility_payload(record.payload_json, record.key)["status"]
                != "planned"
                or head is None
                or head[0] != record.key.attempt
            ):
                raise ExecutionError("execution_activity_unknown")
            return self._save(
                session,
                replace(
                    record,
                    revision=record.revision + 1,
                    payload_json=canonical_json(payload),
                ),
            )

    def _update_unlaunched(
        self,
        expected: ExecutionRecord,
        *,
        status: Literal["blocked", "cancelled"],
        reason: str,
        finished_at: str | None = None,
    ) -> ExecutionRecord:
        """Block/cancel preparation without inventing a launch or history row."""
        with self.database.transaction() as session:
            self._writable(session, expected.generation)
            record = self._cas(
                session, expected.key, expected.revision, expected.generation
            )
            payload = compatibility_payload(record.payload_json, record.key)
            if (
                record.phase != "prepared"
                or record.launch_token is not None
                or record.process is not None
                or record.collection != "pending"
                or payload["status"]
                not in {"planned", "ready", "manual_required", "blocked"}
            ):
                raise ExecutionError("execution_activity_unknown")
            payload.update(
                status=status, failure_reason=reason, finished_at=finished_at
            )
            return self._save(
                session,
                replace(
                    record,
                    revision=record.revision + 1,
                    payload_json=canonical_json(payload),
                ),
            )

    def _collect_manual(
        self,
        expected: ExecutionRecord,
        collection: Literal["collected", "failed", "refused"],
        *,
        failure_reason: str | None = None,
    ) -> ExecutionRecord:
        """Record manual delivery independently of physical execution/history."""
        if collection not in {"collected", "failed", "refused"}:
            raise ValueError("invalid collection")
        with self.database.transaction() as session:
            self._writable(session, expected.generation)
            record = self._cas(
                session, expected.key, expected.revision, expected.generation
            )
            payload = compatibility_payload(record.payload_json, record.key)
            if (
                record.phase != "prepared"
                or record.launch_token is not None
                or record.process is not None
                or payload["status"] != "manual_required"
            ):
                raise ExecutionError("execution_activity_unknown")
            if failure_reason is not None:
                payload["failure_reason"] = failure_reason
            return self._save(
                session,
                replace(
                    record,
                    collection=collection,
                    revision=record.revision + 1,
                    payload_json=canonical_json(payload),
                ),
            )

    def _launch_paths(
        self,
        expected: ExecutionRecord,
        *,
        heartbeat_path: str,
        stdout_path: str,
        stderr_path: str,
    ) -> ExecutionRecord:
        """Capture native attempt paths for an older immutable prepared input.

        Only transport references change. The prepared reference, grants and
        bytes remain unchanged; the host validates paths before this CAS.
        """
        with self.database.transaction() as session:
            self._writable(session, expected.generation)
            record = self._cas(
                session, expected.key, expected.revision, expected.generation
            )
            payload = compatibility_payload(record.payload_json, record.key)
            if (
                record.phase != "prepared"
                or record.launch_token is not None
                or record.collection != "pending"
                or payload["status"] != "ready"
            ):
                raise ExecutionError("execution_activity_unknown")
            refs = dict(
                heartbeat_path=heartbeat_path,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            if all(payload[name] == value for name, value in refs.items()):
                return record
            payload.update(refs)
            return self._save(
                session,
                replace(
                    record,
                    revision=record.revision + 1,
                    payload_json=canonical_json(payload),
                ),
            )

    def reserve_start(
        self,
        key: ExecutionKey,
        *,
        expected_revision: int,
        generation: int,
        launch_token: str,
    ) -> ExecutionRecord:
        """Reserve current ownership durably before any caller launches a process."""
        with self.database.transaction() as session:
            state = self._writable(session, generation)
            if state["active_coverage"] != "complete":
                raise ExecutionError("execution_activity_unknown")
            record = self._cas(session, key, expected_revision, generation)
            head = session.fetch_one(
                SqlStatement(
                    "SELECT latest_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    (key.project_id, key.run_id, key.task_id),
                )
            )
            current = session.fetch_one(
                SqlStatement(
                    "SELECT attempt FROM execution_current WHERE project_id=? AND run_id=? AND task_id=?",
                    (key.project_id, key.run_id, key.task_id),
                )
            )
            if (
                record.phase != "prepared"
                or compatibility_payload(record.payload_json, record.key)["status"]
                != "ready"
                or record.collection != "pending"
                or head is None
                or head[0] != key.attempt
                or current is not None
            ):
                raise ExecutionError("execution_activity_unknown")
            if (
                session.fetch_one(
                    SqlStatement(
                        "SELECT attempt FROM execution_attempts WHERE launch_token=?",
                        (launch_token,),
                    )
                )
                is not None
            ):
                raise ExecutionError("execution_identity_conflict")
            return self._save(
                session,
                replace(
                    record,
                    launch_token=launch_token,
                    phase="starting",
                    revision=record.revision + 1,
                ),
            )

    def apply_observation(
        self,
        observation: ExecutionObservation,
        *,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Admit latest per-kind receipts; duplicate/lower sequences are no-ops."""
        self._key(observation.key)
        with self.database.transaction() as session:
            state = self._writable(session, generation)
            record = self._load(session, observation.key)
            if record is None or record.launch_token != observation.launch_token:
                raise ExecutionError("execution_identity_conflict")
            if record.generation != generation:
                raise ExecutionError("stale_generation")
            receipt_key = (
                *_key_values(observation.key),
                observation.launch_token,
                observation.receipt_kind,
            )
            prior = session.fetch_one(
                SqlStatement(
                    "SELECT sequence,checksum FROM execution_receipt_admissions WHERE "
                    + _KEY
                    + " AND launch_token=? AND kind=?",
                    receipt_key,
                )
            )
            if prior is not None:
                if (
                    prior["sequence"] == observation.sequence
                    and prior["checksum"] != observation.checksum
                ):
                    raise ExecutionError("receipt_conflict")
                if observation.sequence <= _integer(prior["sequence"]):
                    return record
            record = self._cas(session, observation.key, expected_revision, generation)
            updated = apply_evidence(record, observation)
            if updated.phase == "absent" and record.history_seq is None:
                updated = replace(
                    updated, history_seq=_integer(state["next_history_seq"])
                )
                session.execute(
                    SqlStatement(
                        "UPDATE execution_state SET next_history_seq=next_history_seq+1 WHERE singleton=1 AND project_id=?",
                        (self.project_id,),
                    )
                )
            updated = self._save(
                session, replace(updated, revision=record.revision + 1)
            )
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_receipt_admissions(project_id,run_id,task_id,attempt,launch_token,kind,sequence,checksum) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(project_id,run_id,task_id,attempt,launch_token,kind) DO UPDATE SET sequence=excluded.sequence,checksum=excluded.checksum",
                    (*receipt_key, observation.sequence, observation.checksum),
                )
            )
            return updated

    def request_stop(
        self,
        key: ExecutionKey,
        *,
        launch_token: str,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Keep current ownership after stop intent regardless of signal success."""
        with self.database.transaction() as session:
            self._writable(session, generation)
            record = self._cas(session, key, expected_revision, generation)
            if record.launch_token != launch_token:
                raise ExecutionError("execution_identity_conflict")
            if record.phase not in _CURRENT_PHASES:
                raise ExecutionError("execution_activity_unknown")
            return self._save(
                session, replace(record, phase="stopping", revision=record.revision + 1)
            )

    def record_collection(
        self,
        key: ExecutionKey,
        collection: Literal["collected", "failed", "refused"],
        payload_json: str,
        *,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Record validated collection result without reviving physical activity."""
        if collection not in {"collected", "failed", "refused"}:
            raise ValueError("invalid collection")
        payload = compatibility_payload(payload_json, key)
        with self.database.transaction() as session:
            self._writable(session, generation)
            record = self._cas(session, key, expected_revision, generation)
            if record.phase != "absent":
                raise ExecutionError("execution_activity_unknown")
            return self._save(
                session,
                replace(
                    record,
                    collection=collection,
                    payload_json=canonical_json(payload),
                    revision=record.revision + 1,
                ),
            )

    def current(
        self, *, limit: int = 128, deadline: float | None = None
    ) -> CurrentSnapshot:
        """Read only bounded current rows, with no historical scan or reconciliation."""
        _limit(limit)
        try:
            with self.database.read(deadline=deadline) as session:
                state = self._state(session)
                readiness = self._readiness(state)
                if not readiness.ready:
                    return CurrentSnapshot(
                        readiness, (), False, _integer(state["revision"])
                    )
                with session.stream(
                    SqlStatement(CURRENT_SQL, (self.project_id, limit + 1)),
                    batch_size=min(limit + 1, 1000),
                ) as rows:
                    records = tuple(_record(row) for row in rows)
                # SQLite's progress hook cannot interrupt Python DTO decoding.
                # An overrun must still refuse an exact activity count.
                if deadline is not None and time.monotonic() >= deadline:
                    raise DatabaseError("database_deadline_exceeded")
                complete = (
                    readiness.active_coverage == "complete" and len(records) <= limit
                )
                return CurrentSnapshot(
                    readiness, records[:limit], complete, _integer(state["revision"])
                )
        except (DatabaseError, ExecutionError, ValueError) as error:
            reason = (
                error.code
                if isinstance(error, (DatabaseError, ExecutionError))
                else "database_corrupt"
            )
            readiness = StorageReadiness(
                "sql",
                False,
                "unknown",
                0,
                self.database.target.identity.store_id,
                reason,
            )
            return CurrentSnapshot(readiness, (), False, 0)

    def page_history(
        self, *, after: int = 0, high_water: int | None = None, limit: int = 256
    ) -> HistoryPage:
        """Page immutable first-absence sequence order with a stable high water."""
        _limit(limit)
        if (
            type(after) is not int
            or after < 0
            or (
                high_water is not None
                and (type(high_water) is not int or high_water < after)
            )
        ):
            raise ValueError("invalid history cursor")
        with self.database.read() as session:
            state = self._require_ready(session)
            available = _integer(state["next_history_seq"]) - 1
            high = available if high_water is None else high_water
            if high > available or after > high:
                raise ValueError("invalid history cursor")
            with session.stream(
                SqlStatement(
                    "SELECT "
                    + _COLUMNS
                    + " FROM execution_attempts WHERE project_id=? AND history_seq>? AND history_seq<=? ORDER BY history_seq LIMIT ?",
                    (self.project_id, after, high, limit + 1),
                ),
                batch_size=min(limit + 1, 1000),
            ) as rows:
                records = tuple(_record(row) for row in rows)
            cursor = records[limit - 1].history_seq if len(records) > limit else None
            return HistoryPage(records[:limit], cursor, high)

    def ack_projection(
        self, key: ExecutionKey, *, revision: int, generation: int
    ) -> bool:
        """Acknowledge only the matching latest key/revision/generation."""
        self._key(key)
        with self.database.transaction() as session:
            self._writable(session, generation)
            row = session.fetch_one(
                SqlStatement(
                    "SELECT a.revision FROM execution_heads h JOIN execution_attempts a ON a.project_id=h.project_id AND a.run_id=h.run_id AND a.task_id=h.task_id AND a.attempt=h.latest_attempt WHERE h.project_id=? AND h.run_id=? AND h.task_id=? AND h.latest_attempt=? AND a.generation=?",
                    (*_key_values(key), generation),
                )
            )
            if type(revision) is not int or row is None or row[0] != revision:
                return False
            session.execute(
                SqlStatement(
                    "UPDATE execution_attempts SET projected_revision=? WHERE " + _KEY,
                    (revision, *_key_values(key)),
                )
            )
            session.execute(
                SqlStatement(
                    "UPDATE execution_heads SET projection_dirty=0 WHERE project_id=? AND run_id=? AND task_id=? AND latest_attempt=?",
                    _key_values(key),
                )
            )
            return True

    def dirty_heads(self, *, limit: int = 128) -> tuple[tuple[str, str], ...]:
        """Return bounded indexed projection repair candidates, never all history."""
        _limit(limit)
        with self.database.read() as session:
            self._require_ready(session)
            with session.stream(
                SqlStatement(
                    "SELECT run_id,task_id FROM execution_heads WHERE project_id=? AND projection_dirty=1 ORDER BY run_id,task_id LIMIT ?",
                    (self.project_id, limit),
                )
            ) as rows:
                return tuple((_text(row[0]), _text(row[1])) for row in rows)

    def import_legacy(
        self,
        session: SqlSession,
        records: tuple[ExecutionRecord, ...],
        *,
        source_facts: tuple[tuple[str, str, str], ...],
        next_attempt_floors: tuple[tuple[str, str, int], ...],
    ) -> tuple[int, int]:
        """Import <=256 frozen latest snapshots in the caller-owned transaction.

        Returns (inserted, replayed). No connect/commit/binding/cutover occurs.
        W4 checkpoints in this same session. Provenance is immutable; replay is
        exact. Records carry the next (cutover) generation while state remains
        importing/legacy in the source generation; W4 must CAS that state to the
        same target generation before any ordinary repository access.
        Floor-only facts may be imported with empty records/source_facts. They
        create only allocation floors; return counters count snapshots only.
        The caller's checkpoint must include floor facts in this same session.
        """
        if (
            not isinstance(records, tuple)
            or len(records) > 256
            or len(records) != len(source_facts)
            or len(next_attempt_floors) > 256
        ):
            raise ValueError("invalid import batch")
        state = self._state(session)
        if state["authority"] != "legacy" or state["readiness"] != "importing":
            raise ExecutionError("execution_storage_not_ready")
        generation = _integer(state["generation"])
        next_sequence = _integer(state["next_history_seq"])
        inserted = replayed = 0
        for record, (path, source_checksum, semantic_checksum) in zip(
            records, source_facts, strict=True
        ):
            self._key(record.key)
            if record.generation != generation + 1:
                raise ExecutionError("stale_generation")
            if (
                not path
                or "\x00" in path
                or "\\" in path
                or PurePosixPath(path).is_absolute()
                or PureWindowsPath(path).drive
                or any(part in {".", "..", ""} for part in path.split("/"))
                or any(
                    re.fullmatch(r"sha256:[0-9a-f]{64}", checksum) is None
                    for checksum in (source_checksum, semantic_checksum)
                )
            ):
                raise ValueError("invalid import provenance")
            compatibility_payload(record.payload_json, record.key)
            record = replace(
                record, payload_json=canonical_json(json.loads(record.payload_json))
            )
            old = self._load(session, record.key)
            if old is not None:
                source = session.fetch_one(
                    SqlStatement(
                        "SELECT source_path,source_checksum,semantic_checksum FROM execution_attempts WHERE "
                        + _KEY,
                        _key_values(record.key),
                    )
                )
                if (
                    source is None
                    or source.values != (path, source_checksum, semantic_checksum)
                    or replace(record, history_seq=old.history_seq) != old
                ):
                    raise ExecutionError("execution_identity_conflict")
                replayed += 1
                continue
            task = (self.project_id, record.key.run_id, record.key.task_id)
            head = session.fetch_one(
                SqlStatement(
                    "SELECT latest_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            if head is not None:
                raise ExecutionError("execution_identity_conflict")
            if record.phase == "absent":
                record = replace(record, history_seq=next_sequence)
                next_sequence += 1
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_attempts("
                    + _COLUMNS
                    + ",source_path,source_checksum,semantic_checksum) VALUES("
                    + ",".join("?" for _ in range(17))
                    + ")",
                    (*_values(record), path, source_checksum, semantic_checksum),
                )
            )
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_heads(project_id,run_id,task_id,latest_attempt,next_attempt,projection_dirty) VALUES(?,?,?,?,?,1)",
                    (*task, record.key.attempt, record.key.attempt + 1),
                )
            )
            saved_floor = session.fetch_one(
                SqlStatement(
                    "SELECT next_attempt FROM execution_allocation_floors WHERE project_id=? AND run_id=? AND task_id=?",
                    task,
                )
            )
            if saved_floor is not None:
                session.execute(
                    SqlStatement(
                        "UPDATE execution_heads SET next_attempt=MAX(next_attempt,?) WHERE project_id=? AND run_id=? AND task_id=?",
                        (_integer(saved_floor[0]), *task),
                    )
                )
                session.execute(
                    SqlStatement(
                        "DELETE FROM execution_allocation_floors WHERE project_id=? AND run_id=? AND task_id=?",
                        task,
                    )
                )
            if record.phase in _CURRENT_PHASES:
                session.execute(
                    SqlStatement(
                        "INSERT INTO execution_current(project_id,run_id,task_id,attempt) VALUES(?,?,?,?)",
                        _key_values(record.key),
                    )
                )
            inserted += 1
        for run_id, task_id, floor in next_attempt_floors:
            ExecutionKey(self.project_id, run_id, task_id, floor)
            head = session.fetch_one(
                SqlStatement(
                    "SELECT latest_attempt FROM execution_heads WHERE project_id=? AND run_id=? AND task_id=?",
                    (self.project_id, run_id, task_id),
                )
            )
            if head is None:
                session.execute(
                    SqlStatement(
                        "INSERT INTO execution_allocation_floors(project_id,run_id,task_id,next_attempt) VALUES(?,?,?,?) ON CONFLICT(project_id,run_id,task_id) DO UPDATE SET next_attempt=MAX(next_attempt,excluded.next_attempt)",
                        (self.project_id, run_id, task_id, floor),
                    )
                )
                continue
            if floor <= _integer(head[0]):
                raise ValueError("invalid attempt floor")
            session.execute(
                SqlStatement(
                    "UPDATE execution_heads SET next_attempt=MAX(next_attempt,?) WHERE project_id=? AND run_id=? AND task_id=?",
                    (floor, self.project_id, run_id, task_id),
                )
            )
        session.execute(
            SqlStatement(
                "UPDATE execution_state SET next_history_seq=?,revision=revision+? WHERE singleton=1 AND project_id=?",
                (next_sequence, inserted, self.project_id),
            )
        )
        return inserted, replayed
