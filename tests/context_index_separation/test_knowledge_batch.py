"""Verify batch ordering, native transaction recovery and the thin CLI contract.

All runtime fixtures stay in the batch contributor's owned scratch. Native tests
configure Main with a synthetic distribution before constructing its owners;
they do not initialize PF Work, Runtime, host integration or a real workplace.
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

from pf_cli.commands.knowledge_batch import KnowledgeBatchCommand
from pf_cli.parsers.knowledge_batch import register_knowledge_add_batch

from processforge_core.authoring.plans import AuthoringPlan, AuthoringWrite
from processforge_core.common.ids import safe_id
from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.common.yaml_io import load_yaml_document
from processforge_core.resources.knowledge_batch import (
    KnowledgeAddPlan,
    KnowledgeBatchService,
)
from processforge_core.resources.project_packages import PackageRootResolution

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_ROOT = (
    Path(os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir())
    / "context-index-knowledge-batch"
)
PACKAGE_ID = "docs.fixture"


def _batch(*records: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "resources": list(records)}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data) + "\n", encoding="utf-8")


class _OwnedFixture(unittest.TestCase):
    """Provide a contained, uniquely named fixture and exact cleanup boundary."""

    def setUp(self) -> None:
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = SCRATCH_ROOT / ("batch-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        target = self.root.resolve()
        if target.parent != SCRATCH_ROOT.resolve():
            raise AssertionError("batch fixture escaped owned scratch")
        shutil.rmtree(target)

    def tree(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }


class KnowledgeBatchTests(_OwnedFixture):
    """Exercise the callback contract and observable batch behavior."""

    def setUp(self) -> None:
        super().setUp()
        self.manifest = self.root / "package.json"
        self.manifest.write_text('{"resources": []}', encoding="utf-8")
        self.events: list[str] = []
        self.build = Mock(side_effect=self._build)
        self.preflight = Mock(side_effect=self._preflight)
        self.execute = Mock(side_effect=self._execute)
        self.index = Mock(
            return_value={"status": "fresh", "workplace_reconciled": False}
        )

    def service(self) -> KnowledgeBatchService:
        return KnowledgeBatchService(
            build_plan=self.build,
            preflight_plan=self.preflight,
            execute_plan=self.execute,
            index_resources=self.index,
        )

    def run_batch(self, envelope: object, **modes: bool) -> dict[str, Any]:
        return self.service().run(envelope, package_id=PACKAGE_ID, **modes)

    def _build(self, record: dict[str, Any]) -> KnowledgeAddPlan:
        resource_id = safe_id(
            str(record.get("id") or record.get("title") or "resource")
        )
        self.events.append("build:" + resource_id)
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        existing = [row for row in manifest["resources"] if row["id"] != resource_id]
        resource = {**record, "id": resource_id}
        result = "updated" if len(existing) != len(manifest["resources"]) else "added"
        manifest["resources"] = [*existing, resource]
        plan = AuthoringPlan(
            transaction_id=resource_id,
            command="knowledge-add-batch",
            runtime_root=self.root / "runtime",
            authoritative_writes=[
                AuthoringWrite(self.manifest, json.dumps(manifest).encode("utf-8"))
            ],
            registry_writes=[],
            post_commit_effects=[],
            validation_callbacks=[],
        )
        root = PackageRootResolution("fixture", "packages", self.root, "available", [])
        return plan, resource, result, self.manifest, self.root / "index.yaml", root

    def _preflight(self, plan: AuthoringPlan) -> None:
        self.events.append("preflight:" + plan.transaction_id)

    def _execute(self, plan: AuthoringPlan) -> dict[str, Any]:
        self.events.append("execute:" + plan.transaction_id)
        for write in plan.authoritative_writes:
            assert write.content is not None
            write.destination.write_bytes(write.content)
        return {"state": "committed_audit_complete"}

    def test_constructors_are_cold(self) -> None:
        self.service()
        factory = Mock(side_effect=AssertionError("cold factory"))
        loader = Mock(side_effect=AssertionError("cold loader"))
        KnowledgeBatchCommand(service_factory=factory, load_batch=loader)
        for callback in (
            self.build,
            self.preflight,
            self.execute,
            self.index,
            factory,
            loader,
        ):
            callback.assert_not_called()

    def test_default_and_explicit_dry_run_have_no_effects(self) -> None:
        before = self.tree()
        for modes in ({}, {"dry_run": True}):
            with self.subTest(modes=modes):
                report = self.run_batch(_batch({"id": "one"}, {"id": "two"}), **modes)
                self.assertEqual(report["status"], "planned")
                self.assertEqual(
                    [row["status"] for row in report["results"]], ["planned"] * 2
                )
                self.assertEqual(report["successful_resource_ids"], [])
                self.assertEqual(report["indexing"]["reason"], "dry_run")
                self.assertEqual(self.tree(), before)
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_core_refuses_mode_conflict_before_callbacks(self) -> None:
        before = self.tree()
        report = self.run_batch(_batch({"id": "one"}), apply=True, dry_run=True)
        self.assertEqual(report["error"], "knowledge_batch_mode_conflict")
        self.assertEqual(report["results"], [])
        self.assertEqual(self.tree(), before)
        for callback in (self.build, self.preflight, self.execute, self.index):
            callback.assert_not_called()

    def test_envelope_refusals_precede_every_callback(self) -> None:
        invalid: list[object] = [
            None,
            [],
            {},
            {"schema_version": 1},
            {"schema_version": True, "resources": [{"id": "one"}]},
            {"schema_version": 1.0, "resources": [{"id": "one"}]},
            {"schema_version": 2, "resources": [{"id": "one"}]},
            _batch(),
            {"schema_version": 1, "resources": {}},
            {"schema_version": 1, "resources": [{"id": "one"}, None]},
            {"schema_version": 1, "resources": ["invalid"]},
            {**_batch({"id": "one"}), "unexpected": True},
            {"__yaml_error__": str(self.root / "private")},
        ]
        before = self.tree()
        for envelope in invalid:
            with self.subTest(envelope=envelope):
                report = self.run_batch(envelope, apply=True)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["results"], [])
                self.assertEqual(self.tree(), before)
        for callback in (self.build, self.preflight, self.execute, self.index):
            callback.assert_not_called()

    def test_duplicate_explicit_normalized_ids_fail_before_writes(self) -> None:
        for records in (
            ({"id": "one"}, {"id": "one"}),
            ({"id": "Guide_A"}, {"id": "guide-a"}),
        ):
            report = self.run_batch(_batch(*records), apply=True)
            self.assertEqual(report["error"], "knowledge_batch_duplicate_id")
        self.build.assert_not_called()
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_apply_prepares_against_latest_manifest_and_indexes_once_last(self) -> None:
        def index(ids: list[str]) -> dict[str, Any]:
            self.events.append("index")
            self.assertEqual(len(json.loads(self.manifest.read_text())["resources"]), 2)
            return {"status": "fresh"}

        self.index.side_effect = index
        report = self.run_batch(_batch({"id": "one"}, {"id": "two"}), apply=True)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(
            self.events,
            [
                "build:one",
                "preflight:one",
                "execute:one",
                "build:two",
                "preflight:two",
                "execute:two",
                "index",
            ],
        )
        self.index.assert_called_once_with(["docs.fixture:one", "docs.fixture:two"])
        self.assertFalse(report["indexing"]["workplace_reconciled"])

    def test_mixed_validation_commit_failures_keep_order_and_successes(self) -> None:
        def build(record: dict[str, Any]) -> KnowledgeAddPlan:
            if record["id"] == "invalid":
                raise SystemExit("FAIL: " + str(self.root / "private"))
            return self._build(record)

        def execute(plan: AuthoringPlan) -> dict[str, Any]:
            if plan.transaction_id == "broken":
                raise OSError(str(self.root / "private"))
            return self._execute(plan)

        self.build.side_effect = build
        self.execute.side_effect = execute
        report = self.run_batch(
            _batch(*({"id": name} for name in ("one", "invalid", "broken", "two"))),
            apply=True,
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual([row["index"] for row in report["results"]], [1, 2, 3, 4])
        self.assertEqual(
            [row["status"] for row in report["results"]],
            ["ok", "error", "error", "ok"],
        )
        self.assertEqual(report["results"][2]["authoring_state"], "unconfirmed")
        self.assertNotIn(str(self.root), json.dumps(report))
        self.index.assert_called_once_with(["docs.fixture:one", "docs.fixture:two"])

    def test_preflight_error_continues_without_executing_failed_row(self) -> None:
        def preflight(plan: AuthoringPlan) -> None:
            if plan.transaction_id == "broken":
                raise OSError(str(self.root / "private"))
            self._preflight(plan)

        self.preflight.side_effect = preflight
        report = self.run_batch(_batch({"id": "broken"}, {"id": "good"}), apply=True)
        self.assertEqual([row["status"] for row in report["results"]], ["error", "ok"])
        self.assertEqual(report["results"][0]["phase"], "preflight")
        self.assertEqual(self.execute.call_count, 1)
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual([row["id"] for row in manifest["resources"]], ["good"])
        self.assertNotIn(str(self.root), json.dumps(report))
        self.index.assert_called_once_with(["docs.fixture:good"])

    def test_all_failed_items_do_not_index(self) -> None:
        self.preflight.side_effect = SystemExit("FAIL: validation refused")
        report = self.run_batch(_batch({"id": "one"}, {"id": "two"}), apply=True)
        self.assertEqual([row["phase"] for row in report["results"]], ["preflight"] * 2)
        self.assertEqual(report["indexing"]["reason"], "no_successful_resources")
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_derived_repeated_id_executes_both_rows_and_indexes_unique_id(self) -> None:
        report = self.run_batch(
            _batch({"title": "Guide"}, {"title": "Guide"}), apply=True
        )
        self.assertEqual([row["status"] for row in report["results"]], ["ok", "ok"])
        self.assertEqual(
            [row["result"] for row in report["results"]], ["added", "updated"]
        )
        self.assertEqual(self.execute.call_count, 2)
        self.index.assert_called_once_with(["docs.fixture:guide"])

    def test_reusing_service_does_not_reuse_previous_selection(self) -> None:
        service = self.service()
        first = service.run(_batch({"id": "one"}), package_id=PACKAGE_ID, apply=True)
        self.assertEqual(first["successful_resource_ids"], ["docs.fixture:one"])
        self.index.assert_called_once_with(["docs.fixture:one"])
        self.index.reset_mock()
        second = service.run(_batch({"id": "two"}), package_id=PACKAGE_ID)
        self.assertEqual(second["successful_resource_ids"], [])
        self.assertEqual(second["indexing"]["reason"], "dry_run")
        self.index.assert_not_called()
        third = service.run(_batch({"id": "two"}), package_id=PACKAGE_ID, apply=True)
        self.assertEqual(third["successful_resource_ids"], ["docs.fixture:two"])
        self.index.assert_called_once_with(["docs.fixture:two"])

    def test_final_index_error_does_not_erase_or_rollback_committed_rows(self) -> None:
        self.index.side_effect = RuntimeError(str(self.root / "private"))
        report = self.run_batch(_batch({"id": "one"}, {"id": "two"}), apply=True)
        self.assertEqual(report["status"], "failed")
        self.assertEqual([row["status"] for row in report["results"]], ["ok", "ok"])
        self.assertEqual(report["indexing"]["error"], "knowledge_batch_indexing_failed")
        self.assertEqual(len(json.loads(self.manifest.read_text())["resources"]), 2)
        self.assertNotIn(str(self.root), json.dumps(report))
        self.index.assert_called_once()

    def test_failed_or_malformed_index_return_is_separate_failure(self) -> None:
        for result in (
            {},
            None,
            {"status": "degraded"},
            {"status": "fresh", "failed_file_count": 1},
            {"status": "fresh", "error": str(self.root)},
        ):
            with self.subTest(result=result):
                self.index.return_value = result
                report = self.run_batch(_batch({"id": "one"}), apply=True)
                self.assertEqual(report["results"][0]["status"], "ok")
                self.assertEqual(report["indexing"]["status"], "error")
                self.assertEqual(report["status"], "failed")
                self.assertNotIn(str(self.root), json.dumps(report))

    def test_index_report_drops_private_fields_and_preserves_selection(self) -> None:
        def index(ids: list[str]) -> dict[str, Any]:
            ids.clear()
            return {
                "status": "fresh",
                "private_path": str(self.root),
                "workplace_reconciled": True,
            }

        self.index.side_effect = index
        report = self.run_batch(_batch({"id": "one"}), apply=True)
        self.assertEqual(report["successful_resource_ids"], ["docs.fixture:one"])
        self.assertEqual(report["indexing"]["resource_ids"], ["docs.fixture:one"])
        self.assertFalse(report["indexing"]["workplace_reconciled"])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_incomplete_or_malformed_journal_is_a_failed_item(self) -> None:
        self.execute.side_effect = None
        journal: object
        for journal in (
            None,
            [],
            {},
            {"state": "committed"},
            {"state": "committed_audit_pending"},
            {"state": "rolled_back"},
        ):
            with self.subTest(journal=journal):
                self.execute.return_value = journal
                report = self.run_batch(_batch({"id": "one"}), apply=True)
                self.assertEqual(
                    report["results"][0]["error"],
                    "knowledge_batch_authoring_incomplete",
                )
                self.assertEqual(report["successful_resource_ids"], [])
        self.index.assert_not_called()

    def test_cancellation_propagates_at_all_execution_boundaries(self) -> None:
        for callback in (self.build, self.preflight, self.execute, self.index):
            original = callback.side_effect
            for error in (KeyboardInterrupt(), SystemExit(17), SystemExit("cancelled")):
                with self.subTest(callback=callback, error=error):
                    callback.side_effect = error
                    with self.assertRaises(type(error)):
                        self.run_batch(_batch({"id": "one"}), apply=True)
            callback.side_effect = original
        self.execute.side_effect = SystemExit(
            "FAIL: cancellation after entering executor"
        )
        with self.assertRaises(SystemExit):
            self.run_batch(_batch({"id": "one"}), apply=True)

    def test_missing_package_is_never_created(self) -> None:
        prepared = self._build({"id": "one"})
        missing = self.root / "missing-package.yaml"
        self.build.side_effect = None
        self.build.return_value = (*prepared[:3], missing, *prepared[4:])
        report = self.run_batch(_batch({"id": "one"}), apply=True)
        self.assertEqual(
            report["results"][0]["error"], "knowledge_batch_package_missing"
        )
        self.assertFalse(missing.exists())
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_callback_mutation_does_not_change_inline_input(self) -> None:
        envelope = _batch(
            {
                "id": "one",
                "source": {"type": "url", "url": "https://example.invalid/guide"},
            }
        )
        before = copy.deepcopy(envelope)

        def build(record: dict[str, Any]) -> KnowledgeAddPlan:
            record["source"]["url"] = "https://example.invalid/changed"
            return self._build(record)

        self.build.side_effect = build
        self.run_batch(envelope, dry_run=True)
        self.assertEqual(envelope, before)

    def args(self, **overrides: Any) -> argparse.Namespace:
        values = {
            "workplace": str(self.root),
            "package": PACKAGE_ID,
            "batch_file": str(self.root / "batch.yaml"),
            "package_root": None,
            "apply": False,
            "dry_run": False,
            "json": True,
        }
        return argparse.Namespace(**{**values, **overrides})

    def test_cli_emits_one_json_document_despite_native_output(self) -> None:
        def execute(plan: AuthoringPlan) -> dict[str, Any]:
            print("PROPOSAL: " + str(self.root / "private"))
            print("legacy detail", file=sys.stderr)
            return self._execute(plan)

        self.execute.side_effect = execute
        factory = Mock(return_value=self.service())
        command = KnowledgeBatchCommand(
            service_factory=factory, load_batch=lambda path: _batch({"id": "one"})
        )
        stdout, stderr = io.StringIO(), io.StringIO()
        args = self.args(apply=True)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = command.execute(args)
        self.assertEqual(code, 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["status"], "ok")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(str(self.root), stdout.getvalue())
        factory.assert_called_once_with(args)

    def test_cli_default_is_read_only_and_reads_yaml_url_record(self) -> None:
        args = self.args()
        _write_yaml(
            Path(args.batch_file),
            _batch(
                {
                    "id": "web",
                    "source": {"type": "url", "url": "https://example.invalid/guide"},
                }
            ),
        )
        before = self.tree()
        command = KnowledgeBatchCommand(service_factory=lambda args: self.service())
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(args)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "planned")
        self.assertEqual(self.tree(), before)
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_cli_refuses_conflicting_modes_before_loading_or_factory(self) -> None:
        factory, loader = Mock(), Mock()
        command = KnowledgeBatchCommand(service_factory=factory, load_batch=loader)
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(self.args(apply=True, dry_run=True))
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(output.getvalue())["error"], "knowledge_batch_mode_conflict"
        )
        factory.assert_not_called()
        loader.assert_not_called()

    def test_cli_unreadable_file_does_not_construct_service(self) -> None:
        factory = Mock()
        loader = Mock(side_effect=OSError(str(self.root / "private")))
        command = KnowledgeBatchCommand(service_factory=factory, load_batch=loader)
        with redirect_stdout(io.StringIO()) as output:
            code = command.execute(self.args())
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(output.getvalue())["error"], "knowledge_batch_file_unreadable"
        )
        self.assertNotIn(str(self.root), output.getvalue())
        factory.assert_not_called()

    def test_cli_nonzero_for_mixed_failure_and_for_final_index_failure(self) -> None:
        def execute(plan: AuthoringPlan) -> dict[str, Any]:
            if plan.transaction_id == "one":
                raise RuntimeError("item")
            return self._execute(plan)

        command = KnowledgeBatchCommand(
            service_factory=lambda args: self.service(),
            load_batch=lambda path: _batch({"id": "one"}, {"id": "two"}),
        )
        for failure in ("item", "index"):
            with self.subTest(failure=failure):
                self.execute.side_effect = (
                    execute if failure == "item" else self._execute
                )
                self.index.reset_mock()
                self.index.side_effect = (
                    RuntimeError("index") if failure == "index" else None
                )
                with redirect_stdout(io.StringIO()) as output:
                    code = command.execute(self.args(apply=True, json=False))
                self.assertEqual(code, 1)
                self.assertIn("STATUS: failed", output.getvalue())
                selected = (
                    ["docs.fixture:two"]
                    if failure == "item"
                    else ["docs.fixture:one", "docs.fixture:two"]
                )
                self.index.assert_called_once_with(selected)

    def test_cli_loader_and_factory_cancellation_propagates(self) -> None:
        for phase in ("load", "factory"):
            for error in (KeyboardInterrupt(), SystemExit(17)):
                with self.subTest(phase=phase, error=error):
                    factory = Mock(return_value=self.service())
                    loader = Mock(return_value=_batch({"id": "one"}))
                    callback = loader if phase == "load" else factory
                    callback.side_effect = error
                    command = KnowledgeBatchCommand(
                        service_factory=factory, load_batch=loader
                    )
                    output = io.StringIO()
                    with redirect_stdout(output), self.assertRaises(type(error)):
                        command.execute(self.args(apply=True))
                    self.assertEqual(output.getvalue(), "")
        self.execute.assert_not_called()
        self.index.assert_not_called()

    def test_parser_has_required_targets_and_optional_read_only_default(self) -> None:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        execute = Mock()
        register_knowledge_add_batch(subparsers.add_parser, execute=execute)
        base = [
            "knowledge-add-batch",
            "--workplace",
            "fixture",
            "--package",
            PACKAGE_ID,
            "--batch-file",
            "batch.yaml",
        ]
        args = parser.parse_args(base)
        self.assertFalse(args.apply)
        self.assertFalse(args.dry_run)
        self.assertIs(args.func, execute)
        applied = parser.parse_args(
            [*base, "--apply", "--json", "--package-root", "local"]
        )
        self.assertTrue(applied.apply)
        self.assertEqual(applied.package_root, "local")
        for argv in ([*base, "--apply", "--dry-run"], base[:-2], [*base, "--appl"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(argv)
        execute.assert_not_called()


class NativeKnowledgeBatchTests(_OwnedFixture):
    """Use actual native builder/preflight/transactions/audit with fixture data."""

    def setUp(self) -> None:
        super().setUp()
        self.distribution = self.root / "distribution"
        self.workplace = self.root / "workplace"
        self.manifest = self.workplace / "packages" / PACKAGE_ID / "package.yaml"
        _write_yaml(
            self.workplace / "workplace.yaml", {"schema_version": 1, "id": "fixture"}
        )
        _write_yaml(
            self.workplace / "registries/package-roots.yaml",
            {
                "package_roots": [
                    {
                        "id": "local",
                        "path": "packages",
                        "status": "available",
                        "default": True,
                    }
                ]
            },
        )
        _write_yaml(
            self.manifest,
            {
                "schema_version": 1,
                "id": PACKAGE_ID,
                "version": "1.0.0",
                "resources": [],
            },
        )
        # These synthetic schemas isolate transaction behavior from release
        # schema coverage, which remains part of the primary's registered QA.
        schemas = self.distribution / "schemas"
        schemas.mkdir(parents=True)
        for name in (
            "package-manifest",
            "knowledge-resource-index",
            "private-resource-paths-registry",
        ):
            (schemas / f"{name}.schema.json").write_text(
                '{"type": "object"}', encoding="utf-8"
            )
        self.main = self._main()
        self.index = Mock(
            return_value={"status": "fresh", "workplace_reconciled": False}
        )

    def _main(self) -> ModuleType:
        source_path = PROJECT_ROOT / "tools/processforge.py"
        source = source_path.read_text(encoding="utf-8")
        seam = "ROOT = _bootstrap_repo_src()"
        if source.count(seam) != 1:
            raise AssertionError("Main fixture distribution seam changed")
        module = ModuleType("pf_batch_fixture_" + uuid.uuid4().hex)
        module.__file__ = str(source_path)
        module.__dict__["FIXTURE_DISTRIBUTION_ROOT"] = self.distribution
        sys.modules[module.__name__] = module
        self.addCleanup(sys.modules.pop, module.__name__, None)
        code = compile(
            source.replace(seam, "ROOT = FIXTURE_DISTRIBUTION_ROOT"),
            str(source_path),
            "exec",
        )
        exec(code, module.__dict__)
        return module

    def service(self) -> KnowledgeBatchService:
        args = argparse.Namespace(
            workplace=str(self.workplace), package=PACKAGE_ID, package_root="local"
        )
        return KnowledgeBatchService(
            build_plan=lambda record: self.main.build_knowledge_resource_add_plan(
                args, "knowledge-add-batch", record
            ),
            preflight_plan=self.main.preflight_authoring_plan,
            execute_plan=self.main.execute_authoring_plan,
            index_resources=self.index,
        )

    def run_batch(self, envelope: object, **modes: bool) -> dict[str, Any]:
        with redirect_stdout(io.StringIO()):
            return self.service().run(envelope, package_id=PACKAGE_ID, **modes)

    def journals(self) -> list[Path]:
        return sorted(
            (self.workplace / "runtime/authoring-transactions").glob("*/journal.yaml")
        )

    def private_record(self, resource_id: str) -> dict[str, Any]:
        directory = self.root / "private-docs" / resource_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "guide.md").write_text("fixture body", encoding="utf-8")
        return {"id": resource_id, "kind": "documentation", "path": str(directory)}

    def test_native_transactions_keep_all_manifest_index_registry_updates(self) -> None:
        records = [
            self.private_record("one"),
            self.private_record("two"),
            {
                "id": "web",
                "source": {"type": "url", "url": "https://example.invalid/guide"},
            },
        ]
        with patch.object(
            self.main, "urlopen", side_effect=AssertionError("network forbidden")
        ):
            report = self.run_batch(_batch(*records), apply=True)
        self.assertEqual(report["status"], "ok", report)
        manifest = load_yaml_document(self.manifest)
        self.assertEqual(
            [row["id"] for row in manifest["resources"]], ["one", "two", "web"]
        )
        index_path = self.manifest.parent / "indexes/resource-index.yaml"
        self.assertEqual(len(load_yaml_document(index_path)["resources"]), 3)
        registry = load_yaml_document(
            self.workplace / "registries/private-resource-paths.yaml"
        )
        self.assertEqual(
            [row["id"] for row in registry["private_resource_paths"]], ["one", "two"]
        )
        self.assertEqual(len(self.journals()), 3)
        for path in self.journals():
            journal = load_yaml_document(path)
            self.assertEqual(journal["state"], "committed_audit_complete")
            self.assertTrue(journal["post_commit_completed"])
        self.index.assert_called_once_with(
            ["docs.fixture:one", "docs.fixture:two", "docs.fixture:web"]
        )
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_native_default_and_dry_run_do_not_create_runtime_or_registry(self) -> None:
        record = self.private_record("one")
        before = self.tree()
        for modes in ({}, {"dry_run": True}):
            report = self.run_batch(_batch(record), **modes)
            self.assertEqual(report["status"], "planned", report)
            self.assertEqual(self.tree(), before)
        self.assertFalse((self.workplace / "runtime").exists())
        self.index.assert_not_called()

    def test_native_commit_failure_rolls_back_and_next_item_can_complete(self) -> None:
        def fail(phase: str, plan: AuthoringPlan, write: AuthoringWrite | None) -> None:
            if "-broken-" in plan.transaction_id and phase == "after_entity_publish:1":
                raise RuntimeError("fixture publish failure")

        records = [self.private_record("broken"), self.private_record("good")]
        with patch.object(self.main, "AUTHORING_FAILURE_INJECTOR", fail):
            report = self.run_batch(_batch(*records), apply=True)
        self.assertEqual(
            [row["status"] for row in report["results"]], ["error", "ok"], report
        )
        manifest = load_yaml_document(self.manifest)
        self.assertEqual([row["id"] for row in manifest["resources"]], ["good"])
        states = [load_yaml_document(path)["state"] for path in self.journals()]
        self.assertCountEqual(states, ["rolled_back", "committed_audit_complete"])
        registry = load_yaml_document(
            self.workplace / "registries/private-resource-paths.yaml"
        )
        self.assertEqual(
            [row["id"] for row in registry["private_resource_paths"]], ["good"]
        )
        self.index.assert_called_once_with(["docs.fixture:good"])

    def test_native_post_commit_audit_failure_preserves_recovery(self) -> None:
        records = [self.private_record("one"), {"id": "two"}]
        with patch.object(
            self.main,
            "execute_authoring_effect",
            side_effect=OSError(str(self.root / "private-error")),
        ):
            report = self.run_batch(_batch(*records), apply=True)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            [row["status"] for row in report["results"]], ["error", "error"]
        )
        self.assertEqual(report["results"][0]["authoring_state"], "unconfirmed")
        self.assertEqual(report["results"][1]["phase"], "preflight")
        manifest = load_yaml_document(self.manifest)
        self.assertEqual([row["id"] for row in manifest["resources"]], ["one"])
        self.assertEqual(len(self.journals()), 1)
        journal_path = self.journals()[0]
        journal = load_yaml_document(journal_path)
        self.assertEqual(journal["state"], "committed_audit_pending")
        self.assertEqual(journal["post_commit_effects"][0]["state"], "failed")
        self.index.assert_not_called()
        self.assertNotIn(str(self.root), json.dumps(report))
        with redirect_stdout(io.StringIO()):
            state = self.main.recover_authoring_transaction(journal_path)
        self.assertEqual(state, "committed_audit_complete")
        self.index.assert_not_called()

    def test_native_audit_failure_indexes_only_completed_previous_item(self) -> None:
        def fail(phase: str, plan: AuthoringPlan, write: AuthoringWrite | None) -> None:
            if (
                "-broken-" in plan.transaction_id
                and phase == "after_commit_before_audit"
            ):
                raise OSError(str(self.root / "private"))

        records = [
            self.private_record("good"),
            self.private_record("broken"),
            {"id": "blocked"},
        ]
        with patch.object(self.main, "AUTHORING_FAILURE_INJECTOR", fail):
            report = self.run_batch(_batch(*records), apply=True)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(
            [row["status"] for row in report["results"]], ["ok", "error", "error"]
        )
        self.assertEqual(report["results"][2]["phase"], "preflight")
        manifest = load_yaml_document(self.manifest)
        self.assertEqual(
            [row["id"] for row in manifest["resources"]], ["good", "broken"]
        )
        states = [load_yaml_document(path)["state"] for path in self.journals()]
        self.assertCountEqual(states, ["committed_audit_complete", "committed"])
        self.assertEqual(report["successful_resource_ids"], ["docs.fixture:good"])
        self.index.assert_called_once_with(["docs.fixture:good"])

    def test_native_builder_cannot_create_an_absent_package(self) -> None:
        self.manifest.unlink()
        before = self.tree()
        report = self.run_batch(_batch({"id": "one"}), apply=True)
        self.assertEqual(
            report["results"][0]["error"], "knowledge_batch_package_missing"
        )
        self.assertEqual(self.tree(), before)
        self.assertFalse(self.manifest.exists())
        self.index.assert_not_called()
