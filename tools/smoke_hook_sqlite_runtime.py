#!/usr/bin/env python3
"""Ingress without history, live overrides, idle projections and Work recovery."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import processforge as core
from processforge_core.configuration import ProjectPFConfig
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from pf_runtime import host
from pf_runtime.codex_hooks import native_envelope
from smoke_conversation_completeness import setup_basic_project, transcript
from process_execution_smoke_support import fixture
from smoke_work_completion_recovery import prepare, interrupt, paths
from processforge_core.process_execution import ProcessExecutionService


def main():
    with tempfile.TemporaryDirectory(prefix="pf-sqlite-runtime-") as directory:
        workplace, project = setup_basic_project(Path(directory), "project")
        core.configuration_service(workplace / "configuration.yaml").update({"logging.events": False, "logging.raw_hooks": False})
        from processforge_core.work.consistency import RunTaskInputReader

        path = RunTaskInputReader().event_runtime_paths(project)[0]
        journal = ProcessEventJournal()
        baseline = journal.count(path)
        start = native_envelope({"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project), "session_id": "live"})
        prompt = native_envelope({"hook_event_name": "UserPromptSubmit", "cwd": str(project), "session_id": "live", "turn_id": "turn", "prompt": "Decision without optional history"})
        with patch.object(host, "rebuild_projection", side_effect=AssertionError("hook rebuilt history")), \
                patch.object(host, "rebuild_stage_obligations", side_effect=AssertionError("hook rebuilt stages")), \
                patch.object(ProcessEventJournal, "records", side_effect=AssertionError("hook scanned history")):
            first = host.ingest_event(start, workplace, core)
            repeated = host.ingest_event(start, workplace, core)
            captured = host.ingest_event(prompt, workplace, core)
        assert first["accepted"] and repeated["deduplicated"] and captured["chat_message_ids"]
        assert transcript(project, "live")[0]["message"]["content"] == "Decision without optional history"
        assert journal.count(path) == baseline
        pending = native_envelope({"hook_event_name": "PostToolUse", "cwd": str(project), "session_id": "live",
                                   "tool_name": "Read", "tool_use_id": "pending-dispatch"})
        with patch.object(core, "selected_hooks", return_value=[{"id": "test"}]), \
                patch.object(core, "dispatch_hooks", side_effect=OSError("after admission, before dispatch")):
            try:
                host.ingest_event(pending, workplace, core)
            except OSError:
                pass
            else:
                raise AssertionError("dispatch interruption was swallowed")
        assert journal.pending_dispatch(path)
        with patch.object(core, "dispatch_hooks", return_value=[]) as dispatch:
            host.ingest_event(pending, workplace, core)
            assert dispatch.call_count == 1
        assert not journal.pending_dispatch(path)
        raw_path = project / ".pf/runtime/agent-events/hooks.sqlite3"
        assert RawHookJournal().count(raw_path) == 0
        with RawHookJournal.connection(raw_path) as connection:
            assert connection.execute("SELECT COUNT(*) FROM receipts WHERE pending_record IS NOT NULL").fetchone()[0] == 0
        project_service = core.project_configuration_service(project / ".pf/configuration.yaml")
        project_service.create()
        project_service.update({"logging.events": True})
        tool = native_envelope({"hook_event_name": "PostToolUse", "cwd": str(project), "session_id": "live", "tool_name": "Read", "tool_use_id": "read-1"})
        host.ingest_event(tool, workplace, core)
        assert journal.count(path) == baseline + 1
        assert RawHookJournal().count(raw_path) == 0
        project_service.update({"logging.events": False, "logging.raw_hooks": True})
        tool["raw_payload"]["tool_use_id"] = "read-2"
        # Rebuild the adapter envelope so the trust boundary still verifies it.
        host.ingest_event(native_envelope(tool["raw_payload"]), workplace, core)
        assert journal.count(path) == baseline + 1
        assert RawHookJournal().count(raw_path) == 1
        host.refresh_stage_obligations(project, core)
        projection = host.stage_obligations_path(project, core)
        before = projection.read_bytes()
        with patch.object(host, "stage_obligation_rows", side_effect=AssertionError("idle full stage rebuild")):
            core.append_process_event(project, {"event_id": "evt_ordinary"}, dispatch=False)
            host.refresh_stage_obligations(project, core)
        assert projection.read_bytes() == before
        # New verification facts invalidate the projection even with history off.
        journal.append(path, {"event_id": "evt_verify", "event_type": "passed", "subject": "task",
                              "data": {"verification_fingerprint": "fp"}}, record=False)
        with patch.object(host, "stage_obligation_rows", wraps=host.stage_obligation_rows) as build:
            host.refresh_stage_obligations(project, core)
            assert build.call_count == 1
    with fixture() as (workplace, project, started):
        config = project / ".pf/configuration.yaml"
        from processforge_core.work.consistency import RunTaskInputReader
        import processforge_core.common.yaml_io as _core_common_yaml_io

        _core_common_yaml_io.write_yaml_file(config, ProjectPFConfig().with_changes({"logging.events": False}).to_dict())
        before = ProcessEventJournal().count(RunTaskInputReader().event_runtime_paths(project)[0])
        service = ProcessExecutionService(project, workplace, core)
        _proof, evidence = prepare(service, started, project)
        intent = interrupt(service, started, project, evidence, "event", "after")
        result = ProcessExecutionService(project, workplace, core).transition(run_id=started["run_id"], outcome="completed")
        assert result["action"] == "run_completed", result
        assert not paths(project, started)["intent"].exists()
        assert ProcessEventJournal().count(RunTaskInputReader().event_runtime_paths(project)[0]) == before
        assert all(core.process_event_exists(RunTaskInputReader().event_runtime_paths(project)[0], event["event_id"]) for event in intent["final"]["events"])
    print("PASS: raw/history off, live overrides, conversation delivery, no ingress rebuild/scan, unchanged tick and Work recovery without history")


if __name__ == "__main__":
    main()
