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

from processforge_core.document_store import YamlDocumentReader
from processforge_core.garage import CurrentWorkService, governed_work_summary


class FakeReadCore:
    def __init__(self):
        self.calls = []
        self.reader = YamlDocumentReader(lambda text: {})

    def locate_flow_root(self, project_root: Path) -> Path:
        self.calls.append(("root", project_root))
        return project_root / ".pf"

    def load_yaml_document(self, path: Path) -> dict:
        self.calls.append(("load", path))
        return self.reader.load(path)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pf-read-composition-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.core = FakeReadCore()
        self.service = CurrentWorkService(self.project, self.core)

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
        self.assertIn("__yaml_error__", self.core.load_yaml_document(path))
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
        self.assertEqual(governed_work_summary(self.project, self.core), self.service.summary())


class CompositionTests(Fixture):
    def setUp(self):
        super().setUp()
        from processforge_core.composition import LegacyWorkReadAdapter, build_current_work_service
        self.adapter_type = LegacyWorkReadAdapter
        self.build = build_current_work_service

    def test_factory_has_no_io_and_injects_exact_port(self):
        service = self.build(self.project, self.core)
        self.assertEqual(self.core.calls, [])
        self.assertIs(service.core, self.core)
        self.assertEqual(service.summary(), self.service.summary())
        self.assertNotIn("processforge", sys.modules)

    def test_independent_instances(self):
        first = self.build(self.project, self.core)
        other = FakeReadCore()
        second = self.build(self.project, other)
        self.assertIsNot(first, second)
        self.assertIs(second.core, other)

    def test_adapter_preserves_values_and_exception(self):
        module = ModuleType("fake_legacy")
        module.locate_flow_root = self.core.locate_flow_root
        payload = {"__yaml_error__": "sentinel"}
        module.load_yaml_document = lambda path: payload
        adapter = self.adapter_type(module)
        self.assertIs(adapter.load_yaml_document(self.project), payload)
        self.assertEqual(adapter.locate_flow_root(self.project), self.project / ".pf")
        def fail(path):
            raise ValueError("sentinel")
        module.load_yaml_document = fail
        with self.assertRaisesRegex(ValueError, "sentinel"):
            adapter.load_yaml_document(self.project)

    def test_bootstrap_additive_method_and_fields(self):
        from processforge_core.bootstrap import RuntimeBootstrap
        module = ModuleType("fake_legacy")
        module.locate_flow_root = self.core.locate_flow_root
        module.load_yaml_document = self.core.load_yaml_document
        runtime = RuntimeBootstrap(self.project, module, ModuleType("host"), ModuleType("service"))
        self.assertEqual([f.name for f in fields(runtime)], ["repo_root", "core", "host", "service"])
        self.assertEqual(runtime.current_work_service(self.project).summary(), self.service.summary())
        self.assertIs(runtime.core, module)
        self.assertNotIn("processforge", sys.modules)

    def test_port_members_only(self):
        from processforge_core.ports import WorkReadCorePort
        methods = {name for name in vars(WorkReadCorePort) if not name.startswith("_")}
        self.assertEqual(methods, {"locate_flow_root", "load_yaml_document"})

    def test_installed_shaped_package_without_cli(self):
        target = self.project / "installed" / "src" / "processforge_core"
        shutil.copytree(ROOT / "src" / "processforge_core", target, ignore=shutil.ignore_patterns("__pycache__"))
        script = "\n".join([
            "import sys", f"sys.path.insert(0, {str(target.parent)!r})",
            "from pathlib import Path",
            "from processforge_core.composition import build_current_work_service",
            "class Port:", "    def locate_flow_root(self, project): return project / '.pf'",
            "    def load_yaml_document(self, path): return {}",
            "service = build_current_work_service(Path('.'), Port())",
            "assert not service.summary()['governed']",
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
