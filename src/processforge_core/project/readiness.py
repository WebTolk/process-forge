"""Existing project context readiness rules, independent of transports and I/O."""

from __future__ import annotations

from typing import Any


class ProjectContextReadinessPolicy:
    """Build ordered execution and resource readiness projections."""

    def capabilities(
        self,
        required: list[str],
        optional: list[str],
        providers: dict[str, str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        available = set(providers)

        def record(capability: str, required_capability: bool) -> dict[str, Any]:
            is_available = capability in available
            provider = providers.get(capability)
            return {
                "id": capability,
                "status": "available" if is_available else "missing",
                "provider": provider if is_available else None,
                "severity": "fail" if required_capability and not is_available else ("warn" if not required_capability and not is_available else "info"),
            }

        return [record(item, True) for item in required], [record(item, False) for item in optional]

    def execution(
        self,
        required_records: list[dict[str, Any]],
        capability_resolution: dict[str, Any] | None = None,
        *,
        coordination_blocked: bool = False,
    ) -> dict[str, Any]:
        missing_capabilities: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        seen_capabilities: set[tuple[str, str]] = set()

        for item in required_records:
            if not isinstance(item, dict) or item.get("status") != "missing":
                continue
            capability = str(item.get("id") or "")
            if not capability:
                continue
            key = (capability, "project.required_capabilities")
            if key in seen_capabilities:
                continue
            seen_capabilities.add(key)
            missing = {
                "capability": capability,
                "required_by": "project.required_capabilities",
                "availability": "missing",
                "reason": "no active project registry provider declared the required capability",
                "expected_provider_scope": "project or workplace tool/MCP registry",
            }
            missing_capabilities.append(missing)
            blockers.append({"type": "capability_missing", **missing})

        resolution = capability_resolution if isinstance(capability_resolution, dict) else {}
        for item in resolution.get("unsatisfied", []) if isinstance(resolution.get("unsatisfied"), list) else []:
            if not isinstance(item, dict):
                continue
            capability = str(item.get("capability") or "")
            required_by = str(item.get("required_by") or "execution_route")
            if not capability:
                continue
            key = (capability, required_by)
            if key in seen_capabilities:
                continue
            seen_capabilities.add(key)
            missing = {
                "capability": capability,
                "required_by": required_by,
                "availability": "missing",
                "reason": str(item.get("reason") or "selected execution resources do not provide the capability"),
                "expected_provider_scope": "specialization resource profile, active process pack, or workplace registry",
            }
            missing_capabilities.append(missing)
            blockers.append({"type": "capability_missing", **missing})

        if coordination_blocked:
            blockers.append(
                {
                    "type": "coordination_unavailable",
                    "reason": "organized coordination is selected but the workplace Director is unavailable",
                    "required_by": "project.coordination",
                }
            )

        return {
            "status": "blocked" if blockers else "ready",
            "missing_capabilities": missing_capabilities,
            "blockers": blockers,
        }

    def resources(
        self,
        *,
        platform_resolution: dict[str, Any],
        required_resource_missing: list[str],
        specialization_conflicts: list[dict[str, Any]],
        parameter_conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        blockers: list[dict[str, Any]] = []
        for item in platform_resolution.get("missing_required_contracts", []):
            blockers.append({"type": "platform_contract_missing", "id": str(item)})
        for item in platform_resolution.get("circular_platforms", []):
            blockers.append({"type": "platform_contract_cycle", "id": str(item)})
        for item in required_resource_missing:
            blockers.append({"type": "required_resource_missing", "id": str(item)})
        for item in specialization_conflicts:
            if isinstance(item, dict):
                blockers.append({"type": "specialization_conflict", **item})
        for item in parameter_conflicts:
            if isinstance(item, dict):
                blockers.append({"type": "parameter_conflict", **item})
        return {"status": "blocked" if blockers else "fresh", "blockers": blockers}
