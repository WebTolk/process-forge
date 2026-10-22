"""Collector cases plus a sanitized native Codex terminal usage receipt."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from processforge_core.accounting.binding import CollectionBinding
from processforge_core.accounting.collectors import (
    ProviderCollector,
    execution_interval,
    import_timing,
)
from processforge_core.accounting.model import Attribution, QueryFilter
from processforge_core.accounting.service import AccountingService
from processforge_core.accounting.storage import (
    RevisionConflict,
    SQLiteAccountingRepository,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
CODEX = {
    "type": "turn.completed",
    "usage": {"input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 30},
}


class SyntheticCollectorTests(unittest.TestCase):
    """Check mapping, occurrence identity, replay and bounded failure behavior."""

    def setUp(self) -> None:
        self.root = Path(__file__).parent.resolve() / ("fixture-" + uuid4().hex)
        self.root.mkdir()
        assert self.root.parent == Path(__file__).parent.resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.service = AccountingService(
            SQLiteAccountingRepository(self.root / "usage.sqlite3")
        )
        self.binding = CollectionBinding(
            origin_id="local-test",
            source_id="attempt-1",
            profile="codex-exec-v1",
            observed_at=NOW,
            attribution=Attribution(
                project_id="p",
                agent_instance_id="agent",
                session_id="session",
                run_id="run",
                assignment_id="task",
                attempt=1,
                provider="codex",
                model="test-model",
            ),
        )
        self.path = self.root / "synthetic.jsonl"
        self.collector = ProviderCollector()

    def write_events(self, *events: dict) -> None:
        self.path.write_bytes(
            b"".join(json.dumps(event).encode() + b"\n" for event in events)
        )

    def totals(self) -> dict:
        return self.service.summary(["p"]).to_dict()

    def kimi(self) -> tuple[CollectionBinding, dict]:
        binding = replace(
            self.binding,
            profile="kimi-code-2.3.0-v1",
            attribution=replace(self.binding.attribution, provider="kimi"),
        )
        event = {
            "type": "usage.record",
            "primary": True,
            "occurrence_id": "request-1",
            "session_id": "session",
            "agentId": "agent",
            "model": "test-model",
            "usageScope": "session",
            "timestamp": NOW.isoformat(),
            "usage": {
                "inputOther": 40,
                "inputCacheRead": 20,
                "inputCacheCreation": 10,
                "output": 3,
            },
        }
        return binding, event

    def test_identical_distinct_codex_requests_and_replay(self) -> None:
        self.write_events(CODEX, CODEX)
        first = self.collector.collect(self.path, self.binding, self.service)
        self.assertEqual(first.stored, 2)
        self.assertEqual(self.totals()["totals"]["total"], 260)
        self.assertEqual(self.totals()["totals"]["input_cache_read"], 40)
        self.assertEqual(
            self.collector.collect(self.path, self.binding, self.service).stored, 0
        )
        with self.path.open("ab") as stream:
            stream.write(json.dumps(CODEX).encode() + b"\n")
        self.assertEqual(
            self.collector.collect(self.path, self.binding, self.service).stored, 1
        )

    def test_missing_counter_is_null_not_zero(self) -> None:
        self.write_events({"type": "turn.completed", "usage": {"input_tokens": 0}})
        self.collector.collect(self.path, self.binding, self.service)
        data = self.totals()
        self.assertEqual(data["totals"]["input_total"], 0)
        self.assertIsNone(data["totals"]["output_total"])
        self.assertIsNone(data["totals"]["total"])
        self.assertFalse(data["coverage"]["complete"])

    def test_native_codex_subcategories_and_replay(self) -> None:
        # Sanitized usage payload captured from the PF core-fix worker on 2026-10-22.
        self.write_events(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 1221601,
                    "cached_input_tokens": 1148928,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 21482,
                    "reasoning_output_tokens": 8603,
                },
            }
        )
        self.assertEqual(
            self.collector.collect(self.path, self.binding, self.service).stored, 1
        )
        totals = self.totals()["totals"]
        self.assertEqual(totals["input_total"], 1221601)
        self.assertEqual(totals["output_total"], 21482)
        self.assertEqual(totals["total"], 1243083)
        self.assertEqual(totals["input_cache_read"], 1148928)
        self.assertEqual(totals["input_cache_write"], 0)
        self.assertEqual(totals["output_reasoning"], 8603)
        self.assertEqual(
            self.collector.collect(self.path, self.binding, self.service).stored, 0
        )
        self.assertEqual(self.totals()["totals"], totals)

    def test_torn_tail_resumes_without_duplicate_prefix(self) -> None:
        self.write_events(CODEX)
        with self.path.open("ab") as stream:
            stream.write(b'{"type":')
        result = self.collector.collect(self.path, self.binding, self.service)
        self.assertEqual(result.stored, 1)
        self.assertEqual(result.error, "oversized_or_torn_line")
        self.write_events(CODEX, CODEX)
        self.assertEqual(
            self.collector.collect(self.path, self.binding, self.service).stored, 1
        )

    def test_malformed_tail_is_explicit_and_keeps_prefix(self) -> None:
        self.write_events(CODEX)
        with self.path.open("ab") as stream:
            stream.write(b"{bad}\n")
        result = self.collector.collect(self.path, self.binding, self.service)
        self.assertEqual(result.error, "malformed_receipt")
        self.assertEqual(result.lines, 1)
        self.assertEqual(result.stored, 1)

    def test_invalid_timestamp_keeps_prefix_and_resumes(self) -> None:
        for index, bad_timestamp in enumerate((None, 123, [], {})):
            with self.subTest(timestamp=bad_timestamp):
                binding = replace(self.binding, source_id=f"bad-timestamp-{index}")
                self.write_events(CODEX, {**CODEX, "timestamp": bad_timestamp})
                result = self.collector.collect(self.path, binding, self.service)
                self.assertEqual(result.error, "malformed_receipt")
                self.assertEqual(result.stored, 1)
                self.assertEqual(result.lines, 1)
                cursor = self.service.repository.get_cursor(
                    binding.origin_id, binding.source_id
                )
                self.assertEqual(json.loads(cursor.position)["line"], 1)
                # Repair only the unaccepted tail; the accepted prefix stays exact.
                self.write_events(CODEX, CODEX)
                resumed = self.collector.collect(self.path, binding, self.service)
                self.assertIsNone(resumed.error)
                self.assertEqual(resumed.stored, 1)
                self.assertEqual(
                    self.collector.collect(self.path, binding, self.service).stored, 0
                )

    def test_changed_or_truncated_prefix_is_rejected(self) -> None:
        self.write_events(CODEX, CODEX)
        self.collector.collect(self.path, self.binding, self.service)
        self.write_events({**CODEX, "usage": {"input_tokens": 1}}, CODEX)
        with self.assertRaisesRegex(ValueError, "prefix_changed"):
            self.collector.collect(self.path, self.binding, self.service)
        self.write_events(CODEX)
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.collector.collect(self.path, self.binding, self.service)

    def test_changed_binding_is_rejected(self) -> None:
        self.write_events(CODEX)
        self.collector.collect(self.path, self.binding, self.service)
        changed = replace(
            self.binding,
            attribution=replace(self.binding.attribution, assignment_id="other"),
        )
        with self.assertRaisesRegex(ValueError, "binding_changed"):
            self.collector.collect(self.path, changed, self.service)

    def test_kimi_session_delta_and_context_counts(self) -> None:
        binding, event = self.kimi()
        self.write_events(
            {
                "type": "PreCompact",
                "token_count": 99999,
                "estimated_token_count": 99999,
            },
            event,
            {**event, "occurrence_id": "request-2"},
        )
        self.assertEqual(
            self.collector.collect(self.path, binding, self.service).stored, 2
        )
        self.assertEqual(self.totals()["totals"]["input_total"], 140)
        self.assertEqual(self.totals()["totals"]["total"], 146)
        self.assertEqual(self.totals()["totals"]["input_cache_write"], 20)

    def test_kimi_partial_input_is_unknown(self) -> None:
        binding, event = self.kimi()
        del event["usage"]["inputOther"]
        self.write_events(event)
        self.collector.collect(self.path, binding, self.service)
        self.assertIsNone(self.totals()["totals"]["input_total"])

    def test_kimi_duplicate_native_occurrence_deduplicates(self) -> None:
        binding, event = self.kimi()
        self.write_events(event, event)
        self.assertEqual(
            self.collector.collect(self.path, binding, self.service).stored, 1
        )

    def test_kimi_bad_identity_or_mirror_is_rejected(self) -> None:
        binding, event = self.kimi()
        for change in (
            {"session_id": "wrong"},
            {"agentId": "child"},
            {"primary": False},
            {"occurrence_id": ""},
            {"model": "wrong"},
        ):
            with self.subTest(change=change):
                self.write_events({**event, **change})
                result = self.collector.collect(self.path, binding, self.service)
                self.assertEqual(result.error, "malformed_receipt")
                self.assertEqual(result.stored, 0)

    def test_conflicting_occurrence_rolls_back_batch_and_cursor(self) -> None:
        binding, event = self.kimi()
        self.write_events(event, {**event, "usage": {"output": 7}})
        with self.assertRaises(RevisionConflict):
            self.collector.collect(self.path, binding, self.service)
        self.assertIsNone(
            self.service.repository.get_cursor(binding.origin_id, binding.source_id)
        )
        self.assertIsNone(self.totals()["totals"]["total"])

    def test_empty_missing_and_unsupported_coverage(self) -> None:
        result = self.collector.collect(self.path, self.binding, self.service)
        self.assertEqual(result.status, "missing")
        self.assertEqual(self.totals()["coverage"]["declared_sources"]["missing"], 1)
        self.path.write_bytes(b"")
        self.collector.collect(self.path, self.binding, self.service)
        self.assertIsNone(self.totals()["totals"]["input_total"])
        legacy = replace(
            self.binding,
            source_id="legacy",
            profile="kimi-cli-legacy-unsupported",
            attribution=replace(self.binding.attribution, provider="kimi"),
        )
        self.assertEqual(
            self.collector.collect(self.path, legacy, self.service).status,
            "unsupported",
        )

    def test_no_wall_clock_fiction_or_open_tail(self) -> None:
        fact = execution_interval(
            self.binding,
            start=NOW,
            wall_end=NOW + timedelta(seconds=90),
            elapsed_seconds=10,
            source_hash="synthetic",
        )
        self.assertEqual(fact.end, NOW + timedelta(seconds=90))
        self.assertEqual(fact.clock_quality, "discrepant")
        self.assertEqual(fact.clock_discrepancy_seconds, -80)
        self.assertEqual(fact.elapsed_seconds, 10)
        self.assertEqual(fact.quality, "partial")
        self.service.ingest(activity=[fact])
        self.assertEqual(self.totals()["execution_seconds"], 10)
        self.assertEqual(self.totals()["coverage"]["partial_activity"], 1)

    def test_timing_replay_and_exact_binding(self) -> None:
        path = self.root / "timing.json"
        payload = {
            "schema_version": 1,
            "source_id": self.binding.source_id,
            "attribution": vars(self.binding.attribution),
            "start": NOW.isoformat(),
            "wall_end": (NOW + timedelta(seconds=10)).isoformat(),
            "elapsed_seconds": 10,
            "revision": 1,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(import_timing(path, self.binding, self.service), 1)
        self.assertEqual(import_timing(path, self.binding, self.service), 0)
        self.assertEqual(self.totals()["execution_seconds"], 10)
        with self.assertRaisesRegex(ValueError, "binding_mismatch"):
            import_timing(path, replace(self.binding, source_id="wrong"), self.service)

    def test_unknown_project_or_incomplete_work_binding_rejected(self) -> None:
        with self.assertRaises(ValueError):
            replace(
                self.binding, attribution=replace(self.binding.attribution, run_id=None)
            )
        self.assertEqual(
            self.service.summary([]).to_dict()["coverage"]["usage_records"], 0
        )
        with self.assertRaises(PermissionError):
            self.service.summary(["p"], QueryFilter(project_id="other"))

    def test_bounds_and_invalid_counters(self) -> None:
        self.write_events(CODEX)
        with patch("processforge_core.accounting.collectors.MAX_FILE", 8):
            self.assertEqual(
                self.collector.collect(self.path, self.binding, self.service).error,
                "receipt_size_limit",
            )
        with patch("processforge_core.accounting.collectors.MAX_LINE", 8):
            self.assertEqual(
                self.collector.collect(self.path, self.binding, self.service).error,
                "oversized_or_torn_line",
            )
        for value in (True, -1, 1.5, 2**63):
            self.write_events(
                {"type": "turn.completed", "usage": {"input_tokens": value}}
            )
            self.assertEqual(
                self.collector.collect(self.path, self.binding, self.service).error,
                "malformed_receipt",
            )

    def test_batch_boundary_retains_valid_prefix_on_conflict(self) -> None:
        binding, event = self.kimi()
        events = [
            {**event, "occurrence_id": f"request-{number}"} for number in range(100)
        ]
        self.write_events(*events, {**events[0], "usage": {"output": 9}})
        with self.assertRaises(RevisionConflict):
            self.collector.collect(self.path, binding, self.service)
        cursor = self.service.repository.get_cursor(
            binding.origin_id, binding.source_id
        )
        self.assertEqual(json.loads(cursor.position)["line"], 100)
        self.assertEqual(self.totals()["coverage"]["usage_records"], 100)

    def test_project_only_kimi_unknown_model_and_interrupted_interval(self) -> None:
        binding, event = self.kimi()
        binding = replace(
            binding,
            attribution=replace(
                binding.attribution,
                run_id=None,
                assignment_id=None,
                attempt=None,
                model=None,
            ),
        )
        del event["model"]
        self.write_events(event)
        self.collector.collect(self.path, binding, self.service)
        self.assertEqual(self.totals()["attribution"]["usage_project_unassigned"], 1)
        interval = execution_interval(
            binding,
            start=NOW,
            wall_end=None,
            elapsed_seconds=None,
            source_hash="interrupted",
        )
        self.service.ingest(activity=[interval])
        self.assertIsNone(self.totals()["execution_seconds"])
        self.assertEqual(self.totals()["coverage"]["unknown_duration"], 1)


if __name__ == "__main__":
    unittest.main()
