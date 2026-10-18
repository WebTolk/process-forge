from __future__ import annotations

from typing import Any

from processforge_core.common.ids import safe_id, title_from_id
from processforge_core.common.values import as_list, string_list
from processforge_core.process_catalog.evolution import ProcessEvolutionPolicy


class ProcessAuthoringDefinitionBuilder:
    def __init__(self) -> None:
        self._evolution = ProcessEvolutionPolicy()

    def defaults(self, process_id: str, title: str, description: str = "") -> dict[str, Any]:
        process_id = safe_id(process_id, "new-process")
        title = title or title_from_id(process_id)
        return {
            "schema_version": 1,
            "process": {
                "id": process_id,
                "name": title,
                "version": "1.0.0",
                "status": "draft",
                "kind": "project_process",
                "scope": "project",
                "description": description or f"Guide repeatable work for {title}.",
            },
            "run_model": {
                "supports_multiple_tasks": False,
                "default_task_loop": {
                    "enabled": False,
                    "iteration_kinds": ["work", "debug", "fix", "review", "handoff"],
                },
            },
            "execution_mode": "single_agent",
            "execution_mode_questions": {},
            "coordination_requirements": {
                "mode": "simple_allowed",
                "director_inbox": {"required": False, "optional": False},
                "error_workflow": {"mode": "none"},
                "simple_mode_behavior": "disable_director_features",
            },
            "error_handling": {
                "enabled": False,
                "mode": "none",
                "fallback_if_no_director": "needs_operator",
            },
            "evolve": self._evolution.default_block(answers=True),
            "roles": [
                {"id": "author", "title": "Author", "responsibility": "Creates the main work artifacts."},
                {"id": "reviewer", "title": "Reviewer", "responsibility": "Checks quality gates before handoff."},
            ],
            "stages": [
                {
                    "id": "intake",
                    "title": "Intake",
                    "description": "Capture objective, constraints, and expected outputs.",
                    "required_role": "author",
                    "produced_artifacts": ["brief"],
                    "exit_gates": ["brief-approved"],
                    "handoff_required": False,
                },
                {
                    "id": "work",
                    "title": "Work",
                    "description": "Create the requested outputs.",
                    "required_role": "author",
                    "required_inputs": ["brief"],
                    "produced_artifacts": ["work-output"],
                    "entry_gates": ["brief-approved"],
                    "exit_gates": ["work-ready-for-review"],
                    "handoff_required": False,
                },
                {
                    "id": "review",
                    "title": "Review",
                    "description": "Validate the output and record risks.",
                    "required_role": "reviewer",
                    "required_inputs": ["work-output"],
                    "produced_artifacts": ["review-notes"],
                    "entry_gates": ["work-ready-for-review"],
                    "exit_gates": ["review-passed"],
                    "handoff_required": False,
                },
                {
                    "id": "handoff",
                    "title": "Handoff",
                    "description": "Summarize delivered state and next steps.",
                    "required_role": "author",
                    "required_inputs": ["review-notes"],
                    "produced_artifacts": ["handoff"],
                    "entry_gates": ["review-passed"],
                    "exit_gates": ["handoff-created"],
                    "handoff_required": True,
                },
            ],
            "artifacts": [
                {"id": "brief", "title": "Brief", "owner_role": "author", "template": "artifact-template"},
                {"id": "work-output", "title": "Work Output", "owner_role": "author", "template": "artifact-template"},
                {"id": "review-notes", "title": "Review Notes", "owner_role": "reviewer", "template": "review-template"},
                {"id": "handoff", "title": "Handoff", "owner_role": "author", "template": "handoff-template"},
            ],
            "evidence_definitions": [
                {"id": "review-attestation", "title": "Review attestation", "kind": "attestation"},
            ],
            "gates": [
                {"id": "brief-approved", "description": "Brief is explicit enough to start work.", "blocking": True, "required_artifact": "brief"},
                {"id": "work-ready-for-review", "description": "Work output exists and is ready for review.", "blocking": True, "required_artifact": "work-output"},
                {"id": "review-passed", "description": "Review has no blocking failures.", "blocking": True, "required_artifact": "review-notes"},
                {"id": "handoff-created", "description": "Handoff artifact exists.", "blocking": True, "required_artifact": "handoff"},
            ],
            "required_capabilities": ["process_coordination", "artifact_review", "reporting"],
            "required_packages": ["process-forge-core"],
            "required_templates": ["artifact-template", "review-template", "handoff-template"],
            "allowed_tools": ["processforge-cli", "validator"],
            "forbidden_actions": ["write_private_absolute_paths_to_public_files", "skip_blocking_review"],
        }

    def normalize(self, raw: dict[str, Any], fallback_id: str = "new-process", fallback_title: str = "") -> dict[str, Any]:
        base = self.defaults(fallback_id, fallback_title or title_from_id(fallback_id))
        if not raw:
            return base
        process = raw.get("process") if isinstance(raw.get("process"), dict) else {}
        if not process and ("id" in raw or "name" in raw or "title" in raw):
            process = raw
        process_id = safe_id(str(process.get("id") or raw.get("id") or fallback_id), "new-process")
        base["process"].update(
            {
                "id": process_id,
                "name": str(process.get("name") or process.get("title") or raw.get("name") or raw.get("title") or title_from_id(process_id)),
                "version": str(process.get("version") or raw.get("version") or "1.0.0"),
                "status": str(process.get("status") or raw.get("status") or "draft"),
                "kind": str(process.get("kind") or raw.get("kind") or base["process"]["kind"]),
                "scope": str(process.get("scope") or raw.get("scope") or base["process"]["scope"]),
                "description": str(process.get("description") or raw.get("description") or base["process"]["description"]),
            }
        )
        for key in [
            "run_model",
            "execution_mode",
            "execution_mode_questions",
            "coordination_requirements",
            "error_handling",
            "roles",
            "stages",
            "artifacts",
            "artifact_definitions",
            "evidence_definitions",
            "gates",
            "hooks",
            "evolve",
            "evolution_policy",
            "expected_artifacts",
            "process_transitions",
            "agent_requirements",
            "responsibility_boundaries",
            "subagent_policy",
            "runtime_requirements",
            "runtime_execution_boundary",
            "stage_completion",
            "run_completion",
            "metadata",
        ]:
            if key in raw:
                base[key] = raw[key]
        if "artifact_definitions" in raw and "artifacts" not in raw:
            base["artifacts"] = raw["artifact_definitions"]
        base["evolve"] = self._evolution.normalize_block(base.get("evolve"), answers=True)
        for key in ["required_capabilities", "required_packages", "required_templates", "allowed_tools", "forbidden_actions"]:
            if key in raw:
                base[key] = string_list(raw[key])
        base["process_transitions"] = self.normalize_transitions(base.get("process_transitions"), process_id)
        return base

    def build(self, answers: dict[str, Any]) -> dict[str, Any]:
        process = answers.get("process") if isinstance(answers.get("process"), dict) else {}
        process_id = safe_id(str(process.get("id", "new-process")), "new-process")
        roles: list[dict[str, Any]] = []
        for item in as_list(answers.get("roles")):
            if isinstance(item, dict):
                role_id = safe_id(str(item.get("id") or item.get("title") or "role"), "role")
                responsibility = str(item.get("responsibility") or "")
                roles.append(
                    {
                        "id": role_id,
                        "title": str(item.get("title") or title_from_id(role_id)),
                        "kind": str(item.get("kind") or "primary_agent"),
                        "responsibility": responsibility,
                        "responsibilities": string_list(item.get("responsibilities")) or ([responsibility] if responsibility else [f"Owns {title_from_id(role_id)} responsibilities."]),
                    }
                )
        if not roles:
            roles = [{"id": "author", "title": "Author", "responsibility": "Creates process artifacts."}]
        role_ids = {item["id"] for item in roles}

        artifacts: list[dict[str, Any]] = []
        for item in as_list(answers.get("artifacts")):
            if isinstance(item, dict):
                artifact_id = safe_id(str(item.get("id") or item.get("title") or "artifact"), "artifact")
                owner_role = safe_id(str(item.get("owner_role") or roles[0]["id"]), roles[0]["id"])
                if owner_role not in role_ids:
                    owner_role = roles[0]["id"]
                artifacts.append(
                    {
                        "id": artifact_id,
                        "title": str(item.get("title") or title_from_id(artifact_id)),
                        "owner_role": owner_role,
                        "type": str(item.get("type") or "markdown"),
                        "required": bool(item.get("required", True)),
                        "template": str(item.get("template") or "artifact-template"),
                        "path_hint": str(item.get("path_hint") or f".pf/artifacts/{artifact_id}.md"),
                        "lifecycle": string_list(item.get("lifecycle")) or ["draft", "ready_for_review", "approved"],
                    }
                )
        artifact_ids = {item["id"] for item in artifacts}

        gates: list[dict[str, Any]] = []
        for item in as_list(answers.get("gates")):
            if isinstance(item, dict):
                gate_id = safe_id(str(item.get("id") or item.get("description") or "gate"), "gate")
                gate: dict[str, Any] = {
                    "id": gate_id,
                    "description": str(item.get("description") or title_from_id(gate_id)),
                    "type": str(item.get("type") or ("artifact_exists" if item.get("required_artifact") else "checklist")),
                    "blocking": bool(item.get("blocking", True)),
                    "required": bool(item.get("required", item.get("blocking", True))),
                }
                if item.get("required_artifact"):
                    gate["required_artifact"] = safe_id(str(item.get("required_artifact")), "artifact")
                gates.append(gate)
        gate_ids = {item["id"] for item in gates}

        stages: list[dict[str, Any]] = []
        handoff_note_required = False
        for item in as_list(answers.get("stages")):
            if isinstance(item, dict):
                stage_id = safe_id(str(item.get("id") or item.get("title") or "stage"), "stage")
                produced = [safe_id(value, "artifact") for value in string_list(item.get("produced_artifacts"))]
                exits = [safe_id(value, "gate") for value in string_list(item.get("exit_gates") or item.get("gates"))]
                if not produced and artifact_ids:
                    produced = [sorted(artifact_ids)[0]]
                if not exits and gate_ids:
                    exits = [sorted(gate_ids)[0]]
                role_id = safe_id(str(item.get("required_role") or roles[0]["id"]), roles[0]["id"])
                if role_id not in role_ids:
                    role_id = roles[0]["id"]
                if bool(item.get("handoff_required", False)):
                    handoff_note_required = True
                stages.append(
                    {
                        "id": stage_id,
                        "title": str(item.get("title") or title_from_id(stage_id)),
                        "goal": str(item.get("goal") or item.get("description") or item.get("title") or title_from_id(stage_id)),
                        "description": str(item.get("description") or ""),
                        "actor": str(item.get("actor") or "primary_agent"),
                        "required_inputs": [safe_id(value, "artifact") for value in string_list(item.get("required_inputs"))],
                        "produced_artifacts": produced,
                        "required_artifacts": [safe_id(value, "artifact") for value in string_list(item.get("required_artifacts"))],
                        "required_evidence": [safe_id(value, "evidence") for value in string_list(item.get("required_evidence"))],
                        "required_role": role_id,
                        "required_capabilities": string_list(item.get("required_capabilities")),
                        "parameters": item.get("parameters") if isinstance(item.get("parameters"), dict) else {},
                        "allowed_tools": string_list(item.get("allowed_tools")),
                        "entry_gates": [safe_id(value, "gate") for value in string_list(item.get("entry_gates"))],
                        "exit_gates": exits,
                        "automation_bindings": as_list(item.get("automation_bindings")) or as_list(item.get("technical_obligations")),
                    }
                )
        if not artifacts:
            artifacts = [
                {
                    "id": "brief",
                    "title": "Brief",
                    "owner_role": roles[0]["id"],
                    "type": "markdown",
                    "required": True,
                    "template": "artifact-template",
                    "path_hint": ".pf/artifacts/brief.md",
                    "lifecycle": ["draft", "ready_for_review", "approved"],
                }
            ]
            artifact_ids = {"brief"}
        if not gates:
            gates = [{"id": "brief-approved", "description": "Brief is approved.", "blocking": True, "required_artifact": "brief"}]
            gate_ids = {"brief-approved"}
        if not stages:
            stages = [{"id": "intake", "title": "Intake", "goal": "Capture scope.", "description": "Capture scope.", "actor": "primary_agent", "required_inputs": [], "produced_artifacts": list(artifact_ids), "required_role": roles[0]["id"], "exit_gates": list(gate_ids), "gates": list(gate_ids)}]
            handoff_note_required = True

        run_model = answers.get("run_model") if isinstance(answers.get("run_model"), dict) else {}
        output = {
            "schema_version": 1,
            "id": process_id,
            "name": str(process.get("name") or title_from_id(process_id)),
            "kind": str(process.get("kind") or "project_process"),
            "scope": str(process.get("scope") or "project"),
            "version": str(process.get("version") or "1.0.0"),
            "status": str(process.get("status") or "draft"),
            "description": str(process.get("description") or ""),
            "purpose": str(process.get("purpose") or process.get("description") or ""),
            "execution_mode": str(answers.get("execution_mode") or process.get("execution_mode") or "single_agent"),
            "execution_mode_questions": answers.get("execution_mode_questions") if isinstance(answers.get("execution_mode_questions"), dict) else {},
            "coordination_requirements": answers.get("coordination_requirements") if isinstance(answers.get("coordination_requirements"), dict) else self.defaults(process_id, "").get("coordination_requirements", {}),
            "error_handling": answers.get("error_handling") if isinstance(answers.get("error_handling"), dict) else self.defaults(process_id, "").get("error_handling", {}),
            "run_model": run_model,
            "required_capabilities": string_list(answers.get("required_capabilities")),
            "hooks": answers.get("hooks") if isinstance(answers.get("hooks"), dict) else {
                "emit": [
                    {"event": "process.created", "required": True},
                    {"event": "process.started", "required": True},
                    {"event": "stage.started", "required": True},
                    {"event": "stage.completed", "required": True},
                    {"event": "artifact.created", "required": True},
                    {"event": "review.completed", "required": True},
                    {"event": "process.completed", "required": True},
                ],
                "tracking": {"include": ["process_id", "stage_id", "artifact_refs", "assignment_id", "run_id", "task_id", "status"]},
            },
            "roles": roles,
            "stages": stages,
            "artifact_definitions": artifacts,
            "evidence_definitions": [
                {
                    "id": safe_id(str(item.get("id") or item.get("title") or "evidence"), "evidence"),
                    "title": str(item.get("title") or title_from_id(safe_id(str(item.get("id") or "evidence"), "evidence"))),
                    "kind": str(item.get("kind") or "attestation"),
                    **({"artifact": safe_id(str(item.get("artifact")), "artifact")} if item.get("artifact") else {}),
                    **({"description": str(item.get("description"))} if item.get("description") else {}),
                }
                for item in as_list(answers.get("evidence_definitions"))
                if isinstance(item, dict)
            ],
            "gates": gates,
            "required_packages": string_list(answers.get("required_packages")) or ["process-forge-core"],
            "required_templates": string_list(answers.get("required_templates")) or ["artifact-template"],
            "allowed_tools": string_list(answers.get("allowed_tools")) or ["processforge-cli"],
            "forbidden_actions": string_list(answers.get("forbidden_actions")) or ["write_private_absolute_paths_to_public_files"],
            "evolve": self._evolution.normalize_block(answers.get("evolve")),
            "stage_completion": answers.get("stage_completion") if isinstance(answers.get("stage_completion"), dict) else {"handoff_note_required": handoff_note_required},
            "run_completion": answers.get("run_completion") if isinstance(answers.get("run_completion"), dict) else {"summary_required": True, "handoff_artifact_required": handoff_note_required},
            "evolution_policy": answers.get("evolution_policy") if isinstance(answers.get("evolution_policy"), dict) else {
                "active_run_upgrade": {"default": "manual_only"},
                "safe_changes": ["add_optional_stage", "add_non_blocking_gate"],
                "blocked_changes": ["remove_existing_required_artifact", "weaken_blocking_gate_without_review"],
                "requires_approval": ["change_stage_order", "change_required_artifact_lifecycle"],
            },
        }
        for key in [
            "expected_artifacts",
            "process_transitions",
            "agent_requirements",
            "subagent_policy",
            "runtime_requirements",
            "runtime_execution_boundary",
            "metadata",
        ]:
            if key in answers:
                output[key] = answers[key]
        if "responsibility_boundaries" in answers:
            output["responsibility_boundaries"] = self.materialize_responsibility_boundaries(
                answers["responsibility_boundaries"]
            )
        return output

    def normalize_transitions(self, value: Any, source_process: str) -> list[dict[str, Any]]:
        """Materialize legacy authoring-route shorthand as schema-valid transitions."""
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if not isinstance(value, dict):
            return []

        shared_return = {
            key: value[key]
            for key in ["offline_agent_policy", "continuation_capsule_required", "post_handoff_run_owner"]
            if key in value
        }
        transitions: list[dict[str, Any]] = []
        for route in as_list(value.get("routes")):
            if not isinstance(route, dict):
                continue
            target_process = safe_id(str(route.get("to_process") or route.get("target_process") or ""), "")
            if not target_process:
                continue
            transition: dict[str, Any] = {
                "id": safe_id(str(route.get("id") or f"{source_process}-to-{target_process}"), "transition"),
                "from_process": source_process,
                "to_process": target_process,
                "mode": str(route.get("mode") or "wait_for_result"),
            }
            if route.get("required_role"):
                transition["requires_agent"] = {"required_role": str(route["required_role"])}
            if route.get("input_artifacts"):
                transition["input_contract"] = {"artifacts": string_list(route["input_artifacts"])}
            if route.get("expected_output_artifacts"):
                transition["output_contract"] = {"artifacts": string_list(route["expected_output_artifacts"])}
            if shared_return:
                transition["return"] = shared_return
            transitions.append(transition)
        return transitions

    def materialize_responsibility_boundaries(self, value: Any) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {}
        if all(
            isinstance(items, list) and all(isinstance(item, str) for item in items)
            for items in value.values()
        ):
            return {str(key): list(items) for key, items in value.items()}

        output: dict[str, list[str]] = {}

        def add(role: str, message: str) -> None:
            text = message.strip()
            if text:
                output.setdefault(role, []).append(text)

        role_fields = {
            "coordinator_role": "coordinator",
            "execution_inspector_role": "execution_inspector",
            "worker_role": "worker",
        }
        for field, role in role_fields.items():
            if value.get(field):
                add(role, f"Assigned role: {value[field]}.")
        if isinstance(value.get("needs_agent_director"), bool):
            add(
                "director",
                "Required by this process." if value["needs_agent_director"] else "Not required by this process.",
            )
        if isinstance(value.get("needs_execution_inspector"), bool):
            add(
                "execution_inspector",
                "Required by this process." if value["needs_execution_inspector"] else "Not required by this process.",
            )
        list_fields = {
            "director_decisions": "director",
            "inspector_checks": "execution_inspector",
            "worker_actions": "worker",
            "automatic_cli_checks": "cli_tools",
        }
        consumed = {*role_fields, "needs_agent_director", "needs_execution_inspector", *list_fields}
        for field, role in list_fields.items():
            for item in string_list(value.get(field)):
                add(role, item)
        for key, items in value.items():
            if key in consumed:
                continue
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str):
                        add(str(key), item)
        return output
