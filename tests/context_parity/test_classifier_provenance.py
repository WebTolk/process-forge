"""Keep classifier provenance portable without hiding real context drift."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from processforge_core.project.classifier_sources import ProjectClassifierSourceReader
from processforge_core.project.initialization_discovery import ProjectDiscoveryReader
from processforge_core.project.resolved_comparison import (
    ProjectSnapshotResolvedComparison,
)
from processforge_core.project.snapshot_sources import ProjectSnapshotSourcesReader
from processforge_core.project.source_check import ProjectSnapshotSourceCheckService

ROOT = Path(__file__).resolve().parents[2]
PACK_ID = "processforge.official.provenance-test"
CLASSIFIER_ID = "fixture.distribution.classifier"
CLASSIFIER_SOURCE_ID = "official-pack-processforge-official-provenance-test-fixture"
CLASSIFIER_PATH = Path(
    "packs/official/provenance-test/project-classifiers/fixture.yaml"
)
CLASSIFIER_TEXT = """schema_version: 1
kind: processforge.project_classifier
id: fixture.distribution.classifier
status: active
rules:
  - id: fixture.python-rule
    when:
      any:
        - exists: app.py
    classify_as:
      project_types:
        - fixture.python
      tags:
        - fixture
    confidence: high
"""


def write_text(path: Path, text: str) -> None:
    """Write disposable fixtures with deterministic newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class ClassifierProvenanceTests(unittest.TestCase):
    """Use real registries, document readers and freshness comparisons."""

    def setUp(self) -> None:
        parent = Path(
            os.environ.get(
                "PF_CONTEXT_PARITY_TEST_ROOT",
                ROOT / ".pf/tmp/pf-context-parity-20261020/tests",
            )
        )
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="provenance-", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.outer = self.root / "outer-distribution"
        self.make_distribution(self.outer)
        self.project = self.outer / "project with spaces"
        write_text(self.project / "app.py", "pass\n")
        write_text(
            self.project / ".pf/process-forge.yaml",
            "schema_version: 1\nproject:\n  id: provenance-test\n",
        )
        self.workplace = self.outer / ".pf/tmp/workplace"
        self.manifest = self.workplace / "workplace.yaml"
        write_text(self.manifest, "schema_version: 1\n")
        write_text(
            self.project / ".pf/process-forge.local.yaml",
            f'workplace:\n  manifest: "{self.manifest.as_posix()}"\n',
        )
        self.pack_registry = self.workplace / "registries/process-packs.yaml"
        write_text(
            self.pack_registry,
            f"schema_version: 1\nprocess_packs:\n  - id: {PACK_ID}\n"
            "    status: active\n",
        )
        self.installed = self.workplace / "core"
        self.sibling = self.outer / "sibling-source"
        self.nested = self.project / ".pf/tmp/candidate/source"
        self.layouts = (self.installed, self.sibling, self.nested)
        for distribution in self.layouts:
            self.make_distribution(distribution)

    def make_distribution(self, root: Path) -> None:
        """Use the existing four-marker recognition contract, not a mock."""
        write_text(root / "bin/pf.py", "# fixture launcher\n")
        write_text(root / "tools/processforge.py", "# fixture marker\n")
        write_text(root / "schemas/process-definition.schema.json", "{}\n")
        (root / "processes/core").mkdir(parents=True, exist_ok=True)
        pack = root / "packs/official/provenance-test"
        write_text(
            pack / "package.yaml",
            "schema_version: 1\nkind: processforge.pack\norigin: official\n"
            f"id: {PACK_ID}\nprovides:\n  project_classifiers:\n"
            f"    - {CLASSIFIER_ID}\n",
        )
        write_text(
            pack / "project-classifiers/registry-entry.yaml",
            "schema_version: 1\nproject_classifiers:\n"
            f"  - id: {CLASSIFIER_ID}\n"
            "    path: project-classifiers/fixture.yaml\n    status: active\n",
        )
        write_text(root / CLASSIFIER_PATH, CLASSIFIER_TEXT)

    def classify(self, distribution: Path) -> dict[str, Any]:
        """Select the classifier through the active official pack registry."""
        return ProjectDiscoveryReader(
            ProjectClassifierSourceReader(distribution)
        ).classify_project(self.project, workplace_manifest=self.manifest)

    def snapshot(self, distribution: Path) -> dict[str, Any]:
        return {
            "project_classification": self.classify(distribution),
            "sources": {
                "fingerprints": ProjectSnapshotSourcesReader(
                    self.project, distribution_root=distribution
                ).read()
            },
        }

    def source_reasons(self, snapshot: dict[str, Any], distribution: Path) -> list[str]:
        return ProjectSnapshotSourceCheckService(
            self.project, distribution_root=distribution
        ).compare(snapshot)

    def test_active_pack_classification_and_freshness_match_all_layouts(
        self,
    ) -> None:
        baseline = self.snapshot(self.installed)
        self.assertEqual(
            baseline["project_classification"]["matched_rules"],
            [
                {
                    "classifier": CLASSIFIER_ID,
                    "rule": "fixture.python-rule",
                    "confidence": "high",
                    "source": CLASSIFIER_PATH.as_posix(),
                }
            ],
        )
        for distribution in self.layouts:
            with self.subTest(layout=distribution.name):
                reader = ProjectClassifierSourceReader(distribution)
                classifier = distribution / CLASSIFIER_PATH
                self.assertEqual(
                    reader.project_classifier_paths(self.manifest, self.project),
                    [classifier],
                )
                self.assertEqual(
                    reader.processforge_distribution_root_for_path(classifier),
                    distribution,
                )
                current = self.snapshot(distribution)
                self.assertEqual(
                    current["project_classification"],
                    baseline["project_classification"],
                )
                self.assertEqual(
                    ProjectSnapshotResolvedComparison().compare(baseline, current),
                    ([], [], [], []),
                )
                self.assertEqual(self.source_reasons(baseline, distribution), [])

    def test_project_that_is_distribution_keeps_relative_identity(self) -> None:
        self.make_distribution(self.project)
        self.assertEqual(self.classify(self.project), self.classify(self.installed))

    def test_local_custom_and_incomplete_distribution_paths_remain_distinct(
        self,
    ) -> None:
        reader = ProjectClassifierSourceReader(self.nested)
        for relative in (
            ".pf/project-classifiers/fixture.yaml",
            "custom/fixture.yaml",
            ".pf/tmp/incomplete/source/packs/official/provenance-test/"
            "project-classifiers/fixture.yaml",
        ):
            with self.subTest(path=relative):
                path = self.project / relative
                write_text(path, CLASSIFIER_TEXT)
                self.assertEqual(
                    reader.processforge_distribution_root_for_path(path), self.outer
                )
                self.assertEqual(
                    reader.project_classifier_source_label(
                        path, self.project, workplace_manifest=self.manifest
                    ),
                    relative,
                )
                self.assertNotEqual(relative, CLASSIFIER_PATH.as_posix())

    def test_same_basename_in_distribution_does_not_collapse_paths(self) -> None:
        reader = ProjectClassifierSourceReader(self.nested)
        for relative in (
            "custom/fixture.yaml",
            "packs/official/other/project-classifiers/fixture.yaml",
        ):
            path = self.nested / relative
            write_text(path, CLASSIFIER_TEXT)
            self.assertEqual(
                reader.project_classifier_source_label(path, self.project), relative
            )
            self.assertNotEqual(relative, CLASSIFIER_PATH.as_posix())

    def test_workplace_guard_rejects_enclosing_distribution(self) -> None:
        reader = ProjectClassifierSourceReader(self.nested)
        path = self.workplace / "project-classifiers/fixture.yaml"
        write_text(path, CLASSIFIER_TEXT)
        self.assertEqual(
            reader.processforge_distribution_root_for_path(path), self.outer
        )
        self.assertEqual(
            reader.project_classifier_source_label(
                path, self.project, workplace_manifest=self.manifest
            ),
            "fixture.yaml",
        )
        nested_workplace = self.project / ".pf/tmp/local-workplace"
        nested_manifest = nested_workplace / "workplace.yaml"
        write_text(nested_manifest, "schema_version: 1\n")
        nested_path = nested_workplace / "project-classifiers/fixture.yaml"
        write_text(nested_path, CLASSIFIER_TEXT)
        self.assertEqual(
            reader.project_classifier_source_label(
                nested_path, self.project, workplace_manifest=nested_manifest
            ),
            ".pf/tmp/local-workplace/project-classifiers/fixture.yaml",
        )

    def test_changed_rules_still_change_classification_and_fingerprints(
        self,
    ) -> None:
        baseline = self.snapshot(self.installed)
        write_text(
            self.nested / CLASSIFIER_PATH,
            CLASSIFIER_TEXT.replace("fixture.python", "fixture.changed"),
        )
        current = self.snapshot(self.nested)
        classification = current["project_classification"]
        self.assertEqual(classification["project_types"], ["fixture.changed"])
        self.assertEqual(
            classification["matched_rules"][0]["source"], CLASSIFIER_PATH.as_posix()
        )
        self.assertEqual(
            ProjectSnapshotResolvedComparison().compare(baseline, current)[0],
            ["project classification changed"],
        )
        self.assertIn(
            f"source changed: {CLASSIFIER_SOURCE_ID}",
            self.source_reasons(baseline, self.nested),
        )

    def test_comment_only_change_is_not_hidden_by_equal_classification(self) -> None:
        baseline = self.snapshot(self.installed)
        write_text(self.nested / CLASSIFIER_PATH, CLASSIFIER_TEXT + "# changed\n")
        self.assertEqual(self.classify(self.nested), baseline["project_classification"])
        self.assertIn(
            f"source changed: {CLASSIFIER_SOURCE_ID}",
            self.source_reasons(baseline, self.nested),
        )

    def test_inactive_pack_is_not_loaded_from_nested_source(self) -> None:
        write_text(
            self.pack_registry,
            f"schema_version: 1\nprocess_packs:\n  - id: {PACK_ID}\n"
            "    status: disabled\n",
        )
        classification = self.classify(self.nested)
        self.assertEqual(classification["loaded_classifiers"], [])
        self.assertEqual(classification["matched_rules"], [])
