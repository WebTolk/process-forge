"""Real shared/exclusive native lease identity, independently of Core stores."""

from __future__ import annotations

import contextvars
import os
import sys
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
