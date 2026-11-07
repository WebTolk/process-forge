"""A real process death after intent, without in-memory scratch finalizers."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import processforge as core
import pytest

from processforge_core.configuration import DeviceConfigurationSource
from processforge_core.executions.composition import ExecutionStorage
from processforge_core.prepared import input as prepared_input
from processforge_core.prepared import retry_publication as rp
from tests.executions.test_lifecycle import sql_cli_fixture as sql_cli_fixture
from tests.executions.test_repository import isolated_path as isolated_path


def _death_worker(sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Collected only by the child invocation's explicit python_functions option."""
    root, _, args, _ = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    namespace = ".pf/tmp/process-death"
    (root / ".pf/tmp").mkdir(parents=True, exist_ok=True)
    semantic["scope"] = {
        "allowed_actions": ["write_product"],
        "allowed_files": [namespace + "/**"],
        "ownership": {
            "writer": True,
            "owner_id": "process-death",
            "owned_files": [namespace + "/**"],
        },
    }
    publish = rp.publish_raw_once

    def commit_then_die(project: Path, destination: Path, raw: bytes) -> None:
        publish(project, destination, raw)
        if destination.name == rp.INTENT:
            Path(os.environ["W76_DEATH_PROOF"]).write_text(
                json.dumps({"root": str(root), "args": vars(args)}), encoding="utf8"
            )
            os._exit(73)

    monkeypatch.setattr(rp, "publish_raw_once", commit_then_die)
    core.command_worker_run_prepare(args)
    raise AssertionError("intent boundary was not reached")


@pytest.mark.skipif(os.name != "nt", reason="Windows Job process-death/reap proof")
def test_process_death_keeps_exact_scratch_and_replays_n(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pf_native_control import spawn_owned

    proof = tmp_path / "proof.json"
    env = dict(os.environ, W76_DEATH_PROOF=str(proof))
    source = Path(__file__).resolve().parents[2]
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(Path(__file__).resolve()),
        "-q",
        "-p",
        "no:cacheprovider",
        "-o",
        "python_functions=_death_worker",
    ]
    with (
        (tmp_path / "child.stdout").open("wb") as stdout,
        (tmp_path / "child.stderr").open("wb") as stderr,
    ):
        proc = spawn_owned(
            command,
            receipt_path=tmp_path / "native-tree.json",
            identity={"run_id": "publication-crash", "task_id": "child", "attempt": 1},
            env=env,
            cwd=source,
            stdout=stdout,
            stderr=stderr,
        )
        try:
            assert proc.wait(timeout=30) == 73, (tmp_path / "child.stderr").read_text(
                errors="replace"
            )
        finally:
            if proc.poll() is None:
                getattr(proc, "native_job").stop(deadline=time.monotonic() + 5)
            proc.wait(timeout=5)
            getattr(proc, "native_job").close()
    result = json.loads(proof.read_text(encoding="utf8"))
    root = Path(result["root"])
    assert root.is_relative_to(Path(os.environ["W3_FIXTURE_ROOT"]))
    args = argparse.Namespace(**result["args"])
    paths = core._work_paths.worker_run(root, "run", "task")
    directory = paths["root"] / "attempts/1"
    publication = rp.load_publication(root, directory)
    document_raw = (directory / "prepared-input.json").read_bytes()
    document = rp.strict_json(document_raw)
    scratch = root / document["managed_scratch"]["path"]
    identity = (scratch.stat().st_dev, scratch.stat().st_ino)
    assert (
        scratch.is_dir()
        and not (directory / "scratch-preparation-failure.json").exists()
    )
    assert not paths["status"].exists()
    monkeypatch.setattr(
        DeviceConfigurationSource,
        "default_path",
        staticmethod(lambda: root / "device.yaml"),
    )
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    monkeypatch.setattr(
        prepared_input, "semantic_input", lambda *a, **k: document["input"]
    )
    monkeypatch.setattr(
        core._process_event_recorder, "emit_process_event", lambda *a, **k: {}
    )
    assert core.command_worker_run_prepare(args) == 0
    assert core.json_read(paths["status"])["attempt"] == 1
    assert (
        core.json_read(paths["command"])["prepared_input"]
        == publication.intent["new_reference"]
    )
    assert (directory / "prepared-input.json").read_bytes() == document_raw
    assert (scratch.stat().st_dev, scratch.stat().st_ino) == identity
    assert not (paths["root"] / "attempts/2").exists()
