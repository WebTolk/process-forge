"""Real governed stage advance after native collection, without model/services."""

from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest
from execution_migration.test_fresh_native_sql import publish
from execution_migration.test_native_control import native_root as native_root
from project_initialization.test_first_worker_preparation import successful


@pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned backend required",
)
def test_collect_governed_stage_advance_then_next_prepare(native_root):
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
                    "allowed_files": [".pf/artifacts/cycle/**", ".pf/tmp/cycle/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "cycle-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/cycle/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf8",
    )
    work = json.loads(
        successful(
            native_root,
            "start-work",
            cli,
            "work-start",
            "--project-root",
            str(project),
            "--objective",
            "Synthetic historical cleanup regression without a model.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert work["action"] == "created_new"
    worker = ["--project-root", str(project), "--task", work["assignment_id"]]
    selectors = [
        "--project-root",
        str(project),
        "--run",
        work["run_id"],
        "--assignment",
        work["assignment_id"],
        "--context-id",
        work["context"]["id"],
    ]
    successful(
        native_root,
        "prepare-a",
        cli,
        "worker-run",
        "prepare",
        *worker,
        "--driver",
        "test-echo-worker",
    )
    runtime = (
        project / ".pf/runtime/agent-runs" / work["run_id"] / work["assignment_id"]
    )
    state_a = json.loads((runtime / "status.json").read_bytes())
    attempt_a = project / state_a["prepared_input"]["path"]
    prepared_a = json.loads(attempt_a.read_bytes())
    scratch_a = project / prepared_a["managed_scratch"]["path"]
    (scratch_a / "payload").write_bytes(b"owned scratch")
    successful(
        native_root,
        "run-a",
        cli,
        "worker-run",
        "start",
        *worker,
        "--driver",
        "test-echo-worker",
        "--wait",
    )
    successful(native_root, "collect-a", cli, "worker-run", "collect", *worker)
    assert not scratch_a.exists()
    cleanup = json.loads(attempt_a.with_name("scratch-cleanup.json").read_bytes())
    assert cleanup["result"] == "deleted" and cleanup["deleted_files"] == 1
    originals = {
        name: attempt_a.with_name(name).read_bytes()
        for name in (
            "prepared-input.json",
            "collection-receipt.json",
            "collection-complete.json",
            "scratch-resource.json",
            "scratch-release.json",
        )
    }
    capsule = project / prepared_a["input"]["capsule"]["path"]
    capsule_bytes = capsule.read_bytes()
    binding = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
    database = project / ".pf" / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute(
            "SELECT phase,collection FROM execution_attempts WHERE task_id=? AND attempt=1",
            (work["assignment_id"],),
        ).fetchone() == ("absent", "collected")
    current = json.loads(
        successful(native_root, "state-a", cli, "work-state", *selectors, "--json")
    )
    evidence = current["evidence_guidance"]["transition_template"]["evidence"]
    for item in evidence:
        item["path"] = ".pf/artifacts/cycle/report.md"
    evidence_file = native_root / "evidence.json"
    evidence_file.write_text(json.dumps(evidence), encoding="utf8")
    transitioned = json.loads(
        successful(
            native_root,
            "advance",
            cli,
            "work-transition",
            *selectors,
            "--outcome",
            "completed",
            "--evidence-file",
            str(evidence_file),
            "--notes",
            "Synthetic fixture evidence for the governed cleanup cycle.",
            "--json",
        )
    )
    assert transitioned["action"] == "stage_transitioned"
    assert transitioned["stage"]["id"] != prepared_a["input"]["stage"]["id"]
    report = project / ".pf/artifacts/cycle/report.md"
    report.write_bytes(b"new stage output must not invalidate historical collection")
    successful(
        native_root,
        "prepare-b",
        cli,
        "worker-run",
        "prepare",
        *worker,
        "--driver",
        "test-echo-worker",
    )
    state_b = json.loads((runtime / "status.json").read_bytes())
    assert state_b["attempt"] == 2 and state_b["status"] == "ready"
    prepared_b = json.loads((project / state_b["prepared_input"]["path"]).read_bytes())
    assert prepared_b["input"]["stage"]["id"] == transitioned["stage"]["id"]
    assert (
        prepared_b["managed_scratch"]["path"] != prepared_a["managed_scratch"]["path"]
    )
    assert capsule.read_bytes() == capsule_bytes
    assert originals == {
        name: attempt_a.with_name(name).read_bytes() for name in originals
    }
    assert (
        report.read_bytes()
        == b"new stage output must not invalidate historical collection"
    )
    # End only the never-launched attempt owned by this fixture.
    successful(native_root, "cancel-b", cli, "worker-run", "stop", *worker)
