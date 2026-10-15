"""Describe supported syntax without dispatching operations or deciding authority.

Adapters supply immutable descriptor data and fresh, bounded Work facts. This
module neither imports transports nor reads a project, registry or parser.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Literal


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class CatalogRequestError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class WorkFacts:
    """A projection, never an authorization decision for an individual action."""

    selection: Literal["absent", "explicit"] = "absent"
    context_validation: str = "unknown"
    execution_readiness: str = "unknown"
    state_action: str = "unknown"
    blockers_present: bool = False


@dataclass(frozen=True)
class ActionDescriptor:
    action_id: str
    surface: Literal["cli", "mcp"]
    name: str
    summary: str
    # A canonical JSON value keeps nested advertised schemas immutable too.
    contract_json: str
    aliases: tuple[str, ...] = ()
    effect_status: str = "unknown"
    read_only: bool | None = None
    effects: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    native_validation: tuple[str, ...] = ()

    def summary_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id, "surface": self.surface,
            "name": self.name, "summary": self.summary, "aliases": list(self.aliases),
            "supported": True,
            "permission": {"status": "unknown", "reason": "native_operation_not_evaluated"},
            "availability": {"status": "unknown", "native_validation_required": True},
            "side_effects": {"status": self.effect_status, "read_only": self.read_only, "details": list(self.effects)},
            "schema_fingerprint": _fingerprint(json.loads(self.contract_json)),
        }

    def detail_payload(self) -> dict[str, Any]:
        return {
            **self.summary_payload(), "contract": json.loads(self.contract_json),
            "preconditions": list(self.preconditions),
            "native_validation": list(self.native_validation),
        }


class ActionCatalog:
    """A request-local catalogue of data, with no execution entry point."""

    def __init__(self, descriptors: Iterable[ActionDescriptor], *, version: str,
                 sources: Iterable[str] = ("supplied_descriptors",)):
        self._descriptors = tuple(sorted(descriptors, key=lambda item: item.action_id))
        self._by_id = {item.action_id: item for item in self._descriptors}
        if len(self._by_id) != len(self._descriptors):
            raise ValueError("duplicate_action_id")
        summaries = [item.summary_payload() for item in self._descriptors]
        self._provenance = {
            "catalogue_fingerprint": _fingerprint([item.detail_payload() for item in self._descriptors]),
            "schema_fingerprint": _fingerprint([{key: row[key] for key in ("action_id", "schema_fingerprint")} for row in summaries]),
            "version": version,
            "version_source": "caller_running_distribution",
            "implementation": "processforge_core.operations.catalogue.ActionCatalog",
            "contract_version": 1,
            "sources": sorted(set(sources)),
            "installed_build": "unknown", "connected_host_build": "unknown",
        }

    @staticmethod
    def validate_request(
        *, operation: str, action_id: str = "", query: str = "", surface: str = "",
        limit: int = 25, offset: int = 0,
    ) -> None:
        if not isinstance(operation, str) or operation not in {"list", "describe"}:
            raise CatalogRequestError("unsupported_catalog_operation")
        if not isinstance(action_id, str) or len(action_id) > 256 or (operation == "describe" and not action_id):
            raise CatalogRequestError("invalid_action_id")
        if not isinstance(query, str) or len(query) > 256:
            raise CatalogRequestError("invalid_query")
        if not isinstance(surface, str) or surface not in {"", "cli", "mcp"}:
            raise CatalogRequestError("invalid_surface")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise CatalogRequestError("invalid_limit")
        if type(offset) is not int or offset < 0:
            raise CatalogRequestError("invalid_offset")

    def query(
        self, *, operation: str, action_id: str = "", query: str = "", surface: str = "",
        limit: int = 25, offset: int = 0, work: WorkFacts | None = None,
    ) -> dict[str, Any]:
        self.validate_request(operation=operation, action_id=action_id, query=query, surface=surface, limit=limit, offset=offset)
        # Return fresh JSON containers; callers cannot change later responses.
        result: dict[str, Any] = {
            "schema_version": 1, "kind": "pf.actions." + operation, "status": "ready",
            "discovery_only": True, "provenance": json.loads(json.dumps(self._provenance)),
            "work_context": asdict(work or WorkFacts()),
        }
        if operation == "describe":
            selected = self._by_id.get(action_id)
            if selected is None:
                return {**result, "status": "unsupported", "reason": "unsupported_action", "action_id": action_id}
            return {**result, "action": selected.detail_payload()}
        needle = query.casefold()
        filtered = [item for item in self._descriptors if (not surface or item.surface == surface)
                    and (not needle or needle in (item.action_id + " " + item.summary).casefold())]
        page = filtered[offset:offset + limit]
        next_offset = offset + len(page)
        return {
            **result, "query": query, "surface": surface or "all", "limit": limit, "offset": offset,
            "total": len(filtered), "returned": len(page), "has_more": next_offset < len(filtered),
            "next_offset": next_offset if next_offset < len(filtered) else None,
            "actions": [item.summary_payload() for item in page],
        }
