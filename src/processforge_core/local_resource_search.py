"""Snapshot-authorized, rebuildable SQLite FTS5 local resource search.

The module intentionally has no registry or workplace discovery.  Its caller
supplies the current project snapshot; only paths explicitly present there can
enter the corpus.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAX_FILE_BYTES = 1_000_000
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".csv"}
SCHEMA_VERSION = 2


@dataclass(frozen=True)
class LocalSearchError(Exception):
    code: str


@dataclass(frozen=True)
class AuthorizedRoot:
    resource_id: str
    package_id: str
    kind: str
    root: Path


def _snapshot_checksum(snapshot: dict[str, Any]) -> str:
    value = snapshot.get("snapshot") if isinstance(snapshot.get("snapshot"), dict) else {}
    return str(value.get("checksum") or value.get("sha256") or value.get("id") or "")


def _scope_key(snapshot: dict[str, Any]) -> str:
    checksum = _snapshot_checksum(snapshot)
    return checksum or "snapshot-unknown"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_int(value: Any, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise LocalSearchError("invalid_limit")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise LocalSearchError("invalid_limit") from exc
    if not 1 <= result <= maximum:
        raise LocalSearchError("invalid_limit")
    return result


def pagination(*, limit: Any = None, limitstart: Any = None, offset: Any = None) -> tuple[int, int]:
    page_limit = _as_int(limit, default=DEFAULT_LIMIT, maximum=MAX_LIMIT)
    if limitstart not in (None, "") and offset not in (None, "") and str(limitstart) != str(offset):
        raise LocalSearchError("ambiguous_offset")
    raw_start = limitstart if limitstart not in (None, "") else offset
    if raw_start in (None, ""):
        return page_limit, 0
    if isinstance(raw_start, bool):
        raise LocalSearchError("invalid_offset")
    try:
        start = int(raw_start)
    except (TypeError, ValueError) as exc:
        raise LocalSearchError("invalid_offset") from exc
    if start < 0:
        raise LocalSearchError("invalid_offset")
    return page_limit, start


def _resource_records(snapshot: dict[str, Any]) -> Iterable[dict[str, Any]]:
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    for key in ("available_knowledge_resources", "knowledge_resources", "templates", "template_resources"):
        rows = resolved.get(key) if isinstance(resolved, dict) else []
        if isinstance(rows, list):
            yield from (row for row in rows if isinstance(row, dict))
    # Future snapshot producers can publish this explicit compact manifest.
    rows = snapshot.get("local_search_resources")
    if isinstance(rows, list):
        yield from (row for row in rows if isinstance(row, dict))


def authorized_roots(project_root: Path, snapshot: dict[str, Any]) -> list[AuthorizedRoot]:
    result: list[AuthorizedRoot] = []
    seen: set[tuple[str, str]] = set()
    for row in _resource_records(snapshot):
        resource_id = str(row.get("id") or row.get("resource_id") or "").strip()
        if not resource_id:
            continue
        raw_paths: list[Any] = []
        for key in ("content_roots", "search_roots", "paths"):
            if isinstance(row.get(key), list):
                raw_paths.extend(row[key])
        raw_paths.extend(row.get(key) for key in ("resolved_path", "local_path", "path") if row.get(key))
        for raw in raw_paths:
            value = str(raw or "").strip()
            if not value or value.startswith("<") or "://" in value:
                continue
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = project_root / candidate
            try:
                root = candidate.resolve(strict=True)
            except OSError:
                continue
            identity = (resource_id, str(root))
            if identity in seen:
                continue
            seen.add(identity)
            result.append(AuthorizedRoot(resource_id, str(row.get("package_id") or row.get("package") or ""), str(row.get("kind") or "knowledge"), root))
    return result


def _iter_text_files(root: AuthorizedRoot) -> Iterable[Path]:
    if root.root.is_file():
        if root.root.suffix.lower() in TEXT_SUFFIXES and root.root.stat().st_size <= MAX_FILE_BYTES:
            yield root.root
        return
    for path in root.root.rglob("*"):
        try:
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and path.stat().st_size <= MAX_FILE_BYTES:
                yield path
        except OSError:
            continue


def _documents(roots: list[AuthorizedRoot]) -> list[tuple[str, str, str, str, str, str]]:
    documents: list[tuple[str, str, str, str, str, str]] = []
    for item in roots:
        for path in _iter_text_files(item):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                canonical = path.relative_to(item.root).as_posix() if item.root.is_dir() else path.name
            except (OSError, ValueError):
                continue
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            documents.append((item.resource_id, item.package_id, item.kind, canonical, f"{item.resource_id}:{canonical}", digest + "\n" + text))
    return documents


def index_path(project_root: Path, workplace_root: Path | None = None) -> Path:
    """Return the private derived search DB path.

    MCP and CLI callers should pass a workplace root so all projects share one
    workplace-level index.  The project-local fallback preserves older tests and
    direct library callers until they are migrated.
    """

    if workplace_root is not None:
        return workplace_root / "runtime" / "search" / "local-resource-search.sqlite"
    return project_root / ".pf" / "runtime" / "local-resource-search" / "search.sqlite"


def sqlite_fts5_capability() -> dict[str, Any]:
    db = sqlite3.connect(":memory:")
    try:
        version = sqlite3.sqlite_version
        try:
            db.execute("CREATE VIRTUAL TABLE fts5_probe USING fts5(content)")
            fts5_available = True
        except sqlite3.Error:
            fts5_available = False
    finally:
        db.close()
    return {"sqlite_version": version, "fts5_available": fts5_available}


def _ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    current = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if current and str(current[0]) != str(SCHEMA_VERSION):
        raise LocalSearchError("index_schema_mismatch")
    db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", ("schema_version", str(SCHEMA_VERSION)))
    db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", ("sqlite_version", sqlite3.sqlite_version))
    db.execute(
        "CREATE TABLE IF NOT EXISTS index_state ("
        "scope_key TEXT PRIMARY KEY, "
        "snapshot_checksum TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "generation TEXT NOT NULL, "
        "resource_count INTEGER NOT NULL, "
        "document_count INTEGER NOT NULL, "
        "failed_file_count INTEGER NOT NULL DEFAULT 0, "
        "last_successful_refresh TEXT, "
        "last_full_reconciliation TEXT, "
        "last_error TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "id INTEGER PRIMARY KEY, "
        "scope_key TEXT NOT NULL, "
        "resource_id TEXT, "
        "package_id TEXT, "
        "kind TEXT, "
        "canonical_path TEXT, "
        "path_ref TEXT, "
        "fingerprint TEXT)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS documents_scope_idx ON documents(scope_key)")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(title, content, document_id UNINDEXED, scope_key UNINDEXED)")


def _check_schema(db: sqlite3.Connection) -> None:
    required = {"meta", "index_state", "documents", "documents_fts"}
    rows = db.execute("SELECT name FROM sqlite_master WHERE name IN ('meta', 'index_state', 'documents', 'documents_fts')").fetchall()
    existing = {str(row[0]) for row in rows}
    if required - existing:
        raise LocalSearchError("index_schema_missing")
    current = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if not current or str(current[0]) != str(SCHEMA_VERSION):
        raise LocalSearchError("index_schema_mismatch")


def _delete_scope(db: sqlite3.Connection, scope_key: str) -> None:
    document_ids = [row[0] for row in db.execute("SELECT id FROM documents WHERE scope_key=?", (scope_key,)).fetchall()]
    if document_ids:
        placeholders = ",".join("?" for _item in document_ids)
        db.execute(f"DELETE FROM documents_fts WHERE document_id IN ({placeholders})", document_ids)
    db.execute("DELETE FROM documents WHERE scope_key=?", (scope_key,))


def _document_fingerprint_map(roots: list[AuthorizedRoot]) -> dict[str, str]:
    result: dict[str, str] = {}
    for resource_id, _package_id, _kind, canonical, path_ref, raw in _documents(roots):
        fingerprint, _content = raw.split("\n", 1)
        result[f"{resource_id}:{path_ref}:{canonical}"] = fingerprint
    return result


def build_index(project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None, full_reconciliation: bool = False) -> dict[str, Any]:
    roots = authorized_roots(project_root, snapshot)
    path = index_path(project_root, workplace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    documents = _documents(roots)
    scope_key = _scope_key(snapshot)
    generation_seed = "\n".join(sorted(row[4] + ":" + row[5].split("\n", 1)[0] for row in documents))
    generation = hashlib.sha256((scope_key + "\n" + generation_seed).encode("utf-8")).hexdigest()[:16]
    db = sqlite3.connect(path)
    try:
        _ensure_schema(db)
        _delete_scope(db, scope_key)
        for resource_id, package_id, kind, canonical, path_ref, raw in documents:
            fingerprint, content = raw.split("\n", 1)
            cursor = db.execute("INSERT INTO documents (scope_key, resource_id, package_id, kind, canonical_path, path_ref, fingerprint) VALUES (?, ?, ?, ?, ?, ?, ?)", (scope_key, resource_id, package_id, kind, canonical, path_ref, fingerprint))
            db.execute("INSERT INTO documents_fts (title, content, document_id, scope_key) VALUES (?, ?, ?, ?)", (canonical, content, cursor.lastrowid, scope_key))
        refreshed_at = _now_utc()
        db.execute(
            "INSERT OR REPLACE INTO index_state (scope_key, snapshot_checksum, status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scope_key,
                _snapshot_checksum(snapshot),
                "fresh",
                generation,
                len(roots),
                len(documents),
                0,
                refreshed_at,
                refreshed_at if full_reconciliation else None,
                None,
            ),
        )
        db.commit()
    finally:
        db.close()
    return {"status": "fresh", "indexed": len(documents), "resources": len(roots), "snapshot_checksum": _snapshot_checksum(snapshot), "generation": generation}


def rebuild_index(project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None) -> dict[str, Any]:
    path = index_path(project_root, workplace_root)
    path.unlink(missing_ok=True)
    return build_index(project_root, snapshot, workplace_root=workplace_root, full_reconciliation=True)


def index_status(project_root: Path, snapshot: dict[str, Any] | None = None, *, workplace_root: Path | None = None, verify_files: bool = False) -> dict[str, Any]:
    capability = sqlite_fts5_capability()
    path = index_path(project_root, workplace_root)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "pf.search_index.status",
        "path": str(path),
        "sqlite": capability,
        "status": "missing",
        "generation": None,
        "resource_count": 0,
        "document_count": 0,
        "stale_resource_count": 0,
        "failed_file_count": 0,
        "last_successful_refresh": None,
        "last_full_reconciliation": None,
    }
    if not capability.get("fts5_available"):
        payload["status"] = "degraded"
        payload["error"] = "fts5_unavailable"
        return payload
    if not path.is_file():
        return payload
    try:
        db = sqlite3.connect(path)
        try:
            _check_schema(db)
            scope_key = _scope_key(snapshot) if snapshot is not None else None
            if scope_key:
                row = db.execute("SELECT status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error FROM index_state WHERE scope_key=?", (scope_key,)).fetchone()
                if not row:
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = 1
                    return payload
                if verify_files and snapshot is not None:
                    stored_rows = db.execute("SELECT resource_id, path_ref, canonical_path, fingerprint FROM documents WHERE scope_key=?", (scope_key,)).fetchall()
                    stored = {f"{item[0]}:{item[1]}:{item[2]}": str(item[3]) for item in stored_rows}
                    current = _document_fingerprint_map(authorized_roots(project_root, snapshot))
                    if stored != current:
                        payload["status"] = "stale"
                        payload["stale_resource_count"] = 1
                        payload["resource_count"] = row[2]
                        payload["document_count"] = row[3]
                        payload["failed_file_count"] = row[4]
                        payload["last_successful_refresh"] = row[5]
                        payload["last_full_reconciliation"] = row[6]
                        payload["error"] = "document_fingerprint_changed"
                        return payload
                payload.update(
                    {
                        "status": row[0],
                        "generation": row[1],
                        "resource_count": row[2],
                        "document_count": row[3],
                        "failed_file_count": row[4],
                        "last_successful_refresh": row[5],
                        "last_full_reconciliation": row[6],
                    }
                )
                if row[7]:
                    payload["error"] = row[7]
            else:
                row = db.execute("SELECT count(*), COALESCE(sum(resource_count), 0), COALESCE(sum(document_count), 0), COALESCE(sum(failed_file_count), 0), max(last_successful_refresh), max(last_full_reconciliation) FROM index_state").fetchone()
                payload.update(
                    {
                        "status": "fresh" if row and row[0] else "missing",
                        "resource_count": int(row[1] or 0) if row else 0,
                        "document_count": int(row[2] or 0) if row else 0,
                        "failed_file_count": int(row[3] or 0) if row else 0,
                        "last_successful_refresh": row[4] if row else None,
                        "last_full_reconciliation": row[5] if row else None,
                    }
                )
        finally:
            db.close()
    except (OSError, sqlite3.Error, LocalSearchError) as exc:
        payload["status"] = "degraded"
        payload["error"] = str(exc) or "index_unreadable"
    return payload


def maintenance_tick(project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None, verify_files: bool = True) -> dict[str, Any]:
    before = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=verify_files)
    action = "none"
    result: dict[str, Any] | None = None
    if before.get("status") in {"missing", "stale"}:
        result = build_index(project_root, snapshot, workplace_root=workplace_root)
        action = "refresh"
    elif before.get("status") == "degraded" and str(before.get("error") or "").startswith("index_schema_"):
        result = rebuild_index(project_root, snapshot, workplace_root=workplace_root)
        action = "rebuild"
    after = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=False)
    return {"schema_version": 1, "kind": "pf.search_index.maintenance_tick", "action": action, "before": before, "after": after, "result": result}


def search(project_root: Path, snapshot: dict[str, Any], *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None, workplace_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise LocalSearchError("invalid_query")
    page_limit, start = pagination(limit=limit, limitstart=limitstart, offset=offset)
    path = index_path(project_root, workplace_root)
    expected = _snapshot_checksum(snapshot)
    scope_key = _scope_key(snapshot)
    try:
        if not path.is_file():
            state = {**build_index(project_root, snapshot, workplace_root=workplace_root), "status": "missing"}
        else:
            stored = None
            db = sqlite3.connect(path)
            try:
                _ensure_schema(db)
                stored = db.execute("SELECT snapshot_checksum, generation FROM index_state WHERE scope_key=?", (scope_key,)).fetchone()
            except (sqlite3.Error, LocalSearchError):
                db.close()
                path.unlink(missing_ok=True)
                state = {**build_index(project_root, snapshot, workplace_root=workplace_root), "status": "stale"}
                db = sqlite3.connect(path)
            finally:
                try:
                    db.close()
                except sqlite3.Error:
                    pass
            if stored is not None:
                state = {"status": "fresh", "indexed": None, "resources": None, "snapshot_checksum": expected, "generation": stored[1] if stored else None}
                if stored[0] != expected:
                    rebuilt = build_index(project_root, snapshot, workplace_root=workplace_root)
                    state = {**rebuilt, "status": "stale"}
            else:
                rebuilt = build_index(project_root, snapshot, workplace_root=workplace_root)
                state = {**rebuilt, "status": "stale"}
        db = sqlite3.connect(path)
    except (OSError, sqlite3.Error) as exc:
        raise LocalSearchError("search_unavailable") from exc
    # Treat normal user input as one literal FTS phrase.  This keeps `-`,
    # punctuation and other FTS operators from unexpectedly becoming syntax.
    fts_query = '"' + query.replace('"', '""') + '"'
    try:
        try:
            total = int(db.execute("SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ? AND scope_key=?", (fts_query, scope_key)).fetchone()[0])
            rows = db.execute("SELECT d.resource_id, d.package_id, d.kind, d.canonical_path, d.path_ref, bm25(documents_fts) FROM documents_fts JOIN documents d ON d.id = documents_fts.document_id WHERE documents_fts MATCH ? AND documents_fts.scope_key=? ORDER BY bm25(documents_fts), d.resource_id, d.canonical_path LIMIT ? OFFSET ?", (fts_query, scope_key, page_limit, start)).fetchall()
        except sqlite3.OperationalError as exc:
            raise LocalSearchError("invalid_query" if "syntax" in str(exc).lower() else "search_unavailable") from exc
    finally:
        db.close()
    items = [{"resource_id": row[0], "resource_type": row[2], "title": row[3], "provenance": {"package_id": row[1], "kind": row[2], "snapshot_checksum": expected}, "canonical_path": row[3], "relative_path": row[3], "path_ref": row[4], "match": {"fields": ["title", "content"], "rank": row[5], "reason": "FTS5 title/content match"}} for row in rows]
    return {
        "schema_version": 1,
        "kind": "pf.search",
        "search_status": state["status"],
        "index_generation": state.get("generation"),
        "query": query,
        "total": total,
        "limit": page_limit,
        "offset": start,
        "items": items,
        "results": items,
        "page": {"limit": page_limit, "limitstart": start, "offset": start, "returned": len(rows), "total": total, "next_limitstart": start + len(rows) if start + len(rows) < total else None},
    }
