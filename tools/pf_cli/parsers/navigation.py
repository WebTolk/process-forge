"""Register existing CLI commands for navigation."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ResourceIndexCommandParser:
    """Register the existing navigation command family."""

    def __init__(
        self,
        *,
        path_resolve: Callable[[argparse.Namespace], int],
        search_index_doctor: Callable[[argparse.Namespace], int],
        search_index_rebuild: Callable[[argparse.Namespace], int],
        search_index_refresh: Callable[[argparse.Namespace], int],
        search_index_status: Callable[[argparse.Namespace], int],
        search_index_tick: Callable[[argparse.Namespace], int],
    ) -> None:
        self._path_resolve = path_resolve
        self._search_index_doctor = search_index_doctor
        self._search_index_rebuild = search_index_rebuild
        self._search_index_refresh = search_index_refresh
        self._search_index_status = search_index_status
        self._search_index_tick = search_index_tick

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        path_resolve = add_parser("path-resolve", help="Resolve a workplace path using path_constants.")
        path_resolve.add_argument("--workplace", required=True, help="Workplace root path.")
        path_resolve.add_argument("--path", required=True, help="Raw path with optional ${CONST}.")
        path_resolve.set_defaults(func=self._path_resolve)

        search_index = add_parser("search-index", help="Inspect and maintain the derived workplace local resource search index.")
        search_index_sub = search_index.add_subparsers(dest="search_index_command", required=True)
        search_index_status = search_index_sub.add_parser("status", help="Show search index readiness for a project snapshot.")
        search_index_status.add_argument("--project-root", required=True, help="Project root path.")
        search_index_status.add_argument("--workplace", required=True, help="Workplace root path.")
        search_index_status.add_argument("--verify-files", action="store_true", help="Read authorized files and mark the scope stale when fingerprints changed.")
        search_index_status.set_defaults(func=self._search_index_status)
        search_index_refresh = search_index_sub.add_parser("refresh", help="Refresh the project snapshot scope in the workplace search index.")
        search_index_refresh.add_argument("--project-root", required=True, help="Project root path.")
        search_index_refresh.add_argument("--workplace", required=True, help="Workplace root path.")
        search_index_refresh.set_defaults(func=self._search_index_refresh)
        search_index_rebuild = search_index_sub.add_parser("rebuild", help="Rebuild the derived workplace search index for the project snapshot scope.")
        search_index_rebuild.add_argument("--project-root", required=True, help="Project root path.")
        search_index_rebuild.add_argument("--workplace", required=True, help="Workplace root path.")
        search_index_rebuild.set_defaults(func=self._search_index_rebuild)
        search_index_doctor = search_index_sub.add_parser("doctor", help="Validate search index capabilities and readiness.")
        search_index_doctor.add_argument("--project-root", required=True, help="Project root path.")
        search_index_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        search_index_doctor.set_defaults(func=self._search_index_doctor)
        search_index_tick = search_index_sub.add_parser("tick", help="Run one bounded maintenance pass for the project snapshot search scope.")
        search_index_tick.add_argument("--project-root", required=True, help="Project root path.")
        search_index_tick.add_argument("--workplace", required=True, help="Workplace root path.")
        search_index_tick.add_argument("--skip-file-verify", action="store_true", help="Skip file fingerprint verification and only refresh missing/stale metadata state.")
        search_index_tick.set_defaults(func=self._search_index_tick)
