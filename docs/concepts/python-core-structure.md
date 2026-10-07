# Python Core Structure

The core is evolving incrementally. `tools/processforge.py` is still the active legacy facade, not retired code. Existing CLI, MCP, hook entrypoints and bootstrap aliases remain unchanged.

## Current Ownership

| Module | Responsibility |
| --- | --- |
| `src/processforge_core/garage.py` | Project/context/read-model services, including `CurrentWorkService`. |
| `src/processforge_core/process_execution.py`, `continuation.py` | Governed lifecycle, selection, pinned execution, evidence and completion/recovery. |
| `src/processforge_core/work_state.py` | I/O-free completion requirements and Work-state action/blocker policy; not lifecycle authority. |
| `src/processforge_core/document_store.py`, `work_inventory.py` | YAML reading and live sorted discovery; no shared mutable document cache. |
| `src/processforge_core/work_records.py` | Live raw Run/Assignment reader; selection and recovery remain in the application service. |
| `src/processforge_core/work_context_read.py` | Existing capsule validation and assignment normalization with explicit path/validator callbacks. |
| `src/processforge_core/process_definition_read.py` | Existing effective ProcessDefinition and pin-status read rules with explicit resolver/fingerprint callbacks. |
| `src/processforge_core/project_snapshot_read.py` | Live ProjectContextSnapshot loading and raw-byte checksum through explicit path/loader/hash callbacks. |
| `src/processforge_core/ports.py` | Internal structural current-work, raw Work-record, context-read and process-definition dependencies. |
| `src/processforge_core/composition.py` | Explicit service factories and narrow legacy read/context/definition adapters. |
| `src/processforge_core/bootstrap.py` | Existing runtime module assembly and lazy access to the service factories. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade and transport/host/provider adapters. |

`build_current_work_service(project_root, port)` accepts any structurally compatible read dependency and constructs the existing service without importing the CLI or doing I/O. `RuntimeBootstrap.current_work_service(project_root)` uses the already-loaded legacy core through `LegacyWorkReadAdapter`. No service locator, global service cache or DI container is introduced.

The existing `CurrentWorkService(project_root, core)` constructor and module path are preserved. Its discovery order, missing-assignment fallback, bootstrap-placeholder handling, summary shape and error behavior are unchanged. Existing consumers need not migrate immediately.

`build_process_execution_service(project_root, workplace_root, core, *, observer=None, records=None, context=None, definitions=None, snapshots=None)` is shared by CLI, MCP and Host/Daemon. `RuntimeBootstrap.process_execution_service(...)` delegates to it. Construction does not load the CLI, resolve a project, read configuration or perform I/O. The three-argument `ProcessExecutionService` constructor remains compatible; optional dependencies are keyword-only and excluded from equality/repr. Remaining legacy dependencies are explicit, not replaced by a universal Core interface.

`WorkRecordReadPort` exposes `runs`, `load_run` and `load_assignment`. The factory defaults to `YamlWorkRecordReader`, which uses the existing `WorkInventory` and YAML loader. Roots and records are read live; no cross-request result cache is added. Direct legacy construction retains its inventory and private-path fallback, including subclass overrides. Raw readers neither choose Work nor hide duplicate/alias discovery or pending recovery.

`WorkContextReadPort` exposes `validation` and `normalized_assignment`. The default is assembled lazily through `build_work_context_read_service`, using the caller's private path callbacks and the narrow `LegacyWorkContextAdapter`. `WorkContextReadService` does not depend on the monolithic core: its four dependencies resolve paths, validate contracts and normalize assignments. Existing `work_context.py` rules still own signed identity/intent, pins, scope and stage views. Byte limits, symlink/containment checks, raw checksum, safe parsing and original error order remain intact. Default assembly captures no document/root/logger; validation and normalization return live results.

`ProcessDefinitionReadPort` exposes `effective_process(run)`. `ProcessDefinitionReadService` receives the legacy definition resolver and existing fingerprint function. By default, `_effective_process` delegates lazily through `build_process_definition_read_service` and the narrow `LegacyProcessDefinitionAdapter`. Valid and corrupt pins do not consult the catalog; legacy definitions are resolved live on each call. Returned copies preserve unknown fields. The existing `pinned`, `corrupt`, `legacy_unpinned`, `missing` statuses and exception boundaries remain unchanged. The reader does not select a process, create pins or authorize transitions; catalog resolution and other legacy dependencies remain.

`ProjectSnapshotReadPort` exposes `load(path=None)` and `checksum(path)`. The default `ProjectSnapshotReadService` is assembled lazily through `build_project_snapshot_read_service` and `LegacyProjectSnapshotAdapter`, preserving the existing YAML loader and private `_flow_root`/`_sha256_file` overrides. Pin creation passes one captured path to loading and checksum; resource selection, start preflight and capsule capture load independently. A missing file produces an empty checksum; load/hash failures retain their original order. No new cache is introduced. Snapshot-generation checks remain in `work_context.py`; its validator compares pinned capsule metadata and does not gain a live snapshot-read dependency.

`ProcessExecutionService.state()` retains exact selection, context/pin checks, evidence/outcome validation and permission readiness. `WorkStatePolicy` separately computes completion requirements and action/blockers from supplied records. It does not read files, alter records, choose caller identity or advance a process. Terminal, completed, blocked and incomplete precedence remains unchanged; permission readiness stays a separate response field.

`ProjectContextService` also accepts the keyword-only `snapshots` dependency. Its snapshot read and the compatible two-argument Garage `load_snapshot` helper reuse the existing reader through `build_project_context_snapshot_read_service`. The legacy path resolver and YAML loader run in their original order on every default call; malformed path pairs and loader errors propagate unchanged. Assembly performs no I/O, and a legacy read does not require a checksum callback. Existing MCP context consumers use `build_project_context_service` after their session/project guards. Freshness checks, context payloads, request scopes and other legacy Garage dependencies remain in their existing owners; composition grants no permissions.

`ResourceSearchService` accepts the same keyword-only `snapshots` port. Default reads in readiness coverage and search use the compatible Garage helper; an explicitly supplied empty snapshot still bypasses loading. The search freshness guard precedes reading, while blocked readiness retains its existing coverage read. `build_resource_search_service` assembles the existing MCP search consumer without I/O, after ingress guards. Index maintenance, query arguments, navigation, coverage, payloads and error boundaries retain their existing behavior.

`ResourceResolveService` accepts a keyword-only `snapshots` port through the same helper. An empty resource id still returns project metadata without reading. `build_resource_resolve_service` assembles the MCP resolver without I/O, after the existing binding and freshness guards. Selection order, aliases, denied results, path reference resolution and private navigation retain their behavior. Host uses the compatible constructor of this shared service; its routing is unchanged.

`GarageModeService` uses the same keyword-only read port. Its existing `snapshot or ...` fallback is preserved: an empty supplied snapshot triggers a read, while a nonempty one bypasses it. `build_garage_mode_service` assembles the existing `ProjectContextService.context` consumer without I/O and preserves the default three-argument constructor call. Context does not forward its own optional reader into the mode fallback. Coordination, session representation, blockers and mode policy retain their behavior; a session alone does not promote Garage to Forge.

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

`tools/smoke_garage_snapshot_read_composition.py` covers Garage snapshot injection, live paths, constructor compatibility, context/runtime payloads, error order, request isolation and MCP composition after ingress guards. It supports retained original methods through `--baseline` and confines fixtures through `--scratch-root`.

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
