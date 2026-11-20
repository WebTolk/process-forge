"""Validate the actual bundled indexing schema through native authoring checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from processforge_core.maintenance.schema_checks import UpdateSchemaChecks

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = {"$ref": "resource-indexing.schema.json"}


def test_bundled_indexing_ref_uses_its_own_internal_definitions():
    policy = {
        "enabled": True,
        "mode": "fulltext",
        "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}],
    }
    assert UpdateSchemaChecks(ROOT).validate(policy, REFERENCE, {}, "$") == []


@pytest.mark.parametrize(
    "policy",
    [
        {"mode": "metadata"},
        {"enabled": True, "mode": "invalid"},
        {"enabled": False, "mode": "fulltext"},
        {
            "enabled": True,
            "mode": "fulltext",
            "sources": [{"path": ".", "mode": "invalid"}],
        },
    ],
)
def test_bundled_indexing_ref_still_rejects_invalid_policies(policy):
    assert UpdateSchemaChecks(ROOT).validate(policy, REFERENCE, {}, "$")


def test_missing_bundled_indexing_schema_is_a_portable_refusal(tmp_path):
    with pytest.raises(ValueError, match="bundled indexing schema unavailable"):
        UpdateSchemaChecks(tmp_path).validate({}, REFERENCE, {}, "$")


@pytest.mark.parametrize("content", [b"{", b"[]", b"\xff"])
def test_invalid_bundled_indexing_schema_is_a_portable_refusal(tmp_path, content):
    folder = tmp_path / "schemas"
    folder.mkdir()
    (folder / "resource-indexing.schema.json").write_bytes(content)
    with pytest.raises(ValueError, match="bundled indexing schema unavailable"):
        UpdateSchemaChecks(tmp_path).validate({}, REFERENCE, {}, "$")


@pytest.mark.parametrize(
    "reference",
    [
        "other.schema.json",
        "../resource-indexing.schema.json",
        "https://example.org/schema.json",
    ],
)
def test_unknown_external_schema_references_remain_denied(reference):
    with pytest.raises(ValueError, match="unsupported external ref"):
        UpdateSchemaChecks(ROOT).validate({}, {"$ref": reference}, {}, "$")
