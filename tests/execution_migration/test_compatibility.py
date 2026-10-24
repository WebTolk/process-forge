"""Keep existing CLI contracts and refuse unknown, pending or foreign targets."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from pf_cli.commands.journal_maintenance import JournalMaintenanceCommand
from pf_cli.parsers.journal_maintenance import register_journal_maintenance

from processforge_core.database import SchemaManager
from processforge_core.executions.schema import EXECUTION_SCHEMA
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.execution_migration import MIGRATION_ID

from .test_migration import Harness, payload


@pytest.fixture
def harness() -> Harness:
    """Create an independent fixture within the explicitly selected QA root."""
    return Harness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)


def parser(command: JournalMaintenanceCommand) -> argparse.ArgumentParser:
    """Use the actual cold parser/handler pair without shared host integration."""
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(required=True)
    register_journal_maintenance(commands.add_parser, execute=command.execute)
    return result


def test_cold_adapters_and_service_construction(harness: Harness) -> None:
    with (
        patch.object(Path, "open", side_effect=AssertionError("unexpected open")),
        patch.object(Path, "mkdir", side_effect=AssertionError("unexpected mkdir")),
    ):
        command = JournalMaintenanceCommand(
            execution_factory=lambda root: harness.service
        )
        parser(command)
        type(harness.service)(
            database=harness.database,
            repository=harness.repository,
            admission=harness.service.admission,
            backup=harness.service.backup,
        )


@pytest.mark.parametrize("operation", ["execution-inspect", "execution-import"])
def test_readonly_commands_one_json_no_initialization(
    harness: Harness, operation: str
) -> None:
    harness.status("task")
    command = JournalMaintenanceCommand(execution_factory=lambda root: harness.service)
    args = parser(command).parse_args(
        ["journal-maintenance", operation, "--project-root", str(harness.project)]
    )
    output = io.StringIO()
    with redirect_stdout(output):
        code = args.func(args)
    assert code == 0
    assert len(output.getvalue().splitlines()) == 1
    assert json.loads(output.getvalue())["status"] == "planned"
    assert not harness.database.target.path.exists() and not harness.evidence.exists()


def test_new_cli_missing_host_factory_fails_closed(harness: Harness) -> None:
    command = JournalMaintenanceCommand()
    args = parser(command).parse_args(
        [
            "journal-maintenance",
            "execution-import",
            "--project-root",
            str(harness.project),
        ]
    )
    output = io.StringIO()
    with redirect_stdout(output):
        assert args.func(args) == 1
    assert "execution_safety_unavailable" in output.getvalue()
    assert str(harness.project) not in output.getvalue()


def test_new_cli_real_success_and_resume(harness: Harness) -> None:
    harness.status("task")
    command = JournalMaintenanceCommand(execution_factory=lambda root: harness.service)
    args = parser(command).parse_args(
        [
            "journal-maintenance",
            "execution-import",
            "--project-root",
            str(harness.project),
            "--apply",
            "--offline-confirmed",
            "--evidence-dir",
            str(harness.evidence),
        ]
    )
    output = io.StringIO()
    with redirect_stdout(output):
        assert args.func(args) == 0
    result = json.loads(output.getvalue())
    assert result["status"] == "ready"
    args = parser(command).parse_args(
        [
            "journal-maintenance",
            "execution-resume",
            "--project-root",
            str(harness.project),
            "--migration-id",
            MIGRATION_ID,
            "--plan-checksum",
            result["plan_checksum"],
            "--evidence-dir",
            str(harness.evidence),
            "--apply",
            "--offline-confirmed",
        ]
    )
    output = io.StringIO()
    with redirect_stdout(output):
        assert args.func(args) == 0
    assert len(output.getvalue().splitlines()) == 1


def test_apply_missing_required_arguments_refuses(harness: Harness) -> None:
    command = JournalMaintenanceCommand(execution_factory=lambda root: harness.service)
    args = parser(command).parse_args(
        [
            "journal-maintenance",
            "execution-import",
            "--project-root",
            str(harness.project),
            "--apply",
        ]
    )
    with redirect_stdout(io.StringIO()):
        assert args.func(args) == 1
    assert not harness.evidence.exists()


def test_resume_parser_requires_exact_selectors_and_apply() -> None:
    with pytest.raises(SystemExit) as error:
        parser(JournalMaintenanceCommand()).parse_args(
            ["journal-maintenance", "execution-resume", "--project-root", "project"]
        )
    assert error.value.code == 2


@pytest.mark.parametrize(
    "operation,options",
    [
        ("backup", ["--database", "db", "--output", "out"]),
        ("verify", ["--backup", "backup"]),
        ("restore", ["--backup", "backup", "--destination", "target"]),
        ("inspect", ["--project-root", "root", "--workplace", "workplace"]),
        ("import", ["--project-root", "root", "--workplace", "workplace"]),
    ],
)
def test_old_five_parser_operations_unchanged(
    operation: str, options: list[str]
) -> None:
    args = parser(JournalMaintenanceCommand()).parse_args(
        ["journal-maintenance", operation, *options, "--json"]
    )
    assert args.maintenance_command == operation and args.json is True
    assert not hasattr(args, "offline_confirmed")


def test_pending_binding_missing_db_never_legacy_fallback(harness: Harness) -> None:
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_backup", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    assert not harness.database.target.path.exists()
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_resume_required"
    )
    assert harness.resume(plan)["status"] == "ready"


def test_execution_namespace_without_binding_refuses(harness: Harness) -> None:
    SchemaManager().initialize(harness.database, (EXECUTION_SCHEMA,))
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "execution_storage_not_ready"
    )


def test_foreign_and_corrupt_target_not_relabeled(harness: Harness) -> None:
    harness.database.target.path.parent.mkdir()
    harness.database.target.path.write_bytes(b"NOT A PF STORE")
    before = harness.database.target.path.read_bytes()
    assert harness.service.plan(harness.project)["blocked"]
    assert harness.database.target.path.read_bytes() == before


def test_missing_explicit_owner_no_rootname_fallback(harness: Harness) -> None:
    (harness.flow / "process-forge.yaml").write_text(
        "project:\n  name: no-id\n", encoding="utf-8"
    )
    assert (
        harness.service.plan(harness.project)["error"]["code"]
        == "project_identity_required"
    )


@pytest.mark.parametrize(
    "outside", ["../escape", "runtime/agent-runs/run/task", "data"]
)
def test_evidence_containment(harness: Harness, outside: str) -> None:
    result = harness.service.plan(harness.project, evidence_dir=harness.flow / outside)
    assert result["error"]["code"] == "execution_evidence_unsafe"


def test_receipt_drift_and_directory_floor_drift_block(harness: Harness) -> None:
    path = harness.status("task")
    receipt = path.parent / "exit.json"
    receipt.write_text('{"schema_version":1,"exit_code":0}', encoding="utf-8")
    plan = harness.service.plan(harness.project)
    receipt.write_text('{"schema_version":1,"exit_code":1}', encoding="utf-8")
    assert harness.apply(plan)["error"]["code"] == "execution_manifest_changed"


def test_live_sources_drift_on_resume_stays_pending(harness: Harness) -> None:
    path = harness.status("task")
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_verify", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    path.write_text(json.dumps(payload("task", attempt=2)), encoding="utf-8")
    assert harness.resume(plan)["error"]["code"] == "execution_manifest_changed"
    assert harness.scalar("SELECT authority FROM execution_state") == "legacy"


def test_committed_resume_does_not_reimport_updated_json(harness: Harness) -> None:
    path = harness.status("task")
    plan = harness.service.plan(harness.project)
    assert harness.apply(plan)["status"] == "ready"
    path.write_text(json.dumps(payload("task", attempt=99)), encoding="utf-8")
    assert harness.resume(plan)["status"] == "ready"
    assert harness.scalar("SELECT attempt FROM execution_attempts") == 1


def test_bad_frozen_raw_or_manifest_cannot_cutover(harness: Harness) -> None:
    harness.status("task")
    plan = harness.service.plan(harness.project)
    with patch.object(harness.service, "_import", side_effect=InterruptedError()):
        assert harness.apply(plan)["blocked"]
    source = next((harness.evidence / "sources").iterdir())
    source.write_bytes(b"tampered")
    assert harness.resume(plan)["error"]["code"] == "execution_source_changed"
    assert harness.scalar("SELECT authority FROM execution_state") == "legacy"


def test_plan_and_binding_identity_tampering_refuses(harness: Harness) -> None:
    plan = harness.service.plan(harness.project)
    changed = dict(plan, store_id="b" * 32)
    assert harness.apply(changed)["error"]["code"] == "execution_plan_changed"
    assert not harness.database.target.path.exists()


def test_report_failure_after_commit_remains_ready(harness: Harness) -> None:
    from processforge_core.maintenance import execution_migration as engine

    original = engine._atomic

    def failure(path: Path, value: object) -> None:
        if path.name == "report.json":
            raise OSError("private-error-text")
        original(path, value)

    plan = harness.service.plan(harness.project)
    with patch.object(engine, "_atomic", side_effect=failure):
        report = harness.apply(plan)
    assert report["status"] == "ready" and report["publication_pending"]
    assert harness.repository.readiness().ready
    assert harness.resume(plan)["status"] == "ready"


def test_error_payload_never_leaks_private_host_message(harness: Harness) -> None:
    command = JournalMaintenanceCommand(execution_factory=lambda root: harness.service)
    args = parser(command).parse_args(
        [
            "journal-maintenance",
            "execution-inspect",
            "--project-root",
            str(harness.project),
        ]
    )
    with patch.object(
        harness.service,
        "inspect",
        side_effect=MaintenanceError("execution_activity_unknown"),
    ):
        output = io.StringIO()
        with redirect_stdout(output):
            assert args.func(args) == 1
    assert str(harness.project) not in output.getvalue()


def test_nested_parent_traversal_evidence_is_rejected(harness: Harness) -> None:
    result = harness.service.plan(
        harness.project, evidence_dir=harness.flow / "maintenance/../runtime"
    )
    assert result["error"]["code"] == "execution_evidence_unsafe"


def test_isolated_import_performs_no_filesystem_or_connection_io() -> None:
    program = """
import pathlib, sqlite3
from unittest.mock import patch
with patch.object(pathlib.Path, 'open', side_effect=AssertionError('open')), \\
     patch.object(pathlib.Path, 'stat', side_effect=AssertionError('stat')), \\
     patch.object(pathlib.Path, 'mkdir', side_effect=AssertionError('mkdir')), \\
     patch.object(sqlite3, 'connect', side_effect=AssertionError('connect')):
    from processforge_core.maintenance.execution_migration import EXECUTION_MIGRATION_SCHEMA
    from pf_cli.commands.journal_maintenance import JournalMaintenanceCommand
    JournalMaintenanceCommand()
    assert EXECUTION_MIGRATION_SCHEMA.namespace == 'execution_migration'
print('cold')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "cold"


@pytest.mark.parametrize(
    "body",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"schema_version": 1, "project_id": "foreign"},
        {"schema_version": 1, "attempt": 2},
    ],
)
def test_receipt_schema_and_explicit_identity_must_match(
    harness: Harness, body: dict[str, object]
) -> None:
    path = harness.status("task")
    directory = path.parent / "attempts/1"
    directory.mkdir(parents=True)
    (directory / "exit.json").write_text(json.dumps(body), encoding="utf-8")
    assert harness.service.plan(harness.project)["blocked"]
