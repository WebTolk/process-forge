"""Existing stage readiness rules with explicit material and definition callbacks."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class StageReadinessPolicy:
    file_diagnostic: Callable[[dict[str, Any] | None], dict[str, Any] | None]
    string_list: Callable[[Any], list[str]]
    stage_definitions: Callable[[dict[str, Any]], list[dict[str, Any]]]
    blocker_callback: Callable[[str, str, dict[str, Any]], dict[str, Any]]

    def requirement(self, kind: str, identifier: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        aliases = {'artifact': ('artifact_id', 'id'), 'input': ('input_id', 'artifact_id', 'id'), 'evidence': ('evidence_id', 'id')}
        accepted_kinds = {'artifact': {'artifact'}, 'input': {'input', 'artifact'}, 'evidence': {'evidence', 'attestation'}}
        statuses = {'ready', 'present', 'passed', 'approved', 'not_applicable'}
        match = next((item for item in reversed(evidence) if str(item.get('kind') or '') in accepted_kinds[kind] and any((str(item.get(key) or '') == identifier for key in aliases[kind]))), None)
        if match is None:
            return {'id': identifier, 'kind': kind, 'satisfied': False, 'evidence': {}}
        diagnostic = self.file_diagnostic(match)
        status = str(match.get('status') or '')
        if diagnostic is None and status not in statuses:
            diagnostic = {'code': 'evidence_status_not_acceptable', 'status': status or 'missing', 'id': identifier}
        result = {'id': identifier, 'kind': kind, 'satisfied': diagnostic is None, 'evidence': copy.deepcopy(match)}
        if diagnostic is not None:
            result['diagnostic'] = diagnostic
        return result

    def gate(self, process: dict[str, Any], gate_id: str, evidence: list[dict[str, Any]], *, phase: str) -> dict[str, Any]:
        definitions = process.get('gates') if isinstance(process.get('gates'), list) else []
        definition = next((item for item in definitions if isinstance(item, dict) and str(item.get('id') or '') == gate_id), {})
        match = next((item for item in reversed(evidence) if str(item.get('kind') or '') == 'gate' and str(item.get('gate_id') or item.get('id') or '') == gate_id), None)
        diagnostic = self.file_diagnostic(match) if match is not None else None
        if diagnostic is None and match is not None and (str(match.get('status') or '') not in {'passed', 'approved', 'not_applicable'}):
            diagnostic = {'code': 'evidence_status_not_acceptable', 'status': str(match.get('status') or 'missing'), 'id': gate_id}
        result = {'id': gate_id, 'phase': phase, 'type': str(definition.get('type') or 'checklist'), 'blocking': bool(definition.get('blocking', True)), 'required': bool(definition.get('required', True)), 'satisfied': match is not None and diagnostic is None, 'evidence': copy.deepcopy(match) if match is not None else {}}
        if diagnostic is not None:
            result['diagnostic'] = diagnostic
        return result

    def required_artifact_ids(self, process: dict[str, Any], stage: dict[str, Any]) -> list[str]:
        declared = self.string_list(stage.get('required_artifacts'))
        if declared:
            return declared
        definitions = process.get('artifact_definitions') if isinstance(process.get('artifact_definitions'), list) else []
        optional = {str(item.get('id')) for item in definitions if isinstance(item, dict) and item.get('required') is False}
        consumed_inputs = {artifact_id for candidate in self.stage_definitions(process) for artifact_id in self.string_list(candidate.get('required_inputs'))}
        return [item for item in self.string_list(stage.get('produced_artifacts')) if item not in optional or item in consumed_inputs]

    def requirements(self, inputs: list[dict[str, Any]], artifacts: list[dict[str, Any]], required_evidence: list[dict[str, Any]], gates: list[dict[str, Any]], obligations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        requirements: list[dict[str, Any]] = []
        requirements.extend((self.blocker_callback('required_input_missing', 'input_id', item) for item in inputs if not item['satisfied']))
        requirements.extend((self.blocker_callback('artifact_evidence_missing', 'artifact_id', item) for item in artifacts if not item['satisfied']))
        requirements.extend((self.blocker_callback('required_evidence_missing', 'evidence_id', item) for item in required_evidence if not item['satisfied']))
        requirements.extend((self.blocker_callback('gate_evidence_missing', 'gate_id', item) for item in gates if item['required'] and item['blocking'] and (not item['satisfied'])))
        requirements.extend(({'code': 'automation_not_ready', 'obligation_id': item['id'], 'status': item['status']} for item in obligations if item['status'] != 'ready'))
        return requirements

    def blocker(self, code: str, identifier_key: str, requirement: dict[str, Any]) -> dict[str, Any]:
        blocker = {'code': code, identifier_key: requirement['id']}
        diagnostic = requirement.get('diagnostic')
        if isinstance(diagnostic, dict):
            blocker['diagnostic'] = copy.deepcopy(diagnostic)
        return blocker
