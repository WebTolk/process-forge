"""Knowledge candidate identity, routing and targeting policy."""

from __future__ import annotations

from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.ids import safe_id
from processforge_core.common.values import string_list
from processforge_core.process_catalog.evolution import EVOLVE_CANDIDATE_TARGETS


EVOLVE_APPLICABILITY_SCOPES = {"project", "workplace", "package", "platform", "parent_platform", "platform_family", "process", "core"}
EVOLVE_GENERALIZATION_LEVELS = {
    "narrow_observation",
    "project_rule",
    "package_rule",
    "platform_rule",
    "parent_platform_candidate",
    "parent_platform_rule",
    "universal_rule",
}
EVOLVE_PROMOTION_STATUSES = {"not_requested", "proposed", "needs_more_evidence", "approved", "rejected"}


class KnowledgeCandidateTargetingPolicy:
    def id_from_data(self, data: dict[str, Any], fallback: str = "candidate") -> str:
        return safe_id(str(data.get("id") or data.get("candidate_id") or fallback), "candidate")

    def target(self, data: dict[str, Any]) -> dict[str, Any]:
        target = data.get("target")
        if isinstance(target, dict):
            return target
        legacy_type = str(data.get("target_type") or target or "")
        legacy_id = str(data.get("target_package") or data.get("package") or data.get("target_id") or "")
        if legacy_type:
            return {"type": legacy_type, "id": legacy_id}
        return {}

    def target_type(self, data: dict[str, Any]) -> str:
        return str(self.target(data).get("type") or "")

    def target_id(self, data: dict[str, Any]) -> str:
        return str(self.target(data).get("id") or "")

    def routing_destination(self, data: dict[str, Any]) -> dict[str, Any]:
        routing = data.get("routing") if isinstance(data.get("routing"), dict) else {}
        destination = routing.get("recommended_destination")
        return destination if isinstance(destination, dict) else {}

    def destination_matches(self, data: dict[str, Any], package_id: str) -> bool:
        destination = self.routing_destination(data)
        if str(destination.get("id") or "") == package_id:
            return True
        return self.target_id(data) == package_id

    def promotion_status(self, data: dict[str, Any]) -> str:
        promotion = data.get("promotion") if isinstance(data.get("promotion"), dict) else {}
        return str(promotion.get("status") or "not_requested")

    def generalization_level(self, data: dict[str, Any]) -> str:
        generalization = data.get("generalization") if isinstance(data.get("generalization"), dict) else {}
        return str(generalization.get("level") or "")

    def is_parent_promotion_candidate(self, data: dict[str, Any]) -> bool:
        level = self.generalization_level(data)
        applicability = data.get("applicability") if isinstance(data.get("applicability"), dict) else {}
        return level in {"parent_platform_candidate", "parent_platform_rule", "universal_rule"} or str(applicability.get("scope") or "") in {"parent_platform", "platform_family", "core"}

    def ready_for_curated_package(self, data: dict[str, Any]) -> bool:
        if not self.is_parent_promotion_candidate(data):
            return True
        return self.promotion_status(data) == "approved" or self.generalization_level(data) in {"parent_platform_rule", "universal_rule"}

    def validate(self, data: dict[str, Any], *, strict: bool = True) -> list[Check]:
        checks: list[Check] = []
        level = "FAIL" if strict else "WARN"
        target = self.target(data)
        target_type = str(target.get("type") or "")
        target_id = str(target.get("id") or "")
        checks.append(check("PASS" if target_type in EVOLVE_CANDIDATE_TARGETS else "FAIL", f"candidate target.type valid: {target_type}"))
        checks.append(check("PASS" if target_id.strip() else "FAIL", "candidate target.id declared"))
        applicability = data.get("applicability") if isinstance(data.get("applicability"), dict) else {}
        checks.append(check("PASS" if applicability else level, "candidate applicability declared"))
        scope = str(applicability.get("scope") or "")
        checks.append(check("PASS" if scope in EVOLVE_APPLICABILITY_SCOPES else level, f"candidate applicability.scope valid: {scope}"))
        source_context = data.get("source_context") if isinstance(data.get("source_context"), dict) else {}
        checks.append(check("PASS" if isinstance(source_context, dict) and source_context else "WARN", "candidate source_context declared"))
        generalization = data.get("generalization") if isinstance(data.get("generalization"), dict) else {}
        level_value = str(generalization.get("level") or "")
        if level_value:
            checks.append(check("PASS" if level_value in EVOLVE_GENERALIZATION_LEVELS else "FAIL", f"candidate generalization.level valid: {level_value}"))
        promotion = data.get("promotion") if isinstance(data.get("promotion"), dict) else {}
        promotion_status = str(promotion.get("status") or "not_requested")
        checks.append(check("PASS" if promotion_status in EVOLVE_PROMOTION_STATUSES else "FAIL", f"candidate promotion.status valid: {promotion_status}"))
        if target_type in {"knowledge_package", "platform_contract"} and scope in {"parent_platform", "platform_family", "core"}:
            checks.append(check("PASS" if level_value in {"parent_platform_candidate", "parent_platform_rule", "universal_rule"} else level, "parent/platform-wide candidate has explicit generalization metadata"))
        inheritance = applicability.get("inheritance") if isinstance(applicability.get("inheritance"), dict) else {}
        observed = string_list(inheritance.get("observed_on"))
        parents = string_list(inheritance.get("parent_platforms"))
        if parents and observed and target_id in parents and not bool(inheritance.get("safe_for_parent", False)):
            checks.append(check(level, "child platform observation targets parent without safe_for_parent evidence"))
        confidence = data.get("applicability_confidence") if isinstance(data.get("applicability_confidence"), dict) else {}
        evidence_count = confidence.get("evidence_count")
        if scope in {"parent_platform", "platform_family", "core"}:
            checks.append(check("PASS" if isinstance(evidence_count, int) and evidence_count > 1 else "WARN", "broad applicability has multi-evidence support or remains unreviewed"))
        return checks
