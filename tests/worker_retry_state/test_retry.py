"""Attempt retirement and real bounded native retry regression."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import processforge as core
import pytest

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.executions.composition import ExecutionStorage
from processforge_core.executions.model import ExecutionError
from tests.executions.test_lifecycle import sql_cli_fixture as sql_cli_fixture
from tests.executions.test_repository import isolated_path as isolated_path


@pytest.fixture
def legacy(sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    root, _, args, driver_path = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    driver = core.load_yaml_document(driver_path)
    driver["command"]["args"] = [
        "-c",
        "import os,pathlib; p=pathlib.Path(os.environ['PF_PROJECT_ROOT'])/'target-count'; "
        "p.open('a').write('x'); raise SystemExit(1)",
    ]
    write_yaml_file(driver_path, driver)
    assert core.command_worker_run_prepare(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    return root, args, paths


@pytest.mark.skipif(os.name != "nt", reason="native Windows Job proof")
@pytest.mark.parametrize("stop", [False, True])
def test_real_failed_prepare_observe_start_or_stop(legacy: Any, stop: bool) -> None:
    root, args, paths = legacy
    assert core.command_worker_run_start(args) == 1
    old = core.load_agent_run_state(root, "run", "task")
    assert old["status"] == "failed" and old["attempt"] == 1
    originals = {
        n: paths[n].read_bytes() for n in ("status", "command", "process", "exit")
    }
    assert core.command_worker_run_prepare(args) == 0
    state = core.load_agent_run_state(root, "run", "task")
    assert state["status"] == "ready" and state["attempt"] == 2
    assert state["pid"] is None and state["started_at"] is None
    previous = root / old["prepared_input"]["path"]
    for name, raw in originals.items():
        assert (
            previous.with_name("retry-previous-" + name + ".json").read_bytes() == raw
        )
    assert not paths["process"].exists() and not paths["exit"].exists()
    assert (
        not (root / state["prepared_input"]["path"])
        .with_name("native-tree.json")
        .exists()
    )
    assert core.command_worker_run_status(args) == 0
    assert core.load_agent_run_state(root, "run", "task") == state
    assert (root / "target-count").read_text() == "x"
    if stop:
        assert core.command_worker_run_stop(args) == 0
        assert core.load_agent_run_state(root, "run", "task")["status"] == "cancelled"
    else:
        assert core.command_worker_run_start(args) == 1
        current = core.load_agent_run_state(root, "run", "task")
        assert current["attempt"] == 2 and current["status"] == "failed"
        assert core._legacy_tree_probe(root, "run", "task", current) is True
        assert (root / "target-count").read_text() == "xx"


@pytest.mark.parametrize("probe", [None, False])
def test_live_or_unknown_retirement_preserves_all(
    legacy: Any, monkeypatch: Any, probe: Any
) -> None:
    root, _, paths = legacy
    state = core.load_agent_run_state(root, "run", "task")
    state.update(status="starting", started_at="2026-11-05T00:00:00Z")
    core._core_common_json_io.json_write(paths["status"], state)
    originals = {
        n: core._observation_bytes(paths[n])
        for n in ("status", "command", "process", "exit")
    }
    monkeypatch.setattr(core, "_legacy_tree_probe", lambda *a, **k: probe)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        core._legacy_retire_projection(root, "run", "task", paths)
    assert originals == {n: core._observation_bytes(paths[n]) for n in originals}


def test_command_attempt_mismatch_is_closed(legacy: Any) -> None:
    root, _, paths = legacy
    command = core.json_read(paths["command"])
    command["attempt"] = 999
    core._core_common_json_io.json_write(paths["command"], command)
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        core._legacy_retire_projection(root, "run", "task", paths)


def test_starting_without_facts_fails_start_and_stop(legacy: Any, capsys: Any) -> None:
    root, args, paths = legacy
    state = core.load_agent_run_state(root, "run", "task")
    state.update(status="starting", pid=None)
    core._core_common_json_io.json_write(paths["status"], state)
    assert core.command_worker_run_start(args) == 1
    assert core.command_worker_run_stop(args) == 1
    output = capsys.readouterr().out
    assert "FAIL: execution_activity_unknown" in output
    assert "already running" not in output


@pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned process proof",
)
def test_retained_old_process_reaped_and_single_launch(legacy: Any) -> None:
    from pf_native_control import spawn_owned

    root, args, paths = legacy
    state = core.load_agent_run_state(root, "run", "task")
    facts = (root / state["prepared_input"]["path"]).with_name("native-tree.json")
    proc = spawn_owned(
        [sys.executable, "-c", "pass"],
        receipt_path=facts,
        identity={"run_id": "run", "task_id": "task", "attempt": 1},
    )
    try:
        proc.wait(timeout=5)
        key = core._core_runtime_observation_inputs.worker_process_key(
            root, "run", "task"
        )
        core._core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES[key] = proc
        state.update(status="failed", pid=proc.pid)
        core._core_common_json_io.json_write(paths["status"], state)
        assert core.command_worker_run_prepare(args) == 0
        assert (
            key not in core._core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES
        )
        assert core.command_worker_run_start(args) == 1
        assert core.load_agent_run_state(root, "run", "task")["attempt"] == 2
    finally:
        if proc.poll() is None:
            getattr(proc, "native_job").stop(deadline=core.time.monotonic() + 5)
        proc.wait(timeout=5)
        getattr(proc, "native_job").close()


@pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned process proof",
)
@pytest.mark.parametrize("fault", ["foreign", "live", "same-pid-wrong-birth"])
def test_real_live_and_foreign_facts_cannot_retire(legacy: Any, fault: str) -> None:
    from pf_native_control import spawn_owned

    root, _, paths = legacy
    state = core.load_agent_run_state(root, "run", "task")
    facts = (root / state["prepared_input"]["path"]).with_name("native-tree.json")
    proc = spawn_owned(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        receipt_path=facts,
        identity={
            "run_id": "run",
            "task_id": "task",
            "attempt": 9 if fault == "foreign" else 1,
        },
    )
    try:
        state.update(status="starting", pid=proc.pid)
        core._core_common_json_io.json_write(paths["status"], state)
        if fault == "same-pid-wrong-birth":
            raw = json.loads(facts.read_text())
            raw["birth_id"] = "wrong-incarnation"
            facts.write_text(json.dumps(raw))
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            core._legacy_retire_projection(root, "run", "task", paths)
        assert proc.poll() is None
        assert json.loads(facts.read_text())["pid"] == proc.pid
    finally:
        getattr(proc, "native_job").stop(deadline=core.time.monotonic() + 5)
        proc.wait(timeout=5)
        getattr(proc, "native_job").close()


def test_archive_conflict_preserves_current(legacy: Any) -> None:
    root, _, paths = legacy
    state = core.load_agent_run_state(root, "run", "task")
    archive = (root / state["prepared_input"]["path"]).with_name(
        "retry-previous-status.json"
    )
    archive.write_bytes(b"different original")
    before = paths["status"].read_bytes()
    with pytest.raises(ExecutionError, match="execution_identity_conflict"):
        core._legacy_retire_projection(root, "run", "task", paths)
    assert paths["status"].read_bytes() == before
    assert archive.read_bytes() == b"different original"


@pytest.mark.skipif(os.name != "nt", reason="native Windows Job proof")
def test_interrupted_resume_has_facts_and_supported_stop(
    legacy: Any, monkeypatch: Any
) -> None:
    import pf_native_control as native

    root, args, _ = legacy

    def interrupt(*args: Any) -> None:
        raise OSError("fixture interrupted before resume")

    monkeypatch.setattr(native, "_resume_initial_thread", interrupt)
    assert core.command_worker_run_start(args) == 1
    state = core.load_agent_run_state(root, "run", "task")
    assert core._legacy_tree_facts(root, "run", "task", state) is not None
    assert core._legacy_tree_probe(root, "run", "task", state) is True
    assert core.command_worker_run_stop(args) == 0
    assert core.load_agent_run_state(root, "run", "task")["status"] == "cancelled"
