"""Workplace-owned, snapshot-authorized SQLite FTS5 local resource search.

The index is resource-oriented: documents are stored once per resource in the
workplace DB. Project snapshots only authorize which resource identities may be
queried; they do not own or duplicate indexed documents.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MAX_FILE_BYTES = 1_000_000
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".csv"}
SCHEMA_VERSION = 3
POLICY_MODES = {"fulltext", "metadata", "none"}


@dataclass(frozen=True)
class LocalSearchError(Exception):
    code: str


@dataclass(frozen=True)
class IndexSource:
    path: str
    mode: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    role: str


@dataclass(frozen=True)
class AuthorizedResource:
    resource_id: str
    package_id: str
    kind: str
    title: str
    description: str
    version: str
    fingerprint: str
    root: Path
    root_ref: str
    indexing: dict[str, Any]
    sources: tuple[IndexSource, ...]


@dataclass(frozen=True)
class ResourceSearchIndex:
    """Stateful application service for one project's local resource index."""

    project_root: Path
    snapshot: dict[str, Any] | None = None
    workplace_root: Path | None = None

    def status(self, *, verify_files: bool = False) -> dict[str, Any]:
        return index_status(self.project_root, self.snapshot, workplace_root=self.workplace_root, verify_files=verify_files)

    def refresh(self) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return build_index(self.project_root, self.snapshot, workplace_root=self.workplace_root)

    def rebuild(self) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return rebuild_index(self.project_root, self.snapshot, workplace_root=self.workplace_root)

    def mark_dirty(self, *, reason: str = "dirty") -> dict[str, Any]:
        return mark_index_dirty(self.project_root, self.snapshot, workplace_root=self.workplace_root, reason=reason)

    def maintenance_tick(self, *, verify_files: bool = True) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return maintenance_tick(self.project_root, self.snapshot, workplace_root=self.workplace_root, verify_files=verify_files)

    def search(self, *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return search(
            self.project_root,
            self.snapshot,
            query=query,
            limit=limit,
            limitstart=limitstart,
            offset=offset,
            workplace_root=self.workplace_root,
        )


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


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _policy_hash(policy: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(policy).encode("utf-8")).hexdigest()


def _resource_records(snapshot: dict[str, Any]) -> Iterable[dict[str, Any]]:
    resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    rows = snapshot.get("local_search_resources")
    if isinstance(rows, list):
        yield from (row for row in rows if isinstance(row, dict))
        return
    # Pre-selection snapshots have no local search grant. Keep compatibility
    # with their resolved resources, never with the diagnostic available list.
    for key in ("knowledge_resources", "templates", "template_resources"):
        rows = resolved.get(key) if isinstance(resolved, dict) else []
        if isinstance(rows, list):
            yield from (row for row in rows if isinstance(row, dict))


def _fingerprint_value(row: dict[str, Any]) -> str:
    raw = row.get("fingerprint")
    if isinstance(raw, dict):
        value = raw.get("value")
        if value:
            return str(value)
    if raw:
        return str(raw)
    version = str(row.get("version") or row.get("generation") or "")
    identity = {
        "id": row.get("id") or row.get("resource_id"),
        "path_ref": row.get("path_ref"),
        "version": version,
        "indexing": row.get("indexing") or row.get("index_policy"),
    }
    return "sha256:" + hashlib.sha256(_stable_json(identity).encode("utf-8")).hexdigest()


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item))
    return ()


def _normalize_source(raw: dict[str, Any], default_mode: str) -> IndexSource:
    mode = str(raw.get("mode") or default_mode or "metadata")
    if mode not in POLICY_MODES:
        mode = "metadata"
    return IndexSource(
        path=str(raw.get("path") or "."),
        mode=mode,
        include=_string_list(raw.get("include")) or ("**/*",),
        exclude=_string_list(raw.get("exclude")),
        role=str(raw.get("role") or ""),
    )


def normalize_indexing_policy(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize the public indexing contract for one resource."""

    raw = row.get("indexing") if isinstance(row.get("indexing"), dict) else None
    if raw is None:
        legacy = str(row.get("index_policy") or "").strip()
        if legacy in {"none", "never", "disabled"}:
            raw = {"enabled": False, "mode": "none"}
        elif legacy in {"metadata", "metadata_first", "index_only", "source_tree", "symbols"}:
            raw = {"enabled": True, "mode": "metadata", "fields": ["title", "description", "tags", "path"]}
        elif legacy in {"fulltext", "always_index", "snapshot_authorized"}:
            raw = {
                "enabled": True,
                "mode": "fulltext",
                "fields": ["title", "description", "path"],
                "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md", "**/*.txt", "**/*.rst"]}],
            }
        else:
            # Compatibility for old direct callers. Snapshot producers should
            # write explicit `indexing` and not rely on this fallback.
            raw = {
                "enabled": True,
                "mode": "fulltext",
                "fields": ["title", "description", "path"],
                "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*"]}],
                "legacy_default": True,
            }
    enabled = bool(raw.get("enabled", True))
    mode = str(raw.get("mode") or ("metadata" if enabled else "none"))
    if mode not in POLICY_MODES:
        mode = "metadata"
    if not enabled:
        mode = "none"
    fields = _string_list(raw.get("fields")) or ("title", "description", "path")
    source_rows = raw.get("sources") if isinstance(raw.get("sources"), list) else []
    sources = tuple(_normalize_source(item, mode) for item in source_rows if isinstance(item, dict))
    if not sources and mode != "none":
        sources = (_normalize_source({"path": ".", "mode": mode, "include": ["**/*"]}, mode),)
    return {
        "enabled": enabled,
        "mode": mode,
        "fields": list(fields),
        "sources": [
            {
                "path": item.path,
                "mode": item.mode,
                "include": list(item.include),
                "exclude": list(item.exclude),
                **({"role": item.role} if item.role else {}),
            }
            for item in sources
        ],
        **({"legacy_default": True} if raw.get("legacy_default") else {}),
    }


def authorized_resource_ids(snapshot: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for row in _resource_records(snapshot):
        resource_id = str(row.get("id") or row.get("resource_id") or "").strip()
        if resource_id and resource_id not in seen:
            seen.add(resource_id)
            result.append(resource_id)
    return result


def indexable_resource_ids(resources: list[AuthorizedResource]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for resource in resources:
        if resource.resource_id not in seen:
            seen.add(resource.resource_id)
            result.append(resource.resource_id)
    return result


def authorized_roots(project_root: Path, snapshot: dict[str, Any]) -> list[AuthorizedResource]:
    result: list[AuthorizedResource] = []
    seen: set[tuple[str, str]] = set()
    for row in _resource_records(snapshot):
        resource_id = str(row.get("id") or row.get("resource_id") or "").strip()
        if not resource_id:
            continue
        policy = normalize_indexing_policy(row)
        if policy.get("mode") == "none":
            continue
        raw_paths: list[Any] = []
        for key in ("content_roots", "search_roots", "paths"):
            if isinstance(row.get(key), list):
                raw_paths.extend(row[key])
        raw_paths.extend(row.get(key) for key in ("resolved_path", "local_path", "path") if row.get(key))
        for raw_path in raw_paths:
            value = str(raw_path or "").strip()
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
            sources = tuple(_normalize_source(item, str(policy.get("mode") or "metadata")) for item in policy.get("sources", []) if isinstance(item, dict))
            result.append(
                AuthorizedResource(
                    resource_id=resource_id,
                    package_id=str(row.get("package_id") or row.get("package") or ""),
                    kind=str(row.get("kind") or "knowledge"),
                    title=str(row.get("title") or resource_id),
                    description=str(row.get("description") or ""),
                    version=str(row.get("version") or row.get("generation") or ""),
                    fingerprint=_fingerprint_value(row),
                    root=root,
                    root_ref=_stable_json(row.get("path_ref")) if isinstance(row.get("path_ref"), dict) else str(root),
                    indexing=policy,
                    sources=sources,
                )
            )
    return result


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    normalized_path = path.lstrip("/")
    for pattern in patterns:
        normalized_pattern = pattern.lstrip("/")
        candidates = [normalized_pattern]
        if normalized_pattern.startswith("**/"):
            candidates.append(normalized_pattern[3:])
        if any(fnmatch.fnmatch(normalized_path, candidate) for candidate in candidates):
            return True
    return False


def _iter_source_files(root: Path, source: IndexSource) -> Iterable[tuple[Path, str]]:
    base = (root / source.path).resolve() if source.path not in {"", "."} else root
    try:
        base.relative_to(root if root.is_dir() else root.parent)
    except ValueError:
        return
    if base.is_file():
        rel_path = base.relative_to(root.parent if not root.is_dir() else root).as_posix() if root != base else base.name
        if base.suffix.lower() in TEXT_SUFFIXES and base.stat().st_size <= MAX_FILE_BYTES:
            yield base, rel_path
        return
    if not base.is_dir():
        return
    for path in base.rglob("*"):
        try:
            if not (path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and path.stat().st_size <= MAX_FILE_BYTES):
                continue
            rel_path = path.relative_to(root).as_posix() if root.is_dir() else path.name
            source_rel = path.relative_to(base).as_posix()
            if not _matches_any(source_rel, source.include):
                continue
            if source.exclude and (_matches_any(source_rel, source.exclude) or _matches_any(rel_path, source.exclude)):
                continue
            yield path, rel_path
        except OSError:
            continue


def _metadata_content(resource: AuthorizedResource, source: IndexSource | None = None) -> str:
    parts = [
        resource.title,
        resource.description,
        resource.resource_id,
        resource.package_id,
        resource.kind,
        resource.version,
        resource.root_ref,
    ]
    if source is not None:
        parts.extend([source.path, source.role])
    return "\n".join(item for item in parts if item)


def _documents(resources: list[AuthorizedResource]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for resource in resources:
        policy_hash = _policy_hash(resource.indexing)
        if all(source.mode != "fulltext" for source in resource.sources):
            content = _metadata_content(resource, resource.sources[0] if resource.sources else None)
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            documents.append(
                {
                    "resource_id": resource.resource_id,
                    "package_id": resource.package_id,
                    "kind": resource.kind,
                    "relative_path": ".",
                    "title": resource.title,
                    "content": content,
                    "content_hash": content_hash,
                    "fingerprint": f"{resource.fingerprint}:{policy_hash}:{content_hash}",
                    "metadata": {"mode": "metadata", "root_ref": resource.root_ref, "version": resource.version},
                }
            )
            continue
        for source in resource.sources:
            if source.mode == "none":
                continue
            if source.mode == "metadata":
                content = _metadata_content(resource, source)
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                documents.append(
                    {
                        "resource_id": resource.resource_id,
                        "package_id": resource.package_id,
                        "kind": resource.kind,
                        "relative_path": source.path or ".",
                        "title": resource.title,
                        "content": content,
                        "content_hash": content_hash,
                        "fingerprint": f"{resource.fingerprint}:{policy_hash}:{content_hash}",
                        "metadata": {"mode": "metadata", "role": source.role, "root_ref": resource.root_ref, "version": resource.version},
                    }
                )
                continue
            for path, relative_path in _iter_source_files(resource.root, source):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                content = _metadata_content(resource, source) + "\n" + text
                content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                documents.append(
                    {
                        "resource_id": resource.resource_id,
                        "package_id": resource.package_id,
                        "kind": resource.kind,
                        "relative_path": relative_path,
                        "title": relative_path,
                        "content": content,
                        "content_hash": content_hash,
                        "fingerprint": f"{resource.fingerprint}:{policy_hash}:{relative_path}:{content_hash}",
                        "metadata": {"mode": "fulltext", "root_ref": resource.root_ref, "version": resource.version},
                    }
                )
    return documents


def index_path(project_root: Path, workplace_root: Path | None = None) -> Path:
    """Return the private derived search DB path."""

    if workplace_root is not None:
        return workplace_root / "runtime" / "search" / "local-resource-search.sqlite"
    return project_root / ".pf" / "runtime" / "local-resource-search" / "search.sqlite"


def sqlite_fts5_capability() -> dict[str, Any]:
    version = sqlite3.sqlite_version
    try:
        db = sqlite3.connect(":memory:")
    except sqlite3.Error as exc:
        return {"sqlite_version": version, "fts5_available": False, "error": _error_code(exc) or "sqlite_unavailable"}
    try:
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
        "CREATE TABLE IF NOT EXISTS resources ("
        "resource_id TEXT PRIMARY KEY, "
        "resource_type TEXT, "
        "version TEXT, "
        "fingerprint TEXT, "
        "indexing_policy_hash TEXT, "
        "root_ref TEXT, "
        "indexed_at TEXT, "
        "status TEXT NOT NULL, "
        "last_error TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "id INTEGER PRIMARY KEY, "
        "resource_id TEXT NOT NULL, "
        "package_id TEXT, "
        "kind TEXT, "
        "relative_path TEXT NOT NULL, "
        "title TEXT, "
        "content_hash TEXT, "
        "metadata TEXT, "
        "fingerprint TEXT, "
        "UNIQUE(resource_id, relative_path))"
    )
    db.execute("CREATE INDEX IF NOT EXISTS documents_resource_idx ON documents(resource_id)")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(title, content, document_id UNINDEXED, resource_id UNINDEXED)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS index_state ("
        "scope_key TEXT PRIMARY KEY, "
        "snapshot_checksum TEXT NOT NULL, "
        "allowed_resource_ids TEXT NOT NULL, "
        "status TEXT NOT NULL, "
        "generation TEXT NOT NULL, "
        "resource_count INTEGER NOT NULL, "
        "document_count INTEGER NOT NULL, "
        "failed_file_count INTEGER NOT NULL DEFAULT 0, "
        "last_successful_refresh TEXT, "
        "last_full_reconciliation TEXT, "
        "last_error TEXT)"
    )


def _check_schema(db: sqlite3.Connection) -> None:
    required = {"meta", "resources", "index_state", "documents", "documents_fts"}
    rows = db.execute("SELECT name FROM sqlite_master WHERE name IN ('meta', 'resources', 'index_state', 'documents', 'documents_fts')").fetchall()
    existing = {str(row[0]) for row in rows}
    if required - existing:
        raise LocalSearchError("index_schema_missing")
    current = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if not current or str(current[0]) != str(SCHEMA_VERSION):
        raise LocalSearchError("index_schema_mismatch")


def _delete_resource(db: sqlite3.Connection, resource_id: str) -> None:
    db.execute("DELETE FROM documents_fts WHERE resource_id=?", (resource_id,))
    db.execute("DELETE FROM documents WHERE resource_id=?", (resource_id,))
    db.execute("DELETE FROM resources WHERE resource_id=?", (resource_id,))


def _error_code(exc: BaseException) -> str:
    if isinstance(exc, LocalSearchError):
        return exc.code
    return str(exc) or type(exc).__name__


def _document_fingerprint_map(resources: list[AuthorizedResource]) -> dict[str, str]:
    return {f"{item['resource_id']}:{item['relative_path']}": str(item["fingerprint"]) for item in _documents(resources)}


def _stored_fingerprint_map(db: sqlite3.Connection, resource_ids: list[str]) -> dict[str, str]:
    if not resource_ids:
        return {}
    placeholders = ",".join("?" for _ in resource_ids)
    rows = db.execute(f"SELECT resource_id, relative_path, fingerprint FROM documents WHERE resource_id IN ({placeholders})", resource_ids).fetchall()
    return {f"{row[0]}:{row[1]}": str(row[2]) for row in rows}


def _scope_generation(snapshot: dict[str, Any], resource_ids: list[str], fingerprints: dict[str, str]) -> str:
    seed = {"snapshot": _snapshot_checksum(snapshot), "allowed_resource_ids": sorted(resource_ids), "fingerprints": fingerprints}
    return hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()[:16]


def build_index(project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None, full_reconciliation: bool = False) -> dict[str, Any]:
    resources = authorized_roots(project_root, snapshot)
    resource_ids = indexable_resource_ids(resources)
    path = index_path(project_root, workplace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    documents = _documents(resources)
    scope_key = _scope_key(snapshot)
    refreshed_at = _now_utc()
    fingerprints = {f"{item['resource_id']}:{item['relative_path']}": str(item["fingerprint"]) for item in documents}
    generation = _scope_generation(snapshot, resource_ids, fingerprints)
    db = sqlite3.connect(path)
    try:
        _ensure_schema(db)
        for resource in resources:
            _delete_resource(db, resource.resource_id)
            db.execute(
                "INSERT OR REPLACE INTO resources (resource_id, resource_type, version, fingerprint, indexing_policy_hash, root_ref, indexed_at, status, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (resource.resource_id, resource.kind, resource.version, resource.fingerprint, _policy_hash(resource.indexing), resource.root_ref, refreshed_at, "fresh", None),
            )
        for item in documents:
            cursor = db.execute(
                "INSERT OR REPLACE INTO documents (resource_id, package_id, kind, relative_path, title, content_hash, metadata, fingerprint) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item["resource_id"], item["package_id"], item["kind"], item["relative_path"], item["title"], item["content_hash"], _stable_json(item["metadata"]), item["fingerprint"]),
            )
            document_id = cursor.lastrowid
            if not document_id:
                row = db.execute("SELECT id FROM documents WHERE resource_id=? AND relative_path=?", (item["resource_id"], item["relative_path"])).fetchone()
                document_id = int(row[0])
            db.execute("DELETE FROM documents_fts WHERE document_id=?", (document_id,))
            db.execute("INSERT INTO documents_fts (title, content, document_id, resource_id) VALUES (?, ?, ?, ?)", (item["title"], item["content"], document_id, item["resource_id"]))
        db.execute(
            "INSERT OR REPLACE INTO index_state (scope_key, snapshot_checksum, allowed_resource_ids, status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (scope_key, _snapshot_checksum(snapshot), _stable_json(sorted(resource_ids)), "fresh", generation, len(resource_ids), len(documents), 0, refreshed_at, refreshed_at if full_reconciliation else None, None),
        )
        db.commit()
    finally:
        db.close()
    return {"status": "fresh", "indexed": len(documents), "resources": len(resource_ids), "snapshot_checksum": _snapshot_checksum(snapshot), "generation": generation}


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
                row = db.execute("SELECT status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error, allowed_resource_ids, snapshot_checksum FROM index_state WHERE scope_key=?", (scope_key,)).fetchone()
                current_resources = authorized_roots(project_root, snapshot or {})
                resource_ids = indexable_resource_ids(current_resources)
                if not row:
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = len(resource_ids) or 1
                    payload["error"] = "scope_not_indexed"
                    return payload
                if row[9] != _snapshot_checksum(snapshot or {}):
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = len(resource_ids) or 1
                    payload["error"] = "snapshot_checksum_changed"
                    return payload
                if json.loads(row[8] or "[]") != sorted(resource_ids):
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = len(resource_ids) or 1
                    payload["error"] = "allowed_resources_changed"
                    return payload
                missing_resources = [item for item in resource_ids if not db.execute("SELECT 1 FROM resources WHERE resource_id=?", (item,)).fetchone()]
                if missing_resources:
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = len(missing_resources)
                    payload["error"] = "resource_not_indexed"
                    return payload
                if verify_files and snapshot is not None:
                    current = _document_fingerprint_map(current_resources)
                    stored = _stored_fingerprint_map(db, resource_ids)
                    if stored != current:
                        payload.update({"status": "stale", "stale_resource_count": 1, "resource_count": row[2], "document_count": row[3], "failed_file_count": row[4], "last_successful_refresh": row[5], "last_full_reconciliation": row[6], "error": "document_fingerprint_changed"})
                        return payload
                payload.update({"status": row[0], "generation": row[1], "resource_count": row[2], "document_count": row[3], "failed_file_count": row[4], "last_successful_refresh": row[5], "last_full_reconciliation": row[6]})
                if row[7]:
                    payload["error"] = row[7]
            else:
                row = db.execute("SELECT count(*), count(*), COALESCE((SELECT count(*) FROM documents), 0), 0, max(indexed_at), max(indexed_at) FROM resources").fetchone()
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
    except (OSError, sqlite3.Error, LocalSearchError, json.JSONDecodeError) as exc:
        payload["status"] = "degraded"
        payload["error"] = _error_code(exc) or "index_unreadable"
    return payload


def mark_index_dirty(project_root: Path, snapshot: dict[str, Any] | None = None, *, workplace_root: Path | None = None, reason: str = "dirty") -> dict[str, Any]:
    path = index_path(project_root, workplace_root)
    payload = {"schema_version": 1, "kind": "pf.search_index.dirty_mark", "path": str(path), "reason": reason, "status": "missing", "marked_scope_count": 0}
    if not path.is_file():
        return payload
    db = sqlite3.connect(path)
    try:
        _check_schema(db)
        scope_key = _scope_key(snapshot) if snapshot is not None else None
        if scope_key:
            cursor = db.execute("UPDATE index_state SET status='stale', last_error=? WHERE scope_key=?", (reason, scope_key))
        else:
            cursor = db.execute("UPDATE index_state SET status='stale', last_error=?", (reason,))
        db.commit()
        payload["status"] = "stale" if cursor.rowcount else "missing"
        payload["marked_scope_count"] = int(cursor.rowcount or 0)
    finally:
        db.close()
    return payload


def maintenance_tick(project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None, verify_files: bool = True) -> dict[str, Any]:
    before = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=verify_files)
    action = "none"
    result: dict[str, Any] | None = None
    error = str(before.get("error") or "")
    try:
        if before.get("status") in {"missing", "stale"}:
            result = build_index(project_root, snapshot, workplace_root=workplace_root)
            action = "refresh"
        elif before.get("status") == "degraded" and error != "fts5_unavailable":
            result = rebuild_index(project_root, snapshot, workplace_root=workplace_root)
            action = "rebuild"
    except (OSError, sqlite3.Error, LocalSearchError) as exc:
        action = "failed_" + ("rebuild" if before.get("status") == "degraded" else "refresh")
        after_failure = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=False)
        after_failure["status"] = "degraded"
        after_failure["error"] = _error_code(exc)
        return {"schema_version": 1, "kind": "pf.search_index.maintenance_tick", "action": action, "before": before, "after": after_failure, "result": result}
    after = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=False)
    return {"schema_version": 1, "kind": "pf.search_index.maintenance_tick", "action": action, "before": before, "after": after, "result": result}


def search(project_root: Path, snapshot: dict[str, Any], *, query: Any, limit: Any = None, limitstart: Any = None, offset: Any = None, workplace_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise LocalSearchError("invalid_query")
    page_limit, start = pagination(limit=limit, limitstart=limitstart, offset=offset)
    path = index_path(project_root, workplace_root)
    scope_key = _scope_key(snapshot)
    resource_ids = indexable_resource_ids(authorized_roots(project_root, snapshot))
    state = index_status(project_root, snapshot, workplace_root=workplace_root, verify_files=False)
    if state.get("status") != "fresh":
        return {
            "schema_version": 1,
            "kind": "pf.search",
            "search_status": state.get("status"),
            "index_generation": state.get("generation"),
            "query": query,
            "total": 0,
            "limit": page_limit,
            "offset": start,
            "items": [],
            "results": [],
            "page": {"limit": page_limit, "limitstart": start, "offset": start, "returned": 0, "total": 0, "next_limitstart": None},
            "degraded_reason": state.get("error") or "index_not_fresh",
        }
    if not resource_ids:
        return {
            "schema_version": 1,
            "kind": "pf.search",
            "search_status": "fresh",
            "index_generation": state.get("generation"),
            "query": query,
            "total": 0,
            "limit": page_limit,
            "offset": start,
            "items": [],
            "results": [],
            "page": {"limit": page_limit, "limitstart": start, "offset": start, "returned": 0, "total": 0, "next_limitstart": None},
        }
    try:
        db = sqlite3.connect(path)
    except OSError as exc:
        raise LocalSearchError("search_unavailable") from exc
    fts_query = '"' + query.replace('"', '""') + '"'
    placeholders = ",".join("?" for _ in resource_ids)
    args = [fts_query, *resource_ids]
    try:
        try:
            total = int(db.execute(f"SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ? AND resource_id IN ({placeholders})", args).fetchone()[0])
            rows = db.execute(
                f"SELECT d.id, d.resource_id, d.package_id, d.kind, d.relative_path, d.metadata, bm25(documents_fts) FROM documents_fts JOIN documents d ON d.id = documents_fts.document_id WHERE documents_fts MATCH ? AND documents_fts.resource_id IN ({placeholders}) ORDER BY bm25(documents_fts), d.resource_id, d.relative_path LIMIT ? OFFSET ?",
                [*args, page_limit, start],
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise LocalSearchError("invalid_query" if "syntax" in str(exc).lower() else "search_unavailable") from exc
    finally:
        db.close()
    expected = _snapshot_checksum(snapshot)
    items: list[dict[str, Any]] = []
    for row in rows:
        metadata = json.loads(row[5] or "{}")
        items.append(
            {
                "document_id": row[0],
                "resource_id": row[1],
                "resource_type": row[3],
                "title": row[4],
                "provenance": {"package_id": row[2], "kind": row[3], "snapshot_checksum": expected},
                "canonical_path": row[4],
                "relative_path": row[4],
                "path_ref": f"{row[1]}:{row[4]}",
                "metadata": metadata,
                "match_reason": "content" if metadata.get("mode") == "fulltext" else "metadata",
                "match": {"fields": ["title", "content"], "rank": row[6], "reason": "FTS5 title/content match"},
            }
        )
    return {
        "schema_version": 1,
        "kind": "pf.search",
        "search_status": "fresh",
        "index_generation": state.get("generation"),
        "scope_key": scope_key,
        "query": query,
        "total": total,
        "limit": page_limit,
        "offset": start,
        "items": items,
        "results": items,
        "page": {"limit": page_limit, "limitstart": start, "offset": start, "returned": len(rows), "total": total, "next_limitstart": start + len(rows) if start + len(rows) < total else None},
    }
