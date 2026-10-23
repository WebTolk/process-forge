#!/usr/bin/env python3
"""Resource search snapshot injection and retained-service compatibility."""

from __future__ import annotations

import argparse
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core import composition, garage  # noqa: E402 - source bootstrap
from processforge_core.common import request_scope  # noqa: E402 - source bootstrap
from processforge_core.resources import access  # noqa: E402 - source bootstrap

BASELINE = None
SCRATCH = None


def outcome(call):
    try:
        return ("return", call())
    except (Exception, SystemExit) as exc:
        return ("error", type(exc).__name__, getattr(exc, "code", None), str(exc))


def scenario(
    service_type,
    kind="search",
    *,
    status="fresh",
    supplied=None,
    index_status="fresh",
    error="",
    snapshots=None,
    namespace=None,
):
    events = []
    document = {"marker": "live", "unknown": ["kept"]}

    def paths(root):
        events.append(("path", str(root)))
        return Path("snapshot.yaml"), Path("snapshot.md")

    def load(path):
        events.append(("load", str(path)))
        if error == "load":
            raise OSError("yaml-load-failure")
        return copy.deepcopy(document)

    def check(*a, **kw):
        events.append(("check", kw))
        return {"status": status}

    def runtime(root):
        events.append(("runtime", str(root)))
        return {"index": "workplace"}

    core = SimpleNamespace(
        project_context_snapshot_paths=paths,
        load_yaml_document=load,
        project_context_check_result=check,
        workplace_search_runtime_snapshot=runtime,
    )

    class Index:
        def __init__(self, root, snapshot, workplace):
            self.root = root
            events.append(("index", str(root), copy.deepcopy(snapshot)))

        def status(self, **kw):
            events.append(("status", str(self.root), kw))
            if error == "index":
                raise access.LocalSearchError("index_failure")
            return {
                "status": index_status,
                "resource_count": 1,
                "document_count": 0 if error == "empty" else 1,
            }

        def maintenance_tick(self):
            events.append(("maintenance", str(self.root)))
            raise AssertionError("Read-only search must not maintain the index")

        def search(self, **kw):
            events.append(("query", kw))
            if error == "query":
                raise access.LocalSearchError("invalid_query")
            return {"results": [{"unknown": "kept"}], "query": kw}

    class Observation:
        def __init__(self, root):
            self.root = root

        def observe(self):
            return Index(self.root, runtime(self.root), self.root).status(
                verify_files=False
            )

        def checkpoint(self):
            return None, None

    def coverage(root, snapshot, **kw):
        events.append(("coverage", copy.deepcopy(snapshot)))
        return {
            "marker": snapshot.get("marker"),
            "scope": "authorized",
            "indexed_resource_count": 1,
            "document_count": 0 if error == "empty" else 1,
        }

    def roots(root, snapshot, workplace, core=None):
        events.append(("roots", copy.deepcopy(snapshot)))
        return {**snapshot, "runtime": "resolved"}

    def navigation(payload, snapshot):
        events.append(("navigation", copy.deepcopy(snapshot)))
        payload["navigation"] = "private"

    replacements = {
        "ResourceSearchIndex": Index,
        "IndexObservationService": Observation,
        "authorized_coverage": coverage,
        "snapshot_with_resolved_search_roots": roots,
        "add_private_navigation": navigation,
    }
    with ExitStack() as stack:
        stack.enter_context(patch.dict(access.__dict__, replacements))
        if namespace is not None:
            stack.enter_context(patch.dict(namespace, replacements))
        if service_type is access.ResourceSearchService:
            # Policy traces substitute observation at its explicit read seam.
            # Real catalogue/SQLite behavior is covered by integration fixtures.
            service = composition.build_resource_search_service(
                Path("p"),
                Path("w"),
                core,
                snapshots=snapshots
                if snapshots is not None
                else FixtureSnapshots(paths, load),
            )
        else:
            service = service_type(
                Path("p"),
                Path("w"),
                core,
                **({"snapshots": snapshots} if snapshots is not None else {}),
            )
        result = outcome(
            lambda: (
                service.readiness(snapshot=supplied)
                if kind == "readiness"
                else service.search(query="needle", limit="2", limitstart="1", offset=1)
            )
        )
    return result, events


class FixtureSnapshots:
    """Injected test port for policy traces; never the production default."""

    def __init__(self, paths, load):
        self.paths, self.read = paths, load

    def load(self, path=None):
        if path is None:
            path, _ = self.paths(Path("p"))
        return self.read(path)

    def checksum(self, path):
        raise AssertionError("Policy snapshot reads must not hash")


class MemorySnapshots:
    def __init__(self):
        self.calls = []
        self.document = {"marker": "injected", "unknown": ["kept"]}

    def __bool__(self):
        return False

    def load(self, path=None):
        self.calls.append(path)
        return self.document

    def checksum(self, path):
        raise AssertionError("Search must not hash the snapshot")


class SearchSnapshotTests(unittest.TestCase):
    def test_readonly_policy_and_error_contract(self):
        options = [
            ("readiness", {}),
            ("readiness", {"supplied": {}}),
            ("readiness", {"status": "stale"}),
            ("readiness", {"index_status": "stale"}),
            ("readiness", {"error": "index"}),
            ("readiness", {"error": "empty"}),
            ("search", {}),
            ("search", {"status": "stale"}),
            ("search", {"status": "fresh_with_updates"}),
            ("search", {"index_status": "missing"}),
            ("search", {"error": "load"}),
            ("search", {"error": "index"}),
            ("search", {"index_status": "stale", "error": "maintenance"}),
            ("search", {"error": "query"}),
        ]
        for kind, config in options:
            actual = scenario(access.ResourceSearchService, kind, **config)
            self.assertFalse(
                any(row[0] == "maintenance" for row in actual[1]), (kind, config)
            )
            # Hidden maintenance was intentionally removed. Baseline parity is
            # meaningful only for the preceding stale-context refusal guard.
            if BASELINE and config.get("status") == "stale":
                expected = scenario(
                    BASELINE["ResourceSearchService"],
                    kind,
                    namespace=BASELINE,
                    **config,
                )
                self.assertEqual(actual, expected, (kind, config))
            if kind == "search" and config.get("status") == "stale":
                self.assertEqual(
                    actual[0][1:3], ("LocalSearchError", "snapshot_not_fresh")
                )
                self.assertEqual([row[0] for row in actual[1]], ["check"])
            elif kind == "search" and config.get("index_status") in {
                "missing",
                "stale",
            }:
                self.assertEqual(actual[0][0], "return")
                self.assertEqual(actual[0][1]["search_status"], config["index_status"])
                self.assertEqual(actual[0][1]["results"], [])
                self.assertEqual(
                    (actual[0][1]["limit"], actual[0][1]["offset"]), (2, 1)
                )
            elif kind == "search" and config.get("error") in {"query", "load", "index"}:
                self.assertEqual(actual[0][0], "error")
                expected = {
                    "query": "invalid_query",
                    "index": "index_failure",
                    "load": None,
                }[config["error"]]
                self.assertEqual(actual[0][2], expected)
            elif kind == "readiness" and config.get("index_status") == "stale":
                self.assertEqual(actual[0][1]["status"], "stale")
            elif kind == "readiness" and config.get("error") == "empty":
                self.assertEqual(actual[0][1]["status"], "empty")

    def test_injected_falsey_reader_and_snapshot_override(self):
        memory = MemorySnapshots()
        result, events = scenario(access.ResourceSearchService, snapshots=memory)
        self.assertEqual(result[0], "return")
        self.assertEqual(result[1]["authorized_coverage"]["marker"], "injected")
        self.assertEqual(memory.calls, [None])
        self.assertFalse(any(event[0] in ("path", "load") for event in events))
        memory.calls.clear()
        result, _events = scenario(
            access.ResourceSearchService, "readiness", snapshots=memory, supplied={}
        )
        self.assertEqual(result[1]["authorized_coverage"]["marker"], None)
        self.assertFalse(memory.calls)

    def test_guard_and_blocked_readiness_keep_distinct_order(self):
        memory = MemorySnapshots()
        result, events = scenario(
            access.ResourceSearchService, status="stale", snapshots=memory
        )
        self.assertEqual(result[0], "error")
        self.assertFalse(memory.calls)
        self.assertEqual([row[0] for row in events], ["check"])
        result, events = scenario(
            access.ResourceSearchService, "readiness", status="stale", snapshots=memory
        )
        self.assertEqual(result[1]["reason"], "snapshot_not_fresh")
        self.assertEqual(memory.calls, [None])
        self.assertEqual([row[0] for row in events], ["check", "coverage"])

    def test_constructor_factory_without_io(self):
        def fail(*a, **k):
            return self.fail("Assembly must not call Core")

        core = SimpleNamespace(
            project_context_snapshot_paths=fail,
            load_yaml_document=fail,
            project_context_check_result=fail,
        )
        memory = MemorySnapshots()
        old = composition.build_resource_search_service(Path("p"), Path("w"), core)
        built = composition.build_resource_search_service(
            Path("p"), Path("w"), core, snapshots=memory
        )
        self.assertIs(built.snapshots, memory)
        self.assertEqual(old, built)
        self.assertEqual(repr(old), repr(built))
        self.assertEqual(outcome(lambda: hash(old)), outcome(lambda: hash(built)))
        self.assertEqual(
            old.__match_args__, ("project_root", "workplace_root", "reads")
        )
        field = next(item for item in fields(built) if item.name == "snapshots")
        self.assertTrue(field.kw_only)
        self.assertFalse(field.compare or field.repr)
        with self.assertRaises(TypeError):
            access.ResourceSearchService(Path("p"), Path("w"), old.reads, memory)

    def test_real_yaml_live_reads_and_scope_isolation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            path = Path(directory) / ".pf/contexts/project-context.snapshot.yaml"
            path.parent.mkdir(parents=True)
            path.write_text("marker: aa\n", encoding="utf-8")

            def load(*args):
                self.fail("Default reader must not call the legacy loader or paths")

            core = SimpleNamespace(
                project_context_snapshot_paths=load,
                load_yaml_document=load,
                project_context_check_result=lambda *_args, **_kwargs: {
                    "status": "fresh"
                },
            )
            service = composition.build_resource_search_service(
                Path(directory), Path("w"), core
            )
            with (
                patch.object(access, "IndexObservationService") as observer,
                patch.object(
                    access.ResourceSearchService,
                    "_readiness",
                    return_value={"status": "ready"},
                ),
                patch.object(
                    access,
                    "authorized_coverage",
                    side_effect=lambda root, document, **kw: document,
                ),
            ):
                observer.return_value.checkpoint.return_value = (None, None)
                observer.return_value.observe.return_value = {"status": "fresh"}
                stat = path.stat()
                with request_scope.request_scope() as scope:
                    first = service.readiness()["authorized_coverage"]
                    first["marker"] = "mutated"
                    self.assertEqual(
                        service.readiness()["authorized_coverage"], {"marker": "aa"}
                    )
                    path.write_text("marker: bb\n", encoding="utf-8")
                    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                    self.assertEqual(path.stat().st_size, stat.st_size)
                    self.assertEqual(
                        service.readiness()["authorized_coverage"], {"marker": "bb"}
                    )
                    self.assertEqual((scope.loads, scope.parses, scope.hits), (3, 2, 1))
                self.assertIsNone(request_scope._CURRENT.get())
                with request_scope.request_scope() as scope:
                    self.assertEqual(
                        service.readiness()["authorized_coverage"], {"marker": "bb"}
                    )
                    # A new request reloads bytes and reuses the shared parse.
                    self.assertEqual((scope.loads, scope.parses, scope.hits), (1, 0, 1))
                path.write_text("marker: [\n", encoding="utf-8")
                with request_scope.request_scope():
                    self.assertIn(
                        "__yaml_error__", service.readiness()["authorized_coverage"]
                    )
                self.assertIsNone(request_scope._CURRENT.get())

    def test_mcp_composition_guards_and_error_mapping(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from pf_runtime import mcp_server, session_read

        core = SimpleNamespace(project_id=lambda root: str(root))
        host = SimpleNamespace(
            resolve_project=lambda reference, core: Path(reference),
            project_for_session=lambda *a: Path("bound"),
        )
        runtime = SimpleNamespace(core=core, host=host)
        calls = []

        def factory(root, workplace, given_core):
            calls.append(root)
            return SimpleNamespace(search=lambda **kw: {"query_arguments": kw})

        with patch.object(
            composition, "build_resource_search_service", side_effect=factory
        ):
            for arguments, session, reason in [
                (
                    {"project_root": "bound", "session_id": "other"},
                    "s",
                    "session_mismatch",
                ),
                ({"project_root": "other"}, "s", "session_project_mismatch"),
                ({}, "", "missing_project_root"),
            ]:
                with self.assertRaises(session_read.SessionReadError) as caught:
                    mcp_server.tool_result(
                        "pf.search", arguments, Path("w"), session, runtime
                    )
                self.assertEqual(caught.exception.code, reason)
                self.assertFalse(calls)
            result = mcp_server.tool_result(
                "pf.search",
                {"project_root": "bound", "query": "needle", "limit": "2", "offset": 0},
                Path("w"),
                "s",
                runtime,
            )
            self.assertEqual(
                result["query_arguments"],
                {"query": "needle", "limit": "2", "limitstart": None, "offset": 0},
            )
        self.assertEqual(calls, [Path("bound")])
        denied = SimpleNamespace(
            search=lambda **kw: (_ for _ in ()).throw(
                access.LocalSearchError("snapshot_not_fresh")
            )
        )
        with patch.object(
            composition, "build_resource_search_service", return_value=denied
        ):
            with self.assertRaises(session_read.SessionReadError) as caught:
                mcp_server.tool_result(
                    "pf.search",
                    {"project_root": "bound", "query": "needle"},
                    Path("w"),
                    "",
                    runtime,
                )
            self.assertEqual(caught.exception.code, "snapshot_not_fresh")
            self.assertIsInstance(caught.exception.__cause__, access.LocalSearchError)
        self.assertIsNone(request_scope._CURRENT.get())

    def test_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            shutil.copytree(
                ROOT / "src/processforge_core",
                root / "processforge_core",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            code = "from pathlib import Path; from processforge_core.composition import build_resource_search_service; from types import SimpleNamespace; assert build_resource_search_service(Path('p'),Path('w'),SimpleNamespace()).snapshots is None"
            result = subprocess.run(
                [sys.executable, "-B", "-c", code],
                cwd=root,
                capture_output=True,
                text=True,
                env=dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--scratch-root", type=Path)
    args = parser.parse_args()
    if args.baseline:
        BASELINE = dict(garage.__dict__)
        exec(
            compile(
                args.baseline.read_text(encoding="utf-8"), str(args.baseline), "exec"
            ),
            BASELINE,
        )
    if args.scratch_root:
        args.scratch_root.mkdir(parents=True, exist_ok=True)
        SCRATCH = args.scratch_root
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SearchSnapshotTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
