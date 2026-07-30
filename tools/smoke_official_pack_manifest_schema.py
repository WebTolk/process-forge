#!/usr/bin/env python3
"""Validate every official process-pack manifest against its public schema."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACK_IDS = {
    "processforge.official.software-development",
    "processforge.official.content-workflow",
    "processforge.official.verification",
}


def load_validator():
    path = ROOT / "tools" / "validate-process-forge-schemas.py"
    spec = importlib.util.spec_from_file_location("processforge_schema_validator_smoke", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "process-pack-manifest.schema.json").read_text(encoding="utf-8")
    )
    validator = load_validator()
    manifests = sorted((ROOT / "packs" / "official").glob("*/package.yaml"))
    assert len(manifests) == len(EXPECTED_PACK_IDS), manifests

    seen: set[str] = set()
    for path in manifests:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = validator.validate_instance(data, schema, schema, "$")
        assert not errors, f"{path.relative_to(ROOT)}: {errors}"
        seen.add(str(data["id"]))
        assert data["origin"] == "official"
        assert data["bundled_with_distribution"] is True
        assert data["core_runtime_dependency"] is False
        assert data["production_ready"] is True
        assert data["activation"]["active_by_default"] is False
        assert data["activation"]["available_by_default"] is True
        assert data["provides"]["processes"]
        required_capabilities: set[str] = set()

        def collect_required_capabilities(value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "required_capabilities" and isinstance(item, list):
                        required_capabilities.update(str(capability) for capability in item)
                    collect_required_capabilities(item)
            elif isinstance(value, list):
                for item in value:
                    collect_required_capabilities(item)

        for process_path in sorted((path.parent / "processes").glob("*.yaml")):
            collect_required_capabilities(
                yaml.safe_load(process_path.read_text(encoding="utf-8"))
            )
        assert set(data["provides"]["capabilities"]) == required_capabilities, (
            path,
            data["provides"]["capabilities"],
            required_capabilities,
        )

    assert seen == EXPECTED_PACK_IDS, (seen, EXPECTED_PACK_IDS)
    print("PASS: smoke_official_pack_manifest_schema")


if __name__ == "__main__":
    main()
