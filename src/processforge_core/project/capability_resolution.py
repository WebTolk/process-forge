"""Existing project capability providers, execution routes and satisfaction rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.values import as_list
from ..process_catalog.catalog_read import ProcessCatalogReadService
from ..process_catalog.official_read import OfficialProcessPackReader
from ..resources.buckets import RESOURCE_GROUP_KEYS, dedupe_sorted, resource_bucket
from .capability_registry import CapabilityRegistryReader as _CapabilityRegistryReader
from ..resources.registries import WorkplaceRegistryReader


class ProjectCapabilityResolution:
    """Resolve with explicit distribution roots and live concrete Core readers."""

    def __init__(self, distribution_root: Path) -> None:
        self._distribution_root = distribution_root
        self._registry_reader = WorkplaceRegistryReader()

    def resource_profile_capability_provider(self, specialization_id: str, resources: dict[str, Any]) -> dict[str, Any]:
        provider: dict[str, Any] = {"specialization": specialization_id}
        for key in RESOURCE_GROUP_KEYS:
            values: set[str] = set()
            for bucket in ["requires", "recommends", "optional"]:
                values.update(resource_bucket(resources, bucket, key))
            provider[key] = dedupe_sorted(list(values))
        return provider

    def active_registry_capability_providers(
        self,
        workplace_manifest: Path | None,
        activated: dict[str, set[str]],
    ) -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
        capabilities: set[str] = set()
        providers: dict[str, list[dict[str, Any]]] = {}
        registry_specs = [
            ("tools", "tools", "tool", "tools"),
            ("mcp", "mcp_servers", "mcp", "mcp"),
            ("templates", "templates", "template", "templates"),
            ("templates", "template_roots", "template", "templates"),
        ]
        for registry_key, collection_key, provider_key, resource_key in registry_specs:
            registry = self._registry_reader.load_workplace_registry(workplace_manifest, registry_key, f"{registry_key}.yaml")
            entries = registry.get(collection_key) if isinstance(registry, dict) else None
            if not isinstance(entries, list):
                continue
            active_ids = activated.get(resource_key, set())
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                resource_id = str(entry.get("id") or "")
                if not resource_id or resource_id not in active_ids:
                    continue
                if str(entry.get("status") or "available") in {"disabled", "missing"}:
                    continue
                provided = _CapabilityRegistryReader.values(entry)
                capabilities.update(provided)
                for capability in provided:
                    providers.setdefault(capability, []).append({"provider": "registry", provider_key: resource_id})
        pack_capabilities, pack_providers = self.official_pack_capability_providers(workplace_manifest)
        capabilities.update(pack_capabilities)
        for capability, items in pack_providers.items():
            providers.setdefault(capability, []).extend(items)
        return capabilities, providers

    def build_execution_route(self, project_root: Path, process_id: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        route: dict[str, Any] = {
            "process": process_id or "",
            "stages": [],
            "required_capabilities": [],
            "capability_requirements": [],
            "required_artifacts": [],
            "required_evidence": [],
            "acceptance_criteria": [],
        }
        if not process_id:
            return route, []
        try:
            process_ref = ProcessCatalogReadService(project_root, distribution_root=self._distribution_root).resolve_definition(process_id)
        except SystemExit:
            return route, []
        process = process_ref.process if isinstance(process_ref.process, dict) else {}
        route["process"] = str(process.get("id") or process_ref.process_id or process_id)
        top_required_capabilities = [str(item) for item in as_list(process.get("required_capabilities")) if str(item)]
        capability_requirements: list[dict[str, Any]] = [
            {"capability": item, "required_by": f"process:{route['process']}"}
            for item in top_required_capabilities
        ]
        required_artifacts: set[str] = set(str(item) for item in as_list(process.get("required_artifacts")) if str(item))
        required_evidence: set[str] = set(str(item) for item in as_list(process.get("required_evidence")) if str(item))
        acceptance = process.get("acceptance") if isinstance(process.get("acceptance"), dict) else {}
        if acceptance:
            required_evidence.update(str(item) for item in as_list(acceptance.get("requires")) if str(item))
            route["acceptance_criteria"] = [str(item) for item in as_list(acceptance.get("criteria")) if str(item)]
        stages: list[dict[str, Any]] = []
        for stage in process.get("stages", []) if isinstance(process.get("stages"), list) else []:
            if not isinstance(stage, dict):
                continue
            stage_id = str(stage.get("id") or "stage")
            stage_capabilities = [str(item) for item in as_list(stage.get("required_capabilities")) if str(item)]
            stage_artifacts = [str(item) for item in as_list(stage.get("required_artifacts")) if str(item)]
            stage_evidence = [str(item) for item in as_list(stage.get("required_evidence")) if str(item)]
            required_artifacts.update(stage_artifacts)
            required_evidence.update(stage_evidence)
            for capability in stage_capabilities:
                capability_requirements.append({"capability": capability, "required_by": f"{route['process']}:{stage_id}"})
            stages.append(
                {
                    "id": stage_id,
                    "required_capabilities": stage_capabilities,
                    "required_artifacts": stage_artifacts,
                    "required_evidence": stage_evidence,
                    "exit_gates": [str(item) for item in as_list(stage.get("exit_gates")) if str(item)],
                }
            )
        route["stages"] = stages
        route["capability_requirements"] = capability_requirements
        route["required_capabilities"] = dedupe_sorted([item["capability"] for item in capability_requirements])
        route["required_artifacts"] = dedupe_sorted(list(required_artifacts))
        route["required_evidence"] = dedupe_sorted(list(required_evidence))
        return route, []

    def build_capability_resolution(
        self,
        execution_route: dict[str, Any],
        provided_capabilities: set[str],
        capability_providers: dict[str, list[dict[str, Any]]],
        activated: dict[str, set[str]],
    ) -> dict[str, list[dict[str, Any]]]:
        satisfied: list[dict[str, Any]] = []
        unsatisfied: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for requirement in execution_route.get("capability_requirements", []) if isinstance(execution_route.get("capability_requirements"), list) else []:
            if not isinstance(requirement, dict):
                continue
            capability = str(requirement.get("capability") or "")
            required_by = str(requirement.get("required_by") or execution_route.get("process") or "")
            if not capability or (capability, required_by) in seen:
                continue
            seen.add((capability, required_by))
            if capability in provided_capabilities:
                provider = dict((capability_providers.get(capability) or [{"provider": "active_resource_profile"}])[0])
                for key in RESOURCE_GROUP_KEYS:
                    provider[key] = [item for item in as_list(provider.get(key)) if item in activated.get(key, set())]
                satisfied.append({"capability": capability, "required_by": required_by, "satisfied_by": provider})
            else:
                unsatisfied.append(
                    {
                        "capability": capability,
                        "required_by": required_by,
                        "reason": "selected resource profile does not provide required capability",
                        "suggested_fix": "select or update a specialization/platform binding that provides this capability",
                    }
                )
        return {"satisfied": satisfied, "unsatisfied": unsatisfied}

    def official_pack_capability_providers(
        self,
        workplace_manifest: Path | None,
    ) -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
        capabilities: set[str] = set()
        providers: dict[str, list[dict[str, Any]]] = {}
        for _path, manifest in OfficialProcessPackReader(workplace_manifest, distribution_root=self._distribution_root).active_records():
            pack_id = str(manifest.get("id") or "")
            provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
            declared = {str(item) for item in as_list(provided.get("capabilities")) if str(item)}
            for tool in as_list(provided.get("tools")):
                if isinstance(tool, dict):
                    declared.update(_CapabilityRegistryReader.values(tool))
            capabilities.update(declared)
            for capability in declared:
                providers.setdefault(capability, []).append(
                    {"provider": "active_process_pack", "process_pack": pack_id}
                )
        return capabilities, providers
