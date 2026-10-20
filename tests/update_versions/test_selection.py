"""Regressions for update precedence through the existing public policy."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from processforge_core.maintenance.versions import UpdateVersionSelectionPolicy  # noqa: E402
from processforge_core.resources.versioning import ResourceVersionPolicy  # noqa: E402


@pytest.mark.parametrize(
    ("available", "installed", "expected"),
    [
        ("1.3.0-alpha1", "1.2.0", True),
        ("1.3.0-alpha2", "1.3.0-alpha1", True),
        ("1.3.0", "1.3.0-alpha1", True),
        ("1.3.0-alpha1", "1.3.0", False),
        ("1.3.0-alpha.10", "1.3.0-alpha.2", True),
        ("1.3.0-alpha.beta", "1.3.0-alpha.10", True),
        ("1.3.0-alpha.1", "1.3.0-alpha", True),
        ("1.3.0-alpha10", "1.3.0-alpha2", False),
        ("1.3.0+build2", "1.3.0+build1", False),
        ("1.3.0-alpha1+build2", "1.3.0-alpha1+build1", False),
        ("v1.3.0-alpha2+build", "v1.3.0-alpha1", True),
        ("1.3", "1.2", True),
        ("1.3.0-alpha1", None, True),
    ],
)
def test_selects_only_newer_precedence(
    available: str, installed: str | None, expected: bool
) -> None:
    record: dict[str, Any] = {"version": available, "download_url": "unchanged"}
    selected, warnings = UpdateVersionSelectionPolicy().select([record], installed)
    assert (selected is record) is expected
    assert warnings == []


def test_greatest_precedence_is_independent_of_manifest_order() -> None:
    records = [
        {"version": "1.3.0"},
        {"version": "1.3.0-alpha2"},
        {"version": "1.3.0-alpha1"},
    ]
    policy = UpdateVersionSelectionPolicy()
    for versions in (records, list(reversed(records))):
        selected, warnings = policy.select(versions, "1.2.0")
        assert selected is records[0]
        assert warnings == []


def test_semver_precedence_sequence() -> None:
    sequence = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    policy = UpdateVersionSelectionPolicy()
    for installed, available in zip(sequence, sequence[1:]):
        selected, warnings = policy.select([{"version": available}], installed)
        assert selected == {"version": available}
        assert warnings == []


def test_lexical_warning_and_resource_constraints_stay_unchanged() -> None:
    selected, warnings = UpdateVersionSelectionPolicy().select(
        [{"version": "release-b"}], "release-a"
    )
    assert selected == {"version": "release-b"}
    assert warnings == ["non-semver version compared lexically"]
    resources = ResourceVersionPolicy()
    assert resources.key("1.3.0-alpha1") == resources.key("1.3.0-alpha2")
    assert resources.is_newer("1.3.0", "1.3.0-alpha1") == (False, None)


def test_channel_filter_still_precedes_version_selection() -> None:
    policy = UpdateVersionSelectionPolicy()
    manifest: dict[str, Any] = {
        "subjects": [
            {
                "id": "processforge",
                "versions": [
                    {"version": "1.3.0-alpha2", "channels": ["alpha"]},
                    {"version": "1.2.0", "channels": ["stable"]},
                ],
            }
        ]
    }
    site: dict[str, Any] = {
        "subject": {"id": "processforge", "type": "core"},
        "source": {"id": "file-test", "provider": "file"},
    }
    assert policy.select(policy.normalize(manifest, site, "stable"), "1.2.0") == (
        None,
        [],
    )
    selected, warnings = policy.select(
        policy.normalize(manifest, site, "alpha"), "1.3.0-alpha1"
    )
    assert selected is not None and selected["version"] == "1.3.0-alpha2"
    assert warnings == []
