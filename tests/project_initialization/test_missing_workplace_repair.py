"""Repair workplace resolution with real resolver and template builder.

Status/preflight fixtures and a writer sink isolate the service boundary; these
tests do not qualify native publication, onboarding or live transport ingress.
"""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.project import initialization
from processforge_core.project.coordination_state import ProjectCoordinationStateService
from processforge_core.project.file_templates import ProjectFileTemplateBuilder


class MissingWorkplaceRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.flow = self.project / ".pf"
        self.flow.mkdir(parents=True)
        self.manifest = self.flow / "process-forge.yaml"
        self.manifest.write_text(
            "project:\n  id: repair-fixture\n  type: generic\n"
            "coordination:\n  mode: inherit\n"
            "platform_contracts: []\n",
            encoding="utf-8",
        )
        self.local = self.flow / "process-forge.local.yaml"
        self.local.write_text("schema_version: 1\n", encoding="utf-8")
        self.workplace = self.root / "workplace" / "workplace.yaml"
        self.workplace.parent.mkdir()
        self.workplace.write_text("schema_version: 1\n", encoding="utf-8")
        self.distribution = Path(__file__).resolve().parents[2]
        self.builder = ProjectFileTemplateBuilder(self.distribution)
        self.callback = Mock(side_effect=self.builder.build_project_files)
        self.core = Mock()
        self.core.load_yaml_document.side_effect = YamlDocumentReader(
            _parse_simple_yaml
        ).load
        self.core.execute_project_initialization.return_value = {"status": "complete"}
        self.before = {"state": "repairable", "snapshot": {}, "agent_entry": {}}
        self.plan = {"blockers": [], "action": "unchanged"}
        self.status = self.enterContext(
            patch.object(initialization, "status", return_value=self.before)
        )
        self.preflight = self.enterContext(
            patch.object(initialization, "plan_agent_entry", return_value=self.plan)
        )

    def request(self, **extra):
        return {
            "project_root": str(self.project),
            "repair_action": "restore_deterministic_artifacts",
            "apply": True,
            **extra,
        }

    def repair(self, **extra):
        return initialization.repair_project(
            self.request(**extra), self.core, build_project_files=self.callback
        )

    def inventory(self):
        return {
            path.relative_to(self.root).as_posix(): (
                hashlib.sha256(path.read_bytes()).hexdigest()
                if path.is_file()
                else "directory"
            )
            for path in self.root.rglob("*")
        }

    def assert_no_generation(self):
        self.callback.assert_not_called()
        self.core.execute_project_initialization.assert_not_called()

    def test_none_refuses_before_builder_or_writer_without_file_effects(self):
        self.assertIsNone(
            ProjectCoordinationStateService().resolve_workplace_manifest(self.local)
        )
        before = self.inventory()
        sequence = Mock()
        sequence.attach_mock(self.status, "status")
        sequence.attach_mock(self.preflight, "preflight")
        sequence.attach_mock(self.core.load_yaml_document, "manifest")
        with self.assertRaises(initialization.ProjectInitializationError) as caught:
            self.repair()
        self.assertEqual(caught.exception.code, "workplace_manifest_required")
        self.assert_no_generation()
        self.core.load_yaml_document.assert_called_once_with(self.manifest)
        self.status.assert_called_once()
        self.preflight.assert_called_once()
        self.assertEqual(
            [call[0] for call in sequence.mock_calls],
            ["status", "preflight", "manifest"],
        )
        self.assertEqual(self.inventory(), before)

    def test_real_builder_preserves_file_directory_and_local_path_branches(self):
        answers = {
            "project": {"id": "repair-fixture", "type": "generic", "platforms": []},
            "coordination": {"mode": "inherit"},
        }
        expected = self.builder.build_project_files(
            self.project, self.workplace.resolve(), answers
        )
        for branch in ("file", "directory", "relative", "absolute"):
            with self.subTest(branch=branch):
                self.callback.reset_mock()
                self.core.execute_project_initialization.reset_mock()
                extra = {}
                if branch == "file":
                    extra["workplace"] = str(self.workplace)
                elif branch == "directory":
                    extra["workplace"] = str(self.workplace.parent)
                else:
                    reference = (
                        "../../workplace/workplace.yaml"
                        if branch == "relative"
                        else self.workplace.as_posix()
                    )
                    self.local.write_text(
                        f"workplace:\n  manifest: '{reference}'\n", encoding="utf-8"
                    )
                before = self.inventory()
                result = self.repair(**extra)
                self.assertTrue(result["applied"])
                self.callback.assert_called_once_with(
                    self.project, self.workplace.resolve(), answers
                )
                self.core.execute_project_initialization.assert_called_once_with(
                    {
                        "project_root": self.project,
                        "project_type": "generic",
                        "force": False,
                        "command": "project-init-repair",
                        "agent_entry_plan": self.plan,
                    },
                    expected,
                )
                self.assertEqual(self.inventory(), before)

    def test_missing_workplace_file_remains_a_path_for_real_builder(self):
        self.workplace.unlink()
        result = self.repair(workplace=str(self.workplace))
        self.assertTrue(result["applied"])
        self.assertEqual(self.callback.call_args.args[1], self.workplace.resolve())
        self.core.execute_project_initialization.assert_called_once()

    def test_preview_returns_before_manifest_and_none_guard(self):
        self.local.unlink()
        self.manifest.unlink()
        result = self.repair(apply=False)
        self.assertEqual(result["status"], "planned")
        self.assertFalse(result["applied"])
        self.assert_no_generation()
        self.core.load_yaml_document.assert_not_called()

    def test_entry_blocker_keeps_precedence_over_manifest_and_none_guard(self):
        self.plan["blockers"] = ["entry_owned_region_modified"]
        self.local.unlink()
        self.manifest.unlink()
        with self.assertRaises(initialization.ProjectInitializationError) as caught:
            self.repair()
        self.assertEqual(caught.exception.code, "entry_owned_region_modified")
        self.assert_no_generation()
        self.core.load_yaml_document.assert_not_called()

    def test_status_failure_keeps_precedence_over_preflight(self):
        self.status.side_effect = OSError("status failure")
        with self.assertRaisesRegex(OSError, "status failure"):
            self.repair()
        self.preflight.assert_not_called()
        self.assert_no_generation()

    def test_missing_local_file_keeps_read_error_before_guard(self):
        self.local.unlink()
        with self.assertRaises(FileNotFoundError):
            self.repair()
        self.assert_no_generation()
        self.core.load_yaml_document.assert_called_once_with(self.manifest)

    def test_manifest_read_failure_keeps_precedence(self):
        self.core.load_yaml_document.side_effect = OSError("manifest failure")
        with self.assertRaisesRegex(OSError, "manifest failure"):
            self.repair()
        self.assert_no_generation()

    def test_callback_and_writer_failures_are_not_hidden(self):
        self.callback.side_effect = OSError("callback failure")
        with self.assertRaisesRegex(OSError, "callback failure"):
            self.repair(workplace=str(self.workplace))
        self.core.execute_project_initialization.assert_not_called()
        self.callback.side_effect = self.builder.build_project_files
        self.core.execute_project_initialization.side_effect = OSError(
            "mandatory writer failure"
        )
        with self.assertRaisesRegex(OSError, "mandatory writer failure"):
            self.repair(workplace=str(self.workplace))

    def test_other_repair_actions_do_not_enter_none_guard(self):
        self.local.unlink()
        self.core.execute_project_repair.return_value = {"status": "complete"}
        result = self.repair(repair_action="refresh_context")
        self.assertTrue(result["applied"])
        self.core.execute_project_repair.assert_called_once_with(
            self.project, workplace=None, reason="manual"
        )
        self.core.execute_project_codex_integration_repair.return_value = {
            "status": "complete"
        }
        self.assertTrue(self.repair(repair_action="install_codex_hooks")["applied"])
        with patch.object(
            initialization, "apply_agent_entry", return_value={"status": "complete"}
        ) as apply_entry:
            self.assertTrue(self.repair(repair_action="migrate_agent_entry")["applied"])
            apply_entry.assert_called_once_with(self.project, self.plan)
        self.assert_no_generation()
