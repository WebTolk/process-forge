"""Narrow operation contracts for explicit SQLite and journal maintenance."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

JsonObject = dict[str, Any]
SourceKind = Literal["events", "raw"]
JournalSource = tuple[SourceKind, Path]
JournalRow = tuple[SourceKind, JsonObject, str]


@dataclass(frozen=True)
class StoreTarget:
    """Host-authorized physical target; paths and identities confer no access."""

    kind: Literal["events", "raw", "accounting", "search", "main"]
    target: Path
    target_relative_path: str
    scope: Literal["project", "workplace"]
    owner_id: str


@dataclass(frozen=True)
class StorageMigrationContext:
    """Exact selected roots and targets, never discovered by scanning a device."""

    project_root: Path | None
    workplace_root: Path | None
    device_config_path: Path
    targets: tuple[StoreTarget, ...]
    unqualified_targets: tuple[
        tuple[Literal["raw", "search", "accounting"], Path], ...
    ] = ()


@dataclass(frozen=True)
class MigrationSafety:
    """Admission for the selected maintenance operation and responsibility model.

    Generation pins routing and identity across freeze/resume/cutover. In Garage,
    the operator stops writers; in Forge, the updater stops the PF executor.
    The host also holds admission and rejects a known running Runtime. Historical
    process enrollment is not a prerequisite. Evidence references are private.
    """

    state: Literal["proven", "active", "unknown"]
    generation: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionMigrationContext:
    """Exact host-authorized pins to revalidate under admission.

    A verifier resolves and compares routing/owners and validates the selected
    maintenance admission. None means standalone, never a fallback when an
    enrolled workplace is inaccessible.
    """

    project_root: Path
    workplace_root: Path | None
    project_id: str
    store_id: str
    target_relative_path: str
    source_generation: int
    target_generation: int
    plan_checksum: str
    manifest_checksum: str
    phase: Literal["inspect", "freeze", "resume", "cutover"]


class ExecutionMigrationVerifier(Protocol):
    """Recheck the host's maintenance admission and pinned routing.

    Engine invokes freeze/resume/cutover while holding real admission gates.
    A missing verifier or changed generation refuses migration. Implementations
    must retain data and identity checks. Operator confirmation supplies the
    responsibility for other writers; it does not bypass admission or source
    verification, and does not claim OS isolation of historical processes.
    """

    def __call__(self, context: ExecutionMigrationContext) -> MigrationSafety:
        """Verify the complete context and return its current evidence epoch."""
        ...


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
