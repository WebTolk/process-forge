"""Phase A host composition, full configuration access and native SQLite parity."""

from __future__ import annotations

import argparse
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from pf_cli.commands.configuration import ConfigurationCommand
from pf_cli.parsers.configuration import ConfigurationCommandParser
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel

from processforge_core import build_configuration_provider
from processforge_core.accounting.composition import WorkplaceAccounting
from processforge_core.accounting.storage import SQLiteAccountingRepository
from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.bootstrap import RuntimeBootstrap
from processforge_core.configuration import (
    ConfigService,
    ConfigurationError,
    ConfigurationProvider,
    DeviceConfigurationSource,
    PFConfig,
    ProjectPFConfig,
)
from processforge_core.configuration.yaml_store import YamlConfigStore
from processforge_core.database import DatabaseFactory, SQLiteDriver
from processforge_core.maintenance.journals import JournalMaintenanceService
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.project.configuration_inputs import ProjectConfigurationReader
from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.resources import local_search
from processforge_core.sqlite_storage import JournalError, transaction
from processforge_core.work.automation_readiness import AutomationReadinessService
from processforge_core.work.consistency import RunTaskConsistencyService


def _native_snapshot(root, configuration=None, *, device_config_path=None):
    from hashlib import sha256

    from processforge_core.runtime.command import configuration_snapshot_bytes

    prepared = root / ".pf/runtime/agent-runs/run/task/attempts/1/prepared-input.json"
    prepared.parent.mkdir(parents=True)
    identity = {
        "project_id": "project",
        "run_id": "run",
        "task_id": "task",
        "attempt": 1,
    }
    raw = configuration_snapshot_bytes(
        configuration or _pinned(), identity, device_config_path=device_config_path
    )
    path = prepared.with_name("configuration.snapshot.json")
    path.write_bytes(raw)
    digest = "sha256:" + sha256(raw).hexdigest()
    document = {
        "project_root": str(root),
        "identity": {
            "project_id": "project",
            "run_id": "run",
            "assignment_id": "task",
            "attempt": 1,
        },
        "native_launch": {
            "configuration": {
                "reader": "native",
                "access": "body",
                "path": path.relative_to(root).as_posix(),
                "sha256": digest,
                "size": len(raw),
            }
        },
    }
    environ = {
        "PF_CONFIGURATION_SNAPSHOT_PATH": str(path),
        "PF_CONFIGURATION_SNAPSHOT_SHA256": digest,
    }
    return prepared, path, document, environ


def test_native_snapshot_uses_exact_full_pinned_value_without_yaml_reads(
    workspace, monkeypatch
):
    from processforge_core.runtime.command import load_configuration_snapshot

    prepared, _path, document, environ = _native_snapshot(workspace)
    monkeypatch.setattr(
        YamlConfigStore, "read", lambda self: pytest.fail("live YAML read")
    )
    provider = load_configuration_snapshot(document, prepared, environ)
    assert provider is not None
    assert provider.get("runtime.metrics.interval_seconds") == 17
    assert provider.get("logging.raw_hooks") is False
    assert provider.snapshot(refresh=True) is provider.snapshot()


@pytest.mark.parametrize(
    "change", ["hash", "path", "identity", "metadata", "size", "unknown_config"]
)
def test_native_snapshot_rejects_corrupt_or_ungranted_body(workspace, change):
    from hashlib import sha256

    from processforge_core.runtime.command import load_configuration_snapshot

    prepared, path, document, environ = _native_snapshot(workspace)
    grant = document["native_launch"]["configuration"]
    if change == "hash":
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "path":
        environ["PF_CONFIGURATION_SNAPSHOT_PATH"] = str(path.with_name("other.json"))
    elif change == "metadata":
        grant["access"] = "metadata"
    elif change == "size":
        grant["size"] = 65537
    else:
        payload = json.loads(path.read_bytes())
        if change == "identity":
            payload["attempt"] = 2
        else:
            payload["configuration"]["unexpected"] = True
        raw = json.dumps(payload).encode()
        path.write_bytes(raw)
        grant.update(sha256="sha256:" + sha256(raw).hexdigest(), size=len(raw))
        environ["PF_CONFIGURATION_SNAPSHOT_SHA256"] = grant["sha256"]
    with pytest.raises(ValueError):
        load_configuration_snapshot(document, prepared, environ)


def test_old_prepared_snapshot_does_not_gain_body_read(workspace, monkeypatch):
    from processforge_core.runtime.command import load_configuration_snapshot

    prepared, _path, document, environ = _native_snapshot(workspace)
    del document["native_launch"]
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: pytest.fail("body read"))
    assert load_configuration_snapshot(document, prepared, {}) is None
    with pytest.raises(ValueError, match="grant_required"):
        load_configuration_snapshot(document, prepared, environ)


def test_native_snapshot_keeps_selected_device_as_nonreading_provenance(
    workspace, monkeypatch
):
    from processforge_core.runtime.command import load_configuration_snapshot

    selected = workspace / "selected-device.yaml"
    prepared, _path, document, environ = _native_snapshot(
        workspace, device_config_path=selected
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            YamlConfigStore, "read", lambda *a, **k: pytest.fail("YAML reread")
        )
        pinned = load_configuration_snapshot(document, prepared, environ)
        assert pinned is not None and pinned.device_path == selected
        original = pinned.current()
        assert pinned.snapshot(refresh=True).config is original
        assert not selected.exists()


def _sql_project(root, current_count=0):
    from processforge_core.database import (
        Database,
        DatabaseIdentity,
        DatabaseTarget,
        SchemaManager,
        SqlStatement,
    )
    from processforge_core.executions.schema import EXECUTION_SCHEMA
    from processforge_core.executions.sqlite_repository import SQLiteExecutionRepository
    from tests.executions.test_repository import payload

    flow = root / ".pf"
    _write(flow / "process-forge.yaml", "project:\n  id: project\n")
    store_id = uuid4().hex
    database = Database(
        SQLiteDriver(),
        DatabaseTarget(
            flow / "data/pf.sqlite3", DatabaseIdentity(store_id, "project", "project")
        ),
    )
    SchemaManager().initialize(database, (EXECUTION_SCHEMA,))
    with database.transaction() as session:
        session.execute(
            SqlStatement(
                "INSERT INTO execution_state(singleton,project_id,generation,authority,readiness,active_coverage,revision,next_history_seq) VALUES(1,'project',1,'sql','ready','complete',0,1)"
            )
        )
    _write(
        flow / "data/execution-storage.json",
        json.dumps(
            {
                "schema_version": 1,
                "project_id": "project",
                "store_id": store_id,
                "profile_id": "project_main",
                "target_relative_path": "data/pf.sqlite3",
            }
        ),
    )
    repo = SQLiteExecutionRepository(database, "project")
    for index in range(current_count):
        record = repo.allocate_attempt(
            "run", f"task{index}", payload(f"task{index}"), generation=1
        )
        repo.reserve_start(
            record.key,
            expected_revision=record.revision,
            generation=1,
            launch_token=uuid4().hex,
        )
    return repo


@pytest.mark.parametrize("current_count", [0, 1, 3, 129])
def test_actual_runtime_count_and_shutdown_share_active_only_route(
    workspace, monkeypatch, current_count
):
    import time
    from types import SimpleNamespace

    from pf_runtime.service import RuntimeProcess

    from processforge_core.runtime import metrics

    root, workplace = workspace / "project", workspace / "workplace"
    _sql_project(root, current_count)
    _write(
        workplace / "runtime/pf-runtime-host/state.json",
        json.dumps({"projects": [{"project_root": str(root)}], "sessions": {}}),
    )
    original_open = Path.open

    def checked_open(path, *args, **kwargs):
        assert path.name != "status.json", "terminal/status projection read"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(
        Path, "glob", lambda *args, **kwargs: pytest.fail("status/history glob")
    )
    runtime = object.__new__(RuntimeProcess)
    runtime.workplace_root, runtime.core, runtime._project_errors = (
        workplace,
        SimpleNamespace(),
        {},
    )
    result = metrics.shutdown_workers(workplace, runtime.core)
    expected = current_count if current_count <= 128 else None
    assert result["counts"]["running"] == expected
    assert runtime.active_worker_count([root]) == expected
    assert time.monotonic() > 0


def test_bound_storage_never_falls_back_to_projection(workspace):
    import time
    from types import SimpleNamespace

    from processforge_core.executions.composition import select_execution_storage
    from processforge_core.executions.model import ExecutionError
    from processforge_core.runtime import metrics

    root = workspace / "project"
    repo = _sql_project(root)
    repo.database.target.path.unlink()
    result = metrics.observe(
        "workers", workspace, [root], SimpleNamespace(), now=time.time()
    )
    assert result["counts"]["running"] is None
    with pytest.raises(ExecutionError):
        select_execution_storage(
            root, configuration=ConfigurationProvider.pinned(PFConfig())
        )


def test_unbound_existing_execution_namespace_refuses(workspace):
    from processforge_core.executions.composition import select_execution_storage
    from processforge_core.executions.model import ExecutionError

    root = workspace / "project"
    _sql_project(root)
    (root / ".pf/data/execution-storage.json").unlink()
    with pytest.raises(ExecutionError):
        select_execution_storage(
            root, configuration=ConfigurationProvider.pinned(PFConfig())
        )


@pytest.mark.parametrize("legacy", [False, True])
def test_real_native_wrapper_new_and_old_prepared_transport(workspace, legacy):
    import hashlib
    import sys

    import prepared_executor

    prepared, _path, document, environ = _native_snapshot(workspace)
    document.update(schema_version=1, kind="pf.prepared-input", input={})
    document["identity"]["context_id"] = "context"
    if legacy:
        del document["native_launch"]
        environ.clear()
    raw = json.dumps(document).encode()
    prepared.write_bytes(raw)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    environ.update(
        PF_PREPARED_INPUT_FILE=str(prepared),
        PF_PREPARED_INPUT_SHA256=digest,
        PF_WORKER_RUN_ID="run",
        PF_WORKER_TASK_ID="task",
        PF_WORKER_ATTEMPT="1",
        PF_PROJECT_ROOT=str(workspace),
    )
    options = argparse.Namespace(
        prepared_input=str(prepared),
        prepared_sha256=digest,
        heartbeat=str(prepared.parent / "heartbeat.json"),
        exit_path=str(prepared.parent / "exit.json"),
    )
    result = prepared_executor.run_target(
        options, [sys.executable, "-B", "-c", "import sys; sys.exit(0)"], environ
    )
    assert result == 0
    assert json.loads(Path(options.exit_path).read_bytes())["exit_code"] == 0
    assert "configuration" not in json.loads(Path(options.heartbeat).read_bytes())


def test_public_facade_reads_bound_sql_and_refuses_json_lifecycle_writes(
    workspace, monkeypatch
):
    import processforge as core

    root = workspace / "project"
    _sql_project(root, 1)
    original_open = Path.open

    def checked_open(path, *args, **kwargs):
        assert path.name != "status.json", "SQL route opened stale projection"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    assert core.load_agent_run_state(root, "run", "task0")["status"] == "starting"
    with pytest.raises(SystemExit, match="execution_storage_not_ready"):
        core.write_agent_run_state(root, {"id": "task0", "run_id": "run"}, {}, "ready")


def test_wrapper_rejects_corrupt_snapshot_before_target_popen(workspace, monkeypatch):
    import hashlib

    import prepared_executor

    prepared, path, document, environ = _native_snapshot(workspace)
    document.update(schema_version=1, kind="pf.prepared-input", input={})
    document["identity"]["context_id"] = "context"
    raw = json.dumps(document).encode()
    prepared.write_bytes(raw)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    environ.update(
        PF_PREPARED_INPUT_FILE=str(prepared),
        PF_PREPARED_INPUT_SHA256=digest,
        PF_WORKER_RUN_ID="run",
        PF_WORKER_TASK_ID="task",
        PF_WORKER_ATTEMPT="1",
    )
    path.write_bytes(b"{}")
    options = argparse.Namespace(
        prepared_input=str(prepared),
        prepared_sha256=digest,
        heartbeat=str(prepared.parent / "heartbeat.json"),
        exit_path=str(prepared.parent / "exit.json"),
    )
    monkeypatch.setattr(
        prepared_executor.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("spawned before validation"),
    )
    assert prepared_executor.run_target(options, ["unused"], environ) == 125


def test_runtime_retains_pinned_reload_diagnostics_without_live_config_reads():
    import threading

    from pf_runtime.service import RuntimeProcess

    runtime = object.__new__(RuntimeProcess)
    runtime.config_service = ConfigurationProvider.pinned(
        _pinned().current(), errors=("configuration_invalid",)
    )
    runtime.state_lock = threading.RLock()
    runtime.state = {}
    runtime.reload_configuration()
    assert runtime.metrics_interval == 17
    assert runtime.state["configuration"]["status"] == "invalid"
    assert runtime.state["configuration"]["error"] == "configuration_invalid"


@pytest.fixture
def workspace(request, monkeypatch):
    """Use only the explicit QA evidence root with inherited workspace access."""
    base = request.config.getoption("basetemp")
    if base is None:
        pytest.fail("explicit --basetemp is required for these isolated host tests")
    root = Path(base) / uuid4().hex
    root.mkdir(parents=True)
    monkeypatch.setattr(
        DeviceConfigurationSource,
        "default_path",
        staticmethod(lambda: root / "device.yaml"),
    )
    return root


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _pinned() -> ConfigurationProvider:
    return ConfigurationProvider.pinned(
        PFConfig.from_dict(
            {
                "runtime": {"metrics": {"interval_seconds": 17}, "garage_hooks": True},
                "logging": {"events": False, "raw_hooks": False},
                "database": {"driver": "sqlite"},
            }
        )
    )


class RecordingDriver(SQLiteDriver):
    def __init__(self):
        self.calls = []

    def _connect(self, database, *, timeout=5.0, isolation_level="", uri=False):
        self.calls.append((database, timeout, isolation_level, uri))
        return super()._connect(
            database, timeout=timeout, isolation_level=isolation_level, uri=uri
        )


def test_cold_builders_do_not_discover_or_touch_files(workspace, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("cold construction attempted I/O")

    monkeypatch.setattr(Path, "stat", denied)
    monkeypatch.setattr(Path, "lstat", denied)
    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(Path, "mkdir", denied)
    monkeypatch.setattr(SQLiteDriver, "_connect", denied)
    monkeypatch.setattr(ProjectMetadataReader, "workplace_manifest", denied)
    provider = build_configuration_provider(project_root=workspace / "project")
    assert provider.project_path == workspace / "project/.pf/configuration.yaml"
    assert provider.workplace_path is None
    assert ProjectConfigurationReader().configuration_provider().project_path is None
    assert RuntimeBootstrap.configuration_provider(object()).project_path is None
    assert ProcessEventJournal().driver is None
    assert RawHookJournal().driver is None


def test_missing_standalone_reads_create_nothing(workspace):
    provider = build_configuration_provider(project_root=workspace / "missing")
    assert provider.current() == PFConfig()
    assert provider.get("database.driver") == "sqlite"
    assert "database" not in provider.current().to_dict()
    assert list(workspace.iterdir()) == []


def test_full_precedence_presence_and_request_isolation(workspace, monkeypatch):
    device = _write(
        workspace / "device.yaml",
        "runtime: {metrics: {interval_seconds: 17}, garage_hooks: true}\nlogging: {events: false, raw_hooks: false}\n",
    )
    workplace = workspace / "workplace"
    _write(workplace / "configuration.yaml", "logging: {events: true}\n")
    project = workspace / "project"
    _write(project / ".pf/configuration.yaml", "logging: {raw_hooks: true}\n")
    reads = []
    original = YamlConfigStore.read

    def tracked(store):
        reads.append(store.path)
        return original(store)

    monkeypatch.setattr(YamlConfigStore, "read", tracked)
    reader = ProjectConfigurationReader()
    provider = reader.configuration_provider(
        project, workplace, device_config_path=device
    )
    snapshot = provider.snapshot()
    assert len(reads) == 3 and len(set(reads)) == 3
    assert snapshot.config.runtime.metrics.interval_seconds == 17
    assert snapshot.config.runtime.garage_hooks is True
    assert snapshot.config.logging.events is True
    assert snapshot.config.logging.raw_hooks is True
    contexts = [
        ProjectPFConfig.from_dict({"logging": {"events": flag}})
        for flag in (False, True)
    ]
    providers = [
        reader.configuration_provider(
            project, workplace, device_config_path=device, context_overrides=c
        )
        for c in contexts
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        flags = list(
            pool.map(lambda i: providers[i % 2].current().logging.events, range(20))
        )
    assert flags == [bool(i % 2) for i in range(20)]
    pinned = ConfigurationProvider.pinned(snapshot.config, errors=("retained_code",))
    monkeypatch.setattr(
        YamlConfigStore, "read", lambda store: pytest.fail("pinned reread")
    )
    _write(device, "logging: {events: false}\n")
    assert pinned.snapshot(refresh=True).config is snapshot.config
    assert pinned.snapshot().errors == ("retained_code",)


def test_legacy_reader_discovery_is_only_in_explicit_read(workspace, monkeypatch):
    workplace = workspace / "workplace"
    _write(workplace / "configuration.yaml", "logging: {events: false}\n")
    calls = []

    def discover(reader):
        calls.append(reader.project_root)
        return workplace / "workplace.yaml"

    monkeypatch.setattr(ProjectMetadataReader, "workplace_manifest", discover)
    reader = ProjectConfigurationReader()
    bound = reader.configuration_provider(workspace / "project")
    assert not calls and bound.current().logging.events is True
    assert (
        reader.project_configuration(workspace / "project").config.logging.events
        is False
    )
    assert calls == [workspace / "project"]


def test_reader_invalid_and_last_valid_reload(workspace):
    device = _write(workspace / "device.yaml", "logging: {events: invalid}\n")
    provider = build_configuration_provider(device_config_path=device)
    with pytest.raises(ConfigurationError):
        provider.snapshot()
    _write(
        device, "runtime: {metrics: {interval_seconds: 17}}\nlogging: {events: false}\n"
    )
    previous = provider.snapshot()
    _write(device, "logging: {events: invalid}\n")
    broken = provider.snapshot(refresh=True)
    assert broken.config == previous.config and broken.errors
    _write(device, "logging: {events: true}\n")
    assert provider.snapshot(refresh=True).config.logging.events is True


def _cli(device: Path):
    def full(path):
        return ConfigService(YamlConfigStore(path))

    def project(path):
        return ConfigService(
            YamlConfigStore(path, model=ProjectPFConfig), defaults=ProjectPFConfig()
        )

    command = ConfigurationCommand(
        service_factory=full,
        project_service_factory=project,
        flow_root=lambda root: root / ".pf",
        device_config_path=device,
    )
    parser = argparse.ArgumentParser()
    ConfigurationCommandParser(execute=command.execute).register(
        parser.add_subparsers().add_parser
    )
    return parser


def _execute(parser, capsys, *args):
    parsed = parser.parse_args(["config", *args, "--json"])
    code = parsed.func(parsed)
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out)


def test_device_full_crud_and_workplace_payload_compatibility(workspace, capsys):
    device = workspace / "settings/device.yaml"
    parser = _cli(device)
    code, missing = _execute(parser, capsys, "read", "--device")
    assert code == 0 and missing["scope"] == "device" and not missing["exists"]
    assert not device.exists() and "database" not in missing["configuration"]
    code, created = _execute(parser, capsys, "create", "--device")
    assert code == 0
    code, updated = _execute(
        parser,
        capsys,
        "update",
        "--device",
        "--key",
        "runtime.metrics.interval_seconds",
        "--value",
        "17",
        "--if-revision",
        created["revision"],
    )
    assert (
        code == 0
        and updated["configuration"]["runtime"]["metrics"]["interval_seconds"] == 17
    )
    assert (
        _execute(
            parser,
            capsys,
            "update",
            "--device",
            "--key",
            "logging.events",
            "--value",
            "false",
            "--if-revision",
            created["revision"],
        )[0]
        == 3
    )
    assert (
        _execute(
            parser,
            capsys,
            "update",
            "--device",
            "--key",
            "database.driver",
            "--value",
            '"sqlite"',
        )[0]
        == 0
    )
    code, reset = _execute(
        parser, capsys, "delete", "--device", "--key", "database.driver"
    )
    assert code == 0 and "database" not in reset["configuration"]
    code, workplace = _execute(
        parser, capsys, "read", "--workplace", str(workspace / "workplace")
    )
    assert code == 0 and set(workplace) == {
        "kind",
        "exists",
        "revision",
        "configuration",
    }
    assert _execute(parser, capsys, "delete", "--device")[1]["exists"] is False


def test_project_cli_effective_full_provider_and_errors(workspace, capsys):
    device = _write(
        workspace / "device.yaml",
        "runtime: {metrics: {interval_seconds: 17}}\nlogging: {events: false}\n",
    )
    workplace = workspace / "workplace"
    _write(workplace / "configuration.yaml", "logging: {raw_hooks: false}\n")
    parser = _cli(device)
    (workspace / "project/.pf").mkdir(parents=True)
    scope = [
        "--workplace",
        str(workplace),
        "--project-root",
        str(workspace / "project"),
    ]
    code, read = _execute(parser, capsys, "read", *scope, "--key", "logging.events")
    assert code == 0 and read["value"] is False and read["override"] is None
    assert (
        read["effective_configuration"]["runtime"]["metrics"]["interval_seconds"] == 17
    )
    assert _execute(parser, capsys, "create", *scope)[0] == 0
    code, updated = _execute(
        parser, capsys, "update", *scope, "--key", "logging.events", "--value", "true"
    )
    assert code == 0 and updated["effective_configuration"]["logging"]["events"] is True
    assert (
        _execute(parser, capsys, "delete", *scope, "--key", "logging.events")[1][
            "effective_configuration"
        ]["logging"]["events"]
        is False
    )
    assert (
        _execute(
            parser,
            capsys,
            "update",
            *scope,
            "--key",
            "runtime.metrics.interval_seconds",
            "--value",
            "2",
        )[0]
        == 1
    )
    assert (
        _execute(parser, capsys, "read", "--device", "--project-root", str(workspace))[
            0
        ]
        == 1
    )
    with pytest.raises(SystemExit) as error:
        parser.parse_args(["config", "read", "--device", "--workplace", str(workplace)])
    assert error.value.code == 2
    capsys.readouterr()


def test_journals_native_transport_noncreation_and_rollback(workspace):
    driver = RecordingDriver()
    path = workspace / "events.sqlite3"
    events = ProcessEventJournal(driver=driver)
    assert events.count(path) == 0 and not path.exists() and not driver.calls
    event = {
        "event_id": "first",
        "event_type": "passed",
        "subject": "task",
        "data": {"verification_fingerprint": "fixture"},
    }
    assert events.append(path, event, record=False)
    assert not events.append(path, event, record=False)
    assert events.latest_assignment_event(path, "task", {"passed"}) == event
    with ProcessEventJournal.connection(
        path, writable=True, driver=driver
    ) as connection:
        with pytest.raises(RuntimeError), transaction(connection):
            connection.execute(
                "INSERT INTO admissions(event_id,payload_hash) VALUES('rolled-back','hash')"
            )
            raise RuntimeError("rollback")
        assert not connection.in_transaction
        assert (
            connection.execute(
                "SELECT 1 FROM admissions WHERE event_id='rolled-back'"
            ).fetchone()
            is None
        )
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0x50464556
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert all(call[1:3] == (10.0, None) for call in driver.calls)
    assert any(call[3] for call in driver.calls)
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    foreign = workspace / "foreign.sqlite3"
    with driver._connect(foreign) as connection:
        connection.execute("CREATE TABLE foreign_table(value)")
    with pytest.raises(JournalError, match="journal_schema_unrecognized"):
        events.append(foreign, event)


def test_accounting_injection_snapshot_and_backup_destination(workspace):
    driver = RecordingDriver()
    path = workspace / "accounting.sqlite3"
    repository = SQLiteAccountingRepository(path, busy_timeout_ms=50, driver=driver)
    with repository.snapshot() as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == 0x50464143
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    target = workspace / "backup.sqlite3"
    repository.backup(target)
    assert target.exists() and driver.calls[-1] == (target, 5.0, "", False)
    assert all(call[1:3] == (0.05, None) for call in driver.calls[:-1])
    with pytest.raises(FileExistsError):
        repository.backup(target)


def test_full_pinned_consumers_do_not_read_yaml(workspace, monkeypatch):
    pinned = _pinned()
    driver = RecordingDriver()
    seen = []

    def select(config=None):
        assert config is pinned.current().database
        seen.append(pinned.current().runtime.metrics.interval_seconds)
        return driver

    monkeypatch.setattr(DatabaseFactory, "resolve_driver", staticmethod(select))
    monkeypatch.setattr(
        YamlConfigStore, "read", lambda store: pytest.fail("consumer YAML open")
    )
    project = workspace / "project"
    recorder = ProcessEventRecorder(configuration=pinned)
    event = {
        "event_id": "verification",
        "event_type": "passed",
        "subject": "task",
        "data": {"verification_fingerprint": "fixture"},
    }
    assert recorder.admit_process_event(project, event, dispatch=False)
    events = project / ".pf/runtime/events/events.sqlite3"
    assert ProcessEventJournal(driver=driver).count(events) == 0
    readiness = AutomationReadinessService(
        project_root=project,
        has_output_checks=lambda: False,
        output_checks=lambda *args: [],
        has_fingerprint=lambda: False,
        fingerprint=lambda *args: None,
        has_event_paths=lambda: True,
        event_paths=lambda root: (events, None),
        latest_event=lambda *args: None,
        configuration=pinned,
    )
    assert readiness.latest_assignment_event("task", {"passed"}) == event
    kernel = RawIngressKernel(
        workspace, flow_root=project / ".pf", configuration=pinned
    )
    native = NativeAgentEvent(
        "fixture",
        "native",
        "message",
        {"content": "retention"},
        native_event_id="raw-1",
    )
    receipt = kernel.ingest(native)
    assert (
        receipt.accepted and RawHookJournal(driver=driver).count(kernel.database) == 0
    )
    assert list(kernel.records())
    kernel.finish(receipt.raw_event_id, {"status": "done"})
    assert kernel.result(receipt.raw_event_id) == {"status": "done"}
    assert not list(kernel.records())
    assert kernel.ingest(native).deduplicated
    accounting = WorkplaceAccounting(
        workplace=workspace / "workplace",
        project_root=project,
        project_id="project",
        configuration=pinned,
    )
    assert accounting.service() is None
    assert accounting.service(create=True) is not None
    assert accounting.service() is not None
    index = local_search.ResourceSearchIndex(project, {}, configuration=pinned)
    assert index.status()["status"] == "missing"
    assert seen and set(seen) == {17}


def test_consistency_provider_uses_verification_driver(workspace, monkeypatch):
    pinned = _pinned()
    driver = RecordingDriver()
    selected = []
    monkeypatch.setattr(
        DatabaseFactory,
        "resolve_driver",
        staticmethod(lambda config=None: selected.append(config) or driver),
    )
    project = workspace / "project"
    _write(project / ".pf/process-forge.yaml", "project: {id: test}\n")
    _write(
        project / ".pf/runs/run/run.yaml",
        "schema_version: 1\nid: run\ntitle: fixture\nprocess: fixture\nstatus: open\ncreated_at: now\nupdated_at: now\ntasks: []\n",
    )
    _write(project / ".pf/runs/run/task-index.md", "Run status: `open`\n")
    service = RunTaskConsistencyService(workspace, configuration=pinned)
    monkeypatch.setattr(service, "process_definition_exists", lambda *args: True)
    checks = service.validate_run_consistency(
        project, "run", include_runtime_events=True
    )
    assert any(item.message == "runtime run events exist" for item in checks)
    assert selected == [pinned.current().database]
    assert not driver.calls


def test_search_all_native_paths_and_read_noncreation(workspace):
    driver = RecordingDriver()
    project = workspace / "project"
    assert local_search.index_status(project, driver=driver)["status"] == "missing"
    assert not project.exists()
    content = workspace / "docs"
    _write(content / "guide.md", "marker-native-provider")
    snapshot = {
        "snapshot": {"id": "fixture", "checksum": "fixture"},
        "local_search_resources": [
            {
                "id": "docs:guide",
                "content_roots": [str(content)],
                "indexing": {
                    "mode": "fulltext",
                    "sources": [
                        {"path": ".", "mode": "fulltext", "include": ["**/*.md"]}
                    ],
                },
            }
        ],
    }
    index = local_search.ResourceSearchIndex(project, snapshot, driver=driver)
    assert index.refresh()["status"] == "fresh"
    assert index.search(query="marker-native-provider")["total"] == 1
    assert (
        local_search.authorized_coverage(project, snapshot, driver=driver)["status"]
        == "complete"
    )
    assert index.mark_dirty()["status"] == "stale"
    assert index.maintenance_tick()["action"] == "refresh"
    assert index.rebuild()["status"] == "fresh"
    material = local_search.search_material(
        [{"title": "marker", "content": "needle"}],
        "needle",
        10,
        0,
        error=lambda: ValueError,
        driver=driver,
    )
    assert material["total"] == 1
    assert any(call == (":memory:", 5.0, "", False) for call in driver.calls)
    assert any(call[1] == 0.0 and call[3] for call in driver.calls)
    assert any(call[1] == 0.0 and not call[3] for call in driver.calls)


def test_project_cli_reads_each_layer_once(workspace, capsys, monkeypatch):
    device = workspace / "device.yaml"
    workplace = workspace / "workplace"
    project = workspace / "project"
    parser = _cli(device)
    reads = []
    original = YamlConfigStore.read

    def tracked(store):
        reads.append(store.path)
        return original(store)

    monkeypatch.setattr(YamlConfigStore, "read", tracked)
    code, result = _execute(
        parser,
        capsys,
        "read",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
    )
    assert code == 0 and not result["exists"]
    assert len(reads) == len(set(reads)) == 3
    assert not project.exists() and not workplace.exists() and not device.exists()


def test_maintenance_uses_pinned_config_and_legacy_transport(workspace, monkeypatch):
    project, workplace = workspace / "project", workspace / "workplace"
    workplace.mkdir()
    _write(
        project / ".pf/process-forge.yaml",
        "schema_version: 1\nproject: {id: phase-a}\n",
    )
    legacy = _write(
        project / ".pf/runtime/events/events.ndjson",
        '{"event_id":"legacy","event_type":"note","unknown":{"kept":true}}\n',
    )
    source = legacy.read_bytes()
    pinned = _pinned()
    driver = RecordingDriver()
    selected = []
    monkeypatch.setattr(
        DatabaseFactory,
        "resolve_driver",
        staticmethod(lambda config=None: selected.append(config) or driver),
    )
    monkeypatch.setattr(
        YamlConfigStore,
        "read",
        lambda store: pytest.fail("maintenance consumer YAML open"),
    )
    service = JournalMaintenanceService(configuration=pinned)
    assert not selected and not driver.calls
    plan = service.migrate(project, workplace)
    assert not plan["blocked"] and not plan["applied"]
    assert not legacy.with_suffix(".sqlite3").exists()
    result = service.migrate(
        project, workplace, apply=True, evidence_dir=workspace / "evidence"
    )
    assert not result["blocked"] and result["applied"]
    assert legacy.read_bytes() == source
    assert selected == [pinned.current().database] * 2
    assert driver.calls
    assert any(call[0] == "" for call in driver.calls)
    assert all(
        call[1:] == (5.0, "", False) if call[0] == "" else call[1:3] == (10.0, None)
        for call in driver.calls
    )
    assert ProcessEventJournal(driver=driver).get(
        legacy.with_suffix(".sqlite3"), "legacy"
    )["unknown"] == {"kept": True}


def test_replay_raw_reader_uses_derived_driver(workspace, monkeypatch):
    from pf_runtime import session_replay

    project, workplace = workspace / "project", workspace / "workplace"
    pinned = _pinned()
    driver = RecordingDriver()
    selected = []
    monkeypatch.setattr(
        DatabaseFactory,
        "resolve_driver",
        staticmethod(lambda config=None: selected.append(config) or driver),
    )
    monkeypatch.setattr(
        YamlConfigStore, "read", lambda store: pytest.fail("replay consumer YAML open")
    )
    monkeypatch.setattr(session_replay, "resolve_project", lambda *args: project)
    kernel = RawIngressKernel(
        workplace, flow_root=project / ".pf", record_raw=True, driver=driver
    )
    kernel.ingest(
        NativeAgentEvent(
            "codex",
            "codex-hooks",
            "unknown",
            {"unsupported": "fixture"},
            source_session_id="session",
            source_project_ref=str(project),
        )
    )
    initial_connections = len(driver.calls)
    core = type(
        "Core",
        (),
        {
            "locate_flow_root": staticmethod(lambda root: root / ".pf"),
            "write": staticmethod(lambda *args: pytest.fail("unexpected write")),
        },
    )()
    result = session_replay.replay_session_raw_records(
        workplace,
        core,
        session_id="session",
        project_ref=str(project),
        configuration=pinned,
    )
    assert result["status"] == "ok" and result["counts"]["unsupported_mapping"] == 1
    assert selected == [pinned.current().database]
    assert any(
        not call[3] for call in driver.calls[initial_connections:]
    )  # finish() used the same transport.
    assert any(call[3] for call in driver.calls[initial_connections:])


@pytest.mark.parametrize("kind", ["events", "raw", "accounting", "search"])
def test_adopted_legacy_access_uses_exact_pin_and_search_keeps_uuid(workspace, kind):
    from processforge_core.maintenance.backup import SQLiteBackupService
    from processforge_core.maintenance.contracts import (
        MaintenanceError,
        MigrationSafety,
        StorageMigrationContext,
        StoreTarget,
    )
    from processforge_core.maintenance.storage_migration import (
        StorageMigrationHost,
        StorageMigrationService,
        _publish_pin,
        add_store_identity,
    )
    from processforge_core.runtime.execution_admission import (
        ExecutionAdmission,
        registry_file_lock,
    )

    project = workspace / "project"
    _write(project / ".pf/process-forge.yaml", "project: {id: project}\n")
    flow = project / ".pf"
    if kind == "events":
        path = flow / "runtime/events/events.sqlite3"
        with ProcessEventJournal.connection(path, writable=True):
            pass
    elif kind == "raw":
        path = flow / "runtime/agent-events/hooks.sqlite3"
        with RawHookJournal.connection(path, writable=True):
            pass
    elif kind == "accounting":
        path = flow / "data/accounting/accounting.sqlite3"
        SQLiteAccountingRepository(path)
        _write(flow / "data/accounting/identity.json", '{"origin_id":"project"}')
    else:
        path = local_search.index_path(project)
        local_search.build_index(project, {})
    target = StoreTarget(
        kind, path, path.relative_to(flow).as_posix(), "project", "project"
    )
    context = StorageMigrationContext(
        project, None, workspace / "device.yaml", (target,)
    )
    service = StorageMigrationService(
        backup=SQLiteBackupService(),
        admission=ExecutionAdmission(registry_file_lock),
        registry_lock=registry_file_lock,
        safety=lambda context: MigrationSafety(
            "unknown", "fixture", ("not an installed-host proof",)
        ),
    )
    host = StorageMigrationHost(context, service)
    identifier = uuid4().hex
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        add_store_identity(connection, target, identifier)
    _publish_pin(flow, target, identifier, "sha256:" + "a" * 64, "pending")
    if kind == "events":
        with pytest.raises(MaintenanceError, match="storage_resume_required"):
            ProcessEventJournal(storage_host=host).count(path)
    elif kind == "raw":
        with pytest.raises(MaintenanceError, match="storage_resume_required"):
            RawHookJournal(storage_host=host).count(path)
    elif kind == "accounting":
        with pytest.raises(MaintenanceError, match="storage_resume_required"):
            SQLiteAccountingRepository(path, storage_host=host)
    else:
        with pytest.raises(MaintenanceError, match="storage_resume_required"):
            local_search.rebuild_index(project, {}, storage_host=host)
    _publish_pin(flow, target, identifier, "sha256:" + "a" * 64, "ready")
    if kind == "events":
        with ProcessEventJournal.connection(
            path, writable=True, storage_host=host
        ) as connection:
            assert (
                connection.execute("SELECT store_id FROM pf_store_meta").fetchone()[0]
                == identifier
            )
            assert (
                connection.execute("PRAGMA application_id").fetchone()[0] == 0x50464556
            )
        assert ProcessEventJournal(storage_host=host).count(path) == 0
    elif kind == "raw":
        assert RawHookJournal(storage_host=host).count(path) == 0
    elif kind == "accounting":
        with SQLiteAccountingRepository(
            path, storage_host=host
        ).snapshot() as connection:
            assert (
                connection.execute("SELECT store_id FROM pf_store_meta").fetchone()[0]
                == identifier
            )
    else:
        inode = path.stat().st_ino
        local_search.rebuild_index(project, {}, storage_host=host)
        assert path.stat().st_ino == inode
        assert (
            local_search.index_status(project, {}, storage_host=host)["status"]
            == "fresh"
        )
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute("SELECT store_id FROM pf_store_meta").fetchone()[0]
                == identifier
            )
        # Ready UUID does not authorize an unexpected extra domain table.
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE unexpected(value)")
        with pytest.raises(MaintenanceError, match="storage_schema_unrecognized"):
            local_search.rebuild_index(project, {}, storage_host=host)
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute("SELECT store_id FROM pf_store_meta").fetchone()[0]
                == identifier
            )
    with pytest.raises(MaintenanceError, match="storage_pin_conflict"):
        _publish_pin(flow, target, identifier, "sha256:" + "a" * 64, "pending")


def test_configuration_operation_pins_exact_scope_and_restores(workspace, monkeypatch):
    from processforge_core.project.configuration_inputs import configuration_operation

    project = workspace / "project"
    reader = ProjectConfigurationReader()
    reads = []
    original = YamlConfigStore.read

    def tracked(store):
        reads.append(store.path)
        return original(store)

    monkeypatch.setattr(YamlConfigStore, "read", tracked)
    with configuration_operation(project, None) as pinned:
        assert reader.configuration_provider(project) is pinned
        assert build_configuration_provider(project_root=project) is pinned
        assert pinned.snapshot() is pinned.snapshot(refresh=True)
        with configuration_operation(project, None) as nested:
            assert nested is pinned
        other = reader.configuration_provider(workspace / "other")
        assert other is not pinned
    assert reader.configuration_provider(project) is not pinned
    assert reads == [workspace / "device.yaml", project / ".pf/configuration.yaml"]
