#!/usr/bin/env python3
"""Six real producers, indexed deduplication, transaction and dispatch recovery."""
from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core
from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher
from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.sqlite_storage import JournalError


def worker(project, index, barrier):
    barrier.wait(timeout=30)
    for number in range(50):
        ProcessEventRecorder().append_process_event(Path(project), {"event_id": f"evt_{index}_{number}",
                                                 "session": {"id": f"session-{index}"},
                                                 "data": {"text": "Журнал 🌍"}}, dispatch=False)
        ProcessEventRecorder().append_process_event(Path(project), {"event_id": "evt_shared"}, dispatch=False)


def main():
    with tempfile.TemporaryDirectory(prefix="pf-sqlite-concurrency-") as directory:
        project = Path(directory)
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(6)
        processes = [ctx.Process(target=worker, args=(str(project), index, barrier)) for index in range(6)]
        started = time.perf_counter()
        for process in processes:
            process.start()
        for process in processes:
            process.join(60)
            assert process.exitcode == 0, process.exitcode
        elapsed = time.perf_counter() - started
        from processforge_core.agents.hook_policy import HookDispatchPolicy
        from processforge_core.work.consistency import RunTaskInputReader

        path = RunTaskInputReader().event_runtime_paths(project)[0]
        journal = ProcessEventJournal()
        assert journal.count(path) == 301
        assert len(journal.page(path, session_id="session-3")) == 50
        assert journal.contains(path, "evt_shared")
        assert not journal.contains(path, "absent")
        assert journal.append(path, {"event_id": "evt_off"}, record=False)
        assert journal.contains(path, "evt_off") and journal.get(path, "evt_off") is None
        assert not journal.append(path, {"event_id": "evt_off"})
        assert journal.count(path) == 301
        # A mid-batch failure rolls back admission and optional history together.
        try:
            journal.append_many(path, [{"event_id": "evt_rollback"}, {}])
        except JournalError:
            pass
        else:
            raise AssertionError("invalid batch accepted")
        assert not ProcessEventJournal().contains(path, "evt_rollback")
        # Historical growth cannot trigger Python-level full-file/history reads.
        journal.append_many(path, ({"event_id": f"evt_bulk_{index}", "event_type": "bulk"} for index in range(100_000)))
        with patch.object(Path, "read_bytes", side_effect=AssertionError("full binary read")), \
                patch.object(Path, "read_text", side_effect=AssertionError("full text read")), \
                patch.object(journal, "records", side_effect=AssertionError("full history scan")):
            assert journal.append(path, {"event_id": "evt_after_bulk"})
            assert journal.contains(path, "evt_bulk_99999")
            assert journal.count(path) == 100_302
        with journal.connection(path) as connection:
            plan = " ".join(str(tuple(row)) for row in connection.execute(
                "EXPLAIN QUERY PLAN SELECT 1 FROM admissions WHERE event_id=?", ("evt_bulk_99999",)))
            assert "INDEX" in plan and "SCAN admissions" not in plan, plan
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # Commit-before-dispatch remains recoverable with optional history off.
        hooks = [{"id": "test"}]
        with patch.object(HookDispatchPolicy, "selected_hooks", return_value=hooks), \
                patch.object(RuntimeHookDispatcher, "dispatch_hooks", side_effect=OSError("simulated dispatch failure")):
            try:
                ProcessEventRecorder().append_process_event(project, {"event_id": "evt_dispatch"})
            except OSError:
                pass
            else:
                raise AssertionError("dispatch failure swallowed")
        assert len(journal.pending_dispatch(path)) == 1
        with patch.object(RuntimeHookDispatcher, "dispatch_hooks", return_value=[]) as dispatch:
            core.flush_pending_event_dispatches(project)
            assert dispatch.call_count == 1
        assert not journal.pending_dispatch(path)
        print(json.dumps({"status": "pass", "producers": 6, "concurrent_unique": 301,
                          "history_rows": journal.count(path), "concurrent_seconds": round(elapsed, 3),
                          "lookup_plan": plan}))


if __name__ == "__main__":
    main()
