"""Exercise bootstrap binding directly through the Core reader."""

from __future__ import annotations

import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.fresh_project import (
    RECEIPT,
    create_project_storage_root,
)
from processforge_core.maintenance.project_event_owner import (
    INERT_LEGACY_PROJECT_TEMPLATE,
)
from processforge_core.project.bootstrap_binding import (
    ProjectBootstrapBinding,
    ProjectBootstrapBindingReader,
)

_HAS_PYYAML = find_spec("yaml") is not None


class ProjectBootstrapBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.flow = self.root / ".pf"
        self.manifest = self.flow / "process-forge.yaml"
        self.local = self.flow / "process-forge.local.yaml"
        self.proposed = {self.manifest: "project:\n  id: proposed-owner\n"}
        self.reader = ProjectBootstrapBindingReader()

    def read(
        self,
        *,
        workplace_manifest: Path | None = None,
        force: bool = False,
        repair: bool = False,
    ) -> ProjectBootstrapBinding:
        return self.reader.read(
            self.root,
            self.proposed,
            workplace_manifest=workplace_manifest,
            force=force,
            repair=repair,
        )

    def test_pending_receipt_reads_proposal_without_writing(self) -> None:
        self.assertTrue(create_project_storage_root(self.root))
        receipt_path = self.flow / RECEIPT
        before = receipt_path.read_bytes()
        self.assertEqual(
            self.read(),
            ProjectBootstrapBinding(json.loads(before), "proposed-owner", None),
        )
        self.assertEqual(
            {path for path in self.flow.rglob("*") if path.is_file()}, {receipt_path}
        )
        self.assertEqual(receipt_path.read_bytes(), before)

    def test_non_forced_live_binding_wins_and_rereads_disk(self) -> None:
        self.flow.mkdir()
        self.manifest.write_text("project:\n  id: ' live-owner '\n", encoding="utf-8")
        self.local.write_text(
            "workplace:\n  manifest: nested/../workplace/workplace.yaml\n",
            encoding="utf-8",
        )
        self.proposed.update({self.manifest: "project: [", self.local: "workplace: ["})
        result = self.read(workplace_manifest=self.root / "other/workplace.yaml")
        self.assertEqual(
            result,
            ProjectBootstrapBinding(None, " live-owner ", self.root / "workplace"),
        )

        self.manifest.write_text("project:\n  id: changed-owner\n", encoding="utf-8")
        self.assertEqual(
            self.read(),
            ProjectBootstrapBinding(None, "changed-owner", self.root / "workplace"),
        )

    def test_absolute_reference_keeps_unresolved_spelling(self) -> None:
        manifest = self.root / "alias/../workplace/workplace.yaml"
        self.proposed[self.local] = f"workplace:\n  manifest: '{manifest.as_posix()}'\n"
        self.assertEqual(
            self.read(workplace_manifest=manifest),
            ProjectBootstrapBinding(None, "proposed-owner", manifest.parent),
        )
        with self.assertRaisesRegex(MaintenanceError, "^storage_enrollment_conflict$"):
            self.read(workplace_manifest=manifest.resolve())

    @unittest.skipUnless(_HAS_PYYAML, "requires the PyYAML parsing path")
    def test_live_and_proposed_yaml_errors_keep_their_precedence(self) -> None:
        self.flow.mkdir()
        self.manifest.write_text("- scalar\n", encoding="utf-8")
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            self.read(force=True)
        self.manifest.write_text("project: [", encoding="utf-8")
        with self.assertRaisesRegex(
            MaintenanceError, "^storage_configuration_invalid$"
        ):
            self.read(force=True)
        self.manifest.unlink()
        self.proposed[self.manifest] = "- scalar\n"
        with self.assertRaisesRegex(
            MaintenanceError, "^storage_configuration_invalid$"
        ):
            self.read()
        self.proposed[self.manifest] = "project: ["
        with self.assertRaisesRegex(
            MaintenanceError, "^storage_configuration_invalid$"
        ):
            self.read()

    def test_invalid_receipt_precedes_yaml(self) -> None:
        self.assertTrue(create_project_storage_root(self.root))
        receipt_path = self.flow / RECEIPT
        receipt = json.loads(receipt_path.read_bytes())
        receipt_path.write_text(
            json.dumps({**receipt, "creation_id": []}), encoding="utf-8"
        )
        self.manifest.write_text("project: [", encoding="utf-8")
        with self.assertRaisesRegex(
            MaintenanceError, "^storage_fresh_receipt_invalid$"
        ):
            self.read(force=True)

    def test_only_exact_inert_template_is_eligible_for_forced_onboarding(self) -> None:
        self.flow.mkdir()
        self.manifest.write_bytes(INERT_LEGACY_PROJECT_TEMPLATE)
        self.assertEqual(self.read(force=True).project_id, "proposed-owner")
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            self.read(force=True, repair=True)
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            self.read()
        self.local.touch()
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            self.read(force=True)
        self.local.unlink()
        self.manifest.write_bytes(INERT_LEGACY_PROJECT_TEMPLATE.replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            self.read(force=True)

    def test_repair_requires_the_surviving_owner_even_without_force(self) -> None:
        self.flow.mkdir()
        self.manifest.write_text("project:\n  id: live-owner\n", encoding="utf-8")
        with self.assertRaisesRegex(MaintenanceError, "^storage_enrollment_conflict$"):
            self.read(repair=True)
        self.proposed[self.manifest] = "project:\n  id: live-owner\n"
        self.assertEqual(self.read(repair=True).project_id, "live-owner")

    def test_missing_pyyaml_uses_the_mapping_fallback_for_both_inputs(self) -> None:
        self.flow.mkdir()
        self.local.write_text(
            "workplace:\n  manifest: workplace/workplace.yaml\n",
            encoding="utf-8",
        )
        self.proposed[self.manifest] += "- ignored by the mapping parser\n"
        expected = ProjectBootstrapBinding(
            None, "proposed-owner", self.root / "workplace"
        )
        with patch.dict(sys.modules, {"yaml": None}):
            self.assertEqual(self.read(), expected)
