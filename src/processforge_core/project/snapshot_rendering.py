"""Markdown rendering of project context snapshots."""

from __future__ import annotations

from typing import Any


class ProjectContextSnapshotRenderer:
    """Render snapshots without retaining request state."""

    def render(self, snapshot: dict[str, Any], freshness: str = "fresh", reasons: list[str] | None = None) -> str:
        project = snapshot.get("project", {})
        flow = snapshot.get("flow", {})
        meta = snapshot.get("snapshot", {})
        capabilities = snapshot.get("capabilities", {})
        policies = snapshot.get("resolved_policies", {})
        process_forge = snapshot.get("process_forge", {}) if isinstance(snapshot.get("process_forge"), dict) else {}
        distribution = process_forge.get("distribution", {}) if isinstance(process_forge.get("distribution"), dict) else {}
        platforms = snapshot.get("platform_contracts", {}).get("selected", []) if isinstance(snapshot.get("platform_contracts"), dict) else []
        platform_stack = snapshot.get("platform_stack", [])
        if not isinstance(platform_stack, list):
            platform_stack = []
        knowledge_resources = snapshot.get("knowledge_resources", {}) if isinstance(snapshot.get("knowledge_resources"), dict) else {}
        required_resources = knowledge_resources.get("required", []) if isinstance(knowledge_resources.get("required"), list) else []
        recommended_resources = knowledge_resources.get("recommended", []) if isinstance(knowledge_resources.get("recommended"), list) else []
        tools = snapshot.get("tools", {}) if isinstance(snapshot.get("tools"), dict) else {}
        mcp = snapshot.get("mcp", {}) if isinstance(snapshot.get("mcp"), dict) else {}
        template_groups = snapshot.get("templates", {}) if isinstance(snapshot.get("templates"), dict) else {}
        processes = snapshot.get("processes", {}).get("enabled", []) if isinstance(snapshot.get("processes"), dict) else []
        project_templates = template_groups.get("project", []) if isinstance(template_groups.get("project"), list) else []
        workplace_coordination = snapshot.get("workplace_coordination", {}) if isinstance(snapshot.get("workplace_coordination"), dict) else {}
        resolved_context = snapshot.get("resolved_context", {}) if isinstance(snapshot.get("resolved_context"), dict) else {}
        selected_specializations = resolved_context.get("selected_specializations", []) if isinstance(resolved_context.get("selected_specializations"), list) else []
        applied_project_overrides = resolved_context.get("applied_project_overrides", []) if isinstance(resolved_context.get("applied_project_overrides"), list) else []
        effective_resources = resolved_context.get("effective_resources", []) if isinstance(resolved_context.get("effective_resources"), list) else []
        provided_capabilities = resolved_context.get("provided_capabilities", []) if isinstance(resolved_context.get("provided_capabilities"), list) else []
        execution_route = resolved_context.get("execution_route", {}) if isinstance(resolved_context.get("execution_route"), dict) else {}
        capability_resolution = resolved_context.get("capability_resolution", {}) if isinstance(resolved_context.get("capability_resolution"), dict) else {}
        resolution_conflicts = resolved_context.get("conflicts", []) if isinstance(resolved_context.get("conflicts"), list) else []
        resolved_parameters = snapshot.get("resolved_parameters", {}) if isinstance(snapshot.get("resolved_parameters"), dict) else {}
        parameter_resolution = snapshot.get("parameter_resolution", {}) if isinstance(snapshot.get("parameter_resolution"), dict) else {}
        parameter_sources = parameter_resolution.get("sources", []) if isinstance(parameter_resolution.get("sources"), list) else []
        parameter_conflicts = parameter_resolution.get("conflicts", []) if isinstance(parameter_resolution.get("conflicts"), list) else []

        def md_items(items: list[Any], empty: str = "None.") -> str:
            if not items:
                return f"- {empty}"
            output: list[str] = []
            for item in items:
                if isinstance(item, dict):
                    label = item.get("id") or item.get("path") or item
                    status = item.get("status")
                    severity = item.get("severity")
                    suffix = f" ({status}, {severity})" if status or severity else ""
                    output.append(f"- {label}{suffix}")
                else:
                    output.append(f"- {item}")
            return "\n".join(output)

        reasons = reasons or []
        return "\n".join(
            [
                "# Project Context Snapshot",
                "",
                "## Generated",
                "",
                f"- generated_at: {meta.get('generated_at', 'unknown')}",
                f"- valid_until: {meta.get('valid_until', 'unknown')}",
                "",
                "## Freshness",
                "",
                freshness + (f": {', '.join(reasons)}" if reasons else ""),
                "",
                "## Project",
                "",
                f"- id: {project.get('id', 'unknown')}",
                f"- name: {project.get('name', 'unknown')}",
                "",
                "## Flow Root",
                "",
                f"`{flow.get('root', '.')}/`",
                "",
                "## Linked ProcessForge",
                "",
                f"- version: {process_forge.get('version', 'unknown')}",
                f"- constraint: {process_forge.get('version_constraint', 'unknown')}",
                f"- install_mode: {process_forge.get('install_mode', 'linked')}",
                f"- distribution: {distribution.get('id', 'processforge')} ({distribution.get('status', 'unknown')})",
                "",
                "## Coordination Mode",
                "",
                f"- project_mode: {workplace_coordination.get('project_mode', 'inherit')}",
                f"- workplace_default_project_mode: {workplace_coordination.get('workplace_default_project_mode', 'simple')}",
                f"- effective_mode: {workplace_coordination.get('effective_mode', 'simple')}",
                f"- director_available_at_workplace: {str(bool(workplace_coordination.get('director_available_at_workplace', False))).lower()}",
                f"- director_required: {str(bool(workplace_coordination.get('director_required', False))).lower()}",
                "",
                "## Connected Knowledge Packages",
                "",
                md_items(snapshot.get("knowledge_stack", [])),
                "",
                "## Platform Contracts",
                "",
                md_items(platforms),
                "",
                "## Platform Stack",
                "",
                md_items(platform_stack),
                "",
                "## Selected Specializations",
                "",
                md_items(selected_specializations),
                "",
                "## Effective Resources",
                "",
                md_items(effective_resources),
                "",
                "## Provided Capabilities",
                "",
                md_items(provided_capabilities),
                "",
                "## Execution Route",
                "",
                f"- process: {execution_route.get('process') or 'None.'}",
                f"- required_capabilities: {', '.join(execution_route.get('required_capabilities', [])) if isinstance(execution_route.get('required_capabilities'), list) and execution_route.get('required_capabilities') else 'None.'}",
                f"- required_evidence: {', '.join(execution_route.get('required_evidence', [])) if isinstance(execution_route.get('required_evidence'), list) and execution_route.get('required_evidence') else 'None.'}",
                "",
                "## Capability Resolution",
                "",
                f"- satisfied: {len(capability_resolution.get('satisfied', [])) if isinstance(capability_resolution.get('satisfied'), list) else 0}",
                f"- unsatisfied: {len(capability_resolution.get('unsatisfied', [])) if isinstance(capability_resolution.get('unsatisfied'), list) else 0}",
                "",
                "## Applied Project Overrides",
                "",
                md_items(applied_project_overrides),
                "",
                "## Resolved Parameters",
                "",
                f"- namespaces: {', '.join(sorted(str(key) for key in resolved_parameters)) if resolved_parameters else 'None.'}",
                f"- sources: {len(parameter_sources)}",
                f"- conflicts: {len(parameter_conflicts)}",
                "",
                "## Resolution Conflicts",
                "",
                md_items(resolution_conflicts),
                "",
                "## Required Knowledge Resources",
                "",
                md_items(required_resources),
                "",
                "## Recommended Knowledge Resources",
                "",
                md_items(recommended_resources),
                "",
                "## Enabled Processes",
                "",
                md_items(processes),
                "",
                "## Required Capabilities",
                "",
                md_items(capabilities.get("required", [])),
                "",
                "## Optional Capabilities",
                "",
                md_items(capabilities.get("optional", [])),
                "",
                "## Required Tools",
                "",
                md_items(tools.get("required", []) if isinstance(tools, dict) else []),
                "",
                "## Recommended Tools",
                "",
                md_items(tools.get("recommended", []) if isinstance(tools, dict) else []),
                "",
                "## Required MCP",
                "",
                md_items(mcp.get("required", []) if isinstance(mcp, dict) else []),
                "",
                "## Recommended MCP",
                "",
                md_items(mcp.get("recommended", []) if isinstance(mcp, dict) else []),
                "",
                "## Hard Policies",
                "",
                md_items(policies.get("hard", []) if isinstance(policies, dict) else []),
                "",
                "## Preferences",
                "",
                md_items(policies.get("preferences", []) if isinstance(policies, dict) else []),
                "",
                "## Project Templates",
                "",
                md_items(project_templates),
                "",
                "## Required Templates",
                "",
                md_items(template_groups.get("required", []) if isinstance(template_groups, dict) else []),
                "",
                "## Recommended Templates",
                "",
                md_items(template_groups.get("recommended", []) if isinstance(template_groups, dict) else []),
                "",
                "## Session Start",
                "",
                "Read in this order:",
                "",
                *[f"{index}. {item}" for index, item in enumerate(snapshot.get("session", {}).get("startup_read_order", []), 1)],
                "",
                f"Telemetry root: `{snapshot.get('session', {}).get('telemetry_root', 'runtime/telemetry')}`",
                f"Events log: `{snapshot.get('session', {}).get('events_log', 'runtime/events/events.sqlite3')}`",
                "",
                "## Current Risks",
                "",
                "- Markdown files are human-readable context and are not authoritative structured merge sources.",
                "- If freshness is stale, refresh before using required capability decisions.",
                "",
                "## Refresh Instructions",
                "",
                "Run `python bin/pf.py project-context-refresh --project-root <project-root>` from the ProcessForge distribution root, or `python .pf/runtime/bin/pf.py project-context-refresh --project-root .` inside the linked project.",
                "",
            ]
        )
