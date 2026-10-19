"""Existing project initialization file generation over concrete Core owners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.markdown import markdown_list
from ..common.values import as_list
from ..common.yaml_dump import dump_yaml
from .classifier_sources import ProjectClassifierSourceReader
from .context_policy import ProjectContextPolicy as _ProjectContextPolicy
from .coordination import ProjectCoordinationReader
from .initialization_discovery import ProjectDiscoveryReader, ProjectResourceMatcher
from .initialization_inputs import ProjectInitializationInputs
from .metadata import PROJECT_FLOW_ROOT
from .platform_resolution import PlatformContractResolver
from .platform_selection import ProjectPlatformSelectionService
from .platforms import PlatformContractReader
from .runtime_launchers import ProjectRuntimeLauncherBuilder


class ProjectFileTemplateBuilder:
    """Generate the existing project files with explicit roots and live readers."""

    def __init__(
        self,
        distribution_root: Path,
        *,
        discovery: ProjectDiscoveryReader | None = None,
        resources: ProjectResourceMatcher | None = None,
        initialization_inputs: ProjectInitializationInputs | None = None,
        platform_selection: ProjectPlatformSelectionService | None = None,
        coordination: ProjectCoordinationReader | None = None,
        platform_resolver: PlatformContractResolver | None = None,
        runtime_launchers: ProjectRuntimeLauncherBuilder | None = None,
    ) -> None:
        self.distribution_root = distribution_root
        self.discovery = discovery if discovery is not None else ProjectDiscoveryReader(ProjectClassifierSourceReader(distribution_root))
        self.resources = resources if resources is not None else ProjectResourceMatcher(PlatformContractReader(distribution_root))
        self.initialization_inputs = initialization_inputs if initialization_inputs is not None else ProjectInitializationInputs()
        self.platform_selection = platform_selection if platform_selection is not None else ProjectPlatformSelectionService(distribution_root)
        self.coordination = coordination if coordination is not None else ProjectCoordinationReader()
        self.platform_resolver = platform_resolver if platform_resolver is not None else PlatformContractResolver(distribution_root)
        self.runtime_launchers = runtime_launchers if runtime_launchers is not None else ProjectRuntimeLauncherBuilder()

    def build_project_files(self, project_root: Path, workplace_manifest: Path, answers: dict[str, Any]) -> dict[Path, str]:
        flow_root = project_root / PROJECT_FLOW_ROOT
        detected = self.discovery.detect_project(project_root, workplace_manifest)
        defaults = self.initialization_inputs.defaults(project_root, answers, detected)
        detected["platforms"] = self.platform_selection.selected(detected, answers, defaults["type"], workplace_manifest, project_root)
        mode = self.initialization_inputs.mode(project_root, answers)
        coordination_answers = answers.get("coordination", {}) if isinstance(answers.get("coordination"), dict) else {}
        project_coordination = self.coordination.project_defaults(coordination_answers.get("mode", "inherit"))
        if isinstance(coordination_answers.get("director"), dict):
            project_coordination["director"].update(coordination_answers["director"])
        required = answers.get("required_capabilities") if isinstance(answers.get("required_capabilities"), list) else []
        optional = answers.get("optional_capabilities") if isinstance(answers.get("optional_capabilities"), list) else []
        required = [str(item) for item in required if str(item)]
        optional = [str(item) for item in optional if str(item)]
        platform_resolution = self.platform_resolver.resolve(workplace_manifest, detected["platforms"], project_root=project_root)
        required_platform_missing, recommended_platform_missing = self.platform_selection.resource_findings(workplace_manifest, platform_resolution)
        required = sorted(set(required).union(platform_resolution["required_capabilities"]))
        matches = self.resources.match_global_resources(workplace_manifest, detected, required, optional)
        knowledge_stack = [
            {"id": "processforge.core", "version": "^1.0", "source": "distribution", "distribution": "processforge"},
        ]
        for package_id in platform_resolution["knowledge_packages"]:
            knowledge_stack.append(
                {
                    "id": package_id,
                    "version": "*",
                    "source": "workplace",
                    "registry": "package_roots",
                    "load_policy": "on_demand",
                    "required_by": sorted(
                        item["id"]
                        for item in platform_resolution["contracts"]
                        if package_id in item.get("required", {}).get("knowledge_packages", [])
                        or package_id in item.get("recommended", {}).get("knowledge_packages", [])
                    ),
                }
            )
        knowledge_stack.append({"id": f"project.{defaults['id']}", "version": "1.0.0", "source": "project"})
        answered_requirements = answers.get("context_requirements") if isinstance(answers.get("context_requirements"), dict) else {}
        context_requirements = answered_requirements or {
            "knowledge_packages": [
                {"id": "processforge.core", "constraint": "^1.0", "required": True},
                *[
                    {"id": package_id, "constraint": "*", "required": package_id in platform_resolution["required_knowledge_packages"]}
                    for package_id in sorted(set(platform_resolution["knowledge_packages"]))
                ],
                {"id": f"project.{defaults['id']}", "constraint": "1.0.0", "required": True},
            ],
            "knowledge_resources": [],
            "template_packages": [],
            "templates": [{"id": item, "required": item in platform_resolution["required_templates"]} for item in sorted(set(platform_resolution["required_templates"] + platform_resolution["recommended_templates"]))],
            "tools": [{"id": item, "required": item in platform_resolution["required_tools"]} for item in sorted(set(platform_resolution["required_tools"] + platform_resolution["recommended_tools"]))],
            "platform_contracts": [{"id": item, "required": True} for item in sorted(set(detected["platforms"]))],
        }
        context_policy = answers.get("context_policy") if isinstance(answers.get("context_policy"), dict) else _ProjectContextPolicy().build({})
        project_parameters = answers.get("parameters") if isinstance(answers.get("parameters"), dict) else {}

        public_manifest = {
            "schema_version": 1,
            "process_forge": {
                "version": "1.0.0",
                "version_constraint": "^1.0",
                "mode": "file_only",
                "install_mode": "linked",
                "distribution": {"id": "processforge", "source": "workplace"},
                "runner_required": False,
                "backend_required": False,
            },
            "project": {"id": defaults["id"], "name": defaults["name"], "type": defaults["type"]},
            "flow": {
                "root": PROJECT_FLOW_ROOT,
                "manifest": f"{PROJECT_FLOW_ROOT}/process-forge.yaml",
                "local_config": f"{PROJECT_FLOW_ROOT}/process-forge.local.yaml",
            },
            "workplace": {"reference": "local_file", "local_config": f"{PROJECT_FLOW_ROOT}/process-forge.local.yaml"},
            "coordination": project_coordination,
            "process": str(answers.get("process") or ""),
            "specializations": [str(item) for item in as_list(answers.get("specializations")) if str(item)],
            "detected": {
                "status": detected["status"],
                "languages": detected["languages"],
                "platforms": detected["platforms"],
                "project_kind": detected["project_kind"],
                "tags": detected["tags"],
                "loaded_classifiers": detected["loaded_classifiers"],
                "matched_rules": detected["matched_rules"],
            },
            "platform_contracts": platform_resolution["contracts"],
            "platform_stack": platform_resolution["platform_stack"],
            "paths": {
                "processes": "processes",
                "packages": "packages",
                "templates": "templates",
                "assignments": "assignments",
                "artifacts": "artifacts",
                "contexts": "contexts",
                "logs": "logs",
                "handoffs": "handoffs",
                "reviews": "reviews",
                "adr": "adr",
                "schemas": "schemas",
                "registries": "registries",
                "runtime": "runtime",
                "hooks": "hooks.yaml",
            },
            "knowledge_stack": knowledge_stack,
            "parameters": project_parameters,
            "context_requirements": context_requirements,
            "context_policy": context_policy,
            "required_capabilities": required,
            "optional_capabilities": optional,
            "selected_resources": {
                "required": {
                    "knowledge_packages": platform_resolution["required_knowledge_packages"],
                    "tools": platform_resolution["required_tools"],
                    "mcp": platform_resolution["required_mcp"],
                    "templates": platform_resolution["required_templates"],
                },
                "recommended": {
                    "knowledge_packages": platform_resolution["recommended_knowledge_packages"],
                    "tools": platform_resolution["recommended_tools"],
                    "mcp": platform_resolution["recommended_mcp"],
                    "templates": platform_resolution["recommended_templates"],
                },
            },
            "policies": {
                "one_writer_per_file_scope": True,
                "approved_artifacts_are_protected": True,
                "execution_context_is_immutable": True,
                "public_files_must_not_contain_local_absolute_paths": True,
            },
        }

        local_manifest = {
            "schema_version": 1,
            "workplace": {"manifest": str(workplace_manifest.resolve())},
            "process_forge": {"distribution_override": str(self.distribution_root.resolve())},
            "local": {"project_root": str(project_root.resolve())},
            "overrides": {"package_roots": [], "template_roots": [], "tool_preferences": {}, "parameters": {}, "context_requirements": {}, "context_policy": {}},
            "runtime": {
                "mode": "manual",
                "queue": "runtime/queue",
                "events": "runtime/events",
                "hooks": "runtime/hooks",
                "chat": "runtime/chat",
            },
        }

        from processforge_core.agent_entry.contract import encoded, load_contract
        from processforge_core.agent_entry.migration import manifest as entry_manifest

        entry_contract = load_contract()
        agents = entry_contract.render(extended=True).decode("utf-8")

        classification_report = f"""# Project Classification Report

## Status

{detected["status"]}

## Languages

{markdown_list(detected["languages"])}

## Platforms

{markdown_list(detected["platforms"])}

## Frameworks

{markdown_list(detected["frameworks"])}

## Project Type

{markdown_list(detected["project_kind"])}

## Confidence

{detected["confidence"]}

## Evidence

{markdown_list(detected["evidence"])}

## Loaded Classifiers

{markdown_list(detected["loaded_classifiers"])}

## Inactive Classifier Suggestions

{markdown_list(detected["inactive_classifier_hints"])}

## Unknowns

- Confirm exact project ownership and release workflow manually.
"""

        repository_map = f"""# Repository Map

## Status

observed

## Main Directories

{markdown_list(detected["top_dirs"])}

## Files

{markdown_list(detected["files"])}

## Critical Files

- .pf/process-forge.yaml
- .pf/process-forge.local.yaml

## Review-Protected Zones

- Existing brownfield files.
"""

        conventions = """# Project Conventions

## Observed

- Existing file layout was scanned.

## Confirmed

- None yet.

## Unknown

- Naming style.
- Coding style.
- Testing style.
- Documentation style.
- Packaging style.
"""

        toolchain = f"""# Toolchain Detection Report

## Found Project-Local Tools

None inferred from file names. Tool selection comes from loaded registries, platform contracts, and explicit project configuration.

## Available Global Tools

{markdown_list(matches["matched_tools"])}

## Missing Tools

{markdown_list(matches["missing_required"])}

## Required Capabilities

{markdown_list(required)}

## Optional Capabilities

{markdown_list(optional)}

## Fallback Mapping

- Missing required capabilities must be resolved before strict automation.
"""

        mcp_report = f"""# MCP Capability Report

## Useful MCP

{markdown_list(optional)}

## Matched MCP

{markdown_list(matches["matched_mcp"])}

## Missing MCP

{markdown_list([cap for cap in optional if cap not in matches["matched_mcp"]])}

## Recommendations

- Treat MCP providers as optional unless a process stage marks them required.
"""

        template_report = f"""# Template Matching Report

## Matched Templates

{markdown_list(matches["matched_templates"])}

## Project Templates

- templates/

## Suggested Templates

- assignment-template
- artifact-template
- review-template
- handoff-template

## Templates Requiring Adaptation

- Domain-specific templates need review before use.

## Templates Not Safe To Use

- Templates containing local absolute paths or credential values.
"""

        hooks = {
            "schema_version": 1,
            "hooks": {
                "mode": "outbox",
                "default_timeout": 30,
                "network_send_enabled": False,
                "targets": [
                    {
                        "id": "wtaicc-outbox",
                        "type": "outbox",
                        "enabled": True,
                        "path": ".pf/runtime/hooks/outbox/wtaicc",
                        "event_types": ["*"],
                    },
                    {
                        "id": "wtaicc-webhook-future",
                        "type": "webhook",
                        "enabled": False,
                        "url_ref": "wtaicc.webhook.url",
                        "secret_ref": "wtaicc.webhook.secret",
                        "event_types": ["assignment.completed", "artifact.created", "chat.message.recorded"],
                    },
                ],
            },
            "policies": {
                "do_not_send_network_by_default": True,
                "secrets_are_refs_only": True,
                "chat_content_requires_opt_in": True,
                "command_hooks_can_block": True,
                "outbox_hooks_are_non_blocking": True,
            },
        }

        resource_report = f"""# Global Resource Matching Report

## Matched Platforms

{markdown_list(matches["matched_platforms"])}

## Missing Required Platform Contracts

{markdown_list(platform_resolution["missing_required_contracts"])}

## Missing Required Platform Resources

{markdown_list([f"{item['kind']}: {item['id']}" for item in required_platform_missing])}

## Missing Recommended Platform Resources

{markdown_list([f"{item['kind']}: {item['id']}" for item in recommended_platform_missing])}

## Matched Packages

{markdown_list(matches["matched_packages"])}

## Matched Tools

{markdown_list(matches["matched_tools"])}

## Matched MCP

{markdown_list(matches["matched_mcp"])}

## Matched Templates

{markdown_list(matches["matched_templates"])}

## Missing Required Capabilities

{markdown_list(matches["missing_required"])}

## Optional Missing Capabilities

{markdown_list(matches["optional_missing"])}

## Capability Diagnostics

- Missing required capabilities are registry declaration gaps, not proof that
  the active runtime lacks access.
- If runtime access was verified independently, record the evidence in
  `.pf/artifacts/capability-waivers.yaml` with `capability`, `status`,
  `reason`, and `evidence`.
- Prefer registering the real provider in the workplace registry when the
  capability should be reusable.

## Conflicts

{markdown_list(matches["conflicts"])}

## Recommendations

- Review missing required capabilities before using strict automated stages.
"""

        profile = f"""# Project Profile

## Status

observed

## Project

- id: {defaults["id"]}
- name: {defaults["name"]}
- type: {defaults["type"]}

## Purpose

Unknown until reviewed.

## Platforms

{markdown_list(detected["platforms"])}

## Languages

{markdown_list(detected["languages"])}

## Main Directories

{markdown_list(detected["top_dirs"])}

## Public Zones

- .pf/process-forge.yaml
- .pf/hooks.yaml
- docs/
- root product assets

## Private Zones

- .pf/process-forge.local.yaml
- .pf/runtime/
- .pf/private-notes/
- .secrets/

## Suggested Processes

- project-initialization

## Constraints

- Keep local absolute paths out of public files.
"""

        proposal = f"""# Project Init Proposal

## Project

- id: {defaults["id"]}
- name: {defaults["name"]}
- mode: {mode}

## Planned Public Files

- AGENTS.md
- .pf/AGENTS.md
- .pf/agent-entry.json
- .pf/process-forge.yaml
- .pf/hooks.yaml
- .pf/packages/project.{defaults["id"]}.yaml
- .pf/artifacts/project-profile.md
- .pf/artifacts/project-classification-report.md
- .pf/artifacts/repository-map.md
- .pf/artifacts/project-conventions.md
- .pf/artifacts/toolchain-detection-report.md
- .pf/artifacts/mcp-capability-report.md
- .pf/artifacts/template-matching-report.md
- .pf/artifacts/global-resource-matching-report.md
- .pf/reviews/project-init-review.md

## Planned Private Files

- .pf/process-forge.local.yaml

## Risks

- Existing files are not overwritten without explicit approval.
- Root and hidden AGENTS receive the same minimum contract K, preserving user text.
- Entry ownership conflicts or known budget loss block apply; generic force cannot override them.
- Detection results are observed, not confirmed.

## Recommendation

Run doctor after apply mode.
"""

        first_assignment = {
            "schema_version": 1,
            "id": "first-assignment",
            "title": "Verify ProcessForge project onboarding",
            "run_id": f"project-onboarding-{defaults['id']}",
            "process": "project-onboarding",
            "status": "open",
            "objective": "Verify that this project is connected to ProcessForge and ready for future assignment work.",
            "iterations": [],
            "result": {"status": "pending", "summary": "", "artifacts": []},
            "tasks": [
                "Read root AGENTS.md (or .pf/AGENTS.md in an unmigrated project)",
                "Inspect the current project through pf.context",
                "Use pf.search or pf.resolve when project knowledge is needed",
                "Use pf.work.start for substantive governed work",
                "Confirm the first working process for this project",
                "Create .pf/artifacts/first-assignment-readiness-note.md",
            ],
            "expected_artifacts": [
                ".pf/artifacts/first-assignment-readiness-note.md",
            ],
        }

        onboarding_report = f"""# Project Onboarding Report

## Status

applied

## Project

- id: {defaults["id"]}
- name: {defaults["name"]}
- type: {defaults["type"]}

## Process Boundary

Project onboarding creates root `AGENTS.md`, hidden `.pf/AGENTS.md`, `.pf/agent-entry.json` and project-local `.pf/` state, linked to an existing workplace. It does not recreate the workplace, copy global packages into the project, or write local absolute paths to public files.

## Created First-Run Files

- AGENTS.md
- .pf/AGENTS.md
- .pf/agent-entry.json
- .pf/assignments/first-assignment.yaml (compatibility placeholder, not required Work)
- .pf/contexts/project-context.snapshot.yaml
- .pf/artifacts/project-onboarding-report.md
- .pf/reviews/project-onboarding-review.md
- .pf/handoffs/project-ready-handoff.md
"""

        onboarding_review = """# Project Onboarding Review

## Reviewed Object

Project onboarding output.

## Result

pass_with_conditions

## Findings

- The onboarding output is file-only and keeps workplace and project responsibilities separate.
- Detection results are observed until manually confirmed.

## Required Follow-Up

- Run `doctor-project` after onboarding.
- Verify current context with `pf.context`, then use `pf.work.start` for substantive work.
- The generated first assignment is an optional compatibility placeholder, not required Work.
"""

        onboarding_handoff = f"""# Handoff: project-onboarding -> governed-work

Objective:
Connect `{defaults["id"]}` to ProcessForge and prepare for governed work.

Current status:
Project onboarding files were generated.

Input artifacts:
- AGENTS.md
- .pf/AGENTS.md
- .pf/agent-entry.json
- .pf/process-forge.yaml
- .pf/process-forge.local.yaml
- .pf/contexts/project-context.snapshot.yaml
- .pf/assignments/first-assignment.yaml (optional compatibility placeholder)

Files changed:
- AGENTS.md
- .pf/
- .gitignore

Files not to touch:
- Workplace registry files unless the user explicitly requests workplace changes.
- Global packages unless a separate workplace process approves it.

Known issues:
- Detection is observed, not domain-approved.

Required checks:
- `python .pf/runtime/bin/pf.py doctor-project --project-root .`
- `python .pf/runtime/bin/pf.py project-context-check --project-root .`

Next recommended action:
Read root `AGENTS.md`, verify `pf.context`, and use `pf.work.start` for the requested work.
Use its returned Run/assignment/capsule identities with `pf.work.state` and
`pf.work.transition` until `run_completed`. Handle `process_choice_required`
from the offered processes. Do not select the onboarding placeholder as ordinary Work.
`agent-start-prompt` prints current guidance without writing files or trusting stored START.
"""

        package = {
            "schema_version": 1,
            "id": f"project.{defaults['id']}",
            "name": f"{defaults['name']} Knowledge",
            "version": "1.0.0",
            "kind": "project",
            "scope": "project",
            "status": "draft",
            "project": {"id": defaults["id"]},
            "provides": {"capabilities": [f"project.{defaults['id']}.context"]},
            "content": {
                "references": [
                    "artifacts/project-profile.md",
                    "artifacts/repository-map.md",
                    "artifacts/project-conventions.md",
                    "artifacts/toolchain-detection-report.md",
                    "artifacts/template-matching-report.md",
                ]
            },
            "resources": [
                {
                    "id": "project-profile",
                    "kind": "note_collection",
                    "title": "Project profile and repository map",
                    "path": "artifacts/project-profile.md",
                    "load_policy": "when_relevant",
                    "index_policy": "full_text",
                },
                {
                    "id": "project-artifacts",
                    "kind": "reference",
                    "title": "Project ProcessForge artifacts",
                    "path": "artifacts",
                    "load_policy": "on_demand",
                    "index_policy": "metadata",
                },
            ],
            "policies": {
                "file_ownership": {"default": "one_writer_per_scope"},
                "public_cleanliness": {"forbid_absolute_local_paths": True},
            },
        }

        review = """# Project Init Review

## Reviewed Object

Project Init output.

## Reviewer

ProcessForge init reviewer

## Criteria

- Public/private separation is correct.
- Local config is ignored.
- Public manifest contains no local absolute paths.
- Brownfield files were not overwritten without approval.
- Required reports exist.

## Result

pass_with_conditions

## Findings

- Detection results are observed until manually confirmed.

## Blocking Issues

- None recorded.

## Evidence

- artifacts/project-init-proposal.md
- .pf/process-forge.yaml
- .pf/process-forge.local.yaml

## Recommendation

Review and confirm observed conventions.
"""

        files = {
            project_root / "AGENTS.md": entry_contract.render().decode("utf-8"),
            flow_root / "AGENTS.md": agents,
            flow_root / "agent-entry.json": encoded(entry_manifest(entry_contract)).decode("utf-8"),
            flow_root / "process-forge.yaml": dump_yaml(public_manifest),
            flow_root / "process-forge.local.yaml": dump_yaml(local_manifest),
            flow_root / "parameters.yaml": dump_yaml({"schema_version": 1, "kind": "processforge.parameters", "scope": "project", "parameters": {}}),
            flow_root / "hooks.yaml": dump_yaml(hooks),
            flow_root / "registries" / "project-classifiers.yaml": dump_yaml(
                {"schema_version": 1, "project_classifiers": []}
            ),
            flow_root / "assignments" / "first-assignment.yaml": dump_yaml(first_assignment),
            flow_root / "packages" / f"project.{defaults['id']}.yaml": dump_yaml(package),
            flow_root / "artifacts" / "project-profile.md": profile,
            flow_root / "artifacts" / "project-classification-report.md": classification_report,
            flow_root / "artifacts" / "repository-map.md": repository_map,
            flow_root / "artifacts" / "project-conventions.md": conventions,
            flow_root / "artifacts" / "toolchain-detection-report.md": toolchain,
            flow_root / "artifacts" / "mcp-capability-report.md": mcp_report,
            flow_root / "artifacts" / "template-matching-report.md": template_report,
            flow_root / "artifacts" / "global-resource-matching-report.md": resource_report,
            flow_root / "artifacts" / "project-init-proposal.md": proposal,
            flow_root / "artifacts" / "project-onboarding-report.md": onboarding_report,
            flow_root / "reviews" / "project-init-review.md": review,
            flow_root / "reviews" / "project-onboarding-review.md": onboarding_review,
            flow_root / "handoffs" / "project-ready-handoff.md": onboarding_handoff,
        }
        files.update(self.runtime_launchers.project_runtime_launcher_files(flow_root))
        return files
