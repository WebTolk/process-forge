"""Narrow operation contracts for explicit SQLite and journal maintenance."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal, Protocol

JsonObject = dict[str, Any]
SourceKind = Literal["events", "raw"]
JournalSource = tuple[SourceKind, Path]
JournalRow = tuple[SourceKind, JsonObject, str]


class MaintenanceError(ValueError):
    """Report a stable maintenance failure without exposing record contents."""

    def __init__(self, code: str) -> None:
        """Keep the machine-readable failure code as the exception message."""
        self.code = code
        super().__init__(code)


class BackupPort(Protocol):
    """Provide verified single-database backup and exclusive restore operations."""

    def create(self, source: Path, bundle: Path) -> JsonObject:
        """Create a new consistent backup bundle without changing its source."""
        ...

    def verify(self, bundle: Path) -> JsonObject:
        """Validate a bundle before any consumer relies on its contents."""
        ...

    def restore(self, bundle: Path, destination: Path) -> JsonObject:
        """Restore a verified backup into an exclusively created destination."""
        ...


class JournalScanPort(Protocol):
    """Read legacy journal sources and preserve invalid records as evidence."""

    def discover(
        self, project: Path, workplace: Path
    ) -> tuple[Path, list[JournalSource]]:
        """Return the actual project flow root and its supported legacy sources."""
        ...

    def rows(
        self,
        sources: list[JournalSource],
        project: Path,
        report: JsonObject,
        *,
        skip_invalid: bool = False,
        quarantine_dir: Path | None = None,
    ) -> Iterator[JournalRow]:
        """Yield valid rows while recording source and corruption observations."""
        ...

    def preflight(
        self,
        project: Path,
        workplace: Path,
        *,
        skip_invalid: bool = False,
        evidence_dir: Path | None = None,
    ) -> JsonObject:
        """Validate identities and source bytes before a migration can start."""
        ...
