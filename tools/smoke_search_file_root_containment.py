#!/usr/bin/env python3
"""Smoke search source containment at authorized file and directory roots."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.local_resource_search import build_index, search


def _resource(resource_id: str, root: Path, sources: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": resource_id,
        "package_id": "fixture",
        "kind": "knowledge",
        "content_roots": [str(root)],
        "indexing": {"mode": "fulltext", "sources": sources},
    }


def _assert_total(root: Path, snapshot: dict[str, object], query: str, expected: int) -> None:
    result = search(root, snapshot, query=query)
    if result.get("total") != expected:
        raise AssertionError({"query": query, "expected": expected, "result": result})


def check(root: Path) -> int:
    root = root.resolve()
    directory = root / "authorized-dir"
    directory.mkdir(parents=True, exist_ok=True)
    authorized = directory / "authorized.md"
    authorized.write_text("AuthorizedDirectoryMarker\n", encoding="utf-8")

    outside = root / "sibling"
    outside.mkdir()
    sibling = outside / "secret.md"
    sibling.write_text("SiblingEscapeMarker\n", encoding="utf-8")
    symlink_target = outside / "symlink-target.md"
    symlink_target.write_text("SymlinkEscapeMarker\n", encoding="utf-8")

    authorized_file = root / "authorized-file.md"
    authorized_file.write_text("AuthorizedFileMarker\n", encoding="utf-8")

    symlink_source = directory / "linked-secret.md"
    try:
        symlink_source.symlink_to(symlink_target)
        symlink_supported = True
    except (OSError, NotImplementedError):
        symlink_supported = False

    sources = [
        {"path": ".", "include": ["**/*.md"]},
        {"path": "../sibling/secret.md", "include": ["*.md"]},
        {"path": str(sibling), "include": ["*.md"]},
    ]
    file_sources = [
        {"path": ".", "include": ["*.md"]},
        {"path": "../sibling/secret.md", "include": ["*.md"]},
        {"path": str(sibling), "include": ["*.md"]},
    ]
    snapshot = {
        "snapshot": {"id": "search-file-root-containment"},
        "local_search_resources": [
            _resource("authorized-directory", directory, sources),
            _resource("authorized-file", authorized_file, file_sources),
        ],
    }

    result = build_index(root, snapshot)
    if result.get("indexed") != 2:
        raise AssertionError(result)
    _assert_total(root, snapshot, "AuthorizedDirectoryMarker", 1)
    _assert_total(root, snapshot, "AuthorizedFileMarker", 1)
    _assert_total(root, snapshot, "SiblingEscapeMarker", 0)
    if symlink_supported:
        _assert_total(root, snapshot, "SymlinkEscapeMarker", 0)

    print("PASS: search source containment protects file roots, directory roots, escapes, and symlinks")
    return 0


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-search-containment-") as raw:
        return check(Path(raw))


if __name__ == "__main__":
    raise SystemExit(main())
