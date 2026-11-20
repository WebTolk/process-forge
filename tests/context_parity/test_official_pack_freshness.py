"""Exercise portable official-pack freshness against real Core file readers."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from processforge_core.project.snapshot_sources import ProjectSnapshotSourcesReader
from processforge_core.project.source_check import ProjectSnapshotSourceCheckService

ROOT = Path(__file__).resolve().parents[2]
PACK_ID = "processforge.official.context-test"
PACK_SOURCE_ID = "official-pack-processforge-official-context-test-package"
PACK_BYTES = (
    b"schema_version: 1\n"
    b"kind: processforge.pack\n"
    b"origin: official\n"
    b"id: processforge.official.context-test\n"
    b"version: 1.0.0\n"
)
CLASSIFIER_BYTES = b"schema_version: 1\nid: context-test\n"


class OfficialPackFreshnessTests(unittest.TestCase):
    """Use distinct distribution roots and the same project/workplace inputs."""

    def setUp(self) -> None:
        parent = Path(
            os.environ.get(
                "PF_CONTEXT_PARITY_TEST_ROOT",
                ROOT / ".pf/tmp/pf-context-parity-20261020/tests",
            )
        )
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="freshness-", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.workplace = self.root / "workplace"
        self.source = self.root / "source"
        self.installed = self.root / "installed"
        (self.project / ".pf").mkdir(parents=True)
        (self.workplace / "registries").mkdir(parents=True)
        self.project_manifest = self.project / ".pf/process-forge.yaml"
        self.project_manifest.write_bytes(
            b"schema_version: 1\nproject:\n  id: context-test\n"
        )
        self.local_config = self.project / ".pf/process-forge.local.yaml"
        self.local_config.write_text(
            f'workplace:\n  manifest: "{self.workplace.as_posix()}/workplace.yaml"\n',
            encoding="utf-8",
            newline="\n",
        )
        (self.workplace / "workplace.yaml").write_bytes(b"schema_version: 1\n")
        self.registry = self.workplace / "registries/process-packs.yaml"
        self.registry.write_text(
            f"schema_version: 1\nprocess_packs:\n  - id: {PACK_ID}\n"
            "    status: active\n",
            encoding="utf-8",
            newline="\n",
        )
        for distribution in (self.source, self.installed):
            pack = self.pack_path(distribution)
            (pack.parent / "project-classifiers").mkdir(parents=True)
            pack.write_bytes(PACK_BYTES)
            self.classifier_path(distribution).write_bytes(CLASSIFIER_BYTES)

    @staticmethod
    def pack_path(distribution: Path) -> Path:
        """Return the same official-pack layout under an explicit root."""
        return distribution / "packs/official/context-test/package.yaml"

    def classifier_path(self, distribution: Path) -> Path:
        """Return one selected classifier alongside its official manifest."""
        return self.pack_path(distribution).parent / "project-classifiers/test.yaml"

    def reader(self, distribution: Path) -> ProjectSnapshotSourcesReader:
        """Compose the concrete reader without legacy CLI or transport objects."""
        return ProjectSnapshotSourcesReader(
            self.project, distribution_root=distribution
        )

    def snapshot(self, distribution: Path) -> dict:
        """Record existing raw fingerprint output without rewriting its shape."""
        return {"sources": {"fingerprints": self.reader(distribution).read()}}

    def compare(self, distribution: Path, snapshot: dict) -> list[str]:
        """Invoke the shared policy directly with its normal dependencies."""
        return ProjectSnapshotSourceCheckService(
            self.project, distribution_root=distribution
        ).compare(snapshot)

    def test_lf_crlf_equivalence_in_both_distribution_directions(self) -> None:
        self.pack_path(self.source).write_bytes(PACK_BYTES.replace(b"\n", b"\r\n"))
        for recorded_root, current_root in (
            (self.source, self.installed),
            (self.installed, self.source),
        ):
            with self.subTest(recorded=recorded_root.name):
                snapshot = self.snapshot(recorded_root)
                self.assertEqual(self.compare(recorded_root, snapshot), [])
                self.assertEqual(self.compare(current_root, snapshot), [])

    def test_classifier_lf_crlf_equivalence_uses_same_policy(self) -> None:
        self.classifier_path(self.source).write_bytes(
            CLASSIFIER_BYTES.replace(b"\n", b"\r\n")
        )
        for recorded_root, current_root in (
            (self.source, self.installed),
            (self.installed, self.source),
        ):
            with self.subTest(recorded=recorded_root.name):
                self.assertEqual(
                    self.compare(current_root, self.snapshot(recorded_root)), []
                )

    def test_real_change_with_same_size_and_mtime_remains_stale(self) -> None:
        snapshot = self.snapshot(self.source)
        target = self.pack_path(self.installed)
        previous = target.stat()
        target.write_bytes(PACK_BYTES.replace(b"1.0.0", b"2.0.0"))
        os.utime(target, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        self.assertEqual(
            self.compare(self.installed, snapshot),
            [f"source changed: {PACK_SOURCE_ID}"],
        )

    def test_reused_service_observes_write_after_equivalent_read(self) -> None:
        self.pack_path(self.source).write_bytes(PACK_BYTES.replace(b"\n", b"\r\n"))
        snapshot = self.snapshot(self.source)
        service = ProjectSnapshotSourceCheckService(
            self.project, distribution_root=self.installed
        )
        self.assertEqual(service.compare(snapshot), [])
        self.pack_path(self.installed).write_bytes(
            PACK_BYTES.replace(b"1.0.0", b"2.0.0")
        )
        self.assertEqual(
            service.compare(snapshot), [f"source changed: {PACK_SOURCE_ID}"]
        )

    def test_classifier_content_change_remains_stale(self) -> None:
        snapshot = self.snapshot(self.source)
        self.classifier_path(self.installed).write_bytes(
            CLASSIFIER_BYTES + b"enabled: false\n"
        )
        self.assertIn(
            "source changed: official-pack-processforge-official-context-test-test",
            self.compare(self.installed, snapshot),
        )

    def test_write_between_fingerprint_and_probe_cannot_hide_observed_drift(
        self,
    ) -> None:
        self.pack_path(self.source).write_bytes(PACK_BYTES.replace(b"\n", b"\r\n"))
        snapshot = self.snapshot(self.source)
        target = self.pack_path(self.installed)
        target.write_bytes(PACK_BYTES.replace(b"1.0.0", b"2.0.0"))

        class RacingReader(ProjectSnapshotSourcesReader):
            def official_pack_checksum_variants(
                self, source_ids: set[str]
            ) -> dict[str, tuple[str, str, str]]:
                target.write_bytes(PACK_BYTES)
                return super().official_pack_checksum_variants(source_ids)

        service = ProjectSnapshotSourceCheckService(
            self.project,
            distribution_root=self.installed,
            sources=RacingReader(self.project, distribution_root=self.installed),
        )
        self.assertEqual(
            service.compare(snapshot), [f"source changed: {PACK_SOURCE_ID}"]
        )

    def test_lone_carriage_returns_are_not_normalized(self) -> None:
        snapshot = self.snapshot(self.source)
        self.pack_path(self.installed).write_bytes(PACK_BYTES.replace(b"\n", b"\r"))
        self.assertEqual(
            self.compare(self.installed, snapshot),
            [f"source changed: {PACK_SOURCE_ID}"],
        )

    def test_comments_are_not_semantically_ignored(self) -> None:
        snapshot = self.snapshot(self.source)
        self.pack_path(self.installed).write_bytes(PACK_BYTES + b"# changed input\n")
        self.assertEqual(
            self.compare(self.installed, snapshot),
            [f"source changed: {PACK_SOURCE_ID}"],
        )

    def test_project_fingerprints_remain_raw_byte_strict(self) -> None:
        snapshot = self.snapshot(self.source)
        self.project_manifest.write_bytes(
            self.project_manifest.read_bytes().replace(b"\n", b"\r\n")
        )
        self.assertIn(
            "source changed: project_manifest",
            self.compare(self.installed, snapshot),
        )

    def test_workplace_registry_fingerprints_remain_raw_byte_strict(self) -> None:
        snapshot = self.snapshot(self.source)
        self.registry.write_bytes(self.registry.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(
            any(
                reason.startswith("source changed: workplace-process-pack-registry-")
                for reason in self.compare(self.installed, snapshot)
            )
        )

    def test_added_classifier_remains_visible(self) -> None:
        snapshot = self.snapshot(self.source)
        target = self.classifier_path(self.installed).with_name("additional.yaml")
        target.write_bytes(b"schema_version: 1\nid: additional\n")
        self.assertIn(
            "source added: official-pack-processforge-official-context-test-additional",
            self.compare(self.installed, snapshot),
        )

    def test_removed_pack_remains_visible(self) -> None:
        snapshot = self.snapshot(self.source)
        self.pack_path(self.installed).unlink()
        self.assertIn(
            f"source removed: {PACK_SOURCE_ID}",
            self.compare(self.installed, snapshot),
        )

    def test_raw_fingerprint_shape_and_digest_are_preserved(self) -> None:
        target = self.pack_path(self.source)
        content = PACK_BYTES.replace(b"\n", b"\r\n")
        target.write_bytes(content)
        record = next(
            row
            for row in self.reader(self.source).read()
            if row["id"] == PACK_SOURCE_ID
        )
        self.assertEqual(set(record), {"id", "path", "kind", "checksum", "private"})
        self.assertEqual(record["checksum"], hashlib.sha256(content).hexdigest())

    def test_no_workplace_keeps_file_only_operation(self) -> None:
        self.local_config.unlink()
        snapshot = self.snapshot(self.source)
        self.assertEqual(self.compare(self.installed, snapshot), [])
        self.assertFalse(
            any(
                row["kind"] == "official-process-pack"
                for row in snapshot["sources"]["fingerprints"]
            )
        )

    def test_inactive_pack_does_not_become_a_context_source(self) -> None:
        self.registry.write_text(
            f"schema_version: 1\nprocess_packs:\n  - id: {PACK_ID}\n"
            "    status: disabled\n",
            encoding="utf-8",
            newline="\n",
        )
        snapshot = self.snapshot(self.source)
        self.pack_path(self.installed).write_bytes(
            PACK_BYTES.replace(b"1.0.0", b"2.0.0")
        )
        self.assertEqual(self.compare(self.installed, snapshot), [])

    def test_core_import_does_not_load_legacy_or_transport(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; "
                "from processforge_core.project.source_check import "
                "ProjectSnapshotSourceCheckService; "
                "assert not any(name == 'processforge' or "
                "name.startswith('pf_runtime') for name in sys.modules)",
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
