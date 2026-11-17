"""Controlled timing/fault regressions; these do not qualify native capability.

The public CLI/Runtime event tests remain the real platform qualification.
Only this module substitutes entry, process, backend and monotonic clock.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pf_native_control as native
import pytest


class Probe:
    """Deterministic root/backend observations with an explicit simulated clock."""

    def __init__(self) -> None:
        self.now = 100.0
        self.root_delay = 0.0
        self.query_delay = 0.0
        self.returncode = 0
        self.wait_error: Exception | None = None
        self.query: Callable[[], int] = lambda: 0
        self.waits: list[float] = []
        self.sleeps: list[float] = []
        self.queries: list[float] = []
        self.closed = 0
        self.stops = 0
        self.live = False
        self.stop_error: Exception | None = None
        self.close_error: Exception | None = None

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        assert 0 < seconds <= 0.01
        self.sleeps.append(seconds)
        self.now += seconds

    def wait(self, *, timeout: float) -> int:
        self.waits.append(timeout)
        if len(self.waits) == 1:
            self.now += self.root_delay
            if self.wait_error is not None:
                self.live = True
                raise self.wait_error
        return self.returncode

    def active(self) -> int:
        assert self.closed == 0, "ownership must be retained during observation"
        self.queries.append(self.now)
        self.now += self.query_delay
        return self.query()

    def stop(self, *, deadline: float) -> bool:
        self.stops += 1
        if self.stop_error is not None:
            raise self.stop_error
        self.live = False
        return True

    def close(self) -> None:
        self.closed += 1
        if self.close_error is not None:
            raise self.close_error


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> Probe:
    probe = Probe()
    process = SimpleNamespace(
        native_job=probe, wait=probe.wait, poll=lambda: None if probe.live else 0
    )
    monkeypatch.setattr(native, "_ENTRY", SimpleNamespace(publication=object()))
    monkeypatch.setattr(native, "os", SimpleNamespace(name="nt", environ={}))
    monkeypatch.setattr(
        native, "sys", SimpleNamespace(platform="win32", executable=sys.executable)
    )
    monkeypatch.setattr(native, "time", probe)
    monkeypatch.setattr(native, "spawn_owned", lambda *args, **kwargs: process)
    return probe


def _facts(caplog: pytest.LogCaptureFixture) -> dict[str, Any]:
    messages = [
        record.getMessage().split("PF_NATIVE_CAPABILITY ", 1)[1]
        for record in caplog.records
        if "PF_NATIVE_CAPABILITY " in record.getMessage()
    ]
    assert messages
    return json.loads(messages[-1])


def test_controlled_delayed_retirement_requires_actual_empty_observation(
    probe: Probe, caplog: pytest.LogCaptureFixture
) -> None:
    values = iter([1, 1, 0])
    probe.root_delay = 4.5
    probe.query = lambda: next(values)
    assert native.supports_owned_execution()
    assert len(probe.queries) == 3
    assert probe.now == pytest.approx(104.52)
    assert probe.closed == 1 and probe.stops == 0
    facts = _facts(caplog)
    assert facts["reason"] == "job_retired_after_wait"
    assert facts["first_active"] == 1 and facts["active"] == 0
    assert facts["observations"] == 3
    assert facts["root_wait_ms"] == 4500 and facts["elapsed_ms"] == 4520


def test_controlled_persistent_activity_refuses_at_existing_deadline(
    probe: Probe, caplog: pytest.LogCaptureFixture
) -> None:
    probe.root_delay = 4.975
    probe.query = lambda: 1
    assert not native.supports_owned_execution()
    assert probe.now == pytest.approx(105)
    assert len(probe.queries) == 3
    assert probe.closed == 1
    facts = _facts(caplog)
    assert facts["reason"] == "job_retirement_timeout"
    assert facts["active"] == 1 and facts["first_active"] == 1
    assert facts["elapsed_ms"] == 5000


def test_controlled_root_wait_does_not_restart_retirement_budget(
    probe: Probe,
) -> None:
    values = iter([1, 0])
    probe.root_delay = 4.995
    probe.query = lambda: next(values)
    assert not native.supports_owned_execution()
    assert len(probe.queries) == 1
    assert next(values) == 0, "an empty result after the deadline cannot qualify"
    assert probe.now == pytest.approx(105)
    assert probe.waits == [5]
    assert probe.sleeps == pytest.approx([0.005])
    assert probe.closed == 1


def test_controlled_empty_query_finishing_after_deadline_refuses(probe: Probe) -> None:
    probe.root_delay = 4.99
    probe.query_delay = 0.02
    assert not native.supports_owned_execution()
    assert len(probe.queries) == 1 and probe.closed == 1


def test_controlled_root_wait_exhausts_deadline_before_first_query(
    probe: Probe,
) -> None:
    probe.root_delay = 5
    assert not native.supports_owned_execution()
    assert probe.queries == [] and probe.closed == 1


@pytest.mark.parametrize(
    "error", [OSError(5, "private-path"), native.NativeControlError()]
)
def test_controlled_query_error_refuses_and_redacts(
    probe: Probe, caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    def refuse() -> int:
        raise error

    probe.query = refuse
    assert not native.supports_owned_execution()
    assert probe.closed == 1
    facts = _facts(caplog)
    assert facts["reason"] == "probe_exception"
    assert facts["failures"][0]["type"] == type(error).__name__
    assert "private-path" not in caplog.text


def test_controlled_nonzero_root_refuses_without_query(
    probe: Probe, caplog: pytest.LogCaptureFixture
) -> None:
    probe.returncode = 7
    assert not native.supports_owned_execution()
    assert probe.queries == [] and probe.closed == 1
    assert _facts(caplog)["returncode"] == 7


def test_controlled_root_timeout_preserves_cleanup(
    probe: Probe, caplog: pytest.LogCaptureFixture
) -> None:
    probe.root_delay = 5
    probe.wait_error = subprocess.TimeoutExpired("private-command", 5)
    assert not native.supports_owned_execution()
    assert probe.stops == 1 and probe.closed == 1
    assert len(probe.waits) == 2 and probe.queries == []
    assert _facts(caplog)["reason"] == "probe_exception"
    assert "private-command" not in caplog.text


def test_controlled_cleanup_failure_still_closes_ownership(probe: Probe) -> None:
    probe.wait_error = subprocess.TimeoutExpired("private-command", 5)
    probe.stop_error = OSError(5, "private-stop")
    assert not native.supports_owned_execution()
    assert probe.stops == 1 and probe.closed == 1


def test_controlled_close_failure_refuses(probe: Probe) -> None:
    probe.close_error = OSError(5, "private-close")
    assert not native.supports_owned_execution()
    assert probe.closed == 1


@pytest.mark.parametrize("entry", [None, SimpleNamespace(publication=None)])
def test_controlled_missing_publication_cannot_probe(
    probe: Probe, monkeypatch: pytest.MonkeyPatch, entry: Any
) -> None:
    monkeypatch.setattr(native, "_ENTRY", entry)
    assert not native.supports_owned_execution()
    assert probe.waits == [] and probe.queries == [] and probe.closed == 0


def test_controlled_linux_inherited_namespace_keeps_existing_semantics(
    probe: Probe, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pf_linux_native_control as linux

    monkeypatch.setattr(
        native, "sys", SimpleNamespace(platform="linux", executable=sys.executable)
    )
    monkeypatch.setattr(linux, "inherited", lambda environment: object())
    assert native.supports_owned_execution()
    assert probe.waits == [] and probe.queries == [] and probe.closed == 0
