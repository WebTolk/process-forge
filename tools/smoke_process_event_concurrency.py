#!/usr/bin/env python3
"""Actual concurrent journal writers, duplicate ids, durability and hook boundaries."""
from __future__ import annotations

from contextlib import contextmanager
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
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


def current_byte_index_controls(project: Path) -> None:
    """Exercise actual byte changes, fallbacks and failure boundaries."""
    project.mkdir(parents=True)
    journal, _ = core.event_runtime_paths(project)
    journal.parent.mkdir(parents=True)
    seed = (json.dumps({"event_id": "evt_seed", "data": "Журнал"}, ensure_ascii=False) + "\n").encode()
    journal.write_bytes(seed)
    service = core.ProcessEventJournal()
    loads = core.json.loads
    calls = []

    id_value = core.event_id_value

    def observe_ids(event):
        calls.append(event)
        return id_value(event)

    with patch.object(core, "_process_event_journal", service), patch.object(core, "event_id_value", observe_ids), patch.object(core, "registry_file_lock", lambda *_a, **_k: nullcontext()):
        core.append_process_event(project, {"event_id": "evt_one"}, dispatch=False)
        assert len(calls) >= 3, "first append must read IDs from current history"
        calls.clear()
        core.append_process_event(project, {"event_id": "evt_two"}, dispatch=False)
        assert len(calls) == 2, "verified warm append should read only input and serialized new ID"
        calls.clear()
        before = journal.read_bytes()
        core.append_process_event(project, {"event_id": "evt_two"}, dispatch=False)
        assert len(calls) == 1 and journal.read_bytes() == before, "warm duplicate changed bytes"

        stamp = journal.stat()
        changed = before.replace(b"evt_seed", b"evt_edit")
        assert len(changed) == len(before)
        journal.write_bytes(changed)
        os.utime(journal, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        core.append_process_event(project, {"event_id": "evt_edit"}, dispatch=False)
        assert calls and journal.read_bytes() == changed, "same-size/mtime edit bypassed current-byte proof"
        calls.clear()
        with journal.open("ab") as handle:
            handle.write(b'{"event_id":"evt_external"}\n')
        before = journal.read_bytes()
        core.append_process_event(project, {"event_id": "evt_external"}, dispatch=False)
        assert calls and journal.read_bytes() == before, "another writer's append was missed"

        journal.write_bytes(b'{"event_id":"evt_short"}\n')
        core.append_process_event(project, {"event_id": "evt_short"}, dispatch=False)
        assert journal.read_bytes() == b'{"event_id":"evt_short"}\n'
        journal.unlink()
        core.append_process_event(project, {"event_id": "evt_fresh"}, dispatch=False)
        assert loads(journal.read_bytes())["event_id"] == "evt_fresh"

    # A zero budget keeps the original full scan; UUID fallback rows must not
    # become stable cached identities even with the ordinary memory budget.
    for budget, prefix in [(0, seed), (16 * 1024 * 1024, b'{}\n' + seed)]:
        journal.write_bytes(prefix)
        service = core.ProcessEventJournal(max_index_bytes=budget)
        calls.clear()
        with patch.object(core, "_process_event_journal", service), patch.object(core, "event_id_value", observe_ids), patch.object(core, "registry_file_lock", lambda *_a, **_k: nullcontext()):
            core.append_process_event(project, {"event_id": "evt_first"}, dispatch=False)
            calls.clear()
            core.append_process_event(project, {"event_id": "evt_next"}, dispatch=False)
            assert len(calls) >= 3, "required full-scan fallback was cached"

    # Cold duplicate must stop before a later non-JSONDecodeError; a new ID
    # still sees the same error and cannot acknowledge a write.
    journal.write_bytes(b'{"event_id":"evt_early"}\nfixture-decoder-failure\n')
    before = journal.read_bytes()

    def failed_decoder(line, *args, **kwargs):
        if line == "fixture-decoder-failure":
            raise ValueError("fixture non-JSONDecodeError")
        return loads(line, *args, **kwargs)

    with patch.object(core, "_process_event_journal", core.ProcessEventJournal()), patch.object(core.json, "loads", failed_decoder):
        core.append_process_event(project, {"event_id": "evt_early"}, dispatch=False)
        try:
            core.append_process_event(project, {"event_id": "evt_absent"}, dispatch=False)
        except ValueError as exc:
            assert str(exc) == "fixture non-JSONDecodeError"
        else:
            raise AssertionError("unrelated history decoder error disappeared")
    assert journal.read_bytes() == before

    # Optional ID-set/hash allocation failures must keep the mandatory scan,
    # append and fsync. Faults are module-local, leaving the real guard intact.
    module = sys.modules[core.ProcessEventJournal.__module__]

    def no_index(*_args, **_kwargs):
        raise MemoryError("fixture optional index")

    for target, value in [("set", no_index), ("hashlib", SimpleNamespace(sha256=no_index))]:
        journal.write_bytes(seed)
        service = core.ProcessEventJournal()
        with patch.object(core, "_process_event_journal", service), patch.object(module, target, value, create=True):
            core.append_process_event(project, {"event_id": "evt_allocation"}, dispatch=False)
        assert journal.read_bytes() == seed + b'{"event_id": "evt_allocation"}\n'

    # A supported interpreter policy change must invalidate old parse facts,
    # even when the journal bytes, size and mtime are unchanged.
    if hasattr(sys, "set_int_max_str_digits"):
        original_limit = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(4300)
            journal.write_bytes(b'{"event_id":"evt_integer","data":' + b"1" * 1000 + b'}\n')
            with patch.object(core, "_process_event_journal", core.ProcessEventJournal()):
                core.append_process_event(project, {"event_id": "evt_warm"}, dispatch=False)
                before = journal.read_bytes()
                sys.set_int_max_str_digits(640)
                try:
                    core.append_process_event(project, {"event_id": "evt_restricted"}, dispatch=False)
                except ValueError as exc:
                    assert "640" in str(exc)
                else:
                    raise AssertionError("current decoder policy was bypassed by cached IDs")
                assert journal.read_bytes() == before
        finally:
            sys.set_int_max_str_digits(original_limit)

    # Unknown configured callbacks may change behavior without changing their
    # identity. Both duplicate/new requests must retain their full-parse errors.
    for target in ("evt_custom_warm", "evt_custom_next"):
        reject = [False]

        def parse_constant(_value):
            if reject[0]:
                raise ValueError("fixture mutable decoder policy")
            return float("nan")

        journal.write_bytes(b'{"event_id":"evt_constant","data":NaN}\n')
        decoder = json.JSONDecoder(parse_constant=parse_constant)
        with patch.object(core, "_process_event_journal", core.ProcessEventJournal()), patch.object(json, "_default_decoder", decoder):
            core.append_process_event(project, {"event_id": "evt_custom_warm"}, dispatch=False)
            before = journal.read_bytes()
            reject[0] = True
            try:
                core.append_process_event(project, {"event_id": target}, dispatch=False)
            except ValueError as exc:
                assert str(exc) == "fixture mutable decoder policy"
            else:
                raise AssertionError("mutable custom parser behavior was cached")
            assert journal.read_bytes() == before

    # Error construction is part of parsing policy even for ignored malformed
    # rows. Unknown mutable aliases must never authorize a cached success.
    for target in ("evt_error_warm", "evt_error_next"):
        reject_error = [False]
        original_error = json.JSONDecodeError

        class ConfiguredError(original_error):
            def __init__(self, *args, **kwargs):
                if reject_error[0]:
                    raise ValueError("fixture mutable error constructor")
                super().__init__(*args, **kwargs)

        journal.write_bytes(b'{broken}\n')
        with patch.object(core, "_process_event_journal", core.ProcessEventJournal()), patch.object(json.decoder, "JSONDecodeError", ConfiguredError):
            core.append_process_event(project, {"event_id": "evt_error_warm"}, dispatch=False)
            before = journal.read_bytes()
            reject_error[0] = True
            try:
                core.append_process_event(project, {"event_id": target}, dispatch=False)
            except ValueError as exc:
                assert str(exc) == "fixture mutable error constructor"
            else:
                raise AssertionError("mutable error constructor was bypassed")
            assert journal.read_bytes() == before

    # Even a descriptor can return the canonical class-visible initializer
    # while changing actual construction. Suppressed malformed rows never
    # publish an index, so both requests retain the current constructor error.
    original_error = json.JSONDecodeError
    original_init = original_error.__init__
    for target in ("evt_descriptor_warm", "evt_descriptor_next"):
        reject_error = [False]

        class ConfiguredInitializer:
            def __get__(self, instance, owner):
                if instance is None:
                    return original_init
                bound = original_init.__get__(instance, owner)

                def initialize(*args, **kwargs):
                    if reject_error[0]:
                        raise ValueError("fixture mutable descriptor constructor")
                    return bound(*args, **kwargs)
                return initialize

        journal.write_bytes(b'{broken}\n')
        service = core.ProcessEventJournal()
        with patch.object(core, "_process_event_journal", service), patch.object(original_error, "__init__", ConfiguredInitializer()):
            core.append_process_event(project, {"event_id": "evt_descriptor_warm"}, dispatch=False)
            assert service._index is None, "malformed history was indexed"
            before = journal.read_bytes()
            reject_error[0] = True
            try:
                core.append_process_event(project, {"event_id": target}, dispatch=False)
            except ValueError as exc:
                assert str(exc) == "fixture mutable descriptor constructor"
            else:
                raise AssertionError("descriptor constructor was bypassed")
            assert journal.read_bytes() == before

    # Optional definitions must not inspect error metadata at module import.
    class MetadataInitializer:
        def __get__(self, instance, owner):
            if instance is None:
                raise RuntimeError("fixture error metadata unavailable")
            return original_init.__get__(instance, owner)

    class PreimportError(original_error):
        __init__ = MetadataInitializer()

    name = "_pf_journal_preimport_control"
    with patch.object(json, "JSONDecodeError", PreimportError), patch.object(json.decoder, "JSONDecodeError", PreimportError):
        try:
            spec = importlib.util.spec_from_file_location(name, module.__file__)
            imported = importlib.util.module_from_spec(spec)
            sys.modules[name] = imported
            spec.loader.exec_module(imported)
            journal.write_bytes(b'{broken}\n')
            service = imported.ProcessEventJournal()
            service.append(journal, {"event_id": "evt_preimport"}, writer_guard=core.registry_file_lock, event_id_value=core.event_id_value)
            assert service._index is None and b"evt_preimport" in journal.read_bytes()
        finally:
            sys.modules.pop(name, None)

    # No clean LF boundary: preserve the old merged-tail bytes and rescan.
    journal.write_bytes(b'{"event_id":"evt_tail"}')
    with patch.object(core, "_process_event_journal", core.ProcessEventJournal()):
        core.append_process_event(project, {"event_id": "evt_new"}, dispatch=False)
        core.append_process_event(project, {"event_id": "evt_tail"}, dispatch=False)
    assert journal.read_bytes().count(b"evt_tail") == 2

    # Preserve preparation errors outside the registry-error adapter.
    with patch.object(core, "event_id_value", side_effect=SystemExit("fixture preparation")):
        try:
            core.append_process_event(project, {"event_id": "evt_prepare"}, dispatch=False)
        except SystemExit as exc:
            assert str(exc) == "fixture preparation"
        else:
            raise AssertionError("preparation SystemExit was translated or hidden")

    # A failed fsync leaves possible durable bytes but no acknowledged success;
    # the next operation must recover from the actual file.
    journal.write_bytes(seed)
    with patch.object(core, "_process_event_journal", core.ProcessEventJournal()), patch.object(core, "registry_file_lock", lambda *_a, **_k: nullcontext()):
        core.append_process_event(project, {"event_id": "evt_warm"}, dispatch=False)
        with patch.object(core.os, "fsync", side_effect=OSError("fixture fsync")):
            try:
                core.append_process_event(project, {"event_id": "evt_uncertain"}, dispatch=False)
            except OSError:
                pass
            else:
                raise AssertionError("failed durability was acknowledged")
        before = journal.read_bytes()
        core.append_process_event(project, {"event_id": "evt_uncertain"}, dispatch=False)
        assert journal.read_bytes() == before, "uncertain durable append was duplicated"


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
        current_byte_index_controls(project / "cache-controls")
    print("PASS: concurrent journal writers, byte-proved bounded index, current mutations, fallback/errors, durability and hooks")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
