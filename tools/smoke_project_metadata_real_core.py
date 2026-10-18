"""File-backed metadata behavior and standalone default Core qualification."""

from __future__ import annotations

import argparse
from dataclasses import fields, FrozenInstanceError, replace
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.composition import build_project_context_service
from processforge_core.common import request_scope
from processforge_core.project.context import ProjectContextReaders
from processforge_core.work.context_documents import ContextContractInputs

SCRATCH = ROOT / ".pf" / "tmp"


class MetadataRejectingCore:
    """Fail even on metadata attribute access; other context duties are unported."""

    def __getattribute__(self, name):
        if name in {"project_id", "locate_flow_root", "load_yaml_document"}:
            raise AssertionError("Metadata must be read by its concrete Core owner")
        return super().__getattribute__(name)


class ProjectMetadataTests(unittest.TestCase):
    def test_real_manifest_shapes_and_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp) / "Проект — Example"
            manifest = root / ".pf" / "process-forge.yaml"
            manifest.parent.mkdir(parents=True)
            reader = ProjectMetadataReader(root)
            inputs = ContextContractInputs()
            cases = [
                ("project:\n  id: exact.identity\n", "exact.identity"),
                ("project:\n  id: 17\n", "17"),
                ("project:\n  id: true\n", "True"),
                ("project:\n  id: '0'\n", "0"),
                ("project:\n  id: {key: value}\n", "{'key': 'value'}"),
            ]
            for text, expected in cases:
                with self.subTest(text=text):
                    manifest.write_text(text, encoding="utf-8")
                    self.assertEqual(reader.project_id(), expected)
                    self.assertEqual(inputs.project_id(root), expected)
            from processforge_core.common.ids import safe_id
            fallback = safe_id(root.name, "project")
            for text in ("", "null\n", "[]\n", "project: []\n", "project: null\n", "project:\n  id: 0\n", "project:\n  id: false\n", "project:\n  id: ''\n", "project: [broken\n"):
                with self.subTest(text=text):
                    manifest.write_text(text, encoding="utf-8")
                    self.assertEqual(reader.project_id(), fallback)
            manifest.unlink()
            self.assertEqual(reader.project_id(), fallback)
            manifest.mkdir()
            self.assertEqual(reader.project_id(), fallback)

    def test_fresh_reads_and_manifest_result_isolation(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            manifest = root / ".pf" / "process-forge.yaml"
            manifest.parent.mkdir()
            reader = ProjectMetadataReader(root)
            manifest.write_text("project:\n  id: first\nunknown: preserved\n", encoding="utf-8")
            stat = manifest.stat()
            data = reader.manifest()
            data["project"]["id"] = "caller mutation"
            self.assertEqual(reader.project_id(), "first")
            manifest.write_text("project:\n  id: other\nunknown: preserved\n", encoding="utf-8")
            os.utime(manifest, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            self.assertEqual(manifest.stat().st_size, stat.st_size)
            self.assertEqual(reader.project_id(), "other")
            self.assertEqual(reader.manifest()["unknown"], "preserved")
            manifest.unlink()
            self.assertNotEqual(reader.project_id(), "other")
            manifest.write_text("project:\n  id: third\n", encoding="utf-8")
            self.assertEqual(reader.project_id(), "third")
            self.assertEqual(reader.flow_root(prefer_pf=False), root / ".pf")
            self.assertEqual(ContextContractInputs().locate_flow_root(root, prefer_pf=False), root / ".pf")

    def test_borrowed_document_reader_and_io_failure(self) -> None:
        class Documents:
            def __init__(self) -> None:
                self.paths: list[Path] = []

            def load(self, path: Path):
                self.paths.append(path)
                raise OSError("retained I/O failure")

        documents = Documents()
        root = Path("borrowed")
        reader = ProjectMetadataReader(root, documents)
        with self.assertRaisesRegex(OSError, "retained I/O failure"):
            reader.project_id()
        with self.assertRaisesRegex(OSError, "retained I/O failure"):
            ContextContractInputs(documents).project_id(root)
        self.assertEqual(documents.paths, [root / ".pf" / "process-forge.yaml"] * 2)

    def test_context_factory_no_io_and_borrowed_falsey_owner(self) -> None:
        class Documents:
            def __init__(self):
                self.paths = []
                self.document = {"project": {"id": 17}, "unknown": ["retained"]}

            def load(self, path):
                self.paths.append(path)
                return self.document

        class FalseyMetadata(ProjectMetadataReader):
            def __bool__(self):
                return False

        root, workplace = Path("uncreated-project"), Path("workplace")
        documents = Documents()
        metadata = FalseyMetadata(root, documents)
        with patch.object(Path, "is_file", side_effect=AssertionError("constructor filesystem I/O")), \
             patch.object(Path, "read_text", side_effect=AssertionError("constructor document I/O")):
            default = build_project_context_service(root, workplace, MetadataRejectingCore())
            borrowed = build_project_context_service(root, workplace, MetadataRejectingCore(), metadata=metadata)
        self.assertIsInstance(default.metadata, ProjectMetadataReader)
        self.assertIs(borrowed.metadata, metadata)
        self.assertIs(borrowed.metadata.documents, documents)
        self.assertFalse(documents.paths)
        self.assertEqual(default, borrowed)
        self.assertEqual(repr(default), repr(borrowed))
        self.assertEqual(hash(default), hash(borrowed))
        self.assertEqual(borrowed.__match_args__, ("project_root", "workplace_root"))
        dependency = next(item for item in fields(borrowed) if item.name == "metadata")
        self.assertTrue(dependency.kw_only)
        self.assertFalse(dependency.repr or dependency.compare)
        with self.assertRaises(FrozenInstanceError):
            borrowed.metadata = default.metadata
        self.assertEqual(borrowed.project_id(), "17")
        self.assertIs(borrowed.metadata.manifest(), documents.document)
        self.assertEqual(documents.paths, [root / ".pf/process-forge.yaml"] * 2)

    def test_default_context_factory_live_projects_and_request_isolation(self) -> None:
        from processforge_core.common.ids import safe_id

        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            roots = [Path(temp) / name for name in ("first-project", "other-project")]
            paths = [root / ".pf/process-forge.yaml" for root in roots]
            for path, identity in zip(paths, ("first", "bravo")):
                path.parent.mkdir(parents=True)
                path.write_text(f"project:\n  id: {identity}\nunknown: [retained]\n", encoding="utf-8")
            first, second = [build_project_context_service(root, Path("w"), MetadataRejectingCore()) for root in roots]
            self.assertIsNot(first.metadata, second.metadata)
            stat = paths[0].stat()
            with request_scope.request_scope() as initial:
                document = first.metadata.manifest()
                document["project"]["id"] = "caller mutation"
                document["unknown"].append("caller mutation")
                self.assertEqual(first.project_id(), "first")
                self.assertEqual(second.project_id(), "bravo")
                paths[0].write_text("project:\n  id: other\nunknown: [retained]\n", encoding="utf-8")
                os.utime(paths[0], ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertEqual((paths[0].stat().st_size, paths[0].stat().st_mtime_ns), (stat.st_size, stat.st_mtime_ns))
                self.assertEqual(first.project_id(), "other")
                self.assertEqual(first.metadata.manifest()["unknown"], ["retained"])
                self.assertEqual(second.project_id(), "bravo")
            self.assertIsNone(request_scope._CURRENT.get())
            with request_scope.request_scope() as following:
                self.assertIsNot(initial, following)
                self.assertEqual(first.project_id(), "other")
                self.assertEqual(second.project_id(), "bravo")
            self.assertIsNone(request_scope._CURRENT.get())
            paths[0].unlink()
            self.assertEqual(first.metadata.manifest(), {})
            self.assertEqual(first.project_id(), safe_id(roots[0].name, "project"))
            paths[0].write_text("project:\n  id: third\nunknown: restored\n", encoding="utf-8")
            self.assertEqual(first.project_id(), "third")
            self.assertEqual(first.metadata.manifest()["unknown"], "restored")
            paths[0].write_text("project: [broken\n", encoding="utf-8")
            self.assertIn("__yaml_error__", first.metadata.manifest())
            self.assertEqual(first.project_id(), safe_id(roots[0].name, "project"))
            self.assertEqual(second.project_id(), "bravo")
            paths[0].write_text("project:\n  id: third\n", encoding="utf-8")
            with patch.object(Path, "read_text", side_effect=OSError("retained metadata I/O failure")):
                with self.assertRaisesRegex(OSError, "retained metadata I/O failure"):
                    first.project_id()
                with self.assertRaisesRegex(OSError, "retained metadata I/O failure"):
                    first.metadata.manifest()

    def test_default_context_metadata_live_read_order_and_errors(self) -> None:
        """Trace the real default owner; replace only explicitly unported duties."""
        from processforge_core.documents.reader import YamlDocumentReader

        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root = Path(temp)
            manifest = root / ".pf/process-forge.yaml"
            manifest.parent.mkdir()
            manifest.write_text("project:\n  id: first\nunknown: retained\n", encoding="utf-8")
            original_load = YamlDocumentReader.load
            for broken in (False, True):
                for failure in ("", "check", "snapshot", "manifest-1", "readiness", "manifest-2"):
                    with self.subTest(broken=broken, failure=failure):
                        events = []
                        reads = []
                        manifest.write_text("project:\n  id: first\nunknown: retained\n", encoding="utf-8")

                        def load(documents, path):
                            events.append("manifest")
                            reads.append(path)
                            if failure == f"manifest-{len(reads)}":
                                raise OSError(failure)
                            return original_load(documents, path)

                        def check():
                            events.append("check")
                            if failure == "check":
                                raise ValueError(failure)
                            return {"broken": broken, "status": "broken" if broken else "fresh"}

                        class Snapshots:
                            def load(self):
                                events.append("snapshot")
                                if failure == "snapshot":
                                    raise ValueError(failure)
                                return {"unknown": ["kept"]}

                        def readiness(*, snapshot, check):
                            events.append("readiness")
                            self.assertIsNotNone(request_scope._CURRENT.get())
                            self.assertEqual(snapshot, {} if broken else {"unknown": ["kept"]})
                            if failure == "readiness":
                                raise ValueError(failure)
                            # Change between reads affects identity; process keeps read 1.
                            manifest.write_text("project:\n  id: other\nunknown: retained\n", encoding="utf-8")
                            return {"status": "ready"}

                        def mode(*, snapshot, session_id):
                            events.append("mode")
                            return {"mode": "garage", "session": {"id": session_id}}

                        def work():
                            events.append("work")
                            return {}

                        def process(snapshot, document):
                            events.append("process")
                            return {"manifest": document}

                        def selection(snapshot):
                            events.append("selection")
                            return {}

                        def reports(*, snapshot):
                            events.append("reports")
                            return {}

                        def diagnostics(*args):
                            events.append("diagnostics")
                            return []

                        def boundary(work):
                            events.append("boundary")
                            return None

                        def readers():
                            events.append("readers")
                            return ProjectContextReaders(mode=mode, process_summary=process,
                                derived_reports=reports, boundary=boundary)

                        service = build_project_context_service(root, Path("w"), MetadataRejectingCore())
                        service = replace(service, snapshots=Snapshots(), context_check=check,
                            context_readers=readers, resource_readiness=readiness, work_summary=work,
                            resource_selection=selection, diagnostics=diagnostics)
                        expected = ["readers", "check"]
                        if not broken:
                            expected.append("snapshot")
                        expected += ["manifest", "readiness", "mode", "work", "manifest", "process",
                                     "selection", "reports", "diagnostics", "boundary"]
                        failing = failure and not (broken and failure == "snapshot")
                        if failing:
                            marker = "manifest" if failure.startswith("manifest-") else failure
                            offset = expected.index(marker)
                            if failure == "manifest-2":
                                offset = expected.index(marker, offset + 1)
                            expected = expected[:offset + 1]
                        with patch.object(YamlDocumentReader, "load", new=load):
                            if failing:
                                error = OSError if failure.startswith("manifest-") else ValueError
                                with self.assertRaisesRegex(error, failure):
                                    service.context(session_id="s")
                            else:
                                payload = service.context(session_id="s")
                                self.assertEqual(payload["project"]["id"], "other")
                                self.assertEqual(payload["process"]["manifest"],
                                    {"project": {"id": "first"}, "unknown": "retained"})
                        self.assertEqual(events, expected)
                        self.assertEqual(reads, [manifest] * expected.count("manifest"))
                        self.assertIsNone(request_scope._CURRENT.get())

    def test_copied_core_default_without_monolith(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            directory = Path(temp)
            shutil.copytree(ROOT / "src" / "processforge_core", directory / "processforge_core", ignore=shutil.ignore_patterns("__pycache__"))
            project = directory / "project"
            manifest = project / ".pf" / "process-forge.yaml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("project:\n  id: copied-core\nunknown: [retained]\n", encoding="utf-8")
            code = """import sys
from pathlib import Path
import os
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.work.context_documents import ContextContractInputs
from processforge_core.composition import build_project_context_service
from processforge_core.common import request_scope
from processforge_core.common.ids import safe_id
root=Path(sys.argv[1])/'project'
assert ProjectMetadataReader(root).project_id()=='copied-core'
assert ContextContractInputs().project_id(root)=='copied-core'
class Core:
    def __getattribute__(self,name):
        if name in {'project_id','locate_flow_root','load_yaml_document'}:
            raise AssertionError('Legacy metadata access')
        return super().__getattribute__(name)
with patch.object(Path,'is_file',side_effect=AssertionError('Constructor I/O')), patch.object(Path,'read_text',side_effect=AssertionError('Constructor I/O')):
    service=build_project_context_service(root,Path('w'),Core())
assert service.project_id()=='copied-core'
assert isinstance(service.metadata,ProjectMetadataReader)
manifest=root/'.pf/process-forge.yaml'
stat=manifest.stat()
other=root.parent/'other-project'
other_manifest=other/'.pf/process-forge.yaml'
other_manifest.parent.mkdir(parents=True)
other_manifest.write_text('project: {id: other-project}\\n',encoding='utf8')
second=build_project_context_service(other,Path('w'),Core())
with request_scope.request_scope() as initial:
    document=service.metadata.manifest()
    document['unknown'].append('caller mutation')
    assert service.metadata.manifest()['unknown']==['retained']
    manifest.write_text('project:' + chr(10) + '  id: copied-next' + chr(10) + 'unknown: [retained]' + chr(10),encoding='utf8')
    os.utime(manifest,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    assert (manifest.stat().st_size,manifest.stat().st_mtime_ns)==(stat.st_size,stat.st_mtime_ns)
    assert service.project_id()=='copied-next'
    assert second.project_id()=='other-project'
assert request_scope._CURRENT.get() is None
with request_scope.request_scope() as following:
    assert initial is not following
    assert service.project_id()=='copied-next'
    assert second.project_id()=='other-project'
manifest.unlink()
assert service.metadata.manifest()=={}
assert service.project_id()==safe_id(root.name,'project')
manifest.write_text('project: {id: restored}\\nunknown: kept\\n',encoding='utf8')
assert service.project_id()=='restored'
manifest.write_text('project: [broken\\n',encoding='utf8')
assert '__yaml_error__' in service.metadata.manifest()
assert service.project_id()==safe_id(root.name,'project')
assert second.project_id()=='other-project'
with patch.object(Path,'read_text',side_effect=OSError('retained copied metadata I/O failure')):
    for operation in (service.project_id,service.metadata.manifest):
        try:
            operation()
        except OSError as exc:
            assert str(exc)=='retained copied metadata I/O failure'
        else:
            raise AssertionError('Missing I/O error')
assert not (Path(sys.argv[1])/'tools').exists()
assert 'processforge' not in sys.modules
assert 'processforge_core._legacy_processforge' not in sys.modules
assert not any(name.startswith('pf_runtime') for name in sys.modules)
assert not any(name.startswith('processforge_core.interfaces') for name in sys.modules)
print('COPIED_CORE_METADATA_PASS')
"""
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(directory)], capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("COPIED_CORE_METADATA_PASS", result.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch-root", type=Path)
    args, unittest_args = parser.parse_known_args()
    if args.scratch_root is not None:
        args.scratch_root.mkdir(parents=True, exist_ok=True)
        SCRATCH = args.scratch_root
    unittest.main(argv=[sys.argv[0], *unittest_args])
