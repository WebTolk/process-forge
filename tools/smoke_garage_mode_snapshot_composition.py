#!/usr/bin/env python3
"""Garage mode snapshot injection and retained-service compatibility."""
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
UNSET = object()
DEFAULT_DOCUMENT = {'workplace_coordination': {'effective_mode': 'simple'}, 'unknown': ['retained']}

def outcome(call):
    try:
        return ('return', call())
    except (Exception, SystemExit) as exc:
        return ('error', type(exc).__name__, getattr(exc, 'code', None), str(exc))

def scenario(service_type, *, document=UNSET, supplied=UNSET, session_id='', error='', snapshots=None, document_path=None):
    events = []
    document = copy.deepcopy(DEFAULT_DOCUMENT if document is UNSET else document)
    def paths(root):
        events.append(('path', str(root)))
        if error == 'path':
            raise OSError('snapshot-path-failure')
        return Path('snapshot.yaml'), Path('snapshot.md')
    def load(path):
        events.append(('load', str(path)))
        if error == 'load':
            raise ValueError('snapshot-load-failure')
        if document_path is not None:
            from processforge_core.request_scope import safe_load
            return safe_load(document_path.read_text(encoding='utf-8'))
        return copy.deepcopy(document)
    core = SimpleNamespace(project_context_snapshot_paths=paths, load_yaml_document=load)
    service = service_type(Path('p'), Path('w'), core, **({'snapshots': snapshots} if snapshots is not None else {}))
    options = {'session_id': session_id}
    if supplied is not UNSET:
        options['snapshot'] = copy.deepcopy(supplied)
    return outcome(lambda: service.status(**options)), events

def context_scenario(service_type, *, document=UNSET, broken=False, memory=None, namespace=None, error=''):
    events = []
    document = copy.deepcopy(DEFAULT_DOCUMENT if document is UNSET else document)
    def load(path):
        events.append(('load', str(path)))
        if path.name == 'snapshot.yaml':
            if error:
                raise OSError('snapshot-error')
            return copy.deepcopy(document)
        return {'manifest': 'retained'}
    core = SimpleNamespace(project_id=lambda root:'fixture', locate_flow_root=lambda root:Path('flow'), project_context_snapshot_paths=lambda root:(Path('snapshot.yaml'),Path('snapshot.md')), load_yaml_document=load, project_context_check_result=lambda *a, **k:{'status':'broken' if broken else 'fresh', 'broken':broken, 'snapshot_id':'fixture', 'policy_action':'continue'})
    substitutes = {'ResourceSearchService': lambda *a:SimpleNamespace(readiness=lambda **kw:{'status':'ready'}), 'CurrentWorkService': lambda *a:SimpleNamespace(summary=lambda:{}), 'DerivedReportLifecycleService': lambda *a:SimpleNamespace(status=lambda **kw:{'status':'ok'}), 'process_summary': lambda *a, **kw:{'process':'same'}, 'resource_selection_summary':lambda *a:{'selection':'same'}, 'fresh_session_continuation':lambda *a:None}
    with ExitStack() as stack:
        for name, value in substitutes.items():
            if namespace is None:
                stack.enter_context(patch.object(garage, name, value))
            else:
                stack.enter_context(patch.dict(namespace, {name:value}))
        result = outcome(lambda: service_type(Path('p'),Path('w'),core, **({'snapshots':memory} if memory is not None else {})).context(session_id='s'))
    return result, events
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
        raise AssertionError('Mode must not hash snapshots')

class ModeSnapshotTests(unittest.TestCase):
    def test_retained_mode_policy_and_errors(self):
        options = [{}, {'session_id':'s'}, {'supplied':{}}, {'supplied':{'unknown':'kept'}, 'error':'load'}, {'document':{}}, {'document':[]}, {'document':None}, {'document':{'workplace_coordination':{'effective_mode':'organized'}}}, {'document':{'workplace_coordination':{'director_required':True}}}, {'document':{'workplace_coordination':{'effective_mode':'organized','director_required':False}}}, {'document':{'workplace_coordination':{'effective_mode':'organized','director_office_exists':True}}}, {'error':'path'}, {'error':'load'}]
        for config in options:
            actual = scenario(garage.GarageModeService, **config)
            if BASELINE:
                self.assertEqual(actual, scenario(BASELINE['GarageModeService'], **config), config)
        for session in ('', 'bound'):
            result, _ = scenario(garage.GarageModeService, session_id=session, document={'workplace_coordination':{'effective_mode':'simple','director_available_at_workplace':True}})
            self.assertEqual(result[1]['mode'], 'garage')
            self.assertFalse(result[1]['blockers'])
        result, _ = scenario(garage.GarageModeService, document={'workplace_coordination':{'effective_mode':'organized'}})
        self.assertEqual(result[1]['blockers'][0]['code'], 'forge_runtime_required_but_unavailable')

    def test_falsey_injection_and_supplied_snapshot_semantics(self):
        memory = MemorySnapshots({'workplace_coordination':{'effective_mode':'organized','director_office_exists':True}, 'unknown':['kept']})
        for supplied in (UNSET, None, {}):
            result, events = scenario(garage.GarageModeService, snapshots=memory, supplied=supplied, error='load')
            self.assertEqual(result[1]['mode'], 'forge')
            self.assertFalse(events)
        self.assertEqual(memory.calls, [None] * 3)
        memory.calls.clear()
        result, events = scenario(garage.GarageModeService, snapshots=memory, supplied={'unknown':'override'}, error='load')
        self.assertEqual(result[1]['mode'], 'garage')
        self.assertFalse(events or memory.calls)
        result, _ = scenario(garage.GarageModeService, snapshots=MemorySnapshots({}))
        self.assertEqual(result[1]['mode'], 'garage')

    def test_constructor_factory_no_io_and_default_substitution(self):
        fail = lambda *a, **k:self.fail('Factory must not call Core')
        core = SimpleNamespace(project_context_snapshot_paths=fail, load_yaml_document=fail)
        memory = MemorySnapshots()
        old = garage.GarageModeService(Path('p'),Path('w'),core)
        built = composition.build_garage_mode_service(Path('p'),Path('w'),core,snapshots=memory)
        self.assertIs(built.snapshots, memory)
        self.assertEqual(old, built)
        self.assertEqual(repr(old), repr(built))
        self.assertEqual(outcome(lambda:hash(old)), outcome(lambda:hash(built)))
        self.assertEqual(old.__match_args__, ('project_root','workplace_root','core'))
        field = next(item for item in fields(built) if item.name == 'snapshots')
        self.assertTrue(field.kw_only)
        self.assertFalse(field.compare or field.repr)
        with self.assertRaises(TypeError):
            garage.GarageModeService(Path('p'),Path('w'),core,memory)
        calls = []
        with patch.object(garage, 'GarageModeService', side_effect=lambda *a:calls.append(a) or 'substitute'):
            self.assertEqual(composition.build_garage_mode_service(Path('p'),Path('w'),core), 'substitute')
        self.assertEqual(calls, [(Path('p'),Path('w'),core)])

    def test_context_consumer_retained_payload_and_fallback(self):
        for config in [{}, {'document':{}}, {'broken':True}, {'broken':True,'error':'load'}, {'document':{'workplace_coordination':{'effective_mode':'organized'}}}]:
            actual = context_scenario(garage.ProjectContextService, **config)
            if BASELINE and 'ProjectContextService' in BASELINE:
                self.assertEqual(actual, context_scenario(BASELINE['ProjectContextService'], namespace=BASELINE, **config), config)
            if not config.get('error'):
                self.assertEqual(actual[0][0], 'return')
            self.assertIsNone(request_scope._CURRENT.get())
        memory = MemorySnapshots({})
        document = {'workplace_coordination':{'effective_mode':'organized'}}
        result, events = context_scenario(garage.ProjectContextService, document=document, memory=memory)
        self.assertEqual(memory.calls, [None])
        self.assertEqual(result[1]['mode'], 'forge')
        self.assertEqual(events, [('load','flow\\process-forge.yaml' if os.name == 'nt' else 'flow/process-forge.yaml'),('load','snapshot.yaml')])
        memory.calls.clear()
        result, events = context_scenario(garage.ProjectContextService, document=document, broken=True, memory=memory)
        self.assertEqual(result[1]['mode'], 'forge')
        self.assertFalse(memory.calls)
        self.assertEqual(len(events), 2)

    def test_real_yaml_live_reads_and_scope_isolation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            path = Path(directory) / 'snapshot.yaml'
            text = 'workplace_coordination: {effective_mode: simple}\nunknown: retained\n'
            path.write_text(text, encoding='utf-8')
            reads = []
            def load(source):
                reads.append(source)
                return request_scope.safe_load(source.read_text(encoding='utf-8'))
            core = SimpleNamespace(project_context_snapshot_paths=lambda root:(path,path.with_suffix('.md')), load_yaml_document=load)
            service = composition.build_garage_mode_service(Path(directory),Path('w'),core)
            stat = path.stat()
            with request_scope.request_scope() as scope:
                first = service.status()
                first['coordination']['effective_mode'] = 'caller-mutation'
                self.assertEqual(service.status()['coordination']['effective_mode'], 'simple')
                path.write_text(text.replace('simple','manual'), encoding='utf-8')
                os.utime(path, ns=(stat.st_atime_ns,stat.st_mtime_ns))
                self.assertEqual(path.stat().st_size, stat.st_size)
                self.assertEqual(service.status()['coordination']['effective_mode'], 'manual')
                self.assertEqual((scope.loads,scope.parses,scope.hits),(3,2,1))
            self.assertIsNone(request_scope._CURRENT.get())
            with request_scope.request_scope() as scope:
                self.assertEqual(service.status()['coordination']['effective_mode'], 'manual')
                self.assertEqual((scope.loads,scope.parses,scope.hits),(1,1,0))
            path.write_text('coordination: [\n', encoding='utf-8')
            with self.assertRaises(Exception):
                with request_scope.request_scope():
                    service.status()
            self.assertIsNone(request_scope._CURRENT.get())
            self.assertEqual(len(reads),5)

    def test_context_calls_factory_with_legacy_arguments(self):
        factory = composition.build_garage_mode_service
        calls = []
        def observed(*args, **kwargs):
            calls.append((args,kwargs))
            return factory(*args, **kwargs)
        with patch.object(composition, 'build_garage_mode_service', side_effect=observed):
            result, _ = context_scenario(garage.ProjectContextService)
        self.assertEqual(result[0], 'return')
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0][0]),3)
        self.assertFalse(calls[0][1])

    def test_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'src/processforge_core', root / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            code = "from pathlib import Path; from processforge_core.composition import build_garage_mode_service; from types import SimpleNamespace; assert build_garage_mode_service(Path('p'),Path('w'),SimpleNamespace()).status(snapshot={'unknown':True})['mode'] == 'garage'"
            result = subprocess.run([sys.executable,'-B','-c',code], cwd=root, capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--context-baseline',type=Path)
    parser.add_argument('--scratch-root',type=Path)
    args = parser.parse_args()
    if args.baseline:
        BASELINE = dict(garage.__dict__)
        exec(compile(args.baseline.read_text(encoding='utf-8'),str(args.baseline),'exec'),BASELINE)
        if args.context_baseline:
            exec(compile(args.context_baseline.read_text(encoding='utf-8'),str(args.context_baseline),'exec'),BASELINE)
    if args.scratch_root:
        args.scratch_root.mkdir(parents=True,exist_ok=True)
        SCRATCH = args.scratch_root
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ModeSnapshotTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1

if __name__ == '__main__':
    raise SystemExit(main())
