"""Existing classification and resolved-resource comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from ..resources.versioning import ResourceVersionPolicy


@dataclass(frozen=True)
class ProjectSnapshotResolvedComparison:
    """Compare supplied snapshots without collection, access or publication."""
    versions: ResourceVersionPolicy = field(default_factory=ResourceVersionPolicy, kw_only=True, repr=False, compare=False)

    def _resource_key(self, resource: dict[str, Any]) -> tuple[str, str, str]:
        return (str(resource.get('package_id') or ''), str(resource.get('id') or ''), str(resource.get('instance_id') or ''))

    def _resource_indexes(self, current_snapshot: dict[str, Any]) -> tuple[dict[tuple[str, str, str], dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
        resolved = current_snapshot.get('resolved') if isinstance(current_snapshot.get('resolved'), dict) else {}
        resources = resolved.get('available_knowledge_resources') if isinstance(resolved.get('available_knowledge_resources'), list) else []
        if not resources:
            resources = resolved.get('knowledge_resources') if isinstance(resolved.get('knowledge_resources'), list) else []
        by_instance: dict[tuple[str, str, str], dict[str, Any]] = {}
        by_subject: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in resources:
            if not isinstance(item, dict):
                continue
            by_instance[self._resource_key(item)] = item
            by_subject.setdefault((str(item.get('package_id') or ''), str(item.get('id') or '')), []).append(item)
        return (by_instance, by_subject)

    def compare(self, snapshot: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        reasons: list[str] = []
        stale_resources: list[dict[str, Any]] = []
        updates_available: list[dict[str, Any]] = []
        broken_refs: list[dict[str, Any]] = []
        old_classification = snapshot.get('project_classification')
        current_classification = current.get('project_classification')
        if json.dumps(old_classification or {}, ensure_ascii=False, sort_keys=True) != json.dumps(current_classification or {}, ensure_ascii=False, sort_keys=True):
            reasons.append('project classification changed')
        old_resolved = snapshot.get('resolved') if isinstance(snapshot.get('resolved'), dict) else {}
        old_resources = old_resolved.get('knowledge_resources') if isinstance(old_resolved.get('knowledge_resources'), list) else []
        current_by_instance, current_by_subject = self._resource_indexes(current)
        for old in old_resources:
            if not isinstance(old, dict):
                continue
            mode = str(old.get('versioning_mode') or 'rolling_index')
            key = self._resource_key(old)
            subject_key = (key[0], key[1])
            current_same_subject = current_by_subject.get(subject_key, [])
            current_instance = current_by_instance.get(key)
            if mode == 'multi_version':
                if current_instance is None:
                    broken_refs.append({'id': old.get('id'), 'instance_id': old.get('instance_id'), 'reason': 'pinned multi_version resource instance missing'})
                    continue
                old_version = str(old.get('resolved_version') or '')
                for current_resource in current_same_subject:
                    current_version = str(current_resource.get('resolved_version') or '')
                    is_newer, _warning = self.versions.is_newer(current_version, old_version)
                    if is_newer:
                        updates_available.append({'id': old.get('id'), 'type': 'knowledge_resource', 'snapshot_version': old_version, 'available_version': current_version, 'snapshot_stale': False, 'reason': 'multi_version resource has newer version but pinned instance still exists'})
            else:
                current_resource = current_same_subject[-1] if current_same_subject else None
                if current_resource is None:
                    broken_refs.append({'id': old.get('id'), 'instance_id': old.get('instance_id'), 'reason': 'current resource missing'})
                    continue
                old_generation = str(old.get('resolved_generation') or old.get('fingerprint', {}).get('value') or '')
                current_generation = str(current_resource.get('resolved_generation') or current_resource.get('fingerprint', {}).get('value') or '')
                old_fingerprint = str(old.get('fingerprint', {}).get('value') or '')
                current_fingerprint = str(current_resource.get('fingerprint', {}).get('value') or '')
                if old_generation != current_generation or old_fingerprint != current_fingerprint:
                    stale_resources.append({'id': old.get('id'), 'snapshot_generation': old_generation, 'current_generation': current_generation, 'reason': f'{mode} resource generation changed'})
        return (reasons, stale_resources, updates_available, broken_refs)
