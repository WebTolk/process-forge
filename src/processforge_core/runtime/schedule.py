"""Monotonic Runtime job cadence, independent of host polling and wall time."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Mapping


class RuntimeSchedule:
    PERIODS = {"ledger": 5, "director": 10, "inspector": 5, "projection": 30}

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        periods: Mapping[str, float] | None = None,
    ) -> None:
        self._clock = clock
        self._periods = dict(self.PERIODS if periods is None else periods)
        if any(
            not math.isfinite(value) or value <= 0 for value in self._periods.values()
        ):
            raise ValueError("Runtime job periods must be finite and positive")
        self._completed: dict[tuple[str, str], float] = {}

    def periods(self) -> dict[str, float]:
        return dict(self._periods)

    def due(self, job: str, scope: str = "") -> bool:
        period = self._periods[job]
        previous = self._completed.get((job, scope))
        return previous is None or self._clock() - previous >= period

    def complete(self, job: str, scope: str = "") -> None:
        # Failed attempts also complete their cadence. Slow jobs never trigger
        # a catch-up loop; the next period starts after the attempt finishes.
        self._periods[job]
        self._completed[job, scope] = self._clock()

    def retain_scopes(self, scopes: Iterable[str]) -> None:
        keep = {"", *scopes}
        self._completed = {
            key: value for key, value in self._completed.items() if key[1] in keep
        }
