"""Validate domain boundaries without a database, CLI or live process fixture."""

from __future__ import annotations

import subprocess
import sys
from copy import copy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Protocol

import pytest

from processforge_core.executions import (
    CurrentSnapshot,
    ExecutionError,
    ExecutionKey,
    ExecutionObservation,
    ExecutionRecord,
    HistoryPage,
    ProcessIdentity,
    StorageReadiness,
)

TOKEN = "a" * 32
CHECKSUM = "sha256:" + "b" * 64


class Validated(Protocol):
    """Expose the runtime boundary validator used by every DTO constructor."""

    def __post_init__(self) -> None:
        """Reject malformed fields supplied at an untyped input boundary."""
        ...


def validate_changes(value: Validated, **changes: object) -> None:
    """Feed deliberately malformed fields to the constructor's exact validator.

    Bypass freezing only on a disposable copy so negative tests do not lie to
    the type checker about the runtime types they intentionally supply.
    """
    candidate = copy(value)
    for name, field_value in changes.items():
        object.__setattr__(candidate, name, field_value)
    candidate.__post_init__()


def key() -> ExecutionKey:
    """Return an exact existing assignment identity."""
    return ExecutionKey("project", "run", "assignment", 1)


def process() -> ProcessIdentity:
    """Return opaque host/birth/tree evidence without inspecting the OS."""
    return ProcessIdentity("host", None, 42, "creation:123", "owned-tree:7")


def readiness() -> StorageReadiness:
    """Return complete SQL coverage, not a process liveness assertion."""
    return StorageReadiness("sql", True, "complete", 1, "c" * 32, None)


def record() -> ExecutionRecord:
    """Return a prepared record with a legacy-shaped payload extension."""
    return ExecutionRecord(
        key(),
        None,
        1,
        1,
        "prepared",
        None,
        "pending",
        None,
        None,
        '{"extension":{"nested":[1,true,null]},"status":"ready"}',
        0,
    )


def observation() -> ExecutionObservation:
    """Return shape-valid evidence; admission still needs checksum verification."""
    return ExecutionObservation(
        key(), TOKEN, "process", 0, CHECKSUM, process(), "2026-10-24T16:00:00Z"
    )


def terminal(sequence: int = 1, attempt: int = 1) -> ExecutionRecord:
    """Return proven absence, separately from collection acceptance."""
    return replace(
        record(),
        key=replace(key(), attempt=attempt),
        phase="absent",
        outcome="unknown_exit",
        history_seq=sequence,
    )


def test_identity_is_preserved_without_normalization() -> None:
    """Keep case, Unicode normalization, punctuation and assignment identity."""
    exact = ExecutionKey("Project.Ω", "run--e\u0301", " assignment:A ", 7)
    assert exact.project_id == "Project.Ω"
    assert exact.run_id.encode("utf-8") == b"run--e\xcc\x81"
    assert exact.task_id == " assignment:A "
    assert exact.attempt == 7
    assert exact != replace(exact, run_id="run--é")


@pytest.mark.parametrize("field", ["project_id", "run_id", "task_id"])
@pytest.mark.parametrize("value", [None, "", " \t", "x\x00y", 7, "\ud800"])
def test_invalid_identity_is_rejected(field: str, value: object) -> None:
    """Do not coerce missing, NUL-bearing or non-UTF-8 identity."""
    with pytest.raises(ValueError, match="invalid"):
        validate_changes(key(), **{field: value})


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "1", None])
def test_attempt_requires_positive_exact_integer(value: object) -> None:
    """Bool cannot alias an existing numeric attempt."""
    with pytest.raises(ValueError, match="attempt"):
        validate_changes(key(), attempt=value)


@pytest.mark.parametrize(
    "changes",
    [
        {"host_id": ""},
        {"birth_id": ""},
        {"birth_id": None},
        {"pid": True},
        {"pid": 0},
        {"pid": -1},
        {"pid": "42"},
        {"boot_id": ""},
        {"tree_id": 7},
    ],
)
def test_pid_alone_and_malformed_process_identity_are_rejected(
    changes: dict[str, object],
) -> None:
    """Require opaque birth evidence while allowing platform-specific boot/tree."""
    with pytest.raises(ValueError):
        validate_changes(process(), **changes)
    assert (
        replace(process(), boot_id="boot-id", tree_id=None).birth_id == "creation:123"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"authority": "other"},
        {"ready": 1},
        {"active_coverage": "partial"},
        {"generation": True},
        {"generation": -1},
        {"store_id": None},
        {"store_id": "not-an-id"},
        {"reason": ""},
    ],
)
def test_readiness_requires_honest_shapes(changes: dict[str, object]) -> None:
    """A ready SQL result requires pinned concrete store identity."""
    with pytest.raises(ValueError):
        validate_changes(readiness(), **changes)


def test_not_ready_or_unknown_empty_snapshot_never_claims_idle() -> None:
    """Unknown coverage and missing bound storage remain explicitly incomplete."""
    for state in (
        replace(readiness(), active_coverage="unknown"),
        replace(readiness(), ready=False, store_id=None, reason="database_missing"),
    ):
        assert not CurrentSnapshot(state, (), False, 0).complete
        with pytest.raises(ValueError, match="complete"):
            CurrentSnapshot(state, (), True, 0)
    legacy = StorageReadiness("legacy", True, "complete", 0, None, None)
    assert CurrentSnapshot(legacy, (), True, 0).complete


@pytest.mark.parametrize(
    "changes",
    [
        {"key": {}},
        {"revision": True},
        {"revision": 0},
        {"generation": False},
        {"generation": -1},
        {"phase": "completed"},
        {"outcome": "completed"},
        {"history_seq": 1},
        {"collection": "accepted"},
        {"process": {"pid": 42}},
        {"projected_revision": -1},
        {"projected_revision": True},
        {"projected_revision": 2},
        {"launch_token": "not-a-token"},
        {"launch_token": "A" * 32},
    ],
)
def test_record_counters_and_facts_are_validated(changes: dict[str, object]) -> None:
    """Reject malformed revisions, generation, process and projection facts."""
    with pytest.raises(ValueError):
        validate_changes(record(), **changes)


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        "null",
        "42",
        "broken",
        '{"x":1,"x":2}',
        '{"x":{"y":1,"y":2}}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":[1e9999]}',
        '{"x":"\\u0000"}',
        '{"x":"\\ud800"}',
    ],
)
def test_payload_rejects_ambiguous_or_nonfinite_json_without_echo(payload: str) -> None:
    """Reject invalid evidence without returning its potentially private body."""
    with pytest.raises(ValueError) as caught:
        replace(record(), payload_json=payload)
    assert str(caught.value) == "invalid payload_json"


def test_payload_extensions_and_exact_text_are_preserved() -> None:
    """Model validation does not rewrite the adapter's compatibility payload."""
    payload = '{ "unknown_extension": "é", "status": "completed" }'
    assert replace(record(), payload_json=payload).payload_json == payload


@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": None},
        {"outcome": "new_public_status"},
        {"history_seq": None},
        {"history_seq": 0},
        {"history_seq": True},
    ],
)
def test_absence_has_one_valid_history_sequence(changes: dict[str, object]) -> None:
    """Absence outcome/history are paired independently of artifact collection."""
    with pytest.raises(ValueError):
        validate_changes(terminal(), **changes)


def test_collection_failure_does_not_revive_a_process() -> None:
    """Failed/refused collection can coexist with proven physical absence."""
    for collection in ("collected", "failed", "refused"):
        result = replace(terminal(), collection=collection)
        assert result.phase == "absent"
        assert result.history_seq == 1
        assert result.outcome == "unknown_exit"


def test_current_snapshot_rejects_history_and_duplicate_task_ownership() -> None:
    """Only current phases and one attempt per task belong in current views."""
    active = replace(record(), phase="starting", launch_token=TOKEN)
    assert CurrentSnapshot(readiness(), (active,), True, 1).records == (active,)
    for records in (
        (record(),),
        (terminal(),),
        (active, active),
        (active, replace(active, key=replace(key(), attempt=2))),
        (replace(active, generation=0),),
    ):
        with pytest.raises(ValueError):
            CurrentSnapshot(readiness(), records, True, 1)
    with pytest.raises(ValueError):
        validate_changes(CurrentSnapshot(readiness(), (), True, 0), records=[])


def test_history_order_high_water_and_cursor_are_bounded() -> None:
    """Later updates retain absence order and cannot extend a captured page."""
    first, second = terminal(1, 1), terminal(3, 2)
    assert HistoryPage((first, second), 3, 3).records == (first, second)
    assert HistoryPage((), None, 0).after is None
    for records in ((second, first), (first, first), (record(),), (terminal(4),)):
        with pytest.raises(ValueError):
            HistoryPage(records, None, 3)
    with pytest.raises(ValueError):
        HistoryPage((first,), 4, 3)
    with pytest.raises(ValueError):
        HistoryPage((), None, True)


@pytest.mark.parametrize(
    "changes",
    [
        {"key": "latest"},
        {"launch_token": ""},
        {"sequence": True},
        {"sequence": -1},
        {"checksum": "b" * 64},
        {"checksum": "sha256:" + "G" * 64},
        {"receipt_kind": "stop"},
        {"process": None},
        {"process": {"pid": 42}},
        {"observed_at": "2026-10-24T16:00:00"},
        {"observed_at": "yesterday"},
        {"tree_absent": 1},
        {"exit_code": True},
        {"exit_code": "0"},
        {"status": ""},
    ],
)
def test_observation_requires_exact_evidence_shapes(changes: dict[str, object]) -> None:
    """Neither PID dictionaries nor unqualified timestamps become evidence."""
    with pytest.raises(ValueError):
        validate_changes(observation(), **changes)


def test_observation_preserves_old_attempt_and_birth_evidence() -> None:
    """Old-attempt evidence stays old; observation creates no terminal record."""
    old = replace(
        observation(),
        receipt_kind="exit",
        sequence=4,
        exit_code=-9,
        tree_absent=False,
        observed_at="2026-10-24T20:00:00+04:00",
    )
    assert old.key.attempt == 1
    assert old.process == process()
    assert old.launch_token == TOKEN
    assert not old.tree_absent
    failed = replace(observation(), receipt_kind="spawn_failed", process=None)
    assert failed.process is None
    with pytest.raises(ValueError):
        replace(failed, process=process())


@pytest.mark.parametrize(
    "value",
    [
        key(),
        process(),
        readiness(),
        record(),
        observation(),
        CurrentSnapshot(readiness(), (), True, 0),
        HistoryPage((), None, 0),
    ],
)
def test_dtos_are_frozen(value: object) -> None:
    """DTOs and tuple containers cannot silently become editable owners."""
    with pytest.raises(FrozenInstanceError):
        setattr(value, "key", key())


def test_error_exposes_only_a_machine_code() -> None:
    """Keep error mapping available without SQL/evidence/private path contents."""
    error = ExecutionError("receipt_conflict")
    assert error.code == "receipt_conflict"
    assert error.args == ("receipt_conflict",)
    with pytest.raises(ValueError):
        ExecutionError("private/path:raw evidence")


def test_cold_import_without_io_or_backend() -> None:
    """Import and construct in a fresh interpreter with side effects forbidden."""
    script = """
import pathlib
import sqlite3
import subprocess
import sys
def forbidden(*args, **kwargs):
    raise AssertionError("unexpected side effect")
sqlite3.connect = forbidden
pathlib.Path.mkdir = forbidden
pathlib.Path.open = forbidden
subprocess.Popen = forbidden
from processforge_core.executions import ExecutionKey, ExecutionRepository
assert ExecutionKey("p", "r", "t", 1).attempt == 1
assert not any(name.startswith(("processforge_core.database",
                              "processforge_core.executions.sqlite_repository",
                              "tools.processforge")) for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
