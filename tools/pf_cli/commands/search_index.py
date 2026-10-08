"""Execute the existing Search Index CLI operations."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from processforge_core.resources.local_search import ResourceSearchIndex


def _print_status(payload: dict[str, Any]) -> None:
    sqlite_info = payload.get("sqlite") if isinstance(payload.get("sqlite"), dict) else {}
    print(f"STATUS: {payload.get('status')}")
    print(f"GENERATION: {payload.get('generation') or 'none'}")
    print(f"SQLITE_VERSION: {sqlite_info.get('sqlite_version') or 'unknown'}")
    print(f"FTS5: {'available' if sqlite_info.get('fts5_available') else 'unavailable'}")
    print(f"RESOURCES: {payload.get('resource_count')}")
    print(f"DOCUMENTS: {payload.get('document_count')}")
    print(f"STALE_RESOURCES: {payload.get('stale_resource_count')}")
    print(f"FAILED_FILES: {payload.get('failed_file_count')}")
    print(f"LAST_SUCCESSFUL_REFRESH: {payload.get('last_successful_refresh') or 'none'}")
    print(f"LAST_FULL_RECONCILIATION: {payload.get('last_full_reconciliation') or 'none'}")
    if payload.get("error"):
        print(f"ERROR: {payload.get('error')}")
    if payload.get("path"):
        print(f"INDEX: {payload.get('path')}")


class SearchIndexStatusCommand:
    """Adapt the existing status operation."""

    def __init__(
        self,
        *,
        index_factory: Callable[[Path], ResourceSearchIndex],
    ) -> None:
        self._index_factory = index_factory

    def execute(self, args: argparse.Namespace) -> int:
        workplace_root = Path(args.workplace).expanduser().resolve()
        status = self._index_factory(workplace_root).status(verify_files=bool(getattr(args, "verify_files", False)))
        _print_status(status)
        return 1 if status.get("status") == "degraded" else 0


class SearchIndexRefreshCommand:
    """Adapt the existing refresh operation."""

    def __init__(
        self,
        *,
        index_factory: Callable[[Path], ResourceSearchIndex],
    ) -> None:
        self._index_factory = index_factory

    def execute(self, args: argparse.Namespace) -> int:
        workplace_root = Path(args.workplace).expanduser().resolve()
        result = self._index_factory(workplace_root).refresh()
        print(f"REFRESHED: {result.get('generation')}")
        print(f"RESOURCES: {result.get('resources')}")
        print(f"DOCUMENTS: {result.get('indexed')}")
        return 0


class SearchIndexRebuildCommand:
    """Adapt the existing rebuild operation."""

    def __init__(
        self,
        *,
        index_factory: Callable[[Path], ResourceSearchIndex],
    ) -> None:
        self._index_factory = index_factory

    def execute(self, args: argparse.Namespace) -> int:
        workplace_root = Path(args.workplace).expanduser().resolve()
        result = self._index_factory(workplace_root).rebuild()
        print(f"REBUILT: {result.get('generation')}")
        print(f"RESOURCES: {result.get('resources')}")
        print(f"DOCUMENTS: {result.get('indexed')}")
        return 0


class SearchIndexDoctorCommand:
    """Adapt the existing doctor operation."""

    def __init__(
        self,
        *,
        index_factory: Callable[[Path], ResourceSearchIndex],
        doctor_formatter: Callable[[dict[str, Any]], int],
    ) -> None:
        self._index_factory = index_factory
        self._doctor_formatter = doctor_formatter

    def execute(self, args: argparse.Namespace) -> int:
        workplace_root = Path(args.workplace).expanduser().resolve()
        status = self._index_factory(workplace_root).status()
        return self._doctor_formatter(status)


class SearchIndexTickCommand:
    """Adapt the existing tick operation."""

    def __init__(
        self,
        *,
        index_factory: Callable[[Path], ResourceSearchIndex],
    ) -> None:
        self._index_factory = index_factory

    def execute(self, args: argparse.Namespace) -> int:
        workplace_root = Path(args.workplace).expanduser().resolve()
        payload = self._index_factory(workplace_root).maintenance_tick(verify_files=not bool(getattr(args, "skip_file_verify", False)))
        print(f"ACTION: {payload.get('action')}")
        after = payload.get("after") if isinstance(payload.get("after"), dict) else {}
        print(f"STATUS: {after.get('status')}")
        print(f"GENERATION: {after.get('generation') or 'none'}")
        print(f"DOCUMENTS: {after.get('document_count')}")
        if after.get("error"):
            print(f"ERROR: {after.get('error')}")
        return 0 if after.get("status") == "fresh" else 1
