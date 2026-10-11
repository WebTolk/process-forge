"""Concrete summary file-backed conformance; optional retained-original parity."""
from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time
import unittest
from unittest.mock import patch
import uuid

parser = argparse.ArgumentParser()
parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--scratch-root', type=Path)
parser.add_argument('--reference', type=Path)
parser.add_argument('--baseline', action='store_true')
OPTIONS, UNITTEST_ARGS = parser.parse_known_args()
ROOT = OPTIONS.project_root.resolve()
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core.process_catalog import summary as summary_module
from processforge_core.process_catalog.catalog_read import ProcessCatalogReadService
from processforge_core.process_catalog.models import ProcessDefinitionRef

ORIGINAL = None
if OPTIONS.reference:
    spec = importlib.util.spec_from_file_location('processforge_core.process_catalog._summary_reference', OPTIONS.reference.resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ORIGINAL = module.ProcessSummaryReadService
if OPTIONS.baseline and ORIGINAL is None:
    parser.error('--baseline requires --reference')

SCRATCH = (OPTIONS.scratch_root or ROOT / '.pf/tmp/oop-parallel-20261011-oop-summary-20261011').resolve()
SCRATCH.relative_to(ROOT / '.pf/tmp')
SCRATCH.mkdir(parents=True, exist_ok=True)
RUN_ROOT = SCRATCH / ('summary-smoke-' + uuid.uuid4().hex)
RUN_ROOT.mkdir()
PARITY_COUNT = 0


def reader(root=None, catalog=None):
    if OPTIONS.baseline:
        resolver = None if root is None else lambda: lambda supplied_root, process_id: (
            catalog if catalog is not None else ProcessCatalogReadService(supplied_root)
        ).resolve_definition(process_id)
        return ORIGINAL(project_root=root, definition_resolver=resolver)
    return summary_module.ProcessSummaryReadService(project_root=root, catalog=catalog)


def reference(root=None, catalog=None):
    resolver = None if root is None else lambda: lambda supplied_root, process_id: (
        catalog if catalog is not None else ProcessCatalogReadService(supplied_root)
    ).resolve_definition(process_id)
    return ORIGINAL(project_root=root, definition_resolver=resolver)


def snapshot(allowed, default='chosen'):
    return {'processes': {'current': {'id': 'current', 'stages': [{}, {}]}, 'selection': {'allowed': allowed, 'default': default}}}


def definition(root, identifier, **fields):
    path = root / '.pf/processes/custom' / (identifier + '.yaml')
    path.parent.mkdir(parents=True, exist_ok=True)
    # JSON is YAML and exercises the actual shared document/parser owner.
    path.write_text(json.dumps({'id': identifier, 'stages': [{'id':'start'}], **fields}, ensure_ascii=False), encoding='utf-8')
    return path


class Port:
    def __init__(self, value=None, error=None):
        self.value = value or {}
        self.error = error
        self.calls = []

    def __bool__(self):
        return False

    def resolve_definition(self, process_id):
        self.calls.append(process_id)
        if self.error:
            raise self.error
        return ProcessDefinitionRef(process_id, Path('fixture.yaml'), self.value, 'fixture', Path('.'), 'canonical', [])


class SummaryConformance(unittest.TestCase):
    def setUp(self):
        self.root = RUN_ROOT / self._testMethodName
        self.root.mkdir()

    def compare(self, snap, manifest=None, root=None, catalog=None):
        global PARITY_COUNT
        actual = reader(root, catalog).summary(copy.deepcopy(snap), copy.deepcopy(manifest))
        if ORIGINAL is not None:
            old = reference(root, catalog).summary(copy.deepcopy(snap), copy.deepcopy(manifest))
            self.assertEqual(actual, old)
            PARITY_COUNT += 1
        return actual

    def test_file_backed_enrichment_order_and_supplied_inputs(self):
        definition(self.root, 'alpha', name='Альфа', purpose='Цель', description='unused', unknown={'x': 1})
        definition(self.root, 'beta', name='', purpose='', description='Описание')
        snap = snapshot(['beta', 'alpha', 'missing', 'alpha'])
        before = copy.deepcopy(snap)
        result = self.compare(snap, {'process':'ignored'}, self.root)
        self.assertEqual(result, {'id':'current', 'stage_count':2, 'default':'chosen', 'allowed':[
            {'id':'beta','title':'beta','purpose':'Описание'},
            {'id':'alpha','title':'Альфа','purpose':'Цель'},
            {'id':'missing','title':'missing','purpose':''},
            {'id':'alpha','title':'Альфа','purpose':'Цель'},
        ]})
        self.assertEqual(snap, before)

    def test_shape_manifest_and_snapshot_precedence_corpus(self):
        manifests = [None, {}, {'process':' alpha '}, {'processes':{'allowed':['alpha','beta','alpha'], 'default':'beta'}}, {'processes':{'allowed':[], 'default':'chosen'}}, {'processes':{'allowed':[{'id':'alpha'},None,0,'beta']}}]
        values = [None, [], '', {}, {'current':[]}, {'current':{'id':0,'stages':'bad'}}, {'current':{'id':77,'stages':[]}}, {'selection':{}}, {'selection':{'allowed':'bad'}}, {'selection':{'allowed':[0,None,False,{'id':'x'},'alpha','alpha'], 'default':0}}, {'selection':{'allowed':['alpha','beta'],'default':'alpha'}}]
        for manifest in manifests:
            for processes in values:
                for root in [None, self.root]:
                    with self.subTest(manifest=manifest, processes=processes, root=root is not None):
                        self.compare({'processes':processes}, manifest, root)
        result = self.compare({'processes':{'selection':{}}}, {'process':'alpha'}, self.root)
        self.assertEqual(result['allowed'], [])
        self.assertEqual(result['default'], '')

    def test_root_none_never_constructs_or_calls_catalog(self):
        port = Port(error=AssertionError('root None must not read'))
        if OPTIONS.baseline:
            result = self.compare(snapshot(['alpha']), root=None, catalog=port)
        else:
            with patch.object(summary_module, 'ProcessCatalogReadService', side_effect=AssertionError('unexpected owner construction')):
                result = self.compare(snapshot(['alpha']), root=None, catalog=port)
        self.assertEqual(port.calls, [])
        self.assertEqual(result['allowed'], [{'id':'alpha','title':'alpha','purpose':''}])

    def test_falsey_port_and_value_fallbacks(self):
        for content in [{'name':0,'purpose':False,'description':31}, {'name':['label'],'purpose':{'x':1}}, {}, {'name':'Title','purpose':'Purpose','description':'unused'}]:
            port = Port(content)
            result = self.compare(snapshot(['alpha', 'beta', 'alpha']), root=self.root, catalog=port)
            self.assertEqual(port.calls[:3], ['alpha','beta','alpha'])
            self.assertEqual(result['allowed'][0]['title'], str(content.get('name') or 'alpha'))
            self.assertEqual(result['allowed'][0]['purpose'], str(content.get('purpose') or content.get('description') or ''))

    def test_only_existing_exceptions_are_swallowed_per_candidate(self):
        for error in [OSError('unavailable'), ValueError('bad'), SystemExit('missing')]:
            port = Port(error=error)
            result = self.compare(snapshot(['alpha','beta']), root=self.root, catalog=port)
            self.assertEqual([x['title'] for x in result['allowed']], ['alpha','beta'])
            self.assertEqual(port.calls[:2], ['alpha','beta'])
        for error in [TypeError('bad'), RuntimeError('bad'), KeyError('bad')]:
            with self.assertRaises(type(error)):
                reader(self.root, Port(error=error)).summary(snapshot(['alpha']))
            if ORIGINAL is not None:
                with self.assertRaises(type(error)):
                    reference(self.root, Port(error=error)).summary(snapshot(['alpha']))

    def test_real_missing_malformed_and_non_mapping_definitions(self):
        path = definition(self.root, 'broken')
        for raw in [b'bad: [unterminated', b'null', b'[]', b'\xff']:
            path.write_bytes(raw)
            result = self.compare(snapshot(['broken','missing']), root=self.root)
            self.assertEqual(result['allowed'], [{'id':'broken','title':'broken','purpose':''}, {'id':'missing','title':'missing','purpose':''}])

    def test_live_create_delete_same_size_same_mtime_and_caller_isolation(self):
        service = reader(self.root)
        snap = snapshot(['live'])
        self.assertEqual(service.summary(snap)['allowed'][0]['title'], 'live')
        path = definition(self.root, 'live', name='First', purpose='one')
        first = service.summary(snap)
        self.assertEqual(first['allowed'][0]['title'], 'First')
        stat = path.stat()
        raw = path.read_bytes().replace(b'First', b'Other')
        self.assertEqual(len(raw), stat.st_size)
        path.write_bytes(raw)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertEqual(service.summary(snap)['allowed'][0]['title'], 'Other')
        first['allowed'][0]['title'] = 'mutated'
        self.assertEqual(service.summary(snap)['allowed'][0]['title'], 'Other')
        path.unlink()
        self.assertEqual(service.summary(snap)['allowed'][0]['title'], 'live')

    def test_project_isolation_and_five_live_operations(self):
        other = self.root / 'other'
        definition(self.root, 'shared', name='First')
        definition(other, 'shared', name='Other')
        first, second = reader(self.root), reader(other)
        durations=[]
        for _ in range(5):
            start = time.perf_counter()
            self.assertEqual(first.summary(snapshot(['shared']))['allowed'][0]['title'], 'First')
            self.assertEqual(second.summary(snapshot(['shared']))['allowed'][0]['title'], 'Other')
            durations.append(round(time.perf_counter()-start, 6))
        print('FIVE_OPERATIONS_SECONDS=' + json.dumps(durations), flush=True)

    @unittest.skipIf(OPTIONS.baseline, 'baseline callback source; concrete default proof after extraction')
    def test_default_copied_core_without_monolith_or_transport(self):
        copy_root = self.root / 'copy'
        shutil.copytree(ROOT / 'src/processforge_core', copy_root / 'src/processforge_core', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        project = copy_root / 'project'
        definition(project, 'copied', name='Copied Core', purpose='Concrete')
        script = textwrap.dedent('''
            import importlib.abc, json, pathlib, sys
            class BlockMonolith(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname == 'processforge' or fullname.startswith(('tools', 'pf_runtime')):
                        raise AssertionError('forbidden dependency: ' + fullname)
            sys.meta_path.insert(0, BlockMonolith())
            sys.path.insert(0, sys.argv[1])
            from processforge_core.process_catalog.summary import ProcessSummaryReadService
            root = pathlib.Path(sys.argv[2])
            service = ProcessSummaryReadService(project_root=root)
            snap = {'processes': {'selection': {'allowed':['copied','missing'], 'default':'copied'}}}
            result = service.summary(snap)
            assert result['allowed'] == [{'id':'copied','title':'Copied Core','purpose':'Concrete'}, {'id':'missing','title':'missing','purpose':''}], result
            path = root / '.pf/processes/custom/copied.yaml'
            path.write_text('{"id":"copied","name":"Next","description":"Live","stages":[{"id":"start"}]}', encoding='utf-8')
            assert service.summary(snap)['allowed'][0] == {'id':'copied','title':'Next','purpose':'Live'}
            assert ProcessSummaryReadService().summary(snap)['allowed'][0]['title'] == 'copied'
            assert not any(name == 'processforge' or name.startswith(('tools.', 'pf_runtime')) for name in sys.modules)
            print('COPIED_CORE_DEFAULT_PASS')
        ''')
        result = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', '-c', script, str(copy_root/'src'), str(project)], cwd=copy_root, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('COPIED_CORE_DEFAULT_PASS', result.stdout)
        print(result.stdout.strip(), flush=True)

    @unittest.skipIf(OPTIONS.baseline, 'source boundary is target of extraction')
    def test_source_has_no_deferred_callback(self):
        source = (ROOT/'src/processforge_core/process_catalog/summary.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertNotIn('definition_resolver', source)
        self.assertNotIn('Callable', source)
        self.assertNotIn('tools.processforge', source)
        self.assertFalse(hasattr(reader(), 'definition_resolver'))


if __name__ == '__main__':
    try:
        program = unittest.main(argv=[sys.argv[0], *UNITTEST_ARGS], verbosity=2, exit=False)
        print('RETAINED_ORIGINAL_COMPARISONS=' + str(PARITY_COUNT), flush=True)
        raise SystemExit(0 if program.result.wasSuccessful() else 1)
    finally:
        # Explicit absolute containment check before recursive workspace cleanup.
        target = RUN_ROOT.resolve()
        target.relative_to(SCRATCH)
        if target == SCRATCH:
            raise RuntimeError('refuse scratch-root removal')
        shutil.rmtree(target)
