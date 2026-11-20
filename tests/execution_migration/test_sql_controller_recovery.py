"""Fresh sealed SQL CLI recovery with real Windows Jobs/Linux namespaces."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import pf_native_control as native
import pytest
from project_initialization.test_first_worker_preparation import run, successful

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy

from .test_fresh_native_sql import publish
from .test_native_control import native_root as native_root

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned backend required",
)


@pytest.fixture
def sql_work(native_root: Path):
    cli = str(publish(native_root))
    workplace, project = native_root / "workplace", native_root / "project"
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
        str(project),
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
                    "allowed_files": [".pf/artifacts/recovery/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "recovery-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/recovery/report.md",
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
            str(project),
            "--objective",
            "Real SQL recovery fixture without a model.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    worker = ["--project-root", str(project), "--task", work["assignment_id"]]
    runtime = (
        project / ".pf/runtime/agent-runs" / work["run_id"] / work["assignment_id"]
    )
    binding = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
    database = project / ".pf" / binding["target_relative_path"]
    try:
        yield native_root, cli, project, worker, runtime, database
    finally:
        # Recover only this fixture's authenticated tree even if an assertion fails.
        for receipt in runtime.glob("attempts/*/native-tree.json"):
            facts = json.loads(receipt.read_bytes())
            job = native.reopen_job(facts, pid=facts["pid"], identity=facts["identity"])
            if job is not None:
                try:
                    assert job.stop(deadline=time.monotonic() + 5)
                finally:
                    job.close()


def prepare(sql_work, *, pause: bool, timeout: int) -> Path:
    root, cli, project, worker, runtime, _database = sql_work
    driver = RuntimeDriverDefinitionPolicy().default_documents()["generic-shell"]
    driver["id"] = "recovery-shell"
    driver["security"]["require_explicit_executable"] = False
    driver["limits"]["timeout_seconds"] = timeout
    driver["environment"]["inherit"] = False
    driver["environment"]["variables"] = {"PYTHONDONTWRITEBYTECODE": "1"}
    driver["command"] = {
        "executable": sys.executable,
        "args": [
            "-c",
            "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)'],start_new_session=True); time.sleep(120)",
        ],
        "model_args": [],
    }
    if pause:
        hook = project / ".pf/tmp/loader"
        hook.mkdir(parents=True)
        (hook / "sitecustomize.py").write_text(
            "import os,pathlib,time\n"
            "if os.environ.get('PF_EXECUTION_LAUNCH_TOKEN'):\n"
            "    pathlib.Path(os.environ['PF_PROJECT_ROOT'], '.pf/tmp/loader/paused').write_text('before receipts')\n"
            "    time.sleep(120)\n",
            encoding="utf-8",
        )
        driver["environment"]["variables"]["PYTHONPATH"] = str(hook)
    path = project / ".pf/runtime/recovery-driver.yaml"
    write_yaml_file(path, driver)
    successful(
        root, "prepare", cli, "worker-run", "prepare", *worker, "--driver", str(path)
    )
    state = json.loads((runtime / "status.json").read_bytes())
    return (project / state["prepared_input"]["path"]).parent


def assert_absent(sql_work, attempt: Path, *, outcome: str | None = None) -> None:
    root, cli, _project, worker, runtime, database = sql_work
    facts = json.loads((attempt / "native-tree.json").read_bytes())
    job = native.reopen_job(facts, pid=facts["pid"], identity=facts["identity"])
    if job is not None:
        try:
            assert job.active() == 0
        finally:
            job.close()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0] == 0
        phase, stored = sql.execute(
            "SELECT phase,outcome FROM execution_attempts"
        ).fetchone()
        assert phase == "absent"
        if outcome is not None:
            assert stored == outcome
    successful(root, "status-replay", cli, "worker-run", "status", *worker)
    if outcome is not None:
        assert json.loads((runtime / "status.json").read_bytes())["status"] == outcome


@pytest.mark.parametrize("tamper", [False, True])
def test_fresh_sql_stop_before_first_wrapper_receipt(sql_work, tamper: bool) -> None:
    root, cli, project, worker, _runtime, _database = sql_work
    attempt = prepare(sql_work, pause=True, timeout=60)
    successful(root, "detached-start", cli, "worker-run", "start", *worker, "--detach")
    deadline = time.monotonic() + 10
    while not (project / ".pf/tmp/loader/paused").exists():
        assert time.monotonic() < deadline, "target loader did not pause"
        time.sleep(0.02)
    assert not (attempt / "process.json").exists()
    receipt = attempt / "native-tree.json"
    original = receipt.read_bytes()
    if tamper:
        foreign = json.loads(original)
        foreign["identity"]["attempt"] += 1
        receipt.write_text(json.dumps(foreign), encoding="utf-8")
        try:
            rejected = run(root, "stop-foreign", cli, "worker-run", "stop", *worker)
            assert rejected.returncode == 1
            assert "FAIL: execution_identity_conflict" in rejected.stdout
            assert "Traceback" not in rejected.stderr
            facts = json.loads(original)
            job = native.reopen_job(facts, pid=facts["pid"], identity=facts["identity"])
            assert job is not None
            try:
                assert job.active() > 0
            finally:
                job.close()
        finally:
            receipt.write_bytes(original)
    successful(root, "stop-recovered", cli, "worker-run", "stop", *worker)
    assert_absent(sql_work, attempt)
    successful(root, "stop-replay", cli, "worker-run", "stop", *worker)


@pytest.mark.parametrize("pause", [False, True])
def test_fresh_sql_detached_deadline_is_reconciled(sql_work, pause: bool) -> None:
    root, cli, _project, worker, _runtime, _database = sql_work
    attempt = prepare(sql_work, pause=pause, timeout=3)
    successful(root, "detached-start", cli, "worker-run", "start", *worker, "--detach")
    # The launching CLI has exited. A new controller must enforce the deadline,
    # including a loader stalled before any process/heartbeat/exit receipt.
    time.sleep(
        max(0, (attempt / "native-tree.json").stat().st_mtime + 3.2 - time.time())
    )
    successful(root, "deadline-status", cli, "worker-run", "status", *worker)
    assert_absent(sql_work, attempt, outcome="timed_out")
    assert (attempt / "controller-timeout.json").is_file()


@pytest.mark.parametrize("pause", [False, True])
def test_fresh_sql_wait_deadline_confirms_tree_absence(sql_work, pause: bool) -> None:
    root, cli, _project, worker, _runtime, _database = sql_work
    attempt = prepare(sql_work, pause=pause, timeout=3)
    result = run(root, "wait-timeout", cli, "worker-run", "start", *worker, "--wait")
    assert result.returncode == 1
    assert "TIMED_OUT:" in result.stdout
    assert "Traceback" not in result.stderr
    assert_absent(sql_work, attempt, outcome="timed_out")
