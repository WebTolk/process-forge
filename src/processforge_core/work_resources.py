"""Explicit immutable Work resource reads, independent of provider and transport."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

import yaml

from .local_resource_search import LocalSearchError, pagination
from .process_execution import SAFE_ID_RE, canonical_fingerprint
from .work_resource_material import DEFAULT_LIMITS, MaterialBudget, MaterialError, capture_material, metadata_descriptor


MAX_STATE_BYTES = 2 * 1024 * 1024


class WorkResourceError(Exception):
    def __init__(self, code: str, **details: Any):
        super().__init__(code)
        self.code, self.details = code, details


def _ids(value: Any, reason: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise WorkResourceError(reason)
    if len(value) != len(set(value)) or len(value) > 64:
        raise WorkResourceError(reason)
    return list(value)


def grant_rows(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """A local-search allowlist, including an empty one, is authoritative."""
    resolved = snapshot.get("resolved") or {}
    originals = {item.get("id"): item for item in resolved.get("knowledge_resources", []) if isinstance(item, dict)}
    raw = snapshot.get("local_search_resources") if "local_search_resources" in snapshot else list(originals.values())
    if not isinstance(raw, list):
        raise WorkResourceError("resource_scope_invalid")
    rows: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise WorkResourceError("resource_scope_invalid")
        identifier = item.get("id") or item.get("resource_id")
        if not isinstance(identifier, str) or not identifier or identifier in rows:
            raise WorkResourceError("resource_scope_invalid")
        rows[identifier] = {**copy.deepcopy(originals.get(identifier, {})), **copy.deepcopy(item), "id": identifier}
    return rows


def portable_reference(row: dict[str, Any]) -> dict[str, Any]:
    reference = row.get("path_ref")
    if not isinstance(reference, dict) or not reference:
        raise WorkResourceError("resource_reference_unverifiable")
    # References are declarations, never a caller-provided absolute root.
    for key in ("relative_path", "path"):
        value = reference.get(key)
        if value is not None and (not isinstance(value, str) or re.match(r"^(?:[A-Za-z]:|[/\\])", value)
                                  or ".." in value.replace("\\", "/").split("/")):
            raise WorkResourceError("resource_path_invalid")
    return copy.deepcopy(reference)


def _root(project: Path, workplace: Path | None, core: Any, row: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    from .garage import resolve_garage_path_ref

    reference = portable_reference(row)
    result = resolve_garage_path_ref(project, reference, workplace or project, core)
    if result.get("status") != "resolved" or not result.get("path"):
        raise WorkResourceError("resource_material_missing", resource_id=row["id"])
    return Path(result["path"]), reference


def build_resource_bindings(project: Path, workplace: Path | None, core: Any,
                            selected_ids: list[str]) -> dict[str, Any]:
    """Pin new material only at capsule creation; never migrate a read request."""
    from .garage import load_snapshot

    result: dict[str, Any] = {"schema_version": 1, "resources": [], "limits": dict(DEFAULT_LIMITS)}
    budget = MaterialBudget()
    try:
        identifiers = _ids(selected_ids, "resource_scope_invalid")
        rows = grant_rows(load_snapshot(project, core))
    except WorkResourceError as exc:
        return {**result, "status": "unavailable", "reason": exc.code}
    for identifier in identifiers:
        try:
            if identifier not in rows:
                raise WorkResourceError("resource_access_revoked")
            row = rows[identifier]
            if str(row.get("status") or "available") in {"disabled", "denied", "missing", "revoked"}:
                raise WorkResourceError("resource_access_revoked")
            root, reference = _root(project, workplace, core, row)
            binding, _ = capture_material(row, root, reference, budget=budget)
        except (MaterialError, WorkResourceError) as exc:
            binding = {"id": identifier, "status": "unavailable", "reason": exc.code}
        except (OSError, ValueError, RuntimeError, SystemExit):
            binding = {"id": identifier, "status": "unavailable", "reason": "resource_material_unavailable"}
        result["resources"].append(binding)
    result["status"] = "available" if all(item["status"] == "available" for item in result["resources"]) else "unavailable"
    return result


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

    def _context(self, run_id: Any, assignment_id: Any, context_id: Any) -> tuple[dict, list, dict]:
        if any(not isinstance(item, str) or not SAFE_ID_RE.fullmatch(item) for item in (run_id, assignment_id, context_id)):
            raise WorkResourceError("work_selector_required")
        flow = self.core.locate_flow_root(self.project_root)
        run = self._load(flow / "runs" / run_id / "run.yaml")
        assignment = self._load(flow / "assignments" / f"{assignment_id}.yaml")
        if (run.get("id") != run_id or assignment.get("id") != assignment_id or assignment.get("run_id") != run_id
                or not any(isinstance(task, dict) and task.get("id") == assignment_id for task in run.get("tasks", []))):
            raise WorkResourceError("work_identity_mismatch")
        pin = run.get("process_execution") or {}
        assignment_pin = assignment.get("process_execution") or {}
        expected_path = f".pf/contexts/assignment-capsules/{assignment_id}.capsule.yaml"
        if assignment_pin.get("assignment_capsule") != expected_path:
            raise WorkResourceError("legacy_contract_incomplete", remediation="create_successor_work")
        path = flow / "contexts" / "assignment-capsules" / f"{assignment_id}.capsule.yaml"
        capsule, digest = self._load(path, with_digest=True)
        if assignment_pin.get("assignment_capsule_checksum") != digest:
            raise WorkResourceError("work_context_checksum_mismatch")
        if capsule.get("capsule", {}).get("id") != context_id:
            raise WorkResourceError("work_context_mismatch")
        if (capsule.get("assignment", {}).get("id") != assignment_id
                or capsule.get("assignment", {}).get("run_id") != run_id
                or capsule.get("capsule", {}).get("assignment_id") != assignment_id
                or capsule.get("capsule", {}).get("immutable") is not True):
            raise WorkResourceError("work_identity_mismatch")
        capsule_pin = capsule.get("process_execution") or {}
        definition = capsule_pin.get("definition")
        if not isinstance(definition, dict) or capsule_pin.get("process_fingerprint") != canonical_fingerprint(definition):
            raise WorkResourceError("process_pin_invalid")
        for key in ("process_id", "process_version", "process_fingerprint", "snapshot_id", "snapshot_checksum"):
            if not capsule_pin.get(key) or capsule_pin.get(key) != pin.get(key) or capsule_pin.get(key) != assignment_pin.get(key):
                raise WorkResourceError("work_context_mismatch")
        if pin.get("definition") != definition:
            raise WorkResourceError("process_pin_invalid")
        snapshot = capsule.get("context_snapshot") or {}
        if snapshot.get("id") != capsule_pin["snapshot_id"] or snapshot.get("sha256") != capsule_pin["snapshot_checksum"]:
            raise WorkResourceError("work_context_mismatch")
        selected = _ids(capsule.get("context", {}).get("selected_resource_ids"), "resource_scope_invalid")
        if selected != capsule_pin.get("selected_resource_ids") or selected != pin.get("selected_resource_ids"):
            raise WorkResourceError("resource_scope_invalid")
        bindings = capsule.get("resource_bindings")
        if not isinstance(bindings, dict):
            raise WorkResourceError("legacy_contract_incomplete", remediation="create_successor_work")
        if type(bindings.get("schema_version")) is not int or bindings["schema_version"] != 1:
            raise WorkResourceError("resource_binding_version_unsupported")
        resources = bindings.get("resources")
        if not isinstance(resources, list) or any(not isinstance(item, dict) for item in resources):
            raise WorkResourceError("resource_binding_invalid")
        if _ids([item.get("id") for item in resources], "resource_binding_invalid") != selected:
            raise WorkResourceError("resource_binding_invalid")
        if "execution_contract" in capsule:
            from .work_context import validate_execution_contract
            validation = validate_execution_contract(self.project_root, flow / "assignments" / f"{assignment_id}.yaml", assignment, capsule, self.core)
            if validation["status"] != "valid":
                raise WorkResourceError(validation.get("reason") or "execution_contract_invalid", remediation="create_successor_work")
            scope = capsule["execution_contract"]["scope"]
            if "read" not in scope["allowed_actions"] or "read" in scope["forbidden_actions"]:
                raise WorkResourceError("scope_denied")
        stage = next((item for item in definition.get("stages", []) if isinstance(item, dict) and item.get("id") == assignment.get("stage")), None)
        if stage is None:
            raise WorkResourceError("work_stage_invalid")
        subset = _ids(stage["resource_subset"], "stage_resource_subset_invalid") if "resource_subset" in stage else selected
        if not set(subset).issubset(selected):
            raise WorkResourceError("stage_resource_subset_invalid")
        identity = {"project_id": self.core.project_id(self.project_root), "run_id": run_id,
                    "assignment_id": assignment_id, "context_id": context_id, "context_checksum": digest,
                    "snapshot_id": snapshot["id"], "snapshot_checksum": snapshot["sha256"], "stage_id": stage["id"]}
        return identity, [item for item in resources if item["id"] in subset], {"pinned": selected, "stage": subset}

    def read(self, *, operation: str, run_id: str, assignment_id: str, context_id: str,
             resource_id: str | None = None, query: Any = None, limit: Any = None,
             limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
        from . import diagnostics
        from .garage import load_snapshot

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
            rows = grant_rows(load_snapshot(self.project_root, self.core))
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
                reference = portable_reference(rows[identifier])
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
        try:
            db = sqlite3.connect(":memory:")
            try:
                db.execute("CREATE VIRTUAL TABLE material USING fts5(title, content)")
                db.executemany("INSERT INTO material(rowid,title,content) VALUES(?,?,?)", ((i + 1, doc["title"], doc["content"]) for i, doc in enumerate(documents)))
                phrase = '"' + query.replace('"', '""') + '"'
                total = db.execute("SELECT count(*) FROM material WHERE material MATCH ?", (phrase,)).fetchone()[0]
                matches = db.execute("SELECT rowid FROM material WHERE material MATCH ? ORDER BY bm25(material), rowid LIMIT ? OFFSET ?", (phrase, limit, start)).fetchall()
            finally:
                db.close()
        except sqlite3.Error as exc:
            raise WorkResourceError("work_search_unavailable") from exc
        results = [{key: value for key, value in documents[row[0] - 1].items() if key != "content"} for row in matches]
        return {"query": query, "total": total, "limit": limit, "offset": start, "results": results, "items": results,
                "page": {"limit": limit, "offset": start, "limitstart": start, "returned": len(results), "total": total,
                         "next_limitstart": start + len(results) if start + len(results) < total else None}}
