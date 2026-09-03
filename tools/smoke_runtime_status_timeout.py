#!/usr/bin/env python3
"""Prove Runtime status does not wait for scheduler reconciliation."""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pf_runtime import service  # noqa: E402


class CoreStub:
    PROCESSFORGE_VERSION = "smoke"

    @staticmethod
    def iter_agent_presence(_workplace_root: Path) -> list[dict[str, object]]:
        return []


def main() -> int:
    lock_acquired = threading.Event()

    def hold_scheduler_lock() -> None:
        with service.host.state_lock():
            lock_acquired.set()
            time.sleep(2.2)

    holder = threading.Thread(target=hold_scheduler_lock, daemon=True)
    holder.start()
    if not lock_acquired.wait(timeout=1):
        raise AssertionError("scheduler lock was not acquired")

    original_load_state = service.host.load_state
    try:
        service.host.load_state = lambda _root: {"projects": [], "sessions": {}}
        runtime = service.RuntimeProcess.__new__(service.RuntimeProcess)
        runtime.workplace_root = Path(".")
        runtime.core = CoreStub()
        runtime.state_lock = threading.RLock()
        runtime.state = {"status": "ready", "health": "ready"}
        started = time.monotonic()
        payload = runtime.status_payload()
        elapsed = time.monotonic() - started
    finally:
        service.host.load_state = original_load_state
        holder.join(timeout=3)

    if payload.get("status") != "ready" or payload.get("health") != "ready":
        raise AssertionError(payload)
    if elapsed >= 1.0:
        raise AssertionError(f"status waited for scheduler reconciliation: {elapsed:.3f}s")

    with tempfile.TemporaryDirectory(prefix="pf-runtime-status-tail-") as raw:
        journal = Path(raw) / "events.ndjson"
        with journal.open("w", encoding="utf-8", newline="\n") as handle:
            for index in range(50_000):
                handle.write(f'{{"event_id":"history-{index:05d}","event_type":"tool"}}\n')
            handle.write('{"event_id":"latest","event_type":"session.end"}\n')
            handle.write("not-json\n")
        started = time.monotonic()
        latest = service.last_json_object(journal)
        tail_elapsed = time.monotonic() - started
    if not latest or latest.get("event_id") != "latest":
        raise AssertionError(latest)
    if tail_elapsed >= 1.0:
        raise AssertionError(f"journal tail read scanned too much data: {tail_elapsed:.3f}s")
    print("PASS: runtime status remains responsive during scheduler reconciliation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
