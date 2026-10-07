#!/usr/bin/env python3
"""Snapshot injection, live reads and retained-method behavior parity."""

from __future__ import annotations

import argparse
import copy
from dataclasses import fields
import hashlib
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core import process_execution as execution
from processforge_core.bootstrap import RuntimeBootstrap
from processforge_core.composition import build_process_execution_service, build_project_snapshot_read_service
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.project.snapshot import ProjectSnapshotReadService
from processforge_core.work.context import ContextContractError

BASELINE = None
SCRATCH = None


class MemorySnapshots:
    def __init__(self):
        self.document = {'snapshot': {'id': 'memory'}, 'resolved': {'knowledge_resources': ['z', 'a', 'a']}}
        self.calls = []

    def __bool__(self):
        return False

    def load(self, path=None):
        self.calls.append(('load', path))
        return self.document

    def checksum(self, path):
        self.calls.append(('checksum', path))
        return 'sha256:memory'


class Core:
    def __init__(self, root, document, error=None):
        self.root, self.document, self.error = root, document, error
        self.calls = []

    def locate_flow_root(self, root):
        self.calls.append(('root', root))
        return self.root

    def load_yaml_document(self, path):
        self.calls.append(('load', path))
        if self.error:
            raise self.error('load-error')
        return copy.deepcopy(self.document)


def outcome(call):
    try:
        return ('return', call())
    except (Exception, SystemExit) as exc:
        return ('error', type(exc).__name__, str(exc))


class SnapshotTests(unittest.TestCase):
    def test_construction_and_forwarding_without_io(self):
        fail = lambda *args: self.fail('Construction must not perform I/O')
        core = SimpleNamespace(load_yaml_document=fail, locate_flow_root=fail)
        reader = build_project_snapshot_read_service(core, snapshot_path=fail, sha256_file=fail)
        self.assertIsInstance(reader, ProjectSnapshotReadService)
        memory = MemorySnapshots()
        old = ProcessExecutionService(Path('p'), None, core)
        direct = ProcessExecutionService(Path('p'), None, core, snapshots=memory)
        built = build_process_execution_service(Path('p'), None, core, snapshots=memory)
        boot = RuntimeBootstrap(Path('distribution'), core, None, None).process_execution_service(Path('p'), None, snapshots=memory)
        self.assertIs(built.snapshots, memory)
        self.assertIs(boot.snapshots, memory)
        self.assertEqual(old, direct)
        self.assertEqual(repr(old), repr(direct))
        self.assertEqual(ProcessExecutionService.__match_args__, ('project_root', 'workplace_root', 'core'))
        field = next(item for item in fields(direct) if item.name == 'snapshots')
        self.assertTrue(field.kw_only)
        self.assertFalse(field.compare or field.repr)
        self.assertEqual(inspect.signature(ProcessExecutionService).parameters['snapshots'].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(memory.calls, [])
        self.assertIs(direct._snapshot_reader(), memory)

    def test_injected_pin_and_resources(self):
        reader = MemorySnapshots()
        core = SimpleNamespace(locate_flow_root=lambda root: root / '.pf')
        service = ProcessExecutionService(Path('p'), None, core, snapshots=reader)
        pin = service._process_pin({'id': 'p'}, Path('p/process.yaml'), active_specializations=[], selected_resource_ids=[], allowed_processes=['p'])
        self.assertEqual((pin['snapshot_id'], pin['snapshot_checksum']), ('memory', 'sha256:memory'))
        self.assertEqual(service._selected_resource_ids(), ['a', 'z'])
        path = Path('p/.pf/contexts/project-context.snapshot.yaml')
        self.assertEqual(reader.calls, [('load', path), ('checksum', path), ('load', None)])

    def test_capsule_immutable_guard_before_load_and_capture_injection(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root = Path(folder)
            reader = MemorySnapshots()
            service = ProcessExecutionService(root, None, SimpleNamespace(locate_flow_root=lambda _: root), snapshots=reader)
            path = root / 'contexts/assignment-capsules/a.capsule.yaml'
            path.parent.mkdir(parents=True)
            path.write_text('immutable', encoding='utf-8')
            with self.assertRaises(ContextContractError) as raised:
                service._write_capsule({}, {'id': 'a'}, {})
            self.assertEqual(raised.exception.code, 'immutable_context_exists')
            self.assertEqual(reader.calls, [])
            path.unlink()
            with patch('processforge_core.work.context.build_context_fields', side_effect=RuntimeError('capture-stop')) as capture:
                with self.assertRaisesRegex(RuntimeError, 'capture-stop'):
                    service._write_capsule({}, {'id': 'a'}, {})
                self.assertIs(capture.call_args.args[3], reader.document)
            self.assertEqual(reader.calls, [('load', None)])
            self.assertFalse(path.exists())

    def test_start_preflight_uses_injection_before_capsule(self):
        reader = MemorySnapshots()
        core = SimpleNamespace(now_utc=lambda: 'now', safe_id=lambda *args: 'a',
                               resolve_process_definition=lambda *args: SimpleNamespace(process={'id': 'p'}, path=Path('p.yaml')),
                               validate_assignment_scope_overlaps=lambda *args, **kwargs: {'status': 'pass'})
        service = ProcessExecutionService(Path('p'), None, core, snapshots=reader)
        pin = dict(process_id='p', process_version='1', process_fingerprint='sha256:p', snapshot_id='s', snapshot_checksum='sha256:s')
        with patch.object(ProcessExecutionService, '_context_check', return_value={'status': 'fresh'}), \
             patch.object(ProcessExecutionService, '_find_by_objective', return_value={}), \
             patch.object(ProcessExecutionService, '_project_process_selection', return_value={'allowed': ['p']}), \
             patch.object(ProcessExecutionService, '_select_process', return_value=('p', {})), \
             patch.object(ProcessExecutionService, '_flow_root', return_value=Path('p/.pf')), \
             patch.object(ProcessExecutionService, '_unique_id', return_value='a'), \
             patch.object(ProcessExecutionService, '_manifest', return_value={}), \
             patch.object(ProcessExecutionService, '_selected_resource_ids', return_value=[]), \
             patch.object(ProcessExecutionService, '_process_pin', return_value=pin), \
             patch.object(ProcessExecutionService, '_with_creation_scope', side_effect=lambda assignment, scope: assignment), \
             patch.object(ProcessExecutionService, '_write_capsule', side_effect=AssertionError('Preflight first')), \
             patch.object(execution, 'creation_scope_intent', side_effect=lambda scope: scope), \
             patch.object(execution, 'executable_stages', return_value=[{'id': 's'}]), \
             patch.object(execution, 'initial_stage_id', return_value='s'), \
             patch.object(execution, 'normalized_outcomes', return_value=[]), \
             patch.object(execution, 'project_specialization_selection', return_value={'active': []}), \
             patch('processforge_core.work.context.normalized_assignment_contract', return_value={'scope': {'allowed_actions': []}}), \
             patch('processforge_core.work.context.build_context_fields', side_effect=RuntimeError('preflight-stop')) as capture:
            with self.assertRaisesRegex(RuntimeError, 'preflight-stop'):
                service._start_locked(objective='snapshot slice', scope_intent={'assignment': {}})
            self.assertIs(capture.call_args.args[3], reader.document)
        self.assertEqual(reader.calls, [('load', None)])

    def test_live_reads_and_raw_checksums_equal_size_mtime(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            path = Path(folder) / 'snapshot.yaml'
            path.write_bytes(b'snapshot: {id: a}\n')
            reader = ProjectSnapshotReadService(lambda: path, lambda p: yaml.safe_load(p.read_bytes()),
                                               lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
            stamp = path.stat().st_mtime_ns
            first = reader.checksum(path)
            self.assertEqual(reader.load()['snapshot']['id'], 'a')
            path.write_bytes(b'snapshot: {id: b}\n')
            os.utime(path, ns=(stamp, stamp))
            self.assertEqual(reader.load()['snapshot']['id'], 'b')
            self.assertNotEqual(first, reader.checksum(path))
            self.assertEqual(reader.checksum(path), 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest())
            path.unlink()
            self.assertEqual(reader.checksum(path), '')
            with self.assertRaises(FileNotFoundError):
                reader.load()

    def test_default_path_and_hash_overrides_and_single_pin_path(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root = Path(folder)
            path = root / 'contexts/project-context.snapshot.yaml'
            path.parent.mkdir()
            path.touch()
            core = Core(Path('unused'), {'snapshot': {'id': 's'}})
            service = ProcessExecutionService(Path('p'), None, core)
            with patch.object(ProcessExecutionService, '_flow_root', side_effect=[root, AssertionError('Repeated root')]) as flow, \
                 patch.object(ProcessExecutionService, '_sha256_file', return_value='override') as digest:
                pin = service._process_pin({}, Path('p.yaml'), active_specializations=[], selected_resource_ids=[], allowed_processes=[])
            self.assertEqual(flow.call_count, 1)
            digest.assert_called_once_with(path)
            self.assertEqual(core.calls, [('load', path)])
            self.assertEqual(pin['snapshot_checksum'], 'sha256:override')

    def test_imports_and_isolated_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            target = Path(folder)
            shutil.copytree(ROOT / 'src/processforge_core', target / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            code = """
import sys
from pathlib import Path
from processforge_core.composition import build_process_execution_service
from processforge_core.project.snapshot import ProjectSnapshotReadService
reader = ProjectSnapshotReadService(lambda: Path('unused'), lambda p: {'resolved': {'knowledge_resources': ['b', 'a']}}, lambda p: 'hash')
service = build_process_execution_service(Path('p'), None, object(), snapshots=reader)
assert service._selected_resource_ids() == ['a', 'b']
assert 'processforge' not in sys.modules
assert 'processforge_core._legacy_processforge' not in sys.modules
"""
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=target, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_original_method_differential(self):
        if BASELINE is None:
            self.skipTest('No retained baseline supplied')
        docs = [{}, {'snapshot': None}, {'snapshot': []}, {'snapshot': {'id': 0}},
                {'snapshot': {'id': 's'}, 'resolved': {'knowledge_resources': ['z', 'a', 'a']}},
                {'resolved': []}, {'resolved': {'knowledge_resources': [{'id': 'r'}, 'x']}}, [], None]
        errors = [None, OSError, ValueError, UnicodeError, SystemExit]
        count = 0
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root = Path(folder)
            path = root / 'contexts/project-context.snapshot.yaml'
            path.parent.mkdir()
            for exists in (False, True):
                if exists:
                    path.touch()
                for doc in docs:
                    for error in errors:
                        for hash_error in (False, True):
                            for process in ({'id': 'p', 'future': ['x']}, {'invalid': object()}):
                                left, right = Core(root, doc, error), Core(root, doc, error)
                                calls = []
                                def digest(service, selected):
                                    calls.append(selected)
                                    if hash_error:
                                        raise OSError('hash-error')
                                    return 'raw'
                                kwargs = dict(active_specializations=['x'], selected_resource_ids=['r'], allowed_processes=['p'])
                                with patch.object(ProcessExecutionService, '_sha256_file', digest):
                                    expected = outcome(lambda: BASELINE(Path('p'), None, left)._process_pin(process, Path('external.yaml'), **kwargs))
                                    expected_hash = calls[:]
                                    calls.clear()
                                    actual = outcome(lambda: ProcessExecutionService(Path('p'), None, right)._process_pin(process, Path('external.yaml'), **kwargs))
                                self.assertEqual(expected, actual)
                                self.assertEqual(left.calls, right.calls)
                                self.assertEqual(expected_hash, calls)
                                count += 1
                        left, right = Core(root, doc, error), Core(root, doc, error)
                        expected = outcome(lambda: BASELINE(Path('p'), None, left)._selected_resource_ids())
                        actual = outcome(lambda: ProcessExecutionService(Path('p'), None, right)._selected_resource_ids())
                        self.assertEqual(expected, actual)
                        self.assertEqual(left.calls, right.calls)
                        count += 1
        print('Original snapshot method comparisons:', count)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    args = parser.parse_args()
    SCRATCH = args.scratch_root
    if SCRATCH:
        SCRATCH.mkdir(parents=True, exist_ok=True)
    if args.baseline:
        namespace = dict(vars(execution))
        exec(compile(args.baseline.read_text(encoding='utf-8'), str(args.baseline), 'exec'), namespace)
        BASELINE = namespace['OriginalProcessExecutionService']
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SnapshotTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
