"""Register existing CLI commands for resources."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Collection


class TemplateCommandParser:
    """Register the existing templates command family."""

    def __init__(
        self,
        *,
        template_add: Callable[[argparse.Namespace], int],
        template_create: Callable[[argparse.Namespace], int],
        template_doctor: Callable[[argparse.Namespace], int],
    ) -> None:
        self._template_add = template_add
        self._template_create = template_create
        self._template_doctor = template_doctor

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        template_add = add_parser("template-add", help="Register a simple workplace template package.")
        template_add.add_argument("--workplace", required=True, help="Workplace root path.")
        template_add.add_argument("--type", required=True, choices=["file", "media", "prompt", "directory", "multi-file"], help="Template type.")
        template_add.add_argument("--id", required=True, help="Template id.")
        template_add.add_argument("--source", required=True, help="Source folder to copy on apply.")
        template_add.add_argument("--dry-run", action="store_true", help="Write proposal only.")
        template_add.add_argument("--apply", action="store_true", help="Copy template payload.")
        template_add.set_defaults(func=self._template_add)

        template_create = add_parser("template-create", help="Author a reusable workplace template.")
        template_create.add_argument("--workplace", required=True, help="Workplace root path.")
        template_create.add_argument("--id", required=True, help="Template id, for example report.audit.basic.")
        template_create.add_argument("--title", required=True, help="Template title.")
        template_create.add_argument("--description", help="Template description.")
        template_create.add_argument("--kind", default="document", choices=["document", "scaffold", "prompt", "assignment", "media_prompt"], help="Template kind.")
        template_create.add_argument("--template-root", dest="template_root", help="Template root id from registries/templates.yaml.")
        template_create.add_argument("--dry-run", action="store_true", help="Write proposal only.")
        template_create.add_argument("--apply", action="store_true", help="Write template files.")
        template_create.add_argument("--force", action="store_true", help="Overwrite an existing template.")
        template_create.set_defaults(func=self._template_create)

        template_doctor = add_parser("template-doctor", help="Validate a reusable workplace template.")
        template_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        template_doctor.add_argument("--template", required=True, help="Template id.")
        template_doctor.set_defaults(func=self._template_doctor)


class ProviderCommandParser:
    """Register the existing providers command family."""

    def __init__(
        self,
        *,
        mcp_register: Callable[[argparse.Namespace], int],
        tool_register: Callable[[argparse.Namespace], int],
    ) -> None:
        self._mcp_register = mcp_register
        self._tool_register = tool_register

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        tool_register = add_parser("tool-register", help="Register a workplace tool capability provider.")
        tool_register.add_argument("--workplace", required=True, help="Workplace root path.")
        tool_register.add_argument("--id", required=True, help="Tool id.")
        tool_register.add_argument("--name", help="Tool display name.")
        tool_register.add_argument("--capability", required=True, help="Capability provided by the tool.")
        tool_register.add_argument("--command", required=True, help="Command without secrets.")
        tool_register.add_argument("--healthcheck", help="Healthcheck command.")
        tool_register.add_argument("--status", default="configured", choices=["configured", "optional", "missing", "disabled"], help="Tool status.")
        tool_register.add_argument("--dry-run", action="store_true", help="Write proposal only.")
        tool_register.add_argument("--apply", action="store_true", help="Update tools registry.")
        tool_register.set_defaults(func=self._tool_register)

        mcp_register = add_parser("mcp-register", help="Register a workplace MCP capability provider.")
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
        mcp_register.set_defaults(func=self._mcp_register)


class SpecializationCommandParser:
    """Register the existing specializations command family."""

    def __init__(
        self,
        *,
        specialization_bind_platform: Callable[[argparse.Namespace], int],
        specialization_create: Callable[[argparse.Namespace], int],
        specialization_doctor: Callable[[argparse.Namespace], int],
        specialization_list: Callable[[argparse.Namespace], int],
        specialization_show: Callable[[argparse.Namespace], int],
    ) -> None:
        self._specialization_bind_platform = specialization_bind_platform
        self._specialization_create = specialization_create
        self._specialization_doctor = specialization_doctor
        self._specialization_list = specialization_list
        self._specialization_show = specialization_show

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        specialization_list = add_parser("specialization-list", help="List workplace/project specialization resources.")
        specialization_list.add_argument("--workplace", required=True, help="Workplace root path.")
        specialization_list.add_argument("--project-root", help="Project root path for project-local specializations.")
        specialization_list.add_argument("--json", action="store_true", help="Print JSON.")
        specialization_list.set_defaults(func=self._specialization_list)

        specialization_show = add_parser("specialization-show", help="Show one specialization resource.")
        specialization_show.add_argument("--workplace", required=True, help="Workplace root path.")
        specialization_show.add_argument("--project-root", help="Project root path for project-local specializations.")
        specialization_show.add_argument("--id", required=True, help="Specialization id.")
        specialization_show.add_argument("--json", action="store_true", help="Print JSON.")
        specialization_show.set_defaults(func=self._specialization_show)

        specialization_doctor = add_parser("specialization-doctor", help="Validate one specialization resource.")
        specialization_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        specialization_doctor.add_argument("--id", required=True, help="Specialization id.")
        specialization_doctor.set_defaults(func=self._specialization_doctor)

        specialization_create = add_parser("specialization-create", help="Create a workplace specialization resource.")
        specialization_create.add_argument("--workplace", required=True, help="Workplace root path.")
        specialization_create.add_argument("--id", required=True, help="Specialization id.")
        specialization_create.add_argument("--title", help="Specialization title.")
        specialization_create.add_argument("--description", help="Specialization description.")
        specialization_create.add_argument("--apply", action="store_true", help="Write the specialization resource.")
        specialization_create.add_argument("--force", action="store_true", help="Overwrite an existing specialization file.")
        specialization_create.set_defaults(func=self._specialization_create)

        specialization_bind_platform = add_parser("specialization-bind-platform", help="Add a platform binding to a specialization.")
        specialization_bind_platform.add_argument("--workplace", required=True, help="Workplace root path.")
        specialization_bind_platform.add_argument("--specialization", required=True, help="Specialization id.")
        specialization_bind_platform.add_argument("--platform", required=True, help="Platform id.")
        specialization_bind_platform.add_argument("--platform-stack-includes", action="append", default=[], help="Platform stack id that also activates this binding. Repeatable.")
        specialization_bind_platform.add_argument("--process", action="append", default=[], help="Deprecated process id filter. Repeatable.")
        specialization_bind_platform.add_argument("--project-type", action="append", default=[], help="Project type filter. Repeatable.")
        specialization_bind_platform.add_argument("--requires-knowledge", action="append", default=[], help="Required knowledge package id. Repeatable.")
        specialization_bind_platform.add_argument("--requires-tool", action="append", default=[], help="Required tool id. Repeatable.")
        specialization_bind_platform.add_argument("--requires-mcp", action="append", default=[], help="Required MCP id. Repeatable.")
        specialization_bind_platform.add_argument("--requires-template", action="append", default=[], help="Required template id. Repeatable.")
        specialization_bind_platform.add_argument("--provides-capability", action="append", default=[], help="Capability id provided by this binding. Repeatable.")
        specialization_bind_platform.add_argument("--apply", action="store_true", help="Write the binding.")
        specialization_bind_platform.set_defaults(func=self._specialization_bind_platform)


class ProjectOverrideCommandParser:
    """Register the existing overrides command family."""

    def __init__(
        self,
        *,
        project_override_add: Callable[[argparse.Namespace], int],
        project_override_doctor: Callable[[argparse.Namespace], int],
        project_override_list: Callable[[argparse.Namespace], int],
        override_modes: Collection[str],
    ) -> None:
        self._project_override_add = project_override_add
        self._project_override_doctor = project_override_doctor
        self._project_override_list = project_override_list
        self._override_modes = override_modes

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        project_override_add = add_parser("project-override-add", help="Add or update a project-local override entry.")
        project_override_add.add_argument("--project-root", required=True, help="Project root path.")
        project_override_add.add_argument("--kind", required=True, help="Override kind: template, knowledge_package, tool, mcp, specialization.")
        project_override_add.add_argument("--target", required=True, help="Target resource id.")
        project_override_add.add_argument("--mode", required=True, choices=sorted(self._override_modes), help="Override mode.")
        project_override_add.add_argument("--path", help="Project-local override file path.")
        project_override_add.add_argument("--project-package", help="Project-local package id for knowledge package extensions.")
        project_override_add.add_argument("--param", action="append", default=[], help="Parameter key=value. Repeatable.")
        project_override_add.add_argument("--reason", required=True, help="Human-readable reason.")
        project_override_add.add_argument("--apply", action="store_true", help="Write .pf/project-overrides.yaml.")
        project_override_add.set_defaults(func=self._project_override_add)

        project_override_list = add_parser("project-override-list", help="List project-local overrides.")
        project_override_list.add_argument("--project-root", required=True, help="Project root path.")
        project_override_list.add_argument("--json", action="store_true", help="Print JSON.")
        project_override_list.set_defaults(func=self._project_override_list)

        project_override_doctor = add_parser("project-override-doctor", help="Validate project-local overrides.")
        project_override_doctor.add_argument("--project-root", required=True, help="Project root path.")
        project_override_doctor.set_defaults(func=self._project_override_doctor)


class PlatformCommandParser:
    """Register the existing platforms command family."""

    def __init__(
        self,
        *,
        platform_contract_doctor: Callable[[argparse.Namespace], int],
        platform_contract_install: Callable[[argparse.Namespace], int],
        platform_create: Callable[[argparse.Namespace], int],
    ) -> None:
        self._platform_contract_doctor = platform_contract_doctor
        self._platform_contract_install = platform_contract_install
        self._platform_create = platform_create

    def register_install(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        platform_contract_install = add_parser("platform-contract-install", help="Create or update a workplace platform contract.")
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
        platform_contract_install.add_argument("--dry-run", action="store_true", help="Show the complete transaction plan without writing.")
        platform_contract_install.add_argument("--apply", action="store_true", help="Write contract and registry entry.")
        platform_contract_install.set_defaults(func=self._platform_contract_install)

    def register_authoring(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        platform_create = add_parser("platform-create", help="Author a workplace platform contract.")
        platform_create.add_argument("--workplace", required=True, help="Workplace root path.")
        platform_create.add_argument("--id", required=True, help="Platform id, with or without platform. prefix.")
        platform_create.add_argument("--title", required=True, help="Platform title.")
        platform_create.add_argument("--platform-root", dest="platform_root", help="Platform contract root id.")
        platform_create.add_argument("--project-type", action="append", default=[], help="Project type hint. May be repeated.")
        platform_create.add_argument("--requires-package", action="append", default=[], help="Required knowledge package id. May be repeated.")
        platform_create.add_argument("--recommends-package", action="append", default=[], help="Recommended knowledge package id. May be repeated.")
        platform_create.add_argument("--optional-package", action="append", default=[], help="Optional knowledge package id. May be repeated.")
        platform_create.add_argument("--requires-template", action="append", default=[], help="Required template id. May be repeated.")
        platform_create.add_argument("--recommends-template", action="append", default=[], help="Recommended template id. May be repeated.")
        platform_create.add_argument("--optional-template", action="append", default=[], help="Optional template id. May be repeated.")
        platform_create.add_argument("--requires-tool", action="append", default=[], help="Required tool id. May be repeated.")
        platform_create.add_argument("--recommends-tool", action="append", default=[], help="Recommended tool id. May be repeated.")
        platform_create.add_argument("--optional-tool", action="append", default=[], help="Optional tool id. May be repeated.")
        platform_create.add_argument("--requires-mcp", action="append", default=[], help="Required MCP id. May be repeated.")
        platform_create.add_argument("--recommends-mcp", action="append", default=[], help="Recommended MCP id. May be repeated.")
        platform_create.add_argument("--optional-mcp", action="append", default=[], help="Optional MCP id. May be repeated.")
        platform_create.add_argument("--process", action="append", default=[], help="Referenced process id. May be repeated.")
        platform_create.add_argument("--dry-run", action="store_true", help="Show the complete transaction plan without writing.")
        platform_create.add_argument("--apply", action="store_true", help="Write platform contract files.")
        platform_create.add_argument("--force", action="store_true", help="Overwrite an existing platform contract.")
        platform_create.set_defaults(func=self._platform_create)

        platform_contract_doctor = add_parser("platform-contract-doctor", help="Validate a workplace platform contract.")
        platform_contract_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        platform_contract_doctor.add_argument("--platform", required=True, help="Platform id, with or without platform. prefix.")
        platform_contract_doctor.set_defaults(func=self._platform_contract_doctor)
