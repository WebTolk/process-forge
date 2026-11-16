"""Qualified fresh CLI initialization and preparation without launching a model.

Source and sealed installations qualify fresh journals; neither establishes
retirement of old workplace writers.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2]
CLI = SOURCE / "tools/processforge.py"
STORAGE_PROBE = """
import json, sqlite3, sys
from contextlib import closing
from pathlib import Path
cli, project, workplace = map(Path, sys.argv[1:])
source = cli.parents[1]
sys.path[:0] = [str(source / 'src'), str(source / 'tools')]
from processforge_core import build_configuration_provider
from processforge_core.executions.composition import select_execution_storage
configuration = build_configuration_provider(project_root=project, workplace_root=workplace)
route = select_execution_storage(project, workplace, configuration=configuration)
assert route.repository is not None
assert route.repository.readiness().ready
database = project / '.pf/runtime/agent-events/hooks.sqlite3'
with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
    assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print(json.dumps({'execution_sql_selected': True, 'raw_integrity': 'ok'}))
"""


def run(root: Path, label: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Keep device configuration, temporary files and CLI receipts in the fixture."""
    environment = os.environ.copy()
    for key, name in (
        ("LOCALAPPDATA", "appdata"),
        ("XDG_CONFIG_HOME", "xdg"),
        ("TEMP", "temp"),
        ("TMP", "temp"),
    ):
        target = root / name
        target.mkdir(exist_ok=True)
        environment[key] = str(target)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(SOURCE / "src"), str(SOURCE / "tools")]
        + ([environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else [])
    )
    command = [sys.executable, *arguments]
    result = subprocess.run(
        command,
        cwd=SOURCE,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    (root / f"{label}.json").write_text(
        json.dumps(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return result


def successful(root: Path, label: str, *arguments: str) -> str:
    result = run(root, label, *arguments)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.mark.parametrize("history_owner", ["foreign", "own"])
@pytest.mark.parametrize("distribution", ["source", "sealed"])
def test_initialized_project_first_raw_and_worker_preparation(
    tmp_path: Path, history_owner: str, distribution: str
) -> None:
    from execution_migration.test_fresh_native_sql import publish, source_cli

    cli = source_cli(tmp_path) if distribution == "source" else publish(tmp_path)
    workplace, project = tmp_path / "workplace", tmp_path / "project"
    successful(
        tmp_path,
        "workplace",
        str(cli),
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    legacy = workplace / "runtime/agent-events/raw/v1/history.ndjson"
    successful(
        tmp_path,
        "enable-fixture-hooks",
        str(cli),
        "config",
        "update",
        "--workplace",
        str(workplace),
        "--key",
        "runtime.garage_hooks",
        "--value",
        "true",
        "--json",
    )
    legacy.parent.mkdir(parents=True, exist_ok=True)
    reference = project if history_owner == "own" else tmp_path / "foreign-project"
    legacy.write_text(
        json.dumps({"source_project_ref": str(reference)}) + "\n", encoding="utf-8"
    )
    before = legacy.read_bytes()
    initialized = successful(
        tmp_path,
        "init",
        str(cli),
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    )
    assert "status: complete" in initialized
    assert "status: pass" in initialized
    envelope = tmp_path / "raw-input.json"
    envelope.write_text(
        json.dumps(
            {
                "provider": "generic",
                "adapter": "integration",
                "native_event_type": "reply",
                "raw_payload": {"first": True},
                "source_project_ref": str(project),
            }
        ),
        encoding="utf-8",
    )
    # Exercise the supported file-only Host command, whose trusted CLI entry
    # captures native capability before Core. A library import grants none.
    raw = run(
        tmp_path,
        "raw",
        str(cli),
        "runtime-host",
        "event",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--input",
        str(envelope),
        "--json",
    )
    assert legacy.read_bytes() == before
    database = project / ".pf/runtime/agent-events/hooks.sqlite3"
    if history_owner == "own":
        assert raw.returncode != 0
        assert "raw_journal_migration_required" in raw.stderr
        assert not database.exists()
        return
    assert raw.returncode == 0, raw.stderr
    receipt = json.loads(raw.stdout)
    assert receipt["accepted"] is True
    assert receipt["raw_event_id"]
    assert receipt["routing_status"] == "denied"
    assert receipt["diagnostics"]["adapter"]["reason"] == "adapter_untrusted"
    assert database.is_file()
    storage = successful(
        tmp_path,
        "raw-storage",
        "-c",
        STORAGE_PROBE,
        str(cli),
        str(project),
        str(workplace),
    )
    assert json.loads(storage) == {
        "execution_sql_selected": True,
        "raw_integrity": "ok",
    }
    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": [".pf/**", "AGENTS.md"],
                    "allowed_files": [".pf/artifacts/qualification/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "qualification", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/qualification/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    created = json.loads(
        successful(
            tmp_path,
            "work-start",
            str(cli),
            "work-start",
            "--project-root",
            str(project),
            "--objective",
            "Fixture qualification: prepare one assignment without launching it.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert created["action"] == "created_new"
    prepared = successful(
        tmp_path,
        "prepare",
        str(cli),
        "worker-run",
        "prepare",
        "--project-root",
        str(project),
        "--task",
        created["assignment_id"],
        "--driver",
        "codex-exec",
        "--model",
        "gpt-6.1-sol",
        "--reasoning-effort",
        "high",
    )
    assert "status=ready" in prepared
    runtime = (
        project
        / ".pf/runtime/agent-runs"
        / created["run_id"]
        / created["assignment_id"]
    )
    attempt = runtime / "attempts/1"
    assert (attempt / "prepared-input.json").is_file()
    assert (runtime / "command.json").is_file()
    status = json.loads((runtime / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "ready"
    assert status["task_id"] == created["assignment_id"]
    assert status["run_id"] == created["run_id"]
    assert status.get("pid") is None
    assert status.get("started_at") is None
    assert legacy.read_bytes() == before


@pytest.mark.parametrize("colocated", [False, True])
def test_source_init_creates_ready_sql_without_publishing_in_place(
    tmp_path: Path,
    colocated: bool,
) -> None:
    import sqlite3

    from execution_migration.test_fresh_native_sql import source_cli

    cli = source_cli(tmp_path)
    source = cli.parents[1]
    before = {path: path.read_bytes() for path in source.rglob("*") if path.is_file()}
    workplace = tmp_path / "workplace"
    project = source / ".pf/tmp/project" if colocated else tmp_path / "project"
    successful(
        tmp_path,
        "workplace",
        str(cli),
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    result = run(
        tmp_path,
        "unsealed-init",
        str(cli),
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "status: complete" in result.stdout
    assert "status: pass" in result.stdout
    assert result.stderr == ""
    flow = project / ".pf"
    binding = json.loads((flow / "data/execution-storage.json").read_bytes())
    database = flow / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute(
            "SELECT authority,readiness,active_coverage FROM execution_state WHERE singleton=1"
        ).fetchone() == ("sql", "ready", "complete")
    assert {
        path: path.read_bytes()
        for path in source.rglob("*")
        if path.is_file() and ".pf" not in path.relative_to(source).parts
    } == before
