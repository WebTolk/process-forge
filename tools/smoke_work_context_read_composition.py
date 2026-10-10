#!/usr/bin/env python3
"""Context read composition, capsule validation and readiness parity checks."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import hashlib
import itertools
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

import yaml
from processforge_core import diagnostics as d
from processforge_core import process_execution as execution
from processforge_core.bootstrap import RuntimeBootstrap
from processforge_core.composition import build_process_execution_service, build_work_context_read_service
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.common.request_scope import request_scope
from processforge_core.work.context import ContextContractError, SOURCE_LIMITS, assignment_intent, fingerprint
from processforge_core.work.context_read import WorkContextReadService
from processforge_core.work.context_documents import ContextContractInputs

BASELINE = None
SCRATCH = None
NORMALIZED = {'scope': {'allowed_actions': ['read'], 'allowed_read_files': ['src/**']},
              'assignment': {'execution_mode': {'kind': 'read_only'}}}


class MemoryContext:
    def __init__(self):
        self.calls = []
        self.result = {'status': 'valid', 'stage_view': {'id': 'read'}}
        self.normalized = copy.deepcopy(NORMALIZED)

    def __bool__(self):
        return False

    def validation(self, assignment):
        self.calls.append(('validation', assignment['id']))
        return copy.deepcopy(self.result)

    def normalized_assignment(self, assignment):
        self.calls.append(('normalized', assignment['id']))
        return copy.deepcopy(self.normalized)


class MemoryRecords:
    def runs(self):
        yield Path('runs/r/run.yaml'), self.load_run('r')

    def load_run(self, identifier):
        return {'id': 'r', 'status': 'open', 'tasks': [{'id': 'a'}]}

    def load_assignment(self, identifier):
        return {'id': 'a', 'run_id': 'r', 'status': 'open', 'stage': 'read'}


class ReadScenario(ProcessExecutionService):
    def _flow_root(self):
        raise AssertionError('Injected state must not resolve filesystem')

    def _assignment_path(self, identifier):
        raise AssertionError('Injected state must not resolve assignment path')

    def _load_completion_intent(self, run, assignment):
        return None, None

    def _effective_process(self, run):
        return {'id': 'p', 'version': '1', 'stages': [{'id': 'read'}]}, 'pinned'

    def _current_evidence(self, assignment):
        return []

    def _accumulated_evidence(self, assignment):
        return []

    def _automation_states(self, process, stage, assignment):
        return []


def scenario(context=None, observer=None, project='p'):
    return ReadScenario(Path(project), None, SimpleNamespace(project_id=lambda p: p.name),
                        records=MemoryRecords(), context=context, observer=observer)


class CompositionTests(unittest.TestCase):
    def test_constructor_factory_bootstrap_do_not_read(self):
        class NoCore:
            def __getattr__(self, name):
                raise AssertionError('Construction must not access core')
        core, context = NoCore(), MemoryContext()
        reader = build_work_context_read_service(Path('p'))
        self.assertIsInstance(reader, WorkContextReadService)
        service = build_process_execution_service(Path('p'), None, core, context=context)
        self.assertIs(service._context_reader(), context)
        bootstrap = RuntimeBootstrap(Path('distribution'), core, None, None)
        built = bootstrap.process_execution_service(Path('p'), None, context=context)
        self.assertIs(built.context, context)
        original = ProcessExecutionService(Path('p'), None, core)
        self.assertEqual(original, service)
        self.assertEqual(repr(original), repr(service))
        self.assertEqual(original.__match_args__, ('project_root', 'workplace_root', 'core'))
        field = next(field for field in fields(original) if field.name == 'context')
        self.assertTrue(field.kw_only)
        self.assertFalse(field.repr or field.compare)

    def test_imports_do_not_load_monolithic_cli(self):
        code = """from pathlib import Path
import sys
from processforge_core.composition import build_process_execution_service, build_work_context_read_service
reader = build_work_context_read_service(Path('p'))
build_process_execution_service(Path('p'), None, object(), context=reader)
assert 'processforge' not in sys.modules
assert 'processforge_core._legacy_processforge' not in sys.modules
"""
        result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=30,
                                env=dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class InjectedContextTests(unittest.TestCase):
    def test_fake_context_state_requires_no_paths_or_legacy_core(self):
        context = MemoryContext()
        state = scenario(context).state(run_id='r', assignment_id='a', context_id='a-capsule')
        self.assertEqual(state['action'], 'work_ready')
        self.assertEqual(state['execution_readiness']['status'], 'ready')
        self.assertEqual(context.calls, [('validation', 'a'), ('normalized', 'a')])
        state['context']['validation']['stage_view']['id'] = 'mutated'
        self.assertEqual(context.result['stage_view']['id'], 'read')

    def test_context_guard_precedes_injected_callbacks(self):
        context = MemoryContext()
        self.assertEqual(scenario(context).state(context_id='other')['reason'], 'work_context_mismatch')
        self.assertEqual(context.calls, [])

    def test_empty_grants_remain_blocked_separately_from_action(self):
        context = MemoryContext()
        context.normalized['scope'] = {}
        state = scenario(context).state()
        self.assertEqual(state['action'], 'work_ready')
        self.assertEqual(state['execution_readiness']['blockers'], ['read_scope_missing'])

    def test_normalization_error_keeps_original_reason(self):
        context = MemoryContext()
        failure = ContextContractError('assignment_contract_changed')
        with patch.object(context, 'normalized_assignment', side_effect=failure):
            state = scenario(context).state()
        self.assertEqual(state['execution_readiness']['blockers'], [failure.code])

    def test_observer_noop_trace_sink_failure_and_exception_identity(self):
        context = MemoryContext()
        expected = scenario(context).state()
        events = []
        config = d.resolve_config(('invocation', {'profile': 'trace', 'sink': 'none',
                                   'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}))
        service = scenario(context, d.Logger(config, sinks=[events.append]))
        self.assertEqual(service.state(), expected)
        event = next(event for event in events if event['code'] == 'work.state.completed')
        self.assertEqual(event['identity']['assignment_id'], 'a')
        self.assertGreaterEqual(event['context']['duration_ms'], 0)
        def failed_sink(event):
            raise OSError('sink offline')
        broken = scenario(context, d.Logger(config, sinks=[failed_sink]))
        self.assertEqual(broken.state(), expected)
        failure = ContextContractError('forced_context_failure')
        with patch.object(context, 'validation', side_effect=failure):
            with self.assertRaises(ContextContractError) as caught:
                broken.state()
        self.assertIs(caught.exception, failure)
        self.assertIs(d.current(), d.NULL)

    def test_projects_threads_do_not_share_context_or_observer_identity(self):
        def read(project):
            context, events = MemoryContext(), []
            observer = d.Logger(d.resolve_config(('invocation', {'sink': 'none'})), sinks=[events.append])
            state = scenario(context, observer, project).state()
            self.assertEqual(state['project']['id'], project)
            self.assertEqual(context.calls, [('validation', 'a'), ('normalized', 'a')])
            self.assertIs(d.current(), d.NULL)
            return state['project']['id']
        projects = ['one', 'two'] * 10
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(read, projects)), projects)

    def test_original_state_payload_parity(self):
        if BASELINE is None:
            self.skipTest('Use --baseline for original state proof')
        namespace = dict(vars(execution))
        exec(compile(BASELINE.read_text(encoding='utf-8'), str(BASELINE), 'exec'), namespace)
        class BaselineScenario(ReadScenario):
            def _assignment_path(self, identifier):
                return Path('p/.pf/assignments') / (identifier + '.yaml')
        count = 0
        for validation, status, grants, failure in itertools.product(
                ('valid', 'blocked', 'legacy'), ('open', 'done'), (True, False), (True, False)):
            context = MemoryContext()
            context.result = {'status': validation}
            if validation == 'blocked':
                context.result['reason'] = 'work_context_mismatch'
            if not grants:
                context.normalized['scope'] = {}
            records = MemoryRecords()
            original_load = records.load_assignment
            records.load_assignment = lambda identifier: {**original_load(identifier), 'status': status}
            service = BaselineScenario(Path('p'), None, SimpleNamespace(project_id=lambda p: p.name),
                                       records=records, context=context)
            error = ContextContractError('assignment_contract_changed')
            with patch('processforge_core.work.context.normalized_assignment_contract',
                       side_effect=error if failure else lambda *args: copy.deepcopy(context.normalized)), \
                    patch.object(context, 'normalized_assignment',
                                 side_effect=error if failure else lambda *args: copy.deepcopy(context.normalized)):
                expected = namespace['baseline_state'](service)
                self.assertEqual(service.state(), expected)
            count += 1
        print('Original state payload comparisons:', count)


class CapsuleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.flow = self.root / '.pf'
        self.path = self.flow / 'contexts/assignment-capsules/a.capsule.yaml'
        self.assignment = {'id': 'a', 'stage': 'read'}
        self.core = SimpleNamespace(locate_flow_root=lambda p: self.flow)
        self.service = ProcessExecutionService(self.root, None, self.core)

    def write(self, raw):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(raw)

    def validate(self):
        return self.service._contract_validation(self.assignment)

    def test_missing_pinned_and_legacy(self):
        self.assertEqual(self.validate()['status'], 'legacy')
        self.assignment['process_execution'] = {'assignment_capsule': 'declared'}
        self.assertEqual(self.validate()['reason'], 'work_context_unavailable')

    def test_checksums_bom_and_validation_forwarding(self):
        raw = b'\xef\xbb\xbfexecution_contract: {}\nfuture: [1]\n'
        self.write(raw)
        self.assignment['process_execution'] = {'assignment_capsule_checksum': 'sha256:' + hashlib.sha256(raw).hexdigest()}
        with patch('processforge_core.work.context.validate_execution_contract', return_value={'status': 'valid'}) as validator:
            result = self.validate()
            self.assertEqual(result['stage_view']['id'], 'read')
            validator.assert_called_once_with(self.root, self.flow / 'assignments/a.yaml', self.assignment,
                                               {'execution_contract': {}, 'future': [1]}, validator.call_args.args[4], check_sources=False)
            self.assertIsInstance(validator.call_args.args[4], ContextContractInputs)
        self.assignment['process_execution']['assignment_capsule_checksum'] = 'sha256:' + '0' * 64
        with patch('processforge_core.work.context.validate_execution_contract', side_effect=AssertionError('checksum first')):
            self.assertEqual(self.validate()['reason'], 'immutable_context_changed')

    def test_invalid_yaml_unicode_nonmapping_and_oversized(self):
        for raw in (b'value: [', b'\xff', b'null', b'42', b"!!python/object/apply:os.system ['exit']", b' ' * (2 * 1024 * 1024 + 1)):
            with self.subTest(raw_length=len(raw)):
                self.write(raw)
                self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')

    def test_symlink_and_containment_checks_precede_read(self):
        self.write(b'execution_contract: {}')
        with patch.object(Path, 'is_symlink', return_value=True), patch.object(Path, 'read_bytes', side_effect=AssertionError('guard first')):
            self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')
        original = Path.resolve
        def outside(path, *args, **kwargs):
            return self.root / 'outside.yaml' if path == self.path else original(path, *args, **kwargs)
        with patch.object(Path, 'resolve', outside), patch.object(Path, 'read_bytes', side_effect=AssertionError('guard first')):
            self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')

    def test_post_read_size_and_read_error_boundary(self):
        self.write(b'execution_contract: {}')
        with patch.object(Path, 'read_bytes', return_value=b' ' * (2 * 1024 * 1024 + 1)):
            self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('denied')):
            self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')
        failure = PermissionError('stat denied before try')
        with patch.object(Path, 'is_file', side_effect=failure):
            with self.assertRaises(PermissionError) as caught:
                self.validate()
        self.assertIs(caught.exception, failure)

    def test_validator_exception_tuple_remains_exact(self):
        self.write(b'execution_contract: {}')
        for failure in (OSError('io'), ValueError('bad'), TypeError('bad'), AttributeError('bad'), yaml.YAMLError('bad')):
            with patch('processforge_core.work.context.validate_execution_contract', side_effect=failure):
                self.assertEqual(self.validate()['reason'], 'execution_contract_invalid')
        for failure in (KeyError('not caught'), RuntimeError('not caught')):
            with patch('processforge_core.work.context.validate_execution_contract', side_effect=failure):
                with self.assertRaises(type(failure)) as caught:
                    self.validate()
            self.assertIs(caught.exception, failure)

    def test_live_changes_same_metadata_creation_deletion_and_result_isolation(self):
        self.assertEqual(self.validate()['status'], 'legacy')
        self.write(b'execution_contract: {}\nfuture: [1]\n')
        def validator(project, path, assignment, capsule, core, **options):
            return {'status': 'valid', 'future': capsule['future']}
        with patch('processforge_core.work.context.validate_execution_contract', side_effect=validator), request_scope():
            self.validate()['future'].clear()
            self.assertEqual(self.validate()['future'], [1])
            metadata = self.path.stat()
            self.write(b'execution_contract: {}\nfuture: [2]\n')
            os.utime(self.path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            self.assertEqual(self.path.stat().st_size, metadata.st_size)
            self.assertEqual(self.validate()['future'], [2])
            self.path.unlink()
            self.assertEqual(self.validate()['status'], 'legacy')

    def test_default_owns_paths_without_private_callbacks(self):
        self.write(b'execution_contract: {}')
        class CustomPaths(ProcessExecutionService):
            def _flow_root(inner):
                return self.flow
            def _assignment_path(inner, identifier):
                return self.root / 'custom.yaml'
        service = CustomPaths(self.root, None, object())
        with patch('processforge_core.work.context.validate_execution_contract', return_value={'status': 'valid'}) as validator:
            self.assertEqual(service._contract_validation(self.assignment)['status'], 'valid')
            self.assertEqual(validator.call_args.args[1], self.flow / 'assignments/a.yaml')
            self.assertIsInstance(validator.call_args.args[4], ContextContractInputs)
        with patch('processforge_core.work.context.normalized_assignment_contract', return_value=NORMALIZED) as normalizer:
            self.assertEqual(service._context_reader().normalized_assignment(self.assignment), NORMALIZED)
            self.assertEqual(normalizer.call_args.args[1], self.flow / 'assignments/a.yaml')
            self.assertIsInstance(normalizer.call_args.args[3], ContextContractInputs)

    def test_baseline_validation_corpus(self):
        if BASELINE is None:
            self.skipTest('Use --baseline for original validation proof')
        namespace = dict(vars(execution))
        exec(compile(BASELINE.read_text(encoding='utf-8'), str(BASELINE), 'exec'), namespace)
        count = 0
        for raw, checksum, result in itertools.product(
                (None, b'{}', b'null', b'[]', b'42', b'bad: [', b'\xff', b'execution_contract: {}'),
                ('', 'sha256:' + '0' * 64),
                ({'status': 'valid'}, {'status': 'blocked', 'reason': 'work_context_mismatch'})):
            if raw is None:
                if self.path.exists():
                    self.path.unlink()
            else:
                self.write(raw)
            self.assignment['process_execution'] = {'assignment_capsule_checksum': checksum}
            with patch('processforge_core.work.context.validate_execution_contract', side_effect=lambda *args, **kwargs: copy.deepcopy(result)):
                expected = namespace['baseline_contract_validation'](self.service, self.assignment)
                self.assertEqual(self.validate(), expected)
            count += 1
        print('Original capsule validation comparisons:', count)


class DefaultCoreTests(unittest.TestCase):
    def test_real_default_inputs_and_copied_core_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            flow = root / '.pf'
            flow.mkdir()
            manifest = flow / 'process-forge.yaml'
            manifest.write_text('project:\n  id: fixture\n', encoding='utf-8')
            metadata = {'id': 'a', 'run_id': 'r', 'process': 'p', 'stage': 'read',
                        'objective': 'context fixture', 'allowed_actions': [], 'allowed_read_files': [],
                        'required_outputs': [{'id': 'report', 'future': {'tag': 'kept'}}]}
            reader = build_work_context_read_service(root)
            normalized = reader.normalized_assignment(metadata)
            self.assertEqual(normalized['scope']['allowed_actions'], [])
            self.assertEqual(normalized['scope']['allowed_read_files'], [])
            self.assertEqual(normalized['outputs']['required_outputs'][0]['future'], {'tag': 'kept'})
            definition = {'id': 'p', 'version': '1', 'stages': [{'id': 'read'}]}
            process_pin = {'process_id': 'p', 'process_version': '1',
                           'process_fingerprint': fingerprint(definition), 'definition': definition}
            intent = assignment_intent(root, flow / 'assignments/a.yaml', metadata, reader.inputs)
            contract = {'contract_version': 1,
                        'identity': {'kind': 'work', 'project_id': 'fixture', 'assignment_id': 'a', 'run_id': 'r', 'context_id': 'a-capsule'},
                        'assignment_intent': intent, 'assignment_intent_checksum': fingerprint(intent),
                        'snapshot': {'id': 'ctx', 'checksum': 'sha256:' + '0' * 64},
                        'process': {'id': 'p', 'version': '1', 'fingerprint': fingerprint(definition)},
                        'resources': {'selected_ids': [], 'bindings_checksum': fingerprint([])},
                        'scope': intent['scope'], 'outputs': intent['outputs'],
                        'capabilities': {'required': [], 'optional': []}, 'workspace_access': intent['workspace_access'],
                        'parameters': {}, 'coordination': {}, 'source_limits': SOURCE_LIMITS,
                        'readiness': {'status': 'ready', 'blockers': []}, 'required_sources': [],
                        'worker_may_rebuild_context': False}
            contract['contract_checksum'] = fingerprint(contract)
            capsule = {'capsule': {'id': 'a-capsule'}, 'execution_contract': contract,
                       'context_snapshot': {'id': 'ctx', 'sha256': 'sha256:' + '0' * 64},
                       'process_execution': process_pin, 'context': {'selected_resource_ids': []},
                       'resource_bindings': [], 'future': {'tag': 'kept'}}
            path = flow / 'contexts/assignment-capsules/a.capsule.yaml'
            path.parent.mkdir(parents=True)
            raw_capsule = yaml.safe_dump(capsule, sort_keys=False).encode('utf-8')
            path.write_bytes(raw_capsule)
            metadata['process_execution'] = {'assignment_capsule': '.pf/contexts/assignment-capsules/a.capsule.yaml',
                                             'assignment_capsule_checksum': 'sha256:' + hashlib.sha256(raw_capsule).hexdigest()}
            run = {'id': 'r', 'process': 'p', 'tasks': [{'id': 'a'}], 'process_execution': process_pin}
            run_path = flow / 'runs/r/run.yaml'
            run_path.parent.mkdir(parents=True)
            run_path.write_text(yaml.safe_dump(run), encoding='utf-8')
            self.assertEqual(reader.validation(metadata)['status'], 'valid')

            class NoLegacy:
                def __getattr__(self, name):
                    raise AssertionError('Default context read reached legacy: ' + name)

            service = ProcessExecutionService(root, None, NoLegacy())
            self.assertEqual(service._contract_validation(metadata)['status'], 'valid')
            self.assertEqual(service._context_reader().normalized_assignment(metadata), normalized)
            with request_scope():
                stamp = manifest.stat()
                manifest.write_text('project:\n  id: changed\n', encoding='utf-8')
                os.utime(manifest, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                self.assertEqual(manifest.stat().st_size, stamp.st_size)
                self.assertEqual(reader.validation(metadata)['reason'], 'work_context_mismatch')
                manifest.write_text('project:\n  id: fixture\n', encoding='utf-8')
                self.assertEqual(reader.validation(metadata)['status'], 'valid')
            run['tasks'].append({'id': 'a'})
            run_path.write_text(yaml.safe_dump(run), encoding='utf-8')
            self.assertEqual(reader.validation(metadata)['reason'], 'work_identity_mismatch')
            run['tasks'].pop()
            run_path.write_text(yaml.safe_dump(run), encoding='utf-8')
            self.assertEqual(reader.validation(metadata)['status'], 'valid')
            checksum = metadata['process_execution']['assignment_capsule_checksum']
            metadata['process_execution']['assignment_capsule_checksum'] = 'sha256:' + '0' * 64
            self.assertEqual(reader.validation(metadata)['reason'], 'immutable_context_changed')
            metadata['process_execution']['assignment_capsule_checksum'] = checksum
            self.assertEqual(reader.validation({'id': 'missing'})['status'], 'legacy')
            self.assertEqual(reader.validation({'id': 'missing', 'process_execution': {'assignment_capsule': 'pinned'}})['reason'],
                             'work_context_unavailable')

            package = root / 'copied-package'
            shutil.copytree(ROOT / 'src/processforge_core', package / 'processforge_core', ignore=shutil.ignore_patterns('__pycache__'))
            metadata_path = root / 'metadata.yaml'
            metadata_path.write_text(yaml.safe_dump(metadata), encoding='utf-8')
            code = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import yaml
from processforge_core.work.context_read import WorkContextReadService
from processforge_core.work.context_documents import ContextContractInputs
reader = WorkContextReadService(Path(sys.argv[2]))
assert isinstance(reader.inputs, ContextContractInputs)
metadata = yaml.safe_load(Path(sys.argv[3]).read_text(encoding='utf-8'))
assert reader.validation(metadata)['status'] == 'valid'
assert not reader.normalized_assignment(metadata)['scope']['allowed_actions']
assert not any(name == 'processforge' or name.startswith(('pf_cli', 'pf_runtime')) for name in sys.modules)
print('PASS: real copied Core context without CLI/Host')
"""
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(package), str(root), str(metadata_path)],
                                    cwd=package, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    args = parser.parse_args()
    BASELINE, SCRATCH = args.baseline, args.scratch_root
    if SCRATCH is not None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
    suite = unittest.TestSuite()
    for case in (CompositionTests, InjectedContextTests, CapsuleTests, DefaultCoreTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
