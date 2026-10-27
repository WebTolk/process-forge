"""Source CLI, generated native command and local ingress proof without services."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml
from test_agent_hooks import ROOT, HookFixture


@unittest.skipUnless(
    os.name == "nt", "The bundled hook command currently uses the Windows py launcher"
)
class LocalIngressTests(HookFixture):
    def cli(self, *arguments, expect=0):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(ROOT / "tools/processforge.py"),
                *arguments,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def seed_real_workplace(self):
        device = self.root / "device"
        self.cli(
            "workplace-init",
            "--profile",
            "generic",
            "--workplace",
            str(device),
            "--apply",
        )
        self.workplace = device / "workplace.yaml"
        manifest = yaml.safe_load(self.workplace.read_text(encoding="utf-8"))
        manifest["coordination"].update(
            {
                "default_project_mode": "organized",
                "director_enabled": True,
                "director_office_enabled": True,
            }
        )
        self.workplace.write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        from processforge_core.project.coordination_state import (
            ProjectCoordinationStateService,
        )

        for directory in (
            ProjectCoordinationStateService().director_office_paths(device).values()
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return device

    def onboard(self, device):
        return self.cli(
            "project-onboard",
            "--project-root",
            str(self.project),
            "--workplace",
            str(device),
            "--type",
            "generic",
            "--apply",
        )

    def run_generated_handler(self, event, payload):
        groups = json.loads(self.target.read_text(encoding="utf-8"))["hooks"][event]
        handler = groups[0]["hooks"][0]
        result = subprocess.run(
            handler["commandWindows"],
            cwd=self.project,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_fresh_cli_identity_precedes_journal_and_survives_repeat(self):
        from processforge_core.process_event_journal import ProcessEventJournal

        device = self.seed_real_workplace()
        journal = ProcessEventJournal()
        expected = [
            "project.onboarding.started",
            "project.flow_root.created",
            "project.platform.detected",
            "project.snapshot.refreshed",
            "launcher.project_runtime.created",
            "assignment.created",
            "project.doctor.passed",
            "project.onboarding.completed",
        ]
        for command in ("project-onboard", "project-init", "init-project"):
            with self.subTest(command=command):
                project = self.root / command
                owner = "explicit-owner-" + command
                answers = self.root / (command + "-answers.yaml")
                answers.write_text(
                    yaml.safe_dump({"project": {"id": owner}}), encoding="utf-8"
                )
                arguments = (
                    command,
                    "--project-root",
                    str(project),
                    "--workplace",
                    str(device),
                    "--type",
                    "generic",
                    "--answers",
                    str(answers),
                    "--apply",
                )
                history = []
                manifest_before = None
                for extra in ((), (), ("--force",)):
                    initialized = yaml.safe_load(self.cli(*arguments, *extra).stdout)
                    self.assertEqual(initialized["status"], "complete")
                    self.assertEqual(initialized["project"]["id"], owner)
                    flow = project / ".pf"
                    manifest = (flow / "process-forge.yaml").read_bytes()
                    self.assertEqual(yaml.safe_load(manifest)["project"]["id"], owner)
                    if manifest_before is not None:
                        self.assertEqual(manifest, manifest_before)
                    manifest_before = manifest
                    local = yaml.safe_load(
                        (flow / "process-forge.local.yaml").read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        Path(local["workplace"]["manifest"]).resolve(),
                        self.workplace.resolve(),
                    )
                    binding_path = flow / "data/execution-storage.json"
                    # Unsealed Source has no qualified native publication and
                    # therefore does not initialize fresh SQL execution storage.
                    self.assertFalse(binding_path.exists())
                    records = list(
                        journal.records(flow / "runtime/events/events.sqlite3")
                    )
                    self.assertTrue(records)
                    self.assertTrue(all(error is None for _, _, error in records))
                    events = [row for _, row, _ in records]
                    self.assertEqual(events[: len(history)], history)
                    added = events[len(history) :]
                    self.assertEqual([row["event_type"] for row in added], expected)
                    self.assertTrue(
                        all(row["project"]["project_id"] == owner for row in events)
                    )
                    self.assertEqual(
                        len({row["event_id"] for row in events}), len(events)
                    )
                    self.assertEqual(added[0]["data"]["command"], command)
                    history = events

    def test_real_init_generated_command_and_ingress_binding_replay_and_mcp(self):
        device = self.seed_real_workplace()
        initialized = yaml.safe_load(self.onboard(device).stdout)
        self.assertEqual(initialized["status"], "complete")
        self.assertEqual(initialized["codex_integration"]["status"], "installed")
        self.assertTrue(initialized["codex_integration"]["required"])
        project_manifest = yaml.safe_load(
            (self.project / ".pf/process-forge.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(project_manifest["process_forge"]["mode"], "file_only")
        self.assertFalse((self.project / ".claude/settings.json").exists())
        self.assertFalse((self.project / ".gemini/settings.json").exists())

        session = "forge-hooks-local-proof"
        native = {
            "cwd": str(self.project),
            "session_id": session,
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        started = self.run_generated_handler("SessionStart", native)
        self.assertIn(session, started.stdout)
        completed = {
            **native,
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "turn_id": "turn-proof",
            "tool_use_id": "use-proof",
        }
        self.run_generated_handler("PostToolUse", completed)

        from pf_runtime import codex_hooks, host, mcp_server

        from processforge_core.agents.presence import AgentPresenceReader
        from processforge_core.process_event_journal import ProcessEventJournal

        journal = ProcessEventJournal()
        event_path = self.project / ".pf/runtime/events/events.sqlite3"

        def events():
            return [row for _sequence, row, _error in journal.records(event_path)]

        matching = [
            row
            for row in events()
            if row.get("session", {}).get("id") == session
            and row.get("event_type") == "agent.command.completed"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(
            matching[0]["project"]["project_id"], project_manifest["project"]["id"]
        )
        presence = AgentPresenceReader(device).find(session_id=session)
        self.assertEqual(
            Path(presence["project_root"]).resolve(), self.project.resolve()
        )
        before_repeat = len(events())
        self.run_generated_handler("PostToolUse", completed)
        self.assertEqual(len(events()), before_repeat)

        runtime = codex_hooks.runtime_bootstrap()
        configuration, collecting = host.hook_configuration(
            self.project, device, runtime.core
        )
        self.assertFalse(configuration.config.runtime.garage_hooks)
        self.assertTrue(collecting)
        forged = copy.deepcopy(codex_hooks.native_envelope(completed))
        forged["derived_event"]["session_id"] = "different-session"
        denied = host.ingest_event(forged, device, runtime.core)
        self.assertEqual(denied["routing_status"], "denied")
        self.assertEqual(
            denied["diagnostics"]["adapter"]["reason"], "provenance_rejected"
        )
        self.assertEqual(len(events()), before_repeat)

        # Exercise the source MCP call adapter directly; no MCP server is started.
        self.target.unlink()
        mcp = mcp_server.tool_result(
            "pf.project_initialization.initialize",
            {"apply": True, "session_id": session},
            device,
            session,
            runtime,
        )
        self.assertEqual(mcp["result"]["codex_integration"]["status"], "installed")
        self.assertTrue(self.target.is_file())
        other = self.root / "other project"
        (other / ".pf").mkdir(parents=True)
        (other / ".pf/process-forge.yaml").write_text(
            "project:\n  id: other-project\n", encoding="utf-8"
        )
        with self.assertRaises(Exception) as caught:
            mcp_server.tool_result(
                "pf.project_initialization.initialize",
                {"apply": True, "session_id": session, "project_root": str(other)},
                device,
                session,
                runtime,
            )
        self.assertIn("session_project_mismatch", str(caught.exception))
        self.assertFalse((other / ".codex/hooks.json").exists())

        evidence_path = os.environ.get("PF_HOOK_EVENT_EVIDENCE")
        if evidence_path:
            evidence = {
                "status": "pass",
                "boundary": "source local fixtures",
                "native_handler_executed": True,
                "envelope_contract": "codex-hooks.v1",
                "events": ["SessionStart", "PostToolUse"],
                "normalized_event": "agent.command.completed",
                "correct_project_and_session": True,
                "repeat_effect_count": 1,
                "forged_session_provenance": "denied",
                "forge_gatekeeper_enabled_with_garage_hooks_false": True,
                "source_mcp_same_initialization": "pass",
                "source_mcp_wrong_project": "session_project_mismatch",
                "services_started": False,
                "live_user_host_changed": False,
            }
            Path(evidence_path).write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
            )

    def test_real_cli_malformed_configuration_fails_without_base_rewrites(self):
        device = self.seed_real_workplace()
        self.onboard(device)
        self.target.write_text("{malformed-private-config", encoding="utf-8")
        protected = [
            self.target,
            self.project / ".pf/contexts/project-context.snapshot.yaml",
            self.project / "AGENTS.md",
        ]
        before = {
            path: (path.read_bytes(), path.stat().st_mtime_ns) for path in protected
        }
        refused = self.cli(
            "project-onboard",
            "--project-root",
            str(self.project),
            "--workplace",
            str(device),
            "--type",
            "generic",
            "--force",
            "--apply",
            expect=1,
        )
        self.assertIn("codex_hooks_configuration_invalid", refused.stderr)
        self.assertEqual(
            before,
            {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in protected},
        )

    def test_generated_command_delivers_on_materialized_core_template_fixture(self):
        """Prove native delivery separately from the OS-private entry transaction."""
        device = self.seed_real_workplace()
        from processforge_core.project.file_templates import ProjectFileTemplateBuilder

        files = ProjectFileTemplateBuilder(ROOT).build_project_files(
            self.project, self.workplace, {"project": {"type": "generic"}}
        )
        for path, contents in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        configured = self.service.apply(self.plan())
        self.assertEqual(configured["status"], "installed")
        session = "forge-hooks-template-proof"
        native = {
            "cwd": str(self.project),
            "session_id": session,
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        started = self.run_generated_handler("SessionStart", native)
        self.assertIn(session, started.stdout)
        completed = {
            **native,
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "turn_id": "template-turn",
            "tool_use_id": "template-use",
        }
        self.run_generated_handler("PostToolUse", completed)

        from pf_runtime import codex_hooks, host, mcp_server

        from processforge_core.agents.presence import AgentPresenceReader
        from processforge_core.process_event_journal import ProcessEventJournal

        journal = ProcessEventJournal()
        path = self.project / ".pf/runtime/events/events.sqlite3"

        def events():
            return [row for _sequence, row, _error in journal.records(path)]

        matching = [
            row
            for row in events()
            if row.get("session", {}).get("id") == session
            and row.get("event_type") == "agent.command.completed"
        ]
        self.assertEqual(len(matching), 1)
        project_manifest = yaml.safe_load(
            (self.project / ".pf/process-forge.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            matching[0]["project"]["project_id"], project_manifest["project"]["id"]
        )
        presence = AgentPresenceReader(device).find(session_id=session)
        self.assertEqual(
            Path(presence["project_root"]).resolve(), self.project.resolve()
        )
        before = len(events())
        self.run_generated_handler("PostToolUse", completed)
        self.assertEqual(len(events()), before)
        runtime = codex_hooks.runtime_bootstrap()
        config, collect = host.hook_configuration(self.project, device, runtime.core)
        self.assertFalse(config.config.runtime.garage_hooks)
        self.assertTrue(collect)
        forged = copy.deepcopy(codex_hooks.native_envelope(completed))
        forged["derived_event"]["session_id"] = "different-session"
        denied = host.ingest_event(forged, device, runtime.core)
        self.assertEqual(denied["routing_status"], "denied")
        self.assertEqual(
            denied["diagnostics"]["adapter"]["reason"], "provenance_rejected"
        )
        self.assertEqual(len(events()), before)
        other = self.root / "other project"
        (other / ".pf").mkdir(parents=True)
        (other / ".pf/process-forge.yaml").write_text(
            "project:\n  id: other-project\n", encoding="utf-8"
        )
        with self.assertRaises(Exception) as caught:
            mcp_server.tool_result(
                "pf.project_initialization.initialize",
                {"apply": True, "session_id": session, "project_root": str(other)},
                device,
                session,
                runtime,
            )
        self.assertIn("session_project_mismatch", str(caught.exception))
        self.assertFalse((other / ".codex/hooks.json").exists())
        evidence_path = os.environ.get("PF_HOOK_EVENT_EVIDENCE")
        if evidence_path:
            evidence = {
                "status": "pass",
                "boundary": "materialized Core-template fixture plus real native handler/Host ingress",
                "full_source_cli_init": "blocked_native_entry_private_acl",
                "native_handler_executed": True,
                "envelope_contract": "codex-hooks.v1",
                "events": ["SessionStart", "PostToolUse"],
                "normalized_event": "agent.command.completed",
                "correct_project_and_session": True,
                "repeat_effect_count": 1,
                "forged_session_provenance": "denied",
                "forge_gatekeeper_enabled_with_garage_hooks_false": True,
                "source_mcp_wrong_project": "session_project_mismatch",
                "services_started": False,
                "live_user_host_changed": False,
            }
            Path(evidence_path).write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
            )


if __name__ == "__main__":
    unittest.main()
