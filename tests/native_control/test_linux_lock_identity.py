"""Host observation of a private lock owner running inside the worker namespace."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pf_native_control as native
import pytest

from processforge_platforms.linux_process_identity import lock_owner_alive

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux procfs identity"
)


def test_namespace_lock_owner_has_observable_host_birth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "owner.json"
    script = """
import json, pathlib, sys, time
from processforge_platforms.linux_process_identity import lock_owner_identity
pathlib.Path(sys.argv[1]).write_text(json.dumps(lock_owner_identity()))
time.sleep(60)
"""
    process = native.spawn_owned([sys.executable, "-c", script, str(marker)])
    job = getattr(process, "native_job")
    try:
        deadline = time.monotonic() + 10
        while not marker.exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        owner = json.loads(marker.read_text())
        assert owner["pid"] > 2 and lock_owner_alive(owner) is True
        assert lock_owner_alive({**owner, "pid": owner["pid"] + 1}) is None
        assert (
            lock_owner_alive(
                {
                    **owner,
                    "linux_identity": {**owner["linux_identity"], "start_ticks": "0"},
                }
            )
            is False
        )
        assert (
            lock_owner_alive(
                {
                    **owner,
                    "linux_identity": {
                        **owner["linux_identity"],
                        "procfs_device": "foreign-view",
                    },
                }
            )
            is None
        )
        original = Path.read_text

        def hidden(path: Path, *args: Any, **kwargs: Any) -> str:
            if path == Path(f"/proc/{owner['pid']}/stat"):
                raise FileNotFoundError("fixture proc entry is hidden")
            return original(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "read_text", hidden)
            assert lock_owner_alive(owner) is None
        assert job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        assert lock_owner_alive(owner) is False
    finally:
        job.stop(deadline=time.monotonic() + 5)
        process.wait(timeout=5)
        job.close()
