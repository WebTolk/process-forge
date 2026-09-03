#!/usr/bin/env python3
"""Portable smoke test for article fulltext and source-tree navigation."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from processforge_core.local_resource_search import maintenance_tick, search


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-garage-resource-search-") as raw:
        project = Path(raw) / "project"
        project.mkdir()
        article_root = Path(raw) / "knowledge-articles"
        article_root.mkdir()
        (article_root / "resource-navigation.md").write_text(
            "PortableArticleNeedle proves fulltext article navigation.",
            encoding="utf-8",
        )
        source_root = Path(raw) / "source-tree"
        source_root.mkdir()
        (source_root / "README.md").write_text("Fixture Source 1.0", encoding="utf-8")
        snapshot = {
            "snapshot": {"id": "portable-resource-search"},
            "local_search_resources": [
                {
                    "id": "fixture.knowledge:articles",
                    "resource_id": "fixture.knowledge:articles",
                    "package_id": "fixture.knowledge",
                    "kind": "knowledge",
                    "title": "Fixture articles",
                    "content_roots": [str(article_root)],
                    "indexing": {
                        "enabled": True,
                        "mode": "fulltext",
                        "sources": [
                            {"path": ".", "mode": "fulltext", "include": ["**/*.md"], "exclude": []}
                        ],
                    },
                },
                {
                    "id": "fixture.source:v1",
                    "resource_id": "fixture.source:v1",
                    "package_id": "fixture.source",
                    "kind": "source_tree",
                    "title": "Fixture Source 1.0",
                    "content_roots": [str(source_root)],
                    "indexing": {
                        "enabled": True,
                        "mode": "metadata",
                        "sources": [{"path": ".", "mode": "metadata", "role": "source_tree"}],
                    },
                },
            ],
        }
        tick = maintenance_tick(project, snapshot)
        if tick.get("after", {}).get("status") != "fresh":
            raise AssertionError(tick)
        result = search(project, snapshot, query="PortableArticleNeedle")
        if result.get("total", 0) < 1:
            raise AssertionError(result)
        first = result["results"][0]
        if first.get("resource_id") != "fixture.knowledge:articles" or not str(
            first.get("relative_path") or ""
        ).endswith(".md"):
            raise AssertionError(result)
        source_result = search(project, snapshot, query="Fixture Source 1.0")
        source_hits = [
            item
            for item in source_result.get("results", [])
            if item.get("resource_id") == "fixture.source:v1"
        ]
        if not source_hits:
            raise AssertionError(source_result)
        if source_hits[0].get("resource_type") != "source_tree":
            raise AssertionError(source_result)
    print("PASS: article fulltext and source-tree metadata are searchable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
