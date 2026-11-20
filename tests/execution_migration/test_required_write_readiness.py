"""Ordinary entrypoints refuse legacy writes before cleanup, locks or spawn."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import processforge as core
import pytest

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.database import SQLiteDriver
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.storage_migration import StorageMigrationService

from .test_automatic import legacy_root as legacy_root


@pytest.fixture
def old_project(legacy_root: Path) -> Path:
    project = legacy_root / "project"
    flow = project / ".pf"
    write_yaml_file(flow / "process-forge.yaml", {"project": {"id": "old-project"}})
    write_yaml_file(
        flow / "assignments/task.yaml",
        {"id": "task", "run_id": "run", "status": "running"},
    )
    status = flow / "runtime/agent-runs/run/task/status.json"
    status.parent.mkdir(parents=True)
    status.write_text(
        json.dumps({"status": "prepared", "attempt": 1, "pid": None}),
        encoding="utf-8",
    )
    scratch = flow / "tmp/old-attempt/evidence.txt"
    scratch.parent.mkdir(parents=True)
    scratch.write_text("Keep original attempt evidence.\n", encoding="utf-8")
    return project


def files(project: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}


def forbidden(*_args: Any, **_kwargs: Any) -> Any:
    pytest.fail("ordinary mutation reached before SQL readiness")


@pytest.mark.parametrize(
    "operation",
    [
        "prepare",
        "start",
        "work-start",
        "transition",
        "continuation-create",
        "continuation-resume",
    ],
)
def test_legacy_refusal_precedes_all_ordinary_mutation(
    old_project: Path,
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = files(old_project)
    for name in (
        "_retry_pending",
        "_retry_refuse_pending",
        "_finalize_worker_scratch",
        "prepare_worker_run",
        "_legacy_worker_run_start",
        "registry_file_lock",
    ):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(SQLiteDriver, "_connect", forbidden)
    if operation in {"prepare", "start"}:
        args = argparse.Namespace(project_root=str(old_project), task="task")
        assert getattr(core, "command_worker_run_" + operation)(args) == 1
        assert capsys.readouterr().out.strip() == "FAIL: storage_migration_required"
    elif operation.startswith("continuation-"):
        from processforge_core.work.continuation import ContinuationService

        arguments: dict[str, Any] = {"continuation_id": "old-work"}
        if operation == "continuation-create":
            arguments.update(
                run_id="run",
                assignment_id="task",
                context_id="task-capsule",
                apply=True,
            )
        result = ContinuationService(old_project, None, core).request(
            operation.removeprefix("continuation-"), **arguments
        )
        assert result["action"] == "blocked"
        assert result["reason"] == "storage_migration_required"
    else:
        service = core.process_execution_service(old_project)
        result = (
            service.start(objective="Require migration")
            if operation == "work-start"
            else service.transition(
                outcome="completed", run_id="run", assignment_id="task"
            )
        )
        assert result["action"] == "blocked"
        assert result["reason"] == "storage_migration_required"
    assert all(path.read_bytes() == content for path, content in before.items())
    after = files(old_project)
    # Physical admission may establish its persistent lock inode; it conveys no
    # storage identity, no migration approval and no permission to launch.
    assert set(after) - set(before) <= {
        old_project / ".pf/runtime/.execution-admission.lock.guard",
        old_project / ".pf/runtime/.storage-identity.lock.guard",
    }
    assert not (old_project / ".pf/data").exists()


@pytest.mark.parametrize("operation", ["prepare", "start", "work-start", "transition"])
def test_actual_cli_refuses_unmigrated_project_without_private_paths(
    old_project: Path, operation: str
) -> None:
    source = Path(core.__file__).resolve().parents[1]
    before = files(old_project)
    arguments = (
        ["worker-run", operation, "--task", "task"]
        if operation in {"prepare", "start"}
        else ["work-start", "--objective", "Require migration", "--json"]
        if operation == "work-start"
        else [
            "work-transition",
            "--run",
            "run",
            "--assignment",
            "task",
            "--outcome",
            "completed",
            "--json",
        ]
    )
    child = subprocess.run(
        [
            sys.executable,
            "-B",
            str(source / "tools/processforge.py"),
            *arguments,
            "--project-root",
            str(old_project),
        ],
        cwd=source,
        env={
            **os.environ,
            "LOCALAPPDATA": str(old_project.parent / "device"),
            "XDG_CONFIG_HOME": str(old_project.parent / "device"),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == 1, child.stdout + child.stderr
    assert not child.stderr
    assert "storage_migration_required" in child.stdout
    assert str(old_project) not in child.stdout
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not (old_project / ".pf/data").exists()


def test_ordinary_write_never_invokes_legacy_migration(
    old_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        StorageMigrationService,
        "ensure_ready",
        forbidden,
    )
    before = files(old_project)
    with pytest.raises(MaintenanceError, match="^storage_migration_required$"):
        core._storage_first_write(old_project)
    assert files(old_project) == before


def test_storage_io_failure_has_typed_path_free_boundary(
    old_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from processforge_core.maintenance import first_write

    failure = PermissionError("private storage path")

    def unreadable(*_args: Any, **_kwargs: Any) -> Any:
        raise failure

    monkeypatch.setattr(first_write, "select_execution_storage", unreadable)
    with pytest.raises(MaintenanceError, match="^storage_activity_unknown$") as result:
        core._storage_first_write(old_project)
    assert result.value.__cause__ is failure
    assert "private" not in str(result.value)


def test_unexpected_storage_failure_propagates_without_retry(
    old_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from processforge_core.maintenance import first_write

    failure = RuntimeError("programming defect")
    calls = []

    def unexpected(*_args: Any, **_kwargs: Any) -> Any:
        calls.append(1)
        raise failure

    monkeypatch.setattr(first_write, "select_execution_storage", unexpected)
    with pytest.raises(RuntimeError) as result:
        core._storage_first_write(old_project)
    assert result.value is failure and calls == [1]
