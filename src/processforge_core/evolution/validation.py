"""Existing knowledge candidate validation composed from concrete Core policies."""

from __future__ import annotations

import json
from typing import Any

from ..common.checks import Check, check
from .candidates import KnowledgeCandidateTargetingPolicy
from .privacy import EvolvePrivacyPolicy


EVOLVE_CANDIDATE_CATEGORIES = {
    "domain",
    "architecture",
    "implementation",
    "assurance",
    "delivery",
    "tooling",
    "process",
    "resource",
    "generic",
}


class KnowledgeCandidateValidationService:
    def __init__(self) -> None:
        self.targeting_policy = KnowledgeCandidateTargetingPolicy()
        self.privacy_policy = EvolvePrivacyPolicy()

    def validate(self, data: dict[str, Any]) -> list[Check]:
        checks: list[Check] = []
        checks.append(check("PASS" if data.get("kind") == "processforge.knowledge_candidate" else "FAIL", "candidate kind is processforge.knowledge_candidate"))
        candidate_id = self.targeting_policy.id_from_data(data)
        checks.append(check("PASS" if candidate_id == str(data.get("id") or data.get("candidate_id")) else "FAIL", "candidate id is portable"))
        category = str(data.get("category") or "generic")
        checks.extend(self.targeting_policy.validate(data, strict=True))
        checks.append(check("PASS" if category in EVOLVE_CANDIDATE_CATEGORIES else "FAIL", f"candidate category valid: {category}"))
        checks.append(check("PASS" if str(data.get("summary") or "").strip() else "FAIL", "candidate summary declared"))
        findings = self.privacy_policy.findings(json.dumps(data, ensure_ascii=False))
        checks.append(check("PASS" if not findings else "FAIL", "candidate has no unsanitized private paths or secrets" + (f": {', '.join(findings)}" if findings else "")))
        return checks
