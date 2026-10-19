"""Check platform resource dependencies through concrete Core catalogs."""

from __future__ import annotations

from pathlib import Path

from ..common.values import registry_ids
from ..resources.project_packages import ProjectPackageCatalogReader
from ..work.context_documents import ContextContractInputs
from .templates import TemplateCatalogService


class PlatformDependencyPreflightService:
    """Observe the supplied workplace afresh for each preflight operation."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.templates = TemplateCatalogService(distribution_root)
        self.inputs = ContextContractInputs()

    def registry_ids(self, workplace_root: Path, registry_name: str, collection_key: str) -> set[str]:
        data = self.inputs.load_yaml_document(workplace_root / "registries" / registry_name)
        return registry_ids(data, collection_key)

    def check(
        self,
        workplace_root: Path,
        required_packages: list[str],
        required_templates: list[str],
        required_tools: list[str],
        required_mcp: list[str],
    ) -> None:
        missing: list[str] = []
        for package_id in required_packages:
            if not self.packages.find_manifests(workplace_root, package_id):
                missing.append(f"knowledge package {package_id}")
        for template_id in required_templates:
            if self.templates.manifest(workplace_root, template_id) is None:
                missing.append(f"template {template_id}")
        tool_ids = self.registry_ids(workplace_root, "tools.yaml", "tools")
        mcp_ids = self.registry_ids(workplace_root, "mcp.yaml", "mcp_servers")
        missing.extend(f"tool {item}" for item in required_tools if item not in tool_ids)
        missing.extend(f"MCP {item}" for item in required_mcp if item not in mcp_ids)
        if missing:
            raise SystemExit("FAIL: required platform resources missing: " + ", ".join(missing))
