#!/usr/bin/env python3
"""Resource resolve snapshot injection and retained-service compatibility."""
from __future__ import annotations
import argparse
from dataclasses import fields
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core import composition, garage, request_scope
BASELINE = None
SCRATCH = None
import copy
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from processforge_core import garage
RESOURCE_ID = 'fixture.knowledge:root'
DEFAULT_DOCUMENT = {'resolved': {'knowledge_resources': [{'id': RESOURCE_ID, 'resource_id': 'root', 'instance_id': RESOURCE_ID + '@current', 'package_id': 'fixture.knowledge', 'kind': 'documentation', 'path_ref': {'registry': 'roots', 'id': 'fixture', 'relative_path': 'docs'}, 'unknown': ['retained']}]}, 'unknown': {'preserved': True}}

def outcome(call):
    try:
        return ('return', call())
    except (Exception, SystemExit) as exc:
        return ('error', type(exc).__name__, getattr(exc, 'code', None), str(exc))

def scenario(service_type, *, document=None, resource_id=RESOURCE_ID, error='', resolution_status='resolved', snapshots=None, namespace=None, document_path=None):
    events = []
    document = copy.deepcopy(DEFAULT_DOCUMENT if document is None else document)
    def project_id(root):
        events.append(('project_id', str(root)))
        if error == 'project_id':
            raise ValueError('project-id-failure')
        return 'fixture-project'
    def paths(root):
        events.append(('path', str(root)))
        if error == 'path':
            raise OSError('snapshot-path-failure')
        return Path('snapshot.yaml'), Path('snapshot.md')
    def load(path):
        events.append(('load', str(path)))
        if error == 'load':
            raise OSError('yaml-load-failure')
        if document_path is not None:
            from processforge_core.request_scope import safe_load
            return safe_load(document_path.read_text(encoding='utf-8'))
        return copy.deepcopy(document)
    def resolve(root, reference, **kw):
        events.append(('resolve', copy.deepcopy(reference), {k:str(v) for k,v in kw.items()}))
        if error == 'resolve':
            raise ValueError('reference-resolution-failure')
        return {'status': resolution_status, 'path': 'fixture-root' if resolution_status == 'resolved' else ''}
    core = SimpleNamespace(project_id=project_id, project_context_snapshot_paths=paths, load_yaml_document=load, resolve_workspace_path_ref=resolve, locate_flow_root=lambda root: root / '.pf')
    service = service_type(Path('p'), Path('w'), core, **({'snapshots': snapshots} if snapshots is not None else {}))
    return outcome(lambda: service.resolve(resource_id=resource_id)), events
class MemorySnapshots:
    def __init__(self, document=None):
        self.document = DEFAULT_DOCUMENT if document is None else document
        self.calls = []
    def __bool__(self):
        return False
    def load(self, path=None):
        self.calls.append(path)
        return self.document
    def checksum(self, path):
        raise AssertionError('Resolve must not hash snapshots')

class ResolveSnapshotTests(unittest.TestCase):
    def test_retained_resolver_and_failure_order(self):
        options = [{}, {'resource_id': None}, {'resource_id': ''}, {'resource_id': 'absent'}, {'resource_id': 'root'}, {'resource_id': RESOURCE_ID + '@current'}, {'resolution_status': 'missing'}, {'resolution_status': 'unresolved'}, {'document': {}}, {'document': []}, *({'error': name} for name in ('project_id', 'path', 'load', 'resolve'))]
        for config in options:
            actual = scenario(garage.ResourceResolveService, **config)
            if BASELINE:
                self.assertEqual(actual, scenario(BASELINE['ResourceResolveService'], **config), config)
            if 'resource_id' in config and not config['resource_id']:
                self.assertEqual([event[0] for event in actual[1]], ['project_id'])
            if config.get('error') == 'project_id':
                self.assertEqual([event[0] for event in actual[1]], ['project_id'])

    def test_selection_order_aliases_and_raw_values(self):
        record = {'id': RESOURCE_ID, 'path': 'first', 'application': {'marker': 'kept'}, 'unknown': [1]}
        document = {'resolved': {'knowledge_resources': [None, 'bad', record]}, 'local_search_resources': [{'id': RESOURCE_ID, 'path': 'second'}], 'unknown': True}
        result, _ = scenario(garage.ResourceResolveService, document=document)
        self.assertEqual(result[1]['resource']['reference'], 'first')
        if BASELINE:
            self.assertEqual((result, _), scenario(BASELINE['ResourceResolveService'], document=document))
        for alias in ('id', 'resource_id', 'instance_id'):
            doc = {'local_search_resources': [{alias: RESOURCE_ID, 'path': 'local', 'package_id': 'fixture', 'kind': 'documentation'}]}
            result, _ = scenario(garage.ResourceResolveService, document=doc)
            self.assertEqual(result[1]['resource']['application'], {'package_id': 'fixture', 'kind': 'documentation'})
            self.assertEqual(result[1]['resource']['reference'], 'local')
        memory = MemorySnapshots(document)
        result, events = scenario(garage.ResourceResolveService, snapshots=memory)
        self.assertIs(result[1]['resource']['application'], record['application'])
        self.assertEqual(memory.calls, [None])
        self.assertFalse(any(event[0] in ('path', 'load') for event in events))
        memory.calls.clear()
        for resource_id in ('', None):
            self.assertEqual(scenario(garage.ResourceResolveService, snapshots=memory, resource_id=resource_id)[0][0], 'return')
        self.assertFalse(memory.calls)
        self.assertEqual(scenario(garage.ResourceResolveService, snapshots=MemorySnapshots({}))[0][1]['resource']['status'], 'denied')

    def test_constructor_factory_without_io(self):
        fail = lambda *a, **k: self.fail('Assembly must not call Core')
        core = SimpleNamespace(project_id=fail, project_context_snapshot_paths=fail, load_yaml_document=fail)
        memory = MemorySnapshots()
        old = garage.ResourceResolveService(Path('p'), Path('w'), core)
        built = composition.build_resource_resolve_service(Path('p'), Path('w'), core, snapshots=memory)
        self.assertIs(built.snapshots, memory)
        self.assertEqual(old, built)
        self.assertEqual(repr(old), repr(built))
        self.assertEqual(outcome(lambda: hash(old)), outcome(lambda: hash(built)))
        self.assertEqual(old.__match_args__, ('project_root', 'workplace_root', 'core'))
        field = next(item for item in fields(built) if item.name == 'snapshots')
        self.assertTrue(field.kw_only)
        self.assertFalse(field.compare or field.repr)
        with self.assertRaises(TypeError):
            garage.ResourceResolveService(Path('p'), Path('w'), core, memory)

    def test_real_yaml_live_reads_and_request_isolation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            path = Path(directory) / 'snapshot.yaml'
            text = 'local_search_resources:\n- id: fixture.knowledge:root\n  path: aa\n  application: {marker: aa}\n'
            path.write_text(text, encoding='utf-8')
            reads = []
            def load(source):
                reads.append(source)
                return request_scope.safe_load(source.read_text(encoding='utf-8'))
            core = SimpleNamespace(project_id=lambda root: 'fixture', project_context_snapshot_paths=lambda root: (path, path.with_suffix('.md')), load_yaml_document=load)
            service = composition.build_resource_resolve_service(Path(directory), Path('w'), core)
            stat = path.stat()
            with request_scope.request_scope() as scope:
                first = service.resolve(resource_id=RESOURCE_ID)['resource']
                first['application']['marker'] = 'mutated'
                self.assertEqual(service.resolve(resource_id=RESOURCE_ID)['resource']['application'], {'marker': 'aa'})
                path.write_text(text.replace('aa', 'bb'), encoding='utf-8')
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(path.stat().st_size, stat.st_size)
                self.assertEqual(service.resolve(resource_id=RESOURCE_ID)['resource']['reference'], 'bb')
                self.assertEqual((scope.loads, scope.parses, scope.hits), (3, 2, 1))
            self.assertIsNone(request_scope._CURRENT.get())
            with request_scope.request_scope() as scope:
                self.assertEqual(service.resolve(resource_id=RESOURCE_ID)['resource']['reference'], 'bb')
                self.assertEqual((scope.loads, scope.parses, scope.hits), (1, 1, 0))
            path.write_text('marker: [\n', encoding='utf-8')
            with self.assertRaises(Exception):
                with request_scope.request_scope():
                    service.resolve(resource_id=RESOURCE_ID)
            self.assertIsNone(request_scope._CURRENT.get())
            self.assertEqual(len(reads), 5)

    def test_mcp_guards_precede_factory(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from pf_runtime import mcp_server, session_read
        status = ['fresh']
        events = []
        def check(root, **kw):
            events.append('check')
            return {'status': status[0]}
        core = SimpleNamespace(project_id=lambda root: str(root), project_context_check_result=check)
        host = SimpleNamespace(resolve_project=lambda reference, core: Path(reference), project_for_session=lambda *a: Path('bound'))
        runtime = SimpleNamespace(core=core, host=host)
        def factory(root, workplace, supplied):
            events.append('factory')
            return SimpleNamespace(resolve=lambda **kw: kw)
        with patch.object(composition, 'build_resource_resolve_service', side_effect=factory):
            for arguments, session, reason in [({'project_root': 'bound', 'session_id': 'other'}, 's', 'session_mismatch'), ({'project_root': 'other'}, 's', 'session_project_mismatch'), ({}, '', 'missing_project_root')]:
                with self.assertRaises(session_read.SessionReadError) as caught:
                    mcp_server.tool_result('pf.resolve', arguments, Path('w'), session, runtime)
                self.assertEqual(caught.exception.code, reason)
                self.assertFalse(events)
            status[0] = 'stale'
            with self.assertRaises(session_read.SessionReadError) as caught:
                mcp_server.tool_result('pf.resolve', {'project_root': 'bound', 'resource_id': RESOURCE_ID}, Path('w'), 's', runtime)
            self.assertEqual(caught.exception.code, 'snapshot_not_fresh')
            self.assertEqual(events, ['check'])
            for accepted in ('fresh', 'fresh_with_updates'):
                status[0] = accepted
                for resource_id, expected in [('', None), (RESOURCE_ID, RESOURCE_ID), (42, '42')]:
                    events.clear()
                    result = mcp_server.tool_result('pf.resolve', {'project_root': 'bound', 'resource_id': resource_id}, Path('w'), 's', runtime)
                    self.assertEqual(result, {'resource_id': expected})
                    self.assertEqual(events, ['check', 'factory'])
        self.assertIsNone(request_scope._CURRENT.get())

    def test_host_keeps_shared_constructor_payload(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from pf_runtime import host as pf_host
        reads = []
        core = SimpleNamespace(project_id=lambda root: 'fixture', project_context_snapshot_paths=lambda root: (Path('snapshot.yaml'), Path('snapshot.md')), load_yaml_document=lambda path: reads.append(path) or copy.deepcopy(DEFAULT_DOCUMENT), resolve_workspace_path_ref=lambda *a, **kw: {'status': 'resolved', 'path': 'fixture-root'})
        with patch.object(pf_host, 'project_for_session', return_value=Path('bound')), patch.object(pf_host, 'route_project', return_value={'id': 'fixture'}):
            call = lambda: pf_host.resolve_payload(Path('w'), core, session='s', resource_id=RESOURCE_ID)
            actual = call()
            self.assertEqual(actual['resource']['navigation'], 'private_runtime_authorized')
            self.assertEqual(len(reads), 1)
            if BASELINE:
                with patch.object(garage, 'ResourceResolveService', BASELINE['ResourceResolveService']):
                    self.assertEqual(call(), actual)
            reads.clear()
            self.assertNotIn('resource', pf_host.resolve_payload(Path('w'), core, session='s'))
            self.assertFalse(reads)
        with patch.object(pf_host, 'project_for_session', side_effect=ValueError('binding-denied')):
            with self.assertRaises(ValueError):
                pf_host.resolve_payload(Path('w'), core, session='s', resource_id=RESOURCE_ID)
            self.assertFalse(reads)

    def test_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'src/processforge_core', root / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            code = "from pathlib import Path; from processforge_core.composition import build_resource_resolve_service; from types import SimpleNamespace; assert build_resource_resolve_service(Path('p'),Path('w'),SimpleNamespace()).resolve() == {'schema_version':1,'kind':'pf.resolve','scope':'project_context','project':{'id':'fixture','root':'p'}}"
            code = code.replace('SimpleNamespace()).resolve()', "SimpleNamespace(project_id=lambda root:'fixture')).resolve()")
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=root, capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1'))
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
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ResolveSnapshotTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
