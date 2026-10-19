"""Existing workplace term definitions, generated without retained state."""

from __future__ import annotations

from typing import Any


class WorkplaceTermsBuilder:
    """Build the existing vocabulary with fresh mappings on each operation."""

    def build_terms(self) -> dict[str, Any]:
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
                    "aliases": ["knowledge resource add", "resource index", "resource import"],
                    "aliases_ru": ["управление знаниями", "индекс ресурсов", "импорт ресурсов"],
                    "definition": "Proposal-first workplace processes and commands for maintaining knowledge resources, templates, tools, MCP, and platform contracts.",
                    "resolves_to": {"processes": ["knowledge-resource-add", "template-add", "tool-register", "mcp-register"]},
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
