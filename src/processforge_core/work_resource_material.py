"""Bounded, provider-neutral material binding for authorized Work resources.

This module does not authorize callers or resolve references. The caller must
pass a root resolved under current authorization and a portable path reference.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .local_resource_search import MAX_FILE_BYTES, POLICY_MODES, TEXT_SUFFIXES, normalize_indexing_policy


PREFIX = "sha256:"
MAX_DESCRIPTOR_BYTES = 65536
MAX_SOURCES = 256
MAX_PATTERN_CHARS = 512
MAX_RELATIVE_CHARS = 1024
RESOURCE_FILES = 256
RESOURCE_BYTES = 8 * 1024 * 1024
DEFAULT_LIMITS = {"resources": 64, "files": 2048, "bytes": 32 * 1024 * 1024,
                  "documents": 2048, "document_bytes": 32 * 1024 * 1024,
                  "visited_entries": 20000, "files_per_resource": RESOURCE_FILES,
                  "bytes_per_resource": RESOURCE_BYTES, "bytes_per_file": MAX_FILE_BYTES}
LEGACY_INDEX_POLICIES = {"none", "never", "disabled", "metadata", "metadata_first", "index_only",
                         "source_tree", "symbols", "fulltext", "full_text", "always_index", "snapshot_authorized"}
LEGACY_POLICY_CANONICAL = {"full_text": "fulltext"}


class MaterialError(Exception):
    """Stable material failure code; messages deliberately contain no paths."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(self.code)


@dataclass
class MaterialBudget:
    """Cumulative fixed ceilings shared across one resource request."""

    resources: int = 0
    files: int = 0
    bytes: int = 0
    visited_entries: int = 0
    documents: int = 0
    document_bytes: int = 0

    max_resources = DEFAULT_LIMITS["resources"]
    max_files = DEFAULT_LIMITS["files"]
    max_bytes = DEFAULT_LIMITS["bytes"]
    max_visited_entries = DEFAULT_LIMITS["visited_entries"]

    @property
    def limits(self) -> dict[str, int]:
        return dict(DEFAULT_LIMITS)

    def add_resource(self) -> None:
        if self.resources + 1 > self.max_resources:
            raise MaterialError("resource_material_budget_exceeded")
        self.resources += 1

    def visit(self, count: int = 1) -> None:
        if count < 0 or self.visited_entries + count > self.max_visited_entries:
            raise MaterialError("resource_material_budget_exceeded")
        self.visited_entries += count

    def add_file(self, size: int) -> None:
        if size < 0 or size > MAX_FILE_BYTES or self.files + 1 > self.max_files or self.bytes + size > self.max_bytes:
            raise MaterialError("resource_material_budget_exceeded")
        self.files += 1
        self.bytes += size

    def add_document(self, content: str) -> None:
        size = len(content.encode("utf-8"))
        if self.documents + 1 > DEFAULT_LIMITS["documents"] or self.document_bytes + size > DEFAULT_LIMITS["document_bytes"]:
            raise MaterialError("resource_material_budget_exceeded")
        self.documents += 1
        self.document_bytes += size


def _canonical(value: Any) -> bytes:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise MaterialError("resource_policy_unverifiable") from exc
    if len(encoded) > MAX_DESCRIPTOR_BYTES:
        raise MaterialError("resource_material_budget_exceeded")
    return encoded


def _sha(value: bytes) -> str:
    return PREFIX + hashlib.sha256(value).hexdigest()


def canonical_fingerprint(value: Any) -> str:
    """Fingerprint canonical JSON using the shared execution-contract format."""
    return _sha(_canonical(value))


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, (str, int, float, bool)):
        text = str(value)
        if len(text) > 8192:
            raise MaterialError("resource_material_budget_exceeded")
        return text
    raise MaterialError("resource_policy_unverifiable")


def _portable_reference(reference: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(reference, dict) or not reference:
        raise MaterialError("resource_policy_unverifiable")
    safe = json.loads(_canonical(reference).decode("utf-8"))
    forbidden = {"path", "local_path", "resolved_path", "content_roots", "root"}

    def check(value: Any, key: str = "") -> Any:
        if key.casefold() in forbidden:
            raise MaterialError("resource_policy_unverifiable")
        if isinstance(value, dict):
            for child_key, child in list(value.items()):
                value[child_key] = check(child, str(child_key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                value[index] = check(child, key)
        elif isinstance(value, str) and key.casefold() not in {"url", "uri"}:
            if key.casefold() == "relative_path":
                return _relative(value, allow_glob=False)
            else:
                win = PureWindowsPath(value)
                posix = PurePosixPath(value)
                if win.drive or win.root or posix.is_absolute():
                    raise MaterialError("resource_policy_unverifiable")
        return value

    check(safe)
    _canonical(safe)
    return safe


def _indexing(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("indexing")
    legacy = str(row.get("index_policy") or "").strip().casefold()
    canonical_legacy = LEGACY_POLICY_CANONICAL.get(legacy, legacy)
    explicit_legacy = legacy in LEGACY_INDEX_POLICIES
    if not isinstance(raw, dict) and not explicit_legacy:
        raise MaterialError("resource_policy_unverifiable")
    if isinstance(raw, dict):
        if "enabled" in raw and type(raw["enabled"]) is not bool:
            raise MaterialError("resource_policy_unverifiable")
        declared_mode = raw.get("mode")
        if declared_mode is not None and str(declared_mode) not in POLICY_MODES:
            raise MaterialError("resource_policy_unverifiable")
        sources = raw.get("sources", [])
        if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
            raise MaterialError("resource_policy_unverifiable")
        for source in sources:
            if not isinstance(source, dict):
                raise MaterialError("resource_policy_unverifiable")
            mode = source.get("mode")
            if mode is not None and str(mode) not in POLICY_MODES:
                raise MaterialError("resource_policy_unverifiable")
            _relative(source.get("path", "."), allow_glob=False)
            for field in ("include", "exclude"):
                patterns = source.get(field, [])
                if not isinstance(patterns, list) or any(not isinstance(item, str) or not item or len(item) > MAX_PATTERN_CHARS for item in patterns):
                    raise MaterialError("resource_policy_unverifiable")
                for pattern in patterns:
                    _relative(pattern, allow_glob=True)
    try:
        policy_row = row if canonical_legacy == legacy else {**row, "index_policy": canonical_legacy}
        policy = normalize_indexing_policy(policy_row)
    except (TypeError, ValueError, AttributeError) as exc:
        raise MaterialError("resource_policy_unverifiable") from exc
    if policy.get("mode") not in POLICY_MODES:
        raise MaterialError("resource_policy_unverifiable")
    for source in policy.get("sources", []):
        if source.get("mode") not in POLICY_MODES:
            raise MaterialError("resource_policy_unverifiable")
        source["path"] = _relative(source.get("path", "."), allow_glob=False)
        for field in ("include", "exclude"):
            source[field] = [_relative(pattern, allow_glob=True) for pattern in source.get(field, [])]
    _canonical(policy)
    return policy


def _relative(value: Any, *, allow_glob: bool) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_RELATIVE_CHARS:
        raise MaterialError("resource_material_path_invalid")
    normalized = value.replace("\\", "/")
    windows, posix = PureWindowsPath(normalized), PurePosixPath(normalized)
    if windows.drive or windows.root or posix.is_absolute() or any(part == ".." for part in posix.parts):
        raise MaterialError("resource_material_path_invalid")
    if not allow_glob and any(char in normalized for char in "*?[]"):
        raise MaterialError("resource_material_path_invalid")
    return "." if normalized in {"", "."} else normalized


def _declared_fingerprint(row: dict[str, Any]) -> dict[str, Any] | str | None:
    raw = row.get("fingerprint")
    if raw is None:
        return None
    if isinstance(raw, str):
        if len(raw) > 1024:
            raise MaterialError("resource_policy_unverifiable")
        return raw
    if isinstance(raw, dict):
        if not raw:
            return None
        value = raw.get("value")
        kind = raw.get("type")
        if value is None or not isinstance(value, (str, int)) or (kind is not None and not isinstance(kind, str)):
            raise MaterialError("resource_policy_unverifiable")
        return {"type": _text(kind, "declared"), "value": _text(value)}
    raise MaterialError("resource_policy_unverifiable")


def metadata_descriptor(row: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Return canonical resource declaration identity, without filesystem IO."""
    if not isinstance(row, dict):
        raise MaterialError("resource_policy_unverifiable")
    resource_id = _text(row.get("id") or row.get("resource_id"))
    if not resource_id:
        raise MaterialError("resource_policy_unverifiable")
    indexing = _indexing(row)
    descriptor = {
        "id": resource_id,
        "package_id": _text(row.get("package_id") or row.get("package")),
        "kind": _text(row.get("kind"), "knowledge"),
        "title": _text(row.get("title"), resource_id),
        "description": _text(row.get("description")),
        "resolved_generation": _text(row.get("resolved_generation")),
        "resolved_version": _text(row.get("resolved_version")),
        "generation": _text(row.get("generation")),
        "version": _text(row.get("version")),
        "fingerprint": _declared_fingerprint(row),
        "reference": _portable_reference(reference),
        "indexing": indexing,
    }
    _canonical(descriptor)
    return descriptor


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    import fnmatch

    normalized = path.lstrip("/")
    for pattern in patterns:
        candidate = pattern.lstrip("/")
        choices = (candidate, candidate[3:]) if candidate.startswith("**/") else (candidate,)
        if any(fnmatch.fnmatch(normalized, item) for item in choices):
            return True
    return False


def _sources(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return list(policy.get("sources") or [])


def _safe_stat(path: Path) -> os.stat_result:
    try:
        if any(part.casefold() == ".pf-egress-private" for part in path.parts):
            raise MaterialError("resource_material_path_invalid")
        if path.is_symlink():
            raise MaterialError("resource_material_path_invalid")
        return path.stat()
    except MaterialError:
        raise
    except OSError as exc:
        raise MaterialError("resource_material_unreadable") from exc


def _revalidate_file(root: Path, path: Path) -> Path:
    """Recheck every component immediately before opening a selected file."""
    try:
        if any(part.casefold() == ".pf-egress-private" for part in path.parts):
            raise MaterialError("resource_material_path_invalid")
        relative = path.relative_to(root)
        if root.is_symlink():
            raise MaterialError("resource_material_path_invalid")
        if not relative.parts:
            canonical_root = root.resolve(strict=True)
            if canonical_root != path or not canonical_root.is_file():
                raise MaterialError("resource_material_changed")
            return canonical_root
        cursor = root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise MaterialError("resource_material_path_invalid")
            resolved = cursor.resolve(strict=True)
            resolved.relative_to(root)
        canonical = cursor.resolve(strict=True)
        if canonical != path or not canonical.is_file():
            raise MaterialError("resource_material_changed")
        return canonical
    except MaterialError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise MaterialError("resource_material_changed") from exc


def _resolve_source(root: Path, source_path: str) -> Path:
    candidate = root if source_path == "." else root / Path(source_path)
    if any(part.casefold() == ".pf-egress-private" for part in candidate.parts):
        raise MaterialError("resource_material_path_invalid")
    try:
        cursor = root
        if source_path != ".":
            for part in PurePosixPath(source_path).parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise MaterialError("resource_material_path_invalid")
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except MaterialError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        if not candidate.exists():
            raise MaterialError("resource_material_missing") from exc
        raise MaterialError("resource_material_path_invalid") from exc
    return resolved


def _iter_files(root: Path, base: Path, source: dict[str, Any], budget: MaterialBudget) -> list[tuple[Path, str]]:
    include = tuple(source.get("include") or ["**/*"])
    exclude = tuple(source.get("exclude") or [])
    found: dict[str, Path] = {}
    if base.is_file():
        budget.visit()
        relative = base.relative_to(root if root.is_dir() else root.parent).as_posix()
        if base.suffix.casefold() in TEXT_SUFFIXES and _matches(base.name, include) and not _matches(relative, exclude):
            try:
                size = base.stat().st_size
            except OSError as exc:
                raise MaterialError("resource_material_unreadable") from exc
            if size > MAX_FILE_BYTES:
                raise MaterialError("resource_material_budget_exceeded")
            found[relative] = base
        return sorted(((path, rel) for rel, path in found.items()), key=lambda item: item[1])
    pending = [base]
    while pending:
        directory = pending.pop()
        try:
            bounded_entries = []
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    budget.visit()
                    bounded_entries.append(entry)
            entries = sorted(bounded_entries, key=lambda entry: entry.name)
        except MaterialError:
            raise
        except OSError as exc:
            raise MaterialError("resource_material_unreadable") from exc
        for entry in entries:
            if entry.name.casefold() == ".pf-egress-private":
                continue
            path = Path(entry.path)
            if entry.is_symlink():
                raise MaterialError("resource_material_path_invalid")
            try:
                canonical = path.resolve(strict=True)
                canonical.relative_to(root)
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except MaterialError:
                raise
            except (OSError, RuntimeError, ValueError) as exc:
                raise MaterialError("resource_material_unreadable") from exc
            if is_dir:
                pending.append(canonical)
                continue
            if not is_file or canonical.suffix.casefold() not in TEXT_SUFFIXES:
                continue
            rel = canonical.relative_to(root).as_posix()
            source_rel = canonical.relative_to(base).as_posix()
            if not _matches(source_rel, include) or _matches(source_rel, exclude) or _matches(rel, exclude):
                continue
            try:
                size = canonical.stat().st_size
            except OSError as exc:
                raise MaterialError("resource_material_unreadable") from exc
            if size > MAX_FILE_BYTES:
                raise MaterialError("resource_material_budget_exceeded")
            found[rel] = canonical
    return [(found[rel], rel) for rel in sorted(found)]


def _content_summary(descriptor: dict[str, Any], source: dict[str, Any] | None = None) -> str:
    reference = json.dumps(descriptor["reference"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    values = [descriptor["title"], descriptor["description"], descriptor["id"], descriptor["package_id"],
              descriptor["kind"], descriptor["resolved_version"] or descriptor["version"], reference]
    if source is not None:
        values.extend((str(source.get("path") or "."), str(source.get("role") or "")))
    return "\n".join(str(value) for value in values if value)


def capture_material(row: dict[str, Any], root: Path, reference: dict[str, Any], *,
                     include_content: bool = False, budget: MaterialBudget | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Capture a bounded binding and optionally its ephemeral searchable docs."""
    if any(part.casefold() == ".pf-egress-private" for part in root.resolve().parts):
        raise MaterialError("resource_material_path_invalid")
    budget = budget if budget is not None else MaterialBudget()
    if not isinstance(budget, MaterialBudget):
        raise MaterialError("resource_material_budget_exceeded")
    budget.add_resource()
    descriptor = metadata_descriptor(row, reference)
    metadata_fingerprint = canonical_fingerprint(descriptor)
    policy = descriptor["indexing"]
    active_sources = [source for source in _sources(policy) if source.get("mode") != "none"]
    if policy["mode"] == "none" or not active_sources:
        material_kind = "none"
    elif any(source.get("mode") == "fulltext" for source in active_sources):
        material_kind = "fulltext"
    else:
        material_kind = "metadata"

    manifest: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    if material_kind != "none":
        try:
            supplied_root = Path(root)
            if supplied_root.is_symlink():
                raise MaterialError("resource_material_path_invalid")
            resolved_root = supplied_root.resolve(strict=True)
            root_stat = _safe_stat(resolved_root)
        except MaterialError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise MaterialError("resource_material_missing") from exc
        if not (resolved_root.is_dir() or resolved_root.is_file()):
            raise MaterialError("resource_material_missing")
        _ = root_stat
        sources = _sources(policy)
        if not sources:
            sources = [{"path": ".", "mode": policy["mode"], "include": ["**/*"], "exclude": []}]
        selected: dict[str, tuple[Path, dict[str, Any]]] = {}
        metadata_sources: list[dict[str, Any]] = []
        for source in sources:
            source_mode = str(source["mode"])
            source_base = _resolve_source(resolved_root, str(source.get("path") or "."))
            _safe_stat(source_base)
            if source_mode == "metadata":
                metadata_sources.append(source)
            elif source_mode == "fulltext":
                for path, relative in _iter_files(resolved_root, source_base, source, budget):
                    selected.setdefault(relative, (path, source))
        if material_kind == "metadata" and not metadata_sources:
            metadata_sources = sources
        for source in metadata_sources:
            summary = _content_summary(descriptor, source)
            budget.add_document(summary)
            if include_content:
                digest = _sha(summary.encode("utf-8"))
                documents.append({"relative_path": str(source.get("path") or "."), "title": descriptor["title"],
                                  "content": summary, "mode": "metadata", "sha256": digest})
        resource_files = 0
        resource_bytes = 0
        for relative, (path, source) in sorted(selected.items()):
            if resource_files + 1 > RESOURCE_FILES:
                raise MaterialError("resource_material_budget_exceeded")
            path = _revalidate_file(resolved_root, path)
            before = _safe_stat(path)
            size = before.st_size
            if size > MAX_FILE_BYTES or resource_bytes + size > RESOURCE_BYTES:
                raise MaterialError("resource_material_budget_exceeded")
            budget.add_file(size)
            try:
                with path.open("rb") as handle:
                    opened = os.fstat(handle.fileno())
                    path = _revalidate_file(resolved_root, path)
                    if (opened.st_size, opened.st_mtime_ns, opened.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
                        raise MaterialError("resource_material_changed")
                    content_bytes = handle.read(MAX_FILE_BYTES + 1)
                    after_open = os.fstat(handle.fileno())
            except OSError as exc:
                raise MaterialError("resource_material_unreadable") from exc
            after = _safe_stat(path)
            if (len(content_bytes) != size or len(content_bytes) > MAX_FILE_BYTES
                    or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino)
                    or (before.st_size, before.st_mtime_ns, before.st_ino) != (after_open.st_size, after_open.st_mtime_ns, after_open.st_ino)):
                raise MaterialError("resource_material_changed")
            digest = _sha(content_bytes)
            manifest.append({"relative_path": relative, "size": size, "sha256": digest})
            resource_files += 1
            resource_bytes += size
            summary = _content_summary(descriptor, source)
            text = content_bytes.decode("utf-8", errors="replace")
            searchable = summary + "\n" + text
            budget.add_document(searchable)
            if include_content:
                documents.append({"relative_path": relative, "title": relative, "content": searchable,
                                  "mode": "fulltext", "sha256": digest})

    manifest.sort(key=lambda item: item["relative_path"])
    material_identity = {"id": descriptor["id"], "kind": material_kind, "metadata_fingerprint": metadata_fingerprint, "manifest": manifest}
    material_fingerprint = _sha(_canonical(material_identity))
    generation = next((descriptor[key] for key in ("resolved_generation", "resolved_version", "generation", "version") if descriptor[key]), material_fingerprint)
    binding = {"id": descriptor["id"], "status": "available", "material_kind": material_kind,
               "generation": generation, "metadata_fingerprint": metadata_fingerprint,
               "material_fingerprint": material_fingerprint, "reference": descriptor["reference"],
               "indexing": descriptor["indexing"], "manifest": manifest}
    deduplicated: dict[str, dict[str, Any]] = {}
    for document in documents:
        previous = deduplicated.get(document["relative_path"])
        if previous is None or (previous["mode"] != "fulltext" and document["mode"] == "fulltext"):
            deduplicated[document["relative_path"]] = document
    documents = sorted(deduplicated.values(), key=lambda item: (item["relative_path"], item["mode"]))
    return binding, documents


__all__ = ["MaterialError", "MaterialBudget", "DEFAULT_LIMITS", "canonical_fingerprint", "metadata_descriptor", "capture_material"]
