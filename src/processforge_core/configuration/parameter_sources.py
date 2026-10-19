"""Existing parameter sources, provenance and requirement fingerprints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.digests import FileDigestReader
from ..common.paths import rel, path_is_relative_to
from ..common.values import parameter_payload
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .parameters import ParameterMergePolicy


class ParameterSourceService:
    def record(self, source_id: str, layer: str, parameters: dict[str, Any], *, path: Path | None = None, project_root: Path | None = None, private: bool = False, display_path: str | None = None) -> dict[str, Any]:
        record: dict[str, Any] = {
            "id": source_id,
            "layer": layer,
            "keys": sorted(str(key) for key in parameters),
            "private": private,
        }
        if path:
            # Private workplace sources may contribute metadata to a public
            # snapshot, but never their absolute filesystem location. Callers can
            # supply a more specific stable marker through `display_path`.
            record["path"] = display_path or (
                rel(path, project_root)
                if project_root and path_is_relative_to(path, project_root)
                else "<private-source-ref>"
                if private
                else str(path)
            )
            record["checksum"] = "sha256:" + FileDigestReader().sha256_file(path) if path.is_file() else "missing"
        return record

    def workplace_paths(self, workplace_manifest: Path | None) -> list[Path]:
        if not workplace_manifest or not workplace_manifest.is_file():
            return []
        workplace_root = workplace_manifest.parent
        workplace_data = ContextContractInputs().load_yaml_document(workplace_manifest)
        registries = workplace_data.get("registries") if isinstance(workplace_data.get("registries"), dict) else {}
        paths: list[Path] = []
        raw_registry = registries.get("parameters") if isinstance(registries, dict) else None
        if raw_registry:
            paths.append(WorkspacePathReferenceReader(workplace_root, workplace_root, workplace_manifest=workplace_manifest).resolve_registry_relative_path(workplace_root, str(raw_registry), workplace_manifest))
        default_path = workplace_root / "registries" / "parameters.yaml"
        if default_path not in paths:
            paths.append(default_path)
        return paths

    def add(
        self,
        result: dict[str, Any],
        *,
        source_id: str,
        layer: str,
        parameters: dict[str, Any],
        path: Path | None = None,
        project_root: Path | None = None,
        private: bool = False,
        display_path: str | None = None,
    ) -> None:
        if not parameters:
            return
        result["sources"].append(self.record(source_id, layer, parameters, path=path, project_root=project_root, private=private, display_path=display_path))
        result["resolved_parameters"] = ParameterMergePolicy().merge_maps(result["resolved_parameters"], parameters, source_id, provenance=result["provenance"])

    def process_parameters(self, path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        data = ContextContractInputs().load_yaml_document(path)
        stages = data.get("stages") if isinstance(data.get("stages"), list) else []
        stage_parameters: dict[str, dict[str, Any]] = {}
        for stage in stages:
            if not isinstance(stage, dict) or not stage.get("id"):
                continue
            params = parameter_payload(stage)
            if params:
                stage_parameters[str(stage["id"])] = params
        return parameter_payload(data), stage_parameters

    def requirements_fingerprints(self, flow_root: Path, project_root: Path) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, path in {
            "process_forge_yaml": flow_root / "process-forge.yaml",
            "process_forge_local_yaml": flow_root / "process-forge.local.yaml",
        }.items():
            result[key] = "sha256:" + FileDigestReader().sha256_file(path) if path.is_file() else "missing"
        return result
