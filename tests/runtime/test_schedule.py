"""Actual job cadence, accumulated-history reads, and persistent job faults."""

from __future__ import annotations

import threading
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from pf_runtime import host, service

from processforge_core.documents.parse_cache import YamlParseCache
from processforge_core.runtime.schedule import RuntimeSchedule
from processforge_core.work.consistency import RunTaskInputReader


def test_schedule_is_per_scope_and_starts_period_after_completion() -> None:
    now = [100.0]
    schedule = RuntimeSchedule(clock=lambda: now[0])
    assert all(type(period) is int for period in schedule.periods().values())
    assert schedule.due("projection", "first")
    now[0] = 140.0  # A slow pass must not create catch-up work.
    schedule.complete("projection", "first")
    assert not schedule.due("projection", "first")
    assert schedule.due("projection", "new-project")
    now[0] = 169.99
    assert not schedule.due("projection", "first")
    now[0] = 170.0
    assert schedule.due("projection", "first")
    schedule.retain_scopes([])
    assert schedule.due("projection", "first")
    periods = schedule.periods()
    periods["projection"] = 0
    assert schedule.periods()["projection"] == 30


@pytest.mark.parametrize("period", [0, -1, float("inf"), float("nan")])
def test_schedule_refuses_unbounded_cadence(period: float) -> None:
    with pytest.raises(ValueError):
        RuntimeSchedule(periods={"job": period})


def test_cache_shares_policy_within_the_existing_memory_limit() -> None:
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    cache = YamlParseCache(max_bytes=50000, max_entry_bytes=50000)
    policy = cache.policy(loader, yaml.load)
    assert policy is not None
    for _ in range(2):
        for number in range(40):
            value, _hit = cache.load(
                f"id: task-{number}\n", loader, yaml.load, policy=policy
            )
            assert value == {"id": f"task-{number}"}
    assert cache.info()["parses"] == 40
    assert cache.info()["hits"] == 40
    assert cache.info()["evictions"] == 0
    assert cache.info()["bytes"] <= 50000
    # The last reference drops the shared policy too; replacement and clear
    # must not accumulate definitions beyond the bounded retained entries.
    cache.max_entries = 1
    for number in range(40, 50):
        cache.load(f"id: task-{number}\n", loader, yaml.load, policy=policy)
        assert cache.info()["entries"] == 1
        assert cache.info()["bytes"] <= 50000
    cache.clear()
    assert cache.info()["bytes"] == 0 and cache.info()["entries"] == 0


def test_active_tasks_match_legacy_and_skip_full_terminal_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignments = tmp_path / ".pf/assignments"
    assignments.mkdir(parents=True)
    cases: list[dict[str, Any]] = [
        {"id": "open", "status": "open", "history": [1]},
        {"id": "done", "status": "done", "history": [2]},
        {"id": "complete", "status": "completed"},
        {"id": "cancel", "status": "cancelled"},
        {"id": "fail", "status": "failed"},
        {"id": 123, "status": "blocked"},
        {"id": "unknown", "status": None},
        {"status": "open"},
    ]
    for index, data in enumerate(cases):
        (assignments / f"{index}.yaml").write_text(
            yaml.safe_dump(data), encoding="utf-8"
        )
    (assignments / "bad.yaml").write_text("history: [broken", encoding="utf-8")
    inputs = RunTaskInputReader()
    original = inputs._yaml_documents.load
    full_reads = []

    def load(path: Path) -> dict:
        full_reads.append(path.name)
        return original(path)

    monkeypatch.setattr(
        type(inputs._yaml_documents), "load", lambda _self, path: load(path)
    )
    terminal = {"done", "completed", "cancelled", "failed"}
    assert list(inputs.active_tasks(tmp_path)) == [
        data
        for data in cases
        if data.get("id") and str(data.get("status") or "") not in terminal
    ]
    assert full_reads == ["0.yaml", "5.yaml", "6.yaml"]
    # Recheck the full read instead of yielding the earlier header snapshot.
    monkeypatch.setattr(
        type(inputs._yaml_documents),
        "load",
        lambda *_: {"id": "finished", "status": "done"},
    )
    assert list(inputs.active_tasks(tmp_path)) == []


def test_runtime_obeys_core_periods_and_keeps_fault_until_same_job_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [0.0]
    roots = [tmp_path / "first", tmp_path / "second"]
    runtime = service.RuntimeProcess.__new__(service.RuntimeProcess)
    runtime.workplace_root = tmp_path
    presence = []
    runtime.core = SimpleNamespace(
        update_stale_agent_presence=lambda *_: presence.append(now[0])
    )
    runtime._schedule = RuntimeSchedule(clock=lambda: now[0])
    runtime._scheduler_errors = {}
    runtime._project_errors = {}
    runtime.state_lock = threading.RLock()
    runtime.state = {"status": "ready"}

    def known() -> list[Path]:
        runtime._project_errors = {}
        return roots

    monkeypatch.setattr(runtime, "known_project_roots", known)
    monkeypatch.setattr(runtime, "observe_temporary_files", lambda _: {})
    calls = []
    fail_projection = [True]

    def tick(_workplace, selected, _core, **flags):
        calls.append((now[0], selected[0].name, flags))
        if flags["projection"] and selected[0] == roots[0] and fail_projection[0]:
            raise OSError("projection unavailable")
        return {"projects": [], "scheduler_status": "ok"}, 1  # preserved task failure

    monkeypatch.setattr(host, "tick_payload", tick)
    runtime.scheduler_pass()
    assert runtime.state["health"] == "degraded"
    for tick_time in range(2, 31, 2):
        now[0] = float(tick_time)
        if tick_time == 30:
            fail_projection[0] = False
        runtime.scheduler_pass()
        if tick_time < 30:
            assert runtime.state["health"] == "degraded"
            assert runtime.state["scheduler"]["jobs"]["projection"]["last_run"]
    assert runtime.state["health"] == "ready"
    for name in ("first", "second"):
        rows = [flags for _, root, flags in calls if root == name]
        assert sum(row["director"] for row in rows) == 4
        assert sum(row["inspector"] for row in rows) == 6
        assert sum(row["projection"] for row in rows) == 2
        assert not any(row["presence"] for row in rows)
    assert presence == [0, 6, 12, 18, 24, 30]
    roots.append(tmp_path / "new")
    now[0] = 32
    runtime.scheduler_pass()
    assert calls[-1][1] == "new" and calls[-1][2]["projection"]
    assert runtime.state["health"] == "ready"


def test_host_skips_optional_jobs_without_skipping_routing_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The existing admission regressions exercise the default path; this checks
    # that cadence flags only skip observational work, not publication guards.
    import pf_native_control

    from processforge_core.project import configuration_inputs

    monkeypatch.setattr(pf_native_control, "current_entry", lambda: None)
    monkeypatch.setattr(
        configuration_inputs, "configuration_operation", lambda *_: nullcontext()
    )
    monkeypatch.setattr(host, "registration_admission", lambda *_: nullcontext())
    routed = []

    def route(*_args: Any) -> dict[str, Any]:
        routed.append(1)
        return {"project_id": "test", "effective_mode": "simple"}

    monkeypatch.setattr(host, "route_project", route)
    monkeypatch.setattr(host, "load_state", lambda *_: {})
    monkeypatch.setattr(host, "remember_project", lambda *_: None)
    monkeypatch.setattr(host, "save_state", lambda *_: None)
    monkeypatch.setattr(
        host,
        "refresh_stage_obligations",
        lambda *_: pytest.fail("projection ran early"),
    )
    core = SimpleNamespace(
        update_stale_agent_presence=lambda *_: pytest.fail("presence repeated"),
        flush_pending_event_dispatches=lambda *_: None,
    )
    result, code = host.tick_payload(
        tmp_path, [tmp_path], core, projection=False, presence=False
    )
    assert code == 0 and result["scheduler_status"] == "ok" and len(routed) == 3
