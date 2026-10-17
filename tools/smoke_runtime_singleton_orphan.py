#!/usr/bin/env python3
"""Regression coverage for Runtime singleton orphan and startup races."""

from __future__ import annotations

import json
import contextlib
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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


@contextlib.contextmanager
def held_windows_reader(path: Path):
    """An actual destination reader that does not grant delete sharing."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handle = create(str(path), 0x80000000, 0x3, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    guard = threading.Lock()

    def release() -> None:
        nonlocal handle
        with guard:
            if handle is not None:
                if not close(handle):
                    raise ctypes.WinError(ctypes.get_last_error())
                handle = None

    try:
        yield release
    finally:
        release()


def publication_checks(root: Path) -> list[dict]:
    """Bounded fault controls plus real Win32 sharing; no Runtime is started."""
    from processforge_core import runtime_service_state as state_core

    writer = state_core.RuntimeServiceStateWriter()
    real_replace = os.replace
    payload = {"status": "starting", "text": "Проверка", "unknown": {"z": 2, "a": 1}}
    expected = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").replace("\n", os.linesep).encode("utf-8")
    old = b'{"old": true}\n'
    results: list[dict] = []

    def target_for(name: str) -> Path:
        directory = root / name
        directory.mkdir()
        path = directory / "service.json"
        path.write_bytes(old)
        return path

    def windows_error(code: int) -> OSError:
        error = OSError("controlled replacement failure")
        error.winerror = code
        return error

    def expect_error(path, error, publish) -> None:
        try:
            publish()
        except BaseException as actual:
            assert actual is error, (type(actual), type(error))
        else:
            raise AssertionError("publication failure was hidden")
        assert path.read_bytes() == old

    path = target_for("exact-bytes")
    service.write_json_atomic(path, payload)
    assert path.read_bytes() == expected
    assert not list(path.parent.glob(".*.tmp"))
    results.append({"case": "adapter_exact_bytes", "status": "pass"})

    for code in (5, 32, 33):
        path = target_for(f"retry-{code}")
        attempts: list[Path] = []
        failure = windows_error(code)

        def recover(tmp, destination):
            attempts.append(tmp)
            assert tmp.read_bytes() == expected and destination.read_bytes() == old
            if len(attempts) < 3:
                raise failure
            real_replace(tmp, destination)

        with patch.object(state_core, "sys", SimpleNamespace(platform="win32")), \
                patch.object(state_core.os, "replace", side_effect=recover), \
                patch.object(state_core.time, "monotonic", return_value=0.0), \
                patch.object(state_core.time, "sleep") as sleeper, \
                patch.object(state_core.json, "dumps", wraps=json.dumps) as serialize, \
                patch.object(Path, "write_text", autospec=True, side_effect=Path.write_text) as write, \
                patch.object(Path, "mkdir", autospec=True, side_effect=Path.mkdir) as mkdir:
            writer.write(path, payload)
        assert len(attempts) == 3 and len(set(attempts)) == 1
        assert write.call_count == mkdir.call_count == serialize.call_count == 1
        assert sleeper.call_count == 2 and path.read_bytes() == expected
        assert not attempts[0].exists()
        assert attempts[0].name.startswith(f".service.json.{os.getpid()}.")
        results.append({"case": f"winerror_{code}_recovery", "status": "pass", "attempts": 3})

    for name, platform, error in (
        ("unexpected-winerror", "win32", windows_error(87)),
        ("errno-only", "win32", PermissionError("no winerror")),
        ("non-windows", "linux", windows_error(5)),
        ("non-os-error", "win32", RuntimeError("unexpected failure")),
    ):
        path = target_for(name)
        with patch.object(state_core, "sys", SimpleNamespace(platform=platform)), \
                patch.object(state_core.os, "replace", side_effect=error) as replace, \
                patch.object(state_core.time, "sleep") as sleeper:
            expect_error(path, error, lambda: writer.write(path, payload))
        assert replace.call_count == 1 and sleeper.call_count == 0
        assert not list(path.parent.glob(".*.tmp"))
        results.append({"case": name, "status": "pass", "attempts": 1})

    for name, ticks, limit in (
        ("frozen-clock", None, 6),
        ("deadline-before-sleep", [0.0, 0.06], 1),
        ("oversleep", [0.0, 0.0, 0.06], 1),
        ("remaining-sleep", [0.0, 0.049, 0.06], 1),
    ):
        path = target_for(name)
        original = windows_error(5)
        failures = [original] + [windows_error(32) for _ in range(5)]
        clock = {"return_value": 0.0} if ticks is None else {"side_effect": ticks}
        with patch.object(state_core, "sys", SimpleNamespace(platform="win32")), \
                patch.object(state_core.os, "replace", side_effect=failures) as replace, \
                patch.object(state_core.time, "monotonic", **clock), \
                patch.object(state_core.time, "sleep") as sleeper:
            expect_error(path, original, lambda: writer.write(path, payload))
        assert replace.call_count == limit
        sleeps = [call.args[0] for call in sleeper.call_args_list]
        assert sum(sleeps) <= 0.05 and all(0 < delay <= 0.01 for delay in sleeps)
        if name == "remaining-sleep":
            assert len(sleeps) == 1 and sleeps[0] < 0.0011
        assert not list(path.parent.glob(".*.tmp"))
        results.append({"case": name, "status": "pass", "attempts": limit, "requested_sleep_seconds": sum(sleeps)})

    path = target_for("unknown-after-conflict")
    fatal = windows_error(87)
    with patch.object(state_core, "sys", SimpleNamespace(platform="win32")), \
            patch.object(state_core.os, "replace", side_effect=[windows_error(5), fatal]) as replace, \
            patch.object(state_core.time, "monotonic", return_value=0.0), \
            patch.object(state_core.time, "sleep") as sleeper:
        expect_error(path, fatal, lambda: writer.write(path, payload))
    assert replace.call_count == 2 and sleeper.call_count == 1
    results.append({"case": "unknown_after_conflict", "status": "pass"})

    path = target_for("late-success")
    attempts = []
    ticks = [0.0]

    def late_success(tmp, destination):
        attempts.append(tmp)
        if len(attempts) == 1:
            raise windows_error(5)
        real_replace(tmp, destination)
        ticks[0] = 10.0  # The successful OS call outlasted the window.

    with patch.object(state_core, "sys", SimpleNamespace(platform="win32")), \
            patch.object(state_core.os, "replace", side_effect=late_success), \
            patch.object(state_core.time, "monotonic", side_effect=lambda: ticks[0]), \
            patch.object(state_core.time, "sleep"):
        writer.write(path, payload)
    assert path.read_bytes() == expected and len(attempts) == 2
    results.append({"case": "success_after_deadline", "status": "pass"})

    for operation in ("mkdir", "serialization", "write"):
        path = target_for("preparation-" + operation)
        failure = windows_error(5)
        if operation == "mkdir":
            fault = patch.object(Path, "mkdir", side_effect=failure)
        elif operation == "serialization":
            fault = patch.object(state_core.json, "dumps", side_effect=failure)
        else:
            fault = patch.object(Path, "write_text", side_effect=failure)
        with fault as prepare, patch.object(state_core.os, "replace") as replace, \
                patch.object(state_core.time, "sleep") as sleeper:
            expect_error(path, failure, lambda: writer.write(path, payload))
        assert prepare.call_count == 1 and replace.call_count == sleeper.call_count == 0
        assert not list(path.parent.glob(".*.tmp"))
        results.append({"case": "preparation_" + operation, "status": "pass"})

    # A partial disk write must not accumulate staging, and must not remove
    # another invocation's file in the same directory.
    path = target_for("partial-write")
    other = path.parent / ".service.json.other-writer.tmp"
    other.write_bytes(b"other writer")
    failure = OSError("controlled partial write")
    real_write = Path.write_text

    def partial_write(temporary, text, *args, **kwargs):
        real_write(temporary, text[:5], *args, **kwargs)
        raise failure

    with patch.object(Path, "write_text", autospec=True, side_effect=partial_write):
        expect_error(path, failure, lambda: writer.write(path, payload))
    assert list(path.parent.glob(".*.tmp")) == [other] and other.read_bytes() == b"other writer"
    results.append({"case": "partial_write_cleans_only_own_staging", "status": "pass"})

    path = target_for("cleanup-denied")
    failure = RuntimeError("original publication failure")
    with patch.object(writer, "_replace", side_effect=failure), \
            patch.object(Path, "unlink", side_effect=PermissionError("cleanup denied")):
        expect_error(path, failure, lambda: writer.write(path, payload))
    assert len(list(path.parent.glob(".*.tmp"))) == 1
    results.append({"case": "cleanup_denial_preserves_original_error", "status": "pass"})

    # Host JSON and text use this owner; the standalone integration installer
    # retains its backup and cleans only its unique failed staging file.
    from pf_runtime import host, codex_integration
    for name, publish in (
        ("host-json", lambda p: host.write_json(p, payload)),
        ("runtime-text", lambda p: writer.write_text(p, "projection\n")),
        ("integration", lambda p: codex_integration.write_atomic(p, payload)),
    ):
        path = target_for(name)
        failure = OSError("controlled adapter failure")
        with patch.object(state_core.os, "replace", side_effect=failure):
            expect_error(path, failure, lambda: publish(path))
        assert not list(path.parent.glob(".*.tmp"))
        if name == "integration":
            backups = list(path.parent.glob("*.pf-backup-*"))
            assert len(backups) == 1 and backups[0].read_bytes() == old
        results.append({"case": name + "_failure_cleanup", "status": "pass"})

    # Existing serve failure/finally path, using only disposable state. No
    # endpoint or scheduler is started because the first save always fails.
    path = target_for("serve-failure")
    runtime = service.RuntimeProcess.__new__(service.RuntimeProcess)
    runtime.workplace_root = path.parent
    runtime.core = SimpleNamespace(now_utc=lambda: "fixed", process_pid_running=lambda pid: pid == os.getpid())
    runtime.instance_id = "failed-publication-owner"
    runtime.token = "scratch-token"
    runtime.state_lock = threading.RLock()
    failure = windows_error(5)
    with patch.object(state_core, "sys", SimpleNamespace(platform="win32")), \
            patch.object(state_core.os, "replace", side_effect=failure) as replace, \
            patch.object(state_core.time, "monotonic", return_value=0.0), \
            patch.object(state_core.time, "sleep"), \
            patch.object(service, "ThreadingHTTPServer") as server:
        try:
            runtime.serve(0)
        except OSError as actual:
            assert actual is failure
        else:
            raise AssertionError("failed startup was accepted")
    assert replace.call_count == 12 and server.call_count == 0
    assert not service.lock_path(runtime.workplace_root).exists()
    assert runtime.state["status"] == runtime.state["health"] == "failed"
    assert not list(service.runtime_root(runtime.workplace_root).glob(".*.tmp"))
    results.append({"case": "serve_failure_releases_own_singleton", "status": "pass", "live_runtime_started": False})

    if sys.platform == "win32":
        for index in range(5):
            path = target_for(f"native-release-{index}")
            conflict = threading.Event()
            attempts = []
            errors = []
            released_at = []
            first_failure_at = []
            with held_windows_reader(path) as release:
                def release_reader():
                    if conflict.wait(timeout=2):
                        time.sleep(0.01)
                        release()
                        released_at.append(time.monotonic())

                releaser = threading.Thread(target=release_reader, daemon=True)
                releaser.start()

                def native_replace(tmp, destination):
                    attempts.append(tmp)
                    assert tmp.read_bytes() == expected and destination.read_bytes() == old
                    try:
                        real_replace(tmp, destination)
                    except OSError as error:
                        if not first_failure_at:
                            first_failure_at.append(time.monotonic())
                        errors.append(error)
                        conflict.set()
                        raise

                started = time.monotonic()
                try:
                    with patch.object(state_core.os, "replace", side_effect=native_replace):
                        writer.write(path, payload)
                finally:
                    conflict.set()
                    releaser.join(timeout=3)
                elapsed = time.monotonic() - started
            assert not releaser.is_alive() and errors and released_at
            # Preparation precedes the retry window. Observe the real
            # conflict/release order; OS calls and scheduling are not a
            # hard wall-time guarantee of the writer's private deadline.
            assert first_failure_at and first_failure_at[0] <= released_at[0]
            assert len(set(attempts)) == 1 and path.read_bytes() == expected
            assert not attempts[0].exists()
            results.append({"case": f"native_reader_released_{index}", "status": "pass", "attempts": len(attempts),
                            "winerrors": [error.winerror for error in errors], "elapsed_seconds": elapsed,
                            "release_seconds": released_at[0] - first_failure_at[0],
                            "release_clock_origin": "first_failed_replace"})

        path = target_for("native-held")
        attempts = []
        errors = []

        def held_replace(tmp, destination):
            attempts.append(tmp)
            try:
                real_replace(tmp, destination)
            except OSError as error:
                errors.append(error)
                raise

        with held_windows_reader(path), patch.object(state_core.os, "replace", side_effect=held_replace):
            started = time.monotonic()
            try:
                writer.write(path, payload)
            except OSError as actual:
                assert errors and actual is errors[0]
            else:
                raise AssertionError("permanently held destination was replaced")
            elapsed = time.monotonic() - started
        assert 1 < len(attempts) <= 6 and len(set(attempts)) == 1
        assert path.read_bytes() == old and not attempts[0].exists()
        writer.write(path, payload)  # Explicit retry after releasing the reader.
        assert path.read_bytes() == expected
        results.append({"case": "native_reader_still_held", "status": "pass", "attempts": len(attempts),
                        "elapsed_seconds": elapsed, "original_error_preserved": True})

        # A file cannot replace an existing directory. The resulting native
        # access denial is permanent; it must remain a failure after the budget.
        path = root / "native-permanent" / "service.json"
        path.mkdir(parents=True)
        attempts = []
        errors = []
        with patch.object(state_core.os, "replace", side_effect=held_replace):
            started = time.monotonic()
            try:
                writer.write(path, payload)
            except OSError as actual:
                assert errors and actual is errors[0] and actual.winerror == 5
            else:
                raise AssertionError("permanent native denial was hidden")
            elapsed = time.monotonic() - started
        assert 1 < len(attempts) <= 6 and len(set(attempts)) == 1
        assert path.is_dir() and not list(path.iterdir())
        assert not attempts[0].exists()
        results.append({"case": "native_permanent_denial", "status": "pass", "attempts": len(attempts),
                        "elapsed_seconds": elapsed, "original_error_preserved": True})

        path = target_for("native-unexpected")
        with patch.object(state_core.os, "replace", side_effect=real_replace) as replace, \
                patch.object(state_core.time, "sleep") as sleeper:
            try:
                writer._replace(path.parent / "absent.tmp", path)
            except OSError as actual:
                assert actual.winerror == 2
            else:
                raise AssertionError("missing native source was accepted")
        assert replace.call_count == 1 and sleeper.call_count == 0
        assert path.read_bytes() == old
        results.append({"case": "native_unexpected_error", "status": "pass", "attempts": 1})
    return results


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runtime-singleton-") as raw:
        publication_results = publication_checks(Path(raw))
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
    print(json.dumps({"publication_checks": publication_results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
