"""Explicit Core composition; distribution properties are captured on request."""

from __future__ import annotations

import re
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Callable

from .common.text import ensure_trailing_newline
from .common.yaml_dump import dump_yaml
from .ports import (
    ProcessDefinitionReadPort,
    ProjectSnapshotReadPort,
    WorkContextReadPort,
    WorkRecordReadPort,
)
from .work.records import CurrentWorkService, YamlWorkRecordReader

if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from typing import Collection, Pattern

    from .agents.process_events import ProcessEventRecorder
    from .common.properties import CoreProperties
    from .completion.documents import CompletionDocumentService
    from .completion.intent_builder import CompletionIntentBuilder
    from .completion.intent_read import CompletionIntentReadService
    from .completion.intent_replay import CompletionIntentReplayService
    from .completion.intent_validation import CompletionIntentValidationService
    from .completion.policy import RunCompletionPolicy
    from .completion.request import (
        CompletionIntentReader,
        CompletionReadinessReader,
        CompletionStateReader,
        CompletionTransition,
        CompletionWorkSelector,
        WorkCompletionRequestService,
    )
    from .configuration import ConfigurationProvider, ProjectPFConfig
    from .diagnostics import Logger
    from .documents.reader import YamlDocumentReader
    from .evidence.readiness import StageReadinessPolicy
    from .evidence.validation import EvidenceValidationService
    from .maintenance.storage_migration import StorageMigrationHost
    from .prepared.knowledge_resources import (
        PreparedKnowledgeMaterialCapture,
        PreparedKnowledgeResourceReader,
        PreparedKnowledgeRootResolver,
    )
    from .prepared.registry_resources import (
        PreparedRegistryPathResolver,
        PreparedRegistryResourceReader,
    )
    from .prepared.resource_selection import PreparedResourceSelectionPolicy
    from .prepared.snapshot_read import PreparedResourceSnapshotReader
    from .presentation.work_summaries import WorkSummaryRenderer
    from .process_catalog.definition_read import ProcessDefinitionReadService
    from .process_catalog.pin import ProcessPinReadService
    from .process_catalog.selection import (
        ProcessSelectionService,
        ResolvedDefinitionView,
    )
    from .process_catalog.summary import ProcessSummaryReadService
    from .process_execution import ProcessExecutionService
    from .project.context import ProjectContextService
    from .project.context_read import ExecutionProjectReadService, ProjectContextCheck
    from .project.metadata import ProjectMetadataReader
    from .project.mode import GarageModeService
    from .project.reconciliation import ContextReconciliationService
    from .project.reports import DerivedReportLifecycleService
    from .project.snapshot import ProjectSnapshotReadService
    from .resources.access import ResourceResolveService, ResourceSearchService
    from .work.automation_readiness import AutomationReadinessService
    from .work.bootstrap import GovernedWorkBootstrapService, WorkStart
    from .work.boundary_advisory import (
        FreshSessionBoundaryReadService,
        WorkBoundaryAdvisoryService,
    )
    from .work.cancellation_replay import (
        CancellationBindingReader,
        CancellationEventReader,
        CancellationReplayService,
        CancellationWorkWriter,
    )
    from .work.capsule_publication import AssignmentCapsulePublisher
    from .work.context_read import WorkContextReadService
    from .work.continuation_publication import (
        ContinuationBindingReader,
        ContinuationDocumentWriter,
        ContinuationPublicationService,
        ContinuationStatusReader,
    )
    from .work.continuation_read import ContinuationRecordReader
    from .work.continuation_status import (
        ContinuationStatusReadService,
        WorkCandidateReader,
    )
    from .work.continuation_work import (
        ContinuationContractValidator,
        ContinuationResourceReads,
        ContinuationWorkReadService,
        ContinuationWorkRecords,
    )
    from .work.creation_scope import CreationScopeService
    from .work.events import ProcessEventEmitter, WorkEventPublisher
    from .work.material_read import WorkMaterialCapture, WorkMaterialReadService
    from .work.metadata import WorkMetadataReadPass
    from .work.publication import WorkDocumentPublisher
    from .work.record_catalog import (
        CompletionIntentLookup,
        WorkCatalogInventoryFactory,
        WorkRecordCatalogService,
    )
    from .work.resource_bindings import BindingMaterialCapture, ResourceBindingBuilder
    from .work.resource_context import (
        WorkContractValidator,
        WorkControlDocumentReader,
        WorkResourceContextReadService,
        WorkResourceErrorFactory,
    )
    from .work.resource_declarations import ResourceDeclarationPolicy
    from .work.resource_material import MaterialBudget, MaterialError
    from .work.resources import WorkResourceError
    from .work.selection import WorkSelectionService
    from .work.start_publication import (
        StartEventWriter,
        StartStateReader,
        WorkStartPublicationService,
    )
    from .work.transition_commit import WorkTransitionCommitService
    from .work.transition_rejection import TransitionRejectionPolicy

__all__ = ()
_core_properties: CoreProperties | None = None
_core_properties_lock = Lock()


def build_configuration_provider(
    *,
    device_config_path: Path | None = None,
    workplace_root: Path | None = None,
    project_root: Path | None = None,
    context_overrides: ProjectPFConfig | None = None,
) -> ConfigurationProvider:
    """Bind a full application configuration; construction performs no reads."""
    from .project.configuration_inputs import ProjectConfigurationReader

    return ProjectConfigurationReader().configuration_provider(
        project_root,
        workplace_root,
        device_config_path=device_config_path,
        context_overrides=context_overrides,
    )


def _update_selection(
    expected: dict[str, Any],
    device_config_path: Path | None,
    *,
    workplace_root: Path | None = None,
) -> AbstractContextManager[Any]:
    """Keep frozen domain errors intact while releasing the selection gates."""

    class Selected(AbstractContextManager[Any]):
        def __enter__(self) -> Any:
            self.scope = _update_selection_scope(
                expected, device_config_path, workplace_root=workplace_root
            )
            return self.scope.__enter__()

        def __exit__(self, *_exception: Any) -> None:
            self.scope.__exit__(None, None, None)

    return Selected()


@contextmanager
def _update_selection_scope(
    expected: dict[str, Any],
    device_config_path: Path | None,
    *,
    workplace_root: Path | None,
) -> Any:
    """Re-read external selectors under the existing gates, without SQL."""
    from contextlib import ExitStack

    from .configuration import ConfigurationProvider, DeviceConfigurationSource
    from .maintenance.contracts import MaintenanceError
    from .runtime.execution_admission import ExecutionAdmission
    from .work.context_documents import ContextContractInputs

    project = Path(expected["project"]) if expected["project"] else None
    workplace = Path(expected["workplace"]) if expected["workplace"] else None
    if workplace_root is not None and workplace_root.resolve() != workplace:
        raise MaintenanceError("storage_enrollment_conflict")
    device = (device_config_path or DeviceConfigurationSource.default_path()).resolve()
    admission = ExecutionAdmission()
    with ExitStack() as gates:
        gates.enter_context(admission.workplace(workplace))
        if project is not None:
            gates.enter_context(admission.project(project))
        # Never reuse an operation's pinned provider: this is an independent
        # external-fact check, including inside the child's configuration scope.
        provider = ConfigurationProvider(
            device_path=device,
            workplace_path=workplace / "configuration.yaml" if workplace else None,
            project_path=ContextContractInputs().locate_flow_root(project)
            / "configuration.yaml"
            if project
            else None,
        )
        snapshot = provider.snapshot(refresh=True)
        if snapshot.errors:
            raise MaintenanceError("storage_configuration_invalid")
        host = build_storage_migration_host(
            project_root=project,
            workplace_root=workplace,
            device_config_path=device,
            configuration=ConfigurationProvider.pinned(snapshot.config),
        )
        resolver = host.service._native_selection
        if resolver is None:
            raise MaintenanceError("storage_safety_unavailable")
        selected = resolver()
        if selected.document() != expected:
            raise MaintenanceError("storage_enrollment_conflict")
        yield selected, snapshot.config.to_dict()


def build_storage_migration_host(
    *,
    project_root: Path | None,
    workplace_root: Path | None,
    device_config_path: Path | None,
    configuration: ConfigurationProvider,
    evidence_dir: Path | None = None,
) -> StorageMigrationHost:
    """Bind a cold host; resolve metadata and UUID only on explicit operations.

    The supplied provider is the operation's full pinned value. No source is
    discovered, read, connected, locked or initialized during construction.
    Native publication/owner proof remains independent from SQLite selection.
    """
    import sys
    from typing import Literal
    from uuid import uuid4

    from .configuration import DeviceConfigurationSource
    from .database import (
        Database,
        DatabaseFactory,
        DatabaseIdentity,
        DatabaseTarget,
        SchemaManager,
        SQLiteDriver,
    )
    from .executions.composition import _execution_profile
    from .executions.sqlite_repository import SQLiteExecutionRepository
    from .maintenance.backup import SQLiteBackupService
    from .maintenance.contracts import (
        ExecutionMigrationContext,
        MaintenanceError,
        MigrationSafety,
        StorageMigrationContext,
        StoreTarget,
    )
    from .maintenance.execution_migration import ExecutionMigrationService, _read
    from .maintenance.storage_migration import (
        MIGRATION_ID,
        StorageMigrationHost,
        StorageMigrationService,
        _safe,
        _uuid,
        validate_storage_context,
    )
    from .project.metadata import ProjectMetadataReader
    from .runtime.execution_admission import ExecutionAdmission, registry_file_lock

    def resolve_context() -> StorageMigrationContext:
        # These are the already selected roots, never an installation/device scan.
        device = device_config_path or DeviceConfigurationSource.default_path()
        _safe(device)
        snapshot = configuration.snapshot()
        if snapshot.errors:
            raise MaintenanceError("storage_configuration_invalid")
        targets: list[StoreTarget] = []
        unqualified: list[tuple[Literal["raw", "search", "accounting"], Path]] = []
        if project_root is not None:
            project = _safe(project_root)
            metadata = ProjectMetadataReader(project)
            flow = metadata.flow_root()
            declared = metadata.workplace_manifest()
            if declared is not None and (
                workplace_root is None
                or declared.absolute() != workplace_root / "workplace.yaml"
            ):
                raise MaintenanceError("storage_enrollment_conflict")
            owner = metadata.manifest().get("project")
            owner_id = owner.get("id") if isinstance(owner, dict) else None
            if not isinstance(owner_id, str) or not owner_id.strip():
                raise MaintenanceError("project_identity_required")
            _profile_id, relative, _timeout = _execution_profile(
                snapshot.config.database
            )
            project_targets: tuple[
                tuple[Literal["events", "raw", "main"], str], ...
            ] = (
                ("events", "runtime/events/events.sqlite3"),
                ("raw", "runtime/agent-events/hooks.sqlite3"),
                ("main", relative),
            )
            for kind, path in project_targets:
                targets.append(
                    StoreTarget(kind, flow / path, path, "project", owner_id)
                )
            if workplace_root is None:
                path = "runtime/local-resource-search/search.sqlite"
                targets.append(
                    StoreTarget("search", flow / path, path, "project", owner_id)
                )
        if workplace_root is not None:
            workplace = _safe(workplace_root)
            from .common.yaml_io import _parse_simple_yaml
            from .documents.reader import YamlDocumentReader

            document = YamlDocumentReader(_parse_simple_yaml).load(
                _safe(workplace / "workplace.yaml")
            )
            section = document.get("workplace")
            workplace_id = (
                section.get("id") if isinstance(section, dict) else document.get("id")
            )
            # No new identity is minted to label an old workplace. An unknown
            # owner is an explicit routing diagnostic, never a root-name ID.
            workplace_targets: tuple[tuple[Literal["raw", "search"], str], ...] = (
                ("raw", "runtime/agent-events/hooks.sqlite3"),
                ("search", "runtime/search/local-resource-search.sqlite"),
            )
            for workplace_kind, path in workplace_targets:
                if isinstance(workplace_id, str) and workplace_id.strip():
                    targets.append(
                        StoreTarget(
                            workplace_kind,
                            workplace / path,
                            path,
                            "workplace",
                            workplace_id,
                        )
                    )
                else:
                    unqualified.append((workplace_kind, workplace / path))
            origin = _safe(workplace / "data/accounting/identity.json")
            if origin.exists():
                origin_id = _read(origin).get("origin_id")
                if not isinstance(origin_id, str) or not origin_id.strip():
                    raise MaintenanceError("owner_identity_required")
                path = "data/accounting/accounting.sqlite3"
                targets.append(
                    StoreTarget(
                        "accounting", workplace / path, path, "workplace", origin_id
                    )
                )
            else:
                unqualified.append(
                    ("accounting", workplace / "data/accounting/accounting.sqlite3")
                )
        context = StorageMigrationContext(
            project_root, workplace_root, device, tuple(targets), tuple(unqualified)
        )
        validate_storage_context(context)
        if evidence_dir is not None:
            _safe(evidence_dir)
            roots = (
                [ProjectMetadataReader(project_root).flow_root()]
                if project_root
                else []
            )
            if workplace_root is not None:
                roots.append(workplace_root)
            if not any(
                evidence_dir.is_relative_to(root / "maintenance")
                and evidence_dir != root / "maintenance"
                for root in roots
            ):
                raise MaintenanceError("storage_evidence_unsafe")
        return context

    def safety(context: StorageMigrationContext) -> MigrationSafety:
        # The frozen value stays pinned, but owner/flow/enrollment facts must
        # still name the same physical targets at every mutation boundary.
        from dataclasses import replace

        actual = resolve_context()
        if replace(actual, targets=context.targets) != context or not set(
            context.targets
        ).issubset(actual.targets):
            raise MaintenanceError("storage_enrollment_conflict")
        # Native leaf was captured before Core. Importing/reloading tools here
        # would invent authority from current-file bytes, so use only that entry.
        module = sys.modules.get("pf_native_control")
        current = getattr(module, "current_entry", None)
        entry = current() if callable(current) else None
        verifier = getattr(entry, "storage_safety", None)
        if not callable(verifier):
            return MigrationSafety("unknown", "", ("native_ownership_unqualified",))
        state, generation, evidence = verifier(context)
        return MigrationSafety(state, generation, evidence)

    admission = ExecutionAdmission(registry_file_lock)

    def engine(
        context: StorageMigrationContext, target: StoreTarget
    ) -> ExecutionMigrationService:
        if context.project_root is None:
            raise MaintenanceError("storage_execution_host_required")
        from .executions.composition import (
            _fresh_initialization,
            _repair_fresh_execution_storage,
        )

        flow = ProjectMetadataReader(context.project_root).flow_root()
        initializer = _fresh_initialization(flow)
        if initializer is not None and initializer["state"] == "pending":
            module = sys.modules.get("pf_native_control")
            capable = getattr(module, "supports_owned_execution", None)
            if not callable(capable) or not capable():
                raise MaintenanceError("execution_storage_not_ready")
            with admission.maintenance(context.project_root, context.workplace_root):
                proof = safety(context)
                if proof.state != "proven":
                    raise MaintenanceError("storage_safety_changed")

                def verify_fresh() -> None:
                    current = safety(context)
                    if (
                        current.state != "proven"
                        or current.generation != proof.generation
                    ):
                        raise MaintenanceError("storage_safety_changed")

                _repair_fresh_execution_storage(
                    context.project_root,
                    context.workplace_root,
                    configuration=configuration,
                    _verify=verify_fresh,
                )
                after = safety(context)
                if after.state != "proven" or after.generation != proof.generation:
                    raise MaintenanceError("storage_safety_changed")
        config = configuration.current()
        profile_id, relative, timeout = _execution_profile(config.database)
        if target.target_relative_path != relative:
            raise MaintenanceError("storage_execution_target_conflict")
        driver = DatabaseFactory.resolve_driver(config.database)
        flow = ProjectMetadataReader(context.project_root).flow_root()
        binding = _safe(flow / "data/execution-storage.json")
        selected = _safe(
            flow / "maintenance/storage-migrations" / MIGRATION_ID / "execution.json"
        )
        if binding.exists():
            pins = _read(binding)
            if (
                pins.get("project_id"),
                pins.get("profile_id"),
                pins.get("target_relative_path"),
            ) != (target.owner_id, profile_id, relative):
                raise MaintenanceError("execution_binding_conflict")
            store_id = _uuid(pins.get("store_id"))
        elif selected.exists():
            checksum = _read(selected).get("plan_checksum")
            if (
                not isinstance(checksum, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", checksum) is None
            ):
                raise MaintenanceError("storage_plan_invalid")
            plan = _read(selected.parent / checksum[7:] / "plan.json")
            if (plan.get("project_id"), plan.get("target_relative_path")) != (
                target.owner_id,
                relative,
            ):
                raise MaintenanceError("storage_execution_target_conflict")
            store_id = _uuid(plan.get("store_id"))
        else:
            discovery = Database(
                driver,
                DatabaseTarget(
                    target.target, DatabaseIdentity(None, "project", target.owner_id)
                ),
                timeout_ms=timeout,
            )
            status = SchemaManager().inspect(discovery, ())
            if status.state == "missing":
                store_id = uuid4().hex  # Only reached after real admitted proof.
            elif status.identity is not None and status.state == "ready":
                store_id = _uuid(status.identity.store_id)
            else:
                raise MaintenanceError("execution_storage_not_ready")
        database = DatabaseFactory.from_profile(
            config.database,
            profile_id,
            DatabaseTarget(
                target.target, DatabaseIdentity(store_id, "project", target.owner_id)
            ),
        )

        def execution_safety(context: ExecutionMigrationContext) -> MigrationSafety:
            pins = context
            if (
                pins.project_root,
                pins.workplace_root,
                pins.project_id,
                pins.store_id,
                pins.target_relative_path,
            ) != (
                selected_context.project_root,
                selected_context.workplace_root,
                target.owner_id,
                store_id,
                relative,
            ):
                raise MaintenanceError("execution_identity_conflict")
            # Re-resolve routing/owners at every freeze/resume/cutover boundary.
            if resolve_context() != selected_context:
                raise MaintenanceError("storage_enrollment_conflict")
            if context.phase == "inspect":
                # Planning scans outside admission; its host proof still uses
                # the real gates. Freeze/cutover revalidate source facts again.
                with admission.maintenance(
                    context.project_root, context.workplace_root
                ):
                    return safety(selected_context)
            return safety(selected_context)

        selected_context = context
        return ExecutionMigrationService(
            database=database,
            repository=SQLiteExecutionRepository(database, target.owner_id),
            admission=admission,
            backup=SQLiteBackupService(driver=driver),
            safety=execution_safety,
            workplace_root=context.workplace_root,
            profile_id=profile_id,
        )

    def native_selection() -> Any:
        import hashlib
        import json

        actual = resolve_context()
        module = sys.modules.get("pf_native_control")
        selection_type = getattr(module, "ManagedSelection", None)
        if selection_type is None:
            raise MaintenanceError("storage_safety_unavailable")
        instance = ""
        if actual.workplace_root is not None:
            state_path = _safe(
                actual.workplace_root / "runtime/pf-runtime/service.json"
            )
            if state_path.exists():
                with state_path.open("rb") as stream:
                    raw = stream.read(65537)
                if len(raw) > 65536:
                    raise MaintenanceError("storage_enrollment_conflict")
                state = json.loads(raw)
                instance = state.get("instance_id", "")
                if not isinstance(instance, str):
                    raise MaintenanceError("storage_enrollment_conflict")
        route = {
            "device": str(actual.device_config_path),
            "configuration": configuration.current().to_dict(),
            "unqualified": [
                (kind, str(path)) for kind, path in actual.unqualified_targets
            ],
        }
        revision = hashlib.sha256(
            json.dumps(route, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        owners = sorted({target.owner_id for target in actual.targets})
        return selection_type(
            str(actual.project_root or ""),
            str(actual.workplace_root or ""),
            ":".join(owners),
            instance,
            revision,
            tuple((t.kind, str(t.target), t.scope, t.owner_id) for t in actual.targets),
            _device_config_path=str(actual.device_config_path),
        )

    from contextlib import contextmanager

    @contextmanager
    def native_operation(
        context: StorageMigrationContext, deadline: float | None
    ) -> Any:
        module = sys.modules.get("pf_native_control")
        current = getattr(module, "current_entry", None)
        entry = current() if callable(current) else None
        if entry is None or getattr(entry, "control", None) is None:
            # No first-old provider: legacy proof stays unknown; pending refuses.
            yield
            return
        producer_type = getattr(module, "ManagedEnrollmentProducer", None)
        if module is None or producer_type is None or entry.publication is None:
            raise MaintenanceError("storage_safety_unavailable")
        producer = producer_type(entry.root, entry.publication.payload[module.LEAF])
        try:
            with producer.operation(
                entry,
                resolver=native_selection,
                admission_held=lambda: admission.held(
                    context.project_root, context.workplace_root
                ),
                deadline=deadline,
            ):
                yield
        except RuntimeError as error:
            if isinstance(error, getattr(module, "NativeControlError", ())):
                raise MaintenanceError("execution_activity_unknown") from None
            raise

    # Driver resolution also remains lazy with respect to the supplied provider.
    # The closed default is SQLite; the resolved full snapshot is bound when
    # context is first requested, before any service operation connects.
    service = StorageMigrationService(
        backup=SQLiteBackupService(driver=SQLiteDriver()),
        admission=admission,
        registry_lock=registry_file_lock,
        safety=safety,
        execution_factory=engine,
        driver=SQLiteDriver(),
    )
    service._native_operation = native_operation
    # Native-only qualification fixtures/handoffs use the actual resolver; no bool proof.
    service._native_selection = native_selection
    original_resolve = resolve_context

    def bind_context() -> StorageMigrationContext:
        context = original_resolve()
        service.driver = DatabaseFactory.resolve_driver(
            configuration.current().database
        )
        service.backup = SQLiteBackupService(driver=service.driver)
        return context

    class AutomaticStorageHost(StorageMigrationHost):
        @property
        def context(self) -> StorageMigrationContext:
            """Select metadata at each adapter boundary within the CLI operation.

            A completed adapter may establish a previously unqualified owner.
            The next adapter selects again; each service call still captures
            one immutable context and safety strictly revalidates that value.
            """
            return bind_context()

    return AutomaticStorageHost(
        None, service, _context_factory=bind_context, _automatic=True
    )


def build_core_properties() -> CoreProperties:
    """Capture the owning Core distribution once per application process."""
    from .common.properties import CoreProperties

    global _core_properties
    with _core_properties_lock:
        if _core_properties is None:
            _core_properties = CoreProperties.from_distribution(
                Path(__file__).resolve().parents[2]
            )
        return _core_properties


def build_work_material_reader(
    *,
    project_root: Callable[[], Path],
    workplace_root: Callable[[], Path | None],
    declarations: Callable[[], ResourceDeclarationPolicy],
    metadata: Callable[[], Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
    fingerprint: Callable[[], Callable[[Any], str]],
    root_resolver: Callable[
        [], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]
    ],
    material_capture: Callable[[], WorkMaterialCapture],
    budget: Callable[[], Callable[[], MaterialBudget]],
    error: Callable[[], WorkResourceErrorFactory],
) -> WorkMaterialReadService:
    from .work.material_read import WorkMaterialReadService

    return WorkMaterialReadService(
        project_root=project_root,
        workplace_root=workplace_root,
        declarations=declarations,
        metadata=metadata,
        fingerprint=fingerprint,
        root_resolver=root_resolver,
        material_capture=material_capture,
        budget=budget,
        error=error,
    )


def build_resource_binding_builder(
    *,
    limits: Callable[[], dict[str, int]],
    budget: Callable[[], Callable[[], MaterialBudget]],
    declarations: Callable[[], ResourceDeclarationPolicy],
    snapshot: Callable[[], Callable[[Path], dict[str, Any]]],
    root_resolver: Callable[
        [], Callable[[Path, Path | None, dict[str, Any]], tuple[Path, dict[str, Any]]]
    ],
    material_capture: Callable[[], BindingMaterialCapture],
    work_error: Callable[[], type[WorkResourceError]],
    material_error: Callable[[], type[MaterialError]],
) -> ResourceBindingBuilder:
    from .work.resource_bindings import ResourceBindingBuilder

    return ResourceBindingBuilder(
        limits=limits,
        budget=budget,
        declarations=declarations,
        snapshot=snapshot,
        root_resolver=root_resolver,
        material_capture=material_capture,
        work_error=work_error,
        material_error=material_error,
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
        selection=selection,
        declarations=declarations,
        metadata=metadata,
        root_resolver=root_resolver,
        material_capture=material_capture,
        budget=budget,
        work_error=work_error,
        material_error=material_error,
        fail=fail,
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
        selection=selection,
        workplace_manifest=workplace_manifest,
        path_resolver=path_resolver,
        revoked_statuses=revoked_statuses,
        fail=fail,
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
        flow_root=flow_root,
        snapshot_paths=snapshot_paths,
        bounded_yaml=bounded_yaml,
        current_snapshot=current_snapshot,
        context_checker=context_checker,
        selector_pattern=selector_pattern,
        fail=fail,
    )


def build_work_resource_context_reader(
    *,
    project_root: Callable[[], Path],
    selector_pattern: Callable[[], re.Pattern[str]],
    flow_root: Callable[[], Callable[[Path], Path]],
    project_id: Callable[[], Callable[[Path], str]],
    load: Callable[[], WorkControlDocumentReader],
    identifiers: Callable[[], Callable[[Any, str], list[str]]],
    fingerprint: Callable[[], Callable[[dict], str]],
    contract_validator: Callable[[], WorkContractValidator],
    error: Callable[[], WorkResourceErrorFactory],
) -> WorkResourceContextReadService:
    from .work.resource_context import WorkResourceContextReadService

    return WorkResourceContextReadService(
        project_root=project_root,
        selector_pattern=selector_pattern,
        flow_root=flow_root,
        project_id=project_id,
        load=load,
        identifiers=identifiers,
        fingerprint=fingerprint,
        contract_validator=contract_validator,
        error=error,
    )


def build_continuation_work_reader(
    *,
    selector: Callable[[], Callable[[str], str]],
    project_root: Callable[[], Path],
    project_id: Callable[[], Callable[[Path], str]],
    resources: Callable[[], ContinuationResourceReads],
    work: Callable[[], ContinuationWorkRecords],
    path_resolver: Callable[[], Callable[[str], Path]],
    bounded_reader: Callable[[], Callable[[Path], bytes]],
    writer_check: Callable[[], Callable[[dict], None]],
    contract_validator: Callable[[], ContinuationContractValidator],
    permission_readiness: Callable[[], Callable[[dict, dict], dict]],
    scope_allows: Callable[[], Callable[[dict, str, str], bool]],
    active_run_statuses: Callable[[], set[str]],
    active_assignment_statuses: Callable[[], set[str]],
    error: Callable[[], type[ValueError]],
) -> ContinuationWorkReadService:
    from .work.continuation_work import ContinuationWorkReadService

    return ContinuationWorkReadService(
        selector=selector,
        project_root=project_root,
        project_id=project_id,
        resources=resources,
        work=work,
        path_resolver=path_resolver,
        bounded_reader=bounded_reader,
        writer_check=writer_check,
        contract_validator=contract_validator,
        permission_readiness=permission_readiness,
        scope_allows=scope_allows,
        active_run_statuses=active_run_statuses,
        active_assignment_statuses=active_assignment_statuses,
        error=error,
    )


def build_continuation_status_reader(
    *,
    path_resolver: Callable[[], Callable[[str], Path]],
    selector: Callable[[], Callable[[str], str]],
    load: Callable[[], Callable[[Path], dict]],
    record_path: Callable[[], Callable[[str], Path]],
    selection_path: Callable[[], Callable[[str], Path]],
    validate_record: Callable[[], Callable[[dict, str], None]],
    waiting_reader: Callable[[], Callable[[dict], dict]],
    work_resolver: Callable[[], Callable[[dict], tuple[dict, dict, dict, dict]]],
    context_checker: Callable[[], Callable[[], dict]],
    work_records: Callable[[], WorkCandidateReader],
    error: Callable[[], type[ValueError]],
) -> ContinuationStatusReadService:
    from .work.continuation_status import ContinuationStatusReadService

    return ContinuationStatusReadService(
        path_resolver=path_resolver,
        selector=selector,
        load=load,
        record_path=record_path,
        selection_path=selection_path,
        validate_record=validate_record,
        waiting_reader=waiting_reader,
        work_resolver=work_resolver,
        context_checker=context_checker,
        work_records=work_records,
        error=error,
    )


def build_continuation_record_reader(
    *,
    path_resolver: Callable[[], Callable[[str], Path]],
    selector: Callable[[], Callable[[str], str]],
    bounded_reader: Callable[[], Callable[[Path, int], bytes]],
    yaml_loader: Callable[[], Callable[[str], Any]],
    error: Callable[[], type[ValueError]],
    workplace: Callable[[], Path | None],
    leases_directory: Callable[[], Callable[[Path | None], Path]],
    control_loader: Callable[[], Callable[[Path], dict]],
) -> ContinuationRecordReader:
    from .work.continuation_read import ContinuationRecordReader

    return ContinuationRecordReader(
        path_resolver=path_resolver,
        selector=selector,
        bounded_reader=bounded_reader,
        yaml_loader=yaml_loader,
        error=error,
        workplace=workplace,
        leases_directory=leases_directory,
        control_loader=control_loader,
    )


def build_work_start_publication_service(
    *,
    run_path: Callable[[], Callable[[str], Path]],
    assignment_path: Callable[[], Callable[[str], Path]],
    atomic_yaml: Callable[[], Callable[[Path, dict[str, Any]], Any]],
    atomic_text: Callable[[], Callable[[Path, str], Any]],
    write_task_index: Callable[[], Callable[[dict[str, Any]], Any]],
    emit: Callable[[], StartEventWriter],
    state: Callable[[], StartStateReader],
    write_projection: Callable[[], Callable[[dict[str, Any]], Any]],
) -> WorkStartPublicationService:
    from .work.start_publication import WorkStartPublicationService

    return WorkStartPublicationService(
        run_path=run_path,
        assignment_path=assignment_path,
        atomic_yaml=atomic_yaml,
        atomic_text=atomic_text,
        write_task_index=write_task_index,
        emit=emit,
        state=state,
        write_projection=write_projection,
    )


def build_creation_scope_service(project_root: Path, core: Any) -> CreationScopeService:
    from .work.creation_scope import CreationScopeService

    def handoff_reader() -> Callable[[Path], bytes]:
        from .prepared.input import bounded_read

        return bounded_read

    return CreationScopeService(
        project_root,
        normalizer=lambda: core.normalize_execution_mode,
        handoff_reader=handoff_reader,
    )


def build_governed_work_bootstrap_service(
    project_root: Path,
    workplace_root: Path,
    core: Any,
    *,
    events: ProcessEventRecorder | None = None,
    summaries: WorkSummaryRenderer | None = None,
) -> GovernedWorkBootstrapService:
    from .work.bootstrap import GovernedWorkBootstrapService

    def work_start() -> WorkStart:
        from .process_execution import ProcessExecutionService

        service = ProcessExecutionService(project_root, workplace_root, core)
        object.__setattr__(service, "_process_events", events)
        object.__setattr__(service, "_work_summaries", summaries)
        return service.start

    return GovernedWorkBootstrapService(
        current_work_summary=lambda: build_current_work_service(project_root).summary(),
        work_start=work_start,
    )


def build_current_work_service(
    project_root: Path,
    *,
    documents: YamlDocumentReader | None = None,
    work_metadata: Callable[[], WorkMetadataReadPass] | None = None,
) -> CurrentWorkService:
    if work_metadata is None:
        if documents is None:
            return CurrentWorkService(project_root)
        return CurrentWorkService(project_root, documents)
    if documents is None:
        return CurrentWorkService(project_root, work_metadata=work_metadata)
    return CurrentWorkService(project_root, documents, work_metadata=work_metadata)


def build_work_metadata_read_pass(project_root: Path) -> WorkMetadataReadPass:
    from .work.metadata import WorkMetadataReadPass

    return WorkMetadataReadPass(project_root)


def build_work_context_read_service(project_root: Path) -> WorkContextReadService:
    from .work.context_read import WorkContextReadService

    return WorkContextReadService(project_root)


def build_process_definition_read_service(
    project_root: Path,
) -> ProcessDefinitionReadService:
    from .process_catalog.definition_read import ProcessDefinitionReadService

    return ProcessDefinitionReadService(project_root)


def build_project_snapshot_read_service(
    project_root: Path,
) -> ProjectSnapshotReadService:
    from .project.snapshot import ProjectSnapshotReadService

    return ProjectSnapshotReadService(project_root)


def build_project_context_snapshot_read_service(
    project_root: Path,
) -> ProjectSnapshotReadService:
    return build_project_snapshot_read_service(project_root)


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
    project_root: Path | None = None,
) -> ProcessSummaryReadService:
    from .process_catalog.summary import ProcessSummaryReadService

    return ProcessSummaryReadService(project_root=project_root)


def build_fresh_session_boundary_read_service(
    project_root: Path,
) -> FreshSessionBoundaryReadService:
    from .work.boundary_advisory import FreshSessionBoundaryReadService

    return FreshSessionBoundaryReadService(project_root)


def build_project_context_service(
    project_root: Path,
    workplace_root: Path,
    core: Any,
    *,
    snapshots: ProjectSnapshotReadPort | None = None,
    metadata: ProjectMetadataReader | None = None,
    work_metadata: Callable[[], WorkMetadataReadPass] | None = None,
) -> ProjectContextService:
    from . import garage
    from .project.context import ProjectContextReaders, ProjectContextService
    from .project.metadata import ProjectMetadataReader

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root)
    if metadata is None:
        metadata = ProjectMetadataReader(project_root)

    def runtime_snapshot_resolver() -> Callable[[dict[str, Any]], dict[str, Any]]:
        resolver = garage.snapshot_with_resolved_search_roots
        return lambda snapshot: resolver(project_root, snapshot, workplace_root)

    def context_readers() -> ProjectContextReaders:
        from .composition import (
            build_derived_report_lifecycle_service,
            build_fresh_session_boundary_read_service,
            build_garage_mode_service,
            build_process_summary_read_service,
        )

        return ProjectContextReaders(
            mode=lambda *, snapshot, session_id: build_garage_mode_service(
                project_root, workplace_root, core
            ).status(snapshot=snapshot, session_id=session_id),
            process_summary=lambda snapshot, manifest: (
                build_process_summary_read_service(project_root).summary(
                    snapshot, manifest
                )
            ),
            derived_reports=lambda *, snapshot: build_derived_report_lifecycle_service(
                project_root, core
            ).status(snapshot=snapshot),
            boundary=lambda work: build_fresh_session_boundary_read_service(
                project_root
            ).read(work),
        )

    return ProjectContextService(
        project_root,
        workplace_root,
        snapshots=snapshots,
        metadata=metadata,
        context_check=lambda: core.project_context_check_result(
            project_root, explicit_workplace=str(workplace_root)
        ),
        runtime_snapshot_resolver=runtime_snapshot_resolver,
        resource_readiness=lambda *, snapshot, check: garage.ResourceSearchService(
            project_root,
            workplace_root,
            LegacyResourceSearchReadAdapter(project_root, workplace_root, core),
        ).readiness(snapshot=snapshot, check=check),
        work_summary=lambda: build_current_work_service(
            project_root, work_metadata=work_metadata
        ).summary(),
        resource_selection=lambda snapshot: garage.resource_selection_summary(snapshot),
        diagnostics=lambda check, search, mode: garage.diagnostics_from_check(
            check, search, mode
        ),
        context_readers=context_readers,
    )


def build_context_reconciliation_service(
    project_root: Path,
    workplace_root: Path,
    core: Any,
) -> ContextReconciliationService:
    from .project.reconciliation import ContextReconciliationService

    return ContextReconciliationService(
        project_root,
        workplace_root,
        context_checker=lambda: core.project_context_check_result,
    )


@dataclass(frozen=True)
class LegacyResourceSearchReadAdapter:
    project_root: Path
    workplace_root: Path
    core: Any

    def read_snapshot(
        self, snapshots: ProjectSnapshotReadPort | None
    ) -> dict[str, Any]:
        from .project.snapshot import load_snapshot

        return load_snapshot(self.project_root, snapshots=snapshots)

    def context_checker(self) -> ProjectContextCheck:
        return self.core.project_context_check_result

    def runtime_snapshot_reader(self) -> Callable[[Path], dict[str, Any]]:
        from .resources.catalog_read import WorkplaceSearchCatalogReader

        return lambda root: WorkplaceSearchCatalogReader(root).runtime_snapshot()

    def search_roots_resolver(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        from .resources.snapshot import snapshot_with_resolved_search_roots

        return lambda snapshot: snapshot_with_resolved_search_roots(
            self.project_root, snapshot, self.workplace_root
        )


def build_resource_search_service(
    project_root: Path,
    workplace_root: Path,
    core: Any,
    *,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceSearchService:
    from .resources.access import ResourceSearchService

    return ResourceSearchService(
        project_root,
        workplace_root,
        LegacyResourceSearchReadAdapter(project_root, workplace_root, core),
        snapshots=snapshots,
    )


def build_resource_resolve_service(
    project_root: Path,
    workplace_root: Path,
    *,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> ResourceResolveService:
    from .resources.access import ResourceResolveService

    return ResourceResolveService(project_root, workplace_root, snapshots=snapshots)


def build_garage_mode_service(
    project_root: Path,
    workplace_root: Path,
    core: Any,
    *,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> GarageModeService:
    from .project.mode import GarageModeService

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root)
    return GarageModeService(project_root, workplace_root, snapshots=snapshots)


def build_derived_report_lifecycle_service(
    project_root: Path,
    core: Any,
    *,
    snapshots: ProjectSnapshotReadPort | None = None,
) -> DerivedReportLifecycleService:
    from .project.reports import DerivedReportLifecycleService

    if snapshots is None:
        snapshots = build_project_context_snapshot_read_service(project_root)
    return DerivedReportLifecycleService(
        snapshots=snapshots, flow_root=lambda: core.locate_flow_root(project_root)
    )


def build_work_event_publisher(
    *,
    project_root: Path,
    has_emitter: Callable[[], bool],
    emitter: Callable[[], ProcessEventEmitter],
) -> WorkEventPublisher:
    from .work.events import WorkEventPublisher

    return WorkEventPublisher(
        project_root=project_root, has_emitter=has_emitter, emitter=emitter
    )


def build_work_document_publisher(
    *,
    text_writer: Callable[[], Callable[[Path, str], None]],
    yaml_formatter: Callable[[], Callable[[dict[str, Any]], str]],
) -> WorkDocumentPublisher:
    from .work.publication import WorkDocumentPublisher

    return WorkDocumentPublisher(text_writer=text_writer, yaml_formatter=yaml_formatter)


def build_assignment_capsule_publisher(
    service: ProcessExecutionService,
    *,
    stable_ids: Callable[[Any], list[str]],
) -> AssignmentCapsulePublisher:
    from .work.capsule_publication import AssignmentCapsulePublisher

    def context_fields(
        assignment_path: Path,
        assignment: dict[str, Any],
        snapshot: dict[str, Any],
        *,
        pin: dict[str, Any],
        run_record: dict[str, Any],
    ) -> dict[str, Any]:
        from .work.context import build_context_fields

        return build_context_fields(
            service.project_root,
            assignment_path,
            assignment,
            snapshot,
            service.core,
            workplace=service.workplace_root,
            pin=pin,
            run_record=run_record,
        )

    return AssignmentCapsulePublisher(
        project_root=service.project_root,
        flow_root=lambda: service._flow_root(),
        assignment_path=lambda identity: service._assignment_path(identity),
        snapshot_reader=lambda: service._snapshot_reader(),
        build_context_fields=context_fields,
        now_utc=lambda: service._clock(),
        dump_yaml=lambda value: dump_yaml(value),
        ensure_trailing_newline=lambda text: ensure_trailing_newline(text),
        relative_path=lambda path, root: service.core.rel(path, root),
        sha256_file=lambda path: service._sha256_file(path),
        stable_ids=stable_ids,
    )


def bind_process_events(
    service: ProcessExecutionService, events: ProcessEventRecorder | None
) -> ProcessExecutionService:
    """Supply the concrete optional recorder without changing the service constructor."""
    object.__setattr__(service, "_process_events", events)
    return service


def bind_work_summaries(
    service: ProcessExecutionService, summaries: WorkSummaryRenderer | None
) -> ProcessExecutionService:
    """Supply the optional concrete renderer without changing dataclass fields."""
    object.__setattr__(service, "_work_summaries", summaries)
    return service


def build_process_execution_service(
    project_root: Path,
    workplace_root: Path | None,
    core: Any,
    *,
    observer: Logger | None = None,
    records: WorkRecordReadPort | None = None,
    context: WorkContextReadPort | None = None,
    definitions: ProcessDefinitionReadPort | None = None,
    snapshots: ProjectSnapshotReadPort | None = None,
    work_metadata: Callable[[], WorkMetadataReadPass] | None = None,
    events: ProcessEventRecorder | None = None,
    summaries: WorkSummaryRenderer | None = None,
) -> ProcessExecutionService:
    from .process_execution import ProcessExecutionService

    if records is None:
        records = YamlWorkRecordReader(project_root)
        if work_metadata is None:

            def work_metadata() -> WorkMetadataReadPass:
                return build_work_metadata_read_pass(project_root)

    service = ProcessExecutionService(
        project_root,
        workplace_root,
        core,
        observer=observer,
        records=records,
        context=context,
        definitions=definitions,
        snapshots=snapshots,
        work_metadata=work_metadata,
    )
    return bind_work_summaries(bind_process_events(service, events), summaries)


def build_evidence_validation_service(
    project_root: Path | Callable[[], Path],
    *,
    now_utc: Callable[[], str],
    relative_path: Callable[[Path], str],
    sha256_file: Callable[[Path], str],
    path_resolver: Callable[[str], Path | None] | None = None,
) -> EvidenceValidationService:
    from .evidence.validation import EvidenceValidationService

    return EvidenceValidationService(
        project_root, now_utc, relative_path, sha256_file, path_resolver
    )


def build_stage_readiness_policy(
    *,
    file_diagnostic: Callable[[dict[str, Any] | None], dict[str, Any] | None],
    string_list: Callable[[Any], list[str]],
    stage_definitions: Callable[[dict[str, Any]], list[dict[str, Any]]],
    blocker_callback: Callable[[str, str, dict[str, Any]], dict[str, Any]],
) -> StageReadinessPolicy:
    from .evidence.readiness import StageReadinessPolicy

    return StageReadinessPolicy(
        file_diagnostic, string_list, stage_definitions, blocker_callback
    )


def build_automation_readiness_service(
    *,
    project_root: Path,
    has_output_checks: Callable[[], bool],
    output_checks: Callable[[Path, dict[str, Any]], Any],
    has_fingerprint: Callable[[], bool],
    fingerprint: Callable[[Path, dict[str, Any]], Any],
    has_event_paths: Callable[[], bool],
    event_paths: Callable[[Path], tuple[Path, Any]],
    latest_event: Callable[[str, set[str]], dict[str, Any] | None],
    configuration: ConfigurationProvider | None = None,
) -> AutomationReadinessService:
    from .work.automation_readiness import AutomationReadinessService

    return AutomationReadinessService(
        project_root=project_root,
        has_output_checks=has_output_checks,
        output_checks=output_checks,
        has_fingerprint=has_fingerprint,
        fingerprint=fingerprint,
        has_event_paths=has_event_paths,
        event_paths=event_paths,
        latest_event=latest_event,
        configuration=configuration,
    )


def build_work_selection_service(
    *,
    bound_selection: Callable[[str], dict[str, Any] | None],
    valid_selector: Callable[[str], bool],
    records: Callable[..., list[dict[str, Any]]],
    prefer: Callable[[list[dict[str, Any]], str], dict[str, Any] | None],
    load_run: Callable[[str], dict[str, Any]],
    load_assignment: Callable[[str], dict[str, Any]],
) -> WorkSelectionService:
    from .work.selection import WorkSelectionService

    return WorkSelectionService(
        bound_selection=bound_selection,
        valid_selector=valid_selector,
        records=records,
        prefer=prefer,
        load_run=load_run,
        load_assignment=load_assignment,
    )


def build_process_selection_service(
    *,
    project_root: Path,
    stable_ids: Callable[[Any], list[str]],
    resolve_definition: Callable[[Path, str], ResolvedDefinitionView],
    blocked: Callable[..., dict[str, Any]],
    candidates: Callable[..., list[dict[str, Any]]],
) -> ProcessSelectionService:
    from .process_catalog.selection import ProcessSelectionService

    return ProcessSelectionService(
        project_root=project_root,
        stable_ids=stable_ids,
        resolve_definition=resolve_definition,
        blocked=blocked,
        candidates=candidates,
    )


def build_process_pin_read_service(
    *,
    project_root: Path,
    flow_root: Callable[[], Path],
    snapshots: Callable[[], ProjectSnapshotReadPort],
    fingerprint: Callable[[Any], str],
    stable_ids: Callable[[Any], list[str]],
) -> ProcessPinReadService:
    from .process_catalog.pin import ProcessPinReadService

    return ProcessPinReadService(
        project_root=project_root,
        flow_root=flow_root,
        snapshots=snapshots,
        fingerprint=fingerprint,
        stable_ids=stable_ids,
    )


def build_run_completion_policy(
    *,
    accumulated_evidence: Callable[[dict[str, Any]], list[dict[str, Any]]],
    string_list: Callable[[Any], list[str]],
    gate_state: Callable[..., dict[str, Any]],
) -> RunCompletionPolicy:
    from .completion.policy import RunCompletionPolicy

    return RunCompletionPolicy(
        accumulated_evidence=accumulated_evidence,
        string_list=string_list,
        gate_state=gate_state,
    )


def build_completion_intent_validation_service(
    *,
    project_root: Path,
    fingerprint: Callable[[Any], str],
    terminal_assignment_statuses: Callable[[], set[str]],
    effective_process: Callable[[dict[str, Any]], tuple[dict[str, Any], str]],
    rel: Callable[[Path, Path], str],
    run_path: Callable[[str], Path],
    assignment_path: Callable[[str], Path],
    flow_root: Callable[[], Path],
    has_project_id: Callable[[], bool],
    project_id: Callable[[Path], Any],
) -> CompletionIntentValidationService:
    from .completion.intent_validation import CompletionIntentValidationService

    return CompletionIntentValidationService(
        project_root=project_root,
        fingerprint=fingerprint,
        terminal_assignment_statuses=terminal_assignment_statuses,
        effective_process=effective_process,
        rel=rel,
        run_path=run_path,
        assignment_path=assignment_path,
        flow_root=flow_root,
        has_project_id=has_project_id,
        project_id=project_id,
    )


def build_transition_rejection_policy(
    *, state: Callable[..., dict[str, Any]]
) -> TransitionRejectionPolicy:
    from .work.transition_rejection import TransitionRejectionPolicy

    return TransitionRejectionPolicy(state=state)


def build_work_boundary_advisory_service(
    *,
    flow_root: Callable[[], Path],
    stable_ids: Callable[[Any], list[str]],
    load_document: Callable[[Path], dict[str, Any]],
) -> WorkBoundaryAdvisoryService:
    from .work.boundary_advisory import WorkBoundaryAdvisoryService

    return WorkBoundaryAdvisoryService(
        flow_root=flow_root, stable_ids=stable_ids, load_document=load_document
    )


def build_completion_document_service(
    *,
    project_root: Path,
    run_path: Callable[[str], Path],
    has_task_index: Callable[[], bool],
    task_index: Callable[[Path, dict[str, Any]], str],
    atomic_text: Callable[[Path, str], Any],
) -> CompletionDocumentService:
    from .completion.documents import CompletionDocumentService

    return CompletionDocumentService(
        project_root=project_root,
        run_path=run_path,
        has_task_index=has_task_index,
        task_index=task_index,
        atomic_text=atomic_text,
    )


def build_completion_intent_builder(
    *,
    project_root: Path,
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
    fingerprint: Callable[[Any], str],
) -> CompletionIntentBuilder:
    from .completion.intent_builder import CompletionIntentBuilder

    return CompletionIntentBuilder(
        project_root=project_root,
        accumulated_evidence=accumulated_evidence,
        set_task_status=set_task_status,
        run_path=run_path,
        assignment_path=assignment_path,
        flow_root=flow_root,
        summary=summary,
        has_task_index=has_task_index,
        task_index=task_index,
        rel=rel,
        intent_path=intent_path,
        project_id=project_id,
        fingerprint=fingerprint,
    )


def build_completion_intent_read_service(
    *,
    run_path: Callable[[str], Path],
    intent_path: Callable[[str], Path],
    valid_id: Callable[[str], bool],
    load_document: Callable[[Path], dict[str, Any]],
    validate: Callable[[Any, dict[str, Any], dict[str, Any], Path], str | None],
) -> CompletionIntentReadService:
    from .completion.intent_read import CompletionIntentReadService

    return CompletionIntentReadService(
        run_path=run_path,
        intent_path=intent_path,
        valid_id=valid_id,
        load_document=load_document,
        validate=validate,
    )


def build_completion_intent_replay_service(
    *,
    assignment_path: Callable[[str], Path],
    run_path: Callable[[str], Path],
    flow_root: Callable[[], Path],
    atomic_yaml: Callable[[Path, dict[str, Any]], Any],
    atomic_text: Callable[[Path, str], Any],
    state: Callable[..., dict[str, Any]],
    write_projection: Callable[[dict[str, Any]], Any],
    emit: Callable[..., Any],
    intent_path: Callable[[str], Path],
) -> CompletionIntentReplayService:
    from .completion.intent_replay import CompletionIntentReplayService

    return CompletionIntentReplayService(
        assignment_path=assignment_path,
        run_path=run_path,
        flow_root=flow_root,
        atomic_yaml=atomic_yaml,
        atomic_text=atomic_text,
        state=state,
        write_projection=write_projection,
        emit=emit,
        intent_path=intent_path,
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
    *,
    fingerprint: Callable[[], Callable[[dict], str]],
    error: Callable[[], type[ValueError]],
    writer_check: Callable[[], Callable[[dict], None]],
    binding_reader: Callable[[], CancellationBindingReader],
    work: Callable[[], CancellationWorkWriter],
    record_loader: Callable[[], Callable[[Path], dict]],
    project_root: Callable[[], Path],
    event_paths: Callable[[], Callable[[Path], tuple[Path, ...]]],
    event_reader: Callable[[], CancellationEventReader],
) -> CancellationReplayService:
    from .work.cancellation_replay import CancellationReplayService

    return CancellationReplayService(
        fingerprint=fingerprint,
        error=error,
        writer_check=writer_check,
        binding_reader=binding_reader,
        work=work,
        record_loader=record_loader,
        project_root=project_root,
        event_paths=event_paths,
        event_reader=event_reader,
    )


def build_continuation_publication_service(
    *,
    record_path: Callable[[], Callable[[str], Path]],
    selection_path: Callable[[], Callable[[str], Path]],
    validate_id: Callable[[], Callable[[object], str]],
    record_loader: Callable[[], Callable[[Path], dict]],
    binding_reader: Callable[[], ContinuationBindingReader],
    waiting_reader: Callable[[], Callable[[dict], dict]],
    status_reader: Callable[[], ContinuationStatusReader],
    run_lock: Callable[[], Callable[[str], AbstractContextManager[Any]]],
    record_lock: Callable[[], Callable[[Path], AbstractContextManager[Any]]],
    publish_document: Callable[[], ContinuationDocumentWriter],
    clock: Callable[[], Callable[[], str]],
    error: Callable[[], type[ValueError]],
) -> ContinuationPublicationService:
    from .work.continuation_publication import ContinuationPublicationService

    return ContinuationPublicationService(
        record_path=record_path,
        selection_path=selection_path,
        validate_id=validate_id,
        record_loader=record_loader,
        binding_reader=binding_reader,
        waiting_reader=waiting_reader,
        status_reader=status_reader,
        run_lock=run_lock,
        record_lock=record_lock,
        publish_document=publish_document,
        clock=clock,
        error=error,
    )


def build_work_record_catalog_service(
    *,
    record_reader: Callable[[], WorkRecordReadPort | None],
    inventory_factory: Callable[[], WorkCatalogInventoryFactory],
    flow_root: Callable[[], Callable[[], Path]],
    document_loader: Callable[[], Callable[[Path], dict[str, Any]]],
    identifier_pattern: Callable[[], Pattern[str]],
    intent_reader: Callable[[], CompletionIntentLookup],
    active_assignment_statuses: Callable[[], Collection[str]],
    active_run_statuses: Callable[[], Collection[str]],
    work_metadata: Callable[[], WorkMetadataReadPass] | None = None,
    intent_path: Callable[[str], Path] | None = None,
) -> WorkRecordCatalogService:
    from .work.record_catalog import WorkRecordCatalogService

    return WorkRecordCatalogService(
        record_reader=record_reader,
        inventory_factory=inventory_factory,
        flow_root=flow_root,
        document_loader=document_loader,
        identifier_pattern=identifier_pattern,
        intent_reader=intent_reader,
        active_assignment_statuses=active_assignment_statuses,
        active_run_statuses=active_run_statuses,
        work_metadata=work_metadata,
        intent_path=intent_path,
    )


def build_work_completion_request_service(
    *,
    work_selector: Callable[[], CompletionWorkSelector],
    blocked_result: Callable[[], Callable[[str], dict[str, Any]]],
    process_reader: Callable[
        [], Callable[[dict[str, Any]], tuple[dict[str, Any], str]]
    ],
    outcomes_reader: Callable[
        [], Callable[[dict[str, Any], str], list[dict[str, Any]]]
    ],
    state_reader: Callable[[], CompletionStateReader],
    run_blockers: Callable[
        [],
        Callable[
            [dict[str, Any], dict[str, Any], dict[str, Any]], list[dict[str, Any]]
        ],
    ],
    intent_reader: Callable[[], CompletionIntentReader],
    completion_readiness: Callable[[], CompletionReadinessReader],
    transition: Callable[[], CompletionTransition],
) -> WorkCompletionRequestService:
    from .completion.request import WorkCompletionRequestService

    return WorkCompletionRequestService(
        work_selector=work_selector,
        blocked_result=blocked_result,
        process_reader=process_reader,
        outcomes_reader=outcomes_reader,
        state_reader=state_reader,
        run_blockers=run_blockers,
        intent_reader=intent_reader,
        completion_readiness=completion_readiness,
        transition=transition,
    )
