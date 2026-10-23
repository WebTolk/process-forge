"""Workplace-owned, snapshot-authorized SQLite FTS5 local resource search.

The index is resource-oriented: documents are stored once per resource in the
workplace DB. Project snapshots only authorize which resource identities may be
queried; they do not own or duplicate indexed documents.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, cast

MAX_FILE_BYTES = 1_000_000
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".rst",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".csv",
}
# Version 5 also invalidates derived rows produced before canonical source-root
# containment, even though the SQL table layout is unchanged.
SCHEMA_VERSION = 6
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
    """Stateful application service for the workplace local resource index.

    A project snapshot may be supplied for backward-compatible scoped
    maintenance and for query authorization.  A workplace maintenance snapshot
    uses ``search_index_scope: workplace`` and owns the one physical index.
    """

    project_root: Path
    snapshot: dict[str, Any] | None = None
    workplace_root: Path | None = None

    def status(self, *, verify_files: bool = False) -> dict[str, Any]:
        return index_status(
            self.project_root,
            self.snapshot,
            workplace_root=self.workplace_root,
            verify_files=verify_files,
        )

    def refresh(self) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return build_index(
            self.project_root, self.snapshot, workplace_root=self.workplace_root
        )

    def rebuild(self) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return rebuild_index(
            self.project_root, self.snapshot, workplace_root=self.workplace_root
        )

    def mark_dirty(self, *, reason: str = "dirty") -> dict[str, Any]:
        return mark_index_dirty(
            self.project_root,
            self.snapshot,
            workplace_root=self.workplace_root,
            reason=reason,
        )

    def maintenance_tick(self, *, verify_files: bool = True) -> dict[str, Any]:
        if self.snapshot is None:
            raise LocalSearchError("snapshot_required")
        return maintenance_tick(
            self.project_root,
            self.snapshot,
            workplace_root=self.workplace_root,
            verify_files=verify_files,
        )

    def search(
        self,
        *,
        query: Any,
        limit: Any = None,
        limitstart: Any = None,
        offset: Any = None,
    ) -> dict[str, Any]:
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


def search_material(
    documents: list[dict[str, Any]],
    query: str,
    limit: int,
    start: int,
    *,
    error: Callable[[], Callable[[str], Exception]],
) -> dict[str, Any]:
    try:
        db = sqlite3.connect(":memory:")
        try:
            db.execute("CREATE VIRTUAL TABLE material USING fts5(title, content)")
            db.executemany(
                "INSERT INTO material(rowid,title,content) VALUES(?,?,?)",
                (
                    (i + 1, doc["title"], doc["content"])
                    for i, doc in enumerate(documents)
                ),
            )
            phrase = '"' + query.replace('"', '""') + '"'
            total = db.execute(
                "SELECT count(*) FROM material WHERE material MATCH ?", (phrase,)
            ).fetchone()[0]
            matches = db.execute(
                "SELECT rowid FROM material WHERE material MATCH ? ORDER BY bm25(material), rowid LIMIT ? OFFSET ?",
                (phrase, limit, start),
            ).fetchall()
        finally:
            db.close()
    except sqlite3.Error as exc:
        raise error()("work_search_unavailable") from exc
    results = [
        {key: value for key, value in documents[row[0] - 1].items() if key != "content"}
        for row in matches
    ]
    return {
        "query": query,
        "total": total,
        "limit": limit,
        "offset": start,
        "results": results,
        "items": results,
        "page": {
            "limit": limit,
            "offset": start,
            "limitstart": start,
            "returned": len(results),
            "total": total,
            "next_limitstart": start + len(results)
            if start + len(results) < total
            else None,
        },
    }


def _snapshot_checksum(snapshot: dict[str, Any]) -> str:
    value = (
        cast(dict[str, Any], snapshot.get("snapshot"))
        if isinstance(snapshot.get("snapshot"), dict)
        else {}
    )
    return str(value.get("checksum") or value.get("sha256") or value.get("id") or "")


def _scope_key(snapshot: dict[str, Any]) -> str:
    if str(snapshot.get("search_index_scope") or "") == "workplace":
        return "workplace"
    checksum = _snapshot_checksum(snapshot)
    return checksum or "snapshot-unknown"


def _now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


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


def pagination(
    *, limit: Any = None, limitstart: Any = None, offset: Any = None
) -> tuple[int, int]:
    page_limit = _as_int(limit, default=DEFAULT_LIMIT, maximum=MAX_LIMIT)
    if (
        limitstart not in (None, "")
        and offset not in (None, "")
        and str(limitstart) != str(offset)
    ):
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
    resolved = (
        snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
    )
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
    return (
        "sha256:" + hashlib.sha256(_stable_json(identity).encode("utf-8")).hexdigest()
    )


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
        elif legacy in {
            "metadata",
            "metadata_first",
            "index_only",
            "source_tree",
            "symbols",
        } or (
            isinstance(row.get("path_ref"), dict)
            and row["path_ref"].get("registry") == "external_resources"
            and legacy in {"", "full_text"}
        ):
            raw = {
                "enabled": True,
                "mode": "metadata",
                "fields": ["title", "description", "tags", "path"],
            }
        elif legacy in {"fulltext", "always_index", "snapshot_authorized"}:
            raw = {
                "enabled": True,
                "mode": "fulltext",
                "fields": ["title", "description", "path"],
                "sources": [
                    {
                        "path": ".",
                        "mode": "fulltext",
                        "include": ["**/*.md", "**/*.txt", "**/*.rst"],
                    }
                ],
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
    source_rows = (
        cast(list[Any], raw.get("sources"))
        if isinstance(raw.get("sources"), list)
        else []
    )
    sources = tuple(
        _normalize_source(item, mode) for item in source_rows if isinstance(item, dict)
    )
    if not sources and mode != "none":
        sources = (
            _normalize_source({"path": ".", "mode": mode, "include": ["**/*"]}, mode),
        )
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


def _denied_path_reference(
    project_root: Path, reference: object, workplace_root: Path | None
) -> bool:
    """Recognize a resolver's explicit containment refusal, never missing access."""
    if not isinstance(reference, dict):
        return False
    from processforge_core.resources.snapshot import resolve_garage_path_ref

    try:
        resolution = resolve_garage_path_ref(
            project_root, reference, workplace_root or project_root
        )
    except (OSError, RuntimeError, ValueError):
        raise LocalSearchError("document_scan_failed") from None
    return resolution.get("status") == "unresolved" and resolution.get("reason") in {
        "invalid_path_ref: relative_path escapes declared package root",
        "invalid_path_ref: registry path escapes workplace root",
        "invalid_path_ref: relative_path escapes declared registry root",
        "invalid_path_ref: relative_path escapes project flow root",
    }


def authorized_roots(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    strict: bool = False,
    workplace_root: Path | None = None,
) -> list[AuthorizedResource]:
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
        raw_paths.extend(
            row.get(key)
            for key in ("resolved_path", "local_path", "path")
            if row.get(key)
        )
        reference = row.get("path_ref")
        if (
            not raw_paths
            and isinstance(reference, dict)
            and reference.get("registry") == "external_resources"
            and policy.get("mode") == "metadata"
            and all(
                not isinstance(source, dict) or source.get("mode") != "fulltext"
                for source in policy.get("sources", [])
            )
        ):
            # External references have no local body. Anchor metadata identity
            # without scanning the root or fetching the referenced URL.
            raw_paths.append(project_root)
        if strict and not raw_paths:
            if _denied_path_reference(project_root, reference, workplace_root):
                continue
            raise LocalSearchError("document_scan_failed")
        for raw_path in raw_paths:
            value = str(raw_path or "").strip()
            if not value or value.startswith("<") or "://" in value:
                if strict:
                    raise LocalSearchError("document_scan_failed")
                continue
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = project_root / candidate
            try:
                root = candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                if strict:
                    raise LocalSearchError("document_scan_failed") from None
                continue
            identity = (resource_id, str(root))
            if identity in seen:
                continue
            seen.add(identity)
            sources = tuple(
                _normalize_source(item, str(policy.get("mode") or "metadata"))
                for item in policy.get("sources", [])
                if isinstance(item, dict)
            )
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
                    root_ref=_stable_json(row.get("path_ref"))
                    if isinstance(row.get("path_ref"), dict)
                    else str(root),
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
    # ``root`` is already canonicalized by ``authorized_roots``.  A file root
    # authorizes that one file only; resolving a source relative to its parent
    # would otherwise make ``../sibling`` readable.  Directory sources and
    # every discovered path must remain canonically below the authorized root,
    # including symlinks which point outside it.
    try:
        root = root.resolve()
        root_stat = root.stat()
    except (OSError, RuntimeError) as error:
        raise LocalSearchError("document_scan_failed") from error
    if stat.S_ISREG(root_stat.st_mode):
        if source.path not in {"", "."}:
            return
        base = root
    else:
        try:
            base = (root / source.path).resolve()
        except OSError as error:
            raise LocalSearchError("document_scan_failed") from error
        except RuntimeError:
            return
    try:
        base.relative_to(root)
    except ValueError:
        return
    try:
        base_stat = base.stat()
    except FileNotFoundError as error:
        # A missing optional source is empty only while its required root is
        # still available. A resolved root can disappear between the two stats.
        if base == root:
            raise LocalSearchError("document_scan_failed") from error
        try:
            root.stat()
        except OSError as root_error:
            raise LocalSearchError("document_scan_failed") from root_error
        return
    except OSError as error:
        raise LocalSearchError("document_scan_failed") from error
    if stat.S_ISREG(base_stat.st_mode):
        rel_path = (
            base.relative_to(
                root.parent if stat.S_ISREG(root_stat.st_mode) else root
            ).as_posix()
            if root != base
            else base.name
        )
        if base.suffix.lower() in TEXT_SUFFIXES and base_stat.st_size <= MAX_FILE_BYTES:
            # Treat an explicit file source exactly like a file discovered
            # beneath a directory source.  In particular, an explicit path
            # must still satisfy include/exclude authorization patterns.
            source_rel = base.name
            if _matches_any(source_rel, source.include) and not (
                source.exclude
                and (
                    _matches_any(source_rel, source.exclude)
                    or _matches_any(rel_path, source.exclude)
                )
            ):
                yield base, rel_path
        return
    if not stat.S_ISDIR(base_stat.st_mode):
        return

    def scan_failed(error: OSError) -> None:
        raise LocalSearchError("document_scan_failed") from error

    for folder, _directories, names in os.walk(
        base, onerror=scan_failed, followlinks=False
    ):
        # Do not descend through directory links/junctions or excluded subtrees.
        # Containment must be enforced before traversal, as well as before reads.
        permitted_directories = []
        for name in _directories:
            directory = Path(folder) / name
            relative = directory.relative_to(base).as_posix() + "/"
            root_relative = directory.relative_to(root).as_posix() + "/"
            if source.exclude and (
                _matches_any(relative, source.exclude)
                or _matches_any(root_relative, source.exclude)
            ):
                continue
            try:
                resolved = directory.resolve()
                if resolved != directory.absolute() or not resolved.is_relative_to(
                    root
                ):
                    continue
            except OSError as error:
                raise LocalSearchError("document_scan_failed") from error
            except RuntimeError:
                continue
            permitted_directories.append(name)
        _directories[:] = permitted_directories
        for name in names:
            path = Path(folder) / name
            try:
                if path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                rel_path = path.relative_to(root).as_posix()
                source_rel = path.relative_to(base).as_posix()
                if not _matches_any(source_rel, source.include):
                    continue
                if source.exclude and (
                    _matches_any(source_rel, source.exclude)
                    or _matches_any(rel_path, source.exclude)
                ):
                    continue
                canonical_path = path.resolve()
                try:
                    canonical_path.relative_to(root)
                except ValueError:
                    continue
                path_stat = path.stat()
                if (
                    not stat.S_ISREG(path_stat.st_mode)
                    or path_stat.st_size > MAX_FILE_BYTES
                ):
                    continue
                yield path, rel_path
            except OSError as error:
                raise LocalSearchError("document_scan_failed") from error
            except RuntimeError:
                continue


def _metadata_content(
    resource: AuthorizedResource, source: IndexSource | None = None
) -> str:
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


def _resource_metadata_hash(resource: AuthorizedResource) -> str:
    """Fingerprint indexed metadata without opening the resource's source files."""
    value = [
        resource.resource_id,
        resource.package_id,
        resource.kind,
        resource.title,
        resource.description,
        resource.version,
        resource.root_ref,
        _policy_hash(resource.indexing),
    ]
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _documents(resources: list[AuthorizedResource]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    positions: dict[tuple[str, str, str], int] = {}
    metadata_hashes = {
        (
            resource.resource_id,
            hashlib.sha256(str(resource.root).encode("utf-8")).hexdigest(),
        ): _resource_metadata_hash(resource)
        for resource in resources
    }

    def append(document: dict[str, Any]) -> None:
        document["metadata"]["resource_metadata_hash"] = metadata_hashes[
            (str(document["resource_id"]), str(document["metadata"]["root_id"]))
        ]
        # Multiple sources may intentionally overlap (for example, a source
        # tree and an explicit file).  A logical document is identified by
        # its resource and canonical relative path, not by the source that
        # happened to discover it first.
        identity = (
            str(document["resource_id"]),
            str(document["metadata"]["root_id"]),
            str(document["relative_path"]),
        )
        if identity not in positions:
            positions[identity] = len(documents)
            documents.append(document)
        elif (
            document["metadata"]["mode"] == "fulltext"
            and documents[positions[identity]]["metadata"]["mode"] != "fulltext"
        ):
            # An explicit fulltext source must not be hidden by a metadata
            # source for the same path merely because of source ordering.
            documents[positions[identity]] = document

    for resource in resources:
        policy_hash = _policy_hash(resource.indexing)
        root_id = hashlib.sha256(str(resource.root).encode("utf-8")).hexdigest()
        if all(source.mode != "fulltext" for source in resource.sources):
            content = _metadata_content(
                resource, resource.sources[0] if resource.sources else None
            )
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            append(
                {
                    "resource_id": resource.resource_id,
                    "package_id": resource.package_id,
                    "kind": resource.kind,
                    "relative_path": ".",
                    "title": resource.title,
                    "content": content,
                    "content_hash": content_hash,
                    "fingerprint": f"{resource.fingerprint}:{policy_hash}:{content_hash}",
                    "metadata": {
                        "mode": "metadata",
                        "root_id": root_id,
                        "root_ref": resource.root_ref,
                        "version": resource.version,
                    },
                }
            )
            continue
        for source in resource.sources:
            if source.mode == "none":
                continue
            if source.mode == "metadata":
                content = _metadata_content(resource, source)
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                append(
                    {
                        "resource_id": resource.resource_id,
                        "package_id": resource.package_id,
                        "kind": resource.kind,
                        "relative_path": source.path or ".",
                        "title": resource.title,
                        "content": content,
                        "content_hash": content_hash,
                        "fingerprint": f"{resource.fingerprint}:{policy_hash}:{content_hash}",
                        "metadata": {
                            "mode": "metadata",
                            "root_id": root_id,
                            "role": source.role,
                            "root_ref": resource.root_ref,
                            "version": resource.version,
                        },
                    }
                )
                continue
            for path, relative_path in _iter_source_files(resource.root, source):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError as error:
                    raise LocalSearchError("document_read_failed") from error
                content = _metadata_content(resource, source) + "\n" + text
                content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                append(
                    {
                        "resource_id": resource.resource_id,
                        "package_id": resource.package_id,
                        "kind": resource.kind,
                        "relative_path": relative_path,
                        "title": relative_path,
                        "content": content,
                        "content_hash": content_hash,
                        "fingerprint": f"{resource.fingerprint}:{policy_hash}:{relative_path}:{content_hash}",
                        "metadata": {
                            "mode": "fulltext",
                            "root_id": root_id,
                            "root_ref": resource.root_ref,
                            "version": resource.version,
                        },
                    }
                )
    return documents


def index_path(project_root: Path, workplace_root: Path | None = None) -> Path:
    """Return the private derived search DB path."""

    if workplace_root is not None:
        return workplace_root / "runtime" / "search" / "local-resource-search.sqlite"
    return project_root / ".pf" / "runtime" / "local-resource-search" / "search.sqlite"


def authorized_coverage(
    project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None
) -> dict[str, Any]:
    """Describe physical index coverage, without equating it with material proof."""
    identifiers = authorized_resource_ids(snapshot)
    result: dict[str, Any] = {
        "authorized_resource_count": len(identifiers),
        "indexed_resource_count": 0,
        "document_count": 0,
        "missing_resource_ids": identifiers,
        "status": "empty" if not identifiers else "none",
    }
    path = index_path(project_root, workplace_root)
    if not identifiers or not path.is_file():
        return result
    counts: dict[str, int] = {}
    try:
        db = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.0
        )
        try:
            for start in range(0, len(identifiers), 128):
                page = identifiers[start : start + 128]
                marks = ",".join("?" for _ in page)
                counts.update(
                    db.execute(
                        f"SELECT resource_id,count(*) FROM documents WHERE resource_id IN ({marks}) GROUP BY resource_id",
                        page,
                    ).fetchall()
                )
        finally:
            db.close()
    except (OSError, sqlite3.Error):
        return {**result, "status": "unavailable"}
    missing = [identifier for identifier in identifiers if identifier not in counts]
    return {
        **result,
        "indexed_resource_count": len(counts),
        "document_count": sum(counts.values()),
        "missing_resource_ids": missing,
        "status": "complete" if not missing else "partial" if counts else "none",
    }


def sqlite_fts5_capability() -> dict[str, Any]:
    version = sqlite3.sqlite_version
    try:
        db = sqlite3.connect(":memory:")
    except sqlite3.Error as exc:
        return {
            "sqlite_version": version,
            "fts5_available": False,
            "error": _error_code(exc) or "sqlite_unavailable",
        }
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
    db.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    current = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if current and str(current[0]) != str(SCHEMA_VERSION):
        raise LocalSearchError("index_schema_mismatch")
    db.execute(
        "INSERT OR REPLACE INTO meta VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    db.execute(
        "INSERT OR REPLACE INTO meta VALUES (?, ?)",
        ("sqlite_version", sqlite3.sqlite_version),
    )
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
        "root_id TEXT NOT NULL, "
        "title TEXT, "
        "content_hash TEXT, "
        "metadata TEXT, "
        "fingerprint TEXT, "
        "UNIQUE(resource_id, root_id, relative_path))"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS documents_resource_idx ON documents(resource_id)"
    )
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(title, content, document_id UNINDEXED, resource_id UNINDEXED)"
    )
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
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE name IN ('meta', 'resources', 'index_state', 'documents', 'documents_fts')"
    ).fetchall()
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


def _document_key(resource_id: str, relative_path: str, root_id: str) -> str:
    return _stable_json([resource_id, root_id, relative_path])


def _document_fingerprint_map(resources: list[AuthorizedResource]) -> dict[str, str]:
    return {
        _document_key(
            item["resource_id"], item["relative_path"], item["metadata"]["root_id"]
        ): str(item["fingerprint"])
        for item in _documents(resources)
    }


def _stored_fingerprint_map(
    db: sqlite3.Connection, resource_ids: list[str]
) -> dict[str, str]:
    if not resource_ids:
        return {}
    placeholders = ",".join("?" for _ in resource_ids)
    rows = db.execute(
        f"SELECT resource_id, relative_path, root_id, fingerprint FROM documents WHERE resource_id IN ({placeholders})",
        resource_ids,
    ).fetchall()
    return {_document_key(row[0], row[1], row[2]): str(row[3]) for row in rows}


def _scope_generation(
    snapshot: dict[str, Any], resource_ids: list[str], fingerprints: dict[str, str]
) -> str:
    seed = {
        "snapshot": _snapshot_checksum(snapshot),
        "allowed_resource_ids": sorted(resource_ids),
        "fingerprints": fingerprints,
    }
    return hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()[:16]


def _resource_fingerprints(resources: list[AuthorizedResource]) -> dict[str, str]:
    """Bind stored resource identity to every actual root, including empty roots."""
    roots: dict[str, set[str]] = {}
    for resource in resources:
        roots.setdefault(resource.resource_id, set()).add(str(resource.root))
    return {
        resource.resource_id: "sha256:"
        + hashlib.sha256(
            _stable_json(
                [resource.fingerprint, sorted(roots[resource.resource_id])]
            ).encode("utf-8")
        ).hexdigest()
        for resource in resources
    }


def _refresh_catalogue_metadata(
    db: sqlite3.Connection,
    project_root: Path,
    catalogue: dict[str, Any],
    refreshed_at: str,
) -> None:
    """Publish known catalogue coverage using stored rows, never unselected bodies."""
    db.execute(
        "UPDATE index_state SET status='stale', last_error='allowed_resources_changed' WHERE scope_key='workplace'"
    )
    try:
        resources = authorized_roots(
            project_root, catalogue, strict=True, workplace_root=project_root
        )
    except LocalSearchError:
        return
    resource_ids = indexable_resource_ids(resources)
    resource_fingerprints = _resource_fingerprints(resources)
    expected = {
        item.resource_id: (
            item.kind,
            item.version,
            resource_fingerprints[item.resource_id],
            _policy_hash(item.indexing),
            item.root_ref,
            "fresh",
            None,
        )
        for item in resources
    }
    stored = {
        str(row[0]): tuple(row[1:])
        for row in db.execute(
            "SELECT resource_id, resource_type, version, fingerprint, indexing_policy_hash, root_ref, status, last_error FROM resources"
        )
    }
    if expected != stored:
        return
    expected_metadata = {
        (
            resource.resource_id,
            hashlib.sha256(str(resource.root).encode("utf-8")).hexdigest(),
        ): _resource_metadata_hash(resource)
        for resource in resources
    }
    present_metadata: set[tuple[str, str]] = set()
    for resource_id, text in db.execute("SELECT resource_id, metadata FROM documents"):
        try:
            metadata = json.loads(text)
        except (TypeError, ValueError):
            return
        if not isinstance(metadata, dict):
            return
        identity = (str(resource_id), str(metadata.get("root_id")))
        expected_hash = expected_metadata.get(identity)
        if (
            expected_hash is None
            or metadata.get("resource_metadata_hash") != expected_hash
        ):
            return
        present_metadata.add(identity)
    for resource in resources:
        needs_metadata = all(
            source.mode != "fulltext" for source in resource.sources
        ) or any(source.mode == "metadata" for source in resource.sources)
        identity = (
            resource.resource_id,
            hashlib.sha256(str(resource.root).encode("utf-8")).hexdigest(),
        )
        if needs_metadata and identity not in present_metadata:
            return
    fingerprints = _stored_fingerprint_map(db, resource_ids)
    generation = _scope_generation(catalogue, resource_ids, fingerprints)
    previous = db.execute(
        "SELECT last_full_reconciliation FROM index_state WHERE scope_key='workplace'"
    ).fetchone()
    db.execute(
        "INSERT OR REPLACE INTO index_state (scope_key, snapshot_checksum, allowed_resource_ids, status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "workplace",
            _snapshot_checksum(catalogue),
            _stable_json(sorted(resource_ids)),
            "fresh",
            generation,
            len(resource_ids),
            len(fingerprints),
            0,
            refreshed_at,
            previous[0] if previous else None,
            None,
        ),
    )


def build_index(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    workplace_root: Path | None = None,
    full_reconciliation: bool = False,
    _prepared: tuple[list[AuthorizedResource], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if _prepared is None:
        resources = authorized_roots(
            project_root, snapshot, strict=True, workplace_root=workplace_root
        )
        documents = _documents(resources)
    else:
        resources, documents = _prepared
    resource_ids = indexable_resource_ids(resources)
    resource_fingerprints = _resource_fingerprints(resources)
    path = index_path(project_root, workplace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    scope_key = _scope_key(snapshot)
    refreshed_at = _now_utc()
    fingerprints = {
        _document_key(
            item["resource_id"], item["relative_path"], item["metadata"]["root_id"]
        ): str(item["fingerprint"])
        for item in documents
    }
    generation = _scope_generation(snapshot, resource_ids, fingerprints)
    db = sqlite3.connect(path)
    try:
        _ensure_schema(db)
        # A Workplace refresh is an authoritative reconciliation of its
        # registered catalogue.  Retaining a removed package here would allow
        # an old project snapshot to query an orphaned document from the shared
        # DB, so remove every no-longer-registered resource before upserting.
        if _scope_key(snapshot) == "workplace":
            stored_ids = [
                str(row[0])
                for row in db.execute("SELECT resource_id FROM resources").fetchall()
            ]
            for resource_id in stored_ids:
                if resource_id not in resource_ids:
                    _delete_resource(db, resource_id)
        elif snapshot.get("search_index_scope") == "resources":
            # A selected resource may have been explicitly disabled. Retire its
            # old derived rows without reconciling any unselected resource.
            for record in _resource_records(snapshot):
                resource_id = str(record.get("id") or record.get("resource_id") or "")
                if resource_id and resource_id not in resource_ids:
                    _delete_resource(db, resource_id)
        for resource in resources:
            _delete_resource(db, resource.resource_id)
            db.execute(
                "INSERT OR REPLACE INTO resources (resource_id, resource_type, version, fingerprint, indexing_policy_hash, root_ref, indexed_at, status, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resource.resource_id,
                    resource.kind,
                    resource.version,
                    resource_fingerprints[resource.resource_id],
                    _policy_hash(resource.indexing),
                    resource.root_ref,
                    refreshed_at,
                    "fresh",
                    None,
                ),
            )
        for item in documents:
            cursor = db.execute(
                "INSERT OR REPLACE INTO documents (resource_id, package_id, kind, relative_path, root_id, title, content_hash, metadata, fingerprint) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["resource_id"],
                    item["package_id"],
                    item["kind"],
                    item["relative_path"],
                    item["metadata"]["root_id"],
                    item["title"],
                    item["content_hash"],
                    _stable_json(item["metadata"]),
                    item["fingerprint"],
                ),
            )
            document_id = cursor.lastrowid
            if not document_id:
                row = db.execute(
                    "SELECT id FROM documents WHERE resource_id=? AND root_id=? AND relative_path=?",
                    (
                        item["resource_id"],
                        item["metadata"]["root_id"],
                        item["relative_path"],
                    ),
                ).fetchone()
                document_id = int(row[0])
            db.execute("DELETE FROM documents_fts WHERE document_id=?", (document_id,))
            db.execute(
                "INSERT INTO documents_fts (title, content, document_id, resource_id) VALUES (?, ?, ?, ?)",
                (item["title"], item["content"], document_id, item["resource_id"]),
            )
        db.execute(
            "INSERT OR REPLACE INTO index_state (scope_key, snapshot_checksum, allowed_resource_ids, status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                scope_key,
                _snapshot_checksum(snapshot),
                _stable_json(sorted(resource_ids)),
                "fresh",
                generation,
                len(resource_ids),
                len(documents),
                0,
                refreshed_at,
                refreshed_at if full_reconciliation else None,
                None,
            ),
        )
        catalogue = snapshot.get("selected_catalogue_metadata")
        if snapshot.get("search_index_scope") == "resources" and isinstance(
            catalogue, dict
        ):
            _refresh_catalogue_metadata(db, project_root, catalogue, refreshed_at)
        db.commit()
    finally:
        db.close()
    return {
        "status": "fresh",
        "indexed": len(documents),
        "resources": len(resource_ids),
        "snapshot_checksum": _snapshot_checksum(snapshot),
        "generation": generation,
    }


def rebuild_index(
    project_root: Path, snapshot: dict[str, Any], *, workplace_root: Path | None = None
) -> dict[str, Any]:
    resources = authorized_roots(
        project_root, snapshot, strict=True, workplace_root=workplace_root
    )
    documents = _documents(resources)
    path = index_path(project_root, workplace_root)
    path.unlink(missing_ok=True)
    return build_index(
        project_root,
        snapshot,
        workplace_root=workplace_root,
        full_reconciliation=True,
        _prepared=(resources, documents),
    )


def index_status(
    project_root: Path,
    snapshot: dict[str, Any] | None = None,
    *,
    workplace_root: Path | None = None,
    verify_files: bool = False,
) -> dict[str, Any]:
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
        db = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.0
        )
        try:
            _check_schema(db)
            scope_key = _scope_key(snapshot) if snapshot is not None else None
            if scope_key:
                row = db.execute(
                    "SELECT status, generation, resource_count, document_count, failed_file_count, last_successful_refresh, last_full_reconciliation, last_error, allowed_resource_ids, snapshot_checksum FROM index_state WHERE scope_key=?",
                    (scope_key,),
                ).fetchone()
                current_resources = authorized_roots(
                    project_root,
                    snapshot or {},
                    strict=verify_files,
                    workplace_root=workplace_root,
                )
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
                missing_resources = [
                    item
                    for item in resource_ids
                    if not db.execute(
                        "SELECT 1 FROM resources WHERE resource_id=?", (item,)
                    ).fetchone()
                ]
                if missing_resources:
                    payload["status"] = "stale"
                    payload["stale_resource_count"] = len(missing_resources)
                    payload["error"] = "resource_not_indexed"
                    return payload
                if verify_files and snapshot is not None:
                    current = _document_fingerprint_map(current_resources)
                    stored = _stored_fingerprint_map(db, resource_ids)
                    expected_resources = _resource_fingerprints(current_resources)
                    stored_resources = {
                        str(item[0]): str(item[1])
                        for item in db.execute(
                            "SELECT resource_id, fingerprint FROM resources"
                        )
                        if str(item[0]) in expected_resources
                    }
                    if stored != current or expected_resources != stored_resources:
                        payload.update(
                            {
                                "status": "stale",
                                "stale_resource_count": 1,
                                "resource_count": row[2],
                                "document_count": row[3],
                                "failed_file_count": row[4],
                                "last_successful_refresh": row[5],
                                "last_full_reconciliation": row[6],
                                "error": "document_fingerprint_changed",
                            }
                        )
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
                row = db.execute(
                    "SELECT count(*), count(*), COALESCE((SELECT count(*) FROM documents), 0), 0, max(indexed_at), max(indexed_at) FROM resources"
                ).fetchone()
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


def mark_index_dirty(
    project_root: Path,
    snapshot: dict[str, Any] | None = None,
    *,
    workplace_root: Path | None = None,
    reason: str = "dirty",
) -> dict[str, Any]:
    path = index_path(project_root, workplace_root)
    payload = {
        "schema_version": 1,
        "kind": "pf.search_index.dirty_mark",
        "path": str(path),
        "reason": reason,
        "status": "missing",
        "marked_scope_count": 0,
    }
    if not path.is_file():
        return payload
    db = sqlite3.connect(path, timeout=0.0)
    try:
        _check_schema(db)
        scope_key = (
            _scope_key(snapshot)
            if snapshot is not None
            and snapshot.get("search_index_scope") != "workplace"
            else None
        )
        if scope_key:
            cursor = db.execute(
                "UPDATE index_state SET status='stale', last_error=? WHERE scope_key=?",
                (reason, scope_key),
            )
        else:
            cursor = db.execute(
                "UPDATE index_state SET status='stale', last_error=?", (reason,)
            )
        db.commit()
        payload["status"] = "stale" if cursor.rowcount else "missing"
        payload["marked_scope_count"] = int(cursor.rowcount or 0)
    finally:
        db.close()
    return payload


def maintenance_tick(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    workplace_root: Path | None = None,
    verify_files: bool = True,
) -> dict[str, Any]:
    before = index_status(
        project_root, snapshot, workplace_root=workplace_root, verify_files=verify_files
    )
    action = "none"
    result: dict[str, Any] | None = None
    error = str(before.get("error") or "")
    if error in {"document_read_failed", "document_scan_failed"}:
        return {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance_tick",
            "action": "failed_refresh",
            "before": before,
            "after": {**before, "status": "degraded"},
            "result": None,
        }
    try:
        if before.get("status") in {"missing", "stale"}:
            result = build_index(project_root, snapshot, workplace_root=workplace_root)
            action = "refresh"
        elif before.get("status") == "degraded" and error != "fts5_unavailable":
            result = rebuild_index(
                project_root, snapshot, workplace_root=workplace_root
            )
            action = "rebuild"
    except (OSError, sqlite3.Error, LocalSearchError) as exc:
        action = "failed_" + (
            "rebuild" if before.get("status") == "degraded" else "refresh"
        )
        after_failure = index_status(
            project_root, snapshot, workplace_root=workplace_root, verify_files=False
        )
        after_failure["status"] = "degraded"
        after_failure["error"] = _error_code(exc)
        return {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance_tick",
            "action": action,
            "before": before,
            "after": after_failure,
            "result": result,
        }
    after = index_status(
        project_root, snapshot, workplace_root=workplace_root, verify_files=False
    )
    return {
        "schema_version": 1,
        "kind": "pf.search_index.maintenance_tick",
        "action": action,
        "before": before,
        "after": after,
        "result": result,
    }


def _empty_search_result(
    query: str, limit: int, start: int, state: dict[str, Any]
) -> dict[str, Any]:
    """Keep the released unavailable-query shape without data or private errors."""
    return {
        "schema_version": 1,
        "kind": "pf.search",
        "search_status": state.get("status"),
        "index_generation": state.get("generation"),
        "query": query,
        "total": 0,
        "limit": limit,
        "offset": start,
        "items": [],
        "results": [],
        "page": {
            "limit": limit,
            "limitstart": start,
            "offset": start,
            "returned": 0,
            "total": 0,
            "next_limitstart": None,
        },
        "degraded_reason": state.get("error") or "index_not_fresh",
    }


def _sqlite_busy(error: sqlite3.Error) -> bool:
    code = getattr(error, "sqlite_errorcode", None)
    return isinstance(code, int) and code & 0xFF in {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    }


def search(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    query: Any,
    limit: Any = None,
    limitstart: Any = None,
    offset: Any = None,
    workplace_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise LocalSearchError("invalid_query")
    page_limit, start = pagination(limit=limit, limitstart=limitstart, offset=offset)
    path = index_path(project_root, workplace_root)
    scope_key = _scope_key(snapshot)
    resource_ids = indexable_resource_ids(authorized_roots(project_root, snapshot))
    # The physical database is maintained from the Workplace resource
    # catalogue.  A project snapshot is deliberately only an authorization
    # filter for the query and must not make a fresh Workplace index appear
    # stale merely because another project has a different checksum.
    state = index_status(
        project_root,
        None if workplace_root is not None else snapshot,
        workplace_root=workplace_root,
        verify_files=False,
    )
    if state.get("status") != "fresh":
        return _empty_search_result(query, page_limit, start, state)
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
            "page": {
                "limit": page_limit,
                "limitstart": start,
                "offset": start,
                "returned": 0,
                "total": 0,
                "next_limitstart": None,
            },
        }
    try:
        db = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.0
        )
    except (OSError, sqlite3.Error) as exc:
        if isinstance(exc, sqlite3.Error) and _sqlite_busy(exc):
            return _empty_search_result(
                query,
                page_limit,
                start,
                {**state, "status": "degraded", "error": "search_database_busy"},
            )
        raise LocalSearchError("search_unavailable") from exc
    fts_query = '"' + query.replace('"', '""') + '"'
    placeholders = ",".join("?" for _ in resource_ids)
    args = [fts_query, *resource_ids]
    try:
        try:
            total = int(
                db.execute(
                    f"SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ? AND resource_id IN ({placeholders})",
                    args,
                ).fetchone()[0]
            )
            rows = db.execute(
                f"SELECT d.id, d.resource_id, d.package_id, d.kind, d.relative_path, d.metadata, bm25(documents_fts) FROM documents_fts JOIN documents d ON d.id = documents_fts.document_id WHERE documents_fts MATCH ? AND documents_fts.resource_id IN ({placeholders}) ORDER BY bm25(documents_fts), d.resource_id, d.relative_path LIMIT ? OFFSET ?",
                [*args, page_limit, start],
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if _sqlite_busy(exc):
                return _empty_search_result(
                    query,
                    page_limit,
                    start,
                    {**state, "status": "degraded", "error": "search_database_busy"},
                )
            raise LocalSearchError(
                "invalid_query"
                if "syntax" in str(exc).lower()
                else "search_unavailable"
            ) from exc
    finally:
        db.close()
    expected = _snapshot_checksum(snapshot)
    items: list[dict[str, Any]] = []
    for row in rows:
        metadata = json.loads(row[5] or "{}")
        metadata.pop("resource_metadata_hash", None)
        items.append(
            {
                "document_id": row[0],
                "resource_id": row[1],
                "resource_type": row[3],
                "title": row[4],
                "provenance": {
                    "package_id": row[2],
                    "kind": row[3],
                    "snapshot_checksum": expected,
                },
                "canonical_path": row[4],
                "relative_path": row[4],
                "path_ref": f"{row[1]}:{row[4]}",
                "metadata": metadata,
                "match_reason": "content"
                if metadata.get("mode") == "fulltext"
                else "metadata",
                "match": {
                    "fields": ["title", "content"],
                    "rank": row[6],
                    "reason": "FTS5 title/content match",
                },
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
        "page": {
            "limit": page_limit,
            "limitstart": start,
            "offset": start,
            "returned": len(rows),
            "total": total,
            "next_limitstart": start + len(rows) if start + len(rows) < total else None,
        },
    }
