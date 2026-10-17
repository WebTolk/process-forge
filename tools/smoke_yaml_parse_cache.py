#!/usr/bin/env python3
"""Shared YAML freshness, policy, mutation, projection and retention checks."""
from __future__ import annotations

import concurrent.futures
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import yaml
import processforge as core
from processforge_core.common import request_scope as scope
from processforge_core.documents.parse_cache import YamlParseCache
from processforge_core.documents.reader import YamlDocumentReader


class YamlCacheTests(unittest.TestCase):
    def setUp(self):
        scope._PARSE_CACHE.clear()

    def test_cross_request_reuse_preserves_aliases_cycles_and_isolation(self):
        text = "a: &a [1, 2]\nb: *a\ncycle: &c [*c]\n"
        first = scope.safe_load(text)
        first["a"].append(9)
        second = scope.safe_load(text)
        self.assertEqual(second["a"], [1, 2])
        self.assertIs(second["a"], second["b"])
        self.assertIs(second["cycle"], second["cycle"][0])
        self.assertIsNot(first["cycle"], second["cycle"])
        self.assertEqual(scope._PARSE_CACHE.info()["parses"], 1)
        with scope.request_scope() as request:
            third = scope.safe_load(text)
            third["a"].clear()
            self.assertEqual(scope.safe_load(text)["a"], [1, 2])
            self.assertEqual((request.parses, request.hits), (0, 2))

    def test_actual_bytes_win_over_same_size_and_restored_mtime(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf/tmp") as directory:
            path = Path(directory) / "run.yaml"
            reader = YamlDocumentReader(lambda _: {})
            path.write_text("id: alpha\nstatus: open\n", encoding="utf-8")
            original = path.stat()
            self.assertEqual(reader.load_fields(path, ("id", "status")), {"id": "alpha", "status": "open"})
            path.write_text("id: bravo\nstatus: done\n", encoding="utf-8")
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
            self.assertEqual(path.stat().st_size, original.st_size)
            self.assertEqual(reader.load_fields(path, ("id", "status")), {"id": "bravo", "status": "done"})
            path.unlink()
            self.assertEqual(reader.load(path), {})
            self.assertEqual(reader.load_fields(path, ("id",)), {})
            path.write_text("id: again\nstatus: open\n", encoding="utf-8")
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
            self.assertEqual(reader.load(path)["id"], "again")

    def test_projection_validates_complete_history_and_keeps_memory_small(self):
        text = "id: large\nstatus: open\nhistory: '" + "x" * (1024 * 1024) + "'\n"
        expected = {"id": "large", "status": "open"}
        self.assertEqual(scope.safe_load_fields(text, ("id", "status")), expected)
        self.assertEqual(scope.safe_load_fields(text, ("id", "status")), expected)
        info = scope._PARSE_CACHE.info()
        self.assertEqual((info["parses"], info["hits"]), (1, 1))
        self.assertLess(info["bytes"], len(text) // 4)
        with self.assertRaises(yaml.YAMLError):
            scope.safe_load_fields("id: large\nstatus: open\nhistory: [broken", ("id", "status"))
        self.assertEqual(scope._PARSE_CACHE.info()["entries"], 1)

    def test_full_value_can_supply_projection_without_another_parse(self):
        text = "id: &id [one]\nstatus: *id\nhistory: [1, 2]\n"
        full = scope.safe_load(text)
        selected = scope.safe_load_fields(text, ("id", "status"))
        self.assertIs(selected["id"], selected["status"])
        selected["id"].append("changed")
        self.assertEqual(full["id"], ["one"])
        self.assertEqual(scope.safe_load_fields(text, ("id", "status"))["id"], ["one"])
        self.assertEqual(scope._PARSE_CACHE.info()["parses"], 1)

    def test_safe_scalar_collection_and_timestamp_types_match_native(self):
        text = "date: 2026-10-17\ntime: 2026-10-17T07:00:00Z\nbytes: !!binary aGVsbG8=\nset: !!set {one: null, two: null}\nordered: !!omap [{a: 1}, {b: 2}]\n"
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        expected = yaml.load(text, Loader=loader)
        self.assertEqual(scope.safe_load(text), expected)
        self.assertEqual(scope.safe_load(text), expected)
        self.assertEqual(scope._PARSE_CACHE.info()["parses"], 1)

    def test_invalid_unsafe_and_surrogate_input_keep_native_errors(self):
        for text in ("a: [", "!!python/object/apply:os.system ['exit']", "a: '\ud800'"):
            scope._PARSE_CACHE.clear()
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            try:
                yaml.load(text, Loader=loader)
            except Exception as expected:
                for _ in range(2):
                    with self.assertRaises(type(expected)) as caught:
                        scope.safe_load(text)
                    self.assertEqual(str(caught.exception), str(expected))
            else:
                self.fail("invalid fixture accepted by native parser")
            self.assertEqual(scope._PARSE_CACHE.info()["entries"], 0)

    def test_resolver_change_is_visible_even_inside_one_request(self):
        loader = yaml.SafeLoader
        changed = dict(loader.yaml_implicit_resolvers)
        changed["y"] = [item for item in changed["y"] if item[0] != "tag:yaml.org,2002:bool"]
        with patch.object(yaml, "CSafeLoader", loader, create=True), scope.request_scope():
            self.assertIs(scope.safe_load("value: yes\n")["value"], True)
            with patch.object(loader, "yaml_implicit_resolvers", changed):
                self.assertEqual(scope.safe_load("value: yes\n")["value"], "yes")
            self.assertIs(scope.safe_load("value: yes\n")["value"], True)

    def test_custom_constructor_effects_are_not_cached(self):
        class Custom(yaml.SafeLoader):
            pass

        calls = []

        def construct(_loader, _node):
            calls.append(True)
            return len(calls)

        Custom.add_constructor("!counter", construct)
        with patch.object(yaml, "CSafeLoader", Custom, create=True), scope.request_scope():
            self.assertEqual(scope.safe_load("!counter x"), 1)
            self.assertEqual(scope.safe_load("!counter x"), 2)
        self.assertEqual(scope._PARSE_CACHE.info()["entries"], 0)

    def test_retention_limits_eviction_and_oversize_bypass(self):
        limited = YamlParseCache(max_bytes=100000, max_entries=2, max_entry_bytes=100000)
        with patch.object(scope, "_PARSE_CACHE", limited):
            for number in range(30):
                self.assertEqual(scope.safe_load(f"value: {number}\n"), {"value": number})
                self.assertLessEqual(limited.info()["entries"], 2)
                self.assertLessEqual(limited.info()["bytes"], 100000)
            self.assertGreater(limited.info()["evictions"], 0)
            self.assertEqual(scope.safe_load("value: 29\n"), {"value": 29})
            before = limited.info()["parses"]
            self.assertEqual(scope.safe_load("value: 29\n"), {"value": 29})
            self.assertEqual(limited.info()["parses"], before)
        with patch.object(scope, "_PARSE_CACHE", YamlParseCache(max_entry_bytes=64)):
            self.assertEqual(scope.safe_load("value: 1\n"), {"value": 1})
            self.assertEqual(scope._PARSE_CACHE.info()["entries"], 0)

    def test_concurrent_reuse_has_independent_values_and_bounded_accounting(self):
        text = "a: &a [one]\nb: *a\n"
        scope.safe_load(text)

        def read(number):
            value = scope.safe_load(text)
            self.assertIs(value["a"], value["b"])
            self.assertEqual(value["a"], ["one"])
            value["a"].append(number)
            return value

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(read, range(60)))
        self.assertEqual(len({id(row["a"]) for row in results}), 60)
        self.assertEqual(scope._PARSE_CACHE.info()["parses"], 1)
        self.assertEqual(scope.safe_load(text)["a"], ["one"])

    def test_reader_fallback_and_strict_error_envelope(self):
        reader = YamlDocumentReader(lambda _: {"id": "fallback", "status": "open", "extra": 1})
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf/tmp") as directory:
            path = Path(directory) / "run.yaml"
            path.write_text("id: native\n", encoding="utf-8")
            with patch.dict(sys.modules, {"yaml": None}):
                self.assertEqual(reader.load(path)["extra"], 1)
                self.assertEqual(reader.load_fields(path, ("id", "status")), {"id": "fallback", "status": "open"})
            path.write_text("history: [broken", encoding="utf-8")
            error = reader.load(path)["__yaml_error__"]
            self.assertEqual(reader.load_fields(path, ("id", "status"))["__yaml_error__"], error)
            with self.assertRaises(SystemExit) as caught:
                reader.read(path)
            self.assertEqual(str(caught.exception), f"FAIL: {path} is invalid YAML: {error}")
            with patch.object(Path, "read_text", side_effect=OSError("read denied")):
                with self.assertRaisesRegex(OSError, "read denied"):
                    reader.load(path)

    def test_active_run_discovery_matches_legacy_types_errors_and_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf/tmp") as directory:
            project = Path(directory)
            (project / ".pf/runs").mkdir(parents=True)
            (project / ".pf/process-forge.yaml").write_text("schema_version: 1\n", encoding="utf-8")
            cases = {"z-last": "id: last\nstatus: open\n", "a-first": "id: first\nstatus: in_progress\n",
                     "b-done": "id: done\nstatus: done\n", "c-missing-id": "status: blocked\n",
                     "d-bad": "status: [broken", "e-reserved": "id: denied\nstatus: open\n__yaml_error__: invalid\n",
                     "f-list": "[one, two]\n", "g-numeric": "id: 123\nstatus: open\n",
                     "h-duplicate": "id: first\nstatus: review\n"}
            for name, text in cases.items():
                target = project / ".pf/runs" / name / "run.yaml"
                target.parent.mkdir()
                target.write_text(text, encoding="utf-8")

            def legacy():
                result = []
                for path in sorted((project / ".pf/runs").glob("*/run.yaml")):
                    value = core.load_yaml_document(path)
                    if not core.yaml_error(value) and str(value.get("status", "")) in {"draft", "open", "in_progress", "blocked", "review"}:
                        result.append(str(value.get("id") or path.parent.name))
                return result

            self.assertEqual(core.active_run_ids(project), legacy())
            self.assertEqual(core.active_run_ids(project), ["first", "c-missing-id", "123", "first", "last"])
            added = project / ".pf/runs/new"
            added.mkdir()
            (added / "run.yaml").write_text("id: new\nstatus: open\n", encoding="utf-8")
            self.assertEqual(core.active_run_ids(project), legacy())
            (project / ".pf/runs/a-first/run.yaml").unlink()
            self.assertEqual(core.active_run_ids(project), legacy())


if __name__ == "__main__":
    unittest.main(verbosity=2)
