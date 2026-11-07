"""Revision 2 operation captures and canonical alias publication boundaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import processforge as core
import pytest

from processforge_core.executions.model import ExecutionError
from processforge_core.prepared import retry_publication as rp
from processforge_core.prepared.input import digest, encoded
from tests.worker_retry_state.test_protocol import capture, pending
from tests.worker_retry_state.test_retry import isolated_path as isolated_path
from tests.worker_retry_state.test_retry import legacy as legacy
from tests.worker_retry_state.test_retry import sql_cli_fixture as sql_cli_fixture


@pytest.mark.parametrize("after", [False, True])
@pytest.mark.parametrize("slot", ["status", "command"])
def test_canonical_alias_failure_replays_same_n(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, after: bool, slot: str
) -> None:
    root, args, paths = legacy
    original = capture(root, paths)
    link = os.link

    def fail(source: Any, target: Any) -> None:
        if Path(target).name == "retry-previous-" + slot + ".json":
            assert core._retry_pending(root, "run", "task") is not None
            if after:
                link(source, target)
            raise OSError("canonical alias boundary")
        link(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", fail)
        with pytest.raises(OSError, match="canonical alias boundary"):
            core.command_worker_run_prepare(args)
    publication = core._retry_pending(root, "run", "task")
    assert publication is not None
    assert capture(root, paths) == original
    assert core.command_worker_run_prepare(args) == 0
    assert core.json_read(paths["status"])["attempt"] == 2
    for key in rp.OBSERVATIONS:
        path = paths["root"] / "attempts/1" / ("retry-previous-" + key + ".json")
        assert rp.read_raw(root, path) == original[key]


def test_prototype_intent_is_preserved_and_rejected(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    publication = pending(legacy, monkeypatch)
    intent = dict(publication.intent)
    intent["schema_version"] = 1
    del intent["operation"]
    intent["operation"] = digest(encoded(intent))
    raw = encoded(intent)
    path = publication.directory / rp.INTENT
    path.write_bytes(raw)
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        core._retry_pending(root, "run", "task")
    assert path.read_bytes() == raw
    assert capture(root, paths) == before


def test_old_bytes_drift_during_capture_refuses_intent(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    link = os.link
    changed = paths["status"].read_bytes() + b" "

    def drift(source: Any, target: Any) -> None:
        link(source, target)
        if Path(target).name == "retry-publication-old-status.bin":
            paths["status"].write_bytes(changed)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", drift)
        assert core.command_worker_run_prepare(args) == 1
    assert core._retry_pending(root, "run", "task") is None
    assert paths["status"].read_bytes() == changed
    assert not (paths["root"] / "attempts/1/retry-previous-status.json").exists()


def test_poisoned_canonical_alias_is_preserved(legacy: Any) -> None:
    root, args, paths = legacy
    alias = paths["root"] / "attempts/1/retry-previous-status.json"
    alias.write_bytes(b"partial prototype evidence")
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert alias.read_bytes() == b"partial prototype evidence"
    assert capture(root, paths) == before
