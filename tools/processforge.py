#!/usr/bin/env python3
"""ProcessForge MVP CLI for workplace/project init and doctor checks."""

from __future__ import annotations

import argparse
import contextlib
import fnmatch
import hashlib
import io
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from processforge_subprocess import diagnostic_text, format_command as format_subprocess_command, run_command as run_subprocess_command


ROOT = Path(__file__).resolve().parents[1]
PROJECT_FLOW_ROOT = ".pf"
PROCESSFORGE_VERSION = "1.0.0"
PROCESSFORGE_SPEC_VERSION = "1.0"
PROCESSFORGE_SCHEMA_BUNDLE_VERSION = "1.0"
RELEASE_NAME = "processforge"
RELEASE_ARCHIVE_VERSION = "1.0.0"

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
    "authoring",
    "authoring/processes",
    "packages",
    "templates",
    "runs",
    "assignments",
    "artifacts",
    "artifacts/runs",
    "contexts",
    "contexts/assignment-capsules",
    "logs",
    "handoffs",
    "handoffs/runs",
    "reviews",
    "reviews/runs",
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
   "платформенные знания", "глобальные шаблоны", "глобальные инструменты", and "MCP".
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
    "knowledge.resource.add.requested",
    "knowledge.resource.added",
    "knowledge.package.updated",
    "snapshot.stale",
    "template.add.requested",
    "template.added",
    "template.updated",
    "tool.registered",
    "tool.healthcheck.passed",
    "tool.healthcheck.failed",
    "mcp.registered",
    "mcp.healthcheck.passed",
    "mcp.healthcheck.failed",
    "platform.contract.updated",
    "path.constant.added",
    "path.constant.updated",
    "registry.path.added",
    "knowledge.resource.path.resolved",
    "knowledge.resource.path.unresolved",
    "project.snapshot.path_redacted",
    "doctor.path.failed",
    "package.root.resolved",
    "package.root.missing",
    "package.root.unavailable",
    "package.created",
    "package.updated",
    "package.index.updated",
    "package.doctor.failed",
    "package.duplicate.detected",
    "workplace.initialization.started",
    "workplace.structure.created",
    "workplace.path_constants.created",
    "workplace.registry.created",
    "workplace.doctor.passed",
    "workplace.doctor.failed",
    "workplace.initialization.completed",
    "project.onboarding.started",
    "project.flow_root.created",
    "project.platform.detected",
    "project.snapshot.refreshed",
    "project.doctor.passed",
    "project.doctor.failed",
    "project.onboarding.completed",
    "agent.start_prompt.generated",
    "launcher.project_runtime.created",
    "template.authoring.started",
    "template.created",
    "template.registered",
    "template.doctor.passed",
    "template.doctor.failed",
    "template.authoring.completed",
    "knowledge_package.authoring.started",
    "knowledge_package.created",
    "knowledge_package.resource_index.created",
    "knowledge_package.doctor.passed",
    "knowledge_package.doctor.failed",
    "knowledge_package.authoring.completed",
    "platform.authoring.started",
    "platform.contract.created",
    "platform.contract.linked",
    "platform.contract.doctor.passed",
    "platform.contract.doctor.failed",
    "platform.authoring.completed",
    "run.created",
    "run.started",
    "run.updated",
    "run.summary.created",
    "run.completed",
    "run.failed",
    "run.cancelled",
    "run.doctor.passed",
    "run.doctor.failed",
    "task.created",
    "task.started",
    "task.updated",
    "task.completed",
    "task.failed",
    "task.cancelled",
    "task.doctor.passed",
    "task.doctor.failed",
    "iteration.added",
    "iteration.started",
    "iteration.completed",
    "iteration.failed",
    "process_authoring.started",
    "process_authoring.answers.created",
    "process_authoring.draft.created",
    "process_authoring.logic_review.created",
    "process_authoring.applied",
    "process_authoring.completed",
    "process_authoring.failed",
    "process.created",
    "process.doctor.passed",
    "process.doctor.failed",
    "authoring_parity.started",
    "authoring_parity.process.checked",
    "authoring_parity.resource.checked",
    "authoring_parity.warning",
    "authoring_parity.failed",
    "authoring_parity.completed",
]

BUILTIN_CAPABILITIES = {
    "repository.read",
    "repository.scan",
    "repository_read",
    "markdown.editing",
    "markdown_editing",
    "filesystem.read",
    "filesystem.write",
    "php",
    "html",
    "css",
    "javascript",
    "web.accessibility",
    "web.performance",
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

BACKSLASH = chr(92)
COLON_WS = ":" + r"\s*"
LOCAL_PATH_PATTERNS = [
    re.compile(r"(?<![A-Za-z])[A-Za-z]:" + re.escape(BACKSLASH)),
    re.compile(r"(?<![A-Za-z])[A-Za-z]:/"),
    re.compile("/" + "home" + "/[A-Za-z0-9_.-]+/"),
    re.compile("/" + "Users" + "/[A-Za-z0-9_.-]+/"),
    re.compile("/" + "srv" + "/"),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]

DEFAULT_PATH_CONSTANTS = {
    "PF_WORKPLACE": ".",
    "PF_DISTRIBUTION": "distributions/processforge",
    "PF_KNOWLEDGE": "knowledge",
    "PF_TEMPLATES": "reusable-templates",
    "PF_TOOLS": "tools",
    "PF_MCP": "mcp",
    "PF_PLATFORM_CONTRACTS": "platform-contracts",
    "PF_PROCESS_TEMPLATES": "process-templates",
    "PF_RUNTIME": "runtime",
    "PF_CACHE": "cache",
}

PATH_CONSTANT_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


@dataclass
class Check:
    level: str
    message: str


@dataclass
class WriteResult:
    path: Path
    status: str
    target: Path


@dataclass
class PackageRootResolution:
    root_id: str
    original_path: str
    resolved_path: Path
    status: str
    warnings: list[str]
    fallback: bool = False
    entry: dict[str, Any] | None = None


def safe_id(value: str, default: str = "project") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or default


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def path_string_is_absolute(value: str) -> bool:
    text = value.strip().replace("\\", "/")
    return bool(re.match(r"^[A-Za-z]:/", text) or text.startswith("/") or text.startswith("//"))


def normalize_path_string(value: str) -> str:
    return value.replace("\\", "/")


def load_workplace_path_constants(workplace_manifest: Path | None, workplace_root: Path | None = None) -> dict[str, str]:
    root = workplace_root or (workplace_manifest.parent if workplace_manifest else Path(".").resolve())
    constants = dict(DEFAULT_PATH_CONSTANTS)
    if workplace_manifest and workplace_manifest.is_file():
        data = load_yaml_document(workplace_manifest)
        raw_constants = data.get("path_constants") if isinstance(data, dict) else None
        if isinstance(raw_constants, dict):
            for key, value in raw_constants.items():
                if isinstance(key, str):
                    constants[key] = "" if value is None else str(value)
    constants.setdefault("PF_WORKPLACE", ".")
    constants["_WORKPLACE_ROOT"] = root.as_posix()
    return constants


def expand_path_constants(raw_path: str, constants: dict[str, str]) -> tuple[str, list[str], list[str]]:
    expanded = raw_path
    used: list[str] = []
    errors: list[str] = []
    visiting: list[str] = []

    def expand_const(name: str) -> str:
        if name in visiting:
            errors.append("cyclic path constant reference: " + " -> ".join([*visiting, name]))
            return "${" + name + "}"
        if name not in constants:
            errors.append(f"unknown path constant: {name}")
            return "${" + name + "}"
        value = str(constants.get(name, ""))
        if value == "":
            errors.append(f"empty path constant: {name}")
            return ""
        used.append(name)
        visiting.append(name)
        result = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), value)
        visiting.pop()
        return result

    for _ in range(20):
        if not PATH_CONSTANT_PATTERN.search(expanded):
            break
        before = expanded
        expanded = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), expanded)
        if expanded == before:
            break
    if PATH_CONSTANT_PATTERN.search(expanded):
        errors.append("unresolved path constant reference remains")
    return expanded, sorted(set(used)), sorted(set(errors))


def resolve_path_with_constants(raw_path: str | None, base_dir: Path, constants: dict[str, str] | None = None) -> dict[str, Any]:
    original = "" if raw_path is None else str(raw_path)
    constants = constants or load_workplace_path_constants(None, base_dir)
    expanded, used_constants, errors = expand_path_constants(original, constants)
    expanded = normalize_path_string(expanded)
    status = "resolved"
    if errors:
        status = "error"
    elif used_constants:
        status = "resolved_from_constant"
    elif path_string_is_absolute(expanded):
        status = "absolute"
    else:
        status = "resolved_relative"
    if path_string_is_absolute(expanded):
        resolved = expanded
        is_absolute = True
    else:
        resolved = normalize_path_string((base_dir / expanded).resolve().as_posix())
        is_absolute = True
    return {
        "original": original,
        "expanded": expanded,
        "resolved": resolved,
        "is_absolute": is_absolute,
        "is_private": is_absolute,
        "path_status": status,
        "constants": used_constants,
        "errors": errors,
    }


def workplace_path_resolution(workplace_root: Path, raw_path: str | None) -> dict[str, Any]:
    manifest = workplace_root / "workplace.yaml"
    return resolve_path_with_constants(raw_path, workplace_root, load_workplace_path_constants(manifest, workplace_root))


def path_resolution_to_path(resolution: dict[str, Any]) -> Path:
    return Path(str(resolution.get("resolved") or resolution.get("expanded") or resolution.get("original") or ""))


def locate_flow_root(project_root: Path, *, prefer_pf: bool = True) -> Path:
    return project_root / PROJECT_FLOW_ROOT


def require_flow_root(project_root: Path) -> Path:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    if not manifest.is_file():
        raise SystemExit(
            f"FAIL: .pf/process-forge.yaml not found under {project_root}. "
            "Run `python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --apply` first."
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
            "platform_knowledge": {
                "label": "platform knowledge",
                "label_ru": "платформенные знания",
                "aliases": ["platform knowledge", "platform contract"],
                "aliases_ru": ["знания платформы", "контракт платформы"],
                "definition": "A platform contract and its referenced knowledge resources.",
                "resolves_to": {"registry": "platform_contracts"},
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
            "resource_management": {
                "label": "resource management",
                "label_ru": "управление ресурсами",
                "aliases": ["knowledge resource add", "resource index", "documentation import"],
                "aliases_ru": ["управление знаниями", "индекс ресурсов", "импорт документации"],
                "definition": "Proposal-first workplace processes and commands for maintaining knowledge resources, templates, tools, MCP, and platform contracts.",
                "resolves_to": {"processes": ["knowledge-resource-add", "documentation-mirror-import", "template-add", "tool-register", "mcp-register"]},
            },
            "resource_index": {
                "label": "resource index",
                "label_ru": "индекс ресурсов",
                "aliases": ["knowledge resource index", "package resource index"],
                "aliases_ru": ["индекс знаний", "индекс пакета"],
                "definition": "Metadata-only package index describing available resources, path_ref, load_policy, index_policy, source, license, and update policy.",
                "resolves_to": {"file": "indexes/resource-index.yaml"},
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
    path_constants = dict(DEFAULT_PATH_CONSTANTS)
    answer_constants = paths_answers.get("path_constants")
    if isinstance(answer_constants, dict):
        for key, value in answer_constants.items():
            if isinstance(key, str) and value not in (None, ""):
                path_constants[key] = str(value)

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
            "version_constraint": "^1.0",
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
        "path_constants": path_constants,
        "registries": {
            "distributions": "registries/distributions.yaml",
            "platforms": "registries/platforms.yaml",
            "knowledge_roots": "registries/knowledge-roots.yaml",
            "package_roots": "registries/package-roots.yaml",
            "templates": "registries/templates.yaml",
            "tools": "registries/tools.yaml",
            "mcp": "registries/mcp.yaml",
            "update_sources": "registries/update-sources.yaml",
            "installed_subjects": "registries/installed-subjects.yaml",
            "update_site_overrides": "registries/update-site-overrides.yaml",
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
    if not package_entries:
        package_entries = [
            {
                "id": "global",
                "label": "Global packages",
                "path": "${PF_WORKPLACE}/packages",
                "scope": "workplace",
                "status": "available",
                "writable": True,
                "default": True,
            }
        ]
    template_entries = dict_entries_from_answers(paths_answers.get("template_roots"), "template-root", "workplace")
    distribution_entries = dict_entries_from_answers(paths_answers.get("distributions"), "distribution", "workplace")
    if not distribution_entries:
        distribution_entries = [
            {
                "id": "processforge",
                "name": "ProcessForge",
                "path": str(ROOT),
                "version": "1.0.0",
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
- registries/update-sources.yaml
- registries/installed-subjects.yaml
- registries/update-site-overrides.yaml

## Notes

- Secret values were not stored.
- Project public manifests must keep local paths out.
"""

    bootstrap_report = f"""# Workplace Bootstrap Report

## Status

created

## Workplace

- id: {defaults["id"]}
- root: {root}

## Created Files

- workplace.yaml
- terms.yaml
- registries/
- artifacts/
- reviews/
- handoffs/
- runtime/events/events.ndjson

## Next Required Check

`workplace-init --apply` runs `doctor-workplace` automatically and updates this report with the doctor result.
"""

    bootstrap_review = """# Workplace Bootstrap Review

## Reviewed Object

Workplace initialization output.

## Result

pending

## Notes

This review is finalized after `doctor-workplace` runs.
"""

    workplace_handoff = """# Handoff: workplace-initialization -> project-onboarding

Objective:
Prepare the workplace for future project onboarding.

Current status:
Workplace files were created.

Input artifacts:
- workplace.yaml
- terms.yaml
- registries/

Files changed:
- workplace root

Files not to touch:
- Project `.pf/` folders; those belong to `project-onboarding`.

Known issues:
- Doctor status is finalized by `workplace-init --apply`.

Required checks:
- `pf doctor-workplace --root <workplace-root>`

Next recommended action:
Run `project-onboard` for a concrete project.
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
        root / "registries" / "update-sources.yaml": dump_yaml(
            {
                "schema_version": 1,
                "product": "processforge",
                "updated_at": None,
                "defaults": {
                    "channel": "stable",
                    "cache_ttl_seconds": 3600,
                    "require_https": True,
                    "require_sha256_for_download": True,
                    "require_sha256_for_install": True,
                    "require_signature_for_install": False,
                },
                "sources": [],
            }
        ),
        root / "registries" / "installed-subjects.yaml": dump_yaml(
            {"schema_version": 1, "updated_at": None, "subjects": []}
        ),
        root / "registries" / "update-site-overrides.yaml": dump_yaml(
            {"schema_version": 1, "updated_at": None, "overrides": []}
        ),
        root / "logs" / "workplace-init-report.md": report,
        root / "artifacts" / "workplace-bootstrap-report.md": bootstrap_report,
        root / "reviews" / "workplace-bootstrap-review.md": bootstrap_review,
        root / "handoffs" / "workplace-ready-handoff.md": workplace_handoff,
    }
    return files


def finalize_workplace_doctor_artifacts(root: Path, status: int, output: str) -> None:
    result = "pass" if status == 0 else "fail"
    report = f"""# Workplace Bootstrap Report

## Status

{result}

## Doctor Command

```bash
pf doctor-workplace --root <workplace-root>
```

## Doctor Output

```text
{output.rstrip()}
```
"""
    review = f"""# Workplace Bootstrap Review

## Reviewed Object

Workplace initialization output.

## Result

{result}

## Evidence

- artifacts/workplace-bootstrap-report.md
- runtime/events/events.ndjson
"""
    handoff = f"""# Handoff: workplace-initialization -> project-onboarding

Objective:
Prepare the workplace for future project onboarding.

Current status:
Doctor status: {result}.

Input artifacts:
- workplace.yaml
- terms.yaml
- registries/
- artifacts/workplace-bootstrap-report.md

Files changed:
- workplace root

Files not to touch:
- Project `.pf/` folders; those belong to `project-onboarding`.

Known issues:
{("- Doctor failed; read artifacts/workplace-bootstrap-report.md for fix hints." if status else "- None recorded.")}

Required checks:
- `pf doctor-workplace --root <workplace-root>`

Next recommended action:
Run `project-onboard` for a concrete project.
"""
    write_file(root / "artifacts" / "workplace-bootstrap-report.md", report, force=True)
    write_file(root / "reviews" / "workplace-bootstrap-review.md", review, force=True)
    write_file(root / "handoffs" / "workplace-ready-handoff.md", handoff, force=True)


def workplace_event(root: Path, event_type: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = root / "workplace.yaml"
    workplace_id = safe_id(root.name or "workplace", "workplace")
    if manifest.is_file():
        data = load_yaml_document(manifest)
        workplace = data.get("workplace") if isinstance(data, dict) else None
        if isinstance(workplace, dict) and workplace.get("id"):
            workplace_id = safe_id(str(workplace["id"]), "workplace")
    return {
        "schema_version": 1,
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": event_type,
        "source": "processforge.cli",
        "subject": workplace_id,
        "time": now_utc(),
        "correlation_id": f"workplace-init-{workplace_id}",
        "project": {"flow_root": "workplace", "project_id": workplace_id},
        "process": {"id": "workplace-initialization", "version": "1.0.0", "stage_id": None, "process_run_id": None},
        "assignment": {"id": None, "path": None},
        "actor": {"type": "agent", "id": "processforge-cli", "role": "orchestrator"},
        "session": {"id": None},
        "data": payload or {},
        "severity": "info",
        "privacy": "private",
    }


def append_workplace_event(root: Path, event_type: str, *, payload: dict[str, Any] | None = None) -> Path:
    events_path = root / "runtime" / "events" / "events.ndjson"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(workplace_event(root, event_type, payload=payload), ensure_ascii=False, sort_keys=True) + "\n")
    return events_path


def command_init_workplace(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    answers = load_answers(Path(args.answers).expanduser().resolve() if args.answers else None)
    files = build_workplace_files(root, answers)
    planned_dirs = [root / "cache", root / "runtime", root / "runtime" / "events", root / "logs", root / "artifacts", root / "reviews", root / "handoffs", root / "packages", root / "knowledge", root / "reusable-templates", root / "platform-contracts", root / "tools", root / "mcp"]
    if not args.apply:
        print_plan("workplace init dry run", list(files) + planned_dirs, root)
        return 0
    append_workplace_event(root, "workplace.initialization.started", payload={"command": getattr(args, "command", "init-workplace")})
    for directory in planned_dirs:
        directory.mkdir(parents=True, exist_ok=True)
    results: list[WriteResult] = []
    for path, content in files.items():
        if path.name == "AGENTS.md":
            results.append(write_global_agent_section(path, force=args.force))
        else:
            results.append(write_file(path, content, force=args.force))
    append_workplace_event(root, "workplace.structure.created", payload={"directories": [rel(path, root) for path in planned_dirs]})
    append_workplace_event(root, "workplace.path_constants.created", payload={"manifest": "workplace.yaml"})
    append_workplace_event(root, "workplace.registry.created", payload={"registries": "registries/"})
    doctor_status, doctor_output = run_command_capture(command_doctor_workplace, argparse.Namespace(root=str(root)))
    print(doctor_output, end="")
    finalize_workplace_doctor_artifacts(root, doctor_status, doctor_output)
    append_workplace_event(
        root,
        "workplace.doctor.passed" if doctor_status == 0 else "workplace.doctor.failed",
        payload={"status": "pass" if doctor_status == 0 else "fail"},
    )
    append_workplace_event(root, "workplace.initialization.completed", payload={"files": [rel(result.target, root) for result in results], "doctor_status": doctor_status})
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, root)}")
    return doctor_status


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


def check_with_hint(level: str, message: str, why: str, fix: str, alternative: str | None = None) -> Check:
    details = [message, "", "Why:", f"  {why}", "", "Fix:"]
    details.extend(f"  {line}" if line else "" for line in fix.splitlines())
    if alternative:
        details.extend(["", "Or:"])
        details.extend(f"  {line}" if line else "" for line in alternative.splitlines())
    return check(level, "\n".join(details))


def run_command_capture(func: Any, args: argparse.Namespace) -> tuple[int, str]:
    buffer = io.StringIO()
    status = 0
    with contextlib.redirect_stdout(buffer):
        try:
            status = int(func(args) or 0)
        except SystemExit as exc:
            status = int(exc.code) if isinstance(exc.code, int) else 1
            if exc.code and not isinstance(exc.code, int):
                print(str(exc.code))
    return status, buffer.getvalue()


def path_constant_checks(workplace_root: Path, workplace_manifest: Path) -> list[Check]:
    checks: list[Check] = []
    data = load_yaml_document(workplace_manifest)
    constants_data = data.get("path_constants") if isinstance(data, dict) else None
    checks.append(check("PASS" if isinstance(constants_data, dict) else "WARN", "path_constants configured" if isinstance(constants_data, dict) else "path_constants missing; defaults will be used"))
    constants = load_workplace_path_constants(workplace_manifest, workplace_root)
    for name, value in constants.items():
        if name.startswith("_"):
            continue
        if not isinstance(value, str) or value == "":
            checks.append(check("FAIL", f"path constant {name} has empty value"))
            continue
        resolution = resolve_path_with_constants("${" + name + "}", workplace_root, constants)
        errors = resolution.get("errors", [])
        if errors:
            checks.append(check("FAIL", f"path constant {name} failed: {', '.join(errors)}"))
        else:
            checks.append(check("PASS", f"path constant {name} resolves ({resolution.get('path_status')})"))
    return checks


def registry_path_resolution_checks(workplace_root: Path, workplace_manifest: Path) -> list[Check]:
    checks: list[Check] = []
    constants = load_workplace_path_constants(workplace_manifest, workplace_root)
    manifest_data = load_yaml_document(workplace_manifest)
    registries = manifest_data.get("registries", {}) if isinstance(manifest_data.get("registries"), dict) else {}
    for key, default_name in [
        ("distributions", "distributions.yaml"),
        ("platforms", "platforms.yaml"),
        ("knowledge_roots", "knowledge-roots.yaml"),
        ("package_roots", "package-roots.yaml"),
        ("templates", "templates.yaml"),
        ("tools", "tools.yaml"),
        ("mcp", "mcp.yaml"),
    ]:
        raw_path = str(registries.get(key) or f"registries/{default_name}")
        resolution = resolve_path_with_constants(raw_path, workplace_root, constants)
        errors = resolution.get("errors", [])
        if errors:
            checks.append(check("FAIL", f"registry {key} path failed: {', '.join(errors)}"))
        else:
            path = path_resolution_to_path(resolution)
            checks.append(check("PASS" if path.is_file() else "FAIL", f"registry {key} resolves to {normalize_path_string(str(path))}"))
    registry_specs = [
        ("knowledge-roots.yaml", "knowledge_roots", "path"),
        ("package-roots.yaml", "package_roots", "path"),
        ("templates.yaml", "template_roots", "path"),
        ("tools.yaml", "tools", "command"),
        ("mcp.yaml", "mcp_servers", "command"),
    ]
    for registry_file, collection_key, path_key in registry_specs:
        registry_path = resolve_registry_path(workplace_manifest, collection_key if collection_key != "mcp_servers" else "mcp", registry_file)
        if collection_key == "template_roots":
            registry_path = resolve_registry_path(workplace_manifest, "templates", registry_file)
        elif collection_key == "tools":
            registry_path = resolve_registry_path(workplace_manifest, "tools", registry_file)
        elif collection_key == "knowledge_roots":
            registry_path = resolve_registry_path(workplace_manifest, "knowledge_roots", registry_file)
        elif collection_key == "package_roots":
            registry_path = resolve_registry_path(workplace_manifest, "package_roots", registry_file)
        if not registry_path.is_file():
            continue
        data = load_yaml_document(registry_path)
        entries = data.get(collection_key) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get(path_key):
                continue
            entry_id = str(entry.get("id", "entry"))
            resolution = resolve_path_with_constants(str(entry[path_key]), workplace_root, constants)
            errors = resolution.get("errors", [])
            if errors:
                checks.append(check("FAIL", f"{collection_key}.{entry_id}.{path_key} failed: {', '.join(errors)}"))
                continue
            if path_key == "path":
                resolved_path = path_resolution_to_path(resolution)
                requires_existing = str(entry.get("status", "available")) == "available" or bool(entry.get("must_exist", False))
                level = "PASS" if resolved_path.exists() or not requires_existing else "WARN"
                checks.append(check(level, f"{collection_key}.{entry_id}.path resolves ({resolution.get('path_status')})"))
            else:
                checks.append(check("PASS", f"{collection_key}.{entry_id}.{path_key} resolves constants"))
    return checks


def package_root_registry_checks(workplace_root: Path) -> list[Check]:
    checks: list[Check] = []
    registry_path = workplace_root / "registries" / "package-roots.yaml"
    if not registry_path.is_file():
        return [check("WARN", "registries/package-roots.yaml missing; package writes will use fallback <workplace-root>/packages")]
    entries = package_root_entries(workplace_root)
    if not entries:
        return [check("WARN", "package_roots registry is empty; package writes will use fallback <workplace-root>/packages")]
    ids: dict[str, int] = {}
    for entry in entries:
        root_id = str(entry.get("id", ""))
        ids[root_id] = ids.get(root_id, 0) + 1
    for root_id, count in sorted(ids.items()):
        checks.append(check("FAIL" if count > 1 else "PASS", f"package_root id {root_id or '<missing>'} unique"))
    selectable = False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        root = package_root_resolution_from_entry(workplace_root, entry)
        label = f"package_root {root.root_id}"
        if root.warnings:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{label} path cannot resolve: {'; '.join(root.warnings)}",
                    "The package root registry points to a path ProcessForge cannot use.",
                    "edit registries/package-roots.yaml so this package_root path exists and is relative to the workplace when possible",
                )
            )
            continue
        exists = root.resolved_path.is_dir()
        status = str(entry.get("status", "available"))
        must_exist = status == "available" or bool(entry.get("must_exist", False))
        checks.append(
            check("PASS", f"{label} path exists")
            if exists or not must_exist
            else check_with_hint(
                "FAIL",
                f"{label} path missing",
                "This package_root is marked available or must_exist but the directory is absent.",
                f"create the package root directory or update registries/package-roots.yaml for {root.root_id}",
            )
        )
        if exists and status == "available":
            selectable = True
        if str(entry.get("writable", True)).lower() != "false" and exists:
            checks.append(check("PASS", f"{label} writable candidate"))
    checks.append(
        check("PASS", "default/first available package_root can be selected")
        if selectable
        else check_with_hint(
            "FAIL",
            "default/first available package_root can be selected",
            "Authoring commands need at least one available package_root unless every write passes an explicit --package-root.",
            "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
            "add an available entry to registries/package-roots.yaml",
        )
    )
    return checks


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
        checks.extend(path_constant_checks(root, manifest))
        checks.extend(registry_path_resolution_checks(root, manifest))
        checks.extend(package_root_registry_checks(root))
    else:
        checks.append(
            check_with_hint(
                "FAIL",
                "workplace.yaml missing",
                "The selected path is not an initialized ProcessForge workplace.",
                "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
            )
        )

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
        checks.append(
            check("PASS", f"{rel_path} found")
            if path.is_file()
            else check_with_hint(
                "FAIL",
                f"{rel_path} missing",
                "A required workplace registry is absent.",
                "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
            )
        )
        if path.is_file() and contains_secret_value(path.read_text(encoding="utf-8", errors="replace")):
            checks.append(check("FAIL", f"{rel_path} appears to contain a secret value"))

    for rel_dir in ["cache", "runtime", "logs"]:
        path = root / rel_dir
        checks.append(check("PASS" if path.is_dir() else "WARN", f"{rel_dir}/ {'found' if path.is_dir() else 'missing'}"))

    if manifest.is_file():
        knowledge_roots = load_workplace_registry(manifest, "knowledge_roots", "knowledge-roots.yaml")
        knowledge_entries = knowledge_roots.get("knowledge_roots") if isinstance(knowledge_roots, dict) else []
        local_docs = next((item for item in knowledge_entries if isinstance(item, dict) and str(item.get("id")) == "local-docs"), None) if isinstance(knowledge_entries, list) else None
        if not local_docs:
            checks.append(
                check_with_hint(
                    "WARN",
                    "knowledge_roots.local-docs configured",
                    "Local heavy documentation and source snapshots must be referenced through knowledge_roots.local-docs instead of private package paths.",
                    "add an entry with id: local-docs to registries/knowledge-roots.yaml, pointing at the machine-local documentation root",
                )
            )
        else:
            local_docs_path = resolve_registry_relative_path(root, str(local_docs.get("path", "")), manifest)
            checks.append(
                check("PASS", "knowledge_roots.local-docs path exists")
                if local_docs_path.is_dir()
                else check_with_hint(
                    "WARN",
                    "knowledge_roots.local-docs path exists",
                    "The local-docs root is registered but the target directory is not available on this machine.",
                    "create the directory or update registries/knowledge-roots.yaml to the correct local documentation root",
                )
            )

        platforms_registry = load_workplace_registry(manifest, "platforms", "platforms.yaml")
        platform_entries = platforms_registry.get("platforms") if isinstance(platforms_registry, dict) else []
        platform_ids = [
            str(item.get("id") or item.get("package_id"))
            for item in platform_entries
            if isinstance(item, dict) and (item.get("id") or item.get("package_id")) and str(item.get("status", "available")) not in {"missing", "disabled"}
        ] if isinstance(platform_entries, list) else []
        if platform_ids:
            workplace_resolution = resolve_platform_contracts(manifest, platform_ids)
            checks.append(check("PASS" if not workplace_resolution["missing_required_contracts"] else "FAIL", "platform inheritance parent platforms resolve"))
            for missing in workplace_resolution["missing_required_contracts"]:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"required platform available: {missing}",
                        "A workplace platform extends or requires a platform that is not registered.",
                        f"python bin/pf.py platform-create --workplace <workplace-root> --id {missing} --title \"{missing}\" --apply",
                    )
                )
            for cycle in workplace_resolution["circular_platforms"]:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"circular platform inheritance detected: {cycle}",
                        "Workplace platform inheritance must resolve to an acyclic stack.",
                        "remove one extends edge from the cycle and rerun doctor-workplace",
                    )
                )
        public_manifest_paths: list[Path] = []
        if platform_ids:
            public_manifest_paths.extend(path for pid in platform_ids for path in [platform_contract_path(root, pid)] if path)
        public_manifest_paths.extend(package_manifest_candidates(root, None, manifest))
        for public_path in sorted(set(public_manifest_paths), key=lambda item: item.as_posix()):
            text = public_path.read_text(encoding="utf-8", errors="replace")
            checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", f"{rel(public_path, root)} contains no private absolute paths"))

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


def selected_project_platforms(detected: dict[str, Any], answers: dict[str, Any], project_type: str, workplace_manifest: Path | None, project_root: Path) -> list[str]:
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
    for key in ["platform", "platforms", "platform_contract", "platform_contracts"]:
        value = project_answers.get(key)
        if value:
            selected.update(platform_contract_id(item).removeprefix("platform.") for item in answer_strings(value))
    selected.update(workplace_platform_ids_for_project_type(workplace_manifest, project_type, project_root))
    selected.update(platform_ids_from_detection_rules(workplace_manifest, project_root))
    return sorted(selected)


def platform_contract_project_type_hints(contract: dict[str, Any]) -> list[str]:
    hints = list_value(contract.get("project_type_hints"))
    applies_to = contract.get("applies_to") if isinstance(contract.get("applies_to"), dict) else {}
    detection = contract.get("detection") if isinstance(contract.get("detection"), dict) else {}
    hints.extend(list_value(applies_to.get("project_type_hints")))
    hints.extend(list_value(applies_to.get("project_types")))
    hints.extend(list_value(detection.get("project_type_hints")))
    return sorted(set(str(item) for item in hints if item))


def hint_matches(candidate: str, hints: list[str]) -> bool:
    candidate_variants = {candidate, normalize_hint(candidate), normalize_hint(candidate).replace(" ", "-")}
    for hint in hints:
        hint_variants = {hint, normalize_hint(hint), normalize_hint(hint).replace(" ", "-")}
        if candidate_variants.intersection(hint_variants):
            return True
    return False


def workplace_platform_ids_for_project_type(workplace_manifest: Path | None, project_type: str, project_root: Path | None = None) -> list[str]:
    matched: list[str] = []
    for contract_id, entry in platform_contract_manifest_index(workplace_manifest, project_root).items():
        if hint_matches(project_type, platform_contract_project_type_hints(entry["contract"])):
            matched.append(contract_id.removeprefix("platform."))
    return sorted(set(item for item in matched if item))


def path_matches_pattern(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    return fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern)


def detection_group_matches(values: Any, available: set[str], *, all_required: bool) -> bool:
    patterns = list_value(values)
    if not patterns:
        return False
    checks = [any(path_matches_pattern(item, pattern) for item in available) for pattern in patterns]
    return all(checks) if all_required else any(checks)


def platform_detection_matches(contract: dict[str, Any], project_root: Path) -> bool:
    detection = contract.get("detection") if isinstance(contract.get("detection"), dict) else {}
    if not detection:
        return False
    files = list_project_files(project_root)
    rel_files = {rel(path, project_root) for path in files}
    directories = {
        item.as_posix()
        for path in files
        for item in [path.relative_to(project_root).parent]
        if item.as_posix() != "."
    }
    directories.update(path.name for path in project_root.iterdir() if path.is_dir() and path.name not in {".git", ".idea", ".serena"})
    dir_rules = detection.get("directories") if isinstance(detection.get("directories"), dict) else {}
    file_rules = detection.get("files") if isinstance(detection.get("files"), dict) else {}
    matched = False
    if detection_group_matches(dir_rules.get("any"), directories, all_required=False):
        matched = True
    if detection_group_matches(dir_rules.get("all"), directories, all_required=True):
        matched = True
    if detection_group_matches(file_rules.get("any"), rel_files, all_required=False):
        matched = True
    if detection_group_matches(file_rules.get("all"), rel_files, all_required=True):
        matched = True
    contains_rules = detection.get("file_contains") if isinstance(detection.get("file_contains"), list) else []
    for rule in contains_rules:
        if not isinstance(rule, dict) or not rule.get("pattern"):
            continue
        candidate_patterns = list_value(rule.get("files")) or ["*"]
        candidate_files = [path for path in files if any(path_matches_pattern(rel(path, project_root), pattern) for pattern in candidate_patterns)]
        for path in candidate_files[:200]:
            text = path.read_text(encoding="utf-8", errors="ignore")[:200000]
            try:
                if re.search(str(rule["pattern"]), text):
                    matched = True
                    break
            except re.error:
                if str(rule["pattern"]) in text:
                    matched = True
                    break
        if matched:
            break
    return matched


def platform_ids_from_detection_rules(workplace_manifest: Path | None, project_root: Path) -> list[str]:
    matched: list[str] = []
    for contract_id, entry in platform_contract_manifest_index(workplace_manifest, project_root).items():
        if platform_detection_matches(entry["contract"], project_root):
            matched.append(contract_id.removeprefix("platform."))
    return sorted(set(matched))


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


def project_runtime_launcher_files(flow_root: Path) -> dict[Path, str]:
    launcher_py = r'''#!/usr/bin/env python3
"""Project-local ProcessForge launcher.

This file lives under .pf/runtime/ and may read private local paths from
.pf/process-forge.local.yaml. Public project files should use `pf` or this
launcher without exposing resolved local paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def project_marker(path: Path) -> bool:
    return (path / ".pf" / "process-forge.local.yaml").is_file()


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    if project_marker(current):
        return current
    script_path = Path(__file__).resolve()
    script_project = script_path.parents[3] if len(script_path.parents) > 3 else None
    if script_project and project_marker(script_project):
        return script_project
    for candidate in [current, *current.parents, *script_path.parents]:
        if project_marker(candidate):
            return candidate
    return None


def yaml_scalar(text: str, key: str) -> str | None:
    prefix = key + ":"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped[len(prefix) :].strip()
            if value in {"", "null", "None", "~"}:
                return None
            return value.strip("'\"")
    return None


def resolve_path(base: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def exec_args(args: list[str]) -> list[str]:
    if os.name != "nt":
        return args
    return [subprocess.list2cmdline([arg]) for arg in args]


def exec_processforge(cli: Path, argv: list[str]) -> int:
    args = exec_args([sys.executable, str(cli), *argv])
    if os.name == "nt":
        return os.spawnv(os.P_WAIT, sys.executable, args)
    os.execv(sys.executable, args)
    return 2


def distribution_from_workplace(workplace_manifest: Path) -> Path | None:
    registry = workplace_manifest.parent / "registries" / "distributions.yaml"
    if not registry.is_file():
        return None
    lines = registry.read_text(encoding="utf-8", errors="replace").splitlines()
    in_processforge = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("id:"):
            in_processforge = stripped.split(":", 1)[1].strip().strip("'\"") == "processforge"
        elif in_processforge and stripped.startswith("path:"):
            raw = stripped.split(":", 1)[1].strip().strip("'\"")
            raw = raw.replace("${PF_WORKPLACE}", str(workplace_manifest.parent))
            return resolve_path(workplace_manifest.parent, raw)
    return None


def distribution_root(project_root: Path) -> Path | None:
    env_home = os.environ.get("PROCESSFORGE_HOME")
    local_manifest = project_root / ".pf" / "process-forge.local.yaml"
    if local_manifest.is_file():
        text = local_manifest.read_text(encoding="utf-8", errors="replace")
        override = yaml_scalar(text, "distribution_override")
        if override:
            return resolve_path(local_manifest.parent, override)
        workplace_raw = yaml_scalar(text, "manifest")
        if workplace_raw:
            workplace = resolve_path(local_manifest.parent, workplace_raw)
            found = distribution_from_workplace(workplace)
            if found:
                return found
    if env_home:
        return Path(env_home).expanduser().resolve()
    return None


def main(argv: list[str]) -> int:
    project_root = find_project_root(Path.cwd())
    if project_root is None:
        message = """FAIL: ProcessForge project root not found.

Fix:
  Run this launcher from a ProcessForge project root, pass --project-root to the command, or rerun project-onboard."""
        print(message, file=sys.stderr)
        return 1
    distribution = distribution_root(project_root)
    if not distribution:
        message = """FAIL: ProcessForge distribution not found.

Fix:
  Set PROCESSFORGE_HOME to the ProcessForge distribution root, or rerun project-onboard from the distribution."""
        print(message, file=sys.stderr)
        return 1
    cli = distribution / "tools" / "processforge.py"
    if not cli.is_file():
        message = f"""FAIL: ProcessForge CLI not found under distribution root: {distribution}

Fix:
  Check PROCESSFORGE_HOME or rerun project-onboard so .pf/process-forge.local.yaml points to a valid distribution."""
        print(message, file=sys.stderr)
        return 1
    try:
        return exec_processforge(cli, argv)
    except OSError as exc:
        print("FAIL: could not exec ProcessForge CLI", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
    launcher_sh = """#!/usr/bin/env sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/pf.py" "$@"
fi
exec python "$SCRIPT_DIR/pf.py" "$@"
"""
    launcher_bat = """@echo off
set SCRIPT_DIR=%~dp0
py -3 "%SCRIPT_DIR%pf.py" %*
if errorlevel 9009 python "%SCRIPT_DIR%pf.py" %*
"""
    return {
        flow_root / "runtime" / "bin" / "pf.py": launcher_py,
        flow_root / "runtime" / "bin" / "pf": launcher_sh,
        flow_root / "runtime" / "bin" / "pf.bat": launcher_bat,
    }


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


def seed_platform_contract_paths(distribution_root: Path | None = None) -> list[Path]:
    root = distribution_root or ROOT
    seed_root = root / "seeds" / "platform-contracts"
    if not seed_root.is_dir():
        return []
    return sorted([*seed_root.glob("*.yaml"), *seed_root.glob("*.yml")])


def project_platform_contract_paths(project_root: Path | None) -> list[Path]:
    if not project_root:
        return []
    candidates: list[Path] = []
    for root in [project_root / PROJECT_FLOW_ROOT / "platform-contracts", project_root / "platform-contracts"]:
        if root.is_dir():
            candidates.extend(sorted(root.glob("*.yaml")))
            candidates.extend(sorted(root.glob("*.yml")))
            candidates.extend(sorted(root.glob("*/platform-contract.yaml")))
            candidates.extend(sorted(root.glob("*/platform-contract.yml")))
    return candidates


def platform_contract_record(path: Path, source: str, registry_entry: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]] | None:
    data = load_yaml_document(path)
    if not data or yaml_error(data):
        return None
    contract_id = data.get("id")
    if not contract_id:
        return None
    normalized_id = platform_contract_id(str(contract_id))
    return normalized_id, {"contract": data, "path": path, "source": source, "status": "available", "registry_entry": registry_entry}


def platform_contract_manifest_index(workplace_manifest: Path | None, project_root: Path | None = None) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in seed_platform_contract_paths(ROOT):
        record = platform_contract_record(path, "seed")
        if record:
            index[record[0]] = record[1]
    for path in project_platform_contract_paths(project_root):
        record = platform_contract_record(path, "project")
        if record:
            index[record[0]] = record[1]
    registry = load_workplace_registry(workplace_manifest, "platforms", "platforms.yaml")
    entries = registry.get("platforms") if isinstance(registry, dict) else None
    if isinstance(entries, list) and workplace_manifest:
        for entry in entries:
            if not isinstance(entry, dict) or str(entry.get("status", "available")) in {"missing", "disabled"}:
                continue
            raw_path = entry.get("path")
            if not raw_path:
                continue
            path = resolve_registry_relative_path(workplace_manifest.parent, str(raw_path), workplace_manifest)
            record = platform_contract_record(path, "workplace", entry)
            if record:
                index[record[0]] = record[1]
    return index


def resolve_registry_relative_path(base: Path, raw_path: str, workplace_manifest: Path | None = None) -> Path:
    constants = load_workplace_path_constants(workplace_manifest, base) if workplace_manifest else load_workplace_path_constants(None, base)
    resolution = resolve_path_with_constants(raw_path, base, constants)
    return path_resolution_to_path(resolution)


def load_platform_contract(workplace_manifest: Path | None, contract_id: str, project_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any] | None, str, str]:
    normalized_id = platform_contract_id(contract_id)
    entry = platform_contract_manifest_index(workplace_manifest, project_root).get(normalized_id)
    if entry:
        return entry["contract"], entry.get("registry_entry"), str(entry.get("status", "available")), str(entry.get("source", "manifest"))
    registry_entry = platform_contract_registry_entry(workplace_manifest, normalized_id)
    if registry_entry and str(registry_entry.get("status", "available")) in {"missing", "disabled"}:
        return {"id": normalized_id, "requires": {}, "includes": {}}, registry_entry, str(registry_entry.get("status")), "registry"
    return {"id": normalized_id, "requires": {}, "includes": {}}, registry_entry, "missing", "missing"


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


def normalize_platform_ref(value: Any, *, default_required: bool = True) -> dict[str, Any] | None:
    if isinstance(value, str):
        ref_id = value.strip()
        if not ref_id:
            return None
        return {"id": platform_contract_id(ref_id), "required": default_required}
    if isinstance(value, dict):
        raw_id = value.get("id") or value.get("platform") or value.get("package_id")
        if not raw_id:
            return None
        record: dict[str, Any] = {"id": platform_contract_id(str(raw_id)), "required": bool(value.get("required", default_required))}
        if value.get("version"):
            record["version"] = str(value["version"])
        return record
    return None


def platform_refs_from(value: Any, *, default_required: bool = True) -> list[dict[str, Any]]:
    values = value if isinstance(value, list) else ([value] if value else [])
    refs: list[dict[str, Any]] = []
    for item in values:
        ref = normalize_platform_ref(item, default_required=default_required)
        if ref:
            refs.append(ref)
    return refs


def contract_extends(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return platform_refs_from(contract.get("extends"), default_required=True)


def contract_required_platforms(contract: dict[str, Any]) -> list[dict[str, Any]]:
    requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
    return platform_refs_from(requires.get("platforms"), default_required=True)


def contract_required_capabilities(contract: dict[str, Any]) -> list[str]:
    requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
    return sorted(set(list_value(contract.get("capabilities"))).union(list_value(requires.get("capabilities"))))


def contract_required_items(contract: dict[str, Any], key: str) -> list[str]:
    requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
    includes = contract.get("includes", {}) if isinstance(contract.get("includes"), dict) else {}
    required = set(list_value(requires.get(key)))
    for item in includes.get(key, []) if isinstance(includes.get(key), list) else []:
        if isinstance(item, dict) and item.get("required") is True:
            item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
            if item_id:
                required.add(str(item_id))
    return sorted(required)


def contract_includes(contract: dict[str, Any], key: str) -> list[str]:
    includes = contract.get("includes", {}) if isinstance(contract.get("includes"), dict) else {}
    output: list[str] = []
    value = includes.get(key)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                output.append(item)
            elif isinstance(item, dict) and item.get("required") is not True:
                item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
                if item_id:
                    output.append(str(item_id))
    return sorted(set(output))


def package_dependency_ids(manifest: dict[str, Any]) -> list[str]:
    dependencies = set(list_value(manifest.get("dependencies")))
    requires = manifest.get("requires") if isinstance(manifest.get("requires"), dict) else {}
    dependencies.update(list_value(requires.get("knowledge_packages")))
    return sorted(item for item in dependencies if item)


def merge_id_list(target: dict[str, str], values: list[str], owner: str, conflicts: list[dict[str, Any]]) -> None:
    for value in values:
        if value not in target:
            target[value] = owner
        elif target[value] != owner:
            conflicts.append({"id": value, "first_owner": target[value], "second_owner": owner, "resolution": "dedupe"})


def resolve_platform_contracts(workplace_manifest: Path | None, platform_ids: list[str], project_root: Path | None = None) -> dict[str, Any]:
    contracts_by_id: dict[str, dict[str, Any]] = {}
    platform_stack: list[dict[str, Any]] = []
    required_capabilities: set[str] = set()
    required_knowledge_packages: dict[str, str] = {}
    recommended_knowledge_packages: dict[str, str] = {}
    required_tools: dict[str, str] = {}
    recommended_tools: dict[str, str] = {}
    required_mcp: dict[str, str] = {}
    recommended_mcp: dict[str, str] = {}
    required_templates: dict[str, str] = {}
    recommended_templates: dict[str, str] = {}
    missing_required_contracts: list[str] = []
    circular_platforms: list[str] = []
    dependency_conflicts: list[dict[str, Any]] = []
    resource_conflicts: list[dict[str, Any]] = []
    resolved: set[str] = set()
    resolving: list[str] = []

    def resolve_one(raw_platform_id: str, *, relation: str = "selected", inherited_by: str | None = None, include_resources: bool = True, required: bool = True) -> None:
        contract_id = platform_contract_id(raw_platform_id)
        if contract_id in resolving:
            cycle = " -> ".join([*resolving[resolving.index(contract_id):], contract_id])
            circular_platforms.append(cycle)
            return
        if contract_id in resolved:
            return
        resolving.append(contract_id)
        contract, entry, status, source = load_platform_contract(workplace_manifest, contract_id, project_root)
        extends_refs = contract_extends(contract)
        required_platform_refs = contract_required_platforms(contract)
        for ref in extends_refs:
            if ref["id"] in resolving:
                cycle = " -> ".join([*resolving[resolving.index(ref["id"]):], ref["id"]])
                circular_platforms.append(cycle)
                continue
            resolve_one(ref["id"], relation="extends", inherited_by=contract_id, include_resources=True, required=bool(ref.get("required", True)))
        for ref in required_platform_refs:
            if ref["id"] in resolving:
                cycle = " -> ".join([*resolving[resolving.index(ref["id"]):], ref["id"]])
                circular_platforms.append(cycle)
                continue
            resolve_one(ref["id"], relation="requires.platforms", inherited_by=contract_id, include_resources=False, required=bool(ref.get("required", True)))
        if status != "available" and required:
            missing_required_contracts.append(contract_id)
        platform_record = {
            "id": contract_id,
            "platform": contract_id.removeprefix("platform."),
            "source": source,
            "status": "available" if status == "available" else "missing",
            "relation": relation,
            "required": required,
            "inherited_by": inherited_by,
            "extends": [ref["id"] for ref in extends_refs],
            "requires_platforms": [ref["id"] for ref in required_platform_refs],
        }
        platform_stack.append(platform_record)
        if include_resources:
            required_capabilities.update(contract_required_capabilities(contract))
            owner = contract_id
            merge_id_list(required_knowledge_packages, contract_required_items(contract, "knowledge_packages"), owner, resource_conflicts)
            merge_id_list(recommended_knowledge_packages, contract_includes(contract, "knowledge_packages"), owner, resource_conflicts)
            merge_id_list(required_tools, contract_required_items(contract, "tools"), owner, resource_conflicts)
            merge_id_list(recommended_tools, contract_includes(contract, "tools"), owner, resource_conflicts)
            merge_id_list(required_mcp, contract_required_items(contract, "mcp"), owner, resource_conflicts)
            merge_id_list(recommended_mcp, contract_includes(contract, "mcp"), owner, resource_conflicts)
            merge_id_list(required_templates, contract_required_items(contract, "templates"), owner, resource_conflicts)
            merge_id_list(recommended_templates, contract_includes(contract, "templates"), owner, resource_conflicts)
        contracts_by_id[contract_id] = {
            "id": contract_id,
            "platform": contract_id.removeprefix("platform."),
            "source": source,
            "status": "available" if status == "available" else "missing",
            "registry_entry": str(entry.get("id")) if isinstance(entry, dict) and entry.get("id") else None,
            "required_contract": required,
            "relation": relation,
            "inherited_by": inherited_by,
            "extends": [ref["id"] for ref in extends_refs],
            "requires_platforms": [ref["id"] for ref in required_platform_refs],
            "required_capabilities": sorted(contract_required_capabilities(contract)),
            "required": {
                "knowledge_packages": sorted(contract_required_items(contract, "knowledge_packages")),
                "tools": sorted(contract_required_items(contract, "tools")),
                "mcp": sorted(contract_required_items(contract, "mcp")),
                "templates": sorted(contract_required_items(contract, "templates")),
            },
            "recommended": {
                "knowledge_packages": sorted(contract_includes(contract, "knowledge_packages")),
                "tools": sorted(contract_includes(contract, "tools")),
                "mcp": sorted(contract_includes(contract, "mcp")),
                "templates": sorted(contract_includes(contract, "templates")),
            },
        }
        resolving.pop()
        resolved.add(contract_id)

    for platform_id in platform_ids:
        resolve_one(platform_id)

    package_index_root = project_root or (workplace_manifest.parent if workplace_manifest and workplace_manifest.is_file() else ROOT)
    package_index = package_manifest_index(package_index_root, ROOT, workplace_manifest)
    dependency_queue = list(required_knowledge_packages)
    while dependency_queue:
        package_id = dependency_queue.pop(0)
        manifest = package_index.get(package_id)
        if not isinstance(manifest, dict):
            continue
        for dependency_id in package_dependency_ids(manifest):
            if dependency_id not in required_knowledge_packages:
                required_knowledge_packages[dependency_id] = f"package:{package_id}"
                dependency_queue.append(dependency_id)

    required_knowledge_ids = set(required_knowledge_packages)
    recommended_knowledge_ids = set(recommended_knowledge_packages) - required_knowledge_ids
    required_tool_ids = set(required_tools)
    recommended_tool_ids = set(recommended_tools) - required_tool_ids
    required_mcp_ids = set(required_mcp)
    recommended_mcp_ids = set(recommended_mcp) - required_mcp_ids
    required_template_ids = set(required_templates)
    recommended_template_ids = set(recommended_templates) - required_template_ids
    return {
        "contracts": [contracts_by_id[item["id"]] for item in platform_stack if item["id"] in contracts_by_id],
        "platform_stack": platform_stack,
        "missing_required_contracts": sorted(set(missing_required_contracts)),
        "circular_platforms": sorted(set(circular_platforms)),
        "dependency_conflicts": dependency_conflicts,
        "resource_conflicts": resource_conflicts,
        "required_capabilities": sorted(required_capabilities),
        "required_knowledge_packages": sorted(required_knowledge_ids),
        "recommended_knowledge_packages": sorted(recommended_knowledge_ids),
        "knowledge_packages": sorted(required_knowledge_ids.union(recommended_knowledge_ids)),
        "required_tools": sorted(required_tool_ids),
        "recommended_tools": sorted(recommended_tool_ids),
        "tools": sorted(required_tool_ids.union(recommended_tool_ids)),
        "required_mcp": sorted(required_mcp_ids),
        "recommended_mcp": sorted(recommended_mcp_ids),
        "mcp": sorted(required_mcp_ids.union(recommended_mcp_ids)),
        "required_templates": sorted(required_template_ids),
        "recommended_templates": sorted(recommended_template_ids),
        "templates": sorted(required_template_ids.union(recommended_template_ids)),
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


def platform_resource_findings(workplace_manifest: Path | None, resolved: dict[str, Any], package_index_ids: set[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    package_ids = registry_ids(load_workplace_registry(workplace_manifest, "package_roots", "package-roots.yaml"), "package_roots")
    if workplace_manifest and workplace_manifest.is_file():
        package_ids = package_ids.union(set(package_manifest_index(workplace_manifest.parent, None, workplace_manifest)) - {"__duplicates__"})
    if package_index_ids:
        package_ids = package_ids.union(package_index_ids)
    tool_ids = registry_ids(load_workplace_registry(workplace_manifest, "tools", "tools.yaml"), "tools")
    mcp_ids = registry_ids(load_workplace_registry(workplace_manifest, "mcp", "mcp.yaml"), "mcp_servers")
    templates_registry = load_workplace_registry(workplace_manifest, "templates", "templates.yaml")
    template_ids = registry_ids(templates_registry, "template_roots").union(registry_ids(templates_registry, "templates"))
    required_missing: list[dict[str, Any]] = []
    recommended_missing: list[dict[str, Any]] = []

    for group, available, collection in [
        ("knowledge_package", package_ids, resolved.get("required_knowledge_packages", [])),
        ("tool", tool_ids, resolved.get("required_tools", [])),
        ("mcp", mcp_ids, resolved.get("required_mcp", [])),
        ("template", template_ids, resolved.get("required_templates", [])),
    ]:
        for item in collection:
            if item not in available:
                required_missing.append({"kind": group, "id": item, "status": "missing", "severity": "fail", "requirement": "required"})

    for group, available, collection in [
        ("knowledge_package", package_ids, resolved.get("recommended_knowledge_packages", [])),
        ("tool", tool_ids, resolved.get("recommended_tools", [])),
        ("mcp", mcp_ids, resolved.get("recommended_mcp", [])),
        ("template", template_ids, resolved.get("recommended_templates", [])),
    ]:
        for item in collection:
            if item not in available:
                recommended_missing.append({"kind": group, "id": item, "status": "missing", "severity": "warn", "requirement": "recommended"})
    return required_missing, recommended_missing


def optional_platform_resource_warnings(workplace_manifest: Path | None, resolved: dict[str, Any], package_index_ids: set[str] | None = None) -> list[dict[str, Any]]:
    _required_missing, recommended_missing = platform_resource_findings(workplace_manifest, resolved, package_index_ids)
    return recommended_missing


def match_global_resources(workplace_manifest: Path, detected: dict[str, Any], required: list[str], optional: list[str]) -> dict[str, list[str]]:
    tools_text = registry_text(workplace_manifest, "tools.yaml")
    mcp_text = registry_text(workplace_manifest, "mcp.yaml")
    templates_text = registry_text(workplace_manifest, "templates.yaml")
    package_text = registry_text(workplace_manifest, "package-roots.yaml")

    available_platform_ids = set(platform_contract_manifest_index(workplace_manifest))
    available_platform_ids.update(item.removeprefix("platform.") for item in list(available_platform_ids))
    matched_platforms = [item for item in detected["platforms"] if item and (item in available_platform_ids or platform_contract_id(item) in available_platform_ids)]
    missing_platforms = [item for item in detected["platforms"] if item and item not in matched_platforms]
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
    detected["platforms"] = selected_project_platforms(detected, answers, defaults["type"], workplace_manifest, project_root)
    mode = project_mode(project_root, answers)
    required = answers.get("required_capabilities") if isinstance(answers.get("required_capabilities"), list) else []
    optional = answers.get("optional_capabilities") if isinstance(answers.get("optional_capabilities"), list) else []
    required = required or ["repository.read", "markdown.editing"]
    optional = optional or ["repository.symbol_analysis", "official_documentation"]
    platform_resolution = resolve_platform_contracts(workplace_manifest, detected["platforms"], project_root=project_root)
    required_platform_missing, recommended_platform_missing = platform_resource_findings(workplace_manifest, platform_resolution)
    required = sorted(set(required).union(platform_resolution["required_capabilities"]))
    matches = match_global_resources(workplace_manifest, detected, required, optional)
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
        "detected": {
            "languages": detected["languages"],
            "platforms": detected["platforms"],
            "project_kind": detected["project_kind"],
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
            "runtime": "runtime",
            "hooks": "hooks.yaml",
        },
        "knowledge_stack": knowledge_stack,
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
        "process_forge": {"distribution_override": str(ROOT.resolve())},
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

    first_assignment = {
        "schema_version": 1,
        "id": "first-assignment",
        "title": "Verify ProcessForge project onboarding",
        "process": "project-onboarding",
        "status": "open",
        "objective": "Verify that this project is connected to ProcessForge and ready for future assignment work.",
        "tasks": [
            "Read .pf/AGENTS.md",
            "Read .pf/contexts/project-context.snapshot.yaml",
            "Run doctor-project",
            "Review .pf/hooks.yaml",
            "Confirm the first working process for this project",
            "Create .pf/artifacts/first-assignment-readiness-note.md",
        ],
        "expected_artifacts": [
            ".pf/artifacts/first-assignment-readiness-note.md",
        ],
    }

    start_agent_here = f"""# Start Agent Here

You are working inside a ProcessForge-enabled project.

## First Steps

1. Read `.pf/AGENTS.md`.
2. Read `.pf/contexts/project-context.snapshot.yaml`.
3. Read the active assignment in `.pf/assignments/`.
4. Run:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

If `pf` is available in PATH, this short form is also acceptable:

```bash
pf doctor-project --project-root .
```

5. If doctor fails, report the failures and propose safe fixes.
6. Do not expose local absolute paths from `.pf/process-forge.local.yaml`.
7. Use ProcessForge artifacts, reviews, and handoffs for outputs.
8. Do not call a distribution-local CLI path from this project root unless this project is the ProcessForge distribution itself.

## Current Assignment

- File: `.pf/assignments/first-assignment.yaml`
- Goal: Verify ProcessForge project onboarding for `{defaults["id"]}`.

## Useful Commands

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py assignment-capsule --project-root . --assignment .pf/assignments/first-assignment.yaml
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type project.onboarding.completed --dry-run
```
"""

    onboarding_report = f"""# Project Onboarding Report

## Status

applied

## Project

- id: {defaults["id"]}
- name: {defaults["name"]}
- type: {defaults["type"]}

## Process Boundary

Project onboarding creates only the project-local `.pf/` flow root and links it to an existing workplace. It does not recreate the workplace, copy global packages into the project, or write local absolute paths to public files.

## Created First-Run Files

- .pf/START_AGENT_HERE.md
- .pf/assignments/first-assignment.yaml
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
- Review the generated first assignment before assigning work.
"""

    onboarding_handoff = f"""# Handoff: project-onboarding -> first-assignment

Objective:
Connect `{defaults["id"]}` to ProcessForge and prepare the first assignment.

Current status:
Project onboarding files were generated.

Input artifacts:
- .pf/process-forge.yaml
- .pf/process-forge.local.yaml
- .pf/contexts/project-context.snapshot.yaml
- .pf/START_AGENT_HERE.md
- .pf/assignments/first-assignment.yaml

Files changed:
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
Start `.pf/assignments/first-assignment.yaml`.
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
        flow_root / "AGENTS.md": agents,
        flow_root / "START_AGENT_HERE.md": start_agent_here,
        flow_root / "process-forge.yaml": dump_yaml(public_manifest),
        flow_root / "process-forge.local.yaml": dump_yaml(local_manifest),
        flow_root / "hooks.yaml": dump_yaml(hooks),
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
    files.update(project_runtime_launcher_files(flow_root))
    return files


def finalize_project_onboarding_doctor_artifacts(project_root: Path, status: int, output: str) -> None:
    flow_root = project_root / PROJECT_FLOW_ROOT
    result = "pass" if status == 0 else "fail"
    report = flow_root / "artifacts" / "project-onboarding-report.md"
    existing = report.read_text(encoding="utf-8", errors="replace") if report.is_file() else "# Project Onboarding Report\n"
    content = existing.rstrip() + f"""

## Doctor Status

{result}

## Doctor Output

```text
{output.rstrip()}
```

## Fix Hints

{"- None required." if status == 0 else "- Resolve the FAIL lines above, then rerun `pf doctor-project --project-root .`."}
"""
    write_file(report, content, force=True)


def command_init_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    workplace = Path(args.workplace).expanduser().resolve()
    if workplace.is_dir():
        workplace = workplace / "workplace.yaml"
    answers = load_answers(Path(args.answers).expanduser().resolve() if args.answers else None)
    project_type = getattr(args, "project_type", None)
    if project_type:
        project_answers = answers.get("project") if isinstance(answers.get("project"), dict) else {}
        project_answers["type"] = project_type
        answers["project"] = project_answers
    if args.apply and not workplace.is_file() and not args.allow_missing_workplace:
        raise SystemExit(
            f"""FAIL: workplace manifest is required before project onboarding.

Why:
  Project onboarding links a project to an existing ProcessForge workplace.

Fix:
  python bin/pf.py workplace-init --workplace {workplace.parent} --apply
  python bin/pf.py project-onboard --project-root {project_root} --workplace {workplace.parent} --type {project_type or '<project-type>'} --apply"""
        )
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
    emit_process_event(project_root, "project.onboarding.started", process_id="project-onboarding", process_version="1.0.0", payload={"command": getattr(args, "command", "init-project")})
    results = [write_file(path, content, force=args.force) for path, content in files.items()]
    results.append(append_gitignore_entries(project_root / ".gitignore", PROJECT_PRIVATE_GITIGNORE, force=args.force))
    emit_process_event(project_root, "project.flow_root.created", process_id="project-onboarding", process_version="1.0.0", payload={"flow_root": PROJECT_FLOW_ROOT})
    emit_process_event(project_root, "project.platform.detected", process_id="project-onboarding", process_version="1.0.0", payload={"project_type": project_type or "auto"})
    snapshot_status, snapshot_paths, _snapshot, _old_reasons = write_project_context_snapshot_outputs(project_root)
    emit_process_event(project_root, "project.snapshot.refreshed", process_id="project-onboarding", process_version="1.0.0", payload={"status": snapshot_status, "paths": {key: rel(value, project_root) for key, value in snapshot_paths.items()}})
    emit_process_event(project_root, "launcher.project_runtime.created", process_id="project-onboarding", process_version="1.0.0", payload={"path": ".pf/runtime/bin/pf.py"})
    emit_process_event(project_root, "agent.start_prompt.generated", process_id="project-onboarding", process_version="1.0.0", payload={"path": ".pf/START_AGENT_HERE.md"})
    emit_process_event(project_root, "assignment.created", process_id="project-onboarding", process_version="1.0.0", assignment_id_value="first-assignment", assignment_path=".pf/assignments/first-assignment.yaml", payload={"path": ".pf/assignments/first-assignment.yaml"})
    doctor_status, doctor_output = run_command_capture(command_doctor_project, argparse.Namespace(project_root=str(project_root)))
    print(doctor_output, end="")
    finalize_project_onboarding_doctor_artifacts(project_root, doctor_status, doctor_output)
    emit_process_event(
        project_root,
        "project.doctor.passed" if doctor_status == 0 else "project.doctor.failed",
        process_id="project-onboarding",
        process_version="1.0.0",
        payload={"status": "pass" if doctor_status == 0 else "fail"},
    )
    emit_process_event(project_root, "project.onboarding.completed", process_id="project-onboarding", process_version="1.0.0", payload={"files": [rel(result.target, project_root) for result in results], "doctor_status": doctor_status})
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, project_root)}")
    for path in snapshot_paths.values():
        print(f"WROTE: {rel(path, project_root)}")
    return doctor_status


def default_start_agent_here(project_root: Path) -> str:
    assignment_path = locate_flow_root(project_root) / "assignments" / "first-assignment.yaml"
    assignment_rel = rel(assignment_path, project_root) if assignment_path.is_file() else ".pf/assignments/"
    run_block = start_agent_run_block(project_root)
    return f"""# Start Agent Here

You are working inside a ProcessForge-enabled project.

## First Steps

1. Read `.pf/AGENTS.md`.
2. Read `.pf/contexts/project-context.snapshot.yaml`.
3. Read the active assignment in `.pf/assignments/`.
4. Run:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

If `pf` is available in PATH, this short form is also acceptable:

```bash
pf doctor-project --project-root .
```

5. If doctor fails, report the failures and propose safe fixes.
6. Do not expose local absolute paths from `.pf/process-forge.local.yaml`.
7. Use ProcessForge artifacts, reviews, and handoffs for outputs.
8. Do not call a distribution-local CLI path from this project root unless this project is the ProcessForge distribution itself.

## Current Assignment

- File: `{assignment_rel}`
- Goal: Verify this project is ready for ProcessForge assignment work.

{run_block}
"""


def start_agent_run_block(project_root: Path) -> str:
    active_runs = active_run_ids(project_root)
    if active_runs:
        return f"""## Active Run

Current ProcessForge run:

```bash
python .pf/runtime/bin/pf.py run-status --project-root . --run {active_runs[0]}
```

Work loop:

```bash
python .pf/runtime/bin/pf.py task-list --project-root . --run {active_runs[0]}
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run {active_runs[0]} --apply
```
"""
    return """## Create A Run

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
```

## Create A Process

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --process <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --process <process-id>
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
```
"""


def refresh_start_agent_run_block(project_root: Path, text: str) -> str:
    block = start_agent_run_block(project_root).rstrip() + "\n"
    markers = ["## Active Run", "## Create A Run"]
    positions = [text.find(marker) for marker in markers if marker in text]
    if positions:
        start = min(positions)
        return text[:start].rstrip() + "\n\n" + block
    return text.rstrip() + "\n\n" + block


def command_agent_start_prompt(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = require_flow_root(project_root)
    target = flow_root / "START_AGENT_HERE.md"
    if target.is_file() and "python tools/processforge.py" not in target.read_text(encoding="utf-8", errors="replace"):
        text = refresh_start_agent_run_block(project_root, target.read_text(encoding="utf-8", errors="replace"))
        target.write_text(ensure_trailing_newline(text), encoding="utf-8")
    else:
        text = default_start_agent_here(project_root)
        target.write_text(ensure_trailing_newline(text), encoding="utf-8")
        emit_process_event(project_root, "artifact.created", payload={"path": rel(target, project_root)})
        emit_process_event(project_root, "agent.start_prompt.generated", payload={"path": rel(target, project_root)})
    print(text.rstrip())
    return 0


def command_first_run(args: argparse.Namespace) -> int:
    workplace_args = argparse.Namespace(
        command="workplace-init",
        root=args.workplace,
        answers=None,
        dry_run=args.dry_run,
        apply=args.apply,
        force=args.force,
        interactive=args.interactive,
    )
    project_args = argparse.Namespace(
        command="project-onboard",
        project_root=args.project_root,
        workplace=args.workplace,
        project_type=args.project_type,
        answers=None,
        dry_run=args.dry_run,
        apply=args.apply,
        force=args.force,
        interactive=args.interactive,
        allow_missing_workplace=False,
    )
    workplace_status = command_init_workplace(workplace_args)
    if workplace_status != 0:
        return workplace_status
    return command_init_project(project_args)


RELEASE_DIRS = ["docs", "schemas", "processes", "packages", "templates", "prompts", "examples", "policies", "seeds", "bin", "tools", "updates"]
RELEASE_ROOT_FILES = ["README.md", "README.ru.md", "QUICKSTART.md", "QUICKSTART.ru.md", "CHANGELOG.md", "LICENSE", "VERSION", ".gitignore", ".processforge-releaseignore"]
RELEASE_PF_PUBLIC_FILES = [".pf/AGENTS.md", ".pf/process-forge.yaml", ".pf/hooks.yaml", ".pf/artifacts/checksum-inventory.sha256"]
RELEASE_REQUIRED_PATHS = [
    "README.md",
    "README.ru.md",
    "QUICKSTART.md",
    "QUICKSTART.ru.md",
    "CHANGELOG.md",
    "LICENSE",
    "AGENTS.md",
    ".gitignore",
    ".processforge-releaseignore",
    ".pf/AGENTS.md",
    ".pf/process-forge.yaml",
    ".pf/hooks.yaml",
    ".pf/artifacts/checksum-inventory.sha256",
    "bin/pf.py",
    "bin/pf",
    "bin/pf.bat",
    "tools",
    "schemas",
    "templates",
    "processes",
    "prompts",
    "docs",
    "examples",
    "policies",
    "seeds",
]
RELEASE_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".sh", ".bat"}
RELEASE_FORBIDDEN_DIR_PARTS = {
    ".git",
    ".idea",
    ".serena",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "private-notes",
}
RELEASE_FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".ps1", ".zip"}
RELEASE_GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
RELEASE_GENERATED_SUFFIXES = {".pyc", ".pyo"}


def release_ignore_patterns(root: Path) -> list[str]:
    path = root / ".processforge-releaseignore"
    if not path.is_file():
        return []
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            patterns.append(value.replace("\\", "/"))
    return patterns


def release_ignore_match(rel_path: str, patterns: list[str]) -> bool:
    normalized = rel_path.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        candidate = pattern.lstrip("./")
        if candidate.startswith("/"):
            candidate = candidate[1:]
        if candidate.endswith("/"):
            prefix = candidate.rstrip("/")
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(normalized, candidate) or fnmatch.fnmatch(Path(normalized).name, candidate):
            return True
        if normalized == candidate:
            return True
    return False


def release_source_files(root: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for name in RELEASE_ROOT_FILES:
        path = root / name
        if path.is_file():
            files.append((name, path))
    root_agents = root / "AGENTS.md"
    pf_agents = root / ".pf" / "AGENTS.md"
    if root_agents.is_file():
        files.append(("AGENTS.md", root_agents))
    elif pf_agents.is_file():
        files.append(("AGENTS.md", pf_agents))
    for name in RELEASE_PF_PUBLIC_FILES:
        path = root / name
        if path.is_file():
            files.append((name, path))
    for dirname in RELEASE_DIRS:
        base = root / dirname
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file():
                    files.append((rel(path, root), path))
    return sorted(files, key=lambda item: item[0])


def release_path_is_forbidden(rel_path: str) -> str | None:
    parts = Path(rel_path).parts
    suffix = Path(rel_path).suffix.lower()
    for part in parts:
        if part in RELEASE_FORBIDDEN_DIR_PARTS:
            return f"forbidden directory part {part}"
    if suffix in RELEASE_FORBIDDEN_SUFFIXES:
        return f"forbidden suffix {suffix}"
    if rel_path.endswith(".env") or "/.env" in rel_path or Path(rel_path).name.startswith(".env."):
        return "private env file"
    if Path(rel_path).name == "process-forge.local.yaml" and not rel_path.startswith(("examples/", "templates/")):
        return "private local config"
    if "runtime/hooks/outbox" in rel_path or "hooks/outbox" in rel_path:
        return "hook outbox payload"
    if "runtime/chat/transcripts" in rel_path or "chat/transcripts" in rel_path:
        return "local chat transcript"
    return None


def forbidden_powershell_reference(text: str) -> bool:
    lower = text.lower()
    if ".ps1" in lower:
        return True
    for line in lower.splitlines():
        if "powershell" not in line:
            continue
        allowed = (
            "does not require powershell" in line
            or "powershell is not required" in line
            or "powershell not required" in line
            or "не требует powershell" in line
            or ("powershell" in line and "не требуется" in line)
            or ("powershell" in line and "не нужен" in line)
        )
        if not allowed:
            return True
    return False


def forbidden_base_technology_platform_reference(text: str) -> bool:
    policy = load_policy_document("platform-id-policy.yaml")
    discouraged = [
        str(item.get("id") if isinstance(item, dict) else item)
        for item in policy.get("discouraged_platform_ids", [])
        if (item.get("id") if isinstance(item, dict) else item)
    ]
    if not discouraged:
        return False
    allowed_markers = [
        "incorrect",
        "discouraged",
        "do not create",
        "not as platform contracts",
        "not platform contracts",
        "не создавайте",
        "а не как platform contracts",
        "не как platform contracts",
        "не являются platform contracts",
    ]
    lines = text.splitlines()
    for index, line in enumerate(lines):
        lower = line.lower()
        matched = [platform_id for platform_id in discouraged if platform_id.lower() in lower]
        if not matched:
            continue
        context = " ".join(lines[max(0, index - 2) : min(len(lines), index + 3)]).lower()
        allowed_discouraged_example = any(marker in context for marker in allowed_markers)
        if not allowed_discouraged_example:
            return True
    return False


def core_hardcode_violations(root: Path) -> list[str]:
    policy = load_policy_document("core-hardcode-policy.yaml", root)
    patterns = policy_entries(policy, "forbidden_core_patterns")
    if not patterns:
        return []
    targets = policy.get("targets")
    target_paths = [str(item) for item in targets] if isinstance(targets, list) else ["tools/processforge.py"]
    violations: list[str] = []
    for target in target_paths:
        path = root / target
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for entry in patterns:
            raw_pattern = entry.get("pattern") or entry.get("id")
            if not raw_pattern:
                continue
            try:
                matched = re.search(str(raw_pattern), text)
            except re.error:
                matched = str(raw_pattern) in text
            if matched:
                violations.append(f"{target}: {entry.get('id', raw_pattern)}")
    return violations


def public_support_policy_violations(archive_path: str, text: str, policy: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    group = archive_path.split("/", 1)[0]
    for entry in policy_entries(policy, "blocked_public_surface_patterns"):
        groups = [str(item) for item in as_list(entry.get("groups")) if item]
        if groups and group not in groups:
            continue
        allowed_paths = [str(item) for item in as_list(entry.get("allowed_paths")) if item]
        if any(fnmatch.fnmatch(archive_path, pattern) for pattern in allowed_paths):
            continue
        raw_pattern = entry.get("pattern") or entry.get("id")
        if not raw_pattern:
            continue
        flags = re.IGNORECASE if entry.get("case_insensitive", True) else 0
        try:
            matched = re.search(str(raw_pattern), text, flags)
        except re.error:
            matched = str(raw_pattern).lower() in text.lower() if flags else str(raw_pattern) in text
        if matched:
            violations.append(str(entry.get("message", entry.get("id", raw_pattern))))
    return violations


def release_required_path_exists(root: Path, archive_path: str) -> bool:
    if archive_path == "AGENTS.md":
        return (root / "AGENTS.md").is_file() or (root / ".pf" / "AGENTS.md").is_file()
    return (root / archive_path).exists()


def release_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    patterns = release_ignore_patterns(root)
    public_support_policy = load_policy_document("public-support-policy.yaml", root)
    public_support_policy_loaded = bool(policy_entries(public_support_policy, "blocked_public_surface_patterns"))
    public_support_policy_failed = False
    if not patterns:
        checks.append(
            check_with_hint(
                "FAIL",
                ".processforge-releaseignore missing or empty",
                "The release packer needs an explicit exclusion policy.",
                "create .processforge-releaseignore with runtime, private, cache, IDE, and archive exclusions",
            )
        )
    else:
        checks.append(check("PASS", ".processforge-releaseignore loaded"))

    for required in RELEASE_REQUIRED_PATHS:
        checks.append(
            check_with_hint(
                "FAIL",
                f"required release path missing: {required}",
                "The v0.1 archive contract lists this path as part of the public distribution.",
                f"restore or generate {required} before release-pack",
            )
            if not release_required_path_exists(root, required)
            else check("PASS", f"required release path present: {required}")
        )

    core_violations = core_hardcode_violations(root)
    if core_violations:
        for violation in core_violations:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"core platform hardcode policy violation: {violation}",
                    "ProcessForge core must load platform/package behavior from manifests and policies, not concrete platform ids in Python logic.",
                    "move the rule to a seed manifest or policy YAML and keep tools/processforge.py generic",
                )
            )
    elif load_policy_document("core-hardcode-policy.yaml", root):
        checks.append(
            check("PASS", "core platform hardcode policy passed")
        )

    for archive_path, path in release_source_files(root):
        if release_ignore_match(archive_path, patterns):
            continue
        forbidden = release_path_is_forbidden(archive_path)
        if forbidden:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{archive_path}: {forbidden}",
                    "Release archives must not contain runtime, private, cache, script-wrapper, or previous archive artifacts.",
                    "python tools/processforge.py clean --root . --release",
                )
            )
            continue
        if path.suffix.lower() in RELEASE_TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            release_text_group = archive_path.split("/", 1)[0]
            user_facing_text = release_text_group in {"README.md", "QUICKSTART.md", "CHANGELOG.md", "VERSION", "AGENTS.md", "docs", "prompts", "examples", "processes", "packages", "templates", "policies", "seeds"}
            if release_text_group in {"README.md", "QUICKSTART.md", "docs", "prompts", "examples"} and forbidden_powershell_reference(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public release text references PowerShell/.ps1",
                        "The v0.1 flow is Python-first and public docs should not direct users to unsupported wrappers.",
                        "replace the command with python bin/pf.py or python .pf/runtime/bin/pf.py",
                    )
                )
            if release_text_group in {"docs", "prompts", "examples", "templates", "packages", "processes"} and forbidden_base_technology_platform_reference(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public release text introduces a base-technology platform",
                        "Base languages and web technologies are knowledge packages and capabilities in v0.1, not platform contracts.",
                        "replace base-technology platform examples with docs.* knowledge package examples",
                    )
                )
            for violation in public_support_policy_violations(archive_path, text, public_support_policy):
                public_support_policy_failed = True
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: {violation}",
                        "Built-in seeds, examples, templates, packages, processes, and prompts must stay neutral unless a support pack is explicitly shipped.",
                        "replace the public sample with neutral ids or add an explicit policy exception for an intentional support pack",
                    )
                )
            if user_facing_text and not is_public_path_safe(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public text contains a private absolute path",
                        "Public release files must be portable across machines.",
                        "replace local filesystem values with path_ref, placeholders, or relative paths",
                    )
                )
            if user_facing_text and contains_secret_value(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public text appears to contain a secret value",
                        "Release files cannot contain credentials, tokens, or private keys.",
                        "remove the secret and keep only a named secret reference",
                    )
                )
    if public_support_policy_loaded and not public_support_policy_failed:
        checks.append(check("PASS", "public support surface policy passed"))
    if not any(item.level == "FAIL" for item in checks):
        checks.append(check("PASS", "release surface excludes runtime/private/cache/script/archive artifacts"))
    return checks


def command_release_check(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    return print_checks(release_checks(root))


def safe_remove_generated_path(path: Path, root: Path) -> bool:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        return False
    if path.is_dir() and path.name in RELEASE_GENERATED_DIRS:
        shutil.rmtree(path)
        return True
    if path.is_file() and path.suffix.lower() in RELEASE_GENERATED_SUFFIXES:
        path.unlink()
        return True
    return False


def command_clean(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not args.release:
        print("WARN: nothing selected; use --release to remove safe generated release artifacts")
        return 0
    removed: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.name in {".git", ".idea", ".serena"}:
            continue
        if safe_remove_generated_path(path, root):
            removed.append(rel(path, root))
    for item in removed:
        print(f"REMOVED: {item}")
    print(f"PASS: release cleanup removed {len(removed)} generated paths.")
    return 0


def command_examples_check(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    examples = root / "examples"
    checks: list[Check] = []
    checks.append(check("PASS" if examples.is_dir() else "FAIL", "examples/ found"))
    for required in ["first-run", "resource-authoring", "process-authoring"]:
        base = examples / required
        checks.append(check("PASS" if base.is_dir() else "FAIL", f"examples/{required}/ found"))
        readmes = list(base.rglob("README.md")) if base.is_dir() else []
        checks.append(check("PASS" if readmes else "FAIL", f"examples/{required}/ has README files"))
    if examples.is_dir():
        for path in sorted(examples.rglob("*")):
            rel_path = rel(path, root)
            if path.is_dir() and path.name in {"runtime", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{rel_path}: stale generated directory",
                        "Examples must remain source examples, not runtime output snapshots.",
                        "remove generated runtime/cache data from examples",
                    )
                )
            if not path.is_file():
                continue
            if path.suffix.lower() == ".ps1":
                checks.append(check_with_hint("FAIL", f"{rel_path}: unsupported .ps1 file", "The release is Python-first.", "replace with python bin/pf.py examples"))
            if path.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                if forbidden_powershell_reference(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: mentions PowerShell/.ps1", "Public examples should not mention removed wrappers.", "use python bin/pf.py or python .pf/runtime/bin/pf.py"))
                if forbidden_base_technology_platform_reference(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: introduces a base-technology platform", "Base technologies should be knowledge packages and capabilities, not platform contracts.", "use docs.php or docs.web.* package examples"))
                if not is_public_path_safe(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: contains private absolute path", "Examples must be portable.", "replace local paths with relative paths or placeholders"))
                if "python tools/processforge.py doctor-project --project-root" in text:
                    checks.append(
                        check_with_hint(
                            "FAIL",
                            f"{rel_path}: linked-project doctor command is misleading",
                            "Normal onboarded projects do not contain tools/processforge.py.",
                            "use python .pf/runtime/bin/pf.py doctor-project --project-root . inside linked projects",
                        )
                    )
    return print_checks(checks)


@dataclass
class ReleaseCommand:
    label: str
    command: list[str]
    timeout: int
    allow_warn: bool = False


def format_command(command: list[str]) -> str:
    return format_subprocess_command(command)


def run_release_command(label: str, command: list[str], cwd: Path, timeout: int, allow_warn: bool = False) -> tuple[str, int, str]:
    print(f"RUN {label}:")
    print(f"  {format_command(command)}")
    sys.stdout.flush()
    result = run_subprocess_command(command, cwd=cwd, timeout=timeout)
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.timed_out:
        return "FAIL", 124, f"timeout after {timeout}s\n{diagnostic_text(result)}"
    code = int(result.returncode or 0)
    if code == 0:
        return "PASS", 0, output
    if allow_warn:
        return "WARN", code, output
    return "FAIL", code, output


def print_release_command_output(label: str, status: str, code: int, output: str) -> None:
    print(f"{status} {label}")
    if status != "PASS":
        print(f"  exit: {code}")
        tail_lines = output.splitlines()[-30:]
        for line in tail_lines:
            print(f"  {line}")


def command_release_test(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    print("ProcessForge release-test")
    commands: list[ReleaseCommand] = [
        ReleaseCommand("py_compile", [sys.executable, "-m", "py_compile", str(root / "tools" / "processforge.py"), str(root / "bin" / "pf.py")], 30),
        ReleaseCommand("clean release artifacts", [sys.executable, str(root / "tools" / "processforge.py"), "clean", "--root", str(root), "--release"], 60),
        ReleaseCommand("schema validation", [sys.executable, str(root / "tools" / "validate-process-forge-schemas.py"), "--root", str(root)], 60),
        ReleaseCommand("public cleanliness", [sys.executable, str(root / "tools" / "validate-public-cleanliness.py"), "--root", str(root)], 60),
        ReleaseCommand("checksum", [sys.executable, str(root / "tools" / "validate-process-forge-checksums.py"), "--root", str(root), "--check"], 60),
        ReleaseCommand("smoke_first_run", [sys.executable, str(root / "tools" / "smoke_first_run.py")], 120),
        ReleaseCommand("smoke_resource_management", [sys.executable, str(root / "tools" / "smoke_resource_management.py")], 180),
        ReleaseCommand("smoke_resource_authoring", [sys.executable, str(root / "tools" / "smoke_resource_authoring_processes.py")], 180),
        ReleaseCommand("smoke_update_framework_readonly", [sys.executable, str(root / "tools" / "smoke_update_framework_readonly.py")], 180),
        ReleaseCommand("smoke_manifest_driven_platforms", [sys.executable, str(root / "tools" / "smoke_manifest_driven_platforms.py")], 180),
        ReleaseCommand("smoke_platform_inheritance", [sys.executable, str(root / "tools" / "smoke_platform_inheritance.py")], 180),
        ReleaseCommand("smoke_process_run_task_batch", [sys.executable, str(root / "tools" / "smoke_process_run_task_batch.py")], 180),
        ReleaseCommand("smoke_process_authoring", [sys.executable, str(root / "tools" / "smoke_process_authoring.py")], 180),
        ReleaseCommand("smoke_authoring_parity", [sys.executable, str(root / "tools" / "smoke_authoring_parity.py")], 180),
        ReleaseCommand("release-check", [sys.executable, str(root / "tools" / "processforge.py"), "release-check", "--root", str(root)], 60),
        ReleaseCommand("examples-check", [sys.executable, str(root / "tools" / "processforge.py"), "examples-check", "--root", str(root)], 60),
        ReleaseCommand("events-validate", [sys.executable, str(root / "tools" / "processforge.py"), "events-validate", "--project-root", str(root)], 60),
        ReleaseCommand("doctor-project", [sys.executable, str(root / "tools" / "processforge.py"), "doctor-project", "--project-root", str(root)], 60),
    ]
    failed = False
    warned = False
    for item in commands:
        status, code, output = run_release_command(item.label, item.command, root, timeout=item.timeout, allow_warn=item.allow_warn)
        print_release_command_output(item.label, status, code, output)
        failed = failed or status == "FAIL"
        warned = warned or status == "WARN"
    git_dir = root / ".git"
    if git_dir.exists():
        status, code, output = run_release_command("git diff --check", ["git", "diff", "--check"], root, timeout=60)
        print_release_command_output("git diff --check", status, code, output)
        failed = failed or status == "FAIL"
        warned = warned or status == "WARN"
    else:
        print("WARN git diff --check skipped: not a git repo")
        warned = True
    if failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS with warnings" if warned else "RESULT: PASS")
    return 0


def command_version(args: argparse.Namespace) -> int:
    version_file = ROOT / "VERSION"
    version = version_file.read_text(encoding="utf-8", errors="replace").strip() if version_file.is_file() else PROCESSFORGE_VERSION
    print(f"ProcessForge {version}")
    print(f"Spec: {PROCESSFORGE_SPEC_VERSION}")
    print(f"Schema bundle: {PROCESSFORGE_SCHEMA_BUNDLE_VERSION}")
    return 0


def command_release_pack(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = (root / output).resolve()
    manifest_path = output.with_suffix(".manifest.json")
    checks = release_checks(root)
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        for item in failures:
            print(f"FAIL: {item.message}")
        return 1
    patterns = release_ignore_patterns(root)
    files = [(archive_path, path) for archive_path, path in release_source_files(root) if not release_ignore_match(archive_path, patterns) and not release_path_is_forbidden(archive_path)]
    if args.dry_run:
        print(f"DRY-RUN: would write {output}")
        print(f"DRY-RUN: would write {manifest_path}")
        print(f"FILES: {len(files)}")
        for archive_path, _path in files[:50]:
            print(f"INCLUDE: {archive_path}")
        if len(files) > 50:
            print(f"... {len(files) - 50} more files")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_files = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for archive_path, source_path in files:
            archive.write(source_path, archive_path)
            manifest_files.append({"path": archive_path, "sha256": sha256_file(source_path)})
    manifest = {
        "name": RELEASE_NAME,
        "version": RELEASE_ARCHIVE_VERSION,
        "generated_at": now_utc(),
        "files": manifest_files,
    }
    manifest_path.write_text(ensure_trailing_newline(json.dumps(manifest, indent=2, sort_keys=True)), encoding="utf-8")
    print(f"WROTE: {rel(output, root)}")
    print(f"WROTE: {rel(manifest_path, root)}")
    print(f"FILES: {len(files)}")
    return 0


def archive_manifest_path(archive_path: Path) -> Path:
    return archive_path.with_suffix(".manifest.json")


def inspect_release_archive(archive_path: Path, manifest_path: Path | None = None) -> list[Check]:
    checks: list[Check] = []
    checks.append(check("PASS" if archive_path.is_file() else "FAIL", f"archive exists: {archive_path}"))
    if not archive_path.is_file():
        return checks
    manifest = manifest_path or archive_manifest_path(archive_path)
    checks.append(check("PASS" if manifest.is_file() else "FAIL", f"manifest exists: {manifest}"))
    with zipfile.ZipFile(archive_path) as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        forbidden = [name for name in names if release_path_is_forbidden(name) or name.startswith(".pf/runtime/") or name.startswith(".serena/") or name.startswith(".idea/") or name.startswith(".vscode/")]
        checks.append(check("PASS" if not forbidden else "FAIL", f"archive forbidden entries: {len(forbidden)}"))
        for name in forbidden[:20]:
            checks.append(check("FAIL", f"forbidden archive entry: {name}"))
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_files = data.get("files") if isinstance(data, dict) else None
            manifest_names = sorted(str(item.get("path")) for item in manifest_files if isinstance(item, dict) and item.get("path")) if isinstance(manifest_files, list) else []
            checks.append(check("PASS" if manifest_names == names else "FAIL", "manifest file list matches zip entries"))
            if manifest_names == names:
                checks.append(check("PASS", f"manifest files: {len(manifest_names)}"))
            else:
                missing = sorted(set(names) - set(manifest_names))
                extra = sorted(set(manifest_names) - set(names))
                for name in missing[:10]:
                    checks.append(check("FAIL", f"zip entry missing from manifest: {name}"))
                for name in extra[:10]:
                    checks.append(check("FAIL", f"manifest entry missing from zip: {name}"))
    return checks


def command_release_archive_test(args: argparse.Namespace) -> int:
    archive_path = Path(args.archive).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else archive_manifest_path(archive_path)
    checks = inspect_release_archive(archive_path, manifest_path)
    if print_checks(checks) != 0:
        return 1
    with tempfile.TemporaryDirectory(prefix="processforge-release-archive-") as temp:
        extract_root = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_root)
        cli = extract_root / "tools" / "processforge.py"
        if not cli.is_file():
            print(f"FAIL: extracted archive has no CLI: {cli}")
            return 1
        status, code, output = run_release_command(
            "release-test extracted archive",
            [sys.executable, str(cli), "release-test", "--root", str(extract_root)],
            extract_root,
            timeout=300,
        )
        print_release_command_output("release-test extracted archive", status, code, output)
        if status != "PASS":
            print("RESULT: FAIL")
            return 1
    print("RESULT: PASS")
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
    return resolve_registry_relative_path(workplace_manifest.parent, raw_path, workplace_manifest)


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
        return resolve_registry_relative_path(workplace_manifest.parent, str(raw_path), workplace_manifest)
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


def public_snapshot_path_checks(project_root: Path) -> list[Check]:
    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    checks: list[Check] = []
    for path in [snapshot_yaml, snapshot_md]:
        if not path.is_file():
            checks.append(check("WARN", f"{rel(path, project_root)} missing"))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checks.append(
            check(
                "PASS" if is_public_path_safe(text) else "FAIL",
                f"{rel(path, project_root)} contains no local absolute paths",
            )
        )
    return checks


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


def load_policy_document(name: str, root: Path | None = None) -> dict[str, Any]:
    path = (root or ROOT) / "policies" / name
    if not path.is_file():
        return {}
    data = load_yaml_document(path)
    return data if isinstance(data, dict) and not yaml_error(data) else {}


def policy_entries(policy: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = policy.get(key)
    if not isinstance(values, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in values:
        if isinstance(item, str):
            entries.append({"id": item})
        elif isinstance(item, dict):
            entries.append(item)
    return entries


def policy_id_matches(identifier: str, entry: dict[str, Any]) -> bool:
    if str(entry.get("id", "")) == identifier:
        return True
    pattern = entry.get("pattern")
    return bool(pattern and re.fullmatch(str(pattern), identifier))


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


def package_root_entries(workplace_root: Path) -> list[dict[str, Any]]:
    registry = load_yaml_document(workplace_root / "registries" / "package-roots.yaml")
    entries = registry.get("package_roots") if isinstance(registry, dict) else None
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def package_root_resolution_from_entry(workplace_root: Path, entry: dict[str, Any]) -> PackageRootResolution:
    root_id = str(entry.get("id", "package-root"))
    original = str(entry.get("path", ""))
    resolution = workplace_path_resolution(workplace_root, original)
    warnings = [str(item) for item in resolution.get("errors", [])]
    return PackageRootResolution(
        root_id=root_id,
        original_path=original,
        resolved_path=path_resolution_to_path(resolution),
        status=str(entry.get("status", "available")),
        warnings=warnings,
        fallback=False,
        entry=entry,
    )


def resolve_package_root(workplace_root: Path, package_root_id: str | None = None, *, mode: str = "read") -> PackageRootResolution:
    entries = package_root_entries(workplace_root)
    fallback = PackageRootResolution(
        root_id="fallback",
        original_path="packages",
        resolved_path=workplace_root / "packages",
        status="fallback",
        warnings=["WARN: registries/package-roots.yaml is missing or empty; using fallback <workplace-root>/packages"],
        fallback=True,
        entry=None,
    )
    if not entries:
        return fallback
    if package_root_id:
        for entry in entries:
            if str(entry.get("id")) == package_root_id:
                selected = package_root_resolution_from_entry(workplace_root, entry)
                break
        else:
            raise SystemExit(f"FAIL: package root '{package_root_id}' not found in registries/package-roots.yaml")
    else:
        available = [entry for entry in entries if str(entry.get("status", "available")) == "available"]
        default_entries = [entry for entry in available if bool(entry.get("default", False))]
        selected_entry = default_entries[0] if default_entries else (available[0] if available else None)
        if selected_entry is None:
            existing = [
                entry for entry in entries
                if entry.get("path") and package_root_resolution_from_entry(workplace_root, entry).resolved_path.exists()
            ]
            selected_entry = existing[0] if existing else entries[0]
        selected = package_root_resolution_from_entry(workplace_root, selected_entry)
    if selected.warnings:
        if mode == "write":
            if not selected.fallback:
                raise SystemExit("FAIL: package root path cannot be resolved: " + "; ".join(selected.warnings))
    if not selected.fallback and not selected.resolved_path.is_dir():
        selected.warnings.append(f"WARN: package root '{selected.root_id}' path does not exist: {selected.resolved_path.as_posix()}")
    if selected.entry is not None and str(selected.entry.get("writable", True)).lower() == "false" and mode == "write":
        raise SystemExit(f"FAIL: package root '{selected.root_id}' is not writable")
    if mode == "write" and not selected.fallback and not selected.resolved_path.is_dir():
        raise SystemExit(f"FAIL: selected package root '{selected.root_id}' path does not exist: {selected.resolved_path.as_posix()}")
    return selected


def package_path_candidates(root_path: Path, package_id: str) -> list[Path]:
    return [
        root_path / package_id / "package.yaml",
        root_path / f"{package_id}.yaml",
    ]


def resolve_package_path(workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[PackageRootResolution, Path]:
    root = resolve_package_root(workplace_root, package_root_id, mode=mode)
    return root, root.resolved_path / package_id / "package.yaml"


def workplace_package_roots(workplace_manifest: Path | None) -> list[PackageRootResolution]:
    if not workplace_manifest or not workplace_manifest.is_file():
        return []
    workplace_root = workplace_manifest.parent
    return [package_root_resolution_from_entry(workplace_root, entry) for entry in package_root_entries(workplace_root)]


def workplace_package_root_paths(workplace_manifest: Path | None) -> list[Path]:
    return [root.resolved_path for root in workplace_package_roots(workplace_manifest)]


def package_manifest_candidates(project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None = None) -> list[Path]:
    flow_root = locate_flow_root(project_root)
    candidates: list[Path] = []
    candidates.extend(manifest_path_refs(project_root, "packages"))
    roots: list[Path | None] = [
        flow_root / "packages",
        distribution_root / "packages" if distribution_root else None,
        (distribution_root or ROOT) / "seeds" / "knowledge-packages",
    ]
    roots.extend(workplace_package_root_paths(workplace_manifest))
    for root in roots:
        if root and root.is_dir():
            candidates.extend(sorted(root.glob("*.yaml")))
            candidates.extend(sorted(root.glob("*.yml")))
            candidates.extend(sorted(root.glob("*/package.yaml")))
            candidates.extend(sorted(root.glob("*/package.yml")))
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
    duplicates: dict[str, list[str]] = {}
    workplace_roots = workplace_package_roots(workplace_manifest)
    for path in package_manifest_candidates(project_root, distribution_root, workplace_manifest):
        data = load_yaml_document(path)
        if not data or yaml_error(data):
            continue
        package_id = data.get("id")
        if not package_id:
            continue
        record = dict(data)
        record["__manifest_path"] = path
        for root in workplace_roots:
            try:
                path.relative_to(root.resolved_path)
                record["__package_root_id"] = root.root_id
                break
            except ValueError:
                continue
        if str(package_id) in index:
            duplicates.setdefault(str(package_id), [index[str(package_id)]["__manifest_path"].as_posix()]).append(path.as_posix())
        index[str(package_id)] = record
    if duplicates:
        index["__duplicates__"] = {"packages": duplicates}
    return index


def resource_record_from_package(package_id: str, resource: dict[str, Any], requirement: str, package_root_id: str | None = None) -> dict[str, Any]:
    resource_id = str(resource.get("id", "resource"))
    record: dict[str, Any] = {
        "id": f"{package_id}:{resource_id}",
        "resource_id": resource_id,
        "package": package_id,
        "requirement": requirement,
        "kind": str(resource.get("kind", "reference")),
        "title": str(resource.get("title", resource_id)),
        "load_policy": str(resource.get("load_policy", "on_demand")),
        "index_policy": str(resource.get("index_policy", "metadata")),
        "status": "indexed",
    }
    if "path_ref" in resource:
        record["path_ref"] = resource["path_ref"]
    elif "path" in resource:
        raw_path = str(resource.get("path", ""))
        if raw_path and Path(raw_path).is_absolute():
            record["path_ref"] = {"registry": "private_resource_paths", "id": resource_id}
            record["path_status"] = "private_absolute_path_redacted"
        elif raw_path:
            if package_root_id:
                record["path_ref"] = {"registry": "package_roots", "id": package_root_id, "relative_path": f"{package_id}/{raw_path}"}
            else:
                record["path_ref"] = {"package": package_id, "relative_path": raw_path}
    for key in ["version", "description"]:
        if key in resource:
            record[key] = resource[key]
    return record


def resolve_package_resources(
    project_root: Path,
    distribution_root: Path | None,
    workplace_manifest: Path | None,
    package_ids: list[str],
    required_package_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    package_index = package_manifest_index(project_root, distribution_root, workplace_manifest)
    resources: list[dict[str, Any]] = []
    required_set = set(required_package_ids or [])
    for package_id in package_ids:
        manifest = package_index.get(package_id)
        if not manifest:
            continue
        requirement = "required" if package_id in required_set else "recommended"
        package_resources = manifest.get("resources")
        if not isinstance(package_resources, list):
            continue
        for resource in package_resources:
            if isinstance(resource, dict):
                resources.append(resource_record_from_package(package_id, resource, requirement, manifest.get("__package_root_id")))
    return resources


HEAVY_RESOURCE_KINDS = {
    "source_tree",
    "documentation",
    "article_collection",
    "note_collection",
    "snippet_collection",
    "example_collection",
    "dataset",
    "media_reference",
}


def resource_management_root(workplace_root: Path) -> Path:
    return workplace_root / "runtime" / "resource-management"


def resource_management_slug(command: str, object_id: str) -> str:
    stamp = now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    return f"{stamp}-{safe_id(command, 'command')}-{safe_id(object_id, 'resource')}"


def write_resource_management_artifact(workplace_root: Path, kind: str, slug: str, content: str) -> Path:
    target = resource_management_root(workplace_root) / kind / f"{slug}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(content), encoding="utf-8")
    return target


def write_resource_management_report(workplace_root: Path, slug: str, title: str, lines: list[str]) -> Path:
    target = resource_management_root(workplace_root) / "reports" / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = ["# " + title, "", *lines, ""]
    target.write_text("\n".join(body), encoding="utf-8")
    return target


def resource_management_event(
    *,
    scope: str,
    command: str,
    event_type: str,
    target: dict[str, Any],
    status: str,
    message: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": event_type,
        "occurred_at": now_utc(),
        "scope": scope,
        "source": {"command": command, "actor_type": "agent"},
        "target": target,
        "result": {"status": status, "message": message},
    }


def append_workplace_resource_event(workplace_root: Path, event: dict[str, Any]) -> Path:
    target = workplace_root / "runtime" / "events" / "events.ndjson"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        (target.read_text(encoding="utf-8") if target.is_file() else "")
        + json.dumps(redact_telemetry_value(event), ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return target


def default_load_policy(kind: str, requested: str | None = None) -> str:
    if requested:
        return requested
    return "on_demand" if kind in HEAVY_RESOURCE_KINDS else "when_relevant"


def default_index_policy(kind: str, requested: str | None = None) -> str:
    if requested:
        return requested
    if kind in {"source_tree"}:
        return "symbols"
    if kind in {"documentation", "article", "article_collection"}:
        return "full_text"
    return "metadata"


def path_ref_for_known_root(workplace_root: Path, raw_path: str) -> dict[str, Any] | None:
    resource_resolution = workplace_path_resolution(workplace_root, raw_path)
    if resource_resolution.get("errors"):
        return None
    resource_resolved = normalize_path_string(str(resource_resolution.get("resolved", ""))).rstrip("/")
    registry_specs = [
        ("knowledge_roots", "knowledge-roots.yaml", "knowledge_roots"),
        ("template_roots", "templates.yaml", "template_roots"),
        ("package_roots", "package-roots.yaml", "package_roots"),
    ]
    for registry_name, registry_file, collection_key in registry_specs:
        registry = load_yaml_document(workplace_root / "registries" / registry_file)
        entries = registry.get(collection_key) if isinstance(registry, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id") or not entry.get("path"):
                continue
            root_resolution = workplace_path_resolution(workplace_root, str(entry["path"]))
            if root_resolution.get("errors"):
                continue
            root_resolved = normalize_path_string(str(root_resolution.get("resolved", ""))).rstrip("/")
            if resource_resolved == root_resolved or resource_resolved.startswith(root_resolved + "/"):
                path_ref: dict[str, Any] = {"registry": registry_name, "id": str(entry["id"])}
                if resource_resolved != root_resolved:
                    path_ref["relative_path"] = resource_resolved[len(root_resolved) + 1 :]
                return path_ref
    return None


def ensure_private_resource_path(workplace_root: Path, resource_id: str, raw_path: str) -> Path:
    target = workplace_root / "registries" / "private-resource-paths.yaml"
    entry = {
        "id": resource_id,
        "label": resource_id.replace("-", " ").title(),
        "path": raw_path,
        "visibility": "private",
        "status": "available",
    }
    upsert_registry_entry(target, "private_resource_paths", entry)
    return target


def public_resource_path_ref(resource_id: str, raw_path: str | None, source_url: str | None = None, workplace_root: Path | None = None) -> dict[str, Any]:
    if source_url:
        return {"registry": "external_resources", "id": resource_id, "url": source_url}
    if raw_path:
        if workplace_root:
            known_ref = path_ref_for_known_root(workplace_root, raw_path)
            if known_ref:
                return known_ref
        if path_string_is_absolute(raw_path) or PATH_CONSTANT_PATTERN.search(raw_path):
            return {"registry": "private_resource_paths", "id": resource_id}
        return {"package": "self", "relative_path": raw_path}
    return {"registry": "external_resources", "id": resource_id}


def normalize_resource_record(resource: dict[str, Any], package_id: str, workplace_root: Path | None = None, *, register_private_path: bool = False) -> dict[str, Any]:
    record = dict(resource)
    resource_id = safe_id(str(record.get("id") or record.get("title") or "resource"), "resource")
    kind = str(record.get("kind") or "reference")
    raw_path = str(record.get("path")) if record.get("path") else None
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    source_url = str(source.get("url") or record.get("url") or "") or None
    record["id"] = resource_id
    record["kind"] = kind
    record["title"] = str(record.get("title") or resource_id.replace("-", " ").title())
    record["load_policy"] = default_load_policy(kind, str(record.get("load_policy")) if record.get("load_policy") else None)
    record["index_policy"] = default_index_policy(kind, str(record.get("index_policy")) if record.get("index_policy") else None)
    if "path_ref" not in record:
        record["path_ref"] = public_resource_path_ref(resource_id, raw_path, source_url, workplace_root)
    if raw_path and (path_string_is_absolute(raw_path) or PATH_CONSTANT_PATTERN.search(raw_path)):
        if workplace_root and register_private_path and record.get("path_ref", {}).get("registry") == "private_resource_paths":
            ensure_private_resource_path(workplace_root, resource_id, raw_path)
        record["path_status"] = "resolved_private_path_hidden"
        resolution = workplace_path_resolution(workplace_root, raw_path) if workplace_root else None
        if resolution and resolution.get("errors"):
            record["path_resolution"] = {"status": "error", "errors": resolution.get("errors")}
        elif record.get("path_ref", {}).get("registry") == "private_resource_paths":
            record["registration_hint"] = "register a knowledge_root/template_root/package_root if this path should be shared by multiple resources"
    record.pop("path", None)
    if source_url and "source" not in record:
        record["source"] = {"type": "url", "url": source_url}
    if "update_policy" not in record:
        record["update_policy"] = {"mode": "manual"}
    if "package" not in record:
        record["package"] = package_id
    return record


def resource_id_from_url(url: str, fallback: str = "resource") -> str:
    parsed = urlparse(url)
    pieces = [parsed.netloc, parsed.path.strip("/").split("/")[-1]]
    return safe_id("-".join(piece for piece in pieces if piece), fallback)


def find_workplace_package_manifests(workplace_root: Path, package_id: str) -> list[tuple[PackageRootResolution, Path]]:
    manifests: list[tuple[PackageRootResolution, Path]] = []
    roots = package_root_entries(workplace_root)
    if roots:
        root_resolutions = [package_root_resolution_from_entry(workplace_root, entry) for entry in roots]
    else:
        root_resolutions = [resolve_package_root(workplace_root, None, mode="read")]
    for root in root_resolutions:
        if root.warnings and not root.fallback:
            continue
        for path in package_path_candidates(root.resolved_path, package_id):
            if path.is_file():
                manifests.append((root, path))
    return manifests


def package_manifest_path_for_write(workplace_root: Path, package_id: str, package_root_id: str | None = None) -> tuple[PackageRootResolution, Path]:
    existing = find_workplace_package_manifests(workplace_root, package_id)
    if package_root_id:
        root, default_path = resolve_package_path(workplace_root, package_id, package_root_id, mode="write")
        for existing_root, existing_path in existing:
            if existing_root.root_id == root.root_id:
                return existing_root, existing_path
        return root, default_path
    if len(existing) > 1:
        roots = ", ".join(f"{root.root_id}:{path.as_posix()}" for root, path in existing)
        raise SystemExit(f"FAIL: duplicate package id '{package_id}' found across package roots: {roots}; pass --package-root")
    if len(existing) == 1:
        root, path = existing[0]
        if not root.resolved_path.is_dir() and not root.fallback:
            raise SystemExit(f"FAIL: package root '{root.root_id}' path does not exist: {root.resolved_path.as_posix()}")
        return root, path
    root, default_path = resolve_package_path(workplace_root, package_id, None, mode="write")
    if root.fallback:
        root.resolved_path.mkdir(parents=True, exist_ok=True)
    return root, default_path


def load_workplace_package_manifest(workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[Path, dict[str, Any], PackageRootResolution]:
    existing = find_workplace_package_manifests(workplace_root, package_id)
    if package_root_id:
        root, default_path = resolve_package_path(workplace_root, package_id, package_root_id, mode=mode)
        path = default_path
        for existing_root, existing_path in existing:
            if existing_root.root_id == root.root_id:
                root, path = existing_root, existing_path
                break
    elif existing:
        if len(existing) > 1:
            roots = ", ".join(f"{root.root_id}:{path.as_posix()}" for root, path in existing)
            root, path = existing[0]
            root.warnings.append(f"WARN: duplicate package id '{package_id}' found across package roots: {roots}")
        else:
            root, path = existing[0]
    else:
        root, path = resolve_package_path(workplace_root, package_id, None, mode=mode)
    data = load_yaml_document(path)
    if not data or yaml_error(data):
        data = {
            "schema_version": 1,
            "id": package_id,
            "name": package_id.replace(".", " ").replace("-", " ").title(),
            "version": "1.0.0",
            "kind": "documentation" if "docs" in package_id or "documentation" in package_id else "platform",
            "scope": "workplace",
            "resources": [],
        }
    if "resources" not in data or not isinstance(data.get("resources"), list):
        data["resources"] = []
    return path, data, root


def resource_index_path_for_package(manifest_path: Path, workplace_root: Path, package_id: str) -> Path:
    if manifest_path.name == "package.yaml":
        return manifest_path.parent / "indexes" / "resource-index.yaml"
    return workplace_root / "packages" / package_id / "indexes" / "resource-index.yaml"


def build_resource_index(package_manifest: dict[str, Any], workplace_root: Path | None = None, package_root_id: str | None = None) -> dict[str, Any]:
    package_id = str(package_manifest.get("id", "package"))
    resources = [
        normalize_resource_record(resource, package_id, workplace_root)
        for resource in package_manifest.get("resources", [])
        if isinstance(resource, dict)
    ]
    return {
        "schema_version": 1,
        "package": {
            "id": package_id,
            "version": str(package_manifest.get("version", "1.0.0")),
            "package_root": package_root_id or str(package_manifest.get("package_root", "")) or None,
        },
        "generated_at": now_utc(),
        "load_policy": {
            "default": "on_demand",
            "heavy_resources": "index_only_until_requested",
            "do_not_load_full_content": True,
        },
        "resources": resources,
    }


def upsert_resource(resources: list[Any], resource: dict[str, Any]) -> str:
    for index, item in enumerate(resources):
        if isinstance(item, dict) and str(item.get("id")) == str(resource["id"]):
            resources[index] = resource
            return "updated"
    resources.append(resource)
    return "added"


def write_package_manifest_and_index(workplace_root: Path, package_id: str, package_manifest: dict[str, Any], package_root_id: str | None = None) -> tuple[Path, Path, PackageRootResolution]:
    package_root, manifest_path = package_manifest_path_for_write(workplace_root, package_id, package_root_id)
    package_manifest["package_root"] = package_root.root_id
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(ensure_trailing_newline(dump_yaml(package_manifest)), encoding="utf-8")
    index_path = resource_index_path_for_package(manifest_path, workplace_root, package_id)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(ensure_trailing_newline(dump_yaml(build_resource_index(package_manifest, workplace_root, package_root.root_id))), encoding="utf-8")
    return manifest_path, index_path, package_root


def registry_ids_from_workplace(workplace_root: Path, registry_name: str, collection_key: str) -> set[str]:
    data = load_yaml_document(workplace_root / "registries" / registry_name)
    return registry_ids(data, collection_key)


def resource_path_ref_missing(workplace_root: Path, resource: dict[str, Any]) -> str | None:
    path_ref = resource.get("path_ref")
    if not isinstance(path_ref, dict):
        return "missing path_ref"
    registry = str(path_ref.get("registry") or "")
    ref_id = str(path_ref.get("id") or "")
    if not registry or not ref_id:
        return None if path_ref.get("package") else "path_ref must include registry/id or package/relative_path"
    known = {
        "knowledge_roots": ("knowledge-roots.yaml", "knowledge_roots"),
        "package_roots": ("package-roots.yaml", "package_roots"),
        "templates": ("templates.yaml", "template_roots"),
        "tools": ("tools.yaml", "tools"),
        "mcp": ("mcp.yaml", "mcp_servers"),
        "private_resource_paths": ("private-resource-paths.yaml", "private_resource_paths"),
    }
    if registry in {"external_resources"}:
        return None
    if registry not in known:
        return f"unknown path_ref registry {registry}"
    registry_file, collection_key = known[registry]
    if ref_id not in registry_ids_from_workplace(workplace_root, registry_file, collection_key):
        return f"path_ref target missing: {registry}/{ref_id}"
    return None


def knowledge_package_doctor_checks(workplace_root: Path, package_id: str, package_root_id: str | None = None) -> list[Check]:
    manifest_path, manifest, package_root = load_workplace_package_manifest(workplace_root, package_id, package_root_id, mode="read")
    checks: list[Check] = []
    if not manifest:
        return [
            check_with_hint(
                "FAIL",
                f"package {package_id} manifest missing",
                "The package id cannot be resolved through registries/package-roots.yaml.",
                f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
            )
        ]
    for warning in package_root.warnings:
        level = "WARN" if warning.startswith("WARN:") else "FAIL"
        checks.append(
            check_with_hint(
                level,
                warning,
                "The package_root resolver found a registry/path issue.",
                "check registries/package-roots.yaml and pass --package-root when multiple roots contain the same package id",
            )
        )
    if not manifest_path.is_file():
        checks.append(
            check_with_hint(
                "FAIL",
                f"package {package_id} not found through package_roots",
                "The package manifest is missing from the selected package_root.",
                f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root <package-root> --title \"{package_id}\" --apply",
            )
        )
        return checks
    checks.append(check("PASS", f"package {package_id} resolved through package root {package_root.root_id}"))
    resources = manifest.get("resources") if isinstance(manifest.get("resources"), list) else []
    checks.append(check("PASS", f"package {package_id} manifest loaded"))
    for resource in resources:
        if not isinstance(resource, dict):
            checks.append(check("FAIL", f"package {package_id} contains non-object resource"))
            continue
        resource_id = str(resource.get("id", "resource"))
        normalized = normalize_resource_record(resource, package_id, workplace_root)
        missing = resource_path_ref_missing(workplace_root, normalized)
        checks.append(
            check("PASS", f"{package_id}:{resource_id} path_ref resolved")
            if not missing
            else check_with_hint(
                "FAIL",
                f"{package_id}:{resource_id} path_ref - {missing}",
                "Public resource records must resolve through a known registry instead of embedding private paths.",
                "update the resource to use path_ref.registry and path_ref.id from the workplace registries",
            )
        )
        kind = str(resource.get("kind") or "reference")
        if kind in HEAVY_RESOURCE_KINDS and not resource.get("load_policy"):
            checks.append(check("WARN", f"{package_id}:{resource_id} heavy resource should declare load_policy"))
        elif kind in HEAVY_RESOURCE_KINDS and str(resource.get("load_policy")) in {"always_index", "session_start", "project_init"}:
            checks.append(check("WARN", f"{package_id}:{resource_id} heavy resource should normally use on_demand"))
    index_path = resource_index_path_for_package(manifest_path, workplace_root, package_id)
    if index_path.is_file():
        index = load_yaml_document(index_path)
        checks.append(check("PASS" if not yaml_error(index) else "FAIL", f"{rel(index_path, workplace_root)} is valid YAML"))
        indexed_ids = {str(item.get("id")) for item in index.get("resources", []) if isinstance(item, dict)}
        for resource in resources:
            if isinstance(resource, dict) and str(resource.get("id")) not in indexed_ids:
                checks.append(check("WARN", f"{package_id}:{resource.get('id')} missing from resource index"))
    else:
        checks.append(check("WARN", f"{rel(index_path, workplace_root)} missing; run knowledge-index-refresh --apply"))
    text = manifest_path.read_text(encoding="utf-8", errors="replace")
    checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", f"package {package_id} manifest has no private absolute paths"))
    navigation = manifest.get("navigation") if isinstance(manifest.get("navigation"), dict) else {}
    if navigation:
        checks.append(check("PASS", f"package {package_id} navigation configured"))
        allowed_sections = {"source_code", "development_articles", "documentation", "api_reference", "usage_rules"}
        for section in navigation:
            checks.append(check("PASS" if str(section) in allowed_sections else "WARN", f"navigation section recognized: {section}"))
    elif package_id.startswith("docs."):
        checks.append(check("WARN", f"package {package_id} navigation configured"))
    dependencies = package_dependency_ids(manifest)
    package_index = package_manifest_index(workplace_root, None, workplace_root / "workplace.yaml")
    for dependency_id in dependencies:
        checks.append(
            check("PASS", f"required knowledge package dependency available: {dependency_id}")
            if dependency_id in package_index
            else check_with_hint(
                "FAIL",
                f"required knowledge package dependency available: {dependency_id}",
                "The package manifest declares this dependency generically.",
                f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {dependency_id} --package-root global --title \"{dependency_id}\" --apply",
            )
        )
    package_policy = load_policy_document("package-id-policy.yaml")
    for entry in policy_entries(package_policy, "package_id_rules"):
        if policy_id_matches(package_id, entry):
            level = str(entry.get("level", "WARN")).upper()
            checks.append(
                check_with_hint(
                    "FAIL" if level == "FAIL" else "WARN",
                    str(entry.get("message", f"package id policy matched: {package_id}")),
                    str(entry.get("why", "The package id matched a data-driven package id policy.")),
                    str(entry.get("fix", "update the package id or policy manifest")),
                )
            )
    return checks


def project_knowledge_resource_index_checks(project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None) -> list[Check]:
    checks: list[Check] = []
    checked = 0
    for manifest_path in package_manifest_candidates(project_root, distribution_root, workplace_manifest):
        manifest = load_yaml_document(manifest_path)
        if not manifest or yaml_error(manifest):
            continue
        resources = manifest.get("resources")
        if not isinstance(resources, list) or not resources:
            continue
        checked += 1
        package_id = str(manifest.get("id", manifest_path.stem))
        root_for_index = manifest_path.parent.parent if manifest_path.parent.name == "packages" else project_root
        if distribution_root:
            try:
                manifest_path.relative_to(distribution_root)
                root_for_index = distribution_root
            except ValueError:
                pass
        index_path = resource_index_path_for_package(manifest_path, root_for_index, package_id)
        checks.append(check("PASS" if index_path.is_file() else "WARN", f"knowledge resource index for {package_id} {'found' if index_path.is_file() else 'missing'}"))
        for resource in resources:
            if not isinstance(resource, dict):
                checks.append(check("FAIL", f"{package_id} contains non-object resource"))
                continue
            normalized = normalize_resource_record(resource, package_id)
            if "path" in resource and Path(str(resource.get("path"))).is_absolute():
                checks.append(check("FAIL", f"{package_id}:{resource.get('id', 'resource')} exposes an absolute path instead of path_ref"))
            if "path_ref" not in normalized:
                checks.append(check("FAIL", f"{package_id}:{resource.get('id', 'resource')} missing path_ref"))
            kind = str(resource.get("kind") or "reference")
            if kind in HEAVY_RESOURCE_KINDS and not resource.get("load_policy"):
                checks.append(check("WARN", f"{package_id}:{resource.get('id', 'resource')} heavy resource should declare load_policy"))
    if checked == 0:
        checks.append(check("PASS", "knowledge resource indexes checked (no package resources declared)"))
    return checks


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
    platform_resolution = resolve_platform_contracts(workplace_manifest_path, manifest_platform_ids, project_root=project_root)
    package_index_ids = set(package_manifest_index(project_root, distribution_root, workplace_manifest_path))
    required_resource_missing, recommended_resource_missing = platform_resource_findings(workplace_manifest_path, platform_resolution, package_index_ids)
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
    required_package_ids = platform_resolution["required_knowledge_packages"]
    package_resources = resolve_package_resources(
        project_root,
        distribution_root,
        workplace_manifest_path,
        sorted(set(package_ids)),
        required_package_ids,
    )
    health_status = "blocked" if any(item["severity"] == "fail" for item in required_records) or platform_resolution["missing_required_contracts"] or platform_resolution["circular_platforms"] or required_resource_missing else ("warn" if any(item["severity"] == "warn" for item in optional_records) or recommended_resource_missing else "pass")
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
            "version": str(process_forge_data.get("version", "1.0.0")),
            "version_constraint": str(process_forge_data.get("version_constraint", "^1.0")),
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
            "stack": platform_resolution["platform_stack"],
            "missing_required": platform_resolution["missing_required_contracts"],
            "circular": platform_resolution["circular_platforms"],
            "missing_required_resources": required_resource_missing,
            "missing_recommended_resources": recommended_resource_missing,
        },
        "platform_stack": platform_resolution["platform_stack"],
        "sources": {"fingerprints": sources},
        "knowledge_stack": manifest_data.get("knowledge_stack", [{"id": "processforge.core", "version": "1.0.0", "source": "distribution"}]),
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
            "required": [item for item in package_resources if item.get("requirement") == "required"],
            "recommended": [item for item in package_resources if item.get("requirement") == "recommended"],
            "missing_required": required_resource_missing,
            "missing_recommended": recommended_resource_missing,
        },
        "tools": {"required": platform_resolution["required_tools"], "recommended": platform_resolution["recommended_tools"], "source": "workplace-registry"},
        "mcp": {"required": platform_resolution["required_mcp"], "recommended": platform_resolution["recommended_mcp"], "source": "workplace-registry"},
        "templates": {
            "project": [str(item["path"]) for item in sources if item.get("kind") == "template"],
            "required": platform_resolution["required_templates"],
            "recommended": platform_resolution["recommended_templates"],
            "source": "workplace-registry",
        },
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
            "## Platform Stack",
            "",
            md_items(platform_stack),
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
            "Run `python bin/pf.py project-context-refresh --project-root <project-root>` from the ProcessForge distribution root, or `python .pf/runtime/bin/pf.py project-context-refresh --project-root .` inside the linked project.",
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


EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+$")


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


ACTIVE_ASSIGNMENT_STATUSES = {"draft", "ready", "open", "pending", "in_progress", "blocked", "debugging", "review", "ready_for_review"}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_assignment_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = re.sub(r"/+", "/", text)
    return text.rstrip("/") if text not in {"", "/"} else text


def assignment_path_key(value: Any) -> str:
    text = normalize_assignment_path(value)
    return text.lower() if os.name == "nt" else text


def assignment_scope_items(value: Any) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for item in as_list(value):
        raw: Any = item
        if isinstance(item, dict):
            raw = item.get("path") or item.get("glob") or item.get("pattern") or item.get("file")
        text = normalize_assignment_path(raw)
        if text and text not in seen:
            items.append(text)
            seen.add(text)
    return items


def normalize_context_artifacts(value: Any) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for item in as_list(value):
        if isinstance(item, dict):
            path = normalize_assignment_path(item.get("path"))
            if not path:
                continue
            artifacts.append(
                {
                    "path": path,
                    "role": str(item.get("role", "input")),
                    "required": bool(item.get("required", True)),
                    "mutable_by_worker": bool(item.get("mutable_by_worker", False)),
                }
            )
        else:
            path = normalize_assignment_path(item)
            if path:
                artifacts.append({"path": path, "role": "input", "required": True, "mutable_by_worker": False})
    return artifacts


def normalize_required_outputs(value: Any) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for item in as_list(value):
        if isinstance(item, dict):
            output_id = str(item.get("id") or item.get("name") or "").strip()
            if not output_id:
                continue
            record = dict(item)
            record["id"] = output_id
            record.setdefault("type", "unspecified")
            record.setdefault("required", True)
            outputs.append(record)
        else:
            output_id = str(item or "").strip()
            if output_id:
                outputs.append({"id": output_id, "type": "unspecified", "required": True})
    return outputs


def normalize_execution_mode(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        mode = dict(value)
    elif isinstance(value, str) and value.strip():
        mode = {"kind": value.strip()}
    else:
        return {}
    kind = str(mode.get("kind", "")).strip()
    if kind:
        mode["kind"] = kind
    mode.setdefault("code_changes_allowed", False)
    mode.setdefault("artifact_changes_allowed", True)
    mode.setdefault("requires_review", True)
    return mode


def normalize_ownership(metadata: dict[str, Any], allowed_files: list[str]) -> dict[str, Any]:
    raw = metadata.get("ownership") if isinstance(metadata.get("ownership"), dict) else {}
    owner_id = str(raw.get("owner_id") or metadata.get("id") or "assignment")
    owned_files = assignment_scope_items(raw.get("owned_files"))
    owned_globs = assignment_scope_items(raw.get("owned_globs"))
    if not owned_files and allowed_files:
        owned_files = list(allowed_files)
    return {
        "owner_id": safe_id(owner_id, "assignment"),
        "owner_label": str(raw.get("owner_label") or f"worker-{safe_id(owner_id, 'assignment')}"),
        "role": str(raw.get("role") or metadata.get("role") or ""),
        "writer": bool(raw.get("writer", bool(allowed_files or owned_files or owned_globs))),
        "owned_files": owned_files,
        "owned_globs": owned_globs,
    }


def normalize_non_overlap(value: Any, current_write_scope: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    result = dict(value)
    active = result.get("active_parallel_tasks")
    if not isinstance(active, list):
        active = []
    if result.get("active_parallel_task"):
        active.append(
            {
                "id": result.get("active_parallel_task"),
                "owner": result.get("active_parallel_owner"),
                "write_scope": assignment_scope_items(result.get("active_parallel_scope")),
            }
        )
    normalized_active: list[dict[str, Any]] = []
    for item in active:
        if isinstance(item, dict):
            record = dict(item)
            if "write_scope" in record:
                record["write_scope"] = assignment_scope_items(record.get("write_scope"))
            normalized_active.append(record)
        elif item:
            normalized_active.append({"id": str(item), "write_scope": []})
    result["policy"] = str(result.get("policy") or "block_on_write_overlap")
    result["active_parallel_tasks"] = normalized_active
    result["current_write_scope"] = current_write_scope
    result.pop("active_parallel_task", None)
    result.pop("active_parallel_owner", None)
    result.pop("active_parallel_scope", None)
    return result


def assignment_write_scope(metadata: dict[str, Any]) -> list[str]:
    allowed = assignment_scope_items(metadata.get("allowed_files"))
    ownership = metadata.get("ownership") if isinstance(metadata.get("ownership"), dict) else {}
    owned = assignment_scope_items(ownership.get("owned_files"))
    owned.extend(assignment_scope_items(ownership.get("owned_globs")))
    owned.extend(assignment_scope_items(metadata.get("allowed_globs")))
    result: list[str] = []
    seen: set[str] = set()
    for item in [*allowed, *owned]:
        key = assignment_path_key(item)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def assignment_has_glob(value: str) -> bool:
    return any(char in value for char in "*?[")


def iter_repo_files(project_root: Path) -> list[str]:
    files: list[str] = []
    skipped = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
    for path in project_root.rglob("*"):
        if any(part in skipped for part in path.parts):
            continue
        if path.is_file():
            files.append(rel(path, project_root))
    return files


def assignment_patterns_overlap(left: str, right: str, repo_files: list[str]) -> tuple[bool, str]:
    left_key = assignment_path_key(left)
    right_key = assignment_path_key(right)
    left_glob = assignment_has_glob(left_key)
    right_glob = assignment_has_glob(right_key)
    files = [assignment_path_key(item) for item in repo_files]
    if not left_glob and not right_glob:
        return (left_key == right_key, "same_file")
    if left_glob and not right_glob:
        return (fnmatch.fnmatch(right_key, left_key), "glob_matches_file")
    if right_glob and not left_glob:
        return (fnmatch.fnmatch(left_key, right_key), "file_matches_glob")
    if left_key == right_key:
        return True, "same_glob"
    if any(fnmatch.fnmatch(item, left_key) and fnmatch.fnmatch(item, right_key) for item in files):
        return True, "glob_matches_same_file"
    left_prefix = re.split(r"[*?\[]", left_key, 1)[0]
    right_prefix = re.split(r"[*?\[]", right_key, 1)[0]
    if left_prefix and right_prefix and (left_prefix.startswith(right_prefix) or right_prefix.startswith(left_prefix)):
        return True, "possible_glob_overlap"
    return False, ""


def assignment_scope_conflicts(
    current_id: str,
    current_scope: list[str],
    other_id: str,
    other_scope: list[str],
    repo_files: list[str],
    *,
    reason_prefix: str = "",
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for current_item in current_scope:
        for other_item in other_scope:
            overlaps, reason = assignment_patterns_overlap(current_item, other_item, repo_files)
            if overlaps:
                conflicts.append(
                    {
                        "current_assignment": current_id,
                        "current_scope": current_item,
                        "other_assignment": other_id,
                        "other_scope": other_item,
                        "reason": reason_prefix + reason,
                    }
                )
    return conflicts


def validate_assignment_scope_overlaps(
    project_root: Path,
    metadata: dict[str, Any],
    *,
    assignment_path: Path | None = None,
) -> dict[str, Any]:
    current_id = safe_id(str(metadata.get("id") or (assignment_path.stem if assignment_path else "assignment")), "assignment")
    current_scope = assignment_write_scope(metadata)
    forbidden_scope = assignment_scope_items(metadata.get("forbidden_files"))
    repo_files = iter_repo_files(project_root)
    conflicts = assignment_scope_conflicts(
        current_id,
        current_scope,
        current_id,
        forbidden_scope,
        repo_files,
        reason_prefix="assignment_forbidden_wins:",
    )
    flow_root = locate_flow_root(project_root)
    current_resolved = assignment_path.resolve() if assignment_path else None
    for candidate in sorted((flow_root / "assignments").glob("*.yaml")):
        if current_resolved and candidate.resolve() == current_resolved:
            continue
        other = load_yaml_document(candidate)
        if yaml_error(other):
            continue
        status = str(other.get("status", "")).strip()
        if status not in ACTIVE_ASSIGNMENT_STATUSES:
            continue
        other_scope = assignment_write_scope(other)
        if not other_scope:
            continue
        other_id = safe_id(str(other.get("id") or candidate.stem), "assignment")
        conflicts.extend(assignment_scope_conflicts(current_id, current_scope, other_id, other_scope, repo_files))
    return {"status": "fail" if conflicts else "pass", "conflicts": conflicts}


def normalized_assignment_contract(project_root: Path, assignment: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    assignment_rel = rel(assignment, project_root)
    required_sources = assignment_scope_items([rel(snapshot_yaml, project_root), assignment_rel, *as_list(metadata.get("required_sources"))])
    context_artifacts = normalize_context_artifacts(metadata.get("context_artifacts"))
    allowed_files = assignment_scope_items(metadata.get("allowed_files"))
    allowed_read_files = assignment_scope_items(metadata.get("allowed_read_files"))
    forbidden_files = assignment_scope_items(metadata.get("forbidden_files"))
    ownership = normalize_ownership(metadata, allowed_files)
    write_scope = assignment_write_scope({"allowed_files": allowed_files, "ownership": ownership})
    non_overlap = normalize_non_overlap(metadata.get("non_overlap"), write_scope)
    return {
        "assignment": {
            "id": safe_id(str(metadata.get("id", assignment.stem)), "assignment"),
            "path": assignment_rel,
            "status": metadata.get("status", "ready"),
            "objective": metadata.get("objective", ""),
            "execution_mode": normalize_execution_mode(metadata.get("execution_mode")),
        },
        "context": {"required_sources": required_sources, "context_artifacts": context_artifacts},
        "scope": {
            "allowed_files": allowed_files,
            "allowed_read_files": allowed_read_files,
            "forbidden_files": forbidden_files,
            "ownership": ownership,
            "non_overlap": non_overlap,
        },
        "outputs": {
            "required_outputs": normalize_required_outputs(metadata.get("required_outputs")),
            "expected_report": metadata.get("expected_report") if isinstance(metadata.get("expected_report"), dict) else {},
        },
    }


def validate_assignment_required_sources(project_root: Path, contract: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    required_sources = contract.get("context", {}).get("required_sources", [])
    for source in required_sources if isinstance(required_sources, list) else []:
        path = project_root / str(source)
        if not path.is_file():
            missing.append(str(source))
    artifacts = contract.get("context", {}).get("context_artifacts", [])
    for item in artifacts if isinstance(artifacts, list) else []:
        if isinstance(item, dict) and item.get("required", True):
            source = str(item.get("path", ""))
            if source and not (project_root / source).is_file():
                missing.append(source)
    return sorted(set(missing))


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
    contract = normalized_assignment_contract(project_root, assignment, metadata)
    missing_sources = validate_assignment_required_sources(project_root, contract)
    if missing_sources:
        raise SystemExit("FAIL: assignment required sources missing: " + ", ".join(missing_sources))
    overlap_check = validate_assignment_scope_overlaps(project_root, metadata, assignment_path=assignment)
    if overlap_check["status"] == "fail":
        raise SystemExit("FAIL: assignment write scope overlaps active assignments: " + dump_yaml(overlap_check))
    contract["scope"]["non_overlap"]["overlap_check"] = overlap_check
    capsule = {
        "schema_version": 1,
        "capsule": {
            "id": f"{assn_id}-capsule",
            "generated_at": now_utc(),
            "assignment_id": assn_id,
            "assignment_path": rel(assignment, project_root),
            "snapshot": rel(snapshot_yaml, project_root),
            "snapshot_checksum": sha256_file(snapshot_yaml),
            "worker_may_rebuild_context": False,
        },
        "assignment": contract["assignment"],
        "context": {
            "snapshot_id": snapshot.get("snapshot", {}).get("id", "project-context"),
            "freshness": status,
            "required_sources": contract["context"]["required_sources"],
            "context_artifacts": contract["context"]["context_artifacts"],
        },
        "scope": contract["scope"],
        "outputs": contract["outputs"],
        "capabilities": {"required": required_records, "optional": optional_records},
        "telemetry": {"events": telemetry_rel, "event_correlation_id": f"assignment-{assn_id}"},
        "required_sources": contract["context"]["required_sources"],
        "allowed_files": contract["scope"]["allowed_files"],
        "forbidden_files": contract["scope"]["forbidden_files"],
        "required_outputs": contract["outputs"]["required_outputs"],
        "required_capabilities": required_records,
        "optional_capabilities": optional_records,
        "selected_sources": metadata.get("selected_sources", []),
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


RUN_STATUSES = {"draft", "open", "in_progress", "blocked", "review", "completed", "cancelled", "failed"}
TASK_STATUSES = {"open", "in_progress", "blocked", "debugging", "review", "done", "cancelled", "failed"}
ITERATION_KINDS = {"work", "debug", "fix", "review", "test", "research", "handoff", "note"}
ITERATION_STATUSES = {"planned", "in_progress", "completed", "passed", "failed", "cancelled"}


def run_root(project_root: Path, run_id: str) -> Path:
    return locate_flow_root(project_root) / "runs" / safe_id(run_id, "run")


def run_yaml_path(project_root: Path, run_id: str) -> Path:
    return run_root(project_root, run_id) / "run.yaml"


def assignment_yaml_path(project_root: Path, task_id: str) -> Path:
    return locate_flow_root(project_root) / "assignments" / f"{safe_id(task_id, 'task')}.yaml"


def task_artifacts_root(project_root: Path, run_id: str, task_id: str) -> Path:
    return locate_flow_root(project_root) / "artifacts" / "runs" / safe_id(run_id, "run") / safe_id(task_id, "task")


def read_yaml_file(path: Path) -> dict[str, Any]:
    data = load_yaml_document(path)
    error = yaml_error(data)
    if error:
        raise SystemExit(f"FAIL: {path} is invalid YAML: {error}")
    return data


def write_yaml_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ensure_trailing_newline(dump_yaml(data)), encoding="utf-8")


def process_definition_exists(project_root: Path, process_id: str) -> bool:
    process_file = f"{safe_id(process_id, 'process')}.yaml"
    flow_root = locate_flow_root(project_root)
    return (
        (project_root / "processes" / process_file).is_file()
        or (flow_root / "processes" / process_file).is_file()
        or (ROOT / "processes" / process_file).is_file()
    )


def active_run_ids(project_root: Path) -> list[str]:
    root = locate_flow_root(project_root) / "runs"
    ids: list[str] = []
    if not root.is_dir():
        return ids
    for path in sorted(root.glob("*/run.yaml")):
        data = load_yaml_document(path)
        if yaml_error(data):
            continue
        status = str(data.get("status", ""))
        if status in {"draft", "open", "in_progress", "blocked", "review"}:
            ids.append(str(data.get("id") or path.parent.name))
    return ids


def task_process_id(task: dict[str, Any]) -> str:
    value = task.get("process")
    if isinstance(value, dict):
        return str(value.get("id", ""))
    return str(value or "")


def next_iteration_id(task: dict[str, Any]) -> str:
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    used = {str(item.get("id")) for item in iterations if isinstance(item, dict)}
    index = 1
    while True:
        candidate = f"iter-{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def render_task_index(project_root: Path, run: dict[str, Any]) -> str:
    tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
    lines = [
        f"# Task Index: {run.get('id', 'run')}",
        "",
        f"Run status: `{run.get('status', 'unknown')}`",
        "",
        "| Order | Task | Status | Assignment |",
        "| --- | --- | --- | --- |",
    ]
    for item in sorted([task for task in tasks if isinstance(task, dict)], key=lambda value: int(value.get("order", 0) or 0)):
        lines.append(f"| {item.get('order', '')} | `{item.get('id', '')}` | `{item.get('status', '')}` | `{item.get('assignment', '')}` |")
    if not tasks:
        lines.append("| | No tasks yet | | |")
    return "\n".join(lines) + "\n"


def write_task_index(project_root: Path, run: dict[str, Any]) -> None:
    run_id = str(run.get("id", "run"))
    (run_root(project_root, run_id) / "task-index.md").write_text(render_task_index(project_root, run), encoding="utf-8")


def load_run(project_root: Path, run_id: str) -> dict[str, Any]:
    path = run_yaml_path(project_root, run_id)
    if not path.is_file():
        raise SystemExit(f"FAIL: run not found: {safe_id(run_id, 'run')}")
    return read_yaml_file(path)


def save_run(project_root: Path, run: dict[str, Any]) -> None:
    run["updated_at"] = now_utc()
    write_yaml_file(run_yaml_path(project_root, str(run.get("id", "run"))), run)
    write_task_index(project_root, run)


def load_task(project_root: Path, task_id: str) -> dict[str, Any]:
    path = assignment_yaml_path(project_root, task_id)
    if not path.is_file():
        raise SystemExit(f"FAIL: task/assignment not found: {safe_id(task_id, 'task')}")
    return read_yaml_file(path)


def save_task(project_root: Path, task: dict[str, Any]) -> None:
    task["updated_at"] = now_utc()
    write_yaml_file(assignment_yaml_path(project_root, str(task.get("id", "task"))), task)


def update_run_task_status(project_root: Path, run_id: str, task_id: str, status: str) -> None:
    run = load_run(project_root, run_id)
    changed = False
    for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
        if isinstance(item, dict) and str(item.get("id")) == task_id:
            item["status"] = status
            changed = True
    if changed:
        save_run(project_root, run)


def public_yaml_has_private_path(data: dict[str, Any]) -> bool:
    return not is_public_path_safe(json.dumps(data, ensure_ascii=False))


def validate_run_consistency(project_root: Path, run_id: str) -> list[Check]:
    flow_root = require_flow_root(project_root)
    checks: list[Check] = []
    path = run_yaml_path(project_root, run_id)
    if not path.is_file():
        return [check("FAIL", f"{rel(path, project_root)} missing")]
    run = read_yaml_file(path)
    error = yaml_error(run)
    if error:
        return [check("FAIL", f"{rel(path, project_root)} invalid YAML: {error}")]
    for key in ["schema_version", "id", "title", "process", "status", "created_at", "updated_at", "tasks"]:
        checks.append(check("PASS" if key in run else "FAIL", f"run.{key} present"))
    status = str(run.get("status", ""))
    checks.append(check("PASS" if status in RUN_STATUSES else "FAIL", f"run status valid: {status or 'missing'}"))
    process_id = str(run.get("process", ""))
    checks.append(check("PASS" if process_definition_exists(project_root, process_id) else "FAIL", f"process exists: {process_id or 'missing'}"))
    checks.append(check("PASS" if not public_yaml_has_private_path(run) else "FAIL", f"{rel(path, project_root)} has no private absolute paths"))
    tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
    seen: set[str] = set()
    if not isinstance(tasks, list):
        checks.append(check("FAIL", "run.tasks must be a list"))
        tasks = []
    for item in tasks:
        if not isinstance(item, dict):
            checks.append(check("FAIL", "run.tasks item must be an object"))
            continue
        task_id = str(item.get("id", ""))
        assignment_rel = str(item.get("assignment", ""))
        task_status = str(item.get("status", ""))
        checks.append(check("PASS" if task_id and task_id not in seen else "FAIL", f"task id unique: {task_id or 'missing'}"))
        seen.add(task_id)
        checks.append(check("PASS" if task_status in TASK_STATUSES else "FAIL", f"task status valid for {task_id}: {task_status or 'missing'}"))
        assignment_path = project_root / assignment_rel if assignment_rel.startswith(PROJECT_FLOW_ROOT + "/") else flow_root / "assignments" / f"{safe_id(task_id, 'task')}.yaml"
        checks.append(check("PASS" if assignment_path.is_file() else "FAIL", f"assignment exists for {task_id}: {assignment_rel or rel(assignment_path, project_root)}"))
        if assignment_path.is_file():
            task = read_yaml_file(assignment_path)
            checks.append(check("PASS" if str(task.get("run_id", "")) == str(run.get("id", "")) else "FAIL", f"{task_id} run_id matches run"))
    if status == "completed":
        incomplete = [str(item.get("id")) for item in tasks if isinstance(item, dict) and item.get("blocking", True) is not False and str(item.get("status")) != "done"]
        checks.append(check("PASS" if not incomplete else "FAIL", "completed run has all blocking tasks done" + (f": {', '.join(incomplete)}" if incomplete else "")))
        summary = run_root(project_root, str(run.get("id", run_id))) / "summary.md"
        handoff = flow_root / "handoffs" / "runs" / f"{safe_id(str(run.get('id', run_id)), 'run')}-handoff.md"
        checks.append(check("PASS" if summary.is_file() else "FAIL", f"{rel(summary, project_root)} exists"))
        checks.append(check("PASS" if handoff.is_file() else "FAIL", f"{rel(handoff, project_root)} exists"))
    events_path, _outbox = event_runtime_paths(project_root)
    event_text = events_path.read_text(encoding="utf-8", errors="replace") if events_path.is_file() else ""
    checks.append(check("PASS" if str(run.get("id", run_id)) in event_text else "WARN", "run events exist"))
    return checks


def validate_task_consistency(project_root: Path, task_id: str) -> list[Check]:
    require_flow_root(project_root)
    checks: list[Check] = []
    path = assignment_yaml_path(project_root, task_id)
    if not path.is_file():
        return [check("FAIL", f"{rel(path, project_root)} missing")]
    task = read_yaml_file(path)
    for key in ["schema_version", "id", "title", "run_id", "process", "status", "iterations", "result"]:
        checks.append(check("PASS" if key in task else "FAIL", f"task.{key} present"))
    status = str(task.get("status", ""))
    checks.append(check("PASS" if status in TASK_STATUSES else "FAIL", f"task status valid: {status or 'missing'}"))
    run_id = str(task.get("run_id", ""))
    checks.append(check("PASS" if run_id and run_yaml_path(project_root, run_id).is_file() else "FAIL", f"referenced run exists: {run_id or 'missing'}"))
    process_id = task_process_id(task)
    checks.append(check("PASS" if process_definition_exists(project_root, process_id) else "FAIL", f"process exists: {process_id or 'missing'}"))
    checks.append(check("PASS" if not public_yaml_has_private_path(task) else "FAIL", f"{rel(path, project_root)} has no private absolute paths"))
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    seen: set[str] = set()
    if not isinstance(iterations, list):
        checks.append(check("FAIL", "task.iterations must be a list"))
        iterations = []
    for item in iterations:
        if not isinstance(item, dict):
            checks.append(check("FAIL", "iteration item must be an object"))
            continue
        iter_id = str(item.get("id", ""))
        kind = str(item.get("kind", ""))
        iter_status = str(item.get("status", ""))
        checks.append(check("PASS" if iter_id and iter_id not in seen else "FAIL", f"iteration id unique: {iter_id or 'missing'}"))
        seen.add(iter_id)
        checks.append(check("PASS" if kind in ITERATION_KINDS else "FAIL", f"iteration kind valid for {iter_id}: {kind or 'missing'}"))
        checks.append(check("PASS" if iter_status in ITERATION_STATUSES else "FAIL", f"iteration status valid for {iter_id}: {iter_status or 'missing'}"))
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    if status == "done":
        result_summary = str(result.get("summary", "")).strip()
        result_artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), list) else []
        checks.append(check("PASS" if result_summary or result_artifacts else "FAIL", "completed task has result summary or artifact"))
    return checks


def process_authoring_root(project_root: Path, process_id: str) -> Path:
    return locate_flow_root(project_root) / "authoring" / "processes" / safe_id(process_id, "process")


def process_authoring_paths(project_root: Path, process_id: str) -> dict[str, Path]:
    root = process_authoring_root(project_root, process_id)
    return {
        "root": root,
        "answers": root / "answers.yaml",
        "draft": root / "draft.process.yaml",
        "questions": root / "questions.md",
        "logic_review": root / "logic-review.md",
        "log": root / "authoring-log.md",
        "apply_report": root / "apply-report.md",
    }


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def title_from_id(value: str) -> str:
    return " ".join(part.capitalize() for part in safe_id(value, "item").split("-"))


def default_process_authoring_answers(process_id: str, title: str, description: str = "") -> dict[str, Any]:
    process_id = safe_id(process_id, "new-process")
    title = title or title_from_id(process_id)
    return {
        "schema_version": 1,
        "process": {
            "id": process_id,
            "name": title,
            "version": "1.0.0",
            "status": "draft",
            "kind": "project_process",
            "scope": "project",
            "description": description or f"Guide repeatable work for {title}.",
        },
        "run_model": {
            "supports_multiple_tasks": False,
            "default_task_loop": {
                "enabled": False,
                "iteration_kinds": ["work", "debug", "fix", "review", "handoff"],
            },
        },
        "roles": [
            {"id": "author", "title": "Author", "responsibility": "Creates the main work artifacts."},
            {"id": "reviewer", "title": "Reviewer", "responsibility": "Checks quality gates before handoff."},
        ],
        "stages": [
            {
                "id": "intake",
                "title": "Intake",
                "description": "Capture objective, constraints, and expected outputs.",
                "required_role": "author",
                "produced_artifacts": ["brief"],
                "exit_gates": ["brief-approved"],
                "handoff_required": False,
            },
            {
                "id": "work",
                "title": "Work",
                "description": "Create the requested outputs.",
                "required_role": "author",
                "required_inputs": ["brief"],
                "produced_artifacts": ["work-output"],
                "entry_gates": ["brief-approved"],
                "exit_gates": ["work-ready-for-review"],
                "handoff_required": False,
            },
            {
                "id": "review",
                "title": "Review",
                "description": "Validate the output and record risks.",
                "required_role": "reviewer",
                "required_inputs": ["work-output"],
                "produced_artifacts": ["review-notes"],
                "entry_gates": ["work-ready-for-review"],
                "exit_gates": ["review-passed"],
                "handoff_required": False,
            },
            {
                "id": "handoff",
                "title": "Handoff",
                "description": "Summarize delivered state and next steps.",
                "required_role": "author",
                "required_inputs": ["review-notes"],
                "produced_artifacts": ["handoff"],
                "entry_gates": ["review-passed"],
                "exit_gates": ["handoff-created"],
                "handoff_required": True,
            },
        ],
        "artifacts": [
            {"id": "brief", "title": "Brief", "owner_role": "author", "template": "artifact-template"},
            {"id": "work-output", "title": "Work Output", "owner_role": "author", "template": "artifact-template"},
            {"id": "review-notes", "title": "Review Notes", "owner_role": "reviewer", "template": "review-template"},
            {"id": "handoff", "title": "Handoff", "owner_role": "author", "template": "handoff-template"},
        ],
        "gates": [
            {"id": "brief-approved", "description": "Brief is explicit enough to start work.", "blocking": True, "required_artifact": "brief"},
            {"id": "work-ready-for-review", "description": "Work output exists and is ready for review.", "blocking": True, "required_artifact": "work-output"},
            {"id": "review-passed", "description": "Review has no blocking failures.", "blocking": True, "required_artifact": "review-notes"},
            {"id": "handoff-created", "description": "Handoff artifact exists.", "blocking": True, "required_artifact": "handoff"},
        ],
        "required_capabilities": ["process_coordination", "artifact_review", "reporting"],
        "required_packages": ["process-forge-core"],
        "required_templates": ["artifact-template", "review-template", "handoff-template"],
        "allowed_tools": ["processforge-cli", "validator"],
        "forbidden_actions": ["write_private_absolute_paths_to_public_files", "skip_blocking_review"],
    }


def normalize_process_authoring_answers(raw: dict[str, Any], fallback_id: str = "new-process", fallback_title: str = "") -> dict[str, Any]:
    base = default_process_authoring_answers(fallback_id, fallback_title or title_from_id(fallback_id))
    if not raw:
        return base
    process = raw.get("process") if isinstance(raw.get("process"), dict) else {}
    if not process and ("id" in raw or "name" in raw or "title" in raw):
        process = raw
    process_id = safe_id(str(process.get("id") or raw.get("id") or fallback_id), "new-process")
    base["process"].update(
        {
            "id": process_id,
            "name": str(process.get("name") or process.get("title") or raw.get("name") or raw.get("title") or title_from_id(process_id)),
            "version": str(process.get("version") or raw.get("version") or "1.0.0"),
            "status": str(process.get("status") or raw.get("status") or "draft"),
            "kind": str(process.get("kind") or raw.get("kind") or base["process"]["kind"]),
            "scope": str(process.get("scope") or raw.get("scope") or base["process"]["scope"]),
            "description": str(process.get("description") or raw.get("description") or base["process"]["description"]),
        }
    )
    for key in ["run_model", "roles", "stages", "artifacts", "artifact_definitions", "gates", "hooks", "evolution_policy", "expected_artifacts"]:
        if key in raw:
            base[key] = raw[key]
    if "artifact_definitions" in raw and "artifacts" not in raw:
        base["artifacts"] = raw["artifact_definitions"]
    for key in ["required_capabilities", "required_packages", "required_templates", "allowed_tools", "forbidden_actions"]:
        if key in raw:
            base[key] = string_list(raw[key])
    return base


def process_from_authoring_answers(answers: dict[str, Any]) -> dict[str, Any]:
    process = answers.get("process") if isinstance(answers.get("process"), dict) else {}
    process_id = safe_id(str(process.get("id", "new-process")), "new-process")
    roles: list[dict[str, Any]] = []
    for item in as_list(answers.get("roles")):
        if isinstance(item, dict):
            role_id = safe_id(str(item.get("id") or item.get("title") or "role"), "role")
            roles.append({"id": role_id, "title": str(item.get("title") or title_from_id(role_id)), "responsibility": str(item.get("responsibility") or "")})
    if not roles:
        roles = [{"id": "author", "title": "Author", "responsibility": "Creates process artifacts."}]
    role_ids = {item["id"] for item in roles}

    artifacts: list[dict[str, Any]] = []
    for item in as_list(answers.get("artifacts")):
        if isinstance(item, dict):
            artifact_id = safe_id(str(item.get("id") or item.get("title") or "artifact"), "artifact")
            owner_role = safe_id(str(item.get("owner_role") or roles[0]["id"]), roles[0]["id"])
            if owner_role not in role_ids:
                owner_role = roles[0]["id"]
            artifacts.append(
                {
                    "id": artifact_id,
                    "title": str(item.get("title") or title_from_id(artifact_id)),
                    "owner_role": owner_role,
                    "template": str(item.get("template") or "artifact-template"),
                    "lifecycle": string_list(item.get("lifecycle")) or ["draft", "ready_for_review", "approved"],
                }
            )
    artifact_ids = {item["id"] for item in artifacts}

    gates: list[dict[str, Any]] = []
    for item in as_list(answers.get("gates")):
        if isinstance(item, dict):
            gate_id = safe_id(str(item.get("id") or item.get("description") or "gate"), "gate")
            gate: dict[str, Any] = {
                "id": gate_id,
                "description": str(item.get("description") or title_from_id(gate_id)),
                "blocking": bool(item.get("blocking", True)),
            }
            if item.get("required_artifact"):
                gate["required_artifact"] = safe_id(str(item.get("required_artifact")), "artifact")
            gates.append(gate)
    gate_ids = {item["id"] for item in gates}

    stages: list[dict[str, Any]] = []
    for item in as_list(answers.get("stages")):
        if isinstance(item, dict):
            stage_id = safe_id(str(item.get("id") or item.get("title") or "stage"), "stage")
            produced = [safe_id(value, "artifact") for value in string_list(item.get("produced_artifacts"))]
            exits = [safe_id(value, "gate") for value in string_list(item.get("exit_gates"))]
            if not produced and artifact_ids:
                produced = [sorted(artifact_ids)[0]]
            if not exits and gate_ids:
                exits = [sorted(gate_ids)[0]]
            role_id = safe_id(str(item.get("required_role") or roles[0]["id"]), roles[0]["id"])
            if role_id not in role_ids:
                role_id = roles[0]["id"]
            stages.append(
                {
                    "id": stage_id,
                    "title": str(item.get("title") or title_from_id(stage_id)),
                    "description": str(item.get("description") or ""),
                    "required_inputs": [safe_id(value, "artifact") for value in string_list(item.get("required_inputs"))],
                    "produced_artifacts": produced,
                    "required_role": role_id,
                    "required_capabilities": string_list(item.get("required_capabilities")),
                    "allowed_tools": string_list(item.get("allowed_tools")),
                    "entry_gates": [safe_id(value, "gate") for value in string_list(item.get("entry_gates"))],
                    "exit_gates": exits,
                    "handoff_required": bool(item.get("handoff_required", False)),
                }
            )
    if not artifacts:
        artifacts = [{"id": "brief", "title": "Brief", "owner_role": roles[0]["id"], "template": "artifact-template", "lifecycle": ["draft", "ready_for_review", "approved"]}]
        artifact_ids = {"brief"}
    if not gates:
        gates = [{"id": "brief-approved", "description": "Brief is approved.", "blocking": True, "required_artifact": "brief"}]
        gate_ids = {"brief-approved"}
    if not stages:
        stages = [{"id": "intake", "title": "Intake", "description": "Capture scope.", "required_inputs": [], "produced_artifacts": list(artifact_ids), "required_role": roles[0]["id"], "exit_gates": list(gate_ids), "handoff_required": True}]

    run_model = answers.get("run_model") if isinstance(answers.get("run_model"), dict) else {}
    output = {
        "schema_version": 1,
        "id": process_id,
        "name": str(process.get("name") or title_from_id(process_id)),
        "kind": str(process.get("kind") or "project_process"),
        "scope": str(process.get("scope") or "project"),
        "version": str(process.get("version") or "1.0.0"),
        "status": str(process.get("status") or "draft"),
        "description": str(process.get("description") or ""),
        "purpose": str(process.get("purpose") or process.get("description") or ""),
        "run_model": run_model,
        "required_capabilities": string_list(answers.get("required_capabilities")),
        "hooks": answers.get("hooks") if isinstance(answers.get("hooks"), dict) else {
            "emit": [
                {"event": "process.created", "required": True},
                {"event": "process.started", "required": True},
                {"event": "stage.started", "required": True},
                {"event": "stage.completed", "required": True},
                {"event": "artifact.created", "required": True},
                {"event": "review.completed", "required": True},
                {"event": "process.completed", "required": True},
            ],
            "tracking": {"include": ["process_id", "stage_id", "artifact_refs", "assignment_id", "run_id", "task_id", "status"]},
        },
        "roles": roles,
        "stages": stages,
        "artifact_definitions": artifacts,
        "gates": gates,
        "required_packages": string_list(answers.get("required_packages")) or ["process-forge-core"],
        "required_templates": string_list(answers.get("required_templates")) or ["artifact-template"],
        "allowed_tools": string_list(answers.get("allowed_tools")) or ["processforge-cli"],
        "forbidden_actions": string_list(answers.get("forbidden_actions")) or ["write_private_absolute_paths_to_public_files"],
        "evolution_policy": answers.get("evolution_policy") if isinstance(answers.get("evolution_policy"), dict) else {
            "active_run_upgrade": {"default": "manual_only"},
            "safe_changes": ["add_optional_stage", "add_non_blocking_gate"],
            "blocked_changes": ["remove_existing_required_artifact", "weaken_blocking_gate_without_review"],
            "requires_approval": ["change_stage_order", "change_required_artifact_lifecycle"],
        },
    }
    if "expected_artifacts" in answers:
        output["expected_artifacts"] = answers["expected_artifacts"]
    return output


def render_authoring_questions(answers: dict[str, Any]) -> str:
    process = answers.get("process") if isinstance(answers.get("process"), dict) else {}
    return "\n".join(
        [
            f"# Process Authoring Questions: {process.get('name', process.get('id', 'process'))}",
            "",
            "- What concrete outcome must this process produce?",
            "- Which roles own each stage and artifact?",
            "- Which artifacts prove that a stage is complete?",
            "- Which blocking gates can stop apply or completion?",
            "- Does the process need multiple assignment-backed tasks or one linear flow?",
            "- Which examples should prove the generated process is usable?",
            "",
            "Answers are stored in `answers.yaml`; the generated candidate is `draft.process.yaml`.",
        ]
    ) + "\n"


def append_authoring_log(paths: dict[str, Path], message: str) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    line = f"- {now_utc()}: {message}\n"
    with paths["log"].open("a", encoding="utf-8") as handle:
        handle.write(line)


def render_logic_review(process: dict[str, Any], checks: list[Check]) -> str:
    lines = [f"# Process Logic Review: {process.get('id', 'process')}", "", "| Level | Check |", "| --- | --- |"]
    for item in checks:
        lines.append(f"| {item.level} | {item.message} |")
    failures = [item for item in checks if item.level == "FAIL"]
    warnings = [item for item in checks if item.level == "WARN"]
    lines.extend(["", f"Result: `{'fail' if failures else 'pass'}`", f"Failures: `{len(failures)}`", f"Warnings: `{len(warnings)}`", ""])
    return "\n".join(lines)


def validate_process_authoring_logic(process: dict[str, Any], answers: dict[str, Any] | None = None) -> list[Check]:
    checks: list[Check] = []
    text = json.dumps({"process": process, "answers": answers or {}}, ensure_ascii=False)
    checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "authoring data has no private absolute paths"))
    checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "authoring data contains no secret-like values"))
    for key in ["schema_version", "id", "name", "version", "status", "description", "stages", "roles", "artifact_definitions", "gates", "evolution_policy"]:
        checks.append(check("PASS" if key in process else "FAIL", f"process.{key} present"))
    roles = [item for item in as_list(process.get("roles")) if isinstance(item, dict)]
    stages = [item for item in as_list(process.get("stages")) if isinstance(item, dict)]
    artifacts = [item for item in as_list(process.get("artifact_definitions")) if isinstance(item, dict)]
    gates = [item for item in as_list(process.get("gates")) if isinstance(item, dict)]

    def id_values(items: list[dict[str, Any]], label: str) -> set[str]:
        values: list[str] = [safe_id(str(item.get("id", "")), label) for item in items]
        duplicates = sorted({item for item in values if values.count(item) > 1})
        checks.append(check("PASS" if not duplicates else "FAIL", f"{label} ids unique" + (f": {', '.join(duplicates)}" if duplicates else "")))
        return set(values)

    role_ids = id_values(roles, "role")
    artifact_ids = id_values(artifacts, "artifact")
    gate_ids = id_values(gates, "gate")
    stage_ids = id_values(stages, "stage")
    checks.append(check("PASS" if stage_ids else "FAIL", "at least one stage exists"))
    checks.append(check("PASS" if role_ids else "FAIL", "at least one role exists"))
    checks.append(check("PASS" if artifact_ids else "FAIL", "at least one artifact exists"))
    checks.append(check("PASS" if gate_ids else "FAIL", "at least one gate exists"))

    for stage in stages:
        stage_id = safe_id(str(stage.get("id", "")), "stage")
        role_id = safe_id(str(stage.get("required_role", "")), "role")
        checks.append(check("PASS" if role_id in role_ids else "FAIL", f"stage {stage_id} references existing role"))
        for artifact_id in [safe_id(value, "artifact") for value in string_list(stage.get("produced_artifacts"))]:
            checks.append(check("PASS" if artifact_id in artifact_ids else "FAIL", f"stage {stage_id} produces known artifact {artifact_id}"))
        for gate_id in [safe_id(value, "gate") for value in string_list(stage.get("entry_gates")) + string_list(stage.get("exit_gates"))]:
            checks.append(check("PASS" if gate_id in gate_ids else "FAIL", f"stage {stage_id} references known gate {gate_id}"))
    for artifact in artifacts:
        owner = safe_id(str(artifact.get("owner_role", "")), "role")
        checks.append(check("PASS" if owner in role_ids else "FAIL", f"artifact {artifact.get('id', '')} owner role exists"))
    for gate_item in gates:
        gate_id = safe_id(str(gate_item.get("id", "")), "gate")
        required_artifact = gate_item.get("required_artifact")
        if required_artifact:
            artifact_id = safe_id(str(required_artifact), "artifact")
            checks.append(check("PASS" if artifact_id in artifact_ids else "FAIL", f"gate {gate_id} required artifact exists: {artifact_id}"))
    review_index = next((index for index, item in enumerate(stages) if "review" in safe_id(str(item.get("id", "")), "stage")), -1)
    for index, stage in enumerate(stages):
        if bool(stage.get("handoff_required")) and (review_index < 0 or review_index > index):
            checks.append(check("WARN", f"handoff stage {stage.get('id', '')} appears before review"))
    run_model = process.get("run_model") if isinstance(process.get("run_model"), dict) else {}
    task_loop = run_model.get("default_task_loop") if isinstance(run_model.get("default_task_loop"), dict) else {}
    if run_model.get("supports_multiple_tasks") is True:
        loop_enabled = task_loop.get("enabled") is True
        kinds = string_list(task_loop.get("iteration_kinds"))
        checks.append(check("PASS" if loop_enabled and kinds else "FAIL", "multiple-task processes define a default task loop"))
        for kind in kinds:
            checks.append(check("PASS" if kind in ITERATION_KINDS else "FAIL", f"default task loop iteration kind valid: {kind}"))
    return checks


def command_process_authoring_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    raw_answers = load_answers(Path(args.answers).expanduser().resolve()) if args.answers else {}
    fallback_id = args.id or str((raw_answers.get("process") or {}).get("id") if isinstance(raw_answers.get("process"), dict) else raw_answers.get("id") or "new-process")
    answers = normalize_process_authoring_answers(raw_answers, fallback_id, args.title or "")
    if args.description:
        answers["process"]["description"] = args.description
    if getattr(args, "scope", None):
        answers["process"]["scope"] = args.scope
    if getattr(args, "kind", None):
        answers["process"]["kind"] = args.kind
    process_id = safe_id(str(answers["process"]["id"]), "new-process")
    draft = process_from_authoring_answers(answers)
    paths = process_authoring_paths(project_root, process_id)
    planned = [paths["answers"], paths["draft"], paths["questions"], paths["log"]]
    if getattr(args, "dry_run", False):
        print_plan("process-authoring-start dry run", planned, project_root)
        return 0
    write_yaml_file(paths["answers"], answers)
    write_yaml_file(paths["draft"], draft)
    paths["questions"].write_text(render_authoring_questions(answers), encoding="utf-8")
    append_authoring_log(paths, "authoring session started")
    emit_process_event(project_root, "process_authoring.started", process_id=process_id, subject=process_id, payload={"process_id": process_id, "session": rel(paths["root"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.answers.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["answers"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.draft.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["draft"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    print(f"WROTE: {rel(paths['answers'], project_root)}")
    print(f"WROTE: {rel(paths['draft'], project_root)}")
    return 0


def command_process_authoring_review(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    process_id = safe_id(args.process or getattr(args, "id", ""), "process")
    paths = process_authoring_paths(project_root, process_id)
    if not paths["draft"].is_file():
        raise SystemExit(f"FAIL: draft not found: {rel(paths['draft'], project_root)}")
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    draft = read_yaml_file(paths["draft"])
    checks = validate_process_authoring_logic(draft, answers)
    paths["logic_review"].write_text(render_logic_review(draft, checks), encoding="utf-8")
    append_authoring_log(paths, "logic review created")
    result = print_checks(checks)
    emit_process_event(project_root, "process_authoring.logic_review.created", process_id=process_id, subject=process_id, severity="error" if result else "info", payload={"path": rel(paths["logic_review"], project_root), "result": "fail" if result else "pass"}, correlation_id=f"process-authoring-{process_id}")
    print(f"WROTE: {rel(paths['logic_review'], project_root)}")
    return result


def render_process_agent_prompt(process: dict[str, Any]) -> str:
    process_id = str(process.get("id", "process"))
    stages = [item for item in as_list(process.get("stages")) if isinstance(item, dict)]
    lines = [
        f"# {process.get('name', title_from_id(process_id))} Agent",
        "",
        f"Process id: `{process_id}`",
        "",
        "Use the canonical Python launcher:",
        "",
        "```bash",
        f"python bin/pf.py process-doctor --project-root <project-root> --process {process_id}",
        f"python bin/pf.py run-create --project-root <project-root> --id <run-id> --title \"<title>\" --process {process_id} --apply",
        "```",
        "",
        "Rules:",
        "",
        "- Read the process definition before starting work.",
        "- Record durable artifacts for every blocking gate.",
        "- Run review before handoff when the process defines a review stage.",
        "- Keep public files portable and free of secrets.",
        "- Use run, task, iteration, review, and handoff files for traceable work.",
        "",
        "Stages:",
        "",
    ]
    for stage in stages:
        lines.append(f"- `{stage.get('id')}`: {stage.get('title', '')}")
    return "\n".join(lines) + "\n"


def render_process_doc(process: dict[str, Any]) -> str:
    process_id = str(process.get("id", "process"))
    lines = [
        f"# {process.get('name', title_from_id(process_id))}",
        "",
        str(process.get("description", "")),
        "",
        f"- process_id: `{process_id}`",
        f"- version: `{process.get('version', '')}`",
        f"- status: `{process.get('status', '')}`",
        f"- scope: `{process.get('scope', 'project')}`",
        "",
        "## Stages",
        "",
    ]
    for stage in as_list(process.get("stages")):
        if isinstance(stage, dict):
            lines.append(f"- `{stage.get('id')}`: {stage.get('description') or stage.get('title', '')}")
    lines.extend(["", "## Artifacts", ""])
    for artifact in as_list(process.get("artifact_definitions")):
        if isinstance(artifact, dict):
            lines.append(f"- `{artifact.get('id')}`: {artifact.get('title', '')}")
    lines.extend(["", "## Gates", ""])
    for gate_item in as_list(process.get("gates")):
        if isinstance(gate_item, dict):
            lines.append(f"- `{gate_item.get('id')}`: {gate_item.get('description', '')}")
    return "\n".join(lines) + "\n"


def write_process_authoring_example(project_root: Path, process: dict[str, Any], answers: dict[str, Any], review_text: str) -> list[Path]:
    process_id = str(process.get("id", "process"))
    example_root = project_root / "examples" / "process-authoring" / process_id
    files = [
        example_root / "README.md",
        example_root / "answers.yaml",
        example_root / "draft.process.yaml",
        example_root / "logic-review.md",
    ]
    readme = "\n".join(
        [
            f"# Process Authoring Example: {process.get('name', title_from_id(process_id))}",
            "",
            "This example shows the authoring inputs, generated process draft, and logic review produced before apply.",
            "",
            "```bash",
            f"python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/{process_id}/answers.yaml --apply",
            f"python bin/pf.py process-doctor --project-root <project-root> --process {process_id}",
            "```",
            "",
        ]
    )
    files[0].parent.mkdir(parents=True, exist_ok=True)
    files[0].write_text(readme, encoding="utf-8")
    write_yaml_file(files[1], answers)
    write_yaml_file(files[2], process)
    files[3].write_text(review_text, encoding="utf-8")
    dogfood_title = str(process.get("name") or title_from_id(process_id))
    dogfood = {
        example_root / f"process-authoring-{process_id}-report.md": f"# {dogfood_title} Process Authoring Report\n\nStatus: authored and applied through ProcessForge process authoring.\n",
        example_root / f"process-authoring-{process_id}-review.md": f"# {dogfood_title} Process Authoring Review\n\nResult: pass.\n",
        example_root / f"process-authoring-{process_id}-handoff.md": f"# {dogfood_title} Process Authoring Handoff\n\nThe example process is ready for `process-doctor` and task-batch use.\n",
    }
    for path, content in dogfood.items():
        path.write_text(content, encoding="utf-8")
        files.append(path)
    return files


def command_process_authoring_apply(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    process_id = safe_id(args.process or getattr(args, "id", ""), "process")
    paths = process_authoring_paths(project_root, process_id)
    if not paths["draft"].is_file():
        raise SystemExit(f"FAIL: draft not found: {rel(paths['draft'], project_root)}")
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    draft = read_yaml_file(paths["draft"])
    checks = validate_process_authoring_logic(draft, answers)
    review_text = render_logic_review(draft, checks)
    paths["logic_review"].write_text(review_text, encoding="utf-8")
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        emit_process_event(project_root, "process_authoring.failed", process_id=process_id, subject=process_id, severity="error", payload={"failures": [item.message for item in failures]}, correlation_id=f"process-authoring-{process_id}")
        return print_checks(checks)
    target_process = project_root / "processes" / f"{process_id}.yaml"
    target_prompt = project_root / "prompts" / f"{process_id}-agent.md"
    target_doc = project_root / "docs" / "processes" / f"{process_id}.md"
    write_yaml_file(target_process, draft)
    target_prompt.parent.mkdir(parents=True, exist_ok=True)
    target_prompt.write_text(render_process_agent_prompt(draft), encoding="utf-8")
    target_doc.parent.mkdir(parents=True, exist_ok=True)
    target_doc.write_text(render_process_doc(draft), encoding="utf-8")
    example_files = write_process_authoring_example(project_root, draft, answers, review_text)
    report_lines = [
        f"# Process Authoring Apply Report: {process_id}",
        "",
        "- result: `applied`",
        f"- process: `{rel(target_process, project_root)}`",
        f"- prompt: `{rel(target_prompt, project_root)}`",
        f"- docs: `{rel(target_doc, project_root)}`",
        "",
        "## Example Files",
        "",
    ]
    report_lines.extend(f"- `{rel(path, project_root)}`" for path in example_files)
    paths["apply_report"].write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    append_authoring_log(paths, "authoring session applied")
    emit_process_event(project_root, "process.created", process_id=process_id, subject=process_id, payload={"path": rel(target_process, project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.applied", process_id=process_id, subject=process_id, payload={"process": rel(target_process, project_root), "prompt": rel(target_prompt, project_root), "docs": rel(target_doc, project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.completed", process_id=process_id, subject=process_id, payload={"report": rel(paths["apply_report"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    print(f"WROTE: {rel(target_process, project_root)}")
    print(f"WROTE: {rel(target_prompt, project_root)}")
    print(f"WROTE: {rel(target_doc, project_root)}")
    print(f"WROTE: {rel(paths['apply_report'], project_root)}")
    return 0


def command_process_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    raw_answers = load_answers(Path(args.answers).expanduser().resolve()) if args.answers else {}
    fallback_id = args.id or str((raw_answers.get("process") or {}).get("id") if isinstance(raw_answers.get("process"), dict) else raw_answers.get("id") or "new-process")
    answers = normalize_process_authoring_answers(raw_answers, fallback_id, args.title or "")
    process_id = safe_id(str(answers["process"]["id"]), "new-process")
    start_args = argparse.Namespace(project_root=str(project_root), answers=None, id=process_id, title=str(answers["process"]["name"]), description=str(answers["process"]["description"]), dry_run=getattr(args, "dry_run", False))
    if getattr(args, "dry_run", False):
        return command_process_authoring_start(start_args)
    paths = process_authoring_paths(project_root, process_id)
    write_yaml_file(paths["answers"], answers)
    write_yaml_file(paths["draft"], process_from_authoring_answers(answers))
    paths["questions"].write_text(render_authoring_questions(answers), encoding="utf-8")
    append_authoring_log(paths, "authoring session created by process-create")
    emit_process_event(project_root, "process_authoring.started", process_id=process_id, subject=process_id, payload={"process_id": process_id, "session": rel(paths["root"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.answers.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["answers"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    emit_process_event(project_root, "process_authoring.draft.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["draft"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    return command_process_authoring_apply(argparse.Namespace(project_root=str(project_root), process=process_id))


def process_definition_path(project_root: Path, process_or_path: str) -> Path:
    candidate = Path(process_or_path)
    if candidate.suffix in {".yaml", ".yml"}:
        path = candidate if candidate.is_absolute() else project_root / candidate
        if path.is_file():
            return path
    process_id = safe_id(process_or_path, "process")
    for path in [project_root / "processes" / f"{process_id}.yaml", locate_flow_root(project_root) / "processes" / f"{process_id}.yaml", ROOT / "processes" / f"{process_id}.yaml"]:
        if path.is_file():
            return path
    raise SystemExit(f"FAIL: process not found: {process_id}")


def validate_process_definition_files(project_root: Path, process: dict[str, Any], process_path: Path) -> list[Check]:
    process_id = str(process.get("id") or process_path.stem)
    checks = validate_process_authoring_logic(process, {})
    checks.append(check("PASS" if not public_yaml_has_private_path(process) else "FAIL", f"{rel(process_path, project_root)} has no private absolute paths"))
    prompt = project_root / "prompts" / f"{process_id}-agent.md"
    doc = project_root / "docs" / "processes" / f"{process_id}.md"
    example = project_root / "examples" / "process-authoring" / process_id / "README.md"
    checks.append(check("PASS" if prompt.is_file() else "FAIL", f"{rel(prompt, project_root)} exists"))
    checks.append(check("PASS" if doc.is_file() else "FAIL", f"{rel(doc, project_root)} exists"))
    checks.append(check("PASS" if example.is_file() else "FAIL", f"{rel(example, project_root)} exists"))
    return checks


def command_process_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    path = process_definition_path(project_root, args.process)
    process = read_yaml_file(path)
    checks = validate_process_definition_files(project_root, process, path)
    result = print_checks(checks)
    process_id = str(process.get("id") or path.stem)
    emit_process_event(project_root, "process.doctor.failed" if result else "process.doctor.passed", process_id=process_id, severity="error" if result else "info", subject=process_id, payload={"path": rel(path, project_root), "result": "fail" if result else "pass"}, correlation_id=f"process-{process_id}")
    return result


def iter_process_definitions(project_root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    seen: set[str] = set()
    items: list[tuple[str, Path, dict[str, Any]]] = []
    for root in [project_root / "processes", locate_flow_root(project_root) / "processes", ROOT / "processes"]:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.yaml")):
            data = load_yaml_document(path)
            if yaml_error(data):
                continue
            process_id = str(data.get("id") or path.stem)
            if process_id in seen:
                continue
            seen.add(process_id)
            items.append((process_id, path, data))
    return items


def command_process_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    items = iter_process_definitions(project_root)
    if not items:
        print("No processes found.")
        return 0
    for process_id, path, data in items:
        print(f"{process_id}\t{data.get('status', 'unknown')}\t{data.get('version', '')}\t{data.get('name', '')}\t{rel(path, project_root)}")
    return 0


def command_process_describe(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    path = process_definition_path(project_root, args.process)
    data = read_yaml_file(path)
    print(f"PROCESS: {data.get('id', path.stem)}")
    print(f"NAME: {data.get('name', '')}")
    print(f"STATUS: {data.get('status', '')}")
    print(f"VERSION: {data.get('version', '')}")
    print(f"PATH: {rel(path, project_root)}")
    print("STAGES:")
    for stage in as_list(data.get("stages")):
        if isinstance(stage, dict):
            print(f"- {stage.get('id')}: {stage.get('title', '')}")
    print("ROLES:")
    for role in as_list(data.get("roles")):
        if isinstance(role, dict):
            print(f"- {role.get('id')}: {role.get('title', '')}")
    print("ARTIFACTS:")
    for artifact in as_list(data.get("artifact_definitions")):
        if isinstance(artifact, dict):
            print(f"- {artifact.get('id')}: {artifact.get('title', '')}")
    print("GATES:")
    for gate_item in as_list(data.get("gates")):
        if isinstance(gate_item, dict):
            print(f"- {gate_item.get('id')}: {gate_item.get('description', '')}")
    return 0


PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL = {
    "schema_version",
    "id",
    "name",
    "kind",
    "scope",
    "version",
    "status",
    "description",
    "purpose",
    "run_model",
    "required_capabilities",
    "hooks",
    "roles",
    "stages",
    "artifact_definitions",
    "gates",
    "required_packages",
    "required_templates",
    "allowed_tools",
    "forbidden_actions",
    "evolution_policy",
    "expected_artifacts",
}


def process_backfill_root(project_root: Path, process_id: str) -> Path:
    return locate_flow_root(project_root) / "authoring" / "backfill" / "processes" / safe_id(process_id, "process")


def process_backfill_paths(project_root: Path, process_id: str) -> dict[str, Path]:
    root = process_backfill_root(project_root, process_id)
    return {
        "root": root,
        "answers": root / "answers.yaml",
        "draft": root / "draft.process.yaml",
        "source": root / "source.process.yaml",
        "semantic_map": root / "semantic-map.yaml",
        "unsupported": root / "unsupported-fields.yaml",
        "import_report": root / "import-report.md",
    }


def process_to_authoring_answers(process: dict[str, Any]) -> dict[str, Any]:
    process_id = safe_id(str(process.get("id", "process")), "process")
    answers: dict[str, Any] = {
        "schema_version": 1,
        "process": {
            "id": process_id,
            "name": str(process.get("name") or title_from_id(process_id)),
            "version": str(process.get("version") or "1.0.0"),
            "status": str(process.get("status") or "draft"),
            "kind": str(process.get("kind") or "process"),
            "scope": str(process.get("scope") or "project"),
            "description": str(process.get("description") or ""),
            "purpose": str(process.get("purpose") or process.get("description") or ""),
        },
        "run_model": process.get("run_model") if isinstance(process.get("run_model"), dict) else {},
        "roles": as_list(process.get("roles")),
        "stages": as_list(process.get("stages")),
        "artifacts": as_list(process.get("artifact_definitions")),
        "gates": as_list(process.get("gates")),
        "required_capabilities": string_list(process.get("required_capabilities")),
        "required_packages": string_list(process.get("required_packages")),
        "required_templates": string_list(process.get("required_templates")),
        "allowed_tools": string_list(process.get("allowed_tools")),
        "forbidden_actions": string_list(process.get("forbidden_actions")),
    }
    for key in ["hooks", "evolution_policy", "expected_artifacts"]:
        if key in process:
            answers[key] = process[key]
    return answers


def process_unsupported_fields(process: dict[str, Any]) -> list[dict[str, str]]:
    unsupported: list[dict[str, str]] = []
    for key in sorted(process.keys()):
        if key not in PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL:
            unsupported.append({"path": key, "reason": "not represented in process-authoring answers schema"})
    return unsupported


def process_semantic_map(process: dict[str, Any], process_path: Path, project_root: Path, unsupported: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": {"type": "process", "id": str(process.get("id", process_path.stem)), "path": rel(process_path, project_root)},
        "mapped": {
            "id": "process.id",
            "title": "process.name",
            "purpose": "process.description",
            "stages": "stages",
            "roles": "roles",
            "gates": "gates",
            "artifacts": "artifact_definitions",
            "events": "hooks.emit",
            "run_model": "run_model",
            "requirements": "required_packages|required_templates|allowed_tools|required_capabilities",
        },
        "unsupported": unsupported,
    }


def render_process_import_report(process: dict[str, Any], process_path: Path, paths: dict[str, Path], project_root: Path, unsupported: list[dict[str, str]]) -> str:
    status = "WARN" if unsupported else "PASS"
    lines = [
        f"# Process Authoring Import: {process.get('id', process_path.stem)}",
        "",
        "## Result",
        "",
        status,
        "",
        "## Source",
        "",
        f"- Path: `{rel(process_path, project_root)}`",
        f"- Process id: `{process.get('id', process_path.stem)}`",
        "",
        "## Created",
        "",
        f"- `{rel(paths['answers'], project_root)}`",
        f"- `{rel(paths['draft'], project_root)}`",
        f"- `{rel(paths['source'], project_root)}`",
        f"- `{rel(paths['semantic_map'], project_root)}`",
        f"- `{rel(paths['unsupported'], project_root)}`",
        "",
        "## Unsupported Fields",
        "",
    ]
    if unsupported:
        lines.extend(f"- `{item['path']}`: {item['reason']}" for item in unsupported)
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def command_process_authoring_import(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    if args.process_file:
        process_path = Path(args.process_file).expanduser()
        process_path = process_path if process_path.is_absolute() else project_root / process_path
        if not process_path.is_file():
            raise SystemExit(f"FAIL: process file not found: {process_path}")
    elif args.process:
        process_path = process_definition_path(project_root, args.process)
    else:
        raise SystemExit("FAIL: provide --process or --process-file")
    process = read_yaml_file(process_path)
    process_id = safe_id(str(process.get("id") or process_path.stem), "process")
    answers = process_to_authoring_answers(process)
    draft = process_from_authoring_answers(answers)
    unsupported = process_unsupported_fields(process)
    paths = process_backfill_paths(project_root, process_id)
    planned = [paths["answers"], paths["draft"], paths["source"], paths["semantic_map"], paths["unsupported"], paths["import_report"]]
    if getattr(args, "dry_run", False):
        print_plan("process-authoring-import dry run", planned, project_root)
        return 0
    write_yaml_file(paths["answers"], answers)
    write_yaml_file(paths["draft"], draft)
    write_yaml_file(paths["source"], process)
    write_yaml_file(paths["semantic_map"], process_semantic_map(process, process_path, project_root, unsupported))
    write_yaml_file(paths["unsupported"], {"schema_version": 1, "unsupported": unsupported})
    paths["import_report"].write_text(render_process_import_report(process, process_path, paths, project_root, unsupported), encoding="utf-8")
    emit_process_event(project_root, "authoring_parity.started", process_id=process_id, subject=process_id, payload={"command": "process-authoring-import", "source": rel(process_path, project_root)}, correlation_id=f"authoring-parity-{process_id}")
    if unsupported:
        emit_process_event(project_root, "authoring_parity.warning", process_id=process_id, subject=process_id, severity="warn", payload={"unsupported": unsupported}, correlation_id=f"authoring-parity-{process_id}")
    print(f"WROTE: {rel(paths['answers'], project_root)}")
    print(f"WROTE: {rel(paths['draft'], project_root)}")
    print(f"WROTE: {rel(paths['semantic_map'], project_root)}")
    return 0


def sorted_strings(values: Any) -> list[str]:
    return sorted(set(string_list(values)))


def event_emits(process: dict[str, Any]) -> list[str]:
    hooks = process.get("hooks") if isinstance(process.get("hooks"), dict) else {}
    emits = hooks.get("emit") if isinstance(hooks.get("emit"), list) else []
    return sorted({str(item.get("event")) for item in emits if isinstance(item, dict) and item.get("event")})


def object_by_id(items: Any, keys: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in as_list(items):
        if not isinstance(item, dict):
            continue
        item_id = safe_id(str(item.get("id", "")), "item")
        result[item_id] = {key: item.get(key) for key in keys if key in item}
    return result


def process_semantics(process: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": safe_id(str(process.get("id", "")), "process"),
        "title": str(process.get("name") or ""),
        "kind": str(process.get("kind") or ""),
        "scope": str(process.get("scope") or ""),
        "purpose": str(process.get("purpose") or process.get("description") or ""),
        "run_model": process.get("run_model") if isinstance(process.get("run_model"), dict) else {},
        "roles": object_by_id(process.get("roles"), ["title", "responsibility"]),
        "stages": object_by_id(process.get("stages"), ["title", "required_role", "required_inputs", "produced_artifacts", "entry_gates", "exit_gates", "handoff_required"]),
        "artifact_definitions": object_by_id(process.get("artifact_definitions"), ["title", "owner_role", "template", "lifecycle"]),
        "gates": object_by_id(process.get("gates"), ["description", "blocking", "required_artifact", "stage", "stage_id"]),
        "events": {"emits": event_emits(process)},
        "requirements": {
            "required_capabilities": sorted_strings(process.get("required_capabilities")),
            "required_packages": sorted_strings(process.get("required_packages")),
            "required_templates": sorted_strings(process.get("required_templates")),
            "allowed_tools": sorted_strings(process.get("allowed_tools")),
            "forbidden_actions": sorted_strings(process.get("forbidden_actions")),
        },
    }


def compare_process_semantics(source: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    source_sem = process_semantics(source)
    candidate_sem = process_semantics(candidate)
    diffs: list[dict[str, str]] = []

    def add(level: str, area: str, message: str) -> None:
        diffs.append({"level": level, "area": area, "message": message})

    for area in ["id", "run_model"]:
        if source_sem.get(area) != candidate_sem.get(area):
            add("FAIL", area, f"{area} differs")
    for area in ["title", "kind", "scope", "purpose"]:
        if area in {"kind", "scope"} and area not in source:
            continue
        if source_sem.get(area) != candidate_sem.get(area):
            add("WARN", area, f"{area} differs")
    for area in ["roles", "stages", "artifact_definitions", "gates"]:
        source_ids = set(source_sem[area].keys())
        candidate_ids = set(candidate_sem[area].keys())
        for missing in sorted(source_ids - candidate_ids):
            add("FAIL", area, f"{area} missing: {missing}")
        for extra in sorted(candidate_ids - source_ids):
            add("WARN", area, f"{area} extra: {extra}")
    for area, label in [("events", "emits")]:
        source_values = set(source_sem[area][label])
        candidate_values = set(candidate_sem[area][label])
        for missing in sorted(source_values - candidate_values):
            add("FAIL", area, f"event missing: {missing}")
    for key, source_values in source_sem["requirements"].items():
        candidate_values = set(candidate_sem["requirements"].get(key, []))
        for missing in sorted(set(source_values) - candidate_values):
            add("FAIL", key, f"{key} missing: {missing}")
    status = "FAIL" if any(item["level"] == "FAIL" for item in diffs) else ("WARN" if any(item["level"] == "WARN" for item in diffs) else "PASS")
    return status, diffs


def render_process_parity_report(process_id: str, source_path: Path, project_root: Path, status: str, diffs: list[dict[str, str]], unsupported: list[dict[str, str]], logic_checks: list[Check]) -> str:
    lines = [
        f"# Process Parity: {process_id}",
        "",
        "## Result",
        "",
        status,
        "",
        "## Source",
        "",
        f"- Path: `{rel(source_path, project_root)}`",
        f"- Process id: `{process_id}`",
        "",
        "## Authoring Coverage",
        "",
        "| Area | Status | Notes |",
        "|---|---|---|",
    ]
    logic_diff_levels = [item["level"] for item in diffs if item["area"] == "logic_review"]
    logic_status = "FAIL" if "FAIL" in logic_diff_levels else ("WARN" if "WARN" in logic_diff_levels else "PASS")
    lines.append(f"| logic_review | {logic_status} | {len(logic_checks)} checks |")
    lines.append(f"| unsupported_fields | {'WARN' if unsupported else 'PASS'} | {len(unsupported)} unsupported fields |")
    lines.append(f"| semantic_diff | {status} | {len(diffs)} differences |")
    lines.extend(["", "## Semantic Diff", ""])
    if diffs:
        lines.extend(f"- {item['level']} `{item['area']}`: {item['message']}" for item in diffs)
    else:
        lines.append("- No meaningful differences.")
    lines.extend(["", "## Unsupported Fields", ""])
    if unsupported:
        lines.extend(f"- `{item['path']}`: {item['reason']}" for item in unsupported)
    else:
        lines.append("- None.")
    expected_warns = [item for item in diffs if item["level"] == "WARN" and item["area"] in {"logic_review", "unsupported_fields"}]
    action_warns = [item for item in diffs if item["level"] == "WARN" and (item["area"] != "unsupported_fields")]
    lines.extend(["", "## Checked", ""])
    lines.append("- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.")
    lines.append("- Candidate process logic against ProcessForge authoring rules.")
    lines.extend(["", "## Skipped", ""])
    lines.append("- Byte-for-byte YAML formatting and key order are intentionally not compared.")
    lines.extend(["", "## Expected WARN", ""])
    if expected_warns:
        lines.extend(f"- `{item['area']}`: {item['message']}" for item in expected_warns)
    else:
        lines.append("- None.")
    lines.extend(["", "## WARN To Fix Before Public Release", ""])
    if action_warns:
        lines.extend(f"- `{item['area']}`: {item['message']}" for item in action_warns)
    else:
        lines.append("- None.")
    lines.extend(["", "## Recommendation", ""])
    if status == "PASS":
        lines.append("Process is semantically reproducible through authoring import.")
    elif status == "WARN":
        lines.append("Process is reproducible with documented warnings; fix action WARN items before public release.")
    else:
        lines.append("Process is not reproducible enough for release parity; fix FAIL items before public release.")
    return "\n".join(lines) + "\n"


def run_process_parity_check(project_root: Path, process_path: Path, candidate_path: Path | None = None) -> tuple[str, Path, Path, list[dict[str, str]]]:
    source = read_yaml_file(process_path)
    process_id = safe_id(str(source.get("id") or process_path.stem), "process")
    paths = process_backfill_paths(project_root, process_id)
    if not paths["draft"].is_file():
        args = argparse.Namespace(project_root=str(project_root), process=process_id, process_file=str(process_path), dry_run=False)
        command_process_authoring_import(args)
    candidate = read_yaml_file(candidate_path) if candidate_path else read_yaml_file(paths["draft"])
    unsupported = process_unsupported_fields(source)
    status, diffs = compare_process_semantics(source, candidate)
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    logic_checks = validate_process_authoring_logic(candidate, answers)
    source_logic_checks = validate_process_authoring_logic(source, answers)
    source_failures = {item.message for item in source_logic_checks if item.level == "FAIL"}
    candidate_failures = {item.message for item in logic_checks if item.level == "FAIL"}
    introduced_failures = sorted(candidate_failures - source_failures)
    inherited_failures = sorted(candidate_failures & source_failures)
    if introduced_failures:
        status = "FAIL"
        diffs.append({"level": "FAIL", "area": "logic_review", "message": "candidate logic review failed: " + "; ".join(introduced_failures)})
    elif inherited_failures and status == "PASS":
        status = "WARN"
        diffs.append({"level": "WARN", "area": "logic_review", "message": "source definition already has logic review findings: " + "; ".join(inherited_failures)})
    if unsupported and status == "PASS":
        status = "WARN"
    review = locate_flow_root(project_root) / "reviews" / "parity" / "processes" / f"{process_id}-parity.md"
    diff_path = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / f"{process_id}-semantic-diff.yaml"
    review.parent.mkdir(parents=True, exist_ok=True)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(render_process_parity_report(process_id, process_path, project_root, status, diffs, unsupported, logic_checks), encoding="utf-8")
    write_yaml_file(diff_path, {"schema_version": 1, "process_id": process_id, "result": status, "diffs": diffs, "unsupported": unsupported})
    emit_process_event(project_root, "authoring_parity.process.checked", process_id=process_id, subject=process_id, severity="error" if status == "FAIL" else ("warn" if status == "WARN" else "info"), payload={"result": status, "review": rel(review, project_root), "semantic_diff": rel(diff_path, project_root)}, correlation_id=f"authoring-parity-{process_id}")
    if status == "FAIL":
        emit_process_event(project_root, "authoring_parity.failed", process_id=process_id, subject=process_id, severity="error", payload={"diffs": diffs}, correlation_id=f"authoring-parity-{process_id}")
    return status, review, diff_path, diffs


def command_process_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    process_path = Path(args.process_file).expanduser() if getattr(args, "process_file", None) else process_definition_path(project_root, args.process)
    if not process_path.is_absolute():
        process_path = project_root / process_path
    candidate_path = Path(args.candidate_file).expanduser() if getattr(args, "candidate_file", None) else None
    if candidate_path and not candidate_path.is_absolute():
        candidate_path = project_root / candidate_path
    status, review, diff_path, _diffs = run_process_parity_check(project_root, process_path, candidate_path)
    print(f"{status}: {rel(review, project_root)}")
    print(f"DIFF: {rel(diff_path, project_root)}")
    return 1 if status == "FAIL" else 0


CRITICAL_PARITY_PROCESSES = {
    "workplace-initialization",
    "project-onboarding",
    "task-batch-execution",
    "process-authoring",
    "reusable-template-authoring",
    "knowledge-package-authoring",
    "platform-contract-authoring",
}


def command_process_parity_check_all(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    rows: list[dict[str, Any]] = []
    failed = False
    warned = False
    for process_id, path, _data in iter_process_definitions(project_root):
        status, review, diff_path, _diffs = run_process_parity_check(project_root, path)
        rows.append({"process_id": process_id, "result": status, "source": rel(path, project_root), "review": rel(review, project_root), "semantic_diff": rel(diff_path, project_root)})
        failed = failed or status == "FAIL"
        warned = warned or status == "WARN"
        print(f"{status}: {process_id}")
    summary = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / "summary.yaml"
    index = locate_flow_root(project_root) / "reviews" / "parity" / "processes" / "index.md"
    result = "FAIL" if failed else ("WARN" if warned else "PASS")
    counts = {status: sum(1 for item in rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
    write_yaml_file(
        summary,
        {
            "schema_version": 1,
            "result": result,
            "counts": counts,
            "checked": ["process semantic parity", "authoring backfill candidate", "process logic review"],
            "skipped": ["byte-for-byte YAML formatting", "YAML key order"],
            "processes": rows,
        },
    )
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(render_parity_index(rows, "Process Authoring Parity"), encoding="utf-8")
    emit_process_event(project_root, "authoring_parity.completed" if not failed else "authoring_parity.failed", severity="error" if failed else ("warn" if warned else "info"), subject="process-parity-check-all", payload={"summary": rel(summary, project_root), "index": rel(index, project_root), "result": "FAIL" if failed else ("WARN" if warned else "PASS")}, correlation_id="authoring-parity-all")
    print(f"SUMMARY: {rel(summary, project_root)}")
    print(f"INDEX: {rel(index, project_root)}")
    return 1 if failed else 0


def render_parity_index(rows: list[dict[str, Any]], title: str) -> str:
    result = aggregate_status([str(item.get("result", "")) for item in rows])
    counts = {status: sum(1 for item in rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
    lines = [
        f"# {title}",
        "",
        f"Result: `{result}`",
        "",
        "## Summary",
        "",
        f"- PASS: {counts['PASS']}",
        f"- WARN: {counts['WARN']}",
        f"- SKIP: {counts['SKIP']}",
        f"- FAIL: {counts['FAIL']}",
        "",
        "## Checked",
        "",
        "- Semantic parity for process definitions discovered by ProcessForge.",
        "- Generated authoring backfill candidates and semantic diff artifacts.",
        "",
        "## Skipped",
        "",
        "- Byte-for-byte YAML formatting and key order are intentionally not compared.",
        "",
        "## Items",
        "",
        "| Item | Result | Source | Review |",
        "|---|---|---|---|",
    ]
    for item in rows:
        name = str(item.get("process_id") or item.get("id") or "item")
        lines.append(f"| `{name}` | {item.get('result', '')} | `{item.get('source', '')}` | `{item.get('review', '')}` |")
    return "\n".join(lines) + "\n"


def resource_parity_report(project_root: Path, kind: str, resource_id: str, status: str, notes: list[str], source: str = "") -> Path:
    report = locate_flow_root(project_root) / "reviews" / "parity" / "resources" / f"{safe_id(kind + '-' + resource_id, 'resource')}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title_from_id(kind)} Parity: {resource_id}",
        "",
        f"Result: `{status}`",
        "",
        "## Checked",
        "",
        f"- source: `{source or 'not-discovered'}`",
        "",
        "## Skipped",
        "",
    ]
    if status in {"WARN", "SKIP"}:
        lines.append("- Full authoring round-trip for this resource type is not implemented in this MVP.")
    else:
        lines.append("- None.")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in notes)
    lines.extend(["", "## WARN To Fix Before Public Release", ""])
    if status == "WARN":
        lines.append("- Replace shallow resource parity with a full authoring round-trip check.")
    else:
        lines.append("- None.")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit_process_event(project_root, "authoring_parity.resource.checked", subject=f"{kind}/{resource_id}", severity="warn" if status in {"WARN", "SKIP"} else ("error" if status == "FAIL" else "info"), payload={"kind": kind, "id": resource_id, "result": status, "review": rel(report, project_root)}, correlation_id=f"authoring-parity-{safe_id(kind + '-' + resource_id, 'resource')}")
    return report


def command_template_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        require_flow_root(project_root)
    template_id = safe_id(args.template, "template")
    candidates = [project_root / "templates" / f"{template_id}.yaml", project_root / "templates" / f"{template_id}.md", project_root / "templates" / args.template]
    found = next((path for path in candidates if path.is_file()), None)
    if not found:
        report = resource_parity_report(project_root, "template", template_id, "SKIP", ["No template manifest discovery model is available for this id in the project root."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    text = found.read_text(encoding="utf-8", errors="replace")
    status = "FAIL" if not is_public_path_safe(text) or contains_secret_value(text) else "WARN"
    notes = ["Template file is discoverable."]
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "template", template_id, status, notes, rel(found, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0


def command_knowledge_package_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        require_flow_root(project_root)
    package_id = safe_id(args.package, "package")
    path = project_root / "packages" / f"{package_id}.yaml"
    if not path.is_file():
        report = resource_parity_report(project_root, "knowledge-package", package_id, "SKIP", ["Package manifest was not found in project packages/."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    data = read_yaml_file(path)
    notes = ["Package manifest is discoverable.", "Package root is not hardcoded by this parity check.", "Heavy resources are not copied."]
    status = "FAIL" if public_yaml_has_private_path(data) else "WARN"
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "knowledge-package", package_id, status, notes, rel(path, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0


def command_platform_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        require_flow_root(project_root)
    platform_id = safe_id(args.platform, "platform")
    candidates = [project_root / "templates" / f"{platform_id}.yaml", project_root / "templates" / f"{platform_id.replace('platform-', 'platform-contract-')}.yaml"]
    path = next((item for item in candidates if item.is_file()), None)
    if not path:
        report = resource_parity_report(project_root, "platform", platform_id, "SKIP", ["Platform contract was not found through the current project discovery model."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    data = read_yaml_file(path)
    notes = ["Platform contract is discoverable.", "Required and recommended resource references remain in the contract file.", "Referenced packages/templates are not copied into the contract."]
    status = "FAIL" if public_yaml_has_private_path(data) else "WARN"
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "platform", platform_id, status, notes, rel(path, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0


def aggregate_status(statuses: list[str]) -> str:
    normalized = [status for status in statuses if status]
    if not normalized:
        return "SKIP"
    if "FAIL" in normalized:
        return "FAIL"
    if "WARN" in normalized:
        return "WARN"
    if all(status == "SKIP" for status in normalized):
        return "SKIP"
    return "PASS"


def resource_report_status(project_root: Path, kind: str, resource_id: str) -> tuple[str, str]:
    report = locate_flow_root(project_root) / "reviews" / "parity" / "resources" / f"{safe_id(kind + '-' + resource_id, 'resource')}.md"
    if not report.is_file():
        return "SKIP", ""
    text = report.read_text(encoding="utf-8", errors="replace")
    match = re.search("Result:" + r"\s+`(PASS|WARN|SKIP|FAIL)`", text)
    return (match.group(1) if match else "WARN"), rel(report, project_root)


def command_authoring_parity_check_all(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    process_result = command_process_parity_check_all(argparse.Namespace(project_root=str(project_root)))
    process_summary = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / "summary.yaml"
    process_status = "FAIL" if process_result else "PASS"
    if process_summary.is_file():
        process_status = str(read_yaml_file(process_summary).get("result") or process_status)
    resource_rows: list[dict[str, Any]] = []
    for kind, resource_id, func in [
        ("template", "process-agent-prompt", command_template_parity_check),
        ("knowledge-package", "process-forge-core", command_knowledge_package_parity_check),
        ("platform", "platform-contract-example-parent", command_platform_parity_check),
    ]:
        code = func(argparse.Namespace(project_root=str(project_root), template=resource_id, package=resource_id, platform=resource_id))
        status, review = resource_report_status(project_root, kind, resource_id)
        if code:
            status = "FAIL"
        resource_rows.append({"id": resource_id, "kind": kind, "result": status, "review": review})
    summary = locate_flow_root(project_root) / "artifacts" / "parity" / "summary.yaml"
    result = aggregate_status([process_status, *[str(item.get("result", "")) for item in resource_rows]])
    resource_counts = {status: sum(1 for item in resource_rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
    write_yaml_file(
        summary,
        {
            "schema_version": 1,
            "result": result,
            "process_result": process_result,
            "process_status": process_status,
            "resource_counts": resource_counts,
            "checked": ["process parity aggregate", "template resource discovery", "knowledge package resource discovery", "platform contract resource discovery"],
            "skipped": ["full resource authoring round-trip for templates, knowledge packages, and platform contracts"],
            "resources": resource_rows,
        },
    )
    print(f"SUMMARY: {rel(summary, project_root)}")
    return process_result


def command_run_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    run_id = safe_id(args.id, "run")
    path = run_yaml_path(project_root, run_id)
    if path.exists():
        raise SystemExit(f"FAIL: run already exists: {rel(path, project_root)}")
    run = {
        "schema_version": 1,
        "id": run_id,
        "title": args.title,
        "process": safe_id(args.process, "task-batch-execution"),
        "status": args.status,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "objective": args.objective or "",
        "scope": {"type": "project", "project_root": "."},
        "tasks": [],
        "final_artifacts": [],
        "events": {"emitted": ["run.created"]},
        "privacy": {"public_safe": True},
    }
    planned = [path, run_root(project_root, run_id) / "plan.md", run_root(project_root, run_id) / "task-index.md"]
    if getattr(args, "dry_run", False):
        print_plan("run-create dry run", planned, project_root)
        return 0
    root = run_root(project_root, run_id)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "reviews").mkdir(parents=True, exist_ok=True)
    write_yaml_file(path, run)
    (root / "plan.md").write_text(f"# Run Plan: {args.title}\n\nObjective: {args.objective or 'TBD'}\n", encoding="utf-8")
    write_task_index(project_root, run)
    emit_process_event(project_root, "run.created", process_id=run["process"], subject=run_id, payload={"run_id": run_id, "path": rel(path, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_run_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    require_flow_root(project_root)
    root = locate_flow_root(project_root) / "runs"
    runs = sorted(root.glob("*/run.yaml")) if root.is_dir() else []
    if not runs:
        print("No runs found.")
        return 0
    for path in runs:
        data = load_yaml_document(path)
        print(f"{data.get('id', path.parent.name)}\t{data.get('status', 'unknown')}\t{data.get('title', '')}")
    return 0


def command_run_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    tasks = [item for item in run.get("tasks", []) if isinstance(item, dict)] if isinstance(run.get("tasks"), list) else []
    counts: dict[str, int] = {}
    for item in tasks:
        counts[str(item.get("status", "unknown"))] = counts.get(str(item.get("status", "unknown")), 0) + 1
    print(f"RUN: {run.get('id')}")
    print(f"TITLE: {run.get('title')}")
    print(f"STATUS: {run.get('status')}")
    print("TASKS: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) if counts else "TASKS: none")
    for item in sorted(tasks, key=lambda value: int(value.get("order", 0) or 0)):
        task = load_yaml_document(assignment_yaml_path(project_root, str(item.get("id", ""))))
        iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
        latest = iterations[-1] if iterations and isinstance(iterations[-1], dict) else {}
        latest_text = f" latest={latest.get('id')}:{latest.get('kind')}:{latest.get('status')}" if latest else ""
        print(f"- {item.get('order')}: {item.get('id')} [{item.get('status')}]{latest_text}")
    blockers = [str(item.get("id")) for item in tasks if item.get("blocking", True) is not False and str(item.get("status")) in {"blocked", "failed"}]
    if blockers:
        print("BLOCKERS: " + ", ".join(blockers))
    return 0


def command_run_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    checks = validate_run_consistency(project_root, args.run)
    result = print_checks(checks)
    run_id = safe_id(args.run, "run")
    emit_process_event(project_root, "run.doctor.failed" if result else "run.doctor.passed", severity="error" if result else "info", subject=run_id, payload={"run_id": run_id, "result": "fail" if result else "pass"}, correlation_id=f"run-{run_id}")
    return result


def command_run_summary(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    summary = run_root(project_root, run_id) / "summary.md"
    handoff = locate_flow_root(project_root) / "handoffs" / "runs" / f"{run_id}-handoff.md"
    lines = [f"# Run Summary: {run.get('title', run_id)}", "", f"- run_id: `{run_id}`", f"- status: `{run.get('status')}`", "", "## Tasks", ""]
    for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
        if isinstance(item, dict):
            task = load_yaml_document(assignment_yaml_path(project_root, str(item.get("id", ""))))
            result = task.get("result") if isinstance(task.get("result"), dict) else {}
            lines.append(f"- `{item.get('id')}`: `{item.get('status')}` - {result.get('summary', task.get('title', ''))}")
    if len(lines) == 7:
        lines.append("- No tasks recorded.")
    handoff_text = f"# Run Handoff: {run_id}\n\nStatus: `{run.get('status')}`\n\nSummary: `{rel(summary, project_root)}`\n"
    if getattr(args, "dry_run", False):
        print_plan("run-summary dry run", [summary, handoff], project_root)
        return 0
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(handoff_text, encoding="utf-8")
    artifacts = [rel(summary, project_root), rel(handoff, project_root)]
    run["final_artifacts"] = artifacts
    emitted = run.setdefault("events", {}).setdefault("emitted", []) if isinstance(run.setdefault("events", {}), dict) else []
    if isinstance(emitted, list) and "run.summary.created" not in emitted:
        emitted.append("run.summary.created")
    save_run(project_root, run)
    emit_process_event(project_root, "run.summary.created", process_id=str(run.get("process", "")), subject=run_id, payload={"run_id": run_id, "artifacts": artifacts}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(summary, project_root)}")
    print(f"WROTE: {rel(handoff, project_root)}")
    return 0


def command_run_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    tasks = [item for item in run.get("tasks", []) if isinstance(item, dict)] if isinstance(run.get("tasks"), list) else []
    incomplete = [str(item.get("id")) for item in tasks if item.get("blocking", True) is not False and str(item.get("status")) != "done"]
    if incomplete:
        raise SystemExit("FAIL: blocking tasks are not done: " + ", ".join(incomplete))
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete run {run_id}")
        return 0
    run["status"] = "completed"
    emitted = run.setdefault("events", {}).setdefault("emitted", []) if isinstance(run.setdefault("events", {}), dict) else []
    if isinstance(emitted, list) and "run.completed" not in emitted:
        emitted.append("run.completed")
    save_run(project_root, run)
    emit_process_event(project_root, "run.completed", process_id=str(run.get("process", "")), subject=run_id, payload={"run_id": run_id}, correlation_id=f"run-{run_id}")
    print(f"COMPLETED: {run_id}")
    return 0


def command_task_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    task_id = safe_id(args.id, "task")
    path = assignment_yaml_path(project_root, task_id)
    if path.exists():
        raise SystemExit(f"FAIL: task already exists: {rel(path, project_root)}")
    tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
    if any(isinstance(item, dict) and item.get("id") == task_id for item in tasks):
        raise SystemExit(f"FAIL: run already contains task id: {task_id}")
    order = args.order or (len(tasks) + 1)
    task = {
        "schema_version": 1,
        "id": task_id,
        "title": args.title,
        "run_id": run_id,
        "process": safe_id(args.process, "task"),
        "status": "open",
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "objective": args.objective or "",
        "order": order,
        "dependencies": {"blocked_by": [], "blocks": []},
        "iterations": [],
        "result": {"status": "pending", "summary": "", "artifacts": []},
    }
    allowed_files = assignment_scope_items([*as_list(getattr(args, "allowed_file", [])), *as_list(getattr(args, "allowed_glob", []))])
    allowed_read_files = assignment_scope_items([*as_list(getattr(args, "read_file", [])), *as_list(getattr(args, "allowed_read_file", []))])
    context_artifacts = normalize_context_artifacts(getattr(args, "context_artifact", []))
    required_sources = assignment_scope_items(getattr(args, "required_source", []))
    forbidden_files = assignment_scope_items([*as_list(getattr(args, "forbidden_file", [])), *as_list(getattr(args, "forbidden_glob", []))])
    required_outputs = normalize_required_outputs(getattr(args, "required_output", []))
    if getattr(args, "execution_mode", None):
        task["execution_mode"] = normalize_execution_mode(args.execution_mode)
        if task["execution_mode"]["kind"] == "implementation":
            task["execution_mode"]["code_changes_allowed"] = True
    if context_artifacts:
        task["context_artifacts"] = context_artifacts
    if required_sources:
        task["required_sources"] = required_sources
    if allowed_files:
        task["allowed_files"] = allowed_files
    if allowed_read_files:
        task["allowed_read_files"] = allowed_read_files
    if forbidden_files:
        task["forbidden_files"] = forbidden_files
    writer = str(getattr(args, "writer", "true")).lower() == "true"
    if allowed_files or getattr(args, "owner", None) or getattr(args, "role", None) or not writer:
        task["ownership"] = {
            "owner_id": safe_id(getattr(args, "owner", None) or task_id, "assignment"),
            "owner_label": f"worker-{safe_id(getattr(args, 'owner', None) or task_id, 'assignment')}",
            "role": getattr(args, "role", None) or "",
            "writer": writer,
            "owned_files": allowed_files if writer else [],
            "owned_globs": [],
        }
    if allowed_files or forbidden_files:
        task["non_overlap"] = {
            "policy": "block_on_write_overlap",
            "active_parallel_tasks": [],
            "current_write_scope": assignment_write_scope(task),
            "rule": "Do not edit files owned by active parallel tasks.",
        }
    if required_outputs:
        task["required_outputs"] = required_outputs
    expected_report: dict[str, Any] = {}
    if getattr(args, "expected_report_language", None):
        expected_report["language"] = args.expected_report_language
    if getattr(args, "expected_report_artifact", None):
        expected_report["artifact"] = normalize_assignment_path(args.expected_report_artifact)
    if expected_report:
        expected_report.setdefault("format", "concise_markdown")
        expected_report.setdefault("include", [item["id"] for item in required_outputs])
        task["expected_report"] = expected_report
    overlap_check = validate_assignment_scope_overlaps(project_root, task, assignment_path=path)
    if overlap_check["status"] == "fail" and not getattr(args, "force_with_handoff", False):
        raise SystemExit("FAIL: task write scope overlaps active assignments: " + dump_yaml(overlap_check))
    if overlap_check["status"] == "fail":
        task.setdefault("non_overlap", {})["overlap_check"] = overlap_check
    planned = [path, task_artifacts_root(project_root, run_id, task_id), run_root(project_root, run_id) / "task-index.md"]
    if getattr(args, "dry_run", False):
        print_plan("task-create dry run", planned, project_root)
        if allowed_files or forbidden_files:
            print("WRITE_SCOPE:")
            for item in assignment_write_scope(task):
                print(f"- {item}")
            print("OVERLAP_CHECK: " + overlap_check["status"])
        return 0
    task_artifacts_root(project_root, run_id, task_id).mkdir(parents=True, exist_ok=True)
    write_yaml_file(path, task)
    tasks.append({"id": task_id, "assignment": rel(path, project_root), "status": "open", "order": order, "blocking": True})
    run["tasks"] = tasks
    save_run(project_root, run)
    for event_type in ["task.created", "assignment.created"]:
        emit_process_event(project_root, event_type, process_id=task["process"], subject=task_id, assignment_id_value=task_id, assignment_path=rel(path, project_root), payload={"run_id": run_id, "task_id": task_id, "path": rel(path, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_task_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    for item in sorted([task for task in run.get("tasks", []) if isinstance(task, dict)], key=lambda value: int(value.get("order", 0) or 0)):
        print(f"{item.get('order')}\t{item.get('id')}\t{item.get('status')}\t{item.get('assignment')}")
    return 0


def command_task_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = load_task(project_root, task_id)
    task["status"] = "in_progress"
    save_task(project_root, task)
    update_run_task_status(project_root, str(task.get("run_id", "")), task_id, "in_progress")
    for event_type in ["task.started", "assignment.started"]:
        emit_process_event(project_root, event_type, process_id=task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(assignment_yaml_path(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id}, correlation_id=f"run-{task.get('run_id')}")
    print(f"STARTED: {task_id}")
    return 0


def command_task_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = load_task(project_root, task_id)
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete task {task_id}")
        return 0
    artifacts = [item for item in (args.artifact or [])]
    task["status"] = "done"
    task["result"] = {"status": "done", "summary": args.summary, "artifacts": artifacts}
    save_task(project_root, task)
    update_run_task_status(project_root, str(task.get("run_id", "")), task_id, "done")
    for event_type in ["task.completed", "assignment.completed"]:
        emit_process_event(project_root, event_type, process_id=task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(assignment_yaml_path(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "summary": args.summary}, correlation_id=f"run-{task.get('run_id')}")
    print(f"DONE: {task_id}")
    return 0


def command_task_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    checks = validate_task_consistency(project_root, task_id)
    result = print_checks(checks)
    emit_process_event(project_root, "task.doctor.failed" if result else "task.doctor.passed", severity="error" if result else "info", subject=task_id, assignment_id_value=task_id, assignment_path=rel(assignment_yaml_path(project_root, task_id), project_root), payload={"task_id": task_id, "result": "fail" if result else "pass"})
    return result


def command_iteration_add(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = load_task(project_root, task_id)
    kind = safe_id(args.kind, "work")
    if kind not in ITERATION_KINDS:
        raise SystemExit(f"FAIL: invalid iteration kind: {kind}")
    status = args.status
    if status not in ITERATION_STATUSES:
        raise SystemExit(f"FAIL: invalid iteration status: {status}")
    iter_id = safe_id(args.id, "iter") if args.id else next_iteration_id(task)
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    if any(isinstance(item, dict) and item.get("id") == iter_id for item in iterations):
        raise SystemExit(f"FAIL: duplicate iteration id: {iter_id}")
    artifact_kind = "debug-log.md" if kind == "debug" else "work-log.md"
    artifact = rel(task_artifacts_root(project_root, str(task.get("run_id", "")), task_id) / artifact_kind, project_root)
    iteration = {"id": iter_id, "kind": kind, "status": status, "started_at": now_utc(), "summary": args.summary, "artifacts": [artifact]}
    if status in {"completed", "passed", "failed", "cancelled"}:
        iteration["completed_at"] = now_utc()
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would add {iter_id} to {task_id}")
        return 0
    task_artifacts_root(project_root, str(task.get("run_id", "")), task_id).mkdir(parents=True, exist_ok=True)
    iterations.append(iteration)
    task["iterations"] = iterations
    if status == "in_progress":
        task["status"] = "debugging" if kind == "debug" else "in_progress"
    save_task(project_root, task)
    emit_process_event(project_root, "iteration.added", process_id=task_process_id(task), subject=iter_id, assignment_id_value=task_id, assignment_path=rel(assignment_yaml_path(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "iteration_id": iter_id, "kind": kind, "status": status}, correlation_id=f"run-{task.get('run_id')}")
    print(f"ADDED: {iter_id}")
    return 0


def command_iteration_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = load_task(project_root, task_id)
    status = args.status
    if status not in ITERATION_STATUSES:
        raise SystemExit(f"FAIL: invalid iteration status: {status}")
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    found = False
    for item in iterations:
        if isinstance(item, dict) and item.get("id") == args.iteration:
            item["status"] = status
            item["completed_at"] = now_utc()
            if args.summary:
                item["summary"] = args.summary
            found = True
            break
    if not found:
        raise SystemExit(f"FAIL: iteration not found: {args.iteration}")
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete iteration {args.iteration}")
        return 0
    task["iterations"] = iterations
    save_task(project_root, task)
    emit_process_event(project_root, "iteration.completed" if status in {"completed", "passed"} else "iteration.failed", process_id=task_process_id(task), subject=args.iteration, assignment_id_value=task_id, assignment_path=rel(assignment_yaml_path(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "iteration_id": args.iteration, "status": status}, correlation_id=f"run-{task.get('run_id')}")
    print(f"UPDATED: {args.iteration}")
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
    workplace_manifest_path: Path | None = None

    if manifest.is_file():
        checks.append(check("PASS", f"{rel(manifest, project_root)} found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "public manifest contains no secret values"))
        manifest_data = load_yaml_document(manifest)
    else:
        checks.append(
            check_with_hint(
                "FAIL",
                f"{rel(manifest, project_root)} missing",
                "The project has not been onboarded into ProcessForge or the .pf flow root is incomplete.",
                "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply",
            )
        )
        manifest_data = {}

    distribution_root: Path | None = None
    if local_manifest.is_file():
        checks.append(check("PASS", "process-forge.local.yaml found"))
        workplace = resolve_workplace_manifest(local_manifest)
        if workplace and workplace.is_file():
            workplace_manifest_path = workplace
            checks.append(check("PASS", "workplace manifest is reachable"))
            registry = resolve_registry_path(workplace, "distributions", "distributions.yaml")
            checks.append(check("PASS" if registry.is_file() else "FAIL", "workplace distributions registry is reachable"))
            distribution_root = resolve_distribution_path(workplace, "processforge")
        else:
            checks.append(
                check_with_hint(
                    "FAIL",
                    "workplace manifest is missing or unreachable",
                    "The local project config points to a workplace manifest that cannot be read.",
                    "update .pf/process-forge.local.yaml so manifest points to an existing workplace.yaml",
                )
            )
    else:
        workplace_data = manifest_data.get("workplace", {}) if isinstance(manifest_data.get("workplace"), dict) else {}
        if workplace_data.get("reference") == "auto":
            auto_workplace_mode = True
            checks.append(check("PASS", "process-forge.local.yaml omitted by explicit workplace.reference auto mode"))
            distribution_root = project_root
        else:
            checks.append(
                check_with_hint(
                    "FAIL",
                    "process-forge.local.yaml missing",
                    "Linked projects need private local workplace/distribution coordinates.",
                    "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply",
                    "set workplace.reference: auto only for self-contained distribution dogfooding projects",
                )
            )

    checks.extend(distribution_checks(distribution_root))
    checks.extend(validate_hooks_config(project_root))

    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for entry in [".pf/process-forge.local.yaml", ".pf/runtime/", ".pf/cache/"]:
            checks.append(
                check("PASS", f".gitignore contains {entry}")
                if entry in ignore_text
                else check_with_hint(
                    "FAIL",
                    f".gitignore missing {entry}",
                    "Private local config and runtime data must stay out of public project files.",
                    f"add {entry} to .gitignore",
                )
            )
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
        checks.append(check("FAIL", """required platform contract is missing from workplace registry
Why:
  The selected project type requires platform knowledge and rules.
Fix:
  python bin/pf.py platform-contract-install --workplace <workplace-root> --id <platform> --apply"""))
    if report_section_has_items(resource_report, "## Missing Required Platform Resources"):
        checks.append(check("FAIL", """required platform resources are missing from workplace registries
Why:
  A platform contract declared required packages, tools, MCP providers, or templates that are not registered.
Fix:
  Register the missing resource in the workplace registry, then rerun project-onboard or project-context-refresh."""))
    if report_section_has_items(resource_report, "## Missing Recommended Platform Resources"):
        checks.append(check("WARN", "recommended platform resources are missing from workplace registries"))
    checks.extend(public_snapshot_path_checks(project_root))
    checks.extend(project_knowledge_resource_index_checks(project_root, distribution_root, workplace_manifest_path))

    for rel_path in [
        "START_AGENT_HERE.md",
        "runtime/bin/pf.py",
        "assignments/first-assignment.yaml",
        "artifacts/project-profile.md",
        "artifacts/project-classification-report.md",
        "artifacts/repository-map.md",
        "artifacts/project-conventions.md",
        "artifacts/global-resource-matching-report.md",
        "artifacts/project-init-proposal.md",
        "artifacts/project-onboarding-report.md",
        "reviews/project-init-review.md",
        "reviews/project-onboarding-review.md",
        "handoffs/project-ready-handoff.md",
    ]:
        path = flow_root / rel_path
        if path.is_file():
            checks.append(check("PASS", f"{rel(path, project_root)} found"))
        elif auto_workplace_mode:
            checks.append(check("WARN", f"{rel(path, project_root)} missing"))
        elif rel_path == "runtime/bin/pf.py":
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{rel(path, project_root)} missing",
                    "A linked project needs its local Python launcher because it does not contain ProcessForge core tools.",
                    "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply",
                )
            )
        elif rel_path.startswith("contexts/project-context.snapshot"):
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{rel(path, project_root)} missing",
                    "The project context snapshot is stale or absent.",
                    "python .pf/runtime/bin/pf.py project-context-refresh --project-root .",
                )
            )
        else:
            checks.append(check("FAIL", f"{rel(path, project_root)} missing"))
    return print_checks(checks)


UPDATE_PROVIDER_TYPES = {
    "processforge_json",
    "processforge_json_file",
    "github_releases",
    "gitverse_releases",
    "gitlab_releases",
    "generic_http_directory",
    "tuf_repository",
}

UPDATE_SUBJECT_TYPES = {
    "*",
    "processforge_distribution",
    "knowledge_package",
    "knowledge_resource",
    "process_definition",
    "template",
    "tool",
    "mcp_server",
    "platform_contract",
    "package",
}

UPDATE_SOURCE_PUBLIC_KEYS = [
    "id",
    "type",
    "priority",
    "url",
    "path",
    "owner",
    "repo",
    "api_base_url",
    "channels",
    "include_prereleases",
    "asset_patterns",
    "trust",
]

UPDATE_SOURCE_LOCAL_KEYS = [
    "auth_ref",
    "auth",
    "headers_env",
    "query_env",
    "custom_headers_env",
    "channel_override",
]


def update_workplace_root(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.name == "workplace.yaml":
        return path.parent
    return path


def update_registry_file(workplace_root: Path, registry_key: str, default_name: str) -> Path:
    manifest = workplace_root / "workplace.yaml"
    if manifest.is_file():
        data = load_yaml_document(manifest)
        registries = data.get("registries") if isinstance(data, dict) else None
        raw = registries.get(registry_key) if isinstance(registries, dict) else None
        if isinstance(raw, str) and raw.strip():
            return path_resolution_to_path(workplace_path_resolution(workplace_root, raw))
    return workplace_root / "registries" / default_name


def update_source_registry_path(workplace_root: Path) -> Path:
    return update_registry_file(workplace_root, "update_sources", "update-sources.yaml")


def installed_subjects_registry_path(workplace_root: Path) -> Path:
    return update_registry_file(workplace_root, "installed_subjects", "installed-subjects.yaml")


def update_site_overrides_path(workplace_root: Path) -> Path:
    return update_registry_file(workplace_root, "update_site_overrides", "update-site-overrides.yaml")


def derived_installed_update_sites_path(workplace_root: Path) -> Path:
    return workplace_root / "runtime" / "update" / "installed-update-sites.json"


def load_update_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = load_yaml_document(path)
    return data if isinstance(data, dict) and not yaml_error(data) else {}


def update_location(source: dict[str, Any], provider_key: str) -> str:
    provider = str(source.get(provider_key) or "")
    if provider in {"processforge_json", "generic_http_directory", "tuf_repository"}:
        return str(source.get("url") or "")
    if provider == "processforge_json_file":
        return str(source.get("path") or "")
    if provider in {"github_releases", "gitverse_releases", "gitlab_releases"}:
        owner = str(source.get("owner") or "")
        repo = str(source.get("repo") or "")
        return f"{owner}/{repo}" if owner or repo else ""
    return ""


def source_requires_https(source: dict[str, Any], defaults: dict[str, Any] | None = None) -> bool:
    trust = source.get("trust") if isinstance(source.get("trust"), dict) else {}
    if "require_https" in trust:
        return bool(trust.get("require_https"))
    if defaults and "require_https" in defaults:
        return bool(defaults.get("require_https"))
    return True


def append_update_source_checks(
    checks: list[Check],
    source: Any,
    label: str,
    *,
    provider_key: str,
    defaults: dict[str, Any] | None = None,
    require_subjects: bool = False,
) -> None:
    if not isinstance(source, dict):
        checks.append(check("FAIL", f"{label} must be an object"))
        return

    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id.strip():
        checks.append(check("FAIL", f"{label} missing id"))
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", source_id):
        checks.append(check("FAIL", f"{label} id must use letters, digits, dot, underscore, or hyphen"))

    enabled = source.get("enabled")
    if not isinstance(enabled, bool):
        checks.append(check("FAIL", f"{label} missing boolean enabled"))

    provider = source.get(provider_key)
    if not isinstance(provider, str) or not provider.strip():
        checks.append(check("FAIL", f"{label} missing {provider_key}"))
    elif provider not in UPDATE_PROVIDER_TYPES:
        checks.append(check("FAIL", f"{label} unsupported {provider_key} {provider!r}"))

    if "priority" in source and not isinstance(source.get("priority"), int):
        checks.append(check("FAIL", f"{label} priority must be an integer"))

    channels = source.get("channels")
    if channels is not None and (
        not isinstance(channels, list) or not all(isinstance(item, str) and item.strip() for item in channels)
    ):
        checks.append(check("FAIL", f"{label} channels must be a list of non-empty strings"))

    if require_subjects:
        subjects = source.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            checks.append(check("FAIL", f"{label} missing subjects"))
        else:
            for index, subject in enumerate(subjects):
                subject_label = f"{label}.subjects[{index}]"
                if not isinstance(subject, dict):
                    checks.append(check("FAIL", f"{subject_label} must be an object"))
                    continue
                subject_type = subject.get("type")
                ids = subject.get("ids")
                if subject_type not in UPDATE_SUBJECT_TYPES:
                    checks.append(check("FAIL", f"{subject_label}.type unsupported subject type {subject_type!r}"))
                if not isinstance(ids, list) or not all(isinstance(item, str) and item.strip() for item in ids):
                    checks.append(check("FAIL", f"{subject_label}.ids must be a list of non-empty strings"))

    provider_text = str(provider or "")
    if provider_text in {"processforge_json", "generic_http_directory", "tuf_repository"}:
        url = source.get("url")
        if not isinstance(url, str) or not url.strip():
            checks.append(check("FAIL", f"{label} provider {provider_text} requires url"))
        elif source_requires_https(source, defaults) and urlparse(url).scheme.lower() != "https":
            checks.append(check("FAIL", f"{label} url must use https unless local trust policy disables require_https"))
    elif provider_text == "processforge_json_file":
        if not isinstance(source.get("path"), str) or not str(source.get("path")).strip():
            checks.append(check("FAIL", f"{label} provider processforge_json_file requires path"))
    elif provider_text in {"github_releases", "gitverse_releases", "gitlab_releases"}:
        for key in ("owner", "repo"):
            if not isinstance(source.get(key), str) or not str(source.get(key)).strip():
                checks.append(check("FAIL", f"{label} provider {provider_text} requires {key}"))

    auth = source.get("auth")
    if isinstance(auth, dict):
        for key in auth:
            if str(key).lower() in {"token", "password", "secret", "authorization", "api_key"}:
                checks.append(check("FAIL", f"{label} auth must not contain raw secret key {key!r}; use *_env or auth_ref"))


def validate_update_source_registry_data(data: dict[str, Any], path: Path) -> list[Check]:
    checks: list[Check] = []
    if not data:
        return [check("FAIL", f"{path} missing or invalid")]
    if data.get("schema_version") != 1:
        checks.append(check("FAIL", "update source registry schema_version must be 1"))
    if data.get("product") != "processforge":
        checks.append(check("FAIL", "update source registry product must be processforge"))
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    sources = data.get("sources")
    if not isinstance(sources, list):
        checks.append(check("FAIL", "update source registry sources must be a list"))
        return checks

    seen: set[str] = set()
    for index, source in enumerate(sources):
        source_id = source.get("id") if isinstance(source, dict) else None
        if isinstance(source_id, str):
            if source_id in seen:
                checks.append(check("FAIL", f"sources[{index}] duplicate id {source_id}"))
            seen.add(source_id)
        append_update_source_checks(
            checks,
            source,
            f"sources[{index}]",
            provider_key="provider",
            defaults=defaults,
            require_subjects=True,
        )
    if not checks:
        checks.append(check("PASS", f"{path} valid"))
    return checks


def sorted_update_sources(data: dict[str, Any]) -> list[dict[str, Any]]:
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    indexed = [(index, source) for index, source in enumerate(sources) if isinstance(source, dict)]
    indexed.sort(key=lambda item: (not bool(item[1].get("enabled")), int(item[1].get("priority", 1000)), item[0]))
    return [source for _, source in indexed]


def print_update_source_list(data: dict[str, Any], *, json_output: bool = False) -> int:
    sources = sorted_update_sources(data)
    if json_output:
        print(json.dumps({"schema_version": 1, "sources": sources}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("ID\tENABLED\tPRIORITY\tPROVIDER\tCHANNELS\tLOCATION")
    for source in sources:
        channels = ",".join(str(item) for item in source.get("channels", [])) if isinstance(source.get("channels"), list) else ""
        print(
            "\t".join(
                [
                    str(source.get("id", "")),
                    str(bool(source.get("enabled", False))).lower(),
                    str(source.get("priority", "")),
                    str(source.get("provider", "")),
                    channels,
                    update_location(source, "provider"),
                ]
            )
        )
    return 0


def command_update_bootstrap_source_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = update_source_registry_path(workplace_root)
    data = load_update_yaml(path)
    if not data:
        print(f"FAIL: update source registry not found or invalid: {path}")
        return 1
    return print_update_source_list(data, json_output=args.json)


def command_update_bootstrap_source_validate(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = update_source_registry_path(workplace_root)
    checks = validate_update_source_registry_data(load_update_yaml(path), path)
    return print_checks(checks)


def command_update_sources(args: argparse.Namespace) -> int:
    if not args.list and not args.validate:
        print("FAIL: choose --list or --validate")
        return 1
    if args.validate:
        status = command_update_bootstrap_source_validate(args)
        if status != 0 or not args.list:
            return status
    return command_update_bootstrap_source_list(args)


def update_manifest_candidates_under(root: Path, patterns: list[str]) -> list[Path]:
    if not root.is_dir():
        return []
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(sorted(root.glob(pattern)))
    return [path.resolve() for path in candidates if path.is_file()]


def update_resolved_registry_paths(workplace_root: Path, registry_name: str, collection_key: str) -> list[Path]:
    data = load_update_yaml(workplace_root / "registries" / registry_name)
    entries = data.get(collection_key) if isinstance(data.get(collection_key), list) else []
    paths: list[Path] = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(path_resolution_to_path(workplace_path_resolution(workplace_root, str(entry.get("path")))))
    return paths


def update_entity_manifest_records(workplace_root: Path) -> list[dict[str, Any]]:
    manifest = workplace_root / "workplace.yaml"
    records: list[dict[str, Any]] = []
    seen: set[Path] = set()

    package_roots = workplace_package_root_paths(manifest if manifest.is_file() else None)
    if not package_roots:
        package_roots = [path_resolution_to_path(workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/packages"))]
    for root in package_roots:
        for path in update_manifest_candidates_under(root, ["*.yaml", "*.yml", "*/package.yaml", "*/package.yml"]):
            if path in seen:
                continue
            seen.add(path)
            data = load_update_yaml(path)
            if not data.get("id"):
                continue
            records.append(
                {
                    "type": "knowledge_package",
                    "id": str(data.get("id")),
                    "scope": str(data.get("scope") or "global"),
                    "version": str(data.get("version") or ""),
                    "manifest_path": path,
                    "data": data,
                }
            )

    process_root = path_resolution_to_path(workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/processes"))
    for path in update_manifest_candidates_under(process_root, ["*.yaml", "*.yml"]):
        data = load_update_yaml(path)
        if data.get("id"):
            records.append(
                {
                    "type": "process_definition",
                    "id": str(data.get("id")),
                    "scope": "global",
                    "version": str(data.get("version") or ""),
                    "manifest_path": path,
                    "data": data,
                }
            )

    template_roots = update_resolved_registry_paths(workplace_root, "templates.yaml", "template_roots")
    if not template_roots:
        template_roots = [path_resolution_to_path(workplace_path_resolution(workplace_root, "${PF_TEMPLATES}"))]
    for root in template_roots:
        for path in update_manifest_candidates_under(root, ["*.yaml", "*.yml", "*/template.yaml", "*/template.yml"]):
            data = load_update_yaml(path)
            if data.get("id"):
                records.append(
                    {
                        "type": "template",
                        "id": str(data.get("id")),
                        "scope": str(data.get("scope") or "global"),
                        "version": str(data.get("version") or ""),
                        "manifest_path": path,
                        "data": data,
                    }
                )

    platform_roots = update_resolved_registry_paths(workplace_root, "platform-contract-roots.yaml", "platform_contract_roots")
    if not platform_roots:
        platform_roots = [
            path_resolution_to_path(workplace_path_resolution(workplace_root, "${PF_PLATFORM_CONTRACTS}")),
            path_resolution_to_path(workplace_path_resolution(workplace_root, "${PF_WORKPLACE}/platforms")),
        ]
    for root in platform_roots:
        for path in update_manifest_candidates_under(root, ["*.yaml", "*.yml", "*/platform.yaml", "*/platform.yml", "*/platform-contract.yaml", "*/platform-contract.yml"]):
            data = load_update_yaml(path)
            if data.get("id") and data.get("type") == "platform_contract":
                records.append(
                    {
                        "type": "platform_contract",
                        "id": str(data.get("id")),
                        "scope": "global",
                        "version": str(data.get("version") or ""),
                        "manifest_path": path,
                        "data": data,
                    }
                )

    tools_path = workplace_root / "registries" / "tools.yaml"
    tools_data = load_update_yaml(tools_path)
    for entry in tools_data.get("tools", []) if isinstance(tools_data.get("tools"), list) else []:
        if isinstance(entry, dict) and entry.get("id"):
            records.append(
                {
                    "type": "tool",
                    "id": str(entry.get("id")),
                    "scope": str(entry.get("scope") or "global"),
                    "version": str(entry.get("version") or ""),
                    "manifest_path": tools_path,
                    "data": entry,
                }
            )

    mcp_path = workplace_root / "registries" / "mcp.yaml"
    mcp_data = load_update_yaml(mcp_path)
    for entry in mcp_data.get("mcp_servers", []) if isinstance(mcp_data.get("mcp_servers"), list) else []:
        if isinstance(entry, dict) and entry.get("id"):
            records.append(
                {
                    "type": "mcp_server",
                    "id": str(entry.get("id")),
                    "scope": str(entry.get("scope") or "global"),
                    "version": str(entry.get("version") or ""),
                    "manifest_path": mcp_path,
                    "data": entry,
                }
            )
    return records


def update_site_stable_key(subject_type: str, subject_id: str, source_id: str) -> str:
    return f"{subject_type}:{subject_id}:{source_id}"


def update_site_overrides(workplace_root: Path) -> dict[str, dict[str, Any]]:
    path = update_site_overrides_path(workplace_root)
    data = load_update_yaml(path)
    overrides = data.get("overrides") if isinstance(data.get("overrides"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for item in overrides:
        if not isinstance(item, dict):
            continue
        key = item.get("site_id") if isinstance(item.get("site_id"), str) else None
        subject = item.get("subject") if isinstance(item.get("subject"), dict) else {}
        update_site_id = item.get("update_site_id") or item.get("source_id")
        if not key and isinstance(update_site_id, str) and subject.get("type") and subject.get("id"):
            key = update_site_stable_key(str(subject.get("type")), str(subject.get("id")), update_site_id)
        if key:
            result[key] = item
    return result


def derived_update_site_record(
    workplace_root: Path,
    subject_type: str,
    subject_id: str,
    subject_scope: str,
    installed_version: str,
    manifest_path: Path,
    site: dict[str, Any],
    overrides: dict[str, dict[str, Any]],
    *,
    parent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_id = str(site.get("id"))
    site_id = update_site_stable_key(subject_type, subject_id, source_id)
    source = {key: site[key] for key in UPDATE_SOURCE_PUBLIC_KEYS if key in site}
    source["id"] = source_id
    source["type"] = str(site.get("type"))
    enabled = bool(site.get("enabled", True))
    preserved = {key: site[key] for key in UPDATE_SOURCE_LOCAL_KEYS if key in site}
    override = overrides.get(site_id, {})
    if isinstance(override, dict):
        if "enabled" in override:
            enabled = bool(override.get("enabled"))
        if isinstance(override.get("channels"), list):
            source["channels"] = override.get("channels")
        preserved_override = override.get("preserved_local") if isinstance(override.get("preserved_local"), dict) else {}
        for key in UPDATE_SOURCE_LOCAL_KEYS:
            if key in override:
                preserved[key] = override[key]
        preserved.update(preserved_override)

    subject: dict[str, Any] = {"type": subject_type, "id": subject_id, "scope": subject_scope}
    if installed_version:
        subject["installed_version"] = installed_version
    if parent:
        subject["parent"] = parent
    record: dict[str, Any] = {
        "site_id": site_id,
        "subject": subject,
        "source": source,
        "manifest_path": rel(manifest_path, workplace_root),
        "enabled": enabled,
    }
    if preserved:
        record["preserved_local"] = preserved
    return record


def build_installed_update_sites(workplace_root: Path) -> tuple[dict[str, Any], list[Check]]:
    checks: list[Check] = []
    overrides = update_site_overrides(workplace_root)
    sites: list[dict[str, Any]] = []
    for record in update_entity_manifest_records(workplace_root):
        data = record["data"]
        update_sites = data.get("update_sites")
        if isinstance(update_sites, list):
            seen: set[str] = set()
            for index, site in enumerate(update_sites):
                label = f"{rel(record['manifest_path'], workplace_root)}.update_sites[{index}]"
                append_update_source_checks(checks, site, label, provider_key="type")
                if isinstance(site, dict) and isinstance(site.get("id"), str):
                    if site["id"] in seen:
                        checks.append(check("FAIL", f"{label} duplicate update site id {site['id']}"))
                    seen.add(site["id"])
                    sites.append(
                        derived_update_site_record(
                            workplace_root,
                            record["type"],
                            record["id"],
                            record["scope"],
                            record["version"],
                            record["manifest_path"],
                            site,
                            overrides,
                        )
                    )
        elif update_sites is not None:
            checks.append(check("FAIL", f"{rel(record['manifest_path'], workplace_root)} update_sites must be a list"))

        if record["type"] == "knowledge_package":
            resources = data.get("resources") if isinstance(data.get("resources"), list) else []
            for resource in resources:
                if not isinstance(resource, dict) or not resource.get("id"):
                    continue
                update_policy = resource.get("update_policy") if isinstance(resource.get("update_policy"), dict) else {}
                resource_sites = resource.get("update_sites") or update_policy.get("update_sites")
                if resource_sites is None:
                    continue
                resource_subject_id = f"{record['id']}/{resource.get('id')}"
                if not isinstance(resource_sites, list):
                    checks.append(check("FAIL", f"{rel(record['manifest_path'], workplace_root)} resource {resource.get('id')} update_sites must be a list"))
                    continue
                for index, site in enumerate(resource_sites):
                    label = f"{rel(record['manifest_path'], workplace_root)}.resources[{resource.get('id')}].update_sites[{index}]"
                    append_update_source_checks(checks, site, label, provider_key="type")
                    if isinstance(site, dict) and isinstance(site.get("id"), str):
                        sites.append(
                            derived_update_site_record(
                                workplace_root,
                                "knowledge_resource",
                                resource_subject_id,
                                record["scope"],
                                str(resource.get("version") or record["version"]),
                                record["manifest_path"],
                                site,
                                overrides,
                                parent={"type": "knowledge_package", "id": record["id"]},
                            )
                        )

    sites.sort(key=lambda item: (item["subject"]["type"], item["subject"]["id"], int(item["source"].get("priority", 1000)), item["site_id"]))
    derived = {"schema_version": 1, "generated_at": now_utc(), "sites": sites}
    return derived, checks


def print_derived_update_sites(data: dict[str, Any], *, subject_type: str = "all", json_output: bool = False) -> int:
    sites = data.get("sites") if isinstance(data.get("sites"), list) else []
    if subject_type != "all":
        sites = [site for site in sites if isinstance(site, dict) and site.get("subject", {}).get("type") == subject_type]
    if json_output:
        print(json.dumps({"schema_version": 1, "sites": sites}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("SITE_ID\tENABLED\tSUBJECT_TYPE\tSUBJECT_ID\tSOURCE_TYPE\tLOCATION\tMANIFEST")
    for site in sites:
        if not isinstance(site, dict):
            continue
        subject = site.get("subject") if isinstance(site.get("subject"), dict) else {}
        source = site.get("source") if isinstance(site.get("source"), dict) else {}
        print(
            "\t".join(
                [
                    str(site.get("site_id", "")),
                    str(bool(site.get("enabled", False))).lower(),
                    str(subject.get("type", "")),
                    str(subject.get("id", "")),
                    str(source.get("type", "")),
                    update_location(source, "type"),
                    str(site.get("manifest_path", "")),
                ]
            )
        )
    return 0


def command_update_entity_sources_rebuild(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    derived, checks = build_installed_update_sites(workplace_root)
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        print_checks(checks)
        return 1
    target = derived_installed_update_sites_path(workplace_root)
    if args.dry_run:
        print(json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"SITES: {len(derived['sites'])}")
    print(f"TARGET: {rel(target, workplace_root)}")
    return 0


def command_update_entity_sources_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    target = derived_installed_update_sites_path(workplace_root)
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: derived registry is invalid JSON: {target}: {exc}")
            return 1
    else:
        data, checks = build_installed_update_sites(workplace_root)
        failures = [item for item in checks if item.level == "FAIL"]
        if failures:
            print_checks(checks)
            return 1
        if not args.json:
            print(f"WARN: {rel(target, workplace_root)} missing; listing live manifest scan")
    return print_derived_update_sites(data, subject_type=args.subject_type, json_output=args.json)


def validate_normalized_update_manifest_data(data: dict[str, Any], path: Path) -> list[Check]:
    checks: list[Check] = []
    if data.get("schema_version") != 1:
        checks.append(check("FAIL", f"{path} schema_version must be 1"))
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    if not product.get("id"):
        checks.append(check("FAIL", f"{path} product.id missing"))
    subjects = data.get("subjects")
    if not isinstance(subjects, list):
        checks.append(check("FAIL", f"{path} subjects must be a list"))
        return checks
    for subject_index, subject in enumerate(subjects):
        if not isinstance(subject, dict):
            checks.append(check("FAIL", f"subjects[{subject_index}] must be an object"))
            continue
        for key in ("type", "id"):
            if not isinstance(subject.get(key), str) or not str(subject.get(key)).strip():
                checks.append(check("FAIL", f"subjects[{subject_index}].{key} missing"))
        versions = subject.get("versions")
        if not isinstance(versions, list):
            checks.append(check("FAIL", f"subjects[{subject_index}].versions must be a list"))
            continue
        for version_index, version in enumerate(versions):
            if not isinstance(version, dict):
                checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}] must be an object"))
                continue
            artifacts = version.get("artifacts")
            if not isinstance(artifacts, list):
                checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts must be a list"))
                continue
            for artifact_index, artifact in enumerate(artifacts):
                if not isinstance(artifact, dict):
                    checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}] must be an object"))
                    continue
                if not artifact.get("url"):
                    checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].url missing"))
                if not artifact.get("sha256"):
                    checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].sha256 missing"))
    if not checks:
        checks.append(check("PASS", f"{path} valid normalized update manifest"))
    return checks


def command_update_manifest_validate(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        print(f"FAIL: manifest file not found: {path}")
        return 1
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: invalid JSON: {path}: {exc}")
            return 1
    else:
        data = load_update_yaml(path)
    if not isinstance(data, dict) or not data:
        print(f"FAIL: normalized update manifest is empty or invalid: {path}")
        return 1
    return print_checks(validate_normalized_update_manifest_data(data, path))


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
    current = str(args.current_version or product.get("current_version") or "1.0.0")
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
    current = str(args.current_version or process_forge_data.get("version") or "1.0.0")
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


def command_path_resolve(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    resolution = workplace_path_resolution(workplace_root, args.path)
    for key in ["original", "expanded", "resolved", "is_absolute", "is_private", "path_status"]:
        print(f"{key}: {resolution.get(key)}")
    if resolution.get("constants"):
        print("constants: " + ", ".join(resolution["constants"]))
    if resolution.get("errors"):
        print("errors: " + ", ".join(resolution["errors"]))
        return 1
    return 0


def write_resource_proposal(workplace_root: Path, command: str, object_id: str, payload: dict[str, Any]) -> tuple[str, Path]:
    slug = resource_management_slug(command, object_id)
    proposal = {
        "schema_version": 1,
        "proposal_id": slug,
        "command": command,
        "created_at": now_utc(),
        "mode": "proposal_first",
        "payload": payload,
        "privacy": {
            "public_project_files_must_not_contain_absolute_paths": True,
            "secret_values_stored": False,
        },
    }
    path = write_resource_management_artifact(workplace_root, "proposals", slug, dump_yaml(proposal))
    return slug, path


def emit_package_root_resolution_event(workplace_root: Path, command: str, package_id: str, package_root: PackageRootResolution) -> None:
    has_unavailable = any("path does not exist" in warning or "cannot" in warning for warning in package_root.warnings)
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command=command,
            event_type="package.root.unavailable" if has_unavailable else "package.root.resolved",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status="warn" if has_unavailable or package_root.fallback else "resolved",
            message="; ".join(package_root.warnings) if package_root.warnings else "package root resolved",
        ),
    )


def command_knowledge_add_url(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    package_root = resolve_package_root(workplace_root, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-add-url", package_id, package_root)
    resource_id = safe_id(args.id or resource_id_from_url(args.url, "article"), "resource")
    resource = normalize_resource_record(
        {
            "id": resource_id,
            "kind": args.kind,
            "title": args.title or resource_id.replace("-", " ").title(),
            "description": args.description or f"External {args.kind} resource registered from URL.",
            "source": {"type": "url", "url": args.url},
            "license": {"name": args.license or "unknown"},
            "load_policy": args.load_policy,
            "index_policy": args.index_policy,
        },
        package_id,
        workplace_root,
    )
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-add-url",
        resource_id,
        {
            "package_id": package_id,
            "package_root": package_root.root_id,
            "package_root_warnings": package_root.warnings,
            "resource": resource,
            "apply_writes": ["package.yaml", "indexes/resource-index.yaml"],
        },
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.resource.add.requested",
            target={"package_id": package_id, "resource_id": resource_id},
            status="dry_run" if args.dry_run else "requested",
            message="resource add proposal created",
        ),
    )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    _manifest_path, manifest, package_root = load_workplace_package_manifest(workplace_root, package_id, package_root_id, mode="write")
    package_existed = _manifest_path.is_file()
    result = upsert_resource(manifest["resources"], resource)
    manifest_path, index_path, package_root = write_package_manifest_and_index(workplace_root, package_id, manifest, package_root_id)
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.resource.added",
            target={"package_id": package_id, "resource_id": resource_id},
            status=result,
            message="resource manifest and index updated",
        ),
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="package.updated" if package_existed else "package.created",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status=result,
            message="package manifest updated through package root" if package_existed else "package manifest created through package root",
        ),
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.package.updated",
            target={"package_id": package_id, "resource_id": resource_id, "package_root": package_root.root_id},
            status="updated",
            message="package resource index refreshed",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge URL Add Report",
        [
            f"- package: {package_id}",
            f"- package_root: {package_root.root_id}",
            f"- resource: {resource_id}",
            f"- manifest: {rel(manifest_path, workplace_root)}",
            f"- index: {rel(index_path, workplace_root)}",
            "- heavy content loaded: no",
        ],
    )
    print(f"{result.upper()}: {resource_id}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"MANIFEST: {rel(manifest_path, workplace_root)}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def command_knowledge_add_resource(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    package_root = resolve_package_root(workplace_root, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-add-resource", package_id, package_root)
    data = load_yaml_document(Path(args.resource_file).expanduser().resolve())
    if not data or yaml_error(data):
        raise SystemExit(f"FAIL: resource file is missing or invalid: {args.resource_file}")
    resource = normalize_resource_record(data, package_id, workplace_root, register_private_path=args.apply)
    resource_id = str(resource["id"])
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-add-resource",
        resource_id,
        {
            "package_id": package_id,
            "package_root": package_root.root_id,
            "package_root_warnings": package_root.warnings,
            "resource": resource,
            "private_input_path": data.get("path"),
            "suggested_registration": "register a knowledge_root/template_root/package_root when the path should be reused" if data.get("path") else None,
            "apply_writes": ["package.yaml", "indexes/resource-index.yaml"],
        },
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="knowledge.resource.add.requested",
            target={"package_id": package_id, "resource_id": resource_id},
            status="dry_run" if args.dry_run else "requested",
            message="resource add proposal created",
        ),
    )
    if data.get("path"):
        path_errors = resource.get("path_resolution", {}).get("errors") if isinstance(resource.get("path_resolution"), dict) else []
        append_workplace_resource_event(
            workplace_root,
            resource_management_event(
                scope="workplace",
                command="knowledge-add-resource",
                event_type="knowledge.resource.path.unresolved" if path_errors else "knowledge.resource.path.resolved",
                target={"package_id": package_id, "resource_id": resource_id},
                status="error" if path_errors else "resolved",
                message=", ".join(path_errors) if path_errors else "resource path resolved to public path_ref",
            ),
        )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    _manifest_path, manifest, package_root = load_workplace_package_manifest(workplace_root, package_id, package_root_id, mode="write")
    package_existed = _manifest_path.is_file()
    result = upsert_resource(manifest["resources"], resource)
    manifest_path, index_path, package_root = write_package_manifest_and_index(workplace_root, package_id, manifest, package_root_id)
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="package.updated" if package_existed else "package.created",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status=result,
            message="package manifest updated through package root" if package_existed else "package manifest created through package root",
        ),
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="knowledge.resource.added",
            target={"package_id": package_id, "resource_id": resource_id, "package_root": package_root.root_id},
            status=result,
            message="resource manifest and index updated",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge Resource Add Report",
        [
            f"- package: {package_id}",
            f"- package_root: {package_root.root_id}",
            f"- resource: {resource_id}",
            f"- manifest: {rel(manifest_path, workplace_root)}",
            f"- index: {rel(index_path, workplace_root)}",
            f"- path_ref: {resource.get('path_ref')}",
        ],
    )
    print(f"{result.upper()}: {resource_id}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def command_knowledge_index_refresh(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    manifest_path, manifest, package_root = load_workplace_package_manifest(workplace_root, package_id, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-index-refresh", package_id, package_root)
    index_path = resource_index_path_for_package(manifest_path, workplace_root, package_id)
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-index-refresh",
        package_id,
        {"package_id": package_id, "package_root": package_root.root_id, "package_root_warnings": package_root.warnings, "index_path": rel(index_path, workplace_root), "resource_count": len(manifest.get("resources", []))},
    )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(ensure_trailing_newline(dump_yaml(build_resource_index(manifest, workplace_root, package_root.root_id))), encoding="utf-8")
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="knowledge-index-refresh",
            event_type="package.index.updated",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status="updated",
            message="resource index refreshed",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge Index Refresh Report",
        [f"- package: {package_id}", f"- package_root: {package_root.root_id}", f"- index: {rel(index_path, workplace_root)}", "- heavy content loaded: no"],
    )
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def command_knowledge_package_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    checks = knowledge_package_doctor_checks(workplace_root, package_id, getattr(args, "package_root", None))
    for item in checks:
        if "duplicate package id" in item.message:
            append_workplace_resource_event(
                workplace_root,
                resource_management_event(
                    scope="workplace",
                    command="knowledge-package-doctor",
                    event_type="package.duplicate.detected",
                    target={"package_id": package_id},
                    status="warn",
                    message=item.message,
                ),
            )
    if any(item.level == "FAIL" for item in checks):
        append_workplace_resource_event(
            workplace_root,
            resource_management_event(
                scope="workplace",
                command="knowledge-package-doctor",
                event_type="package.doctor.failed",
                target={"package_id": package_id},
                status="failed",
                message="; ".join(item.message for item in checks if item.level == "FAIL"),
            ),
        )
    return print_checks(checks)


def command_knowledge_package_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.id)
    package_root = resolve_package_root(workplace_root, args.package_root, mode="write" if args.apply else "read")
    package_dir = package_root.resolved_path / package_id
    manifest_path = package_dir / "package.yaml"
    slug, proposal_path = write_resource_proposal(workplace_root, "knowledge-package-create", package_id, {"package_id": package_id, "package_root": package_root.root_id, "target": rel(manifest_path, workplace_root)})
    emit_package_root_resolution_event(workplace_root, "knowledge-package-create", package_id, package_root)
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.authoring.started", target={"package_id": package_id, "package_root": package_root.root_id}, status="dry_run" if args.dry_run else "started", message="knowledge package authoring started"))
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if manifest_path.exists() and not args.force:
        raise SystemExit(f"FAIL: knowledge package already exists: {rel(manifest_path, workplace_root)}")
    for dirname in ["resources", "indexes", "prompts", "summaries", "tests", "artifacts", "reviews", "handoffs"]:
        (package_dir / dirname).mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 1,
        "id": package_id,
        "name": args.title,
        "title": args.title,
        "kind": args.kind,
        "scope": "workplace",
        "version": "1.0.0",
        "status": "draft",
        "description": args.description or f"Workplace knowledge package {args.title}.",
        "visibility": "workplace",
        "load_policy": "on_demand",
        "resources": [],
        "indexes": {"resource_index": "indexes/resource-index.yaml"},
        "tags": [args.kind, "knowledge"],
    }
    write_authoring_text(manifest_path, dump_yaml(package))
    write_authoring_text(package_dir / "README.md", f"# {args.title}\n\nKnowledge package `{package_id}`.")
    write_authoring_text(package_dir / "indexes" / "resource-index.yaml", dump_yaml({"schema_version": 1, "package": package_id, "resources": []}))
    write_authoring_text(package_dir / "artifacts" / "knowledge-package-authoring-report.md", f"# Knowledge Package Authoring Report\n\n- package: {package_id}\n- package_root: {package_root.root_id}")
    write_authoring_text(package_dir / "reviews" / "knowledge-package-authoring-review.md", "# Knowledge Package Authoring Review\n\nResult: pass_with_conditions")
    write_authoring_text(package_dir / "handoffs" / "knowledge-package-ready-handoff.md", f"# Handoff: knowledge-package-create -> knowledge consumers\n\nPackage `{package_id}` is ready for resource additions.")
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.created", target={"package_id": package_id, "package_root": package_root.root_id}, status="created", message="knowledge package created"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.resource_index.created", target={"package_id": package_id}, status="created", message="resource index created"))
    doctor_status, doctor_output = run_command_capture(command_knowledge_package_doctor, argparse.Namespace(workplace=str(workplace_root), package=package_id, package_root=package_root.root_id))
    print(doctor_output, end="")
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.doctor.passed" if doctor_status == 0 else "knowledge_package.doctor.failed", target={"package_id": package_id}, status="passed" if doctor_status == 0 else "failed", message="knowledge package doctor completed"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.authoring.completed", target={"package_id": package_id}, status="completed", message="knowledge package authoring completed"))
    print(f"PACKAGE: {rel(manifest_path, workplace_root)}")
    return doctor_status


def normalize_platform_id(raw: str) -> tuple[str, str]:
    platform_id = safe_id(raw.removeprefix("platform."), "platform")
    return platform_id, platform_contract_id(platform_id)


def command_platform_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    platform_id, contract_id = normalize_platform_id(args.id)
    for entry in policy_entries(load_policy_document("platform-id-policy.yaml"), "discouraged_platform_ids"):
        if policy_id_matches(contract_id, entry):
            print(str(entry.get("user_message", entry.get("message", "WARN: platform id is discouraged by policy."))), file=sys.stderr)
    root_id, platform_root = resolve_platform_root(workplace_root, getattr(args, "platform_root", None), mode="write" if args.apply else "read")
    target = platform_root / contract_id
    contract_path = target / "platform-contract.yaml"
    knowledge_packages = [item for item in getattr(args, "knowledge_package", []) if item]
    templates = [item for item in getattr(args, "template", []) if item]
    project_types = [item for item in getattr(args, "project_type", []) if item] or [platform_id]
    slug, proposal_path = write_resource_proposal(workplace_root, "platform-create", contract_id, {"platform": contract_id, "platform_root": root_id, "target": rel(contract_path, workplace_root)})
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-create", event_type="platform.authoring.started", target={"platform": contract_id}, status="dry_run" if args.dry_run else "started", message="platform authoring started"))
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if contract_path.exists() and not args.force:
        raise SystemExit(f"FAIL: platform contract already exists: {rel(contract_path, workplace_root)}")
    for dirname in ["tests", "artifacts", "reviews", "handoffs"]:
        (target / dirname).mkdir(parents=True, exist_ok=True)
    contract = {
        "schema_version": 1,
        "id": contract_id,
        "title": args.title,
        "type": "platform_contract",
        "version": "1.0.0",
        "status": "draft",
        "project_type_hints": project_types,
        "applies_to": {"platforms": [platform_id], "project_type_hints": project_types},
        "requires": {"capabilities": ["filesystem.read", "filesystem.write"], "knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "includes": {
            "knowledge_packages": knowledge_packages,
            "templates": templates,
            "tools": [item for item in getattr(args, "tool", []) if item],
            "mcp": [item for item in getattr(args, "mcp", []) if item],
            "processes": [item for item in getattr(args, "process", []) if item] or ["software-feature-development"],
        },
        "policies": {"missing_required_capability": "block", "missing_optional_resource": "warn"},
    }
    write_authoring_text(contract_path, dump_yaml(contract))
    write_authoring_text(target / "README.md", f"# {args.title}\n\nPlatform contract `{contract_id}`.")
    write_authoring_text(target / "project-types.yaml", dump_yaml({"schema_version": 1, "project_type_hints": project_types}))
    write_authoring_text(target / "capabilities.yaml", dump_yaml({"schema_version": 1, "capabilities": contract["requires"]["capabilities"]}))
    write_authoring_text(target / "knowledge.yaml", dump_yaml({"schema_version": 1, "knowledge_packages": knowledge_packages}))
    write_authoring_text(target / "templates.yaml", dump_yaml({"schema_version": 1, "templates": templates}))
    write_authoring_text(target / "tools.yaml", dump_yaml({"schema_version": 1, "tools": contract["includes"]["tools"]}))
    write_authoring_text(target / "mcp.yaml", dump_yaml({"schema_version": 1, "mcp": contract["includes"]["mcp"]}))
    write_authoring_text(target / "processes.yaml", dump_yaml({"schema_version": 1, "processes": contract["includes"]["processes"]}))
    write_authoring_text(target / "artifacts" / "platform-contract-authoring-report.md", f"# Platform Contract Authoring Report\n\n- platform: {contract_id}\n- platform_root: {root_id}")
    write_authoring_text(target / "reviews" / "platform-contract-authoring-review.md", "# Platform Contract Authoring Review\n\nResult: pass_with_conditions")
    write_authoring_text(target / "handoffs" / "platform-contract-ready-handoff.md", f"# Handoff: platform-create -> project-onboarding\n\nPlatform `{contract_id}` is ready for project type matching.")
    upsert_registry_entry(workplace_root / "registries" / "platforms.yaml", "platforms", {"id": platform_id, "package_id": contract_id, "path": rel(contract_path, workplace_root), "status": "available"})
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-create", event_type="platform.contract.created", target={"platform": contract_id}, status="created", message="platform contract created"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-create", event_type="platform.contract.linked", target={"platform": contract_id}, status="linked", message="platform registry updated"))
    doctor_status, doctor_output = run_command_capture(command_platform_contract_doctor, argparse.Namespace(workplace=str(workplace_root), platform=contract_id))
    print(doctor_output, end="")
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-create", event_type="platform.contract.doctor.passed" if doctor_status == 0 else "platform.contract.doctor.failed", target={"platform": contract_id}, status="passed" if doctor_status == 0 else "failed", message="platform doctor completed"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-create", event_type="platform.authoring.completed", target={"platform": contract_id}, status="completed", message="platform authoring completed"))
    print(f"PLATFORM: {rel(contract_path, workplace_root)}")
    return doctor_status


def platform_contract_path(workplace_root: Path, platform: str) -> Path | None:
    platform_id, contract_id = normalize_platform_id(platform)
    for candidate_id in [contract_id, platform_id]:
        entry = platform_contract_registry_entry(workplace_root / "workplace.yaml", candidate_id)
        if entry and entry.get("path"):
            path = workplace_root / str(entry["path"])
            if path.is_file():
                return path
    _root_id, root_path = resolve_platform_root(workplace_root, None, mode="read")
    for candidate in [root_path / contract_id / "platform-contract.yaml", root_path / platform_id / "platform-contract.yaml", workplace_root / "platforms" / platform_id / "platform.yaml"]:
        if candidate.is_file():
            return candidate
    return None


def command_platform_contract_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    platform = str(args.platform)
    checks: list[Check] = []
    contract_path = platform_contract_path(workplace_root, platform)
    checks.append(
        check("PASS", "platform contract found")
        if contract_path
        else check_with_hint(
            "FAIL",
            "platform contract found",
            "The requested platform is not registered or its platform contract path is missing.",
            f"python bin/pf.py platform-create --workplace <workplace-root> --id {platform} --title \"{platform}\" --apply",
        )
    )
    if contract_path:
        text = contract_path.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "platform contract has no local absolute paths"))
        data = load_yaml_document(contract_path)
        checks.append(check("PASS" if data.get("id") else "FAIL", "platform contract id present"))
        contract_id = platform_contract_id(str(data.get("id") or platform))
        for entry in policy_entries(load_policy_document("platform-id-policy.yaml"), "discouraged_platform_ids"):
            if policy_id_matches(contract_id, entry):
                checks.append(
                    check_with_hint(
                        str(entry.get("user_created_behavior", "WARN")).upper(),
                        str(entry.get("message", f"platform id discouraged: {contract_id}")),
                        str(entry.get("why", "The platform id matched a data-driven platform id policy.")),
                        str(entry.get("fix", "update the platform id or policy manifest")),
                    )
                )
        hints = data.get("project_type_hints")
        if not isinstance(hints, list):
            applies_to = data.get("applies_to") if isinstance(data.get("applies_to"), dict) else {}
            hints = applies_to.get("project_type_hints") if isinstance(applies_to.get("project_type_hints"), list) else []
        checks.append(check("PASS" if isinstance(hints, list) and hints else "WARN", "project_type_hints configured"))
        requires = data.get("requires") if isinstance(data.get("requires"), dict) else {}
        checks.append(check("PASS" if requires.get("capabilities") else "WARN", "required capabilities listed"))
        extends_refs = contract_extends(data)
        required_platform_refs = contract_required_platforms(data)
        checks.append(check("PASS", "extends entries are valid") if all(ref.get("id") for ref in extends_refs) else check("FAIL", "extends entries are valid"))
        checks.append(check("PASS", "requires.platforms entries are valid") if all(ref.get("id") for ref in required_platform_refs) else check("FAIL", "requires.platforms entries are valid"))
        for ref in extends_refs:
            if ref.get("required") is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"extends parent is required: {ref['id']}",
                        "Platform inheritance cannot be optional in the pre-release contract model.",
                        "set required: true or move the platform reference to requires.platforms if it is only a dependency",
                    )
                )
        required_platform_by_id = {str(ref["id"]): bool(ref.get("required", True)) for ref in required_platform_refs}
        for ref in extends_refs:
            if required_platform_by_id.get(str(ref["id"])) is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"child platform cannot weaken required parent dependency: {ref['id']}",
                        "An inherited parent is required by definition; requires.platforms cannot mark the same parent optional.",
                        "set requires.platforms[].required: true for the parent platform",
                    )
                )
        platform_resolution = resolve_platform_contracts(workplace_root / "workplace.yaml", [data.get("id") or platform])
        for missing in platform_resolution["missing_required_contracts"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required platform available: {missing}",
                    "The platform contract extends or requires a platform that is not registered in the workplace.",
                    f"python bin/pf.py platform-create --workplace <workplace-root> --id {missing} --title \"{missing}\" --apply",
                )
            )
        for cycle in platform_resolution["circular_platforms"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"circular platform inheritance detected: {cycle}",
                    "Platform inheritance must resolve to an acyclic parent-first stack.",
                    "remove one extends edge from the cycle and rerun platform-contract-doctor",
                )
            )
        checks.append(check("PASS" if platform_resolution["platform_stack"] else "FAIL", "resolved platform stack valid"))
        stack_report = contract_path.parent / "artifacts" / "platform-stack.snapshot.yaml"
        stack_report.parent.mkdir(parents=True, exist_ok=True)
        stack_report.write_text(
            ensure_trailing_newline(
                dump_yaml(
                    {
                        "schema_version": 1,
                        "platform": data.get("id") or platform,
                        "resolved_at": now_utc(),
                        "platform_stack": platform_resolution["platform_stack"],
                        "required_knowledge_packages": platform_resolution["required_knowledge_packages"],
                        "recommended_knowledge_packages": platform_resolution["recommended_knowledge_packages"],
                    }
                )
            ),
            encoding="utf-8",
        )
        checks.append(check("PASS", f"resolved platform stack written: {rel(stack_report, workplace_root)}"))
        inherited_required, inherited_recommended = platform_resource_findings(workplace_root / "workplace.yaml", platform_resolution)
        for item in inherited_required:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack marks this resource as required.",
                    "register the missing resource in the workplace registry or package roots before using this platform",
                )
            )
        for item in inherited_recommended:
            checks.append(
                check_with_hint(
                    "WARN",
                    f"optional {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack recommends this resource, but onboarding can continue.",
                    "register the resource if this platform should provide the optional capability",
                )
            )
        for package_id in list_value(requires.get("knowledge_packages")):
            manifest = package_manifest_index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"required knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "FAIL",
                    f"required knowledge package available: {package_id}",
                    "This platform contract marks the package as required.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                    "mark it as required: false or move it to includes.knowledge_packages if optional",
                )
            )
        for package_id in contract_includes(data, "knowledge_packages"):
            manifest = package_manifest_index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"optional knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "WARN",
                    f"optional knowledge package available: {package_id}",
                    "This platform contract recommends the package, but onboarding can continue without it.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                )
            )
        for template_id in list_value(requires.get("templates")):
            checks.append(
                check("PASS", f"required template available: {template_id}")
                if template_manifest_path(workplace_root, template_id)
                else check_with_hint(
                    "FAIL",
                    f"required template available: {template_id}",
                    "This platform contract marks the template as required.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                    "move it to includes.templates if optional",
                )
            )
        for template_id in contract_includes(data, "templates"):
            checks.append(
                check("PASS", f"optional template available: {template_id}")
                if template_manifest_path(workplace_root, template_id)
                else check_with_hint(
                    "WARN",
                    f"optional template available: {template_id}",
                    "This platform contract recommends the template, but onboarding can continue without it.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                )
            )
        for forbidden in ["package.yaml", "template.yaml"]:
            copied = [path for path in contract_path.parent.rglob(forbidden) if path != contract_path]
            checks.append(check("PASS" if not copied else "FAIL", f"no copied {forbidden} inside platform contract"))
    failed = any(item.level == "FAIL" for item in checks)
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="platform-contract-doctor", event_type="platform.contract.doctor.failed" if failed else "platform.contract.doctor.passed", target={"platform": platform}, status="failed" if failed else "passed", message="platform contract doctor completed"))
    return print_checks(checks)


def command_docs_import_plan(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    source = safe_id(args.source, "source")
    topics = [safe_id(item.strip(), "topic") for item in str(args.topics).split(",") if item.strip()]
    plan_id = safe_id(args.id or f"{source}-{'-'.join(topics)}", "documentation-import")
    resources = [
        {
            "id": f"{source}-{topic}-docs",
            "kind": "documentation",
            "title": f"{source.upper()} {topic.upper()} documentation mirror",
            "path_ref": {"registry": "external_resources", "id": f"{source}-{topic}-docs"},
            "load_policy": "on_demand",
            "index_policy": "full_text",
            "source": {"type": "documentation_source", "id": source, "topic": topic},
            "license": {"name": args.license or "source-specific"},
            "update_policy": {"mode": "manual_plan_first"},
        }
        for topic in topics
    ]
    plan = {
        "schema_version": 1,
        "id": plan_id,
        "source": source,
        "topics": topics,
        "created_at": now_utc(),
        "mode": "plan_only",
        "download": {"enabled": False, "reason": "MVP does not crawl or download large documentation sets"},
        "resources": resources,
        "index_policy": "write_resource_index_without_loading_full_content",
    }
    target = resource_management_root(workplace_root) / "documentation-import-plans" / f"{plan_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(dump_yaml(plan)), encoding="utf-8")
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="docs-import-plan",
            event_type="knowledge.resource.add.requested",
            target={"package_id": args.package or "documentation", "resource_id": plan_id},
            status="planned",
            message="documentation import plan created without downloading content",
        ),
    )
    print(f"PLAN: {rel(target, workplace_root)}")
    return 0


def command_template_add(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = safe_id(args.id, "template")
    source = Path(args.source).expanduser().resolve()
    target_root = path_resolution_to_path(workplace_path_resolution(workplace_root, f"${{PF_TEMPLATES}}/{args.type}/{template_id}"))
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "template-add",
        template_id,
        {"template_id": template_id, "source": str(source), "target": rel(target_root, workplace_root)},
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="template-add",
            event_type="template.add.requested",
            target={"template_id": template_id},
            status="dry_run" if args.dry_run else "requested",
            message="template add proposal created",
        ),
    )
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if not source.is_dir():
        raise SystemExit(f"FAIL: template source folder not found: {source}")
    target_root.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        if item.is_file():
            relative = item.relative_to(source)
            destination = target_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
    readme = target_root / "README.md"
    if not readme.is_file():
        readme.write_text(
            ensure_trailing_newline(
                f"# {template_id}\n\nUse this {args.type} template when the current package or platform contract selects it.\n\n## Placeholders\n\nDocument placeholders before production use.\n\n## Verification\n\nReview generated files before applying them to a project."
            ),
            encoding="utf-8",
        )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="template-add",
            event_type="template.added",
            target={"template_id": template_id},
            status="added",
            message="template payload copied",
        ),
    )
    print(f"TEMPLATE: {rel(target_root, workplace_root)}")
    return 0


def resolve_template_root(workplace_root: Path, template_root_id: str | None = None, *, mode: str = "read") -> tuple[str, Path]:
    registry_path = workplace_root / "registries" / "templates.yaml"
    data = load_yaml_document(registry_path)
    roots = data.get("template_roots") if isinstance(data, dict) else None
    entries = [entry for entry in roots if isinstance(entry, dict)] if isinstance(roots, list) else []
    if not entries:
        entries = [{"id": "global", "label": "Global reusable templates", "path": "${PF_TEMPLATES}", "scope": "workplace", "status": "available"}]
        if mode == "write":
            upsert_registry_entry(registry_path, "template_roots", entries[0])
    selected = None
    if template_root_id:
        for entry in entries:
            if str(entry.get("id")) == template_root_id:
                selected = entry
                break
        if selected is None:
            raise SystemExit(f"FAIL: template root '{template_root_id}' not found in registries/templates.yaml")
    else:
        available = [entry for entry in entries if str(entry.get("status", "available")) == "available"]
        selected = available[0] if available else entries[0]
    root_id = str(selected.get("id", "global"))
    root_path = path_resolution_to_path(workplace_path_resolution(workplace_root, str(selected.get("path") or "${PF_TEMPLATES}")))
    if mode == "write":
        root_path.mkdir(parents=True, exist_ok=True)
    return root_id, root_path


def resolve_platform_root(workplace_root: Path, platform_root_id: str | None = None, *, mode: str = "read") -> tuple[str, Path]:
    registry_path = workplace_root / "registries" / "platform-contract-roots.yaml"
    data = load_yaml_document(registry_path)
    roots = data.get("platform_contract_roots") if isinstance(data, dict) else None
    entries = [entry for entry in roots if isinstance(entry, dict)] if isinstance(roots, list) else []
    if not entries:
        entries = [{"id": "global", "label": "Global platform contracts", "path": "${PF_PLATFORM_CONTRACTS}", "scope": "workplace", "status": "available"}]
        if mode == "write":
            upsert_registry_entry(registry_path, "platform_contract_roots", entries[0])
    selected = None
    if platform_root_id:
        for entry in entries:
            if str(entry.get("id")) == platform_root_id:
                selected = entry
                break
        if selected is None:
            raise SystemExit(f"FAIL: platform root '{platform_root_id}' not found in registries/platform-contract-roots.yaml")
    else:
        available = [entry for entry in entries if str(entry.get("status", "available")) == "available"]
        selected = available[0] if available else entries[0]
    root_id = str(selected.get("id", "global"))
    root_path = path_resolution_to_path(workplace_path_resolution(workplace_root, str(selected.get("path") or "${PF_PLATFORM_CONTRACTS}")))
    if mode == "write":
        root_path.mkdir(parents=True, exist_ok=True)
    return root_id, root_path


def write_authoring_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def command_template_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = str(args.id)
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*", template_id):
        raise SystemExit("FAIL: template id must be lowercase and may use dots or dashes")
    root_id, template_root = resolve_template_root(workplace_root, getattr(args, "template_root", None), mode="write" if args.apply else "read")
    target = template_root / template_id
    slug, proposal_path = write_resource_proposal(workplace_root, "template-create", template_id, {"template_id": template_id, "template_root": root_id, "target": rel(target, workplace_root)})
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-create", event_type="template.authoring.started", target={"template_id": template_id}, status="dry_run" if args.dry_run else "started", message="template authoring started"))
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if target.exists() and not args.force:
        raise SystemExit(f"FAIL: template already exists: {rel(target, workplace_root)}")
    for dirname in ["files", "prompts", "examples", "tests", "artifacts", "reviews", "handoffs"]:
        (target / dirname).mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "id": template_id,
        "title": args.title,
        "kind": args.kind,
        "version": "1.0.0",
        "description": args.description or f"Reusable template {args.title}.",
        "inputs": [{"id": "project_name", "required": True}, {"id": "template_scope", "required": False}],
        "outputs": [{"path": f"{safe_id(template_id, 'template')}.md"}],
        "files": [{"source": f"files/{safe_id(template_id, 'template')}.md", "target": "{{ output_path }}"}],
        "prompts": [{"path": "prompts/authoring-notes.md"}],
        "tags": [args.kind, "processforge-template"],
    }
    write_authoring_text(target / "template.yaml", dump_yaml(manifest))
    write_authoring_text(target / "README.md", f"# {args.title}\n\nReusable template `{template_id}`.")
    write_authoring_text(target / "files" / f"{safe_id(template_id, 'template')}.md", f"# {{{{ project_name }}}}\n\nTemplate scope: {{{{ template_scope }}}}")
    write_authoring_text(target / "prompts" / "authoring-notes.md", f"# Authoring Notes\n\nUse template `{template_id}` through ProcessForge template selection.")
    write_authoring_text(target / "artifacts" / "template-authoring-report.md", f"# Template Authoring Report\n\n- template: {template_id}\n- template_root: {root_id}")
    write_authoring_text(target / "reviews" / "template-authoring-review.md", "# Template Authoring Review\n\nResult: pass_with_conditions")
    write_authoring_text(target / "handoffs" / "template-ready-handoff.md", f"# Handoff: template-create -> template consumers\n\nTemplate `{template_id}` is ready for review.")
    upsert_registry_entry(workplace_root / "registries" / "templates.yaml", "templates", {"id": template_id, "title": args.title, "path": rel(target / "template.yaml", workplace_root), "template_root": root_id, "kind": args.kind, "status": "available"})
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-create", event_type="template.created", target={"template_id": template_id}, status="created", message="template structure created"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-create", event_type="template.registered", target={"template_id": template_id}, status="registered", message="template registry updated"))
    doctor_status, doctor_output = run_command_capture(command_template_doctor, argparse.Namespace(workplace=str(workplace_root), template=template_id))
    print(doctor_output, end="")
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-create", event_type="template.doctor.passed" if doctor_status == 0 else "template.doctor.failed", target={"template_id": template_id}, status="passed" if doctor_status == 0 else "failed", message="template doctor completed"))
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-create", event_type="template.authoring.completed", target={"template_id": template_id}, status="completed", message="template authoring completed"))
    print(f"TEMPLATE: {rel(target, workplace_root)}")
    return doctor_status


def template_manifest_path(workplace_root: Path, template_id: str) -> Path | None:
    _root_id, root_path = resolve_template_root(workplace_root, None, mode="read")
    candidate = root_path / template_id / "template.yaml"
    if candidate.is_file():
        return candidate
    registry = load_yaml_document(workplace_root / "registries" / "templates.yaml")
    entries = registry.get("templates") if isinstance(registry, dict) else None
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("id")) == template_id and entry.get("path"):
                path = workplace_root / str(entry["path"])
                return path if path.is_file() else None
    return None


def command_template_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = str(args.template)
    checks: list[Check] = []
    manifest_path = template_manifest_path(workplace_root, template_id)
    checks.append(
        check("PASS", "template manifest found")
        if manifest_path
        else check_with_hint(
            "FAIL",
            "template manifest found",
            "The template id cannot be resolved through registries/templates.yaml or the default template root.",
            f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
        )
    )
    if manifest_path:
        text = manifest_path.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "template manifest has no local absolute paths"))
        data = load_yaml_document(manifest_path)
        checks.append(check("PASS" if data.get("id") == template_id else "FAIL", "template id matches requested id"))
        root = manifest_path.parent
        for dirname in ["files", "prompts", "examples", "artifacts", "reviews", "handoffs"]:
            checks.append(check("PASS" if (root / dirname).exists() else "WARN", f"{dirname}/ exists"))
        for item in data.get("files", []) if isinstance(data.get("files"), list) else []:
            source = item.get("source") if isinstance(item, dict) else None
            if source:
                checks.append(
                    check("PASS", f"referenced file exists: {source}")
                    if (root / str(source)).is_file()
                    else check_with_hint(
                        "FAIL",
                        f"referenced file exists: {source}",
                        "The template manifest references a payload file that is not present.",
                        f"restore {source} under the template root or remove the file entry from template.yaml",
                    )
                )
        for item in data.get("prompts", []) if isinstance(data.get("prompts"), list) else []:
            prompt_path = item.get("path") if isinstance(item, dict) else None
            if prompt_path:
                checks.append(
                    check("PASS", f"referenced prompt exists: {prompt_path}")
                    if (root / str(prompt_path)).is_file()
                    else check_with_hint(
                        "FAIL",
                        f"referenced prompt exists: {prompt_path}",
                        "The template manifest references a prompt file that is not present.",
                        f"restore {prompt_path} under the template root or remove the prompt entry from template.yaml",
                    )
                )
    failed = any(item.level == "FAIL" for item in checks)
    append_workplace_resource_event(workplace_root, resource_management_event(scope="workplace", command="template-doctor", event_type="template.doctor.failed" if failed else "template.doctor.passed", target={"template_id": template_id}, status="failed" if failed else "passed", message="template doctor completed"))
    return print_checks(checks)


def upsert_registry_entry(path: Path, collection_key: str, entry: dict[str, Any]) -> str:
    data = load_yaml_document(path)
    if not data or yaml_error(data):
        data = {"schema_version": 1, collection_key: []}
    entries = data.get(collection_key)
    if not isinstance(entries, list):
        entries = []
        data[collection_key] = entries
    result = upsert_resource(entries, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ensure_trailing_newline(dump_yaml(data)), encoding="utf-8")
    return result


def command_tool_register(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if contains_secret_value(args.command):
        raise SystemExit("FAIL: command appears to contain a secret value")
    tool_id = safe_id(args.id, "tool")
    entry = {
        "id": tool_id,
        "name": args.name or tool_id,
        "capability": args.capability,
        "command": args.command,
        "scope": "workplace",
        "healthcheck": {"command": args.healthcheck or f"{args.command} --version"},
        "status": args.status,
    }
    slug, proposal_path = write_resource_proposal(workplace_root, "tool-register", tool_id, {"tool": entry})
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    result = upsert_registry_entry(workplace_root / "registries" / "tools.yaml", "tools", entry)
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="tool-register",
            event_type="tool.registered",
            target={"tool_id": tool_id},
            status=result,
            message="tool registry updated",
        ),
    )
    report = write_resource_management_report(workplace_root, slug, "Tool Register Report", [f"- tool: {tool_id}", f"- status: {result}"])
    print(f"{result.upper()}: {tool_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def command_mcp_register(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if contains_secret_value(args.command):
        raise SystemExit("FAIL: command appears to contain a secret value")
    mcp_id = safe_id(args.id, "mcp")
    entry = {
        "id": mcp_id,
        "name": args.name or mcp_id,
        "capability": args.capability,
        "transport": args.transport,
        "command": args.command,
        "auth_ref": args.auth_ref,
        "status": args.status,
    }
    slug, proposal_path = write_resource_proposal(workplace_root, "mcp-register", mcp_id, {"mcp": entry})
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    result = upsert_registry_entry(workplace_root / "registries" / "mcp.yaml", "mcp_servers", entry)
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="mcp-register",
            event_type="mcp.registered",
            target={"mcp_id": mcp_id},
            status=result,
            message="MCP registry updated",
        ),
    )
    report = write_resource_management_report(workplace_root, slug, "MCP Register Report", [f"- mcp: {mcp_id}", f"- status: {result}"])
    print(f"{result.upper()}: {mcp_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def command_platform_contract_install(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    platform_id = safe_id(args.id.removeprefix("platform."), "platform")
    contract_id = platform_contract_id(platform_id)
    contract_path = workplace_root / "platforms" / platform_id / "platform.yaml"
    contract = {
        "schema_version": 1,
        "id": contract_id,
        "type": "platform_contract",
        "version": args.version,
        "applies_to": {"platforms": [platform_id]},
        "requires": {
            "capabilities": [item for item in args.required_capabilities.split(",") if item],
            "knowledge_packages": [item for item in args.required_packages.split(",") if item],
            "tools": [item for item in args.required_tools.split(",") if item],
            "mcp": [item for item in args.required_mcp.split(",") if item],
            "templates": [item for item in args.required_templates.split(",") if item],
        },
        "includes": {
            "knowledge_packages": [item for item in args.recommended_packages.split(",") if item],
            "tools": [item for item in args.recommended_tools.split(",") if item],
            "mcp": [item for item in args.recommended_mcp.split(",") if item],
            "templates": [item for item in args.recommended_templates.split(",") if item],
        },
        "policies": {"missing_required_capability": "block", "missing_optional_resource": "warn"},
    }
    slug, proposal_path = write_resource_proposal(workplace_root, "platform-contract-install", platform_id, {"contract": contract})
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(ensure_trailing_newline(dump_yaml(contract)), encoding="utf-8")
    upsert_registry_entry(
        workplace_root / "registries" / "platforms.yaml",
        "platforms",
        {"id": platform_id, "package_id": contract_id, "path": rel(contract_path, workplace_root), "status": "available"},
    )
    append_workplace_resource_event(
        workplace_root,
        resource_management_event(
            scope="workplace",
            command="platform-contract-install",
            event_type="platform.contract.updated",
            target={"package_id": contract_id},
            status="updated",
            message="platform contract and registry updated",
        ),
    )
    report = write_resource_management_report(workplace_root, slug, "Platform Contract Install Report", [f"- contract: {contract_id}", f"- path: {rel(contract_path, workplace_root)}"])
    print(f"CONTRACT: {rel(contract_path, workplace_root)}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProcessForge MVP init and doctor commands.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_workplace = sub.add_parser("init-workplace", help="Initialize a ProcessForge workplace layer.")
    init_workplace.add_argument("--root", required=True, help="Workplace root path.")
    init_workplace.add_argument("--answers", help="Optional workplace answers YAML.")
    init_workplace.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
    init_workplace.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    init_workplace.add_argument("--apply", action="store_true", help="Write files.")
    init_workplace.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_workplace.set_defaults(func=command_init_workplace)

    workplace_init = sub.add_parser("workplace-init", help="First-run alias for init-workplace.")
    workplace_init.add_argument("--workplace", dest="root", required=True, help="Workplace root path.")
    workplace_init.add_argument("--answers", help="Optional workplace answers YAML.")
    workplace_init.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
    workplace_init.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    workplace_init.add_argument("--apply", action="store_true", help="Write files.")
    workplace_init.add_argument("--force", action="store_true", help="Overwrite existing files.")
    workplace_init.set_defaults(func=command_init_workplace)

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
    init_project.add_argument("--type", dest="project_type", help="Project type override.")
    init_project.add_argument("--answers", help="Optional project answers YAML.")
    init_project.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
    init_project.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    init_project.add_argument("--apply", action="store_true", help="Write files.")
    init_project.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_project.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
    init_project.set_defaults(func=command_init_project)

    project_onboard = sub.add_parser("project-onboard", help="Onboard a project into an existing ProcessForge workplace.")
    project_onboard.add_argument("--project-root", required=True, help="Project root path.")
    project_onboard.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    project_onboard.add_argument("--type", dest="project_type", required=True, help="Project type, for example generic-software-project or example-component.")
    project_onboard.add_argument("--answers", help="Optional project answers YAML.")
    project_onboard.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
    project_onboard.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    project_onboard.add_argument("--apply", action="store_true", help="Write files.")
    project_onboard.add_argument("--force", action="store_true", help="Overwrite existing files.")
    project_onboard.add_argument("--allow-missing-workplace", action="store_true", help="Allow apply mode with a missing workplace manifest.")
    project_onboard.set_defaults(func=command_init_project)

    doctor_project = sub.add_parser("doctor-project", help="Validate a ProcessForge project layer.")
    doctor_project.add_argument("--project-root", required=True, help="Project root path.")
    doctor_project.set_defaults(func=command_doctor_project)

    agent_start_prompt = sub.add_parser("agent-start-prompt", help="Print and ensure the project START_AGENT_HERE prompt.")
    agent_start_prompt.add_argument("--project-root", required=True, help="Project root path.")
    agent_start_prompt.set_defaults(func=command_agent_start_prompt)

    first_run = sub.add_parser("first-run", help="Convenience command that runs workplace-init and then project-onboard.")
    first_run.add_argument("--workplace", required=True, help="Workplace root path.")
    first_run.add_argument("--project-root", required=True, help="Project root path.")
    first_run.add_argument("--type", dest="project_type", required=True, help="Project type.")
    first_run.add_argument("--interactive", action="store_true", help="Accepted for first-run UX; prompts are not required in file-only MVP.")
    first_run.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    first_run.add_argument("--apply", action="store_true", help="Write files.")
    first_run.add_argument("--force", action="store_true", help="Overwrite existing files.")
    first_run.set_defaults(func=command_first_run)

    release_check = sub.add_parser("release-check", help="Run MVP release hygiene checks.")
    release_check.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    release_check.set_defaults(func=command_release_check)

    release_test = sub.add_parser("release-test", help="Run the v0.1 release validation suite.")
    release_test.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    release_test.set_defaults(func=command_release_test)

    smoke_all = sub.add_parser("smoke-all", help="Alias for release-test.")
    smoke_all.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    smoke_all.set_defaults(func=command_release_test)

    clean = sub.add_parser("clean", help="Remove safe generated ProcessForge artifacts.")
    clean.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    clean.add_argument("--release", action="store_true", help="Remove safe generated release artifacts.")
    clean.set_defaults(func=command_clean)

    release_pack = sub.add_parser("release-pack", help="Build a portable ProcessForge release archive and manifest.")
    release_pack.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    release_pack.add_argument("--output", required=True, help="Release archive path.")
    release_pack.add_argument("--dry-run", action="store_true", help="Print archive contents without writing files.")
    release_pack.set_defaults(func=command_release_pack)

    release_archive_test = sub.add_parser("release-archive-test", help="Inspect a release archive and run release-test after extraction.")
    release_archive_test.add_argument("--archive", required=True, help="Release archive ZIP path.")
    release_archive_test.add_argument("--manifest", help="Optional release manifest path. Defaults to archive path with .manifest.json suffix.")
    release_archive_test.set_defaults(func=command_release_archive_test)

    examples_check = sub.add_parser("examples-check", help="Validate release examples for portability and stale generated data.")
    examples_check.add_argument("--root", default=str(ROOT), help="ProcessForge root path.")
    examples_check.set_defaults(func=command_examples_check)

    version = sub.add_parser("version", help="Print ProcessForge distribution and spec versions.")
    version.set_defaults(func=command_version)

    path_resolve = sub.add_parser("path-resolve", help="Resolve a workplace path using path_constants.")
    path_resolve.add_argument("--workplace", required=True, help="Workplace root path.")
    path_resolve.add_argument("--path", required=True, help="Raw path with optional ${CONST}.")
    path_resolve.set_defaults(func=command_path_resolve)

    knowledge_add_url = sub.add_parser("knowledge-add-url", help="Create or apply a proposal to add a URL-backed knowledge resource.")
    knowledge_add_url.add_argument("--workplace", required=True, help="Workplace root path.")
    knowledge_add_url.add_argument("--package", required=True, help="Knowledge package id.")
    knowledge_add_url.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
    knowledge_add_url.add_argument("--url", required=True, help="External source URL.")
    knowledge_add_url.add_argument("--kind", default="article", help="Resource kind.")
    knowledge_add_url.add_argument("--id", help="Resource id override.")
    knowledge_add_url.add_argument("--title", help="Resource title.")
    knowledge_add_url.add_argument("--description", help="Resource description.")
    knowledge_add_url.add_argument("--license", help="License note.")
    knowledge_add_url.add_argument("--load-policy", dest="load_policy", help="Load policy override.")
    knowledge_add_url.add_argument("--index-policy", dest="index_policy", help="Index policy override.")
    knowledge_add_url.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    knowledge_add_url.add_argument("--apply", action="store_true", help="Update package manifest and resource index.")
    knowledge_add_url.set_defaults(func=command_knowledge_add_url)

    knowledge_add_resource = sub.add_parser("knowledge-add-resource", help="Create or apply a proposal to add a YAML resource record.")
    knowledge_add_resource.add_argument("--workplace", required=True, help="Workplace root path.")
    knowledge_add_resource.add_argument("--package", required=True, help="Knowledge package id.")
    knowledge_add_resource.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
    knowledge_add_resource.add_argument("--resource-file", required=True, help="YAML knowledge resource record.")
    knowledge_add_resource.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    knowledge_add_resource.add_argument("--apply", action="store_true", help="Update package manifest and resource index.")
    knowledge_add_resource.set_defaults(func=command_knowledge_add_resource)

    knowledge_package_doctor = sub.add_parser("knowledge-package-doctor", help="Validate a knowledge package manifest and resource index.")
    knowledge_package_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
    knowledge_package_doctor.add_argument("--package", required=True, help="Knowledge package id.")
    knowledge_package_doctor.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
    knowledge_package_doctor.set_defaults(func=command_knowledge_package_doctor)

    knowledge_index_refresh = sub.add_parser("knowledge-index-refresh", help="Refresh a package resource index without loading heavy resources.")
    knowledge_index_refresh.add_argument("--workplace", required=True, help="Workplace root path.")
    knowledge_index_refresh.add_argument("--package", required=True, help="Knowledge package id.")
    knowledge_index_refresh.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
    knowledge_index_refresh.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    knowledge_index_refresh.add_argument("--apply", action="store_true", help="Write resource index.")
    knowledge_index_refresh.set_defaults(func=command_knowledge_index_refresh)

    docs_import_plan = sub.add_parser("docs-import-plan", help="Create a documentation mirror import plan without downloading content.")
    docs_import_plan.add_argument("--workplace", required=True, help="Workplace root path.")
    docs_import_plan.add_argument("--source", required=True, help="Documentation source id, for example mdn.")
    docs_import_plan.add_argument("--topics", required=True, help="Comma-separated topics.")
    docs_import_plan.add_argument("--package", help="Target documentation package id.")
    docs_import_plan.add_argument("--id", help="Plan id override.")
    docs_import_plan.add_argument("--license", help="License note.")
    docs_import_plan.set_defaults(func=command_docs_import_plan)

    template_add = sub.add_parser("template-add", help="Register a simple workplace template package.")
    template_add.add_argument("--workplace", required=True, help="Workplace root path.")
    template_add.add_argument("--type", required=True, choices=["file", "media", "prompt", "directory", "multi-file"], help="Template type.")
    template_add.add_argument("--id", required=True, help="Template id.")
    template_add.add_argument("--source", required=True, help="Source folder to copy on apply.")
    template_add.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    template_add.add_argument("--apply", action="store_true", help="Copy template payload.")
    template_add.set_defaults(func=command_template_add)

    template_create = sub.add_parser("template-create", help="Author a reusable workplace template.")
    template_create.add_argument("--workplace", required=True, help="Workplace root path.")
    template_create.add_argument("--id", required=True, help="Template id, for example report.audit.basic.")
    template_create.add_argument("--title", required=True, help="Template title.")
    template_create.add_argument("--description", help="Template description.")
    template_create.add_argument("--kind", default="document", choices=["document", "scaffold", "prompt", "assignment", "media_prompt"], help="Template kind.")
    template_create.add_argument("--template-root", dest="template_root", help="Template root id from registries/templates.yaml.")
    template_create.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    template_create.add_argument("--apply", action="store_true", help="Write template files.")
    template_create.add_argument("--force", action="store_true", help="Overwrite an existing template.")
    template_create.set_defaults(func=command_template_create)

    template_doctor = sub.add_parser("template-doctor", help="Validate a reusable workplace template.")
    template_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
    template_doctor.add_argument("--template", required=True, help="Template id.")
    template_doctor.set_defaults(func=command_template_doctor)

    tool_register = sub.add_parser("tool-register", help="Register a workplace tool capability provider.")
    tool_register.add_argument("--workplace", required=True, help="Workplace root path.")
    tool_register.add_argument("--id", required=True, help="Tool id.")
    tool_register.add_argument("--name", help="Tool display name.")
    tool_register.add_argument("--capability", required=True, help="Capability provided by the tool.")
    tool_register.add_argument("--command", required=True, help="Command without secrets.")
    tool_register.add_argument("--healthcheck", help="Healthcheck command.")
    tool_register.add_argument("--status", default="configured", choices=["configured", "optional", "missing", "disabled"], help="Tool status.")
    tool_register.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    tool_register.add_argument("--apply", action="store_true", help="Update tools registry.")
    tool_register.set_defaults(func=command_tool_register)

    mcp_register = sub.add_parser("mcp-register", help="Register a workplace MCP capability provider.")
    mcp_register.add_argument("--workplace", required=True, help="Workplace root path.")
    mcp_register.add_argument("--id", required=True, help="MCP id.")
    mcp_register.add_argument("--name", help="MCP display name.")
    mcp_register.add_argument("--capability", required=True, help="Capability provided by the MCP server.")
    mcp_register.add_argument("--command", required=True, help="Command without secrets.")
    mcp_register.add_argument("--transport", default="stdio", help="MCP transport.")
    mcp_register.add_argument("--auth-ref", dest="auth_ref", help="Optional auth reference name, never the secret value.")
    mcp_register.add_argument("--status", default="configured", choices=["configured", "optional", "missing", "disabled"], help="MCP status.")
    mcp_register.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    mcp_register.add_argument("--apply", action="store_true", help="Update MCP registry.")
    mcp_register.set_defaults(func=command_mcp_register)

    platform_contract_install = sub.add_parser("platform-contract-install", help="Create or update a workplace platform contract.")
    platform_contract_install.add_argument("--workplace", required=True, help="Workplace root path.")
    platform_contract_install.add_argument("--id", required=True, help="Platform id, with or without platform. prefix.")
    platform_contract_install.add_argument("--version", default="1.0.0", help="Contract version.")
    platform_contract_install.add_argument("--required-capabilities", default="", help="Comma-separated required capabilities.")
    platform_contract_install.add_argument("--required-packages", default="", help="Comma-separated required knowledge package ids.")
    platform_contract_install.add_argument("--required-tools", default="", help="Comma-separated required tool ids.")
    platform_contract_install.add_argument("--required-mcp", default="", help="Comma-separated required MCP ids.")
    platform_contract_install.add_argument("--required-templates", default="", help="Comma-separated required template ids.")
    platform_contract_install.add_argument("--recommended-packages", default="", help="Comma-separated recommended knowledge package ids.")
    platform_contract_install.add_argument("--recommended-tools", default="", help="Comma-separated recommended tool ids.")
    platform_contract_install.add_argument("--recommended-mcp", default="", help="Comma-separated recommended MCP ids.")
    platform_contract_install.add_argument("--recommended-templates", default="", help="Comma-separated recommended template ids.")
    platform_contract_install.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    platform_contract_install.add_argument("--apply", action="store_true", help="Write contract and registry entry.")
    platform_contract_install.set_defaults(func=command_platform_contract_install)

    knowledge_package_create = sub.add_parser("knowledge-package-create", help="Author a workplace knowledge package.")
    knowledge_package_create.add_argument("--workplace", required=True, help="Workplace root path.")
    knowledge_package_create.add_argument("--id", required=True, help="Package id.")
    knowledge_package_create.add_argument("--title", required=True, help="Package title.")
    knowledge_package_create.add_argument("--description", help="Package description.")
    knowledge_package_create.add_argument("--package-root", dest="package_root", required=True, help="Package root id from registries/package-roots.yaml.")
    knowledge_package_create.add_argument("--kind", default="documentation", choices=["documentation", "rules", "source", "project", "platform", "mixed"], help="Package kind.")
    knowledge_package_create.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    knowledge_package_create.add_argument("--apply", action="store_true", help="Write package files.")
    knowledge_package_create.add_argument("--force", action="store_true", help="Overwrite an existing package.")
    knowledge_package_create.set_defaults(func=command_knowledge_package_create)

    platform_create = sub.add_parser("platform-create", help="Author a workplace platform contract.")
    platform_create.add_argument("--workplace", required=True, help="Workplace root path.")
    platform_create.add_argument("--id", required=True, help="Platform id, with or without platform. prefix.")
    platform_create.add_argument("--title", required=True, help="Platform title.")
    platform_create.add_argument("--platform-root", dest="platform_root", help="Platform contract root id.")
    platform_create.add_argument("--project-type", action="append", default=[], help="Project type hint. May be repeated.")
    platform_create.add_argument("--knowledge-package", action="append", default=[], help="Referenced knowledge package id. May be repeated.")
    platform_create.add_argument("--template", action="append", default=[], help="Referenced template id. May be repeated.")
    platform_create.add_argument("--tool", action="append", default=[], help="Referenced tool id. May be repeated.")
    platform_create.add_argument("--mcp", action="append", default=[], help="Referenced MCP id. May be repeated.")
    platform_create.add_argument("--process", action="append", default=[], help="Referenced process id. May be repeated.")
    platform_create.add_argument("--dry-run", action="store_true", help="Write proposal only.")
    platform_create.add_argument("--apply", action="store_true", help="Write platform contract files.")
    platform_create.add_argument("--force", action="store_true", help="Overwrite an existing platform contract.")
    platform_create.set_defaults(func=command_platform_create)

    platform_contract_doctor = sub.add_parser("platform-contract-doctor", help="Validate a workplace platform contract.")
    platform_contract_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
    platform_contract_doctor.add_argument("--platform", required=True, help="Platform id, with or without platform. prefix.")
    platform_contract_doctor.set_defaults(func=command_platform_contract_doctor)

    update = sub.add_parser("update", help="Read and validate ProcessForge update framework state.")
    update_sub = update.add_subparsers(dest="update_command", required=True)

    bootstrap_source = update_sub.add_parser("bootstrap-source", help="Read global bootstrap update sources.")
    bootstrap_source_sub = bootstrap_source.add_subparsers(dest="bootstrap_source_command", required=True)
    bootstrap_source_list = bootstrap_source_sub.add_parser("list", help="List global bootstrap update sources.")
    bootstrap_source_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    bootstrap_source_list.add_argument("--json", action="store_true", help="Print JSON.")
    bootstrap_source_list.set_defaults(func=command_update_bootstrap_source_list)
    bootstrap_source_validate = bootstrap_source_sub.add_parser("validate", help="Validate global bootstrap update sources.")
    bootstrap_source_validate.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    bootstrap_source_validate.set_defaults(func=command_update_bootstrap_source_validate)

    update_sources = update_sub.add_parser("sources", help="Compatibility read surface for global bootstrap update sources.")
    update_sources.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    update_sources.add_argument("--list", action="store_true", help="List global bootstrap update sources.")
    update_sources.add_argument("--validate", action="store_true", help="Validate global bootstrap update sources.")
    update_sources.add_argument("--json", action="store_true", help="Print JSON for --list.")
    update_sources.set_defaults(func=command_update_sources)

    entity_sources = update_sub.add_parser("entity-sources", help="Read derived installed entity update sources.")
    entity_sources_sub = entity_sources.add_subparsers(dest="entity_sources_command", required=True)
    entity_sources_rebuild = entity_sources_sub.add_parser("rebuild", help="Rebuild derived entity update sources from installed manifests.")
    entity_sources_rebuild.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    entity_sources_rebuild.add_argument("--dry-run", action="store_true", help="Print derived registry without writing runtime state.")
    entity_sources_rebuild.set_defaults(func=command_update_entity_sources_rebuild)
    entity_sources_list = entity_sources_sub.add_parser("list", help="List derived entity update sources.")
    entity_sources_list.add_argument("--workplace", required=True, help="Workplace root path or workplace.yaml.")
    entity_sources_list.add_argument("--subject-type", default="all", help="Subject type filter or all.")
    entity_sources_list.add_argument("--json", action="store_true", help="Print JSON.")
    entity_sources_list.set_defaults(func=command_update_entity_sources_list)

    update_manifest = update_sub.add_parser("manifest", help="Validate normalized update manifest fixtures.")
    update_manifest_sub = update_manifest.add_subparsers(dest="update_manifest_command", required=True)
    update_manifest_validate = update_manifest_sub.add_parser("validate", help="Validate a normalized update manifest fixture.")
    update_manifest_validate.add_argument("--file", required=True, help="JSON or YAML normalized update manifest.")
    update_manifest_validate.set_defaults(func=command_update_manifest_validate)

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

    process_authoring_start = sub.add_parser("process-authoring-start", help="Start a guided process authoring session.")
    process_authoring_start.add_argument("--project-root", required=True, help="Project root path.")
    process_authoring_start.add_argument("--id", help="Process id.")
    process_authoring_start.add_argument("--title", help="Process title.")
    process_authoring_start.add_argument("--description", help="Process description.")
    process_authoring_start.add_argument("--scope", help="Optional process scope recorded in answers.")
    process_authoring_start.add_argument("--kind", help="Optional process kind recorded in answers.")
    process_authoring_start.add_argument("--answers", help="Optional process authoring answers YAML.")
    process_authoring_start.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    process_authoring_start.add_argument("--apply", action="store_true", help="Write authoring session files.")
    process_authoring_start.set_defaults(func=command_process_authoring_start)

    process_authoring_review = sub.add_parser("process-authoring-review", help="Review a process authoring draft for structural logic issues.")
    process_authoring_review.add_argument("--project-root", required=True, help="Project root path.")
    process_authoring_review.add_argument("--process", help="Process id.")
    process_authoring_review.add_argument("--id", help="Compatibility alias for --process.")
    process_authoring_review.set_defaults(func=command_process_authoring_review)

    process_authoring_apply = sub.add_parser("process-authoring-apply", help="Apply a reviewed process authoring draft.")
    process_authoring_apply.add_argument("--project-root", required=True, help="Project root path.")
    process_authoring_apply.add_argument("--process", help="Process id.")
    process_authoring_apply.add_argument("--id", help="Compatibility alias for --process.")
    process_authoring_apply.add_argument("--apply", action="store_true", help="Accepted for command symmetry; apply is the default action.")
    process_authoring_apply.set_defaults(func=command_process_authoring_apply)

    process_authoring_import = sub.add_parser("process-authoring-import", help="Backfill an authoring session from an existing process definition.")
    process_authoring_import.add_argument("--project-root", required=True, help="Project root path.")
    process_authoring_import.add_argument("--process", help="Process id.")
    process_authoring_import.add_argument("--process-file", help="Process YAML path.")
    process_authoring_import.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    process_authoring_import.add_argument("--apply", action="store_true", help="Write backfill files.")
    process_authoring_import.set_defaults(func=command_process_authoring_import)

    process_parity_check = sub.add_parser("process-parity-check", help="Check semantic parity between a process and its authoring-import draft.")
    process_parity_check.add_argument("--project-root", required=True, help="Project root path.")
    process_parity_check.add_argument("--process", help="Process id.")
    process_parity_check.add_argument("--process-file", help="Process YAML path.")
    process_parity_check.add_argument("--candidate-file", help="Optional candidate YAML for diagnostics.")
    process_parity_check.set_defaults(func=command_process_parity_check)

    process_parity_check_all = sub.add_parser("process-parity-check-all", help="Check semantic authoring parity for every process definition.")
    process_parity_check_all.add_argument("--project-root", required=True, help="Project root path.")
    process_parity_check_all.set_defaults(func=command_process_parity_check_all)

    template_parity_check = sub.add_parser("template-parity-check", help="Check template authoring parity or record a SKIP reason.")
    template_parity_check.add_argument("--project-root", help="Project root path.")
    template_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
    template_parity_check.add_argument("--template", required=True, help="Template id.")
    template_parity_check.set_defaults(func=command_template_parity_check)

    knowledge_package_parity_check = sub.add_parser("knowledge-package-parity-check", help="Check knowledge package authoring parity or record a SKIP reason.")
    knowledge_package_parity_check.add_argument("--project-root", help="Project root path.")
    knowledge_package_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
    knowledge_package_parity_check.add_argument("--package", required=True, help="Package id.")
    knowledge_package_parity_check.set_defaults(func=command_knowledge_package_parity_check)

    platform_parity_check = sub.add_parser("platform-parity-check", help="Check platform contract authoring parity or record a SKIP reason.")
    platform_parity_check.add_argument("--project-root", help="Project root path.")
    platform_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
    platform_parity_check.add_argument("--platform", required=True, help="Platform id.")
    platform_parity_check.set_defaults(func=command_platform_parity_check)

    authoring_parity_check_all = sub.add_parser("authoring-parity-check-all", help="Run process and resource authoring parity checks.")
    authoring_parity_check_all.add_argument("--project-root", required=True, help="Project root path.")
    authoring_parity_check_all.set_defaults(func=command_authoring_parity_check_all)

    process_create = sub.add_parser("process-create", help="Create a new process from answers in one command.")
    process_create.add_argument("--project-root", required=True, help="Project root path.")
    process_create.add_argument("--id", help="Process id when no answers file supplies one.")
    process_create.add_argument("--title", help="Process title when no answers file supplies one.")
    process_create.add_argument("--answers", help="Optional process authoring answers YAML.")
    process_create.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
    process_create.add_argument("--apply", action="store_true", help="Write the process, prompt, docs, and example.")
    process_create.set_defaults(func=command_process_create)

    process_doctor = sub.add_parser("process-doctor", help="Validate a process definition and its generated companion files.")
    process_doctor.add_argument("--project-root", required=True, help="Project root path.")
    process_doctor.add_argument("--process", required=True, help="Process id or YAML path.")
    process_doctor.set_defaults(func=command_process_doctor)

    process_list = sub.add_parser("process-list", help="List available process definitions.")
    process_list.add_argument("--project-root", required=True, help="Project root path.")
    process_list.set_defaults(func=command_process_list)

    process_describe = sub.add_parser("process-describe", help="Describe a process definition.")
    process_describe.add_argument("--project-root", required=True, help="Project root path.")
    process_describe.add_argument("--process", required=True, help="Process id or YAML path.")
    process_describe.set_defaults(func=command_process_describe)

    run_create = sub.add_parser("run-create", help="Create a project run/work session.")
    run_create.add_argument("--project-root", required=True, help="Project root path.")
    run_create.add_argument("--id", required=True, help="Run id.")
    run_create.add_argument("--title", required=True, help="Run title.")
    run_create.add_argument("--process", default="task-batch-execution", help="Process definition id.")
    run_create.add_argument("--objective", help="Run objective.")
    run_create.add_argument("--status", default="in_progress", choices=sorted(RUN_STATUSES), help="Initial run status.")
    run_create.add_argument("--apply", action="store_true", help="Write run files.")
    run_create.set_defaults(func=command_run_create)

    run_list = sub.add_parser("run-list", help="List project runs.")
    run_list.add_argument("--project-root", required=True, help="Project root path.")
    run_list.set_defaults(func=command_run_list)

    run_status = sub.add_parser("run-status", help="Show run status and task summary.")
    run_status.add_argument("--project-root", required=True, help="Project root path.")
    run_status.add_argument("--run", required=True, help="Run id.")
    run_status.set_defaults(func=command_run_status)

    run_doctor = sub.add_parser("run-doctor", help="Validate run consistency.")
    run_doctor.add_argument("--project-root", required=True, help="Project root path.")
    run_doctor.add_argument("--run", required=True, help="Run id.")
    run_doctor.set_defaults(func=command_run_doctor)

    run_summary = sub.add_parser("run-summary", help="Create or refresh run summary and handoff.")
    run_summary.add_argument("--project-root", required=True, help="Project root path.")
    run_summary.add_argument("--run", required=True, help="Run id.")
    run_summary.add_argument("--apply", action="store_true", help="Write summary and handoff files.")
    run_summary.set_defaults(func=command_run_summary)

    run_complete = sub.add_parser("run-complete", help="Complete a run after blocking tasks are done.")
    run_complete.add_argument("--project-root", required=True, help="Project root path.")
    run_complete.add_argument("--run", required=True, help="Run id.")
    run_complete.add_argument("--apply", action="store_true", help="Mark the run completed.")
    run_complete.set_defaults(func=command_run_complete)

    task_create = sub.add_parser("task-create", help="Create a task assignment inside a run.")
    task_create.add_argument("--project-root", required=True, help="Project root path.")
    task_create.add_argument("--run", required=True, help="Run id.")
    task_create.add_argument("--id", required=True, help="Task id.")
    task_create.add_argument("--title", required=True, help="Task title.")
    task_create.add_argument("--process", required=True, help="Task process id.")
    task_create.add_argument("--objective", help="Task objective.")
    task_create.add_argument("--order", type=int, help="Task order override.")
    task_create.add_argument("--execution-mode", choices=["read_only", "planning_only", "docs_only", "implementation", "assurance", "release_delivery"], help="Assignment execution mode.")
    task_create.add_argument("--allowed-file", action="append", default=[], help="Repository-relative writable file or simple glob. Repeatable.")
    task_create.add_argument("--allowed-glob", action="append", default=[], help="Repository-relative writable glob. Stored in allowed_files. Repeatable.")
    task_create.add_argument("--allowed-read-file", action="append", default=[], help="Repository-relative readable file. Repeatable.")
    task_create.add_argument("--read-file", action="append", default=[], help="Alias for --allowed-read-file.")
    task_create.add_argument("--context-artifact", action="append", default=[], help="Repository-relative context artifact. Repeatable.")
    task_create.add_argument("--required-source", action="append", default=[], help="Required source to include in assignment capsules. Repeatable.")
    task_create.add_argument("--forbidden-file", action="append", default=[], help="Repository-relative forbidden write file or simple glob. Repeatable.")
    task_create.add_argument("--forbidden-glob", action="append", default=[], help="Repository-relative forbidden write glob. Stored in forbidden_files. Repeatable.")
    task_create.add_argument("--owner", help="Assignment owner id.")
    task_create.add_argument("--role", help="Assignment owner role.")
    task_create.add_argument("--writer", choices=["true", "false"], default="true", help="Whether the assignment owns write scope.")
    task_create.add_argument("--required-output", action="append", default=[], help="Required output id. Repeatable.")
    task_create.add_argument("--expected-report-language", help="Expected report language.")
    task_create.add_argument("--expected-report-artifact", help="Expected durable report artifact.")
    task_create.add_argument("--force-with-handoff", action="store_true", help="Allow write-scope overlap and record the overlap check for orchestrator handoff.")
    task_create.add_argument("--apply", action="store_true", help="Write task files.")
    task_create.set_defaults(func=command_task_create)

    task_list = sub.add_parser("task-list", help="List tasks in a run.")
    task_list.add_argument("--project-root", required=True, help="Project root path.")
    task_list.add_argument("--run", required=True, help="Run id.")
    task_list.set_defaults(func=command_task_list)

    task_start = sub.add_parser("task-start", help="Mark a task assignment in progress.")
    task_start.add_argument("--project-root", required=True, help="Project root path.")
    task_start.add_argument("--task", required=True, help="Task id.")
    task_start.set_defaults(func=command_task_start)

    task_complete = sub.add_parser("task-complete", help="Complete a task assignment and record its result.")
    task_complete.add_argument("--project-root", required=True, help="Project root path.")
    task_complete.add_argument("--task", required=True, help="Task id.")
    task_complete.add_argument("--summary", required=True, help="Task result summary.")
    task_complete.add_argument("--artifact", action="append", help="Result artifact path. May be repeated.")
    task_complete.add_argument("--apply", action="store_true", help="Mark the task done.")
    task_complete.set_defaults(func=command_task_complete)

    task_doctor = sub.add_parser("task-doctor", help="Validate task assignment consistency.")
    task_doctor.add_argument("--project-root", required=True, help="Project root path.")
    task_doctor.add_argument("--task", required=True, help="Task id.")
    task_doctor.set_defaults(func=command_task_doctor)

    iteration_add = sub.add_parser("iteration-add", help="Add a work/debug/fix/review iteration to a task.")
    iteration_add.add_argument("--project-root", required=True, help="Project root path.")
    iteration_add.add_argument("--task", required=True, help="Task id.")
    iteration_add.add_argument("--id", help="Iteration id. Defaults to the next iter-NNN value.")
    iteration_add.add_argument("--kind", required=True, choices=sorted(ITERATION_KINDS), help="Iteration kind.")
    iteration_add.add_argument("--status", default="completed", choices=sorted(ITERATION_STATUSES), help="Iteration status.")
    iteration_add.add_argument("--summary", required=True, help="Iteration summary.")
    iteration_add.add_argument("--apply", action="store_true", help="Write the iteration.")
    iteration_add.set_defaults(func=command_iteration_add)

    iteration_complete = sub.add_parser("iteration-complete", help="Update an existing iteration status and summary.")
    iteration_complete.add_argument("--project-root", required=True, help="Project root path.")
    iteration_complete.add_argument("--task", required=True, help="Task id.")
    iteration_complete.add_argument("--iteration", required=True, help="Iteration id.")
    iteration_complete.add_argument("--status", required=True, choices=sorted(ITERATION_STATUSES), help="Final iteration status.")
    iteration_complete.add_argument("--summary", help="Replacement iteration summary.")
    iteration_complete.add_argument("--apply", action="store_true", help="Write the iteration update.")
    iteration_complete.set_defaults(func=command_iteration_complete)

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
