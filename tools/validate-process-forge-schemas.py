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
    ".pf/AGENTS.md",
    ".pf/process-forge.yaml",
    ".pf/hooks.yaml",
    "docs/concepts/file-first-processes.md",
    "docs/concepts/workplace-layer.md",
    "docs/concepts/project-flow-layer.md",
    "docs/concepts/cascade-merge.md",
    "docs/concepts/execution-context-package.md",
    "docs/concepts/reusable-templates.md",
    "docs/concepts/process-evolution.md",
    "docs/concepts/workplace-init.md",
    "docs/concepts/project-init.md",
    "docs/concepts/linked-workplace-model.md",
    "docs/concepts/path-constants.md",
    "docs/concepts/runtime-model.md",
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
    "docs/concepts/resource-privacy.md",
    "docs/concepts/resource-events.md",
    "docs/concepts/processforge-self-update.md",
    "docs/concepts/workplace-terms.md",
    "docs/concepts/wtaicc-future-compatibility.md",
    "docs/concepts/public-private-config.md",
    "docs/concepts/capability-resolution.md",
    "docs/concepts/session-bootstrap.md",
    "docs/concepts/project-context-snapshot.md",
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
    "docs/authoring/workplace-configuration.md",
    "docs/authoring/project-initialization.md",
    "docs/authoring/knowledge-package-authoring.md",
    "docs/authoring/reusable-template-authoring.md",
    "docs/authoring/template-authoring.md",
    "docs/authoring/platform-contract-authoring.md",
    "docs/getting-started/resource-authoring.md",
    "docs/authoring/task-batch-execution.md",
    "docs/authoring/process-authoring.md",
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
    "docs/ru/authoring/reusable-template-authoring.md",
    "docs/ru/authoring/knowledge-package-authoring.md",
    "docs/ru/authoring/platform-contract-authoring.md",
    "docs/ru/authoring/process-authoring.md",
    "docs/ru/authoring/authoring-parity.md",
    "docs/ru/authoring/backfill-existing-processes.md",
    "docs/ru/concepts/workplace-vs-project.md",
    "docs/ru/concepts/runtime-model.md",
    "docs/ru/concepts/path-constants.md",
    "docs/ru/concepts/package-roots.md",
    "docs/ru/concepts/project-snapshot.md",
    "docs/ru/concepts/runs-tasks-iterations.md",
    "docs/ru/concepts/process-definition-run-task-iteration.md",
    "docs/ru/concepts/platform-contracts.md",
    "docs/ru/concepts/hooks-events.md",
    "docs/ru/concepts/semantic-parity.md",
    "docs/ru/releases/v0.1.0.md",
    "docs/ru/known-limitations.md",
    "docs/assets/processforge-architecture.svg",
    "docs/assets/processforge-run-lifecycle.svg",
    "docs/assets/processforge-authoring-parity.svg",
    "docs/processes/process-authoring.md",
    "docs/getting-started/task-batch-workflow.md",
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
    "schemas/workplace-init-answers.schema.json",
    "schemas/project-init-answers.schema.json",
    "schemas/session-start.schema.json",
    "schemas/project-context-snapshot.schema.json",
    "schemas/session-metadata.schema.json",
    "schemas/session-telemetry-event.schema.json",
    "schemas/event-envelope.schema.json",
    "schemas/process-event.schema.json",
    "schemas/processforge-event.schema.json",
    "schemas/hooks.schema.json",
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
    "templates/workplace.yaml",
    "templates/terms.yaml",
    "templates/registries/distributions.yaml",
    "templates/registries/platforms.yaml",
    "templates/registries/knowledge-roots.yaml",
    "templates/registries/package-roots.yaml",
    "templates/registries/templates.yaml",
    "templates/registries/tools.yaml",
    "templates/registries/mcp.yaml",
    "templates/workplace-init.answers.yaml",
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
    "templates/process-definition-template.yaml",
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
    "docs/getting-started/first-run.md",
    "docs/getting-started/installation.md",
    "docs/getting-started/workplace-initialization.md",
    "docs/getting-started/project-onboarding.md",
    "docs/getting-started/agent-prompts.md",
    "docs/concepts/workplace-vs-project.md",
    "docs/release-checklist.md",
    "examples/first-run/minimal-workplace/README.md",
    "examples/first-run/minimal-project/README.md",
    "examples/first-run/joomla-component-project/README.md",
    "examples/resource-authoring/reusable-template/README.md",
    "examples/resource-authoring/knowledge-package/README.md",
    "examples/resource-authoring/platform-contract/README.md",
    "examples/resource-authoring/full-chain/README.md",
    "examples/task-batch/minimal-run/README.md",
    "examples/task-batch/release-preparation/README.md",
    "examples/task-batch/debug-loop/README.md",
    "examples/process-authoring/seo-audit/README.md",
    "examples/process-authoring/process-authoring/README.md",
    "examples/process-authoring/seo-audit/answers.yaml",
    "examples/process-authoring/bugfix-batch/README.md",
    "examples/process-authoring/bugfix-batch/answers.yaml",
    "examples/process-authoring/content-update/README.md",
    "examples/process-authoring/content-update/answers.yaml",
    "bin/pf.py",
    "bin/pf",
    "bin/pf.bat",
    "tools/smoke_first_run.py",
    "tools/smoke_resource_authoring_processes.py",
    "tools/smoke_process_run_task_batch.py",
    "tools/smoke_process_authoring.py",
    "tools/smoke_authoring_parity.py",
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
    "templates/platform-contract-joomla.yaml",
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
    "updates/processforge-update-index.yaml",
    "updates/migrations/0.1.0-linked-workplace.md",
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
    mappings.extend((path, "process-definition.schema.json") for path in sorted((root / "processes").glob("*.yaml")))
    mappings.extend((path, "package-manifest.schema.json") for path in sorted((root / "packages").glob("*.yaml")))
    if (root / "updates" / "processforge-update-index.yaml").is_file():
        mappings.append((root / "updates" / "processforge-update-index.yaml", "processforge-update-index.schema.json"))
    if (root / "templates" / "registries" / "distributions.yaml").is_file():
        mappings.append((root / "templates" / "registries" / "distributions.yaml", "distributions-registry.schema.json"))
    for path in [root / "templates" / "platform-contract.yaml", root / "templates" / "platform-contract-joomla.yaml"]:
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
