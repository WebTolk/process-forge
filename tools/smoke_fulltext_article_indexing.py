#!/usr/bin/env python3
"""Smoke test for real fulltext indexing of an authorized article fixture."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.local_resource_search import maintenance_tick, search


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-fulltext-article-") as raw:
        project = Path(raw) / "project"
        article_root = project / "knowledge"
        article_root.mkdir(parents=True)
        article = article_root / "garage-stability.md"
        article.write_text(
            "# Garage Stability\n\nUniqueGarageNeedle42 proves article fulltext indexing.\n",
            encoding="utf-8",
        )
        snapshot = {
            "snapshot": {"id": "article-fixture"},
            "local_search_resources": [
                {
                    "id": "fixture.article.resource",
                    "package_id": "fixture.package",
                    "kind": "knowledge",
                    "title": "Fixture Article Resource",
                    "content_roots": [str(article_root)],
                    "indexing": {
                        "mode": "fulltext",
                        "sources": [{"path": ".", "include": ["*.md"], "exclude": []}],
                    },
                }
            ],
        }
        before = search(project, snapshot, query="UniqueGarageNeedle42")
        if before.get("search_status") != "missing":
            raise AssertionError(before)
        tick = maintenance_tick(project, snapshot)
        if tick.get("after", {}).get("status") != "fresh":
            raise AssertionError(tick)
        after = search(project, snapshot, query="UniqueGarageNeedle42")
        results = after.get("results") if isinstance(after.get("results"), list) else []
        if after.get("search_status") != "fresh" or len(results) != 1:
            raise AssertionError(after)
        result = results[0]
        if result.get("resource_id") != "fixture.article.resource" or result.get("canonical_path") != "garage-stability.md":
            raise AssertionError(after)
    print("PASS: fulltext article fixture is indexed and searchable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
