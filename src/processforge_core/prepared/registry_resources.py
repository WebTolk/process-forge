"""Existing prepared registry-resource matching and path-resolution reads."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .resource_selection import PreparedResourceSelectionPolicy


class PreparedRegistryPathResolver(Protocol):
    def __call__(
        self, project_root: Path, path_ref: dict[str, Any], *, workplace_manifest: Path | None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class PreparedRegistryResourceReader:
    selection: Callable[[], PreparedResourceSelectionPolicy] = field(repr=False, compare=False)
    workplace_manifest: Callable[[], Callable[[Path], Path | None]] = field(repr=False, compare=False)
    path_resolver: Callable[[], PreparedRegistryPathResolver] = field(repr=False, compare=False)
    revoked_statuses: Callable[[], set[str]] = field(repr=False, compare=False)
    fail: Callable[[], Callable[[str], None]] = field(repr=False, compare=False)

    def read(
        self, project: Path, requested: list[Any], pinned_snapshot: dict[str, Any],
        current_snapshot: dict[str, Any], group: str,
    ) -> list[dict[str, Any]]:
        if not requested:
            return []
        selection = self.selection()
        pinned_rows = selection.resolved_rows(pinned_snapshot, group)
        current_rows = selection.resolved_rows(current_snapshot, group)
        manifest = self.workplace_manifest()(project)
        grants: list[dict[str, Any]] = []
        seen: set[str] = set()
        for request in requested:
            pinned = selection.unique_match(pinned_rows, request, "resource_not_in_snapshot")
            current = selection.unique_match(current_rows, request, "resource_access_revoked")
            if str(current.get("status") or "available").lower() in self.revoked_statuses():
                self.fail()("resource_access_revoked")
            identifier = str(pinned.get("id") or pinned.get("resource_id") or pinned.get("name") or "")
            if not identifier or identifier in seen:
                self.fail()("resource_scope_invalid")
            seen.add(identifier)
            if current != pinned:
                self.fail()("resource_generation_changed")
            if isinstance(request, dict) and request.get("path_ref") and request.get("path_ref") != pinned.get("path_ref"):
                self.fail()("resource_reference_mismatch")
            path_ref = pinned.get("path_ref")
            if not isinstance(path_ref, dict) or not path_ref:
                self.fail()("resource_reference_unverifiable")
            try:
                resolution = self.path_resolver()(project, path_ref, workplace_manifest=manifest)
            except (OSError, ValueError, RuntimeError, SystemExit, AttributeError):
                self.fail()("resource_material_unavailable")
            if not isinstance(resolution, dict) or resolution.get("status") != "resolved" or not resolution.get("path"):
                self.fail()("resource_material_unavailable")
            grants.append({"id": identifier, "path_ref": copy.deepcopy(path_ref), "resolution": resolution})
        return grants

