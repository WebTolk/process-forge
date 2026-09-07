#!/usr/bin/env python3
"""Regression smoke for the workplace-wide local resource search index."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import processforge as core
from processforge_core.garage import ResourceResolveService
from processforge_core.local_resource_search import search


def cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "processforge.py"), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def snapshot(resource_id: str, content_root: Path) -> dict:
    return {
        "snapshot": {"id": f"project-{resource_id}", "checksum": f"project-{resource_id}"},
        "local_search_resources": [{"id": resource_id, "content_roots": [str(content_root)]}],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-workplace-search-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        packages = workplace / "packages" / "docs.a"
        project_a = root / "project-a"
        project_b = root / "project-b"
        for path in (packages / "guide", packages / "tree", project_a / ".pf" / "contexts", project_b / ".pf" / "contexts"):
            path.mkdir(parents=True, exist_ok=True)
        (packages / "guide" / "guide.md").write_text("workplace-fulltext-marker", encoding="utf-8")
        (packages / "tree" / "large.txt").write_text("workplace-metadata-marker", encoding="utf-8")
        (packages / "ignored.md").write_text("workplace-forbidden-marker", encoding="utf-8")
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text(yaml.safe_dump({"schema_version": 1, "id": "smoke-workplace"}, sort_keys=False), encoding="utf-8")
        (workplace / "registries" / "package-roots.yaml").write_text(
            yaml.safe_dump({"schema_version": 1, "package_roots": [{"id": "local", "path": "packages", "status": "available"}]}, sort_keys=False),
            encoding="utf-8",
        )
        (packages / "package.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "id": "docs.a",
                    "resources": [
                        {"id": "guide", "kind": "documentation", "path": "guide", "indexing": {"mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]}},
                        {"id": "tree", "kind": "source_tree", "path": "tree", "indexing": {"mode": "metadata"}},
                        {"id": "ignored", "kind": "documentation", "path": "ignored.md", "indexing": {"mode": "none"}},
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        guide_id, tree_id = "docs.a:guide", "docs.a:tree"
        # The maintenance CLI takes only the Workplace: no project, Runtime,
        # Ledger, or session is necessary to create the physical index.
        rebuilt = cli("search-index", "rebuild", "--workplace", str(workplace))
        assert "REBUILT:" in rebuilt and "RESOURCES: 2" in rebuilt, rebuilt
        assert "STATUS: fresh" in cli("search-index", "status", "--workplace", str(workplace))
        assert "PASS: workplace resource catalogue resolved without project context" in cli("search-index", "doctor", "--workplace", str(workplace))
        database = workplace / "runtime" / "search" / "local-resource-search.sqlite"
        assert database.is_file()
        db = sqlite3.connect(database)
        try:
            assert db.execute("SELECT count(*) FROM resources").fetchone()[0] == 2
            assert db.execute("SELECT count(*) FROM resources WHERE resource_id=?", (guide_id,)).fetchone()[0] == 1
        finally:
            db.close()
        # Both projects query the same DB but receive only their snapshot grant.
        result_a = search(project_a, snapshot(guide_id, packages / "guide"), query="workplace-fulltext-marker", workplace_root=workplace)
        result_b = search(project_b, snapshot(tree_id, packages / "tree"), query="workplace-fulltext-marker", workplace_root=workplace)
        assert result_a["results"] and result_a["results"][0]["resource_id"] == guide_id, result_a
        assert result_b["results"] == [], result_b
        metadata = search(project_b, snapshot(tree_id, packages / "tree"), query="tree", workplace_root=workplace)
        assert metadata["results"] and metadata["results"][0]["resource_id"] == tree_id, metadata
        assert search(project_a, snapshot(guide_id, packages / "guide"), query="workplace-forbidden-marker", workplace_root=workplace)["results"] == []
        # pf.resolve receives the canonical package root for an authorized
        # resource and remains a project-snapshot authorization operation.
        project_snapshot = {"local_search_resources": [{"id": guide_id, "package_id": "docs.a", "kind": "documentation", "path_ref": {"registry": "package_roots", "id": "local", "relative_path": "docs.a/guide"}}]}
        (project_a / ".pf" / "contexts" / "project-context.snapshot.yaml").write_text(yaml.safe_dump(project_snapshot, sort_keys=False), encoding="utf-8")
        resolved = ResourceResolveService(project_a, workplace, core).resolve(resource_id=guide_id)
        assert Path(resolved["resource"]["local_root"]) == (packages / "guide").resolve(), resolved
    print("PASS: workplace-wide local resource index smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
