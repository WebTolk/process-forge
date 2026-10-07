#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml
import processforge as core
from processforge_core.common import yaml_io
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.garage import CurrentWorkService
from processforge_core.process_catalog import service as catalog
from processforge_core.process_catalog.models import ProcessCatalogContext
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.request_scope import request_scope
from processforge_core.work.inventory import WorkInventory


class YamlInventoryTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".pf" / "tmp"
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.flow = self.root / ".pf"
        self.reader = YamlDocumentReader(fallback=yaml_io._parse_simple_yaml)
        self.inventory = WorkInventory(self.flow, self.reader.load)
        adapter = SimpleNamespace(locate_flow_root=lambda _: self.flow,
                                  load_yaml_document=self.reader.load)
        self.garage = CurrentWorkService(self.root, adapter)
        self.lifecycle = ProcessExecutionService(self.root, self.root, adapter)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
        return path

    def run_doc(self, run_id, tasks):
        return self.write(self.flow / "runs" / run_id / "run.yaml",
                          {"id": run_id, "status": "open", "tasks": tasks})

    def task_doc(self, task_id, run_id):
        return self.write(self.inventory.assignment_path(task_id),
                          {"id": task_id, "run_id": run_id, "status": "open"})

    def test_missing_nonmapping_and_invalid_documents(self):
        path = self.root / "doc.yaml"
        self.assertEqual(self.reader.read(path), {})
        for value in (None, [1, 2], "text", 4):
            self.write(path, value)
            self.assertEqual(self.reader.load(path), {})
        for text in ("value: [", "!!python/object/apply:os.system ['exit']"):
            path.write_text(text, encoding="utf-8")
            self.assertIn("__yaml_error__", self.reader.load(path))
            with self.assertRaisesRegex(SystemExit, "^FAIL: .* is invalid YAML:"):
                self.reader.read(path)
        self.write(path, {"__yaml_error__": ""})
        self.assertEqual(self.reader.read(path), {"__yaml_error__": ""})

    def test_file_read_errors_are_not_parser_errors(self):
        path = self.write(self.root / "doc.yaml", {"value": 1})
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                self.reader.load(path)

    def test_absent_pyyaml_preserves_each_injected_fallback(self):
        path = self.root / "doc.yaml"
        path.write_text("nested:\n  value: true\ncount: 3\n", encoding="utf-8")
        with patch.dict(sys.modules, {"yaml": None}):
            expected = {"nested": {"value": True}, "count": 3}
            self.assertEqual(self.reader.load(path), expected)
            self.assertEqual(core.load_yaml_document(path), expected)
            self.assertEqual(catalog.load_yaml_document(path), expected)

    def test_core_and_catalog_share_parsing_not_mutable_results(self):
        path = self.write(self.root / "doc.yaml", {"values": [1, 2]})
        with request_scope() as scope:
            first = core.load_yaml_document(path)
            first["values"].clear()
            self.assertEqual(catalog.read_yaml_file(path), {"values": [1, 2]})
            self.assertEqual((scope.parses, scope.hits), (1, 1))

    def test_same_metadata_changes_deletion_and_new_run_are_visible(self):
        path = self.run_doc("a", [])
        metadata = path.stat()
        with request_scope():
            self.assertEqual(list(self.inventory.runs())[0][1]["status"], "open")
            text = path.read_text(encoding="utf-8").replace("open", "done")
            path.write_text(text, encoding="utf-8")
            os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            self.assertEqual(path.stat().st_size, metadata.st_size)
            self.assertEqual(list(self.inventory.runs())[0][1]["status"], "done")
            self.run_doc("b", [])
            self.assertEqual([p.parent.name for p, _ in self.inventory.runs()], ["a", "b"])
            path.unlink()
            self.assertEqual([p.parent.name for p, _ in self.inventory.runs()], ["b"])

    def test_garage_placeholder_rules_are_not_lifecycle_rules(self):
        self.run_doc("a", [])
        self.run_doc("b", [{"id": "missing", "status": "draft"}, "ignored"])
        self.write(self.inventory.assignment_path("first-assignment"), {"id": "first-assignment"})
        self.assertEqual([(r["run_id"], r["assignment_id"]) for r in self.garage.items()],
                         [("a", ""), ("b", "missing"), ("", "first-assignment")])
        self.assertEqual(self.lifecycle._work_records(include_historical=True), [])

    def test_lifecycle_retains_validation_and_historical_filtering(self):
        self.run_doc("a", [{"id": "t"}, {"id": "bad"}, {"id": "../unsafe"}])
        task = self.task_doc("t", "a")
        self.task_doc("bad", "other")
        self.assertEqual([r["assignment_id"] for r in self.lifecycle._work_records(include_historical=True)], ["t"])
        self.write(task, {"id": "t", "run_id": "a", "status": "completed"})
        self.assertEqual(self.lifecycle._work_records(include_historical=False), [])
        self.assertEqual(len(self.lifecycle._work_records(include_historical=True)), 1)

    def test_completion_intent_keeps_terminal_work_active(self):
        self.run_doc("a", [{"id": "t"}])
        self.write(self.inventory.assignment_path("t"), {"id": "t", "run_id": "a", "status": "done"})
        with patch.object(ProcessExecutionService, "_load_completion_intent", return_value=({"id": "intent"}, None)):
            record = self.lifecycle._work_records(include_historical=False)[0]
            self.assertTrue(record["active"])
            self.assertTrue(record["pending_completion"])

    def test_new_ambiguity_and_mismatched_identity_are_not_hidden(self):
        self.run_doc("a", [{"id": "t"}])
        self.task_doc("t", "a")
        with request_scope():
            self.assertEqual(self.lifecycle._select_work(run_id="a", assignment_id="t")[1]["id"], "t")
            with self.assertRaisesRegex(ValueError, "work_identity_mismatch"):
                self.lifecycle._select_work(run_id="other", assignment_id="t")
            self.run_doc("a", [{"id": "t"}, {"id": "u"}])
            self.task_doc("u", "a")
            with self.assertRaisesRegex(ValueError, "assignment_choice_required"):
                self.lifecycle._select_work(run_id="a")
            self.inventory.assignment_path("t").unlink()
            self.assertIsNone(self.lifecycle._select_work(run_id="a", assignment_id="t"))

    def test_legacy_aliases_duplicate_discovery_and_invalid_selectors(self):
        path = self.run_doc("a", [{"id": "alias"}])
        self.write(self.inventory.assignment_path("alias"), {"id": "real", "status": "open"})
        self.task_doc("real", "a")
        self.write(self.flow / "runs" / "duplicate" / "run.yaml", self.reader.load(path))
        self.assertEqual([r["assignment_id"] for r in self.lifecycle._work_records(include_historical=True)], ["real", "real"])
        with self.assertRaisesRegex(ValueError, "assignment_choice_required"):
            self.lifecycle._select_work(run_id="a")
        with self.assertRaisesRegex(ValueError, "invalid_work_selector"):
            self.lifecycle._select_work(assignment_id="../unsafe")

    def test_catalog_precedence_strict_warnings_and_fresh_references(self):
        user = self.write(self.root / "processes" / "user" / "p.yaml", {"id": "p", "name": "User"})
        self.write(self.root / "processes" / "core" / "p.yaml", {"id": "p", "name": "Core"})
        context = ProcessCatalogContext(self.root, self.flow, self.root / "distribution", frozenset())
        with request_scope():
            first = catalog.process_catalog_entries(context, strict=True)[0]
            self.assertEqual(first.origin, "user")
            self.assertTrue(any(w.startswith("STRICT:") for w in first.warnings))
            self.assertTrue(any("process_override.reason" in w for w in first.warnings))
            first.process["name"] = "Mutated"
            first.warnings.clear()
            second = catalog.process_catalog_entries(context)[0]
            self.assertEqual(second.process["name"], "User")
            self.assertFalse(any(w.startswith("STRICT:") for w in second.warnings))
            user.unlink()
            self.assertEqual(catalog.process_catalog_entries(context)[0].origin, "core")


def compare_catalog_corpus():
    paths = sorted((ROOT / "processes").rglob("*.yaml"))
    count = 0
    for path in paths:
        expected = yaml_io.load_yaml_document(path)
        actual = catalog.load_yaml_document(path)
        if yaml_io.yaml_error(expected):
            if not yaml_io.yaml_error(actual):
                raise AssertionError(f"catalog failed to reject {path.name}")
        elif actual != expected:
            raise AssertionError(f"catalog parser mismatch: {path.name}")
        count += 1
    print(f"Catalog legacy reader parity: {count} YAML documents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", action="store_true")
    arguments = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(YamlInventoryTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if arguments.corpus:
        compare_catalog_corpus()
