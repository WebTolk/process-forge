#!/usr/bin/env python3
"""Operational hardening smoke for search-index maintenance and dirty recovery."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
for path in (SRC, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import processforge
from processforge_core.local_resource_search import index_path, index_status, maintenance_tick, search


def snapshot(knowledge: Path, template: Path) -> dict:
    return {
        "snapshot": {"id": "operational-smoke", "checksum": "operational-smoke-v1"},
        "local_search_resources": [
            {"id": "knowledge-a", "package_id": "pkg.a", "kind": "knowledge", "content_roots": [str(knowledge)]},
            {"id": "template-a", "package_id": "tpl.a", "kind": "template", "content_roots": [str(template)]},
        ],
    }


def assert_found(project: Path, workplace: Path, snap: dict, marker: str) -> None:
    payload = search(project, snap, query=marker, workplace_root=workplace)
    assert payload["results"], marker
    assert payload["search_status"] in {"fresh", "missing", "stale"}


def assert_not_found(project: Path, workplace: Path, snap: dict, marker: str) -> None:
    payload = search(project, snap, query=marker, workplace_root=workplace)
    assert payload["results"] == [], marker


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-search-operational-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        knowledge = root / "knowledge"
        template = root / "template"
        for directory in (workplace, project, knowledge, template):
            directory.mkdir(parents=True)
        (knowledge / "guide.md").write_text("markerone", encoding="utf-8")
        (template / "template.md").write_text("templatemarker", encoding="utf-8")
        snap = snapshot(knowledge, template)

        first_tick = maintenance_tick(project, snap, workplace_root=workplace)
        assert first_tick["action"] == "refresh"
        assert first_tick["after"]["status"] == "fresh"
        assert_found(project, workplace, snap, "markerone")
        assert_found(project, workplace, snap, "templatemarker")

        (knowledge / "guide.md").write_text("markertwo", encoding="utf-8")
        changed = index_status(project, snap, workplace_root=workplace, verify_files=True)
        assert changed["status"] == "stale" and changed["error"] == "document_fingerprint_changed"
        changed_tick = maintenance_tick(project, snap, workplace_root=workplace)
        assert changed_tick["action"] == "refresh"
        assert_found(project, workplace, snap, "markertwo")
        assert_not_found(project, workplace, snap, "markerone")

        (knowledge / "added.md").write_text("markeradded", encoding="utf-8")
        added_tick = maintenance_tick(project, snap, workplace_root=workplace)
        assert added_tick["action"] == "refresh"
        assert_found(project, workplace, snap, "markeradded")

        (knowledge / "guide.md").unlink()
        deleted_tick = maintenance_tick(project, snap, workplace_root=workplace)
        assert deleted_tick["action"] == "refresh"
        assert_not_found(project, workplace, snap, "markertwo")

        processforge.append_workplace_resource_event(
            workplace,
            processforge.resource_management_event(
                scope="workplace",
                command="smoke",
                event_type="resource.updated",
                target={"resource_id": "knowledge-a"},
                status="updated",
                message="dirty marker smoke",
            ),
        )
        dirty = index_status(project, snap, workplace_root=workplace)
        assert dirty["status"] == "stale" and dirty["error"] == "resource.updated"
        dirty_tick = maintenance_tick(project, snap, workplace_root=workplace)
        assert dirty_tick["action"] == "refresh" and dirty_tick["after"]["status"] == "fresh"

        db_path = index_path(project, workplace)
        db = sqlite3.connect(db_path)
        try:
            db.execute("UPDATE meta SET value='999' WHERE key='schema_version'")
            db.commit()
        finally:
            db.close()
        degraded = index_status(project, snap, workplace_root=workplace)
        assert degraded["status"] == "degraded" and degraded["error"] == "index_schema_mismatch"
        recovered = maintenance_tick(project, snap, workplace_root=workplace)
        assert recovered["action"] == "rebuild" and recovered["after"]["status"] == "fresh"

        errors: list[BaseException] = []

        def reader() -> None:
            try:
                for _ in range(20):
                    search(project, snap, query="markeradded", workplace_root=workplace)
            except BaseException as exc:  # pragma: no cover - surfaced below.
                errors.append(exc)

        thread = threading.Thread(target=reader)
        thread.start()
        (knowledge / "added.md").write_text("markeradded markerconcurrency", encoding="utf-8")
        maintenance_tick(project, snap, workplace_root=workplace)
        thread.join()
        assert not errors, errors
        assert_found(project, workplace, snap, "markerconcurrency")

    print("PASS: search/update operational hardening smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
