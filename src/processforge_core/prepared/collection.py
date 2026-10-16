"""Observe capture or unresolved semantic refusal without accepting inputs anew."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

import yaml

from ..common.ids import safe_id
from ..common.request_scope import safe_load
from ..project.metadata import ProjectMetadataReader
from ..work.context import fingerprint
from .input import bounded_read, digest, encoded, local_file, private_file, load, semantic_input, write_once


_STABLE_REFUSALS = frozenset({
    'prepared_input_changed', 'prepared_input_context_mismatch',
    'required_source_changed', 'work_context_mismatch',
})
_REFUSAL_ORIGINS = {
    load.__code__: frozenset({'prepared_input_changed', 'prepared_input_context_mismatch'}),
    semantic_input.__code__: frozenset({'required_source_changed', 'work_context_mismatch'}),
}


def collection_refusal_reason(error: BaseException) -> str | None:
    """Map existing semantic errors, never unrelated errors with the same text."""
    if type(error) is not ValueError or len(error.args) != 1 or type(error.args[0]) is not str:
        return None
    trace = error.__traceback__
    if trace is None:
        return None
    while trace.tb_next is not None:
        trace = trace.tb_next
    return error.args[0] if error.args[0] in _REFUSAL_ORIGINS.get(trace.tb_frame.f_code, ()) else None


@dataclass(frozen=True)
class _PreparedAttempt:
    attempt: int
    directory: str
    identity: dict[str, Any]
    inputs: dict[str, Any]
    reference: dict[str, Any]
    input_fingerprint: str


def _attempt_location(task: dict[str, Any], state: dict[str, Any], run_id: str) -> tuple[int, str] | None:
    task_id = task['id']
    if (not isinstance(task_id, str) or safe_id(task_id, 'task') != task_id
            or not isinstance(run_id, str) or safe_id(run_id, 'run') != run_id
            or task.get('run_id') != run_id or state.get('run_id') != run_id
            or state.get('task_id') != task_id):
        return None
    attempt = state.get('attempt')
    if isinstance(attempt, str) and attempt.isdigit():
        attempt = int(attempt)
    if type(attempt) is not int or attempt < 1:
        return None
    directory = f'.pf/runtime/agent-runs/{run_id}/{task_id}/attempts/{attempt}'
    return attempt, directory


def _prepared_attempt(project: Path, task: dict[str, Any], state: dict[str, Any], run_id: str) -> _PreparedAttempt | None:
    """Read only current metadata identifying an existing prepared attempt."""
    location = _attempt_location(task, state, run_id)
    if location is None:
        return None
    attempt, directory = location
    task_id = task['id']
    reference = state.get('prepared_input')
    if not isinstance(reference, dict) or reference.get('path') != directory + '/prepared-input.json':
        return None
    raw = bounded_read(private_file(project, reference['path']))
    if digest(raw) != reference.get('checksum'):
        return None
    prepared = json.loads(raw)
    identity, inputs = prepared.get('identity'), prepared.get('input')
    if (type(prepared.get('schema_version')) is not int or prepared['schema_version'] != 1
            or prepared.get('kind') != 'pf.prepared-input'
            or prepared.get('project_root') != str(project) or not isinstance(identity, dict)
            or not isinstance(inputs, dict) or prepared.get('input_fingerprint') != fingerprint(inputs)
            or identity.get('project_id') != ProjectMetadataReader(project).project_id()
            or identity.get('run_id') != run_id or identity.get('assignment_id') != task_id
            or type(identity.get('attempt')) is not int or identity['attempt'] != attempt
            or inputs.get('identity') != {k: v for k, v in identity.items() if k != 'attempt'}):
        return None
    return _PreparedAttempt(attempt, directory, identity, inputs, reference, prepared['input_fingerprint'])


@dataclass(frozen=True)
class CollectionRecoveryRequired:
    attempt: int
    reason: str


@dataclass(frozen=True)
class CollectionRecoveryStore:
    """Historical semantic refusal, never current acceptance or access proof.

    The caller holds the same attempt lifecycle lock as prepare/collect. A
    successful capture supersedes this immutable observation; a new attempt has
    its own path. Failed manual recovery does not prove the old refusal resolved.
    """

    project_root: Path

    def _metadata(self, task: dict[str, Any], state: dict[str, Any], run_id: str) -> tuple[Path, dict[str, Any]] | None:
        if state.get('status') not in {'completed', 'manual_required'}:
            return None
        project = self.project_root.resolve()
        prepared = _prepared_attempt(project, task, state, run_id)
        if prepared is None:
            return None
        context_id = prepared.identity.get('context_id')
        if not isinstance(context_id, str) or safe_id(context_id, 'context') != context_id:
            return None
        relative = f'.pf/contexts/assignment-capsules/{task["id"]}.capsule.yaml'
        pin = prepared.inputs['capsule']
        if pin.get('path') != relative or state.get('capsule_path') != relative:
            return None
        if any(not isinstance(pin.get(key), str) or re.fullmatch(r'sha256:[0-9a-f]{64}', pin[key]) is None
               for key in ('checksum', 'contract_checksum', 'intent_checksum')):
            return None
        if 'process_execution' in task:
            current = task['process_execution']
            if (current.get('assignment_capsule') != relative
                    or current.get('assignment_capsule_checksum') != pin.get('checksum')):
                return None
        document = {'schema_version': 1, 'kind': 'pf.collection-recovery-required',
                    'identity': prepared.identity, 'prepared_input': prepared.reference,
                    'input_fingerprint': prepared.input_fingerprint}
        progress = {}
        for name in ('collection-receipt.json', 'collection-complete.json'):
            candidate = private_file(project, prepared.directory + '/' + name)
            try:
                candidate.stat()
            except FileNotFoundError:
                progress[name] = None
            else:
                progress[name] = digest(bounded_read(candidate))
        document['capture_progress'] = progress
        # Route by progress, then verify the complete document. The short key is
        # not authority: a collision is a miss, never permission to skip checks.
        name = 'collect-block-' + fingerprint(progress).removeprefix('sha256:')[:16] + '.json'
        path = private_file(project, prepared.directory + '/' + name)
        return path, document

    @staticmethod
    def _document(metadata: dict[str, Any], reason: str) -> dict[str, Any]:
        document = dict(metadata, reason=reason)
        document['fingerprint'] = fingerprint(document)
        return document

    def read(self, task: dict[str, Any], state: dict[str, Any], *, run_id: str) -> CollectionRecoveryRequired | None:
        try:
            metadata = self._metadata(task, state, run_id)
            if metadata is None:
                return None
            path, expected = metadata
            observed = json.loads(bounded_read(path, 32 * 1024))
            reason = observed.get('reason')
            if not isinstance(reason, str) or reason not in _STABLE_REFUSALS:
                return None
            identity = observed.get('identity')
            if not isinstance(identity, dict) or type(identity.get('attempt')) is not int:
                return None
            if observed.get('fingerprint') != fingerprint({k: v for k, v in observed.items() if k != 'fingerprint'}):
                return None
            if observed != self._document(expected, reason):
                return None
            return CollectionRecoveryRequired(expected['identity']['attempt'], reason)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, MemoryError, yaml.YAMLError):
            return None

    def record(self, task: dict[str, Any], state: dict[str, Any], *, run_id: str, error: BaseException) -> bool:
        reason = collection_refusal_reason(error)
        if reason is None:
            return False
        try:
            # A refused fresh manual check of a previously captured result is
            # not an outstanding automatic collection. Preserve that distinction.
            if CapturedAttemptReader(self.project_root).read(task, state, run_id=run_id) is not None:
                return False
            expected = self._metadata(task, state, run_id)
            if expected is None:
                return False
            path, metadata = expected
            document = self._document(metadata, reason)
            if len(encoded(document)) > 32 * 1024:
                return False
            if path.exists():
                # Retain the first valid refusal; never overwrite corrupt proof.
                return self.read(task, state, run_id=run_id) is not None
            write_once(path, document)
            return True
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, MemoryError, yaml.YAMLError):
            return False


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
        if state.get('status') != 'completed':
            return None
        location = _attempt_location(task, state, run_id)
        if location is None:
            return None
        attempt, directory = location
        task_id = task['id']
        completion = json.loads(bounded_read(private_file(project, directory + '/collection-complete.json')))
        receipt = json.loads(bounded_read(private_file(project, directory + '/collection-receipt.json')))
        receipt_id = receipt.get('receipt_id')
        if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
                or type(completion.get('schema_version')) is not int or not isinstance(receipt_id, str)
                or receipt_id != fingerprint({k: v for k, v in receipt.items() if k != 'receipt_id'})
                or completion != {'schema_version': 1, 'receipt_id': receipt_id}):
            return None
        prepared = _prepared_attempt(project, task, state, run_id)
        if prepared is None:
            return None
        if receipt.get('prepared_input') != prepared.reference:
            return None
        identity, inputs = prepared.identity, prepared.inputs
        receipt_identity = receipt.get('identity')
        if (not isinstance(receipt_identity, dict) or type(receipt_identity.get('attempt')) is not int
                or receipt_identity != identity):
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
