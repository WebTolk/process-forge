"""Automatic policy and the native script with real full configuration snapshots."""

from __future__ import annotations

import io
import json
import os
import runpy
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.executions.projection import canonical_json
from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.contracts import (
    MigrationSafety,
    StorageMigrationContext,
    StoreTarget,
)

from .test_migration import Harness, payload
from .test_storage_uuid import StorageHarness

_ROOT = Path(__file__).absolute().parents[2]


def test_actual_host_factory_is_cold_and_defers_before_uuid(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_storage_migration_host
    from processforge_core.database import SQLiteDriver

    provider = ConfigurationProvider.pinned(PFConfig())
    with (
        patch.object(Path, "open", side_effect=AssertionError("constructor read")),
        patch.object(Path, "mkdir", side_effect=AssertionError("constructor mkdir")),
        patch.object(
            SQLiteDriver, "_connect", side_effect=AssertionError("constructor connect")
        ),
        patch("uuid.uuid4", side_effect=AssertionError("constructor UUID")),
    ):
        host = build_storage_migration_host(
            project_root=storage.project,
            workplace_root=None,
            device_config_path=storage.context.device_config_path,
            configuration=provider,
        )
    context = host.context
    assert {target.kind for target in context.targets} == {
        "main",
        "events",
        "raw",
        "search",
    }
    with patch.object(
        host.service, "execution_factory", side_effect=AssertionError("early engine")
    ):
        report = host.service.ensure_ready(context, trigger="first_write")
    main = next(item for item in report["targets"] if item["kind"] == "main")
    assert main["state"] == "deferred" and main["legacy_allowed"] is True
    assert not (storage.flow / "data").exists()
    assert not (storage.flow / "maintenance").exists()


def test_actual_host_inspect_and_legacy_reads_create_no_guard(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_storage_migration_host
    from processforge_core.process_event_journal import ProcessEventJournal

    host = build_storage_migration_host(
        project_root=storage.project,
        workplace_root=None,
        device_config_path=storage.context.device_config_path,
        configuration=ConfigurationProvider.pinned(PFConfig()),
    )
    before = set(storage.project.rglob("*"))
    assert host.service.inspect(host.context)["blocked"] is False
    event_path = storage.flow / "runtime/events/events.sqlite3"
    journal = ProcessEventJournal(storage_host=host)
    assert journal.count(event_path) == 0
    assert set(storage.project.rglob("*")) == before


def test_actual_host_selected_profile_alias_and_unknown_initializer(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_storage_migration_host
    from processforge_core.configuration.database import DatabaseConfig, DatabaseProfile
    from processforge_core.process_event_journal import ProcessEventJournal

    config = PFConfig(
        database=DatabaseConfig(
            {
                "archive": DatabaseProfile(
                    "project", "sqlite", "stores/executions.sqlite", 432
                )
            },
            {"project_main": "archive"},
        )
    )
    host = build_storage_migration_host(
        project_root=storage.project,
        workplace_root=None,
        device_config_path=storage.context.device_config_path,
        configuration=ConfigurationProvider.pinned(config),
    )
    main = next(target for target in host.context.targets if target.kind == "main")
    assert main.target == storage.flow / "stores/executions.sqlite"
    assert host.service.execution_factory is not None
    engine = host.service.execution_factory(host.context, main)
    assert engine.profile_id == "archive"
    assert engine.database.timeout_ms == 432
    assert (
        engine._binding(
            {
                "project_id": "stable-project",
                "store_id": "a" * 32,
                "target_relative_path": main.target_relative_path,
            }
        )["profile_id"]
        == "archive"
    )
    # Unsupported/unsealed hosts retain the original absent-store initializer.
    event_path = storage.flow / "runtime/events/events.sqlite3"
    journal = ProcessEventJournal(storage_host=host)
    journal.append(event_path, {"event_id": "old-supported"}, record=True)
    assert journal.count(event_path) == 1
    assert not (storage.flow / "data/storage-identities.json").exists()


def test_host_refuses_enrollment_mismatch_without_fallback(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_storage_migration_host
    from processforge_core.maintenance.contracts import MaintenanceError

    local = storage.flow / "process-forge.local.yaml"
    local.write_text(
        "workplace:\n  manifest: "
        + (storage.workplace / "workplace.yaml").as_posix()
        + "\n",
        encoding="utf-8",
    )
    host = build_storage_migration_host(
        project_root=storage.project,
        workplace_root=None,
        device_config_path=storage.context.device_config_path,
        configuration=ConfigurationProvider.pinned(PFConfig()),
    )
    with pytest.raises(MaintenanceError, match="storage_enrollment_conflict"):
        _ = host.context


def test_fresh_initialization_uses_alias_and_repairs_same_pending_uuid(
    storage: StorageHarness,
) -> None:
    from processforge_core.configuration.database import DatabaseConfig, DatabaseProfile
    from processforge_core.database import SchemaManager
    from processforge_core.executions.composition import (
        _initialize_fresh_execution_storage,
        _repair_fresh_execution_storage,
        select_execution_storage,
    )
    from processforge_core.maintenance.contracts import MaintenanceError
    from processforge_core.runtime.execution_admission import ExecutionAdmission

    provider = ConfigurationProvider.pinned(
        PFConfig(
            database=DatabaseConfig(
                {"selected": DatabaseProfile("project", "sqlite", "state/main.sqlite")},
                {"project_main": "selected"},
            )
        )
    )
    with ExecutionAdmission().maintenance(storage.project, None):
        with patch.object(
            SchemaManager,
            "initialize",
            side_effect=MaintenanceError("fixture_crash_before_create"),
        ):
            with pytest.raises(MaintenanceError, match="fixture_crash_before_create"):
                _initialize_fresh_execution_storage(
                    storage.project, None, configuration=provider
                )
    binding = json.loads((storage.flow / "data/execution-storage.json").read_bytes())
    assert binding["profile_id"] == "selected"
    assert not (storage.flow / "state/main.sqlite").exists()
    assert _repair_fresh_execution_storage(
        storage.project, None, configuration=provider
    )
    assert (
        json.loads((storage.flow / "data/execution-storage.json").read_bytes())
        == binding
    )
    route = select_execution_storage(storage.project, configuration=provider)
    assert route.repository is not None and route.repository.readiness().ready
    assert route.repository.readiness().generation == 1
    assert _repair_fresh_execution_storage(
        storage.project, None, configuration=provider
    )


def test_nested_operation_inherits_selected_device_without_source_reread(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_configuration_provider
    from processforge_core.configuration.yaml_store import YamlConfigStore
    from processforge_core.project.configuration_inputs import configuration_operation

    device = storage.root / "selected-device.yaml"
    device.write_text(
        "schema_version: 1\nlogging:\n  events: false\n", encoding="utf-8"
    )
    with configuration_operation(
        storage.project, None, device_config_path=device
    ) as pinned:
        with patch.object(
            YamlConfigStore, "read", side_effect=AssertionError("nested source reread")
        ):
            assert build_configuration_provider(project_root=storage.project) is pinned
            with configuration_operation(storage.project, None) as nested:
                assert nested is pinned
                assert nested.current().logging.events is False


@pytest.fixture
def storage() -> StorageHarness:
    return StorageHarness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)


def test_marker_before_binding_closes_legacy_and_native_factory_repairs(
    storage: StorageHarness,
) -> None:
    from types import SimpleNamespace

    from processforge_core.composition import build_storage_migration_host
    from processforge_core.executions.composition import (
        _initialize_fresh_execution_storage,
        select_execution_storage,
    )
    from processforge_core.executions.model import ExecutionError
    from processforge_core.maintenance.journal_scan import _exclusive_bytes
    from processforge_core.runtime.execution_admission import ExecutionAdmission

    provider = ConfigurationProvider.pinned(PFConfig())

    def crash(path: Path, content: bytes) -> None:
        if path.name == "execution-storage.json":
            raise OSError("fixture_marker_before_binding")
        _exclusive_bytes(path, content)

    with ExecutionAdmission().maintenance(storage.project, None):
        with patch(
            "processforge_core.maintenance.journal_scan._exclusive_bytes", crash
        ):
            with pytest.raises(OSError, match="fixture_marker_before_binding"):
                _initialize_fresh_execution_storage(
                    storage.project, None, configuration=provider
                )
    marker = storage.flow / "maintenance/execution-initialization.json"
    original = json.loads(marker.read_bytes())["binding"]
    assert not (storage.flow / "data/execution-storage.json").exists()
    with pytest.raises(ExecutionError, match="execution_storage_not_ready"):
        select_execution_storage(storage.project, configuration=provider)
    host = build_storage_migration_host(
        project_root=storage.project,
        workplace_root=None,
        device_config_path=storage.context.device_config_path,
        configuration=provider,
    )
    refused = host.service.resume(host.context)
    assert refused["blocked"] is True
    assert not any(item.get("legacy_allowed") for item in refused["targets"])
    assert json.loads(marker.read_bytes())["binding"] == original

    # These injected native facts qualify engine policy only, not G1 enrollment.
    def proof(context):
        assert ExecutionAdmission.held(context.project_root, context.workplace_root)
        return "proven", "fixture-generation", ("fixture-native-proof",)

    entry = SimpleNamespace(storage_safety=proof)
    native = SimpleNamespace(
        current_entry=lambda: entry, supports_owned_execution=lambda: True
    )
    with patch.dict(sys.modules, {"pf_native_control": native}):
        repaired = host.service.resume(host.context)
        assert repaired["blocked"] is False, repaired
        assert host.service.resume(host.context)["blocked"] is False
    assert json.loads(marker.read_bytes()) == {
        "schema_version": 1,
        "state": "ready",
        "binding": original,
    }
    assert (
        json.loads((storage.flow / "data/execution-storage.json").read_bytes())
        == original
    )
    route = select_execution_storage(storage.project, configuration=provider)
    assert route.repository is not None
    assert route.repository.readiness().store_id == original["store_id"]
    assert route.repository.readiness().generation == 1


def test_operation_keeps_exact_selector_and_host_without_yaml_reread(
    storage: StorageHarness,
) -> None:
    from processforge_core.configuration.yaml_store import YamlConfigStore
    from processforge_core.project.configuration_inputs import (
        configuration_operation,
        operation_device_path,
        operation_storage_host,
    )

    device = storage.root / "selected.yaml"
    device.write_text(
        "schema_version: 1\nlogging:\n  events: false\n", encoding="utf-8"
    )
    with configuration_operation(
        storage.project, None, device_config_path=device
    ) as pinned:
        with patch.object(
            YamlConfigStore, "read", side_effect=AssertionError("reread")
        ):
            assert pinned.device_path is None
            assert operation_device_path(storage.project, None) == device
            host = operation_storage_host(
                storage.flow / "runtime/events/events.sqlite3"
            )
            assert host is not None and host.context.device_config_path == device
            with configuration_operation(storage.project, None) as nested:
                assert nested is pinned
                assert (
                    operation_storage_host(
                        storage.flow / "runtime/events/events.sqlite3"
                    )
                    is host
                )
                assert not nested.current().logging.events
            assert operation_device_path(storage.root / "other-project", None) is None


def test_domain_safety_revalidates_selected_owner_before_leaf_proof(
    storage: StorageHarness,
) -> None:
    from processforge_core.composition import build_storage_migration_host
    from processforge_core.maintenance.contracts import MaintenanceError

    host = build_storage_migration_host(
        project_root=storage.project,
        workplace_root=None,
        device_config_path=storage.context.device_config_path,
        configuration=ConfigurationProvider.pinned(PFConfig()),
    )
    context = host.context
    (storage.flow / "process-forge.yaml").write_text(
        "project:\n  id: changed-owner\n", encoding="utf-8"
    )
    with pytest.raises(MaintenanceError, match="storage_enrollment_conflict"):
        host.service.safety(context)


def test_project_init_pending_uses_coordinator_before_authoring(
    storage: StorageHarness,
) -> None:
    import importlib.util

    from processforge_core.executions.composition import (
        _initialize_fresh_execution_storage,
    )
    from processforge_core.maintenance.contracts import MaintenanceError
    from processforge_core.runtime.execution_admission import ExecutionAdmission

    with ExecutionAdmission().maintenance(storage.project, None):
        with patch(
            "processforge_core.database.SchemaManager.initialize",
            side_effect=OSError("fixture_crash"),
        ):
            with pytest.raises(OSError):
                _initialize_fresh_execution_storage(
                    storage.project,
                    None,
                    configuration=ConfigurationProvider.pinned(PFConfig()),
                )
    name = "pf_w4_init_policy_fixture"
    spec = importlib.util.spec_from_file_location(name, _ROOT / "tools/processforge.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        with patch.object(
            module,
            "_execute_project_initialization",
            side_effect=AssertionError("premature authoring"),
        ):
            with pytest.raises(MaintenanceError):
                module.execute_project_initialization(
                    {"project_root": storage.project}, {}
                )
    finally:
        sys.modules.pop(name, None)


def test_actual_script_without_injected_factory_is_cold_and_legacy_safe(
    storage: StorageHarness,
) -> None:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    command = [
        sys.executable,
        "-B",
        str(_ROOT / "tools/migrate-storage.py"),
        "--project-root",
        str(storage.project),
        "--device-config",
        str(storage.context.device_config_path),
        "--json",
    ]
    before = set(storage.project.rglob("*"))
    inspected = subprocess.run(
        command,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert inspected.returncode == 0, inspected.stderr
    assert len(inspected.stdout.splitlines()) == 1
    assert json.loads(inspected.stdout)["blocked"] is False
    assert set(storage.project.rglob("*")) == before
    applied = subprocess.run(
        [*command, "--apply"],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert applied.returncode == 1, applied.stderr
    report = json.loads(applied.stdout)
    main = next(item for item in report["targets"] if item["kind"] == "main")
    assert main["state"] == "deferred" and main["legacy_allowed"] is True
    assert not (storage.flow / "data").exists()


def test_cold_coordinator_has_no_io_or_uuid(storage: StorageHarness) -> None:
    with (
        patch.object(Path, "open", side_effect=AssertionError("open")),
        patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")),
        patch.object(migration, "uuid4", side_effect=AssertionError("mint")),
    ):
        migration.StorageMigrationService(
            backup=storage.backup,
            admission=storage.service.admission,
            registry_lock=storage.lock,
            safety=storage.proof,
        )


def test_first_write_policy_and_retry_without_agent_calls(
    storage: StorageHarness,
) -> None:
    storage.create()
    storage.state = "active"
    with patch.object(
        subprocess, "Popen", side_effect=AssertionError("agent/process forbidden")
    ):
        deferred = storage.ensure()
        assert deferred["targets"][0]["legacy_allowed"]
        storage.state = "proven"
        assert storage.ensure()["status"] == "ready"
        storage.state = "unknown"
        # Ready path is UUID/schema validation, without another safety decision.
        calls = storage.proof_calls
        assert storage.ensure()["status"] == "ready"
        assert storage.proof_calls == calls


@pytest.mark.parametrize(
    "safety",
    [
        None,
        True,
        MigrationSafety("proven", "", ()),
        MigrationSafety("proven", "version-only", ()),
    ],
)
def test_flag_empty_or_malformed_proof_cannot_authorize(
    storage: StorageHarness, safety: object
) -> None:
    storage.create()
    with patch.object(storage.service, "safety", return_value=safety):
        assert storage.ensure()["blocked"]
    assert not storage.slot


def test_script_inspect_uses_full_real_provider_once(storage: StorageHarness) -> None:
    storage.create()
    storage.context.device_config_path.write_text(
        "schema_version: 1\nruntime:\n  metrics:\n    interval_seconds: 9\nlogging:\n  events: false\n",
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(_ROOT / "tools/migrate-storage.py"))
    calls = []

    def builder(**kwargs: object) -> ConfigurationProvider:
        calls.append("builder")
        return ConfigurationProvider(device_path=storage.context.device_config_path)

    def factory(**kwargs: object) -> migration.StorageMigrationHost:
        provider = kwargs["configuration"]
        assert isinstance(provider, ConfigurationProvider)
        assert provider.get("runtime.metrics.interval_seconds") == 9
        assert provider.get("logging.events") is False
        with patch.object(Path, "open", side_effect=AssertionError("pinned reread")):
            assert isinstance(provider.current(), PFConfig)
            assert provider.snapshot(refresh=True).config is provider.current()
        calls.append("host")
        return migration.StorageMigrationHost(storage.context, storage.service)

    output = io.StringIO()
    with redirect_stdout(output):
        code = namespace["main"](
            [
                "--project-root",
                str(storage.project),
                "--device-config",
                str(storage.context.device_config_path),
                "--json",
            ],
            configuration_builder=builder,
            host_factory=factory,
        )
    assert code == 0 and calls == ["builder", "host"]
    result = json.loads(output.getvalue())
    assert len(output.getvalue().splitlines()) == 1 and result["status"] == "planned"
    assert not storage.slot
    assert str(storage.root) not in output.getvalue()


@pytest.mark.parametrize("mode", ["--apply", "--resume"])
def test_script_native_policy_has_one_json_no_model(
    storage: StorageHarness, mode: str
) -> None:
    storage.create()
    namespace = runpy.run_path(str(_ROOT / "tools/migrate-storage.py"))
    output = io.StringIO()
    with (
        redirect_stdout(output),
        patch.object(subprocess, "Popen", side_effect=AssertionError("no child agent")),
    ):
        code = namespace["main"](
            ["--project-root", str(storage.project), mode],
            configuration_builder=lambda **kw: ConfigurationProvider(
                device_path=storage.context.device_config_path
            ),
            host_factory=lambda **kw: migration.StorageMigrationHost(
                storage.context, storage.service
            ),
        )
    assert code == 0 and len(output.getvalue().splitlines()) == 1
    assert json.loads(output.getvalue())["status"] == "ready"


def test_script_parser_and_host_errors_are_bounded(storage: StorageHarness) -> None:
    namespace = runpy.run_path(str(_ROOT / "tools/migrate-storage.py"))
    with pytest.raises(SystemExit) as error:
        namespace["main"]([])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        namespace["main"](["--project-root", "relative"])
    assert error.value.code == 2
    output = io.StringIO()
    with redirect_stdout(output):
        code = namespace["main"](
            ["--project-root", str(storage.project)],
            configuration_builder=lambda **kw: ConfigurationProvider.pinned(PFConfig()),
            host_factory=lambda **kw: (_ for _ in ()).throw(
                OSError("secret private path")
            ),
        )
    assert (
        code == 1
        and "secret" not in output.getvalue()
        and str(storage.root) not in output.getvalue()
    )


def test_evidence_escape_refused_before_mutation(storage: StorageHarness) -> None:
    storage.create()
    namespace = runpy.run_path(str(_ROOT / "tools/migrate-storage.py"))
    output = io.StringIO()
    with redirect_stdout(output):
        code = namespace["main"](
            [
                "--project-root",
                str(storage.project),
                "--apply",
                "--evidence-dir",
                str(storage.root / "outside"),
            ],
            configuration_builder=lambda **kw: ConfigurationProvider.pinned(PFConfig()),
            host_factory=lambda **kw: migration.StorageMigrationHost(
                storage.context, storage.service
            ),
        )
    assert (
        code == 1
        and json.loads(output.getvalue())["error"]["code"] == "storage_evidence_unsafe"
    )
    assert not storage.slot


@pytest.mark.parametrize("floor_only", [False, True])
def test_outer_coordinator_calls_actual_execution_engine(floor_only: bool) -> None:
    harness = Harness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)
    source = None if floor_only else harness.status("task", attempt=3)
    original = None if source is None else source.read_bytes()
    if floor_only:
        (harness.flow / "runtime/agent-runs/run/task/attempts/7").mkdir(parents=True)
    target = StoreTarget(
        "main",
        harness.database.target.path,
        "data/pf.sqlite3",
        "project",
        "exact-project",
    )
    context = StorageMigrationContext(
        harness.project, None, harness.project / "device.yaml", (target,)
    )

    def safety(value: StorageMigrationContext) -> MigrationSafety:
        assert value == context and harness.depth == 1
        return MigrationSafety(
            "proven", "host-epoch-1", ("fixture:whole-host-exclusion",)
        )

    service = migration.StorageMigrationService(
        backup=harness.service.backup,
        admission=harness.service.admission,
        registry_lock=harness.lock,
        safety=safety,
        execution=harness.service,
    )
    report = service.ensure_ready(context, trigger="first_write")
    assert report["status"] == "ready", report
    assert harness.repository.readiness().authority == "sql"
    record = harness.repository.load_latest("run", "task")
    if floor_only:
        assert record is None
        assert harness.scalar("SELECT count(*) FROM execution_attempts") == 0
        assert harness.repository.page_history().records == ()
        allocated = harness.repository.allocate_attempt(
            "run",
            "task",
            canonical_json(payload("task", status="ready")),
            generation=1,
        )
        assert allocated.key.attempt == 8
    else:
        assert record is not None and record.key.attempt == 3
        assert source is not None and source.read_bytes() == original
    assert service.resume(context)["status"] == "ready"


def test_public_script_actual_current_factory_result(storage: StorageHarness) -> None:
    """Actual subprocess inspect; host completeness is explicitly an integration gate."""
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(_ROOT / "tools/migrate-storage.py"),
            "--project-root",
            str(storage.project),
            "--device-config",
            str(storage.context.device_config_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in {0, 1}
    assert len(result.stdout.splitlines()) == 1
    report = json.loads(result.stdout)
    assert str(storage.root) not in result.stdout
    if result.returncode == 1:
        assert report["blocked"] and report["error"]["code"] in {
            "storage_host_factory_unavailable",
            "storage_operation_failed",
            "storage_safety_unavailable",
            "storage_activity_unknown",
            "owner_identity_required",
        }


def test_script_rejects_snapshot_errors_before_host_factory(
    storage: StorageHarness,
) -> None:
    namespace = runpy.run_path(str(_ROOT / "tools/migrate-storage.py"))
    output = io.StringIO()

    def forbidden_factory(**kwargs: object) -> migration.StorageMigrationHost:
        pytest.fail("invalid configuration reached the migration host")

    with redirect_stdout(output):
        code = namespace["main"](
            ["--project-root", str(storage.project), "--apply"],
            configuration_builder=lambda **kwargs: ConfigurationProvider.pinned(
                PFConfig(), errors=("configuration_invalid",)
            ),
            host_factory=forbidden_factory,
        )
    assert code == 1
    assert len(output.getvalue().splitlines()) == 1
    assert (
        json.loads(output.getvalue())["error"]["code"]
        == "storage_configuration_invalid"
    )
    assert not storage.slot
