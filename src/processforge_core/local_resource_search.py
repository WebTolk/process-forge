"""Snapshot-authorized, rebuildable SQLite FTS5 local resource search.

The module intentionally has no registry or workplace discovery.  Its caller
supplies the current project snapshot; only paths explicitly present there can
enter the corpus.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MAX_FILE_BYTES = 1_000_000
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".csv"}


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


def index_path(project_root: Path) -> Path:
    return project_root / ".pf" / "runtime" / "local-resource-search" / "search.sqlite"


def build_index(project_root: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    roots = authorized_roots(project_root, snapshot)
    path = index_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".sqlite.tmp")
    temporary.unlink(missing_ok=True)
    documents = _documents(roots)
    db = sqlite3.connect(temporary)
    try:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, resource_id TEXT, package_id TEXT, kind TEXT, canonical_path TEXT, path_ref TEXT, fingerprint TEXT)")
        db.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(title, content, document_id UNINDEXED)")
        db.execute("INSERT INTO meta VALUES (?, ?)", ("snapshot_checksum", _snapshot_checksum(snapshot)))
        for resource_id, package_id, kind, canonical, path_ref, raw in documents:
            fingerprint, content = raw.split("\n", 1)
            cursor = db.execute("INSERT INTO documents (resource_id, package_id, kind, canonical_path, path_ref, fingerprint) VALUES (?, ?, ?, ?, ?, ?)", (resource_id, package_id, kind, canonical, path_ref, fingerprint))
            db.execute("INSERT INTO documents_fts (title, content, document_id) VALUES (?, ?, ?)", (canonical, content, cursor.lastrowid))
        db.commit()
    finally:
        db.close()
    os.replace(temporary, path)
    return {"status": "empty" if not documents else "current", "indexed": len(documents), "resources": len(roots), "snapshot_checksum": _snapshot_checksum(snapshot)}


def search(project_root: Path, snapshot: dict[str, Any], *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise LocalSearchError("invalid_query")
    page_limit, start = pagination(limit=limit, limitstart=limitstart, offset=offset)
    path = index_path(project_root)
    expected = _snapshot_checksum(snapshot)
    try:
        if not path.is_file():
            state = build_index(project_root, snapshot)
        else:
            db = sqlite3.connect(path)
            try:
                stored = db.execute("SELECT value FROM meta WHERE key='snapshot_checksum'").fetchone()
            finally:
                db.close()
            state = {"status": "current", "indexed": None, "resources": None, "snapshot_checksum": expected}
            if not stored or stored[0] != expected:
                rebuilt = build_index(project_root, snapshot)
                state = {**rebuilt, "status": "stale"}
        db = sqlite3.connect(path)
    except (OSError, sqlite3.Error) as exc:
        raise LocalSearchError("search_unavailable") from exc
    # Treat normal user input as one literal FTS phrase.  This keeps `-`,
    # punctuation and other FTS operators from unexpectedly becoming syntax.
    fts_query = '"' + query.replace('"', '""') + '"'
    try:
        try:
            total = int(db.execute("SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ?", (fts_query,)).fetchone()[0])
            rows = db.execute("SELECT d.resource_id, d.package_id, d.kind, d.canonical_path, d.path_ref, bm25(documents_fts) FROM documents_fts JOIN documents d ON d.id = documents_fts.document_id WHERE documents_fts MATCH ? ORDER BY bm25(documents_fts) LIMIT ? OFFSET ?", (fts_query, page_limit, start)).fetchall()
        except sqlite3.OperationalError as exc:
            raise LocalSearchError("invalid_query" if "syntax" in str(exc).lower() else "search_unavailable") from exc
    finally:
        db.close()
    return {"schema_version": 1, "kind": "pf.search", "search_status": state["status"], "query": query, "results": [{"resource_id": row[0], "provenance": {"package_id": row[1], "kind": row[2], "snapshot_checksum": expected}, "canonical_path": row[3], "path_ref": row[4], "match": {"fields": ["title", "content"], "rank": row[5]}} for row in rows], "page": {"limit": page_limit, "limitstart": start, "offset": start, "returned": len(rows), "total": total, "next_limitstart": start + len(rows) if start + len(rows) < total else None}}
