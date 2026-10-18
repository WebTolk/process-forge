#!/usr/bin/env python3
"""File-backed default resolve qualification and retained-original comparisons."""
from __future__ import annotations

import argparse
import ast
import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Protocol
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core.resources import access
from processforge_core.resources.snapshot import selected_resource
from processforge_core.common import request_scope
from processforge_core.ports import ProjectSnapshotReadPort
from processforge_core.project.snapshot import load_snapshot
from processforge_core.work.context_documents import ContextContractInputs

BASELINE = None
SCRATCH = None
COMPARISONS = 0

LEGACY_FUNCTIONS = {
    'resolve_workspace_path_ref', 'normalize_workplace_manifest',
    'workspace_registry_specs', 'workplace_registry_entry', 'load_workplace_registry',
    'resolve_registry_path', 'resolve_registry_relative_path', 'workplace_path_resolution',
    'load_workplace_path_constants', 'expand_path_constants', 'resolve_path_with_constants',
    'path_resolution_to_path', 'normalize_path_string', 'locate_flow_root',
    'path_string_is_absolute', 'load_workplace_package_manifest',
    'find_workplace_package_manifests', 'package_path_candidates', 'validate_resource_id',
    'contained_resource_path', 'package_root_entries', 'package_root_resolution_from_entry',
    'resolve_package_root', 'resolve_package_path', 'yaml_error', 'project_id', 'rel',
}
LEGACY_CONSTANTS = {'DEFAULT_PATH_CONSTANTS', 'PATH_CONSTANT_PATTERN', 'RESOURCE_ID_PATTERN', 'WINDOWS_RESERVED_DEVICE_BASENAMES'}


@contextmanager
def fixture_directory():
    # Normal inherited Windows ACLs also work in restricted worker sessions.
    base = Path(SCRATCH if SCRATCH is not None else tempfile.gettempdir()).resolve()
    directory = base / ('pf-resolve-' + uuid.uuid4().hex)
    directory.mkdir()
    try:
        yield directory
    finally:
        directory.resolve().relative_to(base)
        shutil.rmtree(directory)


def original(directory):
    module = ModuleType('retained_resource_resolution')
    sys.modules[module.__name__] = module
    namespace = module.__dict__
    namespace.update(dict(Path=Path, Any=Any, dataclass=dataclass, field=field, re=re, copy=copy,
                     Callable=Callable, Protocol=Protocol,
                     ProjectSnapshotReadPort=ProjectSnapshotReadPort,
                     _context_contract_inputs=ContextContractInputs(),
                     load_yaml_document=ContextContractInputs().load_yaml_document,
                     load_snapshot=load_snapshot, selected_resource=selected_resource,
                     __name__='retained_resource_resolution'))
    for name, wanted in [('processforge.py', LEGACY_FUNCTIONS | LEGACY_CONSTANTS | {'PackageRootResolution'}),
                         ('snapshot.py', {'resolve_garage_path_ref', 'snapshot_with_resolved_search_roots'}),
                         ('access.py', {'ResourceResolveService'})]:
        tree = ast.parse((directory / name).read_text(encoding='utf-8'))
        nodes = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
        for node in tree.body:
            names = {node.name} if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else {target.id for target in node.targets if isinstance(target, ast.Name)} if isinstance(node, ast.Assign) else set()
            if names & wanted:
                nodes.append(node)
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), name, 'exec'), namespace)
    return namespace


def write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')


def outcome(call):
    try:
        return ('return', call())
    except (Exception, SystemExit) as exc:
        return ('error', type(exc).__name__, str(exc))


def fixture(root):
    project, workplace = root / 'Project Test', root / 'workplace'
    project.mkdir()
    workplace.mkdir()
    write(project / '.pf/process-forge.yaml', {'project': {'id': 'opaque/Project:42'}, 'unknown': [1]})
    write(workplace / 'workplace.yaml', {'path_constants': {'DOCS': 'docs'}, 'registries': {'tools': 'custom/tools.yaml'}})
    (workplace / 'docs').mkdir()
    (root / 'outside').mkdir()
    write(workplace / 'registries/knowledge-roots.yaml', {'knowledge_roots': [None, {'id': 'local', 'path': '${DOCS}', 'opaque': [1]}, {'id': 'outside', 'path': str(root / 'outside')}]})
    write(workplace / 'registries/private-resource-paths.yaml', {'private_resource_paths': [{'id': 'private', 'path': str(root / 'outside')}]})
    write(workplace / 'custom/tools.yaml', {'tools': [{'id': 'descriptor', 'description': 'kept', 'unknown': {'x': 2}}, {'id': 'local', 'path': 'docs'}, {'id': 'outside', 'path': str(root / 'outside')}]})
    write(project / '.pf/packages/local.pkg/package.yaml', {'id': 'local.pkg'})
    write(workplace / 'packages/flat.pkg.yaml', {'id': 'flat.pkg'})
    write(workplace / 'packages/work.pkg/package.yaml', {'id': 'work.pkg'})
    write(project / '.pf/artifacts/report.md', {'content': 'fixture'})
    return project, workplace


def refs():
    return [
        {}, {'registry': 'external_resources', 'url': 'https://example.invalid/doc'},
        {'package': 'self'}, {'package': 'self', 'relative_path': '.pf'},
        {'package': 'self', 'relative_path': '../outside'},
        {'package': 'local.pkg'}, {'package': 'local.pkg', 'relative_path': 'missing'},
        {'package': 'local.pkg', 'relative_path': '../escape'},
        {'package': 'work.pkg'}, {'package': 'flat.pkg'}, {'package': 'absent.pkg'},
        {'package': 'project.fixture', 'relative_path': 'artifacts/report.md'},
        {'package': 'project.fixture', 'relative_path': 'missing'},
        {'package': 'project.fixture', 'relative_path': '../escape'},
        {'package': 'BAD'}, {'package': '../bad'}, {'package': 'con'},
        {'registry': 'knowledge_roots', 'id': 'local'},
        {'registry': 'knowledge_roots', 'id': 'outside'},
        {'registry': 'knowledge_roots', 'id': 'local', 'relative_path': '../escape'},
        {'registry': 'knowledge_roots', 'id': 'local', 'relative_path': 'absent'},
        {'registry': 'tools', 'id': 'local'}, {'registry': 'tools', 'id': 'descriptor'},
        {'registry': 'tools', 'id': 'outside'},
        {'registry': 'private_resource_paths', 'id': 'private'},
        {'registry': 'unknown', 'id': 'missing'}, {'registry': 'tools'},
    ]


class OriginalReads:
    def __init__(self, project, workplace):
        self.project, self.workplace = project, workplace
        self.core = SimpleNamespace(**BASELINE)

    def project_id(self):
        return BASELINE['project_id'](self.project)

    def read_snapshot(self, snapshots):
        return load_snapshot(self.project, snapshots=snapshots)

    def path_ref_resolver(self):
        return lambda ref: BASELINE['resolve_garage_path_ref'](self.project, ref, self.workplace, self.core)


class ResolveCoreTests(unittest.TestCase):
    def compare(self, actual, expected):
        global COMPARISONS
        self.assertEqual(actual, expected)
        COMPARISONS += 1

    def test_retained_facade_manifest_configuration(self):
        if BASELINE is None:
            self.skipTest('Use --baseline-dir for retained-original comparisons')
        from processforge_core.resources.snapshot import WorkspacePathReferenceReader
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            custom = workplace / 'custom-workplace.yaml'
            write(custom, {'registries': {'tools': 'custom/alternate-tools.yaml'}})
            write(workplace / 'custom/alternate-tools.yaml', {'tools': [
                {'id': 'descriptor', 'unknown': {'custom': True}},
                {'id': 'local', 'path': 'docs'},
                {'id': 'outside', 'path': str(Path(directory) / 'outside')},
            ]})
            configurations = [
                (workplace, None, workplace / 'workplace.yaml'),
                (None, None, None),
                (workplace, workplace, workplace),
                (workplace, custom, custom),
                (None, custom, custom),
                (workplace, workplace / 'missing.yaml', workplace / 'missing.yaml'),
            ]
            # Isolate the retained facade's unconfigured project binding branch.
            # The production reader receives this binding explicitly from its caller.
            with patch.dict(BASELINE, {'project_workplace_manifest': lambda root: None}):
                for root, configured, old_manifest in configurations:
                    reader = WorkspacePathReferenceReader(project, root, workplace_manifest=configured)
                    for ref in refs():
                        with self.subTest(root=root, manifest=configured, ref=ref):
                            self.compare(
                                outcome(lambda: reader.resolve(ref)),
                                outcome(lambda: BASELINE['resolve_workspace_path_ref'](
                                    project, ref, workplace_manifest=old_manifest)),
                            )
            unconfigured = WorkspacePathReferenceReader(project, None)
            self.assertEqual(unconfigured.resolve({'registry': 'tools', 'id': 'local'}),
                             {'status': 'unresolved', 'reason': 'workplace manifest is not configured'})
            self.assertEqual(WorkspacePathReferenceReader(project, None, workplace_manifest=custom).resolve(
                {'registry': 'tools', 'id': 'descriptor'}),
                {'status': 'descriptor', 'entry': {'id': 'descriptor', 'unknown': {'custom': True}}})

    def test_retained_path_algorithms(self):
        if BASELINE is None:
            self.skipTest('Use --baseline-dir for retained-original comparisons')
        from processforge_core.resources.snapshot import resolve_garage_path_ref, snapshot_with_resolved_search_roots
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            old = OriginalReads(project, workplace)
            for ref in refs():
                with self.subTest(ref=ref):
                    self.compare(outcome(lambda: resolve_garage_path_ref(project, ref, workplace)), outcome(lambda: old.path_ref_resolver()(ref)))
            for constants in ({'DOCS': 'docs'}, {'DOCS': ''}, {'DOCS': '${UNKNOWN}'}, {'DOCS': '${LOOP}', 'LOOP': '${DOCS}'}, {'DOCS': '${PF_WORKPLACE}/docs'}):
                write(workplace / 'workplace.yaml', {'path_constants': constants, 'registries': {'tools': 'custom/tools.yaml'}})
                ref = {'registry': 'knowledge_roots', 'id': 'local'}
                self.compare(outcome(lambda: resolve_garage_path_ref(project, ref, workplace)), outcome(lambda: old.path_ref_resolver()(ref)))
            for entries in ([], [{'id': 'main', 'path': 'packages', 'default': True}], [{'id': 'bad', 'path': '${UNKNOWN}'}, {'id': 'main', 'path': 'packages', 'status': 'disabled'}], [{'id': 'first', 'path': 'packages'}, {'id': 'duplicate', 'path': 'packages'}]):
                write(workplace / 'registries/package-roots.yaml', {'package_roots': entries})
                for package in ('work.pkg', 'flat.pkg', 'absent.pkg'):
                    ref = {'package': package}
                    self.compare(outcome(lambda: resolve_garage_path_ref(project, ref, workplace)), outcome(lambda: old.path_ref_resolver()(ref)))
            snapshot = {'local_search_resources': [None, {'id': 'x', 'path_ref': {'package': 'self'}}, {'id': 'y', 'path_ref': {'package': 'project.fixture', 'relative_path': 'missing'}}], 'unknown': {'x': [1]}}
            before = copy.deepcopy(snapshot)
            self.compare(snapshot_with_resolved_search_roots(project, snapshot, workplace), BASELINE['snapshot_with_resolved_search_roots'](project, snapshot, workplace, old.core))
            self.assertEqual(snapshot, before)

    def test_retained_payloads(self):
        if BASELINE is None:
            self.skipTest('Use --baseline-dir for retained-original comparisons')
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            actual = access.ResourceResolveService(project, workplace)
            previous = BASELINE['ResourceResolveService'](project, workplace, OriginalReads(project, workplace))
            for ref in refs():
                write(project / '.pf/contexts/project-context.snapshot.yaml', {'resolved': {'knowledge_resources': [{'id': 'root', 'path_ref': ref, 'application': {'kept': True}, 'unknown': [1]}]}})
                for identifier in (None, '', 'absent', 'root'):
                    self.compare(outcome(lambda: actual.resolve(resource_id=identifier)), outcome(lambda: previous.resolve(resource_id=identifier)))

    def test_empty_and_denied_do_not_resolve_or_read_snapshot(self):
        from processforge_core.resources.resolve_read import ResourceResolveReadService
        project, workplace = Path('project'), Path('workplace')
        def fail(*args, **kwargs):
            self.fail('Unexpected snapshot or path access')
        with patch.object(ResourceResolveReadService, 'project_id', return_value='id'), patch.object(ResourceResolveReadService, 'read_snapshot', side_effect=fail), patch.object(ResourceResolveReadService, 'path_ref_resolver', side_effect=fail):
            service = access.ResourceResolveService(project, workplace)
            for identifier in (None, ''):
                self.assertNotIn('resource', service.resolve(resource_id=identifier))
        with patch.object(ResourceResolveReadService, 'project_id', return_value='id'), patch.object(ResourceResolveReadService, 'read_snapshot', return_value={}), patch.object(ResourceResolveReadService, 'path_ref_resolver', side_effect=fail):
            self.assertEqual(access.ResourceResolveService(project, workplace).resolve(resource_id='unknown')['resource']['reason'], 'not_in_project_snapshot')

    def test_default_constructor_no_io_and_failure_order(self):
        from processforge_core.resources.resolve_read import ResourceResolveReadService
        def fail(*args, **kwargs):
            self.fail('Construction or rejected operation attempted a later read')
        with patch.object(Path, 'is_file', side_effect=fail), patch.object(Path, 'exists', side_effect=fail):
            service = access.ResourceResolveService(Path('p'), Path('w'))
        self.assertIsInstance(service.reads, ResourceResolveReadService)
        with patch.object(ResourceResolveReadService, 'project_id', side_effect=ValueError('project-error')), patch.object(ResourceResolveReadService, 'read_snapshot', side_effect=fail), patch.object(ResourceResolveReadService, 'path_ref_resolver', side_effect=fail):
            self.assertEqual(outcome(lambda: service.resolve(resource_id='root')), ('error', 'ValueError', 'project-error'))
        with patch.object(ResourceResolveReadService, 'project_id', return_value='id'), patch.object(ResourceResolveReadService, 'read_snapshot', side_effect=OSError('snapshot-error')), patch.object(ResourceResolveReadService, 'path_ref_resolver', side_effect=fail):
            self.assertEqual(outcome(lambda: service.resolve(resource_id='root')), ('error', 'OSError', 'snapshot-error'))

    def test_explicit_falsey_ports_selection_and_metadata(self):
        class Reads:
            def __bool__(self): return False
            def project_id(self): return 'fixture'
            def read_snapshot(self, snapshots): return snapshots.load()
            def path_ref_resolver(self): return lambda ref: {'status': 'descriptor', 'entry': {'unknown': 42}}
        class Snapshots:
            def __bool__(self): return False
            def load(self): return {'resolved': {'knowledge_resources': [{'instance_id': 'alias', 'path_ref': {'registry': 'tools', 'id': 'd'}, 'application': {'unknown': [1]}}]}, 'local_search_resources': [{'id': 'alias', 'path': 'second'}]}
        reads, snapshots = Reads(), Snapshots()
        service = access.ResourceResolveService(Path('p'), Path('w'), reads, snapshots=snapshots)
        self.assertIs(service.reads, reads)
        self.assertIs(service.snapshots, snapshots)
        result = service.resolve(resource_id='alias')['resource']
        self.assertEqual(result['application'], {'unknown': [1]})
        self.assertEqual(result['resolution_status'], 'descriptor')
        self.assertEqual(result['reference'], {'registry': 'tools', 'id': 'd'})

    def test_live_same_metadata_and_request_isolation(self):
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            path = project / '.pf/contexts/project-context.snapshot.yaml'
            doc = {'local_search_resources': [{'id': 'root', 'path': 'aa', 'application': {'marker': 'aa'}}], 'unknown': [42]}
            write(path, doc)
            stat = path.stat()
            service = access.ResourceResolveService(project, workplace)
            with request_scope.request_scope():
                result = service.resolve(resource_id='root')
                result['resource']['application']['marker'] = 'changed'
                self.assertEqual(service.resolve(resource_id='root')['resource']['application']['marker'], 'aa')
                write(path, {'local_search_resources': [{'id': 'root', 'path': 'bb', 'application': {'marker': 'bb'}}], 'unknown': [42]})
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(path.stat().st_size, stat.st_size)
                self.assertEqual(service.resolve(resource_id='root')['resource']['reference'], 'bb')
            self.assertIsNone(request_scope._CURRENT.get())
            with request_scope.request_scope():
                self.assertEqual(service.resolve(resource_id='root')['resource']['application']['marker'], 'bb')
            path.unlink()
            self.assertEqual(service.resolve(resource_id='root')['resource']['status'], 'denied')
            path.write_text('broken: [', encoding='utf-8')
            self.assertEqual(service.resolve(resource_id='root')['resource']['status'], 'denied')
            write(path, doc)
            self.assertEqual(service.resolve(resource_id='root')['resource']['reference'], 'aa')
            write(project / '.pf/process-forge.yaml', {'project': {'id': 'changed'}})
            self.assertEqual(service.resolve()['project']['id'], 'changed')

    def test_real_registry_live_metadata(self):
        from processforge_core.resources.snapshot import WorkspacePathReferenceReader
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            reader = WorkspacePathReferenceReader(project, workplace)
            ref = {'registry': 'tools', 'id': 'descriptor'}
            self.assertEqual(reader.resolve(ref), {'status': 'descriptor', 'entry': {'id': 'descriptor', 'description': 'kept', 'unknown': {'x': 2}}})
            write(workplace / 'custom/tools.yaml', {'tools': [{'id': 'descriptor', 'path': 'docs'}]})
            self.assertEqual(reader.resolve(ref)['status'], 'resolved')
            registry = workplace / 'custom/tools.yaml'
            stat = registry.stat()
            (workplace / 'more').mkdir()
            with request_scope.request_scope():
                self.assertEqual(Path(reader.resolve(ref)['path']).name, 'docs')
                write(registry, {'tools': [{'id': 'descriptor', 'path': 'more'}]})
                os.utime(registry, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual(registry.stat().st_size, stat.st_size)
                self.assertEqual(Path(reader.resolve(ref)['path']).name, 'more')
                self.assertEqual(reader.resolve(ref)['status'], 'resolved')
            self.assertIsNone(request_scope._CURRENT.get())
            (workplace / 'more').rmdir()
            self.assertEqual(reader.resolve(ref)['status'], 'missing')
            write(registry, {'tools': [{'id': 'descriptor', 'path': 'docs'}]})
            (workplace / 'docs').rmdir()
            self.assertEqual(reader.resolve(ref)['status'], 'missing')

    def test_copied_core_default_without_cli_host(self):
        with fixture_directory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'src/processforge_core', root / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            project, workplace = fixture(root)
            write(project / '.pf/contexts/project-context.snapshot.yaml', {'local_search_resources': [{'id': 'root', 'path_ref': {'package': 'self', 'relative_path': '.pf'}}]})
            code = '''import importlib.abc, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
class NoTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'processforge' or fullname.startswith(('tools', 'pf_runtime', 'pf_cli')):
            raise AssertionError('Unexpected transport import: ' + fullname)
sys.meta_path.insert(0, NoTransport())
from processforge_core.resources.access import ResourceResolveService
from processforge_core.resources.resolve_read import ResourceResolveReadService
from processforge_core.resources.snapshot import WorkspacePathReferenceReader
p, w = Path(sys.argv[2]), Path(sys.argv[3])
s = ResourceResolveService(p, w)
assert isinstance(s.reads, ResourceResolveReadService)
assert s.resolve()['project']['id'] == 'opaque/Project:42'
assert s.resolve(resource_id='absent')['resource']['status'] == 'denied'
assert s.resolve(resource_id='root')['resource']['local_root'] == str((p / '.pf').resolve())
assert WorkspacePathReferenceReader(p, None).resolve({'package': 'self'})['path'] == str(p.resolve())
assert WorkspacePathReferenceReader(p, None).resolve({'registry': 'tools', 'id': 'local'})['reason'] == 'workplace manifest is not configured'
assert WorkspacePathReferenceReader(p, None, workplace_manifest=w / 'workplace.yaml').resolve({'registry': 'tools', 'id': 'descriptor'})['entry']['unknown'] == {'x': 2}
assert not any(x.startswith(('pf_cli', 'pf_runtime', 'tools.')) or x == 'processforge' for x in sys.modules)
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(root), str(project), str(workplace)], cwd=root, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-dir', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    parser.add_argument('--characterize', action='store_true')
    args = parser.parse_args()
    if args.scratch_root:
        args.scratch_root.mkdir(parents=True, exist_ok=True)
        SCRATCH = args.scratch_root
    if args.baseline_dir:
        BASELINE = original(args.baseline_dir)
    if args.characterize:
        if BASELINE is None:
            parser.error('--characterize requires --baseline-dir')
        with fixture_directory() as directory:
            project, workplace = fixture(Path(directory))
            reads = OriginalReads(project, workplace)
            results = [outcome(lambda ref=ref: reads.path_ref_resolver()(ref)) for ref in refs()]
            assert results[1][1]['status'] == 'external'
            assert results[4][1]['reason'] == 'invalid_path_ref: relative_path escapes declared package root'
            assert results[11][1]['status'] == 'resolved'
            assert results[13][1]['reason'] == 'invalid_path_ref: relative_path escapes project flow root'
            assert results[22][1]['entry']['unknown'] == {'x': 2}
            print(json.dumps({'status': 'pass', 'original_path_cases': len(results), 'errors': sum(r[0] == 'error' for r in results)}))
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ResolveCoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'status': 'pass' if result.wasSuccessful() else 'fail', 'tests': result.testsRun, 'retained_comparisons': COMPARISONS, 'skipped': len(result.skipped)}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
