"""Describe the index operations consumed by explicit maintenance.

The existing ResourceSearchIndex implements this structural port directly.
This is a search backend boundary, not a connection pool or database layer.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


class ResourceIndexBackend(Protocol):
    """Supply existing mutation operations for one explicitly supplied snapshot."""

    def mark_dirty(self, *, reason: str = "dirty") -> dict[str, Any]:
        """Invalidate the supplied scope while the canonical writer lock is held."""
        ...

    def refresh(self) -> dict[str, Any]:
        """Refresh only resources selected by the backend's snapshot."""
        ...

    def rebuild(self) -> dict[str, Any]:
        """Rebuild using the existing backend's reconciliation semantics."""
        ...

    def maintenance_tick(self, *, verify_files: bool = True) -> dict[str, Any]:
        """Perform one existing maintenance pass and return before/after state."""
        ...


ResourceIndexBackendFactory = Callable[
    [Path, dict[str, Any], Path], ResourceIndexBackend
]
