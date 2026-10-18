"""Read process route documents and validate existing process contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.paths import rel
from processforge_core.common.values import as_list, string_list
from processforge_core.common.yaml_io import _parse_simple_yaml, yaml_error
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.project.metadata import ProjectMetadataReader

from .artifacts import ProcessArtifactDeclarationPolicy
from .coordination import PROCESS_COORDINATION_MODES
from .evolution import ProcessEvolutionPolicy
from .service import (
    PROCESS_CATALOG_CLASSIFICATIONS,
    process_catalog_metadata,
    process_is_public_stable,
)
from .validation import ERROR_WORKFLOW_MODES, ProcessAuthoringValidationService

HANDOFF_MODES = {"wait_for_result", "delegate_and_continue", "consultation", "final_transfer", "fork", "return_required"}


class ProcessRouteDocumentReader:
    """Read current project routes with the existing soft YAML semantics."""

    def __init__(self) -> None:
        self.documents = YamlDocumentReader(_parse_simple_yaml)

    def path(self, project_root: Path) -> Path:
        return ProjectMetadataReader(project_root, documents=self.documents).flow_root() / "process-routes.yaml"

    def read(self, project_root: Path) -> dict[str, Any]:
        data = self.documents.load(self.path(project_root))
        if yaml_error(data) or not data:
            return {"schema_version": 1, "routes": []}
        data.setdefault("schema_version", 1)
        data.setdefault("routes", [])
        return data


class ProcessContractValidationService:
    """Validate process contracts using concrete Core policies and readers."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self._routes = ProcessRouteDocumentReader()
        self._evolution = ProcessEvolutionPolicy()
        self._artifacts = ProcessArtifactDeclarationPolicy()
        self._authoring = ProcessAuthoringValidationService()

    def validate(
        self,
        project_root: Path,
        process: dict[str, Any],
        process_path: Path,
        *,
        strict: bool = False,
        companion_root: Path | None = None,
    ) -> list[Check]:
        process_id = str(process.get("id") or process_path.stem)
        meta = process_catalog_metadata(process)
        stable = process_is_public_stable(process)
        hard = strict or stable
        checks: list[Check] = []
        checks.append(check("PASS" if meta["classification"] in PROCESS_CATALOG_CLASSIFICATIONS else "FAIL", f"{process_id} catalog classification valid"))
        checks.append(check("PASS" if process.get("execution_mode") in {"single_agent", "single_agent_with_subagents", "orchestrated_agents", "process_factory"} else ("FAIL" if hard else "WARN"), f"{process_id} execution_mode declared"))
        coordination = process.get("coordination_requirements") if isinstance(process.get("coordination_requirements"), dict) else {}
        checks.append(check("PASS" if coordination.get("mode") in PROCESS_COORDINATION_MODES else ("FAIL" if hard else "WARN"), f"{process_id} coordination_requirements.mode declared"))
        error_handling = process.get("error_handling") if isinstance(process.get("error_handling"), dict) else {}
        checks.append(check("PASS" if error_handling.get("mode") in ERROR_WORKFLOW_MODES and "enabled" in error_handling else ("FAIL" if hard else "WARN"), f"{process_id} error_handling declared"))
        checks.extend(self._evolution.validate_block(process_id, process.get("evolve"), hard=hard))
        checks.append(check("PASS" if isinstance(process.get("responsibility_boundaries"), dict) else ("FAIL" if hard else "WARN"), f"{process_id} responsibility_boundaries declared"))
        if process.get("execution_mode") in {"single_agent_with_subagents", "orchestrated_agents"}:
            checks.append(check("PASS" if isinstance(process.get("subagent_policy"), dict) else ("FAIL" if hard else "WARN"), f"{process_id} subagent_policy declared"))
        if process.get("execution_mode") == "orchestrated_agents":
            runtime_requirements = process.get("runtime_requirements") if isinstance(process.get("runtime_requirements"), dict) else {}
            checks.append(check("PASS" if "supervisor_required" in runtime_requirements or coordination.get("mode") != "organized_required" else ("FAIL" if hard else "WARN"), f"{process_id} runtime requirements declared where needed"))

        for role in as_list(process.get("roles")):
            if not isinstance(role, dict):
                checks.append(check("FAIL" if hard else "WARN", f"{process_id} role entry is not an object"))
                continue
            label = f"{process_id} role {role.get('id', '<missing>')}"
            checks.append(check("PASS" if role.get("kind") else ("FAIL" if hard else "WARN"), f"{label} kind declared"))
            responsibilities = role.get("responsibilities")
            if responsibilities is None and role.get("responsibility"):
                responsibilities = [role.get("responsibility")]
            checks.append(check("PASS" if string_list(responsibilities) else ("FAIL" if hard else "WARN"), f"{label} responsibilities declared"))

        defined_artifacts = self._artifacts.declared_ids(process)
        evidence_ids = {str(item.get("id")) for item in as_list(process.get("evidence_definitions")) if isinstance(item, dict) and item.get("id")}
        produced = self._artifacts.produced_ids(process)
        missing = sorted(produced - defined_artifacts)
        checks.append(check("PASS" if not missing else ("FAIL" if hard else "WARN"), f"{process_id} produced artifacts declared: {', '.join(missing) if missing else 'all'}"))
        gate_ids = {str(item.get("id")) for item in as_list(process.get("gates")) if isinstance(item, dict) and item.get("id")}
        for gate in as_list(process.get("gates")):
            if isinstance(gate, dict) and gate.get("required_artifact"):
                artifact_id = str(gate.get("required_artifact"))
                checks.append(check("PASS" if artifact_id in defined_artifacts else ("FAIL" if hard else "WARN"), f"{process_id} gate {gate.get('id', '')} required artifact declared: {artifact_id}"))
        for stage in as_list(process.get("stages")):
            if not isinstance(stage, dict):
                continue
            stage_id = str(stage.get("id") or "stage")
            checks.append(check("PASS" if stage.get("actor") else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} actor declared"))
            checks.append(check("PASS" if stage.get("goal") else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} goal declared"))
            unknown_gates = sorted(set(string_list(stage.get("entry_gates")) + string_list(stage.get("gates")) + string_list(stage.get("exit_gates"))) - gate_ids)
            checks.append(check("PASS" if not unknown_gates else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} gates valid: {', '.join(unknown_gates) if unknown_gates else 'all'}"))
            for field in ["required_inputs", "produced_artifacts", "required_artifacts"]:
                unknown_artifacts = sorted(set(string_list(stage.get(field))) - defined_artifacts)
                checks.append(check("PASS" if not unknown_artifacts else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} {field} valid: {', '.join(unknown_artifacts) if unknown_artifacts else 'all'}"))
            unknown_evidence = sorted(set(string_list(stage.get("required_evidence"))) - evidence_ids)
            checks.append(check("PASS" if not unknown_evidence else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} evidence valid: {', '.join(unknown_evidence) if unknown_evidence else 'all'}"))
            if stage.get("gates"):
                checks.append(check("WARN", f"{process_id}.{stage_id} uses deprecated gates alias"))
            if stage.get("technical_obligations"):
                checks.append(check("WARN", f"{process_id}.{stage_id} uses deprecated technical_obligations alias"))
            for binding in as_list(stage.get("automation_bindings")):
                if not isinstance(binding, dict):
                    checks.append(check("FAIL" if hard else "WARN", f"{process_id}.{stage_id} automation binding is object"))
                    continue
                binding_id = str(binding.get("id") or "binding")
                checks.append(check("PASS" if binding.get("projector") else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} automation binding {binding_id} projector declared"))
                if binding.get("artifact"):
                    checks.append(check("PASS" if str(binding.get("artifact")) in defined_artifacts else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} automation binding {binding_id} artifact valid"))
                if binding.get("gate"):
                    checks.append(check("PASS" if str(binding.get("gate")) in gate_ids else ("FAIL" if hard else "WARN"), f"{process_id}.{stage_id} automation binding {binding_id} gate valid"))
            if "handoff_required" in stage:
                checks.append(check("FAIL" if hard else "WARN", f"{process_id}.{stage_id} deprecated handoff_required used without explicit semantics"))
        if "handoff_required" in process:
            checks.append(check("FAIL" if hard else "WARN", f"{process_id} deprecated handoff_required used without explicit semantics"))
        transitions = as_list(process.get("process_transitions"))
        route_file = self._routes.path(project_root)
        route_map = self._routes.read(project_root) if route_file.is_file() else {"routes": []}
        routes_by_id = {
            str(route.get("id") or ""): route
            for route in as_list(route_map.get("routes"))
            if isinstance(route, dict) and route.get("id")
        }
        transition_ids: set[str] = set()
        for transition in transitions:
            if not isinstance(transition, dict):
                checks.append(check("FAIL" if hard else "WARN", f"{process_id} transition is an object"))
                continue
            transition_id = str(transition.get("id") or "")
            checks.append(check("PASS" if transition_id and transition_id not in transition_ids else ("FAIL" if hard else "WARN"), f"{process_id} transition id unique: {transition_id or 'missing'}"))
            transition_ids.add(transition_id)
            checks.append(check("PASS" if str(transition.get("from_process") or "") == process_id else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} starts from declaring process"))
            checks.append(check("PASS" if transition.get("to_process") else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} target declared"))
            checks.append(check("PASS" if str(transition.get("mode") or "") in HANDOFF_MODES else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} mode valid"))
            route_id = str(transition.get("route_id") or "")
            if route_id:
                checks.append(check("PASS" if route_file.is_file() else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} route map exists"))
                route = routes_by_id.get(route_id)
                checks.append(check("PASS" if route is not None else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} route exists: {route_id}"))
                if route is not None:
                    same_contract = (
                        str(route.get("from_process") or "") == process_id
                        and str(route.get("to_process") or "") == str(transition.get("to_process") or "")
                        and str(route.get("mode") or "") == str(transition.get("mode") or "")
                    )
                    checks.append(check("PASS" if same_contract else ("FAIL" if hard else "WARN"), f"{process_id} transition {transition_id or 'missing'} route contract matches: {route_id}"))

        companions = self._authoring.paths(companion_root or project_root, process_id)
        pack = process.get("process_pack") if isinstance(process.get("process_pack"), dict) else {}
        agent_prompt = process.get("agent_prompt") if isinstance(process.get("agent_prompt"), dict) else {}
        prompt_required = bool(agent_prompt.get("required", True))
        if stable:
            checks.append(check("PASS" if companions["prompt"].is_file() or not prompt_required else "FAIL", f"{rel(companions['prompt'], project_root)} exists or is explicitly exempt"))
            checks.append(check("PASS" if companions["doc"].is_file() else "FAIL", f"{rel(companions['doc'], project_root)} exists"))
            example_required = bool(pack.get("example_required", True))
            checks.append(check("PASS" if companions["example"].is_file() or not example_required else "FAIL", f"{rel(companions['example'], project_root)} exists or is explicitly exempt"))
        else:
            checks.append(check("PASS", f"{process_id} companion completeness not strict for {meta['classification']}"))

        for template_id in string_list(process.get("required_templates")):
            template_ref = Path(template_id)
            candidates = [
                project_root / "templates" / template_ref,
                project_root / "templates" / f"{template_id}.yaml",
                project_root / "templates" / f"{template_id}.md",
                self.distribution_root / "templates" / template_ref,
                self.distribution_root / "templates" / f"{template_id}.yaml",
                self.distribution_root / "templates" / f"{template_id}.md",
            ]
            checks.append(check("PASS" if any(candidate.is_file() for candidate in candidates) else ("FAIL" if hard else "WARN"), f"{process_id} required template exists: {template_id}"))
        return checks
