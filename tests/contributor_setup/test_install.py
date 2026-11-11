"""Exercise safe first installation and preservation of an existing workplace."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "tools/install-contributor-knowledge.py"
SPEC = importlib.util.spec_from_file_location("contributor_install", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class ContributorInstallTests(unittest.TestCase):
    """Use isolated workplaces and actual ZIP payloads without network access."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pf-contributor-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workplace = self.root / "workplace with spaces"
        self.registries = self.workplace / "registries"
        self.registries.mkdir(parents=True)
        (self.workplace / "workplace.yaml").write_text(
            "schema_version: 1\n", encoding="utf-8"
        )
        (self.registries / "package-roots.yaml").write_text(
            yaml.safe_dump(
                {
                    "package_roots": [
                        {"id": "global", "path": "${PF_WORKPLACE}/packages"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.other = {
            "type": "tool_definition",
            "id": "existing-tool",
            "version": "2.0.0",
        }
        self.registry = self.registries / "installed-subjects.yaml"
        self.registry.write_text(
            yaml.safe_dump({"schema_version": 1, "subjects": [self.other]}),
            encoding="utf-8",
        )
        self.archives = self.root / "downloads"
        self.archives.mkdir()
        self.package = {
            "id": "docs.sample",
            "version": "1.0.1",
            "archive": "sample.zip",
            "source_id": "sample",
            "download_url": "https://github.com/WebTolk/example/releases/download/v1.0.1/sample.zip",
        }
        data = self.archive()
        self.package["sha256"] = hashlib.sha256(data).hexdigest()
        (self.archives / "sample.zip").write_bytes(data)
        self.profile = self.root / "profile.json"
        self.profile.write_text(
            json.dumps({"packages": [self.package]}), encoding="utf-8"
        )
        self.profile_patch = patch.object(INSTALLER, "PROFILE", self.profile)
        self.profile_patch.start()
        self.addCleanup(self.profile_patch.stop)

    def archive(self, extra_path: str | None = None) -> bytes:
        stream = io.BytesIO()
        document = b"A shared reference document.\n"
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(
                "package.yaml",
                yaml.safe_dump({"id": "docs.sample", "version": "1.0.1"}),
            )
            archive.writestr("resources/reference.md", document)
            archive.writestr(
                "sources.json",
                json.dumps(
                    {
                        "documents": [
                            {
                                "path": "resources/reference.md",
                                "sha256": hashlib.sha256(document).hexdigest(),
                            }
                        ]
                    }
                ),
            )
            if extra_path:
                archive.writestr(extra_path, "outside")
        return stream.getvalue()

    def test_preview_does_not_change_workplace(self) -> None:
        before = {
            p.relative_to(self.workplace): p.read_bytes()
            for p in self.workplace.rglob("*")
            if p.is_file()
        }
        INSTALLER.install(self.workplace, self.archives, False)
        after = {
            p.relative_to(self.workplace): p.read_bytes()
            for p in self.workplace.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)
        self.assertFalse((self.workplace / "packages").exists())

    def test_install_keeps_other_records_and_repeat_is_unchanged(self) -> None:
        INSTALLER.install(self.workplace, self.archives, True)
        data = yaml.safe_load(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(data["subjects"][0], self.other)
        self.assertEqual(data["subjects"][1]["install_path"], "packages/docs.sample")
        before = self.registry.read_bytes()
        INSTALLER.install(self.workplace, self.archives, True)
        self.assertEqual(self.registry.read_bytes(), before)

    def test_existing_files_are_not_overwritten(self) -> None:
        destination = self.workplace / "packages/docs.sample"
        destination.mkdir(parents=True)
        sentinel = destination / "work.txt"
        sentinel.write_bytes(b"Keep local work")
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(ValueError, "Existing package"):
            INSTALLER.install(self.workplace, self.archives, True)
        self.assertEqual(sentinel.read_bytes(), b"Keep local work")
        self.assertEqual(self.registry.read_bytes(), before)

    def test_bad_digest_does_not_install_or_register(self) -> None:
        (self.archives / "sample.zip").write_bytes(b"unexpected download")
        before = self.registry.read_bytes()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            INSTALLER.install(self.workplace, self.archives, True)
        self.assertFalse((self.workplace / "packages/docs.sample").exists())
        self.assertEqual(self.registry.read_bytes(), before)

    def test_verified_hash_does_not_allow_archive_path_escape(self) -> None:
        for path in (
            "../escape.txt",
            "/absolute.txt",
            "C:/drive.txt",
            "..\\escape.txt",
        ):
            with self.subTest(path=path):
                data = self.archive(path)
                package = {**self.package, "sha256": hashlib.sha256(data).hexdigest()}
                with self.assertRaisesRegex(ValueError, "Unsafe archive member"):
                    INSTALLER.checked_archive(data, package)


if __name__ == "__main__":
    unittest.main()
