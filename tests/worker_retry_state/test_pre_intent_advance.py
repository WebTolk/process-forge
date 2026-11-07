"""Design probe: old attempt advances after an aborted pre-intent publication."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import processforge as core
import pytest

from processforge_core.prepared import retry_publication as rp
from tests.worker_retry_state.test_retry import isolated_path as isolated_path
from tests.worker_retry_state.test_retry import legacy as legacy
from tests.worker_retry_state.test_retry import sql_cli_fixture as sql_cli_fixture


def test_old_launch_after_pre_intent_failure_can_retry(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    ready = paths["status"].read_bytes()
    first = core.json_read(paths["status"])
    real_link = os.link

    def link(source: Any, target: Any) -> None:
        if Path(target).name == rp.INTENT:
            raise OSError("before intent commit")
        real_link(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(OSError, match="before intent commit"):
            core.command_worker_run_prepare(args)
    assert core._retry_pending(root, "run", "task") is None
    assert paths["status"].read_bytes() == ready
    archive = (root / first["prepared_input"]["path"]).with_name(
        "retry-previous-status.json"
    )
    assert not archive.exists()
    abandoned = paths["root"] / "attempts/2/retry-publication-old-status.bin"
    assert abandoned.read_bytes() == ready
    assert core.command_worker_run_start(args) == 1
    assert core.json_read(paths["status"])["status"] == "failed"
    assert (root / "target-count").read_bytes() == b"x"
    assert not archive.exists()
    # Intended liveness property. W69s2's fixed old archive name now conflicts
    # with the same old attempt's genuinely advanced terminal status.
    failed = paths["status"].read_bytes()
    assert core.command_worker_run_prepare(args) == 0
    assert archive.read_bytes() == failed
    assert abandoned.read_bytes() == ready
    assert core.json_read(paths["status"])["attempt"] > first["attempt"]
    assert (root / "target-count").read_bytes() == b"x"
