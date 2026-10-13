"""Existing project context defaults, override merge and freshness action rules."""

from __future__ import annotations

from typing import Any


class ProjectContextPolicy:
    """Apply the existing context policy without I/O or retained document state."""


    def merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = value
        return result

    def build(self, manifest_data: dict[str, Any]) -> dict[str, Any]:
        coordination = manifest_data.get('coordination') if isinstance(manifest_data.get('coordination'), dict) else {}
        organized = str(coordination.get('mode') or 'inherit') == 'organized'
        policy = {'on_session_start': {'check_freshness': True, 'check_update_candidates': 'if_due', 'if_fresh': 'continue', 'if_fresh_with_updates': 'notify', 'if_stale': 'notify_director' if organized else 'ask_operator', 'if_broken': 'block'}, 'auto_refresh': {'enabled': False, 'allow_patch': True, 'allow_minor': False, 'allow_major': False, 'allow_rolling_resources': False}, 'active_run_behavior': {'existing_capsules': 'pin_existing', 'new_capsules': 'require_fresh_snapshot'}, 'organized_mode': {'stale_snapshot_action': 'notify_director' if organized else 'needs_operator'}}
        project_policy = manifest_data.get('context_policy') if isinstance(manifest_data.get('context_policy'), dict) else {}
        return self.merge(policy, project_policy)

    def action(self, status: str, policy: dict[str, Any]) -> str:
        session_policy = policy.get('on_session_start') if isinstance(policy.get('on_session_start'), dict) else {}
        if status == 'fresh':
            return str(session_policy.get('if_fresh') or 'continue')
        if status == 'fresh_with_updates':
            return str(session_policy.get('if_fresh_with_updates') or 'notify')
        if status == 'stale':
            return str(session_policy.get('if_stale') or 'ask_operator')
        if status == 'broken':
            return str(session_policy.get('if_broken') or 'block')
        return 'block'
