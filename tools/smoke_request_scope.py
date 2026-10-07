#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml
import processforge as core
from processforge_core.common import request_scope as scope


class RequestScopeTests(unittest.TestCase):
    def test_reuse_and_mutation_isolation(self):
        text = "a: &value [1, 2]\nb: *value\n"
        with scope.request_scope() as current:
            first = scope.safe_load(text)
            first["a"].append(3)
            second = scope.safe_load(text)
            self.assertEqual(second["a"], [1, 2])
            self.assertIs(second["a"], second["b"])
            second["b"].clear()
            self.assertEqual(scope.safe_load(text)["a"], [1, 2])
            self.assertEqual((current.loads, current.parses, current.hits), (3, 1, 2))
        with scope.request_scope() as other:
            scope.safe_load(text)
            self.assertEqual((other.parses, other.hits), (1, 0))

    def test_unchanged_metadata_does_not_hide_changes_or_deletion(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf" / "tmp") as directory:
            path = Path(directory) / "document.yaml"
            path.write_text("value: old\n", encoding="utf-8")
            metadata = path.stat()
            with scope.request_scope():
                self.assertEqual(core.load_yaml_document(path), {"value": "old"})
                path.write_text("value: new\n", encoding="utf-8")
                os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                self.assertEqual(path.stat().st_size, metadata.st_size)
                self.assertEqual(core.load_yaml_document(path), {"value": "new"})
                path.unlink()
                self.assertEqual(core.load_yaml_document(path), {})
            path.write_text("value: end\n", encoding="utf-8")
            os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            with scope.request_scope():
                self.assertEqual(core.load_yaml_document(path), {"value": "end"})

    def test_invalid_and_unsafe_yaml_are_not_cached(self):
        for text in ("a: [", "!!python/object/apply:os.system ['exit']"):
            with scope.request_scope() as current:
                for _ in range(2):
                    with self.assertRaises(yaml.YAMLError):
                        scope.safe_load(text)
                self.assertEqual(current.parses, 2)
                self.assertFalse(current.documents)

    def test_safe_python_fallback_and_loader_identity(self):
        with scope.request_scope() as current:
            scope.safe_load("value: yes\n")
            original = getattr(yaml, "CSafeLoader", None)
            try:
                if original is not None:
                    del yaml.CSafeLoader
                self.assertEqual(scope.safe_load("value: yes\n"), {"value": True})
                self.assertIn((yaml.SafeLoader, "value: yes\n"), current.documents)
                self.assertEqual(current.parses, 2 if original is not None else 1)
            finally:
                if original is not None:
                    yaml.CSafeLoader = original

    def test_nested_scopes_cleanup_and_decorator(self):
        @scope.scoped_request
        def broken():
            with scope.request_scope() as inner:
                self.assertIs(inner, scope._CURRENT.get())
                scope.safe_load("value: 1\n")
            raise RuntimeError("expected")

        with self.assertRaises(RuntimeError):
            broken()
        self.assertIsNone(scope._CURRENT.get())
        self.assertEqual(broken.__name__, "broken")
        with scope.request_scope() as outer:
            with scope.request_scope() as inner:
                self.assertIs(outer, inner)

    def test_independent_threads(self):
        with scope.request_scope() as outer:
            scope.safe_load("value: 1\n")

            def worker():
                self.assertIsNone(scope._CURRENT.get())
                with scope.request_scope() as current:
                    scope.safe_load("value: 1\n")
                    return current.parses, current.hits, current is outer

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(list(pool.map(lambda _: worker(), range(4))), [(1, 0, False)] * 4)
            self.assertEqual((outer.parses, outer.hits), (1, 0))

    def test_frozen_exception_identity_survives_context_and_trace(self):
        @dataclass(frozen=True)
        class FrozenError(Exception):
            code: str

        error = FrozenError("session_project_mismatch")

        @scope.scoped_request
        def denied():
            with scope.request_scope():
                raise error

        records = []
        config = scope.diagnostics.resolve_config(("invocation", {
            "profile": "trace", "expires_at": datetime.fromtimestamp(time.time() + 600, timezone.utc).isoformat(),
        }))
        logger = scope.diagnostics.Logger(config, sinks=[records.append])
        identity = scope.diagnostics._IDENTITY.set({})
        stdout = io.StringIO()
        try:
            with patch.object(scope.diagnostics, "current", return_value=logger), contextlib.redirect_stdout(stdout):
                with self.assertRaises(FrozenError) as caught:
                    denied()
        finally:
            scope.diagnostics._IDENTITY.reset(identity)
        self.assertIs(caught.exception, error)
        self.assertIsNone(scope._CURRENT.get())
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual([record["code"] for record in records], [
            "work.request.span_start", "work.request.span_end", "work.request.yaml",
        ])
        self.assertEqual(records[-1]["context"]["operation"], "denied")

    def test_cache_limits_and_large_document(self):
        with patch.object(scope, "MAX_CACHE_ENTRIES", 1), scope.request_scope() as current:
            scope.safe_load("a: 1\n")
            scope.safe_load("a: 2\n")
            scope.safe_load("a: 2\n")
            self.assertEqual((len(current.documents), current.parses), (1, 3))
        with patch.object(scope, "MAX_CACHE_BYTES", 4), scope.request_scope() as current:
            scope.safe_load("a: 1\n")
            self.assertFalse(current.documents)
        with patch.object(scope, "MAX_DOCUMENT_BYTES", 4), scope.request_scope() as current:
            self.assertEqual(scope.safe_load("a: 1\n"), {"a": 1})
            self.assertFalse(current.documents)


def compare_corpus() -> None:
    count = 0
    paths = sorted((ROOT / ".pf" / "assignments").glob("*.yaml"))
    paths += sorted((ROOT / ".pf" / "runs").glob("*/run.yaml"))
    paths += sorted((ROOT / ".pf" / "contexts").rglob("*.yaml"))
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        try:
            expected = yaml.safe_load(text)
        except yaml.YAMLError:
            continue
        actual = scope.safe_load(text)
        if actual != expected:
            raise AssertionError(f"safe parser corpus mismatch: {path.name}")
        count += 1
    print(f"SafeLoader candidate parity: {count} valid project YAML documents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", action="store_true")
    arguments = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RequestScopeTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if arguments.corpus:
        compare_corpus()
