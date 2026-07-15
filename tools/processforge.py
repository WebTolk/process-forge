#!/usr/bin/env python3
"""ProcessForge MVP CLI for workplace/project init and doctor checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_FLOW_ROOT = ".pf"

PROJECT_PRIVATE_GITIGNORE = [
    ".pf/process-forge.local.yaml",
    ".pf/runtime/",
    ".pf/private-notes/",
    ".pf/cache/",
    ".secrets/",
    "*.tmp",
    "*.bak",
]

PROJECT_FLOW_DIRS = [
    "processes",
    "packages",
    "templates",
    "assignments",
    "artifacts",
    "contexts",
    "contexts/assignment-capsules",
    "logs",
    "handoffs",
    "reviews",
    "adr",
    "schemas",
    "runtime/cache",
    "runtime/telemetry",
    "runtime/events",
    "runtime/chat/transcripts",
    "runtime/hooks/outbox",
    "runtime/hooks/results",
    "runtime/queue",
    "runtime/sessions",
]

GLOBAL_AGENT_SECTION_START = "<!-- PROCESSFORGE:START -->"
GLOBAL_AGENT_SECTION_END = "<!-- PROCESSFORGE:END -->"

GLOBAL_AGENT_SECTION = f"""{GLOBAL_AGENT_SECTION_START}
## ProcessForge

Apply this section when:
- the user mentions ProcessForge;
- the user says "по флоу";
- the user points to a `.pf/` directory;
- the project contains `.pf/process-forge.yaml`;
- an assignment references ProcessForge.

Rules:
1. Do not load all knowledge from this file.
2. Read the project flow entrypoint: `.pf/AGENTS.md`.
3. Read `.pf/process-forge.yaml`.
4. Prefer `.pf/contexts/project-context.snapshot.md` if it exists.
5. If the snapshot is missing or stale, run/request project context refresh.
6. Read the workplace manifest and terms registry from `.pf/process-forge.local.yaml` when local config exists.
7. Use `terms.yaml` to resolve phrases such as "локальная база знаний", "проектная база знаний",
   "платформенные знания Joomla", "глобальные шаблоны", "глобальные инструменты", and "MCP".
8. Never write secrets or local absolute paths to public files.
9. Follow assignment boundaries.
10. Write session telemetry when working inside ProcessForge.
{GLOBAL_AGENT_SECTION_END}
"""

REQUIRED_TELEMETRY_EVENTS = [
    "session_start",
    "snapshot_check",
    "source_read",
    "assignment_loaded",
    "capability_check",
    "tool_selected",
    "tool_invoked",
    "tool_failed",
    "mcp_check",
    "fallback_used",
    "conflict_detected",
    "file_scope_checked",
    "artifact_written",
    "review_requested",
    "handoff_created",
    "doctor_run",
    "session_end",
]

REQUIRED_PROCESSFORGE_EVENT_TYPES = [
    "session.started",
    "session.ended",
    "session.message.recorded",
    "chat.message.recorded",
    "process.started",
    "process.completed",
    "stage.started",
    "stage.completed",
    "assignment.created",
    "assignment.started",
    "assignment.completed",
    "artifact.created",
    "artifact.updated",
    "review.requested",
    "review.completed",
    "gate.passed",
    "gate.failed",
    "tool.invoked",
    "tool.failed",
    "mcp.invoked",
    "mcp.failed",
    "hook.dispatched",
    "hook.failed",
    "context.snapshot.refreshed",
    "context.snapshot.stale",
    "capability.missing",
]

BUILTIN_CAPABILITIES = {
    "repository.read",
    "repository.scan",
    "repository_read",
    "markdown.editing",
    "markdown_editing",
    "filesystem.read",
    "filesystem.write",
    "schema_validation",
    "validation",
    "context.status",
    "context.resolve",
    "processforge-cli",
    "architecture",
    "artifact_review",
    "content_planning",
    "editorial_review",
    "investigation",
    "process_coordination",
    "process_governance",
    "reporting",
    "repository_write",
    "research",
    "review",
    "test_execution",
    "test_planning",
    "test_running",
    "writing",
}

BUILTIN_SEED_CAPABILITIES = set(BUILTIN_CAPABILITIES)

JOOMLA_PROJECT_TYPES = {
    "joomla-component",
    "joomla_component",
    "joomla component",
    "joomla-plugin",
    "joomla_plugin",
    "joomla plugin",
    "joomla-library",
    "joomla_library",
    "joomla library",
}

BUILTIN_PLATFORM_CONTRACTS: dict[str, dict[str, Any]] = {
    "platform.joomla": {
        "schema_version": 1,
        "id": "platform.joomla",
        "type": "platform_contract",
        "version": "1.0.0",
        "requires": {
            "capabilities": [
                "repository.read",
                "markdown.editing",
                "schema_validation",
            ]
        },
        "includes": {
            "knowledge_packages": [
                "php.core",
                "joomla.official-docs",
                "joomla.source-code",
                "joomla.development-articles",
                "joomla.snippets",
            ],
            "tools": [
                "php.syntax-check",
                "php.static-analysis",
                "package.builder",
            ],
            "mcp": [
                "repository.symbol-analysis",
                "official-documentation",
            ],
            "templates": [
                "joomla.component",
                "joomla.plugin",
                "joomla.form-field",
                "php.docblock",
            ],
        },
        "policies": {
            "missing_required_capability": "block",
            "missing_optional_resource": "warn",
        },
    }
}

BACKSLASH = chr(92)
COLON_WS = ":" + r"\s*"
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


def locate_flow_root(project_root: Path, *, prefer_pf: bool = True) -> Path:
    return project_root / PROJECT_FLOW_ROOT


def require_flow_root(project_root: Path) -> Path:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    if not manifest.is_file():
        raise SystemExit(
            f"FAIL: .pf/process-forge.yaml not found under {project_root}. "
            "Run `processforge init-project --project-root <project-root> --workplace <workplace.yaml> --apply` first."
        )
    return flow_root


def flow_layout(project_root: Path) -> str:
    flow_root = locate_flow_root(project_root)
    return "pf" if (flow_root / "process-forge.yaml").is_file() else "missing"


def flow_label(project_root: Path) -> str:
    return PROJECT_FLOW_ROOT


def flow_path(project_root: Path, *parts: str) -> Path:
    return locate_flow_root(project_root) / Path(*parts)


def iter_flow_roots(project_root: Path) -> list[Path]:
    pf_root = project_root / PROJECT_FLOW_ROOT
    return [pf_root] if pf_root.is_dir() else []


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
    yaml_literals = {"*", "null", "true", "false", "yes", "no", "on", "off", "~"}
    special_start = ("-", "?", "&", "*", "!", "%", "@", "`", ">", "|")
    if (
        text.lower() in yaml_literals
        or text.startswith(special_start)
        or any(char in text for char in [":", "#", "{", "}", "[", "]", "\\"])
        or text.strip() != text
    ):
        return "'" + text.replace("'", "''") + "'"
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


def upsert_bounded_section(existing: str, section: str) -> str:
    section = ensure_trailing_newline(section).rstrip()
    pattern = re.compile(
        re.escape(GLOBAL_AGENT_SECTION_START) + r".*?" + re.escape(GLOBAL_AGENT_SECTION_END),
        re.DOTALL,
    )
    if pattern.search(existing):
        return ensure_trailing_newline(pattern.sub(section, existing).rstrip())
    if existing.strip():
        return ensure_trailing_newline(existing.rstrip() + "\n\n" + section)
    return ensure_trailing_newline(section)


def write_global_agent_section(path: Path, *, dry_run: bool = False, force: bool = False) -> WriteResult:
    existing = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    updated = upsert_bounded_section(existing, GLOBAL_AGENT_SECTION)
    if existing == updated:
        return WriteResult(path, "unchanged", path)
    if dry_run or (path.exists() and not force):
        candidate = path.with_name(path.name + ".candidate")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(updated, encoding="utf-8")
        return WriteResult(path, "candidate", candidate)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
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
            "local_knowledge_base": {
                "label": "local knowledge base",
                "label_ru": "локальная база знаний",
                "aliases": ["local knowledge", "knowledge folders", "documentation roots"],
                "aliases_ru": ["локальные знания", "папки со знаниями", "локальная база знаний"],
                "definition": "Workplace-scoped directories with documentation, standards, references, and rules.",
                "resolves_to": {"registry": "knowledge_roots", "scope": "workplace"},
            },
            "project_knowledge_base": {
                "label": "project knowledge base",
                "label_ru": "проектная база знаний",
                "aliases": ["project knowledge", "project notes", "project artifacts"],
                "aliases_ru": ["проектные знания", "знания проекта"],
                "definition": "Project-scoped knowledge stored in the project flow.",
                "resolves_to": {"type": "project_knowledge", "project_paths": [".pf/packages", ".pf/artifacts"]},
            },
            "joomla_platform_knowledge": {
                "label": "Joomla platform knowledge",
                "label_ru": "платформенные знания Joomla",
                "aliases": ["Joomla knowledge", "Joomla platform"],
                "aliases_ru": ["знания Joomla", "платформа Joomla"],
                "definition": "Joomla platform contract and its referenced knowledge resources.",
                "resolves_to": {"registry": "platform_contracts", "id": "joomla"},
            },
            "global_templates": {
                "label": "global templates",
                "label_ru": "глобальные шаблоны",
                "aliases": ["template roots", "shared templates", "reusable templates"],
                "aliases_ru": ["общие шаблоны", "межпроектные шаблоны", "копируемые шаблоны"],
                "definition": "Reusable template directories available to projects through the workplace.",
                "resolves_to": {"registry": "templates", "scope": "workplace"},
            },
            "global_tools": {
                "label": "global tools",
                "label_ru": "глобальные инструменты",
                "aliases": ["tool registry", "tools", "global tools"],
                "aliases_ru": ["сборщики", "линтеры", "генераторы", "утилиты"],
                "definition": "Configured tool capability providers available through the workplace.",
                "resolves_to": {"registry": "tools", "scope": "workplace"},
            },
            "mcp_registry": {
                "label": "MCP registry",
                "aliases": ["MCP", "MCP servers"],
                "definition": "Configured MCP capability providers.",
                "resolves_to": {"registry": "mcp", "scope": "workplace"},
            },
            "package_roots": {
                "label": "package roots",
                "aliases": ["knowledge packages", "process packages"],
                "definition": "Directories containing versioned ProcessForge packages.",
                "resolves_to": {"registry": "package_roots", "scope": "workplace"},
            },
            "distribution_registry": {
                "label": "distribution registry",
                "aliases": ["ProcessForge distribution", "linked core", "core registry"],
                "definition": "Workplace registry that points projects to versioned ProcessForge distributions.",
                "resolves_to": {"registry": "distributions", "scope": "workplace"},
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
            "install_mode": "linked",
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
            "distributions": "registries/distributions.yaml",
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
    distribution_entries = dict_entries_from_answers(paths_answers.get("distributions"), "distribution", "workplace")
    if not distribution_entries:
        distribution_entries = [
            {
                "id": "processforge",
                "name": "ProcessForge",
                "path": str(ROOT),
                "version": "0.1.0",
                "channel": "stable",
                "status": "available",
                "provides": [
                    "processforge.core",
                    "processforge.schemas",
                    "processforge.tools",
                    "processforge.templates",
                    "processforge.processes",
                ],
            }
        ]

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
- registries/distributions.yaml
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
        root / "registries" / "distributions.yaml": dump_yaml(
            {"schema_version": 1, "distributions": distribution_entries}
        ),
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
    results: list[WriteResult] = []
    for path, content in files.items():
        if path.name == "AGENTS.md":
            results.append(write_global_agent_section(path, force=args.force))
        else:
            results.append(write_file(path, content, force=args.force))
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, root)}")
    return 0


def command_global_agents_section(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    result = write_global_agent_section(path, dry_run=args.dry_run, force=args.force)
    print(f"{result.status.upper()}: {result.target}")
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
        "registries/distributions.yaml",
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
    top_dirs = sorted(
        {
            item.parts[0]
            for path in files
            for item in [path.relative_to(project_root)]
            if item.parts
        }.union({path.name for path in project_root.iterdir() if path.is_dir() and path.name not in {".git", ".idea", ".serena"}})
    )
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


def answer_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(answer_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(answer_strings(item))
    return strings


def normalize_hint(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def platform_ids_from_hints(hints: list[str]) -> list[str]:
    platforms: set[str] = set()
    for hint in hints:
        normalized = normalize_hint(hint)
        compact = normalized.replace(" ", "-")
        if compact in JOOMLA_PROJECT_TYPES or normalized in JOOMLA_PROJECT_TYPES:
            platforms.add("joomla")
        elif "joomla" in normalized and any(kind in normalized for kind in ["component", "plugin", "library", "extension"]):
            platforms.add("joomla")
    return sorted(platforms)


def selected_project_platforms(detected: dict[str, Any], answers: dict[str, Any], project_type: str) -> list[str]:
    project_answers = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
    intake = answers.get("intake", {})
    hints = [project_type]
    for key in ["type", "type_hint", "platform", "platform_hint", "kind"]:
        value = project_answers.get(key)
        if value:
            hints.extend(answer_strings(value))
    if intake:
        hints.extend(answer_strings(intake))
    selected = set(str(item) for item in detected.get("platforms", []) if item)
    selected.update(platform_ids_from_hints(hints))
    return sorted(selected)


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
    project_type = str(project_answers.get("type") or project_answers.get("type_hint") or detected_kind)
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


def load_workplace_registry(workplace_manifest: Path | None, registry_key: str, default_name: str) -> dict[str, Any]:
    if not workplace_manifest or not workplace_manifest.is_file():
        return {}
    path = resolve_registry_path(workplace_manifest, registry_key, default_name)
    return load_yaml_document(path)


def platform_contract_id(platform_id: str) -> str:
    return platform_id if platform_id.startswith("platform.") else f"platform.{platform_id}"


def platform_contract_registry_entry(workplace_manifest: Path | None, contract_id: str) -> dict[str, Any] | None:
    registry = load_workplace_registry(workplace_manifest, "platforms", "platforms.yaml")
    entries = registry.get("platforms") if isinstance(registry, dict) else None
    if not isinstance(entries, list):
        return None
    aliases = {contract_id, contract_id.removeprefix("platform.")}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_ids = {str(entry.get("id", "")), str(entry.get("package_id", ""))}
        if aliases.intersection(entry_ids):
            return entry
    return None


def resolve_registry_relative_path(base: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_platform_contract(workplace_manifest: Path | None, contract_id: str) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    builtin = BUILTIN_PLATFORM_CONTRACTS.get(contract_id, {"id": contract_id, "requires": {}, "includes": {}})
    entry = platform_contract_registry_entry(workplace_manifest, contract_id)
    if not entry:
        return builtin, None, "missing"
    if str(entry.get("status", "available")) in {"missing", "disabled"}:
        return builtin, entry, str(entry.get("status"))
    raw_path = entry.get("path")
    if raw_path and workplace_manifest:
        contract_path = resolve_registry_relative_path(workplace_manifest.parent, str(raw_path))
        contract_data = load_yaml_document(contract_path)
        if contract_data and not yaml_error(contract_data):
            return contract_data, entry, "available"
    return builtin, entry, "available"


def list_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                output.append(item)
            elif isinstance(item, dict):
                item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
                if item_id:
                    output.append(str(item_id))
        return output
    return []


def contract_required_capabilities(contract: dict[str, Any]) -> list[str]:
    requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
    return list_value(requires.get("capabilities"))


def contract_includes(contract: dict[str, Any], key: str) -> list[str]:
    includes = contract.get("includes", {}) if isinstance(contract.get("includes"), dict) else {}
    return list_value(includes.get(key))


def resolve_platform_contracts(workplace_manifest: Path | None, platform_ids: list[str]) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    required_capabilities: set[str] = set()
    knowledge_packages: set[str] = set()
    tools: set[str] = set()
    mcp: set[str] = set()
    templates: set[str] = set()
    missing_required_contracts: list[str] = []

    for platform_id in platform_ids:
        contract_id = platform_contract_id(platform_id)
        contract, entry, status = load_platform_contract(workplace_manifest, contract_id)
        required_capabilities.update(contract_required_capabilities(contract))
        knowledge_packages.update(contract_includes(contract, "knowledge_packages"))
        tools.update(contract_includes(contract, "tools"))
        mcp.update(contract_includes(contract, "mcp"))
        templates.update(contract_includes(contract, "templates"))
        if status != "available":
            missing_required_contracts.append(contract_id)
        contracts.append(
            {
                "id": contract_id,
                "platform": platform_id,
                "source": "workplace",
                "status": "available" if status == "available" else "missing",
                "registry_entry": str(entry.get("id")) if isinstance(entry, dict) and entry.get("id") else None,
                "required": True,
                "required_capabilities": sorted(contract_required_capabilities(contract)),
                "knowledge_packages": sorted(contract_includes(contract, "knowledge_packages")),
                "tools": sorted(contract_includes(contract, "tools")),
                "mcp": sorted(contract_includes(contract, "mcp")),
                "templates": sorted(contract_includes(contract, "templates")),
            }
        )

    return {
        "contracts": contracts,
        "missing_required_contracts": sorted(set(missing_required_contracts)),
        "required_capabilities": sorted(required_capabilities),
        "knowledge_packages": sorted(knowledge_packages),
        "tools": sorted(tools),
        "mcp": sorted(mcp),
        "templates": sorted(templates),
    }


def registry_ids(data: dict[str, Any], collection_key: str) -> set[str]:
    entries = data.get(collection_key) if isinstance(data, dict) else None
    ids: set[str] = set()
    if not isinstance(entries, list):
        return ids
    for entry in entries:
        if isinstance(entry, dict):
            for key in ["id", "package_id", "capability"]:
                value = entry.get(key)
                if value:
                    ids.add(str(value))
    return ids


def optional_platform_resource_warnings(workplace_manifest: Path | None, resolved: dict[str, Any], package_index_ids: set[str] | None = None) -> list[dict[str, Any]]:
    package_ids = registry_ids(load_workplace_registry(workplace_manifest, "package_roots", "package-roots.yaml"), "package_roots")
    if package_index_ids:
        package_ids = package_ids.union(package_index_ids)
    tool_ids = registry_ids(load_workplace_registry(workplace_manifest, "tools", "tools.yaml"), "tools")
    mcp_ids = registry_ids(load_workplace_registry(workplace_manifest, "mcp", "mcp.yaml"), "mcp_servers")
    template_ids = registry_ids(load_workplace_registry(workplace_manifest, "templates", "templates.yaml"), "template_roots")
    warnings: list[dict[str, Any]] = []
    for group, available, collection in [
        ("knowledge_package", package_ids, resolved.get("knowledge_packages", [])),
        ("tool", tool_ids, resolved.get("tools", [])),
        ("mcp", mcp_ids, resolved.get("mcp", [])),
        ("template", template_ids, resolved.get("templates", [])),
    ]:
        for item in collection:
            if item not in available:
                warnings.append({"kind": group, "id": item, "status": "missing", "severity": "warn"})
    return warnings


def match_global_resources(workplace_manifest: Path, detected: dict[str, Any], required: list[str], optional: list[str]) -> dict[str, list[str]]:
    platforms_text = registry_text(workplace_manifest, "platforms.yaml")
    tools_text = registry_text(workplace_manifest, "tools.yaml")
    mcp_text = registry_text(workplace_manifest, "mcp.yaml")
    templates_text = registry_text(workplace_manifest, "templates.yaml")
    package_text = registry_text(workplace_manifest, "package-roots.yaml")

    matched_platforms = [item for item in detected["platforms"] if item and item in platforms_text]
    missing_platforms = [item for item in detected["platforms"] if item and item not in platforms_text]
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
        "missing_platforms": missing_platforms,
        "matched_packages": matched_packages,
        "matched_tools": matched_tools,
        "matched_mcp": matched_mcp,
        "matched_templates": matched_templates,
        "missing_required": missing_required,
        "optional_missing": optional_missing,
        "conflicts": [],
    }


def build_project_files(project_root: Path, workplace_manifest: Path, answers: dict[str, Any]) -> dict[Path, str]:
    flow_root = project_root / PROJECT_FLOW_ROOT
    detected = detect_project(project_root)
    defaults = project_defaults(project_root, answers, detected)
    detected["platforms"] = selected_project_platforms(detected, answers, defaults["type"])
    mode = project_mode(project_root, answers)
    required = answers.get("required_capabilities") if isinstance(answers.get("required_capabilities"), list) else []
    optional = answers.get("optional_capabilities") if isinstance(answers.get("optional_capabilities"), list) else []
    required = required or ["repository.read", "markdown.editing"]
    optional = optional or ["repository.symbol_analysis", "official_documentation"]
    platform_resolution = resolve_platform_contracts(workplace_manifest, detected["platforms"])
    required = sorted(set(required).union(platform_resolution["required_capabilities"]))
    matches = match_global_resources(workplace_manifest, detected, required, optional)
    knowledge_stack = [
        {"id": "processforge.core", "version": "^0.1", "source": "distribution", "distribution": "processforge"},
    ]
    for platform_id in detected["platforms"]:
        knowledge_stack.append(
            {
                "id": f"platform.{platform_id}",
                "version": "^1.0",
                "source": "workplace",
                "registry": "platforms",
            }
        )
    for package_id in platform_resolution["knowledge_packages"]:
        knowledge_stack.append(
            {
                "id": package_id,
                "version": "*",
                "source": "workplace",
                "registry": "package_roots",
                "load_policy": "on_demand",
            }
        )
    knowledge_stack.append({"id": f"project.{defaults['id']}", "version": "0.1.0", "source": "project"})

    public_manifest = {
        "schema_version": 1,
        "process_forge": {
            "version": "0.1.0",
            "version_constraint": "^0.1",
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
        "detected": {
            "languages": detected["languages"],
            "platforms": detected["platforms"],
            "project_kind": detected["project_kind"],
        },
        "platform_contracts": platform_resolution["contracts"],
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
            "hooks": "hooks.yaml",
        },
        "knowledge_stack": knowledge_stack,
        "required_capabilities": required,
        "optional_capabilities": optional,
        "selected_resources": {
            "knowledge_packages": platform_resolution["knowledge_packages"],
            "tools": platform_resolution["tools"],
            "mcp": platform_resolution["mcp"],
            "templates": platform_resolution["templates"],
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
        "process_forge": {"distribution_override": None},
        "local": {"project_root": str(project_root.resolve())},
        "overrides": {"package_roots": [], "template_roots": [], "tool_preferences": {}},
        "runtime": {
            "mode": "manual",
            "queue": "runtime/queue",
            "events": "runtime/events",
            "hooks": "runtime/hooks",
            "chat": "runtime/chat",
        },
    }

    agents = """# ProcessForge Project Instructions

This project uses ProcessForge.

## Start Order

1. Read `.pf/process-forge.yaml`.
2. Read `.pf/contexts/project-context.snapshot.md`.
3. If the snapshot is missing or stale, run/request project context refresh.
4. Read the current assignment from `.pf/assignments/` if assigned.
5. Read latest `.pf/artifacts/session-status-report.md` if present.
6. Read latest relevant logs/reviews/handoffs.
7. Use only tools/templates listed in snapshot or assignment.
8. Write session telemetry to `.pf/runtime/telemetry/`.
9. Let ProcessForge commands emit flow events to `.pf/runtime/events/`.

## Important Rules

- Do not edit files outside assignment scope.
- Do not put absolute local paths into public files.
- Do not commit `.pf/process-forge.local.yaml`.
- Do not commit `.pf/runtime/`.
- Use project-local templates before global templates when allowed.
- Record template usage.
- Record tool/MCP usage in session telemetry.
- Do not commit `.pf/runtime/events/` or webhook outbox payloads.
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

## Missing Optional Platform Resources

{markdown_list([f"{item['kind']}: {item['id']}" for item in optional_platform_resource_warnings(workplace_manifest, platform_resolution)])}

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

- .pf/AGENTS.md
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
- Root project AGENTS.md is not created by default.
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

    return {
        flow_root / "AGENTS.md": agents,
        flow_root / "process-forge.yaml": dump_yaml(public_manifest),
        flow_root / "process-forge.local.yaml": dump_yaml(local_manifest),
        flow_root / "hooks.yaml": dump_yaml(hooks),
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
        flow_root / "reviews" / "project-init-review.md": review,
    }


def command_init_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    workplace = Path(args.workplace).expanduser().resolve()
    answers = load_answers(Path(args.answers).expanduser().resolve() if args.answers else None)
    if args.apply and not workplace.is_file() and not args.allow_missing_workplace:
        raise SystemExit(f"FAIL: workplace manifest not found: {workplace}")
    if not project_root.exists() and args.apply:
        project_root.mkdir(parents=True)
    if not project_root.exists() and args.apply:
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    files = build_project_files(project_root, workplace, answers)
    flow_root = project_root / PROJECT_FLOW_ROOT
    planned_paths = list(files) + [flow_root / item for item in PROJECT_FLOW_DIRS] + [project_root / ".gitignore"]
    if not args.apply:
        print_plan("project init dry run", planned_paths, project_root)
        mode = project_mode(project_root, answers)
        print(f"MODE: {mode}")
        return 0

    for dirname in PROJECT_FLOW_DIRS:
        (flow_root / dirname).mkdir(parents=True, exist_ok=True)
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


def resolve_workplace_manifest(local_manifest: Path) -> Path | None:
    workplace = find_local_workplace_manifest(local_manifest.read_text(encoding="utf-8", errors="replace"))
    if not workplace:
        return None
    if not workplace.is_absolute():
        workplace = (local_manifest.parent / workplace).resolve()
    return workplace


def resolve_registry_path(workplace_manifest: Path, registry_key: str, default_name: str) -> Path:
    workplace = load_yaml_document(workplace_manifest)
    registries = workplace.get("registries", {}) if isinstance(workplace, dict) and isinstance(workplace.get("registries"), dict) else {}
    raw_path = str(registries.get(registry_key) or f"registries/{default_name}")
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (workplace_manifest.parent / path).resolve()


def distribution_registry_entries(workplace_manifest: Path) -> list[dict[str, Any]]:
    registry = resolve_registry_path(workplace_manifest, "distributions", "distributions.yaml")
    data = load_yaml_document(registry)
    entries = data.get("distributions") if isinstance(data, dict) else None
    return [item for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def resolve_distribution_path(workplace_manifest: Path, distribution_id: str = "processforge") -> Path | None:
    for entry in distribution_registry_entries(workplace_manifest):
        if str(entry.get("id")) != distribution_id:
            continue
        raw_path = entry.get("path")
        if not raw_path:
            return None
        path = Path(str(raw_path))
        if path.is_absolute():
            return path
        return (workplace_manifest.parent / path).resolve()
    return None


def distribution_checks(distribution_root: Path | None) -> list[Check]:
    checks: list[Check] = []
    if not distribution_root:
        return [check("FAIL", "processforge distribution path is not configured")]
    checks.append(check("PASS" if distribution_root.is_dir() else "FAIL", "processforge distribution exists"))
    for dirname in ["tools", "schemas", "processes", "packages", "templates"]:
        path = distribution_root / dirname
        checks.append(check("PASS" if path.is_dir() else "FAIL", f"processforge distribution has {dirname}/"))
    return checks


def report_has_missing_required_capabilities(path: Path) -> bool:
    return report_section_has_items(path, "## Missing Required Capabilities")


def report_section_has_items(path: Path, marker: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if marker not in text:
        return False
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    listed = [line.strip() for line in section.splitlines() if line.strip().startswith("- ")]
    return any(line != "- None." for line in listed)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def yaml_list_values(text: str, key: str) -> list[str]:
    values: list[str] = []
    lines = text.splitlines()
    key_pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*$")
    inline_pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$")
    for index, line in enumerate(lines):
        inline = inline_pattern.match(line)
        if inline:
            values.extend(item.strip().strip('"').strip("'") for item in inline.group(1).split(",") if item.strip())
            continue
        match = key_pattern.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        for child in lines[index + 1 :]:
            if not child.strip():
                continue
            child_indent = len(child) - len(child.lstrip(" "))
            if child_indent <= indent:
                break
            stripped = child.strip()
            if stripped.startswith("- "):
                values.append(stripped[2:].strip().strip('"').strip("'"))
    return values


def source_record(path: Path, root: Path, kind: str, required: bool, selection_reason: str, load_policy: str) -> dict[str, Any]:
    exists = path.is_file()
    record: dict[str, Any] = {
        "path": rel(path, root),
        "kind": kind,
        "required": required,
        "exists": exists,
        "selection_reason": selection_reason,
        "load_policy": load_policy,
    }
    if exists:
        checksum = sha256_file(path)
        record["checksum"] = checksum
        record["fingerprint"] = checksum
    else:
        record["checksum"] = "missing"
        record["fingerprint"] = "missing"
    return record


def resolve_flow_reference(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (locate_flow_root(project_root) / path).resolve()


def manifest_path_refs(project_root: Path, key: str) -> list[Path]:
    manifest = locate_flow_root(project_root) / "process-forge.yaml"
    data = load_yaml_document(manifest)
    refs = data.get(key) if isinstance(data, dict) else None
    paths: list[Path] = []
    if not isinstance(refs, list):
        return paths
    for item in refs:
        if isinstance(item, dict) and item.get("path"):
            paths.append(resolve_flow_reference(project_root, str(item["path"])))
    return paths


def collect_context_sources(project_root: Path, assignment: Path | None = None) -> list[dict[str, Any]]:
    flow_root = locate_flow_root(project_root)
    candidates: list[tuple[Path, str, bool]] = [
        (flow_root / "AGENTS.md", "agent-boot", True),
        (flow_root / "process-forge.yaml", "project-flow", True),
        (flow_root / "process-forge.local.yaml", "local-config", False),
        (project_root / "tools" / "processforge.py", "tool", False),
    ]
    candidates.extend((path, "process", False) for path in manifest_path_refs(project_root, "processes"))
    candidates.extend((path, "package", False) for path in manifest_path_refs(project_root, "packages"))
    for dirname, kind in [("processes", "process"), ("packages", "package")]:
        root = flow_root / dirname
        if root.is_dir():
            candidates.extend((path, kind, False) for path in sorted(root.glob("*.yaml")))
    template_root = flow_root / "templates"
    if template_root.is_dir():
        candidates.extend((path, "template", False) for path in sorted(template_root.glob("*.yaml")))
        candidates.extend((path, "template", False) for path in sorted(template_root.glob("*.md")))
    if assignment is not None:
        candidates.append((assignment, "assignment", True))

    seen: set[Path] = set()
    records: list[dict[str, Any]] = []
    for path, kind, required in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if required:
            reason = "required for session bootstrap" if kind != "assignment" else "required by context compile assignment"
            policy = "read_required"
        elif kind in {"process", "package", "template"}:
            reason = "available in broad project context; not loaded by default for workers"
            policy = "available"
        elif kind == "local-config":
            reason = "optional private local config"
            policy = "recommended_if_present"
        else:
            reason = "supporting context source"
            policy = "recommended"
        records.append(source_record(path, project_root, kind, required, reason, policy))
    return records


def source_fingerprints(sources: list[dict[str, Any]]) -> dict[str, str]:
    return {str(item["path"]): str(item.get("fingerprint", "missing")) for item in sources}


def source_texts(project_root: Path, sources: list[dict[str, Any]]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for item in sources:
        path = project_root / str(item["path"])
        if path.is_file():
            texts[str(item["path"])] = path.read_text(encoding="utf-8", errors="replace")
    return texts


def values_from_registry_entry(entry: Any) -> list[str]:
    values: list[str] = []
    if not isinstance(entry, dict):
        return values
    for key in ("capability", "capabilities", "provides"):
        value = entry.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
        elif isinstance(value, dict):
            nested = value.get("capabilities")
            if isinstance(nested, list):
                values.extend(str(item) for item in nested if isinstance(item, (str, int, float)))
    return values


def load_registry_capability_providers(project_root: Path) -> dict[str, str]:
    providers: dict[str, str] = {}
    registry_root = locate_flow_root(project_root)
    for rel_path, collection_key in [
        ("registries/tools.yaml", "tools"),
        ("registries/mcp.yaml", "mcp_servers"),
    ]:
        path = registry_root / rel_path
        if not path.is_file():
            continue
        try:
            data = load_answers(path)
        except SystemExit:
            continue
        entries = data.get(collection_key) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            provider_id = str(entry.get("id", rel_path)) if isinstance(entry, dict) else rel_path
            for capability in values_from_registry_entry(entry):
                providers[capability] = provider_id
    return providers


def resolve_capabilities(texts: dict[str, str], project_root: Path) -> dict[str, Any]:
    required: list[str] = []
    optional: list[str] = []
    for text in texts.values():
        required.extend(yaml_list_values(text, "required_capabilities"))
        optional.extend(yaml_list_values(text, "optional_capabilities"))
    required = sorted(set(item for item in required if item))
    optional = sorted(set(item for item in optional if item))
    registry_providers = load_registry_capability_providers(project_root)
    available = set(BUILTIN_SEED_CAPABILITIES).union(registry_providers)
    missing_required = [item for item in required if item not in available]
    missing_optional = [item for item in optional if item not in available]
    return {
        "required": required,
        "optional": optional,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "builtin": sorted(BUILTIN_SEED_CAPABILITIES),
        "providers": registry_providers,
    }


def load_yaml_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(text)
    except Exception as exc:
        return {"__yaml_error__": f"{exc.__class__.__name__}: {exc}"}


def yaml_error(data: Any) -> str | None:
    if isinstance(data, dict) and isinstance(data.get("__yaml_error__"), str):
        return str(data["__yaml_error__"])
    return None


def fingerprint_record(path: Path, project_root: Path, source_id: str, kind: str, *, private: bool = False, display_path: str | None = None) -> dict[str, Any]:
    exists = path.is_file()
    record: dict[str, Any] = {
        "id": source_id,
        "path": display_path or rel(path, project_root),
        "kind": kind,
        "checksum": sha256_file(path) if exists else "missing",
    }
    if private:
        record["private"] = True
    if not exists:
        record["exists"] = False
    return record


def collect_project_snapshot_sources(project_root: Path) -> list[dict[str, Any]]:
    flow_root = locate_flow_root(project_root)
    sources: list[dict[str, Any]] = [
        fingerprint_record(flow_root / "process-forge.yaml", project_root, "project_manifest", "manifest"),
    ]
    local_config = flow_root / "process-forge.local.yaml"
    if local_config.is_file():
        sources.append(fingerprint_record(local_config, project_root, "local_config", "local-config", private=True))
        workplace = find_local_workplace_manifest(local_config.read_text(encoding="utf-8", errors="replace"))
        if workplace:
            workplace_path = workplace.expanduser()
            if not workplace_path.is_absolute():
                workplace_path = (local_config.parent / workplace_path).resolve()
            sources.append(
                fingerprint_record(
                    workplace_path,
                    project_root,
                    "workplace_manifest",
                    "workplace",
                    private=True,
                    display_path="<private-workplace-manifest-ref>",
                )
            )

    for path in manifest_path_refs(project_root, "processes"):
        source_id = safe_id(f"process-{rel(path, project_root)}", "process-source")
        sources.append(fingerprint_record(path, project_root, source_id, "process"))
    for path in manifest_path_refs(project_root, "packages"):
        source_id = safe_id(f"package-{rel(path, project_root)}", "package-source")
        sources.append(fingerprint_record(path, project_root, source_id, "package"))

    for dirname, kind in [
        ("processes", "process-override"),
        ("packages", "package-override"),
        ("registries", "registry"),
        ("templates", "template-override"),
    ]:
        root = flow_root / dirname
        if root.is_dir():
            for path in sorted(item for item in root.rglob("*") if item.is_file() and item.suffix.lower() in {".yaml", ".yml", ".json", ".md"}):
                source_id = safe_id(f"{kind}-{rel(path, flow_root)}", f"{kind}-source")
                sources.append(fingerprint_record(path, project_root, source_id, kind))
    return sources


def workplace_package_root_paths(workplace_manifest: Path | None) -> list[Path]:
    if not workplace_manifest or not workplace_manifest.is_file():
        return []
    registry = load_workplace_registry(workplace_manifest, "package_roots", "package-roots.yaml")
    entries = registry.get("package_roots") if isinstance(registry, dict) else None
    roots: list[Path] = []
    if not isinstance(entries, list):
        return roots
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        roots.append(resolve_registry_relative_path(workplace_manifest.parent, str(entry["path"])))
    return roots


def package_manifest_candidates(project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None = None) -> list[Path]:
    flow_root = locate_flow_root(project_root)
    candidates: list[Path] = []
    candidates.extend(manifest_path_refs(project_root, "packages"))
    roots: list[Path | None] = [flow_root / "packages", distribution_root / "packages" if distribution_root else None]
    roots.extend(workplace_package_root_paths(workplace_manifest))
    for root in roots:
        if root and root.is_dir():
            candidates.extend(sorted(root.glob("*.yaml")))
            candidates.extend(sorted(root.glob("*.yml")))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def package_manifest_index(project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None = None) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in package_manifest_candidates(project_root, distribution_root, workplace_manifest):
        data = load_yaml_document(path)
        if not data or yaml_error(data):
            continue
        package_id = data.get("id")
        if not package_id:
            continue
        record = dict(data)
        record["__manifest_path"] = path
        index[str(package_id)] = record
    return index


def resource_record_from_package(package_id: str, resource: dict[str, Any]) -> dict[str, Any]:
    resource_id = str(resource.get("id", "resource"))
    record: dict[str, Any] = {
        "id": f"{package_id}:{resource_id}",
        "resource_id": resource_id,
        "package": package_id,
        "kind": str(resource.get("kind", "reference")),
        "title": str(resource.get("title", resource_id)),
        "load_policy": str(resource.get("load_policy", "on_demand")),
        "index_policy": str(resource.get("index_policy", "metadata")),
        "status": "indexed",
    }
    for key in ["path", "path_ref", "version", "description"]:
        if key in resource:
            record[key] = resource[key]
    return record


def resolve_package_resources(project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None, package_ids: list[str]) -> list[dict[str, Any]]:
    package_index = package_manifest_index(project_root, distribution_root, workplace_manifest)
    resources: list[dict[str, Any]] = []
    for package_id in package_ids:
        manifest = package_index.get(package_id)
        if not manifest:
            continue
        package_resources = manifest.get("resources")
        if not isinstance(package_resources, list):
            continue
        for resource in package_resources:
            if isinstance(resource, dict):
                resources.append(resource_record_from_package(package_id, resource))
    return resources


def capability_records(required: list[str], optional: list[str], providers: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    available = set(BUILTIN_SEED_CAPABILITIES).union(providers)

    def record(capability: str, required_capability: bool) -> dict[str, Any]:
        is_available = capability in available
        provider = "builtin" if capability in BUILTIN_SEED_CAPABILITIES else providers.get(capability)
        return {
            "id": capability,
            "status": "available" if is_available else "missing",
            "provider": provider if is_available else None,
            "severity": "fail" if required_capability and not is_available else ("warn" if not required_capability and not is_available else "info"),
        }

    return [record(item, True) for item in required], [record(item, False) for item in optional]


def project_context_snapshot_paths(project_root: Path) -> tuple[Path, Path]:
    contexts = locate_flow_root(project_root) / "contexts"
    return contexts / "project-context.snapshot.yaml", contexts / "project-context.snapshot.md"


def build_project_context_snapshot(project_root: Path, *, max_age_days: int = 7) -> dict[str, Any]:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    if not manifest.is_file():
        raise SystemExit(f"FAIL: process-forge manifest not found: {rel(manifest, project_root)}")
    manifest_data = load_yaml_document(manifest)
    manifest_text = manifest.read_text(encoding="utf-8", errors="replace")
    sources = collect_project_snapshot_sources(project_root)
    providers = load_registry_capability_providers(project_root)
    required = sorted(set(yaml_list_values(manifest_text, "required_capabilities")))
    optional = sorted(set(yaml_list_values(manifest_text, "optional_capabilities")))
    required_records, optional_records = capability_records(required, optional, providers)
    generated_at = now_utc()
    valid_until = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=max_age_days)).isoformat().replace("+00:00", "Z")
    project = manifest_data.get("project", {}) if isinstance(manifest_data.get("project"), dict) else {}
    process_forge_data = manifest_data.get("process_forge", {}) if isinstance(manifest_data.get("process_forge"), dict) else {}
    detected_data = manifest_data.get("detected", {}) if isinstance(manifest_data.get("detected"), dict) else {}
    workplace_manifest_path: Path | None = None
    distribution_root: Path | None = None
    local_config = flow_root / "process-forge.local.yaml"
    if local_config.is_file():
        workplace_manifest_path = resolve_workplace_manifest(local_config)
        if workplace_manifest_path and workplace_manifest_path.is_file():
            distribution_root = resolve_distribution_path(workplace_manifest_path, "processforge")
    elif isinstance(manifest_data.get("workplace"), dict) and manifest_data["workplace"].get("reference") == "auto":
        distribution_root = project_root
    manifest_platform_contracts = manifest_data.get("platform_contracts") if isinstance(manifest_data.get("platform_contracts"), list) else []
    manifest_platform_ids = [
        str(item.get("platform") or str(item.get("id", "")).removeprefix("platform."))
        for item in manifest_platform_contracts
        if isinstance(item, dict) and (item.get("platform") or item.get("id"))
    ]
    if not manifest_platform_ids:
        manifest_platform_ids = [str(item) for item in detected_data.get("platforms", []) if isinstance(item, str)]
    platform_resolution = resolve_platform_contracts(workplace_manifest_path, manifest_platform_ids)
    package_index_ids = set(package_manifest_index(project_root, distribution_root, workplace_manifest_path))
    platform_resource_warnings = optional_platform_resource_warnings(workplace_manifest_path, platform_resolution, package_index_ids)
    package_ids = [
        str(item.get("id"))
        for item in manifest_data.get("knowledge_stack", [])
        if isinstance(item, dict) and item.get("id")
    ]
    package_ids.extend(platform_resolution["knowledge_packages"])
    process_refs = manifest_data.get("processes") if isinstance(manifest_data.get("processes"), list) else []
    package_refs = manifest_data.get("packages") if isinstance(manifest_data.get("packages"), list) else []
    enabled_processes = [
        {"id": str(item.get("id", "unknown")), "path": str(item.get("path", ""))}
        for item in process_refs
        if isinstance(item, dict)
    ]
    selected_packages = [
        {"id": str(item.get("id", "unknown")), "path": str(item.get("path", ""))}
        for item in package_refs
        if isinstance(item, dict)
    ]
    package_ids.extend(item["id"] for item in selected_packages)
    package_resources = resolve_package_resources(project_root, distribution_root, workplace_manifest_path, sorted(set(package_ids)))
    health_status = "blocked" if any(item["severity"] == "fail" for item in required_records) or platform_resolution["missing_required_contracts"] else ("warn" if any(item["severity"] == "warn" for item in optional_records) or platform_resource_warnings else "pass")
    return {
        "schema_version": 1,
        "snapshot": {
            "id": "project-context",
            "generated_at": generated_at,
            "valid_until": valid_until,
            "refresh_policy": {
                "max_age_days": max_age_days,
                "refresh_when_sources_change": True,
                "refresh_when_workplace_changes": True,
                "refresh_when_package_versions_change": True,
                "refresh_when_required_tools_change": True,
            },
            "health": {"status": health_status},
        },
        "project": {
            "id": str(project.get("id", safe_id(project_root.name))),
            "name": str(project.get("name", project_root.name)),
            "type": project.get("type", ["software_project"]),
        },
        "flow": {
            "root": flow_label(project_root),
            "layout": flow_layout(project_root),
            "manifest": rel(manifest, project_root),
            "local_config": rel(flow_root / "process-forge.local.yaml", project_root),
        },
        "process_forge": {
            "version": str(process_forge_data.get("version", "0.1.0")),
            "version_constraint": str(process_forge_data.get("version_constraint", "^0.1")),
            "install_mode": str(process_forge_data.get("install_mode", "linked")),
            "distribution": {
                "id": "processforge",
                "source": "workplace" if workplace_manifest_path else "project",
                "path": "<private-distribution-ref>" if distribution_root else "missing",
                "status": "available" if distribution_root and distribution_root.is_dir() else "missing",
            },
        },
        "platform_contracts": {
            "selected": platform_resolution["contracts"],
            "missing_required": platform_resolution["missing_required_contracts"],
            "missing_optional_resources": platform_resource_warnings,
        },
        "sources": {"fingerprints": sources},
        "knowledge_stack": manifest_data.get("knowledge_stack", [{"id": "processforge.core", "version": "0.1.0", "source": "distribution"}]),
        "resolved_policies": {
            "hard": [
                {"id": "public.no_local_absolute_paths", "value": True, "locked": True},
                {"id": "files.one_writer_per_scope", "value": True, "locked": True},
                {"id": "secrets.do_not_store", "value": True, "locked": True},
                {"id": "runtime.private", "value": True, "locked": True},
                {"id": "markdown.not_machine_merge_source", "value": True, "locked": True},
            ],
            "preferences": [
                {"id": "templates.project_overrides_global", "value": True},
                {"id": "session.prefer_project_context_snapshot", "value": True},
            ],
        },
        "capabilities": {"required": required_records, "optional": optional_records},
        "knowledge_resources": {
            "selected": package_resources,
            "missing_optional": platform_resource_warnings,
        },
        "tools": {"required": platform_resolution["tools"], "optional": [], "source": "workplace-registry"},
        "mcp": {"required": platform_resolution["mcp"], "optional": [], "source": "workplace-registry"},
        "templates": {"project": [str(item["path"]) for item in sources if item.get("kind") == "template"], "global": platform_resolution["templates"], "source": "workplace-registry"},
        "processes": {"enabled": enabled_processes},
        "packages": {"selected": selected_packages},
        "session": {
            "startup_read_order": [
                rel(flow_root / "AGENTS.md", project_root),
                rel(flow_root / "process-forge.yaml", project_root),
                rel(flow_root / "contexts" / "project-context.snapshot.md", project_root),
                "current assignment",
                "relevant logs/reviews/handoffs",
            ],
            "telemetry_root": rel(flow_root / "runtime" / "telemetry", project_root),
            "events_log": rel(flow_root / "runtime" / "events" / "events.ndjson", project_root),
        },
    }


def render_project_context_snapshot_md(snapshot: dict[str, Any], freshness: str = "fresh", reasons: list[str] | None = None) -> str:
    project = snapshot.get("project", {})
    flow = snapshot.get("flow", {})
    meta = snapshot.get("snapshot", {})
    capabilities = snapshot.get("capabilities", {})
    policies = snapshot.get("resolved_policies", {})
    process_forge = snapshot.get("process_forge", {}) if isinstance(snapshot.get("process_forge"), dict) else {}
    distribution = process_forge.get("distribution", {}) if isinstance(process_forge.get("distribution"), dict) else {}
    platforms = snapshot.get("platform_contracts", {}).get("selected", []) if isinstance(snapshot.get("platform_contracts"), dict) else []
    resources = snapshot.get("knowledge_resources", {}).get("selected", []) if isinstance(snapshot.get("knowledge_resources"), dict) else []
    processes = snapshot.get("processes", {}).get("enabled", []) if isinstance(snapshot.get("processes"), dict) else []
    templates = snapshot.get("templates", {}).get("project", []) if isinstance(snapshot.get("templates"), dict) else []

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
            "## Connected Knowledge Packages",
            "",
            md_items(snapshot.get("knowledge_stack", [])),
            "",
            "## Platform Contracts",
            "",
            md_items(platforms),
            "",
            "## Knowledge Resources",
            "",
            md_items(resources),
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
            "## Missing Tools / MCP",
            "",
            "- None recorded in this snapshot.",
            "",
            "## Hard Policies",
            "",
            md_items(policies.get("hard", []) if isinstance(policies, dict) else []),
            "",
            "## Preferences",
            "",
            md_items(policies.get("preferences", []) if isinstance(policies, dict) else []),
            "",
            "## Templates",
            "",
            md_items(templates),
            "",
            "## Session Start",
            "",
            "Read in this order:",
            "",
            "1. `.pf/AGENTS.md`.",
            "2. `.pf/process-forge.yaml`.",
            "3. this snapshot.",
            "4. current assignment.",
            "5. relevant logs/reviews/handoffs.",
            "",
            f"Telemetry root: `{snapshot.get('session', {}).get('telemetry_root', 'runtime/telemetry')}`",
            f"Events log: `{snapshot.get('session', {}).get('events_log', 'runtime/events/events.ndjson')}`",
            "",
            "## Current Risks",
            "",
            "- Markdown files are human-readable context and are not authoritative structured merge sources.",
            "- If freshness is stale, refresh before using required capability decisions.",
            "",
            "## Refresh Instructions",
            "",
            "Run `python tools/processforge.py project-context-refresh --project-root <project-root>`.",
            "",
        ]
    )


def parse_snapshot_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def project_context_freshness(project_root: Path) -> tuple[str, list[str], dict[str, Any]]:
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    if not snapshot_yaml.is_file():
        return "missing", [], {}
    snapshot = load_yaml_document(snapshot_yaml)
    reasons: list[str] = []
    for key in ["schema_version", "snapshot", "project", "flow", "sources", "capabilities", "session"]:
        if key not in snapshot:
            reasons.append(f"snapshot schema invalid: missing {key}")
    meta = snapshot.get("snapshot", {}) if isinstance(snapshot.get("snapshot"), dict) else {}
    valid_until = parse_snapshot_timestamp(meta.get("valid_until"))
    if valid_until is None:
        reasons.append("valid_until missing or invalid")
    elif valid_until < datetime.now(timezone.utc):
        reasons.append("valid_until expired")

    recorded_sources = {}
    sources = snapshot.get("sources", {}) if isinstance(snapshot.get("sources"), dict) else {}
    fingerprints = sources.get("fingerprints", []) if isinstance(sources, dict) else []
    if isinstance(fingerprints, list):
        for item in fingerprints:
            if isinstance(item, dict) and "id" in item:
                recorded_sources[str(item["id"])] = str(item.get("checksum", "missing"))
    current_sources = collect_project_snapshot_sources(project_root)
    current_by_id = {str(item["id"]): str(item.get("checksum", "missing")) for item in current_sources}
    for source_id, checksum in current_by_id.items():
        if source_id not in recorded_sources:
            reasons.append(f"source added: {source_id}")
        elif recorded_sources[source_id] != checksum:
            reasons.append(f"source changed: {source_id}")
    for source_id in sorted(set(recorded_sources) - set(current_by_id)):
        reasons.append(f"source removed: {source_id}")

    current = build_project_context_snapshot(project_root)
    required = current.get("capabilities", {}).get("required", []) if isinstance(current.get("capabilities"), dict) else []
    for item in required:
        if isinstance(item, dict) and item.get("status") == "missing":
            reasons.append(f"required capability missing: {item.get('id')}")
    return ("fresh" if not reasons else "stale"), reasons, snapshot


def write_project_context_snapshot_outputs(project_root: Path) -> tuple[str, dict[str, Path], dict[str, Any], list[str]]:
    snapshot = build_project_context_snapshot(project_root)
    status, reasons, _previous = project_context_freshness(project_root)
    if status == "missing":
        reasons = []
    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    snapshot_yaml.parent.mkdir(parents=True, exist_ok=True)
    snapshot_yaml.write_text(ensure_trailing_newline(dump_yaml(snapshot)), encoding="utf-8")
    snapshot_md.write_text(render_project_context_snapshot_md(snapshot, "fresh", []), encoding="utf-8")
    workplace_snapshot = write_workplace_context_snapshot(project_root, snapshot)
    return "fresh", {"snapshot_yaml": snapshot_yaml, "snapshot_md": snapshot_md, "workplace_snapshot": workplace_snapshot}, snapshot, reasons


def telemetry_session_id(prefix: str = "session") -> str:
    stamp = now_utc().replace("-", "").replace(":", "").replace("Z", "z")
    return f"{prefix}-{stamp}"


def redact_telemetry_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_telemetry_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_telemetry_value(item) for item in value]
    if isinstance(value, str) and contains_secret_value(value):
        return "<redacted>"
    return value


def append_telemetry_event(telemetry_path: Path, event: str, **payload: Any) -> None:
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    item = {"ts": now_utc(), "event": event}
    item.update(redact_telemetry_value(payload))
    with telemetry_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def event_runtime_paths(project_root: Path) -> tuple[Path, Path]:
    runtime = locate_flow_root(project_root) / "runtime" / "events"
    return runtime / "events.ndjson", locate_flow_root(project_root) / "runtime" / "hooks" / "outbox"


def hook_config_path(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "hooks.yaml"


def hook_results_root(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "runtime" / "hooks" / "results"


def validate_hooks_config(project_root: Path) -> list[Check]:
    path = hook_config_path(project_root)
    checks: list[Check] = []
    if not path.is_file():
        return [check("FAIL", f"{rel(path, project_root)} missing")]
    data = load_yaml_document(path)
    error = yaml_error(data)
    if error:
        return [check("FAIL", f"{rel(path, project_root)} is invalid YAML: {error}")]
    hooks_config = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks_config, dict):
        return [check("FAIL", f"{rel(path, project_root)} missing hooks object")]
    targets = hooks_config.get("targets")
    if not isinstance(targets, list):
        checks.append(check("FAIL", f"{rel(path, project_root)} hooks.targets must be a list"))
        return checks
    checks.append(check("PASS", f"{rel(path, project_root)} is valid YAML"))
    checks.append(check("PASS", f"{rel(path, project_root)} hooks.targets is a list"))
    for index, target in enumerate(targets):
        label = f"hooks.targets[{index}]"
        if not isinstance(target, dict):
            checks.append(check("FAIL", f"{label} must be an object"))
            continue
        for key in ["id", "type", "enabled", "event_types"]:
            checks.append(check("PASS" if key in target else "FAIL", f"{label}.{key} present"))
        event_types = target.get("event_types")
        if isinstance(event_types, list) and all(isinstance(item, str) and item for item in event_types):
            checks.append(check("PASS", f"{label}.event_types is a string list"))
        else:
            checks.append(check("FAIL", f"{label}.event_types must be a string list; quote wildcard as \"*\""))
    return checks


def resolve_runtime_config_path(project_root: Path, value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == PROJECT_FLOW_ROOT:
        return project_root / path
    return locate_flow_root(project_root) / path


def project_id(project_root: Path) -> str:
    manifest = locate_flow_root(project_root) / "process-forge.yaml"
    data = load_yaml_document(manifest)
    project = data.get("project") if isinstance(data, dict) else None
    if isinstance(project, dict) and project.get("id"):
        return str(project["id"])
    return safe_id(project_root.name, "project")


def processforge_event(
    project_root: Path,
    event_type: str,
    *,
    severity: str = "info",
    session_id: str | None = None,
    assignment_id_value: str | None = None,
    assignment_path: str | None = None,
    process_id: str | None = None,
    process_version: str | None = None,
    stage: str | None = None,
    subject: str | None = None,
    payload: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    privacy: str = "private",
    correlation_id: str | None = None,
    causation_id: str | None = None,
    actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    correlation = correlation_id or session_id or f"corr-{uuid.uuid4().hex[:12]}"
    event_id = f"evt_{uuid.uuid4().hex}"
    clean_data = redact_telemetry_value(data if data is not None else (payload or {}))
    actor_data = actor or {"type": "agent", "id": "processforge-cli", "role": "orchestrator"}
    event_subject = subject or assignment_path or assignment_id_value or session_id or event_type
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "source": "processforge.cli",
        "subject": event_subject,
        "time": now_utc(),
        "correlation_id": correlation,
        "causation_id": causation_id,
        "project": {"flow_root": flow_label(project_root), "project_id": project_id(project_root)},
        "process": {"id": process_id, "version": process_version, "stage_id": stage, "process_run_id": None},
        "assignment": {"id": assignment_id_value, "path": assignment_path},
        "actor": actor_data,
        "session": {"id": session_id},
        "data": clean_data,
        "severity": severity,
        "privacy": privacy,
    }


def event_id_value(event: dict[str, Any]) -> str:
    return str(event.get("event_id") or event.get("id") or f"evt_{uuid.uuid4().hex}")


def event_type_name(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or event.get("type") or "")


def event_matches_hook(event: dict[str, Any], hook: dict[str, Any]) -> bool:
    event_types = hook.get("event_types", ["*"])
    if not isinstance(event_types, list):
        return False
    return "*" in event_types or event_type_name(event) in event_types


def hook_targets(project_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = load_yaml_document(hook_config_path(project_root))
    hooks_config = config.get("hooks") if isinstance(config, dict) else None
    if isinstance(hooks_config, dict):
        targets = hooks_config.get("targets", [])
        return hooks_config, targets if isinstance(targets, list) else []
    if isinstance(hooks_config, list):
        return {"mode": config.get("dispatch", {}).get("default_mode", "outbox") if isinstance(config.get("dispatch"), dict) else "outbox"}, hooks_config
    return {"mode": "outbox"}, []


def selected_hooks(project_root: Path, event: dict[str, Any]) -> list[dict[str, Any]]:
    _hooks_config, hooks = hook_targets(project_root)
    selected: list[dict[str, Any]] = []
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        if not hook.get("enabled", False):
            continue
        if event_matches_hook(event, hook):
            selected.append(hook)
    return selected


def hook_delivery_payload(event: dict[str, Any], target: dict[str, Any], mode: str, delivery_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "delivery_id": delivery_id,
        "delivery_time": now_utc(),
        "target_id": str(target.get("id", "hook")),
        "mode": mode,
        "event": event,
    }


def wtaicc_outbox_payload(event: dict[str, Any], *, chat: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": "wtaicc",
        "delivery_mode": "outbox",
        "created_at": now_utc(),
        "event": event,
        "chat": chat or {"included": False, "mode": "metadata_only", "messages": []},
    }


def write_hook_result(project_root: Path, result: dict[str, Any]) -> Path:
    results_root = hook_results_root(project_root)
    results_root.mkdir(parents=True, exist_ok=True)
    target = results_root / f"{result['delivery_id']}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def dispatch_hooks(project_root: Path, event: dict[str, Any], *, dry_run: bool = False, outbox: bool = True) -> list[dict[str, Any]]:
    hooks_config, _all_hooks = hook_targets(project_root)
    hooks = selected_hooks(project_root, event)
    actions: list[dict[str, Any]] = []
    for hook in hooks:
        hook_id = safe_id(str(hook.get("id", "hook")), "hook")
        hook_type = str(hook.get("type", "outbox"))
        delivery_id = f"del_{uuid.uuid4().hex}"
        action: dict[str, Any] = {"hook": hook_id, "target_id": hook_id, "type": hook_type, "delivery_id": delivery_id}
        if dry_run:
            action["status"] = "dry_run"
            action["mode"] = "dry_run"
        elif hook_type in {"outbox", "file_outbox", "webhook", "webhook_future"} and outbox:
            default_outbox = locate_flow_root(project_root) / "runtime" / "hooks" / "outbox"
            target_root = resolve_runtime_config_path(project_root, str(hook.get("path") or hook.get("outbox") or ""), default_outbox)
            if hook_id.startswith("wtaicc") and target_root.name != "wtaicc":
                target_root = target_root / "wtaicc"
            target_root.mkdir(parents=True, exist_ok=True)
            delivery = hook_delivery_payload(event, hook, "outbox", delivery_id)
            payload = wtaicc_outbox_payload(event) if hook_id.startswith("wtaicc") else delivery
            target = target_root / f"{event_id_value(event)}.{hook_id}.json"
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            action["status"] = "outbox_written"
            action["outbox"] = rel(target, project_root)
            result = {
                "schema_version": 1,
                "delivery_id": delivery_id,
                "target_id": hook_id,
                "status": "written",
                "exit_code": 0,
                "blocking": False,
                "message": "Outbox payload written",
                "outbox": rel(target, project_root),
            }
            action["result"] = rel(write_hook_result(project_root, result), project_root)
        elif hook_type == "command":
            action["status"] = "skipped"
            action["reason"] = "command hooks require an explicit future runner/executor"
            result = {
                "schema_version": 1,
                "delivery_id": delivery_id,
                "target_id": hook_id,
                "status": "skipped",
                "exit_code": 0,
                "blocking": bool(hook.get("blocking", False)),
                "message": action["reason"],
            }
            action["result"] = rel(write_hook_result(project_root, result), project_root)
        elif hook_type == "webhook" and not hooks_config.get("network_send_enabled", False):
            action["status"] = "skipped"
            action["reason"] = "network send is disabled by default"
        else:
            action["status"] = "skipped"
            action["reason"] = f"unsupported hook type: {hook_type}"
        actions.append(action)
    return actions


def append_process_event(project_root: Path, event: dict[str, Any], *, dispatch: bool = True) -> Path:
    events_path, _outbox = event_runtime_paths(project_root)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    if dispatch:
        dispatch_hooks(project_root, event, dry_run=False, outbox=True)
    return events_path


def emit_process_event(project_root: Path, event_type: str, **kwargs: Any) -> dict[str, Any]:
    event = processforge_event(project_root, event_type, **kwargs)
    append_process_event(project_root, event)
    return event


EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")


def validate_event_object(event: Any, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, dict):
        return [f"{label}: event is not an object"]
    for key in ["schema_version", "event_id", "event_type", "source", "subject", "time", "correlation_id", "project", "data"]:
        if key not in event:
            errors.append(f"{label}: missing {key}")
    event_type = event.get("event_type")
    if not isinstance(event_type, str) or not EVENT_TYPE_PATTERN.fullmatch(event_type):
        errors.append(f"{label}: invalid event_type")
    serialized = json.dumps(event, ensure_ascii=False)
    if contains_secret_value(serialized):
        errors.append(f"{label}: secret-like value found")
    return errors


def validate_chat_message_object(message: Any, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(message, dict):
        return [f"{label}: chat message is not an object"]
    for key in ["schema_version", "message_id", "session_id", "turn_id", "timestamp", "participant", "message", "source"]:
        if key not in message:
            errors.append(f"{label}: missing {key}")
    body = message.get("message") if isinstance(message.get("message"), dict) else {}
    if "content_hash" not in body:
        errors.append(f"{label}: missing message.content_hash")
    serialized = json.dumps(message, ensure_ascii=False)
    if contains_secret_value(serialized):
        errors.append(f"{label}: secret-like value found")
    return errors


def iter_ndjson(path: Path) -> list[tuple[int, Any, str | None]]:
    rows: list[tuple[int, Any, str | None]] = []
    if not path.is_file():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append((line_number, json.loads(line), None))
        except json.JSONDecodeError as exc:
            rows.append((line_number, None, str(exc)))
    return rows


def chat_transcript_path(project_root: Path, session_id: str) -> Path:
    return locate_flow_root(project_root) / "runtime" / "chat" / "transcripts" / f"{safe_id(session_id, 'session')}.ndjson"


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_chat_content(content: str, max_chars: int = 20000) -> tuple[str, str]:
    redacted = content
    redaction = "none"
    for pattern in SECRET_VALUE_PATTERNS:
        redacted, count = pattern.subn("<redacted>", redacted)
        if count:
            redaction = "redacted"
    if len(redacted) > max_chars:
        redacted = redacted[:max_chars]
        redaction = "truncated" if redaction == "none" else "redacted_truncated"
    return redacted, redaction


def chat_participant(participant_id: str, role: str, participant_type: str | None = None) -> dict[str, Any]:
    inferred_type = participant_type or ("human" if participant_id in {"operator", "user"} else ("subagent" if participant_id.startswith("subagent") else "agent"))
    return {"id": participant_id, "type": inferred_type, "role": role}


def append_chat_message(
    project_root: Path,
    *,
    session_id: str,
    participant_id: str,
    participant_role: str,
    message_role: str,
    content: str,
    participant_type: str | None = None,
    turn_id: str | None = None,
    parent_message_id: str | None = None,
    source_kind: str = "manual_capture",
    process_id: str | None = None,
    stage_id: str | None = None,
    assignment_id_value: str | None = None,
    include_event_content: bool = False,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    transcript = chat_transcript_path(project_root, session_id)
    transcript.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines() if transcript.is_file() else []
    line_number = len([line for line in existing_lines if line.strip()]) + 1
    redacted_content, redaction = redact_chat_content(content)
    message_id = f"msg_{uuid.uuid4().hex}"
    record = {
        "schema_version": 1,
        "message_id": message_id,
        "session_id": session_id,
        "turn_id": turn_id or f"turn_{line_number}",
        "parent_message_id": parent_message_id,
        "timestamp": now_utc(),
        "participant": chat_participant(participant_id, participant_role, participant_type),
        "message": {
            "role": message_role,
            "content_type": "text/markdown",
            "content": redacted_content,
            "content_hash": sha256_text(redacted_content),
            "redaction": redaction,
        },
        "source": {"kind": source_kind, "hook_event": None, "transcript_path": rel(transcript, project_root)},
        "process": {"id": process_id, "stage_id": stage_id},
        "assignment": {"id": assignment_id_value},
    }
    with transcript.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    content_ref = {"path": rel(transcript, project_root), "line": line_number, "message_id": message_id}
    event_data: dict[str, Any] = {
        "session_id": session_id,
        "message_id": message_id,
        "participant": record["participant"],
        "message": {
            "role": message_role,
            "content_hash": record["message"]["content_hash"],
            "redaction": redaction,
            "content_ref": content_ref,
        },
    }
    if include_event_content:
        event_data["message"]["content"] = redacted_content
        event_data["message"]["content_mode"] = "full" if redaction == "none" else redaction
    else:
        event_data["message"]["content_mode"] = "metadata_only"
    event = emit_process_event(
        project_root,
        "chat.message.recorded",
        session_id=session_id,
        assignment_id_value=assignment_id_value,
        process_id=process_id,
        stage=stage_id,
        subject=f"chat/{session_id}/{message_id}",
        data=event_data,
        privacy="private",
        correlation_id=session_id,
    )
    return transcript, record, event


def load_chat_messages(project_root: Path, session_id: str) -> list[dict[str, Any]]:
    transcript = chat_transcript_path(project_root, session_id)
    messages: list[dict[str, Any]] = []
    for _line_number, data, error in iter_ndjson(transcript):
        if error is None and isinstance(data, dict):
            messages.append(data)
    return messages


def chat_export_messages(messages: list[dict[str, Any]], *, include_content: bool) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for item in messages:
        body = item.get("message") if isinstance(item.get("message"), dict) else {}
        exported_item = {
            "message_id": item.get("message_id"),
            "session_id": item.get("session_id"),
            "turn_id": item.get("turn_id"),
            "timestamp": item.get("timestamp"),
            "participant": item.get("participant"),
            "message": {
                "role": body.get("role"),
                "content_hash": body.get("content_hash"),
                "redaction": body.get("redaction", "none"),
            },
        }
        if include_content:
            exported_item["message"]["content"] = body.get("content", "")
            exported_item["message"]["content_mode"] = "full" if body.get("redaction") == "none" else body.get("redaction", "redacted")
        else:
            exported_item["message"]["content_mode"] = "metadata_only"
        exported.append(exported_item)
    return exported


def write_workplace_context_snapshot(project_root: Path, snapshot: dict[str, Any]) -> Path:
    cache = locate_flow_root(project_root) / "runtime" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    local_config = locate_flow_root(project_root) / "process-forge.local.yaml"
    payload = {
        "schema_version": 1,
        "snapshot": {
            "id": "workplace-context",
            "generated_at": now_utc(),
            "privacy": "private",
        },
        "project": {"id": project_id(project_root)},
        "flow": {
            "root": flow_label(project_root),
            "manifest": rel(locate_flow_root(project_root) / "process-forge.yaml", project_root),
            "local_config": rel(local_config, project_root),
            "local_config_exists": local_config.is_file(),
        },
        "capabilities": snapshot.get("capabilities", {}),
        "tools": snapshot.get("tools", {}),
        "mcp": snapshot.get("mcp", {}),
        "notes": ["Private runtime snapshot may include local availability state."],
    }
    target = cache / "workplace-context.snapshot.yaml"
    target.write_text(ensure_trailing_newline(dump_yaml(payload)), encoding="utf-8")
    return target


def session_runtime_paths(project_root: Path, session_id: str) -> tuple[Path, Path]:
    runtime = locate_flow_root(project_root) / "runtime"
    return runtime / "sessions" / f"{session_id}.yaml", runtime / "telemetry" / f"{session_id}.ndjson"


def write_session_metadata(project_root: Path, session_id: str, mode: str, snapshot_status: str, telemetry_path: Path) -> Path:
    session_path, _events_path = session_runtime_paths(project_root, session_id)
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    payload = {
        "schema_version": 1,
        "session": {
            "id": session_id,
            "mode": mode,
            "actor_type": "human_started_agent",
            "role": "orchestrator",
            "started_at": now_utc(),
        },
        "context": {
            "project_flow_root": flow_label(project_root),
            "snapshot": rel(snapshot_yaml, project_root),
            "snapshot_status": snapshot_status,
        },
        "telemetry": {"events": rel(telemetry_path, project_root)},
    }
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(ensure_trailing_newline(dump_yaml(payload)), encoding="utf-8")
    return session_path


def collect_action_rules(texts: dict[str, str]) -> tuple[list[str], list[str]]:
    allowed = {"read_required_sources"}
    forbidden = {"edit_forbidden_files", "rebuild_context_without_approval"}
    for text in texts.values():
        allowed.update(yaml_list_values(text, "allowed_actions"))
        forbidden.update(yaml_list_values(text, "forbidden_actions"))
    return sorted(allowed), sorted(forbidden)


def build_context_payload(project_root: Path, assignment: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    flow_root = locate_flow_root(project_root)
    sources = collect_context_sources(project_root, assignment)
    fingerprints = source_fingerprints(sources)
    texts = source_texts(project_root, sources)
    capabilities = resolve_capabilities(texts, project_root)
    allowed_actions, forbidden_actions = collect_action_rules(texts)

    conflicts: list[dict[str, str]] = []
    for item in sources:
        if item.get("required") and not item.get("exists"):
            conflicts.append({"status": "blocked", "message": f"required source missing: {item['path']}", "source": str(item["path"])})
    manifest_rel = rel(flow_root / "process-forge.yaml", project_root)
    manifest_text = texts.get(manifest_rel, "")
    if manifest_text:
        if not is_public_path_safe(manifest_text):
            conflicts.append({"status": "blocked", "message": "public manifest contains a local absolute path", "source": manifest_rel})
        if contains_secret_value(manifest_text):
            conflicts.append({"status": "blocked", "message": "public manifest contains a secret-like value", "source": manifest_rel})
    for capability in capabilities["missing_required"]:
        conflicts.append({"status": "blocked", "message": f"required capability is unresolved: {capability}", "source": "capabilities"})
    for capability in capabilities["missing_optional"]:
        conflicts.append({"status": "warn", "message": f"optional capability is unresolved: {capability}", "source": "capabilities"})

    overlap = sorted(set(allowed_actions).intersection(forbidden_actions))
    for action in overlap:
        conflicts.append({"status": "blocked", "message": f"action is both allowed and forbidden: {action}", "source": "resolved-rules"})

    gitignore = project_root / ".gitignore"
    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        if ".pf/runtime/" not in ignore_text:
            conflicts.append({"status": "warn", "message": "runtime cache path is not ignored", "source": ".gitignore"})
    if assignment is None:
        conflicts.append({"status": "warn", "message": "broad project context includes available sources that workers should not load by default", "source": "context-index"})

    if any(item["status"] == "blocked" for item in conflicts):
        status = "blocked"
    elif any(item["status"] == "requires_approval" for item in conflicts):
        status = "requires_approval"
    elif any(item["status"] == "warn" for item in conflicts):
        status = "warn"
    else:
        status = "resolved"

    selected_processes = [Path(str(item["path"])).stem for item in sources if item["kind"] == "process" and item["exists"]]
    selected_packages = [Path(str(item["path"])).stem for item in sources if item["kind"] == "package" and item["exists"]]
    selected_templates = [Path(str(item["path"])).name for item in sources if item["kind"] == "template" and item["exists"]]
    template_records = [
        {
            "id": safe_id(Path(str(item["path"])).stem, "template"),
            "path": str(item["path"]),
            "source": "project",
            "status": "selected" if item.get("load_policy") != "available" else "available",
        }
        for item in sources
        if item["kind"] == "template" and item["exists"]
    ]

    index = {
        "schema_version": 1,
        "context": {
            "id": "context-index",
            "generated_at": now_utc(),
            "mode": "context_resolve",
            "project_flow": manifest_rel,
        },
        "sources": sources,
        "selected_processes": selected_processes,
        "selected_packages": selected_packages,
        "selected_templates": selected_templates,
        "capabilities": capabilities,
        "fingerprints": fingerprints,
        "freshness": {"status": "fresh", "stale_sources": []},
    }
    resolved = {
        "schema_version": 1,
        "rules": {
            "hard": [
                {"id": "public-files-no-local-paths", "source": "process-forge.yaml"},
                {"id": "no-secret-values-in-generated-files", "source": "process-forge.yaml"},
            ],
            "locked": [{"id": "locked-hard-policies-cannot-be-weakened", "source": "process-forge.yaml"}],
            "preferences": [],
            "gates": [{"id": "blocked-conflicts-stop-context-compile", "source": "context-resolution"}],
            "tools": [{"id": "processforge-cli", "source": "tools/processforge.py"}],
            "templates": template_records,
        },
        "allowed_actions": allowed_actions,
        "forbidden_actions": forbidden_actions,
        "merge": {
            "order": [
                "core",
                "workplace",
                "organization",
                "direction",
                "specialization",
                "platform",
                "toolchain",
                "project",
                "process",
                "stage",
                "task",
                "agent_profile",
            ],
            "conflict_policy": "block_on_locked_policy_conflict",
        },
        "source_fingerprints": fingerprints,
    }
    report = render_conflict_report(status, conflicts, fingerprints)
    return index, resolved, report, status


def render_conflict_report(status: str, conflicts: list[dict[str, str]], fingerprints: dict[str, str]) -> str:
    blocking = [item for item in conflicts if item["status"] == "blocked"]
    warnings = [item for item in conflicts if item["status"] == "warn"]
    approvals = [item for item in conflicts if item["status"] == "requires_approval"]
    resolved = [item for item in conflicts if item["status"] == "resolved"]

    def lines(items: list[dict[str, str]]) -> list[str]:
        return [f"- {item['message']} ({item.get('source', 'unknown')})" for item in items] or ["- None."]

    output: list[str] = [
        "schema_version: 1",
        f"status: {status}",
        f"blocking_conflicts: {len(blocking)}",
        f"warnings: {len(warnings)}",
        f"requires_approval: {len(approvals)}",
        "",
        "# Context Conflict Report",
        "",
        "## Blocking Conflicts",
        "",
        *lines(blocking),
        "",
        "## Warnings",
        "",
        *lines(warnings),
        "",
        "## Requires Approval",
        "",
        *lines(approvals),
        "",
        "## Resolved",
        "",
        *lines(resolved),
        "",
        "## Source Fingerprints",
        "",
    ]
    output.extend(f"- {path}: {fingerprint}" for path, fingerprint in fingerprints.items())
    return "\n".join(output) + "\n"


def write_context_outputs(project_root: Path, assignment: Path | None = None) -> tuple[str, dict[str, Path]]:
    index, resolved, report, status = build_context_payload(project_root, assignment)
    flow_root = locate_flow_root(project_root)
    contexts = flow_root / "contexts"
    cache = flow_root / "runtime" / "cache"
    contexts.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    paths = {
        "context_index": contexts / "context-index.yaml",
        "resolved_rules": contexts / "resolved-rules.yaml",
        "conflict_report": contexts / "context-conflict-report.md",
        "context_cache": cache / "context-cache.yaml",
    }
    paths["context_index"].write_text(ensure_trailing_newline(dump_yaml(index)), encoding="utf-8")
    paths["resolved_rules"].write_text(ensure_trailing_newline(dump_yaml(resolved)), encoding="utf-8")
    paths["conflict_report"].write_text(report, encoding="utf-8")
    cache_payload = {
        "schema_version": 1,
        "cache": {"id": "context-cache", "generated_at": now_utc(), "status": "fresh" if status != "blocked" else "stale"},
        "fingerprints": index["fingerprints"],
        "sources": index["sources"],
        "health": {"conflict_status": status},
    }
    paths["context_cache"].write_text(ensure_trailing_newline(dump_yaml(cache_payload)), encoding="utf-8")
    return status, paths


def context_report_status(path: Path) -> str:
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?m)^status" + COLON_WS + r"([a-z_]+)\s*$", text)
    return match.group(1) if match else "missing"


def context_freshness(project_root: Path) -> tuple[str, list[str]]:
    index_path = locate_flow_root(project_root) / "contexts" / "context-index.yaml"
    if not index_path.is_file():
        return "missing", []
    text = index_path.read_text(encoding="utf-8", errors="replace")
    current_sources = collect_context_sources(project_root)
    stale: list[str] = []
    for item in current_sources:
        path = str(item["path"])
        fingerprint = str(item.get("fingerprint", "missing"))
        if path not in text or fingerprint not in text:
            stale.append(path)
    return ("fresh" if not stale else "stale"), stale


def assignment_id(path: Path) -> str:
    return safe_id(path.stem, "assignment")


def conflict_metric(report: str, key: str) -> int:
    match = re.search(rf"(?m)^{re.escape(key)}" + COLON_WS + r"(\d+)\s*$", report)
    return int(match.group(1)) if match else 0


def normalized_context_status(status: str) -> str:
    return "pass" if status == "resolved" else status


def unique_context_path(contexts: Path, assn_id: str, suffix: str) -> Path:
    stamp = now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    return contexts / f"{assn_id}.{stamp}.{suffix}"


def ecp_checksum(payload: dict[str, Any]) -> str:
    stable = dict(payload)
    stable["checksum"] = "pending"
    return hashlib.sha256(ensure_trailing_newline(dump_yaml(stable)).encode("utf-8")).hexdigest()


def compile_execution_context(
    project_root: Path,
    assignment: Path,
    *,
    write_capsule: bool = False,
    supersede: bool = False,
    allow_requires_approval: bool = False,
) -> tuple[Path, Path | None, Path]:
    if not assignment.is_file():
        raise SystemExit(f"FAIL: assignment not found: {assignment}")

    index, resolved, report, status = build_context_payload(project_root, assignment)
    assn_id = assignment_id(assignment)
    flow_root = locate_flow_root(project_root)
    contexts = flow_root / "contexts"
    contexts.mkdir(parents=True, exist_ok=True)
    assignment_conflict_report = contexts / f"{assn_id}.conflicts.md"
    assignment_conflict_report.write_text(report, encoding="utf-8")

    if status == "blocked":
        raise SystemExit(f"FAIL: assignment context has blocking conflicts: {rel(assignment_conflict_report, project_root)}")
    if status == "requires_approval" and not allow_requires_approval:
        raise SystemExit(f"FAIL: assignment context requires approval: {rel(assignment_conflict_report, project_root)}")

    ecp_path = contexts / f"{assn_id}.ecp.yaml"
    supersedes: str | None = None
    if ecp_path.exists():
        if not supersede:
            raise SystemExit(f"FAIL: ECP already exists: {rel(ecp_path, project_root)}")
        supersedes = rel(ecp_path, project_root)
        ecp_path = unique_context_path(contexts, assn_id, "ecp.yaml")
    capsule_path: Path | None = contexts / f"{assn_id}.capsule.yaml" if write_capsule else None
    if capsule_path and capsule_path.exists():
        if not supersede:
            raise SystemExit(f"FAIL: capsule already exists: {rel(capsule_path, project_root)}")
        capsule_path = unique_context_path(contexts, assn_id, "capsule.yaml")

    sources = [
        {
            "path": item["path"],
            "checksum": item.get("checksum", "missing"),
            "kind": item.get("kind", "source"),
            "selection_reason": item.get("selection_reason", ""),
            "load_policy": item.get("load_policy", ""),
        }
        for item in index["sources"]
        if item.get("required") or item.get("load_policy") == "read_required"
    ]
    source_fingerprints = [{"path": item["path"], "checksum": item.get("checksum", "missing")} for item in sources]
    context_status = normalized_context_status(status)
    ecp = {
        "schema_version": 1,
        "id": f"{assn_id}-context",
        "type": "execution_context_package",
        "assignment": assn_id,
        "assignment_path": rel(assignment, project_root),
        "process": "assignment-execute",
        "stage": "assignment_execute",
        "role": "worker",
        "context_status": context_status,
        "blocking_conflicts": conflict_metric(report, "blocking_conflicts"),
        "warnings": conflict_metric(report, "warnings"),
        "requires_approval": conflict_metric(report, "requires_approval"),
        "conflict_report": rel(assignment_conflict_report, project_root),
        "source_fingerprints": source_fingerprints,
        "read_sources": [str(item["path"]) for item in sources],
        "resolved_rules": {
            "allowed_actions": resolved["allowed_actions"],
            "forbidden_actions": resolved["forbidden_actions"],
            "merge": resolved["merge"],
        },
        "allowed_files": [rel(assignment, project_root)],
        "forbidden_files": [],
        "required_outputs": [],
        "required_capabilities": index["capabilities"].get("required", []),
        "selected_tools": ["processforge-cli"],
        "selected_mcp": [],
        "selected_templates": resolved["rules"].get("templates", []),
        "created_at": now_utc(),
        "checksum": "pending",
        "context": {
            "id": f"{assn_id}-context",
            "created_at": now_utc(),
            "immutable": True,
            "context_index": rel(contexts / "context-index.yaml", project_root),
            "conflict_report": rel(assignment_conflict_report, project_root),
        },
        "task_input": [rel(assignment, project_root)],
        "sources": sources,
        "packages": [{"id": item, "status": "available"} for item in index.get("selected_packages", [])],
        "templates": resolved["rules"].get("templates", []),
        "allowed_actions": resolved["allowed_actions"],
        "forbidden_actions": resolved["forbidden_actions"],
        "quality_gates": ["doctor-context"],
        "checksums": {"assignment": sha256_file(assignment), "context_index": sha256_file(contexts / "context-index.yaml")},
    }
    if supersedes:
        ecp["supersedes"] = supersedes
    ecp["checksum"] = ecp_checksum(ecp)
    ecp_path.write_text(ensure_trailing_newline(dump_yaml(ecp)), encoding="utf-8")

    if write_capsule:
        assert capsule_path is not None
        capsule = {
            "schema_version": 1,
            "capsule": {
                "id": f"{assn_id}-capsule",
                "ecp": rel(ecp_path, project_root),
                "worker_may_rebuild_context": False,
            },
            "assignment": {"id": assn_id, "path": rel(assignment, project_root)},
            "context": {
                "freshness": context_freshness(project_root)[0],
                "conflict_status": status,
                "context_status": context_status,
                "conflict_report": rel(assignment_conflict_report, project_root),
            },
            "required_sources": [str(item["path"]) for item in sources],
            "allowed_files": [rel(assignment, project_root)],
            "forbidden_files": [],
            "allowed_actions": resolved["allowed_actions"],
            "forbidden_actions": resolved["forbidden_actions"],
        }
        capsule_path.write_text(ensure_trailing_newline(dump_yaml(capsule)), encoding="utf-8")
    return ecp_path, capsule_path, assignment_conflict_report


def recent_files(root: Path, dirname: str, limit: int = 5, *, rel_root: Path | None = None) -> list[str]:
    directory = root / dirname
    if not directory.is_dir():
        return []
    files = sorted((path for path in directory.rglob("*") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    return [rel(path, rel_root or root) for path in files[:limit]]


def render_session_status(project_root: Path, mode: str) -> str:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    manifest_text = manifest.read_text(encoding="utf-8", errors="replace") if manifest.is_file() else ""
    name_match = re.search(r"(?m)^\s*name" + COLON_WS + r"(.+?)\s*$", manifest_text)
    version_match = re.search(r"(?m)^\s*version" + COLON_WS + r"(.+?)\s*$", manifest_text)
    project_name = name_match.group(1).strip() if name_match else project_root.name
    flow_version = version_match.group(1).strip() if version_match else "unknown"
    snapshot_freshness, snapshot_stale, _snapshot = project_context_freshness(project_root)
    legacy_freshness, legacy_stale = context_freshness(project_root)
    freshness = snapshot_freshness if snapshot_freshness != "missing" else legacy_freshness
    stale = snapshot_stale if snapshot_freshness != "missing" else legacy_stale
    conflict_status = context_report_status(flow_root / "contexts" / "context-conflict-report.md")
    assignments = recent_files(flow_root, "assignments", rel_root=project_root)
    artifacts = recent_files(flow_root, "artifacts", rel_root=project_root)
    reviews = recent_files(flow_root, "reviews", rel_root=project_root)
    adrs = recent_files(flow_root, "adr", rel_root=project_root)

    def markdown_items(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- None."

    blocked = []
    if conflict_status == "blocked":
        blocked.append("Context conflict report is blocked.")
    if freshness in {"missing", "stale"}:
        blocked.append(f"Context freshness is {freshness}.")

    return "\n".join(
        [
            "# ProcessForge Session Status",
            "",
            "## Project",
            "",
            project_name,
            "",
            "## Flow Version",
            "",
            flow_version,
            "",
            "## Project Flow Root",
            "",
            flow_label(project_root),
            "",
            "## Session Mode",
            "",
            mode,
            "",
            "## Context Freshness",
            "",
            freshness + (f": {', '.join(stale)}" if stale else ""),
            "",
            "## Completed Work",
            "",
            markdown_items(artifacts),
            "",
            "## Current Active Assignments",
            "",
            markdown_items(assignments),
            "",
            "## Blocked Items",
            "",
            markdown_items(blocked),
            "",
            "## Latest Reviews",
            "",
            markdown_items(reviews),
            "",
            "## Important ADR",
            "",
            markdown_items(adrs),
            "",
            "## Risks",
            "",
            "- Project context snapshot is the preferred operational map; context cache is only an accelerator.",
            "",
            "## Recommended Next Steps",
            "",
            "- Run project-context-refresh if the snapshot is stale or missing.",
            "- Run assignment-capsule before starting assignment workers.",
            "",
            "## Suggested Assignments",
            "",
            "- None.",
            "",
        ]
    )


def command_session_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    require_flow_root(project_root)
    session_id = telemetry_session_id()
    session_path, telemetry_path = session_runtime_paths(project_root, session_id)
    freshness, stale_reasons, snapshot = project_context_freshness(project_root)
    if args.rebuild_context_if_stale and freshness in {"missing", "stale"}:
        status, paths, snapshot, _old_reasons = write_project_context_snapshot_outputs(project_root)
        freshness = status
        stale_reasons = []
        print(f"PROJECT_CONTEXT: {status}")
        for path in paths.values():
            print(f"WROTE: {rel(path, project_root)}")
    write_session_metadata(project_root, session_id, args.mode, freshness, telemetry_path)
    emit_process_event(
        project_root,
        "session.started",
        session_id=session_id,
        payload={"mode": args.mode, "snapshot_status": freshness},
        correlation_id=session_id,
    )
    append_telemetry_event(telemetry_path, "session_start", mode=args.mode, actor="agent", session=session_id)
    append_telemetry_event(
        telemetry_path,
        "snapshot_check",
        path=rel(project_context_snapshot_paths(project_root)[0], project_root),
        status=freshness,
        reasons=stale_reasons,
    )
    if freshness == "stale":
        emit_process_event(
            project_root,
            "context.snapshot.stale",
            severity="warn",
            session_id=session_id,
            payload={"reasons": stale_reasons},
            correlation_id=session_id,
        )
    flow_root = locate_flow_root(project_root)
    read_order = [
        flow_root / "AGENTS.md",
        flow_root / "process-forge.yaml",
        flow_root / "contexts" / "project-context.snapshot.md",
    ]
    for source in read_order:
        append_telemetry_event(telemetry_path, "source_read", path=rel(source, project_root), exists=source.is_file(), reason="session_start")
    assignment_path = Path(args.assignment).expanduser().resolve() if args.assignment else None
    append_telemetry_event(
        telemetry_path,
        "assignment_loaded",
        path=rel(assignment_path, project_root) if assignment_path else None,
        status="loaded" if assignment_path and assignment_path.is_file() else "not_provided",
    )
    if assignment_path:
        emit_process_event(
            project_root,
            "assignment.started",
            session_id=session_id,
            assignment_id_value=assignment_id(assignment_path),
            payload={"path": rel(assignment_path, project_root), "exists": assignment_path.is_file()},
            correlation_id=session_id,
        )
    capabilities = snapshot.get("capabilities", {}) if isinstance(snapshot, dict) else {}
    for capability in capabilities.get("required", []) if isinstance(capabilities, dict) else []:
        if isinstance(capability, dict):
            append_telemetry_event(telemetry_path, "capability_check", required=True, **capability)
    for capability in capabilities.get("optional", []) if isinstance(capabilities, dict) else []:
        if isinstance(capability, dict):
            append_telemetry_event(telemetry_path, "capability_check", required=False, **capability)
    append_telemetry_event(telemetry_path, "tool_selected", tool="processforge-cli", reason="session_start")
    append_telemetry_event(telemetry_path, "tool_invoked", tool="processforge-cli", command="session-start")
    emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"tool": "processforge-cli", "command": "session-start"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "tool_failed", tool=None, status="skipped")
    emit_process_event(project_root, "tool.failed", severity="warn", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "mcp_check", status="skipped", reason="no required MCP declared")
    emit_process_event(project_root, "mcp.invoked", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "fallback_used", status="skipped")
    emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"status": "fallback skipped"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "conflict_detected", status="none")
    append_telemetry_event(telemetry_path, "file_scope_checked", status="ok", flow_root=flow_label(project_root))
    report = render_session_status(project_root, args.mode)
    print(report, end="")
    if args.allow_write and not args.report_only:
        target = flow_root / "artifacts" / "session-status-report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report, encoding="utf-8")
        append_telemetry_event(telemetry_path, "artifact_written", path=rel(target, project_root))
        emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"path": rel(target, project_root)}, correlation_id=session_id)
        print(f"WROTE: {rel(target, project_root)}")
    else:
        append_telemetry_event(telemetry_path, "artifact_written", status="skipped", reason="report_only")
    append_telemetry_event(telemetry_path, "review_requested", status="skipped")
    emit_process_event(project_root, "review.requested", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "handoff_created", status="skipped")
    emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"status": "handoff skipped"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "doctor_run", status="skipped")
    append_telemetry_event(telemetry_path, "session_end", status="completed")
    emit_process_event(project_root, "session.ended", session_id=session_id, payload={"mode": args.mode, "status": "completed"}, correlation_id=session_id)
    print(f"SESSION: {rel(session_path, project_root)}")
    print(f"TELEMETRY: {rel(telemetry_path, project_root)}")
    return 0


def command_project_context_refresh(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    require_flow_root(project_root)
    session_id = telemetry_session_id("project-context-refresh")
    _session_path, telemetry_path = session_runtime_paths(project_root, session_id)
    emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"command": "project-context-refresh"}, correlation_id=session_id)
    status, paths, snapshot, old_reasons = write_project_context_snapshot_outputs(project_root)
    append_telemetry_event(telemetry_path, "session_start", mode="project_context_refresh", actor="agent")
    append_telemetry_event(telemetry_path, "snapshot_check", status="previous_" + ("stale" if old_reasons else "fresh"), reasons=old_reasons)
    for source in snapshot.get("sources", {}).get("fingerprints", []):
        if isinstance(source, dict):
            append_telemetry_event(telemetry_path, "source_read", path=source.get("path"), source_id=source.get("id"), reason="snapshot_fingerprint")
    for group in ("required", "optional"):
        for capability in snapshot.get("capabilities", {}).get(group, []):
            if isinstance(capability, dict):
                append_telemetry_event(telemetry_path, "capability_check", required=group == "required", **capability)
    append_telemetry_event(telemetry_path, "tool_selected", tool="processforge-cli", reason="project_context_refresh")
    append_telemetry_event(telemetry_path, "tool_invoked", tool="processforge-cli", command="project-context-refresh")
    emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"tool": "processforge-cli", "command": "project-context-refresh"}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "mcp_check", status="skipped", reason="no required MCP declared")
    emit_process_event(project_root, "mcp.invoked", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    for path in paths.values():
        append_telemetry_event(telemetry_path, "artifact_written", path=rel(path, project_root))
        emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"path": rel(path, project_root)}, correlation_id=session_id)
    for group, event_type, severity in [
        ("required", "capability.missing", "error"),
        ("optional", "capability.missing", "warn"),
    ]:
        for capability in snapshot.get("capabilities", {}).get(group, []):
            if isinstance(capability, dict) and capability.get("status") == "missing":
                emit_process_event(project_root, event_type, severity=severity, session_id=session_id, payload={"capability": capability.get("id")}, correlation_id=session_id)
    append_telemetry_event(telemetry_path, "session_end", status="completed")
    health = snapshot.get("snapshot", {}).get("health", {}).get("status") if isinstance(snapshot.get("snapshot"), dict) else "pass"
    emit_process_event(
        project_root,
        "context.snapshot.refreshed",
        severity="warn" if health == "warn" else ("error" if health == "blocked" else "info"),
        session_id=session_id,
        payload={"status": status, "health": health, "paths": {key: rel(path, project_root) for key, path in paths.items()}},
        correlation_id=session_id,
    )
    print(f"STATUS: {status}")
    for path in paths.values():
        print(f"WROTE: {rel(path, project_root)}")
    print(f"TELEMETRY: {rel(telemetry_path, project_root)}")
    return 1 if health == "blocked" else 0


def command_project_context_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    require_flow_root(project_root)
    status, reasons, snapshot = project_context_freshness(project_root)
    health = "missing"
    if snapshot:
        health = snapshot.get("snapshot", {}).get("health", {}).get("status", "pass") if isinstance(snapshot.get("snapshot"), dict) else "pass"
    print(f"STATUS: {status}")
    print(f"HEALTH: {health}")
    result = "pass" if status == "fresh" and health in {"pass", "warn"} else "fail"
    print(f"RESULT: {result}")
    for reason in reasons:
        print(f"STALE: {reason}")
    return 0 if result == "pass" else 1


def extract_assignment_front_matter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"FAIL: assignment not found: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return load_yaml_document(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return {}
    front_matter = match.group(1).strip()
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(front_matter)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(front_matter)


def command_assignment_capsule(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    assignment = Path(args.assignment).expanduser().resolve()
    metadata = extract_assignment_front_matter(assignment)
    if not metadata:
        raise SystemExit("FAIL: assignment has no YAML front matter; it is human-readable only and cannot produce an automated capsule")
    status, reasons, snapshot = project_context_freshness(project_root)
    if status != "fresh":
        raise SystemExit("FAIL: project context snapshot is not fresh: " + (", ".join(reasons) if reasons else status))
    assn_id = safe_id(str(metadata.get("id", assignment.stem)), "assignment")
    required = [str(item) for item in metadata.get("required_capabilities", [])] if isinstance(metadata.get("required_capabilities"), list) else []
    optional = [str(item) for item in metadata.get("optional_capabilities", [])] if isinstance(metadata.get("optional_capabilities"), list) else []
    providers = load_registry_capability_providers(project_root)
    required_records, optional_records = capability_records(required, optional, providers)
    missing_required = [item["id"] for item in required_records if item.get("status") == "missing"]
    if missing_required:
        for capability in missing_required:
            emit_process_event(project_root, "capability.missing", severity="error", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capability": capability})
        raise SystemExit("FAIL: required capabilities missing: " + ", ".join(missing_required))
    flow_root = locate_flow_root(project_root)
    telemetry_rel = rel(flow_root / "runtime" / "telemetry" / f"{assn_id}.ndjson", project_root)
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    capsule = {
        "schema_version": 1,
        "capsule": {
            "id": f"{assn_id}-capsule",
            "snapshot": rel(snapshot_yaml, project_root),
            "snapshot_checksum": sha256_file(snapshot_yaml),
            "worker_may_rebuild_context": False,
        },
        "assignment": {"id": assn_id, "path": rel(assignment, project_root), "status": metadata.get("status", "ready")},
        "context": {"snapshot_id": snapshot.get("snapshot", {}).get("id", "project-context"), "freshness": status},
        "required_sources": [rel(snapshot_yaml, project_root), rel(assignment, project_root)],
        "allowed_files": metadata.get("allowed_files", []),
        "forbidden_files": metadata.get("forbidden_files", []),
        "required_outputs": metadata.get("required_outputs", []),
        "required_capabilities": required_records,
        "optional_capabilities": optional_records,
        "selected_sources": metadata.get("selected_sources", []),
        "telemetry": {"events": telemetry_rel},
        "event_correlation_id": f"assignment-{assn_id}",
    }
    capsule_dir = flow_root / "contexts" / "assignment-capsules"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = capsule_dir / f"{assn_id}.capsule.yaml"
    if capsule_path.exists() and not args.force:
        raise SystemExit(f"FAIL: capsule already exists: {rel(capsule_path, project_root)}")
    capsule_path.write_text(ensure_trailing_newline(dump_yaml(capsule)), encoding="utf-8")
    emit_process_event(project_root, "assignment.started", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"path": rel(assignment, project_root)}, correlation_id=f"assignment-{assn_id}")
    emit_process_event(project_root, "assignment.created", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capsule": rel(capsule_path, project_root)}, correlation_id=f"assignment-{assn_id}")
    emit_process_event(project_root, "artifact.created", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"path": rel(capsule_path, project_root)}, correlation_id=f"assignment-{assn_id}")
    print(f"WROTE: {rel(capsule_path, project_root)}")
    if optional_records:
        missing_optional = [item["id"] for item in optional_records if item.get("status") == "missing"]
        if missing_optional:
            for capability in missing_optional:
                emit_process_event(project_root, "capability.missing", severity="warn", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capability": capability}, correlation_id=f"assignment-{assn_id}")
            print("WARN: optional capabilities missing: " + ", ".join(missing_optional))
    return 0


def command_hooks_dispatch(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    hook_checks = validate_hooks_config(project_root)
    hook_failures = [item for item in hook_checks if item.level == "FAIL"]
    if hook_failures:
        for item in hook_failures:
            print(f"FAIL: {item.message}")
        return 1
    if getattr(args, "send", False):
        raise SystemExit("FAIL: --send is reserved for a future network transport and is disabled in the MVP")
    event = processforge_event(
        project_root,
        args.event_type,
        severity=args.severity,
        session_id=args.session_id,
        assignment_id_value=args.assignment_id,
        payload={"dry_run": bool(args.dry_run), "outbox": bool(args.outbox), "since": args.since, "source": "hooks-dispatch"},
        privacy="sanitized",
    )
    actions = dispatch_hooks(project_root, event, dry_run=args.dry_run, outbox=args.outbox or not args.dry_run)
    if not actions:
        print("HOOKS: none")
    else:
        for action in actions:
            print(f"HOOK: {action['hook']} {action['type']} {action['status']}")
            if "outbox" in action:
                print(f"OUTBOX: {action['outbox']}")
            if "result" in action:
                print(f"RESULT: {action['result']}")
    if not args.dry_run:
        append_process_event(project_root, event, dispatch=False)
        if actions:
            emit_process_event(project_root, "hook.dispatched", payload={"event_id": event_id_value(event), "actions": actions}, privacy="sanitized", correlation_id=str(event.get("correlation_id")))
        print(f"EVENT: {event_id_value(event)}")
    return 0


def command_events_validate(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    flow_root = locate_flow_root(project_root)
    failures: list[str] = []
    events_path = flow_root / "runtime" / "events" / "events.ndjson"
    for line_number, data, error in iter_ndjson(events_path):
        label = f"{rel(events_path, project_root)}:{line_number}"
        if error:
            failures.append(f"{label}: invalid NDJSON: {error}")
        else:
            failures.extend(validate_event_object(data, label))

    transcript_root = flow_root / "runtime" / "chat" / "transcripts"
    if transcript_root.is_dir():
        for transcript in sorted(transcript_root.glob("*.ndjson")):
            for line_number, data, error in iter_ndjson(transcript):
                label = f"{rel(transcript, project_root)}:{line_number}"
                if error:
                    failures.append(f"{label}: invalid NDJSON: {error}")
                else:
                    failures.extend(validate_chat_message_object(data, label))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: runtime events and chat transcripts validate.")
    return 0


def command_chat_record(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    if args.content_file:
        content = Path(args.content_file).expanduser().read_text(encoding="utf-8", errors="replace")
    elif args.content is not None:
        content = args.content
    else:
        raise SystemExit("FAIL: provide --content or --content-file")
    transcript, record, event = append_chat_message(
        project_root,
        session_id=args.session_id,
        participant_id=args.participant,
        participant_type=args.participant_type,
        participant_role=args.participant_role or args.participant,
        message_role=args.role,
        content=content,
        turn_id=args.turn_id,
        parent_message_id=args.parent_message_id,
        process_id=args.process_id,
        stage_id=args.stage_id,
        assignment_id_value=args.assignment_id,
        include_event_content=args.include_content,
    )
    print(f"TRANSCRIPT: {rel(transcript, project_root)}")
    print(f"MESSAGE: {record['message_id']}")
    print(f"EVENT: {event_id_value(event)}")
    return 0


def command_chat_export(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    if args.target != "wtaicc":
        raise SystemExit("FAIL: only --target wtaicc is supported by the MVP")
    if not args.outbox:
        raise SystemExit("FAIL: chat-export is file-first; pass --outbox to write a delivery payload")
    messages = load_chat_messages(project_root, args.session_id)
    event = processforge_event(
        project_root,
        "session.message.recorded",
        session_id=args.session_id,
        subject=f"chat/{args.session_id}",
        data={"session_id": args.session_id, "message_count": len(messages), "target": args.target},
        privacy="sanitized",
        correlation_id=args.session_id,
    )
    chat_payload = {
        "included": True,
        "mode": "full" if args.include_content else "metadata_only",
        "messages": chat_export_messages(messages, include_content=args.include_content),
    }
    payload = wtaicc_outbox_payload(event, chat=chat_payload)
    outbox_root = locate_flow_root(project_root) / "runtime" / "hooks" / "outbox" / "wtaicc"
    outbox_root.mkdir(parents=True, exist_ok=True)
    stamp = now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    target = outbox_root / f"chat-{safe_id(args.session_id, 'session')}-{stamp}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_process_event(project_root, event, dispatch=False)
    emit_process_event(
        project_root,
        "hook.dispatched",
        session_id=args.session_id,
        data={"target": args.target, "outbox": rel(target, project_root), "message_count": len(messages)},
        privacy="sanitized",
        correlation_id=args.session_id,
    )
    print(f"OUTBOX: {rel(target, project_root)}")
    print(f"MESSAGES: {len(messages)}")
    return 0


def command_context_resolve(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    require_flow_root(project_root)
    print("DEPRECATED: context-resolve is a compatibility command. Use project-context-refresh and project-context-check for .pf projects.")
    status, paths = write_context_outputs(project_root)
    print(f"STATUS: {status}")
    for path in paths.values():
        print(f"WROTE: {rel(path, project_root)}")
    return 1 if status == "blocked" else 0


def command_context_compile(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    assignment = Path(args.assignment).expanduser().resolve()
    print("DEPRECATED: context-compile is a compatibility command. Use assignment-capsule with YAML front matter for .pf projects.")
    ecp_path, capsule_path, conflict_report = compile_execution_context(
        project_root,
        assignment,
        write_capsule=args.capsule,
        supersede=args.supersede,
        allow_requires_approval=args.allow_requires_approval,
    )
    print(f"WROTE: {rel(conflict_report, project_root)}")
    print(f"WROTE: {rel(ecp_path, project_root)}")
    if capsule_path:
        print(f"WROTE: {rel(capsule_path, project_root)}")
    return 0


def command_doctor_context(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = require_flow_root(project_root)
    checks: list[Check] = []
    manifest = flow_root / "process-forge.yaml"
    checks.append(check("PASS" if manifest.is_file() else "FAIL", f"{rel(manifest, project_root)} found"))
    if manifest.is_file():
        manifest_text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(manifest_text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(manifest_text) else "FAIL", "public manifest contains no secret values"))

    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    context_index = flow_root / "contexts" / "context-index.yaml"
    resolved_rules = flow_root / "contexts" / "resolved-rules.yaml"
    conflict_report = flow_root / "contexts" / "context-conflict-report.md"
    cache = flow_root / "runtime" / "cache" / "context-cache.yaml"
    checks.append(check("PASS" if snapshot_yaml.is_file() else "WARN", "project context snapshot YAML found"))
    checks.append(check("PASS" if snapshot_md.is_file() else "WARN", "project context snapshot MD found"))
    snapshot_freshness, snapshot_stale, snapshot = project_context_freshness(project_root)
    if snapshot_yaml.is_file():
        checks.append(check("PASS" if snapshot_freshness == "fresh" else "FAIL", f"project context snapshot freshness is {snapshot_freshness}" + (f": {', '.join(snapshot_stale)}" if snapshot_stale else "")))
        health = snapshot.get("snapshot", {}).get("health", {}).get("status", "pass") if isinstance(snapshot.get("snapshot"), dict) else "pass"
        checks.append(check("PASS" if health != "blocked" else "FAIL", f"project context snapshot health is {health}"))
    checks.append(check("PASS" if context_index.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "context index found"))
    checks.append(check("PASS" if resolved_rules.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "resolved rules found"))
    checks.append(check("PASS" if conflict_report.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "conflict report found"))
    status = context_report_status(conflict_report)
    if conflict_report.is_file():
        checks.append(check("PASS" if status in {"resolved", "warn", "requires_approval"} else "FAIL", f"conflict status is {status}"))
    freshness, stale = context_freshness(project_root)
    if context_index.is_file():
        checks.append(check("PASS" if freshness == "fresh" else "FAIL", f"context freshness is {freshness}" + (f": {', '.join(stale)}" if stale else "")))
    checks.append(check("PASS" if cache.is_file() else "WARN", "context cache found"))

    gitignore = project_root / ".gitignore"
    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        runtime_cache_ignored = "runtime/cache/" in ignore_text or "/runtime/cache/" in ignore_text or "runtime/" in ignore_text or ".pf/runtime/" in ignore_text
        checks.append(check("PASS" if runtime_cache_ignored else "FAIL", ".gitignore contains runtime cache ignore"))
    else:
        checks.append(check("WARN", ".gitignore missing"))

    if args.assignment:
        assignment = Path(args.assignment).expanduser().resolve()
        _index, _resolved, report, assignment_status = build_context_payload(project_root, assignment)
        context_status = normalized_context_status(assignment_status)
        assignment_conflict_report = flow_root / "contexts" / f"{assignment_id(assignment)}.conflicts.md"
        if assignment_status == "blocked":
            checks.append(check("FAIL", "assignment context status is blocked"))
        elif assignment_status == "requires_approval":
            checks.append(check("FAIL", "assignment context requires approval"))
        elif assignment_status == "warn":
            checks.append(check("WARN", "assignment context is usable with warnings"))
        else:
            checks.append(check("PASS", "assignment context status is pass"))
        checks.append(check("PASS" if assignment_conflict_report.is_file() else "FAIL", "assignment-specific conflict report found"))
        if assignment_conflict_report.is_file():
            checks.append(check("PASS" if context_report_status(assignment_conflict_report) == assignment_status else "FAIL", "assignment conflict report status matches resolver"))
        ecp_candidates = sorted((flow_root / "contexts").glob(f"{assignment_id(assignment)}*.ecp.yaml"), key=lambda path: path.stat().st_mtime, reverse=True)
        ecp = ecp_candidates[0] if ecp_candidates else flow_root / "contexts" / f"{assignment_id(assignment)}.ecp.yaml"
        if ecp.is_file():
            ecp_text = ecp.read_text(encoding="utf-8", errors="replace")
            checksum = sha256_file(assignment) if assignment.is_file() else "missing"
            checks.append(check("PASS" if checksum in ecp_text else "FAIL", f"assignment ECP is fresh ({rel(ecp, project_root)})"))
            ecp_data = load_answers(ecp)
            ecp_status = ecp_data.get("context_status") if isinstance(ecp_data, dict) else None
            checks.append(check("PASS" if ecp_status == context_status else "FAIL", f"assignment ECP context_status is {ecp_status}"))
            report_ref = ecp_data.get("conflict_report") if isinstance(ecp_data, dict) else None
            checks.append(check("PASS" if report_ref == rel(assignment_conflict_report, project_root) else "FAIL", "assignment ECP references assignment conflict report"))
            ecp_checksums = ecp_data.get("checksums", {}) if isinstance(ecp_data, dict) else {}
            expected_context_index_checksum = sha256_file(context_index) if context_index.is_file() else "missing"
            checks.append(
                check(
                    "PASS" if ecp_checksums.get("context_index") == expected_context_index_checksum else "FAIL",
                    "assignment ECP context index checksum is fresh",
                )
            )
        else:
            checks.append(check("FAIL" if assignment_status != "blocked" else "PASS", "assignment ECP missing"))

    result = print_checks(checks)
    emit_process_event(
        project_root,
        "gate.failed" if result else "gate.passed",
        severity="error" if result else "info",
        payload={"command": "doctor-context", "result": "fail" if result else "pass"},
    )
    return result


def command_doctor_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = require_flow_root(project_root)
    checks: list[Check] = []
    manifest = flow_root / "process-forge.yaml"
    local_manifest = flow_root / "process-forge.local.yaml"
    gitignore = project_root / ".gitignore"
    auto_workplace_mode = False

    if manifest.is_file():
        checks.append(check("PASS", f"{rel(manifest, project_root)} found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "public manifest contains no secret values"))
        manifest_data = load_yaml_document(manifest)
    else:
        checks.append(check("FAIL", f"{rel(manifest, project_root)} missing"))
        manifest_data = {}

    distribution_root: Path | None = None
    if local_manifest.is_file():
        checks.append(check("PASS", "process-forge.local.yaml found"))
        workplace = resolve_workplace_manifest(local_manifest)
        if workplace and workplace.is_file():
            checks.append(check("PASS", "workplace manifest is reachable"))
            registry = resolve_registry_path(workplace, "distributions", "distributions.yaml")
            checks.append(check("PASS" if registry.is_file() else "FAIL", "workplace distributions registry is reachable"))
            distribution_root = resolve_distribution_path(workplace, "processforge")
        else:
            checks.append(check("FAIL", "workplace manifest is missing or unreachable"))
    else:
        workplace_data = manifest_data.get("workplace", {}) if isinstance(manifest_data.get("workplace"), dict) else {}
        if workplace_data.get("reference") == "auto":
            auto_workplace_mode = True
            checks.append(check("PASS", "process-forge.local.yaml omitted by explicit workplace.reference auto mode"))
            distribution_root = project_root
        else:
            checks.append(check("FAIL", "process-forge.local.yaml missing"))

    checks.extend(distribution_checks(distribution_root))
    checks.extend(validate_hooks_config(project_root))

    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for entry in [".pf/process-forge.local.yaml", ".pf/runtime/", ".pf/cache/"]:
            checks.append(check("PASS" if entry in ignore_text else "FAIL", f".gitignore contains {entry}"))
    else:
        checks.append(check("FAIL", ".gitignore missing"))

    package_exists = any((flow_root / "packages").glob("project.*.yaml")) if (flow_root / "packages").is_dir() else False
    checks.append(check("PASS" if package_exists else ("WARN" if auto_workplace_mode else "FAIL"), "project package draft exists"))
    resource_report = flow_root / "artifacts" / "global-resource-matching-report.md"
    if report_has_missing_required_capabilities(resource_report):
        checks.append(check("FAIL", "required capabilities are missing"))
    elif resource_report.is_file():
        checks.append(check("PASS", "required capabilities are resolved or built in"))
    if report_section_has_items(resource_report, "## Missing Required Platform Contracts"):
        checks.append(check("FAIL", "required platform contract is missing from workplace registry"))
    if report_section_has_items(resource_report, "## Missing Optional Platform Resources"):
        checks.append(check("WARN", "optional platform resources are missing from workplace registries"))

    for rel_path in [
        "artifacts/project-profile.md",
        "artifacts/project-classification-report.md",
        "artifacts/repository-map.md",
        "artifacts/project-conventions.md",
        "artifacts/global-resource-matching-report.md",
        "artifacts/project-init-proposal.md",
        "reviews/project-init-review.md",
    ]:
        path = flow_root / rel_path
        checks.append(check("PASS" if path.is_file() else ("WARN" if auto_workplace_mode else "FAIL"), f"{rel(path, project_root)} {'found' if path.is_file() else 'missing'}"))
    return print_checks(checks)


def load_update_index(distribution_root: Path) -> dict[str, Any]:
    candidates = [
        distribution_root / "updates" / "processforge-update-index.yaml",
        distribution_root / "updates" / "channels.yaml",
    ]
    for path in candidates:
        if path.is_file():
            data = load_yaml_document(path)
            return data if isinstance(data, dict) else {}
    return {}


def latest_update_version(update_index: dict[str, Any], channel: str) -> dict[str, Any] | None:
    channels = update_index.get("channels", {}) if isinstance(update_index.get("channels"), dict) else {}
    latest = None
    channel_data = channels.get(channel)
    if isinstance(channel_data, dict):
        latest = channel_data.get("latest")
    elif isinstance(channel_data, str):
        latest = channel_data
    versions = update_index.get("versions") if isinstance(update_index.get("versions"), list) else []
    for item in versions:
        if isinstance(item, dict) and str(item.get("version")) == str(latest):
            return item
    return None


def render_update_assessment(project_root: Path, current_version: str, channel: str, latest: dict[str, Any] | None) -> str:
    available_version = str(latest.get("version", "none")) if latest else "none"
    migration = latest.get("migration", {}) if latest and isinstance(latest.get("migration"), dict) else {}
    changes = latest.get("changes", []) if latest and isinstance(latest.get("changes"), list) else []
    affected = latest.get("affected_files", []) if latest and isinstance(latest.get("affected_files"), list) else []

    def lines(items: list[Any], empty: str = "None.") -> str:
        if not items:
            return f"- {empty}"
        output = []
        for item in items:
            if isinstance(item, dict):
                output.append(f"- {item.get('type', 'change')}: {item.get('summary', item)}")
            else:
                output.append(f"- {item}")
        return "\n".join(output)

    result = "safe" if available_version in {"none", current_version} else ("requires_migration" if migration.get("required") else "requires_approval")
    return f"""# ProcessForge Update Assessment

## Status

{result}

## Project

- root: {project_root.name}
- current_version: {current_version}
- available_version: {available_version}
- channel: {channel}

## Breaking Changes

{lines([item for item in changes if isinstance(item, dict) and item.get("breaking")], "None recorded.")}

## Required Migrations

- required: {bool(migration.get("required", False))}
- guide: {migration.get("guide", "none")}

## Changes

{lines(changes)}

## Affected Files

{lines(affected, "Review `.pf/process-forge.yaml`, `.pf/hooks.yaml`, and `.pf/contexts/project-context.snapshot.*`.")}

## Required Manual Review

- Review migration guide before changing project files.
- Confirm linked distribution registry points to the intended version.
- Run public cleanliness, schema validation, checksum validation, and project doctor after migration.

## Recommended Steps

1. Read the migration guide.
2. Update the ProcessForge distribution outside the project.
3. Refresh project context.
4. Apply project migrations only with approval.
5. Re-run validation gates.

## Rollback Notes

- Keep the previous ProcessForge distribution available in the workplace registry.
- Repoint the workplace distributions registry to the previous version if migration is blocked.
- Do not delete project `.pf/` artifacts created before the update until review passes.
"""


def command_self_update_check(args: argparse.Namespace) -> int:
    distribution_root = Path(args.distribution_root).expanduser().resolve() if args.distribution_root else ROOT
    channel = args.channel
    update_index = load_update_index(distribution_root)
    if not update_index:
        print(f"FAIL: update index not found under {distribution_root / 'updates'}")
        return 1
    latest = latest_update_version(update_index, channel)
    product = update_index.get("product", {}) if isinstance(update_index.get("product"), dict) else {}
    current = str(args.current_version or product.get("current_version") or "0.1.0")
    print(f"PRODUCT: {product.get('id', 'processforge')}")
    print(f"CURRENT: {current}")
    print(f"CHANNEL: {channel}")
    print(f"LATEST: {latest.get('version') if latest else 'none'}")
    if latest and str(latest.get("version")) != current:
        migration = latest.get("migration", {}) if isinstance(latest.get("migration"), dict) else {}
        print(f"UPDATE: available")
        print(f"MIGRATION_REQUIRED: {bool(migration.get('required', False))}")
        if migration.get("guide"):
            print(f"GUIDE: {migration.get('guide')}")
    else:
        print("UPDATE: none")
    return 0


def command_project_upgrade_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = require_flow_root(project_root)
    manifest = load_yaml_document(flow_root / "process-forge.yaml")
    process_forge_data = manifest.get("process_forge", {}) if isinstance(manifest.get("process_forge"), dict) else {}
    current = str(args.current_version or process_forge_data.get("version") or "0.1.0")
    distribution_root: Path | None = None
    local_manifest = flow_root / "process-forge.local.yaml"
    if local_manifest.is_file():
        workplace = resolve_workplace_manifest(local_manifest)
        if workplace and workplace.is_file():
            distribution_root = resolve_distribution_path(workplace, "processforge")
    if not distribution_root:
        distribution_root = project_root if (project_root / "updates").is_dir() else ROOT
    update_index = load_update_index(distribution_root)
    if not update_index:
        print(f"FAIL: update index not found under {distribution_root / 'updates'}")
        return 1
    latest = latest_update_version(update_index, args.channel)
    report = render_update_assessment(project_root, current, args.channel, latest)
    target = flow_root / "artifacts" / "processforge-update-assessment.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(report), encoding="utf-8")
    print(f"WROTE: {rel(target, project_root)}")
    return 0


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

    global_agents = sub.add_parser("global-agents-section", help="Insert or update the bounded ProcessForge section in an agent instructions file.")
    global_agents.add_argument("--path", required=True, help="Path to AGENTS.md, CODEX.md, or another agent instruction file.")
    global_agents.add_argument("--dry-run", action="store_true", help="Write a .candidate file instead of changing the target.")
    global_agents.add_argument("--force", action="store_true", help="Update the target file in place.")
    global_agents.set_defaults(func=command_global_agents_section)

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
    init_project.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
    init_project.set_defaults(func=command_init_project)

    doctor_project = sub.add_parser("doctor-project", help="Validate a ProcessForge project layer.")
    doctor_project.add_argument("--project-root", required=True, help="Project root path.")
    doctor_project.set_defaults(func=command_doctor_project)

    self_update = sub.add_parser("self-update-check", help="Check the current ProcessForge distribution update index.")
    self_update.add_argument("--distribution-root", help="ProcessForge distribution root. Defaults to this checkout.")
    self_update.add_argument("--current-version", help="Current ProcessForge version to compare.")
    self_update.add_argument("--channel", default="stable", help="Update channel.")
    self_update.set_defaults(func=command_self_update_check)

    project_upgrade = sub.add_parser("project-upgrade-check", help="Write a project update assessment without modifying project files.")
    project_upgrade.add_argument("--project-root", required=True, help="Project root path.")
    project_upgrade.add_argument("--current-version", help="Current ProcessForge version override.")
    project_upgrade.add_argument("--channel", default="stable", help="Update channel.")
    project_upgrade.set_defaults(func=command_project_upgrade_check)

    session_start = sub.add_parser("session-start", help="Start or inspect a ProcessForge session.")
    session_start.add_argument("--mode", required=True, choices=["resume", "project_init", "assignment_execute", "context_resolve", "context_compile", "doctor_context"], help="Session mode.")
    session_start.add_argument("--project-root", required=True, help="Project root path.")
    session_start.add_argument("--assignment", help="Optional assignment path loaded for telemetry.")
    session_start.add_argument("--allow-write", action="store_true", help="Write artifacts/session-status-report.md.")
    session_start.add_argument("--report-only", action="store_true", help="Do not write public artifacts. Private telemetry is still written.")
    session_start.add_argument("--rebuild-context-if-stale", action="store_true", help="Run context resolution when context is missing or stale.")
    session_start.set_defaults(func=command_session_start)

    project_context_refresh = sub.add_parser("project-context-refresh", help="Refresh the project context snapshot.")
    project_context_refresh.add_argument("--project-root", required=True, help="Project root path.")
    project_context_refresh.set_defaults(func=command_project_context_refresh)

    project_context_check = sub.add_parser("project-context-check", help="Check project context snapshot freshness.")
    project_context_check.add_argument("--project-root", required=True, help="Project root path.")
    project_context_check.set_defaults(func=command_project_context_check)

    assignment_capsule = sub.add_parser("assignment-capsule", help="Create an assignment capsule from snapshot plus assignment front matter.")
    assignment_capsule.add_argument("--project-root", required=True, help="Project root path.")
    assignment_capsule.add_argument("--assignment", required=True, help="Assignment Markdown with YAML front matter or assignment YAML.")
    assignment_capsule.add_argument("--force", action="store_true", help="Overwrite an existing capsule.")
    assignment_capsule.set_defaults(func=command_assignment_capsule)

    hooks_dispatch = sub.add_parser("hooks-dispatch", help="Dry-run or enqueue hook delivery for a ProcessForge event.")
    hooks_dispatch.add_argument("--project-root", required=True, help="Project root path.")
    hooks_dispatch.add_argument("--event-type", required=True, choices=REQUIRED_PROCESSFORGE_EVENT_TYPES, help="Event type to test or enqueue.")
    hooks_dispatch.add_argument("--severity", default="info", choices=["info", "warn", "error"], help="Event severity.")
    hooks_dispatch.add_argument("--session-id", help="Optional session id.")
    hooks_dispatch.add_argument("--assignment-id", help="Optional assignment id.")
    hooks_dispatch.add_argument("--dry-run", action="store_true", help="Report selected hooks without writing event/outbox payloads.")
    hooks_dispatch.add_argument("--outbox", action="store_true", help="Write matching hook payloads to .pf/runtime/hooks/outbox/.")
    hooks_dispatch.add_argument("--send", action="store_true", help="Reserved future network transport; disabled by default.")
    hooks_dispatch.add_argument("--since", help="Optional timestamp or event id marker for future event replay.")
    hooks_dispatch.set_defaults(func=command_hooks_dispatch)

    events_validate = sub.add_parser("events-validate", help="Validate runtime event and chat NDJSON files.")
    events_validate.add_argument("--project-root", required=True, help="Project root path.")
    events_validate.set_defaults(func=command_events_validate)

    chat_record = sub.add_parser("chat-record", help="Record one chat message into the private transcript and emit a chat event.")
    chat_record.add_argument("--project-root", required=True, help="Project root path.")
    chat_record.add_argument("--session-id", required=True, help="Session id.")
    chat_record.add_argument("--participant", required=True, help="Participant id, for example operator or subagent-reviewer-1.")
    chat_record.add_argument("--participant-type", choices=["human", "agent", "subagent", "tool"], help="Participant type.")
    chat_record.add_argument("--participant-role", help="Participant role; defaults to participant id.")
    chat_record.add_argument("--role", required=True, choices=["user", "assistant", "system", "tool", "subagent"], help="Message role.")
    chat_record.add_argument("--content", help="Message content.")
    chat_record.add_argument("--content-file", help="Read message content from a UTF-8 text file.")
    chat_record.add_argument("--turn-id", help="Optional turn id.")
    chat_record.add_argument("--parent-message-id", help="Optional parent message id.")
    chat_record.add_argument("--process-id", help="Optional process id.")
    chat_record.add_argument("--stage-id", help="Optional stage id.")
    chat_record.add_argument("--assignment-id", help="Optional assignment id.")
    chat_record.add_argument("--include-content", action="store_true", help="Opt in to include redacted content in the emitted event.")
    chat_record.set_defaults(func=command_chat_record)

    chat_export = sub.add_parser("chat-export", help="Export a chat transcript to an outbox payload without network send.")
    chat_export.add_argument("--project-root", required=True, help="Project root path.")
    chat_export.add_argument("--session-id", required=True, help="Session id.")
    chat_export.add_argument("--target", required=True, choices=["wtaicc"], help="Outbox target.")
    chat_export.add_argument("--outbox", action="store_true", help="Write .pf/runtime/hooks/outbox/wtaicc payload.")
    chat_export.add_argument("--include-content", action="store_true", help="Opt in to include redacted transcript content in the outbox payload.")
    chat_export.set_defaults(func=command_chat_export)

    context_resolve = sub.add_parser("context-resolve", help="Deprecated compatibility context index command.")
    context_resolve.add_argument("--project-root", required=True, help="Project root path.")
    context_resolve.set_defaults(func=command_context_resolve)

    context_compile = sub.add_parser("context-compile", help="Deprecated compatibility Execution Context Package command.")
    context_compile.add_argument("--project-root", default=".", help="Project root path.")
    context_compile.add_argument("--assignment", required=True, help="Assignment path.")
    context_compile.add_argument("--capsule", action="store_true", help="Also write a context capsule.")
    context_compile.add_argument("--supersede", action="store_true", help="Create a versioned ECP when the default immutable ECP already exists.")
    context_compile.add_argument("--allow-requires-approval", action="store_true", help="Allow ECP creation when assignment context requires approval.")
    context_compile.set_defaults(func=command_context_compile)

    doctor_context = sub.add_parser("doctor-context", help="Validate context resolution outputs.")
    doctor_context.add_argument("--project-root", required=True, help="Project root path.")
    doctor_context.add_argument("--assignment", help="Optional assignment path for ECP freshness check.")
    doctor_context.set_defaults(func=command_doctor_context)
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
