from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check, check


class UpdateSchemaChecks:
    """Check governed update documents against the existing schema subset."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root


    def type_matches(self, value: Any, expected: str) -> bool:
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

    def resolve_ref(self, schema: dict[str, Any], ref: str) -> dict[str, Any]:
        if not ref.startswith("#/"):
            raise ValueError(f"unsupported external ref {ref}")
        node: Any = schema
        for part in ref[2:].split("/"):
            node = node[part]
        if not isinstance(node, dict):
            raise ValueError(f"ref {ref} does not resolve to schema object")
        return node

    def validate(self, value: Any, node: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[str]:
        errors: list[str] = []
        if "$ref" in node:
            return self.validate(value, self.resolve_ref(root_schema, str(node["$ref"])), root_schema, path)

        all_of = node.get("allOf")
        if isinstance(all_of, list):
            for alternative in all_of:
                if isinstance(alternative, dict):
                    errors.extend(
                        self.validate(
                            value,
                            alternative,
                            root_schema,
                            path,
                        )
                    )

        any_of = node.get("anyOf")
        if isinstance(any_of, list):
            matches = sum(
                1
                for alternative in any_of
                if isinstance(alternative, dict)
                and not self.validate(value, alternative, root_schema, path)
            )
            if matches == 0:
                errors.append(f"{path}: expected at least one anyOf alternative")

        one_of = node.get("oneOf")
        if isinstance(one_of, list):
            matches = sum(
                1
                for alternative in one_of
                if isinstance(alternative, dict)
                and not self.validate(value, alternative, root_schema, path)
            )
            if matches != 1:
                errors.append(f"{path}: expected exactly one oneOf alternative, got {matches}")

        excluded = node.get("not")
        if isinstance(excluded, dict) and not self.validate(
            value,
            excluded,
            root_schema,
            path,
        ):
            errors.append(f"{path}: matched forbidden not schema")

        conditional = node.get("if")
        if isinstance(conditional, dict):
            condition_matches = not self.validate(
                value,
                conditional,
                root_schema,
                path,
            )
            branch = node.get("then") if condition_matches else node.get("else")
            if isinstance(branch, dict):
                errors.extend(
                    self.validate(
                        value,
                        branch,
                        root_schema,
                        path,
                    )
                )

        expected_type = node.get("type")
        if isinstance(expected_type, list):
            if not any(self.type_matches(value, item) for item in expected_type):
                errors.append(f"{path}: expected one of {expected_type}, got {type(value).__name__}")
                return errors
        elif isinstance(expected_type, str) and not self.type_matches(value, expected_type):
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
        if "uniqueItems" in node and node["uniqueItems"] is True and isinstance(value, list):
            normalized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(normalized) != len(set(normalized)):
                errors.append(f"{path}: expected uniqueItems")
        if "minProperties" in node and isinstance(value, dict) and len(value) < node["minProperties"]:
            errors.append(f"{path}: expected minProperties {node['minProperties']}")
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
                        errors.extend(self.validate(value[key], child_schema, root_schema, f"{path}.{key}"))
            additional = node.get("additionalProperties", True)
            if additional is False and isinstance(properties, dict):
                for key in value:
                    if key not in properties:
                        errors.append(f"{path}: unexpected key {key}")
            elif isinstance(additional, dict) and isinstance(properties, dict):
                for key, child_schema in value.items():
                    if key not in properties:
                        errors.extend(self.validate(child_schema, additional, root_schema, f"{path}.{key}"))

        if isinstance(value, list):
            items_schema = node.get("items")
            if isinstance(items_schema, dict):
                for index, item in enumerate(value):
                    errors.extend(self.validate(item, items_schema, root_schema, f"{path}[{index}]"))

        return errors

    def append(self, checks: list[Check], data: Any, schema_name: str, label: str) -> None:
        schema_path = self.distribution_root / "schemas" / schema_name
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            checks.append(check("FAIL", f"{label} schema {schema_name} could not be loaded: {exc}"))
            return
        try:
            errors = self.validate(data, schema, schema, "$")
        except (KeyError, ValueError) as exc:
            checks.append(check("FAIL", f"{label} schema {schema_name} is unsupported: {exc}"))
            return
        for message in errors:
            checks.append(check("FAIL", f"{label} schema validation failed: {message}"))
        if not errors:
            checks.append(check("PASS", f"{label} matches {schema_name}"))

    def require(self, data: Any, schema_name: str, label: str) -> None:
        """Fail an apply/release precondition when a governed document is invalid."""
        checks: list[Check] = []
        self.append(checks, data, schema_name, label)
        failures = [item.message for item in checks if item.level == "FAIL"]
        if failures:
            raise SystemExit("FAIL: " + "; ".join(failures))
