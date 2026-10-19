"""Existing workplace registry updates through concrete Core infrastructure."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import uuid

from ..common.text import ensure_trailing_newline
from ..common.values import upsert_resource
from ..common.yaml_dump import dump_yaml
from ..common.yaml_io import _parse_simple_yaml, yaml_error
from ..documents.reader import YamlDocumentReader
from ..maintenance.schema_checks import UpdateSchemaChecks


class WorkplaceRegistryWriter:
    """Preserve the existing validation and same-parent replacement algorithm."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.documents = YamlDocumentReader(_parse_simple_yaml)
        self._update_schema_checks = UpdateSchemaChecks(distribution_root)

    def upsert(self, path: Path, collection_key: str, entry: dict[str, Any]) -> str:
        if path.exists() and not path.is_file():
            raise SystemExit(f"FAIL: registry path is not a file: {path}")
        if path.is_file():
            data = self.documents.load(path)
            error = yaml_error(data)
            if error:
                raise SystemExit(f"FAIL: registry YAML invalid; original preserved: {path}: {error}")
            if not isinstance(data, dict) or not data:
                raise SystemExit(f"FAIL: registry must be a non-empty YAML object; original preserved: {path}")
            if collection_key not in data:
                entries = []
                data[collection_key] = entries
            else:
                entries = data.get(collection_key)
            if not isinstance(entries, list):
                raise SystemExit(
                    f"FAIL: registry collection {collection_key} must be a list; original preserved: {path}"
                )
        else:
            data = {"schema_version": 1, collection_key: []}
            entries = data[collection_key]
        result = upsert_resource(entries, entry)
        registry_schemas = {
            "distributions.yaml": "distributions-registry.schema.json",
            "platforms.yaml": "platform-registry.schema.json",
            "knowledge-roots.yaml": "knowledge-roots-registry.schema.json",
            "package-roots.yaml": "package-roots-registry.schema.json",
            "templates.yaml": "template-registry.schema.json",
            "tools.yaml": "tool-registry.schema.json",
            "mcp.yaml": "mcp-registry.schema.json",
            "specializations.yaml": "specialization-registry.schema.json",
            "project-classifiers.yaml": "project-classifier-registry.schema.json",
            "runtime-drivers.yaml": "runtime-driver-registry.schema.json",
            "private-resource-paths.yaml": "private-resource-paths-registry.schema.json",
            "platform-contract-roots.yaml": "platform-contract-roots-registry.schema.json",
        }
        schema_name = registry_schemas.get(path.name)
        if schema_name:
            schema_path = self.distribution_root / "schemas" / schema_name
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                errors = self._update_schema_checks.validate(data, schema, schema, "$")
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
                raise SystemExit(f"FAIL: registry schema validation unavailable for {path}: {exc}") from exc
            if errors:
                raise SystemExit(
                    f"FAIL: registry update rejected; original preserved: {path}: {'; '.join(errors[:8])}"
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(ensure_trailing_newline(dump_yaml(data)), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return result
