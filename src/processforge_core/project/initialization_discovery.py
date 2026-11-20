"""Existing project classifier, detection and initial resource-matching operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml, yaml_error
from ..documents.reader import YamlDocumentReader
from .classification import ProjectClassifierRulePolicy
from .classifier_sources import ProjectClassifierSourceReader
from .detection import ProjectDetectionService
from .platforms import PlatformContractReader

def registry_text(workplace_manifest: Path, registry_name: str) -> str:
    root = workplace_manifest.parent
    path = root / 'registries' / registry_name
    if path.is_file():
        return path.read_text(encoding='utf-8', errors='replace')
    return ''


@dataclass(frozen=True)
class ProjectDiscoveryReader:
    classifiers: ProjectClassifierSourceReader
    rules: ProjectClassifierRulePolicy = field(default_factory=ProjectClassifierRulePolicy)
    detection: ProjectDetectionService = field(default_factory=ProjectDetectionService)
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml))

    def classify_project(self, project_root: Path, workplace_manifest: Path | None=None, explicit_classifier_paths: list[Path] | None=None) -> dict[str, Any]:
        files = self.classifiers.list_classifier_files(project_root)
        available_paths = self.classifiers.project_available_paths(project_root, files)
        project_types: set[str] = set()
        platforms: set[str] = set()
        tags: set[str] = set()
        matched_rules: list[dict[str, Any]] = []
        confidence_rank = {'low': 1, 'medium': 2, 'high': 3}
        confidence = 'low'
        loaded: list[str] = []
        for path in self.classifiers.project_classifier_paths(workplace_manifest, project_root, explicit_classifier_paths):
            classifier = self.documents.load(path)
            if not isinstance(classifier, dict) or yaml_error(classifier) or classifier.get('kind') != 'processforge.project_classifier' or (str(classifier.get('status', 'active')) != 'active'):
                continue
            classifier_id = str(classifier.get('id') or path.stem)
            loaded.append(classifier_id)
            rules = classifier.get('rules')
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict) or not self.rules.matches(rule, available_paths):
                    continue
                classify_as = rule.get('classify_as')
                if not isinstance(classify_as, dict):
                    continue
                project_types.update((str(item) for item in classify_as.get('project_types', []) if str(item)))
                platforms.update((str(item) for item in classify_as.get('platforms', []) if str(item)))
                tags.update((str(item) for item in classify_as.get('tags', []) if str(item)))
                rule_confidence = str(rule.get('confidence', 'medium'))
                if confidence_rank.get(rule_confidence, 0) > confidence_rank.get(confidence, 0):
                    confidence = rule_confidence
                matched_rules.append({'classifier': classifier_id, 'rule': str(rule.get('id') or 'rule'), 'confidence': rule_confidence, 'source': self.classifiers.project_classifier_source_label(path, project_root, workplace_manifest=workplace_manifest)})
        inactive_hints = self.classifiers.inactive_official_classifier_hints(workplace_manifest, project_root, files) if not matched_rules else []
        return {'status': 'classified' if matched_rules else 'unclassified', 'project_types': sorted(project_types), 'platforms': sorted(platforms), 'tags': sorted(tags), 'confidence': confidence, 'loaded_classifiers': sorted(set(loaded)), 'matched_rules': matched_rules, 'inactive_classifier_hints': inactive_hints}

    def detect_project(self, project_root: Path, workplace_manifest: Path | None=None, explicit_classifier_paths: list[Path] | None=None) -> dict[str, Any]:
        files = self.detection.files(project_root)
        top_dirs = sorted({item.parts[0] for path in files for item in [path.relative_to(project_root)] if item.parts}.union({path.name for path in project_root.iterdir() if path.is_dir() and path.name not in {'.git', '.idea', '.serena'}}))
        classification = self.classify_project(project_root, workplace_manifest, explicit_classifier_paths)
        project_types = classification['project_types'] or ['unknown']
        evidence = [f"{item['classifier']}/{item['rule']}" for item in classification['matched_rules']]
        return {'status': classification['status'], 'languages': [], 'platforms': classification['platforms'], 'frameworks': [], 'project_kind': project_types, 'tags': classification['tags'], 'confidence': classification['confidence'], 'loaded_classifiers': classification['loaded_classifiers'], 'matched_rules': classification['matched_rules'], 'inactive_classifier_hints': classification['inactive_classifier_hints'], 'evidence': evidence or ['No loaded project classifier matched.'], 'files': [rel(path, project_root) for path in files[:300]], 'top_dirs': top_dirs}


@dataclass(frozen=True)
class ProjectResourceMatcher:
    platforms: PlatformContractReader

    def match_global_resources(self, workplace_manifest: Path, detected: dict[str, Any], required: list[str], optional: list[str]) -> dict[str, list[str]]:
        tools_text = registry_text(workplace_manifest, 'tools.yaml')
        mcp_text = registry_text(workplace_manifest, 'mcp.yaml')
        templates_text = registry_text(workplace_manifest, 'templates.yaml')
        package_text = registry_text(workplace_manifest, 'package-roots.yaml')
        available_platform_ids = set(self.platforms.index(workplace_manifest))
        available_platform_ids.update((item.removeprefix('platform.') for item in list(available_platform_ids)))
        matched_platforms = [item for item in detected['platforms'] if item and (item in available_platform_ids or self.platforms.contract_id(item) in available_platform_ids)]
        missing_platforms = [item for item in detected['platforms'] if item and item not in matched_platforms]
        matched_tools = [cap for cap in required + optional if cap and cap in tools_text]
        matched_mcp = [cap for cap in required + optional if cap and cap in mcp_text]
        missing_required = [cap for cap in required if cap not in tools_text and cap not in mcp_text]
        optional_missing = [cap for cap in optional if cap not in tools_text and cap not in mcp_text]
        matched_templates = ['template roots configured'] if 'template_roots:' in templates_text and '[]' not in templates_text else []
        matched_packages = ['package roots configured'] if 'package_roots:' in package_text and '[]' not in package_text else []
        return {'matched_platforms': matched_platforms, 'missing_platforms': missing_platforms, 'matched_packages': matched_packages, 'matched_tools': matched_tools, 'matched_mcp': matched_mcp, 'matched_templates': matched_templates, 'missing_required': missing_required, 'optional_missing': optional_missing, 'conflicts': []}
