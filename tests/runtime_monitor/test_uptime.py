"""Calendar uptime and terminal rendering regressions."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture(scope="module")
def monitor_module() -> Iterator[ModuleType]:
    """Load the actual monitor without starting a Runtime or terminal."""
    root = Path(__file__).resolve().parents[2]
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(root / "src"))
        patch.syspath_prepend(str(root / "tools"))
        yield importlib.import_module("pf_runtime.monitor")


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00/00/00/00/00"),
        (59.9, "00/00/00/00/00"),
        (60, "00/00/00/00/01"),
        (3599, "00/00/00/00/59"),
        (3600, "00/00/00/01/00"),
        (86399, "00/00/00/23/59"),
        (86400, "00/00/01/00/00"),
        (184500.0, "00/00/02/03/15"),
    ],
)
def test_elapsed_minutes(
    monitor_module: ModuleType, seconds: float, expected: str
) -> None:
    assert (
        monitor_module.format_uptime(seconds, "2026-10-20T12:00:00+00:00") == expected
    )


@pytest.mark.parametrize(
    ("started", "observed", "expected"),
    [
        ("2025-01-31T10:00:00Z", "2025-02-28T10:00:00Z", "00/01/00/00/00"),
        ("2024-01-31T10:00:00Z", "2024-02-29T10:00:00Z", "00/01/00/00/00"),
        ("2025-01-31T10:00:00Z", "2025-02-28T09:59:00Z", "00/00/27/23/59"),
        ("2024-02-29T10:00:00Z", "2025-02-28T10:00:00Z", "01/00/00/00/00"),
        ("2024-02-29T10:00:00Z", "2025-02-28T09:59:00Z", "00/11/29/23/59"),
        ("2023-12-31T23:00:00Z", "2024-02-29T23:00:00Z", "00/02/00/00/00"),
        ("1900-01-01T00:00:00Z", "2000-01-01T00:00:00Z", "100/00/00/00/00"),
        (
            "2025-01-31T22:00:00+02:00",
            "2025-02-28T21:00:00+01:00",
            "00/01/00/00/00",
        ),
        (
            "2025-01-31T23:30:00Z",
            "2025-02-28T23:30:00-03:00",
            "00/01/00/03/00",
        ),
    ],
)
def test_calendar_anniversaries(
    monitor_module: ModuleType, started: str, observed: str, expected: str
) -> None:
    beginning = datetime.fromisoformat(started)
    ending = datetime.fromisoformat(observed)
    seconds = (ending - beginning).total_seconds()
    assert monitor_module.format_uptime(seconds, observed) == expected


@pytest.mark.parametrize(
    "seconds",
    [None, True, False, -1, "60", float("nan"), float("inf"), 1e300, 10**400],
)
def test_unknown_or_invalid_duration(
    monitor_module: ModuleType, seconds: object
) -> None:
    assert monitor_module.format_uptime(seconds, "2026-10-20T12:00:00Z") == "unknown"


@pytest.mark.parametrize(
    "observed",
    [None, "", "invalid", "2026-10-20T12:00:00", "99999-01-01T00:00:00Z"],
)
def test_invalid_observation(monitor_module: ModuleType, observed: object) -> None:
    assert monitor_module.format_uptime(60, observed) == "unknown"


def test_datetime_underflow(monitor_module: ModuleType) -> None:
    assert monitor_module.format_uptime(1, "0001-01-01T00:00:00Z") == "unknown"


@pytest.mark.parametrize("seconds", [184500.0, None])
@pytest.mark.parametrize("columns", [35, 80])
def test_render_preserves_snapshot_and_numeric_metric(
    monitor_module: ModuleType, seconds: float | None, columns: int
) -> None:
    snapshot = {
        "observed_at": "2026-10-20T12:00:00Z",
        "runtime": {
            "lifecycle": "ready",
            "health": "ready",
            "owner_pid": 123,
            "instance_version": "1.3.0-alpha1",
            "uptime_seconds": seconds,
        },
        "workplace": "test",
        "cli_version": "1.3.0-alpha1",
        "configuration": {"interval_seconds": 10},
        "registrations": {"projects": 1},
        "issues": [],
    }
    before = deepcopy(snapshot)
    rows = monitor_module.render(snapshot, columns, 24, ascii_only=True)
    uptime = next(row for row in rows if row.startswith("Uptime:"))
    assert ("00/00/02/03/15" if seconds is not None else "unknown") in uptime
    if columns == 80:
        assert "y/mo/d/h/min" in uptime
    assert all(monitor_module.cell_width(row) < columns for row in rows)
    assert snapshot == before
