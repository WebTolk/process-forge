"""Interprocess admission primitives; runtime policy remains in host composition."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from ..executions.model import ExecutionError
from ..project.metadata import ProjectMetadataReader


class ExecutionAdmission:
    """Reuse the host's permanent-guard registry lock without importing tools.

    Gate order is workplace, project, existing task lock, SQL transaction.
    The caller verifies enrollment, readiness, instance and stopping fence inside
    the gate; these locks themselves grant no routing or launch permission.
    Shutdown holds the workplace gate while the caller validates instance/routing,
    takes sorted project gates and publishes durable stopping before release.
    No memory lock may be held while waiting to acquire these gates.
    """

    def __init__(
        self, registry_lock: Callable[..., AbstractContextManager[object]]
    ) -> None:
        self.registry_lock = registry_lock

    @contextmanager
    def _gate(self, path: Path, deadline: float | None) -> Iterator[None]:
        timeout = 30.0
        if deadline is not None:
            if not math.isfinite(deadline):
                raise ValueError("invalid deadline")
            timeout = min(timeout, deadline - time.monotonic())
            if timeout <= 0:
                raise ExecutionError("execution_activity_unknown")
        try:
            with self.registry_lock(
                path, timeout_seconds=timeout, stale_after_seconds=0
            ):
                if deadline is not None and time.monotonic() >= deadline:
                    raise ExecutionError("execution_activity_unknown")
                yield
        except (OSError, TimeoutError, SystemExit):
            raise ExecutionError("execution_activity_unknown") from None

    @contextmanager
    def start(
        self,
        project_root: Path,
        workplace_root: Path | None,
        *,
        deadline: float | None = None,
    ) -> Iterator[None]:
        """Serialize reservation with shutdown/registration using one budget.

        Enrollment resolution is mandatory before calling; an enrolled project
        must never supply None merely because its workplace is unavailable.
        """
        project_gate = (
            ProjectMetadataReader(project_root).flow_root()
            / "runtime"
            / "execution-admission"
        )
        if workplace_root is None:
            with self._gate(project_gate, deadline):
                yield
        else:
            with self._gate(
                workplace_root / "runtime" / "pf-runtime" / "execution-admission",
                deadline,
            ):
                with self._gate(project_gate, deadline):
                    yield

    @contextmanager
    def shutdown(
        self, workplace_root: Path, *, expected_instance_id: str, deadline: float
    ) -> Iterator[None]:
        """Hold workplace admission for the caller's exact-instance shutdown check.

        Expected instance is required, but only the host can compare it to its
        authoritative state. This primitive does not clear/recover a stopping
        owner or infer death from elapsed time.
        """
        if (
            not isinstance(expected_instance_id, str)
            or not expected_instance_id.strip()
            or "\x00" in expected_instance_id
        ):
            raise ExecutionError("execution_activity_unknown")
        with self._gate(
            workplace_root / "runtime" / "pf-runtime" / "execution-admission", deadline
        ):
            yield

    @contextmanager
    def maintenance(
        self, project_root: Path, workplace_root: Path | None
    ) -> Iterator[None]:
        """Acquire the same gates for explicit maintenance/binding publication."""
        with self.start(project_root, workplace_root):
            yield
