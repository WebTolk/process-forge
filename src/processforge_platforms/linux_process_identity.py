"""Linux private lock owners in the coordinate system of their shared procfs."""

from __future__ import annotations

import os
import re
import select
from pathlib import Path
from typing import Any


def _view() -> tuple[int, str, str, str]:
    raw = Path("/proc/self/stat").read_text(encoding="ascii")
    pid = int(raw.split(" ", 1)[0])
    ticks = raw[raw.rindex(")") + 2 :].split()[19]
    status = Path("/proc/self/status").read_text(encoding="ascii")
    coordinates = next(
        line for line in status.splitlines() if line.startswith("NSpid:")
    ).split()[1:]
    if (
        int(coordinates[0]) != pid
        or int(coordinates[-1]) != os.getpid()
        or not ticks.isdecimal()
    ):
        raise OSError("linux_procfs_identity_unavailable")
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9-]{36}", boot):
        raise OSError("linux_boot_identity_unavailable")
    return pid, str(Path("/proc").stat().st_dev), boot, ticks


def lock_owner_identity() -> dict[str, Any]:
    """Use a host-visible PID for namespace workers; preserve unsupported legacy mode."""
    try:
        pid, view, boot, ticks = _view()
        descriptor = getattr(os, "pidfd_open")(os.getpid())
        os.close(descriptor)
        return {
            "pid": pid,
            "linux_identity": {
                "version": 1,
                "pid": pid,
                "procfs_device": view,
                "boot_id": boot,
                "start_ticks": ticks,
            },
        }
    except (OSError, ValueError, IndexError, StopIteration, AttributeError) as error:
        if "PF_NATIVE_NAMESPACE" in os.environ:
            raise OSError("linux_lock_identity_unavailable") from error
        return {}  # File-only hosts without this capability keep their legacy format.


def lock_owner_alive(owner: dict[str, Any]) -> bool | None:
    """Require the same procfs view and exact birth; unreadability stays unknown."""
    descriptor: int | None = None
    try:
        value = owner["linux_identity"]
        if (
            not isinstance(value, dict)
            or set(value)
            != {"version", "pid", "procfs_device", "boot_id", "start_ticks"}
            or type(value["version"]) is not int
            or value["version"] != 1
            or type(value["pid"]) is not int
            or not 1 <= value["pid"] <= 0x7FFFFFFF
            or owner["pid"] != value["pid"]
            or not isinstance(value["start_ticks"], str)
            or not value["start_ticks"].isdecimal()
            or not isinstance(value["boot_id"], str)
            or not re.fullmatch(r"[a-f0-9-]{36}", value["boot_id"])
        ):
            return None
        own_pid, view, boot, _ = _view()
        if boot != value["boot_id"]:
            return False
        if view != value["procfs_device"]:
            return None
        if own_pid == os.getpid():
            try:
                descriptor = getattr(os, "pidfd_open")(value["pid"])
            except ProcessLookupError:
                return False
            if select.select([descriptor], [], [], 0)[0]:
                return False
        try:
            raw = Path(f"/proc/{value['pid']}/stat").read_text(encoding="ascii")
        except FileNotFoundError:
            # A hidden proc entry is not death. A host pidfd, when available,
            # distinguishes that denial from actual exit of this kernel object.
            return (
                False
                if descriptor is not None and select.select([descriptor], [], [], 0)[0]
                else None
            )
        return raw[raw.rindex(")") + 2 :].split()[19] == value["start_ticks"]
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        StopIteration,
        AttributeError,
    ):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
