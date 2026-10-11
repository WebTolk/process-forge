"""File-backed metadata behavior and standalone default Core qualification."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.work.context_documents import ContextContractInputs


class ProjectMetadataTests(unittest.TestCase):
    def test_real_manifest_shapes_and_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf" / "tmp") as temp:
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
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf" / "tmp") as temp:
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

    def test_copied_core_default_without_monolith(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".pf" / "tmp") as temp:
            directory = Path(temp)
            shutil.copytree(ROOT / "src" / "processforge_core", directory / "processforge_core", ignore=shutil.ignore_patterns("__pycache__"))
            project = directory / "project"
            manifest = project / ".pf" / "process-forge.yaml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("project:\n  id: copied-core\n", encoding="utf-8")
            code = """import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.work.context_documents import ContextContractInputs
root=Path(sys.argv[1])/'project'
assert ProjectMetadataReader(root).project_id()=='copied-core'
assert ContextContractInputs().project_id(root)=='copied-core'
assert 'processforge' not in sys.modules
assert not any(name.startswith('pf_runtime') for name in sys.modules)
print('COPIED_CORE_METADATA_PASS')
"""
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(directory)], capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("COPIED_CORE_METADATA_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
