"""Internal, explicit service composition; construction performs no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Callable

from .ports import ProcessDefinitionReadPort, ProjectSnapshotReadPort, WorkContextReadPort, WorkRecordReadPort
from .work.records import CurrentWorkService, YamlWorkRecordReader

if TYPE_CHECKING:
    from .documents.reader import YamlDocumentReader
    from .completion.request import CompletionIntentReader, CompletionReadinessReader, CompletionStateReader, CompletionTransition, CompletionWorkSelector, WorkCompletionRequestService
    from typing import Collection, Pattern
    from .work.record_catalog import CompletionIntentLookup, WorkCatalogInventoryFactory, WorkRecordCatalogService
    from contextlib import AbstractContextManager
    from .work.continuation_publication import ContinuationBindingReader, ContinuationDocumentWriter, ContinuationPublicationService, ContinuationStatusReader
    from .work.cancellation_replay import CancellationBindingReader, CancellationEventReader, CancellationReplayService, CancellationWorkWriter
    from .work.material_read import WorkMaterialCapture, WorkMaterialReadService
    from .work.resource_bindings import BindingMaterialCapture, ResourceBindingBuilder
    from .prepared.knowledge_resources import PreparedKnowledgeMaterialCapture, PreparedKnowledgeResourceReader, PreparedKnowledgeRootResolver
    from .work.resource_declarations import ResourceDeclarationPolicy
    from .work.resource_material import MaterialBudget, MaterialError
    from .work.resources import WorkResourceError
    from .prepared.registry_resources import PreparedRegistryPathResolver, PreparedRegistryResourceReader
    from .prepared.resource_selection import PreparedResourceSelectionPolicy
    from .prepared.snapshot_read import PreparedResourceSnapshotReader
    from .work.continuation_work import ContinuationContractValidator, ContinuationResourceReads, ContinuationWorkReadService, ContinuationWorkRecords
    from .work.resource_context import WorkContractValidator, WorkControlDocumentReader, WorkResourceContextReadService, WorkResourceErrorFactory
    from .work.continuation_status import ContinuationStatusReadService, WorkCandidateReader
    from .work.continuation_read import ContinuationRecordReader
    from .work.start_publication import StartEventWriter, StartStateReader, WorkStartPublicationService
    from .work.creation_scope import CreationScopeService
    from .work.bootstrap import GovernedWorkBootstrapService, WorkStart
    from .work.capsule_publication import AssignmentCapsulePublisher
    from .work.events import ProcessEventEmitter, WorkEventPublisher
    from .work.publication import WorkDocumentPublisher
    from .work.boundary_advisory import FreshSessionBoundaryReadService
    from .process_catalog.summary import ProcessSummaryReadService
    from .project.context_read import ExecutionProjectReadService, ProjectContextCheck
    from .project.reconciliation import ContextReconciliationService
    from .work.transition_commit import WorkTransitionCommitService
    from .completion.intent_replay import CompletionIntentReplayService
    from .completion.intent_read import CompletionIntentReadService
    from .completion.intent_builder import CompletionIntentBuilder
    from .completion.documents import CompletionDocumentService
    from .work.boundary_advisory import WorkBoundaryAdvisoryService
    from .work.transition_rejection import TransitionRejectionPolicy
    from .completion.intent_validation import CompletionIntentValidationService
    from .completion.policy import RunCompletionPolicy
    from .process_catalog.pin import ProcessPinReadService
    from .process_catalog.selection import ProcessSelectionService, ResolvedDefinitionView
    from .work.selection import WorkSelectionService
    from .evidence.readiness import StageReadinessPolicy
    from .work.automation_readiness import AutomationReadinessService
    from .evidence.validation import EvidenceValidationService
    from .project.context import ProjectContextService
    from .resources.access import ResourceSearchService
    from .resources.access import ResourceResolveService
    from .project.mode import GarageModeService
    from .project.reports import DerivedReportLifecycleService
    from .diagnostics import Logger
    from .process_execution import ProcessExecutionService
    from .process_catalog.definition_read import ProcessDefinitionReadService
    from .project.snapshot import ProjectSnapshotReadService
    from .work.context_read import WorkContextReadService

__all__ = ()


def build_work_material_reader(
    *,
    project_root: Callable[[], Path],
    workplace_root: Callable[[], Path | None],
    declarations: Callable[[], ResourceDeclarationPolicy],
    metadata: Callable[[], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
    fingerprint: Callable[[], Callable[[Any], str]],
    root_resolver: Callable[[], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]],
    material_capture: Callable[[], WorkMaterialCapture],
    budget: Callable[[], Callable[[], MaterialBudget]],
    error: Callable[[], WorkResourceErrorFactory],
) -> WorkMaterialReadService:
    from .work.material_read import WorkMaterialReadService

    return WorkMaterialReadService(
        project_root=project_root, workplace_root=workplace_root, declarations=declarations,
        metadata=metadata, fingerprint=fingerprint, root_resolver=root_resolver,
        material_capture=material_capture, budget=budget, error=error,
    )


def build_resource_binding_builder(
    *,
    limits: Callable[[], dict[str, int]],
    budget: Callable[[], Callable[[], MaterialBudget]],
    declarations: Callable[[], ResourceDeclarationPolicy],
    snapshot: Callable[[], Callable[[Path], dict[str, Any]]],
    root_resolver: Callable[[], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]],
    material_capture: Callable[[], BindingMaterialCapture],
    work_error: Callable[[], type[WorkResourceError]],
    material_error: Callable[[], type[MaterialError]],
) -> ResourceBindingBuilder:
    from .work.resource_bindings import ResourceBindingBuilder

    return ResourceBindingBuilder(
        limits=limits, budget=budget, declarations=declarations, snapshot=snapshot,
        root_resolver=root_resolver, material_capture=material_capture,
        work_error=work_error, material_error=material_error,
    )


def build_prepared_knowledge_resource_reader(
    *,
    selection: Callable[[], PreparedResourceSelectionPolicy],
    declarations: Callable[[], ResourceDeclarationPolicy],
    metadata: Callable[[], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
    root_resolver: Callable[[], PreparedKnowledgeRootResolver],
    material_capture: Callable[[], PreparedKnowledgeMaterialCapture],
    budget: Callable[[], Callable[[], MaterialBudget]],
    work_error: Callable[[], type[WorkResourceError]],
    material_error: Callable[[], type[MaterialError]],
    fail: Callable[[], Callable[[str], None]],
) -> PreparedKnowledgeResourceReader:
    from .prepared.knowledge_resources import PreparedKnowledgeResourceReader

    return PreparedKnowledgeResourceReader(
        selection=selection, declarations=declarations, metadata=metadata,
        root_resolver=root_resolver, material_capture=material_capture, budget=budget,
        work_error=work_error, material_error=material_error, fail=fail,
    )


def build_prepared_registry_resource_reader(
    *,
    selection: Callable[[], PreparedResourceSelectionPolicy],
    workplace_manifest: Callable[[], Callable[[Path], Path | None]],
    path_resolver: Callable[[], PreparedRegistryPathResolver],
    revoked_statuses: Callable[[], set[str]],
    fail: Callable[[], Callable[[str], None]],
) -> PreparedRegistryResourceReader:
    from .prepared.registry_resources import PreparedRegistryResourceReader

    return PreparedRegistryResourceReader(
        selection=selection, workplace_manifest=workplace_manifest, path_resolver=path_resolver,
        revoked_statuses=revoked_statuses, fail=fail,
    )


def build_prepared_resource_snapshot_reader(
    *,
    flow_root: Callable[[], Callable[[Path], Path]],
    snapshot_paths: Callable[[], Callable[[Path], tuple[Path, Path]]],
    bounded_yaml: Callable[[], Callable[[Path, Path, str], tuple[dict[str, Any], str]]],
    current_snapshot: Callable[[], Callable[[Path], dict[str, Any]]],
    context_checker: Callable[[], ProjectContextCheck],
    selector_pattern: Callable[[], re.Pattern[str]],
    fail: Callable[[], Callable[[str], None]],
) -> PreparedResourceSnapshotReader:
    from .prepared.snapshot_read import PreparedResourceSnapshotReader

    return PreparedResourceSnapshotReader(
        flow_root=flow_root, snapshot_paths=snapshot_paths, bounded_yaml=bounded_yaml,
        current_snapshot=current_snapshot, context_checker=context_checker,
        selector_pattern=selector_pattern, fail=fail,
    )


def build_work_resource_context_reader(
    *, project_root: Callable[[], Path], selector_pattern: Callable[[], re.Pattern[str]],
    flow_root: Callable[[], Callable[[Path], Path]], project_id: Callable[[], Callable[[Path], str]],
    load: Callable[[], WorkControlDocumentReader], identifiers: Callable[[], Callable[[Any, str], list[str]]],
    fingerprint: Callable[[], Callable[[dict], str]], contract_validator: Callable[[], WorkContractValidator],
    error: Callable[[], WorkResourceErrorFactory],
) -> WorkResourceContextReadService:
    from .work.resource_context import WorkResourceContextReadService

    return WorkResourceContextReadService(
        project_root=project_root, selector_pattern=selector_pattern, flow_root=flow_root, project_id=project_id,
        load=load, identifiers=identifiers, fingerprint=fingerprint, contract_validator=contract_validator, error=error,
    )


def build_continuation_work_reader(
    *, selector: Callable[[], Callable[[str], str]], project_root: Callable[[], Path],
    project_id: Callable[[], Callable[[Path], str]], resources: Callable[[], ContinuationResourceReads],
    work: Callable[[], ContinuationWorkRecords], path_resolver: Callable[[], Callable[[str], Path]],
    bounded_reader: Callable[[], Callable[[Path], bytes]], writer_check: Callable[[], Callable[[dict], None]],
    contract_validator: Callable[[], ContinuationContractValidator],
    permission_readiness: Callable[[], Callable[[dict, dict], dict]], scope_allows: Callable[[], Callable[[dict, str, str], bool]],
    active_run_statuses: Callable[[], set[str]], active_assignment_statuses: Callable[[], set[str]],
    error: Callable[[], type[ValueError]],
) -> ContinuationWorkReadService:
    from .work.continuation_work import ContinuationWorkReadService

    return ContinuationWorkReadService(
        selector=selector, project_root=project_root, project_id=project_id, resources=resources, work=work,
        path_resolver=path_resolver, bounded_reader=bounded_reader, writer_check=writer_check,
        contract_validator=contract_validator, permission_readiness=permission_readiness, scope_allows=scope_allows,
        active_run_statuses=active_run_statuses, active_assignment_statuses=active_assignment_statuses, error=error,
    )


def build_continuation_status_reader(
    *, path_resolver: Callable[[], Callable[[str], Path]], selector: Callable[[], Callable[[str], str]],
    load: Callable[[], Callable[[Path], dict]], record_path: Callable[[], Callable[[str], Path]],
    selection_path: Callable[[], Callable[[str], Path]], validate_record: Callable[[], Callable[[dict, str], None]],
    waiting_reader: Callable[[], Callable[[dict], dict]],
    work_resolver: Callable[[], Callable[[dict], tuple[dict, dict, dict, dict]]],
    context_checker: Callable[[], Callable[[], dict]], work_records: Callable[[], WorkCandidateReader],
    error: Callable[[], type[ValueError]],
) -> ContinuationStatusReadService:
    from .work.continuation_status import ContinuationStatusReadService

    return ContinuationStatusReadService(
        path_resolver=path_resolver, selector=selector, load=load, record_path=record_path,
        selection_path=selection_path, validate_record=validate_record, waiting_reader=waiting_reader,
        work_resolver=work_resolver, context_checker=context_checker, work_records=work_records, error=error,
    )


def build_continuation_record_reader(
    *, path_resolver: Callable[[], Callable[[str], Path]], selector: Callable[[], Callable[[str], str]],
    bounded_reader: Callable[[], Callable[[Path, int], bytes]], yaml_loader: Callable[[], Callable[[str], Any]],
    error: Callable[[], type[ValueError]],
    workplace: Callable[[], Path | None], leases_directory: Callable[[], Callable[[Path | None], Path]],
    control_loader: Callable[[], Callable[[Path], dict]],
) -> ContinuationRecordReader:
    from .work.continuation_read import ContinuationRecordReader

    return ContinuationRecordReader(
        path_resolver=path_resolver, selector=selector, bounded_reader=bounded_reader,
        yaml_loader=yaml_loader, error=error,
        workplace=workplace, leases_directory=leases_directory, control_loader=control_loader,
    )


def build_work_start_publication_service(
    *, run_path: Callable[[], Callable[[str], Path]], assignment_path: Callable[[], Callable[[str], Path]],
    atomic_yaml: Callable[[], Callable[[Path, dict[str, Any]], Any]], atomic_text: Callable[[], Callable[[Path, str], Any]],
    write_task_index: Callable[[], Callable[[dict[str, Any]], Any]], emit: Callable[[], StartEventWriter],
    state: Callable[[], StartStateReader], write_projection: Callable[[], Callable[[dict[str, Any]], Any]],
) -> WorkStartPublicationService:
    from .work.start_publication import WorkStartPublicationService

    return WorkStartPublicationService(
        run_path=run_path, assignment_path=assignment_path, atomic_yaml=atomic_yaml,
        atomic_text=atomic_text, write_task_index=write_task_index, emit=emit,
        state=state, write_projection=write_projection,
    )


def build_creation_scope_service(project_root: Path, core: Any) -> CreationScopeService:
    from .work.creation_scope import CreationScopeService

    def handoff_reader() -> Callable[[Path], bytes]:
        from .prepared.input import bounded_read

        return bounded_read

    return CreationScopeService(
        project_root, normalizer=lambda: core.normalize_execution_mode, handoff_reader=handoff_reader,
    )


def build_governed_work_bootstrap_service(project_root: Path, workplace_root: Path, core: Any) -> GovernedWorkBootstrapService:
    from .work.bootstrap import GovernedWorkBootstrapService

    def work_start() -> WorkStart:
        from .process_execution import ProcessExecutionService

        return ProcessExecutionService(project_root, workplace_root, core).start

    return GovernedWorkBootstrapService(
        current_work_summary=lambda: build_current_work_service(project_root).summary(),
        work_start=work_start,
    )


def build_current_work_service(
    project_root: Path, *, documents: YamlDocumentReader | None = None,
) -> CurrentWorkService:
    if documents is None:
        return CurrentWorkService(project_root)
    return CurrentWorkService(project_root, documents)


def build_work_context_read_service(project_root: Path) -> WorkContextReadService:
    from .work.context_read import WorkContextReadService

    return WorkContextReadService(project_root)


@dataclass(frozen=True)
class LegacyProcessDefinitionAdapter:
    project_root: Path
    core: Any

    def resolve_definition(self, process_id: str) -> dict[str, Any]:
        return self.core.resolve_process_definition(self.project_root, process_id).process


def build_process_definition_read_service(
    project_root: Path, core: Any, *, fingerprint: Callable[[dict[str, Any]], str],
) -> ProcessDefinitionReadService:
    from .process_catalog.definition_read import ProcessDefinitionReadService

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
    from .project.snapshot import ProjectSnapshotReadService

    adapter = LegacyProjectSnapshotAdapter(core)
    return ProjectSnapshotReadService(snapshot_path, adapter.load_document, sha256_file)


def build_project_context_snapshot_read_service(project_root: Path, core: Any) -> ProjectSnapshotReadService:
    def snapshot_path() -> Path:
        path, _snapshot_md = core.project_context_snapshot_paths(project_root)
        return path

    return build_project_snapshot_read_service(
        core, snapshot_path=snapshot_path, sha256_file=lambda path: core.sha256_file(path),
    )


def build_execution_project_read_service(
    *,
    project_root: Path,
    workplace_root: Path | None,
    context_checker: Callable[[], ProjectContextCheck],
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]],
    flow_root: Callable[[], Path],
) -> ExecutionProjectReadService:
    from .project.context_read import ExecutionProjectReadService

    return ExecutionProjectReadService(
        project_root=project_root,
        workplace_root=workplace_root,
        context_checker=context_checker,
        document_loader=document_loader,
        flow_root=flow_root,
    )


def build_process_summary_read_service(
    project_root: Path | None = None, core: Any = None,
) -> ProcessSummaryReadService:
    from .process_catalog.summary import ProcessSummaryReadService

    definition_resolver = None
    if core is not None:
        definition_resolver = lambda: core.resolve_process_definition
    return ProcessSummaryReadService(project_root=project_root, definition_resolver=definition_resolver)


def build_fresh_session_boundary_read_service(
    project_root: Path,
) -> FreshSessionBoundaryReadService:
    from .work.boundary_advisory import FreshSessionBoundaryReadService

    return FreshSessionBoundaryReadService(project_root)


def build_project_context_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ProjectContextService:
    from . import garage
    from .project.context import ProjectContextReaders, ProjectContextService

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root, core)

    def runtime_snapshot_resolver() -> Callable[[dict[str, Any]], dict[str, Any]]:
        resolver = garage.snapshot_with_resolved_search_roots
        return lambda snapshot: resolver(project_root, snapshot, workplace_root, core)

    def context_readers() -> ProjectContextReaders:
        from .composition import build_derived_report_lifecycle_service, build_garage_mode_service, build_process_summary_read_service, build_fresh_session_boundary_read_service

        return ProjectContextReaders(
            mode=lambda *, snapshot, session_id: build_garage_mode_service(project_root, workplace_root, core).status(snapshot=snapshot, session_id=session_id),
            process_summary=lambda snapshot, manifest: build_process_summary_read_service(project_root, core).summary(snapshot, manifest),
            derived_reports=lambda *, snapshot: build_derived_report_lifecycle_service(project_root, core).status(snapshot=snapshot),
            boundary=lambda work: build_fresh_session_boundary_read_service(project_root).read(work),
        )

    return ProjectContextService(
        project_root, workplace_root,
        snapshots=snapshots,
        project_id_reader=lambda: core.project_id(project_root),
        context_check=lambda: core.project_context_check_result(project_root, explicit_workplace=str(workplace_root)),
        manifest_reader=lambda: core.load_yaml_document(core.locate_flow_root(project_root) / "process-forge.yaml"),
        runtime_snapshot_resolver=runtime_snapshot_resolver,
        resource_readiness=lambda *, snapshot, check: garage.ResourceSearchService(project_root, workplace_root, LegacyResourceSearchReadAdapter(project_root, workplace_root, core)).readiness(snapshot=snapshot, check=check),
        work_summary=lambda: build_current_work_service(project_root).summary(),
        resource_selection=lambda snapshot: garage.resource_selection_summary(snapshot),
        diagnostics=lambda check, search, mode: garage.diagnostics_from_check(check, search, mode),
        context_readers=context_readers,
    )


def build_context_reconciliation_service(
    project_root: Path, workplace_root: Path, core: Any,
) -> ContextReconciliationService:
    from .project.reconciliation import ContextReconciliationService

    return ContextReconciliationService(
        project_root, workplace_root, context_checker=lambda: core.project_context_check_result,
    )


@dataclass(frozen=True)
class LegacyResourceSearchReadAdapter:
    project_root: Path
    workplace_root: Path
    core: Any

    def read_snapshot(self, snapshots: ProjectSnapshotReadPort | None) -> dict[str, Any]:
        from .resources.access import load_snapshot

        return load_snapshot(self.project_root, self.core, snapshots=snapshots)

    def context_checker(self) -> ProjectContextCheck:
        return self.core.project_context_check_result

    def runtime_snapshot_reader(self) -> Callable[[Path], dict[str, Any]]:
        return self.core.workplace_search_runtime_snapshot

    def search_roots_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        from .resources.access import snapshot_with_resolved_search_roots

        return lambda snapshot: snapshot_with_resolved_search_roots(self.project_root, snapshot, self.workplace_root, self.core)


def build_resource_search_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceSearchService:
    from .resources.access import ResourceSearchService

    return ResourceSearchService(project_root, workplace_root, LegacyResourceSearchReadAdapter(project_root, workplace_root, core), snapshots=snapshots)


@dataclass(frozen=True)
class LegacyResourceResolveReadAdapter:
    project_root: Path
    workplace_root: Path
    core: Any

    def project_id(self) -> str:
        return self.core.project_id(self.project_root)

    def read_snapshot(self, snapshots: ProjectSnapshotReadPort | None) -> dict[str, Any]:
        from .resources.access import load_snapshot

        return load_snapshot(self.project_root, self.core, snapshots=snapshots)

    def path_ref_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        from .resources.access import resolve_garage_path_ref

        return lambda reference: resolve_garage_path_ref(self.project_root, reference, self.workplace_root, self.core)


def build_resource_resolve_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceResolveService:
    from .resources.access import ResourceResolveService

    return ResourceResolveService(project_root, workplace_root, LegacyResourceResolveReadAdapter(project_root, workplace_root, core), snapshots=snapshots)


def build_garage_mode_service(
    project_root: Path, workplace_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> GarageModeService:
    from .project.mode import GarageModeService

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root, core)
    return GarageModeService(project_root, workplace_root, snapshots=snapshots)


def build_derived_report_lifecycle_service(
    project_root: Path, core: Any, *, snapshots: ProjectSnapshotReadPort | None = None,
) -> DerivedReportLifecycleService:
    from .project.reports import DerivedReportLifecycleService

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root, core)
    return DerivedReportLifecycleService(snapshots=snapshots, flow_root=lambda: core.locate_flow_root(project_root))


def build_work_event_publisher(
    *,
    project_root: Path,
    has_emitter: Callable[[], bool],
    emitter: Callable[[], ProcessEventEmitter],
) -> WorkEventPublisher:
    from .work.events import WorkEventPublisher

    return WorkEventPublisher(project_root=project_root, has_emitter=has_emitter, emitter=emitter)


def build_work_document_publisher(
    *,
    text_writer: Callable[[], Callable[[Path, str], None]],
    yaml_formatter: Callable[[], Callable[[dict[str, Any]], str]],
) -> WorkDocumentPublisher:
    from .work.publication import WorkDocumentPublisher

    return WorkDocumentPublisher(text_writer=text_writer, yaml_formatter=yaml_formatter)


def build_assignment_capsule_publisher(
    service: ProcessExecutionService, *, stable_ids: Callable[[Any], list[str]],
) -> AssignmentCapsulePublisher:
    from .work.capsule_publication import AssignmentCapsulePublisher

    def context_fields(
        assignment_path: Path, assignment: dict[str, Any], snapshot: dict[str, Any],
        *, pin: dict[str, Any], run_record: dict[str, Any],
    ) -> dict[str, Any]:
        from .work.context import build_context_fields

        return build_context_fields(
            service.project_root, assignment_path, assignment, snapshot, service.core,
            workplace=service.workplace_root, pin=pin, run_record=run_record,
        )

    return AssignmentCapsulePublisher(
        project_root=service.project_root,
        flow_root=lambda: service._flow_root(),
        assignment_path=lambda identity: service._assignment_path(identity),
        snapshot_reader=lambda: service._snapshot_reader(),
        build_context_fields=context_fields,
        now_utc=lambda: service.core.now_utc(),
        dump_yaml=lambda value: service.core.dump_yaml(value),
        ensure_trailing_newline=lambda text: service.core.ensure_trailing_newline(text),
        relative_path=lambda path, root: service.core.rel(path, root),
        sha256_file=lambda path: service._sha256_file(path),
        stable_ids=stable_ids,
    )


def build_process_execution_service(
    project_root: Path, workplace_root: Path | None, core: Any, *, observer: Logger | None = None,
    records: WorkRecordReadPort | None = None,
    context: WorkContextReadPort | None = None,
    definitions: ProcessDefinitionReadPort | None = None,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> ProcessExecutionService:
    from .process_execution import ProcessExecutionService

    if records is None:
        records = YamlWorkRecordReader(project_root)
    return ProcessExecutionService(project_root, workplace_root, core, observer=observer, records=records, context=context, definitions=definitions, snapshots=snapshots)


def build_evidence_validation_service(
    project_root: Path | Callable[[], Path], *, now_utc: Callable[[], str], relative_path: Callable[[Path], str],
    sha256_file: Callable[[Path], str], path_resolver: Callable[[str], Path | None] | None = None,
) -> EvidenceValidationService:
    from .evidence.validation import EvidenceValidationService

    return EvidenceValidationService(project_root, now_utc, relative_path, sha256_file, path_resolver)


def build_stage_readiness_policy(
    *, file_diagnostic: Callable[[dict[str, Any] | None], dict[str, Any] | None],
    string_list: Callable[[Any], list[str]],
    stage_definitions: Callable[[dict[str, Any]], list[dict[str, Any]]],
    blocker_callback: Callable[[str, str, dict[str, Any]], dict[str, Any]],
) -> StageReadinessPolicy:
    from .evidence.readiness import StageReadinessPolicy

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
    from .work.automation_readiness import AutomationReadinessService

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
    from .process_catalog.selection import ProcessSelectionService

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
    from .process_catalog.pin import ProcessPinReadService

    return ProcessPinReadService(
        project_root=project_root, flow_root=flow_root, snapshots=snapshots, fingerprint=fingerprint, stable_ids=stable_ids
    )


def build_run_completion_policy(
    *, accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]],
    string_list: Callable[[Any], list[str]],
    gate_state: Callable[..., dict[str, Any]]
) -> RunCompletionPolicy:
    from .completion.policy import RunCompletionPolicy

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
    from .completion.intent_validation import CompletionIntentValidationService

    return CompletionIntentValidationService(
        project_root=project_root, fingerprint=fingerprint, terminal_assignment_statuses=terminal_assignment_statuses, effective_process=effective_process, rel=rel, run_path=run_path, assignment_path=assignment_path, flow_root=flow_root, has_project_id=has_project_id, project_id=project_id
    )


def build_transition_rejection_policy(
    *, state: Callable[..., dict[str, Any]]
) -> TransitionRejectionPolicy:
    from .work.transition_rejection import TransitionRejectionPolicy

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
    from .completion.documents import CompletionDocumentService

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
    from .completion.intent_builder import CompletionIntentBuilder

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
    from .completion.intent_read import CompletionIntentReadService

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
    from .completion.intent_replay import CompletionIntentReplayService

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


def build_cancellation_replay_service(
    *, fingerprint: Callable[[], Callable[[dict], str]], error: Callable[[], type[ValueError]],
    writer_check: Callable[[], Callable[[dict], None]], binding_reader: Callable[[], CancellationBindingReader],
    work: Callable[[], CancellationWorkWriter], record_loader: Callable[[], Callable[[Path], dict]],
    project_root: Callable[[], Path], event_paths: Callable[[], Callable[[Path], tuple[Path, ...]]],
    event_reader: Callable[[], CancellationEventReader], event_id: Callable[[], Callable[[dict], str | None]],
) -> CancellationReplayService:
    from .work.cancellation_replay import CancellationReplayService

    return CancellationReplayService(
        fingerprint=fingerprint, error=error, writer_check=writer_check, binding_reader=binding_reader,
        work=work, record_loader=record_loader, project_root=project_root, event_paths=event_paths,
        event_reader=event_reader, event_id=event_id,
    )


def build_continuation_publication_service(
    *, record_path: Callable[[], Callable[[str], Path]], selection_path: Callable[[], Callable[[str], Path]],
    validate_id: Callable[[], Callable[[object], str]], record_loader: Callable[[], Callable[[Path], dict]],
    binding_reader: Callable[[], ContinuationBindingReader], waiting_reader: Callable[[], Callable[[dict], dict]],
    status_reader: Callable[[], ContinuationStatusReader],
    run_lock: Callable[[], Callable[[str], AbstractContextManager[Any]]],
    record_lock: Callable[[], Callable[[Path], AbstractContextManager[Any]]],
    publish_document: Callable[[], ContinuationDocumentWriter], clock: Callable[[], Callable[[], str]],
    error: Callable[[], type[ValueError]],
) -> ContinuationPublicationService:
    from .work.continuation_publication import ContinuationPublicationService

    return ContinuationPublicationService(
        record_path=record_path, selection_path=selection_path, validate_id=validate_id,
        record_loader=record_loader, binding_reader=binding_reader, waiting_reader=waiting_reader,
        status_reader=status_reader, run_lock=run_lock, record_lock=record_lock,
        publish_document=publish_document, clock=clock, error=error,
    )


def build_work_record_catalog_service(
    *, record_reader: Callable[[], WorkRecordReadPort | None],
    inventory_factory: Callable[[], WorkCatalogInventoryFactory], flow_root: Callable[[], Callable[[], Path]],
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]], identifier_pattern: Callable[[], Pattern[str]],
    intent_reader: Callable[[], CompletionIntentLookup],
    active_assignment_statuses: Callable[[], Collection[str]], active_run_statuses: Callable[[], Collection[str]],
) -> WorkRecordCatalogService:
    from .work.record_catalog import WorkRecordCatalogService

    return WorkRecordCatalogService(
        record_reader=record_reader, inventory_factory=inventory_factory, flow_root=flow_root,
        document_loader=document_loader, identifier_pattern=identifier_pattern, intent_reader=intent_reader,
        active_assignment_statuses=active_assignment_statuses, active_run_statuses=active_run_statuses,
    )


def build_work_completion_request_service(
    *, work_selector: Callable[[], CompletionWorkSelector],
    blocked_result: Callable[[], Callable[[str], dict[str, Any]]],
    process_reader: Callable[[], Callable[[dict[str, Any]], tuple[dict[str, Any], str]]],
    outcomes_reader: Callable[[], Callable[[dict[str, Any], str], list[dict[str, Any]]]],
    state_reader: Callable[[], CompletionStateReader],
    run_blockers: Callable[[], Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], list[dict[str, Any]]]],
    intent_reader: Callable[[], CompletionIntentReader], completion_readiness: Callable[[], CompletionReadinessReader],
    transition: Callable[[], CompletionTransition],
) -> WorkCompletionRequestService:
    from .completion.request import WorkCompletionRequestService

    return WorkCompletionRequestService(
        work_selector=work_selector, blocked_result=blocked_result, process_reader=process_reader,
        outcomes_reader=outcomes_reader, state_reader=state_reader, run_blockers=run_blockers,
        intent_reader=intent_reader, completion_readiness=completion_readiness, transition=transition,
    )
