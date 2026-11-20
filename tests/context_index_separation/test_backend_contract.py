"""Check SQLite query errors, writer recovery and concurrent observation."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any
from unittest.mock import patch

from processforge_core.resources.access import ResourceSearchService
from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader
from processforge_core.resources.index_backend import ResourceIndexBackend
from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)
from processforge_core.resources.index_observation import (
    IndexObservationService,
    maintenance_state_path,
)
from processforge_core.resources.index_schedule import IndexMaintenanceJob
from processforge_core.resources.local_search import (
    LocalSearchError,
    ResourceSearchIndex,
    index_path,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_ROOT = (
    Path(os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir())
    / "context-index-backend-contract"
)


class _Reads:
    """Supply explicit current project selection without creating a PF Work."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self.snapshot = snapshot

    def read_snapshot(self, snapshots: Any) -> dict[str, Any]:
        return copy.deepcopy(self.snapshot)

    def context_checker(self) -> Any:
        return lambda *_args, **_kwargs: {"status": "fresh"}

    def search_roots_resolver(self) -> Any:
        return lambda snapshot: snapshot


class BackendContractTests(unittest.TestCase):
    """Exercise real source documents, SQL failures and process-owned locks."""

    def setUp(self) -> None:
        """Create only explicitly owned documents and derived fixture state."""
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = SCRATCH_ROOT / ("contract-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self._cleanup)
        self.workplace = self.root / "workplace"
        resources = []
        for name, mode in (("a", "fulltext"), ("b", "fulltext"), ("meta", "metadata")):
            directory = self.root / name
            directory.mkdir()
            (directory / "guide.md").write_text(
                "sharedneedle " + name + "privatebody", encoding="utf-8"
            )
            resources.append(
                {
                    "id": "fixture:" + name,
                    "title": "NavigationGuide" if name == "meta" else name,
                    "content_roots": [str(directory)],
                    "indexing": {"mode": mode},
                }
            )
        self.snapshot: dict[str, Any] = {
            "snapshot": {"id": "fixture", "checksum": "fixture"},
            "local_search_resources": resources,
        }
        self.catalogue = {**self.snapshot, "search_index_scope": "workplace"}
        self.service = WorkplaceIndexMaintenanceService(self.workplace)
        self.observer = IndexObservationService(self.workplace)
        self.catalogue_patch = patch.object(
            WorkplaceSearchCatalogReader,
            "runtime_snapshot",
            return_value=self.catalogue,
        )
        self.catalogue_patch.start()
        self.addCleanup(self.catalogue_patch.stop)

    def _cleanup(self) -> None:
        """Check the exact fixture boundary before recursively removing it."""
        target = self.root.resolve()
        if target.parent != SCRATCH_ROOT.resolve():
            raise AssertionError("Fixture cleanup escaped owned scratch")
        shutil.rmtree(target)

    def _build(self) -> None:
        self.assertEqual(self.service.run()["results"][0]["status"], "ok")

    def _query(
        self, resources: list[dict[str, Any]] | None = None
    ) -> ResourceSearchIndex:
        snapshot = (
            self.snapshot
            if resources is None
            else {**self.snapshot, "local_search_resources": resources}
        )
        return ResourceSearchIndex(self.root, snapshot, self.workplace)

    def test_sqlite_filters_totals_pagination_and_metadata_bodies(self) -> None:
        """Apply authorization before counts and return metadata without body text."""
        backend: ResourceIndexBackend = self._query()
        result = self.service.run_scoped(self.root, self.snapshot, operation="refresh")
        self.assertEqual(result["resources"], 3)
        self.assertEqual(backend.maintenance_tick()["action"], "none")
        selected = self.snapshot["local_search_resources"][:1]
        query = self._query(selected)
        result = query.search(query="sharedneedle", limit=1)
        self.assertEqual((result["total"], len(result["results"])), (1, 1))
        self.assertEqual(result["results"][0]["resource_id"], "fixture:a")
        self.assertIsNone(result["page"]["next_limitstart"])
        self.assertEqual(query.search(query="bprivatebody")["total"], 0)
        metadata = self._query(self.snapshot["local_search_resources"][2:])
        self.assertEqual(metadata.search(query="metaprivatebody")["results"], [])
        result = metadata.search(query="NavigationGuide")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["match_reason"], "metadata")
        self.assertNotIn("metaprivatebody", json.dumps(result))
        self.assertEqual(self._query([]).search(query="sharedneedle")["total"], 0)

    def test_query_errors_for_fresh_missing_and_stale_index(self) -> None:
        """Do not turn malformed requests into successful unavailable searches."""
        for status in ("missing", "fresh", "stale"):
            with self.subTest(status=status):
                if status == "fresh":
                    self._build()
                elif status == "stale":
                    self._query().mark_dirty(reason="fixture-change")
                for arguments, expected in (
                    ({"query": None}, "invalid_query"),
                    ({"query": 5}, "invalid_query"),
                    ({"query": " "}, "invalid_query"),
                    (
                        {"query": "needle", "limitstart": 1, "offset": 2},
                        "ambiguous_offset",
                    ),
                ):
                    with (
                        self.subTest(arguments=arguments),
                        self.assertRaises(LocalSearchError) as caught,
                    ):
                        self._query().search(**arguments)
                    self.assertEqual(caught.exception.code, expected)

    def test_corrupt_result_metadata_preserves_the_existing_error(self) -> None:
        """Never silently drop corrupt metadata and claim a successful query."""
        self._build()
        database = index_path(self.root, self.workplace)
        with closing(sqlite3.connect(database)) as writer:
            writer.execute(
                "UPDATE documents SET metadata='{' WHERE resource_id='fixture:a'"
            )
            writer.commit()
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        with self.assertRaises(json.JSONDecodeError):
            self._query(self.snapshot["local_search_resources"][:1]).search(
                query="aprivatebody"
            )
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)

    def test_corrupt_scope_metadata_is_degraded_instead_of_fresh(self) -> None:
        """Keep persisted state errors visible through read-only observation."""
        self._build()
        database = index_path(self.root, self.workplace)
        with closing(sqlite3.connect(database)) as writer:
            writer.execute("UPDATE index_state SET allowed_resource_ids='{' ")
            writer.commit()
        status = self.observer.observe()
        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["error"], "index_unreadable")

    def test_running_writer_refuses_second_writer_and_readers_do_not_wait(self) -> None:
        """Observe a real active canonical writer without entering its backend."""
        self._build()
        entered, release = threading.Event(), threading.Event()
        outcomes: list[dict[str, Any]] = []
        original = ResourceSearchIndex.maintenance_tick

        def blocked(
            index: ResourceSearchIndex, *, verify_files: bool = True
        ) -> dict[str, Any]:
            entered.set()
            if not release.wait(10):
                raise AssertionError("Fixture writer was not released")
            return original(index, verify_files=verify_files)

        reads = _Reads(
            {
                **self.snapshot,
                "local_search_resources": self.snapshot["local_search_resources"][:1],
            }
        )
        search = ResourceSearchService(self.root, self.workplace, reads)
        database = index_path(self.root, self.workplace)
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        with patch.object(ResourceSearchIndex, "maintenance_tick", blocked):
            writer = threading.Thread(
                target=lambda: outcomes.append(self.service.run())
            )
            writer.start()
            try:
                self.assertTrue(
                    entered.wait(5), "Canonical writer did not reach barrier"
                )
                started = time.monotonic()
                observed = self.observer.observe()
                result = search.search(query="sharedneedle")
                busy = IndexMaintenanceJob(self.workplace).execute()
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertEqual(observed["status"], "building")
                self.assertEqual(result["search_status"], "building")
                self.assertEqual(result["results"], [])
                self.assertEqual(busy["results"][0]["error"], "search_maintenance_busy")
                self.assertEqual(
                    hashlib.sha256(database.read_bytes()).hexdigest(), before
                )
                self.assertEqual(
                    json.loads(maintenance_state_path(self.workplace).read_text())[
                        "status"
                    ],
                    "running",
                )
            finally:
                release.set()
                writer.join(10)
            self.assertFalse(writer.is_alive())
        self.assertEqual(outcomes[0]["results"][0]["status"], "ok")
        self.assertEqual(search.search(query="sharedneedle")["total"], 1)

    def test_database_writer_lock_is_a_bounded_read_refusal(self) -> None:
        """Exercise the service's real SQLite read path under exclusive contention."""
        self._build()
        database = index_path(self.root, self.workplace)
        with closing(sqlite3.connect(database)) as writer:
            writer.execute("BEGIN EXCLUSIVE")
            try:
                started = time.monotonic()
                result = ResourceSearchService(
                    self.root, self.workplace, _Reads(self.snapshot)
                ).search(query="sharedneedle")
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertNotEqual(result["search_status"], "fresh")
                self.assertEqual(result["results"], [])
            finally:
                writer.rollback()

    def test_crashed_process_releases_lock_and_explicit_cold_job_recovers(self) -> None:
        """Recover an actual abrupt writer exit without deleting running history."""
        self._build()
        fixture = self.root / "input.json"
        fixture.write_text(json.dumps(self.snapshot), encoding="utf-8")
        script = self.root / "crash.py"
        script.write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "from processforge_core.resources.index_maintenance import (\n"
            "    WorkplaceIndexMaintenanceService,\n"
            ")\n"
            "class CrashBackend:\n"
            "    def maintenance_tick(self, *, verify_files=True):\n"
            "        os._exit(23)\n"
            "root = Path(sys.argv[1])\n"
            "snapshot = json.loads((root / 'input.json').read_text())\n"
            "WorkplaceIndexMaintenanceService(\n"
            "    root / 'workplace',\n"
            "    backend_factory=lambda *args: CrashBackend(),\n"
            ").run_scoped(root, snapshot, operation='tick')\n",
            encoding="utf-8",
        )
        child = subprocess.run(
            [sys.executable, "-B", str(script), str(self.root)],
            cwd=self.root,
            env={
                **os.environ,
                "PYTHONPATH": str(PROJECT_ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(child.returncode, 23)
        interrupted = json.loads(maintenance_state_path(self.workplace).read_text())
        self.assertEqual(interrupted["status"], "running")
        self.assertEqual(self.observer.observe()["status"], "building")
        history = maintenance_state_path(self.workplace).parent / "maintenance-history"
        receipt = history / (interrupted["attempt_id"] + "-running.json")
        previous_bytes = receipt.read_bytes()
        recovered = IndexMaintenanceJob(self.workplace).execute()
        self.assertEqual(recovered["results"][0]["status"], "ok")
        current = json.loads(maintenance_state_path(self.workplace).read_text())
        self.assertEqual(current["status"], "complete")
        self.assertEqual(current["previous_status"], "running")
        self.assertEqual(current["reason"], "scheduler")
        self.assertNotEqual(current["attempt_id"], interrupted["attempt_id"])
        self.assertEqual(receipt.read_bytes(), previous_bytes)
        self.assertEqual(self.observer.observe()["status"], "fresh")


if __name__ == "__main__":
    unittest.main()
