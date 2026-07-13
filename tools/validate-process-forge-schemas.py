#!/usr/bin/env python3
"""Validate ProcessForge structure and YAML/JSON files against JSON Schemas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "process-forge.yaml",
    "docs/concepts/file-first-processes.md",
    "docs/concepts/workplace-layer.md",
    "docs/concepts/project-flow-layer.md",
    "docs/concepts/cascade-merge.md",
    "docs/concepts/execution-context-package.md",
    "docs/concepts/reusable-templates.md",
    "docs/concepts/process-evolution.md",
    "docs/concepts/workplace-init.md",
    "docs/concepts/project-init.md",
    "docs/concepts/public-private-config.md",
    "docs/concepts/capability-resolution.md",
    "docs/concepts/session-bootstrap.md",
    "docs/concepts/context-resolution.md",
    "docs/concepts/instruction-conflicts.md",
    "docs/concepts/context-cache.md",
    "docs/concepts/context-index.md",
    "docs/concepts/context-capsule.md",
    "docs/authoring/workplace-configuration.md",
    "docs/authoring/project-initialization.md",
    "docs/validation/doctor-workplace.md",
    "docs/validation/doctor-project.md",
    "docs/validation/doctor-context.md",
    "schemas/process-forge-manifest.schema.json",
    "schemas/workplace.schema.json",
    "schemas/terms.schema.json",
    "schemas/platform-registry.schema.json",
    "schemas/knowledge-roots-registry.schema.json",
    "schemas/package-roots-registry.schema.json",
    "schemas/template-registry.schema.json",
    "schemas/tool-registry.schema.json",
    "schemas/mcp-registry.schema.json",
    "schemas/workplace-init-answers.schema.json",
    "schemas/project-init-answers.schema.json",
    "schemas/session-start.schema.json",
    "schemas/context-index.schema.json",
    "schemas/resolved-rules.schema.json",
    "schemas/context-conflict-report.schema.json",
    "schemas/context-capsule.schema.json",
    "schemas/context-cache.schema.json",
    "schemas/process-definition.schema.json",
    "schemas/package-manifest.schema.json",
    "schemas/reusable-template.schema.json",
    "schemas/assignment.schema.json",
    "schemas/execution-context-package.schema.json",
    "schemas/artifact.schema.json",
    "schemas/review.schema.json",
    "schemas/handoff.schema.json",
    "processes/software-feature-development.yaml",
    "processes/bug-fix.yaml",
    "processes/testing.yaml",
    "processes/content-production.yaml",
    "processes/knowledge-package-improvement.yaml",
    "processes/process-version-upgrade.yaml",
    "processes/workplace-initialization.yaml",
    "processes/project-initialization.yaml",
    "processes/session-bootstrap.yaml",
    "processes/context-resolution.yaml",
    "templates/workplace.yaml",
    "templates/terms.yaml",
    "templates/registries/platforms.yaml",
    "templates/registries/knowledge-roots.yaml",
    "templates/registries/package-roots.yaml",
    "templates/registries/templates.yaml",
    "templates/registries/tools.yaml",
    "templates/registries/mcp.yaml",
    "templates/workplace-init.answers.yaml",
    "templates/project-init.answers.yaml",
    "templates/process-forge.yaml",
    "templates/process-forge.local.yaml",
    "templates/project-agents-template.md",
    "templates/project-init-proposal-template.md",
    "templates/project-profile-template.md",
    "templates/repository-map-template.md",
    "templates/project-conventions-template.md",
    "templates/global-resource-matching-report-template.md",
    "templates/project-init-review-template.md",
    "templates/session-start-template.yaml",
    "templates/session-status-report-template.md",
    "templates/context-index-template.yaml",
    "templates/resolved-rules-template.yaml",
    "templates/context-conflict-report-template.md",
    "templates/context-capsule-template.yaml",
    "tools/processforge.py",
]

PROCESS_REQUIRED_KEYS = [
    "schema_version",
    "id",
    "name",
    "version",
    "status",
    "description",
    "stages",
    "roles",
    "artifact_definitions",
    "gates",
    "evolution_policy",
]

PACKAGE_REQUIRED_KEYS = ["schema_version", "id", "name", "version", "kind", "scope"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_yaml_key(text: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}\s*:", text) is not None


def load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required for schema validation of YAML files") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_schema(root: Path, name: str) -> dict[str, Any]:
    path = root / "schemas" / name
    return json.loads(read_text(path))


def schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported external ref {ref}")
    node: Any = schema
    for part in ref[2:].split("/"):
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"ref {ref} does not resolve to schema object")
    return node


def validate_instance(value: Any, node: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "$ref" in node:
        return validate_instance(value, resolve_ref(root_schema, str(node["$ref"])), root_schema, path)

    expected_type = node.get("type")
    if isinstance(expected_type, list):
        if not any(schema_type_matches(value, item) for item in expected_type):
            errors.append(f"{path}: expected one of {expected_type}, got {type(value).__name__}")
            return errors
    elif isinstance(expected_type, str) and not schema_type_matches(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return errors

    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected const {node['const']!r}")
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: expected one of {node['enum']!r}")
    if "minimum" in node and isinstance(value, (int, float)) and value < node["minimum"]:
        errors.append(f"{path}: expected minimum {node['minimum']}")
    if "minLength" in node and isinstance(value, str) and len(value) < node["minLength"]:
        errors.append(f"{path}: expected minLength {node['minLength']}")
    if "minItems" in node and isinstance(value, list) and len(value) < node["minItems"]:
        errors.append(f"{path}: expected minItems {node['minItems']}")
    if "pattern" in node and isinstance(value, str) and not re.fullmatch(str(node["pattern"]), value):
        errors.append(f"{path}: does not match pattern {node['pattern']!r}")

    if isinstance(value, dict):
        required = node.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path}: missing required key {key}")
        properties = node.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    errors.extend(validate_instance(value[key], child_schema, root_schema, f"{path}.{key}"))
        additional = node.get("additionalProperties", True)
        if additional is False and isinstance(properties, dict):
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected key {key}")
        elif isinstance(additional, dict) and isinstance(properties, dict):
            for key, child in value.items():
                if key not in properties:
                    errors.extend(validate_instance(child, additional, root_schema, f"{path}.{key}"))

    if isinstance(value, list):
        items_schema = node.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_instance(item, items_schema, root_schema, f"{path}[{index}]"))

    return errors


def validate_against_schema(data: Any, schema: dict[str, Any], label: str) -> None:
    errors = validate_instance(data, schema, schema, "$")
    if errors:
        fail(f"{label} failed schema validation: " + "; ".join(errors[:8]))


def validate_required_files(root: Path) -> None:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))


def validate_json_schemas(root: Path) -> None:
    for path in sorted((root / "schemas").glob("*.json")):
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            fail(f"{path.relative_to(root)} is invalid JSON: {exc}")
        for key in ("$schema", "title", "type"):
            if key not in data:
                fail(f"{path.relative_to(root)} missing {key}")


def validate_yaml_like_files(root: Path) -> None:
    manifest = read_text(root / "process-forge.yaml")
    for key in ("schema_version", "process_forge", "project", "paths", "policies"):
        if not has_yaml_key(manifest, key):
            fail(f"process-forge.yaml missing {key}")

    process_count = 0
    non_development = False
    for path in sorted((root / "processes").glob("*.yaml")):
        process_count += 1
        text = read_text(path)
        for key in PROCESS_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(root)} missing {key}")
        if path.name in {"content-production.yaml", "testing.yaml"}:
            non_development = True
    if process_count < 3:
        fail("expected at least three process definitions")
    if not non_development:
        fail("expected at least one non-development process")

    for path in sorted((root / "packages").glob("*.yaml")):
        text = read_text(path)
        for key in PACKAGE_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(root)} missing {key}")


def validate_yaml_schema_files(root: Path) -> None:
    mappings: list[tuple[Path, str]] = [
        (root / "process-forge.yaml", "process-forge-manifest.schema.json"),
    ]
    mappings.extend((path, "process-definition.schema.json") for path in sorted((root / "processes").glob("*.yaml")))
    mappings.extend((path, "package-manifest.schema.json") for path in sorted((root / "packages").glob("*.yaml")))

    context_root = root / "contexts"
    if (context_root / "context-index.yaml").is_file():
        mappings.append((context_root / "context-index.yaml", "context-index.schema.json"))
    if (context_root / "resolved-rules.yaml").is_file():
        mappings.append((context_root / "resolved-rules.yaml", "resolved-rules.schema.json"))
    mappings.extend((path, "execution-context-package.schema.json") for path in sorted(context_root.glob("*.ecp.yaml")))
    mappings.extend((path, "context-capsule.schema.json") for path in sorted(context_root.glob("*.capsule.yaml")))

    if (root / "workplace.yaml").is_file():
        mappings.append((root / "workplace.yaml", "workplace.schema.json"))

    for path, schema_name in mappings:
        data = load_yaml(path)
        schema = load_schema(root, schema_name)
        validate_against_schema(data, schema, path.relative_to(root).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    validate_required_files(root)
    validate_json_schemas(root)
    validate_yaml_like_files(root)
    validate_yaml_schema_files(root)
    print("PASS: ProcessForge structure and JSON Schema validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
