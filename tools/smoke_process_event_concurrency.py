#!/usr/bin/env python3
"""Actual concurrent journal writers, duplicate ids, durability and hook boundaries."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core  # noqa: E402


def worker(project: Path, index: int) -> None:
    (project / f"ready-{index}").touch()
    deadline = time.monotonic() + 20
    while not (project / "start").exists():
        assert time.monotonic() < deadline, "start barrier timed out"
        time.sleep(0.005)
    # Slow the first read to expose check-then-append races deterministically.
    # With a real journal lock, only its owner can reach this read at a time.
    loads = core.json.loads
    first = True

    def slow_first(*args, **kwargs):
        nonlocal first
        if first:
            first = False
            time.sleep(0.25)
        return loads(*args, **kwargs)

    core.json.loads = slow_first
    core.append_process_event(project, {"event_id": "evt_shared", "data": {"text": "same"}}, dispatch=False)
    for item in range(8):
        core.append_process_event(project, {"event_id": f"evt_worker{index}item{item}",
                                           "data": {"text": "Журнал 🌍\n" * 2048}}, dispatch=False)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-event-journal-") as temporary:
        project = Path(temporary)
        journal, _ = core.event_runtime_paths(project)
        journal.parent.mkdir(parents=True)
        prefix = b"".join((json.dumps({"event_id": f"evt_seed{i}", "data": {"padding": "x" * 512}}) + "\n").encode()
                          for i in range(512))
        journal.write_bytes(prefix)
        workers = [subprocess.Popen([sys.executable, "-B", __file__, "--worker", str(project), str(i)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                   for i in range(4)]
        try:
            deadline = time.monotonic() + 25
            while not all((project / f"ready-{i}").exists() for i in range(4)):
                assert time.monotonic() < deadline, "workers did not reach the barrier"
                assert all(p.poll() is None for p in workers), "worker failed before barrier"
                time.sleep(0.01)
            (project / "start").touch()
            for process in workers:
                out, err = process.communicate(timeout=60)
                assert process.returncode == 0, (out, err)
        finally:
            for process in workers:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        raw = journal.read_bytes()
        assert raw.startswith(prefix), "preexisting bytes changed"
        rows = [json.loads(line) for line in raw.splitlines()]
        ids = [row["event_id"] for row in rows]
        assert ids.count("evt_shared") == 1, f"duplicate-id race: {ids.count('evt_shared')} copies"
        assert len(ids) == len(set(ids)) == 545, (len(ids), len(set(ids)))
        expected = {f"evt_worker{i}item{j}" for i in range(4) for j in range(8)}
        assert expected.issubset(ids), "a concurrent event was lost"
        assert all(row["data"]["text"] == "Журнал 🌍\n" * 2048 for row in rows if row["event_id"] in expected)

        held = False
        dispatched = []
        synced = []
        actual_fsync = os.fsync

        @contextmanager
        def observed_lock(path, **kwargs):
            nonlocal held
            assert path == journal and not held
            held = True
            try:
                yield
            finally:
                held = False

        def dispatch(_project, event, **kwargs):
            assert not held, "hook dispatch kept the journal lock"
            dispatched.append(event["event_id"])

        def fsync(fd):
            assert held, "durability must precede lock release"
            synced.append(fd)
            actual_fsync(fd)

        with patch.object(core, "registry_file_lock", observed_lock), patch.object(core, "dispatch_hooks", dispatch), patch.object(core.os, "fsync", fsync):
            core.append_process_event(project, {"event_id": "evt_boundary"})
        assert dispatched == ["evt_boundary"] and synced
        before = journal.read_bytes()

        @contextmanager
        def busy(*_args, **_kwargs):
            raise SystemExit("fixture lock timeout")
            yield

        with patch.object(core, "registry_file_lock", busy), patch.object(core, "dispatch_hooks", dispatch):
            try:
                core.append_process_event(project, {"event_id": "evt_blocked"})
            except RuntimeError as exc:
                assert "journal" in str(exc).lower()
            else:
                raise AssertionError("lock failure was silently acknowledged")
        assert journal.read_bytes() == before and dispatched == ["evt_boundary"]
    print("PASS: concurrent unique/duplicate Unicode events, prefix preservation, durable append, hook boundary and explicit lock failure")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
