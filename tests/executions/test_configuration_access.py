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
    assert driver.calls and all(call[1:3] == (10.0, None) for call in driver.calls)
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
