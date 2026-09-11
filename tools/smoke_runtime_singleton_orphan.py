#!/usr/bin/env python3
"""Regression coverage for Runtime singleton orphan and startup races."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pf_runtime import service  # noqa: E402
import processforge as core  # noqa: E402


def child_process() -> subprocess.Popen[str]:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], text=True)


def expect_rejected(workplace: Path, instance: str) -> None:
    try:
        service.acquire_singleton(workplace, core, instance)
    except SystemExit:
        return
    raise AssertionError("live orphaned owner was acquired")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runtime-singleton-") as raw:
        workplace = Path(raw) / "workplace"
        runtime = service.runtime_root(workplace)
        runtime.mkdir(parents=True)

        owner = child_process()
        try:
            state = {"instance_id": "live-owner", "pid": owner.pid, "status": "ready", "endpoint": ""}
            service.service_path(workplace).write_text(json.dumps(state), encoding="utf-8")
            service.lock_path(workplace).write_text(json.dumps({"instance_id": "other-owner", "pid": owner.pid}), encoding="utf-8")
            expect_rejected(workplace, "new-owner")
            if json.loads(service.lock_path(workplace).read_text(encoding="utf-8")).get("instance_id") != "other-owner":
                raise AssertionError("mismatched live lock was replaced")

            service.lock_path(workplace).unlink()
            expect_rejected(workplace, "new-owner")
            if service.lock_path(workplace).exists():
                raise AssertionError("missing-lock orphan created a replacement lock")
        finally:
            owner.terminate()
            owner.wait(timeout=5)

        stale = {"instance_id": "dead-owner", "pid": 2147483647, "created_at": "old"}
        service.lock_path(workplace).write_text(json.dumps(stale), encoding="utf-8")
        acquired = service.acquire_singleton(workplace, core, "recovered-owner")
        if acquired != service.os.getpid():
            raise AssertionError(acquired)
        if json.loads(service.lock_path(workplace).read_text(encoding="utf-8")).get("instance_id") != "recovered-owner":
            raise AssertionError("dead stale lock was not recovered")
        service.release_singleton(workplace, "recovered-owner", core)

        winners: list[str] = []
        failures: list[BaseException] = []
        barrier = threading.Barrier(2)

        def contender(instance: str) -> None:
            try:
                barrier.wait(timeout=5)
                service.acquire_singleton(workplace, core, instance)
                winners.append(instance)
            except BaseException as exc:  # noqa: BLE001 - capture expected loser.
                failures.append(exc)

        first = threading.Thread(target=contender, args=("race-a",), daemon=True)
        second = threading.Thread(target=contender, args=("race-b",), daemon=True)
        first.start()
        second.start()
        first.join(timeout=10)
        second.join(timeout=10)
        if len(winners) != 1 or not any(isinstance(item, SystemExit) for item in failures):
            raise AssertionError(f"concurrent singleton result is unsafe: winners={winners} failures={failures}")
        lock_owner = json.loads(service.lock_path(workplace).read_text(encoding="utf-8")).get("instance_id")
        if lock_owner != winners[0]:
            raise AssertionError(f"winner lock was replaced: {lock_owner} vs {winners}")
        service.release_singleton(workplace, winners[0], core)
    print("PASS: Runtime singleton protects live orphans and concurrent startup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
