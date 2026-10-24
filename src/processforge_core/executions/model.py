"""Immutable execution facts, independent of storage and operating systems.

Constructors validate shape and local invariants without normalizing identity,
authenticating receipts, probing processes or applying lifecycle transitions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Literal

_HEX_ID = re.compile(r"[0-9a-f]{32}")
_CHECKSUM = re.compile(r"sha256:[0-9a-f]{64}")
_CURRENT_PHASES = frozenset({"starting", "running", "stopping", "unresolved"})
_PHASES = _CURRENT_PHASES | {"prepared", "absent"}
_OUTCOMES = frozenset(
    {"completed", "failed", "timed_out", "cancelled", "unknown_exit", "lost", "blocked"}
)
_COLLECTIONS = frozenset({"pending", "collected", "failed", "refused"})
_RECEIPT_KINDS = frozenset({"process", "heartbeat", "exit", "absence", "spawn_failed"})


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"invalid {field}")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError(f"invalid {field}") from None


def _optional_text(value: object, field: str) -> None:
    if value is not None:
        _text(value, field)


def _integer(value: object, field: str, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"invalid {field}")


def _boolean(value: object, field: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"invalid {field}")


def _choice(value: object, choices: frozenset[str], field: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"invalid {field}")


def _hex_id(value: object, field: str) -> None:
    if not isinstance(value, str) or _HEX_ID.fullmatch(value) is None:
        raise ValueError(f"invalid {field}")


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid payload_json")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("invalid payload_json")


def _json_value(value: object) -> None:
    # parse_constant catches NaN/Infinity, but JSON exponent overflow also
    # produces a nonfinite float and must be rejected recursively.
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("invalid payload_json")
    elif isinstance(value, str):
        if "\x00" in value:
            raise ValueError("invalid payload_json")
        value.encode("utf-8")
    elif isinstance(value, list):
        for item in value:
            _json_value(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _json_value(key)
            _json_value(item)


def _payload(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("invalid payload_json")
    try:
        parsed = json.loads(
            value, object_pairs_hook=_json_object, parse_constant=_nonfinite
        )
        if not isinstance(parsed, dict):
            raise ValueError("invalid payload_json")
        _json_value(parsed)
    except (ValueError, RecursionError):
        raise ValueError("invalid payload_json") from None


@dataclass(frozen=True)
class ExecutionKey:
    """Identify one existing assignment attempt; task_id is assignment_id.

    Identifiers are nonblank, NUL-free opaque strings, retained byte for byte.
    Filesystem selector validation remains the caller's responsibility.
    """

    project_id: str
    run_id: str
    task_id: str
    attempt: int

    def __post_init__(self) -> None:
        """Reject missing identity and nonintegral or nonpositive attempts."""
        for field in ("project_id", "run_id", "task_id"):
            _text(getattr(self, field), field)
        _integer(self.attempt, "attempt", 1)


@dataclass(frozen=True)
class ProcessIdentity:
    """Carry OS-derived birth/tree identity; PID alone is never ownership proof."""

    host_id: str
    boot_id: str | None
    pid: int
    birth_id: str
    tree_id: str | None

    def __post_init__(self) -> None:
        """Require a host, positive PID and opaque birth identity."""
        _text(self.host_id, "host_id")
        _optional_text(self.boot_id, "boot_id")
        _integer(self.pid, "pid", 1)
        _text(self.birth_id, "birth_id")
        _optional_text(self.tree_id, "tree_id")


@dataclass(frozen=True)
class StorageReadiness:
    """Separate storage authority/readiness from completeness of active coverage."""

    authority: Literal["legacy", "sql"]
    ready: bool
    active_coverage: Literal["complete", "unknown"]
    generation: int
    store_id: str | None
    reason: str | None

    def __post_init__(self) -> None:
        """Require concrete store identity before declaring SQL ready."""
        _choice(self.authority, frozenset({"legacy", "sql"}), "authority")
        _boolean(self.ready, "ready")
        _choice(
            self.active_coverage, frozenset({"complete", "unknown"}), "active_coverage"
        )
        _integer(self.generation, "generation")
        if self.store_id is not None:
            _hex_id(self.store_id, "store_id")
        if self.authority == "sql" and self.ready and self.store_id is None:
            raise ValueError("invalid store_id")
        _optional_text(self.reason, "reason")


@dataclass(frozen=True)
class ExecutionRecord:
    """Carry one attempt's internal facts and unchanged compatibility payload.

    Phases and outcomes are internal; adapters own existing public statuses.
    Adapters also validate the full payload schema and canonical serialization.
    """

    key: ExecutionKey
    launch_token: str | None
    revision: int
    generation: int
    phase: Literal[
        "prepared", "starting", "running", "stopping", "unresolved", "absent"
    ]
    outcome: str | None
    collection: Literal["pending", "collected", "failed", "refused"]
    process: ProcessIdentity | None
    history_seq: int | None
    payload_json: str
    projected_revision: int

    def __post_init__(self) -> None:
        """Check counters, immutable nested shapes and terminal/history parity."""
        if not isinstance(self.key, ExecutionKey):
            raise ValueError("invalid key")
        if self.launch_token is not None:
            _hex_id(self.launch_token, "launch_token")
        _integer(self.revision, "revision", 1)
        _integer(self.generation, "generation")
        _choice(self.phase, _PHASES, "phase")
        if self.outcome is not None:
            _choice(self.outcome, _OUTCOMES, "outcome")
        _choice(self.collection, _COLLECTIONS, "collection")
        if self.process is not None and not isinstance(self.process, ProcessIdentity):
            raise ValueError("invalid process")
        if self.history_seq is not None:
            _integer(self.history_seq, "history_seq", 1)
        if self.phase == "absent":
            if self.outcome is None or self.history_seq is None:
                raise ValueError("invalid terminal history")
        elif self.outcome is not None or self.history_seq is not None:
            raise ValueError("invalid nonterminal history")
        _integer(self.projected_revision, "projected_revision")
        if self.projected_revision > self.revision:
            raise ValueError("invalid projected_revision")
        _payload(self.payload_json)


def _records(value: object) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(record, ExecutionRecord) for record in value
    ):
        raise ValueError("invalid records")


@dataclass(frozen=True)
class CurrentSnapshot:
    """Return current executions only; incomplete empty results never prove idle."""

    readiness: StorageReadiness
    records: tuple[ExecutionRecord, ...]
    complete: bool
    revision: int

    def __post_init__(self) -> None:
        """Reject archived rows, duplicate task ownership and false completeness."""
        if not isinstance(self.readiness, StorageReadiness):
            raise ValueError("invalid readiness")
        _records(self.records)
        _boolean(self.complete, "complete")
        _integer(self.revision, "revision")
        if self.complete and (
            not self.readiness.ready or self.readiness.active_coverage != "complete"
        ):
            raise ValueError("invalid complete")
        tasks: set[tuple[str, str, str]] = set()
        for record in self.records:
            if record.phase not in _CURRENT_PHASES:
                raise ValueError("invalid current phase")
            if record.generation != self.readiness.generation:
                raise ValueError("invalid current generation")
            task = (record.key.project_id, record.key.run_id, record.key.task_id)
            if task in tasks:
                raise ValueError("invalid duplicate current task")
            tasks.add(task)


@dataclass(frozen=True)
class HistoryPage:
    """Carry ordered proven absences bounded by a captured sequence high water."""

    records: tuple[ExecutionRecord, ...]
    after: int | None
    high_water: int

    def __post_init__(self) -> None:
        """Reject unordered, duplicate or beyond-snapshot history sequences."""
        _records(self.records)
        _integer(self.high_water, "high_water")
        if self.after is not None:
            _integer(self.after, "after")
            if self.after > self.high_water:
                raise ValueError("invalid after")
        previous = 0
        keys: set[ExecutionKey] = set()
        for record in self.records:
            sequence = record.history_seq
            if record.phase != "absent" or sequence is None:
                raise ValueError("invalid history phase")
            if not previous < sequence <= self.high_water or record.key in keys:
                raise ValueError("invalid history order")
            previous = sequence
            keys.add(record.key)


@dataclass(frozen=True)
class ExecutionObservation:
    """Carry admitted evidence, never a command or independent lifecycle writer.

    Shape validation cannot establish receipt authenticity, sequence freshness,
    checksum parity, launch ownership or full process-tree absence.
    """

    key: ExecutionKey
    launch_token: str
    receipt_kind: Literal["process", "heartbeat", "exit", "absence", "spawn_failed"]
    sequence: int
    checksum: str
    process: ProcessIdentity | None
    observed_at: str
    status: str | None = None
    exit_code: int | None = None
    tree_absent: bool = False

    def __post_init__(self) -> None:
        """Validate launch/evidence shapes and an explicit timestamp offset."""
        if not isinstance(self.key, ExecutionKey):
            raise ValueError("invalid key")
        _hex_id(self.launch_token, "launch_token")
        _choice(self.receipt_kind, _RECEIPT_KINDS, "receipt_kind")
        _integer(self.sequence, "sequence")
        if not isinstance(self.checksum, str) or not _CHECKSUM.fullmatch(self.checksum):
            raise ValueError("invalid checksum")
        if self.process is not None and not isinstance(self.process, ProcessIdentity):
            raise ValueError("invalid process")
        if self.receipt_kind == "process" and self.process is None:
            raise ValueError("invalid process receipt")
        if self.receipt_kind == "spawn_failed" and self.process is not None:
            raise ValueError("invalid spawn_failed receipt")
        _text(self.observed_at, "observed_at")
        try:
            timestamp = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
            if timestamp.utcoffset() is None:
                raise ValueError("missing offset")
        except ValueError:
            raise ValueError("invalid observed_at") from None
        _optional_text(self.status, "status")
        if self.exit_code is not None and type(self.exit_code) is not int:
            raise ValueError("invalid exit_code")
        _boolean(self.tree_absent, "tree_absent")


class ExecutionError(Exception):
    """Expose a stable execution refusal code without evidence or private paths.

    Repository codes include stale_revision, stale_generation, receipt_conflict,
    execution_identity_conflict, execution_activity_unknown and
    execution_storage_not_ready. Validation failures use ValueError instead.
    """

    def __init__(self, code: str) -> None:
        """Retain only the machine-readable code as the exception message."""
        if not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]*", code) is None:
            raise ValueError("invalid execution error code")
        self.code = code
        super().__init__(code)
