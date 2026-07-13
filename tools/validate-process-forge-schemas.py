#!/usr/bin/env python3
"""Validate ProcessForge bootstrap structure with standard-library checks."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "process-forge.yaml",
    "docs/concepts/file-first-processes.md",
    "docs/concepts/workplace-layer.md",
    "docs/concepts/project-flow-layer.md",
    "docs/concepts/cascade-merge.md",
    "docs/concepts/execution-context-package.md",
    "docs/concepts/reusable-templates.md",
    "docs/concepts/process-evolution.md",
    "docs/concepts/workplace-init.md",
    "docs/concepts/project-init.md",
    "docs/concepts/public-private-config.md",
    "docs/concepts/capability-resolution.md",
    "docs/authoring/workplace-configuration.md",
    "docs/authoring/project-initialization.md",
    "docs/validation/doctor-workplace.md",
    "docs/validation/doctor-project.md",
    "schemas/process-forge-manifest.schema.json",
    "schemas/workplace.schema.json",
    "schemas/terms.schema.json",
    "schemas/platform-registry.schema.json",
    "schemas/knowledge-roots-registry.schema.json",
    "schemas/package-roots-registry.schema.json",
    "schemas/template-registry.schema.json",
    "schemas/tool-registry.schema.json",
    "schemas/mcp-registry.schema.json",
    "schemas/workplace-init-answers.schema.json",
    "schemas/project-init-answers.schema.json",
    "schemas/process-definition.schema.json",
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
    "processes/project-initialization.yaml",
    "templates/workplace.yaml",
    "templates/terms.yaml",
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
    "tools/processforge.py",
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


def validate_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))


def validate_json_schemas() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            fail(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
        for key in ("$schema", "title", "type"):
            if key not in data:
                fail(f"{path.relative_to(ROOT)} missing {key}")


def validate_yaml_like_files() -> None:
    manifest = read_text(ROOT / "process-forge.yaml")
    for key in ("schema_version", "process_forge", "project", "paths", "policies"):
        if not has_yaml_key(manifest, key):
            fail(f"process-forge.yaml missing {key}")

    process_count = 0
    non_development = False
    for path in sorted((ROOT / "processes").glob("*.yaml")):
        process_count += 1
        text = read_text(path)
        for key in PROCESS_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(ROOT)} missing {key}")
        if path.name in {"content-production.yaml", "testing.yaml"}:
            non_development = True
    if process_count < 3:
        fail("expected at least three process definitions")
    if not non_development:
        fail("expected at least one non-development process")

    for path in sorted((ROOT / "packages").glob("*.yaml")):
        text = read_text(path)
        for key in PACKAGE_REQUIRED_KEYS:
            if not has_yaml_key(text, key):
                fail(f"{path.relative_to(ROOT)} missing {key}")


def main() -> int:
    validate_required_files()
    validate_json_schemas()
    validate_yaml_like_files()
    print("PASS: ProcessForge structure and schema syntax checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
