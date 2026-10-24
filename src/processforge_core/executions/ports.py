"""Synchronous domain ports; no SQL sessions, paths or CLI payload ownership."""

from __future__ import annotations

from typing import Literal, Protocol

from .model import (
    CurrentSnapshot,
    ExecutionKey,
    ExecutionObservation,
    ExecutionRecord,
    HistoryPage,
    StorageReadiness,
)


class ExecutionRepository(Protocol):
    """Persist project-scoped execution facts with generation/revision CAS.

    Each mutation is atomic. Stale revisions/generations refuse; identical
    admitted receipts are no-ops even after revision advances. No transaction
    spans process creation, waits, signals, output reads or projection I/O.
    """

    def readiness(self, *, deadline: float | None = None) -> StorageReadiness:
        """Read authority without initialization; deadline is absolute monotonic."""
        ...

    def load_latest(self, run_id: str, task_id: str) -> ExecutionRecord | None:
        """Read an indexed head; never use latest to target old-attempt evidence."""
        ...

    def load(self, key: ExecutionKey) -> ExecutionRecord | None:
        """Read the exact preserved attempt identity within this project."""
        ...

    def allocate_attempt(
        self, run_id: str, task_id: str, payload_json: str, *, generation: int
    ) -> ExecutionRecord:
        """Allocate a prepared attempt from heads; refuse current task ownership."""
        ...

    def reserve_start(
        self,
        key: ExecutionKey,
        *,
        expected_revision: int,
        generation: int,
        launch_token: str,
    ) -> ExecutionRecord:
        """Commit starting/current ownership before the caller creates a child."""
        ...

    def apply_observation(
        self,
        observation: ExecutionObservation,
        *,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Admit exact-launch evidence with deduplication and immutable birth ID."""
        ...

    def request_stop(
        self,
        key: ExecutionKey,
        *,
        launch_token: str,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Record stopping intent; signal success alone never proves absence."""
        ...

    def record_collection(
        self,
        key: ExecutionKey,
        collection: Literal["collected", "failed", "refused"],
        payload_json: str,
        *,
        expected_revision: int,
        generation: int,
    ) -> ExecutionRecord:
        """Record artifact collection separately from physical process activity."""
        ...

    def current(
        self, *, limit: int = 128, deadline: float | None = None
    ) -> CurrentSnapshot:
        """Read only current rows in one snapshot; overflow/unknown is incomplete.

        Limits are exact integers 1..1000. Never reconcile, scan history, read
        terminal receipts or send signals on this bounded observation path.
        """
        ...

    def page_history(
        self, *, after: int = 0, high_water: int | None = None, limit: int = 256
    ) -> HistoryPage:
        """Page stable absence sequence order with a first-page high water.

        Limits are exact integers 1..1000. Later collection does not reorder
        history; the returned after cursor is None when no further page remains.
        """
        ...

    def ack_projection(
        self, key: ExecutionKey, *, revision: int, generation: int
    ) -> bool:
        """CAS-ack only matching latest projection; lifecycle revision stays put."""
        ...
