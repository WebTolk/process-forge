"""Read the historical capture of one completed attempt, without accepting it anew."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml

from ..common.ids import safe_id
from ..common.request_scope import safe_load
from ..project.metadata import ProjectMetadataReader
from ..work.context import fingerprint
from .input import bounded_read, digest, local_file, private_file


@dataclass(frozen=True)
class CapturedAttempt:
    attempt: int
    receipt_id: str


@dataclass(frozen=True)
class CapturedAttemptReader:
    project_root: Path

    def read(self, task: dict[str, Any], state: dict[str, Any], *, run_id: str) -> CapturedAttempt | None:
        """Return only a historical fact; unavailable proof requires ordinary collection.

        The caller holds the attempt lifecycle lock. Sources, output bodies,
        current resource access and lifecycle acceptance are deliberately absent.
        All metadata is read again on each call; there is no status/mtime cache.
        """
        try:
            return self._read(task, state, run_id=run_id)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, MemoryError, yaml.YAMLError):
            return None

    def _read(self, task: dict[str, Any], state: dict[str, Any], *, run_id: str) -> CapturedAttempt | None:
        project = self.project_root.resolve()
        task_id = task['id']
        if (not isinstance(task_id, str) or safe_id(task_id, 'task') != task_id
                or not isinstance(run_id, str) or safe_id(run_id, 'run') != run_id
                or task.get('run_id') != run_id or state.get('run_id') != run_id
                or state.get('task_id') != task_id or state.get('status') != 'completed'):
            return None
        attempt = state.get('attempt')
        if isinstance(attempt, str) and attempt.isdigit():
            attempt = int(attempt)
        if type(attempt) is not int or attempt < 1:
            return None
        directory = f'.pf/runtime/agent-runs/{run_id}/{task_id}/attempts/{attempt}'
        completion = json.loads(bounded_read(private_file(project, directory + '/collection-complete.json')))
        receipt = json.loads(bounded_read(private_file(project, directory + '/collection-receipt.json')))
        receipt_id = receipt.get('receipt_id')
        if (receipt.get('schema_version') != 1 or not isinstance(receipt_id, str)
                or receipt_id != fingerprint({k: v for k, v in receipt.items() if k != 'receipt_id'})
                or completion != {'schema_version': 1, 'receipt_id': receipt_id}):
            return None
        reference = state.get('prepared_input')
        if (not isinstance(reference, dict) or reference.get('path') != directory + '/prepared-input.json'
                or receipt.get('prepared_input') != reference):
            return None
        raw = bounded_read(private_file(project, reference['path']))
        if digest(raw) != reference.get('checksum'):
            return None
        prepared = json.loads(raw)
        identity = prepared.get('identity')
        inputs = prepared.get('input')
        if (prepared.get('schema_version') != 1 or prepared.get('kind') != 'pf.prepared-input'
                or prepared.get('project_root') != str(project) or not isinstance(identity, dict)
                or not isinstance(inputs, dict) or prepared.get('input_fingerprint') != fingerprint(inputs)
                or identity.get('project_id') != ProjectMetadataReader(project).project_id()
                or identity.get('run_id') != run_id or identity.get('assignment_id') != task_id
                or identity.get('attempt') != attempt or receipt.get('identity') != identity
                or inputs.get('identity') != {k: v for k, v in identity.items() if k != 'attempt'}):
            return None
        relative = f'.pf/contexts/assignment-capsules/{task_id}.capsule.yaml'
        capsule_raw = bounded_read(local_file(project, relative))
        capsule_pin = inputs['capsule']
        if (capsule_pin.get('path') != relative or capsule_pin.get('checksum') != digest(capsule_raw)
                or state.get('capsule_path') != relative):
            return None
        if 'process_execution' in task:
            pin = task['process_execution']
            if pin.get('assignment_capsule') != relative or pin.get('assignment_capsule_checksum') != capsule_pin['checksum']:
                return None
        capsule = safe_load(capsule_raw.decode('utf-8-sig'))
        contract = capsule['execution_contract']
        if (identity != {**contract['identity'], 'attempt': attempt}
                or identity.get('context_id') != capsule['capsule']['id']
                or capsule_pin.get('contract_checksum') != contract['contract_checksum']
                or capsule_pin.get('intent_checksum') != contract['assignment_intent_checksum']
                or contract['contract_checksum'] != fingerprint({k: v for k, v in contract.items() if k != 'contract_checksum'})
                or contract['assignment_intent_checksum'] != fingerprint(contract['assignment_intent'])):
            return None
        report = inputs['outputs']['expected_report']['artifact']
        if (not isinstance(receipt.get('outputs'), list) or not any(
                item.get('path') == report and item.get('status') == 'present'
                and isinstance(item.get('checksum'), str) and item['checksum'].startswith('sha256:')
                for item in receipt['outputs'])):
            return None
        return CapturedAttempt(attempt=attempt, receipt_id=receipt_id)
