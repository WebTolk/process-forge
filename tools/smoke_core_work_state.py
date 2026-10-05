#!/usr/bin/env python3
"""Work-state policy, composition, observer and adapter compatibility checks."""

from __future__ import annotations

import argparse
import copy
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import io
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from processforge_core import diagnostics as d
from processforge_core import process_execution as execution
from processforge_core.bootstrap import RuntimeBootstrap
from processforge_core.composition import build_process_execution_service
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.work_state import WorkStatePolicy

BASELINE = None
SCRATCH = None
NORMALIZED = {'scope': {'allowed_actions': ['read']},
              'assignment': {'execution_mode': {'kind': 'read_only'}}}


class StateFixture(ProcessExecutionService):
    def _select_work(self, **selectors):
        if self.mode == 'ambiguous':
            raise ValueError('work_selection_ambiguous')
        if self.failure is not None:
            raise self.failure
        return None if self.mode == 'missing' else (self.run, self.assignment)

    def _effective_process(self, run):
        return self.process, 'pinned'

    def _current_evidence(self, assignment):
        return []

    def _accumulated_evidence(self, assignment):
        return []

    def _automation_states(self, process, stage, assignment):
        return []

    def _contract_validation(self, assignment):
        return self.validation

    def _assignment_path(self, assignment_id):
        return self.project_root / '.pf/assignments' / (assignment_id + '.yaml')


def fixture(mode='ready', *, observer=None, project='fixture'):
    core = SimpleNamespace(project_id=lambda path: path.name)
    service = StateFixture(Path(project), None, core, observer=observer)
    values = {
        'mode': mode, 'failure': None, 'run': {'id': 'r', 'status': 'in_progress'},
        'assignment': {'id': 'a', 'stage': 'read', 'status': 'in_progress'},
        'process': {'id': 'p', 'version': '1', 'stages': [{'id': 'read'}]},
        'validation': {'status': 'valid'},
    }
    for key, value in values.items():
        object.__setattr__(service, key, copy.deepcopy(value))
    return service


def logger(profile='normal', *, sinks=None, **options):
    if profile in {'trace', 'diagnostic'}:
        options['expires_at'] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    return d.Logger(d.resolve_config(('invocation', {'profile': profile, **options})), sinks=sinks)


class NormalizedTests(unittest.TestCase):
    def setUp(self):
        self.normalization = patch('processforge_core.work_context.normalized_assignment_contract', return_value=copy.deepcopy(NORMALIZED))
        self.normalization.start()
        self.addCleanup(self.normalization.stop)


class FixtureTests(NormalizedTests):

    def test_ready_shape_and_unknown_fields_preserved(self):
        service = fixture()
        service.run['future'] = {'value': [1]}
        service.assignment['future'] = {'value': [2]}
        before = copy.deepcopy((service.run, service.assignment, service.process))
        state = service.state()
        self.assertEqual(state['action'], 'work_ready')
        self.assertEqual(state['context']['id'], 'a-capsule')
        self.assertEqual(state['stage']['id'], 'read')
        self.assertEqual(state['completion'], {'status': 'complete', 'requirements': []})
        self.assertEqual((service.run, service.assignment, service.process), before)

    def test_missing_and_explicit_selectors(self):
        self.assertEqual(fixture('missing').state()['action'], 'start_recommended')
        for selectors in ({'run_id': 'r'}, {'assignment_id': 'a'}, {'context_id': 'a-capsule'}):
            with self.subTest(selectors=selectors):
                self.assertEqual(fixture('missing').state(**selectors)['reason'], 'work_not_found')

    def test_ambiguity_and_context_guard_before_process_read(self):
        self.assertEqual(fixture('ambiguous').state()['reason'], 'work_selection_ambiguous')
        with patch.object(StateFixture, '_effective_process', side_effect=AssertionError('guard order')):
            self.assertEqual(fixture().state(context_id='wrong')['reason'], 'work_context_mismatch')

    def test_completion_and_stage_override(self):
        service = fixture()
        service.process['stage_completion'] = {'evidence_required': True, 'handoff_note_required': True}
        state = service.state()
        self.assertEqual([x['code'] for x in state['incomplete']], ['stage_evidence_required', 'handoff_note_required'])
        self.assertEqual(state['action'], 'work_incomplete')
        service.process['stages'][0]['stage_completion'] = {}
        self.assertEqual(service.state()['action'], 'work_ready')

    def test_invalid_outcome_remains_incomplete(self):
        service = fixture()
        service.process['stages'][0]['outcomes'] = {'bad': 'unknown'}
        state = service.state()
        self.assertEqual(state['action'], 'work_incomplete')
        self.assertEqual(state['incomplete'][0]['code'], 'invalid_process_definition')
        self.assertEqual(state['allowed_outcomes'], [])

    def test_blockers_and_terminal_precedence(self):
        service = fixture()
        service.assignment['stage_execution'] = {'blockers': [{'code': 'operator'}, 'ignored']}
        service.validation.update(status='blocked', reason='pin_invalid')
        self.assertEqual(service.state()['blockers'], [{'code': 'operator'}, {'code': 'pin_invalid'}])
        for status, action in [('completed', 'run_completed'), ('failed', 'work_terminal'), ('cancelled', 'work_terminal')]:
            service.run['status'] = status
            self.assertEqual(service.state()['action'], action)
        service.assignment['status'] = 'failed'
        service.run['status'] = 'completed'
        self.assertEqual(service.state()['action'], 'work_terminal')

    def test_stage_blocked_fallback_and_default_contract_reason(self):
        service = fixture()
        service.assignment['stage_status'] = 'blocked'
        self.assertEqual(service.state()['blockers'], [{'code': 'stage_marked_blocked', 'stage_id': 'read'}])
        service.validation['status'] = 'blocked'
        self.assertEqual(service.state()['blockers'], [{'code': 'execution_contract_invalid'}])

    def test_permission_readiness_stays_separate(self):
        from processforge_core.work_context import ContextContractError
        with patch('processforge_core.work_context.normalized_assignment_contract', side_effect=ContextContractError('scope_invalid')):
            state = fixture().state()
        self.assertEqual(state['action'], 'work_ready')
        self.assertEqual(state['execution_readiness'], {'status': 'blocked', 'blockers': ['scope_invalid']})

    def test_differential_original_state(self):
        if BASELINE is None:
            self.skipTest('pass --baseline for differential characterization')
        namespace = dict(vars(execution))
        exec(compile(BASELINE.read_text(encoding='utf-8'), str(BASELINE), 'exec'), namespace)
        original = namespace['baseline_state']
        count = 0
        for run_status, assignment_status, blocked, completion in itertools.product(
            ('in_progress', 'completed', 'cancelled', 'failed'),
            ('in_progress', 'done', 'cancelled', 'failed'), (False, True), (False, True),
        ):
            for mode in ('ready', 'missing', 'ambiguous'):
                service = fixture(mode)
                service.run['status'] = run_status
                service.assignment['status'] = assignment_status
                service.assignment['stage_status'] = 'blocked' if blocked else 'in_progress'
                service.process['stage_completion'] = {'evidence_required': completion, 'handoff_note_required': completion}
                for selectors in ({}, {'context_id': 'wrong'}):
                    self.assertEqual(service.state(**selectors), original(service, **selectors))
                    count += 1
        self.assertEqual(count, 384)


class PolicyTests(unittest.TestCase):
    def test_policy_no_io_and_no_mutation(self):
        policy = WorkStatePolicy()
        assignment = {'stage': 'read', 'stage_execution': {'blockers': [{'code': 'operator', 'detail': [1]}]}}
        initial = [{'code': 'existing'}]
        with patch.object(Path, 'read_text', side_effect=AssertionError('no IO')):
            requirements = policy.completion_requirements({'stage_completion': {'evidence_required': True}}, {}, assignment, [], initial)
            decision = policy.decide({}, assignment, {}, requirements)
        self.assertEqual(initial, [{'code': 'existing'}])
        self.assertEqual(decision.action, 'work_blocked')
        decision.blockers[0]['detail'].append(2)
        self.assertEqual(assignment['stage_execution']['blockers'][0]['detail'], [1])

    def test_policy_isolated_import_without_cli_or_host(self):
        script = f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); from processforge_core.work_state import WorkStatePolicy; assert WorkStatePolicy().decide({{}}, {{}}, {{}}, []).action == 'work_ready'; assert 'processforge' not in sys.modules; assert 'pf_runtime.host' not in sys.modules"
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ObserverTests(NormalizedTests):
    def test_profiles_noop_result_and_duration(self):
        expected = fixture().state()
        for profile in ('off', 'normal', 'diagnostic', 'trace'):
            records = []
            observer = logger(profile, sinks=[records.append], spans=1)
            with patch.object(d, 'for_project', side_effect=AssertionError('no implicit file logger')):
                actual = fixture(observer=observer).state(session_id='s')
            self.assertEqual(actual, expected)
            if profile == 'off':
                self.assertEqual(records, [])
            else:
                completed = next(r for r in records if r['code'] == 'work.state.completed')
                self.assertGreaterEqual(completed['context']['duration_ms'], 0)
                for key, value in {'run_id': 'r', 'assignment_id': 'a', 'stage_id': 'read', 'session_id': 's'}.items():
                    self.assertEqual(completed['identity'][key], value)
                self.assertTrue(completed['identity']['request_id'])
            if profile == 'trace':
                self.assertEqual(sum(r['code'].endswith('.span_start') for r in records), 1)
                self.assertTrue(any(r['code'] == 'work.request.yaml' for r in records))
            self.assertIs(d.current(), d.NULL)
            self.assertEqual(d._IDENTITY.get(), {})

    def test_validation_trace_span(self):
        records = []
        fixture(observer=logger('trace', sinks=[records.append])).state()
        validation = next(r for r in records if r['code'] == 'work.state.validation.span_end')
        self.assertGreaterEqual(validation['context']['duration_ms'], 0)
        self.assertEqual(validation['identity']['stage_id'], 'read')

    def test_original_exception_and_frozen_exception(self):
        from processforge_core.work_context import ContextContractError
        for exception in (OSError('read failed'), ContextContractError('frozen_failure')):
            records = []
            service = fixture(observer=logger('trace', sinks=[records.append]))
            with patch.object(StateFixture, '_contract_validation', side_effect=exception):
                try:
                    service.state()
                except BaseException as caught:
                    self.assertIs(caught, exception)
                else:
                    self.fail('original failure missing')
            self.assertTrue(any(r['code'] == 'work.state.failed' for r in records))
            self.assertFalse(any(r['code'] == 'work.state.completed' for r in records))
            self.assertIs(d.current(), d.NULL)
            self.assertEqual(d._IDENTITY.get(), {})

    def test_sink_failure_preserves_result_and_exception(self):
        def fail(record):
            raise PermissionError('optional sink unavailable')
        observer = logger(sinks=[fail])
        service = fixture(observer=observer)
        self.assertEqual(service.state(), fixture().state())
        exception = OSError('business failure')
        object.__setattr__(service, 'failure', exception)
        with patch('sys.stderr', io.StringIO()):
            try:
                service.state()
            except OSError as caught:
                self.assertIs(caught, exception)
        self.assertGreater(observer.health['sink_failures'], 0)

    def test_ambient_observer_not_captured_at_construction(self):
        service = fixture()
        records = []
        observer = logger(sinks=[records.append])
        with d.operation(observer, 'test', 'outer', request_id='req', run_id='outer-run', stage_id='outer-stage'):
            identity = dict(d._IDENTITY.get())
            service.state(session_id='s')
            self.assertIs(d.current(), observer)
            self.assertEqual(d._IDENTITY.get(), identity)
        completed = next(r for r in records if r['code'] == 'work.state.completed')
        self.assertEqual(completed['identity']['request_id'], 'req')
        self.assertEqual(completed['identity']['run_id'], 'r')

    def test_reused_observer_threads_and_missing_work_do_not_leak(self):
        records = []
        observer = logger(sinks=[records.append])
        def read(number):
            service = fixture(observer=observer, project='project-' + str(number))
            service.run['id'] = 'run-' + str(number)
            service.assignment['id'] = 'assignment-' + str(number)
            service.state(session_id='session-' + str(number))
            self.assertEqual(d._IDENTITY.get(), {})
            self.assertIs(d.current(), d.NULL)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(read, range(8)))
        completed = [r for r in records if r['code'] == 'work.state.completed']
        self.assertEqual(len({r['identity']['request_id'] for r in completed}), 8)
        for record in completed:
            identity = record['identity']
            number = identity['run_id'].split('-')[1]
            self.assertEqual(identity['session_id'], 'session-' + number)
            self.assertEqual(identity['assignment_id'], 'assignment-' + number)
        fixture('missing', observer=observer).state()
        self.assertIsNone(records[-1]['identity']['run_id'])
        self.assertIsNone(records[-1]['identity']['stage_id'])

    def test_noop_does_not_create_project_files(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            service = fixture(project=str(root))
            for mode in ('ready', 'missing', 'ambiguous'):
                object.__setattr__(service, 'mode', mode)
                service.state(context_id='wrong')
                service.state()
            self.assertEqual(list(root.iterdir()), [])


class CompositionTests(unittest.TestCase):
    def test_constructor_and_factory_no_io(self):
        dependency = object()
        observer = logger(sinks=[])
        with patch.object(Path, 'read_text', side_effect=AssertionError('factory IO')), patch.object(d, 'for_project', side_effect=AssertionError('factory config')):
            first = build_process_execution_service(Path('p'), None, dependency, observer=observer)
            second = build_process_execution_service(Path('p'), None, dependency)
        self.assertIs(first.core, dependency)
        self.assertIs(first.observer, observer)
        self.assertIsNone(second.observer)
        self.assertIsNot(first, second)
        self.assertEqual(first, second)
        self.assertNotIn('observer=', repr(first))
        self.assertEqual(ProcessExecutionService(Path('p'), None, dependency).__match_args__, ('project_root', 'workplace_root', 'core'))

    def test_bootstrap_additive_method_preserves_fields(self):
        core = ModuleType('fake')
        runtime = RuntimeBootstrap(Path('p'), core, ModuleType('host'), ModuleType('service'))
        self.assertEqual([f.name for f in fields(runtime)], ['repo_root', 'core', 'host', 'service'])
        observer = logger(sinks=[])
        service = runtime.process_execution_service(Path('p'), None, observer=observer)
        self.assertIs(service.core, core)
        self.assertIs(service.observer, observer)

    def test_installed_shaped_package_import_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            target = Path(raw) / 'src/processforge_core'
            shutil.copytree(ROOT / 'src/processforge_core', target, ignore=shutil.ignore_patterns('__pycache__'))
            script = f"import sys; sys.path.insert(0, {str(target.parent)!r}); from pathlib import Path; from processforge_core.composition import build_process_execution_service; from processforge_core.work_state import WorkStatePolicy; service=build_process_execution_service(Path('.'), None, object()); assert service.observer is None; assert WorkStatePolicy().decide({{}}, {{}}, {{}}, []).action=='work_ready'; assert 'processforge' not in sys.modules; assert 'pf_runtime.host' not in sys.modules"
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], cwd=target.parent, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class AdapterTests(NormalizedTests):
    def test_cli_factory_and_output_parity(self):
        import processforge as core
        service = fixture()
        manifest = Path('workplace/workplace.yaml')
        with patch.object(core, 'resolve_project_workplace_manifest', return_value=manifest), patch('processforge_core.composition.build_process_execution_service', return_value=service) as factory:
            self.assertIs(core.process_execution_service(Path('fixture')), service)
            factory.assert_called_once_with(Path('fixture'), manifest.parent, core)
        output = io.StringIO()
        records = []
        arguments = SimpleNamespace(project_root='fixture', json=True)
        with d.operation(logger(sinks=[records.append]), 'cli', 'request', request_id='cli-request'), patch.object(core, 'require_flow_root'), patch.object(core, 'process_execution_service', return_value=service), patch('sys.stdout', output):
            self.assertEqual(core.command_work_state(arguments), 0)
        self.assertEqual(json.loads(output.getvalue()), service.state())
        completed = next(r for r in records if r['code'] == 'work.state.completed')
        self.assertEqual(completed['identity']['request_id'], 'cli-request')

    def test_mcp_factory_selectors_and_guard(self):
        from pf_runtime import mcp_server, session_read
        service = fixture()
        core = SimpleNamespace(project_id=lambda path: path.name)
        host = SimpleNamespace(resolve_project=lambda ref, core: Path(ref), project_for_session=lambda args, workplace, core: Path('fixture'))
        runtime = SimpleNamespace(core=core, host=host)
        records = []
        arguments = {'project_root': 'fixture', 'run_id': 'r', 'assignment_id': 'a', 'context_id': 'a-capsule'}
        with d.operation(logger(sinks=[records.append]), 'mcp', 'request', request_id='mcp-request'), patch('processforge_core.composition.build_process_execution_service', return_value=service) as factory:
            state = mcp_server.tool_result('pf.work.state', arguments, Path('workplace'), 'session', runtime)
            self.assertEqual(state, service.state())
            factory.assert_called_once_with(Path('fixture'), Path('workplace'), core)
        completed = next(r for r in records if r['code'] == 'work.state.completed')
        self.assertEqual(completed['identity']['request_id'], 'mcp-request')
        self.assertEqual(completed['identity']['session_id'], 'session')
        with patch('processforge_core.composition.build_process_execution_service', side_effect=AssertionError('guard before factory')):
            with self.assertRaises(session_read.SessionReadError):
                mcp_server.tool_result('pf.work.state', {**arguments, 'session_id': 'other'}, Path('workplace'), 'session', runtime)

    def test_host_factory_shared_payload_and_denied_guard(self):
        from pf_runtime import host
        service = fixture()
        root = Path('fixture')
        records = []
        core = SimpleNamespace(event_runtime_paths=lambda path: (path / 'none.ndjson', path / 'outbox'),
                               json_read=lambda path: {}, supervisor_state_path=lambda path: path / 'supervisor',
                               iter_agent_presence=lambda workplace: [], read_current_project_session=lambda path: {},
                               rel=lambda path, project: path.name)
        with d.operation(logger(sinks=[records.append]), 'runtime', 'request', request_id='host-request'), patch.object(host, 'project_for_session', return_value=root), patch.object(host, 'route_project', return_value={'project_id': 'fixture'}), patch.object(host, 'stage_obligations_payload', return_value={}), patch.object(host, 'active_execution_records', return_value=[]), patch.object(host, 'journal_events', return_value=[]), patch('processforge_core.composition.build_process_execution_service', return_value=service) as factory:
            payload = host.work_state_payload(Path('workplace'), core, session='session')
            self.assertEqual(payload['current_work_state']['process_execution'], service.state())
            factory.assert_called_once_with(root, Path('workplace'), core)
        completed = next(r for r in records if r['code'] == 'work.state.completed')
        self.assertEqual(completed['identity']['request_id'], 'host-request')
        self.assertEqual(completed['identity']['session_id'], 'session')
        with patch.object(host, 'project_for_session', side_effect=ValueError('denied')), patch('processforge_core.composition.build_process_execution_service', side_effect=AssertionError('guard before factory')):
            with self.assertRaisesRegex(ValueError, 'denied'):
                host.work_state_payload(Path('workplace'), core)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    arguments = parser.parse_args()
    BASELINE, SCRATCH = arguments.baseline, arguments.scratch_root
    if SCRATCH is not None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
    suite = unittest.TestSuite()
    for case in (FixtureTests, PolicyTests, ObserverTests, CompositionTests, AdapterTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
