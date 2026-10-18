#!/usr/bin/env python3
"""File-backed catalog/default definition reads, with optional retained originals."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.process_catalog.catalog_read import ProcessCatalogReadService
from processforge_core.process_catalog.definition_read import ProcessDefinitionReadService
from processforge_core.process_catalog import definition_read, service
from processforge_core.process_execution import canonical_fingerprint
from processforge_core.work.context_documents import ContextContractInputs

SCRATCH = None
BASELINE = None


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def retained_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def observed(operation):
    try:
        value = operation()
        return ("return", asdict(value) if hasattr(value, "catalog_role") else value)
    except (OSError, SystemExit, ValueError) as error:
        return (type(error).__name__, str(error))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.root = SCRATCH / ("case-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.project = self.root / "project"
        self.distribution = self.root / "distribution"
        self.project.mkdir()
        self.distribution.mkdir()
        write(self.project / ".pf/process-forge.yaml", "workplace:\n  reference: auto\n")
        write(self.project / "workplace.yaml", "registries:\n  process_packs: registries/process-packs.yaml\n")
        write(self.project / "registries/process-packs.yaml", "process_packs:\n  - id: pack.active\n    status: active\n")
        for folder, ident in [("active", "pack.active"), ("inactive", "pack.inactive")]:
            pack = self.distribution / "packs/official" / folder
            write(pack / "package.yaml", f"kind: processforge.pack\norigin: official\nid: {ident}\nproduction_ready: true\nprovides:\n  processes: [{folder}, shared]\n")
            write(pack / "processes" / (folder + ".yaml"), f"id: {folder}\nstatus: active\nfuture: {{values: [1]}}\n")
            write(pack / "processes/shared.yaml", "id: shared\nstatus: active\n")
        write(self.distribution / "processes/core/core.yaml", "id: core\nstatus: internal\n")
        write(self.distribution / "processes/core/shared.yaml", "id: shared\n")
        write(self.project / ".pf/processes/user/shared.yml", "id: shared\nfuture: {values: [1]}\n")
        write(self.project / "processes/custom/custom.yaml", "id: custom\n")
        write(self.project / "processes/legacy.yaml", "id: legacy\n")
        self.catalog = ProcessCatalogReadService(self.project, distribution_root=self.distribution)

    def tearDown(self):
        # Verify the resolved deletion target is a child of the selected scratch.
        self.root.resolve().relative_to(SCRATCH.resolve())
        shutil.rmtree(self.root)

    def test_precedence_metadata_warnings_and_available(self):
        entries = {entry.process_id: entry for entry in self.catalog.entries(strict=True)}
        self.assertEqual(entries["shared"].origin, "user")
        self.assertTrue(any("requires process_override.reason" in x for x in entries["shared"].warnings))
        self.assertTrue(any(x.startswith("STRICT:") for x in entries["shared"].warnings))
        self.assertEqual(entries["active"].pack_id, "pack.active")
        self.assertTrue(entries["active"].active and entries["active"].available and entries["active"].production_ready)
        self.assertEqual(entries["core"].catalog_role, "internal")
        self.assertEqual(entries["legacy"].origin, "legacy_flat")
        self.assertTrue(entries["legacy"].warnings)
        self.assertNotIn("inactive", entries)
        inactive = self.catalog.resolve_definition("inactive", include_available_official=True)
        self.assertFalse(inactive.active)
        self.assertEqual(inactive.origin, "official")
        self.assertEqual(self.catalog.resolve_definition(str(inactive.path)), inactive)
        with self.assertRaisesRegex(SystemExit, "available in official pack pack.inactive"):
            self.catalog.resolve_definition("inactive")
        with self.assertRaisesRegex(SystemExit, "FAIL: process not found: absent"):
            self.catalog.resolve_definition("absent")

    def test_workplace_live_statuses_local_precedence_and_constants(self):
        for status, active in [("active", True), ("enabled", True), ("configured", True), ("disabled", False), ("", True)]:
            write(self.project / "registries/process-packs.yaml", f"process_packs: {{id: pack.active, status: '{status}'}}\n")
            self.assertEqual("pack.active" in self.catalog.context().active_official_pack_ids, active)
        write(self.project / ".pf/process-forge.local.yaml", "unrelated: true\n")
        self.assertEqual(self.catalog.context().active_official_pack_ids, frozenset())
        write(self.project / ".pf/process-forge.local.yaml", "workplace:\n  manifest: '../alternate.yaml'\n")
        write(self.project / "alternate.yaml", "registries:\n  process_packs: ${CUSTOM}/packs.yaml\npath_constants:\n  CUSTOM: ${PF_WORKPLACE}/alternate\n")
        write(self.project / "alternate/packs.yaml", "process_packs: {id: pack.inactive}\n")
        self.assertEqual(self.catalog.context().active_official_pack_ids, frozenset({"pack.inactive"}))
        self.assertEqual(self.catalog.resolve_definition("inactive").pack_id, "pack.inactive")
        self.assertEqual(self.catalog.context().distribution_root, self.distribution.resolve())

    def test_live_same_size_mtime_create_delete_and_mutation(self):
        path = self.project / ".pf/processes/user/shared.yml"
        first = self.catalog.resolve_definition("shared")
        first.process["future"]["values"].append(99)
        self.assertEqual(self.catalog.resolve_definition("shared").process["future"]["values"], [1])
        stamp = path.stat()
        write(path, path.read_text().replace("[1]", "[9]"))
        import os
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertEqual(self.catalog.resolve_definition("shared").process["future"]["values"], [9])
        path.unlink()
        self.assertEqual(self.catalog.resolve_definition("shared").origin, "official")
        write(path, "id: shared\nfuture: [fresh]\n")
        self.assertEqual(self.catalog.resolve_definition("shared").process["future"], ["fresh"])

    def test_malformed_explicit_path_and_normalized_yaml(self):
        path = self.project / "processes/custom/bad.yaml"
        write(path, "id: [broken\n")
        self.assertNotIn("bad", [entry.process_id for entry in self.catalog.entries()])
        with self.assertRaisesRegex(SystemExit, "invalid YAML"):
            self.catalog.resolve_definition("processes/custom/bad.yaml")
        for text in ["", "null\n", "[]\n", "\ufeffid: unicode\nfuture: {value: ё}\n"]:
            write(path, text)
            result = self.catalog.resolve_definition("processes/custom/bad.yaml")
            self.assertIsInstance(result.process, dict)
        write(self.project / "registries/process-packs.yaml", "process_packs: [broken\n")
        self.assertEqual(self.catalog.context().active_official_pack_ids, frozenset())

    def test_real_definition_guards_and_independent_results(self):
        reader = ProcessDefinitionReadService(self.project, catalog=self.catalog)
        definition = {"id": "old", "future": {"values": [1]}}
        pin = {"definition": definition, "process_fingerprint": canonical_fingerprint(definition)}
        with patch.object(ProcessCatalogReadService, "resolve_definition", side_effect=AssertionError("No catalog for pin")):
            output, status = reader.effective_process({"process": "shared", "process_execution": pin})
            self.assertEqual(status, "pinned")
            output["future"]["values"].append(2)
            self.assertEqual(definition["future"]["values"], [1])
            pin["process_fingerprint"] = "bad"
            self.assertEqual(reader.effective_process({"process": "shared", "process_execution": pin}), (definition, "corrupt"))
            self.assertEqual(reader.effective_process({"process": "shared", "process_execution": {"definition": []}}), ({"id": "shared", "stages": []}, "corrupt"))
        self.assertEqual(reader.effective_process({"process": "shared"})[1], "legacy_unpinned")
        self.assertEqual(reader.effective_process({"process": "absent"}), ({"id": "absent", "stages": []}, "missing"))
        self.assertEqual(reader.effective_process({"process": "inactive"})[1], "missing")

    def test_definition_exact_exception_and_falsey_catalog_boundaries(self):
        class FalseCatalog:
            def __bool__(self):
                return False

            def resolve_definition(self, ident):
                raise self.error

        catalog = FalseCatalog()
        reader = ProcessDefinitionReadService(self.project, catalog=catalog)
        for error in [OSError("io"), SystemExit("exit"), ValueError("value")]:
            catalog.error = error
            self.assertEqual(reader.effective_process({"process": "p"})[1], "missing")
        for error in [TypeError("type"), RuntimeError("runtime"), KeyboardInterrupt()]:
            catalog.error = error
            with self.assertRaises(type(error)) as caught:
                reader.effective_process({"process": "p"})
            self.assertIs(caught.exception, error)
        with patch.object(definition_read, "canonical_fingerprint", side_effect=ValueError("fingerprint")):
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                reader.effective_process({"process_execution": {"definition": {}}})
        class BadCopy:
            def __deepcopy__(self, memo):
                raise ValueError("copy")
        definition = {"future": BadCopy()}
        for fingerprint in [canonical_fingerprint({}), "bad"]:
            with patch.object(definition_read, "canonical_fingerprint", return_value=canonical_fingerprint({})):
                with self.assertRaisesRegex(ValueError, "copy"):
                    reader.effective_process({"process_execution": {"definition": definition, "process_fingerprint": fingerprint}})

    def test_two_projects_threaded_and_request_scope_live_reads(self):
        from processforge_core.common.request_scope import request_scope
        other = self.root / "other"
        write(other / ".pf/processes/user/shared.yml", "id: shared\nfuture: {values: [7]}\n")
        catalogs = [self.catalog, ProcessCatalogReadService(other, distribution_root=self.distribution)]
        def read(index):
            with request_scope():
                result = catalogs[index % 2].resolve_definition("shared")
                result.process["future"]["values"].append(index)
                return result.process["future"]["values"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(read, range(20))), [[1 if i % 2 == 0 else 7, i] for i in range(20)])
        with request_scope():
            self.assertEqual(self.catalog.resolve_definition("shared").process["future"]["values"], [1])
            write(self.project / ".pf/processes/user/shared.yml", "id: shared\nfuture: {values: [9]}\n")
            self.assertEqual(self.catalog.resolve_definition("shared").process["future"]["values"], [9])

    def test_copied_default_core_python_isolated_without_monolith(self):
        target = self.root / "copied"
        shutil.copytree(ROOT / "src/processforge_core", target / "src/processforge_core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        write(target / "processes/core/shared.yaml", "id: shared\nfuture: {values: [3]}\n")
        code = '''import sys, pathlib, importlib.abc
target=pathlib.Path(sys.argv[1]);sys.path.insert(0,str(target/'src'))
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname in {'processforge','processforge_core._legacy_processforge'} or fullname.startswith(('tools.','pf_runtime.')): raise AssertionError('Forbidden import '+fullname)
sys.meta_path.insert(0,Block())
from processforge_core.process_catalog.catalog_read import ProcessCatalogReadService
from processforge_core.process_catalog.definition_read import ProcessDefinitionReadService
c=ProcessCatalogReadService(target/'project')
assert c.context().distribution_root==target
assert c.resolve_definition('shared').process['future']=={'values':[3]}
assert ProcessDefinitionReadService(target/'project').effective_process({'process':'shared'})[1]=='legacy_unpinned'
for name,module in sys.modules.copy().items():
 if name.startswith('processforge_core') and getattr(module,'__file__',None): pathlib.Path(module.__file__).resolve().relative_to(target)
print('copied Core default passed without monolith/Host')
'''
        result = subprocess.run([sys.executable, "-I", "-X", "utf8", "-B", "-c", code, str(target.resolve())], cwd=target, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        print(result.stdout.strip())

    def test_retained_real_catalog_context_and_definition_parity(self):
        if BASELINE is None:
            self.skipTest("Retained originals not supplied")
        original_service = retained_module("processforge_core.process_catalog._retained_service", BASELINE / "service.py")
        original_definition = retained_module("retained_definition", BASELINE / "definition_read.py")
        documents = YamlDocumentReader(_parse_simple_yaml)
        namespace = {"Path": Path, "re": re, "Any": object, "ROOT": self.distribution,
                     "ProcessCatalogContext": type(self.catalog.context()), "load_yaml_document": documents.load,
                     "locate_flow_root": lambda root: root / ".pf",
                     "as_list": original_service._as_list,
                     "path_string_is_absolute": ContextContractInputs().path_string_is_absolute}
        exec((BASELINE / "legacy-constants.py").read_text(), namespace)
        functions = json.loads((BASELINE / "legacy-functions.json").read_text())
        for source in functions.values():
            exec(source, namespace)
        namespace["resolve_registry_relative_path"] = lambda base, raw, manifest: namespace["path_resolution_to_path"](namespace["resolve_path_with_constants"](raw, base, namespace["load_workplace_path_constants"](manifest, base)))
        comparisons = 0
        for strict in [False, True]:
            for available in [False, True]:
                context = namespace["_process_catalog_context"](self.project)
                self.assertEqual(context, self.catalog.context())
                self.assertEqual([asdict(x) for x in original_service.process_catalog_entries(context, strict=strict, include_available_official=available)], [asdict(x) for x in self.catalog.entries(strict=strict, include_available_official=available)])
                comparisons += 2
        for text in ["id: x\nfuture: {values: [1]}\n", "", "null\n", "[]\n", "id: [broken\n", "\ufeffid: unicode\n"]:
            write(self.project / "processes/custom/input.yaml", text)
            context = namespace["_process_catalog_context"](self.project)
            for ident in ["shared", "active", "inactive", "absent", "processes/custom/input.yaml", "BAD ID"]:
                for available in [False, True]:
                    left = observed(lambda: original_service.resolve_process_definition(context, ident, include_available_official=available))
                    right = observed(lambda: self.catalog.resolve_definition(ident, include_available_official=available))
                    self.assertEqual(left, right)
                    comparisons += 1
        for registry_path in ["registries/process-packs.yaml", "${CUSTOM}/packs.yaml", "${UNKNOWN}/packs.yaml", "${CYCLE}/packs.yaml", "${EMPTY}/packs.yaml"]:
            write(self.project / "workplace.yaml", f"registries:\n  process_packs: '{registry_path}'\npath_constants:\n  CUSTOM: '${{PF_WORKPLACE}}/registries'\n  CYCLE: '${{CYCLE}}'\n  EMPTY: null\n")
            self.assertEqual(namespace["_process_catalog_context"](self.project), self.catalog.context())
            comparisons += 1
        def legacy_resolve(ident):
            return original_service.resolve_process_definition(namespace["_process_catalog_context"](self.project), ident).process
        old = original_definition.ProcessDefinitionReadService(legacy_resolve, canonical_fingerprint)
        new = ProcessDefinitionReadService(self.project, catalog=self.catalog)
        for ident in ["shared", "active", "inactive", "absent"]:
            for definition in [None, [], {}, {"id": "old", "future": [1]}]:
                pins = [None, {}, {"definition": definition}, {"definition": definition, "process_fingerprint": "bad"}]
                if isinstance(definition, dict):
                    pins.append({"definition": definition, "process_fingerprint": canonical_fingerprint(definition)})
                for pin in pins:
                    run = {"process": ident, "process_execution": pin}
                    self.assertEqual(old.effective_process(copy.deepcopy(run)), new.effective_process(copy.deepcopy(run)))
                    comparisons += 1
        print("Retained original comparisons:", comparisons)


def main():
    global SCRATCH, BASELINE
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path)
    args = parser.parse_args()
    SCRATCH, BASELINE = args.scratch_root.resolve(), args.baseline_root
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CatalogTests))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
