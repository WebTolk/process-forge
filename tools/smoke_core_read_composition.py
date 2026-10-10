#!/usr/bin/env python3
"""Characterize the current-work reader and its explicit dependency composition."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.work.records import CurrentWorkService
from processforge_core.common import yaml_io


class FakeDocuments:
    def __init__(self):
        self.calls = []
        self.reader = YamlDocumentReader(yaml_io._parse_simple_yaml)

    def load(self, path: Path) -> dict:
        self.calls.append(path)
        return self.reader.load(path)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pf-read-composition-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.documents = FakeDocuments()
        self.service = CurrentWorkService(self.project, self.documents)

    def document(self, relative: str, data: object) -> Path:
        path = self.project / ".pf" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_document(self, run_id="r1", **extra):
        return self.document(f"runs/{run_id}/run.yaml", {"id": run_id, "status": "in_progress", **extra})


class CurrentWorkCharacterization(Fixture):
    def test_no_legacy_module_import(self):
        self.assertNotIn("processforge", sys.modules)
        self.assertNotIn("processforge_core._legacy_processforge", sys.modules)

    def test_missing_root(self):
        self.assertEqual(self.service.summary(), {"governed": False, "active_runs": [], "active_work": [], "recommendation": "start_work"})

    def test_live_sorted_runs(self):
        self.run_document("z")
        self.run_document("a")
        self.assertEqual([r["run_id"] for r in self.service.items()], ["a", "z"])

    def test_run_id_fallback(self):
        self.document("runs/directory-id/run.yaml", {"status": "in_progress"})
        self.assertEqual(self.service.items()[0]["run_id"], "directory-id")

    def test_missing_assignment_fallback(self):
        self.run_document(tasks=[{"id": "t1", "status": "open"}], objective="from run")
        row, = self.service.items()
        self.assertEqual((row["assignment_id"], row["objective"], row["status"]), ("t1", "from run", "open"))

    def test_assignment_wins_and_same_run_compacted(self):
        self.run_document(tasks=[{"id": "t1"}, {"id": "t2"}], objective="from run")
        for task in ("t1", "t2"):
            self.document(f"assignments/{task}.yaml", {"id": task, "status": "open", "objective": "from assignment"})
        summary = self.service.summary()
        self.assertEqual(len(summary["active_work"]), 2)
        self.assertEqual(len(summary["active_runs"]), 1)
        self.assertEqual(summary["active_work"][0]["objective"], "from assignment")

    def test_first_assignment_placeholder(self):
        self.document("assignments/first-assignment.yaml", {"id": "first-assignment", "status": "open", "objective": "bootstrap"})
        self.assertTrue(self.service.items()[0]["bootstrap_placeholder"])
        self.assertFalse(self.service.summary()["governed"])

    def test_objective_placeholder(self):
        self.run_document(tasks=[{"id": "t1"}], objective="Verify ProcessForge project onboarding checks")
        self.assertEqual(self.service.active_items(), [])

    def test_objective_matching_and_history(self):
        self.run_document("a", objective="Same  Objective")
        self.run_document("b", status="completed", objective="same objective")
        result = self.service.find_by_objective(" SAME\nOBJECTIVE ")
        self.assertEqual(result["active"]["run_id"], "a")
        self.assertEqual(result["historical"][0]["run_id"], "b")

    def test_non_mapping_task_ignored(self):
        self.run_document(tasks=[None, "bad", 123])
        self.assertEqual(self.service.items(), [])

    def test_invalid_yaml_preserves_read_behavior(self):
        path = self.run_document()
        path.write_text("key: [", encoding="utf-8")
        self.assertIn("__yaml_error__", self.documents.load(path))
        self.assertEqual(self.service.items()[0]["run_id"], "r1")

    def test_scalar_yaml(self):
        self.document("runs/r1/run.yaml", [1, 2])
        self.assertEqual(self.service.items()[0]["state"], "other")

    def test_no_shared_cache_between_calls(self):
        path = self.run_document()
        self.assertTrue(self.service.summary()["governed"])
        path.write_text(json.dumps({"id": "r1", "status": "completed"}), encoding="utf-8")
        self.assertFalse(self.service.summary()["governed"])

    def test_existing_facade_parity(self):
        self.run_document()
        from processforge_core.composition import build_current_work_service
        self.assertEqual(build_current_work_service(self.project, documents=self.documents).summary(), self.service.summary())


class CompositionTests(Fixture):
    def setUp(self):
        super().setUp()
        from processforge_core.composition import build_current_work_service
        self.build = build_current_work_service

    def test_factory_has_no_io_and_injects_exact_port(self):
        service = self.build(self.project, documents=self.documents)
        self.assertEqual(self.documents.calls, [])
        self.assertIs(service.documents, self.documents)
        self.assertEqual(service.summary(), self.service.summary())
        self.assertNotIn("processforge", sys.modules)

    def test_independent_instances(self):
        first = self.build(self.project, documents=self.documents)
        other = FakeDocuments()
        second = self.build(self.project, documents=other)
        self.assertIsNot(first, second)
        self.assertIs(second.documents, other)

    def test_default_core_documents_are_live_and_preserve_parser_errors(self):
        service = self.build(self.project)
        path = self.run_document()
        self.assertTrue(service.summary()['governed'])
        path.write_text('key: [', encoding='utf-8')
        self.assertIn('__yaml_error__', service.documents.load(path))
        path.unlink()
        self.assertFalse(service.summary()['governed'])

    def test_bootstrap_additive_method_and_fields(self):
        from processforge_core.bootstrap import RuntimeBootstrap
        module = ModuleType("fake_legacy")
        def denied(*args):
            raise AssertionError("Work reader must not call legacy Core")
        module.locate_flow_root = denied
        module.load_yaml_document = denied
        runtime = RuntimeBootstrap(self.project, module, ModuleType("host"), ModuleType("service"))
        self.assertEqual([f.name for f in fields(runtime)], ["repo_root", "core", "host", "service"])
        self.assertEqual(runtime.current_work_service(self.project).summary(), self.service.summary())
        self.assertIs(runtime.core, module)
        self.assertNotIn("processforge", sys.modules)

    def test_default_record_reader_owns_core_documents(self):
        from processforge_core.work.records import YamlWorkRecordReader
        reader = YamlWorkRecordReader(self.project)
        self.assertEqual(reader.flow_root, self.project / '.pf')
        self.assertIsInstance(reader.documents, YamlDocumentReader)
        self.assertNotIn('core', {f.name for f in fields(reader)})

    def test_installed_shaped_package_without_cli(self):
        self.run_document("copied")
        target = self.project / "installed" / "src" / "processforge_core"
        shutil.copytree(ROOT / "src" / "processforge_core", target, ignore=shutil.ignore_patterns("__pycache__"))
        script = "\n".join([
            "import sys", f"sys.path.insert(0, {str(target.parent)!r})",
            "from pathlib import Path",
            "from processforge_core.composition import build_current_work_service",
            f"service = build_current_work_service(Path({str(self.project)!r}))",
            "assert service.summary()['governed']",
            "assert service.summary()['active_work'][0]['run_id'] == 'copied'",
            "assert 'processforge' not in sys.modules",
            "assert 'pf_runtime.host' not in sys.modules",
        ])
        completed = subprocess.run([sys.executable, "-I", "-B", "-c", script], cwd=target.parent, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--characterize-only", action="store_true")
    args = parser.parse_args()
    loader = unittest.defaultTestLoader
    suite = loader.loadTestsFromTestCase(CurrentWorkCharacterization)
    if not args.characterize_only:
        suite.addTests(loader.loadTestsFromTestCase(CompositionTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
