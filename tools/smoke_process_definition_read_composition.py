#!/usr/bin/env python3
"""Effective process pin rules and explicit read composition compatibility."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
import importlib.util
import inspect
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

from processforge_core import process_execution as execution
from processforge_core.bootstrap import RuntimeBootstrap
from processforge_core.composition import build_process_definition_read_service, build_process_execution_service
from processforge_core.process_catalog.definition_read import ProcessDefinitionReadService
from processforge_core.process_execution import ProcessExecutionService, canonical_fingerprint

BASELINE = None
SCRATCH = None


class Core:
    def __init__(self):
        self.document = {'id': 'p', 'version': '1', 'stages': [{'id': 'read'}], 'future': {'values': [1]}}
        self.calls = []

    def resolve_process_definition(self, root, identifier):
        self.calls.append((root, identifier))
        return SimpleNamespace(process=self.document)


def pinned(definition):
    return {'process': 'p', 'process_execution': {'definition': definition,
                                                'process_fingerprint': canonical_fingerprint(definition)}}


class MemoryDefinitions:
    def __init__(self):
        self.calls = []

    def __bool__(self):
        return False

    def effective_process(self, run):
        self.calls.append(run)
        return {'id': 'p', 'version': '1', 'stages': [{'id': 'read'}]}, 'pinned'


class MemoryContext:
    def validation(self, assignment):
        return {'status': 'valid'}

    def normalized_assignment(self, assignment):
        return {'scope': {'allowed_actions': ['read'], 'allowed_read_files': ['src/**']},
                'assignment': {'execution_mode': {'kind': 'read_only'}}}


class MemoryState(ProcessExecutionService):
    def _select_work(self, **selectors):
        return ({'id': 'r', 'process': 'p', 'status': 'open'},
                {'id': 'a', 'run_id': 'r', 'status': 'open', 'stage': 'read'})


class DefinitionTests(unittest.TestCase):
    def test_pinned_and_corrupt_do_not_resolve(self):
        fail = lambda ident: (_ for _ in ()).throw(AssertionError('Pin must not consult catalog'))
        reader = ProcessDefinitionReadService(fail, canonical_fingerprint)
        source = Core().document
        run = pinned(source)
        result, status = reader.effective_process(run)
        self.assertEqual((result, status), (source, 'pinned'))
        result['future']['values'].append(2)
        self.assertEqual(source['future']['values'], [1])
        run['process_execution']['process_fingerprint'] = 'bad'
        result, status = reader.effective_process(run)
        self.assertEqual(status, 'corrupt')
        result['future']['values'].append(2)
        self.assertEqual(source['future']['values'], [1])
        self.assertEqual(reader.effective_process({'process': 7, 'process_execution': {'x': 1}}),
                         ({'id': '7', 'stages': []}, 'corrupt'))

    def test_empty_definition_can_be_pinned(self):
        reader = ProcessDefinitionReadService(lambda ident: self.fail('No resolver'), canonical_fingerprint)
        self.assertEqual(reader.effective_process(pinned({})), ({}, 'pinned'))

    def test_exact_exception_boundaries(self):
        for error in [OSError('io'), SystemExit('exit'), ValueError('value')]:
            with self.subTest(error=type(error).__name__):
                def resolve(ident):
                    raise error
                reader = ProcessDefinitionReadService(resolve, canonical_fingerprint)
                self.assertEqual(reader.effective_process({'process': 'p'}), ({'id': 'p', 'stages': []}, 'missing'))
        for error in [TypeError('type'), RuntimeError('unexpected'), KeyboardInterrupt()]:
            def resolve(ident):
                raise error
            with self.assertRaises(type(error)) as caught:
                ProcessDefinitionReadService(resolve, canonical_fingerprint).effective_process({'process': 'p'})
            self.assertIs(caught.exception, error)
        error = ValueError('fingerprint failure')
        def fingerprint(definition):
            raise error
        with self.assertRaises(ValueError) as caught:
            ProcessDefinitionReadService(lambda ident: {}, fingerprint).effective_process(pinned({}))
        self.assertIs(caught.exception, error)

    def test_deepcopy_failure_keeps_original_boundary(self):
        class BadCopy:
            def __deepcopy__(self, memo):
                raise ValueError('copy failed')
        definition = {'future': BadCopy()}
        reader = ProcessDefinitionReadService(lambda ident: definition, lambda value: 'pin')
        self.assertEqual(reader.effective_process({'process': 'p'}), ({'id': 'p', 'stages': []}, 'missing'))
        for fingerprint in ['pin', 'bad']:
            with self.assertRaisesRegex(ValueError, 'copy failed'):
                reader.effective_process({'process': 'p', 'process_execution': {
                    'definition': definition, 'process_fingerprint': fingerprint}})

    def test_live_legacy_resolution_and_independent_results(self):
        core = Core()
        reader = build_process_definition_read_service(Path('p'), core, fingerprint=canonical_fingerprint)
        first, status = reader.effective_process({'process': 'p'})
        self.assertEqual(status, 'legacy_unpinned')
        first['future']['values'].append(2)
        core.document['future']['values'] = [9]
        second, _ = reader.effective_process({'process': 'p'})
        self.assertEqual(second['future']['values'], [9])
        self.assertEqual(core.calls, [(Path('p'), 'p')] * 2)

    def test_default_is_lazy_and_uses_live_core_and_fingerprint(self):
        core = Core()
        service = ProcessExecutionService(Path('first'), None, core)
        service._effective_process({'process': 'p'})
        self.assertEqual(core.calls, [(Path('first'), 'p')])
        other = Core()
        core.resolve_process_definition = other.resolve_process_definition
        service._effective_process({'process': 'p'})
        self.assertEqual(other.calls, [(Path('first'), 'p')])
        with patch.object(execution, 'canonical_fingerprint', return_value='custom'):
            result = service._effective_process({'process_execution': {'definition': {}, 'process_fingerprint': 'custom'}})
            self.assertEqual(result, ({}, 'pinned'))

    def test_injection_factory_bootstrap_no_io_and_falsey_port(self):
        class NoCore:
            def __getattr__(self, name):
                raise AssertionError('No core access: ' + name)
        core, definitions = NoCore(), MemoryDefinitions()
        with patch.object(Path, 'is_file', side_effect=AssertionError('No filesystem probe')):
            build_process_definition_read_service(Path('p'), core, fingerprint=canonical_fingerprint)
            service = build_process_execution_service(Path('p'), None, core, definitions=definitions)
            built = RuntimeBootstrap(Path('distribution'), core, None, None).process_execution_service(
                Path('p'), None, definitions=definitions)
            self.assertIs(service.definitions, definitions)
            self.assertIs(built.definitions, definitions)
            self.assertEqual(built._effective_process({'process': 'p'})[1], 'pinned')
        self.assertEqual(len(definitions.calls), 1)

    def test_old_constructor_repr_equality_and_match_args(self):
        core = Core()
        old = ProcessExecutionService(Path('p'), None, core)
        new = ProcessExecutionService(Path('p'), None, core, definitions=MemoryDefinitions())
        self.assertEqual(old, new)
        self.assertEqual(repr(old), repr(new))
        self.assertEqual(ProcessExecutionService.__match_args__, ('project_root', 'workplace_root', 'core'))
        item = next(f for f in fields(new) if f.name == 'definitions')
        self.assertTrue(item.kw_only)
        self.assertFalse(item.repr or item.compare)
        self.assertEqual(inspect.signature(ProcessExecutionService).parameters['definitions'].kind,
                         inspect.Parameter.KEYWORD_ONLY)

    def test_memory_state_guard_and_port_integration(self):
        definitions = MemoryDefinitions()
        service = MemoryState(Path('p'), None, SimpleNamespace(project_id=lambda root: root.name),
                              context=MemoryContext(), definitions=definitions)
        self.assertEqual(service.state(context_id='wrong')['reason'], 'work_context_mismatch')
        self.assertEqual(definitions.calls, [])
        result = service.state(context_id='a-capsule')
        self.assertEqual(result['process']['pin_status'], 'pinned')
        self.assertEqual(result['context']['validation']['status'], 'valid')
        self.assertEqual(result['execution_readiness']['status'], 'ready')
        self.assertEqual(len(definitions.calls), 1)
        service.can_complete()
        # can_complete reads both its definition and the existing state view.
        self.assertEqual(len(definitions.calls), 3)

    def test_threads_do_not_share_mutable_results(self):
        reader = ProcessDefinitionReadService(lambda ident: Core().document, canonical_fingerprint)
        def read(index):
            result, _ = reader.effective_process({'process': str(index)})
            result['future']['values'].append(index)
            return result['future']['values']
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(read, range(20))), [[1, i] for i in range(20)])

    def test_imports_without_cli_or_eager_legacy(self):
        code = (
            "import sys; from processforge_core.process_catalog.definition_read import ProcessDefinitionReadService; "
            "from processforge_core.composition import build_process_execution_service; "
            "assert 'processforge' not in sys.modules; "
            "assert 'processforge_core._legacy_processforge' not in sys.modules"
        )
        result = subprocess.run([sys.executable, '-B', '-c', "import sys; sys.path.insert(0, 'src'); " + code],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_isolated_package_without_cli(self):
        with tempfile.TemporaryDirectory(prefix='pf-process-read-', dir=SCRATCH) as folder:
            target = Path(folder)
            shutil.copytree(ROOT / 'src/processforge_core', target / 'processforge_core',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            code = (
                "from pathlib import Path; from processforge_core.composition import build_process_execution_service; "
                "service = build_process_execution_service(Path('p'), None, object()); "
                "from processforge_core.process_execution import canonical_fingerprint; "
                "assert service._effective_process({'process_execution': {'definition': {}, "
                "'process_fingerprint': canonical_fingerprint({})}}) == ({}, 'pinned')"
            )
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=target,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_original_helper_differential(self):
        if BASELINE is None:
            self.skipTest('No retained baseline supplied')
        definitions = [None, [], {}, {'id': 'p', 'stages': [], 'future': [1]}]
        comparisons = 0
        for definition in definitions:
            pins = [None, {}, {'definition': definition},
                    {'definition': definition, 'process_fingerprint': 'bad'}]
            if isinstance(definition, dict):
                pins.append({'definition': definition, 'process_fingerprint': canonical_fingerprint(definition)})
            for pin in pins:
                left, right = Core(), Core()
                run = {'process': 'p', 'process_execution': pin}
                expected = BASELINE(ProcessExecutionService(Path('p'), None, left), copy.deepcopy(run))
                actual = ProcessExecutionService(Path('p'), None, right)._effective_process(copy.deepcopy(run))
                self.assertEqual(expected, actual)
                self.assertEqual(left.calls, right.calls)
                comparisons += 1
        print('Original helper comparisons:', comparisons)


def main():
    global BASELINE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--scratch-root', type=Path)
    args = parser.parse_args()
    SCRATCH = args.scratch_root
    if args.baseline:
        spec = importlib.util.spec_from_file_location('retained_effective', args.baseline)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        BASELINE = module._effective_process
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DefinitionTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
