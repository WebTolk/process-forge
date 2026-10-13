"""Existing project knowledge requirements and version-aware resource selection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..resources.versioning import ResourceVersionPolicy
from .resource_snapshot import ResourceSnapshotRules


@dataclass(frozen=True)
class KnowledgeResourceSelector:
    """Select existing records using concrete Core rules and fresh result containers."""

    versions: ResourceVersionPolicy = field(
        default_factory=ResourceVersionPolicy,
        kw_only=True,
        repr=False,
        compare=False,
    )
    snapshots: ResourceSnapshotRules = field(
        default_factory=ResourceSnapshotRules,
        kw_only=True,
        repr=False,
        compare=False,
    )


    def requirements(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        requirements = manifest_data.get('context_requirements') if isinstance(manifest_data.get('context_requirements'), dict) else {}
        return {'knowledge_packages': requirements.get('knowledge_packages', []) if isinstance(requirements.get('knowledge_packages'), list) else [], 'knowledge_resources': requirements.get('knowledge_resources', []) if isinstance(requirements.get('knowledge_resources'), list) else [], 'resource_selection': requirements.get('resource_selection', {}) if isinstance(requirements.get('resource_selection'), dict) else {}, 'template_packages': requirements.get('template_packages', []) if isinstance(requirements.get('template_packages'), list) else [], 'templates': requirements.get('templates', []) if isinstance(requirements.get('templates'), list) else [], 'tools': requirements.get('tools', []) if isinstance(requirements.get('tools'), list) else [], 'platform_contracts': requirements.get('platform_contracts', []) if isinstance(requirements.get('platform_contracts'), list) else []}

    def satisfies(self, version: str, constraint: str) -> bool:
        text = (constraint or '').strip()
        if not text or text in {'*', 'latest'}:
            return True
        version_key = self.versions.key(version)
        if version_key[0] != 0:
            return version == text
        version_tuple = version_key[1]
        assert isinstance(version_tuple, tuple)
        for part in text.split():
            if part.startswith('>='):
                other = self.versions.key(part[2:])[1]
                if isinstance(other, tuple) and version_tuple < other:
                    return False
            elif part.startswith('>'):
                other = self.versions.key(part[1:])[1]
                if isinstance(other, tuple) and version_tuple <= other:
                    return False
            elif part.startswith('<='):
                other = self.versions.key(part[2:])[1]
                if isinstance(other, tuple) and version_tuple > other:
                    return False
            elif part.startswith('<'):
                other = self.versions.key(part[1:])[1]
                if isinstance(other, tuple) and version_tuple >= other:
                    return False
            elif part.startswith('^'):
                base = self.versions.key(part[1:])[1]
                if isinstance(base, tuple) and (version_tuple < base or version_tuple[0] != base[0]):
                    return False
            elif part == '||':
                continue
            elif version != part:
                return False
        return True

    def prefix(self, version: str) -> str:
        key = self.versions.key(version)
        if key[0] != 0 or not isinstance(key[1], tuple) or len(key[1]) < 2:
            return ''
        return f'{key[1][0]}.{key[1][1]}'

    def platform_versions(self, package_ids: list[str], selection: dict[str, Any]) -> list[str]:
        configured = selection.get('platform_versions') if isinstance(selection.get('platform_versions'), dict) else {}
        versions = [str(value).strip() for value in configured.values() if str(value).strip()]
        if versions:
            return sorted(set(versions))
        inferred: list[str] = []
        for package_id in package_ids:
            match = re.search('(?:^|[-_.])v?(\\d+)[-_.](\\d+)(?:$|[-_.])', package_id)
            if match:
                inferred.append(f'{match.group(1)}.{match.group(2)}')
        return sorted(set(inferred))

    def legacy_requirements(self, package_resources: list[dict[str, Any]], *, direct_package_ids: list[str], selection: dict[str, Any]) -> list[dict[str, Any]]:
        """Derive a narrow migration set for manifests created before selectors existed."""
        direct = set(direct_package_ids)
        target_versions = self.platform_versions(direct_package_ids, selection)
        requirements: list[dict[str, Any]] = []
        compatible: dict[str, dict[str, Any]] = {}
        for resource in package_resources:
            package_id = str(resource.get('package') or resource.get('package_id') or '')
            resource_id = str(resource.get('id') or resource.get('resource_id') or '')
            version = str(resource.get('version') or resource.get('generation') or '')
            if package_id in direct or package_id.startswith('project.'):
                requirements.append({'id': resource_id, 'preferred_version': version, 'required': True, 'selection_reason': 'legacy_direct_package'})
                continue
            if target_versions and self.prefix(version) in target_versions:
                logical_id = str(resource.get('resource_id') or resource_id)
                previous = compatible.get(logical_id)
                if previous is None or self.versions.key(version) > self.versions.key(str(previous.get('version') or previous.get('generation') or '')):
                    compatible[logical_id] = resource
        for resource in compatible.values():
            requirements.append({'id': str(resource.get('id') or resource.get('resource_id') or ''), 'preferred_version': str(resource.get('version') or resource.get('generation') or ''), 'required': True, 'selection_reason': 'legacy_compatible_version'})
        return requirements

    def select(self, package_resources: list[dict[str, Any]], requirements: dict[str, Any], *, direct_package_ids: list[str] | None=None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        resource_requirements = [item for item in requirements.get('knowledge_resources', []) if isinstance(item, dict)]
        selection = requirements.get('resource_selection') if isinstance(requirements.get('resource_selection'), dict) else {}
        if not resource_requirements:
            resource_requirements = self.legacy_requirements(package_resources, direct_package_ids=direct_package_ids or [], selection=selection)
            mode = 'legacy_narrow'
        else:
            mode = 'explicit'
        resolved: list[dict[str, Any]] = []
        used_keys: set[tuple[str, str]] = set()
        provenance: list[dict[str, Any]] = []
        for requirement in resource_requirements:
            resource_id = str(requirement.get('id') or '')
            candidates = [resource for resource in package_resources if resource_id in {str(resource.get('resource_id') or ''), str(resource.get('id') or '')}]
            preferred = str(requirement.get('preferred_version') or '')
            constraint = str(requirement.get('constraint') or '')
            if preferred:
                candidates = [resource for resource in candidates if str(resource.get('version') or '') == preferred]
            if constraint:
                candidates = [resource for resource in candidates if self.satisfies(str(resource.get('version') or ''), constraint)]
            candidates.sort(key=lambda resource: self.versions.key(str(resource.get('version') or self.snapshots.generation(resource) or '')))
            if candidates:
                selected = candidates[-1]
                selected = dict(selected)
                selected['requirement'] = 'required' if bool(requirement.get('required', True)) else 'recommended'
                instance = self.snapshots.instance(selected)
                key = (instance['id'], instance['instance_id'])
                if key not in used_keys:
                    instance['selection'] = {'mode': mode, 'reason': str(requirement.get('selection_reason') or 'explicit_selector'), 'preferred_version': preferred or None, 'constraint': constraint or None}
                    resolved.append(instance)
                    used_keys.add(key)
                provenance.append({'selector': {key: value for key, value in requirement.items() if key in {'id', 'preferred_version', 'constraint', 'required', 'selection_reason'}}, 'resource_id': instance['id'], 'instance_id': instance['instance_id'], 'status': 'selected'})
            else:
                provenance.append({'selector': {key: value for key, value in requirement.items() if key in {'id', 'preferred_version', 'constraint', 'required', 'selection_reason'}}, 'status': 'unresolved'})
        return (resolved, {'mode': mode, 'status': 'unresolved' if any((item.get('status') == 'unresolved' and item.get('selector', {}).get('required', True) is not False for item in provenance)) else 'resolved', 'target_versions': self.platform_versions(direct_package_ids or [], selection), 'selected_count': len(resolved), 'available_count': len(package_resources), 'provenance': provenance})
