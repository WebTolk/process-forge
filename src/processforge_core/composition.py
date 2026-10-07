"""Internal, explicit service composition; construction performs no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

from .garage import CurrentWorkService
from .ports import ProcessDefinitionReadPort, ProjectSnapshotReadPort, WorkContextReadPort, WorkReadCorePort, WorkRecordReadPort
from .work.records import YamlWorkRecordReader

if TYPE_CHECKING:
    from .work.transition_commit import WorkTransitionCommitService
    from .completion_intent_replay import CompletionIntentReplayService
    from .completion_intent_read import CompletionIntentReadService
    from .completion_intent_builder import CompletionIntentBuilder
    from .completion_documents import CompletionDocumentService
    from .work.boundary_advisory import WorkBoundaryAdvisoryService
    from .transition_rejection import TransitionRejectionPolicy
    from .completion_intent_validation import CompletionIntentValidationService
    from .run_completion import RunCompletionPolicy
    from .process_pin import ProcessPinReadService
    from .process_selection import ProcessSelectionService, ResolvedDefinitionView
    from .work.selection import WorkSelectionService
    from .stage_readiness import StageReadinessPolicy
    from .automation_readiness import AutomationReadinessService
    from .evidence_validation import EvidenceValidationService
    from .garage import ProjectContextService
    from .garage import ResourceSearchService
    from .garage import ResourceResolveService
    from .garage import GarageModeService
    from .diagnostics import Logger
    from .process_execution import ProcessExecutionService
    from .process_definition_read import ProcessDefinitionReadService
    from .project_snapshot_read import ProjectSnapshotReadService
    from .work.context_read import WorkContextReadService

__all__ = ()


@dataclass(frozen=True)
class LegacyWorkReadAdapter:
    core: ModuleType

    def locate_flow_root(self, project_root: Path) -> Path:
        return self.core.locate_flow_root(project_root)

    def load_yaml_document(self, path: Path) -> dict[str, Any]:
        return self.core.load_yaml_document(path)


def build_current_work_service(project_root: Path, core: WorkReadCorePort) -> CurrentWorkService:
    return CurrentWorkService(project_root, core)


@dataclass(frozen=True)
class LegacyWorkContextAdapter:
    project_root: Path
    core: Any

    def validate_contract(self, path: Path, assignment: dict[str, Any], capsule: dict[str, Any]) -> dict[str, Any]:
        from .work.context import validate_execution_contract

        return validate_execution_contract(self.project_root, path, assignment, capsule, self.core, check_sources=False)

    def normalize_assignment(self, path: Path, assignment: dict[str, Any]) -> dict[str, Any]:
        from .work.context import normalized_assignment_contract

        return normalized_assignment_contract(self.project_root, path, assignment, self.core)


def build_work_context_read_service(
    project_root: Path, core: Any, *, flow_root: Callable[[], Path], assignment_path: Callable[[str], Path],
) -> WorkContextReadService:
    from .work.context_read import WorkContextReadService

    adapter = LegacyWorkContextAdapter(project_root, core)
    return WorkContextReadService(flow_root, assignment_path, adapter.validate_contract, adapter.normalize_assignment)


@dataclass(frozen=True)
class LegacyProcessDefinitionAdapter:
    project_root: Path
    core: Any

    def resolve_definition(self, process_id: str) -> dict[str, Any]:
        return self.core.resolve_process_definition(self.project_root, process_id).process


def build_process_definition_read_service(
    project_root: Path, core: Any, *, fingerprint: Callable[[dict[str, Any]], str],
) -> ProcessDefinitionReadService:
    from .process_definition_read import ProcessDefinitionReadService

    adapter = LegacyProcessDefinitionAdapter(project_root, core)
    return ProcessDefinitionReadService(adapter.resolve_definition, fingerprint)


@dataclass(frozen=True)
class LegacyProjectSnapshotAdapter:
    core: Any

    def load_document(self, path: Path) -> dict[str, Any]:
        return self.core.load_yaml_document(path)


def build_project_snapshot_read_service(
    core: Any, *, snapshot_path: Callable[[], Path], sha256_file: Callable[[Path], str],
) -> ProjectSnapshotReadService:
    from .project_snapshot_read import ProjectSnapshotReadService

    adapter = LegacyProjectSnapshotAdapter(core)
    return ProjectSnapshotReadService(snapshot_path, adapter.load_document, sha256_file)


def build_project_context_snapshot_read_service(project_root: Path, core: Any) -> ProjectSnapshotReadService:
    def snapshot_path() -> Path:
        path, _snapshot_md = core.project_context_snapshot_paths(project_root)
        return path

    return build_project_snapshot_read_service(
        core, snapshot_path=snapshot_path, sha256_file=lambda path: core.sha256_file(path),
    )


def build_project_context_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ProjectContextService:
    from .garage import ProjectContextService

    return ProjectContextService(project_root, workplace_root, core, snapshots=snapshots)


def build_resource_search_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceSearchService:
    from .garage import ResourceSearchService

    return ResourceSearchService(project_root, workplace_root, core, snapshots=snapshots)


def build_resource_resolve_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceResolveService:
    from .garage import ResourceResolveService

    return ResourceResolveService(project_root, workplace_root, core, snapshots=snapshots)


def build_garage_mode_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> GarageModeService:
    from .garage import GarageModeService

    if snapshots is None:
        return GarageModeService(project_root, workplace_root, core)
    return GarageModeService(project_root, workplace_root, core, snapshots=snapshots)


def build_process_execution_service(
    project_root: Path, workplace_root: Path | None, core: Any, *, observer: Logger | None = None,
    records: WorkRecordReadPort | None = None,
    context: WorkContextReadPort | None = None,
    definitions: ProcessDefinitionReadPort | None = None,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> ProcessExecutionService:
    from .process_execution import ProcessExecutionService

    if records is None:
        records = YamlWorkRecordReader(project_root, core)
    return ProcessExecutionService(project_root, workplace_root, core, observer=observer, records=records, context=context, definitions=definitions, snapshots=snapshots)


def build_evidence_validation_service(
    project_root: Path | Callable[[], Path], *, now_utc: Callable[[], str], relative_path: Callable[[Path], str],
    sha256_file: Callable[[Path], str], path_resolver: Callable[[str], Path | None] | None = None,
) -> EvidenceValidationService:
    from .evidence_validation import EvidenceValidationService

    return EvidenceValidationService(project_root, now_utc, relative_path, sha256_file, path_resolver)


def build_stage_readiness_policy(
    *, file_diagnostic: Callable[[dict[str, Any] | None], dict[str, Any] | None],
    string_list: Callable[[Any], list[str]],
    stage_definitions: Callable[[dict[str, Any]], list[dict[str, Any]]],
    blocker_callback: Callable[[str, str, dict[str, Any]], dict[str, Any]],
) -> StageReadinessPolicy:
    from .stage_readiness import StageReadinessPolicy

    return StageReadinessPolicy(file_diagnostic, string_list, stage_definitions, blocker_callback)


def build_automation_readiness_service(
    *, project_root: Path,
    has_output_checks: Callable[[], bool],
    output_checks: Callable[[Path, dict[str, Any]], Any],
    has_fingerprint: Callable[[], bool],
    fingerprint: Callable[[Path, dict[str, Any]], Any],
    has_event_paths: Callable[[], bool],
    event_paths: Callable[[Path], tuple[Path, Any]],
    latest_event: Callable[[str, set[str]], dict[str, Any] | None]
) -> AutomationReadinessService:
    from .automation_readiness import AutomationReadinessService

    return AutomationReadinessService(
        project_root=project_root, has_output_checks=has_output_checks, output_checks=output_checks, has_fingerprint=has_fingerprint, fingerprint=fingerprint, has_event_paths=has_event_paths, event_paths=event_paths, latest_event=latest_event
    )


def build_work_selection_service(
    *, bound_selection: Callable[[str], dict[str, Any] | None],
    valid_selector: Callable[[str], bool],
    records: Callable[..., list[dict[str, Any]]],
    prefer: Callable[[list[dict[str, Any]], str], dict[str, Any] | None],
    load_run: Callable[[str], dict[str, Any]],
    load_assignment: Callable[[str], dict[str, Any]]
) -> WorkSelectionService:
    from .work.selection import WorkSelectionService

    return WorkSelectionService(
        bound_selection=bound_selection, valid_selector=valid_selector, records=records, prefer=prefer, load_run=load_run, load_assignment=load_assignment
    )


def build_process_selection_service(
    *, project_root: Path,
    stable_ids: Callable[[Any], list[str]],
    resolve_definition: Callable[[Path, str], ResolvedDefinitionView],
    blocked: Callable[..., dict[str, Any]],
    candidates: Callable[..., list[dict[str, Any]]]
) -> ProcessSelectionService:
    from .process_selection import ProcessSelectionService

    return ProcessSelectionService(
        project_root=project_root, stable_ids=stable_ids, resolve_definition=resolve_definition, blocked=blocked, candidates=candidates
    )


def build_process_pin_read_service(
    *, project_root: Path,
    flow_root: Callable[[], Path],
    snapshots: Callable[[], ProjectSnapshotReadPort],
    fingerprint: Callable[[Any], str],
    stable_ids: Callable[[Any], list[str]]
) -> ProcessPinReadService:
    from .process_pin import ProcessPinReadService

    return ProcessPinReadService(
        project_root=project_root, flow_root=flow_root, snapshots=snapshots, fingerprint=fingerprint, stable_ids=stable_ids
    )


def build_run_completion_policy(
    *, accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]],
    string_list: Callable[[Any], list[str]],
    gate_state: Callable[..., dict[str, Any]]
) -> RunCompletionPolicy:
    from .run_completion import RunCompletionPolicy

    return RunCompletionPolicy(
        accumulated_evidence=accumulated_evidence, string_list=string_list, gate_state=gate_state
    )


def build_completion_intent_validation_service(
    *, project_root: Path,
    fingerprint: Callable[[Any], str],
    terminal_assignment_statuses: Callable[[], set[str]],
    effective_process: Callable[[dict[str, Any]], tuple[dict[str, Any], str]],
    rel: Callable[[Path, Path], str],
    run_path: Callable[[str], Path],
    assignment_path: Callable[[str], Path],
    flow_root: Callable[[], Path],
    has_project_id: Callable[[], bool],
    project_id: Callable[[Path], Any]
) -> CompletionIntentValidationService:
    from .completion_intent_validation import CompletionIntentValidationService

    return CompletionIntentValidationService(
        project_root=project_root, fingerprint=fingerprint, terminal_assignment_statuses=terminal_assignment_statuses, effective_process=effective_process, rel=rel, run_path=run_path, assignment_path=assignment_path, flow_root=flow_root, has_project_id=has_project_id, project_id=project_id
    )


def build_transition_rejection_policy(
    *, state: Callable[..., dict[str, Any]]
) -> TransitionRejectionPolicy:
    from .transition_rejection import TransitionRejectionPolicy

    return TransitionRejectionPolicy(
        state=state
    )


def build_work_boundary_advisory_service(
    *, flow_root: Callable[[], Path],
    stable_ids: Callable[[Any], list[str]],
    load_document: Callable[[Path], dict[str, Any]]
) -> WorkBoundaryAdvisoryService:
    from .work.boundary_advisory import WorkBoundaryAdvisoryService

    return WorkBoundaryAdvisoryService(
        flow_root=flow_root, stable_ids=stable_ids, load_document=load_document
    )


def build_completion_document_service(
    *, project_root: Path,
    run_path: Callable[[str], Path],
    has_task_index: Callable[[], bool],
    task_index: Callable[[Path, dict[str, Any]], str],
    atomic_text: Callable[[Path, str], Any]
) -> CompletionDocumentService:
    from .completion_documents import CompletionDocumentService

    return CompletionDocumentService(
        project_root=project_root, run_path=run_path, has_task_index=has_task_index, task_index=task_index, atomic_text=atomic_text
    )


def build_completion_intent_builder(
    *, project_root: Path,
    accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]],
    set_task_status: Callable[[dict[str, Any], str, str], Any],
    run_path: Callable[[str], Path],
    assignment_path: Callable[[str], Path],
    flow_root: Callable[[], Path],
    summary: Callable[[dict[str, Any], dict[str, Any]], str],
    has_task_index: Callable[[], bool],
    task_index: Callable[[Path, dict[str, Any]], str],
    rel: Callable[[Path, Path], str],
    intent_path: Callable[[str], Path],
    project_id: Callable[[Path], Any],
    fingerprint: Callable[[Any], str]
) -> CompletionIntentBuilder:
    from .completion_intent_builder import CompletionIntentBuilder

    return CompletionIntentBuilder(
        project_root=project_root, accumulated_evidence=accumulated_evidence, set_task_status=set_task_status, run_path=run_path, assignment_path=assignment_path, flow_root=flow_root, summary=summary, has_task_index=has_task_index, task_index=task_index, rel=rel, intent_path=intent_path, project_id=project_id, fingerprint=fingerprint
    )


def build_completion_intent_read_service(
    *, run_path: Callable[[str], Path],
    intent_path: Callable[[str], Path],
    valid_id: Callable[[str], bool],
    load_document: Callable[[Path], dict[str, Any]],
    validate: Callable[[Any, dict[str, Any], dict[str, Any], Path], str | None]
) -> CompletionIntentReadService:
    from .completion_intent_read import CompletionIntentReadService

    return CompletionIntentReadService(
        run_path=run_path, intent_path=intent_path, valid_id=valid_id, load_document=load_document, validate=validate
    )


def build_completion_intent_replay_service(
    *, assignment_path: Callable[[str], Path],
    run_path: Callable[[str], Path],
    flow_root: Callable[[], Path],
    atomic_yaml: Callable[[Path, dict[str, Any]], Any],
    atomic_text: Callable[[Path, str], Any],
    state: Callable[..., dict[str, Any]],
    write_projection: Callable[[dict[str, Any]], Any],
    emit: Callable[..., Any],
    intent_path: Callable[[str], Path]
) -> CompletionIntentReplayService:
    from .completion_intent_replay import CompletionIntentReplayService

    return CompletionIntentReplayService(
        assignment_path=assignment_path, run_path=run_path, flow_root=flow_root, atomic_yaml=atomic_yaml, atomic_text=atomic_text, state=state, write_projection=write_projection, emit=emit, intent_path=intent_path
    )


def build_work_transition_commit_service(
    *,
    now_utc: Callable[[], str],
    set_run_task_status: Callable[[dict[str, Any], str, str], Any],
    assignment_path: Callable[[str], Path],
    run_path: Callable[[str], Path],
    atomic_yaml: Callable[[Path, dict[str, Any]], Any],
    write_task_index: Callable[[dict[str, Any]], Any],
    build_completion_intent: Callable[..., dict[str, Any]],
    completion_intent_path: Callable[[str], Path],
    atomic_text: Callable[[Path, str], Any],
    replay_completion_intent: Callable[..., dict[str, Any]],
    state: Callable[..., dict[str, Any]],
    write_projection: Callable[[dict[str, Any]], Any],
    emit: Callable[..., Any],
    next_work_advisory: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> WorkTransitionCommitService:
    from .work.transition_commit import WorkTransitionCommitService

    return WorkTransitionCommitService(
        now_utc=now_utc,
        set_run_task_status=set_run_task_status,
        assignment_path=assignment_path,
        run_path=run_path,
        atomic_yaml=atomic_yaml,
        write_task_index=write_task_index,
        build_completion_intent=build_completion_intent,
        completion_intent_path=completion_intent_path,
        atomic_text=atomic_text,
        replay_completion_intent=replay_completion_intent,
        state=state,
        write_projection=write_projection,
        emit=emit,
        next_work_advisory=next_work_advisory,
    )
