#!/usr/bin/env python3
"""Garage snapshot composition, compatibility and live-read regression checks."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import copy
from dataclasses import fields
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core import composition, garage
from processforge_core.common import request_scope
from processforge_core.project import mode, reports, snapshot
from processforge_core.process_catalog import summary
from processforge_core.project.snapshot import ProjectSnapshotReadService

BASELINE = None
SCRATCH = None


class Core:
    def __init__(self, document=None, *, paths=None, path_error=None, load_error=None):
        self.document = document
        self.paths = paths if paths is not None else (Path('snapshot.yaml'), Path('snapshot.md'))
        self.path_error, self.load_error = path_error, load_error
        self.calls = []

    def project_context_snapshot_paths(self, root):
        self.calls.append(('path', root))
        if self.path_error:
            raise self.path_error('path-error')
        return self.paths

    def load_yaml_document(self, path):
        self.calls.append(('load', path))
        if self.load_error:
            raise self.load_error('load-error')
        return self.document


class MemorySnapshots:
    def __init__(self):
        self.calls = []
        self.document = {'snapshot': {'id': 'memory'}, 'unknown': ['retained']}

    def __bool__(self):
        return False

    def load(self, path=None):
        self.calls.append(('load', path))
        return self.document

    def checksum(self, path):
        raise AssertionError('Garage snapshot reads must not hash')


def old_load(root, core):
    path, _markdown = core.project_context_snapshot_paths(root)
    return core.load_yaml_document(path)


def outcome(fn):
    try:
        return ('return', fn())
    except (Exception, SystemExit) as exc:
        return ('error', type(exc).__name__, exc.args)


class GarageSnapshotTests(unittest.TestCase):
    def test_no_io_constructor_and_falsey_injection(self):
        core = Core()
        reader = composition.build_project_context_snapshot_read_service(Path('p'), core)
        self.assertIsInstance(reader, ProjectSnapshotReadService)
        memory = MemorySnapshots()
        old = garage.ProjectContextService(Path('p'), Path('w'), core)
        built = composition.build_project_context_service(Path('p'), Path('w'), core, snapshots=memory)
        self.assertFalse(core.calls)
        self.assertEqual(old, built)
        self.assertEqual(repr(old), repr(built))
        self.assertEqual(old.__match_args__, ('project_root', 'workplace_root', 'core'))
        dependency = next(field for field in fields(built) if field.name == 'snapshots')
        self.assertTrue(dependency.kw_only)
        self.assertFalse(dependency.compare or dependency.repr)
        self.assertIs(built.snapshot(), memory.document)
        self.assertIs(snapshot.load_snapshot(Path('p'), core, snapshots=memory), memory.document)
        self.assertEqual(memory.calls, [('load', None)] * 2)
        self.assertFalse(core.calls)
        with self.assertRaises(TypeError):
            garage.ProjectContextService(Path('p'), Path('w'), core, memory)

    def test_default_parity_return_identity_and_errors(self):
        helpers = [old_load]
        if BASELINE:
            helpers += [BASELINE['load_snapshot'], lambda root, core: BASELINE['ProjectContextService'](root, Path('w'), core).snapshot()]
        documents = [{}, {'unknown': {'value': [1, 2]}}, None, ['raw'], 'raw']
        scenarios = [{'document': document} for document in documents]
        scenarios += [{'paths': paths} for paths in [(), (Path('a'),), (Path('a'), Path('b'), Path('c'))]]
        scenarios += [{'path_error': error} for error in [OSError, ValueError, SystemExit]]
        scenarios += [{'load_error': error} for error in [OSError, ValueError, TypeError, SystemExit]]
        for scenario in scenarios:
            for helper in helpers:
                for call in [snapshot.load_snapshot, lambda root, core: garage.ProjectContextService(root, Path('w'), core).snapshot()]:
                    with self.subTest(scenario=scenario, helper=helper, call=call):
                        before, after = Core(**scenario), Core(**scenario)
                        self.assertEqual(outcome(lambda: helper(Path('p'), before)), outcome(lambda: call(Path('p'), after)))
                        self.assertEqual(before.calls, after.calls)
                        if not after.path_error and not after.load_error and len(after.paths) == 2:
                            self.assertIs(call(Path('p'), after), after.document)
        for call in [old_load, snapshot.load_snapshot]:
            core = SimpleNamespace(project_context_snapshot_paths=lambda root: None,
                                   load_yaml_document=lambda path: self.fail('Invalid path must stop before loading'))
            self.assertEqual(outcome(lambda: call(Path('p'), core))[1], 'TypeError')

    def test_live_path_changes_and_deferred_hash(self):
        core = Core({'value': 'a'})
        reader = composition.build_project_context_snapshot_read_service(Path('p'), core)
        self.assertEqual(reader.load(), {'value': 'a'})
        core.paths, core.document = (Path('other.yaml'), Path('other.md')), {'value': 'b'}
        self.assertEqual(reader.load(), {'value': 'b'})
        self.assertEqual(core.calls, [('path', Path('p')), ('load', Path('snapshot.yaml')),
                                     ('path', Path('p')), ('load', Path('other.yaml'))])
        # This minimal legacy core deliberately has no sha256_file attribute.
        self.assertFalse(hasattr(core, 'sha256_file'))

    def test_read_after_write_same_size_mtime_and_request_isolation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            path = Path(directory) / 'snapshot.yaml'
            path.write_text('value: aa\n', encoding='utf-8')
            reads = []
            def load(source):
                reads.append(source)
                return request_scope.safe_load(source.read_text(encoding='utf-8'))
            core = SimpleNamespace(project_context_snapshot_paths=lambda root: (path, path.with_suffix('.md')), load_yaml_document=load)
            service = composition.build_project_context_service(Path(directory), Path('w'), core)
            stat = path.stat()
            with request_scope.request_scope() as scope:
                first = service.snapshot()
                first['value'] = 'caller mutation'
                self.assertEqual(service.snapshot(), {'value': 'aa'})
                path.write_text('value: bb\n', encoding='utf-8')
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(path.stat().st_size, stat.st_size)
                self.assertEqual(service.snapshot(), {'value': 'bb'})
                self.assertEqual((scope.loads, scope.parses, scope.hits), (3, 2, 1))
            self.assertIsNone(request_scope._CURRENT.get())
            with request_scope.request_scope() as second:
                self.assertEqual(service.snapshot(), {'value': 'bb'})
                self.assertEqual((second.loads, second.parses, second.hits), (1, 1, 0))
            path.write_text('value: [\n', encoding='utf-8')
            with self.assertRaises(Exception):
                with request_scope.request_scope():
                    service.snapshot()
            self.assertIsNone(request_scope._CURRENT.get())
            self.assertEqual(len(reads), 5)

    def test_runtime_snapshot_uses_injected_document(self):
        memory = MemorySnapshots()
        core = Core()
        service = composition.build_project_context_service(Path('p'), Path('w'), core, snapshots=memory)
        with patch.object(garage, 'snapshot_with_resolved_search_roots', return_value={'runtime': 'same'}) as resolve:
            self.assertEqual(service.runtime_snapshot(), {'runtime': 'same'})
            resolve.assert_called_once_with(Path('p'), memory.document, Path('w'), core)
        self.assertFalse(core.calls)

    def test_context_payload_broken_branch_and_scope_cleanup(self):
        constructors = [garage.ProjectContextService]
        if BASELINE:
            constructors.insert(0, BASELINE['ProjectContextService'])
        for broken in [False, True]:
            for failure in [False, True]:
                results = []
                for constructor in constructors:
                    core = Core({'unknown': ['kept']})
                    core.project_id = lambda root: 'p'
                    core.locate_flow_root = lambda root: Path('.pf')
                    core.project_context_check_result = lambda *a, **k: {'broken': broken, 'status': 'broken' if broken else 'fresh', 'snapshot_id': 's'}
                    seen = []
                    def readiness(*, snapshot, check):
                        self.assertIsNotNone(request_scope._CURRENT.get())
                        seen.append(copy.deepcopy(snapshot))
                        if failure:
                            raise ValueError('readiness-error')
                        return {'status': 'ready', 'resource_count': 1}
                    replacements = {
                        'ResourceSearchService': lambda *a: SimpleNamespace(readiness=readiness),
                        'CurrentWorkService': lambda *a: SimpleNamespace(summary=lambda: {'active_work': []}),
                        'resource_selection_summary': lambda snapshot: {'document': snapshot},
                        'diagnostics_from_check': lambda *a: [],
                        'fresh_session_continuation': lambda *a: {'id': 'continued'},
                    }
                    process_result = lambda snapshot, manifest, **k: {'snapshot': snapshot, 'manifest': manifest}
                    process_service = lambda *a, **k: SimpleNamespace(summary=process_result)
                    mode_service = lambda *a, **k: SimpleNamespace(status=lambda **k: {'mode': 'garage', 'session': {'id': k['session_id']}})
                    report_service = lambda *a, **k: SimpleNamespace(status=lambda **k: {'status': 'same', 'document': k['snapshot']})
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(reports, 'DerivedReportLifecycleService', side_effect=report_service))
                        stack.enter_context(patch.object(summary, 'ProcessSummaryReadService', side_effect=process_service))
                        stack.enter_context(patch.object(mode, 'GarageModeService', side_effect=mode_service))
                        stack.enter_context(patch.dict(garage.__dict__, replacements))
                        if BASELINE:
                            stack.enter_context(patch.dict(BASELINE, {**replacements, 'GarageModeService': mode_service, 'DerivedReportLifecycleService': report_service, 'process_summary': process_result}))
                        result = outcome(lambda: constructor(Path('p'), Path('w'), core).context(session_id='session'))
                    self.assertIsNone(request_scope._CURRENT.get())
                    self.assertEqual(seen, [{}] if broken else [{'unknown': ['kept']}])
                    self.assertEqual(sum(row[0] == 'path' for row in core.calls), 0 if broken else 1)
                    results.append((result, core.calls))
                self.assertTrue(all(result == results[0] for result in results))
                if not failure:
                    self.assertEqual(results[0][0][1]['work']['recommendation'], 'continue_from_handoff')
                else:
                    self.assertEqual(results[0][0], ('error', 'ValueError', ('readiness-error',)))

    def test_mcp_factory_after_guards_and_existing_projection(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from pf_runtime import mcp_server, session_read
        calls = []
        context = {'project': {'id': 'p'}, 'work': {'active_work': []}, 'context': {'status': 'fresh'}, 'session': {'id': 's'}}
        service = SimpleNamespace(context=lambda **k: copy.deepcopy(context), snapshot=lambda: {'knowledge_resources': {'selected': [{'id': 'fixture.knowledge:root'}]}})
        core = SimpleNamespace(project_id=lambda root: str(root))
        host = SimpleNamespace(resolve_project=lambda reference, core: Path(reference),
                               project_for_session=lambda *a: Path('bound'))
        runtime = SimpleNamespace(host=host, core=core)
        def factory(root, workplace, given_core):
            calls.append((root, workplace, given_core))
            return service
        with patch.object(composition, 'build_project_context_service', side_effect=factory), patch.object(composition, 'build_process_execution_service', return_value=SimpleNamespace(state=lambda **k: {'action': 'start_recommended'})):
            for name in ['pf.context', 'pf.work_state']:
                for arguments, session, code in [({'project_root': 'bound', 'session_id': 'other'}, 's', 'session_mismatch'),
                                                ({'project_root': 'other'}, 's', 'session_project_mismatch'),
                                                ({}, '', 'missing_project_root')]:
                    with self.assertRaises(session_read.SessionReadError) as caught:
                        mcp_server.tool_result(name, arguments, Path('w'), session, runtime)
                    self.assertEqual(caught.exception.code, code)
                    self.assertFalse(calls)
            result = mcp_server.tool_result('pf.work_state', {'project_root': 'bound'}, Path('w'), 's', runtime)
            self.assertEqual(result, context)
            result = mcp_server.tool_result('pf.context', {'project_root': 'bound'}, Path('w'), 's', runtime)
            self.assertEqual(result['resources']['authorized_knowledge_ids'], ['fixture.knowledge:root'])
            self.assertEqual(result['work']['current'], {'action': 'start_recommended'})
            self.assertEqual(result['project'], context['project'])
        self.assertEqual(len(calls), 2)
        self.assertIsNone(request_scope._CURRENT.get())

    def test_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'src/processforge_core', root / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            code = "from pathlib import Path; from types import SimpleNamespace; from processforge_core.composition import build_project_context_service; core=SimpleNamespace(project_context_snapshot_paths=lambda root:(Path('s'),Path('m')),load_yaml_document=lambda path:{'value':1}); assert build_project_context_service(Path('p'),Path('w'),core).snapshot()=={'value':1}"
            environment = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=root, capture_output=True, text=True, env=environment)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    args = parser.parse_args()
    if args.baseline:
        BASELINE = dict(garage.__dict__)
        exec(compile(args.baseline.read_text(encoding='utf-8'), str(args.baseline), 'exec'), BASELINE)
    if args.scratch_root:
        args.scratch_root.mkdir(parents=True, exist_ok=True)
        SCRATCH = args.scratch_root
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GarageSnapshotTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
