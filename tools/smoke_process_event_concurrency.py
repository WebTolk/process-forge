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

    for target, value in [("hashlib", SimpleNamespace(sha256=no_index))]:
        journal.write_bytes(seed)
        service = core.ProcessEventJournal()
        with patch.object(core, "_process_event_journal", service), patch.object(module, target, value, create=True):
            core.append_process_event(project, {"event_id": "evt_allocation"}, dispatch=False)
        assert journal.read_bytes() == seed + b'{"event_id": "evt_allocation"}\n'
    journal.write_bytes(seed)
    with patch.object(core, "_process_event_journal", core.ProcessEventJournal()), patch.object(core.ProcessEventJournal, "_allocate_metadata", side_effect=no_index):
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

    # A descriptor can change actual construction while keeping its visible
    # initializer. Both requests must still see the current error exactly once.
    original_error = json.JSONDecodeError
    original_init = original_error.__init__
    for target in ("evt_descriptor_warm", "evt_descriptor_next"):
        reject_error = [False]
        constructor_calls = []

        class ConfiguredInitializer:
            def __get__(self, instance, owner):
                if instance is None:
                    return original_init
                bound = original_init.__get__(instance, owner)

                def initialize(*args, **kwargs):
                    constructor_calls.append(True)
                    if reject_error[0]:
                        raise ValueError("fixture mutable descriptor constructor")
                    return bound(*args, **kwargs)
                return initialize

        journal.write_bytes(b'{broken}\n')
        service = core.ProcessEventJournal()
        with patch.object(core, "_process_event_journal", service), patch.object(original_error, "__init__", ConfiguredInitializer()):
            core.append_process_event(project, {"event_id": "evt_descriptor_warm"}, dispatch=False)
            before = journal.read_bytes()
            constructor_calls.clear()
            reject_error[0] = True
            try:
                core.append_process_event(project, {"event_id": target}, dispatch=False)
            except ValueError as exc:
                assert str(exc) == "fixture mutable descriptor constructor"
            else:
                raise AssertionError("descriptor constructor was bypassed")
            assert journal.read_bytes() == before
            assert len(constructor_calls) == 1, "current error constructor must run exactly once"

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
            assert b"evt_preimport" in journal.read_bytes()
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


def ordered_error_rows_controls(project: Path) -> None:
    """Observable first-match, error replay and read-only behavior."""
    from pf_runtime import host

    project.mkdir(parents=True)
    journal, _ = core.event_runtime_paths(project)
    journal.parent.mkdir(parents=True)
    original_error = json.JSONDecodeError
    prefix = b'{"event_id":"evt_early"}\n{broken}\n{"event_id":"evt_late"}\n{"event_id":"evt_early"}\n{also-broken}\n'
    for operation in ("append", "contains"):
        for target in ("evt_early", "evt_late", "evt_absent"):
            reject, calls = [False], []

            class CurrentError(original_error):
                def __init__(self, *args, **kwargs):
                    calls.append(True)
                    if reject[0]:
                        raise ValueError("current ordered row error")
                    super().__init__(*args, **kwargs)

            journal.write_bytes(prefix)
            service = core.ProcessEventJournal()
            with patch.object(json.decoder, "JSONDecodeError", CurrentError), patch.object(core, "_process_event_journal", service):
                assert not host.event_exists(project, "evt_warm_absent", core)
                reject[0] = True
                calls.clear()
                before = journal.read_bytes()
                try:
                    result = (core.append_process_event(project, {"event_id": target}, dispatch=False)
                              if operation == "append" else host.event_exists(project, target, core))
                except ValueError as exc:
                    assert target != "evt_early" and str(exc) == "current ordered row error"
                    assert len(calls) == 1
                else:
                    assert target == "evt_early" and result and not calls, "later error was observed before first duplicate"
                assert journal.read_bytes() == before

    # Host has always skipped blank lines before json.loads; append has not.
    calls = []

    class BlankError(original_error):
        def __init__(self, *args, **kwargs):
            calls.append(True)
            raise ValueError("blank append error")

    journal.write_bytes(b' \t\n{"event_id":"evt_blank_seed"}\n')
    service = core.ProcessEventJournal()
    with patch.object(json.decoder, "JSONDecodeError", BlankError), patch.object(core, "_process_event_journal", service):
        assert not host.event_exists(project, "evt_absent", core)
        assert host.event_exists(project, "evt_blank_seed", core) and not calls
        fake = SimpleNamespace(event_runtime_paths=lambda _root: (journal, None), event_id_value=core.event_id_value)
        assert host.event_exists(project, "evt_blank_seed", fake) and not calls
        before = journal.read_bytes()
        try:
            core.append_process_event(project, {"event_id": "evt_new"}, dispatch=False)
        except ValueError as exc:
            assert str(exc) == "blank append error" and len(calls) == 1
        else:
            raise AssertionError("append skipped its mandatory blank-row parse")
        assert journal.read_bytes() == before

    if hasattr(sys, "set_int_max_str_digits"):
        original_limit = sys.get_int_max_str_digits()
        try:
            for operation in ("append", "contains"):
                for suffix_big in (False, True):
                    sys.set_int_max_str_digits(4300)
                    enabled, calls = [False], []

                    class PolicyError(original_error):
                        def __init__(self, *args, **kwargs):
                            calls.append(True)
                            if enabled[0]:
                                sys.set_int_max_str_digits(640)
                            super().__init__(*args, **kwargs)

                    big = b"1" * 1000
                    tail = big if suffix_big else b"1"
                    journal.write_bytes(b'{"event_id":"evt_prefix_big","value":' + big
                                        + b'}\n{broken}\n{"event_id":"evt_tail","value":' + tail + b'}\n')
                    service = core.ProcessEventJournal()
                    with patch.object(json.decoder, "JSONDecodeError", PolicyError), patch.object(core, "_process_event_journal", service):
                        assert not host.event_exists(project, "evt_warm_absent", core)
                        enabled[0] = True
                        calls.clear()
                        before = journal.read_bytes()
                        try:
                            result = (core.append_process_event(project, {"event_id": "evt_tail"}, dispatch=False)
                                      if operation == "append" else host.event_exists(project, "evt_tail", core))
                        except ValueError as exc:
                            assert suffix_big and "640" in str(exc)
                        else:
                            assert not suffix_big and result, "already-consumed prefix was reparsed under changed policy"
                        assert len(calls) == 1 and journal.read_bytes() == before
        finally:
            sys.set_int_max_str_digits(original_limit)

    # Read-only lookup cannot gain a writer lock or mutate filesystem state.
    journal.write_bytes(prefix)
    before = journal.read_bytes()
    service = core.ProcessEventJournal()
    real_open = Path.open

    def read_only_open(path, mode="r", *args, **kwargs):
        assert not any(flag in mode for flag in "wax+"), mode
        return real_open(path, mode, *args, **kwargs)

    with patch.object(Path, "open", read_only_open), patch.object(Path, "mkdir", side_effect=AssertionError("read mkdir")), patch.object(core.os, "fsync", side_effect=AssertionError("read fsync")), patch.object(core, "registry_file_lock", side_effect=AssertionError("read lock")):
        assert not service.contains(journal, "evt_absent", event_id_value=core.event_id_value)
        assert service.contains(journal, "evt_late", event_id_value=core.event_id_value)
    assert journal.read_bytes() == before

    # A deeper caller has less parser recursion headroom. Re-read valid IDs
    # there rather than reusing facts established on a shallower stack.
    journal.write_bytes(b'{"event_id":"evt_depth"}\n')
    calls = []

    def observe_depth(event):
        calls.append(True)
        return core.event_id_value(event)

    service = core.ProcessEventJournal()
    assert not service.contains(journal, "evt_absent", event_id_value=observe_depth)
    calls.clear()

    def deeper():
        return service.contains(journal, "evt_absent", event_id_value=observe_depth)

    assert not deeper() and calls, "deeper caller skipped its current parse"
    with patch.object(core.ProcessEventJournal, "_parsing_depth", side_effect=MemoryError("optional frame metadata")):
        assert service.contains(journal, "evt_depth", event_id_value=core.event_id_value)


def optional_policy_and_serialization_controls(project: Path) -> None:
    """Optional metadata cannot change mandatory errors or durable bytes."""
    from pf_runtime import host

    project.mkdir(parents=True)
    journal, _ = core.event_runtime_paths(project)
    journal.parent.mkdir(parents=True)
    module = sys.modules[core.ProcessEventJournal.__module__]
    original_error = json.JSONDecodeError
    seed = b'{bad-history}\n{"event_id":"evt_seed"}\n'
    for warm in (False, True):
        for operation in ("append", "contains"):
            journal.write_bytes(seed)
            service = core.ProcessEventJournal()
            calls, comparisons = [], [0]

            class CurrentError(original_error):
                def __init__(self, *args, **kwargs):
                    calls.append(args[1])
                    super().__init__(*args, **kwargs)

            def failing_policy_zip(*args, **kwargs):
                if sys._getframe(1).f_code.co_name == "_same_policy":
                    comparisons[0] += 1
                    if comparisons[0] == (2 if warm else 1):
                        raise MemoryError("optional policy comparison allocation")
                return zip(*args, **kwargs)

            with patch.object(core, "_process_event_journal", service), patch.object(json.decoder, "JSONDecodeError", CurrentError):
                if warm:
                    assert not host.event_exists(project, "evt_warm_missing", core)
                    assert service._index is not None
                    calls.clear()
                with patch.object(module, "zip", failing_policy_zip, create=True):
                    if operation == "contains":
                        assert not host.event_exists(project, "evt_missing", core)
                        assert journal.read_bytes() == seed
                    else:
                        core.append_process_event(project, {"event_id": "evt_new"}, dispatch=False)
                        assert journal.read_bytes() == seed + b'{"event_id": "evt_new"}\n'
                assert calls == ["{bad-history}"], "a consumed bad row was repeated or omitted"
                assert comparisons[0] >= (2 if warm else 1)

    limit = sys.get_int_max_str_digits()
    try:
        for replace_encoder in (False, True):
            sys.set_int_max_str_digits(4300)
            journal.write_bytes(seed)
            service = core.ProcessEventJournal()
            calls = []

            class CurrentError(original_error):
                def __init__(self, *args, **kwargs):
                    calls.append(args[1])
                    if args[1] == "{bad-record}":
                        sys.set_int_max_str_digits(640)
                    super().__init__(*args, **kwargs)

            producer = patch.object(json.JSONEncoder, "encode", return_value="{bad-record}") if replace_encoder else patch.object(json, "dumps", return_value="{bad-record}")
            with patch.object(core, "_process_event_journal", service), patch.object(json.decoder, "JSONDecodeError", CurrentError), producer:
                core.append_process_event(project, {"event_id": "evt_new"}, dispatch=False)
            assert journal.read_bytes() == seed + b'{bad-record}\n'
            assert calls == ["{bad-history}"] and sys.get_int_max_str_digits() == 4300
            assert service._index is None
    finally:
        sys.set_int_max_str_digits(limit)

    # Public encoder separators may be str subclasses. Optional recognition
    # must not invoke their comparison callbacks before mandatory serialization.
    try:
        for attribute, separator in (("item_separator", ", "), ("key_separator", ": ")):
            for bad_history in (False, True):
                sys.set_int_max_str_digits(4300)
                seed = b'{bad-history}\n' if bad_history else b''
                journal.write_bytes(seed)
                service = core.ProcessEventJournal()
                event = {"event_id": "evt_separator", "number": 10 ** 999}
                expected = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode()
                compared = []

                class CurrentSeparator(str):
                    def __ne__(self, other):
                        compared.append(True)
                        sys.set_int_max_str_digits(640)
                        return str.__ne__(self, other)

                with patch.object(core, "_process_event_journal", service), patch.object(json.JSONEncoder, attribute, CurrentSeparator(separator)):
                    core.append_process_event(project, event, dispatch=False)
                assert journal.read_bytes() == seed + expected
                assert not compared and sys.get_int_max_str_digits() == 4300
    finally:
        sys.set_int_max_str_digits(limit)


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
        ordered_error_rows_controls(project / "ordered-error-controls")
        optional_policy_and_serialization_controls(project / "optional-boundary-controls")
    print("PASS: concurrent journal writers, byte-proved bounded index, current mutations, fallback/errors, durability and hooks")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
