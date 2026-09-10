#!/usr/bin/env python3
"""Bounded smoke for overlapping local-search sources and path authorization."""

from __future__ import annotations

import argparse
from contextlib import closing
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.local_resource_search import build_index, index_path, index_status, maintenance_tick, search


def check(root: Path) -> int:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    source_root = root / "source"
    source_root.mkdir(exist_ok=True)
    (source_root / "keep.md").write_text("OverlapNeedle legitimate result\n", encoding="utf-8")
    (source_root / "excluded.md").write_text("ExcludedNeedle must not be indexed\n", encoding="utf-8")
    (source_root / "wrong.txt").write_text("IncludeMismatchNeedle must not be indexed\n", encoding="utf-8")
    file_root = root / "file-root.md"
    file_root.write_text("FileRootNeedle legitimate file-root result\n", encoding="utf-8")
    distinct_root = root / "distinct"
    distinct_root.mkdir(exist_ok=True)
    (distinct_root / "keep.md").write_text("DistinctNeedle separate resource\n", encoding="utf-8")

    snapshot = {
        "snapshot": {"id": "search-source-integrity"},
        "local_search_resources": [
            {
                "id": "resource.overlap",
                "package_id": "fixture",
                "kind": "knowledge",
                "title": "Overlap",
                "content_roots": [str(source_root)],
                "indexing": {"mode": "fulltext", "sources": [
                    {"path": "keep.md", "mode": "metadata"},
                    {"path": ".", "include": ["*.md"], "exclude": ["excluded.md"]},
                    {"path": "keep.md", "include": ["*.md"], "exclude": []},
                    {"path": "wrong.txt", "include": ["*.md"], "exclude": []},
                    {"path": "excluded.md", "include": ["*.md"], "exclude": ["excluded.md"]},
                ]},
            },
            {
                "id": "resource.file-root",
                "package_id": "fixture",
                "kind": "knowledge",
                "title": "File root",
                "content_roots": [str(file_root)],
                "indexing": {"mode": "fulltext", "sources": [
                    {"path": ".", "include": ["*.md"], "exclude": []},
                ]},
            },
            {
                "id": "resource.file-root-excluded",
                "package_id": "fixture",
                "kind": "knowledge",
                "content_roots": [str(file_root)],
                "indexing": {"mode": "fulltext", "sources": [
                    {"path": ".", "include": ["*.md"], "exclude": ["**/*.md"]},
                ]},
            },
            {
                "id": "resource.distinct",
                "package_id": "fixture",
                "kind": "knowledge",
                "title": "Distinct",
                "content_roots": [str(distinct_root)],
                "indexing": {"mode": "fulltext", "sources": [
                    {"path": ".", "include": ["*.md"], "exclude": []},
                ]},
            },
        ],
    }

    result = build_index(root, snapshot)
    if result["indexed"] != 3:
        raise AssertionError(result)
    db_path = index_path(root)
    with closing(sqlite3.connect(db_path)) as db:
        rows = db.execute("SELECT count(*) FROM documents").fetchone()[0]
        fts_rows = db.execute("SELECT count(*) FROM documents_fts").fetchone()[0]
        if rows != 3 or fts_rows != 3:
            raise AssertionError({"documents": rows, "fts": fts_rows})
        # Simulate an old inconsistent FTS state.  Refresh must reconcile it.
        db.execute(
            "INSERT INTO documents_fts (title, content, document_id, resource_id) "
            "SELECT title, 'legacy duplicate', id+1000, resource_id FROM documents WHERE resource_id=?",
            ("resource.overlap",),
        )
        db.commit()
        db.execute("UPDATE meta SET value='3' WHERE key='schema_version'")
        db.commit()
    assert index_status(root, snapshot)["status"] == "degraded"
    assert not search(root, snapshot, query="OverlapNeedle")["results"], "old derived rows must not be served"
    refreshed = maintenance_tick(root, snapshot)
    assert refreshed["action"] == "rebuild" and refreshed["after"]["status"] == "fresh", refreshed
    assert maintenance_tick(root, snapshot)["action"] == "none"
    with closing(sqlite3.connect(db_path)) as db:
        if db.execute("SELECT count(*) FROM documents").fetchone()[0] != 3:
            raise AssertionError("document count changed during refresh")
        if db.execute("SELECT count(*) FROM documents_fts").fetchone()[0] != 3:
            raise AssertionError("legacy FTS duplicate was not repaired")

    def one(query: str) -> dict:
        return search(root, snapshot, query=query, limit=1)

    overlap = one("OverlapNeedle")
    if overlap.get("total") != 1 or len(overlap.get("results", [])) != 1:
        raise AssertionError(overlap)
    if one("ExcludedNeedle").get("total") != 0:
        raise AssertionError("excluded explicit content is searchable")
    if one("IncludeMismatchNeedle").get("total") != 0:
        raise AssertionError("include-mismatched explicit content is searchable")
    if one("FileRootNeedle").get("total") != 1:
        raise AssertionError("file-root source was not indexed")
    if one("DistinctNeedle").get("total") != 1:
        raise AssertionError("distinct resource was lost")
    page = search(root, snapshot, query="fixture", limit=1, offset=1)
    if page.get("total") != 3 or len(page.get("results", [])) != 1:
        raise AssertionError(page)
    print("PASS: local-search source overlap, filtering, refresh repair, and pagination")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, help="Optional isolated fixture root; defaults to a system temporary directory.")
    args = parser.parse_args()
    if args.root:
        return check(args.root)
    with tempfile.TemporaryDirectory(prefix="pf-search-integrity-") as raw:
        return check(Path(raw))


if __name__ == "__main__":
    raise SystemExit(main())
