#!/usr/bin/env python3
"""Effective process pin rules and explicit read composition compatibility."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import fields
import importlib.util
import inspect
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from processforge_core.process_catalog import definition_read as definition_reader
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


class CatalogFixture:
    """A narrow catalog reader fixture, independent of the CLI and coordinator."""

    def __init__(self, document=None, error=None):
        self.document = Core().document if document is None else document
        self.error = error
        self.calls = []

    def resolve_definition(self, identifier):
        self.calls.append(identifier)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(process=self.document)


@contextmanager
def workspace():
    base = (SCRATCH or ROOT / '.pf/tmp/process-definition-smoke').resolve()
    base.mkdir(parents=True, exist_ok=True)
    directory = base / ('case-' + uuid4().hex)
    directory.mkdir()
    try:
        yield directory
    finally:
        directory.resolve().relative_to(base)
        shutil.rmtree(directory)


def project_definition(root, values):
    path = root / '.pf/processes/p.process.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('id: p\nversion: "1"\nstages: []\nfuture:\n  values: ' + str(values) + '\n', encoding='utf-8')
    return path


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
        catalog = CatalogFixture(error=AssertionError('Pin must not consult catalog'))
        reader = ProcessDefinitionReadService(Path('p'), catalog=catalog)
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
        self.assertEqual(catalog.calls, [])

    def test_empty_definition_can_be_pinned(self):
        reader = ProcessDefinitionReadService(Path('p'), catalog=CatalogFixture(error=AssertionError('No catalog read')))
        self.assertEqual(reader.effective_process(pinned({})), ({}, 'pinned'))

    def test_exact_exception_boundaries(self):
        for error in [OSError('io'), SystemExit('exit'), ValueError('value')]:
            with self.subTest(error=type(error).__name__):
                reader = ProcessDefinitionReadService(Path('p'), catalog=CatalogFixture(error=error))
                self.assertEqual(reader.effective_process({'process': 'p'}), ({'id': 'p', 'stages': []}, 'missing'))
        for error in [TypeError('type'), RuntimeError('unexpected'), KeyboardInterrupt()]:
            with self.assertRaises(type(error)) as caught:
                ProcessDefinitionReadService(Path('p'), catalog=CatalogFixture(error=error)).effective_process({'process': 'p'})
            self.assertIs(caught.exception, error)
        error = ValueError('fingerprint failure')
        run = pinned({})
        with patch.object(definition_reader, 'canonical_fingerprint', side_effect=error), self.assertRaises(ValueError) as caught:
            ProcessDefinitionReadService(Path('p')).effective_process(run)
        self.assertIs(caught.exception, error)

    def test_deepcopy_failure_keeps_original_boundary(self):
        class BadCopy:
            def __deepcopy__(self, memo):
                raise ValueError('copy failed')
        definition = {'future': BadCopy()}
        reader = ProcessDefinitionReadService(Path('p'), catalog=CatalogFixture(document=definition))
        self.assertEqual(reader.effective_process({'process': 'p'}), ({'id': 'p', 'stages': []}, 'missing'))
        for fingerprint in ['pin', 'bad']:
            with patch.object(definition_reader, 'canonical_fingerprint', return_value='pin'), self.assertRaisesRegex(ValueError, 'copy failed'):
                reader.effective_process({'process': 'p', 'process_execution': {
                    'definition': definition, 'process_fingerprint': fingerprint}})

    def test_live_catalog_resolution_and_independent_results(self):
        with workspace() as root:
            project_definition(root, [1])
            reader = build_process_definition_read_service(root)
            first, status = reader.effective_process({'process': 'p'})
            self.assertEqual(status, 'legacy_unpinned')
            first['future']['values'].append(2)
            project_definition(root, [9])
            second, _ = reader.effective_process({'process': 'p'})
            self.assertEqual(second['future']['values'], [9])

    def test_default_uses_live_catalog_without_core(self):
        class NoCore:
            def __getattr__(self, name):
                raise AssertionError('No monolith callback: ' + name)
        with workspace() as root:
            project_definition(root, [1])
            service = ProcessExecutionService(root, None, NoCore())
            self.assertEqual(service._effective_process({'process': 'p'})[0]['future']['values'], [1])
            project_definition(root, [9])
            self.assertEqual(service._effective_process({'process': 'p'})[0]['future']['values'], [9])
            self.assertEqual(service._effective_process(pinned({})), ({}, 'pinned'))

    def test_injection_factory_bootstrap_no_io_and_falsey_port(self):
        class NoCore:
            def __getattr__(self, name):
                raise AssertionError('No core access: ' + name)
        core, definitions = NoCore(), MemoryDefinitions()
        with patch.object(Path, 'is_file', side_effect=AssertionError('No filesystem probe')):
            build_process_definition_read_service(Path('p'))
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
        reader = ProcessDefinitionReadService(Path('p'), catalog=CatalogFixture())
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
        with workspace() as target:
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
                catalog = CatalogFixture(document=right.document)
                actual = ProcessDefinitionReadService(Path('p'), catalog=catalog).effective_process(copy.deepcopy(run))
                self.assertEqual(expected, actual)
                self.assertEqual(left.calls, [(Path('p'), ident) for ident in catalog.calls])
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
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        BASELINE = module._effective_process
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DefinitionTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
