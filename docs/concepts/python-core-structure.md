# Python Core Structure

The core is evolving incrementally. `tools/processforge.py` is still the active legacy facade, not retired code. Existing CLI, MCP, hook entrypoints and bootstrap aliases remain unchanged.

## Package Placement

New implementation modules belong to a cohesive responsibility package, following
[the Core placement rule](../../src/processforge_core/AGENTS.md). Packages use short
lowercase names, modules use `snake_case.py`, and classes use `CapWords`; a module
may contain a service, its errors and related helpers. There is no class-per-file
requirement. Keep the package tree shallow and package initializers minimal.

The existing Work modules now live in `processforge_core.work`: `context`,
`context_read`, `inventory`, `records`, `resources`, `resource_material`,
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

| Module | Responsibility |
| --- | --- |
| `src/processforge_core/agent_entry/` | Entry contract, profiles, client adapters, start prompt and guarded instruction placement/recovery. |
| `src/processforge_core/completion/` | Run completion policy, summary/index documents and durable completion intent construction, reading, validation and replay. |
| `src/processforge_core/evidence/` | Existing evidence collection/identity, normalization and live file diagnostics, requirement/gate satisfaction and ordered readiness blockers through explicit callbacks. |
| `src/processforge_core/garage.py` | Existing current Work and remaining legacy helpers; project context assembly and reconciliation live under `project/`. |
| `src/processforge_core/work/projection.py` | Existing pure Work projection/classification rules, without Core or lifecycle authority. |
| `src/processforge_core/work/bootstrap.py` | Existing guidance/start delegation through explicit summary and deferred typed start dependencies. |
| `src/processforge_core/work/creation_scope.py` | Existing scope validation/overlay with explicit deferred dependencies, without lifecycle authority. |
| `src/processforge_core/work/start_documents.py` | Existing pure Run/Assignment construction, preserving fields and references. |
| `src/processforge_core/work/start_publication.py` | Existing ordered post-capsule start publication through deferred operation dependencies. |
| `src/processforge_core/work/continuation_read.py` | Existing bounded control-document reads and Continuation/selection paths with explicit live dependencies. |
| `src/processforge_core/work/continuation_contract.py` | Existing record version and binding validation with an explicit error provider. |
| `src/processforge_core/work/continuation_status.py` | Existing live waiting/status/selected reads with explicit dependencies. |
| `src/processforge_core/work/continuation_work.py` | Existing exact Continuation Work binding reads and executable/cancellation validation with narrow dependencies. |
| `src/processforge_core/work/resource_context.py` | Existing pinned Work resource context reads with explicit dependencies. |
| `src/processforge_core/work/resource_declarations.py` | Existing identifier, indexing-declaration, allowlist overlay and portable-reference rules shared with prepared inputs. |
| `src/processforge_core/work/resource_bindings.py` | Existing initial bounded material binding assembly and per-resource failure records for capsule creation. |
| `src/processforge_core/work/permissions.py` | Shared pure Work permission readiness. |
| `src/processforge_core/project/reconciliation.py` | Existing context reconciliation projection through the required deferred typed context checker, without Core. |
| `src/processforge_core/project/context.py` | Existing five ProjectContextService operations and context-specific per-dispatch readers through required typed dependencies, without Core. |
| `src/processforge_core/process_execution.py`, `work/continuation.py` | Governed lifecycle, selection, pinned execution, evidence and completion/recovery. |
| `src/processforge_core/work/state.py` | I/O-free completion requirements and Work-state action/blocker policy; not lifecycle authority. |
| `src/processforge_core/work/automation_readiness.py`, `work/transition_rejection.py` | Existing automation readiness projections, live assignment-event reads and recoverable transition rejection response rules through explicit callbacks. |
| `src/processforge_core/work/boundary_advisory.py` | Existing Work boundary advisory and fresh-session completed-boundary reads with their distinct route/handoff rules and explicit read dependencies. |
| `src/processforge_core/documents/reader.py`, `work/inventory.py` | YAML reading and live sorted discovery; no shared mutable document cache. |
| `src/processforge_core/work/records.py` | Live raw Run/Assignment reader; selection and recovery remain in the application service. |
| `src/processforge_core/work/publication.py` | Existing atomic Work text/YAML publication through explicit deferred formatter/writer dependencies. |
| `src/processforge_core/work/events.py` | Existing Work event envelope and subsequent diagnostics through a typed, dynamically resolved emitter. |
| `src/processforge_core/work/context_read.py` | Existing capsule validation and assignment normalization with explicit path/validator callbacks. |
| `src/processforge_core/process_catalog/` | Catalog models/resolution, effective ProcessDefinition reads, offered process selection and pin construction through explicit callbacks. |
| `src/processforge_core/process_catalog/summary.py` | Existing allowed-process context summary with an optional typed definition resolver, without Core. |
| `src/processforge_core/project/snapshot.py` | Live ProjectContextSnapshot loading and raw-byte checksum through explicit path/loader/hash callbacks. |
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
| `src/processforge_core/composition.py` | Explicit service factories and narrow legacy read/context/definition adapters. |
| `src/processforge_core/bootstrap.py` | Existing runtime module assembly and lazy access to the service factories. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade and transport/host/provider adapters. |

`build_current_work_service(project_root, port)` accepts any structurally compatible read dependency and constructs the existing service without importing the CLI or doing I/O. `RuntimeBootstrap.current_work_service(project_root)` uses the already-loaded legacy core through `LegacyWorkReadAdapter`. No service locator, global service cache or DI container is introduced.

The existing `CurrentWorkService(project_root, core)` constructor and module path are preserved. Its discovery order, missing-assignment fallback, bootstrap-placeholder handling, summary shape and error behavior are unchanged. Existing consumers need not migrate immediately.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None, snapshots=None)` is shared by CLI, MCP and Host/Daemon. `RuntimeBootstrap.process_execution_service(...)` delegates to it. Construction does not load the CLI, resolve a project, read configuration or perform I/O. The three-argument `ProcessExecutionService` constructor remains compatible; optional dependencies are keyword-only and excluded from equality/repr. Remaining legacy dependencies are explicit, not replaced by a universal Core interface.

`WorkRecordReadPort` exposes `runs`, `load_run` and `load_assignment`. The factory defaults to `YamlWorkRecordReader`, which uses the existing `WorkInventory` and YAML loader. Roots and records are read live; no cross-request result cache is added. Direct legacy construction retains its inventory and private-path fallback, including subclass overrides. Raw readers neither choose Work nor hide duplicate/alias discovery or pending recovery.

`WorkContextReadPort` exposes `validation` and `normalized_assignment`. The default is assembled lazily through `build_work_context_read_service`, using the caller's private path callbacks and the narrow `LegacyWorkContextAdapter`. `WorkContextReadService` does not depend on the monolithic core: its four dependencies resolve paths, validate contracts and normalize assignments. Existing `work/context.py` rules still own signed identity/intent, pins, scope and stage views. Byte limits, symlink/containment checks, raw checksum, safe parsing and original error order remain intact. Default assembly captures no document/root/logger; validation and normalization return live results.

`ProcessDefinitionReadPort` exposes `effective_process(run)`. `ProcessDefinitionReadService` receives the legacy definition resolver and existing fingerprint function. By default, `_effective_process` delegates lazily through `build_process_definition_read_service` and the narrow `LegacyProcessDefinitionAdapter`. Valid and corrupt pins do not consult the catalog; legacy definitions are resolved live on each call. Returned copies preserve unknown fields. The existing `pinned`, `corrupt`, `legacy_unpinned`, `missing` statuses and exception boundaries remain unchanged. The reader does not select a process, create pins or authorize transitions; catalog resolution and other legacy dependencies remain.

`ProjectSnapshotReadPort` exposes `load(path=None)` and `checksum(path)`. The default `ProjectSnapshotReadService` is assembled lazily through `build_project_snapshot_read_service` and `LegacyProjectSnapshotAdapter`, preserving the existing YAML loader and private `_flow_root`/`_sha256_file` overrides. Pin creation passes one captured path to loading and checksum; resource selection, start preflight and capsule capture load independently. A missing file produces an empty checksum; load/hash failures retain their original order. No new cache is introduced. Snapshot-generation checks remain in `work/context.py`; its validator compares pinned capsule metadata and does not gain a live snapshot-read dependency.

`ExecutionProjectReadService` belongs to `project/context_read.py`. Its required keyword-only dependencies are project/workplace paths, a typed context-check callable resolver, a document-loader resolver and a late flow-root callback. `build_execution_project_read_service` only assembles these dependencies; each `_context_check` or `_manifest` facade dispatch builds a fresh service without I/O or cached results. Context checking passes the workplace explicitly only when `workplace.yaml` exists; `ProjectContextService.check` retains its distinct always-explicit behavior. Manifest reading resolves the loader before the overridable `_flow_root` callback, preserving callable lookup, live reads and exception order. The coordinator retains its private operational methods, admission decisions, guards and lifecycle authority; no Core field or old module alias is introduced in the read service.

`ProcessExecutionService.state()` retains exact selection, context/pin checks, evidence/outcome validation and permission readiness. `WorkStatePolicy` separately computes completion requirements and action/blockers from supplied records. It does not read files, alter records, choose caller identity or advance a process. Terminal, completed, blocked and incomplete precedence remains unchanged; permission readiness stays a separate response field.

`ProjectContextService` belongs to `project/context.py` and has no Core field. Its two project/workplace paths and required keyword-only snapshot/read dependencies describe the existing five operations. `build_project_context_service(project_root, workplace_root, core, *, snapshots=None)` retains its consumer-facing signature and performs no I/O; it builds the existing default reader only for `None`, preserving falsey injected readers. Snapshot paths, raw documents and errors remain live; no checksum is required for these reads. Context imports/captures its four mode/report/process-summary/boundary factories once at dispatch entry, before the freshness check, in a context-specific `ProjectContextReaders` value. The other helpers are resolved at their original use sites. `scoped_request`, always-explicit workplace checking, check-before-snapshot and broken-check suppression of the primary read remain unchanged. Mode/report fallback receives independent default readers, rather than the injected context port. Runtime resolution captures the current resolver before evaluating `self.snapshot()`. All context keys, resource values, call order and continuation recommendation mutation retain their form. MCP consumers still use the factory after ingress guards; no old Garage class/import alias, constructor compatibility, cache or authority is introduced.

`ResourceSearchService` requires a narrow `ResourceSearchReadPort` instead of the universal Core object and retains optional keyword-only `snapshots` injection. `LegacyResourceSearchReadAdapter` in composition owns the existing Core reads and preserves late callable lookup. An explicitly supplied empty snapshot still bypasses loading; a falsey injected reader retains its identity. The search freshness guard precedes reading, while blocked readiness retains its existing coverage read. `build_resource_search_service` keeps its released signature and assembles the existing MCP search consumer without I/O, after ingress guards. Project context retains its existing replaceable service binding and supplies the same read adapter. Index maintenance, query arguments, navigation, coverage, payloads and error boundaries retain their existing behavior.

`ResourceResolveService` requires `ResourceResolveReadPort` instead of the universal Core object and retains optional keyword-only `snapshots`. `LegacyResourceResolveReadAdapter` in composition binds the existing project-id, snapshot and path-reference operations without I/O at construction. ID reads remain first; an empty resource id returns project metadata without reading a snapshot. A falsey injected reader is retained, and default reads remain live. The path resolver is fetched before evaluating its reference argument. `build_resource_resolve_service` keeps its released signature and assembles both MCP and Host consumers; MCP binding/freshness guards and Host routing retain their order. Selection, aliases, denied results, raw resource fields, path resolution, private navigation, payloads and errors are unchanged. No compatible constructor or new authority is introduced.

`GarageModeService` belongs to `project/mode.py` and takes `(project_root, workplace_root, *, snapshots)` with a required `ProjectSnapshotReadPort`; it receives no Core. The dependency is excluded from repr/equality. Its existing `snapshot or ...` fallback is preserved: an empty supplied snapshot triggers `snapshots.load()`, while a nonempty one bypasses it. `build_garage_mode_service(project_root, workplace_root, core, *, snapshots=None)` performs no I/O and builds the existing default reader only when the dependency is `None`, preserving a falsey injected reader. Context does not forward its own optional reader into the mode fallback. Coordination, session representation, blockers and mode policy retain their behavior; a session alone does not promote Garage to Forge. No old constructor or module alias is retained.

`DerivedReportLifecycleService` and `DERIVED_REPORTS` belong to `project/reports.py`. The service receives required keyword-only `snapshots` and `flow_root` dependencies, with no Core or implicit reads at construction. `build_derived_report_lifecycle_service(project_root, core, *, snapshots=None)` builds an independent default snapshot reader only for `None` and binds flow-root resolution for the later status call. `ProjectContextService.context` uses this factory without forwarding its own injected reader. An empty supplied snapshot still triggers a read before flow-root lookup. Fixed report order and paths, timestamp fallback, filesystem checks, historical exception handling and aggregate status retain the existing rules.

`ProcessSummaryReadService` belongs to `process_catalog/summary.py`; the former Garage `process_summary` function is removed. It keeps the snapshot selection or existing manifest-selection fallback, allowed-process order, current id/stage count and title/purpose/description fallbacks. Optional keyword-only project and typed resolver dependencies preserve the no-project/no-resolver paths. `build_process_summary_read_service(project_root=None, core=None)` binds a resolver provider only when Core is not `None`, performs no I/O and does not resolve a definition at construction. Each candidate fetches the current definition resolver inside the existing `try` before converting its argument to a string; only `OSError`, `ValueError` and `SystemExit` retain the historical fallback. `ProjectContextService.context` uses the factory at the original payload position, and existing Garage checks patch the canonical service. No old function or module alias is retained.

`FreshSessionBoundaryReadService` is colocated with `WorkBoundaryAdvisoryService` in `work/boundary_advisory.py`. Its three required frozen dependencies are the project path, the existing two-method `WorkReadCorePort` and a relative-path callback. `build_fresh_session_boundary_read_service(project_root, core)` supplies `LegacyWorkReadAdapter` and a deferred relative-path lambda without reading files or resolving `core.rel` at construction. `ProjectContextService.context` calls `read(work)` at the former helper position; the Garage `fresh_session_continuation` function is removed without an alias. Governed Work returns before reads. Glob order and timestamp tie handling, newest completed usable handoff selection, live route-file `is_file` checks, stable available-process de-duplication and the no-older-handoff rule retain their existing behavior. This read model keeps `session_continuity.recommendation` as `fresh`; the neighboring advisory keeps its separate `auto` projection and existing rules.

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

`WorkSelectionService` extracts existing exact Work selection, bound preference and objective matching. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_work_selection_service.py` checks retained behavior and injected dependencies.

`ProcessSelectionService` extracts existing offered process selection and bounded candidate descriptions. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_process_selection_service.py` checks retained behavior and injected dependencies.

`ProcessPinReadService` extracts existing live snapshot reads and process pin construction. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_process_pin_read_service.py` checks retained behavior and injected dependencies.

`RunCompletionPolicy` extracts existing run completion blockers and in-memory task status updates. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_run_completion_policy.py` checks retained behavior and injected dependencies.

`CompletionIntentValidationService` extracts existing completion intent validation with ordered ownership and terminal checks. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_validation_service.py` checks retained behavior and injected dependencies.

`TransitionRejectionPolicy` extracts existing recoverable transition rejection classification and response construction. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_transition_rejection_policy.py` checks retained behavior and injected dependencies.

`WorkBoundaryAdvisoryService` extracts existing process boundary recommendations and advisory handoff discovery. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_work_boundary_advisory_service.py` checks retained behavior and injected dependencies.

`CompletionDocumentService` extracts existing completion summary rendering and existing task index publication. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_document_service.py` checks retained behavior and injected dependencies.

`CompletionIntentBuilder` extracts existing self-contained completion intent construction before terminal writes. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_builder.py` checks retained behavior and injected dependencies.

`CompletionIntentReadService` extracts existing completion intent path resolution and guarded live journal reads. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; writes, locks, access checks and recovery retain their owners. `tools/smoke_completion_intent_read_service.py` checks retained behavior and injected dependencies.

`CompletionIntentReplayService` extracts existing ordered completion intent replay through existing storage and event operations. It uses explicit frozen operation dependencies without Core or transport imports. Existing private facade methods and callback overrides remain compatible; coordinator decisions, locks and access checks remain in the facade; storage and event operations retain their adapters. `tools/smoke_completion_intent_replay_service.py` checks retained behavior and injected dependencies.

`WorkTransitionCommitService` publishes an already permitted transition through explicit operation callbacks. It preserves stage history, ordered Run/Assignment publication, completion intent/replay, fresh state, projections, events and boundary advice. `ProcessExecutionService.transition` retains admission, access checks and the enclosing run lock; its constructor and transport entrypoints remain unchanged. `build_work_transition_commit_service` assembles dependencies without I/O. `tools/smoke_work_transition_commit_service.py` checks publication order, required failures and late facade overrides.
