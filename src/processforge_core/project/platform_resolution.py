from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.values import parameter_payload
from ..resources.project_packages import ProjectPackageCatalogReader
from .platform_policy import PlatformContractPolicy
from .platforms import PlatformContractReader


class PlatformContractResolver:
    """Resolve platform inheritance and its project resource requirements."""

    def __init__(self, distribution_root: Path):
        self.distribution_root = distribution_root
        self._platform_contract_reader = PlatformContractReader(distribution_root)
        self._platform_contract_policy = PlatformContractPolicy(self._platform_contract_reader)
        self._package_catalog = ProjectPackageCatalogReader(distribution_root)

    def merge_ids(self, target: dict[str, str], values: list[str], owner: str, conflicts: list[dict[str, Any]]) -> None:
        for value in values:
            if value not in target:
                target[value] = owner
            elif target[value] != owner:
                conflicts.append({"id": value, "first_owner": target[value], "second_owner": owner, "resolution": "dedupe"})

    def resolve(
        self,
        workplace_manifest: Path | None,
        platform_ids: list[str],
        project_root: Path | None = None,
        contract_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        contracts_by_id: dict[str, dict[str, Any]] = {}
        platform_stack: list[dict[str, Any]] = []
        required_capabilities: set[str] = set()
        required_knowledge_packages: dict[str, str] = {}
        recommended_knowledge_packages: dict[str, str] = {}
        required_tools: dict[str, str] = {}
        recommended_tools: dict[str, str] = {}
        required_mcp: dict[str, str] = {}
        recommended_mcp: dict[str, str] = {}
        required_templates: dict[str, str] = {}
        recommended_templates: dict[str, str] = {}
        missing_required_contracts: list[str] = []
        circular_platforms: list[str] = []
        dependency_conflicts: list[dict[str, Any]] = []
        resource_conflicts: list[dict[str, Any]] = []
        resolved: set[str] = set()
        resolving: list[str] = []

        def resolve_one(raw_platform_id: str, *, relation: str = "selected", inherited_by: str | None = None, include_resources: bool = True, required: bool = True) -> None:
            contract_id = self._platform_contract_reader.contract_id(raw_platform_id)
            if contract_id in resolving:
                cycle = " -> ".join([*resolving[resolving.index(contract_id):], contract_id])
                circular_platforms.append(cycle)
                return
            if contract_id in resolved:
                return
            resolving.append(contract_id)
            if contract_overrides and contract_id in contract_overrides:
                contract = contract_overrides[contract_id]
                entry = {"id": contract_id, "status": "available", "source": "staged"}
                status = "available"
                source = "staged"
            else:
                contract, entry, status, source = self._platform_contract_reader.load(workplace_manifest, contract_id, project_root)
            extends_refs = self._platform_contract_policy.extends(contract)
            required_platform_refs = self._platform_contract_policy.required_platforms(contract)
            for ref in extends_refs:
                if ref["id"] in resolving:
                    cycle = " -> ".join([*resolving[resolving.index(ref["id"]):], ref["id"]])
                    circular_platforms.append(cycle)
                    continue
                resolve_one(ref["id"], relation="extends", inherited_by=contract_id, include_resources=True, required=bool(ref.get("required", True)))
            for ref in required_platform_refs:
                if ref["id"] in resolving:
                    cycle = " -> ".join([*resolving[resolving.index(ref["id"]):], ref["id"]])
                    circular_platforms.append(cycle)
                    continue
                resolve_one(ref["id"], relation="requires.platforms", inherited_by=contract_id, include_resources=False, required=bool(ref.get("required", True)))
            if status != "available" and required:
                missing_required_contracts.append(contract_id)
            platform_record = {
                "id": contract_id,
                "platform": contract_id.removeprefix("platform."),
                "source": source,
                "status": "available" if status == "available" else "missing",
                "relation": relation,
                "required": required,
                "inherited_by": inherited_by,
                "extends": [ref["id"] for ref in extends_refs],
                "requires_platforms": [ref["id"] for ref in required_platform_refs],
            }
            platform_stack.append(platform_record)
            if include_resources:
                required_capabilities.update(self._platform_contract_policy.required_capabilities(contract))
                owner = contract_id
                self.merge_ids(required_knowledge_packages, self._platform_contract_policy.required_items(contract, "knowledge_packages"), owner, resource_conflicts)
                self.merge_ids(recommended_knowledge_packages, self._platform_contract_policy.recommended_items(contract, "knowledge_packages"), owner, resource_conflicts)
                self.merge_ids(required_tools, self._platform_contract_policy.required_items(contract, "tools"), owner, resource_conflicts)
                self.merge_ids(recommended_tools, self._platform_contract_policy.recommended_items(contract, "tools"), owner, resource_conflicts)
                self.merge_ids(required_mcp, self._platform_contract_policy.required_items(contract, "mcp"), owner, resource_conflicts)
                self.merge_ids(recommended_mcp, self._platform_contract_policy.recommended_items(contract, "mcp"), owner, resource_conflicts)
                self.merge_ids(required_templates, self._platform_contract_policy.required_items(contract, "templates"), owner, resource_conflicts)
                self.merge_ids(recommended_templates, self._platform_contract_policy.recommended_items(contract, "templates"), owner, resource_conflicts)
            contracts_by_id[contract_id] = {
                "id": contract_id,
                "platform": contract_id.removeprefix("platform."),
                "source": source,
                "status": "available" if status == "available" else "missing",
                "registry_entry": str(entry.get("id")) if isinstance(entry, dict) and entry.get("id") else None,
                "required_contract": required,
                "relation": relation,
                "inherited_by": inherited_by,
                "extends": [ref["id"] for ref in extends_refs],
                "requires_platforms": [ref["id"] for ref in required_platform_refs],
                "required_capabilities": sorted(self._platform_contract_policy.required_capabilities(contract)),
                "required": {
                    "knowledge_packages": sorted(self._platform_contract_policy.required_items(contract, "knowledge_packages")),
                    "tools": sorted(self._platform_contract_policy.required_items(contract, "tools")),
                    "mcp": sorted(self._platform_contract_policy.required_items(contract, "mcp")),
                    "templates": sorted(self._platform_contract_policy.required_items(contract, "templates")),
                },
                "recommended": {
                    "knowledge_packages": sorted(self._platform_contract_policy.recommended_items(contract, "knowledge_packages")),
                    "tools": sorted(self._platform_contract_policy.recommended_items(contract, "tools")),
                    "mcp": sorted(self._platform_contract_policy.recommended_items(contract, "mcp")),
                    "templates": sorted(self._platform_contract_policy.recommended_items(contract, "templates")),
                },
                "optional": {
                    "knowledge_packages": sorted(self._platform_contract_policy.optional_items(contract, "knowledge_packages")),
                    "tools": sorted(self._platform_contract_policy.optional_items(contract, "tools")),
                    "mcp": sorted(self._platform_contract_policy.optional_items(contract, "mcp")),
                    "templates": sorted(self._platform_contract_policy.optional_items(contract, "templates")),
                },
                "parameters": parameter_payload(contract),
            }
            resolving.pop()
            resolved.add(contract_id)

        for platform_id in platform_ids:
            resolve_one(platform_id)

        package_index_root = project_root or (workplace_manifest.parent if workplace_manifest and workplace_manifest.is_file() else self.distribution_root)
        package_index = self._package_catalog.index(package_index_root, self.distribution_root, workplace_manifest)
        dependency_queue = list(required_knowledge_packages)
        while dependency_queue:
            package_id = dependency_queue.pop(0)
            manifest = package_index.get(package_id)
            if not isinstance(manifest, dict):
                continue
            for dependency_id in self._package_catalog.dependencies(manifest):
                if dependency_id not in required_knowledge_packages:
                    required_knowledge_packages[dependency_id] = f"package:{package_id}"
                    dependency_queue.append(dependency_id)

        required_knowledge_ids = set(required_knowledge_packages)
        recommended_knowledge_ids = set(recommended_knowledge_packages) - required_knowledge_ids
        required_tool_ids = set(required_tools)
        recommended_tool_ids = set(recommended_tools) - required_tool_ids
        required_mcp_ids = set(required_mcp)
        recommended_mcp_ids = set(recommended_mcp) - required_mcp_ids
        required_template_ids = set(required_templates)
        recommended_template_ids = set(recommended_templates) - required_template_ids
        return {
            "contracts": [contracts_by_id[item["id"]] for item in platform_stack if item["id"] in contracts_by_id],
            "platform_stack": platform_stack,
            "missing_required_contracts": sorted(set(missing_required_contracts)),
            "circular_platforms": sorted(set(circular_platforms)),
            "dependency_conflicts": dependency_conflicts,
            "resource_conflicts": resource_conflicts,
            "required_capabilities": sorted(required_capabilities),
            "required_knowledge_packages": sorted(required_knowledge_ids),
            "recommended_knowledge_packages": sorted(recommended_knowledge_ids),
            "knowledge_packages": sorted(required_knowledge_ids.union(recommended_knowledge_ids)),
            "required_tools": sorted(required_tool_ids),
            "recommended_tools": sorted(recommended_tool_ids),
            "tools": sorted(required_tool_ids.union(recommended_tool_ids)),
            "required_mcp": sorted(required_mcp_ids),
            "recommended_mcp": sorted(recommended_mcp_ids),
            "mcp": sorted(required_mcp_ids.union(recommended_mcp_ids)),
            "required_templates": sorted(required_template_ids),
            "recommended_templates": sorted(recommended_template_ids),
            "templates": sorted(required_template_ids.union(recommended_template_ids)),
        }
