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
from processforge_core.work import boundary_advisory
from processforge_core.project.snapshot import ProjectSnapshotReadService
from processforge_core.project.metadata import ProjectMetadataReader

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



class FixtureSnapshots:
    """Injected test port for policy traces; never the production default."""
    def __init__(self, paths, load):
        self.paths, self.read = paths, load

    def load(self, path=None):
        if path is None:
            path, _ = self.paths(Path('p'))
        return self.read(path)

    def checksum(self, path):
        raise AssertionError('Policy snapshot reads must not hash')


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
        reader = composition.build_project_context_snapshot_read_service(Path('p'))
        self.assertIsInstance(reader, ProjectSnapshotReadService)
        memory = MemorySnapshots()
        old = composition.build_project_context_service(Path('p'), Path('w'), core)
        built = composition.build_project_context_service(Path('p'), Path('w'), core, snapshots=memory)
        self.assertFalse(core.calls)
        self.assertEqual(old, built)
        self.assertEqual(repr(old), repr(built))
        self.assertEqual(old.__match_args__, ('project_root', 'workplace_root'))
        dependency = next(field for field in fields(built) if field.name == 'snapshots')
        self.assertTrue(dependency.kw_only)
        self.assertFalse(dependency.compare or dependency.repr)
        self.assertIs(built.snapshot(), memory.document)
        self.assertIs(snapshot.load_snapshot(Path('p'), snapshots=memory), memory.document)
        self.assertEqual(memory.calls, [('load', None)] * 2)
        self.assertFalse(core.calls)
        with self.assertRaises(TypeError):
            composition.build_project_context_service(Path('p'), Path('w'), core, memory)

    def test_default_parity_return_identity_and_errors(self):
        from processforge_core.documents.reader import YamlDocumentReader
        from processforge_core.common.yaml_io import _parse_simple_yaml
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            path = root / '.pf/contexts/project-context.snapshot.yaml'
            path.parent.mkdir(parents=True)
            loader = YamlDocumentReader(_parse_simple_yaml)
            old_core = SimpleNamespace(project_context_snapshot_paths=lambda r: (path, path.with_suffix('.md')), load_yaml_document=loader.load)
            fail = lambda *a: self.fail('Default snapshot read must be owned by Core')
            core = SimpleNamespace(project_context_snapshot_paths=fail, load_yaml_document=fail)
            for raw in (None, b'', b'unknown: {value: [1, 2]}\n', b'null\n', b'[raw]\n', b'raw\n', b'broken: [\n', b'\xef\xbb\xbfvalue: bom\n'):
                if path.exists():
                    path.unlink()
                if raw is not None:
                    path.write_bytes(raw)
                expected = old_load(root, old_core)
                self.assertEqual(snapshot.load_snapshot(root), expected)
                service = composition.build_project_context_service(root, Path('w'), core)
                self.assertEqual(service.snapshot(), expected)
                if 'unknown' in expected:
                    result = service.snapshot()
                    result['unknown']['value'].append('caller mutation')
                    self.assertEqual(service.snapshot(), expected)
        # Raw values and failures remain properties of explicit injected ports.
        for document in (None, ['raw'], 'raw'):
            core = Core(document)
            reader = FixtureSnapshots(core.project_context_snapshot_paths, core.load_yaml_document)
            self.assertIs(snapshot.load_snapshot(Path('p'), snapshots=reader), document)
        for error in (OSError, ValueError, TypeError, SystemExit):
            core = Core(load_error=error)
            reader = FixtureSnapshots(core.project_context_snapshot_paths, core.load_yaml_document)
            self.assertEqual(outcome(lambda: old_load(Path('p'), core)), outcome(lambda: snapshot.load_snapshot(Path('p'), snapshots=reader)))

    def test_live_path_changes_and_deferred_hash(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            path = root / '.pf/contexts/project-context.snapshot.yaml'
            path.parent.mkdir(parents=True)
            path.write_text('value: a\n', encoding='utf-8')
            reader = composition.build_project_context_snapshot_read_service(root)
            with patch.object(type(reader.digests), 'sha256_file', side_effect=AssertionError('Snapshot load must not hash')):
                self.assertEqual(reader.load(), {'value': 'a'})
                other = root / 'other.yaml'
                other.write_text('value: b\n', encoding='utf-8')
                self.assertEqual(reader.load(other), {'value': 'b'})
                self.assertEqual(reader.load(), {'value': 'a'})

    def test_read_after_write_same_size_mtime_and_request_isolation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            path = Path(directory) / '.pf/contexts/project-context.snapshot.yaml'
            path.parent.mkdir(parents=True)
            path.write_text('value: aa\n', encoding='utf-8')
            def load(*args):
                self.fail('Default reader must not call the legacy loader or paths')
            core = SimpleNamespace(project_context_snapshot_paths=load, load_yaml_document=load)
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
                # A new request reloads bytes and reuses the shared parse.
                self.assertEqual((second.loads, second.parses, second.hits), (1, 0, 1))
            path.write_text('value: [\n', encoding='utf-8')
            with request_scope.request_scope():
                self.assertIn('__yaml_error__', service.snapshot())
            self.assertIsNone(request_scope._CURRENT.get())

    def test_runtime_snapshot_uses_injected_document(self):
        memory = MemorySnapshots()
        core = Core()
        service = composition.build_project_context_service(Path('p'), Path('w'), core, snapshots=memory)
        with patch.object(garage, 'snapshot_with_resolved_search_roots', return_value={'runtime': 'same'}) as resolve:
            self.assertEqual(service.runtime_snapshot(), {'runtime': 'same'})
            resolve.assert_called_once_with(Path('p'), memory.document, Path('w'))
        self.assertFalse(core.calls)

    def test_context_payload_broken_branch_and_scope_cleanup(self):
        constructors = [composition.build_project_context_service]
        if BASELINE:
            constructors.insert(0, BASELINE['ProjectContextService'])
        for broken in [False, True]:
            for failure in [False, True]:
                results = []
                for constructor in constructors:
                    core = Core({'unknown': ['kept']})
                    snapshot_load = core.load_yaml_document
                    def load(path):
                        if path.name == 'process-forge.yaml':
                            core.calls.append(('load', path))
                            return {'project': {'id': 'p'}, 'unknown': ['kept']}
                        return snapshot_load(path)
                    metadata = ProjectMetadataReader(Path('p'), SimpleNamespace(load=load))
                    core.project_id = lambda root: metadata.project_id()
                    core.locate_flow_root = lambda root: metadata.flow_root()
                    core.load_yaml_document = load
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
                    }
                    process_result = lambda snapshot, manifest, **k: {'snapshot': snapshot, 'manifest': manifest}
                    process_service = lambda *a, **k: SimpleNamespace(summary=process_result)
                    boundary_result = lambda *a: {'id': 'continued'}
                    boundary_service = lambda *a, **k: SimpleNamespace(read=boundary_result)
                    mode_service = lambda *a, **k: SimpleNamespace(status=lambda **k: {'mode': 'garage', 'session': {'id': k['session_id']}})
                    report_service = lambda *a, **k: SimpleNamespace(status=lambda **k: {'status': 'same', 'document': k['snapshot']})
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(reports, 'DerivedReportLifecycleService', side_effect=report_service))
                        stack.enter_context(patch.object(summary, 'ProcessSummaryReadService', side_effect=process_service))
                        stack.enter_context(patch.object(boundary_advisory, 'FreshSessionBoundaryReadService', side_effect=boundary_service))
                        stack.enter_context(patch.object(mode, 'GarageModeService', side_effect=mode_service))
                        stack.enter_context(patch.object(composition, 'CurrentWorkService', replacements['CurrentWorkService']))
                        stack.enter_context(patch.dict(garage.__dict__, {k:v for k,v in replacements.items() if k != 'CurrentWorkService'}))
                        if BASELINE:
                            stack.enter_context(patch.dict(BASELINE, {**replacements, 'GarageModeService': mode_service, 'DerivedReportLifecycleService': report_service, 'process_summary': process_result, 'fresh_session_continuation': boundary_result}))
                        options = {'snapshots': FixtureSnapshots(core.project_context_snapshot_paths, core.load_yaml_document)}
                        if constructor is composition.build_project_context_service:
                            options['metadata'] = metadata
                        result = outcome(lambda: constructor(Path('p'), Path('w'), core, **options).context(session_id='session'))
                    self.assertIsNone(request_scope._CURRENT.get())
                    self.assertEqual(seen, [{}] if broken else [{'unknown': ['kept']}])
                    self.assertEqual(sum(row[0] == 'path' for row in core.calls), 0 if broken else 1)
                    self.assertEqual(core.calls.count(('load', Path('p') / '.pf/process-forge.yaml')), 1 if failure else 2)
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
            path = root / '.pf/contexts/project-context.snapshot.yaml'
            path.parent.mkdir(parents=True)
            path.write_text('value: 1\n', encoding='utf-8')
            code = "import sys; from pathlib import Path; sys.path.insert(0,str(Path.cwd())); from processforge_core.composition import build_project_context_service; assert build_project_context_service(Path.cwd(),Path('w'),object()).snapshot()=={'value':1}; assert 'processforge_core._legacy_processforge' not in sys.modules"
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], cwd=root, capture_output=True, text=True)
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
