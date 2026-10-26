"""Strict permission and existing universal configuration composition."""

import pytest

from processforge_core.configuration import (
    InvalidConfiguration,
    PFConfig,
    ProjectPFConfig,
)

KEY = "runtime.temporary_files.retain_unused"


@pytest.mark.parametrize("value", ["true", "false", 0, 1, [], {}])
@pytest.mark.parametrize("model", [PFConfig, ProjectPFConfig])
def test_invalid_permission(value, model):
    with pytest.raises(
        InvalidConfiguration, match="configuration_temporary_files_retention_invalid"
    ):
        model().with_changes({KEY: value})


def test_global_null_invalid_project_null_inherits():
    with pytest.raises(
        InvalidConfiguration, match="configuration_temporary_files_retention_invalid"
    ):
        PFConfig().with_changes({KEY: None})
    assert PFConfig().get(KEY) is False
    assert ProjectPFConfig().get(KEY) is None
    for global_value in (False, True):
        base = PFConfig().with_changes({KEY: global_value})
        for override in (False, True, None):
            project = ProjectPFConfig().with_changes({KEY: override})
            result = base.for_project(project)
            assert result.get(KEY) is (global_value if override is None else override)
            assert PFConfig.from_dict(result.to_dict()) == result
            assert ProjectPFConfig.from_dict(project.to_dict()) == project


def test_explicit_workplace_false_over_device_true():
    device = PFConfig().with_changes({KEY: True})
    workplace = PFConfig().with_changes({KEY: False})
    assert device.overlay(workplace, explicit_keys=frozenset()).get(KEY) is True
    assert device.overlay(workplace, explicit_keys=frozenset({KEY})).get(KEY) is False
