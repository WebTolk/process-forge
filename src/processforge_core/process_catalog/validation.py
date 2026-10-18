"""Validate authored process definitions and their companion files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.ids import safe_id
from processforge_core.common.paths import rel
from processforge_core.common.privacy import (
    contains_secret_value,
    is_public_path_safe,
    public_yaml_has_private_path,
)
from processforge_core.common.values import as_list, string_list
from processforge_core.process_catalog.artifacts import ProcessArtifactDeclarationPolicy
from processforge_core.process_catalog.coordination import PROCESS_COORDINATION_MODES
from processforge_core.process_catalog.evolution import ProcessEvolutionPolicy


ERROR_WORKFLOW_MODES = {"none", "director_inbox", "route_to_process", "needs_operator"}
ERROR_WORKFLOW_FALLBACKS = {"needs_operator", "fail_validation"}
ITERATION_KINDS = {"work", "debug", "fix", "review", "test", "research", "handoff", "note"}


class ProcessAuthoringValidationService:
    def __init__(self) -> None:
        self._evolution = ProcessEvolutionPolicy()
        self._artifacts = ProcessArtifactDeclarationPolicy()

    def logic(self, process: dict[str, Any], answers: dict[str, Any] | None = None) -> list[Check]:
        checks: list[Check] = []
        text = json.dumps({"process": process, "answers": answers or {}}, ensure_ascii=False)
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "authoring data has no private absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "authoring data contains no secret-like values"))
        for key in ["schema_version", "id", "name", "version", "status", "description", "stages", "roles", "artifact_definitions", "gates", "evolution_policy"]:
            checks.append(check("PASS" if key in process else "FAIL", f"process.{key} present"))
        checks.extend(self._evolution.validate_block(str(process.get("id") or "process"), process.get("evolve"), hard=bool(answers and "evolve" in answers)))
        if answers is not None and answers and "evolve" not in answers:
            checks.append(check("FAIL", "authoring answers include explicit evolve decision"))
        execution_mode = str(process.get("execution_mode") or "single_agent")
        checks.append(check("PASS" if execution_mode in {"single_agent", "single_agent_with_subagents", "orchestrated_agents", "process_factory"} else "FAIL", f"process.execution_mode valid: {execution_mode}"))
        coordination_requirements = process.get("coordination_requirements") if isinstance(process.get("coordination_requirements"), dict) else {}
        coordination_mode = str(coordination_requirements.get("mode") or "simple_allowed")
        checks.append(check("PASS" if coordination_mode in PROCESS_COORDINATION_MODES else "FAIL", f"process.coordination_requirements.mode valid: {coordination_mode}"))
        director_inbox = coordination_requirements.get("director_inbox") if isinstance(coordination_requirements.get("director_inbox"), dict) else {}
        if coordination_mode == "simple_allowed" and bool(director_inbox.get("required", False)):
            checks.append(check("FAIL", "simple_allowed process must not require Director inbox"))
        error_workflow = coordination_requirements.get("error_workflow") if isinstance(coordination_requirements.get("error_workflow"), dict) else {}
        error_workflow_mode = str(error_workflow.get("mode") or "none")
        checks.append(check("PASS" if error_workflow_mode in ERROR_WORKFLOW_MODES else "FAIL", f"process.coordination_requirements.error_workflow.mode valid: {error_workflow_mode}"))
        error_handling = process.get("error_handling") if isinstance(process.get("error_handling"), dict) else {}
        if error_handling:
            handling_mode = str(error_handling.get("mode") or "none")
            fallback = str(error_handling.get("fallback_if_no_director") or "needs_operator")
            checks.append(check("PASS" if handling_mode in ERROR_WORKFLOW_MODES else "FAIL", f"process.error_handling.mode valid: {handling_mode}"))
            checks.append(check("PASS" if fallback in ERROR_WORKFLOW_FALLBACKS else "FAIL", f"process.error_handling.fallback_if_no_director valid: {fallback}"))
        roles = [item for item in as_list(process.get("roles")) if isinstance(item, dict)]
        stages = [item for item in as_list(process.get("stages")) if isinstance(item, dict)]
        artifacts = [item for item in as_list(process.get("artifact_definitions")) if isinstance(item, dict)]
        evidence = [item for item in as_list(process.get("evidence_definitions")) if isinstance(item, dict)]
        gates = [item for item in as_list(process.get("gates")) if isinstance(item, dict)]

        def id_values(items: list[dict[str, Any]], label: str) -> set[str]:
            values: list[str] = [safe_id(str(item.get("id", "")), label) for item in items]
            duplicates = sorted({item for item in values if values.count(item) > 1})
            checks.append(check("PASS" if not duplicates else "FAIL", f"{label} ids unique" + (f": {', '.join(duplicates)}" if duplicates else "")))
            return set(values)

        role_ids = id_values(roles, "role")
        artifact_ids = id_values(artifacts, "artifact")
        declared_artifact_ids = self._artifacts.declared_ids(process)
        evidence_ids = id_values(evidence, "evidence") if evidence else set()
        gate_ids = id_values(gates, "gate")
        stage_ids = id_values(stages, "stage")
        checks.append(check("PASS" if stage_ids else "FAIL", "at least one stage exists"))
        checks.append(check("PASS" if role_ids else "FAIL", "at least one role exists"))
        checks.append(check("PASS" if artifact_ids else "FAIL", "at least one artifact exists"))
        checks.append(check("PASS" if gate_ids else "FAIL", "at least one gate exists"))

        for stage in stages:
            stage_id = safe_id(str(stage.get("id", "")), "stage")
            role_id = safe_id(str(stage.get("required_role", "")), "role")
            checks.append(check("PASS" if role_id in role_ids else "FAIL", f"stage {stage_id} references existing role"))
            for field in ["required_inputs", "produced_artifacts", "required_artifacts"]:
                for artifact_id in [safe_id(value, "artifact") for value in string_list(stage.get(field))]:
                    checks.append(check("PASS" if artifact_id in declared_artifact_ids else "FAIL", f"stage {stage_id} {field} references known artifact {artifact_id}"))
            for evidence_id in [safe_id(value, "evidence") for value in string_list(stage.get("required_evidence"))]:
                checks.append(check("PASS" if evidence_id in evidence_ids else "FAIL", f"stage {stage_id} references known evidence {evidence_id}"))
            for gate_id in [safe_id(value, "gate") for value in string_list(stage.get("entry_gates")) + string_list(stage.get("exit_gates"))]:
                checks.append(check("PASS" if gate_id in gate_ids else "FAIL", f"stage {stage_id} references known gate {gate_id}"))
            if stage.get("gates"):
                checks.append(check("WARN", f"stage {stage_id} uses deprecated gates alias; use exit_gates"))
            if stage.get("technical_obligations"):
                checks.append(check("WARN", f"stage {stage_id} uses deprecated technical_obligations; use automation_bindings"))
            for binding in as_list(stage.get("automation_bindings")):
                if not isinstance(binding, dict):
                    checks.append(check("FAIL", f"stage {stage_id} automation binding is an object"))
                    continue
                binding_id = safe_id(str(binding.get("id") or ""), "binding")
                checks.append(check("PASS" if binding.get("projector") else "FAIL", f"stage {stage_id} automation binding {binding_id} projector declared"))
                if binding.get("artifact"):
                    artifact_id = safe_id(str(binding.get("artifact")), "artifact")
                    checks.append(check("PASS" if artifact_id in declared_artifact_ids else "FAIL", f"automation binding {binding_id} artifact exists: {artifact_id}"))
                if binding.get("gate"):
                    gate_id = safe_id(str(binding.get("gate")), "gate")
                    checks.append(check("PASS" if gate_id in gate_ids else "FAIL", f"automation binding {binding_id} gate exists: {gate_id}"))
        for artifact in artifacts:
            owner = safe_id(str(artifact.get("owner_role", "")), "role")
            checks.append(check("PASS" if owner in role_ids else "FAIL", f"artifact {artifact.get('id', '')} owner role exists"))
        for gate_item in gates:
            gate_id = safe_id(str(gate_item.get("id", "")), "gate")
            required_artifact = gate_item.get("required_artifact")
            if required_artifact:
                artifact_id = safe_id(str(required_artifact), "artifact")
                checks.append(check("PASS" if artifact_id in artifact_ids else "FAIL", f"gate {gate_id} required artifact exists: {artifact_id}"))
        run_model = process.get("run_model") if isinstance(process.get("run_model"), dict) else {}
        task_loop = run_model.get("default_task_loop") if isinstance(run_model.get("default_task_loop"), dict) else {}
        if run_model.get("supports_multiple_tasks") is True:
            loop_enabled = task_loop.get("enabled") is True
            kinds = string_list(task_loop.get("iteration_kinds"))
            checks.append(check("PASS" if loop_enabled and kinds else "FAIL", "multiple-task processes define a default task loop"))
            for kind in kinds:
                checks.append(check("PASS" if kind in ITERATION_KINDS else "FAIL", f"default task loop iteration kind valid: {kind}"))
        return checks

    def files(
        self,
        project_root: Path,
        process: dict[str, Any],
        process_path: Path,
        *,
        companion_root: Path | None = None,
    ) -> list[Check]:
        process_id = str(process.get("id") or process_path.stem)
        checks = self.logic(process, {})
        checks.append(check("PASS" if not public_yaml_has_private_path(process) else "FAIL", f"{rel(process_path, project_root)} has no private absolute paths"))
        companions = self.paths(companion_root or project_root, process_id)
        prompt = companions["prompt"]
        doc = companions["doc"]
        example = companions["example"]
        pack = process.get("process_pack") if isinstance(process.get("process_pack"), dict) else {}
        example_required = bool(pack.get("example_required", True))
        checks.append(check("PASS" if prompt.is_file() else "FAIL", f"{rel(prompt, project_root)} exists"))
        checks.append(check("PASS" if doc.is_file() else "FAIL", f"{rel(doc, project_root)} exists"))
        checks.append(check("PASS" if example.is_file() or not example_required else "FAIL", f"{rel(example, project_root)} exists or is explicitly exempt"))
        return checks

    def paths(self, root: Path, process_id: str) -> dict[str, Path]:
        return {
            "process": root / "processes" / f"{process_id}.yaml",
            "prompt": root / "prompts" / f"{process_id}-agent.md",
            "doc": root / "docs" / "processes" / f"{process_id}.md",
            "example": root / "examples" / "process-authoring" / process_id / "README.md",
        }

