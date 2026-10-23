"""Stdlib fixture checks for read-only index observation and project filtering.

Run directly with Python or collect with pytest. All generated data stays under
the observation contribution's scratch. Nonempty catalogue records are injected
at the catalogue boundary, so these checks require no third-party YAML parser.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sqlite3
import sys
import time
import unittest
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from processforge_core.resources import local_search  # noqa: E402
from processforge_core.resources.access import ResourceSearchService  # noqa: E402
from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader  # noqa: E402
from processforge_core.resources.index_observation import (  # noqa: E402
    IndexObservationService,
    maintenance_state_path,
)
from processforge_core.resources.local_search import (  # noqa: E402
    LocalSearchError,
    ResourceSearchIndex,
    index_path,
)

SCRATCH_ROOT = Path(
    os.environ.get(
        "PF_OBSERVATION_TEST_TMP",
        str(PROJECT_ROOT / ".pf" / "tmp" / "context-index-alpha4-observation-20261023"),
    )
)


class _Reads:
    """Expose current snapshots and record guard ordering without a CLI host."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self.snapshot = snapshot
        self.status = "fresh"
        self.events: list[str] = []

    def read_snapshot(self, snapshots: Any) -> dict[str, Any]:
        self.events.append("snapshot")
        return copy.deepcopy(self.snapshot)

    def context_checker(self) -> Any:
        def check(project_root: Path, *, explicit_workplace: str) -> dict[str, Any]:
            self.events.append("check")
            return {"status": self.status}

        return check

    def search_roots_resolver(self) -> Any:
        def resolve(snapshot: dict[str, Any]) -> dict[str, Any]:
            self.events.append("resolve")
            return snapshot

        return resolve


class _ObservationCase(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = SCRATCH_ROOT / f"observation-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(self.clean_fixture)
        self.distribution = self.root / "distribution"
        self.distribution.mkdir()
        self.corpus = self.root / "corpus"
        resources = []
        for name, mode in (("a", "fulltext"), ("b", "fulltext"), ("meta", "metadata")):
            root = self.corpus / name
            root.mkdir(parents=True)
            (root / "guide.md").write_text(
                f"needle {name}body secretbody", encoding="utf-8"
            )
            resources.append(
                {
                    "id": f"fixture.docs:{name}",
                    "package_id": "fixture.docs",
                    "kind": "documentation",
                    "title": name,
                    "index_policy": mode,
                    "content_roots": [str(root)],
                }
            )
        self.snapshot: dict[str, Any] = {
            "search_index_scope": "workplace",
            "snapshot": {"id": "fixture-catalogue", "checksum": "sha256:fixture-one"},
            "local_search_resources": resources,
        }
        self.observer = IndexObservationService(
            self.root, distribution_root=self.distribution
        )

    def clean_fixture(self) -> None:
        """Remove only this fixture after checking its resolved containment."""
        target = self.root.resolve()
        scratch = SCRATCH_ROOT.resolve()
        if target == scratch or not target.is_relative_to(scratch):
            raise AssertionError("Fixture cleanup escaped owned scratch")
        shutil.rmtree(target)

    def build_fixture(self) -> None:
        """Build only this explicitly owned synthetic corpus before observation."""
        ResourceSearchIndex(self.root, self.snapshot, self.root).refresh()

    def durable(self, status: str, **fields: Any) -> None:
        path = maintenance_state_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"status": status, **fields}), encoding="utf-8")

    def observe(self) -> dict[str, Any]:
        with mock.patch.object(
            WorkplaceSearchCatalogReader, "runtime_snapshot", return_value=self.snapshot
        ):
            return self.observer.observe()

    def tree_state(self) -> dict[str, Any]:
        return {
            path.relative_to(self.root).as_posix(): (
                path.stat().st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
            for path in self.root.rglob("*")
        }

    @contextmanager
    def read_only_operation(self) -> Any:
        """Refuse corpus reads/enumeration, maintenance and explicit waiting."""
        real_open = Path.open

        def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
            if path.is_relative_to(self.corpus):
                raise AssertionError("Observation read document content")
            return real_open(path, *args, **kwargs)

        with ExitStack() as stack:
            for name in (
                "build_index",
                "rebuild_index",
                "maintenance_tick",
                "mark_index_dirty",
                "_documents",
                "_iter_source_files",
                "_document_fingerprint_map",
            ):
                stack.enter_context(
                    mock.patch.object(
                        local_search,
                        name,
                        side_effect=AssertionError(f"Forbidden {name}"),
                    )
                )
            stack.enter_context(mock.patch.object(Path, "open", new=guarded_open))
            stack.enter_context(
                mock.patch("time.sleep", side_effect=AssertionError("Explicit wait"))
            )
            yield


class IndexObservationTests(_ObservationCase):
    def test_construction_and_state_path_are_cold(self) -> None:
        before = self.tree_state()
        with mock.patch.object(Path, "open", side_effect=AssertionError("I/O")):
            with mock.patch.object(Path, "stat", side_effect=AssertionError("I/O")):
                service = IndexObservationService(self.root)
                path = maintenance_state_path(service.workplace_root)
        self.assertEqual(
            path.relative_to(self.root).as_posix(),
            "runtime/search/maintenance-state.json",
        )
        self.assertEqual(self.tree_state(), before)

    def test_default_empty_catalogue_is_read_only_without_yaml_or_host(self) -> None:
        before = self.tree_state()
        with self.read_only_operation():
            first = self.observer.observe()
            second = self.observer.observe()
        self.assertEqual(first["status"], "missing")
        self.assertEqual(first, second)
        self.assertNotIn("path", first)
        self.assertEqual(self.tree_state(), before)
        self.assertNotIn("tools.processforge", sys.modules)

    def test_missing_index_repeated_observation_creates_nothing(self) -> None:
        before = self.tree_state()
        with self.read_only_operation():
            self.assertEqual(self.observe()["status"], "missing")
            self.assertEqual(self.observe()["status"], "missing")
        self.assertEqual(self.tree_state(), before)

    def test_fresh_status_uses_metadata_without_reading_documents_or_writing(
        self,
    ) -> None:
        self.build_fixture()
        before = self.tree_state()
        flags: list[bool] = []
        real_status = ResourceSearchIndex.status

        def observe(
            index: ResourceSearchIndex, *, verify_files: bool = False
        ) -> dict[str, Any]:
            flags.append(verify_files)
            return real_status(index, verify_files=verify_files)

        with self.read_only_operation():
            with mock.patch.object(ResourceSearchIndex, "status", new=observe):
                result = self.observe()
        self.assertEqual(flags, [False])
        self.assertEqual(result["status"], "fresh")
        self.assertGreater(result["document_count"], 0)
        self.assertEqual(self.tree_state(), before)

    def test_live_catalogue_change_is_stale_without_rebuilding(self) -> None:
        self.build_fixture()
        self.snapshot["snapshot"]["checksum"] = "sha256:fixture-two"
        before = self.tree_state()
        with self.read_only_operation():
            result = self.observe()
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["error"], "snapshot_checksum_changed")
        self.assertEqual(self.tree_state(), before)

    def test_unreadable_index_exception_is_safe_and_never_requests_repair(self) -> None:
        self.build_fixture()
        before = self.tree_state()
        with self.read_only_operation():
            with mock.patch.object(
                ResourceSearchIndex,
                "status",
                side_effect=OSError("private-secret-location"),
            ):
                result = self.observe()
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["error"], "index_unreadable")
        self.assertNotIn("private-secret", json.dumps(result))
        self.assertEqual(self.tree_state(), before)

    def test_content_changes_are_left_for_explicit_fingerprint_verification(
        self,
    ) -> None:
        self.build_fixture()
        (self.corpus / "a" / "guide.md").write_text("updated content", encoding="utf-8")
        with self.read_only_operation():
            self.assertEqual(self.observe()["status"], "fresh")

    def test_running_and_failed_records_prevent_index_reads_and_false_ready(
        self,
    ) -> None:
        for state, status in (("running", "building"), ("failed", "degraded")):
            with self.subTest(state=state):
                self.durable(
                    state, error="private/fixture/document", started_at="2000-01-01"
                )
                before = self.tree_state()
                with mock.patch.object(
                    WorkplaceSearchCatalogReader,
                    "runtime_snapshot",
                    side_effect=AssertionError("Catalogue read"),
                ):
                    with mock.patch.object(
                        ResourceSearchIndex,
                        "status",
                        side_effect=AssertionError("Index read"),
                    ):
                        result = self.observer.observe()
                self.assertEqual(result["status"], status)
                self.assertEqual(result["maintenance"]["status"], state)
                self.assertEqual(result["error"], f"search_maintenance_{state}")
                self.assertNotIn("private/fixture", json.dumps(result))
                self.assertEqual(self.tree_state(), before)

    def test_invalid_durable_records_are_safe_and_incomplete(self) -> None:
        path = maintenance_state_path(self.root)
        path.parent.mkdir(parents=True)
        for raw in (b"{bad", b"[]", b'{"status":"unknown"}', b'{"status":{}}', b"\xff"):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.read_only_operation():
                    result = self.observe()
                self.assertEqual(result["status"], "degraded")
                self.assertEqual(
                    result["error"], "search_maintenance_state_unavailable"
                )
                self.assertEqual(path.read_bytes(), raw)

    def test_complete_record_allows_physical_observation(self) -> None:
        self.build_fixture()
        self.durable("complete", attempt_id="one")
        result = self.observe()
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["maintenance"], {"status": "complete"})

    def test_concurrent_completed_pass_invalidates_preceding_observation(self) -> None:
        self.durable("complete", attempt_id="one")

        def changed(*, verify_files: bool = False) -> dict[str, Any]:
            self.durable("complete", attempt_id="two")
            return {"status": "fresh"}

        with mock.patch.object(ResourceSearchIndex, "status", side_effect=changed):
            result = self.observe()
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["error"], "search_maintenance_state_changed")

    def test_concurrent_running_or_failed_pass_is_visible(self) -> None:
        for state, expected in (("running", "building"), ("failed", "degraded")):
            with self.subTest(state=state):
                self.durable("complete", attempt_id="before")

                def changed(*, verify_files: bool = False) -> dict[str, Any]:
                    self.durable(state)
                    return {"status": "fresh"}

                with mock.patch.object(
                    ResourceSearchIndex, "status", side_effect=changed
                ):
                    self.assertEqual(self.observe()["status"], expected)

    def test_public_diagnostics_drop_paths_and_untrusted_errors(self) -> None:
        physical = {
            "status": "degraded",
            "error": "private/fixture/document: failure",
            "path": "private/fixture/database",
            "extra_diagnostic": {"path": "private/fixture/root"},
            "sqlite": {
                "sqlite_version": "fixture",
                "fts5_available": True,
                "error": "private/fixture",
            },
        }
        with mock.patch.object(ResourceSearchIndex, "status", return_value=physical):
            result = self.observe()
        self.assertEqual(result["error"], "index_unreadable")
        self.assertNotIn("private/fixture", json.dumps(result))

    def test_unreadable_index_has_safe_diagnostics(self) -> None:
        path = index_path(self.root, self.root)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a SQLite database")
        before = self.tree_state()
        result = self.observe()
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["error"], "index_unreadable")
        self.assertEqual(self.tree_state(), before)

    def test_durable_running_does_not_wait_for_locked_database(self) -> None:
        self.build_fixture()
        self.durable("running")
        db = sqlite3.connect(index_path(self.root, self.root))
        try:
            db.execute("BEGIN EXCLUSIVE")
            with self.read_only_operation():
                result = self.observe()
            self.assertEqual(result["status"], "building")
        finally:
            db.rollback()
            db.close()

    def test_index_disappearing_before_open_is_never_recreated(self) -> None:
        """Expose a writable-open race in the existing index status owner."""
        self.build_fixture()
        database = index_path(self.root, self.root)
        real_is_file = Path.is_file
        removed = False

        def remove_after_check(path: Path, *args: Any, **kwargs: Any) -> bool:
            nonlocal removed
            present = real_is_file(path, *args, **kwargs)
            if path == database and present and not removed:
                path.unlink()
                removed = True
            return present

        with mock.patch.object(Path, "is_file", new=remove_after_check):
            result = self.observe()
        self.assertTrue(removed)
        self.assertNotEqual(result["status"], "fresh")
        self.assertFalse(
            database.exists(), "Observation recreated the disappeared SQLite database"
        )

    def test_index_read_does_not_wait_for_database_writer(self) -> None:
        """Expose the existing SQLite busy timeout when durable state is absent."""
        self.build_fixture()
        db = sqlite3.connect(index_path(self.root, self.root), timeout=0)
        try:
            db.execute("BEGIN EXCLUSIVE")
            started = time.monotonic()
            result = self.observe()
            elapsed = time.monotonic() - started
        finally:
            db.rollback()
            db.close()
        self.assertNotEqual(result["status"], "fresh")
        self.assertLess(
            elapsed, 1.0, f"Observation waited for the SQLite writer: {elapsed:.3f}s"
        )


class ResourceSearchObservationTests(_ObservationCase):
    def setUp(self) -> None:
        super().setUp()
        self.build_fixture()
        self.selected = copy.deepcopy(self.snapshot)
        self.selected["search_index_scope"] = "project"
        self.selected["snapshot"]["id"] = "project-fixture"
        self.selected["local_search_resources"] = [
            self.selected["local_search_resources"][0]
        ]
        self.reads = _Reads(self.selected)
        self.service = ResourceSearchService(
            self.root / "project", self.root, self.reads
        )
        self.enterContext(
            mock.patch.object(
                WorkplaceSearchCatalogReader,
                "runtime_snapshot",
                return_value=self.snapshot,
            )
        )

    def test_snapshot_guard_precedes_observation_and_query_validation(self) -> None:
        for state in ("stale", "broken", "missing"):
            with self.subTest(state=state):
                self.reads.status = state
                self.reads.events.clear()
                with mock.patch.object(
                    IndexObservationService,
                    "observe",
                    side_effect=AssertionError("Observation before guard"),
                ):
                    with self.assertRaises(LocalSearchError) as caught:
                        self.service.search(query="")
                    readiness = self.service.readiness(snapshot=self.selected)
                self.assertEqual(caught.exception.code, "snapshot_not_fresh")
                self.assertEqual(readiness["reason"], "snapshot_not_fresh")
                self.assertEqual(self.reads.events, ["check", "check"])

    def test_readiness_and_query_preserve_coverage_and_current_filter(self) -> None:
        before = self.tree_state()
        with self.read_only_operation():
            readiness = self.service.readiness()
            first = self.service.search(query="needle")
            self.reads.snapshot["local_search_resources"] = [
                self.snapshot["local_search_resources"][1]
            ]
            second = self.service.search(query="needle")
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(
            readiness["authorized_coverage"]["authorized_resource_count"], 1
        )
        self.assertEqual(readiness["authorized_coverage"]["document_count"], 1)
        self.assertEqual(
            {item["resource_id"] for item in first["results"]}, {"fixture.docs:a"}
        )
        self.assertEqual(
            {item["resource_id"] for item in second["results"]}, {"fixture.docs:b"}
        )
        self.assertEqual(first["scope"], "project_context")
        self.assertEqual(first["search"], first["garage_readiness"])
        self.assertEqual(
            first["authorized_coverage"], first["search"]["authorized_coverage"]
        )
        self.assertEqual(self.tree_state(), before)

    def test_empty_selection_and_metadata_policy_do_not_expose_document_body(
        self,
    ) -> None:
        self.reads.snapshot["local_search_resources"] = []
        with self.read_only_operation():
            empty = self.service.search(query="needle")
            self.reads.snapshot["local_search_resources"] = [
                self.snapshot["local_search_resources"][2]
            ]
            metadata = self.service.search(query="secretbody")
        self.assertEqual(empty["results"], [])
        self.assertEqual(empty["authorized_coverage"]["authorized_resource_count"], 0)
        self.assertEqual(metadata["results"], [])

    def test_incomplete_observation_refuses_queries_with_existing_payload_shape(
        self,
    ) -> None:
        for state, expected in (("running", "building"), ("failed", "degraded")):
            with self.subTest(state=state):
                self.durable(state)
                with self.read_only_operation():
                    with mock.patch.object(
                        ResourceSearchIndex,
                        "search",
                        side_effect=AssertionError("Query during maintenance"),
                    ):
                        result = self.service.search(query="needle", limit=3, offset=1)
                self.assertEqual(result["schema_version"], 1)
                self.assertEqual(result["kind"], "pf.search")
                self.assertEqual(result["search_status"], expected)
                self.assertEqual(result["search"]["status"], "blocked")
                self.assertEqual(result["items"], result["results"])
                self.assertEqual(result["total"], 0)
                self.assertEqual(result["page"]["offset"], 1)
                self.assertEqual(result["page"]["limit"], 3)

    def test_query_and_pagination_validation_remain_active_when_unavailable(
        self,
    ) -> None:
        self.durable("running")
        with self.assertRaises(LocalSearchError) as caught:
            self.service.search(query=" ")
        self.assertEqual(caught.exception.code, "invalid_query")
        with self.assertRaises(LocalSearchError):
            self.service.search(query="needle", limit=-1)

    def test_fresh_with_updates_is_accepted_without_maintenance(self) -> None:
        self.reads.status = "fresh_with_updates"
        with self.read_only_operation():
            result = self.service.search(query="needle")
        self.assertEqual(result["search"]["status"], "ready")
        self.assertEqual(self.reads.events, ["check", "snapshot", "resolve"])


def test_stale_dirty_reason_is_safe_and_explicit(tmp_path: Path) -> None:
    """An unknown dirty reason remains stale without exposing its raw contents."""
    before = set(tmp_path.rglob("*"))
    with mock.patch.object(
        WorkplaceSearchCatalogReader, "runtime_snapshot", return_value={}
    ):
        with mock.patch.object(
            ResourceSearchIndex,
            "status",
            return_value={"status": "stale", "error": "secret-reason-with-content"},
        ):
            observed = IndexObservationService(tmp_path).observe()
    assert observed["status"] == "stale"
    assert observed["error"] == "index_stale"
    assert "secret-reason-with-content" not in json.dumps(observed)
    assert set(tmp_path.rglob("*")) == before


if __name__ == "__main__":
    unittest.main(verbosity=2)
