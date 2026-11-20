"""Behavioral coverage for automatic, bounded Forge hook setup."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]

# Exercise bundled source packages after explicitly adding the distribution roots.
from pf_runtime import codex_integration  # noqa: E402

from processforge_core.project import initialization  # noqa: E402
from processforge_core.project.agent_hooks import (  # noqa: E402
    AgentHookSetupError,
    ProjectAgentHookConfigurator,
)


class InitializationAdapter:
    """Minimal existing writer boundary; hook behavior uses the real service."""

    PROJECT_FLOW_ROOT = ".pf"
    PROJECT_FLOW_DIRS = []

    def __init__(self, *, complete=True):
        self.complete = complete
        self.calls = 0

    def execute_project_initialization(self, request, files):
        self.calls += 1
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return {
            "status": "complete" if self.complete else "blocked",
            "doctor": {"status": "pass" if self.complete else "fail"},
            "codex_integration": {"status": "missing", "required": False},
            "next_action": "continue",
        }

    def rel(self, path, root):
        return path.relative_to(root).as_posix()

    def project_context_snapshot_paths(self, root):
        return (
            root / ".pf/contexts/project-context.snapshot.yaml",
            root / ".pf/contexts/project-context.snapshot.md",
        )

    def project_context_check_result(self, root, **kwargs):
        return {"status": "fresh", "health": {"status": "ready"}}

    def load_yaml_document(self, path):
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def project_codex_integration_status(self, root):
        return {"status": "missing", "scope": "project-local"}


class HookFixture(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(
            os.environ.get("PF_HOOK_TEST_ROOT", tempfile.gettempdir())
        ).resolve()
        self.root = self.scratch / ("pf-project-hooks-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.workplace = self.root / "workplace.yaml"
        self.set_mode("organized")
        self.target = self.project / ".codex/hooks.json"
        self.service = ProjectAgentHookConfigurator(ROOT)
        self.addCleanup(self.cleanup_fixture)

    def cleanup_fixture(self):
        target = self.root.resolve()
        assert target != self.scratch and target.is_relative_to(self.scratch)
        shutil.rmtree(target)

    def set_mode(self, value):
        self.workplace.write_text(
            yaml.safe_dump({"coordination": {"default_project_mode": value}}),
            encoding="utf-8",
        )

    def write_config(self, value):
        self.target.parent.mkdir(exist_ok=True)
        self.target.write_text(json.dumps(value), encoding="utf-8")

    def plan(self):
        return self.service.plan(self.project, self.workplace)

    def seed_status(self):
        flow = self.project / ".pf"
        for name in (
            "process-forge.yaml",
            "assignments/first-assignment.yaml",
            "artifacts/project-onboarding-report.md",
            "contexts/project-context.snapshot.yaml",
        ):
            path = flow / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        (flow / "process-forge.local.yaml").write_text(
            yaml.safe_dump({"workplace": {"manifest": str(self.workplace)}}),
            encoding="utf-8",
        )

    def initialize(self, *, apply=True, adapter=None, service=None):
        adapter = adapter if adapter is not None else InitializationAdapter()
        files = {
            self.project
            / ".pf/process-forge.yaml": "process_forge:\n  mode: file_only\ncoordination:\n  mode: simple\n"
        }
        with patch.object(
            initialization,
            "plan_agent_entry",
            return_value={"blockers": [], "files": []},
        ):
            result = initialization.initialize_project(
                {
                    "project_root": str(self.project),
                    "workplace": str(self.workplace),
                    "apply": apply,
                },
                adapter,
                build_project_files=lambda *_: files,
                agent_hooks=service,
            )
        return result, adapter


class AgentHookTests(HookFixture):
    def test_default_service_configures_forge_even_when_project_is_file_only_and_simple(
        self,
    ):
        result, _ = self.initialize()
        self.assertTrue(self.target.is_file())
        self.assertEqual(result["result"]["codex_integration"]["status"], "installed")
        self.assertTrue(result["result"]["codex_integration"]["required"])
        self.assertEqual(
            set(json.loads(self.target.read_text())["hooks"]),
            set(codex_integration.EVENTS),
        )

    def test_garage_does_not_configure_hooks_for_an_organized_project_override(self):
        flow = self.project / ".pf"
        flow.mkdir()
        (flow / "process-forge.yaml").write_text(
            "coordination:\n  mode: organized\n", encoding="utf-8"
        )
        self.set_mode("simple")
        self.assertIsNone(self.plan())
        result, _ = self.initialize()
        self.assertFalse(self.target.exists())
        self.assertFalse(result["result"]["codex_integration"]["required"])

    def test_missing_workplace_with_explicit_permission_retains_non_forge_behavior(
        self,
    ):
        self.workplace.unlink()
        self.assertIsNone(self.plan())

    def test_dry_run_has_no_hook_or_directory_writes(self):
        before = sorted(
            path.relative_to(self.project).as_posix()
            for path in self.project.rglob("*")
        )
        result, adapter = self.initialize(apply=False)
        self.assertIn(".codex/hooks.json", result["planned_artifacts"])
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(
            before,
            sorted(
                path.relative_to(self.project).as_posix()
                for path in self.project.rglob("*")
            ),
        )

    def test_repeat_initialization_preserves_bytes_mtime_and_backup_count(self):
        self.initialize()
        before = self.target.read_bytes(), self.target.stat().st_mtime_ns
        second, _ = self.initialize()
        self.assertEqual(
            before, (self.target.read_bytes(), self.target.stat().st_mtime_ns)
        )
        self.assertEqual(second["result"]["codex_integration"]["changed_events"], [])
        self.assertEqual(list(self.target.parent.glob("*.pf-backup-*")), [])

    def test_custom_handlers_settings_unknown_events_and_exact_backup_are_preserved(
        self,
    ):
        original = {
            "description": "operator",
            "other": {"keep": [1, 2]},
            "hooks": {
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [
                            {"type": "command", "command": "custom-hook", "timeout": 99}
                        ],
                    }
                ],
                "FutureEvent": {"opaque": True},
            },
        }
        self.write_config(original)
        before = self.target.read_bytes()
        result = self.service.apply(self.plan())
        after = json.loads(self.target.read_text())
        self.assertEqual(after["other"], original["other"])
        self.assertEqual(
            after["hooks"]["FutureEvent"], original["hooks"]["FutureEvent"]
        )
        self.assertEqual(
            after["hooks"]["Stop"][0]["hooks"][0],
            original["hooks"]["Stop"][0]["hooks"][0],
        )
        backup = self.project / result["backup"]
        self.assertEqual(backup.read_bytes(), before)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_existing_managed_handler_is_not_duplicated_or_rewritten(self):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        custom = codex_integration.managed_handler(adapter, "Stop")
        custom["statusMessage"] = "operator message"
        self.write_config({"hooks": {"Stop": [{"hooks": [custom]}]}})
        self.service.apply(self.plan())
        handlers = json.loads(self.target.read_text())["hooks"]["Stop"][0]["hooks"]
        self.assertEqual(handlers, [custom])

    def test_existing_managed_handler_in_later_default_group_is_preserved(self):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        hooks = {}
        for event in codex_integration.EVENTS:
            managed = codex_integration.managed_handler(adapter, event)
            managed["statusMessage"] = "operator message"
            hooks[event] = [
                {"hooks": [{"type": "command", "command": "custom-hook"}]},
                {"hooks": [managed], "operator_field": "keep"},
            ]
        current = {"hooks": hooks, "operator_setting": "keep"}
        payload, changed = codex_integration.install_payload(current, adapter)
        self.assertEqual(changed, [])
        self.assertEqual(payload, current)
        self.write_config(current)
        before = self.target.read_bytes()
        plan = self.plan()
        self.assertEqual(plan.report["status"], "installed")
        self.assertEqual(self.service.apply(plan)["status"], "installed")
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(list(self.target.parent.glob("*.pf-backup-*")), [])

    def test_managed_handler_with_non_command_type_is_not_false_ready(self):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        for handler_type in ("prompt", "agent", None):
            with self.subTest(handler_type=handler_type):
                hooks = {}
                for event in codex_integration.EVENTS:
                    handler = codex_integration.managed_handler(adapter, event)
                    handler["type"] = handler_type
                    hooks[event] = [{"hooks": [handler]}]
                current = {"hooks": hooks}
                with self.assertRaises(SystemExit):
                    codex_integration.install_payload(current, adapter)
                self.write_config(current)
                before = self.target.read_bytes()
                writer = InitializationAdapter()
                with self.assertRaises(
                    initialization.ProjectInitializationError
                ) as caught:
                    self.initialize(adapter=writer)
                self.assertEqual(
                    caught.exception.code, "codex_hooks_configuration_invalid"
                )
                self.assertEqual(writer.calls, 0)
                self.assertEqual(self.target.read_bytes(), before)

    def test_duplicate_managed_handlers_report_conflict_without_writes(self):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        handler = codex_integration.managed_handler(adapter, "Stop")
        current = {"hooks": {"Stop": [{"hooks": [handler]}, {"hooks": [handler]}]}}
        with self.assertRaises(SystemExit):
            codex_integration.install_payload(current, adapter)
        self.write_config(current)
        before = self.target.read_bytes()
        writer = InitializationAdapter()
        with self.assertRaises(initialization.ProjectInitializationError):
            self.initialize(adapter=writer)
        self.assertEqual(writer.calls, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_manual_status_does_not_claim_invalid_or_duplicate_handlers_are_complete(
        self,
    ):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        for scenario in ("valid", "wrong-type", "duplicate"):
            with self.subTest(scenario=scenario):
                hooks = {}
                for event in codex_integration.EVENTS:
                    handler = codex_integration.managed_handler(adapter, event)
                    if scenario == "wrong-type":
                        handler["type"] = "prompt"
                    hooks[event] = [{"hooks": [handler]}]
                if scenario == "duplicate":
                    hooks["Stop"].append(
                        {"hooks": [dict(hooks["Stop"][0]["hooks"][0])]}
                    )
                self.write_config({"hooks": hooks})
                before = self.target.read_bytes()
                with (
                    patch(
                        "sys.argv",
                        [
                            "codex_integration",
                            "status",
                            "--project-root",
                            str(self.project),
                        ],
                    ),
                    patch("sys.stdout", new_callable=io.StringIO) as output,
                ):
                    self.assertEqual(codex_integration.main(), 0)
                self.assertEqual(
                    json.loads(output.getvalue())["complete"], scenario == "valid"
                )
                self.assertEqual(self.target.read_bytes(), before)

    def test_managed_handler_with_scoped_matcher_reports_conflict_without_writes(self):
        adapter = (ROOT / "tools/pf_runtime/codex_hooks.py").resolve()
        self.write_config(
            {
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "specific",
                            "hooks": [
                                codex_integration.managed_handler(adapter, "Stop")
                            ],
                        }
                    ]
                }
            }
        )
        before = self.target.read_bytes()
        self.assertEqual(self.plan().report["error"], "codex_hooks_handler_conflict")
        self.assertEqual(self.target.read_bytes(), before)

    def test_malformed_json_is_rejected_before_base_writer(self):
        self.target.parent.mkdir()
        self.target.write_text("{private-malformed", encoding="utf-8")
        before = self.target.read_bytes()
        adapter = InitializationAdapter()
        with self.assertRaises(initialization.ProjectInitializationError) as caught:
            self.initialize(adapter=adapter)
        self.assertEqual(caught.exception.code, "codex_hooks_configuration_invalid")
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_malformed_known_event_shapes_are_refused_without_writing(self):
        malformed = [
            {"hooks": []},
            {"hooks": {"Stop": {}}},
            {"hooks": {"Stop": [None]}},
            {"hooks": {"Stop": [{"hooks": {}}]}},
            {"hooks": {"Stop": [{"hooks": ["bad-handler"]}]}},
        ]
        for value in malformed:
            with self.subTest(value=value):
                self.write_config(value)
                before = self.target.read_bytes()
                plan = self.plan()
                self.assertEqual(
                    plan.report["error"], "codex_hooks_configuration_invalid"
                )
                with self.assertRaises(AgentHookSetupError):
                    self.service.apply(plan)
                self.assertEqual(self.target.read_bytes(), before)

    def test_invalid_dry_run_reports_blocked_without_changing_configuration(self):
        self.write_config({"hooks": {"Stop": 3}})
        before = self.target.read_bytes()
        result, adapter = self.initialize(apply=False)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["next_action"], "resolve_codex_hooks_blockers")
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_unavailable_packaged_adapter_is_explicit_and_prevents_base_writes(self):
        unavailable = ProjectAgentHookConfigurator(self.root / "absent distribution")
        plan = unavailable.plan(self.project, self.workplace)
        self.assertEqual(plan.report["status"], "unavailable")
        adapter = InitializationAdapter()
        with self.assertRaises(initialization.ProjectInitializationError) as caught:
            self.initialize(adapter=adapter, service=unavailable)
        self.assertEqual(caught.exception.code, "codex_hooks_adapter_unavailable")
        self.assertEqual(adapter.calls, 0)

    def test_failed_base_initialization_never_writes_hooks(self):
        result, _ = self.initialize(adapter=InitializationAdapter(complete=False))
        self.assertEqual(result["result"]["status"], "blocked")
        self.assertFalse(self.target.exists())

    def test_hook_write_failure_after_base_pass_is_not_complete_success(self):
        adapter = InitializationAdapter()
        with patch.object(
            codex_integration,
            "write_atomic",
            side_effect=PermissionError("PRIVATE-MACHINE-DETAIL"),
        ):
            with self.assertRaises(initialization.ProjectInitializationError) as caught:
                self.initialize(adapter=adapter)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(caught.exception.code, "codex_hooks_write_failed")
        self.assertNotIn("PRIVATE-MACHINE-DETAIL", str(caught.exception))
        self.assertFalse(self.target.exists())

    def test_failed_atomic_replace_retains_original_and_backup_without_staging_debris(
        self,
    ):
        self.write_config({"custom": "preserve", "hooks": {}})
        before = self.target.read_bytes()
        plan = self.plan()
        original_replace = Path.replace

        def reject_target(path, destination):
            if Path(destination) == self.target:
                raise PermissionError("fixture replacement denied")
            return original_replace(path, destination)

        with patch.object(Path, "replace", reject_target):
            with self.assertRaises(AgentHookSetupError) as caught:
                self.service.apply(plan)
        self.assertEqual(caught.exception.code, "codex_hooks_write_failed")
        self.assertEqual(self.target.read_bytes(), before)
        backups = list(self.target.parent.glob("*.pf-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)
        self.assertEqual(list(self.target.parent.glob("*.tmp")), [])

    def test_same_size_same_mtime_configuration_change_prevents_lost_update(self):
        self.write_config({"custom": "value-A", "hooks": {}})
        plan = self.plan()
        stamp = self.target.stat()
        replacement = self.target.read_text().replace("value-A", "value-B")
        self.target.write_text(replacement, encoding="utf-8")
        os.utime(self.target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(AgentHookSetupError) as caught:
            self.service.apply(plan)
        self.assertEqual(caught.exception.code, "codex_hooks_configuration_changed")
        self.assertEqual(json.loads(self.target.read_text())["custom"], "value-B")

    def test_hard_link_destination_is_rejected_before_reading_config(self):
        self.target.parent.mkdir()
        outside = self.root / "other-settings.json"
        outside.write_text('{"private": true}', encoding="utf-8")
        os.link(outside, self.target)
        with patch.object(
            codex_integration, "load_config", side_effect=AssertionError("unsafe read")
        ):
            self.assertEqual(self.plan().report["error"], "codex_hooks_unsafe_path")
        self.assertEqual(outside.read_text(), '{"private": true}')

    def test_directory_destination_is_not_treated_as_missing_config(self):
        self.target.mkdir(parents=True)
        self.assertEqual(self.plan().report["error"], "codex_hooks_unsafe_path")

    def test_invalid_workplace_yaml_or_mode_is_an_explicit_failure(self):
        for contents in (
            "coordination: [",
            "coordination:\n  default_project_mode: invalid\n",
        ):
            with self.subTest(contents=contents):
                self.workplace.write_text(contents, encoding="utf-8")
                with self.assertRaises(AgentHookSetupError) as caught:
                    self.plan()
                self.assertEqual(caught.exception.code, "codex_hooks_workplace_invalid")

    def test_status_reports_required_missing_or_invalid_hooks_truthfully(self):
        self.seed_status()
        core = InitializationAdapter()
        missing = initialization.status(
            self.project, core, workplace=str(self.workplace)
        )
        self.assertEqual(missing["state"], "repairable")
        self.assertTrue(missing["codex_integration"]["required"])
        self.assertIn("initialize", missing["repair_plan"])
        self.assertNotIn("refresh_context", missing["repair_plan"])
        self.write_config({"hooks": []})
        invalid = initialization.status(
            self.project, core, workplace=str(self.workplace)
        )
        self.assertEqual(invalid["state"], "blocked")
        self.assertIn("initialize", invalid["repair_plan"])
        self.target.unlink()
        self.service.apply(self.plan())
        complete = initialization.status(self.project, core)
        self.assertEqual(complete["state"], "complete")

    def test_garage_status_keeps_hooks_optional(self):
        self.seed_status()
        self.set_mode("simple")
        result = initialization.status(self.project, InitializationAdapter())
        self.assertEqual(result["state"], "complete")
        self.assertFalse(result["codex_integration"]["required"])
        self.assertEqual(result["repair_plan"], ["migrate_agent_entry"])

    def test_missing_hooks_cannot_downgrade_blocked_context_health(self):
        self.seed_status()
        core = InitializationAdapter()
        with patch.object(
            core,
            "project_context_check_result",
            return_value={"status": "fresh", "health": {"status": "blocked"}},
        ):
            result = initialization.status(
                self.project, core, workplace=str(self.workplace)
            )
        self.assertEqual(result["state"], "blocked")
        self.assertIn("initialize", result["repair_plan"])

    def test_setup_never_accesses_global_agent_home(self):
        with patch.object(
            Path, "home", side_effect=AssertionError("global host access")
        ):
            self.service.apply(self.plan())

    def test_default_service_uses_real_installer_without_importing_main_or_host(self):
        code = """import json, sys
from pathlib import Path
from processforge_core.project.agent_hooks import ProjectAgentHookConfigurator
service = ProjectAgentHookConfigurator()
plan = service.plan(Path(sys.argv[1]), Path(sys.argv[2]))
service.apply(plan)
assert 'processforge' not in sys.modules
assert 'processforge_core._legacy_processforge' not in sys.modules
assert 'pf_runtime.host' not in sys.modules
print(json.dumps({'configured': True, 'main_imported': False, 'host_imported': False}))
"""
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT / "tools"))),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(
            [sys.executable, "-B", "-c", code, str(self.project), str(self.workplace)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["configured"])


if __name__ == "__main__":
    unittest.main()
