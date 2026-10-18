#!/usr/bin/env python3
"""Temporary-file settings: strict immutable values, inheritance and real CRUD."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from processforge_core.configuration import ConfigService, PFConfig, ProjectPFConfig, TemporaryFilesConfig
from processforge_core.configuration.resolution import ConfigurationResolver
from processforge_core.configuration.yaml_store import YamlConfigStore
from smoke_workplace_configuration import cli, rejects

MODE = "runtime.temporary_files.mode"
AGE = "runtime.temporary_files.max_age_hours"


def main():
    assert PFConfig().get(MODE) == "notify" and PFConfig().get(AGE) == 168
    try:
        TemporaryFilesConfig().mode = "off"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("mutable temporary-file config")
    for age in (1, 1.5, 168, 87600):
        assert PFConfig().with_changes({AGE: age}).get(AGE) == age
    for age in (True, False, None, 0, 87601, float("nan"), float("inf"), -float("inf"), "168", [], 10**400):
        rejects(lambda: PFConfig().with_changes({AGE: age}))
        if age is not None:
            rejects(lambda: ProjectPFConfig().with_changes({AGE: age}))
    for mode in (True, False, None, "delete", "", [], {}):
        rejects(lambda: PFConfig().with_changes({MODE: mode}))
        if mode is not None:
            rejects(lambda: ProjectPFConfig().with_changes({MODE: mode}))
    for model in (PFConfig, ProjectPFConfig):
        for value in ({"temporary_files": {"unexpected": 1}}, {"temporary_files": None},
                      {"temporary_files": {"max_age_days": 7}}, {"unexpected": 1}):
            rejects(lambda: model.from_dict({"runtime": value}))
    for mode in ("notify", "off"):
        for age in (1, 168, 87600):
            device = PFConfig().with_changes({MODE: mode, AGE: age})
            for override_mode in (None, "notify", "off"):
                for override_age in (None, 24.5):
                    overrides = ProjectPFConfig().with_changes({MODE: override_mode, AGE: override_age})
                    result = device.for_project(overrides)
                    assert result.get(MODE) == (mode if override_mode is None else override_mode)
                    assert result.get(AGE) == (age if override_age is None else override_age)
                    assert PFConfig.from_dict(result.to_dict()) == result
                    assert ProjectPFConfig.from_dict(overrides.to_dict()) == overrides
    with tempfile.TemporaryDirectory(dir=os.environ.get("PF_TEST_SCRATCH_ROOT", ROOT / ".pf/tmp")) as raw:
        root = Path(raw).resolve()
        project = root / "project"
        (project / ".pf").mkdir(parents=True)
        cli(root, "create")
        cli(root, "create", "--project-root", str(project))
        cli(root, "update", "--key", MODE, "--value", json.dumps("off"))
        assert cli(root, "read", "--project-root", str(project), "--key", MODE)["value"] == "off"
        cli(root, "update", "--project-root", str(project), "--key", AGE, "--value", "24.5")
        read = cli(root, "read", "--project-root", str(project), "--key", AGE)
        assert read["value"] == 24.5 and read["override"] == 24.5
        cli(root, "update", "--project-root", str(project), "--key", AGE, "--value", "null")
        assert cli(root, "read", "--project-root", str(project), "--key", AGE)["override"] is None
        cli(root, "update", "--project-root", str(project), "--key", MODE, "--value", json.dumps("notify"))
        cli(root, "delete", "--project-root", str(project), "--key", MODE)
        assert cli(root, "read", "--project-root", str(project), "--key", MODE)["value"] == "off"
        assert cli(root, "update", "--key", AGE, "--value", "true", exit_code=1)["error"] == "configuration_temporary_files_age_invalid"
        resolver = ConfigurationResolver()
        path = project / ".pf/configuration.yaml"
        assert resolver.resolve(root / "configuration.yaml", path).config.get(MODE) == "off"
        service = ConfigService(YamlConfigStore(path, model=ProjectPFConfig), defaults=ProjectPFConfig())
        service.update({MODE: "notify"})
        assert resolver.resolve(root / "configuration.yaml", path).config.get(MODE) == "notify"
        service.reset(MODE)
        assert resolver.resolve(root / "configuration.yaml", path).config.get(MODE) == "off"
        assert YamlConfigStore._decode((ROOT / "templates/workplace-configuration.yaml").read_bytes()) == PFConfig()
    for name, model in (("workplace", PFConfig), ("project", ProjectPFConfig)):
        schema = json.loads((ROOT / f"schemas/{name}-configuration.schema.json").read_bytes())
        validate = runpy.run_path(str(ROOT / "tools/validate-process-forge-schemas.py"))["validate_instance"]
        assert validate(model().to_dict(), schema, schema, "$") == []
        for mode, age in (("off", 1), ("notify", 87600), ("notify", 1.5)):
            assert validate(model().with_changes({MODE: mode, AGE: age}).to_dict(), schema, schema, "$") == []
        for value in (True, 0, 87601, "168"):
            assert validate({"runtime": {"temporary_files": {"max_age_hours": value}}}, schema, schema, "$")
        assert validate({"runtime": {"temporary_files": {"unknown": 1}}}, schema, schema, "$")
        temporary = schema["properties"]["runtime"]["properties"]["temporary_files"]
        assert temporary["additionalProperties"] is False
        defaults = model().to_dict()["runtime"]["temporary_files"]
        assert {key: rule["default"] for key, rule in temporary["properties"].items()} == defaults
    print("PASS: temporary config validation, 36 inheritance combinations, immutable round trips, real CLI CRUD/reset, resolver reload and schemas")


if __name__ == "__main__":
    main()
