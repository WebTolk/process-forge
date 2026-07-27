#!/usr/bin/env python3
"""Validate ProcessForge structure and YAML/JSON files against JSON Schemas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "README.ru.md",
    "QUICKSTART.md",
    "QUICKSTART.ru.md",
    "CHANGELOG.md",
    "LICENSE",
    "VERSION",
    "requirements.txt",
    ".pf/AGENTS.md",
    ".pf/process-forge.yaml",
    ".pf/hooks.yaml",
    "checksums/processforge.sha256",
    "docs/concepts/file-first-processes.md",
    "docs/concepts/workplace-layer.md",
    "docs/concepts/project-flow-layer.md",
    "docs/concepts/cascade-merge.md",
    "docs/concepts/execution-context-package.md",
    "docs/concepts/reusable-templates.md",
    "docs/concepts/process-evolution.md",
    "docs/concepts/evolve-mechanism.md",
    "docs/concepts/knowledge-candidates.md",
    "docs/concepts/workplace-learning-queue.md",
    "docs/concepts/knowledge-hub.md",
    "docs/concepts/workplace-init.md",
    "docs/concepts/project-init.md",
    "docs/concepts/linked-workplace-model.md",
    "docs/concepts/path-constants.md",
    "docs/concepts/runtime-model.md",
    "docs/concepts/runtime-drivers.md",
    "docs/concepts/process-supervisor.md",
    "docs/concepts/agent-ledger.md",
    "docs/concepts/process-transitions.md",
    "docs/concepts/handoff-contracts.md",
    "docs/concepts/agent-director.md",
    "docs/concepts/project-coordination-modes.md",
    "docs/concepts/shell-agent-subagent-policy.md",
    "docs/concepts/package-roots.md",
    "docs/concepts/project-snapshot.md",
    "docs/concepts/hooks-events.md",
    "docs/concepts/path-resolution.md",
    "docs/concepts/resource-management.md",
    "docs/concepts/workplace-resources.md",
    "docs/concepts/knowledge-resources.md",
    "docs/concepts/documentation-import.md",
    "docs/concepts/template-management.md",
    "docs/concepts/tool-mcp-registration.md",
    "docs/concepts/template-packages.md",
    "docs/concepts/platform-contracts.md",
    "docs/concepts/platform-inheritance.md",
    "docs/concepts/knowledge-resource-navigation.md",
    "docs/concepts/resource-privacy.md",
    "docs/concepts/resource-events.md",
    "docs/concepts/processforge-self-update.md",
    "docs/concepts/update-sites.md",
    "docs/concepts/update-lifecycle.md",
    "docs/concepts/workplace-terms.md",
    "docs/concepts/wtaicc-future-compatibility.md",
    "docs/concepts/public-private-config.md",
    "docs/concepts/capability-resolution.md",
    "docs/concepts/session-bootstrap.md",
    "docs/concepts/project-context-snapshot.md",
    "docs/concepts/project-context-lock-model.md",
    "docs/concepts/session-telemetry.md",
    "docs/concepts/process-events.md",
    "docs/concepts/semantic-parity.md",
    "docs/concepts/runs-tasks-iterations.md",
    "docs/concepts/process-definition-run-task-iteration.md",
    "docs/concepts/hooks-and-webhooks.md",
    "docs/concepts/chat-relay.md",
    "docs/concepts/global-agent-section.md",
    "docs/concepts/project-flow-root.md",
    "docs/concepts/assignment-front-matter.md",
    "docs/concepts/context-freshness.md",
    "docs/concepts/context-resolution.md",
    "docs/concepts/instruction-conflicts.md",
    "docs/concepts/context-cache.md",
    "docs/concepts/context-index.md",
    "docs/concepts/context-capsule.md",
    "docs/concepts/multi-agent-orchestration.md",
    "docs/authoring/workplace-configuration.md",
    "docs/authoring/project-initialization.md",
    "docs/authoring/knowledge-package-authoring.md",
    "docs/authoring/reusable-template-authoring.md",
    "docs/authoring/template-authoring.md",
    "docs/authoring/platform-contract-authoring.md",
    "docs/getting-started/resource-authoring.md",
    "docs/authoring/task-batch-execution.md",
    "docs/authoring/process-authoring.md",
    "docs/authoring/update-sites-for-packages.md",
    "docs/authoring/authoring-parity.md",
    "docs/authoring/backfill-existing-processes.md",
    "docs/ru/index.md",
    "docs/ru/getting-started/installation.md",
    "docs/ru/getting-started/first-run.md",
    "docs/ru/getting-started/workplace-initialization.md",
    "docs/ru/getting-started/project-onboarding.md",
    "docs/ru/getting-started/agent-prompts.md",
    "docs/ru/getting-started/create-your-first-process.md",
    "docs/ru/getting-started/task-batch-workflow.md",
    "docs/ru/getting-started/guided-workplace-setup.md",
    "docs/ru/getting-started/multi-agent-orchestration.md",
    "docs/ru/getting-started/runtime-driver-supervisor.md",
    "docs/ru/getting-started/update-system.md",
    "docs/ru/getting-started/evolve-learning-loop.md",
    "docs/ru/authoring/reusable-template-authoring.md",
    "docs/ru/authoring/knowledge-package-authoring.md",
    "docs/ru/authoring/platform-contract-authoring.md",
    "docs/ru/authoring/process-authoring.md",
    "docs/ru/authoring/authoring-parity.md",
    "docs/ru/authoring/backfill-existing-processes.md",
    "docs/ru/authoring/update-sites-for-packages.md",
    "docs/ru/concepts/workplace-vs-project.md",
    "docs/ru/concepts/runtime-model.md",
    "docs/ru/concepts/runtime-drivers.md",
    "docs/ru/concepts/process-supervisor.md",
    "docs/ru/concepts/agent-ledger.md",
    "docs/ru/concepts/process-transitions.md",
    "docs/ru/concepts/handoff-contracts.md",
    "docs/ru/concepts/agent-director.md",
    "docs/ru/concepts/project-coordination-modes.md",
    "docs/ru/concepts/shell-agent-subagent-policy.md",
    "docs/ru/concepts/path-constants.md",
    "docs/ru/concepts/package-roots.md",
    "docs/ru/concepts/project-snapshot.md",
    "docs/ru/concepts/runs-tasks-iterations.md",
    "docs/ru/concepts/process-definition-run-task-iteration.md",
    "docs/ru/concepts/platform-contracts.md",
    "docs/ru/concepts/platform-inheritance.md",
    "docs/ru/concepts/knowledge-resource-navigation.md",
    "docs/ru/concepts/hooks-events.md",
    "docs/ru/concepts/semantic-parity.md",
    "docs/ru/concepts/multi-agent-file-flow.md",
    "docs/ru/concepts/multi-agent-orchestration.md",
    "docs/ru/concepts/context-capsule.md",
    "docs/ru/concepts/project-context-lock-model.md",
    "docs/ru/concepts/update-sites.md",
    "docs/ru/concepts/update-lifecycle.md",
    "docs/ru/concepts/evolve-mechanism.md",
    "docs/ru/concepts/knowledge-candidates.md",
    "docs/ru/concepts/workplace-learning-queue.md",
    "docs/ru/concepts/knowledge-hub.md",
    "docs/ru/releases/initial-release.md",
    "docs/ru/known-limitations.md",
    "docs/known-limitations.md",
    "docs/assets/processforge-architecture.svg",
    "docs/assets/processforge-run-lifecycle.svg",
    "docs/assets/processforge-authoring-parity.svg",
    "docs/processes/process-authoring.md",
    "docs/processes/process-supervisor.md",
    "docs/processes/software-feature-development.md",
    "docs/ru/processes/software-feature-development.md",
    "docs/getting-started/task-batch-workflow.md",
    "docs/getting-started/guided-workplace-setup.md",
    "docs/getting-started/multi-agent-orchestration.md",
    "docs/getting-started/runtime-driver-supervisor.md",
    "docs/getting-started/update-system.md",
    "docs/getting-started/evolve-learning-loop.md",
    "docs/getting-started/agent-ledger-process-transitions.md",
    "docs/ru/getting-started/agent-ledger-process-transitions.md",
    "docs/getting-started/create-your-first-process.md",
    "docs/validation/doctor-workplace.md",
    "docs/validation/doctor-project.md",
    "docs/validation/doctor-context.md",
    "schemas/process-forge-manifest.schema.json",
    "schemas/workplace.schema.json",
    "schemas/terms.schema.json",
    "schemas/distributions-registry.schema.json",
    "schemas/path-constants.schema.json",
    "schemas/path-ref.schema.json",
    "schemas/knowledge-resource.schema.json",
    "schemas/knowledge-resource-index.schema.json",
    "schemas/knowledge-resource-add-request.schema.json",
    "schemas/documentation-import-plan.schema.json",
    "schemas/platform-contract.schema.json",
    "schemas/template-package.schema.json",
    "schemas/tool-definition.schema.json",
    "schemas/mcp-definition.schema.json",
    "schemas/resource-management-event.schema.json",
    "schemas/processforge-update-index.schema.json",
    "schemas/processforge-update-assessment.schema.json",
    "schemas/platform-registry.schema.json",
    "schemas/knowledge-roots-registry.schema.json",
    "schemas/package-roots-registry.schema.json",
    "schemas/template-registry.schema.json",
    "schemas/tool-registry.schema.json",
    "schemas/mcp-registry.schema.json",
    "schemas/update-source-registry.schema.json",
    "schemas/update-site.schema.json",
    "schemas/entity-update-sites.schema.json",
    "schemas/update-site-overrides.schema.json",
    "schemas/installed-update-sites.schema.json",
    "schemas/normalized-update-manifest.schema.json",
    "schemas/installed-subjects.schema.json",
    "schemas/update-candidates.schema.json",
    "schemas/update-notifications.schema.json",
    "schemas/update-apply-plan.schema.json",
    "schemas/update-stage-record.schema.json",
    "schemas/update-rollback-record.schema.json",
    "schemas/workplace-init-answers.schema.json",
    "schemas/guided-workplace-setup-answers.schema.json",
    "schemas/guided-workplace-setup-proposal.schema.json",
    "schemas/orchestrator-task-plan.schema.json",
    "schemas/worker-launch-prompt.schema.json",
    "schemas/runtime-driver.schema.json",
    "schemas/runtime-driver-registry.schema.json",
    "schemas/agent-run-state.schema.json",
    "schemas/supervisor-profile.schema.json",
    "schemas/supervisor-state.schema.json",
    "schemas/agent-registry.schema.json",
    "schemas/agent-session-event.schema.json",
    "schemas/agent-presence.schema.json",
    "schemas/agent-lease.schema.json",
    "schemas/process-route-map.schema.json",
    "schemas/process-transition.schema.json",
    "schemas/process-handoff.schema.json",
    "schemas/handoff-input-manifest.schema.json",
    "schemas/handoff-return-package.schema.json",
    "schemas/agent-director-policy.schema.json",
    "schemas/continuation-capsule.schema.json",
    "schemas/orchestrator-shell-agent-plan.schema.json",
    "schemas/worker-process-command.schema.json",
    "schemas/project-init-answers.schema.json",
    "schemas/session-start.schema.json",
    "schemas/project-context-snapshot.schema.json",
    "schemas/session-metadata.schema.json",
    "schemas/session-telemetry-event.schema.json",
    "schemas/event-envelope.schema.json",
    "schemas/process-event.schema.json",
    "schemas/processforge-event.schema.json",
    "schemas/hooks.schema.json",
    "tools/smoke_update_sites_schema.py",
    "tools/smoke_update_candidate_discovery.py",
    "tools/smoke_update_notifications.py",
    "tools/smoke_update_stage_verify_apply_file_provider.py",
    "tools/smoke_project_pf_upgrade_assessment_boundary.py",
    "tools/smoke_tool_update_policy.py",
    "tools/context_lock_smoke_helpers.py",
    "tools/smoke_resource_versioning_modes.py",
    "tools/smoke_project_context_snapshot_lock_model.py",
    "tools/smoke_project_context_freshness_policies.py",
    "tools/smoke_session_start_context_check.py",
    "tools/smoke_update_apply_marks_context_stale.py",
    "tools/smoke_capsule_pins_context_snapshot.py",
    "tools/smoke_software_lifecycle_process_contract.py",
    "tools/smoke_software_lifecycle_artifacts.py",
    "tools/smoke_software_lifecycle_description_alignment.py",
    "tools/smoke_software_lifecycle_prompt_alignment.py",
    "tools/smoke_delivery_profile_not_process.py",
    "tools/smoke_software_lifecycle_compact_mode.py",
    "tools/evolve_smoke_helpers.py",
    "tools/smoke_evolve_process_agnostic_contract.py",
    "tools/smoke_process_authoring_evolve_questions.py",
    "tools/smoke_process_authoring_materializes_evolve.py",
    "tools/smoke_generated_processes_include_evolve.py",
    "tools/smoke_builtin_processes_explicit_evolve.py",
    "tools/smoke_evolve_candidate_schema.py",
    "tools/smoke_workplace_learning_queue.py",
    "tools/smoke_evolve_candidate_export.py",
    "tools/smoke_evolve_privacy_sanitizer.py",
    "tools/smoke_knowledge_hub_import.py",
    "tools/smoke_knowledge_package_build_from_candidates.py",
    "tools/smoke_knowledge_package_release_update_manifest.py",
    "tools/smoke_evolve_learning_loop_end_to_end.py",
    "tools/smoke_software_process_uses_common_evolve.py",
    "schemas/hook-delivery.schema.json",
    "schemas/hook-result.schema.json",
    "schemas/chat-message.schema.json",
    "schemas/chat-transcript.schema.json",
    "schemas/wtaicc-outbox-payload.schema.json",
    "schemas/assignment-front-matter.schema.json",
    "schemas/run.schema.json",
    "schemas/iteration.schema.json",
    "schemas/context-index.schema.json",
    "schemas/resolved-rules.schema.json",
    "schemas/context-conflict-report.schema.json",
    "schemas/context-capsule.schema.json",
    "schemas/context-cache.schema.json",
    "schemas/process-definition.schema.json",
    "schemas/process-authoring-answers.schema.json",
    "schemas/evolution-report.schema.json",
    "schemas/knowledge-candidate.schema.json",
    "schemas/process-authoring-session.schema.json",
    "schemas/package-manifest.schema.json",
    "schemas/reusable-template.schema.json",
    "schemas/assignment.schema.json",
    "schemas/execution-context-package.schema.json",
    "schemas/artifact.schema.json",
    "schemas/review.schema.json",
    "schemas/handoff.schema.json",
    "processes/software-feature-development.yaml",
    "processes/bug-fix.yaml",
    "processes/testing.yaml",
    "processes/content-production.yaml",
    "processes/knowledge-package-improvement.yaml",
    "processes/process-version-upgrade.yaml",
    "processes/workplace-initialization.yaml",
    "processes/project-onboarding.yaml",
    "processes/project-initialization.yaml",
    "processes/session-bootstrap.yaml",
    "processes/context-resolution.yaml",
    "processes/processforge-update-check.yaml",
    "processes/knowledge-resource-add.yaml",
    "processes/documentation-mirror-import.yaml",
    "processes/knowledge-package-update.yaml",
    "processes/template-add.yaml",
    "processes/tool-register.yaml",
    "processes/mcp-register.yaml",
    "processes/platform-contract-install.yaml",
    "processes/process-template-install.yaml",
    "processes/reusable-template-authoring.yaml",
    "processes/knowledge-package-authoring.yaml",
    "processes/platform-contract-authoring.yaml",
    "processes/process-authoring.yaml",
    "processes/authoring-parity-audit.yaml",
    "processes/task-batch-execution.yaml",
    "processes/guided-workplace-setup.yaml",
    "processes/multi-agent-task-orchestration.yaml",
    "processes/runtime-driver-registry.yaml",
    "processes/process-supervisor.yaml",
    "processes/agent-director-supervision.yaml",
    "processes/orchestrator-shell-agents-supervision.yaml",
    "templates/workplace.yaml",
    "templates/terms.yaml",
    "templates/registries/distributions.yaml",
    "templates/registries/platforms.yaml",
    "templates/registries/knowledge-roots.yaml",
    "templates/registries/package-roots.yaml",
    "templates/registries/templates.yaml",
    "templates/registries/tools.yaml",
    "templates/registries/mcp.yaml",
    "templates/registries/runtime-drivers.yaml",
    "templates/runtime-drivers/manual.yaml",
    "templates/runtime-drivers/generic-shell.yaml",
    "templates/runtime-drivers/test-echo-worker.yaml",
    "templates/runtime-drivers/test-shell-agent.yaml",
    "templates/supervisor-profile.yaml",
    "templates/registries/agents.yaml",
    "templates/agent-lease.yaml",
    "templates/process-routes.yaml",
    "templates/handoff-package.yaml",
    "templates/agent-director-policy.yaml",
    "templates/continuation-capsule.yaml",
    "templates/orchestrator-shell-agent-plan.yaml",
    "templates/agent-run-state.yaml",
    "templates/worker-process-command.yaml",
    "templates/process-record.yaml",
    "templates/exit-record.yaml",
    "templates/worker-logs.md",
    "templates/registries/update-sources.yaml",
    "templates/registries/installed-subjects.yaml",
    "templates/registries/update-site-overrides.yaml",
    "templates/runtime/update/installed-update-sites.json",
    "policies/platform-id-policy.yaml",
    "policies/package-id-policy.yaml",
    "policies/core-hardcode-policy.yaml",
    "policies/public-support-policy.yaml",
    "templates/workplace-init.answers.yaml",
    "templates/guided-workplace-setup.answers.yaml",
    "templates/guided-workplace-setup.proposal.yaml",
    "templates/orchestrator-task-plan.yaml",
    "templates/worker-launch-prompt.md",
    "templates/project-init.answers.yaml",
    "templates/process-forge.yaml",
    "templates/process-forge.local.yaml",
    "templates/project-agents-template.md",
    "templates/project-init-proposal-template.md",
    "templates/project-profile-template.md",
    "templates/repository-map-template.md",
    "templates/project-conventions-template.md",
    "templates/global-resource-matching-report-template.md",
    "templates/project-init-review-template.md",
    "templates/process-authoring-answers.yaml",
    "templates/process.yaml",
    "templates/process-definition-template.yaml",
    "templates/knowledge-candidate.yaml",
    "templates/process-agent-prompt.md",
    "templates/process-doc.md",
    "prompts/workplace-initialization-agent.md",
    "prompts/project-onboarding-agent.md",
    "prompts/reusable-template-authoring-agent.md",
    "prompts/knowledge-package-authoring-agent.md",
    "prompts/platform-contract-authoring-agent.md",
    "prompts/process-authoring-agent.md",
    "prompts/authoring-parity-audit-agent.md",
    "prompts/task-batch-execution-agent.md",
    "prompts/guided-workplace-setup-agent.md",
    "prompts/multi-agent-task-orchestration-agent.md",
    "prompts/multi-agent-worker-agent.md",
    "prompts/process-supervisor-agent.md",
    "prompts/agent-director-supervision-agent.md",
    "prompts/orchestrator-shell-agents-agent.md",
    "docs/getting-started/first-run.md",
    "docs/getting-started/initialization-order.md",
    "docs/ru/getting-started/initialization-order.md",
    "docs/getting-started/installation.md",
    "docs/getting-started/workplace-initialization.md",
    "docs/getting-started/project-onboarding.md",
    "docs/getting-started/agent-prompts.md",
    "docs/concepts/workplace-vs-project.md",
    "docs/release-checklist.md",
    "examples/first-run/minimal-workplace/README.md",
    "examples/first-run/minimal-project/README.md",
    "examples/first-run/example-component-project/README.md",
    "examples/resource-authoring/reusable-template/README.md",
    "examples/resource-authoring/knowledge-package/README.md",
    "examples/knowledge-packages/base-technologies/README.md",
    "examples/resource-authoring/platform-contract/README.md",
    "examples/resource-authoring/full-chain/README.md",
    "examples/api-platforms/example-provider/README.md",
    "examples/task-batch/minimal-run/README.md",
    "examples/task-batch/release-preparation/README.md",
    "examples/task-batch/debug-loop/README.md",
    "examples/guided-workplace-setup/minimal/README.md",
    "examples/guided-workplace-setup/minimal/answers.yaml",
    "examples/guided-workplace-setup/minimal/expected-proposal.md",
    "examples/multi-agent-orchestration/minimal/README.md",
    "examples/multi-agent-orchestration/minimal/orchestrator-task-plan.yaml",
    "examples/multi-agent-orchestration/minimal/expected-worker-docs-prompt.md",
    "examples/multi-agent-orchestration/minimal/expected-worker-test-prompt.md",
    "examples/runtime-supervisor/minimal/README.md",
    "examples/runtime-supervisor/minimal/orchestrator-task-plan.yaml",
    "examples/orchestrator-shell-agents/minimal/README.md",
    "examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml",
    "examples/process-authoring/quality-audit/README.md",
    "examples/process-authoring/process-authoring/README.md",
    "examples/process-authoring/process-supervisor/README.md",
    "examples/process-authoring/quality-audit/answers.yaml",
    "examples/process-authoring/bugfix-batch/README.md",
    "examples/process-authoring/bugfix-batch/answers.yaml",
    "examples/process-authoring/content-update/README.md",
    "examples/process-authoring/content-update/answers.yaml",
    "bin/pf.py",
    "bin/pf",
    "bin/pf.bat",
    "tools/smoke_first_run.py",
    "tools/smoke_runtime_driver_registry.py",
    "tools/smoke_worker_run_shell.py",
    "tools/smoke_process_supervisor_tick.py",
    "tools/smoke_agent_ledger.py",
    "tools/smoke_single_agent_session_flow.py",
    "tools/smoke_multi_project_agent_sessions.py",
    "tools/smoke_multi_agent_as_composed_sessions.py",
    "tools/smoke_project_coordination_modes.py",
    "tools/smoke_mixed_workplace_projects.py",
    "tools/smoke_worker_awareness_of_director.py",
    "tools/smoke_error_workflow.py",
    "tools/smoke_process_transition_handoff.py",
    "tools/smoke_agent_director_tick.py",
    "tools/smoke_orchestrator_shell_agents_with_subagent_policy.py",
    "tools/smoke_process_run_task_batch.py",
    "tools/processforge_subprocess.py",
    "templates/session-start-template.yaml",
    "templates/session-status-report-template.md",
    "templates/project-context.snapshot.yaml",
    "templates/project-context.snapshot.md",
    "templates/global-agents-processforge-section.md",
    "templates/session-metadata-template.yaml",
    "templates/session-telemetry-event-template.json",
    "templates/processforge-event-template.json",
    "templates/hooks-template.yaml",
    "templates/path-constants.yaml",
    "templates/path-ref.yaml",
    "templates/platform-contract.yaml",
    "templates/platform-contract-example-parent.yaml",
    "templates/knowledge-package.yaml",
    "templates/knowledge-resource.yaml",
    "templates/knowledge-resource-index.yaml",
    "templates/knowledge-resource-add-request.md",
    "templates/documentation-import-plan.yaml",
    "templates/documentation-import-report.md",
    "templates/template-readme-template.md",
    "templates/template-package.yaml",
    "templates/tool-definition.yaml",
    "templates/mcp-definition.yaml",
    "templates/resource-management-review.md",
    "templates/processforge-update-index.yaml",
    "templates/processforge-update-assessment-template.md",
    "templates/assignment-front-matter-template.md",
    "templates/run.yaml",
    "templates/assignment-task.yaml",
    "templates/iteration.yaml",
    "templates/context-index-template.yaml",
    "templates/resolved-rules-template.yaml",
    "templates/context-conflict-report-template.md",
    "templates/context-capsule-template.yaml",
    "tools/processforge.py",
    "tools/test_workers/echo_worker.py",
    "tools/test_agents/pf_shell_agent.py",
    "updates/processforge-update-index.yaml",
    "updates/migrations/0.1.0-linked-workplace.md",
    "updates/migrations/1.0.0-stable-release.md",
]

PROCESS_REQUIRED_KEYS = [
    "schema_version",
    "id",
    "name",
    "version",
    "status",
    "description",
    "stages",
    "roles",
    "artifact_definitions",
    "gates",
    "evolution_policy",
]

PACKAGE_REQUIRED_KEYS = ["schema_version", "id", "name", "version", "kind", "scope"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_yaml_key(text: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}\s*:", text) is not None


def load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("PyYAML is required for schema validation of YAML files") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_schema(root: Path, name: str) -> dict[str, Any]:
    path = root / "schemas" / name
    return json.loads(read_text(path))


def schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported external ref {ref}")
    node: Any = schema
    for part in ref[2:].split("/"):
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"ref {ref} does not resolve to schema object")
    return node


def validate_instance(value: Any, node: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "$ref" in node:
        return validate_instance(value, resolve_ref(root_schema, str(node["$ref"])), root_schema, path)

    expected_type = node.get("type")
    if isinstance(expected_type, list):
        if not any(schema_type_matches(value, item) for item in expected_type):
            errors.append(f"{path}: expected one of {expected_type}, got {type(value).__name__}")
            return errors
    elif isinstance(expected_type, str) and not schema_type_matches(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return errors

    if "const" in node and value != node["const"]:
        errors.append(f"{path}: expected const {node['const']!r}")
    if "enum" in node and value not in node["enum"]:
        errors.append(f"{path}: expected one of {node['enum']!r}")
    if "minimum" in node and isinstance(value, (int, float)) and value < node["minimum"]:
        errors.append(f"{path}: expected minimum {node['minimum']}")
    if "minLength" in node and isinstance(value, str) and len(value) < node["minLength"]:
        errors.append(f"{path}: expected minLength {node['minLength']}")
    if "minItems" in node and isinstance(value, list) and len(value) < node["minItems"]:
        errors.append(f"{path}: expected minItems {node['minItems']}")
    if "pattern" in node and isinstance(value, str) and not re.fullmatch(str(node["pattern"]), value):
        errors.append(f"{path}: does not match pattern {node['pattern']!r}")

    if isinstance(value, dict):
        required = node.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path}: missing required key {key}")
        properties = node.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    errors.extend(validate_instance(value[key], child_schema, root_schema, f"{path}.{key}"))
        additional = node.get("additionalProperties", True)
        if additional is False and isinstance(properties, dict):
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected key {key}")
        elif isinstance(additional, dict) and isinstance(properties, dict):
            for key, child in value.items():
                if key not in properties:
                    errors.extend(validate_instance(child, additional, root_schema, f"{path}.{key}"))

    if isinstance(value, list):
        items_schema = node.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_instance(item, items_schema, root_schema, f"{path}[{index}]"))

    return errors


def validate_against_schema(data: Any, schema: dict[str, Any], label: str) -> None:
    errors = validate_instance(data, schema, schema, "$")
    if errors:
        fail(f"{label} failed schema validation: " + "; ".join(errors[:8]))


def validate_required_files(root: Path) -> None:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))


def validate_json_schemas(root: Path) -> None:
    for path in sorted((root / "schemas").glob("*.json")):
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            fail(f"{path.relative_to(root)} is invalid JSON: {exc}")
        for key in ("$schema", "title", "type"):
            if key not in data:
                fail(f"{path.relative_to(root)} missing {key}")


def validate_yaml_like_files(root: Path) -> None:
    manifest = read_text(root / ".pf" / "process-forge.yaml")
    for key in ("schema_version", "process_forge", "project", "paths", "policies"):
        if not has_yaml_key(manifest, key):
            fail(f".pf/process-forge.yaml missing {key}")

    process_count = 0
    non_development = False
    for path in sorted((root / "processes").glob("*.yaml")):
        process_count += 1
        text = read_text(path)
        for key in PROCESS_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(root)} missing {key}")
        if path.name in {"content-production.yaml", "testing.yaml"}:
            non_development = True
    if process_count < 3:
        fail("expected at least three process definitions")
    if not non_development:
        fail("expected at least one non-development process")

    for path in sorted((root / "packages").glob("*.yaml")):
        text = read_text(path)
        for key in PACKAGE_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(root)} missing {key}")


def validate_yaml_schema_files(root: Path) -> None:
    mappings: list[tuple[Path, str]] = [
        (root / ".pf" / "process-forge.yaml", "process-forge-manifest.schema.json"),
    ]
    if (root / "templates" / "process.yaml").is_file():
        mappings.append((root / "templates" / "process.yaml", "process-definition.schema.json"))
    if (root / "templates" / "knowledge-candidate.yaml").is_file():
        mappings.append((root / "templates" / "knowledge-candidate.yaml", "knowledge-candidate.schema.json"))
    mappings.extend((path, "process-definition.schema.json") for path in sorted((root / "processes").glob("*.yaml")))
    mappings.extend((path, "package-manifest.schema.json") for path in sorted((root / "packages").glob("*.yaml")))
    mappings.extend((path, "run.schema.json") for path in sorted((root / ".pf" / "runs").glob("*/run.yaml")))
    mappings.extend((path, "assignment.schema.json") for path in sorted((root / ".pf" / "assignments").glob("*.yaml")))
    if (root / "updates" / "processforge-update-index.yaml").is_file():
        mappings.append((root / "updates" / "processforge-update-index.yaml", "processforge-update-index.schema.json"))
    if (root / "templates" / "registries" / "distributions.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "distributions.yaml", "distributions-registry.schema.json"))
    if (root / "templates" / "registries" / "update-sources.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "update-sources.yaml", "update-source-registry.schema.json"))
    if (root / "templates" / "registries" / "installed-subjects.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "installed-subjects.yaml", "installed-subjects.schema.json"))
    if (root / "templates" / "registries" / "update-site-overrides.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "update-site-overrides.yaml", "update-site-overrides.schema.json"))
    if (root / "templates" / "registries" / "runtime-drivers.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "runtime-drivers.yaml", "runtime-driver-registry.schema.json"))
    if (root / "templates" / "registries" / "agents.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "agents.yaml", "agent-registry.schema.json"))
    for path in sorted((root / "templates" / "runtime-drivers").glob("*.yaml")):
        mappings.append((path, "runtime-driver.schema.json"))
    if (root / "templates" / "supervisor-profile.yaml").is_file():
        mappings.append((root / "templates" / "supervisor-profile.yaml", "supervisor-profile.schema.json"))
    for path, schema_name in [
        (root / "templates" / "agent-lease.yaml", "agent-lease.schema.json"),
        (root / "templates" / "process-routes.yaml", "process-route-map.schema.json"),
        (root / "templates" / "handoff-package.yaml", "process-handoff.schema.json"),
        (root / "templates" / "agent-director-policy.yaml", "agent-director-policy.schema.json"),
        (root / "templates" / "continuation-capsule.yaml", "continuation-capsule.schema.json"),
        (root / "templates" / "orchestrator-shell-agent-plan.yaml", "orchestrator-shell-agent-plan.schema.json"),
        (root / "examples" / "orchestrator-shell-agents" / "minimal" / "orchestrator-shell-agent-plan.yaml", "orchestrator-shell-agent-plan.schema.json"),
    ]:
        if path.is_file():
            mappings.append((path, schema_name))
    for path in [root / "templates" / "platform-contract.yaml", root / "templates" / "platform-contract-example-parent.yaml"]:
        if path.is_file():
            mappings.append((path, "platform-contract.schema.json"))

    for context_root in [root / "contexts", root / ".pf" / "contexts"]:
        if (context_root / "context-index.yaml").is_file():
            mappings.append((context_root / "context-index.yaml", "context-index.schema.json"))
        if (context_root / "resolved-rules.yaml").is_file():
            mappings.append((context_root / "resolved-rules.yaml", "resolved-rules.schema.json"))
        if (context_root / "project-context.snapshot.yaml").is_file():
            mappings.append((context_root / "project-context.snapshot.yaml", "project-context-snapshot.schema.json"))
        mappings.extend((path, "execution-context-package.schema.json") for path in sorted(context_root.rglob("*.ecp.yaml")))
        mappings.extend((path, "context-capsule.schema.json") for path in sorted(context_root.rglob("*.capsule.yaml")))

    for session_root in [root / "runtime" / "sessions", root / ".pf" / "runtime" / "sessions"]:
        if session_root.is_dir():
            mappings.extend((path, "session-metadata.schema.json") for path in sorted(session_root.glob("*.yaml")))

    if (root / "workplace.yaml").is_file():
        mappings.append((root / "workplace.yaml", "workplace.schema.json"))
    if (root / ".pf" / "hooks.yaml").is_file():
        mappings.append((root / ".pf" / "hooks.yaml", "hooks.schema.json"))
    if (root / ".pf" / "process-routes.yaml").is_file():
        mappings.append((root / ".pf" / "process-routes.yaml", "process-route-map.schema.json"))
    for path in sorted((root / ".pf" / "continuations").glob("*.yaml")):
        mappings.append((path, "continuation-capsule.schema.json"))
    for path in sorted((root / ".pf" / "handoffs").glob("*/handoff.yaml")):
        mappings.append((path, "process-handoff.schema.json"))
    for path in sorted((root / ".pf" / "handoffs").glob("*/input-manifest.yaml")):
        mappings.append((path, "handoff-input-manifest.schema.json"))
    for path in sorted((root / ".pf" / "handoffs").glob("*/return-package.yaml")):
        mappings.append((path, "handoff-return-package.schema.json"))

    for path, schema_name in mappings:
        data = load_yaml(path)
        schema = load_schema(root, schema_name)
        validate_against_schema(data, schema, path.relative_to(root).as_posix())


def validate_ndjson_events(root: Path) -> None:
    checks = [
        (".pf/runtime/events/events.ndjson", "event-envelope.schema.json"),
        (".pf/runtime/telemetry", "session-telemetry-event.schema.json"),
        (".pf/runtime/chat/transcripts", "chat-message.schema.json"),
    ]
    for rel_path, schema_name in checks:
        path = root / rel_path
        schema = load_schema(root, schema_name)
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob("*.ndjson"))
        else:
            files = []
        for ndjson in files:
            for line_number, line in enumerate(ndjson.read_text(encoding="utf-8-sig").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    fail(f"{ndjson.relative_to(root)}:{line_number} invalid NDJSON: {exc}")
                validate_against_schema(data, schema, f"{ndjson.relative_to(root).as_posix()}:{line_number}")


def validate_runtime_json_payloads(root: Path) -> None:
    mappings = [
        (root / "templates" / "runtime" / "update", "installed-update-sites.schema.json"),
        (root / ".pf" / "runtime" / "hooks" / "results", "hook-result.schema.json"),
        (root / ".pf" / "runtime" / "hooks" / "outbox" / "wtaicc", "wtaicc-outbox-payload.schema.json"),
    ]
    for folder, schema_name in mappings:
        if not folder.is_dir():
            continue
        schema = load_schema(root, schema_name)
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(read_text(path))
            except json.JSONDecodeError as exc:
                fail(f"{path.relative_to(root)} is invalid JSON: {exc}")
            validate_against_schema(data, schema, path.relative_to(root).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ProcessForge root path.")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    validate_required_files(root)
    validate_json_schemas(root)
    validate_yaml_like_files(root)
    validate_yaml_schema_files(root)
    validate_ndjson_events(root)
    validate_runtime_json_payloads(root)
    print("PASS: ProcessForge structure and JSON Schema validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
    "examples/platform-inheritance/example-parent/README.md",
    "examples/platform-inheritance/example-child/README.md",
