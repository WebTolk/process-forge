"""Real shared/exclusive native lease identity, independently of Core stores."""

from __future__ import annotations

import contextvars
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pf_native_control as native
import pytest


def _control(root: Path) -> native.NativeControl:
    guard, epoch = root / "guard", root / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"identity-fixture")
    return native.NativeControl(guard, epoch, "identity-fixture")


def test_shared_lease_cannot_supply_exclusive_identity(tmp_path: Path) -> None:
    control = _control(tmp_path)
    with control.operation():
        assert native._native_life_held(control)
        with pytest.raises(native.NativeControlError):
            native._exclusive_lease_identity(control)


_EXCLUSIVE_PROBE = r"""
import sys,time
from pathlib import Path
import pf_native_control as native
root=Path(sys.argv[1])
gate=native.NativeControl(root/"guard",root/"epoch","identity-fixture")
try:
    with gate.exclusive(deadline=time.monotonic()+0.2):
        print("acquired")
except native.NativeControlError:
    print("refused")
"""


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Real fork unlock only"
)
@pytest.mark.parametrize("exception", [False, True])
@pytest.mark.parametrize("exclusive", [False, True])
def test_fork_unwind_cannot_unlock_original_process_lease(
    tmp_path: Path, exception: bool, exclusive: bool
) -> None:
    import select
    import signal
    import subprocess

    control = _control(tmp_path)
    original_pid = os.getpid()
    read_fd, write_fd = os.pipe()
    child = None
    descriptor = None

    def probe() -> str:
        result = subprocess.run(
            [sys.executable, "-B", "-c", _EXCLUSIVE_PROBE, str(tmp_path)],
            check=True,
            capture_output=True,
            timeout=5,
        )
        assert not result.stderr
        return result.stdout.decode().strip()

    def scope() -> int:
        nonlocal child, descriptor
        try:
            with control.exclusive() if exclusive else control.operation():
                child = getattr(os, "fork")()
                if child == 0:
                    os.close(read_fd)
                    if exception:
                        raise RuntimeError("child fixture unwind")
                    return 0
                os.close(write_fd)
                descriptor = getattr(os, "pidfd_open")(child)
                assert select.select([read_fd], [], [], 5)[0], "child unwind timed out"
                assert os.read(read_fd, 1) == b"U"
                assert native._native_life_held(control)
                if exclusive:
                    assert native._exclusive_lease_identity(control)
                assert probe() == "refused"
                return child
        except RuntimeError:
            if os.getpid() == original_pid:
                raise
            return 0

    try:
        result = scope()
        if result == 0:
            # The child has already returned/raised THROUGH the inherited with
            # and executed NativeControl's finally before reporting completion.
            try:
                os.write(write_fd, b"U")
            finally:
                os._exit(0)
        assert probe() == "acquired"
    finally:
        if os.getpid() == original_pid:
            if child:
                if descriptor is None:
                    descriptor = getattr(os, "pidfd_open")(child)
                if not select.select([descriptor], [], [], 1)[0]:
                    getattr(signal, "pidfd_send_signal")(
                        descriptor, getattr(signal, "SIGKILL")
                    )
                os.waitpid(child, 0)
            if descriptor is not None:
                os.close(descriptor)
            os.close(read_fd)
            if child is None:
                os.close(write_fd)


def test_exclusive_identity_comes_from_live_locked_object(tmp_path: Path) -> None:
    control = _control(tmp_path)
    with control.exclusive():
        identity = native._exclusive_lease_identity(control)
        info = control.guard.stat()
        assert identity["guard_identity"] == [info.st_dev, info.st_ino]
        assert identity["accepted_epoch"] == "identity-fixture"
        borrowed = contextvars.copy_context()
    with pytest.raises(native.NativeControlError):
        borrowed.run(native._exclusive_lease_identity, control)
    # A new object holding the same actual gate can recover the exact identity.
    successor = native.NativeControl(
        control.guard, control.epoch_path, "identity-fixture"
    )
    with successor.exclusive():
        assert native._exclusive_lease_identity(successor) == identity


@pytest.mark.parametrize("inner_exclusive", [False, True])
def test_retained_outer_identity_survives_private_nested_gate(
    tmp_path: Path, inner_exclusive: bool
) -> None:
    outer = _control(tmp_path)
    inner_root = tmp_path / "installation"
    inner_root.mkdir()
    inner = _control(inner_root)
    with outer.exclusive():
        expected = native._exclusive_lease_identity(outer)
        # Ordinary callers still cannot upgrade/replace a live current lease.
        with pytest.raises(native.NativeControlError), inner.operation():
            pass
        # The existing private cold/publication path retains its outer OS lock
        # while switching the current operation to a different installation.
        token = native._CONTROL_LEASE.set(None)
        try:
            assert not native._native_life_held(outer)
            assert native._exclusive_lease_identity(outer) == expected
            scope = inner.exclusive() if inner_exclusive else inner.operation()
            with scope:
                assert native._native_life_held(inner)
                assert native._exclusive_lease_identity(outer) == expected
                if inner_exclusive:
                    assert native._exclusive_lease_identity(inner) != expected
                else:
                    with pytest.raises(native.NativeControlError):
                        native._exclusive_lease_identity(inner)
            assert native._exclusive_lease_identity(outer) == expected
        finally:
            native._CONTROL_LEASE.reset(token)
        assert native._native_life_held(outer)
    with pytest.raises(native.NativeControlError):
        native._exclusive_lease_identity(outer)


def test_expired_context_cannot_borrow_successor_lease_after_exception(
    tmp_path: Path,
) -> None:
    control = _control(tmp_path)
    with pytest.raises(RuntimeError, match="fixture unwind"), control.exclusive():
        borrowed = contextvars.copy_context()
        raise RuntimeError("fixture unwind")
    with control.exclusive():
        assert native._exclusive_lease_identity(control)
        with pytest.raises(native.NativeControlError):
            borrowed.run(native._exclusive_lease_identity, control)


def test_copied_context_in_other_thread_cannot_borrow_live_exclusive_lease(
    tmp_path: Path,
) -> None:
    control = _control(tmp_path)
    with control.exclusive():
        borrowed = contextvars.copy_context()

        def refuse() -> None:
            with pytest.raises(native.NativeControlError):
                native._exclusive_lease_identity(control)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(borrowed.run, refuse).result(timeout=5)
        assert native._exclusive_lease_identity(control)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Real fork only")
def test_fork_cannot_borrow_parent_exclusive_lease(tmp_path: Path) -> None:
    import select
    import signal

    control = _control(tmp_path)
    with control.exclusive():
        read_fd, write_fd = os.pipe()
        child = getattr(os, "fork")()
        if child == 0:
            os.close(read_fd)
            try:
                native._exclusive_lease_identity(control)
            except native.NativeControlError:
                os.write(write_fd, b"R")
            else:
                os.write(write_fd, b"A")
            finally:
                os._exit(0)
        os.close(write_fd)
        descriptor = getattr(os, "pidfd_open")(child)
        try:
            assert select.select([read_fd], [], [], 5)[0], "fork fixture timed out"
            assert os.read(read_fd, 1) == b"R"
            assert native._exclusive_lease_identity(control)
        finally:
            # Retained pidfd identifies only this fixture's own unreaped child.
            if not select.select([descriptor], [], [], 1)[0]:
                getattr(signal, "pidfd_send_signal")(
                    descriptor, getattr(signal, "SIGKILL")
                )
            os.waitpid(child, 0)
            os.close(descriptor)
            os.close(read_fd)


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="POSIX replacement case"
)
def test_replaced_guard_is_not_the_locked_object(tmp_path: Path) -> None:
    control = _control(tmp_path)
    original = control.guard.stat()
    with control.exclusive():
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"0")
        os.replace(replacement, control.guard)
        assert control.guard.stat().st_ino != original.st_ino
        with pytest.raises(native.NativeControlError):
            native._exclusive_lease_identity(control)
