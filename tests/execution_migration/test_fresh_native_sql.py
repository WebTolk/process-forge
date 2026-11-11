"""Real Windows/Linux sealed init and no-model lifecycle in fresh SQL storage.

Fixture publications exercise fresh roots; this does not attest legacy adoption
or execution of a model. Existing authority and native APIs are used unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pf_native_control as native
import pytest
from project_initialization.test_first_worker_preparation import successful

from .test_native_control import native_root as native_root

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned backend required",
)
SOURCE = Path(__file__).resolve().parents[2]


def publish(root: Path) -> Path:
    """Build a complete fixture using the existing public inventory and builder."""
    spec = importlib.util.spec_from_file_location(
        "checksum_inventory", SOURCE / "tools/validate-process-forge-checksums.py"
    )
    assert spec and spec.loader
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    payload = {
        name: inventory.released_content(path)
        for name, path in inventory.public_file_entries(SOURCE)
    }
    payload[native.INVENTORY] = b""
    build = native.build_publication(
        payload,
        version=(SOURCE / "VERSION").read_text(encoding="utf-8").strip(),
        source={"fixture": True},
        generated_at="fixture",
    )
    publication = root / "publication"
    publication.mkdir()
    for name, content in {**build.payload, native.MANIFEST: build.manifest}.items():
        target = publication / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return publication / "tools/processforge.py"


def test_sealed_fresh_sql_worker_lifecycle_clears_resolved_unknown(
    native_root: Path,
) -> None:
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
    flow = project / ".pf"
    binding = json.loads((flow / "data/execution-storage.json").read_bytes())
    database = flow / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        state = sql.execute(
            "SELECT project_id,authority,readiness,active_coverage "
            "FROM execution_state WHERE singleton=1"
        ).fetchone()
        assert state == (binding["project_id"], "sql", "ready", "complete")
    scope = native_root / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": [".pf/**", "AGENTS.md"],
                    "allowed_files": [".pf/artifacts/native-fixture/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "native-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/native-fixture/report.md",
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
            "work-start",
            cli,
            "work-start",
            "--project-root",
            str(project),
            "--objective",
            "Deterministic native SQL fixture without a model.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert work["action"] == "created_new"
    selectors = ["--project-root", str(project), "--task", work["assignment_id"]]
    successful(
        native_root,
        "prepare",
        cli,
        "worker-run",
        "prepare",
        *selectors,
        "--driver",
        "test-echo-worker",
    )
    successful(
        native_root,
        "start",
        cli,
        "worker-run",
        "start",
        *selectors,
        "--driver",
        "test-echo-worker",
        "--wait",
    )
    successful(native_root, "collect", cli, "worker-run", "collect", *selectors)
    runtime = flow / "runtime/agent-runs" / work["run_id"] / work["assignment_id"]
    status = json.loads((runtime / "status.json").read_bytes())
    assert status["status"] == "completed" and status["exit_code"] == 0
    assert status["failure_reason"] is None
    assert (project / ".pf/artifacts/native-fixture/report.md").is_file()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0] == 0
        attempt = sql.execute(
            "SELECT phase,outcome,collection,payload_json FROM execution_attempts WHERE task_id=?",
            (work["assignment_id"],),
        ).fetchone()
        assert attempt is not None and attempt[:3] == (
            "absent",
            "completed",
            "collected",
        )
        assert json.loads(attempt[3])["failure_reason"] is None
