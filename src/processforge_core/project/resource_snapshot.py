"""Pure resource versioning, snapshot and indexing rules."""

import copy
import hashlib
import json
from typing import Any

RESOURCE_VERSIONING_MODES = {'multi_version', 'single_current', 'rolling_index', 'external_live'}
RESOURCE_RETENTION_POLICIES = {'keep_versions', 'keep_last_n', 'replace_in_place', 'external_only'}


class ResourceSnapshotRules:
    """Existing resource algorithms, without document I/O or retained state."""

    def versioning_policy(
        self, resource: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        versioning = resource.get('versioning') if isinstance(resource.get('versioning'), dict) else {}
        mode = str(versioning.get('mode') or ('multi_version' if resource.get('version') else 'rolling_index'))
        if mode not in RESOURCE_VERSIONING_MODES:
            mode = 'rolling_index'
        versioning = {
            'mode': mode,
            'version_field': str(versioning.get('version_field') or 'version'),
            'instance_id_template': str(versioning.get('instance_id_template') or '{id}@{version}'),
        }
        retention = resource.get('retention') if isinstance(resource.get('retention'), dict) else {}
        default_retention = (
            'keep_versions' if mode == 'multi_version'
            else 'external_only' if mode == 'external_live' else 'replace_in_place'
        )
        policy = str(retention.get('policy') or default_retention)
        if policy not in RESOURCE_RETENTION_POLICIES:
            policy = default_retention
        retention = {'policy': policy, 'keep_last_n': retention.get('keep_last_n')}
        behavior = resource.get('snapshot_behavior') if isinstance(resource.get('snapshot_behavior'), dict) else {}
        reproducibility = (
            'exact' if mode == 'multi_version' and policy == 'keep_versions'
            else 'non_reproducible' if mode == 'external_live' else 'best_effort'
        )
        snapshot_behavior = {
            'on_new_version': str(
                behavior.get('on_new_version') or ('notify_only' if mode == 'multi_version' else 'mark_stale')
            ),
            'on_current_generation_changed': str(
                behavior.get('on_current_generation_changed')
                or ('notify_only' if mode == 'multi_version' else 'mark_stale')
            ),
            'on_instance_missing': str(behavior.get('on_instance_missing') or 'broken'),
            'reproducibility': str(behavior.get('reproducibility') or reproducibility),
        }
        return (versioning, retention, snapshot_behavior)

    def declared_version(self, resource: dict[str, Any], versioning: dict[str, Any]) -> str:
        field = str(versioning.get('version_field') or 'version')
        value = resource.get(field)
        if value is None:
            value = resource.get('version') or resource.get('resolved_version')
        return str(value or '')

    def generation(self, resource: dict[str, Any]) -> str:
        for key in ['generation', 'resolved_generation', 'updated_at', 'generated_at']:
            if resource.get(key) is not None:
                return str(resource.get(key))
        fingerprint = resource.get('fingerprint') if isinstance(resource.get('fingerprint'), dict) else {}
        if fingerprint.get('value'):
            return str(fingerprint.get('value'))
        return ''

    def fingerprint(
        self, resource: dict[str, Any], versioning: dict[str, Any], generation: str,
    ) -> dict[str, str]:
        fingerprint = resource.get('fingerprint') if isinstance(resource.get('fingerprint'), dict) else {}
        if fingerprint.get('value'):
            value = str(fingerprint.get('value'))
            return {
                'type': str(fingerprint.get('type') or 'declared'),
                'value': value if value.startswith('sha256:') else 'sha256:' + value,
            }
        stable = {
            'id': resource.get('id'),
            'kind': resource.get('kind'),
            'version': self.declared_version(resource, versioning),
            'generation': generation,
            'path_ref': resource.get('path_ref'),
        }
        return {
            'type': 'resource_record_sha256',
            'value': 'sha256:' + hashlib.sha256(
                json.dumps(stable, sort_keys=True, ensure_ascii=False).encode('utf-8')
            ).hexdigest(),
        }

    def instance_id(
        self, resource: dict[str, Any], versioning: dict[str, Any], version: str, generation: str,
    ) -> str:
        explicit = resource.get('instance_id')
        if isinstance(explicit, str) and explicit.strip():
            return explicit
        template = str(versioning.get('instance_id_template') or '{id}@{version}')
        token_value = version or generation or 'current'
        try:
            return template.format(id=resource.get('id'), version=token_value, generation=generation or token_value)
        except (KeyError, ValueError):
            return f"{resource.get('id')}@{token_value}"

    def instance(self, resource: dict[str, Any]) -> dict[str, Any]:
        versioning, retention, behavior = self.versioning_policy(resource)
        public_id = str(resource.get('id') or resource.get('resource_id') or '')
        version = self.declared_version(resource, versioning)
        generation = self.generation(resource)
        fingerprint = self.fingerprint(resource, versioning, generation)
        reproducibility = str(behavior.get('reproducibility') or 'best_effort')
        result: dict[str, Any] = {
            'id': public_id,
            'kind': str(resource.get('kind') or 'reference'),
            'package_id': str(resource.get('package') or resource.get('package_id') or ''),
            'requirement': str(resource.get('requirement') or 'recommended'),
            'versioning_mode': versioning['mode'],
            'retention_policy': retention['policy'],
            'instance_id': self.instance_id({**resource, 'id': public_id}, versioning, version, generation),
            'path_ref': resource.get('path_ref'),
            'fingerprint': fingerprint,
            'reproducibility': {'level': reproducibility},
            'snapshot_behavior': behavior,
        }
        if version:
            result['resolved_version'] = version
        if generation:
            result['resolved_generation'] = generation
            result['current_marker_path_ref'] = resource.get('current_marker_path_ref') or resource.get('path_ref')
        if reproducibility != 'exact':
            result['reproducibility']['reason'] = f"resource retention policy is {retention['policy']}"
        for key in ('resource_id', 'title', 'description', 'load_policy', 'index_policy', 'indexing', 'selection'):
            if key in resource:
                result[key] = copy.deepcopy(resource[key])
        return result

    def indexing(self, resource: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
        indexing = resource.get('indexing') if isinstance(resource.get('indexing'), dict) else {}
        if indexing:
            return copy.deepcopy(indexing)
        if (
            str(selection.get('mode') or '') == 'legacy_narrow'
            and str(resource.get('kind') or '') == 'documentation'
        ):
            return {
                'enabled': True,
                'mode': 'fulltext',
                'fields': ['title', 'description', 'version', 'path'],
                'sources': [{
                    'path': '.',
                    'mode': 'fulltext',
                    'include': ['**/*.md', '**/*.txt', '**/*.rst'],
                    'role': 'documentation',
                }],
                'migration': 'legacy_documentation_fulltext',
            }
        return {
            'enabled': True,
            'mode': 'metadata',
            'fields': ['title', 'description', 'version', 'path'],
            'sources': [{
                'path': '.',
                'mode': 'metadata',
                'role': str(resource.get('kind') or 'knowledge'),
            }],
        }

    def reproducibility(self, resources: list[dict[str, Any]]) -> dict[str, Any]:
        levels = [
            str(item.get('reproducibility', {}).get('level', 'best_effort'))
            for item in resources if isinstance(item, dict)
        ]
        reasons = sorted({
            str(item.get('reproducibility', {}).get('reason'))
            for item in resources if isinstance(item, dict) and item.get('reproducibility', {}).get('reason')
        })
        if not levels or all((level == 'exact' for level in levels)):
            level = 'exact'
        elif any((level == 'non_reproducible' for level in levels)):
            level = 'non_reproducible'
        elif any((level == 'best_effort' for level in levels)):
            level = 'best_effort'
        else:
            level = 'mixed'
        return {'level': level, 'reasons': reasons}
