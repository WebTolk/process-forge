# Python Core Structure

This is an implementation reference for Core contributors. For daily operation,
start with [Garage Core](garage-core.md), [Runtime model](runtime-model.md) and
the shared [requirements](../requirements.md). The ownership and migration
details below are not additional user workflow steps.

The core is evolving incrementally. `tools/processforge.py` is still the active legacy facade, not retired code. Existing CLI, MCP, hook entrypoints and bootstrap aliases remain unchanged.

The migration target is a thin compatibility facade: entrypoints parse and format transport data, then call the OOP Core that owns behavior, state and rules. Each migrated responsibility uses concrete Core owners without importing or calling the monolith. Remaining callback paths are recorded as unfinished migration work.

**pf-app-server** is the optional long-lived background ProcessForge application/server process, launched through the existing runtime/server commands. It hosts Runtime scheduling and shared application services; CLI and MCP are separate entry adapters. The term names the running process and its lifetime; command, API and configuration names stay compatible.

## Package Placement

New implementation modules belong to a cohesive responsibility package, following
[the Core placement rule](../../src/processforge_core/AGENTS.md). Packages use short
lowercase names, modules use `snake_case.py`, and classes use `CapWords`; a module
may contain a service, its errors and related helpers. There is no class-per-file
requirement. Keep the package tree shallow and package initializers minimal.

The existing Work modules now live in `processforge_core.work`: `context`,
`context_read`, `inventory`, `records`, `metadata`, `resources`, `resource_material`,
`selection`, `state`, `boundary_advisory`, `transition_commit`, `automation_readiness`,
`transition_rejection`, `publication`, `events` and `capsule_publication`. For example,
import `WorkResourceService` from `processforge_core.work.resources`. Current
Core/CLI/MCP/Host consumers use these paths. Old flat Work module imports are not
retained during this dev refactor.

Bootstrap/composition/shared seams and remaining legacy modules are still at the
root; other responsibility groups move in subsequent bounded work. The structure
uses ordinary Python packages, with no import compatibility layer or new loader.

The agent instruction entry modules live in `processforge_core.agent_entry`:
`contract`, `migration`, `profiles`, `adapters` and `start_prompt`. For example, import
`load_contract` from `processforge_core.agent_entry.contract`. Project initialization,
CLI and existing checks use canonical imports; old flat entry-module imports are
removed during this dev refactor. The package groups existing implementations and
preserves instruction formats, command behavior and transaction guards.

Run completion services live in `processforge_core.completion`: `policy`,
`documents`, `intent_builder`, `intent_read`, `intent_validation` and `intent_replay`.
For example, import `CompletionIntentReadService` from
`processforge_core.completion.intent_read`. Composition and process execution use
canonical imports; old flat completion modules are removed during this dev refactor.
The existing classes, lazy factories, journal formats and ordered recovery remain
unchanged. The process coordinator retains lifecycle decisions, guards and run locks.

Process definition reading, offered process selection and pin construction live in
the existing `processforge_core.process_catalog` package: `definition_read`,
`selection` and `pin`, alongside `models` and `service`. For example, import
`ProcessDefinitionReadService` from `processforge_core.process_catalog.definition_read`.
Composition, process execution and existing checks use canonical imports; old flat
module paths are removed during this dev refactor. The existing rules, explicit
dependencies and live reads remain unchanged; admission and lifecycle authority
remain in the process coordinator.

Automation readiness projections and recoverable transition rejection rules live
in `processforge_core.work.automation_readiness` and
`processforge_core.work.transition_rejection`. For example, import
`AutomationReadinessService` from `processforge_core.work.automation_readiness`.
Composition, process execution and existing checks use the owning modules; old
flat paths are removed during this dev refactor. The complete existing classes,
frozen callback dependencies and lazy factories are unchanged. Lifecycle guards,
locks, response formats and recovery retain their existing owners.

Evidence collection, validation and stage readiness rules live in
`processforge_core.evidence`: `collection`, `validation` and `readiness`. For
example, import `EvidenceValidationService` from
`processforge_core.evidence.validation`. Composition, process execution and
existing checks use the owning modules; old flat paths are removed during this
dev refactor. The complete existing implementations, frozen callbacks, live file
diagnostics and lazy factories are unchanged. Lifecycle authority, guards, locks
and transition recovery remain in the process coordinator.

## Current Ownership

Action discovery lives in `processforge_core.operations.catalogue`. Its
`ActionCatalog` receives descriptor data and optional explicit Work facts;
it does not import argparse, Runtime or the monolithic CLI, invoke handlers or
grant permissions. CLI/MCP registration inspection belongs to
`tools/pf_runtime/action_catalog.py`. Native MCP execution remains an adapter
over existing owners, not a claim that legacy worker implementation is migrated.
See [supported actions](action-discovery.md).

| Module | Responsibility |
| --- | --- |
| `src/processforge_core/resources/project_packages.py` | Project package manifests, root records, current candidate/index reads, duplicate tracking and dependency IDs through concrete Core paths/documents. |
| `src/processforge_core/project/platform_resolution.py` | Existing recursive platform hierarchy and resource/dependency aggregation with concrete catalog, projection and package owners. |
| `src/processforge_core/process_catalog/semantics.py` | Existing authoring coverage, semantic projections and ordered compatibility comparison. |
| `src/processforge_core/presentation/process_parity.py` | Existing process import/parity Markdown reports, separate from semantic rules. |
| `src/processforge_core/runtime/worker_plans.py` | Existing worker plan defaults, subagent/dependency projections, recursion and current assignment-completion reads. |
| `src/processforge_core/project/platform_selection.py` | Existing platform/type/registry selection and findings with concrete answer, document, detection, platform and package owners. |
| `src/processforge_core/maintenance/registries.py` | Existing entity/override/installed registry reads and install-target resolution; no installation or version-write authority. |
| `src/processforge_core/runtime/worker_validation.py` | Current worker plan, extension-key and subagent report checks. |
| `src/processforge_core/project/hooks.py` | Hook configuration location and ordered validation. |
| `src/processforge_core/common/record_validation.py` | Existing event/chat field and secret validation. |
| `src/processforge_core/process_catalog/routes.py` | Current route lookup, validation and required role. |
| `src/processforge_core/process_catalog/handoffs.py` | Handoff directory/path and soft document read. |
| `src/processforge_core/maintenance/validation.py` | Existing update override and normalized-manifest checks. |
| `src/processforge_core/project/platform_documents.py` | Existing platform document model/byte construction. |
| `src/processforge_core/project/registry_checks.py` | Current registry paths and package-root validation. |
| `src/processforge_core/common/text.py` | Canonical trailing newline and diagnostic hint formatting. |
| `src/processforge_core/common/yaml_dump.py` | Exact existing YAML scalar and recursive serialization. |
| `src/processforge_core/process_catalog/audit.py` | Existing ordered builtin process catalog report and flat package index. |
| `src/processforge_core/project/setup.py` | Existing workplace setup proposal mapping and Markdown. |
| `src/processforge_core/project/registry_write.py` | Existing schema-checked registry upsert and atomic staging. |
| `src/processforge_core/project/templates.py` | Existing template root selection and manifest lookup. |
| `src/processforge_core/project/platform_validation.py` | Existing ordered platform semantic validation. |
| `src/processforge_core/common/policies.py` | Shared policy entry and identifier matching primitives. |
| `src/processforge_core/project/requirements.py` | Existing platform dependency preflight and registry ID reads. |
| `src/processforge_core/process_catalog/contracts.py` | Existing ordered process contract validation, route document reads and shared handoff modes. |
| `src/processforge_core/agent_entry/` | Entry contract, profiles, client adapters, start prompt and guarded instruction placement/recovery. |
| `src/processforge_core/completion/` | Run completion policy, summary/index documents and durable completion intent construction, reading, validation and replay. |
| `src/processforge_core/evidence/` | Existing evidence collection/identity, normalization and live file diagnostics, requirement/gate satisfaction and ordered readiness blockers through explicit callbacks. |
| `src/processforge_core/garage.py` | Remaining legacy helpers; current Work readers live under `work/records.py` and project context under `project/`. |
| `src/processforge_core/work/projection.py` | Existing pure Work projection/classification rules, without Core or lifecycle authority. |
| `src/processforge_core/work/metadata.py` | Explicit operation-local Run/Assignment metadata acquisition shared by summary/catalog, with current-content parse reuse and full live completion inputs when needed. |
| `src/processforge_core/work/bootstrap.py` | Existing guidance/start delegation through explicit summary and deferred typed start dependencies. |
| `src/processforge_core/work/creation_scope.py` | Existing scope validation/overlay with explicit deferred dependencies, without lifecycle authority. |
| `src/processforge_core/work/start_documents.py` | Existing pure Run/Assignment construction, preserving fields and references. |
| `src/processforge_core/work/start_publication.py` | Existing ordered post-capsule start publication through deferred operation dependencies. |
| `src/processforge_core/work/continuation_read.py` | Existing bounded control-document reads and Continuation/selection paths with explicit live dependencies. |
| `src/processforge_core/work/continuation_contract.py` | Existing record version and binding validation with an explicit error provider. |
| `src/processforge_core/work/continuation_status.py` | Existing live waiting/status/selected reads with explicit dependencies. |
| `src/processforge_core/work/continuation_publication.py` | Existing continuation create/resume publication, lock order and session marker recovery through explicit live dependencies. |
| `src/processforge_core/work/cancellation_replay.py` | Existing cancellation journal replay, atomic publication and event deduplication through explicit live dependencies. |
| `src/processforge_core/work/continuation_work.py` | Existing exact Continuation Work binding reads and executable/cancellation validation with narrow dependencies. |
| `src/processforge_core/work/resource_context.py` | Existing pinned Work resource context reads with explicit dependencies. |
| `src/processforge_core/work/resource_declarations.py` | Existing identifier, indexing-declaration, allowlist overlay and portable-reference rules shared with prepared inputs. |
| `src/processforge_core/work/resource_bindings.py` | Existing initial bounded material binding assembly and per-resource failure records for capsule creation. |
| `src/processforge_core/work/permissions.py` | Shared pure Work permission readiness. |
| `src/processforge_core/project/reconciliation.py` | Existing context reconciliation projection through the required deferred typed context checker, without Core. |
| `src/processforge_core/project/context.py` | Existing five ProjectContextService operations and context-specific per-dispatch readers through required typed dependencies, without Core. |
| `src/processforge_core/process_execution.py`, `work/continuation.py` | Governed lifecycle, selection, pinned execution, evidence and completion/recovery. |
| `src/processforge_core/completion/request.py` | Existing completion readiness and completion request orchestration, with live facade callbacks. |
| `src/processforge_core/work/state.py` | I/O-free completion/action/blocker rules and existing Work-state response projection; not lifecycle authority. |
| `src/processforge_core/work/automation_readiness.py`, `work/transition_rejection.py` | Existing automation readiness projections, live assignment-event reads and recoverable transition rejection response rules through explicit callbacks. |
| `src/processforge_core/work/boundary_advisory.py` | Existing Work boundary advisory and fresh-session completed-boundary reads with their distinct route/handoff rules and explicit read dependencies. |
| `src/processforge_core/work/record_catalog.py` | Existing validated active/historical Run/Assignment catalog with pending completion and explicit live dependencies. |
| `src/processforge_core/documents/reader.py`, `work/inventory.py` | YAML reading and live sorted discovery; no shared mutable document cache. |
| `src/processforge_core/work/records.py` | Live raw Run/Assignment reader; selection and recovery remain in the application service. |
| `src/processforge_core/work/publication.py` | Existing atomic Work text/YAML publication through explicit deferred formatter/writer dependencies. |
| `src/processforge_core/work/events.py` | Existing Work event envelope and subsequent diagnostics through a typed, dynamically resolved emitter. |
| `src/processforge_core/work/context_read.py` | Live capsule validation and assignment normalization through concrete Core contract inputs. |
| `src/processforge_core/work/context_documents.py` | Concrete Work field/document inputs, path/scope/dependency projection, required-source observations and capsule coordination projection. |
| `src/processforge_core/work/context.py` | Existing assignment context compilation; parameter merging uses ParameterMergePolicy directly, while the compiler retains other legacy dependencies. |
| `src/processforge_core/process_catalog/` | Concrete catalog and effective ProcessDefinition readers; offered process selection and pin construction retain their explicit operation dependencies. |
| `src/processforge_core/process_catalog/summary.py` | Allowed-process context summary using a concrete catalog by default and an optional narrow catalog port for injection, without a monolith callback. |
| `src/processforge_core/project/metadata.py` | Live project identity, manifest and flow-root reads through concrete Core YAML; shared by context, catalog and resources. |
| `src/processforge_core/project/snapshot.py` | Live ProjectContextSnapshot loading through concrete Core YAML and file digest readers, bound to the project root. |
| `src/processforge_core/common/digests.py` | Existing raw-byte SHA256 file reading, shared by snapshot reads, monolithic facades and maintenance update. |
| `src/processforge_core/configuration/parameters.py` | Stateless ParameterMergePolicy owning existing parameter-map merging and ordered provenance, without a monolith dependency. |
| `src/processforge_core/project/classification.py` | Stateless ProjectClassifierRulePolicy for matching existing classifier rules; registry, traversal and activation remain legacy responsibilities. |
| `src/processforge_core/common/paths.py` | Shared path_matches_pattern primitive for classification and detection, alongside the unchanged rel helper. |
| `src/processforge_core/process_catalog/artifacts.py` | Stateless ProcessArtifactDeclarationPolicy for defined, declared and produced artifact IDs; contract checks and companion inspection use Core services; authoring publication retains its existing owner. |
| `src/processforge_core/process_catalog/authoring.py` | ProcessAuthoringDefinitionBuilder for existing defaults, answer normalization and process materialization, using concrete evolution rules. |
| `src/processforge_core/process_catalog/evolution.py` | ProcessEvolutionPolicy for existing evolve defaults, normalization and ordered validation checks. |
| `src/processforge_core/runtime/drivers.py` | RuntimeDriverDefinitionPolicy for existing builtin documents, registry defaults, placeholders, limits and document readiness checks. |
| `src/processforge_core/maintenance/sites.py` | UpdateSitePolicy for existing source identity, derived site records, overrides and policy merging, without I/O. |
| `src/processforge_core/process_catalog/presentation.py`, `process_catalog/coordination.py` | Existing authoring text rendering and shared process coordination projection. |
| `src/processforge_core/runtime/catalog.py` | RuntimeDriverCatalogReader for existing live registry/document lookup with an explicit distribution root and concrete Core readers. |
| `src/processforge_core/evolution/candidates.py` | KnowledgeCandidateTargetingPolicy for existing candidate identity, target/routing, promotion readiness and targeting validation. |
| `src/processforge_core/maintenance/versions.py`, `maintenance/presentation.py` | Existing update-version normalization/selection and assessment rendering. |
| `src/processforge_core/project/coordination.py` | ProjectCoordinationReader for existing project/workplace coordination defaults, mode normalization and live config reads. |
| `src/processforge_core/common/privacy.py`, `evolution/privacy.py` | Canonical shared text patterns/predicates and existing evolve findings/redaction/recursive value transformation. |
| `src/processforge_core/maintenance/source_contracts.py` | UpdateSourceContractPolicy for existing trust, URL/env/source shape checks, registry validation and stable sorting. |
| `src/processforge_core/work/outputs.py` | WorkOutputPolicy for existing output/report paths, waivers, required-output checks and verification fingerprints. |
| `src/processforge_core/project/detection.py` | ProjectDetectionService for current generic file inventory and existing platform detection rules. |
| `src/processforge_core/runtime/environment.py` | WorkerEnvironmentPolicy for placeholder expansion, durable explicit environment and launch-only inheritance. |
| `src/processforge_core/maintenance/schema_checks.py` | UpdateSchemaChecks for the existing JSON Schema subset and current schema-file checks with an explicit distribution root. |
| `src/processforge_core/work/paths.py` | WorkPaths for existing Run, Assignment, artifact, handoff and worker-attempt locations, preserving their distinct ID normalization. |
| `src/processforge_core/runtime/command.py` | WorkerCommandBuilder for existing sandbox projection and command composition with concrete Core policies. |
| `src/processforge_core/project/platforms.py` | PlatformContractReader for live seed/project/workplace catalog overlays and exact registry fallback. |
| `src/processforge_core/maintenance/documents.py` | UpdateDocumentReader for existing registry paths, YAML/JSON reads, doctor checks and local file-URL resolution. |
| `src/processforge_core/runtime/selection.py` | RuntimeDriverSelectionService for existing task/saved-command driver selection through concrete Core readers and policies. |
| `src/processforge_core/project/platform_policy.py` | PlatformContractPolicy for existing reference, dependency and required/recommended/optional resource projections. |
| `src/processforge_core/process_catalog/validation.py` | ProcessAuthoringValidationService for existing authoring logic, companion paths/file checks and canonical workflow/iteration constants. |
| `src/processforge_core/common/json_io.py` | Canonical existing json_read primitive with current file reads and unchanged native failures. |
| `src/processforge_core/common/checks.py`, `common/ids.py`, `common/values.py` | Shared mutable Check and factory, identifier/title, list/string-list and borrowed parameter-mapping primitives. |
| `src/processforge_core/project/context_read.py` | Existing execution context freshness checks and manifest reads through explicit typed operation dependencies, without Core. |
| `src/processforge_core/project/mode.py` | Existing `GarageModeService` coordination read model through a required snapshot port, without Core. |
| `src/processforge_core/project/reports.py` | Existing `DerivedReportLifecycleService` and fixed derived report paths through required snapshot/flow-root dependencies, without Core. |
| `src/processforge_core/project/initialization.py` | Existing project onboarding, initialization status and deterministic repair, reusing guarded agent entry transactions. |
| `src/processforge_core/resources/local_search.py` | Existing authorized local index, SQLite/FTS search, verified Work material search, coverage and indexing policy helpers. |
| `src/processforge_core/runtime/metrics.py` | Existing bounded runtime metrics collection, registered project roots, freshness and collection workers; import from `processforge_core.runtime.metrics`. |
| `src/processforge_core/maintenance/update.py` | Existing Core update plan, controlled apply, status and recovery, preserving manifest and backup guards; import from `processforge_core.maintenance.update`. |
| `src/processforge_core/prepared/input.py`, `prepared/resources.py` | Existing immutable prepared inputs, worker-attempt manifests, authorized resource material and collection receipts; import from `processforge_core.prepared.input` or `processforge_core.prepared.resources`. |
| `src/processforge_core/prepared/snapshot_read.py` | Existing pinned/current prepared-resource snapshot reads and ordered validation through required deferred dependencies. |
| `src/processforge_core/prepared/resource_selection.py` | Existing prepared resource row selection, unique matching, strict immutable bindings and current-row revocation rules. |
| `src/processforge_core/prepared/registry_resources.py` | Existing prepared templates/tools/MCP registry-resource matching, revocation and path-resolution reads through narrow deferred dependencies. |
| `src/processforge_core/prepared/knowledge_resources.py` | Existing prepared knowledge-resource material verification and grant provenance through required deferred dependencies. |
| `src/processforge_core/project/host_integration.py` | Existing bounded optional host integration status used by project setup and the CLI. |
| `src/processforge_core/common/request_scope.py` | Existing per-request parsing scope shared by Garage, lifecycle, YAML/capsule readers and MCP; isolated snapshots and bounded cache. |
| `src/processforge_core/resources/snapshot.py` | Existing resource snapshot roots, authorized selection, path resolution and private result navigation; snapshot loading remains in project/snapshot.py. |
| `src/processforge_core/resources/access.py` | ResourceSearchService and ResourceResolveService with narrow typed read ports; existing readiness, authorized search/resolve, navigation and snapshot injection. |
| `src/processforge_core/ports.py` | Internal structural current-work, raw Work-record, context-read and process-definition dependencies. |
| `src/processforge_core/composition.py` | Explicit service factories and the remaining LegacyResourceSearchReadAdapter; migrated current-work, context, definition and resource-resolve readers use concrete Core owners. |
| `src/processforge_core/bootstrap.py` | Existing runtime module assembly and lazy access to the service factories. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade and transport/host/provider adapters. |

`build_current_work_service(project_root, *, documents=None)` constructs the concrete CurrentWorkService with Core YAML and inventory readers. RuntimeBootstrap, context and start consumers call this owner directly; LegacyWorkReadAdapter and WorkReadCorePort are removed. Construction performs no I/O and introduces no global service cache or DI container. Remaining bootstrap/lifecycle callback edges still require separate migration.

`CurrentWorkService(project_root, documents=...)` receives a YAML document reader rather than the monolithic Core. The default reader, inventory and projection rules belong to Core; current consumers use the concrete owner. Its module path, discovery order, missing-assignment fallback, bootstrap-placeholder handling, summary shape and error behavior are preserved.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None, snapshots=None)` is shared by CLI, MCP and Host/Daemon. `RuntimeBootstrap.process_execution_service(...)` delegates to it. Construction does not load the CLI, resolve a project, read configuration or perform I/O. The three-argument `ProcessExecutionService` constructor remains compatible; optional dependencies are keyword-only and excluded from equality/repr. Remaining legacy dependencies are explicit, not replaced by a universal Core interface.

`WorkRecordReadPort` exposes `runs`, `load_run` and `load_assignment`. The factory defaults to `YamlWorkRecordReader`, which uses the existing `WorkInventory` and YAML loader. Roots and records are read live; no cross-request result cache is added. Direct legacy construction retains its inventory and private-path fallback, including subclass overrides. Raw readers neither choose Work nor hide duplicate/alias discovery or pending recovery.

`WorkContextReadPort` exposes genuine context-result injection. The default
`WorkContextReadService` is bound to the explicit project root and concrete
`work.context_documents.ContextContractInputs`, which owns the original field
normalizers and document/identity inputs through Core YAML, IDs and paths.
`LegacyWorkContextAdapter` and the factory Core/path callback arguments are removed.
Monolithic helper functions call actual Core methods. Shared `work.context` rules
retain signed identity/intent, pins, scope and stage views; byte/path/checksum,
parse/error order and live reads are preserved. The reader captures no legacy Core.
Generic contract creation and require-ready capability dependencies remain separate
migration work; whole coordinator/bootstrap independence is not claimed.

`ProcessDefinitionReadPort` exposes `effective_process(run)`. The concrete `ProcessCatalogReadService(project_root)` reads project/workplace catalog context and active packs with Core document/path owners, then reuses the existing catalog algorithms. `ProcessDefinitionReadService(project_root, *, catalog=None)` uses that owner and the existing canonical fingerprint. The lazy `build_process_definition_read_service(project_root)` factory and coordinator no longer receive a monolith resolver; `LegacyProcessDefinitionAdapter` is removed. The monolithic catalog-context facade delegates to the catalog owner. Valid and corrupt pins do not consult the catalog; unpinned definitions are resolved live on each call and returned copies preserve unknown fields. Existing `pinned`, `corrupt`, `legacy_unpinned`, `missing` results, exception boundaries and lifecycle authority remain unchanged.

`ProjectSnapshotReadPort` exposes `load(path=None)` and `checksum(path)` for genuine injection. The default `ProjectSnapshotReadService` receives the project root and concrete Core `YamlDocumentReader` and `FileDigestReader`; `LegacyProjectSnapshotAdapter` is removed. Both snapshot factories accept only the project root. Normal Project context, process execution, Garage mode, reports, resource search/resolve, Work resources and prepared resources use this reader without a snapshot callback into old Core. Pin creation still passes one captured path to loading and checksum; resource selection, start preflight and capsule capture load independently. Existing canonical paths, YAML error markers, missing-file behavior, raw-byte hashes and request-local parse isolation are retained. `FileDigestReader` also owns both monolithic `sha256_file` facades and the maintenance update facade. Snapshot-generation checks remain in `work/context.py`; its validator does not gain a live snapshot-read dependency. Other lifecycle, resource and bootstrap adapters remain separate migration work.

`ExecutionProjectReadService` belongs to `project/context_read.py`. Its required keyword-only dependencies are project/workplace paths, a typed context-check callable resolver, a document-loader resolver and a late flow-root callback. `build_execution_project_read_service` only assembles these dependencies; each `_context_check` or `_manifest` facade dispatch builds a fresh service without I/O or cached results. Context checking passes the workplace explicitly only when `workplace.yaml` exists; `ProjectContextService.check` retains its distinct always-explicit behavior. Manifest reading resolves the loader before the overridable `_flow_root` callback, preserving callable lookup, live reads and exception order. The coordinator retains its private operational methods, admission decisions, guards and lifecycle authority; no Core field or old module alias is introduced in the read service.

`ProcessExecutionService.state()` retains exact selection, context/pin checks, evidence/outcome validation and permission readiness. `WorkStatePolicy` separately computes completion requirements and action/blockers from supplied records. It does not read files, alter records, choose caller identity or advance a process. Terminal, completed, blocked and incomplete precedence remains unchanged; permission readiness stays a separate response field.

`ProjectContextService` belongs to `project/context.py` and has no Core field. Its two project/workplace paths and required keyword-only snapshot/read dependencies describe the existing five operations. `build_project_context_service(project_root, workplace_root, core, *, snapshots=None)` retains its consumer-facing signature and performs no I/O; it builds the existing default reader only for `None`, preserving falsey injected readers. Snapshot paths, raw documents and errors remain live; no checksum is required for these reads. Context imports/captures its four mode/report/process-summary/boundary factories once at dispatch entry, before the freshness check, in a context-specific `ProjectContextReaders` value. The other helpers are resolved at their original use sites. `scoped_request`, always-explicit workplace checking, check-before-snapshot and broken-check suppression of the primary read remain unchanged. Mode/report fallback receives independent default readers, rather than the injected context port. Runtime resolution captures the current resolver before evaluating `self.snapshot()`. All context keys, resource values, call order and continuation recommendation mutation retain their form. MCP consumers still use the factory after ingress guards; no old Garage class/import alias, constructor compatibility, cache or authority is introduced.

`ResourceSearchService` requires a narrow `ResourceSearchReadPort` instead of the universal Core object and retains optional keyword-only `snapshots` injection. `LegacyResourceSearchReadAdapter` in composition owns the existing Core reads and preserves late callable lookup. An explicitly supplied empty snapshot still bypasses loading; a falsey injected reader retains its identity. The search freshness guard precedes reading, while blocked readiness retains its existing coverage read. `build_resource_search_service` keeps its released signature and assembles the existing MCP search consumer without I/O, after ingress guards. Project context retains its existing replaceable service binding and supplies the same read adapter. Index maintenance, query arguments, navigation, coverage, payloads and error boundaries retain their existing behavior.

`ResourceResolveService(project_root, workplace_root, reads=None, *, snapshots=None)` uses the concrete `ResourceResolveReadService` by default. It reads project identity, live snapshots and portable path references through Core owners; `LegacyResourceResolveReadAdapter` is removed. `build_resource_resolve_service(project_root, workplace_root, *, snapshots=None)` is shared by Host and MCP. Project ID is read first; an empty resource ID returns project metadata without reading a snapshot. Falsey injected reader/snapshot identity and the existing resolver evaluation order are preserved. `WorkspacePathReferenceReader` owns registry/package/path-constant resolution, and shared search/Garage/Work resource helpers call it without a monolith object. Selection, aliases, raw fields, navigation, errors and Host/MCP binding/freshness guard order remain unchanged. ResourceSearchService still has context/runtime dependencies awaiting later migration; this slice does not claim independence of the entire resource subsystem.

`GarageModeService` belongs to `project/mode.py` and takes `(project_root, workplace_root, *, snapshots)` with a required `ProjectSnapshotReadPort`; it receives no Core. The dependency is excluded from repr/equality. Its existing `snapshot or ...` fallback is preserved: an empty supplied snapshot triggers `snapshots.load()`, while a nonempty one bypasses it. `build_garage_mode_service(project_root, workplace_root, core, *, snapshots=None)` performs no I/O and builds the existing default reader only when the dependency is `None`, preserving a falsey injected reader. Context does not forward its own optional reader into the mode fallback. Coordination, session representation, blockers and mode policy retain their behavior; a session alone does not promote Garage to Forge. No old constructor or module alias is retained.

`DerivedReportLifecycleService` and `DERIVED_REPORTS` belong to `project/reports.py`. The service receives required keyword-only `snapshots` and `flow_root` dependencies, with no Core or implicit reads at construction. `build_derived_report_lifecycle_service(project_root, core, *, snapshots=None)` builds an independent default snapshot reader only for `None` and binds flow-root resolution for the later status call. `ProjectContextService.context` uses this factory without forwarding its own injected reader. An empty supplied snapshot still triggers a read before flow-root lookup. Fixed report order and paths, timestamp fallback, filesystem checks, historical exception handling and aggregate status retain the existing rules.

`ProcessSummaryReadService(project_root=None, catalog=None)` owns allowed-process summaries through the concrete catalog by default, with an optional narrow catalog read port. It preserves snapshot/manifest selection, candidate order and duplicates, current ID/stage count, name/purpose/description fallbacks and exact OSError/ValueError/SystemExit handling. With no project root it does not read definitions. `build_process_summary_read_service(project_root=None)` performs no I/O at construction and passes no monolith resolver or Core object. ProjectContextService uses it at the original payload position. The deferred definition_resolver field is removed; real file-backed and copied-Core default paths qualify the migrated responsibility.

`FreshSessionBoundaryReadService` is colocated with WorkBoundaryAdvisoryService in work/boundary_advisory.py. Its project root, concrete Core document reader and existing relative-path implementation support the fresh-session completed-boundary read without a monolith adapter. `build_fresh_session_boundary_read_service(project_root)` builds that default owner. Governed Work returns before reads. Glob order, timestamp ties, newest usable completed handoff, live route checks, stable process de-duplication and the no-older-handoff rule are preserved. Its fresh recommendation remains distinct from the neighboring auto advisory projection.

`WorkDocumentPublisher` belongs to `work/publication.py` and owns the existing atomic text/YAML operations. Its required keyword-only dependencies resolve a text writer and YAML formatter at operation time; `build_work_document_publisher` binds them without I/O or eager Core/private-method lookup. YAML obtains the current `_atomic_text` callable before formatting, preserving subclass/fault interception and exception order, then applies the existing `rstrip()` plus exactly one newline. Text publication retains parent directory creation, UUID temporary name, UTF-8 write and `Path.replace`, with the existing failure behavior. `ProcessExecutionService` keeps its live `_atomic_yaml`/`_atomic_text` operational methods, so Continuation, transition and completion/recovery callbacks still use the same seams. Caller-supplied paths, locks, guards and lifecycle authority retain their current owners. No Core field, compatibility alias, extra cleanup, fsync or retry rule is introduced.

`WorkEventPublisher` belongs to `work/events.py` and owns the existing event publication algorithm. It receives the project path, an availability callback and a provider of the exact keyword `ProcessEventEmitter` protocol; it receives no Core. `build_work_event_publisher` only binds those dependencies. The coordinator supplies the original dynamic `hasattr` policy and a separate late emitter lookup on every operation, before evaluating event arguments. An absent emitter returns before diagnostics, while a present non-callable attribute still raises. Event payloads, assignment paths, correlation/event IDs and `blockers or []` retain their existing form. Journal publication precedes the late import and existing Work diagnostics. `ProcessExecutionService._emit` remains the live operational facade for start, transition, completion/recovery and Continuation callbacks. Journal storage, event security, locks, deduplication and lifecycle authority retain their current owners; no alias or new rule is introduced.

`AssignmentCapsulePublisher` belongs to `work/capsule_publication.py`. Its required keyword-only dependencies preserve the existing immutable capsule algorithm; the exact keyword `ContextFieldsBuilder` protocol delegates grants and scope normalization to the unchanged builder. `build_assignment_capsule_publisher` binds deferred operational methods and Core helpers without reading files. The context builder is resolved from its owning module when invoked, after the existing-path guard and snapshot read. `_write_capsule` retains the live subclass/fault interception point. Capsule fields, updates, exclusive UTF-8 `open("x")`, `FileExistsError` cause/remediation and relative-path-before-raw-hash return remain unchanged. Ordinary atomic replacement, locks, authority and new publication rules are outside this publisher.

`ContextReconciliationService` belongs to `project/reconciliation.py`. Its required keyword-only getter returns the existing `ProjectContextCheck` before project/workplace arguments are evaluated. `build_context_reconciliation_service` binds that getter without I/O or early Core attribute lookup. The stale-reason classification, technical refresh advice, broken/operator decision, result fields and exceptions retain their existing form. This existing service has no production consumers in the current source; the relocation adds no route or automatic refresh. The old Garage class/import alias is removed.

`GovernedWorkBootstrapService` lives in `work/bootstrap.py`. Required named current-work summary and typed WorkStart getter dependencies replace Core. Cold composition supplies existing CurrentWorkService and ProcessExecutionService at call time; start lookup precedes option normalization. Existing guidance, preferred-stage mapping and lifecycle authority are preserved. The old Garage class/import is removed without an alias; no new route or consumer is added.

`WorkProjectionPolicy` in `work/projection.py` groups the existing item classification, objective normalization and compact active-run projections without I/O or Core. CurrentWorkService retains its constructor and live WorkInventory discovery; it uses a local stateless policy at the existing projection points. Status/fallback order, bootstrap exclusion, ordered deduplication and ten-item limits are unchanged. The old Garage helper functions/constants are removed without aliases.

`CreationScopeService` in `work/creation_scope.py` groups existing pure operator-envelope validation and assignment overlay. Cold composition supplies deferred mode normalization and bounded handoff reads; deep copies, predecessor coordination metadata, raw checksum, errors and lookup order are unchanged. CLI/MCP use the canonical static validator. Actual predecessor identity/admission/overlap/capsule authority remains with existing owners; the public scope schema is unchanged.

`WorkStartDocumentBuilder` in `work/start_documents.py` constructs the existing Run/Assignment dictionaries without I/O or Core. Fields, timestamps, title slicing order and shared pin/specialization references are preserved. The lifecycle coordinator still chooses IDs/process/stage, binds sessions/security/scope, validates readiness, publishes the immutable capsule and owns writes/locks/events. No schema or public start behavior changes.

`WorkStartPublicationService` in `work/start_publication.py` sequences existing post-capsule publication through eight required deferred method providers. Run/Assignment/plan/index writes, four start events, fresh state, projection and created_new response retain their order. Method lookup precedes argument evaluation; construction has no I/O. Admission, locks and capsule authority remain in ProcessExecutionService, and atomic writers/event storage are reused without a new transaction or recovery policy.

`ContinuationRecordReader` in `work/continuation_read.py` owns the existing record/selection paths, 2 MiB bounded reads and worker/lease control-record checks through eight required deferred providers, without Core. Existing decode/dictionary/session rules, terminal worker statuses, wildcard lease predicate, glob/lookup order and errors are unchanged. The coordinator retains overridable read/writer call points and all binding/resume/cancel authority; the control loader stays live and construction performs no reads.

`ContinuationContractPolicy` in `work/continuation_contract.py` owns the existing record ID/status, exact version and binding checks through a required deferred error provider. The coordinator keeps its overridable validation entry and binding authority. The existing pure `permission_readiness` function lives in `work/permissions.py`, shared with lifecycle start/state without importing the Continuation coordinator. Versions, error priority, permission blockers, list references and released results remain unchanged.

`ContinuationStatusReadService` in `work/continuation_status.py` performs the existing waiting/status/selected read workflows through eleven required deferred operation providers. Discovery freshness, the 20-candidate limit, the 128-artifact limit, receipt/version comparisons, callback lookup order and results remain unchanged. The coordinator retains overridable facade methods, public error translation and mutation/binding authority; cold composition introduces no cache or permissions.

`ContinuationWorkReadService` in `work/continuation_work.py` performs the existing exact Run/Assignment/Capsule binding read for continuation and operator cancellation through fourteen required deferred dependencies and narrow read protocols, without Core. Executable and terminal flags, repeated lookups, validation/error order, result references and cancellation identity rules are unchanged. The coordinator retains its constructor, overridable Work call, locks, session binding and mutation/recovery authority; cold composition introduces no new permission or cache.

`WorkResourceContextReadService` in `work/resource_context.py` owns the existing pinned context read through nine required deferred dependencies, without Core. Invalid selectors fail before Core/project-root/document access. Run/Assignment/Capsule reads, digest and process/snapshot/resource/stage pins, execution-contract import/call order, read scope and result references remain unchanged. WorkResourceService keeps its constructor, bounded loader, overridable context call and public resource routes; composition is cold.

`ContinuationPublicationService` in `work/continuation_publication.py` groups the existing create and resume publication algorithms through twelve required deferred providers, without Core. Validation, Work binding, nested lock order, preview/existing/apply semantics, v1 wait-only handling, session selection before resumed marker, OSError recovery and repeated live reads remain unchanged. The coordinator retains the public signatures and existing read/validation/status override points. Cold frozen composition adds no policy, cache or document format.

`CancellationReplayService` in `work/cancellation_replay.py` owns the existing cancellation journal replay through ten required deferred providers and narrow writer/binding/event protocols, without Core. Checksum, quiescence, capsule and preimage checks, repeated lookups, atomic records/index/events/projection/receipt order, event deduplication, exception and reference semantics remain unchanged. The coordinator retains admission, locks, preview, journal creation, already-applied handling and the replay override point. Cold frozen composition adds no cancellation policy or cache.

`WorkMaterialReadService` in `work/material_read.py` owns the existing two-phase metadata verification and material read for Work search/resolve through nine required deferred dependencies, without Core. All requested metadata checks precede budget creation and any material read; original literal statuses, five material comparisons, live root/capture dependencies, per-capture operation checks, deep copies and shared provenance references are preserved. Cold composition performs no reads. WorkResourceService retains selector/grant/freshness/pagination guards, public errors and coverage, overridable context/search calls and the concrete legacy root callback. This adds no resource permissions or material cache.

`ResourceDeclarationPolicy` in `work/resource_declarations.py` groups the existing pure identifier, declared indexing, authoritative allowlist/overlay and portable-reference rules for Work and prepared resources. One required deferred error factory preserves each caller error type; the policy performs no reads and receives no Core. The identical legacy indexing tables are reused from resource_material.py. Order, precedence, bounds, deep copies, unknown fields and lexical path errors are unchanged; all consumers use the owning policy without old helper aliases. Material capture, authorization and worker preparation retain their owners.

`ResourceBindingBuilder` in `work/resource_bindings.py` assembles the existing initial resource bindings through eight required deferred providers, without Core or construction-time reads. The active `build_resource_bindings` function keeps its signature and snapshot import, and explicitly supplies the existing declaration/snapshot/root/material/error operations. Capsule publication and Work/prepared read authorization retain their owners. Empty selections still read the current allowlist, the shared budget and literal status guard remain unchanged, per-resource failures permit subsequent captures, and original binding references and final availability semantics are preserved. The lazy factory only assembles the builder; no cache or read-time pin migration is introduced.

`PreparedResourceSnapshotReader` in `prepared/snapshot_read.py` owns the existing paired current/pinned snapshot read for prepared resource admission. Seven required deferred operation dependencies preserve current-read comparison, freshness, immutable generation pins, checksum fallback, exception boundaries and reference identities without Core or a cache. Its lazy composition factory performs no I/O. The canonical prepared-resource caller retains all admission/material decisions and bounded YAML guards; the old internal snapshot helper is removed.

`PreparedResourceSelectionPolicy` in `prepared/resource_selection.py` groups the existing row selection, unique-match, strict binding-schema and current-row revocation rules shared by knowledge and registry resource preparation. Three required deferred matcher/error/status providers remove Core from these rules. Matching still looks up its callback for each row, original exception boundaries and row references are preserved, and construction performs no I/O. Both existing admission paths use the canonical policy; their grants, material capture, path resolution and access authority remain unchanged.

`PreparedRegistryResourceReader` in `prepared/registry_resources.py` handles the existing shared templates/tools/MCP preparation scenario through five required deferred policy/manifest/resolver/status/error providers. A narrow callable protocol preserves the workspace-manifest Path-or-None keyword contract; neither reader nor lazy factory receives Core or performs construction-time I/O. Every nonempty group keeps live manifest/matcher/resolver reads, ordered refusal checks, path-reference deep copies and original resolution references. The canonical prepared caller retains public admission and grant order; the old internal registry helper is removed.

`PreparedKnowledgeResourceReader` in `prepared/knowledge_resources.py` handles the existing knowledge material verification and grant-provenance scenario through nine required deferred providers. It reuses selection/declaration policies, canonical metadata fingerprints and bounded material capture; two callable protocols describe the actual root/capture operations. The reader and lazy factory receive no Core and perform no construction-time reads. The prepared caller retains outer authority and group order; its explicit callback still delegates root resolution to the existing Work helper. Empty requests retain binding/current-allowlist checks and budget creation. Generation/material checks, error boundaries, live dependencies and grant references stay unchanged. The old knowledge helper and fingerprint wrapper are removed.

`search_material` in `resources/local_search.py` owns the existing in-memory SQLite FTS5 algorithm over already verified Work documents. WorkResourceService retains its search dispatch and all authorization/material checks; a required deferred error factory preserves its error type without a Work import in the search module. SQL, connection cleanup, exception chaining, ranking, pagination and result/provenance references are unchanged. The shared workplace index and its maintenance keep their existing lifetime; no storage adapter or new command is introduced.

## Observation

`EvidenceCollectionPolicy` owns the existing current/history collection, merge and evidence identity rules without I/O or Core. `ProcessExecutionService` retains its private facade methods, passing its current/identity callbacks explicitly so subclass dispatch remains compatible. Current/history and previous merge records are deep-copied; incoming merge records retain their reference identity. Later input/artifact aliases still replace older records. Lifecycle and persistence retain their existing owners.

`tools/smoke_evidence_collection_policy.py` covers retained collection algorithms, alias replacement, ordering, copy/reference semantics, facade overrides and package use without CLI. `--baseline` compares the retained service; `--scratch-root` confines fixtures.

`EvidenceValidationService` owns the existing evidence normalization, safe path and file diagnostic algorithms. Its frozen dependencies are the project root and explicit clock, relative path, hash and optional path resolver callbacks. The composition factory performs no I/O; the private facade preserves deferred Core access and subclass overrides. Paths and file bytes are checked on every call, with the existing diagnostic codes and error order.

`tools/smoke_evidence_validation_service.py` covers retained outcomes and callback counts, copy semantics, not-applicable evidence, live file changes/deletion, unsafe paths, read failures, exception identity and isolated package construction. It accepts `--baseline` and `--scratch-root`.

`StageReadinessPolicy` owns the existing requirement/gate satisfaction, required artifact selection and ordered blocker rules. Its frozen callbacks provide file diagnostics, string lists, executable stages and facade blocker dispatch. The policy performs no direct I/O and receives no Core; the composition factory only assembles dependencies. Private facade methods preserve aliases, latest evidence, status sets, diagnostic priority and copy/reference semantics. Automation loading, state orchestration and transition persistence retain their existing owners.

`tools/smoke_stage_readiness_policy.py` covers retained pure rules, callback counts/overrides, optional artifacts/gates, blocker order, exception identity and live validation of changed/deleted files through the shared facade. It accepts `--baseline` and `--scratch-root`.

Work-state reads use the existing PF diagnostics operation, validation span and bounded request/YAML counters. Pass an existing `diagnostics.Logger` as `observer` for direct-library observation, or inherit the current operation. Without either, the default is no-op and creates no diagnostic files. No ambient logger or current Work is captured at service construction.

Selected run/assignment/stage identity is bound inside the read operation and restored afterward, including failures. Existing profile filtering, expiry, budgets and sink-failure handling apply. An operation-completed record means the read returned, not that a Task succeeded; the domain action is unchanged. Timing/spans are not a CPU or memory profiler.

CLI/MCP retain their outer diagnostic and authorization boundaries. Host state reads share the same instrumentation but do not automatically enable a file logger; without an outer observer they remain no-op. Daemon IPC/scheduler and generic-worker coverage require separate bounded work. Initialization, denied and status preflight paths do not gain implicit logging writes.

## Boundaries

Ports and composition are internal, provisional interfaces, not additions to the package's stable public API. A `Protocol` describes dependencies for type checking; it does not authorize filesystem access or validate grants. The current-work port has no transition or write methods.

Other services still depend on the legacy core. The target separation is domain decisions, application services, infrastructure adapters and thin transports, assembled explicitly. Those layers are not fully extracted yet. Historical formats, pinned capsules, protective refusals and trusted provider boundaries must survive subsequent changes.

`tools/smoke_core_read_composition.py` checks characterization, fake-port composition, bootstrap fields, delegation and an isolated installed-shaped package without a CLI. That fixture is not acceptance of an actual installed Core or connected host. Source, archive, installed and connected-host qualification remain distinct.

`tools/smoke_core_work_state.py` checks the extracted policy, state semantics, no-I/O composition, observer profiles/failures/isolation, and CLI/MCP/Host delegation. Its optional `--baseline` compares a retained original state method; `--scratch-root` confines temporary fixtures. The isolated package check proves imports and composition in an installed-shaped tree, not a live installation or connected Daemon.

`tools/smoke_work_record_read_composition.py` covers injected records, live YAML and selector compatibility. `tools/smoke_work_context_read_composition.py` covers injected context, capsule refusals, normalization/readiness, live reads and observation. Their optional retained baselines prove parity; they do not qualify a real installed Core. Snapshot repositories, atomic writes/recovery and the remaining legacy services still require separate bounded extraction.

`tools/smoke_process_definition_read_composition.py` covers pins, exact exceptions, copying, live legacy resolution, injected dependencies and no-I/O assembly. It also checks state guards and an isolated package without a CLI; `--baseline` compares a retained original method and `--scratch-root` confines fixtures. These are source/fixture checks, not actual installed-Core acceptance.

`tools/smoke_project_snapshot_read_composition.py` checks reader substitution at all four read sites, immutable-capsule refusal before loading, equal-size/mtime updates, raw-byte checksums, private path/hash overrides, constructor compatibility and assembly without the CLI. `--baseline` compares retained original helpers, including exceptions and call order; `--scratch-root` scopes temporary fixtures.

`tools/smoke_garage_snapshot_read_composition.py` covers Garage snapshot injection, live paths, canonical construction/composition, context/runtime payloads, error order, request isolation and MCP composition after ingress guards. It supports retained original methods through `--baseline` and confines fixtures through `--scratch-root`.

`tools/smoke_resource_search_snapshot_composition.py` covers readiness/search read injection, supplied-empty and stale-context branches, maintenance/error order, live YAML, request scopes, MCP guards/error mapping and package use without CLI. `--baseline` compares the retained original service and `--scratch-root` confines fixtures.

`tools/smoke_resource_resolve_snapshot_composition.py` covers retained resolution behavior, empty ids, injected readers, aliases and selection order, live YAML and request isolation, MCP guard order, Host compatibility and package use without CLI. `--baseline` compares the retained original resolver and `--scratch-root` confines fixtures.

`tools/smoke_garage_mode_snapshot_composition.py` covers retained mode and context behavior, empty-snapshot fallback, injected readers, constructor substitutions, session policy, live YAML and request isolation, and package use without CLI. `--baseline` compares the retained mode service, `--context-baseline` compares its retained context consumer, and `--scratch-root` confines fixtures.

`AutomationReadinessService` extracts existing automation readiness projections and live assignment-event reads. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_automation_readiness.py` checks retained behavior and injected dependencies.

`WorkStatePolicy.project_state` also owns the existing full selected-state response projection, from supplied records and two explicit fingerprint/stable-id calculation callbacks. The coordinator retains request scope, guards, validation/readiness/diagnostics and obtains action and project identity in their original order. Field/evaluation order, fallback, exceptions and original references remain unchanged; the policy gains no Core, filesystem reads, cache, constructor dependency or lifecycle authority. Existing decision and completion methods are unchanged.

`WorkRecordCatalogService` in `work/record_catalog.py` owns existing Work record enumeration and active/historical projection through eight required deferred providers, using WorkRecordReadPort or the unchanged WorkInventory fallback. Safe identity filtering before assignment loading, run binding, pending-completion activity, fallback field order, duplicate rows, exceptions and repeated live reads are preserved. ProcessExecutionService retains its private facade and selection/completion override points. Cold frozen composition adds no selection policy or shared cache.

`WorkSelectionService` extracts existing exact Work selection, bound preference and objective matching. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_work_selection_service.py` checks retained behavior and injected dependencies.

`ProcessSelectionService` extracts existing offered process selection and bounded candidate descriptions. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_process_selection_service.py` checks retained behavior and injected dependencies.

`ProcessPinReadService` extracts existing live snapshot reads and process pin construction. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_process_pin_read_service.py` checks retained behavior and injected dependencies.

`WorkCompletionRequestService` in `completion/request.py` owns the existing `can_complete` and `complete` request orchestration. Nine required deferred providers retain selection, pinned/final-stage checks, blocker order, state references and the committed-intent retry path. The public coordinator methods keep their signatures and live `can_complete`/`transition` overrides. The frozen service and lazy factory perform no construction I/O; intent storage, locks, guards, transition and recovery retain their owners.

`RunCompletionPolicy` extracts existing run completion blockers and in-memory task status updates. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_run_completion_policy.py` checks retained behavior and injected dependencies.

`CompletionIntentValidationService` extracts existing completion intent validation with ordered ownership and terminal checks. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_validation_service.py` checks retained behavior and injected dependencies.

`TransitionRejectionPolicy` extracts existing recoverable transition rejection classification and response construction. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_transition_rejection_policy.py` checks retained behavior and injected dependencies.

`WorkBoundaryAdvisoryService` extracts existing process boundary recommendations and advisory handoff discovery. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_work_boundary_advisory_service.py` checks retained behavior and injected dependencies.

`CompletionDocumentService` extracts existing completion summary rendering and existing task index publication. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_document_service.py` checks retained behavior and injected dependencies.

`CompletionIntentBuilder` extracts existing self-contained completion intent construction before terminal writes. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_builder.py` checks retained behavior and injected dependencies.

`CompletionIntentReadService` extracts existing completion intent path resolution and guarded live journal reads. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_read_service.py` checks retained behavior and injected dependencies.

`CompletionIntentReplayService` extracts existing ordered completion intent replay through existing storage and event operations. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; coordinator decisions, locks and access checks remain in the facade; storage and event operations retain their adapters. `tools/smoke_completion_intent_replay_service.py` checks retained behavior and injected dependencies.

`WorkTransitionCommitService` publishes an already permitted transition through explicit operation callbacks. It preserves stage history, ordered Run/Assignment publication, completion intent/replay, fresh state, projections, events and boundary advice. `ProcessExecutionService.transition` retains admission, access checks and the enclosing run lock; its constructor and transport entrypoints remain unchanged. `build_work_transition_commit_service` assembles dependencies without I/O. `tools/smoke_work_transition_commit_service.py` checks publication order, required failures and late facade overrides.


`work.records` owns `YamlWorkRecordReader` and `CurrentWorkService`. Their normal
composition uses the Core `YamlDocumentReader` and YAML fallback directly, with
project-bound paths and live `WorkInventory`; it no longer accepts monolithic Core.
`LegacyWorkReadAdapter`, `WorkReadCorePort`, and the unused internal
`governed_work_summary` facade are removed. Bootstrap/context/start consumers call
these Core readers. `FreshSessionBoundaryReadService` uses Core document and relative
path implementations. The coordinator's raw Run/Assignment reads also use Core YAML;
its remaining lifecycle/admission/completion callbacks still need later migration.
Public CLI/MCP/Daemon contracts are retained. This is a bounded dependency removal,
not proof that the entire bootstrap or coordinator is independent of legacy.

`agents.presence.AgentPresenceReader` owns existing live Agent presence paths,
JSON reads, canonical/legacy record deduplication and exact session selection.
It receives a workplace root and uses concrete Core identity and filesystem
implementations. The monolithic presence functions call its methods; the reader
does not depend on the CLI, Host or legacy callbacks. The shared opaque identity
digest in `common.ids` also serves chat transcript paths. Presence formats,
ambiguity, unknown fields and read failures are retained. Attendance writes,
expiry, binding, leases and bounded Runtime observation keep their current owners.
The Runtime Host, session read models and `RuntimeProcess.status_payload` call
this reader directly at their ten presence read sites. Imports remain local to
operations so adapter modules can still load before Core bootstrap. Stale
updates and their internal reads keep their existing owner; the two Work-state
reads remain separate live reads. CLI presence wrappers, bounded metrics,
attendance mutations and the observational organized-session scan remain
explicit migration work.

`chat.transcripts.ChatTranscriptReader` owns the existing transcript paths and live
exact-session message reads. Its concrete default `common.ndjson.NdjsonReader`
owns the shared NDJSON parser, including original line numbers and parse-error
records. The monolithic path/message/parser functions call Core methods;
Runtime session reads and fallback duplicate detection use the Chat reader directly.
Legacy-before-canonical message order, first-ID deduplication, unknown fields,
opaque identities and decoding/error behavior are preserved. Session authorization,
paging, message writes, export shaping and ingress provenance retain their existing
owners; this slice does not establish independence of the whole pipeline.

`resources.catalog_read.WorkplaceSearchCatalogReader` owns the live physical
Workplace search catalogue: registered package manifests, active official-pack
knowledge packages, resource projection, templates and the deterministic snapshot
fingerprint. Its concrete inputs are Workplace/distribution paths and
`YamlDocumentReader`; it reuses `WorkspacePathReferenceReader` and the single
official-pack traversal in `process_catalog.service`. Construction performs no
document reads or scans. It accepts no monolithic Core, Runtime or Ledger object.

The compatible monolithic catalogue/projection functions delegate to Core.
Workplace maintenance, session search-status projection and ResourceSearch
composition use the concrete catalogue directly. Project-snapshot authorization,
freshness guards, query/error order and physical SQLite ownership are retained.
`LegacyResourceSearchReadAdapter` still supplies the separate legacy
`project_context_check_result` dependency; catalogue extraction does not make the
whole ResourceSearch service or the remaining monolith independent of legacy.
The reader and shared projection remain provisional internal interfaces.

`project.snapshot_sources.ProjectSnapshotSourcesReader` owns the ordered live
source fingerprints consumed by project snapshot assembly and freshness checks.
It uses concrete project metadata, document and raw-byte digest readers. The
related manifest reference operations belong to `ProjectMetadataReader`.
`process_catalog.official_read.OfficialProcessPackReader` owns the existing
list-only active official-pack selection and reuses the single manifest
traversal. Snapshot sources, the Workplace catalogue and Runtime process
resolution use this owner; scalar normalization in other catalog rules remains
unchanged. Their constructors perform no filesystem reads or scans.

The eight compatible monolithic source/reference/pack helpers delegate to Core.
The two actual snapshot collection sites and Runtime active-pack consumer use
the concrete readers directly. These readers accept no monolithic Core or
transport callbacks. Overall snapshot assembly, freshness policy/readiness and
other Runtime bindings still have legacy dependencies; this bounded extraction
does not complete those services or any OOP epic. The new readers are provisional
internal interfaces and preserve existing record formats, errors and live reads.

## Project readiness rules

`project.readiness.ProjectContextReadinessPolicy` owns the existing execution and
resource readiness algorithms. Snapshot assembly calls its `execution` and
`resources` methods directly. The default instance has no I/O or retained request
state and can be imported without the CLI or Runtime. Ordered blockers, capability
deduplication, errors and shallow conflict values keep their existing semantics.

The full freshness checker, classification and resource resolution, snapshot
assembly and publication still have legacy responsibilities and callbacks. This
bounded migration does not complete those owners or any OOP epic.


`project.source_check.ProjectSnapshotSourceCheckService` owns the existing
comparison of recorded fingerprints with current source bytes. The freshness
checker calls it directly at the former inline comparison site. It reuses the
concrete `ProjectSnapshotSourcesReader`; construction performs no I/O, and each
comparison reads current sources after recorded normalization. Ordered reasons,
duplicate handling, package exclusions and native errors are preserved. Snapshot
assembly retains its separate source read. Full checker orchestration and policy,
classification discovery, resource resolution, snapshot assembly and publication
keep their existing legacy bindings.


`project.resolved_comparison.ProjectSnapshotResolvedComparison` owns the existing
classification and resolved-resource comparison of two supplied snapshots. It
uses the concrete stateless `resources.versioning.ResourceVersionPolicy`, which
also owns the shared numeric/lexical version algorithm used by selection,
constraints and update candidates. All known callers use these owners; obsolete
internal key/index/version helpers are removed. Construction performs no I/O,
and comparisons retain ordering, duplicates, warnings and native failures.
Collection, full checker status/policy, snapshot assembly and publication remain
with their existing owners and legacy bindings.


`project.context_sources.ProjectContextSourcesReader` owns the existing broad
context source records and ordered live inventory. Context resolution/compilation
and the existing startup smoke use it directly; the two obsolete internal source
helpers are removed. It reuses concrete project metadata, YAML, digest and path
owners, with no constructor I/O or retained parsed documents. Root AGENTS preference,
PF fallback, optional records, first-resolved-path deduplication, ordering, live
checksums and native failures are preserved. Full checker, snapshot assembly
and publication retain their existing owners.


The same reader owns the existing `fingerprints` and `texts` projections.
Context payload assembly uses one operation-local reader for inventory and both
views; the two obsolete projection helpers are removed. Ordered keys, duplicate
replacement, original string conversions, UTF-8 replacement and native error
precedence are preserved. Text files are read live after inventory fingerprints;
the reader retains neither inputs nor results and adds no atomic snapshot claim.

`project.context_rules.ProjectContextRules` owns the existing text-list parsing,
allowed/forbidden action aggregation and conflict-report rendering. Capability
readers, snapshot construction and broad context assembly call it directly;
the three obsolete internal helpers are removed. The owner performs no I/O and
retains no inputs or results. Text matching, defaults, ordering, native failures
and report bytes keep their existing behavior. Full context orchestration,
freshness and publication retain their existing owners.

`documents.answers.AnswersDocumentReader` owns the existing strict answers read:
missing-file and secret-value refusals, strict UTF-8 decoding, mapping-only YAML
results and the existing `ModuleNotFoundError` fallback through Core's simple
parser. All answers consumers, including project initialization, use it directly;
the old internal loader is removed. CLI secret checks and redaction reuse the
same pattern definitions. This reader keeps its distinct error behavior rather
than using the tolerant `YamlDocumentReader` policy.

`project.capability_registry.CapabilityRegistryReader` owns capability values
and the ordered provider map from workplace and project tools/MCP registries.
All value and provider-map consumers call it directly; the two old helpers are
removed. Its concrete default uses `AnswersDocumentReader` and
`ProjectMetadataReader`, with no CLI dependency or construction-time I/O.
Workplace-before-project reads, overwrite and insertion order, status filtering,
string conversions and the narrow `SystemExit` skip remain unchanged. Every read
returns current data without retaining documents or results. Availability still
does not grant permission to execute a provider.

## Project context policy and resource selection

`project.context_policy.ProjectContextPolicy` owns the existing nested override
merge, context defaults and freshness action mapping. Project initialization,
snapshot assembly and freshness checks call the owner directly. The existing
coordination defaults, override order, shallow value sharing and action fallbacks
remain unchanged.

`project.resource_snapshot.ResourceSnapshotRules` owns resource versioning and
retention values, declared version and generation, fingerprints, instance ids,
resolved resource projections, indexing defaults and aggregate reproducibility.
It preserves the original field order, fallback values, native errors and the
distinction between borrowed values and copied metadata. It performs no I/O.

`project.knowledge_selection.KnowledgeResourceSelector` owns context requirement
projection, version constraints and prefixes, inferred platform versions, legacy
requirements and explicit resource selection. Its default composition uses
per-instance concrete `ResourceVersionPolicy` and `ResourceSnapshotRules` owners.
Construction performs no I/O; no request documents or results are retained.
The CLI and existing narrowing/search smoke call these owners directly; the
17 internal helpers and two resource policy sets have moved out of the CLI.

These are provisional internal Core interfaces. Full context/snapshot assembly,
freshness state collection and publication still retain legacy responsibilities.
This bounded source migration does not complete any OOP epic or qualify archive,
installed Core, Runtime, connected hosts or performance.

## Project context snapshot presentation

`project.snapshot_rendering.ProjectContextSnapshotRenderer` owns the existing
Markdown presentation of a project context snapshot. Snapshot publication and
the existing agent-start smoke call its `render` method directly; the old
internal renderer is removed. The stateless owner preserves section and item
order, defaults, Unicode, trailing newline, native malformed-input errors and
input nonmutation. It performs no document reads and retains no inputs or results.

Snapshot assembly, freshness decisions and durable publication keep their
existing responsibilities. This presentation move does not make those paths
independent of the legacy composition or complete any OOP epic.

## Parameter Merge

`configuration.parameters.ParameterMergePolicy` owns the existing recursive map
merge, ID-list merge, deletion and replacement rules with ordered provenance.
Its instance method is `merge_maps(base, override, source_id, path="", provenance=None)`.
The owner retains no per-merge state, performs no I/O and has no dependency on
the CLI or Host. Deep copies, mutation of supplied provenance, native errors,
iteration order and existing duplicate-ID behavior remain unchanged. Five old
parameter helper definitions have been removed from `tools/processforge.py`.

The two direct consumers import from the owning module: `add_parameter_source`
in `tools/processforge.py` uses the policy for each source merge and passes the
existing provenance object; `work.context.build_context_fields` uses it for
the immutable assignment parameter merge.

`build_context_fields` still calls `core.add_parameter_source` and
`core.parameter_payload` for the process/stage/task source cascade. Assignment
normalization, snapshot paths/checksums, project/workplace resolution, source
capture and coordination also retain existing legacy dependencies. Extracting
the merge policy does not make the complete context compiler independent of
the monolith. This ownership reference describes source code; archive,
installed-Core, Runtime and connected-host acceptance remain separate.

## Classifier matching and process artifact declarations

`project.classification.ProjectClassifierRulePolicy` owns the existing rule
algorithm through its ordinary instance method `matches(rule, available_paths)`;
condition matching is private. Both `inactive_official_classifier_hints` and
`classify_project` in `tools/processforge.py` call this owner directly. A list-valued
`when.all` takes precedence even when empty (which returns false); nonempty `all`
and `any` retain short-circuit evaluation. Existing shape checks and nonblank
`exists` string handling are unchanged.

`common.paths.path_matches_pattern` is the shared primitive used by this policy,
`ProjectDetectionService.group_matches` and `matches`. It preserves backslash
normalization and standard-library `fnmatch.fnmatch` checks on the full path then
its `Path(...).name`, including platform-dependent matching. `rel` is unchanged.
The two old classifier definitions and the old matcher definition are removed
from the monolith; consumers import the owning Core modules explicitly.

`process_catalog.artifacts.ProcessArtifactDeclarationPolicy` owns the ordinary
instance methods `defined_ids(process)`, `declared_ids(process)` and
`produced_ids(process)`. Core authoring/contract validators and builtin catalog
reporting call the owner directly;
the three old artifact-ID definitions are removed. Shared `common.values` helpers
preserve list-only handling, string-list conversion/filter order, comma-separated
strings, dict/list distinctions, ID truthiness, duplicate handling and native
exception order. Remaining monolith consumers import canonical shared primitives;
the two temporally distinct monolith `as_list` definitions remain in place.

Both policies are stateless, perform no I/O and have no monolith callback or
import. Classifier registry loading, tree walking and activation remain in the
legacy CLI paths. Process contract checks and companion inspection belong to
ProcessContractValidationService. Authoring transactions, catalog registration
and activation retain their existing legacy owners. These
pure policy extractions do not fully migrate classification or validation,
complete any OOP epic, or establish archive, installed-Core, Runtime or
connected-host acceptance.

## Process authoring, evolution, driver documents and update sites

`process_catalog.authoring.ProcessAuthoringDefinitionBuilder` owns `defaults`,
`normalize`, `build`, `normalize_transitions` and
`materialize_responsibility_boundaries`. Its normal constructor uses the concrete
`process_catalog.evolution.ProcessEvolutionPolicy`, whose methods are
`default_block`, `normalize_block` and `validate_block`. Both preserve fresh
defaults, the existing shallow sharing and deep-copy locations, unknown fields,
disabled handling and ordered checks. Transition routes retain their shared
return mapping. Full authoring/schema validation and durable publication retain
their legacy responsibilities.

`runtime.drivers.RuntimeDriverDefinitionPolicy` owns `default_documents`,
`default_registry`, `placeholder_errors`, `parse_limits`, `start_readiness` and
`validate`, together with the existing reserved environment keys and placeholders.
Document readiness performs no executable probing. Defaults remain fresh on each
call; validation messages, ordering, native errors and existing argument
normalization are preserved. Runtime process execution, registry I/O and worker
lifecycle retain their existing owners.

`maintenance.sites.UpdateSitePolicy` owns `location`, `source_kind`, `source_id`,
`stable_key`, `record` and `policy`. It retains ordered source-key lists, raw
nonblank IDs, override precedence, shallow policy mutation and borrowed channel,
parent and local-data values. It uses `common.paths.rel` and performs no I/O.
Update discovery, schema validation, network access, installation and recovery
remain with their existing owners.

Shared primitives have one canonical owner: `common.checks.Check` remains a
mutable dataclass and `check` uppercases its level; `common.ids` owns `safe_id`
and `title_from_id`; `common.values` owns strict-list `as_list` and the existing
`string_list` conversion. All known consumers use the concrete owners or these
imports. The obsolete internal definitions are removed without wrappers.
These moves preserve external 1.2.0 contracts and establish bounded source-only
evidence; they do not complete the OOP epics or qualify other delivery layers.

## Presentation, live driver catalog and candidate selection

`ProcessAuthoringDefinitionBuilder.from_definition` owns the existing reverse
projection from a process definition to authoring answers. Earlier builder
methods are unchanged. `process_catalog.presentation.ProcessAuthoringRenderer`
owns `questions`, `logic_review`, `agent_prompt` and `document`, preserving
rendered bytes and evaluation order. The small canonical function
`process_catalog.coordination.process_coordination_requirements` and its mode
set are shared with the remaining monolith consumers.

`runtime.catalog.RuntimeDriverCatalogReader(distribution_root)` uses concrete
`YamlDocumentReader`, `ProjectMetadataReader` and `RuntimeDriverDefinitionPolicy`.
It owns registry paths/entries, entry paths, strict document loading, exact
registered lookup, reference resolution/classification/normalization and the
driver ID list. It preserves first-match lookup, ordered overwrites, direct-path
behavior, builtin fallback, unknown fields and native refusals. Construction
performs no I/O; operations read current files without retaining parsed documents.
The monolith and existing MCP registered-driver lookup call this owner. The MCP
adapter keeps its driver-ID guard before a lazy owning-module import, preserving
standalone bootstrap timing and bound project/workplace values.

`evolution.candidates.KnowledgeCandidateTargetingPolicy` owns existing candidate
ID, target and destination projections, promotion/generalization readiness and
ordered targeting validation. It borrows the original nested mappings and uses
canonical checks, identifiers, string-list conversion and existing evolve target
types. The new responsibility package has a minimal initializer. Full candidate
sanitization, publication/export and lifecycle retain their existing owners.

`maintenance.versions.UpdateVersionSelectionPolicy` uses concrete
`ResourceVersionPolicy` and `UpdateSitePolicy` for existing latest lookup, both
manifest-version shapes, version selection and candidate IDs. Nested references,
subject sharing, stable sorting and warnings retain their earlier behavior.
`maintenance.presentation.UpdateAssessmentRenderer.render` owns the existing
assessment text. Fetching, update orchestration, installation and recovery remain
with their existing owners. These internal interfaces establish source ownership;
external commands, MCP schemas and delivery-layer acceptance retain their existing
contracts.

## Work fields, coordination, shared privacy and source contracts

The existing `work.context_documents.ContextContractInputs` owns eight additional
existing operations: assignment path keys, write-scope projection, glob and
overlap flags, dependency sets, required-source file observations, capsule
coordination and path/scope matching. Its original fields, frozen constructor and
20 earlier methods are unchanged. Existing normalization methods are reused;
two obsolete monolith wrappers are removed. The context compiler calls capsule
coordination directly at the former projection site. Scope decisions retain
platform behavior and empty-scope handling; access, admission, lifecycle and the
remaining compiler dependencies retain their existing owners.

`project.coordination.ProjectCoordinationReader` owns the existing project and
workplace defaults, mode normalization and configuration reads. Its concrete
YAML reader and project metadata reader preserve live observations, shallow
director merges, unknown fields, fresh defaults and refusal order. The reader
retains no project, Work or parsed configuration. Effective coordination assembly
and Director operations remain legacy responsibilities.

`common.privacy` owns `BACKSLASH`, `LOCAL_PATH_PATTERNS`, `SECRET_VALUE_PATTERNS`,
`is_public_path_safe` and `contains_secret_value`. `AnswersDocumentReader` uses
the canonical data with its original class algorithm. `evolution.privacy.EvolvePrivacyPolicy`
owns `findings`, `text` and `value`, preserving regex patterns/flags, redactions,
recursive behavior, dictionary keys, tuple identity and native errors. Host uses
the canonical secret predicate after the existing automatic-content filters;
short-circuit order, bootstrap timing and all authentication/provenance/hash
guards are preserved.

`maintenance.source_contracts.UpdateSourceContractPolicy` owns existing HTTPS
defaults, remote/artifact URL shapes, env-reference and source checks, registry
validation and source sorting. It preserves mutation of the supplied check list,
type/truthiness distinctions, native errors and check order. Schema-based override
and full normalized-manifest validation continue to call these shared helpers
from their legacy owners. No scanner, trust, authorization or update rule is added.
These internal moves preserve module annotation semantics and external 1.2.0
contracts; evidence remains limited to the qualified source slice.

## Output declarations, platform detection, worker environment and schema checks

`work.outputs.WorkOutputPolicy` owns `waivers`, `path`, `task_path`,
`expected_report` and `default_report`. It uses existing `ContextContractInputs`
for normalization and preserves traversal/drive/absolute-path checks before
resolution, containment, native failures and existing defaults. Required-output
normalization calls the existing Core owner directly. The same policy owns
required-output `checks` and verification `fingerprint`; lifecycle remains with
the application service. Host and existing consumers call the policy at their
former guard positions. Optional application dependencies are described below.

`project.detection.ProjectDetectionService` owns `files`, `group_matches` and
`matches`, using canonical `common.paths` and `common.values.list_value`.
Generic inventory retains its existing ignored-component policy and remains
distinct from classifier inventory pruning. Detection preserves file ordering,
read limits, invalid-regex fallback and current filesystem observations; no
parsed or metadata-only cache is introduced. Classifier loading/activation remain
legacy responsibilities.

`runtime.environment.WorkerEnvironmentPolicy` owns `minimal`, `build`,
`materialize` and `expand`, reusing reserved keys from `runtime.drivers`.
Persisted command data contains only existing PF-owned and explicit values;
inherited host environment is materialized at launch. Placeholder recursion,
coercion, reserved-key refusal and native errors retain their original behavior.
Process creation, attempt state, collection and recovery retain their owners.

`maintenance.schema_checks.UpdateSchemaChecks(distribution_root)` owns
`type_matches`, `resolve_ref`, `validate`, `append` and `require`. This is the
existing JSON Schema subset, including its ordered diagnostics and exceptions.
Construction performs no I/O; schema files are read afresh for each check.
Update orchestration, network, installation and recovery remain with their
existing owners. These moves qualify source behavior only; archive, installed,
Runtime and connected-host acceptance remain separate.

## Work locations, worker commands and live catalogs

`work.paths.WorkPaths` owns Run and Assignment document paths, task artifacts,
summaries, handoffs, worker prompts and ordered attempt paths. Run directory and
handoff normalization preserve valid generated IDs with repeated hyphens;
assignment and agent/task locations retain their separate `safe_id` behavior.
The strict assignment-path validation in `ContextContractInputs` remains distinct.
Concrete `ProjectMetadataReader` supplies the flow root without constructor I/O.

`runtime.command.WorkerCommandBuilder(distribution_root)` owns `sandbox` and
`build`, composing existing Work paths, output rules, environment, driver limits
and context normalizers. Output preflight precedes variables and environment;
placeholder expansion, model arguments, prepared wrapper, path resolution and
command fields preserve their earlier ordering and behavior. Existing consumers
use canonical owners. The terminal-admission test spies on the relocated builder
and retains its original assertions. Process launch, locks, durable attempt
state, collection and recovery retain their existing owners.

`project.platforms.PlatformContractReader(distribution_root)` owns ID projection,
registry lookup, seed/project paths, record loading, overlay index and lookup
fallback. It reuses concrete Core YAML and `WorkspacePathReferenceReader` rather
than copying registry/path algorithms. Seed, project and workplace overlays,
aliases, duplicates, unknown fields, disabled/missing records and borrowed values
preserve their existing behavior. Operations read current files without caching.

`maintenance.documents.UpdateDocumentReader(distribution_root)` owns update
registry locations, soft YAML reads, doctor YAML/schema checks, manifest candidate
paths, registry path lists, update index, local file URLs and YAML/JSON document
and text reading. It reuses existing YAML, workspace-path and schema owners.
Soft update YAML filters parse errors; index reading retains its earlier error
sentinel behavior; doctor checks may append schema errors and still return the
parsed mapping. Construction performs no I/O. Network fetch, effects and update
lifecycle remain legacy responsibilities. Egress and prepared-input consumers
use canonical Work paths but retain their other unmoved dependencies. This is
bounded source ownership, with later delivery layers and OOP epics still separate.

## Output readiness, driver selection and validation

`WorkOutputPolicy.checks` and `fingerprint` preserve optional-output skipping,
waivers, missing/pending/invalid distinctions, live file observations and exact
JSON/hash encoding. Earlier fields, constructor and path methods are unchanged.
`ProcessExecutionService` receives independent optional keyword-only callables
`output_checks` and `verification_fingerprint`, with canonical Core methods by
default and explicit `None` for unavailability. Frozen/repr/compare behavior and
the three positional constructor arguments remain intact. Existing automation
projectors retain their guards, reasons and exception identity; unused
capabilities remain lazy. Event/journal dependencies retain their earlier wiring.

`runtime.selection.RuntimeDriverSelectionService(distribution_root)` owns
`for_task` and `for_worker_state`, preserving saved command reads, direct-path
copies, fallback and validation/error order. The existing
`ProjectMetadataReader.workplace_manifest()` owns the local-only workplace
manifest lookup with project identity bound in the reader. It remains distinct
from broader automatic workplace resolution. `common.json_io.json_read` owns
the existing primitive, including raw JSON types and native parse/read failures.

`project.platform_policy.PlatformContractPolicy(catalog)` receives a concrete
`PlatformContractReader` for canonical IDs. It owns reference normalization,
extends/requires and required/recommended/optional resource projections, retaining
type/truthiness distinctions, sorting, deduplication and existing includes rules.
Hierarchy resolution and project package catalogs use the concrete owners below.

`process_catalog.validation.ProcessAuthoringValidationService` owns `logic`,
`files` and `paths`, using existing evolution/artifact policies and canonical
workflow/iteration constants. Guard/check order, nested ID validation, warnings,
companion-root handling and file observations are unchanged. The shared
`common.privacy.public_yaml_has_private_path` retains its original serialization
and predicate. Full process-contract checks use the concrete owner below. Route-map validation,
publication and recovery remain with their existing owners. These are internal source interfaces; external
1.2.0 contracts and later delivery-layer acceptance remain separate.

## Project packages, platform hierarchy, process semantics and worker plans

`resources.project_packages.ProjectPackageCatalogReader(distribution_root)` owns
`workplace_roots`, `workplace_root_paths`, `candidates`, `index`, `dependencies`
and `root_from_entry`. Project and workplace arguments remain explicit per call.
Current candidates retain discovery order, resolved-path deduplication and active
official-pack additions. Project indexes preserve last-wins and the duplicate
sentinel; the existing workplace search catalog keeps its separate first-wins
contract. There is no parsed-document cache or constructor I/O.

The moved `PackageRootResolution` keeps its existing class name, fields,
annotations, defaults and representation. Its root-entry operation uses the
existing `WorkspacePathReferenceReader` algorithm, then explicitly maps the
plain record fields while retaining warnings/entry aliases. The existing private
snapshot record and its consumers are unchanged; path rules are not duplicated.

`project.platform_resolution.PlatformContractResolver(distribution_root)` owns
the existing recursive `resolve` and `merge_ids` operations. It uses concrete
platform catalog/projection/package owners, preserving cycle and traversal order,
extends versus required-platform resource inclusion, override aliases, conflict
order, sorted outputs and package dependency FIFO. `common.values.parameter_payload`
is the shared primitive that returns the original parameter mapping. Existing
Work context assembly uses it directly; its other dependencies remain unmoved.

`process_catalog.semantics.ProcessSemanticPolicy` owns authoring coverage,
semantic-map and process projections, sorted strings/events/objects, and ordered
comparison. `presentation.process_parity.ProcessParityRenderer` owns the existing
`import_report` and `parity_report` Markdown. Their strings, warning/failure
precedence and source-field distinctions retain the prior contract.

`runtime.worker_plans.WorkerPlanPolicy` owns default plans, worker/subagent and
dependency projections, recursive reachability, literal overlap policy and
`task_dependencies_done`. The last operation uses current Work paths and strict
YAML reads. Execution, scope/lease checks, locks, lifecycle and recovery retain
their existing owners. These are internal source responsibilities; external
1.2.0 behavior and later delivery-layer acceptance remain separate.

## Package roots, platform selection, update registries and process contracts

`ProjectPackageCatalogReader` also owns root registry reads, root/path resolution,
manifest discovery and manifest loading through the existing concrete
`WorkspacePathReferenceReader`. The canonical algorithms are reused, with the
public root record retained through one explicit field converter. Existing
private snapshot records and their callers remain unchanged. Prior package
catalog behavior and constructor/field contracts are retained.

`project.platform_selection.ProjectPlatformSelectionService(distribution_root)`
owns existing selected/derived platform decisions, project/parent type hints,
current detection, registry findings, binding matching and forbidden-base rules.
It uses concrete readers and operation-local project/workplace arguments.
`AnswersDocumentReader.strings` owns the recursive answer flattener;
`PlatformContractReader.normalize_id_pair` owns the existing two-ID projection.
Hint normalization/matching live in `project.classification`; `common.values.registry_ids`
is the shared literal registry projection. All previous owner methods and data
remain unchanged. No MCP resource use is introduced by reading existing registry metadata.

`YamlDocumentReader.policy(name, root=None, *, distribution_root)` owns the earlier
policy document lookup. The explicit required keyword replaces the old module
ROOT without capturing a dummy project or changing the constructor. File guards,
soft YAML errors and returned values are unchanged; all callers supply the actual
distribution root. Other document reads retain their earlier behavior.

`maintenance.registries.UpdateRegistryReader(distribution_root)` owns entity
manifest records, overrides, installed subject lookup and install-target selection.
`UpdateDocumentReader` also owns runtime/candidates/notifications locations.
Discovery and override priority, installed-record aliases, package-only dedup and
install override/current-record/fallback precedence remain intact. These operations
read/resolve only; installation, timestamped version writes and update lifecycle
retain their previous owners.

`process_catalog.contracts.ProcessContractValidationService(distribution_root)`
owns the existing full process contract checks, with concrete metadata,
evolution, artifact, authoring and route-document owners. `ProcessRouteDocumentReader`
owns route location and soft document reading. The actual metadata function and
stable predicate live in `process_catalog.service`; shared handoff modes belong
to `contracts`. Guard/check/refusal and filesystem-observation order, strict/stable
severity, unknowns, companion/template precedence and route defaults remain unchanged.
Route-map validation, handoff execution, authoring callbacks/transactions, lifecycle,
locks, recovery and later delivery-layer qualification remain separate work.

## Worker plan checks, record validation and route/handoff readers

`runtime.worker_validation.WorkerPlanValidationService(distribution_root)` owns
the existing plan checks, extension-key filtering and subagent report checks.
It composes current ContextContractInputs, RuntimeDriverCatalogReader,
WorkerPlanPolicy and ScopeConflictService with actual operation-local project
roots. Literal type tests, repeated driver reads, dependency exemptions, scope
conflicts and recursive current report observations retain their earlier order.
The four plan field sets belong to that module. WORKSPACE_ACCESS_KEYS and both
normalizers use existing work.context_documents definitions directly; the old
Main wrappers/duplicate tuple are removed, including three other Core callers.

`project.hooks.HookConfigurationReader` owns hooks.yaml location and its existing
ordered shape checks. `common.record_validation.RecordValidationPolicy` owns
event/chat required fields, the existing event-type expression and the shared
secret check. JSON serialization and its native failures remain unchanged.
Hook dispatch, journals and effects retain their existing owners.

`process_catalog.routes.ProcessRouteService(distribution_root)` owns current
route lookup, validation and required-role projection. It reuses the existing
route reader, shared modes and schema checker. `process_catalog.handoffs.HandoffDocumentReader`
owns handoff directory/path/soft read with real project metadata and document
owners. First matches, borrowed mappings, schema/check order and not-found
refusals remain intact. Handoff writes and execution, leases, continuation,
workflow transactions and recovery retain their existing owners.

`maintenance.validation.UpdateDocumentValidationService(distribution_root)` owns
the existing overrides and normalized manifest checks with concrete schema and
source-contract policies. The SHA-256 expression is unchanged. UpdateRegistryReader
also owns the distinct installed-version projection; UpdateDocumentReader also
owns staged-record location/soft reading. Existing reader constructors and
previous methods are unchanged. Discovery, writes, installation, artifact I/O,
network and timestamp generation retain their earlier owners.

## Platform document building, registry checks and catalog audit

`project.platform_documents.PlatformDocumentBuilder` owns the existing platform
document path/byte/note list construction. It preserves every YAML and Markdown
literal, output order and native lookup failure; it returns data without writing
files. Platform authoring publication retains its owner; semantic validation now uses
PlatformContractValidationService as described below.

`project.registry_checks.WorkplaceRegistryValidationService(distribution_root)`
owns current registry path checks and package-root checks through the existing
WorkspacePathReferenceReader, ContextContractInputs and ProjectPackageCatalogReader.
Actual workplace roots are operation-local. Alias/default/status/writable rules,
duplicates, current filesystem observations and warning/check order are unchanged.
`common.yaml_dump` owns the exact existing format_scalar and recursive dump_yaml;
all actual Main/Runtime/process-execution formatter consumers use that owner.
The zero-argument yaml_formatter provider and one-argument formatting callbacks
retain their earlier shapes. No serializer replacement or Runtime start is added.
`common.text` owns the original ensure_trailing_newline and check_with_hint
functions. Capsule publication composition calls the canonical newline and YAML
formatters from the same one-argument callbacks; the other legacy dependencies stay with
their existing owners. No publication or failure timing is changed.

`process_catalog.audit.BuiltinProcessCatalogAuditService(distribution_root)` owns
the ordered builtin catalog report using a per-operation concrete catalog reader,
contract/authoring/artifact policies and canonical metadata functions. The flat
sorted root/packages/*.yaml index remains distinct from the broader project
package index. Public internal skips, official companion roots, counts, repeated
observations and warning concatenation retain their earlier semantics.
The pure process_catalog_contexts projection lives in existing service.py;
all its prior definitions/data remain unchanged.

`project.setup.WorkplaceSetupProposalBuilder` owns the existing setup proposal
mapping and Markdown using ProjectCoordinationReader. Defaults, literal path
placeholders, list coercions, borrowed fields, ordering and invalid-mode refusals
are preserved. Constructors perform no I/O; actual setup writes, authoring transactions, locks, recovery and later delivery
layers retain their owners. Registry upsert now belongs to WorkplaceRegistryWriter.

## Registry writes, template lookup and platform validation

`project.registry_write.WorkplaceRegistryWriter(distribution_root)` owns the
existing registry upsert. It retains schema mapping/validation and original
refusals, UUID staging beside the destination, os.replace and finally cleanup.
No locking, retry or new atomic-write behavior is added. The shared upsert_resource
primitive lives in existing common.values, whose prior implementation is intact.

`project.templates.TemplateCatalogService(distribution_root)` owns existing
template-root selection and manifest lookup. It reuses WorkspacePathReferenceReader
and WorkplaceRegistryWriter. Read mode stays read-only; write mode preserves the
fallback registry upsert before selected-ID validation and the original mkdir
ordering. Candidate-first lookup, first registry match and original path behavior
remain unchanged; no new containment or template policy is introduced.

`project.platform_validation.PlatformContractValidationService(distribution_root)`
owns the complete existing semantic platform checks through concrete contract,
resolution, selection, package and template owners. Check/message order, repeated
live reads, required/recommended resources, cycles and falsey resolution fallback
are preserved. Pure policy_entries/policy_id_matches live in common.policies;
other Main consumers use those same shared functions.

`project.requirements.PlatformDependencyPreflightService(distribution_root)` owns
the original dependency preflight and direct workplace registry-ID reads. Missing
resource order, duplicates, tool/MCP reads and native refusals remain unchanged.
Constructors perform no I/O or retain project documents. All actual callers use
these owners in the same source slice; authoring publication/transactions and
unselected recovery paths remain with their earlier owners. This source refactor
does not complete the OOP epics or archive/install/Runtime/connected-host gates.
