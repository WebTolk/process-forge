"""Real source CLI initialization and preparation without launching a worker.

This covers source/file-only admission. It does not qualify an enrolled native
execution backend or model execution.
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
RAW_PROBE = """
import json, sys
from pathlib import Path
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel
from processforge_core import build_configuration_provider
from processforge_core.executions.composition import select_execution_storage
project, workplace = map(Path, sys.argv[1:])
configuration = build_configuration_provider(project_root=project, workplace_root=workplace)
route = select_execution_storage(project, workplace, configuration=configuration)
if route.repository is not None:
    assert route.repository.readiness().ready
kernel = RawIngressKernel(workplace, flow_root=project / '.pf', configuration=configuration)
receipt = kernel.ingest(NativeAgentEvent('generic', 'integration', 'reply', {'first': True}, source_project_ref=str(project)))
with kernel.storage.connection(kernel.database) as connection:
    assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print(json.dumps({'accepted': receipt.accepted, 'execution_sql_selected': route.repository is not None}))
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
def test_initialized_project_first_raw_and_worker_preparation(
    tmp_path: Path, history_owner: str
) -> None:
    workplace, project = tmp_path / "workplace", tmp_path / "project"
    successful(
        tmp_path,
        "workplace",
        str(CLI),
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    legacy = workplace / "runtime/agent-events/raw/v1/history.ndjson"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    reference = project if history_owner == "own" else tmp_path / "foreign-project"
    legacy.write_text(
        json.dumps({"source_project_ref": str(reference)}) + "\n", encoding="utf-8"
    )
    before = legacy.read_bytes()
    initialized = successful(
        tmp_path,
        "init",
        str(CLI),
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
    raw = run(tmp_path, "raw", "-c", RAW_PROBE, str(project), str(workplace))
    assert legacy.read_bytes() == before
    database = project / ".pf/runtime/agent-events/hooks.sqlite3"
    if history_owner == "own":
        assert raw.returncode != 0
        assert "JournalMigrationRequired" in raw.stderr
        assert "raw_journal_migration_required" in raw.stderr
        assert not database.exists()
        return
    assert raw.returncode == 0, raw.stderr
    assert json.loads(raw.stdout)["accepted"] is True
    assert database.is_file()
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
            str(CLI),
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
        str(CLI),
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
