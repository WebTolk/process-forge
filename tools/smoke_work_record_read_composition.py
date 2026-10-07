#!/usr/bin/env python3
"""Internal Work read composition, live storage and selection compatibility."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import inspect
import itertools
import os
from pathlib import Path
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
from processforge_core.composition import build_process_execution_service
from processforge_core.common import yaml_io
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.request_scope import request_scope
from processforge_core.work.records import YamlWorkRecordReader

BASELINE = None
SCRATCH = None


class MemoryRecords:
    def __init__(self):
        self.run = {'id': 'r', 'status': 'open', 'tasks': [{'id': 'a'}], 'future': {'values': [1]}}
        self.assignment = {'id': 'a', 'run_id': 'r', 'status': 'open', 'stage': 'read',
                           'future': {'values': [2]}}
        self.calls = []

    def __bool__(self):
        return False

    def runs(self):
        self.calls.append(('runs',))
        yield Path('runs/r/run.yaml'), copy.deepcopy(self.run)

    def load_run(self, run_id):
        self.calls.append(('run', run_id))
        return copy.deepcopy(self.run)

    def load_assignment(self, assignment_id):
        self.calls.append(('assignment', assignment_id))
        return copy.deepcopy(self.assignment)


class ReadScenario(ProcessExecutionService):
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

    def _contract_validation(self, assignment):
        return {'status': 'valid'}

    def _assignment_path(self, assignment_id):
        return self.project_root / '.pf/assignments' / (assignment_id + '.yaml')


class CompositionTests(unittest.TestCase):
    def test_factory_bootstrap_construction_performs_no_io(self):
        class UnusableCore:
            def __getattr__(self, name):
                raise AssertionError('No core access during construction: ' + name)
        core = UnusableCore()
        with patch.object(Path, 'is_file', side_effect=AssertionError('No file probe')):
            service = build_process_execution_service(Path('project'), None, core)
            self.assertIsInstance(service.records, YamlWorkRecordReader)
            runtime = RuntimeBootstrap(Path('distribution'), core, None, None)
            records, observer = MemoryRecords(), object()
            injected = runtime.process_execution_service(Path('project'), None, records=records, observer=observer)
            self.assertIs(injected.records, records)
            self.assertIs(injected.observer, observer)

    def test_legacy_positional_fields_and_equality_preserved(self):
        core = object()
        original = ProcessExecutionService(Path('p'), None, core)
        injected = ProcessExecutionService(Path('p'), None, core, records=MemoryRecords())
        self.assertEqual(original, injected)
        self.assertEqual(repr(original), repr(injected))
        self.assertEqual(ProcessExecutionService.__match_args__, ('project_root', 'workplace_root', 'core'))
        record_field = next(f for f in fields(ProcessExecutionService) if f.name == 'records')
        self.assertTrue(record_field.kw_only)
        self.assertFalse(record_field.repr or record_field.compare)
        self.assertEqual(inspect.signature(build_process_execution_service).parameters['records'].kind,
                         inspect.Parameter.KEYWORD_ONLY)

    def test_import_and_injected_records_need_no_monolithic_cli(self):
        code = """from pathlib import Path
import sys
from processforge_core.composition import build_process_execution_service
from processforge_core.process_execution import ProcessExecutionService
class Records:
    def runs(self): return iter([])
    def load_run(self, identifier): return {}
    def load_assignment(self, identifier): return {}
service = build_process_execution_service(Path('p'), None, object(), records=Records())
assert service._work_records(include_historical=True) == []
assert 'processforge' not in sys.modules
assert 'processforge_core._legacy_processforge' not in sys.modules
"""
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class InjectedReadTests(unittest.TestCase):
    def setUp(self):
        self.records = MemoryRecords()
        self.service = ReadScenario(Path('p'), None, SimpleNamespace(project_id=lambda p: p.name), records=self.records)

    def test_falsey_port_selected_and_documents_reread(self):
        selected = self.service._select_work(run_id='r', assignment_id='a')
        self.assertEqual(self.records.calls, [('runs',), ('assignment', 'a'), ('run', 'r'), ('assignment', 'a')])
        self.assertEqual(selected[0]['future'], {'values': [1]})
        selected[1]['future']['values'].clear()
        self.records.assignment['future']['values'].append(3)
        self.assertEqual(self.service._select_work(assignment_id='a')[1]['future']['values'], [2, 3])

    def test_ids_checked_before_reader(self):
        for method in (self.service._load_run, self.service._load_assignment):
            with self.assertRaisesRegex(ValueError, 'unsafe .* id'):
                method('../outside')
        with self.assertRaisesRegex(ValueError, 'invalid_work_selector'):
            self.service._select_work(run_id='../outside')
        self.assertEqual(self.records.calls, [])

    def test_invalid_records_filtered_without_loading_unsafe_assignment(self):
        self.records.run['tasks'] = [None, {}, {'id': '../bad'}, {'id': 'a'}]
        self.records.assignment['run_id'] = 'other'
        self.assertEqual(self.service._work_records(include_historical=True), [])
        self.assertEqual(self.records.calls, [('runs',), ('assignment', 'a')])

    def test_identity_mismatch_and_duplicates_not_hidden(self):
        with self.assertRaisesRegex(ValueError, 'work_identity_mismatch'):
            self.service._select_work(run_id='other', assignment_id='a')
        self.records.run['tasks'].append({'id': 'a'})
        with self.assertRaisesRegex(ValueError, 'assignment_choice_required'):
            self.service._select_work(run_id='r')

    def test_pending_completion_keeps_terminal_record_active(self):
        self.records.assignment['status'] = 'done'
        self.records.run['status'] = 'completed'
        self.assertEqual(self.service._work_records(include_historical=False), [])
        with patch.object(ReadScenario, '_load_completion_intent', return_value=({'intent': True}, None)):
            record = self.service._work_records(include_historical=False)[0]
            self.assertTrue(record['active'] and record['pending_completion'])

    def test_reader_exceptions_not_rewritten(self):
        failure = PermissionError('read denied')
        with patch.object(self.records, 'load_assignment', side_effect=failure):
            with self.assertRaises(PermissionError) as caught:
                self.service._select_work(assignment_id='a')
        self.assertIs(caught.exception, failure)

    def test_state_observer_noop_trace_and_failing_sink(self):
        normalized = {'scope': {'allowed_actions': ['read']},
                      'assignment': {'execution_mode': {'kind': 'read_only'}}}
        with patch('processforge_core.work.context.normalized_assignment_contract', return_value=normalized):
            expected = self.service.state(run_id='r', assignment_id='a', context_id='a-capsule')
            self.assertEqual(expected['action'], 'work_ready')
            events = []
            config = d.resolve_config(('invocation', {'profile': 'trace', 'sink': 'none',
                                       'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}))
            observer = d.Logger(config, sinks=[events.append])
            observed = ReadScenario(self.service.project_root, None, self.service.core,
                                    records=self.records, observer=observer)
            self.assertEqual(observed.state(run_id='r', assignment_id='a', context_id='a-capsule'), expected)
            completion = next(event for event in events if event['code'] == 'work.state.completed')
            self.assertEqual(completion['identity']['run_id'], 'r')
            self.assertEqual(completion['identity']['assignment_id'], 'a')
            self.assertIn('duration_ms', completion['context'])
            def failing_sink(event):
                raise OSError('sink offline')
            object.__setattr__(observed, 'observer', d.Logger(config, sinks=[failing_sink]))
            self.assertEqual(observed.state(run_id='r', assignment_id='a'), expected)
            self.assertIs(d.current(), d.NULL)


class LiveReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.flow = self.root / '.pf'
        self.document_reader = YamlDocumentReader(fallback=yaml_io._parse_simple_yaml)
        self.core = SimpleNamespace(locate_flow_root=lambda _: self.flow,
                                    load_yaml_document=self.document_reader.load)
        self.reader = YamlWorkRecordReader(self.root, self.core)
        self.service = build_process_execution_service(self.root, None, self.core)

    def write(self, path, document):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding='utf-8')
        return path

    def run_path(self, identifier='r'):
        return self.flow / 'runs' / identifier / 'run.yaml'

    def assignment_path(self, identifier='a'):
        return self.flow / 'assignments' / (identifier + '.yaml')

    def seed(self):
        self.write(self.run_path(), {'id': 'r', 'status': 'open', 'tasks': [{'id': 'a'}]})
        self.write(self.assignment_path(), {'id': 'a', 'run_id': 'r', 'status': 'open'})

    def test_sorted_inventory_missing_and_unknown_fields(self):
        self.assertEqual(list(self.reader.runs()), [])
        self.assertEqual(self.reader.load_run('missing'), {})
        self.assertEqual(self.reader.load_assignment('missing'), {})
        self.seed()
        self.write(self.run_path('b'), {'future': [1]})
        self.assertEqual([p.parent.name for p, _ in self.reader.runs()], ['b', 'r'])
        self.assertEqual(self.reader.load_run('b'), {'future': [1]})

    def test_live_root_per_operation(self):
        self.seed()
        self.assertEqual(self.reader.load_run('r')['id'], 'r')
        self.flow = self.root / 'other'
        self.assertEqual(self.reader.load_run('r'), {})
        self.assertEqual(self.reader.load_assignment('a'), {})
        self.assertEqual(list(self.reader.runs()), [])

    def test_same_metadata_change_is_visible_within_request_and_after_write(self):
        self.seed()
        with request_scope():
            first = self.reader.load_assignment('a')
            metadata = self.assignment_path().stat()
            text = self.assignment_path().read_text(encoding='utf-8').replace('open', 'done')
            self.assignment_path().write_text(text, encoding='utf-8')
            os.utime(self.assignment_path(), ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            self.assertEqual(self.assignment_path().stat().st_size, metadata.st_size)
            self.assertEqual(first['status'], 'open')
            self.assertEqual(self.reader.load_assignment('a')['status'], 'done')
            self.assertEqual(self.service._load_assignment('a')['status'], 'done')
            self.write(self.run_path('b'), {'id': 'b'})
            self.assertEqual([p.parent.name for p, _ in self.reader.runs()], ['b', 'r'])
            self.assignment_path().unlink()
            self.run_path().unlink()
            self.assertEqual(self.reader.load_assignment('a'), {})
            self.assertEqual([p.parent.name for p, _ in self.reader.runs()], ['b'])

    def test_caller_mutations_do_not_change_other_read_results(self):
        self.write(self.assignment_path(), {'future': {'values': [1]}})
        with request_scope():
            self.reader.load_assignment('a')['future']['values'].clear()
            self.assertEqual(self.service._load_assignment('a'), {'future': {'values': [1]}})

    def test_concurrent_projects_and_requests_do_not_share_results(self):
        core = SimpleNamespace(locate_flow_root=lambda root: root / '.pf',
                               load_yaml_document=self.document_reader.load)
        readers = []
        for index in range(2):
            root = self.root / ('project-' + str(index))
            self.write(root / '.pf/assignments/a.yaml', {'project': index, 'values': [index]})
            readers.append(YamlWorkRecordReader(root, core))
        def read(index):
            with request_scope():
                first = readers[index].load_assignment('a')
                first['values'].clear()
                return readers[index].load_assignment('a')
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(read, [0, 1] * 10))
        self.assertEqual(results, [{'project': index, 'values': [index]} for index in [0, 1] * 10])

    def test_invalid_yaml_and_read_errors_keep_loader_contract(self):
        path = self.write(self.assignment_path(), {'id': 'a'})
        for text in ('value: [', "!!python/object/apply:os.system ['exit']"):
            path.write_text(text, encoding='utf-8')
            self.assertIn('__yaml_error__', self.reader.load_assignment('a'))
        with patch.object(Path, 'read_text', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                self.reader.load_assignment('a')

    def test_legacy_private_root_and_path_overrides_preserved(self):
        class LegacyPaths(ProcessExecutionService):
            def _flow_root(inner):
                return self.flow
            def _run_path(inner, identifier):
                return self.root / 'custom-run.yaml'
            def _assignment_path(inner, identifier):
                return self.root / 'custom-assignment.yaml'
        self.seed()
        self.write(self.root / 'custom-run.yaml', {'id': 'custom-run'})
        self.write(self.root / 'custom-assignment.yaml', {'id': 'custom-assignment'})
        core = SimpleNamespace(load_yaml_document=self.document_reader.load)
        legacy = LegacyPaths(self.root, None, core)
        with patch.object(ProcessExecutionService, '_load_completion_intent', return_value=(None, None)):
            self.assertEqual(legacy._work_records(include_historical=True)[0]['assignment_id'], 'a')
        self.assertEqual(legacy._load_run('r'), {'id': 'custom-run'})
        self.assertEqual(legacy._load_assignment('a'), {'id': 'custom-assignment'})

    def test_baseline_raw_reads_and_selection_records(self):
        if BASELINE is None:
            self.skipTest('Use --baseline for original method differential proof')
        namespace = dict(vars(execution))
        exec(compile(BASELINE.read_text(encoding='utf-8'), str(BASELINE), 'exec'), namespace)
        comparisons = 0
        legacy = ProcessExecutionService(self.root, None, self.core)
        for run_status, task_status, pending in itertools.product(
                ('open', 'completed', 'cancelled', ''), ('open', 'done', 'failed', ''), (False, True)):
            self.write(self.run_path(), {'id': 'r', 'status': run_status,
                                        'tasks': [{'id': 'a'}, {'id': 'alias'}, {'id': 'missing'}, {'id': '../bad'}, None]})
            self.write(self.assignment_path(), {'id': 'a', 'run_id': 'r', 'status': task_status,
                                               'future': {'values': [1]}, 'session': {'id': 's'}})
            self.write(self.assignment_path('alias'), {'id': 'a', 'status': task_status})
            self.write(self.run_path('duplicate'), self.reader.load_run('r'))
            with patch.object(ProcessExecutionService, '_load_completion_intent', return_value=({'intent': True} if pending else None, None)):
                for historical in (False, True):
                    expected = namespace['baseline_work_records'](legacy, include_historical=historical)
                    self.assertEqual(self.service._work_records(include_historical=historical), expected)
                    comparisons += 1
            self.assertEqual(self.service._load_run('r'), namespace['baseline_load_run'](legacy, 'r'))
            self.assertEqual(self.service._load_assignment('a'), namespace['baseline_load_assignment'](legacy, 'a'))
            comparisons += 2
        print('Original read differential comparisons:', comparisons)


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
    for case in (CompositionTests, InjectedReadTests, LiveReaderTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
