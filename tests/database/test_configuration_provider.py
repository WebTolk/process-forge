"""Full application layering, byte presence, refresh and request isolation."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from processforge_core.configuration import (
    ConfigService,
    ConfigurationProvider,
    ConfigurationResolver,
    DatabaseConfig,
    DeviceConfigurationSource,
    InvalidConfiguration,
    PFConfig,
    ProjectPFConfig,
)
from processforge_core.configuration.yaml_store import YamlConfigStore
from processforge_core.database import DatabaseFactory

from . import isolated_path
from .test_profiles import MemoryStore, section

tmp_path = isolated_path


def write(path, value):
    staged = path.with_suffix(".staged")
    staged.write_text(json.dumps(value), encoding="utf-8")
    os.replace(staged, path)
    return path


def test_full_layers_presence_defaults_false_and_null(tmp_path):
    device = write(
        tmp_path / "device.yaml",
        {
            "runtime": {
                "metrics": {"interval_seconds": 23},
                "garage_hooks": True,
                "temporary_files": {"mode": "off", "max_age_hours": 99},
            },
            "logging": {"raw_hooks": False, "events": False},
            "database": {"driver": "sqlite"},
        },
    )
    work = write(
        tmp_path / "work.yaml",
        {"runtime": {"garage_hooks": False}, "logging": {"events": True}},
    )
    project = write(
        tmp_path / "project.yaml",
        {
            "runtime": {"temporary_files": {"max_age_hours": 168}},
            "logging": {"raw_hooks": None},
        },
    )
    context = ProjectPFConfig.from_dict(
        {
            "logging": {"events": False},
            "runtime": {"temporary_files": {"mode": "notify"}},
        }
    )
    provider = ConfigurationProvider(
        device_path=device,
        workplace_path=work,
        project_path=project,
        context_overrides=context,
    )
    result = provider.snapshot()
    assert result.workplace.explicit_keys == frozenset(
        {"runtime.garage_hooks", "logging.events"}
    )
    assert result.device.config.runtime.metrics.interval_seconds == 23
    assert result.config.runtime.metrics.interval_seconds == 23
    assert result.config.runtime.garage_hooks is False
    assert result.config.runtime.temporary_files.mode == "notify"
    assert result.config.runtime.temporary_files.max_age_hours == 168
    assert (
        result.config.logging.raw_hooks is False
        and result.config.logging.events is False
    )
    assert provider.get("database.driver") == "sqlite"
    assert result.context_overrides is context


def test_profile_presence_is_atomic_and_disjoint_merge(tmp_path):
    device = write(tmp_path / "device.yaml", {"database": section("workplace", "dev")})
    work = write(tmp_path / "work.yaml", {"database": section("project", "work")})
    project = write(tmp_path / "project.yaml", {"database": section("project", "proj")})
    provider = ConfigurationProvider(
        device_path=device, workplace_path=work, project_path=project
    )
    result = provider.snapshot()
    assert result.workplace.explicit_keys == frozenset(
        {"database.profiles.work", "database.defaults.project_main"}
    )
    assert set(result.config.database.profiles) == {"dev", "work", "proj"}
    assert result.config.database.defaults == {
        "workplace_main": "dev",
        "project_main": "proj",
    }
    write(work, {"database": section("workplace", "dev")})
    with pytest.raises(InvalidConfiguration, match="database_profile_invalid"):
        provider.snapshot()


def test_missing_cold_and_pinned_no_io(tmp_path, monkeypatch):
    target = tmp_path / "absent" / "device.yaml"

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    with monkeypatch.context() as guard:
        guard.setattr(Path, "lstat", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(Path, "mkdir", forbidden)
        guard.setattr(DatabaseFactory, "resolve_driver", forbidden)
        provider = ConfigurationProvider(device_path=target)
        assert provider.device_path == target
    first = provider.snapshot()
    assert first.config == PFConfig() and not first.errors
    assert not first.device.exists and not first.device.explicit_keys
    assert "database" not in first.config.to_dict()
    assert not target.parent.exists()
    pinned = ConfigurationProvider.pinned(first.config, errors=("diagnostic",))
    snapshot = pinned.snapshot()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "lstat", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(DeviceConfigurationSource, "default_path", forbidden)
        assert pinned.snapshot(refresh=True) is snapshot
        assert pinned.current() is first.config
        assert pinned.get("database.driver") == "sqlite"
        assert snapshot.errors == ("diagnostic",)
    with pytest.raises(FrozenInstanceError):
        provider.project_path = tmp_path


def test_same_read_presence_and_cache_refresh(tmp_path, monkeypatch):
    device = write(tmp_path / "device.yaml", {"logging": {"events": False}})
    work = write(tmp_path / "work.yaml", {"logging": {"raw_hooks": False}})
    provider = ConfigurationProvider(device_path=device, workplace_path=work)
    original = YamlConfigStore._raw
    reads = []

    def tracked(store):
        reads.append(store.path)
        return original(store)

    monkeypatch.setattr(YamlConfigStore, "_raw", tracked)
    first = provider.snapshot()
    assert reads == [device, work]
    pinned = ConfigurationProvider.pinned(first.config)
    provider.snapshot()
    assert reads == [device, work]
    provider.snapshot(refresh=True)
    assert reads == [device, work, device, work]
    work.write_text("logging: {raw_hooks: invalid}", encoding="utf-8")
    invalid = provider.snapshot()
    assert invalid.errors == ("configuration_logging_invalid",)
    assert invalid.workplace == first.workplace
    assert invalid.config == first.config
    write(work, {"logging": {"events": True}})
    last = provider.snapshot()
    assert not last.errors
    assert last.config.logging.events is True and last.config.logging.raw_hooks is True
    assert pinned.current() is first.config
    assert pinned.current().logging.events is False


def test_first_invalid_and_merge_errors_propagate(tmp_path):
    invalid = write(
        tmp_path / "invalid.yaml", {"runtime": {"metrics": {"interval_seconds": 0}}}
    )
    with pytest.raises(InvalidConfiguration, match="configuration_interval_invalid"):
        ConfigurationProvider(device_path=invalid).snapshot()
    with pytest.raises(InvalidConfiguration):
        ProjectPFConfig.from_dict({"runtime": {"metrics": {"interval_seconds": 20}}})
    with pytest.raises(
        InvalidConfiguration, match="configuration_project_model_required"
    ):
        ConfigurationProvider(device_path=invalid, context_overrides={})
    with pytest.raises(InvalidConfiguration):
        ProjectPFConfig.from_dict({"database": section("workplace", "bad")})


def test_legacy_positional_resolver_builtin_and_standalone(tmp_path):
    base = write(
        tmp_path / "base.yaml", {"runtime": {"metrics": {"interval_seconds": 40}}}
    )
    project = write(tmp_path / "project.yaml", {"logging": {"events": False}})
    resolver = ConfigurationResolver()
    assert resolver.resolve(base, project).config.runtime.metrics.interval_seconds == 40
    assert resolver.resolve(None, project).config.runtime.metrics.interval_seconds == 10
    assert resolver.resolve(None, None).config == PFConfig()
    assert (
        ConfigurationProvider(device_path=base).get("runtime.metrics.interval_seconds")
        == 40
    )


def test_shared_resolver_two_workplaces_contexts_threads_and_pins(tmp_path):
    device = write(
        tmp_path / "device.yaml",
        {
            "runtime": {"metrics": {"interval_seconds": 34}},
            "logging": {"events": False},
        },
    )
    work1 = write(
        tmp_path / "w1.yaml", {"runtime": {"temporary_files": {"mode": "off"}}}
    )
    work2 = write(tmp_path / "w2.yaml", {"logging": {"events": True}})
    project = write(tmp_path / "project.yaml", {})
    resolver = ConfigurationResolver(max_entries=3)

    def task(index):
        context = ProjectPFConfig.from_dict(
            {"runtime": {"temporary_files": {"max_age_hours": index + 1}}}
        )
        provider = ConfigurationProvider(
            device_path=device,
            workplace_path=work1 if index % 2 else work2,
            project_path=project,
            context_overrides=context,
            resolver=resolver,
        )
        source = provider.snapshot()
        pinned = ConfigurationProvider.pinned(source.config, errors=source.errors)
        assert pinned.get("runtime.temporary_files.max_age_hours") == index + 1
        assert pinned.get("runtime.metrics.interval_seconds") == 34
        assert pinned.get("logging.events") is (not index % 2)
        assert pinned.get("runtime.temporary_files.mode") == (
            "off" if index % 2 else "notify"
        )
        return pinned

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(task, range(40)))
    write(device, {"runtime": {"metrics": {"interval_seconds": 60}}})
    assert all(p.get("runtime.metrics.interval_seconds") == 34 for p in results)
    assert (
        ConfigurationProvider(device_path=device).get(
            "runtime.metrics.interval_seconds"
        )
        == 60
    )


@pytest.mark.parametrize("model", [PFConfig, ProjectPFConfig])
def test_selector_update_reset_preserves_profiles_and_absence(model):
    absent = model()
    assert absent.get("database.driver") == ("sqlite" if model is PFConfig else None)
    selected = absent.with_changes({"database.driver": "sqlite"})
    assert selected.database.driver == "sqlite"
    assert "database" not in selected.with_changes({"database.driver": None}).to_dict()
    config = model.from_dict({"database": section()})
    service = ConfigService(MemoryStore(config), defaults=model())
    service.update({"database.driver": "sqlite"})
    reset = service.reset("database.driver").config
    assert (
        reset.database.driver is None
        and reset.database.profiles == config.database.profiles
    )
    assert reset.database.defaults == config.database.defaults
    with pytest.raises(InvalidConfiguration):
        absent.with_changes({"database.driver": "postgres"})
    assert DatabaseConfig.from_dict({}).driver is None


def test_device_default_path_policy_without_discovery(tmp_path, monkeypatch):
    key = "LOCALAPPDATA" if os.name == "nt" else "XDG_CONFIG_HOME"
    monkeypatch.setenv(key, str(tmp_path))
    suffix = "ProcessForge" if os.name == "nt" else "processforge"
    assert (
        DeviceConfigurationSource.default_path()
        == tmp_path / suffix / "configuration.yaml"
    )
    assert (
        ConfigurationProvider().device_path == DeviceConfigurationSource.default_path()
    )
    monkeypatch.setenv(key, "relative")
    with pytest.raises(Exception, match="configuration_absolute_path_required"):
        DeviceConfigurationSource.default_path()
    monkeypatch.delenv(key)
    assert DeviceConfigurationSource.default_path().is_absolute()


def test_real_yaml_crud_presence_and_pinned_operation(tmp_path):
    path = write(tmp_path / "device.yaml", {"logging": {"events": False}})
    store = YamlConfigStore(path)
    provider = ConfigurationProvider(device_path=path)
    initial = provider.snapshot()
    pinned = ConfigurationProvider.pinned(initial.config)
    service = ConfigService(store)
    updated = service.update({"database.driver": "sqlite"})
    assert "database.driver" in updated.explicit_keys
    assert store.read().explicit_keys == updated.explicit_keys
    assert provider.current().database.driver == "sqlite"
    reset = service.reset("database.driver")
    assert "database" not in reset.config.to_dict()
    assert "database.driver" not in reset.explicit_keys
    assert pinned.current() is initial.config
    assert pinned.current().database is None
    assert provider.current().database is None
    service.delete()
    assert not path.exists()
    assert provider.current() == PFConfig()


def test_config_schema_selectors_and_source_validation(tmp_path):
    for model in (PFConfig, ProjectPFConfig):
        for selector in (None, "sqlite"):
            value = model.from_dict({"database": {"driver": selector}})
            assert value.database.driver == selector
        for invalid in (True, False, 1, "", "SQLite", [], {}):
            with pytest.raises(InvalidConfiguration, match="database_profile_invalid"):
                model.from_dict({"database": {"driver": invalid}})
    path = tmp_path / "config.yaml"
    for invalid in (
        "logging: {events: true, events: false}",
        "logging: &alias {events: false}",
        "schema_version: 2",
        "runtime: {metrics: {interval_seconds: .nan}}",
        "database: {driver: server}",
    ):
        path.write_text(invalid, encoding="utf-8")
        with pytest.raises(InvalidConfiguration):
            ConfigurationProvider(device_path=path).snapshot()


def test_errors_and_revisions_stay_with_exact_source_tuple(tmp_path):
    device = write(tmp_path / "device.yaml", {})
    work1 = write(tmp_path / "work1.yaml", {"logging": {"events": False}})
    work2 = write(tmp_path / "work2.yaml", {"logging": {"events": True}})
    resolver = ConfigurationResolver()
    one = ConfigurationProvider(
        device_path=device, workplace_path=work1, resolver=resolver
    )
    two = ConfigurationProvider(
        device_path=device, workplace_path=work2, resolver=resolver
    )
    old = one.snapshot()
    good = two.snapshot()
    work1.write_text("logging: {events: invalid}", encoding="utf-8")
    bad = one.snapshot()
    assert bad.errors == ("configuration_logging_invalid",)
    assert bad.workplace.revision == old.workplace.revision
    assert two.snapshot().errors == ()
    assert two.snapshot().workplace.revision == good.workplace.revision
    assert two.get("logging.events") is True


def test_pinned_roundtrip_for_native_worker_snapshot():
    config = PFConfig.from_dict(
        {
            "runtime": {"metrics": {"interval_seconds": 49}},
            "logging": {"events": False},
            "database": {"driver": "sqlite"},
        }
    )
    # Identity/hash/path enforcement belongs to the host transport; the provider
    # receives only its strict validated configuration payload.
    payload = json.loads(json.dumps(config.to_dict()))
    pinned = ConfigurationProvider.pinned(PFConfig.from_dict(payload))
    assert pinned.current() == config
    assert pinned.get("runtime.metrics.interval_seconds") == 49
    assert pinned.snapshot(refresh=True) is pinned.snapshot()
    assert pinned != ConfigurationProvider.pinned(PFConfig())
