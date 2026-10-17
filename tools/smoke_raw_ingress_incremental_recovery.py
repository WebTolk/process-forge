#!/usr/bin/env python3
"""Raw transaction rollback, restart/retry, payload retention and project isolation."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel
from processforge_core.sqlite_storage import transaction


def main():
    with tempfile.TemporaryDirectory(prefix="pf-raw-sqlite-") as directory:
        root = Path(directory)
        first = RawIngressKernel(root, flow_root=root / "first/.pf", record_raw=False)
        second = RawIngressKernel(root, flow_root=root / "second/.pf", record_raw=True)
        event = NativeAgentEvent("generic", "test", "reply", {"content": "sensitive test payload"},
                                 native_event_id="reply-1", source_session_id="session")
        receipt = first.ingest(event)
        assert receipt.accepted and first.storage.count(first.database) == 0
        assert list(first.records())[0]["record"]["raw_payload"] == event.raw_payload
        # New process owner recovers an admitted but unfinished native input.
        reopened = RawIngressKernel(root, flow_root=root / "first/.pf", record_raw=False)
        assert reopened.ingest(event).deduplicated
        reopened.finish(receipt.raw_event_id, {"routing_status": "routed", "normalized_event_ids": []})
        assert not list(reopened.records())
        assert reopened.result(receipt.raw_event_id)["routing_status"] == "routed"
        assert reopened.ingest(event).deduplicated
        assert not list(reopened.records()), "retry restored a completed payload with logging off"
        with reopened.storage.connection(reopened.database) as connection:
            assert connection.execute("SELECT pending_record FROM receipts").fetchone()[0] is None
            assert connection.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0] == 0
        assert not second.ingest(event).deduplicated
        assert second.storage.count(second.database) == 1
        conflict = NativeAgentEvent("generic", "test", "reply", {"content": "changed"}, native_event_id="reply-1")
        assert not first.ingest(conflict).accepted
        with first.storage.connection(first.database) as connection:
            assert connection.execute("SELECT record FROM quarantine").fetchone()[0] is None
        # Failure before commit leaves no identity; retry may commit normally.
        failed = NativeAgentEvent("generic", "test", "reply", {"n": 2}, native_event_id="reply-2")
        original = first.storage._accept

        def abort(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("simulated loss before commit")

        with patch.object(first.storage, "_accept", side_effect=abort):
            try:
                first.ingest(failed)
            except OSError:
                pass
            else:
                raise AssertionError("failure swallowed")
        assert not first.ingest(failed).deduplicated
        with first.storage.connection(first.database) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    print("PASS: raw rollback/reopen/retry, pending cleanup, raw-off quarantine and project isolation")


if __name__ == "__main__":
    main()
