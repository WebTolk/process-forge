"""Verify explicit maintenance, durable failures, concurrency and CLI contracts."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from pf_cli.commands.search_index import (
    SearchIndexRebuildCommand,
    SearchIndexRefreshCommand,
    SearchIndexTickCommand,
)
from pf_cli.commands.search_maintenance import WorkplaceIndexMaintenanceCommand
from pf_cli.parsers.search_maintenance import register_search_index_maintenance

from processforge_core.resources.index_backend import ResourceIndexBackend
from processforge_core.resources.index_maintenance import (
    IndexMaintenanceError,
    WorkplaceIndexMaintenanceService,
)
from processforge_core.resources.index_observation import maintenance_state_path
from processforge_core.resources.local_search import LocalSearchError

_CATALOGUE = (
    "processforge_core.resources.index_maintenance.WorkplaceSearchCatalogReader"
)
_ATOMIC_WRITE = "processforge_core.resources.index_maintenance._atomic_write"


class MaintenanceTests(unittest.TestCase):
    """Keep all fixtures local and exercise actual application execution paths."""

    def setUp(self) -> None:
        base = Path(os.environ.get("PF_MAINTENANCE_TEST_TMP", tempfile.gettempdir()))
        self.root = base / f"maintenance-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(self._cleanup, base)
        self.workplace = self.root / "workplace"
        self.snapshot: dict[str, Any] = {"snapshot": {"checksum": "project-a"}}
        self.tick: dict[str, Any] = {
            "action": "none",
            "after": {
                "status": "fresh",
                "generation": "fixture-generation",
                "document_count": 7,
                "stale_resource_count": 0,
                "failed_file_count": 0,
            },
        }

    def _cleanup(self, base: Path) -> None:
        if self.root.resolve().parent != base.resolve():
            raise AssertionError("fixture escaped its temporary base")
        shutil.rmtree(self.root)

    def service(
        self, backend: ResourceIndexBackend | None = None
    ) -> WorkplaceIndexMaintenanceService:
        if backend is None:
            backend = Mock()
            backend.maintenance_tick.return_value = self.tick
            backend.refresh.return_value = {"status": "fresh", "generation": "g"}
        return WorkplaceIndexMaintenanceService(
            self.workplace, backend_factory=lambda *_args: backend
        )

    def state(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(
            maintenance_state_path(self.workplace).read_text(encoding="utf-8")
        )
        return value

    def test_construction_is_cold(self) -> None:
        factory = Mock(side_effect=AssertionError("cold factory"))
        with patch(_CATALOGUE, side_effect=AssertionError("cold catalogue")):
            WorkplaceIndexMaintenanceService(self.workplace, backend_factory=factory)
            WorkplaceIndexMaintenanceCommand(maintenance_factory=factory)
        factory.assert_not_called()
        self.assertFalse(self.workplace.exists())

    def test_running_precedes_backend_and_complete_follows_report(self) -> None:
        backend = Mock()

        def tick(*, verify_files: bool) -> dict[str, Any]:
            self.assertFalse(verify_files)
            self.assertEqual(self.state()["status"], "running")
            return self.tick

        backend.maintenance_tick.side_effect = tick
        with patch(_CATALOGUE) as catalogue:
            catalogue.return_value.runtime_snapshot.return_value = {
                "search_index_scope": "workplace"
            }
            result = self.service(backend).run(verify_files=False)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["kind"], "pf.search_index.maintenance")
        self.assertEqual(result["scope"], "workplace")
        self.assertEqual(result["project_count"], 0)
        self.assertEqual(result["results"][0]["status"], "ok")
        self.assertEqual(self.state()["status"], "complete")
        report = self.workplace / result["report"]
        self.assertTrue(report.is_file())
        self.assertNotIn(str(self.workplace), report.read_text(encoding="utf-8"))
        history = list((report.parent / "maintenance-history").glob("*.json"))
        self.assertEqual(len(history), 2)

    def test_default_composition_reads_live_fixture_catalogue(self) -> None:
        self.workplace.mkdir()
        distribution = self.root / "distribution"
        distribution.mkdir()
        package = self.workplace / "packages/docs.fixture"
        source = package / "guide"
        source.mkdir(parents=True)
        (self.workplace / "registries").mkdir()
        (self.workplace / "workplace.yaml").write_text(
            "schema_version: 1\nid: fixture\n", encoding="utf-8"
        )
        registry = {
            "package_roots": [
                {"id": "local", "path": "packages", "status": "available"}
            ]
        }
        (self.workplace / "registries/package-roots.yaml").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        manifest = {
            "id": "docs.fixture",
            "resources": [
                {"id": "guide", "path": "guide", "indexing": {"mode": "fulltext"}}
            ],
        }
        (package / "package.yaml").write_text(json.dumps(manifest), encoding="utf-8")
        text = source / "guide.md"
        text.write_text("first marker", encoding="utf-8")
        service = WorkplaceIndexMaintenanceService(
            self.workplace, distribution_root=distribution
        )
        first = service.run()
        self.assertEqual(first["results"][0]["action"], "refresh")
        self.assertEqual(first["results"][0]["document_count"], 1)
        self.assertEqual(service.run()["results"][0]["action"], "none")
        text.write_text("other marker", encoding="utf-8")
        self.assertEqual(service.run()["results"][0]["action"], "refresh")
        second = package / "metadata"
        second.mkdir()
        manifest["resources"].append(
            {"id": "metadata", "path": "metadata", "indexing": {"mode": "metadata"}}
        )
        (package / "package.yaml").write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(service.run()["results"][0]["document_count"], 2)

    def test_backend_failure_is_safe_and_next_workplace_pass_retries(self) -> None:
        backend = Mock()
        backend.maintenance_tick.side_effect = OSError(str(self.root / "secret.md"))
        with patch(_CATALOGUE):
            failure = self.service(backend).run(reason=str(self.root))
            self.assertEqual(self.state()["status"], "failed")
            self.assertEqual(
                failure["results"][0]["error"], "search_maintenance_io_failed"
            )
            self.assertNotIn(str(self.root), json.dumps(failure))
            self.assertEqual(self.service().run()["results"][0]["status"], "ok")
        self.assertEqual(self.state()["status"], "complete")
        history = maintenance_state_path(self.workplace).parent / "maintenance-history"
        self.assertEqual(len(list(history.glob("*.json"))), 4)

    def test_failed_tick_is_not_complete_even_if_after_claims_fresh(self) -> None:
        for action in ("failed_refresh", "unknown_action"):
            self.tick["action"] = action
            with patch(_CATALOGUE):
                result = self.service().run()
            self.assertEqual(result["results"][0]["status"], "degraded")
            self.assertEqual(self.state()["status"], "failed")

    def test_partial_failure_count_is_not_complete(self) -> None:
        self.tick["after"]["failed_file_count"] = 1
        with patch(_CATALOGUE):
            self.assertEqual(self.service().run()["results"][0]["status"], "degraded")
        self.assertEqual(self.state()["status"], "failed")

    def test_untrusted_backend_diagnostics_do_not_disclose_paths(self) -> None:
        private = str(self.root / "private.md")
        self.tick["action"] = private
        self.tick["after"].update(
            {
                "error": private,
                "generation": private,
                "document_count": {"path": private},
            }
        )
        with patch(_CATALOGUE):
            result = self.service().run(reason=private)
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(self.state()))
        self.assertEqual(result["results"][0]["error"], "search_maintenance_failed")
        self.assertEqual(self.state()["status"], "failed")

    def test_atomic_replace_failure_retains_prior_state(self) -> None:
        from processforge_core.resources import index_maintenance

        path = self.root / "previous.json"
        path.write_text("previous bytes", encoding="utf-8")
        with patch.object(
            index_maintenance.os, "replace", side_effect=OSError("replace failed")
        ):
            with self.assertRaises(OSError):
                index_maintenance._atomic_write(path, "new bytes")
        self.assertEqual(path.read_text(encoding="utf-8"), "previous bytes")
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_same_process_competing_writer_cannot_enter(self) -> None:
        from processforge_core.resources import index_maintenance

        with index_maintenance._writer_lock(self.workplace):
            backend = Mock()
            with patch(_CATALOGUE) as catalogue:
                busy = self.service(backend).run()
            catalogue.assert_not_called()
            backend.maintenance_tick.assert_not_called()
        self.assertEqual(busy["results"][0]["error"], "search_maintenance_busy")
        self.assertFalse(maintenance_state_path(self.workplace).exists())

    def test_initial_durable_write_failure_prevents_backend(self) -> None:
        backend = Mock()
        with patch(_ATOMIC_WRITE, side_effect=OSError("private write location")):
            result = self.service(backend).run()
        self.assertEqual(
            result["results"][0]["error"], "search_maintenance_state_write_failed"
        )
        backend.maintenance_tick.assert_not_called()
        self.assertIsNone(result["report"])

    def test_report_write_failure_prevents_complete(self) -> None:
        from processforge_core.resources import index_maintenance

        original = index_maintenance._atomic_write

        def write(path: Path, text: str) -> None:
            if path.name == "latest-maintenance.yaml":
                raise OSError("required report unavailable")
            original(path, text)

        with patch(_CATALOGUE), patch(_ATOMIC_WRITE, side_effect=write):
            result = self.service().run()
        self.assertEqual(
            result["results"][0]["error"], "search_maintenance_report_write_failed"
        )
        self.assertEqual(self.state()["status"], "failed")

    def test_final_state_failure_retains_incomplete_running(self) -> None:
        from processforge_core.resources import index_maintenance

        original = index_maintenance._atomic_write

        def write(path: Path, text: str) -> None:
            if (
                path.name == "maintenance-state.json"
                and json.loads(text)["status"] == "complete"
            ):
                raise OSError("terminal state unavailable")
            original(path, text)

        with patch(_CATALOGUE), patch(_ATOMIC_WRITE, side_effect=write):
            result = self.service().run()
        self.assertEqual(
            result["results"][0]["error"], "search_maintenance_state_write_failed"
        )
        self.assertEqual(self.state()["status"], "running")

    def test_scoped_success_cannot_clear_incomplete_workplace(self) -> None:
        path = maintenance_state_path(self.workplace)
        path.parent.mkdir(parents=True)
        for previous in ("failed", "running"):
            path.write_text(json.dumps({"status": previous}), encoding="utf-8")
            result = self.service().run_scoped(
                self.root, self.snapshot, operation="refresh"
            )
            self.assertEqual(result["status"], "fresh")
            self.assertEqual(self.state()["status"], "failed")
            self.assertEqual(self.state()["error"], "search_maintenance_incomplete")

    def test_scoped_backend_exception_keeps_identity_and_durable_failure(self) -> None:
        backend = Mock()
        failure = LocalSearchError("fixture_error")
        backend.refresh.side_effect = failure
        with self.assertRaises(LocalSearchError) as raised:
            self.service(backend).run_scoped(
                self.root, self.snapshot, operation="refresh"
            )
        self.assertIs(raised.exception, failure)
        self.assertEqual(self.state()["status"], "failed")

    def test_cross_process_lock_is_bounded_and_crash_releasing(self) -> None:
        script = """
import sys, time
from pathlib import Path
from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)
assert "processforge" not in sys.modules
assert "pf_runtime.service" not in sys.modules
root = Path(sys.argv[1])
class Backend:
    def refresh(self):
        (root / "entered").write_text("ready")
        while True:
            time.sleep(0.05)
service = WorkplaceIndexMaintenanceService(
    root, backend_factory=lambda *args: Backend()
)
service.run_scoped(root, {"snapshot": {"checksum": "child"}}, operation="refresh")
"""
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", script, str(self.workplace)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 15
            while not (self.workplace / "entered").exists():
                if process.poll() is not None:
                    self.fail(
                        process.communicate()[1].decode("utf-8", errors="replace")
                    )
                if time.monotonic() >= deadline:
                    self.fail("child did not enter maintenance")
                time.sleep(0.02)
            before = maintenance_state_path(self.workplace).read_bytes()
            started = time.monotonic()
            with self.assertRaises(IndexMaintenanceError) as raised:
                self.service().run_scoped(self.root, self.snapshot, operation="refresh")
            self.assertEqual(raised.exception.code, "search_maintenance_busy")
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(
                maintenance_state_path(self.workplace).read_bytes(), before
            )
            busy = self.service().run()
            self.assertEqual(busy["results"][0]["error"], "search_maintenance_busy")
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=15)
        self.assertEqual(self.state()["status"], "running")
        with patch(_CATALOGUE):
            recovered = self.service().run()
        self.assertEqual(recovered["results"][0]["status"], "ok")
        self.assertEqual(self.state()["status"], "complete")
        history = maintenance_state_path(self.workplace).parent / "maintenance-history"
        self.assertTrue(
            any(
                json.loads(path.read_text())["status"] == "running"
                for path in history.glob("*.json")
            )
        )

    def test_cli_apply_refusal_has_no_factory_or_filesystem_effect(self) -> None:
        factory = Mock(side_effect=AssertionError("apply required"))
        command = WorkplaceIndexMaintenanceCommand(maintenance_factory=factory)
        output = io.StringIO()
        with redirect_stdout(output):
            code = command.execute(
                argparse.Namespace(
                    workplace=str(self.workplace), apply=False, json=True
                )
            )
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(output.getvalue())["results"][0]["error"],
            "search_maintenance_apply_required",
        )
        factory.assert_not_called()
        self.assertFalse(self.workplace.exists())

    def test_cli_registration_and_explicit_call_use_same_owner(self) -> None:
        service = self.service()
        command = WorkplaceIndexMaintenanceCommand(
            maintenance_factory=lambda root: service
        )
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        register_search_index_maintenance(
            subparsers.add_parser, execute=command.execute
        )
        args = parser.parse_args(
            [
                "search-index-maintain",
                "--workplace",
                str(self.workplace),
                "--apply",
                "--json",
            ]
        )
        with patch(_CATALOGUE), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(args.func(args), 0)
        self.assertEqual(json.loads(output.getvalue())["results"][0]["status"], "ok")
        self.assertEqual(self.state()["status"], "complete")
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["search-index-maintain", "--apply"])

    def test_cli_text_success_and_failure_keep_portable_diagnostics(self) -> None:
        for successful in (True, False):
            with self.subTest(successful=successful):
                row = {"scope": "workplace", "status": "ok" if successful else "error"}
                if successful:
                    row.update({"search_status": "fresh", "action": "refresh"})
                else:
                    row["error"] = "search_maintenance_busy"
                service = Mock()
                service.run.return_value = {
                    "results": [row],
                    "report": "runtime/search/latest-maintenance.yaml"
                    if successful
                    else None,
                }
                command = WorkplaceIndexMaintenanceCommand(
                    maintenance_factory=Mock(return_value=service)
                )
                with redirect_stdout(io.StringIO()) as output:
                    actual = command.execute(
                        argparse.Namespace(
                            workplace=str(self.workplace), apply=True, json=False
                        )
                    )
                self.assertEqual(actual, 0 if successful else 1)
                expected = (
                    "STATUS: ok\nSEARCH_INDEX: fresh\nACTION: refresh\n"
                    "REPORT: runtime/search/latest-maintenance.yaml\n"
                    if successful
                    else "STATUS: failed\nSEARCH_INDEX: unavailable\nERROR: search_maintenance_busy\n"
                )
                self.assertEqual(output.getvalue(), expected)
                self.assertNotIn(str(self.root), output.getvalue())
                service.run.assert_called_once_with(reason="manual")

    def test_cli_missing_target_refuses_before_constructing_owner(self) -> None:
        factory = Mock(side_effect=AssertionError("no target"))
        command = WorkplaceIndexMaintenanceCommand(maintenance_factory=factory)
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(argparse.Namespace(apply=True, json=True))
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(output.getvalue())["results"][0]["error"],
            "search_maintenance_workplace_required",
        )
        factory.assert_not_called()
        self.assertFalse(self.workplace.exists())

    def test_cli_factory_failure_never_exposes_private_exception_text(self) -> None:
        factory = Mock(side_effect=OSError(str(self.root / "private-secret")))
        command = WorkplaceIndexMaintenanceCommand(maintenance_factory=factory)
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(
                argparse.Namespace(workplace=str(self.workplace), apply=True, json=True)
            )
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(output.getvalue())["results"][0]["error"],
            "search_maintenance_failed",
        )
        self.assertNotIn("private-secret", output.getvalue())
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertFalse(self.workplace.exists())

    def test_legacy_cli_parameters_stdout_and_verification_are_retained(self) -> None:
        cases = (
            (
                SearchIndexRefreshCommand,
                "refresh",
                "REFRESHED: generation\nRESOURCES: 2\nDOCUMENTS: 3\n",
            ),
            (
                SearchIndexRebuildCommand,
                "rebuild",
                "REBUILT: generation\nRESOURCES: 2\nDOCUMENTS: 3\n",
            ),
            (
                SearchIndexTickCommand,
                "tick",
                "ACTION: none\nSTATUS: fresh\n"
                "GENERATION: fixture-generation\nDOCUMENTS: 7\n",
            ),
        )
        for command_type, operation, expected in cases:
            with self.subTest(operation=operation):
                backend = Mock()
                backend.refresh.return_value = {
                    "generation": "generation",
                    "resources": 2,
                    "indexed": 3,
                }
                backend.rebuild.return_value = backend.refresh.return_value
                backend.maintenance_tick.return_value = self.tick
                factory = Mock(return_value=backend)
                reader = Mock(return_value=({"status": "fresh"}, self.snapshot))
                command = command_type(index_factory=factory, snapshot_reader=reader)
                args = argparse.Namespace(
                    project_root=str(self.root),
                    workplace=str(self.workplace),
                    skip_file_verify=True,
                )
                with (
                    patch(_CATALOGUE, side_effect=AssertionError("scope widened")),
                    redirect_stdout(io.StringIO()) as output,
                ):
                    self.assertEqual(command.execute(args), 0)
                self.assertEqual(output.getvalue(), expected)
                factory.assert_called_once_with(
                    self.root.resolve(), self.snapshot, self.workplace.resolve()
                )
                if operation == "tick":
                    backend.maintenance_tick.assert_called_once_with(verify_files=False)
                self.assertEqual(self.state()["scope"], "project")

    def test_legacy_cli_stale_guard_precedes_factory_and_writer(self) -> None:
        for command_type in (
            SearchIndexRefreshCommand,
            SearchIndexRebuildCommand,
            SearchIndexTickCommand,
        ):
            factory = Mock(side_effect=AssertionError("freshness guard required"))
            command = command_type(
                index_factory=factory,
                snapshot_reader=lambda *_args: ({"status": "stale"}, self.snapshot),
            )
            args = argparse.Namespace(
                project_root=str(self.root), workplace=str(self.workplace)
            )
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(command.execute(args), 1)
            self.assertEqual(
                output.getvalue(), "FAIL: project context is not fresh: stale\n"
            )
            factory.assert_not_called()
            self.assertFalse(self.workplace.exists())

    def test_legacy_tick_failure_stdout_and_default_verify_are_retained(self) -> None:
        backend = Mock()
        backend.maintenance_tick.return_value = {
            "action": "failed_refresh",
            "after": {
                "status": "degraded",
                "document_count": 0,
                "error": "fts5_unavailable",
            },
        }
        command = SearchIndexTickCommand(
            index_factory=lambda *_args: backend,
            snapshot_reader=lambda *_args: ({"status": "fresh"}, self.snapshot),
        )
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(
                argparse.Namespace(
                    project_root=str(self.root), workplace=str(self.workplace)
                )
            )
        self.assertEqual(code, 1)
        backend.maintenance_tick.assert_called_once_with(verify_files=True)
        self.assertEqual(
            output.getvalue(),
            "ACTION: failed_refresh\nSTATUS: degraded\nGENERATION: none\n"
            "DOCUMENTS: 0\nERROR: fts5_unavailable\n",
        )
        self.assertEqual(self.state()["status"], "failed")

    def test_scoped_cli_busy_refusal_is_bounded_and_does_not_call_backend(self) -> None:
        from processforge_core.resources.index_maintenance import _writer_lock

        lock = _writer_lock(self.workplace)
        try:
            for command_type in (
                SearchIndexRefreshCommand,
                SearchIndexRebuildCommand,
                SearchIndexTickCommand,
            ):
                with self.subTest(command=command_type.__name__):
                    factory = Mock(side_effect=AssertionError("busy backend invoked"))
                    command = command_type(
                        index_factory=factory,
                        snapshot_reader=lambda *_args: (
                            {"status": "fresh"},
                            self.snapshot,
                        ),
                    )
                    args = argparse.Namespace(
                        project_root=str(self.root), workplace=str(self.workplace)
                    )
                    with redirect_stdout(io.StringIO()) as output:
                        self.assertEqual(command.execute(args), 1)
                    self.assertEqual(
                        output.getvalue(), "FAIL: search_maintenance_busy\n"
                    )
                    factory.assert_not_called()
                    self.assertFalse(maintenance_state_path(self.workplace).exists())
        finally:
            lock.close()

    def test_unknown_coordination_error_code_cannot_expose_raw_details(self) -> None:
        error = IndexMaintenanceError("secret-reason-with-content")
        self.assertEqual(error.code, "search_maintenance_failed")
        self.assertEqual(str(error), "search_maintenance_failed")
