"""Ordered project parameter resolution through concrete Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.paths import path_is_relative_to
from ..common.values import parameter_payload
from ..project.overrides import PROJECT_OVERRIDE_MODES, ProjectOverrideReader
from ..project.platform_selection import ProjectPlatformSelectionService
from ..work.context_documents import ContextContractInputs
from .parameter_sources import ParameterSourceService
from .specializations import SpecializationCatalogReader


class ProjectParameterResolver:
    def __init__(self, distribution_root: Path) -> None:
        self._inputs = ContextContractInputs()
        self._parameter_source_service = ParameterSourceService()
        self._specialization_catalog_reader = SpecializationCatalogReader(distribution_root)
        self._project_override_reader = ProjectOverrideReader(distribution_root)
        self._project_platform_selection_service = ProjectPlatformSelectionService(distribution_root)

    def resolve(
        self,
        project_root: Path,
        workplace_manifest: Path | None,
        manifest_data: dict[str, Any],
        platform_resolution: dict[str, Any],
        specialization_ids: list[str],
        platform_ids: list[str],
        process_id: str | None,
        process_paths: list[Path],
    ) -> dict[str, Any]:
        flow_root = self._inputs.locate_flow_root(project_root)
        result: dict[str, Any] = {
            "status": "resolved",
            "resolved_parameters": {},
            "sources": [],
            "provenance": {},
            "conflicts": [],
        }
        if workplace_manifest and workplace_manifest.is_file():
            workplace_data = self._inputs.load_yaml_document(workplace_manifest)
            self._parameter_source_service.add(
                result,
                source_id="workplace-manifest",
                layer="workplace",
                parameters=parameter_payload(workplace_data),
                path=workplace_manifest,
                project_root=project_root,
                private=True,
                display_path="<private-workplace-manifest-ref>",
            )
            for index, path in enumerate(self._parameter_source_service.workplace_paths(workplace_manifest)):
                data = self._inputs.load_yaml_document(path)
                self._parameter_source_service.add(
                    result,
                    source_id=f"workplace-parameters-{index + 1}",
                    layer="workplace",
                    parameters=parameter_payload(data),
                    path=path,
                    project_root=project_root,
                    private=True,
                    display_path=f"<private-workplace-ref>/{path.relative_to(workplace_manifest.parent).as_posix()}" if path_is_relative_to(path, workplace_manifest.parent) else "<private-workplace-parameters-ref>",
                )
        for contract in platform_resolution.get("contracts", []) if isinstance(platform_resolution.get("contracts"), list) else []:
            if isinstance(contract, dict):
                self._parameter_source_service.add(
                    result,
                    source_id=f"platform:{contract.get('id', 'unknown')}",
                    layer="platform",
                    parameters=parameter_payload(contract),
                )
        index = self._specialization_catalog_reader.manifest_index(workplace_manifest, project_root)
        for specialization_id in [self._specialization_catalog_reader.resource_id(item) for item in specialization_ids if str(item)]:
            spec = index.get(specialization_id)
            if not isinstance(spec, dict):
                continue
            for override_entry in self._project_override_reader.project_specialization_override_entries(project_root, specialization_id):
                mode = str(override_entry.get("mode") or "extension")
                if mode not in PROJECT_OVERRIDE_MODES:
                    result["conflicts"].append({"id": specialization_id, "kind": "specialization", "reason": f"unsupported project override mode: {mode}"})
                    continue
                overlay = self._project_override_reader.load_project_override_document(project_root, override_entry)
                if overlay:
                    spec, _overlay_notes = self._project_override_reader.apply_specialization_overlay(spec, overlay, mode)
            self._parameter_source_service.add(
                result,
                source_id=f"specialization:{specialization_id}",
                layer="specialization",
                parameters=parameter_payload(spec),
                path=spec.get("__manifest_path") if isinstance(spec.get("__manifest_path"), Path) else None,
                project_root=project_root,
                private=str(spec.get("__source") or "") == "workplace",
            )
            for binding_index, binding in enumerate(spec.get("platform_bindings", []) if isinstance(spec.get("platform_bindings"), list) else []):
                if isinstance(binding, dict) and self._project_platform_selection_service.binding_matches(binding, platform_ids, platform_resolution.get("platform_stack", []), process_id):
                    self._parameter_source_service.add(
                        result,
                        source_id=f"specialization:{specialization_id}:binding:{binding_index + 1}",
                        layer="specialization",
                        parameters=parameter_payload(binding),
                    )
        self._parameter_source_service.add(result, source_id="project-manifest", layer="project", parameters=parameter_payload(manifest_data), path=flow_root / "process-forge.yaml", project_root=project_root)
        project_parameters = flow_root / "parameters.yaml"
        self._parameter_source_service.add(result, source_id="project-parameters", layer="project", parameters=parameter_payload(self._inputs.load_yaml_document(project_parameters)), path=project_parameters, project_root=project_root)
        local_config = flow_root / "process-forge.local.yaml"
        local_data = self._inputs.load_yaml_document(local_config)
        local_overrides = local_data.get("overrides") if isinstance(local_data.get("overrides"), dict) else {}
        self._parameter_source_service.add(result, source_id="project-local-overrides", layer="project", parameters=parameter_payload(local_overrides), path=local_config, project_root=project_root, private=True)
        project_local_parameters = flow_root / "parameters.local.yaml"
        self._parameter_source_service.add(result, source_id="project-local-parameters", layer="project", parameters=parameter_payload(self._inputs.load_yaml_document(project_local_parameters)), path=project_local_parameters, project_root=project_root, private=True)
        for index, path in enumerate(process_paths):
            parameters, _stage_parameters = self._parameter_source_service.process_parameters(path)
            self._parameter_source_service.add(result, source_id=f"process:{path.stem}:{index + 1}", layer="process", parameters=parameters, path=path, project_root=project_root)
        if result["conflicts"]:
            result["status"] = "conflict"
        return result
