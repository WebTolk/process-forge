"""Existing hook outbox dispatch, result recording and runtime path resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from ..common.paths import rel
from ..project.metadata import PROJECT_FLOW_ROOT
from ..work.context_documents import ContextContractInputs
from .hook_policy import HookDispatchPolicy


@dataclass(frozen=True)
class RuntimeHookDispatcher:
    policy: HookDispatchPolicy = field(default_factory=HookDispatchPolicy)
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def hook_results_root(self, project_root: Path) -> Path:
        return self.inputs.locate_flow_root(project_root) / 'runtime' / 'hooks' / 'results'

    def resolve_runtime_config_path(self, project_root: Path, value: str | None, default: Path) -> Path:
        if not value:
            return default
        path = Path(value)
        if path.is_absolute():
            return path
        if path.parts and path.parts[0] == PROJECT_FLOW_ROOT:
            return project_root / path
        return self.inputs.locate_flow_root(project_root) / path

    def write_hook_result(self, project_root: Path, result: dict[str, Any]) -> Path:
        results_root = self.hook_results_root(project_root)
        results_root.mkdir(parents=True, exist_ok=True)
        target = results_root / f"{result['delivery_id']}.json"
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return target

    def dispatch_hooks(self, project_root: Path, event: dict[str, Any], *, dry_run: bool=False, outbox: bool=True) -> list[dict[str, Any]]:
        hooks_config, _all_hooks = self.policy.hook_targets(project_root)
        hooks = self.policy.selected_hooks(project_root, event)
        actions: list[dict[str, Any]] = []
        for hook in hooks:
            hook_id = safe_id(str(hook.get('id', 'hook')), 'hook')
            hook_type = str(hook.get('type', 'outbox'))
            delivery_id = 'del_' + hashlib.sha256((self.policy.event_id_value(event) + ':' + hook_id).encode('utf-8')).hexdigest()[:32]
            action: dict[str, Any] = {'hook': hook_id, 'target_id': hook_id, 'type': hook_type, 'delivery_id': delivery_id}
            if dry_run:
                action['status'] = 'dry_run'
                action['mode'] = 'dry_run'
            elif hook_type in {'outbox', 'file_outbox', 'webhook', 'webhook_future'} and outbox:
                default_outbox = self.inputs.locate_flow_root(project_root) / 'runtime' / 'hooks' / 'outbox'
                target_root = self.resolve_runtime_config_path(project_root, str(hook.get('path') or hook.get('outbox') or ''), default_outbox)
                if hook_id.startswith('wtaicc') and target_root.name != 'wtaicc':
                    target_root = target_root / 'wtaicc'
                target_root.mkdir(parents=True, exist_ok=True)
                delivery = self.policy.hook_delivery_payload(event, hook, 'outbox', delivery_id)
                payload = self.policy.wtaicc_outbox_payload(event) if hook_id.startswith('wtaicc') else delivery
                target = target_root / f'{self.policy.event_id_value(event)}.{hook_id}.json'
                target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
                action['status'] = 'outbox_written'
                action['outbox'] = rel(target, project_root)
                result = {'schema_version': 1, 'delivery_id': delivery_id, 'target_id': hook_id, 'status': 'written', 'exit_code': 0, 'blocking': False, 'message': 'Outbox payload written', 'outbox': rel(target, project_root)}
                action['result'] = rel(self.write_hook_result(project_root, result), project_root)
            elif hook_type == 'command':
                action['status'] = 'skipped'
                action['reason'] = 'command hooks require an explicit future runner/executor'
                result = {'schema_version': 1, 'delivery_id': delivery_id, 'target_id': hook_id, 'status': 'skipped', 'exit_code': 0, 'blocking': bool(hook.get('blocking', False)), 'message': action['reason']}
                action['result'] = rel(self.write_hook_result(project_root, result), project_root)
            elif hook_type == 'webhook' and (not hooks_config.get('network_send_enabled', False)):
                action['status'] = 'skipped'
                action['reason'] = 'network send is disabled by default'
            else:
                action['status'] = 'skipped'
                action['reason'] = f'unsupported hook type: {hook_type}'
            actions.append(action)
        return actions
