#!/usr/bin/env python3
"""ProcessForge MVP CLI for workplace/project init and doctor checks."""

from __future__ import annotations

import argparse
import copy
import csv
import contextlib
import fnmatch
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import socket
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from urllib.request import url2pathname, urlopen

if TYPE_CHECKING:
    from processforge_core.work.resources import WorkResourceService
    from processforge_core.resources.local_search import ResourceSearchIndex
    from processforge_core.configuration import ConfigService


def _bootstrap_repo_src() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    src_value = str(src_root)
    if src_value not in sys.path:
        first_entry = Path(sys.path[0] or ".").resolve() if sys.path else None
        tools_root = (repo_root / "tools").resolve()
        sys.path.insert(1 if first_entry == tools_root else 0, src_value)
    return repo_root


ROOT = _bootstrap_repo_src()

from processforge_core.chat.writer import ChatTranscriptWriter
from processforge_core.process_catalog.profile_packs import OfficialPackProfileReader
from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.project.initialization_discovery import ProjectDiscoveryReader
from processforge_core.project.file_templates import ProjectFileTemplateBuilder
from processforge_core.project.initialization_discovery import ProjectResourceMatcher
from processforge_core.project.runtime_launchers import ProjectRuntimeLauncherBuilder
from processforge_core.maintenance.release_plan import ReleaseCommandPlanBuilder
from processforge_core.maintenance.release_manifest import ReleaseManifestPolicy
from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher
from processforge_core.project.workplace_templates import WorkplaceFileBuilder
from processforge_core.project.workplace_terms import WorkplaceTermsBuilder
import processforge_core.common.markdown as _core_common_markdown
import processforge_core.common.release_identity as _core_common_release_identity
import processforge_core.maintenance.release_commands as _core_maintenance_release_commands
import processforge_core.project.configuration_inputs as _core_project_configuration_inputs
import processforge_core.project.initialization_discovery as _core_project_initialization_discovery

from processforge_core.agents.presence import AgentPresenceReader
from processforge_core.chat.transcripts import ChatTranscriptReader
from processforge_core.common.ndjson import NdjsonReader
from processforge_core.common.paths import path_matches_pattern
from processforge_core.project.classification import ProjectClassifierRulePolicy
from processforge_core.work.context_documents import ContextContractInputs
from processforge_core.work.scope_conflicts import ScopeConflictService
from processforge_core.common.digests import FileDigestReader
from processforge_core.project.metadata import ProjectMetadataReader as _ProjectMetadataReader
from processforge_core.project.readiness import ProjectContextReadinessPolicy as _ProjectContextReadinessPolicy
from processforge_core.project.context_policy import ProjectContextPolicy as _ProjectContextPolicy
from processforge_core.project.resource_snapshot import ResourceSnapshotRules as _ResourceSnapshotRules
from processforge_core.project.knowledge_selection import KnowledgeResourceSelector as _KnowledgeResourceSelector
from processforge_core.project.snapshot_sources import ProjectSnapshotSourcesReader as _ProjectSnapshotSourcesReader, local_workplace_manifest_reference as _local_workplace_manifest_reference
from processforge_core.project.source_check import ProjectSnapshotSourceCheckService
from processforge_core.project.context_rules import ProjectContextRules as _ProjectContextRules
from processforge_core.project.snapshot_rendering import ProjectContextSnapshotRenderer as _ProjectContextSnapshotRenderer
from processforge_core.project.capability_registry import CapabilityRegistryReader as _CapabilityRegistryReader
from processforge_core.project.context_sources import ProjectContextSourcesReader
from processforge_core.resources.versioning import ResourceVersionPolicy
from processforge_core.project.resolved_comparison import ProjectSnapshotResolvedComparison
from processforge_core.process_catalog.official_read import OfficialProcessPackReader as _OfficialProcessPackReader
from processforge_core.process_catalog.artifacts import ProcessArtifactDeclarationPolicy
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.sqlite_storage import JournalError
from processforge_core.configuration.parameters import ParameterMergePolicy
from processforge_core.configuration.resolution import ConfigurationResolver

from processforge_core.common.checks import Check, check
from processforge_core.common.ids import safe_id, title_from_id
from processforge_core.common.values import string_list
from processforge_core.process_catalog.authoring import ProcessAuthoringDefinitionBuilder
from processforge_core.process_catalog.evolution import (
    EVOLVE_MODES,
    EVOLVE_TIMINGS,
    EVOLVE_SCOPES,
    EVOLVE_CANDIDATE_TARGETS,
    ProcessEvolutionPolicy,
)
from processforge_core.runtime.drivers import (
    RESERVED_WORKER_ENV_KEYS,
    RUNTIME_DRIVER_PLACEHOLDERS,
    RuntimeDriverDefinitionPolicy,
)
from processforge_core.maintenance.sites import (
    UPDATE_SOURCE_PUBLIC_KEYS,
    UPDATE_SOURCE_LOCAL_KEYS,
    UpdateSitePolicy,
)

_process_evolution_policy = ProcessEvolutionPolicy()
_process_authoring_definition_builder = ProcessAuthoringDefinitionBuilder()
_runtime_driver_definition_policy = RuntimeDriverDefinitionPolicy()
_update_site_policy = UpdateSitePolicy()
from processforge_core.process_catalog.coordination import (
    PROCESS_COORDINATION_MODES,
    process_coordination_requirements,
)
from processforge_core.process_catalog.presentation import ProcessAuthoringRenderer
from processforge_core.runtime.catalog import RuntimeDriverCatalogReader
from processforge_core.evolution.candidates import (
    EVOLVE_APPLICABILITY_SCOPES,
    EVOLVE_GENERALIZATION_LEVELS,
    EVOLVE_PROMOTION_STATUSES,
    KnowledgeCandidateTargetingPolicy,
)
from processforge_core.maintenance.versions import UpdateVersionSelectionPolicy
from processforge_core.maintenance.presentation import UpdateAssessmentRenderer

_process_authoring_renderer = ProcessAuthoringRenderer()
_runtime_driver_catalog_reader = RuntimeDriverCatalogReader(ROOT)
_knowledge_candidate_targeting_policy = KnowledgeCandidateTargetingPolicy()
_update_version_selection_policy = UpdateVersionSelectionPolicy()
_update_assessment_renderer = UpdateAssessmentRenderer()
from processforge_core.common.privacy import (
    BACKSLASH,
    LOCAL_PATH_PATTERNS,
    SECRET_VALUE_PATTERNS,
    is_public_path_safe,
    contains_secret_value,
)
from processforge_core.project.coordination import (
    COORDINATION_PROJECT_MODES,
    WORKPLACE_DEFAULT_PROJECT_MODES,
    DIRECTOR_OFFICE_DEFAULTS,
    ProjectCoordinationReader,
)
from processforge_core.evolution.privacy import EvolvePrivacyPolicy
from processforge_core.maintenance.source_contracts import (
    UPDATE_SUBJECT_TYPES,
    CONTROL_CHAR_RE,
    ENV_REFERENCE_RE,
    UpdateSourceContractPolicy,
)

_project_coordination_reader = ProjectCoordinationReader()
_evolve_privacy_policy = EvolvePrivacyPolicy()
_update_source_contract_policy = UpdateSourceContractPolicy()
from processforge_core.common.values import list_value
from processforge_core.work.outputs import WorkOutputPolicy
from processforge_core.project.detection import ProjectDetectionService
from processforge_core.runtime.environment import WorkerEnvironmentPolicy
from processforge_core.maintenance.schema_checks import UpdateSchemaChecks

_work_output_policy = WorkOutputPolicy()
_project_detection_service = ProjectDetectionService()
_worker_environment_policy = WorkerEnvironmentPolicy()
_update_schema_checks = UpdateSchemaChecks(ROOT)
from processforge_core.work.paths import WorkPaths
from processforge_core.runtime.command import WorkerCommandBuilder
from processforge_core.project.platforms import PlatformContractReader
from processforge_core.maintenance.documents import UpdateDocumentReader

_work_paths = WorkPaths()
_worker_command_builder = WorkerCommandBuilder(ROOT)
_platform_contract_reader = PlatformContractReader(ROOT)
_update_document_reader = UpdateDocumentReader(ROOT)
from processforge_core.common.json_io import json_read
from processforge_core.common.privacy import public_yaml_has_private_path
from processforge_core.runtime.selection import RuntimeDriverSelectionService
from processforge_core.project.platform_policy import PlatformContractPolicy
from processforge_core.process_catalog.validation import (
    ProcessAuthoringValidationService,
    ERROR_WORKFLOW_MODES,
    ERROR_WORKFLOW_FALLBACKS,
    ITERATION_KINDS,
)

_runtime_driver_selection_service = RuntimeDriverSelectionService(ROOT)
_platform_contract_policy = PlatformContractPolicy(_platform_contract_reader)
_process_authoring_validation_service = ProcessAuthoringValidationService()
from processforge_core.resources.project_packages import ProjectPackageCatalogReader, PackageRootResolution
from processforge_core.project.platform_resolution import PlatformContractResolver
from processforge_core.process_catalog.semantics import ProcessSemanticPolicy
from processforge_core.presentation.process_parity import ProcessParityRenderer
from processforge_core.runtime.worker_plans import WorkerPlanPolicy
from processforge_core.common.values import parameter_payload

_project_package_catalog_reader = ProjectPackageCatalogReader(ROOT)
_platform_contract_resolver = PlatformContractResolver(ROOT)
_process_semantic_policy = ProcessSemanticPolicy()
_process_parity_renderer = ProcessParityRenderer()
_worker_plan_policy = WorkerPlanPolicy()
from processforge_core.project.platform_selection import ProjectPlatformSelectionService
from processforge_core.project.classification import normalize_hint, hint_matches
from processforge_core.common.values import registry_ids
from processforge_core.maintenance.registries import UpdateRegistryReader
from processforge_core.process_catalog.contracts import ProcessContractValidationService, ProcessRouteDocumentReader, HANDOFF_MODES
from processforge_core.process_catalog.service import process_is_public_stable

_project_platform_selection_service = ProjectPlatformSelectionService(ROOT)
_update_registry_reader = UpdateRegistryReader(ROOT)
_process_contract_validation_service = ProcessContractValidationService(ROOT)
_process_route_document_reader = ProcessRouteDocumentReader()
from processforge_core.runtime.worker_validation import WorkerPlanValidationService
from processforge_core.project.hooks import HookConfigurationReader
from processforge_core.common.record_validation import RecordValidationPolicy
from processforge_core.process_catalog.routes import ProcessRouteService
from processforge_core.process_catalog.handoffs import HandoffDocumentReader
from processforge_core.maintenance.validation import UpdateDocumentValidationService
from processforge_core.work.context_documents import WORKSPACE_ACCESS_KEYS

_worker_plan_validation_service = WorkerPlanValidationService(ROOT)
_hook_configuration_reader = HookConfigurationReader()
_record_validation_policy = RecordValidationPolicy()
_process_route_service = ProcessRouteService(ROOT)
_handoff_document_reader = HandoffDocumentReader()
_update_document_validation_service = UpdateDocumentValidationService(ROOT)
from processforge_core.project.platform_documents import PlatformDocumentBuilder
from processforge_core.project.registry_checks import WorkplaceRegistryValidationService
from processforge_core.process_catalog.audit import BuiltinProcessCatalogAuditService
from processforge_core.project.setup import WorkplaceSetupProposalBuilder
from processforge_core.common.text import ensure_trailing_newline, check_with_hint
from processforge_core.common.yaml_dump import dump_yaml, format_scalar
from processforge_core.process_catalog.service import process_catalog_contexts

_platform_document_builder = PlatformDocumentBuilder()
_workplace_registry_validation_service = WorkplaceRegistryValidationService(ROOT)
_builtin_process_catalog_audit_service = BuiltinProcessCatalogAuditService(ROOT)
_workplace_setup_proposal_builder = WorkplaceSetupProposalBuilder()
from processforge_core.project.registry_write import WorkplaceRegistryWriter
from processforge_core.project.templates import TemplateCatalogService
from processforge_core.project.platform_validation import PlatformContractValidationService
from processforge_core.project.requirements import PlatformDependencyPreflightService
from processforge_core.common.values import upsert_resource
from processforge_core.common.policies import policy_entries, policy_id_matches

_workplace_registry_writer = WorkplaceRegistryWriter(ROOT)
_template_catalog_service = TemplateCatalogService(ROOT)
_platform_contract_validation_service = PlatformContractValidationService(ROOT)
_platform_dependency_preflight_service = PlatformDependencyPreflightService(ROOT)
from processforge_core.resources.records import ResourceRecordService
from processforge_core.resources.package_checks import KnowledgePackageValidationService
from processforge_core.resources.index_checks import KnowledgeResourceIndexService
from processforge_core.work.worker_assignment import WorkerAssignmentService
from processforge_core.common.paths import path_is_relative_to
from processforge_core.resources.records import HEAVY_RESOURCE_KINDS

_resource_record_service = ResourceRecordService()
_knowledge_package_validation_service = KnowledgePackageValidationService(ROOT)
_knowledge_resource_index_service = KnowledgeResourceIndexService(ROOT)
_worker_assignment_service = WorkerAssignmentService()
from processforge_core.authoring.plans import AuthoringPlanRenderer
from processforge_core.authoring.inputs import AuthoringInputService
from processforge_core.process_catalog.examples import ProcessAuthoringExampleBuilder
from processforge_core.maintenance.candidate_read import UpdateCandidateReader
from processforge_core.authoring.plans import AuthoringWrite, AuthoringEffect, AuthoringPlan
from processforge_core.process_catalog.examples import process_yaml_content
from processforge_core.common.status import aggregate_status

_authoring_plan_renderer = AuthoringPlanRenderer()
_authoring_input_service = AuthoringInputService()
_process_authoring_example_builder = ProcessAuthoringExampleBuilder()
_update_candidate_reader = UpdateCandidateReader(ROOT)
from processforge_core.project.session_read import ProjectSessionReadService
from processforge_core.configuration.specializations import SpecializationCatalogReader
from processforge_core.evolution.validation import KnowledgeCandidateValidationService
from processforge_core.maintenance.transfer import UpdateTransferService
from processforge_core.common.text import COLON_WS
from processforge_core.evolution.validation import EVOLVE_CANDIDATE_CATEGORIES

_project_session_read_service = ProjectSessionReadService()
_specialization_catalog_reader = SpecializationCatalogReader(ROOT)
_knowledge_candidate_validation_service = KnowledgeCandidateValidationService()
_update_transfer_service = UpdateTransferService(ROOT)
from processforge_core.authoring.journals import AuthoringJournalStore
from processforge_core.configuration.parameter_sources import ParameterSourceService
from processforge_core.project.report_read import ReportProjectionReader
from processforge_core.project.initialization_inputs import ProjectInitializationInputs
from processforge_core.project.initialization_inputs import PROCESSFORGE_CORE_PROJECT_TYPES
from processforge_core.project.initialization_inputs import META_PROJECT_TYPES

_authoring_journal_store = AuthoringJournalStore()
_parameter_source_service = ParameterSourceService()
_report_projection_reader = ReportProjectionReader()
_project_initialization_inputs = ProjectInitializationInputs()
_file_digests = FileDigestReader()
_project_classifier_rule_policy = ProjectClassifierRulePolicy()
_process_artifact_declaration_policy = ProcessArtifactDeclarationPolicy()
_process_event_journal = ProcessEventJournal()
_context_contract_inputs = ContextContractInputs()
_resource_version_policy = ResourceVersionPolicy()
_project_snapshot_resolved_comparison = ProjectSnapshotResolvedComparison(versions=_resource_version_policy)
from processforge_core.process_catalog import (
    ProcessCatalogContext,
    ProcessDefinitionRef,
    official_process_definition_refs as catalog_official_process_definition_refs,
    process_catalog_metadata,
    process_catalog_entries as catalog_process_catalog_entries,
    process_catalog_role as catalog_process_catalog_role,
    process_definition_exists as catalog_process_definition_exists,
    process_root_candidates as catalog_process_root_candidates,
    process_root_yaml_files as catalog_process_root_yaml_files,
    require_official_process_active as catalog_require_official_process_active,
    resolve_process_definition as catalog_resolve_process_definition,
)
from processforge_core.process_execution import ProcessExecutionService, project_process_selection, project_specialization_selection
from processforge_core.project import initialization as project_initialization
from processforge_core import diagnostics
from pf_cli.application import CliApplication
from pf_cli.commands.agent_entry import AgentEntryCommand, AgentStartPromptCommand
from pf_cli.commands.agent_actions import ActionsCommand
from pf_cli.commands.configuration import ConfigurationCommand
from pf_cli.commands.search_index import (
    SearchIndexStatusCommand,
    SearchIndexRefreshCommand,
    SearchIndexRebuildCommand,
    SearchIndexDoctorCommand,
    SearchIndexTickCommand,
)
from pf_cli.commands.work import (
    WorkStartCommand,
    WorkStateCommand,
    WorkResourceReadCommand,
    WorkTransitionCommand,
)
from pf_cli.parsers.agent_entry import AgentEntryCommandParser
from pf_cli.parsers.agent_actions import ActionsCommandParser
from pf_cli.parsers.agents import (
    AgentPresenceCommandParser,
    AgentLeaseCommandParser,
)
from pf_cli.parsers.authoring import ProcessAuthoringCommandParser
from pf_cli.parsers.catalog import ProcessCatalogCommandParser
from pf_cli.parsers.configuration import ConfigurationCommandParser
from pf_cli.parsers.context import ProjectContextCommandParser
from pf_cli.parsers.continuation import ContinuationCommandParser
from pf_cli.parsers.coordination import (
    DirectorCommandParser,
    OrchestrationCommandParser,
    HandoffCommandParser,
)
from pf_cli.parsers.diagnostics import DiagnosticsCommandParser
from pf_cli.parsers.distribution import (
    DeliveryCommandParser,
    CoreUpdateCommandParser,
)
from pf_cli.parsers.egress import EgressCommandParser
from pf_cli.parsers.events import (
    HookCommandParser,
    ChatCommandParser,
)
from pf_cli.parsers.evolution import EvolutionCommandParser
from pf_cli.parsers.execution import (
    RuntimeDriverCommandParser,
    WorkerRunCommandParser,
    ExecutionInspectorCommandParser,
)
from pf_cli.parsers.host import (
    CodexMcpCommandParser,
    RuntimeHostCommandParser,
)
from pf_cli.parsers.knowledge import KnowledgeCommandParser
from pf_cli.parsers.lifecycle import (
    RunCommandParser,
    TaskCommandParser,
    IterationCommandParser,
)
from pf_cli.parsers.monitor import MonitorCommandParser
from pf_cli.parsers.navigation import ResourceIndexCommandParser
from pf_cli.parsers.project import ProjectCommandParser
from pf_cli.parsers.resources import (
    TemplateCommandParser,
    ProviderCommandParser,
    SpecializationCommandParser,
    ProjectOverrideCommandParser,
    PlatformCommandParser,
)
from pf_cli.parsers.runtime import RuntimeCommandParser
from pf_cli.parsers.update import UpdateCommandParser
from pf_cli.parsers.work import WorkCommandParser
from pf_cli.parsers.workplace import WorkplaceCommandParser
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.documents.answers import AnswersDocumentReader as _AnswersDocumentReader
from processforge_subprocess import diagnostic_text, format_command as format_subprocess_command, run_command as run_subprocess_command

from processforge_core.agents.registry import AgentWorkplaceRegistry
from processforge_core.chat.export import ChatExportService
from processforge_core.agents.hook_policy import HookDispatchPolicy
from processforge_core.work.orchestration_config import OrchestrationConfigService
from processforge_core.project.capability_resolution import ProjectCapabilityResolution
from processforge_core.project.classifier_sources import ProjectClassifierSourceReader
from processforge_core.project.coordination_state import ProjectCoordinationStateService
from processforge_core.project.overrides import ProjectOverrideReader
from processforge_core.project.scan_policy import ProjectScanPolicy
from processforge_core.maintenance.public_source_checks import PublicSourcePolicy
from processforge_core.maintenance.release_provenance import ReleaseGitProvenance
from processforge_core.maintenance.release_sources import ReleaseSourcePolicy
from processforge_core.work.consistency import RunTaskConsistencyService
from processforge_core.work.consistency import RunTaskInputReader
from processforge_core.agents.session_metadata import SessionMetadataWriter
from processforge_core.runtime.supervisor_inputs import SupervisorInputService
from processforge_core.runtime.supervisor_inputs import SupervisorStateInputs
from processforge_core.agents.telemetry import TelemetryEventService
from processforge_core.runtime.observation_inputs import WorkerObservationInputService
from processforge_core.resources.registries import WorkplaceRegistryReader
from processforge_core.resources.workplace_events import WorkplaceResourceEventJournal
from processforge_core.project.setup_answers import WorkplaceSetupAnswers
from processforge_core.work.workspace_refs import WorkspaceAccessReferenceService
import processforge_core.common.clock as _core_common_clock
import processforge_core.common.json_io as _core_common_json_io
import processforge_core.common.yaml_io as _core_common_yaml_io
import processforge_core.maintenance.public_source_checks as _core_maintenance_public_source_checks
import processforge_core.maintenance.release_provenance as _core_maintenance_release_provenance
import processforge_core.maintenance.release_sources as _core_maintenance_release_sources
import processforge_core.project.overrides as _core_project_overrides
import processforge_core.project.scan_policy as _core_project_scan_policy
import processforge_core.resources.buckets as _core_resources_buckets
import processforge_core.resources.registries as _core_resources_registries
import processforge_core.runtime.observation_inputs as _core_runtime_observation_inputs
import processforge_core.work.consistency as _core_work_consistency


PROJECT_FLOW_ROOT = ".pf"
PROCESSFORGE_VERSION = "1.2.0"
PROCESSFORGE_SPEC_VERSION = "1.0"
PROCESSFORGE_SCHEMA_BUNDLE_VERSION = "1.0"

PROJECT_PRIVATE_GITIGNORE = [
    ".codex/hooks.json",
    ".pf/process-forge.local.yaml",
    ".pf/runtime/",
    ".pf/private-notes/",
    ".pf/cache/",
    ".secrets/",
    "*.tmp",
    "*.bak",
]

PROJECT_FLOW_DIRS = [
    "processes",
    "authoring",
    "authoring/processes",
    "packages",
    "templates",
    "runs",
    "assignments",
    "artifacts",
    "artifacts/runs",
    "contexts",
    "contexts/assignment-capsules",
    "continuations",
    "registries",
    "logs",
    "handoffs",
    "handoffs/runs",
    "reviews",
    "reviews/runs",
    "adr",
    "schemas",
    "runtime/cache",
    "runtime/telemetry",
    "runtime/events",
    "runtime/chat/transcripts",
    "runtime/hooks/outbox",
    "runtime/hooks/results",
    "runtime/queue",
    "runtime/sessions",
    "runtime/agent-runs",
    "runtime/agent-ledger",
    "runtime/agent-presence",
    "runtime/agent-leases",
    "runtime/supervisor",
    "runtime/registries",
]



GLOBAL_AGENT_SECTION_START = "<!-- PROCESSFORGE:START -->"
GLOBAL_AGENT_SECTION_END = "<!-- PROCESSFORGE:END -->"

GLOBAL_AGENT_SECTION = f"""{GLOBAL_AGENT_SECTION_START}
## ProcessForge

Apply this section when:
- the user mentions ProcessForge;
- the user says "по флоу";
- the user points to a `.pf/` directory;
- the project contains `.pf/process-forge.yaml`;
- an assignment references ProcessForge.

Rules:
1. Do not load all knowledge from this file.
2. Read the project flow entrypoint: `.pf/AGENTS.md`.
3. Read `.pf/process-forge.yaml`.
4. Call `pf.context` with the project root; use the current snapshot only as a
   file-only fallback when MCP is unavailable.
5. Use `pf.search`, `pf.resolve`, and `pf.work.start` as the normal high-level
   project path.
6. Never write secrets or local absolute paths to public files.
7. Follow assignment and immutable-capsule boundaries.
8. Do not install, start, or repair PF Runtime, MCP, host hooks, or Agent Ledger
   during ordinary project work; report operator-level infrastructure blockers.
9. Put arbitrary agent scratch only in the project's `.pf/tmp/`. Durable artifacts
   keep their established locations; atomic replacement staging stays beside its
   destination. Age alone never authorizes deletion.
{GLOBAL_AGENT_SECTION_END}
"""

REQUIRED_TELEMETRY_EVENTS = [
    "session_start",
    "snapshot_check",
    "source_read",
    "assignment_loaded",
    "capability_check",
    "tool_selected",
    "tool_invoked",
    "tool_failed",
    "mcp_check",
    "fallback_used",
    "conflict_detected",
    "file_scope_checked",
    "artifact_written",
    "review_requested",
    "handoff_created",
    "doctor_run",
    "session_end",
]

REQUIRED_PROCESSFORGE_EVENT_TYPES = [
    "session.started",
    "session.ended",
    "session.message.recorded",
    "chat.message.recorded",
    "process.started",
    "process.completed",
    "stage.started",
    "stage.completed",
    "process.stage.started",
    "process.stage.completed",
    "process.stage.blocked",
    "process.stage.transitioned",
    "assignment.created",
    "assignment.started",
    "assignment.completed",
    "artifact.created",
    "artifact.updated",
    "review.requested",
    "review.completed",
    "gate.passed",
    "gate.failed",
    "tool.invoked",
    "tool.failed",
    "mcp.invoked",
    "mcp.failed",
    "hook.dispatched",
    "hook.failed",
    "context.snapshot.refreshed",
    "context.snapshot.stale",
    "capability.missing",
    "knowledge.resource.add.requested",
    "knowledge.resource.added",
    "knowledge.package.updated",
    "snapshot.stale",
    "template.add.requested",
    "template.added",
    "template.updated",
    "tool.registered",
    "tool.healthcheck.passed",
    "tool.healthcheck.failed",
    "mcp.registered",
    "mcp.healthcheck.passed",
    "mcp.healthcheck.failed",
    "platform.contract.updated",
    "path.constant.added",
    "path.constant.updated",
    "registry.path.added",
    "knowledge.resource.path.resolved",
    "knowledge.resource.path.unresolved",
    "project.snapshot.path_redacted",
    "doctor.path.failed",
    "package.root.resolved",
    "package.root.missing",
    "package.root.unavailable",
    "package.created",
    "package.updated",
    "package.index.updated",
    "package.doctor.failed",
    "package.duplicate.detected",
    "workplace.initialization.started",
    "workplace.structure.created",
    "workplace.path_constants.created",
    "workplace.registry.created",
    "workplace.doctor.passed",
    "workplace.doctor.failed",
    "workplace.initialization.completed",
    "workplace.setup.started",
    "workplace.setup.reviewed",
    "workplace.setup.applied",
    "project.onboarding.started",
    "project.flow_root.created",
    "project.platform.detected",
    "project.snapshot.refreshed",
    "project.doctor.passed",
    "project.doctor.failed",
    "project.onboarding.completed",
    "agent.start_prompt.generated",
    "launcher.project_runtime.created",
    "template.authoring.started",
    "template.created",
    "template.registered",
    "template.doctor.passed",
    "template.doctor.failed",
    "template.authoring.completed",
    "knowledge_package.authoring.started",
    "knowledge_package.created",
    "knowledge_package.resource_index.created",
    "knowledge_package.doctor.passed",
    "knowledge_package.doctor.failed",
    "knowledge_package.authoring.completed",
    "platform.authoring.started",
    "platform.contract.created",
    "platform.contract.linked",
    "platform.contract.doctor.passed",
    "platform.contract.doctor.failed",
    "platform.authoring.completed",
    "run.created",
    "run.started",
    "run.updated",
    "run.summary.created",
    "run.completed",
    "run.failed",
    "run.cancelled",
    "run.doctor.passed",
    "run.doctor.failed",
    "orchestrator.plan.created",
    "orchestrator.plan.reviewed",
    "orchestrator.plan.applied",
    "worker.launch_prompt.created",
    "task.created",
    "task.started",
    "task.updated",
    "task.completed",
    "task.failed",
    "task.cancelled",
    "task.doctor.passed",
    "task.doctor.failed",
    "iteration.added",
    "iteration.started",
    "iteration.completed",
    "iteration.failed",
    "process_authoring.started",
    "process_authoring.answers.created",
    "process_authoring.draft.created",
    "process_authoring.logic_review.created",
    "process_authoring.applied",
    "process_authoring.completed",
    "process_authoring.failed",
    "process.created",
    "process.doctor.passed",
    "process.doctor.failed",
    "authoring_parity.started",
    "authoring_parity.process.checked",
    "authoring_parity.resource.checked",
    "authoring_parity.warning",
    "authoring_parity.failed",
    "authoring_parity.completed",
]




PATH_CONSTANT_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")




@dataclass
class WriteResult:
    path: Path
    status: str
    target: Path








AUTHORING_FAILURE_INJECTOR: Any = None


def authoring_failure_point(phase: str, plan: AuthoringPlan, write: AuthoringWrite | None = None) -> None:
    callback = AUTHORING_FAILURE_INJECTOR
    if callback is not None:
        callback(phase, plan, write)




















def preflight_authoring_plan(plan: AuthoringPlan) -> None:
    incomplete = _authoring_input_service.incomplete_journals(plan.runtime_root)
    if incomplete:
        raise SystemExit(
            "FAIL: incomplete authoring transaction blocks mutation: "
            + ", ".join(str(path) for path in incomplete)
        )
    writes = [*plan.authoritative_writes, *plan.registry_writes]
    destinations = [write.destination.resolve() for write in writes]
    if len(destinations) != len(set(destinations)):
        raise SystemExit("FAIL: authoring plan contains duplicate destinations")
    for write in writes:
        _authoring_input_service.parent_types(write.destination)
        if write.operation == "delete":
            if not write.destination.is_file():
                raise SystemExit(f"FAIL: authoring delete source missing: {write.destination}")
            continue
        if write.content is None:
            raise SystemExit(f"FAIL: authoring write has no content: {write.destination}")
        if write.destination.exists() and not write.allow_replace:
            raise SystemExit(f"FAIL: authoring destination already exists: {write.destination}")
    for callback in plan.validation_callbacks:
        callback(plan, None)




def render_authoring_dry_run(plan: AuthoringPlan, root: Path) -> None:
    preflight_authoring_plan(plan)
    _authoring_plan_renderer.render(plan, root)


def stage_authoring_plan(plan: AuthoringPlan) -> tuple[dict[str, Any], dict[Path, Path]]:
    transaction_root = _authoring_input_service.transaction_root(plan)
    staged_root = transaction_root / "staged"
    backup_root = transaction_root / "backups"
    journal: dict[str, Any] = {
        "schema_version": 1,
        "transaction_id": plan.transaction_id,
        "command": plan.command,
        "state": "preparing",
        "created_at": _core_common_clock.now_utc(),
        "writes": [],
        "created_directories": [],
        "completed": [],
        "post_commit_effects": [],
    }
    for index, effect in enumerate(plan.post_commit_effects):
        effect_id = f"{plan.transaction_id}:{index + 1:04d}:{safe_id(effect.kind, 'effect')}"
        journal["post_commit_effects"].append(
            {
                "effect_id": effect_id,
                "label": effect.label,
                "kind": effect.kind,
                "payload": effect.payload,
                "destination": effect.destination,
                "role": effect.role,
                "operation": effect.operation,
                "condition": effect.condition,
                "executable": bool(effect.executable),
                "state": "pending" if effect.executable else "not_executable",
                "attempts": 0,
                "last_error": None,
            }
        )
    _authoring_journal_store.write(plan, journal)
    authoring_failure_point("after_journal_prepare", plan)
    staged: dict[Path, Path] = {}
    for index, write in enumerate([*plan.authoritative_writes, *plan.registry_writes]):
        staged_path = staged_root / f"{index:04d}.content"
        backup_path = backup_root / f"{index:04d}.preimage"
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        if write.operation != "delete":
            assert write.content is not None
            staged_path.write_bytes(write.content)
            staged[write.destination] = staged_path
        journal["writes"].append(
            {
                "destination": str(write.destination),
                "role": write.role,
                "operation": write.operation,
                "pre_exists": write.destination.is_file(),
                "pre_sha256": _file_digests.sha256_optional_file(write.destination),
                "staged_sha256": _file_digests.sha256_bytes(write.content) if write.content is not None else None,
                "staged_path": str(staged_path) if write.operation != "delete" else None,
                "backup_path": str(backup_path),
                "published": False,
            }
        )
        _authoring_journal_store.write(plan, journal)
        authoring_failure_point(f"after_staged_item:{index + 1}", plan, write)
    return journal, staged


def validate_staged_authoring_plan(
    plan: AuthoringPlan,
    journal: dict[str, Any],
    staged: dict[Path, Path],
) -> None:
    for write in [*plan.authoritative_writes, *plan.registry_writes]:
        if write.operation == "delete":
            continue
        staged_path = staged[write.destination]
        if _file_digests.sha256_optional_file(staged_path) != _file_digests.sha256_bytes(write.content or b""):
            raise RuntimeError(f"staged authoring hash mismatch: {write.destination}")
    for callback in plan.validation_callbacks:
        callback(plan, staged)
    journal["state"] = "prepared"
    _authoring_journal_store.write(plan, journal)




def publish_authoring_write(
    plan: AuthoringPlan,
    write: AuthoringWrite,
    record: dict[str, Any],
    staged: dict[Path, Path],
    journal: dict[str, Any],
) -> None:
    backup = Path(str(record["backup_path"]))
    if write.destination.is_file():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(write.destination, backup)
    for directory in _authoring_input_service.parent_chain(write.destination):
        directory.mkdir()
        journal["created_directories"].append(str(directory))
    if write.operation == "delete":
        write.destination.unlink()
    else:
        staged_path = staged[write.destination]
        temporary = write.destination.with_name(f".{write.destination.name}.{plan.transaction_id}.tmp")
        shutil.copy2(staged_path, temporary)
        os.replace(temporary, write.destination)
    record["published"] = True
    journal["completed"].append(str(write.destination))
    _authoring_journal_store.write(plan, journal)


def authoring_restore_record(record: dict[str, Any], transaction_id: str) -> list[str]:
    errors: list[str] = []
    destination = Path(str(record.get("destination") or ""))
    backup = Path(str(record.get("backup_path") or ""))
    try:
        if record.get("pre_exists"):
            expected = record.get("pre_sha256")
            if not backup.is_file():
                return [f"missing backup for {destination}"]
            if expected and _file_digests.sha256_optional_file(backup) != expected:
                return [f"backup hash mismatch for {destination}"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.{transaction_id}.restore")
            shutil.copy2(backup, temporary)
            os.replace(temporary, destination)
        elif destination.exists():
            if destination.is_file():
                destination.unlink()
            else:
                shutil.rmtree(destination)
    except OSError as exc:
        errors.append(f"restore failed for {destination}: {exc}")
    return errors


def verify_authoring_rollback(journal: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for record in journal.get("writes", []) if isinstance(journal.get("writes"), list) else []:
        if not isinstance(record, dict) or not record.get("published"):
            continue
        destination = Path(str(record.get("destination") or ""))
        if record.get("pre_exists"):
            expected = record.get("pre_sha256")
            if not destination.is_file():
                errors.append(f"pre-existing destination missing after rollback: {destination}")
            elif expected and _file_digests.sha256_optional_file(destination) != expected:
                errors.append(f"pre-existing destination hash mismatch after rollback: {destination}")
        elif destination.exists():
            errors.append(f"pre-missing destination still exists after rollback: {destination}")
    for raw in journal.get("created_directories", []) if isinstance(journal.get("created_directories"), list) else []:
        directory = Path(str(raw))
        if directory.exists():
            errors.append(f"created directory still exists after rollback: {directory}")
    return errors


def remove_authoring_created_directories(journal: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for raw in reversed(journal.get("created_directories", []) if isinstance(journal.get("created_directories"), list) else []):
        directory = Path(str(raw))
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        except OSError as exc:
            errors.append(f"created directory cleanup failed for {directory}: {exc}")
    return errors


def rollback_authoring_plan(plan: AuthoringPlan, journal: dict[str, Any]) -> None:
    journal["state"] = "rolling_back"
    _authoring_journal_store.write(plan, journal)
    errors: list[str] = []
    for record in reversed(journal.get("writes", [])):
        if not record.get("published"):
            continue
        errors.extend(authoring_restore_record(record, plan.transaction_id))
    errors.extend(remove_authoring_created_directories(journal))
    errors.extend(verify_authoring_rollback(journal))
    ok = not errors
    journal["state"] = "rolled_back" if ok else "recovery_required"
    journal["rollback_verified"] = ok
    journal["recovery_errors"] = errors
    _authoring_journal_store.write(plan, journal)
    if not ok:
        raise RuntimeError(
            f"authoring rollback could not be verified; recovery required: {_authoring_input_service.journal_path(plan)}"
        )


def commit_authoring_plan(
    plan: AuthoringPlan,
    journal: dict[str, Any],
    staged: dict[Path, Path],
) -> None:
    entity_writes = plan.authoritative_writes
    registry_writes = plan.registry_writes
    records = journal["writes"]
    try:
        authoring_failure_point("before_first_entity_publish", plan)
        for index, write in enumerate(entity_writes):
            journal["next_operation"] = str(write.destination)
            _authoring_journal_store.write(plan, journal)
            publish_authoring_write(plan, write, records[index], staged, journal)
            authoring_failure_point(f"after_entity_publish:{index + 1}", plan, write)
        authoring_failure_point("before_first_registry_publish", plan)
        offset = len(entity_writes)
        for index, write in enumerate(registry_writes):
            journal["next_operation"] = str(write.destination)
            _authoring_journal_store.write(plan, journal)
            publish_authoring_write(plan, write, records[offset + index], staged, journal)
            authoring_failure_point(f"after_registry_publish:{index + 1}", plan, write)
        authoring_failure_point("before_commit_verification", plan)
        for write in [*entity_writes, *registry_writes]:
            if write.operation == "delete":
                if write.destination.exists():
                    raise RuntimeError(f"deleted authoring path still exists: {write.destination}")
            elif _file_digests.sha256_optional_file(write.destination) != _file_digests.sha256_bytes(write.content or b""):
                raise RuntimeError(f"committed authoring hash mismatch: {write.destination}")
        journal["state"] = "committed"
        journal["committed_at"] = _core_common_clock.now_utc()
        journal.pop("next_operation", None)
        _authoring_journal_store.write(plan, journal)
    except BaseException:
        rollback_authoring_plan(plan, journal)
        raise


def execute_authoring_effect(record: dict[str, Any], plan: AuthoringPlan | None = None) -> None:
    kind = str(record.get("kind") or "")
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    effect_id = str(record.get("effect_id") or "")
    if kind == "callback" and plan is not None:
        for effect in plan.post_commit_effects:
            if effect.label == record.get("label") and effect.callback is not None:
                effect.callback()
                return
        return
    if kind == "process_event":
        project_root = Path(str(payload["project_root"])).expanduser().resolve()
        _process_event_recorder.emit_process_event(
            project_root,
            str(payload["event_type"]),
            process_id=str(payload["process_id"]),
            subject=str(payload["process_id"]),
            payload=payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
            correlation_id=str(payload["correlation_id"]),
            event_id=f"evt_{safe_id(effect_id, 'effect')}",
        )
        return
    if kind == "knowledge_audit":
        workplace_root = Path(str(payload["workplace_root"])).expanduser().resolve()
        slug = safe_id(effect_id, "effect")
        _slug, proposal_path = write_resource_proposal(
            workplace_root,
            str(payload["command"]),
            str(payload["resource_id"]),
            payload.get("proposal_payload") if isinstance(payload.get("proposal_payload"), dict) else {},
            slug=slug,
        )
        for event in payload.get("events", []) if isinstance(payload.get("events"), list) else []:
            if not isinstance(event, dict):
                continue
            _workplace_resource_events.append_workplace_resource_event(
                workplace_root,
                _workplace_resource_events.resource_management_event(
                    scope="workplace",
                    command=str(payload["command"]),
                    event_type=str(event["event_type"]),
                    target=event.get("target") if isinstance(event.get("target"), dict) else {},
                    status=str(event["status"]),
                    message=str(event["message"]),
                    event_id=f"evt_{safe_id(effect_id + '-' + str(event['event_type']), 'event')}",
                ),
            )
        report = write_resource_management_report(
            workplace_root,
            slug,
            str(payload.get("report_title") or "Knowledge Resource Add Report"),
            [str(item) for item in payload.get("report_lines", []) if isinstance(item, str)],
        )
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        print(f"REPORT: {rel(report, workplace_root)}")
        return
    if kind == "platform_audit":
        workplace_root = Path(str(payload["workplace_root"])).expanduser().resolve()
        slug = safe_id(effect_id, "effect")
        _slug, proposal_path = write_resource_proposal(
            workplace_root,
            str(payload["command"]),
            str(payload["contract_id"]),
            payload.get("proposal_payload") if isinstance(payload.get("proposal_payload"), dict) else {},
            slug=slug,
        )
        for event in payload.get("events", []) if isinstance(payload.get("events"), list) else []:
            if not isinstance(event, dict):
                continue
            _workplace_resource_events.append_workplace_resource_event(
                workplace_root,
                _workplace_resource_events.resource_management_event(
                    scope="workplace",
                    command=str(payload["command"]),
                    event_type=str(event["event_type"]),
                    target=event.get("target") if isinstance(event.get("target"), dict) else {},
                    status=str(event["status"]),
                    message=str(event["message"]),
                    event_id=f"evt_{safe_id(effect_id + '-' + str(event['event_type']), 'event')}",
                ),
            )
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return
    raise RuntimeError(f"unknown authoring effect kind: {kind}")


def run_post_commit_effect_records(
    journal: dict[str, Any],
    journal_path: Path,
    plan: AuthoringPlan | None = None,
) -> None:
    for record in journal.get("post_commit_effects", []) if isinstance(journal.get("post_commit_effects"), list) else []:
        if not isinstance(record, dict) or not record.get("executable"):
            continue
        if record.get("state") == "succeeded":
            continue
        record["state"] = "running"
        record["attempts"] = int(record.get("attempts") or 0) + 1
        record["last_error"] = None
        journal["state"] = "committed_audit_pending"
        _authoring_journal_store.write_data(journal_path, journal)
        try:
            execute_authoring_effect(record, plan)
        except BaseException as exc:
            record["state"] = "failed"
            record["last_error"] = str(exc)
            journal["state"] = "committed_audit_pending"
            _authoring_journal_store.write_data(journal_path, journal)
            raise
        record["state"] = "succeeded"
        _authoring_journal_store.write_data(journal_path, journal)
    journal["state"] = "committed_audit_complete"
    journal["post_commit_completed"] = [
        str(record.get("label") or record.get("effect_id"))
        for record in journal.get("post_commit_effects", [])
        if isinstance(record, dict) and record.get("executable") and record.get("state") == "succeeded"
    ]
    _authoring_journal_store.write_data(journal_path, journal)


def run_post_commit_effects(plan: AuthoringPlan, journal: dict[str, Any]) -> None:
    authoring_failure_point("after_commit_before_audit", plan)
    run_post_commit_effect_records(journal, _authoring_input_service.journal_path(plan), plan)


def execute_authoring_plan(plan: AuthoringPlan) -> dict[str, Any]:
    preflight_authoring_plan(plan)
    journal, staged = stage_authoring_plan(plan)
    try:
        validate_staged_authoring_plan(plan, journal, staged)
        commit_authoring_plan(plan, journal, staged)
    except BaseException:
        if journal.get("state") not in {"rolled_back", "recovery_required"}:
            rollback_authoring_plan(plan, journal)
        raise
    run_post_commit_effects(plan, journal)
    return journal


def validate_authoring_recovery_journal(journal_path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    transaction_root = journal_path.parent.resolve()
    if not isinstance(data.get("transaction_id"), str) or not data.get("transaction_id"):
        errors.append("journal transaction_id missing")
    writes = data.get("writes")
    if not isinstance(writes, list):
        return [*errors, "journal writes missing"]
    for index, record in enumerate(writes):
        if not isinstance(record, dict):
            errors.append(f"write {index} is not an object")
            continue
        destination = Path(str(record.get("destination") or ""))
        backup = Path(str(record.get("backup_path") or ""))
        if not destination.is_absolute():
            errors.append(f"write {index} destination is not absolute")
        try:
            backup.resolve().relative_to(transaction_root)
        except ValueError:
            errors.append(f"write {index} backup path escapes transaction root")
    return errors


def recover_authoring_transaction(journal_path: Path, *, apply: bool = True) -> str:
    data = load_yaml_document(journal_path)
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: authoring journal is invalid: {journal_path}")
    state = str(data.get("state") or "")
    if state in {"rolled_back", "committed_audit_complete"}:
        return state
    if not apply:
        return state or "unknown"
    validation_errors = validate_authoring_recovery_journal(journal_path, data)
    if validation_errors:
        data["state"] = "recovery_required"
        data["rollback_verified"] = False
        data["recovery_errors"] = validation_errors
        _authoring_journal_store.write_data(journal_path, data)
        return "recovery_required"
    if state in {"committed", "committed_audit_pending"}:
        run_post_commit_effect_records(data, journal_path, None)
        return str(data["state"])
    errors: list[str] = []
    transaction_id = str(data.get("transaction_id") or journal_path.parent.name)
    for record in reversed(data.get("writes", []) if isinstance(data.get("writes"), list) else []):
        if not isinstance(record, dict) or not record.get("published"):
            continue
        errors.extend(authoring_restore_record(record, transaction_id))
    errors.extend(remove_authoring_created_directories(data))
    errors.extend(verify_authoring_rollback(data))
    ok = not errors
    data["state"] = "rolled_back" if ok else "recovery_required"
    data["rollback_verified"] = ok
    data["recovery_errors"] = errors
    _authoring_journal_store.write_data(journal_path, data)
    return str(data["state"])


def command_authoring_transaction_recover(args: argparse.Namespace) -> int:
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    transaction_id = validate_resource_id(str(args.transaction), "authoring transaction")
    journal_path = runtime_root / "authoring-transactions" / transaction_id / "journal.yaml"
    if not journal_path.is_file():
        raise SystemExit(f"FAIL: authoring transaction journal not found: {journal_path}")
    mode = _authoring_input_service.mode(args)
    state = recover_authoring_transaction(journal_path, apply=mode == "apply")
    print(f"TRANSACTION: {transaction_id}")
    print(f"STATE: {state}")
    return 1 if state == "recovery_required" else 0


def planned_registry_upsert(
    path: Path,
    collection_key: str,
    entry: dict[str, Any],
    schema_name: str,
) -> tuple[bytes, str, dict[str, Any]]:
    if path.exists() and not path.is_file():
        raise SystemExit(f"FAIL: registry path is not a file: {path}")
    if path.is_file():
        data = load_yaml_document(path)
        error = yaml_error(data)
        if error:
            raise SystemExit(f"FAIL: registry YAML invalid; original preserved: {path}: {error}")
        if not isinstance(data, dict) or not data:
            raise SystemExit(f"FAIL: registry must be a non-empty YAML object; original preserved: {path}")
        entries = data.get(collection_key)
        if entries is None:
            entries = []
            data[collection_key] = entries
        if not isinstance(entries, list):
            raise SystemExit(
                f"FAIL: registry collection {collection_key} must be a list; original preserved: {path}"
            )
    else:
        data = {"schema_version": 1, collection_key: []}
        entries = data[collection_key]
    result = upsert_resource(entries, entry)
    _update_schema_checks.require(data, schema_name, f"registry {path.name}")
    return ensure_trailing_newline(dump_yaml(data)).encode("utf-8"), result, data






def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()




RESOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
WINDOWS_RESERVED_DEVICE_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *{f"com{index}" for index in range(1, 10)},
    *{f"lpt{index}" for index in range(1, 10)},
}


def validate_resource_id(raw: str, resource_kind: str = "resource") -> str:
    value = str(raw)
    invalid_reason = ""
    if not value:
        invalid_reason = "must not be empty"
    elif value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        invalid_reason = "must not contain whitespace or control characters"
    elif "%" in value:
        invalid_reason = "must not contain percent-encoded path characters"
    elif "/" in value or "\\" in value:
        invalid_reason = "must not contain path separators"
    elif ":" in value or re.match(r"^[a-zA-Z]:", value):
        invalid_reason = "must not contain drive, URI, or alternate-stream syntax"
    elif value.endswith((".", " ")):
        invalid_reason = "must not end with a Windows-trimmed dot or space"
    elif any(segment in {"", ".", ".."} for segment in value.split(".")):
        invalid_reason = "must not contain empty or relative dot segments"
    elif value.split(".", 1)[0] in WINDOWS_RESERVED_DEVICE_BASENAMES:
        invalid_reason = "must not use a Windows reserved device basename"
    elif not RESOURCE_ID_PATTERN.fullmatch(value):
        invalid_reason = "must match ^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$"
    if invalid_reason:
        raise SystemExit(f"FAIL: invalid {resource_kind} id {value!r}: {invalid_reason}")
    return value


def contained_resource_path(root: Path, target: Path, resource_kind: str = "resource") -> Path:
    try:
        resolved_root = root.expanduser().resolve()
        resolved_target = target.expanduser().resolve()
        resolved_target.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(
            f"FAIL: invalid {resource_kind} target cannot be contained under declared root: {target.as_posix()}"
        ) from exc
    return resolved_target










def path_string_is_absolute(value: str) -> bool:
    return _context_contract_inputs.path_string_is_absolute(value)


def normalize_path_string(value: str) -> str:
    return value.replace("\\", "/")


def load_workplace_path_constants(workplace_manifest: Path | None, workplace_root: Path | None = None) -> dict[str, str]:
    root = workplace_root or (workplace_manifest.parent if workplace_manifest else Path(".").resolve())
    constants = dict(_core_resources_registries.DEFAULT_PATH_CONSTANTS)
    if workplace_manifest and workplace_manifest.is_file():
        data = load_yaml_document(workplace_manifest)
        raw_constants = data.get("path_constants") if isinstance(data, dict) else None
        if isinstance(raw_constants, dict):
            for key, value in raw_constants.items():
                if isinstance(key, str):
                    constants[key] = "" if value is None else str(value)
    constants.setdefault("PF_WORKPLACE", ".")
    constants["_WORKPLACE_ROOT"] = root.as_posix()
    return constants


def expand_path_constants(raw_path: str, constants: dict[str, str]) -> tuple[str, list[str], list[str]]:
    expanded = raw_path
    used: list[str] = []
    errors: list[str] = []
    visiting: list[str] = []

    def expand_const(name: str) -> str:
        if name in visiting:
            errors.append("cyclic path constant reference: " + " -> ".join([*visiting, name]))
            return "${" + name + "}"
        if name not in constants:
            errors.append(f"unknown path constant: {name}")
            return "${" + name + "}"
        value = str(constants.get(name, ""))
        if value == "":
            errors.append(f"empty path constant: {name}")
            return ""
        used.append(name)
        visiting.append(name)
        result = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), value)
        visiting.pop()
        return result

    for _ in range(20):
        if not PATH_CONSTANT_PATTERN.search(expanded):
            break
        before = expanded
        expanded = PATH_CONSTANT_PATTERN.sub(lambda match: expand_const(match.group(1)), expanded)
        if expanded == before:
            break
    if PATH_CONSTANT_PATTERN.search(expanded):
        errors.append("unresolved path constant reference remains")
    return expanded, sorted(set(used)), sorted(set(errors))


def resolve_path_with_constants(raw_path: str | None, base_dir: Path, constants: dict[str, str] | None = None) -> dict[str, Any]:
    original = "" if raw_path is None else str(raw_path)
    constants = constants or load_workplace_path_constants(None, base_dir)
    expanded, used_constants, errors = expand_path_constants(original, constants)
    expanded = normalize_path_string(expanded)
    status = "resolved"
    if errors:
        status = "error"
    elif used_constants:
        status = "resolved_from_constant"
    elif path_string_is_absolute(expanded):
        status = "absolute"
    else:
        status = "resolved_relative"
    if path_string_is_absolute(expanded):
        resolved = expanded
        is_absolute = True
    else:
        resolved = normalize_path_string((base_dir / expanded).resolve().as_posix())
        is_absolute = True
    return {
        "original": original,
        "expanded": expanded,
        "resolved": resolved,
        "is_absolute": is_absolute,
        "is_private": is_absolute,
        "path_status": status,
        "constants": used_constants,
        "errors": errors,
    }


def workplace_path_resolution(workplace_root: Path, raw_path: str | None) -> dict[str, Any]:
    manifest = workplace_root / "workplace.yaml"
    return resolve_path_with_constants(raw_path, workplace_root, load_workplace_path_constants(manifest, workplace_root))


def path_resolution_to_path(resolution: dict[str, Any]) -> Path:
    return Path(str(resolution.get("resolved") or resolution.get("expanded") or resolution.get("original") or ""))


def locate_flow_root(project_root: Path, *, prefer_pf: bool = True) -> Path:
    return _context_contract_inputs.locate_flow_root(project_root, prefer_pf=prefer_pf)




def flow_layout(project_root: Path) -> str:
    flow_root = locate_flow_root(project_root)
    return "pf" if (flow_root / "process-forge.yaml").is_file() else "missing"




def flow_path(project_root: Path, *parts: str) -> Path:
    return locate_flow_root(project_root) / Path(*parts)


def iter_flow_roots(project_root: Path) -> list[Path]:
    pf_root = project_root / PROJECT_FLOW_ROOT
    return [pf_root] if pf_root.is_dir() else []






def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small mapping-only YAML subset used by init answers."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if stripped.startswith("- "):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return root








def write_file(path: Path, content: str, *, force: bool = False) -> WriteResult:
    content = ensure_trailing_newline(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        if existing == content:
            return WriteResult(path, "unchanged", path)
        if not force:
            candidate = path.with_name(path.name + ".candidate")
            candidate.write_text(content, encoding="utf-8")
            return WriteResult(path, "candidate", candidate)
    path.write_text(content, encoding="utf-8")
    return WriteResult(path, "written", path)


def append_gitignore_entries(path: Path, entries: list[str], *, force: bool = False) -> WriteResult:
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    lines = existing.splitlines()
    changed = False
    for entry in entries:
        if entry not in lines:
            lines.append(entry)
            changed = True
    if not changed:
        return WriteResult(path, "unchanged", path)
    content = "\n".join(lines).rstrip() + "\n"
    if path.exists() and existing and not force:
        candidate = path.with_name(path.name + ".candidate")
        candidate.write_text(content, encoding="utf-8")
        return WriteResult(path, "candidate", candidate)
    path.write_text(content, encoding="utf-8")
    return WriteResult(path, "written", path)


def _codex_integration_module() -> Any:
    module_name = "pf_runtime_codex_integration"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    module_path = ROOT / "tools" / "pf_runtime" / "codex_integration.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL: could not load Codex integration module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _codex_hook_adapter_path() -> Path:
    return ROOT / "tools" / "pf_runtime" / "codex_hooks.py"


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _codex_registered_events(config: dict[str, Any], adapter: Path, integration: Any) -> list[str]:
    installed: list[str] = []
    hooks = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if isinstance(handlers, list) and any(integration.is_managed(item, adapter) for item in handlers):
                installed.append(str(event))
                break
    return sorted(set(installed))


def project_codex_integration_status(project_root: Path) -> dict[str, Any]:
    project_root = Path(project_root).expanduser().resolve()
    target = project_root / ".codex" / "hooks.json"
    adapter = _codex_hook_adapter_path().resolve()
    payload: dict[str, Any] = {
        "status": "missing",
        "target": ".codex/hooks.json",
        "adapter": _repo_relative(adapter, ROOT),
        "event_types": [],
        "registered_events": [],
        "missing_events": [],
        "global_hooks": {"exists": (Path.home() / ".codex" / "hooks.json").is_file(), "managed": False},
        "restart_required": True,
        "scope": "project-local",
    }
    if not adapter.is_file():
        payload.update({"status": "unavailable", "error": "adapter_missing", "restart_required": False})
        return payload
    integration = _codex_integration_module()
    events = sorted(str(item) for item in integration.EVENTS)
    payload["event_types"] = events
    try:
        current = integration.load_config(target)
    except SystemExit as exc:
        payload.update({"status": "invalid", "error": str(exc), "missing_events": events})
        return payload
    registered = _codex_registered_events(current, adapter, integration)
    missing = [event for event in events if event not in registered]
    payload["registered_events"] = registered
    payload["missing_events"] = missing
    if not target.is_file():
        payload["status"] = "missing"
    elif missing:
        payload["status"] = "stale"
    else:
        payload["status"] = "installed"
        payload["restart_required"] = False
    return payload


def project_codex_integration_install(project_root: Path) -> dict[str, Any]:
    project_root = Path(project_root).expanduser().resolve()
    target = project_root / ".codex" / "hooks.json"
    adapter = _codex_hook_adapter_path().resolve()
    if not adapter.is_file():
        raise SystemExit("FAIL: Codex hook adapter path does not exist")
    integration = _codex_integration_module()
    current = integration.load_config(target)
    payload, changed = integration.install_payload(current, adapter)
    result: dict[str, Any] = {
        "status": "installed",
        "target": ".codex/hooks.json",
        "adapter": _repo_relative(adapter, ROOT),
        "changed_events": sorted(changed),
        "restart_required": bool(changed),
    }
    if changed:
        backup = integration.write_atomic(target, payload)
        result["backup"] = rel(backup, project_root) if str(backup) else None
    result["after"] = project_codex_integration_status(project_root)
    return result


def execute_project_codex_integration_repair(project_root: Path) -> dict[str, Any]:
    result = project_codex_integration_install(project_root)
    _process_event_recorder.emit_process_event(
        project_root,
        "project.codex_hooks.installed",
        process_id="project-initialization",
        process_version="1.0.0",
        payload={
            "target": result.get("target"),
            "changed_events": result.get("changed_events", []),
            "restart_required": result.get("restart_required"),
        },
    )
    return {
        "status": "complete",
        "repair_action": "install_codex_hooks",
        "codex_integration": result,
        "next_action": "restart_codex_session" if result.get("restart_required") else "continue",
    }


def upsert_bounded_section(existing: str, section: str) -> str:
    section = ensure_trailing_newline(section).rstrip()
    pattern = re.compile(
        re.escape(GLOBAL_AGENT_SECTION_START) + r".*?" + re.escape(GLOBAL_AGENT_SECTION_END),
        re.DOTALL,
    )
    if pattern.search(existing):
        return ensure_trailing_newline(pattern.sub(section, existing).rstrip())
    if existing.strip():
        return ensure_trailing_newline(existing.rstrip() + "\n\n" + section)
    return ensure_trailing_newline(section)


def write_global_agent_section(path: Path, *, dry_run: bool = False, force: bool = False) -> WriteResult:
    existing = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    updated = upsert_bounded_section(existing, GLOBAL_AGENT_SECTION)
    if existing == updated:
        return WriteResult(path, "unchanged", path)
    if dry_run or (path.exists() and not force):
        candidate = path.with_name(path.name + ".candidate")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(updated, encoding="utf-8")
        return WriteResult(path, "candidate", candidate)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return WriteResult(path, "written", path)


def print_plan(title: str, planned: list[Path], root: Path) -> None:
    print(f"PLAN: {title}")
    for path in planned:
        print(f"  - {rel(path, root)}")














def finalize_workplace_doctor_artifacts(root: Path, status: int, output: str) -> None:
    result = "pass" if status == 0 else "fail"
    report = f"""# Workplace Bootstrap Report

## Status

{result}

## Doctor Command

```bash
pf doctor-workplace --root <workplace-root>
```

## Doctor Output

```text
{output.rstrip()}
```
"""
    review = f"""# Workplace Bootstrap Review

## Reviewed Object

Workplace initialization output.

## Result

{result}

## Evidence

- artifacts/workplace-bootstrap-report.md
- runtime/events/events.ndjson
"""
    handoff = f"""# Handoff: workplace-initialization -> project-onboarding

Objective:
Prepare the workplace for future project onboarding.

Current status:
Doctor status: {result}.

Input artifacts:
- workplace.yaml
- terms.yaml
- registries/
- artifacts/workplace-bootstrap-report.md

Files changed:
- workplace root

Files not to touch:
- Project `.pf/` folders; those belong to `project-onboarding`.

Known issues:
{("- Doctor failed; read artifacts/workplace-bootstrap-report.md for fix hints." if status else "- None recorded.")}

Required checks:
- `pf doctor-workplace --root <workplace-root>`

Next recommended action:
Run `project-onboard` for a concrete project.
"""
    write_file(root / "artifacts" / "workplace-bootstrap-report.md", report, force=True)
    write_file(root / "reviews" / "workplace-bootstrap-review.md", review, force=True)
    write_file(root / "handoffs" / "workplace-ready-handoff.md", handoff, force=True)






def command_init_workplace(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    answers = _AnswersDocumentReader().read(Path(args.answers).expanduser().resolve() if args.answers else None)
    profile = str(getattr(args, "profile", "") or "").strip()
    if profile:
        answers = dict(answers)
        answers["profile"] = profile
    files = _workplace_file_builder.build_workplace_files(root, answers)
    planned_dirs = [root / "cache", root / "runtime", root / "runtime" / "events", root / "logs", root / "artifacts", root / "reviews", root / "handoffs", root / "packages", root / "knowledge", root / "reusable-templates", root / "platform-contracts", root / "specializations", root / "runtime-drivers", root / "tools", root / "mcp"]
    if not args.apply:
        print_plan("workplace init dry run", list(files) + planned_dirs, root)
        return 0
    _workplace_resource_events.append_workplace_event(root, "workplace.initialization.started", payload={"command": getattr(args, "command", "init-workplace")})
    for directory in planned_dirs:
        directory.mkdir(parents=True, exist_ok=True)
    results: list[WriteResult] = []
    for path, content in files.items():
        if path.name == "AGENTS.md":
            results.append(write_global_agent_section(path, force=args.force))
        else:
            results.append(write_file(path, content, force=args.force))
    workplace_coordination = _project_coordination_reader.workplace(root / "workplace.yaml")
    if workplace_coordination.get("director_office_enabled"):
        initialize_director_office(root, workplace_coordination)
    _workplace_resource_events.append_workplace_event(root, "workplace.structure.created", payload={"directories": [rel(path, root) for path in planned_dirs]})
    _workplace_resource_events.append_workplace_event(root, "workplace.path_constants.created", payload={"manifest": "workplace.yaml"})
    _workplace_resource_events.append_workplace_event(root, "workplace.registry.created", payload={"registries": "registries/"})
    doctor_status, doctor_output = run_command_capture(command_doctor_workplace, argparse.Namespace(root=str(root)))
    print(doctor_output, end="")
    finalize_workplace_doctor_artifacts(root, doctor_status, doctor_output)
    _workplace_resource_events.append_workplace_event(
        root,
        "workplace.doctor.passed" if doctor_status == 0 else "workplace.doctor.failed",
        payload={"status": "pass" if doctor_status == 0 else "fail"},
    )
    maintenance = search_index_maintenance_for_known_projects(root, reason="workplace-init")
    _workplace_resource_events.append_workplace_event(root, "workplace.initialization.completed", payload={"files": [rel(result.target, root) for result in results], "doctor_status": doctor_status})
    print_search_index_maintenance_summary(maintenance)
    for result in results:
        print(f"{result.status.upper()}: {rel(result.target, root)}")
    return doctor_status


def command_global_agents_section(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    result = write_global_agent_section(path, dry_run=args.dry_run, force=args.force)
    print(f"{result.status.upper()}: {result.target}")
    return 0


def workplace_setup_session_dir(workplace: Path, session_id: str) -> Path:
    return workplace / "setup-sessions" / safe_id(session_id, "setup-session")












def workplace_setup_agent_snippet(processforge_root: str, workplace_path: str) -> str:
    return f"""# ProcessForge Agent Instructions

ProcessForge is installed at {processforge_root}.
Workplace is {workplace_path}.

Do not copy ProcessForge into agent config folders or projects.

Inside onboarded projects:
1. Read root AGENTS.md (or .pf/AGENTS.md in an unmigrated project), then verify pf.context.
2. Use python .pf/runtime/bin/pf.py from the project root.

Outside projects:
use python {processforge_root}/bin/pf.py.
"""


def command_workplace_setup_start(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    session_id = safe_id(args.session_id or "default", "setup-session")
    session_dir = workplace_setup_session_dir(workplace, session_id)
    answers = _workplace_setup_answers.load_guided_workplace_answers(session_dir, Path(args.answers).expanduser().resolve() if args.answers else None, workplace=workplace, session_id=session_id)
    planned = [session_dir / "answers.yaml", session_dir / "proposal.yaml", session_dir / "proposal.md", session_dir / "next-steps.md"]
    if not args.apply or args.dry_run:
        print_plan("workplace-setup start dry run", planned, workplace)
        return 0
    session_dir.mkdir(parents=True, exist_ok=True)
    _core_common_yaml_io.write_yaml_file(session_dir / "answers.yaml", answers)
    proposal, proposal_md = _workplace_setup_proposal_builder.build(session_id, answers)
    _core_common_yaml_io.write_yaml_file(session_dir / "proposal.yaml", proposal)
    (session_dir / "proposal.md").write_text(ensure_trailing_newline(proposal_md), encoding="utf-8")
    (session_dir / "next-steps.md").write_text(
        "# Next Steps\n\nReview `proposal.md`, adjust `answers.yaml`, then run `workplace-setup apply` with `--apply`.\n",
        encoding="utf-8",
    )
    _workplace_resource_events.append_workplace_event(workplace, "workplace.setup.started", payload={"session_id": session_id})
    print(f"WROTE: {rel(session_dir / 'answers.yaml', workplace)}")
    print(f"WROTE: {rel(session_dir / 'proposal.md', workplace)}")
    return 0


def command_workplace_setup_review(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    session_id = safe_id(args.session_id or "default", "setup-session")
    session_dir = workplace_setup_session_dir(workplace, session_id)
    answers = _workplace_setup_answers.load_guided_workplace_answers(session_dir, Path(args.answers).expanduser().resolve() if args.answers else None, workplace=workplace, session_id=session_id)
    proposal, proposal_md = _workplace_setup_proposal_builder.build(session_id, answers)
    review = f"""# Guided Workplace Setup Review

## Result

pass_with_conditions

## Checked

- answers are parseable YAML
- proposal is generated before apply
- private paths stay in workplace-local setup artifacts
- apply plan delegates to `workplace-init` and `doctor-workplace`

## Conditions

- User should inspect `proposal.md` before running apply on a real machine.
"""
    planned = [session_dir / "answers.yaml", session_dir / "proposal.yaml", session_dir / "proposal.md", session_dir / "review.md"]
    if args.dry_run:
        print_plan("workplace-setup review dry run", planned, workplace)
        return 0
    session_dir.mkdir(parents=True, exist_ok=True)
    _core_common_yaml_io.write_yaml_file(session_dir / "answers.yaml", answers)
    _core_common_yaml_io.write_yaml_file(session_dir / "proposal.yaml", proposal)
    (session_dir / "proposal.md").write_text(ensure_trailing_newline(proposal_md), encoding="utf-8")
    (session_dir / "review.md").write_text(ensure_trailing_newline(review), encoding="utf-8")
    _workplace_resource_events.append_workplace_event(workplace, "workplace.setup.reviewed", payload={"session_id": session_id})
    print(f"WROTE: {rel(session_dir / 'review.md', workplace)}")
    return 0


def command_workplace_setup_apply(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    session_id = safe_id(args.session_id or "default", "setup-session")
    session_dir = workplace_setup_session_dir(workplace, session_id)
    answers = _workplace_setup_answers.load_guided_workplace_answers(session_dir, Path(args.answers).expanduser().resolve() if args.answers else None, workplace=workplace, session_id=session_id)
    proposal, proposal_md = _workplace_setup_proposal_builder.build(session_id, answers)
    planned = [
        workplace / "workplace.yaml",
        workplace / "terms.yaml",
        workplace / "registries",
        session_dir / "apply-report.md",
        session_dir / "agent-instructions.md",
        session_dir / "next-steps.md",
    ]
    if not args.apply or args.dry_run:
        print_plan("workplace-setup apply dry run", planned, workplace)
        return 0
    session_dir.mkdir(parents=True, exist_ok=True)
    _core_common_yaml_io.write_yaml_file(session_dir / "answers.yaml", answers)
    _core_common_yaml_io.write_yaml_file(session_dir / "proposal.yaml", proposal)
    (session_dir / "proposal.md").write_text(ensure_trailing_newline(proposal_md), encoding="utf-8")
    init_answers = _workplace_setup_answers.guided_answers_to_workplace_init_answers(workplace, answers)
    init_answers_path = session_dir / "workplace-init.answers.yaml"
    _core_common_yaml_io.write_yaml_file(init_answers_path, init_answers)
    status, output = run_command_capture(
        command_init_workplace,
        argparse.Namespace(root=str(workplace), answers=str(init_answers_path), apply=True, dry_run=False, force=True, command="workplace-setup apply"),
    )
    machine = answers.get("machine_layout") if isinstance(answers.get("machine_layout"), dict) else {}
    snippet = workplace_setup_agent_snippet(str(machine.get("processforge_root") or "${PROCESSFORGE_ROOT}"), str(machine.get("workplace_path") or workplace))
    (session_dir / "agent-instructions.md").write_text(ensure_trailing_newline(snippet), encoding="utf-8")
    report = f"""# Guided Workplace Setup Apply Report

## Result

{"pass" if status == 0 else "fail"}

## Delegated Mechanics

- workplace-init internals
- doctor-workplace
- registry/bootstrap artifact creation

## Doctor Output

```text
{output.rstrip()}
```
"""
    next_steps = f"""# Next Steps

## Project Onboarding

```bash
python {machine.get("processforge_root") or "<processforge-root>"}/bin/pf.py project-onboard --project-root <project-root> --workplace {workplace} --type generic --apply
```

Inside an onboarded project, read root `AGENTS.md` (explicit `.pf/AGENTS.md` fallback in an unmigrated project), verify `pf.context`, and use `pf.work.start`, `pf.work.state`, and `pf.work.transition` with returned identities. The existing local CLI is `python .pf/runtime/bin/pf.py`.
"""
    (session_dir / "apply-report.md").write_text(ensure_trailing_newline(report), encoding="utf-8")
    (session_dir / "next-steps.md").write_text(ensure_trailing_newline(next_steps), encoding="utf-8")
    _workplace_resource_events.append_workplace_event(workplace, "workplace.setup.applied", payload={"session_id": session_id, "doctor_status": status})
    print(output, end="")
    print(f"WROTE: {rel(session_dir / 'apply-report.md', workplace)}")
    print(f"WROTE: {rel(session_dir / 'agent-instructions.md', workplace)}")
    return status


def command_workplace_setup_status(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    session_id = safe_id(args.session_id or "default", "setup-session")
    session_dir = workplace_setup_session_dir(workplace, session_id)
    print(f"SESSION: {session_id}")
    print(f"WORKPLACE: {workplace}")
    for name in ["answers.yaml", "proposal.yaml", "proposal.md", "review.md", "apply-report.md", "agent-instructions.md", "next-steps.md"]:
        print(f"{'PRESENT' if (session_dir / name).is_file() else 'MISSING'}: {rel(session_dir / name, workplace)}")
    return 0




def print_checks(checks: list[Check]) -> int:
    failed = False
    for item in checks:
        print(f"{item.level}: {item.message}")
        failed = failed or item.level == "FAIL"
    return 1 if failed else 0




def run_command_capture(func: Any, args: argparse.Namespace) -> tuple[int, str]:
    buffer = io.StringIO()
    status = 0
    with contextlib.redirect_stdout(buffer):
        try:
            status = int(func(args) or 0)
        except SystemExit as exc:
            status = int(exc.code) if isinstance(exc.code, int) else 1
            if exc.code and not isinstance(exc.code, int):
                print(str(exc.code))
    return status, buffer.getvalue()


def path_constant_checks(workplace_root: Path, workplace_manifest: Path) -> list[Check]:
    checks: list[Check] = []
    data = load_yaml_document(workplace_manifest)
    constants_data = data.get("path_constants") if isinstance(data, dict) else None
    checks.append(check("PASS" if isinstance(constants_data, dict) else "WARN", "path_constants configured" if isinstance(constants_data, dict) else "path_constants missing; defaults will be used"))
    constants = load_workplace_path_constants(workplace_manifest, workplace_root)
    for name, value in constants.items():
        if name.startswith("_"):
            continue
        if not isinstance(value, str) or value == "":
            checks.append(check("FAIL", f"path constant {name} has empty value"))
            continue
        resolution = resolve_path_with_constants("${" + name + "}", workplace_root, constants)
        errors = resolution.get("errors", [])
        if errors:
            checks.append(check("FAIL", f"path constant {name} failed: {', '.join(errors)}"))
        else:
            checks.append(check("PASS", f"path constant {name} resolves ({resolution.get('path_status')})"))
    return checks






def command_doctor_workplace(args: argparse.Namespace) -> int:
    from processforge_core.configuration import ConfigService, ConfigurationError
    from processforge_core.configuration.yaml_store import YamlConfigStore

    root = Path(args.root).expanduser().resolve()
    checks: list[Check] = []
    try:
        configuration = ConfigService(YamlConfigStore(root / "configuration.yaml")).read()
        checks.append(check("PASS", "configuration.yaml valid" if configuration.exists else "configuration.yaml absent; defaults apply"))
    except ConfigurationError as exc:
        checks.append(check("FAIL", exc.code))
    manifest = root / "workplace.yaml"
    if manifest.is_file():
        checks.append(check("PASS", "workplace.yaml found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        if contains_secret_value(text):
            checks.append(check("FAIL", "workplace.yaml appears to contain a secret value"))
        else:
            checks.append(check("PASS", "workplace.yaml contains no obvious secret values"))
        _update_document_reader.doctor_yaml(manifest, "workplace.schema.json", "workplace manifest", checks)
        cfg = _project_coordination_reader.workplace(manifest)
        checks.append(check("PASS", f"default_project_mode is {cfg['default_project_mode']}"))
        checks.append(check("PASS", f"director_enabled is {str(bool(cfg.get('director_enabled'))).lower()}"))
        if cfg.get("director_office_enabled"):
            checks.append(check("PASS" if _project_coordination_state.director_office_exists(root, cfg) else "WARN", "Director Office exists"))
        checks.extend(path_constant_checks(root, manifest))
        checks.extend(_workplace_registry_validation_service.paths(root, manifest))
        checks.extend(_workplace_registry_validation_service.packages(root))
    else:
        checks.append(
            check_with_hint(
                "FAIL",
                "workplace.yaml missing",
                "The selected path is not an initialized ProcessForge workplace.",
                "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
            )
        )

    for rel_path in [
        "registries/distributions.yaml",
        "registries/platforms.yaml",
        "registries/knowledge-roots.yaml",
        "registries/package-roots.yaml",
        "registries/templates.yaml",
        "registries/tools.yaml",
        "registries/mcp.yaml",
        "registries/process-packs.yaml",
    ]:
        path = root / rel_path
        checks.append(
            check("PASS", f"{rel_path} found")
            if path.is_file()
            else check_with_hint(
                "FAIL",
                f"{rel_path} missing",
                "A required workplace registry is absent.",
                "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
            )
        )
        if path.is_file() and contains_secret_value(path.read_text(encoding="utf-8", errors="replace")):
            checks.append(check("FAIL", f"{rel_path} appears to contain a secret value"))
        registry_schema = {
            "registries/distributions.yaml": "distributions-registry.schema.json",
            "registries/platforms.yaml": "platform-registry.schema.json",
            "registries/knowledge-roots.yaml": "knowledge-roots-registry.schema.json",
            "registries/package-roots.yaml": "package-roots-registry.schema.json",
            "registries/templates.yaml": "template-registry.schema.json",
            "registries/tools.yaml": "tool-registry.schema.json",
            "registries/mcp.yaml": "mcp-registry.schema.json",
        }.get(rel_path)
        if path.is_file() and registry_schema:
            _update_document_reader.doctor_yaml(path, registry_schema, rel_path, checks)
        elif path.is_file() and rel_path == "registries/process-packs.yaml":
            process_pack_registry = load_yaml_document(path)
            error = yaml_error(process_pack_registry)
            if error:
                checks.append(check("FAIL", f"{rel_path} YAML parse failed: {error}"))
            elif not isinstance(process_pack_registry.get("process_packs"), list):
                checks.append(check("FAIL", f"{rel_path} process_packs must be a list"))
            else:
                checks.append(check("PASS", f"{rel_path} has a valid process_packs collection"))

    for rel_dir in ["cache", "runtime", "logs"]:
        path = root / rel_dir
        checks.append(check("PASS" if path.is_dir() else "WARN", f"{rel_dir}/ {'found' if path.is_dir() else 'missing'}"))

    if manifest.is_file():
        knowledge_roots = _workplace_registry_reader.load_workplace_registry(manifest, "knowledge_roots", "knowledge-roots.yaml")
        knowledge_entries = knowledge_roots.get("knowledge_roots") if isinstance(knowledge_roots, dict) else []
        local_docs = next((item for item in knowledge_entries if isinstance(item, dict) and str(item.get("id")) == "local-docs"), None) if isinstance(knowledge_entries, list) else None
        if not local_docs:
            checks.append(
                check_with_hint(
                    "WARN",
                    "knowledge_roots.local-docs missing or empty",
                    "Local heavy documentation and source snapshots must be referenced through knowledge_roots.local-docs instead of private package paths.",
                    "add local-docs pointing to your documentation root",
                )
            )
        else:
            local_docs_path = _workplace_registry_reader.resolve_registry_relative_path(root, str(local_docs.get("path", "")), manifest)
            checks.append(
                check("PASS", "knowledge_roots.local-docs configured")
                if local_docs_path.is_dir()
                else check_with_hint(
                    "WARN",
                    "knowledge_roots.local-docs configured but path missing",
                    "The local-docs root is registered but the target directory is not available on this machine.",
                    "create the directory or update registries/knowledge-roots.yaml to the correct local documentation root",
                )
            )

        platforms_registry = _workplace_registry_reader.load_workplace_registry(manifest, "platforms", "platforms.yaml")
        platform_entries = platforms_registry.get("platforms") if isinstance(platforms_registry, dict) else []
        platform_ids = [
            str(item.get("id") or item.get("package_id"))
            for item in platform_entries
            if isinstance(item, dict) and (item.get("id") or item.get("package_id")) and str(item.get("status", "available")) not in {"missing", "disabled"}
        ] if isinstance(platform_entries, list) else []
        if platform_ids:
            workplace_resolution = _platform_contract_resolver.resolve(manifest, platform_ids)
            checks.append(check("PASS" if not workplace_resolution["missing_required_contracts"] else "FAIL", "platform inheritance parent platforms resolve"))
            for missing in workplace_resolution["missing_required_contracts"]:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"required platform available: {missing}",
                        "A workplace platform extends or requires a platform that is not registered.",
                        f"python bin/pf.py platform-create --workplace <workplace-root> --id {missing} --title \"{missing}\" --apply",
                    )
                )
            for cycle in workplace_resolution["circular_platforms"]:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"circular platform inheritance detected: {cycle}",
                        "Workplace platform inheritance must resolve to an acyclic stack.",
                        "remove one extends edge from the cycle and rerun doctor-workplace",
                    )
                )
        public_manifest_paths: list[Path] = []
        if platform_ids:
            public_manifest_paths.extend(path for pid in platform_ids for path in [platform_contract_path(root, pid)] if path)
        public_manifest_paths.extend(_project_package_catalog_reader.candidates(root, None, manifest))
        for public_path in sorted(set(public_manifest_paths), key=lambda item: item.as_posix()):
            text = public_path.read_text(encoding="utf-8", errors="replace")
            checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", f"{rel(public_path, root)} contains no private absolute paths"))

    mcp_registry = root / "registries" / "mcp.yaml"
    if mcp_registry.is_file():
        mcp_text = mcp_registry.read_text(encoding="utf-8", errors="replace")
        has_mcp_entry = re.search(r"(?m)^\s*-\s*$", mcp_text) or re.search(r"(?m)^\s*-\s+id:", mcp_text)
        if "mcp_servers:" in mcp_text and not has_mcp_entry:
            checks.append(check("WARN", "optional MCP providers are not configured"))
    return print_checks(checks)


def command_workplace_mode_status(args: argparse.Namespace) -> int:
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace))
    manifest = workplace_root / "workplace.yaml"
    cfg = _project_coordination_reader.workplace(manifest)
    office_exists = _project_coordination_state.director_office_exists(workplace_root, cfg)
    payload = {
        "workplace_root": normalize_path_string(str(workplace_root)),
        "director_enabled": bool(cfg.get("director_enabled")),
        "director_office_enabled": bool(cfg.get("director_office_enabled")),
        "director_office_exists": office_exists,
        "default_project_mode": cfg.get("default_project_mode", "simple"),
        "director": cfg.get("director", {}),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"WORKPLACE: {payload['workplace_root']}")
        print(f"DIRECTOR_ENABLED: {str(payload['director_enabled']).lower()}")
        print(f"DIRECTOR_OFFICE_ENABLED: {str(payload['director_office_enabled']).lower()}")
        print(f"DIRECTOR_OFFICE_EXISTS: {str(payload['director_office_exists']).lower()}")
        print(f"DEFAULT_PROJECT_MODE: {payload['default_project_mode']}")
    return 0






def command_workplace_mode_set(args: argparse.Namespace) -> int:
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace))
    if args.director_enabled is None and args.director_office_enabled is None:
        raise SystemExit("FAIL: workplace-mode set requires --director-enabled and/or --director-office-enabled")
    if args.director_enabled is not None and not parse_cli_bool(args.director_enabled, name="--director-enabled") and not args.force:
        active = _project_coordination_state.active_organized_project_sessions(workplace_root)
        if active:
            raise SystemExit("FAIL: cannot disable workplace Director while organized project sessions are active; use --force after migration")

    def updater(cfg: dict[str, Any]) -> None:
        if args.director_enabled is not None:
            cfg["director_enabled"] = parse_cli_bool(args.director_enabled, name="--director-enabled")
        if args.director_office_enabled is not None:
            cfg["director_office_enabled"] = parse_cli_bool(args.director_office_enabled, name="--director-office-enabled")

    cfg = _project_coordination_state.update_workplace_coordination(workplace_root, updater)
    if cfg.get("director_office_enabled"):
        initialize_director_office(workplace_root, cfg)
    print(f"UPDATED: {rel(workplace_root / 'workplace.yaml', workplace_root)}")
    return command_workplace_mode_status(argparse.Namespace(workplace=str(workplace_root), json=args.json))


def command_workplace_mode_set_default_project_mode(args: argparse.Namespace) -> int:
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace))
    mode = _project_coordination_reader.workplace_mode(args.mode)

    def updater(cfg: dict[str, Any]) -> None:
        cfg["default_project_mode"] = mode

    _project_coordination_state.update_workplace_coordination(workplace_root, updater)
    print(f"UPDATED: {rel(workplace_root / 'workplace.yaml', workplace_root)}")
    return command_workplace_mode_status(argparse.Namespace(workplace=str(workplace_root), json=args.json))


def command_workplace_mode_doctor(args: argparse.Namespace) -> int:
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace))
    checks = []
    manifest = workplace_root / "workplace.yaml"
    checks.append(check("PASS" if manifest.is_file() else "FAIL", "workplace.yaml found"))
    if manifest.is_file():
        cfg = _project_coordination_reader.workplace(manifest)
        checks.append(check("PASS", f"default_project_mode is {cfg['default_project_mode']}"))
        checks.append(check("PASS", f"director_enabled is {str(bool(cfg.get('director_enabled'))).lower()}"))
        if cfg.get("director_office_enabled") or cfg.get("director_enabled"):
            checks.append(check("PASS" if _project_coordination_state.director_office_exists(workplace_root, cfg) else "WARN", "Director Office exists"))
    return print_checks(checks)


def command_project_mode_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    payload = _project_coordination_state.effective_project_coordination(project_root, getattr(args, "workplace", None))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"PROJECT: {payload['project_id']}")
        print(f"PROJECT_MODE: {payload['project_mode']}")
        print(f"WORKPLACE_DEFAULT_PROJECT_MODE: {payload['workplace_default_project_mode']}")
        print(f"EFFECTIVE_MODE: {payload['effective_mode']}")
        print(f"DIRECTOR_AVAILABLE: {str(bool(payload['director_available'])).lower()}")
        print(f"DIRECTOR_REQUIRED: {str(bool(payload['director_required'])).lower()}")
    return 0


def command_project_mode_set(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = _run_task_inputs.require_flow_root(project_root)
    mode = _project_coordination_reader.project_mode(args.mode)
    if mode == "organized":
        status = _project_coordination_state.effective_project_coordination(project_root, getattr(args, "workplace", None))
        if not status["workplace_director_enabled"]:
            raise SystemExit("FAIL: organized project mode requires workplace director_enabled=true")
        workplace_root = Path(str(status["workplace_root"])) if status.get("workplace_root") else None
        if workplace_root and (args.init_office or status.get("workplace_director_office_enabled")):
            initialize_director_office(workplace_root)
        elif not status.get("director_office_exists"):
            raise SystemExit("FAIL: organized project mode requires an initialized Director Office; rerun with --init-office or enable workplace Director Office")
    manifest = flow_root / "process-forge.yaml"
    data = read_yaml_file(manifest)
    coordination = data.get("coordination") if isinstance(data.get("coordination"), dict) else _project_coordination_reader.project_defaults()
    director = coordination.get("director") if isinstance(coordination.get("director"), dict) else {}
    coordination["mode"] = mode
    director.setdefault("use_workplace_director", True)
    director.setdefault("inbox_submit_required", False)
    coordination["director"] = director
    data["coordination"] = coordination
    _core_common_yaml_io.write_yaml_file(manifest, data)
    write_project_context_snapshot_outputs(project_root)
    print(f"UPDATED: {rel(manifest, project_root)}")
    return command_project_mode_status(argparse.Namespace(project_root=str(project_root), workplace=getattr(args, "workplace", None), json=args.json))


def command_project_mode_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    checks = coordination_doctor_checks(project_root, getattr(args, "workplace", None))
    return print_checks(checks)




def command_director_inbox_submit(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else None
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace)) if args.workplace else None
    if project_root:
        _run_task_inputs.require_flow_root(project_root)
        status = _project_coordination_state.effective_project_coordination(project_root, str(workplace_root) if workplace_root else None)
        workplace_root = Path(str(status["workplace_root"])) if status.get("workplace_root") else workplace_root
        if status["effective_mode"] == "simple" and not args.allow_simple_submit and args.message_type != "operator_note":
            message = "\n".join(
                [
                    "FAIL: project is in simple coordination mode.",
                    "Director inbox is available at the workplace, but this project is not organized.",
                    "Run:",
                    "  pf project-mode set --project-root <project> --mode organized",
                    "or submit as workspace-level/operator note if appropriate.",
                ]
            )
            if args.json:
                print(json.dumps({"status": "fail", "error": message, "effective_mode": "simple"}, indent=2, sort_keys=True))
                return 1
            raise SystemExit(message)
        if status["effective_mode"] == "organized" and not status["workplace_director_enabled"]:
            raise SystemExit("FAIL: workplace Director is not enabled")
        coordination = status
    else:
        if not workplace_root:
            raise SystemExit("FAIL: director-inbox-submit requires --project-root or --workplace")
        cfg = _project_coordination_reader.workplace(workplace_root / "workplace.yaml")
        if not cfg.get("director_enabled"):
            raise SystemExit("FAIL: workplace Director is not enabled")
        coordination = {"effective_mode": "workspace", "workplace_root": normalize_path_string(str(workplace_root))}
    if not workplace_root:
        raise SystemExit("FAIL: workplace root could not be resolved")
    paths = initialize_director_office(workplace_root)
    payload = _project_coordination_state.director_message_payload(workplace_root, project_root, args.message_type, args.content or "", coordination)
    message_path = paths["inbox_path"] / f"{payload['id']}.yaml"
    _core_common_yaml_io.write_yaml_file(message_path, payload)
    if args.json:
        print(json.dumps({"status": "pass", "message": rel(message_path, workplace_root), "payload": payload}, indent=2, sort_keys=True))
    else:
        print(f"WROTE: {rel(message_path, workplace_root)}")
    return 0




def command_director_case_refresh(args: argparse.Namespace) -> int:
    workplace_root = _project_coordination_state.normalize_workplace_path(Path(args.workplace))
    paths = initialize_director_office(workplace_root)
    include_simple = bool(args.include_simple)
    inbox_project_ids = _project_coordination_state.director_inbox_project_ids(workplace_root)
    refreshed: list[str] = []
    for snapshot_path in sorted(workplace_root.glob("projects/*/.pf/runtime/cache/workplace-context.snapshot.yaml")):
        snapshot = load_yaml_document(snapshot_path)
        project_data = snapshot.get("project") if isinstance(snapshot, dict) else {}
        project_id_value = str(project_data.get("id") or snapshot_path.parents[3].name) if isinstance(project_data, dict) else snapshot_path.parents[3].name
        coordination = snapshot.get("workplace_coordination") if isinstance(snapshot.get("workplace_coordination"), dict) else {}
        effective_mode = str(coordination.get("effective_mode") or "simple")
        if effective_mode != "organized" and project_id_value not in inbox_project_ids and not include_simple:
            continue
        case_path = paths["cases_path"] / f"{safe_id(project_id_value, 'project')}.yaml"
        _core_common_yaml_io.write_yaml_file(
            case_path,
            {
                "schema_version": 1,
                "project_id": project_id_value,
                "status": "open",
                "effective_mode": effective_mode,
                "refreshed_at": _core_common_clock.now_utc(),
                "source": normalize_path_string(str(snapshot_path)),
                "reason": "organized" if effective_mode == "organized" else "open_inbox_or_include_simple",
            },
        )
        refreshed.append(rel(case_path, workplace_root))
    if args.json:
        print(json.dumps({"status": "pass", "cases": refreshed}, indent=2, sort_keys=True))
    else:
        for item in refreshed:
            print(f"WROTE: {item}")
        if not refreshed:
            print("PASS: no director cases required")
    return 0


def command_error_route(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    mode = str(args.mode or "none")
    if mode not in ERROR_WORKFLOW_MODES:
        raise SystemExit("FAIL: error workflow mode must be none, director_inbox, route_to_process, or needs_operator")
    fallback = str(args.fallback_if_no_director or "fail_validation")
    if fallback not in ERROR_WORKFLOW_FALLBACKS:
        raise SystemExit("FAIL: fallback_if_no_director must be needs_operator or fail_validation")
    coordination = _project_coordination_state.effective_project_coordination(project_root, getattr(args, "workplace", None))
    result: dict[str, Any] = {
        "schema_version": 1,
        "created_at": _core_common_clock.now_utc(),
        "project_id": project_id(project_root),
        "effective_mode": coordination["effective_mode"],
        "requested_mode": mode,
        "result_mode": mode,
        "status": "recorded",
        "summary": args.summary or "",
    }
    if mode == "director_inbox" and coordination["effective_mode"] == "organized":
        code = command_director_inbox_submit(
            argparse.Namespace(
                project_root=str(project_root),
                workplace=getattr(args, "workplace", None),
                message_type="error_report",
                content=args.summary or "",
                allow_simple_submit=False,
                json=False,
            )
        )
        if code:
            return code
        result["result_mode"] = "director_inbox"
    elif mode == "director_inbox":
        if fallback == "fail_validation":
            raise SystemExit("FAIL: director_inbox error workflow requires effective organized project mode")
        result["result_mode"] = "needs_operator"
        result["status"] = "needs_operator"
    elif mode == "route_to_process":
        routes = locate_flow_root(project_root) / "process-routes.yaml"
        if not routes.is_file():
            raise SystemExit("FAIL: route_to_process requires .pf/process-routes.yaml")
        result["route"] = rel(routes, project_root)
    elif mode == "needs_operator":
        result["status"] = "needs_operator"
    output = locate_flow_root(project_root) / "artifacts" / "error-workflow" / f"error-{uuid.uuid4().hex[:12]}.yaml"
    _core_common_yaml_io.write_yaml_file(output, result)
    if args.json:
        print(json.dumps({"status": "pass", "path": rel(output, project_root), "result": result}, indent=2, sort_keys=True))
    else:
        print(f"WROTE: {rel(output, project_root)}")
        print(f"RESULT_MODE: {result['result_mode']}")
    return 0




































































































PROJECT_OVERRIDE_MODES = {"overlay", "extension", "replace", "parameterize", "disable", "fork"}




















def load_specialization(workplace_manifest: Path | None, specialization_id: str, project_root: Path | None = None) -> dict[str, Any] | None:
    return _specialization_catalog_reader.manifest_index(workplace_manifest, project_root).get(_specialization_catalog_reader.resource_id(specialization_id))


































def resolve_specialization_context(
    project_root: Path,
    workplace_manifest: Path | None,
    *,
    platform_ids: list[str],
    process_id: str | None = None,
    specialization_ids: list[str] | None = None,
    platform_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_ids = [_specialization_catalog_reader.resource_id(item) for item in (specialization_ids or [])]
    platform_resolution = platform_resolution or _platform_contract_resolver.resolve(workplace_manifest, platform_ids, project_root=project_root)
    required = {
        "knowledge_packages": set(platform_resolution.get("required_knowledge_packages", [])),
        "tools": set(platform_resolution.get("required_tools", [])),
        "mcp": set(platform_resolution.get("required_mcp", [])),
        "templates": set(platform_resolution.get("required_templates", [])),
    }
    recommended = {
        "knowledge_packages": set(platform_resolution.get("recommended_knowledge_packages", [])),
        "tools": set(platform_resolution.get("recommended_tools", [])),
        "mcp": set(platform_resolution.get("recommended_mcp", [])),
        "templates": set(platform_resolution.get("recommended_templates", [])),
    }
    optional = {key: set() for key in _core_resources_buckets.RESOURCE_GROUP_KEYS}
    excluded = {key: set() for key in _core_resources_buckets.RESOURCE_GROUP_KEYS}
    reasons: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    selected_specializations: list[dict[str, Any]] = []
    provided_capabilities: set[str] = set()
    capability_providers: dict[str, list[dict[str, Any]]] = {}
    for _manifest_path, pack_manifest in active_official_pack_records(workplace_manifest):
        pack_id = str(pack_manifest.get("id") or "")
        provided = pack_manifest.get("provides") if isinstance(pack_manifest.get("provides"), dict) else {}
        knowledge_packages = {
            str(item)
            for item in as_list(provided.get("knowledge_packages"))
            if str(item)
        }
        if knowledge_packages:
            optional["knowledge_packages"].update(knowledge_packages)
            reasons.append(
                {
                    "source": pack_id,
                    "reason": "active official process pack knowledge packages merged",
                }
            )
    index = _specialization_catalog_reader.manifest_index(workplace_manifest, project_root)
    for specialization_id in selected_ids:
        spec = index.get(specialization_id)
        if not spec:
            conflicts.append({"id": specialization_id, "kind": "specialization", "reason": "specialization not found"})
            continue
        specialization_overrides = _project_override_reader.project_specialization_override_entries(project_root, specialization_id)
        for override_entry in specialization_overrides:
            mode = str(override_entry.get("mode") or "extension")
            if mode not in PROJECT_OVERRIDE_MODES:
                conflicts.append({"id": specialization_id, "kind": "specialization", "reason": f"unsupported project override mode: {mode}"})
                continue
            overlay = _project_override_reader.load_project_override_document(project_root, override_entry)
            if overlay:
                spec, overlay_notes = _project_override_reader.apply_specialization_overlay(spec, overlay, mode)
                for note in overlay_notes:
                    reasons.append({"source": "project_override", "target": specialization_id, "reason": note})
        resources = _core_resources_buckets.default_resource_buckets()
        _core_resources_buckets.merge_resource_buckets(resources, spec.get("resources") if isinstance(spec.get("resources"), dict) else {})
        spec_capabilities = set(str(item) for item in as_list(spec.get("provides_capabilities")) if str(item))
        matched_bindings: list[dict[str, Any]] = []
        for binding in spec.get("platform_bindings", []) if isinstance(spec.get("platform_bindings"), list) else []:
            if isinstance(binding, dict) and _project_platform_selection_service.binding_matches(binding, platform_ids, platform_resolution.get("platform_stack", []), process_id):
                matched_bindings.append(binding)
                _core_resources_buckets.merge_resource_buckets(resources, binding.get("resources") if isinstance(binding.get("resources"), dict) else {})
                spec_capabilities.update(str(item) for item in as_list(binding.get("provides_capabilities")) if str(item))
        for key in _core_resources_buckets.RESOURCE_GROUP_KEYS:
            required[key].update(resources["requires"][key])
            recommended[key].update(resources["recommends"][key])
            optional[key].update(resources["optional"][key])
            excluded[key].update(resources["excludes"][key])
        provided_capabilities.update(spec_capabilities)
        provider = _project_capability_resolution.resource_profile_capability_provider(specialization_id, resources)
        for capability in spec_capabilities:
            capability_providers.setdefault(capability, []).append(dict(provider))
        selected_specializations.append(
            {
                "id": specialization_id,
                "source": str(spec.get("__source") or "workplace"),
                # A selected workplace specialization is a private resolution
                # input.  Its absolute manifest path must never escape into a
                # public project-context snapshot; Runtime resolves it again
                # through the authorized workplace registry when needed.
                "path": rel(spec.get("__manifest_path"), project_root)
                if isinstance(spec.get("__manifest_path"), Path) and path_is_relative_to(spec["__manifest_path"], project_root)
                else "<private-specialization-ref>",
                "matched_bindings": [
                    {
                        "platforms": list_value(binding.get("platforms")),
                        "platform_stack_includes": list_value(binding.get("platform_stack_includes")),
                    }
                    for binding in matched_bindings
                ],
                "provides_capabilities": _core_resources_buckets.dedupe_sorted(list(spec_capabilities)),
                "sha256": _project_override_reader.sha256_optional_file(spec.get("__manifest_path") if isinstance(spec.get("__manifest_path"), Path) else None),
            }
        )
        reasons.append({"source": specialization_id, "reason": "selected specialization resources merged"})
    applied_overrides: list[dict[str, Any]] = []
    for entry in _project_override_reader.project_override_entries(project_root):
        kind = str(entry.get("kind") or "")
        target = str(entry.get("target") or "")
        mode = str(entry.get("mode") or "extension")
        if mode not in PROJECT_OVERRIDE_MODES:
            conflicts.append({"id": target, "kind": kind, "reason": f"unsupported project override mode: {mode}"})
            continue
        base_path = None
        if kind == "specializations":
            spec = index.get(_specialization_catalog_reader.resource_id(target))
            base_path = spec.get("__manifest_path") if isinstance(spec, dict) and isinstance(spec.get("__manifest_path"), Path) else None
        applied = _project_override_reader.resolved_override_record(project_root, entry, base_path)
        applied_overrides.append(applied)
        if kind in _core_resources_buckets.RESOURCE_GROUP_KEYS:
            if mode == "disable":
                excluded[kind].add(target)
                reasons.append({"source": "project_override", "target": target, "reason": f"{kind} disabled"})
            elif mode in {"extension", "parameterize", "overlay", "replace", "fork"}:
                bucket = "required" if entry.get("required") is True else "recommended"
                (required if bucket == "required" else recommended)[kind].add(str(entry.get("project_package") or target))
                reasons.append({"source": "project_override", "target": target, "reason": f"{kind} {mode} applied"})
        elif kind == "specializations":
            reasons.append({"source": "project_override", "target": target, "reason": f"specialization {mode} recorded"})
    activated = {}
    for key in _core_resources_buckets.RESOURCE_GROUP_KEYS:
        recommended[key] -= required[key]
        activated_set = required[key].union(recommended[key]).union(optional[key])
        activated[key] = _project_override_reader.apply_resource_excludes(required[key], activated_set, excluded[key], conflicts, "project/specialization", key)
    registry_capabilities, registry_providers = _project_capability_resolution.active_registry_capability_providers(workplace_manifest, activated)
    provided_capabilities.update(registry_capabilities)
    for capability, providers in registry_providers.items():
        capability_providers.setdefault(capability, []).extend(providers)
    effective_fingerprints = {f"{item['kind']}:{item['target']}": item["effective_fingerprint"] for item in applied_overrides}
    execution_route, route_conflicts = _project_capability_resolution.build_execution_route(project_root, process_id)
    conflicts.extend(route_conflicts)
    capability_resolution = _project_capability_resolution.build_capability_resolution(execution_route, provided_capabilities, capability_providers, activated)
    for item in capability_resolution["unsatisfied"]:
        conflicts.append({"id": item["capability"], "kind": "capability", "source": item["required_by"], "reason": item["reason"]})
    active_resource_profile = {
        "selected_platform": [_platform_contract_reader.contract_id(item) for item in platform_ids],
        "platform_stack": platform_resolution.get("platform_stack", []),
        "selected_specializations": selected_specializations,
        "available_knowledge_packages": _core_resources_buckets.dedupe_sorted(list(required["knowledge_packages"].union(recommended["knowledge_packages"]).union(optional["knowledge_packages"]))),
        "activated_knowledge_packages": _core_resources_buckets.dedupe_sorted(list(activated["knowledge_packages"])),
        "excluded_knowledge_packages": _core_resources_buckets.dedupe_sorted(list(excluded["knowledge_packages"])),
        "available_tools": _core_resources_buckets.dedupe_sorted(list(required["tools"].union(recommended["tools"]).union(optional["tools"]))),
        "activated_tools": _core_resources_buckets.dedupe_sorted(list(activated["tools"])),
        "excluded_tools": _core_resources_buckets.dedupe_sorted(list(excluded["tools"])),
        "available_mcp": _core_resources_buckets.dedupe_sorted(list(required["mcp"].union(recommended["mcp"]).union(optional["mcp"]))),
        "activated_mcp": _core_resources_buckets.dedupe_sorted(list(activated["mcp"])),
        "excluded_mcp": _core_resources_buckets.dedupe_sorted(list(excluded["mcp"])),
        "activated_templates": _core_resources_buckets.dedupe_sorted(list(activated["templates"])),
        "excluded_templates": _core_resources_buckets.dedupe_sorted(list(excluded["templates"])),
        "provided_capabilities": _core_resources_buckets.dedupe_sorted(list(provided_capabilities)),
        "applied_project_overrides": applied_overrides,
        "effective_resources": [
            {"kind": key, "id": item, "status": "activated"}
            for key in _core_resources_buckets.RESOURCE_GROUP_KEYS
            for item in _core_resources_buckets.dedupe_sorted(list(activated[key]))
        ],
        "effective_fingerprints": effective_fingerprints,
        "resolution_reasons": reasons,
        "conflicts": conflicts,
    }
    resolution_status = "needs_resources" if capability_resolution["unsatisfied"] else ("conflict" if conflicts else "resolved")
    return {
        **active_resource_profile,
        "status": resolution_status,
        "process": process_id or "",
        "active_resource_profile": active_resource_profile,
        "execution_route": execution_route,
        "capability_resolution": capability_resolution,
        "provided_capabilities": active_resource_profile["provided_capabilities"],
    }








def finalize_project_onboarding_doctor_artifacts(project_root: Path, status: int, output: str) -> None:
    flow_root = project_root / PROJECT_FLOW_ROOT
    result = "pass" if status == 0 else "fail"
    report = flow_root / "artifacts" / "project-onboarding-report.md"
    existing = report.read_text(encoding="utf-8", errors="replace") if report.is_file() else "# Project Onboarding Report\n"
    content = existing.rstrip() + f"""

## Doctor Status

{result}

## Doctor Output

The full doctor diagnostic is intentionally not copied into this public
artifact. Run `pf doctor-project --project-root .` locally for the current
diagnostic output.

## Fix Hints

{"- None required." if status == 0 else "- Rerun `pf doctor-project --project-root .`, resolve its FAIL lines, then rerun deterministic repair."}
"""
    write_file(report, content, force=True)


def execute_project_initialization(request: dict[str, Any], files: dict[Path, str]) -> dict[str, Any]:
    """CLI writer adapter used only by project_initialization.initialize_project()."""
    from processforge_core.agent_entry.migration import TARGETS as entry_targets

    project_root = request["project_root"]
    entry_plan = request.get("agent_entry_plan")
    if not isinstance(entry_plan, dict):
        raise project_initialization.ProjectInitializationError("entry_plan_required")
    # Revalidate ownership/budgets before events or ordinary initialization writes.
    entry_result = project_initialization.apply_agent_entry(project_root, entry_plan)
    if entry_result["status"] != "complete":
        return entry_result
    project_type = request.get("project_type")
    force = bool(request.get("force", False))
    flow_root = project_root / PROJECT_FLOW_ROOT
    for dirname in PROJECT_FLOW_DIRS:
        (flow_root / dirname).mkdir(parents=True, exist_ok=True)
    _process_event_recorder.emit_process_event(project_root, "project.onboarding.started", process_id="project-onboarding", process_version="1.0.0", payload={"command": request.get("command", "project-onboard")})
    protected = {project_root / name for name in entry_targets}
    # Legacy START is not initializer-owned, even for an old caller's file map.
    protected.add(flow_root / "START_AGENT_HERE.md")
    results = [write_file(path, content, force=force) for path, content in files.items()
               if path not in protected]
    results.append(append_gitignore_entries(project_root / ".gitignore", PROJECT_PRIVATE_GITIGNORE, force=force))
    from processforge_core.project.host_integration import optional_host_integration_status
    codex_integration = optional_host_integration_status(project_root, sys.modules[__name__])
    _process_event_recorder.emit_process_event(project_root, "project.flow_root.created", process_id="project-onboarding", process_version="1.0.0", payload={"flow_root": PROJECT_FLOW_ROOT})
    _process_event_recorder.emit_process_event(project_root, "project.platform.detected", process_id="project-onboarding", process_version="1.0.0", payload={"project_type": project_type or "auto"})
    snapshot_status, snapshot_paths, _snapshot, _old_reasons = write_project_context_snapshot_outputs(project_root)
    _process_event_recorder.emit_process_event(project_root, "project.snapshot.refreshed", process_id="project-onboarding", process_version="1.0.0", payload={"status": snapshot_status, "paths": {key: rel(value, project_root) for key, value in snapshot_paths.items()}})
    _process_event_recorder.emit_process_event(project_root, "launcher.project_runtime.created", process_id="project-onboarding", process_version="1.0.0", payload={"path": ".pf/runtime/bin/pf.py"})
    _process_event_recorder.emit_process_event(project_root, "assignment.created", process_id="project-onboarding", process_version="1.0.0", assignment_id_value="first-assignment", assignment_path=".pf/assignments/first-assignment.yaml", payload={"path": ".pf/assignments/first-assignment.yaml"})
    doctor_status, doctor_output = run_command_capture(command_doctor_project, argparse.Namespace(project_root=str(project_root)))
    finalize_project_onboarding_doctor_artifacts(project_root, doctor_status, doctor_output)
    _process_event_recorder.emit_process_event(
        project_root,
        "project.doctor.passed" if doctor_status == 0 else "project.doctor.failed",
        process_id="project-onboarding",
        process_version="1.0.0",
        payload={"status": "pass" if doctor_status == 0 else "fail"},
    )
    search_index: dict[str, Any] | None = None
    workplace_manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, request.get("workplace"))
    if workplace_manifest:
        search_index = search_index_maintenance_for_known_projects(
            workplace_manifest.parent,
            reason="project-onboarding",
            project_roots=[project_root],
        )
    _process_event_recorder.emit_process_event(project_root, "project.onboarding.completed", process_id="project-onboarding", process_version="1.0.0", payload={"files": [rel(result.target, project_root) for result in results], "doctor_status": doctor_status})
    return {
        "status": "complete" if doctor_status == 0 else "blocked",
        "agent_entry": entry_result["agent_entry"],
        "project": {"id": project_id(project_root)},
        "created_or_reused": [{"path": rel(result.target, project_root), "status": result.status} for result in results]
        + [{"path": row["path"], "status": "reused" if row["action"] == "unchanged" else "written"} for row in entry_plan["files"]],
        "codex_integration": codex_integration,
        "snapshot": {"status": snapshot_status, "id": _snapshot.get("snapshot", {}).get("id") if isinstance(_snapshot.get("snapshot"), dict) else None},
        "search_index": search_index,
        "doctor": {"status": "pass" if doctor_status == 0 else "fail"},
        "next_action": "continue" if doctor_status == 0 else "resolve_doctor_failures",
    }


def execute_project_repair(project_root: Path, *, workplace: str | None, reason: str) -> dict[str, Any]:
    """Deterministic refresh-only repair adapter; semantic artifacts are untouched."""
    status, paths, snapshot, _old_reasons = write_project_context_snapshot_outputs(project_root, explicit_workplace=workplace)
    doctor_status, doctor_output = run_command_capture(command_doctor_project, argparse.Namespace(project_root=str(project_root)))
    finalize_project_onboarding_doctor_artifacts(project_root, doctor_status, doctor_output)
    _process_event_recorder.emit_process_event(project_root, "context.snapshot.refreshed", process_id="project-initialization", process_version="1.0.0", payload={"status": status, "reason": reason, "paths": {key: rel(path, project_root) for key, path in paths.items()}})
    search_index: dict[str, Any] | None = None
    workplace_manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, workplace)
    if workplace_manifest:
        search_index = search_index_maintenance_for_known_projects(
            workplace_manifest.parent,
            reason="project-repair",
            project_roots=[project_root],
        )
    return {
        "status": "complete" if doctor_status == 0 else "blocked",
        "repair_action": "refresh_context",
        "snapshot": {"status": status, "id": snapshot.get("snapshot", {}).get("id") if isinstance(snapshot.get("snapshot"), dict) else None},
        "search_index": search_index,
        "doctor": {"status": "pass" if doctor_status == 0 else "fail"},
        "next_action": "continue" if doctor_status == 0 else "resolve_doctor_failures",
    }


def _project_initialization_error(exc: project_initialization.ProjectInitializationError) -> SystemExit:
    hints = {
        "apply_required": "Rerun with --apply (or MCP apply: true).",
        "workplace_manifest_required": "Initialize the workplace first, or explicitly allow a missing workplace where that is safe.",
        "project_root_missing": "Create the project root before a dry run, or use --apply for greenfield onboarding.",
        "project_not_initialized": "Use project-onboard for a new project; repair only accepts an existing .pf project.",
        "codex_integration_unsupported": "Use a ProcessForge distribution that includes the Codex hook integration service.",
    }
    return SystemExit(f"FAIL: {exc.code}. {hints.get(exc.code, 'Check the initialization request.')}")


def project_entry_budget_input(args: argparse.Namespace) -> Any:
    from processforge_core.agent_entry.contract import EntryError, decode_json

    name = getattr(args, "entry_budget_file", None)
    if not name:
        return None
    try:
        with Path(name).expanduser().open("rb") as stream:
            return decode_json(stream.read(65537), 65536)
    except (EntryError, OSError) as exc:
        raise project_initialization.ProjectInitializationError(
            exc.reason if isinstance(exc, EntryError) else "budget_file_unreadable") from exc


def command_init_project(args: argparse.Namespace) -> int:
    request = {
        "project_root": args.project_root,
        "workplace": args.workplace,
        "answers_path": args.answers,
        "project_type": getattr(args, "project_type", None),
        "coordination_mode": getattr(args, "coordination_mode", None),
        "platforms": list(getattr(args, "platform", []) or []),
        "specializations": list(getattr(args, "specialization", []) or []),
        "process": getattr(args, "process", None),
        "force": bool(args.force),
        "allow_missing_workplace": bool(args.allow_missing_workplace),
        "apply": args.apply is True,
        "command": getattr(args, "command", "project-onboard"),
    }
    try:
        request["entry_budget_policy"] = project_entry_budget_input(args)
        result = project_initialization.initialize_project(request, sys.modules[__name__], build_project_files=_project_file_templates.build_project_files)
    except project_initialization.ProjectInitializationError as exc:
        raise _project_initialization_error(exc) from exc
    if result.get("applied") is not True:
        print(dump_yaml(result), end="")
        return 1 if result.get("status") == "blocked" else 0
    payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    print(dump_yaml(payload), end="")
    return 0 if payload.get("doctor", {}).get("status") == "pass" else 1


def command_project_init_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().absolute()
    payload = project_initialization.status(project_root, sys.modules[__name__], workplace=getattr(args, "workplace", None))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if getattr(args, "json", False) else dump_yaml(payload))
    return 0


def command_project_init_repair(args: argparse.Namespace) -> int:
    request = {"project_root": args.project_root, "workplace": getattr(args, "workplace", None), "repair_action": args.repair_action, "reason": args.reason, "apply": args.apply is True}
    try:
        request["entry_budget_policy"] = project_entry_budget_input(args)
        result = project_initialization.repair_project(request, sys.modules[__name__], build_project_files=_project_file_templates.build_project_files)
    except project_initialization.ProjectInitializationError as exc:
        raise _project_initialization_error(exc) from exc
    print(dump_yaml(result), end="")
    payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    if result.get("applied") is not True:
        return 1 if result.get("status") == "blocked" else 0
    if payload.get("doctor") is None:
        return 0 if payload.get("status") == "complete" else 1
    return 0 if payload.get("doctor", {}).get("status") == "pass" else 1


def gitignore_effectively_protects(project_root: Path, entry: str) -> bool | None:
    if not (project_root / ".git").exists():
        return None
    probe = entry.rstrip("/")
    if not probe:
        return None
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", probe],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def default_start_agent_here(project_root: Path) -> str:
    from processforge_core.agent_entry.start_prompt import render_start_prompt
    return render_start_prompt()


def start_agent_run_block(project_root: Path) -> str:
    """Compatibility helper: no discovery or selection of diagnostic Runs."""
    from processforge_core.agent_entry.start_prompt import WORK_GUIDANCE
    return WORK_GUIDANCE


def refresh_start_agent_run_block(project_root: Path, text: str) -> str:
    """Pure recognized-content refresh; customized text is never spliced away."""
    from processforge_core.agent_entry.start_prompt import load_start_source, project_start_content
    generated, _source_digest, legacy = load_start_source()
    raw, _action = project_start_content(text.encode("utf-8"), generated, legacy)
    return raw.decode("utf-8")




def command_first_run(args: argparse.Namespace) -> int:
    workplace_args = argparse.Namespace(
        command="workplace-init",
        root=args.workplace,
        answers=None,
        dry_run=args.dry_run,
        apply=args.apply,
        force=args.force,
        interactive=args.interactive,
    )
    project_args = argparse.Namespace(
        command="project-onboard",
        project_root=args.project_root,
        workplace=args.workplace,
        project_type=args.project_type,
        answers=None,
        dry_run=args.dry_run,
        apply=args.apply,
        force=args.force,
        interactive=args.interactive,
        allow_missing_workplace=False,
    )
    workplace_status = command_init_workplace(workplace_args)
    if workplace_status != 0:
        return workplace_status
    return command_init_project(project_args)


RELEASE_REQUIRED_PATHS = [
    "README.md",
    "README.ru.md",
    "QUICKSTART.md",
    "QUICKSTART.ru.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE",
    "requirements.txt",
    "AGENTS.md",
    ".gitignore",
    ".processforge-releaseignore",
    ".pf/AGENTS.md",
    ".pf/process-forge.yaml",
    ".pf/hooks.yaml",
    "checksums/processforge.sha256",
    "bin/pf.py",
    "bin/pf",
    "bin/pf.bat",
    "src/processforge_core",
    "tools",
    "schemas",
    "templates",
    "processes/core",
    "processes/user",
    "processes/custom",
    "packs/official",
    "prompts",
    "docs",
    "examples",
    "policies",
    "seeds",
]
RELEASE_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".sh", ".bat"}
RELEASE_GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
RELEASE_GENERATED_SUFFIXES = {".pyc", ".pyo"}






















def release_required_path_exists(root: Path, archive_path: str) -> bool:
    return (root / archive_path).exists()


def release_agent_entry_checks(root: Path) -> list[Check]:
    """Verify explicit source projections; packaging never generates instructions."""
    from processforge_core.agent_entry.contract import EntryError, block_span, load_contract

    try:
        contract = load_contract(root)
    except EntryError as exc:
        return [check_with_hint(
            "FAIL", f"release agent entry source invalid: {exc.reason}",
            "The versioned contract source, metadata and derived template must agree.",
            "restore the reviewed contract source and derived template before packaging",
        )]
    checks: list[Check] = []
    for name in ("AGENTS.md", ".pf/AGENTS.md"):
        try:
            raw = release_file_content(root / name)
            span = block_span(raw, contract)
            if span is None:
                raise EntryError("entry_contract_missing")
            if raw[span[0]:span[1]] != contract.raw:
                raise EntryError("entry_contract_outdated")
        except (EntryError, OSError) as exc:
            reason = exc.reason if isinstance(exc, EntryError) else "entry_projection_unavailable"
            checks.append(check_with_hint(
                "FAIL", f"release agent entry invalid: {name}: {reason}",
                "Root and hidden source projections must contain the current startup contract; hidden files are not root aliases.",
                "prepare and review explicit current entry projections in the source checkout before packaging",
            ))
        else:
            checks.append(check("PASS", f"release agent entry current: {name}: {contract.version} sha256:{contract.sha256}"))
    return checks


def release_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    patterns = _release_source_policy.release_ignore_patterns(root)
    public_support_policy = _context_contract_inputs.documents.policy("public-support-policy.yaml", root, distribution_root=ROOT)
    public_support_policy_loaded = bool(policy_entries(public_support_policy, "blocked_public_surface_patterns"))
    public_support_policy_failed = False
    if not patterns:
        checks.append(
            check_with_hint(
                "FAIL",
                ".processforge-releaseignore missing or empty",
                "The release packer needs an explicit exclusion policy.",
                "create .processforge-releaseignore with runtime, private, cache, IDE, and archive exclusions",
            )
        )
    else:
        checks.append(check("PASS", ".processforge-releaseignore loaded"))

    for required in RELEASE_REQUIRED_PATHS:
        checks.append(
            check_with_hint(
                "FAIL",
                f"required release path missing: {required}",
                "The v0.1 archive contract lists this path as part of the public distribution.",
                f"restore or generate {required} before release-pack",
            )
            if not release_required_path_exists(root, required)
            else check("PASS", f"required release path present: {required}")
        )

    checks.extend(release_agent_entry_checks(root))

    core_violations = _public_source_policy.core_hardcode_violations(root)
    if core_violations:
        for violation in core_violations:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"core platform hardcode policy violation: {violation}",
                    "ProcessForge core must load platform/package behavior from manifests and policies, not concrete platform ids in Python logic.",
                    "move the rule to a seed manifest or policy YAML and keep tools/processforge.py generic",
                )
            )
    elif _context_contract_inputs.documents.policy("core-hardcode-policy.yaml", root, distribution_root=ROOT):
        checks.append(
            check("PASS", "core platform hardcode policy passed")
        )

    for archive_path, path in _release_source_policy.release_source_files(root):
        if _release_source_policy.release_ignore_match(archive_path, patterns):
            continue
        forbidden = _release_source_policy.release_path_is_forbidden(archive_path)
        if forbidden:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{archive_path}: {forbidden}",
                    "Release archives must not contain runtime, private, cache, script-wrapper, or previous archive artifacts.",
                    "python tools/processforge.py clean --root . --release",
                )
            )
            continue
        if path.suffix.lower() in RELEASE_TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            release_text_group = archive_path.split("/", 1)[0]
            user_facing_text = release_text_group in {"README.md", "QUICKSTART.md", "CHANGELOG.md", "VERSION", "AGENTS.md", "docs", "prompts", "examples", "processes", "packages", "packs", "templates", "policies", "seeds"}
            if release_text_group in {"README.md", "QUICKSTART.md", "docs", "prompts", "examples"} and _release_source_policy.forbidden_powershell_reference(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public release text references PowerShell/.ps1",
                        "Public instructions must use supported Python entry points; legacy .ps1 wrapper references are unsupported.",
                        "replace the command with python bin/pf.py or python .pf/runtime/bin/pf.py",
                    )
                )
            if release_text_group in {"docs", "prompts", "examples", "templates", "packages", "processes"} and _project_platform_selection_service.forbidden_base_reference(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public release text introduces a base-technology platform",
                        "Base languages and web technologies are knowledge packages and capabilities in v0.1, not platform contracts.",
                        "replace base-technology platform examples with docs.* knowledge package examples",
                    )
                )
            for violation in _public_source_policy.public_support_policy_violations(archive_path, text, public_support_policy):
                public_support_policy_failed = True
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: {violation}",
                        "Built-in seeds, examples, templates, packages, processes, and prompts must stay neutral unless a support pack is explicitly shipped.",
                        "replace the public sample with neutral ids or add an explicit policy exception for an intentional support pack",
                    )
                )
            if user_facing_text and not is_public_path_safe(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public text contains a private absolute path",
                        "Public release files must be portable across machines.",
                        "replace local filesystem values with path_ref, placeholders, or relative paths",
                    )
                )
            if user_facing_text and contains_secret_value(text):
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{archive_path}: public text appears to contain a secret value",
                        "Release files cannot contain credentials, tokens, or private keys.",
                        "remove the secret and keep only a named secret reference",
                    )
                )
    if public_support_policy_loaded and not public_support_policy_failed:
        checks.append(check("PASS", "public support surface policy passed"))
    if not any(item.level == "FAIL" for item in checks):
        checks.append(check("PASS", "release surface excludes runtime/private/cache/script/archive artifacts"))
    return checks








def public_release_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    dist = root / "dist"
    stale: list[str] = []
    current_version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else ""
    generated_current = {
        "processforge.zip",
        "processforge.manifest.json",
        f"processforge-{current_version}.zip",
        f"processforge-{current_version}.manifest.json",
    }
    if dist.is_dir():
        for path in sorted(dist.glob("processforge*")):
            if path.name in generated_current:
                continue
            if path.suffix.lower() == ".zip" or path.name.endswith(".manifest.json"):
                stale.append(rel(path, root))
    if stale:
        checks.extend(check("FAIL", f"stale public distribution artifact: {item}") for item in stale)
    else:
        checks.append(check("PASS", "dist contains no stale ProcessForge release artifacts"))

    tagged_warns: list[str] = []
    parity_root = locate_flow_root(root) / "reviews" / "parity"
    if parity_root.is_dir():
        for path in sorted(parity_root.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "WARN To Fix Before Public Release" in text:
                tagged_warns.append(rel(path, root))
    if tagged_warns:
        checks.extend(check("FAIL", f"parity WARN tagged before public release: {item}") for item in tagged_warns)
    else:
        checks.append(check("PASS", "no parity WARN remains tagged before public release"))

    checks.extend(_public_source_policy.russian_mojibake_checks(root))
    return checks


def command_release_check(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    return print_checks(release_checks(root))


def safe_remove_generated_path(path: Path, root: Path) -> bool:
    def retry_readonly_removal(func: Any, target: str, _exc_info: Any) -> None:
        """Retry an approved generated-file removal after clearing Windows ReadOnly.

        Git object files copied into a temporary release stage can retain the
        Windows ReadOnly attribute.  ``shutil.rmtree`` otherwise aborts the
        entire release cleanup even though the enclosing path has already
        passed this function's generated-path containment checks.
        """

        target_path = Path(target)
        target_path.chmod(target_path.stat().st_mode | stat.S_IWRITE)
        func(target)

    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        return False
    if path.is_dir() and resolved_path == (resolved_root / ".pf" / "runtime"):
        shutil.rmtree(path, onerror=retry_readonly_removal)
        return True
    if path.is_dir() and path.name in RELEASE_GENERATED_DIRS:
        shutil.rmtree(path, onerror=retry_readonly_removal)
        return True
    if path.is_file() and path.suffix.lower() in RELEASE_GENERATED_SUFFIXES:
        try:
            path.unlink()
        except PermissionError:
            path.chmod(path.stat().st_mode | stat.S_IWRITE)
            path.unlink()
        return True
    return False


def command_clean(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not args.release:
        print("WARN: nothing selected; use --release to remove safe generated release artifacts")
        return 0
    removed: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.name in {".git", ".idea", ".serena"}:
            continue
        if safe_remove_generated_path(path, root):
            removed.append(rel(path, root))
    for item in removed:
        print(f"REMOVED: {item}")
    print(f"PASS: release cleanup removed {len(removed)} generated paths.")
    return 0


def command_examples_check(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    examples = root / "examples"
    checks: list[Check] = []
    checks.append(check("PASS" if examples.is_dir() else "FAIL", "examples/ found"))
    for required in ["first-run", "resource-authoring", "process-authoring"]:
        base = examples / required
        checks.append(check("PASS" if base.is_dir() else "FAIL", f"examples/{required}/ found"))
        readmes = list(base.rglob("README.md")) if base.is_dir() else []
        checks.append(check("PASS" if readmes else "FAIL", f"examples/{required}/ has README files"))
    if examples.is_dir():
        for path in sorted(examples.rglob("*")):
            rel_path = rel(path, root)
            if path.is_dir() and path.name in {"runtime", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{rel_path}: stale generated directory",
                        "Examples must remain source examples, not runtime output snapshots.",
                        "remove generated runtime/cache data from examples",
                    )
                )
            if not path.is_file():
                continue
            if path.suffix.lower() == ".ps1":
                checks.append(check_with_hint("FAIL", f"{rel_path}: unsupported .ps1 file", "The release is Python-first.", "replace with python bin/pf.py examples"))
            if path.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                if _release_source_policy.forbidden_powershell_reference(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: mentions PowerShell/.ps1", "Public examples should not mention removed wrappers.", "use python bin/pf.py or python .pf/runtime/bin/pf.py"))
                if _project_platform_selection_service.forbidden_base_reference(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: introduces a base-technology platform", "Domain classifications belong to explicit process packs, not core platform contracts.", "move the data into an official or custom process pack and keep it inactive by default"))
                if not is_public_path_safe(text):
                    checks.append(check_with_hint("FAIL", f"{rel_path}: contains private absolute path", "Examples must be portable.", "replace local paths with relative paths or placeholders"))
                if "python tools/processforge.py doctor-project --project-root" in text:
                    checks.append(
                        check_with_hint(
                            "FAIL",
                            f"{rel_path}: linked-project doctor command is misleading",
                            "Normal onboarded projects do not contain tools/processforge.py.",
                            "use python .pf/runtime/bin/pf.py doctor-project --project-root . inside linked projects",
                        )
                    )
    return print_checks(checks)




@dataclass
class ReleaseCommandResult:
    label: str
    status: str
    code: int
    output: str
    started_at: str
    finished_at: str
    elapsed_seconds: float
    timeout_seconds: int
    command: list[str]
    layer: str = "public"
    public_gate: bool = True


def format_command(command: list[str]) -> str:
    return format_subprocess_command(command)


def run_release_command(label: str, command: list[str], cwd: Path, timeout: int, allow_warn: bool = False, *, layer: str = "public", public_gate: bool = True) -> ReleaseCommandResult:
    started_at = _core_common_clock.now_utc()
    started = time.perf_counter()
    print(f"RUN {label}:")
    print(f"  {format_command(command)}")
    print(f"  started_at: {started_at}")
    sys.stdout.flush()
    result = run_subprocess_command(command, cwd=cwd, timeout=timeout)
    elapsed = time.perf_counter() - started
    finished_at = _core_common_clock.now_utc()
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.timed_out:
        return ReleaseCommandResult(label, "FAIL", 124, f"timeout after {timeout}s\n{diagnostic_text(result)}", started_at, finished_at, elapsed, timeout, command, layer, public_gate)
    code = int(result.returncode or 0)
    if code == 0:
        return ReleaseCommandResult(label, "PASS", 0, output, started_at, finished_at, elapsed, timeout, command, layer, public_gate)
    if allow_warn:
        return ReleaseCommandResult(label, "WARN", code, output, started_at, finished_at, elapsed, timeout, command, layer, public_gate)
    return ReleaseCommandResult(label, "FAIL", code, output, started_at, finished_at, elapsed, timeout, command, layer, public_gate)


def print_release_command_output(result: ReleaseCommandResult) -> None:
    print(f"{result.status} {result.label}")
    print(f"  finished_at: {result.finished_at}")
    print(f"  elapsed_seconds: {result.elapsed_seconds:.2f}")
    if result.status != "PASS":
        print(f"  exit: {result.code}")
        tail_lines = result.output.splitlines()[-30:]
        for line in tail_lines:
            print(f"  {line}")




def write_release_test_report(root: Path, results: list[ReleaseCommandResult], public_checks: list[Check], *, public: bool, started_at: str, finished_at: str, elapsed_seconds: float, trace_smokes: bool = False) -> None:
    report_dir = root / ".pf" / "runtime" / "release-test"
    report_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "public": public,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "result": "FAIL" if any(item.status == "FAIL" for item in results) or any(item.level == "FAIL" for item in public_checks) else "PASS",
        "checks": [
            {
                "label": item.label,
                "status": item.status,
                "exit_code": item.code,
                "started_at": item.started_at,
                "finished_at": item.finished_at,
                "elapsed_seconds": round(item.elapsed_seconds, 3),
                "timeout_seconds": item.timeout_seconds,
                "timeout_reason": "timeout" if item.code == 124 else None,
                "command": item.command,
                "layer": item.layer,
                "public_gate": item.public_gate,
            }
            for item in results
        ],
        "public_checks": [{"level": item.level, "message": item.message} for item in public_checks],
    }
    (report_dir / "latest-report.json").write_text(ensure_trailing_newline(json.dumps(data, indent=2, sort_keys=True)), encoding="utf-8")
    lines = [
        "# Release Test Report",
        "",
        f"- result: `{data['result']}`",
        f"- public: `{str(public).lower()}`",
        f"- started_at: `{started_at}`",
        f"- finished_at: `{finished_at}`",
        f"- elapsed_seconds: `{elapsed_seconds:.2f}`",
        "",
        "## Checks",
        "",
        "| Check | Layer | Public Gate | Status | Exit | Elapsed | Timeout |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        lines.append(f"| `{item.label}` | `{item.layer}` | {str(item.public_gate).lower()} | {item.status} | {item.code} | {item.elapsed_seconds:.2f}s | {item.timeout_seconds}s |")
    if public_checks:
        lines.extend(["", "## Public Checks", ""])
        lines.extend(f"- {item.level}: {item.message}" for item in public_checks)
    (report_dir / "latest-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if trace_smokes:
        trace_lines = []
        for item in results:
            trace_lines.append(
                json.dumps(
                    {
                        "label": item.label,
                        "status": item.status,
                        "elapsed_seconds": round(item.elapsed_seconds, 3),
                        "timeout_seconds": item.timeout_seconds,
                        "timeout_reason": "timeout" if item.code == 124 else None,
                        "command": item.command,
                    },
                    sort_keys=True,
                )
            )
        (report_dir / "latest-trace.ndjson").write_text(ensure_trailing_newline("\n".join(trace_lines)), encoding="utf-8")


def positive_timeout_scale(args: argparse.Namespace) -> float | None:
    raw_timeout_scale = getattr(args, "timeout_scale", 1.0)
    timeout_scale = float(1.0 if raw_timeout_scale is None else raw_timeout_scale)
    if not math.isfinite(timeout_scale) or timeout_scale <= 0:
        print("FAIL: --timeout-scale must be a finite value greater than 0")
        return None
    return timeout_scale


def command_release_test(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    timeout_scale = positive_timeout_scale(args)
    if timeout_scale is None:
        return 1
    clean_first = not getattr(args, "no_clean", False)
    if getattr(args, "clean_first", False):
        clean_first = True
    public_requested = bool(getattr(args, "public", False))
    commands = _release_command_plan.release_test_commands(root, clean_first=clean_first, public=public_requested)
    only = set(getattr(args, "only", []) or [])
    skip = set(getattr(args, "skip", []) or [])
    if getattr(args, "list", False):
        for item in commands:
            print(f"{item.label}\tlayer={item.layer}\tpublic_gate={str(item.public_gate).lower()}")
        print("public-gate")
        print("git diff --check")
        return 0
    if only:
        known = {item.label for item in commands}
        known.update({"public-gate", "git diff --check"})
        unknown = sorted(only - known)
        if unknown:
            print("FAIL: unknown --only check(s): " + ", ".join(unknown))
            return 1
        public_group_selected = "public-gate" in only
        public_requested = public_requested or public_group_selected
        commands = [
            item
            for item in commands
            if item.label in only or (public_group_selected and item.public_gate)
        ]
        if not commands and "git diff --check" not in only:
            print("FAIL: --only selection resolved to no release commands")
            return 1
    if "public-gate" in skip:
        public_requested = False
    if skip:
        commands = [
            item
            for item in commands
            if item.label not in skip
            and not ("public-gate" in skip and item.public_gate)
        ]
    git_check_selected = (
        (root / ".git").exists()
        and (not only or "git diff --check" in only)
        and "git diff --check" not in skip
    )
    if not commands and not git_check_selected:
        print("FAIL: release-test selection resolved to no runnable checks")
        return 1
    print("ProcessForge release-test")
    started_at = _core_common_clock.now_utc()
    started = time.perf_counter()
    failed = False
    warned = False
    results: list[ReleaseCommandResult] = []
    for item in commands:
        scaled_timeout = max(1, int(item.timeout * timeout_scale))
        result = run_release_command(item.label, item.command, root, timeout=scaled_timeout, allow_warn=item.allow_warn, layer=item.layer, public_gate=item.public_gate)
        print_release_command_output(result)
        results.append(result)
        failed = failed or result.status == "FAIL"
        warned = warned or result.status == "WARN"
        if failed and getattr(args, "fail_fast", False):
            break
    if not failed or not getattr(args, "fail_fast", False):
        git_dir = root / ".git"
        if git_dir.exists() and (not only or "git diff --check" in only) and "git diff --check" not in skip:
            result = run_release_command("git diff --check", ["git", "diff", "--check"], root, timeout=max(1, int(60 * timeout_scale)))
            print_release_command_output(result)
            results.append(result)
            failed = failed or result.status == "FAIL"
            warned = warned or result.status == "WARN"
        elif not git_dir.exists():
            print("WARN git diff --check skipped: not a git repo")
            warned = True
    else:
        print("SKIP git diff --check: fail-fast")
    public_checks: list[Check] = []
    if public_requested:
        public_checks = public_release_checks(root)
        public_status = print_checks(public_checks)
        failed = failed or public_status != 0
    finished_at = _core_common_clock.now_utc()
    elapsed = time.perf_counter() - started
    write_release_test_report(root, results, public_checks, public=public_requested, started_at=started_at, finished_at=finished_at, elapsed_seconds=elapsed, trace_smokes=bool(getattr(args, "trace_smokes", False)))
    print(f"REPORT: {rel(root / '.pf' / 'runtime' / 'release-test' / 'latest-report.json', root)}")
    print(f"REPORT: {rel(root / '.pf' / 'runtime' / 'release-test' / 'latest-report.md', root)}")
    if getattr(args, "trace_smokes", False):
        print(f"TRACE: {rel(root / '.pf' / 'runtime' / 'release-test' / 'latest-trace.ndjson', root)}")
    print(f"ELAPSED: {elapsed:.2f}s")
    if failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS with warnings" if warned else "RESULT: PASS")
    return 0


def command_dev_test(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    runner = root / ".pf" / "dogfooding" / "run_dogfooding_tests.py"
    if not runner.is_file():
        print(f"FAIL: dogfooding runner missing: {rel(runner, root)}")
        return 1
    command = [sys.executable, str(runner)]
    if getattr(args, "list", False):
        command.append("--list")
    for suite in getattr(args, "suite", []) or []:
        command.extend(["--suite", suite])
    for test in getattr(args, "test", []) or []:
        command.extend(["--test", test])
    if getattr(args, "fail_fast", False):
        command.append("--fail-fast")
    timeout_scale = positive_timeout_scale(args)
    if timeout_scale is None:
        return 1
    command.extend(["--timeout-scale", str(timeout_scale)])
    result = run_subprocess_command(command, cwd=root, timeout=max(1, int(1200 * timeout_scale)))
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if result.timed_out:
        print("RESULT: FAIL")
        print(diagnostic_text(result))
        return 1
    return int(result.returncode or 0)


def command_version(args: argparse.Namespace) -> int:
    version_file = ROOT / "VERSION"
    version = version_file.read_text(encoding="utf-8", errors="replace").strip() if version_file.is_file() else PROCESSFORGE_VERSION
    print(f"ProcessForge {version}")
    print(f"Spec: {PROCESSFORGE_SPEC_VERSION}")
    print(f"Schema bundle: {PROCESSFORGE_SCHEMA_BUNDLE_VERSION}")
    return 0








def official_release_pack_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    official_root = root / "packs" / "official"
    if not official_root.is_dir():
        return entries
    for manifest in sorted(official_root.glob("*/package.yaml")):
        data = load_yaml_document(manifest)
        if not isinstance(data, dict) or data.get("origin") != "official":
            continue
        entries.append(
            {
                "id": str(data.get("id") or ""),
                "version": str(data.get("version") or ""),
                "manifest_path": rel(manifest, root),
                "manifest_sha256": sha256_file(manifest),
            }
        )
    return sorted(entries, key=lambda item: item["id"])


def release_zip_datetime(source_epoch: int) -> tuple[int, int, int, int, int, int]:
    moment = datetime.fromtimestamp(source_epoch, timezone.utc)
    return (moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second)


def release_file_content(source_path: Path) -> bytes:
    """Canonicalize text line endings so archives do not depend on checkout settings."""
    content = source_path.read_bytes()
    return content if b"\0" in content else content.replace(b"\r\n", b"\n")


def release_core_manifest(files: list[tuple[str, Path]], *, version: str, source: dict[str, Any] | None, generated_at: str | None = None) -> dict[str, Any]:
    from processforge_core.maintenance.update import CORE_MANIFEST_NAME, make_core_manifest

    entries = []
    for archive_path, source_path in files:
        if archive_path == CORE_MANIFEST_NAME:
            continue
        content = release_file_content(source_path)
        entries.append({"relative_path": archive_path, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    return make_core_manifest(version=version, source=source, files=entries, generated_at=generated_at)


def write_release_zip(output: Path, files: list[tuple[str, Path]], source_epoch: int, extra_entries: list[tuple[str, bytes]] | None = None) -> list[dict[str, Any]]:
    manifest_files: list[dict[str, Any]] = []
    zip_datetime = release_zip_datetime(source_epoch)
    entries: list[tuple[str, Path | None, bytes | None]] = [(archive_path, source_path, None) for archive_path, source_path in files]
    entries.extend((archive_path, None, content) for archive_path, content in extra_entries or [])
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for archive_path, source_path, generated_content in sorted(entries, key=lambda item: item[0]):
            content = release_file_content(source_path) if source_path is not None else generated_content
            if content is None:
                raise SystemExit(f"FAIL: release-pack entry has no content: {archive_path}")
            info = zipfile.ZipInfo(archive_path, date_time=zip_datetime)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            manifest_files.append(
                {
                    "path": archive_path,
                    "size": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    return manifest_files


def release_manifest_payload(
    root: Path,
    output: Path,
    manifest_files: list[dict[str, Any]],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": _core_common_release_identity.RELEASE_NAME,
        "version": _core_common_release_identity.RELEASE_ARCHIVE_VERSION,
        "schema_bundle_version": PROCESSFORGE_SCHEMA_BUNDLE_VERSION,
        "release_eligible": True,
        "build": {
            "source_date_epoch": provenance["source_date_epoch"],
            "generated_at": provenance["generated_at"],
            "deterministic": True,
        },
        "source": provenance["source"],
        "archive": {
            "filename": output.name,
            "format": "zip",
            "size": output.stat().st_size,
            "sha256": sha256_file(output),
            "entry_count": len(manifest_files),
        },
        "official_packs": official_release_pack_entries(root),
        "files": manifest_files,
    }


def command_release_pack(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = (root / output).resolve()
    manifest_path = output.with_suffix(".manifest.json")
    checks = release_checks(root)
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        for item in failures:
            print(f"FAIL: {item.message}")
        return 1
    for label, script in [
        ("public cleanliness", root / "tools" / "validate-public-cleanliness.py"),
        ("checksum inventory", root / "tools" / "validate-process-forge-checksums.py"),
    ]:
        command = [sys.executable, str(script), "--root", str(root)]
        if label == "checksum inventory":
            command.append("--check")
        result = subprocess.run(command, cwd=root, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
        if result.returncode != 0:
            print(f"FAIL: release-pack preflight {label}")
            print((result.stdout or result.stderr).strip())
            return 1
    patterns = _release_source_policy.release_ignore_patterns(root)
    files = [(archive_path, path) for archive_path, path in _release_source_policy.release_source_files(root) if not _release_source_policy.release_ignore_match(archive_path, patterns) and not _release_source_policy.release_path_is_forbidden(archive_path)]
    if args.dry_run:
        print(f"DRY-RUN: would write {output}")
        print(f"DRY-RUN: would write {manifest_path}")
        print(f"FILES: {len(files) + 1}")
        print("INCLUDE: processforge-core.manifest.json [generated]")
        for archive_path, _path in files[:50]:
            print(f"INCLUDE: {archive_path}")
        if len(files) > 50:
            print(f"... {len(files) - 50} more files")
        return 0
    provenance = _release_git_provenance.release_git_provenance(root)
    from processforge_core.maintenance.update import CORE_MANIFEST_NAME, manifest_bytes

    core_manifest = release_core_manifest(files, version=_core_common_release_identity.RELEASE_ARCHIVE_VERSION, source=provenance["source"], generated_at=provenance["generated_at"])
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_files = write_release_zip(output, files, int(provenance["source_date_epoch"]), extra_entries=[(CORE_MANIFEST_NAME, manifest_bytes(core_manifest))])
    manifest = release_manifest_payload(root, output, manifest_files, provenance)
    manifest_path.write_text(ensure_trailing_newline(json.dumps(manifest, indent=2, sort_keys=True)), encoding="utf-8")
    consumer_checks = inspect_release_archive(output, manifest_path)
    consumer_failures = [item for item in consumer_checks if item.level == "FAIL"]
    if consumer_failures:
        for item in consumer_failures:
            print(f"FAIL: {item.message}")
        return 1
    print(f"WROTE: {rel(output, root)}")
    print(f"WROTE: {rel(manifest_path, root)}")
    print(f"FILES: {len(manifest_files)}")
    return 0


def archive_manifest_path(archive_path: Path) -> Path:
    return archive_path.with_suffix(".manifest.json")






def inspect_release_archive(archive_path: Path, manifest_path: Path | None = None) -> list[Check]:
    checks: list[Check] = []
    checks.append(check("PASS" if archive_path.is_file() else "FAIL", f"archive exists: {archive_path}"))
    if not archive_path.is_file():
        return checks
    manifest = manifest_path or archive_manifest_path(archive_path)
    checks.append(check("PASS" if manifest.is_file() else "FAIL", f"manifest exists: {manifest}"))
    with zipfile.ZipFile(archive_path) as archive:
        infos = [info for info in archive.infolist() if not info.filename.endswith("/")]
        names = sorted(info.filename for info in infos)
        forbidden = [name for name in names if _release_source_policy.release_path_is_forbidden(name) or name.startswith(".serena/") or name.startswith(".idea/") or name.startswith(".vscode/")]
        checks.append(check("PASS" if not forbidden else "FAIL", f"archive forbidden entries: {len(forbidden)}"))
        for name in forbidden[:20]:
            checks.append(check("FAIL", f"forbidden archive entry: {name}"))
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            checks.extend(_release_manifest_policy.validate_release_manifest_contract(data, archive_path, infos))
            manifest_files = data.get("files") if isinstance(data, dict) else None
            manifest_names = sorted(str(item.get("path")) for item in manifest_files if isinstance(item, dict) and item.get("path")) if isinstance(manifest_files, list) else []
            checks.append(check("PASS" if manifest_names == names else "FAIL", "manifest file list matches zip entries"))
            if manifest_names == names:
                checks.append(check("PASS", f"manifest files: {len(manifest_names)}"))
            else:
                missing = sorted(set(names) - set(manifest_names))
                extra = sorted(set(manifest_names) - set(names))
                for name in missing[:10]:
                    checks.append(check("FAIL", f"zip entry missing from manifest: {name}"))
                for name in extra[:10]:
                    checks.append(check("FAIL", f"manifest entry missing from zip: {name}"))
    return checks


def expected_release_files_from_root(root: Path) -> list[tuple[str, Path]]:
    patterns = _release_source_policy.release_ignore_patterns(root)
    expected: list[tuple[str, Path]] = []
    for archive_path, source_path in _release_source_policy.release_source_files(root):
        if _release_source_policy.release_ignore_match(archive_path, patterns):
            continue
        if _release_source_policy.release_path_is_forbidden(archive_path):
            continue
        expected.append((archive_path, source_path))
    return expected


def expected_release_manifest_from_root(root: Path, manifest_data: dict[str, Any] | None = None) -> dict[str, str]:
    expected_files = expected_release_files_from_root(root)
    expected = {archive_path: hashlib.sha256(release_file_content(source_path)).hexdigest() for archive_path, source_path in expected_files}
    if manifest_data:
        from processforge_core.maintenance.update import CORE_MANIFEST_NAME, manifest_bytes

        build = manifest_data.get("build") if isinstance(manifest_data.get("build"), dict) else {}
        source = manifest_data.get("source") if isinstance(manifest_data.get("source"), dict) else None
        core_manifest = release_core_manifest(
            expected_files,
            version=str(manifest_data.get("version") or _core_common_release_identity.RELEASE_ARCHIVE_VERSION),
            source=source,
            generated_at=str(build.get("generated_at") or ""),
        )
        expected[CORE_MANIFEST_NAME] = hashlib.sha256(manifest_bytes(core_manifest)).hexdigest()
    return expected


def archive_manifest_freshness_checks(root: Path, archive_path: Path, manifest_path: Path) -> list[Check]:
    checks: list[Check] = []
    manifest_data: dict[str, Any] | None = None
    if manifest_path.is_file():
        loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_data = loaded_manifest if isinstance(loaded_manifest, dict) else None
    expected = expected_release_manifest_from_root(root, manifest_data)
    if not archive_path.is_file():
        return [check("FAIL", f"archive exists for root freshness check: {archive_path}")]
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = sorted(name for name in archive.namelist() if not name.endswith("/"))
        archive_hashes = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive_names}
    if sorted(expected) != archive_names:
        checks.append(check("FAIL", "archive entries match current root release file set"))
        for name in sorted(set(expected) - set(archive_names))[:20]:
            checks.append(check("FAIL", f"current root file missing from archive: {name}"))
        for name in sorted(set(archive_names) - set(expected))[:20]:
            checks.append(check("FAIL", f"archive entry not present in current root release set: {name}"))
    else:
        checks.append(check("PASS", f"archive entries match current root release file set: {len(expected)}"))
    stale_hashes = [name for name, sha in expected.items() if archive_hashes.get(name) != sha]
    if stale_hashes:
        checks.append(check("FAIL", "archive file hashes match current root"))
        for name in stale_hashes[:20]:
            checks.append(check("FAIL", f"stale archive entry hash: {name}"))
    else:
        checks.append(check("PASS", "archive file hashes match current root"))
    if manifest_data:
        manifest_files = manifest_data.get("files")
        manifest_hashes = {str(item.get("path")): str(item.get("sha256")) for item in manifest_files if isinstance(item, dict) and item.get("path")} if isinstance(manifest_files, list) else {}
        checks.append(check("PASS" if manifest_hashes == expected else "FAIL", "manifest hashes match current root release file set"))
    return checks


def command_release_archive_test(args: argparse.Namespace) -> int:
    archive_path = Path(args.archive).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else archive_manifest_path(archive_path)
    checks = inspect_release_archive(archive_path, manifest_path)
    if getattr(args, "root", None):
        root = Path(args.root).expanduser().resolve()
        checks.extend(archive_manifest_freshness_checks(root, archive_path, manifest_path))
    if print_checks(checks) != 0:
        return 1
    extracted_test = str(getattr(args, "extracted_test", "full") or "full")
    if extracted_test == "skip":
        print("SKIP: extracted archive release-test")
        print("RESULT: PASS")
        return 0
    timeout_scale = positive_timeout_scale(args)
    if timeout_scale is None:
        return 1
    with tempfile.TemporaryDirectory(prefix="processforge-release-archive-") as temp:
        extract_root = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_root)
        cli = extract_root / "tools" / "processforge.py"
        if not cli.is_file():
            print(f"FAIL: extracted archive has no CLI: {cli}")
            return 1
        for label, target in [("bin/pf.py --help", extract_root / "bin" / "pf.py"), ("tools/processforge.py --help", cli)]:
            result = run_release_command(label, [sys.executable, str(target), "--help"], extract_root, timeout=30)
            print_release_command_output(result)
            if result.status != "PASS":
                print("RESULT: FAIL")
                return 1
        command = [sys.executable, str(cli), "release-test", "--root", str(extract_root)]
        if extracted_test == "quick":
            command.extend([
                "--only", "py_compile",
                "--only", "schema validation",
                "--only", "public cleanliness",
                "--only", "checksum",
                "--only", "smoke_processforge_core_package_bootstrap",
                "--only", "smoke_central_event_ingress",
                "--only", "smoke_conversation_completeness",
                "--only", "smoke_central_event_replay",
            ])
        else:
            command.append("--public")
        command.extend(["--timeout-scale", str(timeout_scale)])
        result = run_release_command(
            "release-test extracted archive",
            command,
            extract_root,
            timeout=max(1, int(1200 * timeout_scale)),
        )
        print_release_command_output(result)
        if result.status != "PASS":
            print("RESULT: FAIL")
            return 1
    print("RESULT: PASS")
    return 0


def find_local_workplace_manifest(local_text: str) -> Path | None:
    return _local_workplace_manifest_reference(local_text)






def distribution_registry_entries(workplace_manifest: Path) -> list[dict[str, Any]]:
    registry = _workplace_registry_reader.resolve_registry_path(workplace_manifest, "distributions", "distributions.yaml")
    data = load_yaml_document(registry)
    entries = data.get("distributions") if isinstance(data, dict) else None
    return [item for item in entries if isinstance(item, dict)] if isinstance(entries, list) else []


def resolve_distribution_path(workplace_manifest: Path, distribution_id: str = "processforge") -> Path | None:
    for entry in distribution_registry_entries(workplace_manifest):
        if str(entry.get("id")) != distribution_id:
            continue
        raw_path = entry.get("path")
        if not raw_path:
            return None
        return _workplace_registry_reader.resolve_registry_relative_path(workplace_manifest.parent, str(raw_path), workplace_manifest)
    return None


def distribution_checks(distribution_root: Path | None) -> list[Check]:
    checks: list[Check] = []
    if not distribution_root:
        return [check("FAIL", "processforge distribution path is not configured")]
    checks.append(check("PASS" if distribution_root.is_dir() else "FAIL", "processforge distribution exists"))
    for dirname in ["tools", "schemas", "processes", "packages", "templates"]:
        path = distribution_root / dirname
        checks.append(check("PASS" if path.is_dir() else "FAIL", f"processforge distribution has {dirname}/"))
    return checks








def active_capability_waivers(project_root: Path) -> dict[str, list[dict[str, Any]]]:
    flow_root = locate_flow_root(project_root)
    paths = [
        flow_root / "capability-waivers.yaml",
        flow_root / "artifacts" / "capability-waivers.yaml",
    ]
    active: dict[str, list[dict[str, Any]]] = {}
    now = datetime.now(timezone.utc)
    for path in paths:
        if not path.is_file():
            continue
        data = load_yaml_document(path)
        if not isinstance(data, dict) or yaml_error(data):
            continue
        records = data.get("capability_waivers")
        if not isinstance(records, list):
            records = data.get("waivers")
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            capability = str(record.get("capability") or "").strip()
            if not capability:
                continue
            status = str(record.get("status") or "active")
            if status not in {"active", "waived", "verified"}:
                continue
            expires_at = parse_snapshot_timestamp(record.get("expires_at"))
            if expires_at is not None and expires_at < now:
                continue
            active.setdefault(capability, []).append({**record, "path": rel(path, project_root)})
    return active




def public_snapshot_path_checks(project_root: Path) -> list[Check]:
    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    checks: list[Check] = []
    for path in [snapshot_yaml, snapshot_md]:
        if not path.is_file():
            checks.append(check("WARN", f"{rel(path, project_root)} missing"))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checks.append(
            check(
                "PASS" if is_public_path_safe(text) else "FAIL",
                f"{rel(path, project_root)} contains no local absolute paths",
            )
        )
    return checks




def sha256_file(path: Path) -> str:
    return _file_digests.sha256_file(path)


def resolve_flow_reference(project_root: Path, value: str) -> Path:
    return _ProjectMetadataReader(project_root).resolve_reference(value)


def manifest_path_refs(project_root: Path, key: str) -> list[Path]:
    return _ProjectMetadataReader(project_root).manifest_path_refs(key)








def resolve_capabilities(texts: dict[str, str], project_root: Path) -> dict[str, Any]:
    required: list[str] = []
    optional: list[str] = []
    for text in texts.values():
        required.extend(_ProjectContextRules().list_values(text, "required_capabilities"))
        optional.extend(_ProjectContextRules().list_values(text, "optional_capabilities"))
    required = sorted(set(item for item in required if item))
    optional = sorted(set(item for item in optional if item))
    registry_providers = _CapabilityRegistryReader(project_root).read()
    available = set(registry_providers)
    missing_required = [item for item in required if item not in available]
    missing_optional = [item for item in optional if item not in available]
    return {
        "required": required,
        "optional": optional,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "providers": registry_providers,
    }


_yaml_documents = YamlDocumentReader(fallback=_core_common_yaml_io._parse_simple_yaml)


def load_yaml_document(path: Path) -> dict[str, Any]:
    return _yaml_documents.load(path)


def yaml_error(data: Any) -> str | None:
    if isinstance(data, dict) and isinstance(data.get("__yaml_error__"), str):
        return str(data["__yaml_error__"])
    return None








def fingerprint_record(path: Path, project_root: Path, source_id: str, kind: str, *, private: bool = False, display_path: str | None = None) -> dict[str, Any]:
    return _ProjectSnapshotSourcesReader(project_root).fingerprint(path, source_id, kind, private=private, display_path=display_path)


def collect_project_snapshot_sources(project_root: Path) -> list[dict[str, Any]]:
    return _ProjectSnapshotSourcesReader(project_root, distribution_root=ROOT).read()
































def resource_record_from_package(package_id: str, resource: dict[str, Any], requirement: str, package_root_id: str | None = None) -> dict[str, Any]:
    from processforge_core.resources.catalog_read import resource_record_from_package as project_resource

    return project_resource(package_id, resource, requirement, package_root_id)


def resolve_package_resources(
    project_root: Path,
    distribution_root: Path | None,
    workplace_manifest: Path | None,
    package_ids: list[str],
    required_package_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    from processforge_core.resources.catalog_read import resource_record_from_package as project_resource

    package_index = _project_package_catalog_reader.index(project_root, distribution_root, workplace_manifest)
    resources: list[dict[str, Any]] = []
    required_set = set(required_package_ids or [])
    for package_id in package_ids:
        manifest = package_index.get(package_id)
        if not manifest:
            continue
        requirement = "required" if package_id in required_set else "recommended"
        package_resources = manifest.get("resources")
        if not isinstance(package_resources, list):
            continue
        for resource in package_resources:
            if isinstance(resource, dict):
                resources.append(project_resource(package_id, resource, requirement, manifest.get("__package_root_id")))
    return resources


SNAPSHOT_FRESHNESS_STATUSES = {"fresh", "fresh_with_updates", "stale", "broken"}














def resolve_project_parameters(
    project_root: Path,
    workplace_manifest: Path | None,
    manifest_data: dict[str, Any],
    platform_resolution: dict[str, Any],
    specialization_ids: list[str],
    platform_ids: list[str],
    process_id: str | None,
    process_paths: list[Path],
) -> dict[str, Any]:
    flow_root = locate_flow_root(project_root)
    result: dict[str, Any] = {
        "status": "resolved",
        "resolved_parameters": {},
        "sources": [],
        "provenance": {},
        "conflicts": [],
    }
    if workplace_manifest and workplace_manifest.is_file():
        workplace_data = load_yaml_document(workplace_manifest)
        _parameter_source_service.add(
            result,
            source_id="workplace-manifest",
            layer="workplace",
            parameters=parameter_payload(workplace_data),
            path=workplace_manifest,
            project_root=project_root,
            private=True,
            display_path="<private-workplace-manifest-ref>",
        )
        for index, path in enumerate(_parameter_source_service.workplace_paths(workplace_manifest)):
            data = load_yaml_document(path)
            _parameter_source_service.add(
                result,
                source_id=f"workplace-parameters-{index + 1}",
                layer="workplace",
                parameters=parameter_payload(data),
                path=path,
                project_root=project_root,
                private=True,
                display_path=f"<private-workplace-ref>/{path.relative_to(workplace_manifest.parent).as_posix()}" if path_is_relative_to(path, workplace_manifest.parent) else "<private-workplace-parameters-ref>",
            )
    for contract in platform_resolution.get("contracts", []) if isinstance(platform_resolution.get("contracts"), list) else []:
        if isinstance(contract, dict):
            _parameter_source_service.add(
                result,
                source_id=f"platform:{contract.get('id', 'unknown')}",
                layer="platform",
                parameters=parameter_payload(contract),
            )
    index = _specialization_catalog_reader.manifest_index(workplace_manifest, project_root)
    for specialization_id in [_specialization_catalog_reader.resource_id(item) for item in specialization_ids if str(item)]:
        spec = index.get(specialization_id)
        if not isinstance(spec, dict):
            continue
        for override_entry in _project_override_reader.project_specialization_override_entries(project_root, specialization_id):
            mode = str(override_entry.get("mode") or "extension")
            if mode not in PROJECT_OVERRIDE_MODES:
                result["conflicts"].append({"id": specialization_id, "kind": "specialization", "reason": f"unsupported project override mode: {mode}"})
                continue
            overlay = _project_override_reader.load_project_override_document(project_root, override_entry)
            if overlay:
                spec, _overlay_notes = _project_override_reader.apply_specialization_overlay(spec, overlay, mode)
        _parameter_source_service.add(
            result,
            source_id=f"specialization:{specialization_id}",
            layer="specialization",
            parameters=parameter_payload(spec),
            path=spec.get("__manifest_path") if isinstance(spec.get("__manifest_path"), Path) else None,
            project_root=project_root,
            private=str(spec.get("__source") or "") == "workplace",
        )
        for binding_index, binding in enumerate(spec.get("platform_bindings", []) if isinstance(spec.get("platform_bindings"), list) else []):
            if isinstance(binding, dict) and _project_platform_selection_service.binding_matches(binding, platform_ids, platform_resolution.get("platform_stack", []), process_id):
                _parameter_source_service.add(
                    result,
                    source_id=f"specialization:{specialization_id}:binding:{binding_index + 1}",
                    layer="specialization",
                    parameters=parameter_payload(binding),
                )
    _parameter_source_service.add(result, source_id="project-manifest", layer="project", parameters=parameter_payload(manifest_data), path=flow_root / "process-forge.yaml", project_root=project_root)
    project_parameters = flow_root / "parameters.yaml"
    _parameter_source_service.add(result, source_id="project-parameters", layer="project", parameters=parameter_payload(load_yaml_document(project_parameters)), path=project_parameters, project_root=project_root)
    local_config = flow_root / "process-forge.local.yaml"
    local_data = load_yaml_document(local_config)
    local_overrides = local_data.get("overrides") if isinstance(local_data.get("overrides"), dict) else {}
    _parameter_source_service.add(result, source_id="project-local-overrides", layer="project", parameters=parameter_payload(local_overrides), path=local_config, project_root=project_root, private=True)
    project_local_parameters = flow_root / "parameters.local.yaml"
    _parameter_source_service.add(result, source_id="project-local-parameters", layer="project", parameters=parameter_payload(load_yaml_document(project_local_parameters)), path=project_local_parameters, project_root=project_root, private=True)
    for index, path in enumerate(process_paths):
        parameters, _stage_parameters = _parameter_source_service.process_parameters(path)
        _parameter_source_service.add(result, source_id=f"process:{path.stem}:{index + 1}", layer="process", parameters=parameters, path=path, project_root=project_root)
    if result["conflicts"]:
        result["status"] = "conflict"
    return result


def resolve_assignment_parameters(project_root: Path, snapshot: dict[str, Any], assignment_metadata: dict[str, Any]) -> dict[str, Any]:
    base = snapshot.get("resolved_parameters") if isinstance(snapshot.get("resolved_parameters"), dict) else {}
    snapshot_resolution = snapshot.get("parameter_resolution") if isinstance(snapshot.get("parameter_resolution"), dict) else {}
    result: dict[str, Any] = {
        "status": "resolved",
        "resolved_parameters": copy.deepcopy(base),
        "sources": copy.deepcopy(snapshot_resolution.get("sources", [])) if isinstance(snapshot_resolution.get("sources"), list) else [],
        "provenance": copy.deepcopy(snapshot_resolution.get("provenance", {})) if isinstance(snapshot_resolution.get("provenance"), dict) else {},
        "conflicts": copy.deepcopy(snapshot_resolution.get("conflicts", [])) if isinstance(snapshot_resolution.get("conflicts"), list) else [],
    }
    process_ref = assignment_metadata.get("process")
    process_id = str(process_ref.get("id") if isinstance(process_ref, dict) else process_ref or "")
    stage_id = str(assignment_metadata.get("stage") or "")
    if process_id:
        try:
            process_path = resolve_process_definition(project_root, process_id).path
            process_parameters, stage_parameters = _parameter_source_service.process_parameters(process_path)
            _parameter_source_service.add(result, source_id=f"assignment-process:{process_id}", layer="process", parameters=process_parameters, path=process_path, project_root=project_root)
            if stage_id and stage_id in stage_parameters:
                _parameter_source_service.add(result, source_id=f"assignment-stage:{process_id}:{stage_id}", layer="stage", parameters=stage_parameters[stage_id], path=process_path, project_root=project_root)
        except SystemExit:
            result["conflicts"].append({"id": process_id, "kind": "process", "reason": "assignment process parameters could not be loaded"})
    _parameter_source_service.add(result, source_id="assignment", layer="task", parameters=parameter_payload(assignment_metadata))
    if result["conflicts"]:
        result["status"] = "conflict"
    return result




































def resource_management_root(workplace_root: Path) -> Path:
    return workplace_root / "runtime" / "resource-management"


def resource_management_slug(command: str, object_id: str) -> str:
    stamp = _core_common_clock.now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    return f"{stamp}-{safe_id(command, 'command')}-{safe_id(object_id, 'resource')}"


def write_resource_management_artifact(workplace_root: Path, kind: str, slug: str, content: str) -> Path:
    target = resource_management_root(workplace_root) / kind / f"{slug}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(content), encoding="utf-8")
    return target


def write_resource_management_report(workplace_root: Path, slug: str, title: str, lines: list[str]) -> Path:
    target = resource_management_root(workplace_root) / "reports" / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = ["# " + title, "", *lines, ""]
    target.write_text("\n".join(body), encoding="utf-8")
    return target














def ensure_private_resource_path(workplace_root: Path, resource_id: str, raw_path: str) -> Path:
    target = workplace_root / "registries" / "private-resource-paths.yaml"
    entry = {
        "id": resource_id,
        "label": resource_id.replace("-", " ").title(),
        "path": raw_path,
        "visibility": "private",
        "status": "available",
    }
    _workplace_registry_writer.upsert(target, "private_resource_paths", entry)
    return target






def resource_id_from_url(url: str, fallback: str = "resource") -> str:
    parsed = urlparse(url)
    pieces = [parsed.netloc, parsed.path.strip("/").split("/")[-1]]
    return safe_id("-".join(piece for piece in pieces if piece), fallback)




def package_manifest_path_for_write(workplace_root: Path, package_id: str, package_root_id: str | None = None) -> tuple[PackageRootResolution, Path]:
    existing = _project_package_catalog_reader.find_manifests(workplace_root, package_id)
    if package_root_id:
        root, default_path = _project_package_catalog_reader.resolve_path(workplace_root, package_id, package_root_id, mode="write")
        for existing_root, existing_path in existing:
            if existing_root.root_id == root.root_id:
                return existing_root, existing_path
        return root, default_path
    if len(existing) > 1:
        roots = ", ".join(f"{root.root_id}:{path.as_posix()}" for root, path in existing)
        raise SystemExit(f"FAIL: duplicate package id '{package_id}' found across package roots: {roots}; pass --package-root")
    if len(existing) == 1:
        root, path = existing[0]
        if not root.resolved_path.is_dir() and not root.fallback:
            raise SystemExit(f"FAIL: package root '{root.root_id}' path does not exist: {root.resolved_path.as_posix()}")
        return root, path
    root, default_path = _project_package_catalog_reader.resolve_path(workplace_root, package_id, None, mode="write")
    if root.fallback:
        root.resolved_path.mkdir(parents=True, exist_ok=True)
    return root, default_path






def build_resource_index(package_manifest: dict[str, Any], workplace_root: Path | None = None, package_root_id: str | None = None) -> dict[str, Any]:
    package_id = str(package_manifest.get("id", "package"))
    resources = [
        _resource_record_service.normalize(resource, package_id, workplace_root)
        for resource in package_manifest.get("resources", [])
        if isinstance(resource, dict)
    ]
    return {
        "schema_version": 1,
        "package": {
            "id": package_id,
            "version": str(package_manifest.get("version", "1.0.0")),
            "package_root": package_root_id or str(package_manifest.get("package_root", "")) or None,
        },
        "generated_at": _core_common_clock.now_utc(),
        "load_policy": {
            "default": "on_demand",
            "heavy_resources": "index_only_until_requested",
            "do_not_load_full_content": True,
        },
        "resources": resources,
    }




def write_package_manifest_and_index(workplace_root: Path, package_id: str, package_manifest: dict[str, Any], package_root_id: str | None = None) -> tuple[Path, Path, PackageRootResolution]:
    package_root, manifest_path = package_manifest_path_for_write(workplace_root, package_id, package_root_id)
    package_manifest["package_root"] = package_root.root_id
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(ensure_trailing_newline(dump_yaml(package_manifest)), encoding="utf-8")
    index_path = _knowledge_resource_index_service.index_path(manifest_path, workplace_root, package_id)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(ensure_trailing_newline(dump_yaml(build_resource_index(package_manifest, workplace_root, package_root.root_id))), encoding="utf-8")
    return manifest_path, index_path, package_root






def workspace_registry_specs() -> dict[str, tuple[str, str, str]]:
    return {
        "knowledge_roots": ("knowledge_roots", "knowledge-roots.yaml", "knowledge_roots"),
        "template_roots": ("template_roots", "templates.yaml", "template_roots"),
        "templates": ("templates", "templates.yaml", "templates"),
        "package_roots": ("package_roots", "package-roots.yaml", "package_roots"),
        "tools": ("tools", "tools.yaml", "tools"),
        "mcp": ("mcp", "mcp.yaml", "mcp_servers"),
        "private_resource_paths": ("private_resource_paths", "private-resource-paths.yaml", "private_resource_paths"),
    }


def workplace_registry_entry(workplace_manifest: Path | None, registry: str, ref_id: str) -> dict[str, Any] | None:
    spec = workspace_registry_specs().get(registry)
    if not spec or not workplace_manifest:
        return None
    registry_key, default_name, collection_key = spec
    data = _workplace_registry_reader.load_workplace_registry(workplace_manifest, registry_key, default_name)
    entries = data.get(collection_key) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("id") or "") == ref_id:
            return entry
    return None


def resolve_workspace_path_ref(project_root: Path, path_ref: dict[str, Any], *, workplace_manifest: Path | None = None) -> dict[str, Any]:
    from processforge_core.resources.snapshot import WorkspacePathReferenceReader

    manifest = _workplace_registry_reader.normalize_workplace_manifest(workplace_manifest or _ProjectMetadataReader(project_root).workplace_manifest())
    return WorkspacePathReferenceReader(
        project_root, manifest.parent if manifest else None, workplace_manifest=manifest,
    ).resolve(path_ref)




def workspace_access_runtime_document(project_root: Path, task: dict[str, Any]) -> dict[str, Any]:
    from processforge_core.prepared.resources import authorize_resources
    from processforge_core.work.context import validate_execution_contract
    task_id = safe_id(str(task.get("id") or "task"), "task")
    capsule = load_yaml_document(assignment_capsule_path(project_root, task_id))
    validation = validate_execution_contract(project_root, _work_paths.assignment_document(project_root, task_id), task,
                                             capsule, sys.modules[__name__], require_ready=True)
    if validation["status"] != "valid":
        raise SystemExit("FAIL: " + str(validation.get("reason") or "execution_contract_invalid"))
    try:
        return authorize_resources(project_root, task, capsule, sys.modules[__name__])
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit("FAIL: worker resource preparation blocked: " + str(exc)) from exc


def write_workspace_access_runtime_file(project_root: Path, task: dict[str, Any]) -> Path:
    from processforge_core.prepared.input import private_file
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    task_id = safe_id(str(task.get("id") or "task"), "task")
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    private_file(project_root, rel(paths["workspace_access"], project_root))
    document = workspace_access_runtime_document(project_root, task)
    _core_common_json_io.json_write(paths["workspace_access"], document)
    return paths["workspace_access"]






def project_context_snapshot_paths(project_root: Path) -> tuple[Path, Path]:
    return _context_contract_inputs.project_context_snapshot_paths(project_root)


def project_context_snapshot_generations_dir(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "contexts" / "project-context.snapshots"


def project_context_stale_marker_path(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "runtime" / "context" / "project-context.stale.json"


def project_context_report_path(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "artifacts" / "project-context-refresh-report.md"








def project_context_check_result(project_root: Path, *, explicit_workplace: str | None = None) -> dict[str, Any]:
    with diagnostics.span("context.check", component="context"):
        result = _project_context_check_result(project_root, explicit_workplace=explicit_workplace)
    result["temporary_files"] = project_temporary_files_summary(project_root, explicit_workplace=explicit_workplace)
    diagnostics.annotate(snapshot_id=result.get("snapshot_id"))
    diagnostics.emit("info" if result.get("fresh") else "warning", "context.freshness", lambda: {
        key: result.get(key) for key in ("snapshot_id", "status", "policy_action", "recommended_action", "reasons", "stale_resources", "broken_refs")
    }, component="context")
    return result


def project_temporary_files_summary(project_root: Path, *, explicit_workplace: str | None = None) -> dict[str, Any]:
    from processforge_core.configuration import ConfigurationError
    from processforge_core.maintenance.temporary_files import last_summary

    try:
        workplace = Path(explicit_workplace).expanduser().resolve() if explicit_workplace else None
        resolved = _core_project_configuration_inputs.project_configuration_reader.project_configuration(project_root, workplace)
        if resolved.errors:
            return {"status": "unknown", "notification": False, "reason": "configuration_invalid"}
        return last_summary(project_root, resolved.config.runtime.temporary_files)
    except (ConfigurationError, OSError, RuntimeError, ValueError):
        return {"status": "unknown", "notification": False, "reason": "configuration_unavailable"}


def _project_context_check_result(project_root: Path, *, explicit_workplace: str | None = None) -> dict[str, Any]:
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    if not snapshot_yaml.is_file():
        return {
            "snapshot_id": None,
            "status": "broken",
            "fresh": False,
            "stale": False,
            "broken": True,
            "updates_available": [],
            "stale_resources": [],
            "broken_refs": [{"reason": "project context snapshot missing"}],
            "recommended_action": "project-context-refresh",
            "policy_action": "block",
        }
    snapshot = load_yaml_document(snapshot_yaml)
    reasons: list[str] = []
    stale_resources: list[dict[str, Any]] = []
    updates_available: list[dict[str, Any]] = []
    broken_refs: list[dict[str, Any]] = []
    for key in ["schema_version", "snapshot", "project", "flow", "sources", "capabilities", "session"]:
        if key not in snapshot:
            broken_refs.append({"reason": f"snapshot schema invalid: missing {key}"})
    meta = snapshot.get("snapshot", {}) if isinstance(snapshot.get("snapshot"), dict) else {}
    snapshot_id = str(meta.get("id") or snapshot.get("id") or "project-context")
    valid_until = parse_snapshot_timestamp(meta.get("valid_until"))
    if valid_until is None:
        reasons.append("valid_until missing or invalid")
    elif valid_until < datetime.now(timezone.utc):
        reasons.append("valid_until expired")
    marker_path = project_context_stale_marker_path(project_root)
    if marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            marker = {"reason": "stale marker invalid"}
        stale_resources.append({"id": marker.get("subject") or "project-context", "reason": marker.get("reason") or "snapshot stale marker exists"})
    reasons.extend(ProjectSnapshotSourceCheckService(project_root, distribution_root=ROOT).compare(snapshot))

    current = build_project_context_snapshot(project_root, explicit_workplace=explicit_workplace)
    execution_readiness = current.get("execution_readiness") if isinstance(current.get("execution_readiness"), dict) else {}
    resource_readiness = current.get("resource_readiness") if isinstance(current.get("resource_readiness"), dict) else {}
    readiness = current.get("readiness") if isinstance(current.get("readiness"), dict) else {}
    health = current.get("snapshot", {}).get("health") if isinstance(current.get("snapshot"), dict) and isinstance(current.get("snapshot", {}).get("health"), dict) else {}
    if str(resource_readiness.get("status") or "") == "blocked":
        for item in resource_readiness.get("blockers", []) if isinstance(resource_readiness.get("blockers"), list) else []:
            if isinstance(item, dict):
                broken_refs.append(
                    {
                        "id": item.get("id") or item.get("target") or "resource_readiness",
                        "reason": item.get("reason") or item.get("type") or "resource readiness blocked",
                        "type": item.get("type") or "resource_readiness_blocked",
                    }
                )
    comparison_reasons, comparison_stale, comparison_updates, comparison_broken = _project_snapshot_resolved_comparison.compare(snapshot, current)
    reasons.extend(comparison_reasons)
    stale_resources.extend(comparison_stale)
    updates_available.extend(comparison_updates)
    broken_refs.extend(comparison_broken)
    if broken_refs:
        status = "broken"
    elif stale_resources or reasons:
        status = "stale"
    elif updates_available:
        status = "fresh_with_updates"
    else:
        status = "fresh"
    policy = snapshot.get("context_policy") if isinstance(snapshot.get("context_policy"), dict) else _ProjectContextPolicy().build({})
    policy_action = _ProjectContextPolicy().action(status, policy)
    return {
        "snapshot_id": snapshot_id,
        "snapshot_sha256": "sha256:" + sha256_file(snapshot_yaml),
        "status": status,
        "fresh": status in {"fresh", "fresh_with_updates"},
        "stale": status == "stale",
        "broken": status == "broken",
        "updates_available": updates_available,
        "stale_resources": stale_resources + [{"reason": reason} for reason in reasons],
        "broken_refs": broken_refs,
        "recommended_action": "project-context-refresh" if status in {"stale", "broken"} else "continue",
        "policy_action": policy_action,
        "policy": {"action": policy_action},
        "health": health,
        "readiness": readiness,
        "resource_readiness": resource_readiness,
        "execution_readiness": execution_readiness,
    }


def build_project_context_snapshot(project_root: Path, *, max_age_days: int = 7, explicit_workplace: str | None = None) -> dict[str, Any]:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    if not manifest.is_file():
        raise SystemExit(f"FAIL: process-forge manifest not found: {rel(manifest, project_root)}")
    manifest_data = load_yaml_document(manifest)
    manifest_text = manifest.read_text(encoding="utf-8", errors="replace")
    sources = _ProjectSnapshotSourcesReader(project_root, distribution_root=ROOT).read()
    required = sorted(
        set(_ProjectContextRules().list_values(manifest_text, "required_capabilities")).union(
            str(item)
            for item in as_list(manifest_data.get("required_capabilities"))
            if str(item)
        )
    )
    optional = sorted(
        set(_ProjectContextRules().list_values(manifest_text, "optional_capabilities")).union(
            str(item)
            for item in as_list(manifest_data.get("optional_capabilities"))
            if str(item)
        )
    )
    generated_at = _core_common_clock.now_utc()
    valid_until = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=max_age_days)).isoformat().replace("+00:00", "Z")
    project = manifest_data.get("project", {}) if isinstance(manifest_data.get("project"), dict) else {}
    process_forge_data = manifest_data.get("process_forge", {}) if isinstance(manifest_data.get("process_forge"), dict) else {}
    detected_data = manifest_data.get("detected", {}) if isinstance(manifest_data.get("detected"), dict) else {}
    workplace_manifest_path: Path | None = None
    distribution_root: Path | None = None
    local_config = flow_root / "process-forge.local.yaml"
    if explicit_workplace:
        workplace_manifest_path = _project_coordination_state.workplace_manifest_path_from_root(Path(explicit_workplace).expanduser())
        if workplace_manifest_path.is_file():
            distribution_root = resolve_distribution_path(workplace_manifest_path, "processforge")
    elif local_config.is_file():
        workplace_manifest_path = _project_coordination_state.resolve_workplace_manifest(local_config)
        if workplace_manifest_path and workplace_manifest_path.is_file():
            distribution_root = resolve_distribution_path(workplace_manifest_path, "processforge")
    elif isinstance(manifest_data.get("workplace"), dict) and manifest_data["workplace"].get("reference") == "auto":
        distribution_root = project_root
    providers = _CapabilityRegistryReader(project_root).read(workplace_manifest_path)
    required_records, optional_records = _ProjectContextReadinessPolicy().capabilities(required, optional, providers)
    classification = _project_discovery_reader.classify_project(project_root, workplace_manifest_path)
    manifest_platform_contracts = manifest_data.get("platform_contracts") if isinstance(manifest_data.get("platform_contracts"), list) else []
    manifest_platform_ids = [
        str(item.get("platform") or str(item.get("id", "")).removeprefix("platform."))
        for item in manifest_platform_contracts
        if isinstance(item, dict) and (item.get("platform") or item.get("id"))
    ]
    meta_project_without_selection = _project_initialization_inputs.is_meta_workspace(manifest_data) and not manifest_platform_ids
    if not manifest_platform_ids and not meta_project_without_selection:
        manifest_platform_ids = classification["platforms"]
    platform_resolution = _platform_contract_resolver.resolve(workplace_manifest_path, manifest_platform_ids, project_root=project_root)
    available_platform_contracts = _project_platform_selection_service.available_records(workplace_manifest_path, project_root)
    if meta_project_without_selection:
        platform_selection = {
            "status": "not_applicable",
            "reason": f"Project type {_project_initialization_inputs.types_from_manifest(manifest_data)[0]} does not select one platform stack by default.",
        }
    elif manifest_platform_ids:
        platform_selection = {"status": "selected", "reason": "Project manifest or detection selected platform contracts."}
    else:
        platform_selection = {"status": "not_selected", "reason": "No platform contracts were selected for this project."}
    package_index_ids = set(_project_package_catalog_reader.index(project_root, distribution_root, workplace_manifest_path))
    required_resource_missing, recommended_resource_missing = _project_platform_selection_service.resource_findings(workplace_manifest_path, platform_resolution, package_index_ids)
    process_refs = manifest_data.get("processes") if isinstance(manifest_data.get("processes"), list) else []
    process_selection = project_process_selection(manifest_data)
    package_refs = manifest_data.get("packages") if isinstance(manifest_data.get("packages"), list) else []
    # An implicit task-batch fallback is a work-start default, not a project
    # resource-profile selection. Preserve the legacy generic-project snapshot
    # until a project explicitly declares a process or multi-process mapping.
    process_id_for_resolution = str(
        manifest_data.get("process")
        or (process_selection.get("default") if isinstance(manifest_data.get("processes"), dict) else "")
        or ""
    )
    manifest_specializations = project_specialization_selection(manifest_data, {})["active"]
    specialization_context = resolve_specialization_context(
        project_root,
        workplace_manifest_path,
        platform_ids=manifest_platform_ids,
        process_id=process_id_for_resolution,
        specialization_ids=manifest_specializations,
        platform_resolution=platform_resolution,
    )
    package_ids = [
        str(item.get("id"))
        for item in manifest_data.get("knowledge_stack", [])
        if isinstance(item, dict) and item.get("id")
    ]
    package_ids.extend(specialization_context["activated_knowledge_packages"])
    enabled_processes = [
        {"id": str(item.get("id", "unknown")), "path": str(item.get("path", ""))}
        for item in process_refs
        if isinstance(item, dict)
    ]
    selected_packages = [
        {"id": str(item.get("id", "unknown")), "path": str(item.get("path", ""))}
        for item in package_refs
        if isinstance(item, dict)
    ]
    package_ids.extend(item["id"] for item in selected_packages)
    required_package_ids = sorted(set(platform_resolution["required_knowledge_packages"]).intersection(set(specialization_context["activated_knowledge_packages"])))
    package_resources = resolve_package_resources(
        project_root,
        distribution_root,
        workplace_manifest_path,
        sorted(set(package_ids)),
        required_package_ids,
    )
    context_requirements = _KnowledgeResourceSelector().requirements(manifest_data)
    context_policy = _ProjectContextPolicy().build(manifest_data)
    direct_platform_package_ids = sorted(
        {
            str(package_id)
            for contract in platform_resolution.get("contracts", [])
            if isinstance(contract, dict)
            for package_id in [
                *(contract.get("required", {}).get("knowledge_packages", []) if isinstance(contract.get("required"), dict) else []),
                *(contract.get("recommended", {}).get("knowledge_packages", []) if isinstance(contract.get("recommended"), dict) else []),
            ]
            if str(package_id)
        }
    )
    resolved_knowledge_resources, resource_selection = _KnowledgeResourceSelector().select(
        package_resources,
        context_requirements,
        direct_package_ids=direct_platform_package_ids,
    )
    available_knowledge_resources = [_ResourceSnapshotRules().instance(resource) for resource in package_resources]
    local_search_resources = [
        {
            "id": str(item.get("id") or ""),
            "resource_id": str(item.get("id") or ""),
            "package_id": str(item.get("package_id") or ""),
            "kind": str(item.get("kind") or "knowledge"),
            "title": str(item.get("title") or item.get("id") or ""),
            "description": str(item.get("description") or ""),
            "version": str(item.get("version") or item.get("generation") or ""),
            "fingerprint": item.get("fingerprint") if isinstance(item.get("fingerprint"), dict) else {},
            "path_ref": item.get("path_ref") if isinstance(item.get("path_ref"), dict) else {},
            "status": str(item.get("status") or "available"),
            "load_policy": "snapshot_authorized",
            "indexing": _ResourceSnapshotRules().indexing(item, resource_selection),
        }
        for item in resolved_knowledge_resources
        if str(item.get("id") or "")
    ]
    template_ids = {str(item) for item in specialization_context.get("activated_templates", []) if str(item)}
    template_ids.update(
        str(item.get("id") or "")
        for item in context_requirements.get("templates", [])
        if isinstance(item, dict) and str(item.get("id") or "")
    )
    for template_id in sorted(template_ids):
        entry = workplace_registry_entry(workplace_manifest_path, "templates", template_id)
        if entry and str(entry.get("status") or "available") not in {"missing", "disabled"}:
            local_search_resources.append(
                {
                    "id": template_id,
                    "resource_id": template_id,
                    "package_id": str(entry.get("template_root") or ""),
                    "kind": "template",
                    "title": str(entry.get("title") or template_id),
                    "description": str(entry.get("description") or ""),
                    "version": str(entry.get("version") or ""),
                    "path_ref": {"registry": "templates", "id": template_id},
                    "status": str(entry.get("status") or "available"),
                    "load_policy": "snapshot_authorized",
                    "indexing": entry.get("indexing") if isinstance(entry.get("indexing"), dict) else {
                        "enabled": True,
                        "mode": "metadata",
                        "fields": ["title", "description", "version", "path"],
                        "sources": [
                            {"path": "README.md", "mode": "fulltext", "include": ["README.md"], "role": "description"},
                            {"path": ".", "mode": "metadata", "role": "template_root"},
                        ],
                    },
                }
            )
    reproducibility = _ResourceSnapshotRules().reproducibility(resolved_knowledge_resources)
    parameter_resolution = resolve_project_parameters(
        project_root,
        workplace_manifest_path,
        manifest_data,
        platform_resolution,
        manifest_specializations,
        manifest_platform_ids,
        process_id_for_resolution,
        manifest_path_refs(project_root, "processes"),
    )
    coordination_status = _project_coordination_state.effective_project_coordination(project_root, explicit_workplace)
    coordination_blocked = coordination_status["effective_mode"] == "organized" and (
        not coordination_status["workplace_director_enabled"] or not coordination_status["director_office_exists"]
    )
    health_status = "blocked" if any(item["severity"] == "fail" for item in required_records) or platform_resolution["missing_required_contracts"] or platform_resolution["circular_platforms"] or required_resource_missing or specialization_context["conflicts"] or parameter_resolution["conflicts"] or coordination_blocked else ("warn" if any(item["severity"] == "warn" for item in optional_records) or recommended_resource_missing else "pass")
    readiness_policy = _ProjectContextReadinessPolicy()
    execution_readiness = readiness_policy.execution(
        required_records,
        specialization_context.get("capability_resolution") if isinstance(specialization_context.get("capability_resolution"), dict) else {},
        coordination_blocked=coordination_blocked,
    )
    resource_readiness = readiness_policy.resources(
        platform_resolution=platform_resolution,
        required_resource_missing=required_resource_missing,
        specialization_conflicts=specialization_context["conflicts"],
        parameter_conflicts=parameter_resolution["conflicts"],
    )
    snapshot_id = f"ctx-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    requirements = _parameter_source_service.requirements_fingerprints(flow_root, project_root)
    source_fingerprints = {
        "workplace_manifest": next((item.get("checksum") for item in sources if item.get("id") == "workplace_manifest"), "missing"),
        "package_roots_registry": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "package-roots.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "package-roots.yaml").is_file() else "missing",
        "knowledge_roots_registry": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "knowledge-roots.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "knowledge-roots.yaml").is_file() else "missing",
        "template_registry": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "templates.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "templates.yaml").is_file() else "missing",
        "tool_registry": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "tools.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "tools.yaml").is_file() else "missing",
        "parameters_registry": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "parameters.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "parameters.yaml").is_file() else "missing",
        "installed_subjects": "sha256:" + sha256_file(workplace_manifest_path.parent / "registries" / "installed-subjects.yaml") if workplace_manifest_path and (workplace_manifest_path.parent / "registries" / "installed-subjects.yaml").is_file() else "missing",
    }
    return {
        "schema_version": 1,
        "id": snapshot_id,
        "generated_at": generated_at,
        "snapshot": {
            "id": snapshot_id,
            "generated_at": generated_at,
            "valid_until": valid_until,
            "refresh_policy": {
                "max_age_days": max_age_days,
                "refresh_when_sources_change": True,
                "refresh_when_workplace_changes": True,
                "refresh_when_package_versions_change": True,
                "refresh_when_required_tools_change": True,
            },
            "health": {"status": health_status},
        },
        "project": {
            "id": str(project.get("id", safe_id(project_root.name))),
            "name": str(project.get("name", project_root.name)),
            "type": (
                project.get("type")
                if str(project.get("type") or "") not in {"", "auto", "unknown"}
                else (classification["project_types"][0] if classification["project_types"] else "unknown")
            ),
        },
        "project_classification": classification,
        "flow": {
            "root": _telemetry_event_service.flow_label(project_root),
            "layout": flow_layout(project_root),
            "manifest": rel(manifest, project_root),
            "local_config": rel(flow_root / "process-forge.local.yaml", project_root),
        },
        "process_forge": {
            "version": str(process_forge_data.get("version", "1.0.0")),
            "version_constraint": str(process_forge_data.get("version_constraint", "^1.0")),
            "install_mode": str(process_forge_data.get("install_mode", "linked")),
            "distribution": {
                "id": "processforge",
                "source": "workplace" if workplace_manifest_path else "project",
                "path": "<private-distribution-ref>" if distribution_root else "missing",
                "status": "available" if distribution_root and distribution_root.is_dir() else "missing",
            },
        },
        "platform_contracts": {
            "available": available_platform_contracts,
            "selected": platform_resolution["contracts"],
            "stack": platform_resolution["platform_stack"],
            "missing_required": platform_resolution["missing_required_contracts"],
            "circular": platform_resolution["circular_platforms"],
            "missing_required_resources": required_resource_missing,
            "missing_recommended_resources": recommended_resource_missing,
        },
        "available_platform_contracts": available_platform_contracts,
        "selected_platform_contracts": platform_resolution["contracts"],
        "platform_selection": platform_selection,
        "platform_stack": platform_resolution["platform_stack"],
        "sources": {"fingerprints": sources},
        "requirements_fingerprint": requirements,
        "context_requirements": context_requirements,
        "context_policy": context_policy,
        "resolved_parameters": parameter_resolution["resolved_parameters"],
        "parameter_resolution": {
            "status": parameter_resolution["status"],
            "sources": parameter_resolution["sources"],
            "provenance": parameter_resolution["provenance"],
            "conflicts": parameter_resolution["conflicts"],
        },
        "resolved_context": specialization_context,
        "active_resource_profile": specialization_context["active_resource_profile"],
        "execution_route": specialization_context["execution_route"],
        "capability_resolution": specialization_context["capability_resolution"],
        "selected_specializations": specialization_context["selected_specializations"],
        "applied_project_overrides": specialization_context["applied_project_overrides"],
        "effective_fingerprints": specialization_context["effective_fingerprints"],
        "resolution_reasons": specialization_context["resolution_reasons"],
        "conflicts": specialization_context["conflicts"] + parameter_resolution["conflicts"],
        "resolved": {
            "knowledge_packages": [{"id": item, "constraint": "declared"} for item in sorted(set(package_ids))],
            "knowledge_resources": resolved_knowledge_resources,
            "available_knowledge_resources": available_knowledge_resources,
            "template_packages": context_requirements.get("template_packages", []),
            "templates": [{"id": item, "status": "activated"} for item in specialization_context["activated_templates"]],
            "excluded_templates": [{"id": item, "reason": "excluded by specialization or project override"} for item in specialization_context["excluded_templates"]],
            "tools": [{"id": item, "status": "activated"} for item in specialization_context["activated_tools"]],
            "excluded_tools": [{"id": item, "reason": "excluded by specialization or project override"} for item in specialization_context["excluded_tools"]],
            "platform_contracts": context_requirements.get("platform_contracts", []),
            "process_packages": selected_packages,
        },
        "local_search_resources": local_search_resources,
        "resource_selection": resource_selection,
        "freshness": {
            "status": "fresh",
            "checked_at": generated_at,
            "stale_reasons": [],
            "update_available": [],
            "broken_refs": [],
        },
        "readiness": {
            "context": {"status": "fresh"},
            "resources": resource_readiness,
            "execution": execution_readiness,
        },
        "resource_readiness": resource_readiness,
        "execution_readiness": execution_readiness,
        "reproducibility": reproducibility,
        "source_fingerprints": source_fingerprints,
        "knowledge_stack": manifest_data.get("knowledge_stack", [{"id": "processforge.core", "version": "1.0.0", "source": "distribution"}]),
        "resolved_policies": {
            "hard": [
                {"id": "public.no_local_absolute_paths", "value": True, "locked": True},
                {"id": "files.one_writer_per_scope", "value": True, "locked": True},
                {"id": "secrets.public_exports_sanitized", "value": True, "locked": True},
                {"id": "runtime.private", "value": True, "locked": True},
                {"id": "markdown.not_machine_merge_source", "value": True, "locked": True},
            ],
            "preferences": [
                {"id": "templates.project_overrides_global", "value": True},
                {"id": "session.prefer_project_context_snapshot", "value": True},
            ],
        },
        "capabilities": {"required": required_records, "optional": optional_records},
        "knowledge_resources": {
            "selected": resolved_knowledge_resources,
            "available": available_knowledge_resources,
            "required": [item for item in resolved_knowledge_resources if item.get("requirement") == "required"],
            "recommended": [item for item in resolved_knowledge_resources if item.get("requirement") == "recommended"],
            "missing_required": required_resource_missing,
            "missing_recommended": recommended_resource_missing,
        },
        "tools": {"required": platform_resolution["required_tools"], "recommended": platform_resolution["recommended_tools"], "activated": specialization_context["activated_tools"], "excluded": specialization_context["excluded_tools"], "source": "workplace-registry"},
        "mcp": {"required": platform_resolution["required_mcp"], "recommended": platform_resolution["recommended_mcp"], "activated": specialization_context["activated_mcp"], "excluded": specialization_context["excluded_mcp"], "source": "workplace-registry"},
        "templates": {
            "project": [str(item["path"]) for item in sources if item.get("kind") == "template"],
            "required": platform_resolution["required_templates"],
            "recommended": platform_resolution["recommended_templates"],
            "activated": specialization_context["activated_templates"],
            "excluded": specialization_context["excluded_templates"],
            "source": "workplace-registry",
        },
        "processes": {"enabled": enabled_processes, "selection": process_selection},
        "packages": {"selected": selected_packages},
        "workplace_coordination": {
            "project_mode": coordination_status["project_mode"],
            "workplace_default_project_mode": coordination_status["workplace_default_project_mode"],
            "effective_mode": coordination_status["effective_mode"],
            "director_enabled": bool(coordination_status["workplace_director_enabled"] and coordination_status["effective_mode"] == "organized"),
            "director_available_at_workplace": bool(coordination_status["workplace_director_enabled"]),
            "director_office_exists": bool(coordination_status["director_office_exists"]),
            "director_required": bool(coordination_status["director_required"]),
            "director_process": coordination_status["director_process"] if coordination_status["effective_mode"] == "organized" else None,
            "director_inbox": coordination_status["director_inbox"] if coordination_status["effective_mode"] == "organized" else {"enabled": False},
        },
        "session": {
            "startup_read_order": [
                "AGENTS.md" if (project_root / "AGENTS.md").is_file() else rel(flow_root / "AGENTS.md", project_root),
                rel(flow_root / "process-forge.yaml", project_root),
                "pf.context; verify current snapshot freshness and readiness with the existing CLI when MCP is unavailable",
                "pf.work.start / pf.work.state: returned assignment and immutable capsule, identity, scope and obligations",
                "pf.work.search / pf.work.resolve: exact returned Work/context selectors and authorized resources",
                "extended .pf/AGENTS.md and relevant artifacts/logs/reviews/handoffs on demand",
            ],
            "telemetry_root": rel(flow_root / "runtime" / "telemetry", project_root),
            "events_log": rel(flow_root / "runtime" / "events" / "events.sqlite3", project_root),
        },
    }




def parse_snapshot_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def project_context_freshness(project_root: Path, *, explicit_workplace: str | None = None) -> tuple[str, list[str], dict[str, Any]]:
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    if not snapshot_yaml.is_file():
        return "missing", [], {}
    snapshot = load_yaml_document(snapshot_yaml)
    result = project_context_check_result(project_root, explicit_workplace=explicit_workplace)
    reasons = [str(item.get("reason") or item) for item in result.get("stale_resources", []) if isinstance(item, dict)]
    reasons.extend(str(item.get("reason") or item) for item in result.get("broken_refs", []) if isinstance(item, dict))
    return str(result.get("status") or "stale"), reasons, snapshot


def write_project_context_snapshot_outputs(project_root: Path, *, explicit_workplace: str | None = None) -> tuple[str, dict[str, Path], dict[str, Any], list[str]]:
    snapshot = build_project_context_snapshot(project_root, explicit_workplace=explicit_workplace)
    status, reasons, _previous = project_context_freshness(project_root, explicit_workplace=explicit_workplace)
    if status == "missing":
        reasons = []
    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    snapshot_yaml.parent.mkdir(parents=True, exist_ok=True)
    generations = project_context_snapshot_generations_dir(project_root)
    generations.mkdir(parents=True, exist_ok=True)
    generation_path = generations / f"{snapshot['snapshot']['id']}.yaml"
    generation_path.write_text(ensure_trailing_newline(dump_yaml(snapshot)), encoding="utf-8")
    snapshot_yaml.write_text(ensure_trailing_newline(dump_yaml(snapshot)), encoding="utf-8")
    snapshot_md.write_text(_ProjectContextSnapshotRenderer().render(snapshot, "fresh", []), encoding="utf-8")
    marker = project_context_stale_marker_path(project_root)
    if marker.is_file():
        marker.unlink()
    workplace_snapshot = _session_metadata_writer.write_workplace_context_snapshot(project_root, snapshot)
    report = project_context_report_path(project_root)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Project Context Refresh Report",
                "",
                f"- snapshot_id: {snapshot['snapshot']['id']}",
                f"- status: fresh",
                f"- previous_status: {status}",
                f"- generation: {rel(generation_path, project_root)}",
                f"- current: {rel(snapshot_yaml, project_root)}",
                "",
                "Existing assignment capsules are immutable and remain pinned to their original snapshot id and checksum.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return "fresh", {"snapshot_yaml": snapshot_yaml, "snapshot_md": snapshot_md, "snapshot_generation": generation_path, "refresh_report": report, "workplace_snapshot": workplace_snapshot}, snapshot, reasons












def iter_process_events(path: Path):
    return _process_event_journal.records(path)


def process_event_exists(path: Path, event_id: str) -> bool:
    return _process_event_journal.contains(path, event_id)










def project_id(project_root: Path) -> str:
    return _context_contract_inputs.project_id(project_root)


























def flush_pending_event_dispatches(project_root: Path, *, limit: int = 100) -> None:
    path = _run_task_inputs.event_runtime_paths(project_root)[0]
    for pending in _process_event_journal.pending_dispatch(path, limit=limit):
        _runtime_hook_dispatcher.dispatch_hooks(project_root, pending, dry_run=False, outbox=True)
        _process_event_journal.complete_dispatch(path, _hook_dispatch_policy.event_id_value(pending))










def iter_ndjson(path: Path) -> list[tuple[int, Any, str | None]]:
    return NdjsonReader().read(path)


def chat_transcript_path(project_root: Path, session_id: str) -> Path:
    return ChatTranscriptReader(project_root).path(session_id)


def legacy_chat_transcript_path(project_root: Path, session_id: str) -> Path:
    return ChatTranscriptReader(project_root).legacy_path(session_id)


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()








def load_chat_messages(project_root: Path, session_id: str) -> list[dict[str, Any]]:
    return ChatTranscriptReader(project_root).messages(session_id)










def build_context_payload(project_root: Path, assignment: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    flow_root = locate_flow_root(project_root)
    source_reader = ProjectContextSourcesReader(project_root)
    sources = source_reader.read(assignment)
    fingerprints = source_reader.fingerprints(sources)
    texts = source_reader.texts(sources)
    capabilities = resolve_capabilities(texts, project_root)
    allowed_actions, forbidden_actions = _ProjectContextRules().action_rules(texts)

    conflicts: list[dict[str, str]] = []
    for item in sources:
        if item.get("required") and not item.get("exists"):
            conflicts.append({"status": "blocked", "message": f"required source missing: {item['path']}", "source": str(item["path"])})
    manifest_rel = rel(flow_root / "process-forge.yaml", project_root)
    manifest_text = texts.get(manifest_rel, "")
    if manifest_text:
        if not is_public_path_safe(manifest_text):
            conflicts.append({"status": "blocked", "message": "public manifest contains a local absolute path", "source": manifest_rel})
        if contains_secret_value(manifest_text):
            conflicts.append({"status": "blocked", "message": "public manifest contains a secret-like value", "source": manifest_rel})
    for capability in capabilities["missing_required"]:
        conflicts.append({"status": "blocked", "message": f"required capability is unresolved: {capability}", "source": "capabilities"})
    for capability in capabilities["missing_optional"]:
        conflicts.append({"status": "warn", "message": f"optional capability is unresolved: {capability}", "source": "capabilities"})

    overlap = sorted(set(allowed_actions).intersection(forbidden_actions))
    for action in overlap:
        conflicts.append({"status": "blocked", "message": f"action is both allowed and forbidden: {action}", "source": "resolved-rules"})

    gitignore = project_root / ".gitignore"
    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        if ".pf/runtime/" not in ignore_text:
            conflicts.append({"status": "warn", "message": "runtime cache path is not ignored", "source": ".gitignore"})
    if assignment is None:
        conflicts.append({"status": "warn", "message": "broad project context includes available sources that workers should not load by default", "source": "context-index"})

    if any(item["status"] == "blocked" for item in conflicts):
        status = "blocked"
    elif any(item["status"] == "requires_approval" for item in conflicts):
        status = "requires_approval"
    elif any(item["status"] == "warn" for item in conflicts):
        status = "warn"
    else:
        status = "resolved"

    selected_processes = [Path(str(item["path"])).stem for item in sources if item["kind"] == "process" and item["exists"]]
    selected_packages = [Path(str(item["path"])).stem for item in sources if item["kind"] == "package" and item["exists"]]
    selected_templates = [Path(str(item["path"])).name for item in sources if item["kind"] == "template" and item["exists"]]
    template_records = [
        {
            "id": safe_id(Path(str(item["path"])).stem, "template"),
            "path": str(item["path"]),
            "source": "project",
            "status": "selected" if item.get("load_policy") != "available" else "available",
        }
        for item in sources
        if item["kind"] == "template" and item["exists"]
    ]

    index = {
        "schema_version": 1,
        "context": {
            "id": "context-index",
            "generated_at": _core_common_clock.now_utc(),
            "mode": "context_resolve",
            "project_flow": manifest_rel,
        },
        "sources": sources,
        "selected_processes": selected_processes,
        "selected_packages": selected_packages,
        "selected_templates": selected_templates,
        "capabilities": capabilities,
        "fingerprints": fingerprints,
        "freshness": {"status": "fresh", "stale_sources": []},
    }
    resolved = {
        "schema_version": 1,
        "rules": {
            "hard": [
                {"id": "public-files-no-local-paths", "source": "process-forge.yaml"},
                {"id": "no-secret-values-in-generated-files", "source": "process-forge.yaml"},
            ],
            "locked": [{"id": "locked-hard-policies-cannot-be-weakened", "source": "process-forge.yaml"}],
            "preferences": [],
            "gates": [{"id": "blocked-conflicts-stop-context-compile", "source": "context-resolution"}],
            "tools": [{"id": "processforge-cli", "source": "tools/processforge.py"}],
            "templates": template_records,
        },
        "allowed_actions": allowed_actions,
        "forbidden_actions": forbidden_actions,
        "merge": {
            "order": [
                "core",
                "workplace",
                "organization",
                "direction",
                "specialization",
                "platform",
                "toolchain",
                "project",
                "process",
                "stage",
                "task",
                "agent_profile",
            ],
            "conflict_policy": "block_on_locked_policy_conflict",
        },
        "source_fingerprints": fingerprints,
    }
    report = _ProjectContextRules().conflict_report(status, conflicts, fingerprints)
    return index, resolved, report, status


def write_context_outputs(project_root: Path, assignment: Path | None = None) -> tuple[str, dict[str, Path]]:
    index, resolved, report, status = build_context_payload(project_root, assignment)
    flow_root = locate_flow_root(project_root)
    contexts = flow_root / "contexts"
    cache = flow_root / "runtime" / "cache"
    contexts.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    paths = {
        "context_index": contexts / "context-index.yaml",
        "resolved_rules": contexts / "resolved-rules.yaml",
        "conflict_report": contexts / "context-conflict-report.md",
        "context_cache": cache / "context-cache.yaml",
    }
    paths["context_index"].write_text(ensure_trailing_newline(dump_yaml(index)), encoding="utf-8")
    paths["resolved_rules"].write_text(ensure_trailing_newline(dump_yaml(resolved)), encoding="utf-8")
    paths["conflict_report"].write_text(report, encoding="utf-8")
    cache_payload = {
        "schema_version": 1,
        "cache": {"id": "context-cache", "generated_at": _core_common_clock.now_utc(), "status": "fresh" if status != "blocked" else "stale"},
        "fingerprints": index["fingerprints"],
        "sources": index["sources"],
        "health": {"conflict_status": status},
    }
    paths["context_cache"].write_text(ensure_trailing_newline(dump_yaml(cache_payload)), encoding="utf-8")
    return status, paths






def assignment_id(path: Path) -> str:
    return safe_id(path.stem, "assignment")


def conflict_metric(report: str, key: str) -> int:
    match = re.search(rf"(?m)^{re.escape(key)}" + COLON_WS + r"(\d+)\s*$", report)
    return int(match.group(1)) if match else 0


def normalized_context_status(status: str) -> str:
    return "pass" if status == "resolved" else status


def unique_context_path(contexts: Path, assn_id: str, suffix: str) -> Path:
    stamp = _core_common_clock.now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    return contexts / f"{assn_id}.{stamp}.{suffix}"


def ecp_checksum(payload: dict[str, Any]) -> str:
    stable = dict(payload)
    stable["checksum"] = "pending"
    return hashlib.sha256(ensure_trailing_newline(dump_yaml(stable)).encode("utf-8")).hexdigest()


def compile_execution_context(
    project_root: Path,
    assignment: Path,
    *,
    write_capsule: bool = False,
    supersede: bool = False,
    allow_requires_approval: bool = False,
) -> tuple[Path, Path | None, Path]:
    if not assignment.is_file():
        raise SystemExit(f"FAIL: assignment not found: {assignment}")

    index, resolved, report, status = build_context_payload(project_root, assignment)
    assn_id = assignment_id(assignment)
    flow_root = locate_flow_root(project_root)
    contexts = flow_root / "contexts"
    contexts.mkdir(parents=True, exist_ok=True)
    assignment_conflict_report = contexts / f"{assn_id}.conflicts.md"
    assignment_conflict_report.write_text(report, encoding="utf-8")

    if status == "blocked":
        raise SystemExit(f"FAIL: assignment context has blocking conflicts: {rel(assignment_conflict_report, project_root)}")
    if status == "requires_approval" and not allow_requires_approval:
        raise SystemExit(f"FAIL: assignment context requires approval: {rel(assignment_conflict_report, project_root)}")

    ecp_path = contexts / f"{assn_id}.ecp.yaml"
    supersedes: str | None = None
    if ecp_path.exists():
        if not supersede:
            raise SystemExit(f"FAIL: ECP already exists: {rel(ecp_path, project_root)}")
        supersedes = rel(ecp_path, project_root)
        ecp_path = unique_context_path(contexts, assn_id, "ecp.yaml")
    capsule_path: Path | None = contexts / f"{assn_id}.capsule.yaml" if write_capsule else None
    if capsule_path and capsule_path.exists():
        if not supersede:
            raise SystemExit(f"FAIL: capsule already exists: {rel(capsule_path, project_root)}")
        capsule_path = unique_context_path(contexts, assn_id, "capsule.yaml")

    sources = [
        {
            "path": item["path"],
            "checksum": item.get("checksum", "missing"),
            "kind": item.get("kind", "source"),
            "selection_reason": item.get("selection_reason", ""),
            "load_policy": item.get("load_policy", ""),
        }
        for item in index["sources"]
        if item.get("required") or item.get("load_policy") == "read_required"
    ]
    source_fingerprints = [{"path": item["path"], "checksum": item.get("checksum", "missing")} for item in sources]
    context_status = normalized_context_status(status)
    ecp = {
        "schema_version": 1,
        "id": f"{assn_id}-context",
        "type": "execution_context_package",
        "assignment": assn_id,
        "assignment_path": rel(assignment, project_root),
        "process": "assignment-execute",
        "stage": "assignment_execute",
        "role": "worker",
        "context_status": context_status,
        "blocking_conflicts": conflict_metric(report, "blocking_conflicts"),
        "warnings": conflict_metric(report, "warnings"),
        "requires_approval": conflict_metric(report, "requires_approval"),
        "conflict_report": rel(assignment_conflict_report, project_root),
        "source_fingerprints": source_fingerprints,
        "read_sources": [str(item["path"]) for item in sources],
        "resolved_rules": {
            "allowed_actions": resolved["allowed_actions"],
            "forbidden_actions": resolved["forbidden_actions"],
            "merge": resolved["merge"],
        },
        "allowed_files": [rel(assignment, project_root)],
        "forbidden_files": [],
        "required_outputs": [],
        "required_capabilities": index["capabilities"].get("required", []),
        "selected_tools": ["processforge-cli"],
        "selected_mcp": [],
        "selected_templates": resolved["rules"].get("templates", []),
        "created_at": _core_common_clock.now_utc(),
        "checksum": "pending",
        "context": {
            "id": f"{assn_id}-context",
            "created_at": _core_common_clock.now_utc(),
            "immutable": True,
            "context_index": rel(contexts / "context-index.yaml", project_root),
            "conflict_report": rel(assignment_conflict_report, project_root),
        },
        "task_input": [rel(assignment, project_root)],
        "sources": sources,
        "packages": [{"id": item, "status": "available"} for item in index.get("selected_packages", [])],
        "templates": resolved["rules"].get("templates", []),
        "allowed_actions": resolved["allowed_actions"],
        "forbidden_actions": resolved["forbidden_actions"],
        "quality_gates": ["doctor-context"],
        "checksums": {"assignment": sha256_file(assignment), "context_index": sha256_file(contexts / "context-index.yaml")},
    }
    if supersedes:
        ecp["supersedes"] = supersedes
    ecp["checksum"] = ecp_checksum(ecp)
    ecp_path.write_text(ensure_trailing_newline(dump_yaml(ecp)), encoding="utf-8")

    if write_capsule:
        assert capsule_path is not None
        capsule = {
            "schema_version": 1,
            "capsule": {
                "id": f"{assn_id}-capsule",
                "ecp": rel(ecp_path, project_root),
                "worker_may_rebuild_context": False,
            },
            "assignment": {"id": assn_id, "path": rel(assignment, project_root)},
            "context": {
                "freshness": _project_session_read_service.legacy_freshness(project_root)[0],
                "conflict_status": status,
                "context_status": context_status,
                "conflict_report": rel(assignment_conflict_report, project_root),
            },
            "required_sources": [str(item["path"]) for item in sources],
            "allowed_files": [rel(assignment, project_root)],
            "forbidden_files": [],
            "allowed_actions": resolved["allowed_actions"],
            "forbidden_actions": resolved["forbidden_actions"],
        }
        capsule_path.write_text(ensure_trailing_newline(dump_yaml(capsule)), encoding="utf-8")
    return ecp_path, capsule_path, assignment_conflict_report




def render_session_status(project_root: Path, mode: str) -> str:
    flow_root = locate_flow_root(project_root)
    manifest = flow_root / "process-forge.yaml"
    manifest_text = manifest.read_text(encoding="utf-8", errors="replace") if manifest.is_file() else ""
    name_match = re.search(r"(?m)^\s*name" + COLON_WS + r"(.+?)\s*$", manifest_text)
    version_match = re.search(r"(?m)^\s*version" + COLON_WS + r"(.+?)\s*$", manifest_text)
    project_name = name_match.group(1).strip() if name_match else project_root.name
    flow_version = version_match.group(1).strip() if version_match else "unknown"
    snapshot_freshness, snapshot_stale, _snapshot = project_context_freshness(project_root)
    legacy_freshness, legacy_stale = _project_session_read_service.legacy_freshness(project_root)
    freshness = snapshot_freshness if snapshot_freshness != "missing" else legacy_freshness
    stale = snapshot_stale if snapshot_freshness != "missing" else legacy_stale
    conflict_status = _project_session_read_service.report_status(flow_root / "contexts" / "context-conflict-report.md")
    assignments = _project_session_read_service.recent_files(flow_root, "assignments", rel_root=project_root)
    artifacts = _project_session_read_service.recent_files(flow_root, "artifacts", rel_root=project_root)
    reviews = _project_session_read_service.recent_files(flow_root, "reviews", rel_root=project_root)
    adrs = _project_session_read_service.recent_files(flow_root, "adr", rel_root=project_root)

    def markdown_items(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- None."

    blocked = []
    if conflict_status == "blocked":
        blocked.append("Context conflict report is blocked.")
    if freshness in {"missing", "stale"}:
        blocked.append(f"Context freshness is {freshness}.")

    return "\n".join(
        [
            "# ProcessForge Session Status",
            "",
            "## Project",
            "",
            project_name,
            "",
            "## Flow Version",
            "",
            flow_version,
            "",
            "## Project Flow Root",
            "",
            _telemetry_event_service.flow_label(project_root),
            "",
            "## Session Mode",
            "",
            mode,
            "",
            "## Context Freshness",
            "",
            freshness + (f": {', '.join(stale)}" if stale else ""),
            "",
            "## Completed Work",
            "",
            markdown_items(artifacts),
            "",
            "## Current Active Assignments",
            "",
            markdown_items(assignments),
            "",
            "## Blocked Items",
            "",
            markdown_items(blocked),
            "",
            "## Latest Reviews",
            "",
            markdown_items(reviews),
            "",
            "## Important ADR",
            "",
            markdown_items(adrs),
            "",
            "## Risks",
            "",
            "- Project context snapshot is the preferred operational map; context cache is only an accelerator.",
            "",
            "## Recommended Next Steps",
            "",
            "- Run project-context-refresh if the snapshot is stale or missing.",
            "- Run assignment-capsule before starting assignment workers.",
            "",
            "## Suggested Assignments",
            "",
            "- None.",
            "",
        ]
    )


def command_session_start(args: argparse.Namespace) -> int:
    if getattr(args, "agent", None):
        return command_agent_checkin(args)
    if not getattr(args, "mode", None):
        raise SystemExit("FAIL: session-start requires --mode for telemetry bootstrap or --agent for agent session check-in")
    if not getattr(args, "project_root", None):
        raise SystemExit("FAIL: --project-root is required for session-start telemetry bootstrap")
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    _run_task_inputs.require_flow_root(project_root)
    session_id = _telemetry_event_service.telemetry_session_id()
    session_path, telemetry_path = _session_metadata_writer.session_runtime_paths(project_root, session_id)
    freshness, stale_reasons, snapshot = project_context_freshness(project_root)
    if args.rebuild_context_if_stale and freshness in {"missing", "stale"}:
        status, paths, snapshot, _old_reasons = write_project_context_snapshot_outputs(project_root, explicit_workplace=getattr(args, "workplace", None))
        freshness = status
        stale_reasons = []
        print(f"PROJECT_CONTEXT: {status}")
        for path in paths.values():
            print(f"WROTE: {rel(path, project_root)}")
    check_result = project_context_check_result(project_root, explicit_workplace=getattr(args, "workplace", None)) if project_context_snapshot_paths(project_root)[0].is_file() else {"status": freshness, "policy_action": "project-context-refresh", "recommended_action": "project-context-refresh"}
    print(f"PROJECT_CONTEXT_CHECK: {check_result.get('status')} policy_action={check_result.get('policy_action')}")
    if check_result.get("status") == "broken" and check_result.get("policy_action") == "block":
        print("PROJECT_CONTEXT_BLOCKED: broken snapshot")
        return 1
    _session_metadata_writer.write_session_metadata(project_root, session_id, args.mode, freshness, telemetry_path)
    _process_event_recorder.emit_process_event(
        project_root,
        "session.started",
        session_id=session_id,
        payload={"mode": args.mode, "snapshot_status": freshness},
        correlation_id=session_id,
    )
    _telemetry_event_service.append_telemetry_event(telemetry_path, "session_start", mode=args.mode, actor="agent", session=session_id)
    _telemetry_event_service.append_telemetry_event(
        telemetry_path,
        "snapshot_check",
        path=rel(project_context_snapshot_paths(project_root)[0], project_root),
        status=check_result.get("status", freshness),
        policy_action=check_result.get("policy_action"),
        reasons=stale_reasons,
    )
    if freshness == "stale":
        _process_event_recorder.emit_process_event(
            project_root,
            "context.snapshot.stale",
            severity="warn",
            session_id=session_id,
            payload={"reasons": stale_reasons},
            correlation_id=session_id,
        )
    flow_root = locate_flow_root(project_root)
    read_order = [
        flow_root / "AGENTS.md",
        flow_root / "process-forge.yaml",
        flow_root / "contexts" / "project-context.snapshot.md",
    ]
    for source in read_order:
        _telemetry_event_service.append_telemetry_event(telemetry_path, "source_read", path=rel(source, project_root), exists=source.is_file(), reason="session_start")
    assignment_path = Path(args.assignment).expanduser().resolve() if args.assignment else None
    _telemetry_event_service.append_telemetry_event(
        telemetry_path,
        "assignment_loaded",
        path=rel(assignment_path, project_root) if assignment_path else None,
        status="loaded" if assignment_path and assignment_path.is_file() else "not_provided",
    )
    if assignment_path:
        _process_event_recorder.emit_process_event(
            project_root,
            "assignment.started",
            session_id=session_id,
            assignment_id_value=assignment_id(assignment_path),
            payload={"path": rel(assignment_path, project_root), "exists": assignment_path.is_file()},
            correlation_id=session_id,
        )
    capabilities = snapshot.get("capabilities", {}) if isinstance(snapshot, dict) else {}
    for capability in capabilities.get("required", []) if isinstance(capabilities, dict) else []:
        if isinstance(capability, dict):
            _telemetry_event_service.append_telemetry_event(telemetry_path, "capability_check", required=True, **capability)
    for capability in capabilities.get("optional", []) if isinstance(capabilities, dict) else []:
        if isinstance(capability, dict):
            _telemetry_event_service.append_telemetry_event(telemetry_path, "capability_check", required=False, **capability)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "tool_selected", tool="processforge-cli", reason="session_start")
    selected_specializations = [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(getattr(args, "specialization", []))]
    if selected_specializations:
        _telemetry_event_service.append_telemetry_event(telemetry_path, "specialization_switch", selected_specializations=selected_specializations, reason="explicit_session_start")
        _process_event_recorder.emit_process_event(project_root, "context.snapshot.refreshed", session_id=session_id, payload={"selected_specializations": selected_specializations, "reason": "garage_mode_specialization_switch"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "tool_invoked", tool="processforge-cli", command="session-start")
    _process_event_recorder.emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"tool": "processforge-cli", "command": "session-start"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "tool_failed", tool=None, status="skipped")
    _process_event_recorder.emit_process_event(project_root, "tool.failed", severity="warn", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "mcp_check", status="skipped", reason="no required MCP declared")
    _process_event_recorder.emit_process_event(project_root, "mcp.invoked", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "fallback_used", status="skipped")
    _process_event_recorder.emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"status": "fallback skipped"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "conflict_detected", status="none")
    _telemetry_event_service.append_telemetry_event(telemetry_path, "file_scope_checked", status="ok", flow_root=_telemetry_event_service.flow_label(project_root))
    report = render_session_status(project_root, args.mode)
    print(report, end="")
    if args.allow_write and not args.report_only:
        target = flow_root / "artifacts" / "session-status-report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report, encoding="utf-8")
        _telemetry_event_service.append_telemetry_event(telemetry_path, "artifact_written", path=rel(target, project_root))
        _process_event_recorder.emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"path": rel(target, project_root)}, correlation_id=session_id)
        print(f"WROTE: {rel(target, project_root)}")
    else:
        _telemetry_event_service.append_telemetry_event(telemetry_path, "artifact_written", status="skipped", reason="report_only")
    _telemetry_event_service.append_telemetry_event(telemetry_path, "review_requested", status="skipped")
    _process_event_recorder.emit_process_event(project_root, "review.requested", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "handoff_created", status="skipped")
    _process_event_recorder.emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"status": "handoff skipped"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "doctor_run", status="skipped")
    _telemetry_event_service.append_telemetry_event(telemetry_path, "session_end", status="completed")
    _process_event_recorder.emit_process_event(project_root, "session.ended", session_id=session_id, payload={"mode": args.mode, "status": "completed"}, correlation_id=session_id)
    print(f"SESSION: {rel(session_path, project_root)}")
    print(f"TELEMETRY: {rel(telemetry_path, project_root)}")
    return 0


def command_project_context_refresh(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    _run_task_inputs.require_flow_root(project_root)
    if getattr(args, "dry_run", False):
        snapshot = build_project_context_snapshot(project_root, explicit_workplace=getattr(args, "workplace", None))
        current = project_context_check_result(project_root, explicit_workplace=getattr(args, "workplace", None))
        proposal = {
            "schema_version": 1,
            "created_at": _core_common_clock.now_utc(),
            "reason": getattr(args, "reason", None) or "manual",
            "before": {"snapshot_id": current.get("snapshot_id"), "status": current.get("status")},
            "after": {"snapshot_id": snapshot.get("snapshot", {}).get("id"), "status": "fresh"},
            "impact": {
                "new_capsules": "use_new_snapshot_generation",
                "existing_capsules": "remain_pinned",
            },
            "resolved_resources": snapshot.get("resolved", {}).get("knowledge_resources", []),
        }
        if getattr(args, "write_proposal", None):
            proposal_path = Path(args.write_proposal).expanduser()
            if not proposal_path.is_absolute():
                proposal_path = project_root / proposal_path
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            proposal_path.write_text(ensure_trailing_newline(dump_yaml(proposal)), encoding="utf-8")
            print(f"WROTE: {rel(proposal_path, project_root)}")
        else:
            print(dump_yaml(proposal), end="")
        return 0
    session_id = _telemetry_event_service.telemetry_session_id("project-context-refresh")
    _session_path, telemetry_path = _session_metadata_writer.session_runtime_paths(project_root, session_id)
    _process_event_recorder.emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"command": "project-context-refresh", "reason": getattr(args, "reason", None)}, correlation_id=session_id)
    status, paths, snapshot, old_reasons = write_project_context_snapshot_outputs(project_root, explicit_workplace=getattr(args, "workplace", None))
    _telemetry_event_service.append_telemetry_event(telemetry_path, "session_start", mode="project_context_refresh", actor="agent")
    _telemetry_event_service.append_telemetry_event(telemetry_path, "snapshot_check", status="previous_" + ("stale" if old_reasons else "fresh"), reasons=old_reasons)
    for source in snapshot.get("sources", {}).get("fingerprints", []):
        if isinstance(source, dict):
            _telemetry_event_service.append_telemetry_event(telemetry_path, "source_read", path=source.get("path"), source_id=source.get("id"), reason="snapshot_fingerprint")
    for group in ("required", "optional"):
        for capability in snapshot.get("capabilities", {}).get(group, []):
            if isinstance(capability, dict):
                _telemetry_event_service.append_telemetry_event(telemetry_path, "capability_check", required=group == "required", **capability)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "tool_selected", tool="processforge-cli", reason="project_context_refresh")
    _telemetry_event_service.append_telemetry_event(telemetry_path, "tool_invoked", tool="processforge-cli", command="project-context-refresh")
    _process_event_recorder.emit_process_event(project_root, "tool.invoked", session_id=session_id, payload={"tool": "processforge-cli", "command": "project-context-refresh"}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "mcp_check", status="skipped", reason="no required MCP declared")
    _process_event_recorder.emit_process_event(project_root, "mcp.invoked", session_id=session_id, payload={"status": "skipped"}, correlation_id=session_id)
    for path in paths.values():
        _telemetry_event_service.append_telemetry_event(telemetry_path, "artifact_written", path=rel(path, project_root))
        _process_event_recorder.emit_process_event(project_root, "artifact.updated", session_id=session_id, payload={"path": rel(path, project_root)}, correlation_id=session_id)
    for group, event_type, severity in [
        ("required", "capability.missing", "error"),
        ("optional", "capability.missing", "warn"),
    ]:
        for capability in snapshot.get("capabilities", {}).get(group, []):
            if isinstance(capability, dict) and capability.get("status") == "missing":
                _process_event_recorder.emit_process_event(project_root, event_type, severity=severity, session_id=session_id, payload={"capability": capability.get("id")}, correlation_id=session_id)
    _telemetry_event_service.append_telemetry_event(telemetry_path, "session_end", status="completed")
    health = snapshot.get("snapshot", {}).get("health", {}).get("status") if isinstance(snapshot.get("snapshot"), dict) else "pass"
    _process_event_recorder.emit_process_event(
        project_root,
        "context.snapshot.refreshed",
        severity="warn" if health == "warn" else ("error" if health == "blocked" else "info"),
        session_id=session_id,
        payload={"status": status, "health": health, "paths": {key: rel(path, project_root) for key, path in paths.items()}},
        correlation_id=session_id,
    )
    workplace_manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, getattr(args, "workplace", None))
    maintenance: dict[str, Any] | None = None
    if workplace_manifest:
        maintenance = search_index_maintenance_for_known_projects(
            workplace_manifest.parent,
            reason="project-context-refresh",
            project_roots=[project_root],
        )
    print(f"STATUS: {status}")
    for path in paths.values():
        print(f"WROTE: {rel(path, project_root)}")
    if maintenance:
        print_search_index_maintenance_summary(maintenance)
    print(f"TELEMETRY: {rel(telemetry_path, project_root)}")
    resource_readiness = snapshot.get("resource_readiness") if isinstance(snapshot.get("resource_readiness"), dict) else {}
    return 1 if resource_readiness.get("status") == "blocked" else 0


def command_project_context_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    _run_task_inputs.require_flow_root(project_root)
    result = project_context_check_result(project_root, explicit_workplace=getattr(args, "workplace", None))
    result["session_start"] = bool(getattr(args, "session_start", False))
    result["check_update_candidates"] = getattr(args, "check_update_candidates", "if_due")
    if getattr(args, "write_report", None):
        report_path = Path(args.write_report).expanduser()
        if not report_path.is_absolute():
            report_path = project_root / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Project Context Check Report",
            "",
            f"- snapshot_id: {result.get('snapshot_id')}",
            f"- status: {result.get('status')}",
            f"- policy_action: {result.get('policy_action')}",
            f"- recommended_action: {result.get('recommended_action')}",
            "",
            "## Updates Available",
            "",
            dump_yaml(result.get("updates_available", [])),
            "",
            "## Stale Resources",
            "",
            dump_yaml(result.get("stale_resources", [])),
            "",
            "## Broken References",
            "",
            dump_yaml(result.get("broken_refs", [])),
            "",
            "## Resource Readiness",
            "",
            dump_yaml(result.get("resource_readiness", {})),
            "",
            "## Execution Readiness",
            "",
            dump_yaml(result.get("execution_readiness", {})),
            "",
            "## Temporary Files",
            "",
            dump_yaml(result.get("temporary_files", {})),
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        result["report"] = rel(report_path, project_root)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"SNAPSHOT_ID: {result.get('snapshot_id')}")
        print(f"STATUS: {result.get('status')}")
        print(f"POLICY_ACTION: {result.get('policy_action')}")
        print(f"RECOMMENDED_ACTION: {result.get('recommended_action')}")
        temporary = result.get("temporary_files", {})
        print(f"TEMPORARY_FILES: {temporary.get('status', 'unknown')} notification={temporary.get('notification', False)}")
        for item in result.get("updates_available", []):
            print(f"UPDATE_AVAILABLE: {item.get('id')} {item.get('snapshot_version')} -> {item.get('available_version')}")
        for item in result.get("stale_resources", []):
            print(f"STALE: {item.get('id', 'project-context')}: {item.get('reason')}")
        for item in result.get("broken_refs", []):
            print(f"BROKEN: {item.get('id', 'project-context')}: {item.get('reason')}")
        resource_readiness = result.get("resource_readiness") if isinstance(result.get("resource_readiness"), dict) else {}
        execution_readiness = result.get("execution_readiness") if isinstance(result.get("execution_readiness"), dict) else {}
        if resource_readiness:
            print(f"RESOURCE_READINESS: {resource_readiness.get('status')}")
        if execution_readiness:
            print(f"EXECUTION_READINESS: {execution_readiness.get('status')}")
            for item in execution_readiness.get("missing_capabilities", []) if isinstance(execution_readiness.get("missing_capabilities"), list) else []:
                if isinstance(item, dict):
                    print(f"CAPABILITY_MISSING: {item.get('capability')} required_by={item.get('required_by')}")
    if result.get("status") == "broken":
        return 1
    if getattr(args, "strict", False) and result.get("status") != "fresh":
        return 1
    return 0


def mark_project_context_stale(project_root: Path, *, subject: str, reason: str, source: str = "manual") -> Path:
    marker_path = project_context_stale_marker_path(project_root)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_version": 1,
        "marked_at": _core_common_clock.now_utc(),
        "subject": subject,
        "reason": reason,
        "source": source,
        "status": "stale",
        "recommended_action": "project-context-check",
    }
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coordination = _project_coordination_state.effective_project_coordination(project_root)
    if coordination.get("effective_mode") == "organized":
        flow_root = locate_flow_root(project_root)
        inbox_path = flow_root / "runtime" / "director" / "inbox" / f"context-stale-{safe_id(subject, 'subject')}.json"
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(json.dumps({"type": "context_snapshot_stale", **marker}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "context.snapshot.stale", severity="warn", payload={"subject": subject, "reason": reason, "source": source})
    return marker_path


def command_project_context_mark_stale(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    _run_task_inputs.require_flow_root(project_root)
    marker = mark_project_context_stale(project_root, subject=args.subject, reason=args.reason, source="project-context-mark-stale")
    print(f"MARKED_STALE: {rel(marker, project_root)}")
    return 0


def extract_assignment_front_matter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"FAIL: assignment not found: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return load_yaml_document(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return {}
    front_matter = match.group(1).strip()
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(front_matter)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(front_matter)


ACTIVE_ASSIGNMENT_STATUSES = {"draft", "ready", "open", "pending", "in_progress", "blocked", "debugging", "review", "ready_for_review"}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]








def normalize_context_artifacts(value: Any) -> list[dict[str, Any]]:
    return _context_contract_inputs.normalize_context_artifacts(value)












def normalize_execution_mode(value: Any) -> dict[str, Any]:
    return _context_contract_inputs.normalize_execution_mode(value)


def normalize_ownership(metadata: dict[str, Any], allowed_files: list[str]) -> dict[str, Any]:
    return _context_contract_inputs.normalize_ownership(metadata, allowed_files)


def normalize_non_overlap(value: Any, current_write_scope: list[str]) -> dict[str, Any]:
    return _context_contract_inputs.normalize_non_overlap(value, current_write_scope)






def validate_assignment_scope_overlaps(
    project_root: Path,
    metadata: dict[str, Any],
    *,
    assignment_path: Path | None = None,
) -> dict[str, Any]:
    current_id = safe_id(str(metadata.get("id") or (assignment_path.stem if assignment_path else "assignment")), "assignment")
    from processforge_core.process_execution import scope_handoff_predecessor
    handed_off_predecessor = scope_handoff_predecessor(project_root, metadata, sys.modules[__name__])
    current_scope = _context_contract_inputs.assignment_write_scope(metadata)
    forbidden_scope = _context_contract_inputs.assignment_scope_items(metadata.get("forbidden_files"))
    scope_conflicts = ScopeConflictService(project_root)
    conflicts = scope_conflicts.conflicts(
        current_id,
        current_scope,
        current_id,
        forbidden_scope,
        reason_prefix="assignment_forbidden_wins:",
    )
    flow_root = locate_flow_root(project_root)
    current_resolved = assignment_path.resolve() if assignment_path else None
    for candidate in sorted((flow_root / "assignments").glob("*.yaml")):
        if current_resolved and candidate.resolve() == current_resolved:
            continue
        other = load_yaml_document(candidate)
        if yaml_error(other):
            continue
        status = str(other.get("status", "")).strip()
        if status not in ACTIVE_ASSIGNMENT_STATUSES:
            continue
        other_scope = _context_contract_inputs.assignment_write_scope(other)
        if not other_scope:
            continue
        other_id = safe_id(str(other.get("id") or candidate.stem), "assignment")
        if other_id == handed_off_predecessor:
            continue
        current_deps = _context_contract_inputs.assignment_dependency_set(metadata)
        other_deps = _context_contract_inputs.assignment_dependency_set(other)
        if other_id in current_deps or current_id in other_deps:
            continue
        conflicts.extend(scope_conflicts.conflicts(current_id, current_scope, other_id, other_scope))
    return {"status": "fail" if conflicts else "pass", "conflicts": conflicts}


def overlap_allowed_check(overlap_check: dict[str, Any], source: str) -> dict[str, Any]:
    resolved = dict(overlap_check)
    resolved["policy"] = "allow"
    resolved["source"] = source
    if resolved.get("status") == "fail":
        resolved["status"] = "allowed"
        resolved["behavior"] = "write scope overlap allowed by resolved plan policy"
    return resolved






def normalized_assignment_contract(project_root: Path, assignment: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    from processforge_core.work.context import normalized_assignment_contract as normalize
    return normalize(project_root, assignment, metadata, sys.modules[__name__])






def workspace_access_public_path_issues(access: dict[str, list[Any]]) -> list[str]:
    return _context_contract_inputs.workspace_access_public_path_issues(access)






def command_assignment_capsule(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    assignment = Path(args.assignment).expanduser().resolve()
    metadata = extract_assignment_front_matter(assignment)
    if not metadata:
        raise SystemExit("FAIL: assignment has no YAML front matter; it is human-readable only and cannot produce an automated capsule")
    status, reasons, snapshot = project_context_freshness(project_root)
    if status not in {"fresh", "fresh_with_updates"}:
        raise SystemExit("FAIL: project context snapshot is not fresh: " + (", ".join(reasons) if reasons else status))
    assn_id = safe_id(str(metadata.get("id", assignment.stem)), "assignment")
    capsule_path = locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{assn_id}.capsule.yaml"
    if capsule_path.exists():
        raise SystemExit("FAIL: immutable_context_exists; create_successor_work; --force cannot replace a pinned capsule")
    if (metadata.get("process_execution") or {}).get("assignment_capsule"):
        raise SystemExit("FAIL: pinned_context_unavailable; create_successor_work or restore the exact recorded context")
    required = [str(item) for item in metadata.get("required_capabilities", [])] if isinstance(metadata.get("required_capabilities"), list) else []
    optional = [str(item) for item in metadata.get("optional_capabilities", [])] if isinstance(metadata.get("optional_capabilities"), list) else []
    providers = _CapabilityRegistryReader(project_root).read(_project_coordination_state.resolve_project_workplace_manifest(project_root))
    required_records, optional_records = _ProjectContextReadinessPolicy().capabilities(required, optional, providers)
    missing_required = [item["id"] for item in required_records if item.get("status") == "missing"]
    if missing_required:
        for capability in missing_required:
            _process_event_recorder.emit_process_event(project_root, "capability.missing", severity="error", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capability": capability})
        raise SystemExit("FAIL: required capabilities missing: " + ", ".join(missing_required))
    flow_root = locate_flow_root(project_root)
    telemetry_rel = rel(flow_root / "runtime" / "telemetry" / f"{assn_id}.ndjson", project_root)
    snapshot_yaml, _snapshot_md = project_context_snapshot_paths(project_root)
    snapshot_sha = "sha256:" + sha256_file(snapshot_yaml)
    snapshot_meta = snapshot.get("snapshot", {}) if isinstance(snapshot.get("snapshot"), dict) else {}
    from processforge_core.work.context import ContextContractError, build_context_fields
    try:
        fields = build_context_fields(project_root, assignment, metadata, snapshot, sys.modules[__name__],
            workplace=(_project_coordination_state.resolve_project_workplace_manifest(project_root).parent if _project_coordination_state.resolve_project_workplace_manifest(project_root) else None))
    except ContextContractError as exc:
        prefix = "workspace access must use public refs: " if exc.code == "private_path_forbidden" else ""
        raise SystemExit("FAIL: " + prefix + exc.code) from exc
    contract = fields
    workspace_access_issues = workspace_access_public_path_issues(contract["workspace_access"])
    if workspace_access_issues:
        raise SystemExit("FAIL: workspace access must use public refs: " + "; ".join(workspace_access_issues))
    missing_sources = _context_contract_inputs.validate_assignment_required_sources(project_root, contract)
    if missing_sources:
        raise SystemExit("FAIL: assignment required sources missing: " + ", ".join(missing_sources))
    overlap_check = validate_assignment_scope_overlaps(project_root, metadata, assignment_path=assignment)
    if _context_contract_inputs.assignment_allows_write_scope_overlap(metadata):
        overlap_check = overlap_allowed_check(overlap_check, "plan.allow_write_scope_overlap")
    if overlap_check["status"] == "fail" and not args.force:
        raise SystemExit("FAIL: assignment write scope overlaps active assignments: " + dump_yaml(overlap_check))
    contract["scope"]["non_overlap"]["overlap_check"] = overlap_check
    assignment_parameter_resolution = {**fields["parameter_resolution_summary"], "resolved_parameters": fields["resolved_parameters"]}
    capsule = {
        "schema_version": 1,
        "capsule": {
            "id": f"{assn_id}-capsule",
            "generated_at": _core_common_clock.now_utc(),
            "assignment_id": assn_id,
            "assignment_path": rel(assignment, project_root),
            "assignment_checksum": sha256_file(assignment),
            "snapshot": rel(snapshot_yaml, project_root),
            "snapshot_checksum": sha256_file(snapshot_yaml),
            "immutable": True,
            "worker_may_rebuild_context": False,
        },
        "context_snapshot": {
            "id": snapshot_meta.get("id", "project-context"),
            "sha256": snapshot_sha,
            "generated_at": snapshot_meta.get("generated_at"),
            "freshness_at_creation": status,
        },
        "project_classification": snapshot.get("project_classification", {}),
        "resolved_resources": snapshot.get("resolved", {}).get("knowledge_resources", []) if isinstance(snapshot.get("resolved"), dict) else [],
        "resolved_parameters": assignment_parameter_resolution["resolved_parameters"],
        "parameter_resolution_summary": {
            "status": assignment_parameter_resolution["status"],
            "sources": assignment_parameter_resolution["sources"],
            "conflicts": assignment_parameter_resolution["conflicts"],
        },
        "effective_specializations": snapshot.get("selected_specializations", []),
        "project_override_summary": snapshot.get("applied_project_overrides", []),
        "active_resource_profile": (snapshot.get("resolved_context", {}) if isinstance(snapshot.get("resolved_context"), dict) else {}).get("active_resource_profile", {}),
        "execution_route_summary": (snapshot.get("resolved_context", {}) if isinstance(snapshot.get("resolved_context"), dict) else {}).get("execution_route", {}),
        "capability_resolution_summary": (snapshot.get("resolved_context", {}) if isinstance(snapshot.get("resolved_context"), dict) else {}).get("capability_resolution", {}),
        "effective_resources": (snapshot.get("resolved_context", {}) if isinstance(snapshot.get("resolved_context"), dict) else {}).get("effective_resources", []),
        "assignment": contract["assignment"],
        "context": {
            "snapshot_id": snapshot_meta.get("id", "project-context"),
            "freshness": status,
            "required_sources": contract["context"]["required_sources"],
            "context_artifacts": contract["context"]["context_artifacts"],
            "selected_specializations": [str(item.get("id")) for item in snapshot.get("selected_specializations", []) if isinstance(item, dict)],
            "applied_project_overrides": [str(item.get("target")) for item in snapshot.get("applied_project_overrides", []) if isinstance(item, dict)],
            "parameter_sources": [str(item.get("id")) for item in assignment_parameter_resolution["sources"] if isinstance(item, dict)],
        },
        "scope": contract["scope"],
        "outputs": contract["outputs"],
        "workspace_access": contract["workspace_access"],
        "agent_model": contract["agent_model"],
        "agent_reasoning_effort": contract["agent_reasoning_effort"],
        "subagent_policy": contract["subagent_policy"],
        "workplace_coordination": _context_contract_inputs.capsule_coordination_block(snapshot, metadata),
        "capabilities": {"required": required_records, "optional": optional_records},
        "telemetry": {"events": telemetry_rel, "event_correlation_id": f"assignment-{assn_id}"},
        "required_sources": contract["context"]["required_sources"],
        "allowed_files": contract["scope"]["allowed_files"],
        "forbidden_files": contract["scope"]["forbidden_files"],
        "required_outputs": contract["outputs"]["required_outputs"],
        "required_capabilities": required_records,
        "optional_capabilities": optional_records,
        "selected_sources": metadata.get("selected_sources", []),
        "event_correlation_id": f"assignment-{assn_id}",
    }
    common_context = {**capsule["context"], **fields["context"]}
    capsule.update(fields)
    capsule["context"] = common_context
    capsule["required_capabilities"] = fields["capabilities"]["required"]
    capsule["optional_capabilities"] = fields["capabilities"]["optional"]
    capsule_dir = flow_root / "contexts" / "assignment-capsules"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = capsule_dir / f"{assn_id}.capsule.yaml"
    try:
        with capsule_path.open("x", encoding="utf-8") as stream:
            stream.write(ensure_trailing_newline(dump_yaml(capsule)))
    except FileExistsError as exc:
        raise SystemExit("FAIL: immutable_context_exists; create_successor_work") from exc
    _process_event_recorder.emit_process_event(project_root, "assignment.started", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"path": rel(assignment, project_root)}, correlation_id=f"assignment-{assn_id}")
    _process_event_recorder.emit_process_event(project_root, "assignment.created", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capsule": rel(capsule_path, project_root)}, correlation_id=f"assignment-{assn_id}")
    _process_event_recorder.emit_process_event(project_root, "artifact.created", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"path": rel(capsule_path, project_root)}, correlation_id=f"assignment-{assn_id}")
    print(f"WROTE: {rel(capsule_path, project_root)}")
    if optional_records:
        missing_optional = [item["id"] for item in optional_records if item.get("status") == "missing"]
        if missing_optional:
            for capability in missing_optional:
                _process_event_recorder.emit_process_event(project_root, "capability.missing", severity="warn", assignment_id_value=assn_id, assignment_path=rel(assignment, project_root), payload={"capability": capability}, correlation_id=f"assignment-{assn_id}")
            print("WARN: optional capabilities missing: " + ", ".join(missing_optional))
    return 0


def command_capsule_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    capsule_path = Path(args.capsule).expanduser()
    if not capsule_path.is_absolute():
        capsule_path = project_root / capsule_path
    capsule = load_yaml_document(capsule_path)
    checks: list[Check] = []
    if not capsule:
        return print_checks([check("FAIL", f"capsule missing or invalid: {capsule_path}")])
    context_snapshot = capsule.get("context_snapshot") if isinstance(capsule.get("context_snapshot"), dict) else {}
    context = capsule.get("context") if isinstance(capsule.get("context"), dict) else {}
    snapshot_id = str(context_snapshot.get("id") or context.get("snapshot_id") or "")
    snapshot_sha = str(context_snapshot.get("sha256") or "")
    snapshot_file = project_context_snapshot_generations_dir(project_root) / f"{snapshot_id}.yaml"
    current_snapshot, _current_md = project_context_snapshot_paths(project_root)
    pinned_exists = snapshot_file.is_file() or current_snapshot.is_file()
    checks.append(check("PASS" if snapshot_id else "FAIL", "capsule pins context snapshot id"))
    checks.append(check("PASS" if snapshot_sha.startswith("sha256:") or capsule.get("capsule", {}).get("snapshot_checksum") else "FAIL", "capsule pins context snapshot checksum"))
    checks.append(check("PASS" if pinned_exists else "FAIL", f"pinned snapshot exists: {snapshot_id or 'missing'}"))
    if snapshot_file.is_file() and snapshot_sha.startswith("sha256:"):
        checks.append(check("PASS" if "sha256:" + sha256_file(snapshot_file) == snapshot_sha else "WARN", "pinned snapshot generation checksum matches"))
    resources = capsule.get("resolved_resources") if isinstance(capsule.get("resolved_resources"), list) else []
    for item in resources:
        if not isinstance(item, dict):
            continue
        uses_latest = any(str(item.get(key) or "").lower() == "latest" for key in ["instance_id", "resolved_version", "resolved_generation"])
        reproducibility = item.get("reproducibility") if isinstance(item.get("reproducibility"), dict) else {}
        allowed_live = bool(item.get("non_reproducible_live_resource")) or reproducibility.get("level") == "non_reproducible"
        checks.append(check("FAIL" if uses_latest and not allowed_live else "PASS", f"resource {item.get('id', 'resource')} avoids unpinned latest"))
    if "execution_contract" in capsule:
        from processforge_core.work.context import validate_execution_contract
        assignment_ref = str(capsule.get("capsule", {}).get("assignment_path") or "")
        assignment_path = project_root / assignment_ref
        metadata = extract_assignment_front_matter(assignment_path) if assignment_path.is_file() else {}
        result = validate_execution_contract(project_root, assignment_path, metadata, capsule, sys.modules[__name__])
        checks.append(check("PASS" if result["status"] == "valid" else "FAIL", "execution contract: " + str(result.get("reason") or result["status"])))
        if result.get("readiness", {}).get("status") == "blocked":
            checks.append(check("WARN", "worker readiness: " + ", ".join(item["code"] for item in result["readiness"]["blockers"])))
    else:
        checks.append(check("WARN", "legacy_contract_incomplete: create_successor_work for restricted execution"))
    return print_checks(checks)












def read_yaml_file(path: Path) -> dict[str, Any]:
    data = load_yaml_document(path)
    error = yaml_error(data)
    if error:
        raise SystemExit(f"FAIL: {path} is invalid YAML: {error}")
    return data




def write_yaml_file_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(ensure_trailing_newline(dump_yaml(data)), encoding="utf-8")
    os.replace(temporary, path)


def write_text_file_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _registry_lock_try_os_lock(fd: int) -> bool:
    """Take a non-blocking advisory lock on an open registry lock file."""

    try:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (ImportError, OSError):
        return False
    return True


def _registry_lock_owner_alive(owner: dict[str, Any]) -> bool | None:
    """Return liveness, or None when ownership cannot be safely assessed."""

    owner_host = str(owner.get("host") or "")
    if owner_host and owner_host != socket.gethostname():
        return None
    try:
        pid = int(owner["pid"])
    except (KeyError, TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            from ctypes import wintypes
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                # ERROR_INVALID_PARAMETER means that the PID is gone. Other
                # failures (notably access denied) remain conservatively live.
                return ctypes.get_last_error() != 87
            exit_code = ctypes.c_ulong()
            try:
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return True
                return exit_code.value == 259  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                shell=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return True
        output = result.stdout or ""
        if str(pid) in output:
            return True
        # A failed or access-denied tasklist query is not proof of death.
        # Only the explicit no-match response permits stale recovery.
        if result.returncode == 0 and "no tasks are running" in output.lower():
            return False
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _registry_lock_stale(owner: dict[str, Any], lock_path: Path, stale_after_seconds: float) -> bool:
    try:
        created_at = str(owner["created_at"])
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        age = time.time() - created
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        try:
            age = time.time() - lock_path.stat().st_mtime
        except OSError:
            return False
    return age > stale_after_seconds


def _registry_lock_read_owner(lock_path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


@contextlib.contextmanager
def registry_file_lock(path: Path, *, timeout_seconds: float = 30.0, stale_after_seconds: float = 300.0) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    # Never unlink this guard: all new writers and stale-owner recovery must
    # lock the same inode, including across Windows close-before-unlink.
    guard_path = path.with_name(f".{path.name}.lock.guard")
    guard_fd = os.open(str(guard_path), os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout_seconds
    owner = {"path": str(path), "pid": os.getpid(), "host": socket.gethostname(),
             "created_at": _core_common_clock.now_utc(), "token": uuid.uuid4().hex}
    acquired = False

    def wait_for_owner() -> None:
        if time.monotonic() >= deadline:
            raise SystemExit(f"FAIL: registry is locked by another writer: {lock_path}")
        time.sleep(0.1)

    try:
        while not _registry_lock_try_os_lock(guard_fd):
            wait_for_owner()
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                existing = _registry_lock_read_owner(lock_path)
                if (existing and _registry_lock_stale(existing, lock_path, stale_after_seconds)
                        and _registry_lock_owner_alive(existing) is False):
                    # The persistent guard serializes reapers with acquisition
                    # and release. Unknown/foreign/live legacy owners stay put.
                    if _registry_lock_read_owner(lock_path) == existing:
                        try:
                            lock_path.unlink()
                        except FileNotFoundError:
                            pass
                        continue
                wait_for_owner()
                continue
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(owner, handle, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except BaseException:
                lock_path.unlink(missing_ok=True)
                raise
            acquired = True
            break
        yield
    finally:
        try:
            if acquired and _registry_lock_read_owner(lock_path) == owner:
                lock_path.unlink(missing_ok=True)
        finally:
            os.close(guard_fd)


def parse_cli_bool(value: Any, *, name: str = "value") -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise SystemExit(f"FAIL: {name} must be true or false")
























def initialize_director_office(workplace_root: Path, coordination: dict[str, Any] | None = None) -> dict[str, Path]:
    paths = _project_coordination_state.director_office_paths(workplace_root, coordination)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    agents = paths["office_path"] / "AGENTS.md"
    if not agents.exists():
        agents.write_text(
            ensure_trailing_newline(
                "# Director Office\n\n"
                "This is the workplace-level ProcessForge Director Office.\n\n"
                "- It coordinates organized projects only.\n"
                "- It does not take over simple projects by default.\n"
                "- Generated inbox, case, history, and runtime data stay outside public release archives.\n"
            ),
            encoding="utf-8",
        )
    manifest = paths["office_path"] / "process-forge.yaml"
    if not manifest.exists():
        _core_common_yaml_io.write_yaml_file(
            manifest,
            {
                "schema_version": 1,
                "process_forge": {
                    "version": "1.0.0",
                    "mode": "file_only",
                    "runner_required": False,
                    "backend_required": False,
                },
                "project": {"id": "director-office", "name": "Director Office", "type": "workplace_process"},
                "coordination": {"mode": "organized"},
                "paths": {"inbox": "inbox", "outbox": "outbox", "cases": "cases", "history": "history", "runtime": "runtime"},
                "policies": {"workspace_scope": True, "simple_projects_opt_in_only": True},
            },
        )
    return paths




def coordination_doctor_checks(project_root: Path, explicit_workplace: str | None = None) -> list[Check]:
    status = _project_coordination_state.effective_project_coordination(project_root, explicit_workplace)
    checks = [
        check("PASS", f"project coordination mode is {status['project_mode']}"),
        check("PASS", f"effective coordination mode is {status['effective_mode']}"),
    ]
    if status["effective_mode"] == "organized":
        checks.append(check("PASS" if status["workplace_director_enabled"] else "FAIL", "organized project has workplace director capability"))
        checks.append(check("PASS" if status["director_office_exists"] else "FAIL", "organized project has Director Office available"))
    else:
        checks.append(check("PASS", "simple project does not require Director Office"))
    return checks




def validate_process_against_project_mode(process_data: dict[str, Any], project_root: Path, *, force: bool = False) -> list[Check]:
    requirements = process_coordination_requirements(process_data)
    coordination = _project_coordination_state.effective_project_coordination(project_root)
    effective_mode = str(coordination.get("effective_mode"))
    mode = str(requirements.get("mode"))
    if mode == "organized_required" and effective_mode != "organized":
        return [
            check(
                "WARN" if force else "FAIL",
                "organized_required process cannot run in effective simple project mode without --force or project migration",
            )
        ]
    if mode == "simple_allowed":
        inbox = requirements.get("director_inbox") if isinstance(requirements.get("director_inbox"), dict) else {}
        if bool(inbox.get("required")):
            return [check("FAIL", "simple_allowed process must not require Director inbox")]
    return [check("PASS", f"process coordination requirements match effective {effective_mode} mode")]




def process_catalog_role(process: dict[str, Any]) -> str:
    return catalog_process_catalog_role(process)


def process_override_declared(process: dict[str, Any], overridden_process_id: str) -> bool:
    override = process.get("process_override") if isinstance(process.get("process_override"), dict) else {}
    return str(override.get("overrides") or "") == overridden_process_id and bool(str(override.get("reason") or "").strip())


def official_pack_manifest_records(root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    from processforge_core.process_catalog.service import official_pack_manifest_records as read_official_packs

    return read_official_packs(root or ROOT)




def workplace_process_pack_registry(workplace_manifest: Path | None) -> dict[str, Any]:
    return _OfficialProcessPackReader(workplace_manifest, distribution_root=ROOT).registry()


def active_process_pack_ids(workplace_manifest: Path | None) -> set[str]:
    return _OfficialProcessPackReader(workplace_manifest, distribution_root=ROOT).active_ids()


def active_official_pack_records(workplace_manifest: Path | None) -> list[tuple[Path, dict[str, Any]]]:
    return _OfficialProcessPackReader(workplace_manifest, distribution_root=ROOT).active_records()




def official_process_definition_refs(
    project_root: Path,
    *,
    include_available: bool = False,
    workplace_manifest: Path | None = None,
) -> list[ProcessDefinitionRef]:
    context = _run_task_consistency_service._process_catalog_context(project_root, workplace_manifest=workplace_manifest)
    return catalog_official_process_definition_refs(
        context,
        include_available=include_available,
    )


def process_root_candidates(project_root: Path) -> list[tuple[Path, str, bool]]:
    return catalog_process_root_candidates(_run_task_consistency_service._process_catalog_context(project_root))


def process_root_yaml_files(root: Path, *, legacy_flat: bool) -> list[Path]:
    return catalog_process_root_yaml_files(root, legacy_flat=legacy_flat)


def process_catalog_entries(
    project_root: Path,
    *,
    strict: bool = False,
    include_available_official: bool = False,
    workplace_manifest: Path | None = None,
) -> list[ProcessDefinitionRef]:
    context = _run_task_consistency_service._process_catalog_context(project_root, workplace_manifest=workplace_manifest)
    return catalog_process_catalog_entries(
        context,
        strict=strict,
        include_available_official=include_available_official,
    )


def resolve_process_definition(
    project_root: Path,
    process_or_path: str,
    *,
    include_available_official: bool = False,
    workplace_manifest: Path | None = None,
) -> ProcessDefinitionRef:
    context = _run_task_consistency_service._process_catalog_context(project_root, workplace_manifest=workplace_manifest)
    return catalog_resolve_process_definition(
        context,
        process_or_path,
        include_available_official=include_available_official,
    )


def require_official_process_active(project_root: Path, process_id: str) -> None:
    catalog_require_official_process_active(_run_task_consistency_service._process_catalog_context(project_root), process_id)










def render_task_index(project_root: Path, run: dict[str, Any]) -> str:
    tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
    lines = [
        f"# Task Index: {run.get('id', 'run')}",
        "",
        f"Run status: `{run.get('status', 'unknown')}`",
        "",
        "| Order | Task | Status | Assignment |",
        "| --- | --- | --- | --- |",
    ]
    for item in sorted([task for task in tasks if isinstance(task, dict)], key=lambda value: int(value.get("order", 0) or 0)):
        lines.append(f"| {item.get('order', '')} | `{item.get('id', '')}` | `{item.get('status', '')}` | `{item.get('assignment', '')}` |")
    if not tasks:
        lines.append("| | No tasks yet | | |")
    return "\n".join(lines) + "\n"






def render_run_summary(project_root: Path, run: dict[str, Any]) -> str:
    run_id = str(run.get("id", "run"))
    lines = [f"# Run Summary: {run.get('title', run_id)}", "", f"- run_id: `{run_id}`", f"- status: `{run.get('status')}`", "", "## Tasks", ""]
    for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
        if isinstance(item, dict):
            task = load_yaml_document(_work_paths.assignment_document(project_root, str(item.get("id", ""))))
            result = task.get("result") if isinstance(task.get("result"), dict) else {}
            lines.append(f"- `{item.get('id')}`: `{item.get('status')}` - {result.get('summary', task.get('title', ''))}")
    if len(lines) == 7:
        lines.append("- No tasks recorded.")
    return "\n".join(lines) + "\n"


def render_run_handoff(project_root: Path, run: dict[str, Any]) -> str:
    run_id = str(run.get("id", "run"))
    summary = _work_paths.summary(project_root, run_id)
    return f"# Run Handoff: {run_id}\n\nStatus: `{run.get('status')}`\n\nSummary: `{rel(summary, project_root)}`\n"


def write_run_artifact_bundle(project_root: Path, run: dict[str, Any], *, include_summary_handoff: bool = False) -> None:
    """Persist one Run state and its derived documents while the caller holds its lock."""
    run_id = str(run.get("id", "run"))
    root = _work_paths.run_root(project_root, run_id)
    if include_summary_handoff:
        write_text_file_atomic(_work_paths.summary(project_root, run_id), render_run_summary(project_root, run))
        write_text_file_atomic(_work_paths.handoff(project_root, run_id), render_run_handoff(project_root, run))
    write_text_file_atomic(root / "task-index.md", render_task_index(project_root, run))
    write_yaml_file_atomic(_work_paths.run_document(project_root, run_id), run)


def write_task_index(project_root: Path, run: dict[str, Any]) -> None:
    run_id = str(run.get("id", "run"))
    write_text_file_atomic(_work_paths.run_root(project_root, run_id) / "task-index.md", render_task_index(project_root, run))


def load_run(project_root: Path, run_id: str) -> dict[str, Any]:
    path = _work_paths.run_document(project_root, run_id)
    if not path.is_file():
        raise SystemExit(f"FAIL: run not found: {safe_id(run_id, 'run')}")
    return read_yaml_file(path)


def save_run(project_root: Path, run: dict[str, Any]) -> None:
    run_id = str(run.get("id", "run"))
    with registry_file_lock(_work_paths.run_document(project_root, run_id)):
        save_run_locked(project_root, run)


def save_run_locked(project_root: Path, run: dict[str, Any], *, include_summary_handoff: bool = False) -> None:
    run["updated_at"] = _core_common_clock.now_utc()
    write_run_artifact_bundle(project_root, run, include_summary_handoff=include_summary_handoff)




def save_task(project_root: Path, task: dict[str, Any]) -> None:
    task["updated_at"] = _core_common_clock.now_utc()
    _core_common_yaml_io.write_yaml_file(_work_paths.assignment_document(project_root, str(task.get("id", "task"))), task)


def update_run_task_status(project_root: Path, run_id: str, task_id: str, status: str) -> None:
    safe_run_id = safe_id(run_id, "run")
    with registry_file_lock(_work_paths.run_document(project_root, safe_run_id)):
        update_run_task_status_locked(project_root, safe_run_id, task_id, status)


def update_run_task_status_locked(project_root: Path, run_id: str, task_id: str, status: str) -> None:
    run = load_run(project_root, run_id)
    changed = False
    for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
        if isinstance(item, dict) and str(item.get("id")) == task_id:
            item["status"] = status
            changed = True
    if changed:
        save_run_locked(project_root, run)








def process_authoring_root(project_root: Path, process_id: str) -> Path:
    return locate_flow_root(project_root) / "authoring" / "processes" / safe_id(process_id, "process")


def process_authoring_paths(project_root: Path, process_id: str) -> dict[str, Path]:
    root = process_authoring_root(project_root, process_id)
    return {
        "root": root,
        "answers": root / "answers.yaml",
        "draft": root / "draft.process.yaml",
        "questions": root / "questions.md",
        "logic_review": root / "logic-review.md",
        "log": root / "authoring-log.md",
        "apply_report": root / "apply-report.md",
    }


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


























def append_authoring_log(paths: dict[str, Path], message: str) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    line = f"- {_core_common_clock.now_utc()}: {message}\n"
    with paths["log"].open("a", encoding="utf-8") as handle:
        handle.write(line)






def command_process_authoring_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    raw_answers = _AnswersDocumentReader().read(Path(args.answers).expanduser().resolve()) if args.answers else {}
    if args.answers and "evolve" not in raw_answers:
        raise SystemExit("FAIL: process authoring answers must include explicit evolve enabled/disabled decision")
    fallback_id = args.id or str((raw_answers.get("process") or {}).get("id") if isinstance(raw_answers.get("process"), dict) else raw_answers.get("id") or "new-process")
    answers = _process_authoring_definition_builder.normalize(raw_answers, fallback_id, args.title or "")
    if args.description:
        answers["process"]["description"] = args.description
    if getattr(args, "scope", None):
        answers["process"]["scope"] = args.scope
    if getattr(args, "kind", None):
        answers["process"]["kind"] = args.kind
    process_id = safe_id(str(answers["process"]["id"]), "new-process")
    draft = _process_authoring_definition_builder.build(answers)
    paths = process_authoring_paths(project_root, process_id)
    planned = [paths["answers"], paths["draft"], paths["questions"], paths["log"]]
    if getattr(args, "dry_run", False):
        print_plan("process-authoring-start dry run", planned, project_root)
        return 0
    _core_common_yaml_io.write_yaml_file(paths["answers"], answers)
    _core_common_yaml_io.write_yaml_file(paths["draft"], draft)
    paths["questions"].write_text(_process_authoring_renderer.questions(answers), encoding="utf-8")
    append_authoring_log(paths, "authoring session started")
    _process_event_recorder.emit_process_event(project_root, "process_authoring.started", process_id=process_id, subject=process_id, payload={"process_id": process_id, "session": rel(paths["root"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    _process_event_recorder.emit_process_event(project_root, "process_authoring.answers.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["answers"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    _process_event_recorder.emit_process_event(project_root, "process_authoring.draft.created", process_id=process_id, subject=process_id, payload={"path": rel(paths["draft"], project_root)}, correlation_id=f"process-authoring-{process_id}")
    print(f"WROTE: {rel(paths['answers'], project_root)}")
    print(f"WROTE: {rel(paths['draft'], project_root)}")
    return 0


def command_process_authoring_review(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    process_id = safe_id(args.process or "", "process")
    paths = process_authoring_paths(project_root, process_id)
    if not paths["draft"].is_file():
        raise SystemExit(f"FAIL: draft not found: {rel(paths['draft'], project_root)}")
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    draft = read_yaml_file(paths["draft"])
    checks = _process_authoring_validation_service.logic(draft, answers)
    paths["logic_review"].write_text(_process_authoring_renderer.logic_review(draft, checks), encoding="utf-8")
    append_authoring_log(paths, "logic review created")
    result = print_checks(checks)
    _process_event_recorder.emit_process_event(project_root, "process_authoring.logic_review.created", process_id=process_id, subject=process_id, severity="error" if result else "info", payload={"path": rel(paths["logic_review"], project_root), "result": "fail" if result else "pass"}, correlation_id=f"process-authoring-{process_id}")
    print(f"WROTE: {rel(paths['logic_review'], project_root)}")
    return result






def write_process_authoring_example(project_root: Path, process: dict[str, Any], answers: dict[str, Any], review_text: str) -> list[Path]:
    process_id = str(process.get("id", "process"))
    example_root = project_root / "examples" / "process-authoring" / process_id
    files = [
        example_root / "README.md",
        example_root / "answers.yaml",
        example_root / "draft.process.yaml",
        example_root / "logic-review.md",
    ]
    readme = "\n".join(
        [
            f"# Process Authoring Example: {process.get('name', title_from_id(process_id))}",
            "",
            "This example shows the authoring inputs, generated process draft, and logic review produced before apply.",
            "",
            "```bash",
            f"python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/{process_id}/answers.yaml --apply",
            f"python bin/pf.py process-doctor --project-root <project-root> --process {process_id}",
            "```",
            "",
        ]
    )
    files[0].parent.mkdir(parents=True, exist_ok=True)
    files[0].write_text(readme, encoding="utf-8")
    _core_common_yaml_io.write_yaml_file(files[1], answers)
    _core_common_yaml_io.write_yaml_file(files[2], process)
    files[3].write_text(review_text, encoding="utf-8")
    dogfood_title = str(process.get("name") or title_from_id(process_id))
    dogfood = {
        example_root / f"process-authoring-{process_id}-report.md": f"# {dogfood_title} Process Authoring Report\n\nStatus: authored and applied through ProcessForge process authoring.\n",
        example_root / f"process-authoring-{process_id}-review.md": f"# {dogfood_title} Process Authoring Review\n\nResult: pass.\n",
        example_root / f"process-authoring-{process_id}-handoff.md": f"# {dogfood_title} Process Authoring Handoff\n\nThe example process is ready for `process-doctor` and task-batch use.\n",
    }
    for path, content in dogfood.items():
        path.write_text(content, encoding="utf-8")
        files.append(path)
    return files






def process_authoring_event_effect(
    project_root: Path,
    process_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> AuthoringEffect:
    return AuthoringEffect(
        label=f"event:{event_type}",
        destination=rel(_run_task_inputs.event_runtime_paths(project_root)[0], project_root),
        role="audit",
        operation="append",
        condition="after_commit",
        kind="process_event",
        payload={
            "project_root": str(project_root),
            "process_id": process_id,
            "event_type": event_type,
            "payload": payload,
            "correlation_id": f"process-authoring-{process_id}",
        },
    )


def build_process_create_plan(
    project_root: Path,
    answers: dict[str, Any],
    *,
    output_root: str,
    allow_core: bool,
    existing_session: bool,
) -> tuple[AuthoringPlan, dict[str, Path]]:
    flow_root = _run_task_inputs.require_flow_root(project_root)
    _update_schema_checks.require(
        answers,
        "process-authoring-answers.schema.json",
        "process authoring answers",
    )
    process_id = safe_id(str((answers.get("process") or {}).get("id") or ""), "process")
    output_root = safe_id(output_root or "user", "user")
    if output_root not in {"user", "custom", "core"}:
        raise SystemExit("FAIL: output process root must be user, custom, or core")
    if output_root == "core" and not allow_core:
        raise SystemExit("FAIL: writing process-authoring output to processes/core requires --core")

    draft = _process_authoring_definition_builder.build(answers)
    draft.setdefault("catalog", {})
    if isinstance(draft["catalog"], dict):
        draft["catalog"].setdefault("role", "canonical")
    checks = _process_authoring_validation_service.logic(draft, answers)
    failures = [item.message for item in checks if item.level == "FAIL"]
    if failures:
        raise SystemExit("FAIL: process authoring logic failed: " + "; ".join(failures))
    review_text = _process_authoring_renderer.logic_review(draft, checks)

    paths = process_authoring_paths(project_root, process_id)
    target_process = contained_resource_path(
        project_root / "processes" / output_root,
        project_root / "processes" / output_root / f"{process_id}.yaml",
        "process",
    )
    target_prompt = contained_resource_path(
        project_root / "prompts",
        project_root / "prompts" / f"{process_id}-agent.md",
        "process prompt",
    )
    target_doc = contained_resource_path(
        project_root / "docs" / "processes",
        project_root / "docs" / "processes" / f"{process_id}.md",
        "process documentation",
    )
    answers.setdefault("output", {})
    if isinstance(answers["output"], dict):
        answers["output"]["process_root"] = output_root
        answers["output"]["path"] = rel(target_process, project_root)

    example_documents = _process_authoring_example_builder.build(project_root, draft, answers, review_text)
    report_lines = [
        f"# Process Authoring Apply Report: {process_id}",
        "",
        "- result: `applied`",
        f"- process: `{rel(target_process, project_root)}`",
        f"- prompt: `{rel(target_prompt, project_root)}`",
        f"- docs: `{rel(target_doc, project_root)}`",
        "",
        "## Example Files",
        "",
    ]
    report_lines.extend(f"- `{rel(path, project_root)}`" for path, _content in example_documents)
    timestamp = _core_common_clock.now_utc()
    if existing_session and paths["log"].is_file():
        prior_log = paths["log"].read_text(encoding="utf-8")
        log_text = ensure_trailing_newline(prior_log) + f"- {timestamp}: authoring session applied\n"
    else:
        log_text = (
            f"- {timestamp}: authoring session created by process-create\n"
            f"- {timestamp}: authoring session applied\n"
        )

    session_documents = [
        (paths["answers"], process_yaml_content(answers)),
        (paths["draft"], process_yaml_content(draft)),
        (paths["questions"], _process_authoring_renderer.questions(answers).encode("utf-8")),
        (paths["logic_review"], review_text.encode("utf-8")),
        (paths["log"], log_text.encode("utf-8")),
        (paths["apply_report"], ("\n".join(report_lines) + "\n").encode("utf-8")),
    ]
    public_documents = [
        (target_process, process_yaml_content(draft)),
        (target_prompt, _process_authoring_renderer.agent_prompt(draft).encode("utf-8")),
        (target_doc, _process_authoring_renderer.document(draft).encode("utf-8")),
        *example_documents,
    ]
    writes = [
        AuthoringWrite(
            destination=path,
            content=content,
            role="entity",
            operation="replace" if existing_session and path in paths.values() else "create",
            schema_name="process-definition.schema.json" if path == target_process else None,
            allow_replace=existing_session and path in paths.values(),
        )
        for path, content in [*session_documents, *public_documents]
    ]

    def validate_process_plan(_plan: AuthoringPlan, staged: dict[Path, Path] | None) -> None:
        candidate_path = staged[target_process] if staged is not None else None
        candidate = load_yaml_document(candidate_path) if candidate_path is not None else draft
        _update_schema_checks.require(
            candidate,
            "process-definition.schema.json",
            f"process {process_id}",
        )
        candidate_checks = _process_authoring_validation_service.logic(candidate, answers)
        candidate_failures = [item.message for item in candidate_checks if item.level == "FAIL"]
        if candidate_failures:
            raise SystemExit("FAIL: staged process validation failed: " + "; ".join(candidate_failures))

    events = [
        (
            "process_authoring.started",
            {"process_id": process_id, "session": rel(paths["root"], project_root)},
        ),
        ("process_authoring.answers.created", {"path": rel(paths["answers"], project_root)}),
        ("process_authoring.draft.created", {"path": rel(paths["draft"], project_root)}),
    ] if not existing_session else []
    events.extend(
        [
            ("process.created", {"path": rel(target_process, project_root)}),
            (
                "process_authoring.applied",
                {
                    "process": rel(target_process, project_root),
                    "prompt": rel(target_prompt, project_root),
                    "docs": rel(target_doc, project_root),
                },
            ),
            ("process_authoring.completed", {"report": rel(paths["apply_report"], project_root)}),
        ]
    )
    effects: list[AuthoringEffect] = []
    for event_type, payload in events:
        effects.append(process_authoring_event_effect(project_root, process_id, event_type, payload))
        effects.append(
            AuthoringEffect(
                label=f"hook-outbox:{event_type}",
                destination=f".pf/runtime/hooks/outbox/<event-id>.<hook-id>.json",
                role="conditional_hook",
                operation="create",
                condition=f"after_commit when hooks.yaml selects {event_type}",
                executable=False,
            )
        )
        effects.append(
            AuthoringEffect(
                label=f"hook-result:{event_type}",
                destination=f".pf/runtime/hooks/results/<delivery-id>.json",
                role="conditional_hook",
                operation="create",
                condition=f"after_commit when hook delivery runs for {event_type}",
                executable=False,
            )
        )
    plan = AuthoringPlan(
        transaction_id=f"process-{process_id}-{uuid.uuid4().hex}",
        command="process-authoring-apply" if existing_session else "process-create",
        runtime_root=flow_root / "runtime",
        authoritative_writes=writes,
        registry_writes=[],
        post_commit_effects=effects,
        validation_callbacks=[validate_process_plan],
    )
    return plan, {
        **paths,
        "target_process": target_process,
        "target_prompt": target_prompt,
        "target_doc": target_doc,
    }


def command_process_authoring_apply(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    mode = _authoring_input_service.mode(args)
    process_id = safe_id(args.process or getattr(args, "id", ""), "process")
    paths = process_authoring_paths(project_root, process_id)
    if not paths["draft"].is_file():
        raise SystemExit(f"FAIL: draft not found: {rel(paths['draft'], project_root)}")
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    output = answers.get("output") if isinstance(answers.get("output"), dict) else {}
    output_root = safe_id(str(getattr(args, "output_root", "") or output.get("process_root") or "user"), "user")
    plan, destinations = build_process_create_plan(
        project_root,
        answers,
        output_root=output_root,
        allow_core=bool(getattr(args, "core", False)),
        existing_session=True,
    )
    if mode == "dry_run":
        render_authoring_dry_run(plan, project_root)
        return 0
    execute_authoring_plan(plan)
    print(f"WROTE: {rel(destinations['target_process'], project_root)}")
    print(f"WROTE: {rel(destinations['target_prompt'], project_root)}")
    print(f"WROTE: {rel(destinations['target_doc'], project_root)}")
    print(f"WROTE: {rel(destinations['apply_report'], project_root)}")
    return 0


def command_process_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    mode = _authoring_input_service.mode(args)
    raw_answers = _AnswersDocumentReader().read(Path(args.answers).expanduser().resolve()) if args.answers else {}
    if args.answers and "evolve" not in raw_answers:
        raise SystemExit("FAIL: process authoring answers must include explicit evolve enabled/disabled decision")
    fallback_id = args.id or str((raw_answers.get("process") or {}).get("id") if isinstance(raw_answers.get("process"), dict) else raw_answers.get("id") or "new-process")
    answers = _process_authoring_definition_builder.normalize(raw_answers, fallback_id, args.title or "")
    process_id = safe_id(str(answers["process"]["id"]), "new-process")
    output = answers.get("output") if isinstance(answers.get("output"), dict) else {}
    output_root = safe_id(str(getattr(args, "output_root", "") or output.get("process_root") or "user"), "user")
    answers.setdefault("output", {})
    if isinstance(answers["output"], dict):
        answers["output"]["process_root"] = output_root
    plan, destinations = build_process_create_plan(
        project_root,
        answers,
        output_root=output_root,
        allow_core=bool(getattr(args, "core", False)),
        existing_session=False,
    )
    if mode == "dry_run":
        render_authoring_dry_run(plan, project_root)
        return 0
    execute_authoring_plan(plan)
    print(f"WROTE: {rel(destinations['target_process'], project_root)}")
    print(f"WROTE: {rel(destinations['target_prompt'], project_root)}")
    print(f"WROTE: {rel(destinations['target_doc'], project_root)}")
    print(f"WROTE: {rel(destinations['apply_report'], project_root)}")
    return 0


def process_definition_path(project_root: Path, process_or_path: str) -> Path:
    return resolve_process_definition(project_root, process_or_path).path




















def command_builtin_process_catalog_doctor(args: argparse.Namespace) -> int:
    root_arg = getattr(args, "root", None) or getattr(args, "project_root", None) or "."
    root = Path(root_arg).expanduser().resolve()
    _run_task_inputs.require_flow_root(root)
    report = _builtin_process_catalog_audit_service.report(root, public=bool(getattr(args, "public", False)))
    failed = [item for item in report["checks"] if item["level"] == "FAIL"]
    if getattr(args, "write_report", None):
        target = Path(args.write_report).expanduser()
        if not target.is_absolute():
            target = root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"PROCESS CATALOG: {'FAIL' if failed else 'PASS'}")
        summary = report["summary"]
        print(f"public_stable: {summary['public_stable']} pass, {len(failed)} fail")
        print(f"experimental: {summary['public_experimental']} warn")
        print(f"internal: {summary['internal']} skipped")
        print(f"warnings: {summary['warn']}")
        for item in report["checks"]:
            if item["level"] != "PASS":
                print(f"{item['level']}: {item['message']}")
    return 1 if failed else 0


def command_process_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    resolved = resolve_process_definition(project_root, args.process)
    path = resolved.path
    process = resolved.process
    companion_root = resolved.root if resolved.origin == "official" else project_root
    checks: list[Check] = []
    _update_schema_checks.append(
        checks,
        process,
        "process-definition.schema.json",
        f"process {args.process}",
    )
    checks.extend(_process_authoring_validation_service.files(project_root, process, path, companion_root=companion_root))
    checks.extend(
        _process_contract_validation_service.validate(
            project_root,
            process,
            path,
            strict=getattr(args, "contract_only", False),
            companion_root=companion_root,
        )
    )
    checks.extend(validate_process_against_project_mode(process, project_root, force=getattr(args, "force", False)))
    checks.extend(check("WARN", warning) for warning in resolved.warnings)
    result = print_checks(checks)
    return result


def iter_process_definitions(project_root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    return [(entry.process_id, entry.path, entry.process) for entry in process_catalog_entries(project_root)]


def public_process_origin(origin: str) -> str:
    return {
        "core": "kernel",
        "user": "workspace",
        "custom": "project",
        "legacy_flat": "project",
    }.get(origin, origin)


def command_process_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    workplace_manifest = None
    if getattr(args, "workplace", None):
        workplace_manifest = _project_coordination_state.workplace_manifest_path_from_root(
            Path(args.workplace).expanduser().resolve()
        )
    show_available = bool(getattr(args, "available", False) or getattr(args, "all", False))
    entries = process_catalog_entries(
        project_root,
        include_available_official=show_available,
        workplace_manifest=workplace_manifest,
    )
    origin_filter = str(getattr(args, "origin", "") or "")
    role_filter = str(getattr(args, "role", "") or "")
    status_filter = str(getattr(args, "status", "") or "")
    show_all = bool(getattr(args, "all", False))
    if origin_filter:
        origin_filter = {
            "kernel": "core",
            "workspace": "user",
            "project": "custom",
        }.get(origin_filter, origin_filter)
        entries = [entry for entry in entries if entry.origin == origin_filter]
    if bool(getattr(args, "active", False)):
        entries = [entry for entry in entries if entry.active]
    if bool(getattr(args, "available", False)):
        entries = [entry for entry in entries if entry.available]
    if role_filter:
        entries = [entry for entry in entries if entry.catalog_role == role_filter]
    if status_filter:
        entries = [entry for entry in entries if str(entry.process.get("status", "")) == status_filter]
    if not show_all:
        entries = [
            entry
            for entry in entries
            if entry.origin != "legacy_flat"
            and entry.catalog_role not in {"internal", "helper", "legacy_alias"}
            and str(entry.process.get("status", "")) not in {"internal", "archived", "deprecated"}
        ]
    if not entries:
        print("No processes found.")
        return 0
    print("id\tstatus\torigin\trole\tversion\tname\tpack_id\tactive\tavailable\tproduction_ready\troot\tpath")
    for entry in entries:
        data = entry.process
        print(
            f"{entry.process_id}\t{data.get('status', 'unknown')}\t{public_process_origin(entry.origin)}\t{entry.catalog_role}\t"
            f"{data.get('version', '')}\t{data.get('name', '')}\t{entry.pack_id}\t"
            f"{str(entry.active).lower()}\t{str(entry.available).lower()}\t"
            f"{str(entry.production_ready).lower()}\t{rel(entry.root, project_root)}\t{rel(entry.path, project_root)}"
        )
        for warning in entry.warnings:
            print(f"WARN: {warning}", file=sys.stderr)
    return 0


def command_process_describe(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    workplace_manifest = None
    if getattr(args, "workplace", None):
        workplace_manifest = _project_coordination_state.workplace_manifest_path_from_root(
            Path(args.workplace).expanduser().resolve()
        )
    resolved = resolve_process_definition(
        project_root,
        args.process,
        include_available_official=True,
        workplace_manifest=workplace_manifest,
    )
    path = resolved.path
    data = resolved.process
    print(f"PROCESS: {data.get('id', path.stem)}")
    print(f"NAME: {data.get('name', '')}")
    print(f"STATUS: {data.get('status', '')}")
    print(f"VERSION: {data.get('version', '')}")
    print(f"ORIGIN: {public_process_origin(resolved.origin)}")
    print(f"PACK_ID: {resolved.pack_id}")
    print(f"ACTIVE: {str(resolved.active).lower()}")
    print(f"AVAILABLE: {str(resolved.available).lower()}")
    print(f"PRODUCTION_READY: {str(resolved.production_ready).lower()}")
    print(f"ROLE: {resolved.catalog_role}")
    print(f"ROOT: {rel(resolved.root, project_root)}")
    print(f"PATH: {rel(path, project_root)}")
    print("STAGES:")
    for stage in as_list(data.get("stages")):
        if isinstance(stage, dict):
            print(f"- {stage.get('id')}: {stage.get('title', '')}")
    print("ROLES:")
    for role in as_list(data.get("roles")):
        if isinstance(role, dict):
            print(f"- {role.get('id')}: {role.get('title', '')}")
    print("ARTIFACTS:")
    for artifact in as_list(data.get("artifact_definitions")):
        if isinstance(artifact, dict):
            print(f"- {artifact.get('id')}: {artifact.get('title', '')}")
    print("GATES:")
    for gate_item in as_list(data.get("gates")):
        if isinstance(gate_item, dict):
            print(f"- {gate_item.get('id')}: {gate_item.get('description', '')}")
    return 0


def command_pack_list(args: argparse.Namespace) -> int:
    workplace_manifest: Path | None = None
    if getattr(args, "workplace", None):
        workplace_manifest = _project_coordination_state.workplace_manifest_path_from_root(
            Path(args.workplace).expanduser().resolve()
        )
    elif getattr(args, "project_root", None):
        project_root = Path(args.project_root).expanduser().resolve()
        workplace_manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root)
    active_ids = active_process_pack_ids(workplace_manifest)
    records = official_pack_manifest_records()
    if bool(getattr(args, "active", False)):
        records = [
            (path, manifest)
            for path, manifest in records
            if str(manifest.get("id") or "") in active_ids
        ]
    print("id\torigin\ttier\tstatus\tactive\tavailable\tproduction_ready\tversion\tpath")
    for path, manifest in records:
        pack_id = str(manifest.get("id") or "")
        activation = manifest.get("activation") if isinstance(manifest.get("activation"), dict) else {}
        print(
            f"{pack_id}\t{manifest.get('origin', '')}\t{manifest.get('tier', '')}\t"
            f"{manifest.get('status', '')}\t{str(pack_id in active_ids).lower()}\t"
            f"{str(bool(activation.get('available_by_default', False))).lower()}\t"
            f"{str(bool(manifest.get('production_ready', False))).lower()}\t"
            f"{manifest.get('version', '')}\t{rel(path, ROOT)}"
        )
    return 0


def command_pack_activate(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    workplace_manifest = _project_coordination_state.workplace_manifest_path_from_root(workplace)
    if not workplace_manifest.is_file():
        raise SystemExit(f"FAIL: workplace manifest not found: {workplace_manifest}")
    pack_id = str(args.id)
    manifests = {
        str(manifest.get("id") or ""): (path, manifest)
        for path, manifest in official_pack_manifest_records()
    }
    if pack_id not in manifests:
        raise SystemExit(f"FAIL: official process pack not found: {pack_id}")
    registry_path = workplace / "registries" / "process-packs.yaml"
    if not args.apply:
        print(f"PLAN: activate {pack_id} in {registry_path}")
        return 0
    with registry_file_lock(registry_path):
        registry = load_yaml_document(registry_path) if registry_path.is_file() else {}
        if not isinstance(registry, dict) or yaml_error(registry):
            registry = {}
        entries = [entry for entry in as_list(registry.get("process_packs")) if isinstance(entry, dict)]
        entries = [entry for entry in entries if str(entry.get("id") or "") != pack_id]
        manifest = manifests[pack_id][1]
        entries.append(
            {
                "id": pack_id,
                "origin": "official",
                "status": "active",
                "version": str(manifest.get("version") or ""),
            }
        )
        document = {
            "schema_version": 1,
            "profile": str(registry.get("profile") or "custom"),
            "process_packs": sorted(entries, key=lambda item: str(item.get("id") or "")),
        }
        write_yaml_file_atomic(registry_path, document)
    _workplace_resource_events.append_workplace_event(
        workplace,
        "process.pack.activated",
        payload={"pack_id": pack_id, "origin": "official"},
    )
    print(f"ACTIVATED: {pack_id}")
    print(f"REGISTRY: {rel(registry_path, workplace)}")
    return 0


def process_layout_checks(root: Path) -> list[Check]:
    checks: list[Check] = []
    process_root = root / "processes"
    core_root = process_root / "core"
    user_root = process_root / "user"
    custom_root = process_root / "custom"
    checks.append(check("PASS" if core_root.is_dir() else "FAIL", "processes/core exists"))
    checks.append(check("PASS" if user_root.is_dir() else "FAIL", "processes/user exists"))
    checks.append(check("PASS" if custom_root.is_dir() else "FAIL", "processes/custom exists"))
    flat_files = sorted([*process_root.glob("*.yaml"), *process_root.glob("*.yml")]) if process_root.is_dir() else []
    checks.append(check("PASS" if not flat_files else "WARN", f"legacy flat process files: {len(flat_files)}"))
    for path in flat_files[:20]:
        checks.append(check("WARN", f"legacy flat process path detected: {rel(path, root)}"))
    entries = process_catalog_entries(root, strict=True)
    core_entries = [entry for entry in entries if entry.origin == "core"]
    checks.append(check("PASS" if core_entries else "FAIL", "core processes resolvable"))
    seen_paths = {entry.path.resolve() for entry in entries}
    for path in process_root_yaml_files(core_root, legacy_flat=False):
        checks.append(check("PASS" if path.resolve() in seen_paths else "FAIL", f"core process resolves: {rel(path, root)}"))
    for entry in entries:
        for warning in entry.warnings:
            level = "FAIL" if warning.startswith("STRICT: duplicate") else "WARN"
            checks.append(check(level, warning.removeprefix("STRICT: ")))
    private_user = [path for subdir in [user_root, custom_root] if subdir.is_dir() for path in subdir.rglob("*.y*ml") if path.is_file()]
    checks.append(check("PASS" if not private_user else "WARN", f"user/custom process definitions in distribution root: {len(private_user)}"))
    return checks


def command_process_layout_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    _run_task_inputs.require_flow_root(root)
    result = print_checks(process_layout_checks(root))
    return result


def command_process_layout_migrate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    _run_task_inputs.require_flow_root(root)
    process_root = root / "processes"
    target_root = process_root / ("custom" if getattr(args, "custom", False) else "user")
    built_in_target = process_root / "core"
    flat_files = sorted([*process_root.glob("*.yaml"), *process_root.glob("*.yml")]) if process_root.is_dir() else []
    planned: list[tuple[Path, Path]] = []
    package_ids: set[str] = set()
    for package in _builtin_process_catalog_audit_service.package_index(root).values():
        package_ids.update(package["processes"])
    for path in flat_files:
        data = load_yaml_document(path)
        process_id = str(data.get("id") or path.stem) if isinstance(data, dict) else path.stem
        destination_root = built_in_target if process_id in package_ids else target_root
        planned.append((path, destination_root / path.name))
    if not planned:
        print("PASS: no legacy flat process files found")
        return 0
    failures = [target for _source, target in planned if target.exists()]
    if failures:
        for target in failures:
            print(f"FAIL: target exists: {rel(target, root)}")
        return 1
    for source, target in planned:
        print(f"{'MOVE' if getattr(args, 'apply', False) else 'DRY-RUN'}: {rel(source, root)} -> {rel(target, root)}")
    if not getattr(args, "apply", False):
        return 0
    for source, target in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    return 0


def evolve_artifact_root(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "artifacts" / "evolve"


def learning_root(workplace: Path) -> Path:
    return _project_coordination_state.normalize_workplace_path(workplace) / "learning"


def ensure_learning_layout(workplace: Path) -> Path:
    root = learning_root(workplace)
    for subdir in ["inbox", "bundles"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    index = root / "index.yaml"
    if not index.is_file():
        _core_common_yaml_io.write_yaml_file(index, {"schema_version": 1, "kind": "processforge.learning_queue", "candidates": []})
    exports = root / "exports.ndjson"
    exports.parent.mkdir(parents=True, exist_ok=True)
    if not exports.is_file():
        exports.write_text("", encoding="utf-8")
    return root






























def queue_candidate(workplace: Path, source: Path, *, status: str = "queued") -> Path:
    root = ensure_learning_layout(workplace)
    data = read_yaml_file(source)
    failures = [item.message for item in _knowledge_candidate_validation_service.validate(data) if item.level == "FAIL"]
    if failures:
        raise SystemExit("FAIL: invalid knowledge candidate: " + "; ".join(failures))
    candidate_id = _knowledge_candidate_targeting_policy.id_from_data(data, source.stem)
    data["id"] = candidate_id
    state = data.get("status") if isinstance(data.get("status"), dict) else {}
    state["local"] = status
    data["status"] = state
    target = root / "inbox" / f"{candidate_id}.yaml"
    _core_common_yaml_io.write_yaml_file(target, data)
    index_path = root / "index.yaml"
    index = read_yaml_file(index_path) if index_path.is_file() else {"schema_version": 1, "kind": "processforge.learning_queue", "candidates": []}
    candidates = [item for item in as_list(index.get("candidates")) if isinstance(item, dict) and item.get("id") != candidate_id]
    candidates.append(
        {
            "id": candidate_id,
            "target": _knowledge_candidate_targeting_policy.target(data),
            "target_id": _knowledge_candidate_targeting_policy.target_id(data),
            "target_type": _knowledge_candidate_targeting_policy.target_type(data),
            "routing": data.get("routing") if isinstance(data.get("routing"), dict) else {},
            "applicability_scope": str((data.get("applicability") or {}).get("scope") or "") if isinstance(data.get("applicability"), dict) else "",
            "category": data.get("category", "generic"),
            "sensitivity": (data.get("privacy") or {}).get("sensitivity", data.get("sensitivity", "internal")) if isinstance(data.get("privacy"), dict) else data.get("sensitivity", "internal"),
            "status": status,
            "path": f"inbox/{candidate_id}.yaml",
            "queued_at": _core_common_clock.now_utc(),
        }
    )
    index["candidates"] = sorted(candidates, key=lambda item: str(item.get("id")))
    _core_common_yaml_io.write_yaml_file(index_path, index)
    return target


def command_evolve_candidate_sanitize(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"FAIL: candidate file not found: {path}")
    data = read_yaml_file(path)
    sanitized_data = _evolve_privacy_policy.value(data)
    if not isinstance(sanitized_data, dict):
        sanitized_data = data
    privacy = sanitized_data.get("privacy") if isinstance(sanitized_data.get("privacy"), dict) else {}
    privacy["sanitized"] = True
    privacy["sanitized_at"] = _core_common_clock.now_utc()
    sanitized_data["privacy"] = privacy
    target = path.with_name(path.stem + ".sanitized" + path.suffix)
    _core_common_yaml_io.write_yaml_file(target, sanitized_data)
    print(f"WROTE: {target}")
    return 0


def load_yaml_document_from_text(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        return parse_simple_yaml(text)


def command_evolve_candidate_create(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    source = Path(args.from_file).expanduser()
    if not source.is_absolute():
        source = Path(args.project_root).expanduser().resolve() / source
    target = queue_candidate(workplace, source)
    print(f"QUEUED: {rel(target, _project_coordination_state.normalize_workplace_path(workplace))}")
    return 0


def command_evolve_candidate_list(args: argparse.Namespace) -> int:
    root = ensure_learning_layout(Path(args.workplace).expanduser().resolve())
    index = read_yaml_file(root / "index.yaml")
    for item in as_list(index.get("candidates")):
        if isinstance(item, dict):
            print(f"{item.get('id')}\\t{item.get('target')}\\t{item.get('category')}\\t{item.get('status')}")
    return 0


def command_evolve_candidate_export(args: argparse.Namespace) -> int:
    workplace = Path(args.workplace).expanduser().resolve()
    root = ensure_learning_layout(workplace)
    target_package = str(args.target)
    selected: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / "inbox").glob("*.yaml")):
        data = read_yaml_file(path)
        if not _knowledge_candidate_targeting_policy.destination_matches(data, target_package):
            continue
        findings = _evolve_privacy_policy.findings(dump_yaml(data))
        if findings:
            raise SystemExit("FAIL: candidate export blocked by sanitizer findings in " + path.name + ": " + ", ".join(findings))
        selected.append((path, data))
    if not selected:
        raise SystemExit("FAIL: no exportable candidates for target " + target_package)
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = root / "bundles" / output
    output.parent.mkdir(parents=True, exist_ok=True)
    bundle_id = safe_id(output.stem or f"learning-export-{int(time.time())}", "learning-export")
    manifest = {
        "schema_version": 1,
        "kind": "processforge.learning_export",
        "bundle_id": bundle_id,
        "target": target_package,
        "exported_at": _core_common_clock.now_utc(),
        "candidate_count": len(selected),
        "candidates": [_knowledge_candidate_targeting_policy.id_from_data(data, path.stem) for path, data in selected],
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.yaml", ensure_trailing_newline(dump_yaml(manifest)))
        archive.writestr("evidence/evidence-digest.md", "# Evidence Digest\n\n- Sanitized candidate summaries only.\n")
        for path, data in selected:
            data = dict(data)
            state = data.get("status") if isinstance(data.get("status"), dict) else {}
            state["local"] = "exported"
            state.setdefault("hub", None)
            data["status"] = state
            archive.writestr(f"candidates/{_knowledge_candidate_targeting_policy.id_from_data(data, path.stem)}.yaml", ensure_trailing_newline(dump_yaml(data)))
    bundle_copy = root / "bundles" / output.name
    if output.resolve() != bundle_copy.resolve():
        shutil.copyfile(output, bundle_copy)
    with (root / "exports.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"bundle": output.name, "target": target_package, "exported_at": _core_common_clock.now_utc(), "count": len(selected)}, sort_keys=True) + "\n")
    print(f"EXPORTED: {output}")
    return 0


def command_evolve_run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    process_id = str(getattr(args, "process", None) or "task-batch-execution")
    process = read_yaml_file(process_definition_path(project_root, process_id))
    evolve = process.get("evolve") if isinstance(process.get("evolve"), dict) else {}
    checks = _process_evolution_policy.validate_block(process_id, evolve, hard=True)
    failures = [item.message for item in checks if item.level == "FAIL"]
    if failures:
        raise SystemExit("FAIL: process evolve declaration invalid: " + "; ".join(failures))
    root = evolve_artifact_root(project_root)
    (root / "knowledge-candidates").mkdir(parents=True, exist_ok=True)
    (root / "instruction-update-proposals").mkdir(parents=True, exist_ok=True)
    (root / "process-improvement-proposals").mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "kind": "processforge.evolution_report",
        "id": safe_id(f"evolution-{getattr(args, 'run', '') or 'run'}", "evolution-report"),
        "process_id": process_id,
        "run_id": str(getattr(args, "run", "") or ""),
        "generated_at": _core_common_clock.now_utc(),
        "status": "created",
        "evolve": evolve,
        "candidates": [],
    }
    for candidate in getattr(args, "candidate_file", []) or []:
        source = Path(candidate).expanduser()
        if not source.is_absolute():
            source = project_root / source
        report["candidates"].append(_knowledge_candidate_targeting_policy.id_from_data(read_yaml_file(source), source.stem))
        if getattr(args, "workplace", None):
            queue_candidate(Path(args.workplace).expanduser().resolve(), source)
    _core_common_yaml_io.write_yaml_file(root / "evolution-report.yaml", report)
    (root / "evolution-report.md").write_text(
        "\n".join(
            [
                f"# Evolution Report: {process_id}",
                "",
                f"- run_id: `{report['run_id']}`",
                f"- mode: `{evolve.get('mode')}`",
                f"- timing: `{evolve.get('timing')}`",
                f"- candidates: `{len(report['candidates'])}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"WROTE: {rel(root / 'evolution-report.md', project_root)}")
    print(f"WROTE: {rel(root / 'evolution-report.yaml', project_root)}")
    return 0


def ensure_hub_layout(hub: Path) -> Path:
    for subdir in ["inbox/imports", "candidates", "packages", "updates"]:
        (hub / subdir).mkdir(parents=True, exist_ok=True)
    if not (hub / "hub.yaml").is_file():
        _core_common_yaml_io.write_yaml_file(hub / "hub.yaml", {"schema_version": 1, "kind": "processforge.knowledge_hub", "created_at": _core_common_clock.now_utc()})
    if not (hub / "candidates" / "index.yaml").is_file():
        _core_common_yaml_io.write_yaml_file(hub / "candidates" / "index.yaml", {"schema_version": 1, "kind": "processforge.hub_candidate_index", "candidates": []})
    return hub


def command_knowledge_hub_init(args: argparse.Namespace) -> int:
    hub = Path(args.hub).expanduser().resolve()
    if not getattr(args, "apply", False):
        print_plan("knowledge-hub-init dry run", [hub / "hub.yaml", hub / "candidates" / "index.yaml"], hub.parent)
        return 0
    ensure_hub_layout(hub)
    print(f"WROTE: {hub / 'hub.yaml'}")
    return 0


def command_knowledge_hub_import(args: argparse.Namespace) -> int:
    hub = ensure_hub_layout(Path(args.hub).expanduser().resolve())
    bundle = Path(args.bundle).expanduser().resolve()
    if not bundle.is_file():
        raise SystemExit(f"FAIL: bundle not found: {bundle}")
    if not getattr(args, "apply", False):
        print(f"WOULD IMPORT: {bundle}")
        return 0
    bundle_id = safe_id(bundle.stem, "learning-export")
    import_root = hub / "inbox" / "imports" / bundle_id
    if import_root.exists():
        shutil.rmtree(import_root)
    import_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(import_root)
    index_path = hub / "candidates" / "index.yaml"
    index = read_yaml_file(index_path)
    rows = [item for item in as_list(index.get("candidates")) if isinstance(item, dict)]
    for candidate in sorted((import_root / "candidates").glob("*.yaml")):
        data = read_yaml_file(candidate)
        failures = [item.message for item in _knowledge_candidate_validation_service.validate(data) if item.level == "FAIL"]
        if failures:
            raise SystemExit("FAIL: imported candidate invalid: " + "; ".join(failures))
        candidate_id = _knowledge_candidate_targeting_policy.id_from_data(data, candidate.stem)
        shutil.copyfile(candidate, hub / "candidates" / f"{candidate_id}.yaml")
        rows = [item for item in rows if item.get("id") != candidate_id]
        rows.append(
            {
                "id": candidate_id,
                "target": _knowledge_candidate_targeting_policy.target(data),
                "target_id": _knowledge_candidate_targeting_policy.target_id(data),
                "target_type": _knowledge_candidate_targeting_policy.target_type(data),
                "routing": data.get("routing") if isinstance(data.get("routing"), dict) else {},
                "applicability_scope": str((data.get("applicability") or {}).get("scope") or "") if isinstance(data.get("applicability"), dict) else "",
                "generalization": data.get("generalization") if isinstance(data.get("generalization"), dict) else {},
                "category": data.get("category", "generic"),
                "status": "imported",
                "path": f"candidates/{candidate_id}.yaml",
            }
        )
    index["candidates"] = sorted(rows, key=lambda item: str(item.get("id")))
    _core_common_yaml_io.write_yaml_file(index_path, index)
    print(f"IMPORTED: {bundle_id}")
    return 0


def command_knowledge_package_build_from_candidates(args: argparse.Namespace) -> int:
    package_id = validate_resource_id(str(args.package), "knowledge package")
    hub = ensure_hub_layout(Path(args.hub).expanduser().resolve())
    version = str(args.version)
    package_root = contained_resource_path(
        hub / "packages",
        hub / "packages" / package_id,
        "knowledge package",
    )
    candidates = [read_yaml_file(path) for path in sorted((hub / "candidates").glob("*.yaml"))]
    candidates = [item for item in candidates if _knowledge_candidate_targeting_policy.destination_matches(item, package_id)]
    if not candidates:
        raise SystemExit("FAIL: no candidates available for package " + package_id)
    if not getattr(args, "apply", False):
        print_plan(
            "knowledge-package-build-from-candidates dry run",
            [package_root / "resources" / "candidate-notes.md", package_root / "resources" / "incoming-learnings.md", package_root / "changelog.md"],
            hub,
        )
        return 0
    package_manifest = {
        "schema_version": 1,
        "id": package_id,
        "name": package_id,
        "version": version,
        "kind": "mixed",
        "scope": "workplace",
    }
    _update_schema_checks.require(
        package_manifest,
        "package-manifest.schema.json",
        f"knowledge package {package_id}",
    )
    (package_root / "resources").mkdir(parents=True, exist_ok=True)
    curated_candidates = [item for item in candidates if _knowledge_candidate_targeting_policy.ready_for_curated_package(item)]
    incoming_candidates = [item for item in candidates if not _knowledge_candidate_targeting_policy.ready_for_curated_package(item)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in curated_candidates:
        grouped.setdefault(str(item.get("category") or "generic"), []).append(item)
    notes = ["# Candidate Notes", "", "Reviewed candidates staged for package curation.", ""]
    if grouped:
        for category in sorted(grouped):
            notes.extend([f"## {category}", ""])
            for item in grouped[category]:
                notes.append(f"- `{_knowledge_candidate_targeting_policy.id_from_data(item)}`: {item.get('summary', '')}")
            notes.append("")
    else:
        notes.extend(["No curated candidates were approved for this package build.", ""])
    resources = [{"id": "candidate-notes", "path": "resources/candidate-notes.md", "type": "markdown"}]
    if incoming_candidates:
        incoming = ["# Incoming Learnings", "", "## Unreviewed parent-platform candidates", ""]
        for item in incoming_candidates:
            promotion = item.get("promotion") if isinstance(item.get("promotion"), dict) else {}
            incoming.append(f"- `{_knowledge_candidate_targeting_policy.id_from_data(item)}`: {item.get('summary', '')} (promotion: {promotion.get('status', 'not_requested')})")
        notes.append("")
        (package_root / "resources" / "incoming-learnings.md").write_text("\n".join(incoming), encoding="utf-8")
        resources.append({"id": "incoming-learnings", "path": "resources/incoming-learnings.md", "type": "markdown"})
    (package_root / "resources" / "candidate-notes.md").write_text("\n".join(notes), encoding="utf-8")
    _core_common_yaml_io.write_yaml_file(package_root / "resources" / "index.yaml", {"schema_version": 1, "resources": resources})
    _core_common_yaml_io.write_yaml_file(package_root / "package.yaml", package_manifest)
    changelog_items = ["- Added reviewed learning candidates to `resources/candidate-notes.md`."]
    if incoming_candidates:
        changelog_items.append("- Staged unreviewed parent-platform candidates in `resources/incoming-learnings.md`.")
    (package_root / "changelog.md").write_text(f"# Changelog\n\n## {version}\n\n" + "\n".join(changelog_items) + "\n", encoding="utf-8")
    (package_root / f"release-plan-{version}.md").write_text(f"# Release Plan {version}\n\n- Build package from imported candidates.\n- Publish through local update manifest.\n", encoding="utf-8")
    print(f"BUILT: {package_root}")
    return 0


def command_knowledge_package_release(args: argparse.Namespace) -> int:
    package_id = validate_resource_id(str(args.package), "knowledge package")
    hub = ensure_hub_layout(Path(args.hub).expanduser().resolve())
    version = str(args.version)
    package_root = contained_resource_path(
        hub / "packages",
        hub / "packages" / package_id,
        "knowledge package",
    )
    if not package_root.is_dir():
        raise SystemExit("FAIL: package not built: " + package_id)
    package_manifest_path = package_root / "package.yaml"
    if not package_manifest_path.is_file():
        raise SystemExit("FAIL: package manifest missing: " + str(package_manifest_path))
    package = read_yaml_file(package_manifest_path)
    _update_schema_checks.require(
        package,
        "package-manifest.schema.json",
        f"knowledge package {package_id}",
    )
    if str(package.get("id") or "") != package_id:
        raise SystemExit(
            f"FAIL: package manifest id {package.get('id')!r} does not match requested package {package_id!r}"
        )
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = hub / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file() and "releases" not in path.relative_to(package_root).parts:
                archive.write(path, path.relative_to(package_root).as_posix())
    digest = sha256_file(output)
    manifest = {
        "schema_version": 1,
        "kind": "processforge.update_manifest",
        "subject": {"id": package_id, "type": "knowledge_package", "name": package_id},
        "channels": {
            "stable": {
                "latest": version,
                "versions": [
                    {
                        "version": version,
                        "released_at": _core_common_clock.now_utc(),
                        "download_url": "file:///" + output.as_posix(),
                        "sha256": digest,
                        "changelog_url": "file:///" + (package_root / "changelog.md").as_posix(),
                        "breaking": False,
                        "migration_required": False,
                        "update_policy": {"install_path": f"packages/{package_id}"},
                    }
                ],
            }
        },
    }
    update_manifest = hub / "updates" / f"{package_id}.update.json"
    update_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _core_common_yaml_io.write_yaml_file(
        hub / "updates" / "processforge-update-index.yaml",
        {"schema_version": 1, "updates": [{"id": package_id, "manifest": rel(update_manifest, hub), "version": version, "artifact": rel(output, hub)}]},
    )
    package["version"] = version
    package["update_sites"] = [
        {
            "id": f"{safe_id(package_id)}-local",
            "enabled": True,
            "manifest_url": "file:///" + update_manifest.as_posix(),
            "changelog_url": "file:///" + (package_root / "changelog.md").as_posix(),
            "channel": "stable",
            "priority": 10,
            "trust": {"require_https": False, "require_sha256": True, "allow_unsigned": True, "signature_required": False},
            "policy": {"allow_stage": True, "allow_apply": True, "backup_before_apply": True, "install_path": f"packages/{package_id}"},
        }
    ]
    _update_schema_checks.require(
        package,
        "package-manifest.schema.json",
        f"released knowledge package {package_id}",
    )
    _core_common_yaml_io.write_yaml_file(package_manifest_path, package)
    print(f"RELEASED: {output}")
    print(f"MANIFEST: {update_manifest}")
    return 0




def process_backfill_root(project_root: Path, process_id: str) -> Path:
    return locate_flow_root(project_root) / "authoring" / "backfill" / "processes" / safe_id(process_id, "process")


def process_backfill_paths(project_root: Path, process_id: str) -> dict[str, Path]:
    root = process_backfill_root(project_root, process_id)
    return {
        "root": root,
        "answers": root / "answers.yaml",
        "draft": root / "draft.process.yaml",
        "source": root / "source.process.yaml",
        "semantic_map": root / "semantic-map.yaml",
        "unsupported": root / "unsupported-fields.yaml",
        "import_report": root / "import-report.md",
    }










def command_process_authoring_import(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    if args.process_file:
        process_path = Path(args.process_file).expanduser()
        process_path = process_path if process_path.is_absolute() else project_root / process_path
        if not process_path.is_file():
            raise SystemExit(f"FAIL: process file not found: {process_path}")
    elif args.process:
        process_path = process_definition_path(project_root, args.process)
    else:
        raise SystemExit("FAIL: provide --process or --process-file")
    process = read_yaml_file(process_path)
    process_id = safe_id(str(process.get("id") or process_path.stem), "process")
    answers = _process_authoring_definition_builder.from_definition(process)
    draft = _process_authoring_definition_builder.build(answers)
    unsupported = _process_semantic_policy.unsupported_fields(process)
    paths = process_backfill_paths(project_root, process_id)
    planned = [paths["answers"], paths["draft"], paths["source"], paths["semantic_map"], paths["unsupported"], paths["import_report"]]
    if getattr(args, "dry_run", False):
        print_plan("process-authoring-import dry run", planned, project_root)
        return 0
    _core_common_yaml_io.write_yaml_file(paths["answers"], answers)
    _core_common_yaml_io.write_yaml_file(paths["draft"], draft)
    _core_common_yaml_io.write_yaml_file(paths["source"], process)
    _core_common_yaml_io.write_yaml_file(paths["semantic_map"], _process_semantic_policy.map(process, process_path, project_root, unsupported))
    _core_common_yaml_io.write_yaml_file(paths["unsupported"], {"schema_version": 1, "unsupported": unsupported})
    paths["import_report"].write_text(_process_parity_renderer.import_report(process, process_path, paths, project_root, unsupported), encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "authoring_parity.started", process_id=process_id, subject=process_id, payload={"command": "process-authoring-import", "source": rel(process_path, project_root)}, correlation_id=f"authoring-parity-{process_id}")
    if unsupported:
        _process_event_recorder.emit_process_event(project_root, "authoring_parity.warning", process_id=process_id, subject=process_id, severity="warn", payload={"unsupported": unsupported}, correlation_id=f"authoring-parity-{process_id}")
    print(f"WROTE: {rel(paths['answers'], project_root)}")
    print(f"WROTE: {rel(paths['draft'], project_root)}")
    print(f"WROTE: {rel(paths['semantic_map'], project_root)}")
    return 0














def run_process_parity_check(project_root: Path, process_path: Path, candidate_path: Path | None = None) -> tuple[str, Path, Path, list[dict[str, str]]]:
    source = read_yaml_file(process_path)
    process_id = safe_id(str(source.get("id") or process_path.stem), "process")
    paths = process_backfill_paths(project_root, process_id)
    stale_generated_candidate = (
        not paths["draft"].is_file()
        or not paths["source"].is_file()
        or read_yaml_file(paths["source"]) != source
    )
    if candidate_path is None and stale_generated_candidate:
        args = argparse.Namespace(project_root=str(project_root), process=process_id, process_file=str(process_path), dry_run=False)
        command_process_authoring_import(args)
    candidate = read_yaml_file(candidate_path) if candidate_path else read_yaml_file(paths["draft"])
    unsupported = _process_semantic_policy.unsupported_fields(source)
    status, diffs = _process_semantic_policy.compare(source, candidate)
    answers = read_yaml_file(paths["answers"]) if paths["answers"].is_file() else {}
    logic_checks = _process_authoring_validation_service.logic(candidate, answers)
    source_logic_checks = _process_authoring_validation_service.logic(source, answers)
    source_failures = {item.message for item in source_logic_checks if item.level == "FAIL"}
    candidate_failures = {item.message for item in logic_checks if item.level == "FAIL"}
    introduced_failures = sorted(candidate_failures - source_failures)
    inherited_failures = sorted(candidate_failures & source_failures)
    if introduced_failures:
        status = "FAIL"
        diffs.append({"level": "FAIL", "area": "logic_review", "message": "candidate logic review failed: " + "; ".join(introduced_failures)})
    elif inherited_failures and status == "PASS":
        status = "WARN"
        diffs.append({"level": "WARN", "area": "logic_review", "message": "source definition already has logic review findings: " + "; ".join(inherited_failures)})
    if unsupported and status == "PASS":
        status = "WARN"
    review = locate_flow_root(project_root) / "reviews" / "parity" / "processes" / f"{process_id}-parity.md"
    diff_path = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / f"{process_id}-semantic-diff.yaml"
    review.parent.mkdir(parents=True, exist_ok=True)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(_process_parity_renderer.parity_report(process_id, process_path, project_root, status, diffs, unsupported, logic_checks), encoding="utf-8")
    _core_common_yaml_io.write_yaml_file(diff_path, {"schema_version": 1, "process_id": process_id, "result": status, "diffs": diffs, "unsupported": unsupported})
    _process_event_recorder.emit_process_event(project_root, "authoring_parity.process.checked", process_id=process_id, subject=process_id, severity="error" if status == "FAIL" else ("warn" if status == "WARN" else "info"), payload={"result": status, "review": rel(review, project_root), "semantic_diff": rel(diff_path, project_root)}, correlation_id=f"authoring-parity-{process_id}")
    if status == "FAIL":
        _process_event_recorder.emit_process_event(project_root, "authoring_parity.failed", process_id=process_id, subject=process_id, severity="error", payload={"diffs": diffs}, correlation_id=f"authoring-parity-{process_id}")
    return status, review, diff_path, diffs


def command_process_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    process_path = Path(args.process_file).expanduser() if getattr(args, "process_file", None) else process_definition_path(project_root, args.process)
    if not process_path.is_absolute():
        process_path = project_root / process_path
    candidate_path = Path(args.candidate_file).expanduser() if getattr(args, "candidate_file", None) else None
    if candidate_path and not candidate_path.is_absolute():
        candidate_path = project_root / candidate_path
    status, review, diff_path, _diffs = run_process_parity_check(project_root, process_path, candidate_path)
    print(f"{status}: {rel(review, project_root)}")
    print(f"DIFF: {rel(diff_path, project_root)}")
    return 1 if status == "FAIL" else 0


CRITICAL_PARITY_PROCESSES = {
    "workplace-initialization",
    "project-onboarding",
    "task-batch-execution",
    "process-authoring",
    "reusable-template-authoring",
    "knowledge-package-authoring",
    "platform-contract-authoring",
}


def command_process_parity_check_all(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    rows: list[dict[str, Any]] = []
    failed = False
    warned = False
    for process_id, path, _data in iter_process_definitions(project_root):
        status, review, diff_path, _diffs = run_process_parity_check(project_root, path)
        rows.append({"process_id": process_id, "result": status, "source": rel(path, project_root), "review": rel(review, project_root), "semantic_diff": rel(diff_path, project_root)})
        failed = failed or status == "FAIL"
        warned = warned or status == "WARN"
        print(f"{status}: {process_id}")
    summary = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / "summary.yaml"
    index = locate_flow_root(project_root) / "reviews" / "parity" / "processes" / "index.md"
    result = "FAIL" if failed else ("WARN" if warned else "PASS")
    counts = {status: sum(1 for item in rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
    _core_common_yaml_io.write_yaml_file(
        summary,
        {
            "schema_version": 1,
            "result": result,
            "counts": counts,
            "checked": ["process semantic parity", "authoring backfill candidate", "process logic review"],
            "skipped": ["byte-for-byte YAML formatting", "YAML key order"],
            "processes": rows,
        },
    )
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(_process_parity_renderer.index(rows, "Process Authoring Parity"), encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "authoring_parity.completed" if not failed else "authoring_parity.failed", severity="error" if failed else ("warn" if warned else "info"), subject="process-parity-check-all", payload={"summary": rel(summary, project_root), "index": rel(index, project_root), "result": "FAIL" if failed else ("WARN" if warned else "PASS")}, correlation_id="authoring-parity-all")
    print(f"SUMMARY: {rel(summary, project_root)}")
    print(f"INDEX: {rel(index, project_root)}")
    return 1 if failed else 0




def resource_parity_report(project_root: Path, kind: str, resource_id: str, status: str, notes: list[str], source: str = "") -> Path:
    report = locate_flow_root(project_root) / "reviews" / "parity" / "resources" / f"{safe_id(kind + '-' + resource_id, 'resource')}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title_from_id(kind)} Parity: {resource_id}",
        "",
        f"Result: `{status}`",
        "",
        "## Checked",
        "",
        f"- source: `{source or 'not-discovered'}`",
        "",
        "## Skipped",
        "",
    ]
    if status in {"WARN", "SKIP"}:
        lines.append("- Full authoring round-trip for this resource type is not implemented in this MVP.")
    else:
        lines.append("- None.")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in notes)
    lines.extend(["", "## Deferred Parity Coverage", ""])
    if status == "WARN":
        lines.append("- Replace shallow resource parity with a full authoring round-trip check.")
    else:
        lines.append("- None.")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "authoring_parity.resource.checked", subject=f"{kind}/{resource_id}", severity="warn" if status in {"WARN", "SKIP"} else ("error" if status == "FAIL" else "info"), payload={"kind": kind, "id": resource_id, "result": status, "review": rel(report, project_root)}, correlation_id=f"authoring-parity-{safe_id(kind + '-' + resource_id, 'resource')}")
    return report


def command_template_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        _run_task_inputs.require_flow_root(project_root)
    template_id = safe_id(args.template, "template")
    candidates = [project_root / "templates" / f"{template_id}.yaml", project_root / "templates" / f"{template_id}.md", project_root / "templates" / args.template]
    found = next((path for path in candidates if path.is_file()), None)
    if not found:
        report = resource_parity_report(project_root, "template", template_id, "SKIP", ["No template manifest discovery model is available for this id in the project root."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    text = found.read_text(encoding="utf-8", errors="replace")
    status = "FAIL" if not is_public_path_safe(text) or contains_secret_value(text) else "WARN"
    notes = ["Template file is discoverable."]
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "template", template_id, status, notes, rel(found, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0


def command_knowledge_package_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        _run_task_inputs.require_flow_root(project_root)
    package_id = safe_id(args.package, "package")
    path = project_root / "packages" / f"{package_id}.yaml"
    if not path.is_file():
        report = resource_parity_report(project_root, "knowledge-package", package_id, "SKIP", ["Package manifest was not found in project packages/."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    data = read_yaml_file(path)
    notes = ["Package manifest is discoverable.", "Package root is not hardcoded by this parity check.", "Heavy resources are not copied."]
    status = "FAIL" if public_yaml_has_private_path(data) else "WARN"
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "knowledge-package", package_id, status, notes, rel(path, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0


def command_platform_parity_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else ROOT
    if getattr(args, "project_root", None):
        _run_task_inputs.require_flow_root(project_root)
    platform_id = safe_id(args.platform, "platform")
    candidates = [project_root / "templates" / f"{platform_id}.yaml", project_root / "templates" / f"{platform_id.replace('platform-', 'platform-contract-')}.yaml"]
    path = next((item for item in candidates if item.is_file()), None)
    if not path:
        report = resource_parity_report(project_root, "platform", platform_id, "SKIP", ["Platform contract was not found through the current project discovery model."], "")
        print(f"SKIP: {rel(report, project_root)}")
        return 0
    data = read_yaml_file(path)
    notes = ["Platform contract is discoverable.", "Required and recommended resource references remain in the contract file.", "Referenced packages/templates are not copied into the contract."]
    status = "FAIL" if public_yaml_has_private_path(data) else "WARN"
    if status == "WARN":
        notes.append("WARN: shallow parity check.")
    report = resource_parity_report(project_root, "platform", platform_id, status, notes, rel(path, project_root))
    print(f"{status}: {rel(report, project_root)}")
    return 1 if status == "FAIL" else 0






def command_authoring_parity_check_all(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    process_result = command_process_parity_check_all(argparse.Namespace(project_root=str(project_root)))
    process_summary = locate_flow_root(project_root) / "artifacts" / "parity" / "processes" / "summary.yaml"
    process_status = "FAIL" if process_result else "PASS"
    if process_summary.is_file():
        process_status = str(read_yaml_file(process_summary).get("result") or process_status)
    resource_rows: list[dict[str, Any]] = []
    for kind, resource_id, func in [
        ("template", "process-agent-prompt", command_template_parity_check),
        ("knowledge-package", "process-forge-core", command_knowledge_package_parity_check),
        ("platform", "platform-contract-example-parent", command_platform_parity_check),
    ]:
        code = func(argparse.Namespace(project_root=str(project_root), template=resource_id, package=resource_id, platform=resource_id))
        status, review = _report_projection_reader.resource_status(project_root, kind, resource_id)
        if code:
            status = "FAIL"
        resource_rows.append({"id": resource_id, "kind": kind, "result": status, "review": review})
    summary = locate_flow_root(project_root) / "artifacts" / "parity" / "summary.yaml"
    result = aggregate_status([process_status, *[str(item.get("result", "")) for item in resource_rows]])
    resource_counts = {status: sum(1 for item in resource_rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
    _core_common_yaml_io.write_yaml_file(
        summary,
        {
            "schema_version": 1,
            "result": result,
            "process_result": process_result,
            "process_status": process_status,
            "resource_counts": resource_counts,
            "checked": ["process parity aggregate", "template resource discovery", "knowledge package resource discovery", "platform contract resource discovery"],
            "skipped": ["full resource authoring round-trip for templates, knowledge packages, and platform contracts"],
            "resources": resource_rows,
        },
    )
    print(f"SUMMARY: {rel(summary, project_root)}")
    return 1 if result == "FAIL" else 0


HANDOFF_STATUSES = {"waiting_for_agent", "ready", "accepted", "in_progress", "returned", "finalized", "needs_operator", "cancelled"}
LEASE_STATUSES = {"active", "released", "revoked", "expired", "stale"}


def resolve_workplace_root(value: str | None, *, project_root: Path | None = None) -> Path:
    if value:
        path = Path(value).expanduser()
        if not path.is_absolute() and project_root is not None:
            path = project_root / path
        return path.resolve()
    if project_root is not None:
        manifest = _ProjectMetadataReader(project_root).workplace_manifest()
        if manifest:
            return manifest.parent.resolve()
    raise SystemExit("FAIL: --workplace is required")


















def legacy_agent_presence_path(workplace_root: Path, agent_id: str) -> Path:
    return AgentPresenceReader(workplace_root).legacy_path(agent_id)


def agent_presence_path(workplace_root: Path, agent_id: str, session_id: str) -> Path:
    return AgentPresenceReader(workplace_root).path(agent_id, session_id)


def project_current_session_path(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "runtime" / "current-session.json"


def workplace_current_session_path(workplace_root: Path, project_id: str) -> Path:
    return workplace_root / "runtime" / "current-sessions" / f"{safe_id(project_id, 'project')}.json"


def iter_agent_presence_paths(workplace_root: Path) -> list[Path]:
    return AgentPresenceReader(workplace_root).paths()


def iter_agent_presence(workplace_root: Path) -> list[dict[str, Any]]:
    return AgentPresenceReader(workplace_root).records()


def read_current_project_session(project_root: Path) -> dict[str, Any]:
    return json_read(project_current_session_path(project_root))


def write_current_session_refs(workplace_root: Path, project_root: Path | None, presence: dict[str, Any]) -> None:
    if project_root is None:
        return
    current = {
        "schema_version": 1,
        "agent_id": presence.get("agent_id"),
        "session_id": presence.get("session_id"),
        "project_id": presence.get("project_id"),
        "process_id": presence.get("process_id"),
        "run_id": presence.get("run_id"),
        "status": presence.get("status"),
        "started_at": presence.get("started_at"),
        "last_seen_at": presence.get("last_seen_at"),
        "updated_at": _core_common_clock.now_utc(),
    }
    _core_common_json_io.json_write(project_current_session_path(project_root), current)
    project_id = str(presence.get("project_id") or "")
    if project_id:
        _core_common_json_io.json_write(workplace_current_session_path(workplace_root, project_id), current)


def find_agent_presence(workplace_root: Path, *, agent_id: str | None = None, session_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    return AgentPresenceReader(workplace_root).find(agent_id=agent_id, session_id=session_id, project_id=project_id)


def read_agent_presence(workplace_root: Path, agent_id: str) -> dict[str, Any]:
    return AgentPresenceReader(workplace_root).find(agent_id=agent_id)


def write_agent_presence(workplace_root: Path, payload: dict[str, Any]) -> None:
    _agent_workplace_registry.ensure_agent_workplace_dirs(workplace_root)
    agent_id = str(payload.get("agent_id") or "agent")
    session_id = str(payload.get("session_id") or agent_session_id(agent_id))
    _core_common_json_io.json_write(agent_presence_path(workplace_root, agent_id, session_id), payload)


def agent_session_id(agent_id: str) -> str:
    return f"sess-{safe_id(agent_id, 'agent')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def ttl_expired(presence: dict[str, Any], *, now: datetime | None = None) -> bool:
    timestamp = _worker_observation_inputs.parse_runtime_timestamp(presence.get("last_seen_at"))
    if timestamp is None:
        return True
    ttl = int(presence.get("heartbeat_ttl_seconds") or 300)
    return (now or datetime.now(timezone.utc)) > timestamp + timedelta(seconds=ttl)


def update_stale_agent_presence(workplace_root: Path) -> None:
    for presence in iter_agent_presence(workplace_root):
        if not presence:
            continue
        if str(presence.get("status")) == "online" and ttl_expired(presence):
            presence["status"] = "stale"
            presence["updated_at"] = _core_common_clock.now_utc()
            write_agent_presence(workplace_root, presence)
            project_ref = str(presence.get("project_root") or "")
            if project_ref:
                try:
                    write_current_session_refs(workplace_root, Path(project_ref).expanduser().resolve(), presence)
                except OSError:
                    pass
            _agent_workplace_registry.append_agent_ledger_event(
                workplace_root,
                {
                    "event": "agent.session_expired",
                    "agent_id": presence.get("agent_id"),
                    "session_id": presence.get("session_id"),
                    "project_id": presence.get("project_id"),
                    "process_id": presence.get("process_id"),
                    "run_id": presence.get("run_id"),
                },
            )


def checked_in_agents(workplace_root: Path, *, role: str | None = None, project_id: str | None = None) -> list[dict[str, Any]]:
    update_stale_agent_presence(workplace_root)
    rows: list[dict[str, Any]] = []
    for item in iter_agent_presence(workplace_root):
        if str(item.get("status")) != "online":
            continue
        if role and role not in [str(value) for value in as_list(item.get("roles"))]:
            continue
        if project_id and str(item.get("project_id") or "") != project_id:
            continue
        rows.append(item)
    return rows


def command_agent_register(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    agent_id = safe_id(args.agent, "agent")
    registry = _agent_workplace_registry.load_agent_registry(workplace_root)
    agents = registry.setdefault("agents", [])
    if not isinstance(agents, list):
        agents = []
        registry["agents"] = agents
    record = {
        "id": agent_id,
        "title": args.title or agent_id,
        "kind": args.kind,
        "roles": [str(item) for item in as_list(args.role)],
        "capabilities": [str(item) for item in as_list(args.capability)],
        "supports_specializations": [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(getattr(args, "supports_specialization", []))],
    }
    existing = next((item for item in agents if isinstance(item, dict) and item.get("id") == agent_id), None)
    if existing:
        existing.update(record)
    else:
        agents.append(record)
    _agent_workplace_registry.save_agent_registry(workplace_root, registry)
    print(f"REGISTERED: {agent_id}")
    return 0


def command_agent_list(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    registry = _agent_workplace_registry.load_agent_registry(workplace_root)
    agents = [item for item in registry.get("agents", []) if isinstance(item, dict)]
    if getattr(args, "json", False):
        print(json.dumps({"agents": agents}, ensure_ascii=False, indent=2))
        return 0
    for item in agents:
        print(f"{item.get('id')}\t{','.join(str(role) for role in as_list(item.get('roles')))}\t{item.get('kind', '')}")
    return 0


def command_agent_checkin(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    agent_id = safe_id(args.agent, "agent")
    session_id = args.session or agent_session_id(agent_id)
    project_id = args.project_id or (safe_id(project_root.name, "project") if project_root else "")
    roles = [str(item) for item in as_list(args.role)]
    registry = _agent_workplace_registry.load_agent_registry(workplace_root)
    profile = next((item for item in registry.get("agents", []) if isinstance(item, dict) and item.get("id") == agent_id), {})
    capabilities = [str(item) for item in (as_list(getattr(args, "capability", [])) or as_list(profile.get("capabilities")))]
    supported_specializations = [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(getattr(args, "supports_specialization", [])) or as_list(profile.get("supports_specializations"))]
    now = _core_common_clock.now_utc()
    presence = {
        "schema_version": 1,
        "agent_id": agent_id,
        "session_id": session_id,
        "status": "online",
        "roles": roles,
        "capabilities": capabilities,
        "supports_specializations": supported_specializations,
        "project_id": project_id,
        "project_root_ref": "project-root" if project_root else "",
        "project_root": str(project_root) if project_root else "",
        "process_id": args.process or "",
        "run_id": args.run or "",
        "task_id": args.task or "",
        "started_at": now,
        "last_seen_at": now,
        "heartbeat_ttl_seconds": int(args.ttl or 300),
        "updated_at": now,
    }
    write_agent_presence(workplace_root, presence)
    _agent_workplace_registry.append_agent_ledger_event(
        workplace_root,
        {
            "event": "agent.checked_in",
            "agent_id": agent_id,
            "session_id": session_id,
            "project_id": project_id,
            "project_root_ref": "project-root" if project_root else "",
            "project_root": str(project_root) if project_root else "",
            "process_id": args.process or "",
            "run_id": args.run or "",
            "task_id": args.task or "",
            "roles": roles,
            "supports_specializations": supported_specializations,
            "started_at": now,
        },
    )
    write_current_session_refs(workplace_root, project_root, presence)
    if getattr(args, "json", False):
        print(json.dumps(presence, ensure_ascii=False, indent=2))
    else:
        print(f"CHECKED_IN: {agent_id} session={session_id}")
    return 0


def command_agent_heartbeat(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    current = read_current_project_session(project_root) if project_root else {}
    raw_agent = getattr(args, "agent", None) or str(current.get("agent_id") or "")
    raw_session = getattr(args, "session", None) or str(current.get("session_id") or "")
    presence = find_agent_presence(workplace_root, agent_id=raw_agent or None, session_id=raw_session or None)
    if not presence:
        print(f"FAIL: agent presence not found: agent={raw_agent or '<unspecified>'} session={raw_session or '<unspecified>'}")
        return 1
    if raw_session and presence.get("session_id") != raw_session:
        print(f"FAIL: session mismatch for {presence.get('agent_id')}")
        return 1
    presence["status"] = "online"
    presence["last_seen_at"] = _core_common_clock.now_utc()
    if getattr(args, "task", None):
        presence["task_id"] = args.task
    write_agent_presence(workplace_root, presence)
    write_current_session_refs(workplace_root, project_root, presence)
    _agent_workplace_registry.append_agent_ledger_event(workplace_root, {"event": "agent.heartbeat", "agent_id": presence.get("agent_id"), "session_id": presence.get("session_id"), "project_id": presence.get("project_id"), "process_id": presence.get("process_id"), "run_id": presence.get("run_id"), "task_id": presence.get("task_id")})
    print(f"HEARTBEAT: {presence.get('agent_id')} session={presence.get('session_id')}")
    return 0


def command_agent_checkout(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    current = read_current_project_session(project_root) if project_root else {}
    raw_agent = getattr(args, "agent", None) or str(current.get("agent_id") or "")
    raw_session = getattr(args, "session", None) or str(current.get("session_id") or "")
    presence = find_agent_presence(workplace_root, agent_id=raw_agent or None, session_id=raw_session or None)
    if not presence:
        print(f"FAIL: agent presence not found: agent={raw_agent or '<unspecified>'} session={raw_session or '<unspecified>'}")
        return 1
    if raw_session and presence.get("session_id") != raw_session:
        print(f"FAIL: session mismatch for {presence.get('agent_id')}")
        return 1
    presence["status"] = "checked_out"
    presence["last_seen_at"] = _core_common_clock.now_utc()
    presence["updated_at"] = _core_common_clock.now_utc()
    presence["finished_at"] = presence["updated_at"]
    write_agent_presence(workplace_root, presence)
    write_current_session_refs(workplace_root, project_root, presence)
    _agent_workplace_registry.append_agent_ledger_event(workplace_root, {"event": "agent.checked_out", "agent_id": presence.get("agent_id"), "session_id": presence.get("session_id"), "project_id": presence.get("project_id"), "process_id": presence.get("process_id"), "run_id": presence.get("run_id"), "finished_at": _core_common_clock.now_utc()})
    print(f"CHECKED_OUT: {presence.get('agent_id')} session={presence.get('session_id')}")
    return 0


def command_agent_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    update_stale_agent_presence(workplace_root)
    project_id = getattr(args, "project_id", None) or (safe_id(project_root.name, "project") if project_root else None)
    rows = []
    for item in iter_agent_presence(workplace_root):
        if getattr(args, "agent", None) and item.get("agent_id") != safe_id(args.agent, "agent"):
            continue
        if getattr(args, "session", None) and item.get("session_id") != str(args.session):
            continue
        if project_id and str(item.get("project_id") or "") != project_id:
            continue
        rows.append(item)
    payload: Any = rows[0] if getattr(args, "session", None) and len(rows) == 1 else rows
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(dump_yaml(payload))
    return 0


def command_agent_availability(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    role = args.role
    project_id = getattr(args, "project_id", None) or (safe_id(project_root.name, "project") if project_root else None)
    agents = checked_in_agents(workplace_root, role=role, project_id=project_id)
    payload = {
        "available": bool(agents),
        "role": role,
        "reason": "available" if agents else "no checked-in agent with required role",
        "agents": [{"agent_id": item.get("agent_id"), "session_id": item.get("session_id"), "roles": item.get("roles", [])} for item in agents],
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(("AVAILABLE" if payload["available"] else "UNAVAILABLE") + f": {role} ({payload['reason']})")
    return 0


def command_agent_ledger_doctor(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    update_stale_agent_presence(workplace_root)
    checks: list[Check] = []
    registry = _agent_workplace_registry.workplace_agent_registry_path(workplace_root)
    ledger = _agent_workplace_registry.workplace_agent_ledger_path(workplace_root)
    checks.append(check("PASS" if registry.is_file() else "FAIL", "agent registry exists"))
    checks.append(check("PASS" if ledger.is_file() else "FAIL", "agent session ledger exists"))
    if ledger.is_file():
        for index, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                checks.append(check("FAIL", f"ledger line {index} invalid JSON: {exc}"))
                continue
            checks.append(check("PASS" if event.get("event") in {"agent.checked_in", "agent.heartbeat", "agent.checked_out", "agent.session_expired", "agent.session_recovered"} else "FAIL", f"ledger line {index} event valid"))
    return print_checks(checks)


def lease_path(workplace_root: Path, lease_id: str) -> Path:
    return _agent_workplace_registry.workplace_agent_leases_dir(workplace_root) / f"{safe_id(lease_id, 'lease')}.yaml"


def load_lease(workplace_root: Path, lease_id: str) -> dict[str, Any]:
    return load_yaml_document(lease_path(workplace_root, lease_id))


def save_lease(workplace_root: Path, lease: dict[str, Any]) -> None:
    _agent_workplace_registry.ensure_agent_workplace_dirs(workplace_root)
    with registry_file_lock(_agent_workplace_registry.workplace_agent_leases_dir(workplace_root) / "registry"):
        _core_common_yaml_io.write_yaml_file(lease_path(workplace_root, str(lease.get("id") or "lease")), lease)


def command_agent_lease_grant(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    lease_id = safe_id(args.id or f"lease-{args.agent}-{args.task or args.run or 'work'}", "lease")
    issued = datetime.now(timezone.utc).replace(microsecond=0)
    expires = issued + timedelta(seconds=int(args.ttl or 3600))
    lease = {
        "schema_version": 1,
        "id": lease_id,
        "agent_id": safe_id(args.agent, "agent"),
        "session_id": args.session or read_agent_presence(workplace_root, args.agent).get("session_id", ""),
        "status": "active",
        "scope": {
            "project_id": args.project_id or "",
            "process_id": args.process or "",
            "run_id": args.run or "",
            "task_id": args.task or "",
        },
        "access": {
            "capsule": _context_contract_inputs.normalize_assignment_path(args.capsule or ""),
            "allowed_files": [_context_contract_inputs.normalize_assignment_path(item) for item in as_list(args.allowed_file)],
            "allowed_read_files": [_context_contract_inputs.normalize_assignment_path(item) for item in as_list(args.allowed_read_file)],
            "forbidden_files": [_context_contract_inputs.normalize_assignment_path(item) for item in as_list(args.forbidden_file)],
        },
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
    }
    save_lease(workplace_root, lease)
    print(f"LEASE_GRANTED: {lease_id}")
    return 0


def command_agent_lease_update_status(args: argparse.Namespace, status: str) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    lease = load_lease(workplace_root, args.lease)
    if not lease:
        print(f"FAIL: lease not found: {args.lease}")
        return 1
    lease["status"] = status
    lease["updated_at"] = _core_common_clock.now_utc()
    save_lease(workplace_root, lease)
    print(f"LEASE_{status.upper()}: {lease.get('id')}")
    return 0


def command_agent_lease_release(args: argparse.Namespace) -> int:
    return command_agent_lease_update_status(args, "released")


def command_agent_lease_revoke(args: argparse.Namespace) -> int:
    return command_agent_lease_update_status(args, "revoked")


def command_agent_lease_list(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    rows = [load_yaml_document(path) for path in sorted(_agent_workplace_registry.workplace_agent_leases_dir(workplace_root).glob("*.yaml"))]
    if getattr(args, "json", False):
        print(json.dumps({"leases": rows}, ensure_ascii=False, indent=2))
    else:
        for item in rows:
            print(f"{item.get('id')}\t{item.get('status')}\t{item.get('agent_id')}\t{(item.get('scope') or {}).get('task_id', '')}")
    return 0


def command_agent_lease_doctor(args: argparse.Namespace) -> int:
    workplace_root = resolve_workplace_root(args.workplace)
    checks: list[Check] = []
    for path in sorted(_agent_workplace_registry.workplace_agent_leases_dir(workplace_root).glob("*.yaml")):
        lease = load_yaml_document(path)
        checks.append(check("PASS" if lease.get("id") else "FAIL", f"{path.name} id present"))
        checks.append(check("PASS" if lease.get("agent_id") else "FAIL", f"{path.name} agent_id present"))
        checks.append(check("PASS" if lease.get("status") in LEASE_STATUSES else "FAIL", f"{path.name} status valid"))
        if str(lease.get("status")) == "active":
            expires = _worker_observation_inputs.parse_runtime_timestamp(lease.get("expires_at"))
            checks.append(check("PASS" if expires and expires > datetime.now(timezone.utc) else "WARN", f"{path.name} active lease not expired"))
    if not checks:
        checks.append(check("PASS", "no leases present"))
    return print_checks(checks)


def mark_expired_agent_leases(workplace_root: Path) -> int:
    changed = 0
    now = datetime.now(timezone.utc)
    for path in sorted(_agent_workplace_registry.workplace_agent_leases_dir(workplace_root).glob("*.yaml")):
        lease = load_yaml_document(path)
        if str(lease.get("status")) != "active":
            continue
        expires = _worker_observation_inputs.parse_runtime_timestamp(lease.get("expires_at"))
        if expires and expires <= now:
            lease["status"] = "stale"
            lease["updated_at"] = _core_common_clock.now_utc()
            _core_common_yaml_io.write_yaml_file(path, lease)
            changed += 1
    return changed








def command_process_route_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    routes = [item for item in _process_route_document_reader.read(project_root).get("routes", []) if isinstance(item, dict)]
    if getattr(args, "json", False):
        print(json.dumps({"routes": routes}, ensure_ascii=False, indent=2))
    else:
        for item in routes:
            print(f"{item.get('id')}\t{item.get('from_process')}\t{item.get('to_process')}\t{item.get('mode')}")
    return 0




def command_process_route_validate(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    return print_checks(_process_route_service.validate(project_root))


def command_process_route_doctor(args: argparse.Namespace) -> int:
    return command_process_route_validate(args)








def save_handoff(project_root: Path, handoff: dict[str, Any]) -> None:
    handoff["updated_at"] = _core_common_clock.now_utc()
    _core_common_yaml_io.write_yaml_file(_handoff_document_reader.path(project_root, str(handoff.get("id") or "handoff")), handoff)




def command_handoff_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    route = _process_route_service.by_id(project_root, args.route)
    handoff_id = safe_id(args.id or f"handoff-{route.get('id')}", "handoff")
    root = _handoff_document_reader.directory(project_root, handoff_id)
    handoff = {
        "schema_version": 1,
        "id": handoff_id,
        "status": "waiting_for_agent",
        "route_id": str(route.get("id")),
        "from": {"process": str(route.get("from_process") or ""), "run_id": args.from_run, "stage": args.from_stage or ""},
        "to": {
            "process": str(route.get("to_process") or ""),
            "mode": str(route.get("mode") or "wait_for_result"),
            "required_role": _process_route_service.required_role(route),
            "required_capabilities": [str(item) for item in as_list(route.get("required_capabilities"))],
            "required_specializations": [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(route.get("required_specializations"))],
            "preferred_specializations": [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(route.get("preferred_specializations"))],
        },
        "input_artifacts": as_list((route.get("input_contract") if isinstance(route.get("input_contract"), dict) else {}).get("required_artifacts")),
        "expected_results": as_list((route.get("output_contract") if isinstance(route.get("output_contract"), dict) else {}).get("expected_artifacts")),
        "return_to": route.get("return") if isinstance(route.get("return"), dict) else {"process": str(route.get("from_process") or ""), "run_id": args.from_run},
        "created_at": _core_common_clock.now_utc(),
    }
    planned = [root / "handoff.yaml", root / "handoff.md", root / "input-manifest.yaml", root / "expected-output.yaml", root / "return-package.yaml"]
    if not getattr(args, "apply", False):
        print_plan("handoff-create dry run", planned, project_root)
        return 0
    root.mkdir(parents=True, exist_ok=True)
    save_handoff(project_root, handoff)
    _core_common_yaml_io.write_yaml_file(root / "input-manifest.yaml", {"schema_version": 1, "handoff_id": handoff_id, "artifacts": handoff["input_artifacts"]})
    _core_common_yaml_io.write_yaml_file(root / "expected-output.yaml", {"schema_version": 1, "handoff_id": handoff_id, "expected_results": handoff["expected_results"]})
    _core_common_yaml_io.write_yaml_file(root / "return-package.yaml", {"schema_version": 1, "handoff_id": handoff_id, "status": "pending", "artifacts": []})
    (root / "handoff.md").write_text(f"# Handoff: {handoff_id}\n\nStatus: waiting_for_agent\n\nRoute: `{route.get('id')}`\n", encoding="utf-8")
    print(f"WROTE: {rel(root / 'handoff.yaml', project_root)}")
    return 0


def handoff_available_agents(args: argparse.Namespace, handoff: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    workplace = getattr(args, "workplace", None)
    if not workplace:
        return []
    role = str((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_role") or "")
    project_id = getattr(args, "project_id", None)
    agents = checked_in_agents(resolve_workplace_root(workplace, project_root=project_root), role=role or None, project_id=project_id)
    required_capabilities = set(str(item) for item in as_list((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_capabilities")))
    if required_capabilities:
        agents = [
            agent for agent in agents
            if required_capabilities.issubset({str(item) for item in as_list(agent.get("capabilities"))})
        ]
    required = set(as_list((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_specializations")))
    if required:
        agents = [
            agent for agent in agents
            if required.issubset({_specialization_catalog_reader.resource_id(str(item)) for item in as_list(agent.get("supports_specializations"))})
        ]
    return agents


def command_handoff_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    handoff = _handoff_document_reader.read(project_root, args.handoff)
    agents = handoff_available_agents(args, handoff, project_root)
    payload = {
        "handoff": handoff.get("id"),
        "status": handoff.get("status"),
        "required_role": (handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_role", ""),
        "required_capabilities": (handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_capabilities", []),
        "available_agents": [{"agent_id": item.get("agent_id"), "session_id": item.get("session_id")} for item in agents],
    }
    if payload["status"] == "waiting_for_agent" and agents:
        payload["status"] = "ready"
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(dump_yaml(payload))
    return 0


def command_handoff_accept(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    handoff = _handoff_document_reader.read(project_root, args.handoff)
    handoff["status"] = "accepted"
    handoff["accepted_by"] = {"agent_id": safe_id(args.agent, "agent"), "session_id": args.session or "", "accepted_at": _core_common_clock.now_utc()}
    save_handoff(project_root, handoff)
    print(f"ACCEPTED: {handoff.get('id')}")
    return 0


def command_handoff_start_target_run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    handoff = _handoff_document_reader.read(project_root, args.handoff)
    run_id = safe_id(args.run or f"{handoff.get('id')}-target", "run")
    process_id = str((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("process") or "task-batch-execution")
    if not _work_paths.run_document(project_root, run_id).is_file():
        status = command_run_create(argparse.Namespace(project_root=str(project_root), id=run_id, title=f"Target run for {handoff.get('id')}", process=process_id, objective=f"Handoff target for {handoff.get('id')}", status="in_progress", dry_run=False))
        if status:
            return status
    handoff["status"] = "in_progress"
    handoff.setdefault("target", {})["run_id"] = run_id
    save_handoff(project_root, handoff)
    print(f"TARGET_RUN: {run_id}")
    return 0


def command_handoff_return(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    handoff = _handoff_document_reader.read(project_root, args.handoff)
    artifacts = [_context_contract_inputs.normalize_assignment_path(item) for item in as_list(args.artifact)]
    missing = [item for item in artifacts if not (project_root / item).is_file()]
    if missing:
        print("FAIL: return artifacts missing: " + ", ".join(missing))
        return 1
    handoff["status"] = "returned"
    handoff["returned_at"] = _core_common_clock.now_utc()
    handoff["return_artifacts"] = artifacts
    save_handoff(project_root, handoff)
    _core_common_yaml_io.write_yaml_file(_handoff_document_reader.directory(project_root, str(handoff.get("id"))) / "return-package.yaml", {"schema_version": 1, "handoff_id": handoff.get("id"), "status": "returned", "artifacts": artifacts, "returned_at": handoff["returned_at"]})
    print(f"RETURNED: {handoff.get('id')}")
    return 0


def command_handoff_finalize(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    handoff = _handoff_document_reader.read(project_root, args.handoff)
    if str(handoff.get("status")) not in {"returned", "accepted", "in_progress"}:
        print(f"FAIL: handoff is not finalizable: {handoff.get('status')}")
        return 1
    handoff["status"] = "finalized"
    handoff["finalized_at"] = _core_common_clock.now_utc()
    save_handoff(project_root, handoff)
    print(f"FINALIZED: {handoff.get('id')}")
    return 0


def command_handoff_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    checks: list[Check] = []
    for root in sorted((locate_flow_root(project_root) / "handoffs").glob("*")):
        if not root.is_dir() or root.name == "runs":
            continue
        handoff = load_yaml_document(root / "handoff.yaml")
        checks.append(check("PASS" if handoff.get("id") else "FAIL", f"{root.name} handoff id present"))
        checks.append(check("PASS" if handoff.get("status") in HANDOFF_STATUSES else "FAIL", f"{root.name} handoff status valid"))
        for name in ["input-manifest.yaml", "expected-output.yaml", "return-package.yaml"]:
            checks.append(check("PASS" if (root / name).is_file() else "FAIL", f"{root.name} {name} exists"))
    if not checks:
        checks.append(check("PASS", "no handoff packages present"))
    return print_checks(checks)


def command_handoff_offer(args: argparse.Namespace) -> int:
    return command_handoff_status(args)


def command_agent_director_tick(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    workplace_root = resolve_workplace_root(args.workplace, project_root=project_root)
    changed = mark_expired_agent_leases(workplace_root)
    for root in sorted((locate_flow_root(project_root) / "handoffs").glob("*")):
        if not root.is_dir() or not (root / "handoff.yaml").is_file():
            continue
        handoff = load_yaml_document(root / "handoff.yaml")
        if handoff.get("status") != "waiting_for_agent":
            continue
        role = str((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_role") or "")
        agents = checked_in_agents(workplace_root, role=role or None, project_id=getattr(args, "project_id", None))
        required_capabilities = set(str(item) for item in as_list((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_capabilities")))
        if required_capabilities:
            agents = [
                agent for agent in agents
                if required_capabilities.issubset({str(item) for item in as_list(agent.get("capabilities"))})
            ]
        required_specializations = set(as_list((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_specializations")))
        if required_specializations:
            agents = [
                agent for agent in agents
                if required_specializations.issubset({_specialization_catalog_reader.resource_id(str(item)) for item in as_list(agent.get("supports_specializations"))})
            ]
        if not agents:
            created = _worker_observation_inputs.parse_runtime_timestamp(handoff.get("created_at"))
            if created and datetime.now(timezone.utc) > created + timedelta(seconds=int(args.wait_ttl or 3600)):
                handoff["status"] = "needs_operator"
                handoff["director_reason"] = "required agent unavailable past wait ttl"
                save_handoff(project_root, handoff)
                changed += 1
            continue
        agent = agents[0]
        handoff_id = str(handoff.get("id") or root.name)
        lease_id = f"lease-{handoff_id}-{agent.get('agent_id')}"
        command_agent_lease_grant(
            argparse.Namespace(
                workplace=str(workplace_root),
                id=lease_id,
                agent=str(agent.get("agent_id")),
                session=str(agent.get("session_id") or ""),
                project_id=getattr(args, "project_id", "") or str(agent.get("project_id") or ""),
                process=str((handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("process") or ""),
                run=str((handoff.get("target") if isinstance(handoff.get("target"), dict) else {}).get("run_id") or ""),
                task="",
                capsule="",
                allowed_file=[],
                allowed_read_file=[],
                forbidden_file=[],
                ttl=int(args.lease_ttl or 3600),
            )
        )
        handoff["status"] = "ready"
        handoff["assigned_agent"] = {"agent_id": agent.get("agent_id"), "session_id": agent.get("session_id"), "lease_id": lease_id}
        save_handoff(project_root, handoff)
        changed += 1
    print(f"DIRECTOR_TICK: changed={changed}")
    return 0


def command_agent_director_run(args: argparse.Namespace) -> int:
    ticks = max(1, int(args.max_ticks or 1))
    result = 0
    for _index in range(ticks):
        result = command_agent_director_tick(args)
        if result:
            return result
        if float(args.interval or 0) > 0:
            time.sleep(float(args.interval))
    return result


def command_agent_director_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    rows: list[dict[str, Any]] = []
    for path in sorted((locate_flow_root(project_root) / "handoffs").glob("*/handoff.yaml")):
        handoff = load_yaml_document(path)
        rows.append({"id": handoff.get("id"), "status": handoff.get("status"), "required_role": (handoff.get("to") if isinstance(handoff.get("to"), dict) else {}).get("required_role", "")})
    if getattr(args, "json", False):
        print(json.dumps({"handoffs": rows}, ensure_ascii=False, indent=2))
    else:
        print(dump_yaml({"handoffs": rows}))
    return 0


def continuation_path(project_root: Path, continuation_id: str) -> Path:
    return locate_flow_root(project_root) / "continuations" / f"{safe_id(continuation_id, 'continuation')}.yaml"


def command_continuation_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    if getattr(args, "assignment", None) or getattr(args, "context_id", None):
        return continuation_command(args, "create", continuation_id=args.id, run_id=args.run,
                                    assignment_id=args.assignment, context_id=args.context_id,
                                    expected_artifacts=args.expected_artifact, handoff_id=args.handoff or "",
                                    instruction=args.instruction or "", apply=args.apply)
    continuation_id = safe_id(args.id, "continuation")
    payload = {
        "schema_version": 1,
        "id": continuation_id,
        "agent_id": args.agent or "",
        "previous_session_id": args.session or "",
        "waiting_for": {"handoff_id": args.handoff or "", "expected_artifacts": [_context_contract_inputs.normalize_assignment_path(item) for item in as_list(args.expected_artifact)]},
        "resume": {"process": args.process or "", "run_id": args.run or "", "stage": args.stage or "", "instruction": args.instruction or ""},
        "status": "waiting",
        "created_at": _core_common_clock.now_utc(),
    }
    path = continuation_path(project_root, continuation_id)
    if path.exists():
        print("FAIL: continuation already exists; preserve it and choose a new id")
        return 1
    if not getattr(args, "apply", False):
        print_plan("continuation-create dry run", [path], project_root)
        return 0
    _core_common_yaml_io.write_yaml_file(path, payload)
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_continuation_status(args: argparse.Namespace) -> int:
    return continuation_command(args, "status", continuation_id=args.continuation or "")


def command_continuation_resume(args: argparse.Namespace) -> int:
    return continuation_command(args, "resume", continuation_id=args.continuation, session_id=getattr(args, "session", None) or "")


def continuation_command(args: argparse.Namespace, operation: str, **request: Any) -> int:
    from processforge_core.work.continuation import ContinuationService
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, getattr(args, "workplace", None))
    result = ContinuationService(project_root, manifest.parent if manifest else None, sys.modules[__name__], events=_process_event_recorder).request(operation, **request)
    print(json.dumps(result, ensure_ascii=False, indent=2) if getattr(args, "json", False) else dump_yaml(result))
    return 1 if result.get("status") == "blocked" else 0


def command_work_cancel(args: argparse.Namespace) -> int:
    return continuation_command(args, "cancel_work", run_id=args.run, assignment_id=args.assignment,
                                context_id=args.context_id, capsule_checksum=args.capsule_checksum,
                                reason=args.reason, evidence=args.evidence, apply=args.apply)


def command_continuation_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    checks: list[Check] = []
    for path in sorted((locate_flow_root(project_root) / "continuations").glob("*.yaml")):
        payload = load_yaml_document(path)
        checks.append(check("PASS" if payload.get("id") else "FAIL", f"{path.name} id present"))
        checks.append(check("PASS" if isinstance(payload.get("waiting_for"), dict) else "FAIL", f"{path.name} waiting_for present"))
        checks.append(check("PASS" if isinstance(payload.get("resume"), dict) else "FAIL", f"{path.name} resume present"))
    if not checks:
        checks.append(check("PASS", "no continuation capsules present"))
    return print_checks(checks)















AGENT_RUN_STATUSES = {
    "planned",
    "ready",
    "starting",
    "running",
    "completed",
    "failed",
    "timed_out",
    "unknown_exit",
    "lost",
    "blocked",
    "cancelled",
    "manual_required",
}

AGENT_RUN_FAILURE_TERMINAL_STATUSES = {"failed", "timed_out", "unknown_exit", "lost"}
AGENT_RUN_START_SKIP_STATUSES = {"running", "completed", "failed", "timed_out", "unknown_exit", "lost", "cancelled"}






































def command_runtime_driver_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    if project_root:
        _run_task_inputs.require_flow_root(project_root)
    workplace_manifest = _workplace_registry_reader.normalize_workplace_manifest(Path(args.workplace)) if getattr(args, "workplace", None) else (_ProjectMetadataReader(project_root).workplace_manifest() if project_root else None)
    for driver_id, status, source in _runtime_driver_catalog_reader.ids(workplace_manifest=workplace_manifest, project_root=project_root):
        print(f"{driver_id}\t{status}\t{source}")
    return 0


def command_runtime_driver_validate(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    if project_root:
        _run_task_inputs.require_flow_root(project_root)
    workplace_manifest = _workplace_registry_reader.normalize_workplace_manifest(Path(args.workplace)) if getattr(args, "workplace", None) else (_ProjectMetadataReader(project_root).workplace_manifest() if project_root else None)
    driver = _runtime_driver_catalog_reader.resolve(args.driver, workplace_manifest=workplace_manifest, project_root=project_root)
    return print_checks(_runtime_driver_definition_policy.validate(driver, getattr(args, "executable", None), include_start_readiness=True))


def command_runtime_driver_describe(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    if project_root:
        _run_task_inputs.require_flow_root(project_root)
    workplace_manifest = _workplace_registry_reader.normalize_workplace_manifest(Path(args.workplace)) if getattr(args, "workplace", None) else (_ProjectMetadataReader(project_root).workplace_manifest() if project_root else None)
    driver = _runtime_driver_catalog_reader.resolve(args.driver, workplace_manifest=workplace_manifest, project_root=project_root)
    driver.pop("_source_path", None)
    print(dump_yaml(driver))
    return 0




def supervisor_root(project_root: Path) -> Path:
    return locate_flow_root(project_root) / "runtime" / "supervisor"














@contextlib.contextmanager
def worker_run_lifecycle_lock(project_root: Path, run_id: str, task_id: str) -> Any:
    from processforge_core.prepared.input import private_file
    root = _work_paths.agent_run(project_root, run_id, task_id)
    try:
        for path in _work_paths.worker_run(project_root, run_id, task_id).values():
            private_file(project_root, rel(path, project_root))
        for name in (".lifecycle.lock", ".lifecycle.lock.guard"):
            private_file(project_root, rel(root / name, project_root))
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit("FAIL: worker private path invalid: " + str(exc)) from exc
    # The existing OS guard serializes dead-owner recovery and releases on
    # process exit. Proven dead local owners can be reclaimed immediately.
    with registry_file_lock(root / "lifecycle", stale_after_seconds=0):
        yield










def existing_running_worker_run(project_root: Path, task: dict[str, Any], fallback_driver_ref: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]] | None:
    task_id = safe_id(str(task.get("id") or "task"), "task")
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    state = load_agent_run_state(project_root, run_id, task_id)
    if str(state.get("status") or "") != "running":
        return None
    driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state, fallback_driver_ref)
    observed = observe_worker_run(project_root, task, driver, state) if _worker_observation_inputs.worker_run_state_requires_reconciliation(project_root, run_id, task_id, state) else state
    if str(observed.get("status") or "") == "running":
        return observed, driver, paths
    return None


def emit_worker_run_skip(project_root: Path, task: dict[str, Any], driver: dict[str, Any], state: dict[str, Any], event_type: str) -> None:
    task_id = safe_id(str(task.get("id") or state.get("task_id") or "task"), "task")
    run_id = safe_id(str(task.get("run_id") or state.get("run_id") or "run"), "run")
    pid = state.get("pid")
    _process_event_recorder.emit_process_event(
        project_root,
        event_type,
        process_id=_run_task_inputs.task_process_id(task),
        subject=task_id,
        assignment_id_value=task_id,
        assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root),
        payload={"run_id": run_id, "driver_id": driver.get("id"), "status": "running", "pid": pid if isinstance(pid, int) else None, "reason": "already running"},
        correlation_id=f"run-{run_id}",
    )










def write_agent_run_state(
    project_root: Path,
    task: dict[str, Any],
    driver: dict[str, Any],
    status: str,
    *,
    pid: int | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    exit_code: int | None = None,
    failure_reason: str | None = None,
    command: dict[str, Any] | None = None,
    paths: dict[str, Path] | None = None,
    attempt: int | None = None,
) -> dict[str, Any]:
    task_id = safe_id(str(task.get("id") or "task"), "task")
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    paths = paths or _work_paths.worker_run(project_root, run_id, task_id)
    driver_limits, limit_errors = _runtime_driver_definition_policy.parse_limits(driver)
    if limit_errors:
        raise SystemExit("FAIL: runtime driver invalid: " + "; ".join(limit_errors))
    previous_state = json_read(paths["status"])
    if attempt is None:
        try:
            attempt = max(1, int(previous_state.get("attempt") or 1))
        except (TypeError, ValueError):
            attempt = 1
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task_id,
        "driver_id": str(driver.get("id") or "manual"),
        "agent_model": _context_contract_inputs.normalize_agent_model(task.get("agent_model") or task.get("model") or ""),
        "status": status,
        "pid": pid,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "timeout_seconds": driver_limits["timeout_seconds"],
        "attempt": attempt,
        "max_retries": driver_limits["max_retries"],
        "capsule_path": rel(locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml", project_root),
        "worker_prompt_path": rel(_work_paths.worker_prompt(project_root, run_id, task_id), project_root),
        "expected_report_path": _work_output_policy.expected_report(task),
        "stdout_path": rel(paths["stdout"], project_root),
        "stderr_path": rel(paths["stderr"], project_root),
        "heartbeat_path": rel(paths["heartbeat"], project_root),
        "last_heartbeat_at": None,
        "failure_reason": failure_reason,
    }
    if paths["heartbeat"].is_file():
        state["last_heartbeat_at"] = _core_common_clock.now_utc()
    reference = (command or {}).get("prepared_input")
    if reference is None and previous_state.get("attempt") == attempt:
        reference = previous_state.get("prepared_input")
    if reference:
        state["prepared_input"] = reference
    _core_common_json_io.json_write(paths["status"], state)
    if command:
        _core_common_json_io.json_write(paths["command"], command)
    return state


def load_agent_run_state(project_root: Path, run_id: str, task_id: str) -> dict[str, Any]:
    return json_read(_work_paths.worker_run(project_root, run_id, task_id)["status"])






def terminate_worker_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            return




def observe_worker_run(project_root: Path, task: dict[str, Any], driver: dict[str, Any] | str, state: dict[str, Any]) -> dict[str, Any]:
    task_id = safe_id(str(task.get("id") or state.get("task_id") or "task"), "task")
    run_id = safe_id(str(task.get("run_id") or state.get("run_id") or "run"), "run")
    if isinstance(driver, str):
        driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state, driver)
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    status = str(state.get("status") or "")
    if status != "running":
        return state
    pid = state.get("pid")
    if not isinstance(pid, int):
        return write_agent_run_state(project_root, task, driver, "failed", failure_reason="running state missing pid", paths=paths)
    command = json_read(paths["command"])
    started_at = str(state.get("started_at") or _core_common_clock.now_utc())
    exit_marker = json_read(paths["exit"])
    if exit_marker:
        marker_status = str(exit_marker.get("status") or "")
        marker_exit_code = exit_marker.get("exit_code")
        exit_code = marker_exit_code if isinstance(marker_exit_code, int) else None
        if marker_status not in AGENT_RUN_STATUSES or marker_status in {"planned", "ready", "starting", "running", "blocked", "manual_required"}:
            marker_status = "completed" if exit_code == 0 else "failed"
        finished_at = str(exit_marker.get("finished_at") or _core_common_clock.now_utc())
        failure_reason = str(exit_marker.get("failure_reason") or "") or None
        state = write_agent_run_state(project_root, task, driver, marker_status, pid=pid, started_at=started_at, finished_at=finished_at, exit_code=exit_code, failure_reason=failure_reason, command=command, paths=paths)
        _core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES.pop(_core_runtime_observation_inputs.worker_process_key(project_root, run_id, task_id), None)
        _process_event_recorder.emit_process_event(project_root, "worker.run.finished", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": marker_status, "exit_code": exit_code}, correlation_id=f"run-{run_id}")
        return state
    started_dt = _worker_observation_inputs.parse_runtime_timestamp(started_at)
    timeout_seconds = int(state.get("timeout_seconds") or ((command.get("limits") if isinstance(command.get("limits"), dict) else {}).get("timeout_seconds") or 30))
    timed_out = bool(started_dt and datetime.now(timezone.utc) > started_dt + timedelta(seconds=timeout_seconds))
    proc = _core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES.get(_core_runtime_observation_inputs.worker_process_key(project_root, run_id, task_id))
    exit_code: int | None = proc.poll() if proc else None
    if timed_out and exit_code is None:
        if proc and proc.poll() is None:
            proc.kill()
        else:
            terminate_worker_pid(pid)
        finished_at = _core_common_clock.now_utc()
        state = write_agent_run_state(project_root, task, driver, "timed_out", pid=pid, started_at=started_at, finished_at=finished_at, exit_code=-1, failure_reason="timeout", command=command, paths=paths)
        _core_common_json_io.json_write(paths["exit"], {"schema_version": 1, "exit_code": -1, "finished_at": finished_at, "status": "timed_out"})
        return state
    if exit_code is None:
        if proc is None and not _worker_observation_inputs.process_pid_running(pid):
            lost_observed_at = _worker_observation_inputs.parse_runtime_timestamp(state.get("lost_observed_at"))
            if lost_observed_at is None:
                observed_at = _core_common_clock.now_utc()
                state = write_agent_run_state(project_root, task, driver, "running", pid=pid, started_at=started_at, failure_reason="pid not alive; waiting for durable exit contract", command=command, paths=paths)
                state["lost_observed_at"] = observed_at
                _core_common_json_io.json_write(paths["status"], state)
                return state
            if datetime.now(timezone.utc) < lost_observed_at + timedelta(seconds=0.25):
                return state
            finished_at = _core_common_clock.now_utc()
            failure_reason = "process exited without durable exit contract"
            state = write_agent_run_state(project_root, task, driver, "unknown_exit", pid=pid, started_at=started_at, finished_at=finished_at, exit_code=None, failure_reason=failure_reason, command=command, paths=paths)
            _core_common_json_io.json_write(paths["exit"], {"schema_version": 1, "exit_code": None, "finished_at": finished_at, "status": "unknown_exit", "failure_reason": failure_reason})
            _process_event_recorder.emit_process_event(project_root, "worker.run.finished", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": "unknown_exit", "exit_code": None, "failure_reason": failure_reason}, correlation_id=f"run-{run_id}")
            return state
        else:
            return write_agent_run_state(project_root, task, driver, "running", pid=pid, started_at=started_at, command=command, paths=paths)
    finished_at = _core_common_clock.now_utc()
    final_status = "completed" if exit_code == 0 else "failed"
    state = write_agent_run_state(project_root, task, driver, final_status, pid=pid, started_at=started_at, finished_at=finished_at, exit_code=exit_code, command=command, paths=paths)
    _core_common_json_io.json_write(paths["exit"], {"schema_version": 1, "exit_code": exit_code, "finished_at": finished_at, "status": final_status})
    _core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES.pop(_core_runtime_observation_inputs.worker_process_key(project_root, run_id, task_id), None)
    _process_event_recorder.emit_process_event(project_root, "worker.run.finished", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": final_status, "exit_code": exit_code}, correlation_id=f"run-{run_id}")
    return state




def prepare_worker_run(project_root: Path, task_id: str, driver_arg: str | None = None, executable_override: str | None = None, model_arg: str | None = None, reasoning_effort_arg: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    task = _worker_assignment_service.load(project_root, task_id)
    if _worker_observation_inputs.worker_run_work_is_terminal(project_root, task):
        raise SystemExit("FAIL: work_is_terminal")
    agent_model = _context_contract_inputs.normalize_agent_model(model_arg or task.get("agent_model") or task.get("model") or "")
    agent_reasoning_effort = _context_contract_inputs.normalize_agent_reasoning_effort(reasoning_effort_arg or task.get("agent_reasoning_effort") or task.get("reasoning_effort") or "")
    if agent_model and task.get("agent_model") != agent_model:
        task["agent_model"] = agent_model
        save_task(project_root, task)
    if agent_reasoning_effort and task.get("agent_reasoning_effort") != agent_reasoning_effort:
        task["agent_reasoning_effort"] = agent_reasoning_effort
        save_task(project_root, task)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    capsule_status, capsule_rel = existing_capsule_status(project_root, task_id)
    if capsule_status in {"fresh", "legacy"}:
        suffix = " (legacy capsule without assignment checksum)" if capsule_status == "legacy" else ""
        print(f"PRESENT: {capsule_rel}{suffix}")
    elif capsule_status == "stale":
        raise SystemExit(f"FAIL: assignment capsule is stale for {task_id}: {capsule_rel}; create_successor_work; immutable contexts cannot be rebuilt in place")
    else:
        status, output = run_command_capture(
            command_assignment_capsule,
            argparse.Namespace(
                project_root=str(project_root),
                assignment=str(_work_paths.assignment_document(project_root, task_id)),
                force=_context_contract_inputs.assignment_allows_write_scope_overlap(task),
            ),
        )
        print(output, end="")
        if status:
            raise SystemExit(status)
    task = _worker_assignment_service.load(project_root, task_id)
    from processforge_core.work.context import validate_execution_contract
    prepared_capsule = load_yaml_document(assignment_capsule_path(project_root, task_id))
    validation = validate_execution_contract(project_root, _work_paths.assignment_document(project_root, task_id), task,
                                             prepared_capsule, sys.modules[__name__], require_ready=True)
    if validation["status"] != "valid":
        raise SystemExit("FAIL: " + str(validation.get("reason") or "execution_contract_invalid") + "; create_successor_work")
    driver = _runtime_driver_selection_service.for_task(project_root, task, driver_arg)
    start_failures = [
        item.message
        for item in _runtime_driver_definition_policy.validate(driver, executable_override, include_start_readiness=True)
        if item.level == "FAIL"
    ]
    if start_failures:
        raise SystemExit("FAIL: runtime driver is not start-ready: " + "; ".join(start_failures))
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    previous_state = json_read(paths["status"])
    try:
        attempt = max(1, int(previous_state.get("attempt") or 0) + 1)
    except (TypeError, ValueError):
        attempt = 1
    import processforge_core.prepared.input as prepared_input
    # A failed prepare may have left a manifest but no ready state. Never
    # overwrite it or reuse its identity on the next deliberate attempt.
    attempt_root = paths["root"] / "attempts"
    if attempt_root.is_dir():
        attempt = max([attempt, *[int(item.name) + 1 for item in attempt_root.iterdir() if item.name.isdigit()]])
    prepared_path = attempt_root / str(attempt) / "prepared-input.json"
    try:
        document = prepared_input.build(project_root, task, prepared_capsule, attempt, sys.modules[__name__])
        reference = {"path": rel(prepared_path, project_root), "checksum": prepared_input.digest(prepared_input.encoded(document))}
        command, paths = _worker_command_builder.build(project_root, task, driver, executable_override, attempt=attempt, prepared_input=reference)
        prepared_input.private_file(project_root, reference["path"])
        prepared_input.write_once(prepared_path, document)
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit("FAIL: worker preparation blocked: " + str(exc)) from exc
    _core_common_json_io.json_write(paths["workspace_access"], document["input"]["resources"])
    prompt_path = _work_paths.worker_prompt(project_root, run_id, task_id)
    prepared_input.local_file(project_root, rel(prompt_path, project_root))
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(_worker_assignment_service.render_prompt(project_root, task_id, prepared_input=reference), encoding="utf-8")
    state_status = "manual_required" if str(driver.get("kind")) == "manual" else "ready"
    paths["root"].mkdir(parents=True, exist_ok=True)
    # A deliberate prepare is a new attempt.  An old durable exit contract
    # belongs to the preceding attempt and must not be observed as the result
    # of a newly launched process.
    paths["exit"].unlink(missing_ok=True)
    write_agent_run_state(project_root, task, driver, state_status, command=command, paths=paths, attempt=attempt)
    _process_event_recorder.emit_process_event(project_root, "worker.run.prepared", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": state_status, "attempt": attempt}, correlation_id=f"run-{run_id}")
    diagnostics.annotate(run_id=run_id, assignment_id=task_id, attempt=attempt)
    diagnostics.emit("info", "worker.prepared", {"driver_id": driver.get("id"), "status": state_status}, component="worker")
    return task, driver, paths


def command_worker_run_prepare(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    with worker_run_lifecycle_lock(project_root, run_id, task_id):
        task = _worker_assignment_service.load(project_root, task_id)
        if any(not intent.with_suffix(".applied.json").is_file() for intent in
               (locate_flow_root(project_root) / "runs" / run_id).glob("cancellation-*.yaml")):
            print("FAIL: cancellation_recovery_pending")
            return 1
        if _worker_observation_inputs.worker_run_work_is_terminal(project_root, task):
            print("FAIL: work_is_terminal")
            return 1
        running = existing_running_worker_run(project_root, task, getattr(args, "driver", None))
        if running:
            state, driver, paths = running
            emit_worker_run_skip(project_root, task, driver, state, "worker.run.prepare_skipped")
            print(f"SKIPPED: {task_id} already running pid={state.get('pid')}")
            return 0
        task, driver, paths = prepare_worker_run(project_root, task_id, getattr(args, "driver", None), getattr(args, "executable", None), getattr(args, "model", None), getattr(args, "reasoning_effort", None))
    print(f"PREPARED: {task_id} driver={driver.get('id')} status={json_read(paths['status']).get('status')}")
    return 0


def command_worker_run_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    detach = bool(getattr(args, "detach", False))
    proc: subprocess.Popen[bytes] | None = None
    with worker_run_lifecycle_lock(project_root, run_id, task_id):
        task = _worker_assignment_service.load(project_root, task_id)
        if any(not intent.with_suffix(".applied.json").is_file() for intent in
               (locate_flow_root(project_root) / "runs" / run_id).glob("cancellation-*.yaml")):
            print("FAIL: cancellation_recovery_pending")
            return 1
        if _worker_observation_inputs.worker_run_work_is_terminal(project_root, task):
            print("FAIL: work_is_terminal")
            return 1
        running = existing_running_worker_run(project_root, task, getattr(args, "driver", None))
        if running:
            state, driver, paths = running
            emit_worker_run_skip(project_root, task, driver, state, "worker.run.start_skipped")
            print(f"SKIPPED: {task_id} already running pid={state.get('pid')}")
            return 0
        state = load_agent_run_state(project_root, run_id, task_id)
        if state.get("status") == "blocked" and state.get("prepared_input"):
            print("FAIL: prepared attempt is blocked; use explicit worker-run prepare after repair")
            return 1
        if state.get("status") in {"ready", "manual_required"}:
            paths = _work_paths.worker_run(project_root, run_id, task_id)
            saved = json_read(paths["command"])
            driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state)
            requested_driver = getattr(args, "driver", None)
            if requested_driver and _runtime_driver_selection_service.for_task(project_root, task, requested_driver).get("id") != saved.get("driver_id"):
                print("FAIL: prepared driver differs; use explicit worker-run prepare")
                return 1
            for option, field in (("model", "agent_model"), ("reasoning_effort", "agent_reasoning_effort"), ("executable", "executable_override")):
                value = getattr(args, option, None)
                if value is not None and value != saved.get(field):
                    print("FAIL: prepared launch preference differs; use explicit worker-run prepare")
                    return 1
            if saved.get("prepared_input") != state.get("prepared_input") or str(saved.get("attempt")) != str(state.get("attempt")):
                print("FAIL: prepared command and state identity mismatch")
                return 1
            for key, relative in saved.get("paths", {}).items():
                if key in paths and key != "root":
                    paths[key] = project_root / relative
        else:
            task, driver, paths = prepare_worker_run(project_root, task_id, getattr(args, "driver", None), getattr(args, "executable", None), getattr(args, "model", None), getattr(args, "reasoning_effort", None))
        run_id = safe_id(str(task.get("run_id") or "run"), "run")
        command = json_read(paths["command"])
        import processforge_core.prepared.input as prepared_input
        try:
            prepared_input.load(project_root, task, command, sys.modules[__name__])
        except (OSError, ValueError, RuntimeError) as exc:
            write_agent_run_state(project_root, task, driver, "blocked", failure_reason=str(exc), command=command, paths=paths)
            print("FAIL: prepared launch blocked: " + str(exc))
            return 1
        if str(driver.get("kind")) == "manual":
            print(f"MANUAL: {task_id} prepared at {rel(paths['status'], project_root)}")
            return 0
        argv = command.get("command", {}).get("argv") if isinstance(command.get("command"), dict) else []
        if not argv:
            write_agent_run_state(project_root, task, driver, "failed", failure_reason="empty argv", command=command, paths=paths)
            print(f"FAIL: empty command argv for {task_id}")
            return 1
        timeout_seconds = int((command.get("limits") if isinstance(command.get("limits"), dict) else {}).get("timeout_seconds") or 30)
        command_spec = command.get("command") if isinstance(command.get("command"), dict) else {}
        env = _worker_environment_policy.materialize(command_spec)
        cwd = command_spec.get("working_directory") or str(project_root)
        paths["stdout"].parent.mkdir(parents=True, exist_ok=True)
        paths["stderr"].parent.mkdir(parents=True, exist_ok=True)
        started_at = _core_common_clock.now_utc()
        with paths["stdout"].open("wb") as stdout, paths["stderr"].open("wb") as stderr:
            try:
                proc = subprocess.Popen([str(item) for item in argv], cwd=str(cwd), env=env, stdout=stdout, stderr=stderr, shell=False)
            except OSError as exc:
                finished_at = _core_common_clock.now_utc()
                write_agent_run_state(project_root, task, driver, "failed", started_at=started_at, finished_at=finished_at, exit_code=None, failure_reason=str(exc), command=command, paths=paths)
                print(f"FAIL: start failed for {task_id}: {exc}")
                return 1
        write_agent_run_state(project_root, task, driver, "running", pid=proc.pid, started_at=started_at, command=command, paths=paths)
        _core_common_json_io.json_write(paths["process"], {"schema_version": 1, "pid": proc.pid, "started_at": started_at, "argv": argv})
        if detach:
            _core_runtime_observation_inputs.DETACHED_WORKER_PROCESSES[_core_runtime_observation_inputs.worker_process_key(project_root, run_id, task_id)] = proc
            _process_event_recorder.emit_process_event(project_root, "worker.run.started", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": "running", "pid": proc.pid}, correlation_id=f"run-{run_id}")
            print(f"RUNNING: {task_id} pid={proc.pid}")
            return 0
    assert proc is not None
    try:
        exit_code = proc.wait(timeout=timeout_seconds)
        finished_at = _core_common_clock.now_utc()
        final_status = "completed" if exit_code == 0 else "failed"
        write_agent_run_state(project_root, task, driver, final_status, pid=proc.pid, started_at=started_at, finished_at=finished_at, exit_code=exit_code, command=command, paths=paths)
        _core_common_json_io.json_write(paths["exit"], {"schema_version": 1, "exit_code": exit_code, "finished_at": finished_at, "status": final_status})
    except subprocess.TimeoutExpired:
        proc.kill()
        exit_code = -1
        final_status = "timed_out"
        finished_at = _core_common_clock.now_utc()
        write_agent_run_state(project_root, task, driver, final_status, pid=proc.pid, started_at=started_at, finished_at=finished_at, exit_code=exit_code, failure_reason="timeout", command=command, paths=paths)
        _core_common_json_io.json_write(paths["exit"], {"schema_version": 1, "exit_code": exit_code, "finished_at": finished_at, "status": final_status})
    _process_event_recorder.emit_process_event(project_root, "worker.run.finished", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "driver_id": driver.get("id"), "status": final_status, "exit_code": exit_code}, correlation_id=f"run-{run_id}")
    print(f"{final_status.upper()}: {task_id} exit_code={exit_code}")
    return 0 if final_status == "completed" else 1


def command_worker_run_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    with worker_run_lifecycle_lock(project_root, run_id, task_id):
        state = load_agent_run_state(project_root, run_id, task_id)
        if state and _worker_observation_inputs.worker_run_state_requires_reconciliation(project_root, run_id, task_id, state):
            driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state)
            state = observe_worker_run(project_root, task, driver, state)
    if not state:
        print(f"STATUS: not-prepared {task_id}")
        return 1
    print(dump_yaml(state))
    return 0


def command_worker_run_stop(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    state = load_agent_run_state(project_root, run_id, task_id)
    if not state:
        print(f"STATUS: not-prepared {task_id}")
        return 1
    pid = state.get("pid")
    if pid and state.get("status") == "running":
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(int(pid), signal.SIGTERM)
    driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state)
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    if state.get("status") in {"completed", "failed", "timed_out", "unknown_exit", "lost", "cancelled"}:
        print(f"STATUS: already-terminal {task_id} status={state.get('status')}")
        return 0
    write_agent_run_state(project_root, task, driver, "cancelled", pid=pid if isinstance(pid, int) else None, finished_at=_core_common_clock.now_utc(), failure_reason="stop requested", paths=paths)
    print(f"STOPPED: {task_id}")
    return 0


def command_worker_run_collect(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    with worker_run_lifecycle_lock(project_root, run_id, task_id):
        return _collect_worker_run_locked(project_root, _worker_assignment_service.load(project_root, task_id))


def _collect_worker_run_locked(project_root: Path, task: dict[str, Any]) -> int:
    task_id, run_id = task["id"], task["run_id"]
    state = load_agent_run_state(project_root, run_id, task_id)
    if state and _worker_observation_inputs.worker_run_state_requires_reconciliation(project_root, run_id, task_id, state):
        driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state)
        state = observe_worker_run(project_root, task, driver, state)
    if not state:
        print(f"FAIL: worker run is not prepared: {task_id}")
        return 1
    if state.get("status") not in {"completed", "manual_required"}:
        print(f"FAIL: worker run is not collectible: {task_id} status={state.get('status', 'unknown')}")
        return 1
    missing: list[str] = []
    for output in _context_contract_inputs.normalize_required_outputs(task.get("required_outputs")):
        if not bool(output.get("required", True)):
            continue
        raw_path = output.get("path") if isinstance(output, dict) else ""
        out_path = _work_output_policy.task_path(project_root, output)
        if out_path is None or not out_path.is_file():
            missing.append(_context_contract_inputs.normalize_assignment_path(str(raw_path)))
    try:
        report_path = _work_output_policy.path(project_root, _work_output_policy.expected_report(task))
    except (OSError, ValueError) as exc:
        print(f"FAIL: invalid expected report path: {exc}")
        return 1
    if not report_path.is_file():
        missing.append(_work_output_policy.expected_report(task))
    paths = _work_paths.worker_run(project_root, run_id, task_id)
    lines = [
        f"# Worker Run Collection: {task_id}",
        "",
        f"- status: `{state.get('status', 'unknown')}`",
        f"- expected_report: `{_work_output_policy.expected_report(task)}`",
        f"- missing_outputs: `{len(missing)}`",
    ]
    for item in missing:
        lines.append(f"- missing: `{item}`")
    subagent_failures = _worker_plan_validation_service.subagent_outputs(project_root, task)
    lines.append(f"- subagent_policy_failures: `{len(subagent_failures)}`")
    for item in subagent_failures:
        lines.append(f"- subagent_policy_failure: `{item}`")
    paths["collection"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    if missing or subagent_failures:
        driver = _runtime_driver_selection_service.for_worker_state(project_root, task, state)
        reasons = []
        if missing:
            reasons.append("missing outputs: " + ", ".join(missing))
        if subagent_failures:
            reasons.append("subagent policy failures: " + "; ".join(subagent_failures))
        write_agent_run_state(project_root, task, driver, "failed", failure_reason="; ".join(reasons), paths=paths)
        print("FAIL: " + "; ".join(reasons))
        return 1
    import processforge_core.prepared.input as prepared_input
    try:
        report_raw = prepared_input.bounded_read(report_path, 2 * 1024 * 1024)
        report_content = report_raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        receipt_path, receipt = prepared_input.collection_receipt(project_root, task, state, sys.modules[__name__])
        report_record = next(item for item in receipt["outputs"] if item["path"] == _work_output_policy.expected_report(task))
        if prepared_input.digest(report_raw) != report_record["checksum"]:
            raise ValueError("collected_output_changed")
    except (OSError, ValueError, RuntimeError) as exc:
        from processforge_core.prepared.collection import CollectionRecoveryStore

        # Only a proved semantic refusal may suspend automatic retries. This
        # optional historical record never replaces the full checks above.
        if CollectionRecoveryStore(project_root).record(task, state, run_id=run_id, error=exc):
            print(f"RECOVERY-REQUIRED: {task_id}; explicit collect or a new prepared attempt is required")
        print("FAIL: collection blocked: " + str(exc))
        return 1
    completion_path = receipt_path.with_name("collection-complete.json")
    try:
        prepared_input.private_file(project_root, rel(completion_path, project_root))
    except (OSError, ValueError, RuntimeError) as exc:
        print("FAIL: collection completion path invalid: " + str(exc))
        return 1
    if completion_path.is_file():
        if json_read(completion_path).get("receipt_id") != receipt["receipt_id"]:
            print("FAIL: collection completion identity mismatch")
            return 1
        print(f"COLLECTED: {task_id} already collected for attempt {state['attempt']}")
        return 0
    report_hash = sha256_text(report_content)
    attempt = str(state.get("attempt") or 1)
    expected_report = _work_output_policy.expected_report(task)
    session_id = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"
    envelope = {
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerExpectedReportCaptured",
        "native_event_id": f"worker-output:{run_id}:{task_id}:attempt:{attempt}:{report_hash}",
        "native_id_scope": "project",
        "native_event_id_stable": True,
        "source_session_id": session_id,
        "source_project_ref": str(project_root),
        "payload_version": "1",
        "raw_payload": {
            "run_id": run_id,
            "task_id": task_id,
            "attempt": attempt,
            "expected_report": expected_report,
            "report_content": report_content,
            "report_hash": report_hash,
        },
        "derived_conversation_messages": [{
            "message_role": "assistant",
            "participant": {"id": str(task.get("ownership", {}).get("owner_id") or "worker"), "type": "agent", "role": "worker"},
            "session_id": session_id,
            "turn_id": f"worker-turn:{run_id}:{task_id}:attempt:{attempt}",
            "content": report_content,
            "content_source": {"kind": "pf_codex_exec_output", "provider": "processforge", "adapter": "pf-codex-exec-worker", "native_event_type": "WorkerExpectedReportCaptured", "content_provenance": "pf_owned_output_file"},
            "delivery": {"state": "complete", "sequence": 1, "final": True},
        }],
    }
    from pf_runtime import host as runtime_host
    capture = runtime_host.ingest_event(envelope, None, sys.modules[__name__])
    if not capture.get("accepted") or len(capture.get("chat_message_ids") or []) != 1:
        print("FAIL: collectible expected report was not captured as exactly one assistant transcript message")
        return 1
    # A governed primary Work still has stage obligations. Worker delivery is
    # evidence for those transitions, never a compatibility completion bypass.
    run = load_yaml_document(_work_paths.run_root(project_root, run_id) / "run.yaml")
    governed = "process_execution" in run or "process_execution" in task
    status = 0
    if not governed:
        status, output = run_command_capture(command_task_complete, argparse.Namespace(project_root=str(project_root), task=task_id, summary=f"Collected worker run output from {state.get('driver_id')}", artifact=[_work_output_policy.expected_report(task)], dry_run=False, completion_id=receipt["receipt_id"]))
        print(output, end="")
        if status:
            return status
    emit_worker_completion_event(project_root, "worker.run.collected", receipt["receipt_id"], process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "report": _work_output_policy.expected_report(task), "receipt_id": receipt["receipt_id"], "attempt": state["attempt"]}, correlation_id=f"run-{run_id}")
    prepared_input.write_once(completion_path, {"schema_version": 1, "receipt_id": receipt["receipt_id"]})
    if governed:
        print(f"COLLECTED: {task_id}; governed stage transition remains required")
    return status


def emit_worker_completion_event(project_root: Path, event_type: str, receipt_id: str, **kwargs: Any) -> dict[str, Any]:
    event_id = "evt_" + hashlib.sha256((receipt_id + ":" + event_type).encode("utf-8")).hexdigest()
    path = _run_task_inputs.event_runtime_paths(project_root)[0]
    if _process_event_journal.contains(path, event_id):
        event = _process_event_journal.get(path, event_id) or _telemetry_event_service.processforge_event(project_root, event_type, event_id=event_id, **kwargs)
        _process_event_recorder.admit_process_event(project_root, event)
        return event
    return _process_event_recorder.emit_process_event(project_root, event_type, event_id=event_id, **kwargs)


def sync_failed_worker_lifecycle(project_root: Path, task: dict[str, Any], state: dict[str, Any]) -> None:
    task_id = safe_id(str(task.get("id") or state.get("task_id") or "task"), "task")
    run_id = safe_id(str(task.get("run_id") or state.get("run_id") or "run"), "run")
    if str(task.get("status")) in {"done", "completed", "failed", "cancelled"}:
        return
    run_path = _work_paths.run_root(project_root, run_id) / "run.yaml"
    if "process_execution" in task or (run_path.is_file() and "process_execution" in load_yaml_document(run_path)):
        return
    runtime_status = str(state.get("status") or "failed")
    failure_reason = str(state.get("failure_reason") or runtime_status)
    task["status"] = "failed"
    task["result"] = {
        # Assignment result is a semantic delivery outcome; the more granular
        # Inspector runtime status belongs in its durable agent-run record.
        "status": "failed",
        "summary": f"Worker runtime ended with {runtime_status}: {failure_reason}",
        "artifacts": [],
    }
    save_task(project_root, task)
    update_run_task_status(project_root, run_id, task_id, "failed")
    _process_event_recorder.emit_process_event(project_root, "task.failed", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": run_id, "task_id": task_id, "runtime_status": runtime_status, "failure_reason": failure_reason}, correlation_id=f"run-{run_id}")


















def historical_worker_capture(project_root: Path, run_id: str, task_id: str) -> bool:
    from processforge_core.prepared.collection import CapturedAttemptReader

    try:
        with worker_run_lifecycle_lock(project_root, run_id, task_id):
            task = _worker_assignment_service.load(project_root, task_id)
            state = load_agent_run_state(project_root, run_id, task_id)
            return CapturedAttemptReader(project_root).read(task, state, run_id=run_id) is not None
    except (OSError, ValueError, RuntimeError, SystemExit):
        # This optional observation cannot turn a failed/missing proof into a
        # collected result. The ordinary collect path retains its own failures.
        return False


def worker_collection_recovery_required(project_root: Path, run_id: str, task_id: str) -> dict[str, str] | None:
    from processforge_core.prepared.collection import CollectionRecoveryStore

    try:
        with worker_run_lifecycle_lock(project_root, run_id, task_id):
            task = _worker_assignment_service.load(project_root, task_id)
            state = load_agent_run_state(project_root, run_id, task_id)
            observation = CollectionRecoveryStore(project_root).read(task, state, run_id=run_id)
            return ({"task_id": task_id, "attempt": str(observation.attempt), "reason": observation.reason}
                    if observation is not None else None)
    except (OSError, ValueError, RuntimeError, SystemExit):
        # Unavailable proof retains the ordinary collect path and its errors.
        return None


def supervisor_pending_drain_task_ids(project_root: Path, run_ids: list[str]) -> list[str]:
    pending: list[str] = []
    for run_id in run_ids:
        run = load_run(project_root, run_id)
        for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
            if not isinstance(item, dict):
                continue
            task_id = safe_id(str(item.get("id") or "task"), "task")
            state = load_agent_run_state(project_root, run_id, task_id)
            status = str(state.get("status") or "")
            task_status = str(item.get("status") or "")
            if status == "running" or (status == "completed" and task_status not in {"done", "completed"}
                                       and not historical_worker_capture(project_root, run_id, task_id)):
                pending.append(task_id)
    return sorted(set(pending))


def supervisor_final_drain_timeout(project_root: Path, run_ids: list[str], explicit_timeout: float | None = None) -> float:
    if explicit_timeout is not None:
        return max(0.0, float(explicit_timeout))
    worker_timeouts: list[int] = []
    for run_id in run_ids:
        run = load_run(project_root, run_id)
        for item in run.get("tasks", []) if isinstance(run.get("tasks"), list) else []:
            if not isinstance(item, dict):
                continue
            task_id = safe_id(str(item.get("id") or "task"), "task")
            state = load_agent_run_state(project_root, run_id, task_id)
            if str(state.get("status") or "") == "running":
                timeout_seconds = state.get("timeout_seconds")
                if isinstance(timeout_seconds, int) and timeout_seconds > 0:
                    worker_timeouts.append(timeout_seconds)
    return max(1.0, min(float(min(worker_timeouts) if worker_timeouts else 5), 5.0))


def command_supervisor_tick(args: argparse.Namespace) -> int:
    result = supervisor_tick_result(args)
    return 1 if result["failed"] else 0


def supervisor_tick_result(args: argparse.Namespace) -> dict[str, Any]:
    """Observe one pass, retaining task outcomes separately from execution errors."""
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    profile = _supervisor_input_service.load_supervisor_profile(project_root, getattr(args, "profile", None))
    run_ids = [safe_id(args.run, "run")] if getattr(args, "run", None) else _run_task_inputs.active_run_ids(project_root)
    started: list[str] = []
    collected: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    running: list[str] = []
    observed: list[str] = []
    historical_observed: list[str] = []
    recovery_required: list[dict[str, str]] = []
    blocked_overlap: list[str] = []
    scheduling = profile.get("scheduling") if isinstance(profile.get("scheduling"), dict) else {}
    defaults = profile.get("defaults") if isinstance(profile.get("defaults"), dict) else {}
    max_parallel = int(scheduling.get("max_parallel_workers") or defaults.get("max_parallel_workers") or 1)
    start_allowed = bool(getattr(args, "start_allowed", True))
    scope_conflicts = ScopeConflictService(project_root)
    running_scopes: dict[str, list[str]] = {}
    for run_id in run_ids:
        run = load_run(project_root, run_id)
        plan = _supervisor_state_inputs.load_run_plan_if_present(project_root, run_id)
        runtime = plan.get("runtime") if isinstance(plan.get("runtime"), dict) else {}
        workers = _worker_plan_policy.worker_map(plan)
        run_max_parallel = int(runtime.get("max_parallel_workers") or max_parallel)
        allow_write_scope_overlap = _worker_plan_policy.allows_write_scope_overlap(plan)
        default_driver = getattr(args, "driver", None) or str(runtime.get("default_driver") or scheduling.get("default_driver") or defaults.get("runtime_driver") or "manual")
        tasks = sorted([entry for entry in run.get("tasks", []) if isinstance(entry, dict)], key=lambda value: int(value.get("order", 0) or 0))
        task_rows: list[tuple[str, dict[str, Any], dict[str, Any] | None, str]] = []
        for item in tasks:
            task_id = safe_id(str(item.get("id") or "task"), "task")
            task = _worker_assignment_service.load(project_root, task_id)
            worker = workers.get(task_id)
            state = load_agent_run_state(project_root, run_id, task_id)
            # A prepared run records the concrete driver as durable Inspector
            # state.  A supervisor must observe that driver, not fall back to
            # its run default (commonly `manual`), otherwise it can rewrite a
            # shell worker's timeout and lifecycle while the process is live.
            driver_id = str(state.get("driver_id") or (worker or {}).get("runtime_driver") or task.get("runtime_driver") or default_driver)
            task_rows.append((task_id, task, worker, driver_id))
            if state.get("status") == "running":
                observed_state = observe_worker_run(project_root, task, driver_id, state)
                observed.append(task_id)
                if observed_state.get("status") == "running":
                    running.append(task_id)
                    running_scopes[task_id] = _context_contract_inputs.assignment_write_scope(task)
                elif observed_state.get("status") == "completed" and str(task.get("status")) not in {"done", "completed"}:
                    if historical_worker_capture(project_root, run_id, task_id):
                        historical_observed.append(task_id)
                    elif recovery := worker_collection_recovery_required(project_root, run_id, task_id):
                        recovery_required.append(recovery)
                        failed.append(task_id)
                    else:
                        status = command_worker_run_collect(argparse.Namespace(project_root=str(project_root), task=task_id))
                        if status == 0:
                            collected.append(task_id)
                        else:
                            failed.append(task_id)
                            if recovery := worker_collection_recovery_required(project_root, run_id, task_id):
                                recovery_required.append(recovery)
                elif observed_state.get("status") in AGENT_RUN_FAILURE_TERMINAL_STATUSES:
                    sync_failed_worker_lifecycle(project_root, task, observed_state)
                    failed.append(task_id)
            elif state.get("status") == "completed" and str(task.get("status")) not in {"done", "completed"}:
                if historical_worker_capture(project_root, run_id, task_id):
                    observed.append(task_id)
                    historical_observed.append(task_id)
                elif recovery := worker_collection_recovery_required(project_root, run_id, task_id):
                    observed.append(task_id)
                    recovery_required.append(recovery)
                    failed.append(task_id)
                else:
                    status = command_worker_run_collect(argparse.Namespace(project_root=str(project_root), task=task_id))
                    if status == 0:
                        collected.append(task_id)
                    else:
                        failed.append(task_id)
                        if recovery := worker_collection_recovery_required(project_root, run_id, task_id):
                            recovery_required.append(recovery)
            elif state.get("status") in AGENT_RUN_FAILURE_TERMINAL_STATUSES:
                sync_failed_worker_lifecycle(project_root, task, state)
                failed.append(task_id)
        if not start_allowed:
            continue
        for task_id, task, worker, driver_id in task_rows:
            active_count = len(running) + len(started)
            if active_count >= run_max_parallel:
                break
            state = load_agent_run_state(project_root, run_id, task_id)
            if state.get("status") in AGENT_RUN_START_SKIP_STATUSES:
                continue
            if str(task.get("status")) not in {"open", "in_progress", "blocked"}:
                skipped.append(task_id)
                continue
            if not _worker_plan_policy.task_dependencies_done(project_root, task, worker):
                skipped.append(task_id)
                continue
            if driver_id == "manual":
                prepare_worker_run(project_root, task_id, driver_id, None)
                skipped.append(task_id)
                continue
            current_scope = _context_contract_inputs.assignment_write_scope(task)
            conflict = False
            if not allow_write_scope_overlap:
                for other_id, other_scope in running_scopes.items():
                    if scope_conflicts.conflicts(task_id, current_scope, other_id, other_scope, reason_prefix="supervisor_"):
                        conflict = True
                        break
            if conflict:
                blocked_overlap.append(task_id)
                skipped.append(task_id)
                continue
            try:
                status = command_worker_run_start(argparse.Namespace(project_root=str(project_root), task=task_id, driver=driver_id, executable=None, model=None, detach=True, wait=False))
            except SystemExit as exc:
                status = int(exc.code) if isinstance(exc.code, int) else 1
                print(exc)
            if status == 0:
                started.append(task_id)
                running_scopes[task_id] = current_scope
            else:
                failed.append(task_id)
    report = supervisor_root(project_root) / "last-tick-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Supervisor Tick Report",
                "",
                f"- checked_runs: `{len(run_ids)}`",
                f"- start_allowed: `{str(start_allowed).lower()}`",
                f"- started: `{', '.join(started) if started else 'none'}`",
                f"- running: `{', '.join(running) if running else 'none'}`",
                f"- observed: `{', '.join(observed) if observed else 'none'}`",
                f"- historical_observed: `{', '.join(historical_observed) if historical_observed else 'none'}`",
                f"- recovery_required: `{', '.join(item['task_id'] + ':attempt:' + item['attempt'] + ':' + item['reason'] for item in recovery_required) if recovery_required else 'none'}`",
                f"- collected: `{', '.join(collected) if collected else 'none'}`",
                f"- skipped: `{', '.join(skipped) if skipped else 'none'}`",
                f"- blocked_overlap: `{', '.join(blocked_overlap) if blocked_overlap else 'none'}`",
                f"- failed: `{', '.join(failed) if failed else 'none'}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = {"runs": run_ids, "start_allowed": start_allowed, "started": started, "running": running, "observed": observed, "historical_observed": historical_observed, "recovery_required": recovery_required, "collected": collected, "skipped": skipped, "blocked_overlap": blocked_overlap, "failed": failed, "report": rel(report, project_root)}
    _process_event_recorder.emit_process_event(project_root, "supervisor.tick.completed", process_id="process-supervisor", subject="supervisor", payload=result)
    for item in recovery_required:
        print(f"RECOVERY-REQUIRED: {item['task_id']} attempt={item['attempt']} reason={item['reason']}; explicit collect or a new prepared attempt is required")
    print(f"TICK: started={len(started)} running={len(running)} observed={len(observed)} collected={len(collected)} skipped={len(skipped)} failed={len(failed)}")
    print(f"WROTE: {rel(report, project_root)}")
    return result


def command_supervisor_run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    profile = _supervisor_input_service.load_supervisor_profile(project_root, getattr(args, "profile", None))
    loop = profile.get("loop") if isinstance(profile.get("loop"), dict) else {}
    interval_arg = getattr(args, "interval", None)
    max_ticks_arg = getattr(args, "max_ticks", None)
    interval = float(interval_arg if interval_arg is not None else (loop.get("interval_seconds") or 1))
    max_ticks = int(max_ticks_arg if max_ticks_arg is not None else (loop.get("max_ticks") or 1))
    run_ids = [safe_id(args.run, "run")] if getattr(args, "run", None) else _run_task_inputs.active_run_ids(project_root)
    final_drain_timeout = supervisor_final_drain_timeout(project_root, run_ids, getattr(args, "final_drain_timeout", None))
    drain_interval = min(max(interval if interval > 0 else 0.05, 0.05), 0.25)
    stop_file = project_root / ".pf" / "runtime" / "supervisor" / "stop.request"
    state = {"schema_version": 1, "id": "default", "status": "running", "project_root": ".", "pid": os.getpid(), "started_at": _core_common_clock.now_utc(), "updated_at": _core_common_clock.now_utc(), "stopped_at": None, "tick_count": 0, "drain_tick_count": 0, "final_drain_timeout_seconds": final_drain_timeout, "last_tick_report": ".pf/runtime/supervisor/last-tick-report.md", "stop_requested": False}
    _supervisor_state_inputs.write_supervisor_state(project_root, state)
    failed = False
    for index in range(max_ticks):
        if stop_file.is_file():
            state["stop_requested"] = True
            break
        tick_status = command_supervisor_tick(argparse.Namespace(project_root=str(project_root), run=getattr(args, "run", None), profile=getattr(args, "profile", None), driver=getattr(args, "driver", None)))
        failed = failed or tick_status != 0
        state["tick_count"] = index + 1
        _supervisor_state_inputs.write_supervisor_state(project_root, state)
        if failed:
            break
        if index + 1 < max_ticks:
            time.sleep(interval)
    drain_started_at = time.perf_counter()
    drain_ticks = 0
    pending = supervisor_pending_drain_task_ids(project_root, run_ids)
    while pending and final_drain_timeout > 0 and time.perf_counter() - drain_started_at <= final_drain_timeout:
        tick_status = command_supervisor_tick(argparse.Namespace(project_root=str(project_root), run=getattr(args, "run", None), profile=getattr(args, "profile", None), driver=getattr(args, "driver", None), start_allowed=False))
        failed = failed or tick_status != 0
        drain_ticks += 1
        state["drain_tick_count"] = drain_ticks
        _supervisor_state_inputs.write_supervisor_state(project_root, state)
        if failed:
            break
        pending = supervisor_pending_drain_task_ids(project_root, run_ids)
        if pending and time.perf_counter() - drain_started_at < final_drain_timeout:
            time.sleep(drain_interval)
    pending = supervisor_pending_drain_task_ids(project_root, run_ids)
    if pending:
        print(f"FINAL-DRAIN: pending={', '.join(pending)} timeout={final_drain_timeout:.2f}s")
    elif drain_ticks:
        print(f"FINAL-DRAIN: completed ticks={drain_ticks}")
    state["status"] = "stopped"
    state["stopped_at"] = _core_common_clock.now_utc()
    state["drain_tick_count"] = drain_ticks
    _supervisor_state_inputs.write_supervisor_state(project_root, state)
    print(f"SUPERVISOR: stopped ticks={state['tick_count']} drain_ticks={state['drain_tick_count']}")
    return 1 if failed else 0


def command_supervisor_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    state = json_read(_supervisor_state_inputs.supervisor_state_path(project_root))
    if not state:
        print("STATUS: not-started")
        return 1
    print(dump_yaml(state))
    return 0


def command_supervisor_stop(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    stop_file = supervisor_root(project_root) / "stop.request"
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    stop_file.write_text(_core_common_clock.now_utc() + "\n", encoding="utf-8")
    state = json_read(_supervisor_state_inputs.supervisor_state_path(project_root))
    if state:
        state["status"] = "stopping"
        state["stop_requested"] = True
        _supervisor_state_inputs.write_supervisor_state(project_root, state)
    print(f"STOP REQUESTED: {rel(stop_file, project_root)}")
    return 0


def command_runtime_serve(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_serve(args, sys.modules[__name__])


def command_runtime_start(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_start(args, sys.modules[__name__])


def command_runtime_stop(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_stop(args, sys.modules[__name__])


def command_runtime_restart(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_restart(args, sys.modules[__name__])


def command_runtime_monitor(args: argparse.Namespace) -> int:
    from pf_runtime import monitor

    return monitor.command_monitor(args, sys.modules[__name__])


def command_runtime_status(args: argparse.Namespace) -> int:
    if args.command == "server":
        args.once, args.ascii, args.no_color, args.interval = True, False, True, 2.0
        return command_runtime_monitor(args)
    from pf_runtime import service as runtime_service

    return runtime_service.command_status(args, sys.modules[__name__])


def command_runtime_doctor(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_doctor(args, sys.modules[__name__])


def command_runtime_event(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_event(args, sys.modules[__name__])


def command_runtime_session_register(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_session_register(args, sys.modules[__name__])


def command_runtime_project_state(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_project_state(args, sys.modules[__name__])


def command_runtime_work_state(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_work_state(args, sys.modules[__name__])


def command_runtime_resolve(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_resolve(args, sys.modules[__name__])


def command_runtime_tick(args: argparse.Namespace) -> int:
    from pf_runtime import service as runtime_service

    return runtime_service.command_tick(args, sys.modules[__name__])


def command_runtime_autostart_status(args: argparse.Namespace) -> int:
    from pf_runtime import windows_autostart

    return windows_autostart.command_status(args, sys.modules[__name__])


def command_runtime_autostart_install(args: argparse.Namespace) -> int:
    from pf_runtime import windows_autostart

    return windows_autostart.command_install(args, sys.modules[__name__])


def command_runtime_autostart_remove(args: argparse.Namespace) -> int:
    from pf_runtime import windows_autostart

    return windows_autostart.command_remove(args, sys.modules[__name__])


def command_codex_mcp_status(args: argparse.Namespace) -> int:
    from pf_runtime import codex_mcp

    return codex_mcp.command_status(args, sys.modules[__name__])


def command_codex_mcp_install(args: argparse.Namespace) -> int:
    from pf_runtime import codex_mcp

    return codex_mcp.command_install(args, sys.modules[__name__])


def command_codex_mcp_remove(args: argparse.Namespace) -> int:
    from pf_runtime import codex_mcp

    return codex_mcp.command_remove(args, sys.modules[__name__])


def command_runtime_host_init(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_init(args, sys.modules[__name__])


def command_runtime_host_event(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_event(args, sys.modules[__name__])


def command_runtime_host_status(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_status(args, sys.modules[__name__])


def command_runtime_host_project_state(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_project_state(args, sys.modules[__name__])


def command_runtime_host_work_state(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_work_state(args, sys.modules[__name__])


def command_runtime_host_resolve(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_resolve(args, sys.modules[__name__])


def command_runtime_host_tick(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_tick(args, sys.modules[__name__])


def command_runtime_host_rebuild_projections(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_rebuild_projections(args, sys.modules[__name__])


def command_runtime_host_projection_doctor(args: argparse.Namespace) -> int:
    from pf_runtime import host as runtime_host

    return runtime_host.command_projection_doctor(args, sys.modules[__name__])
























def write_orchestration_summary(project_root: Path, plan: dict[str, Any]) -> None:
    run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
    run_id = safe_id(str(run.get("id") or "run"), "run")
    workers = plan.get("workers") if isinstance(plan.get("workers"), list) else []
    summary = _work_paths.run_root(project_root, run_id) / "orchestration-summary.md"
    task_index = _work_paths.run_root(project_root, run_id) / "orchestration-task-index.md"
    handoff = locate_flow_root(project_root) / "handoffs" / "runs" / f"{run_id}-orchestrator-handoff.md"
    summary_lines = [f"# Orchestration Summary: {run.get('title', run_id)}", "", f"- run_id: `{run_id}`", "- process: `multi-agent-task-orchestration`", "", "## Workers", ""]
    index_lines = [f"# Orchestration Task Index: {run_id}", ""]
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        task_id = safe_id(str(worker.get("id") or "worker"), "worker")
        prompt_rel = rel(_work_paths.worker_prompt(project_root, run_id, task_id), project_root)
        capsule_rel = rel(locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml", project_root)
        summary_lines.append(f"- `{task_id}`: prompt `{prompt_rel}`, capsule `{capsule_rel}`")
        index_lines.append(f"- `{task_id}` -> `.pf/assignments/{task_id}.yaml`")
    handoff_text = f"""# Handoff: orchestrator -> integration/review

Objective:
Coordinate worker outputs for run `{run_id}`.

Current status:
Initial worker assignments, capsules, and launch prompts were generated.

Input artifacts:
- {rel(_orchestration_config_service.orchestrator_plan_path(project_root, run_id), project_root)}
- {rel(summary, project_root)}

Files changed:
- .pf/runs/{run_id}/
- .pf/assignments/
- .pf/contexts/assignment-capsules/

Files not to touch:
- Files outside each worker `allowed_files`.

Known issues:
- Worker outputs are pending.

Required checks:
- `python .pf/runtime/bin/pf.py run-doctor --project-root . --run {run_id}`
- `python .pf/runtime/bin/pf.py task-doctor --project-root . --task <task-id>`

Next recommended action:
Launch workers with the generated prompts, then integrate their required outputs.
"""
    summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    task_index.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(handoff_text, encoding="utf-8")








def materialize_plan_overlap_policy(project_root: Path, plan: dict[str, Any]) -> None:
    if not _worker_plan_policy.allows_write_scope_overlap(plan):
        return
    for worker in plan.get("workers", []) if isinstance(plan.get("workers"), list) else []:
        if not isinstance(worker, dict):
            continue
        task_id = safe_id(str(worker.get("id") or "worker"), "worker")
        path = _work_paths.assignment_document(project_root, task_id)
        if not path.is_file():
            continue
        task = _worker_assignment_service.load(project_root, task_id)
        overlap_check = overlap_allowed_check(validate_assignment_scope_overlaps(project_root, task, assignment_path=path), "plan.allow_write_scope_overlap")
        non_overlap = task.get("non_overlap") if isinstance(task.get("non_overlap"), dict) else {}
        non_overlap.update(
            {
                "policy": "allow_write_scope_overlap",
                "overlap_policy": "allow",
                "overlap_policy_source": "plan.allow_write_scope_overlap",
                "current_write_scope": _context_contract_inputs.assignment_write_scope(task),
                "rule": "Write scope overlap is allowed for workers in this resolved plan.",
                "overlap_check": overlap_check,
            }
        )
        task["non_overlap"] = non_overlap
        save_task(project_root, task)


def command_orchestrator_plan_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    run_id = safe_id(args.run, "run")
    path = _orchestration_config_service.orchestrator_plan_path(project_root, run_id)
    plan = _AnswersDocumentReader().read(Path(args.answers).expanduser().resolve() if args.answers else None) if args.answers else _worker_plan_policy.default_task_plan(run_id, args.title)
    if not plan.get("run"):
        plan["run"] = {"id": run_id, "title": args.title, "process": "multi-agent-task-orchestration"}
    if not args.apply or getattr(args, "dry_run", False):
        print_plan("orchestrator-plan create dry run", [path], project_root)
        return 0
    _core_common_yaml_io.write_yaml_file(path, plan)
    _process_event_recorder.emit_process_event(project_root, "orchestrator.plan.created", process_id="multi-agent-task-orchestration", subject=run_id, payload={"plan": rel(path, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_orchestrator_plan_validate(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    plan = _orchestration_config_service.load_orchestrator_plan(project_root, args.plan, getattr(args, "run", None))
    result = print_checks(_worker_plan_validation_service.validate(project_root, plan))
    if getattr(args, "write_normalized", None):
        output = Path(args.write_normalized).expanduser()
        if not output.is_absolute():
            output = (project_root / output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        _core_common_yaml_io.write_yaml_file(output, _orchestration_config_service.normalized_orchestrator_plan(project_root, plan))
        print(f"WROTE: {rel(output, project_root)}")
    run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
    _process_event_recorder.emit_process_event(project_root, "orchestrator.plan.reviewed", process_id="multi-agent-task-orchestration", subject=str(run.get("id") or "run"), payload={"result": "fail" if result else "pass"})
    return result


def command_worker_launch_prompt_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = str(task.get("run_id") or "")
    output = Path(args.output).expanduser() if getattr(args, "output", None) else _work_paths.worker_prompt(project_root, run_id, task_id)
    if not output.is_absolute():
        output = (project_root / output).resolve()
    prompt = _worker_assignment_service.render_prompt(project_root, task_id)
    if not args.apply or getattr(args, "dry_run", False):
        print_plan("worker-launch-prompt create dry run", [output], project_root)
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(prompt, encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "worker.launch_prompt.created", process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"prompt": rel(output, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(output, project_root)}")
    return 0


def command_orchestrator_plan_apply(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    plan = _orchestration_config_service.load_orchestrator_plan(project_root, args.plan, getattr(args, "run", None))
    plan = _orchestration_config_service.apply_orchestrator_model_override(plan, getattr(args, "model", None))
    checks = _worker_plan_validation_service.validate(project_root, plan)
    if any(item.level == "FAIL" for item in checks):
        print_checks(checks)
        return 1
    run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
    run_id = safe_id(str(run.get("id") or "run"), "run")
    title = str(run.get("title") or run_id)
    runtime = plan.get("runtime") if isinstance(plan.get("runtime"), dict) else {}
    default_driver = str(runtime.get("default_driver") or "manual")
    default_model = _context_contract_inputs.normalize_agent_model(runtime.get("model") or "")
    default_reasoning_effort = _context_contract_inputs.normalize_agent_reasoning_effort(runtime.get("reasoning_effort") or "")
    workers = plan.get("workers") if isinstance(plan.get("workers"), list) else []
    planned = [_work_paths.run_document(project_root, run_id), _orchestration_config_service.orchestrator_plan_path(project_root, run_id), _work_paths.run_root(project_root, run_id) / "worker-prompts", _work_paths.run_root(project_root, run_id) / "config-resolution-report.yaml"]
    if not args.apply or getattr(args, "dry_run", False):
        print_plan("orchestrator-plan apply dry run", planned, project_root)
        return 0
    if not _work_paths.run_document(project_root, run_id).is_file():
        status, output = run_command_capture(
            command_run_create,
            argparse.Namespace(project_root=str(project_root), id=run_id, title=title, process="multi-agent-task-orchestration", objective=str(run.get("objective") or title), status="in_progress", dry_run=False),
        )
        if status:
            print(output, end="")
            return status
    if runtime:
        with registry_file_lock(_work_paths.run_document(project_root, run_id)):
            run_doc = load_run(project_root, run_id)
            run_doc["runtime"] = {
                "default_driver": default_driver,
                "supervisor_profile": str(runtime.get("supervisor_profile") or "default"),
                "start_policy": str(runtime.get("start_policy") or "manual"),
            }
            if "max_parallel_workers" in runtime:
                run_doc["runtime"]["max_parallel_workers"] = int(runtime.get("max_parallel_workers") or 1)
            save_run_locked(project_root, run_doc)
    _core_common_yaml_io.write_yaml_file(_orchestration_config_service.orchestrator_plan_path(project_root, run_id), plan)
    for order, worker in enumerate(workers, start=1):
        if not isinstance(worker, dict):
            continue
        task_id = safe_id(str(worker.get("id") or f"worker-{order}"), "worker")
        assignment_path = _work_paths.assignment_document(project_root, task_id)
        if not assignment_path.is_file():
            status, output = run_command_capture(
                command_task_create,
                argparse.Namespace(
                    project_root=str(project_root),
                    run=run_id,
                    id=task_id,
                    title=str(worker.get("title") or task_id),
                    process=str(worker.get("process") or "task-batch-execution"),
                    objective=str(worker.get("objective") or worker.get("title") or task_id),
                    order=order,
                    execution_mode=str(worker.get("execution_mode") or "implementation"),
                    allowed_file=_context_contract_inputs.assignment_scope_items(worker.get("allowed_files")),
                    allowed_glob=[],
                    allowed_read_file=_context_contract_inputs.assignment_scope_items(worker.get("allowed_read_files")),
                    read_file=[],
                    context_artifact=normalize_context_artifacts(worker.get("context_artifacts")),
                    required_source=_context_contract_inputs.assignment_scope_items(worker.get("required_sources")),
                    workspace_knowledge_resource=_context_contract_inputs.normalize_workspace_access(worker.get("workspace_access"))["knowledge_resources"],
                    workspace_template=_context_contract_inputs.normalize_workspace_access(worker.get("workspace_access"))["templates"],
                    workspace_tool=_context_contract_inputs.normalize_workspace_access(worker.get("workspace_access"))["tools"],
                    workspace_mcp=_context_contract_inputs.normalize_workspace_access(worker.get("workspace_access"))["mcp"],
                    forbidden_file=_context_contract_inputs.assignment_scope_items(worker.get("forbidden_files")),
                    forbidden_glob=[],
                    owner=str(worker.get("owner") or task_id),
                    role=str(worker.get("role") or "worker"),
                    writer="true" if bool(worker.get("writer", True)) else "false",
                    required_output=_context_contract_inputs.normalize_required_outputs(worker.get("required_outputs")),
                    expected_report_language=str(worker.get("expected_report_language") or "en"),
                    expected_report_artifact=str(worker.get("expected_report_artifact") or ""),
                    force_with_handoff=bool(plan.get("allow_write_scope_overlap", False) or as_list(worker.get("dependencies")) or as_list(worker.get("depends_on"))),
                    agent_model=_context_contract_inputs.normalize_agent_model(worker.get("model") or default_model),
                    reasoning_effort=_context_contract_inputs.normalize_agent_reasoning_effort(worker.get("reasoning_effort") or worker.get("agent_reasoning_effort") or default_reasoning_effort),
                    dry_run=False,
                ),
            )
            if status:
                print(output, end="")
                return status
        task = _worker_assignment_service.load(project_root, task_id)
        task["worker_may_rebuild_context"] = bool(worker.get("worker_may_rebuild_context", False))
        task["runtime_driver"] = str(worker.get("runtime_driver") or default_driver)
        agent_model = _context_contract_inputs.normalize_agent_model(worker.get("model") or default_model)
        if agent_model:
            task["agent_model"] = agent_model
        agent_reasoning_effort = _context_contract_inputs.normalize_agent_reasoning_effort(worker.get("reasoning_effort") or worker.get("agent_reasoning_effort") or default_reasoning_effort)
        if agent_reasoning_effort:
            task["agent_reasoning_effort"] = agent_reasoning_effort
        task["workspace_access"] = _context_contract_inputs.normalize_workspace_access(worker.get("workspace_access"))
        task["subagent_policy"] = _worker_plan_policy.subagent_policy(worker)
        blocked_by = sorted({safe_id(str(item), "task") for item in [*as_list(worker.get("dependencies")), *as_list(worker.get("depends_on"))] if item})
        if blocked_by:
            task.setdefault("dependencies", {})["blocked_by"] = blocked_by
        save_task(project_root, task)
    materialize_plan_overlap_policy(project_root, plan)
    _orchestration_config_service.write_orchestrator_config_resolution_artifacts(project_root, plan)
    command_project_context_refresh(argparse.Namespace(project_root=str(project_root)))
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        task_id = safe_id(str(worker.get("id") or "worker"), "worker")
        capsule_status, capsule_rel = existing_capsule_status(project_root, task_id)
        if capsule_status in {"fresh", "legacy"}:
            suffix = " (legacy capsule without assignment checksum)" if capsule_status == "legacy" else ""
            print(f"PRESENT: {capsule_rel}{suffix}")
        elif capsule_status == "stale":
            print(f"FAIL: assignment capsule is stale for {task_id}: {capsule_rel}; create_successor_work; immutable contexts cannot be rebuilt in place")
            return 1
        else:
            status, output = run_command_capture(command_assignment_capsule, argparse.Namespace(project_root=str(project_root), assignment=str(_work_paths.assignment_document(project_root, task_id)), force=bool(plan.get("allow_write_scope_overlap", False))))
            print(output, end="")
            if status:
                return status
        status, output = run_command_capture(command_worker_launch_prompt_create, argparse.Namespace(project_root=str(project_root), task=task_id, output=None, apply=True, dry_run=False))
        print(output, end="")
        if status:
            return status
        task_doctor_status = command_task_doctor(argparse.Namespace(project_root=str(project_root), task=task_id))
        if task_doctor_status:
            return task_doctor_status
        if str(runtime.get("start_policy") or "manual") == "prepare":
            prepare_worker_run(project_root, task_id, None, None)
        if getattr(args, "workplace", None):
            command_agent_lease_grant(
                argparse.Namespace(
                    workplace=args.workplace,
                    id=f"lease-{run_id}-{task_id}",
                    agent=task_id,
                    session="",
                    project_id=safe_id(project_root.name, "project"),
                    process=str(worker.get("process") or "task-batch-execution"),
                    run=run_id,
                    task=task_id,
                    capsule=rel(locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml", project_root),
                    allowed_file=_context_contract_inputs.assignment_scope_items(worker.get("allowed_files")),
                    allowed_read_file=_context_contract_inputs.assignment_scope_items(worker.get("allowed_read_files")),
                    forbidden_file=_context_contract_inputs.assignment_scope_items(worker.get("forbidden_files")),
                    ttl=3600,
                )
            )
    write_orchestration_summary(project_root, plan)
    if str(runtime.get("start_policy") or "manual") == "supervisor" and bool(getattr(args, "shell_plan", False)):
        supervisor_status = command_supervisor_run(
            argparse.Namespace(
                project_root=str(project_root),
                run=run_id,
                profile=str(runtime.get("supervisor_profile") or "default"),
                driver=None,
                interval=0,
                max_ticks=5,
                final_drain_timeout=5,
            )
        )
        if supervisor_status:
            return supervisor_status
    doctor_status = command_run_doctor(argparse.Namespace(project_root=str(project_root), run=run_id))
    _process_event_recorder.emit_process_event(project_root, "orchestrator.plan.applied", process_id="multi-agent-task-orchestration", subject=run_id, payload={"run_id": run_id, "doctor_status": doctor_status}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(_work_paths.run_root(project_root, run_id) / 'orchestration-summary.md', project_root)}")
    return doctor_status


def command_orchestrator_plan_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    plan = _orchestration_config_service.load_orchestrator_plan(project_root, args.plan, getattr(args, "run", None))
    run = plan.get("run") if isinstance(plan.get("run"), dict) else {}
    run_id = safe_id(str(run.get("id") or "run"), "run")
    print(f"RUN: {run_id}")
    print(f"PLAN: {rel(_orchestration_config_service.orchestrator_plan_path(project_root, run_id), project_root)}")
    if _work_paths.run_document(project_root, run_id).is_file():
        return command_run_status(argparse.Namespace(project_root=str(project_root), run=run_id))
    print("STATUS: plan-created")
    return 0


def process_execution_service(project_root: Path, explicit_workplace: str | None = None) -> ProcessExecutionService:
    from processforge_core.composition import build_process_execution_service

    manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, explicit_workplace)
    workplace_root = manifest.parent if manifest is not None else None
    return build_process_execution_service(project_root, workplace_root, sys.modules[__name__], events=_process_event_recorder)


def work_resource_service(project_root: Path, explicit_workplace: str | None = None) -> WorkResourceService:
    from processforge_core.work.resources import WorkResourceService

    manifest = _project_coordination_state.resolve_project_workplace_manifest(project_root, explicit_workplace)
    return WorkResourceService(project_root, manifest.parent if manifest else None, sys.modules[__name__])


def command_run_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    run_id = safe_id(args.id, "run")
    process_id = safe_id(args.process, "task-batch-execution")
    require_official_process_active(project_root, process_id)
    path = _work_paths.run_document(project_root, run_id)
    if path.exists():
        raise SystemExit(f"FAIL: run already exists: {rel(path, project_root)}")
    run = {
        "schema_version": 1,
        "id": run_id,
        "title": args.title,
        "process": process_id,
        "status": args.status,
        "created_at": _core_common_clock.now_utc(),
        "updated_at": _core_common_clock.now_utc(),
        "objective": args.objective or "",
        "platform": getattr(args, "platform", None) or "",
        "selected_specializations": [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(getattr(args, "specialization", []))],
        "scope": {"type": "project", "project_root": "."},
        "tasks": [],
        "final_artifacts": [],
        "events": {"emitted": ["run.created"]},
        "privacy": {"public_safe": True},
    }
    planned = [path, _work_paths.run_root(project_root, run_id) / "plan.md", _work_paths.run_root(project_root, run_id) / "task-index.md"]
    if getattr(args, "dry_run", False):
        print_plan("run-create dry run", planned, project_root)
        return 0
    root = _work_paths.run_root(project_root, run_id)
    root.mkdir(parents=True, exist_ok=True)
    save_run(project_root, run)
    (root / "plan.md").write_text(f"# Run Plan: {args.title}\n\nObjective: {args.objective or 'TBD'}\n", encoding="utf-8")
    _process_event_recorder.emit_process_event(project_root, "run.created", process_id=run["process"], subject=run_id, payload={"run_id": run_id, "path": rel(path, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_run_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    root = locate_flow_root(project_root) / "runs"
    runs = sorted(root.glob("*/run.yaml")) if root.is_dir() else []
    if not runs:
        print("No runs found.")
        return 0
    for path in runs:
        data = load_yaml_document(path)
        print(f"{data.get('id', path.parent.name)}\t{data.get('status', 'unknown')}\t{data.get('title', '')}")
    return 0


def command_run_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    tasks = [item for item in run.get("tasks", []) if isinstance(item, dict)] if isinstance(run.get("tasks"), list) else []
    counts: dict[str, int] = {}
    for item in tasks:
        counts[str(item.get("status", "unknown"))] = counts.get(str(item.get("status", "unknown")), 0) + 1
    print(f"RUN: {run.get('id')}")
    print(f"TITLE: {run.get('title')}")
    print(f"STATUS: {run.get('status')}")
    print("TASKS: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) if counts else "TASKS: none")
    for item in sorted(tasks, key=lambda value: int(value.get("order", 0) or 0)):
        task = load_yaml_document(_work_paths.assignment_document(project_root, str(item.get("id", ""))))
        iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
        latest = iterations[-1] if iterations and isinstance(iterations[-1], dict) else {}
        latest_text = f" latest={latest.get('id')}:{latest.get('kind')}:{latest.get('status')}" if latest else ""
        print(f"- {item.get('order')}: {item.get('id')} [{item.get('status')}]{latest_text}")
    blockers = [str(item.get("id")) for item in tasks if item.get("blocking", True) is not False and str(item.get("status")) in {"blocked", "failed"}]
    if blockers:
        print("BLOCKERS: " + ", ".join(blockers))
    return 0


def command_run_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run_id = str(args.run or "").strip()
    with registry_file_lock(_work_paths.run_document(project_root, run_id)):
        checks = _run_task_consistency_service.validate_run_consistency(project_root, run_id, include_runtime_events=bool(getattr(args, "runtime_events", False)))
    result = print_checks(checks)
    _process_event_recorder.emit_process_event(project_root, "run.doctor.failed" if result else "run.doctor.passed", severity="error" if result else "info", subject=run_id, payload={"run_id": run_id, "result": "fail" if result else "pass"}, correlation_id=f"run-{run_id}")
    return result


def command_run_summary(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run_id = safe_id(args.run, "run")
    with registry_file_lock(_work_paths.run_root(project_root, run_id) / "run.yaml"):
        return _command_run_summary_locked(args)


def _command_run_summary_locked(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    summary = _work_paths.summary(project_root, run_id)
    handoff = _work_paths.handoff(project_root, run_id)
    if getattr(args, "dry_run", False):
        print_plan("run-summary dry run", [summary, handoff], project_root)
        return 0
    artifacts = [rel(summary, project_root), rel(handoff, project_root)]
    run["final_artifacts"] = artifacts
    emitted = run.setdefault("events", {}).setdefault("emitted", []) if isinstance(run.setdefault("events", {}), dict) else []
    if isinstance(emitted, list) and "run.summary.created" not in emitted:
        emitted.append("run.summary.created")
    save_run_locked(project_root, run, include_summary_handoff=True)
    _process_event_recorder.emit_process_event(project_root, "run.summary.created", process_id=str(run.get("process", "")), subject=run_id, payload={"run_id": run_id, "artifacts": artifacts}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(summary, project_root)}")
    print(f"WROTE: {rel(handoff, project_root)}")
    return 0


def command_run_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run_id = safe_id(args.run, "run")
    with registry_file_lock(_work_paths.run_root(project_root, run_id) / "run.yaml"):
        return _command_run_complete_locked(args)


def _command_run_complete_locked(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    tasks = [item for item in run.get("tasks", []) if isinstance(item, dict)] if isinstance(run.get("tasks"), list) else []
    incomplete = [str(item.get("id")) for item in tasks if item.get("blocking", True) is not False and str(item.get("status")) != "done"]
    if incomplete:
        raise SystemExit("FAIL: blocking tasks are not done: " + ", ".join(incomplete))
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete run {run_id}")
        return 0
    run["status"] = "completed"
    emitted = run.setdefault("events", {}).setdefault("emitted", []) if isinstance(run.setdefault("events", {}), dict) else []
    if isinstance(emitted, list) and "run.completed" not in emitted:
        emitted.append("run.completed")
    summary = _work_paths.summary(project_root, run_id)
    handoff = _work_paths.handoff(project_root, run_id)
    artifacts = [rel(summary, project_root), rel(handoff, project_root)]
    run["final_artifacts"] = artifacts
    if isinstance(emitted, list) and "run.summary.created" not in emitted:
        emitted.append("run.summary.created")
    save_run_locked(project_root, run, include_summary_handoff=True)
    _process_event_recorder.emit_process_event(project_root, "run.completed", process_id=str(run.get("process", "")), subject=run_id, payload={"run_id": run_id}, correlation_id=f"run-{run_id}")
    _process_event_recorder.emit_process_event(project_root, "run.summary.created", process_id=str(run.get("process", "")), subject=run_id, payload={"run_id": run_id, "artifacts": artifacts}, correlation_id=f"run-{run_id}")
    print(f"COMPLETED: {run_id}")
    return 0


def command_task_create(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run_id = safe_id(args.run, "run")
    with registry_file_lock(_work_paths.run_document(project_root, run_id)):
        return _command_task_create_locked(args)


def _command_task_create_locked(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    run_id = str(run.get("id", safe_id(args.run, "run")))
    task_id = safe_id(args.id, "task")
    process_id = safe_id(args.process, "task")
    require_official_process_active(project_root, process_id)
    stage_id = safe_id(str(getattr(args, "stage", "") or ""), "stage") if getattr(args, "stage", None) else ""
    if stage_id:
        definition = resolve_process_definition(project_root, process_id)
        declared_stages = {str(item.get("id") or "") for item in as_list(definition.process.get("stages")) if isinstance(item, dict)}
        if stage_id not in declared_stages:
            raise SystemExit(f"FAIL: stage {stage_id} is not declared by process {process_id}")
    path = _work_paths.assignment_document(project_root, task_id)
    if path.exists():
        raise SystemExit(f"FAIL: task already exists: {rel(path, project_root)}")
    tasks = run.get("tasks") if isinstance(run.get("tasks"), list) else []
    if any(isinstance(item, dict) and item.get("id") == task_id for item in tasks):
        raise SystemExit(f"FAIL: run already contains task id: {task_id}")
    order = args.order or (len(tasks) + 1)
    task = {
        "schema_version": 1,
        "id": task_id,
        "title": args.title,
        "run_id": run_id,
        "process": process_id,
        "status": "open",
        "created_at": _core_common_clock.now_utc(),
        "updated_at": _core_common_clock.now_utc(),
        "objective": args.objective or "",
        "platform": getattr(args, "platform", None) or "",
        "selected_specializations": [_specialization_catalog_reader.resource_id(str(item)) for item in as_list(getattr(args, "specialization", []))],
        "order": order,
        "dependencies": {"blocked_by": [], "blocks": []},
        "iterations": [],
        "result": {"status": "pending", "summary": "", "artifacts": []},
    }
    if stage_id:
        task["stage"] = stage_id
    allowed_files = _context_contract_inputs.assignment_scope_items([*as_list(getattr(args, "allowed_file", [])), *as_list(getattr(args, "allowed_glob", []))])
    allowed_read_files = _context_contract_inputs.assignment_scope_items([*as_list(getattr(args, "read_file", [])), *as_list(getattr(args, "allowed_read_file", []))])
    context_artifacts = normalize_context_artifacts(getattr(args, "context_artifact", []))
    required_sources = _context_contract_inputs.assignment_scope_items(getattr(args, "required_source", []))
    forbidden_files = _context_contract_inputs.assignment_scope_items([*as_list(getattr(args, "forbidden_file", [])), *as_list(getattr(args, "forbidden_glob", []))])
    required_outputs = _context_contract_inputs.normalize_required_outputs(getattr(args, "required_output", []))
    if getattr(args, "execution_mode", None):
        task["execution_mode"] = normalize_execution_mode(args.execution_mode)
        if task["execution_mode"]["kind"] == "implementation":
            task["execution_mode"]["code_changes_allowed"] = True
    if context_artifacts:
        task["context_artifacts"] = context_artifacts
    if required_sources:
        task["required_sources"] = required_sources
    workspace_access = _context_contract_inputs.normalize_workspace_access(
        {
            "knowledge_resources": getattr(args, "workspace_knowledge_resource", []),
            "templates": getattr(args, "workspace_template", []),
            "tools": getattr(args, "workspace_tool", []),
            "mcp": getattr(args, "workspace_mcp", []),
        }
    )
    if any(workspace_access[key] for key in WORKSPACE_ACCESS_KEYS):
        task["workspace_access"] = workspace_access
    if allowed_files:
        task["allowed_files"] = allowed_files
    if allowed_read_files:
        task["allowed_read_files"] = allowed_read_files
    if forbidden_files:
        task["forbidden_files"] = forbidden_files
    writer = str(getattr(args, "writer", "true")).lower() == "true"
    if allowed_files or getattr(args, "owner", None) or getattr(args, "role", None) or not writer:
        task["ownership"] = {
            "owner_id": safe_id(getattr(args, "owner", None) or task_id, "assignment"),
            "owner_label": f"worker-{safe_id(getattr(args, 'owner', None) or task_id, 'assignment')}",
            "role": getattr(args, "role", None) or "",
            "writer": writer,
            "owned_files": allowed_files if writer else [],
            "owned_globs": [],
        }
    if allowed_files or forbidden_files:
        task["non_overlap"] = {
            "policy": "block_on_write_overlap",
            "active_parallel_tasks": [],
            "current_write_scope": _context_contract_inputs.assignment_write_scope(task),
            "rule": "Do not edit files owned by active parallel tasks.",
        }
    if required_outputs:
        task["required_outputs"] = required_outputs
    agent_model = _context_contract_inputs.normalize_agent_model(getattr(args, "agent_model", None) or getattr(args, "model", None) or "")
    if agent_model:
        task["agent_model"] = agent_model
    agent_reasoning_effort = _context_contract_inputs.normalize_agent_reasoning_effort(getattr(args, "reasoning_effort", None) or getattr(args, "agent_reasoning_effort", None) or "")
    if agent_reasoning_effort:
        task["agent_reasoning_effort"] = agent_reasoning_effort
    expected_report: dict[str, Any] = {}
    if getattr(args, "expected_report_language", None):
        expected_report["language"] = args.expected_report_language
    if getattr(args, "expected_report_artifact", None):
        expected_report["artifact"] = _context_contract_inputs.normalize_assignment_path(args.expected_report_artifact)
        if len(required_outputs) == 1:
            required_outputs[0].setdefault("path", expected_report["artifact"])
    missing_output_paths = [str(item.get("id") or "output") for item in required_outputs if not str(item.get("path") or "").strip()]
    if missing_output_paths:
        raise SystemExit(
            "FAIL: every required output needs a path; use "
            "--required-output id=<id>,path=<repository-relative-path>. Missing: "
            + ", ".join(missing_output_paths)
        )
    if expected_report:
        expected_report.setdefault("format", "concise_markdown")
        expected_report.setdefault("include", [item["id"] for item in required_outputs])
        task["expected_report"] = expected_report
    overlap_check = validate_assignment_scope_overlaps(project_root, task, assignment_path=path)
    if overlap_check["status"] == "fail" and not getattr(args, "force_with_handoff", False):
        raise SystemExit("FAIL: task write scope overlaps active assignments: " + dump_yaml(overlap_check))
    if overlap_check["status"] == "fail":
        task.setdefault("non_overlap", {})["overlap_check"] = overlap_check
    planned = [path, _work_paths.task_artifacts(project_root, run_id, task_id), _work_paths.run_root(project_root, run_id) / "task-index.md"]
    if getattr(args, "dry_run", False):
        print_plan("task-create dry run", planned, project_root)
        if allowed_files or forbidden_files:
            print("WRITE_SCOPE:")
            for item in _context_contract_inputs.assignment_write_scope(task):
                print(f"- {item}")
            print("OVERLAP_CHECK: " + overlap_check["status"])
        return 0
    _work_paths.task_artifacts(project_root, run_id, task_id).mkdir(parents=True, exist_ok=True)
    _core_common_yaml_io.write_yaml_file(path, task)
    tasks.append({"id": task_id, "assignment": rel(path, project_root), "status": "open", "order": order, "blocking": True})
    run["tasks"] = tasks
    save_run_locked(project_root, run)
    for event_type in ["task.created", "assignment.created"]:
        _process_event_recorder.emit_process_event(project_root, event_type, process_id=task["process"], subject=task_id, assignment_id_value=task_id, assignment_path=rel(path, project_root), payload={"run_id": run_id, "task_id": task_id, "path": rel(path, project_root)}, correlation_id=f"run-{run_id}")
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_task_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    run = load_run(project_root, args.run)
    for item in sorted([task for task in run.get("tasks", []) if isinstance(task, dict)], key=lambda value: int(value.get("order", 0) or 0)):
        print(f"{item.get('order')}\t{item.get('id')}\t{item.get('status')}\t{item.get('assignment')}")
    return 0


def command_task_start(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    with registry_file_lock(_work_paths.run_document(project_root, run_id)):
        return _command_task_start_locked(args)


def _command_task_start_locked(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    require_official_process_active(project_root, _run_task_inputs.task_process_id(task))
    task["status"] = "in_progress"
    save_task(project_root, task)
    update_run_task_status_locked(project_root, str(task.get("run_id", "")), task_id, "in_progress")
    for event_type in ["task.started", "assignment.started"]:
        _process_event_recorder.emit_process_event(project_root, event_type, process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id}, correlation_id=f"run-{task.get('run_id')}")
    print(f"STARTED: {task_id}")
    return 0


def command_task_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    run_id = safe_id(str(task.get("run_id") or "run"), "run")
    with registry_file_lock(_work_paths.run_root(project_root, run_id) / "run.yaml", stale_after_seconds=0 if getattr(args, "completion_id", None) else 300):
        return _command_task_complete_locked(args)


def _command_task_complete_locked(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete task {task_id}")
        return 0
    waivers = _work_output_policy.waivers(getattr(args, "waive_required_output", []))
    output_failures = [item.message for item in _work_output_policy.checks(project_root, task, waivers) if item.level == "FAIL"]
    if output_failures:
        raise SystemExit("FAIL: task required outputs are not complete: " + "; ".join(output_failures))
    artifacts = [item for item in (args.artifact or [])]
    task["status"] = "done"
    task["result"] = {"status": "done", "summary": args.summary, "artifacts": artifacts}
    if waivers:
        task["result"]["waivers"] = waivers
    save_task(project_root, task)
    update_run_task_status_locked(project_root, str(task.get("run_id", "")), task_id, "done")
    for event_type in ["task.completed", "assignment.completed"]:
        event_kwargs = dict(process_id=_run_task_inputs.task_process_id(task), subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "summary": args.summary}, correlation_id=f"run-{task.get('run_id')}")
        if getattr(args, "completion_id", None):
            emit_worker_completion_event(project_root, event_type, args.completion_id, **event_kwargs)
        else:
            _process_event_recorder.emit_process_event(project_root, event_type, **event_kwargs)
    print(f"DONE: {task_id}")
    return 0




def command_task_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    checks = _run_task_consistency_service.validate_task_consistency(project_root, task_id)
    result = print_checks(checks)
    task = _worker_assignment_service.load(project_root, task_id)
    _process_event_recorder.emit_process_event(project_root, "task.doctor.failed" if result else "task.doctor.passed", severity="error" if result else "info", subject=task_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"task_id": task_id, "result": "fail" if result else "pass", "verification_fingerprint": _work_output_policy.fingerprint(project_root, task)})
    return result


def command_iteration_add(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    kind = safe_id(args.kind, "work")
    if kind not in ITERATION_KINDS:
        raise SystemExit(f"FAIL: invalid iteration kind: {kind}")
    status = args.status
    if status not in _core_work_consistency.ITERATION_STATUSES:
        raise SystemExit(f"FAIL: invalid iteration status: {status}")
    iter_id = safe_id(args.id, "iter") if args.id else _run_task_inputs.next_iteration_id(task)
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    if any(isinstance(item, dict) and item.get("id") == iter_id for item in iterations):
        raise SystemExit(f"FAIL: duplicate iteration id: {iter_id}")
    artifact_kind = "debug-log.md" if kind == "debug" else "work-log.md"
    artifact = rel(_work_paths.task_artifacts(project_root, str(task.get("run_id", "")), task_id) / artifact_kind, project_root)
    iteration = {"id": iter_id, "kind": kind, "status": status, "started_at": _core_common_clock.now_utc(), "summary": args.summary, "artifacts": [artifact]}
    if status in {"completed", "passed", "failed", "cancelled"}:
        iteration["completed_at"] = _core_common_clock.now_utc()
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would add {iter_id} to {task_id}")
        return 0
    _work_paths.task_artifacts(project_root, str(task.get("run_id", "")), task_id).mkdir(parents=True, exist_ok=True)
    iterations.append(iteration)
    task["iterations"] = iterations
    if status == "in_progress":
        task["status"] = "debugging" if kind == "debug" else "in_progress"
    save_task(project_root, task)
    _process_event_recorder.emit_process_event(project_root, "iteration.added", process_id=_run_task_inputs.task_process_id(task), subject=iter_id, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "iteration_id": iter_id, "kind": kind, "status": status}, correlation_id=f"run-{task.get('run_id')}")
    print(f"ADDED: {iter_id}")
    return 0


def command_iteration_complete(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    task_id = safe_id(args.task, "task")
    task = _worker_assignment_service.load(project_root, task_id)
    status = args.status
    if status not in _core_work_consistency.ITERATION_STATUSES:
        raise SystemExit(f"FAIL: invalid iteration status: {status}")
    iterations = task.get("iterations") if isinstance(task.get("iterations"), list) else []
    found = False
    for item in iterations:
        if isinstance(item, dict) and item.get("id") == args.iteration:
            item["status"] = status
            item["completed_at"] = _core_common_clock.now_utc()
            if args.summary:
                item["summary"] = args.summary
            found = True
            break
    if not found:
        raise SystemExit(f"FAIL: iteration not found: {args.iteration}")
    if getattr(args, "dry_run", False):
        print(f"DRY-RUN: would complete iteration {args.iteration}")
        return 0
    task["iterations"] = iterations
    save_task(project_root, task)
    _process_event_recorder.emit_process_event(project_root, "iteration.completed" if status in {"completed", "passed"} else "iteration.failed", process_id=_run_task_inputs.task_process_id(task), subject=args.iteration, assignment_id_value=task_id, assignment_path=rel(_work_paths.assignment_document(project_root, task_id), project_root), payload={"run_id": task.get("run_id"), "task_id": task_id, "iteration_id": args.iteration, "status": status}, correlation_id=f"run-{task.get('run_id')}")
    print(f"UPDATED: {args.iteration}")
    return 0


def command_hooks_dispatch(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    hook_checks = _hook_configuration_reader.validate(project_root)
    hook_failures = [item for item in hook_checks if item.level == "FAIL"]
    if hook_failures:
        for item in hook_failures:
            print(f"FAIL: {item.message}")
        return 1
    if getattr(args, "send", False):
        raise SystemExit("FAIL: --send is reserved for a future network transport and is disabled in the MVP")
    event = _telemetry_event_service.processforge_event(
        project_root,
        args.event_type,
        severity=args.severity,
        session_id=args.session_id,
        assignment_id_value=args.assignment_id,
        payload={"dry_run": bool(args.dry_run), "outbox": bool(args.outbox), "since": args.since, "source": "hooks-dispatch"},
        privacy="sanitized",
    )
    actions = _runtime_hook_dispatcher.dispatch_hooks(project_root, event, dry_run=args.dry_run, outbox=args.outbox or not args.dry_run)
    if not actions:
        print("HOOKS: none")
    else:
        for action in actions:
            print(f"HOOK: {action['hook']} {action['type']} {action['status']}")
            if "outbox" in action:
                print(f"OUTBOX: {action['outbox']}")
            if "result" in action:
                print(f"RESULT: {action['result']}")
    if not args.dry_run:
        _process_event_recorder.append_process_event(project_root, event, dispatch=False)
        if actions:
            _process_event_recorder.emit_process_event(project_root, "hook.dispatched", payload={"event_id": _hook_dispatch_policy.event_id_value(event), "actions": actions}, privacy="sanitized", correlation_id=str(event.get("correlation_id")))
        print(f"EVENT: {_hook_dispatch_policy.event_id_value(event)}")
    return 0


def command_events_validate(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    flow_root = locate_flow_root(project_root)
    failures: list[str] = []
    events_path = _run_task_inputs.event_runtime_paths(project_root)[0]
    for line_number, data, error in iter_process_events(events_path):
        label = f"{rel(events_path, project_root)}:{line_number}"
        if error:
            failures.append(f"{label}: invalid event record: {error}")
        else:
            failures.extend(_record_validation_policy.event(data, label))

    transcript_root = flow_root / "runtime" / "chat" / "transcripts"
    if transcript_root.is_dir():
        for transcript in sorted(transcript_root.glob("*.ndjson")):
            for line_number, data, error in iter_ndjson(transcript):
                label = f"{rel(transcript, project_root)}:{line_number}"
                if error:
                    failures.append(f"{label}: invalid NDJSON: {error}")
                else:
                    failures.extend(_record_validation_policy.chat(data, label))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: runtime events and chat transcripts validate.")
    return 0


def command_chat_record(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    if args.content_file:
        content = Path(args.content_file).expanduser().read_text(encoding="utf-8", errors="replace")
    elif args.content is not None:
        content = args.content
    else:
        raise SystemExit("FAIL: provide --content or --content-file")
    transcript, record, event = _chat_transcript_writer.append_chat_message(
        project_root,
        session_id=args.session_id,
        participant_id=args.participant,
        participant_type=args.participant_type,
        participant_role=args.participant_role or args.participant,
        message_role=args.role,
        content=content,
        turn_id=args.turn_id,
        parent_message_id=args.parent_message_id,
        process_id=args.process_id,
        stage_id=args.stage_id,
        assignment_id_value=args.assignment_id,
        include_event_content=args.include_content,
    )
    print(f"TRANSCRIPT: {rel(transcript, project_root)}")
    print(f"MESSAGE: {record['message_id']}")
    print(f"EVENT: {_hook_dispatch_policy.event_id_value(event)}")
    return 0


def command_chat_export(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    if args.target != "wtaicc":
        raise SystemExit("FAIL: only --target wtaicc is supported by the MVP")
    if not args.outbox:
        raise SystemExit("FAIL: chat-export is file-first; pass --outbox to write a delivery payload")
    messages = load_chat_messages(project_root, args.session_id)
    event = _telemetry_event_service.processforge_event(
        project_root,
        "session.message.recorded",
        session_id=args.session_id,
        subject=f"chat/{args.session_id}",
        data={"session_id": args.session_id, "message_count": len(messages), "target": args.target},
        privacy="sanitized",
        correlation_id=args.session_id,
    )
    chat_payload = {
        "included": True,
        "mode": "full" if args.include_content else "metadata_only",
        "messages": _chat_export_service.chat_export_messages(messages, include_content=args.include_content),
    }
    payload = _hook_dispatch_policy.wtaicc_outbox_payload(event, chat=chat_payload)
    outbox_root = locate_flow_root(project_root) / "runtime" / "hooks" / "outbox" / "wtaicc"
    outbox_root.mkdir(parents=True, exist_ok=True)
    stamp = _core_common_clock.now_utc().replace(":", "").replace("-", "").replace("Z", "z")
    target = outbox_root / f"chat-{safe_id(args.session_id, 'session')}-{stamp}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _process_event_recorder.append_process_event(project_root, event, dispatch=False)
    _process_event_recorder.emit_process_event(
        project_root,
        "hook.dispatched",
        session_id=args.session_id,
        data={"target": args.target, "outbox": rel(target, project_root), "message_count": len(messages)},
        privacy="sanitized",
        correlation_id=args.session_id,
    )
    print(f"OUTBOX: {rel(target, project_root)}")
    print(f"MESSAGES: {len(messages)}")
    return 0


def command_context_resolve(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise SystemExit(f"FAIL: project root not found: {project_root}")
    _run_task_inputs.require_flow_root(project_root)
    if getattr(args, "platform", None) or getattr(args, "process", None) or getattr(args, "specialization", None):
        flow_root = locate_flow_root(project_root)
        workplace_manifest = _project_coordination_state.resolve_workplace_manifest(flow_root / "process-forge.local.yaml") if (flow_root / "process-forge.local.yaml").is_file() else None
        if getattr(args, "workplace", None):
            workplace_manifest = _project_coordination_state.workplace_manifest_path_from_root(Path(args.workplace).expanduser())
        platform_ids = [str(item) for item in as_list(getattr(args, "platform", []))]
        resolved = resolve_specialization_context(
            project_root,
            workplace_manifest,
            platform_ids=platform_ids,
            process_id=getattr(args, "process", None),
            specialization_ids=[str(item) for item in as_list(getattr(args, "specialization", []))],
        )
        if getattr(args, "json", False):
            print(json.dumps({"resolved_context": resolved}, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(dump_yaml({"resolved_context": resolved}), end="")
        return 1 if resolved.get("conflicts") else 0
    print("DEPRECATED: context-resolve is a compatibility command. Use project-context-refresh and project-context-check for .pf projects.")
    status, paths = write_context_outputs(project_root)
    print(f"STATUS: {status}")
    for path in paths.values():
        print(f"WROTE: {rel(path, project_root)}")
    return 1 if status == "blocked" else 0


def command_context_compile(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project_root)
    assignment = Path(args.assignment).expanduser().resolve()
    print("DEPRECATED: context-compile is a compatibility command. Use assignment-capsule with YAML front matter for .pf projects.")
    ecp_path, capsule_path, conflict_report = compile_execution_context(
        project_root,
        assignment,
        write_capsule=args.capsule,
        supersede=args.supersede,
        allow_requires_approval=args.allow_requires_approval,
    )
    print(f"WROTE: {rel(conflict_report, project_root)}")
    print(f"WROTE: {rel(ecp_path, project_root)}")
    if capsule_path:
        print(f"WROTE: {rel(capsule_path, project_root)}")
    return 0


def assignment_capsule_path(project_root: Path, task_id: str) -> Path:
    return locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{safe_id(task_id, 'task')}.capsule.yaml"


def existing_capsule_status(project_root: Path, task_id: str) -> tuple[str, str]:
    capsule_path = assignment_capsule_path(project_root, task_id)
    if not capsule_path.is_file():
        return "missing", rel(capsule_path, project_root)
    capsule = load_yaml_document(capsule_path)
    if isinstance(capsule, dict) and "execution_contract" in capsule:
        from processforge_core.work.context import validate_execution_contract
        assignment_path = _work_paths.assignment_document(project_root, task_id)
        metadata = extract_assignment_front_matter(assignment_path) if assignment_path.is_file() else {}
        validation = validate_execution_contract(project_root, assignment_path, metadata, capsule, sys.modules[__name__])
        return ("fresh" if validation["status"] == "valid" else "stale"), rel(capsule_path, project_root)
    capsule_meta = capsule.get("capsule") if isinstance(capsule, dict) else {}
    recorded_checksum = str(capsule_meta.get("assignment_checksum") or "") if isinstance(capsule_meta, dict) else ""
    if not recorded_checksum:
        return "legacy", rel(capsule_path, project_root)
    assignment_path = _work_paths.assignment_document(project_root, task_id)
    current_checksum = sha256_file(assignment_path) if assignment_path.is_file() else ""
    if recorded_checksum == current_checksum:
        return "fresh", rel(capsule_path, project_root)
    return "stale", rel(capsule_path, project_root)


def command_doctor_context(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = _run_task_inputs.require_flow_root(project_root)
    checks: list[Check] = []
    manifest = flow_root / "process-forge.yaml"
    checks.append(check("PASS" if manifest.is_file() else "FAIL", f"{rel(manifest, project_root)} found"))
    if manifest.is_file():
        manifest_text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(manifest_text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(manifest_text) else "FAIL", "public manifest contains no secret values"))

    snapshot_yaml, snapshot_md = project_context_snapshot_paths(project_root)
    context_index = flow_root / "contexts" / "context-index.yaml"
    resolved_rules = flow_root / "contexts" / "resolved-rules.yaml"
    conflict_report = flow_root / "contexts" / "context-conflict-report.md"
    cache = flow_root / "runtime" / "cache" / "context-cache.yaml"
    checks.append(check("PASS" if snapshot_yaml.is_file() else "WARN", "project context snapshot YAML found"))
    checks.append(check("PASS" if snapshot_md.is_file() else "WARN", "project context snapshot MD found"))
    snapshot_freshness, snapshot_stale, snapshot = project_context_freshness(project_root)
    if snapshot_yaml.is_file():
        checks.append(check("PASS" if snapshot_freshness == "fresh" else "FAIL", f"project context snapshot freshness is {snapshot_freshness}" + (f": {', '.join(snapshot_stale)}" if snapshot_stale else "")))
        health = snapshot.get("snapshot", {}).get("health", {}).get("status", "pass") if isinstance(snapshot.get("snapshot"), dict) else "pass"
        checks.append(check("PASS" if health != "blocked" else "FAIL", f"project context snapshot health is {health}"))
    checks.append(check("PASS" if context_index.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "context index found"))
    checks.append(check("PASS" if resolved_rules.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "resolved rules found"))
    checks.append(check("PASS" if conflict_report.is_file() else ("WARN" if snapshot_yaml.is_file() else "FAIL"), "conflict report found"))
    status = _project_session_read_service.report_status(conflict_report)
    if conflict_report.is_file():
        checks.append(check("PASS" if status in {"resolved", "warn", "requires_approval"} else "FAIL", f"conflict status is {status}"))
    freshness, stale = _project_session_read_service.legacy_freshness(project_root)
    if context_index.is_file():
        checks.append(check("PASS" if freshness == "fresh" else "FAIL", f"context freshness is {freshness}" + (f": {', '.join(stale)}" if stale else "")))
    checks.append(check("PASS" if cache.is_file() else "WARN", "context cache found"))

    gitignore = project_root / ".gitignore"
    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        runtime_cache_ignored = "runtime/cache/" in ignore_text or "/runtime/cache/" in ignore_text or "runtime/" in ignore_text or ".pf/runtime/" in ignore_text
        checks.append(check("PASS" if runtime_cache_ignored else "FAIL", ".gitignore contains runtime cache ignore"))
    else:
        checks.append(check("WARN", ".gitignore missing"))

    if args.assignment:
        assignment = Path(args.assignment).expanduser().resolve()
        _index, _resolved, report, assignment_status = build_context_payload(project_root, assignment)
        context_status = normalized_context_status(assignment_status)
        assignment_conflict_report = flow_root / "contexts" / f"{assignment_id(assignment)}.conflicts.md"
        if assignment_status == "blocked":
            checks.append(check("FAIL", "assignment context status is blocked"))
        elif assignment_status == "requires_approval":
            checks.append(check("FAIL", "assignment context requires approval"))
        elif assignment_status == "warn":
            checks.append(check("WARN", "assignment context is usable with warnings"))
        else:
            checks.append(check("PASS", "assignment context status is pass"))
        checks.append(check("PASS" if assignment_conflict_report.is_file() else "FAIL", "assignment-specific conflict report found"))
        if assignment_conflict_report.is_file():
            checks.append(check("PASS" if _project_session_read_service.report_status(assignment_conflict_report) == assignment_status else "FAIL", "assignment conflict report status matches resolver"))
        ecp_candidates = sorted((flow_root / "contexts").glob(f"{assignment_id(assignment)}*.ecp.yaml"), key=lambda path: path.stat().st_mtime, reverse=True)
        ecp = ecp_candidates[0] if ecp_candidates else flow_root / "contexts" / f"{assignment_id(assignment)}.ecp.yaml"
        if ecp.is_file():
            ecp_text = ecp.read_text(encoding="utf-8", errors="replace")
            checksum = sha256_file(assignment) if assignment.is_file() else "missing"
            checks.append(check("PASS" if checksum in ecp_text else "FAIL", f"assignment ECP is fresh ({rel(ecp, project_root)})"))
            ecp_data = _AnswersDocumentReader().read(ecp)
            ecp_status = ecp_data.get("context_status") if isinstance(ecp_data, dict) else None
            checks.append(check("PASS" if ecp_status == context_status else "FAIL", f"assignment ECP context_status is {ecp_status}"))
            report_ref = ecp_data.get("conflict_report") if isinstance(ecp_data, dict) else None
            checks.append(check("PASS" if report_ref == rel(assignment_conflict_report, project_root) else "FAIL", "assignment ECP references assignment conflict report"))
            ecp_checksums = ecp_data.get("checksums", {}) if isinstance(ecp_data, dict) else {}
            expected_context_index_checksum = sha256_file(context_index) if context_index.is_file() else "missing"
            checks.append(
                check(
                    "PASS" if ecp_checksums.get("context_index") == expected_context_index_checksum else "FAIL",
                    "assignment ECP context index checksum is fresh",
                )
            )
        else:
            checks.append(check("FAIL" if assignment_status != "blocked" else "PASS", "assignment ECP missing"))

    result = print_checks(checks)
    _process_event_recorder.emit_process_event(
        project_root,
        "gate.failed" if result else "gate.passed",
        severity="error" if result else "info",
        payload={"command": "doctor-context", "result": "fail" if result else "pass"},
    )
    return result


def command_doctor_project(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = _run_task_inputs.require_flow_root(project_root)
    checks: list[Check] = []
    manifest = flow_root / "process-forge.yaml"
    local_manifest = flow_root / "process-forge.local.yaml"
    gitignore = project_root / ".gitignore"
    auto_workplace_mode = False
    workplace_manifest_path: Path | None = None

    if manifest.is_file():
        checks.append(check("PASS", f"{rel(manifest, project_root)} found"))
        text = manifest.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "public manifest has no local absolute paths"))
        checks.append(check("PASS" if not contains_secret_value(text) else "FAIL", "public manifest contains no secret values"))
        loaded_manifest = _update_document_reader.doctor_yaml(
            manifest,
            "process-forge-manifest.schema.json",
            "project ProcessForge manifest",
            checks,
        )
        manifest_data = loaded_manifest or {}
    else:
        checks.append(
            check_with_hint(
                "FAIL",
                f"{rel(manifest, project_root)} missing",
                "The project has not been onboarded into ProcessForge or the .pf flow root is incomplete.",
                "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic --apply",
            )
        )
        manifest_data = {}

    distribution_root: Path | None = None
    if local_manifest.is_file():
        checks.append(check("PASS", "process-forge.local.yaml found"))
        workplace = _project_coordination_state.resolve_workplace_manifest(local_manifest)
        if workplace and workplace.is_file():
            workplace_manifest_path = workplace
            checks.append(check("PASS", "workplace manifest is reachable"))
            registry = _workplace_registry_reader.resolve_registry_path(workplace, "distributions", "distributions.yaml")
            checks.append(check("PASS" if registry.is_file() else "FAIL", "workplace distributions registry is reachable"))
            distribution_root = resolve_distribution_path(workplace, "processforge")
        else:
            checks.append(
                check_with_hint(
                    "FAIL",
                    "workplace manifest is missing or unreachable",
                    "The local project config points to a workplace manifest that cannot be read.",
                    "update .pf/process-forge.local.yaml so manifest points to an existing workplace.yaml",
                )
            )
    else:
        workplace_data = manifest_data.get("workplace", {}) if isinstance(manifest_data.get("workplace"), dict) else {}
        if workplace_data.get("reference") == "auto":
            auto_workplace_mode = True
            checks.append(check("PASS", "process-forge.local.yaml omitted by explicit workplace.reference auto mode"))
            distribution_root = project_root
        else:
            checks.append(
                check_with_hint(
                    "FAIL",
                    "process-forge.local.yaml missing",
                    "Linked projects need private local workplace/distribution coordinates.",
                    "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic --apply",
                    "set workplace.reference: auto only for self-contained distribution dogfooding projects",
                )
            )

    checks.extend(distribution_checks(distribution_root))
    scan_policy = _project_scan_policy.scan_policy_from_manifest(manifest_data)
    if ProjectScanPolicy.looks_like_processforge_distribution(project_root) and not _project_initialization_inputs.allows_core(manifest_data):
        checks.append(
            check_with_hint(
                "FAIL",
                "project root looks like ProcessForge distribution",
                "This root contains ProcessForge core files and should not be treated as a generic project source tree.",
                "set project.type to processforge-development or processforge-core-development, or choose a normal project root",
            )
        )
    path_roles = _project_scan_policy.project_path_roles(project_root, distribution_root, workplace_manifest_path, manifest_data)
    guarded_roles = {"distribution_root", "workplace_root", "knowledge_root"}
    for role in path_roles:
        role_name = str(role.get("role"))
        if role_name not in guarded_roles:
            continue
        role_path_text = str(role.get("path") or "")
        role_path = Path(role_path_text)
        if not role_path.is_absolute():
            role_path = (project_root / role_path).resolve()
        if not path_is_relative_to(role_path, project_root):
            continue
        same_as_project = role_path.resolve() == project_root.resolve()
        if same_as_project and role_name == "distribution_root" and _project_initialization_inputs.allows_core(manifest_data):
            checks.append(check("PASS", "ProcessForge distribution root allowed by explicit project type"))
            continue
        if same_as_project:
            continue
        if not scan_policy.get("enabled", True):
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"project root contains {role_name} and scan guards are disabled",
                    "Distribution, workplace, and knowledge roots must not be scanned as normal project source.",
                    "enable scan_policy guards or move the supporting root outside the project source root",
                )
            )
        elif role_name == "knowledge_root":
            checks.append(
                check_with_hint(
                    "WARN",
                    "knowledge root is inside project root",
                    "It will be treated as external knowledge, not as project source, unless explicitly included.",
                    "keep scan_policy.exclude_roles including knowledge_root",
                )
            )
        else:
            checks.append(
                check_with_hint(
                    "WARN",
                    "project root contains ProcessForge distribution/workplace subtree",
                    "This subtree will be excluded from project source scan by role-aware scan guards.",
                    "keep scan_policy.exclude_roles including distribution_root and workplace_root",
                )
            )
    checks.extend(_hook_configuration_reader.validate(project_root))
    checks.extend(coordination_doctor_checks(project_root))

    if gitignore.is_file():
        ignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for entry in [".codex/hooks.json", ".pf/process-forge.local.yaml", ".pf/runtime/", ".pf/cache/"]:
            exact = entry in ignore_text
            effective = exact or gitignore_effectively_protects(project_root, entry) is True
            if effective:
                checks.append(check("PASS", f".gitignore protects {entry}"))
                if not exact:
                    checks.append(
                        check_with_hint(
                            "WARN",
                            f".gitignore missing recommended explicit entry {entry}",
                            "Git effective ignore rules protect the private path, but the policy line is not explicit.",
                            f"optionally add {entry} to .gitignore for readability",
                        )
                    )
            else:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f".gitignore missing {entry}",
                        "Private local config and runtime data must stay out of public project files.",
                        f"add {entry} to .gitignore",
                    )
                )
    else:
        checks.append(check("FAIL", ".gitignore missing"))

    package_exists = any((flow_root / "packages").glob("project.*.yaml")) if (flow_root / "packages").is_dir() else False
    checks.append(check("PASS" if package_exists else ("WARN" if auto_workplace_mode else "FAIL"), "project package draft exists"))
    resource_report = flow_root / "artifacts" / "global-resource-matching-report.md"
    missing_capabilities = _report_projection_reader.section_items(resource_report, "## Missing Required Capabilities")
    capability_waivers = active_capability_waivers(project_root) if missing_capabilities else {}
    unwaived_capabilities = [capability for capability in missing_capabilities if capability not in capability_waivers]
    waived_capabilities = [capability for capability in missing_capabilities if capability in capability_waivers]
    if unwaived_capabilities:
        checks.append(
            check_with_hint(
                "FAIL",
                "required capability registry declarations are missing: " + ", ".join(unwaived_capabilities),
                "ProcessForge capability resolution is registry-driven. This means no active provider declared the capability; it does not prove the runtime lacked actual access.",
                "register the capability provider in the workplace, rerun project-onboard or project-context-refresh, then rerun doctor-project",
                _report_projection_reader.waiver_help(),
            )
        )
    elif waived_capabilities:
        checks.append(
            check(
                "WARN",
                "required capabilities covered by explicit runtime-access waiver: " + ", ".join(waived_capabilities),
            )
        )
    elif resource_report.is_file():
        checks.append(check("PASS", "required capabilities are resolved or built in"))
    if _report_projection_reader.section_has_items(resource_report, "## Missing Required Platform Contracts"):
        checks.append(check("FAIL", """required platform contract is missing from workplace registry
Why:
  The selected project type requires platform knowledge and rules.
Fix:
  python bin/pf.py platform-contract-install --workplace <workplace-root> --id <platform> --apply"""))
    if _report_projection_reader.section_has_items(resource_report, "## Missing Required Platform Resources"):
        checks.append(check("FAIL", """required platform resources are missing from workplace registries
Why:
  A platform contract declared required packages, tools, MCP providers, or templates that are not registered.
Fix:
  Register the missing resource in the workplace registry, then rerun project-onboard or project-context-refresh."""))
    if _report_projection_reader.section_has_items(resource_report, "## Missing Recommended Platform Resources"):
        checks.append(check("WARN", "recommended platform resources are missing from workplace registries"))
    checks.extend(public_snapshot_path_checks(project_root))
    checks.extend(_knowledge_resource_index_service.project_checks(project_root, distribution_root, workplace_manifest_path))

    for rel_path in [
        "runtime/bin/pf.py",
        "assignments/first-assignment.yaml",
        "artifacts/project-profile.md",
        "artifacts/project-classification-report.md",
        "artifacts/repository-map.md",
        "artifacts/project-conventions.md",
        "artifacts/global-resource-matching-report.md",
        "artifacts/project-init-proposal.md",
        "artifacts/project-onboarding-report.md",
        "reviews/project-init-review.md",
        "reviews/project-onboarding-review.md",
        "handoffs/project-ready-handoff.md",
    ]:
        path = flow_root / rel_path
        if path.is_file():
            checks.append(check("PASS", f"{rel(path, project_root)} found"))
        elif auto_workplace_mode:
            checks.append(check("WARN", f"{rel(path, project_root)} missing"))
        elif rel_path == "runtime/bin/pf.py":
            if ProjectScanPolicy.looks_like_processforge_distribution(project_root):
                checks.append(
                    check(
                        "WARN",
                        f"{rel(path, project_root)} missing for self-contained ProcessForge distribution",
                    )
                )
            else:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{rel(path, project_root)} missing",
                        "A linked project needs its local Python launcher because it does not contain ProcessForge core tools.",
                        "python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic --apply",
                    )
                )
        elif rel_path.startswith("contexts/project-context.snapshot"):
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"{rel(path, project_root)} missing",
                    "The project context snapshot is stale or absent.",
                    "python .pf/runtime/bin/pf.py project-context-refresh --project-root .",
                )
            )
        else:
            checks.append(check("FAIL", f"{rel(path, project_root)} missing"))
    return print_checks(checks)






def update_workplace_root(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.name == "workplace.yaml":
        return path.parent
    return path














































def print_update_source_list(data: dict[str, Any], *, json_output: bool = False) -> int:
    sources = _update_source_contract_policy.sorted_sources(data)
    if json_output:
        print(json.dumps({"schema_version": 1, "sources": sources}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("ID\tENABLED\tPRIORITY\tSOURCE_KIND\tCHANNELS\tLOCATION")
    for source in sources:
        channels = ",".join(str(item) for item in source.get("channels", [])) if isinstance(source.get("channels"), list) else ""
        print(
            "\t".join(
                [
                    str(source.get("id", "")),
                    str(bool(source.get("enabled", False))).lower(),
                    str(source.get("priority", "")),
                    _update_site_policy.source_kind(source),
                    channels,
                    _update_site_policy.location(source, "provider"),
                ]
            )
        )
    return 0


def command_update_bootstrap_source_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = _update_document_reader.source_registry(workplace_root)
    data = _update_document_reader.yaml(path)
    if not data:
        print(f"FAIL: update source registry not found or invalid: {path}")
        return 1
    return print_update_source_list(data, json_output=args.json)


def command_update_bootstrap_source_validate(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = _update_document_reader.source_registry(workplace_root)
    checks = _update_source_contract_policy.validate_registry(_update_document_reader.yaml(path), path)
    return print_checks(checks)


def command_update_sources(args: argparse.Namespace) -> int:
    if not args.list and not args.validate:
        print("FAIL: choose --list or --validate")
        return 1
    if args.validate:
        status = command_update_bootstrap_source_validate(args)
        if status != 0 or not args.list:
            return status
    return command_update_bootstrap_source_list(args)


















def build_installed_update_sites(workplace_root: Path) -> tuple[dict[str, Any], list[Check]]:
    checks: list[Check] = []
    overrides_path = _update_document_reader.overrides_path(workplace_root)
    if overrides_path.is_file():
        checks.extend(_update_document_validation_service.site_overrides(_update_document_reader.yaml(overrides_path), overrides_path))
    overrides = _update_registry_reader.overrides(workplace_root)
    installed_versions = _update_registry_reader.installed_versions(workplace_root)
    sites: list[dict[str, Any]] = []
    for record in _update_registry_reader.entities(workplace_root):
        installed_version = installed_versions.get((record["type"], record["id"]), record["version"])
        data = record["data"]
        update_sites = data.get("update_sites")
        if isinstance(update_sites, list):
            seen: set[str] = set()
            for index, site in enumerate(update_sites):
                label = f"{rel(record['manifest_path'], workplace_root)}.update_sites[{index}]"
                _update_source_contract_policy.append_source_checks(checks, site, label, provider_key="type")
                if isinstance(site, dict) and isinstance(site.get("manifest_url"), str):
                    source_id = _update_site_policy.source_id(site)
                    if source_id in seen:
                        checks.append(check("FAIL", f"{label} duplicate update site id {source_id}"))
                    seen.add(source_id)
                    sites.append(
                        _update_site_policy.record(
                            workplace_root,
                            record["type"],
                            record["id"],
                            record["scope"],
                            installed_version,
                            record["manifest_path"],
                            site,
                            overrides,
                        )
                    )
        elif update_sites is not None:
            checks.append(check("FAIL", f"{rel(record['manifest_path'], workplace_root)} update_sites must be a list"))

        if record["type"] == "knowledge_package":
            resources = data.get("resources") if isinstance(data.get("resources"), list) else []
            for resource in resources:
                if not isinstance(resource, dict) or not resource.get("id"):
                    continue
                update_policy = resource.get("update_policy") if isinstance(resource.get("update_policy"), dict) else {}
                resource_sites = resource.get("update_sites") or update_policy.get("update_sites")
                if resource_sites is None:
                    continue
                resource_subject_id = f"{record['id']}/{resource.get('id')}"
                if not isinstance(resource_sites, list):
                    checks.append(check("FAIL", f"{rel(record['manifest_path'], workplace_root)} resource {resource.get('id')} update_sites must be a list"))
                    continue
                for index, site in enumerate(resource_sites):
                    label = f"{rel(record['manifest_path'], workplace_root)}.resources[{resource.get('id')}].update_sites[{index}]"
                    _update_source_contract_policy.append_source_checks(checks, site, label, provider_key="type")
                    if isinstance(site, dict) and isinstance(site.get("manifest_url"), str):
                        sites.append(
                            _update_site_policy.record(
                                workplace_root,
                                "knowledge_resource",
                                resource_subject_id,
                                record["scope"],
                                str(resource.get("version") or record["version"]),
                                record["manifest_path"],
                                site,
                                overrides,
                                parent={"type": "knowledge_package", "id": record["id"]},
                            )
                        )

    sites.sort(key=lambda item: (item["subject"]["type"], item["subject"]["id"], int(item["source"].get("priority", 1000)), item["site_id"]))
    derived = {"schema_version": 1, "generated_at": _core_common_clock.now_utc(), "sites": sites}
    return derived, checks


def print_derived_update_sites(data: dict[str, Any], *, subject_type: str = "all", json_output: bool = False) -> int:
    sites = data.get("sites") if isinstance(data.get("sites"), list) else []
    if subject_type != "all":
        sites = [site for site in sites if isinstance(site, dict) and site.get("subject", {}).get("type") == subject_type]
    if json_output:
        print(json.dumps({"schema_version": 1, "sites": sites}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("SITE_ID\tENABLED\tSUBJECT_TYPE\tSUBJECT_ID\tSOURCE_TYPE\tLOCATION\tMANIFEST")
    for site in sites:
        if not isinstance(site, dict):
            continue
        subject = site.get("subject") if isinstance(site.get("subject"), dict) else {}
        source = site.get("source") if isinstance(site.get("source"), dict) else {}
        print(
            "\t".join(
                [
                    str(site.get("site_id", "")),
                    str(bool(site.get("enabled", False))).lower(),
                    str(subject.get("type", "")),
                    str(subject.get("id", "")),
                    str(source.get("type", "")),
                    _update_site_policy.location(source, "type"),
                    str(site.get("manifest_path", "")),
                ]
            )
        )
    return 0


def command_update_entity_sources_rebuild(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    derived, checks = build_installed_update_sites(workplace_root)
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        print_checks(checks)
        return 1
    target = _update_document_reader.derived_sites_path(workplace_root)
    if args.dry_run:
        print(json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"SITES: {len(derived['sites'])}")
    print(f"TARGET: {rel(target, workplace_root)}")
    return 0


def command_update_entity_sources_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    target = _update_document_reader.derived_sites_path(workplace_root)
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: derived registry is invalid JSON: {target}: {exc}")
            return 1
    else:
        data, checks = build_installed_update_sites(workplace_root)
        failures = [item for item in checks if item.level == "FAIL"]
        if failures:
            print_checks(checks)
            return 1
        if not args.json:
            print(f"WARN: {rel(target, workplace_root)} missing; listing live manifest scan")
    return print_derived_update_sites(data, subject_type=args.subject_type, json_output=args.json)




def command_update_manifest_validate(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        print(f"FAIL: manifest file not found: {path}")
        return 1
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL: invalid JSON: {path}: {exc}")
            return 1
    else:
        data = _update_document_reader.yaml(path)
    if not isinstance(data, dict) or not data:
        print(f"FAIL: normalized update manifest is empty or invalid: {path}")
        return 1
    return print_checks(_update_document_validation_service.normalized_manifest(data, path))








def command_self_update_check(args: argparse.Namespace) -> int:
    distribution_root = Path(args.distribution_root).expanduser().resolve() if args.distribution_root else ROOT
    channel = args.channel
    update_index = _update_document_reader.index(distribution_root)
    if not update_index:
        print(f"FAIL: update index not found under {distribution_root / 'updates'}")
        return 1
    latest = _update_version_selection_policy.latest(update_index, channel)
    product = update_index.get("product", {}) if isinstance(update_index.get("product"), dict) else {}
    current = str(args.current_version or product.get("current_version") or "1.0.0")
    print(f"PRODUCT: {product.get('id', 'processforge')}")
    print(f"CURRENT: {current}")
    print(f"CHANNEL: {channel}")
    print(f"LATEST: {latest.get('version') if latest else 'none'}")
    if latest and str(latest.get("version")) != current:
        migration = latest.get("migration", {}) if isinstance(latest.get("migration"), dict) else {}
        print(f"UPDATE: available")
        print(f"MIGRATION_REQUIRED: {bool(migration.get('required', False))}")
        if migration.get("guide"):
            print(f"GUIDE: {migration.get('guide')}")
    else:
        print("UPDATE: none")
    return 0


def command_project_upgrade_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = _run_task_inputs.require_flow_root(project_root)
    manifest = load_yaml_document(flow_root / "process-forge.yaml")
    process_forge_data = manifest.get("process_forge", {}) if isinstance(manifest.get("process_forge"), dict) else {}
    current = str(args.current_version or process_forge_data.get("version") or "1.0.0")
    distribution_root: Path | None = None
    local_manifest = flow_root / "process-forge.local.yaml"
    if local_manifest.is_file():
        workplace = _project_coordination_state.resolve_workplace_manifest(local_manifest)
        if workplace and workplace.is_file():
            distribution_root = resolve_distribution_path(workplace, "processforge")
    if not distribution_root:
        distribution_root = project_root if (project_root / "updates").is_dir() else ROOT
    update_index = _update_document_reader.index(distribution_root)
    if not update_index:
        print(f"FAIL: update index not found under {distribution_root / 'updates'}")
        return 1
    latest = _update_version_selection_policy.latest(update_index, args.channel)
    report = _update_assessment_renderer.render(project_root, current, args.channel, latest)
    target = flow_root / "artifacts" / "processforge-update-assessment.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(report), encoding="utf-8")
    print(f"WROTE: {rel(target, project_root)}")
    return 0


































def command_update_candidates_refresh(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    channel = args.channel
    derived, checks = build_installed_update_sites(workplace_root)
    failures = [item for item in checks if item.level == "FAIL"]
    if failures:
        print_checks(checks)
        return 1
    if not args.dry_run:
        target_sites = _update_document_reader.derived_sites_path(workplace_root)
        target_sites.parent.mkdir(parents=True, exist_ok=True)
        target_sites.write_text(json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    installed = _update_registry_reader.installed_subjects(workplace_root)
    candidates: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for site in derived.get("sites", []) if isinstance(derived.get("sites"), list) else []:
        if not isinstance(site, dict) or not bool(site.get("enabled", False)):
            continue
        subject = site.get("subject") if isinstance(site.get("subject"), dict) else {}
        if subject.get("type") == "project_pf":
            continue
        source = site.get("source") if isinstance(site.get("source"), dict) else {}
        effective_channel = str(source.get("channel") or channel)
        raw_manifest, warnings = _update_transfer_service.manifest(source, workplace_root)
        if not raw_manifest:
            conflicts.append({"site_id": site.get("site_id"), "reason": "; ".join(warnings) or "manifest fetch failed"})
            continue
        versions = _update_version_selection_policy.normalize(raw_manifest, site, effective_channel)
        installed_subject = installed.get((str(subject.get("type")), str(subject.get("id"))), {})
        installed_version = str(subject.get("installed_version") or installed_subject.get("version") or "")
        selected, compare_warnings = _update_version_selection_policy.select(versions, installed_version or None)
        warnings.extend(compare_warnings)
        if not selected:
            continue
        source_policy = _update_site_policy.policy(source, installed_subject)
        pinned = source_policy.get("pin_version")
        if isinstance(pinned, str) and pinned.strip() and str(selected.get("version")) != pinned:
            conflicts.append({"site_id": site.get("site_id"), "reason": f"candidate {selected.get('version')} blocked by pin_version {pinned}"})
            continue
        if source_policy.get("allow_major") is False and installed_version:
            installed_major = _resource_version_policy.key(installed_version)[1]
            selected_major = _resource_version_policy.key(str(selected.get("version")))[1]
            if isinstance(installed_major, tuple) and isinstance(selected_major, tuple) and installed_major[0] != selected_major[0]:
                conflicts.append({"site_id": site.get("site_id"), "reason": f"candidate {selected.get('version')} blocked by allow_major=false"})
                continue
        trust = source.get("trust") if isinstance(source.get("trust"), dict) else {}
        require_sha = bool(trust.get("require_sha256", trust.get("require_sha256_for_install", source_policy.get("require_sha256", True))))
        sha256 = str(selected.get("sha256") or "")
        installable = bool(selected.get("download_url")) and (not require_sha or bool(sha256))
        status = "available" if installable else "missing_required_hash"
        candidate = {
            "id": _update_version_selection_policy.candidate_id(str(subject.get("type")), str(subject.get("id")), str(selected.get("version")), str(selected.get("source_id"))),
            "subject": selected.get("subject") or subject,
            "installed_version": installed_version or None,
            "current_version": installed_version or None,
            "available_version": str(selected.get("version")),
            "channel": effective_channel,
            "source_id": str(selected.get("source_id")),
            "site_id": site.get("site_id"),
            "manifest_url": selected.get("manifest_url"),
            "changelog_url": selected.get("changelog_url"),
            "download_url": selected.get("download_url"),
            "sha256": sha256 or None,
            "artifact_sha256": sha256 or None,
            "breaking": bool(selected.get("breaking", False)),
            "migration_required": bool(selected.get("migration_required", False)),
            "status": status,
            "installable": installable,
            "reason": None if installable else "sha256 required before stage/apply",
            "warnings": sorted(set(warnings)),
            "update_policy": selected.get("update_policy") or source_policy,
            "post_update_doctor": selected.get("post_update_doctor") or source_policy.get("post_update_doctor", []),
        }
        candidates.append(candidate)
    cache = {"schema_version": 1, "generated_at": _core_common_clock.now_utc(), "channel": channel, "candidates": candidates, "conflicts": conflicts}
    if args.dry_run:
        print(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    path = _update_document_reader.candidates_path(workplace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    create_update_notifications_from_candidates(workplace_root, candidates)
    print(f"CANDIDATES: {len(candidates)}")
    print(f"TARGET: {rel(path, workplace_root)}")
    print(f"NOTIFICATIONS: {rel(_update_document_reader.notifications_path(workplace_root), workplace_root)}")
    return 0


def command_update_candidates_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    data = _update_candidate_reader.read(workplace_root)
    candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
    if args.json:
        print(json.dumps({"schema_version": 1, "candidates": candidates}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("ID\tSTATUS\tSUBJECT_TYPE\tSUBJECT_ID\tCURRENT\tAVAILABLE\tCHANGELOG")
    for item in candidates:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject") if isinstance(item.get("subject"), dict) else {}
        print("\t".join([str(item.get("id", "")), str(item.get("status", "")), str(subject.get("type", "")), str(subject.get("id", "")), str(item.get("installed_version") or item.get("current_version") or ""), str(item.get("available_version", "")), str(item.get("changelog_url") or "")]))
    return 0


def command_update_candidates_show(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    if not candidate:
        print(f"FAIL: candidate not found: {args.candidate}")
        return 1
    print(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_update_candidates_clear(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    for path in [_update_document_reader.candidates_path(workplace_root), _update_document_reader.notifications_path(workplace_root)]:
        if path.is_file() and not args.dry_run:
            path.unlink()
    print("CLEARED: update candidates and notifications" if not args.dry_run else "DRY_RUN: would clear update candidates and notifications")
    return 0


def create_update_notifications_from_candidates(workplace_root: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    path = _update_document_reader.notifications_path(workplace_root)
    existing = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data.get("notifications", []) if isinstance(data, dict) and isinstance(data.get("notifications"), list) else []:
                if isinstance(item, dict) and item.get("id"):
                    existing[str(item["id"])] = item
        except json.JSONDecodeError:
            existing = {}
    now = _core_common_clock.now_utc()
    for candidate in candidates:
        if candidate.get("status") != "available":
            continue
        subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
        notification_id = f"notification-{candidate.get('id')}"
        previous = existing.get(notification_id, {})
        if previous.get("status") == "acknowledged":
            continue
        existing[notification_id] = {
            "id": notification_id,
            "type": "update_available",
            "candidate_id": candidate.get("id"),
            "subject": subject,
            "channel": candidate.get("channel") or "stable",
            "version": candidate.get("available_version"),
            "current_version": candidate.get("installed_version") or candidate.get("current_version"),
            "available_version": candidate.get("available_version"),
            "source_id": candidate.get("source_id"),
            "changelog_url": candidate.get("changelog_url"),
            "message": f"Update available: {subject.get('id')} {candidate.get('installed_version') or 'unknown'} -> {candidate.get('available_version')}",
            "first_seen_at": previous.get("first_seen_at") or now,
            "last_notified_at": now,
            "status": "notified",
            "acknowledged_at": None,
            "snoozed_until": None,
        }
    result = {"schema_version": 1, "updated_at": now, "notifications": sorted(existing.values(), key=lambda item: str(item.get("id")))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mirror_update_notifications_to_director(workplace_root, result)
    return result


def mirror_update_notifications_to_director(workplace_root: Path, notifications: dict[str, Any]) -> None:
    office = workplace_root / "director" / "inbox"
    if not office.is_dir():
        return
    for item in notifications.get("notifications", []) if isinstance(notifications.get("notifications"), list) else []:
        if not isinstance(item, dict) or item.get("status") == "acknowledged":
            continue
        target = office / f"{safe_id(str(item.get('id')))}.json"
        if target.exists():
            continue
        target.write_text(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_update_notifications_create(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    data = _update_candidate_reader.read(workplace_root)
    candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
    notifications = create_update_notifications_from_candidates(workplace_root, [item for item in candidates if isinstance(item, dict)])
    print(f"NOTIFICATIONS: {len(notifications.get('notifications', []))}")
    return 0


def command_update_notifications_list(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = _update_document_reader.notifications_path(workplace_root)
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    notifications = data.get("notifications") if isinstance(data.get("notifications"), list) else []
    if args.json:
        print(json.dumps({"schema_version": 1, "notifications": notifications}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("ID\tSTATUS\tSUBJECT_ID\tCURRENT\tAVAILABLE\tCHANGELOG")
    for item in notifications:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject") if isinstance(item.get("subject"), dict) else {}
        print("\t".join([str(item.get("id", "")), str(item.get("status", "")), str(subject.get("id", "")), str(item.get("current_version") or ""), str(item.get("available_version") or item.get("version") or ""), str(item.get("changelog_url") or "")]))
    return 0


def command_update_notifications_acknowledge(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    path = _update_document_reader.notifications_path(workplace_root)
    if not path.is_file():
        print(f"FAIL: notifications cache not found: {path}")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: notifications cache invalid JSON: {exc}")
        return 1
    changed = False
    for item in data.get("notifications", []) if isinstance(data.get("notifications"), list) else []:
        if isinstance(item, dict) and item.get("id") == args.notification:
            item["status"] = "acknowledged"
            item["acknowledged_at"] = _core_common_clock.now_utc()
            changed = True
    if not changed:
        print(f"FAIL: notification not found: {args.notification}")
        return 1
    data["updated_at"] = _core_common_clock.now_utc()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ACKNOWLEDGED: {args.notification}")
    return 0


def command_update_changelog_show(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    if not candidate:
        print(f"FAIL: candidate not found: {args.candidate}")
        return 1
    changelog_url = str(candidate.get("changelog_url") or "")
    print(f"CHANGELOG_URL: {changelog_url or 'none'}")
    if changelog_url.startswith("file://") or (changelog_url and "://" not in changelog_url):
        path = _update_document_reader.file_url_path(changelog_url, workplace_root)
        if path.is_file():
            print(path.read_text(encoding="utf-8")[:4000])
    return 0


def sha256_file(path: Path) -> str:
    return _file_digests.sha256_file(path)




def safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if destination_resolved != target and destination_resolved not in target.parents:
                raise ValueError(f"unsafe archive member: {info.filename}")
        archive.extractall(destination)


def artifact_manifest_from_zip(archive_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if name.endswith((".yaml", ".yml", ".json"))]
        preferred = [name for name in names if Path(name).name in {"package.yaml", "package.yml", "template.yaml", "template.yml", "tool.yaml", "tool.yml", "process.yaml", "process.yml"}]
        for name in preferred + names:
            try:
                text = archive.read(name).decode("utf-8")
            except Exception:
                continue
            data = _update_document_reader.text(text)
            if data.get("id"):
                return data
    return {}






def command_update_stage(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    if not candidate:
        print(f"FAIL: candidate not found: {args.candidate}")
        return 1
    if candidate.get("status") != "available" or not candidate.get("installable"):
        print(f"FAIL: candidate is not installable: {candidate.get('status')}")
        return 1
    stage_dir = _update_document_reader.runtime_root(workplace_root) / "staged" / str(candidate["id"])
    if args.dry_run:
        print(f"DRY_RUN: would stage {candidate['id']} into {rel(stage_dir, workplace_root)}")
        return 0
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = _update_transfer_service.artifact(candidate, stage_dir, workplace_root)
    actual_sha = sha256_file(artifact_path)
    expected_sha = str(candidate.get("sha256") or candidate.get("artifact_sha256") or "")
    verified = not expected_sha or actual_sha.lower() == expected_sha.lower()
    record = {
        "schema_version": 1,
        "candidate_id": candidate["id"],
        "staged_at": _core_common_clock.now_utc(),
        "status": "verified" if verified else "failed",
        "workplace": rel(workplace_root, workplace_root.parent),
        "candidate": candidate,
        "artifact": {"path": rel(artifact_path, workplace_root), "sha256": actual_sha, "expected_sha256": expected_sha or None},
        "verification": {"sha256": "pass" if verified else "fail"},
    }
    _update_document_reader.staged_path(workplace_root, str(candidate["id"])).write_text(dump_yaml(record), encoding="utf-8")
    print(f"STAGED: {rel(artifact_path, workplace_root)}")
    print(f"SHA256: {'pass' if verified else 'fail'}")
    return 0 if verified else 1


def command_update_verify(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    record = _update_document_reader.staged_record(workplace_root, args.candidate)
    if not candidate or not record:
        print(f"FAIL: staged candidate not found: {args.candidate}")
        return 1
    artifact_info = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
    artifact_path = path_resolution_to_path(workplace_path_resolution(workplace_root, str(artifact_info.get("path") or "")))
    if not artifact_path.is_file():
        print(f"FAIL: staged artifact missing: {artifact_path}")
        return 1
    actual_sha = sha256_file(artifact_path)
    expected_sha = str(candidate.get("sha256") or candidate.get("artifact_sha256") or "")
    if expected_sha and actual_sha.lower() != expected_sha.lower():
        print("FAIL: sha256 mismatch")
        return 1
    subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
    manifest = artifact_manifest_from_zip(artifact_path) if artifact_path.suffix.lower() == ".zip" else {}
    if manifest:
        if str(manifest.get("id") or "") != str(subject.get("id") or ""):
            print("FAIL: artifact subject id mismatch")
            return 1
        if str(manifest.get("type") or subject.get("type") or "") != str(subject.get("type") or ""):
            print("FAIL: artifact subject type mismatch")
            return 1
        if str(manifest.get("version") or "") != str(candidate.get("available_version") or ""):
            print("FAIL: artifact version mismatch")
            return 1
    record["status"] = "verified"
    record["verified_at"] = _core_common_clock.now_utc()
    record["verification"] = {"sha256": "pass", "subject_identity": "pass" if manifest else "not_applicable"}
    _update_document_reader.staged_path(workplace_root, args.candidate).write_text(dump_yaml(record), encoding="utf-8")
    print(f"VERIFIED: {args.candidate}")
    return 0




def update_installed_subject_version(workplace_root: Path, candidate: dict[str, Any], install_path: Path | None = None) -> None:
    path = _update_document_reader.installed_registry(workplace_root)
    data = _update_document_reader.yaml(path)
    if not data:
        data = {"schema_version": 1, "subjects": []}
    subjects = data.get("subjects")
    if not isinstance(subjects, list):
        subjects = []
        data["subjects"] = subjects
    candidate_subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
    found = False
    for subject in subjects:
        if not isinstance(subject, dict):
            continue
        if subject.get("type") == candidate_subject.get("type") and subject.get("id") == candidate_subject.get("id"):
            subject["version"] = candidate.get("available_version")
            subject["updated_at"] = _core_common_clock.now_utc()
            if install_path:
                subject["install_path"] = rel(install_path, workplace_root)
            found = True
    if not found:
        subjects.append({"type": candidate_subject.get("type"), "id": candidate_subject.get("id"), "scope": candidate_subject.get("scope") or "global", "version": candidate.get("available_version"), "installed_at": _core_common_clock.now_utc(), "install_path": rel(install_path, workplace_root) if install_path else None})
    data["updated_at"] = _core_common_clock.now_utc()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")


SNAPSHOT_IMPACTING_UPDATE_SUBJECT_TYPES = {
    "knowledge_package",
    "knowledge_resource",
    "template_package",
    "reusable_template",
    "tool_definition",
    "tool_package",
    "platform_contract",
    "process_package",
}


def project_roots_under_workplace(workplace_root: Path) -> list[Path]:
    candidates = []
    if (workplace_root / ".pf" / "process-forge.yaml").is_file():
        candidates.append(workplace_root)
    projects_root = workplace_root / "projects"
    if projects_root.is_dir():
        for path in sorted(projects_root.iterdir()):
            if path.is_dir() and (path / ".pf" / "process-forge.yaml").is_file():
                candidates.append(path)
    return candidates


def mark_impacted_project_contexts_after_update(workplace_root: Path, candidate: dict[str, Any], *, reason: str) -> list[Path]:
    subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
    subject_type = str(subject.get("type") or "")
    subject_id = str(subject.get("id") or "")
    if subject_type not in SNAPSHOT_IMPACTING_UPDATE_SUBJECT_TYPES:
        return []
    marked: list[Path] = []
    for project_root in project_roots_under_workplace(workplace_root):
        snapshot_path, _snapshot_md = project_context_snapshot_paths(project_root)
        if not snapshot_path.is_file():
            continue
        snapshot = load_yaml_document(snapshot_path)
        resolved = snapshot.get("resolved") if isinstance(snapshot.get("resolved"), dict) else {}
        resources = resolved.get("knowledge_resources") if isinstance(resolved.get("knowledge_resources"), list) else []
        impacted = subject_type != "knowledge_resource"
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            if resource.get("id") == subject_id or resource.get("package_id") == subject_id:
                impacted = True
        if impacted:
            marked.append(mark_project_context_stale(project_root, subject=subject_id or subject_type, reason=reason, source="update-apply"))
    return marked


def command_update_apply(args: argparse.Namespace) -> int:
    if not args.confirm:
        print("FAIL: update apply requires --confirm")
        return 1
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    record = _update_document_reader.staged_record(workplace_root, args.candidate)
    if not candidate or not record:
        print(f"FAIL: staged candidate not found: {args.candidate}")
        return 1
    verify_status = command_update_verify(argparse.Namespace(workplace=args.workplace, candidate=args.candidate))
    if verify_status != 0:
        return verify_status
    subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
    subject_type = str(subject.get("type") or "")
    policy = candidate.get("update_policy") if isinstance(candidate.get("update_policy"), dict) else {}
    if policy.get("mode") == "custom_command_requires_confirmation" and not args.allow_custom_command:
        print("FAIL: custom command update policy requires explicit --allow-custom-command and is not executed by default")
        return 1
    artifact_info = record.get("artifact") if isinstance(record.get("artifact"), dict) else {}
    artifact_path = path_resolution_to_path(workplace_path_resolution(workplace_root, str(artifact_info.get("path") or "")))
    backup_dir = _update_document_reader.runtime_root(workplace_root) / "backups" / args.candidate
    apply_dir = _update_document_reader.runtime_root(workplace_root) / "applied" / args.candidate
    if args.dry_run:
        print(f"DRY_RUN: would apply {args.candidate}")
        return 0
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    if policy.get("mode") == "replace_file" or subject_type in {"tool_definition", "tool_package", "tool"}:
        paths = policy.get("executable_paths") if isinstance(policy.get("executable_paths"), list) else []
        if not paths:
            print("FAIL: tool update requires update_policy.executable_paths")
            return 1
        destination = path_resolution_to_path(workplace_path_resolution(workplace_root, str(paths[0])))
        if destination.exists():
            backup_target = backup_dir / "previous-file"
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup_target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact_path, destination)
        install_path = destination
    else:
        install_path = _update_registry_reader.install_path(workplace_root, candidate)
        if install_path.exists():
            backup_target = backup_dir / "previous"
            shutil.copytree(install_path, backup_target)
            shutil.rmtree(install_path)
        install_path.parent.mkdir(parents=True, exist_ok=True)
        if artifact_path.suffix.lower() == ".zip":
            safe_extract_zip(artifact_path, install_path)
        else:
            install_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(artifact_path, install_path / artifact_path.name)
    update_installed_subject_version(workplace_root, candidate, install_path)
    apply_dir.mkdir(parents=True, exist_ok=True)
    apply_record = {"schema_version": 1, "candidate_id": args.candidate, "applied_at": _core_common_clock.now_utc(), "status": "applied", "subject": subject, "installed_version": candidate.get("available_version"), "install_path": rel(install_path, workplace_root), "backup_path": rel(backup_dir, workplace_root), "post_update_doctor": candidate.get("post_update_doctor", [])}
    (apply_dir / "apply-record.yaml").write_text(dump_yaml(apply_record), encoding="utf-8")
    marked = mark_impacted_project_contexts_after_update(workplace_root, candidate, reason="update-applied")
    print(f"APPLIED: {args.candidate}")
    print(f"INSTALL_PATH: {rel(install_path, workplace_root)}")
    print(f"BACKUP: {rel(backup_dir, workplace_root)}")
    if marked:
        print("SNAPSHOTS_MARKED_STALE: " + ", ".join(rel(path, workplace_root) for path in marked))
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="update-apply"))
    return 0


def command_update_rollback(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    candidate = _update_candidate_reader.find(workplace_root, args.candidate)
    if not candidate:
        print(f"FAIL: candidate not found: {args.candidate}")
        return 1
    subject = candidate.get("subject") if isinstance(candidate.get("subject"), dict) else {}
    policy = candidate.get("update_policy") if isinstance(candidate.get("update_policy"), dict) else {}
    backup_dir = _update_document_reader.runtime_root(workplace_root) / "backups" / args.candidate
    if policy.get("mode") == "replace_file" or subject.get("type") in {"tool_definition", "tool_package", "tool"}:
        paths = policy.get("executable_paths") if isinstance(policy.get("executable_paths"), list) else []
        if not paths:
            print("FAIL: tool rollback requires update_policy.executable_paths")
            return 1
        destination = path_resolution_to_path(workplace_path_resolution(workplace_root, str(paths[0])))
        backup_file = backup_dir / "previous-file"
        if not backup_file.is_file():
            print(f"FAIL: backup not found: {backup_file}")
            return 1
        shutil.copy2(backup_file, destination)
        restore_path = destination
    else:
        install_path = _update_registry_reader.install_path(workplace_root, candidate)
        backup_tree = backup_dir / "previous"
        if not backup_tree.is_dir():
            print(f"FAIL: backup not found: {backup_tree}")
            return 1
        if install_path.exists():
            shutil.rmtree(install_path)
        shutil.copytree(backup_tree, install_path)
        restore_path = install_path
    record = {"schema_version": 1, "candidate_id": args.candidate, "rolled_back_at": _core_common_clock.now_utc(), "status": "rolled_back", "restore_path": rel(restore_path, workplace_root)}
    rollback_dir = _update_document_reader.runtime_root(workplace_root) / "rollbacks" / args.candidate
    rollback_dir.mkdir(parents=True, exist_ok=True)
    (rollback_dir / "rollback-record.yaml").write_text(dump_yaml(record), encoding="utf-8")
    marked = mark_impacted_project_contexts_after_update(workplace_root, candidate, reason="update-rollback")
    print(f"ROLLED_BACK: {args.candidate}")
    print(f"RESTORE_PATH: {rel(restore_path, workplace_root)}")
    if marked:
        print("SNAPSHOTS_MARKED_STALE: " + ", ".join(rel(path, workplace_root) for path in marked))
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="update-rollback"))
    return 0


def command_update_doctor(args: argparse.Namespace) -> int:
    workplace_root = update_workplace_root(args.workplace)
    checks: list[Check] = []
    candidates = _update_candidate_reader.read(workplace_root)
    _update_schema_checks.append(checks, candidates, "update-candidates.schema.json", str(_update_document_reader.candidates_path(workplace_root)))
    notifications = {}
    if _update_document_reader.notifications_path(workplace_root).is_file():
        try:
            notifications = json.loads(_update_document_reader.notifications_path(workplace_root).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            notifications = {}
    if notifications:
        _update_schema_checks.append(checks, notifications, "update-notifications.schema.json", str(_update_document_reader.notifications_path(workplace_root)))
    staged_root = _update_document_reader.runtime_root(workplace_root) / "staged"
    checks.append(check("PASS" if staged_root.exists() or candidates.get("candidates") is not None else "WARN", "update runtime state readable"))
    return print_checks(checks)


def command_path_resolve(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    resolution = workplace_path_resolution(workplace_root, args.path)
    for key in ["original", "expanded", "resolved", "is_absolute", "is_private", "path_status"]:
        print(f"{key}: {resolution.get(key)}")
    if resolution.get("constants"):
        print("constants: " + ", ".join(resolution["constants"]))
    if resolution.get("errors"):
        print("errors: " + ", ".join(resolution["errors"]))
        return 1
    return 0


def local_search_runtime_snapshot(project_root: Path, workplace_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    from processforge_core.resources.snapshot import snapshot_with_resolved_search_roots

    context = project_context_check_result(project_root, explicit_workplace=str(workplace_root))
    snapshot_path, _snapshot_md = project_context_snapshot_paths(project_root)
    snapshot = load_yaml_document(snapshot_path) if snapshot_path.is_file() else {}
    runtime_snapshot = snapshot_with_resolved_search_roots(
        project_root,
        snapshot if isinstance(snapshot, dict) else {},
        workplace_root,
    )
    return context, runtime_snapshot


def workplace_search_package_manifest_index(workplace_root: Path) -> dict[str, dict[str, Any]]:
    """Compatible facade for the concrete physical Workplace catalogue."""
    from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader

    return WorkplaceSearchCatalogReader(workplace_root, distribution_root=ROOT).package_manifest_index()


def workplace_search_runtime_snapshot(workplace_root: Path) -> dict[str, Any]:
    """Compatible facade for the concrete physical Workplace search snapshot."""
    from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader

    return WorkplaceSearchCatalogReader(workplace_root, distribution_root=ROOT).runtime_snapshot()


def search_index_project_label(project_root: Path, workplace_root: Path) -> str:
    try:
        return rel(project_root, workplace_root)
    except ValueError:
        return project_root.name or str(project_root)


def write_search_index_maintenance_runtime_report(workplace_root: Path, payload: dict[str, Any]) -> Path:
    report_path = workplace_root / "runtime" / "search" / "latest-maintenance.yaml"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(ensure_trailing_newline(dump_yaml(payload)), encoding="utf-8")
    return report_path


def search_index_maintenance_for_known_projects(
    workplace_root: Path,
    *,
    reason: str,
    project_roots: list[Path] | None = None,
    verify_files: bool = True,
) -> dict[str, Any]:
    """Maintain the one Workplace index without consulting project Runtime state.

    The retained name is a compatibility shim for existing resource-management
    call sites.  ``project_roots`` is intentionally ignored: selection is a
    query-time project-snapshot concern, never an index-maintenance concern.
    """
    from processforge_core.resources.local_search import ResourceSearchIndex

    del project_roots
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "pf.search_index.maintenance",
        "created_at": _core_common_clock.now_utc(),
        "reason": reason,
        "scope": "workplace",
        "project_count": 0,
        "results": [],
    }
    results = payload["results"]
    assert isinstance(results, list)
    row: dict[str, Any] = {"scope": "workplace", "status": "pending"}
    try:
        from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader

        snapshot = WorkplaceSearchCatalogReader(workplace_root, distribution_root=ROOT).runtime_snapshot()
        tick = ResourceSearchIndex(workplace_root, snapshot, workplace_root).maintenance_tick(verify_files=verify_files)
        after = tick.get("after") if isinstance(tick.get("after"), dict) else {}
        row.update(
            {
                "status": "ok" if after.get("status") == "fresh" else "degraded",
                "action": tick.get("action"),
                "search_status": after.get("status"),
                "generation": after.get("generation"),
                "document_count": after.get("document_count"),
                "stale_resource_count": after.get("stale_resource_count"),
                "failed_file_count": after.get("failed_file_count"),
            }
        )
        if after.get("error"):
            row["error"] = after.get("error")
    except Exception as exc:  # pragma: no cover - defensive CLI boundary.
        row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    results.append(row)
    report_path = write_search_index_maintenance_runtime_report(workplace_root, payload)
    payload["report"] = rel(report_path, workplace_root)
    try:
        _workplace_resource_events.append_workplace_event(
            workplace_root,
            "search.index.maintenance.completed",
            payload={
                "reason": reason,
                "project_count": payload["project_count"],
                "report": payload["report"],
                "statuses": [row.get("status") for row in results if isinstance(row, dict)],
            },
        )
    except Exception:
        pass
    return payload


def print_search_index_maintenance_summary(payload: dict[str, Any]) -> None:
    print(f"SEARCH_INDEX_SCOPE: {payload.get('scope') or 'workplace'}")
    if payload.get("report"):
        print(f"SEARCH_INDEX_REPORT: {payload.get('report')}")
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    for row in results:
        if not isinstance(row, dict):
            continue
        project = row.get("project") or row.get("scope")
        if row.get("status") in {"ok", "degraded"}:
            print(
                "SEARCH_INDEX: "
                f"{project} action={row.get('action')} status={row.get('search_status')} "
                f"generation={row.get('generation') or 'none'} documents={row.get('document_count')}"
            )
        elif row.get("status") == "skipped":
            print(
                "SEARCH_INDEX_SKIPPED: "
                f"{project} reason={row.get('reason')} context={row.get('context_status') or 'unknown'} "
                f"next={row.get('recommended_action') or 'none'}"
            )
        elif row.get("status") == "error":
            print(f"SEARCH_INDEX_ERROR: {project} error={row.get('error')}")


def configuration_service(configuration_path: Path) -> ConfigService:
    from processforge_core.configuration import ConfigService
    from processforge_core.configuration.yaml_store import YamlConfigStore

    return ConfigService(YamlConfigStore(configuration_path))


def project_configuration_service(configuration_path: Path) -> ConfigService:
    from processforge_core.configuration import ConfigService, ProjectPFConfig
    from processforge_core.configuration.yaml_store import YamlConfigStore

    return ConfigService(YamlConfigStore(configuration_path, model=ProjectPFConfig), defaults=ProjectPFConfig())


def resource_search_index(
    project_root: Path, snapshot: dict[str, Any], workplace_root: Path
) -> ResourceSearchIndex:
    from processforge_core.resources.local_search import ResourceSearchIndex

    return ResourceSearchIndex(project_root, snapshot, workplace_root)


def search_index_doctor_result(status: dict[str, Any], context: dict[str, Any]) -> int:
    sqlite_info = status.get("sqlite") if isinstance(status.get("sqlite"), dict) else {}
    checks = [
        check("PASS" if sqlite_info.get("fts5_available") else "FAIL", "SQLite FTS5 available"),
        check("PASS" if status.get("status") != "degraded" else "FAIL", "search index readable"),
        check("PASS" if str(context.get("status") or "") in {"fresh", "fresh_with_updates"} else "WARN", f"project context freshness: {context.get('status')}"),
        check("PASS" if status.get("status") == "fresh" else "WARN", f"search index status: {status.get('status')}"),
        check("PASS" if int(status.get("failed_file_count") or 0) == 0 else "WARN", "failed file count is zero"),
    ]
    return print_checks(checks)


def command_core_update_status(args: argparse.Namespace) -> int:
    from processforge_core.maintenance.update import CoreUpdateError, core_status

    try:
        payload = core_status(Path(args.core_root).expanduser().resolve())
    except CoreUpdateError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_core_update_plan(args: argparse.Namespace) -> int:
    from processforge_core.maintenance.update import CoreUpdateError, build_plan

    try:
        payload = build_plan(
            Path(args.core_root).expanduser().resolve(),
            Path(args.archive).expanduser().resolve(),
            workplace_root=Path(args.workplace_root).expanduser().resolve() if args.workplace_root else None,
        )
    except CoreUpdateError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}, indent=2, sort_keys=True))
        return 1
    printable = {key: value for key, value in payload.items() if key != "new_manifest"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "blocked" else 2


def command_core_update_apply(args: argparse.Namespace) -> int:
    from processforge_core.maintenance.update import CoreUpdateError, apply_update

    try:
        payload = apply_update(
            Path(args.core_root).expanduser().resolve(),
            Path(args.archive).expanduser().resolve(),
            confirm=bool(args.confirm),
            force_local_modifications=bool(args.force_local_modifications),
            workplace_root=Path(args.workplace_root).expanduser().resolve() if args.workplace_root else None,
        )
    except CoreUpdateError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}, indent=2, sort_keys=True))
        return 1
    if args.workplace_root:
        core_root = Path(args.core_root).expanduser().resolve()
        command = [sys.executable, str(core_root / "bin" / "pf.py"), "doctor-workplace", "--root", str(Path(args.workplace_root).expanduser().resolve())]
        try:
            completed = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=90)
            doctor = {"status": "pass" if completed.returncode == 0 else "fail", "command": command, "output": completed.stdout + completed.stderr}
        except (OSError, subprocess.TimeoutExpired) as exc:
            doctor = {"status": "fail", "command": command, "output": str(exc)}
        payload["post_update_doctor"] = doctor
        last_apply_path = core_root / "runtime" / "core-update" / "last-apply.json"
        if last_apply_path.is_file():
            last_apply = json.loads(last_apply_path.read_text(encoding="utf-8"))
            last_apply["post_update_doctor"] = doctor
            last_apply_path.write_text(json.dumps(last_apply, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not args.workplace_root or payload["post_update_doctor"]["status"] == "pass" else 2


def command_core_update_repair(args: argparse.Namespace) -> int:
    from processforge_core.maintenance.update import repair_status

    payload = repair_status(Path(args.core_root).expanduser().resolve())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "manual_repair_required" else 2


def write_resource_proposal(workplace_root: Path, command: str, object_id: str, payload: dict[str, Any], slug: str | None = None) -> tuple[str, Path]:
    slug = slug or resource_management_slug(command, object_id)
    proposal = {
        "schema_version": 1,
        "proposal_id": slug,
        "command": command,
        "created_at": _core_common_clock.now_utc(),
        "mode": "proposal_first",
        "payload": payload,
        "privacy": {
            "public_project_files_must_not_contain_absolute_paths": True,
            "secret_values_stored": False,
        },
    }
    path = write_resource_management_artifact(workplace_root, "proposals", slug, dump_yaml(proposal))
    return slug, path


def emit_package_root_resolution_event(workplace_root: Path, command: str, package_id: str, package_root: PackageRootResolution) -> None:
    has_unavailable = any("path does not exist" in warning or "cannot" in warning for warning in package_root.warnings)
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command=command,
            event_type="package.root.unavailable" if has_unavailable else "package.root.resolved",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status="warn" if has_unavailable or package_root.fallback else "resolved",
            message="; ".join(package_root.warnings) if package_root.warnings else "package root resolved",
        ),
    )


def _legacy_command_knowledge_add_url(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    package_root = _project_package_catalog_reader.resolve_root(workplace_root, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-add-url", package_id, package_root)
    resource_id = safe_id(args.id or resource_id_from_url(args.url, "article"), "resource")
    resource = _resource_record_service.normalize(
        {
            "id": resource_id,
            "kind": args.kind,
            "title": args.title or resource_id.replace("-", " ").title(),
            "description": args.description or f"External {args.kind} resource registered from URL.",
            "source": {"type": "url", "url": args.url},
            "license": {"name": args.license or "unknown"},
            "load_policy": args.load_policy,
            "index_policy": args.index_policy,
        },
        package_id,
        workplace_root,
    )
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-add-url",
        resource_id,
        {
            "package_id": package_id,
            "package_root": package_root.root_id,
            "package_root_warnings": package_root.warnings,
            "resource": resource,
            "apply_writes": ["package.yaml", "indexes/resource-index.yaml"],
        },
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.resource.add.requested",
            target={"package_id": package_id, "resource_id": resource_id},
            status="dry_run" if args.dry_run else "requested",
            message="resource add proposal created",
        ),
    )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    _manifest_path, manifest, package_root = _project_package_catalog_reader.load_manifest(workplace_root, package_id, package_root_id, mode="write")
    package_existed = _manifest_path.is_file()
    result = upsert_resource(manifest["resources"], resource)
    manifest_path, index_path, package_root = write_package_manifest_and_index(workplace_root, package_id, manifest, package_root_id)
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.resource.added",
            target={"package_id": package_id, "resource_id": resource_id},
            status=result,
            message="resource manifest and index updated",
        ),
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="package.updated" if package_existed else "package.created",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status=result,
            message="package manifest updated through package root" if package_existed else "package manifest created through package root",
        ),
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-url",
            event_type="knowledge.package.updated",
            target={"package_id": package_id, "resource_id": resource_id, "package_root": package_root.root_id},
            status="updated",
            message="package resource index refreshed",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge URL Add Report",
        [
            f"- package: {package_id}",
            f"- package_root: {package_root.root_id}",
            f"- resource: {resource_id}",
            f"- manifest: {rel(manifest_path, workplace_root)}",
            f"- index: {rel(index_path, workplace_root)}",
            "- heavy content loaded: no",
        ],
    )
    print(f"{result.upper()}: {resource_id}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"MANIFEST: {rel(manifest_path, workplace_root)}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def _legacy_command_knowledge_add_resource(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    package_root = _project_package_catalog_reader.resolve_root(workplace_root, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-add-resource", package_id, package_root)
    data = load_yaml_document(Path(args.resource_file).expanduser().resolve())
    if not data or yaml_error(data):
        raise SystemExit(f"FAIL: resource file is missing or invalid: {args.resource_file}")
    resource = _resource_record_service.normalize(data, package_id, workplace_root, register_private_path=args.apply)
    resource_id = str(resource["id"])
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-add-resource",
        resource_id,
        {
            "package_id": package_id,
            "package_root": package_root.root_id,
            "package_root_warnings": package_root.warnings,
            "resource": resource,
            "private_input_path": data.get("path"),
            "suggested_registration": "register a knowledge_root/template_root/package_root when the path should be reused" if data.get("path") else None,
            "apply_writes": ["package.yaml", "indexes/resource-index.yaml"],
        },
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="knowledge.resource.add.requested",
            target={"package_id": package_id, "resource_id": resource_id},
            status="dry_run" if args.dry_run else "requested",
            message="resource add proposal created",
        ),
    )
    if data.get("path"):
        path_errors = resource.get("path_resolution", {}).get("errors") if isinstance(resource.get("path_resolution"), dict) else []
        _workplace_resource_events.append_workplace_resource_event(
            workplace_root,
            _workplace_resource_events.resource_management_event(
                scope="workplace",
                command="knowledge-add-resource",
                event_type="knowledge.resource.path.unresolved" if path_errors else "knowledge.resource.path.resolved",
                target={"package_id": package_id, "resource_id": resource_id},
                status="error" if path_errors else "resolved",
                message=", ".join(path_errors) if path_errors else "resource path resolved to public path_ref",
            ),
        )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    _manifest_path, manifest, package_root = _project_package_catalog_reader.load_manifest(workplace_root, package_id, package_root_id, mode="write")
    package_existed = _manifest_path.is_file()
    result = upsert_resource(manifest["resources"], resource)
    manifest_path, index_path, package_root = write_package_manifest_and_index(workplace_root, package_id, manifest, package_root_id)
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="package.updated" if package_existed else "package.created",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status=result,
            message="package manifest updated through package root" if package_existed else "package manifest created through package root",
        ),
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-add-resource",
            event_type="knowledge.resource.added",
            target={"package_id": package_id, "resource_id": resource_id, "package_root": package_root.root_id},
            status=result,
            message="resource manifest and index updated",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge Resource Add Report",
        [
            f"- package: {package_id}",
            f"- package_root: {package_root.root_id}",
            f"- resource: {resource_id}",
            f"- manifest: {rel(manifest_path, workplace_root)}",
            f"- index: {rel(index_path, workplace_root)}",
            f"- path_ref: {resource.get('path_ref')}",
        ],
    )
    print(f"{result.upper()}: {resource_id}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    return 0


def private_resource_registry_entry(resource_id: str, raw_path: str) -> dict[str, Any]:
    return {
        "id": resource_id,
        "label": resource_id.replace("-", " ").title(),
        "path": raw_path,
        "visibility": "private",
        "status": "available",
    }


def build_knowledge_resource_add_plan(
    args: argparse.Namespace,
    command_name: str,
    raw_resource: dict[str, Any],
) -> tuple[AuthoringPlan, dict[str, Any], str, Path, Path, PackageRootResolution]:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if not (workplace_root / "workplace.yaml").is_file():
        raise SystemExit(f"FAIL: workplace is not initialized: {workplace_root}")
    package_id = validate_resource_id(str(args.package), "knowledge package")
    package_root_id = getattr(args, "package_root", None)
    manifest_path, manifest, package_root = _project_package_catalog_reader.load_manifest(
        workplace_root,
        package_id,
        package_root_id,
        mode="read",
    )
    if manifest_path.is_file() and yaml_error(manifest):
        raise SystemExit(
            f"FAIL: package manifest YAML invalid; original preserved: {manifest_path}: {yaml_error(manifest)}"
        )
    resources = manifest.get("resources")
    if resources is None:
        resources = []
        manifest["resources"] = resources
    if not isinstance(resources, list):
        raise SystemExit("FAIL: knowledge package resources must be a list")
    resource = _resource_record_service.normalize(
        raw_resource,
        package_id,
        workplace_root,
        register_private_path=False,
    )
    resource_id = str(resource["id"])
    result = upsert_resource(resources, resource)
    manifest["package_root"] = package_root.root_id
    _update_schema_checks.require(
        manifest,
        "package-manifest.schema.json",
        f"knowledge package {package_id}",
    )
    index = build_resource_index(
        manifest,
        workplace_root,
        package_root.root_id,
    )
    _update_schema_checks.require(
        index,
        "knowledge-resource-index.schema.json",
        f"knowledge package {package_id} resource index",
    )
    index_path = _knowledge_resource_index_service.index_path(
        manifest_path,
        workplace_root,
        package_id,
    )
    entity_writes = [
        AuthoringWrite(
            manifest_path,
            ensure_trailing_newline(dump_yaml(manifest)).encode("utf-8"),
            role="entity",
            operation="replace" if manifest_path.is_file() else "create",
            schema_name="package-manifest.schema.json",
            allow_replace=manifest_path.is_file(),
        ),
        AuthoringWrite(
            index_path,
            ensure_trailing_newline(dump_yaml(index)).encode("utf-8"),
            role="entity",
            operation="replace" if index_path.is_file() else "create",
            schema_name="knowledge-resource-index.schema.json",
            allow_replace=index_path.is_file(),
        ),
    ]
    registry_writes: list[AuthoringWrite] = []
    raw_path = str(raw_resource.get("path") or "")
    path_ref = resource.get("path_ref") if isinstance(resource.get("path_ref"), dict) else {}
    if raw_path and path_ref.get("registry") == "private_resource_paths":
        private_registry = workplace_root / "registries" / "private-resource-paths.yaml"
        registry_bytes, _private_result, _private_data = planned_registry_upsert(
            private_registry,
            "private_resource_paths",
            private_resource_registry_entry(resource_id, raw_path),
            "private-resource-paths-registry.schema.json",
        )
        registry_writes.append(
            AuthoringWrite(
                private_registry,
                registry_bytes,
                role="registry",
                operation="replace" if private_registry.is_file() else "create",
                schema_name="private-resource-paths-registry.schema.json",
                allow_replace=private_registry.is_file(),
            )
        )
    transaction_id = f"{safe_id(command_name, 'knowledge')}-{resource_id}-{uuid.uuid4().hex[:12]}"
    plan = AuthoringPlan(
        transaction_id=transaction_id,
        command=command_name,
        runtime_root=workplace_root / "runtime",
        authoritative_writes=entity_writes,
        registry_writes=registry_writes,
        post_commit_effects=[],
        validation_callbacks=[],
    )

    plan.post_commit_effects.append(
        AuthoringEffect(
            "knowledge-audit-events",
            "runtime/resource-management/proposals/<transaction>.yaml, reports, and runtime/events/events.ndjson",
            kind="knowledge_audit",
            payload={
                "workplace_root": str(workplace_root),
                "command": command_name,
                "resource_id": resource_id,
                "proposal_payload": {
                    "transaction_id": transaction_id,
                    "package_id": package_id,
                    "package_root": package_root.root_id,
                    "package_root_warnings": package_root.warnings,
                    "resource": resource,
                    "apply_writes": [
                        rel(manifest_path, workplace_root),
                        rel(index_path, workplace_root),
                        *[
                            rel(write.destination, workplace_root)
                            for write in registry_writes
                        ],
                    ],
                },
                "events": [
                    {
                        "event_type": "knowledge.resource.added",
                        "status": result,
                        "message": "resource manifest and index updated",
                        "target": {
                            "package_id": package_id,
                            "resource_id": resource_id,
                            "package_root": package_root.root_id,
                            "transaction_id": transaction_id,
                        },
                    },
                    {
                        "event_type": "package.updated",
                        "status": result,
                        "message": "package manifest updated through package root",
                        "target": {
                            "package_id": package_id,
                            "resource_id": resource_id,
                            "package_root": package_root.root_id,
                            "transaction_id": transaction_id,
                        },
                    },
                    {
                        "event_type": "knowledge.package.updated",
                        "status": "updated",
                        "message": "package resource index refreshed",
                        "target": {
                            "package_id": package_id,
                            "resource_id": resource_id,
                            "package_root": package_root.root_id,
                            "transaction_id": transaction_id,
                        },
                    },
                ],
                "report_title": "Knowledge Resource Add Report",
                "report_lines": [
                    f"- transaction_id: {transaction_id}",
                    f"- package: {package_id}",
                    f"- package_root: {package_root.root_id}",
                    f"- resource: {resource_id}",
                    f"- manifest: {rel(manifest_path, workplace_root)}",
                    f"- index: {rel(index_path, workplace_root)}",
                    f"- path_ref: {resource.get('path_ref')}",
                ],
            },
        )
    )
    return plan, resource, result, manifest_path, index_path, package_root


def command_knowledge_add_url(args: argparse.Namespace) -> int:
    mode = _authoring_input_service.mode(args)
    resource_id = safe_id(
        args.id or resource_id_from_url(args.url, "article"),
        "resource",
    )
    raw_resource = {
        "id": resource_id,
        "kind": args.kind,
        "title": args.title or resource_id.replace("-", " ").title(),
        "description": args.description
        or f"External {args.kind} resource registered from URL.",
        "source": {"type": "url", "url": args.url},
        "license": {"name": args.license or "unknown"},
        "load_policy": args.load_policy,
        "index_policy": args.index_policy,
    }
    plan, resource, result, manifest_path, index_path, package_root = (
        build_knowledge_resource_add_plan(args, "knowledge-add-url", raw_resource)
    )
    workplace_root = Path(args.workplace).expanduser().resolve()
    if mode == "dry_run":
        preflight_authoring_plan(plan)
        for warning in package_root.warnings:
            print(warning)
        render_authoring_dry_run(plan, workplace_root)
        return 0
    execute_authoring_plan(plan)
    print(f"{result.upper()}: {resource['id']}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"MANIFEST: {rel(manifest_path, workplace_root)}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="knowledge-add-url"))
    return 0


def command_knowledge_add_resource(args: argparse.Namespace) -> int:
    mode = _authoring_input_service.mode(args)
    resource_file = Path(args.resource_file).expanduser().resolve()
    data = load_yaml_document(resource_file)
    if not data or yaml_error(data):
        raise SystemExit(f"FAIL: resource file is missing or invalid: {args.resource_file}")
    plan, resource, result, manifest_path, index_path, package_root = (
        build_knowledge_resource_add_plan(
            args,
            "knowledge-add-resource",
            data,
        )
    )
    workplace_root = Path(args.workplace).expanduser().resolve()
    if mode == "dry_run":
        preflight_authoring_plan(plan)
        for warning in package_root.warnings:
            print(warning)
        render_authoring_dry_run(plan, workplace_root)
        return 0
    execute_authoring_plan(plan)
    print(f"{result.upper()}: {resource['id']}")
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"MANIFEST: {rel(manifest_path, workplace_root)}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="knowledge-add-resource"))
    return 0


def command_knowledge_index_refresh(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    package_root_id = getattr(args, "package_root", None)
    manifest_path, manifest, package_root = _project_package_catalog_reader.load_manifest(workplace_root, package_id, package_root_id, mode="read" if args.dry_run else "write")
    emit_package_root_resolution_event(workplace_root, "knowledge-index-refresh", package_id, package_root)
    index_path = _knowledge_resource_index_service.index_path(manifest_path, workplace_root, package_id)
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "knowledge-index-refresh",
        package_id,
        {"package_id": package_id, "package_root": package_root.root_id, "package_root_warnings": package_root.warnings, "index_path": rel(index_path, workplace_root), "resource_count": len(manifest.get("resources", []))},
    )
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(ensure_trailing_newline(dump_yaml(build_resource_index(manifest, workplace_root, package_root.root_id))), encoding="utf-8")
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="knowledge-index-refresh",
            event_type="package.index.updated",
            target={"package_id": package_id, "package_root": package_root.root_id},
            status="updated",
            message="resource index refreshed",
        ),
    )
    report = write_resource_management_report(
        workplace_root,
        slug,
        "Knowledge Index Refresh Report",
        [f"- package: {package_id}", f"- package_root: {package_root.root_id}", f"- index: {rel(index_path, workplace_root)}", "- heavy content loaded: no"],
    )
    print(f"PACKAGE_ROOT: {package_root.root_id}")
    print(f"INDEX: {rel(index_path, workplace_root)}")
    print(f"REPORT: {rel(report, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="knowledge-index-refresh"))
    return 0


def command_knowledge_package_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = str(args.package)
    checks = _knowledge_package_validation_service.doctor(workplace_root, package_id, getattr(args, "package_root", None))
    return print_checks(checks)


def command_knowledge_package_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    package_id = validate_resource_id(str(args.id), "knowledge package")
    package_root = _project_package_catalog_reader.resolve_root(workplace_root, args.package_root, mode="write" if args.apply else "read")
    package_dir = contained_resource_path(
        package_root.resolved_path,
        package_root.resolved_path / package_id,
        "knowledge package",
    )
    manifest_path = contained_resource_path(
        package_root.resolved_path,
        package_dir / "package.yaml",
        "knowledge package",
    )
    slug, proposal_path = write_resource_proposal(workplace_root, "knowledge-package-create", package_id, {"package_id": package_id, "package_root": package_root.root_id, "target": rel(manifest_path, workplace_root)})
    emit_package_root_resolution_event(workplace_root, "knowledge-package-create", package_id, package_root)
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.authoring.started", target={"package_id": package_id, "package_root": package_root.root_id}, status="dry_run" if args.dry_run else "started", message="knowledge package authoring started"))
    if args.dry_run:
        for warning in package_root.warnings:
            print(warning)
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if manifest_path.exists() and not args.force:
        raise SystemExit(f"FAIL: knowledge package already exists: {rel(manifest_path, workplace_root)}")
    for dirname in ["resources", "indexes", "prompts", "summaries", "tests", "artifacts", "reviews", "handoffs"]:
        (package_dir / dirname).mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 1,
        "id": package_id,
        "name": args.title,
        "title": args.title,
        "kind": args.kind,
        "scope": "workplace",
        "version": "1.0.0",
        "status": "draft",
        "description": args.description or f"Workplace knowledge package {args.title}.",
        "visibility": "workplace",
        "load_policy": "on_demand",
        "resources": [],
        "indexes": {"resource_index": "indexes/resource-index.yaml"},
        "tags": [args.kind, "knowledge"],
    }
    write_authoring_text(manifest_path, dump_yaml(package))
    write_authoring_text(package_dir / "README.md", f"# {args.title}\n\nKnowledge package `{package_id}`.")
    write_authoring_text(package_dir / "indexes" / "resource-index.yaml", dump_yaml({"schema_version": 1, "package": package_id, "resources": []}))
    write_authoring_text(package_dir / "artifacts" / "knowledge-package-authoring-report.md", f"# Knowledge Package Authoring Report\n\n- package: {package_id}\n- package_root: {package_root.root_id}")
    write_authoring_text(package_dir / "reviews" / "knowledge-package-authoring-review.md", "# Knowledge Package Authoring Review\n\nResult: pass_with_conditions")
    write_authoring_text(package_dir / "handoffs" / "knowledge-package-ready-handoff.md", f"# Handoff: knowledge-package-create -> knowledge consumers\n\nPackage `{package_id}` is ready for resource additions.")
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.created", target={"package_id": package_id, "package_root": package_root.root_id}, status="created", message="knowledge package created"))
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.resource_index.created", target={"package_id": package_id}, status="created", message="resource index created"))
    doctor_status, doctor_output = run_command_capture(command_knowledge_package_doctor, argparse.Namespace(workplace=str(workplace_root), package=package_id, package_root=package_root.root_id))
    print(doctor_output, end="")
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.doctor.passed" if doctor_status == 0 else "knowledge_package.doctor.failed", target={"package_id": package_id}, status="passed" if doctor_status == 0 else "failed", message="knowledge package doctor completed"))
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="knowledge-package-create", event_type="knowledge_package.authoring.completed", target={"package_id": package_id}, status="completed", message="knowledge package authoring completed"))
    print(f"PACKAGE: {rel(manifest_path, workplace_root)}")
    return doctor_status




def platform_contract_path(workplace_root: Path, platform: str) -> Path | None:
    platform_id, contract_id = _platform_contract_reader.normalize_id_pair(platform)
    for candidate_id in [contract_id, platform_id]:
        entry = _platform_contract_reader.registry_entry(workplace_root / "workplace.yaml", candidate_id)
        if entry and entry.get("path"):
            path = workplace_root / str(entry["path"])
            if path.is_file():
                return path
    _root_id, root_path = resolve_platform_root(workplace_root, None, mode="read")
    for candidate in [root_path / contract_id / "platform-contract.yaml", root_path / platform_id / "platform-contract.yaml", workplace_root / "platforms" / platform_id / "platform.yaml"]:
        if candidate.is_file():
            return candidate
    return None




def command_platform_contract_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    platform = str(args.platform)
    checks: list[Check] = []
    contract_path = platform_contract_path(workplace_root, platform)
    checks.append(
        check("PASS", "platform contract found")
        if contract_path
        else check_with_hint(
            "FAIL",
            "platform contract found",
            "The requested platform is not registered or its platform contract path is missing.",
            f"python bin/pf.py platform-create --workplace <workplace-root> --id {platform} --title \"{platform}\" --apply",
        )
    )
    if contract_path:
        text = contract_path.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "platform contract has no local absolute paths"))
        data = _update_document_reader.doctor_yaml(
            contract_path,
            "platform-contract.schema.json",
            f"platform {platform} contract",
            checks,
        )
        if data is None:
            return print_checks(checks)
        checks.append(check("PASS" if data.get("id") else "FAIL", "platform contract id present"))
        contract_id = _platform_contract_reader.contract_id(str(data.get("id") or platform))
        for entry in policy_entries(_context_contract_inputs.documents.policy("platform-id-policy.yaml", distribution_root=ROOT), "discouraged_platform_ids"):
            if policy_id_matches(contract_id, entry):
                checks.append(
                    check_with_hint(
                        str(entry.get("user_created_behavior", "WARN")).upper(),
                        str(entry.get("message", f"platform id discouraged: {contract_id}")),
                        str(entry.get("why", "The platform id matched a data-driven platform id policy.")),
                        str(entry.get("fix", "update the platform id or policy manifest")),
                    )
                )
        hints = data.get("project_type_hints")
        if not isinstance(hints, list):
            applies_to = data.get("applies_to") if isinstance(data.get("applies_to"), dict) else {}
            hints = applies_to.get("project_type_hints") if isinstance(applies_to.get("project_type_hints"), list) else []
        checks.append(check("PASS" if isinstance(hints, list) and hints else "WARN", "project_type_hints configured"))
        requires = data.get("requires") if isinstance(data.get("requires"), dict) else {}
        checks.append(check("PASS" if requires.get("capabilities") else "WARN", "required capabilities listed"))
        extends_refs = _platform_contract_policy.extends(data)
        required_platform_refs = _platform_contract_policy.required_platforms(data)
        checks.append(check("PASS", "extends entries are valid") if all(ref.get("id") for ref in extends_refs) else check("FAIL", "extends entries are valid"))
        checks.append(check("PASS", "requires.platforms entries are valid") if all(ref.get("id") for ref in required_platform_refs) else check("FAIL", "requires.platforms entries are valid"))
        for ref in extends_refs:
            if ref.get("required") is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"extends parent is required: {ref['id']}",
                        "Platform inheritance cannot be optional in the pre-release contract model.",
                        "set required: true or move the platform reference to requires.platforms if it is only a dependency",
                    )
                )
        required_platform_by_id = {str(ref["id"]): bool(ref.get("required", True)) for ref in required_platform_refs}
        for ref in extends_refs:
            if required_platform_by_id.get(str(ref["id"])) is False:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"child platform cannot weaken required parent dependency: {ref['id']}",
                        "An inherited parent is required by definition; requires.platforms cannot mark the same parent optional.",
                        "set requires.platforms[].required: true for the parent platform",
                    )
                )
        platform_resolution = _platform_contract_resolver.resolve(workplace_root / "workplace.yaml", [data.get("id") or platform])
        for missing in platform_resolution["missing_required_contracts"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required platform available: {missing}",
                    "The platform contract extends or requires a platform that is not registered in the workplace.",
                    f"python bin/pf.py platform-create --workplace <workplace-root> --id {missing} --title \"{missing}\" --apply",
                )
            )
        for cycle in platform_resolution["circular_platforms"]:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"circular platform inheritance detected: {cycle}",
                    "Platform inheritance must resolve to an acyclic parent-first stack.",
                    "remove one extends edge from the cycle and rerun platform-contract-doctor",
                )
            )
        checks.append(check("PASS" if platform_resolution["platform_stack"] else "FAIL", "resolved platform stack valid"))
        checks.append(check("PASS", "resolved platform stack computed without mutating workplace state"))
        inherited_required, inherited_recommended = _project_platform_selection_service.resource_findings(workplace_root / "workplace.yaml", platform_resolution)
        for item in inherited_required:
            checks.append(
                check_with_hint(
                    "FAIL",
                    f"required {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack marks this resource as required.",
                    "register the missing resource in the workplace registry or package roots before using this platform",
                )
            )
        for item in inherited_recommended:
            checks.append(
                check_with_hint(
                    "WARN",
                    f"optional {item['kind']} available through resolved platform stack: {item['id']}",
                    "A platform in the resolved stack recommends this resource, but onboarding can continue.",
                    "register the resource if this platform should provide the optional capability",
                )
            )
        for package_id in list_value(requires.get("knowledge_packages")):
            manifest = _project_package_catalog_reader.index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"required knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "FAIL",
                    f"required knowledge package available: {package_id}",
                    "This platform contract marks the package as required.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                    "mark it as required: false or move it to includes.knowledge_packages if optional",
                )
            )
        for package_id in _platform_contract_policy.includes(data, "knowledge_packages"):
            manifest = _project_package_catalog_reader.index(workplace_root, None, workplace_root / "workplace.yaml").get(package_id)
            checks.append(
                check("PASS", f"optional knowledge package available: {package_id}")
                if manifest
                else check_with_hint(
                    "WARN",
                    f"optional knowledge package available: {package_id}",
                    "This platform contract recommends the package, but onboarding can continue without it.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                )
            )
        for template_id in list_value(requires.get("templates")):
            checks.append(
                check("PASS", f"required template available: {template_id}")
                if _template_catalog_service.manifest(workplace_root, template_id)
                else check_with_hint(
                    "FAIL",
                    f"required template available: {template_id}",
                    "This platform contract marks the template as required.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                    "move it to includes.templates if optional",
                )
            )
        for template_id in _platform_contract_policy.includes(data, "templates"):
            checks.append(
                check("PASS", f"optional template available: {template_id}")
                if _template_catalog_service.manifest(workplace_root, template_id)
                else check_with_hint(
                    "WARN",
                    f"optional template available: {template_id}",
                    "This platform contract recommends the template, but onboarding can continue without it.",
                    f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
                )
            )
        for forbidden in ["package.yaml", "template.yaml"]:
            copied = [path for path in contract_path.parent.rglob(forbidden) if path != contract_path]
            checks.append(check("PASS" if not copied else "FAIL", f"no copied {forbidden} inside platform contract"))
    return print_checks(checks)


def command_docs_import_plan(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    source = safe_id(args.source, "source")
    topics = [safe_id(item.strip(), "topic") for item in str(args.topics).split(",") if item.strip()]
    plan_id = safe_id(args.id or f"{source}-{'-'.join(topics)}", "documentation-import")
    resources = [
        {
            "id": f"{source}-{topic}-docs",
            "kind": "documentation",
            "title": f"{source.upper()} {topic.upper()} documentation mirror",
            "path_ref": {"registry": "external_resources", "id": f"{source}-{topic}-docs"},
            "load_policy": "on_demand",
            "index_policy": "full_text",
            "source": {"type": "documentation_source", "id": source, "topic": topic},
            "license": {"name": args.license or "source-specific"},
            "update_policy": {"mode": "manual_plan_first"},
        }
        for topic in topics
    ]
    plan = {
        "schema_version": 1,
        "id": plan_id,
        "source": source,
        "topics": topics,
        "created_at": _core_common_clock.now_utc(),
        "mode": "plan_only",
        "download": {"enabled": False, "reason": "MVP does not crawl or download large documentation sets"},
        "resources": resources,
        "index_policy": "write_resource_index_without_loading_full_content",
    }
    target = resource_management_root(workplace_root) / "documentation-import-plans" / f"{plan_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(ensure_trailing_newline(dump_yaml(plan)), encoding="utf-8")
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="docs-import-plan",
            event_type="knowledge.resource.add.requested",
            target={"package_id": args.package or "documentation", "resource_id": plan_id},
            status="planned",
            message="documentation import plan created without downloading content",
        ),
    )
    print(f"PLAN: {rel(target, workplace_root)}")
    return 0


def command_template_add(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = safe_id(args.id, "template")
    source = Path(args.source).expanduser().resolve()
    target_root = path_resolution_to_path(workplace_path_resolution(workplace_root, f"${{PF_TEMPLATES}}/{args.type}/{template_id}"))
    slug, proposal_path = write_resource_proposal(
        workplace_root,
        "template-add",
        template_id,
        {"template_id": template_id, "source": str(source), "target": rel(target_root, workplace_root)},
    )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="template-add",
            event_type="template.add.requested",
            target={"template_id": template_id},
            status="dry_run" if args.dry_run else "requested",
            message="template add proposal created",
        ),
    )
    if args.dry_run or args.apply is not True:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if not source.is_dir():
        raise SystemExit(f"FAIL: template source folder not found: {source}")
    target_root.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        if item.is_file():
            relative = item.relative_to(source)
            destination = target_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
    readme = target_root / "README.md"
    if not readme.is_file():
        readme.write_text(
            ensure_trailing_newline(
                f"# {template_id}\n\nUse this {args.type} template when the current package or platform contract selects it.\n\n## Placeholders\n\nDocument placeholders before production use.\n\n## Verification\n\nReview generated files before applying them to a project."
            ),
            encoding="utf-8",
        )
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="template-add",
            event_type="template.added",
            target={"template_id": template_id},
            status="added",
            message="template payload copied",
        ),
    )
    print(f"TEMPLATE: {rel(target_root, workplace_root)}")
    return 0




def resolve_platform_root(workplace_root: Path, platform_root_id: str | None = None, *, mode: str = "read") -> tuple[str, Path]:
    registry_path = workplace_root / "registries" / "platform-contract-roots.yaml"
    data = load_yaml_document(registry_path)
    roots = data.get("platform_contract_roots") if isinstance(data, dict) else None
    entries = [entry for entry in roots if isinstance(entry, dict)] if isinstance(roots, list) else []
    if not entries:
        entries = [{"id": "global", "label": "Global platform contracts", "path": "${PF_PLATFORM_CONTRACTS}", "scope": "workplace", "status": "available"}]
        if mode == "write":
            _workplace_registry_writer.upsert(registry_path, "platform_contract_roots", entries[0])
    selected = None
    if platform_root_id:
        for entry in entries:
            if str(entry.get("id")) == platform_root_id:
                selected = entry
                break
        if selected is None:
            raise SystemExit(f"FAIL: platform root '{platform_root_id}' not found in registries/platform-contract-roots.yaml")
    else:
        available = [entry for entry in entries if str(entry.get("status", "available")) == "available"]
        selected = available[0] if available else entries[0]
    root_id = str(selected.get("id", "global"))
    root_path = path_resolution_to_path(workplace_path_resolution(workplace_root, str(selected.get("path") or "${PF_PLATFORM_CONTRACTS}")))
    if mode == "write":
        root_path.mkdir(parents=True, exist_ok=True)
    return root_id, root_path


def write_authoring_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ensure_trailing_newline(content), encoding="utf-8")


def command_template_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = str(args.id)
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*", template_id):
        raise SystemExit("FAIL: template id must be lowercase and may use dots or dashes")
    root_id, template_root = _template_catalog_service.resolve_root(workplace_root, getattr(args, "template_root", None), mode="write" if args.apply else "read")
    target = template_root / template_id
    slug, proposal_path = write_resource_proposal(workplace_root, "template-create", template_id, {"template_id": template_id, "template_root": root_id, "target": rel(target, workplace_root)})
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="template-create", event_type="template.authoring.started", target={"template_id": template_id}, status="dry_run" if args.dry_run else "started", message="template authoring started"))
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    if target.exists() and not args.force:
        raise SystemExit(f"FAIL: template already exists: {rel(target, workplace_root)}")
    for dirname in ["files", "prompts", "examples", "tests", "artifacts", "reviews", "handoffs"]:
        (target / dirname).mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "type": "reusable_template",
        "id": template_id,
        "title": args.title,
        "kind": args.kind,
        "version": "1.0.0",
        "description": args.description or f"Reusable template {args.title}.",
        "inputs": [{"id": "project", "required": True}, {"id": "scope", "required": False}],
        "outputs": [{"path": f"{safe_id(template_id, 'template')}.md"}],
        "files": [{"source": f"files/{safe_id(template_id, 'template')}.md", "target": "{{ output_path }}"}],
        "prompts": [{"path": "prompts/authoring-notes.md"}],
        "tags": [args.kind, "processforge-template"],
    }
    write_authoring_text(target / "template.yaml", dump_yaml(manifest))
    write_authoring_text(target / "README.md", f"# {args.title}\n\nReusable template `{template_id}`.")
    write_authoring_text(target / "files" / f"{safe_id(template_id, 'template')}.md", f"# {{{{ project }}}}\n\nTemplate scope: {{{{ scope }}}}")
    write_authoring_text(target / "prompts" / "authoring-notes.md", f"# Authoring Notes\n\nUse template `{template_id}` through ProcessForge template selection.")
    write_authoring_text(target / "artifacts" / "template-authoring-report.md", f"# Template Authoring Report\n\n- template: {template_id}\n- template_root: {root_id}")
    write_authoring_text(target / "reviews" / "template-authoring-review.md", "# Template Authoring Review\n\nResult: pass_with_conditions")
    write_authoring_text(target / "handoffs" / "template-ready-handoff.md", f"# Handoff: template-create -> template consumers\n\nTemplate `{template_id}` is ready for review.")
    _workplace_registry_writer.upsert(workplace_root / "registries" / "templates.yaml", "templates", {"id": template_id, "title": args.title, "path": rel(target / "template.yaml", workplace_root), "template_root": root_id, "kind": args.kind, "status": "available"})
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="template-create", event_type="template.created", target={"template_id": template_id}, status="created", message="template structure created"))
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="template-create", event_type="template.registered", target={"template_id": template_id}, status="registered", message="template registry updated"))
    doctor_status, doctor_output = run_command_capture(command_template_doctor, argparse.Namespace(workplace=str(workplace_root), template=template_id))
    print(doctor_output, end="")
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="template-create", event_type="template.doctor.passed" if doctor_status == 0 else "template.doctor.failed", target={"template_id": template_id}, status="passed" if doctor_status == 0 else "failed", message="template doctor completed"))
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="template-create", event_type="template.authoring.completed", target={"template_id": template_id}, status="completed", message="template authoring completed"))
    print(f"TEMPLATE: {rel(target, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="template-create"))
    return doctor_status




def command_template_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    template_id = str(args.template)
    checks: list[Check] = []
    manifest_path = _template_catalog_service.manifest(workplace_root, template_id)
    checks.append(
        check("PASS", "template manifest found")
        if manifest_path
        else check_with_hint(
            "FAIL",
            "template manifest found",
            "The template id cannot be resolved through registries/templates.yaml or the default template root.",
            f"python bin/pf.py template-create --workplace <workplace-root> --id {template_id} --title \"{template_id}\" --apply",
        )
    )
    if manifest_path:
        text = manifest_path.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", "template manifest has no local absolute paths"))
        data = _update_document_reader.doctor_yaml(
            manifest_path,
            "reusable-template.schema.json",
            f"template {template_id} manifest",
            checks,
        )
        if data is None:
            return print_checks(checks)
        if data.get("schema_version") == 1:
            checks.append(check("WARN", "legacy reusable template schema_version 1 requires explicit migration"))
        checks.append(check("PASS" if data.get("id") == template_id else "FAIL", "template id matches requested id"))
        root = manifest_path.parent
        for dirname in ["files", "prompts", "examples", "artifacts", "reviews", "handoffs"]:
            checks.append(check("PASS" if (root / dirname).exists() else "WARN", f"{dirname}/ exists"))
        for item in data.get("files", []) if isinstance(data.get("files"), list) else []:
            source = item.get("source") if isinstance(item, dict) else None
            if source:
                checks.append(
                    check("PASS", f"referenced file exists: {source}")
                    if (root / str(source)).is_file()
                    else check_with_hint(
                        "FAIL",
                        f"referenced file exists: {source}",
                        "The template manifest references a payload file that is not present.",
                        f"restore {source} under the template root or remove the file entry from template.yaml",
                    )
                )
        for item in data.get("prompts", []) if isinstance(data.get("prompts"), list) else []:
            prompt_path = item.get("path") if isinstance(item, dict) else None
            if prompt_path:
                checks.append(
                    check("PASS", f"referenced prompt exists: {prompt_path}")
                    if (root / str(prompt_path)).is_file()
                    else check_with_hint(
                        "FAIL",
                        f"referenced prompt exists: {prompt_path}",
                        "The template manifest references a prompt file that is not present.",
                        f"restore {prompt_path} under the template root or remove the prompt entry from template.yaml",
                    )
                )
    return print_checks(checks)




def command_tool_register(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if contains_secret_value(args.command):
        raise SystemExit("FAIL: command appears to contain a secret value")
    tool_id = safe_id(args.id, "tool")
    entry = {
        "id": tool_id,
        "name": args.name or tool_id,
        "capability": args.capability,
        "command": args.command,
        "scope": "workplace",
        "healthcheck": {"command": args.healthcheck or f"{args.command} --version"},
        "status": args.status,
    }
    slug, proposal_path = write_resource_proposal(workplace_root, "tool-register", tool_id, {"tool": entry})
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    result = _workplace_registry_writer.upsert(workplace_root / "registries" / "tools.yaml", "tools", entry)
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="tool-register",
            event_type="tool.registered",
            target={"tool_id": tool_id},
            status=result,
            message="tool registry updated",
        ),
    )
    report = write_resource_management_report(workplace_root, slug, "Tool Register Report", [f"- tool: {tool_id}", f"- status: {result}"])
    print(f"{result.upper()}: {tool_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="tool-register"))
    return 0


def command_mcp_register(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if contains_secret_value(args.command):
        raise SystemExit("FAIL: command appears to contain a secret value")
    mcp_id = safe_id(args.id, "mcp")
    entry = {
        "id": mcp_id,
        "name": args.name or mcp_id,
        "capability": args.capability,
        "transport": args.transport,
        "command": args.command,
        "auth_ref": args.auth_ref,
        "status": args.status,
    }
    slug, proposal_path = write_resource_proposal(workplace_root, "mcp-register", mcp_id, {"mcp": entry})
    if args.dry_run:
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        return 0
    result = _workplace_registry_writer.upsert(workplace_root / "registries" / "mcp.yaml", "mcp_servers", entry)
    _workplace_resource_events.append_workplace_resource_event(
        workplace_root,
        _workplace_resource_events.resource_management_event(
            scope="workplace",
            command="mcp-register",
            event_type="mcp.registered",
            target={"mcp_id": mcp_id},
            status=result,
            message="MCP registry updated",
        ),
    )
    report = write_resource_management_report(workplace_root, slug, "MCP Register Report", [f"- mcp: {mcp_id}", f"- status: {result}"])
    print(f"{result.upper()}: {mcp_id}")
    print(f"REPORT: {rel(report, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="mcp-register"))
    return 0


def command_specialization_list(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    index = _specialization_catalog_reader.manifest_index(workplace_root / "workplace.yaml", project_root)
    rows = [
        {
            "id": item.get("id"),
            "name": item.get("name") or item.get("title") or item.get("id"),
            "status": item.get("status", "active"),
            "source": item.get("__source", "workplace"),
            "path": rel(item.get("__manifest_path"), project_root or workplace_root) if isinstance(item.get("__manifest_path"), Path) else "",
        }
        for item in index.values()
    ]
    if getattr(args, "json", False):
        print(json.dumps({"specializations": rows}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    for row in sorted(rows, key=lambda item: str(item.get("id"))):
        print(f"{row['id']}\t{row['status']}\t{row['source']}\t{row['path']}")
    return 0


def command_specialization_show(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve() if getattr(args, "project_root", None) else None
    data = load_specialization(workplace_root / "workplace.yaml", args.id, project_root)
    if not data:
        raise SystemExit(f"FAIL: specialization not found: {_specialization_catalog_reader.resource_id(args.id)}")
    cleaned = {key: value for key, value in data.items() if not str(key).startswith("__")}
    if getattr(args, "json", False):
        print(json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(dump_yaml(cleaned), end="")
    return 0




def specialization_doctor_checks(workplace_root: Path, specialization_id: str) -> list[Check]:
    normalized_id = _specialization_catalog_reader.resource_id(specialization_id)
    checks: list[Check] = []
    path = _specialization_catalog_reader.manifest_path(workplace_root, normalized_id)
    checks.append(
        check("PASS", "specialization manifest found")
        if path
        else check_with_hint(
            "FAIL",
            "specialization manifest found",
            "The specialization id cannot be resolved through registries/specializations.yaml or the default specialization root.",
            f"python bin/pf.py specialization-create --workplace <workplace-root> --id {normalized_id} --apply",
        )
    )
    if not path:
        return checks
    data = _update_document_reader.doctor_yaml(
        path,
        "specialization.schema.json",
        f"specialization {normalized_id} manifest",
        checks,
    )
    if data is None:
        return checks
    checks.append(check("PASS" if isinstance(data, dict) and data.get("kind") == "processforge.specialization" else "FAIL", "specialization kind valid"))
    checks.append(check("PASS" if data.get("id") == normalized_id else "FAIL", "specialization id matches requested id"))
    checks.append(check("PASS" if is_public_path_safe(path.read_text(encoding="utf-8", errors="replace")) else "FAIL", "specialization has no private absolute paths"))
    for bucket in _core_resources_buckets.RESOURCE_BUCKET_KEYS:
        for key in _core_resources_buckets.RESOURCE_GROUP_KEYS:
            values = _core_resources_buckets.resource_bucket(data.get("resources") if isinstance(data.get("resources"), dict) else {}, bucket, key)
            checks.append(check("PASS", f"resources.{bucket}.{key} valid list") if all(isinstance(item, str) for item in values) else check("FAIL", f"resources.{bucket}.{key} valid list"))
    bindings = data.get("platform_bindings") if isinstance(data.get("platform_bindings"), list) else []
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            checks.append(check("FAIL", f"platform_bindings[{index}] is object"))
            continue
        checks.append(check("PASS" if list_value(binding.get("platforms")) or list_value(binding.get("platform_stack_includes")) else "WARN", f"platform_bindings[{index}] has platform selector"))
        resources = binding.get("resources") if isinstance(binding.get("resources"), dict) else {}
        for bucket in _core_resources_buckets.RESOURCE_BUCKET_KEYS:
            for key in _core_resources_buckets.RESOURCE_GROUP_KEYS:
                values = _core_resources_buckets.resource_bucket(resources, bucket, key)
                checks.append(check("PASS", f"platform_bindings[{index}].resources.{bucket}.{key} valid list") if all(isinstance(item, str) for item in values) else check("FAIL", f"platform_bindings[{index}].resources.{bucket}.{key} valid list"))
    return checks


def command_specialization_doctor(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    return print_checks(specialization_doctor_checks(workplace_root, args.id))


def command_specialization_create(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    requested_id = validate_resource_id(str(args.id), "specialization")
    specialization_id = validate_resource_id(
        _specialization_catalog_reader.resource_id(requested_id),
        "specialization",
    )
    specialization_root = workplace_root / "specializations"
    target = contained_resource_path(
        specialization_root,
        specialization_root / f"{specialization_id}.yaml",
        "specialization",
    )
    slug, proposal_path = write_resource_proposal(workplace_root, "specialization-create", specialization_id, {"specialization": specialization_id, "target": rel(target, workplace_root)})
    if not getattr(args, "apply", False):
        print(f"PROPOSAL: {rel(proposal_path, workplace_root)}")
        print(f"TARGET: {rel(target, workplace_root)}")
        return 0
    if target.exists() and not getattr(args, "force", False):
        raise SystemExit(f"FAIL: specialization already exists: {rel(target, workplace_root)}")
    document = {
        "schema_version": 1,
        "kind": "processforge.specialization",
        "id": specialization_id,
        "name": args.title or specialization_id,
        "status": "active",
        "description": args.description or "A workplace-defined specialist resource profile that selects resources data-driven.",
        "scope": {"owner": "workspace", "visibility": "local"},
        "applies_to": {"project_types": [], "roles": [], "tags": []},
        "resources": _core_resources_buckets.default_resource_buckets(),
        "provides_capabilities": [],
        "platform_bindings": [],
        "tool_policy": {"allowed_tools": [], "disallowed_tools": []},
        "metadata": {"tags": []},
    }
    write_authoring_text(target, dump_yaml(document))
    _workplace_registry_writer.upsert(_specialization_catalog_reader.registry_path(workplace_root), "specializations", {"id": specialization_id, "path": rel(target, workplace_root), "status": "available", "scope": "workplace"})
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="specialization-create", event_type="specialization.created", target={"specialization_id": specialization_id}, status="created", message="specialization created"))
    print(f"SPECIALIZATION: {rel(target, workplace_root)}")
    return print_checks(specialization_doctor_checks(workplace_root, specialization_id))


def command_specialization_bind_platform(args: argparse.Namespace) -> int:
    workplace_root = Path(args.workplace).expanduser().resolve()
    specialization_id = _specialization_catalog_reader.resource_id(str(args.specialization))
    path = _specialization_catalog_reader.manifest_path(workplace_root, specialization_id)
    if not path:
        raise SystemExit(f"FAIL: specialization not found: {specialization_id}")
    data = load_yaml_document(path)
    if not isinstance(data, dict) or yaml_error(data):
        raise SystemExit(f"FAIL: specialization YAML invalid: {rel(path, workplace_root)}")
    binding = {
        "platforms": [_platform_contract_reader.contract_id(str(args.platform))],
        "platform_stack_includes": [_platform_contract_reader.contract_id(item) for item in getattr(args, "platform_stack_includes", [])],
        "applies_to_project_types": [str(item) for item in getattr(args, "project_type", [])],
        "tags": [],
        "resources": _core_resources_buckets.default_resource_buckets(),
        "provides_capabilities": [str(item) for item in getattr(args, "provides_capability", [])],
    }
    legacy_process_filters = [str(item) for item in getattr(args, "process", [])]
    if legacy_process_filters:
        binding["applies_to_processes"] = legacy_process_filters
    for value in getattr(args, "requires_knowledge", []):
        binding["resources"]["requires"]["knowledge_packages"].append(str(value))
    for value in getattr(args, "requires_tool", []):
        binding["resources"]["requires"]["tools"].append(str(value))
    for value in getattr(args, "requires_mcp", []):
        binding["resources"]["requires"]["mcp"].append(str(value))
    for value in getattr(args, "requires_template", []):
        binding["resources"]["requires"]["templates"].append(str(value))
    if not getattr(args, "apply", False):
        print(dump_yaml(binding), end="")
        return 0
    bindings = data.setdefault("platform_bindings", [])
    if not isinstance(bindings, list):
        bindings = []
        data["platform_bindings"] = bindings
    bindings.append(binding)
    write_authoring_text(path, dump_yaml(data))
    _workplace_resource_events.append_workplace_resource_event(workplace_root, _workplace_resource_events.resource_management_event(scope="workplace", command="specialization-bind-platform", event_type="specialization.platform_bound", target={"specialization_id": specialization_id, "platform": _platform_contract_reader.contract_id(str(args.platform))}, status="updated", message="specialization platform binding added"))
    print(f"UPDATED: {rel(path, workplace_root)}")
    return 0


def command_project_override_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    entries = _project_override_reader.project_override_entries(project_root)
    if getattr(args, "json", False):
        print(json.dumps({"project_overrides": entries}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    for entry in entries:
        print(f"{entry.get('kind')}\t{entry.get('target')}\t{entry.get('mode')}\t{entry.get('reason', '')}")
    return 0


def command_project_override_add(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    flow_root = locate_flow_root(project_root)
    kind = _core_project_overrides.PROJECT_OVERRIDE_KINDS.get(str(args.kind), str(args.kind))
    mode = str(args.mode)
    if kind not in {"templates", "knowledge_packages", "tools", "mcp", "specializations"}:
        raise SystemExit(f"FAIL: unsupported project override kind: {args.kind}")
    if mode not in PROJECT_OVERRIDE_MODES:
        raise SystemExit(f"FAIL: unsupported project override mode: {mode}")
    path = _project_override_reader.project_overrides_path(project_root)
    data = _project_override_reader.load_project_overrides(project_root)
    overrides = data.setdefault("overrides", {})
    entries = overrides.setdefault(kind, [])
    if not isinstance(entries, list):
        entries = []
        overrides[kind] = entries
    entry = {"target": str(args.target), "mode": mode, "reason": str(args.reason)}
    if getattr(args, "path", None):
        entry["path"] = str(args.path)
    if getattr(args, "project_package", None):
        entry["project_package"] = str(args.project_package)
    params: dict[str, Any] = {}
    for value in getattr(args, "param", []) or []:
        if "=" not in value:
            raise SystemExit("FAIL: --param must use key=value")
        key, param_value = value.split("=", 1)
        params[key] = param_value
    if params:
        entry["params"] = params
    existing = next((item for item in entries if isinstance(item, dict) and str(item.get("target")) == str(args.target)), None)
    if existing:
        existing.update(entry)
    else:
        entries.append(entry)
    if not getattr(args, "apply", False):
        print(dump_yaml(data), end="")
        return 0
    flow_root.mkdir(parents=True, exist_ok=True)
    write_authoring_text(path, dump_yaml(data))
    print(f"WROTE: {rel(path, project_root)}")
    return 0


def command_project_override_doctor(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).expanduser().resolve()
    path = _project_override_reader.project_overrides_path(project_root)
    checks: list[Check] = []
    checks.append(check("PASS", "project overrides file optional") if not path.is_file() else check("PASS", "project overrides file found"))
    data = _project_override_reader.load_project_overrides(project_root)
    checks.append(check("PASS" if data.get("kind") in {None, "processforge.project_overrides"} else "FAIL", "project overrides kind valid"))
    for entry in _project_override_reader.project_override_entries(project_root):
        mode = str(entry.get("mode") or "")
        checks.append(check("PASS" if mode in PROJECT_OVERRIDE_MODES else "FAIL", f"{entry.get('kind')} {entry.get('target')} mode valid"))
        override_path = _project_override_reader.project_override_path(project_root, entry)
        if override_path:
            checks.append(check("PASS" if path_is_relative_to(override_path, locate_flow_root(project_root)) else "FAIL", f"{entry.get('target')} override path is project-local"))
            checks.append(check("PASS" if override_path.is_file() else "WARN", f"{entry.get('target')} override file exists"))
    return print_checks(checks)




def platform_authoring_values(args: argparse.Namespace) -> dict[str, Any]:
    platform_id = validate_resource_id(
        str(args.id).removeprefix("platform."),
        "platform",
    )
    contract_id = _platform_contract_reader.contract_id(platform_id)
    required_packages = [
        item for item in getattr(args, "requires_package", []) if item
    ]
    recommended_packages = [
        item for item in getattr(args, "recommends_package", []) if item
    ]
    optional_packages = [
        item for item in getattr(args, "optional_package", []) if item
    ]
    required_templates = [
        item for item in getattr(args, "requires_template", []) if item
    ]
    recommended_templates = [
        item for item in getattr(args, "recommends_template", []) if item
    ]
    optional_templates = [
        item for item in getattr(args, "optional_template", []) if item
    ]
    required_tools = [item for item in getattr(args, "requires_tool", []) if item]
    recommended_tools = [
        item for item in getattr(args, "recommends_tool", []) if item
    ]
    optional_tools = [item for item in getattr(args, "optional_tool", []) if item]
    required_mcp = [item for item in getattr(args, "requires_mcp", []) if item]
    recommended_mcp = [
        item for item in getattr(args, "recommends_mcp", []) if item
    ]
    optional_mcp = [item for item in getattr(args, "optional_mcp", []) if item]
    project_types = [item for item in getattr(args, "project_type", []) if item] or [
        platform_id
    ]
    return {
        "platform_id": platform_id,
        "contract_id": contract_id,
        "title": str(getattr(args, "title", "") or title_from_id(platform_id)),
        "version": str(getattr(args, "version", "") or "1.0.0"),
        "required_packages": required_packages,
        "recommended_packages": recommended_packages,
        "optional_packages": optional_packages,
        "required_templates": required_templates,
        "recommended_templates": recommended_templates,
        "optional_templates": optional_templates,
        "required_tools": required_tools,
        "recommended_tools": recommended_tools,
        "optional_tools": optional_tools,
        "required_mcp": required_mcp,
        "recommended_mcp": recommended_mcp,
        "optional_mcp": optional_mcp,
        "project_types": project_types,
        "processes": [item for item in getattr(args, "process", []) if item],
    }


def platform_contract_from_values(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": values["contract_id"],
        "title": values["title"],
        "type": "platform_contract",
        "version": values["version"],
        "status": "draft",
        "project_type_hints": values["project_types"],
        "applies_to": {
            "platforms": [values["platform_id"]],
            "project_type_hints": values["project_types"],
        },
        "requires": {
            "capabilities": ["filesystem.read", "filesystem.write"],
            "knowledge_packages": values["required_packages"],
            "tools": values["required_tools"],
            "mcp": values["required_mcp"],
            "templates": values["required_templates"],
        },
        "recommends": {
            "knowledge_packages": values["recommended_packages"],
            "templates": values["recommended_templates"],
            "tools": values["recommended_tools"],
            "mcp": values["recommended_mcp"],
        },
        "optional": {
            "knowledge_packages": values["optional_packages"],
            "templates": values["optional_templates"],
            "tools": values["optional_tools"],
            "mcp": values["optional_mcp"],
        },
        "includes": {
            "knowledge_packages": values["optional_packages"],
            "templates": values["optional_templates"],
            "tools": values["optional_tools"],
            "mcp": values["optional_mcp"],
            "processes": values["processes"],
        },
        "policies": {
            "missing_required_capability": "block",
            "missing_optional_resource": "warn",
        },
    }




def build_platform_authoring_plan(
    args: argparse.Namespace,
    command_name: str,
) -> tuple[AuthoringPlan, dict[str, Any], Path]:
    workplace_root = Path(args.workplace).expanduser().resolve()
    if not (workplace_root / "workplace.yaml").is_file():
        raise SystemExit(f"FAIL: workplace is not initialized: {workplace_root}")
    values = platform_authoring_values(args)
    _platform_dependency_preflight_service.check(
        workplace_root,
        values["required_packages"],
        values["required_templates"],
        values["required_tools"],
        values["required_mcp"],
    )
    root_id, platform_root = resolve_platform_root(
        workplace_root,
        getattr(args, "platform_root", None),
        mode="read",
    )
    target = contained_resource_path(
        platform_root,
        platform_root / values["contract_id"],
        "platform",
    )
    contract_path = target / "platform-contract.yaml"
    legacy_path = (
        workplace_root
        / "platforms"
        / values["platform_id"]
        / "platform.yaml"
    )
    registry_data = load_yaml_document(workplace_root / "registries" / "platforms.yaml")
    registry_entries = (
        registry_data.get("platforms")
        if isinstance(registry_data.get("platforms"), list)
        else []
    )
    existing_entry = next(
        (
            item
            for item in registry_entries
            if isinstance(item, dict)
            and str(item.get("id")) == values["platform_id"]
        ),
        None,
    )
    if legacy_path.is_file():
        raise SystemExit(
            "FAIL: unsupported legacy platform state exists at "
            f"{legacy_path}; remove or recreate it through a separately reviewed conversion"
        )
    if existing_entry and "platforms/" in str(existing_entry.get("path") or "").replace("\\", "/"):
        raise SystemExit(
            "FAIL: unsupported legacy platform registry entry; remove or recreate it "
            "through a separately reviewed conversion"
        )
    force = bool(getattr(args, "force", False))
    if contract_path.exists() and not force:
        raise SystemExit(f"FAIL: platform contract already exists: {contract_path}")
    contract = platform_contract_from_values(values)
    _update_schema_checks.require(
        contract,
        "platform-contract.schema.json",
        f"platform {values['contract_id']} contract",
    )
    registry_path = workplace_root / "registries" / "platforms.yaml"
    registry_bytes, _result, _proposed = planned_registry_upsert(
        registry_path,
        "platforms",
        {
            "id": values["platform_id"],
            "name": values["title"],
            "package_id": values["contract_id"],
            "path": rel(contract_path, workplace_root),
            "status": "available",
        },
        "platform-registry.schema.json",
    )
    registry_writes: list[AuthoringWrite] = []
    root_registry = workplace_root / "registries" / "platform-contract-roots.yaml"
    root_data = load_yaml_document(root_registry)
    roots = (
        root_data.get("platform_contract_roots")
        if isinstance(root_data.get("platform_contract_roots"), list)
        else []
    )
    if not roots:
        root_bytes, _root_result, _root_proposed = planned_registry_upsert(
            root_registry,
            "platform_contract_roots",
            {
                "id": "global",
                "label": "Global platform contracts",
                "path": "${PF_PLATFORM_CONTRACTS}",
                "scope": "workplace",
                "status": "available",
            },
            "platform-contract-roots-registry.schema.json",
        )
        registry_writes.append(
            AuthoringWrite(
                root_registry,
                root_bytes,
                role="registry",
                operation="replace" if root_registry.is_file() else "create",
                schema_name="platform-contract-roots-registry.schema.json",
                allow_replace=root_registry.is_file(),
            )
        )
    registry_writes.append(
        AuthoringWrite(
            registry_path,
            registry_bytes,
            role="registry",
            operation="replace" if registry_path.is_file() else "create",
            schema_name="platform-registry.schema.json",
            allow_replace=registry_path.is_file(),
        )
    )
    entity_writes = [
        AuthoringWrite(
            path,
            content,
            role="entity",
            operation="replace" if path.exists() else "create",
            schema_name=schema_name,
            allow_replace=force,
        )
        for path, content, schema_name in _platform_document_builder.build(
            target,
            values,
            contract,
            root_id,
        )
    ]
    transaction_id = f"{safe_id(command_name, 'platform')}-{values['platform_id']}-{uuid.uuid4().hex[:12]}"
    plan = AuthoringPlan(
        transaction_id=transaction_id,
        command=command_name,
        runtime_root=workplace_root / "runtime",
        authoritative_writes=entity_writes,
        registry_writes=registry_writes,
        post_commit_effects=[],
        validation_callbacks=[],
    )

    def validate_platform_plan(_plan: AuthoringPlan, staged: dict[Path, Path] | None) -> None:
        candidate = contract
        if staged is not None:
            candidate = load_yaml_document(staged[contract_path])
        _update_schema_checks.require(
            candidate,
            "platform-contract.schema.json",
            f"platform {values['contract_id']} staged contract",
        )
        platform_resolution = _platform_contract_resolver.resolve(
            workplace_root / "workplace.yaml",
            [values["contract_id"]],
            contract_overrides={values["contract_id"]: candidate},
        )
        failures = [
            item.message
            for item in _platform_contract_validation_service.validate(
                workplace_root,
                candidate,
                values["contract_id"],
                platform_resolution=platform_resolution,
            )
            if item.level == "FAIL"
        ]
        if failures:
            raise SystemExit("FAIL: staged platform validation failed: " + "; ".join(failures))

    plan.validation_callbacks.append(validate_platform_plan)
    plan.post_commit_effects.append(
        AuthoringEffect(
            "platform-audit-events",
            "runtime/resource-management/proposals/<transaction>.yaml and runtime/events/events.ndjson",
            kind="platform_audit",
            payload={
                "workplace_root": str(workplace_root),
                "command": command_name,
                "contract_id": values["contract_id"],
                "proposal_payload": {
                    "transaction_id": transaction_id,
                    "platform": values["contract_id"],
                    "platform_root": root_id,
                    "target": rel(contract_path, workplace_root),
                },
                "events": [
                    {
                        "event_type": "platform.contract.created",
                        "status": "created",
                        "message": "platform contract created",
                        "target": {"platform": values["contract_id"], "transaction_id": transaction_id},
                    },
                    {
                        "event_type": "platform.contract.linked",
                        "status": "linked",
                        "message": "platform registry updated",
                        "target": {"platform": values["contract_id"], "transaction_id": transaction_id},
                    },
                    {
                        "event_type": "platform.contract.doctor.passed",
                        "status": "passed",
                        "message": "staged platform checks passed",
                        "target": {"platform": values["contract_id"], "transaction_id": transaction_id},
                    },
                    {
                        "event_type": "platform.authoring.completed",
                        "status": "completed",
                        "message": "platform authoring completed",
                        "target": {"platform": values["contract_id"], "transaction_id": transaction_id},
                    },
                ],
            },
        )
    )
    return plan, values, contract_path


def command_platform_create(args: argparse.Namespace) -> int:
    mode = _authoring_input_service.mode(args)
    plan, _values, contract_path = build_platform_authoring_plan(args, "platform-create")
    workplace_root = Path(args.workplace).expanduser().resolve()
    if mode == "dry_run":
        render_authoring_dry_run(plan, workplace_root)
        return 0
    execute_authoring_plan(plan)
    print(f"PLATFORM: {rel(contract_path, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="platform-create"))
    return 0


def install_platform_args(args: argparse.Namespace) -> argparse.Namespace:
    platform_id = validate_resource_id(
        str(args.id).removeprefix("platform."),
        "platform",
    )
    return argparse.Namespace(
        workplace=args.workplace,
        id=platform_id,
        title=title_from_id(platform_id),
        version=args.version,
        platform_root=None,
        project_type=[platform_id],
        requires_package=[item for item in args.required_packages.split(",") if item],
        recommends_package=[
            item for item in args.recommended_packages.split(",") if item
        ],
        optional_package=[],
        requires_template=[
            item for item in args.required_templates.split(",") if item
        ],
        recommends_template=[
            item for item in args.recommended_templates.split(",") if item
        ],
        optional_template=[],
        requires_tool=[item for item in args.required_tools.split(",") if item],
        recommends_tool=[
            item for item in args.recommended_tools.split(",") if item
        ],
        optional_tool=[],
        requires_mcp=[item for item in args.required_mcp.split(",") if item],
        recommends_mcp=[item for item in args.recommended_mcp.split(",") if item],
        optional_mcp=[],
        process=[],
        force=False,
        apply=bool(getattr(args, "apply", False)),
        dry_run=bool(getattr(args, "dry_run", False)),
    )


def command_platform_contract_install(args: argparse.Namespace) -> int:
    normalized = install_platform_args(args)
    mode = _authoring_input_service.mode(normalized)
    plan, _values, contract_path = build_platform_authoring_plan(
        normalized,
        "platform-contract-install",
    )
    workplace_root = Path(args.workplace).expanduser().resolve()
    if mode == "dry_run":
        render_authoring_dry_run(plan, workplace_root)
        return 0
    execute_authoring_plan(plan)
    print(f"CONTRACT: {rel(contract_path, workplace_root)}")
    print_search_index_maintenance_summary(search_index_maintenance_for_known_projects(workplace_root, reason="platform-contract-install"))
    return 0


def command_diagnostics_configure(args: argparse.Namespace) -> int:
    project = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project)
    path = project / ".pf" / "diagnostics.json"
    options = diagnostics.invocation_options(args.diagnostic_profile, args.diagnostic_threshold, args.diagnostic_components, args.diagnostic_sink)
    def proposal():
        return diagnostics.configure_proposal(diagnostics._read_config(path), args.profile,
            duration=args.duration, run_id=args.run_id, session_id=args.session_id, invocation=options)
    try:
        proposed, report = proposal()
        if args.apply:
            with registry_file_lock(path, stale_after_seconds=0):
                proposed, report = proposal()
                # The encoder is identical to the bounded proposal validation.
                temp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    with temp.open("xb") as handle:
                        handle.write(diagnostics.encode(proposed))
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp, path)
                finally:
                    temp.unlink(missing_ok=True)
        report["action"] = "applied" if args.apply else "plan"
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError):
        print("FAIL: diagnostic configuration rejected; invalid input, policy lock or storage unavailable", file=sys.stderr)
        return 1


def command_diagnostics_status(args: argparse.Namespace) -> int:
    project = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project)
    options = diagnostics.invocation_options(args.diagnostic_profile, args.diagnostic_threshold, args.diagnostic_components, args.diagnostic_sink)
    logger = diagnostics.for_project(project, run_id=args.run_id, session_id=args.session_id, invocation=options)
    root = project / ".pf" / "runtime" / "diagnostics"
    files = [{"name": p.name, "bytes": p.stat().st_size} for p in diagnostics.log_files(root) if p.is_file() and not p.is_symlink()]
    print(json.dumps({"schema_version": 1, "effective": logger.effective(), "build": diagnostics.build_identity(__file__),
                      "storage": files, "health_scope": "current-process; retained records carry prior counters"}, indent=2))
    return 0


def command_diagnostics_export(args: argparse.Namespace) -> int:
    project = Path(args.project_root).expanduser().resolve()
    _run_task_inputs.require_flow_root(project)
    check = project_context_check_result(project)
    metadata = {"context_check": {k: check.get(k) for k in ("snapshot_id", "status", "reasons", "broken_refs", "stale_resources", "policy_action")},
                "entry_build": diagnostics.build_identity(__file__)}
    snapshot_yaml, _ = project_context_snapshot_paths(project)
    if snapshot_yaml.is_file():
        metadata["snapshot_sha256"] = hashlib.sha256(snapshot_yaml.read_bytes()).hexdigest()
    result = diagnostics.export_bundle(project, Path(args.output).expanduser().resolve(), request_id=args.request_id,
                                       run_id=args.run_id, since=args.since, until=args.until, metadata=metadata)
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProcessForge MVP init and doctor commands.")
    parser.add_argument("--diagnostic-profile", choices=list(diagnostics.PROFILES))
    parser.add_argument("--diagnostic-threshold", choices=list(diagnostics.LEVELS))
    parser.add_argument("--diagnostic-components", help="Comma-separated optional diagnostic components.")
    parser.add_argument("--diagnostic-sink", choices=["jsonl", "stderr", "both", "none"])
    sub = parser.add_subparsers(dest="command", required=True)

    ActionsCommandParser(execute=ActionsCommand(
        parser_factory=build_parser,
        execution_factory=process_execution_service,
        require_flow_root=_run_task_inputs.require_flow_root,
        dump_yaml=dump_yaml,
        version=PROCESSFORGE_VERSION,
    ).execute).register(sub.add_parser)

    DiagnosticsCommandParser(
        configure=command_diagnostics_configure,
        status=command_diagnostics_status,
        export=command_diagnostics_export,
    ).register(sub.add_parser)

    workplace_commands = WorkplaceCommandParser(
        doctor_workplace=command_doctor_workplace,
        first_run=command_first_run,
        init_workplace=command_init_workplace,
        workplace_mode_doctor=command_workplace_mode_doctor,
        workplace_mode_set=command_workplace_mode_set,
        workplace_mode_set_default_project_mode=command_workplace_mode_set_default_project_mode,
        workplace_mode_status=command_workplace_mode_status,
        workplace_setup_apply=command_workplace_setup_apply,
        workplace_setup_review=command_workplace_setup_review,
        workplace_setup_start=command_workplace_setup_start,
        workplace_setup_status=command_workplace_setup_status,
    )
    workplace_commands.register_setup(sub.add_parser)

    agent_entry_commands = AgentEntryCommandParser(
        agent_entry=AgentEntryCommand().execute,
        agent_start_prompt=AgentStartPromptCommand(
            require_flow_root=_run_task_inputs.require_flow_root,
            start_prompt_renderer=default_start_agent_here,
        ).execute,
        global_agents_section=command_global_agents_section,
    )
    agent_entry_commands.register_global_section(sub.add_parser)

    workplace_commands.register_modes(sub.add_parser)

    project_commands = ProjectCommandParser(
        doctor_project=command_doctor_project,
        init_project=command_init_project,
        project_init_repair=command_project_init_repair,
        project_init_status=command_project_init_status,
        project_mode_doctor=command_project_mode_doctor,
        project_mode_set=command_project_mode_set,
        project_mode_status=command_project_mode_status,
    )
    project_commands.register(sub.add_parser)

    director_commands = DirectorCommandParser(
        agent_director_run=command_agent_director_run,
        agent_director_status=command_agent_director_status,
        agent_director_tick=command_agent_director_tick,
        director_case_refresh=command_director_case_refresh,
        director_inbox_submit=command_director_inbox_submit,
        error_route=command_error_route,
    )
    director_commands.register_inbox(sub.add_parser)

    agent_entry_commands.register_prompt(sub.add_parser)

    workplace_commands.register_first_run(sub.add_parser)

    delivery_commands = DeliveryCommandParser(
        clean=command_clean,
        dev_test=command_dev_test,
        examples_check=command_examples_check,
        release_archive_test=command_release_archive_test,
        release_check=command_release_check,
        release_pack=command_release_pack,
        release_test=command_release_test,
        version=command_version,
        distribution_root=ROOT,
    )
    delivery_commands.register(sub.add_parser)

    navigation_commands = ResourceIndexCommandParser(
        path_resolve=command_path_resolve,
        search_index_doctor=SearchIndexDoctorCommand(
            index_factory=resource_search_index,
            snapshot_reader=local_search_runtime_snapshot,
            doctor_formatter=search_index_doctor_result,
        ).execute,
        search_index_rebuild=SearchIndexRebuildCommand(
            index_factory=resource_search_index,
            snapshot_reader=local_search_runtime_snapshot,
        ).execute,
        search_index_refresh=SearchIndexRefreshCommand(
            index_factory=resource_search_index,
            snapshot_reader=local_search_runtime_snapshot,
        ).execute,
        search_index_status=SearchIndexStatusCommand(
            index_factory=resource_search_index,
            snapshot_reader=local_search_runtime_snapshot,
        ).execute,
        search_index_tick=SearchIndexTickCommand(
            index_factory=resource_search_index,
            snapshot_reader=local_search_runtime_snapshot,
        ).execute,
    )
    navigation_commands.register(sub.add_parser)

    core_update_commands = CoreUpdateCommandParser(
        core_update_apply=command_core_update_apply,
        core_update_plan=command_core_update_plan,
        core_update_repair=command_core_update_repair,
        core_update_status=command_core_update_status,
    )
    core_update_commands.register(sub.add_parser)

    knowledge_commands = KnowledgeCommandParser(
        docs_import_plan=command_docs_import_plan,
        knowledge_add_resource=command_knowledge_add_resource,
        knowledge_add_url=command_knowledge_add_url,
        knowledge_hub_import=command_knowledge_hub_import,
        knowledge_hub_init=command_knowledge_hub_init,
        knowledge_index_refresh=command_knowledge_index_refresh,
        knowledge_package_build_from_candidates=command_knowledge_package_build_from_candidates,
        knowledge_package_create=command_knowledge_package_create,
        knowledge_package_doctor=command_knowledge_package_doctor,
        knowledge_package_release=command_knowledge_package_release,
    )
    knowledge_commands.register_resources(sub.add_parser)

    templates_commands = TemplateCommandParser(
        template_add=command_template_add,
        template_create=command_template_create,
        template_doctor=command_template_doctor,
    )
    templates_commands.register(sub.add_parser)

    providers_commands = ProviderCommandParser(
        mcp_register=command_mcp_register,
        tool_register=command_tool_register,
    )
    providers_commands.register(sub.add_parser)

    specializations_commands = SpecializationCommandParser(
        specialization_bind_platform=command_specialization_bind_platform,
        specialization_create=command_specialization_create,
        specialization_doctor=command_specialization_doctor,
        specialization_list=command_specialization_list,
        specialization_show=command_specialization_show,
    )
    specializations_commands.register(sub.add_parser)

    overrides_commands = ProjectOverrideCommandParser(
        project_override_add=command_project_override_add,
        project_override_doctor=command_project_override_doctor,
        project_override_list=command_project_override_list,
        override_modes=PROJECT_OVERRIDE_MODES,
    )
    overrides_commands.register(sub.add_parser)

    platforms_commands = PlatformCommandParser(
        platform_contract_doctor=command_platform_contract_doctor,
        platform_contract_install=command_platform_contract_install,
        platform_create=command_platform_create,
    )
    platforms_commands.register_install(sub.add_parser)

    knowledge_commands.register_create(sub.add_parser)

    platforms_commands.register_authoring(sub.add_parser)

    updates_commands = UpdateCommandParser(
        project_upgrade_check=command_project_upgrade_check,
        self_update_check=command_self_update_check,
        update_apply=command_update_apply,
        update_bootstrap_source_list=command_update_bootstrap_source_list,
        update_bootstrap_source_validate=command_update_bootstrap_source_validate,
        update_candidates_clear=command_update_candidates_clear,
        update_candidates_list=command_update_candidates_list,
        update_candidates_refresh=command_update_candidates_refresh,
        update_candidates_show=command_update_candidates_show,
        update_changelog_show=command_update_changelog_show,
        update_doctor=command_update_doctor,
        update_entity_sources_list=command_update_entity_sources_list,
        update_entity_sources_rebuild=command_update_entity_sources_rebuild,
        update_manifest_validate=command_update_manifest_validate,
        update_notifications_acknowledge=command_update_notifications_acknowledge,
        update_notifications_create=command_update_notifications_create,
        update_notifications_list=command_update_notifications_list,
        update_rollback=command_update_rollback,
        update_sources=command_update_sources,
        update_stage=command_update_stage,
        update_verify=command_update_verify,
    )
    updates_commands.register(sub.add_parser)

    presence_commands = AgentPresenceCommandParser(
        agent_availability=command_agent_availability,
        agent_checkin=command_agent_checkin,
        agent_checkout=command_agent_checkout,
        agent_heartbeat=command_agent_heartbeat,
        agent_ledger_doctor=command_agent_ledger_doctor,
        agent_list=command_agent_list,
        agent_register=command_agent_register,
        agent_status=command_agent_status,
        session_start=command_session_start,
    )
    presence_commands.register_session_start(sub.add_parser)

    context_commands = ProjectContextCommandParser(
        assignment_capsule=command_assignment_capsule,
        capsule_doctor=command_capsule_doctor,
        context_compile=command_context_compile,
        context_resolve=command_context_resolve,
        doctor_context=command_doctor_context,
        project_context_check=command_project_context_check,
        project_context_mark_stale=command_project_context_mark_stale,
        project_context_refresh=command_project_context_refresh,
    )
    context_commands.register_snapshot_capsule(sub.add_parser)

    authoring_commands = ProcessAuthoringCommandParser(
        authoring_parity_check_all=command_authoring_parity_check_all,
        authoring_transaction_recover=command_authoring_transaction_recover,
        knowledge_package_parity_check=command_knowledge_package_parity_check,
        platform_parity_check=command_platform_parity_check,
        process_authoring_apply=command_process_authoring_apply,
        process_authoring_import=command_process_authoring_import,
        process_authoring_review=command_process_authoring_review,
        process_authoring_start=command_process_authoring_start,
        process_create=command_process_create,
        process_parity_check=command_process_parity_check,
        process_parity_check_all=command_process_parity_check_all,
        template_parity_check=command_template_parity_check,
    )
    authoring_commands.register(sub.add_parser)

    catalog_commands = ProcessCatalogCommandParser(
        builtin_process_catalog_doctor=command_builtin_process_catalog_doctor,
        pack_activate=command_pack_activate,
        pack_list=command_pack_list,
        process_describe=command_process_describe,
        process_doctor=command_process_doctor,
        process_layout_doctor=command_process_layout_doctor,
        process_layout_migrate=command_process_layout_migrate,
        process_list=command_process_list,
    )
    catalog_commands.register(sub.add_parser)

    evolution_commands = EvolutionCommandParser(
        evolve_candidate_create=command_evolve_candidate_create,
        evolve_candidate_export=command_evolve_candidate_export,
        evolve_candidate_list=command_evolve_candidate_list,
        evolve_candidate_sanitize=command_evolve_candidate_sanitize,
        evolve_run=command_evolve_run,
    )
    evolution_commands.register(sub.add_parser)

    knowledge_commands.register_hub_release(sub.add_parser)

    drivers_commands = RuntimeDriverCommandParser(
        runtime_driver_describe=command_runtime_driver_describe,
        runtime_driver_list=command_runtime_driver_list,
        runtime_driver_validate=command_runtime_driver_validate,
    )
    drivers_commands.register(sub.add_parser)

    workers_commands = WorkerRunCommandParser(
        worker_run_collect=command_worker_run_collect,
        worker_run_prepare=command_worker_run_prepare,
        worker_run_start=command_worker_run_start,
        worker_run_status=command_worker_run_status,
        worker_run_stop=command_worker_run_stop,
    )
    workers_commands.register(sub.add_parser)

    inspector_commands = ExecutionInspectorCommandParser(
        supervisor_run=command_supervisor_run,
        supervisor_status=command_supervisor_status,
        supervisor_stop=command_supervisor_stop,
        supervisor_tick=command_supervisor_tick,
    )
    inspector_commands.register(sub.add_parser)

    from pf_runtime.monitor import interval_value

    configuration_commands = ConfigurationCommandParser(
        execute=ConfigurationCommand(service_factory=configuration_service,
                                     project_service_factory=project_configuration_service,
                                     flow_root=locate_flow_root).execute,
    )
    configuration_commands.register(sub.add_parser)

    monitor_commands = MonitorCommandParser(
        runtime_monitor=command_runtime_monitor,
        interval_parser=interval_value,
    )
    monitor_commands.register(sub.add_parser)

    runtime_commands = RuntimeCommandParser(
        runtime_autostart_install=command_runtime_autostart_install,
        runtime_autostart_remove=command_runtime_autostart_remove,
        runtime_autostart_status=command_runtime_autostart_status,
        runtime_doctor=command_runtime_doctor,
        runtime_event=command_runtime_event,
        runtime_project_state=command_runtime_project_state,
        runtime_resolve=command_runtime_resolve,
        runtime_restart=command_runtime_restart,
        runtime_serve=command_runtime_serve,
        runtime_session_register=command_runtime_session_register,
        runtime_start=command_runtime_start,
        runtime_status=command_runtime_status,
        runtime_stop=command_runtime_stop,
        runtime_tick=command_runtime_tick,
        runtime_work_state=command_runtime_work_state,
    )
    runtime_commands.register(sub.add_parser)

    codex_mcp_commands = CodexMcpCommandParser(
        codex_mcp_install=command_codex_mcp_install,
        codex_mcp_remove=command_codex_mcp_remove,
        codex_mcp_status=command_codex_mcp_status,
    )
    codex_mcp_commands.register(sub.add_parser)

    runtime_host_commands = RuntimeHostCommandParser(
        runtime_host_event=command_runtime_host_event,
        runtime_host_init=command_runtime_host_init,
        runtime_host_project_state=command_runtime_host_project_state,
        runtime_host_projection_doctor=command_runtime_host_projection_doctor,
        runtime_host_rebuild_projections=command_runtime_host_rebuild_projections,
        runtime_host_resolve=command_runtime_host_resolve,
        runtime_host_status=command_runtime_host_status,
        runtime_host_tick=command_runtime_host_tick,
        runtime_host_work_state=command_runtime_host_work_state,
    )
    runtime_host_commands.register(sub.add_parser)

    orchestration_commands = OrchestrationCommandParser(
        orchestrator_plan_apply=command_orchestrator_plan_apply,
        orchestrator_plan_create=command_orchestrator_plan_create,
        orchestrator_plan_status=command_orchestrator_plan_status,
        orchestrator_plan_validate=command_orchestrator_plan_validate,
        worker_launch_prompt_create=command_worker_launch_prompt_create,
    )
    orchestration_commands.register_plan_prompt(sub.add_parser)

    presence_commands.register_attendance(sub.add_parser)

    leases_commands = AgentLeaseCommandParser(
        agent_lease_doctor=command_agent_lease_doctor,
        agent_lease_grant=command_agent_lease_grant,
        agent_lease_list=command_agent_lease_list,
        agent_lease_release=command_agent_lease_release,
        agent_lease_revoke=command_agent_lease_revoke,
    )
    leases_commands.register(sub.add_parser)

    handoffs_commands = HandoffCommandParser(
        handoff_accept=command_handoff_accept,
        handoff_create=command_handoff_create,
        handoff_doctor=command_handoff_doctor,
        handoff_finalize=command_handoff_finalize,
        handoff_offer=command_handoff_offer,
        handoff_return=command_handoff_return,
        handoff_start_target_run=command_handoff_start_target_run,
        handoff_status=command_handoff_status,
        process_route_doctor=command_process_route_doctor,
        process_route_list=command_process_route_list,
        process_route_validate=command_process_route_validate,
    )
    handoffs_commands.register(sub.add_parser)

    director_commands.register_scheduling(sub.add_parser)

    continuation_commands = ContinuationCommandParser(
        continuation_create=command_continuation_create,
        continuation_doctor=command_continuation_doctor,
        continuation_resume=command_continuation_resume,
        continuation_status=command_continuation_status,
    )
    continuation_commands.register(sub.add_parser)

    orchestration_commands.register_shell_aliases(sub.add_parser)

    agent_entry_commands.register_operations(sub.add_parser)

    work_commands = WorkCommandParser(
        work_cancel=command_work_cancel,
        work_resource_read=WorkResourceReadCommand(
            resource_factory=work_resource_service,
            require_flow_root=_run_task_inputs.require_flow_root,
            dump_yaml=dump_yaml,
        ).execute,
        work_start=WorkStartCommand(
            execution_factory=process_execution_service,
            require_flow_root=_run_task_inputs.require_flow_root,
            dump_yaml=dump_yaml,
        ).execute,
        work_state=WorkStateCommand(
            execution_factory=process_execution_service,
            require_flow_root=_run_task_inputs.require_flow_root,
            dump_yaml=dump_yaml,
        ).execute,
        work_transition=WorkTransitionCommand(
            execution_factory=process_execution_service,
            require_flow_root=_run_task_inputs.require_flow_root,
            dump_yaml=dump_yaml,
        ).execute,
    )
    work_commands.register_start(sub.add_parser)

    egress_core = sys.modules[__name__]

    def execute_egress(args: argparse.Namespace) -> int:
        import processforge_core.egress.service as egress_service

        return egress_service.command(args, egress_core)

    egress_commands = EgressCommandParser(
        execute=execute_egress,
    )
    egress_commands.register(sub.add_parser)

    work_commands.register_state_resources_transition_cancel(sub.add_parser)

    runs_commands = RunCommandParser(
        run_complete=command_run_complete,
        run_create=command_run_create,
        run_doctor=command_run_doctor,
        run_list=command_run_list,
        run_status=command_run_status,
        run_summary=command_run_summary,
        run_statuses=_core_work_consistency.RUN_STATUSES,
    )
    runs_commands.register(sub.add_parser)

    tasks_commands = TaskCommandParser(
        task_complete=command_task_complete,
        task_create=command_task_create,
        task_doctor=command_task_doctor,
        task_list=command_task_list,
        task_start=command_task_start,
    )
    tasks_commands.register(sub.add_parser)

    iterations_commands = IterationCommandParser(
        iteration_add=command_iteration_add,
        iteration_complete=command_iteration_complete,
        iteration_kinds=ITERATION_KINDS,
        iteration_statuses=_core_work_consistency.ITERATION_STATUSES,
    )
    iterations_commands.register(sub.add_parser)

    hooks_commands = HookCommandParser(
        events_validate=command_events_validate,
        hooks_dispatch=command_hooks_dispatch,
        event_types=REQUIRED_PROCESSFORGE_EVENT_TYPES,
    )
    hooks_commands.register(sub.add_parser)

    chat_commands = ChatCommandParser(
        chat_export=command_chat_export,
        chat_record=command_chat_record,
    )
    chat_commands.register(sub.add_parser)

    context_commands.register_resolution(sub.add_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    return CliApplication(
        parser_factory=build_parser,
        project_id_resolver=project_id,
        entry_file=__file__,
    ).run(argv)



# Concrete owners retain the distribution root and existing request-scoped readers.
_release_source_policy = ReleaseSourcePolicy()
_telemetry_event_service = TelemetryEventService(context_inputs=_context_contract_inputs)
_agent_workplace_registry = AgentWorkplaceRegistry(documents=_yaml_documents)
_chat_export_service = ChatExportService()
_hook_dispatch_policy = HookDispatchPolicy(hooks=_hook_configuration_reader, documents=_yaml_documents)
_orchestration_config_service = OrchestrationConfigService()
_project_capability_resolution = ProjectCapabilityResolution(ROOT)
_project_classifier_sources = ProjectClassifierSourceReader(ROOT)
_project_coordination_state = ProjectCoordinationStateService(documents=_yaml_documents, inputs=_context_contract_inputs)
_project_override_reader = ProjectOverrideReader(ROOT)
_project_scan_policy = ProjectScanPolicy()
_public_source_policy = PublicSourcePolicy(distribution_root=ROOT, inputs=_context_contract_inputs)
_release_git_provenance = ReleaseGitProvenance(source_policy=_release_source_policy)
_run_task_consistency_service = RunTaskConsistencyService(ROOT)
_run_task_inputs = RunTaskInputReader()
_session_metadata_writer = SessionMetadataWriter(inputs=_context_contract_inputs)
_supervisor_input_service = SupervisorInputService(ROOT, documents=_yaml_documents, inputs=_context_contract_inputs, work_paths=_work_paths)
_supervisor_state_inputs = SupervisorStateInputs(documents=_yaml_documents, inputs=_context_contract_inputs, work_paths=_work_paths)
_worker_observation_inputs = WorkerObservationInputService()
_workplace_registry_reader = WorkplaceRegistryReader(inputs=_context_contract_inputs)
_workplace_resource_events = WorkplaceResourceEventJournal(documents=_yaml_documents, telemetry=_telemetry_event_service)
_workplace_setup_answers = WorkplaceSetupAnswers()
_workspace_access_references = WorkspaceAccessReferenceService()



# Concrete Core ownership for the next existing responsibilities.
_project_runtime_launchers = ProjectRuntimeLauncherBuilder()
_project_discovery_reader = ProjectDiscoveryReader(classifiers=_project_classifier_sources, rules=_project_classifier_rule_policy, detection=_project_detection_service, documents=_yaml_documents)
_project_resource_matcher = ProjectResourceMatcher(platforms=_platform_contract_reader)
_project_file_templates = ProjectFileTemplateBuilder(ROOT, discovery=_project_discovery_reader, resources=_project_resource_matcher, initialization_inputs=_project_initialization_inputs, platform_selection=_project_platform_selection_service, coordination=_project_coordination_reader, platform_resolver=_platform_contract_resolver, runtime_launchers=_project_runtime_launchers)
_workplace_file_builder = WorkplaceFileBuilder(ROOT)
_workplace_terms = WorkplaceTermsBuilder()
_official_pack_profiles = OfficialPackProfileReader(ROOT)
_runtime_hook_dispatcher = RuntimeHookDispatcher(policy=_hook_dispatch_policy, inputs=_context_contract_inputs)
_process_event_recorder = ProcessEventRecorder(journal=_process_event_journal, inputs=_run_task_inputs, hooks=_hook_dispatch_policy, telemetry=_telemetry_event_service, configuration=_core_project_configuration_inputs.project_configuration_reader, dispatcher=_runtime_hook_dispatcher)
_chat_transcript_writer = ChatTranscriptWriter(events=_process_event_recorder, exports=_chat_export_service)
_release_manifest_policy = ReleaseManifestPolicy(file_digests=FileDigestReader())
_release_command_plan = ReleaseCommandPlanBuilder()

if __name__ == "__main__":
    sys.exit(main())
