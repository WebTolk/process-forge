"""Existing Work completion request orchestration with deferred operation dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class CompletionWorkSelector(Protocol):
    def __call__(self, *, run_id: str, assignment_id: str, session_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None: ...


class CompletionStateReader(Protocol):
    def __call__(self, *, run_id: str, assignment_id: str, session_id: str) -> dict[str, Any]: ...


class CompletionReadinessReader(Protocol):
    def __call__(self, *, run_id: str, assignment_id: str, session_id: str) -> dict[str, Any]: ...


class CompletionIntentReader(Protocol):
    def __call__(self, run: dict[str, Any], assignment: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]: ...


class CompletionTransition(Protocol):
    def __call__(self, *, outcome: str, evidence: Any, notes: str, run_id: str, assignment_id: str, session_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True, kw_only=True)
class WorkCompletionRequestService:
    work_selector: Callable[[], CompletionWorkSelector] = field(repr=False, compare=False)
    blocked_result: Callable[[], Callable[[str], dict[str, Any]]] = field(repr=False, compare=False)
    process_reader: Callable[[], Callable[[dict[str, Any]], tuple[dict[str, Any], str]]] = field(repr=False, compare=False)
    outcomes_reader: Callable[[], Callable[[dict[str, Any], str], list[dict[str, Any]]]] = field(repr=False, compare=False)
    state_reader: Callable[[], CompletionStateReader] = field(repr=False, compare=False)
    run_blockers: Callable[[], Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], list[dict[str, Any]]]] = field(repr=False, compare=False)
    intent_reader: Callable[[], CompletionIntentReader] = field(repr=False, compare=False)
    completion_readiness: Callable[[], CompletionReadinessReader] = field(repr=False, compare=False)
    transition: Callable[[], CompletionTransition] = field(repr=False, compare=False)

    def can_complete(self, *, run_id: str='', assignment_id: str='', session_id: str='') -> dict[str, Any]:
        try:
            selected = self.work_selector()(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        except ValueError as exc:
            return {'can_complete': False, 'blockers': [{'code': str(exc)}]}
        if not selected:
            return {'can_complete': False, 'blockers': [{'code': 'active_work_not_found'}]}
        run, assignment = selected
        process, pin_status = self.process_reader()(run)
        stage_id = str(assignment.get('stage') or '')
        outcomes = self.outcomes_reader()(process, stage_id)
        final = any((not str(item.get('next_stage') or '') for item in outcomes))
        state = self.state_reader()(run_id=str(run.get('id') or ''), assignment_id=str(assignment.get('id') or ''), session_id=session_id)
        blockers = [*list(state.get('blockers') or []), *list(state.get('incomplete') or [])]
        if pin_status != 'pinned':
            blockers.append({'code': 'process_not_pinned'})
        if not final:
            blockers.append({'code': 'not_final_stage', 'stage_id': stage_id})
        blockers.extend(self.run_blockers()(process, run, assignment))
        return {'can_complete': not blockers, 'blockers': blockers, 'run': state.get('run'), 'assignment': state.get('assignment'), 'stage': state.get('stage')}

    def complete(self, *, outcome: str='completed', evidence: Any=None, notes: str='', run_id: str='', assignment_id: str='', session_id: str='') -> dict[str, Any]:
        try:
            selected = self.work_selector()(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        except ValueError as exc:
            return self.blocked_result()(str(exc))
        if selected:
            run, assignment = selected
            pending, _error = self.intent_reader()(run, assignment)
            if pending is not None:
                # A committed intent is authoritative; retain the original retry path.
                return self.transition()(outcome=outcome, evidence=evidence, notes=notes, run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        readiness = self.completion_readiness()(run_id=run_id, assignment_id=assignment_id, session_id=session_id)
        if readiness['blockers'] and (not evidence):
            return {'schema_version': 1, 'kind': 'pf.work.complete', 'action': 'blocked', **readiness}
        return self.transition()(outcome=outcome, evidence=evidence, notes=notes, run_id=run_id, assignment_id=assignment_id, session_id=session_id)
