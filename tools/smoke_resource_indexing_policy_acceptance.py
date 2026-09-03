#!/usr/bin/env python3
"""Acceptance smoke for declarative resource indexing policy."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from processforge_core.local_resource_search import index_path, index_status, maintenance_tick, search


def fulltext_resource(resource_id: str, root: Path, *, title: str = "") -> dict:
    return {
        "id": resource_id,
        "resource_id": resource_id,
        "package_id": "acceptance",
        "kind": "documentation",
        "title": title or resource_id,
        "content_roots": [str(root)],
        "indexing": {
            "enabled": True,
            "mode": "fulltext",
            "fields": ["title", "description", "path"],
            "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}],
        },
    }


def metadata_resource(resource_id: str, root: Path, *, title: str, kind: str = "source_tree", version: str = "") -> dict:
    return {
        "id": resource_id,
        "resource_id": resource_id,
        "package_id": "acceptance",
        "kind": kind,
        "title": title,
        "description": f"{title} navigation root",
        "version": version,
        "content_roots": [str(root)],
        "indexing": {
            "enabled": True,
            "mode": "metadata",
            "fields": ["title", "description", "version", "path"],
            "sources": [{"path": ".", "mode": "metadata", "role": kind}],
        },
    }


def snapshot(snapshot_id: str, resources: list[dict]) -> dict:
    return {"snapshot": {"id": snapshot_id, "checksum": snapshot_id}, "local_search_resources": resources}


def assert_found(project: Path, workplace: Path, snap: dict, query: str, resource_id: str) -> dict:
    payload = search(project, snap, query=query, workplace_root=workplace)
    assert payload["search_status"] == "fresh", payload
    assert payload["results"], query
    assert payload["results"][0]["resource_id"] == resource_id, payload
    return payload["results"][0]


def assert_not_found(project: Path, workplace: Path, snap: dict, query: str) -> None:
    payload = search(project, snap, query=query, workplace_root=workplace)
    assert payload["search_status"] == "fresh", payload
    assert payload["results"] == [], payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-index-policy-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        articles_a = root / "knowledge-a" / "articles"
        source_a_v1 = root / "knowledge-a" / "core" / "6.1.1"
        source_a_v2 = root / "knowledge-a" / "core" / "6.1.2"
        knowledge_b = root / "knowledge-b"
        knowledge_c = root / "knowledge-c"
        template_t = root / "template-t"
        tool_x = root / "tool-x"
        for directory in [workplace, project, articles_a, source_a_v1, source_a_v2, knowledge_b, knowledge_c, template_t / "files", tool_x]:
            directory.mkdir(parents=True)
        (articles_a / "overview.md").write_text("alpha article marker", encoding="utf-8")
        for index in range(20):
            (source_a_v1 / f"legacy-{index}.php").write_text(f"<?php // legacy-source-token-{index}", encoding="utf-8")
            (source_a_v2 / f"current-{index}.php").write_text(f"<?php // current-source-token-{index}", encoding="utf-8")
        (knowledge_b / "guide.md").write_text("bravo fulltext marker", encoding="utf-8")
        (knowledge_c / "secret.md").write_text("charlie hidden marker", encoding="utf-8")
        (template_t / "README.md").write_text("template purpose marker", encoding="utf-8")
        (template_t / "files" / "boilerplate.py").write_text("boilerplate implementation token", encoding="utf-8")
        (tool_x / "tool.yaml").write_text("tool x executes maintenance safely", encoding="utf-8")

        resource_a_article = fulltext_resource("knowledge-a:articles", articles_a, title="Knowledge A Articles")
        resource_a_source_v1 = metadata_resource("knowledge-a:source:6.1.1", source_a_v1, title="Joomla Core 6.1.1", version="6.1.1")
        resource_a_source_v2 = metadata_resource("knowledge-a:source:6.1.2", source_a_v2, title="Joomla Core 6.1.2", version="6.1.2")
        resource_b = fulltext_resource("knowledge-b:docs", knowledge_b, title="Knowledge B")
        resource_c = fulltext_resource("knowledge-c:hidden", knowledge_c, title="Knowledge C Hidden")
        resource_t = {
            "id": "template:t",
            "resource_id": "template:t",
            "package_id": "acceptance",
            "kind": "template",
            "title": "Template T",
            "content_roots": [str(template_t)],
            "indexing": {
                "enabled": True,
                "mode": "metadata",
                "fields": ["title", "description", "path"],
                "sources": [
                    {"path": "README.md", "mode": "fulltext", "include": ["README.md"], "role": "description"},
                    {"path": "files", "mode": "metadata", "role": "template_root"},
                ],
            },
        }
        resource_x = metadata_resource("tool:x", tool_x, title="Tool X Maintenance", kind="tool")

        admin_snapshot = snapshot("admin-all", [resource_a_article, resource_a_source_v1, resource_b, resource_c, resource_t, resource_x])
        assert maintenance_tick(project, admin_snapshot, workplace_root=workplace)["after"]["status"] == "fresh"

        project_snapshot = snapshot("project-v1", [resource_a_article, resource_a_source_v1, resource_b, resource_t, resource_x])
        assert maintenance_tick(project, project_snapshot, workplace_root=workplace)["after"]["status"] == "fresh"

        assert_found(project, workplace, project_snapshot, "alpha article", "knowledge-a:articles")
        assert_found(project, workplace, project_snapshot, "bravo fulltext", "knowledge-b:docs")
        assert_found(project, workplace, project_snapshot, "template purpose", "template:t")
        assert_found(project, workplace, project_snapshot, "Tool X Maintenance", "tool:x")
        source_result = assert_found(project, workplace, project_snapshot, "Joomla Core 6.1.1", "knowledge-a:source:6.1.1")
        assert source_result["metadata"]["mode"] == "metadata"
        assert "source_tree" in source_result["metadata"]["root_ref"] or source_result["resource_type"] == "source_tree"

        assert_not_found(project, workplace, project_snapshot, "charlie hidden")
        assert_not_found(project, workplace, project_snapshot, "legacy-source-token-5")
        assert_not_found(project, workplace, project_snapshot, "boilerplate implementation token")

        db = sqlite3.connect(index_path(project, workplace))
        try:
            php_document_rows = db.execute("SELECT count(*) FROM documents WHERE resource_id='knowledge-a:source:6.1.1'").fetchone()[0]
        finally:
            db.close()
        assert php_document_rows == 1, php_document_rows

        (articles_a / "overview.md").write_text("alpha article marker refreshed-token", encoding="utf-8")
        changed = index_status(project, project_snapshot, workplace_root=workplace, verify_files=True)
        assert changed["status"] == "stale" and changed["error"] == "document_fingerprint_changed", changed
        assert maintenance_tick(project, project_snapshot, workplace_root=workplace)["after"]["status"] == "fresh"
        assert_found(project, workplace, project_snapshot, "refreshed-token", "knowledge-a:articles")

        project_snapshot_v2 = snapshot("project-v2", [resource_a_article, resource_a_source_v2, resource_b, resource_t, resource_x])
        assert maintenance_tick(project, project_snapshot_v2, workplace_root=workplace)["after"]["status"] == "fresh"
        assert_found(project, workplace, project_snapshot_v2, "Joomla Core 6.1.2", "knowledge-a:source:6.1.2")
        assert_not_found(project, workplace, project_snapshot_v2, "current-source-token-5")

    print("PASS: resource indexing policy acceptance smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
