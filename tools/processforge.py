#!/usr/bin/env python3
"""ProcessForge MVP CLI for workplace/project init and doctor checks."""

from __future__ import annotations

import argparse
import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PROJECT_PRIVATE_GITIGNORE = [
    "process-forge.local.yaml",
    "runtime/",
    "cache/",
    "private-notes/",
    ".secrets/",
    "*.tmp",
    "*.bak",
]

BUILTIN_CAPABILITIES = {
    "repository.read",
    "markdown.editing",
    "filesystem.read",
    "filesystem.write",
}

BACKSLASH = chr(92)
LOCAL_PATH_PATTERNS = [
    re.compile("[A-Za-z]:" + re.escape(BACKSLASH)),
    re.compile("/" + "home" + "/[A-Za-z0-9_.-]+/"),
    re.compile("/" + "Users" + "/[A-Za-z0-9_.-]+/"),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


@dataclass
class Check:
    level: str
    message: str


@dataclass
class WriteResult:
    path: Path
    status: str
    target: Path


def safe_id(value: str, default: str = "project") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or default


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_public_path_safe(text: str) -> bool:
    return not any(pattern.search(text) for pattern in LOCAL_PATH_PATTERNS)


def contains_secret_value(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS)


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small mapping-only YAML subset used by init answers."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if stripped.startswith("- "):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return root


def load_answers(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.is_file():
        raise SystemExit(f"FAIL: answers file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if contains_secret_value(text):
        raise SystemExit("FAIL: answers file appears to contain a secret value")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(text)


def format_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if any(char in text for char in [":", "#", "{", "}", "[", "]"]) or text.strip() != text:
        return '"' + text.replace('"', '\\"') + '"'
    return text


def dump_yaml(data: Any, indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(dump_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {format_scalar(value)}")
    elif isinstance(data, list):
        if not data:
            lines.append(f"{prefix}[]")
        for item in data:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(dump_yaml(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.append(dump_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {format_scalar(item)}")
    else:
        lines.append(f"{prefix}{format_scalar(data)}")
    return "\n".join(lines)


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def write_file(path: Path, content: str, *, force: bool = False) -> WriteResult:
    content = ensure_trailing_newline(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        if existing == content:
            return WriteResult(path, "unchanged", path)
        if not force:
            candidate = path.with_name(path.name + ".candidate")
            candidate.write_text(content, encoding="utf-8")
            return WriteResult(path, "candidate", candidate)
    path.write_text(content, encoding="utf-8")
    return WriteResult(path, "written", path)


def append_gitignore_entries(path: Path, entries: list[str], *, force: bool = False) -> WriteResult:
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    lines = existing.splitlines()
    changed = False
    for entry in entries:
        if entry not in lines:
            lines.append(entry)
            changed = True
    if not changed:
        return WriteResult(path, "unchanged", path)
    content = "\n".join(lines).rstrip() + "\n"
    if path.exists() and existing and not force:
        candidate = path.with_name(path.name + ".candidate")
        candidate.write_text(content, encoding="utf-8")
        return WriteResult(path, "candidate", candidate)
    path.write_text(content, encoding="utf-8")
    return WriteResult(path, "written", path)


def print_plan(title: str, planned: list[Path], root: Path) -> None:
    print(f"PLAN: {title}")
    for path in planned:
        print(f"  - {rel(path, root)}")


def workplace_defaults(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    workplace_answers = answers.get("workplace", {}) if isinstance(answers.get("workplace"), dict) else {}
    paths_answers = answers.get("paths", {}) if isinstance(answers.get("paths"), dict) else {}
    os_name = str(workplace_answers.get("os") or platform.system().lower() or "unknown").lower()
    return {
        "id": safe_id(str(workplace_answers.get("id") or root.name or "workplace"), "workplace"),
        "name": str(workplace_answers.get("name") or root.name or "ProcessForge Workplace"),
        "type": str(workplace_answers.get("type") or "workstation"),
        "os": os_name,
        "root": str(paths_answers.get("root") or root),
    }


def build_terms() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "terms": {
            "knowledge_roots": {
                "label": "knowledge roots",
                "aliases": ["local knowledge", "knowledge folders", "documentation roots"],
                "definition": "Directories with documentation, standards, references, and rules.",
            },
            "template_roots": {
                "label": "template roots",
                "aliases": ["global templates", "shared templates"],
                "definition": "Reusable template directories available to projects.",
            },
            "tool_registry": {
                "label": "tool registry",
                "aliases": ["tools", "global tools"],
                "definition": "Configured tool capability providers.",
            },
            "mcp_registry": {
                "label": "MCP registry",
                "aliases": ["MCP", "MCP servers"],
                "definition": "Configured MCP capability providers.",
            },
            "package_roots": {
                "label": "package roots",
                "aliases": ["knowledge packages", "process packages"],
                "definition": "Directories containing versioned ProcessForge packages.",
            },
        },
    }


def dict_entries_from_answers(container: Any, item_label: str, scope: str) -> list[dict[str, Any]]:
    if not isinstance(container, dict):
        return []
    entries = []
    for key, value in container.items():
        if value in (None, "", "<path>"):
            continue
        entries.append(
            {
                "id": safe_id(str(key), item_label),
                "label": str(key).replace("_", " ").title(),
                "path": str(value),
                "scope": scope,
                "status": "available",
            }
        )
    return entries


def build_workplace_files(root: Path, answers: dict[str, Any]) -> dict[Path, str]:
    defaults = workplace_defaults(root, answers)
    paths_answers = answers.get("paths", {}) if isinstance(answers.get("paths"), dict) else {}
    policies_answers = answers.get("policies", {}) if isinstance(answers.get("policies"), dict) else {}

    workplace = {
        "schema_version": 1,
        "workplace": {
            "id": defaults["id"],
            "name": defaults["name"],
            "type": defaults["type"],
            "os": defaults["os"],
            "owner": None,
        },
        "process_forge": {
            "version_constraint": "^0.1",
            "supported_modes": ["file_only", "local_supervisor_ready"],
        },
        "paths": {
            "root": defaults["root"],
            "terms": "terms.yaml",
            "registries": "registries",
            "cache": "cache",
            "runtime": "runtime",
            "logs": "logs",
        },
        "registries": {
            "platforms": "registries/platforms.yaml",
            "knowledge_roots": "registries/knowledge-roots.yaml",
            "package_roots": "registries/package-roots.yaml",
            "templates": "registries/templates.yaml",
            "tools": "registries/tools.yaml",
            "mcp": "registries/mcp.yaml",
        },
        "policies": {
            "prefer_project_overrides": True,
            "require_explicit_override_for_locked_policies": True,
            "shell_is_fallback": bool(policies_answers.get("shell_is_fallback", True)),
            "do_not_store_secret_values": True,
            "require_public_cleanliness_check": True,
        },
        "capability_resolution": {
            "missing_required_capability": "block",
            "missing_optional_capability": "warn",
            "prefer_project_tool_over_global": True,
            "allow_fallback_tools": True,
        },
    }

    knowledge_entries = dict_entries_from_answers(
        paths_answers.get("knowledge_roots"), "knowledge-root", "workplace"
    )
    for entry in knowledge_entries:
        entry["visibility"] = "private"
        entry["indexing_policy"] = "allowed"

    package_entries = dict_entries_from_answers(paths_answers.get("package_roots"), "package-root", "workplace")
    template_entries = dict_entries_from_answers(paths_answers.get("template_roots"), "template-root", "workplace")

    agents = f"""# ProcessForge Workplace Layer

This directory is a ProcessForge workplace layer.

## Start Here

1. Read `workplace.yaml`.
2. Resolve registries from `registries/`.
3. Use capability providers from `registries/tools.yaml` and `registries/mcp.yaml`.
4. Use package roots and template roots only through registry entries.

## Rules

- Do not store credentials or secret values.
- Keep local absolute paths in workplace-local files only.
- Project public files must not contain local absolute paths.
- Project settings may override workplace defaults only through merge policy.
"""

    report = f"""# Workplace Init Report

## Status

applied

## Workplace

- id: {defaults["id"]}
- name: {defaults["name"]}
- root: {root}

## Files

- AGENTS.md
- workplace.yaml
- terms.yaml
- registries/platforms.yaml
- registries/knowledge-roots.yaml
- registries/package-roots.yaml
- registries/templates.yaml
- registries/tools.yaml
- registries/mcp.yaml

## Notes

- Secret values were not stored.
- Project public manifests must keep local paths out.
"""

    files = {
        root / "AGENTS.md": agents,
        root / "workplace.yaml": dump_yaml(workplace),
        root / "terms.yaml": dump_yaml(build_terms()),
        root / "registries" / "platforms.yaml": dump_yaml({"schema_version": 1, "platforms": []}),
        root / "registries" / "knowledge-roots.yaml": dump_yaml(
            {"schema_version": 1, "knowledge_roots": knowledge_entries}
        ),
        root / "registries" / "package-roots.yaml": dump_yaml(
            {"schema_version": 1, "package_roots": package_entries}
        ),
        root / "registries" / "templates.yaml": dump_yaml(
            {
                "schema_version": 1,
                "template_roots": template_entries,
                "template_policy": {
                    "project_templates_override_global": True,
                    "require_template_usage_log": True,
                    "forbid_blind_copy": True,
                },
            }
        ),
        root / "registries" / "tools.yaml": dump_yaml({"schema_version": 1, "tools": []}),
        root / "registries" / "mcp.yaml": dump_yaml({"schema_version": 1, "mcp_servers": []}),
        root / "logs" / "workplace-init-report.md": report,
    }
    return files


def command_init_workplace(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    answers = load_answers(Path(args.answers).expanduser().resolve() if args.answers else None)
    files = build_workplace_files(root, answers)
    planned_dirs = [root / "cache", root / "runtime", root / "logs"]
    if not args.apply:
        print_plan("workplace init dry run", list(files) + planned_dirs, root)
        return 0
    for directory in planned_dirs:
        directory.mkdir(parents=True, exist_ok=True)
    results = [write_file(path, content, force=args.force) for path, content in files.items()]
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, root)}")
    return 0


def check(level: str, message: str) -> Check:
    return Check(level.upper(), message)


def print_checks(checks: list[Check]) -> int:
    failed = False
    for item in checks:
        print(f"{item.level}: {item.message}")
        failed = failed or item.level == "FAIL"
    return 1 if failed else 0


def command_doctor_workplace(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    checks: list[Check] = []
    manifest = root / "workplace.yaml"
    if manifest.is_file():
        checks.append(check("PASS", "workplace.yaml found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        if contains_secret_value(text):
            checks.append(check("FAIL", "workplace.yaml appears to contain a secret value"))
        else:
            checks.append(check("PASS", "workplace.yaml contains no obvious secret values"))
    else:
        checks.append(check("FAIL", "workplace.yaml missing"))

    for rel_path in [
        "registries/platforms.yaml",
        "registries/knowledge-roots.yaml",
        "registries/package-roots.yaml",
        "registries/templates.yaml",
        "registries/tools.yaml",
        "registries/mcp.yaml",
    ]:
        path = root / rel_path
        checks.append(check("PASS" if path.is_file() else "FAIL", f"{rel_path} {'found' if path.is_file() else 'missing'}"))
        if path.is_file() and contains_secret_value(path.read_text(encoding="utf-8", errors="replace")):
            checks.append(check("FAIL", f"{rel_path} appears to contain a secret value"))

    for rel_dir in ["cache", "runtime", "logs"]:
        path = root / rel_dir
        checks.append(check("PASS" if path.is_dir() else "WARN", f"{rel_dir}/ {'found' if path.is_dir() else 'missing'}"))

    mcp_registry = root / "registries" / "mcp.yaml"
    if mcp_registry.is_file():
        mcp_text = mcp_registry.read_text(encoding="utf-8", errors="replace")
        has_mcp_entry = re.search(r"(?m)^\s*-\s*$", mcp_text) or re.search(r"(?m)^\s*-\s+id:", mcp_text)
        if "mcp_servers:" in mcp_text and not has_mcp_entry:
            checks.append(check("WARN", "optional MCP providers are not configured"))
    return print_checks(checks)


def list_project_files(project_root: Path) -> list[Path]:
    if not project_root.exists():
        return []
    ignored_dirs = {".git", ".idea", ".serena", "__pycache__", "runtime", "cache"}
    files: list[Path] = []
    for path in project_root.rglob("*"):
        if any(part in ignored_dirs for part in path.relative_to(project_root).parts):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(project_root).as_posix())


def detect_project(project_root: Path) -> dict[str, Any]:
    files = list_project_files(project_root)
    rel_files = {rel(path, project_root) for path in files}
    top_dirs = sorted({item.parts[0] for path in files for item in [path.relative_to(project_root)] if item.parts})
    languages: set[str] = set()
    platforms: set[str] = set()
    frameworks: set[str] = set()
    project_kind: set[str] = set()
    evidence: list[str] = []

    if "composer.json" in rel_files or any(path.suffix == ".php" for path in files):
        languages.add("php")
        project_kind.add("php_project")
        evidence.append("composer.json or PHP files")
    if "package.json" in rel_files:
        languages.add("javascript")
        project_kind.add("node_project")
        evidence.append("package.json")
    if "pyproject.toml" in rel_files or any(path.suffix == ".py" for path in files):
        languages.add("python")
        project_kind.add("python_project")
        evidence.append("pyproject.toml or Python files")
    if "phpunit.xml" in rel_files or "phpunit.xml.dist" in rel_files:
        frameworks.add("phpunit")
        evidence.append("phpunit.xml")
    if ".github/workflows" in top_dirs or any(path.startswith(".github/workflows/") for path in rel_files):
        frameworks.add("github-actions")
        evidence.append(".github/workflows")
    if "docs" in top_dirs:
        project_kind.add("documentation_project")
        evidence.append("docs directory")
    if "content" in top_dirs:
        project_kind.add("content_project")
        evidence.append("content directory")
    if "media" in top_dirs:
        project_kind.add("media_project")
        evidence.append("media directory")
    if "administrator" in top_dirs or "plugins" in top_dirs:
        platforms.add("joomla")
        project_kind.add("joomla_extension")
        evidence.append("Joomla-style directories")
    for path in files[:200]:
        if path.suffix.lower() == ".xml":
            text = path.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
            if "<extension" in text:
                platforms.add("joomla")
                project_kind.add("joomla_extension")
                evidence.append(f"Joomla extension manifest candidate: {rel(path, project_root)}")
                break

    if not project_kind:
        project_kind.add("general_project")
    confidence = "medium" if evidence else "low"
    return {
        "languages": sorted(languages),
        "platforms": sorted(platforms),
        "frameworks": sorted(frameworks),
        "project_kind": sorted(project_kind),
        "confidence": confidence,
        "evidence": evidence or ["No strong project markers found."],
        "files": [rel(path, project_root) for path in files[:300]],
        "top_dirs": top_dirs,
    }


def project_mode(project_root: Path, answers: dict[str, Any]) -> str:
    project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
    requested = str(project_answers.get("mode") or "auto")
    if requested in {"greenfield", "brownfield"}:
        return requested
    if not project_root.exists():
        return "greenfield"
    visible = [path for path in project_root.iterdir() if path.name not in {".git", ".idea", ".serena"}]
    return "greenfield" if not visible else "brownfield"


def project_defaults(project_root: Path, answers: dict[str, Any], detected: dict[str, Any]) -> dict[str, Any]:
    project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
    project_id = safe_id(str(project_answers.get("id") or project_root.name), "project")
    project_name = str(project_answers.get("name") or project_root.name or "ProcessForge Project")
    detected_kind = detected["project_kind"][0] if detected["project_kind"] else "general_project"
    project_type = str(project_answers.get("type") or detected_kind)
    if project_type == "auto":
        project_type = detected_kind
    return {"id": project_id, "name": project_name, "type": project_type}


def markdown_list(items: list[str], empty: str = "None.") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def registry_text(workplace_manifest: Path, registry_name: str) -> str:
    root = workplace_manifest.parent
    path = root / "registries" / registry_name
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def match_global_resources(workplace_manifest: Path, detected: dict[str, Any], required: list[str], optional: list[str]) -> dict[str, list[str]]:
    platforms_text = registry_text(workplace_manifest, "platforms.yaml")
    tools_text = registry_text(workplace_manifest, "tools.yaml")
    mcp_text = registry_text(workplace_manifest, "mcp.yaml")
    templates_text = registry_text(workplace_manifest, "templates.yaml")
    package_text = registry_text(workplace_manifest, "package-roots.yaml")

    matched_platforms = [item for item in detected["platforms"] if item and item in platforms_text]
    matched_tools = [cap for cap in required + optional if cap and cap in tools_text]
    matched_mcp = [cap for cap in required + optional if cap and cap in mcp_text]
    missing_required = [
        cap for cap in required if cap not in BUILTIN_CAPABILITIES and cap not in tools_text and cap not in mcp_text
    ]
    optional_missing = [cap for cap in optional if cap not in tools_text and cap not in mcp_text]
    matched_templates = ["template roots configured"] if "template_roots:" in templates_text and "[]" not in templates_text else []
    matched_packages = ["package roots configured"] if "package_roots:" in package_text and "[]" not in package_text else []
    return {
        "matched_platforms": matched_platforms,
        "matched_packages": matched_packages,
        "matched_tools": matched_tools,
        "matched_mcp": matched_mcp,
        "matched_templates": matched_templates,
        "missing_required": missing_required,
        "optional_missing": optional_missing,
        "conflicts": [],
    }


def build_project_files(project_root: Path, workplace_manifest: Path, answers: dict[str, Any]) -> dict[Path, str]:
    detected = detect_project(project_root)
    defaults = project_defaults(project_root, answers, detected)
    mode = project_mode(project_root, answers)
    required = answers.get("required_capabilities") if isinstance(answers.get("required_capabilities"), list) else []
    optional = answers.get("optional_capabilities") if isinstance(answers.get("optional_capabilities"), list) else []
    required = required or ["repository.read", "markdown.editing"]
    optional = optional or ["repository.symbol_analysis", "official_documentation"]
    matches = match_global_resources(workplace_manifest, detected, required, optional)

    public_manifest = {
        "schema_version": 1,
        "process_forge": {"version": "0.1.0", "mode": "file_only", "runner_required": False, "backend_required": False},
        "project": {"id": defaults["id"], "name": defaults["name"], "type": defaults["type"]},
        "workplace": {"reference": "local_file", "local_config": "process-forge.local.yaml"},
        "detected": {
            "languages": detected["languages"],
            "platforms": detected["platforms"],
            "project_kind": detected["project_kind"],
        },
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
            "runtime": "runtime",
        },
        "knowledge_stack": [
            {"package": "process-forge-core", "version": "^0.1", "source": "project"},
            {"package": f"project.{defaults['id']}", "version": "0.1.0", "source": "project"},
        ],
        "required_capabilities": required,
        "optional_capabilities": optional,
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
        "local": {"project_root": str(project_root.resolve())},
        "overrides": {"package_roots": [], "template_roots": [], "tool_preferences": {}},
        "runtime": {"mode": "manual", "queue": "runtime/queue", "events": "runtime/events"},
    }

    agents = """# Project Agent Instructions

This project uses ProcessForge.

## Start Here

1. Read `process-forge.yaml`.
2. Load local configuration from `process-forge.local.yaml` if available.
3. Resolve the workplace layer.
4. Use assignments from `assignments/`.
5. Write logs to `logs/`.
6. Save artifacts to `artifacts/`.
7. Write handoffs to `handoffs/`.
8. Request reviews in `reviews/`.

## Important Rules

- Do not edit files outside assignment scope.
- Do not put absolute local paths into public files.
- Do not commit private local config.
- Use project-local templates before global templates when allowed.
- Record template usage.
"""

    classification_report = f"""# Project Classification Report

## Status

observed

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

## Unknowns

- Confirm exact project ownership and release workflow manually.
"""

    repository_map = f"""# Repository Map

## Status

observed

## Main Directories

{markdown_list(detected["top_dirs"])}

## Code

{markdown_list([item for item in detected["files"] if item.startswith(("src/", "app/", "administrator/", "plugins/"))])}

## Docs

{markdown_list([item for item in detected["files"] if item.startswith("docs/") or item == "README.md"])}

## Tests

{markdown_list([item for item in detected["files"] if "test" in item.lower()])}

## Assets

{markdown_list([item for item in detected["files"] if item.startswith(("media/", "assets/", "public/"))])}

## Build Or Package Config

{markdown_list([item for item in detected["files"] if item in {"composer.json", "package.json", "pyproject.toml", "phing.xml"} or item.startswith(".github/workflows/")])}

## Critical Files

- process-forge.yaml
- process-forge.local.yaml

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

{markdown_list([item for item in detected["files"] if item in {"composer.json", "package.json", "pyproject.toml", "phpunit.xml", "phing.xml"}])}

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

    resource_report = f"""# Global Resource Matching Report

## Matched Platforms

{markdown_list(matches["matched_platforms"])}

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

- process-forge.yaml
- docs/
- artifacts/

## Private Zones

- process-forge.local.yaml
- cache/
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
- process-forge.yaml
- packages/project.{defaults["id"]}.yaml
- artifacts/project-profile.md
- artifacts/project-classification-report.md
- artifacts/repository-map.md
- artifacts/project-conventions.md
- artifacts/toolchain-detection-report.md
- artifacts/mcp-capability-report.md
- artifacts/template-matching-report.md
- artifacts/global-resource-matching-report.md
- reviews/project-init-review.md

## Planned Private Files

- process-forge.local.yaml

## Risks

- Existing files are not overwritten without explicit approval.
- Detection results are observed, not confirmed.

## Recommendation

Run doctor after apply mode.
"""

    package = {
        "schema_version": 1,
        "id": f"project.{defaults['id']}",
        "name": f"{defaults['name']} Knowledge",
        "version": "0.1.0",
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
- process-forge.yaml
- process-forge.local.yaml

## Recommendation

Review and confirm observed conventions.
"""

    return {
        project_root / "AGENTS.md": agents,
        project_root / "process-forge.yaml": dump_yaml(public_manifest),
        project_root / "process-forge.local.yaml": dump_yaml(local_manifest),
        project_root / "packages" / f"project.{defaults['id']}.yaml": dump_yaml(package),
        project_root / "artifacts" / "project-profile.md": profile,
        project_root / "artifacts" / "project-classification-report.md": classification_report,
        project_root / "artifacts" / "repository-map.md": repository_map,
        project_root / "artifacts" / "project-conventions.md": conventions,
        project_root / "artifacts" / "toolchain-detection-report.md": toolchain,
        project_root / "artifacts" / "mcp-capability-report.md": mcp_report,
        project_root / "artifacts" / "template-matching-report.md": template_report,
        project_root / "artifacts" / "global-resource-matching-report.md": resource_report,
        project_root / "artifacts" / "project-init-proposal.md": proposal,
        project_root / "reviews" / "project-init-review.md": review,
    }


def command_init_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    workplace = Path(args.workplace).expanduser().resolve()
    answers = load_answers(Path(args.answers).expanduser().resolve() if args.answers else None)
    if not project_root.exists() and args.apply:
        project_root.mkdir(parents=True)
    if not project_root.exists() and args.apply:
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    files = build_project_files(project_root, workplace, answers)
    dirs = [
        "processes",
        "packages",
        "templates",
        "assignments",
        "artifacts",
        "contexts",
        "logs",
        "handoffs",
        "reviews",
        "adr",
        "schemas",
        "runtime",
    ]
    planned_paths = list(files) + [project_root / item for item in dirs] + [project_root / ".gitignore"]
    if not args.apply:
        print_plan("project init dry run", planned_paths, project_root)
        mode = project_mode(project_root, answers)
        print(f"MODE: {mode}")
        return 0

    for dirname in dirs:
        (project_root / dirname).mkdir(parents=True, exist_ok=True)
    results = [write_file(path, content, force=args.force) for path, content in files.items()]
    results.append(append_gitignore_entries(project_root / ".gitignore", PROJECT_PRIVATE_GITIGNORE, force=args.force))
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, project_root)}")
    return 0


def find_local_workplace_manifest(local_text: str) -> Path | None:
    manifest_pattern = r"(?m)^\s*" + "manifest:" + r"\s*(.+?)\s*$"
    match = re.search(manifest_pattern, local_text)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return Path(value)


def report_has_missing_required_capabilities(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "## Missing Required Capabilities"
    if marker not in text:
        return False
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    listed = [line.strip() for line in section.splitlines() if line.strip().startswith("- ")]
    return any(line != "- None." for line in listed)


def command_doctor_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    checks: list[Check] = []
    manifest = project_root / "process-forge.yaml"
    local_manifest = project_root / "process-forge.local.yaml"
    gitignore = project_root / ".gitignore"

    if manifest.is_file():
        checks.append(check("PASS", "process-forge.yaml found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "public manifest contains no secret values"))
    else:
        checks.append(check("FAIL", "process-forge.yaml missing"))

    if local_manifest.is_file():
        checks.append(check("PASS", "process-forge.local.yaml found"))
        local_text = local_manifest.read_text(encoding="utf-8", errors="replace")
        workplace = find_local_workplace_manifest(local_text)
        if workplace and workplace.is_file():
            checks.append(check("PASS", "workplace manifest is reachable"))
        else:
            checks.append(check("FAIL", "workplace manifest is missing or unreachable"))
    else:
        checks.append(check("FAIL", "process-forge.local.yaml missing"))

    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for entry in ["process-forge.local.yaml", "cache/", ".secrets/"]:
            checks.append(check("PASS" if entry in ignore_text else "FAIL", f".gitignore contains {entry}"))
    else:
        checks.append(check("FAIL", ".gitignore missing"))

    package_exists = any((project_root / "packages").glob("project.*.yaml")) if (project_root / "packages").is_dir() else False
    checks.append(check("PASS" if package_exists else "FAIL", "project package draft exists"))
    resource_report = project_root / "artifacts" / "global-resource-matching-report.md"
    if report_has_missing_required_capabilities(resource_report):
        checks.append(check("FAIL", "required capabilities are missing"))
    elif resource_report.is_file():
        checks.append(check("PASS", "required capabilities are resolved or built in"))

    for rel_path in [
        "artifacts/project-profile.md",
        "artifacts/project-classification-report.md",
        "artifacts/repository-map.md",
        "artifacts/project-conventions.md",
        "artifacts/global-resource-matching-report.md",
        "artifacts/project-init-proposal.md",
        "reviews/project-init-review.md",
    ]:
        path = project_root / rel_path
        checks.append(check("PASS" if path.is_file() else "FAIL", f"{rel_path} {'found' if path.is_file() else 'missing'}"))
    return print_checks(checks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProcessForge MVP init and doctor commands.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_workplace = sub.add_parser("init-workplace", help="Initialize a ProcessForge workplace layer.")
    init_workplace.add_argument("--root", required=True, help="Workplace root path.")
    init_workplace.add_argument("--answers", help="Optional workplace answers YAML.")
    init_workplace.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    init_workplace.add_argument("--apply", action="store_true", help="Write files.")
    init_workplace.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_workplace.set_defaults(func=command_init_workplace)

    doctor_workplace = sub.add_parser("doctor-workplace", help="Validate a ProcessForge workplace layer.")
    doctor_workplace.add_argument("--root", required=True, help="Workplace root path.")
    doctor_workplace.set_defaults(func=command_doctor_workplace)

    init_project = sub.add_parser("init-project", help="Initialize a ProcessForge project layer.")
    init_project.add_argument("--project-root", required=True, help="Project root path.")
    init_project.add_argument("--workplace", required=True, help="Path to workplace.yaml.")
    init_project.add_argument("--answers", help="Optional project answers YAML.")
    init_project.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    init_project.add_argument("--apply", action="store_true", help="Write files.")
    init_project.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_project.set_defaults(func=command_init_project)

    doctor_project = sub.add_parser("doctor-project", help="Validate a ProcessForge project layer.")
    doctor_project.add_argument("--project-root", required=True, help="Project root path.")
    doctor_project.set_defaults(func=command_doctor_project)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "apply") and not args.apply:
        args.dry_run = True
    if hasattr(args, "apply") and args.apply and getattr(args, "dry_run", False):
        parser.error("choose either --dry-run or --apply")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
