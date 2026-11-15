"""Physical qualification of sealed fresh SQL projects on native Windows/Linux.

These tests use real published CLI entry and ordinary owned fixture directories.
They do not qualify legacy adoption or arbitrary live rebinding.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from project_initialization.test_first_worker_preparation import run, successful

from processforge_core.database import DatabaseError
from processforge_core.executions.composition import select_execution_storage
from processforge_core.executions.model import ExecutionError

from .test_fresh_native_sql import publish
from .test_native_control import native_root as native_root

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned backend required",
)


@dataclass
class Project:
    root: Path
    cli: str
    workplace: Path
    project: Path
    binding: dict[str, Any]
    work: dict[str, Any]

    @property
    def flow(self) -> Path:
        return self.project / ".pf"

    @property
    def database(self) -> Path:
        return self.flow / self.binding["target_relative_path"]

    def worker(self, operation: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            self.root,
            operation,
            self.cli,
            "worker-run",
            operation,
            "--project-root",
            str(self.project),
            "--task",
            self.work["assignment_id"],
            *extra,
        )


@pytest.fixture
def project(native_root: Path) -> Project:
    cli = str(publish(native_root))
    workplace, root = native_root / "workplace", native_root / "project"
    successful(
        native_root,
        "workplace",
        cli,
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    successful(
        native_root,
        "init",
        cli,
        "project-init",
        "--project-root",
        str(root),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    )
    scope = native_root / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": [".pf/**", "AGENTS.md"],
                    "allowed_files": [".pf/artifacts/physical-fixture/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "physical-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/physical-fixture/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    work = json.loads(
        successful(
            native_root,
            "work",
            cli,
            "work-start",
            "--project-root",
            str(root),
            "--objective",
            "Qualify physical storage with a deterministic worker.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert work["action"] == "created_new"
    binding = json.loads((root / ".pf/data/execution-storage.json").read_bytes())
    return Project(native_root, cli, workplace, root, binding, work)


def _identity(project: Project) -> tuple[str, str, str, int]:
    with closing(
        sqlite3.connect(
            project.database.as_uri() + "?mode=ro",
            uri=True,
        )
    ) as sql:
        assert sql.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        identity = sql.execute(
            "SELECT store_id,scope,owner_id,format_version FROM pf_store_meta"
        ).fetchall()
        assert identity == [
            (
                project.binding["store_id"],
                "project",
                project.binding["project_id"],
                1,
            )
        ]
        assert UUID(identity[0][0]).hex == identity[0][0]
        assert sql.execute(
            "SELECT project_id,authority,readiness,active_coverage FROM execution_state"
        ).fetchall() == [(project.binding["project_id"], "sql", "ready", "complete")]
        return identity[0]


def _attach(project: Project) -> None:
    route = select_execution_storage(project.project, project.workplace)
    assert route.authority == "sql"
    assert route.repository is not None and route.repository.readiness().ready


def _durable_files(flow: Path) -> dict[str, bytes]:
    # SQLite read connections may create/remove transient WAL/shared-memory files.
    # Persistent guards and CLI diagnostics are not domain facts;
    # all other bytes and names, including execution projections, must hold.
    return {
        path.relative_to(flow).as_posix(): path.read_bytes()
        for path in flow.rglob("*")
        if path.is_file()
        and not path.name.endswith(("-wal", "-shm", ".guard"))
        and path != flow / "runtime/diagnostics/diagnostics.jsonl"
    }


def _refused(result: subprocess.CompletedProcess[str], code: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert lines[-1] == "FAIL: " + code
    assert all(line.startswith("PRESENT: ") for line in lines[:-1])


def test_offline_move_preserves_sql_but_refuses_bound_attempt_reuse(
    project: Project,
) -> None:
    identity = _identity(project)
    assert project.binding["profile_id"] == "project_main"
    assert project.binding["target_relative_path"] == "data/pf.sqlite3"
    before_read = _durable_files(project.flow)
    _attach(project)
    assert _durable_files(project.flow) == before_read
    for operation, extra in (
        ("prepare", ("--driver", "test-echo-worker")),
        ("start", ("--driver", "test-echo-worker", "--wait")),
        ("collect", ()),
    ):
        result = project.worker(operation, *extra)
        assert result.returncode == 0, result.stdout + result.stderr
    report = project.flow / "artifacts/physical-fixture/report.md"
    assert report.is_file()
    with closing(
        sqlite3.connect(project.database.as_uri() + "?mode=ro", uri=True)
    ) as sql:
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone() == (0,)
        assert sql.execute(
            "SELECT phase,outcome,collection FROM execution_attempts WHERE task_id=?",
            (project.work["assignment_id"],),
        ).fetchall() == [("absent", "completed", "collected")]
    assert _identity(project) == identity
    before_move = _durable_files(project.flow)
    original = project.project
    moved = original.with_name("renamed-project")
    original.rename(moved)  # All CLI processes and database connections are closed.
    project.project = moved
    assert not original.exists()
    assert _durable_files(project.flow) == before_move
    assert _identity(project) == identity
    _attach(project)
    result = project.worker("prepare", "--driver", "test-echo-worker")
    # Prepared input binds the original absolute project root. SQL attach after
    # rename does not authorize rewriting that immutable attempt or its cleanup.
    _refused(result, "temporary_cleanup_blocked:ValueError")
    assert _durable_files(project.flow) == before_move
    assert not original.exists()


@pytest.mark.parametrize(
    ("fault", "read_code", "write_code"),
    [
        ("missing", "execution_storage_not_ready", "execution_storage_not_ready"),
        ("corrupt", "database_corrupt", "database_corrupt"),
        ("foreign", "database_foreign", "database_foreign"),
        ("future", "execution_storage_not_ready", "execution_storage_not_ready"),
        ("schema-drift", "execution_storage_not_ready", "execution_storage_not_ready"),
        ("alias", "execution_storage_not_ready", "storage_path_unsafe"),
    ],
)
def test_bound_physical_target_refuses_without_fallback(
    project: Project,
    fault: str,
    read_code: str,
    write_code: str,
) -> None:
    _attach(project)
    original = _identity(project)
    # Publish a genuine JSON projection before breaking the authoritative target.
    result = project.worker("prepare", "--driver", "test-echo-worker")
    assert result.returncode == 0, result.stdout + result.stderr
    saved = project.root / "saved.sqlite3"
    project.database.rename(saved)
    alias: Path | None = None
    if fault == "corrupt":
        project.database.write_bytes(b"not a SQLite database\n")
    elif fault in {"future", "schema-drift"}:
        shutil.copyfile(saved, project.database)
        with closing(sqlite3.connect(project.database, isolation_level=None)) as sql:
            if fault == "future":
                sql.execute("PRAGMA user_version = 2")
            else:
                changed = sql.execute(
                    "UPDATE pf_schema_versions SET checksum=? WHERE namespace='execution'",
                    ("sha256:" + "0" * 64,),
                )
                assert changed.rowcount == 1
    elif fault == "foreign":
        # A valid, independently initialized SQL store, not hand-edited metadata.
        foreign = project.root / "foreign"
        successful(
            project.root,
            "foreign-init",
            project.cli,
            "project-init",
            "--project-root",
            str(foreign),
            "--workplace",
            str(project.workplace),
            "--type",
            "generic",
            "--process",
            "software-feature-development",
            "--apply",
        )
        shutil.copyfile(foreign / ".pf/data/pf.sqlite3", project.database)
    elif fault == "alias":
        # Directory junction on Windows needs no symlink privilege.
        target = project.flow / "data"
        alias = project.root / "aliased-data"
        target.rename(alias)
        shutil.copyfile(saved, alias / project.database.name)
        if os.name == "nt":
            linked = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(target), str(alias)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert linked.returncode == 0, linked.stdout + linked.stderr
        else:
            target.symlink_to(alias, target_is_directory=True)
    before = _durable_files(project.flow)
    saved_bytes = saved.read_bytes()
    alias_before = _durable_files(alias) if alias is not None else None
    with pytest.raises((DatabaseError, ExecutionError)) as error:
        _attach(project)
    assert isinstance(error.value, (DatabaseError, ExecutionError))
    assert error.value.code == read_code
    assert _durable_files(project.flow) == before
    result = project.worker("prepare", "--driver", "test-echo-worker")
    _refused(result, write_code)
    assert _durable_files(project.flow) == before
    assert saved.read_bytes() == saved_bytes
    if alias is not None:
        assert _durable_files(alias) == alias_before
    assert (
        json.loads((project.flow / "data/execution-storage.json").read_bytes())
        == project.binding
    )
    if fault == "missing":
        assert not project.database.exists()
    # Restoration is fixture teardown, not product repair/rebinding.
    if fault != "alias":
        project.database.unlink(missing_ok=True)
        saved.rename(project.database)
        assert _identity(project) == original


def test_real_wal_writer_contention_preserves_sql_authority(project: Project) -> None:
    identity = _identity(project)
    before = _durable_files(project.flow)
    with closing(
        sqlite3.connect(project.database.as_uri() + "?mode=rw", uri=True)
    ) as sql:
        assert sql.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        sql.execute("BEGIN IMMEDIATE")
        try:
            _attach(
                project
            )  # WAL readers are allowed while another writer owns the lock.
            result = project.worker("prepare", "--driver", "test-echo-worker")
            _refused(result, "database_busy")
        finally:
            sql.rollback()
    assert _durable_files(project.flow) == before
    assert _identity(project) == identity
    result = project.worker("prepare", "--driver", "test-echo-worker")
    assert result.returncode == 0, result.stdout + result.stderr
