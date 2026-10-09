"""Existing resource declaration rules shared by Work and prepared inputs."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .resource_material import LEGACY_INDEX_POLICIES, LEGACY_POLICY_CANONICAL


@dataclass(frozen=True, kw_only=True)
class ResourceDeclarationPolicy:
    error: Callable[[], Callable[[str], Exception]] = field(repr=False, compare=False)

    def identifiers(self, value: Any, reason: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise self.error()(reason)
        if len(value) != len(set(value)) or len(value) > 64:
            raise self.error()(reason)
        return list(value)


    @staticmethod
    def declared_policy(row: dict[str, Any]) -> dict[str, Any]:
        if isinstance(row.get("indexing"), dict):
            return {"indexing": copy.deepcopy(row["indexing"])}
        legacy = str(row.get("index_policy") or "").strip().casefold()
        if legacy in LEGACY_INDEX_POLICIES:
            return {"index_policy": LEGACY_POLICY_CANONICAL.get(legacy, legacy)}
        return {}


    def grant_rows(self, snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """A local-search allowlist, including an empty one, is authoritative."""
        resolved = snapshot.get("resolved") or {}
        originals = {item.get("id"): item for item in resolved.get("knowledge_resources", []) if isinstance(item, dict)}
        raw = snapshot.get("local_search_resources") if "local_search_resources" in snapshot else list(originals.values())
        if not isinstance(raw, list):
            raise self.error()("resource_scope_invalid")
        rows: dict[str, dict[str, Any]] = {}
        for item in raw:
            if not isinstance(item, dict):
                raise self.error()("resource_scope_invalid")
            identifier = item.get("id") or item.get("resource_id")
            if not isinstance(identifier, str) or not identifier or identifier in rows:
                raise self.error()("resource_scope_invalid")
            original = copy.deepcopy(originals.get(identifier, {}))
            row = {**original, **copy.deepcopy(item), "id": identifier}
            policy = self.declared_policy(original)
            if policy:
                row.pop("indexing", None)
                row.update(policy)
            rows[identifier] = row
        return rows


    def portable_reference(self, row: dict[str, Any]) -> dict[str, Any]:
        reference = row.get("path_ref")
        if not isinstance(reference, dict) or not reference:
            raise self.error()("resource_reference_unverifiable")
        # References are declarations, never a caller-provided absolute root.
        for key in ("relative_path", "path"):
            value = reference.get(key)
            if value is not None and (not isinstance(value, str) or re.match(r"^(?:[A-Za-z]:|[/\\])", value)
                                      or ".." in value.replace("\\", "/").split("/")):
                raise self.error()("resource_path_invalid")
        return copy.deepcopy(reference)

