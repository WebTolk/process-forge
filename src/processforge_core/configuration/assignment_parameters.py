"""Assignment and stage parameters resolved with the concrete process catalog."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..common.values import parameter_payload
from ..process_catalog.catalog_read import ProcessCatalogReadService
from .parameter_sources import ParameterSourceService


class AssignmentParameterResolver:
    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self._parameter_source_service = ParameterSourceService()

    def resolve(self, project_root: Path, snapshot: dict[str, Any], assignment_metadata: dict[str, Any]) -> dict[str, Any]:
        base = snapshot.get("resolved_parameters") if isinstance(snapshot.get("resolved_parameters"), dict) else {}
        snapshot_resolution = snapshot.get("parameter_resolution") if isinstance(snapshot.get("parameter_resolution"), dict) else {}
        result: dict[str, Any] = {
            "status": "resolved",
            "resolved_parameters": copy.deepcopy(base),
            "sources": copy.deepcopy(snapshot_resolution.get("sources", [])) if isinstance(snapshot_resolution.get("sources"), list) else [],
            "provenance": copy.deepcopy(snapshot_resolution.get("provenance", {})) if isinstance(snapshot_resolution.get("provenance"), dict) else {},
            "conflicts": copy.deepcopy(snapshot_resolution.get("conflicts", [])) if isinstance(snapshot_resolution.get("conflicts"), list) else [],
        }
        process_ref = assignment_metadata.get("process")
        process_id = str(process_ref.get("id") if isinstance(process_ref, dict) else process_ref or "")
        stage_id = str(assignment_metadata.get("stage") or "")
        if process_id:
            try:
                process_path = ProcessCatalogReadService(project_root, distribution_root=self.distribution_root).resolve_definition(process_id).path
                process_parameters, stage_parameters = self._parameter_source_service.process_parameters(process_path)
                self._parameter_source_service.add(result, source_id=f"assignment-process:{process_id}", layer="process", parameters=process_parameters, path=process_path, project_root=project_root)
                if stage_id and stage_id in stage_parameters:
                    self._parameter_source_service.add(result, source_id=f"assignment-stage:{process_id}:{stage_id}", layer="stage", parameters=stage_parameters[stage_id], path=process_path, project_root=project_root)
            except SystemExit:
                result["conflicts"].append({"id": process_id, "kind": "process", "reason": "assignment process parameters could not be loaded"})
        self._parameter_source_service.add(result, source_id="assignment", layer="task", parameters=parameter_payload(assignment_metadata))
        if result["conflicts"]:
            result["status"] = "conflict"
        return result
