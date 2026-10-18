"""Process semantic projection and comparison policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.ids import safe_id
from processforge_core.common.paths import rel
from processforge_core.common.values import as_list, string_list


PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL = {
    "schema_version",
    "id",
    "name",
    "kind",
    "scope",
    "version",
    "status",
    "description",
    "purpose",
    "execution_mode",
    "execution_mode_questions",
    "coordination_requirements",
    "error_handling",
    "run_model",
    "required_capabilities",
    "hooks",
    "evolve",
    "roles",
    "stages",
    "artifact_definitions",
    "evidence_definitions",
    "gates",
    "required_packages",
    "required_templates",
    "allowed_tools",
    "forbidden_actions",
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
    "catalog",
    "process_pack",
    "public_surface",
    "agent_prompt",
    "input_definitions",
    "external_artifacts",
    "virtual_artifacts",
    "generated_files",
}


class ProcessSemanticPolicy:

    def unsupported_fields(self, process: dict[str, Any]) -> list[dict[str, str]]:
        unsupported: list[dict[str, str]] = []
        for key in sorted(process.keys()):
            if key not in PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL:
                unsupported.append({"path": key, "reason": "not represented in process-authoring answers schema"})
        return unsupported

    def map(self, process: dict[str, Any], process_path: Path, project_root: Path, unsupported: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source": {"type": "process", "id": str(process.get("id", process_path.stem)), "path": rel(process_path, project_root)},
            "mapped": {
                "id": "process.id",
                "title": "process.name",
                "purpose": "process.description",
                "stages": "stages",
                "roles": "roles",
                "gates": "gates",
                "artifacts": "artifact_definitions",
                "events": "hooks.emit",
                "evolve": "evolve",
                "run_model": "run_model",
                "requirements": "required_packages|required_templates|allowed_tools|required_capabilities",
            },
            "unsupported": unsupported,
        }

    def describe(self, process: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": safe_id(str(process.get("id", "")), "process"),
            "title": str(process.get("name") or ""),
            "kind": str(process.get("kind") or ""),
            "scope": str(process.get("scope") or ""),
            "purpose": str(process.get("purpose") or process.get("description") or ""),
            "run_model": process.get("run_model") if isinstance(process.get("run_model"), dict) else {},
            "roles": self.objects(process.get("roles"), ["title", "responsibility"]),
            "stages": self.objects(process.get("stages"), ["title", "required_role", "required_inputs", "produced_artifacts", "required_artifacts", "required_evidence", "entry_gates", "exit_gates", "automation_bindings", "handoff_required"]),
            "artifact_definitions": self.objects(process.get("artifact_definitions"), ["title", "owner_role", "template", "lifecycle"]),
            "evidence_definitions": self.objects(process.get("evidence_definitions"), ["title", "kind", "artifact"]),
            "gates": self.objects(process.get("gates"), ["description", "blocking", "required_artifact", "stage", "stage_id"]),
            "events": {"emits": self.events(process)},
            "requirements": {
                "required_capabilities": self.strings(process.get("required_capabilities")),
                "required_packages": self.strings(process.get("required_packages")),
                "required_templates": self.strings(process.get("required_templates")),
                "allowed_tools": self.strings(process.get("allowed_tools")),
                "forbidden_actions": self.strings(process.get("forbidden_actions")),
            },
        }

    def compare(self, source: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        source_sem = self.describe(source)
        candidate_sem = self.describe(candidate)
        diffs: list[dict[str, str]] = []

        def add(level: str, area: str, message: str) -> None:
            diffs.append({"level": level, "area": area, "message": message})

        for area in ["id", "run_model"]:
            if source_sem.get(area) != candidate_sem.get(area):
                add("FAIL", area, f"{area} differs")
        for area in ["title", "kind", "scope", "purpose"]:
            if area in {"kind", "scope"} and area not in source:
                continue
            if source_sem.get(area) != candidate_sem.get(area):
                add("WARN", area, f"{area} differs")
        for area in ["roles", "stages", "artifact_definitions", "gates"]:
            source_ids = set(source_sem[area].keys())
            candidate_ids = set(candidate_sem[area].keys())
            for missing in sorted(source_ids - candidate_ids):
                add("FAIL", area, f"{area} missing: {missing}")
            for extra in sorted(candidate_ids - source_ids):
                add("WARN", area, f"{area} extra: {extra}")
        for area, label in [("events", "emits")]:
            source_values = set(source_sem[area][label])
            candidate_values = set(candidate_sem[area][label])
            for missing in sorted(source_values - candidate_values):
                add("FAIL", area, f"event missing: {missing}")
        for key, source_values in source_sem["requirements"].items():
            candidate_values = set(candidate_sem["requirements"].get(key, []))
            for missing in sorted(set(source_values) - candidate_values):
                add("FAIL", key, f"{key} missing: {missing}")
        status = "FAIL" if any(item["level"] == "FAIL" for item in diffs) else ("WARN" if any(item["level"] == "WARN" for item in diffs) else "PASS")
        return status, diffs

    def strings(self, values: Any) -> list[str]:
        return sorted(set(string_list(values)))

    def events(self, process: dict[str, Any]) -> list[str]:
        hooks = process.get("hooks") if isinstance(process.get("hooks"), dict) else {}
        emits = hooks.get("emit") if isinstance(hooks.get("emit"), list) else []
        return sorted({str(item.get("event")) for item in emits if isinstance(item, dict) and item.get("event")})

    def objects(self, items: Any, keys: list[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in as_list(items):
            if not isinstance(item, dict):
                continue
            item_id = safe_id(str(item.get("id", "")), "item")
            result[item_id] = {key: item.get(key) for key in keys if key in item}
        return result
