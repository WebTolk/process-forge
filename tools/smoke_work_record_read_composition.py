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
from processforge_core.common.request_scope import request_scope
from processforge_core.work.records import YamlWorkRecordReader
from processforge_core.work.records import CurrentWorkService
from processforge_core.work.metadata import WorkMetadataReadPass
from processforge_core.work.inventory import WorkInventory

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
        # These legacy records omit process identity: the canonical preflight
        # fails, so the existing catalog and final raw reloads still run.
        self.assertEqual(self.records.calls, [('run', 'r'), ('assignment', 'a'), ('runs',),
                                              ('assignment', 'a'), ('run', 'r'), ('assignment', 'a')])
        self.assertEqual(selected[0]['future'], {'values': [1]})
        selected[1]['future']['values'].clear()
        self.records.assignment['future']['values'].append(3)
        self.assertEqual(self.service._select_work(assignment_id='a')[1]['future']['values'], [2, 3])

    def test_falsey_port_canonical_pair_uses_four_live_reads(self):
        self.records.run['process'] = self.records.assignment['process'] = 'p'
        selected = self.service._select_work(run_id='r', assignment_id='a')
        self.assertEqual(selected, (self.records.run, self.records.assignment))
        self.assertEqual(self.records.calls, [('run', 'r'), ('assignment', 'a'),
                                              ('run', 'r'), ('assignment', 'a')])

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
        self.reader = YamlWorkRecordReader(self.root, self.document_reader)
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

    def seed_canonical(self):
        self.write(self.run_path(), {'id': 'r', 'process': 'p', 'status': 'open',
                                    'tasks': [{'id': 'a'}], 'future': {'values': [1]}})
        self.write(self.assignment_path(), {'id': 'a', 'run_id': 'r', 'process': 'p',
                                           'status': 'open', 'future': {'values': [2]}})

    def test_default_canonical_pair_is_authoritative_over_foreign_alias(self):
        self.seed_canonical()
        self.write(self.run_path('a-poison'), {'id': 'a-poison', 'process': 'p', 'status': 'open',
                                             'tasks': [{'id': 'alias'}]})
        self.write(self.assignment_path('alias'), {'id': 'a', 'run_id': 'a-poison',
                                                  'process': 'p', 'status': 'open'})
        run, task = self.service._select_work(run_id='r', assignment_id='a')
        self.assertEqual((run['id'], task['id'], task['run_id']), ('r', 'a', 'r'))
        self.assertEqual((run['future'], task['future']), ({'values': [1]}, {'values': [2]}))
        # Assignment-only selection retains historical first-match semantics.
        self.assertEqual(self.service._select_work(assignment_id='a')[0]['id'], 'a-poison')
        self.assertNotIn('processforge', sys.modules)
        self.assertNotIn('processforge_core._legacy_processforge', sys.modules)

    def test_canonical_pair_isolated_from_unrelated_history_read_failure(self):
        self.seed_canonical()
        foreign = self.assignment_path('broken')
        self.write(self.run_path('z-history'), {'id': 'z-history', 'process': 'p',
                                              'tasks': [{'id': 'broken'}]})
        self.write(foreign, {'id': 'broken', 'run_id': 'z-history', 'process': 'p'})
        original = Path.read_text
        failure = OSError('unrelated historical document')
        def read(path, *args, **kwargs):
            if path == foreign:
                raise failure
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            self.assertEqual(self.service._select_work(run_id='r', assignment_id='a')[1]['id'], 'a')
            for selectors in ({'assignment_id': 'a'}, {'run_id': 'r'}, {}):
                with self.assertRaises(OSError) as caught:
                    self.service._select_work(**selectors)
                self.assertIs(caught.exception, failure)

    def test_final_canonical_read_sees_same_metadata_change_within_request(self):
        self.seed_canonical()
        original = YamlDocumentReader.load
        calls = []
        def load(reader, path):
            value = original(reader, path)
            calls.append(path)
            if calls == [self.run_path(), self.assignment_path()]:
                metadata = path.stat()
                path.write_text(path.read_text(encoding='utf-8').replace('open', 'done'), encoding='utf-8')
                os.utime(path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                self.assertEqual(path.stat().st_size, metadata.st_size)
            return value
        with request_scope(), patch.object(YamlDocumentReader, 'load', load):
            selected = self.service._select_work(run_id='r', assignment_id='a')
        self.assertEqual(selected[1]['status'], 'done')
        self.assertEqual(calls, [self.run_path(), self.assignment_path()] * 2)

    def test_final_canonical_identity_change_or_deletion_is_rejected(self):
        original = YamlDocumentReader.load
        for change in ('owner', 'membership', 'assignment-deleted', 'run-deleted', 'malformed'):
            with self.subTest(change=change):
                self.seed_canonical()
                calls = []
                def load(reader, path):
                    value = original(reader, path)
                    calls.append(path)
                    if calls == [self.run_path(), self.assignment_path()]:
                        if change == 'owner':
                            self.write(path, {**value, 'run_id': 'other'})
                        elif change == 'membership':
                            self.write(self.run_path(), {'id': 'r', 'process': 'p', 'tasks': []})
                        elif change == 'assignment-deleted':
                            path.unlink()
                        elif change == 'run-deleted':
                            self.run_path().unlink()
                        else:
                            path.write_text('value: [', encoding='utf-8')
                    return value
                with request_scope(), patch.object(YamlDocumentReader, 'load', load):
                    with self.assertRaisesRegex(ValueError, '^work_identity_mismatch$'):
                        self.service._select_work(run_id='r', assignment_id='a')
                self.assertEqual(calls, [self.run_path(), self.assignment_path()] * 2)

    def test_sorted_inventory_missing_and_unknown_fields(self):
        self.assertEqual(list(self.reader.runs()), [])
        self.assertEqual(self.reader.load_run('missing'), {})
        self.assertEqual(self.reader.load_assignment('missing'), {})
        self.seed()
        self.write(self.run_path('b'), {'future': [1]})
        self.assertEqual([p.parent.name for p, _ in self.reader.runs()], ['b', 'r'])
        self.assertEqual(self.reader.load_run('b'), {'future': [1]})

    def test_live_records_disappear_and_reappear(self):
        self.seed()
        self.assertEqual(self.reader.load_run('r')['id'], 'r')
        self.run_path().unlink()
        self.assignment_path().unlink()
        self.assertEqual(self.reader.load_run('r'), {})
        self.assertEqual(self.reader.load_assignment('a'), {})
        self.assertEqual(list(self.reader.runs()), [])
        self.seed()
        self.assertEqual(self.reader.load_run('r')['id'], 'r')
        self.assertEqual(self.reader.load_assignment('a')['id'], 'a')

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
            readers.append(YamlWorkRecordReader(root))
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


    def test_metadata_shared_pass_reads_each_source_once(self):
        self.seed()
        metadata = WorkMetadataReadPass(self.root)
        current = CurrentWorkService(self.root, work_metadata=lambda: metadata)
        service = build_process_execution_service(self.root, None, self.core, work_metadata=lambda: metadata)
        reads, enumerations = [], []
        original, inventory = Path.read_text, WorkInventory.run_paths
        def read(path, *args, **kwargs):
            reads.append(path)
            return original(path, *args, **kwargs)
        def paths(owner):
            enumerations.append(owner.flow_root)
            yield from inventory(owner)
        with patch.object(Path, 'read_text', read), patch.object(WorkInventory, 'run_paths', paths):
            self.assertEqual(current.summary()['active_work'][0]['assignment_id'], 'a')
            self.assertEqual(service._work_records(include_historical=True)[0]['assignment_id'], 'a')
        self.assertEqual(enumerations, [self.flow])
        self.assertEqual(reads.count(self.run_path()), 1)
        self.assertEqual(reads.count(self.assignment_path()), 1)

    def test_metadata_keeps_different_summary_and_catalog_activity(self):
        self.write(self.run_path(), {'id': 'r', 'status': 'in_progress', 'tasks': [{'id': 'a'}]})
        self.write(self.assignment_path(), {'id': 'a', 'status': 'done'})
        metadata = WorkMetadataReadPass(self.root)
        summary = CurrentWorkService(self.root, work_metadata=lambda: metadata).summary()
        service = build_process_execution_service(self.root, None, self.core, work_metadata=lambda: metadata)
        self.assertTrue(summary['governed'])
        self.assertFalse(service._work_records(include_historical=True)[0]['active'])

    def test_metadata_documents_are_independent_and_rebuilt_after_write(self):
        self.seed()
        metadata = WorkMetadataReadPass(self.root)
        run = next(metadata.runs())[1]
        run['tasks'].clear()
        assignment = metadata.assignment('a')
        assignment['status'] = 'done'
        self.assertEqual(next(metadata.runs())[1]['tasks'], [{'id': 'a'}])
        self.assertEqual(metadata.assignment('a')['status'], 'open')
        with request_scope():
            self.assertEqual(self.service._work_records(include_historical=True)[0]['status'], 'open')
            path = self.assignment_path()
            previous = path.stat()
            text = path.read_text(encoding='utf-8')
            path.write_text(text.replace('open', 'done'), encoding='utf-8')
            os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
            self.assertEqual(path.stat().st_size, previous.st_size)
            self.assertEqual(self.service._work_records(include_historical=True)[0]['status'], 'done')

    def test_metadata_completion_uses_full_live_alias_documents(self):
        self.write(self.run_path(), {'id': 'r', 'status': 'completed', 'tasks': [{'id': 'alias'}],
                                    'process_execution': {'snapshot_id': 'original'}, 'run_future': [1]})
        self.write(self.assignment_path('alias'), {'id': 'a', 'status': 'done', 'task_future': [2]})
        journal = self.root / 'private-completion-intent.yaml'
        self.write(journal, {'pending': True})
        calls = []
        def intent(owner, run, assignment):
            self.assertEqual(run['run_future'], [1])
            self.assertEqual(run['process_execution']['snapshot_id'], 'original')
            self.assertEqual(assignment['task_future'], [2])
            calls.append((run['id'], assignment['id']))
            return {'pending': True}, None
        with patch.object(ProcessExecutionService, '_completion_intent_path', return_value=journal), \
                patch.object(ProcessExecutionService, '_load_completion_intent', intent):
            record = self.service._work_records(include_historical=False)[0]
        self.assertEqual(calls, [('r', 'a')])
        self.assertTrue(record['pending_completion'] and record['active'])

    def test_metadata_preserves_lazy_read_error_order(self):
        self.seed()
        later = self.run_path('z')
        self.write(later, {'id': 'z', 'tasks': []})
        first_failure, later_failure = OSError('assignment first'), OSError('later run')
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path == self.assignment_path():
                raise first_failure
            if path == later:
                raise later_failure
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            for operation in (CurrentWorkService(self.root).items,
                              lambda: self.service._work_records(include_historical=True)):
                with self.assertRaises(OSError) as caught:
                    operation()
                self.assertIs(caught.exception, first_failure)

    def test_metadata_warm_history_avoids_parsing_and_full_reads(self):
        from processforge_core.common.request_scope import _PARSE_CACHE
        self.write(self.run_path(), {'id': 'r', 'status': 'completed', 'tasks': [{'id': 'a'}],
                                    'stage_history': [{'notes': 'history' * 1000}] * 8})
        self.write(self.assignment_path(), {'id': 'a', 'status': 'done',
                                           'stage_history': [{'notes': 'history' * 1000}] * 8})
        _PARSE_CACHE.clear()
        def operation():
            metadata = WorkMetadataReadPass(self.root)
            CurrentWorkService(self.root, work_metadata=lambda: metadata).summary()
            return build_process_execution_service(self.root, None, self.core,
                        work_metadata=lambda: metadata)._work_records(include_historical=True)
        with patch.object(YamlDocumentReader, 'load', side_effect=AssertionError('Full history read')):
            with request_scope() as cold:
                operation()
            with request_scope() as warm:
                operation()
        self.assertEqual(cold.parses, 2)
        self.assertEqual(warm.parses, 0)

    def test_metadata_summary_and_catalog_partial_document_differential(self):
        if BASELINE is None:
            self.skipTest('Use --baseline for original partial-document differential')
        namespace = dict(vars(execution))
        exec(compile(BASELINE.read_text(encoding='utf-8'), str(BASELINE), 'exec'), namespace)
        tasks = ({}, {'future': [1]}, {'id': None}, {'id': False, 'session': []},
                 {'id': 'a', 'status': 'done'}, {'id': 'a', 'objective': ['legacy']})
        runs = ({'id': 'r', 'status': 'open'}, {'status': 'completed'}, {'id': None}, {'id': False})
        comparisons = 0
        for run, task in itertools.product(runs, tasks):
            self.write(self.run_path(), {**run, 'tasks': [{'id': 'a'}, {'id': 'a'}, None, {'id': 'missing'}]})
            self.write(self.assignment_path(), task)
            expected = namespace['baseline_current_items'](CurrentWorkService(self.root))
            self.assertEqual(CurrentWorkService(self.root).items(), expected)
            for historical in (False, True):
                expected = namespace['baseline_work_records'](self.service, include_historical=historical)
                self.assertEqual(self.service._work_records(include_historical=historical), expected)
            comparisons += 3
        print('Metadata partial-document differential comparisons:', comparisons)


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
