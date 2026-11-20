"""Build the existing ordered platform contract document payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.text import ensure_trailing_newline
from ..common.yaml_dump import dump_yaml


class PlatformDocumentBuilder:
    """Construct document values without performing authoring writes."""

    def build(
        self,
        target: Path,
        values: dict[str, Any],
        contract: dict[str, Any],
        root_id: str,
    ) -> list[tuple[Path, bytes, str | None]]:
        title = values["title"]
        contract_id = values["contract_id"]
        documents: list[tuple[Path, bytes, str | None]] = [
            (
                target / "platform-contract.yaml",
                ensure_trailing_newline(dump_yaml(contract)).encode("utf-8"),
                "platform-contract.schema.json",
            ),
            (
                target / "README.md",
                ensure_trailing_newline(
                    f"# {title}\n\nPlatform contract `{contract_id}`."
                ).encode("utf-8"),
                None,
            ),
            (
                target / "project-types.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "project_type_hints": values["project_types"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "capabilities.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "capabilities": contract["requires"]["capabilities"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "knowledge.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "requires": values["required_packages"],
                            "recommends": values["recommended_packages"],
                            "optional": values["optional_packages"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "templates.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "requires": values["required_templates"],
                            "recommends": values["recommended_templates"],
                            "optional": values["optional_templates"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "tools.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "requires": values["required_tools"],
                            "recommends": values["recommended_tools"],
                            "optional": values["optional_tools"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "mcp.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "requires": values["required_mcp"],
                            "recommends": values["recommended_mcp"],
                            "optional": values["optional_mcp"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "processes.yaml",
                ensure_trailing_newline(
                    dump_yaml(
                        {
                            "schema_version": 1,
                            "processes": values["processes"],
                        }
                    )
                ).encode("utf-8"),
                None,
            ),
            (
                target / "artifacts" / "platform-contract-authoring-report.md",
                ensure_trailing_newline(
                    f"# Platform Contract Authoring Report\n\n- platform: {contract_id}\n- platform_root: {root_id}"
                ).encode("utf-8"),
                None,
            ),
            (
                target / "reviews" / "platform-contract-authoring-review.md",
                ensure_trailing_newline(
                    "# Platform Contract Authoring Review\n\nResult: pass_with_conditions"
                ).encode("utf-8"),
                None,
            ),
            (
                target / "handoffs" / "platform-contract-ready-handoff.md",
                ensure_trailing_newline(
                    f"# Handoff: platform-create -> project-onboarding\n\nPlatform `{contract_id}` is ready for project type matching."
                ).encode("utf-8"),
                None,
            ),
        ]
        return documents

    def platform_contract_from_values(self, values: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": values["contract_id"],
            "title": values["title"],
            "type": "platform_contract",
            "version": values["version"],
            "status": "draft",
            "project_type_hints": values["project_types"],
            "applies_to": {
                "platforms": [values["platform_id"]],
                "project_type_hints": values["project_types"],
            },
            "requires": {
                "capabilities": ["filesystem.read", "filesystem.write"],
                "knowledge_packages": values["required_packages"],
                "tools": values["required_tools"],
                "mcp": values["required_mcp"],
                "templates": values["required_templates"],
            },
            "recommends": {
                "knowledge_packages": values["recommended_packages"],
                "templates": values["recommended_templates"],
                "tools": values["recommended_tools"],
                "mcp": values["recommended_mcp"],
            },
            "optional": {
                "knowledge_packages": values["optional_packages"],
                "templates": values["optional_templates"],
                "tools": values["optional_tools"],
                "mcp": values["optional_mcp"],
            },
            "includes": {
                "knowledge_packages": values["optional_packages"],
                "templates": values["optional_templates"],
                "tools": values["optional_tools"],
                "mcp": values["optional_mcp"],
                "processes": values["processes"],
            },
            "policies": {
                "missing_required_capability": "block",
                "missing_optional_resource": "warn",
            },
        }
