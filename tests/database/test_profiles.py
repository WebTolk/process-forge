"""Optional profile validation and old configuration service behavior."""

import json
import os
from dataclasses import replace

import pytest

from processforge_core.configuration import (
    ConfigService,
    ConfigSnapshot,
    DatabaseConfig,
    DatabaseProfile,
    InvalidConfiguration,
    PFConfig,
    ProjectPFConfig,
)
from processforge_core.configuration.resolution import ConfigurationResolver
from processforge_core.database import DatabaseFactory, DatabaseIdentity, DatabaseTarget

from . import isolated_path

tmp_path = isolated_path


def section(scope="project", profile_id="main"):
    return {
        "profiles": {
            profile_id: {"scope": scope, "driver": "sqlite", "path": "data/pf.sqlite3"}
        },
        "defaults": {scope + "_main": profile_id},
    }


@pytest.mark.parametrize("model", [PFConfig, ProjectPFConfig])
def test_absent_serialization_and_strict_old_keys(model):
    config = model.from_dict({})
    assert "database" not in config.to_dict()
    assert model.from_dict(config.to_dict()) == config
    changed = config.with_changes({"logging.raw_hooks": False})
    assert "database" not in changed.to_dict()
    assert changed.get("logging.raw_hooks") is False
    for key in ("unknown", "database", "database.profiles", "runtime.bad"):
        with pytest.raises(InvalidConfiguration, match="configuration_key_unknown"):
            config.get(key)
    with pytest.raises(InvalidConfiguration, match="configuration_fields_invalid"):
        model.from_dict({"unknown": {}})
    with pytest.raises(InvalidConfiguration, match="configuration_key_unknown"):
        config.with_changes({"unknown": 1})
    with pytest.raises(InvalidConfiguration, match="configuration_fields_invalid"):
        model.from_dict({"runtime": {"unknown": 1}})


class MemoryStore:
    def __init__(self, config):
        self.snapshot = ConfigSnapshot(config, "0")

    def read(self):
        return self.snapshot

    def write(self, config, *, expected_revision):
        assert expected_revision == self.snapshot.revision
        self.snapshot = ConfigSnapshot(config, str(int(expected_revision) + 1))
        return self.snapshot


@pytest.mark.parametrize("model", [PFConfig, ProjectPFConfig])
def test_old_get_update_reset_service(model):
    service = ConfigService(MemoryStore(model()), defaults=model())
    assert "database" not in service.read().config.to_dict()
    updated = service.update({"logging.events": False})
    assert updated.config.get("logging.events") is False
    reset = service.reset("logging.events")
    assert reset.config.get("logging.events") == model().get("logging.events")
    assert "database" not in reset.config.to_dict()


@pytest.mark.parametrize("model", [PFConfig, ProjectPFConfig])
def test_profiles_roundtrip_immutable(model):
    payload = section()
    config = model.from_dict({"database": payload})
    assert model.from_dict(config.to_dict()) == config
    payload["profiles"]["main"]["path"] = "changed.sqlite3"
    assert config.database.profiles["main"].path == "data/pf.sqlite3"
    with pytest.raises(TypeError):
        config.database.defaults["project_main"] = "other"
    changed = config.with_changes({"database": section(profile_id="new")})
    assert "new" in changed.database.profiles


@pytest.mark.parametrize(
    "path",
    [
        "../x",
        "a/../x",
        "/x",
        "C:/x",
        "C:x",
        "\\\\host\\share",
        "a//b",
        "a/./b",
        "$ROOT/x",
        "%ROOT%/x",
        "~/x",
        "x\x00y",
        "a/",
        "a\\..\\b",
    ],
)
def test_unsafe_paths(path):
    with pytest.raises(InvalidConfiguration, match="database_profile_invalid"):
        DatabaseProfile("project", "sqlite", path)


@pytest.mark.parametrize("timeout", [True, -1, 30001, 1.5, "10"])
def test_timeout_validation(timeout):
    with pytest.raises(InvalidConfiguration):
        DatabaseProfile("project", "sqlite", "data/x", timeout)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"driver_options": {}},
        {"profiles": []},
        {
            "profiles": {
                "UPPER": {"scope": "project", "driver": "sqlite", "path": "data/x"}
            }
        },
        {
            "profiles": {
                "main": {"scope": "application", "driver": "sqlite", "path": "data/x"}
            }
        },
        {
            "profiles": {
                "main": {"scope": "project", "driver": "server", "path": "data/x"}
            }
        },
        {
            "profiles": {
                "main": {
                    "scope": "project",
                    "driver": "sqlite",
                    "path": "data/x",
                    "options": {},
                }
            }
        },
        {"defaults": {"project_main": "missing"}},
    ],
)
def test_invalid_section(payload):
    with pytest.raises(InvalidConfiguration):
        PFConfig.from_dict({"database": payload})


def test_inheritance_collision_and_workplace_escalation():
    workplace = PFConfig.from_dict({"database": section("workplace", "work")})
    project = ProjectPFConfig.from_dict({"database": section("project", "proj")})
    effective = workplace.for_project(project)
    assert set(effective.database.profiles) == {"work", "proj"}
    assert effective.database.defaults == {
        "workplace_main": "work",
        "project_main": "proj",
    }
    assert workplace.for_project(ProjectPFConfig()).database is workplace.database
    with pytest.raises(InvalidConfiguration):
        ProjectPFConfig.from_dict({"database": section("workplace", "work")})
    with pytest.raises(InvalidConfiguration):
        workplace.for_project(
            ProjectPFConfig.from_dict({"database": section("project", "work")})
        )


def test_cold_factory_pins_target_across_reload(tmp_path):
    config = DatabaseConfig.from_dict(section())
    target = DatabaseTarget(
        tmp_path / "data" / "pf.sqlite3", DatabaseIdentity("a" * 32, "project", "p")
    )
    database = DatabaseFactory.from_profile(config, "main", target)
    changed = replace(config.profiles["main"], path="other/pf.sqlite3")
    reloaded = DatabaseConfig({"main": changed}, config.defaults)
    assert database.target is target and database.timeout_ms == 100
    assert reloaded.profiles["main"].path != config.profiles["main"].path
    assert not target.path.parent.exists()


def test_old_default_payloads_exact():
    assert PFConfig().to_dict() == {
        "runtime": {
            "metrics": {"interval_seconds": 10.0},
            "garage_hooks": False,
            "temporary_files": {
                "mode": "notify",
                "max_age_hours": 168,
                "retain_unused": False,
            },
        },
        "schema_version": 1,
        "logging": {"raw_hooks": True, "events": True},
    }
    assert ProjectPFConfig().to_dict() == {
        "logging": {"raw_hooks": None, "events": None},
        "schema_version": 1,
        "runtime": {
            "garage_hooks": None,
            "temporary_files": {
                "mode": None,
                "max_age_hours": None,
                "retain_unused": None,
            },
        },
    }


def test_real_config_reload_retains_pinned_binding_and_invalid_snapshot(tmp_path):
    path = tmp_path / "project.yaml"
    path.write_text(json.dumps({"database": section()}), encoding="utf-8")
    resolver = ConfigurationResolver()
    first = resolver.resolve(None, path)
    target = DatabaseTarget(
        tmp_path / "data" / "pf.sqlite3", DatabaseIdentity("a" * 32, "project", "p")
    )
    binding = DatabaseFactory.from_profile(first.config.database, "main", target)
    update = section()
    update["profiles"]["main"]["path"] = "other/pf.sqlite3"
    staged = tmp_path / "replacement.yaml"
    staged.write_text(json.dumps({"database": update}), encoding="utf-8")
    os.replace(staged, path)
    second = resolver.resolve(None, path)
    assert not second.errors
    assert second.config.database.profiles["main"].path == "other/pf.sqlite3"
    assert binding.target == target
    assert first.config.database.profiles["main"].path == "data/pf.sqlite3"
    staged.write_text(json.dumps({"database": {"unknown": 1}}), encoding="utf-8")
    os.replace(staged, path)
    invalid = resolver.resolve(None, path)
    assert invalid.config == second.config
    assert invalid.errors == ("database_profile_invalid",)
    assert not target.path.parent.exists()
