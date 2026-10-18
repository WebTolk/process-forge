#!/usr/bin/env python3
"""Reproduce a full-text source escaping a single-file authorized root."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.local_resource_search import (  # noqa: E402
    IndexSource,
    _iter_source_files,
    build_index,
    search,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-audit-search-") as raw:
        root = Path(raw)
        project = root / "project"
        project.mkdir()
        authorized = project / "allowed.md"
        sibling = project / "secret.txt"
        authorized.write_text("authorized marker", encoding="utf-8")
        sibling.write_text("UNAUTHORIZED sibling marker", encoding="utf-8")
        source = IndexSource(path="../secret.txt", mode="fulltext", include=("**/*",), exclude=(), role="")
        discovered = list(_iter_source_files(authorized, source))
        print("DISCOVERED", [(str(path), relative) for path, relative in discovered])
        snapshot = {
            "snapshot": {"id": "audit"},
            "local_search_resources": [
                {
                    "id": "file-resource",
                    "content_roots": [str(authorized)],
                    "indexing": {
                        "mode": "fulltext",
                        "sources": [{"path": "../secret.txt", "mode": "fulltext", "include": ["**/*"]}],
                    },
                }
            ],
        }
        print("INDEXED", build_index(project, snapshot))
        result = search(project, snapshot, query="UNAUTHORIZED")
        print("SEARCH_TOTAL", result["total"])
        print("RESULT_PATHS", [item["relative_path"] for item in result["results"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
