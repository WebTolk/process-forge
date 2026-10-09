"""Existing prepared resource selection, binding and revocation rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class PreparedResourceSelectionPolicy:
    matcher: Callable[[], Callable[[dict[str, Any], Any], bool]] = field(repr=False, compare=False)
    fail: Callable[[], Callable[[str], None]] = field(repr=False, compare=False)
    revoked_statuses: Callable[[], set[str]] = field(repr=False, compare=False)

    @staticmethod
    def resolved_rows(snapshot: dict[str, Any], group: str) -> list[dict[str, Any]]:
        resolved = snapshot.get("resolved")
        if not isinstance(resolved, dict):
            return []
        rows = resolved.get(group)
        return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []

    def unique_match(self, rows: list[dict[str, Any]], requested: Any, reason: str) -> dict[str, Any]:
        try:
            matches = [row for row in rows if self.matcher()(row, requested)]
        except (TypeError, ValueError, AttributeError):
            self.fail()("resource_scope_invalid")
        if len(matches) != 1:
            self.fail()(reason)
        return matches[0]

    def resource_bindings(self, capsule: dict[str, Any]) -> dict[str, dict[str, Any]]:
        bindings = capsule.get("resource_bindings")
        if not isinstance(bindings, dict) or type(bindings.get("schema_version")) is not int or bindings.get("schema_version") != 1:
            self.fail()("legacy_contract_incomplete")
        rows = bindings.get("resources")
        if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
            self.fail()("resource_binding_invalid")
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            identifier = row.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in result:
                self.fail()("resource_binding_invalid")
            result[identifier] = row
        return result

    def current_resource(self, current_rows: dict[str, dict[str, Any]], identifier: str) -> dict[str, Any]:
        row = current_rows.get(identifier)
        if row is None:
            self.fail()("resource_access_revoked")
        if str(row.get("status") or "available").lower() in self.revoked_statuses():
            self.fail()("resource_access_revoked")
        return row
