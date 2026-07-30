#!/usr/bin/env python3
"""Regression coverage for the remediation schema authority and inventory."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
COMMON_ID_PATTERN = "^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$"

OFFICIAL_KNOWLEDGE_MANIFESTS = {
    "packs/official/software-development/knowledge-packages/docs.php.yaml",
    "packs/official/software-development/knowledge-packages/docs.web.html.yaml",
    "packs/official/software-development/knowledge-packages/docs.web.css.yaml",
    "packs/official/software-development/knowledge-packages/docs.web.javascript.yaml",
    "packs/official/software-development/knowledge-packages/docs.web.accessibility.yaml",
    "packs/official/software-development/knowledge-packages/docs.web.performance.yaml",
}

SEED_KNOWLEDGE_MANIFESTS = {
    "seeds/knowledge-packages/docs.example-parent.yaml",
    "seeds/knowledge-packages/docs.example-child.yaml",
}

PACKAGE_KINDS = {
    "core",
    "organization",
    "direction",
    "specialization",
    "platform",
    "toolchain",
    "documentation",
    "rules",
    "source",
    "mixed",
    "project",
    "process",
    "task",
    "agent_profile",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def load_validator(root: Path) -> ModuleType:
    path = root / "tools" / "validate-process-forge-schemas.py"
    spec = importlib.util.spec_from_file_location("processforge_schema_validator", path)
    if spec is None or spec.loader is None:
        fail(f"cannot load validator module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_schema(root: Path, name: str) -> dict[str, Any]:
    return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))


def errors_for(validator: ModuleType, value: Any, schema: dict[str, Any]) -> list[str]:
    return validator.validate_instance(value, schema, schema, "$")


def expect_valid(validator: ModuleType, value: Any, schema: dict[str, Any], label: str) -> None:
    errors = errors_for(validator, value, schema)
    if errors:
        fail(f"{label} unexpectedly failed: {'; '.join(errors)}")


def expect_invalid(validator: ModuleType, value: Any, schema: dict[str, Any], label: str) -> None:
    if not errors_for(validator, value, schema):
        fail(f"{label} unexpectedly passed")


def package_manifest(package_id: str, kind: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": package_id,
        "name": "Schema inventory fixture",
        "version": "1.0.0",
        "kind": kind,
        "scope": "distribution",
        "resources": [],
    }


def validate_package_authority(root: Path, validator: ModuleType) -> None:
    schema = load_schema(root, "package-manifest.schema.json")
    if schema["$defs"]["id"]["pattern"] != COMMON_ID_PATTERN:
        fail("package manifest does not use the approved common resource id grammar")
    if set(schema["properties"]["kind"]["enum"]) != PACKAGE_KINDS:
        fail("package kind enum differs from the approved authority")

    for package_id in ["docs.php", "docs.example-child", "plain-package"]:
        expect_valid(validator, package_manifest(package_id, "documentation"), schema, f"package id {package_id}")
    for kind in sorted(PACKAGE_KINDS):
        expect_valid(validator, package_manifest("schema.inventory", kind), schema, f"package kind {kind}")

    expect_invalid(
        validator,
        package_manifest("schema.inventory", "knowledge_package"),
        schema,
        "forbidden knowledge_package kind",
    )
    for unsafe_id in ["../escaped", "docs/escaped", "Docs.upper", ".hidden", "docs..double"]:
        expect_invalid(validator, package_manifest(unsafe_id, "documentation"), schema, f"unsafe id {unsafe_id}")

    expected = OFFICIAL_KNOWLEDGE_MANIFESTS | SEED_KNOWLEDGE_MANIFESTS
    discovered = {
        path.relative_to(root).as_posix()
        for path in (root / "packs" / "official").glob("*/knowledge-packages/*.yaml")
    }
    discovered.update(
        path.relative_to(root).as_posix()
        for path in (root / "seeds" / "knowledge-packages").glob("*.yaml")
    )
    if discovered != expected:
        fail(f"knowledge inventory differs: expected {sorted(expected)}, got {sorted(discovered)}")
    for relative_path in sorted(expected):
        path = root / relative_path
        data = validator.load_yaml(path)
        expect_valid(validator, data, schema, relative_path)

    print(f"PASS: package authority covers {len(expected)} official/seed manifests")


def validate_template_authority(root: Path, validator: ModuleType) -> None:
    reusable_schema = load_schema(root, "reusable-template.schema.json")
    package_schema = load_schema(root, "template-package.schema.json")

    legacy_pre_release = {
        "schema_version": 1,
        "id": "legacy.report-template",
        "version": "1.0.0",
        "source_package": "docs.example-legacy",
        "type": "document",
    }
    reusable_v1 = {
        "schema_version": 1,
        "type": "reusable_template",
        "id": "report.audit-basic",
        "title": "Audit report",
        "kind": "document",
        "version": "1.0.0",
        "files": [{"source": "files/report.md", "target": "{{ output_path }}"}],
        "inputs": [{"id": "project-name", "required": True}],
        "outputs": [{"path": "report.md"}],
        "prompts": [{"path": "prompts/authoring.md"}],
        "tags": ["audit"],
    }
    portable_package = {
        "schema_version": 1,
        "id": "portable.report-template",
        "type": "multi-file",
        "version": "1.0.0",
        "payload": ["files/report.md"],
    }

    expect_invalid(validator, legacy_pre_release, reusable_schema, "legacy pre-release reusable template")
    expect_valid(validator, reusable_v1, reusable_schema, "reusable template v1")
    empty_files_v1 = dict(reusable_v1)
    empty_files_v1["files"] = []
    expect_valid(validator, empty_files_v1, reusable_schema, "reusable template v1 with empty files")
    expect_valid(validator, portable_package, package_schema, "portable template package")
    expect_valid(
        validator,
        validator.load_yaml(root / "templates" / "template-package.yaml"),
        package_schema,
        "shipped portable template package",
    )
    expect_invalid(validator, reusable_v1, package_schema, "reusable template as portable package")
    expect_invalid(validator, portable_package, reusable_schema, "portable package as reusable template")

    missing_type = dict(reusable_v1)
    missing_type.pop("type")
    expect_invalid(validator, missing_type, reusable_schema, "reusable template without type")
    missing_files = dict(reusable_v1)
    missing_files.pop("files")
    expect_invalid(validator, missing_files, reusable_schema, "reusable template without files")
    print("PASS: reusable template v1 and portable template package contracts remain separate")


def validate_platform_registry_authority(root: Path, validator: ModuleType) -> None:
    schema = load_schema(root, "platform-registry.schema.json")
    entry = {
        "id": "joomla.cms",
        "name": "Joomla CMS",
        "path": "platforms/joomla.cms/platform-contract.yaml",
        "package_id": "platform.example-cms",
        "status": "available",
    }
    registry = {"schema_version": 1, "platforms": [entry]}
    expect_valid(validator, registry, schema, "complete platform registry entry")
    for missing in ["id", "name", "path", "package_id", "status"]:
        incomplete = dict(entry)
        incomplete.pop(missing)
        expect_invalid(
            validator,
            {"schema_version": 1, "platforms": [incomplete]},
            schema,
            f"platform entry without {missing}",
        )
    print("PASS: platform registry requires identity, display name, path, package and status")


def validate_release_inventory(root: Path, validator: ModuleType) -> None:
    source = (root / "tools" / "validate-process-forge-schemas.py").read_text(encoding="utf-8")
    required_fragments = [
        '(root / "packs" / "official").glob("*/knowledge-packages/*.yaml")',
        '(root / "seeds" / "knowledge-packages").glob("*.yaml")',
        'root / "templates" / "template-package.yaml"',
        'root / "templates" / "registries" / "platforms.yaml"',
        '"tools/smoke_remediation_schema_inventory.py"',
    ]
    for fragment in required_fragments:
        if fragment not in source:
            fail(f"release schema inventory missing mapping: {fragment}")

    expected = OFFICIAL_KNOWLEDGE_MANIFESTS | SEED_KNOWLEDGE_MANIFESTS
    required_files = set(validator.REQUIRED_FILES)
    missing = sorted(expected - required_files)
    if missing:
        fail(f"knowledge manifests missing from required release inventory: {missing}")
    print("PASS: release validator inventory includes bundled/seed knowledge and platform registry")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    validator = load_validator(root)

    validate_package_authority(root, validator)
    validate_template_authority(root, validator)
    validate_platform_registry_authority(root, validator)
    validate_release_inventory(root, validator)
    print("PASS: remediation schema inventory smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
