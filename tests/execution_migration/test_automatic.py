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
from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.contracts import (
    MigrationSafety,
    StorageMigrationContext,
    StoreTarget,
)

from .test_migration import Harness
from .test_storage_uuid import StorageHarness

_ROOT = Path(__file__).absolute().parents[2]


@pytest.fixture
def storage() -> StorageHarness:
    return StorageHarness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)


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


def test_outer_coordinator_calls_actual_execution_engine() -> None:
    harness = Harness(Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex)
    source = harness.status("task", attempt=3)
    original = source.read_bytes()
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
    assert record is not None and record.key.attempt == 3
    assert source.read_bytes() == original
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
