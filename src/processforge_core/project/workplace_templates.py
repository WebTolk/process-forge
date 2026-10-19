"""Existing workplace file and registry template generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.process_catalog.profile_packs import OfficialPackProfileReader
from processforge_core.project.coordination import ProjectCoordinationReader
from processforge_core.project.setup_answers import WorkplaceSetupAnswers
from processforge_core.project.workplace_terms import WorkplaceTermsBuilder
import processforge_core.resources.registries as _core_resources_registries
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy


class WorkplaceFileBuilder:
    """Compose existing concrete Core owners for workplace generation."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.setup_answers = WorkplaceSetupAnswers()
        self.coordination = ProjectCoordinationReader()
        self.runtime_drivers = RuntimeDriverDefinitionPolicy()
        self.terms = WorkplaceTermsBuilder()
        self.profile_packs = OfficialPackProfileReader(distribution_root)

    def build_workplace_files(self, root: Path, answers: dict[str, Any]) -> dict[Path, str]:
        from processforge_core.configuration import PFConfig
        defaults = self.setup_answers.workplace_defaults(root, answers)
        profile = str(answers.get("profile") or "generic").strip() or "generic"
        paths_answers = answers.get("paths", {}) if isinstance(answers.get("paths"), dict) else {}
        policies_answers = answers.get("policies", {}) if isinstance(answers.get("policies"), dict) else {}
        coordination_answers = answers.get("coordination", {}) if isinstance(answers.get("coordination"), dict) else {}
        director_answers = coordination_answers.get("director", {}) if isinstance(coordination_answers.get("director"), dict) else {}
        workplace_parameters = answers.get("parameters") if isinstance(answers.get("parameters"), dict) else {}
        workplace_coordination = self.coordination.workplace_defaults()
        workplace_coordination["director_enabled"] = bool(coordination_answers.get("director_enabled", False))
        workplace_coordination["director_office_enabled"] = bool(coordination_answers.get("director_office_enabled", False))
        workplace_coordination["default_project_mode"] = self.coordination.workplace_mode(coordination_answers.get("default_project_mode", "simple"))
        workplace_coordination["director"].update({key: value for key, value in director_answers.items() if value not in (None, "")})
        path_constants = dict(_core_resources_registries.DEFAULT_PATH_CONSTANTS)
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
                "parameters": "registries/parameters.yaml",
                "specializations": "registries/specializations.yaml",
                "project_classifiers": "registries/project-classifiers.yaml",
                "process_packs": "registries/process-packs.yaml",
                "runtime_drivers": "registries/runtime-drivers.yaml",
                "update_sources": "registries/update-sources.yaml",
                "installed_subjects": "registries/installed-subjects.yaml",
                "update_site_overrides": "registries/update-site-overrides.yaml",
            },
            "policies": {
                "prefer_project_overrides": True,
                "require_explicit_override_for_locked_policies": True,
                "shell_is_fallback": bool(policies_answers.get("shell_is_fallback", True)),
                "prefer_secret_refs": True,
                "public_exports_must_sanitize_secrets": True,
                "require_public_cleanliness_check": True,
            },
            "coordination": workplace_coordination,
            "process_packs": {
                "profile": profile,
            },
            "capability_resolution": {
                "missing_required_capability": "block",
                "missing_optional_capability": "warn",
                "prefer_project_tool_over_global": True,
                "allow_fallback_tools": True,
            },
        }
    
        knowledge_entries = self.setup_answers.dict_entries_from_answers(
            paths_answers.get("knowledge_roots"), "knowledge-root", "workplace"
        )
        for entry in knowledge_entries:
            entry["visibility"] = "private"
            entry["indexing_policy"] = "allowed"
    
        package_entries = self.setup_answers.dict_entries_from_answers(paths_answers.get("package_roots"), "package-root", "workplace")
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
        template_entries = self.setup_answers.dict_entries_from_answers(paths_answers.get("template_roots"), "template-root", "workplace")
        distribution_entries = self.setup_answers.dict_entries_from_answers(paths_answers.get("distributions"), "distribution", "workplace")
        if not distribution_entries:
            distribution_entries = [
                {
                    "id": "processforge",
                    "name": "ProcessForge",
                    "path": str(self.distribution_root),
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
        active_process_packs = self.profile_packs.official_pack_registry_entries_for_profile(profile)
    
        agents = f"""# ProcessForge Workplace Layer

This directory is a ProcessForge workplace layer.

## Start Here

1. Read `workplace.yaml`.
2. Resolve registries from `registries/`.
3. Use capability providers from `registries/tools.yaml` and `registries/mcp.yaml`.
4. Use package roots and template roots only through registry entries.

## Rules

- Prefer secret refs for portable data; keep any inline local credentials in private/local parameter sources.
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
- registries/parameters.yaml
- registries/specializations.yaml
- registries/project-classifiers.yaml
- registries/process-packs.yaml
- registries/runtime-drivers.yaml
- registries/update-sources.yaml
- registries/installed-subjects.yaml
- registries/update-site-overrides.yaml

## Notes

- Secret refs are preferred for portable data; local private parameter files may carry inline credentials when the operator accepts that risk.
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
            root / "configuration.yaml": dump_yaml(PFConfig().to_dict()),
            root / "terms.yaml": dump_yaml(self.terms.build_terms()),
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
            root / "registries" / "parameters.yaml": dump_yaml({"schema_version": 1, "kind": "processforge.parameters", "scope": "workplace", "parameters": workplace_parameters}),
            root / "registries" / "specializations.yaml": dump_yaml(
                {"schema_version": 1, "specializations": []}
            ),
            root / "registries" / "project-classifiers.yaml": dump_yaml(
                {"schema_version": 1, "project_classifiers": []}
            ),
            root / "registries" / "process-packs.yaml": dump_yaml(
                {"schema_version": 1, "profile": profile, "process_packs": active_process_packs}
            ),
            root / "registries" / "agents.yaml": dump_yaml({"schema_version": 1, "agents": []}),
            root / "registries" / "runtime-drivers.yaml": dump_yaml(self.runtime_drivers.default_registry()),
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
        for driver_id, driver in self.runtime_drivers.default_documents().items():
            files[root / "runtime-drivers" / f"{driver_id}.yaml"] = dump_yaml(driver)
        return files
