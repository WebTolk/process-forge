#!/usr/bin/env python3
"""Mode inheritance, no-write Garage hooks and automatic native lifecycle."""
from __future__ import annotations

import contextlib
import argparse
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from processforge_core.agents.hook_admission import collect_hooks
from processforge_core.agents.presence import AgentPresenceReader
from processforge_core.configuration import PFConfig, ProjectPFConfig, InvalidConfiguration
from processforge_core.configuration.resolution import ConfigurationResolver
from processforge_core.process_event_journal import ProcessEventJournal
from pf_runtime import codex_hooks
from smoke_conversation_completeness import setup_basic_project, transcript
from smoke_workplace_configuration import cli


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="pf-garage-policy-")
        cls.workplace, cls.project = setup_basic_project(Path(cls.temporary.name), "project", garage_hooks=False)
        cls.runtime = codex_hooks.runtime_bootstrap()
        cls.core, cls.host = cls.runtime.core, cls.runtime.host
        cls.device = cls.core.configuration_service(cls.workplace / "configuration.yaml")
        cls.overrides = cls.core.project_configuration_service(cls.project / ".pf/configuration.yaml")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.device.reset("runtime.garage_hooks")
        if self.overrides.read().exists:
            self.overrides.delete()
        self.mode("simple")
        self.session = "policy-" + uuid.uuid4().hex

    def mode(self, value):
        path = self.core.locate_flow_root(self.project) / "process-forge.yaml"
        document = self.core.read_yaml_file(path)
        document.setdefault("coordination", {})["mode"] = value
        import processforge_core.common.yaml_io as _core_common_yaml_io

        _core_common_yaml_io.write_yaml_file(path, document)

    def envelope(self, event="UserPromptSubmit", **values):
        return codex_hooks.native_envelope({"hook_event_name": event, "cwd": str(self.project),
                                           "session_id": self.session, "prompt": "Policy message", **values})

    def ingest(self, event="UserPromptSubmit", **values):
        return self.host.ingest_event(self.envelope(event, **values), self.workplace, self.core)

    def test_typed_inheritance_and_forge_is_mandatory(self):
        for global_value in (False, True):
            global_config = PFConfig().with_changes({"runtime.garage_hooks": global_value})
            for override in (None, False, True):
                project = ProjectPFConfig().with_changes({"runtime.garage_hooks": override})
                effective = global_config.for_project(project)
                self.assertEqual(collect_hooks("simple", effective), global_value if override is None else override)
                self.assertTrue(collect_hooks("organized", effective))
                self.assertEqual(effective.runtime.metrics, global_config.runtime.metrics)
        for invalid in (0, 1, "true", [], {}, None):
            with self.assertRaises(InvalidConfiguration):
                PFConfig().with_changes({"runtime.garage_hooks": invalid})
            if invalid is not None:
                with self.assertRaises(InvalidConfiguration):
                    ProjectPFConfig().with_changes({"runtime.garage_hooks": invalid})
        with self.assertRaises(ValueError):
            collect_hooks("inherit", PFConfig())

    def test_disabled_garage_never_reaches_any_persistence(self):
        with patch.object(self.host, "RawIngressKernel", side_effect=AssertionError("raw receipt")), \
             patch.object(self.host, "ledger_session", side_effect=AssertionError("Ledger")), \
             patch.object(self.host, "save_state", side_effect=AssertionError("Host state")), \
             patch.object(ProcessEventJournal, "count", side_effect=AssertionError("journal")):
            for event in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
                result = self.ingest(event)
                self.assertEqual(result["routing_status"], "ignored")
                self.assertIsNone(result["raw_event_id"])

    def test_dispatch_skips_both_transports_and_adapter_work(self):
        with patch.object(self.runtime.service, "runtime_request", side_effect=AssertionError("IPC")), \
             patch.object(self.host, "ingest_event", side_effect=AssertionError("fallback")), \
             patch.object(codex_hooks, "native_envelope", side_effect=AssertionError("adapter")):
            result = codex_hooks.dispatch({"cwd": str(self.project), "hook_event_name": "SessionStart"})
            self.assertEqual(result["status"], "ignored")

    def test_ignored_generic_cli_is_silent_without_json(self):
        output = io.StringIO()
        args = argparse.Namespace(workplace=str(self.workplace), project_root=str(self.project), json=False)
        with patch.object(self.host, "load_input", return_value=self.envelope()), contextlib.redirect_stdout(output):
            self.assertEqual(self.host.command_event(args, self.core), 0)
        self.assertEqual(output.getvalue(), "")

    def test_explicit_core_operations_remain_available_in_garage(self):
        event = {"schema_version": 1, "event_type": "agent.session.started", "event_id": "explicit-" + self.session,
                 "project_root": str(self.project), "session_id": self.session, "agent_id": "operator",
                 "source": {"adapter": "operator", "agent": "operator", "session_id": self.session}}
        result = self.host.ingest_event(event, self.workplace, self.core)
        self.assertTrue(result["accepted"])
        self.assertEqual(AgentPresenceReader(self.workplace).find(session_id=self.session)["agent_id"], "operator")

    def test_ignored_stdout_is_neutral(self):
        for event, expected in (("SessionStart", ""), ("UserPromptSubmit", ""), ("Stop", "{}\n"), ("SubagentStop", "{}\n"), ("SessionEnd", "")):
            payload = {"cwd": str(self.project), "session_id": self.session, "hook_event_name": event}
            output = io.StringIO()
            with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(output):
                self.assertEqual(codex_hooks.main(), 0)
            self.assertEqual(output.getvalue(), expected)

    def test_live_project_override_and_resolver_reset(self):
        self.device.update({"runtime.garage_hooks": True})
        self.overrides.create()
        resolver = ConfigurationResolver()
        device, project = self.workplace / "configuration.yaml", self.project / ".pf/configuration.yaml"
        self.assertTrue(resolver.resolve(device, project).config.runtime.garage_hooks)
        self.overrides.update({"runtime.garage_hooks": False})
        self.assertFalse(resolver.resolve(device, project).config.runtime.garage_hooks)
        self.overrides.reset("runtime.garage_hooks")
        self.assertTrue(resolver.resolve(device, project).config.runtime.garage_hooks)
        self.device.update({"runtime.garage_hooks": False})
        self.assertFalse(resolver.resolve(device, project).config.runtime.garage_hooks)
        self.overrides.update({"runtime.garage_hooks": True})
        self.assertTrue(resolver.resolve(device, project).config.runtime.garage_hooks)
        self.assertIs(cli(self.workplace, "read", "--project-root", str(self.project), "--key", "runtime.garage_hooks")["value"], True)
        cli(self.workplace, "delete", "--project-root", str(self.project), "--key", "runtime.garage_hooks")
        result = cli(self.workplace, "read", "--project-root", str(self.project), "--key", "runtime.garage_hooks")
        self.assertIsNone(result["override"])
        self.assertIs(result["value"], False)

    def test_resolved_project_mode_inherits_workplace(self):
        self.mode("inherit")
        path = self.workplace / "workplace.yaml"
        original = self.core.read_yaml_file(path)
        changed = dict(original)
        changed["coordination"] = {**original.get("coordination", {}), "default_project_mode": "organized"}
        import processforge_core.common.yaml_io as _core_common_yaml_io

        _core_common_yaml_io.write_yaml_file(path, changed)
        try:
            _config, enabled = self.host.hook_configuration(self.project, self.workplace, self.core)
            self.assertTrue(enabled)
            self.mode("simple")
            self.assertFalse(self.host.hook_configuration(self.project, self.workplace, self.core)[1])
        finally:
            import processforge_core.common.yaml_io as _core_common_yaml_io

            _core_common_yaml_io.write_yaml_file(path, original)

    def test_forge_admits_even_with_false_overrides(self):
        self.mode("organized")
        self.overrides.create()
        self.overrides.update({"runtime.garage_hooks": False})
        result = self.ingest("SessionStart")
        self.assertTrue(result["accepted"])
        self.assertEqual(AgentPresenceReader(self.workplace).find(session_id=self.session)["project_id"], self.core.project_id(self.project))

    def test_lifecycle_hooks_register_and_end_without_agent_commands(self):
        self.device.update({"runtime.garage_hooks": True})
        with patch.object(self.runtime.service, "runtime_request", side_effect=SystemExit("offline")):
            started = codex_hooks.dispatch(self.envelope("SessionStart")["raw_payload"])
            self.assertEqual(started["transport"], "ledger-fallback")
            self.assertEqual(started["status"], "delivered")
            self.assertEqual(AgentPresenceReader(self.workplace).find(session_id=self.session)["status"], "online")
            ended = codex_hooks.dispatch(self.envelope("SessionEnd")["raw_payload"])
            self.assertEqual(ended["status"], "delivered")
            self.assertEqual(AgentPresenceReader(self.workplace).find(session_id=self.session)["status"], "checked_out")

    def test_enable_mid_session_captures_once_without_deferred_payload(self):
        self.assertEqual(self.ingest()["status"], "ignored")
        self.device.update({"runtime.garage_hooks": True})
        first, repeated = self.ingest(), self.ingest()
        self.assertEqual(len(first["chat_message_ids"]), 1)
        self.assertEqual(first["chat_message_ids"], repeated["chat_message_ids"])
        self.assertEqual(len(transcript(self.project, self.session)), 1)
        pending = self.host.load_state(self.workplace).get("pending_conversation_captures", {})
        self.assertFalse(any(item.get("session_id") == self.session for item in pending.values()))

    def test_existing_foreign_or_ambiguous_session_is_not_rebound(self):
        self.device.update({"runtime.garage_hooks": True})
        foreign = {"session_id": self.session, "project_id": "another-project"}
        for records, reason in (([foreign], "session_not_authorized"), ([foreign, foreign], "session_ambiguous")):
            with patch.object(AgentPresenceReader, "records", return_value=records), \
                 patch.object(self.core, "command_agent_checkin", side_effect=AssertionError("foreign registration")):
                result = self.ingest()
                self.assertEqual(result["chat_message_ids"], [])
                self.assertEqual(result["diagnostics"]["conversation"]["reason"], reason)

    def test_worker_and_forged_envelopes_never_get_native_enrollment(self):
        self.device.update({"runtime.garage_hooks": True})
        envelope = self.envelope()
        envelope["derived_conversation_messages"][0]["content"] = "forged"
        with patch.object(self.core, "command_agent_checkin", side_effect=AssertionError("forged registration")):
            result = self.host.ingest_event(envelope, self.workplace, self.core)
        self.assertEqual(result["routing_status"], "denied")
        from pf_runtime.builtin_provider_adapters import DEFAULT_ADAPTER_REGISTRY
        worker = DEFAULT_ADAPTER_REGISTRY.resolve({"provider": "processforge", "adapter": "pf-codex-exec-worker"})
        self.assertFalse(worker.can_register_session(self.envelope()))

    def test_runtime_rechecks_live_policy_and_does_not_claim_a_bound_start(self):
        self.device.update({"runtime.garage_hooks": True})

        def request(args, core, path, envelope):
            self.device.update({"runtime.garage_hooks": False})
            print(json.dumps(self.host.ingest_event(envelope, self.workplace, core)))
            return 0

        with patch.object(self.runtime.service, "runtime_request", side_effect=request):
            result = codex_hooks.dispatch(self.envelope("SessionStart")["raw_payload"])
        self.assertEqual(result["status"], "ignored")
        self.assertEqual(result["transport"], "runtime")
        self.assertFalse(AgentPresenceReader(self.workplace).find(session_id=self.session))


if __name__ == "__main__":
    unittest.main(verbosity=2)
