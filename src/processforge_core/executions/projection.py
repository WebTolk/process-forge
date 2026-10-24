"""Validated compatibility DTOs and recoverable, task-locked publication."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from contextlib import AbstractContextManager, suppress
from dataclasses import replace
from pathlib import Path
from typing import cast
from uuid import uuid4

from .model import ExecutionKey, ExecutionRecord
from .ports import ExecutionRepository

PUBLIC_STATUSES = frozenset(
    {
        "planned",
        "ready",
        "manual_required",
        "blocked",
        "starting",
        "running",
        "completed",
        "failed",
        "timed_out",
        "unknown_exit",
        "lost",
        "cancelled",
    }
)
_TEXT = (
    "driver_id",
    "agent_model",
    "capsule_path",
    "worker_prompt_path",
    "expected_report_path",
    "stdout_path",
    "stderr_path",
    "heartbeat_path",
)
_OPTIONAL_TEXT = ("started_at", "finished_at", "last_heartbeat_at", "failure_reason")
_PRIVATE = frozenset(
    {"launch_token", "generation", "revision", "projected_revision", "process"}
)


def canonical_json(value: object) -> str:
    """Encode finite UTF-8 JSON without changing opaque strings."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid compatibility payload")
        result[key] = value
    return result


def _walk(value: object) -> None:
    if isinstance(value, str):
        if "\x00" in value:
            raise ValueError("invalid compatibility payload")
        value.encode("utf-8")
    elif isinstance(value, dict):
        for key, item in value.items():
            _walk(key)
            _walk(item)
    elif isinstance(value, list):
        for item in value:
            _walk(item)


def compatibility_payload(payload_json: str, key: ExecutionKey) -> dict[str, object]:
    """Validate the existing schema-1 status DTO, retaining unknown extensions.

    Private execution bookkeeping cannot be introduced into a public payload.
    Paths remain opaque references; authorization belongs to host composition.
    """
    value = json.loads(payload_json, object_pairs_hook=_pairs)
    if not isinstance(value, dict):
        raise ValueError("invalid compatibility payload")
    result = cast(dict[str, object], value)
    _walk(result)
    canonical_json(result)  # Reject NaN, Infinity and exponent overflow recursively.
    if (
        type(result.get("schema_version")) is not int
        or result["schema_version"] != 1
        or result.get("run_id") != key.run_id
        or result.get("task_id") != key.task_id
        or type(result.get("attempt")) is not int
        or result["attempt"] != key.attempt
        or not isinstance(result.get("status"), str)
        or result.get("status") not in PUBLIC_STATUSES
        or _PRIVATE.intersection(result)
    ):
        raise ValueError("invalid compatibility payload")
    for name in _TEXT:
        if not isinstance(result.get(name), str):
            raise ValueError("invalid compatibility payload")
    for name in _OPTIONAL_TEXT:
        if name not in result or (
            result[name] is not None and not isinstance(result[name], str)
        ):
            raise ValueError("invalid compatibility payload")
    for name in ("pid", "exit_code"):
        if name not in result or (
            result[name] is not None and type(result[name]) is not int
        ):
            raise ValueError("invalid compatibility payload")
    if result["pid"] is not None and cast(int, result["pid"]) < 1:
        raise ValueError("invalid compatibility payload")
    for name in ("timeout_seconds", "max_retries"):
        if type(result.get(name)) is not int or cast(int, result[name]) < 0:
            raise ValueError("invalid compatibility payload")
    return result


def projected_payload(record: ExecutionRecord) -> dict[str, object]:
    """Return the authoritative compatibility DTO with existing public statuses."""
    payload = compatibility_payload(record.payload_json, record.key)
    if record.phase == "prepared":
        if payload["status"] not in {
            "planned",
            "ready",
            "manual_required",
            "blocked",
            "cancelled",
            "failed",
        }:
            raise ValueError("invalid prepared payload")
    elif record.phase in {"starting", "running"}:
        payload["status"] = record.phase
    elif record.phase == "stopping":
        payload.update(status="cancelled", failure_reason="stop requested")
    elif record.phase == "unresolved":
        if payload["status"] != "cancelled":
            payload["status"] = "running"
        payload["failure_reason"] = "execution activity unknown"
    else:
        if record.outcome not in PUBLIC_STATUSES:
            raise ValueError("invalid public outcome")
        payload["status"] = record.outcome
    if record.collection == "failed":
        payload["status"] = "failed"
    # Semantic refusal keeps the existing completed/refusal payload, not acceptance.
    return payload


def with_projection(record: ExecutionRecord) -> ExecutionRecord:
    """Keep the compatibility DTO in the same transaction as lifecycle facts."""
    return replace(record, payload_json=canonical_json(projected_payload(record)))


class ExecutionProjection:
    """Publish under the same task lock used by lifecycle writers.

    The host supplies an authorized destination and its existing lifecycle lock.
    All head-changing writers must use that lock. A crash before acknowledgement
    leaves an indexed dirty head for retry; no history reconstruction is needed.
    """

    def __init__(
        self,
        repository: ExecutionRepository,
        task_lock: Callable[[str, str], AbstractContextManager[object]],
    ) -> None:
        self.repository = repository
        self.task_lock = task_lock

    def publish(self, run_id: str, task_id: str, destination: Path) -> bool:
        """Atomically replace the latest DTO, then CAS-ack its exact revision."""
        with self.task_lock(run_id, task_id):
            return self._publish_locked(run_id, task_id, destination)

    def _publish_locked(self, run_id: str, task_id: str, destination: Path) -> bool:
        """Publish when the host already holds the non-reentrant task lock."""
        record = self.repository.load_latest(run_id, task_id)
        if record is None:
            return False
        raw = (canonical_json(projected_payload(record)) + "\n").encode("utf-8")
        temporary = destination.with_name("." + destination.name + "." + uuid4().hex)
        try:
            with temporary.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except OSError:
            return False
        finally:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
        return self.repository.ack_projection(
            record.key, revision=record.revision, generation=record.generation
        )
