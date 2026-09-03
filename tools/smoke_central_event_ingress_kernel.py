#!/usr/bin/env python3
"""Focused file-based smoke for the raw ingress kernel."""

from __future__ import annotations

import json
import multiprocessing
import shutil
import socket
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pf_runtime.raw_ingress_kernel import (
    NativeAgentEvent,
    RawIngressError,
    RawIngressKernel,
    contained_path,
    recover_stale_lock,
)


FIXED_TIME = datetime(2026, 8, 15, 12, tzinfo=timezone.utc)


def submit(root: str, number: int) -> None:
    kernel = RawIngressKernel(root)
    receipt = kernel.ingest(
        NativeAgentEvent(
            "codex",
            "codex-hooks",
            "PostToolUse",
            {"number": number},
            native_event_id=f"event-{number}",
        ),
        FIXED_TIME,
    )
    if not receipt.accepted or receipt.deduplicated:
        raise AssertionError(receipt)


def check() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        kernel = RawIngressKernel(root, max_payload_bytes=128)
        event = NativeAgentEvent(
            "codex",
            "codex-hooks",
            "PostToolUse",
            {"text": "hello"},
            native_event_id="stable-1",
            native_id_scope="session",
            source_session_id="session-1",
        )
        first = kernel.ingest(event, FIXED_TIME)
        duplicate = kernel.ingest(event, FIXED_TIME)
        assert first.accepted and not first.deduplicated
        assert duplicate.accepted and duplicate.deduplicated
        assert duplicate.raw_location == first.raw_location

        conflict = kernel.ingest(
            NativeAgentEvent(
                "codex", "codex-hooks", "PostToolUse", {"text": "changed"},
                native_event_id="stable-1", native_id_scope="session", source_session_id="session-1",
            ),
            FIXED_TIME,
        )
        assert not conflict.accepted and conflict.diagnostics["code"] == "native_id_payload_conflict"
        assert list((root / "runtime" / "agent-events" / "errors" / "poisoned").glob("*.json"))

        indexes = root / "runtime" / "agent-events" / "indexes"
        shutil.rmtree(indexes)
        recovered = kernel.ingest(event, FIXED_TIME)
        assert recovered.accepted and recovered.deduplicated

        try:
            kernel.ingest(NativeAgentEvent("x", "a", "t", {1: "bad"}), FIXED_TIME)
        except RawIngressError:
            pass
        else:
            raise AssertionError("non-string JSON key was accepted")
        try:
            kernel.ingest(NativeAgentEvent("x", "a", "t", {"data": "x" * 256}), FIXED_TIME)
        except RawIngressError:
            pass
        else:
            raise AssertionError("oversized payload was accepted")
        try:
            contained_path(root, "..", "escape")
        except Exception:
            pass
        else:
            raise AssertionError("path traversal was accepted")

        stale = root / "runtime" / "agent-events" / "indexes" / ".manual.lock"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(json.dumps({"pid": 999999, "host": socket.gethostname(), "created_at": time.time() - 600}), encoding="utf-8")
        assert recover_stale_lock(stale, stale_seconds=1)

        processes = [multiprocessing.Process(target=submit, args=(str(root), number)) for number in range(16)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(30)
            assert process.exitcode == 0, process.exitcode
        shards = list((root / "runtime" / "agent-events" / "raw" / "v1").rglob("*.ndjson"))
        count = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in shards)
        assert count == 17, count


if __name__ == "__main__":
    check()
    print("PASS: central event ingress raw kernel smoke")
