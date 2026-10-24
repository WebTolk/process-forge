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
class MigrationSafety:
    """Trusted host verdict, never inferred from an operator confirmation flag.

    Generation pins the host ownership/routing/capability evidence. Proven means
    old writers, publication gaps and all owned physical trees were excluded for
    the exact supplied context. Evidence references are private, not report text.
    """

    state: Literal["proven", "active", "unknown"]
    generation: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionMigrationContext:
    """Exact host-authorized pins to revalidate under admission.

    A verifier must resolve enrollment and compare workplace_root, inspect the
    matching Runtime instance/routing, capability and old-writer exclusion,
    pre-spawn gaps and complete process trees. None means verified standalone,
    not a fallback when an enrolled workplace is inaccessible.
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
    """Recheck actual host evidence; return unknown on any unavailable proof.

    Engine invokes freeze/resume/cutover while holding real admission gates.
    A missing verifier or changed generation refuses migration. Implementations
    must not treat terminal text, empty registry, TTL, PID-only or CLI flags as
    proof. They must keep excluded legacy entrypoints disabled through resume.
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
