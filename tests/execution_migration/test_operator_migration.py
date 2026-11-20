"""Public offline migration works without a historical process manager."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from processforge_core.composition import build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.executions.composition import select_execution_storage
from processforge_core.executions.model import ExecutionKey
from processforge_core.runtime.execution_admission import ExecutionAdmission

from .test_migration import collection_files, payload

SOURCE = Path(__file__).resolve().parents[2]


@pytest.fixture
def legacy(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    (flow / "process-forge.yaml").write_text(
        "project:\n  id: operator-project\n", encoding="utf-8"
    )
    status = flow / "runtime/agent-runs/run/task/status.json"
    status.parent.mkdir(parents=True)
    status.write_text(json.dumps(payload("task", attempt=3)), encoding="utf-8")
    return project


def invoke(
    project: Path, *arguments: str
) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SOURCE / "tools/migrate-storage.py"),
            "--project-root",
            str(project),
            "--device-config",
            str(project.parent / "device.yaml"),
            *arguments,
        ],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert not result.stderr, result.stderr
    return result, json.loads(result.stdout)


def test_public_offline_import_preserves_snapshot_and_repeat_identity(legacy: Path):
    source = legacy / ".pf/runtime/agent-runs/run/task/status.json"
    before = source.read_bytes()
    child, report = invoke(legacy, "--apply", "--offline-confirmed")
    assert child.returncode == 0 and report["status"] == "ready", report
    provider = ConfigurationProvider.pinned(PFConfig())
    route = select_execution_storage(legacy, configuration=provider)
    assert route.repository is not None
    record = route.repository.load(ExecutionKey("operator-project", "run", "task", 3))
    assert record is not None
    assert json.loads(record.payload_json) == payload("task", attempt=3)
    binding = legacy / ".pf/data/execution-storage.json"
    identity = binding.read_bytes()
    child, report = invoke(legacy, "--resume", "--offline-confirmed")
    assert child.returncode == 0 and report["status"] == "ready", report
    assert binding.read_bytes() == identity
    assert source.read_bytes() == before


@pytest.mark.parametrize("completion", ["present", "absent", "previous_attempt"])
def test_public_migration_preserves_completed_collection(
    legacy: Path, completion: str
) -> None:
    status = legacy / ".pf/runtime/agent-runs/run/task/status.json"
    receipt, complete = collection_files(legacy, status, "operator-project")
    if completion == "absent":
        complete.unlink()
    elif completion == "previous_attempt":
        state = json.loads(status.read_bytes())
        state["attempt"] = 4
        state["prepared_input"]["path"] = state["prepared_input"]["path"].replace(
            "/attempts/3/", "/attempts/4/"
        )
        status.write_text(json.dumps(state), encoding="utf-8")
    before = {p: p.read_bytes() for p in (status, receipt, complete) if p.exists()}
    child, report = invoke(legacy, "--apply", "--offline-confirmed")
    assert child.returncode == 0 and report["status"] == "ready", report
    route = select_execution_storage(
        legacy, configuration=ConfigurationProvider.pinned(PFConfig())
    )
    assert route.repository is not None
    record = route.repository.load_latest("run", "task")
    assert record is not None and record.outcome == "completed"
    assert record.collection == ("collected" if completion == "present" else "pending")
    child, report = invoke(legacy, "--resume", "--offline-confirmed")
    assert child.returncode == 0 and report["status"] == "ready", report
    assert route.repository.load_latest("run", "task") == record
    assert {p: p.read_bytes() for p in before} == before


def test_no_confirmation_does_not_start_legacy_migration(legacy: Path):
    child, report = invoke(legacy, "--apply")
    assert child.returncode == 1 and report["blocked"], report
    assert not (legacy / ".pf/data/execution-storage.json").exists()


def test_operator_confirmation_still_requires_actual_admission(legacy: Path):
    host = build_storage_migration_host(
        project_root=legacy,
        workplace_root=None,
        device_config_path=legacy.parent / "device.yaml",
        configuration=ConfigurationProvider.pinned(PFConfig()),
        offline_confirmed=True,
    )
    context = host.context
    assert host.service.safety(context).state == "unknown"
    with ExecutionAdmission().maintenance(legacy, None):
        first = host.service.safety(context)
        assert first.state == "proven"
    assert host.service.safety(context).state == "unknown"
    with ExecutionAdmission().maintenance(legacy, None):
        assert host.service.safety(context).generation == first.generation


def test_known_live_runtime_blocks_offline_migration(legacy: Path):
    workplace = legacy.parent / "workplace"
    state = workplace / "runtime/pf-runtime/service.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    (workplace / "workplace.yaml").write_text(
        "workplace:\n  id: operator-workplace\n", encoding="utf-8"
    )
    (legacy / ".pf/process-forge.local.yaml").write_text(
        json.dumps({"workplace": {"manifest": str(workplace / "workplace.yaml")}}),
        encoding="utf-8",
    )
    child, report = invoke(
        legacy, "--workplace-root", str(workplace), "--apply", "--offline-confirmed"
    )
    assert child.returncode == 1 and report["blocked"], report
    assert not (legacy / ".pf/data/execution-storage.json").exists()


def test_public_journals_import_before_and_after_storage_identity(tmp_path: Path):
    from maintenance_integration.test_acceptance import _cli, _legacy_sources

    project, workplace, events, raw, _event = _legacy_sources(tmp_path)
    (workplace / "workplace.yaml").write_text(
        "workplace:\n  id: journal-workplace\n", encoding="utf-8"
    )
    originals = {path: path.read_bytes() for path in (events, raw)}
    args = (
        "import",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--apply",
        "--skip-invalid",
    )
    first = _cli(tmp_path, *args)
    assert first["status"] == "ready", first
    child, report = invoke(
        project, "--workplace-root", str(workplace), "--apply", "--offline-confirmed"
    )
    assert child.returncode == 0 and report["status"] == "ready", report
    identities = project / ".pf/data/storage-identities.json"
    before = identities.read_bytes()
    repeated = _cli(tmp_path, *args)
    assert repeated["status"] == "ready", repeated
    assert repeated["counts"]["imported"] == 0
    assert repeated["counts"]["already_present"] >= 2
    assert identities.read_bytes() == before
    assert all(path.read_bytes() == content for path, content in originals.items())


def crash_import(project: Path, phase: str, workplace: Path | None = None) -> None:
    """Kill a real CLI process after durable SQL work, without Python cleanup."""
    script = """
import os, runpy, sys
from pathlib import Path
tool, project, device, phase, workplace = sys.argv[1:]
entry = runpy.run_path(tool)
from processforge_core.maintenance.execution_migration import ExecutionMigrationService
from processforge_core.maintenance import storage_migration
if phase == 'identity':
    original = storage_migration._publish_pin
    def publish(root, target, store_id, checksum, state):
        if target.kind == 'events' and state == 'ready':
            os._exit(77)
        return original(root, target, store_id, checksum, state)
    storage_migration._publish_pin = publish
else:
    name = '_import' if phase == 'import' else '_cutover'
    original = getattr(ExecutionMigrationService, name)
    def commit_then_die(self, *args, **kwargs):
        original(self, *args, **kwargs)
        os._exit(77)
    setattr(ExecutionMigrationService, name, commit_then_die)
args = ['--project-root', project, '--device-config', device, '--apply', '--offline-confirmed', '--json']
if workplace:
    args += ['--workplace-root', workplace]
raise SystemExit(entry['main'](args))
"""
    child = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            script,
            str(SOURCE / "tools/migrate-storage.py"),
            str(project),
            str(project.parent / "device.yaml"),
            phase,
            str(workplace) if workplace else "",
        ],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert child.returncode == 77, child.stdout + child.stderr


@pytest.mark.parametrize("phase", ["import", "cutover"])
def test_offline_execution_resume_after_process_death(legacy: Path, phase: str):
    import sqlite3

    source = legacy / ".pf/runtime/agent-runs/run/task/status.json"
    source_bytes = source.read_bytes()
    crash_import(legacy, phase)
    binding_path = legacy / ".pf/data/execution-storage.json"
    binding_bytes = binding_path.read_bytes()
    binding = json.loads(binding_bytes)
    database = legacy / ".pf" / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        checkpoint, state = sql.execute(
            "SELECT checkpoint,state FROM execution_migrations"
        ).fetchone()
        assert checkpoint > 0
        assert state == ("importing" if phase == "import" else "ready")
    evidence = {
        path: path.read_bytes()
        for path in (legacy / ".pf").rglob("*")
        if path.is_file() and ("backup" in path.parts or path.name == "plan.json")
    }
    assert evidence
    child, report = invoke(legacy, "--resume", "--offline-confirmed")
    assert child.returncode == 0 and report["status"] == "ready", report
    route = select_execution_storage(
        legacy, configuration=ConfigurationProvider.pinned(PFConfig())
    )
    assert route.repository is not None
    record = route.repository.load(ExecutionKey("operator-project", "run", "task", 3))
    assert record is not None and json.loads(record.payload_json) == payload(
        "task", attempt=3
    )
    assert (
        binding_path.read_bytes() == binding_bytes
        and source.read_bytes() == source_bytes
    )
    assert all(path.read_bytes() == raw for path, raw in evidence.items())


def test_offline_uuid_resume_after_process_death(tmp_path: Path):
    from maintenance_integration.test_acceptance import _cli, _legacy_sources

    project, workplace, events, raw, _event = _legacy_sources(tmp_path)
    (workplace / "workplace.yaml").write_text(
        "workplace:\n  id: journal-workplace\n", encoding="utf-8"
    )
    originals = {path: path.read_bytes() for path in (events, raw)}
    _cli(
        tmp_path,
        "import",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--apply",
        "--skip-invalid",
    )
    crash_import(project, "identity", workplace)
    pins = project / ".pf/data/storage-identities.json"
    pending = next(
        row for row in json.loads(pins.read_bytes())["slots"] if row["kind"] == "events"
    )
    assert pending["state"] == "pending"
    evidence = {
        path: path.read_bytes()
        for path in (project / ".pf/data/storage-migrations").rglob("*")
        if path.is_file() and ("backup" in path.parts or path.name == "plan.json")
    }
    assert evidence
    child, report = invoke(
        project, "--workplace-root", str(workplace), "--resume", "--offline-confirmed"
    )
    assert child.returncode == 0 and report["status"] == "ready", report
    ready = next(
        row for row in json.loads(pins.read_bytes())["slots"] if row["kind"] == "events"
    )
    assert ready == {**pending, "state": "ready"}
    assert all(
        path.read_bytes() == data for path, data in {**originals, **evidence}.items()
    )
