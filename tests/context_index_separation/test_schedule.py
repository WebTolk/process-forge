"""Exercise the cold job boundary without indexing a workplace."""

from __future__ import annotations

import builtins
import copy
import importlib
import io
import os
import socket
import sqlite3
import sys
import threading
import unittest
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

from processforge_core.resources import index_schedule

_MAINTENANCE_MODULE = "processforge_core.resources.index_maintenance"


class _FakeMaintenanceService:
    """Record calls and supply canonical outcomes without operational effects."""

    def __init__(self, *outcomes: dict[str, Any] | BaseException) -> None:
        """Retain the outcomes supplied by this test."""
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, bool]] = []

    def __bool__(self) -> bool:
        """Expose a valid dependency whose truth value is false."""
        return False

    def run(self, *, reason: str, verify_files: bool) -> dict[str, Any]:
        """Record one explicit call and supply its next outcome."""
        self.calls.append((reason, verify_files))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _UnprintableFailure(RuntimeError):
    """Fail if an adapter tries to render possibly private exception details."""

    def __str__(self) -> str:
        raise AssertionError("The job must not render exception text")


@contextmanager
def _deny_operational_effects() -> Iterator[None]:
    """Reject operational IO while permitting Python's source loader reads."""
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        """Reject eager imports of the operational maintenance dependency."""
        if name == _MAINTENANCE_MODULE:
            raise AssertionError("Maintenance must not be imported eagerly")
        return original_import(name, *args, **kwargs)

    with ExitStack() as stack:
        for name in (
            "resolve",
            "absolute",
            "stat",
            "exists",
            "is_dir",
            "is_file",
            "open",
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "mkdir",
            "iterdir",
            "glob",
            "rglob",
        ):
            stack.enter_context(
                patch.object(Path, name, side_effect=AssertionError(name))
            )
        for owner, name in (
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (os, "mkdir"),
            (os, "scandir"),
            (socket, "socket"),
            (socket, "create_connection"),
            (sqlite3, "connect"),
            (threading, "Thread"),
            (threading, "Timer"),
        ):
            stack.enter_context(
                patch.object(owner, name, side_effect=AssertionError(name))
            )
        stack.enter_context(patch.object(builtins, "__import__", guarded_import))
        yield


class IndexMaintenanceJobTests(unittest.TestCase):
    """Verify delegation, cold composition and failure ownership."""

    def setUp(self) -> None:
        """Use only symbolic roots inside the assignment's scratch scope."""
        self.workplace = Path(
            ".pf/tmp/context-index-alpha4-schedule-r3-20261023/workplace"
        )
        self.distribution = self.workplace.parent / "distribution"

    def test_import_and_construction_have_no_operational_effects(self) -> None:
        """Keep imports and both constructor modes cold."""
        fake = _FakeMaintenanceService({})
        with _deny_operational_effects():
            importlib.reload(index_schedule)
            index_schedule.IndexMaintenanceJob(
                self.workplace, distribution_root=self.distribution
            )
            index_schedule.IndexMaintenanceJob(self.workplace, maintenance_service=fake)
        self.assertEqual(fake.calls, [])

    def test_injected_falsey_service_receives_exact_call_and_result(self) -> None:
        """Preserve a borrowed dependency and its opaque result unchanged."""
        result = {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance",
            "scope": "workplace",
            "project_count": 0,
            "results": [{"status": "complete"}],
            "report": {"future_field": [1, 2]},
        }
        before = copy.deepcopy(result)
        fake = _FakeMaintenanceService(result)
        job = index_schedule.IndexMaintenanceJob(
            self.workplace, maintenance_service=fake
        )
        with _deny_operational_effects():
            actual = job.execute()
        self.assertIs(actual, result)
        self.assertEqual(result, before)
        self.assertEqual(fake.calls, [("scheduler", True)])

    def test_default_composition_uses_canonical_module_and_explicit_roots(self) -> None:
        """Forward both explicit and omitted distribution roots at execution."""
        for distribution in (None, self.distribution):
            with self.subTest(distribution=distribution is not None):
                result = {"report": {"status": "complete"}}
                fake = _FakeMaintenanceService(result)
                factory = Mock(return_value=fake)
                module = ModuleType(_MAINTENANCE_MODULE)
                module.__dict__["WorkplaceIndexMaintenanceService"] = factory
                with patch.dict(sys.modules, {_MAINTENANCE_MODULE: module}):
                    job = index_schedule.IndexMaintenanceJob(
                        self.workplace, distribution_root=distribution
                    )
                    factory.assert_not_called()
                    self.assertIs(job.execute(), result)
                factory.assert_called_once_with(
                    self.workplace, distribution_root=distribution
                )
                self.assertEqual(fake.calls, [("scheduler", True)])

    def test_non_success_results_are_not_relabelled_or_retried(self) -> None:
        """Leave refusal and partial failure policy with the shared owner."""
        for status in ("busy", "failed", "incomplete"):
            with self.subTest(status=status):
                result = {
                    "action": status,
                    "results": [{"status": status}],
                    "report": {"reason": "maintenance_reason", "unknown": [status]},
                }
                before = copy.deepcopy(result)
                fake = _FakeMaintenanceService(result)
                job = index_schedule.IndexMaintenanceJob(
                    self.workplace, maintenance_service=fake
                )
                self.assertIs(job.execute(), result)
                self.assertEqual(result, before)
                self.assertEqual(fake.calls, [("scheduler", True)])

    def test_exceptions_propagate_without_rendering_or_automatic_retry(self) -> None:
        """Preserve failures and cancellation without printing private text."""
        for failure in (_UnprintableFailure(), OSError(), KeyboardInterrupt()):
            with self.subTest(error_type=type(failure).__name__):
                fake = _FakeMaintenanceService(failure)
                job = index_schedule.IndexMaintenanceJob(
                    self.workplace, maintenance_service=fake
                )
                with self.assertRaises(type(failure)) as caught:
                    job.execute()
                self.assertIs(caught.exception, failure)
                self.assertEqual(fake.calls, [("scheduler", True)])

    def test_retry_requires_another_explicit_execution(self) -> None:
        """Permit recovery only when the caller invokes the job again."""
        failure = _UnprintableFailure()
        result = {"report": {"status": "complete", "attempt": 2}}
        fake = _FakeMaintenanceService(failure, result)
        job = index_schedule.IndexMaintenanceJob(
            self.workplace, maintenance_service=fake
        )
        with self.assertRaises(_UnprintableFailure):
            job.execute()
        self.assertEqual(fake.calls, [("scheduler", True)])
        self.assertIs(job.execute(), result)
        self.assertEqual(fake.calls, [("scheduler", True), ("scheduler", True)])

    def test_each_execution_reads_a_new_result(self) -> None:
        """Observe each operation's result without an adapter lifetime cache."""
        first = {"report": {"generation": 1}}
        second = {"report": {"generation": 2}}
        fake = _FakeMaintenanceService(first, second)
        job = index_schedule.IndexMaintenanceJob(
            self.workplace, maintenance_service=fake
        )
        self.assertIs(job.execute(), first)
        self.assertIs(job.execute(), second)
        self.assertEqual(fake.calls, [("scheduler", True), ("scheduler", True)])

    def test_default_service_is_operation_local(self) -> None:
        """Create a separate default service for each explicit execution."""
        first = {"report": {"generation": 1}}
        second = {"report": {"generation": 2}}
        first_service = _FakeMaintenanceService(first)
        second_service = _FakeMaintenanceService(second)
        factory = Mock(side_effect=[first_service, second_service])
        module = ModuleType(_MAINTENANCE_MODULE)
        module.__dict__["WorkplaceIndexMaintenanceService"] = factory
        with patch.dict(sys.modules, {_MAINTENANCE_MODULE: module}):
            job = index_schedule.IndexMaintenanceJob(self.workplace)
            self.assertIs(job.execute(), first)
            self.assertIs(job.execute(), second)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(first_service.calls, [("scheduler", True)])
        self.assertEqual(second_service.calls, [("scheduler", True)])

    def test_default_service_construction_failure_propagates(self) -> None:
        """Preserve a default dependency failure without formatting it."""
        failure = _UnprintableFailure()
        factory = Mock(side_effect=failure)
        module = ModuleType(_MAINTENANCE_MODULE)
        module.__dict__["WorkplaceIndexMaintenanceService"] = factory
        with patch.dict(sys.modules, {_MAINTENANCE_MODULE: module}):
            job = index_schedule.IndexMaintenanceJob(self.workplace)
            with self.assertRaises(_UnprintableFailure) as caught:
                job.execute()
        self.assertIs(caught.exception, failure)
        factory.assert_called_once_with(self.workplace, distribution_root=None)

    def test_real_default_composition_with_maintenance_execution_replaced(self) -> None:
        """Construct the real service while replacing its operational run method."""
        canonical = importlib.import_module(_MAINTENANCE_MODULE)
        result = {"report": {"status": "boundary_fixture"}}
        with patch.object(
            canonical.WorkplaceIndexMaintenanceService,
            "run",
            autospec=True,
            return_value=result,
        ) as run:
            job = index_schedule.IndexMaintenanceJob(
                self.workplace, distribution_root=self.distribution
            )
            run.assert_not_called()
            self.assertIs(job.execute(), result)
        run.assert_called_once()
        service = run.call_args.args[0]
        self.assertIsInstance(service, canonical.WorkplaceIndexMaintenanceService)
        self.assertIs(service.workplace_root, self.workplace)
        self.assertIs(service.distribution_root, self.distribution)
        self.assertEqual(
            run.call_args.kwargs, {"reason": "scheduler", "verify_files": True}
        )
