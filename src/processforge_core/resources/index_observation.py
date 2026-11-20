"""Observe the workplace search index without requesting maintenance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .catalog_read import WorkplaceSearchCatalogReader
from .local_search import SCHEMA_VERSION, LocalSearchError, ResourceSearchIndex

_SAFE_INDEX_ERRORS = frozenset(
    {
        "allowed_resources_changed",
        "document_fingerprint_changed",
        "document_read_failed",
        "document_scan_failed",
        "fts5_unavailable",
        "index_schema_missing",
        "index_schema_mismatch",
        "index_unreadable",
        "resource_not_indexed",
        "scope_not_indexed",
        "snapshot_checksum_changed",
    }
)
_PUBLIC_STATUS_FIELDS = frozenset(
    {
        "schema_version",
        "kind",
        "status",
        "generation",
        "resource_count",
        "document_count",
        "stale_resource_count",
        "failed_file_count",
        "last_successful_refresh",
        "last_full_reconciliation",
        "error",
        "sqlite",
    }
)


@dataclass(frozen=True)
class _MaintenanceState:
    """Keep a private record identity to detect a completed concurrent pass."""

    status: str | None
    fingerprint: str | None = None
    invalidation_token: str | None = None


def maintenance_state_path(workplace_root: Path) -> Path:
    """Return the durable maintenance record path without accessing it."""
    return workplace_root / "runtime" / "search" / "maintenance-state.json"


def invalidation_token_path(workplace_root: Path) -> Path:
    """Locate the opaque invalidation identity without accessing the filesystem."""
    return maintenance_state_path(workplace_root).with_name("invalidation.token")


def read_invalidation_token(workplace_root: Path) -> str | None:
    """Hash opaque notification bytes; an unreadable marker must fail closed."""
    try:
        raw = invalidation_token_path(workplace_root).read_bytes()
    except FileNotFoundError:
        return None
    return hashlib.sha256(raw).hexdigest()


def _maintenance_state(workplace_root: Path) -> _MaintenanceState:
    """Read only the durable status; never expose persisted diagnostics."""
    try:
        text = maintenance_state_path(workplace_root).read_text(encoding="utf-8")
        data = json.loads(text)
    except FileNotFoundError:
        return _MaintenanceState(None)
    except (OSError, UnicodeError, ValueError):
        return _MaintenanceState("unavailable")
    if not isinstance(data, dict):
        return _MaintenanceState("unavailable")
    status = data.get("status")
    if status not in ("running", "complete", "failed"):
        return _MaintenanceState("unavailable")
    token = data.get("invalidation_token")
    return _MaintenanceState(
        status,
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        token if isinstance(token, str) else None,
    )


def _invalidated_status() -> dict[str, Any]:
    return {
        **_incomplete_status("unavailable"),
        "status": "stale",
        "error": "search_index_invalidated",
        "maintenance": {"status": "pending"},
    }


def _incomplete_status(status: str) -> dict[str, Any]:
    """Describe incomplete maintenance without touching the physical index."""
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "pf.search_index.status",
        "status": "building" if status == "running" else "degraded",
        "generation": None,
        "resource_count": 0,
        "document_count": 0,
        "stale_resource_count": 0,
        "failed_file_count": 0,
        "last_successful_refresh": None,
        "last_full_reconciliation": None,
        "error": {
            "running": "search_maintenance_running",
            "failed": "search_maintenance_failed",
            "unavailable": "search_maintenance_state_unavailable",
        }[status],
        "maintenance": {"status": status},
    }


def _public_status(status: dict[str, Any]) -> dict[str, Any]:
    """Remove private paths and untrusted error text from index diagnostics."""
    result = {
        key: value for key, value in status.items() if key in _PUBLIC_STATUS_FIELDS
    }
    if result.get("error") not in (None, ""):
        error = str(result["error"])
        result["error"] = (
            error
            if error in _SAFE_INDEX_ERRORS
            else "index_stale"
            if result.get("status") == "stale"
            else "index_unreadable"
        )
    capability = result.get("sqlite")
    if isinstance(capability, dict):
        result["sqlite"] = {
            key: capability[key]
            for key in ("sqlite_version", "fts5_available")
            if key in capability
        }
    return result


@dataclass(frozen=True)
class IndexObservationService:
    """Read current catalogue/index metadata and durable maintenance status.

    Construction is cold. Observation never verifies document fingerprints,
    builds, marks dirty, queues work or waits for maintenance. A durable running
    record remains incomplete after interruption until an authorized writer
    records recovery; elapsed time does not imply successful completion.
    """

    workplace_root: Path
    distribution_root: Path | None = field(default=None, kw_only=True)

    def checkpoint(self) -> tuple[str | None, str | None]:
        """Capture private durable identities around a complete metadata/query read."""
        token = read_invalidation_token(self.workplace_root)
        notifications = pending_invalidation_notifications(self.workplace_root)
        if notifications:
            token = hashlib.sha256(
                json.dumps([token, notifications]).encode("utf-8")
            ).hexdigest()
        return (
            _maintenance_state(self.workplace_root).fingerprint,
            token,
        )

    def observe(self) -> dict[str, Any]:
        """Return physical status, conservatively honoring durable failures."""

        def read_status() -> dict[str, Any]:
            catalogue = (
                WorkplaceSearchCatalogReader(self.workplace_root)
                if self.distribution_root is None
                else WorkplaceSearchCatalogReader(
                    self.workplace_root, distribution_root=self.distribution_root
                )
            )
            snapshot = catalogue.runtime_snapshot()
            return ResourceSearchIndex(
                self.workplace_root, snapshot, self.workplace_root
            ).status(verify_files=False)

        return self._observe(read_status)

    def observe_status(
        self, read_status: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        """Guard an explicitly authorized scoped diagnostic without widening it.

        The caller retains its existing status factory and verification option.
        Preserve legacy diagnostic fields, including its explicit target path,
        while the shared state guard overrides any raced or incomplete status.
        """
        original: dict[str, Any] = {}

        def read() -> dict[str, Any]:
            original.update(read_status())
            return original

        state = self._observe(read)
        return {**original, **state}

    def _observe(self, read_status: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        before = _maintenance_state(self.workplace_root)
        if before.status is not None and before.status != "complete":
            return _incomplete_status(before.status)
        try:
            token_before = read_invalidation_token(self.workplace_root)
            pending_before = pending_invalidation_notifications(self.workplace_root)
        except OSError:
            return _incomplete_status("unavailable")
        if token_before != before.invalidation_token or pending_before:
            return _invalidated_status()
        try:
            status = read_status()
        except (OSError, RuntimeError, ValueError, sqlite3.Error, LocalSearchError):
            status = {
                **_incomplete_status("unavailable"),
                "error": "index_unreadable",
            }
            status.pop("maintenance")
        # A writer may have started or failed while metadata was being read.
        # Never return a preceding fresh observation over that durable record.
        after = _maintenance_state(self.workplace_root)
        if after.status is not None and after.status != "complete":
            return _incomplete_status(after.status)
        try:
            token_after = read_invalidation_token(self.workplace_root)
            pending_after = pending_invalidation_notifications(self.workplace_root)
        except OSError:
            return _incomplete_status("unavailable")
        if before != after or token_before != token_after or pending_after:
            return {
                **_incomplete_status("unavailable"),
                "error": "search_maintenance_state_changed",
            }
        result = _public_status(status)
        if after.status is not None:
            result["maintenance"] = {"status": after.status}
        return result


def invalidation_notifications_path(workplace_root: Path) -> Path:
    """Locate the private pending-notification journal without creating it."""
    return maintenance_state_path(workplace_root).parent / "invalidation-notifications"


def pending_invalidation_notifications(workplace_root: Path) -> tuple[str, ...]:
    """Observe pending names only, including a notification whose token write failed."""
    folder = invalidation_notifications_path(workplace_root)
    try:
        return tuple(
            sorted(path.name for path in folder.iterdir() if path.suffix == ".json")
        )
    except FileNotFoundError:
        return ()
