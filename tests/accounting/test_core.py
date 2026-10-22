"""Behavioral accounting tests with isolated durable databases and a fixed clock."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from processforge_core.accounting.model import (
    ActivityInterval,
    Attribution,
    FactKey,
    Provenance,
    QueryFilter,
    SourceCapability,
    SourceCursor,
    TokenCounts,
    UsageRecord,
)
from processforge_core.accounting.service import AccountingService
from processforge_core.accounting.storage import (
    APPLICATION_ID,
    AccountingStorageError,
    RevisionConflict,
    SchemaVersionError,
    SQLiteAccountingRepository,
)

BASE = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)
PROVENANCE = Provenance(
    source_ref="private-source-reference",
    source_hash="private-content-hash",
    adapter_version="fixture-v1",
)


def usage(
    record: str = "request",
    *,
    project: str | None = "p1",
    revision: int = 1,
    input_total: int | None = 1000,
    output_total: int | None = 200,
    assignment: str | None = "task",
    minute: int = 0,
) -> UsageRecord:
    """Build a bounded observed request with an explicit occurrence id."""
    return UsageRecord(
        key=FactKey(origin_id="origin", source_id="source", record_id=record),
        revision=revision,
        attribution=Attribution(
            project_id=project,
            agent_instance_id="agent",
            assignment_id=assignment,
            run_id="run" if assignment else None,
            attempt=1 if assignment else None,
            provider="fixture",
            model="model-a",
        ),
        occurred_at=BASE + timedelta(minutes=minute),
        tokens=TokenCounts(input_total=input_total, output_total=output_total),
        provenance=PROVENANCE,
    )


def activity(
    record: str,
    start: int,
    end: int | None,
    *,
    agent: str = "a",
    elapsed: float | None = None,
    project: str = "p1",
) -> ActivityInterval:
    """Build activity in minutes; elapsed is optional confirmed seconds."""
    return ActivityInterval(
        key=FactKey(origin_id="origin", source_id="source", record_id=record),
        revision=1,
        attribution=Attribution(project_id=project, agent_instance_id=agent),
        start=BASE + timedelta(minutes=start),
        end=BASE + timedelta(minutes=end) if end is not None else None,
        elapsed_seconds=elapsed
        if elapsed is not None or end is None
        else (end - start) * 60,
        provenance=PROVENANCE,
    )


def cursor(revision: int = 1, position: str = "offset:10") -> SourceCursor:
    """Create an ordered checkpoint without inferring opaque offset semantics."""
    return SourceCursor(
        origin_id="origin",
        source_id="source",
        revision=revision,
        position=position,
        updated_at=BASE + timedelta(seconds=revision),
    )


class CoreTests(unittest.TestCase):
    """Exercise domain invariants and repository/service behavior."""

    def setUp(self) -> None:
        # Use ordinary inherited directory permissions. On Windows sandbox hosts,
        # tempfile's private mode-0700 ACL can exclude the executing token.
        self.scratch_root = Path(
            os.environ.get(
                "PF_ACCOUNTING_TEST_ROOT", str(Path(__file__).resolve().parent)
            )
        ).resolve()
        self.directory = self.scratch_root / f".accounting-test-{uuid4().hex}"
        self.directory.mkdir()
        self.addCleanup(self.cleanup_directory)
        self.path = self.directory / "accounting.sqlite3"
        self.repository = SQLiteAccountingRepository(self.path, busy_timeout_ms=50)
        self.service = AccountingService(
            self.repository, clock=lambda: BASE + timedelta(hours=3)
        )

    def cleanup_directory(self) -> None:
        """Remove only this test's verified child directory."""
        root = self.scratch_root
        if self.directory.resolve().parent != root:
            raise ValueError("temporary directory escaped test scope")
        shutil.rmtree(self.directory)

    def summary(self, projects: tuple[str, ...] = ("p1",), **filters: object) -> dict:
        """Return the public summary for a fixed authorized scope."""
        return self.service.summary(projects, QueryFilter(**filters)).to_dict()

    def test_nullable_counters_subsets_and_zero(self) -> None:
        self.service.ingest(
            [
                replace(
                    usage(),
                    tokens=TokenCounts(
                        input_total=1000,
                        output_total=200,
                        input_cache_read=600,
                        output_reasoning=80,
                    ),
                ),
                usage("missing", input_total=None, output_total=0),
            ]
        )
        result = self.summary()
        self.assertEqual(result["totals"]["total"], 1200)
        self.assertEqual(result["totals"]["output_total"], 200)
        self.assertIsNone(result["totals"]["input_cache_write"])
        self.assertEqual(result["coverage"]["unknown_metrics"]["total"], 1)
        self.assertFalse(result["coverage"]["complete"])
        self.assertIsNone(self.summary()["execution_seconds"])

    def test_invalid_counters_and_attribution(self) -> None:
        for bad in (-1, True, 1.5, "2"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                TokenCounts(input_total=bad)
        for counters in (
            {"input_total": 10, "input_cache_read": 11},
            {"input_total": 10, "input_cache_read": 6, "input_cache_write": 5},
            {"output_total": 10, "output_reasoning": 11},
            {"input_total": 10, "output_total": 1, "reported_total": 10},
        ):
            with self.subTest(counters=counters), self.assertRaises(ValueError):
                TokenCounts(**counters)
        with self.assertRaises(ValueError):
            Attribution(project_id=None, agent_instance_id="a", assignment_id="t")
        with self.assertRaises(ValueError):
            replace(usage(), revision=True)
        with self.assertRaises(ValueError):
            replace(usage(), revision=None)
        with self.assertRaises(ValueError):
            replace(usage().attribution, attempt=2**64)

    def test_idempotency_conflict_and_identical_real_requests(self) -> None:
        record = usage()
        self.assertEqual(self.service.ingest([record]), 1)
        self.assertEqual(self.service.ingest([record]), 0)
        with self.assertRaises(RevisionConflict):
            self.service.ingest([replace(record, tokens=TokenCounts(input_total=1))])
        self.service.ingest([usage("equal-but-distinct")])
        self.assertEqual(self.summary()["totals"]["total"], 2400)

    def test_ordered_revisions_history_and_tombstone(self) -> None:
        self.service.ingest([usage(revision=2, output_total=60)])
        self.service.ingest([usage(revision=1, output_total=40)])
        self.assertEqual(self.summary()["totals"]["output_total"], 60)
        with self.assertRaises(RevisionConflict):
            self.service.ingest([usage(revision=1, output_total=41)])
        self.service.ingest([replace(usage(revision=3), valid=False)])
        self.assertIsNone(self.summary()["totals"]["total"])
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM revisions").fetchone()[0], 3
            )
        self.service.ingest([usage(revision=4, output_total=5)])
        self.assertEqual(self.summary()["totals"]["output_total"], 5)

    def test_fact_cursor_atomic_rollback_and_replay(self) -> None:
        original = usage()
        self.service.ingest([original], cursor=cursor())
        with self.assertRaises(RevisionConflict):
            self.service.ingest(
                [usage("new"), replace(original, tokens=TokenCounts(input_total=3))],
                cursor=cursor(2, "offset:20"),
            )
        self.assertEqual(self.repository.get_cursor("origin", "source"), cursor())
        self.assertEqual(self.summary()["coverage"]["usage_records"], 1)
        self.assertEqual(self.service.ingest([original], cursor=cursor()), 0)
        self.service.ingest([usage(revision=2)], cursor=cursor(3))
        self.service.ingest([original], cursor=cursor(2))
        self.assertEqual(self.repository.get_cursor("origin", "source"), cursor(3))

    def test_cursor_conflict_rolls_back_facts_and_capabilities(self) -> None:
        self.service.ingest(cursor=cursor())
        capability = SourceCapability(
            origin_id="origin",
            source_id="source",
            project_id="p1",
            adapter_version="fixture-v1",
            observed_at=BASE,
        )
        with self.assertRaises(RevisionConflict):
            self.service.ingest(
                [usage()],
                cursor=cursor(position="different"),
                capabilities=[capability],
            )
        self.assertEqual(self.summary()["coverage"]["usage_records"], 0)
        self.assertFalse(self.summary()["coverage"]["inventory_known"])

    def test_cursor_wrong_source_and_bounded_metadata(self) -> None:
        with self.assertRaises(ValueError):
            self.service.ingest([usage()], cursor=replace(cursor(), source_id="other"))
        with self.assertRaises(ValueError):
            replace(cursor(), position="x" * 4097)
        with self.assertRaises(ValueError):
            self.service.ingest([usage()] * 10_001)

    def test_two_agents_overlap_and_same_agent_nesting(self) -> None:
        self.service.ingest(
            activity=[
                activity("a", 0, 10, elapsed=600),
                activity("b", 5, 15, agent="b", elapsed=600),
                activity("nested-a", 2, 4),
                activity("duplicate-a", 0, 10),
            ]
        )
        summary = self.summary()
        self.assertEqual(summary["execution_seconds"], 1200)
        self.assertEqual(summary["occupied_seconds"], 900)
        simultaneous = QueryFilter(
            start=BASE + timedelta(minutes=5), end=BASE + timedelta(minutes=10)
        )
        result = self.service.summary(["p1"], simultaneous).to_dict()
        self.assertEqual(result["execution_seconds"], 600)
        self.assertEqual(result["occupied_seconds"], 300)

    def test_same_agent_separate_projects_and_origins(self) -> None:
        self.service.ingest(
            activity=[activity("a", 0, 10), activity("b", 0, 10, project="p2")]
        )
        result = self.summary(("p1", "p2"))
        self.assertEqual(result["execution_seconds"], 600)
        separate_origin = replace(
            activity("c", 0, 10),
            key=FactKey(origin_id="separate-device", source_id="source", record_id="c"),
        )
        self.service.ingest(activity=[separate_origin])
        self.assertEqual(self.summary(("p1", "p2"))["execution_seconds"], 1200)

    def test_open_interval_has_only_confirmed_lower_bound(self) -> None:
        self.service.ingest(activity=[activity("crashed", 0, None, elapsed=180)])
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 180)
        self.assertIsNone(result["occupied_seconds"])
        self.assertEqual(result["execution_quality"], "lower_bound")
        item = self.service.details(["p1"], kind="activity").to_dict()["items"][0]
        self.assertIsNone(item["confirmed_end"])
        self.assertEqual(item["clock_quality"], "monotonic_only")
        self.assertEqual(result["coverage"]["partial_activity"], 1)
        self.assertEqual(result["as_of"], "2026-10-22T13:00:00.000000+00:00")
        self.assertIsNone(
            self.summary(start=BASE + timedelta(minutes=5))["execution_seconds"]
        )
        self.service.ingest(activity=[activity("no-confirmation", 0, None)])
        self.assertEqual(self.summary()["execution_seconds"], 180)
        self.assertEqual(self.summary()["coverage"]["unknown_duration"], 1)

    def test_unknown_and_zero_duration_remain_distinct(self) -> None:
        self.service.ingest(activity=[activity("unknown", 0, None)])
        self.assertIsNone(self.summary()["execution_seconds"])
        self.service.ingest(activity=[activity("zero", 0, 0, elapsed=0)])
        self.assertEqual(self.summary()["execution_seconds"], 0)
        self.assertEqual(self.summary()["occupied_seconds"], 0)

    def test_activity_revisions_do_not_add_prior_spans(self) -> None:
        original = activity("a", 0, None, elapsed=180)
        self.service.ingest(activity=[original])
        self.service.ingest(
            activity=[
                replace(
                    original,
                    revision=2,
                    end=BASE + timedelta(minutes=5),
                    elapsed_seconds=300,
                )
            ]
        )
        self.service.ingest(activity=[original])
        self.assertEqual(self.summary()["execution_seconds"], 300)
        with self.assertRaises(RevisionConflict):
            self.service.ingest(activity=[replace(original, elapsed_seconds=100)])

    def test_invalid_time_and_duration(self) -> None:
        with self.assertRaises(ValueError):
            replace(usage(), occurred_at=BASE.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            replace(usage(), occurred_at=BASE.astimezone(timezone(timedelta(hours=1))))
        for bad in (-1, True, float("inf"), float("nan")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                activity("bad", 0, None, elapsed=bad)
        with self.assertRaises(ValueError):
            QueryFilter(start=BASE, end=BASE)

    def test_independent_clock_drift_survives_replay_reopen_and_backup(self) -> None:
        interval = activity("drift", 0, 10, elapsed=600.125)
        self.assertEqual(self.service.ingest(activity=[interval]), 1)
        self.assertEqual(self.service.ingest(activity=[interval]), 0)
        self.repository.backup(self.directory / "drift-backup.sqlite3")
        for path in (self.path, self.directory / "drift-backup.sqlite3"):
            with self.subTest(path=path.name):
                service = AccountingService(
                    SQLiteAccountingRepository(path), clock=lambda: BASE
                )
                result = service.summary(["p1"]).to_dict()
                self.assertAlmostEqual(result["execution_seconds"], 600.125)
                self.assertEqual(result["occupied_seconds"], 600)
                self.assertEqual(result["occupied_quality"], "partial")
                self.assertEqual(result["execution_quality"], "measured")
                self.assertEqual(result["coverage"]["clock_quality"]["discrepant"], 1)
                self.assertEqual(result["coverage"]["partial_activity"], 1)
                item = service.details(["p1"], kind="activity").to_dict()["items"][0]
                self.assertEqual(item["utc_span_seconds"], 600)
                self.assertAlmostEqual(item["clock_discrepancy_seconds"], 0.125)
                self.assertTrue(item["partial"])

    def test_independent_clock_window_requires_confirmed_mapping(self) -> None:
        self.service.ingest(activity=[activity("drift", 0, 10, elapsed=599.75)])
        whole = self.summary(start=BASE, end=BASE + timedelta(minutes=10))
        self.assertAlmostEqual(whole["execution_seconds"], 599.75)
        clipped_result = self.summary(
            start=BASE + timedelta(minutes=2), end=BASE + timedelta(minutes=7)
        )
        self.assertIsNone(clipped_result["execution_seconds"])
        self.assertEqual(clipped_result["execution_quality"], "unknown")
        self.assertEqual(clipped_result["coverage"]["unknown_duration"], 1)
        self.assertEqual(clipped_result["occupied_seconds"], 300)
        self.assertIsNone(
            self.summary(start=BASE + timedelta(minutes=10))["execution_seconds"]
        )

    def test_concurrent_agents_sum_monotonic_time_despite_drift(self) -> None:
        self.service.ingest(
            activity=[
                activity("a", 0, 10, elapsed=600.125),
                activity("b", 5, 15, elapsed=599.875, agent="b"),
            ]
        )
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 1200)
        self.assertEqual(result["occupied_seconds"], 900)
        self.assertEqual(result["execution_quality"], "measured")

    def test_nested_independent_clocks_only_prove_a_lower_bound(self) -> None:
        self.service.ingest(
            activity=[
                activity("outer", 0, 10, elapsed=600.125),
                activity("inner", 2, 4, elapsed=120.025),
                activity("duplicate", 0, 10, elapsed=600.125),
                activity("separate-agent", 5, 15, elapsed=599.875, agent="b"),
            ]
        )
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 1200)
        self.assertEqual(result["occupied_seconds"], 900)
        self.assertEqual(result["execution_quality"], "lower_bound")
        # The same conservative bound applies to a partial overlap with drift;
        # no rate-based prorating or summing nested elapsed values is justified.
        self.service.ingest(activity=[activity("overlap", 5, 15, elapsed=600.2)])
        self.assertAlmostEqual(self.summary()["execution_seconds"], 1200.075)

    def test_backwards_utc_jump_never_becomes_negative_execution(self) -> None:
        self.service.ingest(activity=[activity("backwards", 10, 5, elapsed=120)])
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 120)
        self.assertIsNone(result["occupied_seconds"])
        self.assertEqual(result["coverage"]["clock_quality"]["reversed"], 1)
        # SQL must select by both observed endpoints, even when the start moved
        # past the end; clipping cannot reconstruct time spent inside this window.
        clipped_result = self.summary(
            start=BASE + timedelta(minutes=6), end=BASE + timedelta(minutes=8)
        )
        self.assertEqual(clipped_result["coverage"]["activity_intervals"], 1)
        self.assertIsNone(clipped_result["execution_seconds"])
        self.assertIsNone(clipped_result["occupied_seconds"])
        whole = self.summary(
            start=BASE + timedelta(minutes=5), end=BASE + timedelta(minutes=11)
        )
        self.assertEqual(whole["execution_seconds"], 120)

    def test_forward_utc_jump_and_missing_monotonic_are_distinct(self) -> None:
        self.service.ingest(activity=[activity("jump", 0, 60, elapsed=60)])
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 60)
        self.assertEqual(result["occupied_seconds"], 3600)
        self.assertEqual(result["coverage"]["clock_quality"]["discrepant"], 1)
        self.service.ingest(
            activity=[
                replace(activity("utc-only", 0, 10, agent="b"), elapsed_seconds=None)
            ]
        )
        result = self.summary()
        self.assertEqual(result["execution_seconds"], 60)
        self.assertEqual(result["execution_quality"], "lower_bound")
        self.assertEqual(result["coverage"]["clock_quality"]["utc_only"], 1)
        self.assertEqual(result["coverage"]["unknown_duration"], 1)

    def test_utc_only_activity_does_not_invent_monotonic_duration(self) -> None:
        self.service.ingest(
            activity=[replace(activity("utc-only", 0, 10), elapsed_seconds=None)]
        )
        result = self.summary()
        self.assertIsNone(result["execution_seconds"])
        self.assertEqual(result["occupied_seconds"], 600)
        self.assertEqual(result["execution_quality"], "unknown")

    def test_cross_project_scope_unassigned_and_quarantine(self) -> None:
        self.service.ingest(
            [
                usage(),
                usage("unassigned", assignment=None),
                usage("other", project="p2"),
                usage("quarantine", project=None, assignment=None),
            ]
        )
        self.assertEqual(self.summary()["totals"]["total"], 2400)
        self.assertEqual(self.summary(("p1", "p2"))["totals"]["total"], 3600)
        self.assertEqual(self.summary()["attribution"]["usage_project_unassigned"], 1)
        self.assertEqual(self.summary(assignment_id="task")["totals"]["total"], 1200)
        with self.assertRaises(PermissionError):
            self.summary(project_id="p2")
        self.assertIsNone(self.summary(())["totals"]["total"])
        self.assertEqual(self.service.projects([]).to_dict()["items"], [])

    def test_binding_revision_moves_current_contribution(self) -> None:
        self.service.ingest([usage(project=None, assignment=None)])
        self.service.ingest([usage(revision=2)])
        self.assertEqual(self.summary()["totals"]["total"], 1200)
        self.assertEqual(len(self.service.details(["p1"]).to_dict()["items"]), 1)

    def test_time_filter_clips_activity_but_never_tokens(self) -> None:
        self.service.ingest([usage(minute=12)], [activity("span", 0, 15)])
        result = self.summary(
            start=BASE + timedelta(minutes=5), end=BASE + timedelta(minutes=10)
        )
        self.assertEqual(result["execution_seconds"], 300)
        self.assertIsNone(result["totals"]["total"])
        self.assertEqual(
            self.summary(start=BASE + timedelta(minutes=12))["totals"]["total"], 1200
        )
        self.assertIsNone(
            self.summary(end=BASE + timedelta(minutes=12))["totals"]["total"]
        )
        outside = self.summary(start=BASE + timedelta(minutes=15))
        self.assertIsNone(outside["execution_seconds"])

    def test_filters_and_stable_bounded_pagination(self) -> None:
        self.service.ingest([usage(record) for record in ("z", "a", "m")])
        first = self.service.details(["p1"], QueryFilter(limit=2)).to_dict()
        second = self.service.details(["p1"], QueryFilter(limit=2, offset=2)).to_dict()
        self.assertEqual(
            [item["key"]["record_id"] for item in first["items"]], ["a", "m"]
        )
        self.assertEqual([item["key"]["record_id"] for item in second["items"]], ["z"])
        self.assertEqual(first["pagination"]["next_offset"], 2)
        self.assertIsNone(second["pagination"]["next_offset"])
        self.assertEqual(first["totals"], second["totals"])
        for name, value in (
            ("source_id", "missing"),
            ("model", "missing"),
            ("run_id", "missing"),
            ("attempt", 2),
        ):
            with self.subTest(filter=name):
                self.assertEqual(
                    self.summary(**{name: value})["coverage"]["usage_records"], 0
                )
        for kwargs in (
            {"limit": 0},
            {"limit": 501},
            {"offset": -1},
            {"offset": True},
            {"offset": 1_000_001},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                QueryFilter(**kwargs)
        with self.assertRaises(ValueError):
            self.service.details(["p1"], kind="raw")

    def test_public_dto_is_json_safe_and_omits_private_provenance(self) -> None:
        self.service.ingest([usage()], [activity("span", 0, None, elapsed=180)])
        for kind in ("usage", "activity"):
            result = self.service.details(["p1"], kind=kind).to_dict()
            serialized = json.dumps(result, allow_nan=False)
            self.assertNotIn(PROVENANCE.source_ref, serialized)
            self.assertNotIn(PROVENANCE.source_hash, serialized)
            self.assertNotIn("source_ref", serialized)
            self.assertNotIn("currency", serialized)
            self.assertNotIn("price", serialized)
            self.assertEqual(result["schema_version"], 1)

    def test_sources_missing_unsupported_and_atomic_capability_conflict(self) -> None:
        first = SourceCapability(
            origin_id="origin",
            source_id="source",
            project_id="p1",
            adapter_version="fixture-v1",
            observed_at=BASE,
            supported_metrics=("input_total", "output_total"),
        )
        missing = replace(
            first, source_id="missing", status="missing", supported_metrics=()
        )
        hidden = replace(first, project_id="p2", source_id="private")
        self.service.ingest([usage()], capabilities=[first, missing, hidden])
        result = self.summary()
        self.assertEqual(result["coverage"]["declared_sources"]["available"], 1)
        self.assertEqual(result["coverage"]["declared_sources"]["missing"], 1)
        self.assertEqual(
            result["coverage"]["unsupported_metrics"]["output_reasoning"], 2
        )
        with self.assertRaises(RevisionConflict):
            self.service.ingest(
                [usage("rollback")],
                cursor=cursor(),
                capabilities=[replace(first, status="partial")],
            )
        self.assertEqual(self.summary()["coverage"]["usage_records"], 1)
        self.assertIsNone(self.repository.get_cursor("origin", "source"))
        newer = replace(
            first, observed_at=BASE + timedelta(seconds=1), status="partial"
        )
        self.service.ingest(capabilities=[newer])
        self.service.ingest(capabilities=[first])
        self.assertEqual(self.summary()["coverage"]["declared_sources"]["partial"], 1)

    def test_projects_share_summary_and_include_missing_source_only_project(
        self,
    ) -> None:
        self.service.ingest([usage(), usage("p2", project="p2")])
        self.service.ingest(
            capabilities=[
                SourceCapability(
                    origin_id="origin",
                    source_id="absent",
                    project_id="p3",
                    adapter_version="fixture-v1",
                    observed_at=BASE,
                    status="missing",
                )
            ]
        )
        result = self.service.projects(
            ["p3", "p2", "p1"], QueryFilter(limit=2)
        ).to_dict()
        self.assertEqual([item["project_id"] for item in result["items"]], ["p1", "p2"])
        self.assertEqual(result["pagination"]["total"], 3)
        for item in result["items"]:
            expected = self.service.summary(
                [item["project_id"]],
                QueryFilter(project_id=item["project_id"], limit=2),
            ).to_dict()
            self.assertEqual(item["summary"], expected)

    def test_reopen_backup_and_refuse_overwrite(self) -> None:
        self.service.ingest([usage()], cursor=cursor())
        backup = self.directory / "backup.sqlite3"
        self.repository.backup(backup)
        reopened = SQLiteAccountingRepository(backup)
        self.assertEqual(reopened.get_cursor("origin", "source"), cursor())
        self.assertEqual(
            AccountingService(reopened).summary(["p1"]).to_dict()["totals"]["total"],
            1200,
        )
        with self.assertRaises(FileExistsError):
            self.repository.backup(backup)
        self.assertEqual(
            AccountingService(SQLiteAccountingRepository(self.path))
            .summary(["p1"])
            .to_dict()["totals"]["total"],
            1200,
        )

    def test_foreign_future_and_incomplete_schema_fail_closed(self) -> None:
        foreign = self.directory / "foreign.sqlite3"
        with closing(sqlite3.connect(foreign)) as connection:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
        with self.assertRaises(SchemaVersionError):
            SQLiteAccountingRepository(foreign)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA user_version = 999")
        with self.assertRaises(SchemaVersionError):
            self.summary()
        with self.assertRaises(SchemaVersionError):
            SQLiteAccountingRepository(self.path)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(
                connection.execute("PRAGMA application_id").fetchone()[0],
                APPLICATION_ID,
            )
            connection.execute("PRAGMA user_version = 1")
            connection.execute("DROP TABLE source_cursors")
        with self.assertRaises(SchemaVersionError):
            self.service.ingest([usage()])

    def test_bounded_busy_failure_rolls_back_and_allows_replay(self) -> None:
        blocking = sqlite3.connect(self.path, isolation_level=None)
        self.addCleanup(blocking.close)
        blocking.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaises(AccountingStorageError):
                self.service.ingest([usage()], cursor=cursor())
        finally:
            blocking.execute("ROLLBACK")
        self.assertIsNone(self.repository.get_cursor("origin", "source"))
        self.assertEqual(self.service.ingest([usage()], cursor=cursor()), 1)

    def test_concurrent_replay_has_one_contribution(self) -> None:
        repository = SQLiteAccountingRepository(self.path, busy_timeout_ms=5000)
        with ThreadPoolExecutor(max_workers=4) as executor:
            inserted = list(
                executor.map(
                    lambda _: repository.ingest([usage()], cursor=cursor()), range(8)
                )
            )
        self.assertEqual(sum(inserted), 1)
        self.assertEqual(self.summary()["totals"]["total"], 1200)

    def test_snapshot_consistency_during_late_ingestion(self) -> None:
        self.service.ingest([usage()])
        with self.repository.snapshot() as connection:
            before = list(
                self.repository.facts(connection, ["p1"], QueryFilter(), "usage")
            )
            self.service.ingest([usage("late")])
            after = list(
                self.repository.facts(connection, ["p1"], QueryFilter(), "usage")
            )
        self.assertEqual(before, after)
        self.assertEqual(self.summary()["coverage"]["usage_records"], 2)


if __name__ == "__main__":
    unittest.main()
