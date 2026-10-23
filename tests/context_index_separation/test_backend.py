"""Exercise the real backend seam and retained snapshot isolation."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from processforge_core.resources.index_backend import ResourceIndexBackend
from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)
from processforge_core.resources.local_search import (
    LocalSearchError,
    ResourceSearchIndex,
)


def _snapshot(identity: str, root: Path) -> dict[str, Any]:
    return {
        "snapshot": {"id": identity, "checksum": identity},
        "local_search_resources": [{"id": identity, "content_roots": [str(root)]}],
    }


class BackendTests(unittest.TestCase):
    """Verify default SQLite composition and an actual replacement backend."""

    def setUp(self) -> None:
        base = Path(os.environ.get("PF_MAINTENANCE_TEST_TMP", tempfile.gettempdir()))
        self.root = base / f"backend-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(self._cleanup, base)
        self.workplace = self.root / "workplace"
        self.source_a = self.root / "source-a"
        self.source_b = self.root / "source-b"
        self.source_a.mkdir()
        self.source_b.mkdir()
        (self.source_a / "guide.md").write_text("uniquealpha", encoding="utf-8")
        (self.source_b / "guide.md").write_text("uniquebeta", encoding="utf-8")

    def _cleanup(self, base: Path) -> None:
        if self.root.resolve().parent != base.resolve():
            raise AssertionError("fixture escaped its temporary base")
        shutil.rmtree(self.root)

    def test_default_backend_preserves_project_snapshot_isolation(self) -> None:
        snapshot_a = _snapshot("docs.a:root", self.source_a)
        snapshot_b = _snapshot("docs.b:root", self.source_b)
        service = WorkplaceIndexMaintenanceService(self.workplace)
        with patch(
            "processforge_core.resources.index_maintenance."
            "WorkplaceSearchCatalogReader",
            side_effect=AssertionError("project indexing loaded workplace catalogue"),
        ):
            result = service.run_scoped(self.root, snapshot_a, operation="refresh")
            self.assertEqual(result["resources"], 1)
            backend_a: ResourceIndexBackend = ResourceSearchIndex(
                self.root, snapshot_a, self.workplace
            )
            self.assertEqual(backend_a.maintenance_tick()["action"], "none")
            service.run_scoped(self.root, snapshot_b, operation="refresh")
        query = ResourceSearchIndex(self.root, snapshot_a, self.workplace)
        self.assertTrue(query.search(query="uniquealpha")["results"])
        self.assertEqual(query.search(query="uniquebeta")["results"], [])
        database = self.workplace / "runtime/search/local-resource-search.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            resources = connection.execute(
                "SELECT resource_id FROM resources ORDER BY resource_id"
            ).fetchall()
        self.assertEqual(resources, [("docs.a:root",), ("docs.b:root",)])

    def test_rebuild_keeps_released_engine_semantics_and_scope(self) -> None:
        snapshot_a = _snapshot("docs.a:root", self.source_a)
        snapshot_b = _snapshot("docs.b:root", self.source_b)
        service = WorkplaceIndexMaintenanceService(self.workplace)
        service.run_scoped(self.root, snapshot_b, operation="refresh")
        result = service.run_scoped(self.root, snapshot_a, operation="rebuild")
        self.assertEqual(result["resources"], 1)
        database = self.workplace / "runtime/search/local-resource-search.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            resources = connection.execute(
                "SELECT resource_id FROM resources"
            ).fetchall()
        self.assertEqual(resources, [("docs.a:root",)])

    def test_replacement_backend_receives_only_supplied_snapshot(self) -> None:
        calls: list[Any] = []
        result = {"after": {"status": "fresh"}, "action": "none"}

        class Backend:
            def mark_dirty(self, *, reason: str = "dirty") -> dict[str, Any]:
                calls.append(("dirty", reason))
                return {"status": "stale"}

            def refresh(self) -> dict[str, Any]:
                raise AssertionError("wrong operation")

            def rebuild(self) -> dict[str, Any]:
                raise AssertionError("wrong operation")

            def maintenance_tick(self, *, verify_files: bool = True) -> dict[str, Any]:
                calls.append(verify_files)
                return result

        def factory(
            project: Path, snapshot: dict[str, Any], workplace: Path
        ) -> ResourceIndexBackend:
            calls.append((project, snapshot, workplace))
            return Backend()

        snapshot = _snapshot("docs.a:root", self.source_a)
        service = WorkplaceIndexMaintenanceService(
            self.workplace, backend_factory=factory
        )
        actual = service.run_scoped(
            self.root, snapshot, operation="tick", verify_files=False
        )
        self.assertIs(actual, result)
        self.assertEqual(calls, [(self.root, snapshot, self.workplace), False])
        self.assertFalse(
            (self.workplace / "runtime/search/local-resource-search.sqlite").exists()
        )
        calls.clear()
        service.mark_dirty(reason="resource.changed")
        self.assertEqual(
            calls,
            [
                (self.workplace, {"search_index_scope": "workplace"}, self.workplace),
                ("dirty", "resource.changed"),
            ],
        )
        calls.clear()
        actual = service.run_scoped(
            self.root, snapshot, operation="tick", verify_files=False
        )
        self.assertIs(actual, result)
        self.assertEqual(
            calls,
            [
                (self.root, snapshot, self.workplace),
                ("dirty", "pending-invalidation"),
                False,
            ],
        )
        self.assertFalse(
            (self.workplace / "runtime/search/local-resource-search.sqlite").exists()
        )

    def test_project_cannot_submit_workplace_scope(self) -> None:
        service = WorkplaceIndexMaintenanceService(self.workplace)
        with self.assertRaises(LocalSearchError) as raised:
            service.run_scoped(
                self.root, {"search_index_scope": "workplace"}, operation="refresh"
            )
        self.assertEqual(raised.exception.code, "project_snapshot_required")
        self.assertFalse(self.workplace.exists())
