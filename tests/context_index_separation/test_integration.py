"""Exercise project/index separation using owned registries and real SQLite.

Main is loaded with an empty fixture distribution as its configuration root.
Its command bodies, snapshot assembly and persistence are otherwise unchanged.
Agent entry, optional host integration and the broad project doctor are isolated
at their existing seams; no PF Work or infrastructure is started by these tests.
"""

from __future__ import annotations

import argparse
import ast
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from collections import Counter
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any, Literal
from unittest.mock import patch

from processforge_core import composition
from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.project.snapshot import load_snapshot
from processforge_core.resources import (
    index_maintenance,
    index_observation,
    local_search,
)
from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader
from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)
from processforge_core.resources.index_observation import maintenance_state_path
from processforge_core.resources.index_schedule import IndexMaintenanceJob
from processforge_core.resources.local_search import (
    LocalSearchError,
    ResourceSearchIndex,
)
from processforge_core.work.resource_material import MaterialBudget, capture_material
from processforge_core.work.resources import WorkResourceService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_ROOT = (
    Path(os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir())
    / "context-index-integration"
)
CHARACTERIZATION: list[dict[str, Any]] = []


def _write_yaml(path: Path, document: dict[str, Any]) -> None:
    """Write a fixture document without requiring a test-side YAML dependency."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(document) + "\n", encoding="utf-8")


def _fixture_main(distribution: Path) -> ModuleType:
    """Load real Main with a fixture distribution before constructing its owners."""
    source_path = PROJECT_ROOT / "tools/processforge.py"
    source = source_path.read_text(encoding="utf-8")
    bootstrap = "ROOT = _bootstrap_repo_src()"
    if source.count(bootstrap) != 1:
        raise AssertionError("Main distribution configuration seam changed")
    module = ModuleType("pf_index_integration_" + uuid.uuid4().hex)
    module.__file__ = str(source_path)
    module.__dict__["FIXTURE_DISTRIBUTION_ROOT"] = distribution
    sys.modules[module.__name__] = module
    try:
        exec(
            compile(
                source.replace(bootstrap, "ROOT = FIXTURE_DISTRIBUTION_ROOT"),
                str(source_path),
                "exec",
            ),
            module.__dict__,
        )
    except BaseException:
        sys.modules.pop(module.__name__, None)
        raise
    return module


class ContextIndexIntegrationTests(unittest.TestCase):
    """Verify real fixture behavior across Main and the shared Core owners."""

    def setUp(self) -> None:
        """Create a private, explicitly selected synthetic workplace."""
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = SCRATCH_ROOT / ("integration-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self._cleanup)
        self.distribution = self.root / "distribution"
        self.distribution.mkdir()
        self.workplace = self.root / "workplace"
        self.package = self.workplace / "packages/fixture"
        self.document_paths: set[Path] = set()
        self.selected_paths: set[Path] = set()
        self.resources: list[dict[str, Any]] = []
        for name, mode, body in (
            ("alpha", "fulltext", "sharedneedle alphaonly"),
            ("beta", "fulltext", "sharedneedle betaonly"),
            ("meta", "metadata", "privatebodytoken"),
        ):
            directory = self.package / name
            directory.mkdir(parents=True)
            path = directory / "guide.md"
            path.write_text(body, encoding="utf-8")
            self.document_paths.add(path)
            if name == "alpha":
                self.selected_paths.add(path)
            self.resources.append(
                {
                    "id": name,
                    "kind": "documentation",
                    "title": "NavigationGuide" if name == "meta" else name,
                    "path": name,
                    "indexing": {"mode": mode},
                }
            )
        self._write_package()
        _write_yaml(
            self.workplace / "workplace.yaml",
            {
                "schema_version": 1,
                "id": "index-integration-fixture",
                "paths": {"registries": "registries"},
                "registries": {
                    "package_roots": "registries/package-roots.yaml",
                    "distributions": "registries/distributions.yaml",
                },
            },
        )
        _write_yaml(
            self.workplace / "registries/package-roots.yaml",
            {
                "package_roots": [
                    {
                        "id": "global",
                        "path": str(self.workplace / "packages"),
                        "status": "available",
                        "default": True,
                    }
                ]
            },
        )
        _write_yaml(
            self.workplace / "registries/distributions.yaml",
            {
                "distributions": [
                    {
                        "id": "processforge",
                        "path": str(self.distribution),
                        "status": "available",
                    }
                ]
            },
        )
        self.main = _fixture_main(self.distribution)
        self.addCleanup(sys.modules.pop, self.main.__name__, None)
        self.project = self._project("project")

    def _cleanup(self) -> None:
        """Remove exactly this owned fixture after resolving its containment."""
        target = self.root.resolve()
        if target.parent != SCRATCH_ROOT.resolve():
            raise AssertionError("Fixture cleanup escaped owned scratch")
        shutil.rmtree(target)

    def _write_package(self) -> None:
        _write_yaml(
            self.package / "package.yaml",
            {
                "schema_version": 1,
                "id": "fixture",
                "version": "1.0.0",
                "resources": self.resources,
            },
        )

    def _project(self, name: str) -> Path:
        project = self.root / name
        _write_yaml(
            project / ".pf/process-forge.yaml",
            {
                "schema_version": 1,
                "project": {"id": name, "type": "generic"},
                "process_forge": {"mode": "file_only", "runner_required": False},
                "knowledge_stack": [{"id": "fixture", "source": "workplace"}],
                "context_requirements": {
                    "knowledge_resources": [{"id": "alpha", "required": True}]
                },
                "workplace": {"reference": "none"},
            },
        )
        _write_yaml(
            project / ".pf/process-forge.local.yaml",
            {"workplace": {"manifest": str(self.workplace / "workplace.yaml")}},
        )
        return project

    def _service(self) -> WorkplaceIndexMaintenanceService:
        return WorkplaceIndexMaintenanceService(
            self.workplace, distribution_root=self.distribution
        )

    def _snapshot(self, project: Path | None = None) -> dict[str, Any]:
        return load_snapshot(project or self.project)

    def _refresh(self, project: Path | None = None) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.main.command_project_context_refresh(
                argparse.Namespace(
                    project_root=str(project or self.project),
                    workplace=str(self.workplace),
                    dry_run=False,
                    reason="integration-fixture",
                )
            )
        return code, output.getvalue()

    def _search_tree(self) -> dict[str, tuple[int, bytes]]:
        folder = self.workplace / "runtime/search"
        return {
            path.relative_to(folder).as_posix(): (
                path.stat().st_mtime_ns,
                path.read_bytes(),
            )
            for path in folder.rglob("*")
            if path.is_file()
        }

    @contextmanager
    def _read_capture(self) -> Iterator[Counter[str]]:
        """Count content opens by purpose; reject reads outside this fixture."""
        counts: Counter[str] = Counter()
        real_open = Path.open

        def tracked(path: Path, *args: Any, **kwargs: Any) -> Any:
            mode = args[0] if args else kwargs.get("mode", "r")
            if "r" in mode:
                if not path.resolve().is_relative_to(self.root.resolve()):
                    raise AssertionError("Operation attempted a nonfixture file read")
                if path in self.document_paths:
                    category = (
                        "selected_document"
                        if path in self.selected_paths
                        else "other_document"
                    )
                elif path.is_relative_to(
                    self.workplace / "packages"
                ) or path.is_relative_to(self.workplace / "registries"):
                    category = "catalogue_metadata"
                else:
                    category = "project_and_runtime_metadata"
                counts[category] += 1
                if path.is_file():
                    counts[category + "_bytes"] += path.stat().st_size
            return real_open(path, *args, **kwargs)

        with patch.object(Path, "open", tracked):
            yield counts

    @contextmanager
    def _no_maintenance(self, *, allow_dirty: bool = False) -> Iterator[None]:
        """Reject hidden indexing, queuing, waiting and infrastructure launch."""
        with ExitStack() as stack:
            guards = []
            for name in (
                "build_index",
                "rebuild_index",
                "maintenance_tick",
                "mark_index_dirty",
                "_documents",
                "_iter_source_files",
                "_document_fingerprint_map",
            ):
                if name == "mark_index_dirty" and allow_dirty:
                    continue
                guards.append(
                    stack.enter_context(
                        patch.object(
                            local_search, name, side_effect=AssertionError(name)
                        )
                    )
                )
            for name in ("run", "run_scoped"):
                guards.append(
                    stack.enter_context(
                        patch.object(
                            WorkplaceIndexMaintenanceService,
                            name,
                            side_effect=AssertionError(name),
                        )
                    )
                )
            for target in (
                "time.sleep",
                "threading.Thread.start",
                "threading.Timer",
                "subprocess.Popen",
            ):
                guards.append(
                    stack.enter_context(
                        patch(target, side_effect=AssertionError(target))
                    )
                )
            server = stack.enter_context(
                patch(
                    "socket.create_connection",
                    side_effect=ConnectionRefusedError("fixture server unavailable"),
                )
            )
            yield
            server.assert_not_called()
            for guard in guards:
                guard.assert_not_called()

    @contextmanager
    def _catalogue_configuration(self) -> Iterator[None]:
        """Inject only distribution configuration while retaining the real reader."""

        def reader(root: Path, **_kwargs: Any) -> WorkplaceSearchCatalogReader:
            return WorkplaceSearchCatalogReader(
                root, distribution_root=self.distribution
            )

        with (
            patch.object(
                index_observation, "WorkplaceSearchCatalogReader", side_effect=reader
            ),
            patch.object(
                index_maintenance, "WorkplaceSearchCatalogReader", side_effect=reader
            ),
        ):
            yield

    def _lifecycle(self, operation: str) -> None:
        for state in ("missing", "stale", "building"):
            with self.subTest(state=state, operation=operation):
                project = self._project(operation + "-" + state)
                if state != "missing":
                    self.assertEqual(
                        self._service().run()["results"][0]["status"], "ok"
                    )
                    if state == "stale":
                        ResourceSearchIndex(
                            self.workplace, None, self.workplace
                        ).mark_dirty(reason="fixture-change")
                    else:
                        path = maintenance_state_path(self.workplace)
                        record = json.loads(path.read_text(encoding="utf-8"))
                        record["status"] = "running"
                        path.write_text(json.dumps(record), encoding="utf-8")
                before = self._search_tree()
                with (
                    self._no_maintenance(),
                    self._read_capture() as reads,
                    patch.object(
                        self.main,
                        "run_command_capture",
                        return_value=(0, "fixture doctor"),
                    ),
                    patch.object(
                        self.main, "finalize_project_onboarding_doctor_artifacts"
                    ),
                    patch.object(
                        self.main.project_initialization,
                        "apply_agent_entry",
                        return_value={"status": "complete", "agent_entry": {}},
                    ),
                    patch(
                        "processforge_core.project.host_integration."
                        "optional_host_integration_status",
                        return_value={"status": "unavailable"},
                    ),
                ):
                    for _attempt in range(2):
                        if operation == "refresh":
                            code, output = self._refresh(project)
                            self.assertEqual(code, 0)
                            self.assertIn("STATUS: fresh", output)
                            self.assertIn("action=none status=" + state, output)
                        else:
                            if operation == "init":
                                result = self.main.execute_project_initialization(
                                    {
                                        "project_root": project,
                                        "project_type": "generic",
                                        "workplace": str(self.workplace),
                                        "agent_entry_plan": {"files": []},
                                    },
                                    {},
                                )
                            else:
                                result = self.main.execute_project_repair(
                                    project,
                                    workplace=str(self.workplace),
                                    reason="fixture",
                                )
                            self.assertEqual(result["status"], "complete")
                            self.assertEqual(
                                result["search_index"]["results"][0]["search_status"],
                                state,
                            )
                        snapshot = self._snapshot(project)
                        self.assertEqual(
                            snapshot["resource_readiness"]["status"], "fresh"
                        )
                        self.assertEqual(
                            [row["id"] for row in snapshot["local_search_resources"]],
                            ["fixture:alpha"],
                        )
                self.assertEqual(reads["other_document"], 0)
                self.assertEqual(self._search_tree(), before)

    def test_first_repeat_refresh_without_server_or_index_side_effects(self) -> None:
        """Keep actual snapshot refresh independent of every index state."""
        self._lifecycle("refresh")

    def test_first_repeat_init_without_server_or_index_side_effects(self) -> None:
        """Keep the initializer's search boundary free of implicit maintenance."""
        self._lifecycle("init")

    def test_first_repeat_repair_without_server_or_index_side_effects(self) -> None:
        """Keep refresh-only repair independent of maintenance and App Server."""
        self._lifecycle("repair")

    def test_manual_cli_and_cold_job_use_the_same_real_owner(self) -> None:
        """Exercise actual parser wiring, durable state and default job composition."""
        calls: list[tuple[str, bool]] = []
        original = WorkplaceIndexMaintenanceService.run

        def run(
            service: WorkplaceIndexMaintenanceService,
            *,
            reason: str = "manual",
            verify_files: bool = True,
        ) -> dict[str, Any]:
            calls.append((reason, verify_files))
            return original(service, reason=reason, verify_files=verify_files)

        job = IndexMaintenanceJob(self.workplace, distribution_root=self.distribution)
        self.assertFalse((self.workplace / "runtime/search").exists())
        parser = self.main.build_parser()
        with (
            patch.object(WorkplaceIndexMaintenanceService, "run", run),
            self._catalogue_configuration(),
        ):
            refused = parser.parse_args(
                ["search-index-maintain", "--workplace", str(self.workplace), "--json"]
            )
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(refused.func(refused), 1)
            self.assertEqual(
                json.loads(output.getvalue())["results"][0]["error"],
                "search_maintenance_apply_required",
            )
            self.assertEqual(calls, [])
            self.assertFalse((self.workplace / "runtime/search").exists())
            args = parser.parse_args(
                [
                    "search-index-maintain",
                    "--workplace",
                    str(self.workplace),
                    "--apply",
                    "--json",
                ]
            )
            with self._read_capture(), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(args.func(args), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["kind"], "pf.search_index.maintenance")
            self.assertEqual(payload["project_count"], 0)
            self.assertEqual(calls, [("manual", True)])
            with self._read_capture():
                scheduled = job.execute()
            self.assertEqual(scheduled["results"][0]["action"], "none")
            self.assertEqual(calls, [("manual", True), ("scheduler", True)])
        record = json.loads(
            maintenance_state_path(self.workplace).read_text(encoding="utf-8")
        )
        self.assertEqual(
            (record["status"], record["reason"]), ("complete", "scheduler")
        )

    def test_legacy_cli_operations_keep_scope_and_call_one_component(self) -> None:
        """Use actual released CLI parameters and supplied snapshot filtering."""
        self.assertEqual(self._refresh()[0], 0)
        calls: list[tuple[str, list[str]]] = []
        original = WorkplaceIndexMaintenanceService.run_scoped

        def scoped(
            service: WorkplaceIndexMaintenanceService,
            project: Path,
            snapshot: dict[str, Any],
            *,
            operation: Literal["refresh", "rebuild", "tick"],
            verify_files: bool = True,
        ) -> dict[str, Any]:
            calls.append(
                (operation, [row["id"] for row in snapshot["local_search_resources"]])
            )
            return original(
                service,
                project,
                snapshot,
                operation=operation,
                verify_files=verify_files,
            )

        parser = self.main.build_parser()
        with (
            patch.object(WorkplaceIndexMaintenanceService, "run_scoped", scoped),
            patch.object(
                WorkplaceIndexMaintenanceService,
                "run",
                side_effect=AssertionError("workplace scope widened"),
            ),
        ):
            for operation, marker in (
                ("refresh", "REFRESHED:"),
                ("rebuild", "REBUILT:"),
                ("tick", "ACTION: none"),
            ):
                args = parser.parse_args(
                    [
                        "search-index",
                        operation,
                        "--project-root",
                        str(self.project),
                        "--workplace",
                        str(self.workplace),
                    ]
                )
                with (
                    self._read_capture() as reads,
                    redirect_stdout(io.StringIO()) as output,
                ):
                    self.assertEqual(args.func(args), 0)
                self.assertIn(marker, output.getvalue())
                self.assertEqual(reads["other_document"], 0)
        self.assertEqual(
            calls,
            [(name, ["fixture:alpha"]) for name in ("refresh", "rebuild", "tick")],
        )

    def test_project_query_filters_counts_and_live_snapshot_revocation(self) -> None:
        """A shared physical corpus must not widen results, totals or navigation."""
        self.assertEqual(self._service().run()["results"][0]["status"], "ok")
        self.assertEqual(self._refresh()[0], 0)
        service = composition.build_resource_search_service(
            self.project, self.workplace, self.main
        )
        before = self._search_tree()
        with (
            self._catalogue_configuration(),
            self._no_maintenance(),
            self._read_capture() as reads,
        ):
            result = service.search(query="sharedneedle", limit=1)
            self.assertEqual(result["total"], 1)
            self.assertEqual(
                [row["resource_id"] for row in result["results"]], ["fixture:alpha"]
            )
            self.assertEqual(result["page"]["next_limitstart"], None)
            self.assertEqual(service.search(query="betaonly")["results"], [])
            snapshot = self._snapshot()
            snapshot["local_search_resources"] = []
            _write_yaml(
                self.project / ".pf/contexts/project-context.snapshot.yaml", snapshot
            )
            self.assertEqual(service.search(query="sharedneedle")["total"], 0)
            self.assertEqual(service.search(query="alphaonly")["results"], [])
        self.assertEqual(reads["other_document"], 0)
        self.assertEqual(self._search_tree(), before)

    def test_unavailable_index_preserves_query_and_pagination_errors(self) -> None:
        """Validate malformed inputs even while the workplace index is absent."""
        self.assertEqual(self._refresh()[0], 0)
        service = composition.build_resource_search_service(
            self.project, self.workplace, self.main
        )
        with self._catalogue_configuration(), self._no_maintenance():
            for arguments, expected in (
                ({"query": ""}, "invalid_query"),
                ({"query": None}, "invalid_query"),
                ({"query": "alpha", "limitstart": 1, "offset": 2}, "ambiguous_offset"),
            ):
                with (
                    self.subTest(arguments=arguments),
                    self.assertRaises(LocalSearchError) as caught,
                ):
                    service.search(**arguments)
                self.assertEqual(caught.exception.code, expected)
            result = service.search(query="alpha")
            self.assertEqual(result["search_status"], "missing")
            self.assertEqual(result["results"], [])
            self.assertIn("authorized workplace", result["search"]["remediation"])
        self.assertFalse((self.workplace / "runtime/search").exists())

    def test_required_platform_blocks_refresh_despite_ready_search(self) -> None:
        """A ready search index cannot compensate for a required context resource."""
        manifest_path = self.project / ".pf/process-forge.yaml"
        manifest = self.main.load_yaml_document(manifest_path)
        manifest["platform_contracts"] = [{"id": "platform.fixture-required"}]
        _write_yaml(manifest_path, manifest)
        for indexed in (False, True):
            with self.subTest(indexed=indexed):
                if indexed:
                    self.assertEqual(
                        self._service().run()["results"][0]["status"], "ok"
                    )
                before = self._search_tree()
                with self._no_maintenance(), self._read_capture():
                    code, _output = self._refresh()
                self.assertEqual(code, 1)
                self.assertEqual(
                    self._snapshot()["resource_readiness"]["status"], "blocked"
                )
                self.assertEqual(self._search_tree(), before)

    def test_runtime_does_not_register_the_future_job_or_a_search_timer(self) -> None:
        """Keep future periodic scheduling outside the delivered Runtime surface."""
        source = (PROJECT_ROOT / "tools/pf_runtime/service.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("IndexMaintenanceJob", names)
        self.assertNotIn("IndexMaintenanceSchedule", names)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("index_schedule", node.module or "")
        with (
            patch(
                "threading.Thread.start", side_effect=AssertionError("thread started")
            ),
            patch("threading.Timer", side_effect=AssertionError("timer created")),
            patch.object(
                WorkplaceIndexMaintenanceService,
                "run",
                side_effect=AssertionError("maintenance started"),
            ),
        ):
            IndexMaintenanceJob(self.workplace, distribution_root=self.distribution)
        self.assertFalse((self.workplace / "runtime/search").exists())

    def test_resource_mutations_defer_maintenance_and_only_mark_existing_state(
        self,
    ) -> None:
        """Keep the characterized R4 triggers on the explicit dirty boundary."""
        source = (PROJECT_ROOT / "tools/processforge.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        deferred = {
            keyword.value.value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "defer_search_index_maintenance"
            for keyword in call.keywords
            if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant)
        }
        self.assertTrue(
            {
                "workplace-init",
                "update-apply",
                "update-rollback",
                "knowledge-add-url",
                "knowledge-add-resource",
                "knowledge-index-refresh",
                "template-create",
                "tool-register",
                "mcp-register",
                "platform-create",
                "platform-contract-install",
            }.issubset(deferred)
        )
        self.assertEqual(self._service().run()["results"][0]["status"], "ok")
        catalogue = WorkplaceSearchCatalogReader(
            self.workplace, distribution_root=self.distribution
        ).runtime_snapshot()
        query = ResourceSearchIndex(self.workplace, catalogue, self.workplace)
        previous = query.status()
        with self._no_maintenance(allow_dirty=True), self._read_capture() as reads:
            result = self.main.defer_search_index_maintenance(
                self.workplace, reason="knowledge-add-resource"
            )
        self.assertEqual(result["results"][0]["search_status"], "stale")
        self.assertEqual(result["results"][0]["action"], "none")
        self.assertEqual(query.status()["document_count"], previous["document_count"])
        self.assertEqual(reads["selected_document"], 0)
        self.assertEqual(reads["other_document"], 0)

    def test_work_material_access_stays_live_without_a_workplace_index(self) -> None:
        """Exercise real material verification with an already validated Work seam."""
        self.assertEqual(self._refresh()[0], 0)
        row = self._snapshot()["local_search_resources"][0]
        reference = row["path_ref"]
        binding, _documents = capture_material(
            row,
            self.package / "alpha",
            reference,
            include_content=False,
            budget=MaterialBudget(),
        )
        identity = {
            "project_id": "project",
            "run_id": "fixture-run",
            "assignment_id": "fixture-assignment",
            "context_id": "fixture-context",
            "snapshot_id": "fixture-snapshot",
        }
        grants = {"pinned": [row["id"]], "stage": [row["id"]]}
        service = WorkResourceService(self.project, self.workplace, self.main)
        arguments = {
            "run_id": "fixture-run",
            "assignment_id": "fixture-assignment",
            "context_id": "fixture-context",
        }
        with (
            patch.object(
                service, "_context", return_value=(identity, [binding], grants)
            ),
            self._no_maintenance(),
        ):
            result = service.read(operation="search", query="alphaonly", **arguments)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["total"], 1)
            denied = service.read(
                operation="resolve", resource_id="fixture:beta", **arguments
            )
            self.assertEqual(denied["reason"], "resource_not_in_work")
            grants["stage"] = []
            denied = service.read(
                operation="resolve", resource_id=row["id"], **arguments
            )
            self.assertEqual(denied["reason"], "resource_not_in_stage")
            grants["stage"] = [row["id"]]
            invalid = service.read(operation="search", query="", **arguments)
            self.assertEqual(invalid["reason"], "invalid_query")
            snapshot = self._snapshot()
            snapshot["local_search_resources"] = []
            _write_yaml(
                self.project / ".pf/contexts/project-context.snapshot.yaml", snapshot
            )
            with self._read_capture() as reads:
                revoked = service.read(
                    operation="search", query="alphaonly", **arguments
                )
            self.assertEqual(
                (revoked["status"], revoked["reason"]),
                ("blocked", "resource_access_revoked"),
            )
            self.assertEqual(reads["selected_document"], 0)
            self.assertEqual(reads["other_document"], 0)
        self.assertFalse((self.workplace / "runtime/search").exists())

    def test_work_generation_and_same_stat_material_errors_remain_strict(self) -> None:
        """Verify current metadata and file bytes before serving pinned material."""
        self.assertEqual(self._refresh()[0], 0)
        snapshot = self._snapshot()
        row = snapshot["local_search_resources"][0]
        binding, _documents = capture_material(
            row,
            self.package / "alpha",
            row["path_ref"],
            include_content=False,
            budget=MaterialBudget(),
        )
        identity = {
            "project_id": "project",
            "run_id": "fixture-run",
            "assignment_id": "fixture-assignment",
            "context_id": "fixture-context",
            "snapshot_id": "fixture-snapshot",
        }
        service = WorkResourceService(self.project, self.workplace, self.main)
        arguments = {
            "operation": "search",
            "query": "alphaonly",
            "run_id": "fixture-run",
            "assignment_id": "fixture-assignment",
            "context_id": "fixture-context",
        }
        grants = {"pinned": [row["id"]], "stage": [row["id"]]}
        with (
            patch.object(
                service, "_context", return_value=(identity, [binding], grants)
            ),
            self._no_maintenance(),
        ):
            changed = copy.deepcopy(snapshot)
            changed["local_search_resources"][0]["title"] = "changed metadata"
            _write_yaml(
                self.project / ".pf/contexts/project-context.snapshot.yaml", changed
            )
            with self._read_capture() as reads:
                result = service.read(**arguments)
            self.assertEqual(result["reason"], "resource_generation_changed")
            self.assertEqual(reads["selected_document"], 0)
            _write_yaml(
                self.project / ".pf/contexts/project-context.snapshot.yaml", snapshot
            )
            path = self.package / "alpha/guide.md"
            previous = path.stat()
            path.write_text("sharedneedle otheronly", encoding="utf-8")
            os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
            self.assertEqual(path.stat().st_size, previous.st_size)
            result = service.read(**arguments)
            self.assertEqual(result["reason"], "resource_material_changed")
        self.assertFalse((self.workplace / "runtime/search").exists())

    def test_refresh_and_maintenance_read_counts_on_large_real_registry(self) -> None:
        """Characterize separate operations without a timing-based speed assertion."""
        resource_count, files_per_resource = 64, 24
        for number in range(resource_count):
            name = f"bulk-{number:03d}"
            directory = self.package / name
            directory.mkdir()
            for index in range(files_per_resource):
                path = directory / f"document-{index:03d}.md"
                path.write_text(("corpusneedle " + name + " ") * 100, encoding="utf-8")
                self.document_paths.add(path)
            self.resources.append(
                {
                    "id": name,
                    "kind": "documentation",
                    "path": name,
                    "indexing": {"mode": "fulltext"},
                }
            )
        self._write_package()
        measurements = []
        for phase in (
            "first_refresh_missing_index",
            "explicit_initial_maintenance",
            "repeat_refresh_ready_index",
            "explicit_verified_noop_maintenance",
        ):
            with self._read_capture() as reads:
                started = time.perf_counter()
                if "refresh" in phase:
                    with self._no_maintenance():
                        code, _output = self._refresh()
                    self.assertEqual(code, 0)
                    self.assertEqual(reads["other_document"], 0)
                else:
                    result = self._service().run()
                    self.assertEqual(result["results"][0]["status"], "ok")
                    self.assertGreaterEqual(
                        reads["other_document"], resource_count * files_per_resource
                    )
                elapsed = time.perf_counter() - started
            measurements.append(
                {"phase": phase, "seconds": round(elapsed, 6), "reads": dict(reads)}
            )
        snapshot = self._snapshot()
        self.assertEqual(
            [row["id"] for row in snapshot["local_search_resources"]], ["fixture:alpha"]
        )
        # Content reads needed to validate selected Work material are a separate
        # operation. Blocking indexing must not disable that live verification.
        row = snapshot["local_search_resources"][0]
        with self._no_maintenance(), self._read_capture() as reads:
            started = time.perf_counter()
            capture_material(
                row,
                self.package / "alpha",
                row["path_ref"],
                include_content=False,
                budget=MaterialBudget(),
            )
            elapsed = time.perf_counter() - started
        self.assertEqual(reads["selected_document"], 1)
        self.assertEqual(reads["other_document"], 0)
        measurements.append(
            {
                "phase": "selected_work_material_validation",
                "seconds": round(elapsed, 6),
                "reads": dict(reads),
            }
        )
        CHARACTERIZATION.append(
            {
                "registered_resources": len(self.resources),
                "fulltext_files": len(self.document_paths) - 1,
                "source_bytes": sum(
                    path.stat().st_size for path in self.document_paths
                ),
                "measurement": (
                    "Attempted Path.open calls in read mode; byte totals are sizes "
                    "at open, not physical disk IO; instrumented wall time; real "
                    "Main with fixture distribution; no baseline comparison"
                ),
                "operations": measurements,
            }
        )


if __name__ == "__main__":
    unittest.main()
