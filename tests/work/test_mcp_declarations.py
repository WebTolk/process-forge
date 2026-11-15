"""MCP declarations are advisory; real resource and capsule guards still apply."""

from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn
from unittest.mock import Mock

import pytest
from execution_migration.test_fresh_native_sql import publish
from execution_migration.test_native_control import native_root as native_root
from project_initialization.test_first_worker_preparation import run, successful

from processforge_core.common.yaml_io import read_yaml_file, write_yaml_file
from processforge_core.prepared import input as prepared_input
from processforge_core.prepared.registry_resources import PreparedRegistryResourceReader
from processforge_core.prepared.resource_selection import (
    PreparedResourceSelectionPolicy,
)
from processforge_core.prepared.resources import REVOKED_STATUSES
from processforge_core.work.workspace_refs import WorkspaceAccessReferenceService

MCP_ID = "agent-configured-mcp"


@pytest.mark.parametrize("field", ["run_id", "assignment_id", "project_id", "attempt"])
def test_mcp_metadata_does_not_bypass_prepared_identity(
    tmp_path: Path, field: str
) -> None:
    identity = {
        "kind": "work",
        "run_id": "run",
        "assignment_id": "assignment",
        "project_id": "project",
        "context_id": "context",
        "attempt": 1,
    }
    semantic = {"resources": {"requested": {"mcp": [MCP_ID]}, "grants": {"mcp": []}}}
    document = {
        "schema_version": 1,
        "kind": "pf.prepared-input",
        "identity": identity,
        "project_root": str(tmp_path.resolve()),
        "input": semantic,
        "input_fingerprint": prepared_input.fingerprint(semantic),
    }
    identity[field] = 2 if field == "attempt" else "different"
    relative = ".pf/runtime/agent-runs/run/assignment/attempts/1/prepared-input.json"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    raw = json.dumps(document).encode("utf-8")
    path.write_bytes(raw)
    capsule_read = Mock(side_effect=AssertionError("Identity check was bypassed"))
    core = SimpleNamespace(
        rel=lambda target, root: target.relative_to(root).as_posix(),
        project_id=lambda _project: "project",
        assignment_capsule_path=capsule_read,
    )
    state = {
        "attempt": 1,
        "prepared_input": {"path": relative, "checksum": prepared_input.digest(raw)},
    }
    with pytest.raises(ValueError, match="^prepared_input_identity_mismatch$"):
        prepared_input.load(
            tmp_path, {"id": "assignment", "run_id": "run"}, state, core
        )
    capsule_read.assert_not_called()


def fail(reason: str) -> NoReturn:
    raise ValueError(reason)


def snapshot(status: str = "available") -> dict[str, Any]:
    return {
        "resolved": {
            "mcp": [
                {
                    "id": MCP_ID,
                    "status": status,
                    "path_ref": {"registry": "mcp", "id": MCP_ID},
                }
            ]
        }
    }


@pytest.mark.parametrize(
    "current",
    [
        {},
        {"resolved": {}},
        {"resolved": {"mcp": []}},
        snapshot("disabled"),
        snapshot("unavailable"),
        snapshot("missing"),
        snapshot("revoked"),
        {"resolved": {"mcp": [{"id": MCP_ID, "command": "changed"}]}},
    ],
    ids=[
        "no-resolved",
        "no-mcp",
        "empty",
        "disabled",
        "unavailable",
        "missing",
        "revoked",
        "drift",
    ],
)
@pytest.mark.parametrize("requested", [[], [MCP_ID]])
def test_mcp_never_enters_resource_or_connection_resolution(
    tmp_path: Path, current: dict[str, Any], requested: list[str]
) -> None:
    callbacks = {
        name: Mock(side_effect=AssertionError("MCP resolution callback: " + name))
        for name in (
            "selection",
            "workplace_manifest",
            "path_resolver",
            "revoked_statuses",
            "fail",
        )
    }
    reader = PreparedRegistryResourceReader(**callbacks)
    pinned = snapshot()
    before = copy.deepcopy((requested, pinned, current))
    assert reader.read(tmp_path, requested, pinned, current, "mcp") == []
    assert (requested, pinned, current) == before
    for callback in callbacks.values():
        callback.assert_not_called()


def test_declared_mcp_without_resolved_snapshot_entry(tmp_path: Path) -> None:
    reader = PreparedRegistryResourceReader(
        selection=lambda: PreparedResourceSelectionPolicy(
            matcher=lambda: (
                WorkspaceAccessReferenceService().workspace_ref_matches_resource
            ),
            fail=lambda: fail,
            revoked_statuses=lambda: REVOKED_STATUSES,
        ),
        workplace_manifest=lambda: lambda _project: None,
        path_resolver=Mock(side_effect=AssertionError("MCP path resolution")),
        revoked_statuses=lambda: REVOKED_STATUSES,
        fail=lambda: fail,
    )
    assert (
        reader.read(tmp_path, [MCP_ID], {"resolved": {}}, {"resolved": {}}, "mcp") == []
    )


@pytest.mark.parametrize("group", ["tools", "templates"])
@pytest.mark.parametrize(
    ("current_rows", "reason"),
    [
        ([], "resource_access_revoked"),
        ([{"id": MCP_ID, "status": "disabled"}], "resource_access_revoked"),
        ([{"id": MCP_ID, "status": "changed"}], "resource_generation_changed"),
    ],
)
def test_real_registry_resources_still_require_live_grants(
    tmp_path: Path, group: str, current_rows: list[dict[str, Any]], reason: str
) -> None:
    resolver = Mock(
        side_effect=AssertionError("Rejected resource reached path resolver")
    )
    reader = PreparedRegistryResourceReader(
        selection=lambda: PreparedResourceSelectionPolicy(
            matcher=lambda: (
                WorkspaceAccessReferenceService().workspace_ref_matches_resource
            ),
            fail=lambda: fail,
            revoked_statuses=lambda: REVOKED_STATUSES,
        ),
        workplace_manifest=lambda: lambda _project: None,
        path_resolver=resolver,
        revoked_statuses=lambda: REVOKED_STATUSES,
        fail=lambda: fail,
    )
    pinned = {"resolved": {group: [{"id": MCP_ID, "status": "available"}]}}
    with pytest.raises(ValueError, match="^" + reason + "$"):
        reader.read(
            tmp_path, [MCP_ID], pinned, {"resolved": {group: current_rows}}, group
        )
    resolver.assert_not_called()


@pytest.fixture
def sealed_project(native_root: Path) -> tuple[str, Path]:
    """Use the real publication builder and public init, never a storage stub."""
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
    binding = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
    database = project / ".pf" / binding["target_relative_path"]
    assert database.is_file()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute(
            "SELECT project_id,authority,readiness,active_coverage "
            "FROM execution_state WHERE singleton=1"
        ).fetchone() == (binding["project_id"], "sql", "ready", "complete")
    return cli, project


def start_work(
    root: Path,
    cli: str,
    project: Path,
    access: dict[str, list[str]],
) -> dict[str, Any]:
    source = project / "source.txt"
    source.write_text("Pinned source body\n", encoding="utf-8")
    scope = root / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": [".pf/**", "source.txt"],
                    "allowed_files": [".pf/artifacts/mcp-regression/**"],
                    "required_sources": ["source.txt"],
                    "workspace_access": access,
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "mcp-regression", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/mcp-regression/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    work = json.loads(
        successful(
            root,
            "work-start",
            cli,
            "work-start",
            "--project-root",
            str(project),
            "--objective",
            "Verify advisory MCP metadata with a deterministic worker.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert work["action"] == "created_new"
    return work


def prepare(
    root: Path, cli: str, project: Path, work: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    successful(
        root,
        "prepare",
        cli,
        "worker-run",
        "prepare",
        "--project-root",
        str(project),
        "--task",
        work["assignment_id"],
        "--driver",
        "test-echo-worker",
    )
    runtime = (
        project / ".pf/runtime/agent-runs" / work["run_id"] / work["assignment_id"]
    )
    status = json.loads((runtime / "status.json").read_bytes())
    assert status["status"] == "ready"
    document = json.loads((project / status["prepared_input"]["path"]).read_bytes())
    return runtime, document


@pytest.mark.parametrize("declared", [[], [MCP_ID]], ids=["empty", "unresolved-mcp"])
def test_public_cli_mcp_metadata_in_fresh_sealed_sql(
    native_root: Path,
    sealed_project: tuple[str, Path],
    declared: list[str],
) -> None:
    cli, project = sealed_project
    current = read_yaml_file(project / ".pf/contexts/project-context.snapshot.yaml")
    assert "mcp" not in current["resolved"]
    work = start_work(native_root, cli, project, {"mcp": declared})
    runtime, document = prepare(native_root, cli, project, work)
    assert document["identity"]["assignment_id"] == work["assignment_id"]
    assert document["identity"]["run_id"] == work["run_id"]
    assert document["input"]["resources"]["requested"]["mcp"] == declared
    assert document["input"]["resources"]["grants"]["mcp"] == []
    capsule = project / document["input"]["capsule"]["path"]
    capsule_before = capsule.read_bytes()
    selectors = ["--project-root", str(project), "--task", work["assignment_id"]]
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
    status = json.loads((runtime / "status.json").read_bytes())
    assert status["status"] == "completed" and status["exit_code"] == 0
    assert status["failure_reason"] is None
    assert (project / ".pf/artifacts/mcp-regression/report.md").read_text(
        encoding="utf-8"
    )
    assert capsule.read_bytes() == capsule_before
    prepared_path = project / status["prepared_input"]["path"]
    assert prepared_path.with_name("collection-receipt.json").is_file()
    assert prepared_path.with_name("collection-complete.json").is_file()
    binding = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
    database = project / ".pf" / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert sql.execute(
            "SELECT phase,outcome,collection FROM execution_attempts WHERE task_id=?",
            (work["assignment_id"],),
        ).fetchone() == ("absent", "completed", "collected")
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0] == 0


@pytest.mark.parametrize("group", ["tools", "templates", "knowledge_resources"])
def test_public_prepare_still_rejects_missing_real_resource(
    native_root: Path, sealed_project: tuple[str, Path], group: str
) -> None:
    cli, project = sealed_project
    work = start_work(native_root, cli, project, {group: ["absent-resource"]})
    result = run(
        native_root,
        "prepare-denied",
        cli,
        "worker-run",
        "prepare",
        "--project-root",
        str(project),
        "--task",
        work["assignment_id"],
        "--driver",
        "test-echo-worker",
    )
    assert result.returncode != 0
    assert "resource_not_in_snapshot" in result.stdout + result.stderr
    assert not (project / ".pf/artifacts/mcp-regression/report.md").exists()


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("source", "required_source_changed"),
        ("intent", "assignment_contract_changed"),
        ("file-scope", "assignment_contract_changed"),
        ("mcp-declaration", "assignment_contract_changed"),
        ("capsule", "immutable_context_changed"),
    ],
)
def test_advisory_mcp_does_not_relax_immutable_input(
    native_root: Path, sealed_project: tuple[str, Path], change: str, reason: str
) -> None:
    cli, project = sealed_project
    work = start_work(native_root, cli, project, {"mcp": []})
    runtime, document = prepare(native_root, cli, project, work)
    if change == "source":
        (project / "source.txt").write_text("Changed body\n", encoding="utf-8")
    elif change == "capsule":
        capsule = project / document["input"]["capsule"]["path"]
        capsule.write_bytes(capsule.read_bytes() + b"\n# changed capsule\n")
    else:
        assignment = project / ".pf/assignments" / (work["assignment_id"] + ".yaml")
        task = read_yaml_file(assignment)
        if change == "intent":
            task["objective"] += " changed"
        elif change == "file-scope":
            task["allowed_files"].append("outside/**")
        else:
            task["workspace_access"]["mcp"] = [MCP_ID]
        write_yaml_file(assignment, task)
    result = run(
        native_root,
        "start-denied",
        cli,
        "worker-run",
        "start",
        "--project-root",
        str(project),
        "--task",
        work["assignment_id"],
        "--driver",
        "test-echo-worker",
        "--wait",
    )
    assert result.returncode != 0
    assert reason in result.stdout + result.stderr
    assert not (project / ".pf/artifacts/mcp-regression/report.md").exists()
    assert json.loads((runtime / "status.json").read_bytes())["status"] == "blocked"


def test_advisory_mcp_does_not_grant_work_file_scope(
    native_root: Path, sealed_project: tuple[str, Path]
) -> None:
    cli, project = sealed_project
    scope = native_root / "scope-without-read.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["write_artifact"],
                    "allowed_read_files": [],
                    "allowed_files": [".pf/artifacts/mcp-regression/**"],
                    "workspace_access": {"mcp": [MCP_ID]},
                    "execution_mode": "docs_only",
                },
            }
        ),
        encoding="utf-8",
    )
    before = set((project / ".pf/runs").glob("*.yaml"))
    result = run(
        native_root,
        "denied-read-scope",
        cli,
        "work-start",
        "--project-root",
        str(project),
        "--objective",
        "MCP metadata grants no file scope.",
        "--process-id",
        "software-feature-development",
        "--scope-file",
        str(scope),
        "--json",
    )
    assert result.returncode != 0
    blocked = json.loads(result.stdout)
    assert blocked["reason"] == "work_scope_not_ready"
    assert "read_scope_missing" in blocked["execution_readiness"]["blockers"]
    assert set((project / ".pf/runs").glob("*.yaml")) == before
