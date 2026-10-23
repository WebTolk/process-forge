"""Expose a cold maintenance job for explicit future scheduler invocation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class _MaintenanceService(Protocol):
    """Describe the single maintenance operation used by the job."""

    def run(self, *, reason: str, verify_files: bool) -> dict[str, Any]:
        """Run authorized maintenance and return its canonical result."""
        ...


class IndexMaintenanceJob:
    """Delegate explicit executions to the shared workplace maintenance service.

    This job does not register or schedule itself. Its caller must have separate
    authorization for workplace maintenance before invoking ``execute``.
    """

    def __init__(
        self,
        workplace_root: Path,
        *,
        distribution_root: Path | None = None,
        maintenance_service: _MaintenanceService | None = None,
    ) -> None:
        """Retain configuration without resolving paths or creating resources.

        Args:
            workplace_root: Workplace target for the shared maintenance service.
            distribution_root: Optional distribution passed to that service.
            maintenance_service: Borrowed narrow dependency for isolated callers.
        """
        self._workplace_root = workplace_root
        self._distribution_root = distribution_root
        self._maintenance_service = maintenance_service

    def execute(self) -> dict[str, Any]:
        """Run one maintenance pass and return its result without transformation.

        Default composition creates an operation-local canonical service only
        here. That service owns indexing, serialization and durable recovery.
        Failure payloads and exceptions propagate unchanged; this job neither
        logs exception text nor retries automatically.
        """
        service = self._maintenance_service
        if service is None:
            from processforge_core.resources.index_maintenance import (
                WorkplaceIndexMaintenanceService,
            )

            service = WorkplaceIndexMaintenanceService(
                self._workplace_root,
                distribution_root=self._distribution_root,
            )
        return service.run(reason="scheduler", verify_files=True)
