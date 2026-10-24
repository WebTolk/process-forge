"""Projection CAS, retry after interrupted acknowledgement, and DTO parity."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

import pytest

from processforge_core.executions.model import ExecutionKey
from processforge_core.executions.projection import (
    ExecutionProjection,
    canonical_json,
    compatibility_payload,
    projected_payload,
)

from .test_repository import (
    Harness,
    payload,
    receipt,
)
from .test_repository import (
    harness as harness,
)
from .test_repository import (
    isolated_path as isolated_path,
)


@contextmanager
def task_lock(run_id: str, task_id: str) -> Iterator[None]:
    yield


def test_atomic_publication_and_ack_preserve_lifecycle_revision(
    harness: Harness,
) -> None:
    record = harness.start()
    destination = harness.root / "status.json"
    projection = ExecutionProjection(harness.repo, task_lock)
    before_revision = harness.repo.current().revision
    assert harness.repo.dirty_heads() == (("run", "task"),)
    assert projection.publish("run", "task", destination)
    published = json.loads(destination.read_text(encoding="utf-8"))
    assert published == projected_payload(record)
    assert (
        "launch_token" not in published
        and "revision" not in published
        and "generation" not in published
    )
    assert published["old_extension"] == {"opaque": "unchanged"}
    after = harness.repo.load(record.key)
    assert after is not None and after.projected_revision == record.revision
    assert (
        after.revision == record.revision
        and harness.repo.current().revision == before_revision
    )
    assert harness.repo.dirty_heads() == ()


def test_crash_after_publish_before_ack_repairs_from_sql(harness: Harness) -> None:
    harness.start()
    destination = harness.root / "status.json"
    projection = ExecutionProjection(harness.repo, task_lock)
    with patch.object(
        harness.repo, "ack_projection", side_effect=RuntimeError("crash")
    ):
        with pytest.raises(RuntimeError, match="crash"):
            projection.publish("run", "task", destination)
    assert destination.exists() and harness.repo.dirty_heads() == (("run", "task"),)
    destination.write_text('{"wrong":"stale file is not authority"}', encoding="utf-8")
    assert projection.publish("run", "task", destination)
    assert json.loads(destination.read_text(encoding="utf-8"))["status"] == "starting"


def test_publish_failure_retains_dirty_and_old_attempt_cannot_ack(
    harness: Harness,
) -> None:
    first = harness.finish(harness.start())
    projection = ExecutionProjection(harness.repo, task_lock)
    assert not projection.publish(
        "run", "task", harness.root / "absent-parent" / "status.json"
    )
    assert harness.repo.dirty_heads() == (("run", "task"),)
    newer = harness.prepare(attempt=2)
    assert not harness.repo.ack_projection(
        first.key, revision=first.revision, generation=1
    )
    destination = harness.root / "status.json"
    assert projection.publish("run", "task", destination)
    assert (
        json.loads(destination.read_text(encoding="utf-8"))["attempt"]
        == newer.key.attempt
    )


def test_stale_revision_ack_is_false_and_stop_mapping_compatible(
    harness: Harness,
) -> None:
    start = harness.start()
    stopping = harness.repo.request_stop(
        start.key,
        launch_token=start.launch_token or "",
        expected_revision=start.revision,
        generation=1,
    )
    assert not harness.repo.ack_projection(
        start.key, revision=start.revision, generation=1
    )
    assert projected_payload(stopping)["status"] == "cancelled"
    assert projected_payload(stopping)["failure_reason"] == "stop requested"
    unresolved = harness.repo.apply_observation(
        receipt(stopping, "exit", exit_code=0),
        expected_revision=stopping.revision,
        generation=1,
    )
    assert projected_payload(unresolved)["status"] == "cancelled"
    assert len(harness.repo.current().records) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"attempt": 2},
        {"run_id": "other"},
        {"status": "absent"},
        {"status": []},
        {"pid": True},
        {"timeout_seconds": -1},
        {"launch_token": "a" * 32},
        {"generation": 1},
        {"extra": float("nan")},
    ],
)
def test_invalid_compatibility_payload_refused(change: dict[str, object]) -> None:
    data = json.loads(payload())
    data.update(change)
    # json.dumps deliberately permits nonfinite input to exercise the validator.
    with pytest.raises(ValueError):
        compatibility_payload(
            json.dumps(data), ExecutionKey("project", "run", "task", 1)
        )


def test_json_duplicate_nul_and_full_fields_refused() -> None:
    key = ExecutionKey("project", "run", "task", 1)
    for raw in ('{"x":1,"x":2}', '{"x":"\\u0000"}', "{}"):
        with pytest.raises(ValueError):
            compatibility_payload(raw, key)
    data = json.loads(payload())
    data.pop("heartbeat_path")
    with pytest.raises(ValueError):
        compatibility_payload(canonical_json(data), key)


def test_projection_preserves_legacy_statuses_and_extensions(harness: Harness) -> None:
    record = harness.prepare()
    assert projected_payload(record) == json.loads(record.payload_json)
    for status in ("planned", "ready", "manual_required", "blocked"):
        data = json.loads(record.payload_json)
        data["status"] = status
        assert (
            projected_payload(replace(record, payload_json=canonical_json(data)))[
                "status"
            ]
            == status
        )
