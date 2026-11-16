"""Fresh engine tests use explicit capability stubs, not native qualification."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pf_native_control as native
import pytest

from processforge_core.composition import build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.database import SchemaManager
from processforge_core.executions.composition import select_execution_storage
from processforge_core.maintenance import fresh_project as fresh
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.storage_migration import _slot
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import adapter_identity_access


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(native, "supports_owned_execution", lambda: True)
    root = tmp_path / "project"
    flow = root / ".pf"
    root.mkdir()
    assert fresh.create_project_storage_root(root)
    (flow / "process-forge.yaml").write_text("project:\n  id: fresh-owner\n")
    return root


def provider():
    return ConfigurationProvider.pinned(PFConfig())


def host_for(project, workplace=None):
    return build_storage_migration_host(
        project_root=project,
        workplace_root=workplace,
        device_config_path=project.parent / "device.yaml",
        configuration=provider(),
    )


def target_for(host, kind, scope="project"):
    return next(t for t in host.context.targets if t.kind == kind and t.scope == scope)


def initialize(project, workplace=None):
    assert fresh.initialize_project_storage(
        project, workplace, configuration=provider()
    )


def test_ready_before_first_domain_write_and_lazy_raw(project):
    initialize(project)
    host = host_for(project)
    events, raw = target_for(host, "events"), target_for(host, "raw")
    receipt = fresh._receipt(project)
    assert receipt["state"] == "ready"
    assert _slot(project / ".pf", events)["state"] == "ready"
    assert not raw.target.exists()
    assert _slot(project / ".pf", raw) is None
    expected_raw = fresh._domain(receipt, raw)["store_id"]
    with patch.object(host.service, "safety", side_effect=AssertionError("old proof")):
        with ProcessEventJournal.connection(
            events.target, writable=True, storage_host=host
        ) as db:
            assert db.execute("SELECT COUNT(*) FROM admissions").fetchone()[0] == 0
            assert _slot(project / ".pf", events)["state"] == "ready"
        with RawHookJournal.connection(raw.target, writable=True, storage_host=host):
            assert _slot(project / ".pf", raw)["state"] == "ready"
    assert _slot(project / ".pf", raw)["store_id"] == expected_raw
    assert (
        select_execution_storage(project, configuration=provider()).repository
        is not None
    )


@pytest.mark.parametrize("boundary", ["before_schema", "after_schema", "before_ready"])
def test_domain_interruption_preserves_uuid_and_blocks_read(project, boundary):
    host = host_for(project)
    events = target_for(host, "events")
    real_initialize = fresh._initialize_domain
    real_publish = fresh._publish_pin

    def interrupted(*args):
        if boundary == "after_schema":
            real_initialize(*args)
        raise RuntimeError("interrupted")

    def publish(root, target, store_id, checksum, state):
        if state == "ready":
            raise RuntimeError("interrupted")
        real_publish(root, target, store_id, checksum, state)

    with patch.object(
        fresh,
        "_publish_pin" if boundary == "before_ready" else "_initialize_domain",
        side_effect=publish if boundary == "before_ready" else interrupted,
    ):
        with pytest.raises(RuntimeError, match="interrupted"):
            initialize(project)
    slot = _slot(project / ".pf", events)
    assert slot["state"] == "pending"
    with pytest.raises(MaintenanceError, match="storage_resume_required"):
        with adapter_identity_access(events.target, host):
            pytest.fail("pending read admitted")
    initialize(project)
    assert _slot(project / ".pf", events)["store_id"] == slot["store_id"]
    assert _slot(project / ".pf", events)["state"] == "ready"


def test_execution_interruption_recovers_recorded_binding(project):
    with patch.object(
        SchemaManager, "initialize", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError, match="interrupted"):
            initialize(project)
    path = project / ".pf/data/execution-storage.json"
    binding = json.loads(path.read_bytes())
    initialize(project)
    assert json.loads(path.read_bytes()) == binding


@pytest.mark.parametrize("kind", ["events", "raw"])
def test_ready_missing_store_never_reminted(project, kind):
    initialize(project)
    host = host_for(project)
    target = target_for(host, kind)
    with fresh.identity_access(host, target):
        pass
    before = _slot(project / ".pf", target)
    target.target.unlink()
    with pytest.raises(MaintenanceError, match="storage_identity_conflict"):
        with adapter_identity_access(target.target, host, writable=True):
            pytest.fail("missing ready store recreated")
    assert not target.target.exists()
    assert _slot(project / ".pf", target) == before


def test_pending_rejects_foreign_domain_without_relabeling(project):
    with patch.object(
        fresh, "_initialize_domain", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError):
            initialize(project)
    host = host_for(project)
    target = target_for(host, "events")
    from .test_storage_uuid import create_legacy

    create_legacy(target.target, "events")
    before = target.target.read_bytes()
    with pytest.raises(MaintenanceError, match="storage_identity_conflict"):
        initialize(project)
    assert target.target.read_bytes() == before
    assert _slot(project / ".pf", target)["state"] == "pending"


def test_unknown_existing_root_is_not_fresh(tmp_path):
    root = tmp_path / "old"
    (root / ".pf").mkdir(parents=True)
    assert (
        fresh.initialize_project_storage(root, None, configuration=provider()) is False
    )
    assert list((root / ".pf").iterdir()) == []


def test_capability_failure_publishes_no_authority(tmp_path, monkeypatch):
    root = tmp_path / "unsupported"
    (root / ".pf").mkdir(parents=True)
    monkeypatch.setattr(native, "supports_owned_execution", lambda: False)
    with pytest.raises(MaintenanceError, match="storage_fresh_capability_required"):
        fresh.create_project_storage_root(root)
    assert not (root / ".pf" / fresh.RECEIPT).exists()


@pytest.mark.parametrize("change", ["owner", "physical", "workplace"])
def test_receipt_recovery_rejects_identity_and_routing_changes(project, change):
    initialize(project)
    if change == "owner":
        (project / ".pf/process-forge.yaml").write_text("project:\n  id: other\n")
    elif change == "physical":
        value = fresh._receipt(project)
        value["root_identity"][1] += 1
        (project / ".pf" / fresh.RECEIPT).write_text(json.dumps(value))
    workplace = project.parent / "workplace" if change == "workplace" else None
    if workplace:
        workplace.mkdir()
        (workplace / "workplace.yaml").write_text("workplace:\n  id: existing\n")
    with pytest.raises(MaintenanceError, match="storage_fresh"):
        initialize(project, workplace)


def test_workplace_search_does_not_inherit_fresh_project_authority(project):
    workplace = project.parent / "workplace"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text("workplace:\n  id: existing\n")
    initialize(project, workplace)
    host = host_for(project, workplace)
    search = target_for(host, "search", "workplace")
    assert not fresh.owns_target(host, search)
    with pytest.raises(MaintenanceError, match="storage_activity_unknown"):
        with adapter_identity_access(search.target, host, writable=True):
            pytest.fail("workplace inherited fresh project authority")
    assert not search.target.exists()
    assert _slot(workplace, search) is None


def test_lazy_project_search_has_ready_uuid_before_use(project):
    initialize(project)
    host = host_for(project)
    target = target_for(host, "search")
    assert not target.target.exists()
    with adapter_identity_access(target.target, host, writable=True) as identity:
        assert identity[1] == _slot(project / ".pf", target)["store_id"]
        assert _slot(project / ".pf", target)["state"] == "ready"


def test_existing_and_forced_roots_never_receive_creation_authority(project):
    (project / ".pf" / fresh.RECEIPT).unlink()
    assert fresh.create_project_storage_root(project) is False
    assert fresh._receipt(project) is None


def test_lazy_pending_resume_uses_same_uuid_without_old_writer_proof(project):
    initialize(project)
    host = host_for(project)
    target = target_for(host, "raw")
    with patch.object(
        fresh, "_initialize_domain", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError):
            with adapter_identity_access(target.target, host, writable=True):
                pass
    before = _slot(project / ".pf", target)
    from dataclasses import replace

    context = replace(host.context, targets=(target,))
    with patch.object(host.service, "safety", side_effect=AssertionError("old proof")):
        result = host.service.resume(context)
    assert result["status"] == "ready"
    assert _slot(project / ".pf", target)["store_id"] == before["store_id"]


def test_native_host_coordinator_repairs_fresh_execution_without_old_proof(project):
    with patch.object(
        SchemaManager, "initialize", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError):
            initialize(project)
    host = host_for(project)
    before = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
    with patch.object(host.service, "safety", side_effect=AssertionError("old proof")):
        report = host.service.resume(host.context)
    assert report["status"] == "ready", report
    assert (
        json.loads((project / ".pf/data/execution-storage.json").read_bytes()) == before
    )


def test_cli_initializes_sql_journals_before_first_onboarding_event(
    tmp_path, monkeypatch
):
    import importlib.util
    import sys

    root = tmp_path / "new"
    root.mkdir()
    source = Path(__file__).resolve().parents[2]
    name = "fresh_project_cli_fixture"
    spec = importlib.util.spec_from_file_location(
        name, source / "tools/processforge.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(native, "supports_owned_execution", lambda: True)
    monkeypatch.setattr(
        module.project_initialization,
        "apply_agent_entry",
        lambda *args: {"status": "complete", "agent_entry": {}},
    )
    monkeypatch.setattr(
        module, "build_configuration_provider", lambda **kwargs: provider()
    )

    def first_event(project, event, **kwargs):
        assert event == "project.onboarding.started"
        host = host_for(project)
        target = target_for(host, "events")
        assert fresh._receipt(project)["state"] == "ready"
        assert _slot(project / ".pf", target)["state"] == "ready"
        assert (
            select_execution_storage(project, configuration=provider()).repository
            is not None
        )
        raise RuntimeError("first event reached after readiness")

    monkeypatch.setattr(
        module._process_event_recorder, "emit_process_event", first_event
    )
    with pytest.raises(RuntimeError, match="first event reached after readiness"):
        module.execute_project_initialization(
            {"project_root": root, "agent_entry_plan": {"files": []}},
            {root / ".pf/process-forge.yaml": "project:\n  id: fresh-owner\n"},
        )


@pytest.mark.parametrize("force", [False, True])
def test_cli_existing_root_refuses_before_authoring(tmp_path, monkeypatch, force):
    import importlib.util
    import sys

    root = tmp_path / "existing"
    (root / ".pf").mkdir(parents=True)
    source = Path(__file__).resolve().parents[2]
    name = "existing_project_cli_fixture"
    spec = importlib.util.spec_from_file_location(
        name, source / "tools/processforge.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(native, "supports_owned_execution", lambda: True)
    monkeypatch.setattr(
        module,
        "_storage_first_write",
        lambda *args: (_ for _ in ()).throw(MaintenanceError("migration_required")),
    )
    monkeypatch.setattr(
        module,
        "_execute_project_initialization",
        lambda *args: pytest.fail("unqualified authoring"),
    )
    with pytest.raises(MaintenanceError, match="migration_required"):
        module.execute_project_initialization(
            {"project_root": root, "force": force}, {}
        )
    assert fresh._receipt(root) is None


@pytest.mark.parametrize("kind", ["events", "raw", "search"])
@pytest.mark.parametrize("operation_selected", [False, True])
@pytest.mark.parametrize(
    "boundary", ["main_pending", "receipt_pending", "main_missing", "main_sql_pending"]
)
def test_ordinary_domain_requires_project_and_main_ready(
    project, kind, operation_selected, boundary
):
    from contextlib import nullcontext

    from processforge_core.project.configuration_inputs import configuration_operation

    if boundary == "main_pending":
        with patch.object(
            SchemaManager, "initialize", side_effect=RuntimeError("stop")
        ):
            with pytest.raises(RuntimeError):
                initialize(project)
    elif boundary == "receipt_pending":
        with patch.object(
            fresh, "_initialize_domain", side_effect=RuntimeError("stop")
        ):
            with pytest.raises(RuntimeError):
                initialize(project)
    else:
        initialize(project)
        main = target_for(host_for(project), "main").target
        if boundary == "main_missing":
            main.unlink()
        else:
            with closing(sqlite3.connect(main)) as db:
                db.execute("UPDATE execution_state SET readiness='importing'")
                db.commit()
    host = host_for(project)
    target = target_for(host, kind)
    main = target_for(host, "main").target

    def snapshot():
        # SQLite read-only main validation can create shared-memory read marks
        # and an empty WAL. Preserve every domain byte, pin, receipt and UUID.
        result = {}
        for path in project.rglob("*"):
            if not path.is_file() or path.name.endswith((".lock", ".guard")):
                continue
            if path == Path(str(main) + "-shm"):
                continue
            raw = path.read_bytes()
            if path == Path(str(main) + "-wal") and not raw:
                continue
            result[path.relative_to(project)] = raw
        return result

    before = snapshot()
    scope = (
        configuration_operation(
            project,
            None,
            configuration=provider(),
            device_config_path=project.parent / "device.yaml",
        )
        if operation_selected
        else nullcontext()
    )
    selected = None if operation_selected else host
    with scope:
        with pytest.raises(Exception) as error:
            if kind == "search":
                with adapter_identity_access(target.target, selected, writable=True):
                    pytest.fail("ordinary search admitted before readiness")
            else:
                journal = ProcessEventJournal if kind == "events" else RawHookJournal
                with journal.connection(
                    target.target, writable=True, storage_host=selected
                ):
                    pytest.fail("ordinary journal admitted before readiness")
    assert getattr(error.value, "code", None) in {
        "execution_storage_not_ready",
        "database_missing",
    }
    assert snapshot() == before


@pytest.mark.parametrize("kind", ["events", "raw", "search"])
@pytest.mark.parametrize("recovery", [False, True])
def test_pending_corruption_is_typed_and_preserves_bytes(project, kind, recovery):
    from dataclasses import replace

    from processforge_core.database import DatabaseError

    if kind != "events":
        initialize(project)
    host = host_for(project)
    target = target_for(host, kind)
    with patch.object(fresh, "_initialize_domain", side_effect=RuntimeError("stop")):
        with pytest.raises(RuntimeError):
            if kind == "events":
                initialize(project)
            else:
                with adapter_identity_access(target.target, host, writable=True):
                    pass
    target.target.parent.mkdir(parents=True, exist_ok=True)
    target.target.write_bytes(b"corrupt pending database" * 100)
    before = target.target.read_bytes()
    pin = _slot(project / ".pf", target)
    if recovery:
        result = host.service.resume(replace(host.context, targets=(target,)))
        assert result["error"]["code"] == "database_corrupt"
    else:
        with pytest.raises(DatabaseError) as error:
            if kind == "events":
                initialize(project)
            else:
                with adapter_identity_access(target.target, host, writable=True):
                    pass
        assert error.value.code == "database_corrupt"
        assert isinstance(error.value.__cause__, sqlite3.DatabaseError)
    assert target.target.read_bytes() == before
    assert _slot(project / ".pf", target) == pin


@pytest.mark.parametrize("kind", ["events", "raw", "search"])
@pytest.mark.parametrize("operation_selected", [False, True])
def test_main_readiness_uses_exact_alias_and_pinned_configuration(
    project, kind, operation_selected
):
    from contextlib import nullcontext

    from processforge_core.configuration.database import DatabaseConfig, DatabaseProfile
    from processforge_core.project.configuration_inputs import (
        ProjectConfigurationReader,
        configuration_operation,
    )

    def configured(alias):
        return ConfigurationProvider.pinned(
            PFConfig(
                database=DatabaseConfig(
                    profiles={
                        alias: DatabaseProfile(
                            "project", "sqlite", "data/custom.sqlite3"
                        )
                    },
                    defaults={"project_main": alias},
                )
            )
        )

    selected = configured("chosen")
    assert fresh.initialize_project_storage(project, None, configuration=selected)
    target = target_for(host_for(project), kind)
    device = project.parent / "unused-device.yaml"

    def access(configuration):
        host = build_storage_migration_host(
            project_root=project,
            workplace_root=None,
            device_config_path=device,
            configuration=configuration,
        )
        scope = (
            configuration_operation(
                project, None, configuration=configuration, device_config_path=device
            )
            if operation_selected
            else nullcontext()
        )
        with scope:
            with adapter_identity_access(
                target.target, None if operation_selected else host, writable=True
            ):
                pass

    before = {
        p.relative_to(project): p.read_bytes()
        for p in project.rglob("*")
        if p.is_file() and not p.name.endswith((".lock", ".guard"))
    }
    with patch.object(
        ProjectConfigurationReader,
        "configuration_provider",
        side_effect=AssertionError("configuration rediscovered"),
    ):
        with pytest.raises(MaintenanceError, match="execution_binding_conflict"):
            access(configured("different-alias"))
        after = {
            p.relative_to(project): p.read_bytes()
            for p in project.rglob("*")
            if p.is_file() and not p.name.endswith((".lock", ".guard"))
        }
        assert after == before
        access(selected)
    slot = _slot(project / ".pf", target)
    receipt = fresh._receipt(project)
    assert slot is not None and receipt is not None
    assert slot["store_id"] == fresh._domain(receipt, target)["store_id"]
    assert not (project / ".pf/data/processforge.sqlite3").exists()


@pytest.mark.parametrize("kind", ["events", "raw", "search"])
@pytest.mark.parametrize(
    "fault", ["connect", "os_connect", "ddl", "rollback_close", "close"]
)
@pytest.mark.parametrize("recovery", [False, True])
def test_initializer_storage_failures_keep_pending_identity(
    project, kind, fault, recovery
):
    from dataclasses import replace

    from processforge_core.database import DatabaseError, SQLiteDriver

    if kind != "events":
        initialize(project)
    host = host_for(project)
    target = target_for(host, kind)
    with patch.object(fresh, "_initialize_domain", side_effect=RuntimeError("stop")):
        with pytest.raises(RuntimeError):
            if kind == "events":
                initialize(project)
            else:
                with adapter_identity_access(target.target, host, writable=True):
                    pass
    pin = _slot(project / ".pf", target)
    assert pin is not None
    assert pin["state"] == "pending"
    real_connect = SQLiteDriver._connect
    primary = sqlite3.OperationalError("private diagnostic")
    cleanup = sqlite3.OperationalError("private cleanup")
    calls = []

    class FaultConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("CREATE TABLE") and fault in {"ddl", "rollback_close"}:
                calls.append("ddl")
                # Force a real partial transaction, then fail.
                super().execute("CREATE TABLE partial_schema(value TEXT)")
                raise primary
            if sql == "ROLLBACK" and fault == "rollback_close":
                calls.append("rollback")
                raise cleanup
            return super().execute(sql, *args, **kwargs)

        def close(self):
            super().close()
            if fault in {"close", "rollback_close"}:
                calls.append("close")
                raise cleanup

    def connect(driver, database, **kwargs):
        if str(database) not in {
            str(target.target),
            target.target.as_uri() + "?mode=ro",
        }:
            return real_connect(driver, database, **kwargs)
        calls.append("connect")
        if fault == "connect":
            raise primary
        if fault == "os_connect":
            raise PermissionError(13, "private location")
        return sqlite3.connect(database, factory=FaultConnection, **kwargs)

    with patch.object(SQLiteDriver, "_connect", connect):
        if recovery:
            result = host.service.resume(replace(host.context, targets=(target,)))
            assert result["error"]["code"] == "database_io_failed", result
        else:
            with pytest.raises(DatabaseError) as error:
                if kind == "events":
                    initialize(project)
                else:
                    with adapter_identity_access(target.target, host, writable=True):
                        pass
            assert error.value.code == "database_io_failed"
            assert str(error.value) == "database_io_failed"
            causes = []
            current: BaseException | None = error.value
            while current is not None:
                causes.append(current)
                current = current.__cause__
            if fault in {"ddl", "rollback_close", "connect"}:
                assert primary in causes
            else:
                assert isinstance(causes[-1], (OSError, sqlite3.Error))
            if fault == "rollback_close":
                notes = [
                    note for cause in causes for note in getattr(cause, "__notes__", ())
                ]
                assert any("rollback_failed" in note for note in notes)
                assert any("close_failed" in note for note in notes)
    assert calls
    if fault == "rollback_close":
        assert "rollback" in calls and "close" in calls
    assert _slot(project / ".pf", target) == pin
    if target.target.exists() and fault != "close":
        with closing(sqlite3.connect(target.target)) as db:
            assert db.execute("SELECT name FROM sqlite_schema").fetchall() == []
    # The supported recovery path reuses the planned UUID after the fault clears.
    result = host.service.resume(replace(host.context, targets=(target,)))
    assert result["status"] == "ready", result
    final_pin = _slot(project / ".pf", target)
    assert final_pin is not None
    assert final_pin["store_id"] == pin["store_id"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", []),
        ("domains", 9),
        ("project_id", 9),
        ("workplace", {}),
        ("root_identity", [True, True]),
    ],
)
@pytest.mark.parametrize("entry", ["initializer", "ordinary"])
def test_malformed_receipt_fields_refuse_with_typed_error(project, field, value, entry):
    initialize(project)
    host = host_for(project)
    target = target_for(host, "raw")
    receipt_path = project / ".pf" / fresh.RECEIPT
    document = fresh._receipt(project)
    document[field] = value
    receipt_path.write_text(json.dumps(document), encoding="utf-8")

    def snapshot():
        return {
            p.relative_to(project): p.read_bytes()
            for p in project.rglob("*")
            if p.is_file()
        }

    before = snapshot()
    with pytest.raises(MaintenanceError, match="storage_fresh_receipt_invalid"):
        if entry == "initializer":
            initialize(project)
        else:
            with adapter_identity_access(target.target, host, writable=True):
                pytest.fail("malformed receipt admitted")
    assert snapshot() == before
