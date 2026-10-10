"""Explicit immutable Work resource reads, independent of provider and transport."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ..resources.local_search import LocalSearchError, pagination, search_material
from ..process_execution import SAFE_ID_RE, canonical_fingerprint
from .resource_declarations import ResourceDeclarationPolicy
from .resource_material import DEFAULT_LIMITS, MaterialBudget, MaterialError, capture_material, metadata_descriptor


if TYPE_CHECKING:
    from .resource_context import WorkContractValidator, WorkResourceContextReadService


MAX_STATE_BYTES = 2 * 1024 * 1024


class WorkResourceError(Exception):
    def __init__(self, code: str, **details: Any):
        super().__init__(code)
        self.code, self.details = code, details


def _root(project: Path, workplace: Path | None, core: Any, row: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    from ..resources.snapshot import resolve_garage_path_ref

    reference = ResourceDeclarationPolicy(error=lambda: WorkResourceError).portable_reference(row)
    result = resolve_garage_path_ref(project, reference, workplace or project, core)
    if result.get("status") != "resolved" or not result.get("path"):
        raise WorkResourceError("resource_material_missing", resource_id=row["id"])
    return Path(result["path"]), reference


def build_resource_bindings(project: Path, workplace: Path | None, core: Any,
                            selected_ids: list[str]) -> dict[str, Any]:
    """Pin new material only at capsule creation; never migrate a read request."""
    from ..project.snapshot import load_snapshot
    from ..composition import build_resource_binding_builder

    builder = build_resource_binding_builder(
        limits=lambda: DEFAULT_LIMITS, budget=lambda: MaterialBudget,
        declarations=lambda: ResourceDeclarationPolicy(error=lambda: WorkResourceError),
        snapshot=lambda: lambda project: load_snapshot(project, core),
        root_resolver=lambda: lambda project, workplace, row: _root(project, workplace, core, row),
        material_capture=lambda: capture_material,
        work_error=lambda: WorkResourceError, material_error=lambda: MaterialError,
    )
    return builder.build(project, workplace, selected_ids)


class WorkResourceService:
    def __init__(self, project_root: Path, workplace_root: Path | None, core: Any):
        self.project_root, self.workplace_root, self.core = project_root.resolve(), workplace_root, core

    def _load(self, path: Path, *, with_digest: bool = False) -> Any:
        flow = self.core.locate_flow_root(self.project_root).resolve()
        try:
            target = path.resolve(strict=True)
            target.relative_to(flow)
            if path.is_symlink() or not target.is_file() or target.stat().st_size > MAX_STATE_BYTES:
                raise WorkResourceError("work_context_invalid")
            raw = target.read_bytes()
            if len(raw) > MAX_STATE_BYTES:
                raise WorkResourceError("work_context_invalid")
            value = yaml.safe_load(raw.decode("utf-8-sig"))
        except (yaml.YAMLError, UnicodeError) as exc:
            raise WorkResourceError("work_context_invalid") from exc
        except (OSError, ValueError, RuntimeError, SystemExit) as exc:
            raise WorkResourceError("work_context_unavailable") from exc
        if not isinstance(value, dict):
            raise WorkResourceError("work_context_invalid")
        return (value, "sha256:" + hashlib.sha256(raw).hexdigest()) if with_digest else value

    def _context_reader(self) -> WorkResourceContextReadService:
        from ..composition import build_work_resource_context_reader

        def contract_validator() -> WorkContractValidator:
            from .context import validate_execution_contract

            def validate(project_root: Path, path: Path, assignment: dict, capsule: dict) -> dict:
                return validate_execution_contract(project_root, path, assignment, capsule, self.core)

            return validate

        return build_work_resource_context_reader(
            project_root=lambda: self.project_root, selector_pattern=lambda: SAFE_ID_RE,
            flow_root=lambda: self.core.locate_flow_root, project_id=lambda: self.core.project_id,
            load=lambda: self._load, identifiers=lambda: ResourceDeclarationPolicy(error=lambda: WorkResourceError).identifiers, fingerprint=lambda: canonical_fingerprint,
            contract_validator=contract_validator, error=lambda: WorkResourceError,
        )

    def _context(self, run_id: Any, assignment_id: Any, context_id: Any) -> tuple[dict, list, dict]:
        return self._context_reader().read(run_id, assignment_id, context_id)

    def read(self, *, operation: str, run_id: str, assignment_id: str, context_id: str,
             resource_id: str | None = None, query: Any = None, limit: Any = None,
             limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
        from .. import diagnostics
        from ..project.snapshot import load_snapshot

        payload: dict[str, Any] = {"schema_version": 1, "kind": f"pf.work.{operation}", "scope": "work_context"}
        try:
            if operation not in {"search", "resolve"}:
                raise WorkResourceError("invalid_operation")
            identity, bindings, grants = self._context(run_id, assignment_id, context_id)
            payload["work"] = identity
            diagnostics.select_work(self.project_root, run_id, assignment_id)
            diagnostics.annotate(snapshot_id=identity["snapshot_id"])
            check = self.core.project_context_check_result(self.project_root, explicit_workplace=str(self.workplace_root) if self.workplace_root else None)
            if check.get("status") not in {"fresh", "fresh_with_updates"}:
                raise WorkResourceError("snapshot_not_fresh")
            rows = ResourceDeclarationPolicy(error=lambda: WorkResourceError).grant_rows(load_snapshot(self.project_root, self.core))
            if operation == "resolve":
                if not isinstance(resource_id, str) or not resource_id:
                    raise WorkResourceError("resource_id_required")
                if resource_id not in grants["pinned"]:
                    raise WorkResourceError("resource_not_in_work", resource_id=resource_id)
                if resource_id not in grants["stage"]:
                    raise WorkResourceError("resource_not_in_stage", resource_id=resource_id)
                bindings = [item for item in bindings if item["id"] == resource_id]
            if operation == "search":
                if not isinstance(query, str) or not query.strip() or len(query) > 4096:
                    raise WorkResourceError("invalid_query")
                page_limit, start = pagination(limit=limit, limitstart=limitstart, offset=offset)
            # Authorization and metadata checks for the whole requested set precede any material read.
            for binding in bindings:
                identifier = binding["id"]
                if identifier not in rows or str(rows[identifier].get("status") or "available") in {"disabled", "denied", "missing", "revoked"}:
                    raise WorkResourceError("resource_access_revoked", resource_id=identifier)
                if binding.get("status") != "available":
                    raise WorkResourceError(str(binding.get("reason") or "resource_material_unavailable"), resource_id=identifier)
                reference = ResourceDeclarationPolicy(error=lambda: WorkResourceError).portable_reference(rows[identifier])
                if canonical_fingerprint(metadata_descriptor(rows[identifier], reference)) != binding.get("metadata_fingerprint"):
                    raise WorkResourceError("resource_generation_changed", resource_id=identifier)
            documents, provenances, verified = [], [], []
            budget = MaterialBudget()
            for binding in bindings:
                root, reference = _root(self.project_root, self.workplace_root, self.core, rows[binding["id"]])
                current, docs = capture_material(rows[binding["id"]], root, reference, include_content=operation == "search", budget=budget)
                if any(current.get(key) != binding.get(key) for key in ("generation", "metadata_fingerprint", "material_fingerprint", "material_kind", "manifest")):
                    raise WorkResourceError("resource_material_changed", resource_id=binding["id"])
                provenance = {**identity, "resource_id": binding["id"], **{key: binding[key] for key in ("generation", "metadata_fingerprint", "material_fingerprint", "material_kind")}}
                provenances.append(provenance)
                verified.append({**copy.deepcopy(binding), "local_root": str(root.resolve()),
                                 "navigation": "metadata_only" if binding["material_kind"] != "fulltext" else "verified_declared_material",
                                 "resource_provenance": provenance})
                documents.extend({**doc, "resource_id": binding["id"], "resource_provenance": provenance} for doc in docs)
            payload.update(status="ready", resource_provenance=provenances,
                           coverage={"source": "verified_work_material", "authorized_resources": len(bindings),
                                     "verified_resources": len(verified), "documents": len(documents) if operation == "search" else None,
                                     "status": "complete" if bindings else "empty"})
            if operation == "resolve":
                payload["resource"] = verified[0]
            else:
                payload.update(self._search(documents, query, page_limit, start))
            diagnostics.current().info("Work resource read completed", component="search", code="work.resource_read", context={"operation": operation, "resources": len(bindings)})
        except (WorkResourceError, MaterialError, LocalSearchError) as exc:
            payload.update(status="blocked", reason=exc.code, **getattr(exc, "details", {}))
            diagnostics.current().warning("Work resource read blocked", component="search", code="work.resource_blocked", context={"reason": exc.code})
        except (OSError, ValueError, RuntimeError, SystemExit):
            payload.update(status="blocked", reason="work_resource_unavailable")
        except (TypeError, KeyError, AttributeError):
            payload.update(status="blocked", reason="work_context_invalid")
        return payload

    @staticmethod
    def _search(documents: list[dict[str, Any]], query: str, limit: int, start: int) -> dict[str, Any]:
        return search_material(documents, query, limit, start, error=lambda: WorkResourceError)
