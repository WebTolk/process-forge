"""Crash gaps, uncertainty, collection, stale receipts and process identity."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import replace
from pathlib import Path

import pytest

from processforge_core.executions.model import ExecutionError, ExecutionObservation
from processforge_core.executions.service import ExecutionService
from processforge_core.runtime import process_identity

from .test_repository import (
    PROCESS,
    STAMP,
    Harness,
    receipt,
)
from .test_repository import (
    harness as harness,
)
from .test_repository import (
    isolated_path as isolated_path,
)


def test_controller_death_and_exit_without_tree_proof_stay_current(
    harness: Harness,
) -> None:
    starting = harness.start()
    # No TTL reclamation: losing the controller before Popen/attach stays current.
    assert harness.repo.current().records == (starting,)
    service = ExecutionService(harness.repo)
    running = service.observe(
        receipt(starting, "process"), expected_revision=2, generation=1
    )
    unresolved = service.observe(
        receipt(running, "exit", exit_code=0), expected_revision=3, generation=1
    )
    assert unresolved.phase == "unresolved" and len(harness.repo.current().records) == 1
    assert service.payload(unresolved)["status"] == "running"
    absent = service.observe(
        receipt(unresolved, "absence", tree_absent=True),
        expected_revision=4,
        generation=1,
    )
    assert absent.outcome == "completed" and harness.repo.current().records == ()
    assert absent.history_seq == 1


def test_untrustworthy_exit_does_not_invent_success(harness: Harness) -> None:
    starting = harness.start()
    absent = harness.repo.apply_observation(
        receipt(starting, "absence", tree_absent=True),
        expected_revision=2,
        generation=1,
    )
    assert absent.outcome == "unknown_exit"
    assert (
        json.loads(absent.payload_json)["status"] == "unknown_exit"
    )  # Existing adapter status.
    assert json.loads(absent.payload_json)["exit_code"] is None


def test_unattached_absence_and_spawn_failure(harness: Harness) -> None:
    record = harness.start()
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo.apply_observation(
            receipt(record, "absence", process=None, tree_absent=True),
            expected_revision=2,
            generation=1,
        )
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        harness.repo.apply_observation(
            receipt(record, "spawn_failed", process=None),
            expected_revision=2,
            generation=1,
        )
    absent = harness.repo.apply_observation(
        receipt(record, "spawn_failed", process=None, tree_absent=True),
        expected_revision=2,
        generation=1,
    )
    assert (
        absent.outcome == "failed"
        and absent.process is None
        and absent.history_seq == 1
    )
    assert harness.repo.current().records == ()


def test_heartbeat_timestamp_is_evidence_not_observation_clock(
    harness: Harness,
) -> None:
    record = harness.start()
    first = harness.repo.apply_observation(
        receipt(record, "heartbeat", 10), expected_revision=2, generation=1
    )
    second = harness.repo.apply_observation(
        receipt(first, "heartbeat", 11, observed_at="2026-10-24T15:59:00+00:00"),
        expected_revision=3,
        generation=1,
    )
    assert json.loads(second.payload_json)["last_heartbeat_at"] == STAMP
    old = harness.repo.apply_observation(
        receipt(second, "heartbeat", 9), expected_revision=1, generation=1
    )
    assert old == second


def test_collection_refusal_failure_replay_do_not_revive(harness: Harness) -> None:
    done = harness.finish(harness.start())
    refused = harness.repo.record_collection(
        done.key,
        "refused",
        done.payload_json,
        expected_revision=done.revision,
        generation=1,
    )
    assert refused.outcome == "completed"
    assert json.loads(refused.payload_json)["status"] == "completed"
    failed = harness.repo.record_collection(
        done.key,
        "failed",
        refused.payload_json,
        expected_revision=refused.revision,
        generation=1,
    )
    assert json.loads(failed.payload_json)["status"] == "failed"
    assert harness.repo.current().records == ()
    with pytest.raises(ExecutionError, match="stale_revision"):
        harness.repo.record_collection(
            done.key,
            "collected",
            done.payload_json,
            expected_revision=done.revision,
            generation=1,
        )
    late = harness.repo.apply_observation(
        receipt(failed, "heartbeat", 5), expected_revision=failed.revision, generation=1
    )
    assert late.phase == "absent" and late.history_seq == done.history_seq
    assert harness.repo.current().records == ()


def test_pid_birth_mismatch_never_attaches(harness: Harness) -> None:
    start = harness.start()
    attached = harness.repo.apply_observation(
        receipt(start, "process"), expected_revision=2, generation=1
    )
    for kind in ("exit", "heartbeat", "absence"):
        observation = ExecutionObservation(
            attached.key,
            attached.launch_token or "",
            kind,
            0,
            "sha256:" + "c" * 64,
            replace(PROCESS, birth_id="replacement"),
            STAMP,
            tree_absent=True,
        )
        with pytest.raises(ExecutionError, match="execution_identity_conflict"):
            harness.repo.apply_observation(
                observation, expected_revision=3, generation=1
            )
    assert harness.repo.current().records == (attached,)


def test_real_os_birth_and_tree_cannot_be_inferred() -> None:
    current = process_identity.capture_process(os.getpid())
    assert current is not None and current.birth_id
    assert process_identity.probe_process(current) == "same"
    assert process_identity.tree_absence(current) is False
    reused = replace(current, birth_id="old-incarnation", tree_id="verified-owned-tree")
    assert process_identity.probe_process(reused) == "absent"
    assert process_identity.tree_absence(reused) is None
    assert (
        process_identity.tree_absence(reused, owned_tree_probe=lambda _: False) is False
    )
    assert (
        process_identity.tree_absence(reused, owned_tree_probe=lambda _: True) is True
    )
    assert (
        process_identity.probe_process(replace(current, host_id="foreign-host"))
        == "unknown"
    )


def test_denied_process_probe_remains_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(pid: int, *, tree_id: str | None = None) -> None:
        raise ExecutionError("execution_activity_unknown")

    monkeypatch.setattr(process_identity, "capture_process", denied)
    identity = replace(PROCESS, host_id=socket.gethostname())
    assert process_identity.probe_process(identity) == "unknown"
    assert (
        process_identity.tree_absence(identity, owned_tree_probe=lambda _: True) is None
    )


def test_linux_parser_handles_comm_parentheses(monkeypatch: pytest.MonkeyPatch) -> None:
    def text(path: Path, encoding: str) -> str:
        if path.name == "boot_id":
            return "boot-identity\n"
        return "123 (worker (odd name)) S " + " ".join(["0"] * 18 + ["56789", "0", "0"])

    monkeypatch.setattr(Path, "read_text", text)
    observed = process_identity._linux_identity(123, "host", None)
    assert observed is not None
    assert (
        observed.birth_id == "linux-start-ticks:56789"
        and observed.boot_id == "boot-identity"
    )
