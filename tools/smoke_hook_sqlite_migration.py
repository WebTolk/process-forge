#!/usr/bin/env python3
"""Non-destructive, repeatable migration with explicit invalid/conflict barriers."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("hook_migrator", ROOT / "tools/migrate-hook-journals.py")
migrator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrator)
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import JournalError, JournalMigrationRequired
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel, raw_event_id, raw_payload_hash, stable_native_identity_key


def main():
    with tempfile.TemporaryDirectory(prefix="pf-hook-migration-") as directory:
        root = Path(directory)
        project, workplace = root / "project", root / "workplace"
        flow = project / ".pf"
        flow.mkdir(parents=True)
        (flow / "process-forge.yaml").write_text("schema_version: 1\nproject: {id: migration}\n", encoding="utf-8")
        old_events = flow / "runtime/events/events.ndjson"
        old_events.parent.mkdir(parents=True)
        event = {"event_id": "evt_original", "event_type": "decision", "data": {"text": "Решение"}}
        old_events.write_text(json.dumps(event, ensure_ascii=False) + "\n{broken\n", encoding="utf-8")
        old_raw = workplace / "runtime/agent-events/raw/v1/2026/10/17/01.ndjson"
        old_raw.parent.mkdir(parents=True)
        kernel = RawIngressKernel(workplace)
        native = NativeAgentEvent("test", "adapter", "reply", {"answer": "kept"}, native_id_scope="session",
                                 native_event_id_stable=False, source_session_id="session", source_project_ref=str(project))
        record = kernel._raw_record(native, raw_event_id(native), raw_payload_hash(native.raw_payload),
                                    stable_native_identity_key(native), datetime.now(timezone.utc))
        # Legacy records omit identity controls; existing IDs still must verify.
        record.pop("native_id_scope")
        record.pop("native_event_id_stable")
        other = dict(record, source_project_ref=str(root / "other-project"))
        old_raw.write_text(json.dumps(record) + "\n" + json.dumps(other) + "\n", encoding="utf-8")
        originals = (old_events.read_bytes(), old_raw.read_bytes())
        path = flow / "runtime/events/events.sqlite3"
        try:
            ProcessEventJournal().append(path, {"event_id": "evt_must_block"})
        except JournalMigrationRequired:
            pass
        else:
            raise AssertionError("legacy writer bypassed migration")
        assert migrator.migrate(project, workplace)["blocked"]
        assert not path.exists()
        plan = migrator.migrate(project, workplace, skip_invalid=True)
        assert plan["invalid"] == 1 and plan["other_project_raw"] == 1 and not path.exists()
        first = migrator.migrate(project, workplace, apply=True, skip_invalid=True)
        assert first["status"] == "ready" and first["stored_counts"] == {"events": 1, "raw": 1}
        assert ProcessEventJournal().get(path, "evt_original") == event
        raw_path = flow / "runtime/agent-events/hooks.sqlite3"
        assert list(RawHookJournal().records(raw_path))[0]["record"] == record
        second = migrator.migrate(project, workplace, apply=True, skip_invalid=True)
        assert second["stored_counts"] == first["stored_counts"]
        assert originals == (old_events.read_bytes(), old_raw.read_bytes())
        # Interrupted import cannot be used normally, and a retry finishes it.
        with patch.object(migrator.RawHookJournal, "_accept", side_effect=OSError("interrupted import")):
            try:
                migrator.migrate(project, workplace, apply=True, skip_invalid=True)
            except OSError:
                pass
            else:
                raise AssertionError("interrupted import accepted")
        try:
            ProcessEventJournal().count(path)
        except JournalMigrationRequired:
            pass
        else:
            raise AssertionError("partial migration visible")
        migrator.migrate(project, workplace, apply=True, skip_invalid=True)
        original_rows = migrator._rows
        passes = 0

        def changed_after_read(*args, **kwargs):
            nonlocal passes
            passes += 1
            yield from original_rows(*args, **kwargs)
            if passes == 2:
                with old_events.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"event_id": "evt_late"}) + "\n")

        with patch.object(migrator, "_rows", side_effect=changed_after_read):
            try:
                migrator.migrate(project, workplace, apply=True, skip_invalid=True)
            except JournalError as exc:
                assert "source_changed" in str(exc)
            else:
                raise AssertionError("source changed after import was accepted")
        old_events.write_bytes(originals[0])
        migrator.migrate(project, workplace, apply=True, skip_invalid=True)
        changed = dict(event, data={"text": "conflict"})
        old_events.write_text(json.dumps(event) + "\n" + json.dumps(changed) + "\n", encoding="utf-8")
        try:
            migrator.migrate(project, workplace, apply=True, skip_invalid=True)
        except JournalError as exc:
            assert "conflict" in str(exc)
        else:
            raise AssertionError("identity conflict accepted")
        assert ProcessEventJournal().count(path) == 1
    print("PASS: streaming project migration, dry run, explicit damage skip, stable IDs, originals, repeat, conflict and partial-import recovery")


if __name__ == "__main__":
    main()
