"""Process evolution document defaults, normalization and validation."""

from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.values import string_list


EVOLVE_MODES = {"disabled", "optional", "required"}
EVOLVE_TIMINGS = {"end_of_stage", "end_of_task", "end_of_run"}
EVOLVE_SCOPES = {"project", "workplace", "package", "platform", "core"}
EVOLVE_CANDIDATE_TARGETS = {
    "knowledge_package",
    "template_package",
    "process_definition",
    "delivery_profile",
    "project_rule",
    "workplace_rule",
    "platform_contract",
    "core_docs",
    "core_schema",
    "regression_check",
}


class ProcessEvolutionPolicy:
    def default_block(self, *, answers: bool = False) -> dict[str, Any]:
        block: dict[str, Any] = {
            "enabled": True,
            "mode": "optional",
            "timing": "end_of_run",
            "default_scope": "project",
            "candidate_targets": [
                "knowledge_package",
                "template_package",
                "process_definition",
            ],
            "extraction_hints": [
                "reusable rule",
                "missing knowledge",
                "template improvement",
                "regression check",
                "process improvement",
                "Split candidates when an observation contains project-specific and platform-general parts.",
                "Default to the narrowest safe scope and require evidence before parent-platform promotion.",
            ],
            "candidate_targeting": {
                "default_scope": "project",
                "require_applicability": True,
                "require_target": True,
                "ask_target_layer": True,
                "ask_applicability": True,
                "ask_not_applicable": True,
                "ask_generalization_level": True,
                "default_to_narrowest_scope": True,
            },
            "required_outputs": ["evolution-report"],
            "privacy": {
                "default_sensitivity": "internal",
                "export_requires_sanitization": True,
                "allow_private_paths": False,
            },
            "apply_policy": {
                "auto_apply_global": False,
                "create_candidates_only": True,
            },
        }
        if answers:
            block["decision"] = {
                "value": "enabled",
                "reason": "This process may produce reusable knowledge.",
            }
            block["prompts"] = [
                "What reusable knowledge may appear during this process?",
                "Which outputs are candidates for shared packages?",
                "What must remain project-private?",
            ]
        return block

    def normalize_block(self, raw: Any, *, answers: bool = False) -> dict[str, Any]:
        block = self.default_block(answers=answers)
        if isinstance(raw, dict):
            block.update({key: value for key, value in raw.items() if value not in (None, "")})
            privacy = self.default_block(answers=answers)["privacy"]
            if isinstance(raw.get("privacy"), dict):
                privacy.update(raw["privacy"])
            block["privacy"] = privacy
            apply_policy = self.default_block(answers=answers)["apply_policy"]
            if isinstance(raw.get("apply_policy"), dict):
                apply_policy.update(raw["apply_policy"])
            block["apply_policy"] = apply_policy
            targeting = self.default_block(answers=answers)["candidate_targeting"]
            if isinstance(raw.get("candidate_targeting"), dict):
                targeting.update(raw["candidate_targeting"])
            block["candidate_targeting"] = targeting
            if answers:
                decision = self.default_block(answers=True)["decision"]
                if isinstance(raw.get("decision"), dict):
                    decision.update(raw["decision"])
                block["decision"] = decision
        enabled = bool(block.get("enabled", True))
        block["enabled"] = enabled
        if not enabled:
            block["mode"] = "disabled"
            decision = block.get("decision") if isinstance(block.get("decision"), dict) else {}
            reason = str(block.get("reason") or decision.get("reason") or "").strip()
            if reason:
                block["reason"] = reason
            if answers:
                decision["value"] = "disabled"
                block["decision"] = decision
            for optional_key in ["timing", "default_scope", "candidate_targets", "candidate_targeting", "extraction_hints", "required_outputs", "privacy", "apply_policy", "prompts"]:
                if optional_key in block and optional_key not in {"privacy", "apply_policy"}:
                    block.pop(optional_key, None)
        else:
            block["mode"] = str(block.get("mode") or "optional")
            block["timing"] = str(block.get("timing") or "end_of_run")
            block["default_scope"] = str(block.get("default_scope") or "project")
            block["candidate_targets"] = string_list(block.get("candidate_targets")) or self.default_block()["candidate_targets"]
            block["extraction_hints"] = string_list(block.get("extraction_hints")) or self.default_block()["extraction_hints"]
            if not isinstance(block.get("candidate_targeting"), dict):
                block["candidate_targeting"] = self.default_block()["candidate_targeting"]
            block["required_outputs"] = string_list(block.get("required_outputs")) or ["evolution-report"]
            if answers:
                block["prompts"] = string_list(block.get("prompts")) or self.default_block(answers=True)["prompts"]
                decision = block.get("decision") if isinstance(block.get("decision"), dict) else {}
                decision["value"] = "enabled"
                decision.setdefault("reason", "This process may produce reusable knowledge.")
                block["decision"] = decision
        return block

    def validate_block(self, process_id: str, block: Any, *, hard: bool) -> list[Check]:
        checks: list[Check] = []
        level = "FAIL" if hard else "WARN"
        if not isinstance(block, dict):
            checks.append(check(level, f"{process_id} evolve declared"))
            return checks
        enabled = block.get("enabled")
        checks.append(check("PASS" if isinstance(enabled, bool) else level, f"{process_id} evolve.enabled explicit"))
        mode = str(block.get("mode") or "")
        checks.append(check("PASS" if mode in EVOLVE_MODES else level, f"{process_id} evolve.mode valid"))
        if enabled is False:
            decision = block.get("decision") if isinstance(block.get("decision"), dict) else {}
            reason = str(block.get("reason") or decision.get("reason") or "")
            checks.append(check("PASS" if mode == "disabled" else level, f"{process_id} disabled evolve uses disabled mode"))
            checks.append(check("PASS" if reason.strip() else "FAIL", f"{process_id} disabled evolve has reason"))
            return checks
        checks.append(check("PASS" if str(block.get("timing") or "") in EVOLVE_TIMINGS else level, f"{process_id} evolve.timing valid"))
        checks.append(check("PASS" if str(block.get("default_scope") or "") in EVOLVE_SCOPES else level, f"{process_id} evolve.default_scope valid"))
        targets = string_list(block.get("candidate_targets"))
        bad_targets = sorted(set(targets) - EVOLVE_CANDIDATE_TARGETS)
        checks.append(check("PASS" if targets and not bad_targets else level, f"{process_id} evolve.candidate_targets valid"))
        checks.append(check("PASS" if string_list(block.get("required_outputs")) else level, f"{process_id} evolve.required_outputs declared"))
        targeting = block.get("candidate_targeting") if isinstance(block.get("candidate_targeting"), dict) else {}
        checks.append(check("PASS" if targeting.get("require_target") is True and targeting.get("require_applicability") is True else level, f"{process_id} evolve candidate targeting requires target/applicability"))
        checks.append(check("PASS" if targeting.get("default_to_narrowest_scope") is True else level, f"{process_id} evolve defaults to narrowest safe scope"))
        privacy = block.get("privacy") if isinstance(block.get("privacy"), dict) else {}
        apply_policy = block.get("apply_policy") if isinstance(block.get("apply_policy"), dict) else {}
        checks.append(check("PASS" if privacy.get("export_requires_sanitization") is True and privacy.get("allow_private_paths") is False else level, f"{process_id} evolve privacy boundary declared"))
        checks.append(check("PASS" if apply_policy.get("auto_apply_global") is False and apply_policy.get("create_candidates_only") is True else level, f"{process_id} evolve apply policy creates candidates only"))
        return checks
