#!/usr/bin/env python3
"""Helpers for specialization and project override smokes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run_pf(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PF), *args], cwd=str(cwd or ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def require_ok(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_workspace(root: Path) -> Path:
    workplace = root / "workplace"
    write_yaml(
        workplace / "workplace.yaml",
        {
            "schema_version": 1,
            "registries": {
                "platforms": "registries/platforms.yaml",
                "package_roots": "registries/package-roots.yaml",
                "knowledge_roots": "registries/knowledge-roots.yaml",
                "templates": "registries/templates.yaml",
                "tools": "registries/tools.yaml",
                "mcp": "registries/mcp.yaml",
                "specializations": "registries/specializations.yaml",
            },
            "path_constants": {
                "PF_WORKPLACE": ".",
                "PF_SPECIALIZATIONS": "specializations",
                "PF_PLATFORM_CONTRACTS": "platform-contracts",
            },
        },
    )
    write_yaml(
        workplace / "registries" / "platforms.yaml",
        {
            "schema_version": 1,
            "platforms": [
                {"id": "parent", "package_id": "fixture.platform.parent", "path": "platform-contracts/fixture.platform.parent/platform-contract.yaml", "status": "available"},
                {"id": "child", "package_id": "fixture.platform.child", "path": "platform-contracts/fixture.platform.child/platform-contract.yaml", "status": "available"},
                {"id": "test", "package_id": "fixture.platform.test", "path": "platform-contracts/fixture.platform.test/platform-contract.yaml", "status": "available"},
            ],
        },
    )
    write_yaml(workplace / "registries" / "package-roots.yaml", {"schema_version": 1, "package_roots": [{"id": "global", "path": "packages", "status": "available", "default": True}]})
    write_yaml(workplace / "registries" / "knowledge-roots.yaml", {"schema_version": 1, "knowledge_roots": []})
    write_yaml(workplace / "registries" / "templates.yaml", {"schema_version": 1, "template_roots": [], "templates": [{"id": "fixture.template.a", "path": "templates/a/template.yaml", "status": "available", "provides_capabilities": ["fixture.capability.template-a"]}]})
    write_yaml(workplace / "registries" / "tools.yaml", {"schema_version": 1, "tools": [{"id": "fixture.tool.a", "capability": "fixture.capability.tool-a", "status": "available"}, {"id": "fixture.tool.b", "capability": "fixture.capability.tool-b", "status": "available"}]})
    write_yaml(workplace / "registries" / "mcp.yaml", {"schema_version": 1, "mcp_servers": [{"id": "fixture.mcp.a", "capability": "fixture.capability.mcp-a", "status": "configured"}]})
    write_yaml(workplace / "registries" / "specializations.yaml", {"schema_version": 1, "specializations": []})
    write_yaml(
        workplace / "platform-contracts" / "fixture.platform.parent" / "platform-contract.yaml",
        {
            "schema_version": 1,
            "id": "fixture.platform.parent",
            "title": "Fixture Parent",
            "type": "platform_contract",
            "version": "1.0.0",
            "status": "draft",
            "requires": {"capabilities": [], "knowledge_packages": ["fixture.docs.parent"], "tools": [], "mcp": [], "templates": []},
        },
    )
    write_yaml(
        workplace / "platform-contracts" / "fixture.platform.child" / "platform-contract.yaml",
        {
            "schema_version": 1,
            "id": "fixture.platform.child",
            "title": "Fixture Child",
            "type": "platform_contract",
            "version": "1.0.0",
            "status": "draft",
            "extends": ["fixture.platform.parent"],
            "requires": {"capabilities": [], "knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        },
    )
    write_yaml(
        workplace / "platform-contracts" / "fixture.platform.test" / "platform-contract.yaml",
        {"schema_version": 1, "id": "fixture.platform.test", "title": "Fixture Test", "type": "platform_contract", "version": "1.0.0", "status": "draft", "requires": {"capabilities": []}},
    )
    for package_id in ["fixture.docs.parent", "fixture.docs.child-dev", "fixture.docs.child-content", "project.fixture.local-rules"]:
        write_yaml(workplace / "packages" / package_id / "package.yaml", {"schema_version": 1, "id": package_id, "name": package_id, "version": "1.0.0", "kind": "documentation", "scope": "workplace", "resources": []})
    return workplace


def specialization_doc(
    spec_id: str,
    *,
    tool: str | None = None,
    package: str | None = None,
    platform: str = "fixture.platform.child",
    provides_capabilities: list[str] | None = None,
) -> dict:
    resources = {
        "requires": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "recommends": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "optional": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "excludes": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
    }
    binding_resources = {
        "requires": {
            "knowledge_packages": [package] if package else [],
            "tools": [],
            "mcp": ["fixture.mcp.a"] if spec_id.endswith("audit") else [],
            "templates": ["fixture.template.a"] if spec_id.endswith("content") else [],
        },
        "recommends": {"knowledge_packages": [], "tools": [tool] if tool else [], "mcp": [], "templates": []},
        "optional": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "excludes": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
    }
    return {
        "schema_version": 1,
        "kind": "processforge.specialization",
        "id": spec_id,
        "name": spec_id,
        "status": "active",
        "scope": {"owner": "workspace", "visibility": "local"},
        "resources": resources,
        "provides_capabilities": [],
        "platform_bindings": [{"platforms": [platform], "platform_stack_includes": [], "applies_to_project_types": [], "resources": binding_resources, "provides_capabilities": provides_capabilities or []}],
        "tool_policy": {"allowed_tools": [], "disallowed_tools": []},
        "metadata": {"tags": ["fixture"]},
    }


def write_specialization(
    workplace: Path,
    spec_id: str,
    *,
    tool: str | None = None,
    package: str | None = None,
    platform: str = "fixture.platform.child",
    provides_capabilities: list[str] | None = None,
) -> None:
    path = workplace / "specializations" / f"{spec_id}.yaml"
    write_yaml(path, specialization_doc(spec_id, tool=tool, package=package, platform=platform, provides_capabilities=provides_capabilities))
    registry = read_yaml(workplace / "registries" / "specializations.yaml")
    registry.setdefault("specializations", []).append({"id": spec_id, "path": f"specializations/{spec_id}.yaml", "status": "available", "scope": "workplace"})
    write_yaml(workplace / "registries" / "specializations.yaml", registry)


def write_project(root: Path, workplace: Path, *, specializations: list[str] | None = None, platform: str = "fixture.platform.child") -> Path:
    project = root / "project"
    flow = project / ".pf"
    write_yaml(
        flow / "process-forge.yaml",
        {
            "schema_version": 1,
            "process_forge": {"version": "1.0.0", "install_mode": "linked"},
            "project": {"id": "fixture-project", "name": "Fixture Project", "type": "fixture"},
            "workplace": {"reference": "local_file"},
            "platform_contracts": [{"id": platform}],
            "specializations": specializations or [],
            "required_capabilities": [],
            "optional_capabilities": [],
            "paths": {"contexts": "contexts", "runtime": "runtime"},
            "knowledge_stack": [],
            "context_requirements": {},
        },
    )
    write_yaml(flow / "process-forge.local.yaml", {"schema_version": 1, "workplace": {"manifest": str((workplace / "workplace.yaml").resolve())}})
    (flow / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
    (flow / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    return project


def write_process_with_capability(project: Path, process_id: str = "fixture-process-a", capability: str = "fixture.capability.a") -> Path:
    path = project / ".pf" / "processes" / "user" / f"{process_id}.yaml"
    write_yaml(
        path,
        {
            "schema_version": 1,
            "id": process_id,
            "name": "Fixture Content Publication",
            "version": "1.0.0",
            "status": "draft",
            "description": "Fixture process for capability resolution.",
            "roles": [{"id": "worker", "title": "Worker", "kind": "primary_agent"}],
            "stages": [
                {
                    "id": "acceptance-check",
                    "title": "Acceptance Check",
                    "required_role": "worker",
                    "produced_artifacts": [],
                    "exit_gates": [],
                    "required_capabilities": [capability],
                    "required_evidence": ["fixture-evidence-frontend-report"],
                }
            ],
            "artifact_definitions": [],
            "gates": [],
            "acceptance": {"requires": ["fixture-evidence-frontend-report"], "criteria": ["fixture acceptance is recorded"]},
            "evolution_policy": {},
        },
    )
    return path


def resolve_json(project: Path, workplace: Path, spec_id: str, platform: str = "fixture.platform.child", process: str | None = None) -> dict:
    args = ["context-resolve", "--project-root", str(project), "--workplace", str(workplace), "--platform", platform]
    if process:
        args.extend(["--process", process])
    args.extend(["--specialization", spec_id, "--json"])
    result = run_pf(*args)
    output = require_ok(result)
    return json.loads(output)["resolved_context"]
